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
| Layout | classical two-scale morphology | no | — |
| Filtering | rule-based geometry | no | — |
| OCR | Tesseract 5.5.0 via pytesseract | pretrained LSTM `eng` traineddata, official repo | Apache-2.0 |
| Evaluation | in-repo metrics (`evaluation.py`, `text_metrics.py`) | no | — |

Every stage ended up classical CV / rule-based except OCR itself (Tesseract's pretrained
LSTM, which the brief always allowed). No heavier pretrained layout model was needed to
meet the verification criteria on the test page; the pluggable interfaces remain if one
is ever compared.

## Preprocessing detail (stage 1)

1. Grayscale conversion (`cv2.cvtColor`)
2. Gaussian blur, `preprocessing.gaussian_kernel` (halftone/denoise smoothing)
3. Thresholding, inverted so ink becomes white — `preprocessing.threshold_method`:
   `otsu` (global), `adaptive` (local Gaussian), or `otsu+adaptive` (union, default).
   The union exists because global Otsu alone lost small body text on the real test
   page (verification loop iters 1–3; see CLAUDE.md decisions log).
4. Morphological opening, `preprocessing.morph_open_kernel` (speck/dust removal)
5. Border clearing: connected components whose bounding box touches within
   `preprocessing.border_margin_px` of any page edge are removed (scanner edge artifacts)

Output convention: `uint8`, ink = 255, background = 0.

## Layout detection detail (stage 2)

Two passes over the binary page, boxes unioned (`newspaper_ocr/layout.py`):

1. **Fine pass** — horizontal closing (`layout.horizontal_dilate_kernel`, connects words
   into lines; must stay below the column-gutter width), vertical closing
   (`layout.vertical_dilate_kernel`, merges lines into blocks), square closing, then
   external contours → boxes.
2. **Display pass** (`layout.display_pass`) — only connected components with height in
   [`min_component_height`, `max_component_height`] (headline/masthead glyphs; the upper
   bound keeps photo blobs out) enter a separate mask that is closed aggressively; body
   text isn't in the mask so nothing else fuses. Solves the "one vertical kernel can't
   merge headline lines without fusing distinct regions" problem. Because the horizontal
   closing must bridge headline word gaps (wider than column gutters), display boxes can
   chain across columns — boxes taller than one display line are split at near-inkless
   vertical bands of the original binary (mask-level cut + contour re-extraction).

The union intentionally contains nested/duplicate boxes; stage 3 removes them. Shared box
math (IoU, containment, greedy matching) lives in `newspaper_ocr/boxes.py`.

## OCR detail (stage 4)

`ocr_region` crops come from the ORIGINAL image (never the binary), get a 2x bicubic
upscale, then Tesseract with `--psm 6 --oem 1` via pytesseract `image_to_data`. Words
below `ocr.min_word_confidence` are dropped; results shorter than `ocr.min_text_chars`
collapse to empty text, which the pipeline treats as "no text here" (that is how photo
regions fall out of the final document). Results are cached by SHA-256 of crop bytes +
parameters under `ocr.cache_dir` (gitignored) — delete the directory to invalidate.

## Filtering detail (stage 3)

`filter_regions` (geometry only — garbage-text filtering happens post-OCR in stage 4):
1. Area floor `filtering.min_area_px` and ceiling `max_area_ratio` × page area.
2. Containment de-duplication, largest-first: a box ≥ `containment_threshold` inside an
   already-kept larger box is a nested duplicate and is dropped.

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
      "detection_confidence": "float 0-1 — currently the region's ink density in the binarized page (weak proxy until a learned detector exists)",
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
