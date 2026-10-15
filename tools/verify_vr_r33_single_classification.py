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



def check_readiness_hotpath(src: str) -> None:
    """One ready-frame sync snapshot per route; resample after bootstrap."""
    helper = src.split("bool R33PrepareRightDepthStereo(", 1)[1].split(
        "void R33InvalidateRightForLeftWrite(", 1)[0]
    assert helper.count("R32ReviewTrackedDepthStencil()") == 2
    assert helper.count("R32ReviewRightDepthInSync()") == 2
    assert helper.count("R32ReviewRightStencilInSync()") == 2
    assert "if (!depthInSync || !stencilInSync)" in helper
    assert helper.index("R32ReviewTryBootstrapRightDepth(device);") < helper.rindex(
        "if (!R32ReviewTrackedDepthStencil())")
    assert helper.rindex("depthInSync = R32ReviewRightDepthInSync();") > helper.index(
        "R32ReviewTryBootstrapRightDepth(device);")
    assert helper.rindex("stencilInSync = R32ReviewRightStencilInSync();") > helper.index(
        "R32ReviewTryBootstrapRightDepth(device);")
    assert "if (!depthInSync && R32ReviewDepthTestActive(device))" in helper
    assert "if (!stencilInSync && R32ReviewStencilTestActive(device))" in helper
    for start, end in (("R32ReviewOwnedResult R33TryFastWorld(", "R32ReviewOwnedResult R33TryHud("),
                       ("R32ReviewOwnedResult R33TryHud(", "HRESULT R33Dispatch(")):
        route = src.split(start, 1)[1].split(end, 1)[0]
        assert route.count("R33PrepareRightDepthStereo(device)") == 1
        borrowed = "GetLatchedStereoFrameView()" in route
        read = ("GetLatchedStereoFrameView()" if borrowed
                else "GetLatchedStereoFrame(stereo)")
        assert route.index("R32ReviewEnsureStereoResources(device)") < route.index(
            "R33PrepareRightDepthStereo(device)") < route.index(read)
        assert "if (!R33PrepareRightDepthStereo(device))\n                return {};" in route
        assert "R32ReviewRightDepthInSync()" not in route
        assert "R32ReviewRightStencilInSync()" not in route
        assert route.count("R32ReviewFrameStereoPoseSequence()") == 1
        assert ("framePoseSequence != stereo->poseSequence" if borrowed
                else "framePoseSequence != stereo.poseSequence") in route
        if borrowed:
            assert "if (!stereo)" in route


def negative_readiness_hotpath(src: str) -> None:
    changes = (
        ("if (!R32ReviewTrackedDepthStencil())\n                return true;",
         "if (false)\n                return true;"),
        ("if (!depthInSync || !stencilInSync)", "if (!depthInSync && !stencilInSync)"),
        ("R32ReviewTryBootstrapRightDepth(device);", "/* removed */"),
        ("if (!R32ReviewTrackedDepthStencil())\n                    return true;",
         "if (false)\n                    return true;"),
        ("depthInSync = R32ReviewRightDepthInSync();", "depthInSync = true;"),
        ("stencilInSync = R32ReviewRightStencilInSync();", "stencilInSync = true;"),
        ("if (!depthInSync && R32ReviewDepthTestActive(device))",
         "if (!depthInSync && false)"),
        ("if (!stencilInSync && R32ReviewStencilTestActive(device))",
         "if (!stencilInSync && false)"),
        ("if (!R33PrepareRightDepthStereo(device))", "if (false)"),
        ("R32ReviewFrameStereoPoseSequence();", "0;"),
    )
    # The source can contain unrelated guards with the same text before
    # R33PrepareRightDepthStereo. Mutate the producer itself, otherwise a
    # negative test silently edits the wrong function and reports a false FAIL.
    begin = src.index("bool R33PrepareRightDepthStereo(")
    end = src.index("void R33InvalidateRightForLeftWrite(", begin)
    for i, (before, after) in enumerate(changes, 1):
        if i <= 8:
            helper = src[begin:end]
            # Tests 5/6 specifically damage post-bootstrap resampling, not
            # the first readiness declarations (which share an assignment).
            if i in (5, 6):
                start = helper.index("R32ReviewTryBootstrapRightDepth(device);")
                prefix, suffix = helper[:start], helper[start:]
                assert before in suffix, ("post-bootstrap mutation anchor absent", i)
                mutated_helper = prefix + suffix.replace(before, after, 1)
            else:
                assert before in helper, ("helper mutation anchor absent", i)
                mutated_helper = helper.replace(before, after, 1)
            mutant = src[:begin] + mutated_helper + src[end:]
        else:
            # Route-level mutations: one caller or one pose snapshot must
            # fail the all-routes invariant even if the other path is intact.
            assert before in src[end:], ("route mutation anchor absent", i)
            mutant = src[:end] + src[end:].replace(before, after, 1)
        assert mutant != src, ("mutation did not change source", i)
        try:
            check_readiness_hotpath(mutant)
        except (AssertionError, ValueError, IndexError):
            continue
        raise AssertionError(f"readiness negative mutation {i} survived")


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
        r"resyncAlreadyFlushed,\s*telemetry\)", text
    )) == 4, "every physical draw must forward the recovery flag"



