---
name: dev-tracking
description: Use when adding BidaMobile client tracking logs for fixed GUI or flow points in feature/event modules, especially calls to PoolFunction.SYSTEM_LOG_CLIENT, GroupLogDefine.js, gc.GROUP_NAME_LOG, or gc.FEATURE_NAME.
argument-hint: "[feature folder | JS file | feature name]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Edit
model: sonnet
---

# dev-tracking - BidaMobile Client Tracking

Add client tracking for existing feature/event GUI flows. The core rule: **confirm missing or inferred information before implementation**:

1. Confirm tracking group and feature key only when missing, inferred, ambiguous, or not present in `GroupLogDefine.js`.
2. Always confirm the GUI/flow action map before editing code.

Short prompts are valid, for example: `dung dev-tracking cho feature {featureName}` or `/dev-tracking src/game/event/{featureName}`.
Prompts with explicit names are also valid, for example: `dung dev-tracking cho feature {featureName} voi group name {group}, feature name {feature}`.

## Step 0: Gather Scope

Read the user prompt first. If a path is provided, use it. If not, infer candidate paths from the active files or feature name.

Scan:
- Feature folder, usually `src/game/event/{feature}/` or `src/game/{feature}/`
- Existing tracking calls: `PoolFunction.doFunc(PoolFunction.SYSTEM_LOG_CLIENT`
- Defines: `src/game/system/logic/GroupLogDefine.js`
- System behavior: `src/game/system/SystemModule.js`, methods `logClient` and `logClientStep`

Reference examples:
- `src/game/event/monthlygratitude`
- `src/game/event/bpcustom`

## Step 1: Resolve Names, Maybe Stop

After scope scan and before building implementation details, resolve the tracking names from the prompt and `GroupLogDefine.js`.

If the prompt already provides both group name and feature name:
- Treat each value as either a key (`gc.GROUP_NAME_LOG.event_action_log`) or a value (`"event_action_log"`).
- Check `GroupLogDefine.js` and map values back to keys when possible.
- If both resolve to existing keys, mark Gate 1 as already confirmed and continue to Step 2.
- If either one is missing, ambiguous, or would require adding a new key, stop and ask for confirmation before continuing.

If the prompt does not provide both names, propose:

```text
Group log key: gc.GROUP_NAME_LOG.{suggested_group_key} = "{suggested_group_value}"
Feature key: gc.FEATURE_NAME.{suggested_feature_key} = "{suggested_feature_value}"

Gate 1: I will use these for all tracking in {feature}. OK?
```

Suggestion rules:
- Event features commonly use `gc.GROUP_NAME_LOG.event_action_log`.
- Battle pass variants commonly use `gc.GROUP_NAME_LOG.battle_pass_log`.
- Feature key should match existing analytics style: snake_case value, e.g. `monthly_gratitude`, `battlepass_custom_2`.
- If there is already a matching key in `GroupLogDefine.js`, propose reusing it.
- If the key is missing, say that it will be added to `GroupLogDefine.js`.

**Do not edit code from Step 1.** If Gate 1 was not already satisfied by explicit existing names, wait for user confirmation. If the user changes either name, use the user's choice.
After Gate 1 is satisfied, continue to Step 2.

## Step 2: Build Tracking Map, Then Stop

Trace the feature's actual GUI and module flow, then classify each candidate into a shared tracking category. **Do not copy every action from reference modules.**

Core categories:

| Category | When to log | Common action pattern | Required? |
|---|---|---|---|
| Event availability | Server load-info says the feature/event is active | `have_event` | Yes for event features with load info |
| Entry point click | Player taps lobby icon or fixed entry button | `click_lobby`, `click_{entry}` | Yes when the entry exists |
| Main screen open | Main GUI is actually shown | `enter_event` | Yes when feature has main GUI |
| Popup shown | Any auto/manual popup is shown | `popup_show` or `popup_{popup_id}_show` | Only when popup exists |
| Popup CTA | Primary button inside popup is tapped | `popup_click_join` or `popup_{popup_id}_click_{cta}` | Only when popup has CTA |
| Monetization CTA | Buy/upgrade/payment action starts | `{surface}_click_buy`, `{surface}_click_upgrade` | Only when feature has payment CTA |

Action naming:
- Prefer existing action names already used in the same feature.
- Use the generic popup names (`popup_show`, `popup_click_join`) when there is only one intro/join popup.
- Use subtype names (`popup_buy_pass_show`, `popup_end_pass_show`) only when the feature has multiple meaningful popup types and the subtype matters for analytics.
- Treat `popup_buy_pass_show`, `popup_end_pass_show`, and similar names as examples from BP Custom, not required actions.

Client vs server tracking:
- Add client logs for UI visibility and client-only intent: event availability, entry click, main screen open, popup show, popup CTA, buy/upgrade click.
- Prioritize buy/payment clicks because IAP/payment flows can leave the game client before a normal feature server action is recorded.
- Do not add client logs by default for actions that immediately send a feature packet and can be logged on server, such as claim/receive reward.
- Only add claim/send-packet CTA client logs when the user explicitly asks for client-side intent tracking or when the action can fail before reaching server.

