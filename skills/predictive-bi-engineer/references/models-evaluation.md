# Modelos, avaliação e MLOps

Declare alvo, unidade, frequência, horizonte e disponibilidade de cada atributo. Reserve período final intocado. Ajuste imputação, codificação, escala e seleção somente no treino de cada partição, preferencialmente com Pipeline/ColumnTransformer. Separe grupos/clientes quando sua repetição causar vazamento.

Para faturamento, use calendário consistente, distinguindo zero real de ausência de dados. Faça backtesting com janelas móveis/expansivas; compare último valor e baseline sazonal. Avalie MAE, RMSE e WAPE quando o denominador for válido. Não use MAPE indiscriminadamente com zeros. Calcule defasagens sem acessar futuro e gere intervalos somente com método definido e cobertura avaliada.

Para churn, defina data de referência, observação, horizonte e rótulos ainda não maduros. Use divisão temporal e atributos disponíveis na data de referência. Compare regressão logística e árvores. Avalie PR-AUC, ROC-AUC quando definidas, precisão, revocação, F1 e calibração. Selecione limiar na validação por custo/capacidade operacional, nunca no teste final. Classe única invalida métricas que exigem ambas as classes.

Para segmentação, declare população e recência; prepare RFM ou variáveis justificadas, escale e compare KMeans com alternativas pertinentes. Avalie silhouette quando definida, estabilidade e utilidade dos perfis. Clusters não representam automaticamente classes verdadeiras ou propensão de compra.

Use scikit-learn como base; adicione XGBoost quando justificável. Limite Optuna por tempo/trials e mantenha divisões temporais válidas. Não reutilize o teste na otimização. Se dependências opcionais falharem, preserve baseline e alternativa scikit-learn com limitação explícita.

Registre no MLflow parâmetros, seed, código/revisão, hash/versão dos dados, splits, métricas por janela, pipeline e esquema de atributos. Só promova candidato compatível e validado contra baseline. Sem servidor, registre artefatos locais e declare que tracking MLflow não ocorreu. Não carregue pickle/joblib de origem não confiável.

Use SHAP com background de treino e amostra limitada; registre classe e transformação explicadas. Se indisponível, aplique importância por permutação e identifique corretamente o método. Explicação não prova causalidade. Monitore freshness, drift e desempenho após maturação dos rótulos. Com poucos dados, entregue pipeline verificável e declare ausência de previsão validada.
