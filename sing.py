import os
import sys
import pyodbc
import pandas as pd
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
from pathlib import Path

# =================================================================
# 1. CONFIGURAÇÕES DE DIRETÓRIOS (DINÂMICAS)
# =================================================================

# Pega o caminho de onde este script está (C:\...\Ante)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_CI = os.environ.get("HEADLESS", "").lower() == "true"

if IS_CI:
    # No CI, arquivos .env e clientes ficam no diretorio do repo
    DIRETORIO_BASE = os.getcwd()
    DIRETORIO_ARQUIVO_CLIENTES = os.getcwd()
    DIRETORIO_SAIDA_RELATORIOS = os.path.join(os.getcwd(), 'relatorios_envio')
else:
    # Local
    DIRETORIO_BASE = os.path.join(os.path.dirname(BASE_DIR), 'Reporte - SING')
    DIRETORIO_ARQUIVO_CLIENTES = os.path.join(DIRETORIO_BASE, 'teste_banco', 'Clientes')
    DIRETORIO_SAIDA_RELATORIOS = os.path.join(os.path.dirname(BASE_DIR), 'Envio de e-mail - VSR', 'clientes_para_envio')

NOME_ARQUIVO_LOOKUP = 'clientes_listagem.xlsx'

# =================================================================
# 2. FUNÇÕES DE APOIO E AMBIENTE
# =================================================================

def carregar_credenciais(arquivo_env):
    """ Carrega credenciais do .env selecionado """
    caminho = os.path.join(DIRETORIO_BASE, arquivo_env)
    if os.path.exists(caminho):
        load_dotenv(dotenv_path=caminho, override=True)
        return True
    else:
        print(f"⚠️ ERRO: Arquivo {arquivo_env} não encontrado em {DIRETORIO_BASE}")
        return False

def buscar_dados_mapeamento(arquivo_lookup, diretorio_lookup):
    """ Lê o arquivo Excel de clientes """
    caminho_completo = os.path.join(diretorio_lookup, arquivo_lookup)
    try:
        if not os.path.exists(caminho_completo):
            raise FileNotFoundError(f"Arquivo não existe: {caminho_completo}")

        print(f"\nPasso 1: Lendo mapeamento em '{caminho_completo}'...")
        df = pd.read_excel(caminho_completo, header=None, names=['NomeCliente', 'IDCliente', 'ConfigEnv'])
        
        df['IDCliente'] = pd.to_numeric(df['IDCliente'], errors='coerce')
        df.dropna(subset=['IDCliente'], inplace=True)
        df['IDCliente'] = df['IDCliente'].astype(int)
        df['NomeCliente'] = df['NomeCliente'].astype(str).str.strip()
        df['ConfigEnv'] = df['ConfigEnv'].fillna('.env').astype(str).str.strip()
        
        print(f"✔️ Mapeamento carregado: {len(df)} empresas encontradas.")
        return df
    except Exception as e:
        print(f"❌ Erro crítico ao ler clientes_listagem: {e}")
        sys.exit()

# =================================================================
# 3. CONSULTA SQL E PROCESSAMENTO
# =================================================================

def consultar_veiculos(id_empresa_consulta):
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_DATABASE')
    username = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')
    driver = os.getenv('DB_DRIVER')

    sql_query = """
    SET NOCOUNT ON;
    SELECT veiculo.Placa, veiculo.Descricao, up.DataGPSTZ, up.DataRecebido
    FROM GPS_Ultimas_Posicoes up
    INNER JOIN Tbl_Veiculo veiculo ON up.IDVeiculo = veiculo.ID
    WHERE veiculo.IDCliente = ? AND veiculo.ativo = 1
    ORDER BY DataGPSTZ DESC;
    """
    
    try:
        if not all([server, database, username, password]):
            print("❌ Erro: Variáveis de banco incompletas no arquivo de configuração.")
            return None

        conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
        cnxn = pyodbc.connect(conn_str)
        df_veiculos = pd.read_sql(sql_query, cnxn, params=[id_empresa_consulta])
        cnxn.close()
        return df_veiculos
    except Exception as e:
        print(f"❌ Falha na conexão/query para ID {id_empresa_consulta}: {e}")
        return None

