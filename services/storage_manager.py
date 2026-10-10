import io
import json
import os
import re
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import pandas as pd

from config import Config

UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)


class StorageManager:
    """
    Manages isolated, disk-backed session storage for uploaded datasets,
    cleaning operations, and generated reports.
    Designed for multi-worker production compatibility and defense against path traversal.
    """

    def __init__(self, base_dir: Optional[Path] = None, expiry_minutes: Optional[int] = None):
        self.base_dir = Path(base_dir or Config.TEMP_STORAGE_DIR)
        self.expiry_minutes = expiry_minutes or Config.SESSION_EXPIRY_MINUTES
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _validate_token(self, token: str) -> bool:
        if not token or not isinstance(token, str):
            return False
        return bool(UUID_REGEX.match(token))

    def _get_session_dir(self, token: str) -> Path:
        if not self._validate_token(token):
            raise ValueError("Invalid or malformed session token.")
        session_dir = (self.base_dir / token).resolve()
        # Prevent any path traversal
        if not str(session_dir).startswith(str(self.base_dir.resolve())):
            raise ValueError("Unauthorized path traversal detected.")
        return session_dir

    def create_session(self, df: pd.DataFrame, filename: str) -> str:
        """Creates a new session folder and stores the original dataset."""
        self.cleanup_expired()
        token = str(uuid.uuid4())
        session_dir = self._get_session_dir(token)
        session_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename for safe metadata display
        safe_filename = Path(filename).name
        if len(safe_filename) > 100:
            safe_filename = safe_filename[:96] + Path(filename).suffix

        # Store as CSV and JSON metadata
        original_csv_path = session_dir / "original.csv"
        df.to_csv(original_csv_path, index=False, encoding="utf-8")

        meta = {
            "token": token,
            "filename": safe_filename,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": time.time(),
            "original_rows": len(df),
            "original_cols": len(df.columns),
            "has_cleaned": False,
            "operations_applied": []
        }
        with open(session_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return token

    def get_meta(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            session_dir = self._get_session_dir(token)
            meta_path = session_dir / "meta.json"
            if not meta_path.exists():
                return None
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def get_original_df(self, token: str) -> Optional[pd.DataFrame]:
        try:
            session_dir = self._get_session_dir(token)
            path = session_dir / "original.csv"
            if not path.exists():
                return None
            return pd.read_csv(path, keep_default_na=False, na_values=[""])
        except Exception:
            return None

    def save_cleaned_df(self, token: str, cleaned_df: pd.DataFrame, operations_applied: list) -> bool:
        try:
            session_dir = self._get_session_dir(token)
            cleaned_path = session_dir / "cleaned.csv"
            cleaned_df.to_csv(cleaned_path, index=False, encoding="utf-8")

            meta = self.get_meta(token) or {}
            meta["has_cleaned"] = True
            meta["cleaned_rows"] = len(cleaned_df)
            meta["cleaned_cols"] = len(cleaned_df.columns)
            meta["cleaned_at"] = datetime.now(timezone.utc).isoformat()
            meta["operations_applied"] = operations_applied

            with open(session_dir / "meta.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            return True
        except Exception:
            return False

    def get_cleaned_df(self, token: str) -> Optional[pd.DataFrame]:
        try:
            session_dir = self._get_session_dir(token)
            path = session_dir / "cleaned.csv"
            if not path.exists():
                return None
            return pd.read_csv(path, keep_default_na=False, na_values=[""])
        except Exception:
            return None

    def reset_session(self, token: str) -> bool:
        """Resets the cleaned dataset back to original state."""
        try:
            session_dir = self._get_session_dir(token)
            cleaned_path = session_dir / "cleaned.csv"
            if cleaned_path.exists():
                cleaned_path.unlink()
            
            meta = self.get_meta(token)
            if meta:
                meta["has_cleaned"] = False
                meta["cleaned_rows"] = None
                meta["cleaned_cols"] = None
                meta["operations_applied"] = []
                with open(session_dir / "meta.json", "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)
            return True
        except Exception:
            return False

    def save_analysis(self, token: str, analysis: dict, is_cleaned: bool = False) -> bool:
        try:
            session_dir = self._get_session_dir(token)
            filename = "analysis_cleaned.json" if is_cleaned else "analysis_original.json"
            with open(session_dir / filename, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2)
            return True
        except Exception:
            return False

    def get_analysis(self, token: str, is_cleaned: bool = False) -> Optional[dict]:
        try:
            session_dir = self._get_session_dir(token)
            filename = "analysis_cleaned.json" if is_cleaned else "analysis_original.json"
            path = session_dir / filename
            if not path.exists():
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_report(self, token: str, report: dict) -> bool:
        try:
            session_dir = self._get_session_dir(token)
            with open(session_dir / "report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            return True
        except Exception:
            return False

    def get_report(self, token: str) -> Optional[dict]:
        try:
            session_dir = self._get_session_dir(token)
            path = session_dir / "report.json"
            if not path.exists():
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def export_csv(self, token: str, cleaned: bool = True) -> Optional[bytes]:
        df = self.get_cleaned_df(token) if cleaned else self.get_original_df(token)
        if df is None and cleaned:
            df = self.get_original_df(token)
        if df is None:
            return None
        buffer = io.StringIO()
        df.to_csv(buffer, index=False, encoding="utf-8")
        return buffer.getvalue().encode("utf-8")

    def export_excel(self, token: str, cleaned: bool = True) -> Optional[bytes]:
        df = self.get_cleaned_df(token) if cleaned else self.get_original_df(token)
        if df is None and cleaned:
            df = self.get_original_df(token)
        if df is None:
            return None
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="DataWise_Cleaned" if cleaned else "DataWise_Original")
        buffer.seek(0)
        return buffer.getvalue()

    def cleanup_expired(self) -> int:
        """Deletes session directories that are older than expiry_minutes."""
        cleaned_count = 0
        now = time.time()
        expiry_seconds = self.expiry_minutes * 60
        if not self.base_dir.exists():
            return 0
        for entry in self.base_dir.iterdir():
            if entry.is_dir() and UUID_REGEX.match(entry.name):
                try:
                    meta_path = entry / "meta.json"
                    created_time = entry.stat().st_mtime
                    if meta_path.exists():
                        try:
                            with open(meta_path, "r", encoding="utf-8") as f:
                                meta = json.load(f)
                                created_time = meta.get("timestamp", created_time)
                        except Exception:
                            pass
                    if (now - created_time) > expiry_seconds:
                        shutil.rmtree(entry, ignore_errors=True)
                        cleaned_count += 1
                except Exception:
                    pass
        return cleaned_count
