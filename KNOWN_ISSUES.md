# KNOWN_ISSUES.md — honest list of limitations, edge cases, TODOs

## Open

- **No `origin` remote.** Commits and tags are local-only until the user supplies the
  GitHub repo URL (GITHUB_PUSH_PROTOCOL.md precondition).
- **Real sample page is copyrighted.** `front_page.jpg` / `tests/fixtures/real_sample_page.jpg`
  is a 2020 mid-day (Mumbai) front page supplied by the user — not a public-domain archive
  scan. Fine for local testing; **review before pushing to a public repo.** A public-domain
  Chronicling America page should be added as a second real fixture.
- **Real page is modern, not an old archive.** The brief targets old newspaper archives
  (yellowed paper, letterpress, halftone noise). The current real fixture is a clean modern
  color page — it stresses layout complexity (photos, colored boxes, reverse text) but not
  degradation. Tuning may skew toward modern pages until an archival page fixture is added.
- **Ground truth boxes are agent-annotated (~±15 px)** by visually reading the page, and body
  text for two long columns is transcribed from the visible portion only. Good enough for
  IoU ≥ 0.5 metrics; not pixel-perfect.
- **Border clearing can eat content connected to page-edge rules.** If a frame line touches
  both the page edge and a text component, that component gets cleared. Watched for in the
  preprocessing loop on the real page; mitigation (max component size for clearing) not yet
  implemented.
- **Adaptive threshold outlines photo halftones.** The `otsu+adaptive` union (adopted in
  loop iter 3) more than doubles connected components (1491 → 3485) because photos become
  edge texture. Layout detection (phase 2) must merge/ignore these; if they fragment layout
  boxes, revisit (e.g. texture masking) — tracked for phase 2.
- **Small body text binarizes thin/broken at this resolution** (worst GT region retention
  0.58). Fine for layout detection; OCR (phase 4) crops the ORIGINAL image, not this binary,
  so OCR quality is unaffected by this — but verify in phase 4.
- **Reverse text (white-on-color boxes, e.g. the red quote sidebar) inverts under
  THRESH_BINARY_INV** — those regions binarize as solid blobs, which layout detection will
  see as one region and OCR (which re-crops the original, not the binary) may still read.
  To evaluate honestly in phase 2/4.
- **Layout: 5/30 GT regions unmatched at IoU 0.5 (coverage 83%, floor is 80%).**
  Residual hard cases on the real page: (a) gt02 dateline strip fuses into the masthead
  (descender of "mid-day" touches it); (b) gt18, gt28, gt29, gt30 small caption/photo/number
  blocks fuse with neighbors in the dense bottom-right corners. Multi-line headlines (gt10,
  gt25) were fixed by the display pass + gutter split. Ideas if this needs to improve:
  whitespace-aware row splitting, or a pretrained layout model as an alternative backend
  (brief allows it, interface is pluggable).
- **Layout emits duplicate/nested boxes by design** (fine pass + display pass overlap, word
  fragments inside display regions): 110 boxes vs 30 GT regions on the real page. Stage 3
  (filtering) owns containment de-duplication — do not tune layout to hide this.
- **`filtering.min_area_px` is absolute pixels (4000), so it's resolution-dependent.**
  Correct for the 1220x1490 test page (smallest real region ~7200 px²); a much
  higher-resolution scan would need this scaled (or made relative to page area).
- **No region_type classification** — everything exports as `unclassified` (schema has the
  field so downstream consumers don't break when classification lands).
- **No deskew step.** The brief's preprocessing list doesn't include one; synthetic noisy
  fixture includes mild skew to find out empirically whether it hurts layout detection.

- **`types-PyYAML` not installed** — `mypy` flags `import yaml` as untyped. mypy is not
  (yet) part of the project toolchain; if it gets added to CI, add `types-PyYAML` to the
  dev dependencies.

## Resolved

- ~~Global Otsu loses small body text on pages with heavy dark masses~~ — fixed in phase 1
  loop iter 3 via `threshold_method: otsu+adaptive` (see CLAUDE.md decisions log).
