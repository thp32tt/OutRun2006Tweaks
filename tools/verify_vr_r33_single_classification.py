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



def main() -> None:
    src = SOURCE.read_text(encoding="utf-8")
    check(src)
    check_resync_single_flush(src)
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
    print("PASS R33 single classification + one active resync, bypass recovery, 7 negative mutations")


if __name__ == "__main__":
    main()
