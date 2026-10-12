import json
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = SKILL_ROOT / "SKILL.md"
BASELINE_PATH = SKILL_ROOT / "tests" / "baseline.md"
UI_SCENE_PATTERNS_PATH = (
    SKILL_ROOT.parent / "dev-godot-ui-spec" / "references" / "ui-scene-tree-patterns.md"
)
UI_SKILL_PATH = SKILL_ROOT.parent / "dev-godot-ui-spec" / "SKILL.md"
DESIGN_PATH = SKILL_ROOT.parents[2] / "docs/design/development/dev-godot-skills-design.md"
GODOT_EXE = r"D:\workspace\STM-Godot\godot-client-template\godot.exe"
REFERENCE_NAMES = (
    "feature-tree.md",
    "feature-spec-template.md",
    "module-lifecycle-pattern.md",
    "network-patterns.md",
    "ui-patterns.md",
    "optional-dependency-patterns.md",
    "validation-checklist.md",
)


class SkillPackageTests(unittest.TestCase):
    def _skill_text(self) -> str:
        return SKILL_PATH.read_text(encoding="utf-8")

    def _reference_text(self, name: str) -> str:
        return (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")

    def _baseline_text(self) -> str:
        return BASELINE_PATH.read_text(encoding="utf-8")

    def _ui_scene_patterns_text(self) -> str:
        return UI_SCENE_PATTERNS_PATH.read_text(encoding="utf-8")

    def _canonical_contract_text(self) -> str:
        parts = [self._skill_text()]
        parts.extend(self._reference_text(name) for name in REFERENCE_NAMES)
        parts.append(UI_SKILL_PATH.read_text(encoding="utf-8"))
        parts.append(self._ui_scene_patterns_text())
        return "\n".join(parts)

    def _registry_paths(self, text: str) -> set[str]:
        return set(
            re.findall(
                r"(?<![A-Za-z0-9_./\\:<>&-])"
                r"([A-Za-z0-9_./\\:<>-]*game_feature_registry\.gd)",
                text,
            )
        )

    def test_skill_frontmatter_and_name_are_valid(self) -> None:
        text = self._skill_text()
        match = re.match(r"^---\n(?P<frontmatter>.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match, "SKILL.md must begin with YAML frontmatter")
        frontmatter = match.group("frontmatter") if match else ""
        self.assertIn("name: dev-godot-feature", frontmatter)
        for term in ("creating", "Godot", "feature"):
            self.assertIn(term, frontmatter)
        self.assertRegex(text, r"\bcreate\b")
        self.assertRegex(text, r"\bupdate\b")

    def test_skill_is_at_most_one_hundred_lines(self) -> None:
        self.assertTrue(1 <= len(self._skill_text().splitlines()) <= 100)

    def test_every_required_reference_exists_and_is_linked(self) -> None:
        skill_text = self._skill_text()
        for name in REFERENCE_NAMES:
            with self.subTest(reference=name):
                self.assertTrue((SKILL_ROOT / "references" / name).is_file())
                self.assertIn("(references/%s)" % name, skill_text)

    def test_references_do_not_link_to_a_second_reference_level(self) -> None:
        link_pattern = re.compile(r"\]\(([^)]+)\)")
        for name in REFERENCE_NAMES:
            with self.subTest(reference=name):
                for target in link_pattern.findall(self._reference_text(name)):
                    self.assertFalse(target.startswith(("references/", "../references/")), target)

    def test_skill_requires_foundation_validator_and_gut_gate(self) -> None:
        text = self._skill_text()
        self.assertIn("runtime APIs", text)
        self.assertIn("scripts/validate_feature.py", text)
        self.assertIn("targeted GUT", text)
        self.assertLess(text.index("runtime APIs"), text.index("scripts/validate_feature.py"))

    def test_ui_scope_requires_docs_only_ui_spec_handoff(self) -> None:
        text = self._skill_text()
        self.assertIn("dev-godot-ui-spec", text)
        self.assertRegex(text, r"(?is)Phase A.*docs-only.*A2.*approval.*Phase B")

    def test_phase_a_outputs_use_vietnamese_with_diacritics_and_preserve_machine_schema(self) -> None:
        text = self._skill_text()
        phase_a = text.split("## Phase A", 1)[1].split("## Existing-feature", 1)[0]

        self.assertIn("natural Vietnamese with full diacritics", phase_a)
        self.assertIn("tiếng Việt có dấu", phase_a)
        for artifact in (
            "design/<feature_id>-design.md",
            "spec/<feature_id>-spec.md",
            "dev-status.md",
            "plans/<YYYY-MM-DD>-<feature_id>-plan.md",
        ):
            with self.subTest(artifact=artifact):
                self.assertIn(artifact, phase_a)

        self.assertRegex(phase_a, r"(?is)user-facing.*(?:summaries|summary).*approval questions")
        for preserved_term in (
            "canonical machine-readable Markdown section names and table headers",
            "English",
            "technical identifiers",
            "class names",
            "packet classes/fields",
            "JSON keys",
            "code blocks",
            "CLI commands",
        ):
            with self.subTest(preserved_term=preserved_term):
                self.assertIn(preserved_term, phase_a)

    def test_ui_spec_package_is_linked_and_docs_only(self) -> None:
        ui_skill = SKILL_ROOT.parent / "dev-godot-ui-spec" / "SKILL.md"
        text = ui_skill.read_text(encoding="utf-8")
        self.assertIn("references/ui-scene-tree-patterns.md", text)
        self.assertRegex(text, r"(?is)docs-only.*never.*\.tscn.*approval")

    def test_ui_scene_examples_use_canonical_node_prefixes(self) -> None:
        patterns_text = self._ui_scene_patterns_text()
        self.assertIn("## Full screen", patterns_text)
        control_patterns = patterns_text.split("## Full screen", 1)[1]
        text_blocks = re.findall(
            r"```text\n(?P<tree>.*?)\n```",
            control_patterns,
            re.DOTALL,
        )
        node_names = []
        for block in text_blocks:
            for line in block.splitlines():
                match = re.match(r"^[\s│├└─]*([A-Za-z][A-Za-z0-9]*)\s+\(", line)
                if match:
                    node_names.append(match.group(1))

        self.assertTrue(node_names, "expected node examples in UI scene-tree patterns")
        invalid_names = [
            name
            for name in node_names
            if not name.startswith(("image", "btn", "label", "text"))
        ]
        self.assertEqual([], invalid_names)

    def test_ui_scene_patterns_allow_non_control_world_pairs(self) -> None:
        text = self._ui_scene_patterns_text()
        self.assertIn("## Non-`Control` world and render scene", text)
        self.assertRegex(text, r"RoomBattleWorld \(Node2D; .* extends Node2D\)")
        self.assertIn("folder", text.casefold())
        self.assertIn("inheritance", text.casefold())

    def test_ui_file_examples_keep_feature_prefix_and_matching_class_name(self) -> None:
        rows = re.findall(
            r"(?m)^\| `(?P<feature_id>[a-z][a-z0-9_]*)` "
            r"\| `(?P<scene>[a-z][a-z0-9_]*\.tscn)` "
            r"\| `(?P<script>[a-z][a-z0-9_]*\.gd)` "
            r"\| `(?P<class_name>[A-Z][A-Za-z0-9]*)` \|$",
            self._ui_scene_patterns_text(),
        )
        self.assertGreaterEqual(len(rows), 3, "expected single- and multiword feature examples")

        for feature_id, scene, script, class_name in rows:
            with self.subTest(scene=scene):
                scene_stem = Path(scene).stem
                self.assertEqual(scene_stem, Path(script).stem)
                self.assertTrue(scene_stem.startswith(feature_id + "_"))
                expected_class = "".join(
                    part.capitalize() for part in scene_stem.split("_")
                )
                self.assertEqual(expected_class, class_name)

    def test_feature_source_root_is_explicit_flexible_and_globally_registered(self) -> None:
        skill = self._skill_text()
        tree = self._reference_text("feature-tree.md")
        template = self._reference_text("feature-spec-template.md")
        canonical = self._canonical_contract_text()

        self.assertIn(
            "| Source root | modules/game/event/<feature_id> |",
            template,
        )
        self.assertRegex(
            skill,
            r"(?is)A0.{0,220}(?:exact|approved) source root",
        )
        self.assertRegex(
            skill,
            r"(?is)A2.{0,500}(?:record|write).{0,100}(?:exact|approved) source root",
        )
        self.assertEqual(
            {"modules/game/game_feature_registry.gd"},
            self._registry_paths(canonical),
        )
        self.assertIn("modules/game/room/room_module.gd", tree)
        self.assertIn(
            "modules/game/event/offer_dynamic/offer_dynamic_module.gd",
            tree,
        )
        self.assertRegex(
            tree,
            r"(?is)modules/game/features/<feature_id>.{0,160}optional",
        )

    def test_feature_local_paths_follow_the_approved_source_root(self) -> None:
        canonical = self._canonical_contract_text()
        tree = self._reference_text("feature-tree.md")
        template = self._reference_text("feature-spec-template.md")
        validation = self._reference_text("validation-checklist.md")
        ui_skill = UI_SKILL_PATH.read_text(encoding="utf-8")
        ui_patterns = self._ui_scene_patterns_text()

        self.assertRegex(
            template,
            r"(?is)project-relative.{0,160}(?:without|no).{0,40}`res://`"
            r".{0,200}(?:leaf|final) segment.{0,80}(?:equals|matches).{0,40}`feature_id`",
        )
        for suffix in (
            "/<feature_id>_module.gd",
            "/logic/",
            "/network/",
            "/config/",
            "/ui/",
        ):
            with self.subTest(suffix=suffix):
                self.assertIn("<source_root>" + suffix, canonical)
        self.assertIn("modules/game/event/sample_event", tree)
        self.assertNotIn("modules/game/features/sample_event", canonical)
        self.assertIn(
            "res://<source_root>/ui/<feature_id>_<surface_role>.tscn",
            template,
        )
        self.assertIn(
            "res://<source_root>/ui/lobby/<feature_id>_lobby_icon.tscn",
            template,
        )
        for text in (ui_skill, ui_patterns):
            self.assertIn("Source root", text)
            self.assertIn("<source_root>/ui/", text)
            self.assertRegex(
                text,
                r"(?is)(?:complete|same-stem).{0,100}(?:pair|\.tscn.{0,40}\.gd).{0,180}(?:lobby|popup|functional)",
            )
        self.assertRegex(
            validation,
            r"(?is)<source_root>.{0,160}copied exactly.{0,100}approved spec.{0,100}(?:no|without).{0,40}`res://`",
        )

    def test_source_root_contract_rejects_noncanonical_path_forms(self) -> None:
        skill = self._skill_text()
        template = self._reference_text("feature-spec-template.md")
        tree = self._reference_text("feature-tree.md")
        canonical = "\n".join((skill, template, tree))

        self.assertIn("Every source-root segment uses `snake_case`", canonical)
        self.assertIn("project-relative under `modules/game/`", canonical)
        self.assertRegex(
            canonical,
            r"(?is)(?:forbid|must not|never|has no).{0,100}`res://`"
            r".{0,100}drive-qualified.{0,100}backslash",
        )
        self.assertRegex(
            canonical,
            r"(?is)(?:forbid|must not|never|has no).{0,220}`\.`.{0,60}`\.\.`.{0,80}(?:segment|component)",
        )
        self.assertRegex(
            canonical,
            r"(?is)(?:final|last|leaf) segment.{0,60}(?:equals|matches).{0,40}`feature_id`",
        )

    def test_existing_updates_require_contract_delta_and_documentation_resolution(self) -> None:
        text = self._skill_text()
        template = self._reference_text("feature-spec-template.md")
        route = text.split("## Route and audit", 1)[1].split("## Phase A", 1)[0]
        self.assertRegex(
            text,
            r"(?is)before editing.*update.*added.*changed.*removed.*public API.*caller.*default.*migration",
        )
        self.assertRegex(
            route,
            r"(?is)(?:missing|stale).*docs.*return.*Phase A.*(?:end the turn|stop).*wait.*explicit.*approval",
        )
        self.assertIn("## Existing update record", template)
        self.assertIn("### Schema/API delta", template)

    def test_runtime_supporting_skills_are_invoked_only_in_phase_b(self) -> None:
        text = self._skill_text()
        phase_a = text.split("## Phase A", 1)[1].split("## Existing-feature", 1)[0]
        phase_b = text.split("## Phase B", 1)[1].split("## Completion gates", 1)[0]
        self.assertRegex(phase_a, r"(?is)A2.*config.*mocks")
        self.assertRegex(phase_b, r"(?is)begin only after.*approved")
        for supporting_skill in ("dev-godot-config", "dev-godot-mock"):
            with self.subTest(supporting_skill=supporting_skill):
                self.assertNotIn(supporting_skill, phase_a)
                self.assertIn(supporting_skill, phase_b)

    def test_complete_example_includes_all_phase_a_documents(self) -> None:
        tree = self._reference_text("feature-tree.md")
        example = tree.split("## Complete small example", 1)[1]
        for path in (
            "docs/modules/sample_event/design/sample_event-design.md",
            "docs/modules/sample_event/spec/sample_event-spec.md",
            "docs/modules/sample_event/dev-status.md",
        ):
            with self.subTest(path=path):
                self.assertIn(path, example)
        self.assertRegex(
            example,
            r"docs/modules/sample_event/plans/\d{4}-\d{2}-\d{2}-sample_event-plan\.md",
        )

    def test_spec_template_uses_canonical_contract_tables(self) -> None:
        template = self._reference_text("feature-spec-template.md")
        self.assertIn("## Status", template)
        self.assertIn("## Command ownership", template)
        self.assertIn("## Optional actions", template)
        self.assertIn("## Optional queries", template)
        self.assertIn("## UI and assets", template)
        self.assertNotRegex(template, r"(?m)^Activation:")
        self.assertNotIn("Owned server-push commands:", template)

    def test_cocos_runtime_patterns_are_not_prescribed(self) -> None:
        rejected = (
            "project.json",
            "onGameMessage",
            "ModuleMgr.broadcast",
            "BaseModule.extend",
            "direct global util access",
            "cc.eventManager",
        )
        for name in REFERENCE_NAMES:
            text = self._reference_text(name)
            for token in rejected:
                with self.subTest(reference=name, token=token):
                    for line in text.splitlines():
                        if token in line:
                            self.assertIn("Legacy rejection", line)

    def test_pool_function_is_limited_to_optional_boundaries(self) -> None:
        optional_text = self._reference_text("optional-dependency-patterns.md")
        for token in (
            "PoolFunction.reg_func",
            "PoolFunction.do_func",
            "PoolFunction.remove_all",
            "DEFAULT_",
        ):
            self.assertIn(token, optional_text)
        lifecycle_text = self._reference_text("module-lifecycle-pattern.md")
        self.assertIn("PoolFunction.remove_all(self)", lifecycle_text)
        self.assertNotIn("PoolFunction.reg_func", lifecycle_text)
        self.assertNotIn("PoolFunction.do_func", lifecycle_text)
        self.assertNotIn("PoolFunction", self._reference_text("ui-patterns.md"))

    def test_validation_commands_pin_the_project_godot_executable(self) -> None:
        text = self._reference_text("validation-checklist.md")
        self.assertIn(
            "& '%s' --headless --path . -s addons/gut/gut_cmdln.gd "
            "-gdir=res://tests/unit/features/<feature_id> -gexit -gconfig=" % GODOT_EXE,
            text,
        )
        self.assertIn(
            "& '%s' --headless --path . -s addons/gut/gut_cmdln.gd "
            "-gdir=res://tests -gexit -gconfig=" % GODOT_EXE,
            text,
        )

    def test_completion_gate_invokes_validator_with_required_cli_contract(self) -> None:
        text = self._skill_text()
        commands = [line for line in text.splitlines() if "`python " in line and "validate_feature.py" in line]
        self.assertEqual(len(commands), 1, commands)
        command = commands[0]
        for required_arg in ("--project-root .", "--feature-id", "--spec"):
            self.assertIn(required_arg, command)
        self.assertIn("exit 0", command)

    def test_every_green_records_full_targeted_godot_command_and_non_pass(self) -> None:
        text = self._baseline_text()
        targets = {
            "eager_request_response": "features/sample_event",
            "server_push_vs_lazy": "features/sample_push",
            "lazy_ui_only": "features/sample_help",
            "optional_command_query": "features",
            "optional_provider_removed": "features/feature_b",
            "supporting_skill_handoff": "features/sample_event",
            "existing_feature_update": "features/login",
        }
        for scenario, target in targets.items():
            with self.subTest(scenario=scenario):
                match = re.search(
                    r"(?ms)^## %s\n.*?^### GREEN\n(?P<green>.*?)(?=^## )"
                    % re.escape(scenario),
                    text,
                )
                self.assertIsNotNone(match, "missing GREEN for %s" % scenario)
                green = match.group("green") if match else ""
                command = (
                    "& '%s' --headless --path . -s addons/gut/gut_cmdln.gd "
                    "-gdir=res://tests/unit/%s -gexit -gconfig=" % (GODOT_EXE, target)
                )
                self.assertIn(command, green)
                self.assertIn("signal 11", green)
                self.assertIn("not a suite pass", green)

    def test_module_uses_direct_network_service_and_explicit_composition_root(self) -> None:
        text = self._reference_text("module-lifecycle-pattern.md")
        self.assertNotRegex(text, r"var\s+_network_service\s*:\s*Node\s*=\s*NetworkService")
        self.assertIn("NetworkService.subscribe", text)
        self.assertIn("NetworkService.send_packet", text)
        self.assertIn("ModuleMgr.register_factory(", text)
        self.assertIn("ModuleMgr.open_module(SampleEventModule.MODULE_ID)", text)
        self.assertIn("ModuleMgr.get_module(ProfileModule.MODULE_ID) as ProfileModule", text)
        self.assertNotIn('ModuleMgr.open_module(&"profile")', text)

    def test_optional_boundary_contract_survives_provider_removal(self) -> None:
        text = self._reference_text("optional-dependency-patterns.md")
        self.assertIn("modules/game/contracts/sample_event_optional_boundary.gd", text)
        self.assertIn("class_name SampleEventOptionalBoundary", text)
        self.assertIn("SampleEventOptionalBoundary.OPEN_RELATED", text)
        self.assertIn("SampleEventOptionalBoundary.DEFAULT_OPEN_RELATED", text)
        self.assertNotIn("SampleEventRelatedProvider.OPEN_RELATED", text)
        runtime_block = text.split("## Provider implementation", 1)[1].split("## Consumer call", 1)[0]
        self.assertNotIn("assert_eq", runtime_block)
        self.assertIn("extends BaseModule", runtime_block)
        self.assertNotIn("extends RefCounted", runtime_block)
        self.assertIn("const MODULE_ID", runtime_block)
        self.assertIn("ModuleMgr.register_factory", runtime_block)
        self.assertIn("ModuleMgr.close_module", text)
        self.assertIn("NetworkService.unsubscribe_all(self)", runtime_block)
        self.assertIn("PoolFunction.remove_all(self)", runtime_block)

    def test_optional_constants_are_owned_only_by_retained_neutral_boundaries(self) -> None:
        optional = self._reference_text("optional-dependency-patterns.md")
        template = self._reference_text("feature-spec-template.md")
        design = DESIGN_PATH.read_text(encoding="utf-8")
        canonical = "\n".join((optional, template, design))

        self.assertIn("<Feature>OptionalBoundary.<ACTION>", template)
        self.assertIn("<Feature>OptionalBoundary.DEFAULT_<ACTION>", template)
        self.assertRegex(
            design,
            r"(?is)retained neutral optional-boundary contract.{0,220}authoritative.{0,220}PoolFunction.{0,120}(?:registry|dispatcher)",
        )
        self.assertNotIn("PoolFunction.{FEATURE}_{ACTION}", design)
        self.assertNotRegex(canonical, r"PoolFunction\.SAMPLE_EVENT_[A-Z0-9_]+")

    def test_config_class_names_use_json_acronym_with_snake_case_files(self) -> None:
        template = self._reference_text("feature-spec-template.md")
        validation = self._reference_text("validation-checklist.md")
        design = DESIGN_PATH.read_text(encoding="utf-8")
        canonical = "\n".join((template, validation, design))

        self.assertIn("<feature_id>_json_config.gd", template)
        self.assertIn("<Feature>JSONConfig", template)
        self.assertIn("<FeatureId>JSONConfig", validation)
        self.assertNotRegex(canonical, r"\b(?:<Feature>|<FeatureId>|SampleEvent)JsonConfig\b")

    def test_network_spy_test_preloads_and_always_restores_transport(self) -> None:
        text = self._reference_text("network-patterns.md")
        self.assertIn('preload("res://tests/system/helpers/spy_net_client.gd")', text)
        self.assertIn("func before_each() -> void:", text)
        self.assertIn("func after_each() -> void:", text)
        self.assertIn("NetworkService._connection = _old_connection", text)
        self.assertIn("test_recv_load_info_parses_success_payload", text)

    def test_lazy_ui_scenario_uses_unified_base_contract(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "tests" / "scenarios.json").read_text(encoding="utf-8")
        )
        scenario = next(item for item in payload["scenarios"] if item["id"] == "lazy_ui_only")
        self.assertEqual(
            scenario["must"],
            [
                "lazy factory only",
                "all UI extends BaseScreen",
                "subclass-owned presentation and manual fog",
                "no NetworkService subscription",
            ],
        )


if __name__ == "__main__":
    unittest.main()
