# Canonical Godot UI scene trees

Use these shapes when recording UI and client-side presentation decisions in the main feature spec. A `Control` UI surface has a texture-free root named `imageRoot` whose script directly extends `BaseScreen`, and a texture-free content wrapper named `imageBg` below it. A non-`Control` world/render scene uses a root and direct base class appropriate to its responsibility, such as `Node2D`, `Area2D`, or `Camera2D`. Folder location never determines inheritance. Names are stable binding contracts, not decoration; use feature-specific suffixes where needed.

The root and the wrapper are two different jobs, which is why they are two nodes. The framework owns `imageRoot`: it carries the script, it is what a parent or `GuiService` attaches and detaches, and `show_gui()` calls `move_to_front()` on it. The subclass owns `imageBg`: it is the node presentation code animates for show, hide, slide and fade. A full-screen background must therefore be a **sibling** of `imageBg`, never its child, or every content animation drags the background along with it.

This mirrors the Cocos layout the ported screens come from, where an outer `Layer` holds `image_FullBg` and `image_Bg` side by side. Note the name shifts meaning between the two toolchains: Cocos calls its *content wrapper* `image_Bg`, which maps to `imageBg` here, while the outer `Layer` maps to `imageRoot`. Reading `imageBg` as "the root" is the mistake this split exists to prevent.

Read the exact approved `Source root` from the feature spec. Place every proposed pair below `<source_root>/ui/`; never reconstruct that path from `feature_id`. Group only complete same-stem `.tscn`/`.gd` pairs by a real functional surface such as `ui/lobby/` or `ui/popup/`.

## Scene classification and inheritance

- Classify a pair from its runtime responsibility and root node type, never from the `ui/` path segment.
- A `Control` full screen, popup, layer, slot, or other UI surface directly extends `BaseScreen` and follows the `image...`, `btn...`, `label...`, and `text...` binding rules below.
- A non-`Control` world/render pair directly extends the Godot class its behavior requires. Examples include `Node2D` for a battle world or render composition, `Area2D` for an interactive world entity, and `Camera2D` for a camera controller.
- Every classified scene still requires a same-stem `.tscn`/`.gd` pair, a full feature-prefixed stem, matching PascalCase `class_name`, explicit lifecycle owner, and automated plus manual verification.
- A world scene may contain `Control` children such as world-space labels or health bars without becoming a `BaseScreen`. Name them by type, exactly as a `Control` UI surface would, so a reader never has to know which scene family a node lives in to predict its name. Record which owner handles their input, layout, and localization.
- In a world scene `BaseScreen` machinery does not run. A `btn...` node there is not auto-connected and a `text...` `Label` is not swapped for a `CustomLabel`, so wire the signal and author the `CustomLabel` explicitly. `label...` and `image...` trigger nothing either way, so they carry no such caveat.

## Scene, script, and class names

- Use the full snake_case feature ID as every owned UI file prefix: `<feature_id>_<surface_role>`.
- Pair each scene and script with the exact same stem: `<stem>.tscn` and `<stem>.gd`. Never shorten or omit a multiword feature ID.
- Derive `class_name` by converting the full stem to PascalCase; underscores separate words and do not appear in the class name.
- Use a surface role that states ownership clearly, such as `main_gui`, `popup`, `lobby_icon`, `reward_slot`, `tab`, `item`, or `layer`.

| Feature ID | Scene | Script | `class_name` |
|---|---|---|---|
| `shop` | `shop_main_gui.tscn` | `shop_main_gui.gd` | `ShopMainGui` |
| `offer_dynamic` | `offer_dynamic_popup.tscn` | `offer_dynamic_popup.gd` | `OfferDynamicPopup` |
| `offer_dynamic` | `offer_dynamic_lobby_icon.tscn` | `offer_dynamic_lobby_icon.gd` | `OfferDynamicLobbyIcon` |

## Shared checks for `Control` UI surfaces

