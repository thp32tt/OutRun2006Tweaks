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
# FVF active fog remains rejected in production. The only alternative
# requires real D3D9 source getters + explicit RAW opt-in + bounded floats,
# then poisons complete-frame publication after the authentic native Draw.
for token in ("native_game_inert_fog_modes(sourceTableFog, sourceVertexFog)",
              "D3DRS_FOGTABLEMODE", "D3DRS_FOGVERTEXMODE",
              "sourceKnown = env_raw_visual_opt_in() && fog == TRUE &&",
              "native_raw_fvf_fog_visual_admission(",
              "if (!output.rawFogVisualMismatch) return false;",
              "if (output.rawFogVisualMismatch && s.issued > issuedBeforeFvf)",
              "s.frameBatch.abort();"):
    require(token in bridge, "fixed-function live D3D9 fog fallback missing: " + token)
require("if (rawFogOmitted) liveBatch.abort();" in source,
        "SM3 incomplete RAW Fog Draw cannot certify a full native game frame")
require("native_game_inert_fog_modes(tableMode, vertexMode)" in header,
        "shared programmable and FVF source equation classification absent")
for token in ("LIVE_SM3_FOG_REJECT", "liveSm3FogRejectReasons",
              "NativeSm3FogReject::SourceQuery",
              "D3DRS_RANGEFOGENABLE", "sourceOrdinal"):
    require(token in source or token in bridge,
            "real game fog rejection telemetry/fallback missing: " + token)
for token in ("r283_color.rgb = lerp(", "r283_fogPosition : SV_Position",
              "r283_fogControls.w == 1.0f", "r283_fogControls.w == 2.0f",
              "float4 r283_fogColor;", "register(b4)"):
    require(token in header, "actual native GPU fog missing: " + token)
# Positive and destructive source regression for genuine per-Draw COM query
# ordering. A mode-query failure must not be promoted as NONE/NONE; active
# table/vertex fog still requires its complete original payload and caps.
fog_gate = source.partition("const bool modesKnown =")[2].partition(
    "// The native rasterizer always performs homogeneous clipping.")[0]
require(bool(fog_gate), "missing live mode-first fog gate")
require("readFog(D3DRS_FOGTABLEMODE, tableMode, 1u)" in fog_gate and
        "readFog(D3DRS_FOGVERTEXMODE, vertexMode, 2u)" in fog_gate,
        "both authentic D3D9 mode getters required")
require("native_sm3_fog_needs_parameters(true, tableMode, vertexMode)" in fog_gate and
        "const bool parametersKnown = !activeEquation ||" in fog_gate and
        "if (!modesKnown || !parametersKnown)" in fog_gate and
        "if (activeEquation) {" in fog_gate,
        "inactive query skip / active fog fail-closed linkage missing")
require(fog_gate.index("native_sm3_fog_needs_parameters(") <
        fog_gate.index("readFog(D3DRS_RANGEFOGENABLE") <
        fog_gate.index("native_sm3_table_zfog_admission("),
        "mode, conditional payload, native GPU shader order broken")
for wrong, correct in (
    ("!modesKnown || !parametersKnown", "if (!modesKnown || !parametersKnown)"),
    ("!activeEquation ||", "const bool parametersKnown = !activeEquation ||"),
    ("if (activeEquation) {", "if (activeEquation) {"),
):
    mutant = fog_gate.replace(wrong, "false /* destructive unsafe mutation */", 1)
    require(mutant != fog_gate and not all(t in mutant for t in (
        "if (!modesKnown || !parametersKnown)",
        "const bool parametersKnown = !activeEquation ||",
        "if (activeEquation) {")),
        "destructive source mutation slipped through admission contract")
compiler = shutil.which("g++") or shutil.which("clang++")
if compiler:
    with tempfile.TemporaryDirectory() as folder:
        result = Path(folder) / "fog"
        subprocess.run([compiler, "-std=c++17", "-I", str(root / "src/vr/d3d11"),
                        str(root / "tools/dx11_live_sm3_table_zfog_01005.cpp"),
                        "-o", str(result)], check=True)
        subprocess.run([str(result)], check=True)
print("DX11 SM3 real GPU Z-fog admission/binding/fallback PASS (runtime UNTESTED)")
