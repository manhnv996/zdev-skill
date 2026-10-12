---
name: dev-godot-ui-spec
description: Use when a BidaMobile Godot feature design includes new or ported UI or presentation scenes whose inventory, node trees, bindings, placement, textures, or rich text must be specified before implementation.
argument-hint: "[feature id | approved design path | source UI folder]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# Godot UI Specification

## Boundary and inputs

This is the required docs-only A2 handoff for UI and client-side presentation scenes in `dev-godot-feature`. Start only from an approved `docs/modules/<feature_id>/design/<feature_id>-design.md`. Resolve the feature ID, the approved `Source root` from the main spec `## Status` table, current main spec, porting source UI, available assets, and the actual `BaseScreen` and `CustomLabel` contracts. A prebuilt `.tscn` list is not an input requirement.

Read the parent feature specification template, its UI patterns, and [canonical scene-tree patterns](references/ui-scene-tree-patterns.md). When porting, also inspect source scenes/scripts/assets and existing Godot UI that owns the same presentation boundary.

## Derive the inventory

1. Extract every independently presented full screen or popup, lobby entry, reusable layer, repeated slot/item, stateful reusable node, and non-`Control` world/render scene from the approved design and source evidence.
2. Keep a visual group used by one surface inside its owner scene. Keep layout variants with the same behavior in one scene; split distinct lifecycle or presentation flows.
3. Propose the smallest complete inventory. Do not ask the user to enumerate scenes first.
4. Place every proposed same-stem scene/script pair below `<source_root>/ui/`; group only complete `.tscn`/`.gd` pairs by a real functional surface such as `ui/lobby/`, `ui/popup/`, or `ui/battle/world/`. Classify each pair by its runtime responsibility and root node type. A `Control` UI surface directly extends `BaseScreen`. A non-`Control` world/render pair extends the correct Godot class for its responsibility, such as `Node2D`, `Area2D`, or `Camera2D`; it must not extend `BaseScreen` merely because its path contains `ui`. Folder path never decides inheritance, parent, presentation service, placement, or fog.
5. Present each ambiguous split, placement owner, texture owner, or missing product behavior. Recommend a decision when evidence supports one. Missing product behavior blocks A2; never invent it.

## Write the main specification

Write the UI proposal into `docs/modules/<feature_id>/spec/<feature_id>-spec.md`; do not create a second UI spec. Record:

- paired `.tscn` and `.gd` paths using the full `<feature_id>_<surface_role>` stem, its PascalCase `class_name`, root node type, direct base class, surface/presentation type, owner, placement mode, and applicable fog policy;
- stable node tree, node types, binding names, input ownership, anchors/offsets or container ownership;
- texture path and reload/localization owner, plain-label versus rich-text behavior, and `CustomLabel` usage;
- automated checks and manual runtime verification per scene.

Present the derived inventory, node trees, and unresolved decisions as part of the parent A2 checkpoint. The handoff is docs-only: never create or edit `.tscn`, `.gd`, assets, registries, or tests before explicit A2 approval and the later Phase B start approval. End the turn and return control to `dev-godot-feature` so it can wait at A2.

## Completion check

- Inventory covers every approved UI entry and repeated/stateful surface without speculative scenes.
- Every scene/script pair keeps the full feature-prefixed stem and matching PascalCase `class_name`. Every `Control` UI surface directly extends `BaseScreen`; every non-`Control` world/render pair declares and extends the correct Godot base class for its responsibility. Folder location is never used as an inheritance rule.
- Every stable node has a type and binding. `Control` UI nodes use the applicable canonical `image...`, `btn...`, `label...`, or `text...` prefix; world/render nodes use explicit domain-role names. Textures, localization, rich text, presentation, placement, verification, and applicable fog behavior have owners.
- New `text...` nodes use `CustomLabel` directly. Runtime conversion from `Label` is legacy/import fallback only.
- Only the canonical main spec changed; runtime paths remain untouched.
