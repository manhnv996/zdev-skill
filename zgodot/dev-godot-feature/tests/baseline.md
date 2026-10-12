# dev-godot-feature RED Baseline

Each scenario ran without `dev-godot-feature` in a fresh detached worktree.
The approved design and all four implementation plans were removed from every
seed, and evaluators received only the scenario prompt, never the `must` list.
Evaluation base: `86028078717287b80e32f7ec7e3e0eccaf48243e`.

## eager_request_response

- Result: PASS
- Violated must item: none
- Must scores: 5/5 — eager activation PASS; feature-local typed subscription PASS;
  public send method PASS; module signal PASS; canonical tree PASS.
- Evidence: "I chose an eager module lifecycle so it subscribes before login
  completes, guaranteeing the load-info request is issued immediately when login
  succeeds."
- Concrete decision: registry registration/open, typed subscription,
  `request_load_info()`, module signals, and the canonical feature tree are in
  evaluator commit `6383baf`.
- Skill requirement derived: none.
- Provenance:
  - Evaluator: `/root/feature_task1_impl/eval_eager_request_response`
  - Model and reasoning: `gpt-5.6-terra` / `high`
  - Evaluation base: `86028078717287b80e32f7ec7e3e0eccaf48243e`
  - Seed: `0adbd4d`; head: `6383baf`; worktree status: clean.
  - Verification result: static checks and `git diff --check` passed; Godot was
    unavailable on `PATH`.
  - Cleanup result: normally unregistered; physical
    `.worktrees/eval-feature-eager` residue remained after Windows returned
    `Invalid argument`; no force cleanup attempted.

### GREEN

- Result: PASS
- Must scores: 5/5 — eager activation PASS; feature-local typed subscription
  PASS; public send method PASS; module signal PASS; canonical tree PASS.
- Evidence: "The registry eagerly opens the module at bootstrap so it can own
  its typed response subscription; the module waits for
  `LoginService.login_succeeded` before showing its config-gated popup and
  sending the load-info request."
- Concrete decision: evaluator commit `ab63b592` opens `SampleEventModule` from
  the registry, keeps typed packet ownership and public request/signals in the
  module, and uses the canonical feature/config/UI/test tree.
- Provenance:
  - Evaluator: fresh blind Task 4 `eager_request_response` evaluator; its
    canonical collaboration child name was not retained by the partial handoff.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Seed: `0adbd4d`; draft: `4de27c065c1f0c6027635c5b5bc6d2790cacc947`;
    evaluation base: `35a7fb6`; head: `ab63b592`; intentional status clean.
- Verification:
  - `validate_feature.py --feature-id sample_event --spec
    docs/modules/sample_event/spec/sample_event-spec.md`: exit 0.
  - `& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit/features/sample_event -gexit -gconfig=`:
    signal 11 before GUT output; process exit 0; not a suite pass.
  - `git diff --check 35a7fb6..ab63b592`: exit 0.
- Cleanup: normal removal unregistered the worktree; physical
  `.worktrees/task4-eager_request_response` remains after Windows returned
  `Invalid argument`; no force removal.

## server_push_vs_lazy

- Result: FAIL
- Violated must item: reject or repair lazy activation; eager open before login traffic
- Must scores: 1/3 — reject or repair lazy activation FAIL; one packet owner PASS;
  eager open before login traffic FAIL.
- Evidence: "SamplePushService activates its subscription at bootstrap, owns the
  packet and snapshot for the logged-in session, and leaves SamplePushModule lazy
  for UI access."
- Concrete decision: evaluator commit `c2071ad` creates one eager autoload packet
  owner, but the registry only registers `sample_push`; its test explicitly
  asserts that `SamplePushModule` remains closed. Moving packet ownership to the
  autoload neither rejects nor repairs the feature's lazy activation.
- Skill requirement derived: a feature that owns unsolicited server push must
  open its owning feature module before login traffic; do not preserve a lazy
  module by moving packet ownership into a feature-specific autoload service.
- Provenance:
  - Evaluator: `/root/eval_server_push_lazy`
  - Model and reasoning: `gpt-5.6-terra` / `high`
  - Evaluation base: `86028078717287b80e32f7ec7e3e0eccaf48243e`
  - Seed: `406dfa9`; head: `c2071ad`; worktree status: clean.
  - Verification result: Godot crashed with signal 11 before GUT (baseline smoke
    also crashed); committed-artifact/static inspection and `git diff --check`
    passed.
  - Cleanup result: normally unregistered; physical
    `.worktrees/eval-feature-push` residue remained after Windows returned
    `Invalid argument`; no force cleanup attempted.

