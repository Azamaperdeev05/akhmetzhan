# PhishGuard диплом жобасы: 5 апталық 5-фаза жоспар

## Summary
- Мақсат: 5 аптада қорғалатын, end-to-end жұмыс істейтін PhishGuard MVP жасау және диплом материалдарын дайындау.
- Бекітілген таңдаулар: 1-фаза фокусы `Дерек+модель`, жұмыс форматы `баланс`, үйрету ортасы `жергілікті GPU`.
- Ағымдағы күй: репода тек README бар, сондықтан 1-фазада қаңқаны нөлден құрамыз.
- Иә, 1-фазадан бастаймыз.

## Key Changes
1. **Фаза 1 (1-апта): Дерек және модель базасы**
- README-дегі құрылыммен жоба қаңқасын жасау (`data/`, `model/`, `analyzer/`, `gmail/`, `dashboard/`, `utils/`, `tests/`).
- Kaggle деректерін жинау, бірыңғай форматқа келтіру, `train/val/test = 80/10/10`.
- `data/preprocess.py`, `model/train.py`, `model/evaluate.py` арқылы baseline + BERT v1 нәтижесін алу.
- Шығу критерийі: тестте кемінде `F1 >= 0.90` және reproducible train/eval run.

2. **Фаза 2 (2-апта): Analyzer pipeline + DB**
- `preprocessor`, `url_checker`, `header_analyzer`, `pipeline` модульдерін біріктіру.
- SQLite схема: `emails`, `scan_results`, `url_findings`, `scan_runs`.
- Негізгі интерфейс: `scan_email(email_obj) -> ScanResult`.
- Шығу критерийі: sample хаттар толық анализден өтіп, DB-ға жазылады.

3. **Фаза 3 (3-апта): Gmail интеграциясы**
- OAuth2, inbox fetch, dedup (`message_id`), polling (`SCAN_INTERVAL_MINUTES`).
- Ереже: `phishing_probability > PHISHING_THRESHOLD` болса `PHISHING` label.
- Retry/backoff және structured logging.
- Шығу критерийі: нақты inbox-та кемінде 20 хат өңделеді.

4. **Фаза 4 (4-апта): Dashboard және E2E**
- Flask беттері: `index`, `emails`, `stats`, 30 күндік график, risk деңгейі.
- `.env` параметрлерін (threshold/interval) MVP деңгейінде басқару.
- Gmail -> Analyzer -> DB -> Dashboard толық ағын.
- Шығу критерийі: live демода фишинг хат label қойылып, dashboard-та көрінеді.

5. **Фаза 5 (5-апта): Сапа және қорғау**
- Unit, integration, smoke e2e тесттер.
- Қорытынды метрикалар: Accuracy, Precision, Recall, F1, AUC, latency.
- Диплом артефакттары: диаграмма, эксперимент кестелері, демо сценарий.
- Шығу критерийі: қорғауға дайын demo + есептік материал.

## Public Interfaces
- `ScanResult` өрістері: `message_id`, `received_at`, `phishing_probability`, `label`, `risk_level`, `reasons`, `urls`, `spf_status`, `dkim_status`.
- `.env` контракті: `GMAIL_*`, `DATABASE_URL`, `SCAN_INTERVAL_MINUTES`, `PHISHING_THRESHOLD`, `FLASK_SECRET_KEY`.
- Негізгі run сценарийлері: `python model/train.py`, `python model/evaluate.py`, `python main.py`, `python dashboard/app.py`.

## Test Plan
- Модель: threshold sweep, confusion matrix, imbalance тексерісі.
- Analyzer: HTML-only, empty body, shortened URL, SPF/DKIM fail.
- Gmail: token expiration, rate limit, duplicate fetch, label apply failure.
- E2E: заңды хат, айқын фишинг, шекаралық confidence, URL-only, spoofed header сценарийлері.

## Assumptions
- Жергілікті GPU орта PyTorch CUDA-мен дайын.
- 5 аптада мақсат production емес, қорғалатын MVP.
- Әдепкі шек мәні: `PHISHING_THRESHOLD=0.75`.
- Егер 1-апта соңында BERT әлсіз болса, кешіктірмей RoBERTa-base fallback қосылады.
