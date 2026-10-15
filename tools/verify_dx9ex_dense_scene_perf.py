#!/usr/bin/env python3
"""DX9Ex dense-scene P0-B source guards: five fixes and destructive regressions.

This is a static/portable regression suite. Real Quest3/VDXR timing remains
RUNTIME_VALIDATION=UNTESTED until independently captured on matching hardware.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "src/hooks_graphics.cpp"
R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
R33 = ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp"


def between(source: str, begin: str, end: str) -> str:
    return source.split(begin, 1)[1].split(end, 1)[0]


def verify(hook: str, r30: str, r33: str) -> None:
    face = between(hook, "static void FaceCount_dest(", "\npublic:")
    assert "frameSpike = dt > 0.018;" in face
    assert "frameScale60 = frameSpike ? 0.5f" in face
    assert "std::clamp(dt * 60.0, 0.0, 1.0)" in face
    assert "const int maxFaces = vrNormalized ? (frameSpike ? 2 : 3) : FacesPerCubemap;" in face
    assert "pendingFaces = std::clamp(pendingFaces - float(faces), 0.0f," in face
    assert "vrNormalized ? 1.0f : float(FacesPerCubemap)" in face

    # The previously problematic 120-Hz 0.5 cadence must NOT be interpreted
    # as a spike. Only elapsed dt >18ms triggers the two-face recovery cap.
    for dt, expected in ((1 / 120, 3), (1 / 90, 3),
                         (1 / 72, 3), (1 / 60, 3),
                         (0.025, 2), (0.033, 2), (0.25, 2)):
        spike = dt > 0.018
        max_faces = 2 if spike else 3
        assert max_faces == expected
        frame_scale = 0.5 if spike else min(1.0, max(0.0, dt * 60.0))
        assert frame_scale <= 1.0

    shadow = between(r30, "R30ShadowPtr R30EnsureVertexShadow(", "R30ShadowPtr R30EnsureIndexShadow(")
    assert shadow.index("buffer->GetDesc(&desc)") < shadow.index("if (desc.FVF != 0 &&")
    assert "(desc.FVF & D3DFVF_POSITION_MASK) != D3DFVF_XYZRHW" in shadow
    assert shadow.index("D3DFVF_XYZRHW") < shadow.index("std::make_shared<R30BufferShadow>()")

    active = between(r30, "bool R30GameGlowActive()", "bool R30CaptureSkyGlowSceneBeforeHud(")
    assert "(*Module::exe_ptr<std::uint8_t>(0x39FCD5) & 3) == 2" in active
    assert "*Module::exe_ptr<int>(0x4A8C40) != 0" in active
    capture = between(r30, "bool R30CaptureSkyGlowSceneBeforeHud(", "bool R30ApplyStereoSkyGlow(")
    composite = between(r30, "bool R30ApplyStereoSkyGlow(", "ULONGLONG R30LastTelemetryMs")
    assert capture.index("!R30GameGlowActive()") < capture.index("R29OwnerCaptureFrameSnapshot()")
    assert capture.index("R29OwnerCaptureFrameSnapshot()") < capture.index("device->StretchRect(")
    assert composite.index("!R30GameGlowActive()") < composite.index("R29OwnerCaptureFrameSnapshot()")
    assert "R30SkyGlowSceneCaptureEpoch != frame.presentEpoch" in composite

    world = between(r33, "R32ReviewOwnedResult R33TryFastWorld(", "R32ReviewOwnedResult R33TryHud(")
    # The conservative translucent route is an explicit visual rollback.
    # Do not permit any alpha/disabled-ZWRITE draw through R33's fast WVP.
    assert "OutRunVR::State::StateBlockTracker::Reliable()" in world
    fragile_guard = ("if (fragile)\n            {\n"
                     "                if (R33TelemetryEnabled())\n"
                     "                    R32ReviewNoteDispatchFragile();\n"
                     "                return {};\n            }")
    assert fragile_guard in world
    assert world.index(fragile_guard) < world.index("R32ReviewEnsureStereoResources(")
    assert "R33FragileWorldDepthEligible()" not in world
    assert "OutRunVR::GameSemantic::CorroboratesWorld(scope)" not in world
    # Preserve only one in-function right-pass attachment query.
    assert world.count("R32ReviewTrackedDepthStencil()") == 1

    cull = between(hook, "class DisableStageCulling : public Hook", "class DisableVehicleLODs")
    assert 'Setting<bool> DisableStageCulling{ "Graphics", "DisableStageCulling", true,' in hook
    assert "patch.set(Settings::DisableStageCulling.get());" in cull
    assert "!Settings::VREnabled.get()" not in cull
    anis = between(hook, "class AnisotropicFiltering : public Hook", "class VSyncOverride")
    assert "static bool PreserveScreenTextureFiltering() noexcept" in anis
    assert "RenderScope::ScreenHud" in anis
    assert "RenderScope::ScreenOverlay2D" in anis
    assert anis.count("PreserveScreenTextureFiltering()") >= 4
    second = between(anis, "static void destination2(", "\npublic:")
    assert "if (ctx.edi == D3DSAMP_MINFILTER)" in second
    assert second.index("if (ctx.edi == D3DSAMP_MINFILTER)") < second.index("ctx.esi = D3DTEXF_ANISOTROPIC;")
    assert "D3DSAMP_MAXANISOTROPY" not in second  # single setter remains in destination


def main() -> None:
    original = (H.read_text(encoding="utf-8"), R30.read_text(encoding="utf-8"),
                R33.read_text(encoding="utf-8"))
    verify(*original)
    h, t, w = original
    mutations = [
        (h.replace("frameSpike = dt > 0.018;", "frameSpike = false;", 1), t, w),
        (h.replace("frameSpike ? 2 : 3", "frameSpike ? 6 : 6", 1), t, w),
        (h.replace("std::clamp(dt * 60.0, 0.0, 1.0)",
                   "std::clamp(dt * 60.0, 0.0, 2.0)", 1), t, w),
        (h.replace("patch.set(Settings::DisableStageCulling.get());",
                   "patch.set(Settings::DisableStageCulling.get() && !Settings::VREnabled.get());", 1), t, w),
        (h.replace("RenderScope::ScreenHud", "RenderScope::None", 1), t, w),
        (h, t.replace("desc.FVF != 0", "desc.FVF == 0", 1), w),
        (h, t.replace("!= D3DFVF_XYZRHW", "== D3DFVF_XYZRHW", 1), w),
        (h, t.replace("0x4A8C40) != 0", "0x4A8C40) == 0", 1), w),
        (h, t.replace("!R30GameGlowActive()", "false", 1), w),
        (h, t, w.replace("if (fragile)\n            {",
                          "if (false)\n            {", 1)),
        (h, t, w.replace("R32ReviewNoteDispatchFragile();\n                return {};",
                          "R32ReviewNoteDispatchFragile();\n                /* unsafe promoted alpha */", 1)),
        (h.replace('Setting<bool> DisableStageCulling{ "Graphics", "DisableStageCulling", true,',
                   'Setting<bool> DisableStageCulling{ "Graphics", "DisableStageCulling", false,', 1), t, w),
    ]
    for i, altered in enumerate(mutations, 1):
        assert altered != original, f"mutation {i} missed"
        try:
            verify(*altered)
        except (AssertionError, IndexError, ValueError):
            continue
        raise AssertionError(f"dense-scene mutation {i} survived")
    print(f"PASS DX9Ex dense-scene five-area regression, {len(mutations)} destructive mutations; RUNTIME_VALIDATION=UNTESTED")


if __name__ == "__main__":
    main()
