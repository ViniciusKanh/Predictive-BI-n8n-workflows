# Workflows n8n Community Edition

Entregue JSON importável com name, nodes, connections e settings compatíveis com a versão instalada. Cada nó deve ter ID, nome único, tipo, typeVersion, posição e parâmetros. Use exportações locais ou documentação oficial da versão para contratos; não invente nós. Valide parsing, unicidade, conexões e expressões.

Use Schedule Trigger/Webhook e HTTP Request para chamar a API. Mantenha ETL e ML pesados no backend. Encadeie ingestão, transformação, inferência e registro conforme dependências reais. Propague run_id/idempotency key, limite timeout e retentativas com backoff. Diferencie aceitação HTTP de conclusão e use consulta de status com prazo máximo para jobs longos.

Não exporte senhas, tokens ou conteúdo de credenciais. Documente associação de credenciais à instalação real. Não presuma que variáveis de ambiente estejam liberadas em expressões: isso depende da configuração instalada. Não relaxe configurações globais para contornar restrições.

Use API pública/CLI disponível para importar e executar quando autorizado; não escreva no banco interno. Verifique IDs antes de atualizar para evitar duplicação. Importe inicialmente inativo e faça execução controlada. Ative agendamentos somente quando a automação fizer parte do pedido.

Teste caminho feliz, timeout, erro, reexecução e falha parcial sem duplicação. Sem n8n acessível, entregue JSON validado estruturalmente, teste a API independentemente e declare importação/execução pendentes. Preserve volumes e chave de criptografia.
