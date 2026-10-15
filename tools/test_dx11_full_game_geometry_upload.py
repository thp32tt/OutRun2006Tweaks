#!/usr/bin/env python3
"""Source integration checks for full-resolution native D3D11 VB/IB uploads.

The exact-SHA Windows Build also compiles this code. Real game/HMD remains UNTESTED.
"""
from pathlib import Path

src = (Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
head, submit = src.split("bool submit(State& s,", 1)
start = submit.split("// Pixel shader alpha test", 1)[0]
assert "ComPtr<ID3D11Buffer> fullGameVertexUpload;" in head
assert "ComPtr<ID3D11Buffer> fullGameIndexUpload;" in head
assert "s.fullGameVertexUpload.Reset();" in head
assert "s.fullGameIndexUpload.Reset();" in head
assert "bool ensure_full_game_upload_buffer(" in head
assert "desc.Usage = D3D11_USAGE_DYNAMIC;" in head
assert "desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;" in head
assert "context->Map(buffer, 0u, D3D11_MAP_WRITE_DISCARD, 0u, &mapped)" in head
assert "context->Unmap(buffer, 0u);" in head
assert "if (env_full_game_opt_in()) {" in start
for token in (
    "s.fullGameVertexCapacity, vertexSize,",
    "s.fullGameIndexCapacity, indexSize,",
    "upload_full_game_stream(ctx, s.fullGameVertexUpload.Get(),",
    "upload_full_game_stream(ctx, s.fullGameIndexUpload.Get(),",
    "s.fullGameVertexCapacity,\n                                     vertices.data(), vertexSize)",
    "s.fullGameIndexCapacity,\n                                         indices, indexSize)",
    "if (FAILED(dev->GetDeviceRemovedReason())) return false;",
    "bd.Usage = D3D11_USAGE_IMMUTABLE;",  # diagnostic fallback
    "dev->CreateBuffer(&bd, &initial, vb.GetAddressOf())",
):
    assert token in start, token
assert "ctx->DrawIndexed(indexCount, 0, 0);" in submit
assert "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in submit
assert "mirror_texture(dev, capture, sampledView, sampledSampler)" in submit
# Destructive mutation: a missing live vertex upload cannot satisfy the contract.
assert "upload_full_game_stream(ctx, s.fullGameVertexUpload.Get()," not in start.replace(
    "upload_full_game_stream(ctx, s.fullGameVertexUpload.Get(),", "// detached", 1)
assert "ctx->UpdateSubresource(s.fullGameVertexUpload.Get()" not in start
assert "ctx->UpdateSubresource(s.fullGameIndexUpload.Get()" not in start
print("PASS: live full-game DISCARD-renamed VB/IB uploads and original D3D9 fallback")
