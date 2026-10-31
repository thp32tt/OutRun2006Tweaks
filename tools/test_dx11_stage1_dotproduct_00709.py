#!/usr/bin/env python3
"""00709 native game Stage1 signed DOTPRODUCT3 RGB and original-D3D9 fallback."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
h=(r/"src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
b=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
w=(r/".github/workflows/dx11-fast-structural.yml").read_text()
p=(r/"tools/dx11_game_stage1_dotproduct_probe_00709.cpp").read_text()
def integrated(header,bridge):
    sh=bridge.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
    state=bridge.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    draw=bridge.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
    return all(x in header for x in ("kStage1DotProduct3 = 24u",
        "stage1_dotproduct_color_operation(operation)",
        "!stage1_dotproduct_color_operation(operation)",
        "stage1_dotproduct_color_operation(op)",
        "!stage1_dotproduct_color_operation(op)")) and all(x in sh for x in (
        "if (op == 24) {", "signedA = a.rgb * 2.0f - 1.0f",
        "signedB = b.rgb * 2.0f - 1.0f",
        "signedDot = saturate(dot(signedA, signedB))",
        "float4(signedDot, signedDot, signedDot, signedDot)",
        "stage1Ops.y, stage0, diffuse).a;")) and all(x in state for x in (
        "stage1_combiner_supported(nextColorOp, color1, color2)",
        "stage1_combiner_supported_with_temp(nextColorOp, color1, color2, stage0WritesTemp)",
        "stage1_alpha_supported(alphaOp, alpha1, alpha2)",
        "stage1_alpha_supported_with_temp(alphaOp, alpha1, alpha2, stage0WritesTemp)",
        "stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE",
        "capture.stage1ColorOp = nextColorOp;",
        "capture.stage1AlphaOp = alphaOp;")) and all(x in draw for x in (
        "ctx->PSSetConstantBuffers(1, 1, &combiner)",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")) and (
        "kStage1DotProduct3 == D3DTOP_DOTPRODUCT3" in bridge and
        "before_game_present(" in bridge)
assert integrated(h,b)
for s in ("if (op == 24) {","signedDot = saturate(dot(signedA, signedB))",
          "stage1Ops.y, stage0, diffuse).a;"):
    assert not integrated(h,b.replace(s,"",1))
for s in ("!stage1_dotproduct_color_operation(operation)",
          "!stage1_dotproduct_color_operation(op)"):
    assert not integrated(h.replace(s,"true",1),b)
for s in ("regular!=400u||temp!=160u","stage1_alpha_supported_with_temp(kStage1DotProduct3,t,o,true)",
          "stage1_operation_reads_specular","adjust(a,kStage1AlphaReplicate)"):
    assert s in p
assert "python tools/test_dx11_stage1_dotproduct_00709.py" in w
assert "tools/dx11_game_stage1_dotproduct_probe_00709.cpp" in w
print("PASS 00709 D3D9 DP3->native HLSL->Draw/Indexed, independent alpha, negative/fallback")
