#!/usr/bin/env python3
"""Static negative controls for read-only C993/CABE diagnostic provenance."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
GAME = ROOT / "src/vr/game/outrun_renderer.cpp"
HOOK = ROOT / "src/hooks_graphics.cpp"
SEM = ROOT / "src/vr/game/render_semantics.hpp"


def check(r30: str, game: str, hook: str, sem: str) -> None:
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
        "opaqueObject=WINDOW_LINKED_ONLY",
        "VR LENS R30 SOURCE JOIN:",
        "DEFERRED_WINDOW_CANDIDATE",
        "tex0=0x{:X} tex={}x{} fmt={}",
        "vb0=0x{:X} offset={} stride={}",
        "colorWrite=0x{:X} alphaBlend={}",
        "rawWvpHash=0x{:016X}",
        "leftRT=0x{:X} leftRTDesc={}x{}:{}",
        "rightRT=0x{:X} rightRTDesc={}x{}:{} sameRT={}",
        "vsHr=0x{:08X} vsBound={} fvfHr=0x{:08X}",
        "fvf=0x{:08X}",
        "device->GetVertexShader(&liveVs)",
        "device->GetFVF(&liveFvf)",
        "liveVs->Release()",
        "eyeRT=LEFT_RIGHT_TRANSACTION",
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
    assert "const bool lensPhysicalCandidate = Settings::VRTelemetry &&" in body
    assert body.index("VR LENS R30 PHYSICAL CLASS:") < body.index(
        "if (screenKind == R30ScreenSpaceKind::None)")
    assert body.index("const HRESULT leftHr = actualDraw();") < body.index(
        "VR LENS R30 PHYSICAL EYES:") < body.index(
        "const bool pairComplete = SUCCEEDED(rightHr) && restoreOk;")
    assert body.count("rightHr = actualDraw();") == 1
    assert body.count("const HRESULT leftHr = actualDraw();") == 1
    lower = r30.split("HRESULT R30GuardScreenSpace(", 1)[1].split(
        "// Share the existing R62", 1
    )[0]
    assert "VR LENS R30 LOWER FALLBACK:" in lower
    assert "reason=R30_NOT_ADMITTED" in lower
    assert "lowerActualDraw=NOT_YET_OBSERVED object=UNLINKED" in lower
    assert lower.index("VR LENS R30 LOWER FALLBACK:") < lower.index(
        "const HRESULT lowerHr = r29Draw();")
    assert "const HRESULT lowerHr = r29Draw();" in lower
    assert "VR TRACE VISUAL LOWER PHYSICAL RESULT FULL:" in lower
    assert "opaquePmtIdentity={}" in lower
    assert "INLINE_CALL_STACK_PMT_UNVERIFIED" in body
    assert "opaquePmtIdentity=UNVERIFIED" in body

    for phrase in (
        "VR LENS CAMERA SYNC:",
        "fieldD4={:.5f},{:.5f},{:.5f}",
        "vector3A8={:.5f},{:.5f},{:.5f}",
        "view140OriginValid={}",
        "correctedViewOrigin={:.5f},{:.5f},{:.5f}",
    ):
        assert phrase in game, "missing lens camera provenance: " + phrase

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
    # A wrapper can overlap a native entry; retain the explicit "candidate"
    # qualifier until the original opaque descriptor and flush generation join.
    assert "VR TRACE LENS C64 PROOF FULL:" in r30
    assert "VR TRACE LENS R30 ENTRY FULL:" in body
    assert "VR TRACE LENS LOWER FALLBACK FULL:" in lower
    assert "VR TRACE LENS GPU STATE FULL:" in body
    assert "VR TRACE LENS MATRIX FULL:" in body
    assert "VR TRACE LENS SOURCE FULL:" in hook
    assert "VR TRACE LENS CENTRE ENTER FULL:" in hook
    assert "VR TRACE LENS CENTRE LEAVE FULL:" in hook
    assert "VR LENS R30 INLINE SOURCE ENTRY:" in body
    assert "opaqueDescriptor=UNLINKED" in body
    assert "provenance=CALL_STACK_ONLY" in body
    assert "lensInline.sourceSerial != 0" in body
    assert "ScopedLensOriginalCall inlineSource(" in projected
    assert "ArmLensDeferredPhysical(" in projected
    assert "ClearLensDeferredPhysical();" in projected
    assert "sourceOrdinal == 1" in projected
    assert "VR LENS 570008 DEFERRED WINDOW ARM:" in projected
    assert "VR LENS 570008 DEFERRED WINDOW CLOSE:" in projected
    assert "struct LensDeferredPhysicalReceipt" in sem
    assert "CurrentLensDeferredPhysical" in sem
    # Retail-byte PMT identity is now available only while the exact
    # 405890 -> 404700 entry wrapper is active. Generic SceneEffect and
    # source-window receipts remain candidate-only.
    for phrase in (
        "VR TRACE LENS PMT ENTRY FULL:",
        "authority=EXACT_RETAIL_405890_CALL_404700",
        "Module::exe_ptr(0x5A41)",
        "Module::exe_ptr(0x5C44)",
        "TraceLensOpaquePmtEntry",
        "receipt.objectId = entry[14];",
        "receipt.pass = entry[8];",
        "queueLayout=EXE_PROVEN_405160_4052C0",
    ):
        assert phrase in hook, "missing exact opaque PMT entry trace: " + phrase
    for phrase in (
        "struct LensOpaquePmtEntryReceipt",
        "CurrentLensOpaquePmtEntry",
        "ScopedLensOpaquePmtEntry",
    ):
        assert phrase in sem, "missing PMT entry TLS receipt: " + phrase
    assert "EXACT_RETAIL_405890_404700_PMT_ENTRY" in r30
    assert "pmtObjectId=0x{:06X}" in r30
    assert "pmtEntrySerial={}" in r30
    effective_pmt = sem.split("inline RenderScope EffectiveScope()", 1)[1].split(
        "inline void ArmNextDraw", 1
    )[0]
    assert "CurrentLensOpaquePmtEntry" not in effective_pmt, (
        "PMT diagnostic receipt must not grant EffectiveScope"
    )
    # The original 4052C0 queue is multi-object: the interval receipt is
    # diagnostics only and must never gain EffectiveScope/render authority.
    assert "DeferredLensProjectedOwnsPhysicalDraw" not in sem
    effective = sem.split("inline RenderScope EffectiveScope()", 1)[1].split(
        "inline void ArmNextDraw", 1)[0]
    assert "CurrentLensDeferredPhysical" in effective
    assert "return RenderScope::ProjectedScreenEffect2D;" not in effective
    for phrase in (
        "exactSourceLinked={}",
        "windowAnchorSerial={}",
        "windowAnchorObj=0x{:X}",
        "windowAnchorOrdinal={}",
        "DEFERRED_WINDOW_CANDIDATE",
    ):
        assert phrase in body, "missing candidate-only deferred provenance: " + phrase
    assert "lensInlineLinked ? lensInline.sourceSerial : 0" in body
    assert "lensInlineLinked ? lensInline.objectId : 0" in body
    assert body.count("lensInlineLinked ? 1 : 0") >= 3
    assert centre.count("ScopedLensOriginalCall inlineSource(") == 2
    assert "sourceCallSerial" in centre and "sourceCallSerial" in projected
    assert "ordinalMaySpanSunCalls={}" in projected
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
    sem = SEM.read_text(encoding="utf-8-sig")
    check(r30, game, hook, sem)
    mutations = [
        (0, "opaqueObject=WINDOW_LINKED_ONLY", "opaqueObject=PROVEN_DESCRIPTOR"),
        (0, "DEFERRED_WINDOW_CANDIDATE", "OPAQUE_DESCRIPTOR_PROOF"),
        (0, "lensInlineLinked ? 1 : 0", "1 /* unsafe exact source claim */"),
        (0, "INLINE_CALL_STACK_PMT_UNVERIFIED", "OPAQUE_PMT_PROVEN"),
        (0, "device->GetFVF(&liveFvf)", "D3D_OK"),
        (0, "eyeRT=LEFT_RIGHT_TRANSACTION", "eyeRT=FAKE_SINGLE_RT"),
        (0, "std::memcmp(eyeConstants[0], eyeConstants[1],", "true /* fake eye equality */("),
        (0, "const bool lensPhysicalCandidate = Settings::VRTelemetry &&",
            "const bool lensPhysicalCandidate = true &&"),
        (1, "VR LENS CAMERA SYNC:", "VR CAMERA GENERIC:"),
        (1, "fieldD4={:.5f},{:.5f},{:.5f}", "fieldD4=OMITTED"),
        (1, "nativeResult=NOT_YET_OBSERVED", "nativeResult=SUCCESS"),
        (1, "physicalDraw=UNLINKED", "physicalDraw=C993"),
        (2, "physicalDraw=UNOBSERVED opaqueFlush=UNOBSERVED", "physicalDraw=CONFIRMED opaqueFlush=CONFIRMED"),
        (2, "VR LENS 570008 ORIGINAL BOTH DRAWN", "VR LENS ONE ONLY"),
        (0, "provenance=CALL_STACK_ONLY", "provenance=OPAQUE_MATCH"),
        (0, "opaqueDescriptor=UNLINKED", "opaqueDescriptor=570008"),
        (2, "ordinalMaySpanSunCalls={}", "ordinalIsFrameProof=1"),
        (2, "ArmLensDeferredPhysical(", "/* removed deferred bridge */"),
        (0, "rawWvpHash=0x{:016X}", "rawWvpHash=OMITTED"),
        (0, "sameRT={}", "sameRT=ASSUMED_ZERO"),
        (3, "if (ExactLensCentreDrawOwnsSemantic())",
            "if (CurrentLensDeferredPhysical.sourceSerial != 0) return RenderScope::ProjectedScreenEffect2D;\n        if (ExactLensCentreDrawOwnsSemantic())"),
    ]
    values = [r30, game, hook, sem]
    for idx, old, new in mutations:
        assert old in values[idx], "missing negative mutation: " + old
        mutated = values.copy()
        # Full diagnostics intentionally repeat the exact-source receipt in
        # multiple observational log lines. For this provenance mutation,
        # mutate every receipt so an added log cannot absorb the single
        # replacement while leaving the actual unsafe assertion untouched.
        if old in (
            "lensInlineLinked ? 1 : 0",
            "INLINE_CALL_STACK_PMT_UNVERIFIED",
            "DEFERRED_WINDOW_CANDIDATE",
        ):
            mutated[idx] = mutated[idx].replace(old, new)
        else:
            mutated[idx] = mutated[idx].replace(old, new, 1)
        try:
            check(*mutated)
        except AssertionError:
            continue
        raise AssertionError("unsafe lens provenance mutation escaped: " + old)
    print("PASS lens C993/CABE inline + candidate-only deferred window receipts; "
          f"{len(mutations)} destructive negative controls; "
          "no game optics changes; HMD UNTESTED")


if __name__ == "__main__":
    main()
