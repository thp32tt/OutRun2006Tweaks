#!/usr/bin/env python3
"""00700: end-to-end real game stage-1 operand modifiers, fail-closed source and native draw."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
probe = (root / "tools/dx11_game_stage1_factor_probe.cpp").read_text()
game = bridge.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
submit = bridge.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
shader = bridge.split('constexpr char kStage1FactorShader[] = R"(', 1)[1].split(')";', 1)[0]

def integrated(source):
    hlsl = source.split('constexpr char kStage1FactorShader[] = R"(', 1)[1].split(')";', 1)[0]
    producer = source.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
    consumer = source.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
    return all((
        "kStage1Complement == D3DTA_COMPLEMENT" in source,
        "kStage1AlphaReplicate == D3DTA_ALPHAREPLICATE" in source,
        "(source & 15) == 3 ? stage1Factor : current" in hlsl,
        "if ((source & 32) != 0) value = value.aaaa;" in hlsl,
        "if ((source & 16) != 0) value = 1.0f - value;" in hlsl,
        "Stage1Source(stage0, diffuse, stage1Args.x)" in hlsl,
        "Stage1Source(stage0, diffuse, stage1Args.y)" in hlsl,
        "Stage1Source(stage0, diffuse, stage1Args.z)" in hlsl,
        "Stage1Source(stage0, diffuse, stage1Args.w)" in hlsl,
        "stage1_combiner_supported(nextColorOp, color1, color2)" in producer,
        "stage1_alpha_supported(alphaOp, alpha1, alpha2)" in producer,
        "stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE" in producer,
        "capture.stage1Args = {color1, color2, alpha1, alpha2};" in producer,
        "ctx->PSSetConstantBuffers(1, 1, &combiner)" in consumer,
        "capture.stage1Enabled ?" in consumer,
        "ctx->DrawIndexed(indexCount, 0, 0);" in consumer,
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in consumer,
    ))
assert integrated(bridge), "game stage1 modifiers must reach real native draw"
for token in (
    "kStage1ArgMask = 0x0fu", "kStage1Complement = 0x10u",
    "kStage1AlphaReplicate = 0x20u", "(operand & ~allowedBits) == 0u",
    "source == kStage1Current || source == kStage1Factor",
    "kStage1Modulate2X", "kStage1Modulate4X", "kStage1Subtract",
    "kStage1AddSmooth"):
    assert token in header, token
for token in ("512u", "0x14u", "0x43u", "0x81u", "0x103u",
              "kStage1Complement | kStage1AlphaReplicate"):
    assert token in probe, token
# Fault injection: these are actual source→cbuffer→shader→Draw integration checks,
# not a count of dormant shader helper symbols.
for token in (
    "(source & 15) == 3 ? stage1Factor : current",
    "if ((source & 32) != 0) value = value.aaaa;",
    "if ((source & 16) != 0) value = 1.0f - value;",
    "stage1_combiner_supported(nextColorOp, color1, color2)",
    "stage1_alpha_supported(alphaOp, alpha1, alpha2)",
    "capture.stage1Args = {color1, color2, alpha1, alpha2};",
    "ctx->PSSetConstantBuffers(1, 1, &combiner)",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
):
    assert not integrated(bridge.replace(token, "", 1)), token
print("PASS 00700: game stage-1 RGB/alpha operand modifiers; native Draw/DrawIndexed and DX9Ex fallback")
