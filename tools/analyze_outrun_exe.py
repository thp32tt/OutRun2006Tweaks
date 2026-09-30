#!/usr/bin/env python3
"""Static OR2006C2C.EXE HUD/render anchor analyzer.

No third-party packages are required. The script parses PE32 headers, fingerprints
known OutRun rendering functions, finds direct x86 CALL rel32 references to known
HUD/sprite targets, and emits JSON + Markdown suitable for CI artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path

KNOWN_TARGETS = {
    0x02CFE0: "put_sprite_ex",
    0x029580: "sprani_play_ae_auth_alpha",
    0x02D280: "put_clip_sprite",
    0x02CCB0: "sprSetFontPriority",
    0x02CA60: "sprSetPrintFont",
    0x02CCA0: "sprSetFontColor",
    0x02CC60: "sprSetFontScale",
    0x02CC00: "sprLocateP",
    0x02CCE0: "sprPrintf",
    0x02CDD0: "Sumo_Printf",
    0x049940: "Calc3D2D",
    0x0BAD20: "RankMarker_sub_4BAD20",
}

KNOWN_CALL_SITES = {
    0x0BB0FB: "RankMarker sprani #1",
    0x0BB133: "RankMarker sprani #2",
    0x0BB16C: "RankMarker sprani #3",
    0x0BB1A5: "RankMarker sprani #4",
    0x0BB21F: "RankMarker clip #1",
    0x0BB241: "RankMarker clip #2",
    0x0BB271: "RankMarker clip #3",
    0x0BB2BC: "RankMarker clip #4",
    0x0BB2D0: "RankMarker clip #5",
}

# R135/F13: exact hook RVAs that remain intentionally spacing-only until
# direct-call adjacency/effect provenance is independently established.
# The static analyzer records nearby known sprite/HUD calls from the exact
# upstream EXE; this is evidence collection only and must not promote ownership.
GF_HOOK_PROVENANCE_RVAS = {
    0x0FE8B1: "C2CSpeechBubbleGF uncertain/no-effect spacing hook",
    0x0FD60C: "C2CSpeechBubbleGFHeart spacing hook #1",
    0x0FD591: "C2CSpeechBubbleGFHeart spacing hook #2",
    0x0FD5CD: "C2CSpeechBubbleGFHeart spacing hook #3",
    0x0FD652: "C2CSpeechBubbleGFHeart spacing hook #4",
}


# R137/F13: recurring exact-EXE rel32 targets discovered by the guarded-hook
# raw census. These labels are deliberately neutral: target identity/effect and
# instruction alignment still require independent evidence.
GF_RAW_REL32_TARGET_RVAS = {
    0x000653C0: "guarded GF raw rel32 target A",
    0x00065860: "guarded GF raw rel32 target B",
    0x00065970: "guarded GF raw rel32 target C",
}
GF_RAW_REL32_TARGET_WINDOW = 96

# R138/F13: exact-byte instruction-boundary anchor for guarded-GF target B.
# This deliberately proves only that the first outbound E8 at 0x65874 is on a
# manually reviewed, contiguous x86 instruction boundary beginning at the
# prologue-like 0x65860 anchor. Function identity/effect remains unresolved.
GF_TARGET_B_ENTRY_RVA = 0x00065860
GF_TARGET_B_ALIGNED_CALL_RVA = 0x00065874
GF_TARGET_B_ALIGNED_CALL_TARGET_RVA = 0x000285A0
GF_TARGET_B_PREFIX_INSTRUCTIONS = (
    (0x00065860, "56", "push esi"),
    (0x00065861, "8b f1", "mov esi, ecx"),
    (0x00065863, "8b 46 08", "mov eax, [esi+0x08]"),
    (0x00065866, "57", "push edi"),
    (0x00065867, "33 ff", "xor edi, edi"),
    (0x00065869, "83 f8 ff", "cmp eax, -1"),
    (0x0006586C, "74 1b", "je +0x1b"),
    (0x0006586E, "39 7e 24", "cmp [esi+0x24], edi"),
    (0x00065871, "75 09", "jne +0x09"),
    (0x00065873, "50", "push eax"),
    (0x00065874, "e8 27 2d fc ff", "call rel32"),
    (0x00065879, "83 c4 04", "add esp, 4"),
)


# R140/F13: bounded exact-EXE provenance for the helper reached by the proven
# 0x65874 CALL. This captures helper identity/call topology only. Raw E8 scans
# inside the helper are still not instruction-boundary proof, and no semantic
# ownership is promoted from this evidence alone.
GF_TARGET_B_HELPER_RVA = 0x000285A0
GF_TARGET_B_HELPER_WINDOW = 128
GF_TARGET_B_HELPER_FINGERPRINT_BYTES = 96

# R144/F13: extend the exact-byte instruction-boundary anchor for guarded-GF
# target C through the third/final raw outbound candidate. This proves only
# that 0x65997, 0x659AC and 0x659C1 are instruction-aligned CALLs from the
# reviewed 0x65970 prefix. Helper semantics and draw ownership remain unresolved.
GF_TARGET_C_ENTRY_RVA = 0x00065970
GF_TARGET_C_ALIGNED_CALL_RVA = 0x00065997
GF_TARGET_C_ALIGNED_CALL_TARGET_RVA = 0x00028460
GF_TARGET_C_SECOND_ALIGNED_CALL_RVA = 0x000659AC
GF_TARGET_C_SECOND_ALIGNED_CALL_TARGET_RVA = 0x00028320
GF_TARGET_C_THIRD_ALIGNED_CALL_RVA = 0x000659C1
GF_TARGET_C_THIRD_ALIGNED_CALL_TARGET_RVA = 0x00028800
GF_TARGET_C_PREFIX_INSTRUCTIONS = (
    (0x00065970, "56", "push esi"),
    (0x00065971, "8b f1", "mov esi, ecx"),
    (0x00065973, "8b 46 24", "mov eax, [esi+0x24]"),
    (0x00065976, "85 c0", "test eax, eax"),
    (0x00065978, "75 57", "jne +0x57"),
    (0x0006597A, "8b 4e 0c", "mov ecx, [esi+0x0c]"),
    (0x0006597D, "83 f9 ff", "cmp ecx, -1"),
    (0x00065980, "74 1f", "je +0x1f"),
    (0x00065982, "8b 46 10", "mov eax, [esi+0x10]"),
    (0x00065985, "83 f8 ff", "cmp eax, -1"),
    (0x00065988, "74 17", "je +0x17"),
    (0x0006598A, "8b 16", "mov edx, [esi]"),
    (0x0006598C, "50", "push eax"),
    (0x0006598D, "8b 46 18", "mov eax, [esi+0x18]"),
    (0x00065990, "51", "push ecx"),
    (0x00065991, "8b 4e 14", "mov ecx, [esi+0x14]"),
    (0x00065994, "50", "push eax"),
    (0x00065995, "51", "push ecx"),
    (0x00065996, "52", "push edx"),
    (0x00065997, "e8 c4 2a fc ff", "call rel32"),
    (0x0006599C, "83 c4 14", "add esp, 0x14"),
    (0x0006599F, "eb 13", "jmp +0x13"),
    (0x000659A1, "8b 46 18", "mov eax, [esi+0x18]"),
    (0x000659A4, "8b 4e 14", "mov ecx, [esi+0x14]"),
    (0x000659A7, "8b 16", "mov edx, [esi]"),
    (0x000659A9, "50", "push eax"),
    (0x000659AA, "51", "push ecx"),
    (0x000659AB, "52", "push edx"),
    (0x000659AC, "e8 6f 29 fc ff", "call rel32"),
    (0x000659B1, "83 c4 0c", "add esp, 0x0c"),
    (0x000659B4, "83 f8 ff", "cmp eax, -1"),
    (0x000659B7, "89 46 08", "mov [esi+0x08], eax"),
    (0x000659BA, "74 24", "je +0x24"),
    (0x000659BC, "8b 4e 3c", "mov ecx, [esi+0x3c]"),
    (0x000659BF, "51", "push ecx"),
    (0x000659C0, "50", "push eax"),
    (0x000659C1, "e8 3a 2e fc ff", "call rel32"),
)

# R146/F13: bounded exact-EXE proof for the first helper reached from target C.
# The prefix proves packed-selector lookup/control flow only. Full helper effect
# and render/ScreenHud ownership remain unresolved and must not be inferred.
GF_TARGET_C_HELPER_1_RVA = 0x00028460
GF_TARGET_C_HELPER_PROBE_LEN = 128
GF_TARGET_C_HELPER_1_RANGE_FALLBACK_RVA = 0x00028588
GF_TARGET_C_HELPER_1_MISS_CLEANUP_RVA = 0x000284A6
GF_TARGET_C_HELPER_1_SUCCESS_CONTINUATION_RVA = 0x000284B0
GF_TARGET_C_HELPER_1_TABLE_BASE = 0x009568B8
GF_TARGET_C_HELPER_1_PREFIX_INSTRUCTIONS = (
    (0x00028460, "83 ec 08", "sub esp, 8"),
    (0x00028463, "8b 44 24 0c", "mov eax, [esp+0x0c]"),
    (0x00028467, "53", "push ebx"),
    (0x00028468, "56", "push esi"),
    (0x00028469, "8b f0", "mov esi, eax"),
    (0x0002846B, "c1 ee 10", "shr esi, 0x10"),
    (0x0002846E, "83 fe 20", "cmp esi, 0x20"),
    (0x00028471, "57", "push edi"),
    (0x00028472, "c7 44 24 0c ff ff ff ff", "mov [esp+0x0c], -1"),
    (0x0002847A, "0f 8c 08 01 00 00", "jl 0x28588"),
    (0x00028480, "83 fe 4b", "cmp esi, 0x4b"),
    (0x00028483, "0f 8d ff 00 00 00", "jge 0x28588"),
    (0x00028489, "33 ff", "xor edi, edi"),
    (0x0002848B, "25 ff ff 00 00", "and eax, 0xffff"),
    (0x00028490, "3b f7", "cmp esi, edi"),
    (0x00028492, "7c 12", "jl 0x284a6"),
    (0x00028494, "8b 0c b5 b8 68 95 00", "mov ecx, [esi*4+0x9568b8]"),
    (0x0002849B, "3b cf", "cmp ecx, edi"),
    (0x0002849D, "74 07", "je 0x284a6"),
    (0x0002849F, "8b 1c 81", "mov ebx, [ecx+eax*4]"),
    (0x000284A2, "3b df", "cmp ebx, edi"),
    (0x000284A4, "75 0a", "jne 0x284b0"),
    (0x000284A6, "5f", "pop edi"),
    (0x000284A7, "5e", "pop esi"),
    (0x000284A8, "83 c8 ff", "or eax, -1"),
    (0x000284AB, "5b", "pop ebx"),
    (0x000284AC, "83 c4 08", "add esp, 8"),
    (0x000284AF, "c3", "ret"),
)

# R148/F13: exact-byte continuation of helper 0x28460's first successful path.
# This proves only the first two call-chain edges and the intervening -1 guard.
GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_RVA = 0x000284BC
GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_TARGET_RVA = 0x000282B0
GF_TARGET_C_HELPER_1_SUCCESS_FAILURE_BRANCH_RVA = 0x000284CB
GF_TARGET_C_HELPER_1_SUCCESS_FAILURE_TARGET_RVA = 0x00028587
GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_RVA = 0x000284D2
GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_TARGET_RVA = 0x0008BD20
GF_TARGET_C_HELPER_1_SUCCESS_PREFIX_END_RVA = 0x000284DF
GF_TARGET_C_HELPER_1_SUCCESS_PREFIX_INSTRUCTIONS = (
    (0x000284B0, "55", "push ebp"),
    (0x000284B1, "8b 6c 24 20", "mov ebp, [esp+0x20]"),
    (0x000284B5, "8d 44 24 14", "lea eax, [esp+0x14]"),
    (0x000284B9, "50", "push eax"),
    (0x000284BA, "8b c5", "mov eax, ebp"),
    (0x000284BC, "e8 ef fd ff ff", "call rel32"),
    (0x000284C1, "83 c4 04", "add esp, 4"),
    (0x000284C4, "83 f8 ff", "cmp eax, -1"),
    (0x000284C7, "89 44 24 10", "mov [esp+0x10], eax"),
    (0x000284CB, "0f 84 b6 00 00 00", "je 0x28587"),
    (0x000284D1, "53", "push ebx"),
    (0x000284D2, "e8 49 38 06 00", "call rel32"),
    (0x000284D7, "db 44 24 2c", "fild dword [esp+0x2c]"),
    (0x000284DB, "8b 4c 24 18", "mov ecx, [esp+0x18]"),
)


# R150/F13: instruction-aligned prefix of helper 0x28460's first callee 0x282B0.
# Reuse only exact-EXE bytes validated independently by DXVK-00149. This DX11
# proof stops before 0x2830A because the reviewed window truncates the next
# instruction and therefore cannot prove its complete boundary.
GF_TARGET_C_HELPER_1_FIRST_CALLEE_RVA = 0x000282B0
GF_TARGET_C_HELPER_1_FIRST_CALLEE_PREFIX_END_RVA = 0x0002830A
GF_TARGET_C_HELPER_1_FIRST_CALLEE_COUNT_TABLE = 0x00956558
GF_TARGET_C_HELPER_1_FIRST_CALLEE_CURSOR_TABLE = 0x00956500
GF_TARGET_C_HELPER_1_FIRST_CALLEE_POOL_BASE = 0x0095E028
GF_TARGET_C_HELPER_1_FIRST_CALLEE_POOL_STRIDE = 0x1F00
GF_TARGET_C_HELPER_1_FIRST_CALLEE_SLOT_STRIDE = 0x7C
GF_TARGET_C_HELPER_1_FIRST_CALLEE_RING_SIZE = 0x40
# R152/F13: fresh exact-EXE continuation capture after the proven 0x282B0
# slot-scan prefix. This is provenance only; no continuation semantics or
# render/ScreenHud ownership are inferred from raw bytes/call candidates.
GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_RVA = 0x0002830A
GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_PROBE_LEN = 96

# R154/F13: exact terminal sequence and padding anchor recovered from the fresh
# R152 continuation window. This proves bytes/control-flow only and does not
# assign semantics to the code beginning at 0x28320.
GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_END_RVA = 0x00028319
GF_TARGET_C_HELPER_1_FIRST_CALLEE_PADDING_END_RVA = 0x00028320
GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_RVA = 0x00028320
GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_INSTRUCTIONS = (
    (0x0002830A, "ff 04 85 58 65 95 00", "inc dword [eax*4+0x956558]"),
    (0x00028311, "c1 e0 06", "shl eax, 6"),
    (0x00028314, "5e", "pop esi"),
    (0x00028315, "03 c2", "add eax, edx"),
    (0x00028317, "5f", "pop edi"),
    (0x00028318, "c3", "ret"),
)
GF_TARGET_C_HELPER_1_FIRST_CALLEE_PADDING_BYTES = bytes.fromhex(
    "cc cc cc cc cc cc cc"
)
GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_ANCHOR = bytes.fromhex("83 ec 0c")

# R156/F13: independent provenance window for the code beginning at the
# R154 next-code anchor. This captures exact bytes and rel32 candidates only;
# function-entry and render semantics remain unresolved.
GF_TARGET_C_HELPER_1_NEXT_CODE_RVA = 0x00028320
GF_TARGET_C_HELPER_1_NEXT_CODE_PROBE_LEN = 96

# R158/F13: instruction-aligned prefix recovered from the R156 0x28320 window.
# Stop at 0x2837E because the 96-byte provenance window ends inside the next
# instruction. This proves branch/call alignment only, not function semantics.
GF_TARGET_C_HELPER_1_NEXT_CODE_PREFIX_END_RVA = 0x0002837E
GF_TARGET_C_HELPER_1_NEXT_CODE_COMMON_RANGE_FAIL_RVA = 0x00028433
GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_RVA = 0x00028379
GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_TARGET_RVA = 0x000282B0

# R160/F13: fresh continuation provenance beginning at the exact exclusive end
# of the R158 instruction prefix. Capture bytes/call candidates only.
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA = 0x0002837E
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_PROBE_LEN = 96

# R162/F13: exact instruction-aligned decode of the complete R160 continuation
# window. The 96-byte probe ends exactly at 0x283DE, so every byte is covered by
# complete instructions. This proves control-flow/call alignment only.
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_END_RVA = 0x000283DE
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_FAIL_RVA = 0x00028433
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_RVA = 0x00028390
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_TARGET_RVA = 0x0008BD20
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_RVA = 0x0002839D
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_TARGET_RVA = 0x00182194

# R164/F13: fresh continuation provenance beginning at the exact exclusive end
# of the R162 complete instruction window. Capture bytes/call candidates only.
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA = 0x000283DE
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_PROBE_LEN = 96

# R166/F13: complete instruction proof for the fresh R164 continuation window.
# The exact 96-byte capture ends at RET 0x2843D (exclusive end 0x2843E).
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_END_RVA = 0x0002843E
GF_TARGET_C_HELPER_1_NEXT_CODE_SHARED_EPILOGUE_RVA = 0x00028433

# R168/F13: structural function-entry boundary for the fully bounded 0x28320
# routine. This combines the aligned external CALL target, exact preceding INT3
# padding boundary, contiguous instruction windows, shared epilogue and terminal
# RET. Higher-level data/render semantics remain deliberately unresolved.
GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_ENTRY_RVA = 0x00028320
GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_END_RVA = 0x0002843E

# R170/F13: bounded provenance for the common 0x8BD20 callee reached by two
# independently aligned calls (0x284D2 and 0x28390). Capture bytes/call census
# only; function boundary and semantic effect remain unresolved.
GF_TARGET_C_HELPER_1_SECOND_CALLEE_RVA = 0x0008BD20
GF_TARGET_C_HELPER_1_SECOND_CALLEE_PROBE_LEN = 96

# R172/F13: instruction-aligned bounded body recovered from the R170 96-byte
# 0x8BD20 probe. This proves the local branch/return/padding shape only. The
# bytes before 0x8BD20 are not part of this proof, so function-entry identity,
# higher-level callee semantics, and render ownership remain unresolved.
GF_TARGET_C_HELPER_1_SECOND_CALLEE_BODY_END_RVA = 0x0008BD3C
GF_TARGET_C_HELPER_1_SECOND_CALLEE_PADDING_END_RVA = 0x0008BD40
GF_TARGET_C_HELPER_1_SECOND_CALLEE_NEXT_CODE_RVA = 0x0008BD40
GF_TARGET_C_HELPER_1_SECOND_CALLEE_BRANCH_TARGET_RVA = 0x0008BD39
GF_TARGET_C_HELPER_1_SECOND_CALLEE_INSTRUCTIONS = (
    (0x0008BD20, "8b 4c 24 04", "mov ecx, [esp+0x04]"),
    (0x0008BD24, "85 c9", "test ecx, ecx"),
    (0x0008BD26, "74 11", "je 0x8bd39"),
    (0x0008BD28, "8b 01", "mov eax, [ecx]"),
    (0x0008BD2A, "85 c0", "test eax, eax"),
    (0x0008BD2C, "7e 0b", "jle 0x8bd39"),
    (0x0008BD2E, "8b 49 04", "mov ecx, [ecx+0x04]"),
    (0x0008BD31, "8d 04 c0", "lea eax, [eax+eax*8]"),
    (0x0008BD34, "8d 44 81 dc", "lea eax, [ecx+eax*4-0x24]"),
    (0x0008BD38, "c3", "ret"),
    (0x0008BD39, "33 c0", "xor eax, eax"),
    (0x0008BD3B, "c3", "ret"),
)
GF_TARGET_C_HELPER_1_SECOND_CALLEE_PADDING_BYTES = bytes.fromhex(
    "cc cc cc cc"
)
GF_TARGET_C_HELPER_1_SECOND_CALLEE_NEXT_CODE_ANCHOR = bytes.fromhex(
    "8b 48 08"
)

# R174/F13: bounded provenance for the separate callee reached by the exact
# instruction-aligned 0x2839D CALL in the proven 0x28320 routine. Capture only
# exact .text bytes and raw rel32 candidates. Function-entry identity, higher-
# level semantics and render/HUD ownership remain unresolved.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_RVA = 0x00182194
GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_LEN = 96

# R176/F13: instruction-aligned prefix decoded from the exact R174 96-byte
# 0x182194 capture. The first 95 bytes form complete instructions through the
# JMP at 0x1821F1; byte 96 is only opcode 0x8B for the next incomplete
# instruction at 0x1821F3. Branch targets are proved from encoded rel8 values,
# but function-entry identity, higher-level semantics and ownership stay open.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_PREFIX_END_RVA = 0x001821F3
GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_END_RVA = 0x001821F4
GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_RVA = 0x001821F3
GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_OPCODE = bytes.fromhex("8b")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_ZERO_RVA = 0x001821B5
GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_ZERO_TARGET_RVA = 0x001821F3
GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_SIGN_RVA = 0x001821BB
GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_SIGN_TARGET_RVA = 0x001821DB
GF_TARGET_C_HELPER_1_THIRD_CALLEE_JUMP_1_RVA = 0x001821D9
GF_TARGET_C_HELPER_1_THIRD_CALLEE_JUMP_2_RVA = 0x001821F1
GF_TARGET_C_HELPER_1_THIRD_CALLEE_COMMON_FORWARD_TARGET_RVA = 0x00182207
GF_TARGET_C_HELPER_1_THIRD_CALLEE_PREFIX_INSTRUCTIONS = (
    (0x00182194, "55", "push ebp"),
    (0x00182195, "8b ec", "mov ebp, esp"),
    (0x00182197, "83 ec 20", "sub esp, 0x20"),
    (0x0018219A, "83 e4 f0", "and esp, 0xfffffff0"),
    (0x0018219D, "d9 c0", "fld st(0)"),
    (0x0018219F, "d9 54 24 18", "fst dword [esp+0x18]"),
    (0x001821A3, "df 7c 24 10", "fistp qword [esp+0x10]"),
    (0x001821A7, "df 6c 24 10", "fild qword [esp+0x10]"),
    (0x001821AB, "8b 54 24 18", "mov edx, [esp+0x18]"),
    (0x001821AF, "8b 44 24 10", "mov eax, [esp+0x10]"),
    (0x001821B3, "85 c0", "test eax, eax"),
    (0x001821B5, "74 3c", "je 0x1821f3"),
    (0x001821B7, "de e9", "fsubp st(1), st(0)"),
    (0x001821B9, "85 d2", "test edx, edx"),
    (0x001821BB, "79 1e", "jns 0x1821db"),
    (0x001821BD, "d9 1c 24", "fstp dword [esp]"),
    (0x001821C0, "8b 0c 24", "mov ecx, [esp]"),
    (0x001821C3, "81 f1 00 00 00 80", "xor ecx, 0x80000000"),
    (0x001821C9, "81 c1 ff ff ff 7f", "add ecx, 0x7fffffff"),
    (0x001821CF, "83 d0 00", "adc eax, 0"),
    (0x001821D2, "8b 54 24 14", "mov edx, [esp+0x14]"),
    (0x001821D6, "83 d2 00", "adc edx, 0"),
    (0x001821D9, "eb 2c", "jmp 0x182207"),
    (0x001821DB, "d9 1c 24", "fstp dword [esp]"),
    (0x001821DE, "8b 0c 24", "mov ecx, [esp]"),
    (0x001821E1, "81 c1 ff ff ff 7f", "add ecx, 0x7fffffff"),
    (0x001821E7, "83 d8 00", "sbb eax, 0"),
    (0x001821EA, "8b 54 24 14", "mov edx, [esp+0x14]"),
    (0x001821EE, "83 da 00", "sbb edx, 0"),
    (0x001821F1, "eb 14", "jmp 0x182207"),
)

# R178/F13: fresh exact-EXE continuation provenance starts at the proven
# instruction boundary 0x1821F3, overlapping the lone 0x8B opcode from R176.
# Capture bytes and raw rel32 candidates only. The 96-byte window contains the
# already-proven common forward target 0x182207, but no instruction semantics,
# terminal boundary, function identity, or render/HUD ownership are inferred.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RVA = 0x001821F3
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_LEN = 96
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_END_RVA = 0x00182253

# R180/F13: instruction-boundary proof inside the exact R178 continuation.
# Complete instructions run through 0x182250; the capture then ends with only
# bytes 83 e0 for the next incomplete instruction at 0x182251. The proof also
# closes the predecessor common target at 0x182207 as leave;ret, but does not
# promote 0x182194 function-entry identity, callee semantics, or render ownership.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PREFIX_END_RVA = 0x00182251
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_RVA = 0x00182251
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_OPCODE = bytes.fromhex("83 e0")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_TERMINAL_RVA = 0x00182207
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RET_RVA = 0x00182208
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_POST_RET_RVA = 0x00182209
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_BACK_JNE_RVA = 0x001821FD
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_BACK_JNE_TARGET_RVA = 0x001821B7
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JE_1_RVA = 0x00182219
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JE_1_TARGET_RVA = 0x001822BF
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JE_2_RVA = 0x00182223
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JE_2_TARGET_RVA = 0x0018222E
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JBE_RVA = 0x00182228
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JBE_TARGET_RVA = 0x001822BF
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JAE_RVA = 0x00182234
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JAE_TARGET_RVA = 0x00182258
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JLE_RVA = 0x0018223A
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JLE_TARGET_RVA = 0x0018224A
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_RVA = 0x00182240
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_TARGET_RVA = 0x00186906
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JMP_RVA = 0x00182248
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JMP_TARGET_RVA = 0x00182254
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INSTRUCTIONS = (
    (0x001821F3, "8b 54 24 14", "mov edx, [esp+0x14]"),
    (0x001821F7, "f7 c2 ff ff ff 7f", "test edx, 0x7fffffff"),
    (0x001821FD, "75 b8", "jne 0x1821b7"),
    (0x001821FF, "d9 5c 24 18", "fstp dword [esp+0x18]"),
    (0x00182203, "d9 5c 24 18", "fstp dword [esp+0x18]"),
    (0x00182207, "c9", "leave"),
    (0x00182208, "c3", "ret"),
    (0x00182209, "55", "push ebp"),
    (0x0018220A, "8b ec", "mov ebp, esp"),
    (0x0018220C, "51", "push ecx"),
    (0x0018220D, "53", "push ebx"),
    (0x0018220E, "8b 5d 0c", "mov ebx, [ebp+0x0c]"),
    (0x00182211, "56", "push esi"),
    (0x00182212, "8b 75 08", "mov esi, [ebp+8]"),
    (0x00182215, "83 7e 14 00", "cmp dword [esi+0x14], 0"),
    (0x00182219, "0f 84 a0 00 00 00", "je 0x1822bf"),
    (0x0018221F, "83 7e 24 00", "cmp dword [esi+0x24], 0"),
    (0x00182223, "74 09", "je 0x18222e"),
    (0x00182225, "83 fb 7f", "cmp ebx, 0x7f"),
    (0x00182228, "0f 86 91 00 00 00", "jbe 0x1822bf"),
    (0x0018222E, "81 fb 00 01 00 00", "cmp ebx, 0x100"),
    (0x00182234, "73 22", "jae 0x182258"),
    (0x00182236, "83 7e 28 01", "cmp dword [esi+0x28], 1"),
    (0x0018223A, "7e 0e", "jle 0x18224a"),
    (0x0018223C, "6a 02", "push 2"),
    (0x0018223E, "53", "push ebx"),
    (0x0018223F, "56", "push esi"),
    (0x00182240, "e8 c1 46 00 00", "call 0x186906"),
    (0x00182245, "83 c4 0c", "add esp, 0x0c"),
    (0x00182248, "eb 0a", "jmp 0x182254"),
    (0x0018224A, "8b 46 48", "mov eax, [esi+0x48]"),
    (0x0018224D, "0f b6 04 58", "movzx eax, byte [eax+ebx*2]"),
)

# R182/F13: fresh exact-EXE continuation provenance starts at the proven
# incomplete instruction boundary 0x182251, overlapping the two bytes 83 e0
# exposed by R180. Capture 128 bytes so the already-encoded forward targets
# 0x182254, 0x182258 and 0x1822BF are all inside the evidence window. This is
# raw provenance only: no instruction semantics, function identity, callee
# meaning, or render/HUD ownership are inferred.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_RVA = 0x00182251
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_LEN = 128
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_END_RVA = 0x001822D1
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_FORWARD_TARGET_RVAS = (
    0x00182254,
    0x00182258,
    0x001822BF,
)

# R184/F13: exact instruction/control-flow proof inside the R182 0x182251
# continuation. The full 128-byte probe decodes into complete instructions
# through 0x1822D0 (leave). The byte after leave is outside the R182 window, so
# this proof deliberately does not claim a terminal ret or a function boundary.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PREFIX_END_RVA = 0x001822D1
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_RVA = 0x0018229B
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_TARGET_RVA = 0x001882CC
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_LEAVE_RVA = 0x001822D0
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_BRANCHES = (
    (0x00182256, 0x001822CC),
    (0x00182268, 0x00182279),
    (0x00182277, 0x00182283),
    (0x001822A5, 0x001822CC),
    (0x001822AA, 0x001822B2),
    (0x001822B0, 0x001822CE),
    (0x001822BD, 0x001822CE),
    (0x001822C2, 0x001822CC),
    (0x001822CA, 0x001822CE),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_INSTRUCTIONS = (
    (0x00182251, "83 e0 02", "and eax, 2"),
    (0x00182254, "85 c0", "test eax, eax"),
    (0x00182256, "74 74", "je 0x1822cc"),
    (0x00182258, "8b 56 48", "mov edx, [esi+0x48]"),
    (0x0018225B, "8b c3", "mov eax, ebx"),
    (0x0018225D, "c1 f8 08", "sar eax, 8"),
    (0x00182260, "0f b6 c8", "movzx ecx, al"),
    (0x00182263, "f6 44 4a 01 80", "test byte [edx+ecx*2+1], 0x80"),
    (0x00182268, "74 0f", "je 0x182279"),
    (0x0018226A, "6a 02", "push 2"),
    (0x0018226C, "88 45 08", "mov [ebp+8], al"),
    (0x0018226F, "88 5d 09", "mov [ebp+9], bl"),
    (0x00182272, "c6 45 0a 00", "mov byte [ebp+0x0a], 0"),
    (0x00182276, "58", "pop eax"),
    (0x00182277, "eb 0a", "jmp 0x182283"),
    (0x00182279, "33 c0", "xor eax, eax"),
    (0x0018227B, "88 5d 08", "mov [ebp+8], bl"),
    (0x0018227E, "c6 45 09 00", "mov byte [ebp+9], 0"),
    (0x00182282, "40", "inc eax"),
    (0x00182283, "6a 01", "push 1"),
    (0x00182285, "ff 76 04", "push dword [esi+4]"),
    (0x00182288, "8d 4d fc", "lea ecx, [ebp-4]"),
    (0x0018228B, "6a 03", "push 3"),
    (0x0018228D, "51", "push ecx"),
    (0x0018228E, "50", "push eax"),
    (0x0018228F, "8d 45 08", "lea eax, [ebp+8]"),
    (0x00182292, "50", "push eax"),
    (0x00182293, "68 00 02 00 00", "push 0x200"),
    (0x00182298, "ff 76 14", "push dword [esi+0x14]"),
    (0x0018229B, "e8 2c 60 00 00", "call 0x1882cc"),
    (0x001822A0, "83 c4 20", "add esp, 0x20"),
    (0x001822A3, "85 c0", "test eax, eax"),
    (0x001822A5, "74 25", "je 0x1822cc"),
    (0x001822A7, "83 f8 01", "cmp eax, 1"),
    (0x001822AA, "75 06", "jne 0x1822b2"),
    (0x001822AC, "0f b6 45 fc", "movzx eax, byte [ebp-4]"),
    (0x001822B0, "eb 1c", "jmp 0x1822ce"),
    (0x001822B2, "0f b6 4d fd", "movzx ecx, byte [ebp-3]"),
    (0x001822B6, "33 c0", "xor eax, eax"),
    (0x001822B8, "8a 65 fc", "mov ah, [ebp-4]"),
    (0x001822BB, "0b c1", "or eax, ecx"),
    (0x001822BD, "eb 0f", "jmp 0x1822ce"),
    (0x001822BF, "83 fb 61", "cmp ebx, 0x61"),
    (0x001822C2, "7c 08", "jl 0x1822cc"),
    (0x001822C4, "83 fb 7a", "cmp ebx, 0x7a"),
    (0x001822C7, "8d 43 e0", "lea eax, [ebx-0x20]"),
    (0x001822CA, "7e 02", "jle 0x1822ce"),
    (0x001822CC, "8b c3", "mov eax, ebx"),
    (0x001822CE, "5e", "pop esi"),
    (0x001822CF, "5b", "pop ebx"),
    (0x001822D0, "c9", "leave"),
)

GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_INSTRUCTIONS = (
    (0x000283DE, "b9 00 00 80 3f", "mov ecx, 0x3f800000"),
    (0x000283E3, "d9 58 1c", "fstp dword [eax+0x1c]"),
    (0x000283E6, "89 48 20", "mov [eax+0x20], ecx"),
    (0x000283E9, "89 68 70", "mov [eax+0x70], ebp"),
    (0x000283EC, "89 58 74", "mov [eax+0x74], ebx"),
    (0x000283EF, "81 c7 88 6d 95 00", "add edi, 0x956d88"),
    (0x000283F5, "89 78 28", "mov [eax+0x28], edi"),
    (0x000283F8, "c7 40 2c ff ff ff ff", "mov dword [eax+0x2c], -1"),
    (0x000283FF, "89 50 78", "mov [eax+0x78], edx"),
    (0x00028402, "89 70 68", "mov [eax+0x68], esi"),
    (0x00028405, "89 70 64", "mov [eax+0x64], esi"),
    (0x00028408, "89 70 60", "mov [eax+0x60], esi"),
    (0x0002840B, "89 70 5c", "mov [eax+0x5c], esi"),
    (0x0002840E, "89 70 54", "mov [eax+0x54], esi"),
    (0x00028411, "89 70 50", "mov [eax+0x50], esi"),
    (0x00028414, "89 70 4c", "mov [eax+0x4c], esi"),
    (0x00028417, "89 70 48", "mov [eax+0x48], esi"),
    (0x0002841A, "89 70 40", "mov [eax+0x40], esi"),
    (0x0002841D, "89 70 3c", "mov [eax+0x3c], esi"),
    (0x00028420, "89 70 38", "mov [eax+0x38], esi"),
    (0x00028423, "89 70 34", "mov [eax+0x34], esi"),
    (0x00028426, "89 48 6c", "mov [eax+0x6c], ecx"),
    (0x00028429, "89 48 58", "mov [eax+0x58], ecx"),
    (0x0002842C, "89 48 44", "mov [eax+0x44], ecx"),
    (0x0002842F, "89 48 30", "mov [eax+0x30], ecx"),
    (0x00028432, "5b", "pop ebx"),
    (0x00028433, "8b 44 24 0c", "mov eax, [esp+0x0c]"),
    (0x00028437, "5f", "pop edi"),
    (0x00028438, "5e", "pop esi"),
    (0x00028439, "5d", "pop ebp"),
    (0x0002843A, "83 c4 0c", "add esp, 0x0c"),
    (0x0002843D, "c3", "ret"),
)
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_INSTRUCTIONS = (
    (0x0002837E, "83 c4 04", "add esp, 4"),
    (0x00028381, "83 f8 ff", "cmp eax, -1"),
    (0x00028384, "89 44 24 0c", "mov [esp+0x0c], eax"),
    (0x00028388, "0f 84 a5 00 00 00", "je 0x28433"),
    (0x0002838E, "53", "push ebx"),
    (0x0002838F, "55", "push ebp"),
    (0x00028390, "e8 8b 39 06 00", "call 0x8bd20"),
    (0x00028395, "8b d8", "mov ebx, eax"),
    (0x00028397, "d9 43 08", "fld dword [ebx+8]"),
    (0x0002839A, "83 c4 04", "add esp, 4"),
    (0x0002839D, "e8 f2 9d 15 00", "call 0x182194"),
    (0x000283A2, "6b ff 2c", "imul edi, edi, 0x2c"),
    (0x000283A5, "8b 54 24 20", "mov edx, [esp+0x20]"),
    (0x000283A9, "48", "dec eax"),
    (0x000283AA, "89 44 24 18", "mov [esp+0x18], eax"),
    (0x000283AE, "8b 44 24 14", "mov eax, [esp+0x14]"),
    (0x000283B2, "b9 01 00 00 00", "mov ecx, 1"),
    (0x000283B7, "89 48 04", "mov [eax+4], ecx"),
    (0x000283BA, "db 44 24 18", "fild dword [esp+0x18]"),
    (0x000283BE, "89 50 08", "mov [eax+8], edx"),
    (0x000283C1, "8b 54 24 28", "mov edx, [esp+0x28]"),
    (0x000283C5, "89 70 0c", "mov [eax+0x0c], esi"),
    (0x000283C8, "89 50 10", "mov [eax+0x10], edx"),
    (0x000283CB, "8b 54 24 24", "mov edx, [esp+0x24]"),
    (0x000283CF, "89 50 14", "mov [eax+0x14], edx"),
    (0x000283D2, "8b 15 14 b2 95 00", "mov edx, [0x95b214]"),
    (0x000283D8, "89 48 24", "mov [eax+0x24], ecx"),
    (0x000283DB, "89 70 18", "mov [eax+0x18], esi"),
)
GF_TARGET_C_HELPER_1_NEXT_CODE_PREFIX_INSTRUCTIONS = (
    (0x00028320, "83 ec 0c", "sub esp, 0x0c"),
    (0x00028323, "8b 44 24 10", "mov eax, [esp+0x10]"),
    (0x00028327, "55", "push ebp"),
    (0x00028328, "56", "push esi"),
    (0x00028329, "57", "push edi"),
    (0x0002832A, "8b f8", "mov edi, eax"),
    (0x0002832C, "c1 ef 10", "shr edi, 0x10"),
    (0x0002832F, "83 ff 20", "cmp edi, 0x20"),
    (0x00028332, "c7 44 24 0c ff ff ff ff", "mov dword [esp+0x0c], -1"),
    (0x0002833A, "0f 8c f3 00 00 00", "jl 0x28433"),
    (0x00028340, "83 ff 4b", "cmp edi, 0x4b"),
    (0x00028343, "0f 8d ea 00 00 00", "jge 0x28433"),
    (0x00028349, "33 f6", "xor esi, esi"),
    (0x0002834B, "25 ff ff 00 00", "and eax, 0xffff"),
    (0x00028350, "3b fe", "cmp edi, esi"),
    (0x00028352, "7c 12", "jl 0x28366"),
    (0x00028354, "8b 0c bd b8 68 95 00", "mov ecx, [edi*4+0x9568b8]"),
    (0x0002835B, "3b ce", "cmp ecx, esi"),
    (0x0002835D, "74 07", "je 0x28366"),
    (0x0002835F, "8b 2c 81", "mov ebp, [ecx+eax*4]"),
    (0x00028362, "3b ee", "cmp ebp, esi"),
    (0x00028364, "75 0a", "jne 0x28370"),
    (0x00028366, "5f", "pop edi"),
    (0x00028367, "5e", "pop esi"),
    (0x00028368, "83 c8 ff", "or eax, -1"),
    (0x0002836B, "5d", "pop ebp"),
    (0x0002836C, "83 c4 0c", "add esp, 0x0c"),
    (0x0002836F, "c3", "ret"),
    (0x00028370, "8d 44 24 10", "lea eax, [esp+0x10]"),
    (0x00028374, "50", "push eax"),
    (0x00028375, "8b 44 24 24", "mov eax, [esp+0x24]"),
    (0x00028379, "e8 32 ff ff ff", "call 0x282b0"),
)
GF_TARGET_C_HELPER_1_FIRST_CALLEE_PREFIX_INSTRUCTIONS = (
    (0x000282B0, "8b 0c 85 58 65 95 00", "mov ecx, [eax*4+0x956558]"),
    (0x000282B7, "57", "push edi"),
    (0x000282B8, "8b f8", "mov edi, eax"),
    (0x000282BA, "69 ff 00 1f 00 00", "imul edi, edi, 0x1f00"),
    (0x000282C0, "81 c7 28 e0 95 00", "add edi, 0x95e028"),
    (0x000282C6, "83 f9 40", "cmp ecx, 0x40"),
    (0x000282C9, "7c 05", "jl 0x282d0"),
    (0x000282CB, "83 c8 ff", "or eax, -1"),
    (0x000282CE, "5f", "pop edi"),
    (0x000282CF, "c3", "ret"),
    (0x000282D0, "56", "push esi"),
    (0x000282D1, "8b 14 85 00 65 95 00", "mov edx, [eax*4+0x956500]"),
    (0x000282D8, "8b ca", "mov ecx, edx"),
    (0x000282DA, "6b c9 7c", "imul ecx, ecx, 0x7c"),
    (0x000282DD, "8d 72 01", "lea esi, [edx+1]"),
    (0x000282E0, "03 cf", "add ecx, edi"),
    (0x000282E2, "83 fe 40", "cmp esi, 0x40"),
    (0x000282E5, "89 34 85 00 65 95 00", "mov [eax*4+0x956500], esi"),
    (0x000282EC, "75 0b", "jne 0x282f9"),
    (0x000282EE, "c7 04 85 00 65 95 00 00 00 00 00", "mov dword [eax*4+0x956500], 0"),
    (0x000282F9, "83 39 00", "cmp dword [ecx], 0"),
    (0x000282FC, "75 d3", "jne 0x282d1"),
    (0x000282FE, "8b 74 24 0c", "mov esi, [esp+0x0c]"),
    (0x00028302, "c7 01 01 00 00 00", "mov dword [ecx], 1"),
    (0x00028308, "89 0e", "mov [esi], ecx"),
)


# Mirrors src/vr/hud_semantics.hpp. These ranges come from the shipped
# hooks_uiscaling.cpp reverse engineering and are intentionally semantic,
# rather than D3D primitive-count heuristics.
SEMANTIC_RANGES = (
    (0x05B300, 0x05B700, "HeartDisp_car_heart", "WORLD_HEART", "WORLD_BILLBOARD"),
    (0x060900, 0x061100, "ctrl_icon_work", "HUD_CTRL_ICON", "SCREEN_HUD"),
    (0x081A00, 0x081B00, "C2C_Fruit", "HUD_FRUIT", "SCREEN_HUD"),
    (0x081B00, 0x081C00, "C2C_Heart", "HUD_HEART_TOTAL", "SCREEN_HUD"),
    (0x096A80, 0x096D00, "C2CSpeechBubble", "HUD_GF_SPEECH", "SCREEN_HUD"),
    (0x0B9000, 0x0B9200, "DispGearPosition", "HUD_GEAR_REV", "SCREEN_HUD"),
    (0x0B9E00, 0x0BA100, "DispRank", "HUD_RANK", "SCREEN_HUD"),
    (0x0BAD20, 0x0BB320, "RankMarker/sub_4BAD20", "WORLD_RIVAL_MARKER", "WORLD_BILLBOARD"),
    (0x0BBA00, 0x0BBC00, "DispTempHeartNum", "HUD_TEMP_HEART", "SCREEN_HUD"),
    (0x0BD2E0, 0x0BD360, "C2CTestSlipstream", "HUD_SLIPSTREAM", "SCREEN_HUD"),
    (0x0BD360, 0x0BD500, "C2CDontLoseGF", "HUD_GF_WARNING", "SCREEN_HUD"),
    (0x0BD900, 0x0BE100, "GhostGap", "HUD_GHOST", "SCREEN_HUD"),
    (0x0BE300, 0x0BEA40, "DispTimeAttack2D", "HUD_TIME_ATTACK", "SCREEN_HUD"),
    (0x0BEA40, 0x0BEB20, "NaviPub_DispTimeAttackGoal", "HUD_GOAL_TIME", "SCREEN_HUD"),
    (0x0BEB60, 0x0BEBC0, "NaviPub_Disp_Rival", "HUD_RIVAL", "SCREEN_HUD"),
    (0x0BEBC0, 0x0BEC50, "NaviPub_Disp_Heart", "HUD_HEART_TOTAL", "SCREEN_HUD"),
    (0x0BEC50, 0x0BECA0, "NaviPub_Disp_Rival", "HUD_RIVAL", "SCREEN_HUD"),
    (0x0BECA0, 0x0BED20, "NaviPub_Disp_Heart", "HUD_HEART_TOTAL", "SCREEN_HUD"),
    (0x0BED20, 0x0BEE80, "NaviPub_Disp", "HUD_NAV_GENERIC", "SCREEN_HUD"),
    (0x0FC800, 0x0FC8A0, "C2CSpeechBubbleGF_RankEmoji", "HUD_RANK_EMOJI", "SCREEN_HUD"),
    (0x0FC8A0, 0x0FC900, "C2CSpeechBubbleGF_RankText", "HUD_RANK_TEXT", "SCREEN_HUD"),
    (0x0FC900, 0x0FCC00, "C2CSpeechBubbleGF", "HUD_GF_SPEECH", "SCREEN_HUD"),
    (0x0FCD80, 0x0FD080, "C2CSpeechBubbleGF", "HUD_GF_SPEECH", "SCREEN_HUD"),
    (0x0FD560, 0x0FD680, "C2CSpeechBubbleGF", "HUD_GF_SPEECH", "SCREEN_HUD"),
    (0x0FE860, 0x0FE900, "C2CSpeechBubbleGF", "HUD_GF_SPEECH", "SCREEN_HUD"),
)


def classify_semantic(call_rva: int) -> tuple[str, str, str]:
    for begin, end, area, semantic, space_policy in SEMANTIC_RANGES:
        if begin <= call_rva < end:
            return area, semantic, space_policy
    return "", "UNKNOWN", "UNKNOWN"


HUD_WORDS = re.compile(
    rb"(rank|rival|score|position|goal|time|yes|no|retry|stage|ghost|lap|"
    rb"checkpoint|game.?over|outrun)",
    re.IGNORECASE,
)


@dataclass
class Section:
    name: str
    virtual_size: int
    virtual_address: int
    raw_size: int
    raw_pointer: int

    def contains_rva(self, rva: int) -> bool:
        return self.virtual_address <= rva < (
            self.virtual_address + max(self.virtual_size, self.raw_size)
        )

    def rva_to_offset(self, rva: int) -> int:
        return self.raw_pointer + (rva - self.virtual_address)


@dataclass
class PE:
    data: bytes
    image_base: int
    entry_rva: int
    timestamp: int
    size_of_image: int
    sections: list[Section]

    def section(self, name: str) -> Section | None:
        return next((s for s in self.sections if s.name == name), None)

    def bytes_at_rva(self, rva: int, size: int) -> bytes:
        for section in self.sections:
            if section.contains_rva(rva):
                off = section.rva_to_offset(rva)
                return self.data[off : off + size]
        return b""


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def parse_pe(data: bytes) -> PE:
    if data[:2] != b"MZ":
        raise ValueError("not an MZ executable")
    pe_off = u32(data, 0x3C)
    if data[pe_off : pe_off + 4] != b"PE\0\0":
        raise ValueError("PE signature not found")

    file_header = pe_off + 4
    section_count = u16(data, file_header + 2)
    timestamp = u32(data, file_header + 4)
    optional_size = u16(data, file_header + 16)
    optional = file_header + 20
    magic = u16(data, optional)
    if magic != 0x10B:
        raise ValueError(f"expected PE32/x86 optional header, got 0x{magic:04x}")

    entry_rva = u32(data, optional + 16)
    image_base = u32(data, optional + 28)
    size_of_image = u32(data, optional + 56)

    sections: list[Section] = []
    section_off = optional + optional_size
    for i in range(section_count):
        off = section_off + i * 40
        name = data[off : off + 8].split(b"\0", 1)[0].decode("ascii", "replace")
        sections.append(
            Section(
                name=name,
                virtual_size=u32(data, off + 8),
                virtual_address=u32(data, off + 12),
                raw_size=u32(data, off + 16),
                raw_pointer=u32(data, off + 20),
            )
        )

    return PE(
        data=data,
        image_base=image_base,
        entry_rva=entry_rva,
        timestamp=timestamp,
        size_of_image=size_of_image,
        sections=sections,
    )


def guess_function_start(text: bytes, text_rva: int, index: int) -> int | None:
    lo = max(0, index - 0x500)
    prologues = (b"\x55\x8b\xec", b"\x53\x56\x57", b"\x56\x8b\xf1")
    for pos in range(index, lo - 1, -1):
        if any(text.startswith(p, pos) for p in prologues):
            return text_rva + pos
    return None


def find_calls(pe: PE) -> list[dict]:
    text_section = pe.section(".text")
    if not text_section:
        raise ValueError(".text section not found")

    text = pe.data[
        text_section.raw_pointer :
        text_section.raw_pointer + text_section.raw_size
    ]
    found: list[dict] = []

    for i in range(0, max(0, len(text) - 5)):
        if text[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", text, i + 1)[0]
        call_rva = text_section.virtual_address + i
        next_va = pe.image_base + call_rva + 5
        target_va = (next_va + rel) & 0xFFFFFFFF
        target_rva = (target_va - pe.image_base) & 0xFFFFFFFF
        name = KNOWN_TARGETS.get(target_rva)
        if not name:
            continue
        area, semantic, space_policy = classify_semantic(call_rva)
        found.append(
            {
                "call_rva": call_rva,
                "target_rva": target_rva,
                "target": name,
                "function_start_guess_rva": guess_function_start(
                    text, text_section.virtual_address, i
                ),
                "known_call_site": KNOWN_CALL_SITES.get(call_rva, ""),
                "known_area": area,
                "semantic": semantic,
                "space_policy": space_policy,
            }
        )
    return found


def collect_raw_rel32_call_candidates(
    pe: PE, start_rva: int, size: int = 24
) -> list[dict]:
    """Decode raw E8 rel32 candidates from an exact byte window.

    This is intentionally a byte-level candidate census, not an instruction-
    boundary proof. A candidate is retained only when its rel32 target lands in
    a mapped PE section. Later review must establish true instruction alignment
    and call effect before using it for render ownership.
    """

    blob = pe.bytes_at_rva(start_rva, size)
    out: list[dict] = []
    for offset in range(0, max(0, len(blob) - 4)):
        if blob[offset] != 0xE8:
            continue
        rel = struct.unpack_from("<i", blob, offset + 1)[0]
        call_rva = start_rva + offset
        target_rva = (call_rva + 5 + rel) & 0xFFFFFFFF
        target_section = next(
            (section.name for section in pe.sections if section.contains_rva(target_rva)),
            "",
        )
        if not target_section:
            continue
        out.append(
            {
                "call_rva": call_rva,
                "delta_from_hook": offset,
                "target_rva": target_rva,
                "target_section": target_section,
                "known_target": KNOWN_TARGETS.get(target_rva, ""),
            }
        )
    return out


def collect_raw_inbound_rel32_candidates(pe: PE, target_rva: int) -> list[dict]:
    """Find raw .text E8 rel32 byte candidates that decode to target_rva.

    This scans bytes, not decoded instructions. Results are provenance leads,
    not proof that an E8 byte is an instruction-aligned CALL.
    """

    text_section = pe.section(".text")
    if not text_section:
        return []

    text = pe.data[
        text_section.raw_pointer :
        text_section.raw_pointer + text_section.raw_size
    ]
    out: list[dict] = []
    for i in range(0, max(0, len(text) - 5)):
        if text[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", text, i + 1)[0]
        call_rva = text_section.virtual_address + i
        decoded_target_rva = (call_rva + 5 + rel) & 0xFFFFFFFF
        if decoded_target_rva != target_rva:
            continue
        area, semantic, space_policy = classify_semantic(call_rva)
        out.append(
            {
                "call_rva": call_rva,
                "function_start_guess_rva": guess_function_start(
                    text, text_section.virtual_address, i
                ),
                "known_call_site": KNOWN_CALL_SITES.get(call_rva, ""),
                "known_area": area,
                "semantic": semantic,
                "space_policy": space_policy,
            }
        )
    return out


def collect_guarded_gf_target_provenance(pe: PE) -> list[dict]:
    """Fingerprint recurring guarded-GF rel32 targets from the exact EXE.

    Captures target bytes, a backward prologue guess, raw inbound E8 candidates,
    and raw outbound rel32 candidates in a bounded target window. All call data
    remains byte-level until instruction alignment/effect is separately proven.
    """

    text_section = pe.section(".text")
    text = b""
    if text_section:
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]

    out: list[dict] = []
    for target_rva, label in sorted(GF_RAW_REL32_TARGET_RVAS.items()):
        target_section = next(
            (section.name for section in pe.sections if section.contains_rva(target_rva)),
            "",
        )
        function_start_guess_rva = None
        if text_section and text_section.contains_rva(target_rva):
            function_start_guess_rva = guess_function_start(
                text,
                text_section.virtual_address,
                target_rva - text_section.virtual_address,
            )
        out.append(
            {
                "target_rva": target_rva,
                "label": label,
                "target_section": target_section,
                "bytes64": pe.bytes_at_rva(target_rva, 64).hex(" "),
                "function_start_guess_rva": function_start_guess_rva,
                "raw_inbound_rel32_candidates": collect_raw_inbound_rel32_candidates(
                    pe, target_rva
                ),
                "raw_outbound_rel32_candidates": collect_raw_rel32_call_candidates(
                    pe, target_rva, GF_RAW_REL32_TARGET_WINDOW
                ),
            }
        )
    return out


def collect_guarded_gf_target_c_helper_1_first_callee_continuation_provenance(pe: PE) -> dict:
    """Capture a fresh exact-EXE window beginning at the proven 0x2830A boundary.

    R150 proves complete instructions through 0x28309. This collector starts at
    the exclusive end boundary and captures a new bounded byte/call window for
    later instruction review. It does not decode or promote callee semantics.
    """

    prefix = collect_guarded_gf_target_c_helper_1_first_callee_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_PROBE_LEN
    )
    predecessor_exact = (
        prefix["status"] == "EXACT_FIRST_CALLEE_SLOT_SCAN_PREFIX_PROVEN"
        and prefix["prefix_end_rva"] == target_rva
        and prefix["target_section"] == ".text"
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_PROBE_LEN
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "probe_len": GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_PROBE_LEN,
        "bytes": probe.hex(" "),
        "predecessor_status": prefix["status"],
        "predecessor_end_rva": prefix["prefix_end_rva"],
        "predecessor_exact": predecessor_exact,
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_FIRST_CALLEE_CONTINUATION_PROVENANCE_CAPTURED"
            if captured
            else "FIRST_CALLEE_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "full_callee_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_next_code_function_boundary_proof(pe: PE) -> dict:
    """Prove 0x28320 as an exact structural function-entry boundary."""

    caller = collect_guarded_gf_target_c_alignment_proof(pe)
    padding = collect_guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof(pe)
    prefix = collect_guarded_gf_target_c_helper_1_next_code_prefix_proof(pe)
    continuation = collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe)
    terminal = collect_guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof(pe)

    entry_rva = GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_ENTRY_RVA
    end_rva = GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_END_RVA

    external_call_link = bool(
        caller["status"] == "EXACT_PREFIX_CALL_ALIGNMENT_PROVEN"
        and caller["second_call_alignment_proven"]
        and caller["second_call_is_layout_boundary"]
        and caller["second_call_target_matches"]
        and caller["second_call_target_section"] == ".text"
        and caller["second_decoded_call_target_rva"] == entry_rva
    )
    padding_boundary = bool(
        padding["status"] == "EXACT_FIRST_CALLEE_TERMINAL_PADDING_ANCHOR_PROVEN"
        and padding["padding_matches"]
        and padding["padding_end_rva"] == entry_rva
        and padding["next_code_rva"] == entry_rva
        and padding["next_code_anchor_matches"]
    )
    body_chain = bool(
        prefix["status"] == "EXACT_NEXT_CODE_PREFIX_CALL_ALIGNMENT_PROVEN"
        and prefix["target_rva"] == entry_rva
        and prefix["prefix_end_rva"] == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA
        and continuation["status"] == "EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN"
        and continuation["target_rva"] == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA
        and continuation["end_rva"] == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA
        and terminal["status"] == "EXACT_NEXT_CODE_CONTINUATION_2_TERMINAL_PROVEN"
        and terminal["target_rva"] == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA
        and terminal["end_rva"] == end_rva
        and terminal["shared_epilogue_rva"] == GF_TARGET_C_HELPER_1_NEXT_CODE_SHARED_EPILOGUE_RVA
        and terminal["shared_epilogue_link"]
        and terminal["terminal_ret_rva"] == end_rva - 1
        and terminal["terminal_ret_matches"]
    )
    text_boundary = bool(
        caller["second_call_target_section"] == ".text"
        and prefix["target_section"] == ".text"
        and continuation["target_section"] == ".text"
        and terminal["target_section"] == ".text"
    )
    proven = bool(external_call_link and padding_boundary and body_chain and text_boundary)
    return {
        "entry_rva": entry_rva,
        "end_rva": end_rva,
        "external_call_rva": caller["second_aligned_call_rva"],
        "external_call_target_rva": caller["second_decoded_call_target_rva"],
        "external_call_link": external_call_link,
        "padding_start_rva": padding["padding_start_rva"],
        "padding_end_rva": padding["padding_end_rva"],
        "padding_boundary": padding_boundary,
        "prefix_status": prefix["status"],
        "continuation_status": continuation["status"],
        "terminal_status": terminal["status"],
        "body_chain": body_chain,
        "target_section": prefix["target_section"],
        "text_boundary": text_boundary,
        "terminal_ret_rva": terminal["terminal_ret_rva"],
        "shared_epilogue_rva": terminal["shared_epilogue_rva"],
        "status": (
            "EXACT_28320_FUNCTION_ENTRY_BOUNDARY_PROVEN"
            if proven
            else "FUNCTION_ENTRY_BOUNDARY_PROOF_FAILED"
        ),
        "function_entry_status": (
            "EXACT_CALL_TARGET_PADDING_BOUNDARY_PROVEN"
            if proven
            else "UNRESOLVED"
        ),
        "semantic_effect": "BOUNDARY_IDENTITY_ONLY",
        "data_structure_semantics": "UNRESOLVED",
        "callee_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_second_callee_provenance(pe: PE) -> dict:
    """Capture exact provenance for the common 0x8BD20 callee.

    Two independent exact instruction proofs resolve aligned CALLs to this target:
    0x284D2 in helper 0x28460's success path and 0x28390 in the bounded 0x28320
    routine. This collector captures a fresh .text byte window and raw rel32
    census only; function boundaries and semantic ownership remain unresolved.
    """

    helper_success = collect_guarded_gf_target_c_helper_1_success_prefix_proof(pe)
    routine_cont = collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_SECOND_CALLEE_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    text_section = pe.section(".text")
    function_start_guess_rva = None
    if text_section and text_section.contains_rva(target_rva):
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]
        function_start_guess_rva = guess_function_start(
            text,
            text_section.virtual_address,
            target_rva - text_section.virtual_address,
        )

    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_SECOND_CALLEE_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_SECOND_CALLEE_PROBE_LEN
    )
    inbound_call_rvas = {item["call_rva"] for item in inbound}
    helper_call_link = (
        helper_success["status"] == "EXACT_SUCCESS_CALL_CHAIN_PREFIX_PROVEN"
        and helper_success["second_call_target_matches"]
        and helper_success["second_call_target_rva"] == target_rva
        and GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_RVA in inbound_call_rvas
    )
    routine_call_link = (
        routine_cont["status"] == "EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN"
        and routine_cont["aligned_call_1_target_matches"]
        and routine_cont["aligned_call_1_target_rva"] == target_rva
        and GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_RVA
        in inbound_call_rvas
    )
    captured = bool(
        helper_call_link
        and routine_call_link
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_SECOND_CALLEE_PROBE_LEN
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "function_start_guess_rva": function_start_guess_rva,
        "probe_len": GF_TARGET_C_HELPER_1_SECOND_CALLEE_PROBE_LEN,
        "bytes": probe.hex(" "),
        "helper_predecessor_status": helper_success["status"],
        "helper_call_rva": GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_RVA,
        "helper_call_link": helper_call_link,
        "routine_predecessor_status": routine_cont["status"],
        "routine_call_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_RVA,
        "routine_call_link": routine_call_link,
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_8BD20_DUAL_CALL_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_8BD20_DUAL_CALL_PROVENANCE_CAPTURE_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "UNRESOLVED_CALLEE_BYTES_ONLY",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_second_callee_prefix_proof(pe: PE) -> dict:
    """Prove the bounded instruction/control-flow shape at 0x8BD20.

    The R170 provenance step established two independently aligned callers and
    captured the exact 96-byte window. This step covers the complete first
    bounded routine through both RETs, the following INT3 padding, and the next
    code anchor. It intentionally does not infer a function start from bytes
    before 0x8BD20 and does not assign any render/HUD semantic ownership.
    """

    provenance = collect_guarded_gf_target_c_helper_1_second_callee_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_SECOND_CALLEE_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_SECOND_CALLEE_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    def rel8_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 2)
        if len(raw) != 2:
            return None
        rel = struct.unpack_from("<b", raw, 1)[0]
        return (rva + 2 + rel) & 0xFFFFFFFF

    null_branch_target = rel8_target(0x0008BD26)
    nonpositive_branch_target = rel8_target(0x0008BD2C)
    branch_targets_match = (
        null_branch_target == GF_TARGET_C_HELPER_1_SECOND_CALLEE_BRANCH_TARGET_RVA
        and nonpositive_branch_target
        == GF_TARGET_C_HELPER_1_SECOND_CALLEE_BRANCH_TARGET_RVA
    )
    padding = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_SECOND_CALLEE_BODY_END_RVA,
        GF_TARGET_C_HELPER_1_SECOND_CALLEE_PADDING_END_RVA
        - GF_TARGET_C_HELPER_1_SECOND_CALLEE_BODY_END_RVA,
    )
    padding_matches = padding == GF_TARGET_C_HELPER_1_SECOND_CALLEE_PADDING_BYTES
    next_anchor = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_SECOND_CALLEE_NEXT_CODE_RVA,
        len(GF_TARGET_C_HELPER_1_SECOND_CALLEE_NEXT_CODE_ANCHOR),
    )
    next_anchor_matches = (
        next_anchor == GF_TARGET_C_HELPER_1_SECOND_CALLEE_NEXT_CODE_ANCHOR
    )
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_8BD20_DUAL_CALL_PROVENANCE_CAPTURED"
        and provenance["helper_call_link"]
        and provenance["routine_call_link"]
        and provenance["target_section"] == ".text"
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    terminal_shape = (
        expected_next == GF_TARGET_C_HELPER_1_SECOND_CALLEE_BODY_END_RVA
        and rows[-3]["rva"] == 0x0008BD38
        and rows[-3]["actual_bytes"] == "c3"
        and rows[-1]["rva"] == 0x0008BD3B
        and rows[-1]["actual_bytes"] == "c3"
    )
    proven = bool(
        predecessor_exact
        and contiguous
        and all_bytes_match
        and terminal_shape
        and branch_targets_match
        and padding_matches
        and next_anchor_matches
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_SECOND_CALLEE_RVA,
        "target_section": provenance["target_section"],
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "null_branch_target_rva": null_branch_target,
        "nonpositive_branch_target_rva": nonpositive_branch_target,
        "branch_targets_match": branch_targets_match,
        "terminal_shape": terminal_shape,
        "body_end_rva": GF_TARGET_C_HELPER_1_SECOND_CALLEE_BODY_END_RVA,
        "padding_end_rva": GF_TARGET_C_HELPER_1_SECOND_CALLEE_PADDING_END_RVA,
        "padding_bytes": padding.hex(" "),
        "padding_matches": padding_matches,
        "next_code_rva": GF_TARGET_C_HELPER_1_SECOND_CALLEE_NEXT_CODE_RVA,
        "next_code_anchor": next_anchor.hex(" "),
        "next_code_anchor_matches": next_anchor_matches,
        "status": (
            "EXACT_8BD20_BOUNDED_ROUTINE_PADDING_PROVEN"
            if proven
            else "CALLEE_8BD20_BOUNDED_ROUTINE_PROOF_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_ONLY",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_provenance(pe: PE) -> dict:
    """Capture exact provenance for the separate 0x182194 callee.

    The complete 0x2837E..0x283DD instruction proof resolves the aligned
    0x2839D rel32 CALL to 0x182194. This collector requires that exact
    predecessor proof and the matching raw inbound call candidate, then captures
    a bounded .text byte window and raw rel32 census only. Function boundaries,
    callee semantics and render/HUD ownership remain unresolved.
    """

    routine_cont = collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    text_section = pe.section(".text")
    function_start_guess_rva = None
    if text_section and text_section.contains_rva(target_rva):
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]
        function_start_guess_rva = guess_function_start(
            text,
            text_section.virtual_address,
            target_rva - text_section.virtual_address,
        )

    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_LEN
    )
    inbound_call_rvas = {item["call_rva"] for item in inbound}
    routine_call_link = (
        routine_cont["status"] == "EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN"
        and routine_cont["aligned_call_2_target_matches"]
        and routine_cont["aligned_call_2_target_rva"] == target_rva
        and GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_RVA
        in inbound_call_rvas
    )
    captured = bool(
        routine_call_link
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_LEN
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "function_start_guess_rva": function_start_guess_rva,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_LEN,
        "bytes": probe.hex(" "),
        "routine_predecessor_status": routine_cont["status"],
        "routine_call_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_RVA,
        "routine_call_link": routine_call_link,
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_182194_CALL_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182194_CALL_PROVENANCE_CAPTURE_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "UNRESOLVED_CALLEE_BYTES_ONLY",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_prefix_proof(pe: PE) -> dict:
    """Prove the complete instruction prefix inside the R174 0x182194 probe.

    The exact 96-byte provenance window contains 95 bytes of complete
    instructions and then a lone 0x8B opcode at 0x1821F3. This proof pins every
    complete instruction and the encoded short-branch targets, but deliberately
    stops before decoding the incomplete next instruction or assigning semantics.
    """

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_PREFIX_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    def rel8_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 2)
        if len(raw) != 2:
            return None
        rel = struct.unpack_from("<b", raw, 1)[0]
        return (rva + 2 + rel) & 0xFFFFFFFF

    zero_target = rel8_target(GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_ZERO_RVA)
    sign_target = rel8_target(GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_SIGN_RVA)
    jump_1_target = rel8_target(GF_TARGET_C_HELPER_1_THIRD_CALLEE_JUMP_1_RVA)
    jump_2_target = rel8_target(GF_TARGET_C_HELPER_1_THIRD_CALLEE_JUMP_2_RVA)
    branch_targets_match = (
        zero_target == GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_ZERO_TARGET_RVA
        and sign_target == GF_TARGET_C_HELPER_1_THIRD_CALLEE_BRANCH_SIGN_TARGET_RVA
        and jump_1_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_COMMON_FORWARD_TARGET_RVA
        and jump_2_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_COMMON_FORWARD_TARGET_RVA
    )
    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_OPCODE),
    )
    incomplete_opcode_matches = (
        incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_OPCODE
    )
    provenance_exact = (
        provenance["status"] == "EXACT_EXE_182194_CALL_PROVENANCE_CAPTURED"
        and provenance["routine_call_link"]
        and provenance["target_section"] == ".text"
        and provenance["probe_len"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_LEN
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_PREFIX_END_RVA
    )
    probe_boundary_matches = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_RVA
        + GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_LEN
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_END_RVA
        and GF_TARGET_C_HELPER_1_THIRD_CALLEE_PREFIX_END_RVA
        + len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_OPCODE)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_END_RVA
    )
    proven = bool(
        provenance_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and probe_boundary_matches
        and incomplete_opcode_matches
        and branch_targets_match
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_RVA,
        "target_section": provenance["target_section"],
        "predecessor_status": provenance["status"],
        "predecessor_exact": provenance_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_PREFIX_END_RVA,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_END_RVA,
        "probe_boundary_matches": probe_boundary_matches,
        "incomplete_instruction_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_RVA,
        "incomplete_opcode": incomplete.hex(" "),
        "incomplete_opcode_matches": incomplete_opcode_matches,
        "zero_branch_target_rva": zero_target,
        "sign_branch_target_rva": sign_target,
        "jump_1_target_rva": jump_1_target,
        "jump_2_target_rva": jump_2_target,
        "branch_targets_match": branch_targets_match,
        "status": (
            "EXACT_182194_PREFIX_CONTROL_FLOW_PROVEN"
            if proven
            else "CALLEE_182194_PREFIX_CONTROL_FLOW_PROOF_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_ONLY",
        "ownership_effect": "NONE",
        "continuation_status": "INCOMPLETE_OPCODE_AT_PROBE_END",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_provenance(pe: PE) -> dict:
    """Capture a fresh exact-EXE continuation window from 0x1821F3.

    R176 proves that 0x1821F3 is the next instruction boundary and that the
    previous 96-byte probe exposes only its leading 0x8B opcode. This collector
    overlaps that byte, requires the R176 proof, captures 96 fresh bytes, and
    records raw rel32 candidates. It intentionally performs no instruction
    decode and assigns no higher-level semantics or render/HUD ownership.
    """

    prefix = collect_guarded_gf_target_c_helper_1_third_callee_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_LEN,
    )
    predecessor_exact = (
        prefix["status"] == "EXACT_182194_PREFIX_CONTROL_FLOW_PROVEN"
        and prefix["prefix_end_rva"] == target_rva
        and prefix["incomplete_instruction_rva"] == target_rva
        and prefix["incomplete_opcode_matches"]
        and prefix["target_section"] == ".text"
    )
    overlap_opcode = pe.bytes_at_rva(
        target_rva, len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_OPCODE)
    )
    overlap_matches = (
        overlap_opcode == GF_TARGET_C_HELPER_1_THIRD_CALLEE_INCOMPLETE_OPCODE
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_END_RVA
    )
    common_target_within_probe = (
        target_rva
        <= GF_TARGET_C_HELPER_1_THIRD_CALLEE_COMMON_FORWARD_TARGET_RVA
        < target_rva + len(probe)
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_LEN
        and overlap_matches
        and probe_end_matches
        and common_target_within_probe
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": prefix["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "overlap_opcode": overlap_opcode.hex(" "),
        "overlap_matches": overlap_matches,
        "common_forward_target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_COMMON_FORWARD_TARGET_RVA,
        "common_forward_target_within_probe": common_target_within_probe,
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1821F3_CONTINUATION_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1821F3_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof(pe: PE) -> dict:
    """Prove the complete instruction prefix inside the R178 0x1821F3 window.

    This is a bounded exact-byte/manual-decode proof. It closes the two earlier
    jumps at the shared 0x182207 leave/ret terminal, validates all branch/call
    targets visible in the new window, and stops at the incomplete 83 e0 bytes
    at 0x182251. It does not assign higher-level semantics or render ownership.
    """

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    def rel8_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 2)
        if len(raw) != 2:
            return None
        rel = struct.unpack_from("<b", raw, 1)[0]
        return (rva + 2 + rel) & 0xFFFFFFFF

    def rel32cc_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 6)
        if len(raw) != 6 or raw[0] != 0x0F:
            return None
        rel = struct.unpack_from("<i", raw, 2)[0]
        return (rva + 6 + rel) & 0xFFFFFFFF

    def rel32_call_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) != 5 or raw[0] != 0xE8:
            return None
        rel = struct.unpack_from("<i", raw, 1)[0]
        return (rva + 5 + rel) & 0xFFFFFFFF

    back_jne_target = rel8_target(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_BACK_JNE_RVA
    )
    je_1_target = rel32cc_target(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JE_1_RVA
    )
    je_2_target = rel8_target(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JE_2_RVA
    )
    jbe_target = rel32cc_target(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JBE_RVA
    )
    jae_target = rel8_target(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JAE_RVA
    )
    jle_target = rel8_target(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JLE_RVA
    )
    call_target = rel32_call_target(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_RVA
    )
    jump_target = rel8_target(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JMP_RVA
    )
    branch_targets_match = (
        back_jne_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_BACK_JNE_TARGET_RVA
        and je_1_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JE_1_TARGET_RVA
        and je_2_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JE_2_TARGET_RVA
        and jbe_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JBE_TARGET_RVA
        and jae_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JAE_TARGET_RVA
        and jle_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JLE_TARGET_RVA
        and jump_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_JMP_TARGET_RVA
    )
    call_target_matches = (
        call_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_TARGET_RVA
    )
    raw_call_present = any(
        item["call_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_RVA
        and item["target_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_TARGET_RVA
        for item in provenance["raw_outbound_rel32_candidates"]
    )
    terminal_bytes = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_TERMINAL_RVA, 2
    )
    common_target_terminal_matches = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_COMMON_FORWARD_TARGET_RVA
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_TERMINAL_RVA
        and terminal_bytes == bytes.fromhex("c9 c3")
        and GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RET_RVA
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_TERMINAL_RVA + 1
        and GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_POST_RET_RVA
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RET_RVA + 1
    )
    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_OPCODE),
    )
    incomplete_opcode_matches = (
        incomplete
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_OPCODE
    )
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1821F3_CONTINUATION_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["target_section"] == ".text"
        and provenance["probe_end_matches"]
        and provenance["common_forward_target_within_probe"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PREFIX_END_RVA
    )
    probe_boundary_matches = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PREFIX_END_RVA
        + len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_OPCODE)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_END_RVA
    )
    proven = bool(
        predecessor_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and probe_boundary_matches
        and incomplete_opcode_matches
        and branch_targets_match
        and call_target_matches
        and raw_call_present
        and common_target_terminal_matches
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RVA,
        "target_section": provenance["target_section"],
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PREFIX_END_RVA,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_END_RVA,
        "probe_boundary_matches": probe_boundary_matches,
        "incomplete_instruction_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_RVA,
        "incomplete_opcode": incomplete.hex(" "),
        "incomplete_opcode_matches": incomplete_opcode_matches,
        "common_target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_COMMON_FORWARD_TARGET_RVA,
        "terminal_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_TERMINAL_RVA,
        "ret_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RET_RVA,
        "post_ret_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_POST_RET_RVA,
        "terminal_bytes": terminal_bytes.hex(" "),
        "common_target_terminal_matches": common_target_terminal_matches,
        "back_jne_target_rva": back_jne_target,
        "je_1_target_rva": je_1_target,
        "je_2_target_rva": je_2_target,
        "jbe_target_rva": jbe_target,
        "jae_target_rva": jae_target,
        "jle_target_rva": jle_target,
        "jump_target_rva": jump_target,
        "branch_targets_match": branch_targets_match,
        "call_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_CALL_RVA,
        "call_target_rva": call_target,
        "call_target_matches": call_target_matches,
        "raw_call_candidate_present": raw_call_present,
        "status": (
            "EXACT_1821F3_CONTINUATION_CONTROL_FLOW_PROVEN"
            if proven
            else "CALLEE_1821F3_CONTINUATION_CONTROL_FLOW_PROOF_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "terminal_status": "EXACT_COMMON_TARGET_LEAVE_RET_PROVEN",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_AND_TERMINAL_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_status": "INCOMPLETE_INSTRUCTION_AT_PROBE_END",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance(pe: PE) -> dict:
    """Capture fresh exact-EXE bytes from the R180 0x182251 boundary.

    R180 proves that the preceding continuation is exact through 0x182250 and
    exposes only bytes 83 e0 for the next incomplete instruction at 0x182251.
    This collector overlaps those bytes, requires the R180 proof, captures a
    128-byte window, and records raw rel32 candidates. The window is deliberately
    large enough to include the already-encoded forward targets 0x182254,
    0x182258 and 0x1822BF, but it assigns no instruction semantics or ownership.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_LEN,
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_1821F3_CONTINUATION_CONTROL_FLOW_PROVEN"
        and predecessor["prefix_end_rva"] == target_rva
        and predecessor["incomplete_instruction_rva"] == target_rva
        and predecessor["incomplete_opcode_matches"]
        and predecessor["target_section"] == ".text"
    )
    overlap_opcode = pe.bytes_at_rva(
        target_rva,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_OPCODE),
    )
    overlap_matches = (
        overlap_opcode
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_INCOMPLETE_OPCODE
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_END_RVA
    )
    forward_targets_within_probe = all(
        target_rva <= rva < target_rva + len(probe)
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_FORWARD_TARGET_RVAS
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_LEN
        and overlap_matches
        and probe_end_matches
        and forward_targets_within_probe
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "overlap_opcode": overlap_opcode.hex(" "),
        "overlap_matches": overlap_matches,
        "forward_target_rvas": list(
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_FORWARD_TARGET_RVAS
        ),
        "forward_targets_within_probe": forward_targets_within_probe,
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_182251_CONTINUATION_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182251_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof(pe: PE) -> dict:
    """Prove the exact instruction/control-flow layout of the R182 window.

    The proof decodes every byte in the 128-byte 0x182251 window, validates the
    incoming forward targets established by R180, all local rel8 branches, and
    the exact 0x18229B -> 0x1882CC rel32 call. It stops after the complete leave
    instruction at 0x1822D0 because the following byte was not captured by R182.
    No function-boundary, callee-semantic, or render/HUD ownership claim is made.
    """

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def rel8_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 2)
        if len(raw) != 2:
            return None
        rel = struct.unpack_from("<b", raw, 1)[0]
        return (rva + 2 + rel) & 0xFFFFFFFF

    def rel32_call_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) != 5 or raw[0] != 0xE8:
            return None
        rel = struct.unpack_from("<i", raw, 1)[0]
        return (rva + 5 + rel) & 0xFFFFFFFF

    branch_rows = []
    branch_targets_match = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_BRANCHES:
        decoded_target_rva = rel8_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        branch_rows.append(
            {
                "branch_rva": branch_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "target_is_instruction_boundary": decoded_target_rva in instruction_starts,
                "matches": matches,
            }
        )
        branch_targets_match = branch_targets_match and matches

    predecessor_targets_are_instruction_boundaries = all(
        rva in instruction_starts
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_FORWARD_TARGET_RVAS
    )
    branch_targets_are_instruction_boundaries = all(
        row["target_is_instruction_boundary"] for row in branch_rows
    )
    call_target = rel32_call_target(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_RVA
    )
    call_target_matches = (
        call_target
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_TARGET_RVA
    )
    raw_call_present = any(
        item["call_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_RVA
        and item["target_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_TARGET_RVA
        for item in provenance["raw_outbound_rel32_candidates"]
    )
    leave_bytes = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_LEAVE_RVA, 1
    )
    leave_matches = leave_bytes == bytes.fromhex("c9")
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_182251_CONTINUATION_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["target_section"] == ".text"
        and provenance["probe_end_matches"]
        and provenance["overlap_matches"]
        and provenance["forward_targets_within_probe"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PREFIX_END_RVA
        == provenance["probe_end_rva"]
    )
    proven = bool(
        predecessor_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and predecessor_targets_are_instruction_boundaries
        and branch_targets_match
        and branch_targets_are_instruction_boundaries
        and call_target_matches
        and raw_call_present
        and leave_matches
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_RVA,
        "target_section": provenance["target_section"],
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_PREFIX_END_RVA,
        "probe_end_rva": provenance["probe_end_rva"],
        "prefix_end_matches": prefix_end_matches,
        "predecessor_forward_target_rvas": list(
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_FORWARD_TARGET_RVAS
        ),
        "predecessor_targets_are_instruction_boundaries": predecessor_targets_are_instruction_boundaries,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "branch_targets_are_instruction_boundaries": branch_targets_are_instruction_boundaries,
        "call_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_CALL_RVA,
        "call_target_rva": call_target,
        "call_target_matches": call_target_matches,
        "raw_call_candidate_present": raw_call_present,
        "leave_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_2_LEAVE_RVA,
        "leave_bytes": leave_bytes.hex(" "),
        "leave_matches": leave_matches,
        "status": (
            "EXACT_182251_CONTINUATION_CONTROL_FLOW_PROVEN"
            if proven
            else "CALLEE_182251_CONTINUATION_CONTROL_FLOW_PROOF_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "terminal_status": "LEAVE_PROVEN_RET_NOT_CAPTURED",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_status": "NEXT_BYTE_AFTER_LEAVE_NOT_CAPTURED",
    }


def collect_guarded_gf_target_b_alignment_proof(pe: PE) -> dict:
    """Verify the exact 0x65860 -> 0x65874 instruction-boundary anchor.

    The instruction layout is a manually reviewed exact-byte map. This does not
    infer the helper's semantic effect or promote any guarded GF hook ownership.
    """

    expected_next = GF_TARGET_B_ENTRY_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_B_PREFIX_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    call_bytes = pe.bytes_at_rva(GF_TARGET_B_ALIGNED_CALL_RVA, 5)
    decoded_target_rva = None
    if len(call_bytes) == 5 and call_bytes[0] == 0xE8:
        rel = struct.unpack_from("<i", call_bytes, 1)[0]
        decoded_target_rva = (
            GF_TARGET_B_ALIGNED_CALL_RVA + 5 + rel
        ) & 0xFFFFFFFF

    text_section = pe.section(".text")
    function_start_guess_rva = None
    if text_section and text_section.contains_rva(GF_TARGET_B_ENTRY_RVA):
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]
        function_start_guess_rva = guess_function_start(
            text,
            text_section.virtual_address,
            GF_TARGET_B_ENTRY_RVA - text_section.virtual_address,
        )

    target_section = next(
        (
            section.name
            for section in pe.sections
            if section.contains_rva(GF_TARGET_B_ALIGNED_CALL_TARGET_RVA)
        ),
        "",
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    entry_guess_matches = function_start_guess_rva == GF_TARGET_B_ENTRY_RVA
    call_target_matches = decoded_target_rva == GF_TARGET_B_ALIGNED_CALL_TARGET_RVA
    call_row = next(
        (row for row in rows if row["rva"] == GF_TARGET_B_ALIGNED_CALL_RVA),
        None,
    )
    call_is_layout_boundary = bool(
        call_row
        and call_row["bytes_match"]
        and call_bytes
        and call_bytes[0] == 0xE8
    )
    proven = bool(
        contiguous
        and all_bytes_match
        and entry_guess_matches
        and call_is_layout_boundary
        and call_target_matches
        and target_section
    )
    return {
        "entry_rva": GF_TARGET_B_ENTRY_RVA,
        "function_start_guess_rva": function_start_guess_rva,
        "entry_guess_matches": entry_guess_matches,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "aligned_call_rva": GF_TARGET_B_ALIGNED_CALL_RVA,
        "call_is_layout_boundary": call_is_layout_boundary,
        "decoded_call_target_rva": decoded_target_rva,
        "expected_call_target_rva": GF_TARGET_B_ALIGNED_CALL_TARGET_RVA,
        "call_target_matches": call_target_matches,
        "call_target_section": target_section,
        "status": (
            "EXACT_PREFIX_CALL_ALIGNMENT_PROVEN"
            if proven
            else "ALIGNMENT_PROOF_FAILED"
        ),
        "semantic_effect": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_b_helper_provenance(pe: PE) -> dict:
    """Capture exact-EXE provenance for helper 0x285A0.

    R138 already proves that 0x65874 is an aligned CALL to this helper. R140
    binds that proven caller to the mapped helper bytes, a backward prologue
    guess, and bounded raw inbound/outbound E8 candidates. The raw helper call
    candidates remain diagnostic until independently instruction-decoded.
    """

    helper_section = next(
        (
            section.name
            for section in pe.sections
            if section.contains_rva(GF_TARGET_B_HELPER_RVA)
        ),
        "",
    )

    text_section = pe.section(".text")
    function_start_guess_rva = None
    if text_section and text_section.contains_rva(GF_TARGET_B_HELPER_RVA):
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]
        function_start_guess_rva = guess_function_start(
            text,
            text_section.virtual_address,
            GF_TARGET_B_HELPER_RVA - text_section.virtual_address,
        )

    parent_call_bytes = pe.bytes_at_rva(GF_TARGET_B_ALIGNED_CALL_RVA, 5)
    parent_decoded_target_rva = None
    if len(parent_call_bytes) == 5 and parent_call_bytes[0] == 0xE8:
        rel = struct.unpack_from("<i", parent_call_bytes, 1)[0]
        parent_decoded_target_rva = (
            GF_TARGET_B_ALIGNED_CALL_RVA + 5 + rel
        ) & 0xFFFFFFFF

    inbound = collect_raw_inbound_rel32_candidates(pe, GF_TARGET_B_HELPER_RVA)
    outbound = collect_raw_rel32_call_candidates(
        pe, GF_TARGET_B_HELPER_RVA, GF_TARGET_B_HELPER_WINDOW
    )
    aligned_parent_present = any(
        call["call_rva"] == GF_TARGET_B_ALIGNED_CALL_RVA
        for call in inbound
    )
    exact_parent_link = bool(
        parent_call_bytes == bytes.fromhex("e8 27 2d fc ff")
        and parent_decoded_target_rva == GF_TARGET_B_HELPER_RVA
        and aligned_parent_present
    )
    known_outbound = [
        call for call in outbound if call["known_target"]
    ]
    captured = bool(
        helper_section
        and exact_parent_link
        and len(pe.bytes_at_rva(
            GF_TARGET_B_HELPER_RVA,
            GF_TARGET_B_HELPER_FINGERPRINT_BYTES,
        )) == GF_TARGET_B_HELPER_FINGERPRINT_BYTES
    )

    return {
        "helper_rva": GF_TARGET_B_HELPER_RVA,
        "helper_section": helper_section,
        "function_start_guess_rva": function_start_guess_rva,
        "bytes96": pe.bytes_at_rva(
            GF_TARGET_B_HELPER_RVA,
            GF_TARGET_B_HELPER_FINGERPRINT_BYTES,
        ).hex(" "),
        "parent_call_rva": GF_TARGET_B_ALIGNED_CALL_RVA,
        "parent_call_bytes": parent_call_bytes.hex(" "),
        "parent_decoded_target_rva": parent_decoded_target_rva,
        "aligned_parent_present_in_raw_inbound": aligned_parent_present,
        "exact_parent_link": exact_parent_link,
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "known_outbound_rel32_candidates": known_outbound,
        "status": (
            "EXACT_HELPER_PROVENANCE_CAPTURED"
            if captured
            else "HELPER_PROVENANCE_CAPTURE_FAILED"
        ),
        "semantic_effect": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_alignment_proof(pe: PE) -> dict:
    """Verify exact alignment for all three bounded CALLs from target C.

    The prefix is manually reviewed from the exact public EXE. This is an
    instruction-boundary/call-target proof only and cannot assign HUD ownership.
    """

    expected_next = GF_TARGET_C_ENTRY_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_PREFIX_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    def decode_call_target(call_rva: int):
        call_bytes = pe.bytes_at_rva(call_rva, 5)
        decoded_target_rva = None
        if len(call_bytes) == 5 and call_bytes[0] == 0xE8:
            rel = struct.unpack_from("<i", call_bytes, 1)[0]
            decoded_target_rva = (call_rva + 5 + rel) & 0xFFFFFFFF
        return call_bytes, decoded_target_rva

    call_bytes, decoded_target_rva = decode_call_target(
        GF_TARGET_C_ALIGNED_CALL_RVA
    )
    second_call_bytes, second_decoded_target_rva = decode_call_target(
        GF_TARGET_C_SECOND_ALIGNED_CALL_RVA
    )
    third_call_bytes, third_decoded_target_rva = decode_call_target(
        GF_TARGET_C_THIRD_ALIGNED_CALL_RVA
    )

    text_section = pe.section(".text")
    function_start_guess_rva = None
    if text_section and text_section.contains_rva(GF_TARGET_C_ENTRY_RVA):
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]
        function_start_guess_rva = guess_function_start(
            text,
            text_section.virtual_address,
            GF_TARGET_C_ENTRY_RVA - text_section.virtual_address,
        )

    def section_name(rva: int) -> str:
        return next(
            (
                section.name
                for section in pe.sections
                if section.contains_rva(rva)
            ),
            "",
        )

    target_section = section_name(GF_TARGET_C_ALIGNED_CALL_TARGET_RVA)
    second_target_section = section_name(
        GF_TARGET_C_SECOND_ALIGNED_CALL_TARGET_RVA
    )
    third_target_section = section_name(
        GF_TARGET_C_THIRD_ALIGNED_CALL_TARGET_RVA
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    entry_guess_matches = function_start_guess_rva == GF_TARGET_C_ENTRY_RVA
    call_target_matches = decoded_target_rva == GF_TARGET_C_ALIGNED_CALL_TARGET_RVA
    second_call_target_matches = (
        second_decoded_target_rva == GF_TARGET_C_SECOND_ALIGNED_CALL_TARGET_RVA
    )
    third_call_target_matches = (
        third_decoded_target_rva == GF_TARGET_C_THIRD_ALIGNED_CALL_TARGET_RVA
    )
    call_row = next(
        (row for row in rows if row["rva"] == GF_TARGET_C_ALIGNED_CALL_RVA),
        None,
    )
    second_call_row = next(
        (
            row
            for row in rows
            if row["rva"] == GF_TARGET_C_SECOND_ALIGNED_CALL_RVA
        ),
        None,
    )
    third_call_row = next(
        (
            row
            for row in rows
            if row["rva"] == GF_TARGET_C_THIRD_ALIGNED_CALL_RVA
        ),
        None,
    )
    call_is_layout_boundary = bool(
        call_row
        and call_row["bytes_match"]
        and call_bytes
        and call_bytes[0] == 0xE8
    )
    second_call_is_layout_boundary = bool(
        second_call_row
        and second_call_row["bytes_match"]
        and second_call_bytes
        and second_call_bytes[0] == 0xE8
    )
    second_call_alignment_proven = bool(
        second_call_is_layout_boundary
        and second_call_target_matches
        and second_target_section
    )
    third_call_is_layout_boundary = bool(
        third_call_row
        and third_call_row["bytes_match"]
        and third_call_bytes
        and third_call_bytes[0] == 0xE8
    )
    third_call_alignment_proven = bool(
        third_call_is_layout_boundary
        and third_call_target_matches
        and third_target_section
    )
    proven = bool(
        contiguous
        and all_bytes_match
        and entry_guess_matches
        and call_is_layout_boundary
        and call_target_matches
        and target_section
        and second_call_alignment_proven
        and third_call_alignment_proven
    )
    return {
        "entry_rva": GF_TARGET_C_ENTRY_RVA,
        "function_start_guess_rva": function_start_guess_rva,
        "entry_guess_matches": entry_guess_matches,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "aligned_call_rva": GF_TARGET_C_ALIGNED_CALL_RVA,
        "call_is_layout_boundary": call_is_layout_boundary,
        "decoded_call_target_rva": decoded_target_rva,
        "expected_call_target_rva": GF_TARGET_C_ALIGNED_CALL_TARGET_RVA,
        "call_target_matches": call_target_matches,
        "call_target_section": target_section,
        "second_aligned_call_rva": GF_TARGET_C_SECOND_ALIGNED_CALL_RVA,
        "second_call_is_layout_boundary": second_call_is_layout_boundary,
        "second_decoded_call_target_rva": second_decoded_target_rva,
        "second_expected_call_target_rva": (
            GF_TARGET_C_SECOND_ALIGNED_CALL_TARGET_RVA
        ),
        "second_call_target_matches": second_call_target_matches,
        "second_call_target_section": second_target_section,
        "second_call_alignment_proven": second_call_alignment_proven,
        "third_aligned_call_rva": GF_TARGET_C_THIRD_ALIGNED_CALL_RVA,
        "third_call_is_layout_boundary": third_call_is_layout_boundary,
        "third_decoded_call_target_rva": third_decoded_target_rva,
        "third_expected_call_target_rva": (
            GF_TARGET_C_THIRD_ALIGNED_CALL_TARGET_RVA
        ),
        "third_call_target_matches": third_call_target_matches,
        "third_call_target_section": third_target_section,
        "third_call_alignment_proven": third_call_alignment_proven,
        "status": (
            "EXACT_PREFIX_CALL_ALIGNMENT_PROVEN"
            if proven
            else "ALIGNMENT_PROOF_FAILED"
        ),
        "semantic_effect": "UNRESOLVED",
        "ownership_effect": "NONE",
    }

def collect_guarded_gf_target_c_helper_1_provenance(pe: PE) -> dict:
    """Collect bounded raw provenance for target-C helper 0x28460.

    The byte window and rel32 candidate census are evidence only. They do not
    prove semantic effect or render ownership.
    """

    target_rva = GF_TARGET_C_HELPER_1_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    text_section = pe.section(".text")
    function_start_guess_rva = None
    if text_section and text_section.contains_rva(target_rva):
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]
        function_start_guess_rva = guess_function_start(
            text,
            text_section.virtual_address,
            target_rva - text_section.virtual_address,
        )

    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "function_start_guess_rva": function_start_guess_rva,
        "probe_len": GF_TARGET_C_HELPER_PROBE_LEN,
        "bytes": pe.bytes_at_rva(target_rva, GF_TARGET_C_HELPER_PROBE_LEN).hex(" "),
        "raw_inbound_rel32_candidates": collect_raw_inbound_rel32_candidates(
            pe, target_rva
        ),
        "raw_outbound_rel32_candidates": collect_raw_rel32_call_candidates(
            pe, target_rva, GF_TARGET_C_HELPER_PROBE_LEN
        ),
        "semantic_effect": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_prefix_proof(pe: PE) -> dict:
    """Prove the bounded packed-selector lookup prefix at helper 0x28460.

    The proof stops at the first successful continuation (0x284B0). It proves
    selector splitting, range guards, table lookup and local miss return only.
    """

    provenance = collect_guarded_gf_target_c_helper_1_provenance(pe)
    caller_proof = collect_guarded_gf_target_c_alignment_proof(pe)

    expected_next = GF_TARGET_C_HELPER_1_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_PREFIX_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    def rel8_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 2)
        if len(raw) != 2:
            return None
        rel = struct.unpack_from("<b", raw, 1)[0]
        return (rva + 2 + rel) & 0xFFFFFFFF

    def rel32cc_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 6)
        if len(raw) != 6 or raw[0] != 0x0F:
            return None
        rel = struct.unpack_from("<i", raw, 2)[0]
        return (rva + 6 + rel) & 0xFFFFFFFF

    range_low_target = rel32cc_target(0x0002847A)
    range_high_target = rel32cc_target(0x00028483)
    legacy_negative_target = rel8_target(0x00028492)
    null_table_target = rel8_target(0x0002849D)
    success_target = rel8_target(0x000284A4)

    caller_link_present = any(
        item["call_rva"] == GF_TARGET_C_ALIGNED_CALL_RVA
        for item in provenance["raw_inbound_rel32_candidates"]
    )
    caller_exact = (
        caller_proof["status"] == "EXACT_PREFIX_CALL_ALIGNMENT_PROVEN"
        and caller_proof["decoded_call_target_rva"] == GF_TARGET_C_HELPER_1_RVA
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    range_targets_match = (
        range_low_target == GF_TARGET_C_HELPER_1_RANGE_FALLBACK_RVA
        and range_high_target == GF_TARGET_C_HELPER_1_RANGE_FALLBACK_RVA
    )
    miss_targets_match = (
        legacy_negative_target == GF_TARGET_C_HELPER_1_MISS_CLEANUP_RVA
        and null_table_target == GF_TARGET_C_HELPER_1_MISS_CLEANUP_RVA
    )
    success_target_matches = (
        success_target == GF_TARGET_C_HELPER_1_SUCCESS_CONTINUATION_RVA
    )
    target_section_matches = provenance["target_section"] == ".text"

    proven = bool(
        caller_exact
        and caller_link_present
        and contiguous
        and all_bytes_match
        and range_targets_match
        and miss_targets_match
        and success_target_matches
        and target_section_matches
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_RVA,
        "target_section": provenance["target_section"],
        "function_start_guess_rva": provenance["function_start_guess_rva"],
        "caller_rva": GF_TARGET_C_ALIGNED_CALL_RVA,
        "caller_status": caller_proof["status"],
        "caller_link_present": caller_link_present,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "selector_high_word_range_min_inclusive": 0x20,
        "selector_high_word_range_max_exclusive": 0x4B,
        "selector_low_word_mask": 0xFFFF,
        "table_base": GF_TARGET_C_HELPER_1_TABLE_BASE,
        "range_low_target": range_low_target,
        "range_high_target": range_high_target,
        "range_targets_match": range_targets_match,
        "legacy_negative_target": legacy_negative_target,
        "null_table_target": null_table_target,
        "miss_cleanup_rva": GF_TARGET_C_HELPER_1_MISS_CLEANUP_RVA,
        "miss_targets_match": miss_targets_match,
        "miss_return_value": -1,
        "success_continuation_rva": success_target,
        "success_target_matches": success_target_matches,
        "status": (
            "EXACT_PACKED_SELECTOR_LOOKUP_PREFIX_PROVEN"
            if proven
            else "LOOKUP_PREFIX_PROOF_FAILED"
        ),
        "semantic_effect": "PARTIAL_LOOKUP_PREFIX_ONLY",
        "full_helper_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }

def collect_guarded_gf_target_c_helper_1_success_prefix_proof(pe: PE) -> dict:
    """Prove the first successful call-chain prefix after helper 0x28460 lookup.

    The proof is deliberately bounded to 0x284B0..0x284DE. It establishes two
    exact rel32 call targets plus the -1 error branch between them, while leaving
    the callees' semantics and the remainder of helper 0x28460 unresolved.
    """

    lookup_proof = collect_guarded_gf_target_c_helper_1_prefix_proof(pe)
    provenance = collect_guarded_gf_target_c_helper_1_provenance(pe)

    expected_next = GF_TARGET_C_HELPER_1_SUCCESS_CONTINUATION_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_SUCCESS_PREFIX_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    def rel32_call_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) != 5 or raw[0] != 0xE8:
            return None
        rel = struct.unpack_from("<i", raw, 1)[0]
        return (rva + 5 + rel) & 0xFFFFFFFF

    def rel32cc_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 6)
        if len(raw) != 6 or raw[0:2] != b"\x0f\x84":
            return None
        rel = struct.unpack_from("<i", raw, 2)[0]
        return (rva + 6 + rel) & 0xFFFFFFFF

    first_target = rel32_call_target(GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_RVA)
    failure_target = rel32cc_target(
        GF_TARGET_C_HELPER_1_SUCCESS_FAILURE_BRANCH_RVA
    )
    second_target = rel32_call_target(
        GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_RVA
    )

    first_target_section = next(
        (section.name for section in pe.sections if section.contains_rva(first_target))
        if first_target is not None
        else iter(()),
        "",
    )
    second_target_section = next(
        (section.name for section in pe.sections if section.contains_rva(second_target))
        if second_target is not None
        else iter(()),
        "",
    )
    raw_outbound = {
        (item["call_rva"], item["target_rva"])
        for item in provenance["raw_outbound_rel32_candidates"]
    }
    outbound_candidates_match = (
        (
            GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_RVA,
            GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_TARGET_RVA,
        )
        in raw_outbound
        and (
            GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_RVA,
            GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_TARGET_RVA,
        )
        in raw_outbound
    )
    lookup_prefix_proven = (
        lookup_proof["status"] == "EXACT_PACKED_SELECTOR_LOOKUP_PREFIX_PROVEN"
        and lookup_proof["success_continuation_rva"]
        == GF_TARGET_C_HELPER_1_SUCCESS_CONTINUATION_RVA
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    first_target_matches = (
        first_target == GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_TARGET_RVA
    )
    failure_target_matches = (
        failure_target == GF_TARGET_C_HELPER_1_SUCCESS_FAILURE_TARGET_RVA
    )
    second_target_matches = (
        second_target == GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_TARGET_RVA
    )
    target_sections_match = (
        first_target_section == ".text" and second_target_section == ".text"
    )
    prefix_end_matches = expected_next == GF_TARGET_C_HELPER_1_SUCCESS_PREFIX_END_RVA

    proven = bool(
        lookup_prefix_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and first_target_matches
        and failure_target_matches
        and second_target_matches
        and target_sections_match
        and outbound_candidates_match
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_RVA,
        "lookup_prefix_status": lookup_proof["status"],
        "success_start_rva": GF_TARGET_C_HELPER_1_SUCCESS_CONTINUATION_RVA,
        "success_prefix_end_rva": GF_TARGET_C_HELPER_1_SUCCESS_PREFIX_END_RVA,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "first_call_rva": GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_RVA,
        "first_call_target_rva": first_target,
        "first_call_target_matches": first_target_matches,
        "first_call_target_section": first_target_section,
        "failure_branch_rva": GF_TARGET_C_HELPER_1_SUCCESS_FAILURE_BRANCH_RVA,
        "failure_target_rva": failure_target,
        "failure_target_matches": failure_target_matches,
        "failure_condition": "EAX == -1 after first call",
        "second_call_rva": GF_TARGET_C_HELPER_1_SUCCESS_SECOND_CALL_RVA,
        "second_call_target_rva": second_target,
        "second_call_target_matches": second_target_matches,
        "second_call_target_section": second_target_section,
        "outbound_candidates_match": outbound_candidates_match,
        "status": (
            "EXACT_SUCCESS_CALL_CHAIN_PREFIX_PROVEN"
            if proven
            else "SUCCESS_CALL_CHAIN_PREFIX_PROOF_FAILED"
        ),
        "semantic_effect": "PARTIAL_CALL_CHAIN_ONLY",
        "callee_semantics": "UNRESOLVED",
        "full_helper_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }

def collect_guarded_gf_target_c_helper_1_first_callee_prefix_proof(pe: PE) -> dict:
    """Prove the instruction-aligned 0x282B0..0x28309 first-callee prefix.

    This proof depends only on the already-proven DX11 success-call edge
    0x284BC->0x282B0 plus exact bytes from the shipped EXE. It establishes a
    bounded slot-scan/control-flow shape and deliberately makes no HUD/render
    ownership claim.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_success_prefix_proof(pe)
    expected_next = GF_TARGET_C_HELPER_1_FIRST_CALLEE_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_FIRST_CALLEE_PREFIX_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    def rel8_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 2)
        if len(raw) != 2:
            return None
        rel = struct.unpack_from("<b", raw, 1)[0]
        return (rva + 2 + rel) & 0xFFFFFFFF

    count_ok_target = rel8_target(0x000282C9)
    cursor_nonwrap_target = rel8_target(0x000282EC)
    occupied_retry_target = rel8_target(0x000282FC)
    branch_targets_match = (
        count_ok_target == 0x000282D0
        and cursor_nonwrap_target == 0x000282F9
        and occupied_retry_target == 0x000282D1
    )
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_FIRST_CALLEE_PREFIX_END_RVA
    )
    predecessor_proven = (
        predecessor["status"] == "EXACT_SUCCESS_CALL_CHAIN_PREFIX_PROVEN"
        and predecessor["first_call_target_rva"] == GF_TARGET_C_HELPER_1_FIRST_CALLEE_RVA
        and predecessor["first_call_target_section"] == ".text"
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    proven = bool(
        predecessor_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_FIRST_CALLEE_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_FIRST_CALLEE_PREFIX_END_RVA,
        "predecessor_status": predecessor["status"],
        "caller_rva": predecessor["first_call_rva"],
        "caller_target_rva": predecessor["first_call_target_rva"],
        "caller_link_present": predecessor_proven,
        "target_section": predecessor["first_call_target_section"],
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "count_table": GF_TARGET_C_HELPER_1_FIRST_CALLEE_COUNT_TABLE,
        "cursor_table": GF_TARGET_C_HELPER_1_FIRST_CALLEE_CURSOR_TABLE,
        "pool_base": GF_TARGET_C_HELPER_1_FIRST_CALLEE_POOL_BASE,
        "pool_stride": GF_TARGET_C_HELPER_1_FIRST_CALLEE_POOL_STRIDE,
        "slot_stride": GF_TARGET_C_HELPER_1_FIRST_CALLEE_SLOT_STRIDE,
        "ring_size": GF_TARGET_C_HELPER_1_FIRST_CALLEE_RING_SIZE,
        "count_ok_target_rva": count_ok_target,
        "cursor_nonwrap_target_rva": cursor_nonwrap_target,
        "occupied_retry_target_rva": occupied_retry_target,
        "branch_targets_match": branch_targets_match,
        "failure_return_value": -1,
        "slot_mark_value": 1,
        "status": (
            "EXACT_FIRST_CALLEE_SLOT_SCAN_PREFIX_PROVEN"
            if proven
            else "FIRST_CALLEE_SLOT_SCAN_PREFIX_PROOF_FAILED"
        ),
        "semantic_effect": "PARTIAL_BOUNDED_SLOT_SCAN_ONLY",
        "full_callee_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof(pe: PE) -> dict:
    """Prove the exact terminal sequence, INT3 padding, and next-code anchor.

    The fresh R152 continuation capture starts exactly at 0x2830A. This proof
    decodes only complete terminal instructions through RET at 0x28318, verifies
    seven INT3 bytes through 0x2831F, and pins the next three bytes at 0x28320
    as an anchor. It does not claim a new function boundary or render semantic.
    """

    continuation = collect_guarded_gf_target_c_helper_1_first_callee_continuation_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    terminal_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_END_RVA
    )
    padding = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_END_RVA,
        len(GF_TARGET_C_HELPER_1_FIRST_CALLEE_PADDING_BYTES),
    )
    padding_matches = padding == GF_TARGET_C_HELPER_1_FIRST_CALLEE_PADDING_BYTES
    padding_end_rva = (
        GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_END_RVA + len(padding)
    )
    padding_end_matches = (
        padding_end_rva == GF_TARGET_C_HELPER_1_FIRST_CALLEE_PADDING_END_RVA
        and padding_end_rva == GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_RVA
    )
    next_anchor = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_RVA,
        len(GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_ANCHOR),
    )
    next_anchor_matches = (
        next_anchor == GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_ANCHOR
    )
    predecessor_exact = (
        continuation["status"]
        == "EXACT_EXE_FIRST_CALLEE_CONTINUATION_PROVENANCE_CAPTURED"
        and continuation["target_rva"]
        == GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_RVA
        and continuation["target_section"] == ".text"
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    proven = bool(
        predecessor_exact
        and contiguous
        and all_bytes_match
        and terminal_end_matches
        and padding_matches
        and padding_end_matches
        and next_anchor_matches
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_RVA,
        "predecessor_status": continuation["status"],
        "predecessor_exact": predecessor_exact,
        "target_section": continuation["target_section"],
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "terminal_ret_rva": 0x00028318,
        "terminal_end_rva": GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_END_RVA,
        "terminal_end_matches": terminal_end_matches,
        "padding_start_rva": GF_TARGET_C_HELPER_1_FIRST_CALLEE_TERMINAL_END_RVA,
        "padding_end_rva": padding_end_rva,
        "padding_bytes": padding.hex(" "),
        "padding_matches": padding_matches,
        "next_code_rva": GF_TARGET_C_HELPER_1_FIRST_CALLEE_NEXT_CODE_RVA,
        "next_code_anchor": next_anchor.hex(" "),
        "next_code_anchor_matches": next_anchor_matches,
        "status": (
            "EXACT_FIRST_CALLEE_TERMINAL_PADDING_ANCHOR_PROVEN"
            if proven
            else "FIRST_CALLEE_TERMINAL_PADDING_ANCHOR_PROOF_FAILED"
        ),
        "semantic_effect": "PARTIAL_TERMINAL_DATAFLOW_ONLY",
        "full_callee_semantics": "UNRESOLVED",
        "next_code_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_next_code_provenance(pe: PE) -> dict:
    """Capture exact provenance for code beginning at the R154 0x28320 anchor.

    The predecessor proof establishes only a terminal/padding/three-byte anchor.
    This collector independently captures a fresh bounded .text byte window and
    raw rel32 candidates without claiming a function entry or semantic effect.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_NEXT_CODE_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    text_section = pe.section(".text")
    function_start_guess_rva = None
    if text_section and text_section.contains_rva(target_rva):
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]
        function_start_guess_rva = guess_function_start(
            text,
            text_section.virtual_address,
            target_rva - text_section.virtual_address,
        )

    probe = pe.bytes_at_rva(target_rva, GF_TARGET_C_HELPER_1_NEXT_CODE_PROBE_LEN)
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_NEXT_CODE_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"]
        == "EXACT_FIRST_CALLEE_TERMINAL_PADDING_ANCHOR_PROVEN"
        and predecessor["next_code_rva"] == target_rva
        and predecessor["next_code_anchor_matches"]
        and predecessor["target_section"] == ".text"
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_NEXT_CODE_PROBE_LEN
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "function_start_guess_rva": function_start_guess_rva,
        "probe_len": GF_TARGET_C_HELPER_1_NEXT_CODE_PROBE_LEN,
        "bytes": probe.hex(" "),
        "predecessor_status": predecessor["status"],
        "predecessor_next_code_rva": predecessor["next_code_rva"],
        "predecessor_anchor_matches": predecessor["next_code_anchor_matches"],
        "predecessor_exact": predecessor_exact,
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_NEXT_CODE_PROVENANCE_CAPTURED"
            if captured
            else "NEXT_CODE_PROVENANCE_CAPTURE_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "UNRESOLVED_NEXT_CODE_BYTES_ONLY",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_next_code_prefix_proof(pe: PE) -> dict:
    """Prove the complete 0x28320..0x2837D instruction prefix and aligned call.

    R156 captured the exact 96-byte window. This proof pins every complete
    instruction before the truncated next instruction, verifies branch targets,
    and proves the 0x28379 rel32 call target. It does not claim a function entry
    or assign render/HUD ownership.
    """

    provenance = collect_guarded_gf_target_c_helper_1_next_code_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_NEXT_CODE_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_NEXT_CODE_PREFIX_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    def rel8_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 2)
        if len(raw) != 2:
            return None
        rel = struct.unpack_from("<b", raw, 1)[0]
        return (rva + 2 + rel) & 0xFFFFFFFF

    def rel32_target(rva: int, opcode_len: int) -> int | None:
        raw = pe.bytes_at_rva(rva, opcode_len + 4)
        if len(raw) != opcode_len + 4:
            return None
        rel = struct.unpack_from("<i", raw, opcode_len)[0]
        return (rva + opcode_len + 4 + rel) & 0xFFFFFFFF

    lower_range_fail = rel32_target(0x0002833A, 2)
    upper_range_fail = rel32_target(0x00028343, 2)
    negative_index_fail = rel8_target(0x00028352)
    null_table_fail = rel8_target(0x0002835D)
    nonnull_entry_continue = rel8_target(0x00028364)
    call_target = rel32_target(GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_RVA, 1)
    branch_targets_match = (
        lower_range_fail == GF_TARGET_C_HELPER_1_NEXT_CODE_COMMON_RANGE_FAIL_RVA
        and upper_range_fail == GF_TARGET_C_HELPER_1_NEXT_CODE_COMMON_RANGE_FAIL_RVA
        and negative_index_fail == 0x00028366
        and null_table_fail == 0x00028366
        and nonnull_entry_continue == 0x00028370
    )
    call_target_matches = (
        call_target == GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_TARGET_RVA
    )
    raw_call_present = any(
        item["call_rva"] == GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_RVA
        and item["target_rva"] == GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_TARGET_RVA
        for item in provenance["raw_outbound_rel32_candidates"]
    )
    prefix_end_matches = expected_next == GF_TARGET_C_HELPER_1_NEXT_CODE_PREFIX_END_RVA
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_NEXT_CODE_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["target_section"] == ".text"
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    proven = bool(
        predecessor_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and call_target_matches
        and raw_call_present
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "target_section": provenance["target_section"],
        "function_start_guess_rva": provenance["function_start_guess_rva"],
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "lower_range_fail_target_rva": lower_range_fail,
        "upper_range_fail_target_rva": upper_range_fail,
        "negative_index_fail_target_rva": negative_index_fail,
        "null_table_fail_target_rva": null_table_fail,
        "nonnull_entry_continue_target_rva": nonnull_entry_continue,
        "branch_targets_match": branch_targets_match,
        "failure_return_rva": 0x0002836F,
        "aligned_call_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_RVA,
        "aligned_call_target_rva": call_target,
        "aligned_call_target_matches": call_target_matches,
        "raw_call_candidate_present": raw_call_present,
        "status": (
            "EXACT_NEXT_CODE_PREFIX_CALL_ALIGNMENT_PROVEN"
            if proven
            else "NEXT_CODE_PREFIX_CALL_ALIGNMENT_PROOF_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "PARTIAL_CONTROL_FLOW_CALL_CHAIN_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_next_code_continuation_provenance(pe: PE) -> dict:
    """Capture a fresh exact-EXE window beginning at the proven 0x2837E boundary.

    R158 proves complete instructions only through 0x2837D. This collector starts
    exactly at the exclusive end boundary and captures a bounded .text window
    plus raw rel32 candidates for later review. It does not decode semantics.
    """

    prefix = collect_guarded_gf_target_c_helper_1_next_code_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    text_section = pe.section(".text")
    function_start_guess_rva = None
    if text_section and text_section.contains_rva(target_rva):
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]
        function_start_guess_rva = guess_function_start(
            text,
            text_section.virtual_address,
            target_rva - text_section.virtual_address,
        )

    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_PROBE_LEN
    )
    predecessor_exact = (
        prefix["status"] == "EXACT_NEXT_CODE_PREFIX_CALL_ALIGNMENT_PROVEN"
        and prefix["prefix_end_rva"] == target_rva
        and prefix["target_section"] == ".text"
        and prefix["aligned_call_target_matches"]
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_PROBE_LEN
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "function_start_guess_rva": function_start_guess_rva,
        "probe_len": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_PROBE_LEN,
        "bytes": probe.hex(" "),
        "predecessor_status": prefix["status"],
        "predecessor_end_rva": prefix["prefix_end_rva"],
        "predecessor_call_target_matches": prefix["aligned_call_target_matches"],
        "predecessor_exact": predecessor_exact,
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_NEXT_CODE_CONTINUATION_PROVENANCE_CAPTURED"
            if captured
            else "NEXT_CODE_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe: PE) -> dict:
    """Prove the complete 0x2837E..0x283DD continuation instruction window.

    The R160 96-byte capture ends exactly at 0x283DE. This proof pins every
    instruction byte, the 0x28433 failure edge, and both rel32 call targets.
    Callee semantics, function-entry identity and render ownership stay unresolved.
    """

    provenance = collect_guarded_gf_target_c_helper_1_next_code_continuation_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    def rel32_target(rva: int, opcode_len: int) -> int | None:
        raw = pe.bytes_at_rva(rva, opcode_len + 4)
        if len(raw) != opcode_len + 4:
            return None
        rel = struct.unpack_from("<i", raw, opcode_len)[0]
        return (rva + opcode_len + 4 + rel) & 0xFFFFFFFF

    fail_target = rel32_target(0x00028388, 2)
    call_1_target = rel32_target(
        GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_RVA, 1
    )
    call_2_target = rel32_target(
        GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_RVA, 1
    )
    raw_call_1_present = any(
        item["call_rva"] == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_RVA
        and item["target_rva"]
        == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_TARGET_RVA
        for item in provenance["raw_outbound_rel32_candidates"]
    )
    raw_call_2_present = any(
        item["call_rva"] == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_RVA
        and item["target_rva"]
        == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_TARGET_RVA
        for item in provenance["raw_outbound_rel32_candidates"]
    )
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_NEXT_CODE_CONTINUATION_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["target_section"] == ".text"
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    end_matches = expected_next == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_END_RVA
    fail_target_matches = (
        fail_target == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_FAIL_RVA
    )
    call_targets_match = (
        call_1_target == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_TARGET_RVA
        and call_2_target
        == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_TARGET_RVA
    )
    proven = bool(
        predecessor_exact
        and contiguous
        and all_bytes_match
        and end_matches
        and fail_target_matches
        and call_targets_match
        and raw_call_1_present
        and raw_call_2_present
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA,
        "end_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "target_section": provenance["target_section"],
        "function_start_guess_rva": provenance["function_start_guess_rva"],
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "fail_target_rva": fail_target,
        "fail_target_matches": fail_target_matches,
        "aligned_call_1_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_RVA,
        "aligned_call_1_target_rva": call_1_target,
        "aligned_call_1_target_matches": (
            call_1_target
            == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_TARGET_RVA
        ),
        "raw_call_1_candidate_present": raw_call_1_present,
        "aligned_call_2_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_RVA,
        "aligned_call_2_target_rva": call_2_target,
        "aligned_call_2_target_matches": (
            call_2_target
            == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_TARGET_RVA
        ),
        "raw_call_2_candidate_present": raw_call_2_present,
        "status": (
            "EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN"
            if proven
            else "NEXT_CODE_CONTINUATION_CALLS_PROOF_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "PARTIAL_CONTROL_FLOW_DATA_SETUP_ONLY",
        "call_1_semantics": "UNRESOLVED",
        "call_2_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_next_code_continuation_2_provenance(pe: PE) -> dict:
    """Capture a fresh exact-EXE window beginning at the proven 0x283DE boundary.

    R162 proves every instruction through 0x283DD. This collector starts exactly
    at the exclusive end boundary and captures a bounded .text window plus raw
    rel32 candidates for later review. It deliberately does not decode semantics.
    """

    prefix = collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    text_section = pe.section(".text")
    function_start_guess_rva = None
    if text_section and text_section.contains_rva(target_rva):
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]
        function_start_guess_rva = guess_function_start(
            text,
            text_section.virtual_address,
            target_rva - text_section.virtual_address,
        )

    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_PROBE_LEN
    )
    predecessor_exact = (
        prefix["status"] == "EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN"
        and prefix["end_rva"] == target_rva
        and prefix["target_section"] == ".text"
        and prefix["aligned_call_1_target_matches"]
        and prefix["aligned_call_2_target_matches"]
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_PROBE_LEN
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "function_start_guess_rva": function_start_guess_rva,
        "probe_len": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_PROBE_LEN,
        "bytes": probe.hex(" "),
        "predecessor_status": prefix["status"],
        "predecessor_end_rva": prefix["end_rva"],
        "predecessor_call_1_target_matches": prefix["aligned_call_1_target_matches"],
        "predecessor_call_2_target_matches": prefix["aligned_call_2_target_matches"],
        "predecessor_exact": predecessor_exact,
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_NEXT_CODE_CONTINUATION_2_PROVENANCE_CAPTURED"
            if captured
            else "NEXT_CODE_CONTINUATION_2_PROVENANCE_CAPTURE_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof(pe: PE) -> dict:
    """Prove the complete 0x283DE..0x2843D terminal/data-write window."""

    provenance = collect_guarded_gf_target_c_helper_1_next_code_continuation_2_provenance(pe)
    previous = collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe)
    expected_next = GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append(
            {
                "rva": rva,
                "asm": asm,
                "expected_bytes": expected.hex(" "),
                "actual_bytes": actual.hex(" "),
                "bytes_match": actual == expected,
            }
        )
        expected_next = rva + len(expected)

    predecessor_exact = (
        provenance["status"]
        == "EXACT_EXE_NEXT_CODE_CONTINUATION_2_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["target_section"] == ".text"
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_END_RVA
    )
    ret_matches = (
        pe.bytes_at_rva(GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_END_RVA - 1, 1)
        == b"\xc3"
    )
    shared_epilogue_link = (
        previous["status"] == "EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN"
        and previous["fail_target_matches"]
        and previous["fail_target_rva"]
        == GF_TARGET_C_HELPER_1_NEXT_CODE_SHARED_EPILOGUE_RVA
        and any(
            row["rva"] == GF_TARGET_C_HELPER_1_NEXT_CODE_SHARED_EPILOGUE_RVA
            and row["bytes_match"]
            for row in rows
        )
    )
    proven = bool(
        predecessor_exact
        and contiguous
        and all_bytes_match
        and end_matches
        and ret_matches
        and shared_epilogue_link
    )
    return {
        "target_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA,
        "end_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "target_section": provenance["target_section"],
        "function_start_guess_rva": provenance["function_start_guess_rva"],
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "shared_epilogue_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_SHARED_EPILOGUE_RVA,
        "shared_epilogue_link": shared_epilogue_link,
        "terminal_ret_rva": GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_END_RVA - 1,
        "terminal_ret_matches": ret_matches,
        "status": (
            "EXACT_NEXT_CODE_CONTINUATION_2_TERMINAL_PROVEN"
            if proven
            else "NEXT_CODE_CONTINUATION_2_TERMINAL_PROOF_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "semantic_effect": "PARTIAL_BOUNDED_DATA_WRITES_AND_EPILOGUE_ONLY",
        "data_structure_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_hook_provenance(pe: PE, calls: list[dict]) -> list[dict]:
    """Record exact-EXE context around guarded GF speech/heart hook RVAs.

    This deliberately does not infer draw ownership. It reports the hook bytes
    plus the closest known direct CALL before/after each hook within 0x80 bytes,
    so a later F13 task can require exact adjacency/effect evidence instead of
    relying on producer-range membership alone.
    """

    out: list[dict] = []
    for hook_rva, label in sorted(GF_HOOK_PROVENANCE_RVAS.items()):
        previous = [
            call for call in calls
            if call["call_rva"] <= hook_rva
            and hook_rva - call["call_rva"] <= 0x80
        ]
        following = [
            call for call in calls
            if call["call_rva"] >= hook_rva
            and call["call_rva"] - hook_rva <= 0x80
        ]
        prev_call = max(previous, key=lambda item: item["call_rva"], default=None)
        next_call = min(following, key=lambda item: item["call_rva"], default=None)
        out.append(
            {
                "hook_rva": hook_rva,
                "label": label,
                "bytes24": pe.bytes_at_rva(hook_rva, 24).hex(" "),
                "raw_rel32_call_candidates": collect_raw_rel32_call_candidates(
                    pe, hook_rva, 24
                ),
                "previous_known_call": (
                    {
                        "call_rva": prev_call["call_rva"],
                        "target": prev_call["target"],
                        "delta": hook_rva - prev_call["call_rva"],
                    }
                    if prev_call else None
                ),
                "next_known_call": (
                    {
                        "call_rva": next_call["call_rva"],
                        "target": next_call["target"],
                        "delta": next_call["call_rva"] - hook_rva,
                    }
                    if next_call else None
                ),
            }
        )
    return out


def extract_hud_strings(pe: PE) -> list[dict]:
    results: list[dict] = []
    for section in pe.sections:
        blob = pe.data[section.raw_pointer : section.raw_pointer + section.raw_size]
        for match in re.finditer(rb"[ -~]{4,120}", blob):
            value = match.group(0)
            if not HUD_WORDS.search(value):
                continue
            results.append(
                {
                    "rva": section.virtual_address + match.start(),
                    "section": section.name,
                    "text": value.decode("ascii", "replace"),
                }
            )
    return results[:500]


def symbol_fingerprints(pe: PE) -> list[dict]:
    out = []
    for rva, name in sorted(KNOWN_TARGETS.items()):
        out.append(
            {
                "rva": rva,
                "name": name,
                "bytes24": pe.bytes_at_rva(rva, 24).hex(" "),
            }
        )
    return out


def hexrva(value: int | None) -> str:
    return "-" if value is None else f"0x{value:08X}"


def render_markdown(report: dict) -> str:
    lines = [
        "# OR2006C2C EXE / HUD static analysis",
        "",
        "Generated automatically from the public replacement EXE used by the upstream OutRun2006Tweaks build.",
        "",
        "## EXE identity",
        "",
        f"- SHA-256: {report['sha256']}",
        f"- Size: {report['file_size']} bytes",
        f"- PE timestamp: {report['pe']['timestamp']}",
        f"- Image base: {hexrva(report['pe']['image_base'])}",
        f"- Entry RVA: {hexrva(report['pe']['entry_rva'])}",
        f"- SizeOfImage: {report['pe']['size_of_image']} bytes",
        f"- Known HUD call-site validation: {report['known_call_sites_found']}/{report['known_call_sites_expected']}",
        "",
        "## Known HUD/render anchors",
        "",
        "| RVA | Symbol | First 24 bytes |",
        "|---:|---|---|",
    ]
    for sym in report["symbols"]:
        lines.append(
            f"| {hexrva(sym['rva'])} | {sym['name']} | {sym['bytes24']} |"
        )

    lines += [
        "",
        "## Guarded GF hook provenance census",
        "",
        "Diagnostic-only exact-EXE evidence. Nearby known calls do not by themselves "
        "prove immediate next-draw ownership; guarded hooks remain spacing-only until "
        "a separate review establishes exact adjacency/effect.",
        "",
        "| Hook RVA | Label | First 24 bytes | Raw E8 rel32 candidates | Previous known call | Next known call |",
        "|---:|---|---|---|---|---|",
    ]
    for item in report["guarded_gf_hook_provenance"]:
        prev = item["previous_known_call"]
        nxt = item["next_known_call"]
        prev_text = (
            f"{hexrva(prev['call_rva'])} {prev['target']} (-0x{prev['delta']:X})"
            if prev else "-"
        )
        next_text = (
            f"{hexrva(nxt['call_rva'])} {nxt['target']} (+0x{nxt['delta']:X})"
            if nxt else "-"
        )
        raw_calls = item["raw_rel32_call_candidates"]
        raw_text = "<br>".join(
            f"{hexrva(call['call_rva'])}->{hexrva(call['target_rva'])}"
            f" [{call['known_target'] or 'unknown'}] {call['target_section']}"
            for call in raw_calls
        ) or "-"
        lines.append(
            f"| {hexrva(item['hook_rva'])} | {item['label']} | "
            f"{item['bytes24']} | {raw_text} | {prev_text} | {next_text} |"
        )

    lines += [
        "",
        "## Guarded GF rel32 target function fingerprints",
        "",
        "Diagnostic-only exact-EXE target evidence. Raw inbound/outbound E8 rows "
        "are byte-scan candidates and do not establish instruction boundaries or "
        "semantic effect.",
        "",
        "| Target RVA | Label | Section | Function-start guess | First 64 bytes | Raw inbound E8 candidates | Raw outbound E8 candidates (96B) |",
        "|---:|---|---|---:|---|---|---|",
    ]
    for item in report["guarded_gf_target_provenance"]:
        inbound = item["raw_inbound_rel32_candidates"]
        outbound = item["raw_outbound_rel32_candidates"]
        inbound_text = "<br>".join(
            f"{hexrva(call['call_rva'])} "
            f"[{call['semantic']}/{call['space_policy']}]"
            for call in inbound[:12]
        ) or "-"
        if len(inbound) > 12:
            inbound_text += f"<br>... +{len(inbound) - 12} more"
        outbound_text = "<br>".join(
            f"{hexrva(call['call_rva'])}->{hexrva(call['target_rva'])} "
            f"[{call['known_target'] or 'unknown'}] {call['target_section']}"
            for call in outbound[:12]
        ) or "-"
        if len(outbound) > 12:
            outbound_text += f"<br>... +{len(outbound) - 12} more"
        lines.append(
            f"| {hexrva(item['target_rva'])} | {item['label']} | "
            f"{item['target_section'] or '-'} | "
            f"{hexrva(item['function_start_guess_rva'])} | "
            f"{item['bytes64']} | {inbound_text} | {outbound_text} |"
        )

    proof = report["guarded_gf_target_b_alignment_proof"]
    proof_rows = "<br>".join(
        f"{hexrva(row['rva'])} {row['actual_bytes']} {row['asm']} "
        f"[{'match' if row['bytes_match'] else 'MISMATCH'}]"
        for row in proof["instructions"]
    )
    lines += [
        "",
        "## Guarded GF target B exact instruction-boundary proof",
        "",
        "Exact-byte/manual-decode proof only. This establishes the 0x65874 E8 as "
        "an instruction boundary in the reviewed prefix anchored at 0x65860; it "
        "does not establish the helper's semantic effect or ScreenHud ownership.",
        "",
        f"- Status: {proof['status']}",
        f"- Entry anchor: {hexrva(proof['entry_rva'])}",
        f"- Function-start guess: {hexrva(proof['function_start_guess_rva'])}",
        f"- Layout contiguous: {proof['layout_contiguous']}",
        f"- All instruction bytes match: {proof['all_instruction_bytes_match']}",
        f"- Aligned CALL: {hexrva(proof['aligned_call_rva'])} -> "
        f"{hexrva(proof['decoded_call_target_rva'])} "
        f"({proof['call_target_section'] or '-'})",
        f"- Semantic effect: {proof['semantic_effect']}",
        f"- Reviewed prefix: {proof_rows}",
    ]

    helper = report["guarded_gf_target_b_helper_provenance"]
    helper_outbound = "<br>".join(
        f"{hexrva(call['call_rva'])}->{hexrva(call['target_rva'])} "
        f"[{call['known_target'] or 'unknown'}] {call['target_section']}"
        for call in helper["raw_outbound_rel32_candidates"][:16]
    ) or "-"
    if len(helper["raw_outbound_rel32_candidates"]) > 16:
        helper_outbound += (
            f"<br>... +{len(helper['raw_outbound_rel32_candidates']) - 16} more"
        )
    lines += [
        "",
        "## Guarded GF target B helper provenance",
        "",
        "R140 bounded exact-EXE helper identity evidence. The parent CALL at "
        "0x65874 is already instruction-aligned by R138; helper-internal E8 rows "
        "remain raw byte-scan candidates and cannot justify ScreenHud ownership.",
        "",
        f"- Status: {helper['status']}",
        f"- Helper RVA: {hexrva(helper['helper_rva'])} "
        f"({helper['helper_section'] or '-'})",
        f"- Function-start guess: {hexrva(helper['function_start_guess_rva'])}",
        f"- Exact parent link: {helper['exact_parent_link']} "
        f"({hexrva(helper['parent_call_rva'])} -> "
        f"{hexrva(helper['parent_decoded_target_rva'])})",
        f"- Raw inbound candidates: {len(helper['raw_inbound_rel32_candidates'])}",
        f"- Raw outbound candidates ({GF_TARGET_B_HELPER_WINDOW}B): "
        f"{helper_outbound}",
        f"- Known outbound target candidates: "
        f"{len(helper['known_outbound_rel32_candidates'])}",
        f"- First {GF_TARGET_B_HELPER_FINGERPRINT_BYTES} bytes: "
        f"{helper['bytes96']}",
        f"- Semantic effect: {helper['semantic_effect']}",
        f"- Ownership effect: {helper['ownership_effect']}",
    ]

    target_c = report["guarded_gf_target_c_alignment_proof"]
    target_c_rows = "<br>".join(
        f"{hexrva(row['rva'])} {row['actual_bytes']} {row['asm']} "
        f"[{'match' if row['bytes_match'] else 'MISMATCH'}]"
        for row in target_c["instructions"]
    )
    lines += [
        "",
        "## Guarded GF target C first/second/third CALL instruction-boundary proof",
        "",
        "R144 exact-byte/manual-decode proof only. This extends the reviewed "
        "0x65970 prefix through 0x659C1 and establishes aligned CALLs to "
        "0x28460, 0x28320 and 0x28800. It does not establish helper semantics "
        "or ScreenHud ownership.",
        "",
        f"- Status: {target_c['status']}",
        f"- Entry anchor: {hexrva(target_c['entry_rva'])}",
        f"- Function-start guess: {hexrva(target_c['function_start_guess_rva'])}",
        f"- Layout contiguous: {target_c['layout_contiguous']}",
        f"- All instruction bytes match: {target_c['all_instruction_bytes_match']}",
        f"- First aligned CALL: {hexrva(target_c['aligned_call_rva'])} -> "
        f"{hexrva(target_c['decoded_call_target_rva'])} "
        f"({target_c['call_target_section'] or '-'})",
        f"- Second aligned CALL: {hexrva(target_c['second_aligned_call_rva'])} -> "
        f"{hexrva(target_c['second_decoded_call_target_rva'])} "
        f"({target_c['second_call_target_section'] or '-'})",
        f"- Second CALL proof: {target_c['second_call_alignment_proven']}",
        f"- Third aligned CALL: {hexrva(target_c['third_aligned_call_rva'])} -> "
        f"{hexrva(target_c['third_decoded_call_target_rva'])} "
        f"({target_c['third_call_target_section'] or '-'})",
        f"- Third CALL proof: {target_c['third_call_alignment_proven']}",
        f"- Semantic effect: {target_c['semantic_effect']}",
        f"- Ownership effect: {target_c['ownership_effect']}",
        f"- Reviewed prefix: {target_c_rows}",
    ]

    target_c_helper_1 = report["guarded_gf_target_c_helper_1_prefix_proof"]
    helper_rows = "<br>".join(
        f"{hexrva(row['rva'])} {row['actual_bytes']} {row['asm']} "
        f"[{'match' if row['bytes_match'] else 'MISMATCH'}]"
        for row in target_c_helper_1["instructions"]
    )
    lines += [
        "",
        "## Guarded GF target C helper 0x28460 packed-selector lookup prefix",
        "",
        "R146 bounded exact-EXE control-flow proof only. The prefix proves selector "
        "split/range checks, table lookup, local -1 miss return and the first "
        "success continuation; full helper semantics and ScreenHud ownership remain "
        "unresolved.",
        "",
        f"- Status: {target_c_helper_1['status']}",
        f"- Helper RVA: {hexrva(target_c_helper_1['target_rva'])} "
        f"({target_c_helper_1['target_section'] or '-'})",
        f"- Function-start guess: {hexrva(target_c_helper_1['function_start_guess_rva'])}",
        f"- Exact caller: {hexrva(target_c_helper_1['caller_rva'])} "
        f"({target_c_helper_1['caller_status']})",
        f"- Caller present in raw inbound census: {target_c_helper_1['caller_link_present']}",
        f"- Layout contiguous: {target_c_helper_1['layout_contiguous']}",
        f"- All instruction bytes match: {target_c_helper_1['all_instruction_bytes_match']}",
        f"- Selector high-word range: "
        f"0x{target_c_helper_1['selector_high_word_range_min_inclusive']:X}-"
        f"0x{target_c_helper_1['selector_high_word_range_max_exclusive']:X}",
        f"- Selector low-word mask: 0x{target_c_helper_1['selector_low_word_mask']:X}",
        f"- Table base: 0x{target_c_helper_1['table_base']:08X}",
        f"- Range fallback: {hexrva(target_c_helper_1['range_low_target'])} / "
        f"{hexrva(target_c_helper_1['range_high_target'])}",
        f"- Miss cleanup: {hexrva(target_c_helper_1['miss_cleanup_rva'])}; "
        f"return {target_c_helper_1['miss_return_value']}",
        f"- Success continuation: {hexrva(target_c_helper_1['success_continuation_rva'])}",
        f"- Semantic effect: {target_c_helper_1['semantic_effect']}",
        f"- Full helper semantics: {target_c_helper_1['full_helper_semantics']}",
        f"- Ownership effect: {target_c_helper_1['ownership_effect']}",
        f"- Reviewed prefix: {helper_rows}",
    ]

    lines += [
        "",
        "## Direct CALL references into HUD/sprite anchors",
        "",
        "| Call RVA | Function start guess | Target | Known site | Semantic | Space |",
        "|---:|---:|---|---|---|---|",
    ]
    for call in report["calls"]:
        lines.append(
            f"| {hexrva(call['call_rva'])} | "
            f"{hexrva(call['function_start_guess_rva'])} | "
            f"{call['target']} | {call['known_call_site']} | "
            f"{call['semantic']} | {call['space_policy']} |"
        )

    lines += [
        "",
        "## HUD-related ASCII strings",
        "",
        "| RVA | Section | Text |",
        "|---:|---|---|",
    ]
    for item in report["hud_strings"]:
        text = item["text"].replace("|", "\\|")
        lines.append(
            f"| {hexrva(item['rva'])} | {item['section']} | {text} |"
        )

    lines += [
        "",
        "## Runtime correlation",
        "",
        "The VR HUD inspector writes OutRun2006Tweaks-hudtrace.csv. "
        "Match its call_rva column against this report. UIScaling-derived semantic "
        "classification labels Time Attack, Rank, REV/gear, Ghost, goal time, "
        "Heart, Rival, girlfriend speech/rank UI, and protects world-attached "
        "Rival/Heart billboards from screen-HUD treatment. Previously unknown "
        "callers remain concrete reverse-engineering targets without requiring "
        "an interactive debugger.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    data = args.exe.read_bytes()
    pe = parse_pe(data)
    calls = find_calls(pe)
    found_call_rvas = {item["call_rva"] for item in calls}
    missing_known_call_sites = [
        {"rva": rva, "label": label}
        for rva, label in KNOWN_CALL_SITES.items()
        if rva not in found_call_rvas
    ]

    report = {
        "source": str(args.exe),
        "sha256": hashlib.sha256(data).hexdigest(),
        "file_size": len(data),
        "pe": {
            "image_base": pe.image_base,
            "entry_rva": pe.entry_rva,
            "timestamp": pe.timestamp,
            "size_of_image": pe.size_of_image,
            "sections": [s.__dict__ for s in pe.sections],
        },
        "symbols": symbol_fingerprints(pe),
        "calls": calls,
        "guarded_gf_hook_provenance": collect_guarded_gf_hook_provenance(pe, calls),
        "guarded_gf_target_provenance": collect_guarded_gf_target_provenance(pe),
        "guarded_gf_target_b_alignment_proof": collect_guarded_gf_target_b_alignment_proof(pe),
        "guarded_gf_target_b_helper_provenance": collect_guarded_gf_target_b_helper_provenance(pe),
        "guarded_gf_target_c_alignment_proof": collect_guarded_gf_target_c_alignment_proof(pe),
        "guarded_gf_target_c_helper_1_provenance": collect_guarded_gf_target_c_helper_1_provenance(pe),
        "guarded_gf_target_c_helper_1_prefix_proof": collect_guarded_gf_target_c_helper_1_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_success_prefix_proof": collect_guarded_gf_target_c_helper_1_success_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_first_callee_prefix_proof": collect_guarded_gf_target_c_helper_1_first_callee_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_first_callee_continuation_provenance": collect_guarded_gf_target_c_helper_1_first_callee_continuation_provenance(pe),
        "guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof": collect_guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof(pe),
        "guarded_gf_target_c_helper_1_next_code_provenance": collect_guarded_gf_target_c_helper_1_next_code_provenance(pe),
        "guarded_gf_target_c_helper_1_next_code_prefix_proof": collect_guarded_gf_target_c_helper_1_next_code_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_next_code_continuation_provenance": collect_guarded_gf_target_c_helper_1_next_code_continuation_provenance(pe),
        "guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof": collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_next_code_continuation_2_provenance": collect_guarded_gf_target_c_helper_1_next_code_continuation_2_provenance(pe),
        "guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof": collect_guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_next_code_function_boundary_proof": collect_guarded_gf_target_c_helper_1_next_code_function_boundary_proof(pe),
        "guarded_gf_target_c_helper_1_second_callee_provenance": collect_guarded_gf_target_c_helper_1_second_callee_provenance(pe),
        "guarded_gf_target_c_helper_1_second_callee_prefix_proof": collect_guarded_gf_target_c_helper_1_second_callee_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_provenance": collect_guarded_gf_target_c_helper_1_third_callee_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof(pe),
        "known_call_sites_expected": len(KNOWN_CALL_SITES),
        "known_call_sites_found": len(KNOWN_CALL_SITES) - len(missing_known_call_sites),
        "missing_known_call_sites": missing_known_call_sites,
        "hud_strings": extract_hud_strings(pe),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "OR2006C2C_EXE_ANALYSIS.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (args.out_dir / "OR2006C2C_EXE_ANALYSIS.md").write_text(
        render_markdown(report), encoding="utf-8"
    )

    print(f"sha256={report['sha256']}")
    print(f"calls={len(report['calls'])}")
    print(
        f"known_call_sites={report['known_call_sites_found']}/"
        f"{report['known_call_sites_expected']}"
    )
    provenance = report["guarded_gf_hook_provenance"]
    print(f"guarded_gf_provenance={len(provenance)}/{len(GF_HOOK_PROVENANCE_RVAS)}")
    for item in provenance:
        prev = item["previous_known_call"]
        nxt = item["next_known_call"]
        prev_text = (
            f"0x{prev['call_rva']:08X}:{prev['target']}:delta=0x{prev['delta']:X}"
            if prev else "none"
        )
        next_text = (
            f"0x{nxt['call_rva']:08X}:{nxt['target']}:delta=0x{nxt['delta']:X}"
            if nxt else "none"
        )
        print(
            f"gf_hook_provenance=0x{item['hook_rva']:08X} "
            f"prev={prev_text} next={next_text}"
        )
        raw_calls = item["raw_rel32_call_candidates"]
        raw_text = ",".join(
            f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
            f"{call['known_target'] or 'unknown'}:{call['target_section']}"
            for call in raw_calls
        ) or "none"
        print(
            f"gf_hook_rel32=0x{item['hook_rva']:08X} candidates={raw_text}"
        )
    target_provenance = report["guarded_gf_target_provenance"]
    print(
        f"guarded_gf_targets={len(target_provenance)}/"
        f"{len(GF_RAW_REL32_TARGET_RVAS)}"
    )
    for item in target_provenance:
        inbound = item["raw_inbound_rel32_candidates"]
        outbound = item["raw_outbound_rel32_candidates"]
        outbound_known = ",".join(
            f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
            f"{call['known_target'] or 'unknown'}"
            for call in outbound
        ) or "none"
        print(
            f"gf_target_provenance=0x{item['target_rva']:08X} "
            f"section={item['target_section'] or 'none'} "
            f"start_guess={hexrva(item['function_start_guess_rva'])} "
            f"inbound_raw={len(inbound)} outbound_raw={len(outbound)} "
            f"outbound={outbound_known} "
            f"bytes64={item['bytes64']}"
        )
    alignment = report["guarded_gf_target_b_alignment_proof"]
    print(
        f"gf_target_alignment=0x{alignment['entry_rva']:08X} "
        f"status={alignment['status']} "
        f"start_guess={hexrva(alignment['function_start_guess_rva'])} "
        f"layout_contiguous={alignment['layout_contiguous']} "
        f"bytes_match={alignment['all_instruction_bytes_match']} "
        f"call=0x{alignment['aligned_call_rva']:08X} "
        f"target={hexrva(alignment['decoded_call_target_rva'])} "
        f"target_section={alignment['call_target_section'] or 'none'} "
        f"semantic_effect={alignment['semantic_effect']}"
    )
    helper = report["guarded_gf_target_b_helper_provenance"]
    helper_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_helper=0x{helper['helper_rva']:08X} "
        f"status={helper['status']} "
        f"section={helper['helper_section'] or 'none'} "
        f"start_guess={hexrva(helper['function_start_guess_rva'])} "
        f"parent=0x{helper['parent_call_rva']:08X}->"
        f"{hexrva(helper['parent_decoded_target_rva'])} "
        f"parent_exact={helper['exact_parent_link']} "
        f"inbound_raw={len(helper['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper['raw_outbound_rel32_candidates'])} "
        f"known_outbound={len(helper['known_outbound_rel32_candidates'])} "
        f"outbound={helper_outbound} "
        f"bytes96={helper['bytes96']} "
        f"semantic_effect={helper['semantic_effect']} "
        f"ownership_effect={helper['ownership_effect']}"
    )
    target_c = report["guarded_gf_target_c_alignment_proof"]
    print(
        f"gf_target_c_alignment=0x{target_c['entry_rva']:08X} "
        f"status={target_c['status']} "
        f"start_guess={hexrva(target_c['function_start_guess_rva'])} "
        f"layout_contiguous={target_c['layout_contiguous']} "
        f"bytes_match={target_c['all_instruction_bytes_match']} "
        f"call=0x{target_c['aligned_call_rva']:08X} "
        f"target={hexrva(target_c['decoded_call_target_rva'])} "
        f"target_section={target_c['call_target_section'] or 'none'} "
        f"second_call=0x{target_c['second_aligned_call_rva']:08X} "
        f"second_target={hexrva(target_c['second_decoded_call_target_rva'])} "
        f"second_target_section={target_c['second_call_target_section'] or 'none'} "
        f"second_call_proven={target_c['second_call_alignment_proven']} "
        f"third_call=0x{target_c['third_aligned_call_rva']:08X} "
        f"third_target={hexrva(target_c['third_decoded_call_target_rva'])} "
        f"third_target_section={target_c['third_call_target_section'] or 'none'} "
        f"third_call_proven={target_c['third_call_alignment_proven']} "
        f"semantic_effect={target_c['semantic_effect']} "
        f"ownership_effect={target_c['ownership_effect']}"
    )
    target_c_helper_1 = report["guarded_gf_target_c_helper_1_prefix_proof"]
    print(
        f"gf_target_c_helper_1_prefix=0x{target_c_helper_1['target_rva']:08X} "
        f"status={target_c_helper_1['status']} "
        f"caller=0x{target_c_helper_1['caller_rva']:08X} "
        f"caller_status={target_c_helper_1['caller_status']} "
        f"caller_link={target_c_helper_1['caller_link_present']} "
        f"layout_contiguous={target_c_helper_1['layout_contiguous']} "
        f"bytes_match={target_c_helper_1['all_instruction_bytes_match']} "
        f"high_range=0x{target_c_helper_1['selector_high_word_range_min_inclusive']:X}-"
        f"0x{target_c_helper_1['selector_high_word_range_max_exclusive']:X} "
        f"low_mask=0x{target_c_helper_1['selector_low_word_mask']:X} "
        f"table_base=0x{target_c_helper_1['table_base']:08X} "
        f"range_fallback={hexrva(target_c_helper_1['range_low_target'])}/"
        f"{hexrva(target_c_helper_1['range_high_target'])} "
        f"miss_cleanup={hexrva(target_c_helper_1['miss_cleanup_rva'])} "
        f"miss_return={target_c_helper_1['miss_return_value']} "
        f"success_continuation={hexrva(target_c_helper_1['success_continuation_rva'])} "
        f"semantic_effect={target_c_helper_1['semantic_effect']} "
        f"full_semantics={target_c_helper_1['full_helper_semantics']} "
        f"ownership_effect={target_c_helper_1['ownership_effect']}"
    )
    target_c_helper_1_success = report["guarded_gf_target_c_helper_1_success_prefix_proof"]
    print(
        f"gf_target_c_helper_1_success=0x{target_c_helper_1_success['success_start_rva']:08X} "
        f"status={target_c_helper_1_success['status']} "
        f"lookup_status={target_c_helper_1_success['lookup_prefix_status']} "
        f"layout_contiguous={target_c_helper_1_success['layout_contiguous']} "
        f"bytes_match={target_c_helper_1_success['all_instruction_bytes_match']} "
        f"first_call=0x{target_c_helper_1_success['first_call_rva']:08X}->"
        f"{hexrva(target_c_helper_1_success['first_call_target_rva'])}:"
        f"{target_c_helper_1_success['first_call_target_section'] or 'none'} "
        f"failure_branch=0x{target_c_helper_1_success['failure_branch_rva']:08X}->"
        f"{hexrva(target_c_helper_1_success['failure_target_rva'])} "
        f"failure_condition={target_c_helper_1_success['failure_condition']} "
        f"second_call=0x{target_c_helper_1_success['second_call_rva']:08X}->"
        f"{hexrva(target_c_helper_1_success['second_call_target_rva'])}:"
        f"{target_c_helper_1_success['second_call_target_section'] or 'none'} "
        f"outbound_candidates={target_c_helper_1_success['outbound_candidates_match']} "
        f"semantic_effect={target_c_helper_1_success['semantic_effect']} "
        f"callee_semantics={target_c_helper_1_success['callee_semantics']} "
        f"ownership_effect={target_c_helper_1_success['ownership_effect']}"
    )
    first_callee_prefix = report["guarded_gf_target_c_helper_1_first_callee_prefix_proof"]
    print(
        f"gf_target_c_helper_1_first_callee_prefix=0x{first_callee_prefix['target_rva']:08X} "
        f"status={first_callee_prefix['status']} "
        f"predecessor_status={first_callee_prefix['predecessor_status']} "
        f"caller=0x{first_callee_prefix['caller_rva']:08X}->"
        f"{hexrva(first_callee_prefix['caller_target_rva'])} "
        f"caller_link={first_callee_prefix['caller_link_present']} "
        f"section={first_callee_prefix['target_section'] or 'none'} "
        f"end={hexrva(first_callee_prefix['prefix_end_rva'])} "
        f"layout_contiguous={first_callee_prefix['layout_contiguous']} "
        f"bytes_match={first_callee_prefix['all_instruction_bytes_match']} "
        f"count_table=0x{first_callee_prefix['count_table']:08X} "
        f"cursor_table=0x{first_callee_prefix['cursor_table']:08X} "
        f"pool_base=0x{first_callee_prefix['pool_base']:08X} "
        f"pool_stride=0x{first_callee_prefix['pool_stride']:X} "
        f"slot_stride=0x{first_callee_prefix['slot_stride']:X} "
        f"ring_size=0x{first_callee_prefix['ring_size']:X} "
        f"count_ok={hexrva(first_callee_prefix['count_ok_target_rva'])} "
        f"cursor_nonwrap={hexrva(first_callee_prefix['cursor_nonwrap_target_rva'])} "
        f"occupied_retry={hexrva(first_callee_prefix['occupied_retry_target_rva'])} "
        f"branch_targets={first_callee_prefix['branch_targets_match']} "
        f"failure_return={first_callee_prefix['failure_return_value']} "
        f"slot_mark={first_callee_prefix['slot_mark_value']} "
        f"semantic_effect={first_callee_prefix['semantic_effect']} "
        f"full_semantics={first_callee_prefix['full_callee_semantics']} "
        f"ownership_effect={first_callee_prefix['ownership_effect']}"
    )
    first_callee_cont = report["guarded_gf_target_c_helper_1_first_callee_continuation_provenance"]
    first_callee_cont_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in first_callee_cont["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_first_callee_continuation=0x{first_callee_cont['target_rva']:08X} "
        f"status={first_callee_cont['status']} "
        f"predecessor_status={first_callee_cont['predecessor_status']} "
        f"predecessor_end={hexrva(first_callee_cont['predecessor_end_rva'])} "
        f"predecessor_exact={first_callee_cont['predecessor_exact']} "
        f"section={first_callee_cont['target_section'] or 'none'} "
        f"probe_len={first_callee_cont['probe_len']} "
        f"inbound_raw={len(first_callee_cont['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(first_callee_cont['raw_outbound_rel32_candidates'])} "
        f"outbound={first_callee_cont_outbound} "
        f"semantic_effect={first_callee_cont['semantic_effect']} "
        f"full_semantics={first_callee_cont['full_callee_semantics']} "
        f"ownership_effect={first_callee_cont['ownership_effect']} "
        f"bytes={first_callee_cont['bytes']}"
    )
    first_callee_terminal = report["guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof"]
    print(
        f"gf_target_c_helper_1_first_callee_terminal=0x{first_callee_terminal['target_rva']:08X} "
        f"status={first_callee_terminal['status']} "
        f"predecessor_status={first_callee_terminal['predecessor_status']} "
        f"predecessor_exact={first_callee_terminal['predecessor_exact']} "
        f"section={first_callee_terminal['target_section'] or 'none'} "
        f"layout_contiguous={first_callee_terminal['layout_contiguous']} "
        f"bytes_match={first_callee_terminal['all_instruction_bytes_match']} "
        f"ret=0x{first_callee_terminal['terminal_ret_rva']:08X} "
        f"terminal_end={hexrva(first_callee_terminal['terminal_end_rva'])} "
        f"padding=0x{first_callee_terminal['padding_start_rva']:08X}-"
        f"0x{first_callee_terminal['padding_end_rva'] - 1:08X}:"
        f"{first_callee_terminal['padding_bytes']} "
        f"padding_matches={first_callee_terminal['padding_matches']} "
        f"next_code={hexrva(first_callee_terminal['next_code_rva'])} "
        f"next_anchor={first_callee_terminal['next_code_anchor']} "
        f"next_anchor_matches={first_callee_terminal['next_code_anchor_matches']} "
        f"semantic_effect={first_callee_terminal['semantic_effect']} "
        f"full_semantics={first_callee_terminal['full_callee_semantics']} "
        f"next_code_semantics={first_callee_terminal['next_code_semantics']} "
        f"ownership_effect={first_callee_terminal['ownership_effect']}"
    )
    helper_1_next_code = report["guarded_gf_target_c_helper_1_next_code_provenance"]
    helper_1_next_code_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_next_code["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_next_code=0x{helper_1_next_code['target_rva']:08X} "
        f"status={helper_1_next_code['status']} "
        f"predecessor_status={helper_1_next_code['predecessor_status']} "
        f"predecessor_next={hexrva(helper_1_next_code['predecessor_next_code_rva'])} "
        f"predecessor_anchor={helper_1_next_code['predecessor_anchor_matches']} "
        f"predecessor_exact={helper_1_next_code['predecessor_exact']} "
        f"section={helper_1_next_code['target_section'] or 'none'} "
        f"start_guess={hexrva(helper_1_next_code['function_start_guess_rva'])} "
        f"probe_len={helper_1_next_code['probe_len']} "
        f"inbound_raw={len(helper_1_next_code['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_next_code['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_next_code_outbound} "
        f"function_entry={helper_1_next_code['function_entry_status']} "
        f"semantic_effect={helper_1_next_code['semantic_effect']} "
        f"ownership_effect={helper_1_next_code['ownership_effect']} "
        f"bytes={helper_1_next_code['bytes']}"
    )
    helper_1_next_prefix = report["guarded_gf_target_c_helper_1_next_code_prefix_proof"]
    print(
        f"gf_target_c_helper_1_next_code_prefix=0x{helper_1_next_prefix['target_rva']:08X} "
        f"status={helper_1_next_prefix['status']} "
        f"predecessor_status={helper_1_next_prefix['predecessor_status']} "
        f"predecessor_exact={helper_1_next_prefix['predecessor_exact']} "
        f"section={helper_1_next_prefix['target_section'] or 'none'} "
        f"start_guess={hexrva(helper_1_next_prefix['function_start_guess_rva'])} "
        f"end={hexrva(helper_1_next_prefix['prefix_end_rva'])} "
        f"layout_contiguous={helper_1_next_prefix['layout_contiguous']} "
        f"bytes_match={helper_1_next_prefix['all_instruction_bytes_match']} "
        f"range_fail_lo={hexrva(helper_1_next_prefix['lower_range_fail_target_rva'])} "
        f"range_fail_hi={hexrva(helper_1_next_prefix['upper_range_fail_target_rva'])} "
        f"negative_fail={hexrva(helper_1_next_prefix['negative_index_fail_target_rva'])} "
        f"null_fail={hexrva(helper_1_next_prefix['null_table_fail_target_rva'])} "
        f"nonnull_continue={hexrva(helper_1_next_prefix['nonnull_entry_continue_target_rva'])} "
        f"branch_targets={helper_1_next_prefix['branch_targets_match']} "
        f"failure_ret=0x{helper_1_next_prefix['failure_return_rva']:08X} "
        f"call=0x{helper_1_next_prefix['aligned_call_rva']:08X}->"
        f"{hexrva(helper_1_next_prefix['aligned_call_target_rva'])} "
        f"call_target={helper_1_next_prefix['aligned_call_target_matches']} "
        f"raw_call={helper_1_next_prefix['raw_call_candidate_present']} "
        f"function_entry={helper_1_next_prefix['function_entry_status']} "
        f"semantic_effect={helper_1_next_prefix['semantic_effect']} "
        f"call_semantics={helper_1_next_prefix['call_semantics']} "
        f"ownership_effect={helper_1_next_prefix['ownership_effect']}"
    )
    helper_1_next_cont = report["guarded_gf_target_c_helper_1_next_code_continuation_provenance"]
    helper_1_next_cont_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_next_cont["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_next_code_continuation=0x{helper_1_next_cont['target_rva']:08X} "
        f"status={helper_1_next_cont['status']} "
        f"predecessor_status={helper_1_next_cont['predecessor_status']} "
        f"predecessor_end={hexrva(helper_1_next_cont['predecessor_end_rva'])} "
        f"predecessor_call={helper_1_next_cont['predecessor_call_target_matches']} "
        f"predecessor_exact={helper_1_next_cont['predecessor_exact']} "
        f"section={helper_1_next_cont['target_section'] or 'none'} "
        f"start_guess={hexrva(helper_1_next_cont['function_start_guess_rva'])} "
        f"probe_len={helper_1_next_cont['probe_len']} "
        f"inbound_raw={len(helper_1_next_cont['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_next_cont['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_next_cont_outbound} "
        f"function_entry={helper_1_next_cont['function_entry_status']} "
        f"semantic_effect={helper_1_next_cont['semantic_effect']} "
        f"ownership_effect={helper_1_next_cont['ownership_effect']} "
        f"bytes={helper_1_next_cont['bytes']}"
    )
    helper_1_next_cont_prefix = report["guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof"]
    print(
        f"gf_target_c_helper_1_next_code_continuation_prefix=0x{helper_1_next_cont_prefix['target_rva']:08X} "
        f"status={helper_1_next_cont_prefix['status']} "
        f"predecessor_status={helper_1_next_cont_prefix['predecessor_status']} "
        f"predecessor_exact={helper_1_next_cont_prefix['predecessor_exact']} "
        f"section={helper_1_next_cont_prefix['target_section'] or 'none'} "
        f"start_guess={hexrva(helper_1_next_cont_prefix['function_start_guess_rva'])} "
        f"end={hexrva(helper_1_next_cont_prefix['end_rva'])} "
        f"layout_contiguous={helper_1_next_cont_prefix['layout_contiguous']} "
        f"bytes_match={helper_1_next_cont_prefix['all_instruction_bytes_match']} "
        f"fail_target={hexrva(helper_1_next_cont_prefix['fail_target_rva'])} "
        f"fail_target_match={helper_1_next_cont_prefix['fail_target_matches']} "
        f"call1=0x{helper_1_next_cont_prefix['aligned_call_1_rva']:08X}->"
        f"{hexrva(helper_1_next_cont_prefix['aligned_call_1_target_rva'])} "
        f"call1_target={helper_1_next_cont_prefix['aligned_call_1_target_matches']} "
        f"raw_call1={helper_1_next_cont_prefix['raw_call_1_candidate_present']} "
        f"call2=0x{helper_1_next_cont_prefix['aligned_call_2_rva']:08X}->"
        f"{hexrva(helper_1_next_cont_prefix['aligned_call_2_target_rva'])} "
        f"call2_target={helper_1_next_cont_prefix['aligned_call_2_target_matches']} "
        f"raw_call2={helper_1_next_cont_prefix['raw_call_2_candidate_present']} "
        f"function_entry={helper_1_next_cont_prefix['function_entry_status']} "
        f"semantic_effect={helper_1_next_cont_prefix['semantic_effect']} "
        f"call1_semantics={helper_1_next_cont_prefix['call_1_semantics']} "
        f"call2_semantics={helper_1_next_cont_prefix['call_2_semantics']} "
        f"ownership_effect={helper_1_next_cont_prefix['ownership_effect']}"
    )
    helper_1_next_cont2 = report["guarded_gf_target_c_helper_1_next_code_continuation_2_provenance"]
    helper_1_next_cont2_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_next_cont2["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_next_code_continuation_2=0x{helper_1_next_cont2['target_rva']:08X} "
        f"status={helper_1_next_cont2['status']} "
        f"predecessor_status={helper_1_next_cont2['predecessor_status']} "
        f"predecessor_end={hexrva(helper_1_next_cont2['predecessor_end_rva'])} "
        f"predecessor_call1={helper_1_next_cont2['predecessor_call_1_target_matches']} "
        f"predecessor_call2={helper_1_next_cont2['predecessor_call_2_target_matches']} "
        f"predecessor_exact={helper_1_next_cont2['predecessor_exact']} "
        f"section={helper_1_next_cont2['target_section'] or 'none'} "
        f"start_guess={hexrva(helper_1_next_cont2['function_start_guess_rva'])} "
        f"probe_len={helper_1_next_cont2['probe_len']} "
        f"inbound_raw={len(helper_1_next_cont2['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_next_cont2['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_next_cont2_outbound} "
        f"function_entry={helper_1_next_cont2['function_entry_status']} "
        f"semantic_effect={helper_1_next_cont2['semantic_effect']} "
        f"ownership_effect={helper_1_next_cont2['ownership_effect']} "
        f"bytes={helper_1_next_cont2['bytes']}"
    )
    helper_1_next_cont2_prefix = report["guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof"]
    print(
        f"gf_target_c_helper_1_next_code_continuation_2_prefix=0x{helper_1_next_cont2_prefix['target_rva']:08X} "
        f"status={helper_1_next_cont2_prefix['status']} "
        f"predecessor_status={helper_1_next_cont2_prefix['predecessor_status']} "
        f"predecessor_exact={helper_1_next_cont2_prefix['predecessor_exact']} "
        f"section={helper_1_next_cont2_prefix['target_section'] or 'none'} "
        f"start_guess={hexrva(helper_1_next_cont2_prefix['function_start_guess_rva'])} "
        f"end={hexrva(helper_1_next_cont2_prefix['end_rva'])} "
        f"layout_contiguous={helper_1_next_cont2_prefix['layout_contiguous']} "
        f"bytes_match={helper_1_next_cont2_prefix['all_instruction_bytes_match']} "
        f"shared_epilogue={hexrva(helper_1_next_cont2_prefix['shared_epilogue_rva'])} "
        f"shared_epilogue_link={helper_1_next_cont2_prefix['shared_epilogue_link']} "
        f"ret=0x{helper_1_next_cont2_prefix['terminal_ret_rva']:08X} "
        f"ret_match={helper_1_next_cont2_prefix['terminal_ret_matches']} "
        f"function_entry={helper_1_next_cont2_prefix['function_entry_status']} "
        f"semantic_effect={helper_1_next_cont2_prefix['semantic_effect']} "
        f"data_semantics={helper_1_next_cont2_prefix['data_structure_semantics']} "
        f"ownership_effect={helper_1_next_cont2_prefix['ownership_effect']}"
    )
    helper_1_next_boundary = report["guarded_gf_target_c_helper_1_next_code_function_boundary_proof"]
    print(
        f"gf_target_c_helper_1_next_code_function_boundary=0x{helper_1_next_boundary['entry_rva']:08X} "
        f"status={helper_1_next_boundary['status']} "
        f"end={hexrva(helper_1_next_boundary['end_rva'])} "
        f"external_call=0x{helper_1_next_boundary['external_call_rva']:08X}->"
        f"{hexrva(helper_1_next_boundary['external_call_target_rva'])} "
        f"external_call_link={helper_1_next_boundary['external_call_link']} "
        f"padding=0x{helper_1_next_boundary['padding_start_rva']:08X}-"
        f"0x{helper_1_next_boundary['padding_end_rva'] - 1:08X} "
        f"padding_boundary={helper_1_next_boundary['padding_boundary']} "
        f"prefix_status={helper_1_next_boundary['prefix_status']} "
        f"continuation_status={helper_1_next_boundary['continuation_status']} "
        f"terminal_status={helper_1_next_boundary['terminal_status']} "
        f"body_chain={helper_1_next_boundary['body_chain']} "
        f"section={helper_1_next_boundary['target_section'] or 'none'} "
        f"text_boundary={helper_1_next_boundary['text_boundary']} "
        f"ret=0x{helper_1_next_boundary['terminal_ret_rva']:08X} "
        f"shared_epilogue=0x{helper_1_next_boundary['shared_epilogue_rva']:08X} "
        f"function_entry={helper_1_next_boundary['function_entry_status']} "
        f"semantic_effect={helper_1_next_boundary['semantic_effect']} "
        f"data_semantics={helper_1_next_boundary['data_structure_semantics']} "
        f"callee_semantics={helper_1_next_boundary['callee_semantics']} "
        f"ownership_effect={helper_1_next_boundary['ownership_effect']}"
    )
    helper_1_second_callee = report["guarded_gf_target_c_helper_1_second_callee_provenance"]
    helper_1_second_callee_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_second_callee["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_second_callee=0x{helper_1_second_callee['target_rva']:08X} "
        f"status={helper_1_second_callee['status']} "
        f"helper_predecessor={helper_1_second_callee['helper_predecessor_status']} "
        f"helper_call=0x{helper_1_second_callee['helper_call_rva']:08X} "
        f"helper_link={helper_1_second_callee['helper_call_link']} "
        f"routine_predecessor={helper_1_second_callee['routine_predecessor_status']} "
        f"routine_call=0x{helper_1_second_callee['routine_call_rva']:08X} "
        f"routine_link={helper_1_second_callee['routine_call_link']} "
        f"section={helper_1_second_callee['target_section'] or 'none'} "
        f"start_guess={hexrva(helper_1_second_callee['function_start_guess_rva'])} "
        f"probe_len={helper_1_second_callee['probe_len']} "
        f"inbound_raw={len(helper_1_second_callee['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_second_callee['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_second_callee_outbound} "
        f"function_entry={helper_1_second_callee['function_entry_status']} "
        f"semantic_effect={helper_1_second_callee['semantic_effect']} "
        f"ownership_effect={helper_1_second_callee['ownership_effect']} "
        f"bytes={helper_1_second_callee['bytes']}"
    )
    helper_1_second_callee_prefix = report[
        "guarded_gf_target_c_helper_1_second_callee_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_second_callee_prefix=0x{helper_1_second_callee_prefix['target_rva']:08X} "
        f"status={helper_1_second_callee_prefix['status']} "
        f"predecessor={helper_1_second_callee_prefix['predecessor_status']} "
        f"layout_contiguous={helper_1_second_callee_prefix['layout_contiguous']} "
        f"bytes_match={helper_1_second_callee_prefix['all_instruction_bytes_match']} "
        f"branches={helper_1_second_callee_prefix['branch_targets_match']} "
        f"terminal_shape={helper_1_second_callee_prefix['terminal_shape']} "
        f"padding={helper_1_second_callee_prefix['padding_matches']} "
        f"next_anchor={helper_1_second_callee_prefix['next_code_anchor_matches']} "
        f"function_entry={helper_1_second_callee_prefix['function_entry_status']} "
        f"semantic_effect={helper_1_second_callee_prefix['semantic_effect']} "
        f"ownership_effect={helper_1_second_callee_prefix['ownership_effect']}"
    )
    helper_1_third_callee = report[
        "guarded_gf_target_c_helper_1_third_callee_provenance"
    ]
    helper_1_third_callee_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_third_callee["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee=0x{helper_1_third_callee['target_rva']:08X} "
        f"status={helper_1_third_callee['status']} "
        f"routine_predecessor={helper_1_third_callee['routine_predecessor_status']} "
        f"routine_call=0x{helper_1_third_callee['routine_call_rva']:08X} "
        f"routine_link={helper_1_third_callee['routine_call_link']} "
        f"section={helper_1_third_callee['target_section'] or 'none'} "
        f"start_guess={hexrva(helper_1_third_callee['function_start_guess_rva'])} "
        f"probe_len={helper_1_third_callee['probe_len']} "
        f"inbound_raw={len(helper_1_third_callee['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_callee['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_callee_outbound} "
        f"function_entry={helper_1_third_callee['function_entry_status']} "
        f"semantic_effect={helper_1_third_callee['semantic_effect']} "
        f"ownership_effect={helper_1_third_callee['ownership_effect']} "
        f"bytes={helper_1_third_callee['bytes']}"
    )
    helper_1_third_callee_prefix = report[
        "guarded_gf_target_c_helper_1_third_callee_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_prefix=0x{helper_1_third_callee_prefix['target_rva']:08X} "
        f"status={helper_1_third_callee_prefix['status']} "
        f"predecessor={helper_1_third_callee_prefix['predecessor_status']} "
        f"layout_contiguous={helper_1_third_callee_prefix['layout_contiguous']} "
        f"bytes_match={helper_1_third_callee_prefix['all_instruction_bytes_match']} "
        f"prefix_end=0x{helper_1_third_callee_prefix['prefix_end_rva']:08X} "
        f"probe_end=0x{helper_1_third_callee_prefix['probe_end_rva']:08X} "
        f"probe_boundary={helper_1_third_callee_prefix['probe_boundary_matches']} "
        f"incomplete=0x{helper_1_third_callee_prefix['incomplete_instruction_rva']:08X}:"
        f"{helper_1_third_callee_prefix['incomplete_opcode']} "
        f"incomplete_match={helper_1_third_callee_prefix['incomplete_opcode_matches']} "
        f"branches={helper_1_third_callee_prefix['branch_targets_match']} "
        f"zero_target={hexrva(helper_1_third_callee_prefix['zero_branch_target_rva'])} "
        f"sign_target={hexrva(helper_1_third_callee_prefix['sign_branch_target_rva'])} "
        f"jump1={hexrva(helper_1_third_callee_prefix['jump_1_target_rva'])} "
        f"jump2={hexrva(helper_1_third_callee_prefix['jump_2_target_rva'])} "
        f"function_entry={helper_1_third_callee_prefix['function_entry_status']} "
        f"semantic_effect={helper_1_third_callee_prefix['semantic_effect']} "
        f"ownership_effect={helper_1_third_callee_prefix['ownership_effect']} "
        f"continuation={helper_1_third_callee_prefix['continuation_status']}"
    )
    helper_1_third_cont = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_provenance"
    ]
    helper_1_third_cont_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_third_cont["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation=0x{helper_1_third_cont['target_rva']:08X} "
        f"status={helper_1_third_cont['status']} "
        f"predecessor={helper_1_third_cont['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont['predecessor_exact']} "
        f"section={helper_1_third_cont['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont['probe_len']} "
        f"probe_end=0x{helper_1_third_cont['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont['probe_end_matches']} "
        f"overlap={helper_1_third_cont['overlap_opcode']} "
        f"overlap_match={helper_1_third_cont['overlap_matches']} "
        f"common_target={hexrva(helper_1_third_cont['common_forward_target_rva'])} "
        f"common_target_in_probe={helper_1_third_cont['common_forward_target_within_probe']} "
        f"inbound_raw={len(helper_1_third_cont['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_outbound} "
        f"function_entry={helper_1_third_cont['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont['semantic_effect']} "
        f"ownership_effect={helper_1_third_cont['ownership_effect']} "
        f"scope={helper_1_third_cont['continuation_scope']} "
        f"bytes={helper_1_third_cont['bytes']}"
    )
    helper_1_third_cont_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_prefix=0x{helper_1_third_cont_proof['target_rva']:08X} "
        f"status={helper_1_third_cont_proof['status']} "
        f"predecessor={helper_1_third_cont_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_proof['all_instruction_bytes_match']} "
        f"prefix_end=0x{helper_1_third_cont_proof['prefix_end_rva']:08X} "
        f"probe_end=0x{helper_1_third_cont_proof['probe_end_rva']:08X} "
        f"probe_boundary={helper_1_third_cont_proof['probe_boundary_matches']} "
        f"incomplete=0x{helper_1_third_cont_proof['incomplete_instruction_rva']:08X}:"
        f"{helper_1_third_cont_proof['incomplete_opcode']} "
        f"incomplete_match={helper_1_third_cont_proof['incomplete_opcode_matches']} "
        f"common_target={hexrva(helper_1_third_cont_proof['common_target_rva'])} "
        f"terminal={hexrva(helper_1_third_cont_proof['terminal_rva'])}:"
        f"{helper_1_third_cont_proof['terminal_bytes']} "
        f"terminal_match={helper_1_third_cont_proof['common_target_terminal_matches']} "
        f"ret={hexrva(helper_1_third_cont_proof['ret_rva'])} "
        f"post_ret={hexrva(helper_1_third_cont_proof['post_ret_rva'])} "
        f"branches={helper_1_third_cont_proof['branch_targets_match']} "
        f"back={hexrva(helper_1_third_cont_proof['back_jne_target_rva'])} "
        f"je1={hexrva(helper_1_third_cont_proof['je_1_target_rva'])} "
        f"je2={hexrva(helper_1_third_cont_proof['je_2_target_rva'])} "
        f"jbe={hexrva(helper_1_third_cont_proof['jbe_target_rva'])} "
        f"jae={hexrva(helper_1_third_cont_proof['jae_target_rva'])} "
        f"jle={hexrva(helper_1_third_cont_proof['jle_target_rva'])} "
        f"jump={hexrva(helper_1_third_cont_proof['jump_target_rva'])} "
        f"call=0x{helper_1_third_cont_proof['call_rva']:08X}->"
        f"{hexrva(helper_1_third_cont_proof['call_target_rva'])} "
        f"call_match={helper_1_third_cont_proof['call_target_matches']} "
        f"raw_call={helper_1_third_cont_proof['raw_call_candidate_present']} "
        f"function_entry={helper_1_third_cont_proof['function_entry_status']} "
        f"terminal_status={helper_1_third_cont_proof['terminal_status']} "
        f"semantic_effect={helper_1_third_cont_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_proof['ownership_effect']} "
        f"continuation={helper_1_third_cont_proof['continuation_status']}"
    )
    helper_1_third_cont_2 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance"
    ]
    helper_1_third_cont_2_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_third_cont_2["raw_outbound_rel32_candidates"]
    ) or "none"
    helper_1_third_cont_2_forward = ",".join(
        f"0x{rva:08X}" for rva in helper_1_third_cont_2["forward_target_rvas"]
    )
    print(
        f"gf_target_c_helper_1_third_callee_continuation_2=0x{helper_1_third_cont_2['target_rva']:08X} "
        f"status={helper_1_third_cont_2['status']} "
        f"predecessor={helper_1_third_cont_2['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_2['predecessor_exact']} "
        f"section={helper_1_third_cont_2['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_2['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_2['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_2['probe_end_matches']} "
        f"overlap={helper_1_third_cont_2['overlap_opcode']} "
        f"overlap_match={helper_1_third_cont_2['overlap_matches']} "
        f"forward_targets={helper_1_third_cont_2_forward} "
        f"forward_targets_in_probe={helper_1_third_cont_2['forward_targets_within_probe']} "
        f"inbound_raw={len(helper_1_third_cont_2['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_2['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_2_outbound} "
        f"function_entry={helper_1_third_cont_2['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_2['semantic_effect']} "
        f"ownership_effect={helper_1_third_cont_2['ownership_effect']} "
        f"scope={helper_1_third_cont_2['continuation_scope']} "
        f"bytes={helper_1_third_cont_2['bytes']}"
    )
    helper_1_third_cont_2_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof"
    ]
    helper_1_third_cont_2_branch_text = ",".join(
        f"0x{row['branch_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"boundary={row['target_is_instruction_boundary']}:"
        f"match={row['matches']}"
        for row in helper_1_third_cont_2_proof["branches"]
    )
    print(
        f"gf_target_c_helper_1_third_callee_continuation_2_prefix=0x{helper_1_third_cont_2_proof['target_rva']:08X} "
        f"status={helper_1_third_cont_2_proof['status']} "
        f"predecessor={helper_1_third_cont_2_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_2_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_2_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_2_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_2_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_2_proof['prefix_end_rva']:08X} "
        f"probe_end=0x{helper_1_third_cont_2_proof['probe_end_rva']:08X} "
        f"prefix_end_match={helper_1_third_cont_2_proof['prefix_end_matches']} "
        f"predecessor_targets_boundary={helper_1_third_cont_2_proof['predecessor_targets_are_instruction_boundaries']} "
        f"branches={helper_1_third_cont_2_branch_text} "
        f"branch_targets_match={helper_1_third_cont_2_proof['branch_targets_match']} "
        f"branch_targets_boundary={helper_1_third_cont_2_proof['branch_targets_are_instruction_boundaries']} "
        f"call=0x{helper_1_third_cont_2_proof['call_rva']:08X}->"
        f"{hexrva(helper_1_third_cont_2_proof['call_target_rva'])} "
        f"call_match={helper_1_third_cont_2_proof['call_target_matches']} "
        f"raw_call={helper_1_third_cont_2_proof['raw_call_candidate_present']} "
        f"leave=0x{helper_1_third_cont_2_proof['leave_rva']:08X}:"
        f"{helper_1_third_cont_2_proof['leave_bytes']} "
        f"leave_match={helper_1_third_cont_2_proof['leave_matches']} "
        f"function_entry={helper_1_third_cont_2_proof['function_entry_status']} "
        f"terminal_status={helper_1_third_cont_2_proof['terminal_status']} "
        f"semantic_effect={helper_1_third_cont_2_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_2_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_2_proof['ownership_effect']} "
        f"continuation={helper_1_third_cont_2_proof['continuation_status']}"
    )
    print(f"hud_strings={len(report['hud_strings'])}")
    if missing_known_call_sites:
        for item in missing_known_call_sites:
            print(
                f"missing_known_call_site=0x{item['rva']:08X} "
                f"{item['label']}"
            )
        return 2
    if alignment["status"] != "EXACT_PREFIX_CALL_ALIGNMENT_PROVEN":
        print("guarded_gf_target_b_alignment_proof=FAILED")
        return 3
    if helper["status"] != "EXACT_HELPER_PROVENANCE_CAPTURED":
        print("guarded_gf_target_b_helper_provenance=FAILED")
        return 4
    if target_c["status"] != "EXACT_PREFIX_CALL_ALIGNMENT_PROVEN":
        print("guarded_gf_target_c_alignment_proof=FAILED")
        return 5
    if target_c_helper_1["status"] != "EXACT_PACKED_SELECTOR_LOOKUP_PREFIX_PROVEN":
        print("guarded_gf_target_c_helper_1_prefix_proof=FAILED")
        return 6
    if target_c_helper_1_success["status"] != "EXACT_SUCCESS_CALL_CHAIN_PREFIX_PROVEN":
        print("guarded_gf_target_c_helper_1_success_prefix_proof=FAILED")
        return 7
    if first_callee_prefix["status"] != "EXACT_FIRST_CALLEE_SLOT_SCAN_PREFIX_PROVEN":
        print("guarded_gf_target_c_helper_1_first_callee_prefix_proof=FAILED")
        return 8
    if first_callee_cont["status"] != "EXACT_EXE_FIRST_CALLEE_CONTINUATION_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_first_callee_continuation_provenance=FAILED")
        return 9
    if first_callee_terminal["status"] != "EXACT_FIRST_CALLEE_TERMINAL_PADDING_ANCHOR_PROVEN":
        print("guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof=FAILED")
        return 10
    if helper_1_next_code["status"] != "EXACT_EXE_NEXT_CODE_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_next_code_provenance=FAILED")
        return 11
    if helper_1_next_prefix["status"] != "EXACT_NEXT_CODE_PREFIX_CALL_ALIGNMENT_PROVEN":
        print("guarded_gf_target_c_helper_1_next_code_prefix_proof=FAILED")
        return 12
    if helper_1_next_cont["status"] != "EXACT_EXE_NEXT_CODE_CONTINUATION_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_next_code_continuation_provenance=FAILED")
        return 13
    if helper_1_next_cont_prefix["status"] != "EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN":
        print("guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof=FAILED")
        return 14
    if helper_1_next_cont2["status"] != "EXACT_EXE_NEXT_CODE_CONTINUATION_2_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_next_code_continuation_2_provenance=FAILED")
        return 15
    if helper_1_next_cont2_prefix["status"] != "EXACT_NEXT_CODE_CONTINUATION_2_TERMINAL_PROVEN":
        print("guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof=FAILED")
        return 16
    if helper_1_next_boundary["status"] != "EXACT_28320_FUNCTION_ENTRY_BOUNDARY_PROVEN":
        print("guarded_gf_target_c_helper_1_next_code_function_boundary_proof=FAILED")
        return 17
    if helper_1_second_callee["status"] != "EXACT_EXE_8BD20_DUAL_CALL_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_second_callee_provenance=FAILED")
        return 18
    if helper_1_second_callee_prefix["status"] != "EXACT_8BD20_BOUNDED_ROUTINE_PADDING_PROVEN":
        print("guarded_gf_target_c_helper_1_second_callee_prefix_proof=FAILED")
        return 19
    if helper_1_third_callee["status"] != "EXACT_EXE_182194_CALL_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_provenance=FAILED")
        return 20
    if helper_1_third_callee_prefix["status"] != "EXACT_182194_PREFIX_CONTROL_FLOW_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_prefix_proof=FAILED")
        return 21
    if helper_1_third_cont["status"] != "EXACT_EXE_1821F3_CONTINUATION_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_provenance=FAILED")
        return 22
    if helper_1_third_cont_proof["status"] != "EXACT_1821F3_CONTINUATION_CONTROL_FLOW_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof=FAILED")
        return 23
    if helper_1_third_cont_2["status"] != "EXACT_EXE_182251_CONTINUATION_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance=FAILED")
        return 24
    if helper_1_third_cont_2_proof["status"] != "EXACT_182251_CONTINUATION_CONTROL_FLOW_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof=FAILED")
        return 25
    return 0


if __name__ == "__main__":
    raise SystemExit(main())