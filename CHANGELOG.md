# CHANGELOG.md

## [Unreleased]

### 2026-07-08 (session 2, phase 3)
- **Phase 3 filtering implemented and verified** (loop passed on iteration 5: 35 kept
  regions within the 24–36 window, zero ground-truth matches lost): area floor/ceiling +
  largest-first containment de-duplication.
- Layout display pass hardened during the phase-3 loop (root causes were in stage 2):
  component height window 26–120px, gutter split via mask-level cut. Phase 2 coverage
  improved to 83%; re-verified after every change.
- Layout review fixes: empty-image guard, closing_iterations/min_component_height
  validation, 6 new validation tests, verify-script guard.

### 2026-07-07 (session 2, phase 2)
- **Phase 2 layout detection implemented and verified** (loop passed on iteration 3,
  80% GT coverage at IoU ≥ 0.5): fine-scale morphological closing + contours, plus a
  two-scale "display pass" that isolates tall glyphs (headlines) and closes them
  separately. `newspaper_ocr/boxes.py` added (IoU/containment/greedy matching).
- Synthetic fixture generator: measured ground-truth boxes (cv2.getTextSize), realistic
  word-gap/gutter proportions; fixtures regenerated.
- `scripts/verify_layout.py`: phase-2 verification evidence generator.

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
