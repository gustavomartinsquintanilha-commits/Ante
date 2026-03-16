# Documentação Executiva: Sistema AVSR (Análise de Veículos Sem Reportar)

## 1. Visão Geral do Sistema (O que é)
O **Sistema AVSR (Análise de Veículos Sem Reportar)** é uma solução automatizada desenvolvida internamente por **Gustavo Martins** (Equipe de Suporte e Atendimento - Gestão de Clientes) para garantir o monitoramento ativo e a saúde operacional das frotas dos clientes Tryvia.

Diariamente, milhares de veículos trafegam utilizando rastreadores que enviam dados para múltiplas plataformas (como Telemetria e SING). Quando um equipamento para de transmitir informações por mais de 48 horas (2 dias), chamamos isso de evento "VSR".

A nossa automação varre essas bases de dados para identificar falhas de comunicação e **notifica proativamente** as empresas parceiras via e-mail. O objetivo é garantir que os gestores saibam exatamente quais veículos precisam de atenção – seja por uma manutenção programada, falta de cobertura de sinal ou problemas mecânicos.

## 2. Como Funciona (O processo passo a passo)
O código funciona de maneira 100% autônoma, sem intervenção humana, seguindo as etapas abaixo:

1. **Coleta de Dados**: O sistema coleta planilhas brutas extraídas das plataformas de rastreamento da Tryvia.
2. **Processamento e Filtros**: O código cruza os dados e aplica filtros inteligentes. Por exemplo, ele ignora automaticamente veículos que já estão classificados internamente como "Em Manutenção", "Reserva", "Teste", ou "Venda", focando apenas naqueles que *deveriam* estar transmitindo, mas não estão.
3. **Distribuição por Cliente**: O sistema agrupa os veículos inativos por empresa e gera relatórios individuais (arquivos Excel unificados e organizados).
4. **Acionamento Automático**: 
   - Se a frota possui veículos sem comunicação, um e-mail com os anexos Excel é enviado ao cliente para verificação.
   - Se a frota está 100% ativa, envia-se um e-mail comemorativo de "Parabéns", fortalecendo a parceria e demonstrando a excelência dos nossos equipamentos.
5. **Auditoria Interna**: Uma cópia com o resumo da operação (e possíveis inconsistências logísticas, como empresas novas não cadastradas na base) é enviada para a equipe da Tryvia.

## 3. Tecnologias Utilizadas
A arquitetura foi desenhada para ser rápida, leve e rodar no *background* (em segundo plano). As principais tecnologias são:
- **Python**: Linguagem de programação principal utilizada pelas maiores empresas do mundo, escolhida pela sua altíssima capacidade de automatizar fluxos complexos.
- **Motores de Tratamento de Dados (Pandas & Regex)**: Algoritmos responsáveis por ler planilhas simultaneamente, limpar nomes de empresas inconsistentes e aplicar cálculos de data/hora para detectar a janela exata de 48h sem comunicação.
- **Protocolo SMTP Seguro**: Camada de envio blindada com criptografia de ponta a ponta, conectada diretamente ao servidor de disparos corporativos da Tryvia, garantindo que nossas notificações cheguem com segurança e confiabilidade na caixa de entrada do cliente.

## 4. Modelos de Comunicação (Padrão Corporativo Tryvia)
Nossas comunicações foram reestruturadas para remover o caráter técnico/punitivo de "cobrança" e adotar um tom de **parceria tecnológica e apoio operacional**. Abaixo, os principais cenários automatizados:

### Cenário A: Identificação de Veículos Inativos (Apoio Operacional)
Enviado quando o sistema (AVSR) capta equipamentos sem reportar informações no radar.

> **Assunto:** Relatório veículos sem reportar - <Nome do Cliente> (Telemetria)
> 
> Prezados,
> 
> Este comunicado é enviado de forma automatizada com o objetivo de apoiar o monitoramento operacional dos veículos integrados ao sistema.
> 
> Identificamos atualmente: 
>    - 15 veículos sem envio de informações há mais de 2 dias no sistema Telemetria.
> 
> Conforme relação apresentada no(s) anexo(s). *(Uma planilha Excel com as posições detalhadas é anexada).*
> 
> Esse alerta tem como finalidade permitir a verificação da situação desses veículos, como por exemplo: parada operacional, manutenção, veículos fora de operação ou eventual necessidade de intervenção técnica.
> 
> Caso a verificação indique necessidade de suporte técnico, nossa equipe permanece à disposição para apoiar nas análises e orientações necessárias.
> 
> Atenciosamente,
> Tryvia

