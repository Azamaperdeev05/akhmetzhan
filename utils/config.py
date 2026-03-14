from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_env_path() -> Path:
    configured = os.getenv("PHISHGUARD_ENV_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return PROJECT_ROOT / ".env"


load_dotenv(get_env_path())


def _as_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    return int(value)


def _as_float(value: str | None, default: float) -> float:
    if value is None or value.strip() == "":
        return default
    return float(value)


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    project_root: Path
    database_url: str
    scan_interval_minutes: int
    phishing_threshold: float
    flask_secret_key: str
    dashboard_username: str
    dashboard_password: str
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
    auto_scan_enabled: bool
    allow_sample_fallback: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        project_root=PROJECT_ROOT,
        database_url=os.getenv("DATABASE_URL", "sqlite:///phishguard.db"),
        scan_interval_minutes=_as_int(os.getenv("SCAN_INTERVAL_MINUTES"), 5),
        phishing_threshold=_as_float(os.getenv("PHISHING_THRESHOLD"), 0.75),
        flask_secret_key=os.getenv("FLASK_SECRET_KEY", "change-me"),
        dashboard_username=os.getenv("DASHBOARD_USERNAME", "admin"),
        dashboard_password=os.getenv("DASHBOARD_PASSWORD", "admin12345"),
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
        auto_scan_enabled=_as_bool(os.getenv("AUTO_SCAN_ENABLED"), False),
        allow_sample_fallback=_as_bool(os.getenv("ALLOW_SAMPLE_FALLBACK"), False),
    )


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


def update_env_values(updates: dict[str, str], env_path: Path | None = None) -> Path:
    target = env_path or get_env_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        lines = target.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    normalized = {key: str(value) for key, value in updates.items()}
    seen: set[str] = set()
    output: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output.append(line)
            continue

        key, _value = line.split("=", 1)
        key = key.strip()
        if key in normalized:
            output.append(f"{key}={normalized[key]}")
            seen.add(key)
        else:
            output.append(line)

    for key, value in normalized.items():
        if key not in seen:
            output.append(f"{key}={value}")

    target.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    for key, value in normalized.items():
        os.environ[key] = value
    reload_settings()
    return target
