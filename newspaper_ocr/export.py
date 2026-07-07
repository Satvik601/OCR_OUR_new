"""Stage 5 — structured JSON export.

Assembles and validates the output document per the schema in ARCHITECTURE.md:
region id, bounding box, extracted text, detection confidence, OCR confidence,
region type placeholder. `validate_document` is dependency-free (no jsonschema)
and returns a list of human-readable problems (empty list = valid) — used both
by tests and by the phase-5 verification gate.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import __version__

REGION_TYPES = {"headline", "body", "caption", "masthead", "quote", "other", "unclassified"}
_REGION_FIELDS = ("bbox", "text", "detection_confidence", "ocr_confidence", "region_type")
_BBOX_FIELDS = ("x", "y", "w", "h")


def build_document(
    source_image: str,
    page_size: tuple[int, int],
    regions: list[dict[str, Any]],
    dropped_count: int,
) -> dict[str, Any]:
    """Assemble the output document. `page_size` is (width, height).

    Each input region dict must already carry bbox/text/detection_confidence/
    ocr_confidence/region_type; ids are assigned here (r001, r002, ... in list
    order, which the pipeline keeps as reading order).
    """
    out_regions: list[dict[str, Any]] = []
    for index, region in enumerate(regions, start=1):
        missing = [f for f in _REGION_FIELDS if f not in region]
        if missing:
            raise ValueError(f"region {index} missing fields: {', '.join(missing)}")
        out_regions.append({"id": f"r{index:03d}", **{f: region[f] for f in _REGION_FIELDS}})
    return {
        "source_image": source_image,
        "page_size": [int(page_size[0]), int(page_size[1])],
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": __version__,
        "regions": out_regions,
        "stats": {
            "num_regions": len(out_regions),
            "num_regions_dropped_by_filtering": int(dropped_count),
        },
    }


def validate_document(doc: dict[str, Any]) -> list[str]:
    """Check a document against the ARCHITECTURE.md schema. Returns problems found."""
    errors: list[str] = []
    for field in ("source_image", "page_size", "processed_at", "pipeline_version", "regions", "stats"):
        if field not in doc:
            errors.append(f"document missing field: {field}")
    if errors:
        return errors

    if (
        not isinstance(doc["page_size"], list)
        or len(doc["page_size"]) != 2
        or not all(isinstance(v, int) and v > 0 for v in doc["page_size"])
    ):
        errors.append(f"page_size must be [width, height] of positive ints, got {doc['page_size']!r}")

    seen_ids: set[str] = set()
    for i, region in enumerate(doc["regions"]):
        label = region.get("id", f"index {i}")
        if "id" not in region:
            errors.append(f"region {label} missing field: id")
        elif region["id"] in seen_ids:
            errors.append(f"duplicate region id: {region['id']}")
        else:
            seen_ids.add(region["id"])
        for field in _REGION_FIELDS:
            if field not in region:
                errors.append(f"region {label} missing field: {field}")
        bbox = region.get("bbox")
        if isinstance(bbox, dict):
            bad = [
                f for f in _BBOX_FIELDS
                if not isinstance(bbox.get(f), int) or (f in ("w", "h") and bbox.get(f, 0) <= 0)
            ]
            if bad or set(bbox) != set(_BBOX_FIELDS):
                errors.append(f"region {label} bbox malformed: {bbox!r}")
        elif "bbox" in region:
            errors.append(f"region {label} bbox must be a dict, got {type(bbox).__name__}")
        if "text" in region and not isinstance(region["text"], str):
            errors.append(f"region {label} text must be a string")
        if region.get("region_type") not in REGION_TYPES and "region_type" in region:
            errors.append(f"region {label} region_type invalid: {region['region_type']!r}")
        for field in ("detection_confidence", "ocr_confidence"):
            value = region.get(field)
            if field in region and not isinstance(value, (int, float)):
                errors.append(f"region {label} {field} must be numeric")

    stats = doc["stats"]
    if not isinstance(stats, dict) or "num_regions" not in stats:
        errors.append("stats missing num_regions")
    elif stats["num_regions"] != len(doc["regions"]):
        errors.append(
            f"stats.num_regions ({stats['num_regions']}) != len(regions) ({len(doc['regions'])})"
        )
    return errors