### Cenário B: Frota 100% Operacional (Comemoração e Lealdade)
Disparado estritamente quando o código varre toda a base referencial do cliente e atesta "zero veículos inativos".

> **Assunto:** Parabéns - <Nome do Cliente> sem veículos sem reportar
> 
> Prezados,
> 
> Este comunicado é enviado de forma automatizada com o objetivo de apoiar o monitoramento operacional dos veículos integrados ao sistema.
> 
> Gostaríamos de parabenizar a <Nome do Cliente> por não possuir nenhum veículo sem envio de informações no sistema.
> 
> Este resultado reflete o comprometimento da equipe com o bom funcionamento dos equipamentos. Continuem com o excelente trabalho!
> 
> Atenciosamente,
> Tryvia

## 5. Benefícios para a Tryvia
O impacto operacional que essa automação traz para a saúde das frotas da Tryvia é abrangente:
- **Redução Agressiva de Custo e Tempo**: Quando realizado de forma manual, esse processo exigia que um colaborador dedicasse **cerca de 4 a 5 horas** para concluir todas as etapas — baixando planilhas, cruzando dados, gerando relatórios e disparando e-mails individualmente. Agora, com a automação, **o processo leva aproximadamente 2 minutos**, sem nenhuma etapa manual, sendo executado de forma mais completa e detalhada. Isso libera a equipe de Suporte para atuar de forma mais analítica e estratégica.
- **Eliminação de Erros Manuais**: Foi mitigado o risco de falha humana (esquecer de notificar um parceiro em dia de pico, ou de anexar, por lapso de troca de janelas, o relatório do cliente Y para o cliente X numa quebra de confidencialidade). 
- **Presença Constante de Marca e Pós-Venda Ativo**: Os envios institucionais mantêm o emblema da nossa atuação, zelando pela frota diretamente na caixa de e-mail diária dos gestores operacionais do parceiro. Isso posiciona a **Tryvia** não apenas como fornecedora, mas como uma engrenagem ativa na operação diária e de gestão inteligente da logística do cliente.

## 6. Execução Automática via GitHub Actions
O sistema AVSR é executado de forma **100% automática na nuvem**, utilizando a infraestrutura do **GitHub Actions**. Isso significa que:

- **Não é necessária uma máquina dedicada** para rodar o processo
- **Não há dependência de um computador físico** ligado ou de intervenção manual
- A execução ocorre em servidores remotos seguros e escaláveis

### Agendamento
A pipeline é executada automaticamente **toda quinta-feira às 09:00h** (horário de Brasília), garantindo que os relatórios sejam gerados e enviados de forma consistente e pontual, sem necessidade de ação humana.

> **Nota:** Além do agendamento automático, é possível disparar a execução manualmente a qualquer momento pelo painel de administração do GitHub Actions, caso seja necessário gerar relatórios fora do ciclo semanal.

## 7. Notificações de Status da Execução
Ao término de cada execução, o sistema envia automaticamente um e-mail de resumo para a equipe interna da Tryvia, informando o resultado da operação.

### Cenário de Sucesso
Quando todo o processo é executado corretamente, um e-mail de confirmação é enviado com:
-  Confirmação de execução bem-sucedida
-  Quantidade de relatórios gerados
-  Lista de clientes notificados
-  Clientes que atingiram a meta (0 veículos sem reportar)

### Cenário de Falha
Caso ocorra algum problema durante a execução, o sistema notifica a equipe interna com detalhes sobre o tipo de falha. Os principais tipos de falha esperados são:

| Tipo de Falha | Descrição | Ação Recomendada |
|---------------|-----------|------------------|
| **Falha de Conexão VPN** | Não foi possível estabelecer conexão com a rede interna para acessar o banco de dados | Verificar credenciais VPN e status do gateway FortiGate |
| **Timeout de Banco de Dados** | O SQL Server não respondeu dentro do tempo limite | Verificar disponibilidade do servidor |
| **Falha de Login nas Plataformas** | Credenciais de acesso aos portais web expiraram ou foram alteradas | Atualizar credenciais no código |
| **Erro de Download de Planilhas** | Não foi possível baixar os relatórios das plataformas de rastreamento | Verificar se os portais estão online e acessíveis |
| **Falha no Envio de E-mail (SMTP)** | Problema na autenticação ou limite de envios do Gmail | Verificar App Password e limites de quota |
| **Empresa Não Mapeada** | Uma nova empresa foi detectada nos dados, mas não possui destinatário cadastrado | Adicionar o mapeamento no código `enviar_email.py` |

Essa transparência permite que a equipe de suporte identifique rapidamente a causa raiz e tome as medidas corretivas necessárias, garantindo a continuidade do serviço.
