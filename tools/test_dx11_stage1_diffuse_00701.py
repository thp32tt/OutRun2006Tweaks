#!/usr/bin/env python3
"""00701: stage-1 DIFFUSE RGB and alpha in real captured D3D9 -> native Draw."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
probe = (root / "tools/dx11_game_stage1_factor_probe.cpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(src):
    producer = src.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
    consumer = src.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
    shader = src.split('constexpr char kStage1FactorShader[] = R"(', 1)[1].split(')";', 1)[0]
    return all((
        "if ((source & 15) == 0) value = diffuse;" in shader,
        "float4 Stage1AndAlpha(float4 stage0, float4 diffuse, float4 specular," in shader,
        all(shader.count(
            "Stage1Source(stage0, diffuse, specular, stage1Args." + ch + ")") == 2
            for ch in "xyzw"),
        all("return Stage1AndAlpha(" in shader and
            "v.diffuse, v.specular," in line for line in shader.splitlines()
            if "return Stage1AndAlpha(" in line),
        shader.count("return Stage1AndAlpha(") == 4,
        "stage1_operation_reads_diffuse(nextColorOp, color1, color2)" in producer,
        "stage1_operation_reads_diffuse(alphaOp, alpha1, alpha2)" in producer,
        "(!layout.hasDiffuse &&\n             (stage1_operation_reads_diffuse" in producer,
        "stage1_combiner_supported(nextColorOp, color1, color2)" in producer,
        "stage1_alpha_supported(alphaOp, alpha1, alpha2)" in producer,
        "capture.stage1Args = {color1, color2, alpha1, alpha2};" in producer,
        "stage1Result != D3DTA_CURRENT || stage2Op != D3DTOP_DISABLE" in producer,
        "ctx->PSSetConstantBuffers(1, 1, &combiner)" in consumer,
        "ctx->DrawIndexed(indexCount, 0, 0);" in consumer,
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in consumer,
        "before_game_present(" in src,
    ))

assert integrated(source), "stage1 DIFFUSE must reach native RGB/alpha Draw and fallback"
for snippet in (
    "constexpr std::uint32_t kStage1Diffuse = 0u;",
    "source == kStage1Diffuse", "stage1_operation_reads_diffuse(",
    "if (operation == kStage1Disable) return false;",
    "if (operation == kStage1SelectArg1)",
    "if (operation == kStage1SelectArg2)",
    "static_assert(!stage1_operation_reads_diffuse(kStage1SelectArg1",
):
    assert snippet in header, snippet
for snippet in ("kStage1Diffuse | flags", "stage1_combiner_supported(op, d, kStage1Factor)",
                "stage1_alpha_supported(op, kStage1Factor, d)",
                "stage1_operation_reads_diffuse(kStage1Disable"):
    assert snippet in probe, snippet
assert "python tools/test_dx11_stage1_diffuse_00701.py" in workflow
# Mutation checks cover the live state read, shader source differentiation, PS
# RGB and alpha operands, and BOTH native draw paths, not an inert helper.
for snippet in (
    "if ((source & 15) == 0) value = diffuse;",
    "Stage1Source(stage0, diffuse, specular, stage1Args.x)",
    "Stage1Source(stage0, diffuse, specular, stage1Args.w)",
    "stage1_operation_reads_diffuse(nextColorOp, color1, color2)",
    "stage1_operation_reads_diffuse(alphaOp, alpha1, alpha2)",
    "(!layout.hasDiffuse &&\n             (stage1_operation_reads_diffuse",
    "ctx->PSSetConstantBuffers(1, 1, &combiner)",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
):
    assert not integrated(source.replace(snippet, "", 1)), snippet
print("PASS 00701: D3D9 vertex DIFFUSE stage1 RGB/alpha -> native Draw/DrawIndexed; missing diffuse falls back")
