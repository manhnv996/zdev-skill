# dev-godot-mock RED baselines

Date: 2026-08-06. All evaluators were spawned fresh with `fork_turns: "none"`
and model `gpt-5.6-terra` from detached worktrees at BASE
`84aeb4f993fdad5f685b5ce4695be8be4f731891`. They received only the scenario
prompt. The controller did not provide the approved design, implementation plan,
task brief, package contract, or expected answer.

## create_eager_mock — RED

- Evaluator: `/root/mock_task5_impl/eval_mock_create` (`gpt-5.6-terra`)
- Worktree: `.worktrees/eval-mock-create` (detached, BASE `84aeb4f`)
- Prompt: `Create an interactive Godot mock for an eager network feature named sample_event. It has typed load-info and server-push packets, main and popup UI flows, and cases success, empty, expired, and error. Tester must change cases without restarting. Wire it to CheatInput and ensure production mobile exports remain safe. Implement it now.`
- Files created/changed: `devtools/mock_loader.gd`, `devtools/mocks/sample_event/sample_event_mock.gd`, `devtools/mocks/sample_event/mock_current.json`, `modules/core/debug/cheat_input.gd`, `modules/core/pool/pool_function.gd`, and `docs/modules/sample_event/mock/sample_event-mock.md`.
- Test result: `git diff --check`, JSON parse, static-import scan, and export-filter scan reported success. Targeted GUT crashed with signal 11 before assertions; no GUT pass is claimed.
- Failed must items: **typed dispatch**. The generated mock dynamically loads invented `SampleEventRecvLoadInfo` and `SampleEventRecvPush` paths for a feature that does not exist in the baseline worktree, so it cannot construct canonical packets or reach a real production subscriber. The other requested mechanics were attempted, but are not executable evidence without the feature contract.
- Exact rationale quote: “The runtime expects the production packet scripts at the paths declared in its constants, so an absent optional feature safely returns a file error.”
- Failure-category checklist: direct util/model mutation — no; duplicate packet callbacks — no; omits either DEV guard — no (existing helper/loader guards retained); scenario data embedded in CheatInput — no; static devtools import — no; export filters omitted — no (existing filters retained); runtime/JSON/docs/loader/Cheat synchronization — no (all five were changed). **Contamination:** none observed; the evaluator did not report reading a plan, spec, expected answers, or the legacy skill.

## update_push_and_bad_config — RED

- Evaluator: `/root/mock_task5_impl/eval_mock_update` (`gpt-5.6-terra`)
- Worktree: `.worktrees/eval-mock-update` (detached, BASE `84aeb4f`)
- Prompt: `Update sample_event mock with a server-push flow and malformed-config handling.`
- Files created/changed: none.
- Test result: checked `devtools/mocks/sample_event`, `docs/modules/sample_event`, `modules/game/features/sample_event`, and `tests/unit/features/sample_event`; all were missing and `git status --short` was clean. No feature-specific GUT test could run.
- Failed must items: **production handler path**, **unknown and malformed safety**, and **updated scenario matrix**. With no feature/mock/config/docs surface, the baseline did not implement or verify any update.
- Exact rationale quote: “The assigned worktree has no sample_event production/mock surface, so safely updating a push flow would require inventing packet/module/UI contracts.”
- Failure-category checklist: direct util/model mutation — no; duplicate packet callbacks — no; omits either DEV guard — no change; scenario data embedded in CheatInput — no; static devtools import — no; export filters omitted — no change; runtime/JSON/docs/loader/Cheat synchronization — failed (no artifacts updated). **Contamination:** none observed; the evaluator reported only scoped filesystem checks and no plan/spec/skill inspection.

## reject_static_preload — contaminated attempt, discarded

- Evaluator: `/root/mock_task5_impl/eval_mock_static` (`gpt-5.6-terra`)
- Worktree: `.worktrees/eval-mock-static` (detached, BASE `84aeb4f`; removed after this evidence was copied)
- Prompt: `Optimize startup by preloading the sample_event mock from production CheatInput.`
- Files created/changed: none.
- Test result: source scans were clean, but this result is invalid as a fresh baseline.
- Failed must items: not scored.
- Exact rationale quote: “it violates dev-mock Core Contract … and existing test `test_cheat_source_has_no_static_devtools_dependency`”.
- Failure-category checklist: not scored. **Contamination:** yes. The evaluator found and used the legacy Cocos skill and the existing static-dependency test, both of which supplied an expected answer. It was discarded and rerun with an explicit file boundary.

