# UI patterns

## Required base and responsibility split

Every new or ported `Control` UI surface directly extends `BaseScreen`: full screens, popups, layers, slots, items, tabs, and icons. `BaseScreen` supplies child binding, localization state, keyboard handling, standard button routing, fog primitives, and show/hide state. Non-`Control` world/render scenes placed below `ui/` use their appropriate `Node2D`-family base and do not inherit `BaseScreen`. The subclass chooses its parent, presentation owner, manual fog, animation, and detachment behavior. `GuiBase` and `GuiQueueBase` are compatibility-only classes, not bases for generated `Control` UI.

Choose one presentation pattern per surface: direct parent popup, `GuiService` overlay, or embedded component. A module may lazily construct UI, but the UI subclass owns how it is presented.

## .tscn child binding

Use conventional scene-node names and typed properties. `btn_Close` binds to `btnClose` and `label_Title` binds to `labelTitle` during `_ready()`. If special mappings are needed, override `resolve_node_references()` and call `super.resolve_node_references()` before them. Do not add `.pressed.connect`: `BaseScreen` already routes `button_down` and `button_up`.

```gdscript
class_name RewardPopup
extends BaseScreen

var btnClose: Button
var labelTitle: Label


func on_touch_ended(btn: BaseButton) -> void:
	super.on_touch_ended(btn)
	if btn == btnClose:
		hide_gui()
```

## Direct parent popup

Use direct presentation when the popup belongs to the current screen and its subclass owns reparenting and removal. Add fog before attaching, refresh before the base lifecycle call, and remove fog before the base hide lifecycle and detachment.

```gdscript
class_name ChannelScreen
extends BaseScreen


#region Presentation
func show_gui(channel_id_force: int = -1) -> void:
	var parent_screen := ScreenMgr.get_curr_screen()
	if parent_screen == null:
		push_warning("ChannelScreen: current screen is unavailable")
		return

	show_disable()
	if get_parent() != parent_screen:
		if get_parent() != null:
			get_parent().remove_child(self)
		parent_screen.add_child(self)

	_reload_channel(channel_id_force)
	super.show_gui()


func hide_gui() -> void:
	hide_disable()
	super.hide_gui()
	if get_parent() != null:
		get_parent().remove_child(self)
#endregion
```

## GuiService overlay

Use an overlay when `GuiService` owns stacking. The subclass still controls its manual fog and calls the service; inheritance does not choose the service. This immediate pattern starts the `BaseScreen` lifecycle only after `GuiService.show()` has attached the node. Do not copy it with `queue` or `unique`: queueing can defer attachment and uniqueness can reject/free the node. Those flows need explicit `gui_shown` and rejection ownership before starting the lifecycle.

```gdscript
class_name RewardPopup
extends BaseScreen


#region Presentation
func show_gui() -> void:
	show_disable(70.0)
	GuiService.show(self, {
		"z_index": 10,
	})
	_reload_reward()
	super.show_gui()


func hide_gui() -> void:
	hide_disable()
	super.hide_gui()
	GuiService.hide(self)
#endregion
```

## Embedded component

Use an embedded component when the owning parent controls placement. It can still use `BaseScreen` mechanics, while visibility remains a local presentation decision.

```gdscript
class_name RewardSlot
extends BaseScreen


func show_gui() -> void:
	visible = true
	super.show_gui()


func hide_gui() -> void:
	super.hide_gui()
	visible = false
```

## Module signals during retained UI lifecycle

UI calls public module methods and subscribes only to semantic module signals. For retained nodes that leave and re-enter the tree, `_ready()` alone is insufficient: connect idempotently in `show_gui()` before refresh and `super.show_gui()`, then disconnect in `hide_gui()` before `super.hide_gui()`.

```gdscript
#region Module Signals
func _connect_module_signals() -> void:
	var module := ModuleMgr.get_module(RewardModule.MODULE_ID) as RewardModule
	if module != null and not module.balance_changed.is_connected(_on_balance_changed):
		module.balance_changed.connect(_on_balance_changed)


func _disconnect_module_signals() -> void:
	var module := ModuleMgr.get_module(RewardModule.MODULE_ID) as RewardModule
	if module != null and module.balance_changed.is_connected(_on_balance_changed):
		module.balance_changed.disconnect(_on_balance_changed)


func _on_balance_changed(balance: int) -> void:
	labelBalance.text = Utility.number_to_str(balance)
#endregion
```

## Button routing

Override `on_touch_ended(btn: BaseButton)`, call `super.on_touch_ended(btn)` first, and branch on the bound button reference. Do not add button signal connections in `_ready()`, refresh methods, or presentation methods: `BaseScreen` connects conventional button nodes once.

## Localization

For a retained popup whose text must wait until it is presented, preserve the deferred-localization state:

```gdscript
func localize() -> void:
	if not _is_showing:
		_change_localize = true
		return
	_change_localize = false
	labelTitle.text = tr("reward_title")
```

For an embedded item or slot, localize when binding its data; it does not need a showing-state guard:

```gdscript
func set_info(reward_amount: int) -> void:
	localize()
	labelAmount.text = Utility.number_to_str(reward_amount)


func localize() -> void:
	labelName.text = tr("reward_name")
```

## Network boundary

UI does not call `NetworkService.subscribe`, `NetworkService.send_packet`, packet constructors, or receive handlers. It calls a public method on the feature module and reacts to semantic signals.

## Implementation checklist

- Read this reference before each presentation script; extend `BaseScreen` directly for `Control` UI and use the approved non-`Control` node base for world/render scenes.
- Choose and document one presentation owner per surface; add manual fog only where the subclass needs it.
- Bind conventional `.tscn` children through `BaseScreen`; call `super.resolve_node_references()` before special mappings.
- Order retained-popup work as connect signals, refresh, `super.show_gui()`; order hide as disconnect signals, `super.hide_gui()`, then local detachment when needed.
- Route buttons through `on_touch_ended()` and keep UI packet-free.
