"""Stage 1 — preprocessing: BGR page scan -> clean binary image (ink=255, bg=0).

Steps (see ARCHITECTURE.md):
grayscale -> Gaussian blur -> Otsu (inverted) -> morphological opening -> border clearing.
"""

from __future__ import annotations

import numpy as np

from .config import Config


def preprocess(image: np.ndarray, config: Config) -> np.ndarray:
    """Binarize a page scan. Returns uint8 image, ink=255, background=0."""
    raise NotImplementedError("implemented test-first in phase 1")
