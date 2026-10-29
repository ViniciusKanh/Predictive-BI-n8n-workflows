# Catálogo dos workflows n8n

Gerado dos JSONs versionados. A importação, a publicação e a execução são verificações distintas.

## Predictive BI | Backend de ações

Arquivo: `workflows/local/backend-actions.json` · ID: `pbi-backend-actions` · 6 nós.

| Nó | Tipo real | Versão | Destino ou operação |
| --- | --- | --- | --- |
| Receber pedido do dashboard | `n8n-nodes-base.webhook` | 2 | predictive-bi-actions |
| Validar pedido | `n8n-nodes-base.code` | 2 | runOnceForAllItems |
| Pedido válido? | `n8n-nodes-base.if` | 2.2 | ={{ $json.ok }} |
| Executar serviço especializado | `n8n-nodes-base.httpRequest` | 4.2 | ={{ $json.worker_url }} |
| Preparar resposta da ação | `n8n-nodes-base.code` | 2 | runOnceForAllItems |
| Responder ao frontend | `n8n-nodes-base.respondToWebhook` | 1.4 |  |

### Conexões

| Origem | Saída | Próximo nó |
| --- | --- | --- |
| Receber pedido do dashboard | 0 | Validar pedido |
| Validar pedido | 0 | Pedido válido? |
| Pedido válido? | 0 | Executar serviço especializado |
| Pedido válido? | 1 | Responder ao frontend |
| Executar serviço especializado | 0 | Preparar resposta da ação |
| Preparar resposta da ação | 0 | Responder ao frontend |

Em IF, saída 0 corresponde ao caminho verdadeiro e saída 1 ao falso. Nos demais nós, saída 0 é o fluxo principal.

## Predictive BI | Backend de leitura

Arquivo: `workflows/local/backend-data.json` · ID: `pbi-backend-data` · 6 nós.

| Nó | Tipo real | Versão | Destino ou operação |
| --- | --- | --- | --- |
| Receber pedido do dashboard | `n8n-nodes-base.webhook` | 2 | predictive-bi-data |
| Validar pedido | `n8n-nodes-base.code` | 2 | runOnceForAllItems |
| Pedido válido? | `n8n-nodes-base.if` | 2.2 | ={{ $json.ok }} |
| Consultar fonte de dados | `n8n-nodes-base.httpRequest` | 4.2 | ={{ $json.worker_url }} |
| Calcular KPIs e montar resposta | `n8n-nodes-base.code` | 2 | runOnceForAllItems |
| Responder ao frontend | `n8n-nodes-base.respondToWebhook` | 1.4 |  |

### Conexões

| Origem | Saída | Próximo nó |
| --- | --- | --- |
| Receber pedido do dashboard | 0 | Validar pedido |
| Validar pedido | 0 | Pedido válido? |
| Pedido válido? | 0 | Consultar fonte de dados |
| Pedido válido? | 1 | Responder ao frontend |
| Consultar fonte de dados | 0 | Calcular KPIs e montar resposta |
| Calcular KPIs e montar resposta | 0 | Responder ao frontend |

Em IF, saída 0 corresponde ao caminho verdadeiro e saída 1 ao falso. Nos demais nós, saída 0 é o fluxo principal.

## Predictive BI | Fluxo completo

Arquivo: `workflows/local/complete.json` · ID: `pbi-complete` · 33 nós.

| Nó | Tipo real | Versão | Destino ou operação |
| --- | --- | --- | --- |
| Executar manualmente | `n8n-nodes-base.manualTrigger` | 1 |  |
| Agendamento diário | `n8n-nodes-base.scheduleTrigger` | 1.2 |  |
| Disparar etl | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar etl | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar etl | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar etl'].json.id }} |
| Concluído? etl | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? etl | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar etl'].json.queued_at)) > 600000 }} |
| Registrar falha etl | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |
| Disparar quality | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar quality | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar quality | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar quality'].json.id }} |
| Concluído? quality | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? quality | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar quality'].json.queued_at)) > 600000 }} |
| Registrar falha quality | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |
| Qualidade aprovada? | `n8n-nodes-base.if` | 2.2 | ={{ $json.result.total > 0 && $json.result.passed === $json.result.total }} |
| Disparar train | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar train | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar train | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar train'].json.id }} |
| Concluído? train | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? train | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar train'].json.queued_at)) > 600000 }} |
| Registrar falha train | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |
| Disparar infer | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar infer | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar infer | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar infer'].json.id }} |
| Concluído? infer | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? infer | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar infer'].json.queued_at)) > 600000 }} |
| Registrar falha infer | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |
| Disparar insights | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar insights | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar insights | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar insights'].json.id }} |
| Concluído? insights | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? insights | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar insights'].json.queued_at)) > 600000 }} |
| Registrar falha insights | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |

### Conexões

