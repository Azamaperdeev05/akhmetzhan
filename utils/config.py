from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _as_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    return int(value)


def _as_float(value: str | None, default: float) -> float:
    if value is None or value.strip() == "":
        return default
    return float(value)


@dataclass(frozen=True)
class Settings:
    project_root: Path
    database_url: str
    scan_interval_minutes: int
    phishing_threshold: float
    flask_secret_key: str
    gmail_client_id: str | None
    gmail_client_secret: str | None
    gmail_redirect_uri: str | None
    gmail_credentials_path: Path
    gmail_token_path: Path
    gmail_query: str
    gmail_label_name: str
    max_results_per_scan: int
    log_level: str
    processed_data_dir: Path
    model_dir: Path
    scan_timeout_seconds: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        project_root=PROJECT_ROOT,
        database_url=os.getenv("DATABASE_URL", "sqlite:///phishguard.db"),
        scan_interval_minutes=_as_int(os.getenv("SCAN_INTERVAL_MINUTES"), 5),
        phishing_threshold=_as_float(os.getenv("PHISHING_THRESHOLD"), 0.75),
        flask_secret_key=os.getenv("FLASK_SECRET_KEY", "change-me"),
        gmail_client_id=os.getenv("GMAIL_CLIENT_ID"),
        gmail_client_secret=os.getenv("GMAIL_CLIENT_SECRET"),
        gmail_redirect_uri=os.getenv("GMAIL_REDIRECT_URI"),
        gmail_credentials_path=PROJECT_ROOT
        / os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json"),
        gmail_token_path=PROJECT_ROOT / os.getenv("GMAIL_TOKEN_PATH", "token.json"),
        gmail_query=os.getenv("GMAIL_QUERY", "in:inbox newer_than:1d"),
        gmail_label_name=os.getenv("GMAIL_LABEL_NAME", "PHISHING"),
        max_results_per_scan=_as_int(os.getenv("MAX_RESULTS_PER_SCAN"), 20),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        processed_data_dir=PROJECT_ROOT
        / os.getenv("PROCESSED_DATA_DIR", "data/processed"),
        model_dir=PROJECT_ROOT / os.getenv("MODEL_DIR", "model/saved_model"),
        scan_timeout_seconds=_as_int(os.getenv("SCAN_TIMEOUT_SECONDS"), 10),
    )

