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


# R139/F13: exact-byte instruction-boundary anchor for guarded-GF target C.
# This bounded step proves only the first outbound E8 at 0x65997. The later
# raw candidates at 0x659AC and 0x659C1 remain intentionally unresolved.
GF_TARGET_C_ENTRY_RVA = 0x00065970
GF_TARGET_C_ALIGNED_CALL_RVA = 0x00065997
GF_TARGET_C_ALIGNED_CALL_TARGET_RVA = 0x00028460
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
)

# R140/F13: exact-byte continuation from the proven first-call prefix to the
# second outbound target-C CALL. This proves instruction alignment only.
GF_TARGET_C_SECOND_CALL_ANCHOR_RVA = 0x0006599F
GF_TARGET_C_SECOND_ALIGNED_CALL_RVA = 0x000659AC
GF_TARGET_C_SECOND_ALIGNED_CALL_TARGET_RVA = 0x00028320
GF_TARGET_C_TAIL_PROBE_RVA = 0x000659B1
GF_TARGET_C_TAIL_PROBE_LEN = 32
GF_TARGET_C_SECOND_CALL_INSTRUCTIONS = (
    (0x0006599F, "eb 13", "jmp +0x13"),
    (0x000659A1, "8b 46 18", "mov eax, [esi+0x18]"),
    (0x000659A4, "8b 4e 14", "mov ecx, [esi+0x14]"),
    (0x000659A7, "8b 16", "mov edx, [esi]"),
    (0x000659A9, "50", "push eax"),
    (0x000659AA, "51", "push ecx"),
    (0x000659AB, "52", "push edx"),
    (0x000659AC, "e8 6f 29 fc ff", "call rel32"),
)


# R141/F13: exact-byte continuation from the proven second target-C CALL to the
# third outbound target-C CALL. This proves instruction alignment only.
GF_TARGET_C_THIRD_CALL_ANCHOR_RVA = 0x000659B1
GF_TARGET_C_THIRD_ALIGNED_CALL_RVA = 0x000659C1
GF_TARGET_C_THIRD_ALIGNED_CALL_TARGET_RVA = 0x00028800
GF_TARGET_C_THIRD_CALL_INSTRUCTIONS = (
    (0x000659B1, "83 c4 0c", "add esp, 0x0c"),
    (0x000659B4, "83 f8 ff", "cmp eax, -1"),
    (0x000659B7, "89 46 08", "mov [esi+0x08], eax"),
    (0x000659BA, "74 24", "je +0x24"),
    (0x000659BC, "8b 4e 3c", "mov ecx, [esi+0x3c]"),
    (0x000659BF, "51", "push ecx"),
    (0x000659C0, "50", "push eax"),
    (0x000659C1, "e8 3a 2e fc ff", "call rel32"),
)

# R143/F13: bounded exact-EXE provenance probe for the first helper called by
# guarded-GF target C. This remains raw evidence; helper effect/ownership is not
# inferred until exact instruction/control-flow review is performed separately.
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

# R145/F13: exact-byte continuation of helper 0x28460's first successful path.
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

# R147/F13: bounded exact-EXE provenance capture for the first callee reached by
# helper 0x28460's proven success path. Raw bytes/call candidates are evidence
# only; callee semantics and render ownership remain unresolved.
GF_TARGET_C_HELPER_1_FIRST_CALLEE_RVA = 0x000282B0
GF_TARGET_C_HELPER_1_FIRST_CALLEE_PROBE_LEN = 96

# R149/F13: instruction-aligned prefix recovered from the R147 96-byte probe.
# Stop before 0x2830A because the prior bounded probe ended inside the next
# instruction. This proves local control-flow/data-address behavior only.
GF_TARGET_C_HELPER_1_FIRST_CALLEE_PREFIX_END_RVA = 0x0002830A
GF_TARGET_C_HELPER_1_FIRST_CALLEE_COUNT_TABLE = 0x00956558
GF_TARGET_C_HELPER_1_FIRST_CALLEE_CURSOR_TABLE = 0x00956500
GF_TARGET_C_HELPER_1_FIRST_CALLEE_POOL_BASE = 0x0095E028
GF_TARGET_C_HELPER_1_FIRST_CALLEE_POOL_STRIDE = 0x1F00
GF_TARGET_C_HELPER_1_FIRST_CALLEE_SLOT_STRIDE = 0x7C
GF_TARGET_C_HELPER_1_FIRST_CALLEE_RING_SIZE = 0x40
GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_RVA = 0x0002830A
GF_TARGET_C_HELPER_1_FIRST_CALLEE_CONTINUATION_PROBE_LEN = 96

# R153/F13: exact terminal sequence and padding anchor recovered from the fresh
# R151 continuation window. This proves bytes/control-flow only and does not
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

# R155/F13: independent provenance window for the code beginning at the
# R153 next-code anchor. This captures exact bytes and rel32 candidates only;
# function-entry and render semantics remain unresolved.
GF_TARGET_C_HELPER_1_NEXT_CODE_RVA = 0x00028320
GF_TARGET_C_HELPER_1_NEXT_CODE_PROBE_LEN = 96

# R157/F13: instruction-aligned prefix recovered from the R155 0x28320 window.
# Stop at 0x2837E because the 96-byte provenance window ends inside the next
# instruction. This proves branch/call alignment only, not function semantics.
GF_TARGET_C_HELPER_1_NEXT_CODE_PREFIX_END_RVA = 0x0002837E
GF_TARGET_C_HELPER_1_NEXT_CODE_COMMON_RANGE_FAIL_RVA = 0x00028433
GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_RVA = 0x00028379
GF_TARGET_C_HELPER_1_NEXT_CODE_CALL_TARGET_RVA = 0x000282B0

# R159/F13: fresh continuation provenance beginning at the exact exclusive end
# of the R157 instruction prefix. Capture bytes/call candidates only.
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA = 0x0002837E
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_PROBE_LEN = 96

# R161/F13: exact instruction-aligned decode of the complete R159 continuation
# window. The 96-byte probe ends exactly at 0x283DE, so every byte is covered by
# complete instructions. This proves control-flow/call alignment only.
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_END_RVA = 0x000283DE
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_FAIL_RVA = 0x00028433
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_RVA = 0x00028390
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_1_TARGET_RVA = 0x0008BD20
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_RVA = 0x0002839D
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_CALL_2_TARGET_RVA = 0x00182194

# R163/F13: fresh continuation provenance beginning at the exact exclusive end
# of the R161 complete instruction window. Capture bytes/call candidates only.
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA = 0x000283DE
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_PROBE_LEN = 96

# R165/F13: the complete R163 continuation window. The exact 96-byte capture
# ends at RET 0x2843D (exclusive end 0x2843E), so every byte is covered by a
# complete instruction. This proves bounded data writes/epilogue shape only.
GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_END_RVA = 0x0002843E
GF_TARGET_C_HELPER_1_NEXT_CODE_SHARED_EPILOGUE_RVA = 0x00028433

# R167/F13: structural function-entry boundary for the fully bounded 0x28320
# routine. This combines the aligned external CALL target, exact preceding INT3
# padding boundary, contiguous instruction windows, and terminal RET. It does not
# assign higher-level data/render semantics.
GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_ENTRY_RVA = 0x00028320
GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_END_RVA = 0x0002843E

# R169/F13: bounded provenance for the common 0x8BD20 callee reached by two
# independently aligned calls (0x284D2 and 0x28390). Capture bytes/call census
# only; function boundary and semantic effect remain unresolved.
GF_TARGET_C_HELPER_1_SECOND_CALLEE_RVA = 0x0008BD20
GF_TARGET_C_HELPER_1_SECOND_CALLEE_PROBE_LEN = 96

# R171/F13: instruction-aligned bounded body recovered from the R169 96-byte
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

# R173/F13: bounded provenance for the separate callee reached by the exact
# instruction-aligned 0x2839D CALL in the proven 0x28320 routine. Capture only
# exact .text bytes and raw rel32 candidates. Function-entry identity, higher-
# level semantics and render/HUD ownership remain unresolved.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_RVA = 0x00182194
GF_TARGET_C_HELPER_1_THIRD_CALLEE_PROBE_LEN = 96

# R175/F13: instruction-aligned prefix decoded from the exact R173 96-byte
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

# R177/F13: fresh exact-EXE continuation provenance starts at the proven
# instruction boundary 0x1821F3, overlapping the lone 0x8B opcode from R175.
# Capture bytes and raw rel32 candidates only. The 96-byte window contains the
# already-proven common forward target 0x182207, but no instruction semantics,
# terminal boundary, function identity, or render/HUD ownership are inferred.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_RVA = 0x001821F3
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_LEN = 96
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_PROBE_END_RVA = 0x00182253

# R179/F13: instruction-boundary proof inside the exact R177 continuation.
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


# R181/F13: fresh exact-EXE continuation provenance starts at the proven
# incomplete instruction boundary 0x182251, overlapping the two bytes 83 e0
# exposed by R179. Capture 128 bytes so the already-encoded forward targets
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


# R183/F13: exact instruction/control-flow proof inside the R181 0x182251
# continuation. The full 128-byte probe decodes into complete instructions
# through 0x1822D0 (leave). The byte after leave is outside the R181 window, so
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


# R185/F13: fresh exact-EXE continuation provenance begins at the first byte
# not covered by the R181/R183 0x182251 window. R183 proves 0x1822D0 is a
# complete leave instruction and stops exactly at 0x1822D1. Capture the next
# 96 bytes plus raw rel32 candidates only. The first captured byte is reported
# as evidence but is not interpreted as ret/function-boundary semantics here.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_RVA = 0x001822D1
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_LEN = 96
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_END_RVA = 0x00182331


# R187/F13: interpret only the first exact instruction after the R183 leave,
# then prove the immediate next instruction boundary. R185 captured raw c3 at
# 0x1822D1 and an E8 rel32 candidate at 0x1822D2. This proof may establish the
# exact leave;ret terminal and the 0x1822D2 instruction start/call target, but
# it does not promote 0x1822D2 to a function entry or infer callee/render/HUD
# semantics.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_LEAVE_RVA = 0x001822D0
GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_RET_RVA = 0x001822D1
GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_BYTES = bytes.fromhex("c9 c3")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA = 0x001822D2
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_BYTES = bytes.fromhex("e8 15 39 00 00")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_CALL_TARGET_RVA = 0x00185BEC


