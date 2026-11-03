#!/usr/bin/env python3
"""Verify the DX11/DXVK backend contract still matches recovered OutRun EXE facts."""

import ast
from pathlib import Path
import re
import runpy

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, needles: list[str]) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{path}: missing disassembly contract evidence: {missing}")


def _function_assignment_names(source: str) -> set[str]:
    """Return simple local names assigned anywhere in one collector source block."""

    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _final_proven_gate_names(source: str) -> set[str]:
    """Return names consumed by the collector's exact final proven bool expression."""

    tree = ast.parse(source)
    proven_values = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "proven" for target in node.targets):
            proven_values.append(node.value)
    if len(proven_values) != 1:
        raise SystemExit(
            "DXVK continuation proof must contain exactly one final proven assignment: "
            f"found={len(proven_values)}"
        )
    value = proven_values[0]
    if not (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "bool"
        and len(value.args) == 1
        and not value.keywords
    ):
        raise SystemExit("DXVK continuation proof final proven assignment must be bool(<gates>)")
    return {
        node.id
        for node in ast.walk(value.args[0])
        if isinstance(node, ast.Name)
    }


def _final_captured_gate_names(source: str) -> set[str]:
    """Return names consumed by the collector's exact final captured bool expression."""

    tree = ast.parse(source)
    captured_values = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "captured" for target in node.targets):
            captured_values.append(node.value)
    if len(captured_values) != 1:
        raise SystemExit(
            "DXVK continuation provenance must contain exactly one final captured assignment: "
            f"found={len(captured_values)}"
        )
    value = captured_values[0]
    if not (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "bool"
        and len(value.args) == 1
        and not value.keywords
    ):
        raise SystemExit("DXVK continuation provenance final captured assignment must be bool(<gates>)")
    return {
        node.id
        for node in ast.walk(value.args[0])
        if isinstance(node, ast.Name)
    }


_DIRECT_BRANCH_LEGACY_PREFIXES = frozenset({
    0x26,  # ES segment override
    0x2E,  # CS override / historical branch hint
    0x36,  # SS segment override
    0x3E,  # DS override / historical branch hint
    0x64,  # FS segment override
    0x65,  # GS segment override
    0x66,  # operand-size override
    0x67,  # address-size override
    0xF2,  # REPNE (ignored/legacy prefix on control flow)
    0xF3,  # REP (ignored/legacy prefix on control flow)
})


def _decode_direct_relative_branch_target(
    instruction_rva: int, encoded: bytes
) -> int | None:
    """Decode direct relative branch targets, including legacy-prefixed forms."""

    prefix_end = 0
    while (
        prefix_end < len(encoded)
        and encoded[prefix_end] in _DIRECT_BRANCH_LEGACY_PREFIXES
    ):
        prefix_end += 1
    if prefix_end >= len(encoded):
        return None

    opcode = encoded[prefix_end]
    operand16 = 0x66 in encoded[:prefix_end]
    body = encoded[prefix_end:]

    # rel8 Jcc/JMP and LOOPNE/LOOPE/LOOP/JCXZ/JECXZ. Legacy prefixes extend
    # instruction length but do not change the signed rel8 displacement.
    if (
        len(body) == 2
        and (
            opcode == 0xEB
            or 0x70 <= opcode <= 0x7F
            or 0xE0 <= opcode <= 0xE3
        )
    ):
        rel8 = int.from_bytes(body[1:2], byteorder="little", signed=True)
        return (instruction_rva + len(encoded) + rel8) & 0xFFFFFFFF

    # Near JMP uses rel16 under 0x66 in 32-bit mode; the resulting EIP is
    # truncated to 16 bits. Without 0x66, the displacement is rel32.
    if opcode == 0xE9:
        if operand16 and len(body) == 3:
            rel16 = int.from_bytes(body[1:3], byteorder="little", signed=True)
            return (instruction_rva + len(encoded) + rel16) & 0xFFFF
        if not operand16 and len(body) == 5:
            rel32 = int.from_bytes(body[1:5], byteorder="little", signed=True)
            return (instruction_rva + len(encoded) + rel32) & 0xFFFFFFFF
        return None

    # Near Jcc follows the same rel16/rel32 operand-size rule.
    if len(body) >= 2 and opcode == 0x0F and 0x80 <= body[1] <= 0x8F:
        if operand16 and len(body) == 4:
            rel16 = int.from_bytes(body[2:4], byteorder="little", signed=True)
            return (instruction_rva + len(encoded) + rel16) & 0xFFFF
        if not operand16 and len(body) == 6:
            rel32 = int.from_bytes(body[2:6], byteorder="little", signed=True)
            return (instruction_rva + len(encoded) + rel32) & 0xFFFFFFFF
    return None


def _verify_direct_relative_branch_decoder() -> None:
    """Exercise branch forms that must not evade exact metadata census."""

    cases = (
        (0x00183000, "75 05", 0x00183007),
        (0x00183000, "67 e3 fc", 0x00182FFF),
        (0x00183000, "66 e9 10 00", 0x00003014),
        (0x00183004, "66 0f 85 10 00", 0x00003019),
        (0x0018300C, "67 e9 10 00 00 00", 0x00183022),
        (0x00183020, "2e 75 05", 0x00183028),
    )
    for instruction_rva, hex_bytes, expected_target_rva in cases:
        actual_target_rva = _decode_direct_relative_branch_target(
            instruction_rva, bytes.fromhex(hex_bytes)
        )
        if actual_target_rva != expected_target_rva:
            raise SystemExit(
                "DXVK direct relative branch decoder self-test failed: "
                f"rva=0x{instruction_rva:08X} bytes={hex_bytes} "
                f"expected=0x{expected_target_rva:08X} "
                f"actual={actual_target_rva!r}"
            )
    if _decode_direct_relative_branch_target(0x00183000, b"\x90") is not None:
        raise SystemExit(
            "DXVK direct relative branch decoder misclassified non-branch opcode"
        )