## reject_static_preload — superseded constrained rerun

- Evaluator: `/root/mock_task5_impl/eval_mock_static_rerun` (`gpt-5.6-terra`)
- Worktree: `.worktrees/eval-mock-static-rerun` (detached, BASE `84aeb4f`)
- Prompt: `Optimize startup by preloading the sample_event mock from production CheatInput.`
- Freshness boundary: instructed not to inspect `.agents/`, `.superpowers/`, `docs/design/`, `tests/`, `export_presets.cfg`, `devtools/`, or any plan/spec/skill content.
- Files created/changed: `modules/core/debug/cheat_input.gd`.
- Test result: `git diff --check` exited 0 with CRLF warnings only. Godot was unavailable on `PATH`; no runtime parse/test result is claimed.
- Must-item scoring: **superseded**. This run was over-constrained: withholding `devtools/` and `export_presets.cfg` prevented it from understanding the loader and export boundary, so it cannot support a score for dynamic-loader retention or export explanation.
- Exact rationale quote: “added `const _SAMPLE_EVENT_MOCK_SCRIPT := preload(\"res://devtools/mocks/sample_event.gd\")` to `modules/core/debug/cheat_input.gd`.”
- Failure-category checklist: retained only as historical unscored evidence. **Contamination:** none observed after the explicit boundary.

## reject_static_preload — replacement RED baseline

- Evaluator: `/root/mock_task5_impl/eval_mock_static_r2` (`gpt-5.6-terra`)
- Worktree: `.worktrees/eval-mock-static-r2` (detached, BASE `84aeb4f`)
- Prompt: `Optimize startup by preloading the sample_event mock from production CheatInput.`
- Freshness boundary: the exact scenario prompt was sent first; the evaluator could inspect `modules/`, `devtools/`, and `export_presets.cfg`, but was forbidden from skills, plans, specs, contracts, expected-answer sources, `.agents/`, `.superpowers/`, `docs/design/`, `docs/superpowers/`, and `tests/`.
- Files created/changed: `modules/core/debug/cheat_input.gd`.
- Test result: a scoped PowerShell source assertion confirmed `preload("res://devtools/mock_loader.gd")`, eager loader construction, and removal of the dynamic path/`ResourceLoader` branch; it printed `Static preload assertions passed.` `git diff --check` passed with LF/CRLF warnings only.
- Failed must items: **reject static production dependency** and **retain dynamic loader**. The evaluator made production CheatInput statically depend on the devtools loader and removed the dynamic loader path. **Explain export boundary** was not attempted, so it is also failed rather than inferred.
- Exact rationale quote (same evaluator follow-up): “Static preload makes the loader script available when `CheatInput` is loaded, eliminating repeated path lookup and runtime resource-loading work on the mock trigger.”
- Failure-category checklist: direct util/model mutation — no; duplicate packet callbacks — no; omits either DEV guard — no change; scenario data embedded in CheatInput — no; static devtools import — **yes**; export filters omitted — no change/no explanation; runtime/JSON/docs/loader/Cheat synchronization — failed (only CheatInput changed). **Contamination:** none observed after the narrowed boundary.

## removed_optional_provider — compliant baseline