def check_mono_aux_fastpath(text: str) -> None:
    """Mono/aux draws reuse the raster decision before any R33 classification."""
    guard = text.split("HRESULT R33GuardStereoRasterState(", 1)[1].split(
        "void R33InvalidateDepthStencilCache()", 1)[0]
    dispatch = text.split("HRESULT R33Dispatch(", 1)[1].split(
        "HRESULT __stdcall DrawPrimitiveDestR33(", 1)[0]
    # R33 computes game-device and internal-pass eligibility only once.
    # Keep source-level evidence for their equivalence and the fail-closed
    # bypass, instead of requiring an obsolete duplicate device check.
    for required in (
        "const bool gameDevice = device && R32ReviewIsGameDevice(device);",
        "const bool internalPass = gameDevice && R32ReviewInternalStereoPass();",
        "(gameDevice && !internalPass)",
        "if (!gameDevice || internalPass ||",
        "StateBlockTracker::Recording()", "!R32ReviewStereoWanted()",
        "!R32ReviewTargetIsBackBuffer()",
    ):
        assert required in guard, f"raster bypass lost {required}"
    assert guard.index("if (!gameDevice || internalPass ||") < guard.index(
        "return drawCall(false);")

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
        ("R32ReviewDiscardUnreliableDrawCaches();\n"
         "                if (telemetry)\n"
         "                    R32ReviewNoteDispatchFallback();",
         "R32ReviewDiscardUnreliableDrawCaches();\n"
         "                if (telemetry)\n"
         "                    /* removed */"),
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



