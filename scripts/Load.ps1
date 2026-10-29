$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
& '.\.venv\Scripts\python.exe' -X utf8 scripts/bootstrap.py --allow-sqlite-fallback --task etl
if ($LASTEXITCODE -ne 0) { throw 'ETL falhou.' }
& '.\.venv\Scripts\python.exe' -X utf8 scripts/bootstrap.py --allow-sqlite-fallback --task quality
if ($LASTEXITCODE -ne 0) { throw 'Verificação de qualidade falhou.' }
