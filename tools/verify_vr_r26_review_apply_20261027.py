#!/usr/bin/env python3
"""R26+HUD exact source guards for DX9Ex reviews 01511, 01513, 01515, 01516, 01519 and 01521.

Static regression and destructive mutations only: not a Quest3/GPU test.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R30_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
R7_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r7.inc"
R9_PATH = ROOT / "src/vr/d3d9/stereo_renderer.cpp"


def function_block(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for pos in range(opening, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if depth == 0:
            return source[start:pos + 1]
    raise AssertionError("unbalanced function: " + signature)


def verify_r30(source: str) -> None:
    fn = function_block(source, "HRESULT R30TryScreenSpaceFovDraw(")
    wvp_attempt = fn.index("bool leftWvpOk = false;")
    failed_upload = fn.index("if (!leftWvpOk)")
    clean_fallback = fn.index("return E_NOTIMPL;", failed_upload)
    backup_gap = fn.index("R9NoteStereoDrawWithoutMonoBackup();")
    depth_serial = fn.index("R9NoteMainDepthContentWrite();")
    physical_draw = fn.index("const HRESULT leftHr = actualDraw();")
    assert wvp_attempt < failed_upload < clean_fallback < backup_gap < physical_draw
    assert backup_gap < depth_serial < physical_draw
    assert fn.count("R9NoteStereoDrawWithoutMonoBackup();") == 1
    assert "R9UndoStereoDrawCount();" not in fn
    upload_guard = fn[failed_upload:backup_gap]
    assert "if (!restored)" in upload_guard
    assert "R9Poison(OutRunVR::StereoFailureRestoreFailed," in upload_guard
    assert "return E_FAIL;" in upload_guard
    assert "return E_NOTIMPL;" in upload_guard


def verify_r7(source: str) -> None:
    fn = function_block(source, "HRESULT ExecuteStereoDraw(")
    start = fn.index("if(!PrepareDuplicatedDraw(device,draw))")
    single = fn[start:fn.index("D3DVIEWPORT9 savedViewport{}", start)]
    assert "if(StereoWanted()&&TargetIsBackBuffer())" in single
    assert "InvalidateRightDepthStencilIfLeftMayWrite(device);" in single
    assert single.count("const HRESULT hr=drawCall();") == 1
    assert single.count("return hr;") == 1
    assert "R7TraceVisualEyes(visualTrace,\"PREPARE_REJECT_SINGLE\"" in single
    assert single.index("InvalidateRightDepthStencilIfLeftMayWrite(device);") < single.index(
        "const HRESULT hr=drawCall();") < single.index(
        "R7TraceVisualEyes(visualTrace,\"PREPARE_REJECT_SINGLE\"") < single.index(
        "return hr;")
    assert "!occlusionActive" not in single
    assert "const bool occlusionActive=" not in fn
    # Query handling remains single native execution, never binocular.
    prepare = function_block(source, "bool PrepareDuplicatedDraw(")
    assert "ActiveOcclusionQueries.load(std::memory_order_acquire)>0" in prepare
    assert "return false;" in prepare


def verify_sbs(source: str) -> None:
    fn = function_block(source, "bool ComposeSbs(")
    assert fn.count("setupOk = SUCCEEDED(device->Set") == 25
    assert "bool setupOk=true;" in fn
    assert "if(FAILED(device->CreateStateBlock(D3DSBT_ALL,&stateBlock))||!stateBlock){if(stateBlock)stateBlock->Release();return false;}" in fn
    assert "const bool stateOk=setupOk&&SUCCEEDED(device->SetViewport(&full))" in fn
    assert "success=leftOk&&rightOk&&SUCCEEDED(endHr);" in fn
    assert "if(!restoreOk)NoteRestoreFailure(" in fn


def verify_r7_resource_initialization(source: str) -> None:
    fn = function_block(source, "bool EnsureStereoResources(")
    for marker in (
        "D3DVIEWPORT9 initViewport=savedViewport;",
        "initViewport.X=0;initViewport.Y=0;",
        "initViewport.Width=desc.Width;initViewport.Height=desc.Height;",
        "device->SetViewport(&initViewport)",
    ):
        assert marker in fn, marker
    assert fn.index("device->SetViewport(&initViewport)") < fn.index(
        "if(initOk&&FAILED(ClearHook.stdcall<HRESULT>(") < fn.rindex(
        "device->SetViewport(&savedViewport)")
    assert "if(!initOk){ReleaseStereoResources();return false;}" in fn
    assert fn.index("if(!initOk){ReleaseStereoResources();return false;}") < fn.index(
        "StereoResourcesReady=true;")


def verify_r7_bootstrap_coverage(source: str) -> None:
    fn = function_block(source, "bool TryBootstrapRightDepthFromRecentClear(")
    for marker in (
        "savedViewport.X!=0||savedViewport.Y!=0||",
        "savedViewport.Width!=BackBufferDesc.Width||",
        "savedViewport.Height!=BackBufferDesc.Height)return false;",
    ):
        assert marker in fn, marker
    assert fn.index("savedViewport.X!=0||savedViewport.Y!=0||") < fn.index(
        "SetRenderTargetHook.stdcall<HRESULT>(")
    assert fn.index("savedViewport.Height!=BackBufferDesc.Height)return false;") < fn.index(
        "RightDepthSynchronized=true;")


def verify_r9(source: str) -> None:
    fn = function_block(source, "HRESULT __stdcall PresentDestR9(")
    recovery = fn.split("if (!composedStereo || FrameStereoIncomplete)", 1)[1].split(
        "R9MaybeLogSummary();", 1)[0]
    assert "if (R9MonoSeeded && !R9MonoBackupGap &&" in recovery
    assert "!R9RestoreMonoBeforePresent(device, R9FailureName(FrameFailureReason))" in recovery
    assert recovery.index("!R9RestoreMonoBeforePresent(") < recovery.index(
        "R9MonoBackupGap = true;") < recovery.index(
        "R9Poison(OutRunVR::StereoFailureRestoreFailed,")
    assert "Present/mono-shadow-restore" in recovery
    # The game still physically Presents once; no retry/copy or fabricated
    # mono frame is allowed after an unsuccessful GPU StretchRect.
    assert fn.count("const HRESULT rawPresentHr = PresentHook.stdcall<HRESULT>(") == 1
    assert fn.index("R9Poison(OutRunVR::StereoFailureRestoreFailed,") < fn.index(
        "const HRESULT rawPresentHr = PresentHook.stdcall<HRESULT>(")


def verify_r9_query_color_skip(source: str) -> None:
    fn = function_block(source, "bool R9ReplayMonoDraw(")
    query = fn.split(
        "if (ActiveOcclusionQueries.load(std::memory_order_acquire) > 0)", 1
    )[1].split("IDirect3DSurface9* savedRt", 1)[0]
    required = (
        "ReadTrackedRenderState(",
        "device, D3DRS_COLORWRITEENABLE, colorWriteMask);",
        "if (!colorMaskKnown || colorWriteMask != 0)",
        "InvalidateRightDepthStencilIfLeftMayWrite(device);",
        "R9MonoBackupGap = true;",
        "R9Poison(OutRunVR::StereoFailureOcclusionQueryActive,",
        "++R9OcclusionBackupSkips;",
        "return true; // never duplicate a live occlusion-query Draw",
    )
    for item in required:
        assert item in query, item
    assert query.index("ReadTrackedRenderState(") < query.index(
        "if (!colorMaskKnown || colorWriteMask != 0)") < query.index(
        "InvalidateRightDepthStencilIfLeftMayWrite(device);") < query.index(
        "R9MonoBackupGap = true;") < query.index(
        "R9Poison(OutRunVR::StereoFailureOcclusionQueryActive,") < query.index(
        "return true; // never duplicate a live occlusion-query Draw")
    assert "actualDraw()" not in query
    # R9's caller executes one original draw after the query skip is
    # recognized. A poisoned frame never routes that draw back to stereo.
    caller = function_block(source, "HRESULT R9ExecuteDraw(")
    assert "if (FrameStereoIncomplete)" in caller
    assert caller.index("if (FrameStereoIncomplete)") < caller.index(
        "const auto before = FrameFailureReason;")
    assert "return actualDraw();" in caller


def verify_r9_shared_offscreen_depth(source: str) -> None:
    # 01517: recognize exact COM identity only, never descriptor similarity;
    # preserve a single original offscreen draw and normal return HRESULT.
    fn = function_block(source, "HRESULT R9ExecuteDraw(")
    branch = fn.split("if (!wanted || !mainTarget)", 1)[1].split(
        "// Do not start stereo in the middle of a frame.", 1)[0]
    for marker in (
        "if (wanted && !mainTarget && R9StereoSeeded &&",
        "R9MainDepthKnown && !R9DeferredDepth &&",
        "TrackedDepthStencil == R9MainDepthIdentity &&",
        "(RightDepthSynchronized || RightStencilSynchronized))",
        "InvalidateRightDepthStencilIfLeftMayWrite(device);",
        "++R9MainDepthContentSerial;",
        "return legacyDraw();",
    ):
        assert marker in branch, marker
    assert "GetDesc(" not in branch and "CreateDepthStencilSurface(" not in branch
    assert "R9Poison(" not in branch
    assert branch.count("return legacyDraw();") == 1
    assert branch.index("TrackedDepthStencil == R9MainDepthIdentity &&") < (
        branch.index("InvalidateRightDepthStencilIfLeftMayWrite(device);"))
    assert branch.index("InvalidateRightDepthStencilIfLeftMayWrite(device);") < (
        branch.index("++R9MainDepthContentSerial;"))
    assert branch.index("++R9MainDepthContentSerial;") < branch.index(
        "return legacyDraw();")


def query_gap_if_color_write(mask_known: bool, mask: int) -> bool:
    return not mask_known or mask != 0


def rejects(check, source: str, before: str, after: str) -> None:
    assert before in source, "source mutation anchor missing: " + before
    mutant = source.replace(before, after, 1)
    try:
        check(mutant)
    except (AssertionError, ValueError):
        return
    raise AssertionError("unsafe mutation survived: " + before)


def rejects_in_function(check, source: str, signature: str,
                        before: str, after: str) -> None:
    fn = function_block(source, signature)
    assert before in fn, "function mutation anchor missing: " + before
    mutant = source.replace(fn, fn.replace(before, after, 1), 1)
    try:
        check(mutant)
    except (AssertionError, ValueError):
        return
    raise AssertionError("unsafe function mutation survived: " + before)


def main() -> None:
    r30 = R30_PATH.read_text(encoding="utf-8")
    r7 = R7_PATH.read_text(encoding="utf-8")
    r9 = R9_PATH.read_text(encoding="utf-8")
    verify_r30(r30)
    verify_r7(r7)
    verify_r7_resource_initialization(r7)
    verify_r7_bootstrap_coverage(r7)
    verify_sbs(r7)
    verify_r9(r9)
    verify_r9_query_color_skip(r9)
    verify_r9_shared_offscreen_depth(r9)
    for known, mask, gap in ((True, 0, False), (True, 0xF, True),
                             (True, 0x8, True), (False, 0, True)):
        assert query_gap_if_color_write(known, mask) == gap
    rejects_in_function(verify_r30, r30, "HRESULT R30TryScreenSpaceFovDraw(", "R9NoteStereoDrawWithoutMonoBackup();", "/* missing R9 gap */")
    rejects_in_function(verify_r30, r30, "HRESULT R30TryScreenSpaceFovDraw(", "R9NoteMainDepthContentWrite();", "/* missing R9 depth serial */")
    rejects_in_function(verify_r30, r30, "HRESULT R30TryScreenSpaceFovDraw(", "return E_NOTIMPL;\n            }\n\n            // The first physical LEFT Draw", "return E_NOTIMPL;\n            }\n\n            R9NoteStereoDrawWithoutMonoBackup();\n            // The first physical LEFT Draw")
    rejects_in_function(verify_r30, r30, "HRESULT R30TryScreenSpaceFovDraw(", "R9Poison(OutRunVR::StereoFailureRestoreFailed,", "/* failure not poisoned */ (")
    rejects_in_function(verify_r7, r7, "HRESULT ExecuteStereoDraw(", "if(StereoWanted()&&TargetIsBackBuffer())", "if(StereoWanted()&&TargetIsBackBuffer()&&!occlusionActive)")
    rejects_in_function(verify_r7, r7, "HRESULT ExecuteStereoDraw(", "InvalidateRightDepthStencilIfLeftMayWrite(device);\n\t\t\t\treturn drawCall();", "/* omitted invalidation */\n\t\t\t\treturn drawCall();")
    rejects_in_function(verify_r7, r7, "bool PrepareDuplicatedDraw(", "ActiveOcclusionQueries.load(std::memory_order_acquire)>0", "false")
    rejects_in_function(verify_sbs, r7, "bool ComposeSbs(", "if(stateBlock)stateBlock->Release();return false;", "return false;")
    rejects_in_function(verify_sbs, r7, "bool ComposeSbs(", "const bool stateOk=setupOk&&SUCCEEDED(device->SetViewport(&full))", "const bool stateOk=SUCCEEDED(device->SetViewport(&full))")
    rejects_in_function(verify_sbs, r7, "bool ComposeSbs(", "setupOk = SUCCEEDED(device->SetSamplerState(0,D3DSAMP_SRGBTEXTURE,FALSE)) && setupOk;", "device->SetSamplerState(0,D3DSAMP_SRGBTEXTURE,FALSE);")
    rejects_in_function(verify_r9, r9, "HRESULT __stdcall PresentDestR9(", "!R9RestoreMonoBeforePresent(device, R9FailureName(FrameFailureReason))", "R9RestoreMonoBeforePresent(device, R9FailureName(FrameFailureReason))")
    rejects_in_function(verify_r9, r9, "HRESULT __stdcall PresentDestR9(", "R9MonoBackupGap = true;", "/* lost recovery fence */")
    rejects_in_function(verify_r9, r9, "HRESULT __stdcall PresentDestR9(", 'R9Poison(OutRunVR::StereoFailureRestoreFailed,', '/* lost failure propagation */ (')
    rejects_in_function(verify_r7_bootstrap_coverage, r7, "bool TryBootstrapRightDepthFromRecentClear(", "savedViewport.X!=0||savedViewport.Y!=0||", "savedViewport.X!=0 && savedViewport.Y!=0||")
    rejects_in_function(verify_r7_bootstrap_coverage, r7, "bool TryBootstrapRightDepthFromRecentClear(", "savedViewport.Width!=BackBufferDesc.Width||", "savedViewport.Width>BackBufferDesc.Width||")
    rejects_in_function(verify_r7_resource_initialization, r7, "bool EnsureStereoResources(", "device->SetViewport(&initViewport)", "device->SetViewport(&savedViewport)")
    rejects_in_function(verify_r7_resource_initialization, r7, "bool EnsureStereoResources(", "initViewport.Width=desc.Width;initViewport.Height=desc.Height;", "initViewport.Width=savedViewport.Width;initViewport.Height=savedViewport.Height;")
    rejects_in_function(verify_r9_query_color_skip, r9,
        "bool R9ReplayMonoDraw(", "if (!colorMaskKnown || colorWriteMask != 0)",
        "if (colorMaskKnown && colorWriteMask != 0)")
    rejects_in_function(verify_r9_query_color_skip, r9,
        "bool R9ReplayMonoDraw(", "InvalidateRightDepthStencilIfLeftMayWrite(device);",
        "/* RIGHT depth content erroneously trusted */")
    rejects_in_function(verify_r9_query_color_skip, r9,
        "bool R9ReplayMonoDraw(", "R9MonoBackupGap = true;",
        "/* corrupt mono history allowed */")
    rejects_in_function(verify_r9_query_color_skip, r9,
        "bool R9ReplayMonoDraw(", "R9Poison(OutRunVR::StereoFailureOcclusionQueryActive,",
        "/* loss of fail-closed poison */(")
    rejects_in_function(verify_r9_query_color_skip, r9,
        "bool R9ReplayMonoDraw(", "return true; // never duplicate a live occlusion-query Draw",
        "return false; // query accidentally replayed")
    rejects_in_function(verify_r9_shared_offscreen_depth, r9,
        "HRESULT R9ExecuteDraw(", "TrackedDepthStencil == R9MainDepthIdentity &&",
        "TrackedDepthStencil != R9MainDepthIdentity &&")
    rejects_in_function(verify_r9_shared_offscreen_depth, r9,
        "HRESULT R9ExecuteDraw(", "R9MainDepthKnown && !R9DeferredDepth &&",
        "R9MainDepthKnown &&")
    rejects_in_function(verify_r9_shared_offscreen_depth, r9,
        "HRESULT R9ExecuteDraw(", "InvalidateRightDepthStencilIfLeftMayWrite(device);",
        "/* stale RIGHT depth allowed */")
    rejects_in_function(verify_r9_shared_offscreen_depth, r9,
        "HRESULT R9ExecuteDraw(",
        "return legacyDraw();\n\t\t\t}\n\n\t\t\t// Do not start stereo",
        "return actualDraw();\n\t\t\t}\n\n\t\t\t// Do not start stereo")
    print("PASS R26/R7/R9 01517 exact offscreen depth-lineage guard; 25 destructive mutations")
    print("RUNTIME_VALIDATION=UNTESTED")


if __name__ == "__main__":
    main()
