# Module lifecycle pattern

Feature modules extend `BaseModule`, therefore are `RefCounted` lifecycle objects rather than UI Nodes. Construct util/model state in the module, subscribe eagerly in `on_init()`, reset state in `on_reset()`, and release subscriptions and optional actions in `on_destroy()`. Call the `NetworkService` autoload directly; do not weaken its API behind a `Node` alias or retain any UI Node.

The approved feature-local module path is `<source_root>/<feature_id>_module.gd`; copy `<source_root>` from the spec rather than assuming a grouping folder.

```gdscript
class_name SampleEventModule
extends BaseModule

const MODULE_ID: StringName = &"sample_event"
const CMD_LOAD_INFO: int = 7101

signal info_changed(info: SampleEventInfo)
signal load_failed(error_code: int)

var _util: SampleEventUtil = SampleEventUtil.new()
var _required_profile: ProfileModule


#region Lifecycle
func on_init() -> void:
	# The composition root opened declared dependencies before this module.
	_required_profile = ModuleMgr.get_module(ProfileModule.MODULE_ID) as ProfileModule
	if _required_profile == null:
		push_error("sample_event requires ProfileModule")
		return
	NetworkService.subscribe(CMD_LOAD_INFO, SampleEventRecvLoadInfo, _on_recv_load_info)


func on_reset() -> void:
	_util.reset()


func on_destroy() -> void:
	NetworkService.unsubscribe_all(self)
	PoolFunction.remove_all(self)
	_required_profile = null
#endregion


#region Public Feature API
func request_load_info() -> void:
	var packet := SampleEventSendLoadInfo.new()
	NetworkService.send_packet(packet)


func get_info() -> SampleEventInfo:
	return _util.get_info()
#endregion


#region Typed Packet Handling
func _on_recv_load_info(packet: SampleEventRecvLoadInfo) -> void:
	if not packet.is_ok():
		load_failed.emit(packet.error_code)
		return
	_util.set_info(packet.info)
	info_changed.emit(packet.info)
#endregion
```

```gdscript
# modules/game/game_feature_registry.gd -- composition root
static func register_all() -> void:
	if ModuleMgr.register_factory(ProfileModule.MODULE_ID, ProfileModule) != OK:
		push_error("could not register ProfileModule")
		return
	if ModuleMgr.register_factory(
		SampleEventModule.MODULE_ID,
		SampleEventModule,
		[ProfileModule.MODULE_ID],
	) != OK:
		push_error("could not register SampleEventModule")
		return
	if ModuleMgr.open_module(SampleEventModule.MODULE_ID) == null:
		push_error("could not eagerly open SampleEventModule")
```

`ModuleMgr` owns module construction/closing and resolves the declared dependency graph before `on_init()`; the module reads the required typed dependency with `get_module()`. The module repeats `unsubscribe_all(self)` and `remove_all(self)` so its direct lifecycle remains safe. Keep UI access weak and event-driven: a module emits semantic signals and never stores a strong `Node`, `Control`, screen, popup, or scene reference.
