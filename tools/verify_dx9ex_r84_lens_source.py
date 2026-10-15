#!/usr/bin/env python3
"""C993 centre lens original-WVP source: R84 read-only proof regression.

The exact sun producer must match its own shader, c64 write, call/pose epoch,
bounded draw age and nonqueued source. Never infer a stock WVP from the already
head-injected live D3D9 constants. Rendering stays unchanged pending HMD.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ROOT / "src/vr/core/r29_owner_api.hpp",
    ROOT / "src/vr/d3d9/stereo_renderer_r29.cpp",
    ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp",
    ROOT / "src/vr/d3d9/lens_centre_source_provenance.hpp",
    ROOT / ".github/workflows/vr-dx9ex-active.yml",
)

def check(api, r29, r30, evidence, workflow):
    assert "std::uint64_t R29OwnerTopLevelDrawSerial() noexcept;" in api
    assert "std::uint64_t R29OwnerTopLevelDrawSerial() noexcept" in r29
    assert "return GetTopLevelDrawSerial();" in r29
    assert '#include "lens_centre_source_provenance.hpp"' in r30
    block = r30.split("bool R30HasExactLensCentreRawWvp(", 1)[1].split(
        "R30ScreenSpaceKind R30ClassifyScreenSpacePass(", 1)[0]
    for name in (
        "QueueRenderActive()",
        "EffectiveScope() != RenderScope::WorldBillboard",
        "CurrentRenderProducerToken() != ProducerToken::LensFlareCentre",
        "GetLastRawGameWvpWrite(",
        "GetLastGameWvpSemanticProvenance(",
        "R29OwnerCurrentShaderEpoch(",
        "CurrentLensCentreCallEpoch",
        "GetLastGameWvpLensCentreCallEpoch()",
        "GetCurrentLatchedPoseEpoch()",
        "OutRunVRRenderer::GetLastGameWvpPoseEpoch(),",
        "R29OwnerTopLevelDrawSerial() + 1u",
        "sourceScope == RenderScope::WorldBillboard",
        "sourceProducer == ProducerToken::LensFlareCentre",
        "queueNode == nullptr",
        "OutRunVR::LensCentre::OwnsRawWvp({",
    ):
        assert name in block, "R84 exact C993 evidence lost: " + name
    route = r30.split("R30ScreenSpaceKind R30ClassifyScreenSpacePass(", 1)[1].split(
        "// Only the OpenXR pose/FOV signature affects this affine.", 1)[0]
    for name in (
        "if (Settings::VRTelemetry &&",
        "CurrentRenderProducerToken() ==",
        "ProducerToken::LensFlareCentre)",
        "R30HasExactLensCentreRawWvp(originalGameWvp)",
        "VR R84 C993 RAW_WVP_SOURCE: {}",
        'owned ? "EXACT_OWNER" : "MISSING_OR_STALE"',
        "return R30ScreenSpaceKind::None;",
    ):
        assert name in route, "C993 telemetry or fail-closed route lost: " + name
    assert route.index("R30HasExactLensCentreRawWvp(originalGameWvp)") < route.index(
        "return R30ScreenSpaceKind::None;", route.index(
            "R30HasExactLensCentreRawWvp(originalGameWvp)"))
    assert "return R30ScreenSpaceKind::FlatPerspectiveEffect;" in route
    assert "e.currentCall == e.writtenCall" in evidence
    assert "e.currentPoseEpoch == e.writtenPoseEpoch" in evidence
    assert "e.shaderEpoch == e.writtenShaderEpoch" in evidence
    assert "e.nextDraw - e.writtenDraw <= 128u" in evidence
    assert "static_assert(!OwnsRawWvp(" in evidence
    assert "run: python tools/verify_dx9ex_r84_lens_source.py" in workflow

def main():
    src = tuple(path.read_text(encoding="utf-8-sig") for path in SOURCES)
    check(*src)
    tests = (
        (0, "std::uint64_t R29OwnerTopLevelDrawSerial() noexcept;", "// no facade"),
        (1, "return GetTopLevelDrawSerial();", "return 0;"),
        (2, "QueueRenderActive()", "false"),
        (2, "sourceProducer == ProducerToken::LensFlareCentre", "true"),
        (2, "R29OwnerCurrentShaderEpoch(currentShader, currentShaderEpoch)", "true"),
        (2, "OutRunVRRenderer::GetLastGameWvpPoseEpoch(),", "0,"),
        (2, "R29OwnerTopLevelDrawSerial() + 1u", "0"),
        (2, "if (Settings::VRTelemetry &&", "if (true &&"),
        (3, "e.nextDraw - e.writtenDraw <= 128u", "true"),
        (4, "run: python tools/verify_dx9ex_r84_lens_source.py", "run: echo UNTESTED"),
    )
    for index, old, new in tests:
        assert old in src[index], "negative mutation fixture missing: " + old
        damaged = list(src)
        damaged[index] = damaged[index].replace(old, new, 1)
        try:
            check(*damaged)
        except (AssertionError, IndexError):
            continue
        raise AssertionError("C993 source ownership mutation escaped: " + old)
    print(f"R84 C993 lens source proof PASS ({len(tests)} mutations), "
          "physical renderer unchanged; HMD UNTESTED")

if __name__ == "__main__":
    main()
