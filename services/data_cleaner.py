import re
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
import pandas as pd


# Common string representations of missing values
NULL_STRINGS = {"nan", "null", "none", "n/a", "na", "?", "-", "--", "nil", "undefined"}


class DataCleaner:
    """
    Core Data Cleaning Engine using Pandas and NumPy.
    Provides deterministic, non-destructive data repairs based on user-approved operations.
    """

    def __init__(self, df: pd.DataFrame):
        self.original_df = df.copy(deep=True)

    def clean(self, operations_config: Dict[str, Any]) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Executes approved cleaning operations on a fresh copy of the dataset.
        Returns:
            (cleaned_df, audit_log)
        """
        cleaned_df = self.original_df.copy(deep=True)
        audit_log = []

        # 1. Standardize pseudo-null strings across object columns first
        # so subsequent missing value imputation handles them correctly
        if operations_config.get("standardize_nulls", True):
            cleaned_df, changes = self._standardize_pseudo_nulls(cleaned_df)
            if changes > 0:
                audit_log.append({
                    "operation": "standardize_nulls",
                    "title": "Standardized Null Placeholders",
                    "description": f"Standardized {changes} placeholder string(s) (e.g. 'N/A', 'null', '?') to actual missing values.",
                    "cells_affected": changes
                })

        # 2. Trim whitespace
        if operations_config.get("trim_whitespace", False):
            target_cols = operations_config.get("trim_columns") or list(cleaned_df.columns)
            cleaned_df, count = self._trim_whitespace(cleaned_df, target_cols)
            if count > 0:
                audit_log.append({
                    "operation": "trim_whitespace",
                    "title": "Whitespace Trimmed",
                    "description": f"Trimmed leading/trailing whitespace across {count} text cell(s).",
                    "cells_affected": count,
                    "columns": target_cols
                })

        # 3. Capitalization Normalization
        casing_config = operations_config.get("normalize_casing")
        if casing_config and casing_config.get("enabled"):
            strategy = casing_config.get("strategy", "title")  # title, lower, upper
            target_cols = casing_config.get("columns", [])
            cleaned_df, count = self._normalize_casing(cleaned_df, target_cols, strategy)
            if count > 0:
                audit_log.append({
                    "operation": "normalize_casing",
                    "title": f"Casing Normalized ({strategy.capitalize()})",
                    "description": f"Normalized capitalization for {count} text cell(s) in {len(target_cols)} column(s).",
                    "cells_affected": count,
                    "columns": target_cols
                })

        # 4. Numeric Column Conversion
        numeric_conversions = operations_config.get("convert_numeric", [])
        if numeric_conversions:
            for col_cfg in numeric_conversions:
                col = col_cfg.get("column")
                if col in cleaned_df.columns:
                    cleaned_df, count = self._convert_column_to_numeric(cleaned_df, col)
                    if count > 0:
                        audit_log.append({
                            "operation": "convert_numeric",
                            "title": f"Converted '{col}' to Numeric",
                            "description": f"Sanitized currency/symbols and converted {count} cell(s) to numeric.",
                            "cells_affected": count,
                            "columns": [col]
                        })

        # 5. Date Column Standardization
        date_conversions = operations_config.get("convert_dates", [])
        if date_conversions:
            for col_cfg in date_conversions:
                col = col_cfg.get("column")
                target_format = col_cfg.get("format", "YYYY-MM-DD")
                if col in cleaned_df.columns:
                    cleaned_df, count = self._standardize_dates(cleaned_df, col, target_format)
                    if count > 0:
                        audit_log.append({
                            "operation": "convert_dates",
                            "title": f"Standardized Dates in '{col}'",
                            "description": f"Standardized {count} date value(s) to {target_format} format.",
                            "cells_affected": count,
                            "columns": [col]
                        })

        # 6. Missing Value Handling
        missing_config = operations_config.get("handle_missing")
        if missing_config:
            cleaned_df, missing_logs = self._handle_missing_values(cleaned_df, missing_config)
            audit_log.extend(missing_logs)

        # 7. Remove Exact Duplicate Rows
        if operations_config.get("remove_duplicates", False):
            initial_len = len(cleaned_df)
            cleaned_df = cleaned_df.drop_duplicates(keep="first").reset_index(drop=True)
            dups_removed = initial_len - len(cleaned_df)
            if dups_removed > 0:
                audit_log.append({
                    "operation": "remove_duplicates",
                    "title": "Exact Duplicates Removed",
                    "description": f"Removed {dups_removed} duplicate row(s), keeping first occurrences.",
                    "rows_affected": dups_removed
                })

        # 8. Apply Custom Validation Rule Filters
        rule_filtering = operations_config.get("filter_invalid_rules")
        if rule_filtering and rule_filtering.get("enabled"):
            rules = rule_filtering.get("rules", [])
            cleaned_df, filtered_count = self._filter_rule_violations(cleaned_df, rules)
            if filtered_count > 0:
                audit_log.append({
                    "operation": "filter_invalid_rules",
                    "title": "Filtered Invalid Rule Records",
                    "description": f"Removed {filtered_count} row(s) failing custom validation rules.",
                    "rows_affected": filtered_count
                })

        return cleaned_df, audit_log

    def _standardize_pseudo_nulls(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        count = 0
        for col in df.columns:
            if df[col].dtype == object:
                def replace_null(val):
                    nonlocal count
                    if isinstance(val, str) and val.strip().lower() in NULL_STRINGS:
                        count += 1
                        return np.nan
                    return val
                df[col] = df[col].apply(replace_null)
        return df, count

    def _trim_whitespace(self, df: pd.DataFrame, columns: List[str]) -> Tuple[pd.DataFrame, int]:
        total_trimmed = 0
        for col in columns:
            if col not in df.columns:
                continue
            if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                def clean_space(val):
                    nonlocal total_trimmed
                    if isinstance(val, str):
                        cleaned = re.sub(r"\s+", " ", val).strip()
                        if cleaned != val:
                            total_trimmed += 1
                        return cleaned
                    return val
                df[col] = df[col].apply(clean_space)
        return df, total_trimmed

    def _normalize_casing(self, df: pd.DataFrame, columns: List[str], strategy: str) -> Tuple[pd.DataFrame, int]:
        total_normalized = 0
        for col in columns:
            if col not in df.columns:
                continue
            if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                def apply_casing(val):
                    nonlocal total_normalized
                    if isinstance(val, str) and val.strip():
                        old = val
                        if strategy == "title":
                            new = val.title()
                        elif strategy == "lower":
                            new = val.lower()
                        elif strategy == "upper":
                            new = val.upper()
                        else:
                            new = val
                        if new != old:
                            total_normalized += 1
                        return new
                    return val
                df[col] = df[col].apply(apply_casing)
        return df, total_normalized

    def _convert_column_to_numeric(self, df: pd.DataFrame, col: str) -> Tuple[pd.DataFrame, int]:
        converted_count = 0
        original_col = df[col].copy()

        def clean_numeric_str(val):
            nonlocal converted_count
            if pd.isna(val):
                return np.nan
            if isinstance(val, (int, float)):
                return val
            s = str(val).strip()
            # Remove currency signs, commas, percentages
            s_clean = re.sub(r"[\$,% ]", "", s)
            try:
                num = float(s_clean)
                converted_count += 1
                return num
            except ValueError:
                return np.nan

        df[col] = df[col].apply(clean_numeric_str)
        # If all valid numbers are integers, convert column to Int64 nullable integer
        non_null = df[col].dropna()
        if len(non_null) > 0 and (non_null % 1 == 0).all():
            try:
                df[col] = df[col].astype("Int64")
            except Exception:
                pass
        return df, converted_count

    def _standardize_dates(self, df: pd.DataFrame, col: str, target_format: str) -> Tuple[pd.DataFrame, int]:
        count = 0
        original_col = df[col].copy()

        def parse_and_format(val):
            nonlocal count
            if pd.isna(val) or val == "":
                return np.nan
            try:
                parsed = pd.to_datetime(val, errors="coerce", format="mixed")
                if pd.notna(parsed):
                    count += 1
                    return parsed.strftime("%Y-%m-%d")
                return np.nan
            except Exception:
                return np.nan

        df[col] = df[col].apply(parse_and_format)
        return df, count

    def _handle_missing_values(self, df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        logs = []
        global_strategy = config.get("global_strategy")
        column_strategies = config.get("column_strategies", {})

        # Check for dropping rows globally
        if global_strategy == "drop_rows":
            initial_count = len(df)
            df = df.dropna().reset_index(drop=True)
            dropped = initial_count - len(df)
            if dropped > 0:
                logs.append({
                    "operation": "drop_missing_rows",
                    "title": "Dropped Rows with Missing Values",
                    "description": f"Removed {dropped} row(s) containing any missing values.",
                    "rows_affected": dropped
                })
            return df, logs

        # Column-by-column handling
        for col, strat_info in column_strategies.items():
            if col not in df.columns:
                continue

            strategy = strat_info.get("strategy")
            missing_count = int(df[col].isna().sum())
            if missing_count == 0:
                continue

            if strategy == "drop_row":
                initial_count = len(df)
                df = df.dropna(subset=[col]).reset_index(drop=True)
                dropped = initial_count - len(df)
                logs.append({
                    "operation": f"drop_missing_{col}",
                    "title": f"Dropped Rows Missing '{col}'",
                    "description": f"Removed {dropped} row(s) missing values in '{col}'.",
                    "rows_affected": dropped
                })

            elif strategy == "mean":
                num_series = pd.to_numeric(df[col], errors="coerce")
                if num_series.notna().any():
                    mean_val = round(float(num_series.mean()), 2)
                    df[col] = df[col].fillna(mean_val)
                    logs.append({
                        "operation": f"fill_mean_{col}",
                        "title": f"Imputed Mean for '{col}'",
                        "description": f"Filled {missing_count} missing value(s) in '{col}' with calculated mean ({mean_val}).",
                        "cells_affected": missing_count
                    })

            elif strategy == "median":
                num_series = pd.to_numeric(df[col], errors="coerce")
                if num_series.notna().any():
                    median_val = round(float(num_series.median()), 2)
                    df[col] = df[col].fillna(median_val)
                    logs.append({
                        "operation": f"fill_median_{col}",
                        "title": f"Imputed Median for '{col}'",
                        "description": f"Filled {missing_count} missing value(s) in '{col}' with calculated median ({median_val}).",
                        "cells_affected": missing_count
                    })

            elif strategy == "mode":
                mode_vals = df[col].mode(dropna=True)
                if len(mode_vals) > 0:
                    mode_val = mode_vals.iloc[0]
                    df[col] = df[col].fillna(mode_val)
                    logs.append({
                        "operation": f"fill_mode_{col}",
                        "title": f"Imputed Mode for '{col}'",
                        "description": f"Filled {missing_count} missing value(s) in '{col}' with most frequent value ('{mode_val}').",
                        "cells_affected": missing_count
                    })

            elif strategy == "constant":
                fill_val = strat_info.get("fill_value", "Unknown")
                df[col] = df[col].fillna(fill_val)
                logs.append({
                    "operation": f"fill_constant_{col}",
                    "title": f"Filled Constant for '{col}'",
                    "description": f"Filled {missing_count} missing value(s) in '{col}' with '{fill_val}'.",
                    "cells_affected": missing_count
                })

        return df, logs

    def _filter_rule_violations(self, df: pd.DataFrame, rules: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, int]:
        initial_len = len(df)
        valid_mask = pd.Series(True, index=df.index)

        for rule in rules:
            col = rule.get("column")
            if col not in df.columns:
                continue

            rule_type = rule.get("rule_type", "range")
            series = df[col]

            if rule_type == "range":
                min_v = rule.get("min")
                max_v = rule.get("max")
                num_s = pd.to_numeric(series, errors="coerce")
                if min_v is not None:
                    valid_mask &= (num_s.isna()) | (num_s >= min_v)
                if max_v is not None:
                    valid_mask &= (num_s.isna()) | (num_s <= max_v)

            elif rule_type == "non_negative":
                num_s = pd.to_numeric(series, errors="coerce")
                valid_mask &= (num_s.isna()) | (num_s >= 0)

        df = df[valid_mask].reset_index(drop=True)
        filtered_count = initial_len - len(df)
        return df, filtered_count
