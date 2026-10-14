#!/usr/bin/env python3
"""00715 native real D3D9 game UV1 -> D3D11 TEXCOORD1 shader + fallback."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root/"src/vr/d3d11/live_game_stage1_uv.hpp").read_text()
flow = (root/".github/workflows/dx11-fast-structural.yml").read_text()
capture = bridge.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
vertex = bridge.split("bool translate_vertices(",1)[1].split("bool mirror_texture(",1)[0]
shader = bridge.split('constexpr char kShader[] = R"(',1)[1].split(')";',1)[0]
stage1 = bridge.split('constexpr char kStage1FactorShader[] = R"(',1)[1].split(')";',1)[0]
ia = bridge.split("const D3D11_INPUT_ELEMENT_DESC elements[] =",1)[1].split("return false;",1)[0]
def integrated(c, v, h, ps, a):
    return all(x in c for x in (
        "stage1_game_uv_supported(uv1, layout.texcoordCount, transform1)",
        "GetTransform(D3DTS_TEXTURE1, &matrix1)",
        "capture.stage1CoordIndex = uv1;",
        "capture.stage1TransformUv = transform1 == D3DTTFF_COUNT2;",
        "capture.stage1UvTransform = matrix1",
        "samplerDiff || stage1AlternateUv",
        "tex1.As(&capture.stage1SeparateTexture)")) and all(x in v for x in (
        "game_fvf_select_uv(decoded, layout, capture.stage1CoordIndex,",
        "output[i].uvStage1[0] = u * m._11 + v * m._21 + m._31;",
        "output[i].uvStage1[1] = u * m._12 + v * m._22 + m._32;",
        "!std::isfinite(output[i].uvStage1[0])")) and all(x in h for x in (
        "float2 uvStage1 : TEXCOORD1;",
        "o.uvStage1 = v.uvStage1;",
        "float4 specular : COLOR1; float2 uvStage1 : TEXCOORD1;")) and (
        ps.count("stage1GameTexture.Sample(stage1GameSampler, v.uvStage1)") == 3
    ) and all(x in a for x in (
        '{"TEXCOORD", 1, DXGI_FORMAT_R32G32_FLOAT, 0, 56,',
        "CreateInputLayout(elements, 5,")) and "stage1_game_uv_supported(" in header
assert integrated(capture, vertex, shader, stage1, ia)
for poison in ("stage1_game_uv_supported(uv1, layout.texcoordCount, transform1)",
               "samplerDiff || stage1AlternateUv"):
    assert not integrated(capture.replace(poison,"",1),vertex,shader,stage1,ia)
for poison in ("game_fvf_select_uv(decoded, layout, capture.stage1CoordIndex,",
               "!std::isfinite(output[i].uvStage1[0])"):
    assert not integrated(capture,vertex.replace(poison,"",1),shader,stage1,ia)
assert not integrated(capture,vertex,shader,stage1.replace("v.uvStage1","v.uv"),ia)
assert not integrated(capture,vertex,shader,stage1,ia.replace("CreateInputLayout(elements, 5,","CreateInputLayout(elements, 4,"))
assert "test_dx11_stage1_uv_00715.py" in flow
assert "dx11_game_stage1_uv_probe_00715.cpp" in flow
print("PASS 00715: independent game FVF UV1/COUNT2 -> HLSL t1/s1 native Draw and DX9Ex fallback")
