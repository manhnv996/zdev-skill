# GUT JSON config tests

## Contents

- [Fixture map](#fixture-map)
- [Isolated runnable suite](#isolated-runnable-suite)
- [Focused command](#focused-command)
- [Same-schema family cases](#same-schema-family-cases)

Give each distinct loader class its own production script and focused test file. Test the real `BaseJSONConfig`/`ConfigMgr` behavior; never use a test fixture with two production-style subclasses as a substitute for separate schemas. For a same-schema source family, one production loader and one suite cover all paths; instantiate the real loader at least twice in the same test.

## Fixture map

Use clearly test-only basenames so a crash cannot erase a real user cache:

```text
tests/fixtures/config/sample_event/__dev_godot_config_valid.json      {"reward":42,"enabled":true,"tiers":[{"id":1}]}
tests/fixtures/config/sample_event/__dev_godot_config_no_tiers.json   {"reward":42,"enabled":true}
tests/fixtures/config/sample_event/__dev_godot_config_malformed.json  {"reward":
```

`__dev_godot_config_missing.json` intentionally does not exist. Every listed basename can fall back to `user://configs/<basename>` through `ConfigMgr`; tests back up exact bytes before removal and restore only cache entries prepared successfully.

## Isolated runnable suite

```gdscript
extends GutTest

const SampleEventJSONConfig = preload(
	"res://<source_root>/config/sample_event_json_config.gd"
)
const VALID_PATH := "sample_event/__dev_godot_config_valid.json"
const RELOAD_PATH := "sample_event/__dev_godot_config_reload.json"
const CACHE_BASENAMES := [
	"__dev_godot_config_valid.json",
	"__dev_godot_config_no_tiers.json",
	"__dev_godot_config_malformed.json",
	"__dev_godot_config_missing.json",
	"__dev_godot_config_reload.json",
]


#region Snapshot State
var _original_instances: Dictionary
var _original_url_json: String
var _original_url_skill_json: String
var _original_version_config: Dictionary
var _original_data_config: Dictionary
var _original_reload_markers: Array[String]
var _original_check_list: Array[String]
var _original_registered: Array[String]
var _user_cache_existed: Dictionary = {}
var _user_cache_bytes: Dictionary = {}
var _prepared_cache_basenames: Array[String] = []
#endregion


#region Lifecycle Hooks
func before_each() -> void:
	# Shallow copy preserves original singleton objects without resetting them.
	_original_instances = BaseJSONConfig._instances.duplicate()
	BaseJSONConfig._instances = {}
	_original_url_json = ConfigMgr.get_url_json()
	_original_url_skill_json = ConfigMgr.get_url_skill_json()
	_original_version_config = ConfigMgr._version_config.duplicate(true)
	_original_data_config = ConfigMgr._data_config.duplicate(true)
	_original_reload_markers = ConfigMgr._config_need_reload_by_server.duplicate()
	_original_check_list = ConfigMgr._check_list.duplicate()
	_original_registered = ConfigMgr.get_registered_json_files()
	_user_cache_existed.clear()
	_user_cache_bytes.clear()
	_prepared_cache_basenames.clear()
	for basename: String in CACHE_BASENAMES:
		var backup_error := _backup_user_cache(basename)
		assert_eq(backup_error, OK, "backup must succeed before cleanup")
		if backup_error != OK:
			continue
		var remove_error := _remove_user_cache(basename)
		assert_eq(remove_error, OK, "prepared cache must be removable")
		if remove_error == OK:
			_prepared_cache_basenames.append(basename)
	ConfigMgr.set_url_json("res://tests/fixtures/config/")
	ConfigMgr.set_url_skill_json("res://tests/fixtures/skill/")
	ConfigMgr._version_config.clear()
	ConfigMgr._data_config.clear()
	ConfigMgr.clear_config_need_reload_by_server()
	ConfigMgr._check_list.clear()
	ConfigMgr.clear_registered_json_files_for_tests()


func after_each() -> void:
	# This only resets test-created instances because the registry was swapped.
	BaseJSONConfig.reset_all_instances()
	BaseJSONConfig._instances = _original_instances
	ConfigMgr.set_url_json(_original_url_json)
	ConfigMgr.set_url_skill_json(_original_url_skill_json)
	ConfigMgr._version_config.clear()
	ConfigMgr._version_config.merge(_original_version_config.duplicate(true))
	ConfigMgr._data_config.clear()
	ConfigMgr._data_config.merge(_original_data_config.duplicate(true))
	ConfigMgr.clear_config_need_reload_by_server()
	ConfigMgr._config_need_reload_by_server.append_array(_original_reload_markers)
	ConfigMgr._check_list.clear()
	ConfigMgr._check_list.append_array(_original_check_list)
	ConfigMgr.clear_registered_json_files_for_tests()
	for path: String in _original_registered:
		assert_eq(ConfigMgr.register_json_file(path), OK)
	for basename: String in _prepared_cache_basenames:
		assert_eq(_restore_user_cache(basename), OK, "prepared cache must restore")
#endregion


#region User Cache Safety
func _user_cache_path(basename: String) -> String:
	return OS.get_user_data_dir() + "/configs/" + basename


func _backup_user_cache(basename: String) -> Error:
	var path := _user_cache_path(basename)
	var existed := FileAccess.file_exists(path)
	_user_cache_existed[basename] = existed
	if not existed:
		_user_cache_bytes[basename] = PackedByteArray()
		return OK
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return FileAccess.get_open_error()
	var bytes := file.get_buffer(file.get_length())
	var read_error := file.get_error()
	file.close()
	if read_error != OK:
		return read_error
	_user_cache_bytes[basename] = bytes
	return OK


func _remove_user_cache(basename: String) -> Error:
	var path := _user_cache_path(basename)
	if not FileAccess.file_exists(path):
		return OK
	return DirAccess.remove_absolute(path)


func _restore_user_cache(basename: String) -> Error:
	var path := _user_cache_path(basename)
	if FileAccess.file_exists(path):
		var remove_error := DirAccess.remove_absolute(path)
		if remove_error != OK:
			return remove_error
	if not _user_cache_existed[basename]:
		return OK
	var make_dir_error := DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	if make_dir_error != OK:
		return make_dir_error
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return FileAccess.get_open_error()
	file.store_buffer(_user_cache_bytes[basename] as PackedByteArray)
	var write_error := file.get_error()
	file.close()
	return write_error
#endregion


#region Test Cases
func test_fixture_load_and_dynamic_registration() -> void:
	assert_eq(ConfigMgr.register_json_file(VALID_PATH), OK)
	var config := SampleEventJSONConfig.get_instance(true)
	config.pre_init("", VALID_PATH)
	assert_eq(config.check_init_config(), OK)
	assert_eq(config.get_reward(), 42)
	assert_true(config.is_enabled())


func test_numeric_validation_accepts_integral_values_only() -> void:
	var config := SampleEventJSONConfig.get_instance(true)
	for reward: Variant in [42, 42.0]:
		assert_eq(config.init({"reward": reward, "enabled": true}), OK)
		assert_eq(config.get_reward(), 42)
	for reward: Variant in [42.5, "42", INF, -INF, NAN]:
		assert_eq(config.init({"reward": reward, "enabled": true}), ERR_INVALID_DATA)


func test_optional_default_and_collection_copy() -> void:
	var config := SampleEventJSONConfig.get_instance(true)
	assert_eq(config.init({"reward": 42, "enabled": true}), OK)
	assert_eq(config.get_tiers(), [])
	assert_eq(config.init({"reward": 42, "enabled": true, "tiers": [{"id": 1}]}), OK)
	var caller_copy := config.get_tiers()
	caller_copy[0]["id"] = 99
	assert_eq(config.get_tiers()[0]["id"], 1)


func test_missing_or_malformed_json_stays_unloaded() -> void:
	for file_name: String in ["__dev_godot_config_missing.json", "__dev_godot_config_malformed.json"]:
		var config := SampleEventJSONConfig.get_instance(true)
		config.pre_init("sample_event/", file_name)
		assert_ne(config.check_init_config(), OK)
		assert_false(config.is_loaded())
		assert_null(config.get_data())
		BaseJSONConfig.reset_instance(SampleEventJSONConfig)


func test_successful_server_reload_updates_typed_values_and_clears_marker() -> void:
	ConfigMgr._data_config[RELOAD_PATH] = '{"reward":7,"enabled":true,"tiers":[]}'
	var config := SampleEventJSONConfig.get_instance(true)
	config.pre_init("missing/", RELOAD_PATH)
	assert_eq(config.check_init_config(), OK)
	ConfigMgr._data_config[RELOAD_PATH] = '{"reward":8,"enabled":false,"tiers":[]}'
	ConfigMgr.add_to_config_need_reload_by_server(RELOAD_PATH)
	assert_eq(config.check_init_config(), OK)
	assert_true(config.is_loaded())
	assert_eq(config.get_reward(), 8)
	assert_false(config.is_enabled())
	assert_false(ConfigMgr.check_need_reload_by_server(RELOAD_PATH))


func test_invalid_reload_preserves_prior_typed_and_raw_data() -> void:
	ConfigMgr._data_config[RELOAD_PATH] = '{"reward":7,"enabled":true,"tiers":[{"id":1}]}'
	var config := SampleEventJSONConfig.get_instance(true)
	config.pre_init("missing/", RELOAD_PATH)
	assert_eq(config.check_init_config(), OK)
	# BaseJSONConfig.get_data() is diagnostic/test-only; game callers use typed accessors.
	var raw_before := (config.get_data() as Dictionary).duplicate(true)
	ConfigMgr._data_config[RELOAD_PATH] = '{"reward":7.5,"enabled":true,"tiers":[]}'
	ConfigMgr.add_to_config_need_reload_by_server(RELOAD_PATH)
	assert_eq(config.check_init_config(), ERR_INVALID_DATA)
	assert_false(config.is_loaded())
	assert_eq(config.get_reward(), 7)
	assert_eq(config.get_data(), raw_before)
	assert_true(ConfigMgr.check_need_reload_by_server(RELOAD_PATH))


func test_singleton_reset_returns_distinct_unloaded_instance() -> void:
	var first := SampleEventJSONConfig.get_instance(true)
	BaseJSONConfig.reset_instance(SampleEventJSONConfig)
	var second := SampleEventJSONConfig.get_instance(true)
	assert_ne(first, second)
	assert_false(second.is_loaded())
#endregion
```

`BaseJSONConfig.get_data()` is diagnostic/test-only. Game callers use typed, defensive accessors such as `get_tiers()`.

## Focused command

```powershell
$godotExe = 'D:\workspace\STM-Godot\godot-client-template\godot.exe'
& $godotExe --headless --path . -s addons/gut/gut_cmdln.gd `
  -gtest=res://tests/unit/features/sample_event/test_sample_event_json_config.gd -gexit -gconfig=
```

## Same-schema family cases

A family-loader suite additionally verifies:

- two instances bind different registered paths and expose independent typed/raw values;
- a reload marker for source A changes only A, not B;
- binding the same ID/path twice is idempotent, while any different ID or path returns `ERR_ALREADY_IN_USE`;
- the caller cache returns the same instance by source key and rejects duplicate keys; and
- caller teardown calls `reset()` on every owned instance and clears the keyed cache.

Do not call `BaseJSONConfig.reset_instance(FamilyLoader)` for caller-owned family instances: they were deliberately never added to the static script-keyed registry.
