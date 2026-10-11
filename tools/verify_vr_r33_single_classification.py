#!/usr/bin/env python3
"""Regression guard for one R33 screen-pass classification per physical draw.

The branch choice and HUD arguments must share the same classifier result.
This checks the source contract (not hardware FPS), including negative cases.
"""
from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r33.cpp"


def check(text: str) -> None:
    hud = text.split("R32ReviewOwnedResult R33TryHud(", 1)[1].split(
        "template <typename ActualDraw, typename LowerR29Draw>", 1
    )[0]
    dispatch = text.split("HRESULT R33Dispatch(", 1)[1].split(
        "HRESULT __stdcall DrawPrimitiveDestR33(", 1
    )[0]

    # HUD must receive and use the dispatch-owned classification. No second
    # projection signature or device GetRenderState query for routing.
    assert re.search(r"R32ReviewScreenSpaceKind\s+screenKind\s*,", hud), "HUD classification parameter lost"
    assert not re.search(r"\bR32ReviewClassifyScreenSpacePass\s*\(", hud), "HUD reclassifies draw"
    assert "screenKind == R32ReviewScreenSpaceKind::None" in hud, "HUD fail-closed check lost"

    assert len(re.findall(r"\bR32ReviewClassifyScreenSpacePass\s*\(", dispatch)) == 1, (
        "R33 dispatch must classify once"
    )
    assert re.search(r"const R32ReviewScreenSpaceKind\s+screenKind\s*=\s*"
                     r"R32ReviewClassifyScreenSpacePass\(device\)", dispatch), "missing cached result"
    assert re.search(r"if\s*\(screenKind\s*!=\s*R32ReviewScreenSpaceKind::None\)", dispatch), (
        "HUD/world decision must use cached classification"
    )
    assert re.search(r"R33TryHud\(device,\s*screenKind\s*,", dispatch), (
        "HUD must receive that same classification"
    )
    assert "R33TryFastWorld(device," in dispatch, "world route removed"
    assert "R32ReviewRunLowerFailClosed(device," in dispatch, "R29 fallback removed"



def check_resync_single_flush(text: str) -> None:
    """Guarded stereo draws flush once; bypasses retain the old recovery gate."""
    guard = text.split("HRESULT R33GuardStereoRasterState(", 1)[1].split(
        "void R33InvalidateDepthStencilCache()", 1
    )[0]
    dispatch = text.split("HRESULT R33Dispatch(", 1)[1].split(
        "HRESULT __stdcall DrawPrimitiveDestR33(", 1
    )[0]
    assert guard.count("StateBlockRecovery::FlushPendingResync(device);") == 1
    assert dispatch.count("StateBlockRecovery::FlushPendingResync(device);") == 1
    assert "return drawCall(false);" in guard, "raster bypass must signal no flush"
    assert "return drawCall(true);" in guard, "active raster guard must signal flushed"
    assert guard.index("FlushPendingResync(device);") < guard.index(
        "R32ReviewRunRasterReplayGuard("), "resync must precede raster snapshot"
    assert re.search(
        r"if\s*\(!resyncAlreadyFlushed\s*&&\s*"
        r"!OutRunVR::State::StateBlockTracker::Recording\(\)\)",
        dispatch
    ), "dispatch must preserve fallback StateBlock recovery"
    assert len(re.findall(r"auto call = \[&\]\(bool resyncAlreadyFlushed\)", text)) == 4, (
        "all four primitive entrypoints must carry the guard decision"
    )
    assert len(re.findall(
        r"R33Dispatch\(device, actual, lower,\s*\"R33/[^\"]+\",\s*"
        r"resyncAlreadyFlushed\)", text
    )) == 4, "every physical draw must forward the recovery flag"



def check_mono_aux_fastpath(text: str) -> None:
    """Mono/aux draws reuse the raster decision before any R33 classification."""
    guard = text.split("HRESULT R33GuardStereoRasterState(", 1)[1].split(
        "void R33InvalidateDepthStencilCache()", 1)[0]
    dispatch = text.split("HRESULT R33Dispatch(", 1)[1].split(
        "HRESULT __stdcall DrawPrimitiveDestR33(", 1)[0]
    assert guard.index("if (!device") < guard.index("return drawCall(false);")
    for exclusion in (
        "!R32ReviewIsGameDevice(device)", "R32ReviewInternalStereoPass()",
        "StateBlockTracker::Recording()", "!R32ReviewStereoWanted()",
        "!R32ReviewTargetIsBackBuffer()",
    ):
        assert exclusion in guard, f"raster bypass lost {exclusion}"

    fallback = re.search(
        r"auto fallbackToR29 = \[&\]\(\) -> HRESULT \{(.*?)\n\s*\};",
        dispatch, re.S)
    assert fallback, "R29 shared fail-closed fallback missing"
    body = fallback.group(1)
    assert "R32ReviewDiscardUnreliableDrawCaches();" in body
    assert "if (telemetry)" in body and "R32ReviewNoteDispatchFallback();" in body
    assert "R32ReviewRunLowerFailClosed(device," in body
    assert "std::forward<LowerR29Draw>(lowerR29Draw)" in body
    bypass = "if (!resyncAlreadyFlushed)\n                return fallbackToR29();"
    assert bypass in dispatch, "mono/aux still pays for R33 classification"
    assert dispatch.index("StateBlockTracker::Recording()") < dispatch.index(bypass)
    assert dispatch.index(bypass) < dispatch.index("R32ReviewClassifyScreenSpacePass(device)")
    assert dispatch.rfind("return fallbackToR29();") > dispatch.index(
        "R33TryFastWorld(device,"), "stereo fallback must use identical R29 policy"


