# DataWise AI — Smart Data Quality and Repair Platform

> **Turn messy data into trusted data.**  
> A college hackathon project for deterministic, AI-grade data quality analysis, outlier detection, and non-destructive automated repair.

---

## 1. Project Overview & Hackathon Summary

In data science, machine learning, and enterprise analytics, dirty datasets lead to misleading conclusions, broken pipelines, and biased models. Organizations routinely discard or manually fix hundreds of hours of data because existing data-cleaning tools are either opaque black-boxes, overly simplistic scripts, or require paid cloud AI APIs.

**DataWise AI** provides a transparent, deterministic data-quality profiling and repair studio built with Flask, Pandas, and Vanilla JS. It enables anyone—from college students and hackathon judges to data engineers—to:
1. Upload real CSV or Excel datasets (up to 10 MB).
2. Instantly receive a standardized Data Quality Score (0–100) across 4 foundational pillars.
3. Inspect detected flaws (duplicates, missing fields, whitespace traps, casing variations, broken datatypes, and statistical outliers) with exact row indices.
4. Preview non-destructive repair transformations.
5. Apply approved fixes and export verified cleaned CSV/Excel files alongside full audit reports.

**Core Philosophy:** *Never silently invent missing values or corrupt raw data. Provide complete user agency, auditability, and mathematical explainability.*

---

## 2. Key Features

### 🔍 Deterministic Data Quality Analysis
- **Missing Value Detection:** Pinpoints nulls, whitespace-only cells, and pseudo-missing placeholders (`N/A`, `null`, `none`, `?`, `-`), calculating per-column null rates and sample affected rows.
- **Exact Duplicate Detection:** Identifies exact duplicate rows across all features, preserving first occurrences and calculating record redundancy.
- **Text & Whitespace Standardization:** Detects leading, trailing, and redundant internal whitespace traps. Identifies mixed-casing clusters in categorical columns (e.g., `["Sales", "sales", "SALES"]`).
- **Numeric Validation:** Identifies candidate numeric columns disguised as text, unearthing invalid characters, unparseable strings, currency symbols, and commas.
- **Date Format Auditing:** Discovers candidate date columns with mixed or unparseable date formats (e.g., ISO, slash, hyphenated, written formats).
- **Statistical Outlier Detection:** Employs the non-parametric **1.5x Interquartile Range (IQR)** method ($Q1 - 1.5 \times IQR$ to $Q3 + 1.5 \times IQR$) to flag statistical anomalies without arbitrarily deleting them.
- **Custom Validation Rule Engine:** Enables users to specify domain-specific constraints (e.g., age between 0 and 120, non-negative salaries, or regex patterns like email formats).
- **Column Profiling:** Provides complete metadata per column: inferred data types, non-null counts, distinct counts, and descriptive statistics ($\min$, $\max$, $\text{mean}$, $\text{median}$, $\text{std}$).

### 🛠️ Interactive Non-Destructive Repair Studio
- **Preview Before Commit:** Simulates selected repairs and projects the anticipated score uplift before writing changes.
- **Selective Remediations:** Checkbox-based control for:
  - Exact duplicate removal
  - Whitespace trimming
  - Capitalization normalization (Title Case, lowercase, UPPERCASE)
  - Date format conversion to ISO 8601 (`YYYY-MM-DD`)
  - Numeric sanitization (currency symbol and comma stripping)
  - Missing value imputation: Mean (numeric), Median (numeric), Mode (text), Constant (`'Unknown'`), or row dropping
  - Filtering records violating custom constraints
- **Immutable Originals:** The raw dataset is strictly preserved; repairs are performed on isolated copies.
- **Reset Capability:** One-click rollback to the raw dataset at any time.

### 📊 Quality Score (0 to 100)
A documented, mathematically sound scoring formula that combines 4 weighted pillars:

$$\text{Overall Score} = (\text{Score}_{\text{missing}} \times 0.35) + (\text{Score}_{\text{duplicates}} \times 0.25) + (\text{Score}_{\text{invalid}} \times 0.25) + (\text{Score}_{\text{formatting}} \times 0.15)$$

- **Letter Grades:** A (90–100, Excellent), B (80–89, Good), C (65–79, Fair), D (50–64, Needs Attention), F (<50, Critical Issues).

### 📥 Enterprise-Grade Exports & Audit Reports
- **Cleaned Dataset:** Exportable as **CSV** or **Microsoft Excel (.xlsx)**.
- **Audit Report (JSON):** Machine-readable audit file with executive summaries, timestamps, column profiles, and operation logs.
- **Audit Summary (CSV):** Tabular column health breakdown comparing before-and-after states.

---

## 3. Technology Stack

- **Backend:** Python 3.11+ / Flask 3.1+
- **Data Engineering:** Pandas 3.0+, NumPy 2.4+, OpenPyXL 3.1+
- **Frontend:** HTML5, CSS3 (Modern SaaS Design System), Vanilla JavaScript (ES6+)
- **Visualization:** Chart.js 4.4+ (Radar & Categorical Bar charts)
- **Production Server:** Gunicorn 21+ (Linux/Render) / Waitress or Flask WSGI (Windows)
- **Testing:** Pytest 9+ with Flask Test Client

