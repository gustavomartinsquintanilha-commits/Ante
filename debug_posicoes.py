# -*- coding: utf-8 -*-
"""
debug_posicoes.py - Inspeciona HTML do site bus.systemsatx.com.br
"""
import os
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

URL_LOGIN = "https://bus.systemsatx.com.br/Default.aspx?IdConfig=18"
USUARIO = "julyana"
SENHA = "julyana"
OUTPUT_DIR = Path(os.getcwd()) / "debug_output"
OUTPUT_DIR.mkdir(exist_ok=True)

def main():
    print("[*] Configurando Chrome...", flush=True)
    opts = Options()
    if os.environ.get("HEADLESS", "").lower() == "true":
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")

    print("[*] Abrindo navegador...", flush=True)
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 30)

    try:
        # LOGIN
        print(f"[*] Acessando {URL_LOGIN}", flush=True)
        driver.get(URL_LOGIN)
        driver.save_screenshot(str(OUTPUT_DIR / "01_login_page.png"))
        
        campo_usuario = wait.until(EC.presence_of_element_located((By.ID, "txtLogin")))
        campo_usuario.send_keys(USUARIO)
        campo_senha = driver.find_element(By.ID, "txtSenha")
        campo_senha.send_keys(SENHA)
        driver.find_element(By.ID, "btnLogin").click()
        print("[OK] Login realizado!", flush=True)
        time.sleep(3)
        driver.save_screenshot(str(OUTPUT_DIR / "02_apos_login.png"))

        # ULTIMAS POSICOES
        print("[*] Abrindo Ultimas Posicoes...", flush=True)
        link_posicoes = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick,'AbreUltimasPosicoes')]"))
        )
        # Guarda janela atual
        janela_principal = driver.current_window_handle
        print(f"[INFO] Janela principal: {janela_principal}", flush=True)
        
        link_posicoes.click()
        print("[OK] Clicou em Ultimas Posicoes!", flush=True)
        
        # Aguarda popup abrir (pode demorar)
        print("[*] Aguardando popup abrir...", flush=True)
        for tentativa in range(10):
            time.sleep(1)
            if len(driver.window_handles) > 1:
                print(f"[OK] Popup detectado na tentativa {tentativa+1}!", flush=True)
                break
            print(f"  Tentativa {tentativa+1}: {len(driver.window_handles)} janela(s)", flush=True)

        # Verifica janelas
        print(f"[INFO] Janelas abertas: {len(driver.window_handles)}", flush=True)
        for i, handle in enumerate(driver.window_handles):
            driver.switch_to.window(handle)
            print(f"  Janela[{i}]: {handle} URL={driver.current_url}", flush=True)
        
        # Muda para a janela que NÃO é a principal
        for handle in driver.window_handles:
            if handle != janela_principal:
                driver.switch_to.window(handle)
                print(f"[->] Alternado para popup: {handle}", flush=True)
                time.sleep(3)
                break

        driver.save_screenshot(str(OUTPUT_DIR / "03_ultimas_posicoes.png"))
        print(f"[INFO] URL atual: {driver.current_url}", flush=True)
        print(f"[INFO] Titulo: {driver.title}", flush=True)

        # Salva HTML
        html = driver.page_source
        with open(OUTPUT_DIR / "03_ultimas_posicoes.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("[OK] HTML salvo!", flush=True)

        # Lista iframes
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"[INFO] Iframes: {len(iframes)}", flush=True)
        for i, iframe in enumerate(iframes):
            print(f"  iframe[{i}]: src={iframe.get_attribute('src')} id={iframe.get_attribute('id')}", flush=True)

        # Lista todos os inputs
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"[INFO] Inputs: {len(inputs)}", flush=True)
        for inp in inputs:
            inp_id = inp.get_attribute("id")
            inp_type = inp.get_attribute("type")
            inp_value = inp.get_attribute("value")
            if inp_id or inp_value:
                print(f"  input: id={inp_id} type={inp_type} value={inp_value}", flush=True)

        # Lista todos os buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"[INFO] Buttons: {len(buttons)}", flush=True)
        for btn in buttons:
            print(f"  button: id={btn.get_attribute('id')} text={btn.text[:50] if btn.text else ''}", flush=True)

        # Lista links
        links = driver.find_elements(By.TAG_NAME, "a")
        print(f"[INFO] Links: {len(links)}", flush=True)
        for link in links[:20]:
            href = link.get_attribute("href") or ""
            text = link.text[:30] if link.text else ""
            onclick = link.get_attribute("onclick") or ""
            if "export" in href.lower() or "export" in text.lower() or "export" in onclick.lower() or "xls" in href.lower() or "xls" in text.lower():
                print(f"  a: href={href} text={text} onclick={onclick[:50]}", flush=True)

        # Procura qualquer elemento com "export" ou "xls"
        print("\n[*] Buscando elementos com 'export' ou 'xls'...", flush=True)
        elementos = driver.find_elements(By.XPATH, "//*[contains(@id, 'xport') or contains(@id, 'XLS') or contains(@value, 'Excel') or contains(@onclick, 'xport')]")
        print(f"[INFO] Elementos encontrados: {len(elementos)}", flush=True)
        for el in elementos:
            print(f"  tag={el.tag_name} id={el.get_attribute('id')} value={el.get_attribute('value')} onclick={el.get_attribute('onclick')}", flush=True)

        # Se houver iframe, entra nele e repete a busca
        if iframes:
            print("\n[*] Entrando no primeiro iframe...", flush=True)
            driver.switch_to.frame(iframes[0])
            time.sleep(2)
            driver.save_screenshot(str(OUTPUT_DIR / "04_dentro_iframe.png"))
            
            # Salva HTML do iframe
            html_iframe = driver.page_source
            with open(OUTPUT_DIR / "04_iframe.html", "w", encoding="utf-8") as f:
                f.write(html_iframe)
            
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"[INFO] Inputs no iframe: {len(inputs)}", flush=True)
            for inp in inputs:
                inp_id = inp.get_attribute("id")
                inp_type = inp.get_attribute("type")
                inp_value = inp.get_attribute("value")
                if inp_id or inp_value:
                    print(f"  input: id={inp_id} type={inp_type} value={inp_value}", flush=True)

    finally:
        driver.quit()
        print("\n[OK] Navegador fechado.", flush=True)

if __name__ == "__main__":
    main()
