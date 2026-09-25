$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "====================================="
Write-Host "   UDAANDARPAN DATABASE BACKUP"
Write-Host "====================================="
Write-Host ""

$pgBin = "C:\Program Files\PostgreSQL\18\bin"
$pgDump = Join-Path $pgBin "pg_dump.exe"

if (!(Test-Path $pgDump)) {
    Write-Host "ERROR: pg_dump.exe not found at:"
    Write-Host $pgDump
    exit 1
}

if (!(Test-Path ".\.env")) {
    Write-Host "ERROR: .env file not found."
    exit 1
}

Get-Content ".\.env" | ForEach-Object {

    if ($_ -match "^DB_HOST=(.*)$") {
        $env:PGHOST = $Matches[1]
    }

    if ($_ -match "^DB_PORT=(.*)$") {
        $env:PGPORT = $Matches[1]
    }

    if ($_ -match "^DB_NAME=(.*)$") {
        $env:PGDATABASE = $Matches[1]
    }

    if ($_ -match "^DB_USER=(.*)$") {
        $env:PGUSER = $Matches[1]
    }

    if ($_ -match "^DB_PASSWORD=(.*)$") {
        $env:PGPASSWORD = $Matches[1]
    }
}

$backupDirectory = ".\backups"

if (!(Test-Path $backupDirectory)) {
    New-Item -ItemType Directory -Path $backupDirectory | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$backupFile = "$backupDirectory\airfare_index_$timestamp.dump"

Write-Host "Creating database backup..."
Write-Host ""

& $pgDump `
    --format=custom `
    --file="$backupFile"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Database backup failed."
    exit 1
}

Write-Host ""
Write-Host "Backup completed successfully:"
Write-Host $backupFile
Write-Host ""