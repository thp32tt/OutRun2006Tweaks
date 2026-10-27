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
    assert single.index("InvalidateRightDepthStencilIfLeftMayWrite(device);") < single.index("return drawCall();")
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
    print("PASS R26/R7/R9: 01511,01513,01515,01516,01519,01521 guards; 16 destructive mutations")
    print("RUNTIME_VALIDATION=UNTESTED")


if __name__ == "__main__":
    main()
