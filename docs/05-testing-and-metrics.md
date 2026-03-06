# Testing and Metrics

## Тест жиынтығы

Орны: `tests/`

- `test_model.py`
  - dataset prepare
  - baseline train/eval smoke
- `test_analyzer.py`
  - HTML preprocess
  - suspicious URL detection
  - SPF/DKIM fail handling
  - pipeline output contract
- `test_gmail.py`
  - Gmail message parsing
  - dedup fetch behavior
  - label apply flow
- `test_phase2_pipeline_db.py`
  - analyzer->DB integration
  - scan_runs/scan_results write validation
- `test_phase3_gmail_runtime.py`
  - retry strategy behavior
  - pagination/dedup runtime behavior
  - label apply failure resilience
- `test_phase4_dashboard_e2e.py`
  - scan->db->dashboard E2E flow
  - settings update persistence

## Іске қосу

```bash
python -m pytest tests -q
```

Соңғы орындалған нәтиже:

- `15 passed`

## Метрика артефакттары

Орны: `model/saved_model/`

- `baseline_val_metrics.json`
- `bert_val_metrics.json`
- `train_summary.json`
- `evaluation_report.json`

Phase 5 quality/report артефакттары (орны: `reports/`):

- `phase5_quality_gate.json`
- `phase5_defense_summary.json`
- `phase5_metrics_table.csv`

Phase 3 real Gmail validation артефакты:

- `phase3_real_validation_2026-03-06.json` (`scanned_total=82`, `target_reached=true`)

## Қазіргі алынған мәндер туралы ескерту

- Ағымдағы run шағын demo split-пен жүргізілген.
- Сондықтан F1/accuracy мәндері production-ready қорытынды емес.
- Диплом қорытындысы үшін:
  1. Kaggle толық датасетпен қайта preprocess.
  2. Ұзақ training run (`epochs >= 3`, дұрыс train size).
  3. Final report метрикаларын жаңарту.

## Ұсынылатын acceptance checks

1. Unit tests green (`pytest`).
2. `main.py --once` scan cycle толық өтеді.
3. Dashboard барлық endpoint `200`.
4. `evaluation_report.json` ішінде threshold sweep бар.
