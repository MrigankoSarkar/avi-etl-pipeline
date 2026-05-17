from flask import (
    Flask,
    render_template,
    request,
    send_file,
    jsonify
)

import os
import re
import logging
import pandas as pd

from dotenv import load_dotenv

from werkzeug.utils import secure_filename

from sqlalchemy import create_engine
from sqlalchemy import text

from sqlalchemy.exc import SQLAlchemyError


# =========================================================
# LOAD ENV VARIABLES
# =========================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:

    raise Exception(

        "DATABASE_URL missing in .env"

    )


# =========================================================
# APP CONFIG
# =========================================================

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

UPLOAD_FOLDER = "uploads"

OUTPUT_FOLDER = "cleaned_output"

ALLOWED_EXTENSIONS = {

    "csv",
    "xls",
    "xlsx"

}

os.makedirs(

    UPLOAD_FOLDER,

    exist_ok=True

)

os.makedirs(

    OUTPUT_FOLDER,

    exist_ok=True

)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s - %(levelname)s - %(message)s"

)


# =========================================================
# DATABASE ENGINE
# =========================================================

engine = create_engine(

    DATABASE_URL,

    pool_pre_ping=True,

    pool_recycle=300,

    pool_size=5,

    max_overflow=10,

    future=True,

    connect_args={

        "sslmode": "require"

    }

)

logging.info(

    "Connected To NeonDB"

)


# =========================================================
# FILE VALIDATION
# =========================================================

def allowed_file(filename):

    return (

        "." in filename

        and

        filename.rsplit(".", 1)[1].lower()

        in ALLOWED_EXTENSIONS

    )


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(value):

    if pd.isna(value):

        return ""

    return str(value).strip().title()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(

        "index.html"

    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "healthy"

    })


# =========================================================
# CLEAN DATASET
# =========================================================

@app.route("/upload", methods=["POST"])
def upload_file():

    try:

        # =====================================================
        # GET FILE
        # =====================================================

        file = request.files.get("file")

        if not file:

            return jsonify({

                "error": "No file uploaded"

            }), 400

        if file.filename == "":

            return jsonify({

                "error": "Empty filename"

            }), 400

        if not allowed_file(file.filename):

            return jsonify({

                "error": "Unsupported file format"

            }), 400

        # =====================================================
        # SAVE FILE
        # =====================================================

        filename = secure_filename(

            file.filename

        )

        upload_path = os.path.join(

            UPLOAD_FOLDER,

            filename

        )

        file.save(upload_path)

        logging.info(

            f"Uploaded file: {filename}"

        )

        # =====================================================
        # LOAD DATASET
        # =====================================================

        if filename.lower().endswith(".csv"):

            try:

                df = pd.read_csv(

                    upload_path,

                    dtype=str,

                    encoding="utf-8"

                )

            except UnicodeDecodeError:

                df = pd.read_csv(

                    upload_path,

                    dtype=str,

                    encoding="latin1"

                )

        else:

            df = pd.read_excel(

                upload_path,

                dtype=str

            )

        # =====================================================
        # RENAME COLUMNS
        # =====================================================

        df = df.rename(columns={

            "MDDS STC": "state_code",

            "STATE NAME": "state_name",

            "MDDS DTC": "district_code",

            "DISTRICT NAME": "district_name",

            "MDDS Sub_DT": "subdistrict_code",

            "SUB-DISTRICT NAME": "subdistrict_name",

            "MDDS PLCN": "village_code",

            "Area Name": "village_name"

        })

        # =====================================================
        # REQUIRED SCHEMA
        # =====================================================

        schema_columns = [

            "state_code",
            "state_name",

            "district_code",
            "district_name",

            "subdistrict_code",
            "subdistrict_name",

            "village_code",
            "village_name"

        ]

        missing_columns = [

            col

            for col in schema_columns

            if col not in df.columns

        ]

        if missing_columns:

            return jsonify({

                "error": f"Missing columns: {missing_columns}"

            }), 400

        # =====================================================
        # KEEP REQUIRED COLUMNS
        # =====================================================

        df = df[schema_columns]

        # =====================================================
        # CLEAN TEXT
        # =====================================================

        text_columns = [

            "state_name",

            "district_name",

            "subdistrict_name",

            "village_name"

        ]

        for col in text_columns:

            df[col] = df[col].apply(

                clean_text

            )

        # =====================================================
        # CLEAN CODE COLUMNS
        # =====================================================

        code_columns = [

            "state_code",

            "district_code",

            "subdistrict_code",

            "village_code"

        ]

        for col in code_columns:

            df[col] = (

                df[col]

                .fillna("")

                .astype(str)

                .str.strip()

            )

        # =====================================================
        # REMOVE NULLS
        # =====================================================

        df = df[

            df["village_code"] != ""

        ]

        # =====================================================
        # REMOVE DUPLICATES
        # =====================================================

        df = df.drop_duplicates(

            subset=["village_code"]

        )

        # =====================================================
        # RESET INDEX
        # =====================================================

        df = df.reset_index(

            drop=True

        )

        # =====================================================
        # OUTPUT FILE NAME
        # =====================================================

        base_name = os.path.splitext(

            filename

        )[0]

        match = re.search(

            r'_[0-9]+_(.+)$',

            base_name

        )

        state_name = (

            match.group(1)

            if match

            else base_name

        )

        output_filename = (

            f"cleaned_{state_name}.csv"

        )

        output_path = os.path.join(

            OUTPUT_FOLDER,

            output_filename

        )

        # =====================================================
        # SAVE CLEANED FILE
        # =====================================================

        df.to_csv(

            output_path,

            index=False

        )

        logging.info(

            f"Cleaned dataset saved: {output_filename}"

        )

        # =====================================================
        # RETURN FILE
        # =====================================================

        return send_file(

            output_path,

            as_attachment=True,

            download_name=output_filename

        )

    except Exception as e:

        logging.exception(

            "Dataset cleaning failed"

        )

        return jsonify({

            "error": str(e)

        }), 500


