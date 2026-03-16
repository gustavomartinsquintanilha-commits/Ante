# 📚 Documentação Técnica Corporativa - Sistema VSR (Veículos Sem Reportar)

> **Versão:** 1.1 | **Última atualização:** Março/2026

## 📌 1. Visão Geral da Solução
O **Sistema VSR** é uma pipeline de automação desenvolvida em Python destinada à coleta, consolidação e notificação sobre veículos com problemas sistêmicos (sem reportar localização há mais de 48 horas). 
O fluxo abrange desde o web scraping de portais legados (via Selenium) até a extração via APIs modernas (AWS API Gateway) e consultas em bancos de dados SQL Server, culminando no agrupamento e disparo automatizado de relatórios gerenciais por e-mail utilizando SMTP.

### 1.1 Modos de Execução
O sistema suporta dois modos de execução:

| Modo | Ambiente | Descrição |
|------|----------|-----------|
| **Local** | Windows | Execução via `R_Geral.py` com interface gráfica opcional |
| **CI/CD** | GitHub Actions (Ubuntu) | Execução automatizada em cloud com VPN integrada |

### 1.2 Agendamento Automático
A pipeline é executada automaticamente via **GitHub Actions** toda **quinta-feira às 09:00h** (horário de Brasília).
- **Cron configurado:** `0 12 * * 4` (12:00 UTC = 09:00 BRT)
- **Execução manual:** Disponível via `workflow_dispatch` no painel do GitHub Actions

---

## 🏗️ 2. Arquitetura e Orquestração

A arquitetura do projeto baseia-se em um padrão de **Orquestrador Monolítico** ([R_Geral.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/R_Geral.py)) que dispara módulos independentes atuando como *workers* especializados por domínio/sistema de origem.

### 2.1 Orquestrador: [R_Geral.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/R_Geral.py)
Coordena a execução sequencial em três grandes fases para garantir a consistência das dependências dos dados.

> **Nota:** Em ambiente CI (GitHub Actions), o orquestrador detecta automaticamente o modo headless via variável de ambiente `HEADLESS=true` e ajusta os caminhos de diretórios para o runner.

*   **FASE 1 - Coleta Síncrona (Downloads Brutos)**
    *   **Ferramenta:** `subprocess.run()` (Processamento bloqueante).
    *   **Scripts:** [download_posicoes.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/download_posicoes.py) e [download_logistico.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/download_logistico.py).
    *   **Objetivo:** Garantir que as bases Excel oriundas de web scraping puro estejam totalmente íntegras no disco antes de qualquer processamento lógico iniciar. Se a Fase 1 falhar ou não concluir, comprometerá a Fase 2 (Logístico).

*   **FASE 2 - Extração e Tratamento de Dados Paralelos/Assíncronos**
    *   **Ferramenta:** `subprocess.run()` (Ajustado para síncrono para garantir estabilidade da Fase 3).
    *   **Scripts:** [sing.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/sing.py), [telemetria.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/telemetria.py), [logistico.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/logistico.py).
    *   **Objetivo:** Estes scripts processam dados de fontes distintas (Banco SQL, API REST e as planilhas cruzadas da Fase 1). O resultado desta fase são relatórios padronizados no formato `[Empresa]_[Sistema]_VSR[Qtd]_[Data].xlsx` na pasta central do pipeline.

*   **FASE 3 - Distribuição de E-mails (Notificação Síncrona)**
    *   **Ferramenta:** `subprocess.run()`.
    *   **Script:** [enviar_email.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/enviar_email.py).
    *   **Objetivo:** Consolidar todos os relatórios gerados na Fase 2 e distribuí-los com base em uma matriz de roteamento pré-definida no código.

---

## ⚙️ 3. Módulos de Execução e Regras de Negócio Específicas

### 3.1 Fase 1: Coleta Base [(Selenium)](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/enviar_email.py#222-505)
Estes scripts automatizam a navegação em portais da web focados na raspagem (scraping) da base de frota legada.
*   **Tecnologias:** `selenium`, `webdriver_manager`, `Chrome DevTools Protocol (CDP)`.
*   **Regras:** 
    *   Acesso headless omitido visando visualização do fluxo, mas com flags agressivas (`--disable-notifications`, `--disable-save-password-bubble`).
    *   **Bypass de Segurança HTTP:** O sistema `suporte.newsgps.com.br` (HTTP) bloqueia downloads subjacentes no Chrome moderno. Foi imperativo utilizar comandos CDP (`Page.setDownloadBehavior`, `Browser.setDownloadBehavior`) com suporte ao flag `--unsafely-treat-insecure-origin-as-secure` para forçar o browser a expor a porta de gravação de arquivos não seguros na diretiva de rede local.