| Origem | Saída | Próximo nó |
| --- | --- | --- |
| Executar manualmente | 0 | Disparar etl |
| Agendamento diário | 0 | Disparar etl |
| Disparar etl | 0 | Aguardar etl |
| Aguardar etl | 0 | Consultar etl |
| Consultar etl | 0 | Concluído? etl |
| Concluído? etl | 0 | Disparar quality |
| Concluído? etl | 1 | Falhou ou expirou? etl |
| Falhou ou expirou? etl | 0 | Registrar falha etl |
| Falhou ou expirou? etl | 1 | Aguardar etl |
| Disparar quality | 0 | Aguardar quality |
| Aguardar quality | 0 | Consultar quality |
| Consultar quality | 0 | Concluído? quality |
| Concluído? quality | 0 | Qualidade aprovada? |
| Concluído? quality | 1 | Falhou ou expirou? quality |
| Falhou ou expirou? quality | 0 | Registrar falha quality |
| Falhou ou expirou? quality | 1 | Aguardar quality |
| Qualidade aprovada? | 0 | Disparar train |
| Qualidade aprovada? | 1 | Registrar falha quality |
| Disparar train | 0 | Aguardar train |
| Aguardar train | 0 | Consultar train |
| Consultar train | 0 | Concluído? train |
| Concluído? train | 0 | Disparar infer |
| Concluído? train | 1 | Falhou ou expirou? train |
| Falhou ou expirou? train | 0 | Registrar falha train |
| Falhou ou expirou? train | 1 | Aguardar train |
| Disparar infer | 0 | Aguardar infer |
| Aguardar infer | 0 | Consultar infer |
| Consultar infer | 0 | Concluído? infer |
| Concluído? infer | 0 | Disparar insights |
| Concluído? infer | 1 | Falhou ou expirou? infer |
| Falhou ou expirou? infer | 0 | Registrar falha infer |
| Falhou ou expirou? infer | 1 | Aguardar infer |
| Disparar insights | 0 | Aguardar insights |
| Aguardar insights | 0 | Consultar insights |
| Consultar insights | 0 | Concluído? insights |
| Concluído? insights | 1 | Falhou ou expirou? insights |
| Falhou ou expirou? insights | 0 | Registrar falha insights |
| Falhou ou expirou? insights | 1 | Aguardar insights |

Em IF, saída 0 corresponde ao caminho verdadeiro e saída 1 ao falso. Nos demais nós, saída 0 é o fluxo principal.

## Predictive BI | ETL

Arquivo: `workflows/local/etl.json` · ID: `pbi-etl` · 15 nós.

| Nó | Tipo real | Versão | Destino ou operação |
| --- | --- | --- | --- |
| Executar manualmente | `n8n-nodes-base.manualTrigger` | 1 |  |
| Agendamento diário | `n8n-nodes-base.scheduleTrigger` | 1.2 |  |
| Disparar etl | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar etl | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar etl | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar etl'].json.id }} |
| Concluído? etl | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? etl | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar etl'].json.queued_at)) > 600000 }} |
| Registrar falha etl | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |
| Disparar quality | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar quality | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar quality | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar quality'].json.id }} |
| Concluído? quality | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? quality | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar quality'].json.queued_at)) > 600000 }} |
| Registrar falha quality | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |
| Qualidade aprovada? | `n8n-nodes-base.if` | 2.2 | ={{ $json.result.total > 0 && $json.result.passed === $json.result.total }} |

### Conexões

| Origem | Saída | Próximo nó |
| --- | --- | --- |
| Executar manualmente | 0 | Disparar etl |
| Agendamento diário | 0 | Disparar etl |
| Disparar etl | 0 | Aguardar etl |
| Aguardar etl | 0 | Consultar etl |
| Consultar etl | 0 | Concluído? etl |
| Concluído? etl | 0 | Disparar quality |
| Concluído? etl | 1 | Falhou ou expirou? etl |
| Falhou ou expirou? etl | 0 | Registrar falha etl |
| Falhou ou expirou? etl | 1 | Aguardar etl |
| Disparar quality | 0 | Aguardar quality |
| Aguardar quality | 0 | Consultar quality |
| Consultar quality | 0 | Concluído? quality |
| Concluído? quality | 0 | Qualidade aprovada? |
| Concluído? quality | 1 | Falhou ou expirou? quality |
| Falhou ou expirou? quality | 0 | Registrar falha quality |
| Falhou ou expirou? quality | 1 | Aguardar quality |
| Qualidade aprovada? | 1 | Registrar falha quality |

Em IF, saída 0 corresponde ao caminho verdadeiro e saída 1 ao falso. Nos demais nós, saída 0 é o fluxo principal.

## Predictive BI | GenAI Insights

Arquivo: `workflows/local/insights.json` · ID: `pbi-insights` · 8 nós.

| Nó | Tipo real | Versão | Destino ou operação |
| --- | --- | --- | --- |
| Executar manualmente | `n8n-nodes-base.manualTrigger` | 1 |  |
| Agendamento diário | `n8n-nodes-base.scheduleTrigger` | 1.2 |  |
| Disparar insights | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar insights | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar insights | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar insights'].json.id }} |
| Concluído? insights | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? insights | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar insights'].json.queued_at)) > 600000 }} |
| Registrar falha insights | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |

