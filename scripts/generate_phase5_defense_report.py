from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGETS = {
    "accuracy": 0.97,
    "precision": 0.96,
    "recall": 0.97,
    "f1": 0.965,
    "auc_roc": 0.99,
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _best_threshold(sweep: list[dict[str, Any]]) -> dict[str, Any]:
    if not sweep:
        return {}
    return max(sweep, key=lambda row: float(row.get("f1", 0.0)))


def _metric_status(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, target in TARGETS.items():
        actual = float(metrics.get(name, 0.0))
        rows.append(
            {
                "metric": name,
                "actual": actual,
                "target": target,
                "passed": actual >= target,
            }
        )
    latency = float(metrics.get("latency_per_email_ms", 0.0))
    rows.append(
        {
            "metric": "latency_per_email_ms",
            "actual": latency,
            "target": 500.0,
            "passed": latency <= 500.0 if latency > 0 else False,
        }
    )
    return rows


def _render_markdown(
    evaluation: dict[str, Any],
    quality_gate: dict[str, Any],
    metric_rows: list[dict[str, Any]],
    best_threshold: dict[str, Any],
) -> str:
    mode = evaluation.get("mode", "unknown")
    metrics = evaluation.get("metrics", {})
    gate_ok = bool(quality_gate.get("overall_passed", False))
    checks = quality_gate.get("checks", [])
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    lines.append("# Phase 5 Quality and Defense Report")
    lines.append("")
    lines.append(f"Generated at: {generated_at}")
    lines.append("")
    lines.append("## 1. Executive Summary")
    lines.append(f"- Evaluation mode: `{mode}`")
    lines.append(f"- Quality gate passed: `{gate_ok}`")
    lines.append(f"- Accuracy: `{metrics.get('accuracy', 0):.4f}`")
    lines.append(f"- Precision: `{metrics.get('precision', 0):.4f}`")
    lines.append(f"- Recall: `{metrics.get('recall', 0):.4f}`")
    lines.append(f"- F1: `{metrics.get('f1', 0):.4f}`")
    lines.append(f"- AUC-ROC: `{metrics.get('auc_roc', 0):.4f}`")
    lines.append(f"- Latency/email (ms): `{metrics.get('latency_per_email_ms', 0):.2f}`")
    lines.append("")
    lines.append("## 2. Target vs Actual")
    lines.append("")
    lines.append("| Metric | Actual | Target | Status |")
    lines.append("|---|---:|---:|---|")
    for row in metric_rows:
        status = "PASS" if row["passed"] else "FAIL"
        lines.append(f"| {row['metric']} | {row['actual']:.4f} | {row['target']:.4f} | {status} |")
    lines.append("")
    lines.append("## 3. Threshold Analysis")
    if best_threshold:
        lines.append(
            "- Best threshold by F1: "
            f"`{best_threshold.get('threshold')}` "
            f"(precision={best_threshold.get('precision')}, "
            f"recall={best_threshold.get('recall')}, "
            f"f1={best_threshold.get('f1')})"
        )
    else:
        lines.append("- Threshold sweep data not found.")
    lines.append("")
    lines.append("## 4. Quality Gate Checks")
    for check in checks:
        lines.append(
            f"- {check.get('name')}: "
            f"{'PASS' if check.get('passed') else 'FAIL'} "
            f"({check.get('command', '')})"
        )
    lines.append("")
    lines.append("## 5. Defense Demo Scenario")
    lines.append("1. `python scripts/run_phase2_sample.py --predictor-mode heuristic`")
    lines.append("2. `python scripts/run_phase4_e2e_demo.py --db-url sqlite:///phase4_demo.db`")
    lines.append("3. `python dashboard/app.py` and open `http://localhost:5000`")
    lines.append("4. Show `/`, `/emails`, `/stats`, `/settings`")
    lines.append("5. (Optional) `python scripts/run_phase3_gmail_validation.py --target-count 20`")
    lines.append("")
    lines.append("## 6. Notes")
    lines.append("- Current metrics can be based on demo-size datasets.")
    lines.append("- For diploma final defense, rerun with full Kaggle datasets and regenerate this report.")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Phase 5 defense report from evaluation artifacts.")
    parser.add_argument(
        "--evaluation-report",
        type=Path,
        default=Path("model/saved_model/evaluation_report.json"),
    )
    parser.add_argument(
        "--quality-gate-report",
        type=Path,
        default=Path("reports/phase5_quality_gate.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/09-phase5-quality-and-defense.md"),
    )
    parser.add_argument(
        "--output-summary-json",
        type=Path,
        default=Path("reports/phase5_defense_summary.json"),
    )
    parser.add_argument(
        "--output-metrics-csv",
        type=Path,
        default=Path("reports/phase5_metrics_table.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluation = _load_json(args.evaluation_report)
    quality_gate = _load_json(args.quality_gate_report)
    metrics = evaluation.get("metrics", {}) if isinstance(evaluation, dict) else {}
    sweep = evaluation.get("threshold_sweep", []) if isinstance(evaluation, dict) else []

    best = _best_threshold(sweep if isinstance(sweep, list) else [])
    metric_rows = _metric_status(metrics if isinstance(metrics, dict) else {})

    md = _render_markdown(
        evaluation=evaluation if isinstance(evaluation, dict) else {},
        quality_gate=quality_gate if isinstance(quality_gate, dict) else {},
        metric_rows=metric_rows,
        best_threshold=best,
    )

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(md, encoding="utf-8")

    args.output_metrics_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_metrics_csv.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["metric", "actual", "target", "passed"])
        writer.writeheader()
        for row in metric_rows:
            writer.writerow(row)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_mode": evaluation.get("mode", "unknown") if isinstance(evaluation, dict) else "unknown",
        "quality_gate_passed": bool(quality_gate.get("overall_passed", False))
        if isinstance(quality_gate, dict)
        else False,
        "best_threshold": best,
        "metrics": metrics,
        "targets": TARGETS,
    }
    args.output_summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()

