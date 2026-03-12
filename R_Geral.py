import subprocess
import os
import sys

# Garante saida UTF-8 no console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def executar_processos():
    # Adapta diretorio base para CI/Windows
    IS_CI = os.environ.get("HEADLESS", "").lower() == "true"
    if IS_CI:
        diretorio_base = os.getcwd()
    else:
        diretorio_base = r"C:\Users\gusta\OneDrive\Documentos\Codigos"
    
    print(f"[INFO] Diretorio base: {diretorio_base}", flush=True)

    # ── FASE 1: Downloads (executam primeiro e aguardam conclusao) ──
    downloads = [
        ("Ante", "download_posicoes.py"),
        ("Ante", "download_logistico.py"),
    ]

    # ── FASE 2: Tratativas (so disparam apos os downloads) ──
    reportes = [
        ("Ante", "sing.py"),
        ("Ante", "telemetria.py"),
        ("Ante", "logistico.py"),
    ]

    print("\n" + "=" * 60, flush=True)
    print(" CENTRAL DE REPORTES - INICIANDO PROCESSOS", flush=True)
    print("=" * 60, flush=True)

    # ── FASE 1: Executar downloads e AGUARDAR conclusao ──
    print("\n FASE 1 - DOWNLOADS", flush=True)
    print("-" * 40, flush=True)
    for pasta, nome_script in downloads:
        caminho_pasta = os.path.join(diretorio_base, pasta)
        caminho_script = os.path.join(caminho_pasta, nome_script)

        if os.path.exists(caminho_script):
            print(f"[*] {pasta} -> Executando {nome_script}...", flush=True)
            try:
                resultado = subprocess.run(
                    [sys.executable, nome_script],
                    cwd=caminho_pasta,
                )
                if resultado.returncode == 0:
                    print(f"✅ {nome_script} concluido com sucesso!", flush=True)
                else:
                    print(f"❌ {nome_script} finalizou com erro (codigo {resultado.returncode})", flush=True)
            except Exception as e:
                print(f"❌ ERRO ao executar {nome_script}: {e}", flush=True)
        else:
            print(f"⚠️ CAMINHO NAO ENCONTRADO: {caminho_script}", flush=True)

    # ── FASE 2: Executar reportes e AGUARDAR conclusao ──
    print("\n FASE 2 - REPORTES", flush=True)
    print("-" * 40, flush=True)
    for pasta, nome_script in reportes:
        caminho_pasta = os.path.join(diretorio_base, pasta)
        caminho_script = os.path.join(caminho_pasta, nome_script)

        if os.path.exists(caminho_script):
            print(f"[*] {pasta} -> Executando {nome_script}...", flush=True)
            try:
                resultado = subprocess.run(
                    [sys.executable, nome_script],
                    cwd=caminho_pasta,
                )
                if resultado.returncode == 0:
                    print(f"✅ {nome_script} concluido com sucesso!", flush=True)
                else:
                    print(f"❌ {nome_script} finalizou com erro (codigo {resultado.returncode})", flush=True)
            except Exception as e:
                print(f"❌ ERRO ao executar {nome_script}: {e}", flush=True)
        else:
            print(f"⚠️ CAMINHO NAO ENCONTRADO: {caminho_script}", flush=True)

    # ── FASE 3: Envio de e-mails (apos reportes) ──
    print("\n FASE 3 - ENVIO DE E-MAILS", flush=True)
    print("-" * 40, flush=True)
    pasta_email = os.path.join(diretorio_base, "Ante")
    script_email = os.path.join(pasta_email, "enviar_email.py")
    if os.path.exists(script_email):
        print("[*] Ante -> Executando enviar_email.py...", flush=True)
        try:
            resultado = subprocess.run(
                [sys.executable, "enviar_email.py"],
                cwd=pasta_email,
            )
            if resultado.returncode == 0:
                print("✅ enviar_email.py concluido com sucesso!", flush=True)
            else:
                print(f"❌ enviar_email.py finalizou com erro (codigo {resultado.returncode})", flush=True)
        except Exception as e:
            print(f"❌ ERRO ao executar enviar_email.py: {e}", flush=True)
    else:
        print(f"⚠️ CAMINHO NAO ENCONTRADO: {script_email}", flush=True)

    print("\n✅ Todos os processos foram concluídos!", flush=True)

# Execução direta ao rodar o script
if __name__ == '__main__':
    executar_processos()

