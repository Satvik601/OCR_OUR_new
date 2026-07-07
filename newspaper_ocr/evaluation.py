"""Stage 6 — evaluation against hand-annotated ground truth.

Compares a pipeline output document (ARCHITECTURE.md schema) against
tests/fixtures/real_sample_page_groundtruth.json-style ground truth:

- region precision/recall: greedy one-to-one IoU matching at ``iou_threshold``
  (default 0.5, the same criterion the layout verification uses);
- word accuracy: aggregate over matched pairs whose GT region has complete text,
  weighted by GT word count;
- fragmentation rate: mean number of detected boxes overlapping (IoU >= 0.1)
  each GT region that has at least one overlap — 1.0 is ideal, higher means
  articles are being split;
- articles_found: GT articles with at least one IoU-matched region.
"""

from __future__ import annotations

from typing import Any

from .boxes import Box, iou, match_boxes
from .text_metrics import tokenize, word_accuracy

FRAGMENT_OVERLAP_IOU = 0.1


def _to_box(bbox: dict[str, int]) -> Box:
    return (bbox["x"], bbox["y"], bbox["w"], bbox["h"])


def evaluate(
    result_doc: dict[str, Any],
    ground_truth: dict[str, Any],
    iou_threshold: float = 0.5,
) -> dict[str, float]:
    """Compare a pipeline output document against ground truth; return metrics."""
    detected = result_doc["regions"]
    gt_regions = ground_truth["regions"]
    det_boxes = [_to_box(r["bbox"]) for r in detected]
    gt_boxes = [_to_box(r["bbox"]) for r in gt_regions]

    matches = match_boxes(det_boxes, gt_boxes, iou_threshold)
    matched_gt = {gi for _, gi, _ in matches}

    precision = len(matches) / len(det_boxes) if det_boxes else 0.0
    recall = len(matches) / len(gt_boxes) if gt_boxes else 0.0

    # word accuracy over matched pairs with complete GT text, weighted by GT words
    weighted = 0.0
    weight = 0
    for di, gi, _ in matches:
        gt_region = gt_regions[gi]
        if not gt_region.get("text_complete", True) or not gt_region["text"]:
            continue
        words = len(tokenize(gt_region["text"]))
        weighted += word_accuracy(gt_region["text"], detected[di]["text"]) * words
        weight += words
    accuracy = weighted / weight if weight else 0.0

    # fragmentation: detected boxes overlapping each GT region at IoU >= 0.1
    overlap_counts = []
    for g in gt_boxes:
        n = sum(1 for d in det_boxes if iou(d, g) >= FRAGMENT_OVERLAP_IOU)
        if n:
            overlap_counts.append(n)
    fragmentation = sum(overlap_counts) / len(overlap_counts) if overlap_counts else 0.0

    # articles with at least one matched region
    matched_articles = {
        gt_regions[gi].get("article_id")
        for gi in matched_gt
        if gt_regions[gi].get("article_id")
    }

    return {
        "num_detected": len(det_boxes),
        "num_ground_truth": len(gt_boxes),
        "num_matched": len(matches),
        "region_precision": precision,
        "region_recall": recall,
        "word_accuracy": accuracy,
        "fragmentation_rate": fragmentation,
        "articles_found": len(matched_articles),
        "articles_total": int(ground_truth.get("article_count", 0)),
    }