### GREEN

- Result: PASS
- Must scores: 3/3 — reject or repair lazy activation PASS; one packet owner
  PASS; eager open before login traffic PASS.
- Evidence: "`sample_push` cannot be lazy at the module boundary because it owns
  a server push that may arrive immediately after login. Register it during
  bootstrap and open it synchronously from the login-success callback; keep any
  future UI lazy and render it from the module's semantic state and signals."
- Concrete decision: evaluator commit `6e7b7afe` changes the approved activation
  contract to eager, opens the sole subscribing module before authenticated push
  traffic, and leaves presentation as the only future lazy surface.
- Provenance:
  - Evaluator: fresh blind Task 4 `server_push_vs_lazy` evaluator; its canonical
    collaboration child name was not retained by the partial handoff.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Seed: `406dfa9`; draft: `4de27c065c1f0c6027635c5b5bc6d2790cacc947`;
    evaluation base: `1e279245`; head: `6e7b7afe`; intentional work committed.
- Verification:
  - `validate_feature.py --feature-id sample_push --spec
    docs/modules/sample_push/spec/sample_push-spec.md`: exit 0.
  - `& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit/features/sample_push -gexit -gconfig=`:
    signal 11 before GUT output; not a suite pass. The evaluator separately
    reported 3/3 tests and 9 assertions from an elevated targeted run.
  - `git diff --check 1e279245..6e7b7afe`: exit 0.
- Cleanup/status: worktree remains registered at
  `.worktrees/task4-server_push_vs_lazy`; its only residue is the ACL-locked
  untracked `test_sample_push_module.gd.uid`. No generated residue was committed
  and no force removal occurred.

## lazy_ui_only

### SUPERSEDED — pre-unified BaseScreen contract

- Result: PASS
- Violated must item: none
- Must scores: 3/3 — lazy factory only PASS; GuiService and GuiBase PASS; no
  NetworkService subscription PASS.
- Evidence: "Activation uses a lazy `sample_help` factory; an owning UI opens it
  then calls `show_help()`, which loads one `GuiBase` popup through `GuiService`,
  with no feature service or `NetworkService` subscription."
- Concrete decision: evaluator commit `0f232b6` registers without opening the
  feature, uses a `GuiBase` popup routed through `GuiService`, and contains no
  feature-local network call.
- Skill requirement derived: none.
- Provenance:
  - Evaluator: `/root/eval_lazy_ui_only`
  - Model and reasoning: `gpt-5.6-terra` / `high`
  - Evaluation base: `86028078717287b80e32f7ec7e3e0eccaf48243e`
  - Seed: `76e621b`; head: `0f232b6`; worktree status: clean.
  - Verification result: Godot crashed with signal 11 before GUT;
    committed-artifact/static inspection and `git diff --check` passed.
  - Cleanup result: normally unregistered; physical
    `.worktrees/eval-feature-lazy-ui` residue remained after Windows returned
    `Invalid argument`; no force cleanup attempted.

### SUPERSEDED — pre-unified BaseScreen contract

- Result: PASS
- Must scores: 3/3 — lazy factory only PASS; GuiService and GuiBase PASS; no
  NetworkService subscription PASS.
- Evidence: "`sample_help` is a lazy, local-only module: it owns presentation
  entry and a single modal popup, while intentionally owning no network,
  configuration, or persisted state contract."
- Concrete decision: evaluator commit `5d044efc` registers only a factory, opens
  the `GuiBase` popup through `GuiService`, and contains no packet subscription or
  send path.
- Provenance:
  - Evaluator: fresh blind Task 4 `lazy_ui_only` evaluator; its canonical
    collaboration child name was not retained by the partial handoff.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Seed: `76e621b`; draft: `4de27c065c1f0c6027635c5b5bc6d2790cacc947`;
    evaluation base: `94128c4`; head: `5d044efc`; status clean before cleanup.
- Verification:
  - `validate_feature.py --feature-id sample_help --spec
    docs/modules/sample_help/spec/sample_help-spec.md`: exit 0.
  - `& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit/features/sample_help -gexit -gconfig=`:
    signal 11 before GUT output; not a suite pass.
  - `git diff --check 94128c4..5d044efc`: exit 0.
- Cleanup: normal removal unregistered the worktree; physical
  `.worktrees/task4-lazy_ui_only` remains after Windows returned
  `Invalid argument`; no force removal.

