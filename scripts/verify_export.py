"""Phase 5 verification per PHASE_VERIFICATION_LOOP.md — run against the REAL page.

Pass criteria (loop table): the CLI's JSON output validates against the
ARCHITECTURE.md schema; every kept region that produced text is present with all
required fields; no malformed entries. Runs the actual CLI entry point so the
verified artifact is exactly what a user would get.

Saves evidence to debug_output/05_result_real.json (+ region overlay via --debug-dir).
Exit 0 on pass, 1 on fail.

Usage: python scripts/verify_export.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newspaper_ocr.export import validate_document
from newspaper_ocr.run import main as run_cli

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
DEBUG = ROOT / "debug_output"


def main() -> int:
    DEBUG.mkdir(exist_ok=True)
    out_path = DEBUG / "05_result_real.json"
    code = run_cli(
        [
            "--input", str(FIXTURES / "real_sample_page.jpg"),
            "--output", str(out_path),
            "--debug-dir", str(DEBUG),
        ]
    )
    if code != 0:
        print(f"CLI exited {code}\nRESULT: FAIL")
        return 1

    doc = json.loads(out_path.read_text(encoding="utf-8"))
    problems = validate_document(doc)

    n = doc["stats"]["num_regions"]
    total_chars = sum(len(r["text"]) for r in doc["regions"])
    empty_text = [r["id"] for r in doc["regions"] if not r["text"].strip()]

    print(f"evidence file  : {out_path}")
    print(f"regions        : {n} exported, {doc['stats']['num_regions_dropped_by_filtering']} candidates dropped")
    print(f"text extracted : {total_chars} characters")
    print(f"schema check   : {'PASS' if not problems else 'FAIL: ' + '; '.join(problems)}")
    print(f"non-empty text : {'PASS' if not empty_text else 'FAIL: ' + ', '.join(empty_text)}")

    ok = not problems and not empty_text and n > 0 and total_chars > 0
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
