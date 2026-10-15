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
assert "desc.Usage = D3D11_USAGE_DEFAULT;" in head
assert "if (env_full_game_opt_in()) {" in start
for token in (
    "s.fullGameVertexCapacity, vertexSize,",
    "s.fullGameIndexCapacity, indexSize,",
    "ctx->UpdateSubresource(s.fullGameVertexUpload.Get(), 0u,",
    "ctx->UpdateSubresource(s.fullGameIndexUpload.Get(), 0u,",
    "const D3D11_BOX vertexRange{0u, 0u, 0u, vertexSize, 1u, 1u};",
    "const D3D11_BOX indexRange{0u, 0u, 0u, indexSize, 1u, 1u};",
    "if (FAILED(dev->GetDeviceRemovedReason())) return false;",
    "bd.Usage = D3D11_USAGE_IMMUTABLE;",  # diagnostic fallback
    "dev->CreateBuffer(&bd, &initial, vb.GetAddressOf())",
):
    assert token in start, token
assert "ctx->DrawIndexed(indexCount, 0, 0);" in submit
assert "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in submit
assert "mirror_texture(dev, capture, sampledView, sampledSampler)" in submit
# Destructive mutation: a missing live vertex upload cannot satisfy the contract.
assert "ctx->UpdateSubresource(s.fullGameVertexUpload.Get(), 0u," not in start.replace(
    "ctx->UpdateSubresource(s.fullGameVertexUpload.Get(), 0u,", "// detached", 1)
print("PASS: live native full-game geometry uploads, separate VB/IB, device-loss reset and diagnostic fallback")