### Conexões

| Origem | Saída | Próximo nó |
| --- | --- | --- |
| Executar manualmente | 0 | Disparar insights |
| Agendamento diário | 0 | Disparar insights |
| Disparar insights | 0 | Aguardar insights |
| Aguardar insights | 0 | Consultar insights |
| Consultar insights | 0 | Concluído? insights |
| Concluído? insights | 1 | Falhou ou expirou? insights |
| Falhou ou expirou? insights | 0 | Registrar falha insights |
| Falhou ou expirou? insights | 1 | Aguardar insights |

Em IF, saída 0 corresponde ao caminho verdadeiro e saída 1 ao falso. Nos demais nós, saída 0 é o fluxo principal.

## Predictive BI | Predictive Analytics

Arquivo: `workflows/local/predictive.json` · ID: `pbi-predictive` · 14 nós.

| Nó | Tipo real | Versão | Destino ou operação |
| --- | --- | --- | --- |
| Executar manualmente | `n8n-nodes-base.manualTrigger` | 1 |  |
| Agendamento diário | `n8n-nodes-base.scheduleTrigger` | 1.2 |  |
| Disparar train | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar train | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar train | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar train'].json.id }} |
| Concluído? train | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? train | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar train'].json.queued_at)) > 600000 }} |
| Registrar falha train | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |
| Disparar infer | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar infer | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar infer | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar infer'].json.id }} |
| Concluído? infer | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? infer | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar infer'].json.queued_at)) > 600000 }} |
| Registrar falha infer | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |

### Conexões

| Origem | Saída | Próximo nó |
| --- | --- | --- |
| Executar manualmente | 0 | Disparar train |
| Agendamento diário | 0 | Disparar train |
| Disparar train | 0 | Aguardar train |
| Aguardar train | 0 | Consultar train |
| Consultar train | 0 | Concluído? train |
| Concluído? train | 0 | Disparar infer |
| Concluído? train | 1 | Falhou ou expirou? train |
| Falhou ou expirou? train | 0 | Registrar falha train |
| Falhou ou expirou? train | 1 | Aguardar train |
| Disparar infer | 0 | Aguardar infer |
| Aguardar infer | 0 | Consultar infer |
| Consultar infer | 0 | Concluído? infer |
| Concluído? infer | 1 | Falhou ou expirou? infer |
| Falhou ou expirou? infer | 0 | Registrar falha infer |
| Falhou ou expirou? infer | 1 | Aguardar infer |

Em IF, saída 0 corresponde ao caminho verdadeiro e saída 1 ao falso. Nos demais nós, saída 0 é o fluxo principal.

## Predictive BI | Data Quality

Arquivo: `workflows/local/quality.json` · ID: `pbi-quality` · 9 nós.

| Nó | Tipo real | Versão | Destino ou operação |
| --- | --- | --- | --- |
| Executar manualmente | `n8n-nodes-base.manualTrigger` | 1 |  |
| Agendamento diário | `n8n-nodes-base.scheduleTrigger` | 1.2 |  |
| Disparar quality | `n8n-nodes-base.httpRequest` | 4.2 | http://127.0.0.1:8101/api/jobs |
| Aguardar quality | `n8n-nodes-base.wait` | 1.1 | Aguardar 2 seconds |
| Consultar quality | `n8n-nodes-base.httpRequest` | 4.2 | ={{ 'http://127.0.0.1:8101/api/jobs/' + $node['Disparar quality'].json.id }} |
| Concluído? quality | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'success' }} |
| Falhou ou expirou? quality | `n8n-nodes-base.if` | 2.2 | ={{ $json.status === 'failed' \|\| (Date.now() - Date.parse($node['Disparar quality'].json.queued_at)) > 600000 }} |
| Registrar falha quality | `n8n-nodes-base.stopAndError` | 1 | Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API. |
| Qualidade aprovada? | `n8n-nodes-base.if` | 2.2 | ={{ $json.result.total > 0 && $json.result.passed === $json.result.total }} |

### Conexões

| Origem | Saída | Próximo nó |
| --- | --- | --- |
| Executar manualmente | 0 | Disparar quality |
| Agendamento diário | 0 | Disparar quality |
| Disparar quality | 0 | Aguardar quality |
| Aguardar quality | 0 | Consultar quality |
| Consultar quality | 0 | Concluído? quality |
| Concluído? quality | 0 | Qualidade aprovada? |
| Concluído? quality | 1 | Falhou ou expirou? quality |
| Falhou ou expirou? quality | 0 | Registrar falha quality |
| Falhou ou expirou? quality | 1 | Aguardar quality |
| Qualidade aprovada? | 1 | Registrar falha quality |

Em IF, saída 0 corresponde ao caminho verdadeiro e saída 1 ao falso. Nos demais nós, saída 0 é o fluxo principal.