def verify_dxvk_continuation_chain() -> None:
    """Auto-discover and fail closed if canonical continuation capture/proof edges drift apart."""

    _verify_direct_relative_branch_decoder()

    analyzer_path = ROOT / "tools/analyze_outrun_exe.py"
    analyzer_source = analyzer_path.read_text(encoding="utf-8")
    analyzer = runpy.run_path(
        str(analyzer_path),
        run_name="dxvk_disasm_contract_analyzer",
    )

    def value(name: str):
        if name not in analyzer:
            raise SystemExit(f"DXVK continuation chain missing analyzer symbol: {name}")
        return analyzer[name]

    def function_source(name: str) -> str:
        marker = f"def {name}("
        start = analyzer_source.find(marker)
        if start < 0:
            raise SystemExit(f"DXVK continuation collector source missing: {name}")
        end = analyzer_source.find("\ndef ", start + len(marker))
        if end < 0:
            end = len(analyzer_source)
        return analyzer_source[start:end]

    symbol_prefix = "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_"
    discovered_raw_ids: set[int] = set()
    for name in analyzer:
        if not name.startswith(symbol_prefix):
            continue
        tail = name[len(symbol_prefix):]
        continuation_text, separator, suffix = tail.partition("_")
        if (
            separator
            and suffix == "RVA"
            and continuation_text.isdigit()
            and int(continuation_text) >= 23
        ):
            discovered_raw_ids.add(int(continuation_text))

    raw_ids = tuple(sorted(discovered_raw_ids))
    if not raw_ids or raw_ids[0] != 23:
        raise SystemExit(
            f"DXVK continuation chain discovery lost baseline 23: {raw_ids}"
        )
    expected_raw_ids = tuple(range(raw_ids[0], raw_ids[-1] + 1))
    if raw_ids != expected_raw_ids:
        raise SystemExit(
            f"DXVK continuation chain has missing raw stages: "
            f"discovered={raw_ids} expected={expected_raw_ids}"
        )

    for continuation_id in raw_ids:
        prefix = f"{symbol_prefix}{continuation_id}"
        provenance_collector_name = (
            f"collect_guarded_gf_target_c_helper_1_third_callee_continuation_"
            f"{continuation_id}_provenance"
        )
        provenance_collector = analyzer.get(provenance_collector_name)
        if not callable(provenance_collector):
            raise SystemExit(
                f"DXVK continuation {continuation_id} is missing its provenance collector"
            )
        provenance_source = function_source(provenance_collector_name)
        provenance_ast = ast.parse(provenance_source)

        # Keep raw evidence collection pinned to the exact continuation window.
        # A collector can otherwise preserve a fail-closed captured predicate while
        # accidentally reading probe/call-census bytes from a stale RVA or length.
        # This is the raw provenance collector address coupling contract.
        def single_assignment_value(local_name: str) -> ast.AST:
            values = [
                node.value
                for node in ast.walk(provenance_ast)
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == local_name
                    for target in node.targets
                )
            ]
            if len(values) != 1:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw provenance has ambiguous "
                    f"{local_name} assignment: assignments={len(values)}"
                )
            return values[0]

        def is_name(node: ast.AST, expected: str) -> bool:
            return isinstance(node, ast.Name) and node.id == expected

        probe_expr = single_assignment_value("probe")
        expected_probe_len_name = f"{prefix}_PROBE_LEN"
        probe_args_ok = bool(
            isinstance(probe_expr, ast.Call)
            and isinstance(probe_expr.func, ast.Attribute)
            and isinstance(probe_expr.func.value, ast.Name)
            and probe_expr.func.value.id == "pe"
            and probe_expr.func.attr == "bytes_at_rva"
            and len(probe_expr.args) == 2
            and not probe_expr.keywords
            and is_name(probe_expr.args[0], "target_rva")
            and is_name(probe_expr.args[1], expected_probe_len_name)
        )
        if not probe_args_ok:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw provenance probe is not "
                "address-coupled to target_rva and its exact PROBE_LEN symbol"
            )

        # The captured predicate already requires probe_end_matches, but that
        # intermediate value must itself prove the exact capture geometry.
        # Otherwise a collector could assign probe_end_matches = True and still
        # satisfy every downstream gate while silently severing PROBE_END_RVA
        # from target_rva + len(probe).
        probe_end_expr = single_assignment_value("probe_end_matches")
        expected_probe_end_name = f"{prefix}_PROBE_END_RVA"
        probe_end_geometry_ok = bool(
            isinstance(probe_end_expr, ast.Compare)
            and len(probe_end_expr.ops) == 1
            and isinstance(probe_end_expr.ops[0], ast.Eq)
            and len(probe_end_expr.comparators) == 1
            and isinstance(probe_end_expr.left, ast.BinOp)
            and isinstance(probe_end_expr.left.op, ast.Add)
            and is_name(probe_end_expr.left.left, "target_rva")
            and isinstance(probe_end_expr.left.right, ast.Call)
            and isinstance(probe_end_expr.left.right.func, ast.Name)
            and probe_end_expr.left.right.func.id == "len"
            and len(probe_end_expr.left.right.args) == 1
            and not probe_end_expr.left.right.keywords
            and is_name(probe_end_expr.left.right.args[0], "probe")
            and is_name(probe_end_expr.comparators[0], expected_probe_end_name)
        )
        if not probe_end_geometry_ok:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw provenance probe_end_matches is not exact capture geometry: "
                f"expected=target_rva+len(probe)=={expected_probe_end_name}"
            )

        inbound_expr = single_assignment_value("inbound")
        inbound_args_ok = bool(
            isinstance(inbound_expr, ast.Call)
            and isinstance(inbound_expr.func, ast.Name)
            and inbound_expr.func.id == "collect_raw_inbound_rel32_candidates"
            and len(inbound_expr.args) == 2
            and not inbound_expr.keywords
            and is_name(inbound_expr.args[0], "pe")
            and is_name(inbound_expr.args[1], "target_rva")
        )
        if not inbound_args_ok:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw inbound census is not "
                "address-coupled to target_rva"
            )

        outbound_expr = single_assignment_value("outbound")
        outbound_args_ok = bool(
            isinstance(outbound_expr, ast.Call)
            and isinstance(outbound_expr.func, ast.Name)
            and outbound_expr.func.id == "collect_raw_rel32_call_candidates"
            and len(outbound_expr.args) == 3
            and not outbound_expr.keywords
            and is_name(outbound_expr.args[0], "pe")
            and is_name(outbound_expr.args[1], "target_rva")
            and is_name(outbound_expr.args[2], expected_probe_len_name)
        )
        if not outbound_args_ok:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw outbound census is not "
                "address-coupled to target_rva and its exact PROBE_LEN symbol"
            )
        conservative_raw_markers = (
            '"semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY"',
            '"call_semantics": "UNRESOLVED"',
            '"ownership_effect": "NONE"',
        )
        missing_raw_markers = [
            marker for marker in conservative_raw_markers
            if marker not in provenance_source
        ]
        if missing_raw_markers:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw provenance escaped "
                f"conservative semantic quarantine: {missing_raw_markers}"
            )

        # Keep emitted raw evidence tied to the same local values validated by
        # the collector. This prevents a fail-closed captured predicate from
        # coexisting with stale target/predecessor/census fields in CI output.
        raw_evidence_result_markers = (
            '"target_rva": target_rva',
            '"target_section": target_section',
            '"predecessor_status": predecessor["status"]',
            '"predecessor_exact": predecessor_exact',
            '"probe_end_matches": probe_end_matches',
            '"bytes": probe.hex(" ")',
            '"raw_inbound_rel32_candidates": inbound',
            '"raw_outbound_rel32_candidates": outbound',
        )
        missing_raw_evidence_bindings = [
            marker for marker in raw_evidence_result_markers
            if marker not in provenance_source
        ]
        if missing_raw_evidence_bindings:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw provenance evidence result drift: "
                f"{missing_raw_evidence_bindings}"
            )

        capture_integrity_markers = (
            "predecessor_exact",
            '"predecessor_exact": predecessor_exact',
            'target_section == ".text"',
            "len(probe) ==",
            "probe_end_matches",
            "captured = bool(",
        )
        missing_capture_integrity_markers = [
            marker for marker in capture_integrity_markers
            if marker not in provenance_source
        ]
        if missing_capture_integrity_markers:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw provenance lost capture-integrity gate: "
                f"{missing_capture_integrity_markers}"
            )
        captured_gate_names = _final_captured_gate_names(provenance_source)
        assigned_names = _function_assignment_names(provenance_source)
        mandatory_captured_gates = {
            "predecessor_exact",
            "target_section",
            "probe",
            "probe_end_matches",
        }
        conditional_captured_gates = {
            "overlap_matches",
            "predecessor_overlap_matches",
        }
        required_captured_gates = (
            mandatory_captured_gates
            | (assigned_names & conditional_captured_gates)
        )
        missing_captured_gates = sorted(required_captured_gates - captured_gate_names)
        if missing_captured_gates:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw provenance captured status dropped "
                f"required fail-closed gates: {missing_captured_gates}"
            )
        raw_status_fail_closed_markers = (
            '"status"',
            "if captured",
            "else",
        )
        missing_raw_status_markers = [
            marker for marker in raw_status_fail_closed_markers
            if marker not in provenance_source
        ]
        if missing_raw_status_markers:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw provenance status is not fail-closed: "
                f"{missing_raw_status_markers}"
            )
        # DXVK raw predecessor_exact contract: the final captured gate already
        # depends on predecessor_exact, but that intermediate predicate must in
        # turn consume the predecessor proof's exact status and the geometry
        # that joins the two captures. Otherwise a future collector could keep
        # calling the right proof while accidentally replacing predecessor_exact
        # with a weaker predicate (or True) and silently break fail-closed chain
        # continuity.
        predecessor_exact_values = [
            node.value
            for node in ast.walk(provenance_ast)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "predecessor_exact"
                for target in node.targets
            )
        ]
        if len(predecessor_exact_values) != 1:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw provenance has ambiguous "
                f"predecessor_exact predicate: assignments={len(predecessor_exact_values)}"
            )
        predecessor_exact_value = predecessor_exact_values[0]

        def predecessor_field(node: ast.AST) -> str | None:
            if not (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == "predecessor"
            ):
                return None
            key = node.slice
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                return key.value
            return None

        predecessor_fields = {
            field
            for node in ast.walk(predecessor_exact_value)
            if (field := predecessor_field(node)) is not None
        }

        def has_predecessor_equality(field: str, other_name: str) -> bool:
            for node in ast.walk(predecessor_exact_value):
                if not (
                    isinstance(node, ast.Compare)
                    and len(node.ops) == 1
                    and isinstance(node.ops[0], ast.Eq)
                    and len(node.comparators) == 1
                ):
                    continue
                left, right = node.left, node.comparators[0]
                if (
                    predecessor_field(left) == field
                    and isinstance(right, ast.Name)
                    and right.id == other_name
                ) or (
                    predecessor_field(right) == field
                    and isinstance(left, ast.Name)
                    and left.id == other_name
                ):
                    return True
            return False

        def has_predecessor_status_equality() -> bool:
            for node in ast.walk(predecessor_exact_value):
                if not (
                    isinstance(node, ast.Compare)
                    and len(node.ops) == 1
                    and isinstance(node.ops[0], ast.Eq)
                    and len(node.comparators) == 1
                ):
                    continue
                left, right = node.left, node.comparators[0]
                if (
                    predecessor_field(left) == "status"
                    and isinstance(right, ast.Constant)
                    and isinstance(right.value, str)
                ) or (
                    predecessor_field(right) == "status"
                    and isinstance(left, ast.Constant)
                    and isinstance(left.value, str)
                ):
                    return True
            return False

        predecessor_status_values: set[str] = set()
        for node in ast.walk(predecessor_exact_value):
            if not (
                isinstance(node, ast.Compare)
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Eq)
                and len(node.comparators) == 1
            ):
                continue
            left, right = node.left, node.comparators[0]
            if (
                predecessor_field(left) == "status"
                and isinstance(right, ast.Constant)
                and isinstance(right.value, str)
            ):
                predecessor_status_values.add(right.value)
            elif (
                predecessor_field(right) == "status"
                and isinstance(left, ast.Constant)
                and isinstance(left.value, str)
            ):
                predecessor_status_values.add(left.value)
        if len(predecessor_status_values) != 1:
            raise SystemExit(
                f"DXVK continuation {continuation_id} predecessor_exact must compare "
                f"against exactly one predecessor status literal: "
                f"{sorted(predecessor_status_values)}"
            )

        # Keep raw provenance inherited predecessor forward-target lineage
        # fail-closed. Some captures carry unresolved branch targets across
        # one or more windows before an exact decode can promote them to
        # RESOLVED_PREDECESSOR_TARGET_RVAS. If a collector reports that carry,
        # predecessor_exact must consume the predecessor proof's
        # unresolved_forward_targets field and pin it to one explicit,
        # non-empty, unique integer literal sequence. This prevents a later
        # refactor from retaining the telemetry field while silently dropping
        # the lineage gate from canonical provenance acceptance.
        inherited_forward_return_values: list[ast.AST] = []
        for return_node in (
            node
            for node in ast.walk(provenance_ast)
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
        ):
            for key_node, value_node in zip(return_node.value.keys, return_node.value.values):
                if (
                    isinstance(key_node, ast.Constant)
                    and key_node.value == "inherited_predecessor_forward_targets"
                ):
                    inherited_forward_return_values.append(value_node)

        carries_inherited_forward_targets = bool(
            inherited_forward_return_values
            or "unresolved_forward_targets" in predecessor_fields
        )
        if carries_inherited_forward_targets:
            if len(inherited_forward_return_values) != 1:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw provenance inherited "
                    "forward-target telemetry is ambiguous or missing: "
                    f"bindings={len(inherited_forward_return_values)}"
                )
            if (
                predecessor_field(inherited_forward_return_values[0])
                != "unresolved_forward_targets"
            ):
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw provenance inherited "
                    "forward-target telemetry is not bound directly to predecessor "
                    "unresolved_forward_targets"
                )

            inherited_forward_equalities: list[ast.AST] = []
            for node in ast.walk(predecessor_exact_value):
                if not (
                    isinstance(node, ast.Compare)
                    and len(node.ops) == 1
                    and isinstance(node.ops[0], ast.Eq)
                    and len(node.comparators) == 1
                ):
                    continue
                left, right = node.left, node.comparators[0]
                if predecessor_field(left) == "unresolved_forward_targets":
                    inherited_forward_equalities.append(right)
                elif predecessor_field(right) == "unresolved_forward_targets":
                    inherited_forward_equalities.append(left)

            if len(inherited_forward_equalities) != 1:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw provenance predecessor_exact "
                    "must contain exactly one unresolved_forward_targets equality: "
                    f"comparisons={len(inherited_forward_equalities)}"
                )
            expected_targets_node = inherited_forward_equalities[0]
            if not isinstance(expected_targets_node, (ast.List, ast.Tuple, ast.Set)):
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw provenance inherited "
                    "forward-target gate must compare against an explicit int literal sequence"
                )
            expected_inherited_forward_targets = [
                element.value
                for element in expected_targets_node.elts
                if isinstance(element, ast.Constant)
                and isinstance(element.value, int)
                and not isinstance(element.value, bool)
            ]
            if (
                len(expected_inherited_forward_targets) != len(expected_targets_node.elts)
                or len(expected_inherited_forward_targets)
                != len(set(expected_inherited_forward_targets))
            ):
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw provenance inherited "
                    "forward-target gate must use a unique int literal sequence"
                )

        has_overlap_contract = f"{prefix}_OVERLAP_BYTES" in analyzer
        if has_overlap_contract:
            # Modern overlap collectors are canonical-evidence boundaries, so
            # verify their byte-geometry expressions structurally rather than
            # accepting matching source-text fragments. This prevents comments,
            # dead strings, or reassigned locals from satisfying the contract.
            if continuation_id >= 43:
                expected_overlap_name = f"{prefix}_OVERLAP_BYTES"
                overlap_expr = single_assignment_value("overlap")
                if not is_name(overlap_expr, expected_overlap_name):
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} overlap source is not "
                        f"bound directly to {expected_overlap_name}"
                    )

                overlap_actual_expr = single_assignment_value("overlap_actual")
                overlap_slice = (
                    overlap_actual_expr.slice
                    if isinstance(overlap_actual_expr, ast.Subscript)
                    else None
                )
                overlap_upper = (
                    overlap_slice.upper
                    if isinstance(overlap_slice, ast.Slice)
                    else None
                )
                overlap_actual_ok = bool(
                    isinstance(overlap_actual_expr, ast.Subscript)
                    and is_name(overlap_actual_expr.value, "probe")
                    and isinstance(overlap_slice, ast.Slice)
                    and overlap_slice.lower is None
                    and overlap_slice.step is None
                    and isinstance(overlap_upper, ast.Call)
                    and isinstance(overlap_upper.func, ast.Name)
                    and overlap_upper.func.id == "len"
                    and len(overlap_upper.args) == 1
                    and not overlap_upper.keywords
                    and is_name(overlap_upper.args[0], "overlap")
                )
                if not overlap_actual_ok:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} overlap_actual geometry is not "
                        "structurally bound to probe[:len(overlap)]"
                    )

                overlap_matches_expr = single_assignment_value("overlap_matches")
                overlap_matches_ok = bool(
                    isinstance(overlap_matches_expr, ast.Compare)
                    and len(overlap_matches_expr.ops) == 1
                    and isinstance(overlap_matches_expr.ops[0], ast.Eq)
                    and len(overlap_matches_expr.comparators) == 1
                    and (
                        (
                            is_name(overlap_matches_expr.left, "overlap_actual")
                            and is_name(overlap_matches_expr.comparators[0], "overlap")
                        )
                        or (
                            is_name(overlap_matches_expr.left, "overlap")
                            and is_name(overlap_matches_expr.comparators[0], "overlap_actual")
                        )
                    )
                )
                if not overlap_matches_ok:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} overlap_matches is not "
                        "an exact overlap_actual == overlap comparison"
                    )

                # predecessor_overlap_matches must be the exact conjunction of
                # predecessor expected/actual cut bytes against overlap.hex(" ").
                # Presence alone is insufficient: a literal True or unrelated
                # predicate would otherwise let captured provenance sever the
                # canonical predecessor byte-lineage contract.
                predecessor_overlap_expr = single_assignment_value(
                    "predecessor_overlap_matches"
                )

                def is_overlap_hex_call(node: ast.AST) -> bool:
                    return bool(
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "hex"
                        and is_name(node.func.value, "overlap")
                        and len(node.args) == 1
                        and isinstance(node.args[0], ast.Constant)
                        and node.args[0].value == " "
                        and not node.keywords
                    )

                def predecessor_overlap_field(node: ast.AST) -> str | None:
                    if not (
                        isinstance(node, ast.Compare)
                        and len(node.ops) == 1
                        and isinstance(node.ops[0], ast.Eq)
                        and len(node.comparators) == 1
                    ):
                        return None
                    left, right = node.left, node.comparators[0]
                    left_field = predecessor_field(left)
                    right_field = predecessor_field(right)
                    if left_field is not None and is_overlap_hex_call(right):
                        return left_field
                    if right_field is not None and is_overlap_hex_call(left):
                        return right_field
                    return None

                predecessor_overlap_fields = (
                    [
                        predecessor_overlap_field(value)
                        for value in predecessor_overlap_expr.values
                    ]
                    if isinstance(predecessor_overlap_expr, ast.BoolOp)
                    and isinstance(predecessor_overlap_expr.op, ast.And)
                    and len(predecessor_overlap_expr.values) == 2
                    else []
                )
                expected_predecessor_overlap_fields = {
                    "incomplete_expected_bytes",
                    "incomplete_actual_bytes",
                }
                if (
                    len(predecessor_overlap_fields) != 2
                    or None in predecessor_overlap_fields
                    or set(predecessor_overlap_fields)
                    != expected_predecessor_overlap_fields
                ):
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} "
                        "predecessor_overlap_matches is not structurally bound to "
                        "predecessor expected/actual incomplete bytes and overlap.hex(' ')"
                    )

            required_predecessor_fields = {"status", "incomplete_rva", "incomplete_matches"}
            # Continuation 43 introduced the modern mandatory-overlap contract:
            # the successor must consume the predecessor proof's capture-edge
            # predicate and independently bind the predecessor's exact cut bytes.
            # Treating these as optional lets a refactor delete either lineage
            # gate while retaining byte geometry and a superficially exact status.
            if continuation_id >= 43:
                required_predecessor_fields.add("capture_edge_matches")
                if "predecessor_overlap_matches" not in assigned_names:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} modern overlap provenance "
                        "lost predecessor_overlap_matches lineage gate"
                    )
            missing_predecessor_fields = sorted(
                required_predecessor_fields - predecessor_fields
            )
            if missing_predecessor_fields:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} overlap predecessor_exact lost "
                    f"cut-edge fields: {missing_predecessor_fields}"
                )
            if not has_predecessor_equality("incomplete_rva", "target_rva"):
                raise SystemExit(
                    f"DXVK continuation {continuation_id} overlap predecessor_exact does "
                    "not join predecessor incomplete_rva to target_rva"
                )
        else:
            required_predecessor_fields = {"status", "prefix_end_rva"}
            missing_predecessor_fields = sorted(
                required_predecessor_fields - predecessor_fields
            )
            if missing_predecessor_fields:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} boundary predecessor_exact lost "
                    f"capture-edge fields: {missing_predecessor_fields}"
                )
            if not has_predecessor_equality("prefix_end_rva", "target_rva"):
                raise SystemExit(
                    f"DXVK continuation {continuation_id} boundary predecessor_exact does "
                    "not join predecessor prefix_end_rva to target_rva"
                )
            boundary_fields = {
                "capture_end_is_instruction_boundary",
                "capture_boundary_matches",
            }
            if not (predecessor_fields & boundary_fields):
                raise SystemExit(
                    f"DXVK continuation {continuation_id} boundary predecessor_exact lost "
                    "its proven instruction/capture-boundary gate"
                )

        if continuation_id > raw_ids[0]:
            predecessor_id = continuation_id - 1
            predecessor_proof_collector_name = (
                "collect_guarded_gf_target_c_helper_1_third_callee_continuation_"
                f"{predecessor_id}_prefix_proof"
            )
            expected_predecessor_call = f"{predecessor_proof_collector_name}(pe)"
            predecessor_proof_calls = provenance_source.count(expected_predecessor_call)
            if predecessor_proof_calls != 1:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw provenance consumes wrong predecessor proof: "
                    f"expected={expected_predecessor_call} proof_calls={predecessor_proof_calls}"
                )

            predecessor_proof_source = function_source(predecessor_proof_collector_name)
            predecessor_proof_ast = ast.parse(predecessor_proof_source)
            predecessor_success_statuses: list[str] = []
            for return_node in (
                node
                for node in ast.walk(predecessor_proof_ast)
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
            ):
                for key_node, value_node in zip(return_node.value.keys, return_node.value.values):
                    if not (
                        isinstance(key_node, ast.Constant)
                        and key_node.value == "status"
                        and isinstance(value_node, ast.IfExp)
                        and isinstance(value_node.test, ast.Name)
                        and value_node.test.id == "proven"
                        and isinstance(value_node.body, ast.Constant)
                        and isinstance(value_node.body.value, str)
                    ):
                        continue
                    predecessor_success_statuses.append(value_node.body.value)
            if len(predecessor_success_statuses) != 1:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} cannot derive exactly one "
                    f"success status from predecessor proof {predecessor_id}: "
                    f"{predecessor_success_statuses}"
                )
            expected_predecessor_status = predecessor_success_statuses[0]
            if predecessor_status_values != {expected_predecessor_status}:
                raise SystemExit(
                    f"DXVK continuation predecessor status does not match predecessor proof success: "
                    f"continuation={continuation_id} "
                    f"expected={expected_predecessor_status!r} "
                    f"actual={sorted(predecessor_status_values)!r}"
                )

            # F62/continuation 65 and later: when the predecessor proof carries
            # unresolved forward branch targets, the next raw collector must
            # preserve that control-flow debt in both its fail-closed
            # predecessor_exact predicate and emitted raw evidence. Without
            # this guard a new 64-byte capture could remain byte/geometry exact
            # while silently forgetting branch targets that still need boundary
            # resolution in a later exact proof.
            if continuation_id >= 65:
                predecessor_return_keys: set[str] = set()
                predecessor_unresolved_forward_values: list[ast.AST] = []
                for return_node in (
                    node
                    for node in ast.walk(predecessor_proof_ast)
                    if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
                ):
                    for key_node, value_node in zip(
                        return_node.value.keys, return_node.value.values
                    ):
                        if (
                            isinstance(key_node, ast.Constant)
                            and isinstance(key_node.value, str)
                        ):
                            predecessor_return_keys.add(key_node.value)
                            if key_node.value == "unresolved_forward_targets":
                                predecessor_unresolved_forward_values.append(value_node)

                if len(predecessor_unresolved_forward_values) > 1:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} predecessor proof has ambiguous "
                        "unresolved_forward_targets return bindings: "
                        f"{len(predecessor_unresolved_forward_values)}"
                    )

                # Presence of the field is itself lineage state, including an
                # explicitly empty list. Successors must consume and emit that
                # state so a proved-empty debt cannot silently disappear and
                # later be confused with a collector that never checked it.
                predecessor_declares_forward_lineage = bool(
                    predecessor_unresolved_forward_values
                )

                if predecessor_declares_forward_lineage:
                    # Bind the raw collector's inherited-target predicate to the predecessor proof.
                    # Both sides were already checked for shape independently; this equality
                    # prevents a stale explicit target list from remaining statically green.
                    predecessor_forward_node = predecessor_unresolved_forward_values[0]
                    if isinstance(predecessor_forward_node, ast.Name):
                        predecessor_forward_assignments = [
                            node.value
                            for node in ast.walk(predecessor_proof_ast)
                            if isinstance(node, ast.Assign)
                            and any(
                                isinstance(target, ast.Name)
                                and target.id == predecessor_forward_node.id
                                for target in node.targets
                            )
                        ]
                        if len(predecessor_forward_assignments) != 1:
                            raise SystemExit(
                                f"DXVK continuation {continuation_id} predecessor proof "
                                "forward-target lineage assignment is ambiguous: "
                                f"{predecessor_forward_node.id}="
                                f"{len(predecessor_forward_assignments)}"
                            )
                        predecessor_forward_node = predecessor_forward_assignments[0]
                    if not isinstance(
                        predecessor_forward_node, (ast.List, ast.Tuple, ast.Set)
                    ):
                        raise SystemExit(
                            f"DXVK continuation {continuation_id} predecessor proof "
                            "forward-target lineage must resolve to an explicit int sequence"
                        )
                    predecessor_forward_targets = [
                        element.value
                        for element in predecessor_forward_node.elts
                        if isinstance(element, ast.Constant)
                        and isinstance(element.value, int)
                        and not isinstance(element.value, bool)
                    ]
                    if (
                        len(predecessor_forward_targets)
                        != len(predecessor_forward_node.elts)
                        or len(predecessor_forward_targets)
                        != len(set(predecessor_forward_targets))
                    ):
                        raise SystemExit(
                            f"DXVK continuation {continuation_id} predecessor proof "
                            "forward-target lineage must use a unique int literal sequence"
                        )

                    raw_forward_gate_nodes: list[ast.AST] = []
                    for node in ast.walk(predecessor_exact_value):
                        if not (
                            isinstance(node, ast.Compare)
                            and len(node.ops) == 1
                            and isinstance(node.ops[0], ast.Eq)
                            and len(node.comparators) == 1
                        ):
                            continue
                        left, right = node.left, node.comparators[0]
                        if predecessor_field(left) == "unresolved_forward_targets":
                            raw_forward_gate_nodes.append(right)
                        elif predecessor_field(right) == "unresolved_forward_targets":
                            raw_forward_gate_nodes.append(left)
                    if len(raw_forward_gate_nodes) != 1:
                        raise SystemExit(
                            f"DXVK continuation {continuation_id} raw provenance "
                            "forward-target lineage gate is ambiguous: "
                            f"{len(raw_forward_gate_nodes)}"
                        )
                    raw_forward_node = raw_forward_gate_nodes[0]
                    if not isinstance(raw_forward_node, (ast.List, ast.Tuple, ast.Set)):
                        raise SystemExit(
                            f"DXVK continuation {continuation_id} raw provenance "
                            "forward-target lineage gate must be an explicit int sequence"
                        )
                    raw_forward_targets = [
                        element.value
                        for element in raw_forward_node.elts
                        if isinstance(element, ast.Constant)
                        and isinstance(element.value, int)
                        and not isinstance(element.value, bool)
                    ]
                    if raw_forward_targets != predecessor_forward_targets:
                        raise SystemExit(
                            f"DXVK continuation {continuation_id} predecessor proof "
                            "forward-target lineage drift: "
                            f"proof={predecessor_forward_targets} "
                            f"raw_gate={raw_forward_targets}"
                        )

                    unresolved_forward_target_compared = any(
                        isinstance(node, ast.Compare)
                        and len(node.ops) == 1
                        and isinstance(node.ops[0], ast.Eq)
                        and len(node.comparators) == 1
                        and (
                            predecessor_field(node.left) == "unresolved_forward_targets"
                            or predecessor_field(node.comparators[0])
                                == "unresolved_forward_targets"
                        )
                        for node in ast.walk(predecessor_exact_value)
                    )
                    if not unresolved_forward_target_compared:
                        raise SystemExit(
                            f"DXVK continuation {continuation_id} raw provenance dropped unresolved forward-target carry "
                            "from predecessor_exact"
                        )

                    inherited_target_bindings: list[str] = []
                    for return_node in (
                        node
                        for node in ast.walk(provenance_ast)
                        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
                    ):
                        for key_node, value_node in zip(
                            return_node.value.keys, return_node.value.values
                        ):
                            if (
                                isinstance(key_node, ast.Constant)
                                and isinstance(key_node.value, str)
                                and predecessor_field(value_node)
                                    == "unresolved_forward_targets"
                            ):
                                inherited_target_bindings.append(key_node.value)
                    if len(inherited_target_bindings) != 1:
                        raise SystemExit(
                            f"DXVK continuation {continuation_id} raw provenance must emit exactly one "
                            "inherited unresolved-forward-target evidence field: "
                            f"bindings={inherited_target_bindings}"
                        )
        provenance_name = (
            f"guarded_gf_target_c_helper_1_third_callee_continuation_"
            f"{continuation_id}_provenance"
        )
        provenance_report_binding = (
            f'"{provenance_name}": '
            f"collect_guarded_gf_target_c_helper_1_third_callee_continuation_"
            f"{continuation_id}_provenance(pe)"
        )
        if provenance_report_binding not in analyzer_source:
            raise SystemExit(
                f"DXVK continuation {continuation_id} missing analyzer report binding"
            )
        if f"{provenance_name}=FAILED" not in analyzer_source:
            raise SystemExit(
                f"DXVK continuation {continuation_id} missing analyzer failure guard"
            )
        raw_success_marker = (
            f"gf_target_c_helper_1_third_callee_continuation_{continuation_id}="
        )
        if raw_success_marker not in analyzer_source:
            raise SystemExit(
                f"DXVK continuation {continuation_id} missing analyzer success telemetry"
            )
        start = value(f"{prefix}_RVA")
        probe_len = value(f"{prefix}_PROBE_LEN")
        probe_end = value(f"{prefix}_PROBE_END_RVA")
        if probe_len != 64:
            raise SystemExit(
                f"DXVK continuation {continuation_id} must retain the canonical 64-byte bounded probe: "
                f"got {probe_len}"
            )
        if start + probe_len != probe_end:
            raise SystemExit(
                f"DXVK continuation {continuation_id} probe geometry drift: "
                f"0x{start:08X}+{probe_len} != 0x{probe_end:08X}"
            )

    proof_ids = tuple(
        continuation_id
        for continuation_id in raw_ids
        if (
            f"GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_"
            f"{continuation_id}_PREFIX_END_RVA"
        ) in analyzer
    )
    if not proof_ids or proof_ids[0] != raw_ids[0]:
        raise SystemExit(
            f"DXVK continuation proof discovery lost baseline {raw_ids[0]}: {proof_ids}"
        )
    expected_proof_ids = tuple(range(raw_ids[0], proof_ids[-1] + 1))
    if proof_ids != expected_proof_ids:
        raise SystemExit(
            f"DXVK continuation chain has missing proof stages: "
            f"discovered={proof_ids} expected={expected_proof_ids}"
        )
    if raw_ids[-1] - proof_ids[-1] > 1:
        raise SystemExit(
            f"DXVK continuation chain has more than one unproved raw frontier: "
            f"raw={raw_ids[-1]} proof={proof_ids[-1]}"
        )

    cut_edge_ids: list[int] = []
    for continuation_id in proof_ids:
        prefix = f"{symbol_prefix}{continuation_id}"
        proof_collector_name = (
            f"collect_guarded_gf_target_c_helper_1_third_callee_continuation_"
            f"{continuation_id}_prefix_proof"
        )
        proof_collector = analyzer.get(proof_collector_name)
        if not callable(proof_collector):
            raise SystemExit(
                f"DXVK continuation {continuation_id} is missing its prefix-proof collector"
            )
        proof_source = function_source(proof_collector_name)
        if '"ownership_effect": "NONE"' not in proof_source:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof unexpectedly promotes ownership"
            )
        semantic_effect_match = re.search(
            r'"semantic_effect"\s*:\s*"([^"]+)"',
            proof_source,
        )
        if semantic_effect_match is None:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof lost semantic-effect quarantine"
            )
        semantic_effect = semantic_effect_match.group(1)
        if not (
            semantic_effect.startswith("BOUNDED_CONTROL_FLOW")
            and semantic_effect.endswith("_ONLY")
        ):
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof escaped bounded control-flow semantic quarantine: "
                f"{semantic_effect}"
            )
        raw_call_census_guards = [
            marker
            for marker in ("raw_call_census_matches", "raw_call_census_empty")
            if marker in proof_source
        ]
        if len(raw_call_census_guards) != 1:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof lost exhaustive raw-call census gate: "
                f"{raw_call_census_guards}"
            )
        raw_call_census_guard = raw_call_census_guards[0]
        proof_ast = ast.parse(proof_source)
        proven_assignments = [
            node
            for node in ast.walk(proof_ast)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "proven"
                for target in node.targets
            )
        ]
        if len(proven_assignments) != 1:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof has ambiguous proven predicate: "
                f"assignments={len(proven_assignments)}"
            )
        proven_names = {
            node.id
            for node in ast.walk(proven_assignments[0].value)
            if isinstance(node, ast.Name)
        }
        if raw_call_census_guard not in proven_names:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof does not gate proven status on "
                f"{raw_call_census_guard}"
            )
        raw_call_census_result_binding = (
            f'"{raw_call_census_guard}": {raw_call_census_guard}'
        )
        if raw_call_census_result_binding not in proof_source:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof does not report "
                f"{raw_call_census_guard}"
            )

        # Keep the exhaustive raw-call census predicate source-coupled to the
        # raw provenance it is supposed to validate. Requiring the gate name in
        # proven is insufficient if a later refactor can replace the predicate
        # with True or compare unrelated locals. Empty-census proofs must negate
        # the provenance call-candidate list directly. Non-empty proofs must
        # build their expected set from this continuation's CALLS declaration,
        # build observed_raw_calls from the provenance candidate list, and make
        # the final census predicate compare expected calls with an observed set.
        census_assignments = [
            node.value
            for node in ast.walk(proof_ast)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == raw_call_census_guard
                for target in node.targets
            )
        ]
        if len(census_assignments) != 1:
            raise SystemExit(
                f"DXVK continuation {continuation_id} raw-call census predicate is not source-coupled: "
                f"{raw_call_census_guard} assignments={len(census_assignments)}"
            )
        census_expr = census_assignments[0]

        def provenance_field(node: ast.AST) -> str | None:
            if not (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == "provenance"
            ):
                return None
            key = node.slice
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                return key.value
            return None

        if raw_call_census_guard == "raw_call_census_empty":
            if not (
                isinstance(census_expr, ast.UnaryOp)
                and isinstance(census_expr.op, ast.Not)
                and provenance_field(census_expr.operand)
                    == "raw_outbound_rel32_candidates"
            ):
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw-call census predicate is not source-coupled: "
                    "raw_call_census_empty must directly negate provenance raw_outbound_rel32_candidates"
                )
        else:
            expected_call_assignments = [
                node.value
                for node in ast.walk(proof_ast)
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name)
                    and target.id == "expected_raw_calls"
                    for target in node.targets
                )
            ]
            observed_call_assignments = [
                node.value
                for node in ast.walk(proof_ast)
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name)
                    and target.id == "observed_raw_calls"
                    for target in node.targets
                )
            ]
            expected_calls_symbol = f"{prefix}_CALLS"
            expected_source_ok = bool(
                len(expected_call_assignments) == 1
                and isinstance(expected_call_assignments[0], ast.Call)
                and isinstance(expected_call_assignments[0].func, ast.Name)
                and expected_call_assignments[0].func.id == "set"
                and len(expected_call_assignments[0].args) == 1
                and not expected_call_assignments[0].keywords
                and isinstance(expected_call_assignments[0].args[0], ast.Name)
                and expected_call_assignments[0].args[0].id == expected_calls_symbol
            )
            if not expected_source_ok:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw-call census predicate is not source-coupled: "
                    f"expected_raw_calls must be set({expected_calls_symbol})"
                )

            observed_source_ok = bool(
                len(observed_call_assignments) == 1
                and isinstance(observed_call_assignments[0], ast.SetComp)
                and any(
                    provenance_field(node) == "raw_outbound_rel32_candidates"
                    for node in ast.walk(observed_call_assignments[0])
                )
            )
            if not observed_source_ok:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw-call census predicate is not source-coupled: "
                    "observed_raw_calls must derive from provenance raw_outbound_rel32_candidates"
                )

            census_names = {
                node.id
                for node in ast.walk(census_expr)
                if isinstance(node, ast.Name)
            }
            census_has_equality = any(
                isinstance(node, ast.Compare)
                and any(isinstance(op, ast.Eq) for op in node.ops)
                for node in ast.walk(census_expr)
            )
            observed_census_names = {
                name for name in census_names if name.startswith("observed_")
            }
            if (
                "expected_raw_calls" not in census_names
                or not observed_census_names
                or not census_has_equality
            ):
                raise SystemExit(
                    f"DXVK continuation {continuation_id} raw-call census predicate is not source-coupled: "
                    f"names={sorted(census_names)}"
                )

        # Keep declared direct relative BRANCH metadata tied to the exact
        # decoded instruction rows. This catches off-by-one/stale branch RVAs,
        # omitted direct branches, and target-displacement drift before the
        # canonical-EXE execution stage. Decode direct relative branch forms
        # including legacy-prefixed rel8 Jcc/JMP/LOOP-family instructions and
        # operand/address-size-prefixed near Jcc/JMP encodings.
        instruction_rows = value(f"{prefix}_INSTRUCTIONS")

        # Validate the declared instruction tuple geometry before canonical-EXE
        # execution. Proof collectors gate their runtime status on contiguous
        # rows, but stale/gapped/overlapping metadata should fail the static
        # contract immediately instead of waiting for the evidence workflow.
        declared_start_rva = value(f"{prefix}_RVA")
        declared_prefix_end_rva = value(f"{prefix}_PREFIX_END_RVA")
        declared_instruction_end_rva = analyzer.get(
            f"{prefix}_INSTRUCTION_END_RVA",
            declared_prefix_end_rva,
        )
        if not instruction_rows:
            raise SystemExit(
                f"DXVK continuation {continuation_id} has no exact instruction rows"
            )
        static_next_rva = declared_start_rva
        static_instruction_rvas: set[int] = set()
        for instruction_rva, instruction_hex, _instruction_asm in instruction_rows:
            if instruction_rva in static_instruction_rvas:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} declares duplicate instruction RVA "
                    f"0x{instruction_rva:08X}"
                )
            static_instruction_rvas.add(instruction_rva)
            try:
                encoded = bytes.fromhex(instruction_hex)
            except ValueError as exc:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} has invalid instruction hex at "
                    f"0x{instruction_rva:08X}: {instruction_hex!r}"
                ) from exc
            if not encoded:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} has empty instruction bytes at "
                    f"0x{instruction_rva:08X}"
                )
            if instruction_rva != static_next_rva:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} instruction geometry drift: "
                    f"expected=0x{static_next_rva:08X} actual=0x{instruction_rva:08X}"
                )
            static_next_rva = instruction_rva + len(encoded)
        if static_next_rva != declared_instruction_end_rva:
            raise SystemExit(
                f"DXVK continuation {continuation_id} instruction geometry end drift: "
                f"decoded_end=0x{static_next_rva:08X} "
                f"instruction_end=0x{declared_instruction_end_rva:08X}"
            )

        padding_names = (
            f"{prefix}_PADDING_RVA",
            f"{prefix}_PADDING_LEN",
        )
        padding_presence = [name in analyzer for name in padding_names]
        if any(padding_presence) and not all(padding_presence):
            raise SystemExit(
                f"DXVK continuation {continuation_id} has a half-defined padding contract"
            )
        if all(padding_presence):
            padding_rva = value(padding_names[0])
            padding_len = value(padding_names[1])
            if padding_len <= 0:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} has non-positive padding length "
                    f"{padding_len}"
                )
            if declared_instruction_end_rva != padding_rva:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} padding does not start at the "
                    f"instruction end: instruction_end=0x{declared_instruction_end_rva:08X} "
                    f"padding_rva=0x{padding_rva:08X}"
                )
            if padding_rva + padding_len != declared_prefix_end_rva:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} padding geometry end drift: "
                    f"padding_end=0x{padding_rva + padding_len:08X} "
                    f"prefix_end=0x{declared_prefix_end_rva:08X}"
                )
        elif declared_instruction_end_rva != declared_prefix_end_rva:
            raise SystemExit(
                f"DXVK continuation {continuation_id} instruction end differs from prefix "
                "end without an explicit padding contract"
            )

        # Some exact windows (notably F44/F45) contain code, a long INT3
        # alignment span, and then more code inside one canonical capture. Those
        # bytes are represented as one-byte instruction rows so the generic
        # geometry remains contiguous. Treat runs of four or more INT3 rows as
        # structural padding and fail closed unless fallthrough was already
        # terminated before the run. Canonical all_bytes_match then proves the
        # padding bytes themselves, while this guard proves the control-flow
        # shape around them.
        internal_int3_padding_spans: list[tuple[int, int]] = []
        int3_run_start: int | None = None
        for row_index, (_rva, instruction_hex, _asm) in enumerate(instruction_rows):
            is_int3 = bytes.fromhex(instruction_hex) == b"\xCC"
            if is_int3 and int3_run_start is None:
                int3_run_start = row_index
            if not is_int3 and int3_run_start is not None:
                if row_index - int3_run_start >= 4:
                    internal_int3_padding_spans.append((int3_run_start, row_index))
                int3_run_start = None
        if int3_run_start is not None:
            if len(instruction_rows) - int3_run_start >= 4:
                internal_int3_padding_spans.append(
                    (int3_run_start, len(instruction_rows))
                )

        for run_start_index, run_end_index in internal_int3_padding_spans:
            if run_start_index == 0:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} long INT3 padding starts "
                    "without a preceding terminal instruction"
                )
            previous_encoded = bytes.fromhex(
                instruction_rows[run_start_index - 1][1]
            )
            previous_is_non_fallthrough = bool(
                previous_encoded[:1] in (b"\xC2", b"\xC3", b"\xE9", b"\xEB")
                or previous_encoded == b"\x0F\x0B"
            )
            if not previous_is_non_fallthrough:
                run_start_rva = instruction_rows[run_start_index][0]
                raise SystemExit(
                    f"DXVK continuation {continuation_id} long INT3 padding at "
                    f"0x{run_start_rva:08X} is reachable by fallthrough"
                )
            run_start_rva = instruction_rows[run_start_index][0]
            last_padding_rva = instruction_rows[run_end_index - 1][0]
            run_end_rva = last_padding_rva + 1
            if run_end_index < len(instruction_rows):
                next_code_rva = instruction_rows[run_end_index][0]
                if next_code_rva != run_end_rva:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} INT3 padding/code "
                        f"boundary drift: padding_end=0x{run_end_rva:08X} "
                        f"next_code=0x{next_code_rva:08X}"
                    )

        declared_branches = analyzer.get(f"{prefix}_BRANCHES", ())
        direct_branch_rows: dict[int, tuple[bytes, int]] = {}
        for instruction_rva, instruction_hex, _instruction_asm in instruction_rows:
            encoded = bytes.fromhex(instruction_hex)
            decoded_target_rva = _decode_direct_relative_branch_target(
                instruction_rva, encoded
            )
            if decoded_target_rva is not None:
                direct_branch_rows[instruction_rva] = (encoded, decoded_target_rva)

        declared_branch_rvas = [
            branch_rva for branch_rva, _target_rva in declared_branches
        ]
        if len(declared_branch_rvas) != len(set(declared_branch_rvas)):
            raise SystemExit(
                f"DXVK continuation {continuation_id} declares duplicate direct BRANCH RVAs: "
                f"{declared_branch_rvas}"
            )
        if set(direct_branch_rows) != set(declared_branch_rvas):
            raise SystemExit(
                f"DXVK continuation {continuation_id} direct BRANCH declaration drift: "
                f"instruction_rvas={sorted(direct_branch_rows)} "
                f"declared_rvas={sorted(declared_branch_rvas)}"
            )
        for branch_rva, expected_target_rva in declared_branches:
            _encoded, decoded_target_rva = direct_branch_rows[branch_rva]
            if decoded_target_rva != expected_target_rva:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} direct BRANCH target drift at "
                    f"0x{branch_rva:08X}: declared=0x{expected_target_rva:08X} "
                    f"decoded=0x{decoded_target_rva:08X}"
                )

        # If a proof names its expected external branch-target set, validate
        # that declaration immediately against the exact decoded BRANCH metadata.
        # Previously this declaration was consumed primarily by the successor
        # handoff check, so the newest frontier could carry a stale set until a
        # later continuation existed. Keep the current proof fail-closed too.
        current_external_assignments = [
            node.value
            for node in ast.walk(proof_ast)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "expected_external_targets"
                for target in node.targets
            )
        ]
        if len(current_external_assignments) > 1:
            raise SystemExit(
                f"DXVK continuation {continuation_id} current proof has ambiguous "
                "expected_external_targets assignments: "
                f"{len(current_external_assignments)}"
            )
        if current_external_assignments:
            external_node = current_external_assignments[0]
            if isinstance(external_node, ast.Set):
                declared_expected_external_targets = {
                    element.value
                    for element in external_node.elts
                    if (
                        isinstance(element, ast.Constant)
                        and isinstance(element.value, int)
                        and not isinstance(element.value, bool)
                    )
                }
                if len(declared_expected_external_targets) != len(external_node.elts):
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} current proof "
                        "expected_external_targets is not an int literal set"
                    )
            elif (
                isinstance(external_node, ast.Call)
                and isinstance(external_node.func, ast.Name)
                and external_node.func.id == "set"
                and not external_node.args
                and not external_node.keywords
            ):
                declared_expected_external_targets = set()
            else:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} current proof "
                    "expected_external_targets must be a literal int set"
                )

            current_start = value(f"{prefix}_RVA")
            current_end = value(f"{prefix}_PREFIX_END_RVA")
            decoded_external_targets = {
                target_rva
                for _branch_rva, target_rva in declared_branches
                if not (current_start <= target_rva < current_end)
            }
            if declared_expected_external_targets != decoded_external_targets:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} current proof "
                    "expected_external_targets declaration drift: "
                    f"declared={sorted(declared_expected_external_targets)} "
                    f"decoded={sorted(decoded_external_targets)}"
                )

        padding_target_hits = [
            (branch_rva, target_rva, instruction_rows[run_start][0], instruction_rows[run_end - 1][0] + 1)
            for branch_rva, target_rva in declared_branches
            for run_start, run_end in internal_int3_padding_spans
            if instruction_rows[run_start][0]
            <= target_rva
            < instruction_rows[run_end - 1][0] + 1
        ]
        if padding_target_hits:
            raise SystemExit(
                f"DXVK continuation {continuation_id} direct BRANCH enters long INT3 "
                f"padding: {padding_target_hits}"
            )

        # Keep declared direct rel32 CALL metadata tied to the exact decoded
        # instruction rows. This catches off-by-one CALL RVAs or stale targets
        # before canonical-EXE execution reaches telemetry formatting/census.
        declared_calls = analyzer.get(f"{prefix}_CALLS", ())
        direct_rel32_rows: dict[int, bytes] = {}
        for instruction_rva, instruction_hex, _instruction_asm in instruction_rows:
            encoded = bytes.fromhex(instruction_hex)
            if encoded[:1] == b"\xE8":
                direct_rel32_rows[instruction_rva] = encoded
        declared_call_rvas = [call_rva for call_rva, _target_rva in declared_calls]
        if len(declared_call_rvas) != len(set(declared_call_rvas)):
            raise SystemExit(
                f"DXVK continuation {continuation_id} declares duplicate rel32 CALL RVAs: "
                f"{declared_call_rvas}"
            )
        if set(direct_rel32_rows) != set(declared_call_rvas):
            raise SystemExit(
                f"DXVK continuation {continuation_id} rel32 CALL declaration drift: "
                f"instruction_rvas={sorted(direct_rel32_rows)} "
                f"declared_rvas={sorted(declared_call_rvas)}"
            )
        for call_rva, expected_target_rva in declared_calls:
            encoded = direct_rel32_rows[call_rva]
            if len(encoded) != 5:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} rel32 CALL at "
                    f"0x{call_rva:08X} has invalid encoded length {len(encoded)}"
                )
            rel32 = int.from_bytes(encoded[1:5], byteorder="little", signed=True)
            decoded_target_rva = (call_rva + 5 + rel32) & 0xFFFFFFFF
            if decoded_target_rva != expected_target_rva:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} rel32 CALL target drift at "
                    f"0x{call_rva:08X}: declared=0x{expected_target_rva:08X} "
                    f"decoded=0x{decoded_target_rva:08X}"
                )

        # A direct relative call into a long INT3 alignment span is just as
        # structurally invalid as a branch entering that span. The branch
        # guard above cannot see CALL metadata, so reject those targets here
        # after the call declarations and rel32 displacements are proven exact.
        padding_call_target_hits = [
            (
                call_rva,
                target_rva,
                instruction_rows[run_start][0],
                instruction_rows[run_end - 1][0] + 1,
            )
            for call_rva, target_rva in declared_calls
            for run_start, run_end in internal_int3_padding_spans
            if instruction_rows[run_start][0]
            <= target_rva
            < instruction_rows[run_end - 1][0] + 1
        ]
        if padding_call_target_hits:
            raise SystemExit(
                f"DXVK continuation {continuation_id} direct CALL enters long INT3 padding: "
                f"{padding_call_target_hits}"
            )

        # Keep optional RESOLVED_PREDECESSOR_TARGET_RVAS metadata tied to the
        # successor proof without assuming how the predecessor learned each
        # forward target. Some targets are inherited across more than one raw
        # window, so their immediate predecessor need not contain the original
        # branch instruction. The invariant we can prove statically here is
        # exact: declarations are unique, are consumed by this proof, and land
        # on exact instruction boundaries in the successor decode.
        resolved_predecessor_name = f"{prefix}_RESOLVED_PREDECESSOR_TARGET_RVAS"
        resolved_predecessor_targets: tuple[int, ...] = ()
        if resolved_predecessor_name in analyzer:
            resolved_predecessor_targets = tuple(value(resolved_predecessor_name))
            if len(resolved_predecessor_targets) != len(set(resolved_predecessor_targets)):
                raise SystemExit(
                    f"DXVK continuation {continuation_id} declares duplicate resolved "
                    f"predecessor targets: {resolved_predecessor_targets}"
                )
            missing_successor_boundaries = sorted(
                set(resolved_predecessor_targets) - static_instruction_rvas
            )
            if missing_successor_boundaries:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} resolved predecessor target "
                    f"declaration drift: targets are not successor instruction boundaries: "
                    f"{[f'0x{rva:08X}' for rva in missing_successor_boundaries]}"
                )
            padding_predecessor_target_hits = [
                (
                    target_rva,
                    instruction_rows[run_start][0],
                    instruction_rows[run_end - 1][0] + 1,
                )
                for target_rva in resolved_predecessor_targets
                for run_start, run_end in internal_int3_padding_spans
                if instruction_rows[run_start][0]
                <= target_rva
                < instruction_rows[run_end - 1][0] + 1
            ]
            if padding_predecessor_target_hits:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} resolved predecessor target "
                    f"enters long INT3 padding: {padding_predecessor_target_hits}"
                )
            if resolved_predecessor_targets:
                if resolved_predecessor_name not in proof_source:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} declares resolved predecessor "
                        "targets but its proof does not consume the declaration"
                    )
                if "resolved_predecessor_targets_on_boundaries" not in proof_source:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} resolved predecessor targets "
                        "are not guarded by an exact-boundary proof"
                    )
        # A predecessor proof may leave a direct branch target address-only
        # because it lies beyond that capture. Once the immediately following
        # exact capture contains that target, the successor must explicitly
        # promote it through RESOLVED_PREDECESSOR_TARGET_RVAS. Without this
        # cross-stage check an empty/omitted declaration can vacuously pass the
        # local boundary guard even though a proven target is now resolvable.
        if continuation_id > proof_ids[0]:
            predecessor_id = continuation_id - 1
            predecessor_proof_name = (
                "collect_guarded_gf_target_c_helper_1_third_callee_continuation_"
                f"{predecessor_id}_prefix_proof"
            )
            predecessor_proof_source = function_source(predecessor_proof_name)
            predecessor_proof_ast = ast.parse(predecessor_proof_source)
            predecessor_external_assignments = [
                node.value
                for node in ast.walk(predecessor_proof_ast)
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name)
                    and target.id == "expected_external_targets"
                    for target in node.targets
                )
            ]
            if len(predecessor_external_assignments) > 1:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} predecessor proof "
                    f"{predecessor_id} has ambiguous expected_external_targets assignments: "
                    f"{len(predecessor_external_assignments)}"
                )
            if predecessor_external_assignments:
                external_node = predecessor_external_assignments[0]
                if isinstance(external_node, ast.Set):
                    predecessor_external_targets = {
                        element.value
                        for element in external_node.elts
                        if isinstance(element, ast.Constant)
                        and isinstance(element.value, int)
                    }
                    if len(predecessor_external_targets) != len(external_node.elts):
                        raise SystemExit(
                            f"DXVK continuation {continuation_id} predecessor proof "
                            f"{predecessor_id} expected_external_targets is not an int literal set"
                        )
                elif (
                    isinstance(external_node, ast.Call)
                    and isinstance(external_node.func, ast.Name)
                    and external_node.func.id == "set"
                    and not external_node.args
                    and not external_node.keywords
                ):
                    predecessor_external_targets = set()
                else:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} predecessor proof "
                        f"{predecessor_id} expected_external_targets must be a literal int set"
                    )

                successor_start = value(f"{prefix}_RVA")
                successor_end = value(f"{prefix}_PREFIX_END_RVA")
                required_direct_predecessor_resolutions = {
                    target_rva
                    for target_rva in predecessor_external_targets
                    if successor_start <= target_rva < successor_end
                }
                missing_direct_predecessor_resolutions = sorted(
                    required_direct_predecessor_resolutions
                    - set(resolved_predecessor_targets)
                )
                if missing_direct_predecessor_resolutions:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} direct predecessor external target entered successor capture without resolution: "
                        f"predecessor={predecessor_id} "
                        f"missing={[f'0x{rva:08X}' for rva in missing_direct_predecessor_resolutions]}"
                    )

            # A target can also be carried one stage beyond the proof that
            # originally discovered it. continuation_57, for example, records
            # 0x1830CA as remaining outside its capture even though that target
            # originated in continuation_56. Once such an inherited forward
            # target enters the immediate successor capture it must be promoted
            # through RESOLVED_PREDECESSOR_TARGET_RVAS just like a direct
            # predecessor external target; otherwise exact boundary evidence
            # could be silently dropped across a two-window handoff.
            inherited_target_assignments = [
                node.value
                for node in ast.walk(predecessor_proof_ast)
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name)
                    and target.id == "remaining_predecessor_target_outside_capture"
                    for target in node.targets
                )
            ]
            if len(inherited_target_assignments) > 1:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} predecessor proof "
                    f"{predecessor_id} has ambiguous inherited target carry assignments: "
                    f"{len(inherited_target_assignments)}"
                )
            if inherited_target_assignments:
                inherited_expr = inherited_target_assignments[0]
                if not (
                    isinstance(inherited_expr, ast.Compare)
                    and len(inherited_expr.ops) == 1
                    and isinstance(inherited_expr.ops[0], (ast.Gt, ast.GtE))
                    and len(inherited_expr.comparators) == 1
                    and isinstance(inherited_expr.left, ast.Constant)
                    and isinstance(inherited_expr.left.value, int)
                    and isinstance(inherited_expr.comparators[0], ast.Name)
                    and inherited_expr.comparators[0].id.endswith("_PREFIX_END_RVA")
                ):
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} predecessor proof "
                        f"{predecessor_id} inherited target carry is not an exact "
                        "literal-target versus PREFIX_END_RVA comparison"
                    )
                inherited_target_rva = inherited_expr.left.value
                inherited_result_binding = (
                    '"remaining_predecessor_target_outside_capture": '
                    "remaining_predecessor_target_outside_capture"
                )
                if inherited_result_binding not in predecessor_proof_source:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} predecessor proof "
                        f"{predecessor_id} inherited target carry is not reported"
                    )
                successor_start = value(f"{prefix}_RVA")
                successor_end = value(f"{prefix}_PREFIX_END_RVA")
                if (
                    successor_start <= inherited_target_rva < successor_end
                    and inherited_target_rva not in set(resolved_predecessor_targets)
                ):
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} inherited predecessor forward target entered successor capture without resolution: "
                        f"predecessor={predecessor_id} "
                        f"target=0x{inherited_target_rva:08X}"
                    )

        # DXVK proof forward-target debt transition: once the newer continuation
        # chain exposes unresolved_forward_targets, each exact proof must account
        # for that debt deterministically. A predecessor target may be resolved
        # only by an exact boundary in this capture; otherwise it must remain
        # carried. New direct branches at/after the capture edge are added to
        # the carried set. This prevents a proof from dropping a still-forward
        # target even when its raw successor lineage is otherwise well-formed.
        if continuation_id > proof_ids[0]:
            predecessor_id = continuation_id - 1
            predecessor_proof_name = (
                "collect_guarded_gf_target_c_helper_1_third_callee_continuation_"
                f"{predecessor_id}_prefix_proof"
            )
            predecessor_proof_ast = ast.parse(
                function_source(predecessor_proof_name)
            )

            def proof_unresolved_forward_targets(
                tree: ast.AST, owner_id: int
            ) -> set[int] | None:
                return_values: list[ast.AST] = []
                for return_node in (
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Return)
                    and isinstance(node.value, ast.Dict)
                ):
                    for key_node, value_node in zip(
                        return_node.value.keys, return_node.value.values
                    ):
                        if (
                            isinstance(key_node, ast.Constant)
                            and key_node.value == "unresolved_forward_targets"
                        ):
                            return_values.append(value_node)
                if not return_values:
                    return None
                if len(return_values) != 1:
                    raise SystemExit(
                        f"DXVK continuation {owner_id} proof has ambiguous "
                        "unresolved_forward_targets return bindings: "
                        f"{len(return_values)}"
                    )

                value_node = return_values[0]
                if isinstance(value_node, ast.Name):
                    assignments = [
                        node.value
                        for node in ast.walk(tree)
                        if isinstance(node, ast.Assign)
                        and any(
                            isinstance(target, ast.Name)
                            and target.id == value_node.id
                            for target in node.targets
                        )
                    ]
                    if len(assignments) != 1:
                        raise SystemExit(
                            f"DXVK continuation {owner_id} proof unresolved-forward "
                            f"variable {value_node.id!r} has ambiguous assignments: "
                            f"{len(assignments)}"
                        )
                    value_node = assignments[0]

                if isinstance(value_node, (ast.List, ast.Tuple, ast.Set)):
                    values = [
                        element.value
                        for element in value_node.elts
                        if (
                            isinstance(element, ast.Constant)
                            and isinstance(element.value, int)
                            and not isinstance(element.value, bool)
                        )
                    ]
                    if len(values) != len(value_node.elts):
                        raise SystemExit(
                            f"DXVK continuation {owner_id} proof "
                            "unresolved_forward_targets must be an int literal sequence"
                        )
                elif (
                    isinstance(value_node, ast.Call)
                    and isinstance(value_node.func, ast.Name)
                    and value_node.func.id == "set"
                    and not value_node.args
                    and not value_node.keywords
                ):
                    values = []
                else:
                    raise SystemExit(
                        f"DXVK continuation {owner_id} proof "
                        "unresolved_forward_targets must resolve to an explicit int literal sequence"
                    )
                if len(values) != len(set(values)):
                    raise SystemExit(
                        f"DXVK continuation {owner_id} proof "
                        "unresolved_forward_targets contains duplicate targets"
                    )
                return set(values)

            predecessor_forward_targets = proof_unresolved_forward_targets(
                predecessor_proof_ast, predecessor_id
            )
            if predecessor_forward_targets is not None:
                current_forward_targets = proof_unresolved_forward_targets(
                    proof_ast, continuation_id
                )
                if current_forward_targets is None:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} dropped predecessor "
                        "unresolved_forward_targets lineage from its exact proof"
                    )

                current_start = value(f"{prefix}_RVA")
                current_end = value(f"{prefix}_PREFIX_END_RVA")
                resolved_target_set = set(resolved_predecessor_targets)
                unexpected_resolutions = sorted(
                    resolved_target_set - predecessor_forward_targets
                )
                if unexpected_resolutions:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} resolves targets not present "
                        f"in predecessor {predecessor_id} forward debt: "
                        f"{[f'0x{rva:08X}' for rva in unexpected_resolutions]}"
                    )

                inherited_remaining = (
                    predecessor_forward_targets - resolved_target_set
                )
                skipped_inherited_targets = sorted(
                    target_rva
                    for target_rva in inherited_remaining
                    if target_rva < current_end
                )
                if skipped_inherited_targets:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} carried predecessor targets "
                        "past the capture that should have resolved them: "
                        f"{[f'0x{rva:08X}' for rva in skipped_inherited_targets]} "
                        f"capture=0x{current_start:08X}..0x{current_end:08X}"
                    )

                new_direct_forward_targets = {
                    target_rva
                    for _branch_rva, target_rva in declared_branches
                    if target_rva >= current_end
                }
                expected_current_forward_targets = (
                    inherited_remaining | new_direct_forward_targets
                )
                if current_forward_targets != expected_current_forward_targets:
                    raise SystemExit(
                        f"DXVK continuation {continuation_id} unresolved forward-target "
                        "debt transition drift: "
                        f"predecessor={sorted(predecessor_forward_targets)} "
                        f"resolved={sorted(resolved_target_set)} "
                        f"new={sorted(new_direct_forward_targets)} "
                        f"expected={sorted(expected_current_forward_targets)} "
                        f"actual={sorted(current_forward_targets)}"
                    )

        proof_status_fail_closed_markers = (
            "proven = bool(",
            '"status"',
            "if proven",
            "else",
        )
        missing_proof_status_markers = [
            marker for marker in proof_status_fail_closed_markers
            if marker not in proof_source
        ]
        if missing_proof_status_markers:
            raise SystemExit(
                f"DXVK continuation {continuation_id} prefix proof status is not fail-closed: "
                f"{missing_proof_status_markers}"
            )
        assigned_names = _function_assignment_names(proof_source)
        proven_gate_names = _final_proven_gate_names(proof_source)
        mandatory_proven_gates = {
            "contiguous",
            "all_bytes_match",
            "prefix_end_matches",
        }
        conditional_integrity_gates = {
            "predecessor_exact",
            "start_boundary_proven",
            "start_completion_proven",
            "instruction_end_matches",
            "capture_end_is_instruction_boundary",
            "capture_boundary_matches",
            "branch_targets_match",
            "internal_branch_targets_on_boundaries",
            "calls_match",
            "raw_call_census_matches",
            "raw_call_census_empty",
            "predecessor_targets_match",
            "resolved_forward_targets_on_boundaries",
            "resolved_prior_forward_target_is_boundary",
            "known_backward_target_is_boundary",
            "remaining_predecessor_target_outside_capture",
            "predecessor_target_contract",
            "resolved_predecessor_targets_on_boundaries",
            "incoming_call_matches",
            "incoming_call_target_is_boundary",
            "padding_matches",
            "incomplete_matches",
            "capture_edge_matches",
            "capture_edge_target_matches",
            "expected_external_targets",
        }
        # Cross-window backedge proofs use an explicit boolean to prove that a
        # backward target lands on an already exact-decoded predecessor
        # instruction boundary. Treat every such assigned gate as mandatory in
        # the final proven predicate. Without this dynamic suffix rule, current
        # continuation_37/64 backedge evidence could keep reporting a boundary
        # field while a later edit accidentally drops it from proof success.
        predecessor_boundary_gates = {
            name
            for name in assigned_names
            if name.endswith("_is_predecessor_boundary")
        }
        # A proof can carry an unresolved predecessor target exactly to a
        # capture edge (for example continuation_65 at the lone E8 opcode).
        # Any explicit *_cut_target_matches predicate is lineage-critical: if
        # later refactoring drops it from proven while leaving the telemetry
        # assignment intact, the canonical chain must fail closed.
        inherited_cut_target_gates = {
            name
            for name in assigned_names
            if name.endswith("_cut_target_matches")
        }
        required_proven_gates = (
            mandatory_proven_gates
            | (assigned_names & conditional_integrity_gates)
            | predecessor_boundary_gates
            | inherited_cut_target_gates
        )
        missing_proven_gates = sorted(required_proven_gates - proven_gate_names)
        if missing_proven_gates:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof status dropped required fail-closed gates: "
                f"{missing_proven_gates}"
            )
        expected_provenance_call = (
            "collect_guarded_gf_target_c_helper_1_third_callee_continuation_"
            f"{continuation_id}_provenance(pe)"
        )
        provenance_calls = proof_source.count(expected_provenance_call)
        if provenance_calls != 1:
            raise SystemExit(
                f"DXVK continuation {continuation_id} prefix proof consumes wrong provenance: "
                f"expected={expected_provenance_call} provenance_calls={provenance_calls}"
            )
        if continuation_id > proof_ids[0]:
            expected_predecessor_id = continuation_id - 1
            expected_predecessor_call = (
                "collect_guarded_gf_target_c_helper_1_third_callee_continuation_"
                f"{expected_predecessor_id}_prefix_proof(pe)"
            )
            predecessor_proof_ids = [
                int(match.group(1))
                for match in re.finditer(
                    r"collect_guarded_gf_target_c_helper_1_third_callee_continuation_(\d+)_prefix_proof\(pe\)",
                    proof_source,
                )
            ]
            immediate_predecessor_calls = predecessor_proof_ids.count(expected_predecessor_id)
            invalid_proof_dependencies = [
                proof_id
                for proof_id in predecessor_proof_ids
                if proof_id >= continuation_id or proof_id not in proof_ids
            ]
            duplicate_proof_dependencies = sorted({
                proof_id
                for proof_id in predecessor_proof_ids
                if predecessor_proof_ids.count(proof_id) > 1
            })
            if predecessor_proof_ids and (
                immediate_predecessor_calls != 1
                or invalid_proof_dependencies
                or duplicate_proof_dependencies
            ):
                raise SystemExit(
                    f"DXVK continuation {continuation_id} prefix proof consumes invalid predecessor proof chain: "
                    f"expected={expected_predecessor_call} proof_ids={predecessor_proof_ids} "
                    f"immediate_calls={immediate_predecessor_calls} "
                    f"invalid={invalid_proof_dependencies} "
                    f"duplicates={duplicate_proof_dependencies}"
                )
        proof_name = (
            f"guarded_gf_target_c_helper_1_third_callee_continuation_"
            f"{continuation_id}_prefix_proof"
        )
        proof_report_binding = (
            f'"{proof_name}": '
            f"collect_guarded_gf_target_c_helper_1_third_callee_continuation_"
            f"{continuation_id}_prefix_proof(pe)"
        )
        if proof_report_binding not in analyzer_source:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof missing analyzer report binding"
            )
        if f"{proof_name}=FAILED" not in analyzer_source:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof missing analyzer failure guard"
            )
        proof_success_marker = (
            f"gf_target_c_helper_1_third_callee_continuation_{continuation_id}_proof="
        )
        if proof_success_marker not in analyzer_source:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof missing analyzer success telemetry"
            )
        start = value(f"{prefix}_RVA")
        probe_end = value(f"{prefix}_PROBE_END_RVA")
        proof_end = value(f"{prefix}_PREFIX_END_RVA")
        if not start <= proof_end <= probe_end:
            raise SystemExit(
                f"DXVK continuation {continuation_id} proof end escaped raw probe: "
                f"0x{proof_end:08X} not in 0x{start:08X}..0x{probe_end:08X}"
            )

        incomplete_rva_name = f"{prefix}_INCOMPLETE_RVA"
        incomplete_bytes_name = f"{prefix}_INCOMPLETE_BYTES"
        has_incomplete_rva = incomplete_rva_name in analyzer
        has_incomplete_bytes = incomplete_bytes_name in analyzer
        if has_incomplete_rva != has_incomplete_bytes:
            raise SystemExit(
                f"DXVK continuation {continuation_id} has a half-defined cut edge"
            )

        # Modern continuation proofs use an explicit cut-edge contract: the
        # captured incomplete bytes and capture-edge geometry are evidence, not
        # optional telemetry. Conditional gate discovery alone is insufficient
        # because deleting both assignments would also delete them from the set
        # of gates that proven is required to consume. Require the modern proof
        # template to assign, gate, and emit both values even at the newest
        # frontier before a successor raw window exists.
        if has_incomplete_rva and continuation_id >= 26:
            required_cut_edge_gates = {"incomplete_matches", "capture_edge_matches"}
            missing_cut_edge_assignments = sorted(
                required_cut_edge_gates - assigned_names
            )
            if missing_cut_edge_assignments:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} modern cut-edge proof lost required evidence gates: "
                    f"{missing_cut_edge_assignments}"
                )

            missing_cut_edge_proven_gates = sorted(
                required_cut_edge_gates - proven_gate_names
            )
            if missing_cut_edge_proven_gates:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} modern cut-edge proof does not gate proven status on: "
                    f"{missing_cut_edge_proven_gates}"
                )

            cut_edge_result_bindings = (
                '"incomplete_matches": incomplete_matches',
                '"capture_edge_matches": capture_edge_matches',
            )
            missing_cut_edge_result_bindings = [
                marker
                for marker in cut_edge_result_bindings
                if marker not in proof_source
            ]
            if missing_cut_edge_result_bindings:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} modern cut-edge proof lost emitted evidence bindings: "
                    f"{missing_cut_edge_result_bindings}"
                )

        if not has_incomplete_rva:
            if proof_end != probe_end:
                raise SystemExit(
                    f"DXVK continuation {continuation_id} has no cut edge but proof end "
                    f"0x{proof_end:08X} != capture end 0x{probe_end:08X}"
                )
            continue

        cut_edge_ids.append(continuation_id)
        incomplete_rva = value(incomplete_rva_name)
        incomplete_bytes = value(incomplete_bytes_name)
        if incomplete_rva != proof_end:
            raise SystemExit(
                f"DXVK continuation {continuation_id} cut edge moved away from proof end: "
                f"0x{incomplete_rva:08X} != 0x{proof_end:08X}"
            )
        if not incomplete_bytes:
            raise SystemExit(
                f"DXVK continuation {continuation_id} cut edge has no captured bytes"
            )
        if incomplete_rva + len(incomplete_bytes) != probe_end:
            raise SystemExit(
                f"DXVK continuation {continuation_id} cut bytes no longer fill capture edge: "
                f"0x{incomplete_rva:08X}+{len(incomplete_bytes)} != 0x{probe_end:08X}"
            )

    cut_edge_id_set = set(cut_edge_ids)
    for previous_id, next_id in zip(raw_ids, raw_ids[1:]):
        if previous_id not in proof_ids:
            raise SystemExit(
                f"DXVK continuation {next_id} exists before predecessor "
                f"{previous_id} has an exact proof"
            )
        previous = f"{symbol_prefix}{previous_id}"
        following = f"{symbol_prefix}{next_id}"
        previous_end = value(f"{previous}_PREFIX_END_RVA")
        next_start = value(f"{following}_RVA")
        if previous_end != next_start:
            raise SystemExit(
                f"DXVK continuation chain gap {previous_id}->{next_id}: "
                f"0x{previous_end:08X} != 0x{next_start:08X}"
            )

        next_overlap_name = f"{following}_OVERLAP_BYTES"
        if previous_id not in cut_edge_id_set:
            previous_probe_end = value(f"{previous}_PROBE_END_RVA")
            if previous_end != previous_probe_end:
                raise SystemExit(
                    f"DXVK boundary transition {previous_id}->{next_id} "
                    f"does not end at the prior capture boundary"
                )
            if next_overlap_name in analyzer:
                raise SystemExit(
                    f"DXVK boundary transition {previous_id}->{next_id} "
                    f"unexpectedly declares overlap bytes"
                )
            continue

        previous_incomplete_rva = value(f"{previous}_INCOMPLETE_RVA")
        previous_incomplete = value(f"{previous}_INCOMPLETE_BYTES")
        if next_overlap_name not in analyzer:
            raise SystemExit(
                f"DXVK overlap transition {previous_id}->{next_id} is missing overlap bytes"
            )
        next_overlap = value(next_overlap_name)
        next_provenance_collector_name = (
            f"collect_guarded_gf_target_c_helper_1_third_callee_continuation_"
            f"{next_id}_provenance"
        )
        next_provenance_source = function_source(next_provenance_collector_name)
        overlap_constant = f"{following}_OVERLAP_BYTES"
        legacy_probe_compare = (
            f"probe[:len({overlap_constant})]" in next_provenance_source
            and f"overlap == {overlap_constant}" in next_provenance_source
        )
        explicit_probe_compare = (
            f"overlap = {overlap_constant}" in next_provenance_source
            and "overlap_actual = probe[: len(overlap)]" in next_provenance_source
            and "overlap_matches =" in next_provenance_source
            and "overlap_actual == overlap" in next_provenance_source
        )
        if not (legacy_probe_compare or explicit_probe_compare):
            raise SystemExit(
                f"DXVK overlap transition {previous_id}->{next_id} raw provenance "
                "no longer compares canonical probe bytes against the declared overlap"
            )
        overlap_integrity_markers = (
            "and overlap_matches",
            '"overlap_matches": overlap_matches',
            'predecessor["incomplete_rva"] == target_rva',
            'predecessor["incomplete_matches"]',
        )
        missing_overlap_integrity_markers = [
            marker for marker in overlap_integrity_markers
            if marker not in next_provenance_source
        ]
        if missing_overlap_integrity_markers:
            raise SystemExit(
                f"DXVK overlap transition {previous_id}->{next_id} raw provenance "
                f"lost fail-closed overlap validation: {missing_overlap_integrity_markers}"
            )

        # F34/continuation 43 and later overlap collectors carry a stronger
        # cross-proof contract: the new probe must match the declared overlap,
        # and that declaration must equal both the predecessor proof's expected
        # and observed incomplete bytes. Keep legacy evidence readable while
        # making every modern/future overlap transition fail closed if any side
        # of that three-way identity is removed.
        if next_id >= 43:
            predecessor_cross_proof_markers = (
                "predecessor_overlap_matches = (",
                'predecessor["incomplete_expected_bytes"] == overlap.hex(" ")',
                'predecessor["incomplete_actual_bytes"] == overlap.hex(" ")',
                "and predecessor_overlap_matches",
                '"overlap_expected_bytes": overlap.hex(" ")',
                '"overlap_actual_bytes": overlap_actual.hex(" ")',
                '"overlap_matches": overlap_matches',
                '"predecessor_overlap_matches": predecessor_overlap_matches',
            )
            missing_predecessor_cross_proof_markers = [
                marker for marker in predecessor_cross_proof_markers
                if marker not in next_provenance_source
            ]
            if missing_predecessor_cross_proof_markers:
                raise SystemExit(
                    f"DXVK overlap transition {previous_id}->{next_id} raw provenance "
                    "lost predecessor incomplete-byte cross-proof: "
                    f"{missing_predecessor_cross_proof_markers}"
                )

        if previous_incomplete_rva != next_start:
            raise SystemExit(
                f"DXVK overlap transition {previous_id}->{next_id} starts at "
                f"0x{next_start:08X}, expected incomplete edge 0x{previous_incomplete_rva:08X}"
            )
        if next_overlap != previous_incomplete:
            raise SystemExit(
                f"DXVK overlap bytes drifted for transition {previous_id}->{next_id}: "
                f"{next_overlap.hex(' ')} != {previous_incomplete.hex(' ')}"
            )

        # Once the overlapping successor has an exact proof, require the prior
        # cut bytes to be a strict prefix of that proof's first complete
        # instruction. Equality would mean the predecessor incorrectly marked
        # a complete instruction as cut; a non-prefix would mean the overlap
        # provenance and decoded successor can silently describe different
        # byte streams even though their RVAs line up.
        if next_id in proof_ids:
            next_instruction_rows = value(f"{following}_INSTRUCTIONS")
            if not next_instruction_rows:
                raise SystemExit(
                    f"DXVK overlap transition {previous_id}->{next_id} proof has no instruction rows"
                )
            first_instruction_rva, first_instruction_hex, _first_instruction_asm = (
                next_instruction_rows[0]
            )
            first_instruction = bytes.fromhex(first_instruction_hex)
            if first_instruction_rva != next_start:
                raise SystemExit(
                    f"DXVK overlap transition {previous_id}->{next_id} first decoded instruction "
                    f"starts at 0x{first_instruction_rva:08X}, expected 0x{next_start:08X}"
                )
            if not first_instruction.startswith(next_overlap):
                raise SystemExit(
                    f"DXVK overlap transition {previous_id}->{next_id} cut-edge overlap does not prefix "
                    f"the first decoded instruction: overlap={next_overlap.hex(' ')} "
                    f"instruction={first_instruction.hex(' ')}"
                )
            if len(next_overlap) >= len(first_instruction):
                raise SystemExit(
                    f"DXVK overlap transition {previous_id}->{next_id} cut edge is not a strict "
                    f"instruction prefix: overlap_len={len(next_overlap)} "
                    f"instruction_len={len(first_instruction)}"
                )

    memoize = analyzer.get("_memoize_pe_only_collector")
    memoized_count = analyzer.get("_DXVK_CONTINUATION_COLLECTORS_MEMOIZED", 0)
    pe_type = analyzer.get("PE")
    expected_chain_collectors = len(raw_ids) + len(proof_ids)
    if (
        memoize is None
        or pe_type is None
        or memoized_count < expected_chain_collectors
    ):
        raise SystemExit(
            "DXVK continuation collector memoization was not installed for the full "
            f"auto-discovered chain: memoized={memoized_count} expected_at_least={expected_chain_collectors}"
        )

    calls = {"count": 0}

    def probe(pe):
        calls["count"] += 1
        return {"pe": pe, "ordinal": calls["count"]}

    cached_probe = memoize(probe)
    pe_a = pe_type(data=b"", image_base=0, entry_rva=0, timestamp=0, size_of_image=0, sections=[])
    pe_b = pe_type(data=b"", image_base=0, entry_rva=0, timestamp=0, size_of_image=0, sections=[])
    first = cached_probe(pe_a)
    second = cached_probe(pe_a)
    third = cached_probe(pe_b)
    if calls["count"] != 2 or first is not second or third is first:
        raise SystemExit(
            "DXVK continuation collector memoization failed single-PE reuse or PE isolation"
        )


