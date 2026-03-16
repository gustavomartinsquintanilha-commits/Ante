import os
import re
import unicodedata
from email.message import EmailMessage
import smtplib

# ==========================================================
# MODO DE OPERACAO
# ==========================================================
# True  = envia tudo para GUSTAVO (teste)
# False = envia para os destinatarios reais (producao)
MODO_TESTE = True
EMAIL_TESTE = 'gustavo.martins@optimuz.com.br'

# --- Configurações SMTP ---
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 465
SMTP_USER = 'veiculosemreportar@gmail.com'
SMTP_PASS = 'svhh lgau okua kkof'  # Senha de app

# --- Diretório com os arquivos ---
IS_CI = os.environ.get("HEADLESS", "").lower() == "true"
if IS_CI:
    PASTA_ARQUIVOS = os.path.join(os.getcwd(), "relatorios_envio")
else:
    PASTA_ARQUIVOS = r'C:\Users\gusta\OneDrive\Documentos\Codigos\Envio de e-mail - VSR\clientes_para_envio'

# --- Empresas ignoradas (não processar arquivos delas) ---
empresas_ignorar = {'4bts', 'newsgps', 'projeccons'}

# --- Ativar/desativar subgrupos JCA ---
# False = empresas JCA nao serao processadas nem sinalizadas no alerta
ATIVAR_JCA = False

# --- Mapeamento empresa -> destinatário ---
# Em MODO_TESTE todos os e-mails vao para EMAIL_TESTE.
# Descomente os destinatarios reais quando for para producao.
destinatarios = {
    # 'costaverdetransportesltda': 'trafego@costaverdetransportes.com.br, gerenteoperacional@costaverdetransportes.com.br',
    # 'viacaoprogresso': 'emerson.souza@adtsa.com.br',
    # 'autoviacao1001': 'luigy.costa@viacaocometa.com.br, inteligencia.operacional@viacaocometa.com.br',
    # 'catarinense': 'luigy.costa@viacaocometa.com.br, inteligencia.operacional@viacaocometa.com.br, ricardo.alvares@jcatlm.com.br',
    # 'expressodosul': 'luigy.costa@viacaocometa.com.br, inteligencia.operacional@viacaocometa.com.br, ricardo.alvares@jcatlm.com.br',
    # 'rapidoribeirao': 'luigy.costa@viacaocometa.com.br, inteligencia.operacional@viacaocometa.com.br, ricardo.alvares@jcatlm.com.br',
    # 'cometa': 'luigy.costa@viacaocometa.com.br, inteligencia.operacional@viacaocometa.com.br, ricardo.alvares@jcatlm.com.br',
    # 'maruifriburgo': 'edson.neves@autoviacao1001.com.br, thiago.guimaraes@sitmacae.com.br, ricardo.alvares@jcatlm.com.br',
    # '1001log': 'edson.neves@autoviacao1001.com.br, thiago.guimaraes@sitmacae.com.br, ricardo.alvares@jcatlm.com.br',
    # 'opcaojca': 'luigy.costa@viacaocometa.com.br, inteligencia.operacional@viacaocometa.com.br, ricardo.alvares@jcatlm.com.br',
    # 'macaense': 'edson.neves@autoviacao1001.com.br, thiago.guimaraes@sitmacae.com.br, ricardo.alvares@jcatlm.com.br',
    # 'sit': 'edson.neves@autoviacao1001.com.br, thiago.guimaraes@sitmacae.com.br, ricardo.alvares@jcatlm.com.br',
    # 'bonfim': 'gps@vsbonfim.com.br',
    # 'ouronegro': 'operacional@ouronegro.com.br',
    # 'sitiocarvalho': 'marcia@sitiocarvalho.com.br',
    # 'mineirinho': 'pablo.silva@vixex.com.br',
    # 'frossard': 'fernando@frossard.com.br',
    # 'cervejarianoi': 'cervejarianoi@cervejarianoi.com.br',
    # 'lideranca': 'gerencia.operacional@liderancatur.com.br',
    # 'planalto': 'lindolfo.dejesus@planalto.com.br',
    # 'passaroverde': 'jose.silva@passaroverde.com.br, fabiano.silva@passaroverde.com.br, breno.fonseca@passaroverde.com.br, marcos.bezerra@passaroverde.com.br',
    # 'itabira': 'ronald.batista@viacaoitabira.com.br, jessica.oliveira@viacaoitabira.com.br',
    # 'expressovalonia': 'fernanda.siqueira@expressovalonia.com.br, julio.cesar@expressovalonia.com.br, jose.romeu@expressovalonia.com.br',
    # 'turi': 'jose.silva@turi.com.br, telemetria.pm@turi.com.br',
    # 'riouruguai': 'fabianoriouruguai@gmail.com',
    # 'destigo': 'comercial@destigo.com.br',

    # --- MODO TESTE: todas as empresas apontam para Gustavo ---
    'costaverdetransportesltda': EMAIL_TESTE,
    'viacaoprogresso': EMAIL_TESTE,
    'autoviacao1001': EMAIL_TESTE,
    'catarinense': EMAIL_TESTE,
    'expressodosul': EMAIL_TESTE,
    'rapidoribeirao': EMAIL_TESTE,
    'cometa': EMAIL_TESTE,
    'maruifriburgo': EMAIL_TESTE,
    '1001log': EMAIL_TESTE,
    'opcaojca': EMAIL_TESTE,
    'macaense': EMAIL_TESTE,
    'sit': EMAIL_TESTE,
    'bonfim': EMAIL_TESTE,
    'ouronegro': EMAIL_TESTE,
    'sitiocarvalho': EMAIL_TESTE,
    'mineirinho': EMAIL_TESTE,
    'frossard': EMAIL_TESTE,
    'cervejarianoi': EMAIL_TESTE,
    'lideranca': EMAIL_TESTE,
    'planalto': EMAIL_TESTE,
    'passaroverde': EMAIL_TESTE,
    'itabira': EMAIL_TESTE,
    'expressovalonia': EMAIL_TESTE,
    'turi': EMAIL_TESTE,
    'riouruguai': EMAIL_TESTE,
    'destigo': EMAIL_TESTE,
}

