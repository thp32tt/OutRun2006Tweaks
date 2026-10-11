#!/usr/bin/env python3
"""R23 already-seeded clear optimization, protected by negative source mutations.

This regression guard does not assert real HMD performance or runtime PASS.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r23.cpp"


def clear_body(source: str) -> str:
    start = source.index("HRESULT __stdcall ClearDestR23(")
    end = source.index("void R23BeforeTopLevelDraw(", start)
    return source[start:end]


def verify(src: str) -> None:
    body = clear_body(src)
    def pos(token: str) -> int:
        assert token in body, f"missing seeded-clear contract: {token}"
        return body.index(token)

    bypass = pos("#if !defined(OUTRUN_VR_FORCE_LIVE_RASTER_COMPARE)")
    guard = pos("if (seededStereo &&")
    stateblock = pos("IsTrackedStateBlockReliable() &&")
    shadow = pos("GetTrackedRasterShadow().Valid()")
    fastreturn = pos("return R23ClearR22Hook.stdcall<HRESULT>(")
    endif = pos("#endif")
    capture = pos("const bool stateOk = R23CaptureActualGameState(")
    fallback = pos("if (seededStereo)\n")
    rawclear = pos("const HRESULT hr = ClearHook.stdcall<HRESULT>(")
    assert pos("if (!IsGameDevice(device) || InternalStereoPass)") < bypass
    assert pos("R9StereoSeeded &&") < bypass
    assert pos("OutRunVR::RuntimeEligibility::MayInjectStereo();") < bypass
    assert bypass < guard < stateblock < shadow < fastreturn < endif < capture < fallback < rawclear
    assert body.count("R23ClearR22Hook.stdcall<HRESULT>(") == 3
    assert body.count("R23CaptureActualGameState(") == 1
    assert 'const bool stateOk = R23CaptureActualGameState(\n                device, actual, "Clear", true);' in body
    assert pos("if (FAILED(hr) || !stateOk || !mainBefore || !wantsStereo)") > rawclear
    assert pos("R23InitializeStereoFromAuthoritativeBaseline(") > rawclear


if __name__ == "__main__":
    src = SOURCE.read_text(encoding="utf-8")
    verify(src)
    mutations = (
        ("R9StereoSeeded &&", "true &&"),
        ("OutRunVR::RuntimeEligibility::MayInjectStereo();", "true;"),
        ("#if !defined(OUTRUN_VR_FORCE_LIVE_RASTER_COMPARE)", "#if 1"),
        ("IsTrackedStateBlockReliable() &&", "true &&"),
        ("GetTrackedRasterShadow().Valid()", "true"),
        ("if (seededStereo)\n", "if (true)\n"),
        ('const bool stateOk = R23CaptureActualGameState(\n                device, actual, "Clear", true);',
         "const bool stateOk = true;"),
        ("if (FAILED(hr) || !stateOk || !mainBefore || !wantsStereo)",
         "if (FAILED(hr) || !mainBefore || !wantsStereo)"),
    )
    for good, bad in mutations:
        assert good in clear_body(src), f"missing mutation anchor {good!r}"
        mutant = src.replace(good, bad, 1)
        try:
            verify(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"seeded-clear destructive mutation survived: {good}")
    print(f"PASS R23 seeded-clear raster fastpath/fallback and {len(mutations)} negative mutations")
