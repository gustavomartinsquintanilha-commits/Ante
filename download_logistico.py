# -*- coding: utf-8 -*-
"""
download_logistico.py
Automacao: Login -> Ultimas Posicoes -> Exportar XLS
Site: suporte.newsgps.com.br
"""

import os
import sys
import time
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Garante saida UTF-8 no console Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore

# ==========================================================
# CONFIGURACOES
# ==========================================================
URL_LOGIN = "http://suporte.newsgps.com.br/"
USUARIO = "gustavo"
SENHA = "gustavo"

# Diretorio destino do arquivo baixado
DESTINO = Path(r"C:\Users\gusta\OneDrive\Documentos\Codigos\Reporte - Logistico\Base")

# Tempo maximo de espera (segundos)
TIMEOUT_ELEMENTO = 30
TIMEOUT_DOWNLOAD = 60

# Pasta para salvar screenshots de debug
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


# ==========================================================
# FUNCOES
# ==========================================================

def criar_driver(download_dir: str) -> webdriver.Chrome:
    """Cria e retorna uma instancia do Chrome configurada."""
    opts = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
        # Desativa completamente o gerenciador de senhas
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.password_manager_leak_detection": False,
        # Permite downloads inseguros (HTTP)
        "profile.default_content_setting_values.automatic_downloads": 1,
        "profile.default_content_setting_values.insecure_content": 1,
        "download.insecure_content_allowed": True,
        # Desativa TODOS os popups de senha e leak detection
        "profile.password_manager_leak_detection": False,
        "password_manager.leak_detection": False,
        "profile.default_content_setting_values.notifications": 2,
        # Aceita downloads automaticamente sem confirmacao
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_settings.popups": 0,
        "download.extensions_to_open": "xls",
    }
    opts.add_experimental_option("prefs", prefs)
    # Exclui o popup de salvar senha e alertas
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    # Modo headless: ativado via variavel de ambiente HEADLESS=true (usado no GitHub Actions)
    if os.environ.get("HEADLESS", "").lower() == "true":
        opts.add_argument("--headless=new")
        print("[*] Executando em modo HEADLESS")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-features=PasswordLeakDetection,PasswordCheck,InsecureDownloadWarnings,SafeBrowsingEnhancedProtection,DownloadBubble,DownloadBubbleV2")
    opts.add_argument("--disable-save-password-bubble")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--unsafely-treat-insecure-origin-as-secure=http://suporte.newsgps.com.br")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-insecure-localhost")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver


def aguardar_download(download_dir: str, timeout: int = TIMEOUT_DOWNLOAD) -> str:
    """Aguarda ate que um arquivo .xls apareca no diretorio de download."""
    inicio = time.time()
    while True:
        arquivos = os.listdir(download_dir)
        # Procura por .xls que nao seja arquivo temporario do Chrome
        xls_files = [
            f for f in arquivos
            if f.lower().endswith(".xls") and not f.endswith(".crdownload")
        ]
        if xls_files:
            return os.path.join(download_dir, xls_files[0])
        if time.time() - inicio > timeout:
            raise TimeoutError(
                f"Download nao concluido em {timeout}s. "
                f"Arquivos encontrados: {arquivos}"
            )
        time.sleep(1)
    return ""  # type: ignore


