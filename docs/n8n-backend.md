# Backend em workflows n8n

O objetivo deste modo é aprender e testar fluxos usando o Predictive BI. O React envia suas requisições para `/workflow-api`, um proxy de transporte na mesma origem. O proxy chama os webhooks de produção do n8n. O n8n valida parâmetros, executa regras comerciais em JavaScript e devolve JSON. Python permanece como worker de acesso ao banco, ETL e Machine Learning.

## Workflows

| Arquivo local | Responsabilidade |
| --- | --- |
| `workflows/local/backend-data.json` | GET `/webhook/predictive-bi-data`: leituras, filtros e indicadores comerciais calculados no nó Code |
| `workflows/local/backend-actions.json` | POST `/webhook/predictive-bi-actions`: validação e despacho de tarefas de dados, modelos e insights |
| `workflows/local/complete.json` | ETL → qualidade → treinamento → inferência → insights, acompanhando tarefas até conclusão |

Há também quatro pipelines independentes em `workflows/local`. Os arquivos de backend em `workflows/docker-backend` usam o endereço interno `api:8000`; os locais usam `127.0.0.1:8101`. Para mudar a porta, regenere com `scripts/generate_n8n_backend.py --api-url http://127.0.0.1:PORTA --output workflows/local`.

## Operação local

Inicie o worker e o dashboard com `scripts/Start.ps1`, escolhendo uma porta disponível. `scripts/Start-N8n.ps1 -ApiUrl http://127.0.0.1:8101` prepara os sete workflows e inicia o n8n. Se já houver n8n nessa porta, o script preserva a instância e orienta a importação pelo editor.

No editor local em `http://localhost:5678`, importe os dois arquivos `backend-*.json` e publique **Predictive BI | Backend de leitura** e **Predictive BI | Backend de ações**. Publicar registra os webhooks de produção usados pelo dashboard. Executar uma vez pelo editor registra somente o webhook de teste e não substitui a publicação. O fluxo completo pode ser executado manualmente; seus agendamentos ficam desativados por padrão.

O seletor **Backend do dashboard** usa n8n por padrão. **Python · direto** permite comparar os resultados com a implementação Python. A escolha é explícita e fica no navegador; falhas do n8n não provocam desvio automático para Python. Se os workflows não estiverem publicados, a interface mostra indisponibilidade e a orientação correspondente.

Não é necessário configurar o n8n Assistant, Gemini, Daytona ou um sandbox de assistente para executar estes workflows. Os nós Code são nós comuns do n8n e usam a infraestrutura de execução do próprio n8n.

## Contratos e limites

- Leituras: `analytics`, `models`, `quality`, `pipelines`, `insights`, `status` e acompanhamento de tarefas por ID.
- Analytics aceita `start`, `end`, `region` e `category`. Receita é somada em centavos inteiros; grão de origem é um pedido; pedidos cancelados não entram no faturamento.
- Ações: tarefas `etl`, `quality`, `train`, `infer`, `insights`, além do analista. Chaves de idempotência são preservadas.
- O worker `/internal/orders` fornece as linhas demonstrativas; o nó Code calcula agregados e limita a tabela aos 2.000 pedidos mais recentes. Esse desenho é adequado à demonstração; bases maiores exigem paginação ou agregação no banco.
- URLs de destino são locais e fixadas na geração. O cliente não escolhe um endereço arbitrário. Esta demonstração destina-se ao uso local; exposição à internet exige autenticação e revisão de segurança.

## Verificação realizada

Os dois workflows foram importados com sucesso pelo CLI do n8n 2.45.6 em um diretório de verificação isolado, preservando o banco da instância do usuário. Os testes comparam os cálculos JavaScript com a referência Python usando o dataset existente, validam entradas e verificam o proxy com transporte simulado. O build TypeScript/Vite passou.

Isso comprova importabilidade e contratos, mas não comprova execução dos webhooks na instância do usuário. Nesta sessão, as conexões TCP do processo de execução foram bloqueadas e o navegador conectado ficou indisponível. A publicação e a execução integrada pelo editor permanecem pendentes.
