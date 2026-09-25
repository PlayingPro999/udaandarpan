# UdaanDarpan

**Real-Time Airfare Price Index**

UdaanDarpan is a prototype platform for collecting domestic airfare data, storing and normalizing fare observations, and calculating route-level and national airfare indices across different advance-booking windows.

## Features

- Automated airfare collection through the Ignav API
- Fare normalization and validation
- PostgreSQL database
- Route-level airfare index calculation
- T+1, T+7, T+15, T+30 and T+45 booking windows
- Passenger-weighted national index
- FastAPI backend
- Web dashboard
- Database backup and restore scripts
- Configurable routes, weights and baselines

## Requirements

Install:

- Python 3.11+
- PostgreSQL
- Git
- An Ignav API key for collecting new data

Python packages are installed automatically from `requirements.txt`.

## Setup

Clone the repository:

```powershell
git clone https://github.com/PlayingPro999/udaandarpan.git
cd udaandarpan
```

If PowerShell blocks scripts, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Run the setup script:

```powershell
.\setup.ps1
```

The setup script creates the virtual environment, installs dependencies, creates/checks the PostgreSQL database, creates the schema, and loads the configured weights and baselines.

## Configure `.env`

Open `.env` and enter your own credentials:

```env
IGNAV_API_KEY=YOUR_IGNAV_API_KEY
DB_HOST=localhost
DB_PORT=5432
DB_NAME=airfare_index
DB_USER=postgres
DB_PASSWORD=YOUR_POSTGRES_PASSWORD
```

Never commit `.env` to GitHub.

## Restore Existing Database

If you have the project's PostgreSQL `.dump` backup, run:

```powershell
.\scripts\restore_database.ps1
```

When prompted, provide the path to the `.dump` file.

The database backup is shared separately and is not stored in the GitHub repository.

## Run the Application

Activate the environment if necessary:

```powershell
.\venv\Scripts\Activate.ps1
```

Start FastAPI:

```powershell
python -m uvicorn app.main:app --reload
```

Dashboard:

```text
http://127.0.0.1:8000/dashboard
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

## Collect New Fare Data

Collect fares for the configured routes and booking windows:

```powershell
python -m app.run_collection
```

Calculate route indices:

```powershell
python -m app.index
```

Refresh the dashboard after the index calculation.

## Project Structure

```text
udaandarpan/
├── app/
│   ├── collector.py
│   ├── create_database.py
│   ├── database.py
│   ├── db_config.py
│   ├── index.py
│   ├── ingestion.py
│   ├── load_weights.py
│   ├── main.py
│   ├── national_index.py
│   ├── normalizer.py
│   ├── repository.py
│   ├── run_collection.py
│   ├── schemas.py
│   ├── setup_baseline.py
│   └── static/
│       └── index.html
├── config/
│   ├── baselines.json
│   ├── route_weights.json
│   └── routes.json
├── scripts/
│   ├── backup_database.ps1
│   └── restore_database.ps1
├── data/
├── backups/
├── requirements.txt
├── setup.ps1
├── .env.example
├── .gitignore
└── README.md
```

## Configuration

Routes:

```text
config/routes.json
```

Passenger-based route weights:

```text
config/route_weights.json
```

Route baselines:

```text
config/baselines.json
```

After changing route weights:

```powershell
python -m app.load_weights
```

After changing baselines:

```powershell
python -m app.setup_baseline
```

## Database Backup

Create a PostgreSQL backup:

```powershell
.\scripts\backup_database.ps1
```

Backups are stored in `backups/` and are excluded from Git.

## Typical Workflow

```powershell
.\venv\Scripts\Activate.ps1
python -m app.run_collection
python -m app.index
python -m uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/dashboard
```

## Important Notes

- Fresh fare collection requires a valid Ignav API key.
- `.env`, API keys, database passwords, database dumps and `venv/` must not be committed.
- The current route set and weighting data are prototype configuration and can be expanded.
- The current prototype baselines are configuration data and are not the final historical CPI base period.
