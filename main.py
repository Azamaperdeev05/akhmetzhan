from __future__ import annotations

import argparse
import time
from pathlib import Path

from analyzer.pipeline import PhishGuardPipeline
from gmail.auth import get_gmail_service
from gmail.fetch_emails import fetch_recent_emails, load_sample_emails
from gmail.label_manager import mark_as_phishing
from model.predict import PhishingPredictor
from utils.config import get_settings
from utils.database import Database
from utils.logger import get_logger, setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PhishGuard inbox scanning service.")
    parser.add_argument("--once", action="store_true", help="Run one scan cycle and exit.")
    parser.add_argument("--max-results", type=int, default=None, help="Override max inbox messages per cycle.")
    parser.add_argument(
        "--offline-samples",
        type=Path,
        default=Path("data/raw/sample_inbox.json"),
        help="Path to local sample inbox file used when Gmail API is unavailable.",
    )
    return parser.parse_args()


RETRYABLE_HTTP_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def is_retryable_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is None and hasattr(exc, "resp"):
        status = getattr(exc.resp, "status", None)

    if status is not None:
        try:
            return int(status) in RETRYABLE_HTTP_STATUS
        except (TypeError, ValueError):
            return False

    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True

    lowered = str(exc).lower()
    return any(
        token in lowered
        for token in (
            "timed out",
            "temporarily unavailable",
            "rate limit",
            "connection reset",
            "503",
            "429",
        )
    )


def run_with_retry(logger, fn, retries: int = 3, base_delay: float = 1.5):
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            retryable = is_retryable_error(exc)
            if (not retryable) or attempt == retries:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "retryable_error=%s retryable=%s attempt=%s/%s next_delay_sec=%.1f",
                exc,
                retryable,
                attempt,
                retries,
                delay,
            )
            time.sleep(delay)
    return None


def scan_once(
    db: Database,
    pipeline: PhishGuardPipeline,
    logger,
    settings,
    service,
    max_results: int,
    seen_ids: set[str],
    sample_path: Path,
) -> tuple[int, int]:
    run_id = db.start_scan_run()
    scanned_count = 0
    phishing_count = 0
    label_failure_count = 0

    if service is None:
        logger.warning("gmail_service=unavailable using_sample_emails=%s", sample_path)
        emails = load_sample_emails(sample_path)
    else:
        emails = run_with_retry(
            logger,
            lambda: fetch_recent_emails(
                service=service,
                query=settings.gmail_query,
                max_results=max_results,
                seen_ids=seen_ids,
            ),
            retries=3,
        )

    for email in emails:
        if db.has_scan_result(email.message_id):
            continue

        result = pipeline.scan_email(email)
        db.save_scan_result(email=email, result=result, run_id=run_id)
        scanned_count += 1

        if result.phishing_probability > settings.phishing_threshold:
            phishing_count += 1
            if service is not None:
                try:
                    run_with_retry(
                        logger,
                        lambda: mark_as_phishing(
                            service=service,
                            message_id=email.message_id,
                            label_name=settings.gmail_label_name,
                        ),
                        retries=3,
                    )
                except Exception as exc:
                    label_failure_count += 1
                    logger.error("label_apply_failed message_id=%s error=%s", email.message_id, exc)

        logger.info(
            "scan_result message_id=%s probability=%.4f label=%s risk=%s",
            email.message_id,
            result.phishing_probability,
            result.label,
            result.risk_level,
        )

    notes = (
        f"emails_fetched={len(emails)} "
        f"emails_scanned={scanned_count} "
        f"phishing_detected={phishing_count} "
        f"label_failures={label_failure_count}"
    )
    db.finish_scan_run(
        run_id=run_id,
        scanned_count=scanned_count,
        phishing_count=phishing_count,
        notes=notes,
    )
    return scanned_count, phishing_count


def main() -> None:
    args = parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = get_logger("phishguard.main")

    db = Database(settings.database_url)
    predictor = PhishingPredictor(
        model_dir=settings.model_dir,
        mode="auto",
        threshold=settings.phishing_threshold,
        prefer_gpu=True,
    )
    pipeline = PhishGuardPipeline(
        predictor=predictor,
        threshold=settings.phishing_threshold,
        expand_short_urls=False,
    )
    max_results = args.max_results or settings.max_results_per_scan
    seen_ids: set[str] = set()

    try:
        service = get_gmail_service(
            credentials_path=settings.gmail_credentials_path,
            token_path=settings.gmail_token_path,
        )
        logger.info("gmail_service=connected")
    except Exception as exc:
        service = None
        logger.warning("gmail_service=disabled reason=%s", exc)

    while True:
        try:
            scanned, phishing = scan_once(
                db=db,
                pipeline=pipeline,
                logger=logger,
                settings=settings,
                service=service,
                max_results=max_results,
                seen_ids=seen_ids,
                sample_path=args.offline_samples,
            )
            logger.info("scan_cycle_done scanned=%s phishing=%s", scanned, phishing)
        except KeyboardInterrupt:
            logger.info("shutdown=keyboard_interrupt")
            break
        except Exception:
            logger.exception("scan_cycle_failed")
            if args.once:
                raise

        if args.once:
            break
        time.sleep(settings.scan_interval_minutes * 60)


if __name__ == "__main__":
    main()
