import os, sys, io, pyodbc, smtplib, requests, time
import pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from email.message import EmailMessage

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# =================================================================
# CONFIGURACAO
# =================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_CI = os.environ.get("HEADLESS", "").lower() == "true"
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'), override=True)

# Modo teste: True = envia apenas para Gustavo | False = equipe interna
MODO_TESTE = True

SMTP_HOST, SMTP_PORT = 'smtp.gmail.com', 465
SMTP_USER = 'veiculosemreportar@gmail.com'
SMTP_PASS = 'svhh lgau okua kkof'
URL_ASSINATURA = "https://drive.google.com/uc?export=view&id=1si56G_we2n1lhOTvuomgFTscogWdxrP9"

EMAIL_TESTE = 'gustavo.martins@optimuz.com.br'
DESTINATARIOS_PRODUCAO = [
    'gustavo.martins@optimuz.com.br', 'marciele@newsgps.com.br',
    'julyana@newsgps.com.br', 'marlos.miranda@newsgps.com.br',
    'renata.braga@newsgps.com.br', 'adriana.florencio@newsgps.com.br',
    'andreia.ribeiro@newsgps.com.br', 'jessica.dias@quadrisystems.com.br',
    'hudson.ferreira@optimuz.com.br', 'gustavo.andrade@quadrisystems.com.br',
    'leandro.gomes@optimuz.com.br', 'joao.peres@optimuz.com.br',
    'adriel.carvalho@newsgps.com.br', 'gabriel.oliveira@quadrisystems.com.br',
]

# Regras de alerta por faixa de frota
REGRAS = [
    (1,  25,  30),  # 1-25 veiculos: alerta se >= 30% sem reportar
    (26, 75,  20),  # 26-75 veiculos: alerta se >= 20%
    (76, None, 10), # 76+ veiculos: alerta se >= 10%
]

# Diretorio do clientes_listagem.xlsx (SING)
if IS_CI:
    DIRETORIO_CLIENTES = os.getcwd()
else:
    DIRETORIO_CLIENTES = os.path.join(os.path.dirname(BASE_DIR), 'Reporte - SING', 'teste_banco', 'Clientes')

# Configuracoes da Telemetria (mesmas do telemetria.py)
TELEMETRIA_CONFIGS = [
    {
        "user": "gustavo.martins@optimuz.com.br.ng",
        "group_ids": ["14405", "14416", "14380", "14351", "14451", "14435", "14447", "14445"]
    },
]
TELEMETRIA_PASSWORD = os.getenv("API_PASSWORD", "gustavo")
PALAVRAS_IGNORADAS = ["vendido", "desativado", "historico", "histórico", "sinistro", "teste"]

# =================================================================
# FUNCOES COMUNS
# =================================================================

def obter_limite_pct(total_veiculos):
    for min_v, max_v, pct in REGRAS:
        if max_v is None:
            if total_veiculos >= min_v:
                return pct
        elif min_v <= total_veiculos <= max_v:
            return pct
    return None

def aplicar_regras(df_resumo):
    """Aplica regras de faixa e retorna apenas empresas que atingem o criterio."""
    if df_resumo.empty:
        return pd.DataFrame()
    df_resumo['PctSemReportar'] = (df_resumo['SemReportar'] / df_resumo['TotalVeiculos'] * 100).round(2)
    df_resumo['LimitePct'] = df_resumo['TotalVeiculos'].apply(obter_limite_pct)
    return df_resumo[
        (df_resumo['LimitePct'].notna()) &
        (df_resumo['PctSemReportar'] >= df_resumo['LimitePct'])
    ].copy()

# =================================================================
# SING - Consulta via banco de dados
# =================================================================

def conectar_sing():
    server, database = os.getenv('DB_SERVER'), os.getenv('DB_DATABASE')
    username, password = os.getenv('DB_USERNAME'), os.getenv('DB_PASSWORD')
    driver = os.getenv('DB_DRIVER')
    if IS_CI and driver and '17' in driver:
        driver = '{ODBC Driver 18 for SQL Server}'
    conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    if IS_CI:
        conn_str += ';TrustServerCertificate=yes;Encrypt=yes'
    return pyodbc.connect(conn_str)

