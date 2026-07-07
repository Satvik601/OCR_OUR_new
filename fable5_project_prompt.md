# Project Prompt for Claude Fable 5

Copy everything below into your first message to Fable 5 (ideally in an agentic coding environment like Claude Code, so it can create files, run code, and iterate across sessions).

---

## PROMPT START

You are building a complete, working software project from scratch. Treat this as a real multi-session engineering effort, not a one-shot script. Read this entire brief before writing any code.

### Project

**Title:** Object Detection and OCR-Based Segmentation of Old Newspaper Archives for Structured Database Creation

**Objective:** Build a pipeline that takes a scanned image of an old newspaper page and produces a structured, machine-readable JSON output containing individual article regions and their extracted text — instead of one flat blob of OCR text. The system should preserve article boundaries so the output is usable for search, indexing, and historical text analysis.

**Design constraints (from the original research brief):**
- The baseline approach uses classical computer vision techniques for layout detection to keep the system lightweight and runnable on limited compute. Open-source pretrained tools/models (see "External tools and models" section below) may be substituted at any stage if they perform better — this is a permitted deviation from the original brief, not a violation of it, as long as the tradeoffs are documented.
- OCR should run per-region, not on the whole page, to avoid layout confusion.
- Output must be structured JSON (article regions + extracted text + bounding boxes + confidence/quality signals).

### Required Pipeline Stages

1. **Preprocessing**
   - Grayscale conversion
   - Gaussian blur (denoise / smooth halftone patterns)
   - Otsu adaptive thresholding
   - Morphological opening (remove specks/dust)
   - Border clearing (remove scanner edge artifacts)

2. **Layout Detection**
   - Horizontal dilation to connect characters into lines
   - Vertical dilation to merge lines into paragraph-sized blocks
   - Morphological closing to fill gaps
   - Contour detection to extract bounding boxes for candidate article regions

3. **Filtering**
   - Area thresholds to discard tiny noise regions
   - Containment filtering to remove nested/duplicate boxes
   - Garbage-text filtering for incoherent OCR outputs

4. **OCR Processing**
   - Crop each region from the original high-resolution (non-binarized) image
   - 2x bicubic upscaling before OCR
   - Tesseract with Page Segmentation Mode 6 (single uniform block), LSTM engine
   - Post-OCR filtering of very short/incoherent text

5. **Structured Output**
   - JSON schema with: region id, bounding box coordinates, extracted text, detection confidence, OCR confidence, region type placeholder (headline/body/caption — even if unclassified for now)

6. **Evaluation**
   - Report number of detected regions, major articles found, fragmentation rate
   - Precision/recall/word-accuracy scaffolding against at least one manually annotated test page (see Testing section)

### What I need you to build

**A. Working codebase**
- Modular Python package (e.g., `newspaper_ocr/`) with separate modules for preprocessing, layout detection, filtering, OCR, and JSON export — matching the stages above.
- A CLI entry point: `python -m newspaper_ocr.run --input page.jpg --output result.json`
- `requirements.txt` with pinned versions (opencv-python, pytesseract, numpy, Pillow, etc.)
- Config file (e.g., `config.yaml`) for tunable parameters (kernel sizes, area thresholds, PSM mode) instead of hardcoded magic numbers.

**B. Testing**
- Unit tests for each pipeline stage (pytest), using small synthetic test images so tests don't depend on external files.
- At least one integration test that runs the full pipeline end-to-end on a sample image and checks the JSON output is well-formed and non-empty.
- A manual evaluation script that computes precision/recall/word accuracy against a hand-annotated ground-truth JSON for a real sample newspaper page (use a public-domain scan, e.g., from Library of Congress "Newspaper Navigator" or Chronicling America).
- Run the full test suite and show me the results before considering any milestone "done."

**C. Self-review before reporting progress**
Before telling me a stage is complete, you must:
1. Run the tests and paste the actual output (not a summary).
2. Check the code against the design constraints above (classical CV only, per-region OCR, structured JSON).
3. Identify at least one weakness or edge case you haven't handled yet, and log it in `KNOWN_ISSUES.md`.
4. Only then mark the task complete in `PROGRESS.md`.

**D. Documentation and memory files** (create these at project start, keep them updated every session)

| File | Purpose |
|---|---|
| `CLAUDE.md` | Persistent memory/instructions for you (the agent) across sessions: project conventions, coding style, how to run tests, what's already decided and why. Read this first every session; update it whenever a decision is made. |
| `README.md` | Human-facing overview: what the project does, setup instructions, how to run the CLI, example input/output. |
| `ARCHITECTURE.md` | Explanation of the pipeline stages, module responsibilities, data flow, and the JSON schema. |
| `PROGRESS.md` | Running log of completed milestones, dated, with test results referenced. Append-only. |
| `KNOWN_ISSUES.md` | Honest list of limitations, edge cases, and TODOs (e.g., fragmentation on narrow columns, no semantic labeling yet). |
| `TESTING.md` | What is tested, how to run tests, how the evaluation metrics are computed, and current metric values. |
| `CHANGELOG.md` | Version-style log of what changed between sessions. |
| `PHASE_VERIFICATION_LOOP.md` | The mandatory test-verify-correct loop you must run for every phase before advancing. Provided separately below — copy it into the repo as-is and follow it exactly. |
| `GITHUB_PUSH_PROTOCOL.md` | What to do with version control once a phase passes verification: commit, push, tag. Provided separately below — copy it into the repo as-is and follow it exactly. |

