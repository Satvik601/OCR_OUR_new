# PROGRESS.md — append-only milestone log

## 2026-07-07 — project start

Phased plan (from the brief; each phase gated by PHASE_VERIFICATION_LOOP.md + push protocol):

1. Repo scaffolding + docs + test fixtures ← this session
2. Phase 1: Preprocessing ← this session
3. Phase 2: Layout detection
4. Phase 3: Filtering
5. Phase 4: Per-region OCR
6. Phase 5: JSON export (+ full-pipeline integration test)
7. Phase 6: Evaluation harness (precision/recall/word accuracy vs. ground truth)

Environment verified: Python 3.13.5, Tesseract 5.5.0, opencv-python 4.12.0, numpy 2.1.3.

## 2026-07-07 — milestone: initial scaffolding (commit e9fe378 on main)

Brief, protocol files, pinned `requirements.txt`, `.gitignore`, user-supplied real sample
page committed as the root commit. Local-only (no `origin` configured yet — awaiting repo
URL from the user; see GITHUB_PUSH_PROTOCOL.md preconditions).

Work continues on branch `worktree-ocr-pipeline-build` (harness-mandated isolation; user
fast-forwards `main` when ready — see CLAUDE.md decisions log).

## 2026-07-07 — milestone: test fixtures (commit d3b6cce)

- `tests/fixtures/`: seeded synthetic generator + `synthetic_simple.png`,
  `synthetic_noisy.png`, `synthetic_layout.json`; `real_sample_page.jpg` (user-supplied
  mid-day 2020-09-12 page, 1220x1490); `real_sample_page_groundtruth.json` — 30 regions,
  4 articles, boxes + types + article grouping + transcribed text.
- Annotation verified visually with a box overlay rendered on the page; 4 boxes adjusted
  after inspection (gt10, gt19, gt25, gt26 bottom edges).

## 2026-07-07 — milestone: PHASE 1 PREPROCESSING — verification loop PASSED

Verification per PHASE_VERIFICATION_LOOP.md, real input `tests/fixtures/real_sample_page.jpg`:

| Loop iter | Change tested | Speckle (/Mpx, limit 1500) | Text regions lost (limit 10%) | Result |
|---|---|---|---|---|
| 1 | global Otsu, gaussian 5 | 150 → pass | 10/25 = 40% | **FAIL** — small body text wiped |
| 2 | gaussian 5→3 | 172 → pass | 11/25 = 44% | **FAIL** — global threshold is the cause, not blur |
| 3 | threshold_method otsu+adaptive (union) | 327 → pass | 0/25 = 0% | **PASS** |

- Unit tests: 8/8 passed (`tests/test_preprocessing.py`) — binary contract, ink=white
  convention, text-block survival on clean + noisy synthetic, speckle limit, border
  clearing, input immutability.
- Visual inspection of `debug_output/01_preprocessed_real.png`: headlines crisp, all body
  columns readable, page-edge rules cleared, worst region retention 0.58 (gt18).
- Code reviewed by python-reviewer agent before completion. Findings (2 HIGH, 2 MEDIUM,
  1 LOW — all input-contract validation, no logic bugs) fixed and covered by 6 new tests:
  odd/positive kernel + block-size validation with config-key names in errors, uint8 dtype
  check, (H,W,1) single-channel handling, morph_open_kernel>=1 guard, docstring sync.
  Test suite after fixes: 14/14 passed; verification loop re-run: PASS.
- Security review note: deferred to the phases with actual attack surface (CLI/OCR
  subprocess in phase 4+) — recorded in CLAUDE.md decisions log.
- Commit `199218b`, tag `v0.1-preprocessing`, on branch `worktree-ocr-pipeline-build`.
  Local-only: no `origin` remote configured yet — push happens retroactively
  (`git push --follow-tags origin main`) once the user supplies the repo URL.
- Post-review cleanups in `b5c9f0e` (reviewer verdict: Approve).

## 2026-07-07 — milestone: PHASE 2 LAYOUT DETECTION — verification loop PASSED

