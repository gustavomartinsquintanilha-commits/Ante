import requests
import pandas as pd
import os
import time
from datetime import datetime, timedelta, timezone

# =================================================================
# 1. CONFIGURAÇÕES DE DIRETÓRIOS (DINÂMICAS)
# =================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Sobe um nível para 'Codigos' e entra na pasta de envio
PASTA_BASE = os.path.normpath(os.path.join(BASE_DIR, "..", "Envio de e-mail - VSR", "clientes_para_envio"))

# =================================================================
# 2. PARÂMETROS DE CONFIGURAÇÃO
# =================================================================
CONFIGS = [
    {
        "user": "gustavo.martins@optimuz.com.br.ng",
        "group_ids": ["14405", "14416", "14380", "14351", "14451", "14435", "14447", "14445"]
    },
    # --- Consulta JCA pausada (Comentada abaixo) ---
    # {
    #     "user": "gustavo.martins@optimuz.com.br",
    #     "group_ids": ["14273", "14083", "14155", "14280", "14267", "14300"]
    # }
]

PASSWORD = os.getenv("API_PASSWORD", "gustavo")
SLEEP_TIME = 5

# =================================================================
# 3. FUNÇÕES DE APOIO
# =================================================================

def parse_data(data_str):
    if data_str and data_str.endswith("Z"):
        data_str = data_str[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(data_str)
    except (ValueError, TypeError):
        return None

def gerar_token(user, password):
    print(f"Gerando token para o usuário: {user}...")
    url = f"https://l7g3za95wd.execute-api.us-west-2.amazonaws.com/MovaApi/login?user={user}&pass={password}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    token = response.json().get("token")
    if not token:
        raise Exception("Token não encontrado na resposta!")
    print("Token obtido com sucesso.")
    return token

def consultar_posicoes(token, group_id):
    url = f"https://l7g3za95wd.execute-api.us-west-2.amazonaws.com/MovaApi/devstatus?group_id={group_id}"
    headers = {"token": token}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()

def gerar_excel(dados, nome_arquivo):
    registros = []
    agora_utc = datetime.now(timezone.utc)
    dois_dias_atras = agora_utc - timedelta(days=2)
    palavras_ignoradas = ["vendido", "desativado", "historico", "histórico", "sinistro", "teste"]
    
    for item in dados:
        if isinstance(item, dict) and item.get("device_identifier"):
            nome_unidade = str(item.get("tracked_unit_label2", "")).lower()
            if any(palavra in nome_unidade for palavra in palavras_ignoradas):
                continue

            local_time = parse_data(item.get("local_time"))
            if local_time and local_time.tzinfo is None:
                local_time = local_time.replace(tzinfo=timezone.utc)

            if local_time and local_time <= dois_dias_atras:
                registros.append({
                    "Cliente": item.get("group_name"),
                    "Unidade": item.get("tracked_unit_label2"),
                    "Equipamento": item.get("device_identifier"),
                    "Dia": local_time.strftime("%d/%m/%Y"),
                    "Hora": local_time.strftime("%H:%M:%S"),
                })

    if registros:
        df = pd.DataFrame(registros)
        df.to_excel(nome_arquivo, index=False)
        return len(registros)
    return 0

# =================================================================
# 4. ORQUESTRADOR PRINCIPAL
# =================================================================

def main():
    try:
        os.makedirs(PASTA_BASE, exist_ok=True)
        
        if not PASSWORD or PASSWORD == "gustavo":
            print("AVISO: Usando senha padrão.")

        agora_str = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

        for config in CONFIGS:
            user = config["user"]
            group_ids = config["group_ids"]
            print(f"\n--- INICIANDO TELEMETRIA PARA: {user} ---")
            
            try:
                token = gerar_token(user, PASSWORD)
            except Exception as e:
                print(f"❌ Erro no token para {user}: {e}")
                continue

            for group_id in group_ids:
                print(f"\nConsultando group_id: {group_id}...")
                try:
                    dados = consultar_posicoes(token, group_id)
                    lista_de_devices = dados.get("data", []) if isinstance(dados, dict) else dados

                    if not lista_de_devices:
                        print("ℹ️ Nenhum device encontrado.")
                        continue

                    nome_empresa_raw = lista_de_devices[0].get("group_name", "Desconhecida")
                    nome_limpo = "".join(c for c in nome_empresa_raw if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
                    
                    nome_temp = os.path.join(PASTA_BASE, f"temp_{group_id}.xlsx")
                    qtd = gerar_excel(lista_de_devices, nome_temp)

                    if qtd > 0:
                        nome_final = os.path.join(PASTA_BASE, f"Telemetria_{nome_limpo}_VSR{qtd}_{agora_str}.xlsx")
                        if os.path.exists(nome_final): os.remove(nome_final)
                        os.rename(nome_temp, nome_final)
                        print(f"✔️ Relatório gerado: {os.path.basename(nome_final)}")
                    else:
                        if os.path.exists(nome_temp): os.remove(nome_temp)
                        # Gera arquivo vazio com VSR0 para sinalizar 0 veiculos
                        nome_final_zero = os.path.join(PASTA_BASE, f"Telemetria_{nome_limpo}_VSR0_{agora_str}.xlsx")
                        pd.DataFrame(columns=['Cliente', 'Unidade', 'Equipamento', 'Dia', 'Hora']).to_excel(
                            nome_final_zero, index=False
                        )
                        print(f"ℹ️ {nome_empresa_raw}: Sem veículos em atraso. Gerado VSR0: {os.path.basename(nome_final_zero)}")

                except Exception as e:
                    print(f"⚠️ Erro no group_id {group_id}: {e}")
                
                finally:
                    time.sleep(SLEEP_TIME)

        print("\n🏁 Processamento de Telemetria finalizado.")

    except Exception as e:
        print(f"❌ Erro fatal no script: {e}")

if __name__ == "__main__":
    main()