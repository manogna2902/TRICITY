import pytest
import pandas as pd
import numpy as np
from services.data_analyzer import DataAnalyzer


def test_missing_values_detection():
    data = {
        "col_a": [1, 2, None, 4, 5],
        "col_b": ["apple", "  ", "banana", "n/a", "cherry"],
        "col_c": [None, None, None, None, None]  # 100% empty
    }
    df = pd.DataFrame(data)
    analyzer = DataAnalyzer(df)
    results = analyzer.analyze()

    missing_info = results["missing_analysis"]
    assert missing_info["total_missing"] >= 5
    assert "col_c" in missing_info["empty_columns"]
    assert missing_info["by_column"]["col_a"]["missing_count"] == 1
    assert missing_info["by_column"]["col_b"]["missing_count"] == 2  # empty spaces and "n/a"
    assert missing_info["by_column"]["col_c"]["missing_count"] == 5


def test_duplicate_rows_detection():
    data = {
        "id": [1, 2, 2, 3, 3, 3],
        "name": ["Alice", "Bob", "Bob", "Charlie", "Charlie", "Charlie"]
    }
    df = pd.DataFrame(data)
    analyzer = DataAnalyzer(df)
    results = analyzer.analyze()

    dup_info = results["duplicate_analysis"]
    # 6 rows total: unique are 1, 2, 3. duplicates are 3 rows (one Bob, two Charlies)
    assert dup_info["duplicate_count"] == 3
    assert dup_info["duplicate_pct"] == 50.0
    assert len(dup_info["duplicate_rows_sample"]) > 0


def test_text_formatting_and_casing():
    data = {
        "city": ["New York ", " new york", "NEW YORK", "Chicago", "Boston  "]
    }
    df = pd.DataFrame(data)
    analyzer = DataAnalyzer(df)
    results = analyzer.analyze()

    text_info = results["text_analysis"]
    # Whitespace issues
    assert "city" in text_info["whitespace_issues"]
    assert text_info["whitespace_issues"]["city"]["count"] >= 3

    # Casing inconsistencies
    assert "city" in text_info["casing_inconsistencies"]
    groups = text_info["casing_inconsistencies"]["city"]["groups"]
    assert "new york" in groups
    assert len(groups["new york"]) >= 2


def test_numeric_validation():
    data = {
        "salary": ["50000", "$60000", "70,000", "unknown_val", "85000"]
    }
    df = pd.DataFrame(data)
    analyzer = DataAnalyzer(df)
    results = analyzer.analyze()

    num_info = results["numeric_analysis"]
    assert "salary" in num_info["invalid_entries"]
    assert num_info["invalid_entries"]["salary"]["count"] == 1
    assert "unknown_val" in num_info["invalid_entries"]["salary"]["sample_values"]


def test_date_validation():
    data = {
        "join_date": ["2023-01-15", "2023/02/20", "not_a_valid_date", "2023-04-10"]
    }
    df = pd.DataFrame(data)
    analyzer = DataAnalyzer(df)
    results = analyzer.analyze()

    date_info = results["date_analysis"]
    assert "join_date" in date_info["invalid_dates"]
    assert date_info["invalid_dates"]["join_date"]["count"] == 1
    assert "not_a_valid_date" in date_info["invalid_dates"]["join_date"]["sample_values"]


def test_outlier_detection_iqr():
    # 20 normal numbers between 20 and 30, plus an extreme outlier 900
    values = [20, 21, 22, 23, 24, 25, 22, 23, 24, 25, 26, 27, 28, 22, 23, 24, 25, 26, 27, 900]
    df = pd.DataFrame({"score": values})
    analyzer = DataAnalyzer(df)
    results = analyzer.analyze()

    outlier_info = results["outlier_analysis"]
    assert "score" in outlier_info["outliers_by_column"]
    assert outlier_info["outliers_by_column"]["score"]["count"] == 1
    assert 900 in outlier_info["outliers_by_column"]["score"]["sample_values"]


def test_custom_validation_rules():
    df = pd.DataFrame({
        "age": [25, 30, -5, 140, 45],
        "email": ["valid@test.com", "not_an_email", "good@domain.org", "bad_email", "user@site.io"]
    })
    rules = [
        {"column": "age", "rule_type": "range", "min": 0, "max": 120},
        {"column": "email", "rule_type": "regex", "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"}
    ]
    analyzer = DataAnalyzer(df, custom_rules=rules)
    results = analyzer.analyze()

    rule_info = results["rule_analysis"]
    assert rule_info["total_violations"] == 4  # -5, 140, not_an_email, bad_email
    assert len(rule_info["violations"]) == 2


def test_column_profiling():
    df = pd.DataFrame({
        "age": [20, 25, 30, 35, 40],
        "category": ["A", "B", "A", "B", "C"]
    })
    analyzer = DataAnalyzer(df)
    results = analyzer.analyze()

    profiles = results["column_profiles"]
    assert len(profiles) == 2
    age_profile = next(p for p in profiles if p["name"] == "age")
    assert age_profile["stats"]["min"] == 20
    assert age_profile["stats"]["max"] == 40
    assert age_profile["stats"]["mean"] == 30.0
    assert age_profile["distinct_count"] == 5