- Record each node path, Godot type, script binding, anchors/offsets or container owner, mouse filter, and texture owner.
- Every node name starts with one canonical prefix: `image...` for structural, visual, scrolling, and container nodes; `btn...` for buttons; `label...` for plain `Label`; `text...` for rich `CustomLabel`. `image...` is intentionally the broadest group, including `Control`, `TextureRect`, `ScrollContainer`, and `Container` subclasses.
- `imageRoot` is the texture-free root `Control` and `imageBg` is the texture-free content wrapper directly below it. Every surface has both, with no exception for small ones: a slot that owns nothing to animate today still gets the wrapper, because deciding per scene is what makes a tree unpredictable to read. Reloadable backgrounds are separate `TextureRect` nodes so texture and content lifecycles do not become coupled.
- An added wrapper is one more `Control` in the input chain, so declare its `mouse_filter`. A full-rect wrapper left at the `Control` default of `STOP` swallows every click and leaves the surface silently dead. `IGNORE` is right unless the wrapper itself must take input.
- `custom_minimum_size` stays on `imageRoot`, because a parent `Container` sizes the root and not the wrapper. The wrapper anchors full rect inside it.
- Decorative controls use `mouse_filter = IGNORE`. The interactive `Button` owns the hit target. Declare it explicitly rather than relying on the type default, because the defaults differ: `Label` is already `IGNORE`; `TextureRect` and box containers are `PASS`, which still lets the click reach the button; `ColorRect`, `RichTextLabel`, `Control`, and `PanelContainer` are `STOP` and will swallow the click, leaving the button silently dead.
- Record who reloads locale/theme textures. Do not hide ownership behind the scene tree.
- A scene variant may share one tree only when lifecycle, presentation, binding, and behavior remain the same.

## Non-`Control` world and render scene

Use a domain-specific tree for presentation that exists in world space. Its root is not `imageRoot`, it has no `imageBg` wrapper, and nodes that are not `Control` take domain-role names rather than a `Control` prefix. A `Control` child of such a tree still takes the prefix its type calls for, because the naming rule follows the node's type and not the scene it lives in.

```text
RoomBattleWorld (Node2D; RoomBattleWorld script extends Node2D)
├── Terrain (Node2D or TileMapLayer; visual/map owner)
├── Paths (Node2D; route visualization owner)
├── Towers (Node2D; tower view owner)
├── Enemies (Node2D; enemy view owner)
├── Projectiles (Node2D; projectile view owner)
└── BattleCamera (Camera2D; paired camera script when independently stateful)
```

Record world-unit scale, draw order, camera/canvas ownership, input routing, spawn/despawn owner, and the boundary between presentation and gameplay state. If an entity or camera has independent stateful behavior, give it its own same-stem `.tscn`/`.gd` pair and correct direct Godot base class. Nodes that are not `Control` use domain-role names here, and the type-based `Control` prefixes still apply to any `Control` child.

## Full screen

```text
imageRoot (Control; EventMainScreen script extends BaseScreen; full rect; texture-free)
├── imageFullBg (TextureRect; full rect; bottom-most; mouse ignore)
└── imageBg (Control; full rect; texture-free content wrapper; animation target)
    ├── labelTitle (Label)
    ├── imageBgRewardList (ScrollContainer)
    │   └── imageBgRewardContainer (VBoxContainer)
    └── btnClose (Button; transparent hit target)
        └── imageBtnClose (TextureRect; mouse ignore)
```

`imageFullBg` is an independent sibling of `imageBg` and never parents content, so fading or sliding the content leaves the background where it is. A background needs no code to stretch: full-rect anchors plus `expand_mode` cover it, including inside a `CanvasLayer`. Record navigation owner (`ScreenMgr`/`SceneService` or the approved equivalent), viewport anchors, safe-area behavior, and whether the background texture reloads on locale/theme changes.

## Popup

