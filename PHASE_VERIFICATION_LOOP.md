# Phase Verification Loop Protocol

This file defines a mandatory loop Fable 5 must follow for every phase of the project. Do not advance to the next phase until the current phase passes verification against real input. Read this file at the start of every session, alongside `CLAUDE.md` and `PROGRESS.md`.

## The Loop

For each phase (Preprocessing → Layout Detection → Filtering → OCR → JSON Export → Evaluation), repeat this cycle until it passes:

1. **Run** the current phase's code on the designated test input (see "Test Inputs" below).
2. **Capture** the actual output — not a description of what you expect it to do, the real output (image, bounding boxes, JSON, whatever the phase produces).
3. **Compare** the output against the phase's defined "desired output" (see table below).
4. **Judge pass/fail** using the concrete criteria in the table — not a general impression.
5. **If it passes:** log the result with evidence in `PROGRESS.md` and `TESTING.md`, then move to the next phase.
6. **If it fails:** diagnose the likely cause, make a targeted code/parameter change in the current phase only, and go back to step 1. Do not touch later phases while a current phase is failing.
7. **Cap:** if a phase fails 5 verification cycles in a row, stop looping blindly. Instead, write up the failure pattern in `KNOWN_ISSUES.md` (what you tried, what happened each time, your best hypothesis for the root cause) and flag it to me for input before continuing.

Never report a phase as "done" without having gone through at least one full pass of this loop with visible evidence.

## Test Inputs

Maintain a small fixed set of test inputs in `tests/fixtures/`:

- `synthetic_simple.png` — a generated test image with clean, well-separated text blocks (for fast unit-level checks).
- `synthetic_noisy.png` — a generated test image with added noise/skew/uneven lighting (to stress-test preprocessing).
- `real_sample_page.jpg` — one real public-domain scanned newspaper page (e.g., from Chronicling America or Newspaper Navigator), used for every phase's real-world check.
- `real_sample_page_groundtruth.json` — hand-annotated ground truth for `real_sample_page.jpg`: correct region boxes, correct text per region, article count.

Use the synthetic images for quick iteration and `real_sample_page.jpg` as the final check before a phase is marked passed — a phase isn't done until it passes on the real page, not just the synthetic ones.

## Desired Output & Pass Criteria Per Phase

| Phase | Desired Output | Pass Criteria (must verify against real input) |
|---|---|---|
| Preprocessing | Clean binarized image: text visibly separated from background, minimal speckle noise, no lost characters | Visually inspect output image (save it, view it); speckle count below threshold defined in `config.yaml`; no more than X% of ground-truth text regions show visible character loss |
| Layout Detection | Bounding boxes roughly matching real article/column boundaries on the test page | At least 80% of ground-truth article regions have a detected bounding box with IoU ≥ 0.5 against ground truth |
| Filtering | Noise regions and duplicate/nested boxes removed, real article regions kept | Region count after filtering is within ±20% of ground-truth article count; no ground-truth article region is dropped |
| OCR | Extracted text per region readable and mostly correct | Word accuracy ≥ threshold defined in `config.yaml` (start at 70%, revisit as you tune) against ground-truth text per region |
| JSON Export | Valid JSON matching the schema in `ARCHITECTURE.md` | JSON validates against schema; every detected region present with required fields; no malformed entries |
| Evaluation | Precision/recall/word-accuracy numbers computed and logged | Script runs end-to-end on `real_sample_page.jpg` and produces numeric metrics without errors |

If a criterion in this table turns out to be unrealistic once you start testing (e.g., 80% IoU is too strict for this classical CV approach), don't silently lower it — flag it, propose a revised number with reasoning, and record the change with justification in `CLAUDE.md`.

## What Counts as "Making Corrections" (step 6)

When a phase fails, a correction is a real, targeted change such as:
- Adjusting a kernel size, threshold, or parameter in `config.yaml`
- Fixing a bug in the stage's logic
- Adding a missing filtering rule
- Adjusting preprocessing order

A correction is **not**:
- Loosening the pass criteria to make a failing result pass
- Skipping the real test image and only testing on synthetic images
- Marking the phase done and noting it "needs more work later"

## Session Report Format

At the end of every session, report using this exact structure so progress is auditable:

```
Phase: <name>
Loop iteration: <n>
Test input used: <filename>
Actual output: <paste or summarize with evidence, e.g. saved file path + key numbers>
Pass criteria: <restate from table>
Result: PASS / FAIL
If FAIL: cause hypothesis + correction made + next test planned
If PASS: evidence logged in PROGRESS.md and TESTING.md, next phase: <name>
```
