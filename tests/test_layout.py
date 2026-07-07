"""Unit tests for stage 2 (layout detection) on synthetic fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from newspaper_ocr.boxes import match_boxes
from newspaper_ocr.config import load_config
from newspaper_ocr.layout import detect_regions
from newspaper_ocr.preprocessing import preprocess

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def config():
    return load_config()


@pytest.fixture(scope="module")
def simple_binary(config):
    img = cv2.imread(str(FIXTURES / "synthetic_simple.png"), cv2.IMREAD_COLOR)
    assert img is not None
    return preprocess(img, config)


@pytest.fixture(scope="module")
def layout_gt():
    data = json.loads((FIXTURES / "synthetic_layout.json").read_text(encoding="utf-8"))
    return [tuple(b["bbox"]) for b in data["blocks"]]


def test_returns_boxes_within_image(simple_binary, config):
    boxes = detect_regions(simple_binary, config)
    assert boxes, "no regions detected on the clean synthetic page"
    height, width = simple_binary.shape
    for x, y, w, h in boxes:
        assert w > 0 and h > 0
        assert 0 <= x and 0 <= y
        assert x + w <= width and y + h <= height


def test_all_synthetic_blocks_found(simple_binary, config, layout_gt):
    """Every known block (headline, 2 columns, caption) matched at IoU >= 0.5."""
    boxes = detect_regions(simple_binary, config)
    matches = match_boxes(boxes, layout_gt, iou_threshold=0.5)
    assert len(matches) == len(layout_gt), (
        f"matched {len(matches)}/{len(layout_gt)} blocks; detected boxes: {boxes}"
    )


def test_no_excessive_fragmentation(simple_binary, config, layout_gt):
    """The clean page has 4 blocks; detection shouldn't explode into dozens."""
    boxes = detect_regions(simple_binary, config)
    assert len(boxes) <= 3 * len(layout_gt)


def test_blank_page_yields_no_regions(config):
    blank = np.zeros((500, 400), np.uint8)
    assert detect_regions(blank, config) == []


def test_rejects_bad_input(config):
    with pytest.raises(ValueError, match="binary image"):
        detect_regions(np.zeros((100, 100), np.float32), config)
    with pytest.raises(ValueError, match="binary image"):
        detect_regions(np.zeros((0, 300), np.uint8), config)
    with pytest.raises(ValueError, match="binary image"):
        detect_regions(np.zeros((100, 100, 3), np.uint8), config)


@pytest.mark.parametrize(
    ("key", "bad_value", "match"),
    [
        ("horizontal_dilate_kernel", [0, 1], "horizontal_dilate_kernel"),
        ("vertical_dilate_kernel", [1], "vertical_dilate_kernel"),
        ("closing_kernel", "big", "closing_kernel"),
        ("closing_iterations", 0, "closing_iterations"),
    ],
)
def test_bad_config_values_fail_loudly(key, bad_value, match):
    import copy

    from newspaper_ocr.config import Config

    data = copy.deepcopy(load_config().as_dict())
    data["layout"][key] = bad_value
    with pytest.raises(ValueError, match=match):
        detect_regions(np.zeros((100, 100), np.uint8), Config(data))


def test_display_pass_bad_height_fails_loudly():
    import copy

    from newspaper_ocr.config import Config

    data = copy.deepcopy(load_config().as_dict())
    data["layout"]["display_pass"]["min_component_height"] = 0
    with pytest.raises(ValueError, match="min_component_height"):
        detect_regions(np.full((100, 100), 255, np.uint8), Config(data))


def test_columns_not_merged(simple_binary, config, layout_gt):
    """The two body columns must come out as separate regions, not one wide box."""
    boxes = detect_regions(simple_binary, config)
    col1, col2 = layout_gt[1], layout_gt[2]
    matches = match_boxes(boxes, [col1, col2], iou_threshold=0.5)
    assert len(matches) == 2, f"columns merged or missed; detected: {boxes}"
