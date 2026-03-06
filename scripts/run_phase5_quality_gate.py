from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass
class CheckResult:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


def run_check(name: str, command: list[str], cwd: Path) -> CheckResult:
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        shell=False,
    )
    return CheckResult(
        name=name,
        command=command,
        returncode=proc.returncode,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
    )


def parse_pytest_summary(stdout: str) -> str:
    for line in reversed(stdout.splitlines()):
        if "passed" in line or "failed" in line:
            return line.strip()
    return "summary_not_found"


def parse_json_stdout(stdout: str) -> dict:
    if not stdout:
        return {}

    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    blob = stdout[start : end + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return {}


def build_payload(results: list[CheckResult], workspace: Path) -> dict:
    quality: dict[str, object] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace),
        "overall_passed": all(item.passed for item in results),
        "checks": [],
    }

    for item in results:
        entry: dict[str, object] = {
            "name": item.name,
            "passed": item.passed,
            "returncode": item.returncode,
            "command": " ".join(item.command),
        }

        if item.name == "pytest":
            entry["summary"] = parse_pytest_summary(item.stdout)
            m = re.search(r"(\d+)\s+passed", item.stdout)
            if m:
                entry["passed_count"] = int(m.group(1))

        if item.name in {"phase2_smoke", "phase4_e2e"}:
            entry["details"] = parse_json_stdout(item.stdout)

        if not item.passed:
            entry["stderr"] = item.stderr
            entry["stdout"] = item.stdout

        quality["checks"].append(entry)

    return quality


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 5 quality gate checks and export JSON report.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/phase5_quality_gate.json"),
        help="Output JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workspace = Path(__file__).resolve().parents[1]
    run_id = uuid4().hex[:8]
    phase2_db = f"sqlite:///reports/phase2_quality_{run_id}.db"
    phase4_db = f"sqlite:///reports/phase4_quality_{run_id}.db"

    checks = [
        ("pytest", [sys.executable, "-m", "pytest", "tests", "-q"]),
        (
            "phase2_smoke",
            [
                sys.executable,
                "scripts/run_phase2_sample.py",
                "--predictor-mode",
                "heuristic",
                "--db-url",
                phase2_db,
            ],
        ),
        (
            "phase4_e2e",
            [sys.executable, "scripts/run_phase4_e2e_demo.py", "--db-url", phase4_db],
        ),
    ]

    results: list[CheckResult] = []
    for name, command in checks:
        results.append(run_check(name=name, command=command, cwd=workspace))

    payload = build_payload(results, workspace)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=True))

    if not payload["overall_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
