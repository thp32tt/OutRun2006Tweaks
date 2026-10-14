#!/usr/bin/env python3
"""Live D3D9 Stage1 cross-channel RGB native shader integration (00704)."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
h=(r/"src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
c=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
p=(r/"tools/dx11_game_stage1_cross_channel_probe_00704.cpp").read_text()
w=(r/".github/workflows/dx11-fast-structural.yml").read_text()
codes=(
 "if (op == 18) return saturate(a + a.aaaa * b);",
 "if (op == 19) return saturate(a * b + a.aaaa);",
 "if (op == 20) return saturate(a + (1.0f - a.aaaa) * b);",
 "if (op == 21) return saturate((1.0f - a) * b + a.aaaa);",
)
sdks=(
 "kStage1ModulateAlphaAddColor == D3DTOP_MODULATEALPHA_ADDCOLOR",
 "kStage1ModulateColorAddAlpha == D3DTOP_MODULATECOLOR_ADDALPHA",
 "kStage1ModulateInvAlphaAddColor == D3DTOP_MODULATEINVALPHA_ADDCOLOR",
 "kStage1ModulateInvColorAddAlpha == D3DTOP_MODULATEINVCOLOR_ADDALPHA",
)
def integrated(header,bridge):
 shader=bridge.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
 producer=bridge.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
 submit=bridge.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
 return all(s in bridge for s in sdks) and all(s in shader for s in codes) and all(s in header for s in (
     "stage1_cross_channel_color_operation(operation)) &&",
     "!stage1_cross_channel_color_operation(operation)")) and all(s in producer for s in (
     "stage1_combiner_supported(nextColorOp, color1, color2)",
     "stage1_alpha_supported(alphaOp, alpha1, alpha2)",
     "stage1_operation_reads_diffuse(nextColorOp, color1, color2)",
     "stage1_operation_reads_diffuse(alphaOp, alpha1, alpha2)",
     "capture.stage1ColorOp = nextColorOp;",
     "capture.stage1AlphaOp = alphaOp;",
     "capture.stage1Args = {color1, color2, alpha1, alpha2};")) and all(s in shader for s in (
     "Stage1Source(stage0, diffuse, stage1Args.x)",
     "stage1Ops.x, stage0, diffuse);",
     "stage1Ops.y, stage0, diffuse).a;")) and all(s in submit for s in (
     "ctx->PSSetConstantBuffers(1, 1, &combiner)",
     "ctx->DrawIndexed(indexCount, 0, 0);",
     "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")) and "before_game_present(" in bridge
assert integrated(h,c)
for x in codes+sdks: assert not integrated(h,c.replace(x,"",1)),x
assert not integrated(h.replace("!stage1_cross_channel_color_operation(operation)","true",1),c)
for x in ("variants!=576u","stage1_alpha_supported(op,a,b)","stage1_operation_reads_diffuse",
          "0x40u|kStage1Factor","stage1_combiner_supported(op,2u","stage1_combiner_supported(op,4u"):
 assert x in p,x
assert "python tools/test_dx11_stage1_cross_channel_00704.py" in w
assert "tools/dx11_game_stage1_cross_channel_probe_00704.cpp" in w
print("PASS 00704 Stage1 RGB COLOROP-only D3D9->HLSL->Draw/DrawIndexed alpha/fallback boundaries")