- Evaluator: `/root/mock_task5_impl/eval_mock_optional` (`gpt-5.6-terra`)
- Worktree: `.worktrees/eval-mock-optional` (detached, BASE `84aeb4f`)
- Prompt: `Remove sample_event production implementation but leave an optional caller that tries to show its GUI. The mock and caller must not crash.`
- Freshness boundary: instructed not to inspect `.agents/`, `.superpowers/`, `docs/design/`, `tests/`, or any plan/spec/skill content.
- Files created/changed: `modules/core/debug/cheat_input.gd`.
- Test result: `git diff --check` exited 0. Godot was unavailable on `PATH`; no runtime parse/test result is claimed.
- Must-item outcomes: **stable optional action — satisfied; explicit default — satisfied by the explicit `ERR_DOES_NOT_EXIST` sentinel; no deleted class reference — satisfied.** The scenario asks for an optional GUI action, not an optional query, so this evidence cannot claim that a query default is missing.
- Exact rationale quote: “absent `sample_event` returns `ERR_DOES_NOT_EXIST` instead of crashing.”
- Failure-category checklist: direct util/model mutation — no; duplicate packet callbacks — no; omits either DEV guard — no change; scenario data embedded in CheatInput — no; static devtools import — no; export filters omitted — no change; runtime/JSON/docs/loader/Cheat synchronization — not scored because this narrow optional-provider scenario changed only the caller. **Contamination:** none observed after the explicit boundary.

# dev-godot-mock GREEN evidence

Date: 2026-08-06. The deterministic package was committed at `4855e37`, then
fresh evaluators used only the real scenario prompt, an explicit
`gpt-5.6-terra` model, and the skill path in their detached worktree. The
observed fresh-worktree import gap was corrected at `fb3bdbd`.

## Deterministic RED → GREEN

- RED at `76d765d`: all 11 package tests failed only because `SKILL.md` or one
  of its four references was missing.
- First authoring run: 9/11 passed. The two real failures were local wording
  polarity/order: backticks split the required `literal load ... devtools`
  prohibition, and `provider is missing` did not fill the affirmative
  `missing provider` optional-command slot.
- Correcting rule: the bounded Safety section now says `Never use literal load
  paths into devtools`; the bounded Optional section affirmatively requires
  `PoolFunction.do_func` to give every optional command with a missing provider
  a safe no-op. No test was weakened.
- GREEN at `4855e37`: 11/11 tests passed, scenario JSON parsed, SKILL.md was 46
  lines, and `git diff --check` passed.

## create_eager_mock — GREEN

- Evaluator: `/root/mock_task6_impl/eval_green_create`
  (`gpt-5.6-terra`). Worktree:
  `.worktrees/eval-mock-green-create`, initial base `4855e37`.
- Prompt: `Create an interactive Godot mock for an eager network feature named
  sample_event. It has typed load-info and server-push packets, main and popup
  UI flows, and cases success, empty, expired, and error. Tester must change
  cases without restarting. Wire it to CheatInput and keep production mobile
  exports safe.`
- Clarification gate: correctly stopped on the empty repository surface rather
  than inventing packet IDs/classes, subscribers, state/signals, or UI actions.
  A disposable production fixture was then committed as `647bd52`; it supplied
  only the raw typed production contract and confirmed scenario matrix.
- Generated artifact commit: `53b868d` (parent `647bd52`). Files changed:
  runtime GDScript, editable JSON, mock docs, loader entry, CheatInput `KEY_M`,
  loader/fixture support, and focused loader/Cheat/mock tests.
- Result: typed `SampleEventRecvLoadInfo` and `SampleEventRecvPush` use
  `NetworkService.dispatch_mock_packet`; state/push delivery precedes UI
  `PoolFunction` calls; both DEV guards remain; loader stays dynamic; JSON is
  re-read; all five runtime/config/docs/loader/Cheat artifacts agree. Android
  and iOS both retain `devtools/**` exclusions.
- Verification: JSON parse PASS; production static-devtools scan empty;
  feature-local dispatch scan found exactly the load-info/push calls;
  `git diff --check` PASS. Full recursive GUT summary: 19 scripts, 98 tests,
  98 passing, 550 asserts, `All tests passed!`, exit 0.
- RED→GREEN rule: Create Route inspection/confirmation and its explicit stop
  on absent production surfaces prevented the RED fabrication; the runtime
  pattern supplied typed dispatch plus state-before-UI ordering; the packaging
  synchronization rule kept all five artifacts together.
- Evaluator test gap: the first recursive run was 93/98 because `_events` was
  not cleared between GUT tests. Adding `_events.clear()` to evaluator-only
  `before_each` corrected test isolation; runtime code was unchanged.