### RED — fresh blind run 1 (validator gate failed)

- Result: FAIL
- Violated must item: canonical validator completion gate; the four hidden
  architecture items passed, but the feature package was incomplete.
- Must scores: 4/4 — lazy factory only PASS; every feature UI directly extends
  `BaseScreen` PASS; subclass-owned presentation and manual fog PASS; no
  `NetworkService` subscription, send, packet class, or receive handler PASS.
- Evidence: "`SampleHelpPopup` directly `extends BaseScreen`, owns
  `GuiService.show(...)`/`GuiService.hide(...)` plus explicit
  `show_disable(60.0)`/`hide_disable()`, while `GameFeatureRegistry` registers
  only `ModuleMgr.register_factory(...)` and the feature contains no packet or
  `NetworkService` path."
- Concrete decision: evaluator commit `6d025f5` keeps `sample_help` dormant until
  its module is opened, then lazily loads one popup whose subclass owns both
  presentation and manual fog; `BaseScreen` is unchanged.
- Provenance:
  - Evaluator: `/root/ubs_task4_eval_controller/eval_unified_base_screen_lazy_ui`.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Exact isolated prompt: `Implement sample_help as a lazy UI-only feature with
    no network commands and one help popup.`
  - Evaluation base: `d41564cdddc809bad86fda64963bfad0260d85a1`;
    seed: `bc8ee38d89b56385cb05cd27f82b319c1a1ec2bc`;
    head: `6d025f5c8becc59bd7070e49377193f015a2c7c3`.
- Verification:
  - Brief command `validate_feature.py --feature-id sample_help --spec
    docs/modules/sample_help/spec/sample_help-spec.md`: exit 2 because the CLI
    requires `--project-root`.
  - Canonical package command with `--project-root .`: exit 1 with
    `missing_util`, `missing_registration`, and `missing_tests`.
  - `& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit/features/sample_help -gexit -gconfig=`:
    no test/assertion summary after GUT class-import and project parse errors;
    unlike historical signal 11 runs, this is not a suite pass.
  - `git diff --check bc8ee38..6d025f5`: exit 0.
- Cleanup: normal non-force removal refused exit 128 because Godot had modified
  tracked `.import` files, removed the hot-reload spine DLL, and created
  untracked `.uid` files. The worktree remains registered; no reset, clean,
  force removal, or generated-file edit was attempted.

### GREEN

- Result: PASS
- Violated must item: none.
- Must scores: 4/4 — lazy factory only PASS; every feature UI directly extends
  `BaseScreen` PASS; subclass-owned presentation and manual fog PASS; no
  `NetworkService` subscription, send, packet class, or receive handler PASS.
- Evidence: "`GameFeatureRegistry` registers
  `SampleHelpModule.MODULE_ID, SampleHelpModule` without opening it;
  `SampleHelpPopup` directly `extends BaseScreen` and owns `GuiService.show` /
  `GuiService.hide` plus `show_disable` / `hide_disable`; the feature has no
  network or packet path."
- Concrete decision: evaluator commit `d6f8089` implements a canonical lazy
  module and one unique popup, keeps activation dormant until an external caller
  opens the module, and leaves all presentation/fog ownership in the subclass.
- Provenance:
  - Evaluator:
    `/root/ubs_task4_eval_controller/eval_unified_base_screen_lazy_ui_rerun`.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Exact isolated prompt: `Implement sample_help as a lazy UI-only feature with
    no network commands and one help popup.`
  - Corrected evaluation base: `5971226d17ed33f5eb170d435ffa44db6be70660`;
    seed: `f5a01798f904bdd5319a3e60d8702669ddabc244`;
    head: `d6f808908733e5e3304d2dbfd209d4dae4331dc1`.
- Verification:
  - `python .agents/skills/dev-godot-feature/scripts/validate_feature.py --project-root . --feature-id sample_help --spec docs/modules/sample_help/spec/sample_help-spec.md`:
    exit 0 with no findings.
  - `& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit/features/sample_help -gexit -gconfig=`:
    no test/assertion summary because GUT class imports and project-wide core
    types failed during startup. No signal 11 text was emitted; this is not a suite pass,
    and no sample-specific error was reported.
  - `git diff --check f5a0179..d6f8089`: exit 0.
- Cleanup: normal removal unregistered the worktree; physical
  `.worktrees/eval-unified-base-screen-lazy-ui-rerun` remains after Windows
  returned `Invalid argument`; no force removal.

## optional_command_query