def processar_sing():
    """Consulta veiculos SING apenas das empresas do clientes_listagem.xlsx."""
    print("\n--- SISTEMA: SING ---")

    # Le mapeamento de empresas
    caminho_clientes = os.path.join(DIRETORIO_CLIENTES, 'clientes_listagem.xlsx')
    if not os.path.exists(caminho_clientes):
        print(f"Arquivo nao encontrado: {caminho_clientes}")
        return pd.DataFrame()

    df_clientes = pd.read_excel(caminho_clientes, header=None, names=['NomeCliente', 'IDCliente', 'ConfigEnv'])
    df_clientes['IDCliente'] = pd.to_numeric(df_clientes['IDCliente'], errors='coerce')
    df_clientes.dropna(subset=['IDCliente'], inplace=True)
    df_clientes['IDCliente'] = df_clientes['IDCliente'].astype(int)
    df_clientes['NomeCliente'] = df_clientes['NomeCliente'].astype(str).str.strip()
    print(f"Empresas SING no VSR: {len(df_clientes)}")

    ids_vsr = df_clientes['IDCliente'].tolist()
    if not ids_vsr:
        return pd.DataFrame()

    conn = conectar_sing()
    placeholders = ','.join(['?'] * len(ids_vsr))
    veiculos = pd.read_sql(f"""
        SET NOCOUNT ON;
        SELECT veiculo.IDCliente, veiculo.Placa, veiculo.Descricao, up.DataGPSTZ
        FROM GPS_Ultimas_Posicoes up
        INNER JOIN Tbl_Veiculo veiculo ON up.IDVeiculo = veiculo.ID
        WHERE veiculo.ativo = 1 AND veiculo.IDCliente IN ({placeholders})
    """, conn, params=ids_vsr)
    conn.close()

    print(f"Veiculos ativos SING: {len(veiculos)}")

    if veiculos.empty:
        return pd.DataFrame()

    limite_3h = datetime.now() - timedelta(hours=3)
    veiculos['DataGPSTZ'] = pd.to_datetime(veiculos['DataGPSTZ'], errors='coerce')
    veiculos['sem_reportar'] = (veiculos['DataGPSTZ'] < limite_3h) | (veiculos['DataGPSTZ'].isna())

    resumo = veiculos.groupby('IDCliente').agg(
        TotalVeiculos=('Placa', 'count'),
        SemReportar=('sem_reportar', 'sum')
    ).reset_index()
    resumo['SemReportar'] = resumo['SemReportar'].astype(int)

    # Adiciona nome da empresa
    resumo = resumo.merge(df_clientes[['IDCliente', 'NomeCliente']], on='IDCliente', how='left')
    resumo.rename(columns={'NomeCliente': 'Empresa'}, inplace=True)

    alertas = aplicar_regras(resumo)
    if not alertas.empty:
        print(f"Empresas SING em alerta: {len(alertas)}")
    else:
        print("Nenhuma empresa SING atingiu os criterios.")
    return alertas

# =================================================================
# TELEMETRIA - Consulta via API REST
# =================================================================

