---
name: dev-godot-feature
description: Use when creating, porting, extending, or structurally reviewing a BidaMobile Godot game feature with module, packets, state, UI, config, assets, tests, or optional integrations.
argument-hint: "[feature id | feature spec path | source feature folder]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# Godot Feature Workflow

## Route and audit

1. Resolve whether this is a **create** or **update**. Before either route, audit existing feature files, callers, packet IDs, ConfigMgr registrations, scene/service wiring, assets, tests, mocks, docs, and working-tree changes.
2. Before editing an update, identify the approved spec and smallest affected contract; record the added, changed, and removed packet fields plus public API, caller, default, and migration impact. If missing or stale owning docs are found, return to the scoped Phase A gate, end the turn, and wait for explicit user approval; never create or update docs and continue to implementation in the same turn. Report unexpected drift before editing. For creation, do not infer product behavior—resolve it below.
3. Foundation readiness gate: inspect runtime APIs first: `BaseModule`, `ModuleMgr`, `NetworkService`, `PoolFunction`, UI services, `ConfigMgr`, packet bases, and available GUT setup. Stop if required APIs or activation ownership are unavailable.

## Phase A — create and approve docs

Phase A is docs-only. Do not scaffold runtime files, edit registries, or begin tests/implementation.

### Phase A language contract

Write every A1–A4 document and all user-facing summaries and approval questions in natural Vietnamese with full diacritics (`tiếng Việt có dấu`). This includes narrative prose, rules, flows, decisions, table values, acceptance criteria, status explanations, task descriptions, manual checks, and blockers. Keep canonical machine-readable Markdown section names and table headers in English exactly as the templates and `validate_feature.py` require. Keep technical identifiers unchanged, including `feature_id`, class names, filenames, resource paths, APIs, methods, signals, packet classes/fields, command IDs, JSON keys, enum/error names, `StringName` constants, code blocks, CLI commands, and approved protocol terms. Translate English source narrative faithfully without inventing behavior or changing an approved contract.

1. **A0 — Inputs:** Resolve feature ID; source; the exact approved source root; activation and availability; commands and server push; config; UI; assets; required/optional dependencies; automated tests; and interactive mocks. Every source-root segment uses `snake_case`. The path is project-relative under `modules/game/`; it has no `res://` prefix, drive-qualified prefix, backslash, or `.` or `..` path segment. Its final segment equals `feature_id`; do not infer the path from `feature_id`.
2. **A1 — Design:** Create or normalize `docs/modules/<feature_id>/design/<feature_id>-design.md` with player flow, rules, availability, server/config needs, UI entry, MVP, and acceptance criteria. Present it, end the turn, and wait for explicit user approval before A2.
3. **A2 — Technical specification:** From the approved design, write `docs/modules/<feature_id>/spec/<feature_id>-spec.md` with the exact approved source root recorded in `## Status`, exact tree, APIs/signals, packets, state/config, UI/assets, optional boundaries, tests, and mocks. Record config and mock contracts only; their runtime/test-writing supporting skills run in Phase B. **REQUIRED SUB-SKILL:** use `dev-godot-ui-spec` when UI is in scope; it derives a docs-only scene inventory and canonical node trees without requiring a prebuilt `.tscn` list. Present the spec, end the turn, and wait for explicit A2 approval before A3.
4. **A3 — Dev status:** From the approved spec, create `docs/modules/<feature_id>/dev-status.md` with planned files, tasks, verification, user runtime checks, blockers, and supporting work.
5. **A4 — Plan:** Create `docs/modules/<feature_id>/plans/<YYYY-MM-DD>-<feature_id>-plan.md` from approved design/spec. Present task order and verification, end the turn, and wait for explicit approval.

After A4 approval, ask separately whether to begin Phase B now or stop after docs. End the turn and wait for the answer. An initial request to implement, delivery pressure, or a resumed/compacted session does not replace A1, A2, A4, or Phase B approval; resume only from recorded approval evidence.

## Existing-feature Lightweight Mode

A small existing-feature change may enter Phase B directly only when it belongs to no active Phase A plan, owning docs are current, and it changes no feature tree, packet/config schema, public API/signals, activation, dependency, asset, or mock contract. First audit code, owning docs, callsites, tests, and working-tree changes. If any contract changes or docs are missing/stale, return to the scoped Phase A gate and wait; do not repair docs and continue coding in the same turn.

## Phase B — implement approved plan with TDD

1. Begin only after Phase A and the separate Phase B start gate are approved. Write failing focused tests, then implement in this order: packets/config contract, util/model, `RefCounted` module, UI, registry, tests, docs status.
2. **REQUIRED SUB-SKILL:** `dev-godot-config` whenever typed JSON config, registration, schema, getters, reload, or config tests are in scope.
3. **REQUIRED SUB-SKILL:** `dev-godot-mock` whenever dev-only interactive packets, CheatInput, fake responses, or mock flows are in scope.
4. Keep typed packet ownership in the module; expose public commands/queries and semantic signals. Use direct calls or signals inside a feature. Delegate only optional cross-feature boundaries to `PoolFunction` with namespaced `StringName`, explicit defaults, and owner cleanup.
5. Before coding each presentation script, read [UI patterns](references/ui-patterns.md). Every new or ported `Control` UI surface directly extends `BaseScreen`; non-`Control` world/render scenes may live below `ui/` and use the appropriate `Node2D`-family base. Folder placement never selects inheritance, parent, fog, or presentation service.
6. Keep UI packet-free: it calls public module methods and connects/disconnects semantic signals.

## Completion gates

1. Run `python .agents/skills/dev-godot-feature/scripts/validate_feature.py --project-root . --feature-id '<feature_id>' --spec '<spec>'`; findings mean incomplete work, so correct the artifacts and rerun to exit 0 before targeted GUT and full GUT.
2. Run source/callsite, docs-status, asset, unresolved-symbol checks; verify changed paths and report actual results or blockers.

## Canonical references

- [Feature tree](references/feature-tree.md)
- [Feature specification](references/feature-spec-template.md)
- [Module lifecycle](references/module-lifecycle-pattern.md)
- [Network patterns](references/network-patterns.md)
- [UI patterns](references/ui-patterns.md)
- [Optional dependencies](references/optional-dependency-patterns.md)
- [Validation checklist](references/validation-checklist.md)
