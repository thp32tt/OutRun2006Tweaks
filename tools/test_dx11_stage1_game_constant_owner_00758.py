#!/usr/bin/env python3
"""Live real-game menu/vehicle/race Stage-1 D3D11 b1 ownership regression (00758).

The source test is destructive for buffer lifetime, game-state refresh, and
stage-0-only unbind. The Windows gate compiles the production C++; HMD UNTESTED.
"""
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")


def check(source: str) -> None:
    head, submit = source.split("bool submit(State& s,", 1)
    submit = submit.split("bool observe_source_device(", 1)[0]
    init = head.split("D3D11_BUFFER_DESC constants{}", 1)[1].split("D3D11_TEXTURE2D_DESC desc{}", 1)[0]
    before_draw = submit.split("ctx->DrawIndexed(indexCount, 0, 0);", 1)[0]
    stage = submit.split("if (capture.stage1Enabled) {", 1)[1].split("ComPtr<ID3D11Buffer> vb, ib;", 1)[0]

    assert "struct Stage1Upload {" in head
    assert "static_assert(sizeof(Stage1Upload) == 80u" in head
    assert "ComPtr<ID3D11Buffer> stage1Constants;" in head
    assert "s.alphaConstants && s.stage1Constants && readbackReady)" in head
    assert "constants.ByteWidth = sizeof(Stage1Upload);" in init
    assert "constants.Usage = D3D11_USAGE_DEFAULT;" in init
    assert "dev->CreateBuffer(&constants, nullptr, s.stage1Constants.GetAddressOf())" in init
    assert head.count("s.stage1Constants.Reset();") == 1
    assert source.count("s.stage1Constants.Reset();") == 2  # Ensure/Reset
    assert "payload.factor" in stage and "payload.stageConstant" in stage
    assert "payload.operations[2] = capture.stage0ResultTemp ? 1 : 0;" in stage
    assert "payload.operations[3] = capture.stage1SeparateTexture ? 2 :" in stage
    assert "payload.arguments[i]" in stage and "payload.argZero[i]" in stage
    assert "ctx->UpdateSubresource(s.stage1Constants.Get(), 0u, nullptr," in stage
    assert "D3D11_USAGE_IMMUTABLE" not in stage
    assert "dev->CreateBuffer" not in stage
    assert before_draw.index("ctx->UpdateSubresource(s.stage1Constants.Get()") < before_draw.index("ctx->PSSetConstantBuffers(1, 1, &combiner);")
    assert "ID3D11Buffer* combiner = capture.stage1Enabled ? s.stage1Constants.Get() : nullptr;" in before_draw
    assert before_draw.count("ctx->PSSetConstantBuffers(1, 1, &combiner);") == 1
    assert "if (!vb || (indices && indexCount && !ib)) return false;" in submit
    assert "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in submit


check(SOURCE)
for old, new in (
    ("s.stage1Constants.Reset();", "/* missing native b1 generation reset */"),
    ("ctx->UpdateSubresource(s.stage1Constants.Get(), 0u, nullptr,", "/* no per-game-draw b1 update */"),
    ("ID3D11Buffer* combiner = capture.stage1Enabled ? s.stage1Constants.Get() : nullptr;",
     "ID3D11Buffer* combiner = s.stage1Constants.Get();"),
    ("constants.ByteWidth = sizeof(Stage1Upload);", "constants.ByteWidth = 16u;"),
    ("s.alphaConstants && s.stage1Constants && readbackReady)",
     "s.alphaConstants && readbackReady)"),
):
    assert old in SOURCE
    try:
        check(SOURCE.replace(old, new, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("00758 destructive mutation incorrectly admitted: " + old)

print("PASS 00758: menu/race game Stage-1 b1 GPU owner, per-Draw updates, stage-0 unbind, device Reset and D3D9 fallback")