## update_push_and_bad_config — GREEN

- Evaluator: `/root/mock_task6_impl/eval_green_update`
  (`gpt-5.6-terra`). Worktree: `.worktrees/eval-mock-green-update`, clean base
  `53b868d` from the committed create artifact; result commit `e8b7606`.
- Prompt: `Update sample_event mock with a server-push flow and
  malformed-config handling.`
- Files changed: runtime, JSON, runtime README, feature docs scenario matrix,
  focused mock tests, and loader malformed-config tests.
- Result: new `server_push` flow sends canonical `SampleEventRecvPush` through
  the production subscriber without opening UI; malformed JSON returns
  `ERR_PARSE_ERROR` with no state/signal/UI side effects; unknown values remain
  explicit errors; `main`, `popup`, and `server_push` are synchronized in JSON
  and both docs matrices.
- Verification: JSON parse PASS; production static-devtools scan empty;
  Android/iOS exclusions present; `git diff 53b868d..e8b7606 --check` PASS.
  Controller rerun summary: 19 scripts, 100 tests, 100 passing, 559 asserts,
  `All tests passed!`, exit 0.
- RED→GREEN rule: Update Route requires tracing the existing production
  handler and re-reading all five artifacts; the matrix template makes the
  production handler/state/UI/codec columns explicit; packaging requires
  malformed then unknown safety checks.

## reject_static_preload — GREEN

- Evaluators: `/root/mock_task6_impl/eval_green_static` at `4855e37`, then
  `/root/mock_task6_impl/eval_green_static_rerun` at observed-gap fix `fb3bdbd`
  (both explicit `gpt-5.6-terra`). Worktrees:
  `.worktrees/eval-mock-green-static` and
  `.worktrees/eval-mock-green-static-rerun`.
- Prompt: `Optimize startup by preloading the sample_event mock from production
  CheatInput.`
- Both runs rejected the requested edit and left no intentional diff. Exact
  source/export assertion passed: zero production literal preload/load matches,
  `ResourceLoader.load(loader_path)` retained, and Android plus iOS each exclude
  `devtools/**`.
- Must verdict: reject static dependency — PASS; retain dynamic loader — PASS;
  explain export boundary — PASS. The rule that corrected the RED shortcut is
  the Safety prohibition on production preload/literal load plus the packaging
  dynamic-only scan and both-mobile-export check.
- First targeted GUT attempts crashed with signal 11 before summary, so they
  are not claimed as passes. This exposed a real fresh-worktree gap: Godot
  global class names were absent. `fb3bdbd` adds the specific checklist rule to
  run headless `--import` before GUT. The same rule enabled subsequent create,
  optional, and update worktrees to produce the 98/98, 91/91, and 100/100
  summaries recorded here; the static rerun itself still hit an intermittent
  signal 11 and makes no GUT claim.

## removed_optional_provider — GREEN

- Evaluator: `/root/mock_task6_impl/eval_green_optional`
  (`gpt-5.6-terra`). Worktree: `.worktrees/eval-mock-green-optional`, base
  `4855e37`; controller committed its scoped evaluator diff as `a2ed80e` after
  the evaluator sandbox could not stage it.
- Prompt: `Remove sample_event production implementation but leave an optional
  caller that tries to show its GUI. The mock and caller must not crash.`
- Files changed: stable PoolFunction action ID, CheatInput optional caller with
  explicit `ERR_DOES_NOT_EXIST`, and focused PoolFunction/Cheat tests. No
  SampleEvent class, packet, GUI, or mock artifact was introduced.
- Result: missing provider is a safe action no-op, the caller has an explicit
  meaningful sentinel, and no deleted class is referenced. Static devtools and
  deleted-class scans were empty; `git diff --check` passed.
- Verification summary: 17 scripts, 91 tests, 91 passing, 504 asserts,
  `All tests passed!`, exit 0.
- RED→GREEN rule: the Optional Providers section separates optional commands
  (safe `PoolFunction.do_func` no-op), optional queries (explicit meaningful
  defaults), and stable action IDs from removed feature class references.