def check_write_flags_cached(src: str) -> None:
    """Depth/stencil work is calculated on snapshot and setter, not each draw."""
    state = src.split("struct R33DepthStencilWriteState", 1)[1].split("};", 1)[0]
    helper = src.split("void R33RefreshWriteFlags(", 1)[1].split(
        "bool R33ReadDepthStencilWriteState(", 1)[0]
    read = src.split("bool R33ReadDepthStencilWriteState(", 1)[1].split(
        "bool R33DepthStencilCacheCurrent()", 1)[0]
    getter = src.split("bool R33GetWriteFlags(", 1)[1].split(
        "void R33InvalidateRightForLeftWrite(", 1)[0]
    setter = src.split("HRESULT __stdcall SetRenderStateDestR33(", 1)[1].split(
        "template <typename ActualDraw>", 1)[0]
    assert "bool mayWriteDepth = false;" in state
    assert "bool stencilWritesIfPresent = false;" in state
    for required in (
        "s.mayWriteDepth = s.zEnable != D3DZB_FALSE &&",
        "s.zWrite != FALSE;",
        "s.stencilFail != D3DSTENCILOP_KEEP ||",
        "s.stencilZFail != D3DSTENCILOP_KEEP ||",
        "s.stencilPass != D3DSTENCILOP_KEEP;",
        "s.twoSided != FALSE &&",
        "s.ccwStencilFail != D3DSTENCILOP_KEEP ||",
        "s.ccwStencilZFail != D3DSTENCILOP_KEEP ||",
        "s.ccwStencilPass != D3DSTENCILOP_KEEP);",
        "s.stencilWritesIfPresent = s.stencilEnable != FALSE &&",
        "s.stencilWriteMask != 0 && (frontWrites || backWrites);",
    ):
        assert required in helper, f"cached write-flag computation changed: {required}"
    assert read.count("R33RefreshWriteFlags(next);") == 2, (
        "read must refresh both no-depth and populated snapshots")
    assert "R33RefreshWriteFlags(R33DepthStencilState);" in setter, (
        "tracked render-state setters must recompute write flags")
    for kind in ("D3DRS_ZENABLE", "D3DRS_ZWRITEENABLE",
                 "D3DRS_STENCILENABLE", "D3DRS_STENCILWRITEMASK",
                 "D3DRS_STENCILFAIL", "D3DRS_STENCILZFAIL",
                 "D3DRS_STENCILPASS", "D3DRS_TWOSIDEDSTENCILMODE",
                 "D3DRS_CCW_STENCILFAIL", "D3DRS_CCW_STENCILZFAIL",
                 "D3DRS_CCW_STENCILPASS"):
        assert "case " + kind + ":" in setter, f"setter lost {kind}"
    assert "mayWriteDepth = s.mayWriteDepth;" in getter
    assert ("mayWriteStencil = s.stencilWritesIfPresent &&\n"
            "                R32ReviewMainDepthHasStencil();") in getter, (
                "short-circuited live format gate is mandatory")
    assert "if (!R32ReviewTrackedDepthStencil())\n                return true;" in getter
    assert "if (!OutRunVR::State::StateBlockTracker::Reliable())" in getter
    assert "if (!R33DepthStencilCacheCurrent())" in getter
    assert "if (!R33ReadDepthStencilWriteState(device))" in getter

def negative_write_flag_cache(src: str) -> None:
    alterations = [
        ("s.stencilFail != D3DSTENCILOP_KEEP ||",
         "s.stencilFail == D3DSTENCILOP_KEEP ||"),
        ("s.stencilZFail != D3DSTENCILOP_KEEP ||",
         "s.stencilZFail == D3DSTENCILOP_KEEP ||"),
        ("s.stencilPass != D3DSTENCILOP_KEEP;",
         "s.stencilPass == D3DSTENCILOP_KEEP;"),
        ("s.twoSided != FALSE &&", "s.twoSided == FALSE &&"),
        ("s.ccwStencilPass != D3DSTENCILOP_KEEP);",
         "s.ccwStencilPass == D3DSTENCILOP_KEEP);"),
        ("s.stencilWriteMask != 0 && (frontWrites || backWrites);",
         "s.stencilWriteMask == 0 && (frontWrites || backWrites);"),
        ("s.zWrite != FALSE;", "s.zWrite == FALSE;"),
        ("R33RefreshWriteFlags(R33DepthStencilState);",
         "/* tracked setter cache refresh removed */"),
        ("mayWriteStencil = s.stencilWritesIfPresent &&",
         "mayWriteStencil = s.stencilWritesIfPresent ||"),
        ("R32ReviewMainDepthHasStencil();\n            return true;",
         "true;\n            return true;"),
    ]
    for i, (before, after) in enumerate(alterations, 1):
        assert before in src, f"write-flag mutation anchor {i} missing"
        mutant = src.replace(before, after, 1)
        assert mutant != src
        try:
            check_write_flags_cached(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"R33 cached-write negative mutation {i} escaped")


