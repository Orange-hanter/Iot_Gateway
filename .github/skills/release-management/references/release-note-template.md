---
type: release-note
status: draft
release_date: YYYY-MM-DD
release_scope: milestone|stage-freeze|full-release
target_commit: <sha>
previous_tag: <tag-or-none>
proposed_tag: <tag>
---

# Release Note: <Title>

## Summary

One short paragraph describing what this release represents.

## Included Range

- Previous boundary: `<tag-or-sha>`
- Current boundary: `<sha>`
- Target branch: `develop|main`

## Highlights

### Backend / Product

- item
- item

### Frontend / Admin

- item
- item

### Docs / Architecture

- item
- item

### CI / Ops / Tooling

- item
- item

## Representative Commits

1. `<sha>` — message
2. `<sha>` — message
3. `<sha>` — message

## Operational Impact

- runtime impact
- deployment impact
- testing or release implications

## Publication Plan

1. Commit release note.
2. Create annotated tag.
3. Merge to `main` if this is a full release.
4. Push branch and tags.

## Notes

- extra release caveats