def parse_data_telemetria(data_str):
    if data_str and data_str.endswith("Z"):
        data_str = data_str[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(data_str)
    except (ValueError, TypeError):
        return None

def processar_telemetria():
    """Consulta veiculos Telemetria via API para os group_ids configurados."""
    print("\n--- SISTEMA: TELEMETRIA ---")
    resultados = []
    agora_utc = datetime.now(timezone.utc)
    limite_3h = agora_utc - timedelta(hours=3)

    for config in TELEMETRIA_CONFIGS:
        user = config["user"]
        try:
            url = f"https://l7g3za95wd.execute-api.us-west-2.amazonaws.com/MovaApi/login?user={user}&pass={TELEMETRIA_PASSWORD}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            token = resp.json().get("token")
            if not token:
                print(f"Token nao obtido para {user}")
                continue
        except Exception as e:
            print(f"Erro no token para {user}: {e}")
            continue

        for group_id in config["group_ids"]:
            try:
                url = f"https://l7g3za95wd.execute-api.us-west-2.amazonaws.com/MovaApi/devstatus?group_id={group_id}"
                resp = requests.get(url, headers={"token": token}, timeout=15)
                resp.raise_for_status()
                dados = resp.json()
                lista = dados.get("data", []) if isinstance(dados, dict) else dados

                if not lista:
                    continue

                nome_grupo = lista[0].get("group_name", f"Grupo {group_id}")
                total = 0
                sem_reportar = 0

                for item in lista:
                    if not (isinstance(item, dict) and item.get("device_identifier")):
                        continue
                    nome_unidade = str(item.get("tracked_unit_label2", "")).lower()
                    if any(p in nome_unidade for p in PALAVRAS_IGNORADAS):
                        continue

                    total += 1
                    local_time = parse_data_telemetria(item.get("local_time"))
                    if local_time and local_time.tzinfo is None:
                        local_time = local_time.replace(tzinfo=timezone.utc)

                    if not local_time or local_time < limite_3h:
                        sem_reportar += 1

                if total > 0:
                    resultados.append({
                        'IDCliente': group_id,
                        'Empresa': nome_grupo,
                        'TotalVeiculos': total,
                        'SemReportar': sem_reportar,
                    })

            except Exception as e:
                print(f"Erro no group_id {group_id}: {e}")

            time.sleep(2)

    if not resultados:
        print("Nenhum dado de telemetria obtido.")
        return pd.DataFrame()

    df = pd.DataFrame(resultados)
    print(f"Grupos Telemetria consultados: {len(df)} | Veiculos: {df['TotalVeiculos'].sum()}")

    alertas = aplicar_regras(df)
    if not alertas.empty:
        print(f"Empresas Telemetria em alerta: {len(alertas)}")
    else:
        print("Nenhuma empresa Telemetria atingiu os criterios.")
    return alertas

# =================================================================
# EMAIL
# =================================================================

def gerar_tabela_html(df):
    """Gera tabela HTML a partir de um DataFrame de alertas."""
    return "".join(
        f"<tr>"
        f"<td style='border:1px solid #ddd;padding:8px'>{r['Empresa']}</td>"
        f"<td style='border:1px solid #ddd;padding:8px;text-align:center'>{r['TotalVeiculos']}</td>"
        f"<td style='border:1px solid #ddd;padding:8px;text-align:center'>{r['SemReportar']}</td>"
        f"<td style='border:1px solid #ddd;padding:8px;text-align:center;color:red'>{r['PctSemReportar']}%</td>"
        f"<td style='border:1px solid #ddd;padding:8px;text-align:center'>{r['LimitePct']}%</td>"
        f"</tr>"
        for _, r in df.iterrows()
    )

def enviar_email_alerta(alertas_sing, alertas_telemetria):
    """Envia e-mail HTML com alertas separados por sistema."""
    agora_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    destinatarios = [EMAIL_TESTE] if MODO_TESTE else DESTINATARIOS_PRODUCAO

    tem_sing = not alertas_sing.empty
    tem_telemetria = not alertas_telemetria.empty

    if not tem_sing and not tem_telemetria:
        print("\nNenhuma empresa atingiu os criterios de alerta. E-mail nao enviado.")
        return

    header_tabela = """<thead><tr style='background-color:#f2f2f2'>
        <th style='border:1px solid #ddd;padding:8px;text-align:left'>Empresa</th>
        <th style='border:1px solid #ddd;padding:8px'>Total Veiculos</th>
        <th style='border:1px solid #ddd;padding:8px'>Sem Reportar</th>
        <th style='border:1px solid #ddd;padding:8px'>%</th>
        <th style='border:1px solid #ddd;padding:8px'>Regra</th>
    </tr></thead>"""

    corpo_html = f"""<p>Prezados,</p>
    <p>Segue a listagem de empresas com percentual significativo de veiculos <b>sem reportar ha 3 ou mais horas</b>.</p>
    <p>Data/Hora da verificacao: <b>{agora_str}</b></p>"""

    if tem_sing:
        corpo_html += f"""
        <h3 style='color:#333;border-bottom:2px solid #ddd;padding-bottom:5px'>Sistema: SING</h3>
        <table style='border-collapse:collapse;width:100%;font-family:Arial,sans-serif;margin-bottom:20px'>
        {header_tabela}<tbody>{gerar_tabela_html(alertas_sing)}</tbody></table>"""

    if tem_telemetria:
        corpo_html += f"""
        <h3 style='color:#333;border-bottom:2px solid #ddd;padding-bottom:5px'>Sistema: Telemetria</h3>
        <table style='border-collapse:collapse;width:100%;font-family:Arial,sans-serif;margin-bottom:20px'>
        {header_tabela}<tbody>{gerar_tabela_html(alertas_telemetria)}</tbody></table>"""

    corpo_html += """<br>
    <p><small>Regras aplicadas: 1-25 veiculos: alerta >= 30% | 26-75: >= 20% | 76+: >= 10%</small></p>"""

    msg = EmailMessage()
    msg['Subject'] = f"Alerta - Veiculos sem reportar ha 3+ horas - {agora_str}"
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(destinatarios)
    msg.set_content(f"Alerta de veiculos sem reportar - {agora_str}. Verifique a versao HTML.")
    msg.add_alternative(
        f"<html><body>{corpo_html}<p>Atenciosamente,<br>Tryvia</p>"
        f"<img src='{URL_ASSINATURA}' alt='Assinatura' style='width:200px;height:auto'>"
        f"</body></html>", subtype='html')

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        modo = "TESTE" if MODO_TESTE else "PRODUCAO"
        print(f"\nE-mail enviado com sucesso ({modo}) para: {', '.join(destinatarios)}")
    except Exception as e:
        print(f"\nErro ao enviar e-mail: {e}")

# =================================================================
# MAIN
# =================================================================

if __name__ == "__main__":
    print(f"Alerta de Veiculos Sem Reportar - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if MODO_TESTE:
        print("** MODO TESTE - E-mails apenas para Gustavo **")

    try:
        alertas_sing = processar_sing()
    except Exception as e:
        print(f"Erro no processamento SING: {e}")
        alertas_sing = pd.DataFrame()

    try:
        alertas_telemetria = processar_telemetria()
    except Exception as e:
        print(f"Erro no processamento Telemetria: {e}")
        alertas_telemetria = pd.DataFrame()

    # Exibe resumo no console
    for sistema, df in [("SING", alertas_sing), ("TELEMETRIA", alertas_telemetria)]:
        if not df.empty:
            print(f"\n{sistema} - {len(df)} empresas em alerta:")
            print(df[['Empresa', 'TotalVeiculos', 'SemReportar', 'PctSemReportar', 'LimitePct']].to_string(index=False))

    # Envia e-mail
    enviar_email_alerta(alertas_sing, alertas_telemetria)
