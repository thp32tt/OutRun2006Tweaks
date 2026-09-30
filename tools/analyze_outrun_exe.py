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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())