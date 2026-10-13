# UdaanDarpan — Real-Time Airfare Price Index

**Smart India Hackathon (SIH) Problem Statement: SIH26056**  
**Domain:** Real-Time Airfare Price Intelligence and Indexing

UdaanDarpan is a data collection, processing, and analytics platform designed to monitor domestic airfare prices across Indian routes and calculate route-level and national airfare indices. It brings together multiple independent data collectors, fare normalization, PostgreSQL storage, configurable route baselines, passenger-traffic weights, and a FastAPI-powered dashboard.

The platform aims to support systematic airfare price monitoring and provide structured data that can contribute to airfare inflation analysis and statistical reporting.

---

## Table of Contents

- [Overview](#overview)
- [Objectives](#objectives)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Route Coverage](#route-coverage)
- [Booking Horizons](#booking-horizons)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Environment Configuration](#environment-configuration)
- [Database Initialization](#database-initialization)
- [Running the Application](#running-the-application)
- [Data Collection](#data-collection)
- [Fare Processing Pipeline](#fare-processing-pipeline)
- [Airfare Index Methodology](#airfare-index-methodology)
- [API and Dashboard](#api-and-dashboard)
- [Data Quality and Limitations](#data-quality-and-limitations)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)
- [Future Improvements](#future-improvements)

---

## Overview

Airfare prices can vary with route, departure date, booking horizon, airline, availability, and collection time. Monitoring these changes across several routes requires a consistent process for gathering observations, validating and normalizing fares, storing historical records, and comparing prices against a baseline.

UdaanDarpan addresses this problem through a modular pipeline:

1. Collect airfare observations using independent data collectors.
2. Normalize and validate the collected data.
3. Store observations in PostgreSQL.
4. Compare fares with configured route baselines.
5. Calculate route-level airfare indices.
6. Aggregate route indices using configured passenger-traffic weights.
7. Expose available data through a FastAPI application and dashboard.

The project is intended as a prototype for airfare price intelligence and index computation. The quality of its outputs depends on the availability, coverage, and reliability of the underlying observations and reference data.

## Objectives

- Automate airfare data collection across selected Indian domestic routes.
- Support multiple independent collection mechanisms.
- Maintain structured and persistent airfare observations.
- Normalize data into a consistent internal representation.
- Compare observed fares with configured baseline fares.
- Calculate route-level indices for different booking horizons.
- Produce a weighted national index using configured route weights.
- Provide an API and dashboard for examining the resulting data.
- Establish a foundation for historical analysis and back-testing.

## Key Features

### Independent data collectors

The system has three separate collection implementations:

- **Ignav collector:** Uses the Ignav fare API.
- **Requests-based EaseMyTrip collector:** Uses HTTP requests to collect fare data from EaseMyTrip.
- **Playwright-based EaseMyTrip collector:** Uses browser automation to interact with the website and collect available fare-calendar observations.

Each collector is invoked explicitly. The system does not automatically switch from one collector to another when a collection attempt fails.

### Structured fare processing

Collected data passes through normalization, schema validation, and ingestion before being persisted.

### PostgreSQL persistence

The database stores fare observations, route baselines, route weights, and calculated airfare-index values.

### Route-level and national indices

The platform supports route-level index calculations and a national aggregate using configured passenger-traffic weights.

### Dashboard and API

FastAPI provides the application endpoints, while the dashboard presents available airfare and index information.

---

## System Architecture

The logical data flow is:

```text
                  UdaanDarpan
                       |
          +------------+------------+
          |            |            |
        Ignav       EaseMyTrip    EaseMyTrip
        API          Requests      Playwright
          |            |            |
          +------------+------------+
                       |
              Fare Data Collection
                       |
                  Normalizer
                       |
                 Schema Validation
                       |
                    Ingestion
                       |
                  Repository
                       |
                  PostgreSQL
                       |
          +------------+------------+
          |                         |
     Route Index              National Index
          |                         |
          +------------+------------+
                       |
                 FastAPI Backend
                       |
                Web Dashboard
```

### Main components

| Component | Responsibility |
|---|---|
| `app/collector.py` | Ignav API-based fare collection |
| `app/scraper.py` | Requests-based EaseMyTrip collection, where present in the project |
| `app/browser_scraper.py` | Playwright-based EaseMyTrip browser collection |
| `app/normalizer.py` | Fare normalization and booking-window classification |
| `app/schemas.py` | Fare observation representation and validation |
| `app/ingestion.py` | Converts normalized observations into persisted records |
| `app/repository.py` | Database operations for fare observations |
| `app/database.py` | Database table and index initialization |
| `app/create_database.py` | Creates the application database when necessary |
| `app/load_weights.py` | Loads configured route passenger-traffic weights |
| `app/setup_baseline.py` | Loads configured baseline fares |
| `app/index.py` | Route-level index calculations |
| `app/national_index.py` | National index calculation |
| `app/run_collection.py` | Command-line entry point for selecting a collector |
| `app/main.py` | FastAPI application |
| `app/static/index.html` | Dashboard interface |

The exact files present in the checked-out repository determine which commands and optional components are available.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Collection, processing, and application logic |
| FastAPI | API and backend application |
| PostgreSQL | Persistent relational database |
| psycopg2 | PostgreSQL connectivity |
| Requests | HTTP-based data collection |
| Playwright | Browser automation |
| Pandas and NumPy | Data processing and numerical operations |
| Scikit-learn | Available for analytical or modelling extensions |
| Uvicorn | ASGI application server |
| HTML, CSS, JavaScript | Dashboard interface |
| python-dotenv | Environment-variable configuration |

---

## Route Coverage

The configured domestic route set contains 15 directional routes:

| No. | Origin | Destination | Route |
|---:|---|---|---|
| 1 | Bengaluru | Mumbai | BLR-BOM |
| 2 | Bengaluru | Delhi | BLR-DEL |
| 3 | Mumbai | Bengaluru | BOM-BLR |
| 4 | Mumbai | Delhi | BOM-DEL |
| 5 | Mumbai | Hyderabad | BOM-HYD |
| 6 | Mumbai | Chennai | BOM-MAA |
| 7 | Kolkata | Delhi | CCU-DEL |
| 8 | Delhi | Bengaluru | DEL-BLR |
| 9 | Delhi | Mumbai | DEL-BOM |
| 10 | Delhi | Kolkata | DEL-CCU |
| 11 | Delhi | Hyderabad | DEL-HYD |
| 12 | Delhi | Chennai | DEL-MAA |
| 13 | Hyderabad | Mumbai | HYD-BOM |
| 14 | Hyderabad | Delhi | HYD-DEL |
| 15 | Chennai | Delhi | MAA-DEL |

Routes are directional. For example, `DEL-BOM` and `BOM-DEL` are treated as separate routes because their observed fares and demand patterns may differ.

The routes are configured in `config/routes.json`.

## Booking Horizons

The project is designed to examine fares at multiple lead times before departure:

| Booking horizon | Meaning |
|---|---|
| T+1 | Departure approximately one day after the search date |
| T+7 | Departure approximately seven days after the search date |
| T+15 | Departure approximately fifteen days after the search date |
| T+30 | Departure approximately thirty days after the search date |
| T+45 | Departure approximately forty-five days after the search date |

The booking-window classifier in `app/normalizer.py` determines the applicable horizon according to the project's implementation.

The availability of observations for a horizon depends on the data returned by the selected collector.

---

## Project Structure

The following is the intended high-level organization. Some optional files, including the requests-based scraper, may have different names or may not be present in every repository revision.

```text
udaandarpan/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── db_config.py
│   ├── create_database.py
│   ├── database.py
│   ├── collector.py
│   ├── scraper.py
│   ├── browser_scraper.py
│   ├── run_collection.py
│   ├── schemas.py
│   ├── normalizer.py
│   ├── ingestion.py
│   ├── repository.py
│   ├── load_weights.py
│   ├── setup_baseline.py
│   ├── index.py
│   ├── national_index.py
│   └── static/
│       └── index.html
├── config/
│   ├── routes.json
│   ├── baselines.json
│   └── route_weights.json
├── requirements.txt
├── .env.example
├── .gitignore
├── setup.ps1
└── README.md
```

### Configuration files

- **`config/routes.json`** — Defines the routes used during collection.
- **`config/baselines.json`** — Contains configured baseline fares and their reference dates.
- **`config/route_weights.json`** — Contains passenger counts, route weights, and associated source/period metadata.
- **`.env.example`** — Template for local database credentials and collector API keys.
- **`requirements.txt`** — Python dependency list.

The project root is the working directory for the commands below.

---

## Prerequisites

Install the following before setting up the application:

1. Python compatible with the dependencies in `requirements.txt`.
2. PostgreSQL installed and running locally or accessible on a configured host.
3. Git, if cloning the repository.
4. Internet access for the selected online data collector.
5. A valid Ignav API key if using the Ignav collector.
6. Chromium installed through Playwright if using the browser-based collector.

The provided PowerShell setup script is intended for Windows and may expect PostgreSQL under the standard `C:\Program Files\PostgreSQL` directory.

## Installation and Setup

### 1. Clone the repository

Replace the URL below with the actual Git repository URL.

```powershell
git clone <YOUR_REPOSITORY_URL>
cd udaandarpan
```

If the repository is already on your computer, navigate to its root directory instead.

### 2. Create a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current session, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install the Playwright Chromium browser:

```powershell
python -m playwright install chromium
```

This step is required for the Playwright collector, not for ordinary API-based collection.

### 4. Configure environment variables

Create a local `.env` file from the template:

```powershell
Copy-Item .env.example .env
```

If `.env.example` does not exist, create it using the configuration shown in the next section.

Edit `.env` with your own PostgreSQL credentials and, if applicable, Ignav API key.

### 5. Initialize the database

Ensure PostgreSQL is running and the credentials in `.env` are correct. Then execute:

```powershell
python -m app.create_database
python -m app.database
python -m app.load_weights
python -m app.setup_baseline
```

These commands create the application database if needed, initialize its tables and indexes, load configured route weights, and load configured baseline fares.

### Optional: Run the setup script

If the repository includes `setup.ps1`, it can automate several setup steps.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

Review the script and its environment assumptions before running it. It may require PostgreSQL to be installed in the standard Windows directory and the `.env.example` template to be present.

---

## Environment Configuration

Use the following as the contents of `.env.example`:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=airfare_index
DB_USER=postgres
DB_PASSWORD=replace_with_your_postgres_password

IGNAV_API_KEY=replace_with_your_ignav_api_key
```

### Configuration variables

| Variable | Purpose |
|---|---|
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port |
| `DB_NAME` | Application database name |
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `IGNAV_API_KEY` | Credential used by the Ignav collector |

Only configure credentials that are needed for your environment. The database configuration uses `.env` values, with defaults for some connection settings.

**Never commit your real `.env` file, API keys, or database passwords to GitHub.** The `.env.example` file must contain placeholders only.

---

## Database Initialization

UdaanDarpan uses PostgreSQL to persist the information needed for collection and index computation.

The database initialization code defines the following principal tables:

| Table | Purpose |
|---|---|
| `fare_observations` | Stores collected airfare observations |
| `route_baselines` | Stores reference fares for configured routes |
| `route_weights` | Stores passenger-traffic counts and route weights |
| `airfare_index_values` | Stores calculated index values |

The schema also creates indexes to support common lookups and improve query performance.

### Fare observations

The observation model can represent fields such as:

- Source
- Origin and destination
- Airline and flight number, when available
- Departure date
- Search timestamp
- Departure and arrival times, when available
- Duration and number of stops, when available
- Cabin
- Fare and currency
- Booking-window classification
- Source-specific identifiers and raw data

Not every collector provides every field. Missing information should not be interpreted as a verified value.

### Inspecting the database

Open PostgreSQL's command-line client:

```powershell
psql -U postgres -d airfare_index
```

Then run:

```sql
\dt
```

To inspect fare observations:

```sql
SELECT *
FROM fare_observations
ORDER BY search_timestamp DESC
LIMIT 20;
```

To inspect the configured route weights:

```sql
SELECT *
FROM route_weights
ORDER BY origin, destination;
```

To inspect baseline fares:

```sql
SELECT *
FROM route_baselines
ORDER BY origin, destination;
```

Exit `psql` with:

```sql
\q
```

These commands assume the corresponding tables have been initialized successfully.

---

## Running the Application

### Start the FastAPI server

From the project root, with the virtual environment activated:

```powershell
python -m uvicorn app.main:app --reload
```

The development server normally runs at:

- **Dashboard:** http://127.0.0.1:8000/dashboard
- **Interactive API documentation:** http://127.0.0.1:8000/docs

Use the API documentation to inspect the endpoints actually exposed by the current application.

Keep the terminal running while accessing the dashboard. Stop the development server with `Ctrl+C`.

### Run a collector

The collection command accepts a collector selection:

```powershell
python -m app.run_collection ignav
```

Or:

```powershell
python -m app.run_collection playwright
```

The selected collector runs according to the routes and booking horizons configured in the project.

The requests-based EaseMyTrip scraper is a separate implementation. Invoke it using its own entry point if one is provided by the current repository version; do not assume it is automatically included in the `run_collection.py` command.

Collection may take time because routes and booking horizons are processed individually, and external sites or APIs can limit requests or return incomplete results.

---

## Data Collection

### 1. Ignav collector

The Ignav collector uses the Ignav API to request one-way airfare data.

**Implementation:** `app/collector.py`

It requires a valid `IGNAV_API_KEY` in the environment. The exact observations available depend on the API response, supported routes, request parameters, and API access.

### 2. Requests-based EaseMyTrip collector

This collector uses HTTP requests to retrieve airfare information from EaseMyTrip.

It is separate from both the Ignav collector and the Playwright collector. Its success depends on the website's response structure, request requirements, network access, and any applicable access restrictions.

The collector should only be considered operational for the fields and responses it successfully parses.

### 3. Playwright-based EaseMyTrip collector

**Implementation:** `app/browser_scraper.py`

This collector uses Chromium browser automation to interact with EaseMyTrip and obtain fare-calendar observations.

The distinction matters: **a calendar fare is not necessarily an individual flight-result fare**. Calendar prices should not be presented as verified flight-card records.

If flight-level data is required, the collector must successfully extract the relevant flight-result cards and their actual fields, including airline, flight number, departure and arrival times, duration, stops, and fare. Those fields must not be fabricated when they are absent.

### Collector independence

The three implementations serve different collection paths. Their results should retain the correct source attribution, and one collector's failure should not silently trigger another collector.

For reproducibility, record which collector was used and when observations were collected.

---

## Fare Processing Pipeline

The collection and ingestion workflow is designed around the following steps.

### Step 1: Collect

The selected collector requests or retrieves available fare data for configured routes and departure dates.

### Step 2: Normalize

`app/normalizer.py` transforms supported source values into the internal format. It also determines the applicable booking horizon.

### Step 3: Validate

`app/schemas.py` provides the fare observation representation and validation logic.

Validation helps reject malformed records, but it cannot establish that an external fare is accurate or still available.

### Step 4: Ingest

`app/ingestion.py` converts normalized data into observation records and passes them to the persistence layer.

### Step 5: Persist

`app/repository.py` handles database operations. The repository also applies the project's duplicate-handling rules for records with source identifiers.

### Step 6: Calculate indices

The index modules compare eligible observations with configured baselines and calculate route-level and national index values.

### Collection deduplication

The repository contains duplicate-handling logic involving source identifiers and departure dates. Collection checks also consider route, departure date, source, booking window, and search date.

These mechanisms are implementation-specific; they should not be assumed to guarantee global deduplication across all sources or every possible repeated observation.

---

## Airfare Index Methodology

### Route-level index

The general interpretation of a baseline-relative price index is:

\[
I_r = \frac{P_r}{B_r}\times 100
\]

Where:

- \(I_r\) is the route index.
- \(P_r\) is the eligible observed or aggregated fare for the route and comparison period.
- \(B_r\) is the corresponding configured baseline fare.

Under this interpretation:

- **100** means the compared fare equals its baseline.
- **Above 100** means the compared fare is higher than its baseline.
- **Below 100** means the compared fare is lower than its baseline.

The exact aggregation of observations, comparison periods, and eligibility rules depends on the implemented index calculation.

Baseline fares and reference dates are configured in `config/baselines.json`. Changing these values can change the resulting index even when the collected fares remain the same.

### National index

The national index combines route-level results using configured passenger-traffic weights.

In general, a weighted index can be expressed as:

\[
I_{\text{national}} =
\frac{\sum_r w_r I_r}{\sum_r w_r}
\]

Where:

- \(I_r\) is the eligible index for route \(r\).
- \(w_r\) is the configured weight for that route.

The actual treatment of missing routes and the normalization of weights must follow the implementation in `app/national_index.py`.

The route weights are maintained in `config/route_weights.json`, including their source and period metadata. Their provenance and accuracy should be independently verified before the resulting index is used for official statistical reporting.

### Interpreting results responsibly

An index is only as reliable as its observations, baselines, and weights. A small sample, missing route, changing source coverage, or inconsistent collection time can materially affect the result.

A computed index should therefore be interpreted alongside its observation count, collection period, source, and baseline metadata whenever available.

---

## API and Dashboard

The FastAPI application is defined in `app/main.py`. The dashboard is located in `app/static/index.html`.

The application is intended to expose collected airfare and calculated index information through its available endpoints.

To explore the API:

1. Start the server.
2. Open http://127.0.0.1:8000/docs.
3. Inspect the endpoints registered by the application.
4. Use the dashboard at http://127.0.0.1:8000/dashboard.

The dashboard's displayed results depend on the records in PostgreSQL and the calculations exposed by the running application. An empty or incomplete database may produce empty, partial, or unavailable results.

---

## Data Quality and Limitations

UdaanDarpan is a prototype for airfare collection and index analysis. Consider the following limitations when interpreting its output.

### External source variability

Airline and travel websites may change their page structure, response formats, availability, or access requirements. A scraper that worked previously may require maintenance.

### Calendar fares versus flight-level fares

Fare-calendar prices and individual flight-result prices represent different kinds of observations. They must not be mixed without an explicit and documented methodology.

### Incomplete fields

Airline names, flight numbers, timings, duration, stops, baggage information, and other attributes may be unavailable for some sources. Missing values should remain distinguishable from verified values.

### Fare changes

Displayed fares can change with availability, passenger count, taxes, fees, currency, and the time of collection. Comparisons should use consistent definitions wherever possible.

### Baseline sensitivity

Baseline fares and reference dates directly influence calculated indices. They should be documented, versioned, and reviewed.

### Weight provenance

Passenger-traffic weights should be verified against their cited official source and reference period. Configured weights alone do not establish that the resulting index is an official government statistic.

### Statistical interpretation

A prototype index is not automatically equivalent to an official airfare consumer price index. Official use would require a documented methodology, representative sampling, quality controls, reproducibility, and validation against suitable reference data.

### External service requirements

Use each external source in accordance with its terms, access controls, and applicable requirements. Do not assume a successful response or unrestricted access.

---

## Troubleshooting

### PostgreSQL connection fails

Check that:

- PostgreSQL is installed and running.
- `DB_HOST` and `DB_PORT` are correct.
- The database username and password in `.env` are valid.
- The database has been created and initialized.

Retry the initialization commands after correcting the configuration.

### `ModuleNotFoundError: No module named 'app'`

Run commands from the project root, where the `app` directory is located.

Prefer module execution, for example:

```powershell
python -m app.database
```

### Playwright reports that Chromium is missing

Run:

```powershell
python -m playwright install chromium
```

If installation fails, check network access and the Python environment in which Playwright was installed.

### Ignav authentication fails

Verify the `IGNAV_API_KEY` value in `.env`, confirm that the environment is loaded, and check the API's current access requirements.

Do not commit the key to the repository or include it in diagnostic output.

### EaseMyTrip collection returns no fares

Check the route and departure dates, network connectivity, response status, and current website structure. Inspect whether the selected collector expects an API response or browser-rendered content.

A successful page load does not guarantee that the expected fare fields were returned or parsed.

### Dashboard does not load

Verify that Uvicorn is running and that the dashboard route is registered in the current FastAPI application. Open `/docs` to inspect available routes.

### Setup script cannot find PostgreSQL

The PowerShell setup script may expect PostgreSQL under `C:\Program Files\PostgreSQL`. If it is installed elsewhere, configure the PostgreSQL executable path or initialize the application manually using the database commands above.

---

## Security Considerations

- Keep `.env` out of version control.
- Commit `.env.example` with placeholder values only.
- Do not commit database passwords, API keys, personal tokens, or production credentials.
- Exclude virtual environments, caches, logs, and database dumps from Git.
- Avoid exposing the development server to untrusted networks.
- Do not log authentication headers or secret values.
- Review source access requirements before running collectors.

---

## Future Improvements

Potential extensions to the project include:

- Robust extraction of individual flight-result cards with verified flight-level fields.
- Consistent source adapters and stronger schema validation.
- Historical snapshots and audit trails for index calculations.
- Improved retry, timeout, and rate-limit handling.
- Explicit handling of missing routes and incomplete booking horizons.
- Data-quality reports and source-coverage metrics.
- Versioned baselines and passenger-traffic weights.
- Back-testing against suitable historical reference data.
- Automated tests for normalization, ingestion, deduplication, and index calculations.
- More detailed dashboard filters for route, source, departure date, and booking horizon.

---

**UdaanDarpan — SIH26056**  
*Building a reproducible foundation for real-time airfare price monitoring and index analysis.*