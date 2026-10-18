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
    ("stage-extension-animation", 0x00098000, 0x00099000),
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



# Exact x86 relationships independently checked with N100 REA/Ghidra
# against the canonical SHA. The sixth CALL is inside the *mode-2*
# jump-table case; B4/B5 animation/text are distinct +TIME paths.
STAGE_CALL_EDGES = (
    (0x9898E, 0x29530, "B4 animated sprite"),
    (0x989AD, 0x973C0, "B4 text"),
    (0x98A10, 0x974E0, "B4 number"),
    (0x98A36, 0x29530, "B5 animated sprite"),
    (0x98A89, 0x973C0, "B5 text"),
    (0x98AC6, 0x29530, "mode-2 animated sprite (not B4/B5)"),
)
STAGE_MODE2_JUMP_CASES = (0x98ABC, 0x98C42, 0x98C97, 0x98CD9)


def verify_stage_source_hook_boundary(source: str) -> None:
    """Never relocate an E9 hook over the original JNZ landing at 98A18."""
    safe = "callRva == 0x98A10 ? 0x98A18 : callRva + 5"
    assert safe in source, "unsafe 0x98A10 post-CALL hook mapping"
    assert "Module::exe_ptr(StageExtensionLeaveHookRva(rva)), StageExtensionLeave" in source
    assert "0x9898E, 0x98A36, 0x98AC6" in source
    assert "0x989AD, 0x98A10, 0x98A89" in source


def verify_stage_original_binary(pe, source: str) -> list[str]:
    """Pin six CALL edges + original branch and mode-2 jump-table origin."""
    from struct import unpack
    verify_stage_source_hook_boundary(source)
    read = pe.bytes_at_rva
    facts: list[str] = []
    for call_rva, target_rva, label in STAGE_CALL_EDGES:
        insn = read(call_rva, 5)
        assert len(insn) == 5 and insn[0] == 0xE8, (
            f"{label}: expected original CALL rel32 at RVA {call_rva:#x}")
        actual = (call_rva + 5 + unpack("<i", insn[1:])[0]) & 0xFFFFFFFF
        assert actual == target_rva, (
            f"{label}: expected {target_rva:#x}, found {actual:#x}")
        facts.append(f"- RVA `0x{call_rva:05X}` -> "
                     f"`0x{target_rva:05X}` ({label})")
    jnz = read(0x98958, 6)
    assert len(jnz) == 6 and jnz[:2] == bytes((0x0F, 0x85)), (
        "REA branch guard: expected JNZ rel32 at 0x98958")
    landing = (0x98958 + 6 + unpack("<i", jnz[2:])[0]) & 0xFFFFFFFF
    assert landing == 0x98A18, f"unexpected original JNZ landing {landing:#x}"
    assert read(0x98A15, 3) == bytes((0x83, 0xC4, 0x40)), (
        "0x98A15 is not the expected 3-byte ADD ESP,0x40")
    assert read(0x98A18, 3) == bytes((0x66, 0x3B, 0xF3)), (
        "branch does not enter the expected CMP at 0x98A18")
    jump = read(0x98FFC, 16)
    assert len(jump) == 16
    table = unpack("<4I", jump)
    image_base = pe.image_base
    actual_cases = tuple(x - image_base for x in table)
    assert actual_cases == STAGE_MODE2_JUMP_CASES, (
        f"mode-2 selector jump table changed: {actual_cases!r}")
    assert 0x98ABC < 0x98AC6 < 0x98C42, (
        "0x98AC6 no longer belongs to the mode-2 branch")
    facts.extend((
        "- 0x98958 JNZ lands at RVA 0x98A18, inside an unsafe 5-byte "
        "detour beginning at 0x98A15; current source uses the safe 0x98A18 hook.",
        "- 0x98FFC mode-2 state jump table is 0x98ABC / 0x98C42 / "
        "0x98C97 / 0x98CD9. 0x98AC6 belongs to the first mode-2 case, "
        "not the B4/B5 +TIME transition.",
    ))
    return facts


def test_stage_source_guard_negative(source: str) -> None:
    """Prove the source verifier rejects a replay of the original crash."""
    safe = "callRva == 0x98A10 ? 0x98A18 : callRva + 5"
    mutant = source.replace(safe, "callRva + 5", 1)
    assert mutant != source
    try:
        verify_stage_source_hook_boundary(mutant)
    except AssertionError:
        return
    raise AssertionError("negative test allowed unsafe return detour")


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
    source = Path(__file__).resolve().parents[1].joinpath("src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
    stage_facts = verify_stage_original_binary(pe, source)
    test_stage_source_guard_negative(source)
    dis = Cs(CS_ARCH_X86, CS_MODE_32)
    dis.detail = False
    out = [f"# Canonical OR2006C2C.EXE symbolic P0 source disassembly",
           f"SHA256={digest}", "Only the source-to-target function relationships",
           "and disassembled command flow are used for actionable code changes.",
           ""]
    out.extend(["## REA exact +TIME / mode-2 source and branch guard", *stage_facts, ""])
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