### Mandatory phase verification loop

You must not advance from one phase to the next just because the code runs without errors. For every phase (preprocessing, layout detection, filtering, OCR, JSON export, evaluation), you are required to:

1. Run the phase's code on a real test input.
2. Check the actual output against a concrete "desired output" definition for that phase.
3. If it matches → log evidence and move to the next phase.
4. If it doesn't match → make a targeted correction to the current phase only, then re-test. Repeat this loop until it passes (or you hit 5 failed attempts, at which point stop and flag it to me with your findings instead of continuing to guess).

The full protocol — desired-output definitions per phase, pass criteria, test input requirements, and the exact report format to use — is in `PHASE_VERIFICATION_LOOP.md` (provided as a separate file below this prompt). Read it in full before starting, save it into the repo root, and treat it as binding for every phase, not just the first one.

A phase passing the loop above is not the end of the phase. Once a phase passes, follow `GITHUB_PUSH_PROTOCOL.md` (also provided as a separate file below this prompt, save it into the repo root) to commit, push, and tag the milestone before reporting the phase complete and moving on. A phase is only truly "done" once it has passed verification **and** been pushed.

### Working style I expect from you

- Work in small, verifiable increments: preprocessing → layout detection → filtering → OCR → JSON export → evaluation. Don't jump ahead to later stages before earlier ones are tested, verified against real input per the loop above, and confirmed working.
- At the start of every session, read `CLAUDE.md`, `PROGRESS.md`, `PHASE_VERIFICATION_LOOP.md`, and `GITHUB_PUSH_PROTOCOL.md` before doing anything else, so you don't repeat or contradict earlier decisions, skip the verification loop, or forget to push.
- If you hit a design ambiguity (e.g., how to handle overlapping bounding boxes), state your assumption explicitly in `CLAUDE.md` rather than silently picking one.
- Never claim something works without having actually run it, tested it against real input, and shown me the output.
- Never claim a phase is complete without having committed and pushed it per `GITHUB_PUSH_PROTOCOL.md` — a passing test suite that hasn't been pushed is still in progress.
- When you finish a milestone, report using the exact session report format defined in `PHASE_VERIFICATION_LOOP.md`, extended with the commit/push lines from `GITHUB_PUSH_PROTOCOL.md`.

### Multi-agent setup (ECC)

Before starting, install and use the following from the ECC agent-harness plugin (github.com/affaan-m/ECC) so this project is worked on by multiple specialized agents rather than a single generalist pass. Install only the selective subset below — not the full plugin.

**Agents to install and delegate to:**

| Agent | Use it for |
|---|---|
| `planner` | Turning this brief into the phased implementation plan at the start |
| `architect` | Sanity-checking module boundaries before coding each phase |
| `tdd-guide` | Enforcing write-tests-first for every phase |
| `python-reviewer` | Reviewing each phase's code for Python-specific issues |
| `code-reviewer` | A broader quality/security pass across the repo |
| `build-error-resolver` | Fixing dependency/import errors (opencv-python, pytesseract, etc.) |
| `security-reviewer` | One pass before any phase is marked done |
| `doc-updater` | Keeping `README.md` / `ARCHITECTURE.md` in sync as code changes |
| `docs-lookup` | Looking up OpenCV/Tesseract API details instead of guessing signatures |
| `mle-reviewer` | Reviewing the evaluation harness (precision/recall/word accuracy) for rigor |
| `loop-operator` | Executing `PHASE_VERIFICATION_LOOP.md` autonomously without needing a re-prompt each cycle |

**Skills to install and apply:**

- `verification-loop` — reinforces the same test → verify → correct discipline as `PHASE_VERIFICATION_LOOP.md`
- `eval-harness` — structured pattern for the precision/recall/word-accuracy step
- `tdd-workflow` — TDD methodology per phase
- `python-patterns`, `python-testing` — Python idioms and pytest patterns
- `search-first` — research the correct OpenCV/Tesseract parameters before using them, rather than guessing
- `content-hash-cache-pattern` — avoid re-running OCR on unchanged pages during iteration
- `continuous-learning-v2` — extracts and retains lessons learned across sessions; this is additional cross-session memory on top of `CLAUDE.md`
- `docs/examples/project-guidelines-template.md` — use as the starting skeleton for `CLAUDE.md` instead of writing it unstructured

