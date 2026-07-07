"""Stage 3 — region filtering: candidate boxes -> kept article-region boxes.

Rules (parameters from the ``filtering`` section of config.yaml):
1. Area floor: boxes smaller than ``min_area_px`` are noise.
2. Area ceiling: boxes covering more than ``max_area_ratio`` of the page are
   page frames / whole-page artifacts, not articles.
3. Containment de-duplication: a box whose area is at least
   ``containment_threshold`` inside a larger kept box is a nested duplicate
   (layout's fine pass and display pass intentionally overlap) — dropped.
4. Fragment stitching (``filtering.stitch``): words/pieces of one text line
   sometimes survive as separate boxes (e.g. italic display headlines whose
   glyphs neither the fine pass nor the display pass fully connects). Boxes
   that sit on the same line — similar heights, strong vertical overlap,
   small horizontal gap relative to line height — are merged. Height caps
   keep body-text columns (tall blocks) out, so columns never merge.
   Optionally (``stitch.vertical``) stacked lines of one display block are
   merged too, with tighter gap limits so distinct stacked regions stay apart.

Garbage-TEXT filtering (incoherent OCR output) happens after OCR in stage 4,
not here — this stage is geometry only.
"""

from __future__ import annotations

from .boxes import Box, area, containment, intersection
from .config import Config


def _union(a: Box, b: Box) -> Box:
    x0 = min(a[0], b[0])
    y0 = min(a[1], b[1])
    x1 = max(a[0] + a[2], b[0] + b[2])
    y1 = max(a[1] + a[3], b[1] + b[3])
    return (x0, y0, x1 - x0, y1 - y0)


def _same_line(a: Box, b: Box, s: Config) -> bool:
    """a and b look like fragments of one text line (side by side)."""
    ha, hb = a[3], b[3]
    if ha > s.max_height or hb > s.max_height:
        return False
    if max(ha, hb) / min(ha, hb) > s.max_height_ratio:
        return False
    v_overlap = min(a[1] + ha, b[1] + hb) - max(a[1], b[1])
    if v_overlap / min(ha, hb) < s.min_vertical_overlap:
        return False
    h_gap = max(a[0], b[0]) - min(a[0] + a[2], b[0] + b[2])
    return h_gap <= s.max_gap_ratio * min(ha, hb)


def _stacked_lines(a: Box, b: Box, s: Config) -> bool:
    """a and b look like consecutive lines of one display block (stacked)."""
    ha, hb = a[3], b[3]
    if ha > s.max_height or hb > s.max_height:
        return False
    if max(ha, hb) / min(ha, hb) > s.max_height_ratio:
        return False
    h_overlap = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    if h_overlap / min(a[2], b[2]) < s.vertical.min_horizontal_overlap:
        return False
    v_gap = max(a[1], b[1]) - min(a[1] + ha, b[1] + hb)
    return v_gap <= s.vertical.max_gap_ratio * min(ha, hb)


def _overlapping(a: Box, b: Box, s: Config) -> bool:
    """a and b physically overlap by a non-trivial fraction of the smaller box.

    Overlapping boxes cannot be different columns, so merging them is safe by
    construction — this is the rule that consolidates multi-line fragments of
    one display block (which partially overlap each other). The threshold
    keeps boxes that merely graze each other by a few edge pixels apart.
    """
    inter = intersection(a, b)
    if inter == 0:
        return False
    return inter / min(area(a), area(b)) >= s.min_overlap_merge


def _stitch_fragments(boxes: list[Box], s: Config) -> list[Box]:
    """Iteratively merge overlapping / same-line / stacked-line fragments."""
    boxes = list(boxes)
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if (
                    _overlapping(a, b, s)
                    or _same_line(a, b, s)
                    or (s.vertical.enabled and _stacked_lines(a, b, s))
                ):
                    boxes[i] = _union(a, b)
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    return boxes


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

    if fcfg.stitch.enabled:
        kept = _stitch_fragments(kept, fcfg.stitch)
        # stitched boxes may now envelop other kept boxes — dedupe once more
        kept.sort(key=area, reverse=True)
        deduped: list[Box] = []
        for box in kept:
            if any(containment(box, big) >= fcfg.containment_threshold for big in deduped):
                continue
            deduped.append(box)
        kept = deduped

    kept.sort(key=lambda b: (b[1], b[0]))
    return kept
