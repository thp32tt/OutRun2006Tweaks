#!/usr/bin/env python3
"""Real SM3 source->Z table fog->D3D11 PS RGB/fallback regression (not a game observation)."""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
header = (root / "src/vr/d3d11/live_game_sm3_table_fog.hpp").read_text()
source = bridge.partition("bool submit_live_sm3_game_draw(")[2].partition(
    "// Reuse geometric growth buffers")[0]

def require(condition, why):
    if not condition:
        raise SystemExit("DX11 SM3 table Z-fog FAIL: " + why)

for token in (
    "D3DRS_FOGENABLE", "D3DRS_FOGTABLEMODE",
    "D3DRS_FOGVERTEXMODE", "D3DRS_RANGEFOGENABLE",
    "D3DRS_FOGCOLOR", "D3DRS_FOGSTART", "D3DRS_FOGEND",
    "D3DRS_FOGDENSITY", "D3DPRASTERCAPS_ZFOG",
    "D3DPRASTERCAPS_WFOG", "native_sm3_table_zfog_admission(",
    "tableZFog.enabled", "pipeline.tableZFogConstants",
    "context->PSSetConstantBuffers(4u, 1u, &fogBuffer)",
    "context->DrawIndexed(", "context->Draw(",
):
    require(token in source or token in bridge, "missing real GPU table fog path: " + token)
require(source.index("native_sm3_table_zfog_admission(") <
        source.index("compile_native_live_sm3_program(") <
        source.index("context->PSSetConstantBuffers(4u, 1u, &fogBuffer)") <
        source.index("context->DrawIndexed("), "query, compile, GPU binding, draw order")
for token in ("append_native_sm3_table_zfog(pixelHlsl, tableZFog)",
              "append_native_sm3_alpha_test(pixelHlsl, alphaCompare)"):
    require(token in backend, "native HLSL compile stage disconnected: " + token)
for token in ("LIVE_SM3_FOG_REJECT", "liveSm3FogRejectReasons",
              "NativeSm3FogReject::SourceQuery",
              "D3DRS_RANGEFOGENABLE", "sourceOrdinal"):
    require(token in source or token in bridge,
            "real game fog rejection telemetry/fallback missing: " + token)
for token in ("r283_color.rgb = lerp(", "r283_fogPosition : SV_Position",
              "r283_fogControls.w == 1.0f", "r283_fogControls.w == 2.0f",
              "float4 r283_fogColor;", "register(b4)"):
    require(token in header, "actual native GPU fog missing: " + token)
compiler = shutil.which("g++") or shutil.which("clang++")
if compiler:
    with tempfile.TemporaryDirectory() as folder:
        result = Path(folder) / "fog"
        subprocess.run([compiler, "-std=c++17", "-I", str(root / "src/vr/d3d11"),
                        str(root / "tools/dx11_live_sm3_table_zfog_01005.cpp"),
                        "-o", str(result)], check=True)
        subprocess.run([str(result)], check=True)
print("DX11 SM3 real GPU Z-fog admission/binding/fallback PASS (runtime UNTESTED)")
