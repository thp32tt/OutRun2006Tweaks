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
    shadow = pos("TrackedRasterShadowValid()")
    fastreturn = body.index("return R23ClearR22Hook.stdcall<HRESULT>(", shadow)
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




def draw_body(source: str) -> str:
    start = source.index("void R23BeforeTopLevelDraw(")
    end = source.index("HRESULT __stdcall DrawPrimitiveDestR23(", start)
    return source[start:end]


def verify_draw(src: str) -> None:
    body = draw_body(src)

    def pos(token: str) -> int:
        assert token in body, f"missing R23 draw fastpath: {token}"
        return body.index(token)

    game = pos("if (!IsGameDevice(device) || InternalStereoPass)")
    serial = pos("++R23GameDrawSerial;")
    ifdef = pos("#if !defined(OUTRUN_VR_FORCE_LIVE_RASTER_COMPARE)")
    reliable = pos("if (IsTrackedStateBlockReliable() &&")
    shadow = pos("TrackedRasterShadowValid())")
    bypass = pos("return;\n#endif")
    endif = pos("#endif")
    fallback = pos('R23CaptureActualGameState(device, ignored, "Draw", false);')
    assert game < serial < ifdef < reliable < shadow < bypass < endif < fallback
    assert body.count("R23CaptureActualGameState(") == 1
    assert body.count("++R23GameDrawSerial;") == 1
    # Four draw hooks plus the public NotifyTopLevelDraw forwarding API.
    assert src.count("R23BeforeTopLevelDraw(device);") == 5
    assert "void NotifyTopLevelDraw(IDirect3DDevice9* device)" in src
    assert "OutRunVR::State::D3D9RasterSnapshot ignored{};" in body
    assert pos("R23CaptureActualGameState(") > endif


def verify_draw_mutations(src: str) -> int:
    body = draw_body(src)
    mutations = (
        ("if (!IsGameDevice(device) || InternalStereoPass)", "if (false)"),
        ("++R23GameDrawSerial;", "/* draw serial lost */"),
        ("#if !defined(OUTRUN_VR_FORCE_LIVE_RASTER_COMPARE)", "#if 1"),
        ("if (IsTrackedStateBlockReliable() &&", "if (true &&"),
        ("TrackedRasterShadowValid())", "true)"),
        ("return;\n#endif", "/* no fast exit */\n#endif"),
        ('R23CaptureActualGameState(device, ignored, "Draw", false);',
         "/* no unsafe fallback capture */"),
    )
    for good, bad in mutations:
        assert good in body, f"missing R23 draw mutation anchor: {good}"
        mutant = src.replace(body, body.replace(good, bad, 1), 1)
        try:
            verify_draw(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"R23 draw destructive mutation survived: {good}")
    return len(mutations)

if __name__ == "__main__":
    src = SOURCE.read_text(encoding="utf-8")
    verify(src)
    verify_draw(src)
    mutations = (
        ("R9StereoSeeded &&", "true &&"),
        ("OutRunVR::RuntimeEligibility::MayInjectStereo();", "true;"),
        ("#if !defined(OUTRUN_VR_FORCE_LIVE_RASTER_COMPARE)", "#if 1"),
        ("IsTrackedStateBlockReliable() &&", "true &&"),
        ("TrackedRasterShadowValid()", "true"),
        ("if (seededStereo)\n", "if (true)\n"),
        ('const bool stateOk = R23CaptureActualGameState(\n                device, actual, "Clear", true);',
         "const bool stateOk = true;"),
        ("if (FAILED(hr) || !stateOk || !mainBefore || !wantsStereo)",
         "if (FAILED(hr) || !mainBefore || !wantsStereo)"),
    )
    for good, bad in mutations:
        assert good in clear_body(src), f"missing mutation anchor {good!r}"
        clear = clear_body(src)
        mutant = src.replace(clear, clear.replace(good, bad, 1), 1)
        try:
            verify(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"seeded-clear destructive mutation survived: {good}")
    draw_mutations = verify_draw_mutations(src)
    print(f"PASS R23 seeded-clear + tracked draw raster fastpaths, {len(mutations)} clear and {draw_mutations} draw destructive mutations")
