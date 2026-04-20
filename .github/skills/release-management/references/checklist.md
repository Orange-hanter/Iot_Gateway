# Release Management Checklist

## Before Writing Notes

- Check `git status --short`.
- Identify the target range: tag-to-HEAD, date window, or branch delta.
- Confirm whether the release is historical, periodic, or full publication.
- Confirm target branch: usually `main`.
- Confirm whether tags should be local only or pushed.

## While Writing Notes

- Group by product/backend, frontend/admin, docs/architecture, and ops/CI.
- Keep summary high-level but factual.
- Include representative commits rather than raw commit dumps.
- Record boundary commit and intended tag.

## Before Commit

- Ensure unrelated local editor files are excluded.
- Update `Docs/release-notes/README.md` if this note belongs in the series.
- Verify links point to real files.

## Before Tagging

- Use annotated tags.
- Confirm tag names do not already exist.
- Tag the correct boundary commit, not a random working commit.

## Before Merge To Main

- Confirm `main` exists locally and on origin.
- Pull `main` with `--ff-only`.
- Prefer `git merge --no-ff develop` for release traceability.
- Check `git status --short` after merge.

## Before Push

- Confirm the exact branches and tags to push.
- Push commits first, then tags if desired.
- Note that pushing `main` may trigger GitLab release jobs.

## After Push

- Verify `main` contains the merge commit.
- Verify tags exist on origin.
- If CI publishes releases, verify the pipeline was created.