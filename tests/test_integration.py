"""End-to-end integration test: full pipeline through the CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

from newspaper_ocr.export import validate_document
from newspaper_ocr.run import main
from newspaper_ocr.text_metrics import tokenize

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_full_pipeline_on_synthetic_page(tmp_path):
    out = tmp_path / "result.json"
    code = main(["--input", str(FIXTURES / "synthetic_simple.png"), "--output", str(out)])
    assert code == 0
    doc = json.loads(out.read_text(encoding="utf-8"))

    assert validate_document(doc) == []
    assert doc["stats"]["num_regions"] >= 3, "expected headline + columns + caption"
    assert doc["page_size"] == [800, 1000]

    all_words = [w for r in doc["regions"] for w in tokenize(r["text"])]
    assert len(all_words) > 50, f"pipeline extracted too little text: {len(all_words)} words"
    assert "synthetic" in all_words, "headline text not recovered"


def test_cli_bad_input_path(tmp_path, capsys):
    code = main(["--input", str(tmp_path / "missing.png"), "--output", str(tmp_path / "o.json")])
    assert code == 2
    assert "could not read image" in capsys.readouterr().err
