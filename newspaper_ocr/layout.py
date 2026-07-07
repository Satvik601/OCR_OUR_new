"""Stage 2 — layout detection: binary page -> candidate article-region boxes.

Baseline classical-morphology backend:
1. horizontal closing (connect characters/words into lines),
2. vertical closing (merge lines into paragraph blocks),
3. square closing (fill remaining gaps),
4. external contour detection -> bounding boxes.

Closing (dilate-then-erode) is used instead of plain dilation so gaps smaller
than the kernel get bridged WITHOUT inflating the region beyond its real
content — plain dilation grows every box by half the kernel per side, which
hurts IoU against ground truth and can bridge column gutters.

The stage interface is pluggable: any callable with the signature
``detect_regions(binary_image, config) -> list[Box]`` can be swapped in
(e.g. a pretrained layout model) and compared under the same
PHASE_VERIFICATION_LOOP.md criteria.

All parameters come from the ``layout`` section of config.yaml.
"""

from __future__ import annotations

import cv2
import numpy as np

from .boxes import Box
from .config import Config


def _require_positive_int(value: object, key: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{key} must be an int >= 1, got {value!r}")


def _rect_kernel(size: object, key: str) -> np.ndarray:
    if (
        not isinstance(size, (list, tuple))
        or len(size) != 2
        or not all(isinstance(v, int) and v >= 1 for v in size)
    ):
        raise ValueError(f"{key} must be a [width, height] pair of ints >= 1, got {size!r}")
    return cv2.getStructuringElement(cv2.MORPH_RECT, tuple(size))


def detect_regions(binary_image: np.ndarray, config: Config) -> list[Box]:
    """Detect candidate region bounding boxes on a preprocessed binary page.

    Input: uint8 binary image, ink=255, background=0 (the preprocessing output
    contract). Returns boxes in reading order (top-to-bottom, left-to-right).
    No area/containment filtering happens here — that is stage 3.
    """
    if binary_image.ndim != 2 or binary_image.dtype != np.uint8 or binary_image.size == 0:
        raise ValueError(
            f"expected non-empty 2D uint8 binary image, got shape {binary_image.shape}, "
            f"dtype {binary_image.dtype}"
        )
    lcfg = config.layout
    _require_positive_int(lcfg.closing_iterations, "layout.closing_iterations")
    h_kernel = _rect_kernel(lcfg.horizontal_dilate_kernel, "layout.horizontal_dilate_kernel")
    v_kernel = _rect_kernel(lcfg.vertical_dilate_kernel, "layout.vertical_dilate_kernel")
    c_kernel = _rect_kernel(lcfg.closing_kernel, "layout.closing_kernel")

    lines = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, h_kernel)
    blocks = cv2.morphologyEx(lines, cv2.MORPH_CLOSE, v_kernel)
    closed = cv2.morphologyEx(
        blocks, cv2.MORPH_CLOSE, c_kernel, iterations=lcfg.closing_iterations
    )

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[Box] = [cv2.boundingRect(c) for c in contours]
    if lcfg.display_pass.enabled:
        boxes += _detect_display_regions(binary_image, lcfg.display_pass)
    boxes.sort(key=lambda b: (b[1], b[0]))
    return boxes


def _detect_display_regions(binary_image: np.ndarray, d: Config) -> list[Box]:
    """Second detection pass at display-text scale (headlines, mastheads).

    One vertical kernel can't merge headline lines (30-40px gaps) without also
    fusing distinct stacked regions (~10px gaps). But headline GLYPHS are an
    order of magnitude taller than body-text glyphs, so: keep only connected
    components at least `min_component_height` tall, then close aggressively
    on that display-only mask — body text isn't in the mask, so nothing else
    gets fused. Resulting boxes are unioned with the fine-scale boxes;
    duplicates/nesting are stage-3's (filtering's) job.
    """
    _require_positive_int(d.min_component_height, "layout.display_pass.min_component_height")
    _require_positive_int(d.max_component_height, "layout.display_pass.max_component_height")
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_image, connectivity=8)
    heights = stats[:, cv2.CC_STAT_HEIGHT]
    tall = (heights >= d.min_component_height) & (heights <= d.max_component_height)
    tall[0] = False  # background label
    if not tall.any():
        return []
    mask = (tall[labels]).astype(np.uint8) * 255
    h_kernel = _rect_kernel(d.horizontal_close, "layout.display_pass.horizontal_close")
    v_kernel = _rect_kernel(d.vertical_close, "layout.display_pass.vertical_close")
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, h_kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, v_kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in contours]
    out: list[Box] = []
    for box in boxes:
        out.extend(_split_at_gutters(box, binary_image, mask, d))
    return out


def _split_at_gutters(
    box: Box, binary_image: np.ndarray, mask: np.ndarray, d: Config
) -> list[Box]:
    """Recursively split a display box at blank vertical bands (column gutters).

    The display pass's horizontal closing must bridge headline word gaps
    (~25-30px), which are WIDER than column gutters (~15px) — so it sometimes
    chains display text across columns. The original binary page still shows
    the gutter as a near-inkless vertical band. When one is found, the CLOSED
    MASK (not just the box) is cut there and contours are re-extracted per
    side — a box-level cut would wrongly give each side the union's full
    vertical extent.
    """
    x, y, w, h = box
    if w <= 0 or h <= 0:
        return []
    if h < d.gutter_split_min_height:
        # A single display LINE has full-height blank bands at every word gap —
        # only boxes taller than any one display line can safely be gutter-split.
        return [box]
    crop = binary_image[y : y + h, x : x + w]
    ink_per_col = (crop > 0).sum(axis=0)
    blank = ink_per_col <= d.gutter_max_ink_ratio * h

    # scan interior columns for the first blank run wide enough to be a gutter
    run_start = None
    gutter = None
    for i in range(w):
        if blank[i]:
            if run_start is None:
                run_start = i
            if i - run_start + 1 >= d.gutter_min_px and run_start > 0:
                gutter = run_start
                break
        else:
            run_start = None
    if gutter is None:
        return [box]

    # cut the mask at the gutter within this box, then re-extract real components
    gutter_end = gutter
    while gutter_end < w and blank[gutter_end]:
        gutter_end += 1
    sub_mask = mask[y : y + h, x : x + w].copy()
    sub_mask[:, gutter:gutter_end] = 0
    contours, _ = cv2.findContours(sub_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result: list[Box] = []
    for c in contours:
        sx, sy, sw, sh = cv2.boundingRect(c)
        result.extend(_split_at_gutters((x + sx, y + sy, sw, sh), binary_image, mask, d))
    return result