def gerar_arquivo_excel(df_dados, nome_empresa_param, diretorio_saida):
    if df_dados is None or df_dados.empty:
        return

    df_dados = df_dados.rename(columns={'DataGPSTZ': 'Data de reporte', 'DataRecebido': 'Data de recebimento'})
    for col in ['Data de reporte', 'Data de recebimento']:
        df_dados[col + '_dt'] = pd.to_datetime(df_dados[col], errors='coerce')

    limite = datetime.now() - timedelta(hours=48)
    df_filtrado = df_dados[(df_dados['Data de reporte_dt'] < limite) | (df_dados['Data de reporte_dt'].isna())].copy()

    if df_filtrado.empty:
        print(f"ℹ️ {nome_empresa_param}: Sem veículos em atraso (>48h). Gerando arquivo VSR0...")
        # Gera arquivo vazio com VSR0 para sinalizar 0 veiculos
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        nome_seguro = "".join(c for c in nome_empresa_param if c.isalnum() or c in (' ', '_', '-')).strip()
        nome_arquivo = f"{nome_seguro}_SING_VSR0_{timestamp}.xlsx"
        caminho_final = os.path.join(diretorio_saida, nome_arquivo)
        try:
            os.makedirs(diretorio_saida, exist_ok=True)
            pd.DataFrame(columns=['Placa', 'Descricao', 'Data de reporte', 'Data de recebimento']).to_excel(
                caminho_final, index=False, sheet_name='DadosVeiculos'
            )
            print(f"✔️ Relatório VSR0 salvo: {nome_arquivo}")
        except Exception as e:
            print(f"❌ Erro ao salvar Excel VSR0: {e}")
        return

    df_ordenado = df_filtrado.sort_values(by='Data de reporte_dt', ascending=False, na_position='last')
    for col in ['Data de reporte', 'Data de recebimento']:
        df_ordenado[col] = df_ordenado[col + '_dt'].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('')

    df_final = df_ordenado.drop(columns=['Data de reporte_dt', 'Data de recebimento_dt'])

    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    nome_seguro = "".join(c for c in nome_empresa_param if c.isalnum() or c in (' ', '_', '-')).strip()
    nome_arquivo = f"{nome_seguro}_SING_VSR_{len(df_final)}_{timestamp}.xlsx"
    caminho_final = os.path.join(diretorio_saida, nome_arquivo)

    try:
        os.makedirs(diretorio_saida, exist_ok=True)
        with pd.ExcelWriter(caminho_final, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='DadosVeiculos')
            ws = writer.sheets['DadosVeiculos']
            for i, col in enumerate(df_final.columns):
                width = max(df_final[col].astype(str).map(len).max(), len(col)) + 2
                ws.column_dimensions[chr(65 + i)].width = width
        print(f"✔️ Relatório salvo: {nome_arquivo}")
    except Exception as e:
        print(f"❌ Erro ao salvar Excel: {e}")

# =================================================================
# 4. LOOP PRINCIPAL
# =================================================================

if __name__ == "__main__":
    print(f"🚀 Iniciando processamento - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    df_clientes = buscar_dados_mapeamento(NOME_ARQUIVO_LOOKUP, DIRETORIO_ARQUIVO_CLIENTES)

    for index, cliente in df_clientes.iterrows():
        id_emp = cliente['IDCliente']
        nome_emp = cliente['NomeCliente']
        arq_env = cliente['ConfigEnv']

        print(f"\n--- [Empresa: {nome_emp} | ID: {id_emp}] ---")
        print(f"⚙️ Carregando configurações de: {arq_env}")
        
        if carregar_credenciais(arq_env):
            dados = consultar_veiculos(id_emp)
            if dados is not None:
                gerar_arquivo_excel(dados, nome_emp, DIRETORIO_SAIDA_RELATORIOS)
        
        time.sleep(2)

    print("\n🏁 Processamento finalizado com sucesso.")