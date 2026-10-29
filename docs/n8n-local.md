# n8n Community local para o Predictive BI

> A documentação operacional atual está no [README](../README.md), com instalação, publicação dos backends e os sete fluxos. Falhas de instalação registradas abaixo são históricas e não devem ser presumidas como estado atual.

O n8n Community self-hosted permite executar estes workflows sem assinatura n8n Cloud ou API paga. O computador precisa permanecer ligado durante as execuções. A instalação inicial precisa de acesso ao registro npm; depois, os workflows desta demonstração usam somente serviços locais.

## Iniciar

No primeiro terminal PowerShell do VS Code, mantenha a API e o dashboard abertos:

```powershell
cd C:\dev\Predictive-BI
.\scripts\Start.ps1 -Mode Native -Database SQLite -SkipTraining -RestrictedLoop -Foreground -Port 8101
```

Em outro terminal:

```powershell
cd C:\dev\Predictive-BI
.\scripts\Start-N8n.ps1 -ApiUrl http://127.0.0.1:8101
```

O script verifica a API, prepara cinco JSONs, reutiliza n8n existente quando disponível ou instala a versão 2.45.6 dentro de `.runtime/n8n-tool`, importa os arquivos e inicia o editor em **http://localhost:5678**. Não instala pacotes globais e não altera outra instância n8n. Configurações e execuções ficam em `.runtime/n8n-home`, com banco SQLite próprio do n8n. A chave de criptografia é lida do `.env` e não é impressa.

A versão foi fixada na linha 2.x: a documentação atual informa depreciação da instalação npm a partir do n8n 3.0. O Docker Compose entregue continua sendo a alternativa para a stack completa. O modo npm local foi acrescentado para permitir iniciar a automação sem depender do Docker Engine nesta máquina.

Se o PowerShell bloquear scripts, invoque o mesmo arquivo por `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-N8n.ps1 -ApiUrl http://127.0.0.1:8101`. Isso vale apenas para esse processo.

## Executar pelo editor

1. Abra http://localhost:5678 e crie o usuário inicial de administração, se solicitado. Esse usuário é da sua instalação local; não exige contratar n8n Cloud.
2. Abra **Predictive BI | Fluxo completo**.
3. Clique **Execute workflow**. O gatilho manual inicia o ETL, aguarda a conclusão, verifica qualidade, treina modelos, executa inferência e gera insights.
4. Inspecione a saída de cada nó e o histórico **Executions**. O dashboard pode ser atualizado depois da execução.

Se a importação CLI não conseguir associar os arquivos ao usuário antes da configuração inicial, o script informa a pendência e abre o editor. Após configurar o usuário, use **Import from file** no editor e selecione `workflows/local/complete.json`. Os outros quatro arquivos desse diretório permitem executar módulos separadamente.

Workflows são importados sem ativar agendamentos. Para execução diária, publique somente o fluxo completo, após revisar o horário configurado, evitando publicar também todos os agendamentos dos módulos independentes. O timezone é America/Sao_Paulo. O computador, a API e o n8n precisam permanecer em execução.

## Responsabilidades

O n8n executa a orquestração real: gatilhos, chamadas HTTP, dependências, espera, tratamento de falha e registro de execução no seu motor. Python/FastAPI realiza validação, processamento e treinamento nas bibliotecas instaladas. Essa separação permite observar o fluxo no canvas sem tentar instalar toda a stack de ML dentro de um nó Code.

Os nós HTTP chamam `/api/jobs` e consultam `/api/jobs/{id}` até a conclusão, com prazo de dez minutos por etapa. Erros interrompem a execução. O gate de qualidade exige que todas as verificações tenham sido aprovadas antes de continuar. Chaves de idempotência evitam repetir efeitos em retentativas da mesma etapa/execução.

Sem Ollama disponível, insights são gerados em modo determinístico explicitamente identificado. Executar pelo n8n não muda a disponibilidade de Qwen, MLflow ou PostgreSQL.

## Outros endereços e preservação

Use `-ApiUrl http://127.0.0.1:8100` se essa for a API realmente ativa. Use `-Port 5679` se outra instância ocupar 5678; nenhum serviço existente será encerrado. Os JSONs locais são regenerados para a URL informada, mantendo os IDs.

`-PrepareOnly` gera somente os arquivos, sem instalar ou iniciar n8n. `-ImportOnly` importa na base isolada sem iniciar o editor; evite importar por CLI em paralelo a uma instância já aberta. O script preserva a instância e orienta importação pelo editor se detectar serviço na porta.

Para parar, pressione Ctrl+C no terminal do n8n e, separadamente, no terminal da API. Isso preserva dados, configurações, workflows e modelos. Não remova `.runtime/n8n-home` nem troque a chave de criptografia para reiniciar.

## Verificação desta sessão

### SQLite instalado sem o binário nativo

Se o n8n informar que SQLite não está instalado, mesmo com `node_modules/sqlite3` presente, o driver pode estar sem `node_sqlite3.node`. O npm 12 bloqueia scripts de instalação por padrão, incluindo a etapa que baixa/compila esse binário. A mensagem do TypeORM esconde a causa original.

`Start-N8n.ps1` agora verifica o driver a partir da resolução do próprio TypeORM e executa `SELECT 1` em um banco em memória. Quando necessário, `Repair-N8n.ps1` registra somente `sqlite3` na política local `allowScripts` do ambiente do n8n e executa `npm rebuild sqlite3`. Não aprova scripts globalmente, não apaga bancos e não reinstala o projeto inteiro.

Para reparar separadamente:

```powershell
.\scripts\Repair-N8n.ps1
.\scripts\Start-N8n.ps1 -ApiUrl http://127.0.0.1:8101
```

Se o reparo precisar baixar o binário, o terminal deve conseguir acessar GitHub. Se o binário não estiver disponível e a instalação recorrer a compilação, serão necessários os requisitos nativos do node-gyp. Não é feita instalação global desses componentes automaticamente. `Repair-N8n.ps1 -CheckOnly` apenas diagnostica o driver.

Na tentativa de reparo desta sessão, a aprovação local de `sqlite3@5.1.7` foi registrada, mas o download falhou com `ENOTFOUND github.com`; o fallback de compilação também não conseguiu obter os headers do Node. Portanto, o reparo do binário e a execução real do n8n continuam pendentes de conectividade no terminal do usuário.

A tentativa de instalação local falhou com `ENOTFOUND registry.npmjs.org`, e o Docker Engine continuou inacessível. Portanto, os arquivos foram preparados e seus contratos testados, mas importação e execução **no motor n8n** ainda não foram comprovadas. A primeira execução do script em um terminal com rede disponível é necessária para instalar os pacotes que faltam.

Referências oficiais: [edições e hospedagem](https://docs.n8n.io/choose-how-to-use-n8n/), [instalação npm](https://docs.n8n.io/hosting/installation/npm/) e [CLI](https://docs.n8n.io/hosting/cli-commands/).
