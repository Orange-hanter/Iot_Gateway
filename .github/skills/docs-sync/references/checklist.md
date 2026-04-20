# Docs Sync Checklist

## Before Editing

- Select one `entries[]` scope in `Docs/workspace-map.yaml`.
- Find the canonical source-of-truth file.
- Confirm whether a legacy copy already exists.
- Check whether commands or paths changed in code.

## During Editing

- Keep changes minimal and execution-oriented.
- Prefer links over duplicate explanation.
- Update metadata for active operational docs.

## After Editing

- Verify links point to real workspace files.
- Verify commands still exist in `package.json`, scripts, or Docker config.
- If commands/paths/source-of-truth boundaries changed, run `node tools/generate-workspace-map.mjs`.
- If legacy docs remain, ensure they clearly redirect to the canonical source.