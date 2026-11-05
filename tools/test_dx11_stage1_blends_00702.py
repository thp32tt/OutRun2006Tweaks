#!/usr/bin/env python3
"""00702: live stage1 RGB and independent alpha BLEND* fading through native Draw."""
from pathlib import Path
p = Path(__file__).resolve().parents[1]
bridge = (p / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (p / "src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
probe = (p / "tools/dx11_game_stage1_blend_probe_00702.cpp").read_text()
workflow = (p / ".github/workflows/dx11-fast-structural.yml").read_text()
def integrated(s, h):
    shader = s.split('constexpr char kStage1FactorShader[] = R"(', 1)[1].split(')";', 1)[0]
    capture = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
    native = s.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
    return all((
        all(f"kStage1Blend{kind}Alpha == D3DTOP_BLEND{kind.upper()}ALPHA" in s
            for kind in ("Diffuse", "Factor", "Current")),
        "stage1_alpha_blend_operation(operation)" in h,
        "if (operation == kStage1BlendDiffuseAlpha) return true;" in h,
        "stage1_operation_reads_diffuse(nextColorOp, color1, color2)" in capture,
        "stage1_operation_reads_diffuse(alphaOp, alpha1, alpha2)" in capture,
        "(!layout.hasDiffuse &&" in capture,
        "capture.stage1ColorOp = nextColorOp;" in capture,
        "capture.stage1AlphaOp = alphaOp;" in capture,
        "capture.stage1Factor = {" in capture,
        "float Stage1BlendWeight(int op, float4 stage0, float4 diffuse)" in shader,
        "if (op == 12) return diffuse.a;" in shader,
        "if (op == 14) return stage1Factor.a;" in shader,
        "return stage0.a;" in shader,
        "if (op == 12 || op == 14 || op == 16)" in shader,
        "return saturate(lerp(b, a, Stage1BlendWeight(op, stage0, diffuse)));" in shader,
        "stage1Ops.x, stage0, diffuse);" in shader,
        "stage1Ops.y, stage0, diffuse).a;" in shader,
        "ctx->PSSetConstantBuffers(1, 1, &combiner)" in native,
        "ctx->DrawIndexed(indexCount, 0, 0);" in native,
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in native,
        "before_game_present(" in s,
    ))
assert integrated(bridge, header), "stage1 blend sources must reach native GPU Draw"
for token in ("variants == 432u", "kStage1BlendDiffuseAlpha",
              "stage1_operation_reads_diffuse", "0x40u", "13u", "15u"):
    assert token in probe, token
assert "python tools/test_dx11_stage1_blends_00702.py" in workflow
assert "g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic tools/dx11_game_stage1_blend_probe_00702.cpp" in workflow
for token in (
    "if (op == 12) return diffuse.a;", "if (op == 14) return stage1Factor.a;",
    "return stage0.a;", "if (op == 12 || op == 14 || op == 16)",
    "stage1Ops.x, stage0, diffuse);", "stage1Ops.y, stage0, diffuse).a;",
    "stage1_operation_reads_diffuse(alphaOp, alpha1, alpha2)",
    "capture.stage1Factor = {", "ctx->PSSetConstantBuffers(1, 1, &combiner)",
    "ctx->DrawIndexed(indexCount, 0, 0);", "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
):
    assert not integrated(bridge.replace(token, "", 1), header), token
for token in ("stage1_alpha_blend_operation(operation)",
              "if (operation == kStage1BlendDiffuseAlpha) return true;"):
    assert not integrated(bridge, header.replace(token, "", 1)), token
print("PASS 00702: live game stage1 diffuse/factor/current alpha blends -> RGB/alpha native draw + DX9Ex fallback")
