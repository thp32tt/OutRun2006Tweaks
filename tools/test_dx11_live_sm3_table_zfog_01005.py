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
fvf_header = (root / "src/vr/d3d11/native_game_raw_fvf_fog_visual.hpp").read_text()
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
# Authenticated table Z/W fog may reach exact native FVF RGB; other active
# vertex/range/sRGB fog admits only source-read RAW opt-in, which poisons
# full-frame publication after the authentic native Draw.
for token in ("native_game_inert_fog_modes(sourceTableFog, sourceVertexFog)",
              "D3DRS_FOGTABLEMODE", "D3DRS_FOGVERTEXMODE",
              "sourceKnown = fog == TRUE && fogModesKnown &&",
              "native_raw_fvf_fog_visual_admission(",
              "if (!output.rawFogVisualMismatch) return false;",
              "if (output.rawFogVisualMismatch && s.issued > issuedBeforeFvf)",
              "s.frameBatch.abort();"):
    require(token in bridge, "fixed-function live D3D9 fog fallback missing: " + token)
require("native_sm3_raw_visual_fog_omission(" in source and
        "fogProjectionQueryFailed" in source and
        "fogProjectionQueryFailed ? 9u : 0u" in source and
        "if (rawFogOmitted) liveBatch.abort();" in source,
        "SM3 incomplete RAW Fog Draw cannot certify a full native game frame")
require("sourceInertExponential = native_sm3_inert_exponential_table_fog(" in bridge and
        "const bool sourceFogInactive" in bridge and
        "sourceInertExponential;" in bridge and
        "native_sm3_raw_visual_fog_omission(" in header and
        "(tableMode == 0u && vertexMode == D3DFOG_LINEAR)" in source and
        "(vertexMode == D3DFOG_EXP ||" in source,
        "source FVF inert EXP and raw vertex fog parameter transport missing")
require("native_game_inert_fog_modes(tableMode, vertexMode)" in header,
        "shared programmable and FVF source equation classification absent")
# FVF and SM3 RAW must use exactly the same source equation precedence.
# The FVF bridge reads only consumed original D3D9 DWORDs; a failed required
# getter still prevents native submission and preserves game/DX9Ex fallback.
fvf_gate = bridge.partition("const DWORD sourceFogEquation =")[2].partition(
    "output.rawFogVisualMismatch =")[0]
require(bool(fvf_gate) and
        "sourceTableFog != D3DFOG_NONE" in fvf_gate and
        "native_sm3_table_fog_requires_linear_bounds(sourceFogEquation)" in fvf_gate and
        "native_sm3_table_fog_requires_density(sourceFogEquation)" in fvf_gate and
        "GetRenderState(D3DRS_FOGSTART, &startBits)" in fvf_gate and
        "GetRenderState(D3DRS_FOGEND, &endBits)" in fvf_gate and
        "GetRenderState(D3DRS_FOGDENSITY, &densityBits)" in fvf_gate and
        "SUCCEEDED(game->GetDeviceCaps(&actualCaps))" in fvf_gate,
        "FVF RAW real-source equation-specific COM reads not wired")
require("native_sm3_raw_visual_fog_omission(" in fvf_header and
        '#include "live_game_sm3_table_fog.hpp"' in fvf_header and
        "rangeFog != 1u" in fvf_header,
        "FVF/SM3 shared active table fog semantics or range safety missing")
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
        "const bool densityKnown = !densityProbe ||" in fog_gate and
        "native_sm3_inert_exponential_table_fog(" in fog_gate and
        "!inertExponential;" in fog_gate and
        "const bool parametersKnown = densityKnown && (!activeEquation ||" in fog_gate and
        "if (!modesKnown || !parametersKnown)" in fog_gate and
        "if (activeEquation) {" in fog_gate,
        "density-first inert query skip / active fog fail-closed linkage missing")
require(fog_gate.index("readFog(D3DRS_FOGVERTEXMODE, vertexMode, 2u)") <
        fog_gate.index("const bool densityProbe") <
        fog_gate.index("const bool densityKnown") <
        fog_gate.index("native_sm3_fog_needs_parameters(") <
        fog_gate.index("readFog(D3DRS_RANGEFOGENABLE") <
        fog_gate.index("native_sm3_table_zfog_admission("),
        "source mode, authentic density, conditional payload, native shader order broken")
for wrong, correct in (
    ("!modesKnown || !parametersKnown", "if (!modesKnown || !parametersKnown)"),
    ("!activeEquation ||", "const bool parametersKnown = densityKnown && (!activeEquation ||"),
    ("if (activeEquation) {", "if (activeEquation) {"),
):
    mutant = fog_gate.replace(wrong, "false /* destructive unsafe mutation */", 1)
    require(mutant != fog_gate and not all(t in mutant for t in (
        "if (!modesKnown || !parametersKnown)",
        "const bool parametersKnown = densityKnown && (!activeEquation ||",
        "if (activeEquation) {")),
        "destructive source mutation slipped through admission contract")
require("native_sm3_inert_exponential_table_fog(" in header and
        "std::isfinite(density) && density == 0.0f" in header and
        "if (native_sm3_inert_exponential_table_fog(" in header and
        "if (srgbOutput)" in header,
        "exact zero-density no-op must precede active source fog safety")
