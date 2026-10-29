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
    ("goal-result-time-panel", 0x00098000, 0x00099000),
    # Live race time-extension path: 450CC0 sets manager flag3/time, the
    # Navi control/display pair turns that into the 8446E8 HUD lifetime,
    # and 4B9320/4B9250 emit the split/time sprites and glyphs.
    ("race-time-extend-state", 0x00050C80, 0x00050E20),
    ("navi-time-extend-split", 0x000B9200, 0x000B9480),
    # 4BD0A0 is called from Navi display at 0xBEDE0 every frame, but it
    # conditionally emits the live timer/split popup only while 8446E8 > 0.
    # Disassemble its body so we can hook the conditional display edge rather
    # than the unconditional outer display call.
    ("navi-live-time-popup-dispatch", 0x000BD080, 0x000BD240),
    ("navi-race-display", 0x000BEA80, 0x000BEE20),
    ("goal-record-helpers", 0x000BE000, 0x000BEB20),
    # Original opaque object queue core. 0x4056D0 enqueues DrawObjectAlpha
    # work; 0x4052C0 later consumes the shared queue. Keeping these bodies in
    # the durable artifact is required before assigning a CABE ordinal to a
    # physical PMT/Draw.
    ("lens-opaque-queue-core", 0x000050C0, 0x00005B20),
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



# Exact x86 relationships independently checked against the canonical SHA.
# IMPORTANT 2026-10-29 correction: these 0x989xx edges belong to the
# GAD_PUB GOAL/result-time panel in 0x498670. They are NOT the live in-race
# checkpoint +TIME popup. The sixth CALL remains a separate mode-2 result case.
STAGE_CALL_EDGES = (
    (0x9898E, 0x29530, "B4 animated sprite"),
    (0x989AD, 0x973C0, "B4 text"),
    (0x98A10, 0x974E0, "B4 number"),
    (0x98A36, 0x29530, "B5 animated sprite"),
    (0x98A89, 0x973C0, "B5 text"),
    (0x98AC6, 0x29530, "mode-2 animated sprite (not B4/B5)"),
)
STAGE_MODE2_JUMP_CASES = (0x98ABC, 0x98C42, 0x98C97, 0x98CD9)
LIVE_STAGE_CALL_RVA = 0xBD217
LIVE_STAGE_TARGET_RVA = 0xB9320
LIVE_STAGE_LEAVE_RVA = 0xBD221

LENS_ENQUEUE_RVA = 0x56D0
LENS_FLUSH_RVA = 0x52C0
LENS_OBJECT_DISPATCH_RVA = 0x5360
LENS_RENDER_FLUSH_RVA = 0x5890
LENS_WRAPPER_EDGES = (
    (0xC993, LENS_ENQUEUE_RVA, "C993 centre wrapper -> opaque enqueue"),
    (0xCABE, LENS_ENQUEUE_RVA, "CABE projected wrapper -> opaque enqueue"),
)
LENS_FLUSH_EDGES = (
    (0xD44B, LENS_FLUSH_RVA, "first scene-effect queue flush"),
    (0xD79B, LENS_FLUSH_RVA, "outer lens-child queue flush"),
)
LENS_570008_CALLS = (
    (0xD6B5, 0xD6BA, "570008 before 0xD79B flush"),
    (0xD7AF, 0xD7B4, "570008 after 0xD79B flush"),
)


def verify_stage_source_hook_boundary(source: str) -> None:
    """Never relocate an E9 hook over the original JNZ landing at 98A18."""
    safe = "callRva == 0x98A10 ? 0x98A18 : callRva + 5"
    assert safe in source, "unsafe 0x98A10 post-CALL hook mapping"
    assert "Module::exe_ptr(StageExtensionLeaveHookRva(rva)), StageExtensionLeave" in source
    from re import search
    group = search(r"StageExtensionSpraniCalls\[\]\s*=\s*\{([^}]*)\}", source)
    assert group is not None, "stage animation source array is missing"
    values = tuple(int(x.strip(), 16) for x in group.group(1).split(",") if x.strip())
    assert values == (0x9898E, 0x98A36), (
        "REA mode-2 0x98AC6 must NOT inherit +TIME ScreenHud ownership")
    assert "0x98AC6" in source, "REA mode-2 source separation context missing"
    assert "0x989AD, 0x98A10, 0x98A89" in source
    assert "LiveStageExtensionCallRva = 0xBD217" in source
    assert "LiveStageExtensionLeaveRva = 0xBD221" in source
    assert "Module::exe_ptr(LiveStageExtensionCallRva)" in source
    assert "Module::exe_ptr(LiveStageExtensionLeaveRva)" in source


