"""Phase 4 verification per PHASE_VERIFICATION_LOOP.md — run against the REAL page.

Pass criterion (config.yaml `verification.ocr`): aggregate word accuracy >=
`word_accuracy_threshold` (0.70) against ground-truth text, over GT TEXT regions
(photos and text_complete=false regions excluded) that layout+filtering matched
at IoU >= 0.5. Aggregation is weighted by GT word count, so a long body column
counts more than a two-word caption. Per-region accuracies are printed for
diagnosis.

Saves evidence to debug_output/04_ocr_real.txt (per-region GT vs OCR text).
Exit 0 on pass, 1 on fail.

Usage: python scripts/verify_ocr.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newspaper_ocr.boxes import match_boxes
from newspaper_ocr.config import load_config
from newspaper_ocr.filtering import filter_regions
from newspaper_ocr.layout import detect_regions
from newspaper_ocr.ocr import ocr_region
from newspaper_ocr.preprocessing import preprocess
from newspaper_ocr.text_metrics import tokenize, word_accuracy

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
DEBUG = ROOT / "debug_output"


def main() -> int:
    config = load_config()
    threshold = config.verification.ocr.word_accuracy_threshold
    min_iou = config.verification.layout.min_iou

    image = cv2.imread(str(FIXTURES / "real_sample_page.jpg"), cv2.IMREAD_COLOR)
    assert image is not None, "real_sample_page.jpg missing"
    gt = json.loads((FIXTURES / "real_sample_page_groundtruth.json").read_text(encoding="utf-8"))
    regions = gt["regions"]
    gt_boxes = [(r["bbox"]["x"], r["bbox"]["y"], r["bbox"]["w"], r["bbox"]["h"]) for r in regions]

    binary = preprocess(image, config)
    kept = filter_regions(detect_regions(binary, config), binary.shape, config)
    matches = match_boxes(kept, gt_boxes, min_iou)

    lines: list[str] = []
    weighted_sum = 0.0
    total_weight = 0
    evaluated = 0
    for di, gi, box_iou in sorted(matches, key=lambda m: m[1]):
        region = regions[gi]
        if region["region_type"] == "photo" or not region["text"]:
            continue
        if not region.get("text_complete", True):
            continue
        x, y, w, h = kept[di]
        crop = image[y : y + h, x : x + w]
        result = ocr_region(crop, config)
        accuracy = word_accuracy(region["text"], result.text)
        weight = len(tokenize(region["text"]))
        weighted_sum += accuracy * weight
        total_weight += weight
        evaluated += 1
        print(
            f"  {region['id']} ({region['region_type']:8s}) IoU {box_iou:.2f} "
            f"words {weight:3d}  accuracy {accuracy:.2f}  conf {result.confidence:5.1f}"
        )
        lines.append(
            f"=== {region['id']} ({region['region_type']}, IoU {box_iou:.2f}, "
            f"accuracy {accuracy:.2f}) ===\nGT : {region['text']}\nOCR: {result.text}\n"
        )

    if total_weight == 0:
        print("no evaluable matched text regions — cannot verify")
        return 1
    aggregate = weighted_sum / total_weight

    DEBUG.mkdir(exist_ok=True)
    out_path = DEBUG / "04_ocr_real.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nevidence file  : {out_path}")
    print(f"regions scored : {evaluated} (weighted by GT word count, {total_weight} words)")
    print(f"word accuracy  : {aggregate:.3f} (threshold {threshold})")
    ok = aggregate >= threshold
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
