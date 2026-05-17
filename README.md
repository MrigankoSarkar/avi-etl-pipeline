# All India Villages API ETL Pipeline

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
If you'd like, I can now:

- Add automated tests for the cleaning functions (pytest + sample fixtures)
- Implement chunked COPY-based ingestion for high-volume uploads
- Add a detailed `CONTRIBUTING.md` and `DEVELOPMENT.md` for ETL maintainers

Which of these would you like me to do next?
