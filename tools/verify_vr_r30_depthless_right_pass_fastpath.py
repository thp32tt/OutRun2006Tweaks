#!/usr/bin/env python3
"""R30 state-elision safety on both XYZRHW and flat-FOV stereo routes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
R33 = ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp"
WF = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def block(src, signature):
    start = src.index("{", src.index(signature))
    depth = 0
    for i in range(start, len(src)):
        depth += (src[i] == "{") - (src[i] == "}")
        if depth == 0:
            return src[start:i + 1]
    raise AssertionError(signature)


def check(src, r33):
    restore = block(src, "inline bool R30RestoreDepthlessRightPassState(")
    assert "SetDepthStencilSurface" not in restore
    for token in ("R29OwnerCallOriginalSetRenderTarget(",
                  "device->SetViewport(&savedViewport)",
                  "if (restoreWvp &&",
                  "R29OwnerSetWvpOneRegisterAtATime(device, originalConstants)",
                  "return ok;"):
        assert token in restore, ("restore", token)
    assert (restore.index("R29OwnerCallOriginalSetRenderTarget(")
            < restore.index("device->SetViewport(&savedViewport)")
            < restore.index("R29OwnerSetWvpOneRegisterAtATime("))
    for method, vp, wvp, enabled in (
        ("HRESULT R30ExecuteXyzrhwStereo(", "state.viewport", "nullptr", "false"),
        ("HRESULT R30TryScreenSpaceFovDraw(", "savedViewport", "original", "true"),
    ):
        b = block(src, method)
        assert ("const bool depthlessPass = savedDepth == nullptr &&\n"
                "                OutRunVR::State::StateBlockTracker::Reliable();") in b
        for token in ("IDirect3DSurface9* savedDepth = frame.trackedDepthStencil;",
                      "if (SUCCEEDED(rightHr) && !depthlessPass)",
                      "savedDepth ? frame.rightEyeDepth : nullptr",
                      "restoreOk = depthlessPass",
                      "R30RestoreDepthlessRightPassState(",
                      "R29OwnerRestoreRightPassState(",
                      "R29OwnerArmMonoSafety();", "if (!restoreOk)",
                      "return leftHr;"):
            assert token in b, (method, token)
        assert ("device, savedRt, " + vp + ", " + wvp + ", " + enabled) in b
        assert ("device, savedRt, savedDepth, " + vp + ", " + wvp + ", " + enabled) in b
        assert (b.index("R29OwnerCallOriginalSetRenderTarget(") <
                b.index("if (SUCCEEDED(rightHr) && !depthlessPass)") <
                b.index("rightHr = device->SetViewport(") <
                b.index("R30RestoreDepthlessRightPassState("))
    assert "const bool depthlessPass = savedDepth == nullptr &&" in r33
    for depth_is_null, reliable, bypass in (
        (True, True, True), (True, False, False),
        (False, True, False), (False, False, False)
    ):
        assert (depth_is_null and reliable) == bypass


def main():
    src = SRC.read_text(encoding="utf-8")
    r33 = R33.read_text(encoding="utf-8")
    assert WF.read_text(encoding="utf-8").count(
        "tools/verify_vr_r30_depthless_right_pass_fastpath.py") == 2
    check(src, r33)
    mutations = [
        ("savedDepth == nullptr &&", "savedDepth == nullptr ||"),
        ("StateBlockTracker::Reliable();", "true;"),
        ("if (SUCCEEDED(rightHr) && !depthlessPass)", "if (SUCCEEDED(rightHr))"),
        ("restoreOk = depthlessPass", "restoreOk = false"),
        ("R30RestoreDepthlessRightPassState(", "R30RestoreWrongState("),
        ("R29OwnerRestoreRightPassState(", "R29OwnerOmitFallback("),
        ("R29OwnerCallOriginalSetRenderTarget(", "R29OwnerNoRtRestore("),
        ("if (restoreWvp &&", "if (false &&"),
        ("if (!restoreOk)", "if (false)"),
        ("savedDepth ? frame.rightEyeDepth : nullptr", "frame.rightEyeDepth"),
    ]
    for n, (old, new) in enumerate(mutations, 1):
        assert old in src, (n, old)
        try:
            check(src.replace(old, new, 1), r33)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"unsafe mutation survived: {n}")
    print(f"PASS R30 XYZRHW/FOV depthless state restore + {len(mutations)} mutations")


if __name__ == "__main__":
    main()
