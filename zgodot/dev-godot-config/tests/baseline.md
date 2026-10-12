# dev-godot-config baseline

This file records fresh-agent RED baselines before the `dev-godot-config` skill exists.

## Evaluation protocol

- Each scenario used a fresh agent context (`fork_turns: "none"`) and an isolated disposable worktree at commit `9ee1fba`.
- Evaluators received only the raw scenario request, their worktree path, and the request to implement and report. They did not receive the design document, plans, task briefs, must-list, or planned skill.
- Evaluators did not edit the main skill-authoring worktree. Their disposable worktrees are removed after this evidence is captured.

## Scored failure categories

| Category | Observed? | Evidence |
| --- | --- | --- |
| Edit legacy positional arrays | No | No evaluator edited a ConfigMgr legacy list. |
| Use nonexistent inherited `get_instance()` | No | Create evaluator explicitly called `BaseJSONConfig.register_instance(...)`. |
| Put config path/registration wrapper in subclass | Yes | Create evaluator put `CONFIG_PATH` and `static func register_config()` in `SampleEventConfig`, then called `register_config()` from `get_instance()`. |
| Group independent loaders in one file | Not exercised | Multi-config evaluator created no code because schema/path details were unspecified. |
| Mark null data loaded | No | Create evaluator described transactional parsing; malformed evaluator retained the existing unloaded/null assertions. |
| Remove getter without confirmation | No direct removal | Update evaluator retained a zero-return compatibility shim, but made the breaking schema/API decision without confirmation. |
| Skip regression callsite audit | Yes | Update evaluator changed the parser and stated the test-local class was the only consumer; it did not run a repository callsite audit. |
| Omit tests | Yes, multi scenario | The multi-config evaluator added neither production files nor independent tests. Other scenarios did add or retain unit tests, but none could run GUT because `godot` was unavailable on `PATH`. |

## Results

### `create_from_json` — RED

- Evaluator: `/root/config_task3_impl/baseline_create`
- Isolated path: `D:\workspace\STM-Godot\client\.worktrees\baseline-config-create`
- Artifact/diff: added `assets/config/json/sample_event/sample_event.json`, `modules/game/features/sample_event/sample_event_config.gd`, and `tests/unit/test_sample_event_config.gd`; modified `modules/game/features/game_feature_registry.gd` and `tests/unit/test_config_mgr.gd`. Tracked diff stat was two files, 11 insertions, 2 deletions; Git listed the new files as untracked.
- Choices: created a typed `SampleEventConfig`, typed `Tier` records, a singleton wrapper, and GUT tests. The class owned `CONFIG_PATH`, `CONFIG_FOLDER`, `CONFIG_FILE_NAME`, and `static func register_config()`. `GameFeatureRegistry.register_all()` called that class wrapper.
- Observed rationale: “the config wrapper also self-registers for direct feature use” and “only for a fresh singleton, allowing explicit test/custom `pre_init` usage to remain intact.”
- Must score: failed `sample_event_json_config.gd` (used `sample_event_config.gd`), failed `Static Init Accessors regions`, and failed `ConfigMgr path registration outside subclass`. It did provide a typed singleton wrapper and authored GUT tests. This is a decisive RED baseline for class boundaries and canonical file/region shape.
- Validation: semantic JSON comparison and `git diff --check` passed. GUT was attempted but `godot` was not on `PATH`.

### `schema_update_removal` — RED

- Evaluator: `/root/config_task3_impl/baseline_update`
- Isolated path: `D:\workspace\STM-Godot\client\.worktrees\baseline-config-update`
- Artifact/diff: modified the two shared config fixtures and `tests/unit/test_base_json_config.gd` (3 files, 24 insertions, 19 deletions).
- Choices: removed `reward` from data, renamed `enabled` to `isEnabled`, changed the parser, and retained `get_reward()` as a compatibility shim returning `0`.
- Observed rationale: “this baseline contains no production `sample_event` config class or feature call sites; its only concrete parser is the test-local `SampleConfig`.”
- Must score: failed to present a schema/API diff, failed to request confirmation before the destructive public-API decision, and skipped a repository callsite audit. The update itself was otherwise limited to the available test-local implementation. This is a decisive RED baseline for the update route.
- Validation: both JSON fixtures parsed with PowerShell and `git diff --check` passed. GUT was attempted but unavailable on `PATH`.

### `malformed_and_defaults` — naturally adequate

- Evaluator: `/root/config_task3_impl/baseline_malformed`
- Isolated path: `D:\workspace\STM-Godot\client\.worktrees\baseline-config-malformed`
- Artifact/diff: modified only `tests/unit/test_base_json_config.gd` (14 insertions).
- Choices: added `tiers: Array = []`, used `data_config.get("tiers", [])`, retained valid tiers, and converted a non-array optional value to `[]`. It reused the existing missing/malformed test, which asserts non-OK, unloaded, and null data.
- Observed rationale: “Existing loader behavior already covers missing/unparseable JSON, so duplicating it was unnecessary.”
- Must score: the available code already covered unloaded malformed data and it added a safe default plus a missing-tiers test. No new instruction is needed solely for this naturally adequate behavior.
- Validation: `git diff --check` passed. GUT executable could not be found.

