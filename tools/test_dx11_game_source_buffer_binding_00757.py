#!/usr/bin/env python3
"""Real game Draw/DrawIndexed native buffer ownership regression (00757).

Verify that *both* existing source paths populate the buffers later bound by
the actual D3D11 Draw, rather than shadowing the buffers with local variables.
Windows CI compiles the production renderer; Quest3 gameplay stays UNTESTED.
"""
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")

def require_source_ownership(source: str) -> None:
    submit = source.split("bool submit(State& s,", 1)[1].split("bool observe_source_device(", 1)[0]
    before_draw = submit.split("// Pixel shader alpha test and OM alpha blend", 1)[0]
    owner = "ComPtr<ID3D11Buffer> vb, ib;"
    assert before_draw.count(owner) == 1, "shared D3D11 GPU owners absent"
    shared = before_draw.split(owner, 1)[1]
    assert shared.count("ComPtr<ID3D11Buffer> vb;") == 0, "diagnostic vertex owner shadows live Draw"
    assert shared.count("ComPtr<ID3D11Buffer> ib;") == 0, "diagnostic index owner shadows live Draw"
    full, diagnostic = shared.split("} else {", 1)
    assert "vb = s.fullGameVertexUpload;" in full
    assert "ib = s.fullGameIndexUpload;" in full
    assert "dev->CreateBuffer(&bd, &initial, vb.GetAddressOf())" in diagnostic
    assert "dev->CreateBuffer(&bd, &initial, ib.GetAddressOf())" in diagnostic
    assert "bd.Usage = D3D11_USAGE_IMMUTABLE;" in diagnostic
    assert "ctx->UpdateSubresource(s.fullGameVertexUpload.Get()" in full
    assert "ctx->UpdateSubresource(s.fullGameIndexUpload.Get()" in full
    guard = "if (!vb || (indices && indexCount && !ib)) return false;"
    assert guard in submit, "failed GPU source must preserve original D3D9 fallback"
    assert submit.index(guard) < submit.index("ctx->IASetVertexBuffers(")
    assert "ID3D11Buffer* boundVB = vb.Get();" in submit
    assert "ctx->IASetVertexBuffers(0, 1, &boundVB, &stride, &offset);" in submit
    assert "if (ib) ctx->IASetIndexBuffer(ib.Get(), DXGI_FORMAT_R32_UINT, 0);" in submit
    assert "if (ib) ctx->DrawIndexed(indexCount, 0, 0);" in submit
    assert "else ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in submit
    assert "s.pending = true;" in submit
    assert "return true;" in submit

require_source_ownership(SOURCE)
# Destructive negative tests: reintroducing *either* local shadow must fail,
# even if the D3D11 buffer creation and Draw strings still appear intact.
for invalid in (
    SOURCE.replace("dev->CreateBuffer(&bd, &initial, vb.GetAddressOf())",
                   "ComPtr<ID3D11Buffer> vb;\n    dev->CreateBuffer(&bd, &initial, vb.GetAddressOf())", 1),
    SOURCE.replace("dev->CreateBuffer(&bd, &initial, ib.GetAddressOf())",
                   "ComPtr<ID3D11Buffer> ib;\n        dev->CreateBuffer(&bd, &initial, ib.GetAddressOf())", 1),
    SOURCE.replace("if (!vb || (indices && indexCount && !ib)) return false;",
                   "/* unchecked native geometry */", 1),
):
    try:
        require_source_ownership(invalid)
    except AssertionError:
        pass
    else:
        raise AssertionError("mutated GPU Draw binding contract incorrectly passed")

print("PASS 00757: live game full-frame VB/IB and diagnostic VB/IB own exact IA Draw/DrawIndexed buffers with fallback")