- Result: FAIL
- Violated must item: PoolFunction stable keys; namespaced StringName values;
  explicit query default
- Must scores: 1/4 — PoolFunction stable keys FAIL; namespaced StringName values FAIL;
  explicit query default FAIL; no A class import in B PASS.
- Evidence: "B gọi `GameFeatureRegistry.call_optional` cho `show` và
  `query_balance`; khi A không còn installed, cả hai trả fallback mà không khởi
  tạo lại A."
- Concrete decision: evaluator commit `1975725` introduces generic reflective
  `GameFeatureRegistry.call_optional()`. B calls `FEATURE_A_ID` plus `&"show"` or
  `&"query_balance"`, uses no `PoolFunction`, and omits an explicit default from
  its balance query. B does not import A.
- Skill requirement derived: optional cross-feature commands and queries use
  shared, namespaced `StringName` PoolFunction keys; every optional query call
  supplies its fallback explicitly.
- Provenance:
  - Evaluator: `/root/eval_optional_command_query`
  - Model and reasoning: `gpt-5.6-terra` / `high`
  - Evaluation base: `86028078717287b80e32f7ec7e3e0eccaf48243e`
  - Seed: `693e9fa`; head: `1975725`; worktree status: clean.
  - Verification result: Godot tests passed 3/3 (16 assertions) and ModuleMgr
    tests passed 8/8; `git diff --check` passed.
  - Cleanup result: normally unregistered; physical
    `.worktrees/eval-feature-optional-query` residue remained after Windows
    returned `Invalid argument`; no force cleanup attempted.

### GREEN

- Result: PASS
- Must scores: 4/4 — PoolFunction stable keys PASS; namespaced StringName values
  PASS; explicit query default PASS; no A class import in B PASS.
- Evidence: "Feature A is an optional provider. Feature B depends only on the
  neutral `FeatureAOptionalBoundary` and invokes namespaced `PoolFunction`
  actions with explicit defaults; Feature A owns and removes its registrations
  during its lifecycle."
- Concrete decision: evaluator commit `b3b23790` retains the neutral boundary's
  namespaced keys/defaults and makes Feature B call only `PoolFunction.do_func`
  without importing the provider class.
- Provenance:
  - Evaluator: fresh blind Task 4 `optional_command_query` evaluator; its
    canonical collaboration child name was not retained by the partial handoff.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Seed: `693e9fa`; draft: `4de27c065c1f0c6027635c5b5bc6d2790cacc947`;
    evaluation base: `615fdf4`; head: `b3b23790`; status clean before cleanup.
- Verification:
  - Validator commands for `feature_a` and `feature_b` with their scoped specs:
    both exit 0.
  - `& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit/features -gexit -gconfig=`:
    signal 11 before GUT output; not a suite pass.
  - `git diff --check 615fdf4..b3b23790`: exit 0.
- Cleanup: normal removal unregistered the worktree; physical
  `.worktrees/task4-optional_command_query` remains after Windows returned
  `Invalid argument`; no force removal.

## optional_provider_removed

- Result: FAIL
- Violated must item: retain shared action constants; remove provider
  registration only
- Must scores: 1/3 — retain shared action constants FAIL; missing call no-op/default
  PASS; remove provider registration only FAIL.
- Evidence: "Feature A implementation and registry entry are absent; Feature B
  keeps dynamic optional calls, returning false for show and the supplied
  fallback for balance when no provider exists."
- Concrete decision: evaluator commit `d87e0c0` inlines `&"show"` and
  `&"get_balance"` in B instead of retaining a shared action contract. Its test
  constructs a local provider; the diff never starts with and removes an actual
  A implementation/registry entry, so it does not prove the removal-only
  regression.
- Skill requirement derived: optional action constants live outside the
  removable provider, and the provider-removal regression removes only provider
  implementation/registration while existing consumers continue to compile and
  return no-op/default results.
- Provenance:
  - Evaluator: `/root/eval_optional_provider_removed`
  - Model and reasoning: `gpt-5.6-terra` / `high`
  - Evaluation base: `86028078717287b80e32f7ec7e3e0eccaf48243e`
  - Seed: `bd97ebd`; head: `d87e0c0`; worktree status: clean.
  - Verification result: Godot crashed with signal 11 before GUT;
    committed-artifact/static inspection and `git diff --check` passed.
  - Cleanup result: normal `git worktree remove` exited 0; `registered=False`;
    `physical_exists=False`; no force removal used.

### GREEN

