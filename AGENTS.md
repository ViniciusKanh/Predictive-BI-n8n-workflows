# Predictive-BI — instruções permanentes

Projeto: `C:\dev\Predictive-BI`. Plataforma local de BI preditivo, engenharia de dados, Machine Learning, n8n e IA generativa via Ollama.

## Skill especializada

Use `predictive-bi-engineer` no desenvolvimento, correção, testes e operação deste projeto. Leia primeiro `skills/predictive-bi-engineer/SKILL.md` nesta raiz e somente as referências relevantes. Caminho absoluto: `C:\dev\Predictive-BI\skills\predictive-bi-engineer\SKILL.md`.

A skill está disponível localmente por este AGENTS.md. Se o catálogo global não a apresentar, leia o arquivo diretamente; não dependa do registro global. Invocação pretendida: `$predictive-bi-engineer`.

## Regras

- Respeite o escopo: criar/carregar a skill não autoriza iniciar a plataforma.
- Priorize implementação e execução real; produza código completo e comentários/documentação em português brasileiro.
- Inspecione ambiente e projeto uma única vez no início da tarefa; reutilize o resultado e reconsulte somente componentes alterados ou com diagnóstico invalidado.
- Detecte Docker, Ollama, Python e recursos. Reutilize instalações, modelos, ambientes e volumes; evite downloads redundantes.
- Resolva escolhas rotineiras e reversíveis sem confirmação intermediária e execute os comandos ao seu alcance.
- Preserve dados, volumes e outros projetos. Não exclua dados nem altere configurações globais sem necessidade e autorização específica.
- Use credenciais por variáveis de ambiente, exclua `.env` do Git e nunca exponha segredos.
- Implemente ETL/ELT incremental, idempotente e auditável; declare grão e regras de indicadores.
- Use baselines, validação temporal, explicabilidade e rastreabilidade; impeça vazamento e não fabrique métricas/previsões.
- Agentes respondem apenas com evidências verificáveis; não dependa de APIs pagas.
- Execute verificações, corrija erros e documente fallbacks de dependências opcionais. Testes pulados não são integrações aprovadas.
- Não interrompa para anunciar cada arquivo; encerre com **Implementado**, **Executado**, **Testado** e **Pendente**.

## Implementação e operação

- O dashboard usa workflows n8n como backend por padrão. Preserve essa rota; Python permanece worker de banco/ETL/ML. O modo Python direto deve ser uma escolha explícita, nunca fallback silencioso.
- Backends HTTP: `workflows/local/backend-data.json` e `backend-actions.json`; regras comerciais em `workflows/code/analytics.cjs`. Regenere os JSONs após alterar o código-fonte. Publicação dos webhooks e importação CLI são verificações distintas. Consulte `docs/n8n-backend.md`.

- Backend em `backend/`; interface em `frontend/`; workflows importáveis em `workflows/`; comandos em `scripts/`.
- Configuração principal em `.env`. No modo nativo, `.runtime/local.env` registra o banco realmente selecionado; containers ignoram esse fallback.
- PostgreSQL é o destino principal. SQLite só pode ser usado com fallback explícito e identificação na API, interface e relatório; testes SQLite não comprovam integração PostgreSQL.
- Não sobrescreva os CSVs ou `data/manifest.json` para regenerar demonstrações. Use outro DATA_DIR para novos cenários, preservando o histórico.
- Executar a carga: `.venv/Scripts/python.exe scripts/bootstrap.py --allow-sqlite-fallback --task etl`; treinar: `--task train`; inferir: `--task infer`.
- Testes: `.venv/Scripts/python.exe -m pytest -q --basetemp=.runtime/pytest`. Frontend: `npm run build` dentro de `frontend/`. Compose: `docker compose config --quiet`.
- Iniciar/parar com `scripts/Start.ps1` e `scripts/Stop.ps1`. Não pare processos fora deste projeto para liberar portas.
- A execução desta sessão teve restrições de DNS e conexões TCP. Revalide os componentes bloqueados quando o ambiente mudar; não perpetue esse diagnóstico como uma característica da máquina.
- O loop opcional em `backend/runtime_loop.py` substitui somente a sinalização interna do asyncio no Windows. Não altera política de rede, firewall ou permissões.
- Métricas na documentação descrevem a execução inicial; após novos treinos, use resultados persistidos e atualize a documentação quando pertinente.
