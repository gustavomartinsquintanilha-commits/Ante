import os, sys, io, pyodbc, smtplib
import pandas as pd
from datetime import datetime, timedelta
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

# =================================================================
# FUNCOES
# =================================================================

def conectar():
    server, database = os.getenv('DB_SERVER'), os.getenv('DB_DATABASE')
    username, password = os.getenv('DB_USERNAME'), os.getenv('DB_PASSWORD')
    driver = os.getenv('DB_DRIVER')
    if IS_CI and driver and '17' in driver:
        driver = '{ODBC Driver 18 for SQL Server}'
    conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    if IS_CI:
        conn_str += ';TrustServerCertificate=yes;Encrypt=yes'
    return pyodbc.connect(conn_str)

def consultar_veiculos(conn):
    """Busca TODOS os veiculos ativos com ultima posicao."""
    empresas = pd.read_sql("SET NOCOUNT ON; SELECT ID, Apelido FROM dbo.Com_Empresa", conn)
    veiculos = pd.read_sql("""
        SET NOCOUNT ON;
        SELECT veiculo.IDCliente, veiculo.Placa, veiculo.Descricao, up.DataGPSTZ
        FROM GPS_Ultimas_Posicoes up
        INNER JOIN Tbl_Veiculo veiculo ON up.IDVeiculo = veiculo.ID
        WHERE veiculo.ativo = 1
        ORDER BY veiculo.IDCliente, up.DataGPSTZ DESC
    """, conn)
    return empresas, veiculos

def obter_limite_pct(total_veiculos):
    """Retorna o percentual limite de alerta conforme o tamanho da frota."""
    for min_v, max_v, pct in REGRAS:
        if max_v is None:
            if total_veiculos >= min_v:
                return pct
        elif min_v <= total_veiculos <= max_v:
            return pct
    return None

def processar_alertas(veiculos, empresas):
    """Filtra veiculos sem reportar ha 3h+ e aplica regras de faixa."""
    if veiculos.empty:
        return pd.DataFrame()

    agora = datetime.now()
    limite_3h = agora - timedelta(hours=3)

    # Converte DataGPSTZ para datetime
    veiculos['DataGPSTZ'] = pd.to_datetime(veiculos['DataGPSTZ'], errors='coerce')

    # Marca veiculos sem reportar (DataGPSTZ < 3h atras OU nulo)
    veiculos['sem_reportar'] = (veiculos['DataGPSTZ'] < limite_3h) | (veiculos['DataGPSTZ'].isna())

    # Agrupa por empresa
    resumo = veiculos.groupby('IDCliente').agg(
        TotalVeiculos=('Placa', 'count'),
        SemReportar=('sem_reportar', 'sum')
    ).reset_index()

    resumo['SemReportar'] = resumo['SemReportar'].astype(int)
    resumo['PctSemReportar'] = (resumo['SemReportar'] / resumo['TotalVeiculos'] * 100).round(2)

    # Aplica regra de faixa
    resumo['LimitePct'] = resumo['TotalVeiculos'].apply(obter_limite_pct)
    alertas = resumo[
        (resumo['LimitePct'].notna()) &
        (resumo['PctSemReportar'] >= resumo['LimitePct'])
    ].copy()

    if alertas.empty:
        return pd.DataFrame()

    # De/Para com nome da empresa
    alertas = alertas.merge(empresas, left_on='IDCliente', right_on='ID', how='left').drop(columns=['ID'])
    return alertas.sort_values('PctSemReportar', ascending=False)

def enviar_email_alerta(df):
    """Envia e-mail HTML com a listagem de empresas em alerta."""
    agora_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    destinatarios = [EMAIL_TESTE] if MODO_TESTE else DESTINATARIOS_PRODUCAO

    if df.empty:
        print("Nenhuma empresa atingiu os criterios de alerta. E-mail nao enviado.")
        return

    # Gera tabela HTML
    linhas = "".join(
        f"<tr>"
        f"<td style='border:1px solid #ddd;padding:8px'>{r['IDCliente']}</td>"
        f"<td style='border:1px solid #ddd;padding:8px'>{r['Apelido']}</td>"
        f"<td style='border:1px solid #ddd;padding:8px;text-align:center'>{r['TotalVeiculos']}</td>"
        f"<td style='border:1px solid #ddd;padding:8px;text-align:center'>{r['SemReportar']}</td>"
        f"<td style='border:1px solid #ddd;padding:8px;text-align:center;color:red'>{r['PctSemReportar']}%</td>"
        f"<td style='border:1px solid #ddd;padding:8px;text-align:center'>{r['LimitePct']}%</td>"
        f"</tr>"
        for _, r in df.iterrows()
    )

    corpo_html = f"""<p>Prezados,</p>
    <p>Segue a listagem de empresas com percentual significativo de veiculos <b>sem reportar ha 3 ou mais horas</b>.</p>
    <p>Data/Hora da verificacao: <b>{agora_str}</b></p>
    <table style='border-collapse:collapse;width:100%;font-family:Arial,sans-serif'>
    <thead><tr style='background-color:#f2f2f2'>
        <th style='border:1px solid #ddd;padding:8px;text-align:left'>ID</th>
        <th style='border:1px solid #ddd;padding:8px;text-align:left'>Empresa</th>
        <th style='border:1px solid #ddd;padding:8px'>Total Veiculos</th>
        <th style='border:1px solid #ddd;padding:8px'>Sem Reportar</th>
        <th style='border:1px solid #ddd;padding:8px'>%</th>
        <th style='border:1px solid #ddd;padding:8px'>Regra</th>
    </tr></thead><tbody>{linhas}</tbody></table>
    <br>
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
        print(f"E-mail enviado com sucesso ({modo}) para: {', '.join(destinatarios)}")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

# =================================================================
# MAIN
# =================================================================

if __name__ == "__main__":
    print(f"Alerta de Veiculos Sem Reportar - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if MODO_TESTE:
        print("** MODO TESTE - E-mails apenas para Gustavo **")

    try:
        conn = conectar()
        print("Conectado ao banco de dados.")
        empresas, veiculos = consultar_veiculos(conn)
        conn.close()
        print(f"Dados obtidos. Empresas: {len(empresas)} | Veiculos ativos: {len(veiculos)}")

        alertas = processar_alertas(veiculos, empresas)

        if not alertas.empty:
            print(f"\n{len(alertas)} empresas atingiram os criterios de alerta:")
            print(alertas[['IDCliente', 'Apelido', 'TotalVeiculos', 'SemReportar', 'PctSemReportar', 'LimitePct']].to_string(index=False))
            enviar_email_alerta(alertas)
        else:
            print("\nNenhuma empresa atingiu os criterios de alerta.")

    except Exception as e:
        print(f"Erro durante a execucao: {e}")
