"""Stage 5 — structured JSON export (NOT YET IMPLEMENTED, phase 5).

Serializes detected regions + OCR results into the JSON schema defined
in ARCHITECTURE.md: region id, bounding box, extracted text, detection
confidence, OCR confidence, region type placeholder.
"""

from __future__ import annotations

from typing import Any


def build_document(
    source_image: str,
    page_size: tuple[int, int],
    regions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble the output document dict matching the ARCHITECTURE.md schema."""
    raise NotImplementedError("JSON export is phase 5; OCR must pass first")