```text
imageRoot (Control; RewardPopup script extends BaseScreen; full rect; mouse STOP; texture-free)
└── imageBg (Control; centered; texture-free content wrapper; animation target)
    ├── imageBg2 (TextureRect; reloadable background; mouse ignore)
    ├── imageBgContent (Control; sibling of imageBg2)
    │   ├── labelTitle (Label)
    │   └── imageBgRewardContainer (VBoxContainer)
    └── btnClose (Button; transparent hit target)
        └── imageBtnClose (TextureRect; mouse ignore)
```

A popup has no `imageFullBg`; its own frame art is `imageBg2` inside the wrapper, with `imageBgContent` beside it rather than under it. That is the same rule as one level up, applied again: at every level the art and the content it sits behind are siblings, so neither one's lifecycle or animation drags the other. `imageRoot` covers the full rect at `mouse_filter = STOP` so the popup blocks whatever sits behind it, while `imageBg` is centred and is what a show or hide animation moves. Record direct-parent versus `GuiService` presentation, who attaches/detaches the popup, and manual fog opacity/input blocking. Fog and presentation are subclass decisions, never consequences of inheritance.

## Manually centered icon or slot

Use this for lobby icons and free-positioned slots whose owner places an origin point.

```text
imageRoot (Control; EventLobbyIcon script extends BaseScreen; center-origin; texture-free)
└── imageBg (Control; full rect; texture-free; mouse IGNORE; animation target)
    ├── imageIcon (TextureRect; mouse ignore)
    ├── labelTimer (Label; centered)
    └── btnOpen (Button; transparent hit target)
```

The wrapper is here even though an icon owns no background to keep out of the way, because one shape with no per-scene judgement is what makes these trees readable at a glance. It costs one node and one `mouse_filter` line, and it is already in place the day the icon needs to pop or fade. Record the visual size and offsets (for example left/top `-48`, right/bottom `48`) rather than baking viewport coordinates into the scene. The owning screen positions the root origin.

## Container-managed slot

```text
imageRoot (Control; RewardSlot script extends BaseScreen; minimum size; texture-free)
└── imageBg (Control; full rect; texture-free; mouse IGNORE; animation target)
    ├── imageSlotBg (TextureRect; full rect; mouse ignore)
    ├── imageReward (TextureRect; mouse ignore)
    ├── labelAmount (Label)
    └── btnClaim (Button; transparent hit target)
```

Record `custom_minimum_size` and the parent `Container` type, and keep `custom_minimum_size` on `imageRoot`: the container sizes the root, not the wrapper. The parent container owns slot position and final size; the slot must not declare manual viewport coordinates or fight the container with absolute positioning.

## `Control` screen embedding a world

Use this when a `Control` surface hosts a non-`Control` world that owns a `Camera2D`, such as a battle or
map screen. It is the one shape where a single `imageBg` wrapper does not appear, and the reason is the
engine rather than a preference: a `Camera2D` transforms **its own** canvas layer, so anything that must not
pan or zoom with the camera has to live on a different `CanvasLayer`.

```text
imageRoot (Control; RoomBattleScreen script extends BaseScreen; full rect; mouse PASS; texture-free)
├── imageBgLayer (CanvasLayer; layer -10)
│   └── imageFullBg (TextureRect; full rect; mouse ignore)
├── imageWorldArea (Control; full rect; mouse ignore)
│   └── imageWorldHost (Node2D; hosts the world scene and its Camera2D)
└── imageHudLayer (CanvasLayer; layer 10)
    └── imageHudRoot (Control; full rect; HUD animation target)
```

Three layers, ordered by `layer`: background below the world, world on the default layer with the camera,
HUD above. The wrapper role is split — `imageHudRoot` is what a HUD animation targets, and the background
already sits on its own layer, so nothing needs to be kept out of the way. Record which layer owns the
camera, which owns input, and the `layer` value of each `CanvasLayer`; ordering by tree position instead
would be silently wrong, because a `CanvasLayer` ignores it.

