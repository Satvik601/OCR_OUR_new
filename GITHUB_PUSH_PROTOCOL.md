# GitHub Push Protocol

> **Provenance note:** the project brief (`fable5_project_prompt.md`) referenced this file as
> "provided separately" but it was not present in the project directory. This is a standard
> version drafted by the agent on 2026-07-07 and flagged to the user. If the original protocol
> turns up, replace this file with it.

This file defines what happens with version control once a phase passes the verification loop
in `PHASE_VERIFICATION_LOOP.md`. A phase is only "done" once it has **passed verification and
been committed, pushed, and tagged** per this protocol.

## Preconditions

- Git is initialized in the repo root.
- `origin` points at the project's GitHub repository.
  **Current status: no remote configured — the user must supply the repo URL.** Until then,
  commits and tags are created locally and pushed retroactively (`git push --follow-tags origin main`)
  as soon as `origin` exists. Local-only commits are noted as such in `PROGRESS.md`.

## Per-milestone procedure

1. **Verify clean state:** `git status` — only files belonging to the milestone should be staged.
   Never commit pipeline outputs, caches, or scratch files (see `.gitignore`).
2. **Commit:** one commit per milestone, message format:

   ```
   <type>(<phase>): <summary>

   - what changed
   - verification evidence reference (PROGRESS.md entry date)
   ```

   `type` is one of `feat`, `fix`, `test`, `docs`, `chore`. Example:
   `feat(preprocessing): binarization pipeline passes verification loop on real page`
3. **Tag phase completions** (not intermediate commits): annotated tag
   `v0.<phase-number>-<phase-name>`, e.g. `v0.1-preprocessing`, `v0.2-layout`,
   `v0.3-filtering`, `v0.4-ocr`, `v0.5-json`, `v0.6-evaluation`.
   `git tag -a v0.1-preprocessing -m "Preprocessing passes PHASE_VERIFICATION_LOOP"`
4. **Push:** `git push --follow-tags origin main` (skipped while no remote exists — see above).
5. **Record:** append the commit hash and tag to the milestone entry in `PROGRESS.md`.

## Rules

- Never force-push.
- Never skip hooks.
- Documentation-only updates (`PROGRESS.md`, `KNOWN_ISSUES.md`, etc.) may be committed
  without a tag using `docs(...)` commits.
- Session reports (per `PHASE_VERIFICATION_LOOP.md`) must include the commit hash and tag
  for any phase reported complete.
