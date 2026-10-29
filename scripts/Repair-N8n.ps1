param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$toolRoot = Join-Path $projectRoot '.runtime\n8n-tool'
$checker = Join-Path $PSScriptRoot 'check_n8n_sqlite.cjs'
$node = (Get-Command node -ErrorAction Stop).Source
& $node $checker $toolRoot
if ($LASTEXITCODE -eq 0) { Write-Host 'Driver SQLite do n8n verificado com consulta em memoria.'; return }
if ($CheckOnly) { throw 'SQLite do n8n indisponivel. Execute este script sem -CheckOnly para reparar.' }
if (-not (Test-Path -LiteralPath "$toolRoot\node_modules\n8n\package.json")) {
    throw 'Instale primeiro o n8n com scripts\Start-N8n.ps1.'
}
$cache = Join-Path $projectRoot '.runtime\npm-cache'
Push-Location -LiteralPath $toolRoot
try {
    if (-not (Test-Path -LiteralPath 'node_modules\sqlite3\package.json')) {
        npm.cmd install sqlite3@5.1.7 --save-exact --no-audit --no-fund --fetch-retries=0 --fetch-timeout=15000 --cache $cache
        if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel instalar sqlite3 no ambiente local do n8n.' }
    }
    $npmVersion = [version]((npm.cmd --version) | Select-Object -Last 1)
    if ($npmVersion.Major -ge 12) {
        # Autoriza somente o script da versao instalada do sqlite3, neste package.json.
        npm.cmd approve-scripts sqlite3 --cache $cache
        if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel registrar o script de instalacao do SQLite neste projeto.' }
    }
    Write-Host 'Reconstruindo somente o driver SQLite; nenhum banco ou workflow sera removido.'
    npm.cmd rebuild sqlite3 --foreground-scripts --ignore-scripts=false --fetch-retries=0 --fetch-timeout=15000 --cache $cache
    if ($LASTEXITCODE -ne 0) {
        throw 'Falha ao reconstruir SQLite. Consulte o erro de download/compilacao acima; os dados foram preservados.'
    }
    & $node $checker $toolRoot
    if ($LASTEXITCODE -ne 0) { throw 'O SQLite continua indisponivel; o n8n nao sera iniciado com esse driver.' }
    Write-Host 'Driver SQLite reparado e consulta em memoria aprovada.'
} finally { Pop-Location }
