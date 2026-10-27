#!/usr/bin/env python3
"""Static negative controls for read-only C993/CABE diagnostic provenance."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
GAME = ROOT / "src/vr/game/outrun_renderer.cpp"
HOOK = ROOT / "src/hooks_graphics.cpp"


def check(r30: str, game: str, hook: str) -> None:
    body = r30.split("HRESULT R30TryScreenSpaceFovDraw(", 1)[1].split(
        "HRESULT R30GuardScreenSpace(", 1
    )[0]
    game_body = game.split("HRESULT __stdcall SetVertexShaderConstantFDest(", 1)[1]
    projected = hook.split("static void __cdecl DrawObjectAlphaProjected(", 1)[1].split(
        "static constexpr bool IsProjectedSunScreenObject(", 1
    )[0]
    centre = hook.split("static void __cdecl DrawObjectAlphaCentre(", 1)[1].split(
        "public:", 1
    )[0]

    # Native draw logging cannot identify an original descriptor without an
    # opaque 4056D0/4052C0 transaction join. Never label these as proven IDs.
    for phrase in (
        "VR LENS R30 PHYSICAL CLASS:",
        "VR LENS R30 PHYSICAL EYES:",
        "opaqueObject=UNLINKED shaderForm=UNOBSERVED",
        "eyeRT=LEFT_RIGHT_TRANSACTION object=UNLINKED",
        "Settings::VRTelemetry",
        "n <= 32 || (n & (n - 1)) == 0",
        "OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D",
        "OutRunVR::GameSemantic::RenderScope::SceneEffect",
        "std::memcmp(eyeConstants[0], eyeConstants[1],",
        "TopLevelDrawSerial()",
        "stereo.poseSequence",
        "leftHr=0x{:08X} rightHr=0x{:08X} restore={}",
    ):
        assert phrase in body, "missing physical receipt contract: " + phrase
    assert body.index("VR LENS R30 PHYSICAL CLASS:") < body.index(
        "if (screenKind == R30ScreenSpaceKind::None)")
    assert body.index("const HRESULT leftHr = actualDraw();") < body.index(
        "VR LENS R30 PHYSICAL EYES:") < body.index(
        "const bool pairComplete = SUCCEEDED(rightHr) && restoreOk;")
    assert body.count("rightHr = actualDraw();") == 1
    assert body.count("const HRESULT leftHr = actualDraw();") == 1
    assert "return r29Draw();" in r30.split("HRESULT R30GuardScreenSpace(", 1)[1][:750]

    for phrase in (
        "VR LENS GAME C64 GATE:",
        "nativeResult=NOT_YET_OBSERVED",
        "physicalDraw=UNLINKED",
        "projectedLensWithSyncedCamera ? 1 : 0",
        "CullingCameraOverridden ? 1 : 0",
        "CorroboratesProjectedScreenEffect(",
    ):
        assert phrase in game_body, "missing game c64 source marker: " + phrase
    assert game_body.index("VR LENS GAME C64 GATE:") > game_body.index(
        "const bool projectedLensWithSyncedCamera =")
    assert game_body.index("VR LENS GAME C64 GATE:") < game_body.index(
        "const bool semanticOverlay =")
    assert "VR LENS C993 SOURCE ADMISSION:" in centre
    assert "physicalDraw=UNOBSERVED opaqueFlush=UNOBSERVED" in centre
    assert "VR LENS 570008 ORIGINAL BOTH DRAWN" in projected
    assert "physicalDraw=UNOBSERVED" in projected
    assert "Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);" in projected
    assert "Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);" in centre


def main() -> None:
    r30 = R30.read_text(encoding="utf-8-sig")
    game = GAME.read_text(encoding="utf-8-sig")
    hook = HOOK.read_text(encoding="utf-8-sig")
    check(r30, game, hook)
    mutations = [
        (0, "opaqueObject=UNLINKED shaderForm=UNOBSERVED", "object=570008"),
        (0, "eyeRT=LEFT_RIGHT_TRANSACTION object=UNLINKED", "object=570002"),
        (0, "std::memcmp(eyeConstants[0], eyeConstants[1],", "true /* fake eye equality */("),
        (0, "Settings::VRTelemetry &&", "true &&"),
        (1, "nativeResult=NOT_YET_OBSERVED", "nativeResult=SUCCESS"),
        (1, "physicalDraw=UNLINKED", "physicalDraw=C993"),
        (2, "physicalDraw=UNOBSERVED opaqueFlush=UNOBSERVED", "physicalDraw=CONFIRMED opaqueFlush=CONFIRMED"),
        (2, "VR LENS 570008 ORIGINAL BOTH DRAWN", "VR LENS ONE ONLY"),
    ]
    values = [r30, game, hook]
    for idx, old, new in mutations:
        assert old in values[idx], "missing negative mutation: " + old
        mutated = values.copy()
        mutated[idx] = mutated[idx].replace(old, new, 1)
        try:
            check(*mutated)
        except AssertionError:
            continue
        raise AssertionError("unsafe lens provenance mutation escaped: " + old)
    print("PASS lens C993/CABE source+game-c64+R30 native eye receipts; "
          "8 negative mutations, no game optics changes; HMD UNTESTED")


if __name__ == "__main__":
    main()
