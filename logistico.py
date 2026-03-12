import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import re

# ==========================================================
# 1. CONFIGURAÇÕES DE CAMINHO (GUSTAVO)
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent
IS_CI = os.environ.get("HEADLESS", "").lower() == "true"

if IS_CI:
    # No CI, arquivos estão em output/
    CAMINHO_BASE = Path(os.getcwd()) / "output"
    CAMINHO_ENVIO = Path(os.getcwd()) / "relatorios_envio"
else:
    # Local
    CAMINHO_BASE = BASE_DIR.parent / "Reporte - Logistico" / "Base"
    CAMINHO_ENVIO = BASE_DIR.parent / "Envio de e-mail - VSR" / "clientes_para_envio"

TERMOS_IGNORADOS = ['_Historico', '_Reserva', '_Oficina', '_Venda', '_Teste', 'RESERVA', 'OFICINA', '_HISTORICO']

CAMINHO_ENVIO.mkdir(parents=True, exist_ok=True)

# ==========================================================
# 2. FUNÇÕES DE APOIO
# ==========================================================

def limpar_nome_empresa(nome_sujo):
    if not nome_sujo or pd.isna(nome_sujo):
        return "EmpresaDesconhecida"
    limpo = re.sub(r'[^\w\s-]', '', str(nome_sujo).strip())
    return "_".join(limpo.split())

def aplicar_filtros_veiculo(df, coluna_veiculo):
    if df.empty or coluna_veiculo not in df.columns:
        return df
    padrao_regex = '|'.join(TERMOS_IGNORADOS)
    return df[~df[coluna_veiculo].astype(str).str.contains(padrao_regex, case=False, na=False)].copy()

def obter_arquivo_mais_recente(pasta, padrao_regex):
    """Retorna o arquivo mais recente que combina com o padrão, baseado na data de modificação."""
    arquivos_encontrados = []
    for arquivo in os.listdir(pasta):
        if padrao_regex.match(arquivo):
            caminho_completo = pasta / arquivo
            data_mod = os.path.getmtime(caminho_completo)
            arquivos_encontrados.append((arquivo, data_mod))
    
    if not arquivos_encontrados:
        return None
    
    # Ordena por data de modificação (mais recente primeiro)
    arquivos_encontrados.sort(key=lambda x: x[1], reverse=True)
    return arquivos_encontrados[0][0]

def limpar_arquivos_base(pasta, padrao_regex):
    """Remove todos os arquivos que combinam com o padrão na pasta Base."""
    removidos = 0
    for arquivo in os.listdir(pasta):
        if padrao_regex.match(arquivo):
            try:
                os.remove(pasta / arquivo)
                removidos += 1
            except Exception as e:
                print(f"⚠️ Erro ao remover {arquivo}: {e}")
    if removidos > 0:
        print(f"🗑️ {removidos} arquivo(s) removido(s) da pasta Base.")

# ==========================================================
# 3. PROCESSAMENTOS
# ==========================================================

def processar_arquivos_na_pasta():
    """ Processa UltimasPosicoes (apenas o arquivo mais recente) """
    AGORA = datetime.now()
    LIMITE_DATA = AGORA - timedelta(hours=48)
    DATA_STR = AGORA.strftime("%d-%m-%Y_%Hh%M")
    
    col_map = {'Cliente': 'B', 'Veículo': 'C', 'Data da Posição': 'F', 'Data de Atualização': 'G'}
    df_total = pd.DataFrame()

    print(f"\n>>> Verificando UltimasPosicoes...")
    
    padrao = re.compile(r"UltimasPosicoes.*\.xls", re.IGNORECASE)

    if not CAMINHO_BASE.exists():
        print(f"⚠️ Erro: Pasta Base não encontrada em {CAMINHO_BASE}")
        return

    # Seleciona apenas o arquivo mais recente
    arquivo_recente = obter_arquivo_mais_recente(CAMINHO_BASE, padrao)
    if not arquivo_recente:
        print("ℹ️ Nenhum arquivo UltimasPosicoes encontrado na pasta Base.")
        return

    print(f"[*] Processando o mais recente: {arquivo_recente}")

    todas_empresas = set()

    try:
        temp_df = pd.read_excel(CAMINHO_BASE / arquivo_recente, header=0, engine="xlrd")
        if 'Cliente' in temp_df.columns and not temp_df['Cliente'].dropna().empty:
            for emp_raw in temp_df['Cliente'].dropna().unique():
                emp_nome = limpar_nome_empresa(emp_raw)
                todas_empresas.add(emp_nome)

        df_res = temp_df[list(col_map.keys())].rename(columns=col_map)
        df_res['F'] = pd.to_datetime(df_res['F'], errors='coerce')
        df_res = df_res[df_res['F'] < LIMITE_DATA].copy()
        df_res = aplicar_filtros_veiculo(df_res, 'C')

        if not df_res.empty:
            # Extrai empresa de cada linha para suportar múltiplas empresas no mesmo arquivo
            df_res['Empresa_Final'] = df_res['B'].apply(lambda x: limpar_nome_empresa(x) if pd.notna(x) else "EmpresaDesconhecida")
            df_total = pd.concat([df_total, df_res], ignore_index=True)
    except Exception as e:
        print(f"🚫 Erro em {arquivo_recente}: {e}")

    # Gera arquivos para empresas COM veículos em atraso
    empresas_com_atraso = set()
    if not df_total.empty:
        df_total.drop_duplicates(subset=['C'], inplace=True)
        for emp in df_total['Empresa_Final'].unique():
            empresas_com_atraso.add(emp)
            df_emp = df_total[df_total['Empresa_Final'] == emp].copy()
            vsr = df_emp['C'].nunique()
            df_final = df_emp.drop(columns=['Empresa_Final']).rename(columns={v:k for k,v in col_map.items()})
            df_final['Data da Posição'] = df_final['Data da Posição'].dt.strftime('%d/%m/%Y %H:%M:%S')

            nome_out = f"{emp}_Global_VSR{vsr}_{DATA_STR}.xlsx"
            df_final.to_excel(CAMINHO_ENVIO / nome_out, index=False)
            print(f"✅ Gerado Global: {nome_out}")

    # Gera VSR0 para empresas SEM veículos em atraso
    empresas_sem_atraso = todas_empresas - empresas_com_atraso
    for emp_nome in empresas_sem_atraso:
        nome_out = f"{emp_nome}_Global_VSR0_{DATA_STR}.xlsx"
        caminho_out = CAMINHO_ENVIO / nome_out
        if not caminho_out.exists():
            pd.DataFrame(columns=['Cliente', 'Veículo', 'Data da Posição', 'Data de Atualização']).to_excel(
                caminho_out, index=False
            )
            print(f"✅ Gerado Global VSR0: {nome_out}")

    # Limpa todos os arquivos UltimasPosicoes da pasta Base
    print("\n🗑️ Limpando arquivos UltimasPosicoes da pasta Base...")
    limpar_arquivos_base(CAMINHO_BASE, padrao)