# =========================================================
# UPLOAD TO NEON DB
# =========================================================

@app.route("/upload-to-db", methods=["POST"])
def upload_to_db():

    try:

        # =====================================================
        # GET FILE
        # =====================================================

        file = request.files.get("file")

        if not file:

            return jsonify({

                "error": "No file uploaded"

            }), 400

        if file.filename == "":

            return jsonify({

                "error": "Empty filename"

            }), 400

        if not file.filename.lower().endswith(".csv"):

            return jsonify({

                "error": "Only CSV files allowed"

            }), 400

        # =====================================================
        # SAVE FILE
        # =====================================================

        filename = secure_filename(

            file.filename

        )

        upload_path = os.path.join(

            UPLOAD_FOLDER,

            filename

        )

        file.save(upload_path)

        logging.info(

            f"Database upload file received: {filename}"

        )

        # =====================================================
        # LOAD CSV
        # =====================================================

        try:

            df = pd.read_csv(

                upload_path,

                dtype=str,

                encoding="utf-8"

            )

        except UnicodeDecodeError:

            df = pd.read_csv(

                upload_path,

                dtype=str,

                encoding="latin1"

            )

        # =====================================================
        # REQUIRED COLUMNS
        # =====================================================

        required_columns = [

            "state_code",
            "state_name",

            "district_code",
            "district_name",

            "subdistrict_code",
            "subdistrict_name",

            "village_code",
            "village_name"

        ]

        missing_columns = [

            col

            for col in required_columns

            if col not in df.columns

        ]

        if missing_columns:

            return jsonify({

                "error": f"Missing columns: {missing_columns}"

            }), 400

        # =====================================================
        # KEEP REQUIRED COLUMNS
        # =====================================================

        df = df[required_columns]

        # =====================================================
        # CLEAN DATA
        # =====================================================

        df = df.fillna("")

        for column in required_columns:

            df[column] = (

                df[column]

                .astype(str)

                .str.strip()

            )

        # =====================================================
        # REMOVE EMPTY VILLAGE CODE
        # =====================================================

        df = df[

            df["village_code"] != ""

        ]

        # =====================================================
        # REMOVE DUPLICATES
        # =====================================================

        df = df.drop_duplicates(

            subset=["village_code"]

        )

        # =====================================================
        # RESET INDEX
        # =====================================================

        df = df.reset_index(

            drop=True

        )

        # =====================================================
        # CREATE TABLE
        # =====================================================

        create_table_query = text("""

            CREATE TABLE IF NOT EXISTS village_data (

                id BIGSERIAL PRIMARY KEY,

                state_code TEXT,

                state_name TEXT,

                district_code TEXT,

                district_name TEXT,

                subdistrict_code TEXT,

                subdistrict_name TEXT,

                village_code TEXT UNIQUE,

                village_name TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )

        """)

        # =====================================================
        # CREATE INDEX
        # =====================================================

        create_index_query = text("""

            CREATE INDEX IF NOT EXISTS idx_village_code

            ON village_data(village_code)

        """)

        inserted_rows = 0

        records = df.to_dict(

            orient="records"

        )

        # =====================================================
        # DATABASE TRANSACTION
        # =====================================================

        with engine.begin() as conn:

            conn.execute(

                create_table_query

            )

            conn.execute(

                create_index_query

            )

            insert_query = text("""

                INSERT INTO village_data (

                    state_code,
                    state_name,

                    district_code,
                    district_name,

                    subdistrict_code,
                    subdistrict_name,

                    village_code,
                    village_name

                )

                VALUES (

                    :state_code,
                    :state_name,

                    :district_code,
                    :district_name,

                    :subdistrict_code,
                    :subdistrict_name,

                    :village_code,
                    :village_name

                )

                ON CONFLICT (village_code)

                DO NOTHING

            """)

            # =================================================
            # BATCH INSERT
            # =================================================

            batch_size = 1000

            for i in range(

                0,

                len(records),

                batch_size

            ):

                batch = records[i:i + batch_size]

                conn.execute(

                    insert_query,

                    batch

                )

                inserted_rows += len(batch)

        logging.info(

            f"Inserted {inserted_rows} rows into NeonDB"

        )

        # =====================================================
        # VERIFY INSERTION
        # =====================================================

        with engine.connect() as conn:

            result = conn.execute(text("""

                SELECT COUNT(*) AS total

                FROM village_data

            """))

            total_rows = result.scalar()

        return jsonify({

            "success": True,

            "message": "Dataset uploaded successfully",

            "rows_inserted": inserted_rows,

            "total_rows_in_db": total_rows

        })

    except SQLAlchemyError as e:

        logging.exception(

            "Database upload failed"

        )

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500

    except Exception as e:

        logging.exception(

            "Unexpected upload error"

        )

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=False

    )