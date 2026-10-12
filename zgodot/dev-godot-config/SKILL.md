---
name: dev-godot-config
description: Use when creating or updating typed JSON configuration classes, getters, schema mappings, registration, or config tests for a BidaMobile Godot feature.
argument-hint: "[feature id | JSON path | JSON path + config script path]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# Godot JSON Config

Create and update typed `BaseJSONConfig` loaders without coupling feature paths to their data model. Support both singleton sources and same-schema source families.

## Resolve first

1. Resolve the exact approved source root from the approved feature spec or from an explicitly supplied config script path, together with feature ID, JSON path(s), feature-registration flow, ownership/cache lifecycle, and caller tests. Never derive a runtime folder or source root from `feature_id`. If an approved feature spec supplies schema/API, use it; otherwise propose the schema and typed getters for confirmation.
2. **Existing-file audit:** before either route, inspect existing loader, JSON fixtures, registrations, getters, callsites, and tests. Report unexpected JSON drift before editing.
3. Read [canonical loader pattern](references/json-config-pattern.md), [schema-diff workflow](references/schema-diff-workflow.md), and [GUT config tests](references/config-test-pattern.md) for the applicable work.

## Create

1. Confirm the JSON schema, required versus optional fields, defaults, and public getters.
2. Classify each source as either a singleton schema or a same-schema family. Different schemas or parsing behavior get separate top-level loader files. A family such as per-level maps gets one loader class and one caller-owned instance per source path; source count does not determine loader-script count.
3. Implement transactional `init(data) -> Error`, `read_config()`, and typed accessors. Use the canonical singleton for a singleton source. For a family, omit the static singleton wrapper, add bind-once source metadata, and forbid retargeting an instance after it is bound.
4. Keep path selection/constants, registration, keyed instance cache, and reset ownership outside loaders. Register every relative path before binding/loading it. Use `get_instance(true).pre_init("", path)` for singletons; use `Loader.new()` plus the family bind API for same-schema sources.
5. Do not append to `_list_json`, `_list_skill_json`, `_list_json_new`, `_list_json_new2`, or `_list_json_new3`.
6. Add isolated GUT coverage for valid data, defaults, malformed/missing data, registration, reload, and reset. A family suite must also prove two simultaneous paths have independent data/reload state, reject retargeting, and are all reset by their owner.

## Update

1. Produce a schema diff (added, changed, removed fields), affected getters/callsites, migration/default plan, and test impact before editing.
2. An approved feature spec takes precedence. For a destructive API change such as removing a getter, stop for explicit confirmation after the audit; do not hide it behind an unapproved compatibility shim.
3. Make the smallest confirmed parser/getter/callsite/test change. Preserve loaded data until a new parse validates, then run the focused GUT suite.

## Completion

Report paths changed, registrations, schema/API decisions, caller audit, test commands/results, and unresolved drift. Never place `CONFIG_PATH` or `register_config()` in a config subclass.