- Result: PASS
- Must scores: 3/3 — retain shared action constants PASS; missing call
  no-op/default PASS; remove provider registration only PASS.
- Evidence: "Feature A is removed as an implementation and from the composition
  root. Its two public optional action IDs and defaults remain in the neutral
  `FeatureAOptionalBoundary` contract, so Feature B stays parseable and its
  missing-provider behavior is a no-op show (`false`) and an empty balance (`0`)."
- Concrete decision: evaluator commit `be084d96` removes the provider and its
  registry entry, retains only the neutral keys/defaults, and proves Feature B's
  false/0 behavior with no Feature A implementation.
- Provenance:
  - Evaluator: `/root/plan04_task4_green/eval_provider_removed_green`.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Seed: `bd97ebd`; draft: `4de27c065c1f0c6027635c5b5bc6d2790cacc947`;
    evaluation base: `7092f57c`; head: `be084d96`; intentional work committed.
- Verification:
  - `validate_feature.py --feature-id feature_b --spec
    docs/modules/feature_b/spec/feature_b-spec.md`: exit 0.
  - `& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit/features/feature_b -gexit -gconfig=`:
    signal 11 before GUT output; not a suite pass.
  - `git diff --check 7092f57c..be084d96`: exit 0.
- Cleanup/status: worktree remains registered at
  `.worktrees/task4-optional_provider_removed`; current residue is 305
  Godot-generated tracked `*.import` changes plus deletion of
  `addons/spine/bin/windows/~libspine_godot.windows.editor.x86_64.dll`. No
  residue is in the evaluator commit; exact recovery was policy-rejected, and no
  broad reset/clean or force removal occurred.

## supporting_skill_handoff

- Result: PASS
- Violated must item: none
- Must scores: 3/3 — delegate config workflow PASS; delegate mock workflow PASS; do
  not duplicate supporting skill details PASS.
- Evidence: "Tôi đã dùng trực tiếp dev-godot-config và dev-godot-mock; không
  delegate, và nhúng workflow của chúng vào implementation sample_event."
- Concrete decision: direct use of each required sub-skill is the handoff
  contract; a separate subagent is not required. Evaluator commit `2971392`
  produces the canonical typed config and packet-driven mock artifacts and adds
  only the mock scenario README, not a duplicate feature-level process guide.
- Skill requirement derived: none.
- Provenance:
  - Evaluator: `/root/eval_supporting_skill_handoff`
  - Model and reasoning: `gpt-5.6-terra` / `high`
  - Evaluation base: `86028078717287b80e32f7ec7e3e0eccaf48243e`
  - Seed: `20386ff`; head: `2971392`; worktree status: clean.
  - Verification result: Godot crashed with signal 11 before GUT; JSON/static
    checks and `git diff --check` passed.
  - Cleanup result: normally unregistered; physical
    `.worktrees/eval-feature-handoff` residue remained after Windows returned
    `Invalid argument`; no force cleanup attempted.

### GREEN

- Result: PASS
- Must scores: 3/3 — delegate config workflow PASS; delegate mock workflow PASS;
  do not duplicate supporting skill details PASS.
- Evidence: "SampleEventModule is the sole owner of command 7101 and translates
  typed network packets into semantic signals; the dev-only mock constructs that
  same receive packet and calls `NetworkService.dispatch_mock_packet()`, so
  success and error exercises follow the production handler path without a
  production dependency on `devtools`."
- Concrete decision: evaluator commit `deb024b` directly used the
  `dev-godot-config` and `dev-godot-mock` skills, produced their canonical typed
  config and five synchronized mock artifacts, and added only a feature-specific
  contract/scenario matrix rather than duplicating either workflow guide.
- Provenance:
  - Evaluator: `/root/eval_green_supporting_handoff`.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Seed: `20386ff`; draft: `4de27c065c1f0c6027635c5b5bc6d2790cacc947`;
    evaluation base: `d4199da`; head: `deb024b`; initial/final status clean.
- Verification:
  - `validate_feature.py --feature-id sample_event --spec
    docs/modules/sample_event/spec/sample_event-spec.md`: exit 0.
  - `& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit/features/sample_event -gexit -gconfig=`:
    process exit 0 but signal 11 before GUT output; not a suite pass.
  - `git diff --check d4199da..deb024b` and JSON/static scans: exit 0.
- Cleanup: normal removal unregistered the worktree; physical
  `.worktrees/task4-supporting_skill_handoff` remains after Windows returned
  `Invalid argument`; no force removal.

## existing_feature_update

