import io
from datetime import datetime, timezone
from typing import Dict, Any, List
import pandas as pd


class ReportGenerator:
    """
    Generates comprehensive Data Quality Audit and Repair Reports in JSON and CSV formats.
    Provides complete before-and-after transparency for audits, stakeholders, and hackathon judges.
    """

    @classmethod
    def generate_full_report(
        cls,
        filename: str,
        initial_analysis: Dict[str, Any],
        initial_score: Dict[str, Any],
        cleaned_analysis: Dict[str, Any],
        cleaned_score: Dict[str, Any],
        audit_log: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Creates structured audit report comparing original and cleaned datasets."""
        init_summary = initial_analysis.get("summary", {})
        clean_summary = cleaned_analysis.get("summary", {})

        init_issues = initial_analysis.get("issues", [])
        clean_issues = cleaned_analysis.get("issues", [])

        # Count issues resolved
        total_initial_issues = len(init_issues)
        total_remaining_issues = len(clean_issues)
        issues_resolved = max(0, total_initial_issues - total_remaining_issues)

        score_delta = round(cleaned_score.get("overall_score", 0.0) - initial_score.get("overall_score", 0.0), 1)

        report = {
            "metadata": {
                "dataset_name": filename,
                "report_id": f"REP_{int(datetime.now().timestamp())}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "engine_version": "DataWise AI v1.0.0"
            },
            "executive_summary": {
                "initial_score": initial_score.get("overall_score", 0.0),
                "initial_grade": initial_score.get("grade", "F"),
                "cleaned_score": cleaned_score.get("overall_score", 0.0),
                "cleaned_grade": cleaned_score.get("grade", "A"),
                "score_improvement": score_delta,
                "initial_rows": init_summary.get("total_rows", 0),
                "cleaned_rows": clean_summary.get("total_rows", 0),
                "rows_delta": clean_summary.get("total_rows", 0) - init_summary.get("total_rows", 0),
                "initial_columns": init_summary.get("total_cols", 0),
                "cleaned_columns": clean_summary.get("total_cols", 0),
                "total_issues_detected": total_initial_issues,
                "total_issues_resolved": issues_resolved,
                "total_issues_remaining": total_remaining_issues,
                "resolution_rate_pct": round((issues_resolved / max(1, total_initial_issues)) * 100, 1)
            },
            "category_comparison": {
                "missing_values": {
                    "initial_count": initial_analysis.get("missing_analysis", {}).get("total_missing", 0),
                    "cleaned_count": cleaned_analysis.get("missing_analysis", {}).get("total_missing", 0),
                    "resolved": (
                        initial_analysis.get("missing_analysis", {}).get("total_missing", 0) -
                        cleaned_analysis.get("missing_analysis", {}).get("total_missing", 0)
                    )
                },
                "duplicate_rows": {
                    "initial_count": initial_analysis.get("duplicate_analysis", {}).get("duplicate_count", 0),
                    "cleaned_count": cleaned_analysis.get("duplicate_analysis", {}).get("duplicate_count", 0),
                    "resolved": (
                        initial_analysis.get("duplicate_analysis", {}).get("duplicate_count", 0) -
                        cleaned_analysis.get("duplicate_analysis", {}).get("duplicate_count", 0)
                    )
                },
                "formatting_issues": {
                    "initial_count": (
                        initial_analysis.get("text_analysis", {}).get("total_whitespace_count", 0) +
                        initial_analysis.get("text_analysis", {}).get("total_casing_count", 0)
                    ),
                    "cleaned_count": (
                        cleaned_analysis.get("text_analysis", {}).get("total_whitespace_count", 0) +
                        cleaned_analysis.get("text_analysis", {}).get("total_casing_count", 0)
                    )
                },
                "invalid_entries": {
                    "initial_count": (
                        initial_analysis.get("numeric_analysis", {}).get("total_invalid_numeric", 0) +
                        initial_analysis.get("date_analysis", {}).get("total_invalid_dates", 0)
                    ),
                    "cleaned_count": (
                        cleaned_analysis.get("numeric_analysis", {}).get("total_invalid_numeric", 0) +
                        cleaned_analysis.get("date_analysis", {}).get("total_invalid_dates", 0)
                    )
                }
            },
            "cleaning_operations_applied": audit_log,
            "column_profiles_summary": cleaned_analysis.get("column_profiles", []),
            "remaining_issues": clean_issues,
            "scoring_methodology": {
                "weights": initial_score.get("breakdown", {}),
                "formula": initial_score.get("formula_explanation", ""),
                "disclaimer": "DataWise AI measures adherence to common statistical and programmatic data quality standards. A score of 100 indicates no errors detected by implemented checks, not external factual ground-truth."
            }
        }
        return report

    @classmethod
    def generate_summary_csv(cls, report: Dict[str, Any]) -> str:
        """Converts key metrics and column comparison to a clean CSV summary string."""
        buffer = io.StringIO()
        exec_sum = report.get("executive_summary", {})
        meta = report.get("metadata", {})

        # Header summary
        buffer.write(f"# DataWise AI Quality & Audit Report\n")
        buffer.write(f"# Dataset: {meta.get('dataset_name')}\n")
        buffer.write(f"# Generated: {meta.get('generated_at')}\n")
        buffer.write(f"# Initial Score: {exec_sum.get('initial_score')} ({exec_sum.get('initial_grade')})\n")
        buffer.write(f"# Cleaned Score: {exec_sum.get('cleaned_score')} ({exec_sum.get('cleaned_grade')})\n")
        buffer.write(f"# Score Improvement: +{exec_sum.get('score_improvement')} pts\n")
        buffer.write(f"# Rows: {exec_sum.get('initial_rows')} -> {exec_sum.get('cleaned_rows')}\n")
        buffer.write(f"# Issues Resolved: {exec_sum.get('total_issues_resolved')} of {exec_sum.get('total_issues_detected')}\n\n")

        # Column breakdown table
        col_profiles = report.get("column_profiles_summary", [])
        if col_profiles:
            df_cols = pd.DataFrame([
                {
                    "Column Name": p.get("name"),
                    "Inferred Type": p.get("inferred_type"),
                    "Valid Rows": p.get("valid_count"),
                    "Missing Count": p.get("missing_count"),
                    "Missing %": f"{p.get('missing_pct')}%",
                    "Distinct Values": p.get("distinct_count"),
                    "Min": p.get("stats", {}).get("min") if p.get("stats") else "N/A",
                    "Max": p.get("stats", {}).get("max") if p.get("stats") else "N/A",
                    "Mean": p.get("stats", {}).get("mean") if p.get("stats") else "N/A",
                }
                for p in col_profiles
            ])
            df_cols.to_csv(buffer, index=False)

        return buffer.getvalue()
