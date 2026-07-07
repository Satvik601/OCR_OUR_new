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
