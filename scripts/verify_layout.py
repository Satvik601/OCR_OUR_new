"""Phase 2 verification per PHASE_VERIFICATION_LOOP.md — run against the REAL page.

Pass criterion (config.yaml `verification.layout`): at least `min_gt_coverage` (80%)
of ground-truth regions have a detected box with IoU >= `min_iou` (0.5).

Saves evidence to debug_output/02_layout_real.png: detected boxes (green) over the
page, matched GT in blue, unmatched GT in red. Exit 0 on pass, 1 on fail.

Usage: python scripts/verify_layout.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newspaper_ocr.boxes import match_boxes
from newspaper_ocr.config import load_config
from newspaper_ocr.layout import detect_regions
from newspaper_ocr.preprocessing import preprocess

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
DEBUG = ROOT / "debug_output"


def main() -> int:
    config = load_config()
    vcfg = config.verification.layout

    image = cv2.imread(str(FIXTURES / "real_sample_page.jpg"), cv2.IMREAD_COLOR)
    assert image is not None, "real_sample_page.jpg missing"
    gt = json.loads((FIXTURES / "real_sample_page_groundtruth.json").read_text(encoding="utf-8"))
    gt_regions = gt["regions"]
    gt_boxes = [(r["bbox"]["x"], r["bbox"]["y"], r["bbox"]["w"], r["bbox"]["h"]) for r in gt_regions]
    if not gt_boxes:
        sys.exit("no ground-truth regions in real_sample_page_groundtruth.json")

    binary = preprocess(image, config)
    detected = detect_regions(binary, config)

    matches = match_boxes(detected, gt_boxes, iou_threshold=vcfg.min_iou)
    matched_gt = {gi for _, gi, _ in matches}
    coverage = len(matched_gt) / len(gt_boxes)

    # evidence overlay
    overlay = image.copy()
    for x, y, w, h in detected:
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 200, 0), 2)
    for gi, (r, b) in enumerate(zip(gt_regions, gt_boxes)):
        color = (255, 0, 0) if gi in matched_gt else (0, 0, 255)
        cv2.rectangle(overlay, (b[0], b[1]), (b[0] + b[2], b[1] + b[3]), color, 2)
        if gi not in matched_gt:
            cv2.putText(overlay, r["id"], (b[0] + 4, b[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    DEBUG.mkdir(exist_ok=True)
    out_path = DEBUG / "02_layout_real.png"
    cv2.imwrite(str(out_path), overlay)

    iou_by_gt = {gi: v for _, gi, v in matches}
    print(f"evidence image : {out_path}")
    print(f"detected boxes : {len(detected)}")
    print(
        f"GT coverage    : {len(matched_gt)}/{len(gt_boxes)} = {coverage:.0%} at IoU>="
        f"{vcfg.min_iou} (need >= {vcfg.min_gt_coverage:.0%})"
    )
    unmatched = [r["id"] + f"({r['region_type']})" for gi, r in enumerate(gt_regions) if gi not in matched_gt]
    if unmatched:
        print(f"unmatched GT   : {', '.join(unmatched)}")
    matched_ious = sorted(iou_by_gt.values())
    if matched_ious:
        print(f"matched IoUs   : min {matched_ious[0]:.2f}, median {matched_ious[len(matched_ious)//2]:.2f}")

    ok = coverage >= vcfg.min_gt_coverage
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
