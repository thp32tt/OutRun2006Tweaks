#!/usr/bin/env python3
"""R26+HUD exact source guards for DX9Ex reviews 01511, 01516 and 01521.

Static regression and destructive mutations only: not a Quest3/GPU test.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R30_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
R7_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r7.inc"


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
    assert "const bool stateOk=setupOk&&SUCCEEDED(device->SetViewport(&full))" in fn
    assert "success=leftOk&&rightOk&&SUCCEEDED(endHr);" in fn
    assert "if(!restoreOk)NoteRestoreFailure(" in fn


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
    verify_r30(r30)
    verify_r7(r7)
    verify_sbs(r7)
    rejects_in_function(verify_r30, r30, "HRESULT R30TryScreenSpaceFovDraw(", "R9NoteStereoDrawWithoutMonoBackup();", "/* missing R9 gap */")
    rejects_in_function(verify_r30, r30, "HRESULT R30TryScreenSpaceFovDraw(", "R9NoteMainDepthContentWrite();", "/* missing R9 depth serial */")
    rejects_in_function(verify_r30, r30, "HRESULT R30TryScreenSpaceFovDraw(", "return E_NOTIMPL;\n            }\n\n            // The first physical LEFT Draw", "return E_NOTIMPL;\n            }\n\n            R9NoteStereoDrawWithoutMonoBackup();\n            // The first physical LEFT Draw")
    rejects_in_function(verify_r30, r30, "HRESULT R30TryScreenSpaceFovDraw(", "R9Poison(OutRunVR::StereoFailureRestoreFailed,", "/* failure not poisoned */ (")
    rejects_in_function(verify_r7, r7, "HRESULT ExecuteStereoDraw(", "if(StereoWanted()&&TargetIsBackBuffer())", "if(StereoWanted()&&TargetIsBackBuffer()&&!occlusionActive)")
    rejects_in_function(verify_r7, r7, "HRESULT ExecuteStereoDraw(", "InvalidateRightDepthStencilIfLeftMayWrite(device);\n\t\t\t\treturn drawCall();", "/* omitted invalidation */\n\t\t\t\treturn drawCall();")
    rejects_in_function(verify_r7, r7, "bool PrepareDuplicatedDraw(", "ActiveOcclusionQueries.load(std::memory_order_acquire)>0", "false")
    rejects_in_function(verify_sbs, r7, "bool ComposeSbs(", "const bool stateOk=setupOk&&SUCCEEDED(device->SetViewport(&full))", "const bool stateOk=SUCCEEDED(device->SetViewport(&full))")
    rejects_in_function(verify_sbs, r7, "bool ComposeSbs(", "setupOk = SUCCEEDED(device->SetSamplerState(0,D3DSAMP_SRGBTEXTURE,FALSE)) && setupOk;", "device->SetSamplerState(0,D3DSAMP_SRGBTEXTURE,FALSE);")
    print("PASS R26 01521 mono WVP + R7 01516 query-depth + 01511 SBS setup HRESULT; 9 destructive mutations")
    print("RUNTIME_VALIDATION=UNTESTED")


if __name__ == "__main__":
    main()
