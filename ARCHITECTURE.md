# Architecture

## Data flow

```
                    original BGR image ──────────────────────────┐
                          │                                      │ (crops come from the
                          ▼                                      │  ORIGINAL image, not
   [1] preprocessing → binary page (ink=255, bg=0)               │  the binarized one)
                          │                                      │
                          ▼                                      │
   [2] layout        → candidate boxes [(x,y,w,h), ...]          │
                          │                                      │
                          ▼                                      │
   [3] filtering     → kept boxes                                │
                          │                                      │
                          ▼                                      ▼
   [4] ocr           → per-box: crop original → 2x bicubic → Tesseract PSM 6 / OEM 1
                          │
                          ▼
   [5] export        → structured JSON document
                          │
                          ▼
   [6] evaluation    → precision / recall / word accuracy vs. ground truth
```

## Module responsibilities

| Module | Stage | Contract |
|---|---|---|
| `newspaper_ocr/preprocessing.py` | 1 | `preprocess(bgr_image, config) -> binary uint8 {0,255}, ink=255` |
| `newspaper_ocr/layout.py` | 2 | `detect_regions(binary, config) -> list[Box]`, `Box=(x,y,w,h)` |
| `newspaper_ocr/filtering.py` | 3 | `filter_regions(boxes, page_shape, config) -> list[Box]` |
| `newspaper_ocr/ocr.py` | 4 | `ocr_region(original_crop, config) -> OcrResult(text, confidence)` |
| `newspaper_ocr/export.py` | 5 | `build_document(...) -> dict` matching the schema below |
| `newspaper_ocr/evaluation.py` | 6 | `evaluate(result_doc, ground_truth) -> metrics dict` |
| `newspaper_ocr/config.py` | — | loads `config.yaml`; all tunables live there |
| `newspaper_ocr/run.py` | — | CLI orchestration of stages 1–5 |

Every stage is a pure function of (input, Config) so backends are swappable — e.g. the
classical morphology layout detector can be compared side-by-side against a pretrained
layout model under identical verification criteria. Which backend won per stage, and why,
gets recorded here when a comparison happens.

### Stage backends currently in use

| Stage | Backend | External model? | License |
|---|---|---|---|
| Preprocessing | classical CV (OpenCV) | no | Apache-2.0 (opencv-python) |
| Layout | classical morphology (planned) | no | — |
| Filtering | rule-based (planned) | no | — |
| OCR | Tesseract 5.5.0 via pytesseract (planned) | pretrained LSTM `eng` traineddata, official repo | Apache-2.0 |
| Evaluation | in-repo metrics (planned) | no | — |

## Preprocessing detail (stage 1)

1. Grayscale conversion (`cv2.cvtColor`)
2. Gaussian blur, `preprocessing.gaussian_kernel` (halftone/denoise smoothing)
3. Otsu global threshold, inverted (`THRESH_BINARY_INV | THRESH_OTSU`) → ink becomes white
4. Morphological opening, `preprocessing.morph_open_kernel` (speck/dust removal)
5. Border clearing: connected components whose bounding box touches within
   `preprocessing.border_margin_px` of any page edge are removed (scanner edge artifacts)

Output convention: `uint8`, ink = 255, background = 0.

## Output JSON schema (stage 5 target)

```json
{
  "source_image": "str — input path as given",
  "page_size": "[width, height] of the input image in px",
  "processed_at": "ISO-8601 timestamp",
  "pipeline_version": "newspaper_ocr.__version__",
  "regions": [
    {
      "id": "str — r001, r002, ... stable within a document",
      "bbox": {"x": "int", "y": "int", "w": "int", "h": "int"},
      "text": "str — OCR output, post-filtered",
      "detection_confidence": "float 0-1 — layout stage confidence signal",
      "ocr_confidence": "float 0-100 — mean Tesseract word confidence, -1 if unavailable",
      "region_type": "headline | body | caption | masthead | quote | other | unclassified"
    }
  ],
  "stats": {
    "num_regions": "int",
    "num_regions_dropped_by_filtering": "int"
  }
}
```

`region_type` is a placeholder for now — everything is exported `unclassified` until a
classification step exists (see `KNOWN_ISSUES.md`).

## Ground truth format (evaluation input)

`tests/fixtures/real_sample_page_groundtruth.json`: same `bbox` convention, plus
`region_type`, `article_id` (grouping regions into articles), and `text` per region.
Metrics: region precision/recall at IoU ≥ 0.5, word accuracy on matched regions,
fragmentation rate = detected boxes per matched GT region.
