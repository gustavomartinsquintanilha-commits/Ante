# -*- coding: utf-8 -*-
"""
download_posicoes.py
Automacao: Login -> Ultimas Posicoes -> Exportar XLS
Site: bus.systemsatx.com.br
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Garante saida UTF-8 no console Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore

# ==========================================================
# CONFIGURACOES
# ==========================================================
URL_LOGIN = "https://bus.systemsatx.com.br/Default.aspx?IdConfig=18"
USUARIO = "julyana"
SENHA = "julyana"

# Diretorio destino do arquivo baixado
IS_CI = os.environ.get("HEADLESS", "").lower() == "true"
if IS_CI:
    DESTINO = Path(os.getcwd()) / "output"
else:
    DESTINO = Path(r"C:\Users\gusta\OneDrive\Documentos\Codigos\Reporte - Logistico\Base")

# Tempo maximo de espera (segundos)
TIMEOUT_ELEMENTO = 30
TIMEOUT_DOWNLOAD = 60

# Pasta para salvar screenshots de debug
SCREENSHOTS_DIR = Path(os.getcwd()) / "screenshots"
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
    }
    opts.add_experimental_option("prefs", prefs)
    # Modo headless via variavel de ambiente
    if IS_CI:
        opts.add_argument("--headless=new")
        print("[*] Executando em modo HEADLESS", flush=True)
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")

    # No CI usa chromedriver do sistema, local usa webdriver_manager
    if IS_CI:
        driver = webdriver.Chrome(options=opts)
    else:
        from webdriver_manager.chrome import ChromeDriverManager
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
    download_tmp = tempfile.mkdtemp(prefix="posicoes_dl_")
    print(f"[DIR] Download temporario: {download_tmp}", flush=True)

    # Garante que o destino existe
    DESTINO.mkdir(parents=True, exist_ok=True)

    driver = None
    try:
        # ----- Inicializa o browser -----
        print("[*] Abrindo navegador...", flush=True)
        driver = criar_driver(download_tmp)
        driver.set_page_load_timeout(30)
        wait = WebDriverWait(driver, TIMEOUT_ELEMENTO)

        # ----- ETAPA 1: LOGIN -----
        print(f"[*] Acessando {URL_LOGIN}", flush=True)
        try:
            driver.get(URL_LOGIN)
        except Exception as e:
            print(f"[WARN] Timeout no page load: {e}", flush=True)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "posicoes_01_login.png"))
        print("[SCREENSHOT] posicoes_01_login.png", flush=True)

        campo_usuario = wait.until(
            EC.presence_of_element_located((By.ID, "txtLogin"))
        )
        campo_usuario.clear()
        campo_usuario.send_keys(USUARIO)

        campo_senha = driver.find_element(By.ID, "txtSenha")
        campo_senha.clear()
        campo_senha.send_keys(SENHA)

        btn_entrar = driver.find_element(By.ID, "btnLogin")
        btn_entrar.click()
        print("[OK] Login realizado!", flush=True)
        time.sleep(3)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "posicoes_02_apos_login.png"))
        print("[SCREENSHOT] posicoes_02_apos_login.png", flush=True)

        # ----- ETAPA 2: ULTIMAS POSICOES -----
        print("[*] Abrindo Ultimas Posicoes...", flush=True)
        link_posicoes = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@onclick,'AbreUltimasPosicoes')]")
            )
        )
        link_posicoes.click()
        print("[OK] Ultimas Posicoes aberta!", flush=True)

        # Aguarda a pagina de posicoes carregar
        time.sleep(3)

        # Verifica se abriu em nova janela/aba
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            print("[->] Alternado para nova janela/aba.")

        # ----- ETAPA 3: EXPORTAR XLS -----
        print("[*] Clicando em Exportar XLS...", flush=True)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "posicoes_03_ultimas_posicoes.png"))
        btn_exportar = wait.until(
            EC.element_to_be_clickable(
                (By.ID, "ctl00_ContentPlaceHolderPortal_btnExportXLS")
            )
        )
        btn_exportar.click()
        print("[OK] Exportacao iniciada!", flush=True)

        # ----- ETAPA 4: AGUARDAR DOWNLOAD -----
        print("[*] Aguardando download...", flush=True)
        arquivo_baixado = aguardar_download(download_tmp)
        print(f"[OK] Download concluido: {os.path.basename(arquivo_baixado)}", flush=True)

        # ----- ETAPA 5: MOVER E RENOMEAR -----
        agora = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        nome_final = f"UltimasPosicoes - {agora}.xls"
        caminho_final = DESTINO / nome_final

        shutil.move(arquivo_baixado, str(caminho_final))
        print(f"[OK] Arquivo salvo em: {caminho_final}")

    except Exception as e:
        print(f"[ERRO] {e}", flush=True)
        if driver:
            driver.save_screenshot(str(SCREENSHOTS_DIR / "posicoes_99_ERRO.png"))
            print("[SCREENSHOT] posicoes_99_ERRO.png", flush=True)
        raise
    finally:
        if driver:
            driver.quit()
            print("[OK] Navegador fechado.", flush=True)
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
    print("DOWNLOAD AUTOMATICO - ULTIMAS POSICOES")
    print("=" * 60)
    executar()
    print("\n[OK] Processo concluido com sucesso!")
