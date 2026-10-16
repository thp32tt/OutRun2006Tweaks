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
BUDGET = ROOT / "src/vr/game/reflection_frame_budget.hpp"


def between(source: str, begin: str, end: str) -> str:
    return source.split(begin, 1)[1].split(end, 1)[0]


def verify(hook: str, r30: str, r33: str, budget: str) -> None:
    face = between(hook, "static void FaceCount_dest(", "\npublic:")
    # The original 18-ms safety backstop now lives inside the adaptive
    # cadence helper. Preserve both the measured-QPC path and conservative
    # original failure cutoffs, rather than enforcing the retired expression.
    assert "AdaptiveFrameCadence frameCadence{};" in face
    assert "frameSpike = frameCadence.Observe(dt);" in face
    assert "frameCadence.Reset();" in face
    assert "struct AdaptiveFrameCadence final" in budget
    assert "constexpr double OriginalLateSeconds = 0.018;" in budget
    assert "const bool cadenceMiss = healthySamples >= 4 &&" in budget
    assert "elapsedSeconds > referenceSeconds * 1.20 + 0.0005;" in budget
    assert "const bool late = elapsedSeconds > OriginalLateSeconds || cadenceMiss;" in budget
    assert "if (!late && elapsedSeconds >= FastestPlausible &&" in budget
    assert "if (healthySamples < 4)" in budget
    assert "frameScale60 = frameSpike ? 0.5f" in face
    assert "std::clamp(dt * 60.0, 0.0, 1.0)" in face
    assert "OutRunVR::ReflectionFrameBudget::Advance(" in face
    assert "Settings::ReflectionUpdateRate.get(), frameScale60," in face
    assert "Settings::VREnabled && Settings::VRNormalizeReflectionRate" in face
    assert "pendingFaces = budget.pendingFaces;" in face
    assert "ctx.eax = budget.faces;" in face
    assert "const int limit = vrNormalized ? (lateFrame ? 2 : 3) : 6;" in budget
    assert "std::clamp(elapsed60, 0.f, 1.f)" in budget
    assert "std::clamp(requestedRate, 0.f, 1.f)" in budget
    assert "std::clamp(requested - faces, 0.0, vrNormalized ? 1.0 : 6.0)" in budget
    assert "double(previous) + 6.0 * double(rate) * double(scaled)" in budget

    # Healthy 60/72/80/90/120-Hz periods retain the on-time face cap,
    # whereas a measured 12-ms frame misses a learned 120-Hz deadline even
    # though it falls below the original 18-ms backstop. This mathematical
    # sanity model complements the separately compiled native C++ regression.
    for hz in (60, 72, 80, 90, 120):
        dt = 1.0 / hz
        assert not (dt > 0.018 or dt > dt * 1.20 + 0.0005)
    for hz, dt, expected in (
        (120, 1 / 120, 3), (90, 1 / 90, 3),
        (72, 1 / 72, 3), (60, 1 / 60, 3),
        (120, 0.012, 2), (90, 0.015, 2),
        (60, 0.019, 2), (120, 0.025, 2),
    ):
        reference = 1.0 / hz
        spike = dt > 0.018 or dt > reference * 1.20 + 0.0005
        assert (2 if spike else 3) == expected
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
    budget = BUDGET.read_text(encoding="utf-8")
    verify(*original, budget)
    h, t, w = original
    mutations = [
        (h.replace("frameSpike = frameCadence.Observe(dt);", "frameSpike = false;", 1), t, w),
        (h.replace("frameCadence.Reset();", "/* cadence stale on VR disable */", 1), t, w),
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
            verify(*altered, budget)
        except (AssertionError, IndexError, ValueError):
            continue
        raise AssertionError(f"dense-scene mutation {i} survived")
    # The extracted Quest-style budget has become live source and must
    # retain the old 60 Hz workload, late-frame cap and bounded debt.
    budget_mutations = [
        budget.replace("OriginalLateSeconds = 0.018", "OriginalLateSeconds = 0.180", 1),
        budget.replace("healthySamples >= 4", "healthySamples >= 400", 1),
        budget.replace("OriginalLateSeconds || cadenceMiss", "OriginalLateSeconds && cadenceMiss", 1),
        budget.replace("referenceSeconds * 1.20 + 0.0005",
                       "referenceSeconds * 2.0 + 0.0005", 1),
        budget.replace("lateFrame ? 2 : 3", "lateFrame ? 6 : 6", 1),
        budget.replace("std::clamp(elapsed60, 0.f, 1.f)",
                       "std::clamp(elapsed60, 0.f, 2.f)", 1),
        budget.replace("std::clamp(requestedRate, 0.f, 1.f)",
                       "std::clamp(requestedRate, 0.f, 2.f)", 1),
        budget.replace("vrNormalized ? 1.0 : 6.0", "vrNormalized ? 6.0 : 6.0", 1),
        budget.replace("double(previous) + 6.0 * double(rate)",
                       "double(previous) + 12.0 * double(rate)", 1),
    ]
    for i, altered in enumerate(budget_mutations, 1):
        assert altered != budget, f"reflection budget mutation {i} missed"
        try:
            verify(*original, altered)
        except (AssertionError, IndexError, ValueError):
            continue
        raise AssertionError(f"reflection budget mutation {i} survived")
    print(f"PASS DX9Ex dense-scene five-area regression, {len(mutations)+len(budget_mutations)} destructive mutations; RUNTIME_VALIDATION=UNTESTED")


if __name__ == "__main__":
    main()