# --- CC ---
EMAIL_CC_PRODUCAO = 'marciele@newsgps.com.br, julyana@newsgps.com.br, marlos.miranda@newsgps.com.br, renata.braga@newsgps.com.br, adriana.florencio@newsgps.com.br, andreia.ribeiro@newsgps.com.br, jessica.dias@quadrisystems.com.br, gustavo.martins@optimuz.com.br, hudson.ferreira@optimuz.com.br, gustavo.andrade@quadrisystems.com.br, leandro.gomes@optimuz.com.br, joao.peres@optimuz.com.br'
EMAIL_CC = '' if MODO_TESTE else EMAIL_CC_PRODUCAO

# --- Mapeamento de aliases ---
empresa_aliases = {
    'telemetrialiderancaturismo': 'lideranca', 'telemetriaplanalto': 'planalto',
    'telemetriapassaroverde': 'passaroverde',
    'telemetriaviacaoprogresso': 'viacaoprogresso', 'costaverde': 'costaverdetransportesltda',
    'marui1001': 'maruifriburgo',
    'maruifriburgo': 'maruifriburgo',
    'maruifriburgo1001': 'maruifriburgo',
    'opcao': 'opcaojca', 'senhordobonfim': 'bonfim', 'expressodosul': 'expressodosul',
    'ouronegro': 'ouronegro', 'sitiocarvalho': 'sitiocarvalho', 'v1001': 'autoviacao1001',
    'viacaoprogresso': 'viacaoprogresso', 'mineirinho': 'mineirinho', 'lideranca': 'lideranca',
    'passaroverde': 'passaroverde',
    'esxriodasoistras': 'ouronegro', 'rapido': 'rapidoribeirao', 'progresso': 'viacaoprogresso', 'expresso': 'expressodosul',
    'passaro': 'passaroverde', 'liderancaturismo': 'lideranca',
    '1001log': '1001log',
    'itabira': 'itabira', 'viacaoitabira': 'itabira', 'viacao_itabira': 'itabira',
    'expressovalonia': 'expressovalonia', 'valonia': 'expressovalonia',
    'turi': 'turi',
    'riouruguai': 'riouruguai', 'uruguai': 'riouruguai',
    'destigo': 'destigo',
}

