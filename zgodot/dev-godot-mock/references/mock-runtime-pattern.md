# Canonical Mock Runtime Pattern

Adapt this single complete example to the real feature packet classes, command IDs, fields, and retained neutral optional-boundary constants/defaults discovered during inspection. `PoolFunction` only dispatches; it does not own feature-specific IDs.

```gdscript
extends RefCounted

const VALID_CASES: Array[StringName] = [&"success", &"empty", &"expired", &"error"]
const VALID_FLOWS: Array[StringName] = [&"main", &"popup"]


#region Public API
func run(case_id: StringName, flow_id: StringName, options: Dictionary = {}) -> Error:
	if case_id not in VALID_CASES or flow_id not in VALID_FLOWS:
		return ERR_INVALID_PARAMETER
	var delivery_error := apply_case(case_id, options)
	if delivery_error != OK:
		return delivery_error
	if case_id == &"error":
		return OK
	return run_flow(flow_id, options)


func apply_case(case_id: StringName, options: Dictionary = {}) -> Error:
	var packet := SampleEventRecvLoadInfo.new()
	packet.cmd_id = CmdDefine.SAMPLE_EVENT_LOAD_INFO
	packet.error_code = 1 if case_id == &"error" else 0
	packet.items = [] if case_id in [&"empty", &"expired"] else options.get("items", [{"id": 1}])
	packet.expired = case_id == &"expired"
	return NetworkService.dispatch_mock_packet(packet)


func run_flow(flow_id: StringName, options: Dictionary = {}) -> Error:
	match flow_id:
		&"main":
			PoolFunction.do_func(
				SampleEventOptionalBoundary.SHOW_MAIN,
				[],
				SampleEventOptionalBoundary.DEFAULT_SHOW_MAIN,
			)
			return OK
		&"popup":
			var packet := SampleEventRecvPush.new()
			packet.cmd_id = CmdDefine.SAMPLE_EVENT_PUSH
			packet.error_code = 0
			packet.payload = options.get("push", {})
			var delivery_error := NetworkService.dispatch_mock_packet(packet)
			if delivery_error != OK:
				return delivery_error
			PoolFunction.do_func(
				SampleEventOptionalBoundary.SHOW_POPUP,
				[],
				SampleEventOptionalBoundary.DEFAULT_SHOW_POPUP,
			)
			return OK
	return ERR_INVALID_PARAMETER
#endregion
```

The `error` case still dispatches its typed nonzero-error packet through the production handler, then `run()` returns `OK` without invoking a UI flow. For other cases, the state-producing `dispatch_mock_packet()` call must complete before either UI `PoolFunction` call. Never import or mutate `SampleEventUtil` or its model directly.

Add the runtime and editable config together to `devtools/mock_loader.gd`:

```gdscript
const BUILTIN_ENTRIES: Dictionary = {
	&"sample_event": {
		"mock_script_path": "res://devtools/mocks/sample_event/sample_event_mock.gd",
		"config_path": "res://devtools/mocks/sample_event/mock-current.json",
	},
}
```

Add the real key invocation to the existing `KEY_M` branch in `CheatInput._handle_dev_key()`:

```gdscript
KEY_M:
	_run_dev_mock(&"sample_event")
```

`CheatInput._run_dev_mock()` must retain its dynamic `ResourceLoader` path; do not statically import `devtools`.
