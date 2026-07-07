"""Phase 1 verification per PHASE_VERIFICATION_LOOP.md — run against the REAL page.

Checks (thresholds from config.yaml `verification.preprocessing`):
1. Speckle: connected components with area < min_speckle_area_px, per megapixel,
   must be < max_speckle_per_mpx.
2. Character loss: for every ground-truth TEXT region (photos excluded), ink pixels in
   the preprocessed crop must be >= min_ink_retention x a per-crop plain-Otsu baseline;
   at most max_lost_region_pct % of regions may fail.

Saves evidence to debug_output/ (01_preprocessed_real.png) and prints a PASS/FAIL report.
Exit code 0 on pass, 1 on fail.

Usage: python scripts/verify_preprocessing.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newspaper_ocr.config import load_config
from newspaper_ocr.preprocessing import preprocess, to_grayscale

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
DEBUG = ROOT / "debug_output"


def main() -> int:
    config = load_config()
    vcfg = config.verification.preprocessing

    image = cv2.imread(str(FIXTURES / "real_sample_page.jpg"), cv2.IMREAD_COLOR)
    assert image is not None, "real_sample_page.jpg missing"
    gt = json.loads((FIXTURES / "real_sample_page_groundtruth.json").read_text(encoding="utf-8"))

    binary = preprocess(image, config)
    DEBUG.mkdir(exist_ok=True)
    out_path = DEBUG / "01_preprocessed_real.png"
    cv2.imwrite(str(out_path), binary)

    # --- check 1: speckle density ---
    n, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    speckles = int((areas < vcfg.min_speckle_area_px).sum())
    per_mpx = speckles / (binary.size / 1_000_000)
    speckle_pass = per_mpx < vcfg.max_speckle_per_mpx

    # --- check 2: per-region ink retention vs plain-Otsu baseline ---
    gray = to_grayscale(image)
    text_regions = [r for r in gt["regions"] if r["region_type"] != "photo" and r["text"]]
    losses = []
    for r in text_regions:
        b = r["bbox"]
        crop_gray = gray[b["y"] : b["y"] + b["h"], b["x"] : b["x"] + b["w"]]
        crop_bin = binary[b["y"] : b["y"] + b["h"], b["x"] : b["x"] + b["w"]]
        _, baseline = cv2.threshold(crop_gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        base_ink = int((baseline == 255).sum())
        kept_ink = int((crop_bin == 255).sum())
        retention = kept_ink / base_ink if base_ink else 1.0
        losses.append((r["id"], r["region_type"], retention))
    failed = [(rid, rtype, ret) for rid, rtype, ret in losses if ret < vcfg.min_ink_retention]
    lost_pct = 100.0 * len(failed) / len(text_regions)
    retention_pass = lost_pct <= vcfg.max_lost_region_pct

    # --- report ---
    print(f"evidence image : {out_path}")
    print(f"components     : {n - 1}")
    print(
        f"speckle check  : {speckles} speckles (<{vcfg.min_speckle_area_px}px) "
        f"= {per_mpx:.0f}/Mpx  (limit {vcfg.max_speckle_per_mpx}/Mpx) "
        f"-> {'PASS' if speckle_pass else 'FAIL'}"
    )
    print(
        f"retention check: {len(failed)}/{len(text_regions)} text regions below "
        f"{vcfg.min_ink_retention} retention = {lost_pct:.1f}% lost "
        f"(limit {vcfg.max_lost_region_pct}%) -> {'PASS' if retention_pass else 'FAIL'}"
    )
    for rid, rtype, ret in sorted(losses, key=lambda t: t[2])[:8]:
        marker = " <-- FAIL" if ret < vcfg.min_ink_retention else ""
        print(f"    {rid} ({rtype}): retention {ret:.2f}{marker}")

    overall = speckle_pass and retention_pass
    print(f"\nRESULT: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
