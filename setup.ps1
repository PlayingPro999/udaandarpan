$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "====================================="
Write-Host "       UDAANDARPAN PROJECT SETUP"
Write-Host "====================================="
Write-Host ""

# 1. Check Python
Write-Host "Checking Python..."

try {
    python --version
    if ($LASTEXITCODE -ne 0) {
        throw "Python is not installed or not in PATH."
    }
}
catch {
    Write-Host "ERROR: Python is not installed or not in PATH."
    exit 1
}

# 2. Create virtual environment
if (!(Test-Path ".\venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Could not create virtual environment."
        exit 1
    }
}
else {
    Write-Host "Virtual environment already exists."
}

# 3. Use venv Python directly
# This avoids PowerShell execution-policy problems with Activate.ps1.
$pythonExe = Join-Path (Get-Location) "venv\Scripts\python.exe"

if (!(Test-Path $pythonExe)) {
    Write-Host "ERROR: Virtual environment Python was not found."
    exit 1
}

# 4. Install dependencies
Write-Host ""
Write-Host "Installing project dependencies..."

& $pythonExe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip upgrade failed."
    exit 1
}

& $pythonExe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Dependency installation failed."
    exit 1
}

# 5. Install Playwright Chromium
Write-Host ""
Write-Host "Installing Playwright Chromium..."

& $pythonExe -m playwright install chromium
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Playwright Chromium installation failed."
    exit 1
}

# 6. Configure environment file
if (!(Test-Path ".\.env")) {
    if (Test-Path ".\.env.example") {
        Write-Host "Creating .env from .env.example..."
        Copy-Item ".\.env.example" ".\.env"
        Write-Host "Edit .env with your actual API key and database settings."
        Read-Host "Press ENTER after editing .env"
    }
    else {
        Write-Host "ERROR: .env.example is missing."
        Write-Host "Create .env.example with the required variable names first."
        exit 1
    }
}
else {
    Write-Host ".env already exists. Keeping existing configuration."
}

# 7. Locate PostgreSQL
Write-Host ""
Write-Host "Looking for PostgreSQL..."

$postgresRoot = "C:\Program Files\PostgreSQL"

if (!(Test-Path $postgresRoot)) {
    Write-Host "ERROR: PostgreSQL installation was not found at $postgresRoot."
    Write-Host "Install PostgreSQL or update this script for your installation path."
    exit 1
}

$postgresInstallations = @(
    Get-ChildItem $postgresRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d+$' } |
    Sort-Object { [int]$_.Name } -Descending
)

if ($postgresInstallations.Count -eq 0) {
    Write-Host "ERROR: No PostgreSQL version was found."
    exit 1
}

$pgBin = Join-Path $postgresInstallations[0].FullName "bin"
$psql = Join-Path $pgBin "psql.exe"
$pgDump = Join-Path $pgBin "pg_dump.exe"
$pgRestore = Join-Path $pgBin "pg_restore.exe"

foreach ($exe in @($psql, $pgDump, $pgRestore)) {
    if (!(Test-Path $exe)) {
        Write-Host "ERROR: Required PostgreSQL tool not found: $exe"
        exit 1
    }
}

$env:Path = "$pgBin;$env:Path"

Write-Host "PostgreSQL tools found at: $pgBin"

# 8. Verify database connectivity
# Database credentials must be configured in .env.
Write-Host ""
Write-Host "Checking database setup..."

& $pythonExe -m app.create_database
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Database creation/check failed."
    exit 1
}

# 9. Initialize schema
Write-Host ""
Write-Host "Creating database schema..."

& $pythonExe -m app.database
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Database schema setup failed."
    exit 1
}

# 10. Load route weights
Write-Host ""
Write-Host "Loading route weights..."

& $pythonExe -m app.load_weights
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Route weights failed to load."
    exit 1
}

# 11. Load route baselines
Write-Host ""
Write-Host "Loading route baselines..."

& $pythonExe -m app.setup_baseline
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Route baselines failed to load."
    exit 1
}

# 12. Complete
Write-Host ""
Write-Host "====================================="
Write-Host "          SETUP COMPLETE"
Write-Host "====================================="
Write-Host ""
Write-Host "Activate the environment if desired:"
Write-Host ".\venv\Scripts\Activate.ps1"
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
Write-Host "Collectors:"
Write-Host "python -m app.run_collection ignav"
Write-Host "python -m app.run_collection playwright"
Write-Host ""