## Transparent button hit target

```text
btnClaim (Button; transparent normal/hover/pressed/focus styles)
├── imageBtnClaim (TextureRect; mouse ignore)
├── imageBtnClaimDisable (TextureRect; mouse ignore; hidden; state art)
└── labelBtnClaim (Label; mouse ignore; optional)
```

Size the `Button` for interaction independently from its visual children. Keep visuals inside the button so they move with the hit target, but never let them intercept input. Binding remains `btnClaim`; `BaseScreen` owns conventional button routing.

Naming a button's children after the button, as `imageBtnClaim` and `labelBtnClaim`, is the preferred shape: the name states which hit target owns the node, and it stays correct when the content is reworded. When one button needs several children of the same kind, keep the button stem and put the role last, as `imageBtnClaimBg` or `imageBtnClaimDisable`.

For a button with more than one visual state, prefer one node per state over reloading a texture on a single node. A disabled or selected look is a second hidden `TextureRect` beside the first, and switching state sets `visible` on two nodes. State then lives in the scene where it can be reviewed, instead of in a runtime texture swap whose art path exists only in code.

## Stateful group wrapper

```text
imageBgRewardGroup (Control; stable visibility/opacity/animation owner)
├── imageBgRewardGroup2 (TextureRect; reloadable group background; mouse ignore)
└── imageBgRewardGroupContent (Control; sibling of imageBgRewardGroup2)
    ├── labelProgress (Label)
    └── imageBgRewardContainer (HBoxContainer)
```

Use a wrapper only when the nodes change visibility, opacity, transform, or animation together. The point is that nodes sharing one state share one parent, so later code toggles a single node instead of walking a list. The `...Group` name is a convention for that role, not a requirement; a wrapper is identified by owning shared state, not by its name.

The wrapper stays texture-free; a reloadable background is a separate child beside group content. A wrapper that draws its own background, such as a `PanelContainer` using the theme panel, couples the background to the content: it can no longer be reloaded on a theme or locale change on its own, and content cannot animate without the panel following.

## Plain and rich text

```text
labelDescription (Label; plain localized text)
textRewardDetail (CustomLabel; Cocos color/size/opacity tags)
```

Use `label...` with `Label` for plain text. Author every new `text...` node directly as `CustomLabel`, including `bbcode_enabled`, fit/wrap behavior, defaults, and alignment decisions required by the content. `BaseScreen` converting a `text...` `Label` at runtime is a legacy/import fallback, not the default for a new scene.

## Per-scene review

- The scene exists because it owns an independent lifecycle/presentation flow or reusable stateful/repeated behavior.
- Scene and script share the full `<feature_id>_<surface_role>` stem; `class_name` is that complete stem converted to PascalCase.
- A `Control` UI surface root is `imageRoot` with an `imageBg` content wrapper below it, its script directly extends `BaseScreen`, the animation target and any full-screen background are siblings rather than parent and child, and presentation owner and fog are explicit. A screen embedding a world with a camera is the one shape without a single `imageBg`, and its `CanvasLayer` values are recorded. A non-`Control` world/render root has an explicit domain-role name, correct root/base-class match, lifecycle owner, camera/canvas boundary, and no inherited fog assumption.
- Manual UI placement has a declared origin and offsets; container placement has minimum size and a named container owner. World/render placement instead records world-unit scale, coordinate owner, draw order, and camera relationship.
- UI hit targets are transparent buttons and decorative `Control` children ignore mouse input. World interaction records its explicit input owner and collision/picking contract.
- A node name follows the node's type in every scene: `btn...` for `BaseButton`, `label...` for `Label`, `text...` for `CustomLabel`, and `image...` for every other `Control`, including `Control` itself and `TextureRect`, `ColorRect`, `ScrollContainer` and `Container` subclasses. Nodes that are not `Control` use explicit domain-role names. Names bind predictably, and every texture/reload/localization/rich-text decision has one owner where applicable.
