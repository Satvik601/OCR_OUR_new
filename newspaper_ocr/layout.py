"""Stage 2 — layout detection (NOT YET IMPLEMENTED, phase 2).

Baseline backend: classical morphology — horizontal dilation to connect
characters into lines, vertical dilation to merge lines into blocks,
morphological closing, then contour detection to produce candidate
region bounding boxes.

The stage interface is pluggable: any callable with the signature
``detect_regions(binary_image, config) -> list[Box]`` can be swapped in
(e.g. a pretrained layout model) and compared under the same
PHASE_VERIFICATION_LOOP.md criteria.
"""

from __future__ import annotations

import numpy as np

from .config import Config

# Box = (x, y, w, h) in pixel coordinates of the input image.
Box = tuple[int, int, int, int]


def detect_regions(binary_image: np.ndarray, config: Config) -> list[Box]:
    """Detect candidate article-region bounding boxes on a binarized page."""
    raise NotImplementedError("layout detection is phase 2; preprocessing must pass first")
