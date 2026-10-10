import io
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename
import pandas as pd

from config import Config
from services import (
    StorageManager,
    DataAnalyzer,
    QualityScoreEngine,
    DataCleaner,
    ReportGenerator,
)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize isolated storage manager
storage_manager = StorageManager(
    base_dir=Config.TEMP_STORAGE_DIR,
    expiry_minutes=Config.SESSION_EXPIRY_MINUTES
)


# Security headers middleware
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# Central exception handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "success": False,
        "error": f"File exceeds the maximum upload limit of {Config.MAX_CONTENT_LENGTH // (1024 * 1024)} MB."
    }), 413


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Requested API resource not found."}), 404
    return render_template("index.html"), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "success": False,
        "error": "An unexpected server error occurred while processing the request."
    }), 500


# --- Views & Health Check ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "DataWise AI Platform",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }), 200


# --- File Upload & Analysis APIs ---

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def load_dataframe_from_file(file_storage, filename: str) -> pd.DataFrame:
    ext = filename.rsplit(".", 1)[1].lower()
    if ext == "csv":
        try:
            # Try reading with utf-8 first, fallback to latin-1
            file_storage.seek(0)
            df = pd.read_csv(file_storage, encoding="utf-8", keep_default_na=False, na_values=[""])
        except UnicodeDecodeError:
            file_storage.seek(0)
            df = pd.read_csv(file_storage, encoding="latin-1", keep_default_na=False, na_values=[""])
    elif ext in ["xlsx", "xls"]:
        file_storage.seek(0)
        df = pd.read_excel(file_storage, engine="openpyxl", keep_default_na=False, na_values=[""])
    else:
        raise ValueError(f"Unsupported file extension: .{ext}")

    return df


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded in the request."}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    raw_filename = secure_filename(file.filename) or "dataset.csv"
    if not allowed_file(raw_filename):
        return jsonify({
            "success": False,
            "error": f"Invalid file format. Allowed formats: {', '.join(Config.ALLOWED_EXTENSIONS)}"
        }), 400

    try:
        df = load_dataframe_from_file(file, raw_filename)
    except pd.errors.EmptyDataError:
        return jsonify({"success": False, "error": "The uploaded file is empty."}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Unable to parse file: {str(e)}"}), 400

    if df.empty or len(df.columns) == 0:
        return jsonify({"success": False, "error": "The dataset contains no rows or columns."}), 400

    if len(df) > Config.MAX_PROCESSING_ROWS:
        return jsonify({
            "success": False,
            "error": f"Dataset exceeds the interactive limit of {Config.MAX_PROCESSING_ROWS:,} rows."
        }), 400

    # Ensure duplicate column names are renamed cleanly
    cols = []
    seen = {}
    for col in df.columns:
        clean_col = str(col).strip()
        if clean_col in seen:
            seen[clean_col] += 1
            cols.append(f"{clean_col}_{seen[clean_col]}")
        else:
            seen[clean_col] = 0
            cols.append(clean_col)
    df.columns = cols

    # Run complete analysis
    token = storage_manager.create_session(df, raw_filename)
    analyzer = DataAnalyzer(df)
    analysis = analyzer.analyze()
    score = QualityScoreEngine.calculate(analysis)

    storage_manager.save_analysis(token, analysis, is_cleaned=False)

    return jsonify({
        "success": True,
        "token": token,
        "filename": raw_filename,
        "analysis": analysis,
        "score": score
    }), 200


@app.route("/api/sample", methods=["POST", "GET"])
def load_sample_dataset():
    """Loads the pre-packaged sample dataset for instant hackathon evaluation."""
    sample_path = Config.SAMPLE_DATA_PATH
    if not sample_path.exists():
        return jsonify({"success": False, "error": "Sample dataset not found on server."}), 404

    try:
        df = pd.read_csv(sample_path, keep_default_na=False, na_values=[""])
        token = storage_manager.create_session(df, "sample_dataset.csv")

        analyzer = DataAnalyzer(df)
        analysis = analyzer.analyze()
        score = QualityScoreEngine.calculate(analysis)

        storage_manager.save_analysis(token, analysis, is_cleaned=False)

        return jsonify({
            "success": True,
            "token": token,
            "filename": "sample_dataset.csv",
            "analysis": analysis,
            "score": score
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Error loading sample dataset: {str(e)}"}), 500


@app.route("/api/state/<token>", methods=["GET"])
def get_session_state(token: str):
    """Retrieves current session analysis and cleaned status."""
    meta = storage_manager.get_meta(token)
    if not meta:
        return jsonify({"success": False, "error": "Session expired or not found."}), 404

    original_analysis = storage_manager.get_analysis(token, is_cleaned=False)
    cleaned_analysis = storage_manager.get_analysis(token, is_cleaned=True)
    report = storage_manager.get_report(token)

    init_score = QualityScoreEngine.calculate(original_analysis) if original_analysis else None
    cleaned_score = QualityScoreEngine.calculate(cleaned_analysis) if cleaned_analysis else None

    return jsonify({
        "success": True,
        "meta": meta,
        "original_analysis": original_analysis,
        "initial_score": init_score,
        "cleaned_analysis": cleaned_analysis,
        "cleaned_score": cleaned_score,
        "report": report
    }), 200


# --- Cleaning & Repair APIs ---

@app.route("/api/preview-clean", methods=["POST"])
def preview_cleaning():
    """Simulates cleaning operations on a sample and returns the predicted outcome."""
    payload = request.get_json() or {}
    token = payload.get("token")
    operations = payload.get("operations", {})

    if not token:
        return jsonify({"success": False, "error": "Token is required."}), 400

    df = storage_manager.get_original_df(token)
    if df is None:
        return jsonify({"success": False, "error": "Session expired or dataset not found."}), 404

    try:
        cleaner = DataCleaner(df)
        cleaned_df, audit_log = cleaner.clean(operations)

        # Run fast analysis on cleaned result
        analyzer = DataAnalyzer(cleaned_df)
        cleaned_analysis = analyzer.analyze()
        new_score = QualityScoreEngine.calculate(cleaned_analysis)

        # Retrieve initial score for comparison
        init_analysis = storage_manager.get_analysis(token, is_cleaned=False)
        init_score = QualityScoreEngine.calculate(init_analysis) if init_analysis else new_score

        return jsonify({
            "success": True,
            "preview_cleaned_rows": analyzer._get_safe_preview(limit=25),
            "new_score": new_score,
            "score_delta": round(new_score["overall_score"] - init_score["overall_score"], 1),
            "audit_log": audit_log,
            "projected_rows": len(cleaned_df),
            "projected_cols": len(cleaned_df.columns)
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Preview error: {str(e)}"}), 500


@app.route("/api/clean", methods=["POST"])
def apply_cleaning():
    """Applies approved cleaning operations and produces authoritative cleaned dataset & report."""
    payload = request.get_json() or {}
    token = payload.get("token")
    operations = payload.get("operations", {})

    if not token:
        return jsonify({"success": False, "error": "Token is required."}), 400

    original_df = storage_manager.get_original_df(token)
    if original_df is None:
        return jsonify({"success": False, "error": "Session expired or dataset not found."}), 404

    meta = storage_manager.get_meta(token) or {}
    filename = meta.get("filename", "dataset.csv")

    try:
        # Non-destructively clean a copy
        cleaner = DataCleaner(original_df)
        cleaned_df, audit_log = cleaner.clean(operations)

        # Reanalyze cleaned dataset
        cleaned_analyzer = DataAnalyzer(cleaned_df)
        cleaned_analysis = cleaned_analyzer.analyze()
        cleaned_score = QualityScoreEngine.calculate(cleaned_analysis)

        # Retrieve initial analysis & score
        initial_analysis = storage_manager.get_analysis(token, is_cleaned=False)
        if not initial_analysis:
            initial_analyzer = DataAnalyzer(original_df)
            initial_analysis = initial_analyzer.analyze()
        initial_score = QualityScoreEngine.calculate(initial_analysis)

        # Persist cleaned dataset and analysis
        storage_manager.save_cleaned_df(token, cleaned_df, audit_log)
        storage_manager.save_analysis(token, cleaned_analysis, is_cleaned=True)

        # Generate comprehensive audit report
        report = ReportGenerator.generate_full_report(
            filename=filename,
            initial_analysis=initial_analysis,
            initial_score=initial_score,
            cleaned_analysis=cleaned_analysis,
            cleaned_score=cleaned_score,
            audit_log=audit_log
        )
        storage_manager.save_report(token, report)

        return jsonify({
            "success": True,
            "token": token,
            "cleaned_analysis": cleaned_analysis,
            "cleaned_score": cleaned_score,
            "initial_score": initial_score,
            "score_delta": round(cleaned_score["overall_score"] - initial_score["overall_score"], 1),
            "audit_log": audit_log,
            "report": report,
            "cleaned_preview": cleaned_analyzer._get_safe_preview(limit=30)
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Cleaning error: {str(e)}"}), 500


@app.route("/api/reset", methods=["POST"])
def reset_to_original():
    """Resets the dataset to its pristine original state."""
    payload = request.get_json() or {}
    token = payload.get("token")
    if not token:
        return jsonify({"success": False, "error": "Token is required."}), 400

    success = storage_manager.reset_session(token)
    if not success:
        return jsonify({"success": False, "error": "Failed to reset session."}), 400

    orig_analysis = storage_manager.get_analysis(token, is_cleaned=False)
    score = QualityScoreEngine.calculate(orig_analysis) if orig_analysis else None

    return jsonify({
        "success": True,
        "message": "Reset to original dataset successfully.",
        "analysis": orig_analysis,
        "score": score
    }), 200


# --- Download & Export APIs ---

@app.route("/api/download/<token>/csv", methods=["GET"])
def download_csv(token: str):
    version = request.args.get("version", "cleaned")
    is_cleaned = (version == "cleaned")
    meta = storage_manager.get_meta(token)
    if not meta:
        return jsonify({"success": False, "error": "Invalid or expired token."}), 404

    base_name = Path(meta.get("filename", "dataset")).stem
    out_filename = f"{base_name}_cleaned.csv" if is_cleaned else f"{base_name}_original.csv"

    csv_bytes = storage_manager.export_csv(token, cleaned=is_cleaned)
    if csv_bytes is None:
        return jsonify({"success": False, "error": "Dataset content unavailable."}), 404

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name=out_filename
    )


@app.route("/api/download/<token>/excel", methods=["GET"])
def download_excel(token: str):
    version = request.args.get("version", "cleaned")
    is_cleaned = (version == "cleaned")
    meta = storage_manager.get_meta(token)
    if not meta:
        return jsonify({"success": False, "error": "Invalid or expired token."}), 404

    base_name = Path(meta.get("filename", "dataset")).stem
    out_filename = f"{base_name}_cleaned.xlsx" if is_cleaned else f"{base_name}_original.xlsx"

    excel_bytes = storage_manager.export_excel(token, cleaned=is_cleaned)
    if excel_bytes is None:
        return jsonify({"success": False, "error": "Dataset content unavailable."}), 404

    return send_file(
        io.BytesIO(excel_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=out_filename
    )


@app.route("/api/report/<token>/json", methods=["GET"])
def download_report_json(token: str):
    report = storage_manager.get_report(token)
    if not report:
        return jsonify({"success": False, "error": "Report not found or not yet generated."}), 404

    meta = storage_manager.get_meta(token) or {}
    base_name = Path(meta.get("filename", "dataset")).stem
    out_filename = f"{base_name}_quality_report.json"

    import json
    json_bytes = json.dumps(report, indent=2).encode("utf-8")

    return send_file(
        io.BytesIO(json_bytes),
        mimetype="application/json",
        as_attachment=True,
        download_name=out_filename
    )


@app.route("/api/report/<token>/csv", methods=["GET"])
def download_report_csv(token: str):
    report = storage_manager.get_report(token)
    if not report:
        return jsonify({"success": False, "error": "Report not found or not yet generated."}), 404

    meta = storage_manager.get_meta(token) or {}
    base_name = Path(meta.get("filename", "dataset")).stem
    out_filename = f"{base_name}_quality_summary.csv"

    csv_str = ReportGenerator.generate_summary_csv(report)

    return send_file(
        io.BytesIO(csv_str.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=out_filename
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
