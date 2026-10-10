import io
import json
import pytest
import pandas as pd
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"DataWise" in res.data


def test_upload_valid_csv(client):
    csv_content = "id,name,score\n1,Alice,95\n2,Bob,88\n3,Charlie,\n2,Bob,88\n"
    data = {
        "file": (io.BytesIO(csv_content.encode("utf-8")), "students.csv")
    }
    res = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert "token" in json_data
    assert json_data["analysis"]["summary"]["total_rows"] == 4
    assert json_data["score"]["overall_score"] > 0


def test_upload_valid_excel(client):
    df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["A", "B", "C"]})
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    excel_buf.seek(0)

    data = {
        "file": (excel_buf, "test_excel.xlsx")
    }
    res = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["analysis"]["summary"]["total_rows"] == 3


def test_upload_invalid_file_extension(client):
    data = {
        "file": (io.BytesIO(b"malicious script"), "script.exe")
    }
    res = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["success"] is False
    assert "Invalid file format" in json_data["error"]


def test_upload_empty_file(client):
    data = {
        "file": (io.BytesIO(b""), "empty.csv")
    }
    res = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["success"] is False


def test_sample_dataset_route(client):
    res = client.post("/api/sample")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["filename"] == "sample_dataset.csv"
    assert data["analysis"]["summary"]["total_rows"] > 20
    assert data["score"]["overall_score"] < 100.0  # Dirty data


def test_complete_cleaning_workflow_and_downloads(client):
    # 1. Load sample dataset
    sample_res = client.post("/api/sample")
    token = sample_res.get_json()["token"]
    init_score = sample_res.get_json()["score"]["overall_score"]

    # 2. Preview cleaning
    ops = {
        "remove_duplicates": True,
        "trim_whitespace": True,
        "normalize_casing": {"enabled": True, "strategy": "title", "columns": ["full_name", "department"]},
        "handle_missing": {
            "global_strategy": "none",
            "column_strategies": {"age": {"strategy": "mean"}, "email": {"strategy": "constant", "fill_value": "missing@domain.com"}}
        },
        "convert_numeric": [{"column": "salary"}],
        "convert_dates": [{"column": "join_date", "format": "YYYY-MM-DD"}]
    }

    prev_res = client.post("/api/preview-clean", json={"token": token, "operations": ops})
    assert prev_res.status_code == 200
    prev_data = prev_res.get_json()
    assert prev_data["success"] is True
    assert prev_data["new_score"]["overall_score"] > init_score

    # 3. Apply cleaning
    clean_res = client.post("/api/clean", json={"token": token, "operations": ops})
    assert clean_res.status_code == 200
    clean_data = clean_res.get_json()
    assert clean_data["success"] is True
    assert clean_data["cleaned_score"]["overall_score"] > init_score
    assert len(clean_data["audit_log"]) > 0

    # 4. Download Cleaned CSV
    dl_csv = client.get(f"/api/download/{token}/csv?version=cleaned")
    assert dl_csv.status_code == 200
    assert "text/csv" in dl_csv.content_type
    assert len(dl_csv.data) > 0

    # 5. Download Cleaned Excel
    dl_excel = client.get(f"/api/download/{token}/excel?version=cleaned")
    assert dl_excel.status_code == 200
    assert "openxmlformats" in dl_excel.content_type
    assert len(dl_excel.data) > 0

    # 6. Download Quality Report JSON
    rep_json = client.get(f"/api/report/{token}/json")
    assert rep_json.status_code == 200
    assert "application/json" in rep_json.content_type
    rep_data = json.loads(rep_json.data)
    assert "executive_summary" in rep_data

    # 7. Download Quality Report CSV
    rep_csv = client.get(f"/api/report/{token}/csv")
    assert rep_csv.status_code == 200
    assert "text/csv" in rep_csv.content_type
    assert b"DataWise AI Quality & Audit Report" in rep_csv.data

    # 8. Reset to original
    reset_res = client.post("/api/reset", json={"token": token})
    assert reset_res.status_code == 200
    assert reset_res.get_json()["success"] is True


def test_path_traversal_protection(client):
    malicious_token = "../../../../etc/passwd"
    res = client.get(f"/api/download/{malicious_token}/csv")
    # Must fail safely with 404
    assert res.status_code in [400, 404]
