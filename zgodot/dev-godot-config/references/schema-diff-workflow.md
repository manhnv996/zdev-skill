# Schema-diff workflow

Use this workflow before changing a loader that already has a JSON schema or callers.

## Audit and proposal

1. Read the existing JSON, loader, registration, fixtures, GUT tests, and every getter/callsite with `rg`.
2. Compare the requested JSON against the known schema. Treat an undocumented field/type change as drift and report it before editing.
3. Produce this compact proposal. An approved feature spec is the source of truth; do not ask again for decisions already confirmed there.

| Change | JSON field | Typed state/getter | Callers | Decision |
| --- | --- | --- | --- | --- |
| Added | `tiers` | `get_tiers()` | none | default `[]` |
| Changed | `enabled` → `isEnabled` | `is_enabled()` | lobby | confirm migration |
| Removed | `reward` | `get_reward()` | battle UI | destructive: confirm |

## Create route

Confirm required fields, optional defaults, generated getter names, JSON path, and registration owner. If the request omits a schema or path, locate existing feature/spec/JSON artifacts first; if still unknown, ask one focused question rather than inventing a public API.

## Update route

Keep the update minimal: validate the new data, update typed state and affected getters only after approval, repair confirmed callsites, and add regression cases. Before removing or renaming a public getter, show the schema diff and caller audit, then wait for explicit confirmation. Do not silently remove a getter or substitute an unapproved compatibility shim.

For a same-schema source family, diff the schema once against the shared loader and typed model, then audit every catalog entry/fixture for compatibility. Never create or update one subclass per source path. Exercise representative variants plus a pass over all shipped family files, and verify the caller-owned instance cache still gives each path independent load/reload state.

## Completion summary

State:

- schema changes and accepted defaults;
- getters added/changed/removed and confirmation for destructive changes;
- audited callsites and migrations;
- loader/registration/test paths changed; and
- GUT command and result.
