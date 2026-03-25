import os, sys, io, pyodbc, smtplib
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from email.message import EmailMessage

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_CI = os.environ.get("HEADLESS", "").lower() == "true"
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'), override=True)

SMTP_HOST, SMTP_PORT = 'smtp.gmail.com', 465
SMTP_USER = 'veiculosemreportar@gmail.com'
SMTP_PASS = 'svhh lgau okua kkof'
URL_ASSINATURA = "https://drive.google.com/uc?export=view&id=1si56G_we2n1lhOTvuomgFTscogWdxrP9"

DESTINATARIOS = [
    'gustavo.martins@optimuz.com.br', 'marciele@newsgps.com.br',
    'julyana@newsgps.com.br', 'marlos.miranda@newsgps.com.br',
    'renata.braga@newsgps.com.br', 'adriana.florencio@newsgps.com.br',
    'andreia.ribeiro@newsgps.com.br', 'jessica.dias@quadrisystems.com.br',
    'hudson.ferreira@optimuz.com.br', 'gustavo.andrade@quadrisystems.com.br',
    'leandro.gomes@optimuz.com.br', 'joao.peres@optimuz.com.br',
    'adriel.carvalho@newsgps.com.br', 'gabriel.oliveira@quadrisystems.com.br',
]

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

def consultar_dados(conn):
    empresas = pd.read_sql("SET NOCOUNT ON; SELECT ID, Apelido FROM dbo.Com_Empresa", conn)
    viagens = pd.read_sql("""
        SET NOCOUNT ON;
        SELECT g.DataReferencia, g.DataPartidaPrevista, g.DataPartidaReal, g.IDCliente,
               s.DataPartidaPrevista AS DataPartidaPrevista_Servico
        FROM dbo.Ope_GradeOperacao g
        INNER JOIN dbo.Ope_GradeOperacao_Srvp p ON p.IDGradeOperacao = g.ID
        INNER JOIN dbo.Ope_GradeOperacao_Srvp_Servicos s ON s.IDSRVP = p.ID
        WHERE g.DataReferencia >= CAST(DATEADD(DAY, -1, GETDATE()) AS DATE)
          AND g.DataReferencia < CAST(GETDATE() AS DATE)
          AND s.DataPartidaPrevista >= CAST(DATEADD(DAY, -1, GETDATE()) AS DATE)
          AND s.DataPartidaPrevista < CAST(GETDATE() AS DATE)
    """, conn)
    return empresas, viagens

def processar_analise(viagens, empresas):
    if viagens.empty:
        return pd.DataFrame()
    agrupado = viagens.groupby(['DataReferencia', 'IDCliente']).agg(
        Prevista=('DataPartidaPrevista', 'count'),
        Realizada=('DataPartidaReal', 'count')
    ).reset_index()
    agrupado['Pct'] = (agrupado['Realizada'] / agrupado['Prevista'] * 100).round(2)
    resultado = agrupado[agrupado['Pct'] <= 80].copy()
    resultado = resultado.merge(empresas, left_on='IDCliente', right_on='ID', how='left').drop(columns=['ID'])
    return resultado.sort_values(['DataReferencia', 'Pct'])

def enviar_email_resultado(df):
    ontem = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
    if df.empty:
        corpo_html = f"<p>Bom dia,</p><p>Nao foram encontrados clientes com execucao de viagens <b>&lt;= 80%</b> para a data de {ontem}.</p>"
    else:
        linhas = "".join(
            f"<tr><td style='border:1px solid #ddd;padding:8px'>{r['IDCliente']}</td>"
            f"<td style='border:1px solid #ddd;padding:8px'>{r['Apelido']}</td>"
            f"<td style='border:1px solid #ddd;padding:8px;text-align:center'>{r['Prevista']}</td>"
            f"<td style='border:1px solid #ddd;padding:8px;text-align:center'>{r['Realizada']}</td>"
            f"<td style='border:1px solid #ddd;padding:8px;text-align:center;color:red'>{r['Pct']}%</td></tr>"
            for _, r in df.iterrows()
        )
        corpo_html = f"""<p>Bom dia,</p>
        <p>Seguem os clientes com percentual de execucao de viagens <b>menor ou igual a 80%</b> para a data de ontem (D-1): <b>{ontem}</b></p>
        <table style='border-collapse:collapse;width:100%;font-family:Arial,sans-serif'>
        <thead><tr style='background-color:#f2f2f2'>
            <th style='border:1px solid #ddd;padding:8px;text-align:left'>ID Cliente</th>
            <th style='border:1px solid #ddd;padding:8px;text-align:left'>Empresa (Apelido)</th>
            <th style='border:1px solid #ddd;padding:8px'>Previstas</th>
            <th style='border:1px solid #ddd;padding:8px'>Realizadas</th>
            <th style='border:1px solid #ddd;padding:8px'>% Exec</th>
        </tr></thead><tbody>{linhas}</tbody></table>"""

    msg = EmailMessage()
    msg['Subject'] = f"Analise de Execucao de Viagens (D-1) - {ontem}"
    msg['From'], msg['To'] = SMTP_USER, ", ".join(DESTINATARIOS)
    msg.set_content(f"Relatorio de Execucao de Viagens - {ontem}. Verifique a versao HTML.")
    msg.add_alternative(f"<html><body>{corpo_html}<br><p>Atenciosamente,<br>Tryvia</p>"
                        f"<img src='{URL_ASSINATURA}' alt='Assinatura' style='width:200px;height:auto'>"
                        f"</body></html>", subtype='html')
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print("✅ E-mail enviado com sucesso para a equipe interna.")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")

if __name__ == "__main__":
    print(f"Iniciando Analise de Execucao de Viagens - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    try:
        conn = conectar()
        print("Conectado ao banco de dados.")
        empresas, viagens = consultar_dados(conn)
        conn.close()
        print(f"Dados obtidos. Empresas: {len(empresas)} | Viagens: {len(viagens)}")
        resultado = processar_analise(viagens, empresas)
        if not resultado.empty:
            print(f"\nEncontrados {len(resultado)} registros com execucao <= 80%.")
            print(resultado[['IDCliente', 'Apelido', 'Prevista', 'Realizada', 'Pct']].to_string(index=False))
        enviar_email_resultado(resultado)
    except Exception as e:
        print(f"❌ Erro durante a execucao: {e}")
