#!/usr/bin/env python3
"""DX9Ex 00683: preserve synchronous live pose ownership without per-draw copies."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "src/vr/ipc/protocol.hpp"
GAME = ROOT / "src/vr/game/outrun_renderer.cpp"
DISPATCH = ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp"


def body(src: str, signature: str) -> str:
    at = src.index(signature)
    begin = src.index("{", at)
    depth = 0
    for i in range(begin, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[begin:i + 1]
    raise AssertionError("unclosed function " + signature)


def verify(api: str, game: str, dispatch: str) -> None:
    assert "const LatchedStereoFrame* GetLatchedStereoFrameView() noexcept;" in api
    # Old copying API remains available for consumers that need an owned snapshot.
    assert "bool GetLatchedStereoFrame(LatchedStereoFrame& out);" in api
    assert "out = LatchedStereo;" in body(game, "bool GetLatchedStereoFrame(")
    view = body(game, "const LatchedStereoFrame* GetLatchedStereoFrameView() noexcept")
    assert "LatchedStereo.valid && LatchedStereo.poseSequence != 0" in view
    assert "? &LatchedStereo : nullptr" in view
    assert "static " not in view and "new " not in view
    assert "LatchedStereo = {};" in body(game, "void ResetFrameState()")
    assert "++BeginSceneCalls;" in body(game, "HRESULT __stdcall BeginSceneDest(")
    assert "LatchFramePose();" in body(game, "HRESULT __stdcall BeginSceneDest(")
    for name, builder in (
        ("R33TryFastWorld", "R32ReviewBuildFastWorldConstants(device, *stereo, draw)"),
        ("R33TryHud", "R32ReviewBuildScreenSpaceEyeConstants(device, *stereo, screenKind,"),
    ):
        chunk = body(dispatch, "R32ReviewOwnedResult " + name + "(")
        assert chunk.count("GetLatchedStereoFrameView()") == 1, name
        assert "if (!stereo)" in chunk, name
        assert "framePoseSequence != stereo->poseSequence" in chunk, name
        assert "GetLatchedStereoFrame(stereo)" not in chunk, name
        assert "LatchedStereoFrame stereo{}" not in chunk, name
        assert builder in chunk, name
        if name == "R33TryFastWorld":
            assert "draw.poseSequence, *stereo)" in chunk
        # Eligibility and reset/StateBlock checks MUST precede borrowed view.
        assert chunk.index("R32ReviewStableStereoBase(device)") < chunk.index("GetLatchedStereoFrameView()")
    assert dispatch.count("GetLatchedStereoFrameView()") == 2


def destructive_checks(api: str, game: str, dispatch: str) -> None:
    cases = (
        ("permit-invalid-pose", api, game.replace(
            "LatchedStereo.valid && LatchedStereo.poseSequence != 0",
            "LatchedStereo.poseSequence != 0", 1), dispatch),
        ("permit-zero-sequence", api, game.replace(
            "LatchedStereo.valid && LatchedStereo.poseSequence != 0",
            "LatchedStereo.valid", 1), dispatch),
        ("world-snapshot-regression", api, game, dispatch.replace(
            "R32ReviewBuildFastWorldConstants(device, *stereo, draw)",
            "R32ReviewBuildFastWorldConstants(device, stereo, draw)", 1)),
        ("hud-snapshot-regression", api, game, dispatch.replace(
            "R32ReviewBuildScreenSpaceEyeConstants(device, *stereo, screenKind,",
            "R32ReviewBuildScreenSpaceEyeConstants(device, stereo, screenKind,", 1)),
        ("world-pose-fence", api, game, dispatch.replace(
            "framePoseSequence != stereo->poseSequence",
            "framePoseSequence == stereo->poseSequence", 1)),
        ("drop-hud-view", api, game, dispatch.replace(
            "const auto* stereo = OutRunVRRenderer::GetLatchedStereoFrameView();",
            "const auto* stereo = nullptr;", 1)),
        ("break-reset-invalidation", api, game.replace(
            "LatchedStereo = {};", "// removed reset", 1), dispatch),
        ("drop-world-duplication-snapshot", api, game, dispatch.replace(
            "draw.poseSequence, *stereo)", "draw.poseSequence, stereo)", 1)),
    )
    for label, a, g, d in cases:
        try:
            verify(a, g, d)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("negative mutation unexpectedly passed: " + label)


def main() -> None:
    a = API.read_text(encoding="utf-8")
    g = GAME.read_text(encoding="utf-8")
    d = DISPATCH.read_text(encoding="utf-8")
    verify(a, g, d)
    destructive_checks(a, g, d)
    print("R33 latched pose borrowed-view: PASS (8 negative mutations)")


if __name__ == "__main__":
    main()
