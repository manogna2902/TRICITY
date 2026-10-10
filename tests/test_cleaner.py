import pytest
import pandas as pd
import numpy as np
from services.data_cleaner import DataCleaner


def test_remove_duplicate_rows():
    df = pd.DataFrame({
        "id": [1, 2, 2, 3],
        "name": ["Alice", "Bob", "Bob", "Charlie"]
    })
    orig_copy = df.copy(deep=True)

    cleaner = DataCleaner(df)
    cleaned_df, audit_log = cleaner.clean({"remove_duplicates": True})

    assert len(cleaned_df) == 3
    assert len(audit_log) == 1
    assert audit_log[0]["rows_affected"] == 1
    # Check original DataFrame is unchanged
    pd.testing.assert_frame_equal(df, orig_copy)


def test_trim_whitespace():
    df = pd.DataFrame({
        "name": ["  Alice  ", "Bob   ", "  Charlie Brown  "],
        "dept": ["Engineering  ", "  Sales  ", " HR "]
    })
    cleaner = DataCleaner(df)
    cleaned_df, audit_log = cleaner.clean({
        "trim_whitespace": True,
        "trim_columns": ["name", "dept"]
    })

    assert cleaned_df["name"].tolist() == ["Alice", "Bob", "Charlie Brown"]
    assert cleaned_df["dept"].tolist() == ["Engineering", "Sales", "HR"]


def test_normalize_casing():
    df = pd.DataFrame({
        "city": ["new york", "NEW YORK", "New york"]
    })
    cleaner = DataCleaner(df)
    cleaned_df, _ = cleaner.clean({
        "normalize_casing": {
            "enabled": True,
            "strategy": "title",
            "columns": ["city"]
        }
    })

    assert (cleaned_df["city"] == "New York").all()


def test_numeric_conversion():
    df = pd.DataFrame({
        "salary": ["$50,000", "60000", "$75,500.50", "invalid_str"]
    })
    cleaner = DataCleaner(df)
    cleaned_df, audit_log = cleaner.clean({
        "convert_numeric": [{"column": "salary"}]
    })

    assert cleaned_df["salary"].iloc[0] == 50000.0
    assert cleaned_df["salary"].iloc[1] == 60000.0
    assert cleaned_df["salary"].iloc[2] == 75500.50
    assert pd.isna(cleaned_df["salary"].iloc[3])


def test_date_standardization():
    df = pd.DataFrame({
        "date_str": ["2023/01/15", "15-02-2023", "2023-03-20", "invalid"]
    })
    cleaner = DataCleaner(df)
    cleaned_df, audit_log = cleaner.clean({
        "convert_dates": [{"column": "date_str", "format": "YYYY-MM-DD"}]
    })

    assert cleaned_df["date_str"].iloc[0] == "2023-01-15"
    assert cleaned_df["date_str"].iloc[2] == "2023-03-20"
    assert pd.isna(cleaned_df["date_str"].iloc[3])


def test_missing_values_imputation_mean_and_mode():
    df = pd.DataFrame({
        "score": [10.0, 20.0, 30.0, np.nan],
        "category": ["A", "B", "A", np.nan]
    })
    cleaner = DataCleaner(df)
    cleaned_df, audit_log = cleaner.clean({
        "handle_missing": {
            "column_strategies": {
                "score": {"strategy": "mean"},
                "category": {"strategy": "mode"}
            }
        }
    })

    # Mean of 10, 20, 30 is 20.0
    assert cleaned_df["score"].iloc[3] == 20.0
    # Mode of A, B, A is A
    assert cleaned_df["category"].iloc[3] == "A"
    assert cleaned_df["score"].isna().sum() == 0
    assert cleaned_df["category"].isna().sum() == 0


def test_drop_missing_rows():
    df = pd.DataFrame({
        "a": [1, 2, np.nan, 4],
        "b": ["x", "y", "z", np.nan]
    })
    cleaner = DataCleaner(df)
    cleaned_df, audit_log = cleaner.clean({
        "handle_missing": {"global_strategy": "drop_rows"}
    })

    assert len(cleaned_df) == 2
    assert cleaned_df["a"].tolist() == [1.0, 2.0]


def test_filter_rule_violations():
    df = pd.DataFrame({
        "age": [25, 30, -5, 140, 45]
    })
    cleaner = DataCleaner(df)
    cleaned_df, audit_log = cleaner.clean({
        "filter_invalid_rules": {
            "enabled": True,
            "rules": [{"column": "age", "rule_type": "range", "min": 0, "max": 120}]
        }
    })

    assert len(cleaned_df) == 3
    assert -5 not in cleaned_df["age"].values
    assert 140 not in cleaned_df["age"].values
