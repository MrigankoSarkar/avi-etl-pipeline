from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    send_file
)

import os
import logging
import traceback
import pandas as pd

from dotenv import load_dotenv

from werkzeug.utils import secure_filename

from sqlalchemy import (
    create_engine,
    text
)

from sqlalchemy.exc import SQLAlchemyError


# =========================================================
# LOAD ENV
# =========================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL missing in .env")


# =========================================================
# APP CONFIG
# =========================================================

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "cleaned_output"

ALLOWED_EXTENSIONS = {
    "csv",
    "xls",
    "xlsx"
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


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
    future=True,
    connect_args={
        "sslmode": "require"
    }
)

logging.info("Connected To NeonDB")


# =========================================================
# HELPERS
# =========================================================

def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def clean_text(value):

    if pd.isna(value):
        return ""

    return str(value).strip().title()


def get_single_value(conn, query, params=None):

    return conn.execute(
        text(query),
        params or {}
    ).scalar()


# =========================================================
# LOAD DATASET
# =========================================================

def load_dataset(filepath):

    extension = filepath.split(".")[-1].lower()

    if extension == "csv":

        try:

            df = pd.read_csv(
                filepath,
                dtype=str,
                encoding="utf-8"
            )

        except UnicodeDecodeError:

            df = pd.read_csv(
                filepath,
                dtype=str,
                encoding="latin1"
            )

    elif extension in ["xls", "xlsx"]:

        df = pd.read_excel(
            filepath,
            dtype=str
        )

    else:

        raise Exception("Unsupported file type")

    return df


# =========================================================
# CLEAN DATASET
# =========================================================

def clean_dataset_dataframe(df):

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

        raise Exception(
            f"Missing columns: {missing_columns}"
        )

    # =====================================================
    # KEEP REQUIRED
    # =====================================================

    df = df[required_columns]

    # =====================================================
    # CLEAN NULLS
    # =====================================================

    df = df.fillna("")

    # =====================================================
    # STRING CLEANING
    # =====================================================

    for col in required_columns:

        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
        )

    # =====================================================
    # CLEAN TEXT COLUMNS
    # =====================================================

    text_columns = [

        "state_name",
        "district_name",
        "subdistrict_name",
        "village_name"

    ]

    for col in text_columns:

        df[col] = df[col].apply(clean_text)

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

    df = df.reset_index(drop=True)

    return df


# =========================================================
# CREATE TABLES
# =========================================================

def create_tables(conn):

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS country (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            code TEXT UNIQUE NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

    """))

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS state (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            code TEXT NOT NULL,

            country_id INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(country_id, code)

        )

    """))

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS district (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            code TEXT NOT NULL,

            state_id INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(state_id, code)

        )

    """))

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS subdistrict (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            code TEXT NOT NULL,

            district_id INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(district_id, code)

        )

    """))

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS village (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            code TEXT NOT NULL,

            subdistrict_id INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(subdistrict_id, code)

        )

    """))

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS village_data (

            id SERIAL PRIMARY KEY,

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

    """))


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    logging.info("Homepage Opened")

    return render_template("index.html")


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "healthy",

        "message": "Server Running"

    })


# =========================================================
# CLEAN DATASET ROUTE
# =========================================================

@app.route("/upload", methods=["POST"])
def clean_dataset():

    try:

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
                "error": "Invalid file format"
            }), 400

        filename = secure_filename(file.filename)

        upload_path = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        file.save(upload_path)

        logging.info(
            "Dataset cleaning initialized"
        )

        # =================================================
        # LOAD DATA
        # =================================================

        df = load_dataset(upload_path)

        # =================================================
        # CLEAN DATA
        # =================================================

        df = clean_dataset_dataframe(df)

        # =================================================
        # OUTPUT FILE
        # =================================================

        output_filename = f"cleaned_{filename}"

        output_path = os.path.join(
            OUTPUT_FOLDER,
            output_filename
        )

        df.to_csv(
            output_path,
            index=False
        )

        logging.info(
            "Dataset cleaning completed"
        )

        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename
        )

    except Exception as e:

        logging.error(traceback.format_exc())

        return jsonify({

            "success": False,
            "error": str(e)

        }), 500


# =========================================================
# UPLOAD TO DATABASE
# =========================================================

