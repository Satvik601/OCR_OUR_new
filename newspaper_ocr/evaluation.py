"""Stage 6 — evaluation against hand-annotated ground truth (NOT YET IMPLEMENTED, phase 6).

Computes region precision/recall (IoU-matched against
tests/fixtures/real_sample_page_groundtruth.json), word accuracy per
matched region, and fragmentation rate (detected regions per ground-truth
region).
"""

from __future__ import annotations

from typing import Any


def evaluate(result_doc: dict[str, Any], ground_truth: dict[str, Any]) -> dict[str, float]:
    """Compare a pipeline output document against ground truth; return metrics."""
    raise NotImplementedError("evaluation is phase 6; JSON export must pass first")
