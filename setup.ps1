$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "====================================="
Write-Host "       UDAANDARPAN PROJECT SETUP"
Write-Host "====================================="
Write-Host ""

# --------------------------------------------------
# 1. Check Python
# --------------------------------------------------

Write-Host "Checking Python..."

python --version

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python is not installed or not in PATH."
    exit 1
}

# --------------------------------------------------
# 2. Create virtual environment
# --------------------------------------------------

if (!(Test-Path ".\venv")) {

    Write-Host "Creating virtual environment..."

    python -m venv venv

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Could not create virtual environment."
        exit 1
    }

} else {

    Write-Host "Virtual environment already exists."

}

# --------------------------------------------------
# 3. Activate virtual environment
# --------------------------------------------------

Write-Host "Activating virtual environment..."

& ".\venv\Scripts\Activate.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Could not activate virtual environment."
    exit 1
}

# --------------------------------------------------
# 4. Install Python dependencies
# --------------------------------------------------

Write-Host "Installing project dependencies..."

python -m pip install --upgrade pip

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip upgrade failed."
    exit 1
}

pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Dependency installation failed."
    exit 1
}

# --------------------------------------------------
# 5. Create .env if missing
# --------------------------------------------------

if (!(Test-Path ".\.env")) {

    Write-Host "Creating .env from .env.example..."

    Copy-Item ".\.env.example" ".\.env"

    Write-Host ""
    Write-Host "IMPORTANT:"
    Write-Host "Open .env and enter:"
    Write-Host "  IGNAV_API_KEY"
    Write-Host "  DB_PASSWORD"
    Write-Host ""

    Read-Host "Press ENTER after editing .env"

} else {

    Write-Host ".env already exists. Keeping existing configuration."

}

# --------------------------------------------------
# 6. Find PostgreSQL automatically
# --------------------------------------------------

Write-Host "Looking for PostgreSQL..."

$postgresRoot = "C:\Program Files\PostgreSQL"

if (!(Test-Path $postgresRoot)) {

    Write-Host "ERROR: PostgreSQL installation was not found."
    exit 1

}

$postgresInstallations = Get-ChildItem $postgresRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d+$' } |
    Sort-Object { [int]$_.Name } -Descending

if ($postgresInstallations.Count -eq 0) {

    Write-Host "ERROR: No PostgreSQL version was found."
    exit 1

}

$postgresVersion = $postgresInstallations[0].Name

$pgBin = Join-Path $postgresInstallations[0].FullName "bin"

$psql = Join-Path $pgBin "psql.exe"
$pgDump = Join-Path $pgBin "pg_dump.exe"
$pgRestore = Join-Path $pgBin "pg_restore.exe"

if (!(Test-Path $psql)) {

    Write-Host "ERROR: psql.exe was not found."
    exit 1

}

if (!(Test-Path $pgDump)) {

    Write-Host "ERROR: pg_dump.exe was not found."
    exit 1

}

if (!(Test-Path $pgRestore)) {

    Write-Host "ERROR: pg_restore.exe was not found."
    exit 1

}

Write-Host ""
Write-Host "PostgreSQL found:"
Write-Host "Version: $postgresVersion"
Write-Host "Path:    $pgBin"
Write-Host ""

# Make PostgreSQL commands available
# in the current PowerShell session.

$env:Path = "$pgBin;$env:Path"

# --------------------------------------------------
# 7. Create/check database
# --------------------------------------------------

Write-Host "Creating/checking database..."

python -m app.create_database

if ($LASTEXITCODE -ne 0) {

    Write-Host "ERROR: Database creation/check failed."
    exit 1

}

# --------------------------------------------------
# 8. Create database schema
# --------------------------------------------------

Write-Host "Creating database schema..."

python -m app.database

if ($LASTEXITCODE -ne 0) {

    Write-Host "ERROR: Database schema setup failed."
    exit 1

}

# --------------------------------------------------
# 9. Load route weights
# --------------------------------------------------

Write-Host "Loading route weights..."

python -m app.load_weights

if ($LASTEXITCODE -ne 0) {

    Write-Host "ERROR: Route weights failed to load."
    exit 1

}

# --------------------------------------------------
# 10. Load route baselines
# --------------------------------------------------

Write-Host "Loading route baselines..."

python -m app.setup_baseline

if ($LASTEXITCODE -ne 0) {

    Write-Host "ERROR: Route baselines failed to load."
    exit 1

}

# --------------------------------------------------
# 11. Finished
# --------------------------------------------------

Write-Host ""
Write-Host "====================================="
Write-Host "          SETUP COMPLETE"
Write-Host "====================================="
Write-Host ""

Write-Host "Start API:"
Write-Host "python -m uvicorn app.main:app --reload"

Write-Host ""

Write-Host "Dashboard:"
Write-Host "http://127.0.0.1:8000/dashboard"

Write-Host ""

Write-Host "API Docs:"
Write-Host "http://127.0.0.1:8000/docs"

Write-Host ""