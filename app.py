from flask import (
    Flask,
    render_template,
    request,
    send_file,
    jsonify
)

import pandas as pd

import os
import re
import logging

from werkzeug.utils import secure_filename


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
# FILE VALIDATION
# =========================================================

def allowed_file(filename):

    return (

        "." in filename

        and

        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    )


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(value):

    if pd.isna(value):

        return None

    return str(value).strip().title()


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
# FILE UPLOAD
# =========================================================

@app.route("/upload", methods=["POST"])
def upload_file():

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

                "error": "Unsupported file format"

            }), 400

        filename = secure_filename(file.filename)

        upload_path = os.path.join(

            UPLOAD_FOLDER,
            filename

        )

        file.save(upload_path)

        logging.info(f"Uploaded file: {filename}")

        # =====================================================
        # LOAD DATASET
        # =====================================================

        if filename.endswith(".csv"):

            df = pd.read_csv(upload_path)

        else:

            df = pd.read_excel(upload_path)

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
        # SCHEMA
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

            df[col] = df[col].apply(clean_text)

        # =====================================================
        # CLEAN CODES
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
                .astype(str)
                .str.strip()

            )

        # =====================================================
        # REMOVE NULLS
        # =====================================================

        df = df.dropna(

            subset=code_columns

        )

        # =====================================================
        # REMOVE DUPLICATES
        # =====================================================

        df = df.drop_duplicates(

            subset=["village_code"]

        )

        df = df.reset_index(drop=True)

        # =====================================================
        # OUTPUT FILE
        # =====================================================

        base_name = os.path.splitext(filename)[0]

        match = re.search(

            r'_[0-9]+_(.+)$',

            base_name

        )

        state_name = (

            match.group(1)

            if match

            else base_name

        )

        output_filename = f"cleaned_{state_name}.csv"

        output_path = os.path.join(

            OUTPUT_FOLDER,
            output_filename

        )

        # =====================================================
        # SAVE OUTPUT
        # =====================================================

        df.to_csv(

            output_path,
            index=False

        )

        logging.info(

            f"Cleaned dataset created: {output_filename}"

        )

        return send_file(

            output_path,

            as_attachment=True

        )

    except Exception as e:

        logging.exception("Upload failed")

        return jsonify({

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