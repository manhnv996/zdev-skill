"""Read-only contract validation for canonical Godot game features."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Sequence


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class CommandContract:
    command_id: str
    direction: str
    packet_class: str
    response_kind: str


@dataclass(frozen=True)
class OptionalContract:
    key: str
    provider_signature: str
    call_arguments: str
    explicit_default: str


FOUNDATION_REQUIREMENTS = (
    (
        "modules/core/base/module/base_module.gd",
        r"(?m)^func\s+on_reset\s*\(",
        "BaseModule.on_reset",
    ),
    (
        "modules/core/managers/module_mgr.gd",
        r"(?m)^static\s+func\s+register_factory\s*\(",
        "ModuleMgr.register_factory",
    ),
    (
        "modules/core/managers/module_mgr.gd",
        r"dependencies\s*:\s*Array\[StringName\]",
        "dependency-aware ModuleMgr.register_factory",
    ),
    (
        "modules/core/pool/pool_function.gd",
        r"(?m)^static\s+func\s+remove_all\s*\(",
        "PoolFunction.remove_all",
    ),
    (
        "modules/connector/network_service.gd",
        r"(?m)^func\s+subscribe\s*\(",
        "NetworkService.subscribe",
    ),
)


def _display_path(project_root: Path, path: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _gdscript_code(text: str) -> str:
    """Replace comments and string literals with spaces while preserving lines."""
    result: list[str] = []
    quote: str | None = None
    escaped = False
    in_comment = False
    for character in text:
        if in_comment:
            if character == "\n":
                in_comment = False
                result.append(character)
            else:
                result.append(" ")
        elif quote is not None:
            result.append("\n" if character == "\n" else " ")
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif character == "#":
            in_comment = True
            result.append(" ")
        elif character in ('"', "'"):
            quote = character
            result.append(" ")
        else:
            result.append(character)
    return "".join(result)


def _module_class_name(feature_id: str) -> str:
    return "".join(part.capitalize() for part in feature_id.split("_")) + "Module"


def _foundation_findings(project_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for relative_path, pattern, description in FOUNDATION_REQUIREMENTS:
        path = project_root / relative_path
        if not path.is_file():
            findings.append(Finding("foundation_unavailable", relative_path, "%s is missing" % description))
        elif re.search(pattern, _gdscript_code(_read(path))) is None:
            findings.append(Finding("foundation_unavailable", relative_path, "%s is unavailable" % description))
    return findings


def _section_text(spec_text: str, heading: str) -> str | None:
    match = re.search(r"^##\s+%s\s*$" % re.escape(heading), spec_text, re.MULTILINE)
    if match is None:
        return None
    next_heading = re.search(r"^##\s+", spec_text[match.end():], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading is not None else len(spec_text)
    return spec_text[match.end():end]


def _split_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def _markdown_tables(section_text: str) -> list[tuple[list[str], list[list[str]]]]:
    lines = section_text.splitlines()
    tables: list[tuple[list[str], list[list[str]]]] = []
    index = 0
    while index + 1 < len(lines):
        headers = _split_table_row(lines[index])
        separator = _split_table_row(lines[index + 1])
        if headers is None or separator is None or len(headers) != len(separator) or not _is_table_separator(separator):
            index += 1
            continue

        rows: list[list[str]] = []
        index += 2
        while index < len(lines):
            row = _split_table_row(lines[index])
            if row is None:
                break
            next_row = _split_table_row(lines[index + 1]) if index + 1 < len(lines) else None
            if next_row is not None and len(row) == len(next_row) and _is_table_separator(next_row):
                break
            if len(row) == len(headers):
                rows.append(row)
            index += 1
        tables.append(([header.casefold() for header in headers], rows))
    return tables


def _table_rows(spec_text: str, heading: str, required_headers: tuple[str, ...]) -> list[dict[str, str]]:
    section = _section_text(spec_text, heading)
    if section is None:
        return []
    normalized_headers = tuple(header.casefold() for header in required_headers)
    for headers, rows in _markdown_tables(section):
        if not all(header in headers for header in normalized_headers):
            continue
        return [
            {header: row[headers.index(header)] for header in normalized_headers}
            for row in rows
        ]
    return []


def _strip_code_cell(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1].strip()
    return stripped


def _is_none_cell(value: str) -> bool:
    return _strip_code_cell(value).casefold().rstrip(".") == "none"


def _has_explicit_default(value: str) -> bool:
    default_value = _strip_code_cell(value)
    return bool(
        default_value
        and default_value.casefold().rstrip(".") not in {"none", "tbd"}
        and not default_value.startswith("<")
    )


def _pascal_name(value: str) -> str:
    return "".join(part.capitalize() for part in value.split("_") if part)


def _normalize_expression(value: str) -> str:
    stripped = value.strip().rstrip(",").rstrip()
    normalized: list[str] = []
    quote: str | None = None
    escaped = False
    for character in stripped:
        if quote is not None:
            normalized.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif character in ('"', "'"):
            quote = character
            normalized.append(character)
        elif not character.isspace():
            normalized.append(character)
    return "".join(normalized)


def _strip_inline_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif character in ('"', "'"):
            quote = character
        elif character == "#":
            return value[:index].rstrip()
    return value.rstrip()


def _strip_string_literal(value: str) -> str | None:
    stripped = value.strip()
    match = re.fullmatch(r'(?:&)?"((?:[^"\\]|\\.)*)"', stripped)
    if match is None:
        return None
    return match.group(1)


def _split_contract_items(value: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"\s*(?:<br\s*/?>|;)\s*", value, flags=re.IGNORECASE)
        if item.strip()
    ]


def _normalized_signature(value: str, allow_return: bool = True) -> tuple[str, str] | None:
    signature = _strip_code_cell(value)
    if not signature or signature.startswith("<"):
        return None
    name_match = re.match(r"^([a-z][A-Za-z0-9_]*)\s*\(", signature)
    if name_match is None:
        return None
    open_index = signature.find("(", name_match.start())
    parsed = _split_arguments_at(signature, open_index)
    if parsed is None:
        return None
    arguments, close_index = parsed
    suffix = signature[close_index + 1:].strip()
    return_type = ""
    if suffix:
        return_match = re.fullmatch(r"->\s*(.+)", suffix)
        if not allow_return or return_match is None:
            return None
        return_type = _normalize_expression(return_match.group(1))
    normalized_arguments = ",".join(_normalize_expression(argument) for argument in arguments)
    normalized = "%s(%s)" % (name_match.group(1), normalized_arguments)
    if return_type:
        normalized += "->" + return_type
    return name_match.group(1), normalized


def _split_arguments_at(text: str, open_index: int) -> tuple[list[str], int] | None:
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = ["("]
    arguments: list[str] = []
    argument_start = open_index + 1
    quote: str | None = None
    escaped = False
    in_comment = False
    for index in range(open_index + 1, len(text)):
        character = text[index]
        if in_comment:
            if character == "\n":
                in_comment = False
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character == "#":
            in_comment = True
        elif character in ('"', "'"):
            quote = character
        elif character in pairs:
            stack.append(character)
        elif character in pairs.values():
            if not stack or character != pairs[stack[-1]]:
                return None
            stack.pop()
            if not stack:
                final_argument = text[argument_start:index]
                if final_argument.strip():
                    arguments.append(final_argument.strip())
                return arguments, index
        elif character == "," and len(stack) == 1:
            arguments.append(text[argument_start:index].strip())
            argument_start = index + 1
    return None


def _call_arguments(text: str, callee: str) -> list[list[str]]:
    code = _gdscript_code(text)
    calls: list[list[str]] = []
    pattern = re.compile(r"\b%s\s*\(" % re.escape(callee))
    for match in pattern.finditer(code):
        open_index = code.rfind("(", match.start(), match.end())
        parsed = _split_arguments_at(text, open_index)
        if parsed is not None:
            calls.append(parsed[0])
    return calls


def _function_bodies(code: str) -> dict[str, list[str]]:
    functions: dict[str, list[str]] = {}
    lines = code.splitlines()
    signature = re.compile(
        r"^(?:static\s+)?func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)(?:\s*->\s*[^:]+)?\s*:\s*$"
    )
    for line_index, line in enumerate(lines):
        match = signature.fullmatch(line)
        if match is None:
            continue
        body: list[str] = []
        for body_line in lines[line_index + 1:]:
            if body_line.strip() and not body_line[:1].isspace():
                break
            body.append(body_line)
        functions.setdefault(match.group(1), []).append("\n".join(body))
    return functions


def _declared_function_signatures(text: str) -> dict[str, set[str]]:
    code = _gdscript_code(text)
    signatures: dict[str, set[str]] = {}
    pattern = re.compile(r"(?m)^(?:static\s+)?func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    for match in pattern.finditer(code):
        open_index = code.find("(", match.start(), match.end())
        parsed = _split_arguments_at(text, open_index)
        if parsed is None:
            continue
        arguments, close_index = parsed
        suffix_match = re.match(r"\s*(?:->\s*([^:\n]+))?\s*:", code[close_index + 1:])
        if suffix_match is None:
            continue
        normalized = "%s(%s)" % (
            match.group(1),
            ",".join(_normalize_expression(argument) for argument in arguments),
        )
        if suffix_match.group(1):
            normalized += "->" + _normalize_expression(suffix_match.group(1))
        signatures.setdefault(match.group(1), set()).add(normalized)
    return signatures


def _declared_signal_signatures(text: str) -> dict[str, set[str]]:
    code = _gdscript_code(text)
    signatures: dict[str, set[str]] = {}
    pattern = re.compile(r"(?m)^signal\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    for match in pattern.finditer(code):
        open_index = code.find("(", match.start(), match.end())
        parsed = _split_arguments_at(text, open_index)
        if parsed is None:
            continue
        arguments, _close_index = parsed
        normalized = "%s(%s)" % (
            match.group(1),
            ",".join(_normalize_expression(argument) for argument in arguments),
        )
        signatures.setdefault(match.group(1), set()).add(normalized)
    for match in re.finditer(r"(?m)^signal\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", code):
        signatures.setdefault(match.group(1), set()).add(match.group(1) + "()")
    return signatures


def _script_class_name(text: str) -> str | None:
    match = re.search(r"(?m)^class_name\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", _gdscript_code(text))
    return match.group(1) if match is not None else None


def _script_base_name(text: str) -> str | None:
    match = re.search(r"(?m)^extends\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", _gdscript_code(text))
    return match.group(1) if match is not None else None


def _has_control_lineage(base_name: str | None, class_bases: dict[str, str]) -> bool:
    control_bases = {
        "BaseButton", "Button", "CenterContainer", "CheckBox", "CheckButton",
        "ColorRect", "Container", "Control", "GraphEdit", "GraphNode",
        "GridContainer", "HBoxContainer", "ItemList", "Label", "LineEdit",
        "MarginContainer", "MenuButton", "NinePatchRect", "OptionButton",
        "Panel", "PanelContainer", "ProgressBar", "Range", "RichTextLabel",
        "ScrollContainer", "Slider", "SpinBox", "TabBar", "TabContainer",
        "TextEdit", "TextureButton", "TextureRect", "Tree", "VBoxContainer",
        "VideoStreamPlayer", "SubViewportContainer", "GuiBase", "GuiQueueBase",
    }
    current = base_name
    seen: set[str] = set()
    while current is not None and current not in seen:
        if current in control_bases:
            return True
        if current == "BaseScreen":
            return False
        seen.add(current)
        current = class_bases.get(current)
    return False


def _constant_expressions(text: str) -> dict[str, str]:
    code = _gdscript_code(text)
    expressions: dict[str, str] = {}
    pattern = re.compile(
        r"(?m)^const\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*:\s*[^=\n]+)?\s*(?::=|=)\s*"
    )
    for match in pattern.finditer(code):
        line_end = text.find("\n", match.end())
        if line_end == -1:
            line_end = len(text)
        expression = _strip_inline_comment(text[match.end():line_end].strip())
        if expression:
            expressions[match.group(1)] = expression
    return expressions


def _script_texts(root: Path) -> list[tuple[Path, str]]:
    if not root.is_dir():
        return []
    return [(path, _read(path)) for path in sorted(root.rglob("*.gd"))]


def _constant_catalog(script_texts: list[tuple[Path, str]]) -> dict[str, str]:
    catalog: dict[str, str] = {}
    for _path, text in script_texts:
        class_name = _script_class_name(text)
        if class_name is None:
            continue
        for constant_name, expression in _constant_expressions(text).items():
            catalog["%s.%s" % (class_name, constant_name)] = expression
    return catalog


def _resolve_expression(
    expression: str,
    constants: dict[str, str],
    local_class: str | None = None,
    seen: frozenset[str] = frozenset(),
) -> str:
    normalized = _normalize_expression(expression)
    try:
        return str(int(normalized, 0))
    except ValueError:
        pass
    lookup = normalized
    if "." not in lookup and local_class:
        lookup = "%s.%s" % (local_class, lookup)
    if lookup in seen or lookup not in constants:
        return normalized
    return _resolve_expression(constants[lookup], constants, lookup.split(".", 1)[0], seen | {lookup})


def _expressions_match(
    actual: str,
    expected: str,
    constants: dict[str, str],
    actual_class: str | None = None,
    expected_class: str | None = None,
) -> bool:
    return _resolve_expression(actual, constants, actual_class) == _resolve_expression(
        expected,
        constants,
        expected_class,
    )


def _command_contracts(spec_text: str) -> list[CommandContract]:
    contracts: list[CommandContract] = []
    headers = ("ID", "Direction", "Send/receive class", "Response/push")
    for row in _table_rows(spec_text, "Command ownership", headers):
        command_id = _strip_code_cell(row["id"])
        if _is_none_cell(command_id):
            continue
        contracts.append(
            CommandContract(
                command_id=command_id,
                direction=_strip_code_cell(row["direction"]).casefold(),
                packet_class=_strip_code_cell(row["send/receive class"]),
                response_kind=_strip_code_cell(row["response/push"]).casefold(),
            )
        )
    return contracts


def _packet_command_matches(
    packet_text: str,
    packet_class: str,
    command_id: str,
    constants: dict[str, str],
) -> bool:
    packet_constants = _constant_expressions(packet_text)
    candidates: list[str] = []
    if "CMD_ID" in packet_constants:
        candidates.append(packet_constants["CMD_ID"])
    code = _gdscript_code(packet_text)
    candidates.extend(
        match.group(1).strip()
        for match in re.finditer(r"(?m)^\s*(?:var\s+)?cmd_id(?:\s*:\s*[^=\n]+)?\s*(?::=|=)\s*([^\n]+)$", code)
    )
    return any(
        _expressions_match(candidate, command_id, constants, packet_class)
        for candidate in candidates
    )


def _has_exact_subscription(
    module_text: str,
    module_class: str,
    contract: CommandContract,
    constants: dict[str, str],
) -> bool:
    for arguments in _call_arguments(module_text, "NetworkService.subscribe"):
        if len(arguments) != 3:
            continue
        if _normalize_expression(arguments[1]) != contract.packet_class:
            continue
        if _expressions_match(arguments[0], contract.command_id, constants, module_class):
            return True
    return False


def _has_exact_send_callsite(module_text: str, packet_class: str) -> bool:
    code = _gdscript_code(module_text)
    direct = r"\bNetworkService\.send_packet\s*\(\s*%s\.new\s*\(" % re.escape(packet_class)
    if re.search(direct, code) is not None:
        return True
    for bodies in _function_bodies(code).values():
        for body in bodies:
            variables = re.findall(
                r"(?m)^\s*(?:var\s+)?([A-Za-z_][A-Za-z0-9_]*)"
                r"(?:\s*:\s*[^=\n]+)?\s*(?::=|=)\s*%s\.new\s*\("
                % re.escape(packet_class),
                body,
            )
            if any(
                re.search(r"\bNetworkService\.send_packet\s*\(\s*%s\s*\)" % re.escape(variable), body)
                is not None
                for variable in variables
            ):
                return True
    return False


def _function_body(code: str, function_name: str) -> str | None:
    lines = code.splitlines()
    signature = re.compile(
        r"^func\s+%s\s*\([^)]*\)(?:\s*->\s*[^:]+)?\s*:\s*$" % re.escape(function_name)
    )
    for line_index, line in enumerate(lines):
        if signature.fullmatch(line) is None:
            continue
        body: list[str] = []
        for body_line in lines[line_index + 1:]:
            if body_line.strip() and not body_line[:1].isspace():
                break
            body.append(body_line)
        return "\n".join(body)
    return None


def _optional_contracts(spec_text: str, heading: str) -> list[OptionalContract]:
    headers = ("Namespaced StringName", "Provider method", "Call arguments", "Explicit default")
    contracts: list[OptionalContract] = []
    for row in _table_rows(spec_text, heading, headers):
        key = _strip_code_cell(row["namespaced stringname"])
        if _is_none_cell(key):
            continue
        contracts.append(
            OptionalContract(
                key=key,
                provider_signature=_strip_code_cell(row["provider method"]),
                call_arguments=_strip_code_cell(row["call arguments"]),
                explicit_default=_strip_code_cell(row["explicit default"]),
            )
        )
    return contracts


def _boundary_names(feature_id: str, key: str) -> tuple[str, str, str] | None:
    match = re.fullmatch(r'&"%s\.([a-z][a-z0-9_]*)"' % re.escape(feature_id), key)
    if match is None:
        return None
    action = match.group(1).upper()
    return _pascal_name(feature_id) + "OptionalBoundary", action, "DEFAULT_" + action


def _has_exact_pool_registration(
    module_text: str,
    boundary_class: str,
    action_constant: str,
    provider_method: str,
) -> bool:
    expected_key = boundary_class + "." + action_constant
    for arguments in _call_arguments(module_text, "PoolFunction.reg_func"):
        if len(arguments) != 3:
            continue
        if (
            _normalize_expression(arguments[0]) == expected_key
            and _normalize_expression(arguments[1]) == "self"
            and _normalize_expression(arguments[2]) == provider_method
        ):
            return True
    return False


def _has_exact_pool_callsite(
    script_texts: list[tuple[Path, str]],
    boundary_class: str,
    action_constant: str,
    call_arguments: str,
    default_constant: str,
) -> bool:
    expected_key = boundary_class + "." + action_constant
    expected_default = boundary_class + "." + default_constant
    for _path, text in script_texts:
        for arguments in _call_arguments(text, "PoolFunction.do_func"):
            if len(arguments) != 3:
                continue
            if (
                _normalize_expression(arguments[0]) == expected_key
                and _normalize_expression(arguments[1]) == _normalize_expression(call_arguments)
                and _normalize_expression(arguments[2]) == expected_default
            ):
                return True
    return False


def _config_class_name(feature_id: str, file_name: str) -> str | None:
    primary = feature_id + "_json_config.gd"
    if file_name == primary:
        return _pascal_name(feature_id) + "JSONConfig"
    prefix = feature_id + "_"
    suffix = "_json_config.gd"
    if not file_name.startswith(prefix) or not file_name.endswith(suffix):
        return None
    domain = file_name[len(prefix):-len(suffix)]
    if re.fullmatch(r"[a-z][a-z0-9_]*", domain) is None:
        return None
    return _pascal_name(feature_id) + _pascal_name(domain) + "JSONConfig"


def _registered_config_path(script_texts: list[tuple[Path, str]], relative_path: str) -> bool:
    for _path, text in script_texts:
        for arguments in _call_arguments(text, "ConfigMgr.register_json_file"):
            if arguments and _strip_string_literal(arguments[0]) == relative_path:
                return True
    return False


def _preinitialized_config_path(
    script_texts: list[tuple[Path, str]],
    config_class: str,
    relative_path: str,
) -> bool:
    callee = config_class + ".get_instance(true).pre_init"
    for _path, text in script_texts:
        for arguments in _call_arguments(text, callee):
            if arguments and _strip_string_literal(arguments[-1]) == relative_path:
                return True
    return False


def _expand_config_path_contract(value: str) -> list[str] | None:
    """Expand an exact path or one zero-padded numeric source-family range."""
    match = re.fullmatch(r"(.*)\{(\d+)\.\.(\d+)\}(.*\.json)", value)
    if match is None:
        return [value]
    first_text, last_text = match.group(2), match.group(3)
    if len(first_text) != len(last_text):
        return None
    first, last = int(first_text), int(last_text)
    if first > last or last - first > 999:
        return None
    width = len(first_text)
    return [
        "%s%s%s" % (match.group(1), str(index).zfill(width), match.group(4))
        for index in range(first, last + 1)
    ]


def _has_multi_instance_config_owner(
    script_texts: list[tuple[Path, str]],
    config_class: str,
) -> bool:
    """Recognize a caller-owned same-schema family without pretending it is a singleton."""
    loader_binds_once = False
    owner_constructs_and_registers = False
    for _path, text in script_texts:
        if _script_class_name(text) == config_class and _call_arguments(text, "pre_init"):
            loader_binds_once = True
        code = _gdscript_code(text)
        if re.search(r"\b%s\.new\s*\(" % re.escape(config_class), code) is None:
            continue
        registrations = _call_arguments(text, "ConfigMgr.register_json_file")
        preinitializations = _call_arguments(text, "pre_init")
        if registrations:
            owner_constructs_and_registers = True
        for registration in registrations:
            if not registration:
                continue
            registration_path = _normalize_expression(registration[0])
            for preinitialization in preinitializations:
                if preinitialization and _normalize_expression(preinitialization[-1]) == registration_path:
                    return True
    return owner_constructs_and_registers and loader_binds_once


def _test_function_bodies(test_text: str) -> dict[str, str]:
    code = _gdscript_code(test_text)
    if re.search(r"(?m)^extends\s+GutTest\s*$", code) is None:
        return {}
    return {
        name: bodies[0]
        for name, bodies in _function_bodies(code).items()
        if name.startswith("test_") and bodies
    }


def _has_asserted_evidence(body: str, evidence_symbols: set[str]) -> bool:
    def mentions_evidence(expression: str) -> bool:
        return any(
            re.search(r"\b%s\b" % re.escape(symbol), expression) is not None
            for symbol in evidence_symbols
        )

    derived_locals: set[str] = set()
    assignment_pattern = re.compile(
        r"(?m)^\s*(?:var\s+)?([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\s*:\s*[^=\n]+)?\s*(?::=|=)\s*([^\n]+)$"
    )
    for assignment in assignment_pattern.finditer(body):
        if mentions_evidence(assignment.group(2)):
            derived_locals.add(assignment.group(1))

    assertion_pattern = re.compile(r"\bassert_(?!not_null\b)[A-Za-z0-9_]+\s*\(")
    for assertion in assertion_pattern.finditer(body):
        open_index = body.find("(", assertion.start(), assertion.end())
        parsed = _split_arguments_at(body, open_index)
        if parsed is None:
            continue
        assertion_expression = ",".join(parsed[0])
        if mentions_evidence(assertion_expression) or any(
            re.search(r"\b%s\b" % re.escape(local_name), assertion_expression) is not None
            for local_name in derived_locals
        ):
            return True
    return False


def _spec_activation(spec_text: str) -> str | None:
    for row in _table_rows(spec_text, "Status", ("Field", "Approved value")):
        if _strip_code_cell(row["field"]).casefold() != "activation":
            continue
        value = _strip_code_cell(row["approved value"]).casefold()
        modes = set(re.findall(r"\b(?:eager|lazy)\b", value))
        if len(modes) == 1:
            mode = modes.pop()
            if re.match(r"^%s(?:\s|$)" % mode, value):
                return mode
    return None


def _spec_source_root(spec_text: str, feature_id: str) -> str | None:
    for row in _table_rows(spec_text, "Status", ("Field", "Approved value")):
        if _strip_code_cell(row["field"]).casefold() != "source root":
            continue
        value = _strip_code_cell(row["approved value"])
        if re.fullmatch(r"modules/game(?:/[a-z][a-z0-9_]*)+", value) is None:
            return None
        path = PurePosixPath(value)
        if path.name != feature_id:
            return None
        return value
    return None


def _has_server_push(spec_text: str) -> bool:
    return any(contract.response_kind == "server push" for contract in _command_contracts(spec_text))


def _asset_roots(spec_text: str) -> list[str]:
    roots: list[str] = []
    for row in _table_rows(spec_text, "UI and assets", ("Asset root",)):
        asset_root = _strip_code_cell(row["asset root"])
        if not asset_root or asset_root.casefold() == "none" or asset_root.startswith("<"):
            continue
        roots.append(asset_root.removeprefix("res://"))
    return roots


def _finding(code: str, project_root: Path, path: Path, message: str) -> Finding:
    return Finding(code, _display_path(project_root, path), message)


def validate_feature(project_root: Path, feature_id: str, spec_path: Path) -> list[Finding]:
    """Return deterministic contract findings without modifying project files."""
    findings: list[Finding] = []
    spec_text = _read(spec_path)
    source_root = _spec_source_root(spec_text, feature_id)
    if source_root is None:
        return [
            _finding(
                "invalid_source_root",
                project_root,
                spec_path,
                "Status table must declare Source root as modules/game/.../%s" % feature_id,
            )
        ]

    feature_root = project_root.joinpath(*PurePosixPath(source_root).parts)
    module_path = feature_root / (feature_id + "_module.gd")
    util_path = feature_root / "logic" / (feature_id + "_util.gd")
    registry_path = project_root / "modules/game/game_feature_registry.gd"
    tests_root = project_root / "tests/unit/features" / feature_id
    module_class = _module_class_name(feature_id)
    module_text = _read(module_path) if module_path.is_file() else ""
    module_code = _gdscript_code(module_text)
    module_functions = _declared_function_signatures(module_text) if module_text else {}
    module_signals = _declared_signal_signatures(module_text) if module_text else {}
    module_bodies = _function_bodies(module_code) if module_text else {}
    project_script_texts = sorted(
        _script_texts(project_root / "modules") + _script_texts(project_root / "devtools"),
        key=lambda item: item[0].as_posix(),
    )
    constants = _constant_catalog(project_script_texts)
    network_script_texts = _script_texts(feature_root / "network")
    packet_scripts = {
        class_name: (path, text)
        for path, text in network_script_texts
        if (class_name := _script_class_name(text)) is not None
    }

    if not feature_root.is_dir():
        findings.append(_finding("missing_feature_root", project_root, feature_root, "canonical feature root is missing"))
    if not module_path.is_file():
        findings.append(_finding("missing_module", project_root, module_path, "canonical feature module is missing"))
    if not util_path.is_file():
        findings.append(_finding("missing_util", project_root, util_path, "canonical feature utility is missing"))

    activation = _spec_activation(spec_text)
    command_contracts = _command_contracts(spec_text)
    has_server_push = _has_server_push(spec_text)
    if activation is None:
        findings.append(_finding("invalid_activation", project_root, spec_path, "Status table must declare one activation mode: eager or lazy"))
    elif activation == "lazy" and has_server_push:
        findings.append(_finding("lazy_push_owner", project_root, spec_path, "lazy features cannot own server-push commands"))

    if module_path.is_file():
        if re.search(r"^extends\s+BaseModule\b", module_code, re.MULTILINE) is None:
            findings.append(_finding("module_not_base_module", project_root, module_path, "module must extend BaseModule"))
        owns_network_subscriptions = re.search(r"\bNetworkService\.subscribe\s*\(", module_code) is not None
        owns_pool_registrations = re.search(r"\bPoolFunction\.reg_func\s*\(", module_code) is not None
        destroy_body = _function_body(module_code, "on_destroy")
        missing_network_cleanup = owns_network_subscriptions and (
            destroy_body is None
            or re.search(r"\bNetworkService\.unsubscribe_all\s*\(\s*self\s*\)", destroy_body) is None
        )
        missing_pool_cleanup = owns_pool_registrations and (
            destroy_body is None
            or re.search(r"\bPoolFunction\.remove_all\s*\(\s*self\s*\)", destroy_body) is None
        )
        if missing_network_cleanup or missing_pool_cleanup:
            findings.append(_finding("missing_owner_cleanup", project_root, module_path, "module must clean up each owned registration inside on_destroy"))

    valid_command_contracts: list[CommandContract] = []
    for contract in command_contracts:
        valid_id = re.fullmatch(
            r"(?:0x[0-9A-Fa-f]+|[0-9]+|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)",
            contract.command_id,
        )
        valid_class = re.fullmatch(r"[A-Z][A-Za-z0-9]*", contract.packet_class)
        if (
            valid_id is None
            or valid_class is None
            or contract.direction not in {"client -> server", "server -> client"}
            or contract.response_kind not in {"response", "server push"}
        ):
            findings.append(
                _finding(
                    "invalid_command_contract",
                    project_root,
                    spec_path,
                    "each command row requires an exact ID, direction, packet class, and response/server push kind",
                )
            )
            continue
        valid_command_contracts.append(contract)
        packet_entry = packet_scripts.get(contract.packet_class)
        if packet_entry is None:
            findings.append(
                _finding(
                    "command_class_mismatch",
                    project_root,
                    feature_root / "network",
                    "documented packet class %s is not declared by the feature network scripts" % contract.packet_class,
                )
            )
        else:
            packet_path, packet_text = packet_entry
            if not _packet_command_matches(packet_text, contract.packet_class, contract.command_id, constants):
                findings.append(
                    _finding(
                        "command_id_mismatch",
                        project_root,
                        packet_path,
                        "%s must own documented command ID %s" % (contract.packet_class, contract.command_id),
                    )
                )
        if not module_path.is_file():
            continue
        if contract.direction == "server -> client":
            if not _has_exact_subscription(module_text, module_class, contract, constants):
                findings.append(
                    _finding(
                        "command_registration_mismatch",
                        project_root,
                        module_path,
                        "module subscription must match %s and command %s" % (contract.packet_class, contract.command_id),
                    )
                )
        elif not _has_exact_send_callsite(module_text, contract.packet_class):
            findings.append(
                _finding(
                    "command_callsite_mismatch",
                    project_root,
                    module_path,
                    "module must construct and send %s" % contract.packet_class,
                )
            )

    receive_contracts = [
        contract for contract in valid_command_contracts if contract.direction == "server -> client"
    ]
    if module_path.is_file() and receive_contracts and not _call_arguments(module_text, "NetworkService.subscribe"):
        findings.append(
            _finding(
                "missing_owner_subscription",
                project_root,
                module_path,
                "documented receive commands require owned typed NetworkService.subscribe calls",
            )
        )

    if feature_root.is_dir():
        feature_script_texts = _script_texts(feature_root)
        class_bases = {
            class_name: base_name
            for _path, text in feature_script_texts
            if (class_name := _script_class_name(text)) is not None
            if (base_name := _script_base_name(text)) is not None
        }
        for script_path, script_text in feature_script_texts:
            script_code = _gdscript_code(script_text)
            relative_parts = script_path.relative_to(feature_root).parts
            is_ui_script = "ui" in relative_parts
            direct_base = _script_base_name(script_text)
            if is_ui_script and direct_base != "BaseScreen" and _has_control_lineage(
                direct_base, class_bases
            ):
                findings.append(
                    _finding(
                        "ui_not_base_screen",
                        project_root,
                        script_path,
                        "Control UI scripts must directly extend BaseScreen; non-Control world/render scripts use their Node base",
                    )
                )
            if is_ui_script and (
                re.search(r"\bNetworkService\.subscribe\s*\(", script_code) is not None
                or re.search(r"\bsend_packet\s*\(", script_code) is not None
            ):
                findings.append(_finding("network_outside_module", project_root, script_path, "UI scripts cannot subscribe or send network packets"))
            elif script_path != module_path and re.search(r"\bNetworkService\.subscribe\s*\(", script_code) is not None:
                findings.append(_finding("network_outside_module", project_root, script_path, "only the module may subscribe to NetworkService"))

        network_root = feature_root / "network"
        if network_root.is_dir():
            prefixes = (feature_id + "_send_", feature_id + "_recv_")
            for network_path in sorted(network_root.rglob("*.gd")):
                if not network_path.name.startswith(prefixes):
                    findings.append(_finding("invalid_network_filename", project_root, network_path, "network filename must use the feature send_/recv_ prefix"))

    documented_symbols: set[str] = set()
    api_headers = ("Command/query", "Signature", "Semantic signal")
    for api_row in _table_rows(spec_text, "State and public module API", api_headers):
        signature_value = _strip_code_cell(api_row["signature"])
        if _is_none_cell(signature_value):
            continue
        signature = _normalized_signature(signature_value)
        if (
            signature is None
            or not module_path.is_file()
            or signature[1] not in module_functions.get(signature[0], set())
        ):
            findings.append(
                _finding(
                    "public_api_mismatch",
                    project_root,
                    module_path if module_path.is_file() else spec_path,
                    "documented public signature is missing or differs: %s" % signature_value,
                )
            )
        elif signature is not None:
            documented_symbols.add(signature[0])

        signal_value = _strip_code_cell(api_row["semantic signal"])
        if _is_none_cell(signal_value):
            continue
        signal = _normalized_signature(signal_value, allow_return=False)
        signal_matches = bool(
            signal is not None
            and signal[1] in module_signals.get(signal[0], set())
            and re.search(r"\b%s\.emit\s*\(" % re.escape(signal[0]), module_code) is not None
        )
        if not signal_matches:
            findings.append(
                _finding(
                    "semantic_signal_mismatch",
                    project_root,
                    module_path if module_path.is_file() else spec_path,
                    "documented signal must match its declaration and emission: %s" % signal_value,
                )
            )
        elif signal is not None:
            documented_symbols.add(signal[0])

    optional_contracts: list[tuple[str, OptionalContract]] = []
    optional_contracts.extend(("action", contract) for contract in _optional_contracts(spec_text, "Optional actions"))
    optional_contracts.extend(("query", contract) for contract in _optional_contracts(spec_text, "Optional queries"))
    boundary_path = project_root / "modules/game/contracts" / (feature_id + "_optional_boundary.gd")
    boundary_text = _read(boundary_path) if boundary_path.is_file() else ""
    boundary_constants = _constant_expressions(boundary_text) if boundary_text else {}

    for kind, contract in optional_contracts:
        malformed_code = "malformed_optional_action" if kind == "action" else "malformed_optional_query"
        boundary_names = _boundary_names(feature_id, contract.key)
        if re.fullmatch(r'&"[^"]+"', contract.key) is None:
            findings.append(
                _finding(
                    malformed_code,
                    project_root,
                    spec_path,
                    "optional %s key must be one StringName literal" % kind,
                )
            )
            continue
        if boundary_names is None:
            findings.append(
                _finding(
                    "unnamespaced_action",
                    project_root,
                    spec_path,
                    "optional %s key must use &\"%s.<action>\"" % (kind, feature_id),
                )
            )
            continue
        if not _has_explicit_default(contract.explicit_default):
            findings.append(
                _finding(
                    "missing_optional_default",
                    project_root,
                    spec_path,
                    "optional %s requires an explicit default" % kind,
                )
            )
            continue

        boundary_class, action_constant, default_constant = boundary_names
        if (
            not boundary_path.is_file()
            or _script_class_name(boundary_text) != boundary_class
            or _normalize_expression(boundary_constants.get(action_constant, ""))
            != _normalize_expression(contract.key)
        ):
            findings.append(
                _finding(
                    "optional_boundary_mismatch",
                    project_root,
                    boundary_path,
                    "%s.%s must retain key %s" % (boundary_class, action_constant, contract.key),
                )
            )
        if _normalize_expression(boundary_constants.get(default_constant, "")) != _normalize_expression(
            contract.explicit_default
        ):
            findings.append(
                _finding(
                    "optional_default_mismatch",
                    project_root,
                    boundary_path,
                    "%s.%s must equal documented default %s"
                    % (boundary_class, default_constant, contract.explicit_default),
                )
            )

        provider = _normalized_signature(contract.provider_signature)
        if (
            provider is None
            or provider[1] not in module_functions.get(provider[0], set())
        ):
            findings.append(
                _finding(
                    "optional_provider_mismatch",
                    project_root,
                    module_path if module_path.is_file() else spec_path,
                    "optional provider signature must match: %s" % contract.provider_signature,
                )
            )
            continue
        documented_symbols.add(provider[0])
        if not _has_exact_pool_registration(
            module_text,
            boundary_class,
            action_constant,
            provider[0],
        ):
            findings.append(
                _finding(
                    "optional_registration_mismatch",
                    project_root,
                    module_path,
                    "PoolFunction registration must use %s.%s, self, and %s"
                    % (boundary_class, action_constant, provider[0]),
                )
            )
        if not _has_exact_pool_callsite(
            project_script_texts,
            boundary_class,
            action_constant,
            contract.call_arguments,
            default_constant,
        ):
            findings.append(
                _finding(
                    "optional_callsite_mismatch",
                    project_root,
                    project_root / "modules/game",
                    "PoolFunction callsite must use %s.%s, documented arguments, and %s.%s"
                    % (boundary_class, action_constant, boundary_class, default_constant),
                )
            )

    config_headers = ("File", "One class", "ConfigMgr relative path", "Typed accessors")
    for config_row in _table_rows(spec_text, "JSON configuration", config_headers):
        file_name = _strip_code_cell(config_row["file"])
        if _is_none_cell(file_name):
            continue
        config_class = _strip_code_cell(config_row["one class"])
        relative_path_contract = _strip_code_cell(config_row["configmgr relative path"])
        relative_paths = _expand_config_path_contract(relative_path_contract)
        if relative_paths is None:
            findings.append(
                _finding(
                    "config_registration_mismatch",
                    project_root,
                    spec_path,
                    "invalid config source-family range %s" % relative_path_contract,
                )
            )
            continue
        is_source_family = len(relative_paths) > 1
        expected_class = _config_class_name(feature_id, file_name)
        config_path = feature_root / "config" / file_name
        config_text = _read(config_path) if config_path.is_file() else ""
        if expected_class is None or config_class != expected_class:
            findings.append(
                _finding(
                    "config_class_mismatch",
                    project_root,
                    spec_path,
                    "%s must declare canonical class %s" % (file_name, expected_class or "<Feature>JSONConfig"),
                )
            )
        if not config_path.is_file():
            findings.append(
                _finding("missing_config_file", project_root, config_path, "documented config loader file is missing")
            )
            continue
        if _script_class_name(config_text) != config_class:
            findings.append(
                _finding(
                    "config_class_mismatch",
                    project_root,
                    config_path,
                    "config script class_name must equal %s" % config_class,
                )
            )
        if is_source_family and re.search(r"(?m)^static\s+func\s+get_instance\s*\(", config_text):
            findings.append(
                _finding(
                    "config_family_singleton_mismatch",
                    project_root,
                    config_path,
                    "same-schema source-family loaders use caller-owned new() instances, not one Script-keyed singleton",
                )
            )
        config_functions = _declared_function_signatures(config_text)
        for accessor_value in _split_contract_items(config_row["typed accessors"]):
            if _is_none_cell(accessor_value):
                continue
            accessor = _normalized_signature(accessor_value)
            if accessor is None or accessor[1] not in config_functions.get(accessor[0], set()):
                findings.append(
                    _finding(
                        "config_accessor_mismatch",
                        project_root,
                        config_path,
                        "documented typed accessor must match: %s" % accessor_value,
                    )
                )
            elif accessor is not None:
                documented_symbols.add(accessor[0])
        family_owner_exists = is_source_family and _has_multi_instance_config_owner(
            project_script_texts, config_class
        )
        for relative_path in relative_paths:
            valid_relative_path = (
                re.fullmatch(r"%s/[a-z][a-z0-9_./-]*\.json" % re.escape(feature_id), relative_path)
                is not None
                and ".." not in PurePosixPath(relative_path).parts
            )
            if not valid_relative_path or (
                not family_owner_exists
                and not _registered_config_path(project_script_texts, relative_path)
            ):
                findings.append(
                    _finding(
                        "config_registration_mismatch",
                        project_root,
                        registry_path,
                        "ConfigMgr must register documented path %s" % relative_path,
                    )
                )
            if not family_owner_exists and not _preinitialized_config_path(
                project_script_texts, config_class, relative_path
            ):
                findings.append(
                    _finding(
                        "config_pre_init_mismatch",
                        project_root,
                        registry_path,
                        "%s must pre_init with documented path %s" % (config_class, relative_path),
                    )
                )

    for asset_root in _asset_roots(spec_text):
        asset_path = project_root / asset_root
        if not asset_path.is_dir():
            findings.append(_finding("missing_asset_root", project_root, asset_path, "documented asset root is missing"))

    if module_path.is_file() and not registry_path.is_file():
        findings.append(_finding("missing_registration", project_root, registry_path, "feature registry is missing"))
    elif module_path.is_file():
        registry_code = _gdscript_code(_read(registry_path))
        registration = r"ModuleMgr\.register_factory\(\s*%s\.MODULE_ID\s*,\s*%s\b" % (module_class, module_class)
        open_call = r"ModuleMgr\.open_module\(\s*%s\.MODULE_ID\s*\)" % module_class
        if re.search(registration, registry_code) is None:
            findings.append(_finding("missing_registration", project_root, registry_path, "registry must register the feature module factory"))
        if activation == "eager" and re.search(open_call, registry_code) is None:
            findings.append(_finding("missing_eager_open", project_root, registry_path, "eager feature must open its module in the registry"))
        if activation == "lazy" and re.search(open_call, registry_code) is not None:
            findings.append(_finding("lazy_eager_open", project_root, registry_path, "lazy feature must not open its module in the registry"))

    test_files = sorted(tests_root.rglob("*.gd")) if tests_root.is_dir() else []
    test_functions: dict[str, list[tuple[Path, str]]] = {}
    for test_path in test_files:
        for function_name, body in _test_function_bodies(_read(test_path)).items():
            test_functions.setdefault(function_name, []).append((test_path, body))

    scenario_rows = _table_rows(spec_text, "Verification", ("Automated scenario", "Expected result"))
    scenario_problem = False
    scenario_count = 0
    evidence_symbols = documented_symbols | {contract.packet_class for contract in valid_command_contracts}
    for scenario_row in scenario_rows:
        scenario = _strip_code_cell(scenario_row["automated scenario"])
        if _is_none_cell(scenario):
            continue
        scenario_count += 1
        expected_result = _strip_code_cell(scenario_row["expected result"])
        if (
            re.fullmatch(r"[a-z][a-z0-9_]*", scenario) is None
            or not expected_result
            or expected_result.casefold() in {"tbd", "placeholder"}
            or expected_result.startswith("<")
            or "validator exits" in expected_result.casefold()
        ):
            scenario_problem = True
            findings.append(
                _finding(
                    "invalid_test_scenario",
                    project_root,
                    spec_path,
                    "automated scenarios require a snake_case ID and concrete observable result",
                )
            )
            continue
        function_name = "test_" + scenario
        matches = test_functions.get(function_name, [])
        if not matches:
            scenario_problem = True
            findings.append(
                _finding(
                    "missing_scenario_test",
                    project_root,
                    tests_root,
                    "verification scenario %s requires func %s" % (scenario, function_name),
                )
            )
            continue
        meaningful = any(
            _has_asserted_evidence(body, evidence_symbols)
            for _test_path, body in matches
        )
        if not meaningful:
            scenario_problem = True
            findings.append(
                _finding(
                    "weak_scenario_test",
                    project_root,
                    matches[0][0],
                    "%s must assert observable module contract behavior" % function_name,
                )
            )

    if scenario_count == 0 or scenario_problem:
        findings.append(
            _finding(
                "missing_tests",
                project_root,
                tests_root,
                "each documented automated scenario needs asserted GUT evidence for %s" % module_class,
            )
        )

    return findings


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a Godot feature contract without modifying files.")
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--feature-id", required=True)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--json", action="store_true", dest="json_mode")
    return parser.parse_args(argv)


def _write_findings(findings: list[Finding], json_mode: bool) -> None:
    if json_mode:
        payload = {
            "valid": not findings,
            "findings": [
                {"code": finding.code, "path": finding.path, "message": finding.message}
                for finding in findings
            ],
        }
        print(json.dumps(payload, sort_keys=True))
        return
    for finding in findings:
        print("%s %s: %s" % (finding.code, finding.path, finding.message))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    project_root = args.project_root.resolve()
    spec_path = args.spec.resolve()
    if re.fullmatch(r"[a-z][a-z0-9_]*", args.feature_id) is None:
        _write_findings([Finding("invalid_feature_id", args.feature_id, "feature ID must be snake_case")], args.json_mode)
        return 2
    if not project_root.is_dir():
        _write_findings([Finding("invalid_project_root", str(project_root), "project root must be a directory")], args.json_mode)
        return 2
    if not spec_path.is_file():
        _write_findings([Finding("invalid_spec_path", str(spec_path), "spec must be an existing file")], args.json_mode)
        return 2

    foundation_findings = _foundation_findings(project_root)
    if foundation_findings:
        _write_findings(foundation_findings, args.json_mode)
        return 2

    findings = validate_feature(project_root, args.feature_id, spec_path)
    _write_findings(findings, args.json_mode)
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
