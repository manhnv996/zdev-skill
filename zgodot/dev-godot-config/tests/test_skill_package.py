"""Deterministic contract for the dev-godot-config skill package."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_PATH = SKILL_DIR / "SKILL.md"
REFERENCE_NAMES = (
    "json-config-pattern.md",
    "schema-diff-workflow.md",
    "config-test-pattern.md",
)


def read_text(path: Path) -> str:
	return path.read_text(encoding="utf-8") if path.exists() else ""


class SkillPackageTests(unittest.TestCase):
	def _skill_text(self) -> str:
		return read_text(SKILL_PATH)

	def _reference_text(self, name: str) -> str:
		return read_text(SKILL_DIR / "references" / name)

	def _package_text(self) -> str:
		parts = [self._skill_text()]
		parts.extend(self._reference_text(name) for name in REFERENCE_NAMES)
		return "\n".join(parts)

	def _canonical_class_and_bootstrap(self) -> tuple[str, str]:
		pattern_text = self._reference_text("json-config-pattern.md")
		class_match = re.search(
			r"```gdscript[^\n]*\n(?P<class>class_name\s+SampleEventJSONConfig\b.*?)(?:\n)?```",
			pattern_text,
			re.DOTALL,
		)
		self.assertIsNotNone(class_match, "reference must include the canonical config class")
		if class_match is None:
			return "", pattern_text
		bootstrap_text = pattern_text[:class_match.start()] + pattern_text[class_match.end():]
		return class_match.group("class"), bootstrap_text

	def _canonical_region(self, class_text: str, region_name: str) -> str:
		match = re.search(
			rf"(?ms)^#region {re.escape(region_name)}\s*$\n(?P<region>.*?)^#endregion\s*$",
			class_text,
		)
		self.assertIsNotNone(match, f"canonical class must include {region_name} region")
		return match.group("region") if match else ""

	def test_frontmatter_name_and_trigger_description(self) -> None:
		"""Changing the discoverable skill identity must fail this contract."""
		match = re.match(r"^---\s*\n(?P<frontmatter>.*?)\n---\s*\n", self._skill_text(), re.DOTALL)
		self.assertIsNotNone(match, "SKILL.md must start with YAML-style frontmatter")
		frontmatter = match.group("frontmatter") if match else ""
		self.assertIn("name: dev-godot-config", frontmatter)
		description_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
		self.assertIsNotNone(description_match, "frontmatter must declare description")
		description = description_match.group(1) if description_match else ""
		for token in ("creating", "updating", "JSON", "Godot"):
			self.assertIn(token, description)

	def test_skill_is_at_most_one_hundred_lines(self) -> None:
		"""Adding an oversized routing document must fail this contract."""
		line_count = len(self._skill_text().splitlines())
		self.assertGreaterEqual(line_count, 1)
		self.assertLessEqual(line_count, 100)

	def test_all_three_references_exist_and_are_linked(self) -> None:
		"""Removing a required one-level reference must fail this contract."""
		skill_text = self._skill_text()
		for name in REFERENCE_NAMES:
			self.assertTrue((SKILL_DIR / "references" / name).is_file(), name)
			self.assertIn("references/" + name, skill_text)

	def test_skill_has_create_and_update_routes(self) -> None:
		"""Removing the explicit create/update decision must fail this contract."""
		skill_text = self._skill_text()
		create_match = re.search(r"(?mi)^#+\s+Create\b", skill_text)
		update_match = re.search(r"(?mi)^#+\s+Update\b", skill_text)
		audit_match = re.search(r"(?i)existing[- ]file audit", skill_text)
		self.assertIsNotNone(create_match)
		self.assertIsNotNone(update_match)
		self.assertIsNotNone(audit_match)
		audit_index = audit_match.start() if audit_match else -1
		self.assertLess(audit_index, create_match.start() if create_match else -1)
		self.assertLess(audit_index, update_match.start() if update_match else -1)

	def test_skill_forbids_positional_legacy_array_edits(self) -> None:
		"""Allowing feature registration through a legacy list must fail this contract."""
		package_text = self._package_text()
		legacy_lists = (
			"_list_json",
			"_list_skill_json",
			"_list_json_new",
			"_list_json_new2",
			"_list_json_new3",
		)
		prohibition_blocks = re.findall(
			r"(?ims)^(?P<block>(?:(?!\n\s*\n).)*(?:do not|must not|never)\s+append(?:(?!\n\s*\n).)*)",
			package_text,
		)
		self.assertTrue(prohibition_blocks, "package must contain a legacy-array append prohibition")
		self.assertTrue(
			any(all(list_name in block for list_name in legacy_lists) for block in prohibition_blocks),
			"one append-prohibition block must name every legacy positional array",
		)

	def test_skill_keeps_registration_out_of_config_classes(self) -> None:
		"""Putting config paths or registration wrappers in a loader must fail."""
		class_text, bootstrap_text = self._canonical_class_and_bootstrap()
		self.assertNotIn("CONFIG_PATH", class_text)
		self.assertNotIn("static func register_config", class_text)
		self.assertNotIn("ConfigMgr.register_json_file(", class_text)
		self.assertNotIn("get_instance(true).pre_init(", class_text)
		registration_index = bootstrap_text.find("ConfigMgr.register_json_file(")
		pre_init_index = bootstrap_text.find("get_instance(true).pre_init(")
		self.assertNotEqual(registration_index, -1)
		self.assertNotEqual(pre_init_index, -1)
		self.assertLess(registration_index, pre_init_index)

	def test_skill_requires_one_loader_class_per_file(self) -> None:
		"""Distinct schemas stay separate while same-schema sources share a class."""
		pattern_text = self._reference_text("json-config-pattern.md")
		self.assertIn("<feature_id>_json_config.gd", pattern_text)
		self.assertIn("<feature_id>_<domain>_json_config.gd", pattern_text)
		self.assertRegex(pattern_text, r"(?is)forbid.{0,140}multiple independent-schema.{0,140}BaseJSONConfig subclasses.{0,140}one file")
		self.assertRegex(pattern_text, r"(?is)only.{0,100}private record inner classes")

	def test_skill_supports_same_schema_source_families(self) -> None:
		"""A path family must share code without sharing mutable loader state."""
		package_text = self._package_text()
		pattern_text = self._reference_text("json-config-pattern.md")
		for token in (
			"## Same-schema source family",
			"RoomMapJSONConfig.new()",
			"func bind_source(source_id: StringName, relative_path: String) -> Error:",
			"ERR_ALREADY_IN_USE",
			"caller-owned cache",
			"17 JSON files",
			"8 loader scripts",
		):
			self.assertIn(token, pattern_text)
		self.assertRegex(package_text, r"(?is)never.{0,120}(?:retarget|pre_init\(\).{0,40}again)")
		self.assertIn("two instances bind different registered paths", package_text)
		self.assertIn("reset()` on every owned instance", package_text)
		self.assertRegex(pattern_text, r"(?s)func reset\(\) -> void:.{0,80}super\.reset\(\)")

	def test_family_scenario_is_kept(self) -> None:
		"""The forward scenario must continue exercising the new family route."""
		scenarios = read_text(SKILL_DIR / "tests" / "scenarios.json")
		for token in (
			'"id": "same_schema_source_family"',
			'"one map loader script"',
			'"caller-owned keyed cache"',
			'"bind once"',
			'"owner reset"',
		):
			self.assertIn(token, scenarios)

	def test_loader_class_uses_json_acronym_while_file_stays_snake_case(self) -> None:
		"""Changing JSON to title-case Json or camel-casing the file must fail."""
		pattern_text = self._reference_text("json-config-pattern.md")
		self.assertIn("class_name SampleEventJSONConfig", pattern_text)
		self.assertIn("sample_event_json_config.gd", pattern_text)
		self.assertIn("SampleEventInfoJSONConfig", pattern_text)
		self.assertNotRegex(pattern_text, r"\bSampleEvent(?:Info|Reward)?JsonConfig\b")

	def test_skill_preserves_channel_config_method_groups(self) -> None:
		"""Canonical grouping, numeric validation, and internal state must remain safe."""
		class_text, _bootstrap_text = self._canonical_class_and_bootstrap()
		static_text = self._canonical_region(class_text, "Static")
		init_text = self._canonical_region(class_text, "Init")
		self._canonical_region(class_text, "Accessors")
		self.assertEqual(len(re.findall(r"(?m)^\s*static func get_instance\s*\(", static_text)), 1)
		self.assertEqual(len(re.findall(r"(?m)^\s*func init\s*\(", init_text)), 1)
		self.assertEqual(len(re.findall(r"(?m)^\s*func read_config\s*\(", init_text)), 1)
		self.assertEqual(len(re.findall(r"(?m)^\s*static func get_instance\s*\(", class_text)), 1)
		self.assertEqual(len(re.findall(r"(?m)^\s*func init\s*\(", class_text)), 1)
		self.assertEqual(len(re.findall(r"(?m)^\s*func read_config\s*\(", class_text)), 1)
		self.assertLess(class_text.index("#region Static"), class_text.index("#region Init"))
		self.assertLess(class_text.index("#region Init"), class_text.index("#region Accessors"))
		self.assertIn("var _data_config: Dictionary = {}", class_text)
		self.assertNotIn("var data_config", class_text)
		self.assertIn("return is_finite(number) and number == floor(number)", class_text)
		self.assertNotIn(".is_finite()", class_text)
		self.assertNotIn("is_equal_approx(", class_text)
		self.assertIn("func get_tiers() -> Array[Dictionary]:", class_text)
		self.assertIn("return _tiers.duplicate(true)", class_text)

	def test_skill_requires_schema_diff_confirmation_and_gut(self) -> None:
		"""GUT guidance must make isolation, fixtures, and failure behavior executable."""
		package_text = self._package_text()
		self.assertIn("schema diff", package_text)
		self.assertRegex(package_text, r"(?is)(?:remove|removing).{0,120}getter.{0,120}(?:confirm|confirmation)")
		self.assertIn("ConfigMgr.register_json_file", package_text)
		for token in ("--headless", "addons/gut/gut_cmdln.gd", "-gtest="):
			self.assertIn(token, package_text)
		config_tests = self._reference_text("config-test-pattern.md")
		for token in (
			"## Contents",
			"tests/fixtures/config/sample_event/__dev_godot_config_valid.json",
			"tests/fixtures/config/sample_event/__dev_godot_config_no_tiers.json",
			"tests/fixtures/config/sample_event/__dev_godot_config_malformed.json",
			"BaseJSONConfig._instances.duplicate()",
			"BaseJSONConfig._instances = {}",
			"_original_url_skill_json",
			"_original_check_list",
			"OS.get_user_data_dir()",
			"_backup_user_cache",
			"_restore_user_cache",
			"42.0",
			"42.5",
			"INF",
			"-INF",
			"NAN",
			"test_invalid_reload_preserves_prior_typed_and_raw_data",
			"test_optional_default_and_collection_copy",
			"test_successful_server_reload_updates_typed_values_and_clears_marker",
			"test_singleton_reset_returns_distinct_unloaded_instance",
			"__dev_godot_config_",
			"PackedByteArray",
			"get_buffer(file.get_length())",
			"FileAccess.get_open_error()",
			"_prepared_cache_basenames",
			"func _remove_user_cache(basename: String) -> Error:",
			"func _restore_user_cache(basename: String) -> Error:",
			"get_data() is diagnostic/test-only",
		):
			self.assertIn(token, config_tests)
		self.assertNotIn("## GREEN forward tests", self._reference_text("../tests/baseline.md"))

	def test_config_examples_use_approved_feature_source_root(self) -> None:
		"""Deriving config ownership from feature_id must fail this contract."""
		skill_text = self._skill_text()
		json_pattern = self._reference_text("json-config-pattern.md")
		test_pattern = self._reference_text("config-test-pattern.md")
		canonical_text = "\n".join((skill_text, json_pattern, test_pattern))

		self.assertRegex(
			skill_text,
			r"(?is)(?:exact|approved) source root.{0,220}(?:approved feature spec|explicitly supplied config script path)",
		)
		self.assertRegex(
			skill_text,
			r"(?is)never.{0,160}(?:derive|infer).{0,100}(?:runtime folder|source root).{0,80}feature_id",
		)
		self.assertIn("<source_root>/config/", json_pattern)
		self.assertIn(
			'res://<source_root>/config/sample_event_json_config.gd',
			test_pattern,
		)
		self.assertNotIn("modules/game/features/sample_event", canonical_text)


if __name__ == "__main__":
	unittest.main()