For `have_event`, log only when the event is active. Follow local pattern:
- Monthly Gratitude logs in `cmdReceiveMonthlyGratitudeLoadInfo` success.
- BP Custom logs in `cmdReceiveBPCustomLoadInfo` success only when `!cmd.isEndEvent`.

For lobby icon embedded/origin flags, preserve existing behavior. Example: Monthly Gratitude sends `[this._isFromEvent]`; BP Custom sends `[]`.

Before editing code, present the action map and stop:

```text
Gate 2: Proposed client tracking map for {feature}

| Category | File / Flow | Action | Params | Reason |
|---|---|---|---|---|
| Main screen open | {Feature}MainGui.showGui() | enter_event | [] | Main GUI is shown |
| Popup shown | {Feature}PopupGui.showGui() | popup_show | [] | Intro popup is shown |

Excluded:
- claim reward: sends feature packet, server can log it
- close popup: close tracking was not requested

OK to implement this action map?
```

Gate 2 reply handling:
- If the user replies `OK`, `confirm`, or clearly approves the whole map unchanged, continue to Step 3.
- If the user says to add, remove, rename, move, or change params for any action, update the table and `Excluded` list, then show Gate 2 again.
- If the requested change names a GUI/flow not yet traced, inspect that GUI/flow first, update the map, then show Gate 2 again.
- Do not implement immediately after a change request, even if the change looks simple. The updated map is the contract.

Only implement after the current Gate 2 map is explicitly confirmed.

## Step 3: Implement

Only start after Gate 1 is satisfied and Gate 2 is confirmed.

Use this exact call shape:

```js
PoolFunction.doFunc(PoolFunction.SYSTEM_LOG_CLIENT,
    gc.GROUP_NAME_LOG.{group_key},
    gc.FEATURE_NAME.{feature_key},
    "{action_name}", {param_array}
);
```

Implementation rules:
- Add missing `gc.GROUP_NAME_LOG` or `gc.FEATURE_NAME` keys in `GroupLogDefine.js` only after user confirmation.
- Place log calls **after the guard** that can return early, so a blocked flow is never logged.
- Place log calls **after the action itself has been called**, not before it. Logging `click_x` above the
  `PoolFunction.doFunc(...)` that performs the action records intent, not the action — and reads backwards.
  These are two separate requirements; satisfying only the guard one is the common slip.
- Put the log at the **end of its block** (right before `break;`, or last statement of the function), with a
  **blank line above it**. Tracking is not feature logic — keeping it in one separated block at the end means
  a reader can tell logic from tracking at a glance, and the next person adding a log has an obvious place.
- Put the log in the **class that owns the behavior**, not in the Module that routes to it. `enter_event` goes
  in `{Feature}MainGui.showGui()`, like `MonthlyGratitudeMainGui` / `BPCustomMainGui` / `RelicHuntMainGui`.
  Only move it up to the Module when the Module holds data the GUI cannot see, or when several entry paths
  share one Module method and the guards live there.
- Do not log close buttons unless the user explicitly requested close tracking.
- Do not use `ClientTracking.trackingLog(...)` directly when the local pattern uses `PoolFunction.SYSTEM_LOG_CLIENT`.
- Keep project JS organization: use `// #region <Name>` / `// #endregion` for new or clearly grouped logic in touched JS files.
- Keep edits scoped to tracking and necessary define keys.

## Step 4: Verify

Agent checks:
- `rg "SYSTEM_LOG_CLIENT" {feature_folder}` shows every selected action exactly once in the intended flow.
- `GroupLogDefine.js` has confirmed group and feature keys, or the skill reused existing keys.
- No action logs were added before early-return guards.
- For `event_action_log` and `stick_enhance_log`, remember `SystemModule.logClient` sends each `(group + feature + action)` only once per session.

Report:

```text
dev-tracking done: {feature}
Group: gc.GROUP_NAME_LOG.{group_key}
Feature: gc.FEATURE_NAME.{feature_key}
Added logs: have_event, enter_event, ...
Files changed: ...
Runtime note: please verify analytics payload on device/server logs.
```

## Common Mistakes

- Implementing before confirming group/feature names.
- Adding a new key even though `GroupLogDefine.js` already has one.
- Logging `have_event` when server says the event ended.
- Copying reference-module actions as mandatory actions for every feature.
- Adding client logs for claim/server-packet actions without a specific client-intent requirement.
- Implementing immediately after the user changes Gate 2 instead of showing the updated map again.
- Adding logs to helper functions that can be called by multiple unrelated flows.
- Forgetting that `event_action_log` is deduped once per session by `SystemModule.logClient`.
- Logging before the action call instead of after it, while believing the "after the guard" rule was satisfied.
- Dropping a log in the middle of a handler instead of at the end of the block, with no blank line around it.
- Pushing a GUI-owned log up into the Module without a reason the GUI actually lacks.
