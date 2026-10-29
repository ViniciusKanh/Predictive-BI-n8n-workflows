param(
    [ValidateSet('Native','Docker')][string]$Mode = 'Native',
    [switch]$SkipTraining,
    [switch]$RestrictedLoop,
    [switch]$Foreground,
    [ValidateSet('Existing','SQLite','PostgreSQL')][string]$Database = 'Existing',
    [ValidateRange(1024,65535)][int]$Port = 8100
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
& "$PSScriptRoot\Initialize-Environment.ps1"
if ($Mode -eq 'Docker') {
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Configuração Compose inválida.' }
    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Engine indisponível; os dados existentes foram preservados.' }
    docker compose up -d --build
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível iniciar o Compose; verifique os logs do projeto.' }
    $task = if ($SkipTraining) { 'etl' } else { 'all' }
    docker compose exec -T api python scripts/bootstrap.py --task $task
    if ($LASTEXITCODE -ne 0) { throw 'A inicialização dos dados/modelos falhou.' }
    Write-Host 'Dashboard: http://127.0.0.1:5180 | API: http://127.0.0.1:8100/docs'
    Write-Host 'n8n: http://127.0.0.1:5680 | MLflow: http://127.0.0.1:5010'
    exit
}
New-Item -ItemType Directory -Force '.runtime' | Out-Null
$baseUrl = "http://127.0.0.1:$Port"
function Test-PredictiveReady {
    try {
        $health = Invoke-RestMethod -Uri "$baseUrl/health" -TimeoutSec 2 -ErrorAction Stop
        return ($health.application -eq 'predictive-bi' -and $health.status -eq 'ok')
    } catch { return $false }
}
if (Test-PredictiveReady) {
    Write-Host "API respondeu ao healthcheck: $baseUrl"
    return
}
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível criar o ambiente isolado.' }
}
& $python -c 'import fastapi,uvicorn,pandas,sklearn,psycopg,httpx,dotenv'
if ($LASTEXITCODE -ne 0) {
    python -m pip --python .venv install -r requirements.txt --retries 1
    if ($LASTEXITCODE -ne 0) { throw 'Dependências básicas indisponíveis. Não foi alterada a instalação global.' }
}
if (-not (Test-Path -LiteralPath 'frontend\node_modules\vite')) {
    Push-Location frontend
    try { npm.cmd install --no-audit --no-fund; if ($LASTEXITCODE -ne 0) { throw 'Instalação frontend falhou.' } }
    finally { Pop-Location }
}
$buildOutput = Get-Item -LiteralPath 'frontend\dist\index.html' -ErrorAction SilentlyContinue
$buildInputs = @(Get-ChildItem frontend\src -Recurse -File)
$buildInputs += @(Get-Item frontend\package.json,frontend\vite.config.ts,frontend\index.html)
$needsBuild = (-not $buildOutput) -or @($buildInputs | Where-Object { $_.LastWriteTimeUtc -gt $buildOutput.LastWriteTimeUtc }).Count -gt 0
if ($needsBuild) {
    Push-Location frontend
    try { npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw 'Build do dashboard falhou.' } }
    finally { Pop-Location }
} else { Write-Host 'Build existente reutilizado.' }
# Reutiliza somente o cluster exclusivo deste projeto, se ele já foi inicializado.
$pgCtl = Get-Command pg_ctl -ErrorAction SilentlyContinue
$cluster = Join-Path $projectRoot '.runtime\postgres'
$usePostgres = $Database -eq 'PostgreSQL'
if ($Database -eq 'Existing' -and (Test-Path -LiteralPath '.runtime\local.env')) {
    $usePostgres = [bool](Select-String -LiteralPath '.runtime\local.env' -Pattern '^DATABASE_URL=postgresql' -Quiet)
}
if ($usePostgres -and $pgCtl -and (Test-Path -LiteralPath "$cluster\PG_VERSION")) {
    & $pgCtl.Source status -D $cluster 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        & $pgCtl.Source start -D $cluster -l "$projectRoot\.runtime\postgres.log" -o '-p 55432 -h 127.0.0.1' -w
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Cluster local não iniciou; o bootstrap verificará o fallback.' }
    }
}
$task = if ($SkipTraining) { 'etl' } else { 'all' }
$databaseMode = switch ($Database) { 'SQLite' { 'sqlite' }; 'PostgreSQL' { 'configured' }; default { 'existing' } }
if ($Database -eq 'SQLite') {
    $sqliteUrl = 'sqlite:///' + (Join-Path $projectRoot 'data\demo.db')
    [IO.File]::WriteAllText((Join-Path $projectRoot '.runtime\local.env'), "DATABASE_URL=$sqliteUrl`n", (New-Object Text.UTF8Encoding $false))
}
$reuseData = $SkipTraining -and $Database -ne 'PostgreSQL' -and (Test-Path -LiteralPath 'data\manifest.json') -and (Test-Path -LiteralPath '.runtime\local.env')
if ($reuseData) {
    Write-Host 'Base e modelos existentes preservados; carga e treino nao foram repetidos.'
} else {
    & $python -X utf8 scripts/bootstrap.py --allow-sqlite-fallback --database-mode $databaseMode --task $task
    if ($LASTEXITCODE -ne 0) { throw 'Carga/treinamento falhou; consulte a saída acima.' }
}
if ($RestrictedLoop -or (Test-Path -LiteralPath '.runtime\restricted-loop')) { $env:PBI_RESTRICTED_LOOP = '1' }
$localDatabaseLine = Get-Content -LiteralPath '.runtime\local.env' | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
$previousDatabaseUrl = $env:DATABASE_URL
if ($localDatabaseLine) { $env:DATABASE_URL = $localDatabaseLine.Substring(13) }
if ($Foreground) {
    try {
        Write-Host "Iniciando em primeiro plano: $baseUrl (Ctrl+C para parar)."
        & $python -u -X utf8 scripts/serve.py --port $Port
        if ($LASTEXITCODE -ne 0) { throw 'A API nao iniciou; consulte a mensagem acima. Nenhum processo existente foi encerrado.' }
    } finally { $env:DATABASE_URL = $previousDatabaseUrl }
    return
}
try {
    $process = Start-Process -FilePath $python -ArgumentList @('-u','-X','utf8','scripts/serve.py','--port',"$Port") -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "$projectRoot\.runtime\api-$Port.log" -RedirectStandardError "$projectRoot\.runtime\api-$Port.err.log"
} finally { $env:DATABASE_URL = $previousDatabaseUrl }
$deadline = [DateTime]::UtcNow.AddSeconds(40)
do {
    if (Test-PredictiveReady) { Write-Host "Dashboard e API verificados: $baseUrl | $baseUrl/docs"; return }
    $process.Refresh()
    if ($process.HasExited) { break }
    Start-Sleep -Milliseconds 500
} while ([DateTime]::UtcNow -lt $deadline)
throw "A API nao confirmou disponibilidade. Consulte .runtime\api-$Port.err.log ou use -Foreground -Port 8101."
