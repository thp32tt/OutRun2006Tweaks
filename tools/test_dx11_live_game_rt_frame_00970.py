#!/usr/bin/env python3
"""00970: real full-size game render-target texture feedback into native Draw."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/live_game_render_target_readback.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
def integrated(source):
    begin = source.index("bool mirror_texture(")
    end = source.index("bool submit(", begin)
    mirror = source[begin:end]
    budget = mirror.index("native_rt_readback::bounded_gpu_snapshot(")
    snap = mirror.index("GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())")
    decode = mirror.index("native_rt_readback::unpack_row(")
    bind = mirror.index("CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())")
    return all((
        "base.Width, base.Height, levels, rtLayout))" in mirror,
        budget < snap < decode < bind,
        "readbackSurface->LockRect(&lock, nullptr, D3DLOCK_READONLY)" in mirror,
        "readbackSurface->UnlockRect()" in mirror,
        "if (gpuRenderTarget && (base.Width > 1024u || base.Height > 1024u))" not in mirror,
        "mirror_texture(dev, capture, sampledView, sampledSampler)" in source,
        "ctx->PSSetShaderResources(0, 1, &boundView);" in source,
        "if (ib) ctx->DrawIndexed(indexCount, 0, 0);" in source,
        "void observe_linear(" in source and "void observe_indexed(" in source,
        "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in source,
        "monoNativePublicationAllowed" in source,
        "kMaxLiveRtReadbackSurfaceBytes = 16ull << 20u" in header,
        "kMaxLiveRtReadbackMipChainBytes = 24ull << 20u" in header,
    ))
assert integrated(bridge), "native full-game RTT must be per-Draw, budgeted and fail-closed"
for old in (
    "native_rt_readback::bounded_gpu_snapshot(",
    "GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())",
    "native_rt_readback::unpack_row(",
    "ctx->PSSetShaderResources(0, 1, &boundView);",
    "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)",
):
    assert old in bridge
    assert not integrated(bridge.replace(old, "/* removed source boundary */", 1)), old
assert "tools/dx11_live_game_rt_frame_probe_00970.cpp" in workflow
assert "python tools/test_dx11_live_game_rt_frame_00970.py" in workflow
print("00970 live full-size D3D9 RT -> native SRV/Draw -> guarded frame source PASS")
