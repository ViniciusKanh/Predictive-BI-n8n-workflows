# Verificação consolidada da implementação

Data: 29/10/2026. Evidências estruturadas em `artifacts/verification.json`, `artifacts/test-results.xml`, `artifacts/bootstrap-report.json` e no banco demonstrativo. A data de referência dos dados é 30/09/2026.

| Verificação | Resultado observado |
| --- | --- |
| Dataset reproduzível | 47.784 pedidos, 1.200 clientes, 60 produtos; seed 42 e SHA-256 registrado |
| Carga e integridade | ETL executado; 9/9 verificações de qualidade sem inconsistências |
| Receita reconciliada | 6.101.595.772 centavos na origem e no destino SQLite |
| Previsão de faturamento | Treino, validação em duas janelas, teste final e inferência de oito semanas executados |
| Churn | Regressão logística, Random Forest e XGBoost treinados e avaliados temporalmente |
| Segmentação | K-Means comparado para K=3,4,5 sobre RFM transformado |
| SHAP | TreeExplainer executado; modelo explicado identificado nos resultados |
| Testes automatizados | 16 aprovados, 0 falhas, 0 erros, 0 pulados |
| Endpoints | 10 rotas incluindo dashboard, docs e OpenAPI retornaram 200 no transporte ASGI em processo |
| Frontend | Checagem TypeScript e build Vite aprovados |
| PowerShell | Sintaxe dos 6 scripts analisada com Parser nativo |
| Docker Compose | Configuração válida; inicialização bloqueada por Engine indisponível |
| n8n | 4 JSONs e referências estruturais verificados; importação/execução reais pendentes |
| PostgreSQL | Cluster exclusivo iniciado; conexão de cliente bloqueada, sem carga comprovada |
| MLflow | Integração implementada; dependência/servidor indisponíveis, registro pendente |
| Ollama | Listener iniciado; Qwen2.5:3b localizado em manifesto existente; chamadas TCP bloqueadas |
| Analista | Resumo determinístico real com evidências persistidas; geração Qwen não comprovada |
| Ruff | Configurado; execução pendente por ausência da dependência e bloqueio do índice de pacotes |
| Navegador | Acesso/inspeção visual bloqueados; não considerados aprovados |

## Métricas do teste final

| Indicador | Valor medido |
| --- | --- |
| Previsão selecionada por validação | Random Forest |
| WAPE previsão | 11,3548% |
| WAPE baseline sazonal | 14,0322% |
| MAE semanal | R$ 46.552,12 |
| RMSE semanal | R$ 52.439,16 |
| Churn selecionado por validação | Random Forest |
| ROC-AUC churn | 0,9319 |
| PR-AUC churn | 0,9345 |
| Precisão churn | 0,9362 |
| Revocação churn | 0,7473 |
| F1 churn | 0,8311 |
| Brier churn | 0,1015 |
| Silhouette segmentação | 0,6187 |

As avaliações utilizam somente dados demonstrativos. Métricas altas nesse cenário não validam desempenho em uma população real. O teste de vazamento temporal modifica compras futuras e comprova que os atributos anteriores permanecem iguais, embora o rótulo possa mudar.

## Serviços e acessibilidade

A API iniciou um listener de produção local em `http://127.0.0.1:8100`, servindo o build React. A documentação fica em `/docs`. O ambiente desta sessão impediu clientes TCP de acessar inclusive localhost; portanto não foi possível confirmar a acessibilidade desses endereços no navegador. Isso é distinto dos testes ASGI aprovados.

Os endereços n8n `:5680`, MLflow `:5010` e frontend Docker `:5180` estão configurados, mas seus serviços não foram iniciados. A documentação de início/parada e recuperação está em README.md e operations.md. Nenhum volume foi removido e nenhum outro projeto foi modificado.
