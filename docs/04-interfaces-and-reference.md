# Interfaces and Reference

## Core interface

## `scan_email(email_obj) -> ScanResult`

Орны: `analyzer/pipeline.py`

`EmailMessage` кірісі:

- `message_id: str`
- `thread_id: str | None`
- `subject: str`
- `body: str`
- `sender: str`
- `sender_domain: str`
- `received_at: datetime`
- `headers: dict[str, str]`
- `urls: list[str]`

`ScanResult` шығысы:

- `message_id`
- `received_at`
- `phishing_probability`
- `label` (`PHISHING` немесе `LEGITIMATE`)
- `risk_level` (`LOW`, `MEDIUM`, `HIGH`)
- `reasons: list[str]`
- `urls: list[URLFinding]`
- `spf_status`
- `dkim_status`
- `scanned_at`

## Decision rules

- Label:
  - `PHISHING`, егер `phishing_probability > PHISHING_THRESHOLD`
  - әйтпесе `LEGITIMATE`
- Risk level:
  - `HIGH`, егер жоғары ықтималдық немесе бірнеше suspicious URL немесе SPF+DKIM fail
  - `MEDIUM`, егер threshold маңында немесе 1 suspicious URL
  - `LOW`, қалғаны

## Environment contract (`.env`)

Негізгі айнымалылар:

- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REDIRECT_URI`
- `GMAIL_CREDENTIALS_PATH`
- `GMAIL_TOKEN_PATH`
- `GMAIL_QUERY`
- `GMAIL_LABEL_NAME`
- `DATABASE_URL`
- `SCAN_INTERVAL_MINUTES`
- `MAX_RESULTS_PER_SCAN`
- `PHISHING_THRESHOLD`
- `SCAN_TIMEOUT_SECONDS`
- `FLASK_SECRET_KEY`
- `LOG_LEVEL`
- `PROCESSED_DATA_DIR`
- `MODEL_DIR`

## CLI interfaces

- Data preprocess:
  - `python data/preprocess.py`
  - optional: `--phishing-path`, `--legitimate-path`, `--output-dir`, `--seed`
- Training:
  - `python model/train.py --mode baseline|bert|both`
- Evaluation:
  - `python model/evaluate.py --mode auto|baseline|bert`
- Scanner:
  - `python main.py [--once] [--max-results N] [--offline-samples FILE]`
- Dashboard:
  - `python dashboard/app.py`

## HTTP interfaces (Dashboard)

- `GET /`  
  Overview + recent scans.
- `GET /emails?page=N`  
  Paginated scan list.
- `GET /stats`  
  30 күндік визуал статистика.
- `GET /api/stats`  
  JSON summary + daily stats.

## Database schema summary

- `emails`
  - message metadata + sender + preview + headers
- `scan_runs`
  - scan cycle lifecycle (`started_at`, `finished_at`, counts)
- `scan_results`
  - per-email classification output
- `url_findings`
  - per-URL suspicious findings

