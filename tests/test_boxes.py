"""Unit tests for the bounding-box utilities."""

from __future__ import annotations

import pytest

from newspaper_ocr.boxes import containment, iou, match_boxes


def test_iou_identical():
    assert iou((10, 10, 100, 50), (10, 10, 100, 50)) == pytest.approx(1.0)


def test_iou_disjoint():
    assert iou((0, 0, 10, 10), (100, 100, 10, 10)) == 0.0


def test_iou_half_overlap():
    # second box shifted right by half its width
    assert iou((0, 0, 100, 100), (50, 0, 100, 100)) == pytest.approx(1 / 3)


def test_iou_degenerate_zero_area():
    assert iou((0, 0, 0, 0), (0, 0, 0, 0)) == 0.0


def test_containment_nested():
    assert containment((10, 10, 10, 10), (0, 0, 100, 100)) == pytest.approx(1.0)
    assert containment((0, 0, 100, 100), (10, 10, 10, 10)) == pytest.approx(0.01)


def test_match_boxes_one_to_one():
    gt = [(0, 0, 100, 100), (200, 0, 100, 100)]
    det = [(5, 5, 100, 100), (198, 0, 100, 100), (500, 500, 50, 50)]
    matches = match_boxes(det, gt, iou_threshold=0.5)
    assert len(matches) == 2
    matched_gt = {gi for _, gi, _ in matches}
    assert matched_gt == {0, 1}


def test_match_boxes_greedy_prefers_higher_iou():
    gt = [(0, 0, 100, 100)]
    det = [(40, 40, 100, 100), (2, 2, 100, 100)]  # second is the better match
    matches = match_boxes(det, gt, iou_threshold=0.1)
    assert len(matches) == 1
    assert matches[0][0] == 1  # detected index 1 won


def test_match_boxes_empty():
    assert match_boxes([], [(0, 0, 10, 10)], 0.5) == []
    assert match_boxes([(0, 0, 10, 10)], [], 0.5) == []
