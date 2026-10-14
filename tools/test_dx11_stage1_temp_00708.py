#!/usr/bin/env python3
"""00708 live Stage0 TEMP -> Stage1 CURRENT/TEMP RGB/alpha and native draw."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
b=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
w=(root/".github/workflows/dx11-fast-structural.yml").read_text()
p=(root/"tools/dx11_game_stage1_temp_probe_00708.cpp").read_text()
def connected(header,bridge):
    capture=bridge.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    shader=bridge.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
    submit=bridge.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
    return all(x in header for x in ("kStage1Temp = 5u","stage1_operand_supported_with_temp",
        "stage1_combiner_supported_with_temp","stage1_alpha_supported_with_temp",
        "stage1_three_source_supported_with_temp","!stage1_operand_supported(kStage1Temp)")) and all(
        x in capture for x in ("resultArg == D3DTA_TEMP && nextColorOp != D3DTOP_DISABLE && layout.hasDiffuse",
        "stage0WritesTemp && !capture.enabled","stage1_three_source_supported_with_temp(nextColorOp",
        "stage1_combiner_supported_with_temp(nextColorOp","stage1_three_source_supported_with_temp(alphaOp",
        "stage1_alpha_supported_with_temp(alphaOp","stage1Result != D3DTA_CURRENT",
        "capture.stage0ResultTemp = stage0WritesTemp;")) and all(
        x in shader for x in ("if ((source & 15) == 1 && stage1Ops.z != 0) value = diffuse;",
        "if ((source & 15) == 5) value = current;","if (stage1Ops.z != 0) return diffuse.a;",
        "(stage1Ops.z != 0 ? diffuse.a : stage0.a)")) and all(
        x in submit for x in ("payload.operations[2] = capture.stage0ResultTemp ? 1 : 0;",
        "ctx->PSSetConstantBuffers(1, 1, &combiner)",
        "ctx->DrawIndexed(indexCount, 0, 0);","ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
assert connected(h,b)
for token in ("stage0WritesTemp && !capture.enabled",
    "stage1_three_source_supported_with_temp(nextColorOp",
    "stage1_alpha_supported_with_temp(alphaOp",
    "capture.stage0ResultTemp = stage0WritesTemp;",
    "if ((source & 15) == 5) value = current;",
    "if (stage1Ops.z != 0) return diffuse.a;",
    "payload.operations[2] = capture.stage0ResultTemp ? 1 : 0;",
    "ctx->DrawIndexed(indexCount, 0, 0);"):
    assert not connected(h,b.replace(token,"",1)),token
assert "stage1_three_source_supported_with_temp" in p
assert "python tools/test_dx11_stage1_temp_00708.py" in w
assert "tools/dx11_game_stage1_temp_probe_00708.cpp" in w
print("PASS 00708 native Stage0 TEMP producer, Stage1 RGBA, and safe fallback")
