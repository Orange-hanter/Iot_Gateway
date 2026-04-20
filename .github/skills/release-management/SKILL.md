---
name: release-management
description: 'Use when preparing release notes, milestone notes, tags, main-branch releases, history backfills, or publishing a release to the git system. Keywords: release note, release notes, milestone, tag release, publish release, merge to main, cut release, historical releases, changelog from commits.'
argument-hint: 'Describe the release goal, scope, target branch, and whether to create notes only or also tag/push/publish'
user-invocable: true
disable-model-invocation: false
---

# Release Management

Use this skill when the user wants release notes, milestone notes, a tagged checkpoint, or a full release publication flow.

## When To Use

- The user asks to prepare or publish a release.
- The user wants periodic release notes from commit history.
- The user wants milestone notes for a time window such as 2 weeks.
- The user wants tags created and attached to specific commits.
- The user wants `develop` merged into `main` as a formal release.

## Core Rules

1. Treat `main` as the release branch. If the user says `master` but the repository only has `main`, use `main` and say so.
2. Never include unrelated local files in the release, especially editor-only changes such as `.vscode/` files.
3. Build release notes from git history first, then tag, then merge, then push.
4. Prefer annotated tags.
5. Prefer a merge commit for full releases into `main` to preserve release traceability unless the user explicitly requests squash.
6. For historical backfills, create milestone notes in two-week windows unless the user specifies another cadence.
7. Align publication behavior with `.gitlab-ci.yml`: releases are published from `main`, and CI creates runtime-style tags named `vYYYY.MM.DD.IID`.

## Repository Conventions

- Release notes live in `Docs/release-notes/`.
- Historical milestone notes use `YYYY-MM-DD-milestone-XX-<slug>.md`.
- Point-in-time stage notes may use `YYYY-MM-DD-<scope>.md`.
- Use `README.md` in `Docs/release-notes/` as the index of release artifacts.

## Default Workflow

### A. Prepare

1. Check `git status --short`.
2. Identify unrelated local changes and exclude them from release commits.
3. Inspect branches, remotes, and existing tags.
4. Determine whether this is:
   - notes only;
   - notes + local tags;
   - full release to `main` + push.

### B. Build Release Notes

1. Collect commit history for the requested range.
2. Group changes into user-meaningful areas:
   - backend/product functionality;
   - frontend/admin/UI;
   - docs and architecture;
   - CI, Docker, infra, tooling.
3. Write notes into `Docs/release-notes/`.
4. Update `Docs/release-notes/README.md` if the note belongs in the long-lived series.

### C. Commit Release Artifacts

1. Commit release-note files separately from code when practical.
2. Use explicit commit messages such as:
   - `docs(release): add milestone release note for M03`
   - `docs(release): add release note for v0.3 stage freeze`

### D. Tag

1. For historical milestones, tag the boundary commit with an annotated tag such as:
   - `history-m03-2026-04-15`
2. For full releases to `main`, prefer a release tag such as:
   - `release-v0.3.0`
   - or defer to CI-generated runtime tag naming on `main`.

### E. Merge And Publish

1. Update local refs.
2. Merge `develop` into `main`.
3. Default command pattern:
   - `git checkout main`
   - `git pull --ff-only origin main`
   - `git merge --no-ff develop`
4. Push `main`, `develop`, and tags only after release artifacts are committed.
5. If GitLab release jobs exist on `main`, note that pushing `main` is what triggers release publication.

## Release Logic

### Historical Backfill Logic

- Start from the first commit.
- Split by 14-day windows.
- For each window capture:
  - period;
  - representative commits;
  - functional highlights;
  - docs/governance highlights;
  - operational impact.

### Ongoing Periodic Logic

- On a recurring basis, compare the latest release tag to `HEAD` or to the target release branch.
- Generate one new note for the delta.
- Update the index.
- Tag the resulting release boundary.

### Full Release Logic

- Ensure desired release notes exist.
- Ensure working tree is clean apart from intentionally excluded local files.
- Merge `develop` into `main`.
- Create or confirm release tag strategy.
- Push branch and tags.
- Let GitLab publish the release from `main`.

## Safety Checks

- Do not merge if there are unresolved conflicts.
- Do not push if the user did not request push.
- Do not rewrite history for release publication unless the user explicitly asks for it.
- If unrelated local modifications exist, either exclude them or ask only if exclusion is impossible.

## Checklist

Use the companion checklist in [references/checklist.md](./references/checklist.md).
Use the note template in [references/release-note-template.md](./references/release-note-template.md).