# --- Subgrupos JCA (usados somente quando ATIVAR_JCA = True) ---
subgrupo_1 = {'sit', 'macaense', 'maruifriburgo', '1001log'}
subgrupo_2 = {'autoviacao1001', 'catarinense', 'expressodosul', 'rapidoribeirao', 'cometa', 'opcaojca'}
todas_empresas_jca = subgrupo_1 | subgrupo_2

# --- URL da assinatura ---
URL_ASSINATURA = "https://drive.google.com/uc?export=view&id=1si56G_we2n1lhOTvuomgFTscogWdxrP9"


# ==========================================================
# FUNCOES
# ==========================================================

def enviar_email(destinatario, corpo, anexos, assunto):
    """Envia e-mail em HTML com anexos."""
    msg = EmailMessage()
    msg['Subject'] = assunto
    msg['From'] = SMTP_USER
    msg['To'] = destinatario
    if EMAIL_CC:
        msg['Cc'] = EMAIL_CC

    msg.set_content(corpo)

    paragrafos = corpo.split('\n\n')
    corpo_html_partes = [f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragrafos if p.strip()]
    corpo_html_corpo = "".join(corpo_html_partes)

    corpo_final_html = f"""
    <html>
    <body>
        {corpo_html_corpo}
        <br>
        <p>Atenciosamente,<br>
        Tryvia</p>
        <img src="{URL_ASSINATURA}" alt="Assinatura" style="width:200px;height:auto;">
    </body>
    </html>
    """
    msg.add_alternative(corpo_final_html, subtype='html')

    for caminho in anexos:
        try:
            with open(caminho, 'rb') as f:
                data = f.read()
                nome_arquivo = os.path.basename(caminho)
                msg.add_attachment(data, maintype='application', subtype='octet-stream', filename=nome_arquivo)
        except Exception as e:
            print(f"Erro ao anexar arquivo {caminho}: {e}")

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"  ✅ E-mail enviado para {destinatario}" + (f" com CC para {EMAIL_CC}" if EMAIL_CC else ""))
    except Exception as e:
        print(f"  ❌ Erro ao enviar email: {e}")


def enviar_email_alerta(empresas_sem_arquivo, empresas_sem_cadastro):
    """Envia e-mail de alerta sobre inconsistencias encontradas."""
    destinatario = EMAIL_TESTE if MODO_TESTE else EMAIL_CC_PRODUCAO

    corpo = "Prezados,\n\n"
    corpo += "Este é um alerta automático do sistema de envio de relatórios VSR.\n"
    corpo += "Foram identificadas inconsistências que impediram o envio de alguns e-mails:\n"

    if empresas_sem_arquivo:
        corpo += "\n\n📁 EMPRESAS CADASTRADAS NO SISTEMA, MAS SEM ARQUIVO NA PASTA:\n"
        corpo += "(Estas empresas possuem destinatários configurados, porém nenhum relatório foi gerado)\n"
        for empresa in sorted(empresas_sem_arquivo):
            corpo += f"\n   - {empresa}"

    if empresas_sem_cadastro:
        corpo += "\n\n📋 ARQUIVOS ENCONTRADOS, MAS SEM CADASTRO NO SISTEMA:\n"
        corpo += "(Foram encontrados relatórios para estas empresas, mas não há destinatários configurados)\n"
        for empresa in sorted(empresas_sem_cadastro):
            corpo += f"\n   - {empresa}"

    corpo += "\n\nPor favor, verifique e atualize o cadastro conforme necessário."

    print("\n📨 Enviando e-mail de alerta de inconsistências...")
    enviar_email(destinatario, corpo, [], "ATENÇÃO VSR - E-MAILS NÃO ENVIADOS")


