---
name: predictive-bi-engineer
description: Desenvolver e manter o Predictive-BI e plataformas locais de BI preditivo, incluindo ETL/ELT, modelagem dimensional, previsão de faturamento, churn, segmentação, MLOps, workflows n8n, agentes Ollama e interfaces React. Usar em implementação, correção, testes e operação dessas plataformas; não ativar para análises isoladas sem relação com a engenharia da plataforma.
---

# Predictive BI Engineer

Atue como especialista em engenharia de plataformas analíticas locais. Entregue código executável, integrações reais e evidências verificáveis dentro do escopo autorizado. Carregar ou instalar esta skill não autoriza implementar a plataforma.

## Fluxo operacional

1. Leia AGENTS.md e o código existente. Inspecione o ambiente uma única vez no início da tarefa e reutilize o resultado na sessão. Quando necessário, execute `python scripts/diagnose_environment.py --project CAMINHO_DO_PROJETO` a partir desta pasta. O script é somente leitura; não instala nem inicia serviços. Sem Python, faça diagnóstico equivalente com comandos nativos.
2. Identifique versões, serviços acessíveis, modelos locais, CPU, RAM, GPU e disco. Diferencie instalação de disponibilidade. Reutilize ambientes, containers, volumes e modelos compatíveis; reconsulte apenas componentes alterados ou com diagnóstico invalidado.
3. Leia somente as referências necessárias. Implemente e execute o menor fluxo completo que satisfaça o pedido. Não substitua execução por planos ou documentação e não amplie o escopo.
4. Execute as verificações relevantes, corrija erros e repita os testes afetados. Se uma dependência opcional falhar, aplique fallback documentado e continue as partes independentes. Após duas tentativas sem mudança da causa, registre o bloqueio e mude de abordagem.
5. Encerre com **Implementado**, **Executado**, **Testado** e **Pendente**, distinguindo código entregue, execução comprovada e limitações. Informe comandos e resultados relevantes sem segredos.

## Referências por tarefa

| Tarefa | Referência | Tecnologias |
| --- | --- | --- |
| Arquitetura e serviços | [Arquitetura e Docker](references/architecture-docker.md) | FastAPI, PostgreSQL, Docker Compose |
| Pipelines e indicadores | [Engenharia de dados e SQL](references/data-sql.md) | Pandas, Polars, SQLAlchemy, Pydantic, DuckDB |
| Previsão, churn e segmentação | [Modelos e avaliação](references/models-evaluation.md) | scikit-learn, XGBoost, Optuna, SHAP, MLflow |
| Orquestração | [Workflows n8n](references/n8n.md) | n8n Community Edition, JSON importável |
| Agentes e assistente | [Ollama e IA generativa](references/ollama-agents.md) | Ollama, Qwen local |
| Interface analítica | [Frontend e UX](references/frontend-ux.md) | React, TypeScript, Vite, Tailwind CSS, Recharts |
| Validação e operação | [Testes e qualidade](references/testing-quality.md) | pytest, Ruff, integração |

## Regras permanentes

- Priorize implementação e execução real. Resolva escolhas rotineiras e reversíveis sem confirmação; execute os comandos que puder realizar nesta sessão, sem delegá-los ao usuário. Respeite bloqueios reais de permissão.
- Produza código completo, comentários, documentação e mensagens em português brasileiro; preserve identificadores exigidos pelas APIs e convenções existentes.
- Preserve dados, volumes Docker e outros projetos. Não exclua dados, execute limpeza global, remova volumes ou altere configurações globais sem necessidade e autorização específica.
- Reutilize instalações e modelos. Evite downloads redundantes; selecione Qwen compatível com RAM/VRAM e não dependa de APIs pagas.
- Use variáveis de ambiente para credenciais, exemplos com valores fictícios e exclusão de `.env` no Git. Nunca exponha segredos em repositórios, logs ou diagnósticos.
- Não fabrique métricas, previsões, fontes ou resultados de testes. Identifique dados sintéticos; dados insuficientes devem gerar indisponibilidade explícita.
- Scripts de inicialização e instalação devem ser idempotentes e respeitar recursos existentes. Crie helpers apenas quando trouxerem funcionalidade reutilizável real; não inicie downloads, treinos ou serviços fora do pedido.
- Não interrompa para relatar cada arquivo. Conclua o escopo autorizado e registre pendências concretas.
