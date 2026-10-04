#!/usr/bin/env python3
"""Verify the shared VR producer semantic catalog stays synchronized."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "src" / "vr" / "game" / "disasm_render_contract.hpp"
HUD = ROOT / "src" / "vr" / "hud_semantics.hpp"
RUNTIME_SEMANTICS = ROOT / "src" / "vr" / "game" / "render_semantics.hpp"
OUTRUN_RENDERER = ROOT / "src" / "vr" / "game" / "outrun_renderer.cpp"
R30_RENDERER = ROOT / "src" / "vr" / "d3d9" / "stereo_renderer_r30_overlay.inc"
ANALYZER = ROOT / "tools" / "analyze_outrun_exe.py"

ENTRY_RE = re.compile(
    r'\{\s*0x([0-9A-Fa-f]+)u,\s*0x([0-9A-Fa-f]+)u,\s*'
    r'"([^"]+)",\s*"([^"]+)",\s*'
    r'SpacePolicy::(ScreenHud|WorldBillboard|ProjectedWorldMarker2D|'
    r'ProjectedScreenEffect2D)\s*\}'
)
POLICY_NAMES = {
    "ScreenHud": "SCREEN_HUD",
    "WorldBillboard": "WORLD_BILLBOARD",
    "ProjectedWorldMarker2D": "PROJECTED_WORLD_MARKER_2D",
    "ProjectedScreenEffect2D": "PROJECTED_SCREEN_EFFECT_2D",
}


def load_analyzer_ranges(source: str) -> list[tuple]:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "SEMANTIC_RANGES"
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        return [tuple(item) for item in value]
    raise AssertionError("SEMANTIC_RANGES assignment not found")


def load_contract_ranges(source: str) -> list[tuple]:
    ranges = [
        (
            int(begin, 16),
            int(end, 16),
            area,
            semantic,
            POLICY_NAMES[policy],
        )
        for begin, end, area, semantic, policy in ENTRY_RE.findall(source)
    ]
    if not ranges:
        raise AssertionError("CriticalProducerRanges entries not found")
    return ranges


def main() -> int:
    contract_ranges = load_contract_ranges(CONTRACT.read_text(encoding="utf-8"))
    analyzer_ranges = load_analyzer_ranges(ANALYZER.read_text(encoding="utf-8"))

    if contract_ranges != analyzer_ranges:
        missing = [item for item in contract_ranges if item not in analyzer_ranges]
        extra = [item for item in analyzer_ranges if item not in contract_ranges]
        raise AssertionError(
            "semantic catalog drift: "
            f"contract={len(contract_ranges)} analyzer={len(analyzer_ranges)} "
            f"missing_in_analyzer={missing!r} extra_in_analyzer={extra!r}"
        )

    if len(contract_ranges) != 25:
        raise AssertionError(
            f"expected 25 reviewed producer ranges, found {len(contract_ranges)}"
        )

    hud_source = HUD.read_text(encoding="utf-8")
    if "OutRunVR::DisasmContract::CriticalProducerRanges" not in hud_source:
        raise AssertionError("runtime HUD classifier does not consume shared catalog")
    if "InRange(callRva" in hud_source:
        raise AssertionError("runtime HUD classifier still contains a duplicate range map")

    contract_source = CONTRACT.read_text(encoding="utf-8")
    runtime_source = RUNTIME_SEMANTICS.read_text(encoding="utf-8")
    for policy in ("ProjectedWorldMarker2D", "ProjectedScreenEffect2D"):
        if policy not in contract_source:
            raise AssertionError(f"F15 shared SpacePolicy missing {policy}")
        if f"SpacePolicy::{policy}" not in hud_source:
            raise AssertionError(f"F15 HUD policy naming missing {policy}")
        if (
            f"Policy::{policy}" not in runtime_source
            or f"RenderScope::{policy}" not in runtime_source
        ):
            raise AssertionError(
                f"F15 shared-to-runtime projected policy bridge missing {policy}"
            )

    # R71 c64 ownership-lifetime bridge: production mode 2 may surface only
    # an exact queue semantic at WVP-upload time. Generic queue overlays must
    # remain ScreenOverlay2D until the draw path consumes them.
    for marker in (
        "ResolveWvpUploadScope(",
        "mode >= 2 && IsExactHudScope(queueExactScope)",
        "EffectiveWvpUploadScope()",
        "2, RenderScope::ScreenOverlay2D, RenderScope::None",
        "1, RenderScope::ScreenOverlay2D, RenderScope::ScreenHud",
    ):
        if marker not in runtime_source:
            raise AssertionError(
                f"R71 c64 exact-queue ownership contract missing marker: {marker}"
            )

    # Set 04 F16: exact SpriteNode ownership must fail closed under abnormal
    # table pressure. Never evict an already-published live tag to admit a
    # newer producer; expose rejection telemetry and behavior-test recovery
    # once capacity becomes available again.
    for marker in (
        "SpriteNodeSemanticOverflowRejected",
        "Preserve every published tag",
        "reject only this newest unique registration",
    ):
        if marker not in runtime_source:
            raise AssertionError(
                f"F16 fail-closed semantic overflow contract missing marker: {marker}"
            )
    if "std::size_t oldest = 0" in runtime_source:
        raise AssertionError(
            "F16 regression: full semantic table still replaces the oldest live tag"
        )

    cmake_source = (ROOT / "vrhost" / "CMakeLists.txt").read_text(encoding="utf-8")
    workflow_source = (
        ROOT / ".github" / "workflows" / "vr-openxr.yml"
    ).read_text(encoding="utf-8")
    overflow_smoke_source = (
        ROOT / "vrhost" / "tests" / "semantic_tag_overflow_smoke.cpp"
    ).read_text(encoding="utf-8")
    for marker in (
        "SpriteNodeSemanticCapacity",
        "SpriteNodeSemanticOverflowRejected",
        "ConsumeSpriteNodeScope(Node(0))",
        "RenderScope::ScreenOverlay2D",
        "RenderScope::ProjectedWorldMarker2D",
    ):
        if marker not in overflow_smoke_source:
            raise AssertionError(
                f"F16 semantic overflow behavior smoke missing marker: {marker}"
            )
    if "outrun-vr-semantic-tag-overflow-smoke" not in cmake_source:
        raise AssertionError("F16 semantic overflow smoke is not in the host build graph")
    if (
        "Run SpriteNode semantic overflow regression" not in workflow_source
        or "outrun-vr-semantic-tag-overflow-smoke.exe" not in workflow_source
    ):
        raise AssertionError("F16 semantic overflow smoke is not executed by OpenXR CI")

    renderer_source = OUTRUN_RENDERER.read_text(encoding="utf-8")
    if "OutRunVR::GameSemantic::EffectiveWvpUploadScope()" not in renderer_source:
        raise AssertionError(
            "R71 renderer c64 path does not consume exact queue ownership"
        )
    if "SCREEN_OVERLAY_2D remains generic and is never promoted" not in renderer_source:
        raise AssertionError(
            "R71 renderer c64 guard lost generic-overlay non-promotion rationale"
        )

    r30_source = R30_RENDERER.read_text(encoding="utf-8")

    # L1-VIS-002 / SkyGlow: the stereo world glow must be composited before
    # recognized HUD/non-world overlay draws. Present is only a fallback when
    # no pre-HUD attempt occurred; a failed pre-HUD attempt must not retry over UI.
    for marker in (
        "R30SkyGlowAppliedEpoch",
        "R30SkyGlowPreHudAttemptEpoch",
        "R30CompositeSkyGlowBeforeHud(",
        "R30SkyGlowPreHudAttemptEpoch = PresentEpoch",
        "R30SkyGlowAppliedEpoch = PresentEpoch",
        "R30SkyGlowAppliedEpoch != PresentEpoch",
        "R30SkyGlowPreHudAttemptEpoch != PresentEpoch",
        "if (!state.worldEffect)\n                R30CompositeSkyGlowBeforeHud(device);",
        "Composite completed world glow before the first recognized HUD",
    ):
        if marker not in r30_source:
            raise AssertionError(
                f"DXVK SkyGlow pre-HUD composite contract missing marker: {marker}"
            )

    helper_pos = r30_source.find("bool R30CompositeSkyGlowBeforeHud(")
    present_pos = r30_source.find("HRESULT __stdcall PresentDestR30(")
    if helper_pos < 0 or present_pos < 0 or helper_pos > present_pos:
        raise AssertionError("SkyGlow pre-HUD helper must be defined before Present fallback")
    if r30_source.count("R30CompositeSkyGlowBeforeHud(device);") < 2:
        raise AssertionError(
            "SkyGlow pre-HUD composite must cover both non-world XYZRHW and recognized HUD paths"
        )

    # DX9EX-FINGERPRINT-001: diagnostics may fingerprint exact queue owners,
    # projected screen effects, and generic queue overlays only while the queue
    # renderer is active. Fingerprints are bounded and never grant ownership.
    for marker in (
        "R30DrawFingerprintCapacity = 64",
        "R30FingerprintEligible(",
        "QueueRenderActive()",
        "GplShaderFingerprint::CaptureCurrent(device)",
        "VR DRAW FP:",
        "R30TraceDrawFingerprint(",
        "ScreenOverlay2D, false",
        "SceneEffect, true",
    ):
        if marker not in r30_source:
            raise AssertionError(
                f"R71 bounded draw-fingerprint contract missing marker: {marker}"
            )


    # DXVK/R71 rank-marker provenance: do not regress to the older generic
    # WORLD_BILLBOARD sidecar. The current path reconstructs the exact
    # Calc3D2D rank view point, carries it with the SpriteNode exact semantic,
    # and reaches the per-eye ProjectedWorldMarker2D draw path. Runtime visual
    # correctness is still a Quest3/VDXR gate.
    ui_source = (ROOT / "src" / "hooks_uiscaling.cpp").read_text(encoding="utf-8")
    for marker in (
        "Module::exe_ptr(0xBAEE7)",
        "recoverViewPoint(RankMarkerProjectedInfo)",
        "R57RankProducerScope(true)",
        "R57RankProducerScope(false)",
        "RenderScope::ProjectedWorldMarker2D",
        "ScopedProducerSemantic producer(",
        "RegisterSpriteNodeScope(",
        "node, r57Scope, r57Marker",
    ):
        if marker not in ui_source:
            raise AssertionError(
                f"DXVK rank projected-marker producer contract missing marker: {marker}"
            )

    for marker in (
        "ProjectedMarkerInfo projectedMarker{}",
        "CurrentQueueProjectedMarker",
        "CurrentProjectedMarker()",
        "projectedMarker ? *projectedMarker : ProjectedMarkerInfo{}",
    ):
        if marker not in runtime_source:
            raise AssertionError(
                f"DXVK rank projected-marker queue contract missing marker: {marker}"
            )

    r30_safe_source = (
        ROOT / "src" / "vr" / "d3d9" / "stereo_renderer_r30_r26_safe.cpp"
    ).read_text(encoding="utf-8")
    for marker in (
        "CorroboratesProjectedWorldMarker(",
        "R57BuildProjectedMarkerDelta(",
        "state.projectedWorldMarker2D = semanticProjectedWorld",
        "const bool applyHeadCorrection =",
        "explicitMarker == nullptr",
        "(R57Mode() == 6 || R57Mode() == 8)",
        "VR R68 PROJECTED MARKER:",
    ):
        if marker not in r30_safe_source:
            raise AssertionError(
                f"DXVK rank projected-marker draw contract missing marker: {marker}"
            )

    analyzer_source = (
        ROOT / "tools" / "Analyze-OutRunVRSession.ps1"
    ).read_text(encoding="utf-8")
    for marker in (
        "RankProjectedMarkerDrawEvidenceAvailable",
        "RankProjectedMarkerDrawFingerprintCount",
        "'PROJECTED_WORLD_MARKER_2D'",
        "$_.ExactQueueScope -and $_.ProjectedMarker",
    ):
        if marker not in analyzer_source:
            raise AssertionError(
                f"DXVK rank projected-marker analyzer contract missing marker: {marker}"
            )

    expected_f14 = {
        (0x060900, 0x061100, "ctrl_icon_work", "HUD_CTRL_ICON", "SCREEN_HUD"),
        (0x0BBA00, 0x0BBC00, "DispTempHeartNum", "HUD_TEMP_HEART", "SCREEN_HUD"),
    }
    if not expected_f14.issubset(set(contract_ranges)):
        raise AssertionError("F14 ranges are missing from the shared catalog")

    print(f"VR semantic catalog contract: OK ({len(contract_ranges)} ranges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