### 3.2 Fase 2: Extratores Secundários (Data Processing)

#### A. Módulo [sing.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/sing.py) (ODBC / SQL Server)
Responsável por verificar os veículos das listagens corporativas conectando-se diretamente ao SQL Server.
*   **Tecnologias:** `pyodbc`, `pandas`, `openpyxl`, `python-dotenv`.
*   **Regras de Negócio:**
    *   Consulta o arquivo de mapeamento `clientes_listagem.xlsx` que atrela o Cliente ao seu respectivo `IDCliente` e arquivo `.env` de conexão.
    *   Query verifica a tabela `GPS_Ultimas_Posicoes` cruzando com `Tbl_Veiculo` (apenas veículos `ativo = 1`).
    *   **Filtro de VSR (48h):** O DataFrame exclui as posições recebidas em menos de 48 horas (`Data de reporte_dt < datetime.now() - 48h`) ou nulas.
    *   **Fallback (VSR0):** Caso não haja nenhum veículo no critério, o pacote gera obrigatoriamente um arquivo template zerado (`_SING_VSR0_`) garantindo que o downstream (Fase 3) perceba que a empresa rodou e alcançou meta 100%.

#### B. Módulo [telemetria.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/telemetria.py) (RESTful API AWS)
Responsável por consumir os pacotes do novo portal de rastreamento da AWS via API Gateway.
*   **Tecnologias:** `requests`, `pandas`.
*   **Regras de Negócio:**
    *   Garante um Auth Token (Bearer) dinâmico via credenciais (`user/pass`).
    *   Loopa sobre uma matriz de `group_ids` para resgatar o array JSON completo de posições dos clientes.
    *   **Filtros de Exclusão:** Veículos contendo strings reservadas (`vendido, desativado, historico, sinistro, teste`) no campo `tracked_unit_label2` são dropados antes da ingestão e cálculo de 48h.
    *   Conversão de TZ: Strings em ISO-8601 de UTC puro para TZ Aware.
    *   Gera métricas para VSR0 nestes moldes.

#### C. Módulo [logistico.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/logistico.py) (ETL Pandas Local)
Atua como Parser das planilhas brutas oriundas da Fase 1 (`download_posicoes` e `download_logistico`).
*   **Tecnologias:** `pandas` (Engines: `openpyxl` e legado `xlrd`), `regex`.
*   **Regras de Negócio:**
    *   Processa dois tipos de arquiteturas de XLS (UltimasPosicoes e logistico) legados vindos do Excel 2003/97 (`.xls` puro que precisa do read_excel com `xlrd`).
    *   Regex para localizar arquivos e limpar strings sujas (nomes de empresas com caracteres inválidos na matriz principal).
    *   Aplicação do mesmo Threshold (> 48h) e Filtros de Ignorados (Reserva, Oficina, etc.).
    *   Gera arquivos do tipo `_Global_` e `_Logistico_`. Assim como os outros, produz `VSR0` se zerado.

### 3.3 Fase 3: Roteamento de E-mails ([enviar_email.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/enviar_email.py))
Módulo crítico de despacho e reconciliação dos dados gerados na Fase 2.

