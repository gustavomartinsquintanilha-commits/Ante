import os, sys, io
import pyodbc
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage

# Forcar UTF-8 no console Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configuracoes
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_CI = os.environ.get("HEADLESS", "").lower() == "true"
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'), override=True)

# Configuracoes de Email (reutilizadas do enviar_email.py)
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 465
SMTP_USER = 'veiculosemreportar@gmail.com'
SMTP_PASS = 'svhh lgau okua kkof'  # Senha de app
URL_ASSINATURA = "https://drive.google.com/uc?export=view&id=1si56G_we2n1lhOTvuomgFTscogWdxrP9"

# Destinatarios (Equipe Interna)
DESTINATARIOS = [
    'marciele@newsgps.com.br', 'julyana@newsgps.com.br', 'marlos.miranda@newsgps.com.br',
    'renata.braga@newsgps.com.br', 'adriana.florencio@newsgps.com.br', 'andreia.ribeiro@newsgps.com.br',
    'jessica.dias@quadrisystems.com.br', 'gustavo.martins@optimuz.com.br', 'hudson.ferreira@optimuz.com.br',
    'gustavo.andrade@quadrisystems.com.br', 'leandro.gomes@optimuz.com.br', 'joao.peres@optimuz.com.br'
]

def conectar():
    """Conecta ao banco NGAdmin usando credenciais do .env."""
    server   = os.getenv('DB_SERVER')
    database = os.getenv('DB_DATABASE')
    username = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')
    driver   = os.getenv('DB_DRIVER')
    
    if IS_CI and driver and '17' in driver:
        driver = '{ODBC Driver 18 for SQL Server}'

    conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    if IS_CI:
        conn_str += ';TrustServerCertificate=yes;Encrypt=yes'
    return pyodbc.connect(conn_str)

def consultar_dados(conn):
    """Busca empresas e viagens com data dinamica (hoje)."""
    # Consulta todas as empresas para o De/Para de Apelido
    empresas = pd.read_sql("SET NOCOUNT ON; SELECT ID, Apelido FROM dbo.Com_Empresa", conn)

    # Consulta viagens do dia anterior (data dinamica D-1)
    viagens = pd.read_sql("""
        SET NOCOUNT ON;
        SELECT DataReferencia, DataPartidaPrevista, DataPartidaReal, IDCliente
        FROM dbo.Ope_GradeOperacao
        WHERE DataReferencia >= CAST(DATEADD(DAY, -1, GETDATE()) AS DATE)
          AND DataReferencia < CAST(GETDATE() AS DATE)
          AND (isCancelado = 0 OR isCancelado IS NULL)
    """, conn)

    return empresas, viagens

def processar_analise(viagens, empresas):
    """Calcula percentual de execucao e filtra resultados <= 80%."""
    if viagens.empty:
        return pd.DataFrame()

    agrupado = viagens.groupby(['DataReferencia', 'IDCliente']).agg(
        Prevista=('DataPartidaPrevista', 'count'),
        Realizada=('DataPartidaReal', 'count')
    ).reset_index()

    agrupado['Pct'] = (agrupado['Realizada'] / agrupado['Prevista'] * 100).round(2)

    # Filtro solicitado: apenas execucao <= 80%
    resultado = agrupado[agrupado['Pct'] <= 80].copy()
    resultado = resultado.merge(empresas, left_on='IDCliente', right_on='ID', how='left').drop(columns=['ID'])
    return resultado.sort_values(['DataReferencia', 'Pct'])

def enviar_email_resultado(df):
    """Gera tabela HTML e envia por e-mail para a equipe interna."""
    # Data de ontem (D-1) para o relatorio
    ontem = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
    
    if df.empty:
        corpo_txt = f"Bom dia,\n\nNao foram encontrados clientes com execucao de viagens <= 80% para a data de {ontem}."
        corpo_html = f"<p>Bom dia,</p><p>Nao foram encontrados clientes com execucao de viagens <b><= 80%</b> para a data de {ontem}.</p>"
    else:
        # Constroi tabela HTML
        linhas_tabela = ""
        for _, r in df.iterrows():
            linhas_tabela += f"""
            <tr>
                <td style='border: 1px solid #ddd; padding: 8px;'>{r['IDCliente']}</td>
                <td style='border: 1px solid #ddd; padding: 8px;'>{r['Apelido']}</td>
                <td style='border: 1px solid #ddd; padding: 8px; text-align: center;'>{r['Prevista']}</td>
                <td style='border: 1px solid #ddd; padding: 8px; text-align: center;'>{r['Realizada']}</td>
                <td style='border: 1px solid #ddd; padding: 8px; text-align: center; color: red;'>{r['Pct']}%</td>
            </tr>
            """
        
        corpo_txt = f"Relatorio de Execucao de Viagens - {ontem}. Verifique a versao HTML para detalhes."
        corpo_html = f"""
        <p>Bom dia,</p>
        <p>Seguem os clientes com percentual de execucao de viagens <b>menor ou igual a 80%</b> para a data de ontem (D-1): <b>{ontem}</b></p>
        <table style='border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;'>
            <thead>
                <tr style='background-color: #f2f2f2;'>
                    <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>ID Cliente</th>
                    <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Empresa (Apelido)</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>Previstas</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>Realizadas</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>% Exec</th>
                </tr>
            </thead>
            <tbody>
                {linhas_tabela}
            </tbody>
        </table>
        """

    msg = EmailMessage()
    msg['Subject'] = f"Analise de Execucao de Viagens (D-1) - {ontem}"
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(DESTINATARIOS)
    
    msg.set_content(corpo_txt)
    
    corpo_final_html = f"""
    <html>
    <body>
        {corpo_html}
        <br>
        <p>Atenciosamente,<br>Tryvia</p>
        <img src="{URL_ASSINATURA}" alt="Assinatura" style="width:200px;height:auto;">
    </body>
    </html>
    """
    msg.add_alternative(corpo_final_html, subtype='html')

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"✅ E-mail enviado com sucesso para a equipe interna.")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")

if __name__ == "__main__":
    hoje = datetime.now().strftime('%d/%m/%Y %H:%M')
    print(f"Iniciando Analise de Execucao de Viagens - {hoje}")
    
    try:
        conn = conectar()
        print("Conectado ao banco de dados.")
        
        empresas, viagens = consultar_dados(conn)
        conn.close()
        print(f"Dados obtidos. Empresas: {len(empresas)} | Viagens hoje: {len(viagens)}")
        
        resultado = processar_analise(viagens, empresas)
        
        # Exibe no console para debug
        if not resultado.empty:
            print(f"\nEncontrados {len(resultado)} registros com execucao <= 80%.")
            print(resultado[['IDCliente', 'Apelido', 'Prevista', 'Realizada', 'Pct']].to_string(index=False))
        
        # Envia e-mail
        enviar_email_resultado(resultado)
        
    except Exception as e:
        print(f"❌ Erro durante a execucao: {e}")
