# Setup and Runbook

## 1. Орнату

```bash
python -m pip install -r requirements.txt
```

## 2. Конфигурация

```bash
copy .env.example .env
```

`.env` ішінде кемінде:

- `DATABASE_URL=sqlite:///phishguard.db`
- `PHISHING_THRESHOLD=0.75`
- `SCAN_INTERVAL_MINUTES=5`
- `MODEL_DIR=model/saved_model`

Gmail real mode үшін:

- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REDIRECT_URI`
- `credentials.json` (project root)

## 3. Data Pipeline

```bash
python data/preprocess.py
```

Нәтиже:

- `data/processed/train.csv`
- `data/processed/val.csv`
- `data/processed/test.csv`

## 4. Model Training

## Baseline (жылдам)

```bash
python model/train.py --mode baseline
```

## BERT

```bash
python model/train.py --mode bert --epochs 4 --batch-size 16 --use-gpu
```

Қысқа smoke нұсқа:

```bash
python model/train.py --mode bert --epochs 1 --batch-size 4 --use-gpu
```

## 5. Model Evaluation

## Baseline

```bash
python model/evaluate.py --mode baseline
```

## BERT

```bash
python model/evaluate.py --mode bert --use-gpu
```

Нәтиже:

- `model/saved_model/evaluation_report.json`

## 6. Scanner іске қосу

## Бір цикл (ұсынылады)

```bash
python main.py --once
```

## Үздіксіз polling

```bash
python main.py
```

## Offline sample арқылы test

```bash
python main.py --once --offline-samples data/raw/sample_inbox.json
```

## 7. Dashboard іске қосу

```bash
python dashboard/app.py
```

Ашу: `http://localhost:5000`

## 8. Тесттер

```bash
python -m pytest tests -q
```

## 9. Phase 2 smoke (Analyzer + DB)

Sample хаттарды pipeline арқылы өткізіп, нәтижені SQLite-ке жазу:

```bash
python scripts/run_phase2_sample.py --predictor-mode heuristic
```

Қажет болса басқа DB:

```bash
python scripts/run_phase2_sample.py --db-url sqlite:///phase2_demo.db
```
