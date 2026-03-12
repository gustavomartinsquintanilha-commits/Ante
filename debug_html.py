# -*- coding: utf-8 -*-
"""
debug_html.py - Captura HTML e screenshot do site para debug
"""
import os
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

URL_LOGIN = "http://suporte.newsgps.com.br/"
OUTPUT_DIR = Path(os.getcwd()) / "debug_output"
OUTPUT_DIR.mkdir(exist_ok=True)
print(f"[INFO] Working dir: {os.getcwd()}")
print(f"[INFO] Output dir: {OUTPUT_DIR}")

def main():
    opts = Options()
    if os.environ.get("HEADLESS", "").lower() == "true":
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--unsafely-treat-insecure-origin-as-secure=http://suporte.newsgps.com.br")

    print("[*] Abrindo navegador...")
    driver = webdriver.Chrome(options=opts)

    try:
        print(f"[*] Acessando {URL_LOGIN}")
        driver.get(URL_LOGIN)
        time.sleep(3)

        # Salva screenshot
        driver.save_screenshot(str(OUTPUT_DIR / "debug_01_inicial.png"))
        print("[OK] Screenshot salvo")

        # Salva HTML completo
        html = driver.page_source
        with open(OUTPUT_DIR / "debug_01_html.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("[OK] HTML salvo")

        # Imprime URL atual
        print(f"[INFO] URL atual: {driver.current_url}")
        print(f"[INFO] Titulo: {driver.title}")

        # Imprime todos os iframes
        iframes = driver.find_elements("tag name", "iframe")
        print(f"[INFO] Iframes encontrados: {len(iframes)}")
        for i, iframe in enumerate(iframes):
            print(f"  iframe[{i}]: src={iframe.get_attribute('src')} id={iframe.get_attribute('id')}")

        # Imprime todos os forms
        forms = driver.find_elements("tag name", "form")
        print(f"[INFO] Forms encontrados: {len(forms)}")
        for i, form in enumerate(forms):
            print(f"  form[{i}]: action={form.get_attribute('action')} id={form.get_attribute('id')}")

        # Imprime todos os selects (dropdowns)
        selects = driver.find_elements("tag name", "select")
        print(f"[INFO] Selects encontrados: {len(selects)}")
        for i, sel in enumerate(selects):
            print(f"  select[{i}]: id={sel.get_attribute('id')} name={sel.get_attribute('name')}")

        # Imprime todos os inputs
        inputs = driver.find_elements("tag name", "input")
        print(f"[INFO] Inputs encontrados: {len(inputs)}")
        for i, inp in enumerate(inputs):
            print(f"  input[{i}]: id={inp.get_attribute('id')} name={inp.get_attribute('name')} type={inp.get_attribute('type')}")

        # Imprime todos os links
        links = driver.find_elements("tag name", "a")
        print(f"[INFO] Links encontrados: {len(links)}")
        for i, link in enumerate(links):
            href = link.get_attribute("href")
            print(f"  a[{i}]: href={href} text={link.text[:50] if link.text else ''}")

        # Tenta acessar URL direta de login
        urls_login = [
            "http://suporte.newsgps.com.br/login.aspx",
            "http://suporte.newsgps.com.br/Login.aspx",
            "http://suporte.newsgps.com.br/Default.aspx",
        ]
        for url in urls_login:
            print(f"\n[*] Tentando: {url}")
            driver.get(url)
            time.sleep(2)
            driver.save_screenshot(str(OUTPUT_DIR / f"debug_{url.split('/')[-1]}.png"))
            print(f"[INFO] URL atual: {driver.current_url}")
            print(f"[INFO] Titulo: {driver.title}")

            selects = driver.find_elements("tag name", "select")
            print(f"[INFO] Selects: {len(selects)}")
            for s in selects:
                print(f"  select: id={s.get_attribute('id')}")

            inputs = driver.find_elements("tag name", "input")
            print(f"[INFO] Inputs: {len(inputs)}")
            for inp in inputs:
                print(f"  input: id={inp.get_attribute('id')} type={inp.get_attribute('type')}")

    finally:
        driver.quit()
        print("\n[OK] Navegador fechado.")

if __name__ == "__main__":
    main()
