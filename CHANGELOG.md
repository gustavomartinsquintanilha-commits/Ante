# AVSR - Automacao VSR (Changelog)

## v1.0 - 2026-03-16 (Release Inicial)

### Scripts
- **R_Geral.py** - Orquestrador principal (3 fases: Downloads, Reportes, Envio)
- **download_logistico.py** - Download automatico do relatorio logistico (bus.systemsatx.com.br)
- **download_posicoes.py** - Download automatico das ultimas posicoes (bus.systemsatx.com.br)
- **logistico.py** - Processamento do relatorio logistico (XLS -> Excel formatado)
- **sing.py** - Consulta SQL Server (SING) e gera relatorios por empresa
- **telemetria.py** - Geracao de relatorios de telemetria via API
- **enviar_email.py** - Envio automatizado de e-mails com relatorios anexados

### Infraestrutura CI/CD
- **GitHub Actions** (`pipeline_completa.yml`) - Pipeline automatizada
- **VPN FortiGate SSL** via openfortivpn no CI
- **ODBC Driver 18** para SQL Server no Ubuntu 24.04
- **Chrome headless** para automacao web no CI
- Suporte a ambiente local (Windows) e CI (Ubuntu) via `HEADLESS` env var

### Arquivos de Dados
- `.env` - Credenciais SQL Server (airflowSING / NGAdmin)
- `2.env` - Credenciais SQL Server (airflowADTSA / NGAdmin_ADTSA)
- `clientes_listagem.xlsx` - Mapeamento de empresas para SING

---

## v1.1 - 2026-03-19 (Estável)

### Alteracoes
- **download_logistico.py** - Novo filtro de data de inicio antes de exportar:
  - Abre calendario de Data Inicio (CP_DataInicio_B-1Img)
  - Clica 2x na seta "ano anterior" (<<) para voltar 2 anos
  - Seleciona o primeiro dia disponivel do mes
  - Valida que a data foi aplicada no campo
  - Entao exporta o XLS
