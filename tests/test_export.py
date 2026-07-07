"""Unit tests for stage 5 (structured JSON export)."""

from __future__ import annotations

import json

import pytest

from newspaper_ocr.export import build_document, validate_document


def _region(i: int = 1) -> dict:
    return {
        "bbox": {"x": 10 * i, "y": 20 * i, "w": 100, "h": 50},
        "text": f"region {i} text",
        "detection_confidence": 0.5,
        "ocr_confidence": 88.0,
        "region_type": "unclassified",
    }


def test_document_structure_and_ids():
    doc = build_document("page.jpg", (1220, 1490), [_region(1), _region(2)], dropped_count=7)
    assert doc["source_image"] == "page.jpg"
    assert doc["page_size"] == [1220, 1490]
    assert doc["pipeline_version"]
    assert "processed_at" in doc
    assert [r["id"] for r in doc["regions"]] == ["r001", "r002"]
    assert doc["stats"] == {"num_regions": 2, "num_regions_dropped_by_filtering": 7}


def test_document_is_json_serializable():
    doc = build_document("p.jpg", (100, 200), [_region()], dropped_count=0)
    parsed = json.loads(json.dumps(doc, ensure_ascii=False))
    assert parsed["regions"][0]["text"] == "region 1 text"


def test_validate_accepts_built_document():
    doc = build_document("p.jpg", (100, 200), [_region()], dropped_count=0)
    assert validate_document(doc) == []


def test_validate_flags_missing_and_malformed():
    doc = build_document("p.jpg", (100, 200), [_region(), _region(2)], dropped_count=0)
    del doc["regions"][0]["text"]
    doc["regions"][1]["bbox"]["w"] = -5
    doc["regions"][1]["region_type"] = "banner"  # not an allowed type
    errors = validate_document(doc)
    assert any("text" in e for e in errors)
    assert any("bbox" in e for e in errors)
    assert any("region_type" in e for e in errors)


def test_validate_flags_duplicate_ids():
    doc = build_document("p.jpg", (100, 200), [_region(), _region(2)], dropped_count=0)
    doc["regions"][1]["id"] = doc["regions"][0]["id"]
    assert any("duplicate" in e for e in validate_document(doc))


def test_empty_regions_document_is_valid():
    doc = build_document("p.jpg", (100, 200), [], dropped_count=3)
    assert validate_document(doc) == []
    assert doc["stats"]["num_regions"] == 0


def test_build_document_rejects_missing_region_fields():
    with pytest.raises(ValueError, match="ocr_confidence"):
        bad = _region()
        del bad["ocr_confidence"]
        build_document("p.jpg", (100, 200), [bad], dropped_count=0)