---

## 4. Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │              Browser UI                │
                      │  Vanilla JS + CSS3 + Chart.js (SaaS)   │
                      └──────────────────┬─────────────────────┘
                                         │ RESTful JSON / Multipart
                                         ▼
                      ┌────────────────────────────────────────┐
                      │             Flask Backend              │
                      │         (app.py / config.py)           │
                      └──────┬───────────┬───────────┬─────────┘
                             │           │           │
           ┌─────────────────▼┐   ┌──────▼──────┐   ┌▼─────────────────┐
           │   DataAnalyzer   │   │ DataCleaner │   │QualityScoreEngine│
           │ (Pandas / NumPy) │   │ (Deep Copy) │   │ (0-100 Weighted) │
           └──────────────────┘   └─────────────┘   └──────────────────┘
                             │           │                   │
                             └───────────┼───────────────────┘
                                         ▼
                      ┌────────────────────────────────────────┐
                      │             StorageManager             │
                      │ Isolated UUID sessions in temp_storage │
                      │  Automatic cleanup of expired sessions │
                      └──────────────────┬─────────────────────┘
                                         ▼
                      ┌────────────────────────────────────────┐
                      │             ReportGenerator            │
                      │  Cleaned CSV / XLSX / JSON Reports     │
                      └────────────────────────────────────────┘
```

---

## 5. Project Folder Structure

```
TRICITY/
├── app.py                      # Flask application and REST routes
├── config.py                   # Centralized configuration and weights
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render cloud deployment blueprint
├── .gitignore                  # Git ignore rules
├── README.md                   # Complete documentation
├── sample_data/
│   └── sample_dataset.csv      # Pre-packaged synthetic demo dataset
├── services/
│   ├── __init__.py             # Package exports
│   ├── data_analyzer.py        # Core quality profiling & issue engine
│   ├── data_cleaner.py         # Non-destructive repair transformations
│   ├── quality_score.py        # 0-100 mathematical quality score
│   ├── report_generator.py     # JSON and CSV audit report generator
│   └── storage_manager.py      # Session token isolation & export manager
├── static/
│   ├── css/
│   │   └── styles.css          # Modern SaaS CSS design system
│   └── js/
│       └── app.js              # Client state, dynamic DOM, and Chart.js
├── templates/
│   └── index.html              # Single-page dashboard interface
└── tests/
    ├── __init__.py             # Test suite package
    ├── test_analyzer.py        # Tests for analyzer engine
    ├── test_cleaner.py         # Tests for repair transformations
    ├── test_quality_score.py   # Tests for scoring algorithm
    └── test_routes.py          # Integration tests for Flask endpoints
