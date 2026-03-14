from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

from analyzer.pipeline import PhishGuardPipeline
from gmail.auth import get_gmail_service
from main import scan_once
from model.predict import PhishingPredictor
from utils.config import get_settings, reload_settings
from utils.database import Database
from utils.logger import get_logger, setup_logging


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DashboardScannerService:
    def __init__(self) -> None:
        settings = get_settings()
        setup_logging(settings.log_level)

        self._logger = get_logger("phishguard.dashboard.scanner")
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._seen_ids: set[str] = set()
        self._predictor: PhishingPredictor | None = None
        self._predictor_model_dir: Path | None = None
        self._auto_enabled = bool(settings.auto_scan_enabled)
        self._last_status: dict[str, object] = {
            "ok": True,
            "trigger": "none",
            "source": "n/a",
            "scanned": 0,
            "phishing": 0,
            "timestamp": "",
            "error": "",
        }

        if self._auto_enabled:
            self.start_auto()

    def _ensure_predictor(self, settings) -> PhishingPredictor:
        model_dir = Path(settings.model_dir).resolve()
        if self._predictor is None or self._predictor_model_dir != model_dir:
            self._predictor = PhishingPredictor(
                model_dir=model_dir,
                mode="auto",
                threshold=settings.phishing_threshold,
                prefer_gpu=True,
            )
            self._predictor_model_dir = model_dir
            self._logger.info("predictor_loaded backend=%s model_dir=%s", self._predictor.backend, model_dir)
        return self._predictor

    def _resolve_gmail_service(self, settings):
        try:
            service = get_gmail_service(
                credentials_path=settings.gmail_credentials_path,
                token_path=settings.gmail_token_path,
            )
            return service, "gmail", ""
        except Exception as exc:
            error_text = str(exc)
            self._logger.warning("gmail_service=disabled reason=%s", error_text)
            return None, "sample", error_text

    def run_scan_cycle(self, trigger: str = "manual") -> dict[str, object]:
        with self._lock:
            settings = reload_settings()
            db = Database(settings.database_url)
            predictor = self._ensure_predictor(settings)
            pipeline = PhishGuardPipeline(
                predictor=predictor,
                threshold=settings.phishing_threshold,
                expand_short_urls=False,
            )
            service, source, service_error = self._resolve_gmail_service(settings)

            try:
                scanned, phishing = scan_once(
                    db=db,
                    pipeline=pipeline,
                    logger=self._logger,
                    settings=settings,
                    service=service,
                    max_results=settings.max_results_per_scan,
                    seen_ids=self._seen_ids,
                    sample_path=settings.project_root / "data" / "raw" / "sample_inbox.json",
                    allow_sample_fallback=settings.allow_sample_fallback,
                )
                self._last_status = {
                    "ok": True,
                    "trigger": trigger,
                    "source": source,
                    "scanned": scanned,
                    "phishing": phishing,
                    "timestamp": _utcnow_iso(),
                    "error": "" if source == "gmail" else service_error,
                }
                return dict(self._last_status)
            except Exception as exc:
                self._last_status = {
                    "ok": False,
                    "trigger": trigger,
                    "source": source,
                    "scanned": 0,
                    "phishing": 0,
                    "timestamp": _utcnow_iso(),
                    "error": str(exc),
                }
                raise

    def _auto_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_scan_cycle(trigger="auto")
            except Exception:
                self._logger.exception("auto_scan_cycle_failed")

            settings = reload_settings()
            sleep_seconds = max(30, int(settings.scan_interval_minutes) * 60)
            self._stop_event.wait(timeout=sleep_seconds)

    def start_auto(self) -> None:
        self._auto_enabled = True
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._auto_loop,
            name="phishguard-auto-scan",
            daemon=True,
        )
        self._thread.start()
        self._logger.info("auto_scan=started")

    def stop_auto(self) -> None:
        self._auto_enabled = False
        self._stop_event.set()
        self._logger.info("auto_scan=stopped")

    def set_auto_enabled(self, enabled: bool) -> None:
        if enabled:
            self.start_auto()
        else:
            self.stop_auto()

    def is_auto_enabled(self) -> bool:
        return self._auto_enabled

    def get_last_status(self) -> dict[str, object]:
        return dict(self._last_status)
