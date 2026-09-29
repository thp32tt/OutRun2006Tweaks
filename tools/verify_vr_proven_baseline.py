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

# The R26+HUD production wrapper must describe and hook the chain it actually
# compiles. Stale R29 names previously made source review look like renderer R29
# was inherited even though this production owner deliberately stops at R26/R23.
require_all("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
    '#include "stereo_renderer_r26.cpp"',
    'R30DrawPrimitiveR26Hook',
    'R30PresentR26Hook',
    'reinterpret_cast<void*>(&DrawPrimitiveDestR26)',
    'reinterpret_cast<void*>(&PresentDestR27)',
    'const auto r26 = R26InstallState.load(',
], "P1_R26_HUD_ACTUAL_LOWER_OWNER")
for stale in [
    "R30DrawPrimitiveR29Hook",
    "R30DrawIndexedPrimitiveR29Hook",
    "R30DrawPrimitiveUPR29Hook",
    "R30DrawIndexedPrimitiveUPR29Hook",
    "R30PresentR29Hook",
    "R30ResetR29Hook",
    "R29 prerequisite failed",
    "R29 remains active",
]:
    forbid("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
           stale, f"P1_NO_STALE_R29_OWNER_{stale}")

# PASS 2 — R69 CLEAN fixes projected-rank ownership to one production path.
for rel in [
    "src/hooks_uiscaling.cpp",
    "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
    "tools/Run-OutRunVRTest.ps1",
]:
    forbid(rel, "OUTRUN_VR_R57_MODE", f"P2_NO_R57_MODE_SELECTOR_{rel}")

require_all("src/hooks_uiscaling.cpp", [
    "R57RankProducerScope(bool) noexcept",
    "RenderScope::ProjectedWorldMarker2D",
    "constexpr bool exactPositionOwner = true;",
], "P2_FIXED_PRODUCER_OWNERSHIP")
require_all("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
    "VR R69 CLEAN PROJECTED MARKER:",
    "fixed projected-world-marker production path active",
], "P2_FIXED_RENDERER_PATH")
require_all("tools/OutRunVR-Test-Selector.ps1", [
    "& $selector -Backend d3d9 -TestProfile $profile -VariantId $variant",
    "Invoke-R71Test 'CORRECTNESS' 'R71_HUD_FLARE'",
    "Invoke-R71Test 'HUD_MENU' 'R71_HUD_MENU'",
], "P2_SELECTOR_R71_EVENING")
selector = read("tools/OutRunVR-Test-Selector.ps1")
for variant in ["R71_HUD_FLARE", "R71_HUD_MENU"]:
    if selector.count(variant) != 1:
        errors.append(f"P2_SELECTOR_UNIQUE_R71: {variant} must appear exactly once in the evening GUI")
if not any(e.startswith("P2_SELECTOR_UNIQUE_R71") for e in errors):
    passes.append("P2_SELECTOR_UNIQUE_R71")
for stale in ["R57_01_POSITION_KIND1_HUD35", "R57_05_RANK_PROJECTED_IPD", "R57_10_RANK_PROJECTED_TRACE"]:
    if stale in selector:
        errors.append(f"P2_SELECTOR_NO_STALE_R57: stale selector entry present: {stale}")
if not any(e.startswith("P2_SELECTOR_NO_STALE_R57") for e in errors):
    passes.append("P2_SELECTOR_NO_STALE_R57")