```

---

## 6. Local Installation & Setup

### Prerequisites
- Python 3.11 or higher
- `git` and `pip`

### Step 1: Clone or Navigate to Project
```bash
git clone https://github.com/your-username/datawise-ai.git
cd datawise-ai
```

### Step 2: Create a Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 7. Running the Application

### Local Development Mode
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### Production Mode (Linux / Mac)
```bash
gunicorn app:app
```

---

## 8. Running the Automated Test Suite

We maintain 100% test pass rates across all analysis, repair, scoring, and route integration tests:

```bash
pytest -v
```

Expected output:
```
============================= test session starts =============================
tests/test_analyzer.py::test_missing_values_detection PASSED             [  3%]
tests/test_analyzer.py::test_duplicate_rows_detection PASSED             [  6%]
tests/test_analyzer.py::test_text_formatting_and_casing PASSED           [ 10%]
tests/test_analyzer.py::test_numeric_validation PASSED                   [ 13%]
tests/test_analyzer.py::test_date_validation PASSED                      [ 17%]
tests/test_analyzer.py::test_outlier_detection_iqr PASSED                [ 20%]
tests/test_analyzer.py::test_custom_validation_rules PASSED              [ 24%]
tests/test_analyzer.py::test_column_profiling PASSED                     [ 27%]
tests/test_cleaner.py::test_remove_duplicate_rows PASSED                 [ 31%]
tests/test_cleaner.py::test_trim_whitespace PASSED                       [ 34%]
tests/test_cleaner.py::test_normalize_casing PASSED                      [ 37%]
tests/test_cleaner.py::test_numeric_conversion PASSED                    [ 41%]
tests/test_cleaner.py::test_date_standardization PASSED                  [ 44%]
tests/test_cleaner.py::test_missing_values_imputation_mean_and_mode PASSED [ 48%]
tests/test_cleaner.py::test_drop_missing_rows PASSED                     [ 51%]
tests/test_cleaner.py::test_filter_rule_violations PASSED                [ 55%]
tests/test_quality_score.py::test_perfect_dataset_score PASSED           [ 58%]
tests/test_quality_score.py::test_dirty_dataset_penalties PASSED         [ 62%]
tests/test_quality_score.py::test_empty_dataset_score PASSED             [ 65%]
tests/test_quality_score.py::test_weights_sum_to_one PASSED              [ 68%]
tests/test_routes.py::test_health_endpoint PASSED                        [ 72%]
tests/test_routes.py::test_index_page PASSED                             [ 75%]
tests/test_routes.py::test_upload_valid_csv PASSED                       [ 79%]
tests/test_routes.py::test_upload_valid_excel PASSED                     [ 82%]
tests/test_routes.py::test_upload_invalid_file_extension PASSED          [ 86%]
tests/test_routes.py::test_upload_empty_file PASSED                      [ 89%]
tests/test_routes.py::test_sample_dataset_route PASSED                   [ 93%]
tests/test_routes.py::test_complete_cleaning_workflow_and_downloads PASSED [ 96%]
tests/test_routes.py::test_path_traversal_protection PASSED              [100%]
============================= 29 passed in 1.59s ==============================
```

---

## 9. API Endpoint Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the single-page application dashboard. |
| `GET` | `/health` | Health check endpoint returning JSON status & version. |
| `POST` | `/api/upload` | Multipart upload of CSV or XLSX dataset. Returns UUID token and full quality profile. |
| `POST` | `/api/sample` | Loads built-in synthetic dataset for instant evaluation. |
| `GET` | `/api/state/<token>` | Restores session state upon page refresh. |
| `POST` | `/api/preview-clean` | Computes simulated impact of selected cleaning operations without mutating stored data. |
| `POST` | `/api/clean` | Applies approved cleaning transformations, re-analyzes dataset, and generates audit report. |
| `POST` | `/api/reset` | Reverts the session dataset back to its raw original state. |
| `GET` | `/api/download/<token>/csv` | Downloads cleaned or original dataset as standard CSV. |
| `GET` | `/api/download/<token>/excel` | Downloads cleaned or original dataset as Microsoft Excel (`.xlsx`). |
| `GET` | `/api/report/<token>/json` | Downloads machine-readable JSON quality and audit report. |
| `GET` | `/api/report/<token>/csv` | Downloads tabular column summary audit report as CSV. |

---

## 10. Built-in Sample Dataset Guide

For hackathon judges and demo evaluations, click **"Try Sample Dataset"** on the dashboard. The included synthetic dataset (`sample_data/sample_dataset.csv`) features deliberate real-world issues:
1. **Duplicate Records:** Rows 1 and 2 repeat verbatim.
2. **Missing Fields:** Null values across age, email, and salary.
3. **Whitespace Traps:** `"  Alice Johnson  "`, `" MARKETING "`.
4. **Casing Inconsistencies:** Department categorized as `"marketing"`, `"Marketing"`, `"MARKETING"`, `"sales"`, `"Sales"`, `"SALES"`.
5. **Invalid Numbers:** Salary entries formatted as `"$92000"`, `"unknown"`, and negative ages (`-5`).
6. **Mixed Dates:** Datetime formats mixing `YYYY-MM-DD`, `YYYY/MM/DD`, `DD/MM/YYYY`, `MM-DD-YYYY`, and unparseable strings.
7. **Outlier Records:** Age `145` and salary `$950,000` (flagged via 1.5x IQR).

---

## 11. Production Deployment on Render

This project is pre-configured for one-click deployment on **Render**:

### Method A: Connect GitHub Repository to Render
1. Push this repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of DataWise AI platform"
   git remote add origin https://github.com/<your-username>/datawise-ai.git
   git branch -M main
   git push -u origin main
   ```
2. Log in to [Render.com](https://render.com).
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository.
5. Configure the service settings:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Plan:** Free or Starter
6. Add Environment Variables (optional):
   - `FLASK_ENV=production`
   - `SECRET_KEY=<random-hex-key>`
7. Click **Create Web Service**.

### Method B: Blueprint Deployment (`render.yaml`)
Render will automatically detect `render.yaml` located at the root of the repository, setting up the runtime and start command with zero manual configuration.

---

## 12. Security, Privacy & Reliability Considerations

- **No Permanent Retention:** Uploaded files and artifacts reside in isolated UUID directories that expire and are cleaned automatically.
- **Path Traversal Protection:** Session tokens are strictly checked against a canonical UUID regex pattern before any disk lookup.
- **No Paid AI Dependencies:** Analysis and repair logic use deterministic Python, Pandas, and NumPy algorithms, guaranteeing zero token costs, no downtime, and no probabilistic hallucinations.
- **Multi-Worker Compatibility:** Session files are stored in directory structures accessible to all Gunicorn worker processes.

---

## 13. Future Roadmap

- **Fuzzy Deduplication:** Integrating Levenshtein distance (e.g., rapidfuzz) for approximate string matching.
- **Schema Drift Detection:** Alerting when uploaded datasets violate pre-defined enterprise schemas.
- **Automated Pipeline Webhooks:** Integrating with Airflow, dbt, and Kafka for continuous streaming data quality validation.

---

## 14. License & Credits

Developed with ❤️ for the College Hackathon.  
Open-source under the MIT License.