### `multiple_independent_configs` — RED

- Evaluator: `/root/config_task3_impl/baseline_multi`
- Isolated path: `D:\workspace\STM-Godot\client\.worktrees\baseline-config-multi`
- Artifact/diff: no files changed; `git diff --stat` was empty.
- Choices: the evaluator discovered that separate subclasses would get independent reload markers and proposed two scripts under `modules/game/features/sample_event/config/`, each registered separately in `GameFeatureRegistry`.
- Observed rationale: “The raw request does not specify exact JSON filenames, schema, or consumer API. I avoided inventing production paths/class APIs.”
- Must score: it produced neither the required schema loader(s) nor registrations/tests, so it fails the required output. The conservative reasoning is useful, but a skill needs an explicit route for resolving missing schema/path information, separating distinct schemas, and recognizing a same-schema source family with one bind-once instance per path.
- Validation: read-only discovery and clean Git status only; no GUT run.

## Baseline conclusion

At least three scenarios are RED. The observed gaps to address are: canonical config filename and `Static`/`Init`/`Accessors` grouping; feature bootstrap registration outside config subclasses; create/update routing; visible schema/API diff and confirmation before a destructive getter change; callsite audit; and the one-loader-per-independent-file rule. Do not add extra malformed/default wording beyond the existing adequate pattern unless it is needed to connect the canonical test reference.

## Forward-test outcomes with `dev-godot-config`

Each evaluator was a fresh context and received only `Use dev-godot-config at <main-worktree skill path>`, the raw scenario, and its disposable target worktree. No evaluator received this plan, the must-list, baseline conclusion, or implementation solution. Target worktrees were seeded only with raw JSON input where the scenario required it.

| Scenario | Evaluator / target | Seed setup | Result and evidence |
| --- | --- | --- | --- |
| `schema_update_removal` | `/root/config_task4_impl/config_eval_update` / `eval-config-update` | `assets/config/json/sample_event/sample_event.json` with the original `reward`, `enabled`, `tiers` | Stopped for explicit confirmation before removing `get_reward()`. It reported the schema/API diff, audited that no production loader/callers exist, called the mismatch unexpected drift, and made no edits. |
| `malformed_and_defaults` | `/root/config_task4_impl/config_eval_malformed` / `eval-config-malformed` | `assets/config/json/sample_event/sample_event.json` | Added RED-first cases plus `no_tiers.json`; implemented typed empty-array default, malformed optional value rejection, defensive copy, reset, and preserved missing/malformed unloaded behavior. `git diff --check` passed. GUT was attempted but Godot 4.6.2 crashed with signal 11 before a summary; an outside capture then exposed missing imported class cache/project extension parse errors, so no false pass claim was made. |
| `multiple_independent_configs` | `/root/config_task4_impl/config_eval_multi` / `eval-config-multi` | discoverable `sample_event_info.json` (`enabled`, `title`) and `sample_event_reward.json` (`reward`) | Produced two separate loaders and two separate focused tests; feature bootstrap registered/pre-initialized both full relative paths, with no subclass registration or legacy-list append. `git diff --check` passed. Bounded headless Godot 4.6.2 crashed before GUT output (misleading exit `0`), so runtime pass remains unavailable. |
| `create_from_json` | `/root/config_task4_impl/config_eval_create` / `eval-config-create`, then fresh `/root/config_task4_impl/config_eval_create_rerun` / `eval-config-create-rerun` | `assets/config/json/sample_event/sample_event.json` with `reward`, `enabled`, and `tiers` | First evaluator produced canonical loader/bootstrap/focused tests, discovered whole JSON number `42` is parsed as `float`, and corrected production validation to accept integral `int`/`float` only. This witnessed gap updated the canonical reference. The fresh rerun then generated the same separate `sample_event_json_config.gd`, external `GameFeatureRegistry` registration, and isolated GUT suite; `git diff --check` passed, registration search found the external path, and positional-list/subclass-path searches had no matches. Bounded GUT attempts either crashed before output or timed out after initial cache/import setup, so runtime evidence is recorded as unavailable rather than GREEN by assertion count. |

### Forward-test comparison

- The update evaluator no longer made the unapproved destructive API decision from RED.
- The multi evaluator no longer stopped for missing schema/path detail: discoverable raw JSON led to two independent files, registrations, and tests.
- The create evaluator followed `Static`/`Init`/`Accessors`, dynamic `ConfigMgr` registration outside the subclass, and avoided positional legacy arrays.
- The malformed/default evaluator covered the existing unloaded behavior and typed optional default policy.
- A real Godot JSON parser result revealed that strict `TYPE_INT` rejects whole-number JSON literals. The smallest owning reference now permits only integral `int`/`float`, still rejecting fractional values and strings.
