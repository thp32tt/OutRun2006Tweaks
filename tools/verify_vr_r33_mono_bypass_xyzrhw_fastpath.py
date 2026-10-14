#!/usr/bin/env python3
"""R33 mono/aux draw bypass: never probe R30 XYZRHW outside the stereo raster guard."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R33 = ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp"
R29 = ROOT / "src/vr/d3d9/stereo_renderer_r29.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"

DRAW_NAMES = (
    ("DrawPrimitiveDestR33(", "PrimitiveVB", "DrawPrimitive"),
    ("DrawIndexedPrimitiveDestR33(", "IndexedPrimitiveVB", "DrawIndexedPrimitive"),
    ("DrawPrimitiveUPDestR33(", "PrimitiveUP", "DrawPrimitiveUP"),
    ("DrawIndexedPrimitiveUPDestR33(", "IndexedPrimitiveUP", "DrawIndexedPrimitiveUP"),
)


def body(source, signature):
    at = source.index(signature)
    start = source.index("{", at)
    level = 0
    for at in range(start, len(source)):
        if source[at] == "{":
            level += 1
        elif source[at] == "}":
            level -= 1
            if level == 0:
                return source[start:at + 1]
    raise AssertionError("unclosed " + signature)


def check(r33, r29):
    try:
        guard = body(r33, "HRESULT R33GuardStereoRasterState(")
        stable = body(r29, "bool R29StableStereoBase(")
        assert "const bool gameDevice = device && R32ReviewIsGameDevice(device);" in guard
        assert "const bool internalPass = gameDevice && R32ReviewInternalStereoPass();" in guard
        assert "(gameDevice && !internalPass)" in guard
        assert "if (!gameDevice || internalPass ||" in guard
        assert "StateBlockTracker::Recording()" in guard
        assert "!R32ReviewStereoWanted() || !R32ReviewTargetIsBackBuffer()" in guard
        assert "return drawCall(false);" in guard
        assert "return drawCall(true);" in guard
        # The lower R29 gate must reject every reason the outer guard bypasses.
        for required in ("!IsGameDevice(device)", "InternalStereoPass",
                         "!TargetIsBackBuffer()", "!StereoWanted()"):
            assert required in stable
        for func, path, raw in DRAW_NAMES:
            draw = body(r33, "HRESULT __stdcall " + func)
            probe = "R32ReviewTryXyzrhw" + path + "("
            assert draw.count(probe) == 1
            assert "auto call = [&](bool resyncAlreadyFlushed)" in draw
            assert "const bool tryXyzrhw = resyncAlreadyFlushed &&" in draw
            assert "(!OutRunVR::State::StateBlockTracker::Reliable() ||" in draw
            assert "R32ReviewCurrentVertexShaderIdentity() == 0);" in draw
            assert "const HRESULT xyzrhw = tryXyzrhw\n                    ? " + probe in draw
            assert ": E_NOTIMPL;" in draw
            assert "if (xyzrhw != E_NOTIMPL)\n                    return xyzrhw;" in draw
            assert "R32ReviewCallRaw" + raw + "(" in draw
            assert "R32ReviewCallLower" + raw + "(" in draw
            assert "R33GuardStereoRasterState(" in draw
            assert "R33Dispatch(" in draw
        return True
    except (AssertionError, ValueError):
        return False


def main():
    r33 = R33.read_text(encoding="utf-8")
    r29 = R29.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("tools/verify_vr_r33_mono_bypass_xyzrhw_fastpath.py") == 2
    assert check(r33, r29), "R33 stereo eligibility / mono bypass contract"
    cases = []
    for _, path, _ in DRAW_NAMES:
        probe = "R32ReviewTryXyzrhw" + path + "("
        cases += [
            r33.replace(
                "const bool tryXyzrhw = resyncAlreadyFlushed &&",
                "const bool tryXyzrhw = true &&", 1),
            r33.replace(
                "R32ReviewCurrentVertexShaderIdentity() == 0);",
                "true);", 1),
            r33.replace(
                "StateBlockTracker::Reliable() ||",
                "StateBlockTracker::Reliable() &&", 1),
            r33.replace(": E_NOTIMPL;", ": D3D_OK;", 1),
        ]
    cases += [
        r33.replace("if (!gameDevice || internalPass ||",
                    "if (false || false ||", 1),
        r33.replace("return drawCall(false);", "return drawCall(true);", 1),
        r33.replace("return drawCall(true);", "return drawCall(false);", 1),
        r29.replace("!TargetIsBackBuffer()", "false", 1),
    ]
    for i, candidate in enumerate(cases):
        assert candidate != r33 and candidate != r29, ("unchanged mutation", i)
        assert not check(candidate, r29) if i < len(cases)-1 else not check(r33, candidate), (
            "mutation passed", i)
    print(f"PASS R33 guarded XYZRHW mono/aux bypass and raw/R29 fallback; {len(cases)} destructive checks")


if __name__ == "__main__":
    main()
