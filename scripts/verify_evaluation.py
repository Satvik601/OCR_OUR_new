"""Phase 6 verification per PHASE_VERIFICATION_LOOP.md — run against the REAL page.

Pass criterion (loop table): the evaluation runs end-to-end on real_sample_page.jpg
and produces numeric metrics without errors. Metrics are also the project's headline
numbers — logged into TESTING.md when they change.

Runs the actual CLI to produce the document, then evaluates it against ground truth.
Saves evidence to debug_output/06_metrics_real.json. Exit 0 on pass, 1 on fail.

Usage: python scripts/verify_evaluation.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newspaper_ocr.evaluation import evaluate
from newspaper_ocr.run import main as run_cli

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
DEBUG = ROOT / "debug_output"


def main() -> int:
    DEBUG.mkdir(exist_ok=True)
    doc_path = DEBUG / "05_result_real.json"
    code = run_cli(
        ["--input", str(FIXTURES / "real_sample_page.jpg"), "--output", str(doc_path)]
    )
    if code != 0:
        print(f"CLI exited {code}\nRESULT: FAIL")
        return 1

    doc = json.loads(doc_path.read_text(encoding="utf-8"))
    gt = json.loads((FIXTURES / "real_sample_page_groundtruth.json").read_text(encoding="utf-8"))
    metrics = evaluate(doc, gt)

    out_path = DEBUG / "06_metrics_real.json"
    out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"evidence file : {out_path}")
    for key, value in metrics.items():
        print(f"  {key:20s} = {value:.3f}" if isinstance(value, float) else f"  {key:20s} = {value}")

    numeric_ok = all(
        isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v))
        for v in metrics.values()
    )
    print(f"\nRESULT: {'PASS' if numeric_ok else 'FAIL'}")
    return 0 if numeric_ok else 1


if __name__ == "__main__":
    sys.exit(main())
