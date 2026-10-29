# Testes e qualidade

Use pytest, Ruff e testes de integração em Python; verifique tipos e build no frontend. Execute comandos aplicáveis ao que existe; instalar a skill não exige instalar a stack. Quando precisar confirmar APIs e versões, consulte documentação primária compatível com o ambiente.

Priorize invariantes reais: reexecutar lote não duplica; rollback não avança watermark; chegada tardia é incorporada; join preserva faturamento; atributos não contêm futuro; agente rejeita valores sem evidência; falha de workflow não repete efeitos. Teste isolamento entre treino, validação e teste. Evite testes que apenas espelhem a implementação.

Teste PostgreSQL, FastAPI, n8n e Ollama reais quando disponíveis, com recursos isolados e sem apagar dados ou disparar automações externas. Mocks complementam integrações; testes pulados não contam como aprovados. DuckDB/SQLite não comprovam comportamento específico do PostgreSQL.

Documente configuração por variáveis, instalação, inicialização, healthchecks, ETL, treino, inferência, importação e recuperação de falhas quando esses componentes forem implementados. Scripts precisam de idempotência, pré-requisitos e exit codes úteis. Exemplos não devem conter credenciais reais; mantenha dados privados e artefatos pesados fora do Git conforme necessidade.

No relatório final, registre implementado, executado, testado e pendente com comandos, resultados e causas concretas. Após checks relevantes passarem, só repita verificações por mudança, falha ou dúvida ainda aberta.
