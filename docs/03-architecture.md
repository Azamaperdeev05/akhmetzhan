# Architecture

## Жоғары деңгейлі схема

```mermaid
flowchart LR
    A["Gmail Inbox немесе Sample Inbox"] --> B["Fetch & Parse (gmail/fetch_emails.py)"]
    B --> C["Preprocess (analyzer/preprocessor.py)"]
    C --> D["Model Predict (model/predict.py)"]
    B --> E["Header Analyzer (SPF/DKIM)"]
    B --> F["URL Checker"]
    D --> G["Decision Engine (analyzer/pipeline.py)"]
    E --> G
    F --> G
    G --> H["Persist (utils/database.py)"]
    H --> I["Dashboard (dashboard/app.py)"]
    G --> J["Gmail Label Manager"]
```

## Негізгі компоненттер

- `main.py`
  - scanner orchestration
  - retry/backoff
  - periodic polling
- `model/`
  - baseline + bert training/eval
  - prediction backend auto-selection
- `analyzer/`
  - text cleaning
  - URL risk analysis
  - SPF/DKIM heuristics
  - risk-level aggregation
- `utils/database.py`
  - scan нәтижелерін сақтау
  - summary/stats query
- `dashboard/app.py`
  - статистика және scan history көрсету

## Runtime flow

1. `main.py` settings жүктейді (`utils/config.py`).
2. Gmail service ашылады (немесе sample fallback).
3. Әр email үшін `scan_email` орындалады.
4. `ScanResult` DB-ға жазылады.
5. `phishing_probability > threshold` болса Gmail label қойылады.
6. Dashboard DB-дан summary және history көрсетеді.

## Data flow және state

- Input state:
  - Gmail message payload немесе `data/raw/sample_inbox.json`
- Processing state:
  - preprocessed text
  - model probability
  - url/header findings
- Persistent state (SQLite):
  - email metadata
  - scan run metadata
  - per-scan classification
  - per-url findings

## Тәуелділік қабаттары

- Infra: `utils/config.py`, `utils/logger.py`, `utils/database.py`
- Domain: `utils/schemas.py`, `analyzer/*`
- Integration: `gmail/*`
- Application: `main.py`, `dashboard/app.py`
- ML tooling: `data/*`, `model/*`

