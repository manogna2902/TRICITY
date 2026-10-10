import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "datawise-ai-hackathon-secret-key-2025")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB limit
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
    
    # Storage settings
    TEMP_STORAGE_DIR = BASE_DIR / "temp_storage"
    SAMPLE_DATA_PATH = BASE_DIR / "sample_data" / "sample_dataset.csv"
    SESSION_EXPIRY_MINUTES = int(os.environ.get("SESSION_EXPIRY_MINUTES", "60"))
    
    # Preview limits
    MAX_PREVIEW_ROWS = 50
    MAX_PROCESSING_ROWS = 100000  # Safe cap for interactive in-memory processing
    
    # Data Quality Scoring Weights (must sum to 1.0)
    SCORE_WEIGHTS = {
        "missing": 0.35,
        "duplicates": 0.25,
        "invalid": 0.25,
        "formatting": 0.15
    }

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    TESTING = True
    DEBUG = False