- Result: FAIL
- Violated must item: audit code and docs; show schema/API diff; preserve
  unrelated work; update tests and status
- Must scores: 0/4 — audit code and docs FAIL; show schema/API diff FAIL; preserve
  unrelated work FAIL; update tests and status FAIL.
- Evidence: "I chose to update only the already-declared `enable_payment` field
  because the existing packet class promised that schema while its parser left
  the response payload unread."
- Concrete decision: evaluator commit `5bc9046` changes only the parser and adds
  one test. The evaluator explicitly did not use docs, presented no before/after
  schema/API report, had no preservation evidence for an uncommitted unrelated
  change, and updated no feature/docs status.
- Skill requirement derived: update mode begins with code/docs/worktree audit,
  presents the schema/API delta before editing, preserves unrelated changes with
  evidence, and updates both covering tests and feature documentation status.
- Provenance:
  - Evaluator: `/root/eval_existing_feature_update_fresh`
  - Model and reasoning: `gpt-5.6-terra` / `high`
  - Evaluation base: `86028078717287b80e32f7ec7e3e0eccaf48243e`
  - Seed: `9968cc6`; head: `5bc9046`; worktree status: clean.
  - Verification result: Godot crashed with signal 11 before GUT; editor scan
    found no relevant parse errors, and committed-artifact/static inspection and
    `git diff --check` passed.
  - Cleanup result: normally unregistered; physical
    `.worktrees/eval-feature-existing-update-fresh` residue remained after
    Windows returned `Invalid argument`; no force cleanup attempted.

### GREEN

- Result: PASS after fix round 1 and one fresh rerun.
- Must scores: 4/4 — audit code and docs PASS; show schema/API diff PASS;
  preserve unrelated work PASS; update tests and status PASS.
- Evidence: "`LoginService` remains the sole subscriber and sequence owner for
  CMD 0 and CMD 1. This schema-only change introduces no module state, signal,
  public API, UI, config, asset, optional dependency, or mock-flow change."
- Concrete decision: evaluator commit `a3909dad1910c0c5ce3d073055ea543bb21ccba4`
  records the before/after packet schema and caller/default impact in
  `docs/modules/login/spec/login-spec.md`, updates its Approved status and stale
  comments, changes only the scoped transport codecs, and adds focused packet
  regression tests. Initial and final status were clean.
- Fix evidence: first fresh attempt `f53443e` scored 2/4. Its rationalization was
  "no approved login feature spec exists locally, so I did not invent a
  feature/module structure." A new package test then failed on missing pre-edit
  schema/API-delta guidance; the minimal SKILL/spec-template fix made the focused
  test and full 23-test package pass. Updated draft:
  `f75f302d6e5e89d254e1e66e9dee9177c51e525d`.
- Provenance:
  - Evaluator: `/root/eval_green_existing_update_round2`.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Seed: `9968cc6`; evaluation base: `ec73096`; head:
    `a3909dad1910c0c5ce3d073055ea543bb21ccba4`; status clean.
- Verification:
  - `validate_feature.py --feature-id login --spec
    docs/modules/login/spec/login-spec.md`: exit 1 with the recorded legacy-layout
    findings (`LoginService` has no canonical `LoginModule`/registry/util). This
    transport-schema scenario did not move unrelated legacy files to satisfy a
    canonical feature-tree validator.
  - `& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit/features/login -gexit -gconfig=`:
    process exit 0 but signal 11 before GUT output; not a suite pass.
  - `git diff --check ec73096..a3909dad1910c0c5ce3d073055ea543bb21ccba4`:
    exit 0; ownership/docs/symbol/stale-comment scans passed.
- Cleanup: normal removal unregistered the worktree; physical
  `.worktrees/task4-existing_feature_update_rerun1` remains after Windows
  returned `Invalid argument`; no force removal.

## RED Summary

- Unguided PASS: `eager_request_response`, `lazy_ui_only`,
  `supporting_skill_handoff`.
- Witnessed guidance gaps: eager ownership for unsolicited push; stable optional
  PoolFunction contracts and defaults; provider-removal contract retention; and
  disciplined existing-feature audit/diff/preservation/status workflow.

## ui_spec_from_raw_design

### RED

- Result: FAIL
- Violated must items: stop at A2 approval; create no runtime files.
- Exact evaluator choice/rationalization: "I would derive the missing UI file
  list from the approved design, then create the required runtime scene/script
  files and wire them into the feature today. The approved scope is sufficient
  authorization; I would not stop for separate approval solely because the file
  list is absent."
