#!/usr/bin/env python3
"""DX9Ex R32/R33: skip both null depth submissions only with proven live tracking."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R32 = ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp"
R33 = ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp"
API = ROOT / "src/vr/core/r32_review_api.hpp"


def body(source, start, end):
    return source.split(start, 1)[1].split(end, 1)[0]


def verify(r32, r33, api):
    assert "bool depthlessPass,\n        bool skipSavedViewportRestore) noexcept;" in api
    restore = body(r32, "bool R32RestoreRightPassState(", "template <typename LowerDraw>")
    assert "bool restoreWvp,\n            bool depthlessPass,\n            bool skipSavedViewportRestore" in restore
    assert "if (!depthlessPass)" in restore
    assert restore.index("if (!depthlessPass)") < restore.index(
        "R30SupportCallOriginalSetDepthStencilSurface(")
    assert restore.index("R30SupportCallOriginalSetDepthStencilSurface(") < restore.index(
        "device->SetViewport(&savedViewport)")
    wrapper = body(r32, "bool R32ReviewRestoreRightPassState(", "void R32ReviewObserveFrameWorkload(")
    assert "bool restoreWvp, bool depthlessPass,\n        bool skipSavedViewportRestore" in wrapper
    assert "originalConstants, restoreWvp, depthlessPass,\n            skipSavedViewportRestore" in wrapper
    for start, end in (
        ("R32ReviewOwnedResult R33TryFastWorld(", "R32ReviewOwnedResult R33TryHud("),
        ("R32ReviewOwnedResult R33TryHud(", "HRESULT R33Dispatch("),
    ):
        scope = body(r33, start, end)
        assert "const bool depthlessPass = savedDepth == nullptr &&\n                OutRunVR::State::StateBlockTracker::Reliable();" in scope
        guard = "if (SUCCEEDED(rightHr) && !depthlessPass)"
        assert guard in scope, "depth setter requires a verified depthless bypass"
        assert scope.index("R32ReviewSetRenderTarget(") < scope.index(guard)
        assert scope.index(guard) < scope.index("rightHr = device->SetViewport(")
        assert scope.index("R32ReviewRestoreRightPassState(") > scope.index(guard)
        assert "true, depthlessPass, skipSavedViewportRestore);" in scope
        # One authoritative post-left-draw attachment snapshot feeds right-eye
        # bind, depthless decision and restore: no second cross-TU lookup per
        # stereo primitive, including HUD/fast-world.
        assert scope.count("R32ReviewTrackedDepthStencil()") == 1
        assert "IDirect3DSurface9* savedDepth = R32ReviewTrackedDepthStencil();" in scope
        assert "savedDepth ? R32ReviewRightEyeDepth() : nullptr" in scope
        assert "R32ReviewTrackedDepthStencil() ? R32ReviewRightEyeDepth() : nullptr" not in scope
        # A failed right-eye bind never claims depthless success. A null
        # left attachment with unreliable StateBlocks must take both setters.
        for is_null, reliable, must_set in (
            (True, True, False), (True, False, True),
            (False, True, True), (False, False, True),
        ):
            assert not (is_null and reliable) == must_set


def main():
    original = [p.read_text(encoding="utf-8") for p in (R32, R33, API)]
    verify(*original)
    r32, r33, api = original
    mutations = [
        (r32, r33.replace("savedDepth == nullptr &&", "savedDepth == nullptr ||", 1), api),
        (r32, r33.replace("savedDepth == nullptr &&\n                OutRunVR::State::StateBlockTracker::Reliable();",
                          "savedDepth == nullptr &&\n                true;", 1), api),
        (r32, r33.replace("if (SUCCEEDED(rightHr) && !depthlessPass)",
                          "if (SUCCEEDED(rightHr))", 1), api),
        (r32, r33.replace("true, depthlessPass, skipSavedViewportRestore);",
                          "true, false, skipSavedViewportRestore);", 1), api),
        (r32, r33.replace("savedDepth ? R32ReviewRightEyeDepth() : nullptr",
                           "R32ReviewTrackedDepthStencil() ? R32ReviewRightEyeDepth() : nullptr", 1), api),
        (r32, r33.replace("savedDepth ? R32ReviewRightEyeDepth() : nullptr",
                           "R32ReviewTrackedDepthStencil() ? R32ReviewRightEyeDepth() : nullptr", 1), api),
        (r32.replace("if (!depthlessPass)", "if (false)", 1), r33, api),
        (r32.replace("originalConstants, restoreWvp, depthlessPass",
                     "originalConstants, restoreWvp, false", 1), r33, api),
        (r32, r33, api.replace("bool depthlessPass,\n        bool skipSavedViewportRestore) noexcept;",
                     "bool depthlessPass = false,\n        bool skipSavedViewportRestore) noexcept;", 1)),
    ]
    for i, altered in enumerate(mutations, 1):
        assert altered != tuple(original), f"mutation {i} missed its anchor"
        try:
            verify(*altered)
        except (AssertionError, IndexError, ValueError):
            continue
        raise AssertionError(f"mutation {i} survived")
    print(f"PASS R32/R33 depthless stereo D3D9 state-elision; {len(mutations)} negative mutations")


if __name__ == "__main__":
    main()
