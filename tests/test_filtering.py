"""Unit tests for stage 3 (filtering)."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import pytest

from newspaper_ocr.boxes import match_boxes
from newspaper_ocr.config import load_config
from newspaper_ocr.filtering import filter_regions
from newspaper_ocr.layout import detect_regions
from newspaper_ocr.preprocessing import preprocess

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PAGE = (1000, 800)  # (height, width)


@pytest.fixture(scope="module")
def config():
    return load_config()


def test_empty_input(config):
    assert filter_regions([], PAGE, config) == []


def test_small_noise_boxes_dropped(config):
    boxes = [(10, 10, 5, 5), (50, 50, 300, 200)]  # 25 px^2 vs 60000 px^2
    kept = filter_regions(boxes, PAGE, config)
    assert (50, 50, 300, 200) in kept
    assert (10, 10, 5, 5) not in kept


def test_page_sized_box_dropped(config):
    """A box covering ~the whole page is a page-frame artifact, not an article."""
    boxes = [(2, 2, 796, 996), (50, 50, 300, 200)]
    kept = filter_regions(boxes, PAGE, config)
    assert (2, 2, 796, 996) not in kept
    assert (50, 50, 300, 200) in kept


def test_nested_box_dropped_outer_kept(config):
    outer = (100, 100, 400, 300)
    inner = (150, 150, 100, 50)  # fully inside outer
    kept = filter_regions([inner, outer], PAGE, config)
    assert outer in kept
    assert inner not in kept


def test_duplicate_boxes_deduped(config):
    box = (100, 100, 200, 150)
    kept = filter_regions([box, box, box], PAGE, config)
    assert kept.count(box) == 1


def test_disjoint_boxes_all_kept(config):
    boxes = [(10, 10, 100, 100), (300, 10, 100, 100), (10, 300, 100, 100)]
    kept = filter_regions(boxes, PAGE, config)
    assert sorted(kept) == sorted(boxes)


def test_partial_overlap_not_deduped(config):
    """Half-overlapping boxes are distinct regions, not nested duplicates."""
    a = (100, 100, 200, 100)
    b = (200, 100, 200, 100)
    kept = filter_regions([a, b], PAGE, config)
    assert a in kept and b in kept


def test_synthetic_blocks_survive_filtering(config):
    """End-to-end through stages 1-3 on the clean synthetic page: all 4 ground-truth
    blocks stay matched, and filtering never increases the box count."""
    img = cv2.imread(str(FIXTURES / "synthetic_simple.png"), cv2.IMREAD_COLOR)
    layout_gt = json.loads((FIXTURES / "synthetic_layout.json").read_text(encoding="utf-8"))
    gt_boxes = [tuple(b["bbox"]) for b in layout_gt["blocks"]]

    binary = preprocess(img, config)
    detected = detect_regions(binary, config)
    kept = filter_regions(detected, binary.shape, config)

    assert len(kept) <= len(detected)
    matches = match_boxes(kept, gt_boxes, iou_threshold=0.5)
    assert len(matches) == len(gt_boxes), f"lost blocks after filtering; kept={kept}"
