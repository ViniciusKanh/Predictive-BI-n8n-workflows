param([ValidateSet('Native','Docker')][string]$Mode = 'Native')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
if ($Mode -eq 'Docker') {
    # Para somente serviços deste Compose; mantém containers e todos os volumes.
    docker compose stop
    exit
}
$pidFile = Join-Path $projectRoot '.runtime\api.pid'
if (Test-Path -LiteralPath $pidFile) {
    $servicePid = [int](Get-Content -LiteralPath $pidFile)
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$servicePid" -ErrorAction SilentlyContinue
    if ($process -and $process.CommandLine -like '*scripts/serve.py*' -and $process.ExecutablePath -like '*Predictive-BI*') {
        Stop-Process -Id $servicePid
    } else { Write-Host 'Nenhum processo correspondente ao servidor deste projeto foi encerrado.' }
}
$pgCtl = Get-Command pg_ctl -ErrorAction SilentlyContinue
$cluster = Join-Path $projectRoot '.runtime\postgres'
if ($pgCtl -and (Test-Path -LiteralPath "$cluster\PG_VERSION")) {
    & $pgCtl.Source status -D $cluster 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { & $pgCtl.Source stop -D $cluster -m fast -w }
}
Write-Host 'Dados, artefatos e volumes preservados. Ollama compartilhado não foi encerrado.'