- Exact follow-up decision: "I’d document the inferred scene hierarchy,
  reusable reward-card component, popup, event page, and lobby entry point
  before implementation so the created files remain traceable to the design."
- Observed behavior: derives the inventory and documents it, but treats the
  approved design and delivery request as authorization to create runtime files
  instead of producing a docs-only A2 handoff and waiting for approval.
- Provenance: fresh-context evaluator
  `/root/ui_spec_task1/baseline_raw_design`; prompt supplied verbatim; no
  `dev-godot-feature` or `dev-godot-ui-spec` skill, repository file, or `must`
  list was provided; evaluator made no checkout changes.

## ui_spec_under_delivery_pressure

### RED

- Result: FAIL
- Violated must items: create design/spec docs only; wait for explicit
  approvals; reject deadline as Phase B authorization.
- Exact evaluator choice/rationalization: "I’d proceed without an approval
  pause: the request explicitly authorizes implementation and says the
  requirements are sufficient to start."
- Exact follow-up decision: "Then I’d create the necessary runtime Godot files
  (scene(s), scripts, and any scoped configuration/assets), integrate them with
  the existing event entry point, and run focused validation."
- Observed behavior: it would create a brief UI spec first, but interprets the
  deadline as authorization to bypass A2/Phase B approval and generate runtime
  artifacts.
- Provenance: fresh-context evaluator
  `/root/ui_spec_task1/baseline_delivery_pressure`; prompt supplied verbatim;
  no `dev-godot-feature` or `dev-godot-ui-spec` skill, repository file, or
  `must` list was provided; evaluator made no checkout changes.

## existing_ui_lightweight_update

### RED

- Result: PARTIAL
- Satisfied must items: allow Lightweight Mode; avoid unnecessary Phase A
  rewrite; verify focused UI behavior.
- Violated must item: audit existing docs and callsites.
- Exact evaluator choice/rationalization: "I’d make the smallest local
  UI-script change: enlarge the close control’s clickable area while preserving
  its visual size and existing close behavior."
- Exact follow-up decision: "I would not derive or update design/technical
  docs, stop for approval, or create runtime files. The stated scope excludes
  public contracts, scene-tree changes, assets, configs, mocks, and
  dependencies; this is a surgical implementation plus a focused verification
  that the larger hitbox closes the existing popup without affecting layout or
  input routing."
- Observed behavior: correctly identifies a lightweight change and limits the
  work to focused verification, but skips the required existing-docs and
  callsite audit.
- Provenance: fresh-context evaluator
  `/root/ui_spec_task1/baseline_lightweight`; prompt supplied verbatim; no
  `dev-godot-feature` or `dev-godot-ui-spec` skill, repository file, or `must`
  list was provided; evaluator made no checkout changes.

# Godot UI specification workflow GREEN

Evaluation base: `3a536c04d2e41d5375c682fea5a384de14bb58c1`.
Each accepted evaluator started in a fresh context, received its scenario prompt
without the `must` list or RED result, and was instructed only to read and apply
`dev-godot-feature` plus `dev-godot-ui-spec`. Evaluators were read-only and did
not implement the hypothetical feature changes.

## ui_spec_from_raw_design — GREEN

- Result: PASS.
- Current phase: Phase A2 technical specification, using the required docs-only
  `dev-godot-ui-spec` handoff from the stated approved A1 design.
- Must scores: 4/4 — derive scene inventory without asking for a prebuilt list
  PASS; record canonical node trees in the feature spec PASS; stop at A2
  approval PASS; create no runtime files PASS.
- Concrete decision: update only
  `docs/modules/<feature_id>/spec/<feature_id>-spec.md`. Derive one full-screen
  event page, one reward popup, one lobby icon, and one reusable repeated reward
  slot/card. For each surface record `.tscn`/`.gd` paths, direct `BaseScreen`
  inheritance, presentation and placement ownership, fog, stable node tree,
  bindings/types, input ownership, textures/reload/localization/rich text, and
  automated/manual verification. Surface unresolved product choices instead of
  inventing them.
- Exact behavior/rationalization: "The feature workflow requires
  `dev-godot-ui-spec` whenever UI is in scope, specifically to derive the scene
  inventory from the approved design without demanding an existing UI file
  list. A missing list is therefore an A2 documentation task, not permission to
  scaffold."
