#!/usr/bin/env python3
"""00673: live stage1 CURRENT/TFACTOR colors, alpha, fallback and native Draw."""
from pathlib import Path
p = Path(__file__).resolve().parents[1]
src = (p / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (p / "src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
producer = src.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
consumer = src.split("bool submit(", 1)[1].split("void observe(", 1)[0]
shader = src.split("constexpr char kStage1FactorShader[] = R\"(", 1)[1].split(')\";', 1)[0]
def integrated(source):
    return all(x in source for x in (
        "GetTextureStageState(1, D3DTSS_COLOROP, &nextColorOp)",
        "stage1_combiner_supported(nextColorOp, color1, color2)",
        "stage1_alpha_supported(alphaOp, alpha1, alpha2)",
        "!stage1_alpha_supported(alphaOp, alpha1, alpha2)",
        "stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE",
        "capture.stage1Enabled = true;",
        "capture.stage1Factor = {",
        "capture.stage0FullModulate =",
        "!capture.stage0FullModulate &&",
        "stage1FactorShader" if False else "kStage1FactorShader",
        'compile("PSStage1Modulate", "ps_4_0", stage1ModulateCode)',
        'static const std::string stage1ShaderSource = shaderSource + kStage1FactorShader;',
        'D3DCompile(stage1ShaderSource.data(), stage1ShaderSource.size(),'
        "s.stage1DiffusePs.GetAddressOf()",
        "s.stage1AddPs.GetAddressOf()",
        "ctx->PSSetConstantBuffers(1, 1, &combiner)",
        "capture.stage1Enabled ?",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    ))
assert integrated(src)
# Both the pipeline-rebuild and full-reset paths must release stage-1 PS owners.
for name in ("stage1DiffusePs", "stage1ModulatePs", "stage1TextureOnlyPs", "stage1AddPs"):
    assert src.count("s." + name + ".Reset();") == 2, name
assert len(shader) < 16380
for label, snippet in (
    ("1st stage read", "GetTextureStageState(1, D3DTSS_COLOROP, &nextColorOp)"),
    ("stage 2 disable", "stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE"),
    ("no unsupported stage0", "!capture.stage0FullModulate &&"),
    ("alpha source", "!stage1_alpha_supported(alphaOp, alpha1, alpha2)"),
    ("independent stage1 PS", "capture.stage1Enabled ?"),
    ("constant bound", "ctx->PSSetConstantBuffers(1, 1, &combiner)"),
    ("indexed GPU draw", "ctx->DrawIndexed(indexCount, 0, 0);"),
    ("linear GPU draw", "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"),
):
    assert not integrated(src.replace(snippet, "", 1)), label
assert all(x in header for x in ("kStage1Modulate2X", "kStage1Modulate4X",
    "kStage1AddSmooth", "stage1_operand_supported(arg1)",
    "stage1_operand_supported(arg2)"))
assert all(x in shader for x in (
    "stage1Ops.x", "stage1Ops.y == 1", "Stage1Source(stage0, stage1Args.x)",
    "Stage1Source(stage0, stage1Args.w)", "AlphaGate(result.a);",
    "float4 PSStage1Diffuse", "float4 PSStage1Modulate",
    "float4 PSStage1TextureOnly", "float4 PSStage1Add",
    "return saturate(a - b);", "return saturate(a + b * (1.0f - a));"))
assert "capture.stage1Enabled" in producer and "capture.stage1Enabled" in consumer
print("00673 stage1 native Draw/DrawIndexed and destructive fallback/source regressions: PASS")
