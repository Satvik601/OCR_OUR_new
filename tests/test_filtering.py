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


def test_heavy_overlap_merges_light_grazing_does_not(config):
    """Heavily overlapping boxes are fragments of one region and merge; boxes
    that merely graze each other (< min_overlap_merge of the smaller) stay apart."""
    a = (100, 100, 200, 100)
    b = (200, 100, 200, 100)  # 50% mutual overlap -> fragments -> merged union
    kept = filter_regions([a, b], PAGE, config)
    assert kept == [(100, 100, 300, 100)]

    # taller-than-line blocks (columns) that merely graze: neither the overlap
    # rule (2.5% < threshold) nor the line-gap rule (too tall) may merge them
    c = (100, 300, 200, 150)
    d = (295, 300, 200, 150)
    kept = filter_regions([c, d], PAGE, config)
    assert c in kept and d in kept


def test_overlapping_fragments_stitched(config):
    """Boxes overlapping by a meaningful fraction merge into one region."""
    a = (100, 100, 200, 60)
    b = (260, 105, 200, 60)  # overlaps a by 40px-wide strip (~33% of a line height)
    kept = filter_regions([a, b], PAGE, config)
    assert len(kept) == 1
    x, y, w, h = kept[0]
    assert x == 100 and x + w == 460


def test_same_line_word_fragments_stitched(config):
    """Adjacent same-height boxes on one text line merge (word fragments)."""
    words = [(100, 100, 90, 40), (210, 102, 110, 38), (340, 100, 80, 40)]
    kept = filter_regions(words, PAGE, config)
    assert len(kept) == 1


def test_columns_never_stitched(config):
    """Tall body-column blocks with a gutter gap must NOT merge."""
    col1 = (40, 100, 180, 300)
    col2 = (240, 100, 180, 300)  # 20px gutter
    kept = filter_regions([col1, col2], PAGE, config)
    assert len(kept) == 2


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
