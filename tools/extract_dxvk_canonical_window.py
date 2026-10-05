"""Extract a SHA-bound canonical PE RVA window for DXVK disassembly evidence."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path
from typing import Sequence


_PROOF_RE = re.compile(
    r"^collect_guarded_gf_target_c_helper_1_third_callee_continuation_(\d+)_prefix_proof$"
)
_CONST_RE = re.compile(
    r"^GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_(\d+)_(INCOMPLETE_RVA|PREFIX_END_RVA)$"
)

_F124_FRONTIER_CONTINUATION_ID = 95
_F124_START_RVA = 0x00183A0C
_F124_END_RVA = 0x00183A4C
_F124_OVERLAP_BYTES = bytes.fromhex("83")
_F124_EXPECTED_BYTES = bytes.fromhex(
    "83 fa 20 88 4c 02 04 73 25 80 7d 0f 00 75 0e 8b "
    "ca bb 00 00 00 80 d3 eb 8b 4d 08 09 19 bb 00 00 "
    "00 80 8b ca d3 eb 8d 44 b8 44 09 18 eb 29 80 7d "
    "0f 00 75 10 8d 4a e0 bb 00 00 00 80 d3 eb 8b 4d"
)
_F124_INHERITED_FORWARD_TARGETS = [0x00183A63, 0x00183B6F]
_F124_PREDECESSOR_STATUS = "EXACT_1839CD_TO_183A0C_CONTROL_FLOW_WITH_183A0C_CUT_EDGE_PROVEN"
_F124_CAPTURE_STATUS = "EXACT_EXE_183A0C_TO_183A4C_PROVENANCE_CAPTURED"


# CONVERSION-DXVK-00381/F126: bind the next raw frontier to the F125
# mandatory trailing MOV overlap without promoting function/runtime semantics.
_F126_FRONTIER_CONTINUATION_ID = 96
_F126_START_RVA = 0x00183A4A
_F126_END_RVA = 0x00183A8A
_F126_OVERLAP_BYTES = bytes.fromhex("8b 4d")
_F126_EXPECTED_BYTES = bytes.fromhex(
    "8b 4d 08 09 59 04 8d 4a e0 ba 00 00 00 80 d3 ea "
    "8d 84 b8 c4 00 00 00 09 10 8b 45 fc 89 06 89 44 "
    "30 fc 8b 45 f0 ff 08 0f 85 f7 00 00 00 a1 40 bc "
    "98 00 85 c0 0f 84 dc 00 00 00 8b 0d 58 bc 98 00"
)
_F126_INHERITED_FORWARD_TARGETS = [0x00183A50, 0x00183A63, 0x00183B6F]
_F126_PREDECESSOR_STATUS = "EXACT_183A0C_TO_183A4A_CONTROL_FLOW_WITH_183A4A_CUT_EDGE_PROVEN"
_F126_CAPTURE_STATUS = "EXACT_EXE_183A4A_TO_183A8A_PROVENANCE_CAPTURED"


# CONVERSION-DXVK-00387/F128: bind the fresh raw frontier to the F127 exact
# 0x183A8A instruction boundary. This start has no inherited overlap debt.
_F128_FRONTIER_CONTINUATION_ID = 97
_F128_START_RVA = 0x00183A8A
_F128_END_RVA = 0x00183ACA
_F128_EXPECTED_BYTES = bytes.fromhex(
    "8b 35 bc 60 59 00 68 00 40 00 00 c1 e1 0f 03 48 "
    "0c bb 00 80 00 00 53 51 ff d6 8b 0d 58 bc 98 00 "
    "a1 40 bc 98 00 ba 00 00 00 80 d3 ea 09 50 08 a1 "
    "40 bc 98 00 8b 40 10 8b 0d 58 bc 98 00 83 a4 88"
)
_F128_INHERITED_FORWARD_TARGETS = [0x00183B60, 0x00183B6E, 0x00183B6F]
_F128_PREDECESSOR_STATUS = "EXACT_183A4A_TO_183A8A_CONTROL_FLOW_BOUNDARY_PROVEN"
_F128_CAPTURE_STATUS = "EXACT_EXE_183A8A_TO_183ACA_PROVENANCE_CAPTURED"


# CONVERSION-DXVK-00393/F130: bind the next raw frontier to the F129
# mandatory trailing three-byte cut-edge without promoting runtime semantics.
_F130_FRONTIER_CONTINUATION_ID = 98
_F130_START_RVA = 0x00183AC7
_F130_END_RVA = 0x00183B07
_F130_OVERLAP_BYTES = bytes.fromhex("83 a4 88")
_F130_EXPECTED_BYTES = bytes.fromhex(
    "83 a4 88 c4 00 00 00 00 a1 40 bc 98 00 8b 40 10 "
    "fe 48 43 a1 40 bc 98 00 8b 48 10 80 79 43 00 75 "
    "09 83 60 04 fe a1 40 bc 98 00 83 78 08 ff 75 69 "
    "53 6a 00 ff 70 0c ff d6 a1 40 bc 98 00 ff 70 10"
)
_F130_INHERITED_FORWARD_TARGETS = [0x00183B60, 0x00183B6E, 0x00183B6F]
_F130_PREDECESSOR_STATUS = "EXACT_183A8A_TO_183AC7_CONTROL_FLOW_WITH_183AC7_CUT_EDGE_PROVEN"
_F130_CAPTURE_STATUS = "EXACT_EXE_183AC7_TO_183B07_PROVENANCE_CAPTURED"


# CONVERSION-DXVK-00399/F132: capture the next canonical raw frontier from the
# F131 exact instruction boundary. Preserve the one observed direct rel32 call
# as address provenance only and carry the trailing raw cut bytes forward.
_F132_FRONTIER_CONTINUATION_ID = 99
_F132_START_RVA = 0x00183B07
_F132_END_RVA = 0x00183B47
_F132_EXPECTED_BYTES = bytes.fromhex(
    "6a 00 ff 35 5c bc 98 00 ff 15 4c 61 59 00 a1 44 "
    "bc 98 00 8b 15 48 bc 98 00 8d 04 80 c1 e0 02 8b "
    "c8 a1 40 bc 98 00 2b c8 8d 4c 11 ec 51 8d 48 14 "
    "51 50 e8 02 c8 ff ff 8b 45 08 83 c4 0c ff 0d 44"
)
_F132_INHERITED_FORWARD_TARGETS = [0x00183B60, 0x00183B6E, 0x00183B6F]
_F132_PREDECESSOR_STATUS = "EXACT_183AC7_TO_183B07_CONTROL_FLOW_BOUNDARY_PROVEN"
_F132_CAPTURE_STATUS = "EXACT_EXE_183B07_TO_183B47_PROVENANCE_CAPTURED"
_F132_RAW_OUTBOUND_REL32 = [(0x00183B39, 0x00180340)]
_F132_TRAILING_OVERLAP_RVA = 0x00183B44
_F132_TRAILING_OVERLAP_BYTES = bytes.fromhex("ff 0d 44")


# CONVERSION-DXVK-00401/F134: consume the F133 mandatory cut edge only when
# the full overlapping instruction is present, pin the next 64 canonical raw
# bytes, preserve inherited target debt, and carry the trailing branch opcode.
_F134_FRONTIER_CONTINUATION_ID = 100
_F134_START_RVA = 0x00183B44
_F134_END_RVA = 0x00183B84
_F134_EXPECTED_BYTES = bytes.fromhex(
    "ff 0d 44 bc 98 00 3b 05 40 bc 98 00 76 04 83 6d "
    "08 14 a1 48 bc 98 00 a3 50 bc 98 00 8b 45 08 a3 "
    "40 bc 98 00 89 3d 58 bc 98 00 5b 5f 5e c9 c3 a1 "
    "44 bc 98 00 8b 0d 54 bc 98 00 57 33 ff 3b c1 75"
)
_F134_INHERITED_FORWARD_TARGETS = [0x00183B60, 0x00183B6E, 0x00183B6F]
_F134_PREDECESSOR_STATUS = "EXACT_183B07_TO_183B44_CONTROL_FLOW_WITH_183B44_CUT_EDGE_PROVEN"
_F134_CAPTURE_STATUS = "EXACT_EXE_183B44_TO_183B84_PROVENANCE_CAPTURED"
_F134_PREDECESSOR_CUT_BYTES = bytes.fromhex("ff 0d 44")
_F134_REQUIRED_OVERLAP_INSTRUCTION = bytes.fromhex("ff 0d 44 bc 98 00")
_F134_TRAILING_OVERLAP_RVA = 0x00183B83
_F134_TRAILING_OVERLAP_BYTES = bytes.fromhex("75")


# CONVERSION-DXVK-00403/F136: bind the next raw frontier to the F135
# mandatory short-Jcc cut edge. Consume only the complete 75 34 overlap,
# preserve the exact 64 canonical bytes, and carry the next incomplete PUSH.
_F136_FRONTIER_CONTINUATION_ID = 101
_F136_START_RVA = 0x00183B83
_F136_END_RVA = 0x00183BC3
_F136_EXPECTED_BYTES = bytes.fromhex(
    "75 34 8d 44 89 50 c1 e0 02 50 ff 35 48 bc 98 00 "
    "57 ff 35 5c bc 98 00 ff 15 68 61 59 00 3b c7 75 04 "
    "33 c0 5f c3 83 05 54 bc 98 00 10 a3 48 bc 98 00 "
    "a1 44 bc 98 00 8b 0d 48 bc 98 00 56 68 c4 41"
)
_F136_INHERITED_FORWARD_TARGETS: list[int] = []
_F136_PREDECESSOR_STATUS = "EXACT_183B44_TO_183B83_CONTROL_FLOW_WITH_183B83_CUT_EDGE_PROVEN"
_F136_CAPTURE_STATUS = "EXACT_EXE_183B83_TO_183BC3_PROVENANCE_CAPTURED"
_F136_PREDECESSOR_CUT_BYTES = bytes.fromhex("75")
_F136_REQUIRED_OVERLAP_INSTRUCTION = bytes.fromhex("75 34")
_F136_TRAILING_OVERLAP_RVA = 0x00183BC0
_F136_TRAILING_OVERLAP_BYTES = bytes.fromhex("68 c4 41")


# CONVERSION-DXVK-00405/F138: bind the next raw frontier to the F137
# mandatory PUSH imm32 cut edge. Consume only the complete overlapping PUSH,
# preserve the exact canonical bytes, and carry the next incomplete FF 76 cut.
_F138_FRONTIER_CONTINUATION_ID = 102
_F138_START_RVA = 0x00183BC0
_F138_END_RVA = 0x00183C00
_F138_EXPECTED_BYTES = bytes.fromhex(
    "68 c4 41 00 00 6a 08 ff 35 5c bc 98 00 8d 04 80 "
    "8d 34 81 ff 15 48 61 59 00 3b c7 89 46 10 75 04 "
    "33 c0 eb 43 6a 04 68 00 20 00 00 68 00 00 10 00 "
    "57 ff 15 3c 61 59 00 3b c7 89 46 0c 75 12 ff 76"
)
_F138_INHERITED_FORWARD_TARGETS: list[int] = []
_F138_PREDECESSOR_STATUS = "EXACT_183B83_TO_183BC0_CONTROL_FLOW_WITH_183BC0_CUT_EDGE_PROVEN"
_F138_CAPTURE_STATUS = "EXACT_EXE_183BC0_TO_183C00_PROVENANCE_CAPTURED"
_F138_PREDECESSOR_CUT_BYTES = bytes.fromhex("68 c4 41")
_F138_REQUIRED_OVERLAP_INSTRUCTION = bytes.fromhex("68 c4 41 00 00")
_F138_TRAILING_OVERLAP_RVA = 0x00183BFE
_F138_TRAILING_OVERLAP_BYTES = bytes.fromhex("ff 76")


# CONVERSION-DXVK-00407/F140: bind the next raw frontier to the F139
# mandatory FF 76 cut edge. Consume only the complete overlapping PUSH,
# preserve the exact canonical bytes and inherited external-target debt, and
# carry the next incomplete short-JMP opcode without semantic promotion.
_F140_FRONTIER_CONTINUATION_ID = 103
_F140_START_RVA = 0x00183BFE
_F140_END_RVA = 0x00183C3E
_F140_EXPECTED_BYTES = bytes.fromhex(
    "ff 76 10 57 ff 35 5c bc 98 00 ff 15 4c 61 59 00 "
    "eb d0 83 4e 08 ff 89 3e 89 7e 04 ff 05 44 bc 98 "
    "00 8b 46 10 83 08 ff 8b c6 5e 5f c3 55 8b ec 51 "
    "51 8b 4d 08 8b 41 08 53 56 8b 71 10 57 33 db eb"
)
_F140_INHERITED_FORWARD_TARGETS = [0x00183C10, 0x00183C27]
_F140_PREDECESSOR_STATUS = "EXACT_183BC0_TO_183BFE_CONTROL_FLOW_WITH_183BFE_CUT_EDGE_PROVEN"
_F140_CAPTURE_STATUS = "EXACT_EXE_183BFE_TO_183C3E_PROVENANCE_CAPTURED"
_F140_PREDECESSOR_CUT_BYTES = bytes.fromhex("ff 76")
_F140_REQUIRED_OVERLAP_INSTRUCTION = bytes.fromhex("ff 76 10")
_F140_TRAILING_OVERLAP_RVA = 0x00183C3D
_F140_TRAILING_OVERLAP_BYTES = bytes.fromhex("eb")


# CONVERSION-DXVK-00409/F142: bind the next raw frontier to the F141
# mandatory short-JMP cut edge. Consume only the complete EB 03 overlap,
# preserve the exact 64 canonical bytes with no inherited forward-target debt,
# and carry the next incomplete FF opcode without semantic promotion.
_F142_FRONTIER_CONTINUATION_ID = 104
_F142_START_RVA = 0x00183C3D
_F142_END_RVA = 0x00183C7D
_F142_EXPECTED_BYTES = bytes.fromhex(
    "eb 03 d1 e0 43 85 c0 7d f9 8b c3 69 c0 04 02 00 "
    "00 8d 84 30 44 01 00 00 6a 3f 89 45 f8 5a 89 40 "
    "08 89 40 04 83 c0 08 4a 75 f4 6a 04 8b fb 68 00 "
    "10 00 00 c1 e7 0f 03 79 0c 68 00 80 00 00 57 ff"
)
_F142_INHERITED_FORWARD_TARGETS: list[int] = []
_F142_PREDECESSOR_STATUS = "EXACT_183BFE_TO_183C3D_CONTROL_FLOW_WITH_183C3D_CUT_EDGE_PROVEN"
_F142_CAPTURE_STATUS = "EXACT_EXE_183C3D_TO_183C7D_PROVENANCE_CAPTURED"
_F142_PREDECESSOR_CUT_BYTES = bytes.fromhex("eb")
_F142_REQUIRED_OVERLAP_INSTRUCTION = bytes.fromhex("eb 03")
_F142_TRAILING_OVERLAP_RVA = 0x00183C7C
_F142_TRAILING_OVERLAP_BYTES = bytes.fromhex("ff")


def discover_frontier_rva(source_path: Path) -> dict:
    """Discover the next raw frontier from the latest exact continuation proof."""

    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    proof_ids = {
        int(match.group(1))
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        if (match := _PROOF_RE.match(node.name))
    }
    if not proof_ids:
        raise ValueError("no continuation prefix proof found in analyzer source")
    continuation_id = max(proof_ids)

    constants: dict[str, int] = {}
    for node in tree.body:
        name = None
        value_node = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            value_node = node.value
        if name is None or value_node is None:
            continue
        match = _CONST_RE.match(name)
        if not match or int(match.group(1)) != continuation_id:
            continue
        if (
            not isinstance(value_node, ast.Constant)
            or not isinstance(value_node.value, int)
            or isinstance(value_node.value, bool)
        ):
            raise ValueError(f"{name} must be an integer literal")
        constants[match.group(2)] = value_node.value

    if "INCOMPLETE_RVA" in constants:
        return {
            "continuation_id": continuation_id,
            "rva": constants["INCOMPLETE_RVA"],
            "basis": "INCOMPLETE_RVA",
        }
    if "PREFIX_END_RVA" in constants:
        return {
            "continuation_id": continuation_id,
            "rva": constants["PREFIX_END_RVA"],
            "basis": "PREFIX_END_RVA",
        }
    raise ValueError(
        f"latest continuation {continuation_id} has neither INCOMPLETE_RVA nor PREFIX_END_RVA literal"
    )


def _u16(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise ValueError(f"PE field outside file at offset 0x{offset:X}")
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"PE field outside file at offset 0x{offset:X}")
    return struct.unpack_from("<I", data, offset)[0]


def _parse_rva(value: str) -> int:
    parsed = int(value, 0)
    if parsed < 0 or parsed > 0xFFFFFFFF:
        raise argparse.ArgumentTypeError("RVA must fit in uint32")
    return parsed


def _map_rva(data: bytes, rva: int, length: int) -> tuple[int, str]:
    if length <= 0:
        raise ValueError("length must be positive")
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not an MZ executable")

    pe_offset = _u32(data, 0x3C)
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("invalid PE signature")

    section_count = _u16(data, pe_offset + 6)
    optional_size = _u16(data, pe_offset + 20)
    optional_offset = pe_offset + 24
    if optional_offset + optional_size > len(data):
        raise ValueError("optional header outside file")
    magic = _u16(data, optional_offset)
    if magic not in (0x10B, 0x20B):
        raise ValueError(f"unsupported PE optional-header magic 0x{magic:04X}")
    if optional_size < 64:
        raise ValueError("optional header too small for SizeOfHeaders")

    size_of_headers = _u32(data, optional_offset + 60)
    if rva < size_of_headers:
        if rva + length > size_of_headers or rva + length > len(data):
            raise ValueError("requested RVA window exceeds PE headers")
        return rva, "PE_HEADERS"

    section_table = optional_offset + optional_size
    if section_table + section_count * 40 > len(data):
        raise ValueError("section table outside file")

    for index in range(section_count):
        base = section_table + index * 40
        name = (
            data[base:base + 8].split(b"\0", 1)[0].decode("ascii", errors="replace")
            or f"section_{index}"
        )
        virtual_size = _u32(data, base + 8)
        virtual_address = _u32(data, base + 12)
        raw_size = _u32(data, base + 16)
        raw_pointer = _u32(data, base + 20)
        mapped_size = max(virtual_size, raw_size)
        if virtual_address <= rva < virtual_address + mapped_size:
            delta = rva - virtual_address
            if delta + length > raw_size:
                raise ValueError(
                    f"requested RVA window exceeds raw section bytes: section={name} "
                    f"delta=0x{delta:X} length={length} raw_size=0x{raw_size:X}"
                )
            file_offset = raw_pointer + delta
            if file_offset + length > len(data):
                raise ValueError("requested RVA window exceeds executable file")
            return file_offset, name

    raise ValueError(f"RVA 0x{rva:08X} is not mapped by any PE section")


def extract_window(
    *,
    exe_path: Path,
    rva: int,
    length: int,
    expected_sha256: str,
    source_sha: str = "",
) -> dict:
    data = exe_path.read_bytes()
    actual_sha256 = hashlib.sha256(data).hexdigest()
    expected = expected_sha256.strip().lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise ValueError(
            "expected SHA256 must be 64 lowercase/uppercase hexadecimal characters"
        )
    if actual_sha256 != expected:
        raise ValueError(
            f"canonical executable SHA256 mismatch: expected={expected} actual={actual_sha256}"
        )

    file_offset, section = _map_rva(data, rva, length)
    window = data[file_offset:file_offset + length]
    if len(window) != length:
        raise ValueError("short read while extracting canonical RVA window")

    return {
        "schema_version": 1,
        "source_sha": source_sha,
        "canonical_exe_sha256": actual_sha256,
        "rva_start": f"0x{rva:08X}",
        "rva_end_exclusive": f"0x{rva + length:08X}",
        "length": length,
        "section": section,
        "file_offset": f"0x{file_offset:08X}",
        "bytes_hex": window.hex(" "),
    }


def _load_frontier_analyzer(source_path: Path):
    module_name = "_dxvk_frontier_analyzer"
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import frontier analyzer: {source_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    return module


def validate_f124_frontier_contract(
    *, frontier: dict, payload: dict, exe_path: Path, source_path: Path, length: int
) -> dict:
    """Fail closed on F124 raw provenance without semantic promotion."""
    if frontier.get("continuation_id") != _F124_FRONTIER_CONTINUATION_ID:
        return {}
    actual = bytes.fromhex(payload.get("bytes_hex", ""))
    if (
        frontier.get("rva") != _F124_START_RVA
        or length != len(_F124_EXPECTED_BYTES)
        or payload.get("rva_start") != f"0x{_F124_START_RVA:08X}"
        or payload.get("rva_end_exclusive") != f"0x{_F124_END_RVA:08X}"
        or payload.get("section") != ".text"
        or not actual.startswith(_F124_OVERLAP_BYTES)
        or actual != _F124_EXPECTED_BYTES
    ):
        raise ValueError("F124 canonical frontier contract mismatch")

    analyzer = _load_frontier_analyzer(source_path)
    pe = analyzer.parse_pe(exe_path.read_bytes())
    predecessor = analyzer.collect_guarded_gf_target_c_helper_1_third_callee_continuation_95_prefix_proof(pe)
    if (
        predecessor.get("status") != _F124_PREDECESSOR_STATUS
        or predecessor.get("prefix_end_rva") != _F124_START_RVA
        or predecessor.get("incomplete_rva") != _F124_START_RVA
        or predecessor.get("incomplete_expected_bytes") != _F124_OVERLAP_BYTES.hex(" ")
        or predecessor.get("incomplete_actual_bytes") != _F124_OVERLAP_BYTES.hex(" ")
        or not predecessor.get("incomplete_matches")
        or not predecessor.get("capture_edge_matches")
        or predecessor.get("unresolved_forward_targets") != _F124_INHERITED_FORWARD_TARGETS
    ):
        raise ValueError("F124 predecessor proof/debt mismatch")

    inbound = analyzer.collect_raw_inbound_rel32_candidates(pe, _F124_START_RVA)
    outbound = analyzer.collect_raw_rel32_call_candidates(pe, _F124_START_RVA, length)
    if inbound or outbound:
        raise ValueError("F124 raw rel32 census is not empty")

    return {
        "frontier_contract_status": _F124_CAPTURE_STATUS,
        "frontier_predecessor_status": predecessor["status"],
        "frontier_overlap_bytes": _F124_OVERLAP_BYTES.hex(" "),
        "frontier_overlap_matches": True,
        "frontier_exact_bytes_match": True,
        "frontier_inherited_unresolved_forward_targets": [
            f"0x{rva:08X}" for rva in _F124_INHERITED_FORWARD_TARGETS
        ],
        "frontier_raw_inbound_rel32_count": 0,
        "frontier_raw_outbound_rel32_count": 0,
        "frontier_semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "frontier_call_semantics": "UNRESOLVED",
        "frontier_ownership_effect": "NONE",
        "frontier_runtime_validation": "UNTESTED",
    }


def validate_f126_frontier_contract(
    *, frontier: dict, payload: dict, exe_path: Path, source_path: Path, length: int
) -> dict:
    """Fail closed on F126 raw provenance without semantic promotion."""
    if frontier.get("continuation_id") != _F126_FRONTIER_CONTINUATION_ID:
        return {}
    actual = bytes.fromhex(payload.get("bytes_hex", ""))
    if (
        frontier.get("rva") != _F126_START_RVA
        or length != len(_F126_EXPECTED_BYTES)
        or payload.get("rva_start") != f"0x{_F126_START_RVA:08X}"
        or payload.get("rva_end_exclusive") != f"0x{_F126_END_RVA:08X}"
        or payload.get("section") != ".text"
        or not actual.startswith(_F126_OVERLAP_BYTES)
        or actual != _F126_EXPECTED_BYTES
    ):
        raise ValueError("F126 canonical frontier contract mismatch")

    analyzer = _load_frontier_analyzer(source_path)
    pe = analyzer.parse_pe(exe_path.read_bytes())
    predecessor = analyzer.collect_guarded_gf_target_c_helper_1_third_callee_continuation_96_prefix_proof(pe)
    if (
        predecessor.get("status") != _F126_PREDECESSOR_STATUS
        or predecessor.get("prefix_end_rva") != _F126_START_RVA
        or predecessor.get("incomplete_rva") != _F126_START_RVA
        or predecessor.get("incomplete_expected_bytes") != _F126_OVERLAP_BYTES.hex(" ")
        or predecessor.get("incomplete_actual_bytes") != _F126_OVERLAP_BYTES.hex(" ")
        or not predecessor.get("incomplete_matches")
        or not predecessor.get("capture_edge_matches")
        or predecessor.get("unresolved_forward_targets") != _F126_INHERITED_FORWARD_TARGETS
    ):
        raise ValueError("F126 predecessor proof/debt mismatch")

    inbound = analyzer.collect_raw_inbound_rel32_candidates(pe, _F126_START_RVA)
    outbound = analyzer.collect_raw_rel32_call_candidates(pe, _F126_START_RVA, length)
    if inbound or outbound:
        raise ValueError("F126 raw rel32 census is not empty")

    return {
        "frontier_contract_status": _F126_CAPTURE_STATUS,
        "frontier_predecessor_status": predecessor["status"],
        "frontier_overlap_bytes": _F126_OVERLAP_BYTES.hex(" "),
        "frontier_overlap_matches": True,
        "frontier_exact_bytes_match": True,
        "frontier_inherited_unresolved_forward_targets": [
            f"0x{rva:08X}" for rva in _F126_INHERITED_FORWARD_TARGETS
        ],
        "frontier_raw_inbound_rel32_count": 0,
        "frontier_raw_outbound_rel32_count": 0,
        "frontier_semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "frontier_call_semantics": "UNRESOLVED",
        "frontier_ownership_effect": "NONE",
        "frontier_runtime_validation": "UNTESTED",
    }


def validate_f128_frontier_contract(
    *, frontier: dict, payload: dict, exe_path: Path, source_path: Path, length: int
) -> dict:
    """Fail closed on F128 raw provenance from the exact F127 boundary."""
    if frontier.get("continuation_id") != _F128_FRONTIER_CONTINUATION_ID:
        return {}
    actual = bytes.fromhex(payload.get("bytes_hex", ""))
    if (
        frontier.get("rva") != _F128_START_RVA
        or length != len(_F128_EXPECTED_BYTES)
        or payload.get("rva_start") != f"0x{_F128_START_RVA:08X}"
        or payload.get("rva_end_exclusive") != f"0x{_F128_END_RVA:08X}"
        or payload.get("section") != ".text"
        or actual != _F128_EXPECTED_BYTES
    ):
        raise ValueError("F128 canonical frontier contract mismatch")

    analyzer = _load_frontier_analyzer(source_path)
    pe = analyzer.parse_pe(exe_path.read_bytes())
    predecessor = analyzer.collect_guarded_gf_target_c_helper_1_third_callee_continuation_97_prefix_proof(pe)
    if (
        predecessor.get("status") != _F128_PREDECESSOR_STATUS
        or predecessor.get("prefix_end_rva") != _F128_START_RVA
        or predecessor.get("capture_end_rva") != _F128_START_RVA
        or not predecessor.get("prefix_end_matches")
        or not predecessor.get("capture_boundary_matches")
        or predecessor.get("unresolved_forward_targets") != _F128_INHERITED_FORWARD_TARGETS
        or predecessor.get("continuation_status")
        != "COMPLETE_INSTRUCTIONS_END_AT_183A8A_EXACT_CAPTURE_BOUNDARY_NO_OVERLAP_DEBT"
    ):
        raise ValueError("F128 predecessor proof/debt mismatch")

    inbound = analyzer.collect_raw_inbound_rel32_candidates(pe, _F128_START_RVA)
    outbound = analyzer.collect_raw_rel32_call_candidates(pe, _F128_START_RVA, length)
    if inbound or outbound:
        raise ValueError("F128 raw rel32 census is not empty")

    return {
        "frontier_contract_status": _F128_CAPTURE_STATUS,
        "frontier_predecessor_status": predecessor["status"],
        "frontier_start_boundary_status": "EXACT_F127_CAPTURE_BOUNDARY_NO_OVERLAP",
        "frontier_exact_bytes_match": True,
        "frontier_inherited_unresolved_forward_targets": [
            f"0x{rva:08X}" for rva in _F128_INHERITED_FORWARD_TARGETS
        ],
        "frontier_raw_inbound_rel32_count": 0,
        "frontier_raw_outbound_rel32_count": 0,
        "frontier_semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "frontier_call_semantics": "UNRESOLVED",
        "frontier_ownership_effect": "NONE",
        "frontier_runtime_validation": "UNTESTED",
    }


def validate_f130_frontier_contract(
    *, frontier: dict, payload: dict, exe_path: Path, source_path: Path, length: int
) -> dict:
    """Fail closed on F130 overlap provenance from the exact F129 cut edge."""
    if frontier.get("continuation_id") != _F130_FRONTIER_CONTINUATION_ID:
        return {}
    actual = bytes.fromhex(payload.get("bytes_hex", ""))
    if (
        frontier.get("rva") != _F130_START_RVA
        or length != len(_F130_EXPECTED_BYTES)
        or payload.get("rva_start") != f"0x{_F130_START_RVA:08X}"
        or payload.get("rva_end_exclusive") != f"0x{_F130_END_RVA:08X}"
        or payload.get("section") != ".text"
        or not actual.startswith(_F130_OVERLAP_BYTES)
        or actual != _F130_EXPECTED_BYTES
    ):
        raise ValueError("F130 canonical frontier contract mismatch")

    analyzer = _load_frontier_analyzer(source_path)
    pe = analyzer.parse_pe(exe_path.read_bytes())
    predecessor = analyzer.collect_guarded_gf_target_c_helper_1_third_callee_continuation_98_prefix_proof(pe)
    if (
        predecessor.get("status") != _F130_PREDECESSOR_STATUS
        or predecessor.get("prefix_end_rva") != _F130_START_RVA
        or predecessor.get("incomplete_rva") != _F130_START_RVA
        or predecessor.get("incomplete_expected_bytes") != _F130_OVERLAP_BYTES.hex(" ")
        or predecessor.get("incomplete_actual_bytes") != _F130_OVERLAP_BYTES.hex(" ")
        or not predecessor.get("incomplete_matches")
        or not predecessor.get("capture_edge_matches")
        or predecessor.get("unresolved_forward_targets") != _F130_INHERITED_FORWARD_TARGETS
        or predecessor.get("continuation_status")
        != "COMPLETE_INSTRUCTIONS_END_AT_183AC7_TRAILING_83A488_REQUIRES_OVERLAP"
    ):
        raise ValueError("F130 predecessor proof/debt mismatch")

    inbound = analyzer.collect_raw_inbound_rel32_candidates(pe, _F130_START_RVA)
    outbound = analyzer.collect_raw_rel32_call_candidates(pe, _F130_START_RVA, length)
    if inbound or outbound:
        raise ValueError("F130 raw rel32 census is not empty")

    return {
        "frontier_contract_status": _F130_CAPTURE_STATUS,
        "frontier_predecessor_status": predecessor["status"],
        "frontier_start_boundary_status": "F129_EXACT_183AC7_MANDATORY_OVERLAP",
        "frontier_overlap_bytes": _F130_OVERLAP_BYTES.hex(" "),
        "frontier_overlap_matches": True,
        "frontier_exact_bytes_match": True,
        "frontier_inherited_unresolved_forward_targets": [
            f"0x{rva:08X}" for rva in _F130_INHERITED_FORWARD_TARGETS
        ],
        "frontier_raw_inbound_rel32_count": 0,
        "frontier_raw_outbound_rel32_count": 0,
        "frontier_semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "frontier_call_semantics": "UNRESOLVED",
        "frontier_ownership_effect": "NONE",
        "frontier_runtime_validation": "UNTESTED",
    }


def validate_f132_frontier_contract(
    *, frontier: dict, payload: dict, exe_path: Path, source_path: Path, length: int
) -> dict:
    """Fail closed on F132 raw provenance from the exact F131 boundary."""
    if frontier.get("continuation_id") != _F132_FRONTIER_CONTINUATION_ID:
        return {}
    actual = bytes.fromhex(payload.get("bytes_hex", ""))
    trailing_offset = _F132_TRAILING_OVERLAP_RVA - _F132_START_RVA
    if (
        frontier.get("rva") != _F132_START_RVA
        or length != len(_F132_EXPECTED_BYTES)
        or payload.get("rva_start") != f"0x{_F132_START_RVA:08X}"
        or payload.get("rva_end_exclusive") != f"0x{_F132_END_RVA:08X}"
        or payload.get("section") != ".text"
        or actual != _F132_EXPECTED_BYTES
        or trailing_offset < 0
        or actual[trailing_offset:] != _F132_TRAILING_OVERLAP_BYTES
    ):
        raise ValueError("F132 canonical frontier contract mismatch")

    analyzer = _load_frontier_analyzer(source_path)
    pe = analyzer.parse_pe(exe_path.read_bytes())
    predecessor = analyzer.collect_guarded_gf_target_c_helper_1_third_callee_continuation_99_prefix_proof(pe)
    if (
        predecessor.get("status") != _F132_PREDECESSOR_STATUS
        or predecessor.get("prefix_end_rva") != _F132_START_RVA
        or predecessor.get("capture_end_rva") != _F132_START_RVA
        or not predecessor.get("prefix_end_matches")
        or not predecessor.get("capture_boundary_matches")
        or predecessor.get("unresolved_forward_targets") != _F132_INHERITED_FORWARD_TARGETS
        or predecessor.get("continuation_status")
        != "COMPLETE_INSTRUCTIONS_END_AT_183B07_EXACT_CAPTURE_BOUNDARY_NO_OVERLAP_DEBT"
    ):
        raise ValueError("F132 predecessor proof/debt mismatch")

    inbound = analyzer.collect_raw_inbound_rel32_candidates(pe, _F132_START_RVA)
    outbound = analyzer.collect_raw_rel32_call_candidates(pe, _F132_START_RVA, length)
    outbound_identity = [
        (row.get("call_rva"), row.get("target_rva"))
        for row in outbound
    ]
    if inbound:
        raise ValueError("F132 raw inbound rel32 census is not empty")
    if outbound_identity != _F132_RAW_OUTBOUND_REL32:
        raise ValueError(
            "F132 raw outbound rel32 census mismatch: "
            f"expected={_F132_RAW_OUTBOUND_REL32} actual={outbound_identity}"
        )

    return {
        "frontier_contract_status": _F132_CAPTURE_STATUS,
        "frontier_predecessor_status": predecessor["status"],
        "frontier_start_boundary_status": "EXACT_F131_CAPTURE_BOUNDARY_NO_OVERLAP",
        "frontier_exact_bytes_match": True,
        "frontier_inherited_unresolved_forward_targets": [
            f"0x{rva:08X}" for rva in _F132_INHERITED_FORWARD_TARGETS
        ],
        "frontier_raw_inbound_rel32_count": 0,
        "frontier_raw_outbound_rel32_count": len(outbound),
        "frontier_raw_outbound_rel32": [
            {
                "call_rva": f"0x{call_rva:08X}",
                "target_rva": f"0x{target_rva:08X}",
            }
            for call_rva, target_rva in _F132_RAW_OUTBOUND_REL32
        ],
        "frontier_trailing_overlap_rva": f"0x{_F132_TRAILING_OVERLAP_RVA:08X}",
        "frontier_trailing_overlap_bytes": _F132_TRAILING_OVERLAP_BYTES.hex(" "),
        "frontier_next_overlap_required": True,
        "frontier_semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "frontier_call_semantics": "REL32_TARGET_ADDRESS_PROVEN_SEMANTICS_UNRESOLVED",
        "frontier_ownership_effect": "NONE",
        "frontier_runtime_validation": "UNTESTED",
    }



def validate_f134_frontier_contract(
    *, frontier: dict, payload: dict, exe_path: Path, source_path: Path, length: int
) -> dict:
    """Fail closed on F134 overlap provenance from the exact F133 cut edge."""
    if frontier.get("continuation_id") != _F134_FRONTIER_CONTINUATION_ID:
        return {}

    actual = bytes.fromhex(payload.get("bytes_hex", ""))
    trailing_offset = _F134_TRAILING_OVERLAP_RVA - _F134_START_RVA
    if (
        frontier.get("rva") != _F134_START_RVA
        or length != len(_F134_EXPECTED_BYTES)
        or payload.get("rva_start") != f"0x{_F134_START_RVA:08X}"
        or payload.get("rva_end_exclusive") != f"0x{_F134_END_RVA:08X}"
        or payload.get("section") != ".text"
        or actual != _F134_EXPECTED_BYTES
        or not actual.startswith(_F134_REQUIRED_OVERLAP_INSTRUCTION)
        or trailing_offset < 0
        or actual[trailing_offset:] != _F134_TRAILING_OVERLAP_BYTES
    ):
        raise ValueError("F134 canonical frontier contract mismatch")

    analyzer = _load_frontier_analyzer(source_path)
    pe = analyzer.parse_pe(exe_path.read_bytes())
    predecessor = analyzer.collect_guarded_gf_target_c_helper_1_third_callee_continuation_100_prefix_proof(pe)
    if (
        predecessor.get("status") != _F134_PREDECESSOR_STATUS
        or predecessor.get("prefix_end_rva") != _F134_START_RVA
        or predecessor.get("incomplete_rva") != _F134_START_RVA
        or predecessor.get("incomplete_bytes") != _F134_PREDECESSOR_CUT_BYTES.hex(" ")
        or not predecessor.get("capture_edge_matches")
        or predecessor.get("unresolved_forward_targets") != _F134_INHERITED_FORWARD_TARGETS
        or predecessor.get("continuation_status")
        != "COMPLETE_INSTRUCTIONS_END_AT_183B44_TRAILING_FF0D44_REQUIRES_OVERLAP"
    ):
        raise ValueError("F134 predecessor proof/debt mismatch")

    inbound = analyzer.collect_raw_inbound_rel32_candidates(pe, _F134_START_RVA)
    outbound = analyzer.collect_raw_rel32_call_candidates(pe, _F134_START_RVA, length)
    if inbound:
        raise ValueError("F134 raw inbound rel32 census is not empty")
    if outbound:
        raise ValueError(f"F134 raw outbound rel32 census is not empty: {outbound}")

    return {
        "frontier_contract_status": _F134_CAPTURE_STATUS,
        "frontier_predecessor_status": predecessor["status"],
        "frontier_start_boundary_status": "F133_MANDATORY_OVERLAP_FULL_INSTRUCTION_CONSUMED",
        "frontier_predecessor_cut_bytes": _F134_PREDECESSOR_CUT_BYTES.hex(" "),
        "frontier_required_overlap_instruction": _F134_REQUIRED_OVERLAP_INSTRUCTION.hex(" "),
        "frontier_exact_bytes_match": True,
        "frontier_inherited_unresolved_forward_targets": [
            f"0x{rva:08X}" for rva in _F134_INHERITED_FORWARD_TARGETS
        ],
        "frontier_raw_inbound_rel32_count": 0,
        "frontier_raw_outbound_rel32_count": 0,
        "frontier_trailing_overlap_rva": f"0x{_F134_TRAILING_OVERLAP_RVA:08X}",
        "frontier_trailing_overlap_bytes": _F134_TRAILING_OVERLAP_BYTES.hex(" "),
        "frontier_next_overlap_required": True,
        "frontier_semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "frontier_call_semantics": "UNRESOLVED",
        "frontier_ownership_effect": "NONE",
        "frontier_runtime_validation": "UNTESTED",
    }

def validate_f136_frontier_contract(
    *, frontier: dict, payload: dict, exe_path: Path, source_path: Path, length: int
) -> dict:
    """Fail closed on F136 overlap provenance from the exact F135 cut edge."""
    if frontier.get("continuation_id") != _F136_FRONTIER_CONTINUATION_ID:
        return {}

    actual = bytes.fromhex(payload.get("bytes_hex", ""))
    trailing_offset = _F136_TRAILING_OVERLAP_RVA - _F136_START_RVA
    if (
        frontier.get("rva") != _F136_START_RVA
        or length != len(_F136_EXPECTED_BYTES)
        or payload.get("rva_start") != f"0x{_F136_START_RVA:08X}"
        or payload.get("rva_end_exclusive") != f"0x{_F136_END_RVA:08X}"
        or payload.get("section") != ".text"
        or actual != _F136_EXPECTED_BYTES
        or not actual.startswith(_F136_REQUIRED_OVERLAP_INSTRUCTION)
        or trailing_offset < 0
        or actual[trailing_offset:] != _F136_TRAILING_OVERLAP_BYTES
    ):
        raise ValueError("F136 canonical frontier contract mismatch")

    analyzer = _load_frontier_analyzer(source_path)
    pe = analyzer.parse_pe(exe_path.read_bytes())
    predecessor = analyzer.collect_guarded_gf_target_c_helper_1_third_callee_continuation_101_prefix_proof(pe)
    if (
        predecessor.get("status") != _F136_PREDECESSOR_STATUS
        or predecessor.get("prefix_end_rva") != _F136_START_RVA
        or predecessor.get("incomplete_rva") != _F136_START_RVA
        or predecessor.get("incomplete_bytes") != _F136_PREDECESSOR_CUT_BYTES.hex(" ")
        or not predecessor.get("capture_edge_matches")
        or predecessor.get("unresolved_forward_targets") != _F136_INHERITED_FORWARD_TARGETS
        or predecessor.get("remaining_predecessor_external_targets") != []
        or predecessor.get("continuation_status")
        != "COMPLETE_INSTRUCTIONS_END_AT_183B83_TRAILING_75_REQUIRES_OVERLAP"
    ):
        raise ValueError("F136 predecessor proof/debt mismatch")

    inbound = analyzer.collect_raw_inbound_rel32_candidates(pe, _F136_START_RVA)
    outbound = analyzer.collect_raw_rel32_call_candidates(pe, _F136_START_RVA, length)
    if inbound:
        raise ValueError("F136 raw inbound rel32 census is not empty")
    if outbound:
        raise ValueError(f"F136 raw outbound rel32 census is not empty: {outbound}")

    return {
        "frontier_contract_status": _F136_CAPTURE_STATUS,
        "frontier_predecessor_status": predecessor["status"],
        "frontier_start_boundary_status": "F135_MANDATORY_OVERLAP_FULL_INSTRUCTION_CONSUMED",
        "frontier_predecessor_cut_bytes": _F136_PREDECESSOR_CUT_BYTES.hex(" "),
        "frontier_required_overlap_instruction": _F136_REQUIRED_OVERLAP_INSTRUCTION.hex(" "),
        "frontier_exact_bytes_match": True,
        "frontier_inherited_unresolved_forward_targets": [],
        "frontier_raw_inbound_rel32_count": 0,
        "frontier_raw_outbound_rel32_count": 0,
        "frontier_trailing_overlap_rva": f"0x{_F136_TRAILING_OVERLAP_RVA:08X}",
        "frontier_trailing_overlap_bytes": _F136_TRAILING_OVERLAP_BYTES.hex(" "),
        "frontier_next_overlap_required": True,
        "frontier_semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "frontier_call_semantics": "UNRESOLVED",
        "frontier_ownership_effect": "NONE",
        "frontier_runtime_validation": "UNTESTED",
    }


def validate_f138_frontier_contract(
    *, frontier: dict, payload: dict, exe_path: Path, source_path: Path, length: int
) -> dict:
    """Fail closed on F138 overlap provenance from the exact F137 cut edge."""
    if frontier.get("continuation_id") != _F138_FRONTIER_CONTINUATION_ID:
        return {}

    actual = bytes.fromhex(payload.get("bytes_hex", ""))
    trailing_offset = _F138_TRAILING_OVERLAP_RVA - _F138_START_RVA
    if (
        frontier.get("rva") != _F138_START_RVA
        or length != len(_F138_EXPECTED_BYTES)
        or payload.get("rva_start") != f"0x{_F138_START_RVA:08X}"
        or payload.get("rva_end_exclusive") != f"0x{_F138_END_RVA:08X}"
        or payload.get("section") != ".text"
        or actual != _F138_EXPECTED_BYTES
        or not actual.startswith(_F138_REQUIRED_OVERLAP_INSTRUCTION)
        or trailing_offset < 0
        or actual[trailing_offset:] != _F138_TRAILING_OVERLAP_BYTES
    ):
        raise ValueError("F138 canonical frontier contract mismatch")

    analyzer = _load_frontier_analyzer(source_path)
    pe = analyzer.parse_pe(exe_path.read_bytes())
    predecessor = analyzer.collect_guarded_gf_target_c_helper_1_third_callee_continuation_102_prefix_proof(pe)
    if (
        predecessor.get("status") != _F138_PREDECESSOR_STATUS
        or predecessor.get("prefix_end_rva") != _F138_START_RVA
        or predecessor.get("incomplete_rva") != _F138_START_RVA
        or predecessor.get("incomplete_bytes") != _F138_PREDECESSOR_CUT_BYTES.hex(" ")
        or not predecessor.get("capture_edge_matches")
        or predecessor.get("unresolved_forward_targets") != _F138_INHERITED_FORWARD_TARGETS
        or predecessor.get("continuation_status")
        != "COMPLETE_INSTRUCTIONS_END_AT_183BC0_TRAILING_68C441_REQUIRES_OVERLAP"
    ):
        raise ValueError("F138 predecessor proof/debt mismatch")

    inbound = analyzer.collect_raw_inbound_rel32_candidates(pe, _F138_START_RVA)
    outbound = analyzer.collect_raw_rel32_call_candidates(pe, _F138_START_RVA, length)
    if inbound:
        raise ValueError("F138 raw inbound rel32 census is not empty")
    if outbound:
        raise ValueError(f"F138 raw outbound rel32 census is not empty: {outbound}")

    return {
        "frontier_contract_status": _F138_CAPTURE_STATUS,
        "frontier_predecessor_status": predecessor["status"],
        "frontier_start_boundary_status": "F137_MANDATORY_OVERLAP_FULL_INSTRUCTION_CONSUMED",
        "frontier_predecessor_cut_bytes": _F138_PREDECESSOR_CUT_BYTES.hex(" "),
        "frontier_required_overlap_instruction": _F138_REQUIRED_OVERLAP_INSTRUCTION.hex(" "),
        "frontier_exact_bytes_match": True,
        "frontier_inherited_unresolved_forward_targets": [],
        "frontier_raw_inbound_rel32_count": 0,
        "frontier_raw_outbound_rel32_count": 0,
        "frontier_trailing_overlap_rva": f"0x{_F138_TRAILING_OVERLAP_RVA:08X}",
        "frontier_trailing_overlap_bytes": _F138_TRAILING_OVERLAP_BYTES.hex(" "),
        "frontier_next_overlap_required": True,
        "frontier_semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "frontier_call_semantics": "UNRESOLVED",
        "frontier_ownership_effect": "NONE",
        "frontier_runtime_validation": "UNTESTED",
    }


def validate_f140_frontier_contract(
    *, frontier: dict, payload: dict, exe_path: Path, source_path: Path, length: int
) -> dict:
    """Fail closed on F140 overlap provenance from the exact F139 cut edge."""
    if frontier.get("continuation_id") != _F140_FRONTIER_CONTINUATION_ID:
        return {}

    actual = bytes.fromhex(payload.get("bytes_hex", ""))
    trailing_offset = _F140_TRAILING_OVERLAP_RVA - _F140_START_RVA
    if (
        frontier.get("rva") != _F140_START_RVA
        or length != len(_F140_EXPECTED_BYTES)
        or payload.get("rva_start") != f"0x{_F140_START_RVA:08X}"
        or payload.get("rva_end_exclusive") != f"0x{_F140_END_RVA:08X}"
        or payload.get("section") != ".text"
        or actual != _F140_EXPECTED_BYTES
        or not actual.startswith(_F140_REQUIRED_OVERLAP_INSTRUCTION)
        or trailing_offset < 0
        or actual[trailing_offset:] != _F140_TRAILING_OVERLAP_BYTES
    ):
        raise ValueError("F140 canonical frontier contract mismatch")

    analyzer = _load_frontier_analyzer(source_path)
    pe = analyzer.parse_pe(exe_path.read_bytes())
    predecessor = analyzer.collect_guarded_gf_target_c_helper_1_third_callee_continuation_103_prefix_proof(pe)
    if (
        predecessor.get("status") != _F140_PREDECESSOR_STATUS
        or predecessor.get("prefix_end_rva") != _F140_START_RVA
        or predecessor.get("incomplete_rva") != _F140_START_RVA
        or predecessor.get("incomplete_bytes") != _F140_PREDECESSOR_CUT_BYTES.hex(" ")
        or not predecessor.get("capture_edge_matches")
        or predecessor.get("unresolved_forward_targets") != _F140_INHERITED_FORWARD_TARGETS
        or predecessor.get("continuation_status")
        != "COMPLETE_INSTRUCTIONS_END_AT_183BFE_TRAILING_FF76_REQUIRES_OVERLAP"
    ):
        raise ValueError("F140 predecessor proof/debt mismatch")

    inbound = analyzer.collect_raw_inbound_rel32_candidates(pe, _F140_START_RVA)
    outbound = analyzer.collect_raw_rel32_call_candidates(pe, _F140_START_RVA, length)
    if inbound:
        raise ValueError("F140 raw inbound rel32 census is not empty")
    if outbound:
        raise ValueError(f"F140 raw outbound rel32 census is not empty: {outbound}")

    return {
        "frontier_contract_status": _F140_CAPTURE_STATUS,
        "frontier_predecessor_status": predecessor["status"],
        "frontier_start_boundary_status": "F139_MANDATORY_OVERLAP_FULL_INSTRUCTION_CONSUMED",
        "frontier_predecessor_cut_bytes": _F140_PREDECESSOR_CUT_BYTES.hex(" "),
        "frontier_required_overlap_instruction": _F140_REQUIRED_OVERLAP_INSTRUCTION.hex(" "),
        "frontier_exact_bytes_match": True,
        "frontier_inherited_unresolved_forward_targets": _F140_INHERITED_FORWARD_TARGETS,
        "frontier_raw_inbound_rel32_count": 0,
        "frontier_raw_outbound_rel32_count": 0,
        "frontier_trailing_overlap_rva": f"0x{_F140_TRAILING_OVERLAP_RVA:08X}",
        "frontier_trailing_overlap_bytes": _F140_TRAILING_OVERLAP_BYTES.hex(" "),
        "frontier_next_overlap_required": True,
        "frontier_semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "frontier_call_semantics": "UNRESOLVED",
        "frontier_ownership_effect": "NONE",
        "frontier_runtime_validation": "UNTESTED",
    }


def validate_f142_frontier_contract(
    *, frontier: dict, payload: dict, exe_path: Path, source_path: Path, length: int
) -> dict:
    """Fail closed on F142 overlap provenance from the exact F141 cut edge."""
    if frontier.get("continuation_id") != _F142_FRONTIER_CONTINUATION_ID:
        return {}

    actual = bytes.fromhex(payload.get("bytes_hex", ""))
    trailing_offset = _F142_TRAILING_OVERLAP_RVA - _F142_START_RVA
    if (
        frontier.get("rva") != _F142_START_RVA
        or length != len(_F142_EXPECTED_BYTES)
        or payload.get("rva_start") != f"0x{_F142_START_RVA:08X}"
        or payload.get("rva_end_exclusive") != f"0x{_F142_END_RVA:08X}"
        or payload.get("section") != ".text"
        or actual != _F142_EXPECTED_BYTES
        or not actual.startswith(_F142_REQUIRED_OVERLAP_INSTRUCTION)
        or trailing_offset < 0
        or actual[trailing_offset:] != _F142_TRAILING_OVERLAP_BYTES
    ):
        raise ValueError("F142 canonical frontier contract mismatch")

    analyzer = _load_frontier_analyzer(source_path)
    pe = analyzer.parse_pe(exe_path.read_bytes())
    predecessor = analyzer.collect_guarded_gf_target_c_helper_1_third_callee_continuation_104_prefix_proof(pe)
    if (
        predecessor.get("status") != _F142_PREDECESSOR_STATUS
        or predecessor.get("prefix_end_rva") != _F142_START_RVA
        or predecessor.get("incomplete_rva") != _F142_START_RVA
        or predecessor.get("incomplete_bytes") != _F142_PREDECESSOR_CUT_BYTES.hex(" ")
        or not predecessor.get("capture_edge_matches")
        or predecessor.get("unresolved_forward_targets") != _F142_INHERITED_FORWARD_TARGETS
        or predecessor.get("remaining_predecessor_external_targets") != []
        or predecessor.get("continuation_status")
        != "COMPLETE_INSTRUCTIONS_END_AT_183C3D_TRAILING_EB_REQUIRES_OVERLAP"
    ):
        raise ValueError("F142 predecessor proof/debt mismatch")

    inbound = analyzer.collect_raw_inbound_rel32_candidates(pe, _F142_START_RVA)
    outbound = analyzer.collect_raw_rel32_call_candidates(pe, _F142_START_RVA, length)
    if inbound:
        raise ValueError(f"F142 raw inbound rel32 census is not empty: {inbound}")
    if outbound:
        raise ValueError(f"F142 raw outbound rel32 census is not empty: {outbound}")

    return {
        "frontier_contract_status": _F142_CAPTURE_STATUS,
        "frontier_predecessor_status": predecessor["status"],
        "frontier_start_boundary_status": "F141_MANDATORY_OVERLAP_FULL_INSTRUCTION_CONSUMED",
        "frontier_predecessor_cut_bytes": _F142_PREDECESSOR_CUT_BYTES.hex(" "),
        "frontier_required_overlap_instruction": _F142_REQUIRED_OVERLAP_INSTRUCTION.hex(" "),
        "frontier_exact_bytes_match": True,
        "frontier_inherited_unresolved_forward_targets": [],
        "frontier_raw_inbound_rel32_count": 0,
        "frontier_raw_outbound_rel32_count": 0,
        "frontier_trailing_overlap_rva": f"0x{_F142_TRAILING_OVERLAP_RVA:08X}",
        "frontier_trailing_overlap_bytes": _F142_TRAILING_OVERLAP_BYTES.hex(" "),
        "frontier_next_overlap_required": True,
        "frontier_semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "frontier_call_semantics": "UNRESOLVED",
        "frontier_ownership_effect": "NONE",
        "frontier_runtime_validation": "UNTESTED",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument("--rva", type=_parse_rva)
    location.add_argument("--frontier-source", type=Path)
    parser.add_argument("--length", type=int, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--source-sha", default="")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    frontier = (
        discover_frontier_rva(args.frontier_source)
        if args.frontier_source
        else None
    )
    rva = frontier["rva"] if frontier else args.rva
    payload = extract_window(
        exe_path=args.exe,
        rva=rva,
        length=args.length,
        expected_sha256=args.expected_sha256,
        source_sha=args.source_sha,
    )
    if frontier:
        payload["frontier_continuation_id"] = frontier["continuation_id"]
        payload["frontier_basis"] = frontier["basis"]
        payload["frontier_source"] = str(args.frontier_source)
        for validator in (
            validate_f124_frontier_contract,
            validate_f126_frontier_contract,
            validate_f128_frontier_contract,
            validate_f130_frontier_contract,
            validate_f132_frontier_contract,
            validate_f134_frontier_contract,
            validate_f136_frontier_contract,
            validate_f138_frontier_contract,
            validate_f140_frontier_contract,
            validate_f142_frontier_contract,
        ):
            payload.update(
                validator(
                    frontier=frontier,
                    payload=payload,
                    exe_path=args.exe,
                    source_path=args.frontier_source,
                    length=args.length,
                )
            )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

