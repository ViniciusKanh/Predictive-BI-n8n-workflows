# Operação e recuperação

## Persistência

Os arquivos `data/`, `artifacts/`, `.runtime/` e `.env` são locais e excluídos do Git. O Compose usa volumes próprios `predictive-bi_postgres_data`, `predictive-bi_n8n_data` e `predictive-bi_mlflow_data`, com nomes definidos pelo projeto Compose. Nenhum script executa prune, down -v, truncate ou exclusão de diretórios de dados.

Faça backup consistente do PostgreSQL com pg_dump e preserve `.env`, especialmente a chave n8n. Para SQLite, pare os jobs e use a API de backup do SQLite ou pare a API antes de copiar o banco. Não copie arquivos de um cluster PostgreSQL ativo como substituto de backup lógico.

## Modos nativo e Docker

No modo Docker, PostgreSQL é a base principal; n8n usa um banco próprio no mesmo servidor, e MLflow persiste metadados SQLite e artefatos em seu volume dedicado. A API e o MLflow usam a mesma imagem Python, com comandos diferentes. O frontend é um build estático servido por Nginx com proxy interno para FastAPI.

No modo nativo, `Start.ps1` reaproveita o cluster exclusivo em `.runtime/postgres` se existir. Em outra máquina, instale/aponte um PostgreSQL válido pelo `.env`; não se tenta instalar um serviço global. Sem PostgreSQL acessível, o bootstrap pode operar no fallback SQLite explicitamente identificado. Esse fallback não comprova sintaxe, concorrência ou desempenho em PostgreSQL.

Uma sessão sem rede pode reaproveitar bibliotecas previamente instaladas. Isso foi necessário nesta execução. Uma instalação hermética deve usar um virtualenv sem acesso aos pacotes globais e instalar `requirements.txt`; não há alteração silenciosa dos pacotes globais.

`Stop.ps1` usa o PID registrado e confere o comando e caminho antes de encerrar a API. O cluster só é parado usando seu caminho absoluto. O Ollama compartilhado não é encerrado. Nenhum processo de outro projeto deve ser parado para liberar portas. Se houver conflito, registre e escolha outra porta em uma configuração local consistente.

## Restrições observadas

- PyPI não resolveu via DNS na sessão; a instalação online de dependências falhou.
- Docker CLI/Compose existem, mas o pipe dockerDesktopLinuxEngine não estava disponível. A tentativa de iniciar Docker Desktop informou ausência da chave de registro esperada.
- O PostgreSQL 18.4 iniciou em 127.0.0.1:55432, mas a conexão de cliente falhou com WinError 10013; não foi considerada uma carga PostgreSQL aprovada.
- Ollama iniciou listener em 11434, porém chamadas a seus endpoints também foram bloqueadas. Nenhum modelo foi baixado.
- O loop padrão asyncio no Windows depende de socketpair TCP; ele ficou bloqueado na mesma restrição. O modo `PBI_RESTRICTED_LOOP=1` substitui apenas a sinalização interna por polling de 20 ms. Não abre acesso de rede proibido, não altera firewall e não libera conexões PostgreSQL/Ollama.
- A API iniciou com esse loop alternativo em 8100. Testes de endpoints usaram o mesmo ASGI em processo. A inspeção visual pelo navegador permaneceu bloqueada; portanto o build não foi apresentado como validação visual.
- Ruff e MLflow não estavam instalados. Registro MLflow e lint Ruff continuam pendentes; compilação Python, testes e checagem TypeScript foram executados.

## Workflows

Importação e execução CLI ficam em Import-N8n.ps1. Os quatro workflows têm IDs estáveis, dois gatilhos (manual/diário), chamadas HTTP, polling a cada dois segundos, timeout por etapa e tratamento explícito de falha. O treinamento é diário por padrão às 3h; para operação real, ajuste a frequência ao custo e à chegada de dados. ETL às 2h, insights às 4h e qualidade às 5h, no timezone America/Sao_Paulo. O treinamento encadeia inferência; ETL encadeia qualidade.

Nenhum agendamento foi ativado nesta sessão. Um serviço indisponível não gera execução fictícia. O histórico do dashboard identifica execuções API/CLI; não representa confirmação de execução pelo n8n.

## MLflow e Ollama

MLflow: com a stack completa iniciada, reexecute o treinamento para gerar os runs no servidor. Os JSONs locais anteriores conservam o status pending e não são retroativamente apresentados como rastreados. Os joblib são para carga apenas de artefatos produzidos e confiáveis deste projeto.

Ollama: verifique disponibilidade e modelos pelo endpoint de status da API. O código prioriza Qwen local já disponível e não faz pull. Modelo indisponível, timeout ou JSON inválido produzem resumo determinístico identificado. Perguntas sem evidências retornam insuficiência. Nunca se troca para uma API paga.

## Recuperação de falhas

Uma falha de ETL não avança o watermark. Corrija a origem e reexecute a carga; hashes e chave primária evitam duplicação. Jobs interrompidos são sinalizados ao reiniciar a API. Depois de falha de treinamento, os resultados já persistidos permanecem acessíveis; a publicação dos três módulos não é uma promoção atômica de conjunto. Para uso produtivo, acrescente versionamento de bundle de modelos e promoção transacional.

A implantação é local de demonstração, vinculada a loopback e rede interna Docker. Não a publique na internet sem autenticação, autorização, TLS e limites operacionais apropriados. Não há exposição pública nem alteração dessas proteções nesta implementação.
