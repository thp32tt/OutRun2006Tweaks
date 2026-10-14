#!/usr/bin/env python3
"""Native game FVF SPECULAR source must flow D3D9 bytes -> VS COLOR1 -> Stage1 PS."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
h=(r/"src/vr/d3d11/live_game_stage1_factor.hpp").read_text()
f=(r/"src/vr/d3d11/live_game_fvf_layout.hpp").read_text()
b=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
p=(r/"tools/dx11_game_stage1_specular_probe_00706.cpp").read_text()
w=(r/".github/workflows/dx11-fast-structural.yml").read_text()
cap=b.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
translate=b.split("bool translate_vertices(",1)[1].split("bool mirror_texture(",1)[0]
shader=b.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
base=b.split('constexpr char kShader[] = R"(',1)[1].split(')";',1)[0]
def integrated(layout,header,bridge,producer,decoder,vs,ps):
    return (all(s in layout for s in (
        "std::uint32_t specular = 0u;",
        "if (layout.hasSpecular)",
        "std::memcpy(&candidate.specular",
        "(layout.hasDiffuse ? 4u : 0u), 4u);")) and
      all(s in header for s in (
        "kStage1Specular = 4u",
        "stage1_operation_reads_specular",
        "stage1_three_source_reads_specular",
        "source == kStage1Specular")) and
      all(s in bridge for s in (
        "kStage1Specular == D3DTA_SPECULAR",
        "float specular[4];",
        "DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 40",
        "CreateInputLayout(elements, 4",
        "static_assert(sizeof(NativeVertex) == 56u")) and
      all(s in producer for s in (
        "!layout.hasSpecular",
        "stage1_operation_reads_specular(nextColorOp, color1, color2)",
        "stage1_operation_reads_specular(alphaOp, alpha1, alpha2)",
        "stage1_three_source_reads_specular(nextColorOp, color0, color1, color2)",
        "stage1_three_source_reads_specular(alphaOp, alpha0, alpha1, alpha2)")) and
      all(s in decoder for s in ("const DWORD specular = decoded.specular;",
        "v.specular[0] =", "v.specular[3] =")) and
      all(s in vs for s in ("float4 specular : COLOR1",
                           "o.specular = v.specular;")) and
      all(s in ps for s in ("value = specular;",
          "Stage1Source(stage0, diffuse, specular, arg0)",
          "Stage1AndAlpha(float4 stage0, float4 diffuse, float4 specular,",
          "Stage1AndAlpha(v.diffuse, v.diffuse, v.specular, 0.0f)",
          "Stage1ThreeSource(stage0, diffuse, specular, stage1Ops")) and
      "ctx->DrawIndexed(indexCount, 0, 0);" in bridge and
      "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in bridge and
      "before_game_present(" in bridge)
assert integrated(f,h,b,cap,translate,base,shader)
for target in ("!layout.hasSpecular","stage1_operation_reads_specular(alphaOp, alpha1, alpha2)",
               "stage1_three_source_reads_specular(nextColorOp, color0, color1, color2)"):
    assert not integrated(f,h,b,cap.replace(target,"",1),translate,base,shader),target
assert not integrated(f,h,b,cap,translate.replace("v.specular[3] =","",1),base,shader)
for target in ("value = specular;","Stage1AndAlpha(v.diffuse, v.diffuse, v.specular, 0.0f)"):
    assert not integrated(f,h,b,cap,translate,base,shader.replace(target,"",1))
assert "rgbAlpha!=256u" in p and "triadic!=4096u" in p
assert "python tools/test_dx11_stage1_specular_00706.py" in w
assert "tools/dx11_game_stage1_specular_probe_00706.cpp" in w
print("PASS 00706 game FVF SPECULAR/COLOR1 native Draw/DrawIndexed and safe fallback structural mutations")
