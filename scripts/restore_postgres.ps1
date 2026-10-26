param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $BackupFile)) { throw "Backup file not found: $BackupFile" }
if (-not $env:PGHOST) { $env:PGHOST = "localhost" }
if (-not $env:PGPORT) { $env:PGPORT = "5432" }
if (-not $env:PGDATABASE) { $env:PGDATABASE = "resq_ai" }
if (-not $env:PGUSER) { $env:PGUSER = "resq" }
if (-not $env:PGPASSWORD) { throw "Set PGPASSWORD in the process environment; do not put it in this script." }

pg_restore --clean --if-exists --no-owner --dbname=$env:PGDATABASE $BackupFile
if ($LASTEXITCODE -ne 0) { throw "pg_restore failed" }
Write-Output "Backup restored: $BackupFile"
