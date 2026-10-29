# Arquitetura e Docker

Separe API, ingestão, transformação, treinamento/inferência, frontend e orquestração conforme a tarefa real. FastAPI expõe contratos Pydantic; SQLAlchemy gerencia sessões e transações; PostgreSQL mantém dados operacionais e dimensionais; DuckDB atende processamento analítico local. Não construa serviços que o pedido não exige.

Antes de operar Compose, identifique containers, portas, redes e volumes do projeto. Use nome de projeto próprio, healthchecks e versões compatíveis fixadas após verificar o ambiente. Valide com `docker compose config --quiet`, sem imprimir valores interpolados. Não derrube containers de outros projetos nem use `down -v` como rotina.

Persista PostgreSQL, dados n8n e artefatos MLflow. Mantenha a chave de criptografia do n8n estável em variável de ambiente: perdê-la impede recuperar credenciais. Dentro de containers, use DNS de serviços; no navegador, URLs alcançáveis pelo host. Para Ollama existente no Windows, avalie `host.docker.internal` antes de instalar outro servidor.

Use migrações versionadas e não recrie tabelas para alterar esquemas. Configure pools, limites e retentativas finitas, logs com identificador de execução e desligamento gracioso. Exponha serviços locais em loopback por padrão; restrinja CORS ao frontend.

Sem Docker, permita execução local e DuckDB quando semântica e concorrência forem compatíveis. Declare que isso não comprova integração PostgreSQL/n8n. Scripts de inicialização só devem ser criados quando houver serviços reais a iniciar.
