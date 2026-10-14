#!/usr/bin/env python3
"""00705: triadic game-authored D3D9 stage1 -> D3D11 HLSL -> Draw integration."""
from pathlib import Path
r = Path(__file__).resolve().parents[1]
h = (r/"src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
b = (r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
p = (r/"tools/dx11_game_stage1_triop_probe_00705.cpp").read_text()
w = (r/".github/workflows/dx11-fast-structural.yml").read_text()
sdk = ("kStage1MultiplyAdd == D3DTOP_MULTIPLYADD",
       "kStage1Lerp == D3DTOP_LERP")
cap = b.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
shader = b.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
submit = b.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
checks = (
    "D3DTSS_COLORARG0, &color0", "D3DTSS_ALPHAARG0, &alpha0",
    "stage1_three_source_supported(nextColorOp, color0, color1, color2)",
    "stage1_three_source_supported(alphaOp, alpha0, alpha1, alpha2)",
    "stage1_three_source_reads_diffuse(nextColorOp, color0, color1, color2)",
    "stage1_three_source_reads_diffuse(alphaOp, alpha0, alpha1, alpha2)",
    "capture.stage1ArgZero = {color0, alpha0};",
)
hlsl = ("int4 stage1ArgZero;", "Stage1Source(stage0, diffuse, specular, arg0)",
        "if (op == 25) return saturate(a1 + a2 * a0);",
        "return saturate(lerp(a2, a1, a0));",
        "stage1ArgZero.x, stage1Args.x, stage1Args.y",
        "stage1ArgZero.y, stage1Args.z, stage1Args.w",
        "AlphaGate(result.a);")
uploads = ("static_assert(sizeof(Stage1Upload) == 80u);",
           "payload.argZero[i] = static_cast<std::int32_t>(capture.stage1ArgZero[i]);",
           "float stageConstant[4];", // The triadic arg0 offsets remain intact after new RGBA CB field.
           "payload.stageConstant);",
           "ctx->PSSetConstantBuffers(1, 1, &combiner)",
           "ctx->DrawIndexed(indexCount, 0, 0);",
           "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")
def valid(header,bridge,capture,ps,submission):
    return (all(s in bridge for s in sdk) and
            all(s in capture for s in checks) and
            all(s in ps for s in hlsl) and
            all(s in submission for s in uploads) and
            "stage1_operand_supported(arg0)" in header and
            "!stage1_combiner_supported" in header and
            "before_game_present(" in bridge)
assert valid(h,b,cap,shader,submit)
for item in checks:
    assert not valid(h,b,cap.replace(item,"",1),shader,submit),item
for item in hlsl:
    assert not valid(h,b,cap,shader.replace(item,"",1),submit),item
assert not valid(h.replace("stage1_operand_supported(arg0)","true",1),b,cap,shader,submit)
for item in ("cases!=3456u","stage1_three_source_reads_diffuse",
             "stage1_combiner_supported(op,b,c)","stage1_alpha_supported(op,b,c)",
             "stage1_three_source_supported(24u","near(ref(25u","near(ref(26u"):
    assert item in p,item
assert "python tools/test_dx11_stage1_triop_00705.py" in w
assert "tools/dx11_game_stage1_triop_probe_00705.cpp" in w
print("PASS 00705 three-input Stage1 D3D9/CB/HLSL/Draw RGB+alpha fail-closed contract")
