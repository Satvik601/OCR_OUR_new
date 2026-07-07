"""CLI entry point: python -m newspaper_ocr.run --input page.jpg --output result.json

Runs whichever pipeline stages are implemented so far. Until all phases
pass verification (see PHASE_VERIFICATION_LOOP.md) this exits with a
clear message at the first unimplemented stage rather than pretending to
produce full output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

from .config import load_config
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
        help="if set, save intermediate images (preprocessed page, region overlays) here",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except (OSError, ValueError) as exc:
        print(f"error: could not load config: {exc}", file=sys.stderr)
        return 2

    image = cv2.imread(args.input, cv2.IMREAD_COLOR)
    if image is None:
        print(f"error: could not read image: {args.input}", file=sys.stderr)
        return 2

    try:
        binary = preprocess(image, config)
    except (ValueError, AttributeError) as exc:
        # bad parameter value / missing config key — clean message, not a traceback
        print(f"error: preprocessing failed: {exc}", file=sys.stderr)
        return 2

    if args.debug_dir:
        debug_dir = Path(args.debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(debug_dir / "01_preprocessed.png"), binary)

    # Later phases are wired in here as they pass verification.
    print(
        "preprocessing complete; layout detection (phase 2) is not implemented yet, "
        "so no JSON was written. See PROGRESS.md for pipeline status.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    sys.exit(main())
