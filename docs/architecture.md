# Arquitetura e contratos

## Fluxo

CSV demonstrativo → validação Pydantic → upsert transacional → fatos/dimensões → Pandas/scikit-learn/XGBoost → artefatos e avaliações → API FastAPI → React/Recharts. n8n agenda operações pelo contrato de jobs. MLflow recebe experimentos quando disponível. Ollama interpreta evidências sem calcular valores financeiros.

## Modelo de dados

| Tabela | Grão e responsabilidade |
| --- | --- |
| dim_customer | Um cliente fictício, com região, canal e entrada |
| dim_product | Um produto, categoria e preço em centavos |
| dim_date | Um dia do calendário demonstrativo |
| fact_order | Um pedido de um produto; quantidade pode ser maior que um |
| pipeline_run | Uma execução de pipeline, duração, status e resultado/erro |
| app_state | Checkpoints, resultados estruturados, jobs e avaliações versionadas por chave |

Receita líquida: soma de `revenue_cents / 100`; pedidos cancelados têm receita zero. Ticket médio: receita líquida por pedido concluído. Recompra: clientes com mais de um pedido concluído divididos pelos compradores com pedido concluído, no período filtrado. Não há deduplicação por nome: as chaves são numéricas e estáveis.

## Incrementalidade

O watermark armazena `updated_at` e `order_id`. A seleção inclui sobreposição de sete dias; hashes detectam linhas realmente alteradas. Upsert usa chave primária, e o checkpoint é confirmado na mesma transação da carga. PostgreSQL acrescenta advisory lock transacional. O processo da API serializa pipelines e rejeita novo trabalho concorrente com 409. O lote inteiro é rejeitado se contiver duplicidade de pedido, órfãos ou contrato inválido. Dados inválidos não são descartados silenciosamente.

O gerador é append-only por desenho; exclusões na origem não são propagadas. Correções precisam atualizar `updated_at`. Modificações antigas sem alteração desse campo e fora da janela não são detectadas pelo incremental; uma recarga controlada exige limpar somente o checkpoint, preservando tabelas, para reavaliar hashes. O projeto não executa essa operação automaticamente.

## API

| Método e caminho | Contrato |
| --- | --- |
| GET /health | Liveness e conexão ao banco; identifica SQLite degradado |
| GET /api/analytics | Indicadores, séries e amostra de pedidos; start/end/category/region |
| GET /api/models | Previsão, churn, segmentação, métricas e inferência persistidos |
| GET /api/quality | Resultado da última verificação de qualidade |
| GET /api/pipelines | Até 100 execuções, status e duração |
| GET /api/insights | Última análise, fontes e modo de geração |
| GET /api/status | Banco efetivo, manifesto e disponibilidade Ollama |
| POST /api/jobs | JSON pipeline=etl/train/infer/quality/insights; retorna 202 e status_url |
| GET /api/jobs/{id} | queued/running/success/failed; resultado ou causa |
| POST /api/analyst | JSON pipeline=insights e question; resposta tipada com evidências |

`Idempotency-Key` no POST /api/jobs retorna o mesmo job para tentativas repetidas do mesmo pedido. Reutilizar a chave com outra operação retorna 409. O worker tem uma fila ativa por processo; use uma instância de API neste deployment. Jobs em andamento são marcados como interrompidos/falhos ao reiniciar, para não permanecerem falsamente ativos. Não há fila distribuída ou retomada automática de treinamento interrompido.

## Avaliação

Faturamento é agregado em semanas completas de segunda a domingo. Features de calendário/tendência são conhecidas no instante de previsão. As duas janelas de validação precedem oito semanas finais intocadas. A escolha entre Ridge, Random Forest e baseline sazonal usa somente validação. O modelo escolhido é avaliado no teste e depois reajustado para serving.

No churn, snapshots de treino são 30/06/2024 e 31/12/2024; validação em 30/06/2025; teste em 31/03/2026. Features olham somente compras concluídas anteriores ao snapshot. O rótulo considera ausência de compra nos 90 dias seguintes e só é construído quando o horizonte amadureceu. O modelo de serving é reajustado após registrar a avaliação. SHAP explica o modelo identificado, que pode diferir do selecionado, sem inferência causal.

Segmentação usa recência, frequência e valor; escolha de K por silhouette é exploratória e não uma avaliação supervisionada. Clusters não representam classes verdadeiras. Não se infere causalidade de sazonalidade, correlação ou importância de atributos.

## Fronteiras da execução atual

O backend utiliza Pandas, Pydantic e psycopg diretamente, com SQL parametrizado para PostgreSQL e adaptador SQLite explícito. SQLAlchemy, Polars, DuckDB e Optuna estão previstos nas dependências completas, mas não foram necessários ao fluxo executado e não foram instalados nesta sessão sem rede. Não há alegação de uso desses módulos.

O dashboard não chama modelos para inventar valores. Modelos e períodos são globais ao treinamento; filtros comerciais não retreinam nem recalculam automaticamente previsões para segmentos. Isso evita sugerir que uma previsão global se refere a um recorte não avaliado.
