# Documentation Architecture Checklist

Use this when bootstrapping or auditing project documentation structure.

## Bootstrap Checklist (New Project)

- [ ] `AGENTS.md` exists at repo root with: workspace rules, task routing, editing rules, branching and commit rules.
- [ ] `Docs/MASTER_DOCUMENTATION.md` exists and lists canonical paths for every category of content.
- [ ] `Docs/AGENT_START.md` exists with a task-type table and common commands.
- [ ] `Docs/workspace-map.yaml` is generated, not hand-edited, and lists every surface with `source_of_truth`, `run`, `test`, `build`, `depends_on`.
- [ ] Every canonical doc has a YAML frontmatter block with at minimum: `status`, `owner`, `last_reviewed`, `source_of_truth: true`, `audience`.
- [ ] No two files contain the same narrative content simultaneously.
- [ ] Layer 5 READMEs contain only: one-paragraph purpose, run commands, pointer to canonical docs.

## Audit Checklist (Existing Project)

- [ ] Identify all files that describe the same topic — keep only one, redirect the rest.
- [ ] Non-canonical files expose `canonical_source` in first 10 lines.
- [ ] Legacy redirect files contain no duplicate content below the redirect.
- [ ] `workspace-map.yaml` `source_of_truth` paths still resolve to real files.
- [ ] `last_reviewed` in frontmatter is within 90 days; trigger review if not.
- [ ] Generated artifacts (e.g., split OpenAPI files) are not hand-edited directly.
- [ ] No module content lives in more than one Layer 2 file simultaneously.

## Ongoing Maintenance

- [ ] When code changes: update `source_of_truth` file for that surface first.
- [ ] When paths or commands change: regenerate `workspace-map.yaml`.
- [ ] When a legacy redirect file's canonical target has stabilised for 30+ days: delete the redirect stub.
- [ ] When a module spec exceeds ~300 lines: split into a per-module folder (see SKILL.md §Module Spec Format).
