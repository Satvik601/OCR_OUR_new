"""Unit tests for stage 4 (per-region OCR). Requires a Tesseract install (the
project's environment contract — see README) but no fixture files."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from newspaper_ocr.config import load_config
from newspaper_ocr.ocr import ocr_region
from newspaper_ocr.text_metrics import word_accuracy


@pytest.fixture(scope="module")
def config():
    return load_config()


def _render(text: str, scale: float = 1.2, pad: int = 24) -> np.ndarray:
    """White BGR crop with black text, like a crop from an original page."""
    (w, h), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
    img = np.full((h + base + 2 * pad, w + 2 * pad, 3), 255, np.uint8)
    cv2.putText(
        img, text, (pad, pad + h), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 2, cv2.LINE_AA
    )
    return img


def test_reads_clean_text(config):
    result = ocr_region(_render("The quick brown fox jumps"), config)
    assert word_accuracy("The quick brown fox jumps", result.text) >= 0.6, result.text
    assert result.confidence > 30


def test_blank_crop_yields_empty(config):
    blank = np.full((60, 200, 3), 255, np.uint8)
    result = ocr_region(blank, config)
    assert result.text == ""


def test_noise_crop_filtered_out(config):
    rng = np.random.default_rng(7)
    noise = rng.integers(0, 256, (80, 200, 3)).astype(np.uint8)
    result = ocr_region(noise, config)
    # garbage filter: nothing confident/long enough should survive pure noise
    assert len(result.text) < 15


def test_accepts_grayscale_crop(config):
    gray = cv2.cvtColor(_render("hello world"), cv2.COLOR_BGR2GRAY)
    result = ocr_region(gray, config)
    assert word_accuracy("hello world", result.text) >= 0.5, result.text


def test_min_text_chars_zero_does_not_crash(tmp_path):
    """Regression: min_text_chars=0 + a wordless crop used to divide by zero."""
    import copy

    from newspaper_ocr.config import Config

    data = copy.deepcopy(load_config().as_dict())
    data["ocr"]["min_text_chars"] = 0
    data["ocr"]["cache_dir"] = str(tmp_path)
    blank = np.full((60, 200, 3), 255, np.uint8)
    result = ocr_region(blank, Config(data))
    assert result.text == ""
    assert result.confidence == -1.0


def test_corrupt_cache_entry_is_a_miss(config, tmp_path):
    """Regression: a truncated cache file must trigger recompute, not a crash."""
    import copy

    from newspaper_ocr.config import Config

    data = copy.deepcopy(config.as_dict())
    data["ocr"]["cache_dir"] = str(tmp_path)
    cfg = Config(data)
    crop = _render("resilient")
    first = ocr_region(crop, cfg)  # populates the cache
    cache_file = next(tmp_path.glob("*.json"))
    cache_file.write_text('{"text": "trunc', encoding="utf-8")
    again = ocr_region(crop, cfg)
    assert again == first


@pytest.mark.parametrize(
    ("key", "bad_value", "match"),
    [
        ("psm", 99, "psm"),
        ("psm", "6 --oem 1", "psm"),
        ("oem", -1, "oem"),
        ("lang", "eng; rm -rf", "lang"),
    ],
)
def test_bad_tesseract_params_fail_loudly(key, bad_value, match, tmp_path):
    import copy

    from newspaper_ocr.config import Config

    data = copy.deepcopy(load_config().as_dict())
    data["ocr"][key] = bad_value
    data["ocr"]["cache_dir"] = str(tmp_path)
    with pytest.raises(ValueError, match=match):
        ocr_region(_render("x y z"), Config(data))


def test_cache_hit_skips_tesseract(config, monkeypatch, tmp_path):
    """Second call with identical crop+params must come from the content-hash cache."""
    import copy

    import newspaper_ocr.ocr as ocr_mod
    from newspaper_ocr.config import Config

    data = copy.deepcopy(config.as_dict())
    data["ocr"]["cache_dir"] = str(tmp_path)
    cfg = Config(data)

    crop = _render("cache me")
    calls = {"n": 0}
    real = ocr_mod.pytesseract.image_to_data

    def counting(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_data", counting)
    first = ocr_region(crop, cfg)
    second = ocr_region(crop, cfg)
    assert calls["n"] == 1, "second call should be served from cache"
    assert first == second
