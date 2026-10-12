# Feature tree

Create only files that an approved spec owns. Copy `<source_root>` exactly from its `## Status` table. Every source-root segment uses `snake_case`. The path is project-relative under `modules/game/`; it has no `res://` prefix, drive-qualified prefix, backslash, or `.` or `..` path segment. Its final segment equals `feature_id`. Use the full snake_case feature ID as each owned file prefix and derive PascalCase `class_name` from the entire stem: `sample_event_module.gd` -> `SampleEventModule`; `offer_dynamic_popup.gd` -> `OfferDynamicPopup`. Packet files likewise keep the full prefix, such as `sample_event_send_load_info.gd` -> `SampleEventSendLoadInfo`.

```
assets/
  textures/<feature_id>/                 # owned textures; add other approved asset roots
docs/modules/<feature_id>/
  design/<feature_id>-design.md
  spec/<feature_id>-spec.md
  dev-status.md
  plans/<YYYY-MM-DD>-<feature_id>-plan.md
modules/game/game_feature_registry.gd    # single global composition root
<source_root>/                           # exact approved source root below modules/game
  <feature_id>_module.gd                 # class_name <FeatureId>Module
  logic/
    <feature_id>_util.gd                 # class_name <FeatureId>Util (optional model files)
  network/
    <feature_id>_send_<action>.gd
    <feature_id>_recv_<event>.gd
  ui/                                    # owned Control UI and approved non-Control presentation scenes
    <feature_id>_main_gui.tscn
    <feature_id>_main_gui.gd             # class_name <FeatureId>MainGui
    <feature_id>_popup.tscn
    <feature_id>_popup.gd                # class_name <FeatureId>Popup
  config/                                # only if feature owns JSON
    <feature_id>_json_config.gd
    <feature_id>_<domain>_json_config.gd
tests/unit/features/<feature_id>/
  test_<feature_id>_module.gd
  test_<feature_id>_packets.gd
  test_<feature_id>_json_config.gd
devtools/mocks/<feature_id>/             # only for approved interactive mock flows
```

Each distinct schema/parser owns one `BaseJSONConfig` loader class. Use the primary `<feature_id>_json_config.gd` for the feature's main JSON; add `<feature_id>_<domain>_json_config.gd` for a distinct schema. A same-schema source family may reuse one loader class through multiple caller-owned instances, each bound once to one path with independent reload/reset lifecycle; never retarget a loaded instance. Delegate loader implementation and registration detail to `dev-godot-config`.

Feature-local ownership always stays below the recorded root: `<source_root>/<feature_id>_module.gd`, `<source_root>/logic/`, `<source_root>/network/`, `<source_root>/config/`, and `<source_root>/ui/`.

Approved source-root shapes are flexible. A standalone feature may use `modules/game/room/room_module.gd`; a grouped event may use `modules/game/event/offer_dynamic/offer_dynamic_module.gd`. `modules/game/features/<feature_id>` is also a valid but optional grouping, never a mandatory default.

## Complete small example: `sample_event`

```
assets/textures/sample_event/event_badge.png
docs/modules/sample_event/design/sample_event-design.md
docs/modules/sample_event/spec/sample_event-spec.md
docs/modules/sample_event/dev-status.md
docs/modules/sample_event/plans/2026-08-07-sample_event-plan.md
modules/game/event/sample_event/sample_event_module.gd
modules/game/event/sample_event/logic/sample_event_util.gd
modules/game/event/sample_event/network/sample_event_send_load_info.gd
modules/game/event/sample_event/network/sample_event_recv_load_info.gd
modules/game/event/sample_event/ui/sample_event_main_gui.tscn
modules/game/event/sample_event/ui/sample_event_main_gui.gd
modules/game/event/sample_event/config/sample_event_json_config.gd
modules/game/event/sample_event/config/sample_event_reward_json_config.gd
tests/unit/features/sample_event/test_sample_event_module.gd
tests/unit/features/sample_event/test_sample_event_packets.gd
tests/unit/features/sample_event/test_sample_event_json_config.gd
devtools/mocks/sample_event/sample_event_mock.gd
```

Do not create optional UI, packet, config, model, asset, or mock files merely to fill this tree. `modules/game/game_feature_registry.gd` is the single global composition root: register the module factory and open it only when the approved activation rule requires it.
