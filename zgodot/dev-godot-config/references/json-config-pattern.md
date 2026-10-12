# Canonical JSON config loader

Use the `ChannelJSONConfig` grouping: optional singleton wrapper, `init` plus `read_config`, then game-facing accessors. This canonical contract returns `Error`, keeps raw parsed data internal, and does not mix IDs with positional indexes. The static wrapper applies only to a singleton source; use the family pattern below when many paths share one schema.

```gdscript
class_name SampleEventJSONConfig
extends BaseJSONConfig

var _data_config: Dictionary = {}
var _reward: int = 0
var _enabled: bool = false
var _tiers: Array[Dictionary] = []


#region Static
static func get_instance(is_pre_init: bool = false) -> SampleEventJSONConfig:
	return BaseJSONConfig.register_instance(
		SampleEventJSONConfig,
		is_pre_init
	) as SampleEventJSONConfig
#endregion


#region Init
func init(data: Variant) -> Error:
	if not data is Dictionary:
		return ERR_INVALID_DATA
	var source := data as Dictionary
	var reward_value: Variant = source.get("reward")
	var tiers_value: Variant = source.get("tiers", [])
	if not _is_integer_value(reward_value):
		return ERR_INVALID_DATA
	if typeof(source.get("enabled")) != TYPE_BOOL or not tiers_value is Array:
		return ERR_INVALID_DATA
	for tier_value: Variant in tiers_value:
		if not tier_value is Dictionary:
			return ERR_INVALID_DATA
	_data_config = source.duplicate(true)
	read_config()
	return OK


func read_config() -> void:
	_reward = int(_data_config["reward"])
	_enabled = bool(_data_config["enabled"])
	_tiers = []
	for tier_value: Variant in _data_config.get("tiers", []):
		_tiers.append((tier_value as Dictionary).duplicate(true))


func _is_integer_value(value: Variant) -> bool:
	if value is int:
		return true
	if not value is float:
		return false
	var number := float(value)
	return is_finite(number) and number == floor(number)
#endregion


#region Accessors
func get_reward() -> int:
	return _reward


func is_enabled() -> bool:
	return _enabled


func get_tiers() -> Array[Dictionary]:
	return _tiers.duplicate(true)
#endregion
```

`init()` validates all required input before replacing `_data_config`, does not call `super.init(data)`, and returns an error without changing prior valid parsed values. Godot JSON parses whole-number literals as `float`: integer fields accept finite integral `int`/`float` values only, rejecting fractional values, strings, `INF`, `-INF`, and `NAN`. `BaseJSONConfig.init_with_file()` sets loaded state only after `OK`.

## Registration belongs to feature bootstrap

Keep relative JSON paths and registration outside the loader class. Invoke this helper from the feature-registration flow and propagate its error:

```gdscript
static func _register_sample_event_configs() -> Error:
	var registration_error := ConfigMgr.register_json_file(
		"sample_event/sample_event.json"
	)
	if registration_error != OK:
		return registration_error
	SampleEventJSONConfig.get_instance(true).pre_init(
		"",
		"sample_event/sample_event.json"
	)
	return OK
```

Do not append to `_list_json`, `_list_skill_json`, `_list_json_new`, `_list_json_new2`, or `_list_json_new3`; dynamic feature registration uses only `ConfigMgr.register_json_file(relative_path)`.

The approved source root affects only the loader script location. `ConfigMgr.register_json_file()` and `pre_init()` keep paths relative to `assets/config/json/`; do not prefix those JSON paths with `<source_root>`.

## File boundary

```text
<source_root>/config/
├── sample_event_json_config.gd          # SampleEventJSONConfig only (one primary JSON)
├── sample_event_info_json_config.gd     # SampleEventInfoJSONConfig only
└── sample_event_reward_json_config.gd   # SampleEventRewardJSONConfig only
```

Use `<feature_id>_json_config.gd` for one JSON and `<feature_id>_<domain>_json_config.gd` for each distinct schema/parser. Loader class names preserve the acronym form `<Feature>JSONConfig` or `<Feature><Domain>JSONConfig`; filenames remain `snake_case` with `_json_config.gd`. Forbid multiple independent-schema BaseJSONConfig subclasses in one file. A single JSON with sections stays in one loader and splits parsing in `read_config()`. Only small private record inner classes are allowed inside that loader.

## Same-schema source family

When a catalog lists many files with exactly the same schema—for example one file per map—use one loader script and multiple instances. Do not generate a wrapper class per path: 7 singleton schemas plus 10 map sources may correctly produce 8 loader scripts for 17 JSON files.

```gdscript
class_name RoomMapJSONConfig
extends BaseJSONConfig

var _source_id: StringName = &""
var _source_path: String = ""
var _map_config: Variant = null


#region Binding
func bind_source(source_id: StringName, relative_path: String) -> Error:
	if source_id.is_empty() or relative_path.is_empty():
		return ERR_INVALID_PARAMETER
	if not _source_path.is_empty():
		return OK if _source_id == source_id and _source_path == relative_path else ERR_ALREADY_IN_USE
	_source_id = source_id
	_source_path = relative_path
	pre_init("", relative_path)
	return OK
#endregion


#region Lifecycle
func reset() -> void:
	super.reset()
	_map_config = null # Clear every typed cache; keep the immutable binding.
#endregion
```

The caller owns registration, instances, and keyed lookup:

```gdscript
func register_map(source_id: StringName, relative_path: String) -> Error:
	if _map_configs.has(source_id):
		return ERR_ALREADY_EXISTS
	var error := ConfigMgr.register_json_file(relative_path)
	if error != OK:
		return error
	var config := RoomMapJSONConfig.new()
	error = config.bind_source(source_id, relative_path)
	if error != OK:
		return error
	_map_configs[source_id] = config
	return config.check_init_config()


func reset_maps() -> void:
	for value: Variant in _map_configs.values():
		(value as RoomMapJSONConfig).reset()
	_map_configs.clear()
```

- Never put family instances in `BaseJSONConfig.register_instance()`: that registry is keyed by script and therefore represents only one instance per loader class.
- Bind each instance to one source ID/path once. Never call `pre_init()` again to retarget a loaded or previously bound instance.
- Each instance inherits its own `_file_name`, raw data, loaded flag, and reload check. The caller-owned cache makes its lifetime and reset explicit.
- Override `reset()` to call `super.reset()` and clear every typed cache, but retain the immutable source binding for diagnostics and accidental-reuse protection.
- Adding a source changes catalog/JSON only. Adding or changing a shared field changes the one family loader, typed model, validator, and shared tests only.

## Canonical checks

- No `CONFIG_PATH`, `ConfigMgr.register_json_file`, or `static func register_config` in a config subclass. Only a family loader's bind-once method may call inherited `pre_init()`; singleton bootstrap calls it externally.
- Raw config state is private; every collection accessor returns a deep duplicate.
- Register the full relative path consistently for version checks, `pre_init`, and server reload markers.
- For a same-schema family, register every source path and keep one bound loader instance per source key.
