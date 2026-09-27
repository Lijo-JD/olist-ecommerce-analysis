# Olist Brazilian E-Commerce Analytics

End-to-end **data engineering + data analytics** project built on the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — approximately 100,000 orders across 9 relational tables covering September 2016 to October 2018.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)
![pandas](https://img.shields.io/badge/pandas-2.x-150458.svg)
![Tests](https://img.shields.io/badge/tests-pytest-green.svg)
![License: MIT](https://img.shields.io/badge/code-MIT-yellow.svg)
![Data: CC BY-NC-SA 4.0](https://img.shields.io/badge/data-CC%20BY--NC--SA%204.0-lightgrey.svg)

---

## Table of Contents

1. [Overview](#overview)
2. [What This Project Demonstrates](#what-this-project-demonstrates)
3. [Architecture](#architecture)
4. [Repository Structure](#repository-structure)
5. [Dataset & License](#dataset--license)
6. [Prerequisites](#prerequisites)
7. [Setup — Local PostgreSQL (Recommended)](#setup--local-postgresql-recommended)
8. [Setup — Docker (Alternative)](#setup--docker-alternative)
9. [Running the Project](#running-the-project)
10. [Notebooks Overview](#notebooks-overview)
11. [SQL Files](#sql-files)
12. [Source Code (`src/`)](#source-code-src)
13. [Scripts (`scripts/`)](#scripts-scripts)
14. [Testing](#testing)
15. [Key Findings](#key-findings)
16. [Troubleshooting](#troubleshooting)
17. [License & Attribution](#license--attribution)

---

## Overview

This project is a portfolio-grade end-to-end analytics pipeline. It reads 9 CSV files from Olist's public marketplace dataset, cleans and normalizes them, loads them into PostgreSQL, engineers analytical feature tables, and produces business insights through SQL queries and Python visualizations.

It is designed to be:

- **Reproducible** — clone, install, run. No hidden steps.
- **Tested** — `pytest` covers the ETL, schema, and feature engineering logic against a real PostgreSQL database.
- **Layered** — the code separates concerns between `src/` (library), `sql/` (queries), `notebooks/` (analysis), and `scripts/` (orchestration).
- **Postgres-only** — one database technology end to end. The pipeline, the notebooks, and the tests all exercise the same engine.

---

## What This Project Demonstrates

| For **data engineering** roles | For **data analytics** roles |
|-------------------------------|------------------------------|
| Modular ETL package (`src/etl.py`) | Exploratory data analysis (`01_eda.ipynb`) |
| PostgreSQL schema with indexes | Feature engineering (`02_feature_engineering.ipynb`) |
| Bulk loading via PostgreSQL `COPY` | Business KPI analysis (`03_business_analysis.ipynb`) |
| Test suite with `pytest` against a real Postgres instance | SQL showcase — CTEs, window functions (`04_sql_showcase.ipynb`) |
| One-command pipeline runner | Business insights document (`final_insights.docx`) |
| Docker alternative for reproducibility | Consistent visualizations |
| Environment management with `.env` | Narrative-driven notebooks |
| Auto-generated insights report (`scripts/generate_insights.py`) | Tables and charts refreshed from live data |

---

## Architecture

```
┌────────────────────┐    extract    ┌───────────────┐   transform   ┌───────────────────┐
│    data/raw/       │──────────────▶│    pandas     │──────────────▶│     Parquet       │
│    (9 CSVs)        │               │  DataFrames   │               │  data/processed/  │
└────────────────────┘               └───────┬───────┘               └────────┬──────────┘
                                             │                                │
                                             │ load (COPY)                    │ features
                                             ▼                                ▼
                                     ┌───────────────┐              ┌───────────────────┐
                                     │  PostgreSQL   │              │  feature_*.parquet│
                                     │    (local)    │              │  orders/customers │
                                     └───────┬───────┘              │  products/sellers │
                                             │                      └────────┬──────────┘
                                             │ query                         │
                                             ▼                               ▼
                                     ┌─────────────────────────────────────────────┐
                                     │                 Notebooks                   │
                                     │  01 EDA → 02 Features → 03 Business         │
                                     │  → 04 SQL showcase                          │
                                     └───────────────────┬─────────────────────────┘
                                                         │
                                                         │ scripts/generate_insights.py
                                                         ▼
                                                 ┌─────────────────────┐
                                                 │ final_insights.docx │
                                                 └─────────────────────┘
```

**Data flow summary:**

1. **Extract** — read the 9 CSVs into pandas DataFrames.
2. **Transform** — parse datetimes, cast integer columns, clean strings, deduplicate reviews.
3. **Load** — bulk-insert into PostgreSQL using `COPY` (with `to_sql` as a safety fallback).
4. **Persist** — write cleaned tables to Parquet for fast re-analysis.
5. **Feature engineer** — build order/customer/product/seller analytical tables.
6. **Analyze** — notebooks query the DB and the feature Parquets to produce KPIs and charts.
7. **Report** — `scripts/generate_insights.py` pulls live numbers from PostgreSQL and the feature tables, then writes `final_insights.docx`.

---

## Repository Structure

```
olist-ecommerce-analysis/
│
├── data/
│   ├── raw/                          # Kaggle CSVs — NOT committed (gitignored)
│   ├── processed/                    # Parquet outputs — NOT committed (gitignored)
│   └── README.md                     # Dataset documentation + license
│
├── notebooks/
│   ├── 01_eda.ipynb                  # Exploratory data analysis
│   ├── 02_feature_engineering.ipynb  # Feature table construction
│   ├── 03_business_analysis.ipynb    # KPIs and visualizations
│   └── 04_sql_showcase.ipynb         # SQL proficiency demonstration
│
├── sql/
│   ├── 01_schema.sql                 # DDL — tables + indexes (PostgreSQL)
│   ├── 02_analysis_queries.sql       # Core KPI queries
│   └── 03_advanced_queries.sql       # CTEs, window functions
│
├── src/
│   ├── __init__.py                   # Package marker
│   ├── config.py                     # Paths, DB config, dataset metadata
│   ├── db_utils.py                   # SQLAlchemy engine, query helpers, COPY loader
│   ├── etl.py                        # Extract → Transform → Load pipeline
│   ├── features.py                   # RFM, cycle-time, and aggregation features
│   └── viz.py                        # Matplotlib/Seaborn style + helpers
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Shared pytest fixtures (Postgres engine)
│   ├── test_etl.py                   # ETL + schema smoke tests
│   └── test_features.py              # Feature engineering tests
│
├── scripts/
│   ├── __init__.py                   # Package marker for scripts/
│   ├── setup_test_db.py              # Creates the olist_test database
│   ├── run_pipeline.py               # One-command ETL + features runner
│   └── generate_insights.py          # Builds final_insights.docx from live data
│
├── visuals/                          # Auto-generated PNG charts (gitignored)
│
├── .env.example                      # Template for environment variables
├── .gitignore
├── docker-compose.yml                # Optional — PostgreSQL + pgAdmin
├── requirements.txt
├── README.md                         # You are here
├── final_insights.docx               # Business insight document (generated)
├── business_questions.docx           # Analytical questions answered
├── LICENSE                           # MIT for code
└── LICENSE-DATA                      # CC BY-NC-SA 4.0 notice for the dataset
```

---

## Dataset & License

### Source

**Brazilian E-Commerce Public Dataset by Olist**
Kaggle: <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>

### License

The dataset is licensed under **CC BY-NC-SA 4.0** — Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International.

| Term | Meaning |
|------|---------|
| ✅ **Attribution** | You must credit Olist as the source |
| ✅ **Non-Commercial** | No commercial use without permission |
| ✅ **ShareAlike** | Derivatives must use the same license |
| ❌ **No warranty** | Provided "as is" |

**Consequences for this repository:**

- Raw CSV files are **not committed** — they're large and the license restricts redistribution.
- Only aggregated, non-raw analytical outputs are committed.
- All derived content is shared under the same CC BY-NC-SA 4.0 license.
- Full details are in [`data/README.md`](data/README.md).

### Code license

All source code in this repository is licensed under the **MIT License** — see [`LICENSE`](LICENSE).

### Required files

The 9 CSV files you must download from Kaggle:

```
olist_customers_dataset.csv
olist_geolocation_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_orders_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
```

---

## Prerequisites

Before you begin, make sure you have:

- **Python 3.10 or newer** — check with `python --version`
- **PostgreSQL 14 or newer** — see the setup section below for OS-specific install instructions
- **Git** — for cloning the repository
- **~500 MB free disk space** — for the CSV files, Parquet outputs, and DB
- A **Kaggle account** (free) — to download the dataset

Optional:

- **Docker Desktop** — if you prefer Docker over a local PostgreSQL install
- **VS Code** with the Jupyter extension — recommended over plain Jupyter for a nicer workflow

---

## Setup — Local PostgreSQL (Recommended)

This is the primary setup path. It assumes you have PostgreSQL installed locally and either have `psql` on your PATH or can use a GUI SQL client (DBeaver, pgAdmin, VS Code).

This project uses the **`postgres` superuser** for local development. There is no separate application role. In production you would create a dedicated least-privilege role — see the [Production deployment notes](#production-deployment-notes) at the end of this section.

### Step 1 — Verify PostgreSQL is running

```bash
psql --version
# Expected: psql (PostgreSQL) 14.x or higher
```

If `psql` isn't on your PATH but PostgreSQL is installed, you can use any GUI client. You can also invoke the bundled `psql` directly:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres
```

If PostgreSQL isn't installed:

**Windows:** Download the installer from <https://www.postgresql.org/download/windows/>. During install:
- Set a password for the `postgres` superuser — remember it.
- Keep the default port `5432`.
- Include pgAdmin and Command Line Tools.

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Step 2 — Clone the repository

```bash
git clone https://github.com/Lijo-JD/olist-ecommerce-analysis.git
cd olist-ecommerce-analysis
```

### Step 3 — Create a Python virtual environment

```bash
# Create the venv
python -m venv .venv

# Activate — pick the line for your shell
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows cmd
.venv\Scripts\activate.bat
```

Verify the venv is active:

```bash
# macOS / Linux
which python
# Should print something like: .../olist-ecommerce-analysis/.venv/bin/python

# Windows
where python
# Should print something like: ...\olist-ecommerce-analysis\.venv\Scripts\python.exe
```

### Step 4 — Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**What gets installed:**

| Package | Purpose |
|---------|---------|
| `pandas`, `numpy` | Data manipulation |
| `matplotlib`, `seaborn` | Visualization |
| `sqlalchemy`, `psycopg2-binary` | PostgreSQL access |
| `python-dotenv` | Environment variable loading |
| `pyarrow` | Parquet serialization |
| `jupyter`, `notebook`, `ipykernel` | Notebook environment |
| `pytest`, `pytest-cov` | Testing |
| `python-docx` | Documentation generation |

### Step 5 — Register the notebook kernel

Register the venv's Python as a Jupyter kernel so notebooks use the right environment:

```bash
python -m ipykernel install --user --name=olist --display-name="Python (Olist)"
```

You'll see `Python (Olist)` in Jupyter's kernel picker. **Always use this kernel** for the project notebooks.

**Verify the kernel was registered:**

```bash
jupyter kernelspec list
```

Expected output includes a line like:

```
olist        C:\Users\<you>\AppData\Roaming\jupyter\kernels\olist
```

If `olist` isn't listed, the registration failed. Re-run the `ipykernel install` command and check for errors.

---

### Step 5b — Open the notebooks in VS Code (recommended)

VS Code gives you inline outputs, a built-in variable inspector, and Git integration — a nicer workflow than browser Jupyter for this project.

**1. Install VS Code and the required extensions**

Download VS Code from <https://code.visualstudio.com/> if you don't have it. Then install two extensions:

- **Python** (`ms-python.python`)
- **Jupyter** (`ms-toolsai.jupyter`)

Install from the VS Code Marketplace, or from the command line:

```bash
code --install-extension ms-python.python
code --install-extension ms-toolsai.jupyter
```

**2. Open the project folder in VS Code**

From the project root:

```bash
code .
```

Or open VS Code, go to **File → Open Folder…**, and select `olist-ecommerce-analysis`.

**3. Select the venv's Python interpreter**

VS Code needs to know which Python to use for the project:

1. Press **Ctrl+Shift+P** (Windows/Linux) or **Cmd+Shift+P** (macOS) to open the Command Palette.
2. Type and select: **Python: Select Interpreter**.
3. Pick the entry that shows `.venv` — something like:

   ```
   Python 3.13.5 ('.venv': venv)   .\.venv\Scripts\python.exe
   ```

If you don't see the `.venv` option, click **Enter interpreter path…** and navigate to `.venv\Scripts\python.exe` (Windows) or `.venv/bin/python` (macOS/Linux).

Once selected, the bottom status bar shows `.venv` — confirming VS Code is using the project's environment.

**4. Open a notebook**

In the VS Code Explorer, expand `notebooks/` and click `01_eda.ipynb`. VS Code opens it in the built-in notebook editor.

**5. Select the kernel**

Top-right of the notebook editor, click the kernel picker (it usually shows a Python version like `Python 3.13.5` or `Select Kernel`).

From the dropdown, choose:

```
Python (Olist)   .\.venv\Scripts\python.exe
```

If you don't see it:

1. Click **Select Another Kernel…** → **Jupyter Kernel…**.
2. The list now includes `Python (Olist)` (registered in the previous step).
3. If it still doesn't appear, restart VS Code — it caches kernel lists at startup.

**6. Run the notebook**

- **Run all cells:** click the double-play icon at the top of the notebook, or press **Ctrl+Alt+Enter**.
- **Run a single cell:** click the play icon on the cell, or press **Shift+Enter**.
- **Restart the kernel:** click the circular arrow in the top toolbar.

Cell outputs appear inline, including matplotlib charts. No browser needed.

**7. Verify the environment**

Run this in the first cell of any notebook:

```python
import sys
print(sys.executable)
```

Expected output (Windows):

```
E:\Portfolio\olist-ecommerce-analysis\.venv\Scripts\python.exe
```

macOS/Linux:

```
/path/to/olist-ecommerce-analysis/.venv/bin/python
```

If `sys.executable` points anywhere other than `.venv`, the wrong kernel is selected. Switch it via the kernel picker.

**8. Recommended VS Code settings (optional)**

Create `.vscode/settings.json` in the project root to enforce the right interpreter for anyone opening the repo:

```json
{
    "python.defaultInterpreterPath": ".venv/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "jupyter.notebookFileRoot": "${workspaceFolder}",
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/*.egg-info": true
    }
}
```

Two things this does:

- **`python.defaultInterpreterPath`** — on Windows, uses the venv's Python automatically. On macOS/Linux, change the value to `.venv/bin/python`.
- **`jupyter.notebookFileRoot`** — sets the working directory for notebooks to the project root. This means `sys.path.append('..')` in the notebooks can be simplified, and relative paths like `data/raw/` work consistently.

If you commit `.vscode/settings.json`, collaborators get the same setup automatically. Some teams prefer to gitignore it and let each developer configure their own — either choice is fine. For a portfolio project, committing it helps anyone who clones the repo.

**Recommended: commit this file.** It signals that you've thought about reproducibility at the editor level, which is a small professionalism signal.

**9. Troubleshooting VS Code specifics**

| Symptom | Fix |
|---------|-----|
| Notebook shows `ModuleNotFoundError: No module named 'src'` | Kernel is wrong. Select **Python (Olist)** again. |
| `Python (Olist)` doesn't appear in the kernel picker | Restart VS Code. It caches the kernel list at startup. |
| Kernel dies immediately on start | The venv is broken or was deleted. Recreate it: `python -m venv .venv` then `pip install -r requirements.txt`. |
| Interpreter shows system Python, not `.venv` | Run **Python: Select Interpreter** again and pick the `.venv` entry explicitly. |
| Charts don't render | Ensure the notebook's kernel has `matplotlib` installed — it will if you installed from `requirements.txt`. |

---

### Why register the kernel at all if you're using VS Code?

You might wonder why Step 5 matters if VS Code can pick the venv interpreter directly.

**Two reasons:**

1. **Consistency across tools.** If you switch between browser Jupyter and VS Code, both will see the same `Python (Olist)` kernel. No surprises.
2. **Clear identity.** The kernel name `Python (Olist)` is unambiguous. When you see it selected in a notebook, you know exactly which environment you're running. The raw venv path can look similar across projects.

Registering once is cheap. It makes both workflows reliable.

### Step 6 — Create the main database

Connect as the `postgres` superuser to the default `postgres` database:

```sql
CREATE DATABASE olist;
```

That's it. No owner clause or separate user is required — `postgres` will own it automatically.

**Verify:**

```sql
SELECT datname FROM pg_database WHERE datname = 'olist';
```

Should return one row.

### Step 7 — Configure environment variables

Copy the example file and adjust as needed:

```bash
cp .env.example .env
```

Default `.env` contents:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=olist
DB_TEST_NAME=olist_test
DB_USER=postgres
DB_PASSWORD=your_postgres_password_here
```

**Replace `your_postgres_password_here` with the password you set during PostgreSQL installation.**

The project reads these variables through `src/config.py`. Two connection URLs are derived automatically:

- `DATABASE_URL` → points at `DB_NAME` (the main database)
- `TEST_DATABASE_URL` → points at `DB_TEST_NAME` (the test database)

> ⚠️ `.env` is gitignored — it will never be committed. Keep your real credentials there. Only `.env.example` (with placeholder values) is committed.

### Step 8 — Create the test database

The test suite requires a separate database. The project ships a script that creates it:

```bash
python scripts/setup_test_db.py
```

**Expected output:**

```
Setting up test database: olist_test
  host: localhost:5432
  user: postgres

Database 'olist' already exists.
Created database 'olist_test'.

Verified connection: postgres @ olist_test

Setup complete. Run `pytest` to start testing.
```

The script is idempotent — safe to run multiple times. It will:

1. Ensure the main `olist` database exists.
2. Drop and recreate `olist_test` (so each run starts from a clean state).
3. Verify the connection end to end.

### Step 9 — Download the dataset

1. Go to <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>
2. Sign in with a free Kaggle account
3. Accept the dataset's terms
4. Download the ZIP file (~45 MB)
5. Extract the 9 CSVs into `data/raw/`

**Verify** that all 9 files are present:

```bash
# macOS / Linux
ls -1 data/raw/*.csv | wc -l
# Expected: 9

# Windows PowerShell
(Get-ChildItem data/raw/*.csv).Count
# Expected: 9
```

### Step 10 — Run the pipeline

You're ready. Jump to [Running the Project](#running-the-project).

### Production deployment notes

The local setup uses the `postgres` superuser for convenience. In a production deployment:

- Create a dedicated role with least privilege:

  ```sql
  CREATE ROLE olist_app LOGIN PASSWORD '...';
  GRANT CONNECT ON DATABASE olist TO olist_app;
  GRANT USAGE ON SCHEMA public TO olist_app;
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO olist_app;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO olist_app;
  ```

- Store the password in a secrets manager, not in `.env`.
- Restrict network access with `pg_hba.conf`.
- Use a separate database for tests, and drop it after the test run.

---

## Setup — Docker (Alternative)

If you don't want to install PostgreSQL locally, use Docker Compose. This spins up a PostgreSQL 16 container and a pgAdmin web UI.

**Prerequisites:** Docker Desktop installed and running.

### Step 1 — Start the stack

From the repository root:

```bash
docker compose up -d
```

This starts two services:

- **PostgreSQL 16** on `localhost:5432` (user `postgres`, password `admin`, database `olist`)
- **pgAdmin** on <http://localhost:5050> (login: `admin@example.com` / `admin`)

> **Note 1:** If you already have a local PostgreSQL on port 5432, remap the Docker container to a different port. In `docker-compose.yml`, change `ports: - "5432:5432"` to `ports: - "5433:5432"`, and set `DB_PORT=5433` in your `.env`.

> **Note 2:** Recent pgAdmin versions reject `.local` domains. If the container exits with an email validation error, either change the email in `docker-compose.yml` to `admin@example.com`, or add `PGADMIN_CONFIG_ALLOW_SPECIAL_EMAIL_DOMAINS: "'local'"` to the pgAdmin environment block. You must run `docker compose down -v` before restarting to clear the invalid user record.

### Step 2 — Wait for the container to be healthy

```bash
docker compose ps
```

You should see `postgres` in `running (healthy)` state. If not, wait 10 seconds and check again.

### Step 3 — Create the test database inside the container

The Docker container only creates the main `olist` database on first start. The test database is created by the setup script:

```bash
python scripts/setup_test_db.py
```

### Step 4 — Run the pipeline

```bash
python -m scripts.run_pipeline
```

Or the direct form:

```bash
python scripts/run_pipeline.py
```

### Step 5 — Stop the stack when done

```bash
# Stop but keep data
docker compose down

# Stop and wipe the database volume
docker compose down -v
```

### Connecting from a SQL client

| Setting | Value |
|---------|-------|
| Host | `localhost` |
| Port | `5432` (or `5433` if remapped) |
| Database | `olist` (or `olist_test`) |
| User | `postgres` |
| Password | `admin` |

---

## Running the Project

There are two ways to run everything: **one command** or **step by step**.

### Option A — One command (recommended)

From the project root:

```bash
python -m scripts.run_pipeline
```

Or, equivalently:

```bash
python scripts/run_pipeline.py
```

Both forms work — the script has a `sys.path` bootstrap so it runs correctly even when invoked directly.

This runs the complete pipeline:

1. Rebuilds the PostgreSQL schema (drops and recreates tables)
2. Loads all 9 CSVs via `COPY`
3. Builds feature tables and writes them to `data/processed/`

**Expected output:**

```
==============================================================
Olist pipeline — target: PostgreSQL
==============================================================

[1/2] Extract → Transform → Load
Rebuilding schema ...
Schema ready.
LOAD  customers -> customers (99,441 rows)
customers done via COPY
LOAD  geolocation -> geolocation (1,000,163 rows)
geolocation done via COPY
...
DONE  ETL complete.

[2/2] Feature engineering
OK    features_orders: (99441, 17)
[orders] done in 3.42s
OK    features_customers: (96096, 16)
[customers] done in 2.10s
OK    features_products: (32951, 9)
[products] done in 4.87s
OK    features_sellers: (3095, 8)
[sellers] done in 1.93s

Pipeline complete.
```

Total runtime on a typical laptop: **~60 seconds**.

### Option B — Step by step

**1. Run the ETL:**

```bash
python -m src.etl
```

This loads the 9 raw tables into PostgreSQL.

**2. Build feature tables:**

```bash
python -m src.features
```

This reads the Parquet files written by the ETL and produces `features_*.parquet`.

**3. Launch Jupyter:**

```bash
jupyter notebook
```

Or, if using VS Code, open any notebook and select the **Python (Olist)** kernel.

**4. Run the notebooks in order:**

1. `01_eda.ipynb` — exploratory analysis
2. `02_feature_engineering.ipynb` — feature construction
3. `03_business_analysis.ipynb` — KPIs and charts
4. `04_sql_showcase.ipynb` — SQL demonstrations against PostgreSQL

Each notebook appends the project root to `sys.path` so `from src...` imports work regardless of where Jupyter was launched.

**5. Generate the business insights document:**

```bash
python scripts/generate_insights.py
```

See [Generating the insights document](#generating-the-insights-document) below.

### Generating the insights document

`scripts/generate_insights.py` produces `final_insights.docx` — a Word document with executive summary, KPI tables, and embedded charts.

**When to run it:** after the ETL has run and after notebooks 02 and 03 have been executed. Those notebooks produce the charts saved in `visuals/` and the feature Parquets in `data/processed/` that the script reads.

**How to run it:**

```bash
python scripts/generate_insights.py
```

Or, if you prefer module form:

```bash
python -m scripts.generate_insights
```

**Expected output:**

```
Connecting to PostgreSQL ...
Fetching metrics and building document ...
Saved: /path/to/olist-ecommerce-analysis/final_insights.docx
```

**What it does:**

- Queries PostgreSQL for live KPIs, category breakdowns, state revenue, delivery performance, and payment mix.
- Reads `features_customers.parquet` for the RFM segment distribution.
- Embeds the PNG charts from `visuals/` — if a chart is missing, it inserts a gray placeholder so the document still builds.
- Writes a fully formatted `.docx` with headings, tables, and images.

**Why the numbers are live:** the script pulls from the database and Parquet files, not hardcoded values. Change the pipeline, re-run the script, and `final_insights.docx` updates automatically. That's reproducibility.

**Prerequisite artifacts:**

| File | Produced by |
|------|-------------|
| `visuals/03_monthly_revenue.png` | `03_business_analysis.ipynb` |
| `visuals/03_top_categories.png` | `03_business_analysis.ipynb` |
| `visuals/03_geo_distribution.png` | `03_business_analysis.ipynb` |
| `visuals/03_delivery_buckets.png` | `03_business_analysis.ipynb` |
| `visuals/03_delay_vs_reviews.png` | `03_business_analysis.ipynb` |
| `visuals/03_payment_types.png` | `03_business_analysis.ipynb` |
| `visuals/03_review_distribution.png` | `03_business_analysis.ipynb` |
| `visuals/02_rfm_segments.png` | `02_feature_engineering.ipynb` |
| `data/processed/features_customers.parquet` | `02_feature_engineering.ipynb` |

If any of these are missing, the script prints a warning and inserts a placeholder in the document instead of crashing. That keeps the report buildable even in partial-pipeline scenarios.

### Verifying the load

```bash
psql -h localhost -U postgres -d olist -c "SELECT COUNT(*) FROM orders;"
```

Expected: `99441`.

Or check several tables at once:

```sql
SELECT 'orders' AS table_name, COUNT(*) FROM orders
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL SELECT 'geolocation', COUNT(*) FROM geolocation
UNION ALL SELECT 'category_translation', COUNT(*) FROM category_translation;
```

### Cleaning generated artifacts

```bash
# macOS / Linux
rm -rf data/processed/*.parquet visuals/*.png
find . -type d -name __pycache__ -exec rm -rf {} +
rm -rf .pytest_cache

# Windows PowerShell
Remove-Item -Recurse -Force data/processed/*.parquet, visuals/*.png -ErrorAction Ignore
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Remove-Item -Recurse -Force .pytest_cache -ErrorAction Ignore
```

---

## Notebooks Overview

| # | Notebook | Purpose | Audience |
|---|----------|---------|----------|
| 01 | `01_eda.ipynb` | Data quality, distributions, coverage, missingness | Analyst |
| 02 | `02_feature_engineering.ipynb` | Build order/customer/product/seller feature tables | Analyst + Engineer |
| 03 | `03_business_analysis.ipynb` | KPIs, trends, delivery impact, payment mix, review distribution | Analyst |
| 04 | `04_sql_showcase.ipynb` | Run and inspect SQL queries against PostgreSQL | SQL reviewer |

Every notebook:

- Appends the project root to `sys.path` for reliable imports.
- Uses `src/viz.py` for consistent chart styling.
- Saves PNGs to `visuals/` for reuse in the business document.
- Prints intermediate results so a reviewer can follow the logic without running anything.

---

## SQL Files

### `sql/01_schema.sql`

DDL for all 9 tables plus indexes. Idempotent — drops and recreates. Design notes:

- **No foreign keys** — the source data has known orphan rows. Correctness is enforced via `LEFT JOIN`s in analysis, not schema constraints.
- **`NUMERIC(10,2)` for money** — never `FLOAT` for currency.
- **Native `TIMESTAMP`** — enables efficient comparisons and indexing.
- **Misspelled columns preserved** (`product_name_lenght`) — matches the source.

### `sql/02_analysis_queries.sql`

Core KPI queries. Each section is delimited by `-- @@NAME` so notebooks can load and run them individually. Covers:

- Overall KPIs (revenue, orders, unique customers)
- Order status distribution
- Monthly revenue trend
- Top categories by revenue
- Geographic revenue breakdown
- Delivery performance buckets
- Review score distribution
- Payment method breakdown

### `sql/03_advanced_queries.sql`

Advanced SQL demonstrating:

- **CTEs** (`WITH ... AS`) — chained staged logic
- **Window functions** — `RANK()`, `NTILE()`, `LAG()`, `SUM() OVER`
- **Month-over-month growth** with running totals
- **Top-N per group** via `RANK() PARTITION BY`
- **RFM segmentation** via `NTILE(5)`
- **Delay vs review score** correlation

All queries are Postgres-native. They use `EXTRACT(EPOCH FROM interval) / 86400` for day calculations and `DATE_TRUNC('month', ts)` for bucketing.

---

## Source Code (`src/`)

Every module is documented with docstrings and inline comments so it can be read and defended in a code review.

| Module | Purpose |
|--------|---------|
| `config.py` | All paths, DB credentials, dataset metadata, CSV/table mappings, `DATABASE_URL`, `TEST_DATABASE_URL` |
| `db_utils.py` | SQLAlchemy engine factory, query helpers, `COPY` bulk loader |
| `etl.py` | Extract → Transform → Load pipeline for the 9 tables |
| `features.py` | Order/customer/product/seller feature engineering |
| `viz.py` | Matplotlib/Seaborn style + reusable chart functions |

### Design principles

- **Config-as-code.** No module hardcodes a path or credential; everything reads from `config.py`.
- **Idempotent ETL.** Running the pipeline twice produces identical state.
- **Postgres-only.** No dialect branching in application code. The schema and queries are Postgres-native.
- **Bulk-first loading.** `COPY` for speed with `to_sql` as a graceful fallback.
- **Testable functions.** Business logic is separated from orchestration so it can be unit-tested.

---

## Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `setup_test_db.py` | Ensures the main database exists and recreates the test database (`olist_test`). Reads credentials from `.env`; uses PostgreSQL `AUTOCOMMIT` because `CREATE DATABASE` cannot run inside a transaction. |
| `run_pipeline.py` | One-command ETL + feature pipeline. Also callable as `python -m scripts.run_pipeline`. |
| `generate_insights.py` | Builds `final_insights.docx` by pulling live KPIs from PostgreSQL and embedding the charts from `visuals/`. Also callable as `python -m scripts.generate_insights`. |

All scripts include a `sys.path` bootstrap so they run correctly whether invoked as a module (`python -m scripts.X`) or as a file path (`python scripts/X.py`).

---

## Testing

Tests live in `tests/` and use `pytest`. **All tests run against a real PostgreSQL database** (`olist_test`) — there is no SQLite fallback. This ensures the schema, DDL, and Postgres-specific SQL are exercised against the same engine used in production.

### One-time setup

The test database must exist before running `pytest`. The project ships a script:

```bash
python scripts/setup_test_db.py
```

This reads credentials from `.env`, drops any existing `olist_test`, recreates it fresh, and verifies the connection. Run it once (or any time you want a clean slate).

### Running tests

```bash
# Run all tests (verbose)
pytest tests/ -v

# Run a single file
pytest tests/test_etl.py -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing
```

**Expected output:**

```
================================================ test session starts =================================================
collected 11 items

tests/test_etl.py::test_schema_creates_expected_tables PASSED                                                    [  9%]
tests/test_etl.py::test_schema_uses_native_timestamps PASSED                                                      [ 18%]
tests/test_etl.py::test_schema_indexes_are_created PASSED                                                         [ 27%]
tests/test_etl.py::test_transform_parses_datetimes PASSED                                                         [ 36%]
tests/test_etl.py::test_transform_strips_strings PASSED                                                           [ 45%]
tests/test_etl.py::test_transform_dedupes_reviews PASSED                                                          [ 54%]
tests/test_etl.py::test_transform_casts_float_integers PASSED                                                     [ 63%]
tests/test_etl.py::test_transform_preserves_nulls_in_integer_columns PASSED                                       [ 72%]
tests/test_features.py::test_days_between_basic PASSED                                                            [ 81%]
tests/test_features.py::test_days_between_preserves_nat PASSED                                                    [ 90%]
tests/test_features.py::test_rfm_scores_in_range PASSED                                                           [100%]

================================================= 11 passed in 1.84s ==================================================
```

### How the fixtures work

- **`tests/conftest.py`** defines a session-scoped `engine` fixture that connects to `TEST_DATABASE_URL`, verifies the connection, and rebuilds the schema once per session.
- If the test database is unreachable, the fixture calls `pytest.exit` with a clear error message — a missing DB is a real configuration problem, not something to skip silently.
- Tests that insert data can use the `clean_tables` fixture to truncate every table before they run.

### What's covered

| Test | Verifies |
|------|----------|
| `test_schema_creates_expected_tables` | All 9 tables exist in `public` |
| `test_schema_uses_native_timestamps` | Timestamps are `timestamp without time zone`, not `TEXT` |
| `test_schema_indexes_are_created` | All 7 declared indexes exist |
| `test_transform_parses_datetimes` | Date strings become `datetime64` |
| `test_transform_strips_strings` | Whitespace is stripped from string columns |
| `test_transform_dedupes_reviews` | `review_id` deduplication keeps the latest answer |
| `test_transform_casts_float_integers` | Float-stored integers (`"40.0"`) become true integers |
| `test_transform_preserves_nulls_in_integer_columns` | Nullable integer columns retain nulls |
| `test_days_between_basic` | Day arithmetic works |
| `test_days_between_preserves_nat` | `NaT` inputs produce `NaN`, not `0` |
| `test_rfm_scores_in_range` | RFM quintiles are always 1–5 |

### Why Postgres instead of SQLite

Earlier iterations used SQLite in-memory for speed. That approach has two problems:

1. **Dialect drift.** Postgres-specific syntax (`DROP TABLE ... CASCADE`, `TRUNCATE`, `information_schema` behavior, native `TIMESTAMP` types) fails or behaves differently in SQLite. Tests that pass under SQLite don't guarantee the code works in production.
2. **Maintenance burden.** Every Postgres feature requires a SQLite compatibility shim. That's complexity in the test suite with no corresponding benefit to the application.

Using PostgreSQL for tests eliminates both problems. The trade-off is that tests require a running Postgres — acceptable for a project that already requires Postgres for the pipeline.

---

## Key Findings

Full write-up in [`final_insights.docx`](final_insights.docx). Highlights:

### Revenue

- **~R$15.8M** in total revenue across delivered orders.
- **São Paulo (SP)** alone accounts for roughly a third of both revenue and orders.
- **November 2017** (Black Friday) is the single largest revenue month on record.
- Revenue is concentrated in a small number of product categories: `bed_bath_table`, `health_beauty`, `sports_leisure`, `computers_accessories`, `furniture_decor`.

### Delivery

- Average delivery time is **~12 days**.
- Roughly **8%** of orders arrive after the estimated delivery date.
- **Late delivery has a disproportionate impact on satisfaction:** average review score drops from **~4.3** (early) to **~2.5** (late) — a ~40% reduction.

### Customers

- **~96K unique customers** in the analysis window.
- Repeat purchase rate is very low — **~97%** of customers place a single order.
- RFM segmentation reveals a small **Champion** segment and a larger **Lost** segment.

### Payments

- **Credit card** dominates at ~74% of payments.
- **Boleto** (Brazilian bank slip) is second at ~19%.
- Most credit card customers choose a **single installment** (no financing).

### Reviews

- Bimodal distribution: **~57%** 5-star and **~12%** 1-star.
- Review scores correlate strongly with delivery performance — logistics is the biggest lever on satisfaction.

---

## Troubleshooting

### `psql: error: connection to server at "localhost" ... failed`

PostgreSQL isn't running, or you're connecting to the wrong host/port.

- **Windows:** Check Services → `postgresql-x64-*` is Running.
- **macOS:** `brew services list` — confirm postgresql is `started`.
- **Linux:** `sudo systemctl status postgresql`.
- Confirm your `.env` matches your actual Postgres port (default 5432).

### `FATAL: password authentication failed for user "postgres"`

Your `.env` password doesn't match the one you set when installing PostgreSQL. Either:

- Edit `.env` to match, or
- Reset the password in Postgres:

```sql
ALTER USER postgres WITH PASSWORD 'newpassword';
```

### `ERROR: CREATE DATABASE cannot run inside a transaction block`

Some SQL clients (DBeaver, pgAdmin with "begin transaction" enabled) wrap statements in a transaction, and PostgreSQL refuses to run `CREATE DATABASE` inside one.

**Fix:** use the project's setup script, which connects with `AUTOCOMMIT`:

```bash
python scripts/setup_test_db.py
```

Or, in your SQL client, disable auto-commit / begin-transaction, then re-run `CREATE DATABASE`.

### `pytest: sqlite3.ProgrammingError: You can only execute one statement at a time`

You have an older `tests/test_etl.py` that uses SQLite. The current version runs against PostgreSQL. Replace `tests/test_etl.py` with the Postgres version, and make sure `tests/conftest.py` exists.

**Verify:**

```powershell
Get-Content tests\test_etl.py | Select-String -Pattern "sqlite|tmp_path"
```

Should print nothing. If it prints lines, the file still has the old content.

### `ModuleNotFoundError: No module named 'src'`

Happens when a script or notebook can't find the `src/` package.

**For scripts:**
- Run as a module: `python -m scripts.run_pipeline` from the project root.
- Or rely on the built-in `sys.path` bootstrap in `scripts/run_pipeline.py`, `scripts/generate_insights.py`, and `scripts/setup_test_db.py` — all add the project root to `sys.path` automatically.

**For notebooks:**
- Confirm the **Python (Olist)** kernel is selected in the notebook.
- Confirm the venv is activated (`which python` / `where python`).
- Ensure the first notebook cell appends the project root to `sys.path`.

### `invalid input syntax for type integer: "40.0"` (products COPY failure)

Some source CSVs store integers as floats. The ETL handles this via `INTEGER_COLUMNS` in `src/config.py`. If you see this error:

- Ensure `src/config.py` contains the `INTEGER_COLUMNS` map.
- Ensure `src/etl.py`'s `transform()` applies the integer cast before string cleanup.

### `Pandas4Warning: For backward compatibility, 'str' dtypes are included by select_dtypes...`

Pandas 2.x deprecation. Fix:

```python
# Instead of:
string_cols = df.select_dtypes(include=["object"]).columns

# Use:
string_cols = df.select_dtypes(include=["object", "str"]).columns
```

This is already applied in `src/etl.py`.

### Feature engineering is slow (>30 seconds)

Verify `build_customer_features()` uses a vectorized RFM (no lambdas inside `.agg()`). See the docstring in `src/features.py`.

### Kernel "hangs" during `build_all_features()`

Most common cause is the old RFM implementation with a lambda. The corrected version in `src/features.py` completes in ~2 seconds. If still slow, check:

- Disk I/O — avoid running from OneDrive/Dropbox/iCloud-synced folders.
- Memory — close other applications; 96K customers is small but a heavily loaded machine can swap.
- Pandas version — `pip install --upgrade "pandas>=2.1"`.

### `generate_insights.py` inserts placeholder text instead of charts

The charts are produced by notebooks 02 and 03. If you haven't run those notebooks yet, `visuals/` is empty and the script substitutes placeholders.

**Fix:** run `01_eda.ipynb`, `02_feature_engineering.ipynb`, and `03_business_analysis.ipynb` in order, then re-run `python scripts/generate_insights.py`.

### `generate_insights.py` fails with `FileNotFoundError: features_customers.parquet`

The RFM feature table is produced by notebook 02 or by `python -m src.features`. Run one of those first.

**Fix:**

```bash
python -m src.features
```

Then re-run the script.

### `generate_insights.py` fails with a psycopg2 connection error

The script queries PostgreSQL for its KPI tables. Confirm:

- The ETL has already loaded the database (`python -m scripts.run_pipeline`).
- `.env` points at a reachable Postgres instance.
- The database user has `SELECT` privileges on all tables.

### `pytest` fails with `Cannot connect to test database at ...`

The `engine` fixture in `tests/conftest.py` couldn't reach `olist_test`. Confirm:

- PostgreSQL is running (`pg_isready` or check the service).
- `olist_test` exists — create it with `python scripts/setup_test_db.py`.
- `.env` has `DB_TEST_NAME=olist_test` and the correct credentials.

### Docker: `unable to get image 'dpage/pgadmin4:latest'` on Windows

Docker Desktop isn't running, or its engine is stopped. Start Docker Desktop, wait for "Docker Desktop is running," then retry `docker compose up -d`. If the engine is stuck, run `wsl --update` and restart the machine.

### Docker: port 5432 already in use

You already have a local PostgreSQL on 5432. Remap the container to 5433:

```yaml
ports:
  - "5433:5432"
```

And set `DB_PORT=5433` in `.env`.

### pgAdmin: `'admin@olist.local' does not appear to be a valid email address`

Recent pgAdmin versions reject `.local` domains. Two options:

1. Change the email in `docker-compose.yml` to `admin@example.com`.
2. Add `PGADMIN_CONFIG_ALLOW_SPECIAL_EMAIL_DOMAINS: "'local'"` to the pgAdmin environment.

You must run `docker compose down -v` after either change — pgAdmin only reads the default email on first container start.

---

## License

This repository contains two kinds of content, licensed differently:

### Source code — MIT License

All source code in this repository (`src/`, `sql/`, `scripts/`, `tests/`, `notebooks/`, configuration files) is licensed under the **MIT License**. See [`LICENSE`](LICENSE) for the full text.

You may use, modify, and redistribute the code freely, including for commercial purposes.

### Dataset and derived outputs — CC BY-NC-SA 4.0

The analysis is built on the **Brazilian E-Commerce Public Dataset by Olist**, which is licensed under **CC BY-NC-SA 4.0**. Analytical outputs in this repository (aggregated statistics, charts, notebooks computing results from the dataset) are derivatives of the dataset and inherit the same license.

See [`LICENSE-DATA`](LICENSE-DATA) for the full notice and [`data/README.md`](data/README.md) for dataset-specific documentation.

**Summary:**

| Content | License | Commercial use? |
|---------|---------|-----------------|
| Source code | MIT | ✅ Yes |
| Dataset & derived analytics | CC BY-NC-SA 4.0 | ❌ No |

The dataset itself is not redistributed here. Download it directly from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

### Attribution

> Olist. (2018). *Brazilian E-Commerce Public Dataset by Olist*. Kaggle.
> https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

### Contributions

Issues and pull requests are welcome. Please keep the code style consistent with the existing modules (type hints, docstrings, comments where non-obvious).

---

**Built as a portfolio project.** If you find the structure useful for your own project, fork it — attribution appreciated.