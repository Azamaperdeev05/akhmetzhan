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

## Іске қосу

```bash
python -m pytest tests -q
```

Соңғы орындалған нәтиже:

- `13 passed`

## Метрика артефакттары

Орны: `model/saved_model/`

- `baseline_val_metrics.json`
- `bert_val_metrics.json`
- `train_summary.json`
- `evaluation_report.json`

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
