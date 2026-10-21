#!/usr/bin/env python3
"""DX9Ex review105 TEST-only source guard for F11 frustum and shader identity.

This gate is not a claim of headset optical correctness. The Windows build
runs the constexpr C++ F11 tests; these checks reject accidental source drift.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F11 = ROOT / "src/vr/d3d9/f11_screen_2d.hpp"
SHADER = ROOT / "src/vr/d3d9/shader_fingerprint_gpl.hpp"
TRANSPORT = ROOT / "src/vr/d3d9/stereo_renderer_r7.inc"


def check_f11(source: str) -> None:
    header = source.split("constexpr bool Build(", 1)[1].split(
        "constexpr bool TestEqualEyes()", 1
    )[0]
    for token in (
        "fov[0].left > fov[1].left",
        "fov[0].right < fov[1].right",
        "fov[0].down > fov[1].down",
        "fov[0].up < fov[1].up",
        "commonWidth <= 0.05f",
        "commonHeight <= 0.05f",
        "out[0] = candidate[0];",
        "out[1] = candidate[1];",
    ):
        assert token in header, token
    assert "0.5f * (fov[0].left + fov[1].left)" not in header
    assert "TestIntersectionInsideBothEyes()" in source
    assert "TestDisjointEyesKeepBoth()" in source
    assert "static_assert(TestIntersectionInsideBothEyes())" in source
    assert "static_assert(TestDisjointEyesKeepBoth())" in source


def check_shader(source: str) -> None:
    body = source.split("inline ShaderPair CaptureCurrent(", 1)[1].split(
        "inline bool RememberPair(", 1
    )[0]
    assert "result.vertex = HashBytecode(vertex);" in body
    assert "result.pixel = HashBytecode(pixel);" in body
    assert "if (vertex) vertex->Release();" in body
    assert "if (pixel) pixel->Release();" in body
    assert "HashBytecodeCached(" not in source
    assert "vsCache" not in source and "psCache" not in source
    assert "std::array<Seen, 256> seen{};" in source


def check_direct_eye(source: str) -> None:
    body = source.split("HRESULT StretchDirectEye(", 1)[1].split(
        "bool EnsureDirectTransportResources(", 1
    )[0]
    for token in (
        "OUTRUN_VR_DIRECT_EYE_POINT_TEST",
        "pointTest ? D3DTEXF_POINT : D3DTEXF_LINEAR",
        "if (FAILED(hr) && pointTest)",
        "if (FAILED(hr))",
        "D3DTEXF_NONE",
        "return hr;",
    ):
        assert token in body, token
    assert body.index("D3DTEXF_POINT") < body.index(
        "if (FAILED(hr) && pointTest)") < body.index(
        "D3DTEXF_NONE")



def check_optical_provenance(source: str) -> None:
    """Do not lose direct GOAL or mislabel scene/queue draws as physical owners."""
    goal = source.split("void R30TraceGoalOriginalC64Status(", 1)[1].split(
        "bool R30GetExtendedRawWvpForExactHud(", 1)[0]
    for token in (
        "const bool queued = OutRunVR::GameSemantic::QueueRenderActive();",
        "if (!queued && !cmd.IsExactFiniteResultHud())",
        "OutRunVR::GameSemantic::CurrentQueueProducerToken()",
        ": cmd.producer;",
        "cmd.queueEpoch,",
    ):
        assert token in goal, token

    optical = source.split("void R30TraceOpticalPhysicalEntry(", 1)[1].split(
        "HRESULT __stdcall DrawPrimitiveDestR30(", 1)[0]
    for token in (
        "!IsGameDevice(device) || InternalStereoPass",
        "Token::LensFlareCentre",
        "Token::StageExtensionTime",
        "cmd.IsExactFiniteResultHud()",
        "if (family == 3u)",
        "if (n > 24 && (n & (n - 1)) != 0)",
        "GetVertexShader(&vs)",
        "GetPixelShader(&ps)",
        "GetTexture(0, &tex)",
        "GetRenderTarget(0, &rt)",
        "GetSamplerState(0, D3DSAMP_MINFILTER",
        "if (rt) rt->Release();",
        "if (tex) tex->Release();",
        "if (ps) ps->Release();",
        "if (vs) vs->Release();",
    ):
        assert token in optical, token
    assert "SetRenderState" not in optical and "SetTexture" not in optical
    for api in range(4):
        entry = f"R30TraceOpticalPhysicalEntry(device, {api}u, type, primitiveCount);"
        assert source.count(entry) == 1, entry

    shader = source.split("HRESULT R30TryScreenSpaceFovDraw(", 1)[1].split(
        "template <typename ActualDraw, typename R29Draw>", 1)[0]
    assert shader.index("const auto traceCmd") < shader.index(
        "R30BuildScreenSpaceEyeConstants(device, stereo")
    assert "traceCmd.IsExactFiniteResultHud()" in shader
    assert "rightDrawAttempted = true;" in shader
    assert "rightDrawAttempted ? 1 : 0" in shader
    assert "VR R26 RESULT_SHADER_EYES:" in shader



def check_r62_goal_boundary(renderer: str, ui: str) -> None:
    """R62 restore failure is fatal for all physical owners; counters stay source-owned."""
    fixed = renderer.split("HRESULT R62TryFixedFunctionSpriteIndexed(", 1)[1].split(
        "void R30TraceOpticalPhysicalEntry(", 1)[0]
    assert "NoteRestoreFailure(" in fixed
    assert "R30ArmSafeFallback();" in fixed
    assert "return !restored && SUCCEEDED(hr) ? E_FAIL : hr;" in fixed
    assert "return exactResult && !restored" not in fixed
    assert fixed.index("R30ExecuteXyzrhwStereo(") < fixed.index(
        "bool restored = false;") < fixed.index(
        "return !restored && SUCCEEDED(hr) ? E_FAIL : hr;")

    queue = ui.split("static void BeforeQueueNode(const void* nextNode)", 1)[1].split(
        "static void BeforeQueueEnd() noexcept", 1)[0]
    assert "HudBatch.homogeneous &&" in queue
    assert "GoalOwner(HudBatch.scope, HudBatch.producer);" in queue
    assert "(outgoingGoal ? GoalFlushes : StageFlushes).fetch_add(" in queue
    assert "(outgoingGoal ? GoalFallbacks : StageFallbacks).fetch_add(" in queue
    assert queue.index("const bool outgoingGoal =") < queue.index(
        "FlushTracked(sprite)")
    assert "HudBatch.boundaryReady = enteringStage || enteringGoal;" in queue

    end = ui.split("static void BeforeQueueEnd() noexcept", 1)[1].split(
        "private:\n    static HRESULT __stdcall DrawDest(", 1)[0]
    assert "GoalOwner(HudBatch.scope, HudBatch.producer);" in end
    assert "(outgoingGoal ? GoalFlushes : StageFlushes).fetch_add(" in end
    assert "(outgoingGoal ? GoalFallbacks : StageFallbacks).fetch_add(" in end
    assert "HudBatch.matchesGpuOwner(" in end
    assert "HudBatch.producer == CurrentRenderProducerToken()" in end
    assert "HudBatch.boundaryReady = false;" in end


def main() -> None:
    f11 = F11.read_text(encoding="utf-8")
    shader = SHADER.read_text(encoding="utf-8")
    transport = TRANSPORT.read_text(encoding="utf-8")
    check_direct_eye(transport)
    check_f11(f11)
    check_shader(shader)
    renderer = (ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(
        encoding="utf-8")
    check_optical_provenance(renderer)
    ui = (ROOT / "src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
    check_r62_goal_boundary(renderer, ui)
    for changed_renderer, changed_ui in (
        (renderer.replace(
            "return !restored && SUCCEEDED(hr) ? E_FAIL : hr;",
            "return exactResult && !restored && SUCCEEDED(hr) ? E_FAIL : hr;", 1), ui),
        (renderer, ui.replace(
            "(outgoingGoal ? GoalFlushes : StageFlushes).fetch_add(",
            "StageFlushes.fetch_add(", 1)),
        (renderer, ui.replace(
            "(outgoingGoal ? GoalFallbacks : StageFallbacks).fetch_add(",
            "StageFallbacks.fetch_add(", 1)),
    ):
        try:
            check_r62_goal_boundary(changed_renderer, changed_ui)
        except AssertionError:
            pass
        else:
            raise AssertionError("R62/GOAL negative source mutation escaped")
    for original, mutated in (
        ("if (!queued && !cmd.IsExactFiniteResultHud())",
         "if (!queued)"),
        ("if (!Settings::VRTelemetry || !device ||\n                !IsGameDevice(device) || InternalStereoPass)",
         "if (!Settings::VRTelemetry || !device ||\n                !IsGameDevice(device))"),
        ("rightDrawAttempted = true;", "rightDrawAttempted = false;"),
    ):
        assert original in renderer, original
        try:
            check_optical_provenance(renderer.replace(original, mutated, 1))
        except AssertionError:
            pass
        else:
            raise AssertionError("Optical provenance mutation escaped: " + original)
    f11_mutations = (
        ("fov[0].left > fov[1].left", "fov[0].left < fov[1].left"),
        ("fov[0].right < fov[1].right", "fov[0].right > fov[1].right"),
        ("commonHeight <= 0.05f", "commonHeight < -1.0f"),
    )
    for old, new in f11_mutations:
        assert old in f11
        try:
            check_f11(f11.replace(old, new, 1))
        except AssertionError:
            continue
        raise AssertionError("F11 source mutation escaped: " + old)
    for old, new in (
        ("result.vertex = HashBytecode(vertex);", "result.vertex = {};"),
        ("result.pixel = HashBytecode(pixel);", "result.pixel = {};"),
    ):
        assert old in shader
        try:
            check_shader(shader.replace(old, new, 1))
        except AssertionError:
            continue
        raise AssertionError("shader identity mutation escaped: " + old)
    mutated_transport = transport.replace(
        "pointTest ? D3DTEXF_POINT : D3DTEXF_LINEAR",
        "D3DTEXF_POINT", 1)
    try:
        check_direct_eye(mutated_transport)
    except AssertionError:
        pass
    else:
        raise AssertionError("DirectGPU point-filter unconditional mutation escaped")
    print("PASS DX9Ex review105 F11, shader lifetime, DirectGPU A/B and R26 optical provenance; 12 negative mutations; HMD UNTESTED")


if __name__ == "__main__":
    main()
