#!/usr/bin/env python3
"""
Verify that executable-RVA hooks are tied to the exact canonical OR2006C2C.EXE
used by upstream OutRun2006Tweaks.

The verifier intentionally works on the on-disk PE before load/relocation.
Strict mode gates a candidate on:
  * SHA-256 identity
  * PE32/x86 machine type
  * image base
  * exact byte signatures at reviewed RVAs
  * source bindings that prove the reviewed RVA is still the one in source

Discovery mode prints the identity/signatures/disassembly needed to pin a new
canonical manifest. It does not weaken strict mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import sys
from dataclasses import dataclass
from typing import Iterable


IMAGE_FILE_MACHINE_I386 = 0x014C


@dataclass(frozen=True)
class Section:
    name: str
    virtual_address: int
    virtual_size: int
    raw_size: int
    raw_pointer: int

    def contains_rva(self, rva: int) -> bool:
        span = max(self.virtual_size, self.raw_size)
        return self.virtual_address <= rva < self.virtual_address + span


@dataclass(frozen=True)
class PEInfo:
    machine: int
    image_base: int
    size_of_headers: int
    sections: tuple[Section, ...]


def parse_int(value: object) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    return int(text, 0)


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_pe(data: bytes) -> PEInfo:
    if len(data) < 0x100 or data[:2] != b"MZ":
        raise ValueError("not a DOS/PE executable")
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_off + 24 > len(data) or data[pe_off:pe_off + 4] != b"PE\0\0":
        raise ValueError("PE signature missing")

    file_hdr = pe_off + 4
    machine, section_count, _time, _sym, _nsyms, opt_size, _chars = struct.unpack_from(
        "<HHIIIHH", data, file_hdr
    )
    opt = file_hdr + 20
    if opt + opt_size > len(data):
        raise ValueError("optional header outside file")
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic != 0x10B:
        raise ValueError(f"expected PE32 optional header, got 0x{magic:04X}")

    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    size_of_headers = struct.unpack_from("<I", data, opt + 60)[0]

    sec_off = opt + opt_size
    sections: list[Section] = []
    for i in range(section_count):
        off = sec_off + i * 40
        if off + 40 > len(data):
            raise ValueError("section table truncated")
        raw_name = data[off:off + 8].split(b"\0", 1)[0]
        name = raw_name.decode("ascii", errors="replace")
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", data, off + 8
        )
        sections.append(
            Section(name, virtual_address, virtual_size, raw_size, raw_pointer)
        )

    return PEInfo(machine, image_base, size_of_headers, tuple(sections))


def rva_to_offset(pe: PEInfo, rva: int) -> int:
    if rva < pe.size_of_headers:
        return rva
    for sec in pe.sections:
        if sec.contains_rva(rva):
            delta = rva - sec.virtual_address
            if delta >= sec.raw_size:
                raise ValueError(
                    f"RVA 0x{rva:X} lies in zero-fill tail of section {sec.name}"
                )
            return sec.raw_pointer + delta
    raise ValueError(f"RVA 0x{rva:X} is not mapped by any PE section")


def bytes_at(data: bytes, pe: PEInfo, rva: int, count: int) -> bytes:
    off = rva_to_offset(pe, rva)
    end = off + count
    if end > len(data):
        raise ValueError(f"RVA 0x{rva:X} signature exceeds file")
    return data[off:end]


def normalize_hex(text: str) -> str:
    return "".join(text.split()).lower()


def disassemble_x86(blob: bytes, address: int) -> list[str]:
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    except Exception:
        return ["<capstone unavailable; byte signature still available>"]

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    lines: list[str] = []
    for insn in md.disasm(blob, address):
        op = f" {insn.op_str}" if insn.op_str else ""
        lines.append(f"0x{insn.address:08X}: {insn.mnemonic}{op}")
    if not lines:
        lines.append("<no instruction decoded>")
    return lines


def validate_source_bindings(root: pathlib.Path, bindings: Iterable[dict]) -> list[str]:
    errors: list[str] = []
    for binding in bindings:
        rel = pathlib.PurePosixPath(binding["path"])
        path = root.joinpath(*rel.parts)
        if not path.exists():
            errors.append(f"source binding missing file: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        needle = str(binding["needle"])
        if needle not in text:
            errors.append(f"source binding missing needle in {rel}: {needle}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True, type=pathlib.Path)
    ap.add_argument("--manifest", required=True, type=pathlib.Path)
    ap.add_argument("--source-root", default=".", type=pathlib.Path)
    ap.add_argument("--discover", action="store_true")
    args = ap.parse_args()

    data = args.exe.read_bytes()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    pe = parse_pe(data)
    digest = sha256_file(args.exe)

    identity = {
        "sha256": digest,
        "machine": f"0x{pe.machine:04X}",
        "imageBase": f"0x{pe.image_base:08X}",
        "size": len(data),
    }
    print("CANONICAL_EXE_IDENTITY=" + json.dumps(identity, sort_keys=True))

    errors: list[str] = []
    canonical = manifest.get("canonicalExe", {})
    expected_sha = str(canonical.get("sha256", "")).strip().lower()
    expected_base = canonical.get("imageBase")

    if not args.discover:
        if not expected_sha or expected_sha == "discover":
            errors.append("manifest canonicalExe.sha256 is not pinned")
        elif digest.lower() != expected_sha:
            errors.append(
                f"canonical EXE SHA-256 mismatch: got {digest}, expected {expected_sha}"
            )

        if pe.machine != IMAGE_FILE_MACHINE_I386:
            errors.append(
                f"canonical EXE machine mismatch: got 0x{pe.machine:04X}, expected x86/0x014C"
            )

        if expected_base not in (None, "", "discover"):
            base = parse_int(expected_base)
            if pe.image_base != base:
                errors.append(
                    f"image base mismatch: got 0x{pe.image_base:X}, expected 0x{base:X}"
                )

    source_root = args.source_root.resolve()
    for contract in manifest.get("contracts", []):
        cid = str(contract["id"])
        rva = parse_int(contract["rva"])
        sig_len = int(contract.get("signatureLength", 16))
        window_len = max(sig_len, int(contract.get("disassemblyWindow", 32)))
        blob = bytes_at(data, pe, rva, window_len)
        signature = blob[:sig_len].hex()

        record = {
            "id": cid,
            "rva": f"0x{rva:08X}",
            "signatureLength": sig_len,
            "expectedBytes": signature,
            "disassembly": disassemble_x86(blob, pe.image_base + rva),
        }
        print("CONTRACT_DISCOVERY=" + json.dumps(record, ensure_ascii=False))

        expected = normalize_hex(str(contract.get("expectedBytes", "")))
        if not args.discover:
            if not expected or expected == "discover":
                errors.append(f"{cid}: expectedBytes is not pinned")
            elif signature != expected:
                errors.append(
                    f"{cid}: byte signature mismatch at RVA 0x{rva:X}: "
                    f"got {signature}, expected {expected}"
                )

        errors.extend(
            f"{cid}: {err}"
            for err in validate_source_bindings(
                source_root, contract.get("sourceBindings", [])
            )
        )

    if errors:
        for err in errors:
            print("BINARY_CONTRACT_ERROR: " + err, file=sys.stderr)
        return 2

    mode = "DISCOVERY" if args.discover else "STRICT"
    print(f"VR binary contract verification passed ({mode}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
