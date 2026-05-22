# All India Villages API ETL Pipeline

<p align="center">
  Production-grade ETL pipeline for cleaning, validating, normalizing, and ingesting MDDS-style Indian administrative geography datasets into PostgreSQL.
</p>

<p align="center">

  <!-- Documentation -->
  <a href="https://avi-docs.readthedocs.io/" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/readthedocs/avi-docs?style=for-the-badge" alt="Read the Docs">
  </a>

  <!-- License -->
  <a href="./LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT License">
  </a>

  <!-- Repo Stats -->
  <img src="https://img.shields.io/github/stars/MrigankoSarkar/All_India_Villages_API?style=for-the-badge" alt="Stars">

  <img src="https://img.shields.io/github/forks/MrigankoSarkar/All_India_Villages_API?style=for-the-badge" alt="Forks">

  <img src="https://img.shields.io/github/issues/MrigankoSarkar/All_India_Villages_API?style=for-the-badge" alt="Issues">

</p>

---

## Tech Stacks

<p align="center">

  <!-- Python -->
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python" alt="Python">

  <!-- Flask -->
  <img src="https://img.shields.io/badge/Flask-3-black?style=for-the-badge&logo=flask" alt="Flask">

  <!-- PostgreSQL -->
  <img src="https://img.shields.io/badge/PostgreSQL-16-blue?style=for-the-badge&logo=postgresql" alt="PostgreSQL">

  <!-- Pandas -->
  <img src="https://img.shields.io/badge/Pandas-2-darkblue?style=for-the-badge&logo=pandas" alt="Pandas">

  <!-- Neon -->
  <img src="https://img.shields.io/badge/Neon-Postgres-00E599?style=for-the-badge" alt="Neon">

</p>

---

## Deployments


<p align="center">

  <!-- Main Website -->
  <a href="https://all-india-villages-api-lyart.vercel.app" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/Live_Website-All_India_Villages_API-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Live Website">
  </a>

  <!-- ETL Pipeline Website -->
  <a href="https://avi-etl-pipeline.onrender.com/" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/ETL_Pipeline_Website-Cloud_Hosting-5A67D8?style=for-the-badge&logo=render&logoColor=white" alt="Render">
  </a>

  <!-- Neon -->
  <a href="https://neon.com/" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/Neon-Serverless_Postgres-00E599?style=for-the-badge&logo=neon&logoColor=black" alt="Neon">
  </a>

  <!-- Render -->
  <a href="https://render.com/" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/Render-Cloud_Hosting-5A67D8?style=for-the-badge&logo=render&logoColor=white" alt="Render">
  </a>

</p>

---

## Social & Contact

<p align="center">

  <!-- GitHub -->
  <a href="https://github.com/MrigankoSarkar" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub">
  </a>

  <!-- LinkedIn -->
  <a href="https://www.linkedin.com/in/mriganko-sarkar-4446aa250" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn">
  </a>

  <!-- Instagram -->
  <a href="https://www.instagram.com/mrigankosarkar2004/" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" alt="Instagram">
  </a>

  <!-- Facebook -->
  <a href="https://www.facebook.com/profile.php?id=100086938462226" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white" alt="Facebook">
  </a>

  <!-- Gmail -->
  <a href="mailto:mrigankosarkar04@gmail.com" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email">
  </a>

</p>

---
## Overview

The **All India Villages API ETL Pipeline** is a production-focused Flask-based ETL service designed to clean, validate, normalize, and ingest hierarchical Indian administrative geography datasets into PostgreSQL-compatible databases.

The system supports:

- MDDS-compatible administrative geography ingestion
- CSV and Excel uploads
- Deterministic data normalization
- Idempotent PostgreSQL inserts
- Hierarchical relational modeling
- Internal ETL workflows for geography APIs and analytics systems

---

## Features

- CSV / XLS / XLSX ingestion
- Automatic column normalization
- Deduplication and validation
- PostgreSQL + Neon support
- Idempotent `ON CONFLICT` ingestion
- Hierarchical geography modeling
- Flask-based upload UI
- Downloadable cleaned datasets
- Transaction-safe inserts
- UTF-8 + latin1 CSV support

---




## ETL Pipeline Workflows

Production-grade ETL utility for cleaning, validating, and ingesting MDDS-like administrative
geography datasets (Country → State → District → Subdistrict → Village) into a PostgreSQL
instance (Neon recommended).

This repository contains a small Flask web application that provides two main flows:

- `/upload` — accepts a CSV/XLS/XLSX file, performs deterministic cleaning and normalization,
	and returns a cleaned CSV for download.
- `/upload-to-db` — accepts a CSV/XLS/XLSX file, cleans it, and inserts hierarchical records into
	database tables (`country`, `state`, `district`, `subdistrict`, `village`, and `village_data`).

