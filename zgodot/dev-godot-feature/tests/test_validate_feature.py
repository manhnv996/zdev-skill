import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
CASES = json.loads((TESTS_DIR / "fixture_cases.json").read_text(encoding="utf-8"))
VALIDATOR = TESTS_DIR.parent / "scripts" / "validate_feature.py"
DEFAULT_SOURCE_ROOT = "modules/game/event/sample_event"
REGISTRY_PATH = "modules/game/game_feature_registry.gd"


class ValidateFeatureCliTests(unittest.TestCase):
    def _feature_root(self, root: Path) -> Path:
        return root / DEFAULT_SOURCE_ROOT

    def _registry_path(self, root: Path) -> Path:
        return root / REGISTRY_PATH

    def _write(self, root: Path, relative_path: str, content: str = "") -> Path:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _canonical_spec_text(
        self,
        activation: str = "eager",
        has_server_push: bool = True,
        source_root: str = DEFAULT_SOURCE_ROOT,
    ) -> str:
        activation_value = "eager at bootstrap" if activation == "eager" else "lazy from help entry"
        response_kind = "server push" if has_server_push else "response"
        return f"""# Sample Event

## Status
| Field | Approved value |
|---|---|
| Status | Approved |
| Feature ID | `sample_event` |
| Source root | `{source_root}` |
| Activation | {activation_value} |
| Availability source | local rule |

## Existing update record

### Schema/API delta
| Change | Before | After | Caller/default/migration impact |
|---|---|---|---|
| No contract change | current | current | none |

### Documentation status
Current and approved for this fixture.

## Dependencies
| Kind | Dependency | Why | Missing behavior |
|---|---|---|---|
| Required | none | standalone fixture | feature remains available |

## Command ownership
| ID | Direction | Send/receive class | Fields | Response/push | Error behavior |
|---:|---|---|---|---|---|
| 100 | client -> server | `SampleEventSendLoadInfo` | none | response | `load_failed(error_code: int)` |
| 101 | server -> client | `SampleEventRecvLoadInfo` | `balance: int` | {response_kind} | `load_failed(error_code: int)` |

## State and public module API
| Owner | State | Reset rule |
|---|---|---|
| `SampleEventUtil` | balance | clear in `on_reset()` |

| Command/query | Signature | Semantic signal |
|---|---|---|
| command | `request_load_info() -> void` | `load_failed(error_code: int)` |
| query | `get_balance() -> int` | `balance_changed(balance: int)` |

## Optional actions
| Namespaced StringName | Provider method | Call arguments | Explicit default |
|---|---|---|---|
| `&"sample_event.show"` | `show() -> bool` | `[]` | `false` |

## Optional queries
| Namespaced StringName | Provider method | Call arguments | Explicit default |
|---|---|---|---|
| `&"sample_event.balance"` | `get_balance() -> int` | `[]` | `0` |

## JSON configuration
| File | One class | ConfigMgr relative path | Typed accessors |
|---|---|---|---|
| `sample_event_json_config.gd` | `SampleEventJSONConfig` | `sample_event/sample_event.json` | `get_reward() -> int` |

## UI and assets
| Surface | Owner/service | Scene | Notes |
|---|---|---|---|
| none | none | none | no owned UI |

| Asset root | Contents |
|---|---|
| `assets/textures/sample_event/` | owned test assets |

## Verification
| Automated scenario | Expected result |
|---|---|
| `load_info_updates_balance` | `get_balance()` returns 7 and `balance_changed` emits 7 |
| `request_load_info_sends_packet` | `NetworkService` sends `SampleEventSendLoadInfo` with command 100 |

| Interactive mock flow | Expected typed handler/UI result |
|---|---|
| none | no interactive mock |
"""

    def _build_fixture(
        self,
        root: Path,
        activation: str = "eager",
        has_server_push: bool = True,
        source_root: str = DEFAULT_SOURCE_ROOT,
    ) -> Path:
        self._write(
            root,
            "modules/core/base/module/base_module.gd",
            "class_name BaseModule\nfunc on_reset() -> void:\n\tpass\n",
        )
        self._write(
            root,
            "modules/core/managers/module_mgr.gd",
            "static func register_factory(module_id: StringName, module_script: Script, dependencies: Array[StringName] = []) -> Error:\n\treturn OK\n",
        )
        self._write(
            root,
            "modules/core/pool/pool_function.gd",
            "static func remove_all(owner: Object) -> void:\n\tpass\n",
        )
        self._write(
            root,
            "modules/connector/network_service.gd",
            "var last_sent_packet: Variant\n\n"
            "func subscribe(cmd_id: int, packet_class: Script, handler: Callable) -> void:\n\tpass\n\n"
            "func send_packet(packet: Variant) -> void:\n\tlast_sent_packet = packet\n",
        )
        self._write(
            root,
            "modules/game/contracts/sample_event_optional_boundary.gd",
            "class_name SampleEventOptionalBoundary\n"
            "extends RefCounted\n\n"
            "const SHOW: StringName = &\"sample_event.show\"\n"
            "const BALANCE: StringName = &\"sample_event.balance\"\n"
            "const DEFAULT_SHOW: bool = false\n"
            "const DEFAULT_BALANCE: int = 0\n",
        )
        self._write(
            root,
            f"{source_root}/sample_event_module.gd",
            "class_name SampleEventModule\n"
            "extends BaseModule\n\n"
            "const MODULE_ID := &\"sample_event\"\n\n"
            "signal balance_changed(balance: int)\n"
            "signal load_failed(error_code: int)\n\n"
            "var _util := SampleEventUtil.new()\n\n"
            "func on_init() -> void:\n"
            "\tNetworkService.subscribe(101, SampleEventRecvLoadInfo, _on_load_info)\n"
            "\tPoolFunction.reg_func(SampleEventOptionalBoundary.SHOW, self, show)\n"
            "\tPoolFunction.reg_func(SampleEventOptionalBoundary.BALANCE, self, get_balance)\n\n"
            "func on_destroy() -> void:\n"
            "\tNetworkService.unsubscribe_all(self)\n"
            "\tPoolFunction.remove_all(self)\n\n"
            "func request_load_info() -> void:\n"
            "\tvar packet := SampleEventSendLoadInfo.new()\n"
            "\tNetworkService.send_packet(packet)\n\n"
            "func get_balance() -> int:\n"
            "\treturn _util.get_balance()\n\n"
            "func show() -> bool:\n"
            "\treturn true\n\n"
            "func _on_load_info(packet: SampleEventRecvLoadInfo) -> void:\n"
            "\tif not packet.is_ok():\n"
            "\t\tload_failed.emit(packet.error_code)\n"
            "\t\treturn\n"
            "\t_util.set_balance(packet.balance)\n"
            "\tbalance_changed.emit(packet.balance)\n",
        )
        self._write(
            root,
            f"{source_root}/logic/sample_event_util.gd",
            "var _balance: int = 0\n\n"
            "func set_balance(value: int) -> void:\n\t_balance = value\n\n"
            "func get_balance() -> int:\n\treturn _balance\n",
        )
        self._write(
            root,
            "modules/game/sample_event_consumer.gd",
            "func try_show_sample_event() -> bool:\n"
            "\treturn PoolFunction.do_func(\n"
            "\t\tSampleEventOptionalBoundary.SHOW,\n"
            "\t\t[],\n"
            "\t\tSampleEventOptionalBoundary.DEFAULT_SHOW,\n"
            "\t)\n\n"
            "func query_sample_event_balance() -> int:\n"
            "\treturn PoolFunction.do_func(\n"
            "\t\tSampleEventOptionalBoundary.BALANCE,\n"
            "\t\t[],\n"
            "\t\tSampleEventOptionalBoundary.DEFAULT_BALANCE,\n"
            "\t)\n",
        )
        self._write(
            root,
            f"{source_root}/network/sample_event_send_load_info.gd",
            "class_name SampleEventSendLoadInfo\n"
            "extends RefCounted\n\n"
            "const CMD_ID: int = 100\n"
            "var cmd_id: int = CMD_ID\n",
        )
        self._write(
            root,
            f"{source_root}/network/sample_event_recv_load_info.gd",
            "class_name SampleEventRecvLoadInfo\n"
            "extends RefCounted\n\n"
            "const CMD_ID: int = 101\n"
            "var cmd_id: int = CMD_ID\n"
            "var error_code: int = 0\n"
            "var balance: int = 0\n\n"
            "func is_ok() -> bool:\n\treturn error_code == 0\n",
        )
        self._write(
            root,
            f"{source_root}/config/sample_event_json_config.gd",
            "class_name SampleEventJSONConfig\n"
            "extends BaseJSONConfig\n\n"
            "static func get_instance(is_pre_init: bool = false) -> SampleEventJSONConfig:\n"
            "\treturn BaseJSONConfig.register_instance(SampleEventJSONConfig, is_pre_init) as SampleEventJSONConfig\n\n"
            "func get_reward() -> int:\n\treturn 7\n",
        )
        self._write(
            root,
            f"{source_root}/ui/sample_event_main_gui.gd",
            "class_name SampleEventMainGui\nextends BaseScreen\n",
        )
        registry_text = (
            "ModuleMgr.register_factory(SampleEventModule.MODULE_ID, SampleEventModule)\n"
            "ConfigMgr.register_json_file(\"sample_event/sample_event.json\")\n"
            "SampleEventJSONConfig.get_instance(true).pre_init(\"\", \"sample_event/sample_event.json\")\n"
        )
        if activation == "eager":
            registry_text += "ModuleMgr.open_module(SampleEventModule.MODULE_ID)\n"
        self._write(root, REGISTRY_PATH, registry_text)
        self._write(root, "assets/textures/sample_event/.gitkeep")
        self._write(
            root,
            "tests/unit/features/sample_event/test_sample_event_module.gd",
            "extends GutTest\n\n"
            "func test_load_info_updates_balance() -> void:\n"
            "\tvar module := SampleEventModule.new()\n"
            "\twatch_signals(module)\n"
            "\tvar packet := SampleEventRecvLoadInfo.new()\n"
            "\tpacket.balance = 7\n"
            "\tmodule._on_load_info(packet)\n"
            "\tassert_eq(module.get_balance(), 7)\n"
            "\tassert_signal_emitted_with_parameters(module, \"balance_changed\", [7])\n\n"
            "func test_request_load_info_sends_packet() -> void:\n"
            "\tvar module := SampleEventModule.new()\n"
            "\tmodule.request_load_info()\n"
            "\tassert_true(NetworkService.last_sent_packet is SampleEventSendLoadInfo)\n"
            "\tassert_eq(NetworkService.last_sent_packet.cmd_id, 100)\n",
        )
        return self._write(
            root,
            "docs/modules/sample_event/spec/sample_event-spec.md",
            self._canonical_spec_text(activation, has_server_push, source_root),
        )

    def _run(self, root: Path, feature_id: str, spec: Path, json_mode: bool = False) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(VALIDATOR),
            "--project-root",
            str(root),
            "--feature-id",
            feature_id,
            "--spec",
            str(spec),
        ]
        if json_mode:
            command.append("--json")
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def _apply_case(self, root: Path, spec: Path, case: dict[str, object]) -> None:
        activation = case.get("activation")
        has_server_push = case.get("hasServerPush")
        if activation is not None or has_server_push is not None:
            spec = self._build_fixture(
                root,
                str(activation or "eager"),
                bool(has_server_push) if has_server_push is not None else True,
            )

        feature_root = self._feature_root(root)
        registry = self._registry_path(root)
        util = feature_root / "logic/sample_event_util.gd"
        module = feature_root / "sample_event_module.gd"
        ui = feature_root / "ui/sample_event_main_gui.gd"
        test_file = root / "tests/unit/features/sample_event/test_sample_event_module.gd"

        if case.get("remove") == "module":
            module.unlink()
        elif case.get("remove") == "registry_entry":
            registry.write_text("ModuleMgr.open_module(SampleEventModule.MODULE_ID)\n", encoding="utf-8")
        elif case.get("remove") == "registry_open":
            registry.write_text("ModuleMgr.register_factory(SampleEventModule.MODULE_ID, SampleEventModule)\n", encoding="utf-8")
        elif case.get("remove") == "tests":
            test_file.unlink()

        injection = case.get("inject")
        if injection == "ui_network_subscribe":
            ui.write_text(
                ui.read_text(encoding="utf-8")
                + "\nfunc connect_network() -> void:\n"
                + "\tNetworkService.subscribe(100, SampleEventRecvLoadInfo, Callable())\n",
                encoding="utf-8",
            )
        elif injection == "ui_wrong_base":
            ui.write_text(
                ui.read_text(encoding="utf-8").replace("extends BaseScreen", "extends GuiBase"),
                encoding="utf-8",
            )
        elif injection == "remove_destroy_cleanup":
            module.write_text(module.read_text(encoding="utf-8").replace("\tNetworkService.unsubscribe_all(self)\n", ""), encoding="utf-8")
        elif injection == "bad_optional_key":
            spec.write_text(spec.read_text(encoding="utf-8").replace('&"sample_event.show"', '&"show"'), encoding="utf-8")
        elif injection == "missing_query_default":
            spec.write_text(
                spec.read_text(encoding="utf-8").replace(
                    '| `&"sample_event.balance"` | `get_balance() -> int` | `[]` | `0` |',
                    '| `&"sample_event.balance"` | `get_balance() -> int` | `[]` |  |',
                ),
                encoding="utf-8",
            )
        elif injection == "registry_open":
            registry.write_text(
                "ModuleMgr.register_factory(SampleEventModule.MODULE_ID, SampleEventModule)\nModuleMgr.open_module(SampleEventModule.MODULE_ID)\n",
                encoding="utf-8",
            )

    def _hash_map(self, root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def _replace_file(self, path: Path, before: str, after: str) -> None:
        text = path.read_text(encoding="utf-8")
        self.assertIn(before, text, "fixture mutation target must exist: %s" % before)
        path.write_text(text.replace(before, after, 1), encoding="utf-8")

    def _assert_contract_finding(self, root: Path, spec: Path, code: str) -> None:
        result = self._run(root, "sample_event", spec)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(code, result.stdout + result.stderr)

    def test_valid_eager_network_feature_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            result = self._run(root, "sample_event", spec)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, "")

    def test_no_argument_signal_and_packet_only_scenario_are_exact_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            self._replace_file(
                spec,
                '| query | `get_balance() -> int` | `balance_changed(balance: int)` |',
                '| query | `get_balance() -> int` | `balance_changed(balance: int)` |\n'
                '| command | `refresh() -> void` | `refreshed()` |',
            )
            self._replace_file(
                spec,
                '| `request_load_info_sends_packet` | `NetworkService` sends `SampleEventSendLoadInfo` with command 100 |',
                '| `request_load_info_sends_packet` | `NetworkService` sends `SampleEventSendLoadInfo` with command 100 |\n'
                '| `recv_packet_owns_command` | `SampleEventRecvLoadInfo.CMD_ID` equals 101 |',
            )
            module = self._feature_root(root) / "sample_event_module.gd"
            self._replace_file(
                module,
                "signal load_failed(error_code: int)\n",
                "signal load_failed(error_code: int)\nsignal refreshed\n",
            )
            self._replace_file(
                module,
                "func get_balance() -> int:\n\treturn _util.get_balance()\n",
                "func get_balance() -> int:\n\treturn _util.get_balance()\n\n"
                "func refresh() -> void:\n\trefreshed.emit()\n",
            )
            test_path = root / "tests/unit/features/sample_event/test_sample_event_module.gd"
            test_path.write_text(
                test_path.read_text(encoding="utf-8")
                + "\nfunc test_recv_packet_owns_command() -> void:\n"
                + "\tvar packet := SampleEventRecvLoadInfo.new()\n"
                + "\tassert_eq(packet.CMD_ID, 101)\n",
                encoding="utf-8",
            )

            result = self._run(root, "sample_event", spec)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_typed_send_packet_local_is_a_valid_exact_callsite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            module = self._feature_root(root) / "sample_event_module.gd"
            self._replace_file(
                module,
                "var packet := SampleEventSendLoadInfo.new()",
                "var packet: SampleEventSendLoadInfo = SampleEventSendLoadInfo.new()",
            )

            result = self._run(root, "sample_event", spec)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_assigned_local_from_documented_call_is_meaningful_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            test_path = root / "tests/unit/features/sample_event/test_sample_event_module.gd"
            self._replace_file(
                test_path,
                "\tassert_eq(module.get_balance(), 7)",
                "\tvar observed_balance := module.get_balance()\n"
                "\tassert_eq(observed_balance, 7)",
            )

            result = self._run(root, "sample_event", spec)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_root_status_drives_grouped_feature_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)

            result = self._run(root, "sample_event", spec)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_root_status_supports_standalone_feature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root = "modules/game/sample_event"
            spec = self._build_fixture(root, source_root=source_root)

            result = self._run(root, "sample_event", spec)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_features_group_is_valid_only_when_explicitly_approved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root = "modules/game/features/sample_event"
            spec = self._build_fixture(root, source_root=source_root)

            result = self._run(root, "sample_event", spec)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_or_unsafe_source_root_is_rejected(self) -> None:
        unsafe_source_roots = (
            "res://modules/game/sample_event",
            "C:/game/sample_event",
            "modules\\game\\sample_event",
            "modules/game/../sample_event",
            "modules/game/SampleEvent",
            "modules/game/event/not_sample_event",
        )
        for source_root in (None, *unsafe_source_roots):
            with self.subTest(source_root=source_root), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                spec_text = spec.read_text(encoding="utf-8")
                source_root_row = "| Source root | `%s` |\n" % DEFAULT_SOURCE_ROOT
                replacement = "" if source_root is None else "| Source root | `%s` |\n" % source_root
                spec.write_text(spec_text.replace(source_root_row, replacement), encoding="utf-8")

                self._assert_contract_finding(root, spec, "invalid_source_root")

    def test_registry_must_live_at_game_composition_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            registry = root / REGISTRY_PATH
            legacy_registry = root / "modules/game/features/game_feature_registry.gd"
            legacy_registry.parent.mkdir(parents=True, exist_ok=True)
            registry.replace(legacy_registry)

            result = self._run(root, "sample_event", spec)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("missing_registration", result.stdout)
            self.assertIn(REGISTRY_PATH, result.stdout)

    def test_populated_template_format_spec_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            spec.write_text(self._canonical_spec_text(), encoding="utf-8")

            result = self._run(root, "sample_event", spec)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, "")

    def test_invalid_feature_id_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            result = self._run(root, "SampleEvent", spec)
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid_feature_id", result.stdout + result.stderr)

    def test_each_contract_violation_exits_one_with_expected_code(self) -> None:
        for case in CASES["invalidContracts"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                self._apply_case(root, spec, case)
                result = self._run(root, "sample_event", spec)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(case["code"], result.stdout + result.stderr)

        for case in CASES["invalidArguments"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                result = self._run(root, case["featureId"], spec)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(case["code"], result.stdout + result.stderr)

    def test_json_mode_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            result = self._run(root, "sample_event", spec, json_mode=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(set(payload), {"valid", "findings"})

    def test_ui_must_directly_extend_base_screen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            spec = self._build_fixture(root)
            ui = self._feature_root(root) / "ui/sample_event_main_gui.gd"
            ui.write_text("class_name SampleEventMainGui\nextends Control\n", encoding="utf-8")
            result = self._run(root, "sample_event", spec, json_mode=True)
            self.assertIn("ui_not_base_screen", result.stdout)

    def test_gui_base_is_not_canonical_feature_ui_base(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            spec = self._build_fixture(root)
            ui = self._feature_root(root) / "ui/sample_event_main_gui.gd"
            ui.write_text("class_name SampleEventMainGui\nextends GuiBase\n", encoding="utf-8")
            result = self._run(root, "sample_event", spec, json_mode=True)
            self.assertIn("ui_not_base_screen", result.stdout)

    def test_base_screen_in_comment_or_string_does_not_satisfy_ui_base(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            spec = self._build_fixture(root)
            ui = self._feature_root(root) / "ui/sample_event_main_gui.gd"
            ui.write_text(
                'class_name SampleEventMainGui\nextends Control\n# extends BaseScreen\nvar note := "extends BaseScreen"\n',
                encoding="utf-8",
            )
            result = self._run(root, "sample_event", spec, json_mode=True)
            self.assertIn("ui_not_base_screen", result.stdout)

    def test_non_control_world_script_may_live_below_ui(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            spec = self._build_fixture(root)
            self._write(
                root,
                DEFAULT_SOURCE_ROOT + "/ui/battle/world/sample_event_battle_world.gd",
                "class_name SampleEventBattleWorld\nextends Node2D\n",
            )
            result = self._run(root, "sample_event", spec, json_mode=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("ui_not_base_screen", result.stdout)

    def test_validator_never_modifies_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            before = self._hash_map(root)
            text_result = self._run(root, "sample_event", spec)
            json_result = self._run(root, "sample_event", spec, json_mode=True)
            self.assertEqual(text_result.returncode, 0, text_result.stdout + text_result.stderr)
            self.assertEqual(json_result.returncode, 0, json_result.stdout + json_result.stderr)
            self.assertEqual(self._hash_map(root), before)

    def test_optional_action_parser_is_section_scoped_and_requires_string_name(self) -> None:
        mutations = {
            "ordinary_string": ('`&"sample_event.show"`', '`"sample_event.show"`', "malformed_optional_action"),
            "trailing_syntax": ('`&"sample_event.show"`', '`&"sample_event.show" trailing`', "malformed_optional_action"),
            "missing_default": (
                '| `&"sample_event.show"` | `show() -> bool` | `[]` | `false` |',
                '| `&"sample_event.show"` | `show() -> bool` | `[]` |  |',
                "missing_optional_default",
            ),
        }
        for case_id, (before, after, code) in mutations.items():
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                spec.write_text(spec.read_text(encoding="utf-8").replace(before, after), encoding="utf-8")
                self._assert_contract_finding(root, spec, code)

        with self.subTest(case="unrelated_string_name"), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            spec.write_text(spec.read_text(encoding="utf-8") + '\nRequired local ID: &"shared.key"\n', encoding="utf-8")
            result = self._run(root, "sample_event", spec)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_status_and_command_tables_are_the_only_activation_and_push_sources(self) -> None:
        with self.subTest(case="legacy_activation_cannot_override_table"), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            spec.write_text(
                spec.read_text(encoding="utf-8").replace(
                    "| Activation | eager at bootstrap |",
                    "| Activation | on_demand |",
                )
                + "\nActivation: eager\n",
                encoding="utf-8",
            )
            self._assert_contract_finding(root, spec, "invalid_activation")

        with self.subTest(case="legacy_push_cannot_override_table"), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root, activation="lazy", has_server_push=False)
            spec.write_text(
                spec.read_text(encoding="utf-8") + "\nOwned server-push commands:\n- SAMPLE_EVENT_LOAD_INFO\n",
                encoding="utf-8",
            )
            result = self._run(root, "sample_event", spec)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        with self.subTest(case="command_table_push_is_enforced"), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root, activation="lazy", has_server_push=True)
            spec.write_text(
                spec.read_text(encoding="utf-8") + "\nOwned server-push commands:\n- none\n",
                encoding="utf-8",
            )
            self._assert_contract_finding(root, spec, "lazy_push_owner")

    def test_asset_root_table_is_scoped_to_ui_and_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            spec.write_text(
                spec.read_text(encoding="utf-8").replace(
                    "| `assets/textures/sample_event/` | owned test assets |",
                    "| none | no owned assets |",
                )
                + "\n## Unrelated inventory\n"
                "| Asset root | Contents |\n"
                "|---|---|\n"
                "| `assets/missing/` | must not be treated as feature ownership |\n",
                encoding="utf-8",
            )

            result = self._run(root, "sample_event", spec)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_optional_query_table_requires_namespaced_key_and_default(self) -> None:
        valid_row = '| `&"sample_event.balance"` | `get_balance() -> int` | `[]` | `0` |'
        cases = (
            (
                "missing_default",
                '| `&"sample_event.balance"` | `get_balance() -> int` | `[]` |  |',
                "missing_optional_default",
            ),
            (
                "ordinary_string_key",
                '| `"sample_event.balance"` | `get_balance() -> int` | `[]` | `0` |',
                "malformed_optional_query",
            ),
            (
                "wrong_namespace",
                '| `&"shared.balance"` | `get_balance() -> int` | `[]` | `0` |',
                "unnamespaced_action",
            ),
        )
        for case_id, replacement_row, code in cases:
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                spec.write_text(spec.read_text(encoding="utf-8").replace(valid_row, replacement_row), encoding="utf-8")
                self._assert_contract_finding(root, spec, code)

        with self.subTest(case="valid_nested_arguments"), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            nested_row = '| `&"sample_event.balance"` | `get_balance() -> int` | `[Vector2(1, 2), {"label": "x,y"}]` | `0` |'
            spec.write_text(spec.read_text(encoding="utf-8").replace(valid_row, nested_row), encoding="utf-8")
            consumer = root / "modules/game/sample_event_consumer.gd"
            self._replace_file(
                consumer,
                "\t\tSampleEventOptionalBoundary.BALANCE,\n\t\t[],",
                '\t\tSampleEventOptionalBoundary.BALANCE,\n\t\t[Vector2(1, 2), {"label": "x,y"}],',
            )
            result = self._run(root, "sample_event", spec)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cleanup_is_required_only_for_owned_resources(self) -> None:
        with self.subTest(case="no_owned_resources"), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root, has_server_push=False)
            spec_text = spec.read_text(encoding="utf-8")
            spec_text = spec_text.replace(
                '| 100 | client -> server | `SampleEventSendLoadInfo` | none | response | `load_failed(error_code: int)` |\n'
                '| 101 | server -> client | `SampleEventRecvLoadInfo` | `balance: int` | response | `load_failed(error_code: int)` |',
                "| none | none | none | none | none | none |",
            )
            spec_text = spec_text.replace(
                '| command | `request_load_info() -> void` | `load_failed(error_code: int)` |\n'
                '| query | `get_balance() -> int` | `balance_changed(balance: int)` |',
                '| query | `get_balance() -> int` | none |',
            )
            spec_text = spec_text.replace(
                '| `&"sample_event.show"` | `show() -> bool` | `[]` | `false` |',
                "| none | none | none | none |",
            )
            spec_text = spec_text.replace(
                '| `&"sample_event.balance"` | `get_balance() -> int` | `[]` | `0` |',
                "| none | none | none | none |",
            )
            spec_text = spec_text.replace(
                '| `load_info_updates_balance` | `get_balance()` returns 7 and `balance_changed` emits 7 |\n'
                '| `request_load_info_sends_packet` | `NetworkService` sends `SampleEventSendLoadInfo` with command 100 |',
                '| `balance_defaults_to_zero` | `get_balance()` returns 0 without opening owned resources |',
            )
            spec.write_text(spec_text, encoding="utf-8")
            module = self._feature_root(root) / "sample_event_module.gd"
            module.write_text(
                "class_name SampleEventModule\nextends BaseModule\n\n"
                "const MODULE_ID := &\"sample_event\"\n\n"
                "func get_balance() -> int:\n\treturn 0\n",
                encoding="utf-8",
            )
            test_path = root / "tests/unit/features/sample_event/test_sample_event_module.gd"
            test_path.write_text(
                "extends GutTest\n\n"
                "func test_balance_defaults_to_zero() -> void:\n"
                "\tvar module := SampleEventModule.new()\n"
                "\tassert_eq(module.get_balance(), 0)\n",
                encoding="utf-8",
            )
            result = self._run(root, "sample_event", spec)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        with self.subTest(case="network_owner"), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            module = self._feature_root(root) / "sample_event_module.gd"
            module.write_text(
                module.read_text(encoding="utf-8").replace("\tNetworkService.unsubscribe_all(self)\n", ""),
                encoding="utf-8",
            )
            self._assert_contract_finding(root, spec, "missing_owner_cleanup")

        with self.subTest(case="pool_owner"), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root, has_server_push=False)
            module = self._feature_root(root) / "sample_event_module.gd"
            module.write_text(
                "class_name SampleEventModule\nextends BaseModule\n\n"
                "const MODULE_ID := &\"sample_event\"\n\n"
                "func on_init() -> void:\n\tPoolFunction.reg_func(&\"sample_event.show\", self, _show)\n\n"
                "func on_destroy() -> void:\n\tpass\n\n"
                "func _show() -> bool:\n\treturn true\n",
                encoding="utf-8",
            )
            self._assert_contract_finding(root, spec, "missing_owner_cleanup")

    def test_cleanup_calls_must_be_inside_on_destroy(self) -> None:
        cases = {
            "network_cleanup_in_on_init": (
                "func on_init() -> void:\n"
                "\tNetworkService.subscribe(100, SampleEventRecvLoadInfo, _on_load_info)\n"
                "\tNetworkService.unsubscribe_all(self)\n\n"
                "func on_destroy() -> void:\n\tPoolFunction.remove_all(self)\n"
            ),
            "pool_cleanup_in_on_init": (
                "func on_init() -> void:\n"
                "\tNetworkService.subscribe(100, SampleEventRecvLoadInfo, _on_load_info)\n"
                "\tPoolFunction.reg_func(&\"sample_event.show\", self, _on_load_info)\n"
                "\tPoolFunction.remove_all(self)\n\n"
                "func on_destroy() -> void:\n\tNetworkService.unsubscribe_all(self)\n"
            ),
            "network_cleanup_in_string": (
                "func on_init() -> void:\n"
                "\tNetworkService.subscribe(100, SampleEventRecvLoadInfo, _on_load_info)\n\n"
                'func on_destroy() -> void:\n\tvar note := "NetworkService.unsubscribe_all(self)"\n'
            ),
            "pool_cleanup_in_comment": (
                "func on_init() -> void:\n"
                "\tNetworkService.subscribe(100, SampleEventRecvLoadInfo, _on_load_info)\n"
                "\tPoolFunction.reg_func(&\"sample_event.show\", self, _on_load_info)\n\n"
                "func on_destroy() -> void:\n"
                "\tNetworkService.unsubscribe_all(self)\n"
                "\t# PoolFunction.remove_all(self)\n"
            ),
        }
        for case_id, lifecycle in cases.items():
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                module = self._feature_root(root) / "sample_event_module.gd"
                module.write_text(
                    "class_name SampleEventModule\nextends BaseModule\n\n"
                    "const MODULE_ID := &\"sample_event\"\n\n"
                    + lifecycle
                    + "\nfunc _on_load_info(_packet: Variant) -> void:\n\tpass\n",
                    encoding="utf-8",
                )
                self._assert_contract_finding(root, spec, "missing_owner_cleanup")

    def test_registry_ignores_registration_and_open_calls_in_comments_or_strings(self) -> None:
        fake_templates = {
            "comment": "# %s\n",
            "string": 'var note := "%s"\n',
        }
        registration = "ModuleMgr.register_factory(SampleEventModule.MODULE_ID, SampleEventModule)"
        open_call = "ModuleMgr.open_module(SampleEventModule.MODULE_ID)"
        config_calls = (
            'ConfigMgr.register_json_file("sample_event/sample_event.json")\n'
            'SampleEventJSONConfig.get_instance(true).pre_init("", "sample_event/sample_event.json")\n'
        )
        for representation, fake_template in fake_templates.items():
            with self.subTest(case=representation + "_registration"), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                registry = self._registry_path(root)
                registry.write_text(fake_template % registration + open_call + "\n" + config_calls, encoding="utf-8")
                self._assert_contract_finding(root, spec, "missing_registration")

            with self.subTest(case=representation + "_eager_open"), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                registry = self._registry_path(root)
                registry.write_text(registration + "\n" + fake_template % open_call + config_calls, encoding="utf-8")
                self._assert_contract_finding(root, spec, "missing_eager_open")

            with self.subTest(case=representation + "_lazy_open"), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root, activation="lazy", has_server_push=False)
                registry = self._registry_path(root)
                registry.write_text(registration + "\n" + fake_template % open_call + config_calls, encoding="utf-8")
                result = self._run(root, "sample_event", spec)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_module_does_not_cascade_registry_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            (self._feature_root(root) / "sample_event_module.gd").unlink()
            self._registry_path(root).write_text("", encoding="utf-8")

            result = self._run(root, "sample_event", spec)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("missing_module", result.stdout)
            self.assertNotIn("missing_registration", result.stdout)
            self.assertNotIn("missing_eager_open", result.stdout)

    def test_documented_server_push_requires_owner_subscription(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            module = self._feature_root(root) / "sample_event_module.gd"
            module.write_text(
                module.read_text(encoding="utf-8").replace(
                    "\tNetworkService.subscribe(101, SampleEventRecvLoadInfo, _on_load_info)\n",
                    "\t# NetworkService.subscribe is intentionally absent.\n",
                ),
                encoding="utf-8",
            )
            self._assert_contract_finding(root, spec, "missing_owner_subscription")

    def test_command_contract_requires_exact_id_class_registration_and_send_callsite(self) -> None:
        cases = (
            (
                "packet_id",
                DEFAULT_SOURCE_ROOT + "/network/sample_event_recv_load_info.gd",
                "const CMD_ID: int = 101",
                "const CMD_ID: int = 102",
                "command_id_mismatch",
            ),
            (
                "packet_class",
                DEFAULT_SOURCE_ROOT + "/network/sample_event_recv_load_info.gd",
                "class_name SampleEventRecvLoadInfo",
                "class_name SampleEventWrongRecv",
                "command_class_mismatch",
            ),
            (
                "subscription_registration",
                DEFAULT_SOURCE_ROOT + "/sample_event_module.gd",
                "NetworkService.subscribe(101, SampleEventRecvLoadInfo, _on_load_info)",
                "NetworkService.subscribe(999, SampleEventRecvLoadInfo, _on_load_info)",
                "command_registration_mismatch",
            ),
            (
                "send_callsite",
                DEFAULT_SOURCE_ROOT + "/sample_event_module.gd",
                "var packet := SampleEventSendLoadInfo.new()",
                "var packet := SampleEventWrongSend.new()",
                "command_callsite_mismatch",
            ),
        )
        for case_id, relative_path, before, after, finding in cases:
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                self._replace_file(root / relative_path, before, after)
                self._assert_contract_finding(root, spec, finding)

    def test_public_api_and_semantic_signals_match_exact_spec_signatures(self) -> None:
        cases = (
            (
                "public_return_type",
                "func get_balance() -> int:",
                "func get_balance() -> Variant:",
                "public_api_mismatch",
            ),
            (
                "signal_declaration",
                "signal balance_changed(balance: int)",
                "signal balance_changed(value: int)",
                "semantic_signal_mismatch",
            ),
            (
                "signal_emission",
                "\tbalance_changed.emit(packet.balance)\n",
                "\tpass\n",
                "semantic_signal_mismatch",
            ),
        )
        for case_id, before, after, finding in cases:
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                module = self._feature_root(root) / "sample_event_module.gd"
                self._replace_file(module, before, after)
                self._assert_contract_finding(root, spec, finding)

    def test_optional_contract_matches_neutral_constants_registration_callsite_and_default(self) -> None:
        cases = (
            (
                "provider_registration",
                DEFAULT_SOURCE_ROOT + "/sample_event_module.gd",
                "PoolFunction.reg_func(SampleEventOptionalBoundary.SHOW, self, show)",
                "PoolFunction.reg_func(SampleEventOptionalBoundary.BALANCE, self, show)",
                "optional_registration_mismatch",
            ),
            (
                "consumer_arguments",
                "modules/game/sample_event_consumer.gd",
                "\t\t[],\n\t\tSampleEventOptionalBoundary.DEFAULT_SHOW,",
                "\t\t[1],\n\t\tSampleEventOptionalBoundary.DEFAULT_SHOW,",
                "optional_callsite_mismatch",
            ),
            (
                "provider_signature",
                DEFAULT_SOURCE_ROOT + "/sample_event_module.gd",
                "func show() -> bool:",
                "func show() -> Variant:",
                "optional_provider_mismatch",
            ),
            (
                "retained_default",
                "modules/game/contracts/sample_event_optional_boundary.gd",
                "const DEFAULT_SHOW: bool = false",
                "const DEFAULT_SHOW: bool = true",
                "optional_default_mismatch",
            ),
        )
        for case_id, relative_path, before, after, finding in cases:
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                self._replace_file(root / relative_path, before, after)
                self._assert_contract_finding(root, spec, finding)

    def test_config_contract_matches_file_class_registration_path_and_accessor(self) -> None:
        cases = (
            (
                "class_name",
                DEFAULT_SOURCE_ROOT + "/config/sample_event_json_config.gd",
                "class_name SampleEventJSONConfig",
                "class_name SampleEventJsonConfig",
                "config_class_mismatch",
            ),
            (
                "registration_path",
                REGISTRY_PATH,
                'ConfigMgr.register_json_file("sample_event/sample_event.json")',
                'ConfigMgr.register_json_file("sample_event/wrong.json")',
                "config_registration_mismatch",
            ),
            (
                "typed_accessor",
                DEFAULT_SOURCE_ROOT + "/config/sample_event_json_config.gd",
                "func get_reward() -> int:",
                "func get_reward() -> Variant:",
                "config_accessor_mismatch",
            ),
        )
        for case_id, relative_path, before, after, finding in cases:
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                self._replace_file(root / relative_path, before, after)
                self._assert_contract_finding(root, spec, finding)

    def test_same_schema_config_family_uses_one_class_with_caller_owned_instances(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            spec.write_text(
                spec.read_text(encoding="utf-8").replace(
                    "| `sample_event_json_config.gd` | `SampleEventJSONConfig` | `sample_event/sample_event.json` | `get_reward() -> int` |",
                    "| `sample_event_json_config.gd` | `SampleEventJSONConfig` | `sample_event/sample_event.json` | `get_reward() -> int` |\n"
                    "| `sample_event_map_json_config.gd` | `SampleEventMapJSONConfig` | `sample_event/maps/sample_event_map_{01..02}.json` | `get_map() -> Dictionary` |",
                ),
                encoding="utf-8",
            )
            self._write(
                root,
                DEFAULT_SOURCE_ROOT + "/config/sample_event_map_json_config.gd",
                "class_name SampleEventMapJSONConfig\n"
                "extends BaseJSONConfig\n\n"
                "func bind_source(path: String) -> void:\n\tpre_init(\"\", path)\n\n"
                "func get_map() -> Dictionary:\n\treturn {}\n\n"
                "func reset() -> void:\n\tsuper.reset()\n",
            )
            self._write(
                root,
                DEFAULT_SOURCE_ROOT + "/logic/sample_event_config_service.gd",
                "func initialize(paths: Array[String]) -> void:\n"
                "\tfor path: String in paths:\n"
                "\t\tConfigMgr.register_json_file(path)\n"
                "\t\tvar loader := SampleEventMapJSONConfig.new()\n"
                "\t\tloader.bind_source(path)\n",
            )
            result = self._run(root, "sample_event", spec, json_mode=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            family_loader = self._feature_root(root) / "config/sample_event_map_json_config.gd"
            family_loader.write_text(
                family_loader.read_text(encoding="utf-8")
                + "\nstatic func get_instance() -> SampleEventMapJSONConfig:\n"
                + "\treturn BaseJSONConfig.register_instance(SampleEventMapJSONConfig) as SampleEventMapJSONConfig\n",
                encoding="utf-8",
            )
            invalid_result = self._run(root, "sample_event", spec, json_mode=True)
            self.assertIn("config_family_singleton_mismatch", invalid_result.stdout)

    def test_automated_scenarios_require_exact_asserted_gut_evidence(self) -> None:
        with self.subTest(case="scenario_name_mismatch"), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            test_path = root / "tests/unit/features/sample_event/test_sample_event_module.gd"
            self._replace_file(
                test_path,
                "func test_load_info_updates_balance() -> void:",
                "func test_unrelated_balance_case() -> void:",
            )
            self._assert_contract_finding(root, spec, "missing_scenario_test")

        with self.subTest(case="construction_only"), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            test_path = root / "tests/unit/features/sample_event/test_sample_event_module.gd"
            test_path.write_text(
                "extends GutTest\n\n"
                "func test_load_info_updates_balance() -> void:\n"
                "\tvar module := SampleEventModule.new()\n"
                "\tassert_not_null(module)\n\n"
                "func test_request_load_info_sends_packet() -> void:\n"
                "\tvar module := SampleEventModule.new()\n"
                "\tassert_not_null(module)\n",
                encoding="utf-8",
            )
            self._assert_contract_finding(root, spec, "weak_scenario_test")

        unrelated_assertions = (
            "assert_true(true)",
            "assert_false(false)",
            "assert_eq(7, 7)",
        )
        for unrelated_assertion in unrelated_assertions:
            with self.subTest(
                case="documented_call_with_unrelated_assertion",
                assertion=unrelated_assertion,
            ), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                test_path = root / "tests/unit/features/sample_event/test_sample_event_module.gd"
                test_path.write_text(
                    "extends GutTest\n\n"
                    "func test_load_info_updates_balance() -> void:\n"
                    "\tvar module := SampleEventModule.new()\n"
                    "\tmodule.get_balance()\n"
                    "\t%s\n\n" % unrelated_assertion
                    + "func test_request_load_info_sends_packet() -> void:\n"
                    "\tvar module := SampleEventModule.new()\n"
                    "\tmodule.request_load_info()\n"
                    "\tassert_true(NetworkService.last_sent_packet is SampleEventSendLoadInfo)\n",
                    encoding="utf-8",
                )
                self._assert_contract_finding(root, spec, "weak_scenario_test")

    def test_module_coverage_requires_executable_gut_test_reference(self) -> None:
        invalid_tests = {
            "comment_only": "# extends GutTest\n# func test_module_exists(): SampleEventModule.new()\n",
            "helper_only": "extends GutTest\n\nfunc build_module() -> Variant:\n\treturn SampleEventModule.new()\n",
            "comment_reference": "extends GutTest\n\nfunc test_placeholder() -> void:\n\t# SampleEventModule should be tested later.\n\tassert_true(true)\n",
        }
        for case_id, test_text in invalid_tests.items():
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                test_path = root / "tests/unit/features/sample_event/test_sample_event_module.gd"
                test_path.write_text(test_text, encoding="utf-8")
                self._assert_contract_finding(root, spec, "missing_tests")

    def test_foundation_unavailable_exits_two(self) -> None:
        mutations = (
            ("modules/core/base/module/base_module.gd", "func on_reset", "func reset_missing"),
            ("modules/core/managers/module_mgr.gd", "static func register_factory", "static func factory_missing"),
            ("modules/core/managers/module_mgr.gd", "dependencies: Array[StringName]", "dependencies: Array"),
            ("modules/core/pool/pool_function.gd", "static func remove_all", "static func cleanup_missing"),
            ("modules/connector/network_service.gd", "func subscribe", "func subscribe_missing"),
        )
        for relative_path, before, after in mutations:
            with self.subTest(path=relative_path, token=before), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                foundation = root / relative_path
                foundation.write_text(foundation.read_text(encoding="utf-8").replace(before, after), encoding="utf-8")
                result = self._run(root, "sample_event", spec)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("foundation_unavailable", result.stdout + result.stderr)

    def test_invalid_project_root_and_spec_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._build_fixture(root)
            result = self._run(root / "missing-project", "sample_event", spec)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("invalid_project_root", result.stdout + result.stderr)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._build_fixture(root)
            result = self._run(root, "sample_event", root / "missing-spec.md")
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("invalid_spec_path", result.stdout + result.stderr)

    def test_required_contract_groups_emit_expected_codes(self) -> None:
        def remove_feature_root(root: Path, _spec: Path) -> None:
            shutil.rmtree(self._feature_root(root))

        def remove_util(root: Path, _spec: Path) -> None:
            (self._feature_root(root) / "logic/sample_event_util.gd").unlink()

        def invalidate_activation(_root: Path, spec: Path) -> None:
            spec.write_text(
                spec.read_text(encoding="utf-8").replace(
                    "| Activation | eager at bootstrap |",
                    "| Activation | on_demand |",
                ),
                encoding="utf-8",
            )

        def remove_base_class(root: Path, _spec: Path) -> None:
            module = self._feature_root(root) / "sample_event_module.gd"
            module.write_text(module.read_text(encoding="utf-8").replace("extends BaseModule", "extends RefCounted"), encoding="utf-8")

        def add_non_ui_subscription(root: Path, _spec: Path) -> None:
            self._write(
                root,
                DEFAULT_SOURCE_ROOT + "/logic/sample_event_listener.gd",
                "func on_init() -> void:\n\tNetworkService.subscribe(101, SampleEventRecvLoadInfo, _on_load_info)\n",
            )

        def add_ui_send(root: Path, _spec: Path) -> None:
            ui = self._feature_root(root) / "ui/sample_event_main_gui.gd"
            ui.write_text(
                ui.read_text(encoding="utf-8")
                + "\nfunc send() -> void:\n"
                + "\tNetworkService.send_packet(100)\n",
                encoding="utf-8",
            )

        def add_bad_network_filename(root: Path, _spec: Path) -> None:
            self._write(root, DEFAULT_SOURCE_ROOT + "/network/load_info.gd", "class_name LoadInfo\n")

        def remove_asset_root(root: Path, _spec: Path) -> None:
            keep = root / "assets/textures/sample_event/.gitkeep"
            keep.unlink()
            keep.parent.rmdir()

        cases = (
            ("missing_feature_root", remove_feature_root, "missing_feature_root"),
            ("missing_util", remove_util, "missing_util"),
            ("invalid_activation", invalidate_activation, "invalid_activation"),
            ("module_not_base_module", remove_base_class, "module_not_base_module"),
            ("non_ui_subscription", add_non_ui_subscription, "network_outside_module"),
            ("ui_send_packet", add_ui_send, "network_outside_module"),
            ("invalid_network_filename", add_bad_network_filename, "invalid_network_filename"),
            ("missing_asset_root", remove_asset_root, "missing_asset_root"),
        )
        for case_id, mutate, code in cases:
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = self._build_fixture(root)
                mutate(root, spec)
                result = self._run(root, "sample_event", spec)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(code, result.stdout + result.stderr)
                if case_id == "ui_send_packet":
                    self.assertNotIn("ui_not_base_screen", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