def verify_stage_original_binary(pe, source: str) -> list[str]:
    """Pin GOAL/result panel CALL edges + original branch/jump-table origin."""
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
    live = read(LIVE_STAGE_CALL_RVA, 5)
    assert len(live) == 5 and live[0] == 0xE8, "live +TIME expected E8 at 0xBD217"
    live_target = (LIVE_STAGE_CALL_RVA + 5 + unpack("<i", live[1:])[0]) & 0xFFFFFFFF
    assert live_target == LIVE_STAGE_TARGET_RVA, f"live +TIME expected 0xB9320, found {live_target:#x}"
    assert read(LIVE_STAGE_LEAVE_RVA, 5) == bytes((0xC3, 0xCC, 0xCC, 0xCC, 0xCC)), "live +TIME safe leave RET/padding changed"
    facts.extend((
        "- Live checkpoint +TIME: RVA 0xBD217 -> 0xB9320 after 4BD0A0 proves 8446E8 > 0 and variant 0/1.",
        "- Safe live +TIME leave is RVA 0xBD221 RET plus INT3 padding; 0xBD21C is a shared branch target.",
        "- 0x98958 JNZ lands at RVA 0x98A18, inside an unsafe 5-byte "
        "detour beginning at 0x98A15; current source uses the safe 0x98A18 hook.",
        "- 0x98FFC mode-2 state jump table is 0x98ABC / 0x98C42 / "
        "0x98C97 / 0x98CD9. 0x98AC6 belongs to the first mode-2 case, "
        "not the B4/B5 +TIME transition.",
    ))
    return facts


def verify_lens_original_queue_edges(pe) -> list[str]:
    """Pin enqueue/flush boundaries without claiming descriptor identity."""
    from struct import unpack

    read = pe.bytes_at_rva
    facts: list[str] = []

    def call_target(call_rva: int) -> int:
        insn = read(call_rva, 5)
        assert len(insn) == 5 and insn[0] == 0xE8, (
            f"expected original CALL rel32 at RVA {call_rva:#x}")
        return (call_rva + 5 + unpack("<i", insn[1:])[0]) & 0xFFFFFFFF

    for call_rva, target_rva, label in (*LENS_WRAPPER_EDGES, *LENS_FLUSH_EDGES):
        actual = call_target(call_rva)
        assert actual == target_rva, (
            f"{label}: expected {target_rva:#x}, found {actual:#x}")
        facts.append(
            f"- RVA `0x{call_rva:05X}` -> `0x{target_rva:05X}` ({label}).")

    # 4056D0 itself calls 405360, and 405360 conditionally calls 4052C0.
    # Therefore a source wrapper can cause an inline flush OR leave work for
    # the later D44B/D79B shared flush depending on original game state.
    assert call_target(0x5813) == LENS_OBJECT_DISPATCH_RVA, (
        "4056D0 no longer dispatches through 405360")
    assert call_target(0x542A) == LENS_FLUSH_RVA, (
        "405360 inline flush edge to 4052C0 changed")
    assert call_target(0x52C6) == LENS_RENDER_FLUSH_RVA, (
        "4052C0 render flush edge to 405890 changed")
    facts.extend((
        "- RVA `0x05813` inside 4056D0 calls `0x05360`.",
        "- RVA `0x0542A` inside 405360 conditionally calls `0x052C0`; "
        "an opaque flush may therefore occur before the source wrapper returns.",
        "- RVA `0x052C6` inside 4052C0 calls `0x05890`, the render/queue "
        "consumer that must be inspected for descriptor-to-physical-Draw identity.",
    ))

    # The same 0x570008 scene object is submitted once before and once after
    # the second shared queue flush. This proves CALL ordinal alone cannot be
    # treated as the identity of a later opaque PMT consumed by 0x4052C0.
    for push_rva, call_rva, label in LENS_570008_CALLS:
        push = read(push_rva, 5)
        assert push == bytes((0x68, 0x08, 0x00, 0x57, 0x00)), (
            f"{label}: 0x570008 PUSH changed at {push_rva:#x}")
        target = call_target(call_rva)
        assert target == 0xC9A0, (
            f"{label}: expected projected wrapper 0xC9A0, found {target:#x}")
        facts.append(
            f"- RVA `0x{push_rva:05X}` pushes `0x570008` and "
            f"`0x{call_rva:05X}` calls `0x0C9A0` ({label}).")

    assert LENS_570008_CALLS[0][1] < LENS_FLUSH_EDGES[1][0] < LENS_570008_CALLS[1][0], (
        "0x570008 before/flush/after ordering changed")
    facts.append(
        "- Therefore CABE call-stack ordinal is source chronology only; "
        "opaque PMT identity remains UNVERIFIED until the 0x4056D0/0x405360 "
        "descriptor lifetime and 0x4052C0/0x405890 consumer are joined.")
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
    lens_queue_facts = verify_lens_original_queue_edges(pe)
    test_stage_source_guard_negative(source)
    dis = Cs(CS_ARCH_X86, CS_MODE_32)
    dis.detail = False
    out = [f"# Canonical OR2006C2C.EXE symbolic P0 source disassembly",
           f"SHA256={digest}", "Only the source-to-target function relationships",
           "and disassembled command flow are used for actionable code changes.",
           ""]
    out.extend(["## Exact GOAL result-time panel / mode-2 branch guard", *stage_facts, "",
                "## Original lens opaque queue boundary", *lens_queue_facts, "",
                "## Live +TIME investigation contract",
                "- Race-manager 0x450CC0 is the actual time-extension state transition.",
                "- Navi 0x4B93E0 observes manager flag3 and arms HUD timer 0x8446E8.",
                "- Navi display 0x4BEB00 consumes 0x8446E8; OutRun variants route to 0x4B9320.",
                "- 0x4B9320 -> 0x4B9250 emits the split/time glyphs and 0x2C00BC frame; "
                "variant 0 can also create 0x2C00BD on the extension flash.",
                "- Exact original E8 call RVAs are read from the new disassembly windows below; "
                "no source owner is inferred from the old 0x989xx hooks.", ""])
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