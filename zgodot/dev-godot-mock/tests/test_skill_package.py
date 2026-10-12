"""Deterministic contract for the dev-godot-mock instruction package."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
SKILL_PATH = PACKAGE_DIR / "SKILL.md"
REFERENCE_PATHS = {
    "runtime": "references/mock-runtime-pattern.md",
    "config": "references/mock-current-template.json",
    "matrix": "references/scenario-matrix-template.md",
    "packaging": "references/packaging-checklist.md",
}


class SkillPackageTests(unittest.TestCase):
    """Reject a package that cannot instruct the required safe mock workflow."""

    def _skill_source(self) -> str:
        self.assertTrue(SKILL_PATH.is_file(), "SKILL.md must exist")
        return SKILL_PATH.read_text(encoding="utf-8")

    def _reference_source(self, reference_id: str) -> str:
        relative_path = REFERENCE_PATHS[reference_id]
        reference_path = PACKAGE_DIR / relative_path
        self.assertTrue(reference_path.is_file(), f"reference must exist: {relative_path}")
        return reference_path.read_text(encoding="utf-8")

    def _section(self, source: str, heading_pattern: str) -> str:
        match = re.search(
            rf"(?ims)^##+[^\n]*{heading_pattern}[^\n]*\n(.*?)(?=^##+\s|\Z)",
            source,
        )
        self.assertIsNotNone(match, f"missing bounded section: {heading_pattern}")
        return match.group(1)

    def _assert_ordered(self, source: str, *patterns: str) -> None:
        cursor = 0
        for pattern in patterns:
            match = re.search(pattern, source[cursor:], re.IGNORECASE | re.DOTALL)
            self.assertIsNotNone(match, f"missing ordered requirement: {pattern}")
            cursor += match.end()

    def _assert_forbidden_instruction(self, source: str, target_pattern: str) -> None:
        self.assertRegex(
            source,
            rf"(?is)\b(?:do not|never|must not|forbid\w*)\b[^\n.]{{0,180}}{target_pattern}",
            f"missing normative prohibition for: {target_pattern}",
        )

    def _assert_route_contract(self, route: str) -> None:
        inspection = re.search(
            r"(?im)^\s*(?:[-*]|\d+\.)?\s*(?:read|inspect|audit|trace)\b[^\n]{0,360}$",
            route,
        )
        self.assertIsNotNone(inspection, "route must include an imperative inspection instruction")
        inspection_line = inspection.group(0)
        for target in ("feature", "spec", "module", "receive", "UI", "test"):
            self.assertRegex(inspection_line, rf"(?i)\b{target}\w*\b", f"inspection must cover {target}")

        confirmation = re.search(
            r"(?im)^\s*(?:[-*]|\d+\.)?\s*(?:confirm|ask for confirmation)\b[^\n]*\bscenario matrix\b[^\n]*$",
            route[inspection.end():],
        )
        self.assertIsNotNone(
            confirmation,
            "route must confirm the scenario matrix after inspection",
        )

    def _has_affirmative_requirement_line(self, source: str, *patterns: str) -> bool:
        affirmative = re.compile(
            r"\b(?:must|should|always|require|ensure|synchroniz\w*|check|verify)\b",
            re.IGNORECASE,
        )
        negation = re.compile(
            r"\b(?:not|never|without|do not|must not)\b|\bno\b(?![- ]op\b)",
            re.IGNORECASE,
        )
        return any(
            affirmative.search(line)
            and not negation.search(line)
            and all(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)
            for line in source.splitlines()
        )

    def _assert_affirmative_guard_line(self, source: str, subject: str) -> None:
        guard = r"(?:gc\.SERVER_ID\s*==\s*GameEnvironment\.SERVER_ID_DEV|DEV guard)"
        affirmative = r"\b(?:must|should|always|require|ensure|check|verify)\b"
        negation = r"\b(?:not|never|without|do not|must not)\b|\bno\b(?![- ]op\b)"
        candidate_lines = [
            line
            for line in source.splitlines()
            if re.search(subject, line, re.IGNORECASE)
            and re.search(guard, line, re.IGNORECASE)
            and re.search(affirmative, line, re.IGNORECASE)
            and not re.search(negation, line, re.IGNORECASE)
        ]
        other_subject = r"NetworkService\.dispatch_mock_packet" if subject == r"mock loader" else r"mock loader"
        bound_lines = [line for line in candidate_lines if not re.search(other_subject, line, re.IGNORECASE)]
        self.assertTrue(bound_lines, f"{subject} needs a subject-bound DEV guard line")

    def test_frontmatter_names_a_create_and_update_godot_mock_skill(self) -> None:
        source = self._skill_source()
        self.assertRegex(source, r"(?s)^---\s*\nname:\s*dev-godot-mock\s*\n")
        frontmatter = source.split("---", 2)[1]
        self.assertRegex(frontmatter, r"(?i)description:.*\bcreat\w*")
        self.assertRegex(frontmatter, r"(?i)description:.*\bupdat\w*")
        self.assertRegex(frontmatter, r"(?i)description:.*\bGodot\b")
        self.assertRegex(frontmatter, r"(?i)description:.*\b(interactive )?mock")

    def test_skill_is_concise_and_links_the_complete_file_map(self) -> None:
        source = self._skill_source()
        self.assertGreaterEqual(len(source.splitlines()), 1)
        self.assertLessEqual(len(source.splitlines()), 100)
        for relative_path in REFERENCE_PATHS.values():
            self.assertTrue((PACKAGE_DIR / relative_path).is_file(), f"missing File Map reference: {relative_path}")
            self.assertRegex(source, re.escape("(" + relative_path + ")"), f"SKILL.md must link {relative_path}")

    def test_create_route_inspects_before_confirming_the_scenario_matrix(self) -> None:
        with self.assertRaises(AssertionError):
            self._assert_route_contract("feature spec module receive UI tests scenario matrix confirm")
        create_route = self._section(self._skill_source(), r"\bcreate\b")
        self._assert_route_contract(create_route)

    def test_update_route_inspects_before_confirming_the_scenario_matrix(self) -> None:
        with self.assertRaises(AssertionError):
            self._assert_route_contract(
                "- Confirm the scenario matrix.\n- Inspect feature spec module receive UI tests."
            )
        update_route = self._section(self._skill_source(), r"\bupdate\b")
        self._assert_route_contract(update_route)

    def test_safety_section_prohibits_the_three_unsafe_shortcuts(self) -> None:
        with self.assertRaises(AssertionError):
            self._assert_forbidden_instruction(
                "direct util/model mutation; production preload devtools; literal load devtools; silent socket interception",
                r"direct util/model mutation",
            )
        safety = self._section(self._skill_source(), r"\bsafety\b")
        self._assert_forbidden_instruction(safety, r"(?:direct util/model mutation|mutat\w*[^\n.]*util/model[^\n.]*direct)")
        self._assert_forbidden_instruction(safety, r"(?:production[^\n.]*preload|preload[^\n.]*production)[^\n.]*devtools")
        self._assert_forbidden_instruction(safety, r"literal load[^\n.]*devtools")
        self._assert_forbidden_instruction(safety, r"silent socket interception")

    def test_safe_optional_feature_section_defines_commands_queries_and_defaults(self) -> None:
        with self.assertRaises(AssertionError):
            self.assertTrue(
                self._has_affirmative_requirement_line(
                    "Optional command has a safe no-op when no provider exists.",
                    r"PoolFunction\.do_func",
                    r"optional.{0,40}command|command.{0,40}optional",
                    r"(?:missing|absent).{0,40}(?:provider|handler)",
                    r"safe.{0,40}no[- ]?op",
                )
            )
        with self.assertRaises(AssertionError):
            self.assertTrue(
                self._has_affirmative_requirement_line(
                    "Do not give an optional query an explicit meaningful default.",
                    r"optional.{0,40}quer(?:y|ies)|quer(?:y|ies).{0,40}optional",
                    r"(?:explicit|defined).{0,80}(?:meaningful|safe).{0,80}(?:default|value)",
                )
            )
        with self.assertRaises(AssertionError):
            self.assertTrue(
                self._has_affirmative_requirement_line(
                    "Never call PoolFunction.do_func for an optional command with an absent provider; safe no-op.",
                    r"PoolFunction\.do_func",
                    r"optional.{0,40}command|command.{0,40}optional",
                    r"(?:missing|absent).{0,40}(?:provider|handler)",
                    r"safe.{0,40}no[- ]?op",
                )
            )
        optional = self._section(self._skill_source(), r"\boptional\b")
        self.assertTrue(
            self._has_affirmative_requirement_line(
                optional,
                r"PoolFunction\.do_func",
                r"optional.{0,40}command|command.{0,40}optional",
                r"(?:missing|absent).{0,40}(?:provider|handler)",
                r"safe.{0,40}no[- ]?op",
            ),
            "optional commands require a local PoolFunction.do_func no-provider safe-no-op rule",
        )
        self.assertTrue(
            self._has_affirmative_requirement_line(
                optional,
                r"optional.{0,40}quer(?:y|ies)|quer(?:y|ies).{0,40}optional",
                r"(?:explicit|defined).{0,80}(?:meaningful|safe).{0,80}(?:default|value)",
            ),
            "optional queries require a local explicit meaningful default rule",
        )

    def test_runtime_reference_uses_the_production_dispatch_and_action_apis(self) -> None:
        runtime = self._reference_source("runtime")
        for api in (
            "NetworkService.dispatch_mock_packet",
            "CheatInput._run_dev_mock",
            "PoolFunction.do_func",
        ):
            self.assertIn(api, runtime, f"runtime pattern must use {api}")

    def test_runtime_reference_uses_retained_optional_boundary_constants(self) -> None:
        runtime = self._reference_source("runtime")
        for token in (
            "SampleEventOptionalBoundary.SHOW_MAIN",
            "SampleEventOptionalBoundary.DEFAULT_SHOW_MAIN",
            "SampleEventOptionalBoundary.SHOW_POPUP",
            "SampleEventOptionalBoundary.DEFAULT_SHOW_POPUP",
        ):
            self.assertIn(token, runtime)
        self.assertNotRegex(runtime, r"PoolFunction\.SAMPLE_EVENT_[A-Z0-9_]+")

    def test_error_case_dispatches_to_handler_then_returns_without_ui(self) -> None:
        runtime = self._reference_source("runtime")
        run_match = re.search(
            r"(?ms)^func run\([^\n]*\) -> Error:\n(.*?)(?=^func apply_case)",
            runtime,
        )
        self.assertIsNotNone(run_match, "runtime example needs a complete run function")
        self._assert_ordered(
            run_match.group(1),
            r"delivery_error\s*:=\s*apply_case",
            r"delivery_error\s*!=\s*OK",
            r"case_id\s*==\s*&\"error\"",
            r"return\s+OK",
            r"return\s+run_flow",
        )
        apply_match = re.search(
            r"(?ms)^func apply_case\([^\n]*\) -> Error:\n(.*?)(?=^func run_flow)",
            runtime,
        )
        self.assertIsNotNone(apply_match, "runtime example needs a complete apply_case function")
        self._assert_ordered(
            apply_match.group(1),
            r"packet\.error_code\s*=.*case_id\s*==\s*&\"error\"",
            r"NetworkService\.dispatch_mock_packet\(packet\)",
        )

        matrix = self._reference_source("matrix")
        error_row = next(
            (line for line in matrix.splitlines() if re.match(r"^\|\s*`error`\s*\|", line)),
            None,
        )
        self.assertIsNotNone(error_row, "scenario matrix needs an error row")
        cells = [cell.strip().lower() for cell in error_row.strip().strip("|").split("|")]
        self.assertGreaterEqual(len(cells), 5, "error row must include state and UI cells")
        self.assertRegex(cells[3], r"production.*handler.*(?:handle|report).*error")
        self.assertEqual(cells[4], "ui does not open")

    def test_config_reference_is_valid_editable_reloadable_mock_current_json(self) -> None:
        config = json.loads(self._reference_source("config"))
        self.assertEqual(config["feature"], "sample_event")
        self.assertIn(config["caseId"], config["_validCases"])
        self.assertIn(config["flowId"], config["_validFlows"])
        self.assertIsInstance(config["options"], dict)
        self.assertIn("save", config["_help"].lower())
        self.assertRegex(config["_help"], r"(?i)(press|trigger).*(dev|key)")

    def test_scenario_matrix_reference_has_each_required_verification_column(self) -> None:
        matrix = self._reference_source("matrix")
        for column in (
            "case ID",
            "typed packet/state input",
            "flow ID",
            "expected module signals/state",
            "expected UI",
            "manual verification",
            "automated codec counterpart",
            "documented client-only exception",
        ):
            self.assertIn(column.lower(), matrix.lower(), f"scenario matrix column missing: {column}")

    def test_packaging_reference_requires_independent_guards_and_delivery_checks(self) -> None:
        with self.assertRaises(AssertionError):
            self._assert_affirmative_guard_line(
                "Mock loader and NetworkService.dispatch_mock_packet use a DEV guard.",
                r"mock loader",
            )
        with self.assertRaises(AssertionError):
            self._assert_affirmative_guard_line("Mock loader has no DEV guard.", r"mock loader")
        with self.assertRaises(AssertionError):
            self._assert_affirmative_guard_line(
                "NetworkService.dispatch_mock_packet must not use a DEV guard.",
                r"NetworkService\.dispatch_mock_packet",
            )
        packaging = self._reference_source("packaging")
        self._assert_affirmative_guard_line(packaging, r"mock loader")
        self._assert_affirmative_guard_line(packaging, r"NetworkService\.dispatch_mock_packet")
        self._assert_ordered(packaging, r"JSON", r"re-read")
        self._assert_ordered(packaging, r"Android", r"iOS", r"export")
        self._assert_ordered(packaging, r"malformed", r"unknown")
        self.assertIn("targeted GUT", packaging)

    def test_packaging_reference_has_copy_pasteable_powershell_gut_commands(self) -> None:
        packaging = self._reference_source("packaging")
        command_match = re.search(r"(?ms)^```powershell\s*\n(.*?)^```\s*$", packaging)
        self.assertIsNotNone(command_match, "packaging needs a PowerShell command block")
        commands = command_match.group(1)
        for token in (
            "$godotExe",
            "$featureMockTest",
            "$featureHandlerTest",
            "--import",
            "Start-Process",
            "res://tests/unit/test_dev_mock_loader.gd",
            "res://tests/unit/test_cheat_input.gd",
            "res://tests/unit/test_devtools_packaging.gd",
            "Run Summary",
            "All tests passed",
            "ExitCode",
        ):
            self.assertIn(token, commands, f"packaging command contract missing: {token}")
        self.assertRegex(
            commands,
            r"Start-Process\s+-FilePath\s+\$godotExe[\s\S]*?'--import'",
        )
        for invocation in (
            r"Invoke-GutTestFile\s+\$featureMockTest",
            r"Invoke-GutTestFile\s+\$featureHandlerTest",
            r"Invoke-GutTestFile\s+'res://tests/unit/test_dev_mock_loader\.gd'",
            r"Invoke-GutTestFile\s+'res://tests/unit/test_cheat_input\.gd'",
            r"Invoke-GutTestFile\s+'res://tests/unit/test_devtools_packaging\.gd'",
        ):
            self.assertRegex(commands, invocation)

    def test_packaging_reference_names_every_synchronized_artifact(self) -> None:
        with self.assertRaises(AssertionError):
            self.assertTrue(
                self._has_affirmative_requirement_line(
                    "Never synchronize runtime, JSON, docs, loader, and Cheat.",
                    r"synchron",
                    r"\bruntime\b",
                    r"\bJSON\b",
                    r"\bdocs\b",
                    r"\bloader\b",
                    r"\bCheat\b",
                )
            )
        synchronization = self._section(self._reference_source("packaging"), r"\bsynchronization\b")
        self.assertTrue(
            self._has_affirmative_requirement_line(
                synchronization,
                r"synchron",
                r"\bruntime\b",
                r"\bJSON\b",
                r"\bdocs\b",
                r"\bloader\b",
                r"\bCheat\b",
            ),
            "synchronization requires one explicit normative five-artifact instruction",
        )


if __name__ == "__main__":
    unittest.main()
