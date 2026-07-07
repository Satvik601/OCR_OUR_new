"""CLI entry point: python -m newspaper_ocr.run --input page.jpg --output result.json

Full pipeline: preprocess -> layout -> filtering -> per-region OCR -> JSON export.
Exit codes: 0 success, 2 input/config error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

from .config import load_config
from .export import build_document, validate_document
from .filtering import filter_regions
from .layout import detect_regions
from .ocr import ocr_region
from .preprocessing import preprocess


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m newspaper_ocr.run",
        description="Segment a scanned newspaper page into article regions and OCR each region.",
    )
    parser.add_argument("--input", required=True, help="path to the scanned page image")
    parser.add_argument("--output", required=True, help="path for the structured JSON output")
    parser.add_argument("--config", default=None, help="path to config.yaml (default: repo root)")
    parser.add_argument(
        "--debug-dir",
        default=None,
        help="if set, save intermediate images (preprocessed page, region overlay) here",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except (OSError, ValueError) as exc:
        print(f"error: could not load config: {exc}", file=sys.stderr)
        return 2

    # Decompression-bomb guard: check declared dimensions from the header (PIL
    # reads it lazily) before cv2.imread decodes the full pixel buffer.
    try:
        from PIL import Image

        with Image.open(args.input) as probe:
            declared_pixels = probe.size[0] * probe.size[1]
        max_pixels = config.limits.max_image_pixels
        if declared_pixels > max_pixels:
            print(
                f"error: image declares {declared_pixels:,} pixels, over the "
                f"limits.max_image_pixels cap of {max_pixels:,}",
                file=sys.stderr,
            )
            return 2
    except (OSError, ValueError) as exc:
        print(f"error: could not read image: {args.input} ({exc})", file=sys.stderr)
        return 2

    image = cv2.imread(args.input, cv2.IMREAD_COLOR)
    if image is None:
        print(f"error: could not read image: {args.input}", file=sys.stderr)
        return 2

    try:
        binary = preprocess(image, config)
        candidate_boxes = detect_regions(binary, config)
        kept_boxes = filter_regions(candidate_boxes, binary.shape, config)
    except (ValueError, AttributeError) as exc:
        # bad parameter value / missing config key — clean message, not a traceback
        print(f"error: pipeline failed: {exc}", file=sys.stderr)
        return 2

    regions = []
    for x, y, w, h in kept_boxes:
        crop = image[y : y + h, x : x + w]
        result = ocr_region(crop, config)
        if not result.text:
            continue  # post-OCR garbage filter: regions with no confident text are dropped
        # Weak detection-confidence proxy until a learned detector exists: the
        # region's ink density in the binarized page (documented in ARCHITECTURE.md).
        ink_ratio = float((binary[y : y + h, x : x + w] == 255).mean())
        regions.append(
            {
                "bbox": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
                "text": result.text,
                "detection_confidence": round(ink_ratio, 3),
                "ocr_confidence": round(result.confidence, 1),
                "region_type": "unclassified",
            }
        )

    height, width = binary.shape
    doc = build_document(
        source_image=args.input,
        page_size=(width, height),
        regions=regions,
        dropped_count=len(candidate_boxes) - len(regions),
    )
    problems = validate_document(doc)
    if problems:
        print("error: output failed schema validation: " + "; ".join(problems), file=sys.stderr)
        return 2

    output_path = Path(args.output)
    if output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.debug_dir:
        debug_dir = Path(args.debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(debug_dir / "01_preprocessed.png"), binary)
        overlay = image.copy()
        for region in doc["regions"]:
            b = region["bbox"]
            cv2.rectangle(overlay, (b["x"], b["y"]), (b["x"] + b["w"], b["y"] + b["h"]), (0, 200, 0), 2)
            cv2.putText(
                overlay, region["id"], (b["x"] + 3, b["y"] + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 0), 2,
            )
        cv2.imwrite(str(debug_dir / "05_regions.png"), overlay)

    print(
        f"wrote {doc['stats']['num_regions']} regions to {args.output} "
        f"({doc['stats']['num_regions_dropped_by_filtering']} candidates dropped)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
