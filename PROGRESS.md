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
