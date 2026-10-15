#!/usr/bin/env python3
"""Single-pass whole-source OutRun VR cross-domain result/+TIME audit.

Scan all first-party production source and tooling once per changed SHA.
Never spin 1000/5000 over unchanged HUD source. This is a risk inventory,
not a headset optical validator or proof of a manual line-by-line review.
"""
from __future__ import annotations
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ("src", "vrhost/src", "tools")
SUFFIXES = {".cpp", ".hpp", ".h", ".inc", ".py", ".ps1"}
PATTERNS = {
    "broad_game_state": r"Game::is_in_game\s*\(",
    "shared_stereo_presentation": r"Game::is_vr_gameplay_presentation\s*\(",
    "sbs_eligibility": r"StereoWanted\s*\(",
    "host_theater": r"PresentationTheater",
    "render_ownership": r"GameSemantic::|RenderScope::|ProducerToken::",
    "result_progress": r"0x97BE4|0x97DEC",
    "result_stage": r"0x975EE|0x97727|0x977FB",
    "goal_time": r"0xBEA5A|0xBEA5F",
    "generic_glyph": r"0x2C808|0x2C9DB",
    "time_advance": r"fn43FA10\s*\(",
    "fixedfn_sprite": r"R62TryFixedFunctionSpriteIndexed|0x00000142u",
    "pre_draw_c64": r"SetVertexShaderConstantFDest|GetLastRawGameWvpWrite",
    "no_tick_replay": r"SumoUISpriteReplay|vrProjectedMarker",
    "xr_layer": r"finalLayerKind|XrCompositionLayerQuad|XrCompositionLayerProjection",
}
records: dict[str, list[str]] = {name: [] for name in PATTERNS}
all_sources = []
for folder in SOURCE_DIRS:
    for path in sorted((ROOT / folder).rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        relative = path.relative_to(ROOT).as_posix()
        content = path.read_text(encoding="utf-8-sig", errors="replace")
        all_sources.append(relative)
        for label, pattern in PATTERNS.items():
            if re.search(pattern, content):
                records[label].append(relative)

def require(test: bool, description: str) -> None:
    if not test:
        raise SystemExit("VR WHOLE-SOURCE P0 RESULT FAILURE: " + description)

def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def body(text: str, marker: str) -> str:
    start = text.find(marker)
    require(start >= 0, "missing " + marker)
    opening = text.find("{", start)
    require(opening >= 0, "missing brace for " + marker)
    depth = 0
    for idx in range(opening, len(text)):
        if text[idx] == "{":
            depth += 1
        elif text[idx] == "}":
            depth -= 1
            if not depth:
                return text[opening:idx + 1]
    raise SystemExit("VR WHOLE-SOURCE P0 RESULT FAILURE: unclosed " + marker)

require(len(all_sources) >= 200, "source inventory unexpectedly reduced")
for label in PATTERNS:
    require(bool(records[label]), "disappeared full-source risk anchor " + label)

r7 = source("src/vr/d3d9/stereo_renderer_r7.inc")
game = body(r7, "bool GameplayActive()")
policy = "if (!Game::is_vr_gameplay_presentation())"
broad = "if (Game::is_in_game())"
require(game.find(policy) >= 0 and
        game.find(broad) > game.find(policy),
        "game generates SBS during host mono Theater result/continue states")
shared = body(source("src/game_addrs.hpp"),
              "inline bool is_vr_gameplay_presentation() noexcept")
for theater in ("STATE_TRYAGAIN", "STATE_OUTRUNMILES"):
    require(theater not in shared,
            "host Theater state promoted to gameplay: " + theater)
for gameplay in ("STATE_GOAL", "STATE_TIMEUP", "STATE_LINK_TIMEUP"):
    require(gameplay in shared,
            "GOAL/TIMEUP host game state removed: " + gameplay)
renderer = source("src/vr/game/outrun_renderer.cpp")
require("return Game::is_vr_gameplay_presentation()" in renderer,
        "host-facing client presentation diverged from shared predicate")
hud = source("src/hooks_uiscaling.cpp")
for address in ("0x975EE", "0x97727", "0x977FB",
                "0x97BE4", "0x97DEC", "0xBEA5A", "0xBEA5F",
                "0x2C808", "0x2C9DB"):
    require(address in hud, "original exact result/+TIME producer missing: " +
            address)
for token in ("OutRunStagePrintf", "ResultProgress", "GoalTimeHelper",
              "OutRunHudText"):
    require("ProducerToken::" + token in hud,
            "result parent lost true source identity: " + token)
r30 = source("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
require("R62TryFixedFunctionSpriteIndexed(" in r30 and
        "fvf != 0x00000142u" in r30 and
        "VR P0 RESULT DRAW ROUTE" in r30,
        "shader/fixed-function end-owner or result telemetry missing")
framerate = source("src/hooks_framerate.cpp")
require("Game::fn43FA10(numUpdates)" in framerate and
        "entry.vrProducer" in framerate,
        "original extension-time tick or replay provenance broken")
host = source("vrhost/src/main_r23.cpp")
require("requestedPresentation == OutRunVR::PresentationGameplay" in host and
        "if (presentation != OutRunVR::PresentationGameplay)" in host,
        "host missing projection vs mono Theater transition boundaries")

# Sources on disk are not necessarily production artifacts. Guard the exact
# Win32 game + x64 host BUILD GRAPH: the packaged DX9Ex candidate uses
# R26+HUD, not R33-only compare, and the host runs main_r23.cpp rather than
# the older inert main.cpp. Never claim a review of the wrong source owns VR.
game_cmake = source("CMakeLists.txt")
host_cmake = source("vrhost/CMakeLists.txt")
active_workflow = source(".github/workflows/vr-dx9ex-active.yml")
require("option(OUTRUN_VR_R26_HUD_COMPARE" in game_cmake and
        "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp" in game_cmake,
        "packaged R26+HUD game renderer source graph disappeared")
require("add_executable(outrun-vr-host" in host_cmake and
        "src/main_r23.cpp" in host_cmake,
        "reviewed OpenXR host main_r23.cpp no longer compiled")
require('cmake -S . -B build-game' in active_workflow and
        '-DOUTRUN_VR_R26_HUD_COMPARE=ON' in active_workflow,
        "DX9Ex package no longer builds reviewed R26+HUD game path")
require('cmake -S . -B build-full-chain' in active_workflow and
        '-DOUTRUN_VR_REFACTOR_SPLIT_R33_R32=ON' in active_workflow,
        "R33 full-chain CI must remain a separate compile comparison")

report = {
    "schemaVersion": 1,
    "status": "SOURCE_CROSS_DOMAIN_CONTRACT_PASS_RUNTIME_HMD_UNTESTED",
    "scannedFiles": len(all_sources),
    "sourceRoots": list(SOURCE_DIRS),
    "productionGameBackend": "Win32 R26 + R30 HUD",
    "productionHostEntry": "vrhost/src/main_r23.cpp",
    "comparisonOnlyCompile": "Win32 R33",
    "riskReferences": records,
    "resultOriginalCallsites": ["975EE", "97727", "977FB", "97BE4",
                                "97DEC", "BEA5A", "BEA5F", "2C808",
                                "2C9DB"],
    "note": ("A single-pass complete source-path risk scan and bounded exact "
             "contracts, not a claim that every file was manually reviewed "
             "or that result/+TIME is visually resolved in Quest 3."),
}
print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
