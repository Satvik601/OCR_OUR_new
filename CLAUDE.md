# CLAUDE.md — Agent memory for the newspaper OCR project

Read this first every session, together with `PROGRESS.md`, `PHASE_VERIFICATION_LOOP.md`,
and `GITHUB_PUSH_PROTOCOL.md`. Update this file whenever a decision is made.

## What this project is

Pipeline: scanned newspaper page → article-region segmentation → per-region OCR →
structured JSON. Full brief: `fable5_project_prompt.md`. Phases run strictly in order
(preprocessing → layout → filtering → OCR → JSON export → evaluation) and each phase must
pass `PHASE_VERIFICATION_LOOP.md` **and** be committed per `GITHUB_PUSH_PROTOCOL.md`
before the next phase starts.

## How to run things

- Tests: `python -m pytest` from the repo root (Python 3.13.5, Tesseract 5.5.0 on PATH).
- CLI: `python -m newspaper_ocr.run --input <page> --output <json> [--debug-dir out/]`
- Preprocessing verification: `python scripts/verify_preprocessing.py` (writes evidence to
  `debug_output/` and prints the pass/fail metrics used by the loop).
- Regenerate synthetic fixtures: `python tests/fixtures/make_synthetic.py`

## Conventions

- All tunables live in `config.yaml`; code takes a `Config` object (`newspaper_ocr/config.py`).
  No magic numbers in stage code.
- Binary image convention: **text/ink = 255 (white), background = 0** (standard for OpenCV
  morphology). Anything consuming preprocessed output must assume this.
- `Box = (x, y, w, h)` in pixel coordinates of the ORIGINAL input image, everywhere.
- Each stage is a pure function taking (input, Config) — pluggable backends per the brief.
- Commit style: `<type>(<phase>): summary` per `GITHUB_PUSH_PROTOCOL.md`.

## Decisions log

- **2026-07-07 — real sample page:** the brief suggests a public-domain Chronicling America
  scan, but the user supplied `front_page.jpg` (mid-day, Mumbai, 2020-09-12, 1220x1490 RGB) in
  the repo root. Using it as `tests/fixtures/real_sample_page.jpg` since a user-provided page
  is the more relevant target. NOTE: this page is a modern copyrighted newspaper, not an old
  public-domain archive — fine for local testing/research, but flagged in `KNOWN_ISSUES.md`
  re: pushing to a public repo. A public-domain Chronicling America page can be added as a
  second fixture later.
- **2026-07-07 — ground truth annotation:** `real_sample_page_groundtruth.json` was annotated
  by the agent by visually reading the page (boxes accurate to roughly ±15 px). Region text is
  transcribed for headline/subhead/caption/quote regions and body columns. IoU-based criteria
  (≥0.5) tolerate this box precision.
- **2026-07-07 — git branching:** the harness requires background-session work to happen in an
  isolated worktree branch (`worktree-ocr-pipeline-build`), and forbids the agent merging to
  `main` itself. So milestone commits + tags land on the worktree branch; the user
  fast-forwards `main` and pushes when ready. `GITHUB_PUSH_PROTOCOL.md`'s "push to main" step
  is deferred accordingly. **No `origin` remote is configured yet — user must supply the repo
  URL** (also noted in the protocol file).
- **2026-07-07 — Otsu variant:** brief says "Otsu adaptive thresholding". Implemented as
  cv2.THRESH_OTSU with THRESH_BINARY_INV (global Otsu after Gaussian blur), which is what the
  classical pipeline in the source research uses. If uneven illumination on real scans breaks
  it, the fallback is adaptive Gaussian thresholding — that swap happens inside the
  preprocessing verification loop, not silently.
- **2026-07-07 — border clearing:** implemented as connected-component removal for components
  whose bbox touches within `border_margin_px` of the page edge. Known risk: a full-page frame
  rule could connect to real content; the loop on the real page checks for this.
- **2026-07-07 — ECC multi-agent setup:** the brief's agent roster is available through the
  installed `everything-claude-code` plugin (planner, architect, tdd-guide, python-reviewer,
  code-reviewer, build-error-resolver, security-reviewer, doc-updater, docs-lookup,
  loop-operator). `mle-reviewer` does not exist in the installed plugin — `code-reviewer`
  covers the evaluation-harness review instead. The phased plan itself is taken directly from
  the brief (its six stages ARE the plan); recorded in `PROGRESS.md` rather than re-derived.
- **2026-07-07 — preprocessing verification metrics** (making the loop's criteria concrete):
  - *Speckle*: connected components with area < `min_speckle_area_px` (10 px), normalized as
    speckles per megapixel; pass if < `max_speckle_per_mpx` (1500).
  - *Character loss*: per GT text region, foreground-pixel count in the preprocessed crop must
    be ≥ `min_ink_retention` (0.5) × foreground of a plain per-crop Otsu baseline; pass if
    ≤ `max_lost_region_pct` (10%) of GT regions fail. Rationale: preprocessing may legitimately
    remove some ink (specks, halftone), but losing >50% of a region's ink means characters died.
