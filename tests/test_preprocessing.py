"""Unit tests for stage 1 (preprocessing). Fixture images only — no OCR, no network."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from newspaper_ocr.config import load_config
from newspaper_ocr.preprocessing import preprocess

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def config():
    return load_config()


@pytest.fixture(scope="module")
def simple_bgr():
    img = cv2.imread(str(FIXTURES / "synthetic_simple.png"), cv2.IMREAD_COLOR)
    assert img is not None
    return img


@pytest.fixture(scope="module")
def noisy_bgr():
    img = cv2.imread(str(FIXTURES / "synthetic_noisy.png"), cv2.IMREAD_COLOR)
    assert img is not None
    return img


@pytest.fixture(scope="module")
def layout_gt():
    return json.loads((FIXTURES / "synthetic_layout.json").read_text(encoding="utf-8"))


def test_output_is_strict_binary(simple_bgr, config):
    out = preprocess(simple_bgr, config)
    assert out.dtype == np.uint8
    assert out.shape == simple_bgr.shape[:2]  # single channel, same size
    assert set(np.unique(out)).issubset({0, 255})


def test_accepts_grayscale_input(simple_bgr, config):
    gray = cv2.cvtColor(simple_bgr, cv2.COLOR_BGR2GRAY)
    out = preprocess(gray, config)
    assert out.shape == gray.shape
    assert set(np.unique(out)).issubset({0, 255})


def test_ink_is_white_convention(simple_bgr, config):
    """Text pages are mostly background, so with ink=255 the white fraction is small."""
    out = preprocess(simple_bgr, config)
    ink_fraction = (out == 255).mean()
    assert 0.001 < ink_fraction < 0.25


def test_text_blocks_survive(simple_bgr, config, layout_gt):
    """Every known text block still contains a meaningful amount of ink."""
    out = preprocess(simple_bgr, config)
    for block in layout_gt["blocks"]:
        x, y, w, h = block["bbox"]
        crop = out[y : y + h, x : x + w]
        ink_ratio = (crop == 255).mean()
        assert ink_ratio > 0.005, f"block {block['name']} lost its text (ink={ink_ratio:.4f})"


def test_text_blocks_survive_noise(noisy_bgr, config, layout_gt):
    """Same blocks on the degraded scan (boxes padded for the ~1.5 deg rotation)."""
    out = preprocess(noisy_bgr, config)
    pad = 20
    height, width = out.shape
    for block in layout_gt["blocks"]:
        x, y, w, h = block["bbox"]
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(width, x + w + pad), min(height, y + h + pad)
        crop = out[y0:y1, x0:x1]
        ink_ratio = (crop == 255).mean()
        assert ink_ratio > 0.003, f"block {block['name']} lost its text (ink={ink_ratio:.4f})"


def test_speckles_below_threshold_on_noisy(noisy_bgr, config):
    """Salt & pepper noise must be mostly gone after morphological opening."""
    out = preprocess(noisy_bgr, config)
    vcfg = config.verification.preprocessing
    n, _, stats, _ = cv2.connectedComponentsWithStats(out, connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA]  # skip background label 0
    speckles = int((areas < vcfg.min_speckle_area_px).sum())
    per_mpx = speckles / (out.size / 1_000_000)
    assert per_mpx < vcfg.max_speckle_per_mpx, f"{per_mpx:.0f} speckles/Mpx"


def test_border_artifacts_cleared(noisy_bgr, config):
    """The synthetic noisy page has black scanner bars on the left and bottom edges."""
    out = preprocess(noisy_bgr, config)
    assert (out[:, :6] == 255).mean() < 0.01, "left edge bar not cleared"
    assert (out[-8:, :] == 255).mean() < 0.01, "bottom edge bar not cleared"


def test_input_not_mutated(simple_bgr, config):
    before = simple_bgr.copy()
    preprocess(simple_bgr, config)
    assert np.array_equal(before, simple_bgr)


def test_accepts_hw1_single_channel(simple_bgr, config):
    gray3d = cv2.cvtColor(simple_bgr, cv2.COLOR_BGR2GRAY)[:, :, None]
    out = preprocess(gray3d, config)
    assert out.shape == gray3d.shape[:2]


def test_rejects_non_uint8(simple_bgr, config):
    with pytest.raises(ValueError, match="uint8"):
        preprocess(simple_bgr.astype(np.float32), config)


@pytest.mark.parametrize(
    ("key", "bad_value", "match"),
    [
        ("gaussian_kernel", 4, "gaussian_kernel"),
        ("gaussian_kernel", -3, "gaussian_kernel"),
        ("adaptive_block_size", 2, "adaptive_block_size"),
        ("morph_open_kernel", 0, "morph_open_kernel"),
    ],
)
def test_bad_config_values_fail_loudly(simple_bgr, key, bad_value, match):
    import copy

    from newspaper_ocr.config import Config

    data = copy.deepcopy(load_config().as_dict())
    data["preprocessing"][key] = bad_value
    with pytest.raises(ValueError, match=match):
        preprocess(simple_bgr, Config(data))
