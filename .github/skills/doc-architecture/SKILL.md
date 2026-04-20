---
name: doc-architecture
description: 'Use when setting up documentation structure for a new project, or when the existing docs structure needs to be aligned with the canonical layered model. Keywords: documentation architecture, docs structure, doc layers, organize docs, set up docs, canonical docs, workspace map, documentation governance.'
argument-hint: 'Describe the project type, number of surfaces (backend, frontend, admin), and whether it is a mono-repo or single-surface project.'
user-invocable: true
disable-model-invocation: false
---

# Documentation Architecture Skill

Use this skill when bootstrapping documentation for a new project or when an existing project's docs have grown chaotic and need structural alignment.

## When To Use

- Starting a new repository and need to decide where docs live.
- Docs have grown as scattered markdown files across the repo root and multiple folders.
- A new team member or AI agent cannot navigate the docs reliably.
- You want to enforce a single source of truth with zero ambiguity about where to write or read any given piece of information.

---

## Core Principles

### 1. Single Source Of Truth Per Topic

Every topic has exactly one canonical home. All other files that overlap with it must either redirect to the canonical file or be deleted. Never let two files contain the same information in parallel — they will drift apart.

### 2. Layered Abstraction Model

Docs are split into abstraction layers. Each layer has a different audience and a different lifecycle. Never mix content from different layers into the same file.

| Layer | Content | Audience | Lifetime |
|-------|---------|----------|----------|
| 1 — Governance & Execution | Repo rules, agent entrypoints, command catalogs, machine-readable maps | Agents, contributors | Permanent, always current |
| 2 — Product & System Specs | Platform behavior, architecture, module specifications | Developers, architects | Stable, versioned |
| 3 — Requirements & Domain Inputs | Customer specs, business domain, regulatory appendices | Product, stakeholders | Stable input, not re-editable |
| 4 — Derived Analysis | Temporary decomposition, synthesis, interpretation work | Agents, architects | Transient, archive after use |
| 5 — Project-Local Supplements | Per-surface READMEs, local dev notes | Surface owners | Local scope only |
| 6 — Legacy Compatibility | Redirect stubs pointing to canonical files | Nobody reads directly | Temporary, delete after cleanup |

### 3. Canonical Vault Location

All Layer 1–4 documents live inside a single canonical folder — typically `Docs/` at the root — and when using Obsidian or a similar tool, inside `Docs/obsidian/`. Project-local supplements (Layer 5) live next to the surface they describe (e.g., `restate-api/README.md`).

### 4. Machine-Readable Workspace Map

A single YAML file (`Docs/workspace-map.yaml`) lists every project surface with its:
- `name` — identifier
- `path` — relative root
- `purpose` — one sentence
- `stack` — technologies
- `run`, `test`, `build` — key commands
- `docs` — paths to relevant docs for this surface
- `source_of_truth` — paths to the authoritative files for this surface
- `depends_on` — other surfaces this one consumes

Agents use this file as the first lookup before opening anything else. It must be regenerated (not hand-edited) when paths change.

### 5. YAML Frontmatter On Every Canonical File

Every canonical document must open with a YAML frontmatter block:

```yaml
---
tags: [docs, <topic>]
project: <PROJECT_NAME>
status: active | draft | deprecated
owner: <Team or Role>
last_reviewed: YYYY-MM-DD
source_of_truth: true        # omit or set false for non-canonical files
audience: [contributors, agents, stakeholders]
related_code:
  - path/to/relevant/file.ts
---
```

Non-canonical files must expose `canonical_source`, `scope`, `audience`, and `related_code` in the first ten lines so readers can exit immediately.

### 6. Governance Entrypoints

Every repository needs exactly four governance entrypoints:

| File | Role |
|------|------|
| `AGENTS.md` (root) | Workspace rules for AI agents and contributors. Task routing, editing rules, branching, commit rules. |
| `Docs/MASTER_DOCUMENTATION.md` | Documentation control center: where each type of content lives, canonical vs legacy, surface index. |
| `Docs/AGENT_START.md` | Shortest onboarding path: one table mapping task types to first-read files and commands. |
| `Docs/workspace-map.yaml` | Machine-readable surface map. Generated, not hand-edited. |

If only one surface exists (not a monorepo), `AGENTS.md` and a single `README.md` may be enough for Layer 1, with `Docs/` for Layers 2–4.

### 7. No Duplicate Narratives

When writing documentation:
- Update the canonical file. Not a copy.
- If a copied file already exists, convert it to a redirect stub with `canonical_source` at the top, then schedule deletion.
- Do not create a module spec in both `Docs/obsidian/Modules/` and a project README. The README may contain a brief summary and a pointer only.

### 8. Legacy File Contract

A legacy redirect file must have:
1. A frontmatter marking `source_of_truth: false` and a `canonical_source` path.
2. A one-line redirect sentence in the body.
3. No repeated content from the canonical file below the redirect.

Example:
```markdown
---
source_of_truth: false
canonical_source: Docs/obsidian/Modules/M1-Auth.md
scope: redirect
audience: [contributors]
related_code: []
---

This content moved to [Docs/obsidian/Modules/M1-Auth.md](../Docs/obsidian/Modules/M1-Auth.md).
```

### 9. Module Spec Format

Each feature module gets its own spec. When a module grows large, split it into a per-module folder:

```
Docs/obsidian/Modules/
  M1-Auth/
    overview.md
    domain.md
    api-contracts.md
    security.md
  M2-Listings/
    overview.md
    ...
```

Each module file should open with: scope, status, implemented_in, related_code, depends_on.

### 10. Docs Update Discipline

When code changes:
1. Identify affected surface via `workspace-map.yaml`.
2. Open `source_of_truth` for that surface.
3. Edit the canonical file.
4. If a legacy file overlaps, convert or delete it.
5. Update `last_reviewed` in frontmatter.
6. Regenerate `workspace-map.yaml` if paths or commands changed.
7. Verify all links still resolve.

Never edit derived files (e.g., split OpenAPI files in `Docs/api/`) directly — edit the source and regenerate.

---

## Applying This To A New Project

### Minimal Single-Surface Project

```
project-root/
  README.md                    # Layer 5 (project-local)
  AGENTS.md                    # Layer 1 governance (optional but recommended)
  Docs/
    MASTER_DOCUMENTATION.md    # Layer 1 control center
    AGENT_START.md             # Layer 1 onboarding
    workspace-map.yaml         # Layer 1 machine-readable map
    architecture.md            # Layer 2 system design
    modules/                   # Layer 2 module specs
    requirements/              # Layer 3 input docs
    analysis/                  # Layer 4 (delete after use)
```

### Monorepo With Multiple Surfaces

Each surface gets a local `README.md` (Layer 5) that contains only:
- What this surface does (2–3 lines)
- How to run it locally (one command block)
- Pointer to canonical docs for deeper reading

All spec, architecture, and module content lives in `Docs/`.

### AI Agent Configuration

Place agent config files under `.github/agents/` and skills under `.github/skills/`. Name skills after the workflow they support (`docs-sync`, `doc-architecture`, `release-management`). Each skill file uses the same frontmatter format and follows the same principle: one canonical place, no duplicate content.

---

## Checklist

See companion checklist in [references/checklist.md](./references/checklist.md).
