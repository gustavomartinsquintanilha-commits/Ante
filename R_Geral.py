import subprocess
import os
import sys


def executar_processos():
    diretorio_base = r"C:\Users\gusta\OneDrive\Documentos\Codigos"

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

    print("\n" + "=" * 60)
    print(" CENTRAL DE REPORTES - INICIANDO PROCESSOS")
    print("=" * 60)

    # ── FASE 1: Executar downloads e AGUARDAR conclusao ──
    print("\n FASE 1 - DOWNLOADS")
    print("-" * 40)
    for pasta, nome_script in downloads:
        caminho_pasta = os.path.join(diretorio_base, pasta)
        caminho_script = os.path.join(caminho_pasta, nome_script)

        if os.path.exists(caminho_script):
            print(f"[*] {pasta} -> Executando {nome_script}...")
            try:
                resultado = subprocess.run(
                    [sys.executable, nome_script],
                    cwd=caminho_pasta,
                )
                if resultado.returncode == 0:
                    print(f"✅ {nome_script} concluido com sucesso!")
                else:
                    print(f"❌ {nome_script} finalizou com erro (codigo {resultado.returncode})")
            except Exception as e:
                print(f"❌ ERRO ao executar {nome_script}: {e}")
        else:
            print(f"⚠️ CAMINHO NAO ENCONTRADO: {caminho_script}")

    # ── FASE 2: Executar reportes e AGUARDAR conclusao ──
    print("\n FASE 2 - REPORTES")
    print("-" * 40)
    for pasta, nome_script in reportes:
        caminho_pasta = os.path.join(diretorio_base, pasta)
        caminho_script = os.path.join(caminho_pasta, nome_script)

        if os.path.exists(caminho_script):
            print(f"[*] {pasta} -> Executando {nome_script}...")
            try:
                resultado = subprocess.run(
                    [sys.executable, nome_script],
                    cwd=caminho_pasta,
                )
                if resultado.returncode == 0:
                    print(f"✅ {nome_script} concluido com sucesso!")
                else:
                    print(f"❌ {nome_script} finalizou com erro (codigo {resultado.returncode})")
            except Exception as e:
                print(f"❌ ERRO ao executar {nome_script}: {e}")
        else:
            print(f"⚠️ CAMINHO NAO ENCONTRADO: {caminho_script}")

    # ── FASE 3: Envio de e-mails (apos reportes) ──
    print("\n FASE 3 - ENVIO DE E-MAILS")
    print("-" * 40)
    pasta_email = os.path.join(diretorio_base, "Ante")
    script_email = os.path.join(pasta_email, "enviar_email.py")
    if os.path.exists(script_email):
        print("[*] Ante -> Executando enviar_email.py...")
        try:
            resultado = subprocess.run(
                [sys.executable, "enviar_email.py"],
                cwd=pasta_email,
            )
            if resultado.returncode == 0:
                print("✅ enviar_email.py concluido com sucesso!")
            else:
                print(f"❌ enviar_email.py finalizou com erro (codigo {resultado.returncode})")
        except Exception as e:
            print(f"❌ ERRO ao executar enviar_email.py: {e}")
    else:
        print(f"⚠️ CAMINHO NAO ENCONTRADO: {script_email}")

    print("\n✅ Todos os processos foram concluídos!")

# Execução direta ao rodar o script
if __name__ == '__main__':
    executar_processos()

