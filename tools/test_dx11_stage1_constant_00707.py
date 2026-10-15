#!/usr/bin/env python3
"""00707: D3D9 Stage1 CONSTANT -> native shader/Draw plus input-safe fallback."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
h=(r/"src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
b=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
p=(r/"tools/dx11_game_stage1_constant_probe_00707.cpp").read_text()
w=(r/".github/workflows/dx11-fast-structural.yml").read_text()
def integrated(h,b):
 game=b.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
 shader=b.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
 submit=b.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
 return (all(x in h for x in ("kStage1Constant = 6u","source == kStage1Constant",
  "stage1_operation_reads_constant","stage1_three_source_reads_constant")) and
  "kStage1Constant == D3DTA_CONSTANT" in b and
  all(x in game for x in ("stage1_operation_reads_constant(nextColorOp,color1,color2)",
   "stage1_operation_reads_constant(alphaOp,alpha1,alpha2)",
   "stage1_three_source_reads_constant(nextColorOp,color0,color1,color2)",
   "stage1_three_source_reads_constant(alphaOp,alpha0,alpha1,alpha2)",
   "needsStageConstant &&","GetTextureStageState(1,D3DTSS_CONSTANT,&stageConstant)",
   "capture.stage1Constant = {","(stageConstant >> 24) & 255u")) and
  all(x in shader for x in ("float4 stage1Constant;","if ((source & 15) == 6) value = stage1Constant;",
   "if ((source & 32) != 0) value = value.aaaa;",
   "if ((source & 16) != 0) value = 1.0f - value;",
   "Stage1ThreeSource(stage0, diffuse, specular, stage1Ops.y,")) and
  all(x in b for x in ("float stageConstant[4];",
   "static_assert(sizeof(Stage1Upload) == 80u &&",
   "constants.ByteWidth = sizeof(Stage1Upload);")) and
  all(x in submit for x in ("ctx->UpdateSubresource(s.stage1Constants.Get(), 0u, nullptr,",
   "payload.stageConstant);","ctx->PSSetConstantBuffers(1, 1, &combiner)",
   "ctx->DrawIndexed(indexCount, 0, 0);","ctx->Draw(static_cast<UINT>(vertices.size()), 0);")))
assert integrated(h,b)
for t in ("needsStageConstant &&","GetTextureStageState(1,D3DTSS_CONSTANT,&stageConstant)",
 "capture.stage1Constant = {","float4 stage1Constant;",
 "if ((source & 15) == 6) value = stage1Constant;","payload.stageConstant);",
 "ctx->PSSetConstantBuffers(1, 1, &combiner)",
 "float stageConstant[4];",
 "static_assert(sizeof(Stage1Upload) == 80u &&",
 "constants.ByteWidth = sizeof(Stage1Upload);",
 "ctx->UpdateSubresource(s.stage1Constants.Get(), 0u, nullptr,"):
 assert not integrated(h,b.replace(t,"",1)),t
assert "pairs!=400u" in p and "triadic!=16000u" in p
assert "python tools/test_dx11_stage1_constant_00707.py" in w
assert "tools/dx11_game_stage1_constant_probe_00707.cpp" in w
print("PASS 00707 integrated Stage1 CONSTANT RGB/alpha and safe native fallback")