def executar():
    """Fluxo principal de automacao."""
    # Cria pasta temporaria para download
    download_tmp = tempfile.mkdtemp(prefix="logistico_dl_")
    print(f"[DIR] Download temporario: {download_tmp}")

    # Garante que o destino existe
    DESTINO.mkdir(parents=True, exist_ok=True)

    driver = None
    try:
        # ----- Inicializa o browser -----
        print("[*] Abrindo navegador...")
        driver = criar_driver(download_tmp)

        # Forca o Chrome a permitir downloads via CDP (contorna bloqueio HTTP)
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": download_tmp,
        })
        driver.execute_cdp_cmd("Browser.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": download_tmp,
        })

        wait = WebDriverWait(driver, TIMEOUT_ELEMENTO)

        # ----- ETAPA 1: LOGIN -----
        print(f"[*] Acessando {URL_LOGIN}")
        driver.get(URL_LOGIN)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "01_pagina_inicial.png"))
        print("[SCREENSHOT] 01_pagina_inicial.png")

        # Re-aplica CDP apos carregar a pagina (necessario em algumas versoes do Chrome)
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": download_tmp,
        })

        # Selecionar "Logistica" no dropdown de empresa
        print("[*] Selecionando servico: Logistica...")
        dropdown_empresa = wait.until(
            EC.presence_of_element_located((By.ID, "ddlEmpresa"))
        )
        select = Select(dropdown_empresa)
        select.select_by_value("Logistica")
        print("[OK] Servico selecionado!")
        driver.save_screenshot(str(SCREENSHOTS_DIR / "02_servico_selecionado.png"))
        print("[SCREENSHOT] 02_servico_selecionado.png")

        # Aguarda a pagina reagir ao postback do dropdown
        time.sleep(2)

        # Preencher usuario
        campo_usuario = wait.until(
            EC.presence_of_element_located((By.ID, "txtLogin"))
        )
        campo_usuario.click()
        campo_usuario.clear()
        campo_usuario.send_keys(USUARIO)

        # Preencher senha
        campo_senha = driver.find_element(By.ID, "txtSenha")
        campo_senha.click()
        campo_senha.clear()
        campo_senha.send_keys(SENHA)

        # Clicar em Entrar (imagem btEntrar.jpg)
        btn_entrar = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "img[src*='btEntrar']")
            )
        )
        btn_entrar.click()
        print("[OK] Login realizado!")
        time.sleep(2)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "03_apos_login.png"))
        print("[SCREENSHOT] 03_apos_login.png")

        # ----- ETAPA 2: ULTIMAS POSICOES -----
        print("[*] Abrindo Ultimas Posicoes...")
        link_posicoes = wait.until(
            EC.element_to_be_clickable((By.ID, "CP_btn01"))
        )
        link_posicoes.click()
        print("[OK] Ultimas Posicoes aberta!")

        # Aguarda a pagina de posicoes carregar
        time.sleep(3)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "04_ultimas_posicoes.png"))
        print("[SCREENSHOT] 04_ultimas_posicoes.png")

        # Verifica se abriu em nova janela/aba
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            print("[->] Alternado para nova janela/aba.")

        # ----- ETAPA 3: EXPORTAR XLS -----
        print("[*] Clicando em Exportar XLS...")
        
        # Tenta fechar qualquer alert/popup antes de clicar
        try:
            alert = driver.switch_to.alert
            alert.dismiss()
            print("[->] Alert fechado.")
        except:
            pass
        
        btn_exportar = wait.until(
            EC.element_to_be_clickable((By.ID, "CP_BtnExportXLS"))
        )
        btn_exportar.click()
        print("[OK] Exportacao iniciada!")
        driver.save_screenshot(str(SCREENSHOTS_DIR / "05_apos_exportar.png"))
        print("[SCREENSHOT] 05_apos_exportar.png")
        
        # Aguarda um pouco e tenta aceitar qualquer confirmacao de download
        time.sleep(2)
        try:
            alert = driver.switch_to.alert
            alert.accept()
            print("[->] Confirmacao de download aceita.")
        except:
            pass

        # ----- ETAPA 4: AGUARDAR DOWNLOAD -----
        print("[*] Aguardando download...")
        arquivo_baixado = aguardar_download(download_tmp)
        print(f"[OK] Download concluido: {os.path.basename(arquivo_baixado)}")

        # ----- ETAPA 5: MOVER E RENOMEAR -----
        agora = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        nome_final = f"Logistico - {agora}.xls"
        caminho_final = DESTINO / nome_final

        shutil.move(arquivo_baixado, str(caminho_final))
        print(f"[OK] Arquivo salvo em: {caminho_final}")

    except Exception as e:
        print(f"[ERRO] {e}")
        raise
    finally:
        if driver:
            driver.quit()
            print("[OK] Navegador fechado.")
        # Limpa pasta temporaria
        try:
            shutil.rmtree(download_tmp, ignore_errors=True)
        except Exception:
            pass


# ==========================================================
# EXECUCAO
# ==========================================================
if __name__ == "__main__":
    print("=" * 60)
    print("DOWNLOAD AUTOMATICO - LOGISTICO (NewsGPS)")
    print("=" * 60)
    executar()
    print("\n[OK] Processo concluido com sucesso!")
