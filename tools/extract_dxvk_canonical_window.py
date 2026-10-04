#!/usr/bin/env python3
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
        payload.update(
            validate_f124_frontier_contract(
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
