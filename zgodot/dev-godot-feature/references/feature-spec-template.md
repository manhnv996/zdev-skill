# Approved feature specification template

Create `docs/modules/<feature_id>/spec/<feature_id>-spec.md`. An approved specification is complete: replace every example with a decision; do not leave unchecked status or `TBD`.

```md
# <Feature name>

## Status
| Field | Approved value |
|---|---|
| Status | Approved |
| Feature ID | `<feature_id>` |
| Source root | modules/game/event/<feature_id> |
| Activation | eager at bootstrap / lazy from <entry> |
| Availability source | <server flag, config rule, or local rule> |

Every source-root segment uses `snake_case`. The path is project-relative under `modules/game/`; it has no `res://` prefix, drive-qualified prefix, backslash, or `.` or `..` path segment. Its final segment equals `feature_id`. Record the exact approved value; do not derive it later from the feature ID.

## Existing update record

### Schema/API delta

| Change | Before | After | Caller/default/migration impact |
|---|---|---|---|
| Added/changed/removed packet field or public API | <prior schema/API> | <new schema/API> | <affected callers, default, compatibility or migration> |

### Documentation status

State whether this scoped spec was current, updated, or created for the update. If its owner or approval is unresolved, stop for approval before implementation; never silently skip docs/status.

## Dependencies
| Kind | Dependency | Why | Missing behavior |
|---|---|---|---|
| Required | `<module_id>` | <typed API used> | feature does not activate |
| Optional | `<provider>` | <boundary action> | explicit default below |

## Command ownership
| ID | Direction | Send/receive class | Fields | Response/push | Error behavior |
|---:|---|---|---|---|---|
| `<id>` | client -> server | `<Feature>Send<Action>` | <typed fields> | response | <semantic failure signal> |
| `<id>` | server -> client | `<Feature>Recv<Event>` | <typed fields> | server push | <state + semantic signal> |

Use the exact command ID expression and packet class implemented by each row. The send class owns that ID and the module constructs/sends it; the receive class owns that ID and the module registers the exact ID/class pair with `NetworkService.subscribe()`.

## State and public module API
| Owner | State | Reset rule |
|---|---|---|
| `<Feature>Util` / model | <fields> | clear in `on_reset()` |

| Command/query | Signature | Semantic signal |
|---|---|---|
| command | `request_load_info() -> void` | `load_failed(error_code: int)` |
| query | `get_info() -> <Info>` | `info_changed(info: <Info>)` |

Signatures and signals are exact typed contracts. Every documented signal is declared and emitted by the module.

## Optional actions
| Namespaced StringName | Provider method | Call arguments | Explicit default |
|---|---|---|---|
| `&"<feature_id>.open_related"` | `open_related() -> bool` | `[]` | `false` |

## Optional queries
| Namespaced StringName | Provider method | Call arguments | Explicit default |
|---|---|---|---|
| `&"<feature_id>.has_related"` | `has_related() -> bool` | `[]` | `false` |

Each optional row maps to retained neutral constants at `modules/game/contracts/<feature_id>_optional_boundary.gd`: `<Feature>OptionalBoundary.<ACTION>` stores the namespaced key and `<Feature>OptionalBoundary.DEFAULT_<ACTION>` stores the documented default. Providers register that key, consumers pass both constants to `PoolFunction.do_func()`, and `PoolFunction` only dispatches.

## JSON configuration
| File | One class | ConfigMgr relative path | Typed accessors |
|---|---|---|---|
| `<feature_id>_json_config.gd` | `<Feature>JSONConfig` | `<feature_id>/<file>.json` | `<getter>() -> <Type>` |
| `<feature_id>_map_json_config.gd` | `<Feature>MapJSONConfig` | `<feature_id>/maps/<feature_id>_map_{01..10}.json` | `get_map() -> <Feature>MapConfig` |

Class names preserve the `JSON` acronym even though loader filenames remain `snake_case`. An exact path uses the singleton registration flow. A zero-padded `{01..10}` range declares a same-schema source family: one non-singleton loader class, one caller-owned instance per expanded path, and dynamic `register_json_file(path)` plus `pre_init("", path)` before caching that instance. Each instance is bound once and reset by its owner.

## UI and assets
Use the **REQUIRED SUB-SKILL** `dev-godot-ui-spec` when UI is in scope. Its canonical scene-tree reference owns node-shape rules; this main feature spec owns the approved inventory and decisions.

### Scene inventory

| Surface | Base class | Presentation owner | Scene | Fog | Notes |
|---|---|---|---|---|---|
| Main popup | `BaseScreen` | subclass via `GuiService` | `res://modules/game/event/sample_event/ui/sample_event_main_gui.tscn` | manual 70% blocking | lazy, packet-free |

Every `Control` UI surface uses `BaseScreen`. Approved non-`Control` world/render scenes may also live below `ui/` with the appropriate `Node2D`-family base; presentation owner and fog remain independent per-surface decisions.

### `<scene_name>` scene contract

| Field | Approved decision |
|---|---|
| Scene/script/class | `res://<source_root>/ui/<feature_id>_<surface_role>.tscn` / matching `res://<source_root>/ui/<feature_id>_<surface_role>.gd` / PascalCase `<FeatureId><SurfaceRole>` |
| Surface and lifecycle | <full screen, popup, reusable layer, repeated slot/item, or stateful node> |
| Placement owner | <manual center-origin + offsets, parent Container + minimum size, or viewport anchors> |
| Texture/reload owner | <node paths, asset paths, locale/theme reload method> |
| Localization/rich text | <plain `label...` / direct `CustomLabel` `text...`; content and update owner> |
| Verification | <automated structural/behavior check and manual runtime check> |

Keep every same-stem `.tscn`/`.gd` pair together. Use a nested functional path such as `res://<source_root>/ui/lobby/<feature_id>_lobby_icon.tscn` with its matching `.gd` only when the feature actually needs that grouping; `ui/popup/` follows the same rule.

```text
imageRoot (Control; <SceneClass> script extends BaseScreen; texture-free root)
└── imageBg (Control; texture-free content wrapper; animation target)
    └── <stable prefixed node tree with Godot types>
```

| Node path | Godot type | Bound property | Placement/input role |
|---|---|---|---|
| `<path>` | `<type>` | `<property>` | <anchors/offsets or container owner; hit target or mouse-ignore decoration> |

| Asset root | Contents |
|---|---|
| `assets/textures/<feature_id>/` | <textures and loading owner> |

## Verification
| Automated scenario | Expected result |
|---|---|
| `<scenario_id>` | <concrete state, signal, packet, config, or error result> |

| Interactive mock flow | Expected typed handler/UI result |
|---|---|
| <named flow> | <observable result> |
```

The module owns command routing, typed network subscriptions, feature state transitions, and semantic signals. UI owns presentation and calls public module methods; it does not own packet parsing. Record all config paths through `ConfigMgr` and all asset roots, including texture roots.

Every automated scenario ID is `snake_case` and maps to an asserted GUT function named `test_<scenario_id>`. Construction-only tests and meta-results such as “validator exits zero” are not scenario evidence.
