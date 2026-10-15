#!/usr/bin/env python3
"""R23 private-eye depth/stencil batching; static path + destructive mutations.

D3D9 Clear can clear depth and stencil together for a compatible depth surface.
The test proves the guarded path and fallback, not headset FPS or GPU timings.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r23.cpp"


def slices(source: str) -> tuple[str, str]:
    start = source.index("bool R23ClearPrivateDepth(")
    end = source.index("bool R23InitializeStereoFromAuthoritativeBaseline(", start)
    tail = source.index("bool R23HaveFreshCurrentFramePose(")
    # The private-eye function must appear after the state-restore function.
    assert tail < start
    return source[start:end], source[end:source.index("HRESULT __stdcall ClearDestR23(", end)]


def verify(source: str) -> None:
    body, initializer = slices(source)
    ordered = (
        "if (!depth)",
        "SetRenderTargetHook.stdcall<HRESULT>(device, 0u, rt)",
        "SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, depth)",
        "device->SetViewport(&state.viewport)",
        "device->SetScissorRect(&state.rect)",
        "device->SetRenderState(D3DRS_SCISSORTESTENABLE,",
        "const bool clearStencil = stencilSafe && SurfaceHasStencil(depth);",
        "const DWORD clearFlags = D3DCLEAR_ZBUFFER |",
        "(clearStencil ? D3DCLEAR_STENCIL : 0u);",
        "const HRESULT hr = ClearHook.stdcall<HRESULT>(device, 0u, nullptr,",
        "clearFlags, 0, R23DepthClearZ,",
        "clearStencil ? R23StencilClearValue : 0u);",
        "++R23RecoveryVrSurfaceWrites;",
        "return SUCCEEDED(hr);",
    )
    positions = [body.find(token) for token in ordered]
    assert all(i >= 0 for i in positions), [ordered[n] for n, i in enumerate(positions) if i < 0]
    assert positions == sorted(positions), "R23 depth/stencil clear ordering changed"
    assert body.count("ClearHook.stdcall<HRESULT>(") == 1, "extra depth/stencil GPU clear call"
    assert "D3DCLEAR_STENCIL, 0" not in body, "independent stencil pass restored"
    assert "if (!depth)\n                return true;" in body
    assert initializer.count("R23ClearPrivateDepth(device,") == 2, "two private-eye clear calls required"
    assert initializer.index("R23ClearPrivateDepth(device, RightEyeSurface,") < initializer.index(
        "R23ClearPrivateDepth(device, R9MonoSurface,")
    assert initializer.index("R23ClearPrivateDepth(device, R9MonoSurface,") < initializer.index(
        "R23RestoreActualGameState(device, savedRt, savedDepth, state)")


if __name__ == "__main__":
    source = SOURCE.read_text(encoding="utf-8")
    verify(source)
    mutations = (
        ("stencilSafe && SurfaceHasStencil(depth)", "true && SurfaceHasStencil(depth)"),
        ("SurfaceHasStencil(depth)", "true"),
        ("D3DCLEAR_ZBUFFER |", "0u |"),
        ("clearStencil ? D3DCLEAR_STENCIL : 0u", "clearStencil ? 0u : 0u"),
        ("clearFlags, 0, R23DepthClearZ,", "clearFlags, 0, 1.0f,"),
        ("clearStencil ? R23StencilClearValue : 0u", "clearStencil ? 0u : 0u"),
        ("++R23RecoveryVrSurfaceWrites;", "/* missing GPU-write accounting */"),
        ("return SUCCEEDED(hr);", "return true;"),
        ("SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, depth)", "SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, nullptr)"),
        ("device->SetViewport(&state.viewport)", "device->GetViewport(&state.viewport)"),
        ("ClearHook.stdcall<HRESULT>(device, 0u, nullptr,", "device->Clear(0u, nullptr,"),
    )
    for good, bad in mutations:
        body, _ = slices(source)
        assert good in body, f"mutation anchor absent: {good}"
        mutant = source.replace(body, body.replace(good, bad, 1), 1)
        try:
            verify(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"R23 private-eye destructive mutation survived: {good}")
    print(f"PASS R23 depth/stencil merged private-eye clears and {len(mutations)} negative mutations")