def mutate_dispatch(src: str, before: str, after: str) -> str:
    head, tail = src.split("HRESULT R33Dispatch(", 1)
    body, end = tail.split("HRESULT __stdcall DrawPrimitiveDestR33(", 1)
    assert before in body, f"mutation anchor missing: {before!r}"
    return (head + "HRESULT R33Dispatch(" + body.replace(before, after, 1)
            + "HRESULT __stdcall DrawPrimitiveDestR33(" + end)


def negative_mono_aux_fastpath(src: str) -> None:
    bypass = "if (!resyncAlreadyFlushed)\n                return fallbackToR29();"
    cases = [
        (bypass, "if (false)\n                return fallbackToR29();"),
        (bypass, "if (resyncAlreadyFlushed)\n                return fallbackToR29();"),
        ("return R32ReviewRunLowerFailClosed(device,",
         "return R32ReviewCallRawDrawPrimitive(device,"),
        ("R32ReviewDiscardUnreliableDrawCaches();", "/* removed */"),
        ("R32ReviewNoteDispatchFallback();", "/* removed */"),
        ("if (!resyncAlreadyFlushed)\n                return fallbackToR29();",
         "if (!resyncAlreadyFlushed)\n                return actualDraw();"),
        ("return fallbackToR29();\n        }\n\n        HRESULT" ,
         "return actualDraw();\n        }\n\n        HRESULT"),
    ]
    # Last mutation spans the dispatch function boundary: handle separately.
    for index, (before, after) in enumerate(cases, 1):
        if index == len(cases):
            assert before in src
            mutant = src.replace(before, after, 1)
        else:
            mutant = mutate_dispatch(src, before, after)
        assert mutant != src, f"mutation fixture {index} did not alter source"
        try:
            check_mono_aux_fastpath(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"mono/aux negative mutation {index} escaped")


def main() -> None:
    src = SOURCE.read_text(encoding="utf-8")
    check(src)
    check_resync_single_flush(src)
    check_mono_aux_fastpath(src)
    negative_mono_aux_fastpath(src)
    mutants = [
        src.replace("R33TryHud(device, screenKind,", "R33TryHud(device, R32ReviewScreenSpaceKind::None,", 1),
        src.replace("if (screenKind != R32ReviewScreenSpaceKind::None)",
                    "if (R32ReviewClassifyScreenSpacePass(device) != R32ReviewScreenSpaceKind::None)", 1),
        src.replace("R32ReviewScreenSpaceKind screenKind,\n            ActualDraw",
                    "R32ReviewScreenSpaceKind screenKind,\n            ActualDraw", 1).replace(
                        "if (OutRunVR::State::StateBlockTracker::Recording() || !R32ReviewStableStereoBase(device) ||",
                        "if (R32ReviewClassifyScreenSpacePass(device) == R32ReviewScreenSpaceKind::None ||"
                        " OutRunVR::State::StateBlockTracker::Recording() || !R32ReviewStableStereoBase(device) ||", 1),
    ]
    for i, mutant in enumerate(mutants, 1):
        try:
            check(mutant)
        except AssertionError:
            continue
        raise AssertionError(f"regression mutation {i} was not rejected")
    resync_mutants = [
        src.replace("return drawCall(false);", "return drawCall(true);", 1),
        src.replace("return drawCall(true);", "return drawCall(false);", 1),
        src.replace("if (!resyncAlreadyFlushed &&", "if (", 1),
        src.replace("resyncAlreadyFlushed);", "false);", 1),
    ]
    for i, mutant in enumerate(resync_mutants, 1):
        try:
            check_resync_single_flush(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"resync regression mutation {i} was not rejected")
    print("PASS R33 single classification, mono/aux R29 bypass, one active resync, 14 negative mutations")


if __name__ == "__main__":
    main()
