param([switch]$Execute)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
docker compose exec -T n8n n8n import:workflow --separate --input=/workflows/
if ($LASTEXITCODE -ne 0) { throw 'Importação n8n falhou; nenhum sucesso foi presumido.' }
docker compose exec -T n8n n8n import:workflow --separate --input=/workflows/docker-backend/
if ($LASTEXITCODE -ne 0) { throw 'Importação do backend n8n falhou.' }
if ($Execute) {
    foreach ($id in @('pbi-etl','pbi-predictive','pbi-insights','pbi-quality')) {
        docker compose exec -T n8n n8n execute --id $id
        if ($LASTEXITCODE -ne 0) { throw "Workflow $id falhou." }
    }
}
Write-Host 'Workflows importados. Publique os agendamentos no editor após revisar horários.'
