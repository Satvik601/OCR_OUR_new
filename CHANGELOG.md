# CHANGELOG.md

## [Unreleased]

### 2026-07-07 (session 2, continued)
- Test fixtures: synthetic simple/noisy pages (seeded generator), real sample page,
  hand-annotated ground truth (30 regions, 4 articles).
- **Phase 1 preprocessing implemented and verified** (loop passed on iteration 3):
  grayscale → Gaussian(3) → Otsu ∪ adaptive-Gaussian threshold → 3x3 opening → border
  clearing. `threshold_method` config option added after global-Otsu-only failed the loop.
- `scripts/verify_preprocessing.py`: phase-1 verification evidence generator.

### 2026-07-07 (session 2)
- Repository skeleton: `newspaper_ocr/` package (config loader, stage modules with
  contracts, CLI entry point), `config.yaml` with all tunables + verification thresholds.
- Nine documentation/memory files created with real initial content.
- Default branch set to `main`; root commit `e9fe378` (brief, protocols, requirements,
  sample page).

### 2026-07-07 (session 1)
- Project brief saved (`fable5_project_prompt.md`), `PHASE_VERIFICATION_LOOP.md` saved
  as provided, `GITHUB_PUSH_PROTOCOL.md` drafted (original not provided — flagged),
  `requirements.txt` pinned against the dev machine, `.gitignore` created.