*   **Tecnologias:** `smtplib`, `email.message`, [re](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/logistico.py#26-31) (Regex Engine de classificação).
*   **Arquitetura de Reconhecimento:**
    O código ignora metadados do SO e usa Regex severo em cima do *filename* final para extrair:
    1.  Empresa (Nome)
    2.  Sistema Origem (`SING`, `Telemetria`, `Global`, `Logístico`)
    3.  QTD Veículos Atrás da Meta (`VSRX`)
*   **Matriz de Equivalência (Alias Engine):**
    Uma vez extraído o "nome", o texto passa por conversões pesadas (`unicodedata`, remoção de strings não alfanuméricas) até virar um stub único. Esse stub é mapeado contra um `dict` (dicionário Python) chamado `empresa_aliases` para fundir nomes de sistemas diferentes numa mesma "empresa roteada" (Ex: `esxriodasoistras`, `ouronegro` viram -> `ouronegro`).

*   **Regras de Negócio e Disparo:**
    1.   **Feature Toggle (JCA):** Grupos do Subgrupo 1 e Subgrupo 2 da JCA são sensíveis. Há uma flag em tempo de execução `ATIVAR_JCA` que caso seja booleana `False`, corta as avaliações da rede JCA não lendo os relatórios em disco e não incluindo no alert log.
    2.   **Modo de Testes Sandbox:** Se a flag `MODO_TESTE = True`, a tabela hash reescreve localmente a chave SMTP de envio forçando os headers `[To]` e omitindo cópias CCO para o e-mail central do desenvolvedor, validando as pipelines sem vazamento em Prod.
    3.  **Deteção de Anomalias Reversas:**
        *   Faz a diferença simétrica e subtrações de Sets Python (`set(a) - set(b)`) comparando as Empresas Mapeadas no Código VS Arquivos Extraídos.
        *   Caso `Empresa_Matriz != Extrator`, dispara o erro *ATA VSR - Não Enviados*.
    4.   **Sistema de Gamificação e Compliance (Meta 0):** Para qualquer relatório sinalizando de QTD `0` (O arquétipo _VSR0_), remove-se o e-mail padrão de cobrança e emite-se um template customizado de `Parabéns` corporativo em HTML para os clientes.

---

## 🛡️ 4. Fluxograma Final

```mermaid
graph TD
    A[Executar R_Geral.py] --> B[FASE 1: subprocess - Downloads.py]
    B -->|Aguardando Completar| B1[Selenium navega em N sites, burla HTTP Insecure via CDP]
    B1 --> B2[Planilhas .xls base geradas cruas]
    B2 --> C[FASE 2: subprocess - Data Processing]
    
    C --> C1(sing.py: SQL Queries -> Regex Filters -> Excel Output)
    C --> C2(telemetria.py: AWS APIGateway -> Bearer Token JSON Parsing -> Excel Output)
    C --> C3(logistico.py: Pandas Read XLS Dataframe Merge -> Filters -> Excel Output)
    
    C1 --> O[Pasta clientes_para_envio]
    C2 --> O
    C3 --> O
    
    O -->|Todos Arquivos Gerados (VSRx e VSR0)| E[FASE 3: enviar_email.py]
    E --> F{ATIVAR_JCA == True?}
    F -->|Sim| F1[Anexa Relatórios JCA e Prepara Envio Grupal]
    F -->|Não| F2[Ignora Disparo Grupal JCA]
    
    E --> G{Qtd == 0?}
    G -->|Sim| G1[E-mail SMTP: Padrão Parabéns Meta Alcançada]
    G -->|Não| G2[E-mail SMTP: Cobrança Normal VSR e Anexos Excel]
    
    E --> V[Análise Crossover Set Python]
    V --> V1[Se Listas cruzadas derem divergentes, emite e-mail de alerta para VSR sobre relatorios não criados]
```

---

## 🛑 5. Boas Práticas e Pontos de Atenção (SPOF - Single Points of Failure)

*   **Drive App Password:** O Google rotaciona os acessos Less Secure Apps. Atualmente, a matriz depende vitalmente da *App Password SMTP* configurada em open-text no fonte ([enviar_email.py](file:///c:/Users/gusta/OneDrive/Documentos/Codigos/Ante/enviar_email.py)). Em caso de falha de login (Auth 535), este será o primeiro ofensor.
*   **Limites de E-Mail (Anti-Spam Gmail):** Por usar um serviço SMTP de correio comum `@gmail.com`, pode ocorrer `rate limiting` (Limite de taxa diária de envio ≈ 500 emails/dia).
*   **Limites de Compatibilidade Pandas/XLRD:** Como as velhas versões dos softwares originais exportam em arquivo BIFF8 puro (`.xls`), se a equipe remover a lib arcaica `xlrd`, o módulo da fase 2 desmorona na função de extração e os relatórios deixarão de ser enviados.

---

## ☁️ 6. Infraestrutura CI/CD (GitHub Actions)

A partir da versão 1.1, o sistema passou a ser executado integralmente via **GitHub Actions**, permitindo automação completa sem intervenção manual.

### 6.1 Workflow: `pipeline_completa.yml`

| Componente | Configuração |
|------------|--------------|
| **Runner** | `ubuntu-latest` |
| **Python** | 3.11 |
| **Chrome** | Stable (via `browser-actions/setup-chrome`) |
| **ODBC Driver** | Microsoft ODBC Driver 18 for SQL Server |
| **VPN Client** | `openfortivpn` (FortiGate SSL-VPN) |

### 6.2 Conexão VPN (FortiGate SSL)

Para acessar o SQL Server interno (`192.168.40.30`), o workflow estabelece uma conexão VPN automaticamente:

```yaml
# Certificado SHA256 do FortiGate (fingerprint em lowercase)
CERT_HASH="92782b4f0bf72089ee27b368ae824d955c432528ce4cdb9b9a178d0c23762b8a"

# Conexão via openfortivpn
sudo openfortivpn 8.243.35.166:443 \
  -u <usuario> \
  -p '<senha>' \
  --trusted-cert=$CERT_HASH
```

**Sequência de estabelecimento:**
1. Conecta ao gateway FortiGate
2. Aguarda interface `ppp0` receber IP (até 30s)
3. Adiciona rota estática `192.168.40.0/24 dev ppp0`
4. Valida conectividade via ping ao SQL Server

### 6.3 Adaptações para Ambiente CI

| Script | Adaptação CI |
|--------|--------------|
| `sing.py` | Override do driver ODBC 17→18; adiciona `TrustServerCertificate=yes` |
| `download_*.py` | Modo headless automático; diretórios ajustados para `./output` |
| `enviar_email.py` | Detecta `HEADLESS=true` e ajusta pasta de relatórios |

### 6.4 Artefatos Gerados

O workflow preserva os seguintes artefatos por 7 dias:
- **arquivos-baixados**: Planilhas XLS brutas da Fase 1
- **relatorios-gerados**: Relatórios Excel processados (Fase 2)
- **screenshots-debug**: Capturas de tela do Selenium para diagnóstico

---

## 📋 7. Arquivos de Configuração

### 7.1 Credenciais SQL Server (`.env`)

O sistema utiliza arquivos `.env` para credenciais de banco, mapeados via `clientes_listagem.xlsx`:

| Arquivo | Banco | Uso |
|---------|-------|-----|
| `.env` | NGAdmin | Empresas: Costa Verde, Planalto, Pássaro Verde, Liderança |
| `2.env` | NGAdmin_ADTSA | Empresa: Viação Progresso |

**Estrutura do `.env`:**
```env
DB_SERVER=192.168.40.30,1433
DB_DATABASE=NGAdmin
DB_USERNAME=airflowSING
DB_PASSWORD=<senha>
DB_DRIVER=ODBC Driver 17 for SQL Server
```

> **Nota:** No CI, o driver é automaticamente sobrescrito para `ODBC Driver 18 for SQL Server`.

### 7.2 Mapeamento de Clientes (`clientes_listagem.xlsx`)

Arquivo Excel que mapeia cada empresa ao seu respectivo `IDCliente` e arquivo `.env`:

| Coluna | Descrição |
|--------|-----------|
| Empresa | Nome da empresa |
| IDCliente | ID no banco SQL Server |
| env_file | Arquivo `.env` a ser carregado |

---

## 🔄 8. Changelog

### v1.1 (Março/2026)
- **download_logistico.py**: Novo filtro de data de início (2 anos atrás) antes de exportar
  - Abre calendário de Data Início
  - Retrocede 2 anos via seta `<<`
  - Seleciona primeiro dia disponível do mês
- **GitHub Actions**: Pipeline automatizada com agendamento (quintas 09:00)
- **VPN integrada**: Conexão automática ao FortiGate para acesso ao SQL Server
- **ODBC Driver 18**: Suporte ao Ubuntu 24.04 com certificado autoassinado

### v1.0 (Março/2026)
- Release inicial com suporte a execução local e CI
- Scripts: `R_Geral.py`, `download_posicoes.py`, `download_logistico.py`, `logistico.py`, `sing.py`, `telemetria.py`, `enviar_email.py`
- Infraestrutura CI/CD básica configurada
