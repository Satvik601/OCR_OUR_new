"""Stage 4 — per-region OCR.

Each region is cropped from the ORIGINAL (non-binarized) image, upscaled by
``ocr.upscale_factor`` with bicubic interpolation, then run through Tesseract
(PSM/OEM/lang from config; defaults: PSM 6 single uniform block, OEM 1 LSTM).
Post-OCR garbage filtering: words below ``ocr.min_word_confidence`` are dropped,
and results shorter than ``ocr.min_text_chars`` collapse to empty text.

Results are cached by content hash (SHA-256 of crop bytes + OCR parameters) in
``ocr.cache_dir`` so re-running the pipeline on unchanged pages doesn't re-invoke
Tesseract. Delete the cache directory to invalidate.

The backend is pluggable: any callable ``ocr_region(image_crop, config)
-> OcrResult`` can be swapped in (e.g. EasyOCR / PaddleOCR) and compared
under the same verification criteria.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytesseract

from .config import Config

_LANG_PATTERN = re.compile(r"[a-z_]{3,7}(\+[a-z_]{3,7})*")


@dataclass
class OcrResult:
    text: str
    confidence: float  # mean kept-word confidence, 0-100; -1.0 if no words kept


def _cache_key(image_crop: np.ndarray, ocfg: Config) -> str:
    hasher = hashlib.sha256()
    hasher.update(image_crop.tobytes())
    hasher.update(str(image_crop.shape).encode())
    params = (ocfg.psm, ocfg.oem, ocfg.lang, ocfg.upscale_factor,
              ocfg.min_word_confidence, ocfg.min_text_chars)
    hasher.update(repr(params).encode())
    return hasher.hexdigest()


def _validate_tesseract_params(ocfg: Config) -> None:
    """psm/oem/lang are interpolated into the Tesseract invocation — validate them
    eagerly so a config typo (or a hostile config value) fails clearly here rather
    than smuggling extra CLI flags into the subprocess or dying inside Tesseract."""
    if not isinstance(ocfg.psm, int) or isinstance(ocfg.psm, bool) or not 0 <= ocfg.psm <= 13:
        raise ValueError(f"ocr.psm must be an int in 0..13, got {ocfg.psm!r}")
    if not isinstance(ocfg.oem, int) or isinstance(ocfg.oem, bool) or not 0 <= ocfg.oem <= 3:
        raise ValueError(f"ocr.oem must be an int in 0..3, got {ocfg.oem!r}")
    if not isinstance(ocfg.lang, str) or not _LANG_PATTERN.fullmatch(ocfg.lang):
        raise ValueError(f"ocr.lang must look like 'eng' or 'eng+deu', got {ocfg.lang!r}")


def _run_tesseract(image: np.ndarray, ocfg: Config) -> OcrResult:
    data = pytesseract.image_to_data(
        image,
        lang=ocfg.lang,
        config=f"--psm {ocfg.psm} --oem {ocfg.oem}",
        output_type=pytesseract.Output.DICT,
    )
    words: list[str] = []
    confidences: list[float] = []
    for word, conf in zip(data["text"], data["conf"]):
        word = word.strip()
        if not word:
            continue
        conf = float(conf)
        if conf < ocfg.min_word_confidence:
            continue
        words.append(word)
        confidences.append(conf)
    text = " ".join(words)
    if not confidences or len(text) < ocfg.min_text_chars:
        return OcrResult(text="", confidence=-1.0)
    return OcrResult(text=text, confidence=sum(confidences) / len(confidences))


def ocr_region(image_crop: np.ndarray, config: Config) -> OcrResult:
    """Run OCR on a single region crop from the original image.

    Accepts BGR or grayscale uint8 crops. Returns empty text (confidence -1)
    for regions with no confident words — callers treat that as "no text here".
    """
    if image_crop.dtype != np.uint8:
        raise ValueError(f"expected uint8 crop, got dtype {image_crop.dtype}")
    if image_crop.ndim not in (2, 3) or image_crop.size == 0:
        raise ValueError(f"expected non-empty 2D/3D crop, got shape {image_crop.shape}")
    ocfg = config.ocr
    _validate_tesseract_params(ocfg)

    cache_dir = Path(ocfg.cache_dir)
    cache_path = cache_dir / f"{_cache_key(image_crop, ocfg)}.json"
    if ocfg.cache_enabled and cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(cached.get("text"), str) and isinstance(
                cached.get("confidence"), (int, float)
            ):
                return OcrResult(text=cached["text"], confidence=float(cached["confidence"]))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError, AttributeError):
            pass
        # corrupt/partial/wrong-typed cache entry -> treat as a miss and recompute

    factor = float(ocfg.upscale_factor)
    if factor <= 0:
        raise ValueError(f"ocr.upscale_factor must be > 0, got {factor!r}")
    if image_crop.ndim == 3:
        # cv2 crops are BGR; PIL (inside pytesseract) assumes RGB — convert or
        # colored regions get their channels swapped before Tesseract binarizes
        image_crop = cv2.cvtColor(image_crop, cv2.COLOR_BGR2RGB)
    upscaled = cv2.resize(
        image_crop, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC
    )
    result = _run_tesseract(upscaled, ocfg)

    if ocfg.cache_enabled:
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_suffix(f".{os.getpid()}.tmp")
        tmp_path.write_text(
            json.dumps({"text": result.text, "confidence": result.confidence}),
            encoding="utf-8",
        )
        os.replace(tmp_path, cache_path)  # atomic on POSIX and Windows
    return result
