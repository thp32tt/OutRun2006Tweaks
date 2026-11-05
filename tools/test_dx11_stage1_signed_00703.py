#!/usr/bin/env python3
"""00703 signed-add menu/vehicle/race stage1 RGB + independent alpha native Draw integration."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
legacy = (root / "tools/dx11_game_stage1_factor_probe.cpp").read_text()
probe = (root / "tools/dx11_game_stage1_signed_probe_00703.cpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(s, h):
    shader = s.split('constexpr char kStage1FactorShader[] = R"(', 1)[1].split(')";', 1)[0]
    producer = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
    submit = s.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
    return all((
        "kStage1AddSigned == D3DTOP_ADDSIGNED" in s,
        "kStage1AddSigned2X == D3DTOP_ADDSIGNED2X" in s,
        "operation == kStage1AddSigned || operation == kStage1AddSigned2X" in h,
        "if (op == 8) return saturate(a + b - 0.5f);" in shader,
        "if (op == 9) return saturate(2.0f * (a + b - 0.5f));" in shader,
        "stage1Ops.x, stage0, diffuse);" in shader,
        "stage1Ops.y, stage0, diffuse).a;" in shader,
        "stage1_combiner_supported(nextColorOp, color1, color2)" in producer,
        "stage1_alpha_supported(alphaOp, alpha1, alpha2)" in producer,
        "stage1_operation_reads_diffuse(nextColorOp, color1, color2)" in producer,
        "stage1_operation_reads_diffuse(alphaOp, alpha1, alpha2)" in producer,
        "capture.stage1ColorOp = nextColorOp;" in producer,
        "capture.stage1AlphaOp = alphaOp;" in producer,
        "capture.stage1Args = {color1, color2, alpha1, alpha2};" in producer,
        "ctx->PSSetConstantBuffers(1, 1, &combiner)" in submit,
        "ctx->DrawIndexed(indexCount, 0, 0);" in submit,
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in submit,
        "before_game_present(" in s,
    ))

assert integrated(bridge, header), "signed stage1 must integrate live D3D9 -> RGB/alpha HLSL -> native Draw"
for token in ("kStage1AddSigned, kStage1AddSigned2X", "variants == 288u",
              "stage1_operation_reads_diffuse", "0x40u", "kStage1Disable",
              "signed_add(op, 0.3f, 0.4f)"):
    assert token in probe, token
assert "for (std::uint32_t bad : {0u, 1u, 13u, 15u, 17u, 255u})" in legacy
assert "python tools/test_dx11_stage1_signed_00703.py" in workflow
assert "g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic tools/dx11_game_stage1_signed_probe_00703.cpp" in workflow
for token in (
    "kStage1AddSigned == D3DTOP_ADDSIGNED",
    "kStage1AddSigned2X == D3DTOP_ADDSIGNED2X",
    "if (op == 8) return saturate(a + b - 0.5f);",
    "if (op == 9) return saturate(2.0f * (a + b - 0.5f));",
    "stage1Ops.x, stage0, diffuse);", "stage1Ops.y, stage0, diffuse).a;",
    "stage1_combiner_supported(nextColorOp, color1, color2)",
    "stage1_alpha_supported(alphaOp, alpha1, alpha2)",
    "capture.stage1Args = {color1, color2, alpha1, alpha2};",
    "ctx->PSSetConstantBuffers(1, 1, &combiner)",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
):
    assert not integrated(bridge.replace(token, "", 1), header), token
assert not integrated(bridge, header.replace("operation == kStage1AddSigned || operation == kStage1AddSigned2X", "", 1))
print("PASS 00703: D3D9 stage1 signed add/2X RGB+alpha native game Draw; fail-closed input and GPU fallback")
