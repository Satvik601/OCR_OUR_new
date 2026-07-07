"""Stage 4 — per-region OCR (NOT YET IMPLEMENTED, phase 4).

Each region is cropped from the ORIGINAL (non-binarized) image, upscaled
2x bicubic, then run through Tesseract with PSM 6 (single uniform block)
and the LSTM engine (OEM 1). Very short / incoherent outputs are dropped.

The backend is pluggable: any callable ``ocr_region(image_crop, config)
-> OcrResult`` can be swapped in (e.g. EasyOCR / PaddleOCR) and compared
under the same verification criteria.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import Config


@dataclass
class OcrResult:
    text: str
    confidence: float  # mean word confidence, 0-100; -1 if unavailable


def ocr_region(image_crop: np.ndarray, config: Config) -> OcrResult:
    """Run OCR on a single region crop from the original image."""
    raise NotImplementedError("OCR is phase 4; filtering must pass first")