# R189/F13: decode the exact code sequence beginning at the R187-proven
# instruction boundary 0x1822D2 through its ret at 0x1822F3, then require the
# 12-byte INT3 padding through 0x1822FF. 0x182300 is thereby established only
# as the next code boundary; neither 0x1822D2 nor 0x182300 is promoted to a
# function-entry identity and no callee/render/HUD semantics are inferred.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PREFIX_END_RVA = 0x001822F4
GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_RET_RVA = 0x001822F3
GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_RVA = 0x001822F4
GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_LEN = 12
GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_NEXT_CODE_RVA = 0x00182300
GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_BRANCHES = (
    (0x001822E0, 0x001822E7),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_CALLS = (
    (0x001822D2, 0x00185BEC),
    (0x001822E2, 0x00186B0E),
    (0x001822EC, 0x00182209),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_INSTRUCTIONS = (
    (0x001822D2, "e8 15 39 00 00", "call 0x185bec"),
    (0x001822D7, "8b 40 64", "mov eax, [eax+0x64]"),
    (0x001822DA, "3b 05 5c 5e 73 00", "cmp eax, [0x735e5c]"),
    (0x001822E0, "74 05", "je 0x1822e7"),
    (0x001822E2, "e8 27 48 00 00", "call 0x186b0e"),
    (0x001822E7, "ff 74 24 04", "push dword [esp+4]"),
    (0x001822EB, "50", "push eax"),
    (0x001822EC, "e8 18 ff ff ff", "call 0x182209"),
    (0x001822F1, "59", "pop ecx"),
    (0x001822F2, "59", "pop ecx"),
    (0x001822F3, "c3", "ret"),
)


# R191/F13: decode the exact code sequence beginning at the R189-proven
# 0x182300 code boundary through its immediate ret at 0x182313. The byte at
# 0x182314 is thereby established only as the next instruction boundary.
# Rel32 calls are validated against the R185 raw census, but neither 0x182300,
# 0x182314 nor the 0x18231D call target is promoted to a function-entry
# identity or semantic/render ownership claim.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_START_RVA = 0x00182300
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_PREFIX_END_RVA = 0x00182314
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_RET_RVA = 0x00182313
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_NEXT_INSTRUCTION_RVA = 0x00182314
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CALLS = (
    (0x00182306, 0x00188948),
    (0x0018230B, 0x0018231D),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INSTRUCTIONS = (
    (0x00182300, "83 ec 0c", "sub esp, 0x0c"),
    (0x00182303, "dd 14 24", "fst qword [esp]"),
    (0x00182306, "e8 3d 66 00 00", "call 0x188948"),
    (0x0018230B, "e8 0d 00 00 00", "call 0x18231d"),
    (0x00182310, "83 c4 0c", "add esp, 0x0c"),
    (0x00182313, "c3", "ret"),
)


# R193/F13: consume the remaining exact bytes in the R185 0x1822D1 probe,
# beginning at the R191-proven 0x182314 boundary and ending exactly at the
# probe boundary 0x182331. The prior 0x18230B call proves 0x18231D is an
# incoming call target and this proof confirms it is an instruction boundary.
# The two forward conditional targets 0x182331 and 0x182391 are decoded only;
# their target instruction boundaries and higher-level semantics remain
# unresolved because they are outside the captured byte window.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_RVA = 0x00182314
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_END_RVA = 0x00182331
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_CALL_RVA = 0x0018230B
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_TARGET_RVA = 0x0018231D
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_BRANCHES = (
    (0x00182322, 0x00182391),
    (0x0018232A, 0x00182331),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_CALLS = (
    (0x00182318, 0x00188905),
    (0x0018232C, 0x001888D5),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_INSTRUCTIONS = (
    (0x00182314, "8d 54 24 04", "lea edx, [esp+4]"),
    (0x00182318, "e8 e8 65 00 00", "call 0x188905"),
    (0x0018231D, "52", "push edx"),
    (0x0018231E, "9b", "fwait"),
    (0x0018231F, "d9 3c 24", "fnstcw word [esp]"),
    (0x00182322, "74 6d", "je 0x182391"),
    (0x00182324, "66 81 3c 24 7f 02", "cmp word [esp], 0x027f"),
    (0x0018232A, "74 05", "je 0x182331"),
    (0x0018232C, "e8 a4 65 00 00", "call 0x1888d5"),
)


# R195/F13: fresh exact-EXE provenance starts exactly at the R193 capture end
# and runs 96 bytes to the previously decoded forward target 0x182391. This
# task captures raw evidence only: it does not decode 0x182331 as an
# instruction boundary, nor promote 0x182391, any rel32 candidate, or any
# render/HUD semantic identity.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA = 0x00182331
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_LEN = 96
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_END_RVA = 0x00182391


# R197/F13: exact-decode the entire R195 96-byte continuation window. The
# predecessor R193 branch 0x18232A -> 0x182331 is thereby upgraded from a
# decoded-only target to a proven instruction boundary. Internal control flow
# and the single rel32 call are validated, while targets at/after 0x182391
# remain outside captured bytes and retain unresolved boundary/function status.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PREFIX_END_RVA = 0x00182391
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_INCOMING_BRANCH_RVA = 0x0018232A
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_BRANCHES = (
    (0x00182336, 0x00182365, "rel8"),
    (0x0018234F, 0x0018895E, "rel32"),
    (0x00182360, 0x0018896B, "rel32"),
    (0x00182365, 0x0018239F, "rel8"),
    (0x00182376, 0x0018239F, "rel8"),
    (0x00182380, 0x00182386, "rel8"),
    (0x00182384, 0x00182348, "rel8"),
    (0x00182388, 0x00182348, "rel8"),
    (0x0018238F, 0x001823AC, "rel8"),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_CALLS = (
    (0x0018238A, 0x001888EC),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_INSTRUCTIONS = (
    (0x00182331, "3d 00 00 f0 3f", "cmp eax, 0x3ff00000"),
    (0x00182336, "73 2d", "jae 0x182365"),
    (0x00182338, "d9 e8", "fld1"),
    (0x0018233A, "d8 c1", "fadd st(0), st(1)"),
    (0x0018233C, "d9 e8", "fld1"),
    (0x0018233E, "d8 e2", "fsub st(0), st(2)"),
    (0x00182340, "de c9", "fmulp st(1), st(0)"),
    (0x00182342, "d9 fa", "fsqrt"),
    (0x00182344, "d9 c9", "fxch st(1)"),
    (0x00182346, "d9 f3", "fpatan"),
    (0x00182348, "83 3d 64 fa 85 00 00", "cmp dword [0x85fa64], 0"),
    (0x0018234F, "0f 85 09 66 00 00", "jne 0x18895e"),
    (0x00182355, "ba 0d 00 00 00", "mov edx, 0x0d"),
    (0x0018235A, "8d 0d d0 59 73 00", "lea ecx, [0x7359d0]"),
    (0x00182360, "e9 06 66 00 00", "jmp 0x18896b"),
    (0x00182365, "77 38", "ja 0x18239f"),
    (0x00182367, "8b 44 24 0c", "mov eax, [esp+0x0c]"),
    (0x0018236B, "8b c8", "mov ecx, eax"),
    (0x0018236D, "25 ff ff 0f 00", "and eax, 0x000fffff"),
    (0x00182372, "0b 44 24 08", "or eax, [esp+0x08]"),
    (0x00182376, "75 27", "jne 0x18239f"),
    (0x00182378, "81 e1 00 00 00 80", "and ecx, 0x80000000"),
    (0x0018237E, "dd d8", "fstp st(0)"),
    (0x00182380, "74 04", "je 0x182386"),
    (0x00182382, "d9 eb", "fldpi"),
    (0x00182384, "eb c2", "jmp 0x182348"),
    (0x00182386, "d9 ee", "fldz"),
    (0x00182388, "eb be", "jmp 0x182348"),
    (0x0018238A, "e8 5d 65 00 00", "call 0x1888ec"),
    (0x0018238F, "eb 1b", "jmp 0x1823ac"),
)


# R199/F13: extend exact-EXE provenance from the R197 capture end at 0x182391.
# The 96-byte window includes the previously decoded forward targets 0x18239F
# and 0x1823AC, but this task records raw bytes/census only and deliberately
# does not promote any endpoint or included target to an instruction boundary,
# function entry, callee identity, or render/HUD semantic owner.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RVA = 0x00182391
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_LEN = 96
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_END_RVA = 0x001823F1
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_REFERENCED_TARGET_RVAS = (
    0x00182391,
    0x0018239F,
    0x001823AC,
)


# R201/F13: exact-decode the first complete block in the R199 continuation.
# This upgrades previously decoded targets 0x182391, 0x18239F and 0x1823AC
# to proven instruction boundaries, proves ret at 0x1823CA, five INT3 padding
# bytes, and the next code boundary at 0x1823D0. Callee/function/render
# semantics remain intentionally unresolved.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PREFIX_END_RVA = 0x001823CB
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RET_RVA = 0x001823CA
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_RVA = 0x001823CB
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_LEN = 5
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_NEXT_CODE_RVA = 0x001823D0
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_REFERENCED_BOUNDARY_RVAS = (
    0x00182391,
    0x0018239F,
    0x001823AC,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_BRANCHES = (
    (0x00182396, 0x0018238A, "rel8"),
    (0x0018239D, 0x0018238A, "rel8"),
    (0x001823B3, 0x0018895E, "rel32"),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_CALLS = (
    (0x001823C4, 0x00188877),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_INSTRUCTIONS = (
    (0x00182391, "a9 ff ff 0f 00", "test eax, 0x000fffff"),
    (0x00182396, "75 f2", "jne 0x18238a"),
    (0x00182398, "83 7c 24 08 00", "cmp dword [esp+8], 0"),
    (0x0018239D, "75 eb", "jne 0x18238a"),
    (0x0018239F, "dd d8", "fstp st(0)"),
    (0x001823A1, "db 2d f0 60 73 00", "fld tbyte [0x7360f0]"),
    (0x001823A7, "b8 01 00 00 00", "mov eax, 1"),
    (0x001823AC, "83 3d 64 fa 85 00 00", "cmp dword [0x85fa64], 0"),
    (0x001823B3, "0f 85 a5 65 00 00", "jne 0x18895e"),
    (0x001823B9, "ba 0d 00 00 00", "mov edx, 0x0d"),
    (0x001823BE, "8d 0d d0 59 73 00", "lea ecx, [0x7359d0]"),
    (0x001823C4, "e8 ae 64 00 00", "call 0x188877"),
    (0x001823C9, "5a", "pop edx"),
    (0x001823CA, "c3", "ret"),
)


# R203/F13: consume the remaining complete instructions in the R199 capture,
# starting at the R201-proven 0x1823D0 boundary. The exact sequence contains
# one complete sub/fst/call/call/add/ret block and a following lea/call/push/
# fwait prefix. The capture ends after two bytes of the next instruction at
# 0x1823EF, so no decode is promoted beyond that capture edge. Function,
# callee and render/HUD semantics remain intentionally unresolved.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RVA = 0x001823D0
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_PREFIX_END_RVA = 0x001823EF
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RET_RVA = 0x001823E3
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_NEXT_CODE_RVA = 0x001823E4
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INCOMPLETE_RVA = 0x001823EF
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INCOMPLETE_BYTES = bytes.fromhex("d9 3c")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_CALLS = (
    (0x001823D6, 0x00188948),
    (0x001823DB, 0x001823ED),
    (0x001823E8, 0x00188905),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INSTRUCTIONS = (
    (0x001823D0, "83 ec 0c", "sub esp, 0x0c"),
    (0x001823D3, "dd 14 24", "fst qword [esp]"),
    (0x001823D6, "e8 6d 65 00 00", "call 0x188948"),
    (0x001823DB, "e8 0d 00 00 00", "call 0x1823ed"),
    (0x001823E0, "83 c4 0c", "add esp, 0x0c"),
    (0x001823E3, "c3", "ret"),
    (0x001823E4, "8d 54 24 04", "lea edx, [esp+4]"),
    (0x001823E8, "e8 18 65 00 00", "call 0x188905"),
    (0x001823ED, "52", "push edx"),
    (0x001823EE, "9b", "fwait"),
)


# R205/F13: extend exact-EXE provenance from the R203 capture edge at
# 0x1823EF. This is deliberately a raw-byte proof only: it requires the exact
# d9 3c overlap already proven by R203, then captures a fresh 64-byte .text
# window through exclusive end 0x18242F. No instruction, function, callee,
# render or HUD semantic identity is promoted by this collector.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_RVA = 0x001823EF
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_END_RVA = 0x0018242F
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PRIOR_CAPTURE_END_RVA = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_END_RVA
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INCOMPLETE_BYTES
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PREFIX_END_RVA = 0x0018242E
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_RVA = 0x0018242E
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_BYTES = bytes.fromhex("e9")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_BRANCHES = (
    (0x001823F2, 0x00182461),
    (0x001823FA, 0x00182401),
    (0x00182406, 0x00182433),
    (0x0018241D, 0x0018895E),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_CALLS = (
    (0x001823FC, 0x001888D5),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INSTRUCTIONS = (
    (0x001823EF, "d9 3c 24", "fnstcw word [esp]"),
    (0x001823F2, "74 6d", "je 0x182461"),
    (0x001823F4, "66 81 3c 24 7f 02", "cmp word [esp], 0x027f"),
    (0x001823FA, "74 05", "je 0x182401"),
    (0x001823FC, "e8 d4 64 00 00", "call 0x1888d5"),
    (0x00182401, "3d 00 00 f0 3f", "cmp eax, 0x3ff00000"),
    (0x00182406, "73 2b", "jae 0x182433"),
    (0x00182408, "d9 e8", "fld1"),
    (0x0018240A, "d8 c1", "fadd st(0), st(1)"),
    (0x0018240C, "d9 e8", "fld1"),
    (0x0018240E, "d8 e2", "fsub st(0), st(2)"),
    (0x00182410, "de c9", "fmulp st(1), st(0)"),
    (0x00182412, "d9 fa", "fsqrt"),
    (0x00182414, "d9 f3", "fpatan"),
    (0x00182416, "83 3d 64 fa 85 00 00", "cmp dword [0x85fa64], 0"),
    (0x0018241D, "0f 85 3b 65 00 00", "jne 0x18895e"),
    (0x00182423, "ba 0e 00 00 00", "mov edx, 0x0e"),
    (0x00182428, "8d 0d e0 59 73 00", "lea ecx, [0x7359e0]"),
)


# R209/F13: extend exact-EXE provenance from the R207 capture edge at
# 0x18242E. This is deliberately a raw-byte proof only: it requires the exact
# e9 overlap preserved by R207, then captures a fresh 64-byte .text window
# through exclusive end 0x18246E. No instruction, function, callee, render or
# HUD semantic identity is promoted by this collector.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_RVA = 0x0018242E
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_END_RVA = 0x0018246E
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PRIOR_CAPTURE_END_RVA = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_END_RVA
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_BYTES
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PREFIX_END_RVA = 0x0018246D
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_RVA = 0x0018246D
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_BYTES = bytes.fromhex("75")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_BRANCHES = (
    (0x0018242E, 0x0018896B),
    (0x00182433, 0x0018246F),
    (0x00182444, 0x0018246F),
    (0x00182454, 0x00182416),
    (0x00182458, 0x00182416),
    (0x0018245F, 0x0018247C),
    (0x00182466, 0x0018245A),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_CALLS = (
    (0x0018245A, 0x001888EC),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INSTRUCTIONS = (
    (0x0018242E, "e9 38 65 00 00", "jmp 0x18896b"),
    (0x00182433, "77 3a", "ja 0x18246f"),
    (0x00182435, "8b 44 24 0c", "mov eax, [esp+0x0c]"),
    (0x00182439, "8b c8", "mov ecx, eax"),
    (0x0018243B, "25 ff ff 0f 00", "and eax, 0x000fffff"),
    (0x00182440, "0b 44 24 08", "or eax, [esp+0x08]"),
    (0x00182444, "75 29", "jne 0x18246f"),
    (0x00182446, "81 e1 00 00 00 80", "and ecx, 0x80000000"),
    (0x0018244C, "dd d8", "fstp st(0)"),
    (0x0018244E, "db 2d fa 60 73 00", "fld tbyte [0x7360fa]"),
    (0x00182454, "74 c0", "je 0x182416"),
    (0x00182456, "d9 e0", "fchs"),
    (0x00182458, "eb bc", "jmp 0x182416"),
    (0x0018245A, "e8 8d 64 00 00", "call 0x1888ec"),
    (0x0018245F, "eb 1b", "jmp 0x18247c"),
    (0x00182461, "a9 ff ff 0f 00", "test eax, 0x000fffff"),
    (0x00182466, "75 f2", "jne 0x18245a"),
    (0x00182468, "83 7c 24 08 00", "cmp dword [esp+0x08], 0"),
)

# R213/F13: extend exact-EXE provenance from the R211 capture edge at
# 0x18246D. This is deliberately a raw-byte proof only: it requires the exact
# 75 overlap preserved by R211, then captures a fresh 64-byte .text window
# through exclusive end 0x1824AD. No instruction, function, callee, render or
# HUD semantic identity is promoted by this collector.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RVA = 0x0018246D
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_END_RVA = 0x001824AD
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PRIOR_CAPTURE_END_RVA = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_END_RVA
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_BYTES
)

# R215/F13: exact-decode only complete instructions from the R213-proven
# 0x18246D..0x1824AD capture. The final e8 5e bytes begin a rel32 CALL but
# do not contain its full displacement, so they remain an explicit capture
# edge. Function/callee/render/HUD semantics remain unresolved.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PREFIX_END_RVA = 0x001824AB
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RET_RVA = 0x0018249A
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_NEXT_CODE_RVA = 0x0018249B
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_RVA = 0x001824AB
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_BYTES = bytes.fromhex("e8 5e")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_BRANCHES = (
    (0x0018246D, 0x0018245A),
    (0x00182483, 0x0018895E),
    (0x001824A9, 0x001824B0),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_CALLS = (
    (0x00182494, 0x00188877),
    (0x0018249B, 0x00185BEC),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INSTRUCTIONS = (
    (0x0018246D, "75 eb", "jne 0x18245a"),
    (0x0018246F, "dd d8", "fstp st(0)"),
    (0x00182471, "db 2d f0 60 73 00", "fld tbyte [0x7360f0]"),
    (0x00182477, "b8 01 00 00 00", "mov eax, 1"),
    (0x0018247C, "83 3d 64 fa 85 00 00", "cmp dword [0x85fa64], 0"),
    (0x00182483, "0f 85 d5 64 00 00", "jne 0x18895e"),
    (0x00182489, "ba 0e 00 00 00", "mov edx, 0x0e"),
    (0x0018248E, "8d 0d e0 59 73 00", "lea ecx, [0x7359e0]"),
    (0x00182494, "e8 de 63 00 00", "call 0x188877"),
    (0x00182499, "5a", "pop edx"),
    (0x0018249A, "c3", "ret"),
    (0x0018249B, "e8 4c 37 00 00", "call 0x185bec"),
    (0x001824A0, "8b 40 64", "mov eax, [eax+0x64]"),
    (0x001824A3, "3b 05 5c 5e 73 00", "cmp eax, [0x735e5c]"),
    (0x001824A9, "74 05", "je 0x1824b0"),
)


# R217/F13: extend exact-EXE provenance from the R215 capture edge at
# 0x1824AB. This is deliberately a raw-byte proof only: it requires the exact
# e8 5e overlap preserved by R215, then captures a fresh 64-byte .text window
# through exclusive end 0x1824EB. No instruction, function, callee, render or
# HUD semantic identity is promoted by this collector.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RVA = 0x001824AB
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_END_RVA = 0x001824EB
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PRIOR_CAPTURE_END_RVA = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_END_RVA
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_BYTES
)


# R219/F13: exact-decode only complete instructions from the R217-proven
# 0x1824AB..0x1824EB capture. The final e8 byte at 0x1824EA begins a rel32
# CALL but does not contain its displacement, so it remains an explicit
# capture edge. Function/callee/render/HUD semantics remain unresolved.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PREFIX_END_RVA = 0x001824EA
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RET_RVAS = (
    0x001824C8,
    0x001824D9,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_POST_RET_CODE_RVAS = (
    0x001824C9,
    0x001824DA,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INCOMPLETE_RVA = 0x001824EA
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INCOMPLETE_BYTES = bytes.fromhex("e8")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_BRANCHES = (
    (0x001824B4, 0x001824C9),
    (0x001824E8, 0x001824EF),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_CALLS = (
    (0x001824AB, 0x00186B0E),
    (0x001824C0, 0x00186906),
    (0x001824DA, 0x00185BEC),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INSTRUCTIONS = (
    (0x001824AB, "e8 5e 46 00 00", "call 0x186b0e"),
    (0x001824B0, "83 78 28 01", "cmp dword [eax+0x28], 1"),
    (0x001824B4, "7e 13", "jle 0x1824c9"),
    (0x001824B6, "68 03 01 00 00", "push 0x103"),
    (0x001824BB, "ff 74 24 08", "push dword [esp+0x08]"),
    (0x001824BF, "50", "push eax"),
    (0x001824C0, "e8 41 44 00 00", "call 0x186906"),
    (0x001824C5, "83 c4 0c", "add esp, 0x0c"),
    (0x001824C8, "c3", "ret"),
    (0x001824C9, "8b 40 48", "mov eax, [eax+0x48]"),
    (0x001824CC, "8b 4c 24 04", "mov ecx, [esp+0x04]"),
    (0x001824D0, "0f b7 04 48", "movzx eax, word [eax+ecx*2]"),
    (0x001824D4, "25 03 01 00 00", "and eax, 0x103"),
    (0x001824D9, "c3", "ret"),
    (0x001824DA, "e8 0d 37 00 00", "call 0x185bec"),
    (0x001824DF, "8b 40 64", "mov eax, [eax+0x64]"),
    (0x001824E2, "3b 05 5c 5e 73 00", "cmp eax, [0x735e5c]"),
    (0x001824E8, "74 05", "je 0x1824ef"),
)

# R221/F13: extend exact-EXE provenance from the R219 capture edge at
# 0x1824EA. This is deliberately a raw-byte proof only: it requires the exact
# e8 overlap preserved by R219, then captures a fresh 64-byte .text window
# through exclusive end 0x18252A. No instruction, function, callee, render or
# HUD semantic identity is promoted by this collector.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RVA = 0x001824EA
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_END_RVA = 0x0018252A
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PRIOR_CAPTURE_END_RVA = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_END_RVA
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INCOMPLETE_BYTES
)

# R223/F13: exact-decode only complete instructions from the R221-proven
# 0x1824EA..0x18252A capture. The final 83 byte at 0x182529 begins another
# instruction but does not contain enough bytes to decode it, so it remains
# an explicit capture edge. Function/callee/render/HUD semantics remain
# unresolved.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PREFIX_END_RVA = 0x00182529
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RET_RVAS = (
    0x00182504,
    0x00182513,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_POST_RET_CODE_RVAS = (
    0x00182505,
    0x00182514,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_RVA = 0x00182529
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_BYTES = bytes.fromhex("83")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_BRANCHES = (
    (0x001824F3, 0x00182505),
    (0x00182522, 0x00182529),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_CALLS = (
    (0x001824EA, 0x00186B0E),
    (0x001824FC, 0x00186906),
    (0x00182514, 0x00185BEC),
    (0x00182524, 0x00186B0E),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INSTRUCTIONS = (
    (0x001824EA, "e8 1f 46 00 00", "call 0x186b0e"),
    (0x001824EF, "83 78 28 01", "cmp dword [eax+0x28], 1"),
    (0x001824F3, "7e 10", "jle 0x182505"),
    (0x001824F5, "6a 04", "push 4"),
    (0x001824F7, "ff 74 24 08", "push dword [esp+0x08]"),
    (0x001824FB, "50", "push eax"),
    (0x001824FC, "e8 05 44 00 00", "call 0x186906"),
    (0x00182501, "83 c4 0c", "add esp, 0x0c"),
    (0x00182504, "c3", "ret"),
    (0x00182505, "8b 40 48", "mov eax, [eax+0x48]"),
    (0x00182508, "8b 4c 24 04", "mov ecx, [esp+0x04]"),
    (0x0018250C, "0f b6 04 48", "movzx eax, byte [eax+ecx*2]"),
    (0x00182510, "83 e0 04", "and eax, 4"),
    (0x00182513, "c3", "ret"),
    (0x00182514, "e8 d3 36 00 00", "call 0x185bec"),
    (0x00182519, "8b 40 64", "mov eax, [eax+0x64]"),
    (0x0018251C, "3b 05 5c 5e 73 00", "cmp eax, [0x735e5c]"),
    (0x00182522, "74 05", "je 0x182529"),
    (0x00182524, "e8 e5 45 00 00", "call 0x186b0e"),
)


# R225/F13: extend exact-EXE provenance from the R223 capture edge at
# 0x182529. This is deliberately a raw-byte proof only: it requires the exact
# 83 overlap preserved by R223, then captures a fresh 64-byte .text window
# through exclusive end 0x182569. No instruction, function, callee, render or
# HUD semantic identity is promoted by this collector.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_RVA = 0x00182529
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_END_RVA = 0x00182569
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PRIOR_CAPTURE_END_RVA = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_END_RVA
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_BYTES
)

# R263/F13: extend exact-EXE provenance from the R261-proven exact capture
# boundary at 0x182569. Unlike R225, the predecessor decode ends exactly on an
# instruction boundary, so this fresh 64-byte .text window starts contiguously
# at 0x182569 without overlapping an incomplete instruction. This collector is
# raw provenance only and does not promote function/callee/render/HUD semantics.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_RVA = 0x00182569
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_END_RVA = 0x001825A9
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PRIOR_CAPTURE_END_RVA = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_END_RVA
)

# R267/F13 follow-up: the validated R263/R267 window ends three bytes into a
# five-byte TEST EAX, imm32 instruction at 0x1825A6. Start the next provenance
# window at that incomplete instruction, require the known a9 00 00 overlap,
# and extend far enough to include the nearby 0x1825AD/B2/B7/BC branch targets.
# This remains raw provenance only; no function/render/HUD semantics are inferred.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_RVA = 0x001825A6
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_END_RVA = 0x001825E6
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PRIOR_CAPTURE_END_RVA = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_END_RVA
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_OVERLAP_BYTES = bytes.fromhex(
    "a9 00 00"
)

# R267/F13 exact decode of the validated 0x1825A6..0x1825E6 window. Only
# complete instructions are admitted. The final 0x74 byte at 0x1825E5 begins a
# short conditional branch whose displacement lies outside the capture, so it
# remains an explicit incomplete capture edge.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PREFIX_END_RVA = 0x001825E5
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INCOMPLETE_RVA = 0x001825E5
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INCOMPLETE_BYTES = bytes.fromhex("74")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PREDECESSOR_TARGET_RVAS = (
    0x001825AD,
    0x001825B2,
    0x001825B7,
    0x001825BC,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_BACKEDGE_TARGET_RVA = 0x0018257C
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_BACKEDGE_TARGET_BYTES = bytes.fromhex("8b 07")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_BRANCHES = (
    (0x001825AB, 0x0018257C),
    (0x001825B0, 0x001825BF),
    (0x001825B5, 0x001825BF),
    (0x001825BA, 0x001825BF),
    (0x001825C9, 0x001825D4),
    (0x001825D0, 0x0018262E),
    (0x001825D2, 0x001825F6),
    (0x001825DB, 0x0018261A),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INSTRUCTIONS = (
    (0x001825A6, "a9 00 00 00 ff", "test eax, 0xff000000"),
    (0x001825AB, "75 cf", "jne 0x18257c"),
    (0x001825AD, "83 ef 01", "sub edi, 1"),
    (0x001825B0, "eb 0d", "jmp 0x1825bf"),
    (0x001825B2, "83 ef 02", "sub edi, 2"),
    (0x001825B5, "eb 08", "jmp 0x1825bf"),
    (0x001825B7, "83 ef 03", "sub edi, 3"),
    (0x001825BA, "eb 03", "jmp 0x1825bf"),
    (0x001825BC, "83 ef 04", "sub edi, 4"),
    (0x001825BF, "8b 74 24 14", "mov esi, [esp+0x14]"),
    (0x001825C3, "f7 c6 03 00 00 00", "test esi, 3"),
    (0x001825C9, "75 09", "jne 0x1825d4"),
    (0x001825CB, "8b d9", "mov ebx, ecx"),
    (0x001825CD, "c1 e9 02", "shr ecx, 2"),
    (0x001825D0, "75 5c", "jne 0x18262e"),
    (0x001825D2, "eb 22", "jmp 0x1825f6"),
    (0x001825D4, "8a 16", "mov dl, [esi]"),
    (0x001825D6, "83 c6 01", "add esi, 1"),
    (0x001825D9, "84 d2", "test dl, dl"),
    (0x001825DB, "74 3d", "je 0x18261a"),
    (0x001825DD, "88 17", "mov [edi], dl"),
    (0x001825DF, "83 c7 01", "add edi, 1"),
    (0x001825E2, "83 e9 01", "sub ecx, 1"),
)

# R267/F13 next bounded window. The prior proof ends with the single-byte 0x74
# short-Jcc opcode at 0x1825E5, so overlap that byte and capture through an exact
# instruction boundary at 0x182635. This range includes all previously unresolved
# forward targets 0x1825F6, 0x18261A and 0x18262E.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_RVA = 0x001825E5
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_LEN = 80
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_END_RVA = 0x00182635
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PRIOR_CAPTURE_END_RVA = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_END_RVA
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INCOMPLETE_BYTES
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREFIX_END_RVA = 0x00182635
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREDECESSOR_TARGET_RVAS = (
    0x001825F6,
    0x0018261A,
    0x0018262E,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_BACKEDGE_TARGET_RVA = 0x001825D4
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_BACKEDGE_TARGET_BYTES = bytes.fromhex("8a 16")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_RET_RVAS = (
    0x00182619,
    0x00182623,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_POST_RET_CODE_RVAS = (
    0x0018261A,
    0x00182624,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_BRANCHES = (
    (0x001825E5, 0x00182610),
    (0x001825ED, 0x001825D4),
    (0x001825F4, 0x0018262E),
    (0x001825FB, 0x00182610),
    (0x00182609, 0x00182612),
    (0x0018260E, 0x001825FD),
    (0x0018262C, 0x001825F6),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_INSTRUCTIONS = (
    (0x001825E5, "74 29", "je 0x182610"),
    (0x001825E7, "f7 c6 03 00 00 00", "test esi, 3"),
    (0x001825ED, "75 e5", "jne 0x1825d4"),
    (0x001825EF, "8b d9", "mov ebx, ecx"),
    (0x001825F1, "c1 e9 02", "shr ecx, 2"),
    (0x001825F4, "75 38", "jne 0x18262e"),
    (0x001825F6, "8b cb", "mov ecx, ebx"),
    (0x001825F8, "83 e1 03", "and ecx, 3"),
    (0x001825FB, "74 13", "je 0x182610"),
    (0x001825FD, "8a 16", "mov dl, [esi]"),
    (0x001825FF, "83 c6 01", "add esi, 1"),
    (0x00182602, "88 17", "mov [edi], dl"),
    (0x00182604, "83 c7 01", "add edi, 1"),
    (0x00182607, "84 d2", "test dl, dl"),
    (0x00182609, "74 07", "je 0x182612"),
    (0x0018260B, "83 e9 01", "sub ecx, 1"),
    (0x0018260E, "75 ed", "jne 0x1825fd"),
    (0x00182610, "88 0f", "mov [edi], cl"),
    (0x00182612, "5b", "pop ebx"),
    (0x00182613, "5e", "pop esi"),
    (0x00182614, "8b 44 24 08", "mov eax, [esp+0x08]"),
    (0x00182618, "5f", "pop edi"),
    (0x00182619, "c3", "ret"),
    (0x0018261A, "88 17", "mov [edi], dl"),
    (0x0018261C, "8b 44 24 10", "mov eax, [esp+0x10]"),
    (0x00182620, "5b", "pop ebx"),
    (0x00182621, "5e", "pop esi"),
    (0x00182622, "5f", "pop edi"),
    (0x00182623, "c3", "ret"),
    (0x00182624, "89 17", "mov [edi], edx"),
    (0x00182626, "83 c7 04", "add edi, 4"),
    (0x00182629, "83 e9 01", "sub ecx, 1"),
    (0x0018262C, "74 c8", "je 0x1825f6"),
    (0x0018262E, "ba ff fe fe 7e", "mov edx, 0x7efefeff"),
    (0x00182633, "8b 06", "mov eax, [esi]"),
)


# R271/F13 fresh bounded provenance from the exact 0x182635 instruction boundary.
# This stage intentionally captures bytes only. It does not infer a function boundary,
# render/HUD ownership, or runtime semantics from the continuation.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_RVA = 0x00182635
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PROBE_END_RVA = 0x00182675
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREDECESSOR_END_RVA = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREFIX_END_RVA
)

GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREFIX_END_RVA = 0x00182673
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INCOMPLETE_RVA = 0x00182673
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INCOMPLETE_BYTES = bytes.fromhex("88 57")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREDECESSOR_TARGET_BYTES = (
    (0x00182624, bytes.fromhex("89 17")),
    (0x0018261A, bytes.fromhex("88 17")),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_BRANCHES = (
    (0x00182646, 0x00182624),
    (0x0018264A, 0x0018261A),
    (0x0018264E, 0x0018267A),
    (0x00182656, 0x0018266A),
    (0x0018265E, 0x00182624),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INSTRUCTIONS = (
    (0x00182635, "03 d0", "add edx, eax"),
    (0x00182637, "83 f0 ff", "xor eax, 0xffffffff"),
    (0x0018263A, "33 c2", "xor eax, edx"),
    (0x0018263C, "8b 16", "mov edx, [esi]"),
    (0x0018263E, "83 c6 04", "add esi, 4"),
    (0x00182641, "a9 00 01 01 81", "test eax, 0x81010100"),
    (0x00182646, "74 dc", "je 0x182624"),
    (0x00182648, "84 d2", "test dl, dl"),
    (0x0018264A, "74 ce", "je 0x18261a"),
    (0x0018264C, "84 f6", "test dh, dh"),
    (0x0018264E, "74 2a", "je 0x18267a"),
    (0x00182650, "f7 c2 00 00 ff 00", "test edx, 0x00ff0000"),
    (0x00182656, "74 12", "je 0x18266a"),
    (0x00182658, "f7 c2 00 00 00 ff", "test edx, 0xff000000"),
    (0x0018265E, "75 c4", "jne 0x182624"),
    (0x00182660, "89 17", "mov [edi], edx"),
    (0x00182662, "8b 44 24 10", "mov eax, [esp+0x10]"),
    (0x00182666, "5b", "pop ebx"),
    (0x00182667, "5e", "pop esi"),
    (0x00182668, "5f", "pop edi"),
    (0x00182669, "c3", "ret"),
    (0x0018266A, "66 89 17", "mov [edi], dx"),
    (0x0018266D, "33 d2", "xor edx, edx"),
    (0x0018266F, "8b 44 24 10", "mov eax, [esp+0x10]"),
)


# R271/F13 continuation from the cut MOV at 0x182673. The canonical artifact
# completes that instruction, resolves the prior 0x18267A forward target, and the
# bounded 64-byte window ends exactly on the 0x1826B3 instruction boundary.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_RVA = 0x00182673
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_END_RVA = 0x001826B3
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_OVERLAP_BYTES = bytes.fromhex("88 57")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PREDECESSOR_TARGET_RVA = 0x0018267A
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_BRANCHES = (
    (0x00182697, 0x00182724),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_RET_RVAS = (
    0x00182679,
    0x00182684,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PADDING_RVA = 0x00182685
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PADDING_BYTES = bytes.fromhex(
    "cc cc cc cc cc cc cc cc cc cc cc"
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_NEXT_CODE_RVA = 0x00182690
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_INSTRUCTIONS = (
    (0x00182673, "88 57 02", "mov [edi+2], dl"),
    (0x00182676, "5b", "pop ebx"),
    (0x00182677, "5e", "pop esi"),
    (0x00182678, "5f", "pop edi"),
    (0x00182679, "c3", "ret"),
    (0x0018267A, "66 89 17", "mov [edi], dx"),
    (0x0018267D, "8b 44 24 10", "mov eax, [esp+0x10]"),
    (0x00182681, "5b", "pop ebx"),
    (0x00182682, "5e", "pop esi"),
    (0x00182683, "5f", "pop edi"),
    (0x00182684, "c3", "ret"),
    (0x00182685, "cc", "int3"),
    (0x00182686, "cc", "int3"),
    (0x00182687, "cc", "int3"),
    (0x00182688, "cc", "int3"),
    (0x00182689, "cc", "int3"),
    (0x0018268A, "cc", "int3"),
    (0x0018268B, "cc", "int3"),
    (0x0018268C, "cc", "int3"),
    (0x0018268D, "cc", "int3"),
    (0x0018268E, "cc", "int3"),
    (0x0018268F, "cc", "int3"),
    (0x00182690, "83 3d 20 bb 98 00 00", "cmp dword [0x98bb20], 0"),
    (0x00182697, "0f 84 87 00 00 00", "je 0x182724"),
    (0x0018269D, "83 ec 08", "sub esp, 8"),
    (0x001826A0, "0f ae 5c 24 04", "stmxcsr [esp+4]"),
    (0x001826A5, "8b 44 24 04", "mov eax, [esp+4]"),
    (0x001826A9, "25 80 1f 00 00", "and eax, 0x1f80"),
    (0x001826AE, "3d 80 1f 00 00", "cmp eax, 0x1f80"),
)


# R271/F13 next bounded window from exact 0x1826B3 boundary. The 64-byte
# capture ends two bytes into FNSTCW at 0x1826F1, so only the complete prefix is
# promoted and the d9 3c tail remains raw capture-edge evidence.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_RVA = 0x001826B3
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PROBE_END_RVA = 0x001826F3
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PREFIX_END_RVA = 0x001826F1
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INCOMPLETE_RVA = 0x001826F1
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INCOMPLETE_BYTES = bytes.fromhex("d9 3c")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_BRANCHES = (
    (0x001826B3, 0x001826C4),
    (0x001826C8, 0x00182724),
    (0x001826CA, 0x00188DE9),
    (0x001826D7, 0x0018270B),
    (0x001826EF, 0x00182700),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INSTRUCTIONS = (
    (0x001826B3, "75 0f", "jne 0x1826c4"),
    (0x001826B5, "d9 3c 24", "fnstcw [esp]"),
    (0x001826B8, "66 8b 04 24", "mov ax, [esp]"),
    (0x001826BC, "66 83 e0 7f", "and ax, 0x7f"),
    (0x001826C0, "66 83 f8 7f", "cmp ax, 0x7f"),
    (0x001826C4, "8d 64 24 08", "lea esp, [esp+8]"),
    (0x001826C8, "75 5a", "jne 0x182724"),
    (0x001826CA, "e9 1a 67 00 00", "jmp 0x188de9"),
    (0x001826CF, "90", "nop"),
    (0x001826D0, "83 3d 20 bb 98 00 00", "cmp dword [0x98bb20], 0"),
    (0x001826D7, "74 32", "je 0x18270b"),
    (0x001826D9, "83 ec 08", "sub esp, 8"),
    (0x001826DC, "0f ae 5c 24 04", "stmxcsr [esp+4]"),
    (0x001826E1, "8b 44 24 04", "mov eax, [esp+4]"),
    (0x001826E5, "25 80 1f 00 00", "and eax, 0x1f80"),
    (0x001826EA, "3d 80 1f 00 00", "cmp eax, 0x1f80"),
    (0x001826EF, "75 0f", "jne 0x182700"),
)


# R271/F13 overlap continuation at the cut FNSTCW. This window resolves prior
# external targets 0x182700/0x18270B/0x182724 and stops at the 0x9B start of a
# wait-prefixed FSTCW sequence. Preserve that final byte as capture-edge evidence.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_RVA = 0x001826F1
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PROBE_END_RVA = 0x00182731
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_OVERLAP_BYTES = bytes.fromhex("d9 3c")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PREFIX_END_RVA = 0x00182730
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INCOMPLETE_RVA = 0x00182730
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INCOMPLETE_BYTES = bytes.fromhex("9b")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PREDECESSOR_TARGET_RVAS = (
    0x00182700,
    0x0018270B,
    0x00182724,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_BRANCHES = (
    (0x00182704, 0x0018270B),
    (0x00182706, 0x00188DD0),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_CALLS = (
    (0x0018271B, 0x0018272D),
    (0x00182728, 0x00188905),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INSTRUCTIONS = (
    (0x001826F1, "d9 3c 24", "fnstcw [esp]"),
    (0x001826F4, "66 8b 04 24", "mov ax, [esp]"),
    (0x001826F8, "66 83 e0 7f", "and ax, 0x7f"),
    (0x001826FC, "66 83 f8 7f", "cmp ax, 0x7f"),
    (0x00182700, "8d 64 24 08", "lea esp, [esp+8]"),
    (0x00182704, "75 05", "jne 0x18270b"),
    (0x00182706, "e9 c5 66 00 00", "jmp 0x188dd0"),
    (0x0018270B, "83 ec 14", "sub esp, 0x14"),
    (0x0018270E, "d9 c9", "fxch st(1)"),
    (0x00182710, "dd 1c 24", "fstp qword [esp]"),
    (0x00182713, "dd 54 24 08", "fst qword [esp+8]"),
    (0x00182717, "8b 44 24 0c", "mov eax, [esp+0x0c]"),
    (0x0018271B, "e8 0d 00 00 00", "call 0x18272d"),
    (0x00182720, "83 c4 14", "add esp, 0x14"),
    (0x00182723, "c3", "ret"),
    (0x00182724, "8d 54 24 0c", "lea edx, [esp+0x0c]"),
    (0x00182728, "e8 d8 61 00 00", "call 0x188905"),
    (0x0018272D, "8b c8", "mov ecx, eax"),
    (0x0018272F, "50", "push eax"),
)


# R271/F13 continuation from the wait-prefix capture edge at 0x182730.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_RVA = 0x00182730
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PROBE_END_RVA = 0x00182770
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_OVERLAP_BYTES = bytes.fromhex("9b")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PREFIX_END_RVA = 0x0018276D
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INCOMPLETE_RVA = 0x0018276D
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INCOMPLETE_BYTES = bytes.fromhex("8a 4c 24")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_BRANCHES = (
    (0x0018273A, 0x00182741),
    (0x00182751, 0x001827F4),
    (0x0018275C, 0x001827F0),
    (0x00182767, 0x00182863),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_CALLS = (
    (0x0018273C, 0x001888D5),
    (0x00182757, 0x00188905),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INSTRUCTIONS = (
    (0x00182730, "9b d9 3c 24", "fstcw [esp]"),
    (0x00182734, "66 81 3c 24 7f 02", "cmp word [esp], 0x27f"),
    (0x0018273A, "74 05", "je 0x182741"),
    (0x0018273C, "e8 94 61 00 00", "call 0x1888d5"),
    (0x00182741, "81 e1 00 00 f0 7f", "and ecx, 0x7ff00000"),
    (0x00182747, "8d 54 24 08", "lea edx, [esp+8]"),
    (0x0018274B, "81 f9 00 00 f0 7f", "cmp ecx, 0x7ff00000"),
    (0x00182751, "0f 84 9d 00 00 00", "je 0x1827f4"),
    (0x00182757, "e8 a9 61 00 00", "call 0x188905"),
    (0x0018275C, "0f 84 8e 00 00 00", "je 0x1827f0"),
    (0x00182762, "a9 00 00 f0 7f", "test eax, 0x7ff00000"),
    (0x00182767, "0f 84 f6 00 00 00", "je 0x182863"),
)

# R271/F13 continuation from the cut MOV at 0x18276D. This window ends at the
# first byte of a near Jcc at 0x1827AC; that byte remains raw-only.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_RVA = 0x0018276D
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PROBE_END_RVA = 0x001827AD
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_OVERLAP_BYTES = bytes.fromhex("8a 4c 24")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PREFIX_END_RVA = 0x001827AC
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INCOMPLETE_RVA = 0x001827AC
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INCOMPLETE_BYTES = bytes.fromhex("0f")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_BRANCHES = (
    (0x00182774, 0x001828CD),
    (0x00182784, 0x00182788),
    (0x0018278F, 0x0018895E),
    (0x001827A0, 0x001889A9),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_CALLS = (
    (0x0018277C, 0x001888C0),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INSTRUCTIONS = (
    (0x0018276D, "8a 4c 24 0f", "mov cl, [esp+0x0f]"),
    (0x00182771, "80 e1 80", "and cl, 0x80"),
    (0x00182774, "0f 85 53 01 00 00", "jne 0x1828cd"),
    (0x0018277A, "d9 f1", "fyl2x"),
    (0x0018277C, "e8 3f 61 00 00", "call 0x1888c0"),
    (0x00182781, "80 f9 01", "cmp cl, 1"),
    (0x00182784, "75 02", "jne 0x182788"),
    (0x00182786, "d9 e0", "fchs"),
    (0x00182788, "83 3d 64 fa 85 00 00", "cmp dword [0x85fa64], 0"),
    (0x0018278F, "0f 85 c9 61 00 00", "jne 0x18895e"),
    (0x00182795, "8d 0d f8 59 73 00", "lea ecx, [0x7359f8]"),
    (0x0018279B, "ba 1d 00 00 00", "mov edx, 0x1d"),
    (0x001827A0, "e9 04 62 00 00", "jmp 0x1889a9"),
    (0x001827A5, "83 3d 64 fa 85 00 00", "cmp dword [0x85fa64], 0"),
)


# R278/F13: extend raw canonical-EXE provenance from the cut near-Jcc opcode
# at 0x1827AC. The predecessor proves only the first 0x0F byte at this capture
# edge, so overlap that byte and collect a fresh 64-byte window. This stage
# intentionally does not decode the near branch or promote function/callee,
# render/HUD ownership, or runtime semantics.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_RVA = 0x001827AC
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PROBE_END_RVA = 0x001827EC
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INCOMPLETE_BYTES
)

GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PREFIX_END_RVA = 0x001827E9
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INCOMPLETE_RVA = 0x001827E9
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INCOMPLETE_BYTES = bytes.fromhex("b8 07 00")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_BRANCHES = (
    (0x001827AC, 0x0018895E),
    (0x001827D2, 0x001827D7),
    (0x001827D5, 0x0018280A),
    (0x001827DE, 0x001827A5),
    (0x001827E5, 0x001827D7),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_CALLS = (
    (0x001827BD, 0x00188860),
    (0x001827C8, 0x00188905),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PREDECESSOR_TARGET_BYTES = (
    (0x001827A5, bytes.fromhex("83 3d 64 fa 85 00 00")),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INSTRUCTIONS = (
    (0x001827AC, "0f 85 ac 61 00 00", "jne 0x18895e"),
    (0x001827B2, "8d 0d f8 59 73 00", "lea ecx, [0x7359f8]"),
    (0x001827B8, "ba 1d 00 00 00", "mov edx, 0x1d"),
    (0x001827BD, "e8 9e 60 00 00", "call 0x188860"),
    (0x001827C2, "5a", "pop edx"),
    (0x001827C3, "c3", "ret"),
    (0x001827C4, "8d 54 24 08", "lea edx, [esp+8]"),
    (0x001827C8, "e8 38 61 00 00", "call 0x188905"),
    (0x001827CD, "f6 44 24 16 08", "test byte [esp+0x16], 8"),
    (0x001827D2, "75 03", "jne 0x1827d7"),
    (0x001827D4, "41", "inc ecx"),
    (0x001827D5, "eb 33", "jmp 0x18280a"),
    (0x001827D7, "de c1", "faddp st(1), st"),
    (0x001827D9, "b8 01 00 00 00", "mov eax, 1"),
    (0x001827DE, "eb c5", "jmp 0x1827a5"),
    (0x001827E0, "f6 44 24 0e 08", "test byte [esp+0x0e], 8"),
    (0x001827E5, "75 f0", "jne 0x1827d7"),
    (0x001827E7, "de c1", "faddp st(1), st"),
)


# CONV-DXVK-000002/F13: continue from the incomplete MOV EAX,imm32 at
# 0x1827E9. Capture a fresh bounded canonical-EXE window before decoding or
# assigning function/render/HUD/runtime semantics. The predecessor overlap is
# mandatory so stale or mismatched binaries fail closed.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_RVA = 0x001827E9
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PROBE_END_RVA = 0x00182829
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INCOMPLETE_BYTES
)

# CONV-DXVK-000002/F13: exact-decode the complete instruction prefix exposed by
# the canonical 0x1827E9 window. The final 0x85 byte is only an incomplete TEST
# opcode at the capture edge, so keep it raw and force the next continuation to
# overlap from 0x182828 rather than guessing its ModRM or semantics.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PREFIX_END_RVA = 0x00182828
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INCOMPLETE_RVA = 0x00182828
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INCOMPLETE_BYTES = bytes.fromhex("85")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_BRANCHES = (
    (0x001827EE, 0x001827A5),
    (0x001827F2, 0x0018280A),
    (0x001827FF, 0x001827C4),
    (0x00182820, 0x00182828),
    (0x00182826, 0x001827E0),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_CALLS = (
    (0x00182805, 0x00188905),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PREDECESSOR_TARGET_BYTES = (
    (0x001827A5, bytes.fromhex("83 3d 64 fa 85 00 00")),
    (0x001827C4, bytes.fromhex("8d 54 24 08")),
    (0x001827E0, bytes.fromhex("f6 44 24 0e 08")),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INSTRUCTIONS = (
    (0x001827E9, "b8 07 00 00 00", "mov eax, 7"),
    (0x001827EE, "eb b5", "jmp 0x1827a5"),
    (0x001827F0, "33 c9", "xor ecx, ecx"),
    (0x001827F2, "eb 16", "jmp 0x18280a"),
    (0x001827F4, "33 c9", "xor ecx, ecx"),
    (0x001827F6, "25 ff ff 0f 00", "and eax, 0x000fffff"),
    (0x001827FB, "0b 44 24 10", "or eax, [esp+0x10]"),
    (0x001827FF, "75 c3", "jne 0x1827c4"),
    (0x00182801, "8d 54 24 08", "lea edx, [esp+8]"),
    (0x00182805, "e8 fb 60 00 00", "call 0x188905"),
    (0x0018280A, "8b 44 24 0c", "mov eax, [esp+0x0c]"),
    (0x0018280E, "8b d0", "mov edx, eax"),
    (0x00182810, "25 00 00 f0 7f", "and eax, 0x7ff00000"),
    (0x00182815, "81 e2 ff ff 0f 00", "and edx, 0x000fffff"),
    (0x0018281B, "3d 00 00 f0 7f", "cmp eax, 0x7ff00000"),
    (0x00182820, "75 06", "jne 0x182828"),
    (0x00182822, "0b 54 24 08", "or edx, [esp+8]"),
    (0x00182826, "75 b8", "jne 0x1827e0"),
)



# CONV-DXVK-000002/F14: overlap the cut TEST opcode at 0x182828 and capture a
# fresh canonical-EXE window. This stage is provenance-only: it deliberately
# does not decode the TEST ModRM or assign function/render/HUD/runtime meaning
# until the new bytes have been observed and checked on the canonical image.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_RVA = 0x00182828
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PROBE_END_RVA = 0x00182868
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INCOMPLETE_BYTES
)

# CONV-DXVK-000002/F14: exact-decode only the complete instruction prefix from
# the canonical 0x182828 window. The final 0x25 byte begins AND EAX,imm32 but
# its immediate is outside this capture, so keep it raw and require overlap in
# the next continuation rather than guessing bytes or semantics.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PREFIX_END_RVA = 0x00182867
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INCOMPLETE_RVA = 0x00182867
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INCOMPLETE_BYTES = bytes.fromhex("25")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_BRANCHES = (
    (0x0018282A, 0x001827E7),
    (0x00182853, 0x0018895E),
    (0x0018285E, 0x001827A5),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_CALLS = (
    (0x00182840, 0x00189B95),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PREDECESSOR_TARGET_BYTES = (
    (0x001827A5, bytes.fromhex("83 3d 64 fa 85 00 00")),
    (0x001827E7, bytes.fromhex("de c1")),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INSTRUCTIONS = (
    (0x00182828, "85 c9", "test ecx, ecx"),
    (0x0018282A, "75 bb", "jne 0x1827e7"),
    (0x0018282C, "83 ec 74", "sub esp, 0x74"),
    (0x0018282F, "8b cc", "mov ecx, esp"),
    (0x00182831, "51", "push ecx"),
    (0x00182832, "83 ec 10", "sub esp, 0x10"),
    (0x00182835, "dd 1c 24", "fstp qword [esp]"),
    (0x00182838, "dd 5c 24 08", "fstp qword [esp+0x8]"),
    (0x0018283C, "9b dd 71 08", "fsave [ecx+0x8]"),
    (0x00182840, "e8 50 73 00 00", "call 0x189b95"),
    (0x00182845, "83 c4 10", "add esp, 0x10"),
    (0x00182848, "59", "pop ecx"),
    (0x00182849, "dd 61 08", "frstor [ecx+0x8]"),
    (0x0018284C, "dd 01", "fld qword [ecx]"),
    (0x0018284E, "83 c4 74", "add esp, 0x74"),
    (0x00182851, "85 c0", "test eax, eax"),
    (0x00182853, "0f 84 05 61 00 00", "je 0x18895e"),
    (0x00182859, "b8 01 00 00 00", "mov eax, 1"),
    (0x0018285E, "e9 42 ff ff ff", "jmp 0x1827a5"),
    (0x00182863, "8b 44 24 0c", "mov eax, [esp+0x0c]"),
)


# CONV-DXVK-000002/F15: overlap the cut AND EAX,imm32 opcode at 0x182867
# and capture a fresh bounded canonical-EXE window. Keep this stage
# provenance-only until the newly exposed bytes are validated and decoded.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_RVA = 0x00182867
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PROBE_END_RVA = 0x001828A7
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_OVERLAP_BYTES = (
    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INCOMPLETE_BYTES
)

# CONV-DXVK-000002/F15: exact-decode the full canonical 0x182867 window.
# The 64-byte capture ends exactly on an instruction boundary at 0x1828A7;
# branch/call targets outside the capture remain address-only evidence.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PREFIX_END_RVA = 0x001828A7
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_BRANCHES = (
    (0x00182870, 0x0018276D),
    (0x00182885, 0x001828C4),
    (0x0018289B, 0x001828B3),
    (0x001828A5, 0x001828A9),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_CALLS = (
    (0x00182887, 0x001828F2),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PREDECESSOR_TARGET_BYTES = (
    (0x0018276D, bytes.fromhex("8a 4c 24 0f")),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_INSTRUCTIONS = (
    (0x00182867, "25 ff ff 0f 00", "and eax, 0x000fffff"),
    (0x0018286C, "0b 44 24 08", "or eax, [esp+0x8]"),
    (0x00182870, "0f 85 f7 fe ff ff", "jne 0x18276d"),
    (0x00182876, "dd d8", "fstp st(0)"),
    (0x00182878, "8b 44 24 14", "mov eax, [esp+0x14]"),
    (0x0018287C, "25 ff ff ff 7f", "and eax, 0x7fffffff"),
    (0x00182881, "0b 44 24 10", "or eax, [esp+0x10]"),
    (0x00182885, "74 3d", "je 0x1828c4"),
    (0x00182887, "e8 66 00 00 00", "call 0x1828f2"),
    (0x0018288C, "8a 6c 24 0f", "mov ch, byte [esp+0x0f]"),
    (0x00182890, "c0 ed 07", "shr ch, 7"),
    (0x00182893, "f7 44 24 17 80 00 00 00", "test dword [esp+0x17], 0x80"),
    (0x0018289B, "74 16", "je 0x1828b3"),
    (0x0018289D, "db 2d 20 61 73 00", "fld tbyte [0x736120]"),
    (0x001828A3, "84 cd", "test ch, cl"),
    (0x001828A5, "74 02", "je 0x1828a9"),
)


# CONV-DXVK-000002/F16: the F15 exact proof ends on a verified instruction
# boundary at 0x1828A7. Capture the next bounded canonical window without
# assuming function/render/HUD/runtime semantics; decode is a separate step.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_RVA = 0x001828A7
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PROBE_LEN = 64
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PROBE_END_RVA = 0x001828E7

# CONV-DXVK-000002/F16: exact-decode only complete instructions from the
# canonical 0x1828A7 capture. The trailing five bytes start FLD tbyte [disp32]
# but the final displacement byte is outside this window, so preserve them as
# raw capture-edge evidence and require a future overlapping continuation.
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PREFIX_END_RVA = 0x001828E2
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INCOMPLETE_RVA = 0x001828E2
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INCOMPLETE_BYTES = bytes.fromhex("db 2d f0 60 73")
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_BRANCHES = (
    (0x001828AE, 0x001827A5),
    (0x001828B7, 0x0018895E),
    (0x001828BF, 0x0018895E),
    (0x001828C8, 0x0018895E),
    (0x001828D8, 0x0018277A),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_CALLS = (
    (0x001828CF, 0x001828F2),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PREDECESSOR_TARGET_BYTES = (
    (0x001827A5, bytes.fromhex("83 3d 64 fa 85 00 00")),
    (0x0018277A, bytes.fromhex("d9 f1")),
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_RESOLVED_FORWARD_TARGET_RVAS = (
    0x001828A9,
    0x001828B3,
    0x001828C4,
    0x001828CD,
)
GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INSTRUCTIONS = (
    (0x001828A7, "d9 e0", "fchs"),
    (0x001828A9, "b8 02 00 00 00", "mov eax, 2"),
    (0x001828AE, "e9 f2 fe ff ff", "jmp 0x1827a5"),
    (0x001828B3, "d9 ee", "fldz"),
    (0x001828B5, "84 cd", "test ch, cl"),
    (0x001828B7, "0f 84 a1 60 00 00", "je 0x18895e"),
    (0x001828BD, "d9 e0", "fchs"),
    (0x001828BF, "e9 9a 60 00 00", "jmp 0x18895e"),
    (0x001828C4, "dd d8", "fstp st(0)"),
    (0x001828C6, "d9 e8", "fld1"),
    (0x001828C8, "e9 91 60 00 00", "jmp 0x18895e"),
    (0x001828CD, "d9 c1", "fld st(1)"),
    (0x001828CF, "e8 1e 00 00 00", "call 0x1828f2"),
    (0x001828D4, "d9 e0", "fchs"),
    (0x001828D6, "84 c9", "test cl, cl"),
    (0x001828D8, "0f 85 9c fe ff ff", "jne 0x18277a"),
    (0x001828DE, "dd d8", "fstp st(0)"),
    (0x001828E0, "dd d8", "fstp st(0)"),
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


# Mirrors the canonical producer catalog in
# src/vr/game/disasm_render_contract.hpp. Keep this Python representation
# mechanically checked by tools/verify_vr_semantic_catalog.py.
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
    """Return the nearest known prologue in the bounded backward window.

    Use bytes.rfind so the hot inbound-rel32 census does not execute a Python
    loop for every byte of every candidate.  The search bounds preserve the
    prior startswith semantics, including accepting a prologue whose first byte
    is exactly at *index*.
    """

    lo = max(0, index - 0x500)
    prologues = (b"\x55\x8b\xec", b"\x53\x56\x57", b"\x56\x8b\xf1")
    nearest = -1
    for prologue in prologues:
        hi = min(len(text), index + len(prologue))
        pos = text.rfind(prologue, lo, hi)
        if pos > nearest and pos <= index:
            nearest = pos
    return text_rva + nearest if nearest >= 0 else None


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


def _raw_inbound_rel32_offset_index(pe: PE) -> dict[int, list[int]]:
    """Index raw .text E8 rel32 candidates once per PE instance.

    The analyzer asks for inbound candidates at many nearby targets. Re-scanning
    the complete .text section for every target is quadratic in review breadth,
    so cache only byte offsets keyed by decoded target. Semantic classification
    and function-start guesses remain query-local to preserve existing output.
    """

    cached = getattr(pe, "_raw_inbound_rel32_offsets_by_target", None)
    if cached is not None:
        return cached

    text_section = pe.section(".text")
    offsets_by_target: dict[int, list[int]] = {}
    if text_section:
        text = pe.data[
            text_section.raw_pointer :
            text_section.raw_pointer + text_section.raw_size
        ]
        for i in range(0, max(0, len(text) - 5)):
            if text[i] != 0xE8:
                continue
            rel = struct.unpack_from("<i", text, i + 1)[0]
            call_rva = text_section.virtual_address + i
            decoded_target_rva = (call_rva + 5 + rel) & 0xFFFFFFFF
            offsets_by_target.setdefault(decoded_target_rva, []).append(i)

    setattr(pe, "_raw_inbound_rel32_offsets_by_target", offsets_by_target)
    return offsets_by_target


def collect_raw_inbound_rel32_candidates(pe: PE, target_rva: int) -> list[dict]:
    """Find raw .text E8 rel32 byte candidates that decode to target_rva.

    This uses a cached byte-level offset index, not decoded instructions.
    Results are provenance leads, not proof that an E8 byte is an
    instruction-aligned CALL.
    """

    text_section = pe.section(".text")
    if not text_section:
        return []

    text = pe.data[
        text_section.raw_pointer :
        text_section.raw_pointer + text_section.raw_size
    ]
    out: list[dict] = []
    for i in _raw_inbound_rel32_offset_index(pe).get(target_rva, ()):
        call_rva = text_section.virtual_address + i
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
                "bytes96": pe.bytes_at_rva(target_rva, GF_RAW_REL32_TARGET_WINDOW).hex(" "),
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


def collect_guarded_gf_target_c_helper_1_provenance(pe: PE) -> dict:
    """Collect bounded raw provenance for target-C helper 0x28460.

    The byte window and rel32 candidate census are evidence only. They do not
    prove instruction alignment, semantic effect, or render ownership.
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


def collect_guarded_gf_target_c_helper_1_first_callee_provenance(pe: PE) -> dict:
    """Capture bounded raw provenance for helper 0x28460's first proven callee.

    The preceding success-prefix proof already establishes the aligned
    0x284BC -> 0x282B0 edge. This collector adds exact-EXE bytes plus raw
    inbound/outbound rel32 candidates for 0x282B0 without inferring callee
    semantics or render ownership.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_success_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_FIRST_CALLEE_RVA
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
        target_rva, GF_TARGET_C_HELPER_1_FIRST_CALLEE_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_FIRST_CALLEE_PROBE_LEN
    )
    caller_link_present = any(
        item["call_rva"] == GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_RVA
        for item in inbound
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_SUCCESS_CALL_CHAIN_PREFIX_PROVEN"
        and predecessor["first_call_target_rva"] == target_rva
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and caller_link_present
        and len(probe) == GF_TARGET_C_HELPER_1_FIRST_CALLEE_PROBE_LEN
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "function_start_guess_rva": function_start_guess_rva,
        "probe_len": GF_TARGET_C_HELPER_1_FIRST_CALLEE_PROBE_LEN,
        "bytes": probe.hex(" "),
        "predecessor_status": predecessor["status"],
        "caller_rva": GF_TARGET_C_HELPER_1_SUCCESS_FIRST_CALL_RVA,
        "caller_link_present": caller_link_present,
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_FIRST_CALLEE_PROVENANCE_CAPTURED"
            if captured
            else "FIRST_CALLEE_PROVENANCE_CAPTURE_FAILED"
        ),
        "semantic_effect": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_prefix_proof(pe: PE) -> dict:
    """Prove the bounded packed-selector lookup prefix at helper 0x28460.

    This proof stops at the first successful continuation (0x284B0). It proves
    selector splitting, range guards, table lookup, and the local miss return,
    but does not infer the helper's full semantic effect or render ownership.
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
        caller_proof["status"] == "EXACT_FIRST_CALL_ALIGNMENT_PROVEN"
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
    """Prove the instruction-aligned 0x282B0..0x28309 callee prefix.

    The bounded proof establishes the exact table/base/stride immediates, the
    >=64 failure return, the 64-entry cursor wrap, the occupied-slot retry edge,
    and the first slot mark/output-pointer store. It deliberately stops before
    the next instruction and does not infer HUD/render ownership.
    """

    provenance = collect_guarded_gf_target_c_helper_1_first_callee_provenance(pe)
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
        provenance["status"] == "EXACT_EXE_FIRST_CALLEE_PROVENANCE_CAPTURED"
        and provenance["caller_link_present"]
        and provenance["target_section"] == ".text"
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
        "predecessor_status": provenance["status"],
        "caller_rva": provenance["caller_rva"],
        "caller_link_present": provenance["caller_link_present"],
        "target_section": provenance["target_section"],
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


def collect_guarded_gf_target_c_helper_1_first_callee_continuation_provenance(pe: PE) -> dict:
    """Capture a fresh exact-EXE window beginning at the proven 0x2830A boundary.

    R149 proves complete instructions through 0x28309. This collector starts at
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


def collect_guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof(pe: PE) -> dict:
    """Prove the exact terminal sequence, INT3 padding, and next-code anchor.

    The fresh R151 continuation capture starts exactly at 0x2830A. This proof
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
    """Capture exact provenance for code beginning at the R153 0x28320 anchor.

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

    R155 captured the exact 96-byte window. This proof pins every complete
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

    R157 proves complete instructions only through 0x2837D. This collector starts
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

    The R159 96-byte capture ends exactly at 0x283DE. This proof pins every
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

    R161 proves every instruction through 0x283DD. This collector starts exactly
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
    """Prove the complete 0x283DE..0x2843D terminal/data-write window.

    R163 captured an exact 96-byte window that ends on RET. This proof pins every
    instruction byte and verifies that the previously proven 0x28433 fail edge
    lands on the shared epilogue entry. Data meaning and render ownership remain
    unresolved.
    """

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


def collect_guarded_gf_target_c_helper_1_next_code_function_boundary_proof(pe: PE) -> dict:
    """Prove 0x28320 as an exact structural function-entry boundary.

    This combines four already independent proofs: an instruction-aligned external
    CALL resolving to 0x28320, exact INT3 padding immediately before 0x28320,
    contiguous exact instruction coverage from 0x28320 through 0x2843D, and the
    terminal RET/shared epilogue. Only boundary identity is promoted.
    """

    caller = collect_guarded_gf_target_c_second_call_alignment_proof(pe)
    padding = collect_guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof(pe)
    prefix = collect_guarded_gf_target_c_helper_1_next_code_prefix_proof(pe)
    continuation = collect_guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof(pe)
    terminal = collect_guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof(pe)

    entry_rva = GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_ENTRY_RVA
    end_rva = GF_TARGET_C_HELPER_1_NEXT_CODE_FUNCTION_END_RVA

    external_call_link = bool(
        caller["status"] == "EXACT_SECOND_CALL_ALIGNMENT_PROVEN"
        and caller["call_is_layout_boundary"]
        and caller["call_target_matches"]
        and caller["call_target_section_matches"]
        and caller["decoded_call_target_rva"] == entry_rva
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
        and prefix["prefix_end_rva"]
        == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA
        and continuation["status"] == "EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN"
        and continuation["target_rva"]
        == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_RVA
        and continuation["end_rva"]
        == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA
        and terminal["status"] == "EXACT_NEXT_CODE_CONTINUATION_2_TERMINAL_PROVEN"
        and terminal["target_rva"]
        == GF_TARGET_C_HELPER_1_NEXT_CODE_CONTINUATION_2_RVA
        and terminal["end_rva"] == end_rva
        and terminal["terminal_ret_rva"] == end_rva - 1
        and terminal["terminal_ret_matches"]
    )
    text_boundary = bool(
        caller["call_target_section"] == ".text"
        and prefix["target_section"] == ".text"
        and continuation["target_section"] == ".text"
        and terminal["target_section"] == ".text"
    )
    proven = bool(
        external_call_link
        and padding_boundary
        and body_chain
        and text_boundary
    )
    return {
        "entry_rva": entry_rva,
        "end_rva": end_rva,
        "external_call_rva": caller["aligned_call_rva"],
        "external_call_target_rva": caller["decoded_call_target_rva"],
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

    The R169 provenance step established two independently aligned callers and
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
    """Prove the complete instruction prefix inside the R173 0x182194 probe.

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

    R175 proves that 0x1821F3 is the next instruction boundary and that the
    previous 96-byte probe exposes only its leading 0x8B opcode. This collector
    overlaps that byte, requires the R175 proof, captures 96 fresh bytes, and
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
    """Prove the complete instruction prefix inside the R177 0x1821F3 window.

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
    """Capture fresh exact-EXE bytes from the R179 0x182251 boundary.

    R179 proves that the preceding continuation is exact through 0x182250 and
    exposes only bytes 83 e0 for the next incomplete instruction at 0x182251.
    This collector overlaps those bytes, requires the R179 proof, captures a
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
    """Prove the exact instruction/control-flow layout of the R181 window.

    The proof decodes every byte in the 128-byte 0x182251 window, validates the
    incoming forward targets established by R179, all local rel8 branches, and
    the exact 0x18229B -> 0x1882CC rel32 call. It stops after the complete leave
    instruction at 0x1822D0 because the following byte was not captured by R181.
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



def collect_guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance(pe: PE) -> dict:
    """Capture exact bytes immediately after the R183 0x1822D0 leave.

    The predecessor proof must consume its entire 128-byte window through the
    leave at 0x1822D0 and end exactly at 0x1822D1. This collector then captures
    96 fresh bytes and raw rel32 candidates. The first byte is surfaced only as
    raw evidence; ret/function-boundary, callee, and render/HUD semantics remain
    unresolved until a separate instruction-boundary proof reviews these bytes.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_LEN,
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_182251_CONTINUATION_CONTROL_FLOW_PROVEN"
        and predecessor["prefix_end_rva"] == target_rva
        and predecessor["probe_end_rva"] == target_rva
        and predecessor["leave_rva"] == target_rva - 1
        and predecessor["leave_matches"]
        and predecessor["terminal_status"] == "LEAVE_PROVEN_RET_NOT_CAPTURED"
        and predecessor["continuation_status"] == "NEXT_BYTE_AFTER_LEAVE_NOT_CAPTURED"
        and predecessor["target_section"] == ".text"
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_LEN
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "predecessor_leave_rva": predecessor["leave_rva"],
        "predecessor_leave_bytes": predecessor["leave_bytes"],
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "first_byte": probe[:1].hex(" "),
        "first_16_bytes": probe[:16].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1822D1_CONTINUATION_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1822D1_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "function_entry_status": "UNRESOLVED",
        "terminal_status": "UNRESOLVED_RAW_FIRST_BYTE_ONLY",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_AND_REL32_CENSUS_ONLY",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof(pe: PE) -> dict:
    """Prove the exact leave;ret terminal and immediate next instruction start.

    R183 proved a complete leave at 0x1822D0 but stopped before the following
    byte. R185 then captured raw c3 at 0x1822D1 and a raw rel32 candidate at
    0x1822D2. This proof combines only those exact bytes: c9 c3 is established
    as a leave;ret terminal, and the five-byte E8 instruction at 0x1822D2 is
    decoded to target 0x185BEC. The 0x1822D2 address remains an instruction
    boundary only; function-entry identity and all higher-level semantics stay
    unresolved.
    """

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance(pe)
    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof(pe)

    terminal_bytes = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_LEAVE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_BYTES),
    )
    terminal_matches = (
        terminal_bytes == GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_BYTES
    )
    ret_matches_provenance = (
        provenance["first_byte"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_BYTES[1:].hex(" ")
    )

    next_bytes = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_BYTES),
    )
    next_instruction_matches = (
        next_bytes == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_BYTES
    )
    decoded_call_target_rva = None
    if len(next_bytes) == 5 and next_bytes[0] == 0xE8:
        rel = struct.unpack_from("<i", next_bytes, 1)[0]
        decoded_call_target_rva = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA + 5 + rel
        ) & 0xFFFFFFFF
    call_target_matches = (
        decoded_call_target_rva
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_CALL_TARGET_RVA
    )
    raw_call_candidate_present = any(
        item["call_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA
        and item["target_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_CALL_TARGET_RVA
        for item in provenance["raw_outbound_rel32_candidates"]
    )

    predecessor_exact = (
        predecessor["status"] == "EXACT_182251_CONTINUATION_CONTROL_FLOW_PROVEN"
        and predecessor["leave_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_LEAVE_RVA
        and predecessor["leave_matches"]
        and predecessor["prefix_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_RET_RVA
        and predecessor["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_RET_RVA
    )
    provenance_exact = (
        provenance["status"] == "EXACT_EXE_1822D1_CONTINUATION_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["target_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_RET_RVA
        and provenance["target_section"] == ".text"
        and provenance["probe_end_matches"]
    )
    next_boundary_contiguous = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_RET_RVA + 1
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA
    )

    proven = bool(
        predecessor_exact
        and provenance_exact
        and terminal_matches
        and ret_matches_provenance
        and next_boundary_contiguous
        and next_instruction_matches
        and call_target_matches
        and raw_call_candidate_present
    )
    return {
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "provenance_status": provenance["status"],
        "provenance_exact": provenance_exact,
        "terminal_leave_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_LEAVE_RVA,
        "terminal_ret_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_RET_RVA,
        "terminal_expected_bytes": GF_TARGET_C_HELPER_1_THIRD_CALLEE_TERMINAL_BYTES.hex(" "),
        "terminal_actual_bytes": terminal_bytes.hex(" "),
        "terminal_matches": terminal_matches,
        "ret_matches_provenance": ret_matches_provenance,
        "next_instruction_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA,
        "next_instruction_expected_bytes": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_BYTES.hex(" "),
        "next_instruction_actual_bytes": next_bytes.hex(" "),
        "next_instruction_matches": next_instruction_matches,
        "next_boundary_contiguous": next_boundary_contiguous,
        "decoded_call_target_rva": decoded_call_target_rva,
        "expected_call_target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_CALL_TARGET_RVA,
        "call_target_matches": call_target_matches,
        "raw_call_candidate_present": raw_call_candidate_present,
        "status": (
            "EXACT_1822D0_LEAVE_RET_AND_1822D2_NEXT_INSTRUCTION_PROVEN"
            if proven
            else "CALLEE_1822D0_TERMINAL_BOUNDARY_PROOF_FAILED"
        ),
        "terminal_status": "EXACT_LEAVE_RET_PROVEN",
        "next_boundary_status": "EXACT_NEXT_INSTRUCTION_START_PROVEN",
        "function_entry_status": "UNRESOLVED_AT_1822D2",
        "semantic_effect": "TERMINAL_AND_NEXT_INSTRUCTION_BOUNDARY_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof(pe: PE) -> dict:
    """Prove the exact 0x1822D2 code sequence, ret, padding and next boundary.

    R187 proves 0x1822D2 is the immediate instruction start after the prior
    leave;ret terminal. This proof decodes every exact byte from 0x1822D2
    through the ret at 0x1822F3, validates the local branch and three rel32
    call targets against the R185 raw census, then requires twelve 0xCC bytes
    through 0x1822FF. The next byte at 0x182300 is therefore a code boundary
    only; function-entry and semantic ownership remain unresolved.
    """

    terminal = collect_guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof(pe)
    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance(pe)

    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_INSTRUCTIONS:
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
    branch_targets_are_instruction_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_BRANCHES:
        decoded_target_rva = rel8_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        boundary = decoded_target_rva in instruction_starts
        branch_rows.append(
            {
                "branch_rva": branch_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "target_is_instruction_boundary": boundary,
                "matches": matches,
            }
        )
        branch_targets_match = branch_targets_match and matches
        branch_targets_are_instruction_boundaries = (
            branch_targets_are_instruction_boundaries and boundary
        )

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_CALLS:
        decoded_target_rva = rel32_call_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(
            item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva
            for item in provenance["raw_outbound_rel32_candidates"]
        )
        call_rows.append(
            {
                "call_rva": call_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "raw_candidate_present": raw_present,
            }
        )
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present

    padding = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_RVA,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_LEN,
    )
    expected_padding = bytes([0xCC]) * GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_LEN
    padding_matches = padding == expected_padding
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PREFIX_END_RVA
    )
    padding_end_rva = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_RVA
        + len(padding)
    )
    next_code_boundary_matches = (
        padding_end_rva == GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_NEXT_CODE_RVA
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    ret_matches = (
        pe.bytes_at_rva(GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_RET_RVA, 1)
        == b"\xC3"
    )
    predecessor_exact = (
        terminal["status"] == "EXACT_1822D0_LEAVE_RET_AND_1822D2_NEXT_INSTRUCTION_PROVEN"
        and terminal["next_instruction_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA
        and terminal["next_instruction_matches"]
        and terminal["next_boundary_contiguous"]
    )
    provenance_exact = (
        provenance["status"] == "EXACT_EXE_1822D1_CONTINUATION_PROVENANCE_CAPTURED"
        and provenance["target_section"] == ".text"
        and provenance["probe_end_matches"]
    )
    proven = bool(
        predecessor_exact
        and provenance_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and ret_matches
        and branch_targets_match
        and branch_targets_are_instruction_boundaries
        and call_targets_match
        and raw_call_candidates_present
        and padding_matches
        and next_code_boundary_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_INSTRUCTION_RVA,
        "target_section": provenance["target_section"],
        "predecessor_status": terminal["status"],
        "predecessor_exact": predecessor_exact,
        "provenance_status": provenance["status"],
        "provenance_exact": provenance_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PREFIX_END_RVA,
        "prefix_end_matches": prefix_end_matches,
        "ret_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_RET_RVA,
        "ret_matches": ret_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "branch_targets_are_instruction_boundaries": branch_targets_are_instruction_boundaries,
        "calls": call_rows,
        "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "padding_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_RVA,
        "padding_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_PADDING_LEN,
        "padding_bytes": padding.hex(" "),
        "padding_matches": padding_matches,
        "padding_end_rva": padding_end_rva,
        "next_code_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_POST_TERMINAL_NEXT_CODE_RVA,
        "next_code_boundary_matches": next_code_boundary_matches,
        "status": (
            "EXACT_1822D2_SEQUENCE_RET_PADDING_NEXT_BOUNDARY_PROVEN"
            if proven
            else "CALLEE_1822D2_SEQUENCE_BOUNDARY_PROOF_FAILED"
        ),
        "terminal_status": "EXACT_RET_AT_1822F3_PROVEN",
        "padding_status": "EXACT_12_BYTE_INT3_PADDING_PROVEN",
        "next_boundary_status": "EXACT_182300_CODE_BOUNDARY_PROVEN",
        "function_entry_status": "UNRESOLVED_AT_1822D2_AND_182300",
        "semantic_effect": "BOUNDED_SEQUENCE_CONTROL_FLOW_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof(pe: PE) -> dict:
    """Prove the exact 0x182300 sequence through its immediate ret.

    R189 proves 0x182300 is the next code boundary after the 0x1822D2
    sequence and twelve-byte INT3 padding. This proof decodes only the six
    exact instructions through ret 0x182313 and validates the two rel32 call
    targets against the R185 raw census. The following 0x182314 address is an
    instruction boundary only; function-entry and semantic ownership remain
    unresolved.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof(pe)
    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance(pe)

    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_START_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INSTRUCTIONS:
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

    def rel32_call_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) != 5 or raw[0] != 0xE8:
            return None
        rel = struct.unpack_from("<i", raw, 1)[0]
        return (rva + 5 + rel) & 0xFFFFFFFF

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CALLS:
        decoded_target_rva = rel32_call_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(
            item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva
            for item in provenance["raw_outbound_rel32_candidates"]
        )
        call_rows.append(
            {
                "call_rva": call_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "raw_candidate_present": raw_present,
            }
        )
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present

    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_PREFIX_END_RVA
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_NEXT_INSTRUCTION_RVA
    )
    ret_matches = (
        pe.bytes_at_rva(GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_RET_RVA, 1)
        == b"\xC3"
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_1822D2_SEQUENCE_RET_PADDING_NEXT_BOUNDARY_PROVEN"
        and predecessor["next_code_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_START_RVA
        and predecessor["next_code_boundary_matches"]
        and predecessor["padding_matches"]
    )
    provenance_exact = (
        provenance["status"] == "EXACT_EXE_1822D1_CONTINUATION_PROVENANCE_CAPTURED"
        and provenance["target_section"] == ".text"
        and provenance["probe_end_matches"]
        and provenance["probe_end_rva"] >= GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_PREFIX_END_RVA
    )
    proven = bool(
        predecessor_exact
        and provenance_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and ret_matches
        and call_targets_match
        and raw_call_candidates_present
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_START_RVA,
        "target_section": provenance["target_section"],
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "provenance_status": provenance["status"],
        "provenance_exact": provenance_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_PREFIX_END_RVA,
        "prefix_end_matches": prefix_end_matches,
        "ret_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_RET_RVA,
        "ret_matches": ret_matches,
        "calls": call_rows,
        "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "next_instruction_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_NEXT_INSTRUCTION_RVA,
        "next_instruction_boundary_matches": prefix_end_matches,
        "status": (
            "EXACT_182300_SEQUENCE_RET_NEXT_BOUNDARY_PROVEN"
            if proven
            else "CALLEE_182300_SEQUENCE_BOUNDARY_PROOF_FAILED"
        ),
        "terminal_status": "EXACT_RET_AT_182313_PROVEN",
        "next_boundary_status": "EXACT_182314_INSTRUCTION_BOUNDARY_PROVEN",
        "function_entry_status": "UNRESOLVED_AT_182300_182314_AND_18231D",
        "semantic_effect": "BOUNDED_SEQUENCE_AND_CALL_TARGETS_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof(pe: PE) -> dict:
    """Prove the exact remainder of the R185 continuation window.

    R191 proves 0x182314 is the immediate instruction boundary after ret
    0x182313. This proof consumes every remaining byte through the R185 probe
    end at 0x182331, validates the prior 0x18230B -> 0x18231D incoming call
    target as an exact instruction start, and checks two rel32 calls against
    the R185 raw census. Forward conditional targets 0x182331 and 0x182391 are
    decoded but not promoted to instruction boundaries or semantic identities
    because target bytes are outside this evidence window.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof(pe)
    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance(pe)

    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_INSTRUCTIONS:
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

    predecessor_incoming_call = next(
        (
            row
            for row in predecessor["calls"]
            if row["call_rva"]
            == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_CALL_RVA
            and row["decoded_target_rva"]
            == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_TARGET_RVA
            and row["matches"]
            and row["raw_candidate_present"]
        ),
        None,
    )
    incoming_target_is_instruction_boundary = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_TARGET_RVA
        in instruction_starts
    )

    branch_rows = []
    branch_targets_match = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_BRANCHES:
        decoded_target_rva = rel8_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        branch_rows.append(
            {
                "branch_rva": branch_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "target_within_captured_window": (
                    GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_RVA
                    <= decoded_target_rva
                    < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_3_PROBE_END_RVA
                    if decoded_target_rva is not None
                    else False
                ),
                "target_is_proven_instruction_boundary": (
                    decoded_target_rva in instruction_starts
                ),
            }
        )
        branch_targets_match = branch_targets_match and matches

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_CALLS:
        decoded_target_rva = rel32_call_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(
            item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva
            for item in provenance["raw_outbound_rel32_candidates"]
        )
        call_rows.append(
            {
                "call_rva": call_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "raw_candidate_present": raw_present,
            }
        )
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present

    predecessor_exact = (
        predecessor["status"] == "EXACT_182300_SEQUENCE_RET_NEXT_BOUNDARY_PROVEN"
        and predecessor["next_instruction_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_RVA
        and predecessor["next_instruction_boundary_matches"]
        and predecessor_incoming_call is not None
    )
    provenance_exact = (
        provenance["status"] == "EXACT_EXE_1822D1_CONTINUATION_PROVENANCE_CAPTURED"
        and provenance["target_section"] == ".text"
        and provenance["probe_end_matches"]
        and provenance["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_END_RVA
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    end_matches = (
        expected_next
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_END_RVA
        == provenance["probe_end_rva"]
    )
    proven = bool(
        predecessor_exact
        and provenance_exact
        and contiguous
        and all_bytes_match
        and end_matches
        and incoming_target_is_instruction_boundary
        and branch_targets_match
        and call_targets_match
        and raw_call_candidates_present
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_RVA,
        "target_section": provenance["target_section"],
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "provenance_status": provenance["status"],
        "provenance_exact": provenance_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_CONTINUATION_END_RVA,
        "end_matches_probe": end_matches,
        "incoming_call_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_CALL_RVA,
        "incoming_target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_NEXT_BLOCK_INCOMING_TARGET_RVA,
        "incoming_call_proven": predecessor_incoming_call is not None,
        "incoming_target_is_instruction_boundary": incoming_target_is_instruction_boundary,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "calls": call_rows,
        "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "status": (
            "EXACT_182314_TO_182331_CAPTURE_END_CONTROL_FLOW_PROVEN"
            if proven
            else "CALLEE_182314_CONTINUATION_CONTROL_FLOW_PROOF_FAILED"
        ),
        "incoming_target_status": "EXACT_18231D_INCOMING_CALL_TARGET_BOUNDARY_PROVEN",
        "forward_target_status": "DECODED_ONLY_TARGET_BYTES_NOT_CAPTURED",
        "function_entry_status": "UNRESOLVED_AT_182314_18231D_182331_182391",
        "semantic_effect": "BOUNDED_CAPTURE_END_CONTROL_FLOW_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_status": "EXACT_CAPTURE_END_AT_182331_REACHED",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance(pe: PE) -> dict:
    """Capture fresh exact bytes from 0x182331 through exclusive end 0x182391.

    R193 proves the preceding exact decode consumes every captured byte through
    0x182330 and reaches the R185 capture end at 0x182331. This collector
    extends provenance by exactly 96 bytes and records raw rel32 candidates
    only. The end address equals the previously decoded forward target
    0x182391, but no instruction-boundary/function/semantic claim is made for
    either endpoint in this task.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_LEN,
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_182314_TO_182331_CAPTURE_END_CONTROL_FLOW_PROVEN"
        and predecessor["end_rva"] == target_rva
        and predecessor["end_matches_probe"]
        and predecessor["continuation_status"] == "EXACT_CAPTURE_END_AT_182331_REACHED"
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_LEN
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "first_byte": probe[:1].hex(" "),
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_182331_TO_182391_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182331_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "UNRESOLVED_RAW_BYTES_ONLY",
        "end_target_status": "REACHED_182391_TARGET_BYTES_NOT_CAPTURED",
        "function_entry_status": "UNRESOLVED_AT_182331_AND_182391",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_AND_REL32_CENSUS_ONLY",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof(pe: PE) -> dict:
    """Decode the full R195 0x182331..0x182390 exact byte window.

    The predecessor R193 branch to 0x182331 is required and is upgraded to a
    proven instruction-boundary target only because this task decodes an exact
    first instruction there. All thirty instructions must be contiguous and
    exact. Internal branch targets must land on decoded instruction starts;
    external/forward targets are arithmetic-only evidence. The one E8 call
    must also match the R195 raw rel32 census.
    """

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance(pe)
    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof(pe)

    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_INSTRUCTIONS:
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

    def rel32_target(rva: int, size: int) -> int | None:
        raw = pe.bytes_at_rva(rva, size)
        if len(raw) != size:
            return None
        rel = struct.unpack_from("<i", raw, size - 4)[0]
        return (rva + size + rel) & 0xFFFFFFFF

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva, encoding in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_BRANCHES:
        decoded_target_rva = (
            rel8_target(branch_rva)
            if encoding == "rel8"
            else rel32_target(branch_rva, 6 if pe.bytes_at_rva(branch_rva, 1) == b"\x0f" else 5)
        )
        matches = decoded_target_rva == expected_target_rva
        target_within_window = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append(
            {
                "branch_rva": branch_rva,
                "encoding": encoding,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "target_within_window": target_within_window,
                "target_is_instruction_boundary": target_is_boundary,
            }
        )
        branch_targets_match = branch_targets_match and matches
        if target_within_window:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_CALLS:
        decoded_target_rva = rel32_target(call_rva, 5)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(
            item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva
            for item in provenance["raw_outbound_rel32_candidates"]
        )
        call_rows.append(
            {
                "call_rva": call_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "raw_candidate_present": raw_present,
            }
        )
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present

    incoming = next(
        (
            row
            for row in predecessor["branches"]
            if row["branch_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_INCOMING_BRANCH_RVA
            and row["decoded_target_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA
            and row["matches"]
        ),
        None,
    )
    incoming_target_is_instruction_boundary = (
        incoming is not None
        and GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA in instruction_starts
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_182314_TO_182331_CAPTURE_END_CONTROL_FLOW_PROVEN"
        and predecessor["end_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA
        and predecessor["end_matches_probe"]
        and incoming is not None
    )
    provenance_exact = (
        provenance["status"] == "EXACT_EXE_182331_TO_182391_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["target_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA
        and provenance["probe_end_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PREFIX_END_RVA
        and provenance["probe_end_matches"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PREFIX_END_RVA
    )
    proven = bool(
        predecessor_exact
        and provenance_exact
        and contiguous
        and all_bytes_match
        and end_matches
        and incoming_target_is_instruction_boundary
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and call_targets_match
        and raw_call_candidates_present
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA,
        "end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_PREFIX_END_RVA,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "provenance_status": provenance["status"],
        "provenance_exact": provenance_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "end_matches": end_matches,
        "incoming_branch_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_INCOMING_BRANCH_RVA,
        "incoming_target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_4_RVA,
        "incoming_target_is_instruction_boundary": incoming_target_is_instruction_boundary,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "calls": call_rows,
        "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "status": (
            "EXACT_182331_TO_182391_CONTROL_FLOW_PREFIX_PROVEN"
            if proven
            else "CALLEE_182331_CONTROL_FLOW_PREFIX_PROOF_FAILED"
        ),
        "incoming_target_status": "EXACT_182331_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN",
        "end_target_status": "REACHED_182391_TARGET_BYTES_NOT_CAPTURED",
        "function_entry_status": "UNRESOLVED_AT_182331_182391_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_AND_CALL_TARGET_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance(pe: PE) -> dict:
    """Capture fresh exact bytes from 0x182391 through exclusive end 0x1823F1.

    R197 proves the prior exact decode ends exactly at 0x182391 and decodes
    branches toward 0x182391, 0x18239F and 0x1823AC. This collector captures
    all three target byte locations in one 96-byte .text window and records
    raw rel32 census only. No included address is upgraded to an instruction
    boundary or semantic/function identity in this task.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_LEN,
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_182331_TO_182391_CONTROL_FLOW_PREFIX_PROVEN"
        and predecessor["end_rva"] == target_rva
        and predecessor["end_matches"]
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_END_RVA
    )
    referenced_targets_in_window = all(
        target_rva <= rva < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_END_RVA
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_REFERENCED_TARGET_RVAS
    )
    referenced_target_bytes = [
        {
            "rva": rva,
            "first_8_bytes": pe.bytes_at_rva(rva, 8).hex(" "),
        }
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_REFERENCED_TARGET_RVAS
    ]
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_LEN
        and probe_end_matches
        and referenced_targets_in_window
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "first_byte": probe[:1].hex(" "),
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "referenced_targets_in_window": referenced_targets_in_window,
        "referenced_target_bytes": referenced_target_bytes,
        "status": (
            "EXACT_EXE_182391_TO_1823F1_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182391_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "UNRESOLVED_RAW_BYTES_ONLY",
        "referenced_target_status": "BYTES_CAPTURED_BOUNDARIES_UNRESOLVED",
        "function_entry_status": "UNRESOLVED_AT_182391_18239F_1823AC",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_TARGET_BYTES_AND_REL32_CENSUS_ONLY",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof(pe: PE) -> dict:
    """Prove the exact 0x182391 block, terminal ret, padding and next boundary."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance(pe)
    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof(pe)
    earlier = collect_guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof(pe)

    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_INSTRUCTIONS:
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

    def rel32_target(rva: int, size: int) -> int | None:
        raw = pe.bytes_at_rva(rva, size)
        if len(raw) != size:
            return None
        rel = struct.unpack_from("<i", raw, size - 4)[0]
        return (rva + size + rel) & 0xFFFFFFFF

    branch_rows = []
    branch_targets_match = True
    prior_target_boundaries_match = True
    prior_instruction_starts = {row["rva"] for row in predecessor["instructions"]}
    for branch_rva, expected_target_rva, encoding in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_BRANCHES:
        decoded_target_rva = (
            rel8_target(branch_rva)
            if encoding == "rel8"
            else rel32_target(branch_rva, 6)
        )
        matches = decoded_target_rva == expected_target_rva
        prior_boundary = (
            decoded_target_rva in prior_instruction_starts
            if decoded_target_rva is not None
            else False
        )
        branch_rows.append(
            {
                "branch_rva": branch_rva,
                "encoding": encoding,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "target_is_predecessor_instruction_boundary": prior_boundary,
            }
        )
        branch_targets_match = branch_targets_match and matches
        if expected_target_rva == 0x0018238A:
            prior_target_boundaries_match = prior_target_boundaries_match and prior_boundary

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_CALLS:
        decoded_target_rva = rel32_target(call_rva, 5)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(
            item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva
            for item in provenance["raw_outbound_rel32_candidates"]
        )
        call_rows.append(
            {
                "call_rva": call_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "raw_candidate_present": raw_present,
            }
        )
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present

    prior_refs = {
        "0x00182391": any(
            row["branch_rva"] == 0x00182322
            and row["decoded_target_rva"] == 0x00182391
            and row["matches"]
            for row in earlier["branches"]
        ),
        "0x0018239F": any(
            row["decoded_target_rva"] == 0x0018239F and row["matches"]
            for row in predecessor["branches"]
        ),
        "0x001823AC": any(
            row["decoded_target_rva"] == 0x001823AC and row["matches"]
            for row in predecessor["branches"]
        ),
    }
    referenced_boundaries = {
        f"0x{rva:08X}": (
            rva in instruction_starts
            and prior_refs.get(f"0x{rva:08X}", False)
        )
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_REFERENCED_BOUNDARY_RVAS
    }
    referenced_boundaries_proven = all(referenced_boundaries.values())

    padding = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_RVA,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_LEN,
    )
    padding_matches = padding == (b"\xCC" * GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_LEN)
    next_code = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_NEXT_CODE_RVA, 3
    )
    next_code_boundary_matches = next_code == bytes.fromhex("83 ec 0c")

    predecessor_exact = (
        predecessor["status"] == "EXACT_182331_TO_182391_CONTROL_FLOW_PREFIX_PROVEN"
        and predecessor["end_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RVA
        and predecessor["end_matches"]
    )
    provenance_exact = (
        provenance["status"] == "EXACT_EXE_182391_TO_1823F1_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["target_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RVA
        and provenance["probe_end_matches"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PREFIX_END_RVA
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_RVA
    )
    ret_matches = (
        pe.bytes_at_rva(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RET_RVA, 1)
        == b"\xC3"
    )
    proven = bool(
        predecessor_exact
        and provenance_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and ret_matches
        and padding_matches
        and next_code_boundary_matches
        and referenced_boundaries_proven
        and branch_targets_match
        and prior_target_boundaries_match
        and call_targets_match
        and raw_call_candidates_present
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RVA,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "provenance_status": provenance["status"],
        "provenance_exact": provenance_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PREFIX_END_RVA,
        "prefix_end_matches": prefix_end_matches,
        "ret_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_RET_RVA,
        "ret_matches": ret_matches,
        "padding_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_RVA,
        "padding_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PADDING_LEN,
        "padding_bytes": padding.hex(" "),
        "padding_matches": padding_matches,
        "next_code_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_NEXT_CODE_RVA,
        "next_code_bytes": next_code.hex(" "),
        "next_code_boundary_matches": next_code_boundary_matches,
        "referenced_boundaries": referenced_boundaries,
        "referenced_boundaries_proven": referenced_boundaries_proven,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "prior_target_boundaries_match": prior_target_boundaries_match,
        "calls": call_rows,
        "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "status": (
            "EXACT_182391_SEQUENCE_RET_PADDING_NEXT_BOUNDARY_PROVEN"
            if proven
            else "CALLEE_182391_SEQUENCE_BOUNDARY_PROOF_FAILED"
        ),
        "terminal_status": "EXACT_RET_AT_1823CA_PROVEN",
        "padding_status": "EXACT_5_BYTE_INT3_PADDING_PROVEN",
        "next_boundary_status": "EXACT_1823D0_CODE_BOUNDARY_PROVEN",
        "function_entry_status": "UNRESOLVED_AT_182391_1823D0_AND_CALLEES",
        "semantic_effect": "BOUNDED_SEQUENCE_CONTROL_FLOW_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof(pe: PE) -> dict:
    """Prove the exact 0x1823D0 tail through the R199 capture edge."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance(pe)
    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof(pe)

    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INSTRUCTIONS:
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

    def rel32_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) != 5:
            return None
        rel = struct.unpack_from("<i", raw, 1)[0]
        return (rva + 5 + rel) & 0xFFFFFFFF

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    internal_call_targets_on_boundaries = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_CALLS:
        decoded_target_rva = rel32_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(
            item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva
            for item in provenance["raw_outbound_rel32_candidates"]
        )
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        call_rows.append(
            {
                "call_rva": call_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "raw_candidate_present": raw_present,
                "target_within_prefix": target_within_prefix,
                "target_is_instruction_boundary": target_is_boundary,
            }
        )
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present
        if target_within_prefix:
            internal_call_targets_on_boundaries = (
                internal_call_targets_on_boundaries and target_is_boundary
            )

    predecessor_exact = (
        predecessor["status"] == "EXACT_182391_SEQUENCE_RET_PADDING_NEXT_BOUNDARY_PROVEN"
        and predecessor["next_code_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RVA
        and predecessor["next_code_boundary_matches"]
    )
    provenance_exact = (
        provenance["status"] == "EXACT_EXE_182391_TO_1823F1_PROVENANCE_CAPTURED"
        and provenance["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_END_RVA
        and provenance["probe_end_matches"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_PREFIX_END_RVA
    )
    ret_matches = (
        pe.bytes_at_rva(
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RET_RVA, 1
        )
        == b"\xC3"
    )
    next_code = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_NEXT_CODE_RVA, 4
    )
    next_code_boundary_matches = (
        next_code == bytes.fromhex("8d 54 24 04")
        and GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_NEXT_CODE_RVA
        in instruction_starts
    )
    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INCOMPLETE_BYTES
    )
    capture_end_matches = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INCOMPLETE_RVA
        + len(incomplete)
        == provenance["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_PROBE_END_RVA
    )
    internal_call_boundary_proven = any(
        row["call_rva"] == 0x001823DB
        and row["decoded_target_rva"] == 0x001823ED
        and row["matches"]
        and row["target_is_instruction_boundary"]
        for row in call_rows
    )
    proven = bool(
        predecessor_exact
        and provenance_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and ret_matches
        and next_code_boundary_matches
        and incomplete_matches
        and capture_end_matches
        and call_targets_match
        and raw_call_candidates_present
        and internal_call_targets_on_boundaries
        and internal_call_boundary_proven
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_PREFIX_END_RVA,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "provenance_status": provenance["status"],
        "provenance_exact": provenance_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "ret_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_RET_RVA,
        "ret_matches": ret_matches,
        "next_code_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_NEXT_CODE_RVA,
        "next_code_bytes": next_code.hex(" "),
        "next_code_boundary_matches": next_code_boundary_matches,
        "calls": call_rows,
        "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "internal_call_targets_on_boundaries": internal_call_targets_on_boundaries,
        "internal_call_boundary_proven": internal_call_boundary_proven,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_5_TAIL_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_matches": capture_end_matches,
        "status": (
            "EXACT_1823D0_TO_1823EF_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_1823D0_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "terminal_status": "EXACT_RET_AT_1823E3_PROVEN",
        "next_boundary_status": "EXACT_1823E4_CODE_BOUNDARY_PROVEN",
        "internal_call_target_status": "EXACT_1823ED_INCOMING_CALL_TARGET_BOUNDARY_PROVEN",
        "continuation_status": "INCOMPLETE_INSTRUCTION_AT_1823EF_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_1823D0_1823E4_1823ED_AND_CALLEES",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance(pe: PE) -> dict:
    """Capture fresh exact bytes from 0x1823EF through exclusive end 0x18242F.

    The first two bytes must preserve the d9 3c overlap proven by R203. The
    remainder extends beyond the prior 0x1823F1 capture edge. This collector
    records raw bytes and rel32 census only; it does not decode or assign
    function/callee/render/HUD semantics.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_LEN,
    )
    overlap_len = len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_OVERLAP_BYTES)
    overlap = probe[:overlap_len]
    predecessor_exact = (
        predecessor["status"] == "EXACT_1823D0_TO_1823EF_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
        and predecessor["capture_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PRIOR_CAPTURE_END_RVA
    )
    overlap_matches = (
        overlap
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_END_RVA
    )
    extends_prior_capture = (
        target_rva
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PRIOR_CAPTURE_END_RVA
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_LEN
        and overlap_matches
        and probe_end_matches
        and extends_prior_capture
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "prior_capture_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PRIOR_CAPTURE_END_RVA,
        "extends_prior_capture": extends_prior_capture,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1823EF_TO_18242F_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1823EF_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "overlap_status": (
            "EXACT_D9_3C_OVERLAP_PROVEN"
            if overlap_matches
            else "D9_3C_OVERLAP_MISMATCH"
        ),
        "start_boundary_status": "R203_INCOMPLETE_INSTRUCTION_START_ONLY",
        "function_entry_status": "UNRESOLVED_AT_1823EF_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof(pe: PE) -> dict:
    """Exact-decode only the complete instructions already captured by R205."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INSTRUCTIONS:
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

    def branch_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 6)
        if len(raw) >= 2 and raw[0] in (0x73, 0x74):
            rel = struct.unpack_from("<b", raw, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        if len(raw) == 6 and raw[:2] == b"\x0F\x85":
            rel = struct.unpack_from("<i", raw, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_BRANCHES:
        decoded_target_rva = branch_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append(
            {
                "branch_rva": branch_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "target_within_prefix": target_within_prefix,
                "target_is_instruction_boundary": target_is_boundary,
            }
        )
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    def rel32_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) != 5 or raw[0] != 0xE8:
            return None
        rel = struct.unpack_from("<i", raw, 1)[0]
        return (rva + 5 + rel) & 0xFFFFFFFF

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_CALLS:
        decoded_target_rva = rel32_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(
            item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva
            for item in provenance["raw_outbound_rel32_candidates"]
        )
        call_rows.append(
            {
                "call_rva": call_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "raw_candidate_present": raw_present,
            }
        )
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present

    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1823EF_TO_18242F_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PREFIX_END_RVA
    )
    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_BYTES
    )
    capture_end_matches = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_RVA
        + len(incomplete)
        == provenance["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PROBE_END_RVA
    )
    internal_branch_boundary_proven = any(
        row["branch_rva"] == 0x001823FA
        and row["decoded_target_rva"] == 0x00182401
        and row["matches"]
        and row["target_is_instruction_boundary"]
        for row in branch_rows
    )
    proven = bool(
        predecessor_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and internal_branch_boundary_proven
        and call_targets_match
        and raw_call_candidates_present
        and incomplete_matches
        and capture_end_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "internal_branch_boundary_proven": internal_branch_boundary_proven,
        "calls": call_rows,
        "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_6_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_matches": capture_end_matches,
        "status": (
            "EXACT_1823EF_TO_18242E_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_1823EF_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_1823EF_CODE_BOUNDARY_PROVEN",
        "internal_branch_target_status": "EXACT_182401_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN",
        "continuation_status": "INCOMPLETE_REL32_JMP_AT_18242E_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_1823EF_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance(pe: PE) -> dict:
    """Capture fresh exact bytes from 0x18242E through exclusive end 0x18246E.

    The first byte must preserve the e9 overlap proven by R207. The remainder
    extends beyond the prior 0x18242F capture edge. This collector records raw
    bytes and rel32 census only; it does not decode or assign function, callee,
    render or HUD semantics.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_LEN,
    )
    overlap_len = len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_OVERLAP_BYTES)
    overlap = probe[:overlap_len]
    predecessor_exact = (
        predecessor["status"] == "EXACT_1823EF_TO_18242E_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
        and predecessor["capture_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PRIOR_CAPTURE_END_RVA
    )
    overlap_matches = (
        overlap
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_END_RVA
    )
    extends_prior_capture = (
        target_rva
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PRIOR_CAPTURE_END_RVA
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_LEN
        and overlap_matches
        and probe_end_matches
        and extends_prior_capture
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "prior_capture_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PRIOR_CAPTURE_END_RVA,
        "extends_prior_capture": extends_prior_capture,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_18242E_TO_18246E_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_18242E_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "overlap_status": (
            "EXACT_E9_OVERLAP_PROVEN"
            if overlap_matches
            else "E9_OVERLAP_MISMATCH"
        ),
        "start_boundary_status": "R207_INCOMPLETE_REL32_JMP_START_ONLY",
        "function_entry_status": "UNRESOLVED_AT_18242E_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof(pe: PE) -> dict:
    """Exact-decode complete instructions already captured by R209."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance(pe)
    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INSTRUCTIONS:
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

    predecessor_instruction_starts = {
        row["rva"] for row in predecessor["instructions"] if row["bytes_match"]
    }

    def branch_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) >= 5 and raw[0] == 0xE9:
            rel = struct.unpack_from("<i", raw, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        if len(raw) >= 2 and (raw[0] == 0xEB or 0x70 <= raw[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    predecessor_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_BRANCHES:
        decoded_target_rva = branch_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PREFIX_END_RVA
        )
        target_in_predecessor = expected_target_rva in predecessor_instruction_starts
        target_is_boundary = decoded_target_rva in instruction_starts
        predecessor_target_is_boundary = (
            decoded_target_rva in predecessor_instruction_starts
        )
        branch_rows.append(
            {
                "branch_rva": branch_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "target_within_prefix": target_within_prefix,
                "target_is_instruction_boundary": target_is_boundary,
                "target_in_predecessor": target_in_predecessor,
                "predecessor_target_is_instruction_boundary": predecessor_target_is_boundary,
            }
        )
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )
        if target_in_predecessor:
            predecessor_branch_targets_on_boundaries = (
                predecessor_branch_targets_on_boundaries
                and predecessor_target_is_boundary
            )

    def rel32_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) != 5 or raw[0] != 0xE8:
            return None
        rel = struct.unpack_from("<i", raw, 1)[0]
        return (rva + 5 + rel) & 0xFFFFFFFF

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_CALLS:
        decoded_target_rva = rel32_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(
            item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva
            for item in provenance["raw_outbound_rel32_candidates"]
        )
        call_rows.append(
            {
                "call_rva": call_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "raw_candidate_present": raw_present,
            }
        )
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present

    incoming_182461_boundary_proven = any(
        row["branch_rva"] == 0x001823F2
        and row["decoded_target_rva"] == 0x00182461
        and row["matches"]
        for row in predecessor["branches"]
    ) and 0x00182461 in instruction_starts
    backedge_182416_boundary_proven = all(
        any(
            row["branch_rva"] == branch_rva
            and row["decoded_target_rva"] == 0x00182416
            and row["matches"]
            and row["predecessor_target_is_instruction_boundary"]
            for row in branch_rows
        )
        for branch_rva in (0x00182454, 0x00182458)
    )
    internal_18245a_boundary_proven = any(
        row["branch_rva"] == 0x00182466
        and row["decoded_target_rva"] == 0x0018245A
        and row["matches"]
        and row["target_is_instruction_boundary"]
        for row in branch_rows
    )

    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_18242E_TO_18246E_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
        and predecessor["status"] == "EXACT_1823EF_TO_18242E_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PREFIX_END_RVA
    )
    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_BYTES
    )
    capture_end_matches = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_RVA
        + len(incomplete)
        == provenance["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PROBE_END_RVA
    )
    proven = bool(
        predecessor_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and predecessor_branch_targets_on_boundaries
        and incoming_182461_boundary_proven
        and backedge_182416_boundary_proven
        and internal_18245a_boundary_proven
        and call_targets_match
        and raw_call_candidates_present
        and incomplete_matches
        and capture_end_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "predecessor_branch_targets_on_boundaries": predecessor_branch_targets_on_boundaries,
        "incoming_182461_boundary_proven": incoming_182461_boundary_proven,
        "backedge_182416_boundary_proven": backedge_182416_boundary_proven,
        "internal_18245a_boundary_proven": internal_18245a_boundary_proven,
        "calls": call_rows,
        "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_7_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_matches": capture_end_matches,
        "status": (
            "EXACT_18242E_TO_18246D_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_18242E_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_18242E_CODE_BOUNDARY_PROVEN",
        "incoming_branch_target_status": "EXACT_182461_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN",
        "backedge_target_status": "EXACT_182416_BACKEDGE_TARGET_BOUNDARY_PROVEN",
        "internal_branch_target_status": "EXACT_18245A_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN",
        "continuation_status": "INCOMPLETE_SHORT_JCC_AT_18246D_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_18242E_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
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


def collect_guarded_gf_target_c_alignment_proof(pe: PE) -> dict:
    """Verify the exact 0x65970 -> 0x65997 first-CALL instruction boundary.

    This is intentionally narrower than a full target-C control-flow proof.
    Later outbound raw candidates at 0x659AC and 0x659C1 remain unresolved.
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

    call_bytes = pe.bytes_at_rva(GF_TARGET_C_ALIGNED_CALL_RVA, 5)
    decoded_target_rva = None
    if len(call_bytes) == 5 and call_bytes[0] == 0xE8:
        rel = struct.unpack_from("<i", call_bytes, 1)[0]
        decoded_target_rva = (
            GF_TARGET_C_ALIGNED_CALL_RVA + 5 + rel
        ) & 0xFFFFFFFF

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

    target_section = next(
        (
            section.name
            for section in pe.sections
            if section.contains_rva(GF_TARGET_C_ALIGNED_CALL_TARGET_RVA)
        ),
        "",
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    entry_guess_matches = function_start_guess_rva == GF_TARGET_C_ENTRY_RVA
    call_target_matches = decoded_target_rva == GF_TARGET_C_ALIGNED_CALL_TARGET_RVA
    target_section_matches = target_section == ".text"
    call_row = next(
        (row for row in rows if row["rva"] == GF_TARGET_C_ALIGNED_CALL_RVA),
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
        and target_section_matches
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
        "call_target_section_matches": target_section_matches,
        "status": (
            "EXACT_FIRST_CALL_ALIGNMENT_PROVEN"
            if proven
            else "ALIGNMENT_PROOF_FAILED"
        ),
        "semantic_effect": "UNRESOLVED",
        "ownership_effect": "NONE",
        "remaining_raw_call_rvas": [0x000659AC, 0x000659C1],
    }


def collect_guarded_gf_target_c_second_call_alignment_proof(pe: PE) -> dict:
    """Verify the exact 0x6599F -> 0x659AC second-CALL instruction boundary.

    This continuation is anchored to the already-proven target-C first-call
    prefix. It does not infer the 0x28320 helper's semantic effect or ownership.
    """

    first_proof = collect_guarded_gf_target_c_alignment_proof(pe)
    first_last_rva, first_last_hex, _ = GF_TARGET_C_PREFIX_INSTRUCTIONS[-1]
    first_prefix_end_rva = first_last_rva + len(bytes.fromhex(first_last_hex))
    anchor_matches_first_prefix_end = (
        first_prefix_end_rva == GF_TARGET_C_SECOND_CALL_ANCHOR_RVA
    )

    expected_next = GF_TARGET_C_SECOND_CALL_ANCHOR_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_SECOND_CALL_INSTRUCTIONS:
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

    call_bytes = pe.bytes_at_rva(GF_TARGET_C_SECOND_ALIGNED_CALL_RVA, 5)
    decoded_target_rva = None
    if len(call_bytes) == 5 and call_bytes[0] == 0xE8:
        rel = struct.unpack_from("<i", call_bytes, 1)[0]
        decoded_target_rva = (
            GF_TARGET_C_SECOND_ALIGNED_CALL_RVA + 5 + rel
        ) & 0xFFFFFFFF

    target_section = next(
        (
            section.name
            for section in pe.sections
            if section.contains_rva(GF_TARGET_C_SECOND_ALIGNED_CALL_TARGET_RVA)
        ),
        "",
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    call_target_matches = (
        decoded_target_rva == GF_TARGET_C_SECOND_ALIGNED_CALL_TARGET_RVA
    )
    target_section_matches = target_section == ".text"
    call_row = next(
        (
            row
            for row in rows
            if row["rva"] == GF_TARGET_C_SECOND_ALIGNED_CALL_RVA
        ),
        None,
    )
    call_is_layout_boundary = bool(
        call_row
        and call_row["bytes_match"]
        and call_bytes
        and call_bytes[0] == 0xE8
    )
    first_call_proven = (
        first_proof["status"] == "EXACT_FIRST_CALL_ALIGNMENT_PROVEN"
    )
    proven = bool(
        first_call_proven
        and anchor_matches_first_prefix_end
        and contiguous
        and all_bytes_match
        and call_is_layout_boundary
        and call_target_matches
        and target_section_matches
    )
    return {
        "entry_rva": GF_TARGET_C_ENTRY_RVA,
        "function_start_guess_rva": first_proof["function_start_guess_rva"],
        "first_call_status": first_proof["status"],
        "first_call_proven": first_call_proven,
        "anchor_rva": GF_TARGET_C_SECOND_CALL_ANCHOR_RVA,
        "anchor_matches_first_prefix_end": anchor_matches_first_prefix_end,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "aligned_call_rva": GF_TARGET_C_SECOND_ALIGNED_CALL_RVA,
        "call_is_layout_boundary": call_is_layout_boundary,
        "decoded_call_target_rva": decoded_target_rva,
        "expected_call_target_rva": GF_TARGET_C_SECOND_ALIGNED_CALL_TARGET_RVA,
        "call_target_matches": call_target_matches,
        "call_target_section": target_section,
        "call_target_section_matches": target_section_matches,
        "status": (
            "EXACT_SECOND_CALL_ALIGNMENT_PROVEN"
            if proven
            else "ALIGNMENT_PROOF_FAILED"
        ),
        "semantic_effect": "UNRESOLVED",
        "ownership_effect": "NONE",
        "remaining_raw_call_rvas": [0x000659C1],
    }


def collect_guarded_gf_target_c_third_call_alignment_proof(pe: PE) -> dict:
    """Verify the exact 0x659B1 -> 0x659C1 third-CALL instruction boundary.

    This continuation is anchored to the already-proven target-C second CALL.
    It does not infer the 0x28800 helper's semantic effect or ownership.
    """

    second_proof = collect_guarded_gf_target_c_second_call_alignment_proof(pe)
    second_call_end_rva = GF_TARGET_C_SECOND_ALIGNED_CALL_RVA + 5
    anchor_matches_second_call_end = (
        second_call_end_rva == GF_TARGET_C_THIRD_CALL_ANCHOR_RVA
    )
    raw_candidate_carried_forward = (
        GF_TARGET_C_THIRD_ALIGNED_CALL_RVA
        in second_proof["remaining_raw_call_rvas"]
    )

    expected_next = GF_TARGET_C_THIRD_CALL_ANCHOR_RVA
    contiguous = True
    rows: list[dict] = []
    for rva, hex_bytes, asm in GF_TARGET_C_THIRD_CALL_INSTRUCTIONS:
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

    call_bytes = pe.bytes_at_rva(GF_TARGET_C_THIRD_ALIGNED_CALL_RVA, 5)
    decoded_target_rva = None
    if len(call_bytes) == 5 and call_bytes[0] == 0xE8:
        rel = struct.unpack_from("<i", call_bytes, 1)[0]
        decoded_target_rva = (
            GF_TARGET_C_THIRD_ALIGNED_CALL_RVA + 5 + rel
        ) & 0xFFFFFFFF

    target_section = next(
        (
            section.name
            for section in pe.sections
            if section.contains_rva(GF_TARGET_C_THIRD_ALIGNED_CALL_TARGET_RVA)
        ),
        "",
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    call_target_matches = (
        decoded_target_rva == GF_TARGET_C_THIRD_ALIGNED_CALL_TARGET_RVA
    )
    target_section_matches = target_section == ".text"
    call_row = next(
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
    second_call_proven = (
        second_proof["status"] == "EXACT_SECOND_CALL_ALIGNMENT_PROVEN"
    )
    proven = bool(
        second_call_proven
        and anchor_matches_second_call_end
        and raw_candidate_carried_forward
        and contiguous
        and all_bytes_match
        and call_is_layout_boundary
        and call_target_matches
        and target_section_matches
    )
    return {
        "entry_rva": GF_TARGET_C_ENTRY_RVA,
        "function_start_guess_rva": second_proof["function_start_guess_rva"],
        "second_call_status": second_proof["status"],
        "second_call_proven": second_call_proven,
        "anchor_rva": GF_TARGET_C_THIRD_CALL_ANCHOR_RVA,
        "anchor_matches_second_call_end": anchor_matches_second_call_end,
        "raw_candidate_carried_forward": raw_candidate_carried_forward,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "aligned_call_rva": GF_TARGET_C_THIRD_ALIGNED_CALL_RVA,
        "call_is_layout_boundary": call_is_layout_boundary,
        "decoded_call_target_rva": decoded_target_rva,
        "expected_call_target_rva": GF_TARGET_C_THIRD_ALIGNED_CALL_TARGET_RVA,
        "call_target_matches": call_target_matches,
        "call_target_section": target_section,
        "call_target_section_matches": target_section_matches,
        "status": (
            "EXACT_THIRD_CALL_ALIGNMENT_PROVEN"
            if proven
            else "ALIGNMENT_PROOF_FAILED"
        ),
        "semantic_effect": "UNRESOLVED",
        "ownership_effect": "NONE",
        "remaining_raw_call_rvas": [],
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance(pe: PE) -> dict:
    """Capture fresh exact bytes from 0x18246D through exclusive end 0x1824AD.

    The first byte must preserve the 75 overlap proven by R211. The remainder
    extends beyond the prior 0x18246E capture edge. This collector records raw
    bytes and rel32 census only; it does not decode or assign function, callee,
    render or HUD semantics.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_LEN,
    )
    overlap_len = len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_OVERLAP_BYTES)
    overlap = probe[:overlap_len]
    predecessor_exact = (
        predecessor["status"] == "EXACT_18242E_TO_18246D_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
        and predecessor["capture_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PRIOR_CAPTURE_END_RVA
    )
    overlap_matches = (
        overlap
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_END_RVA
    )
    extends_prior_capture = (
        target_rva
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PRIOR_CAPTURE_END_RVA
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_LEN
        and overlap_matches
        and probe_end_matches
        and extends_prior_capture
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "prior_capture_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PRIOR_CAPTURE_END_RVA,
        "extends_prior_capture": extends_prior_capture,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_18246D_TO_1824AD_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_18246D_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "overlap_status": (
            "EXACT_75_OVERLAP_PROVEN"
            if overlap_matches
            else "75_OVERLAP_MISMATCH"
        ),
        "start_boundary_status": "R211_INCOMPLETE_SHORT_JCC_START_ONLY",
        "function_entry_status": "UNRESOLVED_AT_18246D_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof(pe: PE) -> dict:
    """Exact-decode complete instructions already captured by R213."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance(pe)
    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INSTRUCTIONS:
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

    predecessor_instruction_starts = {
        row["rva"] for row in predecessor["instructions"] if row["bytes_match"]
    }

    def branch_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 6)
        if len(raw) >= 6 and raw[0] == 0x0F and 0x80 <= raw[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        if len(raw) >= 5 and raw[0] == 0xE9:
            rel = struct.unpack_from("<i", raw, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        if len(raw) >= 2 and (raw[0] == 0xEB or 0x70 <= raw[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    predecessor_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_BRANCHES:
        decoded_target_rva = branch_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PREFIX_END_RVA
        )
        target_in_predecessor = expected_target_rva in predecessor_instruction_starts
        target_is_boundary = decoded_target_rva in instruction_starts
        predecessor_target_is_boundary = (
            decoded_target_rva in predecessor_instruction_starts
        )
        branch_rows.append(
            {
                "branch_rva": branch_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "target_within_prefix": target_within_prefix,
                "target_is_instruction_boundary": target_is_boundary,
                "target_in_predecessor": target_in_predecessor,
                "predecessor_target_is_instruction_boundary": predecessor_target_is_boundary,
            }
        )
        branch_targets_match = branch_targets_match and matches
        if target_in_predecessor:
            predecessor_branch_targets_on_boundaries = (
                predecessor_branch_targets_on_boundaries
                and predecessor_target_is_boundary
            )

    def rel32_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) != 5 or raw[0] != 0xE8:
            return None
        rel = struct.unpack_from("<i", raw, 1)[0]
        return (rva + 5 + rel) & 0xFFFFFFFF

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_CALLS:
        decoded_target_rva = rel32_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(
            item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva
            for item in provenance["raw_outbound_rel32_candidates"]
        )
        call_rows.append(
            {
                "call_rva": call_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "raw_candidate_present": raw_present,
            }
        )
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present

    incoming_18246f_boundary_proven = all(
        any(
            row["branch_rva"] == branch_rva
            and row["decoded_target_rva"] == 0x0018246F
            and row["matches"]
            for row in predecessor["branches"]
        )
        for branch_rva in (0x00182433, 0x00182444)
    ) and 0x0018246F in instruction_starts
    incoming_18247c_boundary_proven = any(
        row["branch_rva"] == 0x0018245F
        and row["decoded_target_rva"] == 0x0018247C
        and row["matches"]
        for row in predecessor["branches"]
    ) and 0x0018247C in instruction_starts
    backedge_18245a_boundary_proven = any(
        row["branch_rva"] == 0x0018246D
        and row["decoded_target_rva"] == 0x0018245A
        and row["matches"]
        and row["predecessor_target_is_instruction_boundary"]
        for row in branch_rows
    )

    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_18246D_TO_1824AD_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
        and predecessor["status"] == "EXACT_18242E_TO_18246D_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PREFIX_END_RVA
    )
    ret_matches = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RET_RVA in instruction_starts
        and pe.bytes_at_rva(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RET_RVA, 1)
        == b"\xc3"
    )
    next_boundary_proven = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_NEXT_CODE_RVA
        in instruction_starts
    )
    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_BYTES
    )
    capture_end_matches = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_RVA
        + len(incomplete)
        == provenance["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PROBE_END_RVA
    )
    proven = bool(
        predecessor_exact
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and predecessor_branch_targets_on_boundaries
        and incoming_18246f_boundary_proven
        and incoming_18247c_boundary_proven
        and backedge_18245a_boundary_proven
        and call_targets_match
        and raw_call_candidates_present
        and ret_matches
        and next_boundary_proven
        and incomplete_matches
        and capture_end_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "predecessor_branch_targets_on_boundaries": predecessor_branch_targets_on_boundaries,
        "incoming_18246f_boundary_proven": incoming_18246f_boundary_proven,
        "incoming_18247c_boundary_proven": incoming_18247c_boundary_proven,
        "backedge_18245a_boundary_proven": backedge_18245a_boundary_proven,
        "calls": call_rows,
        "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "ret_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_RET_RVA,
        "ret_matches": ret_matches,
        "next_code_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_NEXT_CODE_RVA,
        "next_boundary_proven": next_boundary_proven,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_8_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_matches": capture_end_matches,
        "status": (
            "EXACT_18246D_TO_1824AB_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_18246D_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_18246D_CODE_BOUNDARY_PROVEN",
        "incoming_18246f_status": "EXACT_18246F_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN",
        "incoming_18247c_status": "EXACT_18247C_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN",
        "backedge_status": "EXACT_18245A_BACKEDGE_TARGET_BOUNDARY_PROVEN",
        "terminal_status": "EXACT_RET_AT_18249A_PROVEN",
        "next_boundary_status": "EXACT_18249B_CODE_BOUNDARY_PROVEN",
        "continuation_status": "INCOMPLETE_REL32_CALL_AT_1824AB_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_18246D_18249B_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance(pe: PE) -> dict:
    """Capture fresh exact bytes from 0x1824AB through exclusive end 0x1824EB.

    The first two bytes must preserve the e8 5e overlap proven by R215. The
    remainder extends beyond the prior 0x1824AD capture edge. This collector
    records raw bytes and rel32 census only; it does not decode or assign
    function, callee, render or HUD semantics.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_LEN,
    )
    overlap_len = len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_OVERLAP_BYTES)
    overlap = probe[:overlap_len]
    predecessor_exact = (
        predecessor["status"] == "EXACT_18246D_TO_1824AB_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
        and predecessor["capture_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PRIOR_CAPTURE_END_RVA
    )
    overlap_matches = (
        overlap
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_END_RVA
    )
    extends_prior_capture = (
        target_rva
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PRIOR_CAPTURE_END_RVA
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_LEN
        and overlap_matches
        and probe_end_matches
        and extends_prior_capture
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "prior_capture_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PRIOR_CAPTURE_END_RVA,
        "extends_prior_capture": extends_prior_capture,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1824AB_TO_1824EB_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1824AB_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "overlap_status": (
            "EXACT_E8_5E_OVERLAP_PROVEN"
            if overlap_matches
            else "E8_5E_OVERLAP_MISMATCH"
        ),
        "start_boundary_status": "R215_INCOMPLETE_REL32_CALL_START_ONLY",
        "function_entry_status": "UNRESOLVED_AT_1824AB_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof(pe: PE) -> dict:
    """Exact-decode complete instructions already captured by R217."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance(pe)
    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INSTRUCTIONS:
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

    def branch_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 6)
        if len(raw) >= 6 and raw[0] == 0x0F and 0x80 <= raw[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        if len(raw) >= 5 and raw[0] == 0xE9:
            rel = struct.unpack_from("<i", raw, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        if len(raw) >= 2 and (raw[0] == 0xEB or 0x70 <= raw[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_BRANCHES:
        decoded_target_rva = branch_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append(
            {
                "branch_rva": branch_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "target_within_prefix": target_within_prefix,
                "target_is_instruction_boundary": target_is_boundary,
            }
        )
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    def rel32_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) != 5 or raw[0] != 0xE8:
            return None
        rel = struct.unpack_from("<i", raw, 1)[0]
        return (rva + 5 + rel) & 0xFFFFFFFF

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_CALLS:
        decoded_target_rva = rel32_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(
            item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva
            for item in provenance["raw_outbound_rel32_candidates"]
        )
        call_rows.append(
            {
                "call_rva": call_rva,
                "expected_target_rva": expected_target_rva,
                "decoded_target_rva": decoded_target_rva,
                "matches": matches,
                "raw_candidate_present": raw_present,
            }
        )
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present

    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1824AB_TO_1824EB_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
        and predecessor["status"] == "EXACT_18246D_TO_1824AB_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RVA
        and predecessor["incomplete_matches"]
    )
    start_boundary_proven = (
        predecessor["incomplete_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RVA
        and predecessor["incomplete_matches"]
    )
    incoming_1824b0_boundary_proven = any(
        row["branch_rva"] == 0x001824A9
        and row["decoded_target_rva"] == 0x001824B0
        and row["matches"]
        for row in predecessor["branches"]
    ) and 0x001824B0 in instruction_starts
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PREFIX_END_RVA
    )
    ret_matches = all(
        rva in instruction_starts and pe.bytes_at_rva(rva, 1) == b"\xc3"
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RET_RVAS
    )
    post_ret_boundaries_proven = all(
        rva in instruction_starts
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_POST_RET_CODE_RVAS
    )
    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INCOMPLETE_BYTES
    )
    capture_end_matches = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INCOMPLETE_RVA
        + len(incomplete)
        == provenance["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PROBE_END_RVA
    )
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and incoming_1824b0_boundary_proven
        and call_targets_match
        and raw_call_candidates_present
        and ret_matches
        and post_ret_boundaries_proven
        and incomplete_matches
        and capture_end_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "incoming_1824b0_boundary_proven": incoming_1824b0_boundary_proven,
        "calls": call_rows,
        "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "ret_rvas": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_RET_RVAS),
        "ret_matches": ret_matches,
        "post_ret_code_rvas": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_POST_RET_CODE_RVAS),
        "post_ret_boundaries_proven": post_ret_boundaries_proven,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_9_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_matches": capture_end_matches,
        "status": (
            "EXACT_1824AB_TO_1824EA_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_1824AB_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_1824AB_REL32_CALL_BOUNDARY_PROVEN",
        "incoming_1824b0_status": "EXACT_1824B0_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN",
        "internal_branch_status": "EXACT_1824C9_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN",
        "external_branch_status": "EXACT_1824EF_TARGET_DECODED_OUTSIDE_CAPTURE",
        "terminal_status": "EXACT_RET_AT_1824C8_AND_1824D9_PROVEN",
        "post_terminal_boundary_status": "EXACT_1824C9_AND_1824DA_CODE_BOUNDARIES_PROVEN",
        "continuation_status": "INCOMPLETE_REL32_CALL_AT_1824EA_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_1824AB_1824C9_1824DA_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance(pe: PE) -> dict:
    """Capture fresh exact bytes from 0x1824EA through exclusive end 0x18252A.

    The first byte must preserve the e8 overlap proven by R219. The remainder
    extends beyond the prior 0x1824EB capture edge. This collector records raw
    bytes and rel32 census only; it does not decode or assign function, callee,
    render or HUD semantics.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_LEN,
    )
    overlap_len = len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_OVERLAP_BYTES)
    overlap = probe[:overlap_len]
    predecessor_exact = (
        predecessor["status"] == "EXACT_1824AB_TO_1824EA_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
        and predecessor["capture_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PRIOR_CAPTURE_END_RVA
    )
    overlap_matches = (
        overlap
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_END_RVA
    )
    extends_prior_capture = (
        target_rva
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PRIOR_CAPTURE_END_RVA
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_LEN
        and overlap_matches
        and probe_end_matches
        and extends_prior_capture
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "prior_capture_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PRIOR_CAPTURE_END_RVA,
        "extends_prior_capture": extends_prior_capture,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1824EA_TO_18252A_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1824EA_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "overlap_status": (
            "EXACT_E8_OVERLAP_PROVEN"
            if overlap_matches
            else "E8_OVERLAP_MISMATCH"
        ),
        "start_boundary_status": "R219_INCOMPLETE_REL32_CALL_START_ONLY",
        "function_entry_status": "UNRESOLVED_AT_1824EA_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof(pe: PE) -> dict:
    """Exact-decode complete instructions already captured by R221."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance(pe)
    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({"rva": rva, "asm": asm, "expected_bytes": expected.hex(" "), "actual_bytes": actual.hex(" "), "bytes_match": actual == expected})
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def branch_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 6)
        if len(raw) >= 6 and raw[0] == 0x0F and 0x80 <= raw[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        if len(raw) >= 5 and raw[0] == 0xE9:
            rel = struct.unpack_from("<i", raw, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        if len(raw) >= 2 and (raw[0] == 0xEB or 0x70 <= raw[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_BRANCHES:
        decoded_target_rva = branch_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RVA <= expected_target_rva < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PREFIX_END_RVA)
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append({"branch_rva": branch_rva, "expected_target_rva": expected_target_rva, "decoded_target_rva": decoded_target_rva, "matches": matches, "target_within_prefix": target_within_prefix, "target_is_instruction_boundary": target_is_boundary})
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = internal_branch_targets_on_boundaries and target_is_boundary

    def rel32_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 5)
        if len(raw) != 5 or raw[0] != 0xE8:
            return None
        rel = struct.unpack_from("<i", raw, 1)[0]
        return (rva + 5 + rel) & 0xFFFFFFFF

    call_rows = []
    call_targets_match = True
    raw_call_candidates_present = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_CALLS:
        decoded_target_rva = rel32_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        raw_present = any(item["call_rva"] == call_rva and item["target_rva"] == expected_target_rva for item in provenance["raw_outbound_rel32_candidates"])
        call_rows.append({"call_rva": call_rva, "expected_target_rva": expected_target_rva, "decoded_target_rva": decoded_target_rva, "matches": matches, "raw_candidate_present": raw_present})
        call_targets_match = call_targets_match and matches
        raw_call_candidates_present = raw_call_candidates_present and raw_present

    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1824EA_TO_18252A_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"] and provenance["overlap_matches"] and provenance["probe_end_matches"]
        and predecessor["status"] == "EXACT_1824AB_TO_1824EA_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RVA
        and predecessor["incomplete_matches"]
    )
    start_boundary_proven = predecessor["incomplete_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RVA and predecessor["incomplete_matches"]
    incoming_1824ef_boundary_proven = any(row["branch_rva"] == 0x001824E8 and row["decoded_target_rva"] == 0x001824EF and row["matches"] for row in predecessor["branches"]) and 0x001824EF in instruction_starts
    capture_edge_branch_target_proven = any(row["branch_rva"] == 0x00182522 and row["decoded_target_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_RVA and row["matches"] for row in branch_rows)
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PREFIX_END_RVA
    ret_matches = all(rva in instruction_starts and pe.bytes_at_rva(rva, 1) == b"\xc3" for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RET_RVAS)
    post_ret_boundaries_proven = all(rva in instruction_starts for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_POST_RET_CODE_RVAS)
    incomplete = pe.bytes_at_rva(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_RVA, len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_BYTES))
    incomplete_matches = incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_BYTES
    capture_end_matches = (GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_RVA + len(incomplete) == provenance["probe_end_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PROBE_END_RVA)
    proven = bool(
        predecessor_exact and start_boundary_proven and contiguous and all_bytes_match and prefix_end_matches
        and branch_targets_match and internal_branch_targets_on_boundaries and incoming_1824ef_boundary_proven
        and capture_edge_branch_target_proven and call_targets_match and raw_call_candidates_present
        and ret_matches and post_ret_boundaries_proven and incomplete_matches and capture_end_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_PREFIX_END_RVA,
        "predecessor_status": provenance["status"], "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven, "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match, "instructions": rows, "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches, "branches": branch_rows, "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "incoming_1824ef_boundary_proven": incoming_1824ef_boundary_proven,
        "capture_edge_branch_target_proven": capture_edge_branch_target_proven,
        "calls": call_rows, "call_targets_match": call_targets_match,
        "raw_call_candidates_present": raw_call_candidates_present,
        "ret_rvas": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_RET_RVAS), "ret_matches": ret_matches,
        "post_ret_code_rvas": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_POST_RET_CODE_RVAS),
        "post_ret_boundaries_proven": post_ret_boundaries_proven,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_10_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "), "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"], "capture_end_matches": capture_end_matches,
        "status": ("EXACT_1824EA_TO_182529_CONTROL_FLOW_CAPTURE_EDGE_PROVEN" if proven else "CALLEE_1824EA_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"),
        "start_boundary_status": "EXACT_1824EA_REL32_CALL_BOUNDARY_PROVEN",
        "incoming_1824ef_status": "EXACT_1824EF_INCOMING_BRANCH_TARGET_BOUNDARY_PROVEN",
        "internal_branch_status": "EXACT_182505_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN",
        "capture_edge_branch_status": "EXACT_182529_BRANCH_TARGET_AT_CAPTURE_EDGE_PROVEN",
        "terminal_status": "EXACT_RET_AT_182504_AND_182513_PROVEN",
        "post_terminal_boundary_status": "EXACT_182505_AND_182514_CODE_BOUNDARIES_PROVEN",
        "continuation_status": "INCOMPLETE_INSTRUCTION_AT_182529_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_1824EA_182505_182514_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED", "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance(pe: PE) -> dict:
    """Capture fresh exact bytes from 0x182529 through exclusive end 0x182569.

    The first byte must preserve the 83 overlap proven by R223. The remainder
    extends beyond the prior 0x18252A capture edge. This collector records raw
    bytes and rel32 census only; it does not decode or assign function, callee,
    render or HUD semantics.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_LEN,
    )
    overlap_len = len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_OVERLAP_BYTES)
    overlap = probe[:overlap_len]
    predecessor_exact = (
        predecessor["status"] == "EXACT_1824EA_TO_182529_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
        and predecessor["capture_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PRIOR_CAPTURE_END_RVA
    )
    overlap_matches = (
        overlap
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_END_RVA
    )
    extends_prior_capture = (
        target_rva
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PRIOR_CAPTURE_END_RVA
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_LEN
        and overlap_matches
        and probe_end_matches
        and extends_prior_capture
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "prior_capture_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_11_PRIOR_CAPTURE_END_RVA,
        "extends_prior_capture": extends_prior_capture,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_182529_TO_182569_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182529_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "overlap_status": (
            "EXACT_83_OVERLAP_PROVEN"
            if overlap_matches
            else "83_OVERLAP_MISMATCH"
        ),
        "start_boundary_status": "R223_INCOMPLETE_83_START_ONLY",
        "function_entry_status": "UNRESOLVED_AT_182529_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_12_provenance(pe: PE) -> dict:
    """Capture fresh exact bytes from 0x182569 through exclusive end 0x1825A9.

    R261 proved that the predecessor decode ends exactly at 0x182569 with no
    partial instruction bytes consumed. This collector therefore requires exact
    predecessor provenance and contiguous start/end identity, then records only
    raw bytes and rel32 candidate census. It does not assign function, callee,
    render or HUD semantics.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_LEN,
    )
    starts_at_prior_capture_end = (
        target_rva
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PRIOR_CAPTURE_END_RVA
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_EXE_182529_TO_182569_PROVENANCE_CAPTURED"
        and predecessor["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PRIOR_CAPTURE_END_RVA
        and starts_at_prior_capture_end
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_END_RVA
    )
    extends_prior_capture = (
        starts_at_prior_capture_end
        and GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_END_RVA
        > GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PRIOR_CAPTURE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_LEN
        and probe_end_matches
        and extends_prior_capture
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "prior_capture_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_12_PRIOR_CAPTURE_END_RVA,
        "starts_at_prior_capture_end": starts_at_prior_capture_end,
        "extends_prior_capture": extends_prior_capture,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_182569_TO_1825A9_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182569_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "continuity_status": (
            "EXACT_182569_CONTIGUOUS_BOUNDARY_PROVEN"
            if starts_at_prior_capture_end
            else "182569_CONTIGUITY_MISMATCH"
        ),
        "start_boundary_status": "R261_EXACT_CAPTURE_END_INSTRUCTION_BOUNDARY",
        "function_entry_status": "UNRESOLVED_AT_182569_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_CONTIGUITY_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_13_provenance(pe: PE) -> dict:
    """Capture fresh exact bytes from 0x1825A6 through exclusive end 0x1825E6.

    R267 proved that 0x1825A6 begins a TEST EAX, imm32 instruction but the
    validated predecessor window contains only its first three bytes (a9 00 00).
    Require that exact overlap before accepting any newly observed bytes. The
    wider window includes the nearby external conditional-branch targets through
    0x1825BC but does not assign semantics to them.
    """

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_12_provenance(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe,
        target_rva,
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_LEN,
    )
    overlap_len = len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_OVERLAP_BYTES)
    overlap = probe[:overlap_len]
    predecessor_exact = (
        predecessor["status"] == "EXACT_EXE_182569_TO_1825A9_PROVENANCE_CAPTURED"
        and predecessor["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PRIOR_CAPTURE_END_RVA
    )
    overlap_matches = (
        overlap
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_END_RVA
    )
    extends_prior_capture = (
        target_rva
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PRIOR_CAPTURE_END_RVA
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_END_RVA
    )
    branch_targets_covered = all(
        target_rva <= branch_rva < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_END_RVA
        for branch_rva in (0x001825AD, 0x001825B2, 0x001825B7, 0x001825BC)
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_LEN
        and overlap_matches
        and probe_end_matches
        and extends_prior_capture
        and branch_targets_covered
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "prior_capture_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PRIOR_CAPTURE_END_RVA,
        "extends_prior_capture": extends_prior_capture,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "branch_targets_covered": branch_targets_covered,
        "covered_branch_targets": [0x001825AD, 0x001825B2, 0x001825B7, 0x001825BC],
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1825A6_TO_1825E6_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1825A6_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "overlap_status": (
            "EXACT_A9_00_00_OVERLAP_PROVEN"
            if overlap_matches
            else "A9_00_00_OVERLAP_MISMATCH"
        ),
        "start_boundary_status": "R267_INCOMPLETE_TEST_EAX_IMM32_START",
        "function_entry_status": "UNRESOLVED_AT_1825A6_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_BRANCH_TARGET_COVERAGE_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_13_prefix_proof(pe: PE) -> dict:
    """Exact-decode complete instructions already captured by R267 follow-up."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_13_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva,
            "asm": asm,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def branch_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 2)
        if len(raw) >= 2 and (raw[0] == 0xEB or 0x70 <= raw[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_BRANCHES:
        decoded_target_rva = branch_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix": target_within_prefix,
            "target_is_instruction_boundary": target_is_boundary,
        })
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    predecessor_targets_on_boundaries = all(
        target in instruction_starts
        for target in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PREDECESSOR_TARGET_RVAS
    )
    backedge_target_bytes = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_BACKEDGE_TARGET_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_BACKEDGE_TARGET_BYTES),
    )
    backedge_target_boundary_proven = (
        backedge_target_bytes
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_BACKEDGE_TARGET_BYTES
    )
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1825A6_TO_1825E6_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
        and provenance["branch_targets_covered"]
    )
    start_boundary_proven = bool(rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"])
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PREFIX_END_RVA
    )
    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INCOMPLETE_BYTES
    )
    capture_end_matches = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INCOMPLETE_RVA
        + len(incomplete)
        == provenance["probe_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PROBE_END_RVA
    )
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and predecessor_targets_on_boundaries
        and backedge_target_boundary_proven
        and incomplete_matches
        and capture_end_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "predecessor_target_rvas": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_PREDECESSOR_TARGET_RVAS),
        "predecessor_targets_on_boundaries": predecessor_targets_on_boundaries,
        "backedge_target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_BACKEDGE_TARGET_RVA,
        "backedge_target_bytes": backedge_target_bytes.hex(" "),
        "backedge_target_boundary_proven": backedge_target_boundary_proven,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_13_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_matches": capture_end_matches,
        "status": (
            "EXACT_1825A6_TO_1825E5_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_1825A6_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_1825A6_TEST_EAX_IMM32_BOUNDARY_PROVEN",
        "predecessor_target_status": "EXACT_1825AD_B2_B7_BC_BOUNDARIES_PROVEN",
        "backedge_status": "EXACT_18257C_PREDECESSOR_BOUNDARY_BYTES_PROVEN",
        "continuation_status": "INCOMPLETE_SHORT_JCC_AT_1825E5",
        "function_entry_status": "UNRESOLVED_AT_1825A6_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_ONLY",
        "call_semantics": "NONE_IN_PREFIX",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_14_provenance(pe: PE) -> dict:
    """Capture exact bytes from 0x1825E5 through exclusive end 0x182635."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_13_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_LEN
    )
    overlap_len = len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_OVERLAP_BYTES)
    overlap = probe[:overlap_len]
    predecessor_exact = (
        predecessor["status"] == "EXACT_1825A6_TO_1825E5_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
        and predecessor["capture_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PRIOR_CAPTURE_END_RVA
    )
    overlap_matches = (
        overlap == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_END_RVA
    )
    extends_prior_capture = (
        target_rva
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PRIOR_CAPTURE_END_RVA
        < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_END_RVA
    )
    predecessor_targets_covered = all(
        target_rva <= rva < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_END_RVA
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREDECESSOR_TARGET_RVAS
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_LEN
        and overlap_matches
        and probe_end_matches
        and extends_prior_capture
        and predecessor_targets_covered
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "prior_capture_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PRIOR_CAPTURE_END_RVA,
        "extends_prior_capture": extends_prior_capture,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "predecessor_targets_covered": predecessor_targets_covered,
        "covered_predecessor_targets": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREDECESSOR_TARGET_RVAS),
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1825E5_TO_182635_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1825E5_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "overlap_status": (
            "EXACT_74_OVERLAP_PROVEN" if overlap_matches else "74_OVERLAP_MISMATCH"
        ),
        "start_boundary_status": "R267_INCOMPLETE_SHORT_JCC_OPCODE_START",
        "function_entry_status": "UNRESOLVED_AT_1825E5_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_PREDECESSOR_TARGET_COVERAGE_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_14_prefix_proof(pe: PE) -> dict:
    """Exact-decode the complete 0x1825E5..0x182635 validated window."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_14_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva, "asm": asm, "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "), "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def branch_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 2)
        if len(raw) >= 2 and (raw[0] == 0xEB or 0x70 <= raw[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_BRANCHES:
        decoded_target_rva = branch_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix": target_within_prefix,
            "target_is_instruction_boundary": target_is_boundary,
        })
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    predecessor_targets_on_boundaries = all(
        rva in instruction_starts
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREDECESSOR_TARGET_RVAS
    )
    backedge_bytes = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_BACKEDGE_TARGET_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_BACKEDGE_TARGET_BYTES),
    )
    backedge_target_boundary_proven = (
        backedge_bytes == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_BACKEDGE_TARGET_BYTES
    )
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1825E5_TO_182635_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"] and provenance["overlap_matches"]
        and provenance["probe_end_matches"] and provenance["predecessor_targets_covered"]
    )
    start_boundary_proven = bool(rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"])
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREFIX_END_RVA
        == provenance["probe_end_rva"]
    )
    ret_matches = all(
        rva in instruction_starts and pe.bytes_at_rva(rva, 1) == b"\xc3"
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_RET_RVAS
    )
    post_ret_boundaries_proven = all(
        rva in instruction_starts
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_POST_RET_CODE_RVAS
    )
    proven = bool(
        predecessor_exact and start_boundary_proven and contiguous and all_bytes_match
        and prefix_end_matches and branch_targets_match and internal_branch_targets_on_boundaries
        and predecessor_targets_on_boundaries and backedge_target_boundary_proven
        and ret_matches and post_ret_boundaries_proven
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREFIX_END_RVA,
        "predecessor_status": provenance["status"], "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven, "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match, "instructions": rows,
        "instruction_count": len(rows), "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows, "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "predecessor_target_rvas": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_PREDECESSOR_TARGET_RVAS),
        "predecessor_targets_on_boundaries": predecessor_targets_on_boundaries,
        "backedge_target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_BACKEDGE_TARGET_RVA,
        "backedge_target_bytes": backedge_bytes.hex(" "),
        "backedge_target_boundary_proven": backedge_target_boundary_proven,
        "ret_rvas": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_RET_RVAS),
        "ret_matches": ret_matches,
        "post_ret_code_rvas": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_14_POST_RET_CODE_RVAS),
        "post_ret_boundaries_proven": post_ret_boundaries_proven,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_is_instruction_boundary": prefix_end_matches,
        "status": (
            "EXACT_1825E5_TO_182635_CONTROL_FLOW_PREFIX_PROVEN"
            if proven else "CALLEE_1825E5_CONTROL_FLOW_PREFIX_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_1825E5_SHORT_JCC_BOUNDARY_PROVEN",
        "predecessor_target_status": "EXACT_1825F6_18261A_18262E_BOUNDARIES_PROVEN",
        "backedge_status": "EXACT_1825D4_PREDECESSOR_BOUNDARY_BYTES_PROVEN",
        "terminal_status": "EXACT_RET_182619_182623_AND_CONTINUATIONS_PROVEN",
        "continuation_status": "EXACT_CAPTURE_END_INSTRUCTION_BOUNDARY_182635",
        "function_entry_status": "UNRESOLVED_AT_1825E5_AND_FORWARD_BYTES",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_ONLY",
        "call_semantics": "NONE_IN_PREFIX",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_15_provenance(pe: PE) -> dict:
    """Capture exact canonical-EXE bytes at 0x182635..0x182674 without semantic promotion."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_14_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_1825E5_TO_182635_CONTROL_FLOW_PREFIX_PROVEN"
        and predecessor["capture_end_is_instruction_boundary"]
        and predecessor["prefix_end_rva"]
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREDECESSOR_END_RVA
        and target_rva
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREDECESSOR_END_RVA
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PROBE_LEN
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "predecessor_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREDECESSOR_END_RVA,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_182635_TO_182675_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182635_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "EXACT_182635_PREDECESSOR_INSTRUCTION_BOUNDARY",
        "function_entry_status": "UNRESOLVED_AT_182635_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_15_prefix_proof(pe: PE) -> dict:
    """Exact-decode only the complete prefix captured at 0x182635; preserve the cut tail raw-only."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_15_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva,
            "asm": asm,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def short_branch_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 2)
        if len(raw) >= 2 and 0x70 <= raw[0] <= 0x7F:
            rel = struct.unpack_from("<b", raw, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_BRANCHES:
        decoded_target_rva = short_branch_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix": target_within_prefix,
            "target_is_instruction_boundary": target_is_boundary,
        })
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    predecessor_target_rows = []
    predecessor_targets_match = True
    for rva, expected in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREDECESSOR_TARGET_BYTES:
        actual = pe.bytes_at_rva(rva, len(expected))
        matches = actual == expected
        predecessor_target_rows.append({
            "rva": rva,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "matches": matches,
        })
        predecessor_targets_match = predecessor_targets_match and matches

    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INCOMPLETE_BYTES
    )
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_182635_TO_182675_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(
        rows
        and rows[0]["rva"] == provenance["target_rva"]
        and rows[0]["bytes_match"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREFIX_END_RVA
    )
    incomplete_inside_capture = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INCOMPLETE_RVA
        < provenance["probe_end_rva"]
    )
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and predecessor_targets_match
        and incomplete_matches
        and incomplete_inside_capture
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "predecessor_targets": predecessor_target_rows,
        "predecessor_targets_match": predecessor_targets_match,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_15_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_matches": provenance["probe_end_matches"],
        "status": (
            "EXACT_182635_TO_182673_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_182635_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_182635_CODE_BOUNDARY_PROVEN",
        "predecessor_target_status": "EXACT_182624_18261A_PREDECESSOR_TARGET_BYTES_PROVEN",
        "internal_branch_status": "EXACT_18266A_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN",
        "external_branch_status": "EXACT_18267A_TARGET_DECODED_OUTSIDE_CAPTURE",
        "terminal_status": "EXACT_RET_AT_182669_PROVEN",
        "continuation_status": "INCOMPLETE_MOV_BYTE_AT_182673_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_182635_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "NONE_IN_PREFIX",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_16_provenance(pe: PE) -> dict:
    """Capture canonical bytes from 0x182673 through exact boundary 0x1826B3."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_15_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_LEN
    )
    overlap = probe[:len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_OVERLAP_BYTES)]
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_182635_TO_182673_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
    )
    overlap_matches = (
        overlap == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_LEN
        and overlap_matches
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_182673_TO_1826B3_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182673_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "R271_INCOMPLETE_MOV_BYTE_START",
        "function_entry_status": "UNRESOLVED_AT_182673_18267A_182690",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_16_prefix_proof(pe: PE) -> dict:
    """Exact-decode the complete 0x182673..0x1826B3 bounded window."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_16_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva,
            "asm": asm,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def near_jcc_target(rva: int) -> int | None:
        raw = pe.bytes_at_rva(rva, 6)
        if len(raw) >= 6 and raw[0] == 0x0F and 0x80 <= raw[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_BRANCHES:
        decoded_target_rva = near_jcc_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix": (
                GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_RVA
                <= expected_target_rva
                < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_END_RVA
            ),
        })
        branch_targets_match = branch_targets_match and matches

    predecessor_target_is_boundary = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PREDECESSOR_TARGET_RVA
        in instruction_starts
    )
    padding = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PADDING_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PADDING_BYTES),
    )
    padding_matches = (
        padding == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PADDING_BYTES
    )
    ret_matches = all(
        rva in instruction_starts and pe.bytes_at_rva(rva, 1) == b"\xc3"
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_RET_RVAS
    )
    next_code_boundary = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_NEXT_CODE_RVA
        in instruction_starts
    )
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_182673_TO_1826B3_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(
        rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    capture_end_is_instruction_boundary = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_END_RVA
    )
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and capture_end_is_instruction_boundary
        and branch_targets_match
        and predecessor_target_is_boundary
        and padding_matches
        and ret_matches
        and next_code_boundary
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PROBE_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "predecessor_target_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PREDECESSOR_TARGET_RVA,
        "predecessor_target_is_boundary": predecessor_target_is_boundary,
        "ret_rvas": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_RET_RVAS),
        "ret_matches": ret_matches,
        "padding_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_PADDING_RVA,
        "padding_bytes": padding.hex(" "),
        "padding_matches": padding_matches,
        "next_code_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_16_NEXT_CODE_RVA,
        "next_code_boundary": next_code_boundary,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_is_instruction_boundary": capture_end_is_instruction_boundary,
        "status": (
            "EXACT_182673_TO_1826B3_CONTROL_FLOW_PREFIX_PROVEN"
            if proven
            else "CALLEE_182673_CONTROL_FLOW_PREFIX_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_182673_MOV_BYTE_COMPLETION_PROVEN",
        "predecessor_target_status": "EXACT_18267A_PREDECESSOR_FORWARD_TARGET_BOUNDARY_PROVEN",
        "terminal_status": "EXACT_RET_AT_182679_182684_PROVEN",
        "padding_status": "EXACT_182685_TO_18268F_INT3_PADDING_PROVEN",
        "next_code_status": "EXACT_182690_NEXT_CODE_BOUNDARY_PROVEN",
        "external_branch_status": "EXACT_182724_TARGET_DECODED_OUTSIDE_CAPTURE",
        "continuation_status": "EXACT_CAPTURE_END_INSTRUCTION_BOUNDARY_1826B3",
        "function_entry_status": "UNRESOLVED_AT_182673_18267A_182690",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_TERMINALS_AND_PADDING_ONLY",
        "call_semantics": "NONE_IN_PREFIX",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_17_provenance(pe: PE) -> dict:
    """Capture exact bytes at 0x1826B3..0x1826F2; do not decode the cut tail."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_16_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_182673_TO_1826B3_CONTROL_FLOW_PREFIX_PROVEN"
        and predecessor["capture_end_is_instruction_boundary"]
        and predecessor["capture_end_rva"] == target_rva
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PROBE_LEN
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1826B3_TO_1826F3_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1826B3_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "EXACT_1826B3_PREDECESSOR_INSTRUCTION_BOUNDARY",
        "function_entry_status": "UNRESOLVED_AT_1826B3_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_17_prefix_proof(pe: PE) -> dict:
    """Exact-decode the complete 0x1826B3..0x1826F0 prefix only."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_17_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva,
            "asm": asm,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def branch_target(rva: int) -> int | None:
        raw2 = pe.bytes_at_rva(rva, 2)
        if len(raw2) >= 2 and (raw2[0] == 0xEB or 0x70 <= raw2[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw2, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        raw5 = pe.bytes_at_rva(rva, 5)
        if len(raw5) >= 5 and raw5[0] == 0xE9:
            rel = struct.unpack_from("<i", raw5, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_BRANCHES:
        decoded_target_rva = branch_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix": target_within_prefix,
            "target_is_instruction_boundary": target_is_boundary,
        })
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INCOMPLETE_BYTES
    )
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1826B3_TO_1826F3_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(
        rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PREFIX_END_RVA
    )
    incomplete_inside_capture = (
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INCOMPLETE_RVA
        < provenance["probe_end_rva"]
    )
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and incomplete_matches
        and incomplete_inside_capture
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_17_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_matches": provenance["probe_end_matches"],
        "status": (
            "EXACT_1826B3_TO_1826F1_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_1826B3_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_1826B3_CODE_BOUNDARY_PROVEN",
        "internal_branch_status": "EXACT_1826C4_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN",
        "external_branch_status": "EXACT_182724_18270B_182700_188DE9_TARGETS_DECODED_OUTSIDE_CAPTURE",
        "continuation_status": "INCOMPLETE_FNSTCW_AT_1826F1_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_1826B3_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "NONE_IN_PREFIX",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_18_provenance(pe: PE) -> dict:
    """Capture exact canonical bytes from the cut 0x1826F1 FNSTCW start."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_17_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PROBE_LEN
    )
    overlap = probe[:len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_OVERLAP_BYTES)]
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_1826B3_TO_1826F1_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
    )
    overlap_matches = (
        overlap == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PROBE_LEN
        and overlap_matches
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1826F1_TO_182731_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1826F1_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "R271_INCOMPLETE_FNSTCW_START",
        "function_entry_status": "UNRESOLVED_AT_1826F1_182700_18270B_182724",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_18_prefix_proof(pe: PE) -> dict:
    """Exact-decode complete instructions through 0x18272F; stop before wait-prefixed FSTCW."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_18_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva,
            "asm": asm,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def rel_target(rva: int) -> int | None:
        raw2 = pe.bytes_at_rva(rva, 2)
        if len(raw2) >= 2 and (raw2[0] == 0xEB or 0x70 <= raw2[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw2, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        raw5 = pe.bytes_at_rva(rva, 5)
        if len(raw5) >= 5 and raw5[0] in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", raw5, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_BRANCHES:
        decoded_target_rva = rel_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix": target_within_prefix,
            "target_is_instruction_boundary": target_is_boundary,
        })
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    call_rows = []
    calls_match = True
    internal_call_targets_on_boundaries = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_CALLS:
        decoded_target_rva = rel_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        call_rows.append({
            "call_rva": call_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix": target_within_prefix,
            "target_is_instruction_boundary": target_is_boundary,
        })
        calls_match = calls_match and matches
        if target_within_prefix:
            internal_call_targets_on_boundaries = (
                internal_call_targets_on_boundaries and target_is_boundary
            )

    predecessor_targets_on_boundaries = all(
        rva in instruction_starts
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PREDECESSOR_TARGET_RVAS
    )
    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INCOMPLETE_BYTES
    )
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1826F1_TO_182731_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(
        rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PREFIX_END_RVA
    )
    ret_matches = (
        0x00182723 in instruction_starts and pe.bytes_at_rva(0x00182723, 1) == b"\xc3"
    )
    post_ret_boundary = 0x00182724 in instruction_starts
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and calls_match
        and internal_call_targets_on_boundaries
        and predecessor_targets_on_boundaries
        and incomplete_matches
        and ret_matches
        and post_ret_boundary
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "calls": call_rows,
        "calls_match": calls_match,
        "internal_call_targets_on_boundaries": internal_call_targets_on_boundaries,
        "predecessor_target_rvas": list(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_PREDECESSOR_TARGET_RVAS),
        "predecessor_targets_on_boundaries": predecessor_targets_on_boundaries,
        "ret_matches": ret_matches,
        "post_ret_boundary": post_ret_boundary,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_18_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "status": (
            "EXACT_1826F1_TO_182730_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_1826F1_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_1826F1_FNSTCW_COMPLETION_PROVEN",
        "predecessor_target_status": "EXACT_182700_18270B_182724_FORWARD_TARGET_BOUNDARIES_PROVEN",
        "internal_call_status": "EXACT_18271B_TO_18272D_INTERNAL_CALL_BOUNDARY_PROVEN",
        "terminal_status": "EXACT_RET_182723_AND_POST_RET_182724_BOUNDARY_PROVEN",
        "external_target_status": "EXACT_188DD0_188905_TARGETS_DECODED_OUTSIDE_CAPTURE",
        "continuation_status": "INCOMPLETE_WAIT_PREFIX_AT_182730_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_1826F1_182700_18270B_182724_18272D",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_CALLS_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_19_provenance(pe: PE) -> dict:
    """Capture canonical bytes from 0x182730 with fail-closed predecessor overlap."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_18_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PROBE_LEN
    )
    overlap = probe[:len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_OVERLAP_BYTES)]
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_1826F1_TO_182730_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
    )
    overlap_matches = (
        overlap == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PROBE_LEN
        and overlap_matches
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_182730_TO_182770_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182730_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "R271_INCOMPLETE_WAIT_PREFIX_START",
        "function_entry_status": "UNRESOLVED_AT_182730_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_19_prefix_proof(pe: PE) -> dict:
    """Decode complete instructions from 0x182730; stop before cut MOV at 0x18276D."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_19_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({"rva": rva, "asm": asm, "expected_bytes": expected.hex(" "),
                     "actual_bytes": actual.hex(" "), "bytes_match": actual == expected})
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def rel_target(rva: int) -> int | None:
        raw2 = pe.bytes_at_rva(rva, 2)
        if len(raw2) >= 2 and 0x70 <= raw2[0] <= 0x7F:
            rel = struct.unpack_from("<b", raw2, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        raw5 = pe.bytes_at_rva(rva, 5)
        if len(raw5) >= 5 and raw5[0] == 0xE8:
            rel = struct.unpack_from("<i", raw5, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        raw6 = pe.bytes_at_rva(rva, 6)
        if len(raw6) >= 6 and raw6[0] == 0x0F and 0x80 <= raw6[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw6, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_BRANCHES:
        decoded_target_rva = rel_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append({"branch_rva": branch_rva, "expected_target_rva": expected_target_rva,
                            "decoded_target_rva": decoded_target_rva, "matches": matches,
                            "target_within_prefix": target_within_prefix,
                            "target_is_instruction_boundary": target_is_boundary})
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = internal_branch_targets_on_boundaries and target_is_boundary

    call_rows = []
    calls_match = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_CALLS:
        decoded_target_rva = rel_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        call_rows.append({"call_rva": call_rva, "expected_target_rva": expected_target_rva,
                          "decoded_target_rva": decoded_target_rva, "matches": matches})
        calls_match = calls_match and matches

    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INCOMPLETE_BYTES),
    )
    incomplete_matches = incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INCOMPLETE_BYTES
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_182730_TO_182770_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"] and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"])
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PREFIX_END_RVA
    proven = bool(
        predecessor_exact and start_boundary_proven and contiguous and all_bytes_match
        and prefix_end_matches and branch_targets_match and internal_branch_targets_on_boundaries
        and calls_match and incomplete_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_PREFIX_END_RVA,
        "predecessor_status": provenance["status"], "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven, "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match, "instructions": rows,
        "instruction_count": len(rows), "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows, "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "calls": call_rows, "calls_match": calls_match,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_19_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "), "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "status": (
            "EXACT_182730_TO_18276D_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven else "CALLEE_182730_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_182730_WAIT_PREFIXED_FSTCW_COMPLETION_PROVEN",
        "internal_branch_status": "EXACT_182741_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN",
        "external_target_status": "EXACT_1827F4_1827F0_182863_1888D5_188905_TARGETS_DECODED_OUTSIDE_CAPTURE",
        "continuation_status": "INCOMPLETE_MOV_CL_AT_18276D_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_182730_182741_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_CALLS_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_20_provenance(pe: PE) -> dict:
    """Capture canonical bytes from 0x18276D with fail-closed predecessor overlap."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_19_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PROBE_LEN
    )
    overlap = probe[:len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_OVERLAP_BYTES)]
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_182730_TO_18276D_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
    )
    overlap_matches = (
        overlap == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PROBE_LEN
        and overlap_matches
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_18276D_TO_1827AD_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_18276D_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "R271_INCOMPLETE_MOV_CL_START",
        "function_entry_status": "UNRESOLVED_AT_18276D_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_20_prefix_proof(pe: PE) -> dict:
    """Decode complete instructions from 0x18276D; stop at cut near-Jcc opcode."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_20_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({"rva": rva, "asm": asm, "expected_bytes": expected.hex(" "),
                     "actual_bytes": actual.hex(" "), "bytes_match": actual == expected})
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def rel_target(rva: int) -> int | None:
        raw2 = pe.bytes_at_rva(rva, 2)
        if len(raw2) >= 2 and 0x70 <= raw2[0] <= 0x7F:
            rel = struct.unpack_from("<b", raw2, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        raw5 = pe.bytes_at_rva(rva, 5)
        if len(raw5) >= 5 and raw5[0] in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", raw5, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        raw6 = pe.bytes_at_rva(rva, 6)
        if len(raw6) >= 6 and raw6[0] == 0x0F and 0x80 <= raw6[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw6, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_BRANCHES:
        decoded_target_rva = rel_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append({"branch_rva": branch_rva, "expected_target_rva": expected_target_rva,
                            "decoded_target_rva": decoded_target_rva, "matches": matches,
                            "target_within_prefix": target_within_prefix,
                            "target_is_instruction_boundary": target_is_boundary})
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = internal_branch_targets_on_boundaries and target_is_boundary

    call_rows = []
    calls_match = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_CALLS:
        decoded_target_rva = rel_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        call_rows.append({"call_rva": call_rva, "expected_target_rva": expected_target_rva,
                          "decoded_target_rva": decoded_target_rva, "matches": matches})
        calls_match = calls_match and matches

    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INCOMPLETE_BYTES),
    )
    incomplete_matches = incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INCOMPLETE_BYTES
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_18276D_TO_1827AD_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"] and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"])
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PREFIX_END_RVA
    proven = bool(
        predecessor_exact and start_boundary_proven and contiguous and all_bytes_match
        and prefix_end_matches and branch_targets_match and internal_branch_targets_on_boundaries
        and calls_match and incomplete_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_PREFIX_END_RVA,
        "predecessor_status": provenance["status"], "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven, "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match, "instructions": rows,
        "instruction_count": len(rows), "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows, "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "calls": call_rows, "calls_match": calls_match,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_20_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "), "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "status": (
            "EXACT_18276D_TO_1827AC_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven else "CALLEE_18276D_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_18276D_MOV_CL_COMPLETION_PROVEN",
        "internal_branch_status": "EXACT_182788_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN",
        "external_target_status": "EXACT_1828CD_1888C0_18895E_1889A9_TARGETS_DECODED_OUTSIDE_CAPTURE",
        "continuation_status": "INCOMPLETE_NEAR_JCC_OPCODE_AT_1827AC_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_18276D_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_CALLS_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }




def collect_guarded_gf_target_c_helper_1_third_callee_continuation_21_provenance(pe: PE) -> dict:
    """Capture exact canonical bytes from the cut 0x1827AC near-Jcc opcode."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_20_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PROBE_LEN
    )
    overlap = probe[:len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_OVERLAP_BYTES)]
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_18276D_TO_1827AC_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
    )
    overlap_matches = (
        overlap == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PROBE_LEN
        and overlap_matches
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1827AC_TO_1827EC_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1827AC_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "R278_INCOMPLETE_NEAR_JCC_OPCODE_START",
        "function_entry_status": "UNRESOLVED_AT_1827AC_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_21_prefix_proof(pe: PE) -> dict:
    """Exact-decode complete instructions in the R278 raw window; preserve cut MOV raw-only."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_21_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva,
            "asm": asm,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def rel_target(rva: int) -> int | None:
        raw2 = pe.bytes_at_rva(rva, 2)
        if len(raw2) >= 2 and (raw2[0] == 0xEB or 0x70 <= raw2[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw2, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        raw5 = pe.bytes_at_rva(rva, 5)
        if len(raw5) >= 5 and raw5[0] in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", raw5, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        raw6 = pe.bytes_at_rva(rva, 6)
        if len(raw6) >= 6 and raw6[0] == 0x0F and 0x80 <= raw6[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw6, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_BRANCHES:
        decoded_target_rva = rel_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix": target_within_prefix,
            "target_is_instruction_boundary": target_is_boundary,
        })
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = internal_branch_targets_on_boundaries and target_is_boundary

    call_rows = []
    calls_match = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_CALLS:
        decoded_target_rva = rel_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        call_rows.append({
            "call_rva": call_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
        })
        calls_match = calls_match and matches

    predecessor_rows = []
    predecessor_targets_match = True
    for rva, expected in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PREDECESSOR_TARGET_BYTES:
        actual = pe.bytes_at_rva(rva, len(expected))
        matches = actual == expected
        predecessor_rows.append({
            "rva": rva,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "matches": matches,
        })
        predecessor_targets_match = predecessor_targets_match and matches

    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INCOMPLETE_BYTES),
    )
    incomplete_matches = incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INCOMPLETE_BYTES
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1827AC_TO_1827EC_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(
        rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PREFIX_END_RVA
    )
    ret_matches = (
        0x001827C3 in instruction_starts and pe.bytes_at_rva(0x001827C3, 1) == b"\xc3"
    )
    post_ret_boundary = 0x001827C4 in instruction_starts
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and calls_match
        and predecessor_targets_match
        and incomplete_matches
        and ret_matches
        and post_ret_boundary
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "calls": call_rows,
        "calls_match": calls_match,
        "predecessor_targets": predecessor_rows,
        "predecessor_targets_match": predecessor_targets_match,
        "ret_matches": ret_matches,
        "post_ret_boundary": post_ret_boundary,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_21_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "status": (
            "EXACT_1827AC_TO_1827E9_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_1827AC_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_1827AC_NEAR_JCC_COMPLETION_PROVEN",
        "internal_branch_status": "EXACT_1827D7_INTERNAL_BRANCH_TARGET_BOUNDARY_PROVEN",
        "predecessor_target_status": "EXACT_1827A5_PREDECESSOR_BACKEDGE_TARGET_BYTES_PROVEN",
        "terminal_status": "EXACT_RET_1827C3_AND_POST_RET_1827C4_BOUNDARY_PROVEN",
        "external_target_status": "EXACT_18895E_18280A_188860_188905_TARGETS_DECODED_OUTSIDE_CAPTURE",
        "continuation_status": "INCOMPLETE_MOV_EAX_IMM32_AT_1827E9_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_1827AC_1827C4_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_CALLS_TERMINAL_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_22_provenance(pe: PE) -> dict:
    """Capture the next canonical bytes from the cut 0x1827E9 MOV EAX,imm32."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_21_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PROBE_LEN
    )
    overlap = probe[:len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_OVERLAP_BYTES)]
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_1827AC_TO_1827E9_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
    )
    overlap_matches = (
        overlap == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PROBE_LEN
        and overlap_matches
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1827E9_TO_182829_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1827E9_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "PREDECESSOR_INCOMPLETE_MOV_EAX_IMM32_START",
        "function_entry_status": "UNRESOLVED_AT_1827E9_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_22_prefix_proof(pe: PE) -> dict:
    """Exact-decode the complete 0x1827E9 prefix; preserve the cut TEST opcode raw-only."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_22_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva,
            "asm": asm,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def rel_target(rva: int) -> int | None:
        raw2 = pe.bytes_at_rva(rva, 2)
        if len(raw2) >= 2 and (raw2[0] == 0xEB or 0x70 <= raw2[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw2, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        raw5 = pe.bytes_at_rva(rva, 5)
        if len(raw5) >= 5 and raw5[0] in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", raw5, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        raw6 = pe.bytes_at_rva(rva, 6)
        if len(raw6) >= 6 and raw6[0] == 0x0F and 0x80 <= raw6[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw6, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        return None

    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INCOMPLETE_BYTES
    )
    known_boundaries = set(instruction_starts)
    known_boundaries.add(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INCOMPLETE_RVA)

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_BRANCHES:
        decoded_target_rva = rel_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix_or_edge = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_RVA
            <= expected_target_rva
            <= GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in known_boundaries
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix_or_edge": target_within_prefix_or_edge,
            "target_is_instruction_or_capture_boundary": target_is_boundary,
        })
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix_or_edge:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    call_rows = []
    calls_match = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_CALLS:
        decoded_target_rva = rel_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        call_rows.append({
            "call_rva": call_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
        })
        calls_match = calls_match and matches

    predecessor_rows = []
    predecessor_targets_match = True
    for rva, expected in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PREDECESSOR_TARGET_BYTES:
        actual = pe.bytes_at_rva(rva, len(expected))
        matches = actual == expected
        predecessor_rows.append({
            "rva": rva,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "matches": matches,
        })
        predecessor_targets_match = predecessor_targets_match and matches

    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1827E9_TO_182829_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(
        rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PREFIX_END_RVA
    )
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and calls_match
        and predecessor_targets_match
        and incomplete_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "calls": call_rows,
        "calls_match": calls_match,
        "predecessor_targets": predecessor_rows,
        "predecessor_targets_match": predecessor_targets_match,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_22_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "status": (
            "EXACT_1827E9_TO_182828_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_1827E9_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_1827E9_MOV_EAX_IMM32_COMPLETION_PROVEN",
        "internal_branch_status": "EXACT_18280A_AND_182828_BRANCH_TARGET_BOUNDARIES_PROVEN",
        "predecessor_target_status": "EXACT_1827A5_1827C4_1827E0_PREDECESSOR_TARGET_BYTES_PROVEN",
        "external_target_status": "EXACT_188905_CALL_TARGET_DECODED_OUTSIDE_CAPTURE",
        "continuation_status": "INCOMPLETE_TEST_OPCODE_AT_182828_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_1827E9_182828_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_CALL_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }



def collect_guarded_gf_target_c_helper_1_third_callee_continuation_23_provenance(pe: PE) -> dict:
    """Capture canonical bytes from the cut 0x182828 TEST opcode without semantic promotion."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_22_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PROBE_LEN
    )
    overlap = probe[:len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_OVERLAP_BYTES)]
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_1827E9_TO_182828_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
    )
    overlap_matches = (
        overlap == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PROBE_LEN
        and overlap_matches
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_182828_TO_182868_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182828_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "PREDECESSOR_INCOMPLETE_TEST_OPCODE_START",
        "function_entry_status": "UNRESOLVED_AT_182828_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_23_prefix_proof(pe: PE) -> dict:
    """Exact-decode the complete 0x182828 prefix; preserve the cut AND opcode raw-only."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_23_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva,
            "asm": asm,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def rel_target(rva: int) -> int | None:
        raw2 = pe.bytes_at_rva(rva, 2)
        if len(raw2) >= 2 and (raw2[0] == 0xEB or 0x70 <= raw2[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw2, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        raw5 = pe.bytes_at_rva(rva, 5)
        if len(raw5) >= 5 and raw5[0] in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", raw5, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        raw6 = pe.bytes_at_rva(rva, 6)
        if len(raw6) >= 6 and raw6[0] == 0x0F and 0x80 <= raw6[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw6, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        return None

    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INCOMPLETE_BYTES
    )
    known_boundaries = set(instruction_starts)
    known_boundaries.add(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INCOMPLETE_RVA)

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_BRANCHES:
        decoded_target_rva = rel_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix_or_edge = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_RVA
            <= expected_target_rva
            <= GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in known_boundaries
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix_or_edge": target_within_prefix_or_edge,
            "target_is_instruction_or_capture_boundary": target_is_boundary,
        })
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix_or_edge:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    call_rows = []
    calls_match = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_CALLS:
        decoded_target_rva = rel_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        call_rows.append({
            "call_rva": call_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
        })
        calls_match = calls_match and matches

    predecessor_rows = []
    predecessor_targets_match = True
    for rva, expected in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PREDECESSOR_TARGET_BYTES:
        actual = pe.bytes_at_rva(rva, len(expected))
        matches = actual == expected
        predecessor_rows.append({
            "rva": rva,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "matches": matches,
        })
        predecessor_targets_match = predecessor_targets_match and matches

    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_182828_TO_182868_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(
        rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PREFIX_END_RVA
    )
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and calls_match
        and predecessor_targets_match
        and incomplete_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "calls": call_rows,
        "calls_match": calls_match,
        "predecessor_targets": predecessor_rows,
        "predecessor_targets_match": predecessor_targets_match,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_23_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "status": (
            "EXACT_182828_TO_182867_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_182828_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_182828_TEST_ECX_ECX_COMPLETION_PROVEN",
        "internal_branch_status": "NO_INTERNAL_BRANCH_TARGETS_IN_182828_TO_182867_PREFIX",
        "predecessor_target_status": "EXACT_1827A5_1827E7_PREDECESSOR_TARGET_BYTES_PROVEN",
        "external_target_status": "EXACT_18895E_BRANCH_AND_189B95_CALL_TARGETS_DECODED_OUTSIDE_CAPTURE",
        "continuation_status": "INCOMPLETE_AND_EAX_IMM32_AT_182867_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_182828_182867_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_CALL_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_24_provenance(pe: PE) -> dict:
    """Capture canonical bytes from the cut 0x182867 AND EAX,imm32 without semantic promotion."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_23_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PROBE_LEN
    )
    overlap = probe[:len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_OVERLAP_BYTES)]
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_182828_TO_182867_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
        and predecessor["incomplete_rva"] == target_rva
        and predecessor["incomplete_matches"]
    )
    overlap_matches = (
        overlap == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_OVERLAP_BYTES
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PROBE_LEN
        and overlap_matches
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "overlap_bytes": overlap.hex(" "),
        "overlap_matches": overlap_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_182867_TO_1828A7_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_182867_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "PREDECESSOR_INCOMPLETE_AND_EAX_IMM32_START",
        "function_entry_status": "UNRESOLVED_AT_182867_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_OVERLAP_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_24_prefix_proof(pe: PE) -> dict:
    """Exact-decode the complete 0x182867..0x1828A7 canonical capture."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_24_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva,
            "asm": asm,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def rel_target(rva: int) -> int | None:
        raw2 = pe.bytes_at_rva(rva, 2)
        if len(raw2) >= 2 and (raw2[0] == 0xEB or 0x70 <= raw2[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw2, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        raw5 = pe.bytes_at_rva(rva, 5)
        if len(raw5) >= 5 and raw5[0] in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", raw5, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        raw6 = pe.bytes_at_rva(rva, 6)
        if len(raw6) >= 6 and raw6[0] == 0x0F and 0x80 <= raw6[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw6, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    internal_branch_targets_on_boundaries = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_BRANCHES:
        decoded_target_rva = rel_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        target_within_prefix = (
            GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_RVA
            <= expected_target_rva
            < GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PREFIX_END_RVA
        )
        target_is_boundary = decoded_target_rva in instruction_starts
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
            "target_within_prefix": target_within_prefix,
            "target_is_instruction_boundary": target_is_boundary,
        })
        branch_targets_match = branch_targets_match and matches
        if target_within_prefix:
            internal_branch_targets_on_boundaries = (
                internal_branch_targets_on_boundaries and target_is_boundary
            )

    call_rows = []
    calls_match = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_CALLS:
        decoded_target_rva = rel_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        call_rows.append({
            "call_rva": call_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
        })
        calls_match = calls_match and matches

    predecessor_rows = []
    predecessor_targets_match = True
    for rva, expected in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PREDECESSOR_TARGET_BYTES:
        actual = pe.bytes_at_rva(rva, len(expected))
        matches = actual == expected
        predecessor_rows.append({
            "rva": rva,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "matches": matches,
        })
        predecessor_targets_match = predecessor_targets_match and matches

    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_182867_TO_1828A7_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["overlap_matches"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(
        rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PREFIX_END_RVA
        and provenance["probe_end_rva"] == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PREFIX_END_RVA
    )
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and internal_branch_targets_on_boundaries
        and calls_match
        and predecessor_targets_match
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_24_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "internal_branch_targets_on_boundaries": internal_branch_targets_on_boundaries,
        "calls": call_rows,
        "calls_match": calls_match,
        "predecessor_targets": predecessor_rows,
        "predecessor_targets_match": predecessor_targets_match,
        "capture_end_rva": provenance["probe_end_rva"],
        "capture_end_is_instruction_boundary": prefix_end_matches,
        "status": (
            "EXACT_182867_TO_1828A7_CONTROL_FLOW_PREFIX_PROVEN"
            if proven
            else "CALLEE_182867_CONTROL_FLOW_PREFIX_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_182867_AND_EAX_IMM32_COMPLETION_PROVEN",
        "internal_branch_status": "NO_INTERNAL_BRANCH_TARGETS_IN_182867_TO_1828A7_PREFIX",
        "predecessor_target_status": "EXACT_18276D_PREDECESSOR_BRANCH_TARGET_BYTES_PROVEN",
        "external_target_status": "EXACT_1828A9_1828B3_1828C4_BRANCH_AND_1828F2_CALL_TARGETS_DECODED_OUTSIDE_CAPTURE",
        "continuation_status": "EXACT_CAPTURE_END_INSTRUCTION_BOUNDARY_1828A7",
        "function_entry_status": "UNRESOLVED_AT_182867_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_CALL_AND_CAPTURE_BOUNDARY_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_25_provenance(pe: PE) -> dict:
    """Capture fresh canonical bytes from the exact F15 boundary at 0x1828A7."""

    predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_24_prefix_proof(pe)
    target_rva = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_RVA
    target_section = next(
        (section.name for section in pe.sections if section.contains_rva(target_rva)),
        "",
    )
    probe = pe.bytes_at_rva(
        target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PROBE_LEN
    )
    inbound = collect_raw_inbound_rel32_candidates(pe, target_rva)
    outbound = collect_raw_rel32_call_candidates(
        pe, target_rva, GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PROBE_LEN
    )
    predecessor_exact = (
        predecessor["status"] == "EXACT_182867_TO_1828A7_CONTROL_FLOW_PREFIX_PROVEN"
        and predecessor["prefix_end_rva"] == target_rva
        and predecessor["capture_end_is_instruction_boundary"]
    )
    probe_end_matches = (
        target_rva + len(probe)
        == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PROBE_END_RVA
    )
    captured = bool(
        predecessor_exact
        and target_section == ".text"
        and len(probe) == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PROBE_LEN
        and probe_end_matches
    )
    return {
        "target_rva": target_rva,
        "target_section": target_section,
        "predecessor_status": predecessor["status"],
        "predecessor_exact": predecessor_exact,
        "predecessor_end_rva": predecessor["prefix_end_rva"],
        "predecessor_end_is_instruction_boundary": predecessor["capture_end_is_instruction_boundary"],
        "probe_len": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PROBE_LEN,
        "probe_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PROBE_END_RVA,
        "probe_end_matches": probe_end_matches,
        "first_16_bytes": probe[:16].hex(" "),
        "last_16_bytes": probe[-16:].hex(" "),
        "bytes": probe.hex(" "),
        "raw_inbound_rel32_candidates": inbound,
        "raw_outbound_rel32_candidates": outbound,
        "status": (
            "EXACT_EXE_1828A7_TO_1828E7_PROVENANCE_CAPTURED"
            if captured
            else "CALLEE_1828A7_CONTINUATION_PROVENANCE_CAPTURE_FAILED"
        ),
        "start_boundary_status": "EXACT_PREDECESSOR_INSTRUCTION_BOUNDARY_1828A7",
        "function_entry_status": "UNRESOLVED_AT_1828A7_AND_FORWARD_BYTES",
        "semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY",
        "call_semantics": "UNRESOLVED",
        "ownership_effect": "NONE",
        "continuation_scope": "RAW_BYTES_AND_REL32_CENSUS_ONLY",
    }


def collect_guarded_gf_target_c_helper_1_third_callee_continuation_25_prefix_proof(pe: PE) -> dict:
    """Exact-decode 0x1828A7..0x1828E2 and preserve the cut FLD raw-only."""

    provenance = collect_guarded_gf_target_c_helper_1_third_callee_continuation_25_provenance(pe)
    expected_next = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_RVA
    contiguous = True
    rows: list[dict] = []
    instruction_starts: set[int] = set()
    for rva, hex_bytes, asm in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INSTRUCTIONS:
        expected = bytes.fromhex(hex_bytes)
        if rva != expected_next:
            contiguous = False
        actual = pe.bytes_at_rva(rva, len(expected))
        rows.append({
            "rva": rva,
            "asm": asm,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "bytes_match": actual == expected,
        })
        instruction_starts.add(rva)
        expected_next = rva + len(expected)

    def rel_target(rva: int) -> int | None:
        raw2 = pe.bytes_at_rva(rva, 2)
        if len(raw2) >= 2 and (raw2[0] == 0xEB or 0x70 <= raw2[0] <= 0x7F):
            rel = struct.unpack_from("<b", raw2, 1)[0]
            return (rva + 2 + rel) & 0xFFFFFFFF
        raw5 = pe.bytes_at_rva(rva, 5)
        if len(raw5) >= 5 and raw5[0] in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", raw5, 1)[0]
            return (rva + 5 + rel) & 0xFFFFFFFF
        raw6 = pe.bytes_at_rva(rva, 6)
        if len(raw6) >= 6 and raw6[0] == 0x0F and 0x80 <= raw6[1] <= 0x8F:
            rel = struct.unpack_from("<i", raw6, 2)[0]
            return (rva + 6 + rel) & 0xFFFFFFFF
        return None

    branch_rows = []
    branch_targets_match = True
    for branch_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_BRANCHES:
        decoded_target_rva = rel_target(branch_rva)
        matches = decoded_target_rva == expected_target_rva
        branch_rows.append({
            "branch_rva": branch_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
        })
        branch_targets_match = branch_targets_match and matches

    call_rows = []
    calls_match = True
    for call_rva, expected_target_rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_CALLS:
        decoded_target_rva = rel_target(call_rva)
        matches = decoded_target_rva == expected_target_rva
        call_rows.append({
            "call_rva": call_rva,
            "expected_target_rva": expected_target_rva,
            "decoded_target_rva": decoded_target_rva,
            "matches": matches,
        })
        calls_match = calls_match and matches

    expected_raw_calls = set(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_CALLS)
    observed_raw_calls = {
        (item["call_rva"], item["target_rva"])
        for item in provenance["raw_outbound_rel32_candidates"]
    }
    raw_call_census_matches = observed_raw_calls == expected_raw_calls

    predecessor_rows = []
    predecessor_targets_match = True
    for rva, expected in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PREDECESSOR_TARGET_BYTES:
        actual = pe.bytes_at_rva(rva, len(expected))
        matches = actual == expected
        predecessor_rows.append({
            "rva": rva,
            "expected_bytes": expected.hex(" "),
            "actual_bytes": actual.hex(" "),
            "matches": matches,
        })
        predecessor_targets_match = predecessor_targets_match and matches

    resolved_forward_targets = [
        {
            "rva": rva,
            "is_instruction_boundary": rva in instruction_starts,
        }
        for rva in GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_RESOLVED_FORWARD_TARGET_RVAS
    ]
    resolved_forward_targets_on_boundaries = all(
        item["is_instruction_boundary"] for item in resolved_forward_targets
    )

    incomplete = pe.bytes_at_rva(
        GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INCOMPLETE_RVA,
        len(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INCOMPLETE_BYTES),
    )
    incomplete_matches = (
        incomplete == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INCOMPLETE_BYTES
    )
    predecessor_exact = (
        provenance["status"] == "EXACT_EXE_1828A7_TO_1828E7_PROVENANCE_CAPTURED"
        and provenance["predecessor_exact"]
        and provenance["probe_end_matches"]
    )
    start_boundary_proven = bool(
        rows and rows[0]["rva"] == provenance["target_rva"] and rows[0]["bytes_match"]
    )
    all_bytes_match = all(row["bytes_match"] for row in rows)
    prefix_end_matches = (
        expected_next == GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PREFIX_END_RVA
    )
    proven = bool(
        predecessor_exact
        and start_boundary_proven
        and contiguous
        and all_bytes_match
        and prefix_end_matches
        and branch_targets_match
        and calls_match
        and raw_call_census_matches
        and predecessor_targets_match
        and resolved_forward_targets_on_boundaries
        and incomplete_matches
    )
    return {
        "start_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_RVA,
        "prefix_end_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_PREFIX_END_RVA,
        "predecessor_status": provenance["status"],
        "predecessor_exact": predecessor_exact,
        "start_boundary_proven": start_boundary_proven,
        "layout_contiguous": contiguous,
        "all_instruction_bytes_match": all_bytes_match,
        "instructions": rows,
        "instruction_count": len(rows),
        "prefix_end_matches": prefix_end_matches,
        "branches": branch_rows,
        "branch_targets_match": branch_targets_match,
        "calls": call_rows,
        "calls_match": calls_match,
        "raw_call_census_matches": raw_call_census_matches,
        "raw_call_candidates": provenance["raw_outbound_rel32_candidates"],
        "predecessor_targets": predecessor_rows,
        "predecessor_targets_match": predecessor_targets_match,
        "resolved_forward_targets": resolved_forward_targets,
        "resolved_forward_targets_on_boundaries": resolved_forward_targets_on_boundaries,
        "incomplete_rva": GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_25_INCOMPLETE_RVA,
        "incomplete_bytes": incomplete.hex(" "),
        "incomplete_matches": incomplete_matches,
        "capture_end_rva": provenance["probe_end_rva"],
        "status": (
            "EXACT_1828A7_TO_1828E2_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"
            if proven
            else "CALLEE_1828A7_CONTROL_FLOW_CAPTURE_EDGE_PROOF_FAILED"
        ),
        "start_boundary_status": "EXACT_PREDECESSOR_INSTRUCTION_BOUNDARY_1828A7",
        "resolved_forward_target_status": "EXACT_1828A9_1828B3_1828C4_1828CD_TARGET_BOUNDARIES_PROVEN",
        "external_target_status": "EXACT_1827A5_18277A_BRANCH_AND_1828F2_CALL_TARGETS_PROVEN",
        "continuation_status": "INCOMPLETE_FLD_TBYTE_DISP32_AT_1828E2_CAPTURE_END",
        "function_entry_status": "UNRESOLVED_AT_1828A7_1828E2_AND_FORWARD_TARGETS",
        "semantic_effect": "BOUNDED_CONTROL_FLOW_CALL_AND_CAPTURE_EDGE_ONLY",
        "call_semantics": "UNRESOLVED",
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

    proof_c = report["guarded_gf_target_c_alignment_proof"]
    proof_c_rows = "<br>".join(
        f"{hexrva(row['rva'])} {row['actual_bytes']} {row['asm']} "
        f"[{'match' if row['bytes_match'] else 'MISMATCH'}]"
        for row in proof_c["instructions"]
    )
    lines += [
        "",
        "## Guarded GF target C first-CALL instruction-boundary proof",
        "",
        "Exact-byte/manual-decode proof only. This establishes the 0x65997 E8 as "
        "an instruction boundary in the reviewed prefix anchored at 0x65970. "
        "Later calls at 0x659AC/0x659C1 and semantic ownership remain unresolved.",
        "",
        f"- Status: {proof_c['status']}",
        f"- Entry anchor: {hexrva(proof_c['entry_rva'])}",
        f"- Function-start guess: {hexrva(proof_c['function_start_guess_rva'])}",
        f"- Layout contiguous: {proof_c['layout_contiguous']}",
        f"- All instruction bytes match: {proof_c['all_instruction_bytes_match']}",
        f"- Aligned first CALL: {hexrva(proof_c['aligned_call_rva'])} -> "
        f"{hexrva(proof_c['decoded_call_target_rva'])} "
        f"({proof_c['call_target_section'] or '-'})",
        f"- Semantic effect: {proof_c['semantic_effect']}",
        f"- Remaining raw calls: "
        f"{', '.join(hexrva(rva) for rva in proof_c['remaining_raw_call_rvas'])}",
        f"- Reviewed prefix: {proof_c_rows}",
    ]

    proof_c2 = report["guarded_gf_target_c_second_call_alignment_proof"]
    proof_c2_rows = "<br>".join(
        f"{hexrva(row['rva'])} {row['actual_bytes']} {row['asm']} "
        f"[{'match' if row['bytes_match'] else 'MISMATCH'}]"
        for row in proof_c2["instructions"]
    )
    lines += [
        "",
        "## Guarded GF target C second-CALL instruction-boundary proof",
        "",
        "Exact-byte/manual-decode continuation only. This anchors the reviewed "
        "layout at the end of the proven first-call prefix and establishes the "
        "0x659AC E8 as an instruction boundary resolving to 0x28320 in .text. "
        "The later raw call at 0x659C1 and semantic ownership remain unresolved.",
        "",
        f"- Status: {proof_c2['status']}",
        f"- Entry anchor: {hexrva(proof_c2['entry_rva'])}",
        f"- First-call status: {proof_c2['first_call_status']}",
        f"- Continuation anchor: {hexrva(proof_c2['anchor_rva'])}",
        f"- Anchor matches first prefix end: "
        f"{proof_c2['anchor_matches_first_prefix_end']}",
        f"- Layout contiguous: {proof_c2['layout_contiguous']}",
        f"- All instruction bytes match: "
        f"{proof_c2['all_instruction_bytes_match']}",
        f"- Aligned second CALL: {hexrva(proof_c2['aligned_call_rva'])} -> "
        f"{hexrva(proof_c2['decoded_call_target_rva'])} "
        f"({proof_c2['call_target_section'] or '-'})",
        f"- Semantic effect: {proof_c2['semantic_effect']}",
        f"- Remaining raw calls: "
        f"{', '.join(hexrva(rva) for rva in proof_c2['remaining_raw_call_rvas'])}",
        f"- Reviewed continuation: {proof_c2_rows}",
    ]

    proof_c3 = report["guarded_gf_target_c_third_call_alignment_proof"]
    proof_c3_rows = "<br>".join(
        f"{hexrva(row['rva'])} {row['actual_bytes']} {row['asm']} "
        f"[{'match' if row['bytes_match'] else 'MISMATCH'}]"
        for row in proof_c3["instructions"]
    )
    lines += [
        "",
        "## Guarded GF target C third-CALL instruction-boundary proof",
        "",
        "Exact-byte/manual-decode continuation only. This anchors the reviewed "
        "layout at the end of the proven second CALL and establishes the "
        "0x659C1 E8 as an instruction boundary resolving to 0x28800 in .text. "
        "Helper semantics and semantic ownership remain unresolved.",
        "",
        f"- Status: {proof_c3['status']}",
        f"- Entry anchor: {hexrva(proof_c3['entry_rva'])}",
        f"- Second-call status: {proof_c3['second_call_status']}",
        f"- Continuation anchor: {hexrva(proof_c3['anchor_rva'])}",
        f"- Anchor matches second CALL end: "
        f"{proof_c3['anchor_matches_second_call_end']}",
        f"- Raw candidate carried forward: "
        f"{proof_c3['raw_candidate_carried_forward']}",
        f"- Layout contiguous: {proof_c3['layout_contiguous']}",
        f"- All instruction bytes match: "
        f"{proof_c3['all_instruction_bytes_match']}",
        f"- Aligned third CALL: {hexrva(proof_c3['aligned_call_rva'])} -> "
        f"{hexrva(proof_c3['decoded_call_target_rva'])} "
        f"({proof_c3['call_target_section'] or '-'})",
        f"- Semantic effect: {proof_c3['semantic_effect']}",
        f"- Remaining raw calls: "
        f"{', '.join(hexrva(rva) for rva in proof_c3['remaining_raw_call_rvas']) or 'none'}",
        f"- Reviewed continuation: {proof_c3_rows}",
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
        "guarded_gf_target_c_alignment_proof": collect_guarded_gf_target_c_alignment_proof(pe),
        "guarded_gf_target_c_second_call_alignment_proof": collect_guarded_gf_target_c_second_call_alignment_proof(pe),
        "guarded_gf_target_c_third_call_alignment_proof": collect_guarded_gf_target_c_third_call_alignment_proof(pe),
        "guarded_gf_target_c_helper_1_provenance": collect_guarded_gf_target_c_helper_1_provenance(pe),
        "guarded_gf_target_c_helper_1_prefix_proof": collect_guarded_gf_target_c_helper_1_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_success_prefix_proof": collect_guarded_gf_target_c_helper_1_success_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_first_callee_provenance": collect_guarded_gf_target_c_helper_1_first_callee_provenance(pe),
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
        "guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof": collect_guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof": collect_guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_12_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_12_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_13_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_13_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_13_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_13_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_14_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_14_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_14_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_14_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_15_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_15_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_15_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_15_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_16_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_16_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_16_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_16_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_17_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_17_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_17_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_17_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_18_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_18_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_18_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_18_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_19_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_19_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_19_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_19_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_20_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_20_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_20_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_20_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_21_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_21_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_21_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_21_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_22_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_22_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_22_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_22_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_23_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_23_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_23_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_23_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_24_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_24_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_24_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_24_prefix_proof(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_25_provenance": collect_guarded_gf_target_c_helper_1_third_callee_continuation_25_provenance(pe),
        "guarded_gf_target_c_helper_1_third_callee_continuation_25_prefix_proof": collect_guarded_gf_target_c_helper_1_third_callee_continuation_25_prefix_proof(pe),
        "guarded_gf_target_c_tail_probe": {
            "rva": GF_TARGET_C_TAIL_PROBE_RVA,
            "length": GF_TARGET_C_TAIL_PROBE_LEN,
            "bytes": pe.bytes_at_rva(GF_TARGET_C_TAIL_PROBE_RVA, GF_TARGET_C_TAIL_PROBE_LEN).hex(" "),
        },
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
            f"bytes64={item['bytes64']} "
            f"bytes96={item['bytes96']}"
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
    alignment_c = report["guarded_gf_target_c_alignment_proof"]
    print(
        f"gf_target_alignment=0x{alignment_c['entry_rva']:08X} "
        f"status={alignment_c['status']} "
        f"start_guess={hexrva(alignment_c['function_start_guess_rva'])} "
        f"layout_contiguous={alignment_c['layout_contiguous']} "
        f"bytes_match={alignment_c['all_instruction_bytes_match']} "
        f"call=0x{alignment_c['aligned_call_rva']:08X} "
        f"target={hexrva(alignment_c['decoded_call_target_rva'])} "
        f"target_section={alignment_c['call_target_section'] or 'none'} "
        f"semantic_effect={alignment_c['semantic_effect']} "
        f"remaining_raw_calls={','.join(hexrva(rva) for rva in alignment_c['remaining_raw_call_rvas'])}"
    )
    alignment_c2 = report["guarded_gf_target_c_second_call_alignment_proof"]
    print(
        f"gf_target_second_alignment=0x{alignment_c2['entry_rva']:08X} "
        f"status={alignment_c2['status']} "
        f"start_guess={hexrva(alignment_c2['function_start_guess_rva'])} "
        f"first_status={alignment_c2['first_call_status']} "
        f"anchor={hexrva(alignment_c2['anchor_rva'])} "
        f"anchor_matches={alignment_c2['anchor_matches_first_prefix_end']} "
        f"layout_contiguous={alignment_c2['layout_contiguous']} "
        f"bytes_match={alignment_c2['all_instruction_bytes_match']} "
        f"call=0x{alignment_c2['aligned_call_rva']:08X} "
        f"target={hexrva(alignment_c2['decoded_call_target_rva'])} "
        f"target_section={alignment_c2['call_target_section'] or 'none'} "
        f"semantic_effect={alignment_c2['semantic_effect']} "
        f"remaining_raw_calls={','.join(hexrva(rva) for rva in alignment_c2['remaining_raw_call_rvas'])}"
    )
    alignment_c3 = report["guarded_gf_target_c_third_call_alignment_proof"]
    print(
        f"gf_target_third_alignment=0x{alignment_c3['entry_rva']:08X} "
        f"status={alignment_c3['status']} "
        f"start_guess={hexrva(alignment_c3['function_start_guess_rva'])} "
        f"second_status={alignment_c3['second_call_status']} "
        f"anchor={hexrva(alignment_c3['anchor_rva'])} "
        f"anchor_matches={alignment_c3['anchor_matches_second_call_end']} "
        f"raw_candidate={alignment_c3['raw_candidate_carried_forward']} "
        f"layout_contiguous={alignment_c3['layout_contiguous']} "
        f"bytes_match={alignment_c3['all_instruction_bytes_match']} "
        f"call=0x{alignment_c3['aligned_call_rva']:08X} "
        f"target={hexrva(alignment_c3['decoded_call_target_rva'])} "
        f"target_section={alignment_c3['call_target_section'] or 'none'} "
        f"semantic_effect={alignment_c3['semantic_effect']} "
        f"remaining_raw_calls={','.join(hexrva(rva) for rva in alignment_c3['remaining_raw_call_rvas']) or 'none'}"
    )
    helper_1 = report["guarded_gf_target_c_helper_1_provenance"]
    helper_1_inbound = ",".join(
        f"0x{call['call_rva']:08X}:{call['semantic']}/{call['space_policy']}"
        for call in helper_1["raw_inbound_rel32_candidates"]
    ) or "none"
    helper_1_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1=0x{helper_1['target_rva']:08X} "
        f"section={helper_1['target_section'] or 'none'} "
        f"start_guess={hexrva(helper_1['function_start_guess_rva'])} "
        f"probe_len={helper_1['probe_len']} "
        f"inbound_raw={len(helper_1['raw_inbound_rel32_candidates'])} "
        f"inbound={helper_1_inbound} "
        f"outbound_raw={len(helper_1['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_outbound} "
        f"semantic_effect={helper_1['semantic_effect']} "
        f"bytes={helper_1['bytes']}"
    )
    helper_1_proof = report["guarded_gf_target_c_helper_1_prefix_proof"]
    print(
        f"gf_target_c_helper_1_prefix=0x{helper_1_proof['target_rva']:08X} "
        f"status={helper_1_proof['status']} "
        f"caller=0x{helper_1_proof['caller_rva']:08X} "
        f"caller_status={helper_1_proof['caller_status']} "
        f"caller_link={helper_1_proof['caller_link_present']} "
        f"layout_contiguous={helper_1_proof['layout_contiguous']} "
        f"bytes_match={helper_1_proof['all_instruction_bytes_match']} "
        f"high_range=0x{helper_1_proof['selector_high_word_range_min_inclusive']:X}-"
        f"0x{helper_1_proof['selector_high_word_range_max_exclusive']:X} "
        f"low_mask=0x{helper_1_proof['selector_low_word_mask']:X} "
        f"table_base=0x{helper_1_proof['table_base']:08X} "
        f"range_fallback={hexrva(helper_1_proof['range_low_target'])}/"
        f"{hexrva(helper_1_proof['range_high_target'])} "
        f"miss_cleanup={hexrva(helper_1_proof['miss_cleanup_rva'])} "
        f"miss_return={helper_1_proof['miss_return_value']} "
        f"success_continuation={hexrva(helper_1_proof['success_continuation_rva'])} "
        f"semantic_effect={helper_1_proof['semantic_effect']} "
        f"full_semantics={helper_1_proof['full_helper_semantics']} "
        f"ownership_effect={helper_1_proof['ownership_effect']}"
    )
    helper_1_success = report["guarded_gf_target_c_helper_1_success_prefix_proof"]
    print(
        f"gf_target_c_helper_1_success=0x{helper_1_success['success_start_rva']:08X} "
        f"status={helper_1_success['status']} "
        f"lookup_status={helper_1_success['lookup_prefix_status']} "
        f"layout_contiguous={helper_1_success['layout_contiguous']} "
        f"bytes_match={helper_1_success['all_instruction_bytes_match']} "
        f"first_call=0x{helper_1_success['first_call_rva']:08X}->"
        f"{hexrva(helper_1_success['first_call_target_rva'])}:"
        f"{helper_1_success['first_call_target_section'] or 'none'} "
        f"failure_branch=0x{helper_1_success['failure_branch_rva']:08X}->"
        f"{hexrva(helper_1_success['failure_target_rva'])} "
        f"failure_condition={helper_1_success['failure_condition']} "
        f"second_call=0x{helper_1_success['second_call_rva']:08X}->"
        f"{hexrva(helper_1_success['second_call_target_rva'])}:"
        f"{helper_1_success['second_call_target_section'] or 'none'} "
        f"outbound_candidates={helper_1_success['outbound_candidates_match']} "
        f"semantic_effect={helper_1_success['semantic_effect']} "
        f"callee_semantics={helper_1_success['callee_semantics']} "
        f"ownership_effect={helper_1_success['ownership_effect']}"
    )
    helper_1_callee = report["guarded_gf_target_c_helper_1_first_callee_provenance"]
    helper_1_callee_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_callee["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_first_callee=0x{helper_1_callee['target_rva']:08X} "
        f"status={helper_1_callee['status']} "
        f"predecessor_status={helper_1_callee['predecessor_status']} "
        f"caller=0x{helper_1_callee['caller_rva']:08X} "
        f"caller_link={helper_1_callee['caller_link_present']} "
        f"section={helper_1_callee['target_section'] or 'none'} "
        f"start_guess={hexrva(helper_1_callee['function_start_guess_rva'])} "
        f"probe_len={helper_1_callee['probe_len']} "
        f"inbound_raw={len(helper_1_callee['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_callee['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_callee_outbound} "
        f"semantic_effect={helper_1_callee['semantic_effect']} "
        f"ownership_effect={helper_1_callee['ownership_effect']} "
        f"bytes={helper_1_callee['bytes']}"
    )
    helper_1_callee_prefix = report["guarded_gf_target_c_helper_1_first_callee_prefix_proof"]
    print(
        f"gf_target_c_helper_1_first_callee_prefix=0x{helper_1_callee_prefix['target_rva']:08X} "
        f"status={helper_1_callee_prefix['status']} "
        f"predecessor_status={helper_1_callee_prefix['predecessor_status']} "
        f"caller=0x{helper_1_callee_prefix['caller_rva']:08X} "
        f"caller_link={helper_1_callee_prefix['caller_link_present']} "
        f"section={helper_1_callee_prefix['target_section'] or 'none'} "
        f"end={hexrva(helper_1_callee_prefix['prefix_end_rva'])} "
        f"layout_contiguous={helper_1_callee_prefix['layout_contiguous']} "
        f"bytes_match={helper_1_callee_prefix['all_instruction_bytes_match']} "
        f"count_table=0x{helper_1_callee_prefix['count_table']:08X} "
        f"cursor_table=0x{helper_1_callee_prefix['cursor_table']:08X} "
        f"pool_base=0x{helper_1_callee_prefix['pool_base']:08X} "
        f"pool_stride=0x{helper_1_callee_prefix['pool_stride']:X} "
        f"slot_stride=0x{helper_1_callee_prefix['slot_stride']:X} "
        f"ring_size=0x{helper_1_callee_prefix['ring_size']:X} "
        f"count_ok={hexrva(helper_1_callee_prefix['count_ok_target_rva'])} "
        f"cursor_nonwrap={hexrva(helper_1_callee_prefix['cursor_nonwrap_target_rva'])} "
        f"occupied_retry={hexrva(helper_1_callee_prefix['occupied_retry_target_rva'])} "
        f"branch_targets={helper_1_callee_prefix['branch_targets_match']} "
        f"failure_return={helper_1_callee_prefix['failure_return_value']} "
        f"slot_mark={helper_1_callee_prefix['slot_mark_value']} "
        f"semantic_effect={helper_1_callee_prefix['semantic_effect']} "
        f"full_semantics={helper_1_callee_prefix['full_callee_semantics']} "
        f"ownership_effect={helper_1_callee_prefix['ownership_effect']}"
    )
    helper_1_callee_cont = report["guarded_gf_target_c_helper_1_first_callee_continuation_provenance"]
    helper_1_callee_cont_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_callee_cont["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_first_callee_continuation=0x{helper_1_callee_cont['target_rva']:08X} "
        f"status={helper_1_callee_cont['status']} "
        f"predecessor_status={helper_1_callee_cont['predecessor_status']} "
        f"predecessor_end={hexrva(helper_1_callee_cont['predecessor_end_rva'])} "
        f"predecessor_exact={helper_1_callee_cont['predecessor_exact']} "
        f"section={helper_1_callee_cont['target_section'] or 'none'} "
        f"probe_len={helper_1_callee_cont['probe_len']} "
        f"inbound_raw={len(helper_1_callee_cont['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_callee_cont['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_callee_cont_outbound} "
        f"semantic_effect={helper_1_callee_cont['semantic_effect']} "
        f"full_semantics={helper_1_callee_cont['full_callee_semantics']} "
        f"ownership_effect={helper_1_callee_cont['ownership_effect']} "
        f"bytes={helper_1_callee_cont['bytes']}"
    )
    helper_1_callee_terminal = report["guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof"]
    print(
        f"gf_target_c_helper_1_first_callee_terminal=0x{helper_1_callee_terminal['target_rva']:08X} "
        f"status={helper_1_callee_terminal['status']} "
        f"predecessor_status={helper_1_callee_terminal['predecessor_status']} "
        f"predecessor_exact={helper_1_callee_terminal['predecessor_exact']} "
        f"section={helper_1_callee_terminal['target_section'] or 'none'} "
        f"layout_contiguous={helper_1_callee_terminal['layout_contiguous']} "
        f"bytes_match={helper_1_callee_terminal['all_instruction_bytes_match']} "
        f"ret=0x{helper_1_callee_terminal['terminal_ret_rva']:08X} "
        f"terminal_end={hexrva(helper_1_callee_terminal['terminal_end_rva'])} "
        f"padding=0x{helper_1_callee_terminal['padding_start_rva']:08X}-"
        f"0x{helper_1_callee_terminal['padding_end_rva'] - 1:08X}:"
        f"{helper_1_callee_terminal['padding_bytes']} "
        f"padding_matches={helper_1_callee_terminal['padding_matches']} "
        f"next_code={hexrva(helper_1_callee_terminal['next_code_rva'])} "
        f"next_anchor={helper_1_callee_terminal['next_code_anchor']} "
        f"next_anchor_matches={helper_1_callee_terminal['next_code_anchor_matches']} "
        f"semantic_effect={helper_1_callee_terminal['semantic_effect']} "
        f"full_semantics={helper_1_callee_terminal['full_callee_semantics']} "
        f"next_code_semantics={helper_1_callee_terminal['next_code_semantics']} "
        f"ownership_effect={helper_1_callee_terminal['ownership_effect']}"
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

    helper_1_third_cont_3 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance"
    ]
    helper_1_third_cont_3_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_third_cont_3["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_3=0x{helper_1_third_cont_3['target_rva']:08X} "
        f"status={helper_1_third_cont_3['status']} "
        f"predecessor={helper_1_third_cont_3['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_3['predecessor_exact']} "
        f"predecessor_leave=0x{helper_1_third_cont_3['predecessor_leave_rva']:08X}:"
        f"{helper_1_third_cont_3['predecessor_leave_bytes']} "
        f"section={helper_1_third_cont_3['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_3['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_3['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_3['probe_end_matches']} "
        f"first_byte={helper_1_third_cont_3['first_byte']} "
        f"first16={helper_1_third_cont_3['first_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_3['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_3['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_3_outbound} "
        f"function_entry={helper_1_third_cont_3['function_entry_status']} "
        f"terminal_status={helper_1_third_cont_3['terminal_status']} "
        f"semantic_effect={helper_1_third_cont_3['semantic_effect']} "
        f"ownership_effect={helper_1_third_cont_3['ownership_effect']} "
        f"scope={helper_1_third_cont_3['continuation_scope']} "
        f"bytes={helper_1_third_cont_3['bytes']}"
    )

    helper_1_third_terminal = report[
        "guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_terminal="
        f"0x{helper_1_third_terminal['terminal_leave_rva']:08X} "
        f"status={helper_1_third_terminal['status']} "
        f"predecessor={helper_1_third_terminal['predecessor_status']} "
        f"predecessor_exact={helper_1_third_terminal['predecessor_exact']} "
        f"provenance={helper_1_third_terminal['provenance_status']} "
        f"provenance_exact={helper_1_third_terminal['provenance_exact']} "
        f"terminal=0x{helper_1_third_terminal['terminal_leave_rva']:08X}:"
        f"{helper_1_third_terminal['terminal_actual_bytes']} "
        f"terminal_match={helper_1_third_terminal['terminal_matches']} "
        f"ret=0x{helper_1_third_terminal['terminal_ret_rva']:08X} "
        f"ret_matches_provenance={helper_1_third_terminal['ret_matches_provenance']} "
        f"next=0x{helper_1_third_terminal['next_instruction_rva']:08X}:"
        f"{helper_1_third_terminal['next_instruction_actual_bytes']} "
        f"next_match={helper_1_third_terminal['next_instruction_matches']} "
        f"next_contiguous={helper_1_third_terminal['next_boundary_contiguous']} "
        f"call_target={hexrva(helper_1_third_terminal['decoded_call_target_rva'])} "
        f"call_match={helper_1_third_terminal['call_target_matches']} "
        f"raw_call={helper_1_third_terminal['raw_call_candidate_present']} "
        f"terminal_status={helper_1_third_terminal['terminal_status']} "
        f"next_boundary_status={helper_1_third_terminal['next_boundary_status']} "
        f"function_entry={helper_1_third_terminal['function_entry_status']} "
        f"semantic_effect={helper_1_third_terminal['semantic_effect']} "
        f"call_semantics={helper_1_third_terminal['call_semantics']} "
        f"ownership_effect={helper_1_third_terminal['ownership_effect']}"
    )

    helper_1_third_post_terminal = report[
        "guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof"
    ]
    helper_1_third_post_terminal_branches = ",".join(
        f"0x{row['branch_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"boundary={row['target_is_instruction_boundary']}:"
        f"match={row['matches']}"
        for row in helper_1_third_post_terminal["branches"]
    ) or "none"
    helper_1_third_post_terminal_calls = ",".join(
        f"0x{row['call_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:raw={row['raw_candidate_present']}"
        for row in helper_1_third_post_terminal["calls"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_post_terminal="
        f"0x{helper_1_third_post_terminal['start_rva']:08X} "
        f"status={helper_1_third_post_terminal['status']} "
        f"predecessor={helper_1_third_post_terminal['predecessor_status']} "
        f"predecessor_exact={helper_1_third_post_terminal['predecessor_exact']} "
        f"provenance={helper_1_third_post_terminal['provenance_status']} "
        f"provenance_exact={helper_1_third_post_terminal['provenance_exact']} "
        f"layout_contiguous={helper_1_third_post_terminal['layout_contiguous']} "
        f"bytes_match={helper_1_third_post_terminal['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_post_terminal['instruction_count']} "
        f"prefix_end=0x{helper_1_third_post_terminal['prefix_end_rva']:08X} "
        f"prefix_end_match={helper_1_third_post_terminal['prefix_end_matches']} "
        f"ret=0x{helper_1_third_post_terminal['ret_rva']:08X} "
        f"ret_match={helper_1_third_post_terminal['ret_matches']} "
        f"branches={helper_1_third_post_terminal_branches} "
        f"branch_targets_match={helper_1_third_post_terminal['branch_targets_match']} "
        f"branch_targets_boundary={helper_1_third_post_terminal['branch_targets_are_instruction_boundaries']} "
        f"calls={helper_1_third_post_terminal_calls} "
        f"call_targets_match={helper_1_third_post_terminal['call_targets_match']} "
        f"raw_calls={helper_1_third_post_terminal['raw_call_candidates_present']} "
        f"padding=0x{helper_1_third_post_terminal['padding_rva']:08X}:"
        f"{helper_1_third_post_terminal['padding_bytes']} "
        f"padding_match={helper_1_third_post_terminal['padding_matches']} "
        f"padding_end=0x{helper_1_third_post_terminal['padding_end_rva']:08X} "
        f"next_code=0x{helper_1_third_post_terminal['next_code_rva']:08X} "
        f"next_boundary_match={helper_1_third_post_terminal['next_code_boundary_matches']} "
        f"terminal_status={helper_1_third_post_terminal['terminal_status']} "
        f"padding_status={helper_1_third_post_terminal['padding_status']} "
        f"next_boundary_status={helper_1_third_post_terminal['next_boundary_status']} "
        f"function_entry={helper_1_third_post_terminal['function_entry_status']} "
        f"semantic_effect={helper_1_third_post_terminal['semantic_effect']} "
        f"call_semantics={helper_1_third_post_terminal['call_semantics']} "
        f"ownership_effect={helper_1_third_post_terminal['ownership_effect']}"
    )

    helper_1_third_next_block = report[
        "guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof"
    ]
    helper_1_third_next_block_calls = ",".join(
        f"0x{row['call_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:raw={row['raw_candidate_present']}"
        for row in helper_1_third_next_block["calls"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_next_block="
        f"0x{helper_1_third_next_block['start_rva']:08X} "
        f"status={helper_1_third_next_block['status']} "
        f"predecessor={helper_1_third_next_block['predecessor_status']} "
        f"predecessor_exact={helper_1_third_next_block['predecessor_exact']} "
        f"provenance={helper_1_third_next_block['provenance_status']} "
        f"provenance_exact={helper_1_third_next_block['provenance_exact']} "
        f"layout_contiguous={helper_1_third_next_block['layout_contiguous']} "
        f"bytes_match={helper_1_third_next_block['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_next_block['instruction_count']} "
        f"prefix_end=0x{helper_1_third_next_block['prefix_end_rva']:08X} "
        f"prefix_end_match={helper_1_third_next_block['prefix_end_matches']} "
        f"ret=0x{helper_1_third_next_block['ret_rva']:08X} "
        f"ret_match={helper_1_third_next_block['ret_matches']} "
        f"calls={helper_1_third_next_block_calls} "
        f"call_targets_match={helper_1_third_next_block['call_targets_match']} "
        f"raw_calls={helper_1_third_next_block['raw_call_candidates_present']} "
        f"next=0x{helper_1_third_next_block['next_instruction_rva']:08X} "
        f"next_boundary_match={helper_1_third_next_block['next_instruction_boundary_matches']} "
        f"terminal_status={helper_1_third_next_block['terminal_status']} "
        f"next_boundary_status={helper_1_third_next_block['next_boundary_status']} "
        f"function_entry={helper_1_third_next_block['function_entry_status']} "
        f"semantic_effect={helper_1_third_next_block['semantic_effect']} "
        f"call_semantics={helper_1_third_next_block['call_semantics']} "
        f"ownership_effect={helper_1_third_next_block['ownership_effect']}"
    )

    helper_1_third_next_cont = report[
        "guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof"
    ]
    helper_1_third_next_cont_branches = ",".join(
        f"0x{row['branch_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:"
        f"captured={row['target_within_captured_window']}:"
        f"boundary={row['target_is_proven_instruction_boundary']}"
        for row in helper_1_third_next_cont["branches"]
    ) or "none"
    helper_1_third_next_cont_calls = ",".join(
        f"0x{row['call_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:raw={row['raw_candidate_present']}"
        for row in helper_1_third_next_cont["calls"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_next_continuation="
        f"0x{helper_1_third_next_cont['start_rva']:08X} "
        f"status={helper_1_third_next_cont['status']} "
        f"predecessor={helper_1_third_next_cont['predecessor_status']} "
        f"predecessor_exact={helper_1_third_next_cont['predecessor_exact']} "
        f"provenance={helper_1_third_next_cont['provenance_status']} "
        f"provenance_exact={helper_1_third_next_cont['provenance_exact']} "
        f"layout_contiguous={helper_1_third_next_cont['layout_contiguous']} "
        f"bytes_match={helper_1_third_next_cont['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_next_cont['instruction_count']} "
        f"end=0x{helper_1_third_next_cont['end_rva']:08X} "
        f"end_match={helper_1_third_next_cont['end_matches_probe']} "
        f"incoming=0x{helper_1_third_next_cont['incoming_call_rva']:08X}->"
        f"0x{helper_1_third_next_cont['incoming_target_rva']:08X} "
        f"incoming_proven={helper_1_third_next_cont['incoming_call_proven']} "
        f"incoming_boundary={helper_1_third_next_cont['incoming_target_is_instruction_boundary']} "
        f"branches={helper_1_third_next_cont_branches} "
        f"branch_targets_match={helper_1_third_next_cont['branch_targets_match']} "
        f"calls={helper_1_third_next_cont_calls} "
        f"call_targets_match={helper_1_third_next_cont['call_targets_match']} "
        f"raw_calls={helper_1_third_next_cont['raw_call_candidates_present']} "
        f"incoming_status={helper_1_third_next_cont['incoming_target_status']} "
        f"forward_target_status={helper_1_third_next_cont['forward_target_status']} "
        f"function_entry={helper_1_third_next_cont['function_entry_status']} "
        f"semantic_effect={helper_1_third_next_cont['semantic_effect']} "
        f"call_semantics={helper_1_third_next_cont['call_semantics']} "
        f"ownership_effect={helper_1_third_next_cont['ownership_effect']} "
        f"continuation={helper_1_third_next_cont['continuation_status']}"
    )

    helper_1_third_cont_4 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance"
    ]
    helper_1_third_cont_4_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_third_cont_4["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_4="
        f"0x{helper_1_third_cont_4['target_rva']:08X} "
        f"status={helper_1_third_cont_4['status']} "
        f"predecessor={helper_1_third_cont_4['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_4['predecessor_exact']} "
        f"section={helper_1_third_cont_4['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_4['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_4['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_4['probe_end_matches']} "
        f"first_byte={helper_1_third_cont_4['first_byte']} "
        f"first16={helper_1_third_cont_4['first_16_bytes']} "
        f"last16={helper_1_third_cont_4['last_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_4['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_4['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_4_outbound} "
        f"start_boundary={helper_1_third_cont_4['start_boundary_status']} "
        f"end_target={helper_1_third_cont_4['end_target_status']} "
        f"function_entry={helper_1_third_cont_4['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_4['semantic_effect']} "
        f"ownership_effect={helper_1_third_cont_4['ownership_effect']} "
        f"scope={helper_1_third_cont_4['continuation_scope']} "
        f"bytes={helper_1_third_cont_4['bytes']}"
    )

    helper_1_third_cont_4_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof"
    ]
    helper_1_third_cont_4_branches = ",".join(
        f"0x{row['branch_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:"
        f"within={row['target_within_window']}:"
        f"boundary={row['target_is_instruction_boundary']}"
        for row in helper_1_third_cont_4_proof["branches"]
    ) or "none"
    helper_1_third_cont_4_calls = ",".join(
        f"0x{row['call_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:raw={row['raw_candidate_present']}"
        for row in helper_1_third_cont_4_proof["calls"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_4_proof="
        f"0x{helper_1_third_cont_4_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_4_proof['status']} "
        f"predecessor={helper_1_third_cont_4_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_4_proof['predecessor_exact']} "
        f"provenance={helper_1_third_cont_4_proof['provenance_status']} "
        f"provenance_exact={helper_1_third_cont_4_proof['provenance_exact']} "
        f"layout_contiguous={helper_1_third_cont_4_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_4_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_4_proof['instruction_count']} "
        f"end=0x{helper_1_third_cont_4_proof['end_rva']:08X} "
        f"end_match={helper_1_third_cont_4_proof['end_matches']} "
        f"incoming=0x{helper_1_third_cont_4_proof['incoming_branch_rva']:08X}->"
        f"0x{helper_1_third_cont_4_proof['incoming_target_rva']:08X} "
        f"incoming_boundary={helper_1_third_cont_4_proof['incoming_target_is_instruction_boundary']} "
        f"branches={helper_1_third_cont_4_branches} "
        f"branch_targets_match={helper_1_third_cont_4_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_4_proof['internal_branch_targets_on_boundaries']} "
        f"calls={helper_1_third_cont_4_calls} "
        f"call_targets_match={helper_1_third_cont_4_proof['call_targets_match']} "
        f"raw_calls={helper_1_third_cont_4_proof['raw_call_candidates_present']} "
        f"incoming_status={helper_1_third_cont_4_proof['incoming_target_status']} "
        f"end_target_status={helper_1_third_cont_4_proof['end_target_status']} "
        f"function_entry={helper_1_third_cont_4_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_4_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_4_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_4_proof['ownership_effect']}"
    )

    helper_1_third_cont_5 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance"
    ]
    helper_1_third_cont_5_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_third_cont_5["raw_outbound_rel32_candidates"]
    ) or "none"
    helper_1_third_cont_5_targets = ",".join(
        f"0x{row['rva']:08X}:{row['first_8_bytes']}"
        for row in helper_1_third_cont_5["referenced_target_bytes"]
    )
    print(
        f"gf_target_c_helper_1_third_callee_continuation_5="
        f"0x{helper_1_third_cont_5['target_rva']:08X} "
        f"status={helper_1_third_cont_5['status']} "
        f"predecessor={helper_1_third_cont_5['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_5['predecessor_exact']} "
        f"section={helper_1_third_cont_5['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_5['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_5['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_5['probe_end_matches']} "
        f"first_byte={helper_1_third_cont_5['first_byte']} "
        f"first16={helper_1_third_cont_5['first_16_bytes']} "
        f"last16={helper_1_third_cont_5['last_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_5['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_5['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_5_outbound} "
        f"targets_in_window={helper_1_third_cont_5['referenced_targets_in_window']} "
        f"targets={helper_1_third_cont_5_targets} "
        f"start_boundary={helper_1_third_cont_5['start_boundary_status']} "
        f"target_status={helper_1_third_cont_5['referenced_target_status']} "
        f"function_entry={helper_1_third_cont_5['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_5['semantic_effect']} "
        f"ownership_effect={helper_1_third_cont_5['ownership_effect']} "
        f"scope={helper_1_third_cont_5['continuation_scope']} "
        f"bytes={helper_1_third_cont_5['bytes']}"
    )

    helper_1_third_cont_5_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof"
    ]
    helper_1_third_cont_5_branches = ",".join(
        f"0x{row['branch_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:"
        f"prior_boundary={row['target_is_predecessor_instruction_boundary']}"
        for row in helper_1_third_cont_5_proof["branches"]
    ) or "none"
    helper_1_third_cont_5_calls = ",".join(
        f"0x{row['call_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:raw={row['raw_candidate_present']}"
        for row in helper_1_third_cont_5_proof["calls"]
    ) or "none"
    helper_1_third_cont_5_refs = ",".join(
        f"{key}:{value}"
        for key, value in helper_1_third_cont_5_proof["referenced_boundaries"].items()
    )
    print(
        f"gf_target_c_helper_1_third_callee_continuation_5_proof="
        f"0x{helper_1_third_cont_5_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_5_proof['status']} "
        f"predecessor={helper_1_third_cont_5_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_5_proof['predecessor_exact']} "
        f"provenance={helper_1_third_cont_5_proof['provenance_status']} "
        f"provenance_exact={helper_1_third_cont_5_proof['provenance_exact']} "
        f"layout_contiguous={helper_1_third_cont_5_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_5_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_5_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_5_proof['prefix_end_rva']:08X} "
        f"prefix_end_match={helper_1_third_cont_5_proof['prefix_end_matches']} "
        f"ret=0x{helper_1_third_cont_5_proof['ret_rva']:08X} "
        f"ret_match={helper_1_third_cont_5_proof['ret_matches']} "
        f"padding=0x{helper_1_third_cont_5_proof['padding_rva']:08X}:"
        f"{helper_1_third_cont_5_proof['padding_bytes']} "
        f"padding_match={helper_1_third_cont_5_proof['padding_matches']} "
        f"next=0x{helper_1_third_cont_5_proof['next_code_rva']:08X}:"
        f"{helper_1_third_cont_5_proof['next_code_bytes']} "
        f"next_boundary_match={helper_1_third_cont_5_proof['next_code_boundary_matches']} "
        f"refs={helper_1_third_cont_5_refs} "
        f"refs_proven={helper_1_third_cont_5_proof['referenced_boundaries_proven']} "
        f"branches={helper_1_third_cont_5_branches} "
        f"branch_targets_match={helper_1_third_cont_5_proof['branch_targets_match']} "
        f"calls={helper_1_third_cont_5_calls} "
        f"call_targets_match={helper_1_third_cont_5_proof['call_targets_match']} "
        f"raw_calls={helper_1_third_cont_5_proof['raw_call_candidates_present']} "
        f"terminal_status={helper_1_third_cont_5_proof['terminal_status']} "
        f"padding_status={helper_1_third_cont_5_proof['padding_status']} "
        f"next_boundary_status={helper_1_third_cont_5_proof['next_boundary_status']} "
        f"function_entry={helper_1_third_cont_5_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_5_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_5_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_5_proof['ownership_effect']}"
    )

    helper_1_third_cont_5_tail = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof"
    ]
    helper_1_third_cont_5_tail_calls = ",".join(
        f"0x{row['call_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:raw={row['raw_candidate_present']}:"
        f"within={row['target_within_prefix']}:boundary={row['target_is_instruction_boundary']}"
        for row in helper_1_third_cont_5_tail["calls"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_5_tail_proof="
        f"0x{helper_1_third_cont_5_tail['start_rva']:08X} "
        f"status={helper_1_third_cont_5_tail['status']} "
        f"predecessor={helper_1_third_cont_5_tail['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_5_tail['predecessor_exact']} "
        f"provenance={helper_1_third_cont_5_tail['provenance_status']} "
        f"provenance_exact={helper_1_third_cont_5_tail['provenance_exact']} "
        f"layout_contiguous={helper_1_third_cont_5_tail['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_5_tail['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_5_tail['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_5_tail['prefix_end_rva']:08X} "
        f"prefix_end_match={helper_1_third_cont_5_tail['prefix_end_matches']} "
        f"ret=0x{helper_1_third_cont_5_tail['ret_rva']:08X}:"
        f"match={helper_1_third_cont_5_tail['ret_matches']} "
        f"next=0x{helper_1_third_cont_5_tail['next_code_rva']:08X}:"
        f"{helper_1_third_cont_5_tail['next_code_bytes']}:"
        f"boundary={helper_1_third_cont_5_tail['next_code_boundary_matches']} "
        f"calls={helper_1_third_cont_5_tail_calls} "
        f"call_targets_match={helper_1_third_cont_5_tail['call_targets_match']} "
        f"raw_calls={helper_1_third_cont_5_tail['raw_call_candidates_present']} "
        f"internal_boundaries={helper_1_third_cont_5_tail['internal_call_targets_on_boundaries']} "
        f"internal_call_boundary={helper_1_third_cont_5_tail['internal_call_boundary_proven']} "
        f"incomplete=0x{helper_1_third_cont_5_tail['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_5_tail['incomplete_bytes']}:"
        f"match={helper_1_third_cont_5_tail['incomplete_matches']} "
        f"capture_end=0x{helper_1_third_cont_5_tail['capture_end_rva']:08X}:"
        f"match={helper_1_third_cont_5_tail['capture_end_matches']} "
        f"terminal_status={helper_1_third_cont_5_tail['terminal_status']} "
        f"next_boundary_status={helper_1_third_cont_5_tail['next_boundary_status']} "
        f"internal_call_status={helper_1_third_cont_5_tail['internal_call_target_status']} "
        f"continuation={helper_1_third_cont_5_tail['continuation_status']} "
        f"function_entry={helper_1_third_cont_5_tail['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_5_tail['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_5_tail['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_5_tail['ownership_effect']}"
    )

    helper_1_third_cont_6 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance"
    ]
    helper_1_third_cont_6_outbound = ",".join(
        f"0x{call['call_rva']:08X}->0x{call['target_rva']:08X}:"
        f"{call['known_target'] or 'unknown'}:{call['target_section']}"
        for call in helper_1_third_cont_6["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_6="
        f"0x{helper_1_third_cont_6['target_rva']:08X} "
        f"status={helper_1_third_cont_6['status']} "
        f"predecessor={helper_1_third_cont_6['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_6['predecessor_exact']} "
        f"section={helper_1_third_cont_6['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_6['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_6['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_6['probe_end_matches']} "
        f"prior_capture_end=0x{helper_1_third_cont_6['prior_capture_end_rva']:08X} "
        f"extends_prior_capture={helper_1_third_cont_6['extends_prior_capture']} "
        f"overlap={helper_1_third_cont_6['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_6['overlap_matches']} "
        f"overlap_status={helper_1_third_cont_6['overlap_status']} "
        f"first16={helper_1_third_cont_6['first_16_bytes']} "
        f"last16={helper_1_third_cont_6['last_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_6['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_6['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_6_outbound} "
        f"start_boundary={helper_1_third_cont_6['start_boundary_status']} "
        f"function_entry={helper_1_third_cont_6['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_6['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_6['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_6['ownership_effect']} "
        f"scope={helper_1_third_cont_6['continuation_scope']} "
        f"bytes={helper_1_third_cont_6['bytes']}"
    )

    helper_1_third_cont_6_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof"
    ]
    helper_1_third_cont_6_branches = ",".join(
        f"0x{row['branch_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:"
        f"within={row['target_within_prefix']}:"
        f"boundary={row['target_is_instruction_boundary']}"
        for row in helper_1_third_cont_6_proof["branches"]
    ) or "none"
    helper_1_third_cont_6_calls = ",".join(
        f"0x{row['call_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:raw={row['raw_candidate_present']}"
        for row in helper_1_third_cont_6_proof["calls"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_6_proof="
        f"0x{helper_1_third_cont_6_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_6_proof['status']} "
        f"predecessor={helper_1_third_cont_6_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_6_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_6_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_6_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_6_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_6_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_6_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_6_branches} "
        f"branch_targets_match={helper_1_third_cont_6_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_6_proof['internal_branch_targets_on_boundaries']} "
        f"internal_branch={helper_1_third_cont_6_proof['internal_branch_boundary_proven']} "
        f"calls={helper_1_third_cont_6_calls} "
        f"call_targets_match={helper_1_third_cont_6_proof['call_targets_match']} "
        f"raw_calls={helper_1_third_cont_6_proof['raw_call_candidates_present']} "
        f"incomplete=0x{helper_1_third_cont_6_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_6_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_6_proof['incomplete_matches']} "
        f"capture_end=0x{helper_1_third_cont_6_proof['capture_end_rva']:08X}:"
        f"match={helper_1_third_cont_6_proof['capture_end_matches']} "
        f"start_boundary={helper_1_third_cont_6_proof['start_boundary_status']} "
        f"internal_branch_status={helper_1_third_cont_6_proof['internal_branch_target_status']} "
        f"continuation={helper_1_third_cont_6_proof['continuation_status']} "
        f"function_entry={helper_1_third_cont_6_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_6_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_6_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_6_proof['ownership_effect']}"
    )

    helper_1_third_cont_7 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance"
    ]
    helper_1_third_cont_7_outbound = ",".join(
        f"0x{item['call_rva']:08X}->0x{item['target_rva']:08X}:"
        f"{item['known_target'] or 'unknown'}:{item['target_section']}"
        for item in helper_1_third_cont_7["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_7="
        f"0x{helper_1_third_cont_7['target_rva']:08X} "
        f"status={helper_1_third_cont_7['status']} "
        f"predecessor={helper_1_third_cont_7['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_7['predecessor_exact']} "
        f"section={helper_1_third_cont_7['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_7['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_7['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_7['probe_end_matches']} "
        f"prior_capture_end=0x{helper_1_third_cont_7['prior_capture_end_rva']:08X} "
        f"extends_prior_capture={helper_1_third_cont_7['extends_prior_capture']} "
        f"overlap={helper_1_third_cont_7['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_7['overlap_matches']} "
        f"overlap_status={helper_1_third_cont_7['overlap_status']} "
        f"first16={helper_1_third_cont_7['first_16_bytes']} "
        f"last16={helper_1_third_cont_7['last_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_7['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_7['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_7_outbound} "
        f"start_boundary={helper_1_third_cont_7['start_boundary_status']} "
        f"function_entry={helper_1_third_cont_7['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_7['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_7['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_7['ownership_effect']} "
        f"scope={helper_1_third_cont_7['continuation_scope']} "
        f"bytes={helper_1_third_cont_7['bytes']}"
    )

    helper_1_third_cont_8 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance"
    ]
    helper_1_third_cont_8_outbound = ",".join(
        f"0x{item['call_rva']:08X}->0x{item['target_rva']:08X}:"
        f"{item['known_target'] or 'unknown'}:{item['target_section']}"
        for item in helper_1_third_cont_8["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_8="
        f"0x{helper_1_third_cont_8['target_rva']:08X} "
        f"status={helper_1_third_cont_8['status']} "
        f"predecessor={helper_1_third_cont_8['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_8['predecessor_exact']} "
        f"section={helper_1_third_cont_8['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_8['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_8['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_8['probe_end_matches']} "
        f"prior_capture_end=0x{helper_1_third_cont_8['prior_capture_end_rva']:08X} "
        f"extends_prior_capture={helper_1_third_cont_8['extends_prior_capture']} "
        f"overlap={helper_1_third_cont_8['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_8['overlap_matches']} "
        f"overlap_status={helper_1_third_cont_8['overlap_status']} "
        f"first16={helper_1_third_cont_8['first_16_bytes']} "
        f"last16={helper_1_third_cont_8['last_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_8['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_8['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_8_outbound} "
        f"start_boundary={helper_1_third_cont_8['start_boundary_status']} "
        f"function_entry={helper_1_third_cont_8['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_8['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_8['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_8['ownership_effect']} "
        f"scope={helper_1_third_cont_8['continuation_scope']} "
        f"bytes={helper_1_third_cont_8['bytes']}"
    )

    helper_1_third_cont_8_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof"
    ]
    helper_1_third_cont_8_branches = ",".join(
        f"0x{row['branch_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:"
        f"prev_boundary={row['predecessor_target_is_instruction_boundary']}"
        for row in helper_1_third_cont_8_proof["branches"]
    ) or "none"
    helper_1_third_cont_8_calls = ",".join(
        f"0x{row['call_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:raw={row['raw_candidate_present']}"
        for row in helper_1_third_cont_8_proof["calls"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_8_proof="
        f"0x{helper_1_third_cont_8_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_8_proof['status']} "
        f"predecessor={helper_1_third_cont_8_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_8_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_8_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_8_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_8_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_8_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_8_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_8_branches} "
        f"branch_targets_match={helper_1_third_cont_8_proof['branch_targets_match']} "
        f"predecessor_boundaries={helper_1_third_cont_8_proof['predecessor_branch_targets_on_boundaries']} "
        f"incoming_18246f={helper_1_third_cont_8_proof['incoming_18246f_boundary_proven']} "
        f"incoming_18247c={helper_1_third_cont_8_proof['incoming_18247c_boundary_proven']} "
        f"backedge_18245a={helper_1_third_cont_8_proof['backedge_18245a_boundary_proven']} "
        f"calls={helper_1_third_cont_8_calls} "
        f"call_targets_match={helper_1_third_cont_8_proof['call_targets_match']} "
        f"raw_calls={helper_1_third_cont_8_proof['raw_call_candidates_present']} "
        f"ret=0x{helper_1_third_cont_8_proof['ret_rva']:08X}:"
        f"match={helper_1_third_cont_8_proof['ret_matches']} "
        f"next=0x{helper_1_third_cont_8_proof['next_code_rva']:08X}:"
        f"boundary={helper_1_third_cont_8_proof['next_boundary_proven']} "
        f"incomplete=0x{helper_1_third_cont_8_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_8_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_8_proof['incomplete_matches']} "
        f"capture_end=0x{helper_1_third_cont_8_proof['capture_end_rva']:08X}:"
        f"match={helper_1_third_cont_8_proof['capture_end_matches']} "
        f"start_boundary={helper_1_third_cont_8_proof['start_boundary_status']} "
        f"incoming_18246f_status={helper_1_third_cont_8_proof['incoming_18246f_status']} "
        f"incoming_18247c_status={helper_1_third_cont_8_proof['incoming_18247c_status']} "
        f"backedge_status={helper_1_third_cont_8_proof['backedge_status']} "
        f"terminal_status={helper_1_third_cont_8_proof['terminal_status']} "
        f"next_boundary_status={helper_1_third_cont_8_proof['next_boundary_status']} "
        f"continuation={helper_1_third_cont_8_proof['continuation_status']} "
        f"function_entry={helper_1_third_cont_8_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_8_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_8_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_8_proof['ownership_effect']}"
    )

    helper_1_third_cont_9 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance"
    ]
    helper_1_third_cont_9_outbound = ",".join(
        f"0x{item['call_rva']:08X}->0x{item['target_rva']:08X}:"
        f"{item['known_target'] or 'unknown'}:{item['target_section']}"
        for item in helper_1_third_cont_9["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_9="
        f"0x{helper_1_third_cont_9['target_rva']:08X} "
        f"status={helper_1_third_cont_9['status']} "
        f"predecessor={helper_1_third_cont_9['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_9['predecessor_exact']} "
        f"section={helper_1_third_cont_9['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_9['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_9['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_9['probe_end_matches']} "
        f"prior_capture_end=0x{helper_1_third_cont_9['prior_capture_end_rva']:08X} "
        f"extends_prior_capture={helper_1_third_cont_9['extends_prior_capture']} "
        f"overlap={helper_1_third_cont_9['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_9['overlap_matches']} "
        f"overlap_status={helper_1_third_cont_9['overlap_status']} "
        f"first16={helper_1_third_cont_9['first_16_bytes']} "
        f"last16={helper_1_third_cont_9['last_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_9['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_9['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_9_outbound} "
        f"start_boundary={helper_1_third_cont_9['start_boundary_status']} "
        f"function_entry={helper_1_third_cont_9['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_9['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_9['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_9['ownership_effect']} "
        f"scope={helper_1_third_cont_9['continuation_scope']} "
        f"bytes={helper_1_third_cont_9['bytes']}"
    )


    helper_1_third_cont_9_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof"
    ]
    helper_1_third_cont_9_branches = ",".join(
        f"0x{row['branch_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:"
        f"within={row['target_within_prefix']}:"
        f"boundary={row['target_is_instruction_boundary']}"
        for row in helper_1_third_cont_9_proof["branches"]
    ) or "none"
    helper_1_third_cont_9_calls = ",".join(
        f"0x{row['call_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:raw={row['raw_candidate_present']}"
        for row in helper_1_third_cont_9_proof["calls"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_9_proof="
        f"0x{helper_1_third_cont_9_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_9_proof['status']} "
        f"predecessor={helper_1_third_cont_9_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_9_proof['predecessor_exact']} "
        f"start_boundary_proven={helper_1_third_cont_9_proof['start_boundary_proven']} "
        f"layout_contiguous={helper_1_third_cont_9_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_9_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_9_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_9_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_9_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_9_branches} "
        f"branch_targets_match={helper_1_third_cont_9_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_9_proof['internal_branch_targets_on_boundaries']} "
        f"incoming_1824b0={helper_1_third_cont_9_proof['incoming_1824b0_boundary_proven']} "
        f"calls={helper_1_third_cont_9_calls} "
        f"call_targets_match={helper_1_third_cont_9_proof['call_targets_match']} "
        f"raw_calls={helper_1_third_cont_9_proof['raw_call_candidates_present']} "
        f"rets={','.join(hexrva(rva) for rva in helper_1_third_cont_9_proof['ret_rvas'])}:"
        f"match={helper_1_third_cont_9_proof['ret_matches']} "
        f"post_ret={','.join(hexrva(rva) for rva in helper_1_third_cont_9_proof['post_ret_code_rvas'])}:"
        f"boundary={helper_1_third_cont_9_proof['post_ret_boundaries_proven']} "
        f"incomplete=0x{helper_1_third_cont_9_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_9_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_9_proof['incomplete_matches']} "
        f"capture_end=0x{helper_1_third_cont_9_proof['capture_end_rva']:08X}:"
        f"match={helper_1_third_cont_9_proof['capture_end_matches']} "
        f"start_boundary={helper_1_third_cont_9_proof['start_boundary_status']} "
        f"incoming_1824b0_status={helper_1_third_cont_9_proof['incoming_1824b0_status']} "
        f"internal_branch_status={helper_1_third_cont_9_proof['internal_branch_status']} "
        f"external_branch_status={helper_1_third_cont_9_proof['external_branch_status']} "
        f"terminal_status={helper_1_third_cont_9_proof['terminal_status']} "
        f"post_terminal_boundary_status={helper_1_third_cont_9_proof['post_terminal_boundary_status']} "
        f"continuation={helper_1_third_cont_9_proof['continuation_status']} "
        f"function_entry={helper_1_third_cont_9_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_9_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_9_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_9_proof['ownership_effect']}"
    )

    helper_1_third_cont_10 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance"
    ]
    helper_1_third_cont_10_outbound = ",".join(
        f"0x{item['call_rva']:08X}->0x{item['target_rva']:08X}:"
        f"{item['known_target'] or 'unknown'}:{item['target_section']}"
        for item in helper_1_third_cont_10["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_10="
        f"0x{helper_1_third_cont_10['target_rva']:08X} "
        f"status={helper_1_third_cont_10['status']} "
        f"predecessor={helper_1_third_cont_10['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_10['predecessor_exact']} "
        f"section={helper_1_third_cont_10['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_10['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_10['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_10['probe_end_matches']} "
        f"prior_capture_end=0x{helper_1_third_cont_10['prior_capture_end_rva']:08X} "
        f"extends_prior_capture={helper_1_third_cont_10['extends_prior_capture']} "
        f"overlap={helper_1_third_cont_10['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_10['overlap_matches']} "
        f"overlap_status={helper_1_third_cont_10['overlap_status']} "
        f"first16={helper_1_third_cont_10['first_16_bytes']} "
        f"last16={helper_1_third_cont_10['last_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_10['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_10['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_10_outbound} "
        f"start_boundary={helper_1_third_cont_10['start_boundary_status']} "
        f"function_entry={helper_1_third_cont_10['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_10['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_10['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_10['ownership_effect']} "
        f"scope={helper_1_third_cont_10['continuation_scope']} "
        f"bytes={helper_1_third_cont_10['bytes']}"
    )

    helper_1_third_cont_10_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof"
    ]
    helper_1_third_cont_10_branches = ",".join(
        f"0x{row['branch_rva']:08X}->{hexrva(row['decoded_target_rva'])}:match={row['matches']}:within={row['target_within_prefix']}:boundary={row['target_is_instruction_boundary']}"
        for row in helper_1_third_cont_10_proof["branches"]
    ) or "none"
    helper_1_third_cont_10_calls = ",".join(
        f"0x{row['call_rva']:08X}->{hexrva(row['decoded_target_rva'])}:match={row['matches']}:raw={row['raw_candidate_present']}"
        for row in helper_1_third_cont_10_proof["calls"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_10_proof="
        f"0x{helper_1_third_cont_10_proof['start_rva']:08X} status={helper_1_third_cont_10_proof['status']} "
        f"predecessor={helper_1_third_cont_10_proof['predecessor_status']} predecessor_exact={helper_1_third_cont_10_proof['predecessor_exact']} "
        f"start_boundary_proven={helper_1_third_cont_10_proof['start_boundary_proven']} layout_contiguous={helper_1_third_cont_10_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_10_proof['all_instruction_bytes_match']} instruction_count={helper_1_third_cont_10_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_10_proof['prefix_end_rva']:08X}:match={helper_1_third_cont_10_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_10_branches} branch_targets_match={helper_1_third_cont_10_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_10_proof['internal_branch_targets_on_boundaries']} incoming_1824ef={helper_1_third_cont_10_proof['incoming_1824ef_boundary_proven']} "
        f"capture_edge_branch={helper_1_third_cont_10_proof['capture_edge_branch_target_proven']} calls={helper_1_third_cont_10_calls} "
        f"call_targets_match={helper_1_third_cont_10_proof['call_targets_match']} raw_calls={helper_1_third_cont_10_proof['raw_call_candidates_present']} "
        f"rets={','.join(hexrva(rva) for rva in helper_1_third_cont_10_proof['ret_rvas'])}:match={helper_1_third_cont_10_proof['ret_matches']} "
        f"post_ret={','.join(hexrva(rva) for rva in helper_1_third_cont_10_proof['post_ret_code_rvas'])}:boundary={helper_1_third_cont_10_proof['post_ret_boundaries_proven']} "
        f"incomplete=0x{helper_1_third_cont_10_proof['incomplete_rva']:08X}:{helper_1_third_cont_10_proof['incomplete_bytes']}:match={helper_1_third_cont_10_proof['incomplete_matches']} "
        f"capture_end=0x{helper_1_third_cont_10_proof['capture_end_rva']:08X}:match={helper_1_third_cont_10_proof['capture_end_matches']} "
        f"start_boundary={helper_1_third_cont_10_proof['start_boundary_status']} incoming_1824ef_status={helper_1_third_cont_10_proof['incoming_1824ef_status']} "
        f"internal_branch_status={helper_1_third_cont_10_proof['internal_branch_status']} capture_edge_branch_status={helper_1_third_cont_10_proof['capture_edge_branch_status']} "
        f"terminal_status={helper_1_third_cont_10_proof['terminal_status']} post_terminal_boundary_status={helper_1_third_cont_10_proof['post_terminal_boundary_status']} "
        f"continuation={helper_1_third_cont_10_proof['continuation_status']} function_entry={helper_1_third_cont_10_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_10_proof['semantic_effect']} call_semantics={helper_1_third_cont_10_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_10_proof['ownership_effect']}"
    )

    helper_1_third_cont_11 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance"
    ]
    helper_1_third_cont_11_outbound = ",".join(
        f"0x{item['call_rva']:08X}->0x{item['target_rva']:08X}:"
        f"{item['known_target'] or 'unknown'}:{item['target_section']}"
        for item in helper_1_third_cont_11["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_11="
        f"0x{helper_1_third_cont_11['target_rva']:08X} "
        f"status={helper_1_third_cont_11['status']} "
        f"predecessor={helper_1_third_cont_11['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_11['predecessor_exact']} "
        f"section={helper_1_third_cont_11['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_11['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_11['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_11['probe_end_matches']} "
        f"prior_capture_end=0x{helper_1_third_cont_11['prior_capture_end_rva']:08X} "
        f"extends_prior_capture={helper_1_third_cont_11['extends_prior_capture']} "
        f"overlap={helper_1_third_cont_11['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_11['overlap_matches']} "
        f"overlap_status={helper_1_third_cont_11['overlap_status']} "
        f"first16={helper_1_third_cont_11['first_16_bytes']} "
        f"last16={helper_1_third_cont_11['last_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_11['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_11['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_11_outbound} "
        f"start_boundary={helper_1_third_cont_11['start_boundary_status']} "
        f"function_entry={helper_1_third_cont_11['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_11['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_11['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_11['ownership_effect']} "
        f"scope={helper_1_third_cont_11['continuation_scope']} "
        f"bytes={helper_1_third_cont_11['bytes']}"
    )

    helper_1_third_cont_12 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_12_provenance"
    ]
    helper_1_third_cont_12_outbound = ",".join(
        f"0x{item['call_rva']:08X}->0x{item['target_rva']:08X}:"
        f"{item['known_target'] or 'unknown'}:{item['target_section']}"
        for item in helper_1_third_cont_12["raw_outbound_rel32_candidates"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_12="
        f"0x{helper_1_third_cont_12['target_rva']:08X} "
        f"status={helper_1_third_cont_12['status']} "
        f"predecessor={helper_1_third_cont_12['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_12['predecessor_exact']} "
        f"section={helper_1_third_cont_12['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_12['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_12['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_12['probe_end_matches']} "
        f"prior_capture_end=0x{helper_1_third_cont_12['prior_capture_end_rva']:08X} "
        f"starts_at_prior_capture_end={helper_1_third_cont_12['starts_at_prior_capture_end']} "
        f"extends_prior_capture={helper_1_third_cont_12['extends_prior_capture']} "
        f"continuity_status={helper_1_third_cont_12['continuity_status']} "
        f"first16={helper_1_third_cont_12['first_16_bytes']} "
        f"last16={helper_1_third_cont_12['last_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_12['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_12['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_12_outbound} "
        f"start_boundary={helper_1_third_cont_12['start_boundary_status']} "
        f"function_entry={helper_1_third_cont_12['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_12['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_12['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_12['ownership_effect']} "
        f"scope={helper_1_third_cont_12['continuation_scope']} "
        f"bytes={helper_1_third_cont_12['bytes']}"
    )

    helper_1_third_cont_13 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_13_provenance"
    ]
    helper_1_third_cont_13_outbound = ",".join(
        f"0x{item['call_rva']:08X}->0x{item['target_rva']:08X}:"
        f"{item['known_target'] or 'unknown'}:{item['target_section']}"
        for item in helper_1_third_cont_13["raw_outbound_rel32_candidates"]
    ) or "none"
    helper_1_third_cont_13_targets = ",".join(
        f"0x{target:08X}" for target in helper_1_third_cont_13["covered_branch_targets"]
    )
    print(
        f"gf_target_c_helper_1_third_callee_continuation_13="
        f"0x{helper_1_third_cont_13['target_rva']:08X} "
        f"status={helper_1_third_cont_13['status']} "
        f"predecessor={helper_1_third_cont_13['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_13['predecessor_exact']} "
        f"section={helper_1_third_cont_13['target_section'] or 'none'} "
        f"probe_len={helper_1_third_cont_13['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_13['probe_end_rva']:08X} "
        f"probe_end_match={helper_1_third_cont_13['probe_end_matches']} "
        f"prior_capture_end=0x{helper_1_third_cont_13['prior_capture_end_rva']:08X} "
        f"extends_prior_capture={helper_1_third_cont_13['extends_prior_capture']} "
        f"overlap={helper_1_third_cont_13['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_13['overlap_matches']} "
        f"overlap_status={helper_1_third_cont_13['overlap_status']} "
        f"branch_targets_covered={helper_1_third_cont_13['branch_targets_covered']} "
        f"covered_branch_targets={helper_1_third_cont_13_targets} "
        f"first16={helper_1_third_cont_13['first_16_bytes']} "
        f"last16={helper_1_third_cont_13['last_16_bytes']} "
        f"inbound_raw={len(helper_1_third_cont_13['raw_inbound_rel32_candidates'])} "
        f"outbound_raw={len(helper_1_third_cont_13['raw_outbound_rel32_candidates'])} "
        f"outbound={helper_1_third_cont_13_outbound} "
        f"start_boundary={helper_1_third_cont_13['start_boundary_status']} "
        f"function_entry={helper_1_third_cont_13['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_13['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_13['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_13['ownership_effect']} "
        f"scope={helper_1_third_cont_13['continuation_scope']} "
        f"bytes={helper_1_third_cont_13['bytes']}"
    )

    helper_1_third_cont_13_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_13_prefix_proof"
    ]
    helper_1_third_cont_13_proof_branches = ",".join(
        f"0x{row['branch_rva']:08X}->0x{row['decoded_target_rva']:08X}:"
        f"match={row['matches']}:within={row['target_within_prefix']}:"
        f"boundary={row['target_is_instruction_boundary']}"
        for row in helper_1_third_cont_13_proof["branches"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_13_proof="
        f"0x{helper_1_third_cont_13_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_13_proof['status']} "
        f"predecessor={helper_1_third_cont_13_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_13_proof['predecessor_exact']} "
        f"start_boundary={helper_1_third_cont_13_proof['start_boundary_proven']} "
        f"layout_contiguous={helper_1_third_cont_13_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_13_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_13_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_13_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_13_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_13_proof_branches} "
        f"branch_targets_match={helper_1_third_cont_13_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_13_proof['internal_branch_targets_on_boundaries']} "
        f"predecessor_targets={helper_1_third_cont_13_proof['predecessor_targets_on_boundaries']} "
        f"backedge_18257c={helper_1_third_cont_13_proof['backedge_target_boundary_proven']} "
        f"incomplete=0x{helper_1_third_cont_13_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_13_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_13_proof['incomplete_matches']} "
        f"capture_end=0x{helper_1_third_cont_13_proof['capture_end_rva']:08X}:"
        f"match={helper_1_third_cont_13_proof['capture_end_matches']} "
        f"continuation={helper_1_third_cont_13_proof['continuation_status']} "
        f"function_entry={helper_1_third_cont_13_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_13_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_13_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_13_proof['ownership_effect']}"
    )

    helper_1_third_cont_14 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_14_provenance"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_14="
        f"0x{helper_1_third_cont_14['target_rva']:08X} "
        f"status={helper_1_third_cont_14['status']} "
        f"predecessor={helper_1_third_cont_14['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_14['predecessor_exact']} "
        f"probe_len={helper_1_third_cont_14['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_14['probe_end_rva']:08X} "
        f"overlap={helper_1_third_cont_14['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_14['overlap_matches']} "
        f"predecessor_targets_covered={helper_1_third_cont_14['predecessor_targets_covered']} "
        f"bytes={helper_1_third_cont_14['bytes']}"
    )
    helper_1_third_cont_14_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_14_prefix_proof"
    ]
    helper_1_third_cont_14_branches = ",".join(
        f"0x{row['branch_rva']:08X}->0x{row['decoded_target_rva']:08X}:"
        f"match={row['matches']}:within={row['target_within_prefix']}:"
        f"boundary={row['target_is_instruction_boundary']}"
        for row in helper_1_third_cont_14_proof["branches"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_14_proof="
        f"0x{helper_1_third_cont_14_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_14_proof['status']} "
        f"predecessor_exact={helper_1_third_cont_14_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_14_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_14_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_14_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_14_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_14_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_14_branches} "
        f"branch_targets_match={helper_1_third_cont_14_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_14_proof['internal_branch_targets_on_boundaries']} "
        f"predecessor_targets={helper_1_third_cont_14_proof['predecessor_targets_on_boundaries']} "
        f"backedge_1825d4={helper_1_third_cont_14_proof['backedge_target_boundary_proven']} "
        f"ret_matches={helper_1_third_cont_14_proof['ret_matches']} "
        f"post_ret_boundaries={helper_1_third_cont_14_proof['post_ret_boundaries_proven']} "
        f"capture_end_boundary={helper_1_third_cont_14_proof['capture_end_is_instruction_boundary']} "
        f"continuation={helper_1_third_cont_14_proof['continuation_status']} "
        f"semantic_effect={helper_1_third_cont_14_proof['semantic_effect']} "
        f"ownership_effect={helper_1_third_cont_14_proof['ownership_effect']}"
    )

    helper_1_third_cont_7_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof"
    ]
    helper_1_third_cont_7_branches = ",".join(
        f"0x{row['branch_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:"
        f"within={row['target_within_prefix']}:"
        f"boundary={row['target_is_instruction_boundary']}:"
        f"prev_boundary={row['predecessor_target_is_instruction_boundary']}"
        for row in helper_1_third_cont_7_proof["branches"]
    ) or "none"
    helper_1_third_cont_7_calls = ",".join(
        f"0x{row['call_rva']:08X}->"
        f"{hexrva(row['decoded_target_rva'])}:"
        f"match={row['matches']}:raw={row['raw_candidate_present']}"
        for row in helper_1_third_cont_7_proof["calls"]
    ) or "none"
    print(
        f"gf_target_c_helper_1_third_callee_continuation_7_proof="
        f"0x{helper_1_third_cont_7_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_7_proof['status']} "
        f"predecessor={helper_1_third_cont_7_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_7_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_7_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_7_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_7_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_7_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_7_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_7_branches} "
        f"branch_targets_match={helper_1_third_cont_7_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_7_proof['internal_branch_targets_on_boundaries']} "
        f"predecessor_boundaries={helper_1_third_cont_7_proof['predecessor_branch_targets_on_boundaries']} "
        f"incoming_182461={helper_1_third_cont_7_proof['incoming_182461_boundary_proven']} "
        f"backedge_182416={helper_1_third_cont_7_proof['backedge_182416_boundary_proven']} "
        f"internal_18245a={helper_1_third_cont_7_proof['internal_18245a_boundary_proven']} "
        f"calls={helper_1_third_cont_7_calls} "
        f"call_targets_match={helper_1_third_cont_7_proof['call_targets_match']} "
        f"raw_calls={helper_1_third_cont_7_proof['raw_call_candidates_present']} "
        f"incomplete=0x{helper_1_third_cont_7_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_7_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_7_proof['incomplete_matches']} "
        f"capture_end=0x{helper_1_third_cont_7_proof['capture_end_rva']:08X}:"
        f"match={helper_1_third_cont_7_proof['capture_end_matches']} "
        f"start_boundary={helper_1_third_cont_7_proof['start_boundary_status']} "
        f"incoming_branch_status={helper_1_third_cont_7_proof['incoming_branch_target_status']} "
        f"backedge_status={helper_1_third_cont_7_proof['backedge_target_status']} "
        f"internal_branch_status={helper_1_third_cont_7_proof['internal_branch_target_status']} "
        f"continuation={helper_1_third_cont_7_proof['continuation_status']} "
        f"function_entry={helper_1_third_cont_7_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_7_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_7_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_7_proof['ownership_effect']}"
    )

    tail_probe = report["guarded_gf_target_c_tail_probe"]
    print(
        f"gf_target_c_tail_probe=0x{tail_probe['rva']:08X} "
        f"len={tail_probe['length']} bytes={tail_probe['bytes']}"
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
    if alignment_c["status"] != "EXACT_FIRST_CALL_ALIGNMENT_PROVEN":
        print("guarded_gf_target_c_alignment_proof=FAILED")
        return 4
    if alignment_c2["status"] != "EXACT_SECOND_CALL_ALIGNMENT_PROVEN":
        print("guarded_gf_target_c_second_call_alignment_proof=FAILED")
        return 5
    if alignment_c3["status"] != "EXACT_THIRD_CALL_ALIGNMENT_PROVEN":
        print("guarded_gf_target_c_third_call_alignment_proof=FAILED")
        return 6
    if helper_1_proof["status"] != "EXACT_PACKED_SELECTOR_LOOKUP_PREFIX_PROVEN":
        print("guarded_gf_target_c_helper_1_prefix_proof=FAILED")
        return 7
    if helper_1_success["status"] != "EXACT_SUCCESS_CALL_CHAIN_PREFIX_PROVEN":
        print("guarded_gf_target_c_helper_1_success_prefix_proof=FAILED")
        return 8
    if helper_1_callee["status"] != "EXACT_EXE_FIRST_CALLEE_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_first_callee_provenance=FAILED")
        return 9
    if helper_1_callee_prefix["status"] != "EXACT_FIRST_CALLEE_SLOT_SCAN_PREFIX_PROVEN":
        print("guarded_gf_target_c_helper_1_first_callee_prefix_proof=FAILED")
        return 10
    if helper_1_callee_cont["status"] != "EXACT_EXE_FIRST_CALLEE_CONTINUATION_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_first_callee_continuation_provenance=FAILED")
        return 11
    if helper_1_callee_terminal["status"] != "EXACT_FIRST_CALLEE_TERMINAL_PADDING_ANCHOR_PROVEN":
        print("guarded_gf_target_c_helper_1_first_callee_terminal_padding_proof=FAILED")
        return 12
    if helper_1_next_code["status"] != "EXACT_EXE_NEXT_CODE_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_next_code_provenance=FAILED")
        return 13
    if helper_1_next_prefix["status"] != "EXACT_NEXT_CODE_PREFIX_CALL_ALIGNMENT_PROVEN":
        print("guarded_gf_target_c_helper_1_next_code_prefix_proof=FAILED")
        return 14
    if helper_1_next_cont["status"] != "EXACT_EXE_NEXT_CODE_CONTINUATION_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_next_code_continuation_provenance=FAILED")
        return 15
    if helper_1_next_cont_prefix["status"] != "EXACT_NEXT_CODE_CONTINUATION_CALLS_PROVEN":
        print("guarded_gf_target_c_helper_1_next_code_continuation_prefix_proof=FAILED")
        return 16
    if helper_1_next_cont2["status"] != "EXACT_EXE_NEXT_CODE_CONTINUATION_2_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_next_code_continuation_2_provenance=FAILED")
        return 17
    if helper_1_next_cont2_prefix["status"] != "EXACT_NEXT_CODE_CONTINUATION_2_TERMINAL_PROVEN":
        print("guarded_gf_target_c_helper_1_next_code_continuation_2_prefix_proof=FAILED")
        return 18
    if helper_1_next_boundary["status"] != "EXACT_28320_FUNCTION_ENTRY_BOUNDARY_PROVEN":
        print("guarded_gf_target_c_helper_1_next_code_function_boundary_proof=FAILED")
        return 19
    if helper_1_second_callee["status"] != "EXACT_EXE_8BD20_DUAL_CALL_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_second_callee_provenance=FAILED")
        return 20
    if helper_1_second_callee_prefix["status"] != "EXACT_8BD20_BOUNDED_ROUTINE_PADDING_PROVEN":
        print("guarded_gf_target_c_helper_1_second_callee_prefix_proof=FAILED")
        return 21
    if helper_1_third_callee["status"] != "EXACT_EXE_182194_CALL_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_provenance=FAILED")
        return 22
    if helper_1_third_callee_prefix["status"] != "EXACT_182194_PREFIX_CONTROL_FLOW_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_prefix_proof=FAILED")
        return 23
    if helper_1_third_cont["status"] != "EXACT_EXE_1821F3_CONTINUATION_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_provenance=FAILED")
        return 24
    if helper_1_third_cont_proof["status"] != "EXACT_1821F3_CONTINUATION_CONTROL_FLOW_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_prefix_proof=FAILED")
        return 25
    if helper_1_third_cont_2["status"] != "EXACT_EXE_182251_CONTINUATION_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_2_provenance=FAILED")
        return 26
    if helper_1_third_cont_2_proof["status"] != "EXACT_182251_CONTINUATION_CONTROL_FLOW_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_2_prefix_proof=FAILED")
        return 27
    if helper_1_third_cont_3["status"] != "EXACT_EXE_1822D1_CONTINUATION_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_3_provenance=FAILED")
        return 28
    if helper_1_third_terminal["status"] != "EXACT_1822D0_LEAVE_RET_AND_1822D2_NEXT_INSTRUCTION_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_terminal_boundary_proof=FAILED")
        return 29
    if helper_1_third_post_terminal["status"] != "EXACT_1822D2_SEQUENCE_RET_PADDING_NEXT_BOUNDARY_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_post_terminal_prefix_proof=FAILED")
        return 30
    if helper_1_third_next_block["status"] != "EXACT_182300_SEQUENCE_RET_NEXT_BOUNDARY_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_next_block_prefix_proof=FAILED")
        return 31
    if helper_1_third_next_cont["status"] != "EXACT_182314_TO_182331_CAPTURE_END_CONTROL_FLOW_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_next_block_continuation_proof=FAILED")
        return 32
    if helper_1_third_cont_4["status"] != "EXACT_EXE_182331_TO_182391_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_4_provenance=FAILED")
        return 33
    if helper_1_third_cont_4_proof["status"] != "EXACT_182331_TO_182391_CONTROL_FLOW_PREFIX_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_4_prefix_proof=FAILED")
        return 34
    if helper_1_third_cont_5["status"] != "EXACT_EXE_182391_TO_1823F1_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_5_provenance=FAILED")
        return 35
    if helper_1_third_cont_5_proof["status"] != "EXACT_182391_SEQUENCE_RET_PADDING_NEXT_BOUNDARY_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_5_prefix_proof=FAILED")
        return 36
    if helper_1_third_cont_5_tail["status"] != "EXACT_1823D0_TO_1823EF_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_5_tail_prefix_proof=FAILED")
        return 37
    if helper_1_third_cont_6["status"] != "EXACT_EXE_1823EF_TO_18242F_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_6_provenance=FAILED")
        return 38
    if helper_1_third_cont_6_proof["status"] != "EXACT_1823EF_TO_18242E_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_6_prefix_proof=FAILED")
        return 39
    if helper_1_third_cont_7["status"] != "EXACT_EXE_18242E_TO_18246E_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_7_provenance=FAILED")
        return 40
    if helper_1_third_cont_7_proof["status"] != "EXACT_18242E_TO_18246D_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_7_prefix_proof=FAILED")
        return 41
    if helper_1_third_cont_8["status"] != "EXACT_EXE_18246D_TO_1824AD_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_8_provenance=FAILED")
        return 42
    if helper_1_third_cont_8_proof["status"] != "EXACT_18246D_TO_1824AB_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_8_prefix_proof=FAILED")
        return 43
    if helper_1_third_cont_9["status"] != "EXACT_EXE_1824AB_TO_1824EB_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_9_provenance=FAILED")
        return 44
    if helper_1_third_cont_9_proof["status"] != "EXACT_1824AB_TO_1824EA_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_9_prefix_proof=FAILED")
        return 45
    if helper_1_third_cont_10["status"] != "EXACT_EXE_1824EA_TO_18252A_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_10_provenance=FAILED")
        return 46
    if helper_1_third_cont_10_proof["status"] != "EXACT_1824EA_TO_182529_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_10_prefix_proof=FAILED")
        return 47
    if helper_1_third_cont_11["status"] != "EXACT_EXE_182529_TO_182569_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_11_provenance=FAILED")
        return 48
    if helper_1_third_cont_12["status"] != "EXACT_EXE_182569_TO_1825A9_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_12_provenance=FAILED")
        return 49


    helper_1_third_cont_15 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_15_provenance"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_15="
        f"0x{helper_1_third_cont_15['target_rva']:08X} "
        f"status={helper_1_third_cont_15['status']} "
        f"predecessor={helper_1_third_cont_15['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_15['predecessor_exact']} "
        f"probe_len={helper_1_third_cont_15['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_15['probe_end_rva']:08X} "
        f"bytes={helper_1_third_cont_15['bytes']}"
    )


    helper_1_third_cont_15_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_15_prefix_proof"
    ]
    helper_1_third_cont_15_branches = ",".join(
        f"0x{row['branch_rva']:08X}->0x{row['decoded_target_rva']:08X}:"
        f"match={row['matches']}:within={row['target_within_prefix']}:"
        f"boundary={row['target_is_instruction_boundary']}"
        for row in helper_1_third_cont_15_proof["branches"]
    )
    print(
        f"gf_target_c_helper_1_third_callee_continuation_15_proof="
        f"0x{helper_1_third_cont_15_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_15_proof['status']} "
        f"predecessor={helper_1_third_cont_15_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_15_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_15_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_15_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_15_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_15_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_15_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_15_branches} "
        f"branch_targets_match={helper_1_third_cont_15_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_15_proof['internal_branch_targets_on_boundaries']} "
        f"predecessor_targets={helper_1_third_cont_15_proof['predecessor_targets_match']} "
        f"incomplete=0x{helper_1_third_cont_15_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_15_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_15_proof['incomplete_matches']} "
        f"capture_end=0x{helper_1_third_cont_15_proof['capture_end_rva']:08X}:"
        f"match={helper_1_third_cont_15_proof['capture_end_matches']} "
        f"continuation={helper_1_third_cont_15_proof['continuation_status']} "
        f"function_entry={helper_1_third_cont_15_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_15_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_15_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_15_proof['ownership_effect']}"
    )


    helper_1_third_cont_16 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_16_provenance"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_16="
        f"0x{helper_1_third_cont_16['target_rva']:08X} "
        f"status={helper_1_third_cont_16['status']} "
        f"predecessor={helper_1_third_cont_16['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_16['predecessor_exact']} "
        f"probe_len={helper_1_third_cont_16['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_16['probe_end_rva']:08X} "
        f"overlap={helper_1_third_cont_16['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_16['overlap_matches']} "
        f"bytes={helper_1_third_cont_16['bytes']}"
    )
    helper_1_third_cont_16_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_16_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_16_proof="
        f"0x{helper_1_third_cont_16_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_16_proof['status']} "
        f"predecessor={helper_1_third_cont_16_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_16_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_16_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_16_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_16_proof['instruction_count']} "
        f"branch_targets_match={helper_1_third_cont_16_proof['branch_targets_match']} "
        f"predecessor_target_boundary={helper_1_third_cont_16_proof['predecessor_target_is_boundary']} "
        f"rets={helper_1_third_cont_16_proof['ret_matches']} "
        f"padding={helper_1_third_cont_16_proof['padding_matches']} "
        f"next_code=0x{helper_1_third_cont_16_proof['next_code_rva']:08X}:"
        f"boundary={helper_1_third_cont_16_proof['next_code_boundary']} "
        f"capture_end=0x{helper_1_third_cont_16_proof['capture_end_rva']:08X}:"
        f"boundary={helper_1_third_cont_16_proof['capture_end_is_instruction_boundary']} "
        f"continuation={helper_1_third_cont_16_proof['continuation_status']} "
        f"function_entry={helper_1_third_cont_16_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_16_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_16_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_16_proof['ownership_effect']}"
    )


    helper_1_third_cont_17 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_17_provenance"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_17="
        f"0x{helper_1_third_cont_17['target_rva']:08X} "
        f"status={helper_1_third_cont_17['status']} "
        f"predecessor={helper_1_third_cont_17['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_17['predecessor_exact']} "
        f"probe_len={helper_1_third_cont_17['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_17['probe_end_rva']:08X} "
        f"bytes={helper_1_third_cont_17['bytes']}"
    )
    helper_1_third_cont_17_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_17_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_17_proof="
        f"0x{helper_1_third_cont_17_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_17_proof['status']} "
        f"predecessor={helper_1_third_cont_17_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_17_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_17_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_17_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_17_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_17_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_17_proof['prefix_end_matches']} "
        f"branch_targets_match={helper_1_third_cont_17_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_17_proof['internal_branch_targets_on_boundaries']} "
        f"incomplete=0x{helper_1_third_cont_17_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_17_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_17_proof['incomplete_matches']} "
        f"capture_end=0x{helper_1_third_cont_17_proof['capture_end_rva']:08X}:"
        f"match={helper_1_third_cont_17_proof['capture_end_matches']} "
        f"continuation={helper_1_third_cont_17_proof['continuation_status']} "
        f"function_entry={helper_1_third_cont_17_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_17_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_17_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_17_proof['ownership_effect']}"
    )


    helper_1_third_cont_18 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_18_provenance"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_18="
        f"0x{helper_1_third_cont_18['target_rva']:08X} "
        f"status={helper_1_third_cont_18['status']} "
        f"predecessor={helper_1_third_cont_18['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_18['predecessor_exact']} "
        f"probe_len={helper_1_third_cont_18['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_18['probe_end_rva']:08X} "
        f"overlap={helper_1_third_cont_18['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_18['overlap_matches']} "
        f"bytes={helper_1_third_cont_18['bytes']}"
    )
    helper_1_third_cont_18_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_18_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_18_proof="
        f"0x{helper_1_third_cont_18_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_18_proof['status']} "
        f"predecessor={helper_1_third_cont_18_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_18_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_18_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_18_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_18_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_18_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_18_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_18_proof['branch_targets_match']} "
        f"calls={helper_1_third_cont_18_proof['calls_match']} "
        f"predecessor_targets={helper_1_third_cont_18_proof['predecessor_targets_on_boundaries']} "
        f"incomplete=0x{helper_1_third_cont_18_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_18_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_18_proof['incomplete_matches']} "
        f"continuation={helper_1_third_cont_18_proof['continuation_status']} "
        f"function_entry={helper_1_third_cont_18_proof['function_entry_status']} "
        f"semantic_effect={helper_1_third_cont_18_proof['semantic_effect']} "
        f"call_semantics={helper_1_third_cont_18_proof['call_semantics']} "
        f"ownership_effect={helper_1_third_cont_18_proof['ownership_effect']}"
    )


    helper_1_third_cont_19 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_19_provenance"
    ]
    helper_1_third_cont_19_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_19_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_19="
        f"0x{helper_1_third_cont_19['target_rva']:08X} "
        f"status={helper_1_third_cont_19['status']} "
        f"predecessor={helper_1_third_cont_19['predecessor_status']} "
        f"overlap={helper_1_third_cont_19['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_19['overlap_matches']} "
        f"bytes={helper_1_third_cont_19['bytes']}"
    )
    print(
        f"gf_target_c_helper_1_third_callee_continuation_19_proof="
        f"0x{helper_1_third_cont_19_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_19_proof['status']} "
        f"layout_contiguous={helper_1_third_cont_19_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_19_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_19_proof['instruction_count']} "
        f"branches={helper_1_third_cont_19_proof['branch_targets_match']} "
        f"calls={helper_1_third_cont_19_proof['calls_match']} "
        f"incomplete=0x{helper_1_third_cont_19_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_19_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_19_proof['incomplete_matches']} "
        f"continuation={helper_1_third_cont_19_proof['continuation_status']} "
        f"ownership_effect={helper_1_third_cont_19_proof['ownership_effect']}"
    )

    helper_1_third_cont_20 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_20_provenance"
    ]
    helper_1_third_cont_20_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_20_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_20="
        f"0x{helper_1_third_cont_20['target_rva']:08X} "
        f"status={helper_1_third_cont_20['status']} "
        f"predecessor={helper_1_third_cont_20['predecessor_status']} "
        f"overlap={helper_1_third_cont_20['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_20['overlap_matches']} "
        f"bytes={helper_1_third_cont_20['bytes']}"
    )
    print(
        f"gf_target_c_helper_1_third_callee_continuation_20_proof="
        f"0x{helper_1_third_cont_20_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_20_proof['status']} "
        f"layout_contiguous={helper_1_third_cont_20_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_20_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_20_proof['instruction_count']} "
        f"branches={helper_1_third_cont_20_proof['branch_targets_match']} "
        f"calls={helper_1_third_cont_20_proof['calls_match']} "
        f"incomplete=0x{helper_1_third_cont_20_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_20_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_20_proof['incomplete_matches']} "
        f"continuation={helper_1_third_cont_20_proof['continuation_status']} "
        f"ownership_effect={helper_1_third_cont_20_proof['ownership_effect']}"
    )

    helper_1_third_cont_21 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_21_provenance"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_21="
        f"0x{helper_1_third_cont_21['target_rva']:08X} "
        f"status={helper_1_third_cont_21['status']} "
        f"predecessor={helper_1_third_cont_21['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_21['predecessor_exact']} "
        f"probe_len={helper_1_third_cont_21['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_21['probe_end_rva']:08X} "
        f"overlap={helper_1_third_cont_21['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_21['overlap_matches']} "
        f"bytes={helper_1_third_cont_21['bytes']}"
    )


    helper_1_third_cont_21_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_21_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_21_proof="
        f"0x{helper_1_third_cont_21_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_21_proof['status']} "
        f"predecessor={helper_1_third_cont_21_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_21_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_21_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_21_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_21_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_21_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_21_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_21_proof['branch_targets_match']} "
        f"calls={helper_1_third_cont_21_proof['calls_match']} "
        f"predecessor_targets={helper_1_third_cont_21_proof['predecessor_targets_match']} "
        f"incomplete=0x{helper_1_third_cont_21_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_21_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_21_proof['incomplete_matches']} "
        f"continuation={helper_1_third_cont_21_proof['continuation_status']} "
        f"ownership_effect={helper_1_third_cont_21_proof['ownership_effect']}"
    )

    helper_1_third_cont_22 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_22_provenance"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_22="
        f"0x{helper_1_third_cont_22['target_rva']:08X} "
        f"status={helper_1_third_cont_22['status']} "
        f"predecessor={helper_1_third_cont_22['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_22['predecessor_exact']} "
        f"probe_len={helper_1_third_cont_22['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_22['probe_end_rva']:08X} "
        f"overlap={helper_1_third_cont_22['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_22['overlap_matches']} "
        f"bytes={helper_1_third_cont_22['bytes']}"
    )


    helper_1_third_cont_22_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_22_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_22_proof="
        f"0x{helper_1_third_cont_22_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_22_proof['status']} "
        f"predecessor={helper_1_third_cont_22_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_22_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_22_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_22_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_22_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_22_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_22_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_22_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_22_proof['internal_branch_targets_on_boundaries']} "
        f"calls={helper_1_third_cont_22_proof['calls_match']} "
        f"predecessor_targets={helper_1_third_cont_22_proof['predecessor_targets_match']} "
        f"incomplete=0x{helper_1_third_cont_22_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_22_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_22_proof['incomplete_matches']} "
        f"continuation={helper_1_third_cont_22_proof['continuation_status']} "
        f"ownership_effect={helper_1_third_cont_22_proof['ownership_effect']}"
    )


    helper_1_third_cont_23 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_23_provenance"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_23="
        f"0x{helper_1_third_cont_23['target_rva']:08X} "
        f"status={helper_1_third_cont_23['status']} "
        f"predecessor={helper_1_third_cont_23['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_23['predecessor_exact']} "
        f"probe_len={helper_1_third_cont_23['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_23['probe_end_rva']:08X} "
        f"overlap={helper_1_third_cont_23['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_23['overlap_matches']} "
        f"bytes={helper_1_third_cont_23['bytes']}"
    )



    helper_1_third_cont_23_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_23_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_23_proof="
        f"0x{helper_1_third_cont_23_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_23_proof['status']} "
        f"predecessor={helper_1_third_cont_23_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_23_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_23_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_23_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_23_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_23_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_23_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_23_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_23_proof['internal_branch_targets_on_boundaries']} "
        f"calls={helper_1_third_cont_23_proof['calls_match']} "
        f"predecessor_targets={helper_1_third_cont_23_proof['predecessor_targets_match']} "
        f"incomplete=0x{helper_1_third_cont_23_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_23_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_23_proof['incomplete_matches']} "
        f"continuation={helper_1_third_cont_23_proof['continuation_status']} "
        f"ownership_effect={helper_1_third_cont_23_proof['ownership_effect']}"
    )


    helper_1_third_cont_24 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_24_provenance"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_24="
        f"0x{helper_1_third_cont_24['target_rva']:08X} "
        f"status={helper_1_third_cont_24['status']} "
        f"predecessor={helper_1_third_cont_24['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_24['predecessor_exact']} "
        f"probe_len={helper_1_third_cont_24['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_24['probe_end_rva']:08X} "
        f"overlap={helper_1_third_cont_24['overlap_bytes']} "
        f"overlap_match={helper_1_third_cont_24['overlap_matches']} "
        f"bytes={helper_1_third_cont_24['bytes']}"
    )


    helper_1_third_cont_24_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_24_prefix_proof"
    ]
    helper_1_third_cont_24_branches = ",".join(
        f"0x{row['branch_rva']:08X}->0x{row['decoded_target_rva']:08X}:"
        f"match={row['matches']}:within={row['target_within_prefix']}:"
        f"boundary={row['target_is_instruction_boundary']}"
        for row in helper_1_third_cont_24_proof["branches"]
    )
    print(
        f"gf_target_c_helper_1_third_callee_continuation_24_proof="
        f"0x{helper_1_third_cont_24_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_24_proof['status']} "
        f"predecessor={helper_1_third_cont_24_proof['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_24_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_24_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_24_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_24_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_24_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_24_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_24_branches} "
        f"branch_targets_match={helper_1_third_cont_24_proof['branch_targets_match']} "
        f"internal_boundaries={helper_1_third_cont_24_proof['internal_branch_targets_on_boundaries']} "
        f"calls={helper_1_third_cont_24_proof['calls_match']} "
        f"predecessor_targets={helper_1_third_cont_24_proof['predecessor_targets_match']} "
        f"capture_end=0x{helper_1_third_cont_24_proof['capture_end_rva']:08X}:"
        f"boundary={helper_1_third_cont_24_proof['capture_end_is_instruction_boundary']} "
        f"continuation={helper_1_third_cont_24_proof['continuation_status']} "
        f"ownership_effect={helper_1_third_cont_24_proof['ownership_effect']}"
    )


    if helper_1_third_cont_13["status"] != "EXACT_EXE_1825A6_TO_1825E6_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_13_provenance=FAILED")
        return 50
    if helper_1_third_cont_13_proof["status"] != "EXACT_1825A6_TO_1825E5_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_13_prefix_proof=FAILED")
        return 51
    if helper_1_third_cont_14["status"] != "EXACT_EXE_1825E5_TO_182635_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_14_provenance=FAILED")
        return 52
    if helper_1_third_cont_14_proof["status"] != "EXACT_1825E5_TO_182635_CONTROL_FLOW_PREFIX_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_14_prefix_proof=FAILED")
        return 53
    if helper_1_third_cont_15["status"] != "EXACT_EXE_182635_TO_182675_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_15_provenance=FAILED")
        return 54
    if helper_1_third_cont_15_proof["status"] != "EXACT_182635_TO_182673_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_15_prefix_proof=FAILED")
        return 55
    if helper_1_third_cont_16["status"] != "EXACT_EXE_182673_TO_1826B3_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_16_provenance=FAILED")
        return 56
    if helper_1_third_cont_16_proof["status"] != "EXACT_182673_TO_1826B3_CONTROL_FLOW_PREFIX_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_16_prefix_proof=FAILED")
        return 57
    if helper_1_third_cont_17["status"] != "EXACT_EXE_1826B3_TO_1826F3_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_17_provenance=FAILED")
        return 58
    if helper_1_third_cont_17_proof["status"] != "EXACT_1826B3_TO_1826F1_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_17_prefix_proof=FAILED")
        return 59
    if helper_1_third_cont_18["status"] != "EXACT_EXE_1826F1_TO_182731_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_18_provenance=FAILED")
        return 60
    if helper_1_third_cont_18_proof["status"] != "EXACT_1826F1_TO_182730_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_18_prefix_proof=FAILED")
        return 61
    if helper_1_third_cont_19["status"] != "EXACT_EXE_182730_TO_182770_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_19_provenance=FAILED")
        return 62
    if helper_1_third_cont_19_proof["status"] != "EXACT_182730_TO_18276D_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_19_prefix_proof=FAILED")
        return 63
    if helper_1_third_cont_20["status"] != "EXACT_EXE_18276D_TO_1827AD_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_20_provenance=FAILED")
        return 64
    if helper_1_third_cont_20_proof["status"] != "EXACT_18276D_TO_1827AC_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_20_prefix_proof=FAILED")
        return 65
    if helper_1_third_cont_21["status"] != "EXACT_EXE_1827AC_TO_1827EC_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_21_provenance=FAILED")
        return 66
    if helper_1_third_cont_21_proof["status"] != "EXACT_1827AC_TO_1827E9_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_21_prefix_proof=FAILED")
        return 67
    if helper_1_third_cont_22["status"] != "EXACT_EXE_1827E9_TO_182829_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_22_provenance=FAILED")
        return 68
    if helper_1_third_cont_22_proof["status"] != "EXACT_1827E9_TO_182828_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_22_prefix_proof=FAILED")
        return 69
    if helper_1_third_cont_23["status"] != "EXACT_EXE_182828_TO_182868_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_23_provenance=FAILED")
        return 70
    if helper_1_third_cont_23_proof["status"] != "EXACT_182828_TO_182867_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_23_prefix_proof=FAILED")
        return 71
    if helper_1_third_cont_24["status"] != "EXACT_EXE_182867_TO_1828A7_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_24_provenance=FAILED")
        return 72
    helper_1_third_cont_25 = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_25_provenance"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_25="
        f"0x{helper_1_third_cont_25['target_rva']:08X} "
        f"status={helper_1_third_cont_25['status']} "
        f"predecessor={helper_1_third_cont_25['predecessor_status']} "
        f"predecessor_exact={helper_1_third_cont_25['predecessor_exact']} "
        f"predecessor_end=0x{helper_1_third_cont_25['predecessor_end_rva']:08X}:"
        f"boundary={helper_1_third_cont_25['predecessor_end_is_instruction_boundary']} "
        f"probe_len={helper_1_third_cont_25['probe_len']} "
        f"probe_end=0x{helper_1_third_cont_25['probe_end_rva']:08X}:"
        f"match={helper_1_third_cont_25['probe_end_matches']} "
        f"bytes={helper_1_third_cont_25['bytes']}"
    )


    if helper_1_third_cont_24_proof["status"] != "EXACT_182867_TO_1828A7_CONTROL_FLOW_PREFIX_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_24_prefix_proof=FAILED")
        return 73
    if helper_1_third_cont_25["status"] != "EXACT_EXE_1828A7_TO_1828E7_PROVENANCE_CAPTURED":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_25_provenance=FAILED")
        return 74

    helper_1_third_cont_25_proof = report[
        "guarded_gf_target_c_helper_1_third_callee_continuation_25_prefix_proof"
    ]
    print(
        f"gf_target_c_helper_1_third_callee_continuation_25_proof="
        f"0x{helper_1_third_cont_25_proof['start_rva']:08X} "
        f"status={helper_1_third_cont_25_proof['status']} "
        f"predecessor_exact={helper_1_third_cont_25_proof['predecessor_exact']} "
        f"layout_contiguous={helper_1_third_cont_25_proof['layout_contiguous']} "
        f"bytes_match={helper_1_third_cont_25_proof['all_instruction_bytes_match']} "
        f"instruction_count={helper_1_third_cont_25_proof['instruction_count']} "
        f"prefix_end=0x{helper_1_third_cont_25_proof['prefix_end_rva']:08X}:"
        f"match={helper_1_third_cont_25_proof['prefix_end_matches']} "
        f"branches={helper_1_third_cont_25_proof['branch_targets_match']} "
        f"calls={helper_1_third_cont_25_proof['calls_match']} "
        f"raw_call_census={helper_1_third_cont_25_proof['raw_call_census_matches']} "
        f"predecessor_targets={helper_1_third_cont_25_proof['predecessor_targets_match']} "
        f"resolved_forward_targets={helper_1_third_cont_25_proof['resolved_forward_targets_on_boundaries']} "
        f"incomplete=0x{helper_1_third_cont_25_proof['incomplete_rva']:08X}:"
        f"{helper_1_third_cont_25_proof['incomplete_bytes']}:"
        f"match={helper_1_third_cont_25_proof['incomplete_matches']} "
        f"continuation={helper_1_third_cont_25_proof['continuation_status']} "
        f"ownership_effect={helper_1_third_cont_25_proof['ownership_effect']}"
    )
    if helper_1_third_cont_25_proof["status"] != "EXACT_1828A7_TO_1828E2_CONTROL_FLOW_CAPTURE_EDGE_PROVEN":
        print("guarded_gf_target_c_helper_1_third_callee_continuation_25_prefix_proof=FAILED")
        return 75
    return 0


if __name__ == "__main__":
    raise SystemExit(main())