# FVF table fog must reach native GPU RGB and an authentic per-Draw b2,
# not merely an admission helper or repeated prior SM3 PASS.
for token in ("PSFvfTableFogDiffuse", "PSFvfTableFogModulate",
              "PSFvfTableFogTextureOnly", "FvfApplyTableFog",
              "rcp(v.clip.w)", "color.rgb = lerp(",
              "ctx->PSSetConstantBuffers(2u, 1u, &fvfFogBuffer)",
              "ctx->PSSetShader(fixedPixelShader",
              "native_sm3_projection_fog_depth(",
              "native_sm3_table_zfog_admission(",
              "output.nativeTableFog.enabled",
              "sourceTableFog != D3DFOG_NONE",
              "if (!output.rawFogVisualMismatch) return false;",
              "s.fvfFogConstants.Reset()"):
    require(token in bridge,
            "FVF native table fog game-state, GPU PS, or fallback missing: " + token)
require(bridge.index("ctx->PSSetConstantBuffers(2u, 1u, &fvfFogBuffer)") <
        bridge.index("ctx->PSSetShader(fixedPixelShader, nullptr, 0u)") <
        bridge.index("if (ib) ctx->DrawIndexed(indexCount, 0, 0);"),
        "FVF native table fog was bound after GPU submission")
# The actual real-game PS dispatch expression is a deeply nested conditional.
# A single lost parenthesis here produced a C2059 on the Windows source lane,
# even when standalone Linux fog tests passed. Protect the complete expression.
from re import sub as _fog_re_sub
fixed_ps_start = bridge.index("ID3D11PixelShader* fixedPixelShader = (")
fixed_ps_end = bridge.index("// Three established common FVF shaders", fixed_ps_start)
fixed_ps_expression = bridge[fixed_ps_start:fixed_ps_end]
require(fixed_ps_expression.count("(") == fixed_ps_expression.count(")") and
        "capture.stage1Enabled ?" in fixed_ps_expression and
        "s.sampledPs.Get()" in fixed_ps_expression,
        "native game FVF PS selection unbalanced or stage-1 fallback missing")
mutated_ps = fixed_ps_expression.replace("s.sampledPs.Get()))", "s.sampledPs.Get())", 1)
require(mutated_ps != fixed_ps_expression and
        mutated_ps.count("(") != mutated_ps.count(")"),
        "destructive fixed-game PS source syntax mutation escaped C2059 guard")
# Every *already supported* stage-0/1 shader must preserve its source
# alpha/discard and apply exact native Fog on final RGB. No unknown shader
# pointers or JIT failures may become an admitted native GPU Draw.
selected_fog = bridge.partition("if (output.nativeTableFog.enabled) {")[2].partition(
    "ctx->PSSetShader(fixedPixelShader, nullptr, 0u);")[0]
for token in ("s.fvfFogDiffusePs.Get()", "s.fvfFogModulatePs.Get()",
              "s.fvfFogTextureOnlyPs.Get()",
              "game_fvf_exact_table_fog_variant(", "if (!fixedPixelShader) return false;"):
    require(token in selected_fog, "FVF exact source pixel dispatch missing: " + token)
for token in ("game_fvf_original_pixel_entry(", "s.fvfFogVariants.clear();",
              "if (!originalEntry) return nullptr;",
              "if (s.fvfFogVariants.size() >= kMaxSourceVariants)",
              "if (FAILED(device->CreatePixelShader(",
              "return nullptr;", "kStage1FactorShader + kFvfTableFogShader",
              "native_fvf_specular_wrapper(originalEntry)",
              "entry.specularAdd == specularAdd",
              "game_fvf_specular_final_variant(", "output.nativeSpecularAdd",
              "native_fvf_vertex_specular_shade_admitted(shadeMode)",
              "D3DRS_SHADEMODE"):
    require(token in bridge, "bounded native FVF fog compilation/fallback missing: " + token)

compiler = shutil.which("g++") or shutil.which("clang++")
if compiler:
    with tempfile.TemporaryDirectory() as folder:
        result = Path(folder) / "fog"
        subprocess.run([compiler, "-std=c++17", "-I", str(root / "src/vr/d3d11"),
                        str(root / "tools/dx11_live_sm3_table_zfog_01005.cpp"),
                        "-o", str(result)], check=True)
        subprocess.run([str(result)], check=True)
require("native_raw_fvf_specular_fog_visual_admission(" in bridge and
        "game_fvf_raw_visual_specular_variant(" in bridge and
        "native_fvf_raw_specular_fog_omission_wrapper(originalEntry)" in bridge and
        "entry.rawFogOmitted == rawFogOmitted" in bridge and
        "if (output.rawFogVisualMismatch && s.issued > issuedBeforeFvf)" in bridge and
        "s.frameBatch.abort();" in bridge,
        "RAW authentic FVF specular tile / full frame safety disconnected")
# Portable native C++ unit regression for dynamic HLSL entry composition.
# This is not a real D3D11 GPU or HMD observation.
if compiler:
    with tempfile.TemporaryDirectory() as folder:
        result = Path(folder) / "fvf_fog"
        subprocess.run([compiler, "-std=c++17", "-I", str(root),
                        str(root / "tests/native_game_fvf_fog_dispatch_test.cpp"),
                        "-o", str(result)], check=True)
        subprocess.run([str(result)], check=True)
if compiler:
    with tempfile.TemporaryDirectory() as folder:
        result = Path(folder) / "raw_fvf_fog"
        subprocess.run([compiler, "-std=c++17", "-I", str(root),
                        str(root / "tests/native_raw_fvf_fog_visual_test.cpp"),
                        "-o", str(result)], check=True)
        subprocess.run([str(result)], check=True)
print("DX11 SM3 + FVF table fog / RAW specular visual source dispatch PASS (runtime UNTESTED)")
