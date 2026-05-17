from flask import (
    Flask,
    request,
    jsonify,
    render_template
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
    raise Exception("DATABASE_URL missing in .env")


# =========================================================
# APP CONFIG
# =========================================================

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {"csv"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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

    result = conn.execute(
        text(query),
        params or {}
    ).scalar()

    return result


# =========================================================
# CREATE TABLES
# =========================================================

def create_tables(conn):

    # =====================================================
    # COUNTRY
    # =====================================================

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS country (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            code TEXT UNIQUE NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

    """))

    # =====================================================
    # STATE
    # =====================================================

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS state (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            code TEXT NOT NULL,

            country_id INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(country_id, code),

            FOREIGN KEY (country_id)
            REFERENCES country(id)

        )

    """))

    # =====================================================
    # DISTRICT
    # =====================================================

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS district (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            code TEXT NOT NULL,

            state_id INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(state_id, code),

            FOREIGN KEY (state_id)
            REFERENCES state(id)

        )

    """))

    # =====================================================
    # SUBDISTRICT
    # =====================================================

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS subdistrict (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            code TEXT NOT NULL,

            district_id INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(district_id, code),

            FOREIGN KEY (district_id)
            REFERENCES district(id)

        )

    """))

    # =====================================================
    # VILLAGE
    # =====================================================

    conn.execute(text("""

        CREATE TABLE IF NOT EXISTS village (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            code TEXT NOT NULL,

            subdistrict_id INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(subdistrict_id, code),

            FOREIGN KEY (subdistrict_id)
            REFERENCES subdistrict(id)

        )

    """))

    # =====================================================
    # RAW TABLE
    # =====================================================

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

    return render_template("index.html")


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "healthy"

    })


# =========================================================
# UPLOAD TO DB
# =========================================================

@app.route("/upload-to-db", methods=["POST"])
def upload_to_db():

    try:

        # =================================================
        # FILE VALIDATION
        # =================================================

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
                "error": "Only CSV allowed"
            }), 400

        # =================================================
        # SAVE FILE
        # =================================================

        filename = secure_filename(file.filename)

        filepath = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        file.save(filepath)

        logging.info(f"Uploaded: {filename}")

        # =================================================
        # READ CSV
        # =================================================

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

        # =================================================
        # RENAME COLUMNS
        # =================================================

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

        # =================================================
        # VALIDATE COLUMNS
        # =================================================

        missing_columns = [

            col
            for col in required_columns
            if col not in df.columns

        ]

        if missing_columns:

            return jsonify({

                "error": f"Missing columns: {missing_columns}"

            }), 400

        # =================================================
        # CLEAN DATA
        # =================================================

        df = df[required_columns]

        df = df.fillna("")

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

        # =================================================
        # REMOVE EMPTY
        # =================================================

        df = df[
            df["village_code"] != ""
        ]

        # =================================================
        # REMOVE DUPLICATES
        # =================================================

        df = df.drop_duplicates(
            subset=["village_code"]
        )

        df = df.reset_index(drop=True)

        # =================================================
        # DATABASE TRANSACTION
        # =================================================

        with engine.begin() as conn:

            create_tables(conn)

            # =============================================
            # RAW TABLE INSERT
            # =============================================

            raw_insert = text("""

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
                raw_insert,
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
                WHERE code = 'IN'

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
                    WHERE code = :code
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
                    WHERE code = :code
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
                    WHERE code = :code
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

        # =================================================
        # SUCCESS
        # =================================================

        return jsonify({

            "success": True,
            "message": "Dataset uploaded successfully",

            "total_records": len(df)

        })

    except SQLAlchemyError as e:

        logging.exception("Database Error")

        return jsonify({

            "success": False,
            "error": str(e)

        }), 500

    except Exception as e:

        logging.exception("Unexpected Error")

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