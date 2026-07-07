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
- **Global Otsu assumes reasonably even illumination.** Old scans with strong gradients may
  need the adaptive-threshold fallback (see CLAUDE.md decisions log). Not yet exercised.
- **Reverse text (white-on-color boxes, e.g. the red quote sidebar) inverts under
  THRESH_BINARY_INV** — those regions binarize as solid blobs, which layout detection will
  see as one region and OCR (which re-crops the original, not the binary) may still read.
  To evaluate honestly in phase 2/4.
- **No region_type classification** — everything exports as `unclassified` (schema has the
  field so downstream consumers don't break when classification lands).
- **No deskew step.** The brief's preprocessing list doesn't include one; synthetic noisy
  fixture includes mild skew to find out empirically whether it hurts layout detection.

## Resolved

(none yet)
