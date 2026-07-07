"""Phase 3 verification per PHASE_VERIFICATION_LOOP.md — run against the REAL page.

Pass criteria (config.yaml `verification.filtering` + loop table):
1. Kept-region count within ±`region_count_tolerance` (20%) of the ground-truth
   REGION count (see CLAUDE.md decisions log: the loop table says "article count",
   interpreted as region count because detection is region-level).
2. No ground-truth region that was matched BEFORE filtering loses its match AFTER
   (filtering must never drop a real article region).

Saves evidence to debug_output/03_filtering_real.png (kept boxes green, dropped red).
Exit 0 on pass, 1 on fail.

Usage: python scripts/verify_filtering.py
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
from newspaper_ocr.preprocessing import preprocess

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
DEBUG = ROOT / "debug_output"


def main() -> int:
    config = load_config()
    tol = config.verification.filtering.region_count_tolerance
    min_iou = config.verification.layout.min_iou

    image = cv2.imread(str(FIXTURES / "real_sample_page.jpg"), cv2.IMREAD_COLOR)
    assert image is not None, "real_sample_page.jpg missing"
    gt = json.loads((FIXTURES / "real_sample_page_groundtruth.json").read_text(encoding="utf-8"))
    gt_boxes = [(r["bbox"]["x"], r["bbox"]["y"], r["bbox"]["w"], r["bbox"]["h"]) for r in gt["regions"]]

    binary = preprocess(image, config)
    detected = detect_regions(binary, config)
    kept = filter_regions(detected, binary.shape, config)

    before = {gi for _, gi, _ in match_boxes(detected, gt_boxes, min_iou)}
    after = {gi for _, gi, _ in match_boxes(kept, gt_boxes, min_iou)}
    lost = before - after

    lo, hi = len(gt_boxes) * (1 - tol), len(gt_boxes) * (1 + tol)
    count_ok = lo <= len(kept) <= hi
    coverage_ok = not lost

    dropped = [b for b in detected if b not in kept]
    overlay = image.copy()
    for x, y, w, h in dropped:
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 0, 255), 1)
    for x, y, w, h in kept:
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 200, 0), 2)
    DEBUG.mkdir(exist_ok=True)
    out_path = DEBUG / "03_filtering_real.png"
    cv2.imwrite(str(out_path), overlay)

    print(f"evidence image : {out_path}")
    print(f"boxes          : {len(detected)} detected -> {len(kept)} kept ({len(dropped)} dropped)")
    print(
        f"count check    : {len(kept)} vs GT {len(gt_boxes)} regions, allowed "
        f"[{lo:.0f}, {hi:.0f}] -> {'PASS' if count_ok else 'FAIL'}"
    )
    print(
        f"coverage check : matched GT before={len(before)}, after={len(after)}, "
        f"lost={sorted(gt['regions'][i]['id'] for i in lost) if lost else 'none'} "
        f"-> {'PASS' if coverage_ok else 'FAIL'}"
    )

    ok = count_ok and coverage_ok
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