**Orchestration commands:**

- `/ecc:plan` — generate the phased plan first
- `/multi-plan` and `/multi-execute` — decompose phases across multiple agents and run them in parallel where phases don't depend on each other (note: requires `npx ccg-workflow` running first)
- `/quality-gate` — the verification gate between phases, paired with `PHASE_VERIFICATION_LOOP.md`
- `/checkpoint` — save verification evidence at each pass (this is the loop's "log evidence" step)
- `/learn-eval` — extract and save patterns/instincts after each session

**How agents map onto phases:**

For each pipeline phase, use `planner` to scope the phase, implement with `tdd-guide` driving test-first development, hand off to `python-reviewer` and `code-reviewer` for review, run the phase through `loop-operator` against `PHASE_VERIFICATION_LOOP.md`, and only after it passes, use `doc-updater` to update the documentation files and `/learn-eval` to record what was learned before moving to the next phase. Use `/multi-plan` + `/multi-execute` only for independent workstreams (e.g., building test fixtures while also scaffolding the CLI) — keep the sequential preprocessing → layout → filtering → OCR → JSON → evaluation order strictly sequential since each phase depends on the last.

Install command reference (adjust paths to your environment):
```bash
git clone https://github.com/affaan-m/ECC.git
cd ECC
mkdir -p ~/.claude/agents ~/.claude/skills ~/.claude/rules/ecc
cp agents/planner.md agents/architect.md agents/tdd-guide.md agents/python-reviewer.md \
   agents/code-reviewer.md agents/build-error-resolver.md agents/security-reviewer.md \
   agents/doc-updater.md agents/docs-lookup.md agents/mle-reviewer.md agents/loop-operator.md \
   ~/.claude/agents/
cp -r skills/verification-loop skills/eval-harness skills/tdd-workflow \
      skills/python-patterns skills/python-testing skills/search-first \
      skills/content-hash-cache-pattern skills/continuous-learning-v2 \
      ~/.claude/skills/
cp -r rules/common rules/python ~/.claude/rules/ecc/
```

### External tools and models

You are allowed to use open-source tools and pretrained models from public sources (Hugging Face, PaddleOCR, EasyOCR, docTR, LayoutParser, Detectron2, and similar, in addition to Tesseract) for **any** stage of the pipeline — preprocessing, layout detection, filtering, OCR, or evaluation — not just OCR. This supersedes the earlier "layout detection stays classical CV" constraint from the original brief: if a pretrained layout model or other open-source tool genuinely does the job better, you may use it, subject to the rules below.

If you introduce an external tool or model at any stage:

- State the reason in `CLAUDE.md` before switching — don't swap silently mid-project.
- Check and record the license in `ARCHITECTURE.md` (must be permissive enough for the intended use — flag anything GPL/non-commercial to me before adopting it).
- Note the compute/size tradeoff against the original goal of staying lightweight and running on limited resources. If a heavier model gives a real accuracy gain, say so explicitly and let me weigh in before making it the default for that stage.
- Run it through the exact same `PHASE_VERIFICATION_LOOP.md` criteria for that stage as the classical/baseline approach — no exceptions just because it's a fancier model.
- Keep each stage's interface pluggable (preprocessing, layout detection, and OCR should each accept a swappable backend) so we can compare results side by side — e.g. classical morphology vs. a pretrained layout model — and keep whichever wins per `TESTING.md`, rather than hardcoding one approach per stage.
- Downloading a model or tool from an untrusted or unofficial mirror is not okay — stick to official Hugging Face model pages, the tool's own GitHub repo, or PyPI/npm registries.

Document which stages ended up using classical CV vs. an external pretrained tool, and why, in `ARCHITECTURE.md` — this project's value partly comes from being able to show that tradeoff clearly.

### First task

Confirm the ECC agents and skills listed above are installed and available. Confirm git is initialized and `origin` is configured per `GITHUB_PUSH_PROTOCOL.md` — ask me for the repo URL if it isn't already set up. Use the `planner` agent (or `/ecc:plan`) to turn this brief into a phased plan. Then set up the repository skeleton, `requirements.txt`, `.gitignore`, and the nine documentation/memory files listed above (populated with real initial content, not placeholders — this includes saving `PHASE_VERIFICATION_LOOP.md` and `GITHUB_PUSH_PROTOCOL.md` into the repo root). Commit and push this initial scaffolding as its own commit. Then create the test fixtures described in `PHASE_VERIFICATION_LOOP.md` (synthetic test images, one real public-domain sample page, and its hand-annotated ground truth), commit and push those. Then implement the **preprocessing** stage using `tdd-guide`, review it with `python-reviewer`/`code-reviewer`, run it through the full verification loop via `loop-operator`, and once it passes, commit, push, and tag it per `GITHUB_PUSH_PROTOCOL.md` before reporting back. Do not move to layout detection until preprocessing passes and is pushed.

## PROMPT END