User instructed to continue phases with push still pending (see CLAUDE.md decisions log).
Verification per PHASE_VERIFICATION_LOOP.md, real input `real_sample_page.jpg`,
criterion: ≥80% of GT regions matched at IoU ≥ 0.5:

| Loop iter | Change tested | Coverage | Result |
|---|---|---|---|
| 1 | brief's kernels [40,1]/[1,20] | 1/30 = 3% (page merged into 1 box) | **FAIL** |
| 2 | kernels [10,1]/[1,8]/[9,9] + line-merge post-pass | 17/30 = 57% (merge pass over-merged) | **FAIL** |
| 3 | line-merge replaced with two-scale display pass (components ≥26px tall closed separately at [60,1]/[1,20]) | **24/30 = 80%** | **PASS** |
| 4* | display-pass hardening driven by the phase-3 loop: component height cap (≤120px keeps photo blobs out) + gutter split of chained boxes (mask-level cut + contour re-extraction) | **25/30 = 83%** | **PASS** |

(*) iteration 4 changes were made while phase 3's loop exposed display-pass over-merge
artifacts; phase 2 was re-verified after every change and never regressed below 80%.

- Diagnosis between iterations used parameter sweeps against ground truth (documented in
  TESTING.md); the two-scale approach is still pure classical CV.
- Unit tests: 27/27 (incl. new test_boxes.py: IoU/containment/greedy matching; test_layout.py:
  block recovery, column separation, fragmentation cap, blank page, bounds).
- Synthetic fixture generator corrected during the loop: measured (getTextSize) ground-truth
  boxes instead of estimates; realistic word-gap-to-gutter proportions.
- Visual inspection of `debug_output/02_layout_real.png`: all major regions boxed; the 6
  unmatched GT regions are hard cases logged in KNOWN_ISSUES.md (masthead-fused dateline,
  two multi-line headlines, three fused small blocks bottom-right).
- Detected boxes include word-level duplicates inside display regions — stage-3
  filtering's job (containment removal), per ARCHITECTURE.md staging.
- Code reviewed by python-reviewer agent (1 HIGH: empty-image validation gap; 2 MEDIUM:
  unvalidated closing_iterations/min_component_height, missing validation tests; 2 LOW).
  All fixed; 6 new tests. Reviewer confirmed boxes.py math, greedy matching, and
  no-mutation properties empirically.
- Final state: 25/30 = 83% coverage, 41/41 tests, verify_layout PASS.
- Commit + tag: recorded below after push protocol step.

## 2026-07-08 — milestone: PHASE 3 FILTERING — verification loop PASSED

Criteria (see CLAUDE.md decisions log for the "article count" → region-count
interpretation): kept-box count within ±20% of GT region count (24–36), and no GT region
matched before filtering may lose its match after.

| Loop iter | Change tested | Kept | Lost matches | Result |
|---|---|---|---|---|
| 1 | area floor 500 + containment 0.85, largest-first | 14 | 16 | **FAIL** — display-pass mega-boxes absorbed real regions |
| 2 | display-pass component height cap ≤120 (photo blobs out) + box-level gutter split | 38 | 3 | **FAIL** — split kept union's y-extent |
| 3 | split guard for single-line boxes (fixed synthetic regression) | 38 | 3 | **FAIL** — same 3 absorbed |
| 4 | mask-level gutter cut + contour re-extraction | 39 | **0** | **FAIL** — count 39 > 36 |
| 5 | min_area_px 500 → 4000 (smallest real GT region is ~7200 px²) | **35** | **0** | **PASS** |

- Iterations 2–4's fixes live in the layout stage (root cause was there); phase 2 was
  re-verified after each change (never below 80%, ended at 83%).
- Unit tests: 41/41 (test_filtering.py: area floor/ceiling, nesting, dedupe, disjoint
  survival, partial-overlap protection, stages-1-3 end-to-end on synthetic).
- Visual inspection of `debug_output/03_filtering_real.png`: kept boxes map to real
  regions; dropped boxes are word fragments and nested duplicates.
- Commit + tag: recorded below after push protocol step.
