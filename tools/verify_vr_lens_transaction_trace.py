#!/usr/bin/env python3
"""Read-only R26 lens receipts must distinguish setup from native eye Draw.

Source-order controls deliberately remove or move instrumentation. These are
not hardware tests and do not prove the submitted pixels are optically correct.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(src: str) -> None:
    body = src.split("HRESULT R30TryScreenSpaceFovDraw(", 1)[1].split(
        "HRESULT R30GuardScreenSpace(", 1)[0]
    assert "R30LensTransactionTrace lensTransaction" in body
    assert "lensTransaction.Begin(lensPhysicalCandidate," in body
    for token in (
        'lensTransaction.Emit("LEFT_WVP", E_FAIL);',
        'lensTransaction.Emit("LEFT_WVP", E_NOTIMPL);',
        'lensTransaction.Emit("LEFT_DRAW", leftHr);',
        'lensTransaction.Emit(lensTransaction.rightStage, leftHr);',
        "lensTransaction.leftDrawAttempted = true;",
        "lensTransaction.rightDrawAttempted = true;",
        "lensTransaction.leftDrawHr = leftHr;",
        "lensTransaction.rightDrawHr = rightHr;",
        'lensTransaction.rightStage = "RIGHT_RT";',
        'lensTransaction.rightStage = "RIGHT_DEPTH";',
        'lensTransaction.rightStage = "RIGHT_VIEWPORT";',
        'lensTransaction.rightStage = "RIGHT_WVP";',
        'lensTransaction.rightStage = "RIGHT_DRAW";',
        "lensTransaction.rightResultHr = rightHr;",
        "lensTransaction.restoreOk = restoreOk;",
    ):
        assert token in body, token
    assert body.count("const HRESULT leftHr = actualDraw();") == 1
    assert body.count("rightHr = actualDraw();") == 1
    assert body.index("lensTransaction.left.Capture(device);") < body.index(
        "const HRESULT leftHr = actualDraw();") < body.index(
        "lensTransaction.leftDrawHr = leftHr;") < body.index("if (FAILED(leftHr))")
    right = body.split('lensTransaction.rightStage = "RIGHT_DRAW";', 1)[1]
    assert right.index("lensTransaction.right.Capture(device);") < right.index(
        "rightHr = actualDraw();") < right.index("RestoreRightPassState(")
    assert right.index("RestoreRightPassState(") < right.index(
        "lensTransaction.post.Capture(device);")
    assert body.count("lensTransaction.post.Capture(device);") == 3
    for name, count in (("left", 1), ("right", 1), ("post", 3)):
        assert body.count(
            f"if (lensTransaction.sample) lensTransaction.{name}.Capture(device);") == count
    helper = src.split("struct R30LensRasterTrace", 1)[1].split(
        "void R30TraceVisualPipelineFull(", 1)[0]
    for token in (
        "HRESULT viewportHr = E_PENDING;", "HRESULT scissorHr = E_PENDING;",
        "HRESULT scissorEnableHr = E_PENDING;", "HRESULT rtHr = E_PENDING;",
        "HRESULT depthHr = E_PENDING;", "HRESULT leftDrawHr = E_PENDING;",
        "HRESULT rightDrawHr = E_PENDING;", "if (!enabled) return;",
        "if (!sample && !failureSample) return;",
        "reset.readStable && reset.resetSerial != sampledEpoch",
        "epochSamples <= 8", "failures <= 16",
        "device->GetViewport(&viewport)", "device->GetScissorRect(&scissor)",
        "device->GetRenderState(D3DRS_SCISSORTESTENABLE, &scissorEnabled)",
        "device->GetRenderTarget(0, &surface)",
        "device->GetDepthStencilSurface(&surface)",
        "VR LENS R30 TRANSACTION:", "VR LENS R30 EYE RASTER:",
        "leftDrawAttempted={}", "rightDrawAttempted={}",
        "captured={}", "viewportZ={:.9g},{:.9g}",
        "resetEpochEnd={}", "resetSnapshotStableEnd={}",
        'left.Log("LEFT_PRE_DRAW", serial);',
        'right.Log("RIGHT_PRE_DRAW", serial);',
        'post.Log("POST_RESTORE", serial);',
    ):
        assert token in helper, token
    assert helper.count("surface->Release();") == 2
    for forbidden in ("device->Set", "device->Draw", "device->Clear", "Flush("):
        assert forbidden not in helper, forbidden


if __name__ == "__main__":
    source = (ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text()
    verify(source)
    mutations = [
        ('lensTransaction.Emit("LEFT_DRAW", leftHr);', ''),
        ('lensTransaction.Emit("LEFT_WVP", E_NOTIMPL);', ''),
        ('lensTransaction.Emit("LEFT_WVP", E_FAIL);', ''),
        ("lensTransaction.rightDrawAttempted = true;", ""),
        ("lensTransaction.rightDrawHr = rightHr;", ""),
        ("lensTransaction.right.Capture(device);", "lensTransaction.left.Capture(device);"),
        ("lensTransaction.post.Capture(device);", ""),
        ("HRESULT rightDrawHr = E_PENDING;", "HRESULT rightDrawHr = D3D_OK;"),
        ("device->GetRenderState(D3DRS_SCISSORTESTENABLE, &scissorEnabled)", "E_PENDING"),
        ("if (!sample && !failureSample) return;", ""),
        ("epochSamples <= 8", "epochSamples <= 0"),
        ("surface->Release();", ""),
        ("if (lensTransaction.sample) lensTransaction.left.Capture(device);",
         "lensTransaction.left.Capture(device);"),
        ("if (lensTransaction.sample) lensTransaction.right.Capture(device);",
         "lensTransaction.right.Capture(device);"),
        ("if (lensTransaction.sample) lensTransaction.post.Capture(device);",
         "lensTransaction.post.Capture(device);"),
    ]
    for good, bad in mutations:
        assert good in source, good
        try:
            verify(source.replace(good, bad, 1))
        except (AssertionError, ValueError, IndexError):
            continue
        raise AssertionError("surviving mutation: " + good)
    print(f"PASS lens transaction failure/raster contracts; {len(mutations)} mutations rejected")
