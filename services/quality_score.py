from typing import Dict, Any
from config import Config


class QualityScoreEngine:
    """
    Computes a transparent, standardized Data Quality Score (0 - 100).
    Formula:
      Overall Score = (Missing Score * 0.35)
                    + (Duplicate Score * 0.25)
                    + (Validity Score * 0.25)
                    + (Formatting Score * 0.15)
    
    Each component is scored from 0 to 100 based on the detected error rate.
    """

    DEFAULT_WEIGHTS = Config.SCORE_WEIGHTS

    @classmethod
    def calculate(cls, analysis_results: Dict[str, Any], weights: Dict[str, float] = None) -> Dict[str, Any]:
        w = weights or cls.DEFAULT_WEIGHTS

        summary = analysis_results.get("summary", {})
        total_rows = summary.get("total_rows", 0)
        total_cols = summary.get("total_cols", 0)
        total_cells = summary.get("total_cells", 0)

        if total_rows == 0 or total_cols == 0 or total_cells == 0:
            return {
                "overall_score": 0.0,
                "grade": "F",
                "status": "Empty Dataset",
                "breakdown": {
                    "missing": {"score": 0.0, "weight": w["missing"], "penalty": 100.0, "details": "No data available"},
                    "duplicates": {"score": 0.0, "weight": w["duplicates"], "penalty": 100.0, "details": "No data available"},
                    "invalid": {"score": 0.0, "weight": w["invalid"], "penalty": 100.0, "details": "No data available"},
                    "formatting": {"score": 0.0, "weight": w["formatting"], "penalty": 100.0, "details": "No data available"}
                },
                "methodology": "Score is based on weighted error rates across missing values, duplicates, invalid values, and formatting."
            }

        # 1. Missing Score (0 - 100)
        missing_analysis = analysis_results.get("missing_analysis", {})
        total_missing = missing_analysis.get("total_missing", 0)
        missing_rate = total_missing / total_cells if total_cells > 0 else 0
        # Linear scaling penalty: 100% missing -> 0 score; 0% missing -> 100 score
        # Using a slight multiplier to penalize high missing rates appropriately
        missing_penalty = min(100.0, missing_rate * 150.0)
        missing_score = max(0.0, 100.0 - missing_penalty)

        # 2. Duplicate Score (0 - 100)
        duplicate_analysis = analysis_results.get("duplicate_analysis", {})
        dup_count = duplicate_analysis.get("duplicate_count", 0)
        dup_rate = dup_count / total_rows if total_rows > 0 else 0
        # Duplicate penalty: 50% duplicate rows gives maximum penalty
        dup_penalty = min(100.0, dup_rate * 200.0)
        duplicate_score = max(0.0, 100.0 - dup_penalty)

        # 3. Validity Score (0 - 100)
        numeric_analysis = analysis_results.get("numeric_analysis", {})
        date_analysis = analysis_results.get("date_analysis", {})
        rule_analysis = analysis_results.get("rule_analysis", {})

        total_invalid = (
            numeric_analysis.get("total_invalid_numeric", 0) +
            date_analysis.get("total_invalid_dates", 0) +
            rule_analysis.get("total_violations", 0)
        )
        invalid_rate = total_invalid / total_cells if total_cells > 0 else 0
        invalid_penalty = min(100.0, invalid_rate * 300.0)
        invalid_score = max(0.0, 100.0 - invalid_penalty)

        # 4. Formatting Score (0 - 100)
        text_analysis = analysis_results.get("text_analysis", {})
        total_formatting = (
            text_analysis.get("total_whitespace_count", 0) +
            text_analysis.get("total_casing_count", 0)
        )
        format_rate = total_formatting / total_cells if total_cells > 0 else 0
        format_penalty = min(100.0, format_rate * 200.0)
        formatting_score = max(0.0, 100.0 - format_penalty)

        # Weighted combination
        overall = (
            (missing_score * w["missing"]) +
            (duplicate_score * w["duplicates"]) +
            (invalid_score * w["invalid"]) +
            (formatting_score * w["formatting"])
        )
        overall = round(max(0.0, min(100.0, overall)), 1)

        # Letter grade and status badge
        if overall >= 90:
            grade = "A"
            status = "Excellent"
        elif overall >= 80:
            grade = "B"
            status = "Good"
        elif overall >= 65:
            grade = "C"
            status = "Fair"
        elif overall >= 50:
            grade = "D"
            status = "Needs Attention"
        else:
            grade = "F"
            status = "Critical Issues"

        return {
            "overall_score": overall,
            "grade": grade,
            "status": status,
            "breakdown": {
                "missing": {
                    "score": round(missing_score, 1),
                    "weight": round(w["missing"] * 100, 0),
                    "penalty": round(missing_penalty, 1),
                    "count": total_missing,
                    "details": f"{total_missing} missing cells ({round(missing_rate * 100, 1)}% of all cells)"
                },
                "duplicates": {
                    "score": round(duplicate_score, 1),
                    "weight": round(w["duplicates"] * 100, 0),
                    "penalty": round(dup_penalty, 1),
                    "count": dup_count,
                    "details": f"{dup_count} duplicate rows ({round(dup_rate * 100, 1)}% of records)"
                },
                "invalid": {
                    "score": round(invalid_score, 1),
                    "weight": round(w["invalid"] * 100, 0),
                    "penalty": round(invalid_penalty, 1),
                    "count": total_invalid,
                    "details": f"{total_invalid} invalid or rule-violating cells"
                },
                "formatting": {
                    "score": round(formatting_score, 1),
                    "weight": round(w["formatting"] * 100, 0),
                    "penalty": round(format_penalty, 1),
                    "count": total_formatting,
                    "details": f"{total_formatting} whitespace or capitalization issues"
                }
            },
            "formula_explanation": (
                f"Overall Score = (Missing {round(missing_score,1)} * {w['missing']}) + "
                f"(Duplicates {round(duplicate_score,1)} * {w['duplicates']}) + "
                f"(Invalid {round(invalid_score,1)} * {w['invalid']}) + "
                f"(Formatting {round(formatting_score,1)} * {w['formatting']}) = {overall}/100"
            )
        }
