"""Bounding-box utilities shared by layout detection, filtering, and evaluation.

Box convention everywhere: ``(x, y, w, h)`` in pixel coordinates of the original image.
"""

from __future__ import annotations

Box = tuple[int, int, int, int]


def area(box: Box) -> int:
    return box[2] * box[3]


def intersection(a: Box, b: Box) -> int:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    return ix * iy


def iou(a: Box, b: Box) -> float:
    inter = intersection(a, b)
    union = area(a) + area(b) - inter
    return inter / union if union else 0.0


def containment(inner: Box, outer: Box) -> float:
    """Fraction of `inner`'s area that lies inside `outer` (1.0 = fully nested)."""
    inner_area = area(inner)
    return intersection(inner, outer) / inner_area if inner_area else 0.0


def match_boxes(
    detected: list[Box], ground_truth: list[Box], iou_threshold: float
) -> list[tuple[int, int, float]]:
    """Greedy one-to-one matching by descending IoU.

    Returns (detected_index, ground_truth_index, iou) triples for pairs with
    IoU >= iou_threshold. Each box appears in at most one pair.
    """
    candidates = [
        (iou(d, g), di, gi)
        for di, d in enumerate(detected)
        for gi, g in enumerate(ground_truth)
    ]
    candidates = [(v, di, gi) for v, di, gi in candidates if v >= iou_threshold]
    candidates.sort(reverse=True)
    used_d: set[int] = set()
    used_g: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    for value, di, gi in candidates:
        if di in used_d or gi in used_g:
            continue
        used_d.add(di)
        used_g.add(gi)
        matches.append((di, gi, value))
    return matches