def enviar_email_parabens(empresa_raw, empresa_chave, sistema):
    """Envia e-mail parabenizando empresa com 0 veiculos sem reportar."""
    destinatario = destinatarios.get(empresa_chave, EMAIL_TESTE)

    corpo = f"""Prezados,

Este comunicado é enviado de forma automatizada com o objetivo de apoiar o monitoramento operacional dos veículos integrados ao sistema.

Gostaríamos de parabenizar a {empresa_raw.replace('_', ' ')} por não possuir nenhum veículo sem envio de informações no sistema.

Este resultado reflete o comprometimento da equipe com a manutenção e o bom funcionamento dos equipamentos.

Continuem com o excelente trabalho!"""

    assunto = f"Parabéns - {empresa_raw.replace('_', ' ')} sem veículos sem reportar"
    print(f"  🎉 Enviando parabéns para {empresa_raw.replace('_', ' ')} ({sistema})...")
    enviar_email(destinatario, corpo, [], assunto)


def enviar_email_sucesso(arquivos_por_empresa, empresas_zero_veiculos):
    """Envia e-mail interno de confirmação quando todos os envios foram bem-sucedidos."""
    destinatario = EMAIL_TESTE if MODO_TESTE else EMAIL_CC_PRODUCAO

    # Agrupa empresas por sistema
    sistemas = {}
    for empresa_chave, dados in arquivos_por_empresa.items():
        nome = dados['empresa_raw'].replace('_', ' ')
        for r in dados['relatorios']:
            sistema = r['sistema']
            qtd = r['qtd']
            sistemas.setdefault(sistema, []).append({'nome': nome, 'qtd': qtd})

    # Adiciona empresas com 0 veículos ao agrupamento
    for info in empresas_zero_veiculos:
        nome = info['empresa_raw'].replace('_', ' ')
        sistema = info['sistema']
        sistemas.setdefault(sistema, []).append({'nome': nome, 'qtd': '0'})

    # Ordena as empresas dentro de cada sistema pelo nome
    for sistema in sistemas:
        # Usamos um dicionário para remover duplicatas (caso haja) mantendo o último valor de qtd lido para aquela empresa
        empresas_unicas = {e['nome']: e for e in sistemas[sistema]}.values()
        sistemas[sistema] = sorted(empresas_unicas, key=lambda x: x['nome'])

    corpo = "Prezados,\n\n"
    corpo += "Informamos que todos os envios de relatórios VSR foram realizados com sucesso.\n"
    corpo += "Não foram identificadas inconsistências no processo.\n"
    corpo += "\n📊 RESUMO DOS ENVIOS POR SISTEMA:\n"

    for sistema, empresas in sorted(sistemas.items()):
        corpo += f"\n🔹 {sistema}:\n"
        for empresa_info in empresas:
            corpo += f"   - {empresa_info['nome']} - {empresa_info['qtd']} Veículo(s)\n"

    if empresas_zero_veiculos:
        corpo += "\n🎉 EMPRESAS COM 0 VEÍCULOS SEM REPORTAR (PARABÉNS):\n"
        for info in empresas_zero_veiculos:
            corpo += f"   - {info['empresa_raw'].replace('_', ' ')} ({info['sistema']})\n"

    corpo += "\nCaso esteja faltando alguma empresa no envio de veículos sem reportar, favor informar para que seja acrescentada."

    print("\n📨 Enviando e-mail de confirmação de sucesso...")
    enviar_email(destinatario, corpo, [], "✅ VSR - Todos os envios realizados com sucesso")


