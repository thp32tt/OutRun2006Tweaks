#!/usr/bin/env python3
"""
Fail-closed source gate for the HMD-proven OutRun VR baseline.

This is intentionally stricter than a normal unit test: it protects exact
reverse-engineered producer addresses, runtime defaults, renderer selection and
known regression fixes from being silently omitted by later builds.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

errors: list[str] = []
passes: list[str] = []

def require(rel: str, needle: str, label: str) -> None:
    text = read(rel)
    if needle not in text:
        errors.append(f"{label}: missing {rel} :: {needle}")
    else:
        passes.append(label)

def require_all(rel: str, needles: list[str], label: str) -> None:
    text = read(rel)
    missing = [n for n in needles if n not in text]
    if missing:
        errors.append(f"{label}: missing from {rel}: {missing}")
    else:
        passes.append(label)

def forbid(rel: str, needle: str, label: str) -> None:
    text = read(rel)
    if needle in text:
        errors.append(f"{label}: forbidden pattern present in {rel}: {needle}")
    else:
        passes.append(label)

# PASS 1 — build configuration must default to the proven R26+HUD renderer.
require_all("CMakeLists.txt", [
    'option(OUTRUN_VR_SAFE_DRAW_COMPARE "Use R26-only safe-draw diagnostic path" OFF)',
    'option(OUTRUN_VR_R26_HUD_COMPARE "Build R26-safe world path with R30 HUD/XYZRHW/SkyGlow overlay" ON)',
], "P1_BUILD_DEFAULT_R26_HUD")
require_all("cmake.toml", [
    'option(OUTRUN_VR_SAFE_DRAW_COMPARE "Use R26-only safe-draw diagnostic path" OFF)',
    'option(OUTRUN_VR_R26_HUD_COMPARE "Build R26-safe world path with R30 HUD/XYZRHW/SkyGlow overlay" ON)',
], "P1_CMKR_SOURCE_DEFAULT_R26_HUD")

# PASS 2 — the HMD-proven projected-rank mode is the production default.
require_all("src/hooks_uiscaling.cpp", [
    '"OUTRUN_VR_R57_MODE"',
    'return 6;',
    'return (value >= 0 && value <= 10) ? value : 6;',
], "P2_R57_SOURCE_DEFAULT")
require_all("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
    '"OUTRUN_VR_R57_MODE"',
    'return (value >= 0 && value <= 10) ? value : 6;',
], "P2_R57_RENDERER_DEFAULT")
require_all("tools/OutRunVR-Test-Selector.ps1", [
    "'DX9Ex + D3D11 Host','d3d9','R57_06_RANK_PROJECTED_HEAD'",
    "'DX11 Host DirectGPU','dx11','R57_06_RANK_PROJECTED_HEAD'",
    "'DXVK SAFE','dxvk-safe','R57_06_RANK_PROJECTED_HEAD'",
], "P2_SELECTOR_DEFAULT_R57_06")

selector = read("tools/OutRunVR-Test-Selector.ps1")
if selector.count("'R57_05_RANK_PROJECTED_IPD'=@") != 1 or selector.count("'R57_06_RANK_PROJECTED_HEAD'=@") != 1:
    errors.append("P2_SELECTOR_UNIQUE_SLOTS: R57_05/R57_06 diagnostic slot keys must each be defined exactly once")
else:
    passes.append("P2_SELECTOR_UNIQUE_SLOTS")
require_all("tools/Run-OutRunVRTest.ps1", [
    "'R57_06_RANK_PROJECTED_HEAD'",
    "$hudExperimentMode='2'; $r57Mode='6'",
], "P2_RUNNER_R57_06_MAPPING")

# PASS 3 — diagnostics stay disabled and exact queue ownership stays sticky.
require_all("src/hooks_uiscaling.cpp", [
    '"OUTRUN_VR_HUD_PROBE"',
    'int experimentMode = 2;',
    'OutRunVR::GameSemantic::SetHudExperimentMode(experimentMode);',
], "P3_HUD_SEMANTIC_DEFAULTS")
# Guard specifically against the accidental probe=6 regression.
probe = read("src/hooks_uiscaling.cpp")
m = re.search(r"static int VRHudProbeMode\(\) noexcept(?P<body>.*?)inline static std::atomic", probe, re.S)
if not m or "if (len == 0 || len >= sizeof(text))\n\t\t\t\treturn 0;" not in m.group("body"):
    errors.append("P3_HUD_PROBE_OFF: VRHudProbeMode default is not 0")
else:
    passes.append("P3_HUD_PROBE_OFF")

# PASS 4 — exact world-rank and POSITION producers cannot be dropped.
require_all("src/hooks_uiscaling.cpp", [
    'RankMarker_SpraniCalls[] = { 0xBB0FB, 0xBB133, 0xBB16C, 0xBB1A5 }',
    'RankMarker_ClipSpriteCalls[] = { 0xBB21F, 0xBB241, 0xBB271, 0xBB2BC, 0xBB2D0 }',
    'DispRank_SpraniCall = 0xB9DA6',
    '0xB9F3A, 0xB9F5E, 0xB9F81, 0xB9FD0',
    '0xB9FFC, 0xBA01E, 0xBA035, 0xBA052',
    'SpriteNodeOwner::DispRank',
    'RenderScope::ProjectedWorldMarker2D',
], "P4_RANK_AND_POSITION_OWNERS")

# PASS 5 — canonical font glyph and exact option arrows remain exact, never broad.
require_all("src/hooks_uiscaling.cpp", [
    'Module::exe_ptr(0x2C9DB)',
    '0xE358B, 0xE35A3, 0xE35CC, 0xE35F7',
    '0xE481B, 0xE4833, 0xE485C, 0xE4887',
    'VR R66 OPTION ARROW: exact node pinned',
], "P5_TEXT_AND_OPTION_ARROW")
forbid("src/hooks_uiscaling.cpp",
       'InjectHook(Module::exe_ptr(0x2D280)',
       "P5_NO_GLOBAL_PUT_CLIP_PROMOTION")

# PASS 6 — final GOAL/TIME owns only the reverse-proven goal caller edges.
require_all("src/hooks_uiscaling.cpp", [
    'Module::exe_ptr(0xBEA5A)',
    'Module::exe_ptr(0xBEA5F)',
    'GoalTime_TagHelper(0xBE020, "BE020")',
    'GoalTime_TagHelper(0xBE150, "BE150")',
    'VR R66 GOAL TIME HUD:',
], "P6_GOAL_TIME_EXACT_OWNER")

# PASS 7 — lens flare stays exact and uses the R26+HUD production path.
require_all("src/hooks_graphics.cpp", [
    'Module::exe_ptr(0xCABE)',
    'RenderScope::ProjectedScreenEffect2D',
    'VR R65 FLARE: exact EXE+0xCABE projected-alpha semantic installed',
], "P7_FLARE_EXACT_PRODUCER")
require_all("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
    'R30ScreenSpaceKind::ProjectedScreenEffect2D',
    'VR R65 FLARE FIX: exact projected-screen effect uses asymmetric-FOV affine only',
], "P7_FLARE_R26HUD_PATH")

# PASS 8 — selector shadow and START presentation protections remain present.
require_all("src/hooks_graphics.cpp", [
    '*Game::current_mode == GameState::STATE_SELECTOR',
    'VR R65 SELECTOR: restored base shadow bypassed',
], "P8_SELECTOR_SHADOW")
require_all("src/game_addrs.hpp", [
    'is_vr_gameplay_presentation()',
    'GameState::STATE_START',
    '*Game::game_start_progress_code == 65',
], "P8_START_GATE")
require("src/vr/d3d9/stereo_renderer_r7.inc",
        'return Game::is_vr_gameplay_presentation();',
        "P8_STEREO_SHARED_PREDICATE")
require("src/vr/game/outrun_renderer.cpp",
        'Game::is_vr_gameplay_presentation()',
        "P8_RENDERER_SHARED_PREDICATE")

# PASS 9 — canonical package builders explicitly pin R26+HUD.
require_all("tools/Build-OutRunPCFast.ps1", [
    "'-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF'",
    "'-DOUTRUN_VR_R26_HUD_COMPARE=ON'",
    "R66-PROVEN-R26HUD-v1",
    "ACTIVE_R26_HUD_R66",
], "P9_PC_FAST_CONTRACT")
require_all(".github/workflows/build.yml", [
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF',
    '-DOUTRUN_VR_R26_HUD_COMPARE=ON',
], "P9_GENERIC_BUILD_CONTRACT")
require_all(".github/workflows/vr-dx9ex-active.yml", [
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF',
    '-DOUTRUN_VR_R26_HUD_COMPARE=ON',
    "ACTIVE_R26_HUD_R66",
], "P9_DX9EX_BUILD_CONTRACT")
require_all(".github/workflows/vr-nightly-unified-20260926.yml", [
    'python tools/verify_vr_proven_baseline.py',
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF -DOUTRUN_VR_R26_HUD_COMPARE=ON -DOUTRUN_VR_C1_COMPARE=OFF -DOUTRUN_VR_C2_COMPARE=OFF',
    'VR R66 OPTION ARROW: exact node pinned',
], "P9_NIGHTLY_GUARDED")
require_all(".github/workflows/vr-unified-backends.yml", [
    'P4_R26_HUD_SAFE',
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF -DOUTRUN_VR_R26_HUD_COMPARE=ON -DOUTRUN_VR_C1_COMPARE=OFF -DOUTRUN_VR_C2_COMPARE=OFF',
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF -DOUTRUN_VR_R26_HUD_COMPARE=OFF -DOUTRUN_VR_C1_COMPARE=ON -DOUTRUN_VR_C2_COMPARE=OFF',
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF -DOUTRUN_VR_R26_HUD_COMPARE=OFF -DOUTRUN_VR_C1_COMPARE=OFF -DOUTRUN_VR_C2_COMPARE=ON',
], "P9_UNIFIED_VARIANTS_EXPLICIT")
require_all(".github/workflows/outrun-exe-hud-inspector.yml", [
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=ON -DOUTRUN_VR_R26_HUD_COMPARE=OFF -DOUTRUN_VR_C1_COMPARE=OFF -DOUTRUN_VR_C2_COMPARE=OFF',
], "P9_HUD_INSPECTOR_EXPLICIT")
require_all(".github/workflows/vr-openxr-r20.yml", [
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=ON -DOUTRUN_VR_R26_HUD_COMPARE=OFF -DOUTRUN_VR_C1_COMPARE=OFF -DOUTRUN_VR_C2_COMPARE=OFF',
], "P9_R20_DIAGNOSTIC_EXPLICIT")
require_all(".github/workflows/vr-openxr-r21.yml", [
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF -DOUTRUN_VR_R26_HUD_COMPARE=ON -DOUTRUN_VR_C1_COMPARE=OFF -DOUTRUN_VR_C2_COMPARE=OFF',
], "P9_R21_R26HUD_EXPLICIT")
require(".github/workflows/vr-openxr.yml",
        'outrun2006-vr-x86-r26-only-diagnostic-DO-NOT-PACKAGE',
        "P9_SAFE_ONLY_ARTIFACT_QUARANTINED")
forbid(".github/workflows/vr-openxr.yml",
       'name: outrun2006-vr-x86\n          path: build-vr-game/bin/dinput8.dll',
       "P9_NO_AMBIGUOUS_SAFE_ARTIFACT")

# PASS 10 — the binary contract must cover every new exact production edge.
contract = read("docs/VR_BINARY_CONTRACT.json")
required_contract_rvas = [
    "0x0002C9DB", # canonical glyph -> put_sprite_ex
    "0x0000CABE",  # lens flare -> DrawObjectAlpha_Internal
    "0x000BEA5A", # GOAL helper 020
    "0x000BEA5F", # GOAL helper 150
    "0x000E358B", "0x000E35A3", "0x000E35CC", "0x000E35F7",
    "0x000E481B", "0x000E4833", "0x000E485C", "0x000E4887"
]
missing_contracts = [r for r in required_contract_rvas if r not in contract]
if missing_contracts:
    errors.append(f"P10_BINARY_CONTRACT_COVERAGE: missing RVAs {missing_contracts}")
else:
    passes.append("P10_BINARY_CONTRACT_COVERAGE")

unique_passes = []
for p in passes:
    if p not in unique_passes:
        unique_passes.append(p)

for p in unique_passes:
    print("VR_PROVEN_BASELINE_PASS:", p)

if errors:
    for e in errors:
        print("VR_PROVEN_BASELINE_ERROR:", e, file=sys.stderr)
    print(f"VR proven baseline verification FAILED: {len(errors)} error(s).", file=sys.stderr)
    raise SystemExit(2)

print(f"VR proven baseline verification passed: {len(unique_passes)} guards.")
