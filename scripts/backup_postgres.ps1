param(
    [string]$OutputDirectory = "./backups"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$output = Join-Path $OutputDirectory "resq-ai-$timestamp.dump"

if (-not $env:PGHOST) { $env:PGHOST = "localhost" }
if (-not $env:PGPORT) { $env:PGPORT = "5432" }
if (-not $env:PGDATABASE) { $env:PGDATABASE = "resq_ai" }
if (-not $env:PGUSER) { $env:PGUSER = "resq" }
if (-not $env:PGPASSWORD) { throw "Set PGPASSWORD in the process environment; do not put it in this script." }

pg_dump --format=custom --file=$output
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }
Write-Output "Backup created: $output"
