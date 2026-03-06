# Phase 5 Quality and Defense Report

Generated at: 2026-03-06 05:29 UTC

## 1. Executive Summary
- Evaluation mode: `bert`
- Quality gate passed: `True`
- Accuracy: `0.3333`
- Precision: `0.3333`
- Recall: `1.0000`
- F1: `0.5000`
- AUC-ROC: `1.0000`
- Latency/email (ms): `76.26`

## 2. Target vs Actual

| Metric | Actual | Target | Status |
|---|---:|---:|---|
| accuracy | 0.3333 | 0.9700 | FAIL |
| precision | 0.3333 | 0.9600 | FAIL |
| recall | 1.0000 | 0.9700 | PASS |
| f1 | 0.5000 | 0.9650 | FAIL |
| auc_roc | 1.0000 | 0.9900 | PASS |
| latency_per_email_ms | 76.2555 | 500.0000 | PASS |

## 3. Threshold Analysis
- Best threshold by F1: `0.1` (precision=0.3333333333333333, recall=1.0, f1=0.5)

## 4. Quality Gate Checks
- pytest: PASS (C:\Users\Acer\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe -m pytest tests -q)
- phase2_smoke: PASS (C:\Users\Acer\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe scripts/run_phase2_sample.py --predictor-mode heuristic --db-url sqlite:///reports/phase2_quality_78b2f5a8.db)
- phase4_e2e: PASS (C:\Users\Acer\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe scripts/run_phase4_e2e_demo.py --db-url sqlite:///reports/phase4_quality_78b2f5a8.db)

## 5. Defense Demo Scenario
1. `python scripts/run_phase2_sample.py --predictor-mode heuristic`
2. `python scripts/run_phase4_e2e_demo.py --db-url sqlite:///phase4_demo.db`
3. `python dashboard/app.py` and open `http://localhost:5000`
4. Show `/`, `/emails`, `/stats`, `/settings`
5. (Optional) `python scripts/run_phase3_gmail_validation.py --target-count 20`

## 6. Notes
- Current metrics can be based on demo-size datasets.
- For diploma final defense, rerun with full Kaggle datasets and regenerate this report.