Contents
 - **app.py** — Flask application with upload, cleaning, and DB ingestion logic
 - **requirements.txt** — Python dependencies
 - **runtime.txt** — runtime indicator (python-3.11.11)
 - **templates/index.html** — simple web UI for uploading files
 - **static/** — frontend JS and CSS used by the UI

Design goals
 - Idempotent ingestion: uses `ON CONFLICT` statements to avoid duplicates
 - Minimal required columns: enforces a small canonical set of columns and fails loudly if missing
 - Resilient DB writes: uses SQLAlchemy with transactional batch writes (`engine.begin()`)
 - Simple UX: provides a client to clean and then upload datasets

Supported input formats
 - CSV (UTF-8 preferred, falls back to latin1 on decode errors)
 - XLS / XLSX (via `pandas.read_excel`, `openpyxl`)

Expected input columns (before cleaning)
The ETL expects the source dataset to contain, or map to, the following fields (case-sensitive in
the source file after mapping performed by the ETL):

- `state_code`, `state_name`
- `district_code`, `district_name`
- `subdistrict_code`, `subdistrict_name`
- `village_code`, `village_name`

app.py behavior (key functions)
- `load_dataset(filepath)` — loads CSV or Excel into a pandas DataFrame with string dtype.
- `clean_dataset_dataframe(df)` —
	- renames known MDDS-like columns to the canonical names (see code mappings)
	- asserts required columns exist and raises if missing
	- trims whitespace, fills nulls, title-cases name fields, removes rows with empty `village_code`,
		deduplicates on `village_code`, and resets index
- `create_tables(conn)` — creates required tables (`country`, `state`, `district`, `subdistrict`,
	`village`, `village_data`) if not present. The SQL is idempotent.
- `/upload` route — accepts a file, runs cleaning, returns cleaned CSV as attachment
- `/upload-to-db` route — accepts a file, runs cleaning, and inserts hierarchical rows within a
	transaction using `ON CONFLICT DO NOTHING` to avoid duplicates. Returns JSON with insertion
	summary including `rows_inserted` and `total_rows`.

Database notes
- The app uses SQLAlchemy's `create_engine` with `connect_args` set to `sslmode=require` to
	accommodate Neon. Adjust the `DATABASE_URL` accordingly (use the Neon connection string).
- The ETL creates `village_data` as a raw/audit table in addition to normalized tables.

Environment & Dependencies
- Add a `.env` file or export `DATABASE_URL` before running. The app will fail early if
	`DATABASE_URL` is not set.
- Dependencies are listed in `requirements.txt`. Key packages:
	- Flask — web server and routes
	- pandas — data parsing and cleaning
	- SQLAlchemy — DB engine and execution
	- psycopg2-binary — Postgres driver

Quick start (local)

```bash
# create virtualenv
python -m venv .venv
# mac/linux
source .venv/bin/activate
# windows
.\.venv\Scripts\activate

pip install -r requirements.txt

# export DATABASE_URL (example)
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

python app.py

# open http://localhost:5000 to use the UI
```

Run with Gunicorn (production example)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

API examples

Upload & download cleaned dataset (curl)

```bash
curl -F "file=@raw_dataset.csv" http://localhost:5000/upload -o cleaned_dataset.csv
```

Upload and insert into DB

```bash
curl -F "file=@cleaned_dataset.csv" http://localhost:5000/upload-to-db
```

Operational considerations
- Transaction size: The app inserts rows in batches via `conn.execute(..., df.to_dict(orient="records"))`.
	For very large datasets consider chunking to avoid memory pressure.
- Indexing: Ensure database indexes exist on the unique constraints used (`country.code`,
	`(country_id, code)` on `state`, etc.) to keep `ON CONFLICT` efficient.
- SSL / networking: The app sets `sslmode=require` in the engine connect args — ensure your
	database enforces TLS and that any required client certificates or network policies are configured.
- Encoding: The loader falls back to `latin1` when reading CSVs fails with `UnicodeDecodeError`.

Security
- Protect the upload endpoints behind authentication or network controls in production. The UI is
	intended for internal ETL runs; exposing upload endpoints publicly without authentication is unsafe.
- Secrets: never commit `.env` with credentials — these are intentionally excluded via `.gitignore`.

Logging & Monitoring
- Basic `logging` is configured to INFO; failures print tracebacks. For production, attach a
	structured logger and export logs to a centralized system.
- Add health checks and metrics (e.g., Prometheus) around DB latency and rows inserted per job.

Extensibility & improvements
- Chunked inserts with COPY: For very large files prefer `COPY FROM STDIN` for bulk ingestion.
- Schema validation: add explicit schema validation (e.g., with `pandera`) to catch malformed rows.
- Job queue: integrate with a background queue (e.g., BullMQ on the Node side or RQ/Celery in Python)
	for long-running ingest jobs and to return immediate 202 responses.
- Idempotency tokens: support a job identifier to re-run safely and avoid duplicated audit writes.

Troubleshooting
- "Missing columns" error: ensure your source file contains the fields mapped in the renaming
	step; inspect the cleaned CSV by using `/upload` before sending to `/upload-to-db`.
- DB connection errors: confirm `DATABASE_URL` and network access; test with `psql` or a simple SQLAlchemy
	script to validate connectivity.

Contact & ownership
- Maintained as part of the All India Villages API project. Open issues or PRs in the parent repo.

---

## License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for details.

---

## Author

Developed and maintained by **Mriganko Sarkar**.

---

## Maintainers

Maintained by the All India Villages API contributors.

For enterprise integrations, ETL workflows, collaboration, or infrastructure support, contact via LinkedIn or email above.

---

## Documentation

Full documentation is available at: [ReadTheDocs](https://avi-docs.readthedocs.io/)