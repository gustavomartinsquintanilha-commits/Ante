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
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-features=PasswordLeakDetection,PasswordCheck,InsecureDownloadWarnings,SafeBrowsingEnhancedProtection,DownloadBubble,DownloadBubbleV2")
    opts.add_argument("--disable-save-password-bubble")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--unsafely-treat-insecure-origin-as-secure=http://suporte.newsgps.com.br")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-insecure-localhost")

    # No GitHub Actions, usa chromedriver do sistema; localmente usa webdriver_manager
    if os.environ.get("HEADLESS", "").lower() == "true":
        # GitHub Actions - chromedriver já está no PATH
        driver = webdriver.Chrome(options=opts)
    else:
        # Local - usa webdriver_manager
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
    download_tmp = tempfile.mkdtemp(prefix="logistico_dl_")
    print(f"[DIR] Download temporario: {download_tmp}")

    # Garante que o destino existe
    DESTINO.mkdir(parents=True, exist_ok=True)

    driver = None
    try:
        # ----- Inicializa o browser -----
        print("[*] Abrindo navegador...", flush=True)
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
        print(f"[*] Acessando {URL_LOGIN}", flush=True)
        driver.set_page_load_timeout(30)
        try:
            driver.get(URL_LOGIN)
        except Exception as e:
            print(f"[WARN] Timeout no page load (esperado - Flash/YouTube): {e}", flush=True)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "01_pagina_inicial.png"))
        print("[SCREENSHOT] 01_pagina_inicial.png", flush=True)
        print(f"[INFO] URL atual: {driver.current_url}", flush=True)

        # Re-aplica CDP apos carregar a pagina (necessario em algumas versoes do Chrome)
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": download_tmp,
        })

        # Selecionar "Logistica" no dropdown de empresa
        print("[*] Selecionando servico: Logistica...", flush=True)
        time.sleep(3)  # Aguarda pagina carregar completamente
        
        # Tenta encontrar o dropdown com retry
        dropdown_empresa = None
        for tentativa in range(3):
            try:
                dropdown_empresa = wait.until(
                    EC.presence_of_element_located((By.ID, "ddlEmpresa"))
                )
                break
            except:
                print(f"[WARN] Tentativa {tentativa + 1} falhou, aguardando...", flush=True)
                time.sleep(2)
        
        if not dropdown_empresa:
            raise Exception("Dropdown de empresa nao encontrado apos 3 tentativas")
        select = Select(dropdown_empresa)
        select.select_by_value("Logistica")
        print("[OK] Servico selecionado!", flush=True)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "02_servico_selecionado.png"))
        print("[SCREENSHOT] 02_servico_selecionado.png", flush=True)

        # Aguarda a pagina reagir ao postback do dropdown
        print("[*] Aguardando postback...", flush=True)
        time.sleep(5)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "02b_apos_postback.png"))
        print("[SCREENSHOT] 02b_apos_postback.png", flush=True)

        # Preencher usuario
        print("[*] Procurando campo txtLogin...", flush=True)
        campo_usuario = wait.until(
            EC.presence_of_element_located((By.ID, "txtLogin"))
        )
        print("[OK] Campo txtLogin encontrado!", flush=True)
        campo_usuario.click()
        campo_usuario.clear()
        campo_usuario.send_keys(USUARIO)

        # Preencher senha
        campo_senha = driver.find_element(By.ID, "txtSenha")
        campo_senha.click()
        campo_senha.clear()
        campo_senha.send_keys(SENHA)
        print("[OK] Credenciais preenchidas!", flush=True)

        # Clicar em Entrar (imagem btEntrar.jpg)
        btn_entrar = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "img[src*='btEntrar']")
            )
        )
        btn_entrar.click()
        print("[OK] Login realizado!", flush=True)
        time.sleep(3)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "03_apos_login.png"))
        print("[SCREENSHOT] 03_apos_login.png", flush=True)
        print(f"[INFO] URL apos login: {driver.current_url}", flush=True)

        # ----- ETAPA 2: ULTIMAS POSICOES -----
        print("[*] Abrindo Ultimas Posicoes...", flush=True)
        link_posicoes = wait.until(
            EC.element_to_be_clickable((By.ID, "CP_btn01"))
        )
        link_posicoes.click()
        print("[OK] Ultimas Posicoes aberta!", flush=True)

        # Aguarda a pagina de posicoes carregar
        time.sleep(5)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "04_ultimas_posicoes.png"))
        print("[SCREENSHOT] 04_ultimas_posicoes.png", flush=True)

        # Verifica se abriu em nova janela/aba
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            print("[->] Alternado para nova janela/aba.")

        # ----- ETAPA 3: FILTRO DATA INICIO (2 anos atras) -----
        print("[*] Configurando filtro de data de inicio...", flush=True)

        # 3a. Clica no dropdown do calendario de data inicio
        print("[*] Abrindo calendario de Data Inicio...", flush=True)
        btn_calendario = wait.until(
            EC.element_to_be_clickable((By.ID, "CP_DataInicio_B-1Img"))
        )
        btn_calendario.click()
        time.sleep(1)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "05_calendario_aberto.png"))
        print("[SCREENSHOT] 05_calendario_aberto.png", flush=True)

        # 3b. Clica 2x na seta "ano anterior" (<<) para voltar 2 anos
        for click_num in range(1, 3):
            print(f"[*] Clicando seta ano anterior ({click_num}/2)...", flush=True)
            btn_prev_year = wait.until(
                EC.element_to_be_clickable((By.ID, "CP_DataInicio_DDD_C_PYCImg"))
            )
            btn_prev_year.click()
            time.sleep(0.5)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "06_2anos_atras.png"))
        print("[SCREENSHOT] 06_2anos_atras.png", flush=True)

        # 3c. Seleciona o primeiro dia disponivel do mes no calendario
        print("[*] Selecionando primeiro dia disponivel...", flush=True)
        dias_disponiveis = driver.find_elements(
            By.CSS_SELECTOR, "td.dxeCalendarDay"
        )
        dia_selecionado = None
        for dia in dias_disponiveis:
            classes = dia.get_attribute("class") or ""
            if "dxeCalendarOtherMonth" in classes:
                continue
            texto = dia.text.strip()
            if texto and texto.isdigit():
                dia.click()
                dia_selecionado = texto
                print(f"[OK] Dia selecionado: {dia_selecionado}", flush=True)
                break

        if not dia_selecionado:
            raise Exception("Nenhum dia disponivel encontrado no calendario!")

        time.sleep(1)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "07_data_selecionada.png"))
        print("[SCREENSHOT] 07_data_selecionada.png", flush=True)

        # 3d. Valida que a data foi aplicada no campo
        campo_data = driver.find_element(By.ID, "CP_DataInicio_I")
        valor_data = campo_data.get_attribute("value") or ""
        print(f"[VALIDACAO] Data de inicio configurada: '{valor_data}'", flush=True)
        if not valor_data:
            print("[WARN] Campo de data parece vazio!", flush=True)

        # ----- ETAPA 4: EXPORTAR XLS -----
        print("[*] Clicando em Exportar XLS...", flush=True)
        
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
        print("[OK] Exportacao iniciada!", flush=True)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "05_apos_exportar.png"))
        print("[SCREENSHOT] 05_apos_exportar.png", flush=True)
        
        # Aguarda um pouco e tenta aceitar qualquer confirmacao de download
        time.sleep(2)
        try:
            alert = driver.switch_to.alert
            alert.accept()
            print("[->] Confirmacao de download aceita.")
        except:
            pass

        # ----- ETAPA 5: AGUARDAR DOWNLOAD -----
        print("[*] Aguardando download...", flush=True)
        arquivo_baixado = aguardar_download(download_tmp)
        print(f"[OK] Download concluido: {os.path.basename(arquivo_baixado)}", flush=True)

        # ----- ETAPA 6: MOVER E RENOMEAR -----
        agora = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        nome_final = f"Logistico - {agora}.xls"
        caminho_final = DESTINO / nome_final

        shutil.move(arquivo_baixado, str(caminho_final))
        print(f"[OK] Arquivo salvo em: {caminho_final}")

    except Exception as e:
        print(f"[ERRO] {e}", flush=True)
        if driver:
            driver.save_screenshot(str(SCREENSHOTS_DIR / "99_ERRO.png"))
            print("[SCREENSHOT] 99_ERRO.png - Captura no momento do erro")
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
