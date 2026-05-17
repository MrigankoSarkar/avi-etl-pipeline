from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    send_file
)

import os
import logging
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
    raise Exception("DATABASE_URL missing")


# =========================================================
# APP CONFIG
# =========================================================

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "cleaned_output"

ALLOWED_EXTENSIONS = {"csv"}

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
# LOAD + CLEAN DATASET
# =========================================================

def load_and_clean_dataset(filepath):

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

    df = df.fillna("")

    # =====================================================
    # CLEAN STRINGS
    # =====================================================

    for col in required_columns:

        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
        )

    text_columns = [

        "state_name",
        "district_name",
        "subdistrict_name",
        "village_name"

    ]

    for col in text_columns:

        df[col] = df[col].apply(clean_text)

    # =====================================================
    # REMOVE EMPTY
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

    df = df.reset_index(drop=True)

    return df


# =========================================================
# CREATE TABLES
# =========================================================

def create_tables(conn):

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS country (

            id SERIAL PRIMARY KEY,
            name TEXT,
            code TEXT UNIQUE

        )

    """))

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS state (

            id SERIAL PRIMARY KEY,
            name TEXT,
            code TEXT,
            country_id INTEGER,

            UNIQUE(country_id, code)

        )

    """))

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS district (

            id SERIAL PRIMARY KEY,
            name TEXT,
            code TEXT,
            state_id INTEGER,

            UNIQUE(state_id, code)

        )

    """))

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS subdistrict (

            id SERIAL PRIMARY KEY,
            name TEXT,
            code TEXT,
            district_id INTEGER,

            UNIQUE(district_id, code)

        )

    """))

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS village (

            id SERIAL PRIMARY KEY,
            name TEXT,
            code TEXT,
            subdistrict_id INTEGER,

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
            village_name TEXT

        )

    """))


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return jsonify({

        "message": "Server Running"

    })


# =========================================================
# HEALTH
# =========================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "healthy"

    })


# =========================================================
# CLEAN DATASET ONLY
# =========================================================

@app.route("/clean-dataset", methods=["POST"])
def clean_dataset():

    try:

        file = request.files.get("file")

        if not file:

            return jsonify({
                "error": "No file uploaded"
            }), 400

        filename = secure_filename(file.filename)

        filepath = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        file.save(filepath)

        logging.info("Dataset cleaning initialized")

        df = load_and_clean_dataset(filepath)

        output_path = os.path.join(
            OUTPUT_FOLDER,
            f"cleaned_{filename}"
        )

        df.to_csv(
            output_path,
            index=False
        )

        logging.info("Dataset cleaning completed")

        return send_file(
            output_path,
            as_attachment=True
        )

    except Exception as e:

        logging.exception("Dataset cleaning failed")

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

        filename = secure_filename(file.filename)

        filepath = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        file.save(filepath)

        logging.info("Database upload initialized")

        # =================================================
        # CLEAN DATASET
        # =================================================

        df = load_and_clean_dataset(filepath)

        # =================================================
        # DB TRANSACTION
        # =================================================

        with engine.begin() as conn:

            create_tables(conn)

            # =============================================
            # RAW TABLE
            # =============================================

            raw_query = text("""

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

            conn.execute(
                raw_query,
                df.to_dict(orient="records")
            )

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

        logging.info("Database upload completed")

        return jsonify({

            "success": True,
            "message": "Dataset uploaded successfully",
            "total_rows": len(df)

        })

    except Exception as e:

        logging.exception("Database upload failed")

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
        debug=True
    )