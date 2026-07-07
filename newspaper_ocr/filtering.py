"""Stage 3 — region filtering (NOT YET IMPLEMENTED, phase 3).

Removes noise regions (area thresholds), nested/duplicate boxes
(containment filtering), and — after OCR — regions whose text is
incoherent garbage.
"""

from __future__ import annotations

from .config import Config
from .layout import Box


def filter_regions(boxes: list[Box], page_shape: tuple[int, int], config: Config) -> list[Box]:
    """Filter candidate boxes: area thresholds + containment de-duplication."""
    raise NotImplementedError("filtering is phase 3; layout detection must pass first")
