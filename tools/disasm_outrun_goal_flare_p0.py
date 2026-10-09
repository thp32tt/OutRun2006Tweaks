#!/usr/bin/env python3
"""Read-only exact canonical EXE disassembly for three VR HMD optical P0 faults.

Run in HUD Inspector CI after downloading the public upstream replacement EXE
and verifying the exact SHA-256. This script does NOT publish executable bytes.
Disassembly is an investigation artifact; only original E8 signatures and
producer structures established from it may inform source modifications.
"""
import argparse
import hashlib
from pathlib import Path

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from analyze_outrun_exe import parse_pe

EXPECTED_SHA = "68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3"
WINDOWS = (
    ("goal-result-stage", 0x00097000, 0x00098000),
    ("goal-record-helpers", 0x000BE000, 0x000BEB20),
    ("lens-objects", 0x0000C900, 0x0000D950),
    ("sprite-glyph-queue", 0x0002C800, 0x0002D300),
    ("calc3d2d", 0x00049940, 0x00049B20),
)
ANCHORS = (
    0x000975EE, 0x00097727, 0x000977FB, 0x00097BB7,
    0x00097BE4, 0x00097DA7, 0x00097DEC,
    0x000BEA5A, 0x000BEA5F, 0x0000CABE,
    0x0000CF4E, 0x0002C808, 0x0002C9DB,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    binary = Path(args.exe).read_bytes()
    digest = hashlib.sha256(binary).hexdigest()
    if digest != EXPECTED_SHA:
        raise SystemExit("Canonical EXE SHA mismatch: " + digest)
    pe = parse_pe(binary)
    dis = Cs(CS_ARCH_X86, CS_MODE_32)
    dis.detail = False
    out = [f"# Canonical OR2006C2C.EXE symbolic P0 source disassembly",
           f"SHA256={digest}", "Only the source-to-target function relationships",
           "and disassembled command flow are used for actionable code changes.",
           ""]
    for title, start, end in WINDOWS:
        blob = pe.bytes_at_rva(start, end - start)
        if len(blob) != end - start:
            raise SystemExit("Cannot read code RVA window "+title)
        out.extend([f"## {title} 0x{start:06X}..0x{end:06X}",
                    f"Window SHA256={hashlib.sha256(blob).hexdigest()}"])
        count = 0
        for ins in dis.disasm(blob, pe.image_base + start):
            rva = ins.address - pe.image_base
            tag = " << EXACT HOOK >>" if rva in ANCHORS else ""
            out.append(f"0x{rva:06X} {ins.mnemonic:<9} {ins.op_str}{tag}")
            count += 1
        if count < 10:
            raise SystemExit("Disassembly unexpectedly empty: "+title)
        out.append("")
    p = Path(args.out_dir)
    p.mkdir(parents=True, exist_ok=True)
    (p / "DX9EX_CANONICAL_GOAL_TIME_LENS_P0.asm.md").write_text(
        "\n".join(out) + "\n", encoding="utf-8")
    print(f"DX9Ex original P0 deep disassembly generated: {len(out)} lines")


if __name__ == "__main__":
    main()
