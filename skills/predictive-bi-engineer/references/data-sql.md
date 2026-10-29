# Engenharia de dados e SQL

Defina fonte, granularidade, chave natural, atualização, moeda, timezone e regras dos indicadores. Preserve dados brutos rastreáveis e associe lotes a run_id, origem e data de extração. Escolha Pandas, Polars ou DuckDB pelo volume e integração, estimando memória antes de materializar dados.

Use watermark persistente com desempate por chave, sobreposição para chegadas tardias e upsert com restrição única. Confirme o watermark somente após o commit no destino. Reexecutar um lote deve preservar o resultado. Trate deleções da fonte explicitamente. Use staging, transações e proteção contra concorrência; retentativas exigem idempotência.

Audite início/fim, status, watermarks e contagens lidas, rejeitadas, inseridas e atualizadas. Registros rejeitados precisam de motivo e referência sem vazar conteúdo sensível. Valide entradas com Pydantic e integridade com constraints SQL. Teste duplicatas, atrasos e recuperação de falhas.

Declare o grão de cada fato; use dimensões com chaves substitutas, membro desconhecido e SCD tipo 2 quando histórico for necessário. Não misture evento, saldo e snapshot na mesma soma. Evite duplicação em joins um-para-muitos e reconcilie totais com a origem. Defina receita bruta/líquida, cancelamentos, competência/caixa, filtros e denominadores antes de calcular KPIs. Use decimal para dinheiro.

Parametrize SQL e autorize identificadores por lista explícita. Use migrações, índices e planos de execução quando relevantes. DuckDB não substitui automaticamente semântica transacional e concorrência do PostgreSQL.
