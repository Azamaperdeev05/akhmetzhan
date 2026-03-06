# Diploma Deliverables Checklist

## 1. Код және жүйе

- [x] `main.py` арқылы scanner demo.
- [x] Dashboard (`/`, `/emails`, `/stats`) live көрсетілім.
- [ ] Gmail label қою (real OAuth mode, OAuth рұқсат толық аяқталуы керек).

## 2. ML нәтижелері

- [ ] Full dataset preprocess есебі (Kaggle толық run pending).
- [x] Final training config (seed, epochs, batch, lr).
- [x] Final metrics: Accuracy, Precision, Recall, F1, AUC, latency.
- [x] Confusion matrix және threshold selection rationale (threshold sweep арқылы).

## 3. Техникалық құжаттама

- [x] README актуал.
- [x] `docs/` толық және консистентті.
- [x] `.env.example` барлық керек айнымалылармен.

## 4. Диплом мәтініне керек материалдар

- [x] Архитектура диаграммасы.
- [x] DB schema сипаттамасы.
- [x] Pipeline блок-схемасы.
- [x] Тест кестелері және қорытынды талдау.

## 5. Қорғау сценарийі (ұсыныс)

1. Проблема + мақсат (1-2 мин).
2. Архитектура және модульдер (2-3 мин).
3. Live demo:
   - scanner run
   - phishing detection
   - dashboard refresh
4. Метрика және салыстыру (2-3 мин).
5. Қорытынды және future work (1 мин).