def check_gpu_profiler_disabled_fastpath(src: str) -> None:
    """GPU timestamp opt-out must not enter the Meter singleton on any draw."""
    before = ("const bool gpuTimed = GpuWaterProbe::Enabled() &&\n"
              "                GpuWaterProbe::instance().beforeDraw(device, primitiveCount);")
    after = ("if (gpuTimed)\n"
             "                GpuWaterProbe::instance().afterDraw(true);")
    for name in ("DrawPrimitiveDestR33", "DrawIndexedPrimitiveDestR33",
                 "DrawPrimitiveUPDestR33", "DrawIndexedPrimitiveUPDestR33"):
        body = src.split("HRESULT __stdcall " + name + "(", 1)[1].split(
            "HRESULT __stdcall ", 1)[0]
        assert body.count(before) == 1, name + ": disabled Meter still entered"
        assert body.count(after) == 1, name + ": sparse sample completion lost"
        assert body.index(before) < body.index("R33GuardStereoRasterState(")
        assert body.index(after) > body.index("R33GuardStereoRasterState(")
        assert "GpuWaterProbe::instance().afterDraw(gpuTimed)" not in body
    present = src.split("HRESULT __stdcall PresentDestR33(", 1)[1]
    assert ("if (device && R32ReviewIsGameDevice(device) && "
            "GpuWaterProbe::Enabled())\n"
            "                GpuWaterProbe::instance().beforePresent(device);") in present
    assert ("if (GpuWaterProbe::Enabled())\n"
            "                    GpuWaterProbe::instance().afterPresent(device);") in present
    assert "R33LogPerfWindow();" in present, "normal R33 telemetry lost"
    assert "GpuWaterProbe::instance().reset();" in present, "lost-device reset lost"


def negative_gpu_profiler_fastpath(src: str) -> None:
    mutations = (
        ("GpuWaterProbe::Enabled() &&\n", "true &&\n"),
        ("GpuWaterProbe::Enabled() &&\n", "GpuWaterProbe::Enabled() ||\n"),
        ("if (gpuTimed)\n", "if (true)\n"),
        ("GpuWaterProbe::instance().afterDraw(true);",
         "GpuWaterProbe::instance().afterDraw(gpuTimed);"),
        ("if (GpuWaterProbe::Enabled())\n"
         "                    GpuWaterProbe::instance().afterPresent(device);",
         "GpuWaterProbe::instance().afterPresent(device);"),
        ("R32ReviewIsGameDevice(device) && GpuWaterProbe::Enabled())",
         "R32ReviewIsGameDevice(device))"),
    )
    for i, (before, after) in enumerate(mutations, 1):
        assert before in src, f"GPU profiler negative fixture {i} missing"
        mutant = src.replace(before, after, 1)
        try:
            check_gpu_profiler_disabled_fastpath(mutant)
        except (AssertionError, IndexError, ValueError):
            continue
        raise AssertionError(f"GPU profiler negative mutation {i} survived")


def main() -> None:
    src = SOURCE.read_text(encoding="utf-8")
    check(src)
    check_resync_single_flush(src)
    check_mono_aux_fastpath(src)
    check_write_flags_cached(src)
    check_readiness_hotpath(src)
    negative_readiness_hotpath(src)
    check_gpu_profiler_disabled_fastpath(src)
    negative_gpu_profiler_fastpath(src)
    negative_mono_aux_fastpath(src)
    negative_write_flag_cache(src)
    for i, mutant in enumerate((
        src.replace("device && R32ReviewIsGameDevice(device)",
                    "device != nullptr", 1),
        src.replace("gameDevice && R32ReviewInternalStereoPass()",
                    "false", 1),
        src.replace("if (!gameDevice || internalPass ||",
                    "if (false || false ||", 1),
    ), 1):
        assert mutant != src, f"cached guard mutation {i} not applied"
        try:
            check_mono_aux_fastpath(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"cached guard negative mutation {i} escaped")
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
        src.replace("resyncAlreadyFlushed, telemetry);", "false, telemetry);", 1),
    ]
    for i, mutant in enumerate(resync_mutants, 1):
        assert mutant != src, f"resync mutation {i} did not change source"
        try:
            check_resync_single_flush(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"resync regression mutation {i} was not rejected")
    print("PASS R33 classification/resync plus cached depth-stencil write flags (30 negative mutations)")


if __name__ == "__main__":
    main()