# ==========================================================
# FUNCAO PRINCIPAL
# ==========================================================

def main():
    print("\n" + "=" * 60)
    print("📧 ENVIO AUTOMÁTICO DE RELATÓRIOS VSR")
    if MODO_TESTE:
        print("⚠️  MODO TESTE - Todos os e-mails serão enviados para:", EMAIL_TESTE)
    print("=" * 60)

    arquivos = os.listdir(PASTA_ARQUIVOS)
    arquivos_por_empresa = {}
    empresas_nao_localizadas = []
    empresas_com_arquivo = set()       # empresas que tiveram arquivo encontrado
    empresas_zero_veiculos = []        # empresas com 0 veiculos sem reportar

    for arquivo in arquivos:
        caminho = os.path.join(PASTA_ARQUIVOS, arquivo)
        if not os.path.isfile(caminho) or arquivo.startswith('~$') or arquivo.startswith('01') or arquivo.lower() == 'geral.xlsx':
            continue

        nome_normalizado = unicodedata.normalize('NFKD', arquivo).encode('ASCII', 'ignore').decode('ASCII').lower()
        if any(x in nome_normalizado for x in empresas_ignorar):
            print(f"Ignorando arquivo de empresa ignorada: {arquivo}")
            continue

        match_telemetria = re.match(r'Telemetria_(.+?)_VSR(\d+)_.*\.xlsx$', arquivo, re.IGNORECASE)
        match_sing = re.match(r'(.+?)_SING_VSR_?(\d+)_.*\.xlsx$', arquivo, re.IGNORECASE)
        match_logistico = re.match(r'(.+?)_Logistico_VSR(\d+)_.*\.xlsx$', arquivo, re.IGNORECASE)
        match_global = re.match(r'(.+?)_Global_VSR(\d+)_.*\.xlsx$', arquivo, re.IGNORECASE)
        match_padrao = re.match(r'Telemetria_(.+)_(\d+)\.xlsx$', arquivo, re.IGNORECASE)

        match = match_telemetria or match_sing or match_logistico or match_global or match_padrao

        if not match:
            match_generico = re.match(r'(.+?)_VSR_?(\d+)_.*\.xlsx$', arquivo, re.IGNORECASE)
            if not match_generico:
                match_generico = re.match(r'(.+?)_(\d+)\.xlsx$', arquivo, re.IGNORECASE)

            if not match_generico:
                 print(f"Arquivo '{arquivo}' não reconhecido.")
                 continue
            match = match_generico

        sistema_raw = "N/A"
        if match_telemetria:
            empresa_raw, qtd = match.groups()
            sistema_raw = "Telemetria"
        elif match_sing:
            empresa_raw, qtd = match.groups()
            sistema_raw = "SING"
        elif match_logistico:
            empresa_raw, qtd = match.groups()
            sistema_raw = "Logístico"
        elif match_global:
            empresa_raw, qtd = match.groups()
            sistema_raw = "Global"
        elif match_padrao:
            empresa_raw, qtd = match.groups()
            sistema_raw = "Telemetria"
        else:
             empresa_raw, qtd = match.groups()
             if 'telemetria' in arquivo.lower(): sistema_raw = "Telemetria"
             elif 'sing' in arquivo.lower(): sistema_raw = "SING"
             elif 'logistico' in arquivo.lower(): sistema_raw = "Logístico"
             elif 'global' in arquivo.lower(): sistema_raw = "Global"

        empresa_norm = unicodedata.normalize('NFKD', empresa_raw).encode('ASCII', 'ignore').decode('ASCII').lower()
        empresa_norm = re.sub(r'[^a-zA-Z0-9]', '', empresa_norm)
        empresa_chave = empresa_aliases.get(empresa_norm, empresa_norm)

        # Pula empresas JCA se o grupo estiver desativado
        if not ATIVAR_JCA and empresa_chave in todas_empresas_jca:
            print(f"Ignorando empresa JCA (desativado): {empresa_raw}")
            continue

        # Verifica se a empresa tem cadastro
        if empresa_chave not in destinatarios:
            if empresa_norm not in empresas_ignorar:
                empresas_nao_localizadas.append(empresa_raw)
            else:
                print(f"Ignorando empresa na lista de ignorar: {empresa_raw}")
            continue

        empresas_com_arquivo.add(empresa_chave)

        # Verifica se tem 0 veiculos sem reportar -> parabenizar
        if qtd == '0':
            empresas_zero_veiculos.append({
                'empresa_raw': empresa_raw,
                'empresa_chave': empresa_chave,
                'sistema': sistema_raw,
            })
            continue  # Nao adiciona aos relatorios de problema

        if empresa_chave not in arquivos_por_empresa:
            arquivos_por_empresa[empresa_chave] = {
                'empresa_raw': empresa_raw,
                'relatorios': []
            }

        arquivos_por_empresa[empresa_chave]['relatorios'].append({
            'qtd': qtd,
            'sistema': sistema_raw,
            'caminho': caminho
        })

    # --- Deteccao de inconsistencias ---
    todas_empresas_cadastradas = set(destinatarios.keys()) - empresas_ignorar
    # Exclui empresas JCA da deteccao quando o grupo esta desativado
    if not ATIVAR_JCA:
        todas_empresas_cadastradas -= todas_empresas_jca
    empresas_sem_arquivo = todas_empresas_cadastradas - empresas_com_arquivo - {
        e['empresa_chave'] for e in empresas_zero_veiculos
    }

    # --- Exibição no terminal ---
    print("\n--- Relatórios para Envio ---")

    if ATIVAR_JCA:
        para_enviar_jca1 = {empresa: dados for empresa, dados in arquivos_por_empresa.items() if empresa in subgrupo_1}
        para_enviar_jca2 = {empresa: dados for empresa, dados in arquivos_por_empresa.items() if empresa in subgrupo_2}
        para_enviar_individuais = {empresa: dados for empresa, dados in arquivos_por_empresa.items() if empresa not in subgrupo_1 and empresa not in subgrupo_2}
    else:
        para_enviar_jca1 = {}
        para_enviar_jca2 = {}
        para_enviar_individuais = dict(arquivos_por_empresa)

    print("\nEmpresas do Subgrupo JCA 1:")
    if not para_enviar_jca1:
        print("   Nenhuma.")
    else:
        destinatario = destinatarios.get(str(list(para_enviar_jca1.keys())[0]))
        print(f"   - E-mail para: {destinatario}")
        for empresa_chave, dados in para_enviar_jca1.items():
            qtds = ", ".join([f"{r['qtd']} ({r['sistema']})" for r in dados['relatorios']])
            print(f"     - {dados['empresa_raw'].replace('_', ' ')}: {qtds}")
            for relatorio in dados['relatorios']:
                nome_arquivo = os.path.basename(relatorio['caminho'])
                print(f"       - Anexo: {nome_arquivo}")

    print("\nEmpresas do Subgrupo JCA 2:")
    if not para_enviar_jca2:
        print("   Nenhuma.")
    else:
        destinatario = destinatarios.get(str(list(para_enviar_jca2.keys())[0]))
        print(f"   - E-mail para: {destinatario}")
        for empresa_chave, dados in para_enviar_jca2.items():
            qtds = ", ".join([f"{r['qtd']} ({r['sistema']})" for r in dados['relatorios']])
            print(f"     - {dados['empresa_raw'].replace('_', ' ')}: {qtds}")
            for relatorio in dados['relatorios']:
                nome_arquivo = os.path.basename(relatorio['caminho'])
                print(f"       - Anexo: {nome_arquivo}")

    print("\nEmpresas com Relatórios Individuais:")
    if not para_enviar_individuais:
        print("   Nenhuma.")
    else:
        for empresa_chave, dados in para_enviar_individuais.items():
            destinatario = destinatarios.get(str(empresa_chave))
            print(f"   - {dados['empresa_raw'].replace('_', ' ')}")
            print(f"     E-mail para: {destinatario}")
            for relatorio in dados['relatorios']:
                nome_arquivo = os.path.basename(relatorio['caminho'])
                print(f"       - Relatório: {relatorio['qtd']} carros (Sistema: {relatorio['sistema']})")
                print(f"       - Anexo: {nome_arquivo}")
            print()

    if empresas_zero_veiculos:
        print("\n🎉 Empresas com 0 veículos sem reportar (receberão parabéns):")
        for info in empresas_zero_veiculos:
            print(f"   - {info['empresa_raw'].replace('_', ' ')} ({info['sistema']})")

    if empresas_sem_arquivo:
        print("\n⚠️  Empresas cadastradas SEM arquivo na pasta:")
        for empresa in sorted(empresas_sem_arquivo):
            print(f"   - {empresa}")

    if empresas_nao_localizadas:
        print("\n⚠️  Arquivos com empresas SEM cadastro no sistema:")
        for empresa in empresas_nao_localizadas:
            print(f"   - {empresa}")

    # ==========================================================
    # ENVIO AUTOMATICO
    # ==========================================================
    print("\n" + "=" * 60)
    print("📤 INICIANDO ENVIO DOS E-MAILS...")
    print("=" * 60)

    # --- E-mails JCA Subgrupo 1 ---
    if para_enviar_jca1:
        corpo = "Prezados, boa tarde a todos!\n\n"
        corpo += "Atualmente estamos com a seguinte listagem de veículos sem reportar nos sistemas:\n"
        anexos_jca1 = []
        for empresa_chave, dados in para_enviar_jca1.items():
            qtds = ", ".join([f"{r['qtd']} carros no sistema {r['sistema']}" for r in dados['relatorios']])
            corpo += f"\n- {dados['empresa_raw'].replace('_', ' ')}: {qtds}"
            anexos_jca1.extend([r['caminho'] for r in dados['relatorios']])

        corpo += "\n\nGostaríamos de entender quais medidas serão adotadas para corrigir essa situação e reforço que estamos à disposição para prestar assistência, caso necessário."

        destinatario_jca1 = destinatarios.get(str(list(para_enviar_jca1.keys())[0]))
        print("\n📨 Enviando e-mail JCA Subgrupo 1 (Urbano)...")
        enviar_email(destinatario_jca1, corpo, anexos_jca1, "Relatório veículos sem reportar - Grupo JCA (Urbano)")

    # --- E-mails JCA Subgrupo 2 ---
    if para_enviar_jca2:
        corpo = "Prezados, boa tarde a todos!\n\n"
        corpo += "Atualmente estamos com a seguinte listagem de veículos sem reportar nos sistemas:\n"
        anexos_jca2 = []
        for empresa_chave, dados in para_enviar_jca2.items():
            empresa_formatada = dados['empresa_raw'].replace('_', ' ')
            corpo += f"\n\n- {empresa_formatada}:"

            relatorios_empresa = dados['relatorios']
            for relatorio in relatorios_empresa:
                qtd = relatorio['qtd']
                sistema = relatorio['sistema']
                corpo += f"\n   - {qtd} carros sem reportar no sistema {sistema}."
                anexos_jca2.append(relatorio['caminho'])

        corpo += "\n\nGostaríamos de entender quais medidas serão adotadas para corrigir essa situação e reforço que estamos à disposição para prestar assistência, caso necessário."

        destinatario_jca2 = destinatarios.get(str(list(para_enviar_jca2.keys())[0]))
        print("\n📨 Enviando e-mail JCA Subgrupo 2 (Rodoviário)...")
        enviar_email(destinatario_jca2, corpo, anexos_jca2, "Relatório veículos sem reportar - Grupo JCA (Rodoviario)")

    # --- E-mails individuais ---
    for empresa_chave, dados in para_enviar_individuais.items():
        relatorios = dados['relatorios']
        anexos = [r['caminho'] for r in relatorios]
        destinatario = destinatarios.get(str(empresa_chave))
        empresa_raw = dados['empresa_raw']

        if len(relatorios) > 1:
            corpo = f"""Prezados,

Este comunicado é enviado de forma automatizada com o objetivo de apoiar o monitoramento operacional dos veículos integrados ao sistema.

Identificamos atualmente:
"""
            for relatorio in relatorios:
                corpo += f"   - {relatorio['qtd']} veículos sem envio de informações há mais de 2 dias no sistema {relatorio['sistema']}.\n"

            corpo += f"""
Conforme relação apresentada no(s) anexo(s).

Esse alerta tem como finalidade permitir a verificação da situação desses veículos, como por exemplo: parada operacional, manutenção, veículos fora de operação ou eventual necessidade de intervenção técnica.

Caso a verificação indique necessidade de suporte técnico, nossa equipe permanece à disposição para apoiar nas análises e orientações necessárias.
"""
            assunto = f"Relatório veículos sem reportar - {empresa_raw.replace('_', ' ')} (SING/TELEMETRIA)"
            print(f"\n📨 Enviando e-mail para {empresa_raw.replace('_', ' ')}...")
            enviar_email(destinatario, corpo, anexos, assunto)
        else:
            relatorio_unico = relatorios[0]
            sistema = unicodedata.normalize('NFKD', relatorio_unico['sistema']).encode('ASCII', 'ignore').decode('ASCII')
            corpo = f"""Prezados,

Este comunicado é enviado de forma automatizada com o objetivo de apoiar o monitoramento operacional dos veículos integrados ao sistema.

Identificamos atualmente {relatorio_unico['qtd']} veículos sem envio de informações há mais de 2 dias no sistema {sistema}, conforme relação apresentada no anexo.

Esse alerta tem como finalidade permitir a verificação da situação desses veículos, como por exemplo: parada operacional, manutenção, veículos fora de operação ou eventual necessidade de intervenção técnica.

Caso a verificação indique necessidade de suporte técnico, nossa equipe permanece à disposição para apoiar nas análises e orientações necessárias.
"""
            assunto = f"Relatório veículos sem reportar - {empresa_raw.replace('_', ' ')} ({sistema})"
            print(f"\n📨 Enviando e-mail para {empresa_raw.replace('_', ' ')}...")
            enviar_email(destinatario, corpo, anexos, assunto)

    # --- E-mails de parabéns (0 veiculos) ---
    if empresas_zero_veiculos:
        print("\n" + "-" * 40)
        print("🎉 ENVIANDO E-MAILS DE PARABÉNS...")
        print("-" * 40)
        for info in empresas_zero_veiculos:
            enviar_email_parabens(info['empresa_raw'], info['empresa_chave'], info['sistema'])

    # --- E-mail de alerta de inconsistencias ou confirmação de sucesso ---
    if empresas_sem_arquivo or empresas_nao_localizadas:
        print("\n" + "-" * 40)
        print("⚠️  ENVIANDO ALERTA DE INCONSISTÊNCIAS...")
        print("-" * 40)
        enviar_email_alerta(empresas_sem_arquivo, set(empresas_nao_localizadas))
    else:
        print("\n" + "-" * 40)
        print("✅ NENHUMA INCONSISTÊNCIA - ENVIANDO CONFIRMAÇÃO...")
        print("-" * 40)
        enviar_email_sucesso(arquivos_por_empresa, empresas_zero_veiculos)

    print("\n" + "=" * 60)
    print("✅ PROCESSO DE ENVIO CONCLUÍDO!")
    print("=" * 60)


# --- Execução ---
if __name__ == '__main__':
    main()