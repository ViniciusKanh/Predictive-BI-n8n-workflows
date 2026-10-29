# Verificação da publicação — 29/10/2026

Esta revisão prepara código e documentação para Predictive-BI-n8n-workflows. Dados, bancos, credenciais e instalações locais não fazem parte da publicação.

## Escopo

- README expandido com instalação nativa e Docker, origem dos dados, indicadores, contratos, sete workflows e guia das nove páginas.
- Catálogo gerado dos nós e conexões reais em `workflow-catalog.md`.
- Métricas extraídas por consulta somente leitura ao banco em `reference-results.json`.
- Utilitário opcional de mídia com instantes e intervalos explícitos.
- Exclusões de ambientes, segredos, bancos e backups; normalização de texto em LF.

## Evidências e limites

Resultados desta revisão são registrados após pytest, TypeScript/Vite, sintaxe Python e configuração Compose. A ferramenta de mídia foi exercitada em gravação sintética de três segundos em `.runtime`, sem publicar esse material como a gravação do autor.

A transferência inicial dos anexos falhou por rede. Em seguida, o autor disponibilizou os originais em Downloads. Foram produzidos 11 prints e quatro GIFs a partir da gravação real; o PNG original foi incorporado ao menu, favicon e README. Os originais foram preservados. A mídia e seus intervalos estão em docs/media/media-manifest.json.

Git direto não resolveu `github.com` no processo local. A publicação pode usar o conector GitHub autorizado, preservando exclusões e verificando o commit remoto. Isso não implica que DNS ou rede local estejam corrigidos.

Não foram iniciados novos treinos ou agendamentos. O tracking MLflow segue pendente no resultado de referência. A importação isolada dos backends no n8n havia sido comprovada, mas não comprova publicação/execução atual dos webhooks. Não houve nova validação integrada de PostgreSQL, Ollama ou Docker Engine.

## Checks executados nesta revisão

| Verificação | Resultado |
| --- | --- |
| pytest | 32 testes aprovados em 16,20 segundos |
| TypeScript e Vite | Build concluído, 2.310 módulos transformados |
| Docker Compose | Configuração validada com exit code 0; stack não iniciada |
| Ferramenta de mídia | Dois prints e corte de 1 segundo em vídeo sintético isolado |
| Sintaxe Python | export_demo_media.py compilado com sucesso |
| Ruff | Não executado: pacote ausente no ambiente atual |

## Revisão visual da mídia

As barras do navegador e os favoritos foram removidos. O vídeo mostra o estado da aplicação na gravação; não comprova uma nova execução nem contém a integração posterior do logo. GIFs usam resolução reduzida, três quadros por segundo e nenhum áudio.