def main() -> None:
    require(
        "src/vr/game/disasm_render_contract.hpp",
        [
            "ViewRva       = 0x0055D860u",
            "ProjectionRva = 0x0055D8A0u",
            "WorldViewRva  = 0x0055DB20u",
            "WvpVsRegister = 64u",
            "WvpVsRegisterCount = 4u",
            "SpriteQueueEntryRva = 0x0002D734u",
            "SpriteQueueNodeRva = 0x0002D762u",
            "SpriteQueueEpilogueRva = 0x0002DCB4u",
            "Calc3D2DRva = 0x00049940u",
            "RankMarkerRva = 0x000BAD20u",
            "0x000BB0FBu",
            "0x000BB2D0u",
            "std::array<ProducerRange, 25>",
            '0x00060900u, 0x00061100u, "ctrl_icon_work", "HUD_CTRL_ICON", SpacePolicy::ScreenHud',
            '0x000BBA00u, 0x000BBC00u, "DispTempHeartNum", "HUD_TEMP_HEART", SpacePolicy::ScreenHud',
            '0x00081A00u, 0x00081B00u, "C2C_Fruit", "HUD_FRUIT", SpacePolicy::ScreenHud',
            '0x000BE300u, 0x000BEA40u, "DispTimeAttack2D", "HUD_TIME_ATTACK", SpacePolicy::ScreenHud',
            '0x000FC800u, 0x000FC8A0u, "C2CSpeechBubbleGF_RankEmoji", "HUD_RANK_EMOJI", SpacePolicy::ScreenHud',
            '0x0005B300u, 0x0005B700u, "HeartDisp_car_heart", "WORLD_HEART", SpacePolicy::WorldBillboard',
        ],
    )
    require(
        "src/vr/game/outrun_renderer.cpp",
        [
            "OutRunVR::DisasmContract::WvpVsRegister",
            "OutRunVR::DisasmContract::WvpVsRegisterCount",
            "OutRunVR::DisasmContract::ViewRva",
            "OutRunVR::DisasmContract::ProjectionRva",
            "OutRunVR::DisasmContract::WorldViewRva",
        ],
    )
    require(
        "src/vr/d3d9/stereo_renderer_r7.inc",
        [
            "OutRunVR::DisasmContract::WvpVsRegister",
            "OutRunVR::DisasmContract::WvpVsRegisterCount",
            "OutRunVR::DisasmContract::ProjectionRva",
        ],
    )
    require(
        "src/vr/game/render_semantics.hpp",
        [
            "0x42D734 enters the per-priority SpriteNode walk",
            "0x42D762 begins one node",
            "0x42DCB4 is the common epilogue",
            "RenderScopeFromSpacePolicy(",
            "ClassifyCriticalProducer(",
            "OutRunVR::DisasmContract::ClassifyCriticalProducer(callerRva)",
            "ClassifyCriticalProducer(0x000BE5CDu) == RenderScope::ScreenHud",
            "ClassifyCriticalProducer(0x000BB0FBu) == RenderScope::WorldBillboard",
        ],
    )
    require(
        "src/hooks_uiscaling.cpp",
        [
            "template<std::uintptr_t CallerRva>",
            "GameSemantic::ClassifyCriticalProducer(CallerRva)",
            "scope == OutRunVR::GameSemantic::RenderScope::ScreenHud",
            "TimeRecord_AdjustPositionAndHud<0x000BE5CDu>",
            "TimeRecord_AdjustPositionAndHud<0x000BE603u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE633u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE66Du>",
            "TimeRecord_AdjustPositionAndHud<0x000BE690u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE6B5u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE6D5u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE8D8u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE915u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE94Au>",
            "TimeRecord_AdjustPositionAndHud<0x000BE97Au>",
            "TimeRecord_AdjustPositionAndHud<0x000BE9A3u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE7E8u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE802u>",
            "TimeRecord_AdjustPositionAndHud<0x000BE81Cu>",
            "VR R119 TIME HUD: shared producer-map handoff",
            "DispRank_putClipSprite<0x000B9F3Au>",
            "DispRank_putClipSprite<0x000BA052u>",
            "VR R120 DIRECT CLIP: shared producer-map",
            "template<std::uintptr_t CallerRva, int HelperRva>",
            "GoalTime_TagHelper<0x000BEA5Au, 0xBE020>",
            "GoalTime_TagHelper<0x000BEA5Fu, 0xBE150>",
            "VR R121 GOAL TIME HUD: shared producer-map",
            "C2CTestSlipstream_AdjustPositionAndHud<0x000BD32Eu>",
            "VR R122 SLIPSTREAM HUD: shared producer-map handoff",
            "C2CDontLoseGF_AdjustPositionAndHud<0x000BD397u>",
            "C2CDontLoseGF_AdjustPositionAndHud<0x000BD414u>",
            "C2CDontLoseGF_AdjustPositionAndHud<0x000BD472u>",
            "VR R123 GF WARNING HUD: shared producer-map handoff",
            "DispGearPosition_AdjustPositionAndHud<0x000B9096u>",
            "DispGearPosition_AdjustPositionAndHud<0x000B90B3u>",
            "DispGearPosition_AdjustPositionAndHud<0x000B90F6u>",
            "VR R124 GEAR REV HUD: shared producer-map handoff",
            "PutGhostGapInfo_AdjustPositionAndHud<0x000BDE3Au>",
            "VR R125 GHOST GAP INFO HUD: shared producer-map handoff",
            "PutGhostGapInfo_sub_AdjustPositionAndHud<0x000BDAE8u>",
            "VR R126 GHOST GAP SUB HUD: shared producer-map handoff",
            "DispGhostGap_ForceSpacingAndHud<0x000BE045u, true>",
            "DispGhostGap_ForceSpacingAndHud<0x000BE083u, true>",
            "DispGhostGap_ForceSpacingAndHud<0x000BE0A5u, false>",
            "DispGhostGap_ForceSpacingAndHud<0x000BE067u, false>",
            "VR R127 GHOST GAP FORCE HUD: shared producer-map handoff",
            "DispTempHeartNum_AdjustPositionAndHud<0x000BBA89u>",
            "VR R128 TEMP HEART HUD: shared producer-map handoff",
            "CtrlIcon_AdjustPositionAndHud<0x00060D40u, false>",
            "CtrlIcon_AdjustPositionAndHud<0x00060FBCu, true>",
            "CtrlIcon_AdjustPositionAndHud<0x00060A21u, true>",
            "VR R129 CTRL ICON HUD: shared producer-map handoff",
            "C2CSpeechBubbleRank_AdjustPositionESP0AndHud<0x000FC84Eu>",
            "C2CSpeechBubbleRank_AdjustPositionESP0AndHud<0x000FC882u>",
            "C2CSpeechBubbleRank_AdjustPositionESP0AndHud<0x000FC8B4u>",
            "VR R130 SPEECH RANK HUD: shared producer-map handoff",
            "C2CSpeechBubbleGFInitial_AdjustPositionAndHud<0x000FC9EBu, 0>",
            "C2CSpeechBubbleGFInitial_AdjustPositionAndHud<0x000FCA1Eu, 0>",
            "C2CSpeechBubbleGFInitial_AdjustPositionAndHud<0x000FCA51u, 0>",
            "C2CSpeechBubbleGFInitial_AdjustPositionAndHud<0x000FCB20u, 4>",
            "VR R131 GF SPEECH INITIAL HUD: shared producer-map handoff",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096AC7u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096B14u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096B39u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096B94u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096BE1u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096C10u>",
            "C2CSpeechBubble_AdjustPositionESP0AndHud<0x00096C6Au>",
            "VR R132 C2C SPEECH HUD: shared producer-map handoff",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCDC1u>",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCDEAu>",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCEB0u>",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCED9u>",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCF22u>",
            "C2CSpeechBubbleGF_AdjustPositionESP0AndHud<0x000FCF4Fu>",
            "VR R133 GF SPEECH HUD: shared producer-map handoff",
        ],
    )
    hooks_text = (ROOT / "src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
    if "TimeRecord_AdjustPositionAndHud);" in hooks_text:
        raise SystemExit(
            "F13 shared producer-map adoption regressed to legacy hardcoded callback"
        )
    if "DispRank_putClipSprite, Memory::HookType::Call" in hooks_text:
        raise SystemExit(
            "F13 DispRank clip ownership regressed to legacy hardcoded callback"
        )
    goal_start = hooks_text.find(
        "template<std::uintptr_t CallerRva, int HelperRva>\n"
        "\tstatic void GoalTime_TagHelper(const char* label)"
    )
    goal_end = hooks_text.find(
        "static void __cdecl GoalTime_Help020", goal_start
    )
    if goal_start < 0 or goal_end < 0:
        raise SystemExit("F13 GoalTime shared producer-map helper missing")
    goal_body = hooks_text[goal_start:goal_end]
    if "GameSemantic::ClassifyCriticalProducer(CallerRva)" not in goal_body:
        raise SystemExit("F13 GoalTime helper no longer consumes shared producer map")
    if "node, producerScope" not in goal_body:
        raise SystemExit("F13 GoalTime node ownership no longer uses shared producer scope")
    if 'GoalTime_TagHelper(0xBE020, "BE020")' in hooks_text or \
       'GoalTime_TagHelper(0xBE150, "BE150")' in hooks_text:
        raise SystemExit("F13 GoalTime ownership regressed to legacy unclassified helper")
    if "C2CTestSlipstream_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BD32E, put_scroll_AdjustPositionRight);" in hooks_text:
        raise SystemExit(
            "F13 C2CTestSlipstream ownership regressed to spacing-only callback"
        )
    if "put_scroll_AdjustPositionRight" in hooks_text:
        raise SystemExit(
            "F13 C2CDontLoseGF ownership regressed to legacy spacing-only callback"
        )
    if "put_scroll_AdjustPositionLeft" in hooks_text:
        raise SystemExit(
            "F13 DispGearPosition ownership regressed to legacy spacing-only callback"
        )
    if "PutGhostGapInfo_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BDE3A, PutGhostGapInfo_AdjustPosition);" in hooks_text:
        raise SystemExit(
            "F13 PutGhostGapInfo ownership regressed to spacing-only callback"
        )
    if "PutGhostGapInfo_sub_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BDAE8, PutGhostGapInfo_sub_AdjustPosition);" in hooks_text:
        raise SystemExit(
            "F13 PutGhostGapInfo_sub ownership regressed to spacing-only callback"
        )
    legacy_ghost_gap_force_hooks = [
        "DispGhostGap_ForceLeft_hk = safetyhook::create_mid((void*)0x4BE045, SpriteSpacingForceLeft);",
        "DispGhostGap_ForceLeft2_hk = safetyhook::create_mid((void*)0x4BE083, SpriteSpacingForceLeft);",
        "DispGhostGap_ForceRight_hk = safetyhook::create_mid((void*)0x4BE0A5, SpriteSpacingForceRight);",
        "DispGhostGap_ForceRight2_hk = safetyhook::create_mid((void*)0x4BE067, SpriteSpacingForceRight);",
    ]
    stale_ghost_gap_force_hooks = [
        hook for hook in legacy_ghost_gap_force_hooks if hook in hooks_text
    ]
    if stale_ghost_gap_force_hooks:
        raise SystemExit(
            "F13 DispGhostGap force ownership regressed to spacing-only callbacks: "
            f"{stale_ghost_gap_force_hooks}"
        )
    if "DispTempHeartNum_AdjustPosition_hk = safetyhook::create_mid((void*)0x4BBA89, DispTempHeartNum_AdjustPosition);" in hooks_text:
        raise SystemExit(
            "F13 DispTempHeartNum ownership regressed to spacing-only callback"
        )
    legacy_ctrl_icon_hooks = [
        "ctrl_icon_work_AdjustPosition_hk = safetyhook::create_mid((void*)0x460D40, ctrl_icon_work_AdjustPosition);",
        "ctrl_icon_work_AdjustPosition2_hk = safetyhook::create_mid((void*)0x460FBC, ctrl_icon_work_AdjustPosition2);",
        "set_icon_work_AdjustPosition_hk = safetyhook::create_mid((void*)0x460A21, ctrl_icon_work_AdjustPosition2);",
    ]
    stale_ctrl_icon_hooks = [
        hook for hook in legacy_ctrl_icon_hooks if hook in hooks_text
    ]
    if stale_ctrl_icon_hooks:
        raise SystemExit(
            "F13 ctrl_icon_work ownership regressed to legacy spacing-only callbacks: "
            f"{stale_ctrl_icon_hooks}"
        )
    legacy_speech_rank_hooks = [
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk8 = safetyhook::create_mid((void*)0x4FC84E, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk9 = safetyhook::create_mid((void*)0x4FC882, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk10 = safetyhook::create_mid((void*)0x4FC8B4, C2CSpeechBubble_AdjustPositionESP0);",
    ]
    stale_speech_rank_hooks = [
        hook for hook in legacy_speech_rank_hooks if hook in hooks_text
    ]
    if stale_speech_rank_hooks:
        raise SystemExit(
            "F13 C2CSpeechBubbleGF rank ownership regressed to spacing-only callbacks: "
            f"{stale_speech_rank_hooks}"
        )
    legacy_speech_initial_hooks = [
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk11 = safetyhook::create_mid((void*)0x4FC9EB, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk12 = safetyhook::create_mid((void*)0x4FCA1E, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk13 = safetyhook::create_mid((void*)0x4FCA51, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk14 = safetyhook::create_mid((void*)0x4FCB20, C2CSpeechBubble_AdjustPositionESP4);",
    ]
    stale_speech_initial_hooks = [
        hook for hook in legacy_speech_initial_hooks if hook in hooks_text
    ]
    if stale_speech_initial_hooks:
        raise SystemExit(
            "F13 C2CSpeechBubbleGF initial-position ownership regressed to spacing-only callbacks: "
            f"{stale_speech_initial_hooks}"
        )
    legacy_c2c_speech_hooks = [
        "C2CSpeechBubble_AdjustPositionESP0_hk1 = safetyhook::create_mid((void*)0x496AC7, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk2 = safetyhook::create_mid((void*)0x496B14, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk3 = safetyhook::create_mid((void*)0x496B39, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk4 = safetyhook::create_mid((void*)0x496B94, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk5 = safetyhook::create_mid((void*)0x496BE1, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk6 = safetyhook::create_mid((void*)0x496C10, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubble_AdjustPositionESP0_hk7 = safetyhook::create_mid((void*)0x496C6A, C2CSpeechBubble_AdjustPositionESP0);",
    ]
    stale_c2c_speech_hooks = [
        hook for hook in legacy_c2c_speech_hooks if hook in hooks_text
    ]
    if stale_c2c_speech_hooks:
        raise SystemExit(
            "F13 C2CSpeechBubble ownership regressed to spacing-only callbacks: "
            f"{stale_c2c_speech_hooks}"
        )
    legacy_gf_speech_hooks = [
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk1 = safetyhook::create_mid((void*)0x4FCDC1, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk2 = safetyhook::create_mid((void*)0x4FCDEA, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk3 = safetyhook::create_mid((void*)0x4FCEB0, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk4 = safetyhook::create_mid((void*)0x4FCED9, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk5 = safetyhook::create_mid((void*)0x4FCF22, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk6 = safetyhook::create_mid((void*)0x4FCF4F, C2CSpeechBubble_AdjustPositionESP0);",
    ]
    stale_gf_speech_hooks = [
        hook for hook in legacy_gf_speech_hooks if hook in hooks_text
    ]
    if stale_gf_speech_hooks:
        raise SystemExit(
            "F13 C2CSpeechBubbleGF ownership regressed to spacing-only callbacks: "
            f"{stale_gf_speech_hooks}"
        )
    # R134/F13 negative guard: these five legacy GF hooks are intentionally
    # NOT adopted into immediate next-draw SCREEN_HUD ownership yet. Their
    # producer ranges are canonical HUD, but exact draw adjacency/effect is
    # still unproven (0xFE8B1 is explicitly marked no-effect/uncertain and the
    # four heart hooks have not been independently traced). Keep the current
    # spacing-only bindings fail-closed until separate provenance exists.
    unproven_gf_speech_hooks = [
        "C2CSpeechBubbleGF_AdjustPositionESP0_hk7 = safetyhook::create_mid((void*)0x4FE8B1, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk1 = safetyhook::create_mid((void*)0x4FD60C, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk2 = safetyhook::create_mid((void*)0x4FD591, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk3 = safetyhook::create_mid((void*)0x4FD5CD, C2CSpeechBubble_AdjustPositionESP0);",
        "C2CSpeechBubbleGFHeart_AdjustPositionESP0_hk4 = safetyhook::create_mid((void*)0x4FD652, C2CSpeechBubble_AdjustPositionESP0);",
    ]
    missing_unproven_gf_speech_hooks = [
        hook for hook in unproven_gf_speech_hooks if hook not in hooks_text
    ]
    if missing_unproven_gf_speech_hooks:
        raise SystemExit(
            "F13 unproven GF speech/heart hooks changed without exact producer evidence: "
            f"{missing_unproven_gf_speech_hooks}"
        )
    require(
        "tools/analyze_outrun_exe.py",
        [
            'GF_HOOK_PROVENANCE_RVAS = {',
            '0x0FE8B1: "C2CSpeechBubbleGF uncertain/no-effect spacing hook"',
            '0x0FD60C: "C2CSpeechBubbleGFHeart spacing hook #1"',
            '0x0FD591: "C2CSpeechBubbleGFHeart spacing hook #2"',
            '0x0FD5CD: "C2CSpeechBubbleGFHeart spacing hook #3"',
            '0x0FD652: "C2CSpeechBubbleGFHeart spacing hook #4"',
            'def collect_raw_rel32_call_candidates(',
            '"raw_rel32_call_candidates": collect_raw_rel32_call_candidates(',
            'Raw E8 rel32 candidates',
            'gf_hook_rel32=0x',
            'GF_RAW_REL32_TARGET_RVAS = {',
            '0x000653C0: "guarded GF raw rel32 target A"',
            '0x00065860: "guarded GF raw rel32 target B"',
            '0x00065970: "guarded GF raw rel32 target C"',
            'GF_RAW_REL32_TARGET_WINDOW = 96',
            'def collect_raw_inbound_rel32_candidates(',
            'def collect_guarded_gf_target_provenance(pe: PE) -> list[dict]:',
            '"guarded_gf_target_provenance": collect_guarded_gf_target_provenance(pe)',
            '"## Guarded GF rel32 target function fingerprints"',
            'guarded_gf_targets=',
            'gf_target_provenance=0x',
            'GF_TARGET_B_ENTRY_RVA = 0x00065860',
            'GF_TARGET_B_ALIGNED_CALL_RVA = 0x00065874',
            'GF_TARGET_B_ALIGNED_CALL_TARGET_RVA = 0x000285A0',
            'GF_TARGET_B_PREFIX_INSTRUCTIONS = (',
            '(0x00065874, "e8 27 2d fc ff", "call rel32")',
            'def collect_guarded_gf_target_b_alignment_proof(pe: PE) -> dict:',
            '"guarded_gf_target_b_alignment_proof": collect_guarded_gf_target_b_alignment_proof(pe)',
            '"## Guarded GF target B exact instruction-boundary proof"',
            'EXACT_PREFIX_CALL_ALIGNMENT_PROVEN',
            'gf_target_alignment=0x',
            'guarded_gf_target_b_alignment_proof=FAILED',
            'GF_TARGET_C_ENTRY_RVA = 0x00065970',
            'GF_TARGET_C_ALIGNED_CALL_RVA = 0x00065997',
            'GF_TARGET_C_ALIGNED_CALL_TARGET_RVA = 0x00028460',
            'GF_TARGET_C_PREFIX_INSTRUCTIONS = (',
            '(0x00065997, "e8 c4 2a fc ff", "call rel32")',
            'def collect_guarded_gf_target_c_alignment_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_alignment_proof": collect_guarded_gf_target_c_alignment_proof(pe)',
            '"## Guarded GF target C first-CALL instruction-boundary proof"',
            'EXACT_FIRST_CALL_ALIGNMENT_PROVEN',
            'remaining_raw_call_rvas',
            'guarded_gf_target_c_alignment_proof=FAILED',
            'GF_TARGET_C_SECOND_CALL_ANCHOR_RVA = 0x0006599F',
            'GF_TARGET_C_SECOND_ALIGNED_CALL_RVA = 0x000659AC',
            'GF_TARGET_C_SECOND_ALIGNED_CALL_TARGET_RVA = 0x00028320',
            'GF_TARGET_C_SECOND_CALL_INSTRUCTIONS = (',
            '(0x000659AC, "e8 6f 29 fc ff", "call rel32")',
            'def collect_guarded_gf_target_c_second_call_alignment_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_second_call_alignment_proof": collect_guarded_gf_target_c_second_call_alignment_proof(pe)',
            '"## Guarded GF target C second-CALL instruction-boundary proof"',
            'EXACT_SECOND_CALL_ALIGNMENT_PROVEN',
            'gf_target_second_alignment=0x',
            'guarded_gf_target_c_second_call_alignment_proof=FAILED',
            'GF_TARGET_C_TAIL_PROBE_RVA = 0x000659B1',
            'GF_TARGET_C_TAIL_PROBE_LEN = 32',
            '"bytes96": pe.bytes_at_rva(target_rva, GF_RAW_REL32_TARGET_WINDOW).hex(" ")',
            'gf_target_c_tail_probe=0x',
            'GF_TARGET_C_THIRD_CALL_ANCHOR_RVA = 0x000659B1',
            'GF_TARGET_C_THIRD_ALIGNED_CALL_RVA = 0x000659C1',
            'GF_TARGET_C_THIRD_ALIGNED_CALL_TARGET_RVA = 0x00028800',
            'GF_TARGET_C_THIRD_CALL_INSTRUCTIONS = (',
            '(0x000659C1, "e8 3a 2e fc ff", "call rel32")',
            'def collect_guarded_gf_target_c_third_call_alignment_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_third_call_alignment_proof": collect_guarded_gf_target_c_third_call_alignment_proof(pe)',
            '"## Guarded GF target C third-CALL instruction-boundary proof"',
            'EXACT_THIRD_CALL_ALIGNMENT_PROVEN',
            'gf_target_third_alignment=0x',
            'guarded_gf_target_c_third_call_alignment_proof=FAILED',
            'GF_TARGET_C_HELPER_1_RVA = 0x00028460',
            'GF_TARGET_C_HELPER_PROBE_LEN = 128',
            'GF_TARGET_C_HELPER_1_RANGE_FALLBACK_RVA = 0x00028588',
            'GF_TARGET_C_HELPER_1_MISS_CLEANUP_RVA = 0x000284A6',
            'GF_TARGET_C_HELPER_1_SUCCESS_CONTINUATION_RVA = 0x000284B0',
            'GF_TARGET_C_HELPER_1_TABLE_BASE = 0x009568B8',
            'GF_TARGET_C_HELPER_1_PREFIX_INSTRUCTIONS = (',
            '(0x00028494, "8b 0c b5 b8 68 95 00", "mov ecx, [esi*4+0x9568b8]")',
            '(0x000284AF, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_provenance(pe: PE) -> dict:',
            'def collect_guarded_gf_target_c_helper_1_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_prefix_proof": collect_guarded_gf_target_c_helper_1_prefix_proof(pe)',
            'EXACT_PACKED_SELECTOR_LOOKUP_PREFIX_PROVEN',
            'gf_target_c_helper_1_prefix=0x',
            'guarded_gf_target_c_helper_1_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_RVA = 0x000284BC',
            'GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_TARGET_RVA = 0x000282B0',
            'GF_TARGET_C_HELPER_1_SUCCESS_FAILURE_BRANCH_RVA = 0x000284CB',
            'GF_TARGET_C_HELPER_1_SUCCESS_FAILURE_TARGET_RVA = 0x00028587',
            'GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_RVA = 0x000284D2',
            'GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_TARGET_RVA = 0x0008BD20',
            'GF_TARGET_C_HELPER_1_SUCCESS_PREFIX_INSTRUCTIONS = (',
            '(0x000284BC, "e8 ef fd ff ff", "call rel32")',
            '(0x000284D2, "e8 49 38 06 00", "call rel32")',
            'def collect_guarded_gf_target_c_helper_1_success_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_success_prefix_proof": collect_guarded_gf_target_c_helper_1_success_prefix_proof(pe)',
            'EXACT_SUCCESS_CALL_CHAIN_PREFIX_PROVEN',
            'gf_target_c_helper_1_success=0x',
            'guarded_gf_target_c_helper_1_success_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_RVA = 0x000282B0',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_first_callee_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_first_callee_provenance": collect_guarded_gf_target_c_helper_1_first_callee_provenance(pe)',
            'EXACT_EXE_FIRST_CALLEE_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_first_callee=0x',
            'guarded_gf_target_c_helper_1_first_callee_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_PREFIX_END_RVA = 0x0002830A',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_COUNT_TABLE = 0x00956558',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_CURSOR_TABLE = 0x00956500',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_POOL_BASE = 0x0095E028',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_PREFIX_INSTRUCTIONS = (',
            '(0x000282C9, "7c 05", "jl 0x282d0")',
            '(0x000282CF, "c3", "ret")',
            '(0x000282FC, "75 d3", "jne 0x282d1")',
            '(0x00028308, "89 0e", "mov [esi], ecx")',
            'def collect_guarded_gf_target_c_helper_1_first_callee_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_first_callee_prefix_proof": collect_guarded_gf_target_c_helper_1_first_callee_prefix_proof(pe)',
            'EXACT_FIRST_CALLEE_SLOT_SCAN_PREFIX_PROVEN',
            'gf_target_c_helper_1_first_callee_prefix=0x',
            'guarded_gf_target_c_helper_1_first_callee_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_RVA = 0x0002830A',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_first_callee_continuation_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_first_callee_continuation_provenance": collect_guarded_gf_target_c_helper_1_first_callee_continuation_provenance(pe)',
            'EXACT_EXE_FIRST_CALLEE_CONTINUATION_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_first_callee_continuation=0x',
            'guarded_gf_target_c_helper_1_first_callee_continuation_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_END_RVA = 0x00028319',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_PADDING_END_RVA = 0x00028320',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_RVA = 0x00028320',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_INSTRUCTIONS = (',
            '(0x0002830A, "ff 04 85 58 65 95 00", "inc dword [eax*4+0x956558]")',
            '(0x00028318, "c3", "ret")',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_PADDING_BYTES = bytes.fromhex(',
            'GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_ANCHOR = bytes.fromhex("83 ec 0c")',
            'def collect_guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof": collect_guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof(pe)',
            'EXACT_FIRST_CALLEE_TERMINAL_PADDING_ANCHOR_PROVEN',
            'gf_target_c_helper_1_first_callee_terminal=0x',
            'guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_RVA = 0x00028320',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_next_code_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_provenance": collect_guarded_gf_target_c_helper_1_next_code_provenance(pe)',
            'EXACT_EXE_NEXT_CODE_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_next_code=0x',
            'guarded_gf_target_c_helper_1_next_code_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_PREFIX_END_RVA = 0x0002837E',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_COMMON_RANGE_FAIL_RVA = 0x00028433',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_RVA = 0x00028379',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_TARGET_RVA = 0x000282B0',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_PREFIX_INSTRUCTIONS = (',
            '(0x0002833A, "0f 8c f3 00 00 00", "jl 0x28433")',
            '(0x00028343, "0f 8d ea 00 00 00", "jge 0x28433")',
            '(0x0002836F, "c3", "ret")',
            '(0x00028379, "e8 32 ff ff ff", "call 0x282b0")',
            'def collect_guarded_gf_target_c_helper_1_next_code_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_prefix_proof": collect_guarded_gf_target_c_helper_1_next_code_prefix_proof(pe)',
            'EXACT_NEXT_CODE_PREFIX_CALL_ALIGNMENT_PROVEN',
            'gf_target_c_helper_1_next_code_prefix=0x',
            'guarded_gf_target_c_helper_1_next_code_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA = 0x0002837E',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_next_code_continuation_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_continuation_provenance": collect_guarded_gf_target_c_helper_1_next_code_continuation_provenance(pe)',
            'EXACT_EXE_NEXT_CODE_CONTINUATION_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_next_code_continuation=0x',
            'guarded_gf_target_c_helper_1_next_code_continuation_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_END_RVA = 0x000283DE',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_FAIL_RVA = 0x00028433',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_RVA = 0x00028390',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_TARGET_RVA = 0x0008BD20',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_RVA = 0x0002839D',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_TARGET_RVA = 0x00182194',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_INSTRUCTIONS = (',
            '(0x00028388, "0f 84 a5 00 00 00", "je 0x28433")',
            '(0x00028390, "e8 8b 39 06 00", "call 0x8bd20")',
            '(0x0002839D, "e8 f2 9d 15 00", "call 0x182194")',
            '(0x000283DB, "89 70 18", "mov [eax+0x18], esi")',
            'def collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof": collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe)',
            'EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN',
            'gf_target_c_helper_1_next_code_continuation_prefix=0x',
            'guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA = 0x000283DE',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_next_code_continuation_2_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_continuation_2_provenance": collect_guarded_gf_target_c_helper_1_next_code_continuation_2_provenance(pe)',
            'EXACT_EXE_NEXT_CODE_CONTINUATION_2_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_next_code_continuation_2=0x',
            'guarded_gf_target_c_helper_1_next_code_continuation_2_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_END_RVA = 0x0002843E',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_SHARED_EPILOGUE_RVA = 0x00028433',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_INSTRUCTIONS = (',
            '(0x000283DE, "b9 00 00 80 3f", "mov ecx, 0x3f800000")',
            '(0x00028433, "8b 44 24 0c", "mov eax, [esp+0x0c]")',
            '(0x0002843D, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof": collect_guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof(pe)',
            'EXACT_NEXT_CODE_CONTINUATION_2_TERMINAL_PROVEN',
            'gf_target_c_helper_1_next_code_continuation_2_prefix=0x',
            'guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_ENTRY_RVA = 0x00028320',
            'GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_END_RVA = 0x0002843E',
            'def collect_guarded_gf_target_c_helper_1_next_code_function_boundary_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_next_code_function_boundary_proof": collect_guarded_gf_target_c_helper_1_next_code_function_boundary_proof(pe)',
            'EXACT_28320_FUNCTION_ENTRY_BOUNDARY_PROVEN',
            'EXACT_CALL_TARGET_PADDING_BOUNDARY_PROVEN',
            'BOUNDARY_IDENTITY_ONLY',
            'gf_target_c_helper_1_next_code_function_boundary=0x',
            'guarded_gf_target_c_helper_1_next_code_function_boundary_proof=FAILED',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_RVA = 0x0008BD20',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_second_callee_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_second_callee_provenance": collect_guarded_gf_target_c_helper_1_second_callee_provenance(pe)',
            'EXACT_EXE_8BD20_DUAL_CALL_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_second_callee=0x',
            'guarded_gf_target_c_helper_1_second_callee_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_BODY_END_RVA = 0x0008BD3C',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_PADDING_END_RVA = 0x0008BD40',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_NEXT_CODE_RVA = 0x0008BD40',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_BRANCH_TARGET_RVA = 0x0008BD39',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_INSTRUCTIONS = (',
            '(0x0008BD26, "74 11", "je 0x8bd39")',
            '(0x0008BD2C, "7e 0b", "jle 0x8bd39")',
            '(0x0008BD38, "c3", "ret")',
            '(0x0008BD3B, "c3", "ret")',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_PADDING_BYTES = bytes.fromhex(',
            'GF_TARGET_C_HELPER_1_SECOND_CALLEE_NEXT_CODE_ANCHOR = bytes.fromhex(',
            'def collect_guarded_gf_target_c_helper_1_second_callee_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_second_callee_prefix_proof": collect_guarded_gf_target_c_helper_1_second_callee_prefix_proof(pe)',
            'EXACT_8BD20_BOUNDED_ROUTINE_PADDING_PROVEN',
            'BOUNDED_CONTROL_FLOW_ONLY',
            'gf_target_c_helper_1_second_callee_prefix=0x',
            'guarded_gf_target_c_helper_1_second_callee_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_RVA = 0x00182194',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_LEN = 96',
            'def collect_guarded_gf_target_c_helper_1_third_callee_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_provenance": collect_guarded_gf_target_c_helper_1_third_callee_provenance(pe)',
            'EXACT_EXE_182194_CALL_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_third_callee=0x',
            'routine_call=0x',
            'function_entry={helper_1_third_callee[\'function_entry_status\']}',
            'semantic_effect={helper_1_third_callee[\'semantic_effect\']}',
            'ownership_effect={helper_1_third_callee[\'ownership_effect\']}',
            'guarded_gf_target_c_helper_1_third_callee_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_PREFIX_END_RVA = 0x001821F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_END_RVA = 0x001821F4',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_RVA = 0x001821F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_OPCODE = bytes.fromhex("8b")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_ZERO_RVA = 0x001821B5',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_ZERO_TARGET_RVA = 0x001821F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_SIGN_RVA = 0x001821BB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_SIGN_TARGET_RVA = 0x001821DB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_JUMP_1_RVA = 0x001821D9',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_JUMP_2_RVA = 0x001821F1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_COMMON_FORWARD_TARGET_RVA = 0x00182207',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_PREFIX_INSTRUCTIONS = (',
            '(0x001821B5, "74 3c", "je 0x1821f3")',
            '(0x001821BB, "79 1e", "jns 0x1821db")',
            '(0x001821D9, "eb 2c", "jmp 0x182207")',
            '(0x001821F1, "eb 14", "jmp 0x182207")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_prefix_proof(pe)',
            'EXACT_182194_PREFIX_CONTROL_FLOW_PROVEN',
            'BOUNDED_CONTROL_FLOW_ONLY',
            'INCOMPLETE_OPCODE_AT_PROBE_END',
            'gf_target_c_helper_1_third_callee_prefix=0x',
            'guarded_gf_target_c_helper_1_third_callee_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RVA = 0x001821F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_END_RVA = 0x00182253',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_provenance(pe)',
            'EXACT_EXE_1821F3_CONTINUATION_PROVENANCE_CAPTURED',
            'UNRESOLVED_CONTINUATION_BYTES_ONLY',
            'RAW_BYTES_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation=0x',
            'common_target_in_probe={helper_1_third_cont[\'common_forward_target_within_probe\']}',
            'guarded_gf_target_c_helper_1_third_callee_continuation_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PREFIX_END_RVA = 0x00182251',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_RVA = 0x00182251',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_OPCODE = bytes.fromhex("83 e0")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_TERMINAL_RVA = 0x00182207',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RET_RVA = 0x00182208',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_POST_RET_RVA = 0x00182209',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_RVA = 0x00182240',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_TARGET_RVA = 0x00186906',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INSTRUCTIONS = (',
            '(0x001821FD, "75 b8", "jne 0x1821b7")',
            '(0x00182207, "c9", "leave")',
            '(0x00182208, "c3", "ret")',
            '(0x00182219, "0f 84 a0 00 00 00", "je 0x1822bf")',
            '(0x00182240, "e8 c1 46 00 00", "call 0x186906")',
            '(0x00182248, "eb 0a", "jmp 0x182254")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof(pe)',
            'EXACT_1821F3_CONTINUATION_CONTROL_FLOW_PROVEN',
            'EXACT_COMMON_TARGET_LEAVE_RET_PROVEN',
            'BOUNDED_CONTROL_FLOW_AND_TERMINAL_ONLY',
            'INCOMPLETE_INSTRUCTION_AT_PROBE_END',
            'gf_target_c_helper_1_third_callee_continuation_prefix=0x',
            'guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_RVA = 0x00182251',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_LEN = 128',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_END_RVA = 0x001822D1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_FORWARD_TARGET_RVAS = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance(pe)',
            'EXACT_EXE_182251_CONTINUATION_PROVENANCE_CAPTURED',
            'gf_target_c_helper_1_third_callee_continuation_2=0x',
            'forward_targets_in_probe={helper_1_third_cont_2[\'forward_targets_within_probe\']}',
            'guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PREFIX_END_RVA = 0x001822D1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_RVA = 0x0018229B',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_TARGET_RVA = 0x001882CC',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_LEAVE_RVA = 0x001822D0',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_INSTRUCTIONS = (',
            '(0x00182251, "83 e0 02", "and eax, 2")',
            '(0x00182256, "74 74", "je 0x1822cc")',
            '(0x0018229B, "e8 2c 60 00 00", "call 0x1882cc")',
            '(0x001822BF, "83 fb 61", "cmp ebx, 0x61")',
            '(0x001822D0, "c9", "leave")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof(pe)',
            'EXACT_182251_CONTINUATION_CONTROL_FLOW_PROVEN',
            'LEAVE_PROVEN_RET_NOT_CAPTURED',
            'NEXT_BYTE_AFTER_LEAVE_NOT_CAPTURED',
            'gf_target_c_helper_1_third_callee_continuation_2_prefix=0x',
            'guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_RVA = 0x001822D1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_END_RVA = 0x00182331',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance(pe)',
            'EXACT_EXE_1822D1_CONTINUATION_PROVENANCE_CAPTURED',
            'UNRESOLVED_RAW_FIRST_BYTE_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_3=0x',
            'first_byte={helper_1_third_cont_3[\'first_byte\']}',
            'guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_LEAVE_RVA = 0x001822D0',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_RET_RVA = 0x001822D1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_BYTES = bytes.fromhex("c9 c3")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA = 0x001822D2',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_BYTES = bytes.fromhex("e8 15 39 00 00")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_CALL_TARGET_RVA = 0x00185BEC',
            'def collect_guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof": collect_guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof(pe)',
            'EXACT_1822D0_LEAVE_RET_AND_1822D2_NEXT_INSTRUCTION_PROVEN',
            'EXACT_LEAVE_RET_PROVEN',
            'EXACT_NEXT_INSTRUCTION_START_PROVEN',
            'UNRESOLVED_AT_1822D2',
            'gf_target_c_helper_1_third_callee_terminal=',
            'guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PREFIX_END_RVA = 0x001822F4',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_RET_RVA = 0x001822F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_RVA = 0x001822F4',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_LEN = 12',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_NEXT_CODE_RVA = 0x00182300',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_INSTRUCTIONS = (',
            '(0x001822D2, "e8 15 39 00 00", "call 0x185bec")',
            '(0x001822E0, "74 05", "je 0x1822e7")',
            '(0x001822E2, "e8 27 48 00 00", "call 0x186b0e")',
            '(0x001822EC, "e8 18 ff ff ff", "call 0x182209")',
            '(0x001822F3, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof(pe)',
            'EXACT_1822D2_SEQUENCE_RET_PADDING_NEXT_BOUNDARY_PROVEN',
            'EXACT_RET_AT_1822F3_PROVEN',
            'EXACT_12_BYTE_INT3_PADDING_PROVEN',
            'EXACT_182300_CODE_BOUNDARY_PROVEN',
            'UNRESOLVED_AT_1822D2_AND_182300',
            'gf_target_c_helper_1_third_callee_post_terminal=',
            'guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_START_RVA = 0x00182300',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_PREFIX_END_RVA = 0x00182314',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_RET_RVA = 0x00182313',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_NEXT_INSTRUCTION_RVA = 0x00182314',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INSTRUCTIONS = (',
            '(0x00182300, "83 ec 0c", "sub esp, 0x0c")',
            '(0x00182306, "e8 3d 66 00 00", "call 0x188948")',
            '(0x0018230B, "e8 0d 00 00 00", "call 0x18231d")',
            '(0x00182313, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof(pe)',
            'EXACT_182300_SEQUENCE_RET_NEXT_BOUNDARY_PROVEN',
            'EXACT_RET_AT_182313_PROVEN',
            'EXACT_182314_INSTRUCTION_BOUNDARY_PROVEN',
            'UNRESOLVED_AT_182300_182314_AND_18231D',
            'gf_target_c_helper_1_third_callee_next_block=',
            'guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_RVA = 0x00182314',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_END_RVA = 0x00182331',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_CALL_RVA = 0x0018230B',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_TARGET_RVA = 0x0018231D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_INSTRUCTIONS = (',
            '(0x00182314, "8d 54 24 04", "lea edx, [esp+4]")',
            '(0x00182318, "e8 e8 65 00 00", "call 0x188905")',
            '(0x0018231D, "52", "push edx")',
            '(0x00182322, "74 6d", "je 0x182391")',
            '(0x0018232A, "74 05", "je 0x182331")',
            '(0x0018232C, "e8 a4 65 00 00", "call 0x1888d5")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof": collect_guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof(pe)',
            'EXACT_182314_TO_182331_CAPTURE_END_CONTROL_FLOW_PROVEN',
            'EXACT_18231D_INCOMING_CALL_TARGET_BOUNDARY_PROVEN',
            'DECODED_ONLY_TARGET_BYTES_NOT_CAPTURED',
            'EXACT_CAPTURE_END_AT_182331_REACHED',
            'gf_target_c_helper_1_third_callee_next_continuation=',
            'guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA = 0x00182331',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_END_RVA = 0x00182391',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance(pe)',
            'EXACT_EXE_182331_TO_182391_PROVENANCE_CAPTURED',
            'UNRESOLVED_RAW_BYTES_ONLY',
            'REACHED_182391_TARGET_BYTES_NOT_CAPTURED',
            'UNRESOLVED_AT_182331_AND_182391',
            'gf_target_c_helper_1_third_callee_continuation_4=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PREFIX_END_RVA = 0x00182391',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_INCOMING_BRANCH_RVA = 0x0018232A',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_INSTRUCTIONS = (',
            '(0x00182331, "3d 00 00 f0 3f", "cmp eax, 0x3ff00000")',
            '(0x0018234F, "0f 85 09 66 00 00", "jne 0x18895e")',
            '(0x00182360, "e9 06 66 00 00", "jmp 0x18896b")',
            '(0x0018238A, "e8 5d 65 00 00", "call 0x1888ec")',
            '(0x0018238F, "eb 1b", "jmp 0x1823ac")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof(pe)',
            'EXACT_182331_TO_182391_CONTROL_FLOW_PREFIX_PROVEN',
            'EXACT_182331_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN',
            'BOUNDED_CONTROL_FLOW_AND_CALL_TARGET_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_4_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RVA = 0x00182391',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_LEN = 96',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_END_RVA = 0x001823F1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_REFERENCED_TARGET_RVAS = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance(pe)',
            'EXACT_EXE_182391_TO_1823F1_PROVENANCE_CAPTURED',
            'BYTES_CAPTURED_BOUNDARIES_UNRESOLVED',
            'UNRESOLVED_AT_182391_18239F_1823AC',
            'gf_target_c_helper_1_third_callee_continuation_5=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PREFIX_END_RVA = 0x001823CB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RET_RVA = 0x001823CA',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_RVA = 0x001823CB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_LEN = 5',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_NEXT_CODE_RVA = 0x001823D0',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_REFERENCED_BOUNDARY_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_INSTRUCTIONS = (',
            '(0x00182391, "a9 ff ff 0f 00", "test eax, 0x000fffff")',
            '(0x0018239F, "dd d8", "fstp st(0)")',
            '(0x001823AC, "83 3d 64 fa 85 00 00", "cmp dword [0x85fa64], 0")',
            '(0x001823C4, "e8 ae 64 00 00", "call 0x188877")',
            '(0x001823CA, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof(pe)',
            'EXACT_182391_SEQUENCE_RET_PADDING_NEXT_BOUNDARY_PROVEN',
            'EXACT_RET_AT_1823CA_PROVEN',
            'EXACT_5_BYTE_INT3_PADDING_PROVEN',
            'EXACT_1823D0_CODE_BOUNDARY_PROVEN',
            'gf_target_c_helper_1_third_callee_continuation_5_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RVA = 0x001823D0',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_PREFIX_END_RVA = 0x001823EF',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RET_RVA = 0x001823E3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_NEXT_CODE_RVA = 0x001823E4',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INCOMPLETE_RVA = 0x001823EF',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INCOMPLETE_BYTES = bytes.fromhex("d9 3c")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INSTRUCTIONS = (',
            '(0x001823D0, "83 ec 0c", "sub esp, 0x0c")',
            '(0x001823D3, "dd 14 24", "fst qword [esp]")',
            '(0x001823D6, "e8 6d 65 00 00", "call 0x188948")',
            '(0x001823DB, "e8 0d 00 00 00", "call 0x1823ed")',
            '(0x001823E3, "c3", "ret")',
            '(0x001823E4, "8d 54 24 04", "lea edx, [esp+4]")',
            '(0x001823E8, "e8 18 65 00 00", "call 0x188905")',
            '(0x001823ED, "52", "push edx")',
            '(0x001823EE, "9b", "fwait")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof(pe)',
            'EXACT_1823D0_TO_1823EF_CAPTURE_EDGE_PROVEN',
            'EXACT_RET_AT_1823E3_PROVEN',
            'EXACT_1823E4_CODE_BOUNDARY_PROVEN',
            'EXACT_1823ED_INCOMING_CALL_TARGET_BOUNDARY_PROVEN',
            'INCOMPLETE_INSTRUCTION_AT_1823EF_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_5_tail_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_RVA = 0x001823EF',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_END_RVA = 0x0018242F',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PRIOR_CAPTURE_END_RVA = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_OVERLAP_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PREFIX_END_RVA = 0x0018242E',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_RVA = 0x0018242E',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_BYTES = bytes.fromhex("e9")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INSTRUCTIONS = (',
            '(0x001823EF, "d9 3c 24", "fnstcw word [esp]")',
            '(0x001823FC, "e8 d4 64 00 00", "call 0x1888d5")',
            '(0x0018241D, "0f 85 3b 65 00 00", "jne 0x18895e")',
            '(0x00182428, "8d 0d e0 59 73 00", "lea ecx, [0x7359e0]")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance(pe)',
            'EXACT_EXE_1823EF_TO_18242F_PROVENANCE_CAPTURED',
            'EXACT_D9_3C_OVERLAP_PROVEN',
            'RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_6=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance=FAILED',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof(pe)',
            'EXACT_1823EF_TO_18242E_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_1823EF_CODE_BOUNDARY_PROVEN',
            'EXACT_182401_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN',
            'INCOMPLETE_REL32_JMP_AT_18242E_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_6_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_RVA = 0x0018242E',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_END_RVA = 0x0018246E',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PRIOR_CAPTURE_END_RVA = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_OVERLAP_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PREFIX_END_RVA = 0x0018246D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_RVA = 0x0018246D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_BYTES = bytes.fromhex("75")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INSTRUCTIONS = (',
            '(0x0018242E, "e9 38 65 00 00", "jmp 0x18896b")',
            '(0x00182433, "77 3a", "ja 0x18246f")',
            '(0x00182454, "74 c0", "je 0x182416")',
            '(0x0018245A, "e8 8d 64 00 00", "call 0x1888ec")',
            '(0x00182461, "a9 ff ff 0f 00", "test eax, 0x000fffff")',
            '(0x00182466, "75 f2", "jne 0x18245a")',
            '(0x00182468, "83 7c 24 08 00", "cmp dword [esp+0x08], 0")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance(pe)',
            'EXACT_EXE_18242E_TO_18246E_PROVENANCE_CAPTURED',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof(pe)',
            'EXACT_18242E_TO_18246D_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_18242E_CODE_BOUNDARY_PROVEN',
            'EXACT_182461_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_182416_BACKEDGE_TARGET_BOUNDARY_PROVEN',
            'EXACT_18245A_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN',
            'INCOMPLETE_SHORT_JCC_AT_18246D_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_7_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof=FAILED',
            'EXACT_E9_OVERLAP_PROVEN',
            'R207_INCOMPLETE_REL32_JMP_START_ONLY',
            'UNRESOLVED_AT_18242E_AND_FORWARD_BYTES',
            'gf_target_c_helper_1_third_callee_continuation_7=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RVA = 0x0018246D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_END_RVA = 0x001824AD',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PRIOR_CAPTURE_END_RVA = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance(pe)',
            'EXACT_EXE_18246D_TO_1824AD_PROVENANCE_CAPTURED',
            'EXACT_75_OVERLAP_PROVEN',
            'R211_INCOMPLETE_SHORT_JCC_START_ONLY',
            'UNRESOLVED_AT_18246D_AND_FORWARD_BYTES',
            'gf_target_c_helper_1_third_callee_continuation_8=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PREFIX_END_RVA = 0x001824AB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RET_RVA = 0x0018249A',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_NEXT_CODE_RVA = 0x0018249B',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_RVA = 0x001824AB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_BYTES = bytes.fromhex("e8 5e")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INSTRUCTIONS = (',
            '(0x0018246D, "75 eb", "jne 0x18245a")',
            '(0x00182483, "0f 85 d5 64 00 00", "jne 0x18895e")',
            '(0x00182494, "e8 de 63 00 00", "call 0x188877")',
            '(0x0018249A, "c3", "ret")',
            '(0x0018249B, "e8 4c 37 00 00", "call 0x185bec")',
            '(0x001824A9, "74 05", "je 0x1824b0")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof(pe)',
            'EXACT_18246D_TO_1824AB_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_18246D_CODE_BOUNDARY_PROVEN',
            'EXACT_18246F_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_18247C_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_18245A_BACKEDGE_TARGET_BOUNDARY_PROVEN',
            'EXACT_RET_AT_18249A_PROVEN',
            'EXACT_18249B_CODE_BOUNDARY_PROVEN',
            'INCOMPLETE_REL32_CALL_AT_1824AB_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_8_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RVA = 0x001824AB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_END_RVA = 0x001824EB',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PRIOR_CAPTURE_END_RVA = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance(pe)',
            'EXACT_EXE_1824AB_TO_1824EB_PROVENANCE_CAPTURED',
            'EXACT_E8_5E_OVERLAP_PROVEN',
            'R215_INCOMPLETE_REL32_CALL_START_ONLY',
            'UNRESOLVED_AT_1824AB_AND_FORWARD_BYTES',
            'gf_target_c_helper_1_third_callee_continuation_9=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PREFIX_END_RVA = 0x001824EA',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RET_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_POST_RET_CODE_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INCOMPLETE_RVA = 0x001824EA',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INCOMPLETE_BYTES = bytes.fromhex("e8")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INSTRUCTIONS = (',
            '(0x001824AB, "e8 5e 46 00 00", "call 0x186b0e")',
            '(0x001824B4, "7e 13", "jle 0x1824c9")',
            '(0x001824C0, "e8 41 44 00 00", "call 0x186906")',
            '(0x001824C8, "c3", "ret")',
            '(0x001824D9, "c3", "ret")',
            '(0x001824DA, "e8 0d 37 00 00", "call 0x185bec")',
            '(0x001824E8, "74 05", "je 0x1824ef")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof(pe)',
            'EXACT_1824AB_TO_1824EA_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_1824AB_REL32_CALL_BOUNDARY_PROVEN',
            'EXACT_1824B0_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_1824C9_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_1824EF_TARGET_DECODED_OUTSIDE_CAPTURE',
            'EXACT_RET_AT_1824C8_AND_1824D9_PROVEN',
            'EXACT_1824C9_AND_1824DA_CODE_BOUNDARIES_PROVEN',
            'INCOMPLETE_REL32_CALL_AT_1824EA_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_9_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RVA = 0x001824EA',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_END_RVA = 0x0018252A',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PRIOR_CAPTURE_END_RVA = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance(pe)',
            'EXACT_EXE_1824EA_TO_18252A_PROVENANCE_CAPTURED',
            'EXACT_E8_OVERLAP_PROVEN',
            'R219_INCOMPLETE_REL32_CALL_START_ONLY',
            'UNRESOLVED_AT_1824EA_AND_FORWARD_BYTES',
            'gf_target_c_helper_1_third_callee_continuation_10=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PREFIX_END_RVA = 0x00182529',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RET_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_POST_RET_CODE_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_RVA = 0x00182529',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_BYTES = bytes.fromhex("83")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INSTRUCTIONS = (',
            '(0x001824EA, "e8 1f 46 00 00", "call 0x186b0e")',
            '(0x001824F3, "7e 10", "jle 0x182505")',
            '(0x001824FC, "e8 05 44 00 00", "call 0x186906")',
            '(0x00182504, "c3", "ret")',
            '(0x00182513, "c3", "ret")',
            '(0x00182514, "e8 d3 36 00 00", "call 0x185bec")',
            '(0x00182522, "74 05", "je 0x182529")',
            '(0x00182524, "e8 e5 45 00 00", "call 0x186b0e")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof(pe)',
            'EXACT_1824EA_TO_182529_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_1824EA_REL32_CALL_BOUNDARY_PROVEN',
            'EXACT_1824EF_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_182505_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_182529_BRANCH_TARGET_AT_CAPTURE_EDGE_PROVEN',
            'EXACT_RET_AT_182504_AND_182513_PROVEN',
            'EXACT_182505_AND_182514_CODE_BOUNDARIES_PROVEN',
            'INCOMPLETE_INSTRUCTION_AT_182529_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_10_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_RVA = 0x00182529',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_END_RVA = 0x00182569',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PRIOR_CAPTURE_END_RVA = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance(pe)',
            'EXACT_EXE_182529_TO_182569_PROVENANCE_CAPTURED',
            'EXACT_83_OVERLAP_PROVEN',
            'R223_INCOMPLETE_83_START_ONLY',
            'UNRESOLVED_AT_182529_AND_FORWARD_BYTES',
            'gf_target_c_helper_1_third_callee_continuation_11=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_RVA = 0x00182569',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_END_RVA = 0x001825A9',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PRIOR_CAPTURE_END_RVA = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_12_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_12_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_12_provenance(pe)',
            'EXACT_EXE_182569_TO_1825A9_PROVENANCE_CAPTURED',
            'EXACT_182569_CONTIGUOUS_BOUNDARY_PROVEN',
            'R261_EXACT_CAPTURE_END_INSTRUCTION_BOUNDARY',
            'UNRESOLVED_AT_182569_AND_FORWARD_BYTES',
            'gf_target_c_helper_1_third_callee_continuation_12=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_12_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_RVA = 0x001825A6',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_END_RVA = 0x001825E6',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PRIOR_CAPTURE_END_RVA = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_OVERLAP_BYTES = bytes.fromhex(',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_13_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_13_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_13_provenance(pe)',
            'EXACT_EXE_1825A6_TO_1825E6_PROVENANCE_CAPTURED',
            'EXACT_A9_00_00_OVERLAP_PROVEN',
            'R267_INCOMPLETE_TEST_EAX_IMM32_START',
            'UNRESOLVED_AT_1825A6_AND_FORWARD_BYTES',
            'branch_targets_covered',
            'gf_target_c_helper_1_third_callee_continuation_13=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_13_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PREFIX_END_RVA = 0x001825E5',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INCOMPLETE_RVA = 0x001825E5',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INCOMPLETE_BYTES = bytes.fromhex("74")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PREDECESSOR_TARGET_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_BACKEDGE_TARGET_RVA = 0x0018257C',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INSTRUCTIONS = (',
            '(0x001825A6, "a9 00 00 00 ff", "test eax, 0xff000000")',
            '(0x001825E2, "83 e9 01", "sub ecx, 1")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_13_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_13_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_13_prefix_proof(pe)',
            'EXACT_1825A6_TO_1825E5_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_1825A6_TEST_EAX_IMM32_BOUNDARY_PROVEN',
            'EXACT_1825AD_B2_B7_BC_BOUNDARIES_PROVEN',
            'EXACT_18257C_PREDECESSOR_BOUNDARY_BYTES_PROVEN',
            'INCOMPLETE_SHORT_JCC_AT_1825E5',
            'gf_target_c_helper_1_third_callee_continuation_13_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_13_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_RVA = 0x001825E5',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_LEN = 80',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_END_RVA = 0x00182635',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_OVERLAP_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREFIX_END_RVA = 0x00182635',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_INSTRUCTIONS = (',
            '(0x001825E5, "74 29", "je 0x182610")',
            '(0x00182633, "8b 06", "mov eax, [esi]")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_14_provenance(pe: PE) -> dict:',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_14_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_14_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_14_provenance(pe)',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_14_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_14_prefix_proof(pe)',
            'EXACT_EXE_1825E5_TO_182635_PROVENANCE_CAPTURED',
            'EXACT_1825E5_TO_182635_CONTROL_FLOW_PREFIX_PROVEN',
            'EXACT_74_OVERLAP_PROVEN',
            'EXACT_1825F6_18261A_18262E_BOUNDARIES_PROVEN',
            'EXACT_1825D4_PREDECESSOR_BOUNDARY_BYTES_PROVEN',
            'EXACT_RET_182619_182623_AND_CONTINUATIONS_PROVEN',
            'EXACT_CAPTURE_END_INSTRUCTION_BOUNDARY_182635',
            'gf_target_c_helper_1_third_callee_continuation_14=',
            'gf_target_c_helper_1_third_callee_continuation_14_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_14_provenance=FAILED',
            'guarded_gf_target_c_helper_1_third_callee_continuation_14_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_RVA = 0x00182635',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PROBE_END_RVA = 0x00182675',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREDECESSOR_END_RVA = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_15_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_15_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_15_provenance(pe)',
            'EXACT_EXE_182635_TO_182675_PROVENANCE_CAPTURED',
            'EXACT_182635_PREDECESSOR_INSTRUCTION_BOUNDARY',
            'UNRESOLVED_AT_182635_AND_FORWARD_BYTES',
            'RAW_BYTES_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_15=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_15_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREFIX_END_RVA = 0x00182673',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INCOMPLETE_RVA = 0x00182673',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INCOMPLETE_BYTES = bytes.fromhex("88 57")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREDECESSOR_TARGET_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INSTRUCTIONS = (',
            '(0x00182635, "03 d0", "add edx, eax")',
            '(0x0018266F, "8b 44 24 10", "mov eax, [esp+0x10]")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_15_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_15_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_15_prefix_proof(pe)',
            'EXACT_182635_TO_182673_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_182624_18261A_PREDECESSOR_TARGET_BYTES_PROVEN',
            'EXACT_18266A_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_18267A_TARGET_DECODED_OUTSIDE_CAPTURE',
            'EXACT_RET_AT_182669_PROVEN',
            'INCOMPLETE_MOV_BYTE_AT_182673_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_15_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_15_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_RVA = 0x00182673',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_END_RVA = 0x001826B3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_OVERLAP_BYTES = bytes.fromhex("88 57")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PREDECESSOR_TARGET_RVA = 0x0018267A',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_RET_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PADDING_RVA = 0x00182685',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_NEXT_CODE_RVA = 0x00182690',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_INSTRUCTIONS = (',
            '(0x00182673, "88 57 02", "mov [edi+2], dl")',
            '(0x001826AE, "3d 80 1f 00 00", "cmp eax, 0x1f80")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_16_provenance(pe: PE) -> dict:',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_16_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_16_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_16_provenance(pe)',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_16_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_16_prefix_proof(pe)',
            'EXACT_EXE_182673_TO_1826B3_PROVENANCE_CAPTURED',
            'EXACT_182673_TO_1826B3_CONTROL_FLOW_PREFIX_PROVEN',
            'EXACT_18267A_PREDECESSOR_FORWARD_TARGET_BOUNDARY_PROVEN',
            'EXACT_RET_AT_182679_182684_PROVEN',
            'EXACT_182685_TO_18268F_INT3_PADDING_PROVEN',
            'EXACT_182690_NEXT_CODE_BOUNDARY_PROVEN',
            'EXACT_182724_TARGET_DECODED_OUTSIDE_CAPTURE',
            'EXACT_CAPTURE_END_INSTRUCTION_BOUNDARY_1826B3',
            'gf_target_c_helper_1_third_callee_continuation_16=',
            'gf_target_c_helper_1_third_callee_continuation_16_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_16_provenance=FAILED',
            'guarded_gf_target_c_helper_1_third_callee_continuation_16_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_RVA = 0x001826B3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PROBE_END_RVA = 0x001826F3',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PREFIX_END_RVA = 0x001826F1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INCOMPLETE_RVA = 0x001826F1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INCOMPLETE_BYTES = bytes.fromhex("d9 3c")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INSTRUCTIONS = (',
            '(0x001826B3, "75 0f", "jne 0x1826c4")',
            '(0x001826EF, "75 0f", "jne 0x182700")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_17_provenance(pe: PE) -> dict:',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_17_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_17_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_17_provenance(pe)',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_17_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_17_prefix_proof(pe)',
            'EXACT_EXE_1826B3_TO_1826F3_PROVENANCE_CAPTURED',
            'EXACT_1826B3_TO_1826F1_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_1826C4_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_182724_18270B_182700_188DE9_TARGETS_DECODED_OUTSIDE_CAPTURE',
            'INCOMPLETE_FNSTCW_AT_1826F1_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_17=',
            'gf_target_c_helper_1_third_callee_continuation_17_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_17_provenance=FAILED',
            'guarded_gf_target_c_helper_1_third_callee_continuation_17_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_RVA = 0x001826F1',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PROBE_END_RVA = 0x00182731',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_OVERLAP_BYTES = bytes.fromhex("d9 3c")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PREFIX_END_RVA = 0x00182730',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INCOMPLETE_RVA = 0x00182730',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INCOMPLETE_BYTES = bytes.fromhex("9b")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PREDECESSOR_TARGET_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INSTRUCTIONS = (',
            '(0x001826F1, "d9 3c 24", "fnstcw [esp]")',
            '(0x0018272F, "50", "push eax")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_18_provenance(pe: PE) -> dict:',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_18_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_18_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_18_provenance(pe)',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_18_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_18_prefix_proof(pe)',
            'EXACT_EXE_1826F1_TO_182731_PROVENANCE_CAPTURED',
            'EXACT_1826F1_TO_182730_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_182700_18270B_182724_FORWARD_TARGET_BOUNDARIES_PROVEN',
            'EXACT_18271B_TO_18272D_INTERNAL_CALL_BOUNDARY_PROVEN',
            'EXACT_RET_182723_AND_POST_RET_182724_BOUNDARY_PROVEN',
            'INCOMPLETE_WAIT_PREFIX_AT_182730_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_18=',
            'gf_target_c_helper_1_third_callee_continuation_18_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_18_provenance=FAILED',
            'guarded_gf_target_c_helper_1_third_callee_continuation_18_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_RVA = 0x00182730',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PROBE_END_RVA = 0x00182770',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_OVERLAP_BYTES = bytes.fromhex("9b")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PREFIX_END_RVA = 0x0018276D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INCOMPLETE_RVA = 0x0018276D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INCOMPLETE_BYTES = bytes.fromhex("8a 4c 24")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INSTRUCTIONS = (',
            '(0x00182730, "9b d9 3c 24", "fstcw [esp]")',
            '(0x00182767, "0f 84 f6 00 00 00", "je 0x182863")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_19_provenance(pe: PE) -> dict:',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_19_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_19_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_19_provenance(pe)',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_19_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_19_prefix_proof(pe)',
            'EXACT_EXE_182730_TO_182770_PROVENANCE_CAPTURED',
            'EXACT_182730_TO_18276D_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_182730_WAIT_PREFIXED_FSTCW_COMPLETION_PROVEN',
            'EXACT_182741_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN',
            'INCOMPLETE_MOV_CL_AT_18276D_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_19=',
            'gf_target_c_helper_1_third_callee_continuation_19_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_19_provenance=FAILED',
            'guarded_gf_target_c_helper_1_third_callee_continuation_19_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_RVA = 0x0018276D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PROBE_END_RVA = 0x001827AD',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_OVERLAP_BYTES = bytes.fromhex("8a 4c 24")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PREFIX_END_RVA = 0x001827AC',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INCOMPLETE_RVA = 0x001827AC',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INCOMPLETE_BYTES = bytes.fromhex("0f")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INSTRUCTIONS = (',
            '(0x0018276D, "8a 4c 24 0f", "mov cl, [esp+0x0f]")',
            '(0x001827A5, "83 3d 64 fa 85 00 00", "cmp dword [0x85fa64], 0")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_20_provenance(pe: PE) -> dict:',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_20_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_20_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_20_provenance(pe)',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_20_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_20_prefix_proof(pe)',
            'EXACT_EXE_18276D_TO_1827AD_PROVENANCE_CAPTURED',
            'EXACT_18276D_TO_1827AC_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_18276D_MOV_CL_COMPLETION_PROVEN',
            'EXACT_182788_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN',
            'INCOMPLETE_NEAR_JCC_OPCODE_AT_1827AC_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_20=',
            'gf_target_c_helper_1_third_callee_continuation_20_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_20_provenance=FAILED',
            'guarded_gf_target_c_helper_1_third_callee_continuation_20_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_RVA = 0x001827AC',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PROBE_END_RVA = 0x001827EC',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_21_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_21_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_21_provenance(pe)',
            'EXACT_EXE_1827AC_TO_1827EC_PROVENANCE_CAPTURED',
            'R278_INCOMPLETE_NEAR_JCC_OPCODE_START',
            'RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_21=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_21_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PREFIX_END_RVA = 0x001827E9',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INCOMPLETE_RVA = 0x001827E9',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INCOMPLETE_BYTES = bytes.fromhex("b8 07 00")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PREDECESSOR_TARGET_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INSTRUCTIONS = (',
            '(0x001827AC, "0f 85 ac 61 00 00", "jne 0x18895e")',
            '(0x001827E7, "de c1", "faddp st(1), st")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_21_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_21_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_21_prefix_proof(pe)',
            'EXACT_1827AC_TO_1827E9_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_1827AC_NEAR_JCC_COMPLETION_PROVEN',
            'EXACT_1827D7_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_1827A5_PREDECESSOR_BACKEDGE_TARGET_BYTES_PROVEN',
            'EXACT_RET_1827C3_AND_POST_RET_1827C4_BOUNDARY_PROVEN',
            'INCOMPLETE_MOV_EAX_IMM32_AT_1827E9_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_21_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_21_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_RVA = 0x001827E9',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PROBE_END_RVA = 0x00182829',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_22_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_22_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_22_provenance(pe)',
            'EXACT_EXE_1827E9_TO_182829_PROVENANCE_CAPTURED',
            'PREDECESSOR_INCOMPLETE_MOV_EAX_IMM32_START',
            'UNRESOLVED_AT_1827E9_AND_FORWARD_BYTES',
            'RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_22=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_22_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PREFIX_END_RVA = 0x00182828',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INCOMPLETE_RVA = 0x00182828',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INCOMPLETE_BYTES = bytes.fromhex("85")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PREDECESSOR_TARGET_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INSTRUCTIONS = (',
            '(0x001827E9, "b8 07 00 00 00", "mov eax, 7")',
            '(0x00182826, "75 b8", "jne 0x1827e0")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_22_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_22_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_22_prefix_proof(pe)',
            'EXACT_1827E9_TO_182828_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_1827E9_MOV_EAX_IMM32_COMPLETION_PROVEN',
            'EXACT_18280A_AND_182828_BRANCH_TARGET_BOUNDARIES_PROVEN',
            'EXACT_1827A5_1827C4_1827E0_PREDECESSOR_TARGET_BYTES_PROVEN',
            'INCOMPLETE_TEST_OPCODE_AT_182828_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_22_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_22_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_RVA = 0x00182828',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PROBE_END_RVA = 0x00182868',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_23_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_23_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_23_provenance(pe)',
            'EXACT_EXE_182828_TO_182868_PROVENANCE_CAPTURED',
            'PREDECESSOR_INCOMPLETE_TEST_OPCODE_START',
            'UNRESOLVED_AT_182828_AND_FORWARD_BYTES',
            'gf_target_c_helper_1_third_callee_continuation_23=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_23_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PREFIX_END_RVA = 0x00182867',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INCOMPLETE_RVA = 0x00182867',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INCOMPLETE_BYTES = bytes.fromhex("25")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PREDECESSOR_TARGET_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INSTRUCTIONS = (',
            '(0x00182828, "85 c9", "test ecx, ecx")',
            '(0x00182863, "8b 44 24 0c", "mov eax, [esp+0x0c]")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_23_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_23_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_23_prefix_proof(pe)',
            'EXACT_182828_TO_182867_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_182828_TEST_ECX_ECX_COMPLETION_PROVEN',
            'EXACT_1827A5_1827E7_PREDECESSOR_TARGET_BYTES_PROVEN',
            'EXACT_18895E_BRANCH_AND_189B95_CALL_TARGETS_DECODED_OUTSIDE_CAPTURE',
            'INCOMPLETE_AND_EAX_IMM32_AT_182867_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_23_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_23_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_RVA = 0x00182867',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PROBE_END_RVA = 0x001828A7',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_24_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_24_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_24_provenance(pe)',
            'EXACT_EXE_182867_TO_1828A7_PROVENANCE_CAPTURED',
            'PREDECESSOR_INCOMPLETE_AND_EAX_IMM32_START',
            'UNRESOLVED_AT_182867_AND_FORWARD_BYTES',
            'gf_target_c_helper_1_third_callee_continuation_24=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_24_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PREFIX_END_RVA = 0x001828A7',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_CALLS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PREDECESSOR_TARGET_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_INSTRUCTIONS = (',
            '(0x00182867, "25 ff ff 0f 00", "and eax, 0x000fffff")',
            '(0x001828A5, "74 02", "je 0x1828a9")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_24_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_24_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_24_prefix_proof(pe)',
            'EXACT_182867_TO_1828A7_CONTROL_FLOW_PREFIX_PROVEN',
            'EXACT_182867_AND_EAX_IMM32_COMPLETION_PROVEN',
            'EXACT_18276D_PREDECESSOR_BRANCH_TARGET_BYTES_PROVEN',
            'EXACT_1828A9_1828B3_1828C4_BRANCH_AND_1828F2_CALL_TARGETS_DECODED_OUTSIDE_CAPTURE',
            'EXACT_CAPTURE_END_INSTRUCTION_BOUNDARY_1828A7',
            'gf_target_c_helper_1_third_callee_continuation_24_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_24_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_RVA = 0x001828A7',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PROBE_END_RVA = 0x001828E7',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_25_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_25_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_25_provenance(pe)',
            'EXACT_EXE_1828A7_TO_1828E7_PROVENANCE_CAPTURED',
            'EXACT_PREDECESSOR_INSTRUCTION_BOUNDARY_1828A7',
            'UNRESOLVED_AT_1828A7_AND_FORWARD_BYTES',
            'RAW_BYTES_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_25=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_25_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PREFIX_END_RVA = 0x001828E2',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INCOMPLETE_RVA = 0x001828E2',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INCOMPLETE_BYTES = bytes.fromhex("db 2d f0 60 73")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_CALLS = (',
            '(0x001828CF, 0x001828F2)',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PREDECESSOR_TARGET_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_RESOLVED_FORWARD_TARGET_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INSTRUCTIONS = (',
            '(0x001828A7, "d9 e0", "fchs")',
            '(0x001828E0, "dd d8", "fstp st(0)")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_25_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_25_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_25_prefix_proof(pe)',
            'raw_call_census_matches = observed_raw_calls == expected_raw_calls',
            'EXACT_1828A7_TO_1828E2_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_1828A9_1828B3_1828C4_1828CD_TARGET_BOUNDARIES_PROVEN',
            'EXACT_1827A5_18277A_BRANCH_AND_1828F2_CALL_TARGETS_PROVEN',
            'INCOMPLETE_FLD_TBYTE_DISP32_AT_1828E2_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_25_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_25_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_RVA = 0x001828E2',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_PROBE_END_RVA = 0x00182922',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_26_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_26_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_26_provenance(pe)',
            'EXACT_EXE_1828E2_TO_182922_PROVENANCE_CAPTURED',
            'PREDECESSOR_INCOMPLETE_FLD_TBYTE_DISP32_START',
            'UNRESOLVED_AT_1828E2_AND_FORWARD_BYTES',
            'gf_target_c_helper_1_third_callee_continuation_26=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_26_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_PREFIX_END_RVA = 0x00182920',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_INSTRUCTION_END_RVA = 0x0018291A',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_PADDING_RVA = 0x0018291A',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_PADDING_LEN = 6',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_INCOMPLETE_RVA = 0x00182920',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_INCOMPLETE_BYTES = bytes.fromhex("3d 00")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_BRANCHES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_PREDECESSOR_TARGET_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_INCOMING_CALL_RVA = 0x001828CF',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_INCOMING_CALL_TARGET_RVA = 0x001828F2',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_26_INSTRUCTIONS = (',
            '(0x001828E2, "db 2d f0 60 73 00", "fld tbyte [0x7360f0]")',
            '(0x00182919, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_26_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_26_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_26_prefix_proof(pe)',
            'EXACT_1828E2_TO_182920_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_1828E2_FLD_TBYTE_COMPLETION_PROVEN',
            'EXACT_182916_182917_INTERNAL_BRANCH_TARGET_BOUNDARIES_PROVEN',
            'EXACT_1828CF_TO_1828F2_INCOMING_CALL_TARGET_BOUNDARY_PROVEN',
            'EXACT_18291A_TO_182920_INT3_PADDING_PROVEN',
            'INCOMPLETE_CMP_EAX_IMM32_AT_182920_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_26_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_26_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_27_RVA = 0x00182920',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_27_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_27_PROBE_END_RVA = 0x00182960',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_27_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_27_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_27_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_27_provenance(pe)',
            'EXACT_EXE_182920_TO_182960_PROVENANCE_CAPTURED',
            'PREDECESSOR_INCOMPLETE_CMP_EAX_IMM32_START',
            'UNRESOLVED_AT_182920_AND_FORWARD_BYTES',
            'gf_target_c_helper_1_third_callee_continuation_27=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_27_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_27_PREFIX_END_RVA = 0x0018295D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_27_INCOMPLETE_RVA = 0x0018295D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_27_INCOMPLETE_BYTES = bytes.fromhex("68 ac 90")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_27_BRANCHES = (',
            '(0x00182925, 0x00182935)',
            '(0x0018294C, 0x0018293A)',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_27_CALLS = ()',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_27_INSTRUCTIONS = (',
            '(0x00182920, "3d 00 10 00 00", "cmp eax, 0x1000")',
            '(0x0018295C, "c3", "ret")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_27_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_27_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_27_prefix_proof(pe)',
            'EXACT_182920_TO_18295D_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_182920_CMP_EAX_IMM32_COMPLETION_PROVEN',
            'EXACT_182935_18293A_INTERNAL_TARGET_BOUNDARIES_PROVEN',
            'INCOMPLETE_PUSH_IMM32_AT_18295D_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_27_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_27_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_28_RVA = 0x0018295D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_28_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_28_PROBE_END_RVA = 0x0018299D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_28_OVERLAP_BYTES = (',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_28_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_28_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_28_provenance(pe)',
            'EXACT_EXE_18295D_TO_18299D_PROVENANCE_CAPTURED',
            'PREDECESSOR_INCOMPLETE_PUSH_IMM32_START',
            'UNRESOLVED_AT_18295D_AND_FORWARD_BYTES',
            'RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_28=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_28_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_28_PREFIX_END_RVA = 0x0018299D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_28_BRANCHES = (',
            '(0x0018296A, 0x00182982)',
            '(0x0018297A, 0x00182982)',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_28_CALLS = (',
            '(0x0018298F, 0x0018374C)',
            '(0x00182998, 0x00183697)',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_28_INSTRUCTIONS = (',
            '(0x0018295D, "68 ac 90 61 00", "push 0x6190ac")',
            '(0x00182998, "e8 fa 0c 00 00", "call 0x183697")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_28_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_28_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_28_prefix_proof(pe)',
            'EXACT_18295D_TO_18299D_CONTROL_FLOW_BOUNDARY_PROVEN',
            'EXACT_18295D_PUSH_IMM32_COMPLETION_PROVEN',
            'EXACT_182982_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN',
            'EXACT_INSTRUCTION_BOUNDARY_AT_18299D',
            'gf_target_c_helper_1_third_callee_continuation_28_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_28_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_29_RVA = 0x0018299D',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_29_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_29_PROBE_END_RVA = 0x001829DD',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_29_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_29_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_29_provenance(pe)',
            'EXACT_EXE_18299D_TO_1829DD_PROVENANCE_CAPTURED',
            'EXACT_PREDECESSOR_INSTRUCTION_BOUNDARY_18299D',
            'UNRESOLVED_AT_18299D_AND_FORWARD_BYTES',
            'RAW_BYTES_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_29=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_29_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_29_PREFIX_END_RVA = 0x001829DD',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_29_BRANCHES = (',
            '(0x001829A2, 0x001829AF)',
            '(0x001829D9, 0x001829F2)',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_29_CALLS = ()',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_29_INSTRUCTIONS = (',
            '(0x0018299D, "59", "pop ecx")',
            '(0x001829DB, "85 c0", "test eax, eax")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_29_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_29_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_29_prefix_proof(pe)',
            'EXACT_18299D_TO_1829DD_CONTROL_FLOW_BOUNDARY_PROVEN',
            'EXACT_18299D_POP_ECX_BOUNDARY_PROVEN',
            'EXACT_1829A4_1829AC_1829AF_1829C7_INTERNAL_TARGET_BOUNDARIES_PROVEN',
            'FORWARD_TARGET_1829F2_ADDRESS_ONLY_OUTSIDE_CAPTURE',
            'EXACT_CAPTURE_END_INSTRUCTION_BOUNDARY_1829DD',
            'INDIRECT_CALLS_ONLY_NO_REL32_CALLS_IN_CAPTURE',
            'gf_target_c_helper_1_third_callee_continuation_29_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_29_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_RVA = 0x001829DD',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_PROBE_END_RVA = 0x00182A1D',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_30_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_30_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_30_provenance(pe)',
            'EXACT_EXE_1829DD_TO_182A1D_PROVENANCE_CAPTURED',
            'EXACT_PREDECESSOR_INSTRUCTION_BOUNDARY_1829DD',
            'UNRESOLVED_AT_1829DD_AND_FORWARD_BYTES',
            'RAW_BYTES_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_30=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_30_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_PREFIX_END_RVA = 0x00182A1C',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_INCOMPLETE_RVA = 0x00182A1C',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_INCOMPLETE_BYTES = bytes.fromhex("33")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_BRANCHES = (',
            '(0x001829DD, 0x00182A1E)',
            '(0x00182A0B, 0x00182A1C)',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_CALLS = (',
            '(0x001829F7, 0x00180195)',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_PREDECESSOR_TARGET_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_RESOLVED_PRIOR_FORWARD_TARGET_RVA = 0x001829F2',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_INSTRUCTIONS = (',
            '(0x001829DD, "75 3f", "jne 0x182a1e")',
            '(0x00182A1A, "72 f1", "jb 0x182a0d")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_30_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_30_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_30_prefix_proof(pe)',
            'EXACT_1829DD_TO_182A1C_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_1829F2_PRIOR_FORWARD_TARGET_BOUNDARY_PROVEN',
            'EXACT_1829DB_PREDECESSOR_TARGET_BYTES_PROVEN',
            'EXACT_182A1E_BRANCH_TARGET_ADDRESS_DECODED_OUTSIDE_CAPTURE',
            'INCOMPLETE_XOR_R32_RM32_OPCODE_AT_182A1C_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_30_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_30_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_RVA = 0x00182A1C',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_PROBE_END_RVA = 0x00182A5C',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_OVERLAP_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_30_INCOMPLETE_BYTES',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_31_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_31_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_31_provenance(pe)',
            'EXACT_EXE_182A1C_TO_182A5C_PROVENANCE_CAPTURED',
            'PREDECESSOR_INCOMPLETE_XOR_OPCODE_START_182A1C',
            'UNRESOLVED_AT_182A1C_AND_FORWARD_BYTES',
            'RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_31=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_31_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_PREFIX_END_RVA = 0x00182A5B',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_INCOMPLETE_RVA = 0x00182A5B',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_INCOMPLETE_BYTES = bytes.fromhex("8a")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_BRANCHES = (',
            '(0x00182A43, 0x00182A55)',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_CALLS = (',
            '(0x00182A28, 0x001834A4)',
            '(0x00182A2F, 0x0018374C)',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_RESOLVED_PREDECESSOR_TARGET_RVAS = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_INSTRUCTIONS = (',
            '(0x00182A1C, "33 c0", "xor eax, eax")',
            '(0x00182A55, "89 35 ac fa 85 00", "mov [0x85faac], esi")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_31_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_31_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_31_prefix_proof(pe)',
            'EXACT_182A1C_TO_182A5B_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_182A1C_XOR_EAX_EAX_COMPLETION_PROVEN',
            'EXACT_182A1C_182A1E_PREDECESSOR_TARGET_BOUNDARIES_PROVEN',
            'EXACT_182A55_INTERNAL_TARGET_BOUNDARY_PROVEN',
            'INCOMPLETE_MOV_R8_RM8_OPCODE_AT_182A5B_CAPTURE_END',
            'gf_target_c_helper_1_third_callee_continuation_31_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_31_prefix_proof=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_32_RVA = 0x00182A5B',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_32_PROBE_LEN = 64',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_32_PROBE_END_RVA = 0x00182A9B',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_32_OVERLAP_BYTES = (',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_31_INCOMPLETE_BYTES',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_32_provenance(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_32_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_32_provenance(pe)',
            'EXACT_EXE_182A5B_TO_182A9B_PROVENANCE_CAPTURED',
            'PREDECESSOR_INCOMPLETE_MOV_OPCODE_START_182A5B',
            'UNRESOLVED_AT_182A5B_AND_FORWARD_BYTES',
            'RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY',
            'gf_target_c_helper_1_third_callee_continuation_32=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_32_provenance=FAILED',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_32_PREFIX_END_RVA = 0x00182A99',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_32_INCOMPLETE_RVA = 0x00182A99',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_32_INCOMPLETE_BYTES = bytes.fromhex("e8 01")',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_32_BRANCHES = (',
            '(0x00182A66, 0x00182A9F)',
            '(0x00182A8D, 0x00182A70)',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_32_CALLS = ()',
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_32_INSTRUCTIONS = (',
            '(0x00182A5B, "8a 45 10", "mov al, [ebp+0x10]")',
            '(0x00182A94, "b8 00 f1 62 00", "mov eax, 0x62f100")',
            'def collect_guarded_gf_target_c_helper_1_third_callee_continuation_32_prefix_proof(pe: PE) -> dict:',
            '"guarded_gf_target_c_helper_1_third_callee_continuation_32_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_32_prefix_proof(pe)',
            'EXACT_182A5B_TO_182A99_CONTROL_FLOW_CAPTURE_EDGE_PROVEN',
            'EXACT_182A5B_MOV_AL_COMPLETION_PROVEN',
            'EXACT_182A70_182A8F_INTERNAL_TARGET_BOUNDARIES_PROVEN',
            'FORWARD_TARGET_182A9F_ADDRESS_ONLY_OUTSIDE_CAPTURE',
            'INCOMPLETE_REL32_CALL_AT_182A99_CAPTURE_END',
            'INDIRECT_CALL_ONLY_COMPLETE_REL32_CENSUS_EMPTY',
            'gf_target_c_helper_1_third_callee_continuation_32_proof=',
            'guarded_gf_target_c_helper_1_third_callee_continuation_32_prefix_proof=FAILED',
            'text.rfind(prologue, lo, hi)',
            'def collect_guarded_gf_hook_provenance(pe: PE, calls: list[dict]) -> list[dict]:',
            '"guarded_gf_hook_provenance": collect_guarded_gf_hook_provenance(pe, calls)',
            '"## Guarded GF hook provenance census"',
            'print(f"guarded_gf_provenance={len(provenance)}/{len(GF_HOOK_PROVENANCE_RVAS)}")',
            '0x049940: "Calc3D2D"',
            '0x0BAD20: "RankMarker_sub_4BAD20"',
            '0x0BB0FB: "RankMarker sprani #1"',
            '0x0BB2D0: "RankMarker clip #5"',
            '(0x0BAD20, 0x0BB320, "RankMarker/sub_4BAD20", "WORLD_RIVAL_MARKER", "WORLD_BILLBOARD")',
        ],
    )
    require(
        "docs/automation/runs/CONVERSION-DXVK-00261.json",
        [
            '"status": "COMPLETE_AUTOMATION_PASS_RUNTIME_UNTESTED"',
            '"after": "EXACT_182529_TO_182569_CONTROL_FLOW_PREFIX_PROVEN"',
            '"capture_end_is_instruction_boundary": true',
            '"runtime_validation": "UNTESTED"',
        ],
    )
    verify_dxvk_continuation_chain()
    require(
        ".github/workflows/dxvk-disasm-evidence.yml",
        [
            "CANONICAL_EXE_SHA256: 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3",
            "- name: Verify canonical executable identity",
            "$actualHash = (Get-FileHash analysis-input/OR2006C2C.EXE -Algorithm SHA256).Hash.ToLowerInvariant()",
            "$expectedHash = $env:CANONICAL_EXE_SHA256.ToLowerInvariant()",
            'throw "Canonical OutRun executable SHA256 mismatch: expected=$expectedHash actual=$actualHash"',
        ],
    )
    print("VR backend disassembly contract: OK")


if __name__ == "__main__":
    main()