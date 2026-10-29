$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath '.env')) {
    function New-LocalSecret([int]$length) {
        $bytes = New-Object byte[] $length
        $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
        return [BitConverter]::ToString($bytes).Replace('-', '').ToLower()
    }
    $password = New-LocalSecret 24
    $encryptionKey = New-LocalSecret 32
    $config = @"
POSTGRES_USER=predictive
POSTGRES_PASSWORD=$password
POSTGRES_DB=predictive_bi
DATABASE_URL=postgresql+psycopg://predictive:${password}@127.0.0.1:55432/predictive_bi
N8N_ENCRYPTION_KEY=$encryptionKey
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=
MLFLOW_TRACKING_URI=http://127.0.0.1:5010
"@
    [IO.File]::WriteAllText((Join-Path $projectRoot '.env'), $config, (New-Object Text.UTF8Encoding $false))
}
Write-Host 'Configuração local preservada; segredos não exibidos.'