require_all("tools/Run-OutRunVRTest.ps1", [
    "'R69_FIXPACK' { $semanticMode='0'; $hudExperimentMode='2' }",
    "'R71_HUD_FLARE' { $semanticMode='0'; $hudExperimentMode='2' }",
    "'R71_HUD_MENU' { $semanticMode='0'; $hudExperimentMode='2' }",
], "P2_RUNNER_R69_R71_MAPPING")

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
    '0x2C808, 0x2C9DB',
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
    'VR R67 FLARE: exact EXE+0xCABE semantic installed; Calc3D2D view anchor will be reprojected per eye',
], "P7_FLARE_EXACT_PRODUCER")
require_all("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
    'R30ScreenSpaceKind::ProjectedScreenEffect2D',
    'VR R73 FLARE FIX: exact projected-screen effect uses reduced-disparity Calc3D2D reprojection',
], "P7_FLARE_R26HUD_PATH")
require_all("src/vr/game/render_semantics.hpp", [
    'CorroboratesProjectedScreenEffect',
    'scope == RenderScope::ProjectedScreenEffect2D',
], "P7_FLARE_PROJECTED_SCREEN_OWNER")
require_all("src/vr/game/outrun_renderer.cpp", [
    'CorroboratesProjectedScreenEffect(',
    'PROJECTED_SCREEN_EFFECT_2D',
    'R30 owns exactly one HUD/flare/world-billboard transform',
], "P7_FLARE_SINGLE_TRANSFORM_OWNER")
require_all("src/vr/d3d9/stereo_renderer_r26.cpp", [
    'RenderScope::ProjectedScreenEffect2D',
    'PROJECTED_SCREEN_EFFECT_2D stay exclusively owned by R30',
], "P7_FLARE_R28_WORLD_REBIND_VETO")
require_all("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
    'std::clamp(Settings::SkyGlowFactor.get(), 1, 16)',
    'Keep the stereo',
    'factor semantics',
], "P7_R70_SKYGLOW_FACTOR_SETTING")
forbid("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
       "constexpr int factor = 2;",
       "P7_NO_FORCED_SKYGLOW_FACTOR2")

# PASS 8 — VR keeps stock PC shadow behavior and selector texture headroom.
require_all("src/hooks_graphics.cpp", [
    'if (Settings::VREnabled)',
    'VR R69 BASE SHADOW: restored console shadow disabled for all VR presentations; stock PC nullsub behavior ACTIVE',
], "P8_SELECTOR_SHADOW")
require_all("src/vr/d3d9/stereo_renderer_r26.cpp", [
    'R71TraceStartGridShadowCandidate',
    'Game::is_vr_gameplay_presentation()',
    'D3DRS_STENCILENABLE',
    'R71StartShadowDiagHits',
    'hit > 32 && (hit & (hit - 1)) != 0',
    'VR R71 START SHADOW DIAG:',
], "P8_R71_START_SHADOW_BOUNDED_DIAG")
require_all("src/vr/d3d9/ex_device_upgrade_r14.cpp", [
    'R69IsSelectorAtlasReserveCandidate',
    'desc.Width == 2048 && desc.Height == 2048',
    'R14GeneralShadowBytes',
    'R14EmergencyShadowBytes',
    'R14EmergencyShadowBudgetBytes',
    'std::uint64_t bytes, bool emergencyReserve,',
    'bool selectorAtlasReserve',
    'R73SelectorAuxShadowBudgetBytes',
    'R73SelectorAuxShadowBytes',
    'emergency > R14EmergencyShadowBudgetBytes - bytes',
    'currentEmergency >',
    'R72IsSelectorReserveCandidate',
    'D3DFMT_DXT1',
    'atlas keeps dedicated 16 MiB headroom',
    'bool selectorAtlas = false',
    'R14FirstSelectorUploadLogged',
    'exact 2048x2048 selector/car atlas CPU-shadow upload succeeded',
    'R71IsSelectorCompanionDiagnosticCandidate',
    'desc.Height == 512 || desc.Height == 1024',
    'CPU-shadow budget reject',
    'companion SYSTEMMEM CreateTexture failed',
    'companion entered DirectOnly',
    'correlate this pointer with later R13 LockRect failure',
], "P8_SELECTOR_ATLAS_RESERVE")
require_all("src/vr/d3d9/ex_device_upgrade_r13.cpp", [
    'VR R71 SELECTOR DIAG: translated MANAGED LockRect FAILED ptr=0x{:08X}',
    'rect=[{},{},{},{}]',
    'size={}x{} fmt={} levels={}',
    'correlate exact pointer with R14 companion DirectOnly fallback',
], "P8_SELECTOR_LOCK_DIAG")
require_all("src/hooks_uiscaling.cpp", [
    'Module::exe_ptr(0xBA9D0)',
    'Module::exe_ptr(0xBAAA0)',
    'Module::exe_ptr(0xBAAEA)',
    'R70ExactScreenHudClipSpriteCalls',
    '0x460F1, 0x463D6, 0x46410',
    '0x97BB7, 0x97DA7',
], "P8_R70_OUTRUN_HUD_EXACT_OWNERS")
require_all("src/vr/hud_semantics.hpp", [
    '"HUD_MENU_ARROW"',
    '"HUD_OUTRUN_RESULT"',
    'ClassifyCaller(0x0460F1)',
    'ClassifyCaller(0x097BB7)',
], "P8_R70_RUNTIME_SEMANTICS")
require_all("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
    'R71: the R70 HMD run proved the old "dead work"',
    'R30SkyGlow.reduced[eye];',
    'compositeSource = R30SkyGlow.temp[eye];',
], "P8_R71_SKYGLOW_FINAL_BLUR_SOURCE")
require_all("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
    'R30SkyGlowAppliedEpoch',
    'R30SkyGlowPreHudAttemptEpoch',
    'R30CompositeSkyGlowBeforeHud',
    'R30SkyGlowPreHudAttemptEpoch != PresentEpoch',
    'the additive glow no longer washes over HUD/menu pixels at Present',
], "P8_R71_SKYGLOW_PRE_HUD_COMPOSITE")
require_all("src/hooks_uiscaling.cpp", [
    'R71RivalMarkerSpraniCall = 0xBB796',
    'Module::exe_ptr(0xBB6F5)',
    'R71RivalMarker_sprani',
    'R71RivalMarkerTaggedNodes',
    'RenderScope::ProjectedWorldMarker2D',
    '&markerSnapshot',
    'exact 0xBB796 nodes pinned PROJECTED_WORLD_MARKER_2D',
    '0x975EE, 0x97727, 0x977FB',
    'R71OutRunPrintEnter',
    'R71OutRunPrintLeave',
    'R71OutRunPrintTailsBefore',
    'R70TagAppendedSpriteNodes(',
    'R71OutRunStageTaggedNodes',
    'exact Sumo_Printf queue nodes pinned SCREEN_HUD',
], "P8_R71_RIVAL_AND_OUTRUN_STAGE_TEXT")
require_all("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
    'VR R71 HUD ALPHA DIAG:',
    'D3DRS_SEPARATEALPHABLENDENABLE',
    'D3DRS_SRCBLENDALPHA',
    'D3DRS_DESTBLENDALPHA',
    'D3DRS_BLENDOPALPHA',
    'D3DRS_ALPHAREF',
    'D3DRS_ALPHAFUNC',
], "P8_R71_HUD_ALPHA_DIAGNOSTIC")

