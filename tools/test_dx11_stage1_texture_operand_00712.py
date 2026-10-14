#!/usr/bin/env python3
"""DX11 Stage1 TEXTURE RGB/alpha real game Draw/Indexed admission regression 00712."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
c=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
w=(root/".github/workflows/dx11-fast-structural.yml").read_text()
def integrated(h,c):
    gate=c.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    shader=c.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
    draw=c.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
    return all(s in h for s in (
        "stage1_matched_texture_two_source_supported(",
        "stage1_matched_texture_three_source_supported(",
        "stage1_operation_reads_texture(",
        "stage1_three_source_reads_texture(",
        "kStage1Texture = 2u",
        "stage1_matched_texture_operand_supported(arg,producerTemp)")) and all(s in gate for s in (
        "stage1NeedsMatchedTexture", "stage1UsesTextureOperand",
        "tex1.Get() != tex.Get()", "uv1 != capture.coordIndex",
        "s0 != s1", "stage1_matched_texture_two_source_supported(",
        "stage1_matched_texture_three_source_supported(",
        "capture.stage1TextureOperands = stage1UsesTextureOperand")) and all(s in shader for s in (
        "Stage1AndAlphaTextured(", "Stage1SourceTextured(",
        "Stage1ThreeSourceTextured(", "(source & 15) != 2",
        "stage1TextureColor", "if (stage1Ops.w != 0)")) and all(s in draw for s in (
        "payload.operations[3] = capture.stage1TextureOperands ? 1 : 0;",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
assert integrated(h,c)
for s in ("stage1NeedsMatchedTexture","s0 != s1","tex1.Get() != tex.Get()",
          "payload.operations[3] = capture.stage1TextureOperands ? 1 : 0;",
          "Stage1ThreeSourceTextured(","stage1_matched_texture_two_source_supported("):
    if s in h: assert not integrated(h.replace(s,"",1),c),s
    else: assert not integrated(h,c.replace(s,"",1)),s
assert "test_dx11_stage1_texture_operand_00712.py" in w
assert "dx11_game_stage1_texture_operand_probe_00712.cpp" in w
print("PASS 00712 source/PS/live Draw+Indexed and gamepad-safe matched-source fallback")
