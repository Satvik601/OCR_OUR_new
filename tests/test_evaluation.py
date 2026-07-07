"""Unit tests for stage 6 (evaluation) using constructed documents — no OCR."""

from __future__ import annotations

import pytest

from newspaper_ocr.evaluation import evaluate


def _gt() -> dict:
    return {
        "article_count": 2,
        "regions": [
            {
                "id": "gt1",
                "bbox": {"x": 0, "y": 0, "w": 200, "h": 100},
                "region_type": "headline",
                "article_id": "a1",
                "text": "big headline news",
                "text_complete": True,
            },
            {
                "id": "gt2",
                "bbox": {"x": 0, "y": 200, "w": 200, "h": 300},
                "region_type": "body",
                "article_id": "a1",
                "text": "one two three four five six seven eight",
                "text_complete": True,
            },
            {
                "id": "gt3",
                "bbox": {"x": 300, "y": 0, "w": 200, "h": 500},
                "region_type": "body",
                "article_id": "a2",
                "text": "second article body text here",
                "text_complete": True,
            },
        ],
    }


def _doc(regions: list[dict]) -> dict:
    return {"regions": regions}


def _region(x, y, w, h, text=""):
    return {"bbox": {"x": x, "y": y, "w": w, "h": h}, "text": text}


def test_perfect_detection():
    doc = _doc(
        [
            _region(0, 0, 200, 100, "big headline news"),
            _region(0, 200, 200, 300, "one two three four five six seven eight"),
            _region(300, 0, 200, 500, "second article body text here"),
        ]
    )
    m = evaluate(doc, _gt())
    assert m["region_precision"] == pytest.approx(1.0)
    assert m["region_recall"] == pytest.approx(1.0)
    assert m["word_accuracy"] == pytest.approx(1.0)
    assert m["articles_found"] == 2
    assert m["fragmentation_rate"] == pytest.approx(1.0)


def test_missed_region_and_false_positive():
    doc = _doc(
        [
            _region(0, 0, 200, 100, "big headline news"),
            _region(600, 600, 50, 50, "noise"),  # matches nothing
        ]
    )
    m = evaluate(doc, _gt())
    assert m["region_precision"] == pytest.approx(1 / 2)
    assert m["region_recall"] == pytest.approx(1 / 3)
    assert m["num_matched"] == 1


def test_fragmentation_counted():
    # gt3 covered by two half-boxes -> fragmentation for gt3 = 2
    doc = _doc(
        [
            _region(300, 0, 200, 250, "second article body"),
            _region(300, 250, 200, 250, "text here"),
        ]
    )
    m = evaluate(doc, _gt())
    # overlaps at IoU>=0.1: gt3 sees 2 boxes; gt1/gt2 see 0 -> mean over GT with >=1 overlap
    assert m["fragmentation_rate"] == pytest.approx(2.0)


def test_word_accuracy_weighted_by_gt_length():
    doc = _doc(
        [
            _region(0, 0, 200, 100, "big headline news"),  # 3 words, perfect
            _region(0, 200, 200, 300, "one two wrong wrong wrong wrong wrong wrong"),  # 8 gt words, 2 right
        ]
    )
    m = evaluate(doc, _gt())
    expected = (1.0 * 3 + 0.25 * 8) / 11
    assert m["word_accuracy"] == pytest.approx(expected)


def test_empty_document():
    m = evaluate(_doc([]), _gt())
    assert m["region_precision"] == 0.0
    assert m["region_recall"] == 0.0
    assert m["num_detected"] == 0
    assert m["articles_found"] == 0