require_all("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
    'R73OutRunTransientHudActive',
    '*Game::game_mode != 32',
    'GameState::STATE_GOAL',
    'GameState::STATE_RESULT',
    'R73OutRunTransientHudPresents = 360',
    'directScreenKind == R30ScreenSpaceKind::ScreenOverlay2D',
    'VR R73 OUTRUN HUD:',
    'constexpr bool R73BypassStereoSkyGlow = true',
    'VR R73 FLARE:',
    'FlareStereoDepth = 0.20f',
], "P8_R73_RUNTIME_VISUALFIX")

require_all("src/hooks_uiscaling.cpp", [
    'R74OutRunResultProgressCallA = 0x97BE4',
    'R74OutRunResultProgressCallB = 0x97DEC',
    'R74ResultProgressEnter',
    'R74ResultProgressLeave',
    'VR R74 OUTRUN RESULT PROGRESS:',
], "P8_R74_OUTRUN_RESULT_PROGRESS_EXACT")
require_all("src/vr/hud_semantics.hpp", [
    '"HUD_OUTRUN_STAGE"',
    'callRva == 0x0975EE || callRva == 0x097727',
    'callRva == 0x0977FB',
    '"WORLD_RIVAL_PROJECTED"',
    'callRva == 0x0BB6F0 || callRva == 0x0BB796',
    'ClassifyCaller(0x0975EE)',
    'ClassifyCaller(0x0BB6F0)',
], "P8_R71_OUTRUN_STAGE_SEMANTICS")
forbid("src/vr/hud_semantics.hpp",
       "InRange(callRva, 0x097300, 0x097F00)",
       "P8_NO_BROAD_R71_OUTRUN_RANGE")
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
require_all("src/vr/d3d9/ex_device_upgrade_r15.cpp", [
    'no pre-Reset state-block replay',
    'D3D9 state blocks are device-reset-sensitive COM objects. Never',
], "P8_RESET_STATEBLOCK_REGRESSION")
require("src/vr/d3d9/stereo_renderer_r23.cpp",
        'VR R23/R25 BASELINE: authoritative first seed opened only after live viewport/scissor + full game draw serial + current-generation depth + fresh current-frame pose; R20/R22 double approval removed',
        "P8_AUTHORITATIVE_SEED")