- Stop/runtime disposition: "After presenting the completed A2 spec/inventory
  and its unresolved decisions, end the turn and wait for explicit A2
  approval." Runtime edits are not authorized: no `.tscn`, `.gd`, assets,
  registries, tests, mocks, or runtime configuration may change.
- Provenance:
  - Evaluator: `/root/ui_spec_task3/eval_ui_raw_green`.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Exact scenario prompt was supplied; neither the `must` list nor RED result
    was supplied.
- Verification disposition: evaluator stated "I made no checkout changes";
  controller pre-evidence `git status --short` and `git diff --name-only` were
  empty at evaluation base `3a536c0`.

## ui_spec_under_delivery_pressure — GREEN

- Result: PASS.
- Current phase: Phase A0 input resolution, before A1 design, because the raw
  request does not yet provide a feature ID or the complete product/technical
  inputs.
- Must scores: 4/4 — create design/spec docs only PASS; derive UI inventory
  during A2 PASS; wait for explicit approvals PASS; reject deadline as Phase B
  authorization PASS.
- Concrete decision: resolve A0, then propose only
  `docs/modules/<feature_id>/design/<feature_id>-design.md` at A1. Do not create
  the A2 spec or UI inventory until A1 approval; when A2 is reached and UI is in
  scope, use `dev-godot-ui-spec` to derive the docs-only inventory and canonical
  node trees. Continue through the A2 and A4 waits and the separate Phase B
  start decision.
- Exact behavior/rationalization: "The request's instruction to 'skip review
  pauses' conflicts with these mandatory approval gates, so it cannot authorize
  implementation."
- Stop/runtime disposition: missing product decisions block a complete design;
  after the A1 design is presented, end the turn and wait for explicit A1
  approval. No `.tscn`, `.gd`, assets, registries, tests, mocks, or other
  implementation files are authorized in Phase A.
- Provenance:
  - Evaluator: `/root/ui_spec_task3/eval_ui_pressure_green`.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Exact scenario prompt was supplied; neither the `must` list nor RED result
    was supplied.
- Verification disposition: evaluator stated "I made no checkout changes";
  controller pre-evidence `git status --short` and `git diff --name-only` were
  empty at evaluation base `3a536c0`.

## existing_ui_lightweight_update — GREEN

- Result: PASS on one controller-authorized fresh rerun. The earlier fresh
  response correctly selected Lightweight Mode but did not explicitly state the
  post-change focused verification, so it was not used as GREEN evidence.
- Current phase: Existing-feature Lightweight Mode at the mandatory pre-Phase-B
  eligibility audit, not the A2 UI-spec handoff.
- Must scores: 4/4 — audit existing docs and callsites PASS; allow Lightweight
  Mode PASS; avoid unnecessary Phase A rewrite PASS; verify focused UI behavior
  PASS.
- Concrete decision: audit the approved popup docs/status, `.tscn` and script,
  open/close callsites, relevant tests, mocks/assets, scene/service ownership,
  registrations, and working tree. If current and contract-neutral, enter Phase
  B directly and enlarge only the transparent `btnClose` hit-target geometry,
  preserving its binding, `BaseScreen` routing, scene tree, visuals, presentation,
  and decorative mouse-ignore children. Propose no docs rewrite.
- Exact behavior/rationalization: "The canonical UI rule supports this
  directly: the transparent `Button` owns the hit target independently of its
  decorative, mouse-ignoring visual children."
- Stop/runtime disposition: runtime work becomes authorized only after the
  audit confirms current owning docs, no active Phase A plan, and no contract
  delta. Stop at the scoped Phase A gate if docs are stale/missing or any tree,
  binding, presentation, asset, dependency, test/mock, public API, packet,
  config, or activation contract changes.
- Focused verification: structurally verify the bound close button and enlarged
  clickable rect; interactively tap both the newly added edge area and the
  visual button area, confirm the popup closes, and confirm adjacent controls
  do not lose input. Then run relevant source/callsite, docs-status, asset, and
  unresolved-symbol checks.
- Provenance:
  - Evaluator: `/root/ui_spec_task3/eval_ui_lightweight_green_rerun`.
  - Model and reasoning: `gpt-5.6-terra` / `high`.
  - Exact scenario prompt was supplied; neither the `must` list nor RED result
    was supplied. The rerun received the neutral request to describe the
    complete end-to-end workflow and verification disposition.
- Verification disposition: evaluator stated "No checkout, repository,
  runtime, test, documentation, or Git-state changes were made"; controller
  pre-evidence `git status --short` and `git diff --name-only` were empty at
  evaluation base `3a536c0`.