def processar_arquivo_logistico():
    AGORA = datetime.now()
    LIMITE_DATA = AGORA - timedelta(hours=48)
    DATA_STR = AGORA.strftime("%d-%m-%Y_%Hh%M")

    print(f"\n>>> Verificando Logistico.xls...")
    padrao = re.compile(r"logistico.*\.xls(x)?", re.IGNORECASE)

    if not CAMINHO_BASE.exists(): return

    # Seleciona apenas o arquivo mais recente
    arquivo_recente = obter_arquivo_mais_recente(CAMINHO_BASE, padrao)
    if not arquivo_recente:
        print("ℹ️ Nenhum arquivo Logistico encontrado na pasta Base.")
        return

    print(f"[*] Processando o mais recente: {arquivo_recente}")

    todas_empresas = set()
    df_consolidado = pd.DataFrame()

    try:
        caminho = CAMINHO_BASE / arquivo_recente
        engine = 'xlrd' if arquivo_recente.endswith('.xls') else 'openpyxl'
        df_bruto = pd.read_excel(caminho, header=None, engine=engine)
        
        df = df_bruto[[0, 1, 6, 7]].rename(columns={0:'Emp', 1:'Vei', 6:'Pos', 7:'Atu'}).iloc[2:].copy()

        # Armazena todas as empresas ANTES de qualquer filtro
        for emp_raw in df['Emp'].dropna().unique():
            todas_empresas.add(limpar_nome_empresa(emp_raw))

        df['Pos'] = pd.to_datetime(df['Pos'], errors='coerce')
        df = df[df['Pos'] < LIMITE_DATA].copy()
        df = aplicar_filtros_veiculo(df, 'Vei')

        if not df.empty:
            df_consolidado = pd.concat([df_consolidado, df], ignore_index=True)
    except Exception as e:
        print(f"🚫 Erro Logistico: {e}")

    # Deduplica veículos (mantém registro mais recente)
    if not df_consolidado.empty:
        df_consolidado = df_consolidado.sort_values('Pos', ascending=False).drop_duplicates(subset=['Vei'], keep='first')

    # Gera arquivos para empresas COM veículos em atraso
    empresas_com_atraso = set()
    if not df_consolidado.empty:
        for emp_raw in df_consolidado['Emp'].unique():
            emp_nome = limpar_nome_empresa(emp_raw)
            empresas_com_atraso.add(emp_nome)
            df_emp = df_consolidado[df_consolidado['Emp'] == emp_raw].copy()
            vsr = df_emp['Vei'].nunique()
            
            df_saida = df_emp.rename(columns={'Emp':'Cliente','Vei':'Veículo','Pos':'Posição','Atu':'Atualização'})
            df_saida['Posição'] = df_saida['Posição'].dt.strftime('%d/%m/%Y %H:%M:%S')
            
            nome_out = f"{emp_nome}_Logistico_VSR{vsr}_{DATA_STR}.xlsx"
            df_saida.to_excel(CAMINHO_ENVIO / nome_out, index=False)
            print(f"✅ Gerado Logistico: {nome_out}")

    # Gera VSR0 para empresas SEM veículos em atraso
    empresas_sem_atraso = todas_empresas - empresas_com_atraso
    for emp_nome in empresas_sem_atraso:
        nome_out = f"{emp_nome}_Logistico_VSR0_{DATA_STR}.xlsx"
        caminho_out = CAMINHO_ENVIO / nome_out
        if not caminho_out.exists():
            pd.DataFrame(columns=['Cliente', 'Veículo', 'Posição', 'Atualização']).to_excel(
                caminho_out, index=False
            )
            print(f"✅ Gerado Logistico VSR0: {nome_out}")

    # Limpa todos os arquivos Logistico da pasta Base
    print("\n🗑️ Limpando arquivos Logistico da pasta Base...")
    limpar_arquivos_base(CAMINHO_BASE, padrao)

# ==========================================================
# 4. EXECUÇÃO
# ==========================================================
if __name__ == "__main__":
    print("="*60)
    print(f"INICIANDO PROCESSAMENTO LOGÍSTICO")
    print(f"BASE: {CAMINHO_BASE}")
    print("="*60)
    
    processar_arquivos_na_pasta()
    processar_arquivo_logistico()
    
    print(f"\n✅ Concluído!")