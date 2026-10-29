$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
& '.\.venv\Scripts\python.exe' -X utf8 scripts/bootstrap.py --allow-sqlite-fallback --task train
if ($LASTEXITCODE -ne 0) { throw 'Treinamento falhou.' }
& '.\.venv\Scripts\python.exe' -X utf8 scripts/bootstrap.py --allow-sqlite-fallback --task infer
if ($LASTEXITCODE -ne 0) { throw 'Inferência falhou.' }
