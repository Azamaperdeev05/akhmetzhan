# Troubleshooting

## 1) `ModuleNotFoundError` (script-ті direct іске қосқанда)

Белгі:

- `No module named 'analyzer'` немесе `No module named 'model'`

Себеп:

- Python path project root-қа қосылмаған.

Статус:

- Кодта bootstrap қосылған (`sys.path` insert), direct run қолдау бар.

## 2) Gmail қосылмайды (`credentials.json` табылмады)

Белгі:

- `Gmail credentials file not found`

Шешім:

1. Google Cloud Console-де OAuth client жасаңыз.
2. `credentials.json` файлын project root-қа қойыңыз.
3. `.env` ішіндегі `GMAIL_CREDENTIALS_PATH` дұрыс екенін тексеріңіз.

## 3) `transformers` версиясымен қате

Белгі:

- `TrainingArguments ... unexpected keyword ...`
- `Trainer ... unexpected keyword tokenizer`

Статус:

- `model/train.py` v4/v5 API айырмашылығына адаптацияланған.

## 4) `main.py` жұмыс істейді, бірақ phishing саны 0

Себеп:

- Threshold жоғары болуы мүмкін.
- Model әлсіз trained болуы мүмкін.
- Demo dataset тым кішкентай болуы мүмкін.

Шешім:

1. `.env` ішіндегі `PHISHING_THRESHOLD` мәнін тексеріңіз.
2. Kaggle толық dataset-пен қайта train жасаңыз.
3. `model/evaluate.py` threshold sweep нәтижесін қолданыңыз.

## 5) Dashboard бос

Себеп:

- DB-да scan жазбалары жоқ.

Шешім:

1. `python main.py --once` орындаңыз.
2. `DATABASE_URL` бірдей файлға қарап тұрғанын тексеріңіз.

## 6) GPU қолданылмайды

Тексеру:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

Егер `False` болса:

- NVIDIA driver/CUDA/PyTorch сәйкестігін тексеріңіз.
- Әзірге CPU режимінде іске қосуға болады.

