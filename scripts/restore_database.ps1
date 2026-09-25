$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "====================================="
Write-Host "   UDAANDARPAN DATABASE RESTORE"
Write-Host "====================================="
Write-Host ""

$pgBin = "C:\Program Files\PostgreSQL\18\bin"
$pgRestore = Join-Path $pgBin "pg_restore.exe"

if (!(Test-Path $pgRestore)) {
    Write-Host "ERROR: pg_restore.exe not found at:"
    Write-Host $pgRestore
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

$backupFile = Read-Host "Enter backup file path"

if (!(Test-Path $backupFile)) {
    Write-Host ""
    Write-Host "ERROR: Backup file not found."
    exit 1
}

Write-Host ""
Write-Host "Restoring database..."
Write-Host ""

& $pgRestore `
    --clean `
    --if-exists `
    --no-owner `
    --dbname="$env:PGDATABASE" `
    "$backupFile"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Database restore failed."
    exit 1
}

Write-Host ""
Write-Host "Database restored successfully."
Write-Host ""