"""Stage 3 — region filtering: candidate boxes -> kept article-region boxes.

Rules (parameters from the ``filtering`` section of config.yaml):
1. Area floor: boxes smaller than ``min_area_px`` are noise.
2. Area ceiling: boxes covering more than ``max_area_ratio`` of the page are
   page frames / whole-page artifacts, not articles.
3. Containment de-duplication: a box whose area is at least
   ``containment_threshold`` inside a larger kept box is a nested duplicate
   (layout's fine pass and display pass intentionally overlap) — dropped.

Garbage-TEXT filtering (incoherent OCR output) happens after OCR in stage 4,
not here — this stage is geometry only.
"""

from __future__ import annotations

from .boxes import Box, area, containment
from .config import Config


def filter_regions(
    boxes: list[Box], page_shape: tuple[int, ...], config: Config
) -> list[Box]:
    """Filter candidate boxes. `page_shape` is (height, width[, ...]) numpy-style.

    Returns kept boxes in reading order (top-to-bottom, left-to-right).
    """
    fcfg = config.filtering
    page_area = int(page_shape[0]) * int(page_shape[1])
    max_area = fcfg.max_area_ratio * page_area

    sized = [b for b in boxes if fcfg.min_area_px <= area(b) <= max_area]

    # Largest first: a nested box is always judged against already-kept larger boxes,
    # so keeping the outer and dropping the inner falls out naturally. Exact duplicates
    # collapse because containment(dup, kept-dup) == 1.0.
    sized.sort(key=area, reverse=True)
    kept: list[Box] = []
    for box in sized:
        if any(containment(box, big) >= fcfg.containment_threshold for big in kept):
            continue
        kept.append(box)

    kept.sort(key=lambda b: (b[1], b[0]))
    return kept
