---
name: docs-sync
description: 'Use when code, commands, architecture, or workflows changed and the repository documentation must be updated in the canonical places. Keywords: sync docs, update docs after code change, refresh README, update commands, documentation maintenance.'
argument-hint: 'Describe the code or workflow change that documentation should reflect'
user-invocable: true
disable-model-invocation: false
---

# Docs Sync

Use this skill when implementation changes require documentation updates.

## When To Use

- A command changed in `package.json`, Docker, or scripts.
- A feature moved between modules or surfaces.
- README files, onboarding docs, or source-of-truth guidance became stale.
- You need to update docs without creating duplicate narratives.

## Core Rule

Update canonical docs first. Prefer `Docs/obsidian`, `Docs/MASTER_DOCUMENTATION.md`, `Docs/AGENT_START.md`, `Docs/DEVELOPMENT_COMMANDS.md`, and targeted project READMEs.

## Procedure

1. Identify the implementation change and the affected project surface.
2. Open `Docs/workspace-map.yaml` and select exactly one `entries[]` scope before broad search.
3. Start edits from that scope's `source_of_truth` and only expand via `depends_on` when needed.
4. Update the canonical doc, not a legacy copy.
5. If a legacy file exists, convert it into a redirect stub or refresh its pointer.
6. Update metadata fields such as `last_reviewed`, `implemented_in`, or `related_code` when the file is operationally relevant.
7. If commands, paths, docs pointers, or source-of-truth boundaries changed, regenerate map via `node tools/generate-workspace-map.mjs`.
8. Verify that commands and links still point to real files.

## Canonical Targets

- Project navigation and governance: `Docs/MASTER_DOCUMENTATION.md`
- Agent workflow: `AGENTS.md`, `Docs/AGENT_START.md`
- Commands and runbooks: `Docs/DEVELOPMENT_COMMANDS.md`, `DOCKER_SETUP.md`
- Module and product specs: `Docs/obsidian/Modules/`, `Docs/obsidian/Architecture.md`
- Project-specific setup: `restate-api/README.md`, `admin-panel/package.json`, `app-restate-frontend/README.md`

## Checklist

Use the companion checklist in [references/checklist.md](./references/checklist.md).