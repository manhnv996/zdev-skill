# Optional dependency boundaries

| Need | Preferred mechanism | Reason |
|---|---|---|
| Same-feature synchronous work | Direct module/util method | Compile-time ownership is clear |
| Same-feature notification | Semantic signal | Multiple presentation consumers can react |
| Cross-feature optional provider | `PoolFunction` | Core stays loadable when provider is absent |

Only use the function pool at an optional cross-feature boundary. Namespace every `StringName`, assign one live owner, pass an explicit default, and remove registrations when the provider ends. The retained neutral optional-boundary contract is authoritative for every stable action/query ID and default; `PoolFunction` only registers and dispatches callbacks and owns no feature-specific constants. Keep the neutral contract in consumer/core composition, never in a removable provider feature: `modules/game/contracts/sample_event_optional_boundary.gd` remains when that provider is deleted.

```gdscript
# modules/game/contracts/sample_event_optional_boundary.gd
class_name SampleEventOptionalBoundary
extends RefCounted

const OPEN_RELATED: StringName = &"sample_event.open_related"
const HAS_RELATED: StringName = &"sample_event.has_related"
const DEFAULT_OPEN_RELATED: bool = false
const DEFAULT_HAS_RELATED: bool = false
```

## Provider implementation

This example assumes the provider's explicitly approved source root is `modules/game/event/sample_event_related`.

```gdscript
# modules/game/event/sample_event_related/sample_event_related_module.gd
class_name SampleEventRelatedModule
extends BaseModule

const MODULE_ID: StringName = &"sample_event_related"

#region Lifecycle
func on_init() -> void:
	var open_error := PoolFunction.reg_func(SampleEventOptionalBoundary.OPEN_RELATED, self, open_related)
	var has_error := PoolFunction.reg_func(SampleEventOptionalBoundary.HAS_RELATED, self, has_related)
	if open_error != OK or has_error != OK:
		push_error("could not register sample_event optional provider")


func on_destroy() -> void:
	NetworkService.unsubscribe_all(self)
	PoolFunction.remove_all(self)
#endregion


#region Optional Boundary API
func open_related() -> bool:
	return true


func has_related() -> bool:
	return true
#endregion
```

```gdscript
# modules/game/game_feature_registry.gd -- global composition root
if ModuleMgr.register_factory(SampleEventRelatedModule.MODULE_ID, SampleEventRelatedModule) != OK:
	push_error("could not register SampleEventRelatedModule")
elif ModuleMgr.open_module(SampleEventRelatedModule.MODULE_ID) == null:
	push_error("could not open SampleEventRelatedModule")
```

## Consumer call

```gdscript
func try_open_related() -> bool:
	return PoolFunction.do_func(
		SampleEventOptionalBoundary.OPEN_RELATED,
		[],
		SampleEventOptionalBoundary.DEFAULT_OPEN_RELATED,
	)
```

```gdscript
extends GutTest

func before_each() -> void:
	ModuleMgr.clear_for_tests()


func after_each() -> void:
	ModuleMgr.clear_for_tests()


func test_provider_removal_returns_explicit_default() -> void:
	assert_eq(
		ModuleMgr.register_factory(SampleEventRelatedModule.MODULE_ID, SampleEventRelatedModule),
		OK,
	)
	var provider := ModuleMgr.open_module(SampleEventRelatedModule.MODULE_ID) as SampleEventRelatedModule
	assert_not_null(provider)
	assert_true(PoolFunction.do_func(
		SampleEventOptionalBoundary.HAS_RELATED,
		[],
		SampleEventOptionalBoundary.DEFAULT_HAS_RELATED,
	))
	assert_eq(ModuleMgr.close_module(SampleEventRelatedModule.MODULE_ID), OK)
	provider = null
	assert_false(PoolFunction.do_func(
		SampleEventOptionalBoundary.HAS_RELATED,
		[],
		SampleEventOptionalBoundary.DEFAULT_HAS_RELATED,
	))
```

The caller imports only `SampleEventOptionalBoundary`, never `SampleEventRelatedModule`; closing or removing the provider module leaves the neutral contract and defaults intact. `ModuleMgr.close_module()` invokes `on_destroy()` and repeats owner cleanup defensively. Do not use this mechanism to dispatch a feature's own UI or module method.
