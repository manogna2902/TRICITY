import re
import math
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd


# Common string representations of missing values
NULL_STRING_VARIANTS = {"nan", "null", "none", "n/a", "na", "?", "-", "--", "nil", "undefined"}


class DataAnalyzer:
    """
    Core Data Quality Analysis Engine using Pandas and NumPy.
    Performs deterministic quality assessments:
    - Missing value detection
    - Exact duplicate detection
    - Text formatting & whitespace analysis
    - Inconsistent capitalization detection
    - Numeric parsing and range validation
    - Date format and parseability checks
    - Statistical IQR outlier detection
    - Custom user-defined validation rules
    - Column-by-column profiling
    """

    def __init__(self, df: pd.DataFrame, custom_rules: Optional[List[Dict[str, Any]]] = None):
        self.df = df.copy()
        self.custom_rules = custom_rules or []
        self.total_rows = len(self.df)
        self.total_cols = len(self.df.columns)
        self.total_cells = self.total_rows * self.total_cols if self.total_cols > 0 else 0

    def analyze(self) -> Dict[str, Any]:
        """Runs the complete suite of data quality checks and returns structured results."""
        if self.total_rows == 0 or self.total_cols == 0:
            return self._empty_analysis_result()

        missing_info = self._analyze_missing_values()
        duplicate_info = self._analyze_duplicates()
        text_info = self._analyze_text_formatting()
        numeric_info = self._analyze_numeric_values()
        date_info = self._analyze_date_values()
        outlier_info = self._analyze_outliers()
        rule_info = self._analyze_custom_rules()
        column_profiles = self._generate_column_profiles()

        # Build list of unified issues
        issues = self._compile_issues(
            missing_info, duplicate_info, text_info, numeric_info, date_info, outlier_info, rule_info
        )

        return {
            "summary": {
                "total_rows": self.total_rows,
                "total_cols": self.total_cols,
                "total_cells": self.total_cells,
                "total_issues_count": len(issues),
                "total_problematic_cells": self._calculate_problematic_cells(
                    missing_info, duplicate_info, text_info, numeric_info, date_info
                ),
                "columns": list(self.df.columns)
            },
            "issues": issues,
            "missing_analysis": missing_info,
            "duplicate_analysis": duplicate_info,
            "text_analysis": text_info,
            "numeric_analysis": numeric_info,
            "date_analysis": date_info,
            "outlier_analysis": outlier_info,
            "rule_analysis": rule_info,
            "column_profiles": column_profiles,
            "preview_rows": self._get_safe_preview(limit=30)
        }

    def _empty_analysis_result(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_rows": self.total_rows,
                "total_cols": self.total_cols,
                "total_cells": 0,
                "total_issues_count": 0,
                "total_problematic_cells": 0,
                "columns": list(self.df.columns)
            },
            "issues": [],
            "missing_analysis": {"total_missing": 0, "by_column": {}},
            "duplicate_analysis": {"duplicate_count": 0, "duplicate_rows": []},
            "text_analysis": {"whitespace_issues": {}, "casing_inconsistencies": {}},
            "numeric_analysis": {"invalid_entries": {}},
            "date_analysis": {"invalid_dates": {}},
            "outlier_analysis": {"outliers_by_column": {}},
            "rule_analysis": {"violations": []},
            "column_profiles": [],
            "preview_rows": []
        }

    def _is_missing_cell(self, val: Any) -> bool:
        if val is None or pd.isna(val):
            return True
        if isinstance(val, str):
            s = val.strip().lower()
            if s == "" or s in NULL_STRING_VARIANTS:
                return True
        return False

    def _analyze_missing_values(self) -> Dict[str, Any]:
        by_column = {}
        total_missing = 0
        empty_columns = []

        for col in self.df.columns:
            series = self.df[col]
            missing_mask = series.apply(self._is_missing_cell)
            missing_count = int(missing_mask.sum())
            missing_pct = round((missing_count / self.total_rows) * 100, 2) if self.total_rows > 0 else 0
            is_empty = missing_count == self.total_rows

            if is_empty:
                empty_columns.append(col)

            # Collect sample affected row indexes (1-indexed)
            affected_rows = [int(idx + 1) for idx in series[missing_mask].index[:10].tolist()]

            by_column[col] = {
                "missing_count": missing_count,
                "missing_pct": missing_pct,
                "is_empty": is_empty,
                "affected_rows_sample": affected_rows
            }
            total_missing += missing_count

        return {
            "total_missing": total_missing,
            "overall_missing_pct": round((total_missing / self.total_cells) * 100, 2) if self.total_cells > 0 else 0,
            "empty_columns": empty_columns,
            "by_column": by_column
        }

    def _analyze_duplicates(self) -> Dict[str, Any]:
        # Exact duplicate rows, preserving first occurrence
        dup_mask = self.df.duplicated(keep="first")
        duplicate_count = int(dup_mask.sum())
        duplicate_pct = round((duplicate_count / self.total_rows) * 100, 2) if self.total_rows > 0 else 0
        duplicate_rows_sample = [int(idx + 1) for idx in self.df[dup_mask].index[:15].tolist()]

        return {
            "duplicate_count": duplicate_count,
            "duplicate_pct": duplicate_pct,
            "duplicate_rows_sample": duplicate_rows_sample
        }

    def _analyze_text_formatting(self) -> Dict[str, Any]:
        whitespace_issues = {}
        casing_inconsistencies = {}
        total_whitespace_count = 0
        total_casing_count = 0

        for col in self.df.columns:
            series = self.df[col].dropna()
            str_series = series[series.apply(lambda x: isinstance(x, str))]
            if len(str_series) == 0:
                continue

            # 1. Whitespace check (leading / trailing / multiple internal spaces)
            def has_whitespace_issue(s: str) -> bool:
                return (s != s.strip()) or (bool(re.search(r"\s{2,}", s)))

            ws_mask = str_series.apply(has_whitespace_issue)
            ws_count = int(ws_mask.sum())
            if ws_count > 0:
                total_whitespace_count += ws_count
                sample_rows = [int(idx + 1) for idx in str_series[ws_mask].index[:10].tolist()]
                sample_vals = str_series[ws_mask].head(5).tolist()
                whitespace_issues[col] = {
                    "count": ws_count,
                    "affected_rows_sample": sample_rows,
                    "sample_values": sample_vals
                }

            # 2. Inconsistent casing check in categorical text columns
            # Group unique stripped strings by their lowercase representation
            unique_vals = [s.strip() for s in str_series.unique() if s.strip() and not self._is_missing_cell(s)]
            case_map = {}
            for v in unique_vals:
                low = v.lower()
                case_map.setdefault(low, set()).add(v)

            # Inconsistencies exist if one lowercase term maps to >= 2 different representations
            inconsistent_groups = {k: sorted(list(v)) for k, v in case_map.items() if len(v) > 1}
            if inconsistent_groups:
                # Count total rows affected by these groups
                affected_casing_rows = []
                for idx, val in str_series.items():
                    if isinstance(val, str) and val.strip().lower() in inconsistent_groups:
                        affected_casing_rows.append(int(idx + 1))
                c_count = len(affected_casing_rows)
                total_casing_count += c_count
                casing_inconsistencies[col] = {
                    "groups": inconsistent_groups,
                    "affected_count": c_count,
                    "affected_rows_sample": affected_casing_rows[:10]
                }

        return {
            "whitespace_issues": whitespace_issues,
            "casing_inconsistencies": casing_inconsistencies,
            "total_whitespace_count": total_whitespace_count,
            "total_casing_count": total_casing_count
        }

    def _analyze_numeric_values(self) -> Dict[str, Any]:
        invalid_entries = {}
        total_invalid_numeric = 0

        for col in self.df.columns:
            series = self.df[col]
            # Check if this column is numeric or candidate numeric
            if pd.api.types.is_numeric_dtype(series):
                continue

            # For object/string columns, test parseability as numbers
            non_missing = series[~series.apply(self._is_missing_cell)]
            if len(non_missing) == 0:
                continue

            # Clean common currency / commas to see if it was intended as a number
            def try_parse_num(val):
                if isinstance(val, (int, float)):
                    return True
                s = str(val).strip()
                # strip $, commas, %, etc.
                s_clean = re.sub(r"[\$,% ]", "", s)
                try:
                    float(s_clean)
                    return True
                except ValueError:
                    return False

            parseable_mask = non_missing.apply(try_parse_num)
            parseable_count = parseable_mask.sum()
            total_non_missing = len(non_missing)

            # If at least 40% of non-missing values can be parsed as numbers,
            # this column was likely intended as numeric
            if (parseable_count / total_non_missing) >= 0.4 and parseable_count < total_non_missing:
                unparseable_mask = ~parseable_mask
                invalid_count = int(unparseable_mask.sum())
                total_invalid_numeric += invalid_count
                sample_rows = [int(idx + 1) for idx in non_missing[unparseable_mask].index[:10].tolist()]
                sample_vals = non_missing[unparseable_mask].head(5).tolist()

                invalid_entries[col] = {
                    "count": invalid_count,
                    "parseable_count": int(parseable_count),
                    "total_tested": total_non_missing,
                    "affected_rows_sample": sample_rows,
                    "sample_values": sample_vals
                }

        return {
            "invalid_entries": invalid_entries,
            "total_invalid_numeric": total_invalid_numeric
        }

    def _analyze_date_values(self) -> Dict[str, Any]:
        invalid_dates = {}
        total_invalid_dates = 0

        # Heuristic keywords for date columns
        date_keywords = ["date", "dob", "time", "day", "created", "updated", "joined", "timestamp", "birth"]

        for col in self.df.columns:
            series = self.df[col]
            if pd.api.types.is_datetime64_any_dtype(series):
                continue

            col_lower = str(col).lower()
            is_candidate = any(kw in col_lower for kw in date_keywords)

            non_missing = series[~series.apply(self._is_missing_cell)]
            if len(non_missing) == 0:
                continue

            # Test datetime parsing
            def parse_date(v):
                try:
                    pd.to_datetime(v, errors="raise", format="mixed")
                    return True
                except Exception:
                    return False

            success_mask = non_missing.apply(parse_date)
            success_count = success_mask.sum()
            total_tested = len(non_missing)

            # If candidate keyword or >40% parsed as dates
            if (is_candidate and total_tested > 0) or ((success_count / total_tested) >= 0.4 and total_tested >= 3):
                unparseable_mask = ~success_mask
                fail_count = int(unparseable_mask.sum())
                if fail_count > 0:
                    total_invalid_dates += fail_count
                    sample_rows = [int(idx + 1) for idx in non_missing[unparseable_mask].index[:10].tolist()]
                    sample_vals = non_missing[unparseable_mask].head(5).tolist()
                    invalid_dates[col] = {
                        "count": fail_count,
                        "valid_count": int(success_count),
                        "total_tested": total_tested,
                        "affected_rows_sample": sample_rows,
                        "sample_values": sample_vals
                    }

        return {
            "invalid_dates": invalid_dates,
            "total_invalid_dates": total_invalid_dates
        }

    def _analyze_outliers(self) -> Dict[str, Any]:
        outliers_by_column = {}
        total_outliers = 0

        for col in self.df.columns:
            # Check strictly numeric series or converted numeric series
            series = pd.to_numeric(
                self.df[col].astype(str).str.replace(r"[\$, ]", "", regex=True),
                errors="coerce"
            ).dropna()

            if len(series) < 6:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            if iqr <= 0:
                continue

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_count = int(outlier_mask.sum())

            if outlier_count > 0:
                total_outliers += outlier_count
                outlier_rows = [int(idx + 1) for idx in series[outlier_mask].index[:10].tolist()]
                outlier_vals = [round(float(v), 2) for v in series[outlier_mask].head(5).tolist()]
                outliers_by_column[col] = {
                    "count": outlier_count,
                    "q1": round(float(q1), 2),
                    "q3": round(float(q3), 2),
                    "iqr": round(float(iqr), 2),
                    "lower_bound": round(float(lower_bound), 2),
                    "upper_bound": round(float(upper_bound), 2),
                    "affected_rows_sample": outlier_rows,
                    "sample_values": outlier_vals,
                    "note": "Statistical outlier based on 1.5x IQR method. An outlier is unusual, not necessarily incorrect."
                }

        return {
            "outliers_by_column": outliers_by_column,
            "total_outliers": total_outliers
        }

    def _analyze_custom_rules(self) -> Dict[str, Any]:
        violations = []
        total_violations = 0

        for rule in self.custom_rules:
            col = rule.get("column")
            if not col or col not in self.df.columns:
                continue

            rule_type = rule.get("rule_type", "range")
            series = self.df[col]
            violating_rows = []
            sample_vals = []

            if rule_type == "range":
                min_val = rule.get("min")
                max_val = rule.get("max")
                num_series = pd.to_numeric(series, errors="coerce")
                for idx, v in num_series.items():
                    if pd.isna(v):
                        continue
                    if (min_val is not None and v < min_val) or (max_val is not None and v > max_val):
                        violating_rows.append(int(idx + 1))
                        sample_vals.append(v)

            elif rule_type == "min":
                min_val = rule.get("min")
                num_series = pd.to_numeric(series, errors="coerce")
                for idx, v in num_series.items():
                    if pd.isna(v):
                        continue
                    if min_val is not None and v < min_val:
                        violating_rows.append(int(idx + 1))
                        sample_vals.append(v)

            elif rule_type == "max":
                max_val = rule.get("max")
                num_series = pd.to_numeric(series, errors="coerce")
                for idx, v in num_series.items():
                    if pd.isna(v):
                        continue
                    if max_val is not None and v > max_val:
                        violating_rows.append(int(idx + 1))
                        sample_vals.append(v)

            elif rule_type == "non_negative":
                num_series = pd.to_numeric(series, errors="coerce")
                for idx, v in num_series.items():
                    if pd.isna(v):
                        continue
                    if v < 0:
                        violating_rows.append(int(idx + 1))
                        sample_vals.append(v)

            elif rule_type == "regex":
                pattern_str = rule.get("pattern", "")
                try:
                    pat = re.compile(pattern_str)
                    for idx, val in series.dropna().items():
                        if not pat.match(str(val).strip()):
                            violating_rows.append(int(idx + 1))
                            sample_vals.append(str(val))
                except Exception:
                    pass

            v_count = len(violating_rows)
            if v_count > 0:
                total_violations += v_count
                violations.append({
                    "column": col,
                    "rule": rule,
                    "count": v_count,
                    "affected_rows_sample": violating_rows[:10],
                    "sample_values": sample_vals[:5]
                })

        return {
            "violations": violations,
            "total_violations": total_violations
        }

    def _generate_column_profiles(self) -> List[Dict[str, Any]]:
        profiles = []
        for col in self.df.columns:
            series = self.df[col]
            missing_mask = series.apply(self._is_missing_cell)
            missing_cnt = int(missing_mask.sum())
            valid_cnt = self.total_rows - missing_cnt

            valid_series = series[~missing_mask]
            distinct_cnt = int(valid_series.nunique())

            # Inferred type
            if pd.api.types.is_numeric_dtype(series):
                inferred_type = "Numeric (Integer)" if pd.api.types.is_integer_dtype(series) else "Numeric (Float)"
            elif pd.api.types.is_datetime64_any_dtype(series):
                inferred_type = "Datetime"
            elif pd.api.types.is_bool_dtype(series):
                inferred_type = "Boolean"
            else:
                # Check if it converts cleanly to numeric
                num_check = pd.to_numeric(valid_series, errors="coerce")
                if len(valid_series) > 0 and num_check.notna().mean() >= 0.8:
                    inferred_type = "Numeric (Mixed/Text)"
                elif distinct_cnt <= 10 and valid_cnt > 20:
                    inferred_type = "Categorical"
                else:
                    inferred_type = "Text / String"

            # Descriptive statistics for numeric
            num_series = pd.to_numeric(valid_series, errors="coerce").dropna()
            stats = None
            if len(num_series) > 0 and (inferred_type.startswith("Numeric") or len(num_series) / max(1, valid_cnt) > 0.5):
                stats = {
                    "min": round(float(num_series.min()), 2),
                    "max": round(float(num_series.max()), 2),
                    "mean": round(float(num_series.mean()), 2),
                    "median": round(float(num_series.median()), 2),
                    "std": round(float(num_series.std()), 2) if len(num_series) > 1 else 0.0
                }

            # Top distinct values preview
            top_values = valid_series.value_counts().head(5).to_dict()
            safe_top_values = {str(k): int(v) for k, v in top_values.items()}

            profiles.append({
                "name": str(col),
                "inferred_type": inferred_type,
                "total_count": self.total_rows,
                "valid_count": valid_cnt,
                "missing_count": missing_cnt,
                "missing_pct": round((missing_cnt / self.total_rows) * 100, 2) if self.total_rows > 0 else 0,
                "distinct_count": distinct_cnt,
                "stats": stats,
                "top_values": safe_top_values
            })

        return profiles

    def _compile_issues(
        self, missing_info, duplicate_info, text_info, numeric_info, date_info, outlier_info, rule_info
    ) -> List[Dict[str, Any]]:
        issues = []
        issue_id = 1

        # 1. Duplicate rows
        if duplicate_info["duplicate_count"] > 0:
            cnt = duplicate_info["duplicate_count"]
            pct = duplicate_info["duplicate_pct"]
            issues.append({
                "id": f"ISSUE_{issue_id}",
                "category": "duplicates",
                "title": "Exact Duplicate Records Found",
                "severity": "critical" if pct > 10 else "warning",
                "column": "Entire Dataset",
                "count": cnt,
                "percentage": pct,
                "affected_rows": duplicate_info["duplicate_rows_sample"],
                "description": f"Detected {cnt} exact duplicate row(s) ({pct}% of dataset). Duplicate rows skew reporting and model training.",
                "recommendation": "Remove duplicate rows, preserving the first occurrence."
            })
            issue_id += 1

        # 2. Missing values
        for col, col_data in missing_info["by_column"].items():
            if col_data["missing_count"] > 0:
                cnt = col_data["missing_count"]
                pct = col_data["missing_pct"]
                severity = "critical" if pct > 40 else ("warning" if pct > 10 else "info")
                if col_data["is_empty"]:
                    desc = f"Column '{col}' is 100% empty (contains no valid data in all {self.total_rows} rows)."
                    rec = "Consider dropping this empty column or reviewing data pipeline extraction."
                else:
                    desc = f"Column '{col}' has {cnt} missing or null values ({pct}% of column rows)."
                    rec = "Impute missing values using mean/median/mode, provide a default constant, or drop affected rows."

                issues.append({
                    "id": f"ISSUE_{issue_id}",
                    "category": "missing",
                    "title": f"Missing Values in '{col}'",
                    "severity": severity,
                    "column": col,
                    "count": cnt,
                    "percentage": pct,
                    "affected_rows": col_data["affected_rows_sample"],
                    "description": desc,
                    "recommendation": rec
                })
                issue_id += 1

        # 3. Whitespace formatting
        for col, data in text_info["whitespace_issues"].items():
            cnt = data["count"]
            pct = round((cnt / self.total_rows) * 100, 2)
            issues.append({
                "id": f"ISSUE_{issue_id}",
                "category": "formatting",
                "title": f"Leading / Trailing Whitespace in '{col}'",
                "severity": "warning",
                "column": col,
                "count": cnt,
                "percentage": pct,
                "affected_rows": data["affected_rows_sample"],
                "description": f"Found {cnt} text cell(s) in '{col}' with leading, trailing, or double internal spaces.",
                "recommendation": "Trim whitespace across all text columns to prevent lookup and join errors."
            })
            issue_id += 1

        # 4. Inconsistent casing
        for col, data in text_info["casing_inconsistencies"].items():
            cnt = data["affected_count"]
            pct = round((cnt / self.total_rows) * 100, 2)
            groups_desc = ", ".join([f"'{k}': {v}" for k, v in list(data["groups"].items())[:3]])
            issues.append({
                "id": f"ISSUE_{issue_id}",
                "category": "formatting",
                "title": f"Inconsistent Capitalization in '{col}'",
                "severity": "warning",
                "column": col,
                "count": cnt,
                "percentage": pct,
                "affected_rows": data["affected_rows_sample"],
                "description": f"Column '{col}' contains inconsistent capitalization variations (e.g., {groups_desc}).",
                "recommendation": "Standardize capitalization to Title Case, lowercase, or UPPERCASE."
            })
            issue_id += 1

        # 5. Invalid numeric entries
        for col, data in numeric_info["invalid_entries"].items():
            cnt = data["count"]
            pct = round((cnt / self.total_rows) * 100, 2)
            sample_str = ", ".join([str(s) for s in data["sample_values"][:3]])
            issues.append({
                "id": f"ISSUE_{issue_id}",
                "category": "invalid",
                "title": f"Non-Numeric Values in Numeric Column '{col}'",
                "severity": "critical",
                "column": col,
                "count": cnt,
                "percentage": pct,
                "affected_rows": data["affected_rows_sample"],
                "description": f"Found {cnt} cell(s) in '{col}' that cannot be converted to numeric values (samples: {sample_str}).",
                "recommendation": "Clean currency/special symbols or coerce unparseable entries to null."
            })
            issue_id += 1

        # 6. Invalid date formats
        for col, data in date_info["invalid_dates"].items():
            cnt = data["count"]
            pct = round((cnt / self.total_rows) * 100, 2)
            sample_str = ", ".join([str(s) for s in data["sample_values"][:3]])
            issues.append({
                "id": f"ISSUE_{issue_id}",
                "category": "invalid",
                "title": f"Unparseable Date Formats in '{col}'",
                "severity": "critical",
                "column": col,
                "count": cnt,
                "percentage": pct,
                "affected_rows": data["affected_rows_sample"],
                "description": f"Found {cnt} unparseable or mixed date values in '{col}' (samples: {sample_str}).",
                "recommendation": "Standardize dates to ISO format (YYYY-MM-DD)."
            })
            issue_id += 1

        # 7. Outliers
        for col, data in outlier_info["outliers_by_column"].items():
            cnt = data["count"]
            pct = round((cnt / self.total_rows) * 100, 2)
            samples = ", ".join([str(s) for s in data["sample_values"][:3]])
            issues.append({
                "id": f"ISSUE_{issue_id}",
                "category": "outliers",
                "title": f"Statistical Outliers in '{col}'",
                "severity": "info",
                "column": col,
                "count": cnt,
                "percentage": pct,
                "affected_rows": data["affected_rows_sample"],
                "description": f"Found {cnt} value(s) outside 1.5x IQR boundary [{data['lower_bound']} to {data['upper_bound']}] (samples: {samples}).",
                "recommendation": "Review outliers manually. Outliers are unusual but may be legitimate records."
            })
            issue_id += 1

        # 8. Custom rule violations
        for v in rule_info["violations"]:
            col = v["column"]
            cnt = v["count"]
            pct = round((cnt / self.total_rows) * 100, 2)
            rule_type = v["rule"].get("rule_type")
            issues.append({
                "id": f"ISSUE_{issue_id}",
                "category": "custom_rules",
                "title": f"Rule Violation: {rule_type} on '{col}'",
                "severity": "warning",
                "column": col,
                "count": cnt,
                "percentage": pct,
                "affected_rows": v["affected_rows_sample"],
                "description": f"{cnt} row(s) violated custom constraint: {v['rule']}.",
                "recommendation": "Review offending values or filter rows outside configured range."
            })
            issue_id += 1

        return issues

    def _calculate_problematic_cells(
        self, missing_info, duplicate_info, text_info, numeric_info, date_info
    ) -> int:
        count = 0
        count += missing_info["total_missing"]
        count += duplicate_info["duplicate_count"] * self.total_cols
        count += text_info["total_whitespace_count"]
        count += text_info["total_casing_count"]
        count += numeric_info["total_invalid_numeric"]
        count += date_info["total_invalid_dates"]
        return min(count, self.total_cells)

    def _get_safe_preview(self, limit: int = 30) -> List[Dict[str, Any]]:
        preview_df = self.df.head(limit).copy()
        # Convert non-serializable elements to safe JSON representation
        records = []
        for idx, row in preview_df.iterrows():
            clean_row = {"_row_index": int(idx + 1)}
            for col in preview_df.columns:
                val = row[col]
                if pd.isna(val) or val is None:
                    clean_row[str(col)] = ""
                elif isinstance(val, (np.integer, int)):
                    clean_row[str(col)] = int(val)
                elif isinstance(val, (np.floating, float)):
                    clean_row[str(col)] = round(float(val), 4) if not (math.isnan(val) or math.isinf(val)) else ""
                else:
                    clean_row[str(col)] = str(val)
            records.append(clean_row)
        return records