require("src/vr/d3d9/stereo_renderer_r22.cpp",
        'VR R22 GAME: shadow-tracked viewport/scissor replay + common initial depth baseline + R21 eligibility gate ACTIVE',
        "P8_R22_VIEWPORT_DEPTH")
require("src/vr/d3d9/stereo_renderer_r13.cpp",
        'VR R13: stereo hardening ACTIVE;',
        "P8_R13_HARDENING")
require_all("vrhost/src/main_r23.cpp", [
    'Do not publish the legacy global consumed-frame',
    'R32 arms an EVENT after the',
    'dedicated per-slot GPU-completion ACK only when',
], "P8_DIRECTGPU_COPY_ACK_ORDER")

# PASS 9 — canonical package builders explicitly pin R26+HUD.
require_all("tools/Build-OutRunPCFast.ps1", [
    "'-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF'",
    "'-DOUTRUN_VR_R26_HUD_COMPARE=ON'",
    "R66-PROVEN-R26HUD-v1",
    "Set-Content (Join-Path $backendDir 'VARIANT_ID.txt') 'ACTIVE_R26_HUD_R73'",
    "VariantId = 'R73_PC_VISUALFIX'",
], "P9_PC_FAST_CONTRACT")
forbid("tools/Build-OutRunPCFast.ps1",
       "VariantId = 'ACTIVE_FULL_R34'",
       "P9_NO_STALE_PC_FAST_VARIANT_ID")
forbid("tools/Build-OutRunPCFast.ps1",
       "VariantId = 'ACTIVE_R26_HUD_R66'",
       "P9_NO_STALE_R66_PC_FAST_VARIANT_ID")
require_all(".github/workflows/build.yml", [
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF',
    '-DOUTRUN_VR_R26_HUD_COMPARE=ON',
], "P9_GENERIC_BUILD_CONTRACT")
require_all(".github/workflows/vr-dx9ex-active.yml", [
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF',
    '-DOUTRUN_VR_R26_HUD_COMPARE=ON',
    "ACTIVE_R26_HUD_R69",
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

require_all("tools/OutRunVR-Test-Selector.ps1", [
    "R71_HUD_FLARE",
    "R71_HUD_MENU",
    "OutRun 2006 VR R71 - HUD / Lens Flare Test",
    "OutRun2_VR_ANALYZE_*.zip",
], "P9_R71_EVENING_SELECTOR")
require_all("tools/START_HERE_VR_TEST.cmd", [
    "R71 - HUD / LENS FLARE EVENING TEST",
    "OutRunVR-Test-Selector.ps1",
    "OutRun2_VR_ANALYZE_*.zip",
], "P9_R71_ONE_CLICK_SELECTOR")
require_all("tools/Collect-OutRunVRLogs.ps1", [
    "'HUD_OPACITY='",
    "'OUTRUN_STAGE_TEXT='",
    "'RIVAL_MARKER='",
    "'LENS_FLARE='",
    "ANALYSIS_REQUEST.json",
], "P9_R71_RESULT_AND_ANALYSIS_CONTRACT")

# PASS 10 — the binary contract must cover every new exact production edge.
contract = read("docs/VR_BINARY_CONTRACT.json")
import json
contract_json = json.loads(contract)
bad_sig_lengths = [
    item.get("id", "<unknown>")
    for item in contract_json.get("contracts", [])
    if len("".join(str(item.get("expectedBytes", "")).split())) !=
       int(item.get("signatureLength", 16)) * 2
]
if bad_sig_lengths:
    errors.append(f"P10_BINARY_CONTRACT_LENGTHS: invalid signature hex lengths {bad_sig_lengths}")
else:
    passes.append("P10_BINARY_CONTRACT_LENGTHS")
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