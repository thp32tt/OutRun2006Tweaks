#!/usr/bin/env python3
"""00774: real menu/vehicle/race native Draw/Indexed uses renamed dynamic streams.
Source gate plus compiled portable memory regression; Quest3/HMD untested.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/native_game_dynamic_stream.hpp").read_text()
wf = (root / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(code):
    head, body = code.split("bool submit(State& s,", 1)
    live = body.split("// Pixel shader alpha test", 1)[0]
    return all(token in head for token in (
        '#include "native_game_dynamic_stream.hpp"',
        "desc.Usage = D3D11_USAGE_DYNAMIC;",
        "desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;",
        "D3D11_MAP_WRITE_DISCARD",
        "game_native_copy_dynamic_stream(",
        "context->Unmap(buffer, 0u);",
    )) and all(token in live for token in (
        "upload_full_game_stream(ctx, s.fullGameVertexUpload.Get(),",
        "upload_full_game_stream(ctx, s.fullGameIndexUpload.Get(),",
        "vb = s.fullGameVertexUpload;",
        "ib = s.fullGameIndexUpload;",
        "bd.Usage = D3D11_USAGE_IMMUTABLE;",
    )) and "ctx->UpdateSubresource(s.fullGameVertexUpload.Get()" not in live \
       and "ctx->UpdateSubresource(s.fullGameIndexUpload.Get()" not in live

assert integrated(src)
for token in ("D3D11_USAGE_DYNAMIC", "D3D11_CPU_ACCESS_WRITE", "D3D11_MAP_WRITE_DISCARD"):
    broken = src.replace(token, "DISABLED_DYNAMIC_UPLOAD", 1)
    assert broken != src and not integrated(broken), token
for token in ("upload_full_game_stream(ctx, s.fullGameVertexUpload.Get(),",
              "upload_full_game_stream(ctx, s.fullGameIndexUpload.Get(),"):
    broken = src.replace(token, "skip_native_upload(", 1)
    assert broken != src and not integrated(broken), token
assert "game_native_copy_dynamic_stream(" in header
assert "if (!mapped || !source || bytes == 0u || bytes > capacity) return false;" in header
assert "tools/dx11_dynamic_stream_probe_00774.cpp" in wf
assert "tools/test_dx11_dynamic_stream_game_frame_00774.py" in wf
print("PASS 00774: game-created Draw/DrawIndexed dynamic upload, fail-closed Map, immutable inset fallback")