@app.route("/upload-to-db", methods=["POST"])
def upload_to_db():

    try:

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
                "error": "Invalid file format"
            }), 400

        filename = secure_filename(file.filename)

        upload_path = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        file.save(upload_path)

        logging.info(
            "Database upload initialized"
        )

        # =================================================
        # LOAD DATA
        # =================================================

        df = load_dataset(upload_path)

        # =================================================
        # CLEAN DATA
        # =================================================

        df = clean_dataset_dataframe(df)

        # =================================================
        # DATABASE TRANSACTION
        # =================================================

        with engine.begin() as conn:

            create_tables(conn)

            # =============================================
            # COUNTRY
            # =============================================

            conn.execute(text("""

                INSERT INTO country (

                    name,
                    code

                )

                VALUES (

                    'India',
                    'IN'

                )

                ON CONFLICT (code)
                DO NOTHING

            """))

            country_id = get_single_value(

                conn,

                """

                SELECT id
                FROM country
                WHERE code='IN'

                """

            )

            # =============================================
            # STATES
            # =============================================

            states = df[[
                "state_code",
                "state_name"
            ]].drop_duplicates()

            for _, row in states.iterrows():

                conn.execute(text("""

                    INSERT INTO state (

                        name,
                        code,
                        country_id

                    )

                    VALUES (

                        :name,
                        :code,
                        :country_id

                    )

                    ON CONFLICT (country_id, code)
                    DO NOTHING

                """), {

                    "name": row["state_name"],
                    "code": row["state_code"],
                    "country_id": country_id

                })

            # =============================================
            # DISTRICTS
            # =============================================

            districts = df[[
                "district_code",
                "district_name",
                "state_code"
            ]].drop_duplicates()

            for _, row in districts.iterrows():

                state_id = get_single_value(

                    conn,

                    """

                    SELECT id
                    FROM state
                    WHERE code=:code
                    LIMIT 1

                    """,

                    {

                        "code": row["state_code"]

                    }

                )

                if state_id:

                    conn.execute(text("""

                        INSERT INTO district (

                            name,
                            code,
                            state_id

                        )

                        VALUES (

                            :name,
                            :code,
                            :state_id

                        )

                        ON CONFLICT (state_id, code)
                        DO NOTHING

                    """), {

                        "name": row["district_name"],
                        "code": row["district_code"],
                        "state_id": state_id

                    })

            # =============================================
            # SUBDISTRICTS
            # =============================================

            subdistricts = df[[
                "subdistrict_code",
                "subdistrict_name",
                "district_code"
            ]].drop_duplicates()

            for _, row in subdistricts.iterrows():

                district_id = get_single_value(

                    conn,

                    """

                    SELECT id
                    FROM district
                    WHERE code=:code
                    LIMIT 1

                    """,

                    {

                        "code": row["district_code"]

                    }

                )

                if district_id:

                    conn.execute(text("""

                        INSERT INTO subdistrict (

                            name,
                            code,
                            district_id

                        )

                        VALUES (

                            :name,
                            :code,
                            :district_id

                        )

                        ON CONFLICT (district_id, code)
                        DO NOTHING

                    """), {

                        "name": row["subdistrict_name"],
                        "code": row["subdistrict_code"],
                        "district_id": district_id

                    })

            # =============================================
            # VILLAGES
            # =============================================

            villages = df[[
                "village_code",
                "village_name",
                "subdistrict_code"
            ]].drop_duplicates()

            inserted_rows = 0

            for _, row in villages.iterrows():

                subdistrict_id = get_single_value(

                    conn,

                    """

                    SELECT id
                    FROM subdistrict
                    WHERE code=:code
                    LIMIT 1

                    """,

                    {

                        "code": row["subdistrict_code"]

                    }

                )

                if subdistrict_id:

                    conn.execute(text("""

                        INSERT INTO village (

                            name,
                            code,
                            subdistrict_id

                        )

                        VALUES (

                            :name,
                            :code,
                            :subdistrict_id

                        )

                        ON CONFLICT (subdistrict_id, code)
                        DO NOTHING

                    """), {

                        "name": row["village_name"],
                        "code": row["village_code"],
                        "subdistrict_id": subdistrict_id

                    })

                    inserted_rows += 1

            # =============================================
            # RAW DATA TABLE
            # =============================================

            conn.execute(

                text("""

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

                """),

                df.to_dict(orient="records")

            )

        logging.info(
            "Database upload completed"
        )

        return jsonify({

            "success": True,

            "message":
            "Dataset uploaded successfully",

            "rows_inserted": inserted_rows,

            "total_rows": len(df)

        })

    except SQLAlchemyError as e:

        logging.error(traceback.format_exc())

        return jsonify({

            "success": False,
            "error": str(e)

        }), 500

    except Exception as e:

        logging.error(traceback.format_exc())

        return jsonify({

            "success": False,
            "error": str(e)

        }), 500


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    logging.info("Server Running")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )