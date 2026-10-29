param(
    [ValidateRange(1024,65535)][int]$Port = 5678,
    [string]$ApiUrl = 'http://127.0.0.1:8101',
    [switch]$PrepareOnly,
    [switch]$ImportOnly
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$apiAddress = $null
if (-not [Uri]::TryCreate($ApiUrl, [UriKind]::Absolute, [ref]$apiAddress) -or
    $apiAddress.Scheme -ne 'http' -or $apiAddress.Host -notin @('127.0.0.1','localhost') -or
    $apiAddress.UserInfo -or $apiAddress.Query -or $apiAddress.Fragment -or $apiAddress.AbsolutePath -ne '/') {
    throw 'ApiUrl deve ser um endereco HTTP local sem credenciais, caminho ou query.'
}
$ApiUrl = $ApiUrl.TrimEnd('/')
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Ambiente Python do projeto nao encontrado.' }
$workflowDirectory = Join-Path $projectRoot 'workflows\local'
& $python -X utf8 scripts/generate_workflows.py --base-url $ApiUrl --output $workflowDirectory --include-master
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel preparar os workflows.' }
& $python -X utf8 scripts/generate_n8n_backend.py --api-url $ApiUrl --output $workflowDirectory
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel preparar o backend n8n.' }
if ($PrepareOnly) { Write-Host "Sete workflows preparados em $workflowDirectory"; return }
$health = $null
try {
    $health = Invoke-RestMethod -Uri "$ApiUrl/health" -TimeoutSec 5
} catch {
    Write-Warning "API indisponivel em $ApiUrl. Detalhe: $($_.Exception.Message)"
    Write-Warning 'O editor n8n pode iniciar; os workflows dependentes de Python so funcionarao quando a API estiver ativa em outro terminal.'
}
if ($null -ne $health -and ($health.application -ne 'predictive-bi' -or $health.status -ne 'ok')) {
    throw "O servico em $ApiUrl nao confirmou a identidade e o estado do Predictive BI. Confira a porta ou reinicie a API deste projeto."
}
$running = $null
try {
    $running = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/healthz" -TimeoutSec 2
} catch {
    # Sem resposta saudavel, a inicializacao abaixo apresentara eventuais conflitos.
}
if ($running.status -eq 'ok') {
    Write-Host "n8n ja esta ativo: http://localhost:$Port"
    Write-Host 'Instancia existente preservada. Os JSONs foram preparados em workflows\local; importe pelo editor e publique os dois backends HTTP.'
    if ($ImportOnly) { throw 'A importacao CLI nao foi executada porque o n8n esta ativo. Importe pelo editor para preservar a instancia em uso.' }
    return
}
& "$PSScriptRoot\Initialize-Environment.ps1"
$node = (Get-Command node -ErrorAction Stop).Source
$nodeVersion = [version]((& $node -p 'process.versions.node') | Select-Object -Last 1)
if ($nodeVersion -lt [version]'20.19.0' -or $nodeVersion.Major -gt 24) { throw 'Esta instalacao fixada requer Node.js entre 20.19 e 24.x.' }
$toolRoot = Join-Path $projectRoot '.runtime\n8n-tool'
$n8nEntry = Join-Path $toolRoot 'node_modules\n8n\bin\n8n'
$globalN8n = Get-Command n8n.cmd -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $n8nEntry) {
    $n8nCommand = $node
    $n8nPrefix = @($n8nEntry)
    $managedLocal = $true
} elseif ($globalN8n) {
    $n8nCommand = $globalN8n.Source
    $n8nPrefix = @()
    $managedLocal = $false
} else {
    Write-Host 'Instalando n8n Community 2.45.6 somente dentro do projeto (primeira execucao).'
    $cache = Join-Path $projectRoot '.runtime\npm-cache'
    npm.cmd install --prefix $toolRoot n8n@2.45.6 --no-audit --no-fund --fetch-retries=1 --fetch-timeout=30000 --cache $cache
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $n8nEntry)) {
        throw 'Instalacao local do n8n falhou. Verifique a mensagem npm; workflows e dados existentes foram preservados.'
    }
    $n8nCommand = $node
    $n8nPrefix = @($n8nEntry)
    $managedLocal = $true
}
if ($managedLocal) {
    & "$PSScriptRoot\Repair-N8n.ps1"
} else {
    $globalRoot = Split-Path $globalN8n.Source -Parent
    & $node "$PSScriptRoot\check_n8n_sqlite.cjs" $globalRoot
    if ($LASTEXITCODE -ne 0) { throw 'SQLite da instalacao global indisponivel; ela nao foi modificada. Use uma instalacao local do projeto.' }
}
$keyLine = Get-Content -LiteralPath '.env' -Encoding UTF8 | Where-Object { $_ -match '^N8N_ENCRYPTION_KEY=' } | Select-Object -First 1
if (-not $keyLine) { throw 'N8N_ENCRYPTION_KEY nao definida no .env.' }
$localSettings = @{
    N8N_USER_FOLDER = (Join-Path $projectRoot '.runtime\n8n-home')
    N8N_ENCRYPTION_KEY = $keyLine.Split('=',2)[1].Trim()
    DB_TYPE = 'sqlite'
    N8N_HOST = 'localhost'
    N8N_LISTEN_ADDRESS = '127.0.0.1'
    N8N_PORT = "$Port"
    N8N_PROTOCOL = 'http'
    N8N_SECURE_COOKIE = 'false'
    N8N_EDITOR_BASE_URL = "http://localhost:$Port"
    WEBHOOK_URL = "http://localhost:$Port/"
    N8N_DIAGNOSTICS_ENABLED = 'false'
    N8N_VERSION_NOTIFICATIONS_ENABLED = 'false'
    N8N_PERSONALIZATION_ENABLED = 'false'
    N8N_TEMPLATES_ENABLED = 'false'
    GENERIC_TIMEZONE = 'America/Sao_Paulo'
    TZ = 'America/Sao_Paulo'
}
$previous = @{}
foreach ($name in $localSettings.Keys) {
    $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process')
    [Environment]::SetEnvironmentVariable($name,$localSettings[$name],'Process')
}
try {
    Write-Host 'Importando pipelines, fluxo completo e dois backends HTTP; nenhum workflow sera publicado automaticamente.'
    & $n8nCommand @n8nPrefix import:workflow --separate "--input=$workflowDirectory"
    $imported = $LASTEXITCODE -eq 0
    if (-not $imported) {
        Write-Warning 'Importacao pendente. Apos criar o usuario inicial, importe complete.json pelo editor do n8n.'
        if ($ImportOnly) { throw 'Importacao nao concluida; consulte a saida do n8n.' }
    }
    if ($ImportOnly) { Write-Host 'Workflows importados sem iniciar um segundo servidor.'; return }
    Write-Host "Iniciando n8n local: http://localhost:$Port"
    Write-Host 'Publique Backend de leitura e Backend de acoes para conectar o dashboard. O fluxo completo pode ser executado manualmente.'
    & $n8nCommand @n8nPrefix start
    if ($LASTEXITCODE -ne 0) { throw 'O n8n encerrou com erro; consulte a mensagem acima.' }
} finally {
    foreach ($name in $previous.Keys) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
}
