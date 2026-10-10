#!/usr/bin/env python3
"""Fail closed when checked-in CMake omits native DX11 translation/census TUs."""

from collections import Counter
from pathlib import Path
import re
from verify_dx11_activation_boundary import main as verify_dx11_activation_boundary
from verify_dx11_dual_source_contract import main as verify_dx11_dual_source_contract

ROOT = Path(__file__).resolve().parents[1]
DX11 = ROOT / "src" / "vr" / "d3d11"
CMAKE = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
CMAKE_TOML = (ROOT / "cmake.toml").read_text(encoding="utf-8")
BACKEND_GATE = (
    ROOT / ".github" / "workflows" / "backend-conversion-gate.yml"
).read_text(encoding="utf-8")
SEMANTIC_SMOKE = (
    ROOT / "tools" / "dx11_fixed_function_shader_semantics.cpp"
).read_text(encoding="utf-8")
INPUT_LAYOUT_SMOKE = (
    ROOT / "tools" / "dx11_input_layout_semantics.cpp"
).read_text(encoding="utf-8")
INPUT_SIGNATURE_SMOKE = (
    ROOT / "tools" / "dx11_input_signature_semantics.cpp"
).read_text(encoding="utf-8")
INPUT_LAYOUT_OBJECT_PROBE = (
    ROOT / "tools" / "dx11_input_layout_object_probe.cpp"
).read_text(encoding="utf-8")
SHADER_OBJECT_PROBE = (
    ROOT / "tools" / "dx11_shader_object_probe.cpp"
).read_text(encoding="utf-8")
SHADER_LINKAGE_PROBE = (
    ROOT / "tools" / "dx11_shader_linkage_probe.cpp"
).read_text(encoding="utf-8")
CONSTANT_BUFFER_PROBE = (
    ROOT / "tools" / "dx11_constant_buffer_probe.cpp"
).read_text(encoding="utf-8")
FIXED_FUNCTION_PIPELINE_PROBE = (
    ROOT / "tools" / "dx11_fixed_function_pipeline_probe.cpp"
).read_text(encoding="utf-8")
FIXED_FUNCTION_PIPELINE_CPP = (
    ROOT / "src" / "vr" / "d3d11" / "fixed_function_pipeline.cpp"
).read_text(encoding="utf-8")
SURFACE_MIRROR_HPP = (
    ROOT / "src" / "vr" / "d3d11" / "surface_mirror.hpp"
).read_text(encoding="utf-8")
SURFACE_MIRROR_CPP = (
    ROOT / "src" / "vr" / "d3d11" / "surface_mirror.cpp"
).read_text(encoding="utf-8")
SURFACE_MIRROR_PROBE = (
    ROOT / "tools" / "dx11_surface_mirror_probe.cpp"
).read_text(encoding="utf-8")
TRIANGLE_FAN_INDEX_BUFFER_HPP = (
    ROOT / "src" / "vr" / "d3d11" / "triangle_fan_index_buffer.hpp"
).read_text(encoding="utf-8")
TRIANGLE_FAN_INDEX_BUFFER_CPP = (
    ROOT / "src" / "vr" / "d3d11" / "triangle_fan_index_buffer.cpp"
).read_text(encoding="utf-8")
TRIANGLE_FAN_INDEX_BUFFER_PROBE = (
    ROOT / "tools" / "dx11_triangle_fan_index_buffer_probe.cpp"
).read_text(encoding="utf-8")
PIPELINE_TRANSLATION_HPP = (
    ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.hpp"
).read_text(encoding="utf-8")
PIPELINE_TRANSLATION_CPP = (
    ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.cpp"
).read_text(encoding="utf-8")
NATIVE_BACKEND_HPP = (
    ROOT / "src" / "vr" / "d3d11" / "native_backend.hpp"
).read_text(encoding="utf-8")
NATIVE_BACKEND_CPP = (
    ROOT / "src" / "vr" / "d3d11" / "native_backend.cpp"
).read_text(encoding="utf-8")
RESOURCE_TRANSLATION_HPP = (
    ROOT / "src" / "vr" / "d3d11" / "resource_translation.hpp"
).read_text(encoding="utf-8")
RESOURCE_TRANSLATION_CPP = (
    ROOT / "src" / "vr" / "d3d11" / "resource_translation.cpp"
).read_text(encoding="utf-8")
STATE_TRANSLATION_CPP = (
    ROOT / "src" / "vr" / "d3d11" / "state_translation.cpp"
).read_text(encoding="utf-8")
D3D9_DRAW_STATE_HPP = (
    ROOT / "src" / "vr" / "core" / "d3d9_draw_state.hpp"
).read_text(encoding="utf-8")
D3D9_RENDER_STATE_CAPTURE = (
    ROOT / "src" / "vr" / "d3d9" / "stereo_renderer_r7.inc"
).read_text(encoding="utf-8")
RUNTIME_CENSUS = (
    ROOT / "src" / "vr" / "d3d11" / "runtime_census.cpp"
).read_text(encoding="utf-8")
RUNTIME_CENSUS_HPP = (
    ROOT / "src" / "vr" / "d3d11" / "runtime_census.hpp"
).read_text(encoding="utf-8")
DX11_CENSUS_ANALYZER = (
    ROOT / "tools" / "analyze_dx11_census.py"
).read_text(encoding="utf-8")
DX11_CENSUS_ANALYZER_TEST = (
    ROOT / "tools" / "test_analyze_dx11_census.py"
).read_text(encoding="utf-8")
CONSTANT_BUFFER_CONTRACT_TEXT = (
    CONSTANT_BUFFER_PROBE + "\n" + NATIVE_BACKEND_CPP
)


def main() -> None:
    # GitHub's Win32 build includes Windows headers that may define max as a
    # function-like macro. Keep numeric_limits::max invocations macro-safe,
    # and keep GetStreamSourceFreq's output storage type API-exact.
    msvc_compile_portability_errors = []
    for source_name, source in [
        ("native_backend.cpp", NATIVE_BACKEND_CPP),
        ("state_translation.cpp", STATE_TRANSLATION_CPP),
        ("triangle_fan_index_buffer.cpp", TRIANGLE_FAN_INDEX_BUFFER_CPP),
        ("dx11_constant_buffer_probe.cpp", CONSTANT_BUFFER_PROBE),
    ]:
        if re.search(r"std::numeric_limits<[^>]+>::max\(\)", source):
            msvc_compile_portability_errors.append(
                source_name + " contains macro-vulnerable numeric_limits::max()"
            )
    if "UINT stream0Frequency = 1u;" not in RUNTIME_CENSUS:
        msvc_compile_portability_errors.append(
            "runtime census stream frequency storage must match UINT* API"
        )
    if "using outrun::vr::dx11::BufferMutationUpdateKind;" not in CONSTANT_BUFFER_PROBE:
        msvc_compile_portability_errors.append(
            "constant-buffer probe must import BufferMutationUpdateKind"
        )
    if msvc_compile_portability_errors:
        raise SystemExit(
            "DX11 MSVC compile-portability contract drift: "
            + ", ".join(msvc_compile_portability_errors)
        )

    verify_dx11_dual_source_contract()

    r202_specular_enable_contract = [
        (
            "DWORD specularEnable = FALSE;",
            D3D9_DRAW_STATE_HPP,
            "R202 tracked specular-enable field and disabled default",
        ),
        (
            "read(D3DRS_SPECULARENABLE, out.specularEnable);",
            D3D9_RENDER_STATE_CAPTURE,
            "R202 live specular-enable capture",
        ),
        (
            "source.specularEnable != FALSE",
            PIPELINE_TRANSLATION_CPP,
            "R202/R204 native pipeline specular fail-closed predicate",
        ),
        (
            "PipelineUnsupportedSpecular = 1u << 20",
            PIPELINE_TRANSLATION_HPP,
            "R204 dedicated post-texture specular blocker identity",
        ),
        (
            "R204 enabled D3DRS_SPECULARENABLE must use dedicated fail-closed blocker",
            SEMANTIC_SMOKE,
            "R204 dedicated specular semantic regression probe",
        ),
        (
            "R204 lighting and specular blockers must remain independently observable",
            SEMANTIC_SMOKE,
            "R204 lighting/specular blocker separation",
        ),
        (
            "specular={}]",
            RUNTIME_CENSUS,
            "R204 runtime unsupported summary field",
        ),
    ]
    missing_r202_specular_enable = [
        meaning
        for token, source, meaning in r202_specular_enable_contract
        if token not in source
    ]
    if missing_r202_specular_enable:
        raise SystemExit(
            "DX11 R202 specular-enable contract drift: "
            + ", ".join(missing_r202_specular_enable)
        )

    r211_raster_census_contract = [
        ("PointRasterUnsupportedSamples", RUNTIME_CENSUS,
         "R211 point-raster census blocker counter"),
        ("LineRasterUnsupportedSamples", RUNTIME_CENSUS,
         "R211 line-raster census blocker counter"),
        ("const bool pointRasterSemanticsExact =", RUNTIME_CENSUS,
         "R211 point-raster exactness gate"),
        ("const bool lineRasterSemanticsExact =", RUNTIME_CENSUS,
         "R211 line-raster exactness gate"),
        ("pointRasterSemanticsExact && lineRasterSemanticsExact &&", RUNTIME_CENSUS,
         "R211 ExactSamples parity with dormant dispatch"),
        ("rasterSemantics[pointUnsupported={},lineUnsupported={}]", RUNTIME_CENSUS,
         "R211 periodic census blocker telemetry"),
        ("pointRasterUnsupported", DX11_CENSUS_ANALYZER,
         "R211 analyzer point blocker parsing"),
        ("lineRasterUnsupported", DX11_CENSUS_ANALYZER,
         "R211 analyzer line blocker parsing"),
        ("r211_raster_semantics = run_case(", DX11_CENSUS_ANALYZER_TEST,
         "R211 analyzer regression fixture"),
    ]
    missing_r211_raster_census = [
        meaning
        for token, source, meaning in r211_raster_census_contract
        if token not in source
    ]
    if missing_r211_raster_census:
        raise SystemExit(
            "DX11 R211 raster census exactness drift: "
            + ", ".join(missing_r211_raster_census)
        )

    r215_shader_translation_exactness_contract = [
        ("ShaderTranslationExactSamples", RUNTIME_CENSUS,
         "R215 exact fixed-function shader census counter"),
        ("signature.shaderTranslationExact =", RUNTIME_CENSUS,
         "R215 fixed-function shader exactness assignment"),
        ("signature.fixedFunctionPipelineShaderExact &&", RUNTIME_CENSUS,
         "R215 pixel/pipeline shader readiness gate"),
        ("signature.fixedFunctionVertexShaderPrototypeGenerated &&", RUNTIME_CENSUS,
         "R215 vertex shader source readiness gate"),
        ("signature.fixedFunctionTransformExact;", RUNTIME_CENSUS,
         "R215 WVP transform readiness gate"),
        ("translationExact={}", RUNTIME_CENSUS,
         "R215 periodic shader readiness telemetry"),
        ("signature.shaderTranslationExact)", RUNTIME_CENSUS,
         "R215 ExactSamples shader gate"),
        ("shaderTranslationExact", DX11_CENSUS_ANALYZER,
         "R215 analyzer shader exactness parsing"),
        ("translationExact=0", DX11_CENSUS_ANALYZER_TEST,
         "R215 analyzer regression fixture"),
    ]
    missing_r215_shader_translation_exactness = [
        meaning
        for token, source, meaning in r215_shader_translation_exactness_contract
        if token not in source
    ]
    if missing_r215_shader_translation_exactness:
        raise SystemExit(
            "DX11 R215 shader translation exactness drift: "
            + ", ".join(missing_r215_shader_translation_exactness)
        )

    r165_dither_contract = [
        ("DWORD ditherEnable = FALSE;", D3D9_DRAW_STATE_HPP,
         "R165 tracked dither field and disabled default"),
        ("read(D3DRS_DITHERENABLE, out.ditherEnable);",
         D3D9_RENDER_STATE_CAPTURE, "R165 live dither capture"),
        ("PipelineUnsupportedDither = 1u << 17", PIPELINE_TRANSLATION_HPP,
         "R165 dedicated unsupported dither bit"),
        ("source.ditherEnable != FALSE", PIPELINE_TRANSLATION_CPP,
         "R165 enabled-dither fail-closed predicate"),
        ("out.unsupported |= PipelineUnsupportedDither;",
         PIPELINE_TRANSLATION_CPP, "R165 pipeline readiness blocker"),
        ("R165 disabled D3D9 dithering must remain exact",
         FIXED_FUNCTION_PIPELINE_PROBE, "R165 disabled positive fixture"),
        ("R165 enabled D3D9 dithering must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "R165 enabled negative fixture"),
        ("R165 fixed-function shader handoff must retain dithering blocker",
         FIXED_FUNCTION_PIPELINE_PROBE, "R165 handoff negative fixture"),
        ("DX11 fixed-function dithering fail-closed R165: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R165 hosted probe completion marker"),
    ]
    missing_r165_dither = [
        meaning
        for token, source, meaning in r165_dither_contract
        if token not in source
    ]
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_DITHERENABLE") < 2:
        missing_r165_dither.append(
            "R165 DITHERENABLE must be both primed and captured")
    if missing_r165_dither:
        raise SystemExit(
            "DX11 R165 dithering contract drift: "
            + ", ".join(missing_r165_dither)
        )

    r170_texture_coordinate_wrap_contract = [
        ("std::array<DWORD, 8> textureCoordinateWrap{};", D3D9_DRAW_STATE_HPP,
         "R170 tracked WRAP0..7 state"),
        ("D3DRS_WRAP0, D3DRS_WRAP1, D3DRS_WRAP2, D3DRS_WRAP3",
         D3D9_RENDER_STATE_CAPTURE, "R170 primed WRAP0..3"),
        ("D3DRS_WRAP4, D3DRS_WRAP5, D3DRS_WRAP6, D3DRS_WRAP7",
         D3D9_RENDER_STATE_CAPTURE, "R170 primed WRAP4..7"),
        ("read(D3DRS_WRAP0, out.textureCoordinateWrap[0]);",
         D3D9_RENDER_STATE_CAPTURE, "R170 live WRAP0 capture"),
        ("read(D3DRS_WRAP7, out.textureCoordinateWrap[7]);",
         D3D9_RENDER_STATE_CAPTURE, "R170 live WRAP7 capture"),
        ("PipelineUnsupportedTextureCoordinateWrap = 1u << 18",
         PIPELINE_TRANSLATION_HPP, "R170 dedicated unsupported bit"),
        ("for (const auto wrap : source.textureCoordinateWrap)",
         PIPELINE_TRANSLATION_CPP, "R170 all-stage readiness scan"),
        ("out.unsupported |= PipelineUnsupportedTextureCoordinateWrap;",
         PIPELINE_TRANSLATION_CPP, "R170 readiness blocker"),
        ("R170 zero texture-coordinate wrap masks must remain exact",
         FIXED_FUNCTION_PIPELINE_PROBE, "R170 positive probe"),
        ("R170 nonzero D3DRS_WRAP0 must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "R170 WRAP0 negative probe"),
        ("R170 nonzero D3DRS_WRAP7 must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "R170 WRAP7 negative probe"),
        ("DX11 texture-coordinate wrap fail-closed R170: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R170 probe completion marker"),
        ("bool textureCoordinateWrapObservationComplete{};", RUNTIME_CENSUS,
         "R170 census observation identity"),
        ("for (const auto wrap : sig.textureCoordinateWrap)",
         RUNTIME_CENSUS, "R170 census value hash"),
        ("signature.textureCoordinateWrap = source.textureCoordinateWrap;",
         RUNTIME_CENSUS, "R170 census propagation"),
        ("VR DX11 R170 texture-coordinate wrap state#{}",
         RUNTIME_CENSUS, "R170 detailed census telemetry"),
    ]
    missing_r170_texture_coordinate_wrap = [
        meaning for token, source, meaning in r170_texture_coordinate_wrap_contract
        if token not in source
    ]
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_WRAP0") < 2:
        missing_r170_texture_coordinate_wrap.append(
            "R170 WRAP0 must be both primed and captured")
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_WRAP7") < 2:
        missing_r170_texture_coordinate_wrap.append(
            "R170 WRAP7 must be both primed and captured")
    if missing_r170_texture_coordinate_wrap:
        raise SystemExit(
            "DX11 R170 texture-coordinate wrap contract drift: "
            + ", ".join(missing_r170_texture_coordinate_wrap)
        )

    r167_dither_identity_contract = [
        ("bool ditherObservationComplete{};", RUNTIME_CENSUS,
         "R167 census dither observation identity"),
        ("DWORD ditherEnable = FALSE;", RUNTIME_CENSUS,
         "R167 census dither value identity"),
        ("hash, sig.ditherObservationComplete ? 1u : 0u", RUNTIME_CENSUS,
         "R167 census dither observation hash"),
        ("hash = hash_mix(hash, sig.ditherEnable);", RUNTIME_CENSUS,
         "R167 census dither value hash"),
        ("signature.ditherObservationComplete =", RUNTIME_CENSUS,
         "R167 captured dither observation propagation"),
        ("signature.ditherEnable = source.ditherEnable;", RUNTIME_CENSUS,
         "R167 captured dither value propagation"),
        ("VR DX11 R167 dither state#{}", RUNTIME_CENSUS,
         "R167 detailed dither telemetry marker"),
    ]
    missing_r167_dither_identity = [
        meaning
        for token, source, meaning in r167_dither_identity_contract
        if token not in source
    ]
    if missing_r167_dither_identity:
        raise SystemExit(
            "DX11 R167 dither census identity drift: "
            + ", ".join(missing_r167_dither_identity)
        )

    d3dtop_add_contract = [
        ("case D3DTOP_ADD:", PIPELINE_TRANSLATION_CPP,
         "D3DTOP_ADD readiness/translation case"),
        ('return first + " + " + second;', PIPELINE_TRANSLATION_CPP,
         "D3DTOP_ADD component-wise shader expression"),
        ("addStages[0].colorOp = D3DTOP_ADD;",
         FIXED_FUNCTION_PIPELINE_PROBE, "D3DTOP_ADD hosted probe fixture"),
        ("float3 nextColor = sampled0.rgb + input.diffuse.rgb;",
         FIXED_FUNCTION_PIPELINE_PROBE, "D3DTOP_ADD generated HLSL assertion"),
        ("D3DTOP_ADD fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "D3DTOP_ADD offline compile assertion"),
        ("DX11 fixed-function D3DTOP_ADD support: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "D3DTOP_ADD hosted probe completion"),
    ]
    missing_d3dtop_add = [
        meaning
        for token, source, meaning in d3dtop_add_contract
        if token not in source
    ]
    if missing_d3dtop_add:
        raise SystemExit(
            "DX11 fixed-function D3DTOP_ADD contract drift: "
            + ", ".join(missing_d3dtop_add)
        )

    r177_d3dtop_subtract_contract = [
        ("case D3DTOP_SUBTRACT:", PIPELINE_TRANSLATION_CPP,
         "R177 D3DTOP_SUBTRACT readiness/translation case"),
        ('return first + " - " + second;', PIPELINE_TRANSLATION_CPP,
         "R177 D3DTOP_SUBTRACT component-wise shader expression"),
        ("subtractStages[0].colorOp = D3DTOP_SUBTRACT;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R177 hosted SUBTRACT probe fixture"),
        ("float3 nextColor = sampled0.rgb - input.diffuse.rgb;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R177 generated HLSL assertion"),
        ("R177 D3DTOP_SUBTRACT fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "R177 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_SUBTRACT support R177: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R177 hosted probe completion"),
    ]
    missing_r177_d3dtop_subtract = [
        meaning
        for token, source, meaning in r177_d3dtop_subtract_contract
        if token not in source
    ]
    if missing_r177_d3dtop_subtract:
        raise SystemExit(
            "DX11 R177 fixed-function D3DTOP_SUBTRACT contract drift: "
            + ", ".join(missing_r177_d3dtop_subtract)
        )

    r180_d3dtop_modulate2x_contract = [
        ("case D3DTOP_MODULATE2X:", PIPELINE_TRANSLATION_CPP,
         "R180 D3DTOP_MODULATE2X readiness/translation case"),
        ('return "(" + first + " * " + second + ") * 2.0";',
         PIPELINE_TRANSLATION_CPP,
         "R180 D3DTOP_MODULATE2X component-wise shader expression"),
        ("modulate2xStages[0].colorOp = D3DTOP_MODULATE2X;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R180 hosted MODULATE2X color fixture"),
        ("modulate2xStages[0].alphaOp = D3DTOP_MODULATE2X;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R180 hosted MODULATE2X alpha fixture"),
        ("float3 nextColor = (sampled0.rgb * input.diffuse.rgb) * 2.0;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R180 generated RGB HLSL assertion"),
        ("float nextAlpha = (sampled0.a * input.diffuse.a) * 2.0;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R180 generated alpha HLSL assertion"),
        ("R180 D3DTOP_MODULATE2X fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "R180 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_MODULATE2X support R180: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R180 hosted probe completion"),
    ]
    missing_r180_d3dtop_modulate2x = [
        meaning
        for token, source, meaning in r180_d3dtop_modulate2x_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_MODULATE2X:") < 3:
        missing_r180_d3dtop_modulate2x.append(
            "R180 MODULATE2X must participate in texture-use, HLSL and readiness switches")
    if missing_r180_d3dtop_modulate2x:
        raise SystemExit(
            "DX11 R180 fixed-function D3DTOP_MODULATE2X contract drift: "
            + ", ".join(missing_r180_d3dtop_modulate2x)
        )

    r181_d3dtop_modulate4x_contract = [
        ("case D3DTOP_MODULATE4X:", PIPELINE_TRANSLATION_CPP,
         "R181 D3DTOP_MODULATE4X readiness/translation case"),
        ('return "(" + first + " * " + second + ") * 4.0";',
         PIPELINE_TRANSLATION_CPP,
         "R181 D3DTOP_MODULATE4X component-wise shader expression"),
        ("modulate4xStages[0].colorOp = D3DTOP_MODULATE4X;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R181 hosted MODULATE4X color fixture"),
        ("modulate4xStages[0].alphaOp = D3DTOP_MODULATE4X;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R181 hosted MODULATE4X alpha fixture"),
        ("float3 nextColor = (sampled0.rgb * input.diffuse.rgb) * 4.0;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R181 generated RGB HLSL assertion"),
        ("float nextAlpha = (sampled0.a * input.diffuse.a) * 4.0;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R181 generated alpha HLSL assertion"),
        ("R181 D3DTOP_MODULATE4X fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "R181 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_MODULATE4X support R181: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R181 hosted probe completion"),
    ]
    missing_r181_d3dtop_modulate4x = [
        meaning
        for token, source, meaning in r181_d3dtop_modulate4x_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_MODULATE4X:") < 3:
        missing_r181_d3dtop_modulate4x.append(
            "R181 MODULATE4X must participate in texture-use, HLSL and readiness switches")
    if missing_r181_d3dtop_modulate4x:
        raise SystemExit(
            "DX11 R181 fixed-function D3DTOP_MODULATE4X contract drift: "
            + ", ".join(missing_r181_d3dtop_modulate4x)
        )

    r182_d3dtop_addsigned_contract = [
        ("case D3DTOP_ADDSIGNED:", PIPELINE_TRANSLATION_CPP,
         "R182 D3DTOP_ADDSIGNED readiness/translation case"),
        ('return first + " + " + second + " - 0.5";',
         PIPELINE_TRANSLATION_CPP,
         "R182 D3DTOP_ADDSIGNED biased-add shader expression"),
        ("addSignedStages[0].colorOp = D3DTOP_ADDSIGNED;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R182 hosted ADDSIGNED color fixture"),
        ("addSignedStages[0].alphaOp = D3DTOP_ADDSIGNED;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R182 hosted ADDSIGNED alpha fixture"),
        ("float3 nextColor = sampled0.rgb + input.diffuse.rgb - 0.5;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R182 generated RGB HLSL assertion"),
        ("float nextAlpha = sampled0.a + input.diffuse.a - 0.5;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R182 generated alpha HLSL assertion"),
        ("R182 D3DTOP_ADDSIGNED fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "R182 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_ADDSIGNED support R182: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R182 hosted probe completion"),
    ]
    missing_r182_d3dtop_addsigned = [
        meaning
        for token, source, meaning in r182_d3dtop_addsigned_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_ADDSIGNED:") < 3:
        missing_r182_d3dtop_addsigned.append(
            "R182 ADDSIGNED must participate in texture-use, HLSL and readiness switches")
    if missing_r182_d3dtop_addsigned:
        raise SystemExit(
            "DX11 R182 fixed-function D3DTOP_ADDSIGNED contract drift: "
            + ", ".join(missing_r182_d3dtop_addsigned)
        )

    r183_d3dtop_addsigned2x_contract = [
        ("case D3DTOP_ADDSIGNED2X:", PIPELINE_TRANSLATION_CPP,
         "R183 D3DTOP_ADDSIGNED2X readiness/translation case"),
        ('return "(" + first + " + " + second + " - 0.5) * 2.0";',
         PIPELINE_TRANSLATION_CPP,
         "R183 D3DTOP_ADDSIGNED2X biased doubled shader expression"),
        ("addSigned2xStages[0].colorOp = D3DTOP_ADDSIGNED2X;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R183 hosted ADDSIGNED2X color fixture"),
        ("addSigned2xStages[0].alphaOp = D3DTOP_ADDSIGNED2X;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R183 hosted ADDSIGNED2X alpha fixture"),
        ("float3 nextColor = (sampled0.rgb + input.diffuse.rgb - 0.5) * 2.0;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R183 generated RGB HLSL assertion"),
        ("float nextAlpha = (sampled0.a + input.diffuse.a - 0.5) * 2.0;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R183 generated alpha HLSL assertion"),
        ("R183 D3DTOP_ADDSIGNED2X fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "R183 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_ADDSIGNED2X support R183: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R183 hosted probe completion"),
    ]
    missing_r183_d3dtop_addsigned2x = [
        meaning
        for token, source, meaning in r183_d3dtop_addsigned2x_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_ADDSIGNED2X:") < 3:
        missing_r183_d3dtop_addsigned2x.append(
            "R183 ADDSIGNED2X must participate in texture-use, HLSL and readiness switches")
    if missing_r183_d3dtop_addsigned2x:
        raise SystemExit(
            "DX11 R183 fixed-function D3DTOP_ADDSIGNED2X contract drift: "
            + ", ".join(missing_r183_d3dtop_addsigned2x)
        )

    r184_d3dtop_addsmooth_contract = [
        ("case D3DTOP_ADDSMOOTH:", PIPELINE_TRANSLATION_CPP,
         "R184 D3DTOP_ADDSMOOTH readiness/translation case"),
        ('return first + " + " + second + " * (1.0 - " + first + ")";',
         PIPELINE_TRANSLATION_CPP,
         "R184 D3DTOP_ADDSMOOTH component-wise shader expression"),
        ("addSmoothStages[0].colorOp = D3DTOP_ADDSMOOTH;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R184 hosted ADDSMOOTH color fixture"),
        ("addSmoothStages[0].alphaOp = D3DTOP_ADDSMOOTH;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R184 hosted ADDSMOOTH alpha fixture"),
        ("float3 nextColor = sampled0.rgb + input.diffuse.rgb * (1.0 - sampled0.rgb);",
         FIXED_FUNCTION_PIPELINE_PROBE, "R184 generated RGB HLSL assertion"),
        ("float nextAlpha = sampled0.a + input.diffuse.a * (1.0 - sampled0.a);",
         FIXED_FUNCTION_PIPELINE_PROBE, "R184 generated alpha HLSL assertion"),
        ("R184 D3DTOP_ADDSMOOTH fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "R184 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_ADDSMOOTH support R184: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R184 hosted probe completion"),
    ]
    missing_r184_d3dtop_addsmooth = [
        meaning
        for token, source, meaning in r184_d3dtop_addsmooth_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_ADDSMOOTH:") < 3:
        missing_r184_d3dtop_addsmooth.append(
            "R184 ADDSMOOTH must participate in texture-use, HLSL and readiness switches")
    if missing_r184_d3dtop_addsmooth:
        raise SystemExit(
            "DX11 R184 fixed-function D3DTOP_ADDSMOOTH contract drift: "
            + ", ".join(missing_r184_d3dtop_addsmooth)
        )

    r185_d3dtop_blenddiffusealpha_contract = [
        ("case D3DTOP_BLENDDIFFUSEALPHA:", PIPELINE_TRANSLATION_CPP,
         "R185 D3DTOP_BLENDDIFFUSEALPHA readiness/translation case"),
        ('return first + " * input.diffuse.a + " + second +',
         PIPELINE_TRANSLATION_CPP,
         "R185 D3DTOP_BLENDDIFFUSEALPHA diffuse-alpha shader expression"),
        ("blendDiffuseAlphaStages[0].colorOp = D3DTOP_BLENDDIFFUSEALPHA;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R185 hosted BLENDDIFFUSEALPHA color fixture"),
        ("blendDiffuseAlphaStages[0].alphaOp = D3DTOP_BLENDDIFFUSEALPHA;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R185 hosted BLENDDIFFUSEALPHA alpha fixture"),
        ("float3 nextColor = sampled0.rgb * input.diffuse.a + input.diffuse.rgb * (1.0 - input.diffuse.a);",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R185 generated RGB HLSL assertion"),
        ("float nextAlpha = sampled0.a * input.diffuse.a + input.diffuse.a * (1.0 - input.diffuse.a);",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R185 generated alpha HLSL assertion"),
        ("R185 D3DTOP_BLENDDIFFUSEALPHA fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "R185 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_BLENDDIFFUSEALPHA support R185: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R185 hosted probe completion"),
    ]
    missing_r185_d3dtop_blenddiffusealpha = [
        meaning
        for token, source, meaning in r185_d3dtop_blenddiffusealpha_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_BLENDDIFFUSEALPHA:") < 3:
        missing_r185_d3dtop_blenddiffusealpha.append(
            "R185 BLENDDIFFUSEALPHA must participate in texture-use, HLSL and readiness switches")
    if missing_r185_d3dtop_blenddiffusealpha:
        raise SystemExit(
            "DX11 R185 fixed-function D3DTOP_BLENDDIFFUSEALPHA contract drift: "
            + ", ".join(missing_r185_d3dtop_blenddiffusealpha)
        )

    d3dtop_blendcurrentalpha_contract = [
        ("case D3DTOP_BLENDCURRENTALPHA:", PIPELINE_TRANSLATION_CPP,
         "D3DTOP_BLENDCURRENTALPHA readiness/translation case"),
        ('return first + " * current.a + " + second +',
         PIPELINE_TRANSLATION_CPP,
         "D3DTOP_BLENDCURRENTALPHA previous-stage alpha expression"),
        ("blendCurrentAlphaStages[1].colorOp = D3DTOP_BLENDCURRENTALPHA;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "hosted BLENDCURRENTALPHA color fixture"),
        ("blendCurrentAlphaStages[1].alphaOp = D3DTOP_BLENDCURRENTALPHA;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "hosted BLENDCURRENTALPHA alpha fixture"),
        ("sampled1.rgb * current.a + input.diffuse.rgb * (1.0 - current.a)",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "generated RGB previous-stage alpha assertion"),
        ("sampled1.a * current.a + input.diffuse.a * (1.0 - current.a)",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "generated alpha previous-stage alpha assertion"),
        ("D3DTOP_BLENDCURRENTALPHA fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "offline compile assertion"),
        ("DX11 fixed-function D3DTOP_BLENDCURRENTALPHA support: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "hosted probe completion"),
    ]
    missing_d3dtop_blendcurrentalpha = [
        meaning
        for token, source, meaning in d3dtop_blendcurrentalpha_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_BLENDCURRENTALPHA:") < 3:
        missing_d3dtop_blendcurrentalpha.append(
            "BLENDCURRENTALPHA must participate in texture-use, HLSL and readiness switches")
    if missing_d3dtop_blendcurrentalpha:
        raise SystemExit(
            "DX11 fixed-function D3DTOP_BLENDCURRENTALPHA contract drift: "
            + ", ".join(missing_d3dtop_blendcurrentalpha)
        )

    r186_d3dtop_blendtexturealpha_contract = [
        ("case D3DTOP_BLENDTEXTUREALPHA:", PIPELINE_TRANSLATION_CPP,
         "R186 D3DTOP_BLENDTEXTUREALPHA readiness/translation case"),
        ("even when neither argument selects texture.", PIPELINE_TRANSLATION_CPP,
         "R186 intrinsic texture dependency"),
        ('"sampled" + std::to_string(stageIndex) + ".a";',
         PIPELINE_TRANSLATION_CPP, "R186 sampled texture-alpha factor"),
        ("blendTextureAlphaStages[0].colorOp = D3DTOP_BLENDTEXTUREALPHA;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R186 hosted color fixture"),
        ("blendTextureAlphaStages[0].alphaOp = D3DTOP_BLENDTEXTUREALPHA;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R186 hosted alpha fixture"),
        ("float3 nextColor = input.diffuse.rgb * sampled0.a + current.rgb * (1.0 - sampled0.a);",
         FIXED_FUNCTION_PIPELINE_PROBE, "R186 RGB HLSL assertion"),
        ("float nextAlpha = input.diffuse.a * sampled0.a + current.a * (1.0 - sampled0.a);",
         FIXED_FUNCTION_PIPELINE_PROBE, "R186 alpha HLSL assertion"),
        ("R186 D3DTOP_BLENDTEXTUREALPHA fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "R186 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_BLENDTEXTUREALPHA support R186: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R186 hosted probe completion"),
    ]
    missing_r186_d3dtop_blendtexturealpha = [
        meaning for token, source, meaning in r186_d3dtop_blendtexturealpha_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_BLENDTEXTUREALPHA:") < 3:
        missing_r186_d3dtop_blendtexturealpha.append(
            "R186 BLENDTEXTUREALPHA must participate in texture-use, HLSL and readiness switches")
    if missing_r186_d3dtop_blendtexturealpha:
        raise SystemExit(
            "DX11 R186 fixed-function D3DTOP_BLENDTEXTUREALPHA contract drift: "
            + ", ".join(missing_r186_d3dtop_blendtexturealpha)
        )

    r187_d3dtop_blendtexturealphapm_contract = [
        ("case D3DTOP_BLENDTEXTUREALPHAPM:", PIPELINE_TRANSLATION_CPP,
         "R187 D3DTOP_BLENDTEXTUREALPHAPM readiness/translation case"),
        ("premultiplied texture-alpha blending still depends on",
         PIPELINE_TRANSLATION_CPP, "R187 intrinsic texture dependency"),
        ('return first + " + " + second +',
         PIPELINE_TRANSLATION_CPP,
         "R187 premultiplied texture-alpha shader expression"),
        ("blendTextureAlphaPmStages[0].colorOp = D3DTOP_BLENDTEXTUREALPHAPM;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R187 hosted color fixture"),
        ("blendTextureAlphaPmStages[0].alphaOp = D3DTOP_BLENDTEXTUREALPHAPM;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R187 hosted alpha fixture"),
        ("float3 nextColor = input.diffuse.rgb + current.rgb * (1.0 - sampled0.a);",
         FIXED_FUNCTION_PIPELINE_PROBE, "R187 RGB HLSL assertion"),
        ("float nextAlpha = input.diffuse.a + current.a * (1.0 - sampled0.a);",
         FIXED_FUNCTION_PIPELINE_PROBE, "R187 alpha HLSL assertion"),
        ("R187 D3DTOP_BLENDTEXTUREALPHAPM fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "R187 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_BLENDTEXTUREALPHAPM support R187: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R187 hosted probe completion"),
    ]
    missing_r187_d3dtop_blendtexturealphapm = [
        meaning
        for token, source, meaning in r187_d3dtop_blendtexturealphapm_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_BLENDTEXTUREALPHAPM:") < 3:
        missing_r187_d3dtop_blendtexturealphapm.append(
            "R187 BLENDTEXTUREALPHAPM must participate in texture-use, HLSL and readiness switches")
    if missing_r187_d3dtop_blendtexturealphapm:
        raise SystemExit(
            "DX11 R187 fixed-function D3DTOP_BLENDTEXTUREALPHAPM contract drift: "
            + ", ".join(missing_r187_d3dtop_blendtexturealphapm)
        )

    implicit_texture_alpha_resource_coverage_contract = [
        ("blendTextureAlphaMissingResource", FIXED_FUNCTION_PIPELINE_PROBE,
         "R186 missing-resource readiness fixture"),
        ("R186 implicit texture-alpha resource coverage must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R186 missing-resource fail-closed assertion"),
        ("blendTextureAlphaPmMissingResource", FIXED_FUNCTION_PIPELINE_PROBE,
         "R187 missing-resource readiness fixture"),
        ("R187 implicit texture-alpha resource coverage must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R187 missing-resource fail-closed assertion"),
        ("FixedFunctionUnsupportedResourceStageCoverage",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "implicit texture-alpha resource coverage blocker"),
    ]
    missing_implicit_texture_alpha_resource_coverage = [
        meaning
        for token, source, meaning
        in implicit_texture_alpha_resource_coverage_contract
        if token not in source
    ]
    if missing_implicit_texture_alpha_resource_coverage:
        raise SystemExit(
            "DX11 implicit texture-alpha resource coverage contract drift: "
            + ", ".join(missing_implicit_texture_alpha_resource_coverage)
        )

    modulatealpha_addcolor_contract = [
        ("case D3DTOP_MODULATEALPHA_ADDCOLOR:", PIPELINE_TRANSLATION_CPP,
         "D3DTOP_MODULATEALPHA_ADDCOLOR dependency/readiness/translation case"),
        ("bool alphaOperation,", PIPELINE_TRANSLATION_CPP,
         "color-only readiness discriminator"),
        ('return first + " + " + firstAlpha + " * " + second;',
         PIPELINE_TRANSLATION_CPP,
         "MODULATEALPHA_ADDCOLOR RGB expression"),
        ("FixedFunctionUnsupportedColorOp, false, out", PIPELINE_TRANSLATION_CPP,
         "COLOROP validator channel identity"),
        ("FixedFunctionUnsupportedAlphaOp, true, out", PIPELINE_TRANSLATION_CPP,
         "ALPHAOP validator channel identity"),
        ("modulateAlphaAddColorStages[0].colorOp =",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "hosted MODULATEALPHA_ADDCOLOR color fixture"),
        ("sampled0.rgb + sampled0.a * input.diffuse.rgb",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "generated RGB MODULATEALPHA_ADDCOLOR assertion"),
        ("FixedFunctionUnsupportedAlphaOp) != 0",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "color-only ALPHAOP rejection assertion"),
        ("D3DTOP_MODULATEALPHA_ADDCOLOR fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "offline compile assertion"),
        ("DX11 fixed-function D3DTOP_MODULATEALPHA_ADDCOLOR COLOROP support: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "hosted probe completion"),
    ]
    missing_modulatealpha_addcolor = [
        meaning
        for token, source, meaning in modulatealpha_addcolor_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count(
            "case D3DTOP_MODULATEALPHA_ADDCOLOR:") < 3:
        missing_modulatealpha_addcolor.append(
            "MODULATEALPHA_ADDCOLOR must participate in dependency, HLSL and readiness switches")
    if missing_modulatealpha_addcolor:
        raise SystemExit(
            "DX11 fixed-function D3DTOP_MODULATEALPHA_ADDCOLOR contract drift: "
            + ", ".join(missing_modulatealpha_addcolor)
        )

    r188_d3dtop_modulatecolor_addalpha_contract = [
        ("case D3DTOP_MODULATECOLOR_ADDALPHA:", PIPELINE_TRANSLATION_CPP,
         "R188 D3DTOP_MODULATECOLOR_ADDALPHA dependency/readiness/translation case"),
        ('return first + " * " + second + " + " + firstAlpha;',
         PIPELINE_TRANSLATION_CPP,
         "R188 MODULATECOLOR_ADDALPHA RGB expression"),
        ("modulateColorAddAlphaStages[0].colorOp =",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R188 hosted MODULATECOLOR_ADDALPHA color fixture"),
        ("sampled0.rgb * input.diffuse.rgb + sampled0.a",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R188 generated RGB MODULATECOLOR_ADDALPHA assertion"),
        ("R188 D3DTOP_MODULATECOLOR_ADDALPHA must remain fail-closed as ALPHAOP",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R188 color-only ALPHAOP rejection assertion"),
        ("R188 D3DTOP_MODULATECOLOR_ADDALPHA fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R188 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_MODULATECOLOR_ADDALPHA COLOROP support R188: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R188 hosted probe completion"),
    ]
    missing_r188_d3dtop_modulatecolor_addalpha = [
        meaning
        for token, source, meaning in r188_d3dtop_modulatecolor_addalpha_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count(
            "case D3DTOP_MODULATECOLOR_ADDALPHA:") < 3:
        missing_r188_d3dtop_modulatecolor_addalpha.append(
            "R188 MODULATECOLOR_ADDALPHA must participate in dependency, HLSL and readiness switches")
    if missing_r188_d3dtop_modulatecolor_addalpha:
        raise SystemExit(
            "DX11 R188 fixed-function D3DTOP_MODULATECOLOR_ADDALPHA contract drift: "
            + ", ".join(missing_r188_d3dtop_modulatecolor_addalpha)
        )


    r189_d3dtop_modulateinvalpha_addcolor_contract = [
        ("case D3DTOP_MODULATEINVALPHA_ADDCOLOR:", PIPELINE_TRANSLATION_CPP,
         "R189 D3DTOP_MODULATEINVALPHA_ADDCOLOR dependency/readiness/translation case"),
        ('return first + " + (1.0 - " + firstAlpha + ") * " + second;',
         PIPELINE_TRANSLATION_CPP,
         "R189 MODULATEINVALPHA_ADDCOLOR RGB expression"),
        ("modulateInvAlphaAddColorStages[0].colorOp =",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R189 hosted MODULATEINVALPHA_ADDCOLOR color fixture"),
        ("sampled0.rgb + (1.0 - sampled0.a) * input.diffuse.rgb",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R189 generated RGB MODULATEINVALPHA_ADDCOLOR assertion"),
        ("R189 D3DTOP_MODULATEINVALPHA_ADDCOLOR must remain fail-closed as ALPHAOP",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R189 color-only ALPHAOP rejection assertion"),
        ("R189 D3DTOP_MODULATEINVALPHA_ADDCOLOR fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R189 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_MODULATEINVALPHA_ADDCOLOR COLOROP support R189: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R189 hosted probe completion"),
    ]
    missing_r189_d3dtop_modulateinvalpha_addcolor = [
        meaning
        for token, source, meaning in r189_d3dtop_modulateinvalpha_addcolor_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count(
            "case D3DTOP_MODULATEINVALPHA_ADDCOLOR:") < 3:
        missing_r189_d3dtop_modulateinvalpha_addcolor.append(
            "R189 MODULATEINVALPHA_ADDCOLOR must participate in dependency, HLSL and readiness switches")
    if missing_r189_d3dtop_modulateinvalpha_addcolor:
        raise SystemExit(
            "DX11 R189 fixed-function D3DTOP_MODULATEINVALPHA_ADDCOLOR contract drift: "
            + ", ".join(missing_r189_d3dtop_modulateinvalpha_addcolor)
        )

    r190_d3dtop_modulateinvcolor_addalpha_contract = [
        ("case D3DTOP_MODULATEINVCOLOR_ADDALPHA:", PIPELINE_TRANSLATION_CPP,
         "R190 D3DTOP_MODULATEINVCOLOR_ADDALPHA dependency/readiness/translation case"),
        ('return "(1.0 - " + first + ") * " + second + " + " +',
         PIPELINE_TRANSLATION_CPP,
         "R190 MODULATEINVCOLOR_ADDALPHA RGB expression"),
        ("modulateInvColorAddAlphaStages[0].colorOp =",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R190 hosted MODULATEINVCOLOR_ADDALPHA color fixture"),
        ("(1.0 - sampled0.rgb) * input.diffuse.rgb + sampled0.a",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R190 generated RGB MODULATEINVCOLOR_ADDALPHA assertion"),
        ("R190 D3DTOP_MODULATEINVCOLOR_ADDALPHA must remain fail-closed as ALPHAOP",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R190 color-only ALPHAOP rejection assertion"),
        ("R190 D3DTOP_MODULATEINVCOLOR_ADDALPHA fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R190 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_MODULATEINVCOLOR_ADDALPHA COLOROP support R190: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R190 hosted probe completion"),
    ]
    missing_r190_d3dtop_modulateinvcolor_addalpha = [
        meaning
        for token, source, meaning in r190_d3dtop_modulateinvcolor_addalpha_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count(
            "case D3DTOP_MODULATEINVCOLOR_ADDALPHA:") < 3:
        missing_r190_d3dtop_modulateinvcolor_addalpha.append(
            "R190 MODULATEINVCOLOR_ADDALPHA must participate in dependency, HLSL and readiness switches")
    if missing_r190_d3dtop_modulateinvcolor_addalpha:
        raise SystemExit(
            "DX11 R190 fixed-function D3DTOP_MODULATEINVCOLOR_ADDALPHA contract drift: "
            + ", ".join(missing_r190_d3dtop_modulateinvcolor_addalpha)
        )


    r191_texture_factor_census_contract = [
        ("DWORD textureFactor = 0xFFFFFFFFu;", D3D9_DRAW_STATE_HPP,
         "R191 texture-factor snapshot and D3D9 default"),
        ("D3DRS_TEXTUREFACTOR,", D3D9_RENDER_STATE_CAPTURE,
         "R191 tracked texture-factor priming"),
        ("read(D3DRS_TEXTUREFACTOR, out.textureFactor);",
         D3D9_RENDER_STATE_CAPTURE,
         "R191 live texture-factor capture"),
        ("bool textureFactorObservationComplete{};", RUNTIME_CENSUS,
         "R191 texture-factor census completeness"),
        ("DWORD textureFactor = 0xFFFFFFFFu;", RUNTIME_CENSUS,
         "R191 texture-factor census value"),
        ("hash, sig.textureFactorObservationComplete ? 1u : 0u",
         RUNTIME_CENSUS,
         "R191 texture-factor completeness hash"),
        ("hash = hash_mix(hash, sig.textureFactor);", RUNTIME_CENSUS,
         "R191 texture-factor value hash"),
        ("signature.textureFactor = source.textureFactor;", RUNTIME_CENSUS,
         "R191 texture-factor propagation"),
        ("VR DX11 R191 ffp texture-factor state#{}", RUNTIME_CENSUS,
         "R191 texture-factor detailed evidence"),
        ("case D3DTA_TFACTOR:", PIPELINE_TRANSLATION_CPP,
         "R191 TFACTOR argument translation"),
        ("case D3DTOP_BLENDFACTORALPHA:", PIPELINE_TRANSLATION_CPP,
         "R191 BLENDFACTORALPHA operation translation"),
        ("D3DRS_TEXTUREFACTOR's alpha byte as one global scalar",
         PIPELINE_TRANSLATION_CPP,
         "R191 BLENDFACTORALPHA semantic ownership"),
        ("source.textureFactor);", FIXED_FUNCTION_PIPELINE_CPP,
         "R191 live pipeline texture-factor handoff"),
        ("sig.textureFactor);", RUNTIME_CENSUS,
         "R191 diagnostic shader texture-factor handoff"),
        ("textureFactorStages[0].colorArg1 = D3DTA_TFACTOR;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R191 TFACTOR hosted fixture"),
        ("blendFactorAlphaStages[0].colorOp = D3DTOP_BLENDFACTORALPHA;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R191 BLENDFACTORALPHA hosted fixture"),
        ("101.0f / 255.0f, 67.0f / 255.0f, 33.0f / 255.0f, 128.0f / 255.0f",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R191 D3DCOLOR ARGB-to-RGBA normalization assertion"),
        ("R191 texture-factor fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R191 offline compile assertion"),
        ("DX11 fixed-function texture-factor consumption R191: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R191 hosted probe completion"),
    ]
    missing_r191_texture_factor_census = [
        meaning
        for token, source, meaning in r191_texture_factor_census_contract
        if token not in source
    ]
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_TEXTUREFACTOR") < 2:
        missing_r191_texture_factor_census.append(
            "R191 TEXTUREFACTOR must be both primed and captured")
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_BLENDFACTORALPHA:") < 3:
        missing_r191_texture_factor_census.append(
            "R191 BLENDFACTORALPHA must participate in dependency, HLSL and readiness switches")
    if missing_r191_texture_factor_census:
        raise SystemExit(
            "DX11 R191 fixed-function texture-factor census contract drift: "
            + ", ".join(missing_r191_texture_factor_census)
        )

    r193_d3dtop_dotproduct3_contract = [
        ("case D3DTOP_DOTPRODUCT3:", PIPELINE_TRANSLATION_CPP,
         "R193 D3DTOP_DOTPRODUCT3 dependency/readiness/translation case"),
        ('return "dot((" + dotFirst + " * 2.0 - 1.0), (" +',
         PIPELINE_TRANSLATION_CPP,
         "R193 signed RGB DOTPRODUCT3 expression"),
        ("dotProductStages[0].colorOp = D3DTOP_DOTPRODUCT3;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R193 hosted DOTPRODUCT3 color fixture"),
        (
            'const auto dotFirst = fixed_function_argument_expression(\n'
            '                    arg1, stageIndex, ".rgb", textureFactor, stageConstant,\n'
            '                    premodulateCurrent);',
            PIPELINE_TRANSLATION_CPP,
            "R193 DOTPRODUCT3 first RGB argument must retain texture-factor/stage-constant/premodulate plumbing",
        ),
        (
            'const auto dotSecond = fixed_function_argument_expression(\n'
            '                    arg2, stageIndex, ".rgb", textureFactor, stageConstant,\n'
            '                    premodulateCurrent);',
            PIPELINE_TRANSLATION_CPP,
            "R193 DOTPRODUCT3 second RGB argument must retain texture-factor/stage-constant/premodulate plumbing",
        ),
        ("dotProductStages[0].alphaOp = D3DTOP_DOTPRODUCT3;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R193 hosted DOTPRODUCT3 alpha fixture"),
        ("sampled0.rgb * 2.0 - 1.0",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R193 signed sampled RGB transform"),
        ("input.diffuse.rgb * 2.0 - 1.0",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R193 signed diffuse RGB transform"),
        ("R193 D3DTOP_DOTPRODUCT3 fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R193 offline compile assertion"),
        ("R193 D3DTOP_DOTPRODUCT3 texture dependency must fail closed without exact resource coverage",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R193 texture-resource fail-closed assertion"),
        ("DX11 fixed-function D3DTOP_DOTPRODUCT3 support R193: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R193 hosted probe completion"),
    ]
    missing_r193_d3dtop_dotproduct3 = [
        meaning
        for token, source, meaning in r193_d3dtop_dotproduct3_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_DOTPRODUCT3:") < 3:
        missing_r193_d3dtop_dotproduct3.append(
            "R193 DOTPRODUCT3 must participate in dependency, HLSL and readiness switches")
    if missing_r193_d3dtop_dotproduct3:
        raise SystemExit(
            "DX11 R193 fixed-function D3DTOP_DOTPRODUCT3 contract drift: "
            + ", ".join(missing_r193_d3dtop_dotproduct3)
        )

    r194_d3dtop_multiplyadd_arg0_contract = [
        ("DWORD colorArg0 = D3DTA_CURRENT;", PIPELINE_TRANSLATION_HPP,
         "R194 COLORARG0 stage identity and D3D9 default"),
        ("DWORD alphaArg0 = D3DTA_CURRENT;", PIPELINE_TRANSLATION_HPP,
         "R194 ALPHAARG0 stage identity and D3D9 default"),
        ("observeTextureStageState(D3DTSS_COLORARG0, out.colorArg0);",
         RUNTIME_CENSUS, "R194 live COLORARG0 observation"),
        ("observeTextureStageState(D3DTSS_ALPHAARG0, out.alphaArg0);",
         RUNTIME_CENSUS, "R194 live ALPHAARG0 observation"),
        ("hash = hash_mix(hash, stage.colorArg0);", RUNTIME_CENSUS,
         "R194 COLORARG0 census identity"),
        ("hash = hash_mix(hash, stage.alphaArg0);", RUNTIME_CENSUS,
         "R194 ALPHAARG0 census identity"),
        ("VR DX11 R197 ffp signature#{}", RUNTIME_CENSUS,
         "R194 ARG0 detailed census evidence retained by R197 log revision"),
        ("case D3DTOP_MULTIPLYADD:", PIPELINE_TRANSLATION_CPP,
         "R194 MULTIPLYADD dependency/HLSL/readiness case"),
        ('return first + " + " + second + " * " + third;',
         PIPELINE_TRANSLATION_CPP, "R194 Arg1 + Arg2 * Arg0 HLSL expression"),
        ("multiplyAddStages[0].colorArg0 = D3DTA_TEXTURE;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R194 COLORARG0 texture fixture"),
        ("multiplyAddStages[0].alphaArg0 = D3DTA_TEXTURE;",
         FIXED_FUNCTION_PIPELINE_PROBE, "R194 ALPHAARG0 texture fixture"),
        ("R194 D3DTOP_MULTIPLYADD ARG0 texture dependency must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "R194 ARG0 resource coverage guard"),
        ("constexpr DWORD invalidArgumentSelector =",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R201-compatible invalid ARG0 selector fixture declaration"),
        ("unsupportedArg0Stages[0].colorArg0 = invalidArgumentSelector;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R194 invalid ARG0 selector fixture must not reuse supported TEMP"),
        ("R194 D3DTOP_MULTIPLYADD unsupported ARG0 selector must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "R194 ARG0 selector guard"),
        ("R194 D3DTOP_MULTIPLYADD fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE, "R194 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_MULTIPLYADD ARG0 support R194: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R194 hosted probe completion"),
    ]
    missing_r194_d3dtop_multiplyadd_arg0 = [
        meaning
        for token, source, meaning in r194_d3dtop_multiplyadd_arg0_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_MULTIPLYADD:") < 3:
        missing_r194_d3dtop_multiplyadd_arg0.append(
            "R194 MULTIPLYADD must participate in dependency, HLSL and readiness switches")
    if missing_r194_d3dtop_multiplyadd_arg0:
        raise SystemExit(
            "DX11 R194 fixed-function D3DTOP_MULTIPLYADD ARG0 contract drift: "
            + ", ".join(missing_r194_d3dtop_multiplyadd_arg0)
        )

    r195_d3dtop_premodulate_contract = [
        ("case D3DTOP_PREMODULATE:", PIPELINE_TRANSLATION_CPP,
         "R195 PREMODULATE dependency/HLSL/readiness case"),
        ("fixed_function_op_uses_current_argument(",
         PIPELINE_TRANSLATION_CPP,
         "R195 next-stage CURRENT dependency classifier"),
        ("fixed_function_stage_uses_texture(",
         PIPELINE_TRANSLATION_CPP,
         "R195 implicit next-stage texture dependency classifier"),
        ("premodulateCurrent",
         PIPELINE_TRANSLATION_CPP,
         "R195 CURRENT rewrite flag"),
        ('? "(current * sampled" + std::to_string(stageIndex) + ")"',
         PIPELINE_TRANSLATION_CPP,
         "R195 CURRENT times next-stage texture expression"),
        ("premodulateColor = stage.colorOp == D3DTOP_PREMODULATE;",
         PIPELINE_TRANSLATION_CPP,
         "R195 color-chain PREMODULATE propagation"),
        ("premodulateAlpha = stage.alphaOp == D3DTOP_PREMODULATE;",
         PIPELINE_TRANSLATION_CPP,
         "R195 alpha-chain PREMODULATE propagation"),
        ("premodulateStages[0].colorOp = D3DTOP_PREMODULATE;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R195 hosted color PREMODULATE fixture"),
        ("premodulateStages[0].alphaOp = D3DTOP_PREMODULATE;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R195 hosted alpha PREMODULATE fixture"),
        ("float3 nextColor = (current * sampled1).rgb;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R195 generated color CURRENT premultiplication assertion"),
        ("float nextAlpha = (current * sampled1).a;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R195 generated alpha CURRENT premultiplication assertion"),
        ("R195 PREMODULATE implicit next-stage texture dependency must fail closed when inexact",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R195 implicit texture exactness guard"),
        ("R195 PREMODULATE must leave next-stage CURRENT unchanged when no texture is bound",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R195 no-texture semantic guard"),
        ("R195 D3DTOP_PREMODULATE fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R195 offline compile assertion"),
        ("DX11 fixed-function PREMODULATE stage-chain support R195: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R195 hosted probe completion"),
    ]
    missing_r195_d3dtop_premodulate = [
        meaning
        for token, source, meaning in r195_d3dtop_premodulate_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_PREMODULATE:") < 3:
        missing_r195_d3dtop_premodulate.append(
            "R195 PREMODULATE must participate in dependency, HLSL and readiness switches")
    if missing_r195_d3dtop_premodulate:
        raise SystemExit(
            "DX11 R195 fixed-function D3DTOP_PREMODULATE contract drift: "
            + ", ".join(missing_r195_d3dtop_premodulate)
        )


    r196_d3dtop_lerp_arg0_contract = [
        ("case D3DTOP_LERP:", PIPELINE_TRANSLATION_CPP,
         "R196 LERP dependency/current/HLSL/readiness cases"),
        ('return first + " * " + proportion + " + " + second +',
         PIPELINE_TRANSLATION_CPP,
         "R196 Arg1*Arg0 + Arg2*(1-Arg0) HLSL expression"),
        ("lerpStages[0].colorOp = D3DTOP_LERP;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R196 hosted LERP color fixture"),
        ("lerpStages[0].alphaOp = D3DTOP_LERP;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R196 hosted LERP alpha fixture"),
        ("lerpStages[0].colorArg0 = D3DTA_TEXTURE;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R196 COLORARG0 interpolation-proportion fixture"),
        ("R196 D3DTOP_LERP ARG0 texture dependency must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R196 ARG0 resource coverage guard"),
        ("unsupportedLerpArg0[0].colorArg0 = invalidArgumentSelector;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R196 invalid ARG0 selector fixture must not reuse supported TEMP"),
        ("R196 D3DTOP_LERP unsupported ARG0 selector must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R196 ARG0 selector guard"),
        ("R196 D3DTOP_LERP fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R196 offline compile assertion"),
        ("DX11 fixed-function D3DTOP_LERP ARG0 support R196: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R196 hosted probe completion"),
    ]
    missing_r196_d3dtop_lerp_arg0 = [
        meaning
        for token, source, meaning in r196_d3dtop_lerp_arg0_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("case D3DTOP_LERP:") < 4:
        missing_r196_d3dtop_lerp_arg0.append(
            "R196 LERP must participate in texture dependency, CURRENT dependency, HLSL and readiness switches")
    if missing_r196_d3dtop_lerp_arg0:
        raise SystemExit(
            "DX11 R196 fixed-function D3DTOP_LERP ARG0 contract drift: "
            + ", ".join(missing_r196_d3dtop_lerp_arg0)
        )

    r197_d3dta_constant_contract = [
        ("DWORD stageConstant = 0xFFFFFFFFu;", PIPELINE_TRANSLATION_HPP,
         "R197 per-stage D3DTSS_CONSTANT identity and D3D9 default"),
        ("case D3DTA_CONSTANT:", PIPELINE_TRANSLATION_CPP,
         "R197 D3DTA_CONSTANT HLSL argument translation"),
        ("stage.stageConstant", PIPELINE_TRANSLATION_CPP,
         "R197 stage constant handoff into generated color/alpha expressions"),
        ("observeTextureStageState(D3DTSS_CONSTANT, out.stageConstant);",
         RUNTIME_CENSUS, "R197 live D3DTSS_CONSTANT observation"),
        ("hash = hash_mix(hash, stage.stageConstant);",
         RUNTIME_CENSUS, "R197 per-stage constant census identity"),
        ("VR DX11 R197 ffp signature#{}", RUNTIME_CENSUS,
         "R197 detailed per-stage constant census evidence"),
        ("stageConstantStages[0].stageConstant = 0x80402010u;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R197 first hosted stage constant fixture"),
        ("stageConstantStages[1].stageConstant = 0xFF102030u;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R197 second hosted stage constant fixture"),
        ("stageConstantStages[1].minFilter = D3DTEXF_POINT;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R197 two-stage fixture uses a supported stage-1 minification filter"),
        ("stageConstantStages[1].magFilter = D3DTEXF_POINT;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R197 two-stage fixture uses a supported stage-1 magnification filter"),
        ("R197 D3DTSS_CONSTANT must preserve independent per-stage ARGB values",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R197 per-stage constant isolation assertion"),
        ("R197 D3DTA_CONSTANT fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R197 offline compile assertion"),
        ("DX11 fixed-function D3DTA_CONSTANT per-stage support R197: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R197 hosted probe completion"),
    ]
    missing_r197_d3dta_constant = [
        meaning
        for token, source, meaning in r197_d3dta_constant_contract
        if token not in source
    ]
    if PIPELINE_TRANSLATION_CPP.count("stage.stageConstant") < 2:
        missing_r197_d3dta_constant.append(
            "R197 stage constant must feed both generated color and alpha expressions")
    if missing_r197_d3dta_constant:
        raise SystemExit(
            "DX11 R197 D3DTA_CONSTANT contract drift: "
            + ", ".join(missing_r197_d3dta_constant)
        )


    r198_d3dta_specular_contract = [
        ("case D3DTA_SPECULAR:", PIPELINE_TRANSLATION_CPP,
         "R198 D3DTA_SPECULAR selector acceptance"),
        ('base = "input.specular";', PIPELINE_TRANSLATION_CPP,
         "R198 D3DTA_SPECULAR COLOR1 pixel expression"),
        ('"    float4 specular : COLOR1;\\n";', PIPELINE_TRANSLATION_CPP,
         "R198 pixel COLOR1 input contract"),
        ("out.hasSpecular = (fvf & D3DFVF_SPECULAR) != 0;",
         PIPELINE_TRANSLATION_CPP,
         "R198 FVF SPECULAR ownership"),
        ('"    output.specular = input.specular.bgra;\\n"', PIPELINE_TRANSLATION_CPP,
         "R198 vertex COLOR1 packed BGRA swizzle"),
        ('"    output.specular = float4(1.0f, 1.0f, 1.0f, 1.0f);\\n"',
         PIPELINE_TRANSLATION_CPP,
         "R198 missing-specular opaque-white default"),
        ("bool hasSpecular = false;", PIPELINE_TRANSLATION_HPP,
         "R198 vertex prototype specular identity"),
        ("specularStages[0].colorArg1 = D3DTA_SPECULAR;",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R198 hosted pixel COLOR1 fixture"),
        ("R198 D3DTA_SPECULAR fixed-function shader prototype did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R198 hosted pixel compile assertion"),
        ("D3DFVF_XYZ | D3DFVF_SPECULAR", SHADER_LINKAGE_PROBE,
         "R198 hosted vertex COLOR1 fixture"),
        ("R198 missing SPECULAR FVF must emit documented opaque-white default",
         SHADER_LINKAGE_PROBE,
         "R198 missing-specular default assertion"),
        ("R198 D3DTA_SPECULAR VS/PS COLOR1 interface rejected",
         SHADER_LINKAGE_PROBE,
         "R198 VS/PS COLOR1 reflection linkage"),
        ("DX11 fixed-function D3DTA_SPECULAR support R198: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R198 pixel probe completion"),
        ("DX11 fixed-function SPECULAR COLOR1 linkage R198: PASS",
         SHADER_LINKAGE_PROBE,
         "R198 linkage probe completion"),
    ]
    missing_r198_d3dta_specular = [
        meaning
        for token, source, meaning in r198_d3dta_specular_contract
        if token not in source
    ]
    if missing_r198_d3dta_specular:
        raise SystemExit(
            "DX11 R198 D3DTA_SPECULAR/COLOR1 contract drift: "
            + ", ".join(missing_r198_d3dta_specular)
        )


    # Detailed fixed-function demand evidence must stay coupled to the current
    # dormant translator support set. This prevents a later semantic addition
    # from leaving the census stale and falsely reporting a now-supported op or
    # argument as outstanding conversion demand.
    detailed_ffp_demand_census_contract = [
        ("summarize_fixed_function_detailed_stage_demand(",
         DX11_CENSUS_ANALYZER,
         "detailed fixed-function demand summarizer"),
        ("FFP_SUPPORTED_ARGUMENT_SELECTORS = frozenset({0, 1, 2, 3, 4, 5, 6})",
         DX11_CENSUS_ANALYZER,
         "current DIFFUSE/CURRENT/TEXTURE/TFACTOR/SPECULAR/TEMP/CONSTANT selector set"),
        ("FFP_SUPPORTED_RESULT_ARGS = frozenset({1, 5})",
         DX11_CENSUS_ANALYZER,
         "R200 CURRENT/TEMP result destination support"),
        ("duplicate_stage_records += 1", DX11_CENSUS_ANALYZER,
         "duplicate detailed-stage de-weighting"),
        ('"FixedFunctionDetailedStageDemand": fixed_function_detailed_stage_demand',
         DX11_CENSUS_ANALYZER,
         "report attachment for detailed demand evidence"),
        ('r198_demand["DuplicateDetailedStageRecordsDropped"] == 2',
         DX11_CENSUS_ANALYZER_TEST,
         "duplicate-stage regression fixture"),
        ('{"value": 22, "name": "BUMPENVMAP", "count": 1}',
         DX11_CENSUS_ANALYZER_TEST,
         "unsupported color-op demand fixture"),
        ('{"value": 7, "name": "UNKNOWN", "count": 1}',
         DX11_CENSUS_ANALYZER_TEST,
         "unsupported unknown selector fixture"),
        ('r198_demand["UnsupportedResultArgs"] == [',
         DX11_CENSUS_ANALYZER_TEST,
         "R200-aware invalid result destination fixture"),
        ('{"value": 0, "name": "DIFFUSE", "count": 1}',
         DX11_CENSUS_ANALYZER_TEST,
         "unsupported RESULTARG selector fixture"),
        ('r198_demand["ActivationProof"] is False',
         DX11_CENSUS_ANALYZER_TEST,
         "diagnostic-only activation boundary"),
    ]
    missing_detailed_ffp_demand_census = [
        meaning
        for token, source, meaning in detailed_ffp_demand_census_contract
        if token not in source
    ]
    if missing_detailed_ffp_demand_census:
        raise SystemExit(
            "DX11 detailed fixed-function demand census contract drift: "
            + ", ".join(missing_detailed_ffp_demand_census)
        )

    r201_temp_default_contract = [
        ("case D3DTA_TEMP:", PIPELINE_TRANSLATION_CPP,
         "R200/R201 D3DTA_TEMP selector support"),
        ("stage.resultArg != D3DTA_TEMP", PIPELINE_TRANSLATION_CPP,
         "R201 CURRENT/TEMP result destination gate"),
        ('"    float4 temp = 0.0f;\\n"', PIPELINE_TRANSLATION_CPP,
         "R201 generated HLSL TEMP default-zero register"),
        ('"        temp = float4(nextColor, nextAlpha);\\n"',
         PIPELINE_TRANSLATION_CPP,
         "R200 generated HLSL TEMP write"),
        ("R200 D3DTSS_RESULTARG TEMP write/read chain must become exact",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R200 hosted TEMP write/read fixture"),
        ("R201 default-zero D3DTA_TEMP read must remain exact",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R201 default-zero TEMP readiness fixture"),
        ("R201 default-zero TEMP fixed-function shader did not compile",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R201 default-zero TEMP offline compile assertion"),
        ("DX11 fixed-function TEMP default-zero semantics R201: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE,
         "R201 hosted probe completion"),
        ("RESULTARG-001 default-zero TEMP read must remain exact",
         SEMANTIC_SMOKE,
         "R201 semantic smoke default-zero TEMP readiness"),
        ("RESULTARG-001 default-zero TEMP shader semantics drift",
         SEMANTIC_SMOKE,
         "R201 semantic smoke default-zero TEMP shader dataflow"),
        ("FFP_SUPPORTED_ARGUMENT_SELECTORS = frozenset({0, 1, 2, 3, 4, 5, 6})",
         DX11_CENSUS_ANALYZER,
         "R200 census TEMP selector support"),
        ("FFP_SUPPORTED_RESULT_ARGS = frozenset({1, 5})",
         DX11_CENSUS_ANALYZER,
         "R200 census CURRENT/TEMP destination support"),
        ('r198_demand["UnsupportedResultArgs"] == [',
         DX11_CENSUS_ANALYZER_TEST,
         "R200 census invalid RESULTARG separation"),
    ]
    missing_r201_temp_default = [
        meaning
        for token, source, meaning in r201_temp_default_contract
        if token not in source
    ]
    if "bool tempAvailable = false;" in PIPELINE_TRANSLATION_CPP:
        missing_r201_temp_default.append(
            "R201 TEMP default-zero read must not depend on a prior write")
    if "fixed_function_op_uses_temp_argument(" in PIPELINE_TRANSLATION_CPP:
        missing_r201_temp_default.append(
            "R201 obsolete TEMP-before-write dependency classifier must be removed")
    if PIPELINE_TRANSLATION_CPP.count("case D3DTA_TEMP:") < 2:
        missing_r201_temp_default.append(
            "R200/R201 TEMP must participate in selector validation and HLSL translation")
    if missing_r201_temp_default:
        raise SystemExit(
            "DX11 R201 fixed-function TEMP default contract drift: "
            + ", ".join(missing_r201_temp_default)
        )

    # R166 makes the enum-owned one-past-last sentinel the census authority.
    # The concrete unsupported bits must stay contiguous, the sentinel must be
    # max(bit)+1, and runtime_census must size its array from that sentinel.
    pipeline_unsupported_bits = sorted({
        int(bit)
        for bit in re.findall(
            r"PipelineUnsupported[A-Za-z0-9_]+\s*=\s*1u\s*<<\s*(\d+)",
            PIPELINE_TRANSLATION_HPP)
    })
    pipeline_bit_count_match = re.search(
        r"PipelineUnsupportedBitCount\s*=\s*(\d+)u?\s*,",
        PIPELINE_TRANSLATION_HPP)
    expected_pipeline_bits = (
        list(range(pipeline_unsupported_bits[-1] + 1))
        if pipeline_unsupported_bits else []
    )
    r166_unsupported_census_errors = []
    if pipeline_unsupported_bits != expected_pipeline_bits:
        r166_unsupported_census_errors.append(
            "PipelineUnsupported bits must remain contiguous from bit 0")
    if (not pipeline_bit_count_match or
            int(pipeline_bit_count_match.group(1)) != len(pipeline_unsupported_bits)):
        r166_unsupported_census_errors.append(
            "PipelineUnsupportedBitCount must equal max concrete bit + 1")
    if "static_cast<std::size_t>(PipelineUnsupportedBitCount)" not in RUNTIME_CENSUS:
        r166_unsupported_census_errors.append(
            "runtime census must size UnsupportedBitCount from the enum sentinel")
    for token, meaning in [
        ("DX11 R166 unsupported census sentinel out of range",
         "compile-time sentinel bounds assertion"),
        ("dualSource={},shadeMode={},clipping={},depthBias={},vertexBlend={},dither={},texCoordWrap={},mrtColorWrite={},specular={}",
         "current log labels for bits 12..20"),
        ("unsupported[12], unsupported[13], unsupported[14], unsupported[15],",
         "R165/R166 log arguments for bits 12..15"),
        ("unsupported[16], unsupported[17], unsupported[18],",
         "current log argument prefix for bits 16..20"),
        ("unsupported[19], unsupported[20]);",
         "R204 MRT/specular log arguments for bits 19..20"),
    ]:
        if token not in RUNTIME_CENSUS:
            r166_unsupported_census_errors.append(meaning)
    if r166_unsupported_census_errors:
        raise SystemExit(
            "DX11 R166 unsupported census sentinel drift: "
            + ", ".join(r166_unsupported_census_errors)
        )

    r162_shade_mode_contract = [
        ("DWORD shadeMode = D3DSHADE_GOURAUD;", D3D9_DRAW_STATE_HPP,
         "R162 tracked shade-mode field and Gouraud default"),
        ("read(D3DRS_SHADEMODE, out.shadeMode);", D3D9_RENDER_STATE_CAPTURE,
         "R162 live shade-mode capture"),
        ("PipelineUnsupportedShadeMode = 1u << 13", PIPELINE_TRANSLATION_HPP,
         "R162 dedicated unsupported shade-mode bit"),
        ("source.shadeMode != D3DSHADE_GOURAUD", PIPELINE_TRANSLATION_CPP,
         "R162 non-Gouraud fail-closed predicate"),
        ("out.unsupported |= PipelineUnsupportedShadeMode;",
         PIPELINE_TRANSLATION_CPP, "R162 pipeline readiness blocker"),
        ("R162 Gouraud shade mode remains exact", FIXED_FUNCTION_PIPELINE_PROBE,
         "R162 Gouraud positive fixture"),
        ("R162 flat shade mode remains fail closed", FIXED_FUNCTION_PIPELINE_PROBE,
         "R162 FLAT negative fixture"),
        ("R162 shader handoff retains flat shade blocker",
         FIXED_FUNCTION_PIPELINE_PROBE, "R162 ownership handoff negative fixture"),
        ("R162 phong shade mode remains fail closed", FIXED_FUNCTION_PIPELINE_PROBE,
         "R162 PHONG negative fixture"),
        ("DX11 fixed-function shade-mode fail-closed R162: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R162 hosted probe completion marker"),
        ("bool shadeModeObservationComplete{};", RUNTIME_CENSUS,
         "R162 census shade observation-completeness identity"),
        ("DWORD shadeMode = D3DSHADE_GOURAUD;", RUNTIME_CENSUS,
         "R162 census shade-mode identity"),
        ("hash, sig.shadeModeObservationComplete ? 1u : 0u", RUNTIME_CENSUS,
         "R162 census shade completeness hash"),
        ("hash = hash_mix(hash, sig.shadeMode);", RUNTIME_CENSUS,
         "R162 census shade-mode hash"),
        ("signature.shadeMode = source.shadeMode;", RUNTIME_CENSUS,
         "R162 captured shade-mode propagation"),
    ]
    missing_r162_shade_mode = [
        meaning
        for token, source, meaning in r162_shade_mode_contract
        if token not in source
    ]
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_SHADEMODE") < 2:
        missing_r162_shade_mode.append(
            "R162 SHADEMODE must be both primed and captured")
    if missing_r162_shade_mode:
        raise SystemExit(
            "DX11 R162 shade-mode contract drift: "
            + ", ".join(missing_r162_shade_mode)
        )

    r163_vertex_blend_contract = [
        ("DWORD vertexBlend = D3DVBF_DISABLE;", D3D9_DRAW_STATE_HPP,
         "R163 tracked vertex-blend mode and disabled default"),
        ("DWORD indexedVertexBlendEnable = FALSE;", D3D9_DRAW_STATE_HPP,
         "R163 tracked indexed vertex-blend default"),
        ("read(D3DRS_VERTEXBLEND, out.vertexBlend);",
         D3D9_RENDER_STATE_CAPTURE, "R163 live vertex-blend capture"),
        ("read(D3DRS_INDEXEDVERTEXBLENDENABLE, out.indexedVertexBlendEnable);",
         D3D9_RENDER_STATE_CAPTURE, "R163 live indexed-blend capture"),
        ("PipelineUnsupportedVertexBlend = 1u << 16",
         PIPELINE_TRANSLATION_HPP, "R163 dedicated vertex-blend blocker"),
        ("source.vertexBlend != D3DVBF_DISABLE ||", PIPELINE_TRANSLATION_CPP,
         "R163 non-default vertex-blend predicate"),
        ("source.indexedVertexBlendEnable != FALSE", PIPELINE_TRANSLATION_CPP,
         "R163 indexed vertex-blend predicate"),
        ("out.unsupported |= PipelineUnsupportedVertexBlend;",
         PIPELINE_TRANSLATION_CPP, "R163 pipeline readiness blocker"),
        ("R163 disabled vertex blending must remain exact",
         FIXED_FUNCTION_PIPELINE_PROBE, "R163 default positive fixture"),
        ("R163 weighted vertex blending must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "R163 weighted-blend negative fixture"),
        ("R163 indexed vertex blending must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "R163 indexed-blend negative fixture"),
        ("R163 fixed-function handoff must retain vertex-blend blocker",
         FIXED_FUNCTION_PIPELINE_PROBE, "R163 ownership handoff fixture"),
        ("DX11 fixed-function vertex-blend fail-closed R163: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R163 hosted probe completion marker"),
        ("bool vertexBlendObservationComplete{};", RUNTIME_CENSUS,
         "R163 census vertex-blend observation identity"),
        ("DWORD vertexBlend = D3DVBF_DISABLE;", RUNTIME_CENSUS,
         "R163 census vertex-blend mode identity"),
        ("DWORD indexedVertexBlendEnable = FALSE;", RUNTIME_CENSUS,
         "R163 census indexed-blend identity"),
        ("hash, sig.vertexBlendObservationComplete ? 1u : 0u",
         RUNTIME_CENSUS, "R163 census observation hash"),
        ("hash = hash_mix(hash, sig.vertexBlend);", RUNTIME_CENSUS,
         "R163 census vertex-blend hash"),
        ("hash = hash_mix(hash, sig.indexedVertexBlendEnable);",
         RUNTIME_CENSUS, "R163 census indexed-blend hash"),
        ("signature.vertexBlend = source.vertexBlend;", RUNTIME_CENSUS,
         "R163 captured vertex-blend propagation"),
        ("signature.indexedVertexBlendEnable = source.indexedVertexBlendEnable;",
         RUNTIME_CENSUS, "R163 captured indexed-blend propagation"),
    ]
    missing_r163_vertex_blend = [
        meaning
        for token, source, meaning in r163_vertex_blend_contract
        if token not in source
    ]
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_VERTEXBLEND") < 2:
        missing_r163_vertex_blend.append(
            "R163 VERTEXBLEND must be both primed and captured")
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_INDEXEDVERTEXBLENDENABLE") < 2:
        missing_r163_vertex_blend.append(
            "R163 INDEXEDVERTEXBLENDENABLE must be both primed and captured")
    if missing_r163_vertex_blend:
        raise SystemExit(
            "DX11 R163 vertex-blend contract drift: "
            + ", ".join(missing_r163_vertex_blend)
        )

    r161_clipping_contract = [
        ("DWORD clipping = TRUE;", D3D9_DRAW_STATE_HPP,
         "R161 tracked D3D9 clipping field and default"),
        ("DWORD clipPlaneEnable = 0;", D3D9_DRAW_STATE_HPP,
         "R161 tracked user clip-plane enable mask"),
        ("read(D3DRS_CLIPPING, out.clipping);", D3D9_RENDER_STATE_CAPTURE,
         "R161 live clipping capture"),
        ("read(D3DRS_CLIPPLANEENABLE, out.clipPlaneEnable);",
         D3D9_RENDER_STATE_CAPTURE, "R161 live clip-plane mask capture"),
        ("PipelineUnsupportedClipping = 1u << 14", PIPELINE_TRANSLATION_HPP,
         "R161 dedicated clipping unsupported bit"),
        ("source.clipping == FALSE || source.clipPlaneEnable != 0u",
         PIPELINE_TRANSLATION_CPP, "R161 non-equivalent clipping predicate"),
        ("out.unsupported |= PipelineUnsupportedClipping;",
         PIPELINE_TRANSLATION_CPP, "R161 pipeline readiness blocker"),
        ("R161 default D3D9 clipping must remain exact",
         FIXED_FUNCTION_PIPELINE_PROBE, "R161 default positive fixture"),
        ("R161 disabled D3D9 clipping must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "R161 clipping-disable negative fixture"),
        ("R161 enabled D3D9 user clip plane must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "R161 user-plane negative fixture"),
        ("R161 fixed-function shader handoff must retain clipping blocker",
         FIXED_FUNCTION_PIPELINE_PROBE, "R161 ownership handoff negative fixture"),
        ("DX11 fixed-function clipping fail-closed R161: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "R161 hosted probe completion marker"),
    ]
    missing_r161_clipping = [
        meaning
        for token, source, meaning in r161_clipping_contract
        if token not in source
    ]
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_CLIPPING") < 2:
        missing_r161_clipping.append(
            "R161 CLIPPING must be both primed and captured")
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_CLIPPLANEENABLE") < 2:
        missing_r161_clipping.append(
            "R161 CLIPPLANEENABLE must be both primed and captured")
    if missing_r161_clipping:
        raise SystemExit(
            "DX11 R161 clipping contract drift: "
            + ", ".join(missing_r161_clipping)
        )

    # Fail closed on partial dormant-readiness API commits. Direct-chat lanes
    # intentionally stage many compose/validate/observe/bind helpers, and a
    # header-only or cpp-only step can otherwise survive until a later link or
    # caller exposes it. Keep the public native fixed-function API and its
    # concrete implementation one-to-one on every source-graph pass.
    native_api_pattern = re.compile(
        r"^(?:\[\[nodiscard\]\]\s+)?"
        r"(?:[A-Za-z_][A-Za-z0-9_:<>,*& \t]*\s+)?"
        r"((?:compose|validate|observe|bind)_fixed_function_[A-Za-z0-9_]+)"
        r"\s*\(",
        re.MULTILINE,
    )
    native_definition_pattern = re.compile(
        r"^(?:[A-Za-z_][A-Za-z0-9_:<>,*& \t]*\s+)?"
        r"((?:compose|validate|observe|bind)_fixed_function_[A-Za-z0-9_]+)"
        r"\s*\(",
        re.MULTILINE,
    )
    declared_native_apis = Counter(native_api_pattern.findall(NATIVE_BACKEND_HPP))
    defined_native_apis = Counter(
        native_definition_pattern.findall(NATIVE_BACKEND_CPP)
    )
    missing_native_definitions = sorted(
        set(declared_native_apis) - set(defined_native_apis)
    )
    undeclared_native_definitions = sorted(
        set(defined_native_apis) - set(declared_native_apis)
    )
    duplicate_native_declarations = sorted(
        name for name, count in declared_native_apis.items() if count != 1
    )
    duplicate_native_definitions = sorted(
        name for name, count in defined_native_apis.items() if count != 1
    )
    if (
        missing_native_definitions
        or undeclared_native_definitions
        or duplicate_native_declarations
        or duplicate_native_definitions
    ):
        raise SystemExit(
            "DX11 native readiness API declaration/definition drift: "
            f"missing_defs={missing_native_definitions}; "
            f"undeclared_defs={undeclared_native_definitions}; "
            f"duplicate_decls={duplicate_native_declarations}; "
            f"duplicate_defs={duplicate_native_definitions}"
        )

    cpp_files = sorted(path.relative_to(ROOT).as_posix() for path in DX11.glob("*.cpp"))
    missing = [path for path in cpp_files if f'"{path}"' not in CMAKE]
    if missing:
        raise SystemExit(
            "DX11 checked-in CMake source graph omits translation units: "
            + ", ".join(missing)
        )

    required = {
        "src/vr/d3d11/native_backend.cpp",
        "src/vr/d3d11/native_shared_eye_ring.cpp",
        "src/vr/d3d11/pipeline_translation.cpp",
        "src/vr/d3d11/resource_translation.cpp",
        "src/vr/d3d11/runtime_census.cpp",
        "src/vr/d3d11/startup_census.cpp",
        "src/vr/d3d11/state_translation.cpp",
    }
    absent = sorted(required - set(cpp_files))
    if absent:
        raise SystemExit(
            "DX11 required translation/census source is absent from repository: "
            + ", ".join(absent)
        )

    if "python tools/verify_dx11_dual_source_contract.py" not in BACKEND_GATE:
        raise SystemExit(
            "DX11 backend conversion gate omits dual-source blend contract validator"
        )

    census = (DX11 / "runtime_census.cpp").read_text(encoding="utf-8")
    pipeline_header = (DX11 / "pipeline_translation.hpp").read_text(encoding="utf-8")
    pipeline_translation = (DX11 / "pipeline_translation.cpp").read_text(
        encoding="utf-8"
    )
    pipeline_contract_text = pipeline_header + "\n" + pipeline_translation
    input_layout_contract = {
        "VertexInputLayoutTranslation": "R78 canonical input-layout result",
        "translate_vertex_input_layout": "D3D9 declaration to D3D11 layout classifier",
        "D3DDECLMETHOD_DEFAULT": "non-default declaration method fail-closed gate",
        "D3D11_INPUT_PER_VERTEX_DATA": "per-vertex slot classification",
        "DXGI_FORMAT_R32G32B32_FLOAT": "FLOAT3 layout mapping",
        "DXGI_FORMAT_B8G8R8A8_UNORM": "D3DCOLOR layout mapping",
        "D3DFVF_XYZRHW": "FVF transformed-position mapping",
        "D3DFVF_TEXCOORDSIZE4": "FVF texture-coordinate width mapping",
        "fvfPath": "R79 explicit FVF path identity",
        "XYZB1..XYZB5": "FVF blend encodings remain fail-closed",
        "fvfPending": "unsupported FVF path remains explicitly pending",
        "FixedFunctionTranslationReadiness": "R82 conservative F20 readiness result",
        "translate_fixed_function_readiness": "R82 fixed-function readiness classifier",
        "FixedFunctionUnsupportedResourceStageCoverage": "R82/R83 texture-using stage requires exact bound resource",
        "textureResourcePresentMask": "R83 readiness receives bound texture-stage mask",
        "textureResourceExactMask": "R83 readiness receives exact texture-stage mask",
        "D3DTOP_MODULATE": "R82 conservative fixed-function op subset",
        "D3DTA_SELECTMASK": "R82 conservative texture-argument subset",
        "D3DTTFF_DISABLE": "R82 texture transforms remain fail closed",
        "FixedFunctionPixelShaderPrototype": "R84 diagnostic-only generated pixel-shader source",
        "generate_fixed_function_pixel_shader_prototype": "R84 ready-state source generator",
        "FixedFunctionShaderPrototypeUnsupportedNotReady": "R84 readiness fail-closed generator gate",
        "FixedFunctionShaderPrototypeUnsupportedResourceType": "R84 2D-texture-only prototype gate",
        "Texture2D texture": "R84 HLSL texture declarations",
        "SamplerState sampler": "R84 HLSL sampler declarations",
        "SV_Target": "R84 HLSL pixel-shader output",
        "hash_shader_source": "R84 deterministic generated-source fingerprint",
        "FixedFunctionPixelShaderCompileProbe": "R85 non-routing compiler probe result",
        "compile_fixed_function_pixel_shader_prototype": "R85 offline compiler probe",
        "D3DCompile": "R85 HLSL compiler acceptance probe",
        "ps_4_0": "R85 diagnostic compiler target",
        "D3DCOMPILE_ENABLE_STRICTNESS": "R85 strict compiler acceptance",
        "D3DTEXF_LINEAR": "R82 point/linear sampler filter subset",
        "D3DTADDRESS_CLAMP": "R82 wrap/clamp address subset",
    }
    missing_input_layout_contract = [
        meaning
        for token, meaning in input_layout_contract.items()
        if token not in pipeline_contract_text
    ]
    if missing_input_layout_contract:
        raise SystemExit(
            "DX11 R78 input-layout translation drift: "
            + ", ".join(missing_input_layout_contract)
        )

    census_contract = {
        "resourceIntrospectionComplete": "sample-level fail-closed resource observation",
        "ResourceIntrospectionFailureSamples": "durable failure counter",
        "sig.resourceIntrospectionComplete ? 1u : 0u": "R217 resource-introspection completeness participates in sampled signature identity",
        "resourceBehaviorDescriptorExact": "R219 per-signature resource descriptor behavior readiness",
        "resourceMutationTelemetryRequired": "R219 per-signature mutation telemetry blocker",
        "resourceManagedShadowRequired": "R219 per-signature managed-shadow blocker",
        "resourceBehaviorExact": "R219 explicit F18 resource-behavior exactness gate",
        "sig.resourceBehaviorExact ? 1u : 0u": "R219 resource behavior participates in sampled signature identity",
        "bool resourcesExact = signature.resourceIntrospectionComplete;": "exactness starts from observation completeness",
        "if (!signature.resourceIntrospectionComplete)": "durable failure accounting gate",
        "if (unsupported == PipelineUnsupportedNone && topology.exact &&": "pipeline/topology exact-sample gate",
        "GetStreamSource": "vertex-buffer observation",
        "GetRenderTarget": "render-target observation",
        "GetDepthStencilSurface": "depth observation",
        "GetIndices": "index-buffer observation",
        "GetTexture": "texture observation",
        "std::array<TextureStageResourceState, 8>": "R83 all eight texture-resource stages",
        "textureResourcePresentMask": "R83 bound texture-stage mask",
        "textureResourceExactMask": "R83 exact texture-stage mask",
        "TextureStageBoundResources": "R83 bound texture-stage evidence",
        "TextureStageExactResources": "R83 exact texture-stage evidence",
        "TextureStagePendingResources": "R83 pending texture-stage evidence",
        "inputLayoutExact": "R78 sample-level input-layout readiness",
        "InputLayoutExactSamples": "R78 exact layout evidence counter",
        "InputLayoutUnsupportedSamples": "R78/R79 unsupported layout evidence counter",
        "InputLayoutFvfExactSamples": "R79 exact FVF layout evidence counter",
        "InputLayoutFvfPendingSamples": "R79 unsupported FVF blocker counter",
        "signature.fixedFunction &&\n            signature.fixedFunctionStateCoverageExact &&\n            signature.fixedFunctionTranslationReady &&\n            signature.resourceBehaviorExact &&\n            resourcesExact && inputLayoutExact &&\n            signature.outputStateObservationComplete &&\n            signature.shaderReadinessExact &&\n            shaderCompileReadinessExact &&\n            signature.shaderTranslationExact": "R219/R220/R222 final ExactSamples preserves resource, FFP, shader-scope and compile-readiness gates",
        "translate_vertex_input_layout": "R78 runtime declaration classifier",
        "GetVertexShader": "vertex shader observation",
        "GetPixelShader": "pixel shader observation",
        "GetFunction": "shader bytecode fingerprint observation",
        "ShaderIntrospectionFailureSamples": "shader introspection failure counter",
        "ShaderMixedPairSamples": "mixed VS/PS fail-closed counter",
        "ShaderFixedFunctionPendingSamples": "fixed-function F20 dependency counter",
        "ShaderProgrammablePendingSamples": "programmable F21 dependency counter",
        "std::array<FixedFunctionStageState, 8>": "R81/R82 all eight fixed-function texture stages",
        "D3DSAMP_MINFILTER": "R81 per-stage sampler min filter observation",
        "D3DSAMP_MAGFILTER": "R81 per-stage sampler mag filter observation",
        "D3DSAMP_MIPFILTER": "R81 per-stage sampler mip filter observation",
        "D3DSAMP_MIPMAPLODBIAS": "R125 per-stage sampler MIP LOD bias observation",
        "D3DSAMP_MAXMIPLEVEL": "R125 per-stage sampler most-detailed-mip observation",
        "D3DSAMP_ADDRESSU": "R81 per-stage sampler U addressing observation",
        "D3DSAMP_ADDRESSV": "R81 per-stage sampler V addressing observation",
        "D3DSAMP_SRGBTEXTURE": "sampler sRGB decode provenance observation",
        "fixedFunctionStateCoverageExact": "R81 fixed-function coverage readiness evidence",
        "FixedFunctionStateCoverageExactSamples": "R81 complete FFP observation counter",
        "FixedFunctionStateCoverageFailureSamples": "R81 failed FFP observation counter",
        "FixedFunctionTranslationReadySamples": "R82 conservative F20 readiness counter",
        "FixedFunctionTranslationPendingSamples": "R82 fail-closed F20 pending counter",
        "translate_fixed_function_readiness": "R82 runtime readiness classifier use",
        "fixedFunctionTranslationUnsupported": "R82 readiness reason mask evidence",
        "FixedFunctionShaderPrototypeGeneratedSamples": "R84 generated-source counter",
        "FixedFunctionShaderPrototypePendingSamples": "R84 pending-source counter",
        "fixedFunctionShaderPrototypeHash": "R84 generated-source hash evidence",
        "generate_fixed_function_pixel_shader_prototype": "R84 runtime source-generation evidence",
        "FixedFunctionShaderCompileSucceededSignatures": "R85 successful unique-signature compile probes",
        "FixedFunctionShaderCompileFailedSignatures": "R85 failed unique-signature compile probes",
        "FixedFunctionShaderCompileSkippedSignatureCap": "R221 signature-hash-cap compile coverage evidence",
        "compile_fixed_function_pixel_shader_prototype": "R85 census compiler probe invocation",
        "SignatureHashCap = 512u": "R114 bounded unique-signature hash cap",
        "DetailedSignatureLogCap = 64u": "R114 bounded detailed-signature log cap",
        "SignatureHashCapHitSamples": "R114 signature hash-cap saturation evidence",
        "DetailedSignatureLogSkippedSignatures": "R114 detailed-log saturation evidence",
        "mix_sample_ordinal": "R114 hashed draw-ordinal sampler",
        "(sampleKey & (sampleStride - 1u)) != 0u": "R114 hashed sampled-mode gate",
        "sampleStride > 1u": "R114 exhaustive-mode sampling bypass gate",
        "FixedFunctionPipelineShaderExactSamples": "R120 fixed-function pipeline/shader exact census counter",
        "FixedFunctionPipelineShaderPendingSamples": "R120 fixed-function pipeline/shader pending census counter",
        "FixedFunctionAlphaTestShaderOwnedSamples": "R120 shader-owned alpha-test census counter",
        "fixedFunctionPipelineShaderExact": "R120 per-signature handoff readiness",
        "fixedFunctionPipelineShaderUnsupported": "R120 per-signature reconciled render-state mask",
        "fixedFunctionAlphaTestOwnedByPixelShader": "R120 per-signature alpha-test ownership evidence",
        "translate_fixed_function_pipeline_with_shader_semantics": "R120 consumes the R118 fixed-function handoff",
        "pipelineShader.renderStates.unsupported": "R120 records reconciled fixed-function render-state blockers",
        "const auto& shaderPrototype = pipelineShader.pixelShader": "R120 uses the reconciled pixel-shader prototype",
        "ffpPipelineShader[exact={},pending={},alphaTestOwned={}]": "R120 summary telemetry",
        "shaderTranslationExact = false": "native shader translation remains fail-closed",
    }
    if "(++stride % SampleStride)" in census:
        raise SystemExit(
            "DX11 R114 fixed-phase modulo sampler must not reappear"
        )

    missing_contract = [
        meaning for token, meaning in census_contract.items() if token not in census
    ]
    if missing_contract:
        raise SystemExit(
            "DX11 resource observation contract drift: " + ", ".join(missing_contract)
        )

    resource_translation = (DX11 / "resource_translation.cpp").read_text(
        encoding="utf-8"
    )
    resource_header = (DX11 / "resource_translation.hpp").read_text(
        encoding="utf-8"
    )
    resource_translation_contract = resource_translation + "\n" + resource_header
    resource_contract = {
        "ResourceBehaviorRules": "explicit VB/IB/texture/RT/depth behavior table",
        "ResourceMirrorLifetime::DeviceGeneration": "default-pool reset lifetime",
        "ResourceMirrorLifetime::ManagedCpuShadow": "managed-pool CPU shadow lifetime",
        "D3D11_BIND_VERTEX_BUFFER": "vertex-buffer mirror role",
        "D3D11_BIND_INDEX_BUFFER": "index-buffer mirror role",
        "D3D11_BIND_SHADER_RESOURCE": "texture mirror role",
        "D3D11_BIND_RENDER_TARGET": "render-target mirror role",
        "D3D11_BIND_DEPTH_STENCIL": "depth mirror role",
        "requiresMutationTelemetry": "lock/update evidence blocker",
        "requiresCpuShadow": "managed Reset-survival blocker",
        "BufferMutationUpdateKind": "explicit VB/IB mutation update plan",
        "translate_buffer_mutation": "Lock flag to D3D11 update classifier",
        "D3D11_MAP_WRITE_DISCARD": "dynamic DISCARD map semantics",
        "D3D11_MAP_WRITE_NO_OVERWRITE": "dynamic NOOVERWRITE map semantics",
        "DefaultUpdateSubresource": "default-usage update semantics",
        "ManagedCpuShadowRead": "managed read shadow dependency",
        "ManagedCpuShadowWrite": "managed write shadow dependency",
        "ManagedMirrorLifetimeState": "managed mirror lifetime state machine",
        "note_managed_shadow_write": "managed CPU-shadow version transition",
        "note_managed_mirror_upload": "managed mirror upload transition",
        "advance_managed_device_generation": "Reset generation transition",
        "managed_mirror_ready": "generation/version readiness gate",
        "static_assert": "compile-time managed lifetime transition checks",
    }
    missing_resource_contract = [
        meaning
        for token, meaning in resource_contract.items()
        if token not in resource_translation_contract
    ]
    if missing_resource_contract:
        raise SystemExit(
            "DX11 R73 resource behavior contract drift: "
            + ", ".join(missing_resource_contract)
        )

    a2b10g10r10_resource_contract = [
        ("case D3DFMT_A2B10G10R10:", resource_translation,
         "A2B10G10R10 exact source-format case"),
        ("DXGI_FORMAT_R10G10B10A2_UNORM", resource_translation,
         "A2B10G10R10 exact DXGI packed-format mapping"),
        ("translate_resource_format(\n        D3DFMT_A2B10G10R10",
         CONSTANT_BUFFER_PROBE, "A2B10G10R10 hosted positive probe"),
        ("D3DFMT_A2R10G10B10, ResourceRole::Texture",
         CONSTANT_BUFFER_PROBE, "A2R10G10B10 fail-closed contrast probe"),
        ("DX11 resource A2B10G10R10 exact mapping: PASS",
         CONSTANT_BUFFER_PROBE, "resource-format hosted probe completion"),
    ]
    missing_a2b10g10r10_resource_contract = [
        meaning
        for token, source, meaning in a2b10g10r10_resource_contract
        if token not in source
    ]
    if "case D3DFMT_A2R10G10B10:" in resource_translation:
        missing_a2b10g10r10_resource_contract.append(
            "A2R10G10B10 must remain fail-closed without an exact DXGI mapping")
    if missing_a2b10g10r10_resource_contract:
        raise SystemExit(
            "DX11 A2B10G10R10 resource-format contract drift: "
            + ", ".join(missing_a2b10g10r10_resource_contract)
        )

    r121_managed_buffer_mutation_plan_contract = {
        "R121: the CPU-shadow/reset-generation implementation now makes":
            "R121 managed-buffer plan exactness rationale",
        "out.planExact = true;":
            "R121 exact managed-buffer mutation plan",
        "out.requiresCpuShadow = true;":
            "R121 CPU-shadow requirement remains explicit",
    }
    missing_r121_managed_buffer_plan = [
        meaning
        for token, meaning in r121_managed_buffer_mutation_plan_contract.items()
        if token not in resource_translation
    ]
    r121_managed_buffer_probe_contract = {
        "R121 managed VB write is an exact CPU-shadow mutation plan":
            "R121 managed write positive probe",
        "R121 managed IB read is an exact CPU-shadow mutation plan":
            "R121 managed read positive probe",
        "R121 managed DISCARD remains fail-closed":
            "R121 managed DISCARD negative probe",
        "R121 managed NOOVERWRITE remains fail-closed":
            "R121 managed NOOVERWRITE negative probe",
    }
    missing_r121_managed_buffer_plan += [
        meaning
        for token, meaning in r121_managed_buffer_probe_contract.items()
        if token not in CONSTANT_BUFFER_PROBE
    ]
    r125_managed_buffer_exact_consumer_contract = {
        "R125: R121 made ordinary MANAGED buffer mutation plans exact.":
            "R125 exact-plan consumer rationale",
        "!mutation.requiresCpuShadow || !mutation.planExact":
            "R125 managed-buffer shadow requires the exact R121 plan",
        "R119 mirror readiness still independently rejects stale snapshots.":
            "R125 stale-readiness boundary remains explicit",
    }
    missing_r121_managed_buffer_plan += [
        meaning
        for token, meaning in r125_managed_buffer_exact_consumer_contract.items()
        if token not in NATIVE_BACKEND_CPP
    ]
    r127_managed_buffer_readiness_contract = {
        "bool mutationPlanExact{};":
            "R127 per-resource mutation-plan readiness bit",
        "out.mutationPlanExact =":
            "R127 managed-buffer readiness computes mutation-plan exactness",
        "out.descriptorExact &&\n        out.mutationPlanExact &&":
            "R127 readiness requires descriptor and mutation-plan exactness",
        "R127 managed-buffer readiness consumes exact mutation plan":
            "R127 hosted readiness probe assertion",
    }
    missing_r121_managed_buffer_plan += [
        meaning
        for token, meaning in r127_managed_buffer_readiness_contract.items()
        if token not in (NATIVE_BACKEND_HPP + "\n" + NATIVE_BACKEND_CPP + "\n" + CONSTANT_BUFFER_PROBE)
    ]
    if missing_r121_managed_buffer_plan:
        raise SystemExit(
            "DX11 R121/R127 managed-buffer mutation-plan contract drift: "
            + ", ".join(missing_r121_managed_buffer_plan)
        )

    surface_mirror_contract_text = SURFACE_MIRROR_HPP + "\n" + SURFACE_MIRROR_CPP
    surface_mirror_contract = {
        "class NativeSurfaceMirror": "dedicated dormant RT/depth mirror owner",
        "ResourceRole::Color": "render-target role gate",
        "ResourceRole::DepthStencil": "depth-stencil role gate",
        "ResourceMirrorLifetime::DeviceGeneration": "Reset-bound surface lifetime",
        "D3DMULTISAMPLE_NONE": "unproven MSAA remains fail-closed",
        "CreateTexture2D": "concrete D3D11 surface mirror allocation",
        "CreateRenderTargetView": "concrete RTV ownership",
        "CreateDepthStencilView": "concrete DSV ownership",
        "observe_device_reset": "Reset invalidation transition",
        "mirror_generation_ != device_generation_": "stale generation readiness gate",
        "descriptor_exact": "concrete descriptor/view identity verifier",
        "viewResource.Get() == texture_.Get()":
            "view-to-texture COM identity verifier",
        "if (!descriptor_exact(device))":
            "post-create descriptor validation fail-closed gate",
        "mirror_serial() const noexcept":
            "monotonic concrete mirror recreation identity",
        "struct NativeSurfacePairReadiness":
            "R119 color/depth pair readiness identity",
        "compose_surface_pair_readiness":
            "R119 fail-closed pair composition API",
        "validate_surface_pair_snapshot":
            "R119 stale pair snapshot validator",
        "out.dimensionsMatch =":
            "R119 render-target dimension compatibility gate",
        "out.generationsCurrent =":
            "R119 per-mirror Reset generation gate",
        "out.componentSerialsPresent =":
            "R119 concrete recreation serial gate",
    }
    missing_surface_mirror_contract = [
        meaning
        for token, meaning in surface_mirror_contract.items()
        if token not in surface_mirror_contract_text
    ]
    if "NativeDrawPathActive" in surface_mirror_contract_text:
        missing_surface_mirror_contract.append(
            "surface mirror must not activate native Draw* routing"
        )
    for graph_text, graph_name in (
        (CMAKE, "checked-in CMake"),
        (CMAKE_TOML, "cmake.toml"),
        (BACKEND_GATE, "backend conversion gate"),
    ):
        if "dx11_surface_mirror_probe" not in graph_text:
            missing_surface_mirror_contract.append(
                f"{graph_name} omits dx11_surface_mirror_probe"
            )
    probe_contract = {
        "D3D_DRIVER_TYPE_WARP": "CI-safe software D3D11 device",
        "color.observe_device_reset();": "Reset invalidation smoke",
        "color.recreate(device.Get())": "post-Reset recreation smoke",
        "D3DPOOL_MANAGED": "MANAGED RT negative smoke",
        "D3DMULTISAMPLE_2_SAMPLES": "MSAA fail-closed negative smoke",
        "color.shutdown();": "explicit surface ownership shutdown smoke",
        "descriptor_exact(nullptr)": "null-device descriptor rejection smoke",
        "surface pair readiness did not compose exact mirrors":
            "R119 positive render-target pair proof",
        "stale surface pair snapshot survived depth Reset":
            "R119 stale snapshot rejection proof",
        "surface pair snapshot did not refresh after recreation":
            "R119 recreation identity refresh proof",
        "surface pair accepted mismatched dimensions":
            "R119 dimension mismatch rejection proof",
    }
    missing_surface_mirror_contract += [
        meaning
        for token, meaning in probe_contract.items()
        if token not in SURFACE_MIRROR_PROBE
    ]

    r130_surface_binding_contract = [
        (
            "class NativeSurfacePairBinding final",
            SURFACE_MIRROR_HPP,
            "R130 dormant surface-pair binding owner",
        ),
        (
            "surface_pair_snapshot_token_ != 0",
            SURFACE_MIRROR_HPP,
            "R130 sealed surface-pair identity",
        ),
        (
            "validate_surface_pair_snapshot(",
            SURFACE_MIRROR_CPP,
            "R130 live surface-pair snapshot revalidation",
        ),
        (
            "color.render_target_view() != rtv_.Get()",
            SURFACE_MIRROR_CPP,
            "R130 stale color-view identity rejection",
        ),
        (
            "depth.depth_stencil_view() != dsv_.Get()",
            SURFACE_MIRROR_CPP,
            "R130 stale depth-view identity rejection",
        ),
        (
            "contextDevice.Get() != device_.Get()",
            SURFACE_MIRROR_CPP,
            "R130 foreign-context rejection",
        ),
        (
            "context->OMSetRenderTargetsAndUnorderedAccessViews(",
            SURFACE_MIRROR_CPP,
            "R130/R146 dormant OM render-target binding with UAV cleanup",
        ),
        (
            "R130 exact surface-pair binding failed",
            SURFACE_MIRROR_PROBE,
            "R130 positive WARP binding probe",
        ),
        (
            "R130 OM render-target binding identity drifted",
            SURFACE_MIRROR_PROBE,
            "R130 bound RTV/DSV identity proof",
        ),
        (
            "R130 foreign context did not fail closed",
            SURFACE_MIRROR_PROBE,
            "R130 foreign-context negative probe",
        ),
        (
            "R130 stale binding survived depth Reset",
            SURFACE_MIRROR_PROBE,
            "R130 Reset invalidation negative probe",
        ),
        (
            "R130 stale binding survived mirror recreation",
            SURFACE_MIRROR_PROBE,
            "R130 recreation invalidation negative probe",
        ),
        (
            "DX11 dormant surface-pair binding R130: PASS",
            SURFACE_MIRROR_PROBE,
            "R130 hosted probe completion marker",
        ),
    ]
    missing_surface_mirror_contract += [
        meaning
        for token, source, meaning in r130_surface_binding_contract
        if token not in source
    ]
    r145_surface_live_binding_contract = [
        ("struct NativeSurfacePairBindingReadiness", SURFACE_MIRROR_HPP,
         "R145 live OM target readiness identity"),
        ("NativeSurfacePairBinding::binding_readiness(", SURFACE_MIRROR_CPP,
         "R145 live OM target observer"),
        ("context->OMGetRenderTargets(", SURFACE_MIRROR_CPP,
         "R145 live RTV/DSV readback"),
        ("D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT", SURFACE_MIRROR_CPP,
         "R145 all RTV slots are observed"),
        ("observedRtvs[slot] != nullptr", SURFACE_MIRROR_CPP,
         "R145 unexpected extra RTV slots fail closed"),
        ("bool unorderedAccessClear{}", SURFACE_MIRROR_HPP,
         "R146 unexpected OM UAV readiness gate"),
        ("context->OMGetRenderTargetsAndUnorderedAccessViews(", SURFACE_MIRROR_CPP,
         "R146 live OM UAV readback"),
        ("observedUav != nullptr", SURFACE_MIRROR_CPP,
         "R146 unexpected OM UAV fails closed"),
        ("R146 live OM target binding rejects unexpected UAV", SURFACE_MIRROR_PROBE,
         "R146 unexpected OM UAV negative proof"),
        ("R146 live OM target apply did not clear unexpected UAV", SURFACE_MIRROR_PROBE,
         "R146 exact owner clears unsupported OM UAV state"),
        ("R146 live OM target restore changed snapshot identity", SURFACE_MIRROR_PROBE,
         "R146 deterministic OM target restore proof"),
        ("return binding_readiness(context, color, depth).ready;", SURFACE_MIRROR_CPP,
         "R145 apply verifies effective OM target state"),
        ("R145 live OM target binding seals exact RTV DSV identity", SURFACE_MIRROR_PROBE,
         "R145 positive live target proof"),
        ("R145 live OM target binding rejects extra RTV slot", SURFACE_MIRROR_PROBE,
         "R145 extra RTV slot negative proof"),
        ("R145 live OM target binding fails closed after RTV DSV unbind", SURFACE_MIRROR_PROBE,
         "R145 live target unbind negative proof"),
        ("R145 live OM target binding restores deterministic snapshot", SURFACE_MIRROR_PROBE,
         "R145 deterministic target restore proof"),
    ]
    missing_surface_mirror_contract += [
        meaning
        for token, source, meaning in r145_surface_live_binding_contract
        if token not in source
    ]

    runtime_surface_binding_users = []
    surface_binding_internal_sources = {
        DX11 / "surface_mirror.cpp",
        DX11 / "native_backend.cpp",
    }
    for source_path in (ROOT / "src").rglob("*.cpp"):
        if source_path in surface_binding_internal_sources:
            continue
        if "NativeSurfacePairBinding" in source_path.read_text(
            encoding="utf-8", errors="ignore"
        ):
            runtime_surface_binding_users.append(
                source_path.relative_to(ROOT).as_posix()
            )
    if runtime_surface_binding_users:
        missing_surface_mirror_contract.append(
            "R130 dormant surface binding gained production callers: "
            + ", ".join(runtime_surface_binding_users)
        )
    if missing_surface_mirror_contract:
        raise SystemExit(
            "DX11 dormant surface-mirror contract drift: "
            + ", ".join(missing_surface_mirror_contract)
        )


    dual_source_blend_contract = [
        (
            "PipelineUnsupportedDualSourceBlend = 1u << 12",
            PIPELINE_TRANSLATION_HPP,
            "dedicated dual-source blend blocker",
        ),
        (
            "case D3DBLEND_SRCCOLOR2: return {D3D11_BLEND_SRC1_COLOR, false};",
            STATE_TRANSLATION_CPP,
            "dual-source source-color mapping stays fail-closed without SV_Target1 proof",
        ),
        (
            "case D3DBLEND_INVSRCCOLOR2: return {D3D11_BLEND_INV_SRC1_COLOR, false};",
            STATE_TRANSLATION_CPP,
            "inverse dual-source source-color mapping stays fail-closed without SV_Target1 proof",
        ),
        (
            "is_dual_source_blend_factor",
            PIPELINE_TRANSLATION_CPP,
            "dual-source factor classifier",
        ),
        (
            "dualSourceBlendRequested",
            PIPELINE_TRANSLATION_CPP,
            "draw-state dual-source provenance",
        ),
        (
            "out.unsupported |= PipelineUnsupportedDualSourceBlend;",
            PIPELINE_TRANSLATION_CPP,
            "dedicated fail-closed dual-source pipeline blocker",
        ),
        (
            "SRCCOLOR2 source blend must report dedicated dual-source blocker",
            SEMANTIC_SMOKE,
            "source SRC1 semantic blocker proof",
        ),
        (
            "INVSRCCOLOR2 source blend must report dedicated dual-source blocker",
            SEMANTIC_SMOKE,
            "inverse source SRC1 semantic blocker proof",
        ),
        (
            "SRCCOLOR2 destination blend must report dedicated dual-source blocker",
            SEMANTIC_SMOKE,
            "destination SRC1 semantic blocker proof",
        ),
        (
            "INVSRCCOLOR2 destination blend must report dedicated dual-source blocker",
            SEMANTIC_SMOKE,
            "inverse destination SRC1 semantic blocker proof",
        ),
        (
            "disabled alpha blending must ignore dormant dual-source factors",
            SEMANTIC_SMOKE,
            "disabled blend does not create a false dual-source blocker",
        ),
    ]
    missing_dual_source_blend_contract = [
        meaning
        for token, source, meaning in dual_source_blend_contract
        if token not in source
    ]
    if missing_dual_source_blend_contract:
        raise SystemExit(
            "DX11 dual-source blend readiness drift: "
            + ", ".join(missing_dual_source_blend_contract)
        )

    legacy_both_source_blend_contract = {
        "sourceBlendValue == D3DBLEND_BOTHSRCALPHA":
            "legacy BOTHSRCALPHA is interpreted only from SRCBLEND",
        "dstBlend = { D3D11_BLEND_INV_SRC_ALPHA, true };":
            "BOTHSRCALPHA overrides DESTBLEND with INV_SRC_ALPHA",
        "sourceBlendValue == D3DBLEND_BOTHINVSRCALPHA":
            "legacy BOTHINVSRCALPHA is interpreted only from SRCBLEND",
        "dstBlend = { D3D11_BLEND_SRC_ALPHA, true };":
            "BOTHINVSRCALPHA overrides DESTBLEND with SRC_ALPHA",
    }
    missing_legacy_both_source_blend_contract = [
        meaning
        for token, meaning in legacy_both_source_blend_contract.items()
        if token not in PIPELINE_TRANSLATION_CPP
    ]
    semantic_legacy_blend_contract = {
        "BOTHSRCALPHA source shortcut did not translate exactly":
            "BOTHSRCALPHA positive semantic smoke",
        "BOTHINVSRCALPHA source shortcut did not translate exactly":
            "BOTHINVSRCALPHA positive semantic smoke",
        "destination BOTHSRCALPHA must remain fail-closed":
            "destination misuse negative semantic smoke",
    }
    missing_legacy_both_source_blend_contract += [
        meaning
        for token, meaning in semantic_legacy_blend_contract.items()
        if token not in SEMANTIC_SMOKE
    ]
    if missing_legacy_both_source_blend_contract:
        raise SystemExit(
            "DX11 legacy both-source blend contract drift: "
            + ", ".join(missing_legacy_both_source_blend_contract)
        )

    triangle_fan_expansion_contract = {
        "translate_triangle_fan_expansion":
            "triangle-fan expansion planning API",
        "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST":
            "triangle-fan expansion targets D3D11 triangle-list topology",
        "out.expandedIndexCount = primitiveCount * 3u":
            "triangle-fan emits three indices per source primitive",
        "triangle_fan_source_element":
            "triangle-fan expanded-index to source-element mapping",
        "materialize_triangle_fan_vertex_indices":
            "triangle-fan concrete triangle-list index materializer",
        "materialize_indexed_triangle_fan_indices":
            "R123 indexed triangle-fan source-stream materializer",
        "sourceIndexFormat != D3DFMT_INDEX16":
            "R123 exact D3D9 index-format gate",
        "startIndex > sourceIndexCount":
            "R124 StartIndex upper-bound fail-closed gate",
        "expansion.sourceElementCount > sourceIndexCount - startIndex":
            "R124 StartIndex-aware source-range fail-closed gate",
        "static_cast<std::size_t>(startIndex + sourceElement)":
            "R124 widened byte-offset arithmetic",
        "std::memcpy(":
            "R123 alignment-safe source-index decoding",
        "expandedIndexCapacity < expansion.expandedIndexCount":
            "triangle-fan destination-capacity fail-closed gate",
        "maxValue - (expansion.sourceElementCount - 1u)":
            "triangle-fan base-vertex overflow fail-closed gate",
        "case D3DPT_TRIANGLEFAN: return {D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED, false};":
            "direct triangle-fan topology remains fail-closed",
    }
    missing_triangle_fan_expansion_contract = [
        meaning
        for token, meaning in triangle_fan_expansion_contract.items()
        if token not in STATE_TRANSLATION_CPP
    ]
    semantic_triangle_fan_contract = {
        "triangle fan direct topology must remain fail-closed":
            "direct fan negative semantic smoke",
        "triangle fan expansion did not target triangle list":
            "triangle-list expansion semantic smoke",
        "triangle fan expansion source mapping drifted":
            "fan source-index mapping semantic smoke",
        "triangle fan materialized index stream drifted":
            "fan concrete index-stream semantic smoke",
        "triangle fan short destination did not fail before writes":
            "fan destination-capacity fail-closed smoke",
        "triangle fan base-vertex overflow did not fail before writes":
            "fan base-vertex overflow fail-closed smoke",
        "zero-primitive triangle fan materialization must be empty-exact":
            "fan empty-stream semantic smoke",
        "using outrun::vr::dx11::materialize_triangle_fan_vertex_indices;":
            "R124 semantic probe imports non-indexed fan materializer",
        "INDEX16 triangle fan did not preserve source indices":
            "R124 INDEX16 StartIndex preservation proof",
        "INDEX32 triangle fan did not preserve 32-bit source indices":
            "R123 INDEX32 source-value preservation proof",
        "indexed triangle fan short source did not fail before writes":
            "R124 StartIndex-aware short-source fail-closed proof",
        "indexed triangle fan StartIndex overflow did not fail before writes":
            "R124 StartIndex upper-bound negative proof",
        "indexed triangle fan short destination did not fail before writes":
            "R123 short-destination fail-closed proof",
        "indexed triangle fan accepted unsupported index format":
            "R123 unsupported-format fail-closed proof",
        "zero-primitive indexed triangle fan must be empty-exact":
            "R123 empty indexed-fan proof",
        "triangle fan expansion overflow did not fail closed":
            "fan expansion-count overflow negative semantic smoke",
    }
    missing_triangle_fan_expansion_contract += [
        meaning
        for token, meaning in semantic_triangle_fan_contract.items()
        if token not in SEMANTIC_SMOKE
    ]
    if missing_triangle_fan_expansion_contract:
        raise SystemExit(
            "DX11 triangle-fan expansion contract drift: "
            + ", ".join(missing_triangle_fan_expansion_contract)
        )

    separate_alpha_snapshot_contract = {
        "DWORD srcBlendAlpha = D3DBLEND_ONE;": "separate alpha source factor snapshot",
        "DWORD destBlendAlpha = D3DBLEND_ZERO;": "separate alpha destination factor snapshot",
        "DWORD blendOpAlpha = D3DBLENDOP_ADD;": "separate alpha operation snapshot",
    }
    missing_separate_alpha_contract = [
        meaning
        for token, meaning in separate_alpha_snapshot_contract.items()
        if token not in D3D9_DRAW_STATE_HPP
    ]
    separate_alpha_capture_contract = {
        "read(D3DRS_SRCBLENDALPHA, out.srcBlendAlpha);": "capture separate alpha source factor",
        "read(D3DRS_DESTBLENDALPHA, out.destBlendAlpha);": "capture separate alpha destination factor",
        "read(D3DRS_BLENDOPALPHA, out.blendOpAlpha);": "capture separate alpha operation",
    }
    missing_separate_alpha_contract += [
        meaning
        for token, meaning in separate_alpha_capture_contract.items()
        if token not in D3D9_RENDER_STATE_CAPTURE
    ]
    separate_alpha_translation_contract = {
        "translate_separate_alpha_blend_factor": "alpha-component blend-factor canonicalization",
        "case D3DBLEND_SRCCOLOR:": "D3D9 source-color alpha-component handling",
        "return { D3D11_BLEND_SRC_ALPHA, true };": "D3D11 alpha-safe source factor",
        "rt.SrcBlendAlpha = srcBlendAlpha.value;": "separate alpha source descriptor",
        "rt.DestBlendAlpha = dstBlendAlpha.value;": "separate alpha destination descriptor",
        "rt.BlendOpAlpha = blendOpAlpha.value;": "separate alpha operation descriptor",
        "PipelineUnsupportedSeparateAlphaBlend": "fail-closed separate alpha gate",
    }
    missing_separate_alpha_contract += [
        meaning
        for token, meaning in separate_alpha_translation_contract.items()
        if token not in PIPELINE_TRANSLATION_CPP
    ]
    separate_alpha_semantic_contract = {
        "separate alpha blend did not translate exactly": "positive separate-alpha semantic smoke",
        "legacy BOTH shortcut must fail closed in separate alpha state": "role-invalid BOTH* negative smoke",
        "disabled alpha blending must ignore separate alpha state": "disabled-state semantic smoke",
    }
    missing_separate_alpha_contract += [
        meaning
        for token, meaning in separate_alpha_semantic_contract.items()
        if token not in SEMANTIC_SMOKE
    ]
    if missing_separate_alpha_contract:
        raise SystemExit(
            "DX11 separate-alpha translation contract drift: "
            + ", ".join(missing_separate_alpha_contract)
        )

    alpha_test_shader_contract = {
        "struct FixedFunctionAlphaTestState":
            "fixed-function alpha-test shader state contract",
        "FixedFunctionShaderPrototypeUnsupportedAlphaTestState":
            "fail-closed alpha-test prototype blocker",
    }
    missing_alpha_test_shader_contract = [
        meaning
        for token, meaning in alpha_test_shader_contract.items()
        if token not in PIPELINE_TRANSLATION_HPP
    ]
    alpha_test_shader_source_contract = {
        "fixed_function_alpha_test_supported(":
            "D3D9 alpha comparison classifier",
        "case D3DCMP_GREATEREQUAL: return \">=\";":
            "GREATEREQUAL alpha comparison mapping",
        "alphaTest.reference & 0xFFu":
            "8-bit D3D9 ALPHAREF normalization",
        "if (!(current.a ":
            "pixel-shader alpha-test discard predicate",
        "FixedFunctionShaderPrototypeUnsupportedAlphaTestState":
            "invalid/incomplete alpha-test fail-closed path",
    }
    missing_alpha_test_shader_contract += [
        meaning
        for token, meaning in alpha_test_shader_source_contract.items()
        if token not in PIPELINE_TRANSLATION_CPP
    ]
    alpha_test_census_contract = {
        "bool alphaTestObservationComplete{};":
            "alpha-test census completeness identity",
        "DWORD alphaTestEnable = FALSE;":
            "alpha-test enable census identity",
        "DWORD alphaTestRef{};":
            "alpha-test reference census identity",
        "DWORD alphaTestFunc = D3DCMP_ALWAYS;":
            "alpha-test function census identity",
        "signature.alphaTestEnable = source.alphaTestEnable;":
            "captured alpha-test enable propagation",
        "signature.alphaTestRef = source.alphaRef;":
            "captured alpha-test reference propagation",
        "signature.alphaTestFunc = source.alphaFunc;":
            "captured alpha-test function propagation",
        "sig.alphaTestRef & 0xFFu":
            "semantic alpha-reference signature hashing",
        "FixedFunctionAlphaTestState{":
            "alpha-test state supplied to diagnostic shader prototype",
    }
    missing_alpha_test_shader_contract += [
        meaning
        for token, meaning in alpha_test_census_contract.items()
        if token not in census
    ]
    alpha_test_semantic_contract = {
        "alpha-test reference normalization drifted":
            "ALPHAREF normalization semantic smoke",
        "alpha-test GREATEREQUAL semantic drift":
            "positive alpha comparison semantic smoke",
        "incomplete alpha-test observation did not fail closed":
            "incomplete-observation negative semantic smoke",
        "invalid alpha-test function did not fail closed":
            "invalid-function negative semantic smoke",
        "disabled alpha test injected pixel-kill semantics":
            "disabled-state semantic smoke",
    }
    missing_alpha_test_shader_contract += [
        meaning
        for token, meaning in alpha_test_semantic_contract.items()
        if token not in SEMANTIC_SMOKE
    ]
    if missing_alpha_test_shader_contract:
        raise SystemExit(
            "DX11 fixed-function alpha-test shader contract drift: "
            + ", ".join(missing_alpha_test_shader_contract)
        )


    fog_observation_snapshot_contract = {
        "DWORD fogColor = 0;": "fog color snapshot",
        "DWORD fogTableMode = D3DFOG_NONE;": "pixel/table fog mode snapshot",
        "DWORD fogStartBits = 0x00000000u;": "raw fog-start bit snapshot",
        "DWORD fogEndBits = 0x3F800000u;": "raw fog-end bit snapshot",
        "DWORD fogDensityBits = 0x3F800000u;": "raw fog-density bit snapshot",
        "DWORD rangeFogEnable = FALSE;": "range-fog enable snapshot",
        "DWORD fogVertexMode = D3DFOG_NONE;": "vertex fog mode snapshot",
    }
    missing_fog_observation_contract = [
        meaning
        for token, meaning in fog_observation_snapshot_contract.items()
        if token not in D3D9_DRAW_STATE_HPP
    ]
    fog_observation_capture_contract = {
        "read(D3DRS_FOGCOLOR, out.fogColor);": "capture fog color",
        "read(D3DRS_FOGTABLEMODE, out.fogTableMode);":
            "capture pixel/table fog mode",
        "read(D3DRS_FOGSTART, out.fogStartBits);":
            "capture raw fog-start bits",
        "read(D3DRS_FOGEND, out.fogEndBits);":
            "capture raw fog-end bits",
        "read(D3DRS_FOGDENSITY, out.fogDensityBits);":
            "capture raw fog-density bits",
        "read(D3DRS_RANGEFOGENABLE, out.rangeFogEnable);":
            "capture range-fog enable",
        "read(D3DRS_FOGVERTEXMODE, out.fogVertexMode);":
            "capture vertex fog mode",
    }
    missing_fog_observation_contract += [
        meaning
        for token, meaning in fog_observation_capture_contract.items()
        if token not in D3D9_RENDER_STATE_CAPTURE
    ]
    fog_observation_census_contract = {
        "bool fogObservationComplete{};":
            "fog census completeness identity",
        "signature.fogColor = source.fogColor;":
            "fog color census propagation",
        "signature.fogTableMode = source.fogTableMode;":
            "fog table-mode census propagation",
        "signature.fogVertexMode = source.fogVertexMode;":
            "fog vertex-mode census propagation",
        "sig.fogColor & 0x00FFFFFFu":
            "fog RGB semantic signature hashing",
        "hash = hash_mix(hash, sig.fogStartBits);":
            "fog-start signature hashing",
        "hash = hash_mix(hash, sig.fogEndBits);":
            "fog-end signature hashing",
        "hash = hash_mix(hash, sig.fogDensityBits);":
            "fog-density signature hashing",
        "hash = hash_mix(hash, sig.rangeFogEnable);":
            "range-fog signature hashing",
        "VR DX11 R119 ffp fog state#{}:":
            "per-signature fog evidence logging",
    }
    missing_fog_observation_contract += [
        meaning
        for token, meaning in fog_observation_census_contract.items()
        if token not in census
    ]
    if missing_fog_observation_contract:
        raise SystemExit(
            "DX11 fog observation/census contract drift: "
            + ", ".join(missing_fog_observation_contract)
        )

    r124_output_snapshot_contract = {
        "DWORD blendFactor = 0xFFFFFFFFu;":
            "R124 D3D9 blend-factor snapshot",
        "DWORD multiSampleMask = 0xFFFFFFFFu;":
            "R124 D3D9 multisample-mask snapshot",
        "D3DVIEWPORT9 viewport{};":
            "R124 viewport snapshot",
        "RECT scissorRect{};":
            "R124 scissor rectangle snapshot",
        "bool outputStateComplete = false;":
            "R124 output-state completeness bit",
    }
    missing_r124_output = [
        meaning
        for token, meaning in r124_output_snapshot_contract.items()
        if token not in D3D9_DRAW_STATE_HPP
    ]
    for token, meaning in {
        "readOutput(D3DRS_BLENDFACTOR, out.blendFactor);":
            "R124 tracked blend-factor capture",
        "readOutput(D3DRS_MULTISAMPLEMASK, out.multiSampleMask);":
            "R124 tracked sample-mask capture",
        "device->GetViewport(&out.viewport)":
            "R124 viewport capture",
        "device->GetScissorRect(&out.scissorRect)":
            "R124 scissor capture",
        "out.outputStateComplete = outputOk;":
            "R124 independent output completeness",
    }.items():
        if token not in D3D9_RENDER_STATE_CAPTURE:
            missing_r124_output.append(meaning)
    if missing_r124_output:
        raise SystemExit(
            "DX11 R124 output-state capture drift: "
            + ", ".join(missing_r124_output)
        )

    r132_pipeline_binding_contract = [
        (
            "bind_for_observation(",
            NATIVE_BACKEND_HPP,
            "R132 dormant R97 pipeline binding API",
        ),
        (
            "NativeFixedFunctionPipelineBundle::bind_for_observation(",
            NATIVE_BACKEND_CPP,
            "R132 dormant R97 pipeline binding implementation",
        ),
        (
            "context->IASetInputLayout(input_layout_.Get());",
            NATIVE_BACKEND_CPP,
            "R132 exact input-layout binding",
        ),
        (
            "context->VSSetShader(vertex_shader_.Get(), nullptr, 0);",
            NATIVE_BACKEND_CPP,
            "R132 exact vertex-shader binding",
        ),
        (
            "context->PSSetShader(pixel_shader_.Get(), nullptr, 0);",
            NATIVE_BACKEND_CPP,
            "R132 exact pixel-shader binding",
        ),
        (
            "contextDevice.Get() != device_.Get()",
            NATIVE_BACKEND_CPP,
            "R132 exact-device context gate",
        ),
        (
            "dormant pipeline binding accepts exact same-device R97 snapshot",
            CONSTANT_BUFFER_PROBE,
            "R132 hosted WARP positive binding probe",
        ),
        (
            "dormant pipeline binding preserves exact IA VS PS identity",
            CONSTANT_BUFFER_PROBE,
            "R132 bound-object identity readback proof",
        ),
        (
            "dormant pipeline binding rejects missing R97 snapshot",
            CONSTANT_BUFFER_PROBE,
            "R132 missing-snapshot negative probe",
        ),
        (
            "dormant pipeline binding rejects stale R97 snapshot",
            CONSTANT_BUFFER_PROBE,
            "R132 stale-snapshot negative probe",
        ),
        (
            "dormant pipeline binding rejects foreign D3D11 context",
            CONSTANT_BUFFER_PROBE,
            "R132 foreign-context negative probe",
        ),
        (
            "DX11 dormant fixed-function pipeline object binding: PASS",
            CONSTANT_BUFFER_PROBE,
            "R132 hosted probe completion marker",
        ),
    ]
    missing_r132_pipeline_binding = [
        meaning
        for token, source, meaning in r132_pipeline_binding_contract
        if token not in source
    ]
    runtime_pipeline_binding_users = []
    for source_path in (ROOT / "src").rglob("*.cpp"):
        if source_path == DX11 / "native_backend.cpp":
            continue
        if ".bind_for_observation(" in source_path.read_text(
            encoding="utf-8", errors="ignore"
        ):
            runtime_pipeline_binding_users.append(
                source_path.relative_to(ROOT).as_posix()
            )
    if runtime_pipeline_binding_users:
        missing_r132_pipeline_binding.append(
            "R132 dormant pipeline binding gained production callers: "
            + ", ".join(runtime_pipeline_binding_users)
        )
    if missing_r132_pipeline_binding:
        raise SystemExit(
            "DX11 R132 dormant pipeline-binding contract drift: "
            + ", ".join(missing_r132_pipeline_binding)
        )

    r126_output_binding_contract = [
        (
            "class NativeFixedFunctionOutputStateBinding final",
            NATIVE_BACKEND_HPP,
            "R126 dormant output-state binding owner",
        ),
        (
            "render_state_snapshot_token_ != 0",
            NATIVE_BACKEND_HPP,
            "R126 sealed R116 component identity",
        ),
        (
            "output_state_snapshot_token_ != 0",
            NATIVE_BACKEND_HPP,
            "R126 sealed R124 component identity",
        ),
        (
            "NativeFixedFunctionOutputStateBinding::initialize(",
            NATIVE_BACKEND_CPP,
            "R126 binding initialization",
        ),
        (
            "renderStateBundle.device() != device",
            NATIVE_BACKEND_CPP,
            "R126 exact-device ownership gate",
        ),
        (
            "context->RSSetViewports(1, &viewport_);",
            NATIVE_BACKEND_CPP,
            "R126 viewport binding",
        ),
        (
            "context->RSSetScissorRects(1, &scissor_rect_);",
            NATIVE_BACKEND_CPP,
            "R126 scissor binding",
        ),
        (
            "context->OMSetBlendState(",
            NATIVE_BACKEND_CPP,
            "R126 blend-factor/sample-mask binding",
        ),
        (
            "context->OMSetDepthStencilState(",
            NATIVE_BACKEND_CPP,
            "R126 depth-stencil reference binding",
        ),
        (
            "R126 WARP context exposes the exact sealed RS/OM binding",
            CONSTANT_BUFFER_PROBE,
            "R126 WARP positive binding probe",
        ),
        (
            "R126 foreign D3D11 context cannot consume binding owner",
            CONSTANT_BUFFER_PROBE,
            "R126 foreign-device fail-closed probe",
        ),
        (
            "R126 missing R124 snapshot token fails closed",
            CONSTANT_BUFFER_PROBE,
            "R126 missing dynamic-state identity probe",
        ),
        (
            "R126 missing R116 snapshot token fails closed",
            CONSTANT_BUFFER_PROBE,
            "R126 missing immutable-state identity probe",
        ),
    ]
    missing_r126_output_binding = [
        meaning
        for token, source, meaning in r126_output_binding_contract
        if token not in source
    ]
    if missing_r126_output_binding:
        raise SystemExit(
            "DX11 R126 output-state binding contract drift: "
            + ", ".join(missing_r126_output_binding)
        )

    r137_live_output_binding_contract = [
        (
            "struct NativeFixedFunctionOutputBindingReadiness",
            NATIVE_BACKEND_HPP,
            "R137 live RS/OM binding readiness identity",
        ),
        (
            "NativeFixedFunctionOutputStateBinding::binding_readiness(",
            NATIVE_BACKEND_CPP,
            "R137 live RS/OM observation implementation",
        ),
        (
            "context->RSGetState(",
            NATIVE_BACKEND_CPP,
            "R137 rasterizer readback",
        ),
        (
            "context->RSGetViewports(",
            NATIVE_BACKEND_CPP,
            "R137 viewport readback",
        ),
        (
            "context->RSGetScissorRects(",
            NATIVE_BACKEND_CPP,
            "R137 scissor readback",
        ),
        (
            "context->OMGetBlendState(",
            NATIVE_BACKEND_CPP,
            "R137 blend state/factor/sample-mask readback",
        ),
        (
            "context->OMGetDepthStencilState(",
            NATIVE_BACKEND_CPP,
            "R137 depth-stencil/stencil-ref readback",
        ),
        (
            "R137 live output binding issues exact RS OM snapshot",
            CONSTANT_BUFFER_PROBE,
            "R137 positive live output binding proof",
        ),
        (
            "R137 live output binding fails closed after RS drift",
            CONSTANT_BUFFER_PROBE,
            "R137 post-apply rasterizer drift negative proof",
        ),
        (
            "R137 restored output binding reproduces exact snapshot",
            CONSTANT_BUFFER_PROBE,
            "R137 deterministic restore proof",
        ),
    ]
    missing_r137_live_output_binding = [
        meaning
        for token, source, meaning in r137_live_output_binding_contract
        if token not in source
    ]
    if missing_r137_live_output_binding:
        raise SystemExit(
            "DX11 R137 live output-binding contract drift: "
            + ", ".join(missing_r137_live_output_binding)
        )

    r126_output_binding_provenance_contract = [
        (
            "renderStateBundle.validate_translation_snapshot(",
            NATIVE_BACKEND_CPP,
            "R126 live render-state snapshot revalidation",
        ),
        (
            "validate_fixed_function_output_state_snapshot(",
            NATIVE_BACKEND_CPP,
            "R126 live R124 source/surface snapshot revalidation",
        ),
        (
            "translation.rasterizer.ScissorEnable != sourceScissorEnabled",
            NATIVE_BACKEND_CPP,
            "R126 immutable/dynamic scissor consistency gate",
        ),
        (
            "R126 mismatched sealed scissor state fails closed",
            CONSTANT_BUFFER_PROBE,
            "R126 cross-snapshot scissor mismatch negative proof",
        ),
        (
            "R126 stale R124 source/token pair fails closed",
            CONSTANT_BUFFER_PROBE,
            "R126 stale output provenance negative proof",
        ),
    ]
    missing_r126_output_binding_provenance = [
        meaning
        for token, source, meaning in r126_output_binding_provenance_contract
        if token not in source
    ]
    if missing_r126_output_binding_provenance:
        raise SystemExit(
            "DX11 R126 output-state provenance contract drift: "
            + ", ".join(missing_r126_output_binding_provenance)
        )

    r131_output_binding_draw_contract = [
        (
            "surface_pair_snapshot_token_ != 0",
            NATIVE_BACKEND_HPP,
            "R131 R126 owner seals surface-pair identity",
        ),
        (
            "surface_pair_snapshot_token_ = surfacePair.snapshotToken;",
            NATIVE_BACKEND_CPP,
            "R131 surface-pair token capture",
        ),
        (
            "token, surface_pair_snapshot_token_",
            NATIVE_BACKEND_CPP,
            "R131 surface-pair token participates in binding identity",
        ),
        (
            "outputStateBinding.surface_pair_snapshot_token() ==",
            CONSTANT_BUFFER_PROBE,
            "R131 hosted owner surface identity assertion",
        ),
        (
            "const NativeFixedFunctionOutputStateBinding& outputBinding",
            NATIVE_BACKEND_HPP,
            "R131 draw composition requires concrete binding owner",
        ),
        (
            "outputBinding.snapshot_token() != 0",
            NATIVE_BACKEND_CPP,
            "R131 draw readiness requires a concrete binding token",
        ),
    ]
    missing_r131_output_binding_draw = [
        meaning
        for token, source, meaning in r131_output_binding_draw_contract
        if token not in source
    ]
    if missing_r131_output_binding_draw:
        raise SystemExit(
            "DX11 R131 output-binding draw contract drift: "
            + ", ".join(missing_r131_output_binding_draw)
        )

    r132_textured_draw_contract = [
        (
            "struct NativeFixedFunctionTextureStageBindingReadiness",
            NATIVE_BACKEND_HPP,
            "R132 observed PS texture-stage binding readiness",
        ),
        (
            "struct NativeFixedFunctionTexturedDrawReadiness",
            NATIVE_BACKEND_HPP,
            "R132 textured draw readiness",
        ),
        (
            "PSGetSamplers(",
            NATIVE_BACKEND_CPP,
            "R132 live sampler binding readback",
        ),
        (
            "PSGetShaderResources(",
            NATIVE_BACKEND_CPP,
            "R132 live SRV binding readback",
        ),
        (
            "out.textureStageSnapshotToken = textureStage.snapshotToken",
            NATIVE_BACKEND_CPP,
            "R132 textured draw consumes exact PS binding identity",
        ),
        (
            "R132 texture-stage binding issues exact sampler/SRV snapshot",
            CONSTANT_BUFFER_PROBE,
            "R132 positive PS binding snapshot proof",
        ),
        (
            "R133 textured draw readiness composes the exact required PS stage",
            CONSTANT_BUFFER_PROBE,
            "R133 positive textured draw composition proof",
        ),
        (
            "R132 textured draw readiness fails closed after PS binding drift",
            CONSTANT_BUFFER_PROBE,
            "R132 stale PS binding negative proof",
        ),
    ]
    missing_r132_textured_draw = [
        meaning
        for token, source, meaning in r132_textured_draw_contract
        if token not in source
    ]
    if missing_r132_textured_draw:
        raise SystemExit(
            "DX11 R132 textured-draw readiness contract drift: "
            + ", ".join(missing_r132_textured_draw)
        )

    r133_textured_stage_mask_contract = [
        (
            "std::uint32_t requiredTextureMask{};",
            NATIVE_BACKEND_HPP,
            "R133 draw-level required texture-stage mask provenance",
        ),
        (
            "bool textureMaskMatches{};",
            NATIVE_BACKEND_HPP,
            "R133 explicit stage-mask identity gate",
        ),
        (
            "std::uint32_t observedTextureMask{};",
            NATIVE_BACKEND_HPP,
            "R133 observed PS stage bit provenance",
        ),
        (
            "out.requiredTextureMask = activation.requiredTextureMask;",
            NATIVE_BACKEND_CPP,
            "R133 activation mask propagated into draw readiness",
        ),
        (
            "out.requiredTextureMask == out.observedTextureMask",
            NATIVE_BACKEND_CPP,
            "R133 exact single-stage mask match",
        ),
        (
            "out.textureMaskMatches &&",
            NATIVE_BACKEND_CPP,
            "R133 stage-mask gate participates in final readiness",
        ),
        (
            "token, out.requiredTextureMask",
            NATIVE_BACKEND_CPP,
            "R133 required stage mask sealed into textured draw token",
        ),
        (
            "token, out.observedTextureMask",
            NATIVE_BACKEND_CPP,
            "R133 observed stage bit sealed into textured draw token",
        ),
        (
            "R133 textured draw rejects texture stage outside activation mask",
            CONSTANT_BUFFER_PROBE,
            "R133 wrong-stage fail-closed proof",
        ),
        (
            "R133 single-stage observer rejects multi-stage activation mask",
            CONSTANT_BUFFER_PROBE,
            "R133 partial multi-stage evidence fail-closed proof",
        ),
    ]
    missing_r133_textured_stage_mask = [
        meaning
        for token, source, meaning in r133_textured_stage_mask_contract
        if token not in source
    ]
    if missing_r133_textured_stage_mask:
        raise SystemExit(
            "DX11 R133 textured-draw stage-mask contract drift: "
            + ", ".join(missing_r133_textured_stage_mask)
        )

    r134_bound_pipeline_draw_contract = [
        (
            "struct NativeFixedFunctionPipelineBindingReadiness",
            NATIVE_BACKEND_HPP,
            "R134 live IA/VS/PS binding readiness identity",
        ),
        (
            "NativeFixedFunctionPipelineBundle::binding_readiness(",
            NATIVE_BACKEND_CPP,
            "R134 pipeline binding observation implementation",
        ),
        (
            "out.translationSnapshotValid =",
            NATIVE_BACKEND_CPP,
            "R134 R112 translation token revalidation",
        ),
        (
            "boundInputLayout.Get() == input_layout_.Get()",
            NATIVE_BACKEND_CPP,
            "R134 exact IA input-layout identity gate",
        ),
        (
            "boundVertexShader.Get() == vertex_shader_.Get()",
            NATIVE_BACKEND_CPP,
            "R134 exact VS identity gate",
        ),
        (
            "boundPixelShader.Get() == pixel_shader_.Get()",
            NATIVE_BACKEND_CPP,
            "R134 exact PS identity gate",
        ),
        (
            "out.pipelineSnapshotToken = activation.pipelineSnapshotToken;",
            NATIVE_BACKEND_CPP,
            "R134 activation pipeline identity propagated into draw",
        ),
        (
            "struct NativeFixedFunctionBoundDrawReadiness",
            NATIVE_BACKEND_HPP,
            "R134 final bound-draw evidence container",
        ),
        (
            "pipelineBinding.pipelineSnapshotToken == draw.pipelineSnapshotToken",
            NATIVE_BACKEND_CPP,
            "R134 pipeline binding must match draw activation pipeline",
        ),
        (
            "R134 exact IA VS PS binding issues a live snapshot",
            CONSTANT_BUFFER_PROBE,
            "R134 positive live pipeline-binding proof",
        ),
        (
            "R138 bound draw reobserves exact live RS OM binding",
            CONSTANT_BUFFER_PROBE,
            "R134 pipeline identity remains composed into the final bound draw",
        ),
        (
            "R134 bound draw rejects mismatched R112 pipeline identity",
            CONSTANT_BUFFER_PROBE,
            "R134 pipeline-token mismatch fail-closed proof",
        ),
        (
            "R134 bound draw rejects textured R133-to-R131 identity drift",
            CONSTANT_BUFFER_PROBE,
            "R134 textured-draw lineage mismatch fail-closed proof",
        ),
        (
            "R134 live PS binding drift invalidates pipeline binding snapshot",
            CONSTANT_BUFFER_PROBE,
            "R134 live pipeline binding drift fail-closed proof",
        ),
    ]
    missing_r134_bound_pipeline_draw = [
        meaning
        for token, source, meaning in r134_bound_pipeline_draw_contract
        if token not in source
    ]
    if missing_r134_bound_pipeline_draw:
        raise SystemExit(
            "DX11 R134 bound pipeline draw contract drift: "
            + ", ".join(missing_r134_bound_pipeline_draw)
        )

    r147_graphics_stage_isolation_contract = [
        (
            "bool graphicsStageIsolationReady{};",
            NATIVE_BACKEND_HPP,
            "R147 graphics-stage isolation readiness field",
        ),
        (
            "context->GSSetShader(nullptr, nullptr, 0);",
            NATIVE_BACKEND_CPP,
            "R147 dormant binder clears geometry shader",
        ),
        (
            "context->HSSetShader(nullptr, nullptr, 0);",
            NATIVE_BACKEND_CPP,
            "R147 dormant binder clears hull shader",
        ),
        (
            "context->DSSetShader(nullptr, nullptr, 0);",
            NATIVE_BACKEND_CPP,
            "R147 dormant binder clears domain shader",
        ),
        (
            "context->GSGetShader(",
            NATIVE_BACKEND_CPP,
            "R147 live geometry shader readback",
        ),
        (
            "context->HSGetShader(",
            NATIVE_BACKEND_CPP,
            "R147 live hull shader readback",
        ),
        (
            "context->DSGetShader(",
            NATIVE_BACKEND_CPP,
            "R147 live domain shader readback",
        ),
        (
            "out.graphicsStageIsolationReady =",
            NATIVE_BACKEND_CPP,
            "R147 fixed-function graphics-stage isolation gate",
        ),
        (
            "R147 live GS drift invalidates fixed-function pipeline binding",
            CONSTANT_BUFFER_PROBE,
            "R147 WARP fail-closed graphics-stage drift proof",
        ),
        (
            "R147 restore fixed-function graphics stage isolation",
            CONSTANT_BUFFER_PROBE,
            "R147 WARP isolation restoration proof",
        ),
    ]
    missing_r147_graphics_stage_isolation = [
        meaning
        for token, source, meaning in r147_graphics_stage_isolation_contract
        if token not in source
    ]
    if missing_r147_graphics_stage_isolation:
        raise SystemExit(
            "DX11 R147 graphics-stage isolation contract drift: "
            + ", ".join(missing_r147_graphics_stage_isolation)
        )

    r136_multi_stage_texture_binding_contract = [
        (
            "struct NativeFixedFunctionTextureBindingSetReadiness",
            NATIVE_BACKEND_HPP,
            "R136 aggregate PS sampler/SRV binding identity",
        ),
        (
            "std::array<std::uint64_t, 8> stageSnapshotTokens{}",
            NATIVE_BACKEND_HPP,
            "R136 per-required-stage snapshot identity",
        ),
        (
            "observe_fixed_function_texture_binding_set(",
            NATIVE_BACKEND_CPP,
            "R136 aggregate live PS binding observer",
        ),
        (
            "(requiredTextureMask & ~kFixedFunctionStageMask) == 0",
            NATIVE_BACKEND_CPP,
            "R136 fixed-function stage 0-7 mask gate",
        ),
        (
            "out.observedTextureMask |= stageBit;",
            NATIVE_BACKEND_CPP,
            "R136 exact bound-stage coverage mask",
        ),
        (
            "out.stageSnapshotTokens[slot] = stage.snapshotToken;",
            NATIVE_BACKEND_CPP,
            "R136 exact per-stage live identity capture",
        ),
        (
            "validate_fixed_function_texture_binding_set_readiness_integrity(",
            NATIVE_BACKEND_CPP,
            "R136 copied aggregate snapshot self-integrity gate",
        ),
        (
            "compose_fixed_function_multistage_textured_draw_readiness(",
            NATIVE_BACKEND_CPP,
            "R136 aggregate binding-to-draw composition",
        ),
        (
            "context, draw.requiredTextureMask, samplers, textures",
            NATIVE_BACKEND_CPP,
            "R136 draw composition reobserves current live PS bindings",
        ),
        (
            "textureBindings.requiredTextureMask == out.requiredTextureMask",
            NATIVE_BACKEND_CPP,
            "R136 aggregate mask must match sealed R135 draw mask",
        ),
        (
            "R136 aggregate two-stage PS binding captures exact live identity",
            CONSTANT_BUFFER_PROBE,
            "R136 positive two-stage live binding proof",
        ),
        (
            "R136 aggregate two-stage PS binding composes exact draw readiness",
            CONSTANT_BUFFER_PROBE,
            "R136 positive aggregate draw proof",
        ),
        (
            "R136 aggregate textured draw remains compatible with R134 pipeline identity",
            CONSTANT_BUFFER_PROBE,
            "R136 aggregate identity reaches final dormant bound-draw evidence",
        ),
        (
            "R136 aggregate binding snapshot rejects copied stage-token drift",
            CONSTANT_BUFFER_PROBE,
            "R136 copied aggregate identity drift fails closed",
        ),
        (
            "R136 aggregate binding snapshot rejects unrequired stage-token injection",
            CONSTANT_BUFFER_PROBE,
            "R136 unused stage-token injection fails exact aggregate integrity",
        ),
        (
            "R136 aggregate binding fails closed after one required PS stage drifts",
            CONSTANT_BUFFER_PROBE,
            "R136 one-stage live drift invalidates aggregate identity",
        ),
        (
            "R136 multistage draw reobserves live PS binding drift",
            CONSTANT_BUFFER_PROBE,
            "R136 downstream draw reobserves instead of trusting stale aggregate",
        ),
        (
            "R136 aggregate binding rejects stages outside fixed-function 0-7",
            CONSTANT_BUFFER_PROBE,
            "R136 unsupported stage-mask bits fail closed",
        ),
    ]
    missing_r136_multi_stage_texture_binding = [
        meaning
        for token, source, meaning in r136_multi_stage_texture_binding_contract
        if token not in source
    ]
    if missing_r136_multi_stage_texture_binding:
        raise SystemExit(
            "DX11 R136 multi-stage texture binding contract drift: "
            + ", ".join(missing_r136_multi_stage_texture_binding)
        )

    r138_final_live_output_binding_contract = [
        (
            "bool outputBindingMatchesDraw{}",
            NATIVE_BACKEND_HPP,
            "R138 final bound draw records live RS/OM lineage match",
        ),
        (
            "const NativeFixedFunctionOutputStateBinding& outputStateBinding",
            NATIVE_BACKEND_HPP,
            "R138 bound draw accepts the sealed R126 output owner",
        ),
        (
            "outputStateBinding.binding_readiness(context)",
            NATIVE_BACKEND_CPP,
            "R138 final composition reobserves current live RS/OM state",
        ),
        (
            "outputBinding.outputBindingSnapshotToken ==",
            NATIVE_BACKEND_CPP,
            "R138 live RS/OM owner token must match sealed draw identity",
        ),
        (
            "draw.outputBindingSnapshotToken",
            NATIVE_BACKEND_CPP,
            "R138 sealed draw output-owner identity participates in final token",
        ),
        (
            "R138 bound draw reobserves exact live RS OM binding",
            CONSTANT_BUFFER_PROBE,
            "R138 positive final live output binding proof",
        ),
        (
            "R138 bound draw fails closed after live RS drift",
            CONSTANT_BUFFER_PROBE,
            "R138 live RS drift invalidates final bound draw",
        ),
        (
            "R138 restored output binding reproduces final bound draw snapshot",
            CONSTANT_BUFFER_PROBE,
            "R138 deterministic RS/OM restore proof",
        ),
    ]
    missing_r138_final_live_output_binding = [
        meaning
        for token, source, meaning in r138_final_live_output_binding_contract
        if token not in source
    ]
    if missing_r138_final_live_output_binding:
        raise SystemExit(
            "DX11 R138 final live output binding contract drift: "
            + ", ".join(missing_r138_final_live_output_binding)
        )


    r139_same_context_final_bound_draw_contract = [
        (
            "compose_fixed_function_same_context_bound_draw_readiness(",
            NATIVE_BACKEND_HPP,
            "R139 public same-context final readiness entrypoint",
        ),
        (
            "validate_fixed_function_same_context_bound_draw_snapshot(",
            NATIVE_BACKEND_HPP,
            "R139 same-context final snapshot validator",
        ),
        (
            "compose_fixed_function_multistage_textured_draw_readiness(\n            draw, context, samplers, textures)",
            NATIVE_BACKEND_CPP,
            "R139 aggregate PS bindings are reobserved on caller context",
        ),
        (
            "pipelineBundle.binding_readiness(\n        context, layout, vertexPrototype, pixelPrototype",
            NATIVE_BACKEND_CPP,
            "R139 IA VS PS bindings are reobserved on caller context",
        ),
        (
            "compose_fixed_function_bound_draw_readiness(\n        draw, texturedDraw, pipelineBinding, context, outputStateBinding)",
            NATIVE_BACKEND_CPP,
            "R139 R138 live RS OM composition consumes same-context observations",
        ),
        (
            "R139 same-context final bound draw reobserves every live binding",
            CONSTANT_BUFFER_PROBE,
            "R139 positive same-context pre-draw proof",
        ),
        (
            "R139 same-context final bound draw rejects live PS pipeline drift",
            CONSTANT_BUFFER_PROBE,
            "R139 live pipeline drift fails closed",
        ),
        (
            "R139 same-context final bound draw rejects live aggregate PS drift",
            CONSTANT_BUFFER_PROBE,
            "R139 aggregate texture drift fails closed",
        ),
        (
            "R139 same-context final bound draw rejects live RS OM drift",
            CONSTANT_BUFFER_PROBE,
            "R139 live output drift fails closed",
        ),
        (
            "R139 same-context final bound draw restores deterministic snapshot",
            CONSTANT_BUFFER_PROBE,
            "R139 deterministic same-context restore proof",
        ),
    ]
    missing_r139_same_context_final_bound_draw = [
        meaning
        for token, source, meaning in r139_same_context_final_bound_draw_contract
        if token not in source
    ]
    if missing_r139_same_context_final_bound_draw:
        raise SystemExit(
            "DX11 R139 same-context final bound draw contract drift: "
            + ", ".join(missing_r139_same_context_final_bound_draw)
        )

    r140_complete_bound_draw_contract = [
        (
            "struct NativeFixedFunctionCompleteBoundDrawReadiness",
            NATIVE_BACKEND_HPP,
            "R140 complete final bound-draw readiness identity",
        ),
        (
            "compose_fixed_function_complete_bound_draw_readiness(",
            NATIVE_BACKEND_HPP,
            "R140 complete final bound-draw composition API",
        ),
        (
            "observe_fixed_function_geometry_binding(\n        context, geometry, vertexBuffer",
            NATIVE_BACKEND_CPP,
            "R140 reobserves live IA geometry on the final caller context",
        ),
        (
            "geometryBinding.geometrySnapshotToken == draw.geometrySnapshotToken",
            NATIVE_BACKEND_CPP,
            "R140 live IA geometry must match the draw-sealed geometry identity",
        ),
        (
            "token, out.geometryBindingSnapshotToken",
            NATIVE_BACKEND_CPP,
            "R140 final token includes the live IA binding snapshot",
        ),
        (
            "R140 complete bound draw includes exact live IA geometry",
            CONSTANT_BUFFER_PROBE,
            "R140 positive complete pre-draw proof",
        ),
        (
            "R140 final gate fails closed after live IA topology drift",
            CONSTANT_BUFFER_PROBE,
            "R140 live IA drift fail-closed proof",
        ),
        (
            "R140 restored IA geometry reproduces complete bound draw snapshot",
            CONSTANT_BUFFER_PROBE,
            "R140 deterministic live IA restore proof",
        ),
    ]
    missing_r140_complete_bound_draw = [
        meaning
        for token, source, meaning in r140_complete_bound_draw_contract
        if token not in source
    ]
    if missing_r140_complete_bound_draw:
        raise SystemExit(
            "DX11 R140 complete bound draw contract drift: "
            + ", ".join(missing_r140_complete_bound_draw)
        )

    r140_complete_ia_parameter_drift_contract = [
        (
            "R140 complete bound draw rejects live IA vertex stride drift",
            CONSTANT_BUFFER_PROBE,
            "R140 exact vertex-stride drift fails closed at final gate",
        ),
        (
            "R140 complete bound draw rejects live IA index offset drift",
            CONSTANT_BUFFER_PROBE,
            "R140 exact index-offset drift fails closed at final gate",
        ),
        (
            "R140 complete bound draw restores exact IA binding parameters",
            CONSTANT_BUFFER_PROBE,
            "R140 deterministic IA parameter restore proof",
        ),
    ]
    missing_r140_complete_ia_parameter_drift = [
        meaning
        for token, source, meaning in r140_complete_ia_parameter_drift_contract
        if token not in source
    ]
    if missing_r140_complete_ia_parameter_drift:
        raise SystemExit(
            "DX11 R140 complete IA parameter drift contract: "
            + ", ".join(missing_r140_complete_ia_parameter_drift)
        )

    r142_complete_fan_bound_draw_contract = [
        (
            "struct NativeFixedFunctionCompleteFanBoundDrawReadiness",
            NATIVE_BACKEND_HPP,
            "R142 complete generated-fan final readiness identity",
        ),
        (
            "compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(",
            NATIVE_BACKEND_HPP,
            "R142 complete generated-fan final composition API",
        ),
        (
            "compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(\n            currentVertex, currentFan, primitiveCount, baseVertex)",
            NATIVE_BACKEND_CPP,
            "R142 reconstructs fan geometry from current owners",
        ),
        (
            "generatedIndexBuffer.binding_readiness(context)",
            NATIVE_BACKEND_CPP,
            "R142 reobserves generated fan IB/topology on final context",
        ),
        (
            "currentGeometry.snapshotToken == draw.geometrySnapshotToken",
            NATIVE_BACKEND_CPP,
            "R142 reconstructed geometry matches sealed draw identity",
        ),
        (
            "observedVertexBuffer.Get() == vertexBuffer.mirror_buffer()",
            NATIVE_BACKEND_CPP,
            "R142 live slot-0 VB identity is exact",
        ),
        (
            "!generatedIndexBuffer.indexedSource",
            NATIVE_BACKEND_CPP,
            "R142 non-indexed fan owner provenance fails closed",
        ),
        (
            "R142 non-indexed fan geometry rejects owner provenance drift",
            CONSTANT_BUFFER_PROBE,
            "R142 fan owner provenance negative proof",
        ),
        (
            "R142 complete fan bound draw seals live VB and generated IB",
            CONSTANT_BUFFER_PROBE,
            "R142 positive complete fan pre-draw proof",
        ),
        (
            "R142 complete fan bound draw rejects generated IB topology drift",
            CONSTANT_BUFFER_PROBE,
            "R142 generated IB topology drift fail-closed proof",
        ),
        (
            "R142 complete fan bound draw rejects live VB stride drift",
            CONSTANT_BUFFER_PROBE,
            "R142 live VB parameter drift fail-closed proof",
        ),
        (
            "R142 complete fan bound draw restores deterministic live IA snapshot",
            CONSTANT_BUFFER_PROBE,
            "R142 deterministic complete fan restore proof",
        ),
    ]
    missing_r142_complete_fan_bound_draw = [
        meaning
        for token, source, meaning in r142_complete_fan_bound_draw_contract
        if token not in source
    ]
    if missing_r142_complete_fan_bound_draw:
        raise SystemExit(
            "DX11 R142 complete generated-fan bound draw contract drift: "
            + ", ".join(missing_r142_complete_fan_bound_draw)
        )

    final_vs_b0_transform_contract = [
        ("struct NativeFixedFunctionTransformBindingReadiness", NATIVE_BACKEND_HPP,
         "final VS b0 transform live-binding evidence container"),
        ("NativeFixedFunctionTransformBuffer::binding_readiness(", NATIVE_BACKEND_CPP,
         "R96 transform owner live-binding observer"),
        ("context->VSGetConstantBuffers(", NATIVE_BACKEND_CPP,
         "live VS b0 constant-buffer readback"),
        ("payload_hash_ = payloadHash;", NATIVE_BACKEND_CPP,
         "uploaded WVP payload identity persistence"),
        ("upload_transform_for_observation(", NATIVE_BACKEND_HPP,
         "pipeline-bundle transform upload observation API"),
        ("struct NativeFixedFunctionFullyBoundDrawReadiness", NATIVE_BACKEND_HPP,
         "final transform-aware dormant pre-draw evidence"),
        ("compose_fixed_function_fully_bound_draw_readiness(", NATIVE_BACKEND_CPP,
         "final transform-aware pre-draw composition"),
        ("final VS b0 transform binding seals exact WVP payload", CONSTANT_BUFFER_PROBE,
         "positive live b0/WVP identity proof"),
        ("final fully bound draw fails closed after VS b0 drift", CONSTANT_BUFFER_PROBE,
         "live VS b0 drift negative proof"),
        ("final VS b0 restore reproduces fully bound draw snapshot", CONSTANT_BUFFER_PROBE,
         "deterministic VS b0 restore proof"),
        ("final VS b0 copied WVP payload drift fails closed", CONSTANT_BUFFER_PROBE,
         "copied WVP payload-integrity negative proof"),
    ]
    missing_final_vs_b0_transform = [
        meaning for token, source, meaning in final_vs_b0_transform_contract
        if token not in source
    ]
    if missing_final_vs_b0_transform:
        raise SystemExit(
            "DX11 final VS b0 transform binding contract drift: "
            + ", ".join(missing_final_vs_b0_transform)
        )

    r145_final_live_om_target_contract = [
        ("struct NativeFixedFunctionRenderTargetBoundDrawReadiness", NATIVE_BACKEND_HPP,
         "R145 final live OM target readiness identity"),
        ("compose_fixed_function_render_target_bound_draw_readiness(", NATIVE_BACKEND_CPP,
         "R145 final live OM target composition"),
        ("surfaceBinding.binding_readiness(", NATIVE_BACKEND_CPP,
         "R145 final gate reobserves surface target owner"),
        ("targetBinding.surfacePairSnapshotToken ==\n            draw.surfacePairSnapshotToken",
         NATIVE_BACKEND_CPP,
         "R145 target identity matches sealed draw surface pair"),
        ("R145 final draw seals exact live OM RTV DSV identity", CONSTANT_BUFFER_PROBE,
         "R145 positive final target-bound draw proof"),
        ("R145 final draw fails closed after live OM target unbind", CONSTANT_BUFFER_PROBE,
         "R145 final target drift negative proof"),
        ("R145 live OM target restore reproduces final draw snapshot", CONSTANT_BUFFER_PROBE,
         "R145 deterministic final target restore proof"),
    ]
    missing_r145_final_live_om_target = [
        meaning
        for token, source, meaning in r145_final_live_om_target_contract
        if token not in source
    ]
    if missing_r145_final_live_om_target:
        raise SystemExit(
            "DX11 R145 final live OM target contract drift: "
            + ", ".join(missing_r145_final_live_om_target)
        )

    r146_final_fan_contract = [
        ("struct NativeFixedFunctionFinalFanBoundDrawReadiness", NATIVE_BACKEND_HPP,
         "R146 generated-fan final readiness identity"),
        ("compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(",
         NATIVE_BACKEND_CPP, "R146 nonindexed fan final composition"),
        ("compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(",
         NATIVE_BACKEND_CPP, "R146 indexed fan final composition"),
        ("validate_fixed_function_final_nonindexed_triangle_fan_bound_draw_snapshot(",
         NATIVE_BACKEND_HPP, "R146 nonindexed fan final validator"),
        ("validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(",
         NATIVE_BACKEND_HPP, "R146 indexed fan final validator"),
        ("R146 nonindexed fan final draw seals live VS b0 and OM target",
         CONSTANT_BUFFER_PROBE, "R146 nonindexed positive proof"),
        ("R146 nonindexed fan final draw fails closed after VS b0 drift",
         CONSTANT_BUFFER_PROBE, "R146 transform drift negative proof"),
        ("R146 nonindexed fan final draw fails closed after OM target drift",
         CONSTANT_BUFFER_PROBE, "R146 OM target drift negative proof"),
        ("R146 nonindexed fan final draw restores transform and OM target snapshot",
         CONSTANT_BUFFER_PROBE, "R146 deterministic restore proof"),
        ("R146 indexed fan final draw seals live VS b0 and OM target",
         CONSTANT_BUFFER_PROBE, "R146 indexed positive proof"),
        ("R146 indexed fan final draw fails closed after VS b0 drift",
         CONSTANT_BUFFER_PROBE, "R146 indexed transform drift negative proof"),
        ("R146 indexed fan final draw fails closed after OM target drift",
         CONSTANT_BUFFER_PROBE, "R146 indexed OM target drift negative proof"),
        ("R146 indexed fan final draw restores transform and OM target snapshot",
         CONSTANT_BUFFER_PROBE, "R146 indexed deterministic restore proof"),
    ]
    missing_r146_final_fan = [
        meaning
        for token, source, meaning in r146_final_fan_contract
        if token not in source
    ]
    if missing_r146_final_fan:
        raise SystemExit(
            "DX11 R146 generated-fan final binding contract drift: "
            + ", ".join(missing_r146_final_fan)
        )

    indexed_fan_probe_declarations = {
        "const auto indexedFanMissingTransform =":
            "indexed fan VS-b0 drift probe declaration",
        "const auto indexedFanMissingTargets =":
            "indexed fan OM-target drift probe declaration",
    }
    duplicate_indexed_fan_probe_declarations = [
        meaning
        for token, meaning in indexed_fan_probe_declarations.items()
        if CONSTANT_BUFFER_PROBE.count(token) != 1
    ]
    if duplicate_indexed_fan_probe_declarations:
        raise SystemExit(
            "DX11 indexed fan final probe declaration uniqueness drift: "
            + ", ".join(duplicate_indexed_fan_probe_declarations)
        )

    r147_direct_draw_dispatch_contract = [
        ("struct NativeFixedFunctionDirectDrawDispatchReadiness", NATIVE_BACKEND_HPP,
         "R147 direct dispatch readiness identity"),
        ("validate_fixed_function_render_target_bound_draw_readiness_integrity(",
         NATIVE_BACKEND_CPP, "R147 copied R145 readiness integrity validator"),
        ("direct_draw_element_count(", NATIVE_BACKEND_CPP,
         "R147 exact direct primitive element-count conversion"),
        ("geometry.indexBufferRequired == indexed", NATIVE_BACKEND_CPP,
         "R147 direct indexed/nonindexed geometry mode match"),
        ("boundDraw.surfacePairSnapshotToken == draw.surfacePairSnapshotToken",
         NATIVE_BACKEND_CPP, "R147 final target identity remains tied to sealed draw"),
        ("startIndexLocation <= maxValue - elementCount", NATIVE_BACKEND_CPP,
         "R147 DrawIndexed range overflow guard"),
        ("startVertexLocation <= maxValue - elementCount", NATIVE_BACKEND_CPP,
         "R147 Draw range overflow guard"),
        ("compose_fixed_function_direct_draw_dispatch_readiness(", NATIVE_BACKEND_CPP,
         "R147 direct dispatch composition API"),
        ("validate_fixed_function_direct_draw_dispatch_snapshot(", NATIVE_BACKEND_CPP,
         "R147 stale direct dispatch validator"),
        ("R147 direct indexed dispatch seals DrawIndexed arguments",
         CONSTANT_BUFFER_PROBE, "R147 positive indexed dispatch proof"),
        ("R147 direct indexed dispatch snapshot rejects StartIndexLocation drift",
         CONSTANT_BUFFER_PROBE, "R147 indexed start drift proof"),
        ("R147 direct nonindexed dispatch seals Draw start vertex",
         CONSTANT_BUFFER_PROBE, "R147 positive nonindexed dispatch proof"),
        ("R147 direct nonindexed dispatch snapshot rejects StartVertexLocation drift",
         CONSTANT_BUFFER_PROBE, "R147 nonindexed start drift proof"),
        ("R147 direct dispatch keeps triangle fan fail closed",
         CONSTANT_BUFFER_PROBE, "R147 fan remains on generated-index path"),
        ("R147 direct dispatch rejects element-count overflow",
         CONSTANT_BUFFER_PROBE, "R147 element-count overflow proof"),
    ]
    missing_r147_direct_draw_dispatch = [
        meaning
        for token, source, meaning in r147_direct_draw_dispatch_contract
        if token not in source
    ]
    if missing_r147_direct_draw_dispatch:
        raise SystemExit(
            "DX11 R147 direct draw dispatch contract drift: "
            + ", ".join(missing_r147_direct_draw_dispatch)
        )

    r149_indexed_source_range_contract = [
        (
            "struct NativeFixedFunctionIndexedSourceRangeReadiness",
            NATIVE_BACKEND_HPP,
            "R149 D3D9 DrawIndexedPrimitive source-range identity",
        ),
        (
            "compose_fixed_function_indexed_source_range_readiness(",
            NATIVE_BACKEND_CPP,
            "R149 indexed source-range compositor",
        ),
        (
            "vertexRangeFits = minVertexIndex <= maxValue - spanMinusOne",
            NATIVE_BACKEND_CPP,
            "R149 MinVertexIndex/NumVertices overflow guard",
        ),
        (
            "const std::int64_t effectiveMinVertex =",
            NATIVE_BACKEND_CPP,
            "R149 BaseVertexIndex effective minimum computation",
        ),
        (
            "effectiveMinVertex >= 0",
            NATIVE_BACKEND_CPP,
            "R149 negative effective vertex rejection",
        ),
        (
            "effectiveMaxVertex <=",
            NATIVE_BACKEND_CPP,
            "R149 effective vertex maximum overflow guard",
        ),
        (
            "startIndex <= maxValue - elementCount",
            NATIVE_BACKEND_CPP,
            "R149 StartIndex plus fetched-index-count overflow guard",
        ),
        (
            "validate_fixed_function_indexed_source_range_snapshot(",
            NATIVE_BACKEND_CPP,
            "R149 stale source-range validator",
        ),
        (
            "R149 indexed source range seals D3D9 DrawIndexedPrimitive arguments",
            CONSTANT_BUFFER_PROBE,
            "R149 positive source-range proof",
        ),
        (
            "R149 indexed source range rejects empty vertex range for live primitives",
            CONSTANT_BUFFER_PROBE,
            "R149 live-draw empty vertex-range rejection",
        ),
        (
            "R149 indexed source range rejects MinVertexIndex NumVertices overflow",
            CONSTANT_BUFFER_PROBE,
            "R149 vertex-range overflow rejection",
        ),
        (
            "R149 indexed source range rejects StartIndex element-count overflow",
            CONSTANT_BUFFER_PROBE,
            "R149 index-range overflow rejection",
        ),
        (
            "R149 indexed source range rejects negative effective BaseVertexIndex range",
            CONSTANT_BUFFER_PROBE,
            "R149 negative effective BaseVertexIndex rejection",
        ),
        (
            "R149 indexed source range rejects effective BaseVertexIndex maximum overflow",
            CONSTANT_BUFFER_PROBE,
            "R149 effective BaseVertexIndex upper overflow rejection",
        ),
        (
            "R149 indexed source range accepts bounded negative BaseVertexIndex",
            CONSTANT_BUFFER_PROBE,
            "R149 legal negative BaseVertexIndex preservation",
        ),
        (
            "primitive != D3DPT_POINTLIST",
            NATIVE_BACKEND_CPP,
            "R149 D3D9 DrawIndexedPrimitive point-list rejection",
        ),
        (
            "R149 indexed source range rejects D3D9 DIP point list",
            CONSTANT_BUFFER_PROBE,
            "R149 unsupported indexed point-list rejection",
        ),
        (
            "R149 indexed source range keeps triangle fan on generated-index path",
            CONSTANT_BUFFER_PROBE,
            "R149 direct-path fan quarantine",
        ),
        (
            "R149 indexed source range snapshot rejects NumVertices drift",
            CONSTANT_BUFFER_PROBE,
            "R149 stale NumVertices identity rejection",
        ),
    ]
    missing_r149_indexed_source_range = [
        meaning
        for token, source, meaning in r149_indexed_source_range_contract
        if token not in source
    ]
    if missing_r149_indexed_source_range:
        raise SystemExit(
            "DX11 R149 indexed source-range contract drift: "
            + ", ".join(missing_r149_indexed_source_range)
        )

    r152_indexed_source_values_contract = [
        ("struct NativeManagedIndexRangeReadiness", NATIVE_BACKEND_HPP,
         "R152 managed IB source-value readiness"),
        ("index_range_readiness(", NATIVE_BACKEND_CPP,
         "R152 managed IB CPU-shadow scanner"),
        ("currentMirror.snapshotToken == mirror.snapshotToken", NATIVE_BACKEND_CPP,
         "R152 exact R119 mirror lineage"),
        ("std::memcpy(&value16, source, sizeof(value16))", NATIVE_BACKEND_CPP,
         "R152 unaligned-safe INDEX16 scan"),
        ("std::memcpy(&value32, source, sizeof(value32))", NATIVE_BACKEND_CPP,
         "R152 unaligned-safe INDEX32 scan"),
        ("value < minVertexIndex || value > maxVertexIndex", NATIVE_BACKEND_CPP,
         "R152 source index declared-range rejection"),
        ("struct NativeFixedFunctionIndexedSourceValueReadiness", NATIVE_BACKEND_HPP,
         "R152 final direct indexed source-value lineage"),
        ("compose_fixed_function_indexed_source_value_readiness(", NATIVE_BACKEND_CPP,
         "R152 final source-value compositor"),
        ("geometry.indexBufferSnapshotToken == sourceValues.mirrorSnapshotToken",
         NATIVE_BACKEND_CPP, "R152 geometry/source IB identity join"),
        ("R152 indexed source values scan exact managed IB range",
         CONSTANT_BUFFER_PROBE, "R152 positive managed IB scan proof"),
        ("R152 indexed source values bind exact IB contents to R150 lineage",
         CONSTANT_BUFFER_PROBE, "R152 positive final lineage proof"),
        ("R152 indexed source values reject index outside declared vertex range",
         CONSTANT_BUFFER_PROBE, "R152 out-of-declared-range rejection"),
        ("R152 indexed source values reject forged managed IB snapshot",
         CONSTANT_BUFFER_PROBE, "R152 forged mirror rejection"),
        ("R152 indexed source values reject geometry IB identity drift",
         CONSTANT_BUFFER_PROBE, "R152 geometry/source mirror mismatch rejection"),
    ]
    missing_r152_indexed_source_values = [
        meaning
        for token, source, meaning in r152_indexed_source_values_contract
        if token not in source
    ]
    if missing_r152_indexed_source_values:
        raise SystemExit(
            "DX11 R152 indexed source-value contract drift: "
            + ", ".join(missing_r152_indexed_source_values)
        )

    r153_indexed_source_binding_contract = [
        ("struct NativeFixedFunctionIndexedSourceBindingReadiness",
         NATIVE_BACKEND_HPP, "R153 live IA/source-value binding identity"),
        ("compose_fixed_function_indexed_source_binding_readiness(",
         NATIVE_BACKEND_CPP, "R153 source-binding compositor"),
        ("validate_fixed_function_indexed_source_value_snapshot(",
         NATIVE_BACKEND_CPP, "R153 revalidates the complete R152 lineage"),
        ("boundDraw.indexFormat == expectedIndexFormat",
         NATIVE_BACKEND_CPP, "R153 D3D9/DXGI index-format equality"),
        ("out.indexOffsetExact = boundDraw.indexOffset == 0u;",
         NATIVE_BACKEND_CPP, "R153 whole-mirror IA offset proof"),
        ("R153 indexed source binding seals live IA format and offset",
         CONSTANT_BUFFER_PROBE, "R153 positive source-binding proof"),
        ("R153 indexed source binding rejects source format drift",
         CONSTANT_BUFFER_PROBE, "R153 source-format drift rejection"),
        ("R153 indexed source binding rejects live IA index offset drift",
         CONSTANT_BUFFER_PROBE, "R153 live IA offset drift rejection"),
    ]
    missing_r153_indexed_source_binding = [
        meaning for token, source, meaning in r153_indexed_source_binding_contract
        if token not in source
    ]
    if missing_r153_indexed_source_binding:
        raise SystemExit(
            "DX11 R153 indexed source-binding contract drift: "
            + ", ".join(missing_r153_indexed_source_binding)
        )

    r158_input_layout_stride_lineage_contract = [
        ("UINT stream0Stride = 0;", PIPELINE_TRANSLATION_HPP,
         "R158 translated input-layout stride identity"),
        ("out.stream0Stride = stream0Stride;", PIPELINE_TRANSLATION_CPP,
         "R158 translator captures caller stream stride"),
        ("hash = mix_readiness_snapshot_token(hash, layout.stream0Stride);",
         NATIVE_BACKEND_CPP, "R158 pipeline identity hashes stride"),
        ("bool vertexStrideMatchesInputLayout{};", NATIVE_BACKEND_HPP,
         "R158 final draw stride lineage gate"),
        ("vertexStride == layout.stream0Stride", NATIVE_BACKEND_CPP,
         "R158 live IA stride must equal translated layout stride"),
        ("boundDraw.vertexStride != boundDraw.inputLayoutStream0Stride",
         NATIVE_BACKEND_CPP, "R158 copied final-readiness stride drift rejection"),
        ("token, boundDraw.inputLayoutStream0Stride",
         NATIVE_BACKEND_CPP, "R203 copied final-readiness integrity hashes translated stride"),
        ("validate_fixed_function_render_target_bound_draw_readiness_integrity(\n                    renderTargetBoundDraw)",
         CONSTANT_BUFFER_PROBE, "R203 WARP positive copied final-readiness integrity proof"),
        ("R158 final draw rejects live IA stride drift from translated layout",
         CONSTANT_BUFFER_PROBE, "R158 live-IA stride mismatch rejection"),
        ("R158 exact IA stride restore keeps final draw snapshot deterministic",
         CONSTANT_BUFFER_PROBE, "R158 exact stride restore proof"),
        ("pipelineChangedStride.inputValid", CONSTANT_BUFFER_PROBE,
         "R158 pipeline input-layout identity includes stride"),
    ]
    missing_r158_input_layout_stride_lineage = [
        meaning
        for token, source, meaning in r158_input_layout_stride_lineage_contract
        if token not in source
    ]
    if missing_r158_input_layout_stride_lineage:
        raise SystemExit(
            "DX11 R158 input-layout stride lineage contract drift: "
            + ", ".join(missing_r158_input_layout_stride_lineage)
        )

    r148_generated_fan_dispatch_contract = [
        (
            "struct NativeFixedFunctionFanDrawDispatchReadiness",
            NATIVE_BACKEND_HPP,
            "R148 generated-fan DrawIndexed tuple identity",
        ),
        (
            "compose_fixed_function_nonindexed_triangle_fan_draw_dispatch_readiness(",
            NATIVE_BACKEND_CPP,
            "R148 nonindexed fan dispatch compositor",
        ),
        (
            "compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness(",
            NATIVE_BACKEND_CPP,
            "R148 indexed fan dispatch compositor",
        ),
        (
            "generated.indexCount == primitiveCount * 3u",
            NATIVE_BACKEND_CPP,
            "R148 generated fan index-count exactness",
        ),
        (
            "generated.sourceIndexSnapshotToken == currentSource.snapshotToken",
            NATIVE_BACKEND_CPP,
            "R148 indexed source provenance remains current at dispatch boundary",
        ),
        (
            "out.startIndexLocation = 0u;",
            NATIVE_BACKEND_CPP,
            "R148 generated index buffer always dispatches from index zero",
        ),
        (
            "R148 generated fan dispatch seals nonindexed DrawIndexed tuple",
            CONSTANT_BUFFER_PROBE,
            "R148 positive nonindexed dispatch proof",
        ),
        (
            "R148 generated fan dispatch rejects nonindexed base-vertex drift",
            CONSTANT_BUFFER_PROBE,
            "R148 nonindexed materialized-base drift rejection",
        ),
        (
            "R148 generated fan dispatch seals indexed DrawIndexed tuple",
            CONSTANT_BUFFER_PROBE,
            "R148 positive indexed dispatch proof",
        ),
        (
            "R148 generated fan dispatch rejects indexed BaseVertexLocation drift",
            CONSTANT_BUFFER_PROBE,
            "R148 indexed BaseVertexLocation drift rejection",
        ),
    ]
    missing_r148_generated_fan_dispatch = [
        meaning
        for token, source, meaning in r148_generated_fan_dispatch_contract
        if token not in source
    ]
    if missing_r148_generated_fan_dispatch:
        raise SystemExit(
            "DX11 R148 generated-fan dispatch contract drift: "
            + ", ".join(missing_r148_generated_fan_dispatch)
        )

    r148_draw_side_effect_isolation_contract = [
        ("streamOutputTargetsClear", NATIVE_BACKEND_HPP,
         "R148 stream-output isolation readiness field"),
        ("predicationClear", NATIVE_BACKEND_HPP,
         "R148 predication isolation readiness field"),
        ("drawSideEffectIsolationReady", NATIVE_BACKEND_HPP,
         "R148 aggregate draw side-effect isolation identity"),
        ("context->SOSetTargets(", NATIVE_BACKEND_CPP,
         "R148 binder clears stream-output targets"),
        ("context->SetPredication(nullptr, FALSE)", NATIVE_BACKEND_CPP,
         "R148 binder clears draw predication"),
        ("context->SOGetTargets(", NATIVE_BACKEND_CPP,
         "R148 live stream-output readback"),
        ("context->GetPredication(", NATIVE_BACKEND_CPP,
         "R148 live predication readback"),
        ("out.drawSideEffectIsolationReady ? 0x148u : 0u",
         NATIVE_BACKEND_CPP, "R148 live-binding token version"),
        ("R148 live SO target drift invalidates fixed-function pipeline binding",
         CONSTANT_BUFFER_PROBE, "R148 SO drift fail-closed proof"),
        ("R148 live predication drift invalidates fixed-function pipeline binding",
         CONSTANT_BUFFER_PROBE, "R148 predication drift fail-closed proof"),
        ("R148 restored SO isolation reproduces pipeline snapshot",
         CONSTANT_BUFFER_PROBE, "R148 SO deterministic restore proof"),
        ("R148 restored predication isolation reproduces pipeline snapshot",
         CONSTANT_BUFFER_PROBE, "R148 predication deterministic restore proof"),
    ]
    missing_r148_draw_side_effect_isolation = [
        meaning
        for token, source, meaning in r148_draw_side_effect_isolation_contract
        if token not in source
    ]
    if missing_r148_draw_side_effect_isolation:
        raise SystemExit(
            "DX11 R148 draw side-effect isolation contract drift: "
            + ", ".join(missing_r148_draw_side_effect_isolation)
        )

    r150_indexed_direct_dispatch_lineage_contract = [
        (
            "struct NativeFixedFunctionIndexedDirectDispatchReadiness",
            NATIVE_BACKEND_HPP,
            "R150 indexed direct dispatch/source-range lineage identity",
        ),
        (
            "compose_fixed_function_indexed_direct_dispatch_readiness(",
            NATIVE_BACKEND_CPP,
            "R150 indexed direct dispatch lineage compositor",
        ),
        (
            "dispatch.startIndexLocation == sourceRange.startIndex",
            NATIVE_BACKEND_CPP,
            "R150 StartIndex lineage equality",
        ),
        (
            "dispatch.baseVertexLocation == sourceRange.baseVertexIndex",
            NATIVE_BACKEND_CPP,
            "R150 BaseVertex lineage equality",
        ),
        (
            "dispatch.elementCount == sourceRange.elementCount",
            NATIVE_BACKEND_CPP,
            "R150 primitive-derived element-count lineage equality",
        ),
        (
            "validate_fixed_function_indexed_direct_dispatch_snapshot(",
            NATIVE_BACKEND_CPP,
            "R150 stale indexed lineage validator",
        ),
        (
            "R150 indexed direct dispatch binds R147 tuple to R149 source range",
            CONSTANT_BUFFER_PROBE,
            "R150 positive lineage proof",
        ),
        (
            "R150 indexed direct dispatch rejects R149 StartIndex lineage drift",
            CONSTANT_BUFFER_PROBE,
            "R150 source-range drift rejection",
        ),
    ]
    missing_r150_indexed_direct_dispatch_lineage = [
        meaning
        for token, source, meaning in r150_indexed_direct_dispatch_lineage_contract
        if token not in source
    ]
    if missing_r150_indexed_direct_dispatch_lineage:
        raise SystemExit(
            "DX11 R150 indexed direct dispatch lineage contract drift: "
            + ", ".join(missing_r150_indexed_direct_dispatch_lineage)
        )

    r151_direct_bound_buffer_capacity_contract = [
        ("UINT byte_width() const noexcept", NATIVE_BACKEND_HPP,
         "R151 managed-buffer byte capacity accessor"),
        ("bool geometryRangeMetadataExact{};", NATIVE_BACKEND_HPP,
         "R151 sealed live IA byte metadata"),
        ("bool bufferRangeExact{};", NATIVE_BACKEND_HPP,
         "R151 direct fetch byte-range gate"),
        ("bool vertexBufferRangeExact{};", NATIVE_BACKEND_HPP,
         "R151 indexed declared vertex-range byte gate"),
        ("out.vertexBufferByteWidth = vertexBuffer.byte_width();", NATIVE_BACKEND_CPP,
         "R151 live vertex-buffer capacity capture"),
        ("out.indexBufferByteWidth = indexBuffer ? indexBuffer->byte_width() : 0u;",
         NATIVE_BACKEND_CPP, "R151 live index-buffer capacity capture"),
        ("R151 validates direct fetches", NATIVE_BACKEND_CPP,
         "R151 widened direct fetch capacity proof"),
        ("countExact && rangeExact && boundDraw.geometryRangeMetadataExact",
         NATIVE_BACKEND_CPP, "R151 byte arithmetic executes only after UINT range proof"),
        ("out.vertexBufferRangeExact =", NATIVE_BACKEND_CPP,
         "R151 indexed declared vertex range capacity proof"),
        ("dispatch, sourceRange, boundDraw", NATIVE_BACKEND_CPP,
         "R151 indexed lineage consumes sealed bound-draw capacity"),
        ("R151 direct indexed dispatch rejects index buffer overrun",
         CONSTANT_BUFFER_PROBE, "R151 indexed IB overrun WARP proof"),
        ("R151 indexed direct lineage rejects declared vertex buffer overrun",
         CONSTANT_BUFFER_PROBE, "R151 indexed VB overrun WARP proof"),
        ("R151 direct nonindexed dispatch rejects vertex buffer overrun",
         CONSTANT_BUFFER_PROBE, "R151 nonindexed VB overrun WARP proof"),
        ("DX11 direct bound-buffer capacity R151: PASS",
         CONSTANT_BUFFER_PROBE, "R151 hosted probe completion marker"),
    ]
    missing_r151_direct_bound_buffer_capacity = [
        meaning for token, source, meaning in r151_direct_bound_buffer_capacity_contract
        if token not in source
    ]
    if missing_r151_direct_bound_buffer_capacity:
        raise SystemExit(
            "DX11 R151 direct bound-buffer capacity contract drift: "
            + ", ".join(missing_r151_direct_bound_buffer_capacity)
        )


    r153_live_index_binding_contract = [
        ("struct NativeFixedFunctionIndexedSourceLiveBindingReadiness",
         NATIVE_BACKEND_HPP, "R153 live IA revalidation identity"),
        ("compose_fixed_function_indexed_source_live_binding_readiness(",
         NATIVE_BACKEND_CPP, "R153 live IA revalidation compositor"),
        ("out.indexMirrorCurrent =", NATIVE_BACKEND_CPP,
         "R153 current R119 mirror identity"),
        ("out.liveIndexBufferExact =", NATIVE_BACKEND_CPP,
         "R153 current IA index-buffer identity"),
        ("out.liveIndexFormatExact =", NATIVE_BACKEND_CPP,
         "R153 current IA index-format identity"),
        ("out.liveIndexOffsetExact =", NATIVE_BACKEND_CPP,
         "R153 current IA index-offset identity"),
        ("R153 live source binding reobserves current IA index mirror",
         CONSTANT_BUFFER_PROBE, "R153 live IA positive proof"),
        ("R153 live source binding rejects post-snapshot IA index drift",
         CONSTANT_BUFFER_PROBE, "R153 stale live IA rejection"),
        ("R153 live source binding restores deterministic IA identity",
         CONSTANT_BUFFER_PROBE, "R153 live IA restore proof"),
    ]
    missing_r153_live_index_binding = [
        meaning
        for token, source, meaning in r153_live_index_binding_contract
        if token not in source
    ]
    if missing_r153_live_index_binding:
        raise SystemExit(
            "DX11 R153 live index-binding contract drift: "
            + ", ".join(missing_r153_live_index_binding)
        )

    r154_nonindexed_fan_vertex_capacity_contract = [
        ("bool vertexBufferRangeExact{};", NATIVE_BACKEND_HPP,
         "R154 generated-fan vertex capacity readiness"),
        ("R154: a generated nonindexed fan encodes source vertices",
         NATIVE_BACKEND_CPP, "R154 deterministic fan source span proof"),
        ("expansion.sourceElementCount - 1u", NATIVE_BACKEND_CPP,
         "R154 fan maximum source vertex identity"),
        ("endByte <= static_cast<std::uint64_t>(vertexBuffer.byte_width())",
         NATIVE_BACKEND_CPP, "R154 managed VB byte-capacity bound"),
        ("out.vertexBufferRangeExact ? 0x154u : 0u", NATIVE_BACKEND_CPP,
         "R154 capacity identity in dispatch token"),
        ("R154 nonindexed fan dispatch rejects vertex buffer overrun",
         CONSTANT_BUFFER_PROBE, "R154 fan VB overrun fail-closed proof"),
        ("R154 nonindexed fan dispatch restores bounded vertex span",
         CONSTANT_BUFFER_PROBE, "R154 deterministic restore proof"),
    ]
    missing_r154_nonindexed_fan_vertex_capacity = [
        meaning
        for token, source, meaning in r154_nonindexed_fan_vertex_capacity_contract
        if token not in source
    ]
    if missing_r154_nonindexed_fan_vertex_capacity:
        raise SystemExit(
            "DX11 R154 nonindexed fan vertex-capacity contract drift: "
            + ", ".join(missing_r154_nonindexed_fan_vertex_capacity)
        )

    r155_indexed_fan_source_content_contract = [
        ("hash_indexed_triangle_fan_window(", NATIVE_BACKEND_HPP,
         "R155 managed source shadow fan-content hasher"),
        ("NativeFixedFunctionIndexedFanSourceContentReadiness", NATIVE_BACKEND_HPP,
         "R155 indexed fan source-content readiness"),
        ("generated.contentHash == expectedExpandedContentHash", NATIVE_BACKEND_CPP,
         "R155 generated immutable IB content comparison"),
        ("out.sourceContentSnapshotToken = sourceContent.snapshotToken;",
         NATIVE_BACKEND_CPP, "R155 source-content lineage reaches dispatch"),
        ("R155 indexed fan source content matches exact managed IB shadow",
         CONSTANT_BUFFER_PROBE, "R155 positive managed-source proof"),
        ("R155 indexed fan source content rejects borrowed token with foreign bytes",
         CONSTANT_BUFFER_PROBE, "R155 pointer/token substitution rejection"),
        ("DX11 indexed fan source content R155: PASS",
         CONSTANT_BUFFER_PROBE, "R155 hosted probe completion marker"),
    ]
    missing_r155_indexed_fan_source_content = [
        meaning
        for token, source, meaning in r155_indexed_fan_source_content_contract
        if token not in source
    ]
    if missing_r155_indexed_fan_source_content:
        raise SystemExit(
            "DX11 R155 indexed fan source-content contract drift: "
            + ", ".join(missing_r155_indexed_fan_source_content)
        )

    r156_dispatch_start = NATIVE_BACKEND_CPP.find(
        "compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness("
    )
    r156_dispatch_end = NATIVE_BACKEND_CPP.find(
        "validate_fixed_function_indexed_triangle_fan_draw_dispatch_snapshot(",
        r156_dispatch_start,
    )
    if (
        r156_dispatch_start < 0
        or r156_dispatch_end < 0
        or r156_dispatch_end <= r156_dispatch_start
    ):
        raise SystemExit(
            "DX11 R156 indexed fan dispatch compositor boundary is missing or reordered"
        )
    r156_indexed_fan_dispatch_body = NATIVE_BACKEND_CPP[
        r156_dispatch_start:r156_dispatch_end
    ]

    # Scope R156 source tokens to the indexed-fan compositor. Several
    # expressions intentionally mirror R154, so whole-file matching could let
    # a partial indexed-fan regression borrow the nonindexed implementation.
    r156_indexed_fan_vertex_capacity_contract = [
        ("R156: indexed fan capacity follows the exact source indices",
         r156_indexed_fan_dispatch_body, "R156 indexed-fan effective vertex capacity proof"),
        ("sourceIndexBuffer.index_range_readiness(",
         r156_indexed_fan_dispatch_body, "R156 exact MANAGED source-index window scan"),
        ("out.sourceValueSnapshotToken = sourceVertexWindow.snapshotToken;",
         r156_indexed_fan_dispatch_body, "R156 source-value snapshot lineage"),
        ("sourceObservedMinIndex", NATIVE_BACKEND_HPP,
         "R156 observed source minimum field"),
        ("sourceObservedMaxIndex", NATIVE_BACKEND_HPP,
         "R156 observed source maximum field"),
        ("out.sourceObservedMinIndex = sourceVertexWindow.observedMinIndex;",
         r156_indexed_fan_dispatch_body, "R156 observed source minimum retained in dispatch"),
        ("out.sourceObservedMaxIndex = sourceVertexWindow.observedMaxIndex;",
         r156_indexed_fan_dispatch_body, "R156 observed source maximum retained in dispatch"),
        ("token, out.sourceObservedMinIndex",
         r156_indexed_fan_dispatch_body, "R156 source minimum participates in snapshot"),
        ("token, out.sourceObservedMaxIndex",
         r156_indexed_fan_dispatch_body, "R156 source maximum participates in snapshot"),
        ("indexedFanDispatch.sourceValueSnapshotToken != 0",
         CONSTANT_BUFFER_PROBE, "R156 positive source-window token proof"),
        ("indexedFanVertexOverrun.sourceValueSnapshotToken != 0",
         CONSTANT_BUFFER_PROBE, "R156 overrun retains source-window evidence"),
        ("effectiveMinVertex >= 0",
         r156_indexed_fan_dispatch_body, "R156 negative effective vertex rejection"),
        ("endByte <= static_cast<std::uint64_t>(vertexBuffer.byte_width())",
         r156_indexed_fan_dispatch_body, "R156 indexed-fan VB byte capacity bound"),
        ("out.vertexBufferRangeExact ? 0x156u : 0u",
         r156_indexed_fan_dispatch_body, "R156 capacity identity in dispatch token"),
        ("R156 indexed fan capacity fixture straddles managed VB boundary",
         CONSTANT_BUFFER_PROBE, "R156 hosted fixture crosses exact VB boundary"),
        ("indexedFanObservedMaxIndex = 9u",
         CONSTANT_BUFFER_PROBE, "R156 hosted fixture bounded source maximum"),
        ("R156 indexed fan dispatch rejects effective vertex buffer overrun",
         CONSTANT_BUFFER_PROBE, "R156 effective VB overrun fail-closed proof"),
        ("DX11 indexed fan vertex capacity R156: PASS",
         CONSTANT_BUFFER_PROBE, "R156 hosted probe completion marker"),
    ]
    missing_r156_indexed_fan_vertex_capacity = [
        meaning
        for token, source, meaning in r156_indexed_fan_vertex_capacity_contract
        if token not in source
    ]
    if missing_r156_indexed_fan_vertex_capacity:
        raise SystemExit(
            "DX11 R156 indexed fan vertex-capacity contract drift: "
            + ", ".join(missing_r156_indexed_fan_vertex_capacity)
        )

    indexed_fan_declared_vertex_range_contract = [
        ("DX11-FAN-DECLARED-RANGE: preserve D3D9 indexed-fan declared vertex range",
         r156_indexed_fan_dispatch_body, "R158 declared source-range proof"),
        ("sourceDeclaredVertexRangeExact", NATIVE_BACKEND_HPP,
         "R158 declared-range readiness field"),
        ("sourceValuesWithinDeclaredRange", NATIVE_BACKEND_HPP,
         "R158 exact source-value range field"),
        ("out.sourceMinVertexIndex = minVertexIndex;",
         r156_indexed_fan_dispatch_body, "R158 MinVertexIndex lineage"),
        ("out.sourceNumVertices = numVertices;",
         r156_indexed_fan_dispatch_body, "R158 NumVertices lineage"),
        ("expansion.sourceElementCount, out.sourceMinVertexIndex",
         r156_indexed_fan_dispatch_body, "R158 bounded MANAGED source scan"),
        ("out.sourceDeclaredVertexRangeExact ? 0x46414e52u : 0u",
         r156_indexed_fan_dispatch_body, "R158 declared range in snapshot"),
        ("out.sourceValuesWithinDeclaredRange ? 0x46414e53u : 0u",
         r156_indexed_fan_dispatch_body, "R158 source-value proof in snapshot"),
        ("indexed fan dispatch rejects source index outside D3D9 declared vertex range",
         CONSTANT_BUFFER_PROBE, "R158 fail-closed declared range probe"),
        ("DX11 indexed fan declared vertex range: PASS",
         CONSTANT_BUFFER_PROBE, "R158 hosted probe completion marker"),
    ]
    missing_indexed_fan_declared_vertex_range = [
        meaning
        for token, source, meaning in indexed_fan_declared_vertex_range_contract
        if token not in source
    ]
    if missing_indexed_fan_declared_vertex_range:
        raise SystemExit(
            "DX11 indexed fan declared vertex-range contract drift: "
            + ", ".join(missing_indexed_fan_declared_vertex_range)
        )

    r160_indexed_fan_declared_vb_capacity_contract = [
        ("bool sourceDeclaredVertexBufferRangeExact{};", NATIVE_BACKEND_HPP,
         "R160 declared-window VB capacity readiness"),
        ("R160: MinVertexIndex/NumVertices describe the complete D3D9 source",
         r156_indexed_fan_dispatch_body, "R160 declared D3D9 window proof"),
        ("effectiveDeclaredMaxVertex", r156_indexed_fan_dispatch_body,
         "R160 BaseVertexLocation declared maximum"),
        ("declaredEndByte <=", r156_indexed_fan_dispatch_body,
         "R160 managed VB byte-capacity bound"),
        ("out.sourceDeclaredVertexBufferRangeExact ? 0x160u : 0u",
         r156_indexed_fan_dispatch_body, "R160 declared-capacity snapshot identity"),
        ("indexedFanDispatch.sourceDeclaredVertexBufferRangeExact",
         CONSTANT_BUFFER_PROBE, "R160 positive declared-capacity proof"),
        ("R160 indexed fan rejects declared vertex window beyond managed VB",
         CONSTANT_BUFFER_PROBE, "R160 declared-capacity overrun rejection"),
        ("DX11 indexed fan declared VB capacity R160: PASS",
         CONSTANT_BUFFER_PROBE, "R160 hosted probe completion marker"),
    ]
    missing_r160_indexed_fan_declared_vb_capacity = [
        meaning
        for token, source, meaning in r160_indexed_fan_declared_vb_capacity_contract
        if token not in source
    ]
    if missing_r160_indexed_fan_declared_vb_capacity:
        raise SystemExit(
            "DX11 R160 indexed fan declared VB-capacity contract drift: "
            + ", ".join(missing_r160_indexed_fan_declared_vb_capacity)
        )

    r155_direct_pointlist_raster_contract = [
        ("bool pointRasterSemanticsExact{};", NATIVE_BACKEND_HPP,
         "R155 direct point-list raster semantic gate"),
        ("out.pointRasterSemanticsExact = primitive != D3DPT_POINTLIST;",
         NATIVE_BACKEND_CPP, "R155 POINTLIST fail-closed assignment"),
        ("out.pointRasterSemanticsExact &&", NATIVE_BACKEND_CPP,
         "R155 readiness requires proven point raster semantics"),
        ("out.pointRasterSemanticsExact ? 0x155u : 0u", NATIVE_BACKEND_CPP,
         "R155 direct-dispatch snapshot contract version"),
        ("R155 point-list fixture reaches exact dormant IA topology",
         CONSTANT_BUFFER_PROBE, "R155 positive topology fixture"),
        ("R155 direct point-list raster semantics remain fail closed", CONSTANT_BUFFER_PROBE,
         "R155 point raster fail-closed proof"),
    ]
    missing_r155_direct_pointlist_raster = [
        meaning
        for token, source, meaning in r155_direct_pointlist_raster_contract
        if token not in source
    ]
    if missing_r155_direct_pointlist_raster:
        raise SystemExit(
            "DX11 R155 direct POINTLIST raster contract drift: "
            + ", ".join(missing_r155_direct_pointlist_raster)
        )

    r157_direct_line_raster_contract = [
        ("bool lineRasterSemanticsExact{};", NATIVE_BACKEND_HPP,
         "R157 direct line-raster semantic gate"),
        ("primitive != D3DPT_LINELIST && primitive != D3DPT_LINESTRIP",
         NATIVE_BACKEND_CPP, "R157 line-list/line-strip fail-closed assignment"),
        ("out.lineRasterSemanticsExact &&", NATIVE_BACKEND_CPP,
         "R157 readiness requires proven line-raster semantics"),
        ("out.lineRasterSemanticsExact ? 0x157u : 0u", NATIVE_BACKEND_CPP,
         "R157 direct-dispatch snapshot contract version"),
        ("R157 line fixture reaches exact dormant IA topology",
         CONSTANT_BUFFER_PROBE, "R157 exact line topology fixture"),
        ("R157 direct line raster semantics remain fail closed",
         CONSTANT_BUFFER_PROBE, "R157 line-raster fail-closed proof"),
        ("DX11 direct line raster semantics R157: PASS",
         CONSTANT_BUFFER_PROBE, "R157 hosted probe completion marker"),
    ]
    missing_r157_direct_line_raster = [
        meaning
        for token, source, meaning in r157_direct_line_raster_contract
        if token not in source
    ]
    if missing_r157_direct_line_raster:
        raise SystemExit(
            "DX11 R157 direct line-raster contract drift: "
            + ", ".join(missing_r157_direct_line_raster)
        )

    runtime_textured_draw_users = []
    for source_path in (ROOT / "src").rglob("*.cpp"):
        if source_path == DX11 / "native_backend.cpp":
            continue
        runtime_source = source_path.read_text(encoding="utf-8")
        if (
            "compose_fixed_function_textured_draw_readiness(" in runtime_source
            or "compose_fixed_function_multistage_textured_draw_readiness(" in runtime_source
            or "validate_fixed_function_multistage_textured_draw_snapshot(" in runtime_source
            or "observe_fixed_function_texture_binding_set(" in runtime_source
            or "validate_fixed_function_texture_binding_set_snapshot(" in runtime_source
            or "compose_fixed_function_bound_draw_readiness(" in runtime_source
            or "compose_fixed_function_same_context_bound_draw_readiness(" in runtime_source
            or "compose_fixed_function_complete_bound_draw_readiness(" in runtime_source
            or "validate_fixed_function_complete_bound_draw_snapshot(" in runtime_source
            or "compose_fixed_function_fully_bound_draw_readiness(" in runtime_source
            or "validate_fixed_function_fully_bound_draw_snapshot(" in runtime_source
            or "compose_fixed_function_render_target_bound_draw_readiness(" in runtime_source
            or "validate_fixed_function_render_target_bound_draw_snapshot(" in runtime_source
            or "compose_fixed_function_direct_draw_dispatch_readiness(" in runtime_source
            or "validate_fixed_function_direct_draw_dispatch_snapshot(" in runtime_source
            or "compose_fixed_function_indexed_source_range_readiness(" in runtime_source
            or "validate_fixed_function_indexed_source_range_snapshot(" in runtime_source
            or "compose_fixed_function_indexed_direct_dispatch_readiness(" in runtime_source
            or "validate_fixed_function_indexed_direct_dispatch_snapshot(" in runtime_source
            or "compose_fixed_function_indexed_source_value_readiness(" in runtime_source
            or "validate_fixed_function_indexed_source_value_snapshot(" in runtime_source
            or "compose_fixed_function_indexed_source_binding_readiness(" in runtime_source
            or "validate_fixed_function_indexed_source_binding_snapshot(" in runtime_source
            or "compose_fixed_function_indexed_source_live_binding_readiness(" in runtime_source
            or "validate_fixed_function_indexed_source_live_binding_snapshot(" in runtime_source
            or ".index_range_readiness(" in runtime_source
            or ".validate_index_range_readiness_snapshot(" in runtime_source
            or "compose_fixed_function_nonindexed_triangle_fan_draw_dispatch_readiness(" in runtime_source
            or "validate_fixed_function_nonindexed_triangle_fan_draw_dispatch_snapshot(" in runtime_source
            or "compose_fixed_function_indexed_triangle_fan_draw_dispatch_readiness(" in runtime_source
            or "validate_fixed_function_indexed_triangle_fan_draw_dispatch_snapshot(" in runtime_source
            or "compose_fixed_function_final_nonindexed_triangle_fan_bound_draw_readiness(" in runtime_source
            or "validate_fixed_function_final_nonindexed_triangle_fan_bound_draw_snapshot(" in runtime_source
            or "compose_fixed_function_final_indexed_triangle_fan_bound_draw_readiness(" in runtime_source
            or "validate_fixed_function_final_indexed_triangle_fan_bound_draw_snapshot(" in runtime_source
            or "upload_transform_for_observation(" in runtime_source
            or "compose_fixed_function_complete_nonindexed_triangle_fan_bound_draw_readiness(" in runtime_source
            or "validate_fixed_function_complete_nonindexed_triangle_fan_bound_draw_snapshot(" in runtime_source
            or "compose_fixed_function_complete_indexed_triangle_fan_bound_draw_readiness(" in runtime_source
            or "validate_fixed_function_complete_indexed_triangle_fan_bound_draw_snapshot(" in runtime_source
            or "validate_fixed_function_same_context_bound_draw_snapshot(" in runtime_source
            or "bind_fixed_function_geometry_for_observation(" in runtime_source
            or "observe_fixed_function_geometry_binding(" in runtime_source
            or "validate_fixed_function_geometry_binding_snapshot(" in runtime_source
            or "compose_fixed_function_indexed_triangle_fan_geometry_readiness(" in runtime_source
            or "validate_fixed_function_indexed_triangle_fan_geometry_snapshot(" in runtime_source
            or ".binding_readiness(" in runtime_source
        ):
            runtime_textured_draw_users.append(
                source_path.relative_to(ROOT).as_posix()
            )
    if runtime_textured_draw_users:
        raise SystemExit(
            "DX11 R132/R133/R134/R136/R137/R138/R139/R140/R141/R142/R143/R144/R145/R146 dormant binding readiness gained a production "
            "caller before activation gate: " + ", ".join(runtime_textured_draw_users)
        )

    # R141 adds a generated triangle-fan owner whose bind() mutates IA state and
    # whose live-binding observer/validator are still dormant activation
    # evidence. Keep all three APIs out of production source until the native
    # Draw activation gate is explicitly opened.
    runtime_generated_fan_users = []
    generated_fan_internal_sources = {
        DX11 / "triangle_fan_index_buffer.cpp",
        DX11 / "native_backend.cpp",
    }
    for source_path in (ROOT / "src").rglob("*.cpp"):
        # The generated-fan owner implements its own observer, while
        # native_backend.cpp composes that dormant R142/R143 evidence. Neither
        # file is a production game caller. Keep the quarantine on every other
        # translation unit until native Draw* activation is explicitly opened.
        if source_path in generated_fan_internal_sources:
            continue
        runtime_source = source_path.read_text(encoding="utf-8")
        if (
            "NativeTriangleFanIndexBuffer" in runtime_source
            and (
                ".bind(" in runtime_source
                or ".binding_readiness(" in runtime_source
                or ".validate_binding_snapshot(" in runtime_source
            )
        ):
            runtime_generated_fan_users.append(
                source_path.relative_to(ROOT).as_posix()
            )
    if runtime_generated_fan_users:
        raise SystemExit(
            "DX11 R141 generated triangle-fan live IA APIs gained a production "
            "caller before activation gate: "
            + ", ".join(runtime_generated_fan_users)
        )

    stencil_snapshot_contract = {
        "DWORD stencilReadMask = 0xFFFFFFFFu;": "stencil read mask snapshot",
        "DWORD stencilRef = 0;": "dynamic stencil reference snapshot",
        "DWORD stencilFunc = D3DCMP_ALWAYS;": "clockwise/front stencil function snapshot",
        "DWORD twoSidedStencilMode = FALSE;": "two-sided stencil mode snapshot",
        "DWORD ccwStencilFunc = D3DCMP_ALWAYS;": "counterclockwise/back stencil function snapshot",
    }
    missing_stencil_contract = [
        meaning
        for token, meaning in stencil_snapshot_contract.items()
        if token not in D3D9_DRAW_STATE_HPP
    ]
    stencil_capture_contract = {
        "read(D3DRS_STENCILMASK, out.stencilReadMask);": "capture stencil read mask",
        "read(D3DRS_STENCILREF, out.stencilRef);": "capture stencil reference",
        "read(D3DRS_STENCILFUNC, out.stencilFunc);": "capture clockwise/front stencil function",
        "read(D3DRS_CCW_STENCILFUNC, out.ccwStencilFunc);": "capture counterclockwise/back stencil function",
    }
    missing_stencil_contract += [
        meaning
        for token, meaning in stencil_capture_contract.items()
        if token not in D3D9_RENDER_STATE_CAPTURE
    ]
    stencil_translation_contract = {
        "translate_stencil_op(": "D3D9 stencil-op translation helper",
        "case D3DSTENCILOP_INCRSAT: return {D3D11_STENCIL_OP_INCR_SAT, true};":
            "saturating increment stencil mapping",
        "out.stencil_ref = source.stencilRef & 0xFFu;":
            "dynamic stencil reference propagation",
        "source.twoSidedStencilMode != FALSE": "two-sided stencil branch",
        "source.cullMode != D3DCULL_NONE": "two-sided stencil cull fail-closed guard",
        "out.depth_stencil.BackFace = out.depth_stencil.FrontFace;":
            "one-sided stencil front/back equivalence",
    }
    stencil_translation_text = STATE_TRANSLATION_CPP + "\n" + PIPELINE_TRANSLATION_CPP
    missing_stencil_contract += [
        meaning
        for token, meaning in stencil_translation_contract.items()
        if token not in stencil_translation_text
    ]
    stencil_semantic_contract = {
        "one-sided stencil did not translate exactly": "one-sided positive semantic smoke",
        "two-sided stencil did not translate exactly": "two-sided positive semantic smoke",
        "invalid stencil op must fail closed": "invalid stencil-op negative semantic smoke",
        "two-sided stencil with culling must fail closed":
            "two-sided/culling combination stays fail-closed",
    }
    missing_stencil_contract += [
        meaning
        for token, meaning in stencil_semantic_contract.items()
        if token not in SEMANTIC_SMOKE
    ]
    if missing_stencil_contract:
        raise SystemExit(
            "DX11 stencil translation contract drift: "
            + ", ".join(missing_stencil_contract)
        )

    census_r73_contract = {
        "ResourceBehaviorUnsupportedSamples": "unmodelled descriptor counter",
        "ResourceMutationTelemetryRequiredSamples": "lock/update blocker counter",
        "ResourceManagedShadowRequiredSamples": "managed shadow blocker counter",
        "ManagedTextureShadowRequiredSamples": "R106 managed texture shadow-required sample counter",
        "ManagedTextureShadowReadySamples": "R106 managed texture shadow-ready sample counter",
        "ManagedTextureShadowPendingSamples": "R106 managed texture shadow-pending sample counter",
        "TextureStageManagedShadowRequiredResources": "R106 bound managed stage requirement counter",
        "TextureStageManagedShadowReadyResources": "R106 bound managed stage ready counter",
        "TextureStageManagedShadowPendingResources": "R106 bound managed stage pending counter",
        "translate_resource_behavior": "per-bound-resource behavior classification",
        "mutationTelemetryRequired": "exact-sample mutation gate",
        "managedShadowRequired": "exact-sample managed lifetime gate",
    }
    missing_r73 = [
        meaning for token, meaning in census_r73_contract.items() if token not in census
    ]
    if missing_r73:
        raise SystemExit(
            "DX11 R73 census resource gate drift: " + ", ".join(missing_r73)
        )

    census_header = (DX11 / "runtime_census.hpp").read_text(encoding="utf-8")
    mutation_api_contract = {
        "observe_vertex_buffer_lock": "VB successful Lock observation API",
        "observe_vertex_buffer_unlock": "VB successful Unlock observation API",
        "forget_vertex_buffer_mutation": "VB release cleanup API",
        "observe_index_buffer_lock": "IB successful Lock observation API",
        "observe_index_buffer_unlock": "IB successful Unlock observation API",
        "forget_index_buffer_mutation": "IB release cleanup API",
        "observe_texture_lock_rect": "texture LockRect observation API",
        "observe_texture_unlock_rect": "texture UnlockRect observation API",
        "observe_managed_texture_lock_rect": "R105 managed LockRect shadow API",
        "stage_managed_texture_unlock_rect": "R105 pre-Unlock staging API",
        "finish_managed_texture_unlock_rect": "R105 post-Unlock commit API",
        "forget_texture_mutation": "R105 texture Release cleanup API",
        "clear_managed_texture_shadows": "R105 renderer rollback cleanup API",
        "observe_update_texture": "device UpdateTexture observation API",
        "observe_update_surface": "device UpdateSurface observation API",
        "observe_device_reset_generation": "successful Reset generation observation API",
    }
    missing_mutation_api = [
        meaning
        for token, meaning in mutation_api_contract.items()
        if token not in census_header or token not in census
    ]
    if missing_mutation_api:
        raise SystemExit(
            "DX11 R74 mutation observation API drift: "
            + ", ".join(missing_mutation_api)
        )

    mutation_counter_contract = {
        "ResourceMutationWriteUnlocks": "successful write Lock/Unlock counter",
        "ResourceMutationReadOnlyUnlocks": "successful READONLY Lock/Unlock counter",
        "ResourceMutationDiscardWriteUnlocks": "successful DISCARD write counter",
        "ResourceMutationNoOverwriteWriteUnlocks": "successful NOOVERWRITE write counter",
        "ResourceMutationPlanExactUnlocks": "exact D3D11 mutation-plan counter",
        "ResourceMutationPlanUnsupportedUnlocks": "unsupported mutation-plan counter",
        "ResourceMutationManagedShadowUnlocks": "managed CPU-shadow dependency counter",
        "ResourceMutationMapWriteUnlocks": "D3D11 MAP_WRITE counter",
        "ResourceMutationMapDiscardUnlocks": "D3D11 MAP_WRITE_DISCARD counter",
        "ResourceMutationMapNoOverwriteUnlocks": "D3D11 MAP_WRITE_NO_OVERWRITE counter",
        "ResourceMutationUpdateSubresourceUnlocks": "UpdateSubresource counter",
        "ResourceTextureMutationWriteUnlocks": "texture successful write LockRect/UnlockRect counter",
        "ResourceTextureMutationReadOnlyUnlocks": "texture successful READONLY LockRect/UnlockRect counter",
        "ResourceTextureMutationDescriptorFailures": "texture mutation descriptor failure counter",
        "ResourceUpdateTextureSuccesses": "UpdateTexture success counter",
        "ResourceUpdateTextureFailures": "UpdateTexture failure counter",
        "ResourceUpdateSurfaceSuccesses": "UpdateSurface success counter",
        "ResourceUpdateSurfaceFailures": "UpdateSurface failure counter",
        "ResourceManagedShadowWrites": "managed CPU-shadow write evidence counter",
        "ResourceManagedShadowReads": "managed CPU-shadow read evidence counter",
        "ResourceManagedResetSuccesses": "successful Reset generation counter",
        "ResourceManagedResetShadowPreserved": "CPU-shadow Reset survival counter",
        "ManagedLifetimeEvidence": "runtime managed lifetime evidence state",
        "advance_managed_device_generation": "runtime generation transition",
        "translate_buffer_mutation": "runtime R75 mutation-plan classification",
    }
    missing_mutation_counters = [
        meaning
        for token, meaning in mutation_counter_contract.items()
        if token not in census
    ]
    if missing_mutation_counters:
        raise SystemExit(
            "DX11 R74 mutation counters drift: "
            + ", ".join(missing_mutation_counters)
        )

    for renderer_name in (
        "stereo_renderer_r30.cpp",
        "stereo_renderer_r30_r26_safe.cpp",
    ):
        renderer = (ROOT / "src" / "vr" / "d3d9" / renderer_name).read_text(
            encoding="utf-8"
        )
        bridge_contract = {
            'vr/d3d11/runtime_census.hpp': "DX11 census observer include",
            "observe_vertex_buffer_lock": "VB Lock bridge",
            "observe_vertex_buffer_unlock": "VB Unlock bridge",
            "forget_vertex_buffer_mutation": "VB release cleanup bridge",
            "observe_index_buffer_lock": "IB Lock bridge",
            "observe_index_buffer_unlock": "IB Unlock bridge",
            "forget_index_buffer_mutation": "IB release cleanup bridge",
            "R30CreateTextureVtableIndex": "CreateTexture hook index",
            "R30TextureReleaseVtableIndex": "Texture Release hook index",
            "R30TextureLockRectVtableIndex": "Texture LockRect hook index",
            "R30TextureUnlockRectVtableIndex": "Texture UnlockRect hook index",
            "R30UpdateSurfaceVtableIndex": "UpdateSurface hook index",
            "R30UpdateTextureVtableIndex": "UpdateTexture hook index",
            "observe_texture_lock_rect": "texture LockRect bridge",
            "observe_texture_unlock_rect": "texture UnlockRect bridge",
            "observe_managed_texture_lock_rect": "R105 managed LockRect capture bridge",
            "stage_managed_texture_unlock_rect": "R105 pre-Unlock staging bridge",
            "finish_managed_texture_unlock_rect": "R105 post-Unlock commit bridge",
            "forget_texture_mutation": "R105 texture Release cleanup bridge",
            "clear_managed_texture_shadows": "R105 rollback registry cleanup bridge",
            "observe_update_texture": "UpdateTexture bridge",
            "observe_update_surface": "UpdateSurface bridge",
            "observe_device_reset_generation": "successful Reset generation bridge",
        }
        missing_bridge = [
            meaning
            for token, meaning in bridge_contract.items()
            if token not in renderer
        ]
        if missing_bridge:
            raise SystemExit(
                f"DX11 R74 mutation bridge drift in {renderer_name}: "
                + ", ".join(missing_bridge)
            )

        # R105 permits census-only CPU-shadow capture through runtime_census,
        # but the R30 renderer must still not own the shadow class, upload a
        # D3D11 mirror, bind an SRV, or route a native draw.
        r105_forbidden_renderer_tokens = {
            "NativeManagedTextureShadow": "direct managed shadow owner construction",
            "NativeManagedTextureRegistry": "direct registry ownership in renderer",
            "begin_source_lock(": "direct source-lock method call",
            "commit_source_unlock(": "direct source-unlock commit call",
            "recreate_and_upload_mirror(": "managed mirror upload activation",
            "mirror_srv()": "managed SRV binding surface",
            "PSSetShaderResources": "native texture binding activation",
        }
        active_r105_tokens = [
            meaning
            for token, meaning in r105_forbidden_renderer_tokens.items()
            if token in renderer
        ]
        if active_r105_tokens:
            raise SystemExit(
                f"DX11 R105 native draw/mirror activated early in {renderer_name}: "
                + ", ".join(active_r105_tokens)
            )

        r105_renderer_contract = {
            "R30TextureReleaseHook": "texture Release hook ownership",
            "R30TextureReleaseDest": "texture Release cleanup detour",
            "observe_managed_texture_lock_rect": "managed LockRect registry begin",
            "stage_managed_texture_unlock_rect": "pre-Unlock byte staging",
            "finish_managed_texture_unlock_rect": "post-Unlock HRESULT commit",
            "forget_texture_mutation": "zero-ref texture registry cleanup",
            "clear_managed_texture_shadows": "renderer rollback registry cleanup",
        }
        missing_r105_renderer = [
            meaning
            for token, meaning in r105_renderer_contract.items()
            if token not in renderer
        ]
        if missing_r105_renderer:
            raise SystemExit(
                f"DX11 R105 managed registry bridge drift in {renderer_name}: "
                + ", ".join(missing_r105_renderer)
            )

        stage_pos = renderer.find("stage_managed_texture_unlock_rect")
        real_unlock_pos = renderer.find(
            "R30TextureUnlockRectHook.stdcall<HRESULT>", stage_pos
        )
        finish_pos = renderer.find(
            "finish_managed_texture_unlock_rect", real_unlock_pos
        )
        if not (
            stage_pos >= 0 and
            real_unlock_pos > stage_pos and
            finish_pos > real_unlock_pos
        ):
            raise SystemExit(
                f"DX11 R105 Unlock ordering drift in {renderer_name}: "
                "stage bytes before real UnlockRect, commit after HRESULT"
            )

    analyzer = (ROOT / "tools" / "analyze_dx11_census.py").read_text(
        encoding="utf-8"
    )
    analyzer_test = (
        ROOT / "tools" / "test_analyze_dx11_census.py"
    ).read_text(encoding="utf-8")
    r194_arg0_analyzer_contract = [
        ("|160|173|194|197)", analyzer,
         "R194/R197 fixed-function log revision parser"),
        ("?P<colorArg0>", analyzer,
         "R194 COLORARG0 parser group"),
        ("?P<alphaArg0>", analyzer,
         "R194 ALPHAARG0 parser group"),
        ('"colorArg0", "colorArg1", "colorArg2"', analyzer,
         "R194 color ARG0 hexadecimal conversion"),
        ('"alphaArg0", "alphaArg1", "alphaArg2"', analyzer,
         "R194 alpha ARG0 hexadecimal conversion"),
        ("r194_arg0 = run_case(", analyzer_test,
         "R194 ARG0 analyzer regression fixture"),
        ('r194_stage["colorArg0"] == 0x00000002', analyzer_test,
         "R194 COLORARG0 analyzer assertion"),
        ('r194_stage["alphaArg0"] == 0x00000001', analyzer_test,
         "R194 ALPHAARG0 analyzer assertion"),
    ]
    missing_r194_arg0_analyzer = [
        meaning
        for token, source, meaning in r194_arg0_analyzer_contract
        if token not in source
    ]
    if missing_r194_arg0_analyzer:
        raise SystemExit(
            "DX11 R194 ARG0 census analyzer contract drift: "
            + ", ".join(missing_r194_arg0_analyzer)
        )

    # Keep the enum-owned unsupported bitset, runtime summary, parser schema
    # and aggregate accounting structurally synchronized. Earlier R166/R170
    # guards pinned specific tails; this parity check makes a future new bit
    # fail closed unless every consumer is extended in the same change.
    unsupported_schema_errors = []
    unsupported_summary_match = re.search(
        r"unsupported\[([A-Za-z0-9_]+=\{\}(?:,[A-Za-z0-9_]+=\{\})*)\]",
        RUNTIME_CENSUS,
    )
    runtime_unsupported_labels = []
    if not unsupported_summary_match:
        unsupported_schema_errors.append(
            "runtime census unsupported summary labels are not discoverable"
        )
    else:
        runtime_unsupported_labels = [
            item.split("=", 1)[0]
            for item in unsupported_summary_match.group(1).split(",")
        ]
        if len(runtime_unsupported_labels) != len(pipeline_unsupported_bits):
            unsupported_schema_errors.append(
                "runtime census unsupported label count must equal "
                "PipelineUnsupportedBitCount"
            )

    summary_start = RUNTIME_CENSUS.find('"VR DX11 R120 census:')
    summary_end = (
        RUNTIME_CENSUS.find(");", summary_start)
        if summary_start >= 0 else -1
    )
    if summary_start < 0 or summary_end < 0:
        unsupported_schema_errors.append(
            "runtime census R120 summary call is not discoverable"
        )
    else:
        summary_call = RUNTIME_CENSUS[summary_start:summary_end + 2]
        runtime_unsupported_indices = [
            int(value)
            for value in re.findall(
                r"unsupported\[(\d+)\]", summary_call
            )
        ]
        if runtime_unsupported_indices != expected_pipeline_bits:
            unsupported_schema_errors.append(
                "runtime census summary arguments must enumerate every "
                "PipelineUnsupported bit exactly once in order"
            )

    parser_start = analyzer.find('r"unsupported\\[')
    parser_end = (
        analyzer.find("\n)\n\nBOOTSTRAP_RE", parser_start)
        if parser_start >= 0 else -1
    )
    if parser_start < 0 or parser_end < 0:
        unsupported_schema_errors.append(
            "census analyzer unsupported parser block is not discoverable"
        )
        analyzer_unsupported_groups = []
    else:
        analyzer_unsupported_groups = re.findall(
            r"\?P<([A-Za-z_][A-Za-z0-9_]*)>",
            analyzer[parser_start:parser_end],
        )
        if len(analyzer_unsupported_groups) != len(pipeline_unsupported_bits):
            unsupported_schema_errors.append(
                "census analyzer unsupported group count must equal "
                "PipelineUnsupportedBitCount"
            )

    unsupported_keys_start = analyzer.find("unsupported_keys = [")
    unsupported_keys_end = (
        analyzer.find("]\n        unsupported_total", unsupported_keys_start)
        if unsupported_keys_start >= 0 else -1
    )
    if unsupported_keys_start < 0 or unsupported_keys_end < 0:
        unsupported_schema_errors.append(
            "census analyzer unsupported aggregate key list is not discoverable"
        )
    else:
        aggregate_keys = re.findall(
            r'"([A-Za-z_][A-Za-z0-9_]*)"',
            analyzer[unsupported_keys_start:unsupported_keys_end],
        )
        if (
            analyzer_unsupported_groups and
            aggregate_keys[-len(analyzer_unsupported_groups):]
            != analyzer_unsupported_groups
        ):
            unsupported_schema_errors.append(
                "census analyzer unsupported parser groups must be the "
                "ordered aggregate tail"
            )

    if (
        runtime_unsupported_labels and
        analyzer_unsupported_groups and
        runtime_unsupported_labels != analyzer_unsupported_groups
    ):
        unsupported_schema_errors.append(
            "runtime unsupported labels and analyzer named groups must "
            "match exactly in order"
        )

    if unsupported_schema_errors:
        raise SystemExit(
            "DX11 unsupported census schema parity drift: "
            + ", ".join(unsupported_schema_errors)
        )

    current_unsupported_analyzer_contract = [
        ("?P<dualSource>", analyzer,
         "current unsupported dual-source parser"),
        ("?P<shadeMode>", analyzer,
         "current unsupported shade-mode parser"),
        ("?P<clipping>", analyzer,
         "current unsupported clipping parser"),
        ("?P<depthBias>", analyzer,
         "current unsupported depth-bias parser"),
        ("?P<vertexBlend>", analyzer,
         "current unsupported vertex-blend parser"),
        ("?P<dither>", analyzer,
         "current unsupported dither parser"),
        ("?P<texCoordWrap>", analyzer,
         "R170 texture-coordinate wrap parser"),
        ("?P<mrtColorWrite>", analyzer,
         "MRT color-write parser"),
        ("?P<specular>", analyzer,
         "R204 dedicated specular parser"),
        (
            '"dualSource",\n            "shadeMode",\n'
            '            "clipping",\n            "depthBias",\n'
            '            "vertexBlend",\n            "dither",\n'
            '            "texCoordWrap",\n            "mrtColorWrite",\n'
            '            "specular",',
            analyzer,
            "current unsupported fields participate in aggregate exactness",
        ),
        ("extended_unsupported = run_case(", analyzer_test,
         "current unsupported-tail analyzer regression fixture"),
        ('extended_unsupported["UnsupportedTotalLatest"] == 35',
         analyzer_test,
         "current unsupported-tail aggregate regression assertion"),
        ('extended_unsupported["LatestSummary"]["specular"] == 8',
         analyzer_test,
         "R204 dedicated specular analyzer regression assertion"),
        ("r170_wrap = run_case(", analyzer_test,
         "R170 wrap analyzer regression fixture"),
        ('r170_wrap["UnsupportedTotalLatest"] == 8',
         analyzer_test,
         "R170 wrap analyzer aggregate assertion"),
    ]
    missing_current_unsupported_analyzer = [
        meaning
        for token, source, meaning in current_unsupported_analyzer_contract
        if token not in source
    ]
    if missing_current_unsupported_analyzer:
        raise SystemExit(
            "DX11 current unsupported census analyzer contract drift: "
            + ", ".join(missing_current_unsupported_analyzer)
        )
    if '"NativeDrawPathActivationAllowed": False' not in analyzer:
        raise SystemExit("DX11 census must remain observation-only")
    if '"OBSERVED_SAMPLE_TRANSLATION_EXACT"' in analyzer:
        raise SystemExit(
            "DX11 R113 ambiguous exact census status must not reappear"
        )
    analyzer_contract = {
        '"CensusExactness": sampled_exactness':
            "R113 sampled census exactness evidence object",
        '"DiagnosticOnly": True':
            "R113 census evidence is diagnostic-only",
        '"ExhaustiveDrawCoverage": exhaustive_draw_coverage':
            "R113/R114 census reports coverage from the explicit sampling contract",
        '"EXHAUSTIVE_V1"':
            "R114 opt-in exhaustive sampling identity",
        '"OBSERVED_EXHAUSTIVE_TRANSLATION_EXACT_DIAGNOSTIC_ONLY"':
            "R114 exhaustive exact status remains explicitly diagnostic-only",
        '"ActivationProof": False':
            "R113 census exactness cannot be an activation proof",
        '"OBSERVED_SAMPLED_TRANSLATION_EXACT_DIAGNOSTIC_ONLY"':
            "R113 exact sampled status is explicitly diagnostic-only",
        '"TRANSLATION_EXACTNESS_PENDING"':
            "R113 zero-unsupported but non-exact sampled status",
        'latest["exact"] == latest["samples"]':
            "R113 exact status requires every sampled draw to be exact",
        '"SamplingCoverage": sampling_coverage':
            "R114 sampling/cap coverage evidence object",
        '"HASHED_ORDINAL_V1"':
            "R114 hashed ordinal sampling identity",
        '"SignatureHashCapSaturated"':
            "R114 hash-cap saturation evidence",
        '"DetailedSignatureLogCapSaturated"':
            "R114 detail-cap saturation evidence",
        '"OBSERVED_SAMPLED_TRANSLATION_EXACT_COVERAGE_SATURATED"':
            "R114 exact sampled evidence fails closed when the signature hash cap saturates",
        "introspectionFailure": "resource introspection failure evidence",
        "behaviorUnsupported": "descriptor behavior evidence",
        "mutationTelemetryRequired": "lock/update blocker evidence",
        "managedShadowRequired": "managed lifetime blocker evidence",
        "managedTextureShadowRequiredSamples": "R106 managed texture sample requirement evidence",
        "managedTextureShadowReadySamples": "R106 managed texture sample ready evidence",
        "managedTextureShadowPendingSamples": "R106 managed texture sample pending evidence",
        "textureStageManagedShadowRequired": "R106 managed texture stage requirement evidence",
        "textureStageManagedShadowReady": "R106 managed texture stage ready evidence",
        "textureStageManagedShadowPending": "R106 managed texture stage pending evidence",
        "ManagedTextureShadow": "R106 activation evidence object",
        "ObservedReady": "R106 all-observed managed texture readiness evidence",
        "R(?:7[23456789]|8[012345]|114|120) census": "R72 through R85 plus R114/R120 summary compatibility",
        "mutationWriteUnlocks": "R74 write Lock/Unlock evidence",
        "mutationReadOnlyUnlocks": "R74 read-only Lock/Unlock evidence",
        "mutationDiscardWriteUnlocks": "R74 DISCARD evidence",
        "mutationNoOverwriteWriteUnlocks": "R74 NOOVERWRITE evidence",
        "mutationPlanExact": "R75 exact mutation-plan evidence",
        "mutationPlanUnsupported": "R75 unsupported mutation-plan evidence",
        "mutationPlanManagedShadow": "R75 managed shadow dependency evidence",
        "mutationPlanMapWrite": "R75 MAP_WRITE evidence",
        "mutationPlanMapDiscard": "R75 MAP_WRITE_DISCARD evidence",
        "mutationPlanMapNoOverwrite": "R75 MAP_WRITE_NO_OVERWRITE evidence",
        "mutationPlanUpdateSubresource": "R75 UpdateSubresource evidence",
        "textureMutationWriteUnlocks": "R76 texture write LockRect evidence",
        "textureMutationReadOnlyUnlocks": "R76 texture READONLY LockRect evidence",
        "textureMutationDescriptorFailures": "R76 texture descriptor failure evidence",
        "textureUpdateTextureSuccesses": "R76 UpdateTexture success evidence",
        "textureUpdateTextureFailures": "R76 UpdateTexture failure evidence",
        "textureUpdateSurfaceSuccesses": "R76 UpdateSurface success evidence",
        "textureUpdateSurfaceFailures": "R76 UpdateSurface failure evidence",
        "managedShadowWrites": "R77 managed CPU-shadow write evidence",
        "managedShadowReads": "R77 managed CPU-shadow read evidence",
        "managedResetSuccesses": "R77 successful Reset evidence",
        "managedResetShadowPreserved": "R77 CPU-shadow Reset survival evidence",
        "managedDeviceGeneration": "R77 device-generation evidence",
        "managedShadowVersion": "R77 CPU-shadow version evidence",
        "managedMirrorReady": "R77 fail-closed mirror readiness evidence",
        "inputLayoutExact": "R78 exact input-layout evidence",
        "inputLayoutUnsupported": "R78/R79 unsupported input-layout evidence",
        "inputLayoutFvfExact": "R79 exact FVF input-layout evidence",
        "inputLayoutFvfPending": "R79 unsupported FVF pending evidence",
        "shaderIntrospectionFailure": "R80 shader introspection failure evidence",
        "shaderMixedPair": "R80 mixed VS/PS pair evidence",
        "shaderFixedFunctionPending": "R80 fixed-function F20 dependency evidence",
        "shaderProgrammablePending": "R80 programmable F21 dependency evidence",
        "fixedFunctionCoverageExact": "R81 complete fixed-function coverage evidence",
        "fixedFunctionQueryFailure": "R81 failed fixed-function coverage evidence",
        "fixedFunctionReadinessReady": "R82 conservative F20 readiness evidence",
        "fixedFunctionReadinessPending": "R82 fail-closed F20 readiness evidence",
        "textureStageBound": "R83 bound texture-stage summary evidence",
        "textureStageExact": "R83 exact texture-stage summary evidence",
        "textureStagePending": "R83 pending texture-stage summary evidence",
        "TEXTURE_RE": "R83 per-stage texture resource parser",
        "texture_stages": "R83 per-signature texture resource evidence",
        "fixedFunctionShaderPrototypeGenerated": "R84 generated-source summary evidence",
        "fixedFunctionShaderPrototypePending": "R84 pending-source summary evidence",
        "FFP_SHADER_PROTOTYPE_RE": "R84 generated-source fingerprint parser",
        "fixed_function_shader_prototype": "R84 per-signature generated-source evidence",
        "fixedFunctionShaderCompileSucceeded": "R85 successful compile summary evidence",
        "fixedFunctionShaderCompileFailed": "R85 failed compile summary evidence",
        "fixedFunctionShaderCompileSkippedCap": "R85 bounded compile summary evidence",
        "FFP_SHADER_COMPILE_RE": "R85 compiler result parser",
        "fixed_function_shader_compile": "R85 per-signature compiler evidence",
        "samplerMin": "R81 per-stage sampler parser evidence",
        "samplerAddressV": "R81 per-stage sampler parser evidence",
        "samplerBorderColor": "current per-stage sampler border-color parser evidence",
        "samplerSrgb": "sampler sRGB decode parser evidence",
    }
    missing_analyzer = [
        meaning for token, meaning in analyzer_contract.items() if token not in analyzer
    ]
    if missing_analyzer:
        raise SystemExit(
            "DX11 analyzer resource evidence drift: " + ", ".join(missing_analyzer)
        )

    if "d3dcompiler.lib" not in CMAKE:
        raise SystemExit(
            "DX11 R85 compiler probe requires d3dcompiler.lib in the checked-in CMake graph"
        )

    r89_link_contract = {
        "target_link_libraries(dx11_input_signature_semantics PUBLIC":
            "R89 input-signature smoke target link block",
        "dxguid.lib":
            "R89 D3DReflect IID_ID3D11ShaderReflection GUID provider",
    }
    missing_r89_link = [
        meaning
        for token, meaning in r89_link_contract.items()
        if token not in CMAKE
    ]
    if missing_r89_link:
        raise SystemExit(
            "DX11 R89 input-signature link contract drift: "
            + ", ".join(missing_r89_link)
        )
    if "dxguid.lib" not in CMAKE_TOML:
        raise SystemExit(
            "DX11 R89 input-signature smoke requires dxguid.lib in cmake.toml"
        )

    r87_smoke_contract = {
        "D3DTOP_SELECTARG1": "R86/R87 SELECTARG1 semantic case",
        "D3DTOP_SELECTARG2": "R87 SELECTARG2 semantic case",
        "D3DTOP_MODULATE": "R86/R87 MODULATE semantic case",
        "D3DTA_CURRENT": "R86/R87 CURRENT stage chaining case",
        "D3DTA_TEXTURE": "R86/R87 texture sampling case",
        "input.tex5.xy": "R87 nonmatching stage/texcoord selection case",
        "D3DTEXF_LINEAR": "R87 supported linear filter readiness case",
        "D3DTADDRESS_CLAMP": "R87 supported clamp addressing readiness case",
        "FixedFunctionUnsupportedStageChain": "R87 stage-chain fail-closed reason",
        "D3DTA_COMPLEMENT": "R87 unsupported argument modifier case",
        "FixedFunctionUnsupportedArgument": "R87 argument fail-closed reason",
        "D3DTTFF_COUNT2": "R87 unsupported texture-transform case",
        "FixedFunctionUnsupportedTextureTransform": "R87 transform fail-closed reason",
        "D3DTEXF_ANISOTROPIC": "R87 unsupported sampler-filter case",
        "FixedFunctionUnsupportedSamplerFilter": "R87 sampler fail-closed reason",
        "sampler LOD bias/MAXMIPLEVEL did not translate exactly": "sampler LOD positive readiness case",
        "out-of-range sampler LOD bias did not fail closed": "sampler LOD bias range guard",
        "out-of-range sampler MAXMIPLEVEL did not fail closed": "sampler MAXMIPLEVEL range guard",
        "no-mip non-default sampler LOD state did not fail closed": "no-mip LOD fail-closed guard",
        "FixedFunctionUnsupportedSamplerLod": "sampler LOD readiness blocker",
        "FixedFunctionShaderPrototypeUnsupportedNotReady": "R86 missing-resource fail-closed case",
        "D3DRTYPE_CUBETEXTURE": "R86 unsupported resource-type case",
        "FixedFunctionShaderPrototypeUnsupportedResourceType": "R86 unsupported resource-type blocker",
        "compile_fixed_function_pixel_shader_prototype": "R86/R87 actual offline D3DCompile invocation",
        "DX11 fixed-function shader semantics smoke R87: PASS": "R87 deterministic smoke completion marker",
    }
    missing_r87_smoke = [
        meaning
        for token, meaning in r87_smoke_contract.items()
        if token not in SEMANTIC_SMOKE
    ]
    if missing_r87_smoke:
        raise SystemExit(
            "DX11 R87 semantic smoke drift: " + ", ".join(missing_r87_smoke)
        )

    r159_sampler_mirror_address_contract = [
        ("D3DTADDRESS_MIRROR ||", PIPELINE_TRANSLATION_CPP,
         "R159 MIRROR support classification"),
        ("D3DTADDRESS_MIRRORONCE;", PIPELINE_TRANSLATION_CPP,
         "R159 MIRRORONCE support classification"),
        ("D3D11_TEXTURE_ADDRESS_MIRROR;", PIPELINE_TRANSLATION_CPP,
         "R159 MIRROR direct mapping"),
        ("D3D11_TEXTURE_ADDRESS_MIRROR_ONCE;", PIPELINE_TRANSLATION_CPP,
         "R159 MIRRORONCE direct mapping"),
        ("R159 mirror sampler addressing readiness was not exact",
         SEMANTIC_SMOKE, "R159 mirror readiness positive smoke"),
        ("R159 mirror sampler address translation drift",
         SEMANTIC_SMOKE, "R159 mirror descriptor positive smoke"),
    ]
    missing_r159_sampler_mirror_address = [
        meaning
        for token, source, meaning in r159_sampler_mirror_address_contract
        if token not in source
    ]
    if missing_r159_sampler_mirror_address:
        raise SystemExit(
            "DX11 R159 sampler mirror-address contract drift: "
            + ", ".join(missing_r159_sampler_mirror_address)
        )

    r160_sampler_border_contract = [
        ("DWORD borderColor = 0;", PIPELINE_TRANSLATION_HPP,
         "R160 fixed-function sampler border-color provenance"),
        ("D3DSAMP_BORDERCOLOR", RUNTIME_CENSUS,
         "R160 runtime census captures D3D9 border color"),
        ("hash = hash_mix(hash, stage.borderColor);", RUNTIME_CENSUS,
         "R160 signature identity includes border color"),
        ("value == D3DTADDRESS_BORDER ||", PIPELINE_TRANSLATION_CPP,
         "R160 BORDER support classification"),
        ("case D3DTADDRESS_BORDER:", PIPELINE_TRANSLATION_CPP,
         "R160 BORDER translation branch"),
        ("D3D11_TEXTURE_ADDRESS_BORDER", PIPELINE_TRANSLATION_CPP,
         "R160 D3D11 BORDER mapping"),
        ("source.borderColor >> 16", PIPELINE_TRANSLATION_CPP,
         "R160 ARGB red-channel conversion"),
        ("source.borderColor >> 24", PIPELINE_TRANSLATION_CPP,
         "R160 ARGB alpha-channel conversion"),
        ("R160 border sampler addressing readiness was not exact",
         SEMANTIC_SMOKE, "R160 BORDER readiness positive smoke"),
        ("R160 border sampler ARGB to RGBA translation drift",
         SEMANTIC_SMOKE, "R160 BORDER color translation smoke"),
        ("R160 created BORDER sampler descriptor preserves ARGB color",
         CONSTANT_BUFFER_PROBE, "R160 WARP sampler descriptor proof"),
    ]
    missing_r160_sampler_border = [
        meaning
        for token, source, meaning in r160_sampler_border_contract
        if token not in source
    ]
    if missing_r160_sampler_border:
        raise SystemExit(
            "DX11 R160 sampler BORDER contract drift: "
            + ", ".join(missing_r160_sampler_border)
        )

    sampler_srgb_provenance_contract = [
        ("FixedFunctionUnsupportedSamplerSrgb = 1u << 11",
         PIPELINE_TRANSLATION_HPP, "sampler sRGB unsupported reason bit"),
        ("DWORD srgbTexture = FALSE;", PIPELINE_TRANSLATION_HPP,
         "sampler sRGB state provenance field"),
        ("source.srgbTexture != FALSE", PIPELINE_TRANSLATION_CPP,
         "sampler descriptor fail-closed sRGB gate"),
        ("stage.srgbTexture != FALSE", PIPELINE_TRANSLATION_CPP,
         "fixed-function readiness sRGB gate"),
        ("FixedFunctionUnsupportedSamplerSrgb", PIPELINE_TRANSLATION_CPP,
         "fixed-function readiness sRGB blocker"),
        ("D3DSAMP_SRGBTEXTURE", RUNTIME_CENSUS,
         "runtime census captures D3D9 sampler sRGB state"),
        ("hash = hash_mix(hash, stage.srgbTexture);", RUNTIME_CENSUS,
         "signature identity includes sampler sRGB state"),
        ("sampler sRGB decode did not fail closed", SEMANTIC_SMOKE,
         "semantic readiness negative sRGB probe"),
        ("sampler owner rejects sRGB decode without sRGB SRV",
         CONSTANT_BUFFER_PROBE, "hosted sampler-owner sRGB rejection"),
        ("samplerSrgb", analyzer, "census analyzer exposes sampler sRGB state"),
        ("samplerSrgb", analyzer_test,
         "census analyzer regression covers sampler sRGB state"),
    ]
    missing_sampler_srgb_provenance = [
        meaning
        for token, source, meaning in sampler_srgb_provenance_contract
        if token not in source
    ]
    if missing_sampler_srgb_provenance:
        raise SystemExit(
            "DX11 sampler sRGB provenance contract drift: "
            + ", ".join(missing_sampler_srgb_provenance)
        )

    result_arg_routing_contract = [
        ("FixedFunctionUnsupportedResultArg = 1u << 12",
         PIPELINE_TRANSLATION_HPP, "RESULTARG dedicated unsupported bit"),
        ("DWORD resultArg = D3DTA_CURRENT;", PIPELINE_TRANSLATION_HPP,
         "RESULTARG provenance with D3D9 default"),
        ("stage.resultArg == D3DTA_TEMP", PIPELINE_TRANSLATION_CPP,
         "RESULTARG TEMP destination support"),
        ("stage.resultArg != D3DTA_TEMP", PIPELINE_TRANSLATION_CPP,
         "CURRENT/TEMP readiness destination gate"),
        ("out.unsupported |= FixedFunctionUnsupportedResultArg;",
         PIPELINE_TRANSLATION_CPP, "RESULTARG readiness blocker propagation"),
        ("D3DTSS_RESULTARG, out.resultArg", RUNTIME_CENSUS,
         "runtime census RESULTARG capture"),
        ("hash = hash_mix(hash, stage.resultArg);", RUNTIME_CENSUS,
         "signature identity includes RESULTARG"),
        ("resultArg=0x{:08X}", RUNTIME_CENSUS,
         "detailed RESULTARG telemetry"),
        ("RESULTARG-001 default CURRENT result routing must remain exact",
         SEMANTIC_SMOKE, "CURRENT positive semantic probe"),
        ("RESULTARG-001 initialized TEMP routing must remain exact",
         SEMANTIC_SMOKE, "initialized TEMP positive semantic probe"),
        ("RESULTARG-001 default-zero TEMP read must remain exact",
         SEMANTIC_SMOKE, "default-zero TEMP positive semantic probe"),
        ("resultArg", analyzer, "census analyzer exposes RESULTARG"),
        ("R(?:72|8[12345]|160|173|194|197) ffp signature", analyzer,
         "RESULTARG census parser retains legacy and current signature versions"),
        ("resultArg", analyzer_test, "census analyzer regression covers RESULTARG"),
        ("VR DX11 R173 ffp signature#1 stage#2:", analyzer_test,
         "R173 RESULTARG census fixture version"),
    ]
    missing_result_arg = [
        meaning for token, source, meaning in result_arg_routing_contract
        if token not in source
    ]
    if missing_result_arg:
        raise SystemExit(
            "DX11 RESULTARG contract drift: " + ", ".join(missing_result_arg)
        )

    depth_bias_fail_closed_contract = [
        ("DWORD depthBiasBits = 0;", D3D9_DRAW_STATE_HPP,
         "depth-bias raw constant provenance"),
        ("DWORD slopeScaleDepthBiasBits = 0;", D3D9_DRAW_STATE_HPP,
         "depth-bias raw slope provenance"),
        ("D3DRS_DEPTHBIAS, out.depthBiasBits", D3D9_RENDER_STATE_CAPTURE,
         "live D3D9 constant depth-bias capture"),
        ("D3DRS_SLOPESCALEDEPTHBIAS, out.slopeScaleDepthBiasBits",
         D3D9_RENDER_STATE_CAPTURE, "live D3D9 slope depth-bias capture"),
        ("PipelineUnsupportedDepthBias = 1u << 15", PIPELINE_TRANSLATION_HPP,
         "dedicated depth-bias readiness blocker"),
        ("source.depthBiasBits != 0u", PIPELINE_TRANSLATION_CPP,
         "nonzero D3D9 constant depth-bias rejection"),
        ("source.slopeScaleDepthBiasBits != 0u", PIPELINE_TRANSLATION_CPP,
         "nonzero D3D9 slope depth-bias rejection"),
        ("DX11 zero depth bias must remain exact", FIXED_FUNCTION_PIPELINE_PROBE,
         "zero-bias positive fixture"),
        ("DX11 nonzero D3D9 constant depth bias must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "constant-bias negative fixture"),
        ("DX11 nonzero D3D9 slope depth bias must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "slope-bias negative fixture"),
        ("DX11 fixed-function handoff must retain depth-bias blocker",
         FIXED_FUNCTION_PIPELINE_PROBE, "handoff blocker retention fixture"),
        ("bool depthBiasObservationComplete{};", RUNTIME_CENSUS,
         "R164 census depth-bias observation identity"),
        ("DWORD depthBiasBits{};", RUNTIME_CENSUS,
         "R164 census constant depth-bias raw identity"),
        ("DWORD slopeScaleDepthBiasBits{};", RUNTIME_CENSUS,
         "R164 census slope depth-bias raw identity"),
        ("hash, sig.depthBiasObservationComplete ? 1u : 0u", RUNTIME_CENSUS,
         "R164 census depth-bias observation hash"),
        ("hash = hash_mix(hash, sig.depthBiasBits);", RUNTIME_CENSUS,
         "R164 census constant depth-bias hash"),
        ("hash = hash_mix(hash, sig.slopeScaleDepthBiasBits);", RUNTIME_CENSUS,
         "R164 census slope depth-bias hash"),
        ("signature.depthBiasBits = source.depthBiasBits;", RUNTIME_CENSUS,
         "R164 captured constant depth-bias propagation"),
        ("signature.slopeScaleDepthBiasBits = source.slopeScaleDepthBiasBits;",
         RUNTIME_CENSUS, "R164 captured slope depth-bias propagation"),
        ("VR DX11 R164 depth-bias state#{}", RUNTIME_CENSUS,
         "R164 detailed census telemetry marker"),
    ]
    missing_depth_bias_fail_closed = [
        meaning
        for token, source, meaning in depth_bias_fail_closed_contract
        if token not in source
    ]
    if missing_depth_bias_fail_closed:
        raise SystemExit(
            "DX11 depth-bias fail-closed contract drift: "
            + ", ".join(missing_depth_bias_fail_closed)
        )

    for graph_name, graph in (
        ("checked-in CMake", CMAKE),
        ("cmake.toml", CMAKE_TOML),
    ):
        if "dx11_fixed_function_shader_semantics" not in graph:
            raise SystemExit(
                f"DX11 R86/R87 semantic smoke target missing from {graph_name}"
            )
        if "tools/dx11_fixed_function_shader_semantics.cpp" not in graph:
            raise SystemExit(
                f"DX11 R86/R87 semantic smoke source missing from {graph_name}"
            )

    for token in (
        "Build DX11 fixed-function shader semantic smoke",
        "Run DX11 fixed-function shader semantic smoke",
        "dx11_fixed_function_shader_semantics",
    ):
        if token not in BACKEND_GATE:
            raise SystemExit(
                "DX11 R86/R87 semantic smoke missing from Backend Conversion Gate: "
                + token
            )

    pipeline_translation = (
        DX11 / "pipeline_translation.cpp"
    ).read_text(encoding="utf-8")
    r88_translation_contract = {
        "append_fvf_blend_weights": "R88 FVF blend-weight descriptor builder",
        "D3DFVF_XYZB1": "R88 one-beta FVF position encoding",
        "D3DFVF_XYZB5": "R88 five-beta FVF position encoding",
        "D3DFVF_LASTBETA_UBYTE4": "R88 packed UBYTE4 blend-index encoding",
        "D3DFVF_LASTBETA_D3DCOLOR": "R88 packed D3DCOLOR blend-index encoding",
        '"BLENDWEIGHT"': "R88 blend-weight semantic",
        '"BLENDINDICES"': "R88 blend-index semantic",
        "DXGI_FORMAT_R8G8B8A8_UINT": "R88 UBYTE4 blend-index format",
        "DXGI_FORMAT_B8G8R8A8_UNORM": "R88 D3DCOLOR blend-index format",
    }
    missing_r88_translation = [
        meaning
        for token, meaning in r88_translation_contract.items()
        if token not in pipeline_translation
    ]
    if missing_r88_translation:
        raise SystemExit(
            "DX11 R88 FVF blend-layout drift: "
            + ", ".join(missing_r88_translation)
        )

    r88_smoke_contract = {
        "D3DFVF_XYZB1": "R88 basic blend-weight case",
        "D3DFVF_XYZB4 | D3DFVF_NORMAL": "R88 blend weights plus normal case",
        "D3DFVF_XYZB5": "R88 split five-weight case",
        "D3DFVF_LASTBETA_UBYTE4": "R88 packed UBYTE4 index case",
        "D3DFVF_LASTBETA_D3DCOLOR": "R88 packed D3DCOLOR index case",
        "DXGI_FORMAT_R32G32B32A32_FLOAT": "R88 four-weight descriptor",
        "DXGI_FORMAT_R8G8B8A8_UINT": "R88 UBYTE4 index descriptor",
        "DXGI_FORMAT_B8G8R8A8_UNORM": "R88 D3DCOLOR index descriptor",
        "dual LASTBETA flags must fail closed": "R88 conflicting index encodings",
        "LASTBETA on XYZ must fail closed": "R88 invalid nonblend LASTBETA",
        "short XYZB5 stride must fail closed": "R88 stride fail-closed case",
        "DX11 input layout semantics smoke R88: PASS": "R88 smoke completion marker",
    }
    missing_r88_smoke = [
        meaning
        for token, meaning in r88_smoke_contract.items()
        if token not in INPUT_LAYOUT_SMOKE
    ]
    if missing_r88_smoke:
        raise SystemExit(
            "DX11 R88 input-layout semantic smoke drift: "
            + ", ".join(missing_r88_smoke)
        )

    for graph_name, graph in (
        ("checked-in CMake", CMAKE),
        ("cmake.toml", CMAKE_TOML),
    ):
        if "dx11_input_layout_semantics" not in graph:
            raise SystemExit(
                f"DX11 R88 input-layout semantic target missing from {graph_name}"
            )
        if "tools/dx11_input_layout_semantics.cpp" not in graph:
            raise SystemExit(
                f"DX11 R88 input-layout semantic source missing from {graph_name}"
            )

    for token in (
        "Build DX11 input-layout semantic smoke",
        "Run DX11 input-layout semantic smoke",
        "dx11_input_layout_semantics",
    ):
        if token not in BACKEND_GATE:
            raise SystemExit(
                "DX11 R88 input-layout semantic smoke missing from Backend Conversion Gate: "
                + token
            )

    r89_smoke_contract = {
        "D3DReflect": "R89 shader-signature reflection",
        "D3D11_SIGNATURE_PARAMETER_DESC": "R89 reflected semantic descriptor",
        "D3D_REGISTER_COMPONENT_UINT32": "R89 UBYTE4 uint shader contract",
        "D3D_REGISTER_COMPONENT_FLOAT32": "R89 float/unorm shader contract",
        "D3DFVF_XYZB5": "R89 split BLENDWEIGHT0/1 case",
        "D3DFVF_LASTBETA_UBYTE4": "R89 UBYTE4 BLENDINDICES case",
        "D3DFVF_LASTBETA_D3DCOLOR": "R89 D3DCOLOR BLENDINDICES case",
        "wrongUbyte4TypeShader": "R89 deliberate float4 mismatch fail-closed case",
        "DX11 input signature semantics smoke R89: PASS": "R89 smoke completion marker",
    }
    missing_r89_smoke = [
        meaning
        for token, meaning in r89_smoke_contract.items()
        if token not in INPUT_SIGNATURE_SMOKE
    ]
    if missing_r89_smoke:
        raise SystemExit(
            "DX11 R89 input-signature semantic smoke drift: "
            + ", ".join(missing_r89_smoke)
        )

    for graph_name, graph in (
        ("checked-in CMake", CMAKE),
        ("cmake.toml", CMAKE_TOML),
    ):
        if "dx11_input_signature_semantics" not in graph:
            raise SystemExit(
                f"DX11 R89 input-signature semantic target missing from {graph_name}"
            )
        if "tools/dx11_input_signature_semantics.cpp" not in graph:
            raise SystemExit(
                f"DX11 R89 input-signature semantic source missing from {graph_name}"
            )

    for token in (
        "Build DX11 input-signature semantic smoke",
        "Run DX11 input-signature semantic smoke",
        "dx11_input_signature_semantics",
    ):
        if token not in BACKEND_GATE:
            raise SystemExit(
                "DX11 R89 input-signature semantic smoke missing from Backend Conversion Gate: "
                + token
            )

    r90_smoke_contract = {
        "D3D11CreateDevice": "R90 hosted D3D11 device creation",
        "D3D_DRIVER_TYPE_WARP": "R90 deterministic hosted WARP device",
        "CreateInputLayout": "R90 real D3D11 input-layout object creation",
        "D3DFVF_XYZB5": "R90 split BLENDWEIGHT0/1 object case",
        "D3DFVF_LASTBETA_UBYTE4": "R90 UINT BLENDINDICES object case",
        "D3DFVF_NORMAL": "R90 blended NORMAL object case",
        "DX11 input layout object probe R90: PASS": "R90 probe completion marker",
    }
    missing_r90_smoke = [
        meaning
        for token, meaning in r90_smoke_contract.items()
        if token not in INPUT_LAYOUT_OBJECT_PROBE
    ]
    if missing_r90_smoke:
        raise SystemExit(
            "DX11 R90 input-layout object probe drift: "
            + ", ".join(missing_r90_smoke)
        )

    for graph_name, graph in (
        ("checked-in CMake", CMAKE),
        ("cmake.toml", CMAKE_TOML),
    ):
        if "dx11_input_layout_object_probe" not in graph:
            raise SystemExit(
                f"DX11 R90 input-layout object target missing from {graph_name}"
            )
        if "tools/dx11_input_layout_object_probe.cpp" not in graph:
            raise SystemExit(
                f"DX11 R90 input-layout object source missing from {graph_name}"
            )

    for token in (
        "Build DX11 input-layout object probe",
        "Run DX11 input-layout object probe",
        "dx11_input_layout_object_probe",
    ):
        if token not in BACKEND_GATE:
            raise SystemExit(
                "DX11 R90 input-layout object probe missing from Backend Conversion Gate: "
                + token
            )

    r91_smoke_contract = {
        "D3D11CreateDevice": "R91 hosted D3D11 device creation",
        "CreateVertexShader": "R91 D3D11 vertex-shader object creation",
        "CreateInputLayout": "R91 input-layout pairing with vertex shader bytecode",
        "generate_fixed_function_pixel_shader_prototype": "R91 R84 pixel-shader generator consumption",
        "CreatePixelShader": "R91 D3D11 pixel-shader object creation",
        "DX11 shader object probe R91: PASS": "R91 probe completion marker",
    }
    missing_r91_smoke = [
        meaning
        for token, meaning in r91_smoke_contract.items()
        if token not in SHADER_OBJECT_PROBE
    ]
    if missing_r91_smoke:
        raise SystemExit(
            "DX11 R91 shader-object probe drift: "
            + ", ".join(missing_r91_smoke)
        )

    for graph_name, graph in (
        ("checked-in CMake", CMAKE),
        ("cmake.toml", CMAKE_TOML),
    ):
        if "dx11_shader_object_probe" not in graph:
            raise SystemExit(
                f"DX11 R91 shader-object target missing from {graph_name}"
            )
        if "tools/dx11_shader_object_probe.cpp" not in graph:
            raise SystemExit(
                f"DX11 R91 shader-object source missing from {graph_name}"
            )

    for token in (
        "Build DX11 shader object probe",
        "Run DX11 shader object probe",
        "dx11_shader_object_probe",
    ):
        if token not in BACKEND_GATE:
            raise SystemExit(
                "DX11 R91 shader-object probe missing from Backend Conversion Gate: "
                + token
            )

    r92_linkage_contract = {
        "D3DReflect": "R92 compiled shader reflection",
        "GetInputParameterDesc": "R92 pixel-shader input signature inspection",
        "GetOutputParameterDesc": "R92 vertex-shader output signature inspection",
        "generate_fixed_function_pixel_shader_prototype": "R92 R84 pixel-shader consumption",
        "COLOR0": "R92 COLOR0 stage linkage",
        "TEXCOORD0": "R92 TEXCOORD0 stage linkage",
        "UINT COLOR0 mismatch did not fail closed": "R92 deliberate component-type mismatch rejection",
        "DX11 shader linkage probe R92: PASS": "R92 probe completion marker",
    }
    missing_r92_linkage = [
        meaning
        for token, meaning in r92_linkage_contract.items()
        if token not in SHADER_LINKAGE_PROBE
    ]
    if missing_r92_linkage:
        raise SystemExit(
            "DX11 R92 shader-linkage probe drift: "
            + ", ".join(missing_r92_linkage)
        )

    for graph_name, graph in (
        ("checked-in CMake", CMAKE),
        ("cmake.toml", CMAKE_TOML),
    ):
        if "dx11_shader_linkage_probe" not in graph:
            raise SystemExit(
                f"DX11 R92 shader-linkage target missing from {graph_name}"
            )
        if "tools/dx11_shader_linkage_probe.cpp" not in graph:
            raise SystemExit(
                f"DX11 R92 shader-linkage source missing from {graph_name}"
            )
        if "dxguid.lib" not in graph:
            raise SystemExit(
                f"DX11 R92 shader reflection link contract missing from {graph_name}"
            )

    for token in (
        "Build DX11 shader linkage probe",
        "Run DX11 shader linkage probe",
        "dx11_shader_linkage_probe",
    ):
        if token not in BACKEND_GATE:
            raise SystemExit(
                "DX11 R92 shader-linkage probe missing from Backend Conversion Gate: "
                + token
            )

    r93_vertex_prototype_contract = {
        "FixedFunctionVertexShaderPrototype": "R93 reusable diagnostic vertex-shader prototype type",
        "FixedFunctionLightingState": "R123 observed fixed-function lighting state",
        "generate_fixed_function_vertex_shader_prototype": "R93 vertex-shader generator declaration",
        "FixedFunctionVertexShaderPrototypeUnsupportedBlend": "R93 blend-weight fail-closed contract",
        "FixedFunctionVertexShaderPrototypeUnsupportedNormal": "R93 normal/lighting fail-closed contract",
        "FixedFunctionVertexShaderPrototypeUnsupportedPosition": "R93 transformed/unsupported position fail-closed contract",
    }
    missing_r93_header = [
        meaning
        for token, meaning in r93_vertex_prototype_contract.items()
        if token not in PIPELINE_TRANSLATION_HPP
    ]
    if missing_r93_header:
        raise SystemExit(
            "DX11 R93 vertex prototype header drift: "
            + ", ".join(missing_r93_header)
        )

    for token, meaning in {
        "worldViewProjection": "R93 WVP constant-buffer contract",
        "register(b0)": "R93 D3D11 constant-buffer slot",
        "mul(float4(input.position, 1.0f)": "R93 position transform",
        "output.diffuse = input.diffuse.bgra": "R93 diffuse packed BGRA swizzle",
        "out.hasNormal": "R123 normal-presence gate",
        "!lighting.observationComplete || lighting.enabled != FALSE": "R123 lighting fail-closed gate",
        "output.normal = input.normal": "R123 unlit normal pass-through contract",
        "D3DFVF_TEXCOORDSIZE4": "R93 1D-4D texture-coordinate handling",
        "hash_shader_source(shader)": "R93 deterministic source identity",
    }.items():
        if token not in PIPELINE_TRANSLATION_CPP:
            raise SystemExit(
                "DX11 R93 vertex prototype source drift: " + meaning
            )

    for token, meaning in {
        "generate_fixed_function_vertex_shader_prototype": "R92/R93 linkage consumes generated VS",
        "R93 fixed-function vertex shader prototype generation": "R93 positive generation case",
        "R93 XYZRHW must fail closed": "R93 transformed-position negative case",
        "R93 blend-weight FVF must fail closed": "R93 blend negative case",
        "R123 unlit normal FVF must generate": "R123 unlit-normal positive case",
        "R123 unknown lighting normal FVF must fail closed": "R123 unknown-lighting negative case",
        "R123 lit normal FVF must fail closed": "R123 active-lighting negative case",
    }.items():
        if token not in SHADER_LINKAGE_PROBE:
            raise SystemExit(
                "DX11 R93 linkage regression drift: " + meaning
            )

    r94_transform_contract = {
        "FixedFunctionTransformConstants": "R94 transform payload type",
        "FixedFunctionTransformUnsupportedIncompleteObservation": "R94 observation fail-closed reason",
        "FixedFunctionTransformUnsupportedNonFinite": "R94 non-finite fail-closed reason",
        "generate_fixed_function_transform_constants": "R94 transform generator declaration",
    }
    missing_r94_header = [
        meaning
        for token, meaning in r94_transform_contract.items()
        if token not in PIPELINE_TRANSLATION_HPP
    ]
    if missing_r94_header:
        raise SystemExit(
            "DX11 R94 transform header drift: "
            + ", ".join(missing_r94_header)
        )

    for token, meaning in {
        "std::isfinite": "R94 finite-matrix guard",
        "worldViewProjection[row * 4u + column]": "R94 row-major b0 payload",
        "multiply(world, view)": "R94 WORLD*VIEW order",
        "multiply(worldView, projection)": "R94 WORLD*VIEW*PROJECTION order",
        "payloadHash = hash_bytes": "R94 deterministic payload identity",
    }.items():
        if token not in PIPELINE_TRANSLATION_CPP:
            raise SystemExit(
                "DX11 R94 transform source drift: " + meaning
            )

    for token, meaning in {
        "GetTransform(D3DTS_WORLD": "R94 passive WORLD observation",
        "GetTransform(D3DTS_VIEW": "R94 passive VIEW observation",
        "GetTransform(D3DTS_PROJECTION": "R94 passive PROJECTION observation",
        "VR DX11 R94 ffp vertex readiness#{}": "R94 passive readiness log",
        "sig.fixedFunctionTransformExact = transform.exact()": "R94 fail-closed census readiness",
    }.items():
        if token not in (ROOT / "src" / "vr" / "d3d11" / "runtime_census.cpp").read_text(encoding="utf-8"):
            raise SystemExit(
                "DX11 R94 census transform drift: " + meaning
            )

    for token, meaning in {
        "R94 transform constants should be exact": "R94 positive transform case",
        "R94 WORLD*VIEW translation order": "R94 matrix-order regression",
        "R94 incomplete transform observation must fail closed": "R94 incomplete observation negative case",
        "R94 non-finite transform must fail closed": "R94 non-finite negative case",
    }.items():
        if token not in SHADER_LINKAGE_PROBE:
            raise SystemExit(
                "DX11 R94 transform regression drift: " + meaning
            )

    r95_constant_buffer_contract = {
        "D3D11_BIND_CONSTANT_BUFFER": "R95 D3D11 constant-buffer object contract",
        "D3D11_USAGE_DYNAMIC": "R95 dynamic upload usage",
        "D3D11_CPU_ACCESS_WRITE": "R95 CPU upload access",
        "D3D11_MAP_WRITE_DISCARD": "R95 discard upload path",
        "GetResourceBindingDescByName": "R95 compiled R93 b0 reflection",
        "FixedFunctionTransform": "R95 R93 constant-buffer name",
        "binding.BindPoint == 0": "R95 b0 slot contract",
        "reflectedBufferDesc.Size == expectedConstantBytes": "R95 64-byte reflected payload",
        "VSSetConstantBuffers(0, 1": "R95 b0 binding operation",
        "VSGetConstantBuffers(0, 1": "R95 b0 binding verification",
        "DX11 constant buffer probe R95: PASS": "R95 probe completion marker",
    }
    missing_r95_probe = [
        meaning
        for token, meaning in r95_constant_buffer_contract.items()
        if token not in CONSTANT_BUFFER_CONTRACT_TEXT
    ]
    if missing_r95_probe:
        raise SystemExit(
            "DX11 R95 constant-buffer probe drift: "
            + ", ".join(missing_r95_probe)
        )

    if "DX11 constant buffer probe R95: PASS" not in CONSTANT_BUFFER_PROBE:
        raise SystemExit(
            "DX11 R95 completion marker must remain in hosted probe"
        )

    for graph_name, graph in (
        ("checked-in CMake", CMAKE),
        ("cmake.toml", CMAKE_TOML),
    ):
        if "dx11_constant_buffer_probe" not in graph:
            raise SystemExit(
                f"DX11 R95 constant-buffer target missing from {graph_name}"
            )
        if "tools/dx11_constant_buffer_probe.cpp" not in graph:
            raise SystemExit(
                f"DX11 R95 constant-buffer source missing from {graph_name}"
            )
        if "dxguid.lib" not in graph:
            raise SystemExit(
                f"DX11 R95 reflection link contract missing from {graph_name}"
            )

    for token in (
        "Build DX11 constant buffer probe",
        "Run DX11 constant buffer probe",
        "dx11_constant_buffer_probe",
    ):
        if token not in BACKEND_GATE:
            raise SystemExit(
                "DX11 R95 constant-buffer probe missing from Backend Conversion Gate: "
                + token
            )

    r96_constant_owner_contract = {
        "NativeFixedFunctionTransformBuffer": "R96 dormant transform-buffer owner type",
        "upload_and_bind": "R96 explicit upload/bind API",
        "upload_generation": "R96 monotonic successful-upload generation",
        "Microsoft::WRL::ComPtr<ID3D11Device> device_": "R96 owning device lifetime",
        "Microsoft::WRL::ComPtr<ID3D11Buffer> buffer_": "R96 owned constant buffer lifetime",
    }
    missing_r96_header = [
        meaning
        for token, meaning in r96_constant_owner_contract.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r96_header:
        raise SystemExit(
            "DX11 R96 constant-owner header drift: "
            + ", ".join(missing_r96_header)
        )

    for token, meaning in {
        "contextDevice.Get() != device_.Get()": "R96 foreign-device context rejection",
        "D3D11_MAP_WRITE_DISCARD": "R96 dynamic transform upload",
        "VSSetConstantBuffers(0, 1": "R96 b0 binding",
        "++upload_generation_": "R96 successful-upload generation advance",
        "buffer_.Reset()": "R96 shutdown buffer release",
        "device_.Reset()": "R96 shutdown device release",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R96 constant-owner source drift: " + meaning
            )

    for token, meaning in {
        "R96 owner must start dormant": "R96 dormant initial state",
        "R96 foreign device context must fail closed": "R96 device ownership negative case",
        "R96 inexact transform must fail closed": "R96 transform exactness negative case",
        "R96 successful upload generation": "R96 successful upload lifecycle",
        "R96 shutdown must release owner resources": "R96 shutdown lifecycle",
        "R96 owner reinitialize after shutdown": "R96 recreate lifecycle",
        "DX11 constant buffer lifetime R96: PASS": "R96 probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R96 constant-owner probe drift: " + meaning
            )

    for graph_name, graph in (
        ("checked-in CMake", CMAKE),
        ("cmake.toml", CMAKE_TOML),
    ):
        if "src/vr/d3d11/native_backend.cpp" not in graph:
            raise SystemExit(
                f"DX11 R96 constant-owner implementation missing from {graph_name}"
            )
        if "dxgi.lib" not in graph:
            raise SystemExit(
                f"DX11 R96 native backend link contract missing from {graph_name}"
            )

    r97_pipeline_bundle_header = {
        "NativeFixedFunctionPipelineBundle": "R97 dormant per-device pipeline bundle",
        "FixedFunctionVertexShaderPrototype": "R97 generated vertex prototype input",
        "FixedFunctionPixelShaderPrototype": "R97 generated pixel prototype input",
        "VertexInputLayoutTranslation": "R97 exact input-layout input",
        "Microsoft::WRL::ComPtr<ID3D11VertexShader> vertex_shader_": "R97 owned vertex shader",
        "Microsoft::WRL::ComPtr<ID3D11PixelShader> pixel_shader_": "R97 owned pixel shader",
        "Microsoft::WRL::ComPtr<ID3D11InputLayout> input_layout_": "R97 owned input layout",
        "NativeFixedFunctionTransformBuffer transform_buffer_": "R97 owned R96 transform buffer",
    }
    missing_r97_header = [
        meaning
        for token, meaning in r97_pipeline_bundle_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r97_header:
        raise SystemExit(
            "DX11 R97 pipeline-bundle header drift: "
            + ", ".join(missing_r97_header)
        )

    for token, meaning in {
        "OutRunR97FixedFunctionVertexShader": "R97 vertex compile identity",
        "OutRunR97FixedFunctionPixelShader": "R97 pixel compile identity",
        '"vs_4_0"': "R97 vertex shader target",
        '"ps_4_0"': "R97 pixel shader target",
        "CreateVertexShader": "R97 vertex shader object creation",
        "CreateInputLayout": "R97 input-layout object creation",
        "CreatePixelShader": "R97 pixel shader object creation",
        "transform_buffer_.initialize(device)": "R97 transform-buffer ownership",
        "input_layout_.Reset()": "R97 input-layout release",
        "pixel_shader_.Reset()": "R97 pixel-shader release",
        "vertex_shader_.Reset()": "R97 vertex-shader release",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R97 pipeline-bundle source drift: " + meaning
            )

    dormant_pipeline_binding_contract = {
        "bind_for_observation(": "explicit dormant pipeline binding entrypoint",
        "validate_translation_snapshot(": "live R97 snapshot revalidation",
        "contextDevice.Get() != device_.Get()": "foreign-context rejection",
        "context->IASetInputLayout(input_layout_.Get());":
            "exact input-layout binding",
        "context->VSSetShader(vertex_shader_.Get(), nullptr, 0);":
            "exact vertex-shader binding",
        "context->PSSetShader(pixel_shader_.Get(), nullptr, 0);":
            "exact pixel-shader binding",
        "boundInputLayout.Get() != input_layout_.Get()":
            "input-layout readback identity gate",
        "boundVertexShader.Get() != vertex_shader_.Get()":
            "vertex-shader readback identity gate",
        "boundPixelShader.Get() != pixel_shader_.Get()":
            "pixel-shader readback identity gate",
    }
    missing_dormant_pipeline_binding = [
        meaning
        for token, meaning in dormant_pipeline_binding_contract.items()
        if token not in NATIVE_BACKEND_CPP
    ]
    if "bind_for_observation(" not in NATIVE_BACKEND_HPP:
        missing_dormant_pipeline_binding.append(
            "dormant pipeline binding declaration"
        )
    if missing_dormant_pipeline_binding:
        raise SystemExit(
            "DX11 dormant pipeline-object binding source drift: "
            + ", ".join(missing_dormant_pipeline_binding)
        )

    runtime_bundle_users = []
    for source_path in (ROOT / "src").rglob("*.cpp"):
        if source_path == DX11 / "native_backend.cpp":
            continue
        if "NativeFixedFunctionPipelineBundle" in source_path.read_text(
            encoding="utf-8"
        ):
            runtime_bundle_users.append(source_path.relative_to(ROOT).as_posix())
    if runtime_bundle_users:
        raise SystemExit(
            "DX11 R97 bundle gained a runtime production caller before activation gate: "
            + ", ".join(runtime_bundle_users)
        )

    for token, meaning in {
        "R97 bundle must start dormant": "R97 dormant initial state",
        "R97 bundle owned-object readiness": "R97 owned object readiness",
        "dormant pipeline binding accepts exact same-device R97 snapshot":
            "same-device exact-snapshot pipeline bind",
        "dormant pipeline binding preserves exact IA VS PS identity":
            "pipeline binding readback identity",
        "dormant pipeline binding rejects missing R97 snapshot":
            "missing snapshot rejection",
        "dormant pipeline binding rejects stale R97 snapshot":
            "stale snapshot rejection",
        "dormant pipeline binding rejects foreign D3D11 context":
            "foreign context rejection",
        "DX11 dormant fixed-function pipeline object binding: PASS":
            "dormant pipeline binding probe completion marker",
        "R97 inexact input layout must fail closed": "R97 fail-closed input-layout gate",
        "R97 failed reinitialize must leave bundle dormant": "R97 failure cleanup",
        "R97 bundle reinitialize after fail-closed reset": "R97 recreate lifecycle",
        "R97 shutdown must clear owned objects": "R97 shutdown lifecycle",
        "DX11 fixed-function pipeline bundle R97: PASS": "R97 probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R97 pipeline-bundle probe drift: " + meaning
            )

    r98_sampler_translation_header = {
        "FixedFunctionSamplerTranslation": "R98 concrete sampler translation result",
        "D3D11_SAMPLER_DESC desc": "R98 D3D11 sampler descriptor",
        "translate_fixed_function_sampler": "R98 sampler translation entrypoint",
        "mipLodBiasBits": "R125 sampler MIP LOD bias provenance",
        "maxMipLevel": "R125 sampler most-detailed-mip provenance",
        "FixedFunctionUnsupportedSamplerLod": "R125 sampler LOD unsupported reason",
    }
    missing_r98_translation_header = [
        meaning
        for token, meaning in r98_sampler_translation_header.items()
        if token not in PIPELINE_TRANSLATION_HPP
    ]
    if missing_r98_translation_header:
        raise SystemExit(
            "DX11 R98 sampler translation header drift: "
            + ", ".join(missing_r98_translation_header)
        )

    for token, meaning in {
        "D3D11_FILTER_MIN_MAG_MIP_POINT": "R98 point sampler mapping",
        "D3D11_FILTER_MIN_MAG_MIP_LINEAR": "R98 linear sampler mapping",
        "D3D11_TEXTURE_ADDRESS_CLAMP": "R98 clamp address mapping",
        "source.mipFilter == D3DTEXF_NONE": "R98 no-mip MaxLOD contract",
        "D3D11_FLOAT32_MAX": "R98 mip-enabled MaxLOD contract",
        "translate_fixed_function_sampler_lod": "sampler LOD translation gate",
        "D3D11_MIP_LOD_BIAS_MIN": "D3D11 MipLODBias lower-bound guard",
        "D3D11_MIP_LOD_BIAS_MAX": "D3D11 MipLODBias upper-bound guard",
        "D3D11_REQ_MIP_LEVELS": "D3D11 representable mip-index guard",
        "desc.MinLOD = static_cast<float>(source.maxMipLevel)": "D3D9 MAXMIPLEVEL to D3D11 MinLOD mapping",
    }.items():
        if token not in PIPELINE_TRANSLATION_CPP:
            raise SystemExit(
                "DX11 R98 sampler translation source drift: " + meaning
            )

    r98_sampler_owner_header = {
        "NativeFixedFunctionSamplerState": "R98 dormant sampler owner",
        "Microsoft::WRL::ComPtr<ID3D11SamplerState> sampler_":
            "R98 owned sampler object",
    }
    missing_r98_sampler_owner = [
        meaning
        for token, meaning in r98_sampler_owner_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r98_sampler_owner:
        raise SystemExit(
            "DX11 R98 sampler-owner header drift: "
            + ", ".join(missing_r98_sampler_owner)
        )

    for token, meaning in {
        "translate_fixed_function_sampler(stage)": "R98 fail-closed translation gate",
        "CreateSamplerState": "R98 D3D11 sampler object creation",
        "sampler_.Reset()": "R98 sampler release",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R98 sampler-owner source drift: " + meaning
            )

    for token, meaning in {
        "bind_fixed_function_texture_stage_for_observation":
            "dormant fixed-function texture-stage binding entrypoint",
        "D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT":
            "sampler-slot fail-closed bound",
        "context->PSSetSamplers(slot, 1, &samplerState)":
            "same-stage sampler binding",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 dormant texture-stage sampler binding drift: " + meaning
            )

    runtime_sampler_users = []
    for source_path in (ROOT / "src").rglob("*.cpp"):
        if source_path == DX11 / "native_backend.cpp":
            continue
        if "NativeFixedFunctionSamplerState" in source_path.read_text(
            encoding="utf-8"
        ):
            runtime_sampler_users.append(source_path.relative_to(ROOT).as_posix())
    if runtime_sampler_users:
        raise SystemExit(
            "DX11 R98 sampler owner gained a production caller before activation gate: "
            + ", ".join(runtime_sampler_users)
        )

    for token, meaning in {
        "R98 point/wrap sampler translation": "R98 point/wrap descriptor case",
        "R98 linear/clamp sampler translation": "R98 linear/clamp descriptor case",
        "sampler LOD bias/MAXMIPLEVEL translation":
            "positive MIP LOD bias/most-detailed-mip descriptor proof",
        "created sampler preserves translated LOD state":
            "created D3D11 sampler LOD descriptor proof",
        "out-of-range sampler MIP LOD bias must fail closed":
            "MipLODBias range fail-closed proof",
        "out-of-range sampler MAXMIPLEVEL must fail closed":
            "most-detailed-mip range fail-closed proof",
        "no-mip non-default sampler LOD must fail closed":
            "no-mip ambiguous LOD state fail-closed proof",
        "R98 anisotropic sampler translation must fail closed":
            "R98 unsupported filter negative case",
        "R98 failed sampler reinitialize must leave owner dormant":
            "R98 fail-closed cleanup",
        "R98 sampler shutdown must clear owned objects":
            "R98 shutdown lifecycle",
        "DX11 fixed-function sampler ownership R98: PASS":
            "R98 probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R98 sampler-owner probe drift: " + meaning
            )

    r99_texture_view_header = {
        "NativeFixedFunctionTextureView": "R99 dormant fixed-function texture/SRV owner",
        "Microsoft::WRL::ComPtr<ID3D11Texture2D> texture_":
            "R99 owned translated texture mirror",
        "Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> srv_":
            "R99 owned Texture2D SRV",
    }
    missing_r99_texture_view = [
        meaning
        for token, meaning in r99_texture_view_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r99_texture_view:
        raise SystemExit(
            "DX11 R99 texture-view header drift: "
            + ", ".join(missing_r99_texture_view)
        )

    for token, meaning in {
        "translate_resource_format(": "R99 exact D3D9-to-DXGI format gate",
        "translate_resource_behavior(": "R99 source pool/usage descriptor gate",
        "behavior.requiresCpuShadow": "R99 unimplemented managed CPU-shadow rejection",
        "texture->GetDevice": "R99 same-device ownership gate",
        "desc.ArraySize != 1": "R99 Texture2D array fail-closed gate",
        "desc.SampleDesc.Count != 1": "R99 multisample fail-closed gate",
        "device->CreateShaderResourceView(": "R99 Texture2D SRV object creation",
        "srv_.Reset()": "R99 SRV release",
        "texture_.Reset()": "R99 texture mirror release",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R99 texture-view source drift: " + meaning
            )

    for token, meaning in {
        "D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT":
            "SRV-slot fail-closed bound",
        "samplerDevice != textureDevice":
            "cross-device owner rejection",
        "contextDevice.Get() != samplerDevice":
            "foreign-context rejection",
        "context->PSSetShaderResources(slot, 1, &shaderResource)":
            "same-stage SRV binding",
        "context->PSGetSamplers(":
            "post-bind sampler identity readback",
        "context->PSGetShaderResources(":
            "post-bind SRV identity readback",
        "boundSampler.Get() != samplerState":
            "sampler identity fail-closed gate",
        "boundResource.Get() != shaderResource":
            "SRV hazard/identity fail-closed gate",
        "context->PSSetSamplers(slot, 1, &nullSampler)":
            "partial sampler binding rollback",
        "context->PSSetShaderResources(slot, 1, &nullResource)":
            "partial SRV binding rollback",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 dormant texture-stage SRV binding drift: " + meaning
            )

    runtime_texture_view_users = []
    for source_path in (ROOT / "src").rglob("*.cpp"):
        if source_path == DX11 / "native_backend.cpp":
            continue
        if "NativeFixedFunctionTextureView" in source_path.read_text(
            encoding="utf-8"
        ):
            runtime_texture_view_users.append(
                source_path.relative_to(ROOT).as_posix()
            )
    if runtime_texture_view_users:
        raise SystemExit(
            "DX11 R99 texture view gained a production caller before activation gate: "
            + ", ".join(runtime_texture_view_users)
        )

    constant_probe_source_block = CMAKE.split(
        "set(dx11_constant_buffer_probe_SOURCES", 1
    )[-1].split(")", 1)[0]
    for required_source in (
        "resource_translation.cpp",
        "surface_mirror.cpp",
        "triangle_fan_index_buffer.cpp",
    ):
        if f'"src/vr/d3d11/{required_source}"' not in constant_probe_source_block:
            raise SystemExit(
                "DX11 R99 constant-buffer probe generated CMake must link "
                + required_source
            )

    constant_probe_toml_block = CMAKE_TOML.split(
        "[target.dx11_constant_buffer_probe]", 1
    )[-1].split("[target.", 1)[0]
    for required_source in (
        "resource_translation.cpp",
        "surface_mirror.cpp",
        "triangle_fan_index_buffer.cpp",
    ):
        if f'"src/vr/d3d11/{required_source}"' not in constant_probe_toml_block:
            raise SystemExit(
                "DX11 R99 constant-buffer probe cmake.toml must link "
                + required_source
            )

    for token, meaning in {
        "R99 texture view must start dormant": "R99 dormant initial state",
        "R99 texture/SRV owner readiness": "R99 owned object readiness",
        "R99 created Texture2D SRV descriptor": "R99 concrete SRV descriptor evidence",
        "R99 mismatched translated format must fail closed":
            "R99 translated format mismatch negative case",
        "R99 managed source without CPU shadow must fail closed":
            "R99 managed-lifetime negative case",
        "R99 texture without shader-resource bind must fail closed":
            "R99 missing SRV bind negative case",
        "R99 texture view recovery after fail-closed reset":
            "R99 recreate lifecycle",
        "R99 texture view shutdown must clear owned objects":
            "R99 shutdown lifecycle",
        "DX11 fixed-function texture view ownership R99: PASS":
            "R99 probe completion marker",
        "DX11 dormant texture-stage same-device bind":
            "texture-stage positive binding case",
        "DX11 dormant texture-stage binding preserves sampler/SRV identity":
            "texture-stage binding readback identity",
        "DX11 dormant texture-stage sampler slot overflow fails closed":
            "texture-stage sampler slot bound",
        "DX11 dormant texture-stage SRV slot overflow fails closed":
            "texture-stage SRV slot bound",
        "DX11 dormant texture-stage foreign context fails closed":
            "texture-stage foreign-context rejection",
        "DX11 dormant texture-stage output hazard fails closed":
            "texture-stage RTV/SRV hazard rejection",
        "DX11 dormant texture-stage failed bind clears partial state":
            "texture-stage failed-bind rollback proof",
        "DX11 dormant texture-stage cross-device owners fail closed":
            "texture-stage cross-device owner rejection",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R99 texture-view probe drift: " + meaning
            )

    if '#include "vr/d3d11/resource_translation.hpp"' not in CONSTANT_BUFFER_PROBE:
        raise SystemExit(
            "DX11 R100 constant-buffer probe must include resource_translation.hpp"
        )

    r100_texture_mutation_header = {
        "TextureMutationUpdateKind": "R100 texture mutation operation identity",
        "TextureMutationTranslation": "R100 texture mutation readiness result",
        "requiresFullSubresource": "R100 DISCARD preservation boundary",
        "translate_texture_mutation": "R100 texture mutation translation entrypoint",
    }
    missing_r100_header = [
        meaning
        for token, meaning in r100_texture_mutation_header.items()
        if token not in RESOURCE_TRANSLATION_HPP
    ]
    if missing_r100_header:
        raise SystemExit(
            "DX11 R100 texture-mutation header drift: "
            + ", ".join(missing_r100_header)
        )

    for token, meaning in {
        "D3DLOCK_READONLY | D3DLOCK_DISCARD | D3DLOCK_NOOVERWRITE":
            "R100 bounded D3D9 LockRect flag classification",
        "ResourceRole::Texture": "R100 texture behavior translation reuse",
        "behavior.usage != D3D11_USAGE_DYNAMIC":
            "R100 dynamic D3D11 mirror gate",
        "TextureMutationUpdateKind::ManagedCpuShadowWrite":
            "R100 managed write remains CPU-shadow dependent",
        "TextureMutationUpdateKind::ManagedCpuShadowRead":
            "R100 managed read remains CPU-shadow dependent",
        "if (!discard || !fullSubresource)":
            "R100 partial/plain dynamic write fail-closed gate",
        "TextureMutationUpdateKind::DynamicMapWriteDiscard":
            "R100 exact full-discard update kind",
        "D3D11_MAP_WRITE_DISCARD": "R100 exact D3D11 map operation",
    }.items():
        if token not in RESOURCE_TRANSLATION_CPP:
            raise SystemExit(
                "DX11 R100 texture-mutation source drift: " + meaning
            )

    for token, meaning in {
        "R100 full dynamic texture discard maps exactly":
            "R100 positive DEFAULT dynamic full-discard case",
        "R100 partial dynamic texture discard must fail closed":
            "R100 partial-write preservation negative case",
        "R100 plain dynamic texture write must fail closed":
            "R100 plain-write preservation negative case",
        "R100 texture NOOVERWRITE must fail closed":
            "R100 no-overwrite negative case",
        "R100 managed texture write requires CPU shadow":
            "R100 managed write dependency",
        "R100 managed texture read requires CPU shadow":
            "R100 managed read dependency",
        "DX11 texture mutation readiness R100: PASS":
            "R100 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R100 texture-mutation probe drift: " + meaning
            )

    r101_texture_upload_header = {
        "upload_full_discard(": "R101 bounded Texture2D upload entrypoint",
        "content_ready()": "R101 content readiness state",
        "source_format_ = D3DFMT_UNKNOWN": "R101 source format provenance",
        "source_pool_ = D3DPOOL_DEFAULT": "R101 source pool provenance",
        "source_usage_ = 0": "R101 source usage provenance",
        "source_metadata_valid_ = false": "R101 source metadata validity",
        "upload_generation_ = 0": "R101 content generation",
    }
    missing_r101_header = [
        meaning
        for token, meaning in r101_texture_upload_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r101_header:
        raise SystemExit(
            "DX11 R101 texture-upload header drift: "
            + ", ".join(missing_r101_header)
        )

    for token, meaning in {
        "texture_uncompressed_row_bytes(": "R101 bounded uncompressed row layout",
        "(std::numeric_limits<UINT>::max)()":
            "R101 Windows max-macro-safe overflow bound",
        "translate_texture_mutation(": "R101 reuse of R100 mutation gate",
        "TextureMutationUpdateKind::DynamicMapWriteDiscard":
            "R101 exact mutation kind requirement",
        "desc.MipLevels != 1": "R101 single-mip scope gate",
        "sourceRows != desc.Height": "R101 full-row coverage gate",
        "sourceRowPitch < rowBytes": "R101 source pitch safety gate",
        "texture_.Get(), 0, mutation.mapType": "R101 dynamic mirror Map operation",
        "context->Unmap(texture_.Get(), 0)": "R101 mirror Unmap operation",
        "++upload_generation_": "R101 successful content generation advance",
        "source_metadata_valid_ = false": "R101 shutdown provenance reset",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R101 texture-upload source drift: " + meaning
            )

    for token, meaning in {
        "R101 dynamic texture content starts uninitialized":
            "R101 initial content state",
        "R101 short source row pitch must fail closed":
            "R101 short-pitch rejection",
        "R101 partial source rows must fail closed":
            "R101 partial-row rejection",
        "R101 foreign device context must fail closed":
            "R101 device ownership rejection",
        "R101 full dynamic texture discard upload":
            "R101 positive upload path",
        "R101 uploaded texture bytes must match source rows":
            "R101 staging readback content proof",
        "R101 upload generation must advance monotonically":
            "R101 repeated upload generation",
        "R101 dynamic texture shutdown resets ownership and content generation":
            "R101 shutdown content reset",
        "DX11 fixed-function texture upload R101: PASS":
            "R101 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R101 texture-upload probe drift: " + meaning
            )

    r102_managed_shadow_header = {
        '#include "resource_translation.hpp"': "R102 lifetime contract header dependency",
        "class NativeManagedTextureShadow final": "R102 dormant managed shadow owner",
        "write_full(": "R102 full managed write entrypoint",
        "read_full(": "R102 full managed read entrypoint",
        "note_mirror_uploaded()": "R102 mirror acknowledgment transition",
        "observe_device_reset()": "R102 Reset generation transition",
        "ManagedMirrorLifetimeState lifetime_{}": "R102 lifetime state storage",
        "std::vector<std::uint8_t> shadow_": "R102 CPU shadow byte storage",
    }
    missing_r102_header = [
        meaning
        for token, meaning in r102_managed_shadow_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r102_header:
        raise SystemExit(
            "DX11 R102 managed-shadow header drift: "
            + ", ".join(missing_r102_header)
        )

    for token, meaning in {
        "D3DPOOL_MANAGED, 0": "R102 managed behavior/mutation contract",
        "ResourceMirrorLifetime::ManagedCpuShadow": "R102 managed lifetime requirement",
        "(std::numeric_limits<std::size_t>::max)()":
            "R102 macro-safe CPU shadow size bound",
        "shadow_.assign(shadowBytes, 0)": "R102 CPU shadow allocation",
        "TextureMutationUpdateKind::ManagedCpuShadowWrite":
            "R102 managed write translation gate",
        "TextureMutationUpdateKind::ManagedCpuShadowRead":
            "R102 managed read translation gate",
        "note_managed_shadow_write(lifetime_)":
            "R102 shadow-version transition",
        "note_managed_mirror_upload(lifetime_)":
            "R102 mirror acknowledgment transition",
        "advance_managed_device_generation(lifetime_)":
            "R102 Reset invalidation transition",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R102 managed-shadow source drift: " + meaning
            )

    if "using outrun::vr::dx11::NativeManagedTextureShadow;" not in CONSTANT_BUFFER_PROBE:
        raise SystemExit(
            "DX11 R102 managed-shadow probe must import NativeManagedTextureShadow directly"
        )

    for token, meaning in {
        "R102 managed shadow starts allocated but content-invalid":
            "R102 initial invalid-content state",
        "R102 managed shadow short source pitch must fail closed":
            "R102 short-pitch rejection",
        "R102 managed shadow partial rows must fail closed":
            "R102 partial-row rejection",
        "R102 managed shadow readback must match source rows":
            "R102 CPU shadow content proof",
        "R102 Reset preserves CPU shadow and invalidates GPU mirror":
            "R102 Reset lifetime proof",
        "R102 post-Reset mirror acknowledgment uses new device generation":
            "R102 post-Reset reupload state",
        "R102 compressed managed shadow must fail closed":
            "R102 unsupported-format rejection",
        "R102 managed shadow shutdown resets storage and lifetime":
            "R102 shutdown lifetime reset",
        "DX11 managed texture shadow lifetime R102: PASS":
            "R102 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R102 managed-shadow probe drift: " + meaning
            )

    r103_managed_mirror_header = {
        "recreate_and_upload_mirror(ID3D11Device* device)":
            "R103 concrete managed mirror recreation entrypoint",
        "mirror_device() const noexcept": "R103 managed mirror device getter",
        "mirror_texture() const noexcept": "R103 managed mirror texture getter",
        "mirror_srv() const noexcept": "R103 managed mirror SRV getter",
        "void release_mirror() noexcept": "R103 generation-bound mirror release helper",
        "Microsoft::WRL::ComPtr<ID3D11Texture2D> mirror_texture_":
            "R103 managed mirror texture ownership",
        "Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> mirror_srv_":
            "R103 managed mirror SRV ownership",
    }
    missing_r103_header = [
        meaning
        for token, meaning in r103_managed_mirror_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r103_header:
        raise SystemExit(
            "DX11 R103 managed-mirror header drift: "
            + ", ".join(missing_r103_header)
        )

    for token, meaning in {
        "behavior.usage != D3D11_USAGE_DEFAULT":
            "R103 DEFAULT mirror usage requirement",
        "D3D11_SUBRESOURCE_DATA initialData{}":
            "R103 CPU-shadow initial upload descriptor",
        "initialData.pSysMem = shadow_.data()":
            "R103 CPU shadow upload source",
        "initialData.SysMemPitch = row_bytes_":
            "R103 compact shadow row pitch",
        "device->CreateTexture2D(":
            "R103 concrete D3D11 Texture2D creation",
        "device->CreateShaderResourceView(":
            "R103 concrete SRV creation",
        "mirror_device_ = device":
            "R103 mirror device ownership",
        "note_mirror_uploaded();":
            "R103 mirror lifetime acknowledgment after resources exist",
        "lifetime_.mirrorValid = false":
            "R103 released mirror lifetime invalidation",
        "release_mirror();\n    lifetime_ = note_managed_shadow_write(lifetime_)":
            "R103 source mutation releases stale mirror",
        "release_mirror();\n    lifetime_ = advance_managed_device_generation(lifetime_)":
            "R103 Reset releases generation-bound mirror",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R103 managed-mirror source drift: " + meaning
            )

    for token, meaning in {
        "R103 mirror upload requires valid CPU shadow":
            "R103 invalid-shadow fail-closed gate",
        "R103 bare mirror acknowledgment must not fabricate readiness":
            "R103 no-resource lifetime acknowledgment guard",
        "R103 managed shadow creates DEFAULT mirror":
            "R103 positive mirror creation",
        "R103 managed mirror DEFAULT descriptor contract":
            "R103 concrete mirror descriptor proof",
        "R103 managed mirror uploaded bytes must match shadow rows":
            "R103 GPU mirror content readback proof",
        "R103 Reset preserves shadow and releases generation-bound mirror":
            "R103 Reset mirror release proof",
        "R103 post-Reset mirror upload uses new device generation":
            "R103 new-generation mirror proof",
        "R103 shadow mutation invalidates and releases uploaded mirror":
            "R103 stale mirror release on shadow mutation",
        "R103 managed shadow shutdown resets CPU and GPU ownership":
            "R103 shutdown ownership proof",
        "DX11 managed texture mirror reupload R103: PASS":
            "R103 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R103 managed-mirror probe drift: " + meaning
            )

    r104_lock_bridge_header = {
        "begin_source_lock(": "R104 D3D9 LockRect capture entrypoint",
        "commit_source_unlock(UINT level)":
            "R104 D3D9 UnlockRect commit entrypoint",
        "cancel_source_lock()": "R104 abandoned lock cleanup entrypoint",
        "source_lock_active() const noexcept":
            "R104 active source-lock visibility",
        "const void* source_lock_bits_ = nullptr":
            "R104 locked source pointer storage",
        "UINT source_lock_pitch_ = 0":
            "R104 locked source pitch storage",
        "bool source_lock_active_ = false":
            "R104 lock transaction state",
        "void clear_source_lock() noexcept":
            "R104 stale pointer cleanup helper",
    }
    missing_r104_header = [
        meaning
        for token, meaning in r104_lock_bridge_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r104_header:
        raise SystemExit(
            "DX11 R104 LockRect bridge header drift: "
            + ", ".join(missing_r104_header)
        )

    for token, meaning in {
        "level != 0 || sourceRect != nullptr":
            "R104 level-zero full-subresource gate",
        "!lockedRect.pBits || lockedRect.Pitch <= 0":
            "R104 valid D3DLOCKED_RECT pointer/pitch gate",
        "mutation.kind != TextureMutationUpdateKind::ManagedCpuShadowWrite":
            "R104 managed writable-lock translation requirement",
        "source_lock_bits_ = lockedRect.pBits":
            "R104 lock source pointer capture",
        "source_lock_pitch_ = pitch":
            "R104 source pitch capture",
        "source_lock_active_ = true":
            "R104 lock transaction arm",
        "return stage_source_unlock(level) &&\n        finish_source_unlock(level, S_OK)":
            "R104 compatibility commit uses staged R105 path",
        "clear_source_lock();\n    clear_unlock_stage();\n    release_mirror();":
            "R104/R105 Reset stale transaction cleanup",
        "source_lock_active_ || source_unlock_staged_":
            "R104/R105 active transaction mirror upload rejection",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R104 LockRect bridge source drift: " + meaning
            )

    for token, meaning in {
        "R104 nonzero mip LockRect must fail closed":
            "R104 mip-level rejection",
        "R104 partial LockRect must fail closed":
            "R104 partial-rect rejection",
        "R104 read-only LockRect must not arm write capture":
            "R104 read-only rejection",
        "R104 MANAGED discard LockRect must fail closed":
            "R104 discard rejection",
        "R104 short-pitch LockRect must fail closed":
            "R104 short-pitch rejection",
        "R104 nested LockRect must fail closed":
            "R104 nested-lock rejection",
        "R104 mismatched UnlockRect level must preserve active capture":
            "R104 mismatched-unlock rejection",
        "R104 matching UnlockRect commits final lock contents":
            "R104 positive UnlockRect commit",
        "R104 UnlockRect-captured bytes must match final source rows":
            "R104 final locked-byte content proof",
        "R104 writable LockRect invalidates stale GPU mirror immediately":
            "R104 pending-write mirror invalidation",
        "R104 active source lock blocks stale shadow read/upload":
            "R104 active-lock stale content gate",
        "R104 Reset clears stale LockRect pointer without committing it":
            "R104 Reset pointer lifetime proof",
        "R104 cancelled LockRect clears capture without shadow mutation":
            "R104 explicit cancel proof",
        "R104 LockRect bridge shutdown clears capture and ownership":
            "R104 shutdown cleanup proof",
        "DX11 managed Texture2D LockRect bridge R104: PASS":
            "R104 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R104 LockRect bridge probe drift: " + meaning
            )

    r105_registry_header = {
        "stage_source_unlock(UINT level)": "R105 pre-Unlock staging entrypoint",
        "finish_source_unlock(UINT level, HRESULT unlockResult)":
            "R105 HRESULT-gated shadow commit entrypoint",
        "source_unlock_staged() const noexcept":
            "R105 staged transaction visibility",
        "std::vector<std::uint8_t> pending_unlock_":
            "R105 pointer-free staged byte ownership",
        "class NativeManagedTextureRegistry final":
            "R105 per-texture registry owner",
        "register_texture(": "R105 registry metadata gate",
        "forget_texture(": "R105 Release cleanup API",
        "read_shadow(": "R105 hosted content verification surface",
    }
    missing_r105_header = [
        meaning
        for token, meaning in r105_registry_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r105_header:
        raise SystemExit(
            "DX11 R105 managed-registry header drift: "
            + ", ".join(missing_r105_header)
        )

    for token, meaning in {
        "pending_unlock_.resize(shadow_.size())":
            "R105 pre-Unlock owned staging allocation",
        "clear_source_lock();\n    source_unlock_level_ = level":
            "R105 raw LockRect pointer cleared before real Unlock",
        "FAILED(unlockResult)":
            "R105 failed Unlock fail-closed gate",
        "lifetime_.cpuShadowValid = false":
            "R105 failed Unlock shadow invalidation",
        "shadow_.data(), pending_unlock_.data(), pending_unlock_.size()":
            "R105 successful HRESULT-gated staged commit",
        "std::make_unique<NativeManagedTextureShadow>()":
            "R105 per-texture shadow allocation",
        "shadows_[textureKey] = std::move(shadow)":
            "R105 registry identity ownership",
        "entry.second->observe_device_reset()":
            "R105 registry Reset propagation",
        "shadows_.erase(it)":
            "R105 zero-ref registry cleanup",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R105 managed-registry source drift: " + meaning
            )

    r105_runtime_contract = {
        '#include "native_backend.hpp"': "R105 runtime registry owner include",
        "NativeManagedTextureRegistry ManagedTextureShadowRegistry":
            "R105 runtime registry instance",
        "observe_managed_texture_lock_rect(":
            "R105 live LockRect-to-registry bridge",
        "ManagedTextureShadowRegistry.register_texture(":
            "R105 lazy exact MANAGED registration",
        "stage_managed_texture_unlock_rect(":
            "R105 live pre-Unlock staging",
        "finish_managed_texture_unlock_rect(":
            "R105 live post-Unlock HRESULT commit",
        "ManagedTextureShadowRegistry.forget_texture(texture)":
            "R105 live Release cleanup",
        "ManagedTextureShadowRegistry.observe_device_reset()":
            "R105 successful Reset propagation",
        "ManagedTextureShadowRegistry.clear()":
            "R105 renderer rollback cleanup",
    }
    missing_r105_runtime = [
        meaning
        for token, meaning in r105_runtime_contract.items()
        if token not in census
    ]
    if missing_r105_runtime:
        raise SystemExit(
            "DX11 R105 runtime registry drift: "
            + ", ".join(missing_r105_runtime)
        )

    for token, meaning in {
        "R105 registry rejects null texture identity":
            "R105 null identity rejection",
        "R105 registry rejects multi-mip MANAGED texture":
            "R105 mip-count fail-closed gate",
        "R105 registry rejects non-MANAGED texture":
            "R105 pool fail-closed gate",
        "R105 pre-Unlock staging clears raw source pointer":
            "R105 pointer lifetime proof",
        "R105 successful real Unlock commits staged bytes":
            "R105 HRESULT success commit proof",
        "R105 commit uses pre-Unlock staged snapshot, not post-stage source":
            "R105 owned staging content proof",
        "R105 failed real Unlock invalidates shadow without commit":
            "R105 failed Unlock fail-closed proof",
        "R105 later successful Unlock recovers invalidated shadow":
            "R105 recovery proof",
        "R105 Reset preserves CPU shadow and advances registry generation":
            "R105 Reset lifetime proof",
        "R105 Release cleanup forgets per-texture shadow":
            "R105 Release cleanup proof",
        "R105 registry shutdown clears all texture ownership":
            "R105 registry shutdown proof",
        "DX11 managed Texture2D lifetime registry R105: PASS":
            "R105 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R105 managed-registry probe drift: " + meaning
            )

    r106_readiness_contract = {
        "bool managedShadowRequired{}": "R106 per-stage managed requirement state",
        "bool managedShadowReady{}": "R106 per-stage managed readiness state",
        "textureManagedShadowRequiredMask": "R106 per-signature required mask",
        "textureManagedShadowReadyMask": "R106 per-signature ready mask",
        "ManagedTextureShadowRegistry.shadow_valid(textureIdentity)":
            "R106 bound Texture2D registry readiness query",
        "ManagedTextureShadowRequiredSamples":
            "R106 managed texture required sample counter",
        "ManagedTextureShadowReadySamples":
            "R106 managed texture ready sample counter",
        "ManagedTextureShadowPendingSamples":
            "R106 managed texture pending sample counter",
        "managedTextureShadow[requiredSamples=":
            "R106 periodic managed texture readiness summary",
        "textureStageManagedShadow[required=":
            "R106 periodic stage readiness summary",
        "managedShadowRequired={} managedShadowReady={}":
            "R106 per-stage readiness signature evidence",
        "R106 exposes managed Texture2D shadow readiness as an independent":
            "R106 non-activation scope marker",
    }
    missing_r106 = [
        meaning
        for token, meaning in r106_readiness_contract.items()
        if token not in census
    ]
    if missing_r106:
        raise SystemExit(
            "DX11 R106 managed-texture readiness drift: "
            + ", ".join(missing_r106)
        )

    for forbidden, meaning in {
        "recreate_and_upload_mirror(": "production mirror upload",
        "mirror_srv()": "production managed SRV access",
        "PSSetShaderResources": "production D3D11 texture binding",
    }.items():
        if forbidden in census:
            raise SystemExit(
                "DX11 R106 readiness census activated native texture path: "
                + meaning
            )

    for token, meaning in {
        "managedTextureShadow\\[requiredSamples=":
            "R106 analyzer sample readiness parser",
        "textureStageManagedShadow\\[required=":
            "R106 analyzer stage readiness parser",
        "managedShadowRequired=(?P<managedShadowRequired>":
            "R106 per-stage readiness parser",
        '"ManagedTextureShadow": managed_texture_shadow_evidence':
            "R106 activation evidence export",
        '"ObservedReady"':
            "R106 observed-ready evidence flag",
        '"NativeDrawPathActivationAllowed": False':
            "R106 non-activation invariant",
    }.items():
        if token not in analyzer:
            raise SystemExit(
                "DX11 R106 analyzer readiness drift: " + meaning
            )

    r107_mutation_source_contract = {
        "invalidate_external_mutation() noexcept":
            "R107 per-shadow external mutation invalidation API",
        "invalidate_external_mutation(const void* textureKey) noexcept":
            "R107 registry invalidation API",
        "shadow->invalidate_external_mutation()":
            "R107 registry-to-shadow invalidation bridge",
        "invalidate_managed_texture_update_target(":
            "R107 D3D9 update target identity bridge",
        "ManagedTextureUpdateTextureInvalidations":
            "R107 UpdateTexture invalidation counter",
        "ManagedTextureUpdateSurfaceInvalidations":
            "R107 UpdateSurface invalidation counter",
        "ManagedTextureShadowRegistry.invalidate_external_mutation(texture)":
            "R107 live managed registry invalidation",
        "managedTextureMutationSource[updateTextureInvalidations=":
            "R107 periodic mutation-source evidence",
    }
    combined_r107_source = (
        NATIVE_BACKEND_HPP + "\n" + NATIVE_BACKEND_CPP + "\n" + census
    )
    missing_r107 = [
        meaning
        for token, meaning in r107_mutation_source_contract.items()
        if token not in combined_r107_source
    ]
    if missing_r107:
        raise SystemExit(
            "DX11 R107 managed-texture mutation-source drift: "
            + ", ".join(missing_r107)
        )

    for token, meaning in {
        "R107 external update invalidates current MANAGED texture shadow":
            "R107 hosted invalidation proof",
        "R107 repeated external update remains fail-closed while shadow is stale":
            "R107 repeated-update fail-closed proof",
        "R107 LockRect recapture restores readiness after external update":
            "R107 post-update recapture proof",
        "DX11 managed Texture2D mutation-source completeness R107: PASS":
            "R107 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R107 hosted probe drift: " + meaning
            )

    for token, meaning in {
        "managedTextureMutationSource\\[updateTextureInvalidations=":
            "R107 analyzer mutation-source parser",
        "managedTextureUpdateTextureInvalidations":
            "R107 analyzer UpdateTexture evidence",
        "managedTextureUpdateSurfaceInvalidations":
            "R107 analyzer UpdateSurface evidence",
        '"ExternalMutationInvalidations"':
            "R107 analyzer aggregate invalidation evidence",
        '"NativeDrawPathActivationAllowed": False':
            "R107 non-activation invariant",
    }.items():
        if token not in analyzer:
            raise SystemExit(
                "DX11 R107 analyzer mutation-source drift: " + meaning
            )

    r108_mirror_readiness_header = {
        "struct NativeManagedTextureMirrorReadiness":
            "R108 non-routing readiness snapshot",
        "recreate_and_upload_mirror_for_observation(":
            "R108 registry observation-only mirror creation API",
        "NativeManagedTextureMirrorReadiness mirror_readiness(":
            "R108 registry readiness query API",
        "bool resourcesOwned{}": "R108 resource ownership evidence",
        "bool lifetimeCurrent{}": "R108 generation/version evidence",
        "bool deviceMatches{}": "R108 exact D3D11 device ownership evidence",
    }
    missing_r108_header = [
        meaning
        for token, meaning in r108_mirror_readiness_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r108_header:
        raise SystemExit(
            "DX11 R108 managed-mirror readiness header drift: "
            + ", ".join(missing_r108_header)
        )

    for token, meaning in {
        "shadow && shadow->recreate_and_upload_mirror(device)":
            "R108 registry identity-to-shadow mirror bridge",
        "out.resourcesOwned =":
            "R108 concrete owned-resource evidence",
        "out.lifetimeCurrent = managed_mirror_ready(lifetime)":
            "R108 generation/shadow-version readiness gate",
        "shadow->mirror_device() == expectedDevice":
            "R108 exact device ownership gate",
        "out.ready =":
            "R108 composite readiness result",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R108 managed-mirror readiness source drift: " + meaning
            )

    for token, meaning in {
        "R108 registry mirror preparation rejects incomplete ownership identity":
            "R108 null identity/device rejection",
        "R108 registry prepares exact identity-owned mirror for observation":
            "R108 positive registry mirror creation",
        "R108 registry mirror readiness seals texture identity generation and shadow version":
            "R108 identity/generation/version proof",
        "R108 foreign D3D11 device cannot claim registered mirror readiness":
            "R108 foreign-device rejection",
        "R108 external mutation clears registry mirror ownership readiness":
            "R108 mutation invalidation proof",
        "R108 Reset invalidates generation-bound registry mirror readiness":
            "R108 Reset invalidation proof",
        "R108 post-Reset mirror readiness uses current device generation":
            "R108 post-Reset recreation proof",
        "DX11 managed Texture2D registry mirror readiness R108: PASS":
            "R108 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R108 managed-mirror probe drift: " + meaning
            )

    r109_stage_readiness_header = {
        "struct NativeManagedTextureStageReadiness":
            "R109 per-stage readiness aggregate",
        "bool inputValid{}": "R109 fail-closed input evidence",
        "std::uint32_t requiredMask{}": "R109 required-stage mask",
        "std::uint32_t readyMask{}": "R109 ready-stage mask",
        "std::uint32_t pendingMask{}": "R109 pending-stage mask",
        "mirror_readiness_for_stages(":
            "R109 stage aggregation API",
    }
    missing_r109_header = [
        meaning
        for token, meaning in r109_stage_readiness_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r109_header:
        raise SystemExit(
            "DX11 R109 stage-readiness header drift: "
            + ", ".join(missing_r109_header)
        )

    for token, meaning in {
        "textureCount > 32":
            "R109 bounded stage count",
        "requiredMask & ~validMask":
            "R109 out-of-range required-bit rejection",
        "requiredMask != 0 && expectedDevice == nullptr":
            "R109 expected-device fail-closed gate",
        "out.registeredMask |= bit":
            "R109 registered-stage evidence",
        "out.shadowValidMask |= bit":
            "R109 shadow-valid evidence",
        "out.resourcesOwnedMask |= bit":
            "R109 concrete mirror resource evidence",
        "out.lifetimeCurrentMask |= bit":
            "R109 generation/version evidence",
        "out.deviceMatchesMask |= bit":
            "R109 exact-device evidence",
        "out.pendingMask = out.requiredMask & ~out.readyMask":
            "R109 activation-pending derivation",
        "out.allRequiredReady = out.pendingMask == 0":
            "R109 aggregate readiness gate",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R109 stage-readiness source drift: " + meaning
            )

    for token, meaning in {
        "R109 stage aggregate rejects null key array fail-closed":
            "R109 null-array rejection",
        "R109 stage aggregate rejects required bits beyond observed stages":
            "R109 stage-mask bounds rejection",
        "R109 stage aggregate rejects missing expected D3D11 device":
            "R109 null-device rejection",
        "R109 exact required stage aggregates all R108 readiness evidence":
            "R109 positive stage evidence aggregation",
        "R109 unregistered required stage remains activation-pending":
            "R109 missing-stage fail-closed proof",
        "R109 foreign device keeps required stage activation-pending":
            "R109 foreign-device fail-closed proof",
        "R109 external mutation makes required stage activation-pending":
            "R109 mutation invalidation proof",
        "R109 recaptured mirror restores required stage readiness":
            "R109 recapture recovery proof",
        "R109 Reset keeps required stage activation-pending":
            "R109 Reset invalidation proof",
        "R109 post-Reset recreation restores required stage readiness":
            "R109 post-Reset recovery proof",
        "DX11 managed Texture2D stage mirror readiness R109: PASS":
            "R109 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R109 stage-readiness probe drift: " + meaning
            )

    r110_snapshot_header = {
        "std::uint64_t snapshotToken{}":
            "R110 stage-readiness snapshot token",
        "mirror_instance_generation() const noexcept":
            "R110 mirror-instance generation getter",
        "std::uint64_t mirror_instance_generation_ = 0":
            "R110 mirror-instance generation storage",
        "validate_mirror_readiness_snapshot_for_stages(":
            "R110 snapshot validation API",
        "advance_membership_generation_locked() noexcept":
            "R110 registry-membership generation helper",
        "std::uint64_t membership_generation_ = 1":
            "R110 registry-membership generation storage",
    }
    missing_r110_header = [
        meaning
        for token, meaning in r110_snapshot_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r110_header:
        raise SystemExit(
            "DX11 R110 readiness-snapshot header drift: "
            + ", ".join(missing_r110_header)
        )

    for token, meaning in {
        "mix_readiness_snapshot_token(":
            "R110 snapshot token mixer",
        "++mirror_instance_generation_":
            "R110 successful mirror recreation generation",
        "reinterpret_cast<std::uintptr_t>(expectedDevice)":
            "R110 expected-device token binding",
        "reinterpret_cast<std::uintptr_t>(this)":
            "R110 registry-instance token binding",
        "membership_generation_":
            "R110 registry-membership token binding",
        "advance_membership_generation_locked();":
            "R110 membership-change invalidation",
        "reinterpret_cast<std::uintptr_t>(textureKeys[stage])":
            "R110 texture-identity token binding",
        "lifetime.deviceGeneration":
            "R110 device-generation token binding",
        "lifetime.cpuShadowVersion":
            "R110 CPU-shadow-version token binding",
        "lifetime.mirrorGeneration":
            "R110 mirror-generation token binding",
        "lifetime.mirrorShadowVersion":
            "R110 mirror-shadow-version token binding",
        "shadow->mirror_instance_generation()":
            "R110 mirror-instance token binding",
        "out.snapshotToken = snapshotToken == 0 ? 1 : snapshotToken":
            "R110 nonzero ready token",
        "current.snapshotToken == snapshotToken":
            "R110 stale-token validation gate",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R110 readiness-snapshot source drift: " + meaning
            )

    for token, meaning in {
        "R110 ready stage aggregate issues a valid nonzero snapshot token":
            "R110 initial token validation",
        "R110 snapshot token is bound to exact device mask and nonzero identity":
            "R110 token identity binding proof",
        "R110 mirror instance recreation invalidates stale readiness token":
            "R110 same-shadow recreation invalidation proof",
        "R110 registry membership change invalidates prior snapshot token":
            "R110 registry-membership invalidation proof",
        "R110 refreshed membership snapshot issues a fresh valid token":
            "R110 membership-refresh token proof",
        "R110 external mutation invalidates prior readiness snapshot token":
            "R110 mutation invalidation proof",
        "R110 recapture and mirror recreation issue a fresh valid token":
            "R110 recapture fresh-token proof",
        "R110 Reset invalidates pre-Reset readiness snapshot token":
            "R110 Reset stale-token proof",
        "R110 post-Reset recreation issues a generation-current fresh token":
            "R110 post-Reset token proof",
        "DX11 managed Texture2D readiness snapshot token R110: PASS":
            "R110 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R110 readiness-snapshot probe drift: " + meaning
            )

    r111_descriptor_header = {
        "bool descriptorExact{}":
            "R111 single-mirror descriptor exactness evidence",
        "std::uint32_t descriptorExactMask{}":
            "R111 per-stage descriptor exactness evidence",
        "mirror_descriptor_exact(":
            "R111 concrete Texture2D/SRV descriptor verifier",
    }
    missing_r111_header = [
        meaning
        for token, meaning in r111_descriptor_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r111_header:
        raise SystemExit(
            "DX11 R111 managed-mirror descriptor header drift: "
            + ", ".join(missing_r111_header)
        )

    for token, meaning in {
        "mirror_device_.Get() != expectedDevice":
            "R111 exact expected-device ownership",
        "textureDesc.Width != width_":
            "R111 source-width descriptor check",
        "textureDesc.Height != height_":
            "R111 source-height descriptor check",
        "textureDesc.MipLevels != 1":
            "R111 single-mip descriptor check",
        "textureDesc.ArraySize != 1":
            "R111 single-array-slice descriptor check",
        "textureDesc.Format != format.format":
            "R111 translated format descriptor check",
        "textureDesc.SampleDesc.Count != 1":
            "R111 single-sample descriptor check",
        "textureDesc.Usage != behavior.usage":
            "R111 D3D11 usage descriptor check",
        "textureDesc.BindFlags != behavior.bindFlags":
            "R111 bind-flags descriptor check",
        "textureDesc.CPUAccessFlags != behavior.cpuAccessFlags":
            "R111 CPU-access descriptor check",
        "srvDesc.ViewDimension != D3D11_SRV_DIMENSION_TEXTURE2D":
            "R111 SRV dimension check",
        "srvDesc.Texture2D.MostDetailedMip != 0":
            "R111 SRV base-mip check",
        "srvDesc.Texture2D.MipLevels != 1":
            "R111 SRV mip-count check",
        "mirror_srv_->GetResource(":
            "R111 SRV-to-resource identity query",
        "viewTexture.Get() != mirror_texture_.Get()":
            "R111 SRV resource identity match",
        "out.descriptorExact =":
            "R111 single readiness descriptor gate",
        "out.descriptorExactMask |= bit":
            "R111 stage readiness descriptor gate",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R111 managed-mirror descriptor source drift: " + meaning
            )

    for token, meaning in {
        "R111 managed mirror descriptor and SRV view identity are exact-device bound":
            "R111 direct descriptor/device proof",
        "descriptorExactMask == 0x1u":
            "R111 ready-stage descriptor mask proof",
        "DX11 managed Texture2D mirror descriptor exactness R111: PASS":
            "R111 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R111 managed-mirror descriptor probe drift: " + meaning
            )

    r112_pipeline_identity_header = {
        "struct NativeFixedFunctionPipelineReadiness":
            "R112 fixed-function pipeline identity readiness",
        "translation_readiness(":
            "R112 exact translation identity query",
        "validate_translation_snapshot(":
            "R112 stale pipeline snapshot rejection API",
        "input_layout_identity_ = 0":
            "R112 stored input-layout identity",
        "vertex_shader_source_hash_ = 0":
            "R112 stored vertex-shader source identity",
        "pixel_shader_source_hash_ = 0":
            "R112 stored pixel-shader source identity",
        "bundle_generation_ = 0":
            "R112 bundle recreation generation",
    }
    missing_r112_header = [
        meaning
        for token, meaning in r112_pipeline_identity_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r112_header:
        raise SystemExit(
            "DX11 R112 pipeline-identity header drift: "
            + ", ".join(missing_r112_header)
        )

    for token, meaning in {
        "hash_pipeline_input_layout_identity(":
            "R112 canonical input-layout identity",
        "vertexPrototype.sourceHash == 0":
            "R112 vertex-source identity prerequisite",
        "pixelPrototype.sourceHash == 0":
            "R112 pixel-source identity prerequisite",
        "input_layout_identity_ = inputLayoutIdentity":
            "R112 persisted input-layout identity",
        "vertex_shader_source_hash_ = vertexPrototype.sourceHash":
            "R112 persisted vertex-source identity",
        "pixel_shader_source_hash_ = pixelPrototype.sourceHash":
            "R112 persisted pixel-source identity",
        "++bundle_generation_":
            "R112 recreation generation advance",
        "vertex_shader_->GetDevice(":
            "R112 live vertex-shader device verification",
        "pixel_shader_->GetDevice(":
            "R112 live pixel-shader device verification",
        "input_layout_->GetDevice(":
            "R112 live input-layout device verification",
        "transform_buffer_.buffer()->GetDevice(":
            "R112 live transform-buffer device verification",
        "out.inputLayoutMatches =":
            "R112 input-layout provenance comparison",
        "out.vertexShaderMatches =":
            "R112 vertex-shader provenance comparison",
        "out.pixelShaderMatches =":
            "R112 pixel-shader provenance comparison",
        "out.snapshotToken = snapshotToken == 0 ? 1 : snapshotToken":
            "R112 nonzero exact pipeline snapshot",
        "current.ready && current.snapshotToken == snapshotToken":
            "R112 stale snapshot validation",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R112 pipeline-identity source drift: " + meaning
            )

    for token, meaning in {
        "R112 exact fixed-function pipeline translation identity issues a valid snapshot":
            "R112 positive identity snapshot proof",
        "R112 pipeline identity fails closed on device layout and shader provenance drift":
            "R112 device/layout/shader negative proof",
        "R112 bundle recreation invalidates stale pipeline translation snapshot":
            "R112 recreation stale-token proof",
        "DX11 fixed-function pipeline translation identity R112: PASS":
            "R112 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R112 pipeline-identity probe drift: " + meaning
            )

    r113_managed_buffer_header = {
        "class NativeManagedBufferShadow final":
            "R113 dormant managed VB/IB shadow owner",
        "bool write_range(":
            "R113 bounded managed-buffer CPU shadow mutation",
        "bool recreate_and_upload_mirror(ID3D11Device* device) noexcept":
            "R113 generation-bound D3D11 buffer mirror creation",
        "bool mirror_descriptor_exact(":
            "R113 exact buffer descriptor/device verifier",
        "ManagedMirrorLifetimeState lifetime_{}":
            "R113 shared Reset-generation lifetime state",
        "Microsoft::WRL::ComPtr<ID3D11Buffer> mirror_buffer_":
            "R113 owned D3D11 buffer mirror",
    }
    missing_r113_header = [
        meaning
        for token, meaning in r113_managed_buffer_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r113_header:
        raise SystemExit(
            "DX11 R113 managed-buffer mirror header drift: "
            + ", ".join(missing_r113_header)
        )

    for token, meaning in {
        "translate_buffer_mutation(":
            "R113 mutation contract prerequisite",
        "BufferMutationUpdateKind::ManagedCpuShadowWrite":
            "R113 writable managed-buffer shadow gate",
        "if (!shadow_valid() &&":
            "R113 first-write completeness fail-closed guard",
        "D3D11_BIND_VERTEX_BUFFER":
            "R113 vertex-buffer bind mapping",
        "D3D11_BIND_INDEX_BUFFER":
            "R113 index-buffer bind mapping",
        "device->CreateBuffer(":
            "R113 concrete D3D11 buffer mirror allocation",
        "lifetime_ = note_managed_mirror_upload(lifetime_)":
            "R113 mirror generation/shadow-version acknowledgement",
        "lifetime_ = advance_managed_device_generation(lifetime_)":
            "R113 Reset generation advance",
        "mirror_buffer_->GetDevice(":
            "R113 exact expected-device verification",
        "desc.StructureByteStride == 0":
            "R113 exact plain-buffer descriptor check",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R113 managed-buffer mirror source drift: " + meaning
            )

    for token, meaning in {
        "R113 first managed buffer write must cover the full resource":
            "R113 incomplete-initial-shadow negative proof",
        "R113 managed vertex-buffer mirror bytes":
            "R113 WARP mirror byte-identity proof",
        "R113 partial managed buffer update invalidates stale mirror":
            "R113 stale mirror invalidation proof",
        "R113 Reset preserves managed buffer CPU shadow only":
            "R113 Reset lifetime proof",
        "R113 managed index-buffer bind contract":
            "R113 index-buffer descriptor proof",
        "R113 managed buffer shutdown releases CPU/GPU ownership":
            "R113 explicit shutdown lifetime proof",
        "DX11 managed vertex/index buffer mirror R113: PASS":
            "R113 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R113 managed-buffer mirror probe drift: " + meaning
            )

    r119_managed_buffer_readiness_header = {
        "struct NativeManagedBufferMirrorReadiness":
            "R119 managed-buffer readiness snapshot",
        "bool lifetimeCurrent{}":
            "R119 generation-current readiness gate",
        "std::uint64_t mirrorInstanceGeneration{}":
            "R119 mirror-instance identity",
        "NativeManagedBufferMirrorReadiness mirror_readiness(":
            "R119 readiness observation API",
        "validate_mirror_readiness_snapshot(":
            "R119 stale-snapshot validator",
        "std::uint64_t mirror_instance_generation_ = 0":
            "R119 monotonic mirror-instance owner",
    }
    missing_r119_header = [
        meaning
        for token, meaning in r119_managed_buffer_readiness_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r119_header:
        raise SystemExit(
            "DX11 R119 managed-buffer readiness header drift: "
            + ", ".join(missing_r119_header)
        )

    for token, meaning in {
        "NativeManagedBufferShadow::mirror_readiness(":
            "R119 readiness implementation",
        "out.lifetimeCurrent = managed_mirror_ready(lifetime_)":
            "R119 current-generation lifetime proof",
        "out.deviceMatches =":
            "R119 expected-device gate",
        "out.descriptorExact =":
            "R119 exact descriptor gate",
        "snapshotToken, out.deviceGeneration":
            "R119 device generation token identity",
        "snapshotToken, out.shadowVersion":
            "R119 CPU shadow version token identity",
        "snapshotToken, out.mirrorInstanceGeneration":
            "R119 mirror instance token identity",
        "++mirror_instance_generation_":
            "R119 successful recreation generation advance",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R119 managed-buffer readiness source drift: " + meaning
            )

    for token, meaning in {
        "R119 managed vertex-buffer mirror issues exact readiness snapshot":
            "R119 positive VB snapshot proof",
        "R119 foreign device cannot claim managed-buffer readiness":
            "R119 foreign-device rejection",
        "R119 shadow mutation invalidates managed-buffer snapshot":
            "R119 CPU mutation stale-token proof",
        "R119 managed-buffer recreation issues fresh snapshot":
            "R119 mirror-recreation token proof",
        "R119 Reset invalidates managed-buffer readiness snapshot":
            "R119 Reset stale-token proof",
        "R119 post-Reset managed-buffer mirror issues generation-current snapshot":
            "R119 post-Reset fresh-token proof",
        "R119 managed index-buffer mirror issues exact readiness snapshot":
            "R119 IB positive snapshot proof",
        "DX11 managed buffer mirror readiness snapshot R119: PASS":
            "R119 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R119 managed-buffer readiness probe drift: " + meaning
            )

    r115_activation_header = {
        "struct NativeFixedFunctionActivationReadiness":
            "R115 composite activation readiness",
        "bool componentSnapshotsPresent{}":
            "R115 explicit component snapshot evidence",
        "std::uint32_t requiredTextureMask{}":
            "R115 texture requirement identity",
        "compose_fixed_function_activation_readiness(":
            "R115 fail-closed readiness composition API",
        "validate_fixed_function_activation_snapshot(":
            "R115 composite snapshot validator",
    }
    missing_r115_header = [
        meaning
        for token, meaning in r115_activation_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r115_header:
        raise SystemExit(
            "DX11 R115 activation-composition header drift: "
            + ", ".join(missing_r115_header)
        )

    for token, meaning in {
        "textureStages.readyMask == textureStages.requiredMask":
            "R115 exact required-stage mask gate",
        "textureStages.pendingMask == 0":
            "R115 no-pending-stage gate",
        "pipeline.ready && pipeline.snapshotToken != 0":
            "R115 pipeline snapshot prerequisite",
        "(!texturesRequired || textureStages.snapshotToken != 0)":
            "R115 texture snapshot prerequisite",
        "out.componentSnapshotsPresent =":
            "R115 explicit component-token aggregation",
        "out.ready =":
            "R115 composite activation-candidate readiness",
        "activationToken, out.pipelineSnapshotToken":
            "R115 pipeline identity in composite token",
        "activationToken, out.textureSnapshotToken":
            "R115 texture identity in composite token",
        "static_cast<std::uint64_t>(out.requiredTextureMask)":
            "R115 required-mask identity in composite token",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R115 activation-composition source drift: " + meaning
            )

    for token, meaning in {
        "R115 composite activation readiness accepts exact untextured evidence":
            "R115 untextured positive composition proof",
        "R115 composite activation readiness requires both exact component snapshots":
            "R115 textured positive composition proof",
        "R115 composite activation readiness fails closed on missing component evidence":
            "R115 missing-evidence fail-closed proof",
        "R115 composite activation snapshot changes with component identity":
            "R115 component-identity invalidation proof",
        "DX11 fixed-function activation evidence composition R115: PASS":
            "R115 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R115 activation-composition probe drift: " + meaning
            )

    r116_render_state_header = {
        "struct NativeFixedFunctionRenderStateReadiness":
            "R116 render-state readiness snapshot",
        "class NativeFixedFunctionRenderStateBundle final":
            "R116 dormant render-state owner",
        "Microsoft::WRL::ComPtr<ID3D11BlendState> blend_state_":
            "R116 owned blend-state object",
        "Microsoft::WRL::ComPtr<ID3D11DepthStencilState> depth_stencil_state_":
            "R116 owned depth-stencil object",
        "Microsoft::WRL::ComPtr<ID3D11RasterizerState> rasterizer_state_":
            "R116 owned rasterizer object",
        "std::uint64_t translation_identity_ = 0":
            "R116 persisted render-state identity",
    }
    missing_r116_header = [
        meaning
        for token, meaning in r116_render_state_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r116_header:
        raise SystemExit(
            "DX11 R116 render-state header drift: "
            + ", ".join(missing_r116_header)
        )

    for token, meaning in {
        "hash_pipeline_render_state_identity(":
            "R116 canonical render-state identity",
        "device->CreateBlendState(":
            "R116 concrete blend-state creation",
        "device->CreateDepthStencilState(":
            "R116 concrete depth-stencil creation",
        "device->CreateRasterizerState(":
            "R116 concrete rasterizer creation",
        "stencil_ref_ = translation.stencil_ref":
            "R116 dynamic stencil-reference ownership",
        "translation_identity_ = translationIdentity":
            "R116 persisted translation identity",
        "blend_state_->GetDevice(":
            "R116 live blend-state device verification",
        "depth_stencil_state_->GetDevice(":
            "R116 live depth-stencil device verification",
        "rasterizer_state_->GetDevice(":
            "R116 live rasterizer device verification",
        "translation_identity_ == translationIdentity":
            "R116 exact translation provenance comparison",
        "snapshotToken, translationIdentity":
            "R116 translation identity in readiness token",
        "snapshotToken, bundle_generation_":
            "R116 recreation generation in readiness token",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R116 render-state source drift: " + meaning
            )

    for token, meaning in {
        "R116 render-state bundle owns exact translated state objects":
            "R116 concrete object ownership proof",
        "R116 exact render-state translation issues a valid snapshot":
            "R116 positive readiness snapshot",
        "R116 changed render-state identity fails closed":
            "R116 translation identity invalidation proof",
        "R116 foreign device cannot claim render-state readiness":
            "R116 foreign-device rejection",
        "R116 inexact render-state translation must fail closed":
            "R116 inexact-translation rejection",
        "R116 render-state bundle recreation invalidates stale snapshot":
            "R116 recreation stale-token proof",
        "DX11 fixed-function render-state bundle R116: PASS":
            "R116 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R116 render-state probe drift: " + meaning
            )

    r122_geometry_header = {
        "struct NativeFixedFunctionGeometryReadiness":
            "R122 geometry readiness snapshot",
        "ResourceRole role = ResourceRole::Vertex":
            "R122 managed-buffer role identity",
        "compose_fixed_function_geometry_readiness(":
            "R122 geometry composition API",
        "validate_fixed_function_geometry_snapshot(":
            "R122 stale geometry validator",
        "bool geometryReady{}":
            "R122 final draw geometry prerequisite",
        "std::uint64_t geometrySnapshotToken{}":
            "R122 final draw geometry identity",
    }
    missing_r122_header = [
        meaning
        for token, meaning in r122_geometry_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r122_header:
        raise SystemExit(
            "DX11 R122 geometry header drift: "
            + ", ".join(missing_r122_header)
        )
    for token, meaning in {
        '#include "state_translation.hpp"':
            "R122 primitive translator dependency",
        "out.role = role_":
            "R122 managed-buffer role propagation",
        "const auto topology = translate_primitive(primitive)":
            "R122 exact topology translation",
        "vertexBuffer.role == ResourceRole::Vertex":
            "R122 vertex-role gate",
        "indexBuffer.role == ResourceRole::Index":
            "R122 index-role gate",
        "token, out.vertexBufferSnapshotToken":
            "R122 vertex snapshot identity",
        "token, out.indexBufferSnapshotToken":
            "R122 index snapshot identity",
        "geometry.ready && geometry.snapshotToken != 0":
            "R122 geometry final-draw prerequisite",
        "drawToken, out.geometrySnapshotToken":
            "R122 geometry final-draw token identity",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R122 geometry source drift: " + meaning
            )
    for token, meaning in {
        "R122 indexed geometry seals VB IB and topology snapshots":
            "R122 indexed geometry positive proof",
        "R122 non-indexed geometry ignores unrelated IB identity":
            "R122 optional-index proof",
        "R122 geometry fails closed on role IB or unowned fan expansion":
            "R122 geometry fail-closed proof",
        "!pendingGeometryDraw.ready":
            "R122 final draw missing-geometry rejection",
        "R122 draw snapshot changes with geometry identity":
            "R122 final draw geometry identity invalidation",
        "DX11 geometry-gated draw readiness R122: PASS":
            "R122 hosted probe marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R122 geometry probe drift: " + meaning
            )

    r139_live_geometry_binding_contract = [
        (
            "struct NativeFixedFunctionGeometryBindingReadiness",
            NATIVE_BACKEND_HPP,
            "R139 live IA geometry binding readiness",
        ),
        (
            "validate_fixed_function_direct_geometry_readiness_integrity(",
            NATIVE_BACKEND_CPP,
            "R139 direct geometry self-integrity validator",
        ),
        (
            "context->IASetVertexBuffers(",
            NATIVE_BACKEND_CPP,
            "R139 exact IA vertex-buffer bind",
        ),
        (
            "context->IASetIndexBuffer(",
            NATIVE_BACKEND_CPP,
            "R139 exact IA index-buffer bind",
        ),
        (
            "context->IASetPrimitiveTopology(geometry.topology);",
            NATIVE_BACKEND_CPP,
            "R139 exact IA topology bind",
        ),
        (
            "context->IAGetVertexBuffers(",
            NATIVE_BACKEND_CPP,
            "R139 live IA vertex-buffer readback",
        ),
        (
            "context->IAGetIndexBuffer(",
            NATIVE_BACKEND_CPP,
            "R139 live IA index-buffer readback",
        ),
        (
            "context->IAGetPrimitiveTopology(",
            NATIVE_BACKEND_CPP,
            "R139 live IA topology readback",
        ),
        (
            "R139 live IA observer seals VB IB stride offsets and topology",
            CONSTANT_BUFFER_PROBE,
            "R139 positive indexed IA proof",
        ),
        (
            "R139 live IA topology drift invalidates geometry binding snapshot",
            CONSTANT_BUFFER_PROBE,
            "R139 live topology drift fail-closed proof",
        ),
        (
            "R139 non-indexed live IA binding is exact and index-free",
            CONSTANT_BUFFER_PROBE,
            "R139 non-indexed IA proof",
        ),
        (
            "R139 copied geometry topology drift fails closed before IA mutation",
            CONSTANT_BUFFER_PROBE,
            "R139 copied-geometry integrity proof",
        ),
        (
            "R139 unsupported IA index format fails closed",
            CONSTANT_BUFFER_PROBE,
            "R139 unsupported index format proof",
        ),
    ]
    missing_r139_live_geometry_binding = [
        meaning
        for token, source, meaning in r139_live_geometry_binding_contract
        if token not in source
    ]
    if missing_r139_live_geometry_binding:
        raise SystemExit(
            "DX11 R139 live IA geometry binding contract drift: "
            + ", ".join(missing_r139_live_geometry_binding)
        )

    r124_output_state_header = {
        "struct NativeFixedFunctionOutputStateReadiness":
            "R124 output-state readiness snapshot",
        "bool viewportExact{}":
            "R124 viewport exactness gate",
        "bool scissorExact{}":
            "R124 scissor exactness gate",
        "bool omDynamicExact{}":
            "R124 OM dynamic exactness gate",
        "std::array<float, 4> blendFactor":
            "R124 D3D11 blend-factor payload",
        "UINT sampleMask = 0xFFFFFFFFu;":
            "R124 D3D11 sample-mask payload",
        "compose_fixed_function_output_state_readiness(":
            "R124 output-state composition API",
        "validate_fixed_function_output_state_snapshot(":
            "R124 stale output-state validator",
        "bool outputStateReady{}":
            "R124 final draw output-state prerequisite",
        "std::uint64_t outputStateSnapshotToken{}":
            "R124 final draw output-state identity",
    }
    missing_r124_output_header = [
        meaning
        for token, meaning in r124_output_state_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r124_output_header:
        raise SystemExit(
            "DX11 R124 output-state header drift: "
            + ", ".join(missing_r124_output_header)
        )
    for token, meaning in {
        "source.outputStateComplete":
            "R124 completeness prerequisite",
        "viewportRight <= surfacePair.width":
            "R124 viewport/output extent gate",
        "source.scissorTestEnable == FALSE || scissorBoundsExact":
            "R124 enabled-scissor bounds gate",
        "(source.blendFactor >> 16) & 0xffu":
            "R124 ARGB-to-R blend factor conversion",
        "out.sampleMask = source.multiSampleMask":
            "R124 sample-mask propagation",
        "token, source.blendFactor":
            "R124 blend-factor snapshot identity",
        "token, source.multiSampleMask":
            "R124 sample-mask snapshot identity",
        "outputState.ready && outputState.snapshotToken != 0":
            "R124 final-draw output-state prerequisite",
        "drawToken, out.outputStateSnapshotToken":
            "R124 final-draw output-state identity",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R124 output-state source drift: " + meaning
            )
    for token, meaning in {
        "R124 exact dynamic output state issues a valid snapshot":
            "R124 positive output-state proof",
        "R124 incomplete output-state observation fails closed":
            "R124 incomplete-observation proof",
        "R124 out-of-bounds viewport fails closed":
            "R124 viewport bounds proof",
        "R124 enabled out-of-bounds scissor fails closed":
            "R124 scissor bounds proof",
        "R124 OM dynamic state changes invalidate output snapshot":
            "R124 OM identity invalidation proof",
        "R131 draw binding rejects output-state identity drift":
            "R124 output-state identity propagates into R131 final draw readiness",
        "DX11 dynamic output-state readiness R124: PASS":
            "R124 hosted probe marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R124 output-state probe drift: " + meaning
            )

    r129_generated_fan_geometry_contract = [
        (
            "compose_fixed_function_nonindexed_triangle_fan_geometry_readiness(",
            NATIVE_BACKEND_HPP,
            "R129 generated non-indexed fan geometry readiness API",
        ),
        (
            "generatedIndexBufferMatchesDraw",
            NATIVE_BACKEND_HPP,
            "R129 generated index identity result",
        ),
        (
            "translate_triangle_fan_expansion(primitiveCount)",
            NATIVE_BACKEND_CPP,
            "R129 fan expansion contract",
        ),
        (
            "triangle_fan_source_element(",
            NATIVE_BACKEND_CPP,
            "R129 generated fan source-element reconstruction",
        ),
        (
            "baseVertex >\n                    (std::numeric_limits<UINT>::max)() - sourceElement",
            NATIVE_BACKEND_CPP,
            "R129 base-vertex overflow fail-closed gate",
        ),
        (
            "generatedIndexBuffer.contentHash == expectedContentHash",
            NATIVE_BACKEND_CPP,
            "R129 generated index content identity gate",
        ),
        (
            "R128 generated IB makes exact non-indexed fan geometry ready",
            CONSTANT_BUFFER_PROBE,
            "R129 positive generated fan geometry probe",
        ),
        (
            "R128 fan geometry rejects mismatched or stale generated IB identity",
            CONSTANT_BUFFER_PROBE,
            "R129 stale/mismatched generated fan negative probe",
        ),
        (
            "R129 non-indexed fan base-vertex overflow fails closed",
            CONSTANT_BUFFER_PROBE,
            "R129 base-vertex overflow negative probe",
        ),
    ]
    missing_r129_generated_fan_geometry = [
        meaning
        for token, source, meaning in r129_generated_fan_geometry_contract
        if token not in source
    ]
    if missing_r129_generated_fan_geometry:
        raise SystemExit(
            "DX11 R129 generated fan geometry contract drift: "
            + ", ".join(missing_r129_generated_fan_geometry)
        )

    r143_indexed_fan_geometry_contract = [
        (
            "compose_fixed_function_indexed_triangle_fan_geometry_readiness(",
            NATIVE_BACKEND_HPP,
            "R143 indexed fan geometry readiness API",
        ),
        (
            "validate_fixed_function_indexed_triangle_fan_geometry_snapshot(",
            NATIVE_BACKEND_HPP,
            "R143 indexed fan geometry snapshot validator",
        ),
        (
            "generatedIndexBuffer.sourceIndexSnapshotToken ==\n            sourceIndexBuffer.snapshotToken",
            NATIVE_BACKEND_CPP,
            "R143 current source-index mirror provenance match",
        ),
        (
            "generatedIndexBuffer.sourceIndexFormat == sourceIndexFormat",
            NATIVE_BACKEND_CPP,
            "R143 indexed fan source-format identity",
        ),
        (
            "generatedIndexBuffer.sourceStartIndex == startIndex",
            NATIVE_BACKEND_CPP,
            "R143 indexed fan StartIndex identity",
        ),
        (
            "generatedIndexBuffer.sourceIndexCount == sourceIndexCount",
            NATIVE_BACKEND_CPP,
            "R143 indexed fan source extent identity",
        ),
        (
            "R143 indexed fan geometry seals current source-index mirror provenance",
            CONSTANT_BUFFER_PROBE,
            "R143 positive indexed fan lineage proof",
        ),
        (
            "R143 indexed fan geometry rejects stale source-index snapshot",
            CONSTANT_BUFFER_PROBE,
            "R143 stale source-index lineage rejection",
        ),
        (
            "R143 indexed fan geometry rejects format start and count drift",
            CONSTANT_BUFFER_PROBE,
            "R143 indexed draw-parameter drift rejection",
        ),
        (
            "R143 indexed fan geometry rejects source role and sealed range drift",
            CONSTANT_BUFFER_PROBE,
            "R143 source-role and sealed-range rejection",
        ),
        (
            "DX11 indexed triangle-fan geometry readiness R143: PASS",
            CONSTANT_BUFFER_PROBE,
            "R143 hosted probe completion marker",
        ),
    ]
    missing_r143_indexed_fan_geometry = [
        meaning
        for token, source, meaning in r143_indexed_fan_geometry_contract
        if token not in source
    ]
    if missing_r143_indexed_fan_geometry:
        raise SystemExit(
            "DX11 R143 indexed fan geometry contract drift: "
            + ", ".join(missing_r143_indexed_fan_geometry)
        )

    r144_indexed_fan_final_contract = [
        (
            "struct NativeFixedFunctionCompleteIndexedFanBoundDrawReadiness",
            NATIVE_BACKEND_HPP,
            "R144 indexed fan final readiness identity",
        ),
        (
            "compose_fixed_function_complete_indexed_triangle_fan_bound_draw_readiness(",
            NATIVE_BACKEND_HPP,
            "R144 indexed fan final composition API",
        ),
        (
            "currentSourceIndex.snapshotToken ==\n            currentGeometry.indexBufferSnapshotToken",
            NATIVE_BACKEND_CPP,
            "R144 current source-index mirror is retained through final composition",
        ),
        (
            "currentFan.indexedSource &&",
            NATIVE_BACKEND_CPP,
            "R144 generated owner is indexed-source provenance",
        ),
        (
            "currentFan.baseVertex == 0 &&",
            NATIVE_BACKEND_CPP,
            "R144 generated indexed fan keeps BaseVertexLocation out of materialized indices",
        ),
        (
            "static_cast<std::uint32_t>(baseVertexLocation)",
            NATIVE_BACKEND_CPP,
            "R144 final snapshot seals future DrawIndexed BaseVertexLocation",
        ),
        (
            "R144 indexed fan final bound draw seals source provenance and live generated IA",
            CONSTANT_BUFFER_PROBE,
            "R144 positive final indexed fan proof",
        ),
        (
            "R144 indexed fan final snapshot rejects BaseVertexLocation drift",
            CONSTANT_BUFFER_PROBE,
            "R144 BaseVertexLocation drift rejection",
        ),
        (
            "R144 indexed fan final bound draw rejects source format drift",
            CONSTANT_BUFFER_PROBE,
            "R144 source-index format drift rejection",
        ),
    ]
    missing_r144_indexed_fan_final = [
        meaning
        for token, source, meaning in r144_indexed_fan_final_contract
        if token not in source
    ]
    if missing_r144_indexed_fan_final:
        raise SystemExit(
            "DX11 R144 indexed fan final bound-draw contract drift: "
            + ", ".join(missing_r144_indexed_fan_final)
        )

    r120_draw_readiness_header = {
        "struct NativeFixedFunctionDrawReadiness":
            "R120 composite draw readiness",
        "struct NativeSurfacePairReadiness;":
            "R120 surface-pair readiness dependency",
        "bool renderStateReady{}":
            "R120 explicit render-state readiness",
        "bool surfacePairReady{}":
            "R120 explicit output-surface readiness",
        "bool outputBindingReady{}":
            "R131 concrete RS/OM binding readiness",
        "bool geometryReady{}":
            "R122 explicit geometry readiness",
        "std::uint64_t renderStateSnapshotToken{}":
            "R120 render-state snapshot identity",
        "std::uint64_t surfacePairSnapshotToken{}":
            "R120 output-surface snapshot identity",
        "std::uint64_t outputBindingSnapshotToken{}":
            "R131 concrete RS/OM binding identity",
        "const NativeSurfacePairReadiness& surfacePair":
            "R120 surface-pair composition input",
        "compose_fixed_function_draw_readiness(":
            "R120 fail-closed draw readiness composition API",
        "validate_fixed_function_draw_snapshot(":
            "R120 composite draw snapshot validator",
    }
    missing_r120_header = [
        meaning
        for token, meaning in r120_draw_readiness_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r120_header:
        raise SystemExit(
            "DX11 R120 draw-readiness header drift: "
            + ", ".join(missing_r120_header)
        )

    for token, meaning in {
        '#include "surface_mirror.hpp"':
            "R120 native backend surface-pair definition dependency",
        "surfacePair.inputValid":
            "R120 surface-pair input validity prerequisite",
        "surfacePair.ready && surfacePair.snapshotToken != 0":
            "R120 surface-pair readiness prerequisite",
        "outputBinding.render_state_snapshot_token() == renderState.snapshotToken":
            "R131 binding/render-state identity match",
        "outputBinding.surface_pair_snapshot_token() == surfacePair.snapshotToken":
            "R131 binding/surface-pair identity match",
        "outputBinding.output_state_snapshot_token() == outputState.snapshotToken":
            "R131 binding/output-state identity match",
        "out.outputBindingReady":
            "R131 concrete binding prerequisite",
        "out.componentSnapshotsPresent =":
            "R120 explicit component-token aggregation",
        "drawToken, out.activationSnapshotToken":
            "R120 activation identity in draw token",
        "drawToken, out.renderStateSnapshotToken":
            "R120 render-state identity in draw token",
        "drawToken, out.surfacePairSnapshotToken":
            "R120 output-surface identity in draw token",
        "drawToken, out.outputBindingSnapshotToken":
            "R131 concrete binding identity in draw token",
        "drawToken, out.geometrySnapshotToken":
            "R122 geometry identity in draw token",
        "drawToken, out.requiredTextureMask":
            "R135 required texture mask in draw identity",
        "validate_fixed_function_draw_readiness_integrity(":
            "R135 self-contained draw snapshot integrity validator",
        "out.drawReady =\n        validate_fixed_function_draw_readiness_integrity(draw);":
            "R135 textured draw integrity gate",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R120 draw-readiness source drift: " + meaning
            )

    for token, meaning in {
        "R131 draw readiness composes sealed output binding identity":
            "R131 positive binding-gated composition proof",
        "R131 draw readiness fails closed on missing binding evidence":
            "R131 missing binding fail-closed proof",
        "R131 draw binding rejects render-state identity drift":
            "R131 render-state/binding mismatch proof",
        "R131 draw binding rejects surface-pair identity drift":
            "R131 surface-pair/binding mismatch proof",
        "R131 draw binding rejects output-state identity drift":
            "R131 output-state/binding mismatch proof",
        "R131 draw snapshot still changes with independent geometry identity":
            "R131 independent geometry identity proof",
        "DX11 fixed-function draw readiness composition R120: PASS":
            "R120 hosted probe completion marker",
        "DX11 draw output-binding readiness R131: PASS":
            "R131 hosted probe completion marker",
        "R135 textured readiness rejects unsealed required-stage mask drift":
            "R135 forged texture-mask negative proof",
        "DX11 draw texture-mask snapshot integrity R135: PASS":
            "R135 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R120 draw-readiness probe drift: " + meaning
            )

    r126_triangle_fan_index_buffer_contract = {
        "class NativeTriangleFanIndexBuffer final":
            "R126 generated index-buffer owner",
        "initialize_nonindexed(":
            "R126 non-indexed fan upload API",
        "initialize_indexed(":
            "R126 indexed fan upload API",
        "NativeTriangleFanIndexBufferReadiness readiness(":
            "R126 readiness snapshot API",
        "bool sourceProvenanceExact{}":
            "R129 source provenance readiness gate",
        "std::uint64_t sourceIndexSnapshotToken{}":
            "R129 source index snapshot identity",
        "bool bind(ID3D11DeviceContext* context) const noexcept":
            "R126 explicit dormant bind primitive",
        "struct NativeTriangleFanIndexBufferBindingReadiness":
            "R141 live generated-fan IA binding readiness",
        "binding_readiness(ID3D11DeviceContext* context) const noexcept;":
            "R141 live generated-fan binding observation API",
        "bool validate_binding_snapshot(":
            "R141 stale live generated-fan binding validator",
    }
    missing_r126_fan_index = [
        meaning
        for token, meaning in r126_triangle_fan_index_buffer_contract.items()
        if token not in TRIANGLE_FAN_INDEX_BUFFER_HPP
    ]
    for token, meaning in {
        "materialize_triangle_fan_vertex_indices(":
            "R126 consumes non-indexed fan materialization",
        "materialize_indexed_triangle_fan_indices(":
            "R126 consumes indexed fan materialization",
        "desc.Usage = D3D11_USAGE_IMMUTABLE;":
            "R126 immutable upload ownership",
        "desc.BindFlags = D3D11_BIND_INDEX_BUFFER;":
            "R126 index-buffer bind descriptor",
        "context->IASetIndexBuffer(buffer_.Get(), DXGI_FORMAT_R32_UINT, 0);":
            "R126 R32_UINT IA binding",
        "context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);":
            "R126 triangle-list IA binding",
        "contextDevice.Get() != device_.Get()":
            "R126 foreign-context fail-closed gate",
        "shutdown();":
            "R126 replacement invalidates prior ownership",
        "sourceIndexSnapshotToken == 0":
            "R129 missing indexed-source snapshot rejection",
        "source_index_snapshot_token_ = sourceIndexSnapshotToken;":
            "R129 persisted indexed-source snapshot provenance",
        "token, out.sourceIndexSnapshotToken":
            "R129 indexed-source snapshot in readiness identity",
        "context->IAGetIndexBuffer(":
            "R141 live generated-fan index-buffer readback",
        "context->IAGetPrimitiveTopology(":
            "R141 live generated-fan topology readback",
        "out.ownerSnapshotToken = owner.snapshotToken;":
            "R141 generated-fan owner readiness identity",
        "return binding_readiness(context).ready;":
            "R141 bind verifies effective IA state",
    }.items():
        if token not in TRIANGLE_FAN_INDEX_BUFFER_CPP:
            missing_r126_fan_index.append(meaning)
    for token, meaning in {
        "R126 non-indexed fan upload bytes drifted":
            "R126 non-indexed GPU upload readback",
        "R126 INDEX16 StartIndex upload bytes drifted":
            "R126 INDEX16 upload readback",
        "R126 INDEX32 source values were narrowed":
            "R126 INDEX32 preservation proof",
        "R141 foreign-device live generated fan binding fails closed":
            "R126/R141 foreign-device owner and live-binding negative proof",
        "R126 rejected replacement retained stale generated IB":
            "R126 stale replacement negative proof",
        "R129 INDEX32 source snapshot provenance was not sealed":
            "R129 indexed source-provenance positive proof",
        "R129 indexed fan without source snapshot provenance did not fail closed":
            "R129 missing source-provenance negative proof",
        "DX11 indexed triangle-fan source provenance R129: PASS":
            "R129 hosted probe completion marker",
        "DX11 triangle-fan generated index buffer R126: PASS":
            "R126 hosted probe completion marker",
        "R141 live generated fan IA binding seals exact owner identity":
            "R141 positive live generated-fan IA proof",
        "R141 live generated fan IA binding fails closed after topology drift":
            "R141 live topology drift negative proof",
        "R141 reupload invalidates stale live generated fan binding identity":
            "R141 owner recreation stale-binding proof",
        "R141 foreign-device live generated fan binding fails closed":
            "R141 foreign-context fail-closed proof",
        "DX11 triangle-fan live IA binding R141: PASS":
            "R141 hosted probe completion marker",
    }.items():
        if token not in TRIANGLE_FAN_INDEX_BUFFER_PROBE:
            missing_r126_fan_index.append(meaning)
    for graph, token, meaning in [
        (CMAKE_TOML, "[target.dx11_triangle_fan_index_buffer_probe]",
         "R126 cmake.toml probe target"),
        (CMAKE, "# Target: dx11_triangle_fan_index_buffer_probe",
         "R126 checked-in CMake probe target"),
        (BACKEND_GATE, "--target dx11_triangle_fan_index_buffer_probe",
         "R126 hosted build step"),
        (BACKEND_GATE, "dx11_triangle_fan_index_buffer_probe.exe",
         "R126 hosted run step"),
    ]:
        if token not in graph:
            missing_r126_fan_index.append(meaning)
    if missing_r126_fan_index:
        raise SystemExit(
            "DX11 R126 generated triangle-fan index-buffer contract drift: "
            + ", ".join(missing_r126_fan_index)
        )

    r141_triangle_fan_live_binding_contract = [
        (
            "struct NativeTriangleFanIndexBufferBindingReadiness",
            TRIANGLE_FAN_INDEX_BUFFER_HPP,
            "R141 generated fan live IA binding readiness",
        ),
        (
            "binding_readiness(ID3D11DeviceContext* context) const noexcept",
            TRIANGLE_FAN_INDEX_BUFFER_HPP,
            "R141 live IA binding observer API",
        ),
        (
            "validate_binding_snapshot(",
            TRIANGLE_FAN_INDEX_BUFFER_HPP,
            "R141 live IA binding snapshot validator",
        ),
        (
            "context->IAGetIndexBuffer(",
            TRIANGLE_FAN_INDEX_BUFFER_CPP,
            "R141 live generated-IB readback",
        ),
        (
            "context->IAGetPrimitiveTopology(&observedTopology);",
            TRIANGLE_FAN_INDEX_BUFFER_CPP,
            "R141 live triangle-list topology readback",
        ),
        (
            "out.ownerSnapshotToken = owner.snapshotToken;",
            TRIANGLE_FAN_INDEX_BUFFER_CPP,
            "R141 generated-owner identity propagation",
        ),
        (
            "R141 live generated fan IA binding seals exact owner identity",
            TRIANGLE_FAN_INDEX_BUFFER_PROBE,
            "R141 positive WARP live-binding proof",
        ),
        (
            "R141 live generated fan IA binding fails closed after topology drift",
            TRIANGLE_FAN_INDEX_BUFFER_PROBE,
            "R141 topology-drift fail-closed proof",
        ),
        (
            "R141 generated fan IA binding restores deterministic snapshot",
            TRIANGLE_FAN_INDEX_BUFFER_PROBE,
            "R141 deterministic live-binding restore proof",
        ),
        (
            "R141 live generated fan IA binding rejects index offset drift",
            TRIANGLE_FAN_INDEX_BUFFER_PROBE,
            "R141 index-offset drift fail-closed proof",
        ),
        (
            "R141 live generated fan IA binding rejects index format drift",
            TRIANGLE_FAN_INDEX_BUFFER_PROBE,
            "R141 index-format drift fail-closed proof",
        ),
    ]
    missing_r141_triangle_fan_live_binding = [
        meaning
        for token, source, meaning in r141_triangle_fan_live_binding_contract
        if token not in source
    ]
    if missing_r141_triangle_fan_live_binding:
        raise SystemExit(
            "DX11 R141 generated triangle-fan live binding contract drift: "
            + ", ".join(missing_r141_triangle_fan_live_binding)
        )

    if (
        "recreate_and_upload_mirror_for_observation(" in census
        or "mirror_readiness(" in census
        or "mirror_readiness_for_stages(" in census
        or "validate_mirror_readiness_snapshot_for_stages(" in census
        or "mirror_descriptor_exact(" in census
    ):
        raise SystemExit(
            "DX11 R108-R111 observation-only registry mirror API gained a runtime census caller"
        )

    r169_point_raster_provenance_contract = [
        ("DWORD pointSizeBits = 0x3F800000u;", D3D9_DRAW_STATE_HPP,
         "R169 point-size snapshot provenance"),
        ("DWORD pointSizeMinBits = 0x3F800000u;", D3D9_DRAW_STATE_HPP,
         "R169 point-size minimum snapshot provenance"),
        ("DWORD pointSizeMaxBits = 0x42800000u;", D3D9_DRAW_STATE_HPP,
         "R169 point-size maximum snapshot provenance"),
        ("DWORD pointSpriteEnable = FALSE;", D3D9_DRAW_STATE_HPP,
         "R169 point-sprite snapshot provenance"),
        ("DWORD pointScaleEnable = FALSE;", D3D9_DRAW_STATE_HPP,
         "R169 point-scale enable snapshot provenance"),
        ("DWORD pointScaleABits = 0x3F800000u;", D3D9_DRAW_STATE_HPP,
         "R169 point-scale A snapshot provenance"),
        ("DWORD pointScaleBBits = 0u;", D3D9_DRAW_STATE_HPP,
         "R169 point-scale B snapshot provenance"),
        ("DWORD pointScaleCBits = 0u;", D3D9_DRAW_STATE_HPP,
         "R169 point-scale C snapshot provenance"),
        ("D3DRS_POINTSIZE, D3DRS_POINTSIZE_MIN",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-size tracked-state priming"),
        ("D3DRS_POINTSIZE_MAX, D3DRS_POINTSPRITEENABLE",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-sprite tracked-state priming"),
        ("D3DRS_POINTSCALEENABLE, D3DRS_POINTSCALE_A",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-scale tracked-state priming"),
        ("D3DRS_POINTSCALE_B, D3DRS_POINTSCALE_C",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-scale tail tracked-state priming"),
        ("read(D3DRS_POINTSIZE, out.pointSizeBits);",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-size capture"),
        ("read(D3DRS_POINTSIZE_MIN, out.pointSizeMinBits);",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-size minimum capture"),
        ("read(D3DRS_POINTSIZE_MAX, out.pointSizeMaxBits);",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-size maximum capture"),
        ("read(D3DRS_POINTSPRITEENABLE, out.pointSpriteEnable);",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-sprite capture"),
        ("read(D3DRS_POINTSCALEENABLE, out.pointScaleEnable);",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-scale enable capture"),
        ("read(D3DRS_POINTSCALE_A, out.pointScaleABits);",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-scale A capture"),
        ("read(D3DRS_POINTSCALE_B, out.pointScaleBBits);",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-scale B capture"),
        ("read(D3DRS_POINTSCALE_C, out.pointScaleCBits);",
         D3D9_RENDER_STATE_CAPTURE, "R169 point-scale C capture"),
        ("bool pointRasterObservationComplete{};", RUNTIME_CENSUS,
         "R169 census observation completeness"),
        ("hash = hash_mix(hash, sig.pointSizeBits);", RUNTIME_CENSUS,
         "R169 point-size census identity"),
        ("hash = hash_mix(hash, sig.pointScaleCBits);", RUNTIME_CENSUS,
         "R169 point-scale census identity"),
        ("signature.pointSizeBits = source.pointSizeBits;", RUNTIME_CENSUS,
         "R169 point-size census capture"),
        ("signature.pointScaleCBits = source.pointScaleCBits;", RUNTIME_CENSUS,
         "R169 point-scale census capture"),
        ("VR DX11 R169 point-raster state#{}", RUNTIME_CENSUS,
         "R169 detailed census evidence"),
        ("out.pointRasterSemanticsExact = primitive != D3DPT_POINTLIST;",
         NATIVE_BACKEND_CPP, "R169 POINTLIST remains fail closed"),
        ("R155 direct point-list raster semantics remain fail closed",
         CONSTANT_BUFFER_PROBE, "R169 retains hosted POINTLIST blocker proof"),
    ]
    missing_r169_point_raster_provenance = [
        meaning
        for token, source, meaning in r169_point_raster_provenance_contract
        if token not in source
    ]
    if missing_r169_point_raster_provenance:
        raise SystemExit(
            "DX11 R169 point-raster provenance drift: "
            + ", ".join(missing_r169_point_raster_provenance)
        )

    r173_resultarg_contract = [
        (
            "FixedFunctionUnsupportedResultArg = 1u << 12",
            PIPELINE_TRANSLATION_HPP,
            "R173/R200 RESULTARG unsupported readiness bit",
        ),
        (
            "DWORD resultArg = D3DTA_CURRENT;",
            PIPELINE_TRANSLATION_HPP,
            "R173 RESULTARG default provenance",
        ),
        (
            "stage.resultArg == D3DTA_TEMP",
            PIPELINE_TRANSLATION_CPP,
            "R200 TEMP result destination support",
        ),
        (
            "stage.resultArg != D3DTA_TEMP",
            PIPELINE_TRANSLATION_CPP,
            "R201 CURRENT/TEMP destination allow-list",
        ),
        (
            "FixedFunctionUnsupportedResultArg;",
            PIPELINE_TRANSLATION_CPP,
            "R173/R200 RESULTARG readiness blocker",
        ),
        (
            "D3DTSS_RESULTARG, out.resultArg",
            RUNTIME_CENSUS,
            "R173 RESULTARG runtime observation",
        ),
        (
            "hash = hash_mix(hash, stage.resultArg);",
            RUNTIME_CENSUS,
            "R173 RESULTARG census identity",
        ),
        (
            "resultArg=0x{:08X}",
            RUNTIME_CENSUS,
            "R173 RESULTARG detailed evidence",
        ),
        (
            "R200 D3DTSS_RESULTARG TEMP write/read chain must become exact",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R200 TEMP positive probe",
        ),
        (
            "R201 default-zero D3DTA_TEMP read must remain exact",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R201 default-zero TEMP positive probe",
        ),
        (
            "DX11 fixed-function TEMP default-zero semantics R201: PASS",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R201 hosted probe completion marker",
        ),
    ]
    missing_r173_resultarg = [
        meaning
        for token, source, meaning in r173_resultarg_contract
        if token not in source
    ]
    if missing_r173_resultarg:
        raise SystemExit(
            "DX11 R173 fixed-function RESULTARG contract drift: "
            + ", ".join(missing_r173_resultarg)
        )

    r178_argument_modifier_contract = [
        (
            "D3DTA_COMPLEMENT and D3DTA_ALPHAREPLICATE are modifiers",
            PIPELINE_TRANSLATION_CPP,
            "R178 documented supported modifier boundary",
        ),
        (
            "static_cast<DWORD>(D3DTA_COMPLEMENT) |",
            PIPELINE_TRANSLATION_CPP,
            "R178 complement accepted modifier bit",
        ),
        (
            "static_cast<DWORD>(D3DTA_ALPHAREPLICATE);",
            PIPELINE_TRANSLATION_CPP,
            "R178 alpha-replicate accepted modifier bit",
        ),
        (
            "if ((value & ~supportedBits) != 0)",
            PIPELINE_TRANSLATION_CPP,
            "R178 unknown modifier fail-closed predicate",
        ),
        (
            'std::string(swizzle) == ".rgb"',
            PIPELINE_TRANSLATION_CPP,
            "R178 RGB alpha-replication selection",
        ),
        (
            'return "(1.0 - " + base + ")";',
            PIPELINE_TRANSLATION_CPP,
            "R178 complement HLSL expression",
        ),
        (
            "observeTextureStageState(D3DTSS_COLORARG1, out.colorArg1);",
            RUNTIME_CENSUS,
            "R178 source argument live observation",
        ),
        (
            "hash = hash_mix(hash, stage.colorArg1);",
            RUNTIME_CENSUS,
            "R178 source argument census identity",
        ),
        (
            "R178 supported D3DTA modifiers must remain shader-exact",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R178 supported modifier readiness probe",
        ),
        (
            "float3 nextColor = (1.0 - sampled0.aaa);",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R178 combined complement/alpha-replicate HLSL probe",
        ),
        (
            "R178 unknown D3DTA modifier bits must fail closed",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R178 unknown modifier negative probe",
        ),
        (
            "DX11 fixed-function argument modifiers R178: PASS",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R178 hosted probe completion marker",
        ),
    ]
    missing_r178_argument_modifier = [
        meaning
        for token, source, meaning in r178_argument_modifier_contract
        if token not in source
    ]
    if missing_r178_argument_modifier:
        raise SystemExit(
            "DX11 R178 fixed-function argument modifier contract drift: "
            + ", ".join(missing_r178_argument_modifier)
        )

    r171_multisample_raster_contract = [
        (
            "DWORD multiSampleAntialias = TRUE;",
            D3D9_DRAW_STATE_HPP,
            "R171 multisample raster snapshot provenance",
        ),
        (
            "D3DRS_MULTISAMPLEANTIALIAS,",
            D3D9_RENDER_STATE_CAPTURE,
            "R171 tracked multisample-raster priming",
        ),
        (
            "read(D3DRS_MULTISAMPLEANTIALIAS, out.multiSampleAntialias);",
            D3D9_RENDER_STATE_CAPTURE,
            "R171 multisample-raster capture",
        ),
        (
            "out.rasterizer.MultisampleEnable =\n            source.multiSampleAntialias != FALSE;",
            PIPELINE_TRANSLATION_CPP,
            "R171 D3D11 multisample-raster translation",
        ),
        (
            "R171 enabled D3D9 multisample raster intent reaches D3D11 rasterizer state",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R171 enabled-state translation probe",
        ),
        (
            "R171 disabled D3D9 multisample raster intent reaches D3D11 rasterizer state",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R171 disabled-state translation probe",
        ),
        (
            "DX11 multisample raster provenance R171: PASS",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R171 hosted probe completion marker",
        ),
        (
            "bool multisampleRasterObservationComplete{};",
            RUNTIME_CENSUS,
            "R172 multisample-raster census observation identity",
        ),
        (
            "hash, sig.multisampleRasterObservationComplete ? 1u : 0u",
            RUNTIME_CENSUS,
            "R172 multisample-raster observation hash",
        ),
        (
            "hash = hash_mix(hash, sig.multiSampleAntialias);",
            RUNTIME_CENSUS,
            "R172 multisample-raster value hash",
        ),
        (
            "signature.multiSampleAntialias = source.multiSampleAntialias;",
            RUNTIME_CENSUS,
            "R172 multisample-raster capture propagation",
        ),
        (
            "VR DX11 R172 multisample-raster state#{}",
            RUNTIME_CENSUS,
            "R172 detailed census evidence",
        ),
    ]
    missing_r171_multisample_raster = [
        meaning
        for token, source, meaning in r171_multisample_raster_contract
        if token not in source
    ]
    if missing_r171_multisample_raster:
        raise SystemExit(
            "DX11 R171 multisample-raster provenance drift: "
            + ", ".join(missing_r171_multisample_raster)
        )

    r168_line_raster_contract = [
        (
            "DWORD lastPixel = TRUE;",
            D3D9_DRAW_STATE_HPP,
            "R168 LASTPIXEL snapshot provenance",
        ),
        (
            "DWORD antialiasedLineEnable = FALSE;",
            D3D9_DRAW_STATE_HPP,
            "R168 antialiased-line snapshot provenance",
        ),
        (
            "D3DRS_LASTPIXEL, D3DRS_ANTIALIASEDLINEENABLE",
            D3D9_RENDER_STATE_CAPTURE,
            "R168 tracked line-raster priming",
        ),
        (
            "read(D3DRS_LASTPIXEL, out.lastPixel);",
            D3D9_RENDER_STATE_CAPTURE,
            "R168 LASTPIXEL capture",
        ),
        (
            "read(D3DRS_ANTIALIASEDLINEENABLE, out.antialiasedLineEnable);",
            D3D9_RENDER_STATE_CAPTURE,
            "R168 antialiased-line capture",
        ),
        (
            "out.rasterizer.AntialiasedLineEnable =\n            source.antialiasedLineEnable != FALSE;",
            PIPELINE_TRANSLATION_CPP,
            "R168 D3D11 line-AA translation",
        ),
        (
            "primitive != D3DPT_LINELIST && primitive != D3DPT_LINESTRIP;",
            NATIVE_BACKEND_CPP,
            "R168 LASTPIXEL keeps direct lines fail closed",
        ),
        (
            "R168 D3D9 antialiased-line intent reaches D3D11 rasterizer state",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R168 positive line-AA translation probe",
        ),
        (
            "R168 LASTPIXEL remains dispatch-scoped rather than globally blocking triangles",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R168 LASTPIXEL scope probe",
        ),
        (
            "DX11 line-raster provenance R168: PASS",
            FIXED_FUNCTION_PIPELINE_PROBE,
            "R168 hosted probe completion marker",
        ),
    ]
    missing_r168_line_raster = [
        meaning
        for token, source, meaning in r168_line_raster_contract
        if token not in source
    ]
    if missing_r168_line_raster:
        raise SystemExit(
            "DX11 R168 line-raster provenance drift: "
            + ", ".join(missing_r168_line_raster)
        )

    r205_line_raster_census_contract = [
        (
            "bool lineRasterObservationComplete{};",
            RUNTIME_CENSUS,
            "R205 line-raster census observation identity",
        ),
        (
            "DWORD lastPixel = TRUE;",
            RUNTIME_CENSUS,
            "R205 LASTPIXEL census identity",
        ),
        (
            "DWORD antialiasedLineEnable = FALSE;",
            RUNTIME_CENSUS,
            "R205 antialiased-line census identity",
        ),
        (
            "hash, sig.lineRasterObservationComplete ? 1u : 0u",
            RUNTIME_CENSUS,
            "R205 line-raster observation hash",
        ),
        (
            "hash = hash_mix(hash, sig.lastPixel);",
            RUNTIME_CENSUS,
            "R205 LASTPIXEL value hash",
        ),
        (
            "hash = hash_mix(hash, sig.antialiasedLineEnable);",
            RUNTIME_CENSUS,
            "R205 antialiased-line value hash",
        ),
        (
            "signature.lastPixel = source.lastPixel;",
            RUNTIME_CENSUS,
            "R205 LASTPIXEL capture propagation",
        ),
        (
            "signature.antialiasedLineEnable = source.antialiasedLineEnable;",
            RUNTIME_CENSUS,
            "R205 antialiased-line capture propagation",
        ),
        (
            "VR DX11 R205 line-raster state#{}",
            RUNTIME_CENSUS,
            "R205 detailed line-raster census evidence",
        ),
        (
            "primitive != D3DPT_LINELIST && primitive != D3DPT_LINESTRIP;",
            NATIVE_BACKEND_CPP,
            "R205 direct line dispatch remains fail closed",
        ),
    ]
    missing_r205_line_raster_census = [
        meaning
        for token, source, meaning in r205_line_raster_census_contract
        if token not in source
    ]
    if missing_r205_line_raster_census:
        raise SystemExit(
            "DX11 R205 line-raster census identity drift: "
            + ", ".join(missing_r205_line_raster_census)
        )


    r175_stream_source_frequency_contract = [
        ("UINT stream0Frequency = 1u;", RUNTIME_CENSUS,
         "R175 stream0 frequency identity and D3D9 default"),
        ("device->GetStreamSourceFreq(", RUNTIME_CENSUS,
         "R175 live stream-frequency observation"),
        ("0, &sig.stream0Frequency", RUNTIME_CENSUS,
         "R175 stream0 frequency capture"),
        ("hash = hash_mix(hash, sig.stream0Frequency);", RUNTIME_CENSUS,
         "R175 stream-frequency signature hash"),
        ("streamSourceFrequencyUnsupported =", RUNTIME_CENSUS,
         "R175 non-default stream-frequency readiness predicate"),
        ("signature.stream0Frequency != 1u", RUNTIME_CENSUS,
         "R175 default-only exactness contract"),
        ("!behaviorDescriptorExact || streamSourceFrequencyUnsupported",
         RUNTIME_CENSUS, "R175 resource behavior unsupported accounting"),
        ("!streamSourceFrequencyUnsupported &&",
         RUNTIME_CENSUS,
         "R175 stream-frequency remains explicit in R219 resourceBehaviorExact fail-closed gate"),
        ("VR DX11 R175 stream0-frequency state#{}", RUNTIME_CENSUS,
         "R175 detailed stream-frequency telemetry"),
    ]
    missing_r175_stream_source_frequency = [
        meaning
        for token, source, meaning in r175_stream_source_frequency_contract
        if token not in source
    ]
    if missing_r175_stream_source_frequency:
        raise SystemExit(
            "DX11 R175 stream-source-frequency contract drift: "
            + ", ".join(missing_r175_stream_source_frequency)
        )

    r179_output_state_census_contract = [
        ("bool outputStateObservationComplete{};", RUNTIME_CENSUS,
         "R179 output-state observation identity"),
        ("DWORD outputBlendFactor = 0xFFFFFFFFu;", RUNTIME_CENSUS,
         "R179 blend-factor identity"),
        ("DWORD outputMultiSampleMask = 0xFFFFFFFFu;", RUNTIME_CENSUS,
         "R179 sample-mask identity"),
        ("D3DVIEWPORT9 outputViewport{};", RUNTIME_CENSUS,
         "R179 viewport identity"),
        ("RECT outputScissorRect{};", RUNTIME_CENSUS,
         "R179 scissor rectangle identity"),
        ("DWORD outputScissorTestEnable = FALSE;", RUNTIME_CENSUS,
         "R179 scissor-enable identity"),
        ("std::uint32_t float_bits(float value) noexcept", RUNTIME_CENSUS,
         "R179 float-bit hashing helper"),
        ("hash, sig.outputStateObservationComplete ? 1u : 0u", RUNTIME_CENSUS,
         "R179 observation completeness hash"),
        ("hash = hash_mix(hash, sig.outputBlendFactor);", RUNTIME_CENSUS,
         "R179 blend-factor hash"),
        ("hash = hash_mix(hash, sig.outputMultiSampleMask);", RUNTIME_CENSUS,
         "R179 sample-mask hash"),
        ("float_bits(sig.outputViewport.MinZ)", RUNTIME_CENSUS,
         "R179 viewport minimum-depth hash"),
        ("float_bits(sig.outputViewport.MaxZ)", RUNTIME_CENSUS,
         "R179 viewport maximum-depth hash"),
        ("sig.outputScissorRect.left", RUNTIME_CENSUS,
         "R179 scissor rectangle hash"),
        ("hash = hash_mix(hash, sig.outputScissorTestEnable);", RUNTIME_CENSUS,
         "R179 scissor-enable hash"),
        ("captured && source.complete && source.outputStateComplete;",
         RUNTIME_CENSUS, "R179 output-state completeness propagation"),
        ("signature.outputBlendFactor = source.blendFactor;", RUNTIME_CENSUS,
         "R179 blend-factor capture propagation"),
        ("signature.outputMultiSampleMask = source.multiSampleMask;", RUNTIME_CENSUS,
         "R179 sample-mask capture propagation"),
        ("signature.outputViewport = source.viewport;", RUNTIME_CENSUS,
         "R179 viewport capture propagation"),
        ("signature.outputScissorRect = source.scissorRect;", RUNTIME_CENSUS,
         "R179 scissor capture propagation"),
        ("signature.outputScissorTestEnable = source.scissorTestEnable;",
         RUNTIME_CENSUS, "R179 scissor-enable capture propagation"),
        ("VR DX11 R179 output state#{}", RUNTIME_CENSUS,
         "R179 detailed output-state telemetry"),
        ("out.sampleMask = source.multiSampleMask;", NATIVE_BACKEND_CPP,
         "R124/R179 sample-mask native consumer"),
        ("context->RSSetViewports(1, &viewport_);", NATIVE_BACKEND_CPP,
         "R124/R179 viewport native binding"),
        ("context->RSSetScissorRects(1, &scissor_rect_);", NATIVE_BACKEND_CPP,
         "R124/R179 scissor native binding"),
        ("context->OMSetBlendState(", NATIVE_BACKEND_CPP,
         "R124/R179 dynamic blend/sample-mask native binding"),
    ]
    missing_r179_output_state_census = [
        meaning
        for token, source, meaning in r179_output_state_census_contract
        if token not in source
    ]
    if missing_r179_output_state_census:
        raise SystemExit(
            "DX11 R179 dynamic output-state census contract drift: "
            + ", ".join(missing_r179_output_state_census)
        )

    r174_source_mrt_contract = [
        ("bool auxiliaryRenderTargetObservationComplete = true;", RUNTIME_CENSUS,
         "R174 auxiliary MRT observation identity"),
        ("std::uint8_t auxiliaryRenderTargetMask{};", RUNTIME_CENSUS,
         "R174 auxiliary MRT mask identity"),
        ("device->GetDeviceCaps(&caps)", RUNTIME_CENSUS,
         "R174 source MRT capability bound"),
        ("device->GetRenderTarget(index, &auxiliary)", RUNTIME_CENSUS,
         "R174 source MRT live observation"),
        ("hash, sig.auxiliaryRenderTargetObservationComplete ? 1u : 0u",
         RUNTIME_CENSUS, "R174 MRT observation hash"),
        ("hash = hash_mix(hash, sig.auxiliaryRenderTargetMask);",
         RUNTIME_CENSUS, "R174 MRT mask hash"),
        ("UnsupportedAuxiliaryRenderTargetSamples", RUNTIME_CENSUS,
         "R174 dedicated MRT unsupported counter"),
        ("signature.auxiliaryRenderTargetMask != 0", RUNTIME_CENSUS,
         "R174 resource exactness fail-closed gate"),
        ("auxRenderTargetUnsupported={}", RUNTIME_CENSUS,
         "R174 summary unsupported label"),
        ("VR DX11 R174 source MRT state#{}", RUNTIME_CENSUS,
         "R174 detailed source MRT telemetry"),
    ]
    missing_r174_source_mrt = [
        meaning
        for token, source, meaning in r174_source_mrt_contract
        if token not in source
    ]
    if missing_r174_source_mrt:
        raise SystemExit(
            "DX11 R174 source MRT census contract drift: "
            + ", ".join(missing_r174_source_mrt)
        )

    r177_surface_msaa_census_contract = [
        ("D3DMULTISAMPLE_TYPE renderTargetMultiSampleType =",
         RUNTIME_CENSUS, "R177 RT0 sample-type census identity"),
        ("DWORD renderTargetMultiSampleQuality = 0;",
         RUNTIME_CENSUS, "R177 RT0 sample-quality census identity"),
        ("D3DMULTISAMPLE_TYPE depthMultiSampleType =",
         RUNTIME_CENSUS, "R177 depth sample-type census identity"),
        ("DWORD depthMultiSampleQuality = 0;",
         RUNTIME_CENSUS, "R177 depth sample-quality census identity"),
        ("sig.renderTargetMultiSampleType = desc.MultiSampleType;",
         RUNTIME_CENSUS, "R177 RT0 sample-type capture"),
        ("sig.renderTargetMultiSampleQuality =",
         RUNTIME_CENSUS, "R177 RT0 sample-quality capture"),
        ("sig.depthMultiSampleType = desc.MultiSampleType;",
         RUNTIME_CENSUS, "R177 depth sample-type capture"),
        ("sig.depthMultiSampleQuality = desc.MultiSampleQuality;",
         RUNTIME_CENSUS, "R177 depth sample-quality capture"),
        ("sig.renderTargetMultiSampleType));",
         RUNTIME_CENSUS, "R177 RT0 sample-type signature hash"),
        ("hash = hash_mix(hash, sig.renderTargetMultiSampleQuality);",
         RUNTIME_CENSUS, "R177 RT0 sample-quality signature hash"),
        ("sig.depthMultiSampleType));",
         RUNTIME_CENSUS, "R177 depth sample-type signature hash"),
        ("hash = hash_mix(hash, sig.depthMultiSampleQuality);",
         RUNTIME_CENSUS, "R177 depth sample-quality signature hash"),
        ("surfaceMultisampleUnsupported =", RUNTIME_CENSUS,
         "R177 non-MSAA resource-exactness predicate"),
        ("signature.renderTargetMultiSampleType != D3DMULTISAMPLE_NONE",
         RUNTIME_CENSUS, "R177 RT0 MSAA fail-closed gate"),
        ("signature.depthMultiSampleType != D3DMULTISAMPLE_NONE",
         RUNTIME_CENSUS, "R177 depth MSAA fail-closed gate"),
        ("VR DX11 R177 surface MSAA state#{}", RUNTIME_CENSUS,
         "R177 detailed source-surface MSAA telemetry"),
        ("unproven D3D9-to-DXGI MSAA mapping must fail closed",
         SURFACE_MIRROR_PROBE, "surface mirror MSAA rejection oracle"),
    ]
    missing_r177_surface_msaa_census = [
        meaning
        for token, source, meaning in r177_surface_msaa_census_contract
        if token not in source
    ]
    if missing_r177_surface_msaa_census:
        raise SystemExit(
            "DX11 R177 surface MSAA census contract drift: "
            + ", ".join(missing_r177_surface_msaa_census)
        )

    r212_rt0_color_write_census_contract = [
        ("read(D3DRS_COLORWRITEENABLE, out.colorWriteEnable);",
         D3D9_RENDER_STATE_CAPTURE, "R212 live RT0 color-write capture"),
        ("rt.RenderTargetWriteMask = translate_color_write_mask(",
         PIPELINE_TRANSLATION_CPP, "R212 exact RT0 write-mask translation"),
        ("bool rt0ColorWriteObservationComplete{};", RUNTIME_CENSUS,
         "R212 RT0 color-write observation identity"),
        ("DWORD colorWriteEnable =", RUNTIME_CENSUS,
         "R212 RT0 color-write value identity"),
        ("hash, sig.rt0ColorWriteObservationComplete ? 1u : 0u",
         RUNTIME_CENSUS, "R212 RT0 observation hash"),
        ("hash = hash_mix(hash, sig.colorWriteEnable);",
         RUNTIME_CENSUS, "R212 RT0 write-mask hash"),
        ("signature.rt0ColorWriteObservationComplete =",
         RUNTIME_CENSUS, "R212 RT0 observation propagation"),
        ("signature.colorWriteEnable = source.colorWriteEnable;",
         RUNTIME_CENSUS, "R212 RT0 write-mask propagation"),
        ("VR DX11 R212 RT0 color-write state#{}",
         RUNTIME_CENSUS, "R212 detailed RT0 color-write telemetry"),
    ]
    missing_r212_rt0_color_write_census = [
        meaning
        for token, source, meaning in r212_rt0_color_write_census_contract
        if token not in source
    ]
    if missing_r212_rt0_color_write_census:
        raise SystemExit(
            "DX11 R212 RT0 color-write census identity drift: "
            + ", ".join(missing_r212_rt0_color_write_census)
        )

    r213_output_state_exactness_contract = [
        ("bool outputStateObservationComplete{};", RUNTIME_CENSUS,
         "R213 output-state observation identity"),
        ("captured && source.complete && source.outputStateComplete;",
         RUNTIME_CENSUS, "R213 output-state observation propagation"),
        ("if (!source.outputStateComplete ||", NATIVE_BACKEND_CPP,
         "native output-state readiness fail-closed boundary"),
        ("signature.outputStateObservationComplete &&", RUNTIME_CENSUS,
         "R213 ExactSamples output-state observation gate"),
    ]
    missing_r213_output_state_exactness = [
        meaning
        for token, source, meaning in r213_output_state_exactness_contract
        if token not in source
    ]
    if missing_r213_output_state_exactness:
        raise SystemExit(
            "DX11 R213 output-state census exactness drift: "
            + ", ".join(missing_r213_output_state_exactness)
        )

    mrt_color_write_contract = [
        ("std::array<DWORD, 3> additionalColorWriteEnable{",
         D3D9_DRAW_STATE_HPP, "tracked MRT color-write fields"),
        ("D3DRS_COLORWRITEENABLE1, D3DRS_COLORWRITEENABLE2,",
         D3D9_RENDER_STATE_CAPTURE, "primed MRT color-write states"),
        ("read(D3DRS_COLORWRITEENABLE1, out.additionalColorWriteEnable[0]);",
         D3D9_RENDER_STATE_CAPTURE, "live COLORWRITEENABLE1 capture"),
        ("read(D3DRS_COLORWRITEENABLE3, out.additionalColorWriteEnable[2]);",
         D3D9_RENDER_STATE_CAPTURE, "live COLORWRITEENABLE3 capture"),
        ("PipelineUnsupportedMrtColorWrite = 1u <<",
         PIPELINE_TRANSLATION_HPP, "dedicated MRT color-write blocker"),
        ("for (const auto mask : source.additionalColorWriteEnable)",
         PIPELINE_TRANSLATION_CPP, "all-secondary-target readiness scan"),
        ("out.unsupported |= PipelineUnsupportedMrtColorWrite;",
         PIPELINE_TRANSLATION_CPP, "fail-closed pipeline gate"),
        ("bool mrtColorWriteObservationComplete{};", RUNTIME_CENSUS,
         "census observation identity"),
        ("for (const auto mask : sig.additionalColorWriteEnable)",
         RUNTIME_CENSUS, "census mask hash"),
        ("signature.additionalColorWriteEnable =",
         RUNTIME_CENSUS, "census propagation"),
        ("VR DX11 MRT color-write state#{}",
         RUNTIME_CENSUS, "detailed census telemetry"),
        ("?P<mrtColorWrite>", analyzer, "unsupported parser group"),
        ('"mrtColorWrite",', analyzer, "unsupported aggregate key"),
        ("mrt_color_write = run_case(", analyzer_test,
         "analyzer regression fixture"),
        ('mrt_color_write["UnsupportedTotalLatest"] == 9',
         analyzer_test, "analyzer aggregate assertion"),
        ("non-default COLORWRITEENABLE1 must fail closed",
         FIXED_FUNCTION_PIPELINE_PROBE, "MRT1 negative probe"),
        ("fixed-function handoff must retain MRT color-write blocker",
         FIXED_FUNCTION_PIPELINE_PROBE, "fixed-function handoff probe"),
        ("DX11 MRT color-write fail-closed: PASS",
         FIXED_FUNCTION_PIPELINE_PROBE, "hosted probe completion marker"),
    ]
    missing_mrt_color_write = [
        meaning for token, source, meaning in mrt_color_write_contract
        if token not in source
    ]
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_COLORWRITEENABLE1") < 2:
        missing_mrt_color_write.append(
            "COLORWRITEENABLE1 must be both primed and captured")
    if D3D9_RENDER_STATE_CAPTURE.count("D3DRS_COLORWRITEENABLE3") < 2:
        missing_mrt_color_write.append(
            "COLORWRITEENABLE3 must be both primed and captured")
    if missing_mrt_color_write:
        raise SystemExit(
            "DX11 MRT color-write contract drift: "
            + ", ".join(missing_mrt_color_write)
        )

    r220_shader_readiness_exact_samples_contract = [
        ("bool shaderReadinessExact{};", RUNTIME_CENSUS,
         "R220 sampled shader readiness identity"),
        ("sig.shaderReadinessExact ? 1u : 0u", RUNTIME_CENSUS,
         "R220 sampled shader readiness hash identity"),
        ("signature.fixedFunction &&\n            signature.shaderTranslationExact;",
         RUNTIME_CENSUS,
         "R220 fixed-function-only shader readiness derivation"),
        ("signature.shaderReadinessExact &&", RUNTIME_CENSUS,
         "R220 final ExactSamples shader readiness gate"),
        ("Programmable D3D9 shader", RUNTIME_CENSUS,
         "R220 programmable shader fail-closed rationale"),
    ]
    missing_r220_shader_readiness = [
        meaning
        for token, source, meaning in r220_shader_readiness_exact_samples_contract
        if token not in source
    ]
    if missing_r220_shader_readiness:
        raise SystemExit(
            "DX11 R220 shader-readiness ExactSamples contract drift: "
            + ", ".join(missing_r220_shader_readiness)
        )

    compile_probe_start = RUNTIME_CENSUS.find(
        "FixedFunctionPixelShaderCompileProbe pixelCompileProbe{};"
    )
    signature_log_start = RUNTIME_CENSUS.find(
        "if (inserted && unique <= DetailedSignatureLogCap)", compile_probe_start
    )
    if compile_probe_start < 0 or signature_log_start < 0:
        raise SystemExit("DX11 R221 shader compile coverage block not found")
    compile_probe_block = RUNTIME_CENSUS[compile_probe_start:signature_log_start]
    if "unique <= DetailedSignatureLogCap" in compile_probe_block:
        raise SystemExit(
            "DX11 R221 shader compile coverage drift: detailed log cap must not cap compile probes"
        )
    for token in [
        "if (inserted && sig.fixedFunction &&",
        "else if (signatureHashCapHit && sig.fixedFunction &&",
        "FixedFunctionShaderCompileSkippedSignatureCap.fetch_add",
    ]:
        if token not in compile_probe_block:
            raise SystemExit(
                "DX11 R221 shader compile coverage drift: missing " + token
            )

    r222_shader_compile_exact_samples_contract = [
        ("FixedFunctionShaderCompileExactHashes;", RUNTIME_CENSUS,
         "R222 successful compile signature cache"),
        ("bool note_signature(", RUNTIME_CENSUS,
         "R222 signature observer returns compile readiness"),
        ("FixedFunctionShaderCompileExactHashes.find(hash) !=",
         RUNTIME_CENSUS, "R222 repeated-signature cached compile lookup"),
        ("pixelCompileProbe.succeeded &&", RUNTIME_CENSUS,
         "R222 pixel compile success remains an admission requirement"),
        ("FixedFunctionShaderCompileExactHashes.insert(hash);",
         RUNTIME_CENSUS, "R222 compile success cache insertion"),
        ("return shaderCompileReadinessExact;", RUNTIME_CENSUS,
         "R222 fail-closed signature readiness result"),
        ("const bool shaderCompileReadinessExact =\n            note_signature(signature, primitive);",
         RUNTIME_CENSUS, "R222 sampled compile readiness capture"),
        ("signature.shaderReadinessExact &&\n            shaderCompileReadinessExact &&\n            signature.shaderTranslationExact",
         RUNTIME_CENSUS, "R222 final ExactSamples compile-readiness gate"),
        ("existing signature observed\n            // before another thread finishes its first compile probe remains",
         RUNTIME_CENSUS, "R222 concurrent first-probe fail-closed rule"),
    ]
    missing_r222_shader_compile_exactness = [
        meaning
        for token, source, meaning in r222_shader_compile_exact_samples_contract
        if token not in source
    ]
    if missing_r222_shader_compile_exactness:
        raise SystemExit(
            "DX11 R222 shader-compile ExactSamples contract drift: "
            + ", ".join(missing_r222_shader_compile_exactness)
        )

    r223_vertex_compile_exact_samples_contract = [
        ("FixedFunctionVertexShaderCompileProbe", PIPELINE_TRANSLATION_HPP,
         "R223 vertex compiler probe type"),
        ("compile_fixed_function_vertex_shader_prototype(",
         PIPELINE_TRANSLATION_HPP, "R223 vertex compiler probe declaration"),
        ('"vs_4_0"', PIPELINE_TRANSLATION_CPP,
         "R223 generated vertex source compiler target"),
        ("fixedFunctionVertexShaderPrototypeSource", RUNTIME_CENSUS,
         "R223 per-signature generated vertex source retention"),
        ("FixedFunctionVertexShaderCompileProbe vertexCompileProbe{};",
         RUNTIME_CENSUS, "R223 bounded vertex compile probe"),
        ("pixelCompileProbe.succeeded &&\n                    vertexCompileProbe.succeeded",
         RUNTIME_CENSUS, "R223 VS/PS pair compile exactness gate"),
        ("compile_fixed_function_vertex_shader_prototype(",
         RUNTIME_CENSUS, "R223 census vertex compile invocation"),
        ("compile_fixed_function_vertex_shader_prototype(vertexPrototype)",
         SEMANTIC_SMOKE, "R223 hosted vertex compiler smoke"),
    ]
    missing_r223_vertex_compile_exactness = [
        meaning
        for token, source, meaning in r223_vertex_compile_exact_samples_contract
        if token not in source
    ]
    if missing_r223_vertex_compile_exactness:
        raise SystemExit(
            "DX11 R223 vertex-shader compile ExactSamples contract drift: "
            + ", ".join(missing_r223_vertex_compile_exactness)
        )

    r223_compile_log_contract = [
        ("pixelCompileProbe.attempted ? 1 : 0",
         "R223 pixel compiler telemetry uses the live probe"),
        ("vertexCompileProbe.attempted ? 1 : 0",
         "R223 vertex compiler telemetry uses the live probe"),
        ("profile=vs_4_0", "R223 vertex compiler telemetry profile"),
    ]
    missing_r223_compile_log = [
        meaning for token, meaning in r223_compile_log_contract
        if token not in RUNTIME_CENSUS
    ]
    if "compileProbe." in RUNTIME_CENSUS:
        missing_r223_compile_log.append(
            "stale pre-R223 compileProbe identifier remains in runtime census"
        )
    if missing_r223_compile_log:
        raise SystemExit(
            "DX11 R223 compiler telemetry contract drift: "
            + ", ".join(missing_r223_compile_log)
        )

    r224_vertex_compile_analyzer_contract = [
        ("FFP_VERTEX_SHADER_COMPILE_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R224 vertex compiler telemetry parser"),
        ("VR DX11 R223 ffp vertex shader compile#",
         DX11_CENSUS_ANALYZER, "R224 vertex compiler log grammar"),
        ("fixed_function_vertex_shader_compiles",
         DX11_CENSUS_ANALYZER, "R224 vertex compiler evidence store"),
        ('signature["fixed_function_vertex_shader_compile"]',
         DX11_CENSUS_ANALYZER, "R224 per-signature analyzer output"),
        ("VR DX11 R223 ffp vertex shader compile#1",
         DX11_CENSUS_ANALYZER_TEST, "R224 analyzer regression fixture"),
    ]
    missing_r224_vertex_compile_analyzer = [
        meaning
        for token, source, meaning in r224_vertex_compile_analyzer_contract
        if token not in source
    ]
    if missing_r224_vertex_compile_analyzer:
        raise SystemExit(
            "DX11 R224 vertex-compiler analyzer parity drift: "
            + ", ".join(missing_r224_vertex_compile_analyzer)
        )

    r225_multi_log_signature_namespace_contract = [
        ("SignatureKey = tuple[str, int, int]",
         DX11_CENSUS_ANALYZER, "R225/R233 source-log and startup-epoch signature namespace type"),
        ("signature_key = (source_log, startup_epoch, signature_id)",
         DX11_CENSUS_ANALYZER, "R225/R233 per-log startup-epoch signature key"),
        ('"source_log": source_log',
         DX11_CENSUS_ANALYZER, "R225 report provenance field"),
        ("r225_multi_log = run_cases(",
         DX11_CENSUS_ANALYZER_TEST, "R225 multi-log regression fixture"),
        ('r225_multi_log["UniqueSignaturesCaptured"] == 2',
         DX11_CENSUS_ANALYZER_TEST, "R225 cross-session collision assertion"),
    ]
    missing_r225_multi_log_signature_namespace = [
        meaning
        for token, source, meaning
        in r225_multi_log_signature_namespace_contract
        if token not in source
    ]
    if missing_r225_multi_log_signature_namespace:
        raise SystemExit(
            "DX11 R225 multi-log signature namespace drift: "
            + ", ".join(missing_r225_multi_log_signature_namespace)
        )

    r226_multi_log_summary_scope_contract = [
        ('summary["source_log"] = source_log',
         DX11_CENSUS_ANALYZER, "R226 summary source-log provenance"),
        ("latest_summaries_by_log: dict[str, dict] = {}",
         DX11_CENSUS_ANALYZER, "R226 per-log latest summary map"),
        ('"AllSourceLogsHavePeriodicSummary": all_source_logs_have_periodic_summary',
         DX11_CENSUS_ANALYZER, "R226 summary completeness evidence"),
        ('elif not all_source_logs_have_summary:',
         DX11_CENSUS_ANALYZER, "R226 partial-summary fail-closed status"),
        ("r226_multi_log_summary = run_cases(",
         DX11_CENSUS_ANALYZER_TEST, "R226 multi-log summary regression fixture"),
        ('r226_multi_log_summary["UnsupportedTotalLatest"] == 64',
         DX11_CENSUS_ANALYZER_TEST, "R226 cross-session unsupported rollup assertion"),
        ('r226_partial_summary["Status"] == "TRANSLATION_EXACTNESS_PENDING"',
         DX11_CENSUS_ANALYZER_TEST, "R226 missing-summary fail-closed assertion"),
    ]
    missing_r226_multi_log_summary_scope = [
        meaning
        for token, source, meaning
        in r226_multi_log_summary_scope_contract
        if token not in source
    ]
    if missing_r226_multi_log_summary_scope:
        raise SystemExit(
            "DX11 R226 multi-log summary scope drift: "
            + ", ".join(missing_r226_multi_log_summary_scope)
        )

    r227_multi_log_startup_bootstrap_provenance_contract = [
        ("startup_entry[\"source_log\"] = source_log",
         DX11_CENSUS_ANALYZER, "R227 startup source-log provenance"),
        ("bootstrap_entry[\"source_log\"] = source_log",
         DX11_CENSUS_ANALYZER, "R227 bootstrap source-log provenance"),
        ("r227_multi_log_startup_bootstrap = run_cases(",
         DX11_CENSUS_ANALYZER_TEST, "R227 multi-log startup/bootstrap regression fixture"),
        ("session-a-startup.log",
         DX11_CENSUS_ANALYZER_TEST, "R227 first startup/bootstrap source assertion"),
        ("session-b-startup.log",
         DX11_CENSUS_ANALYZER_TEST, "R227 second startup/bootstrap source assertion"),
    ]
    missing_r227_multi_log_startup_bootstrap_provenance = [
        meaning
        for token, source, meaning
        in r227_multi_log_startup_bootstrap_provenance_contract
        if token not in source
    ]
    if missing_r227_multi_log_startup_bootstrap_provenance:
        raise SystemExit(
            "DX11 R227 multi-log startup/bootstrap provenance drift: "
            + ", ".join(missing_r227_multi_log_startup_bootstrap_provenance)
        )

    r228_multi_log_startup_bootstrap_coverage_contract = [
        ("latest_startup_by_log: dict[str, dict] = {}",
         DX11_CENSUS_ANALYZER, "R228 per-log latest startup map"),
        ("latest_bootstrap_by_log: dict[str, dict] = {}",
         DX11_CENSUS_ANALYZER, "R228 per-log latest bootstrap map"),
        ('"AllSourceLogsHaveStartupAndBootstrap": bool(',
         DX11_CENSUS_ANALYZER, "R228 startup/bootstrap completeness evidence"),
        ('"StartupBootstrapCoverage": startup_bootstrap_coverage',
         DX11_CENSUS_ANALYZER, "R228 activation-evidence coverage export"),
        ("r228_startup_bootstrap_coverage = run_cases(",
         DX11_CENSUS_ANALYZER_TEST, "R228 partial bootstrap coverage regression fixture"),
        ('"LogsWithBootstrap": 1',
         DX11_CENSUS_ANALYZER_TEST, "R228 missing bootstrap accounting assertion"),
        ('"AllSourceLogsHaveStartupAndBootstrap": False',
         DX11_CENSUS_ANALYZER_TEST, "R228 completeness fail-closed evidence assertion"),
    ]
    missing_r228_multi_log_startup_bootstrap_coverage = [
        meaning
        for token, source, meaning
        in r228_multi_log_startup_bootstrap_coverage_contract
        if token not in source
    ]
    if missing_r228_multi_log_startup_bootstrap_coverage:
        raise SystemExit(
            "DX11 R228 multi-log startup/bootstrap coverage drift: "
            + ", ".join(missing_r228_multi_log_startup_bootstrap_coverage)
        )

    r229_bootstrap_skip_outcome_contract = [
        ("BOOTSTRAP_SKIP_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R229 explicit bootstrap-skip parser"),
        ("bootstrap_skipped: list[dict] = []",
         DX11_CENSUS_ANALYZER, "R229 bootstrap-skip evidence list"),
        ("latest_bootstrap_skip_by_log: dict[str, dict] = {}",
         DX11_CENSUS_ANALYZER, "R229 per-log latest bootstrap-skip map"),
        ('"LogsWithBootstrapSkip": len(latest_bootstrap_skip_by_log)',
         DX11_CENSUS_ANALYZER, "R229 bootstrap-skip coverage accounting"),
        ('"AllSourceLogsHaveBootstrapOutcome": all_source_logs_have_bootstrap_outcome',
         DX11_CENSUS_ANALYZER, "R229 explicit bootstrap outcome completeness"),
        ('"BootstrapSkipped": bootstrap_skipped',
         DX11_CENSUS_ANALYZER, "R229 bootstrap-skip report export"),
        ("r229_bootstrap_skip_outcome = run_cases(",
         DX11_CENSUS_ANALYZER_TEST, "R229 bootstrap-skip multi-log regression fixture"),
        ("VR DX11 R72 bootstrap probe skipped: compatible=0 adapterLuidValid=1",
         DX11_CENSUS_ANALYZER_TEST, "R229 explicit skip telemetry fixture"),
        ('"LogsWithBootstrapOutcome": 2',
         DX11_CENSUS_ANALYZER_TEST, "R229 explicit outcome completeness assertion"),
    ]
    missing_r229_bootstrap_skip_outcome = [
        meaning
        for token, source, meaning in r229_bootstrap_skip_outcome_contract
        if token not in source
    ]
    if missing_r229_bootstrap_skip_outcome:
        raise SystemExit(
            "DX11 R229 bootstrap-skip outcome drift: "
            + ", ".join(missing_r229_bootstrap_skip_outcome)
        )

    r230_latest_bootstrap_outcome_order_contract = [
        ("bootstrap_outcomes: list[dict] = []",
         DX11_CENSUS_ANALYZER, "R230 ordered bootstrap outcome stream"),
        ('bootstrap_outcomes.append({"kind": "probe", **bootstrap_entry})',
         DX11_CENSUS_ANALYZER, "R230 ordered probe outcome append"),
        ('bootstrap_outcomes.append({"kind": "skip", **bootstrap_skip_entry})',
         DX11_CENSUS_ANALYZER, "R230 ordered skip outcome append"),
        ("latest_bootstrap_outcome_by_log: dict[str, dict] = {}",
         DX11_CENSUS_ANALYZER, "R230 latest outcome per source log"),
        ('"LogsWithLatestBootstrapProbe": len(latest_bootstrap_probe_logs)',
         DX11_CENSUS_ANALYZER, "R230 latest probe accounting"),
        ('"BootstrapOutcomeHistoryConflictLogs": bootstrap_outcome_history_conflict_logs',
         DX11_CENSUS_ANALYZER, "R230 mixed-history diagnostic evidence"),
        ('"LatestBootstrapOutcomeByLog": latest_bootstrap_outcome_by_log',
         DX11_CENSUS_ANALYZER, "R230 latest outcome report export"),
        ("r230_latest_bootstrap_outcome_order = run_cases(",
         DX11_CENSUS_ANALYZER_TEST, "R230 ordering regression fixture"),
        ('["kind"] == "skip"',
         DX11_CENSUS_ANALYZER_TEST, "R230 probe-then-skip latest outcome assertion"),
        ('["kind"] == "probe"',
         DX11_CENSUS_ANALYZER_TEST, "R230 skip-then-probe latest outcome assertion"),
    ]
    missing_r230_latest_bootstrap_outcome_order = [
        meaning
        for token, source, meaning in r230_latest_bootstrap_outcome_order_contract
        if token not in source
    ]
    if missing_r230_latest_bootstrap_outcome_order:
        raise SystemExit(
            "DX11 R230 latest bootstrap outcome order drift: "
            + ", ".join(missing_r230_latest_bootstrap_outcome_order)
        )

    r231_latest_startup_bootstrap_pairing_contract = [
        ("latest_startup_line_by_log: dict[str, int] = {}",
         DX11_CENSUS_ANALYZER, "R231 latest startup position map"),
        ("latest_bootstrap_outcome_line_by_log: dict[str, int] = {}",
         DX11_CENSUS_ANALYZER, "R231 latest bootstrap outcome position map"),
        ("latest_startup_bootstrap_outcome_by_log = {",
         DX11_CENSUS_ANALYZER, "R231 current startup/outcome pairing map"),
        ('"LogsWithLatestStartupBootstrapOutcome": len(',
         DX11_CENSUS_ANALYZER, "R231 current startup/outcome coverage count"),
        ('"AllSourceLogsLatestStartupHasBootstrapOutcome": (',
         DX11_CENSUS_ANALYZER, "R231 fail-closed current startup coverage"),
        ('"LatestStartupBootstrapOutcomeByLog": (',
         DX11_CENSUS_ANALYZER, "R231 current startup/outcome report export"),
        ("r231_latest_startup_bootstrap_pairing = run_cases(",
         DX11_CENSUS_ANALYZER_TEST, "R231 accumulated-log regression fixture"),
        ('"session-a-stale-outcome.log" not in (',
         DX11_CENSUS_ANALYZER_TEST, "R231 stale outcome rejection assertion"),
        ('"AllSourceLogsLatestStartupHasBootstrapOutcome": False',
         DX11_CENSUS_ANALYZER_TEST, "R231 latest-startup fail-closed assertion"),
    ]
    missing_r231_latest_startup_bootstrap_pairing = [
        meaning
        for token, source, meaning in r231_latest_startup_bootstrap_pairing_contract
        if token not in source
    ]
    if missing_r231_latest_startup_bootstrap_pairing:
        raise SystemExit(
            "DX11 R231 latest startup/bootstrap pairing drift: "
            + ", ".join(missing_r231_latest_startup_bootstrap_pairing)
        )


    r232_latest_startup_summary_pairing_contract = [
        ("latest_summary_line_by_log: dict[str, int] = {}",
         DX11_CENSUS_ANALYZER, "R232 latest summary position map"),
        ("latest_startup_summary_by_log = {",
         DX11_CENSUS_ANALYZER, "R232 latest startup/summary pairing map"),
        ("current_summaries_by_log = {",
         DX11_CENSUS_ANALYZER, "R232 current summary exactness source"),
        ('"LogsWithCurrentPeriodicSummary": len(current_summaries_by_log)',
         DX11_CENSUS_ANALYZER, "R232 current summary coverage count"),
        ('"AllSourceLogsHaveCurrentPeriodicSummary": all_source_logs_have_summary',
         DX11_CENSUS_ANALYZER, "R232 fail-closed current summary coverage"),
        ('"LatestStartupSummaryByLog": latest_startup_summary_by_log',
         DX11_CENSUS_ANALYZER, "R232 current startup/summary report export"),
        ("r232_latest_startup_summary_pairing = run_cases(",
         DX11_CENSUS_ANALYZER_TEST, "R232 accumulated-log regression fixture"),
        ('"session-a-stale-summary.log"',
         DX11_CENSUS_ANALYZER_TEST, "R232 stale summary rejection fixture"),
        ('"AllSourceLogsHaveCurrentPeriodicSummary": False',
         DX11_CENSUS_ANALYZER_TEST, "R232 latest-startup fail-closed assertion"),
    ]
    missing_r232_latest_startup_summary_pairing = [
        meaning
        for token, source, meaning in r232_latest_startup_summary_pairing_contract
        if token not in source
    ]
    if missing_r232_latest_startup_summary_pairing:
        raise SystemExit(
            "DX11 R232 latest startup/summary pairing drift: "
            + ", ".join(missing_r232_latest_startup_summary_pairing)
        )

    r233_accumulated_log_signature_epoch_contract = [
        ("startup_epoch = 0",
         DX11_CENSUS_ANALYZER, "R233 per-log legacy/startup epoch baseline"),
        ("startup_epoch += 1",
         DX11_CENSUS_ANALYZER, "R233 startup epoch advance"),
        ("SignatureKey = tuple[str, int, int]",
         DX11_CENSUS_ANALYZER, "R233 epoch-scoped signature namespace type"),
        ("signature_key = (source_log, startup_epoch, signature_id)",
         DX11_CENSUS_ANALYZER, "R233 epoch-scoped detail/evidence key"),
        ('"startup_epoch": startup_epoch',
         DX11_CENSUS_ANALYZER, "R233 signature epoch provenance export"),
        ("r233_accumulated_log_signature_epoch = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R233 accumulated-log collision regression fixture"),
        ('["startup_epoch"] for signature in r233_signatures] == [1, 2]',
         DX11_CENSUS_ANALYZER_TEST, "R233 repeated signature id epoch isolation assertion"),
        ('== "0xBBBBBBBBBBBBBBBB"',
         DX11_CENSUS_ANALYZER_TEST, "R233 latest-epoch compile evidence isolation assertion"),
    ]
    missing_r233_accumulated_log_signature_epoch = [
        meaning
        for token, source, meaning in r233_accumulated_log_signature_epoch_contract
        if token not in source
    ]
    if missing_r233_accumulated_log_signature_epoch:
        raise SystemExit(
            "DX11 R233 accumulated-log signature epoch drift: "
            + ", ".join(missing_r233_accumulated_log_signature_epoch)
        )

    r234_current_startup_signature_scope_contract = [
        ("latest_startup_epoch_by_log: dict[str, int] = {}",
         DX11_CENSUS_ANALYZER, "R234 per-log current startup epoch map"),
        ("latest_startup_epoch_by_log[source_log] = startup_epoch",
         DX11_CENSUS_ANALYZER, "R234 current epoch advance tracking"),
        ("current_signatures = {",
         DX11_CENSUS_ANALYZER, "R234 current signature evidence view"),
        ("current_fixed_function = {",
         DX11_CENSUS_ANALYZER, "R234 current fixed-function demand scope"),
        ('"CurrentUniqueSignaturesCaptured": len(current_signatures)',
         DX11_CENSUS_ANALYZER, "R234 current signature count export"),
        ('"HistoricalFixedFunctionDetailedStageDemand": (',
         DX11_CENSUS_ANALYZER, "R234 historical demand provenance export"),
        ("r234_current_startup_signature_scope = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R234 accumulated-log current epoch fixture"),
        ('["CurrentUniqueSignaturesCaptured"] == 1',
         DX11_CENSUS_ANALYZER_TEST, "R234 stale signature exclusion assertion"),
        ('["HasUnsupportedObservedSemantics"]\n        is False',
         DX11_CENSUS_ANALYZER_TEST, "R234 current demand stale-semantics rejection"),
    ]
    missing_r234_current_startup_signature_scope = [
        meaning
        for token, source, meaning in r234_current_startup_signature_scope_contract
        if token not in source
    ]
    if missing_r234_current_startup_signature_scope:
        raise SystemExit(
            "DX11 R234 current startup signature scope drift: "
            + ", ".join(missing_r234_current_startup_signature_scope)
        )

    r235_current_signature_evidence_reconciliation_contract = [
        ("current_signature_evidence_by_log: dict[str, dict] = {}",
         DX11_CENSUS_ANALYZER, "R235 per-log current signature reconciliation"),
        ('"AccountedSignatures": accounted',
         DX11_CENSUS_ANALYZER, "R235 accounted signature evidence export"),
        ("current_signature_evidence_missing_logs = sorted(",
         DX11_CENSUS_ANALYZER, "R235 missing current signature evidence detection"),
        ("current_signature_evidence_overcount_logs = sorted(",
         DX11_CENSUS_ANALYZER, "R235 inconsistent current signature evidence detection"),
        ("all_current_signature_evidence_accounted = bool(source_logs)",
         DX11_CENSUS_ANALYZER, "R235 all-log reconciliation gate"),
        ('"SignatureEvidenceCoverage": signature_coverage',
         DX11_CENSUS_ANALYZER, "R235 activation-evidence coverage export"),
        ("r235_current_signature_evidence_reconciliation = run_cases(",
         DX11_CENSUS_ANALYZER_TEST, "R235 multi-log reconciliation regression fixture"),
        ('["CurrentSignatureEvidenceMissingLogs"] == [',
         DX11_CENSUS_ANALYZER_TEST, "R235 missing-log assertion"),
        ('["AllCurrentSignatureEvidenceAccounted"] is False',
         DX11_CENSUS_ANALYZER_TEST, "R235 fail-closed reconciliation assertion"),
    ]
    missing_r235_current_signature_evidence_reconciliation = [
        meaning
        for token, source, meaning in r235_current_signature_evidence_reconciliation_contract
        if token not in source
    ]
    if missing_r235_current_signature_evidence_reconciliation:
        raise SystemExit(
            "DX11 R235 current signature evidence reconciliation drift: "
            + ", ".join(missing_r235_current_signature_evidence_reconciliation)
        )

    r236_current_signature_hash_cap_coverage_boundary_contract = [
        ('hash_cap_hit_samples = int(summary.get("signatureHashCapHitSamples", 0))',
         DX11_CENSUS_ANALYZER, "R236 per-log signature hash-cap evidence"),
        ('"HashCapSaturated": hash_cap_hit_samples > 0',
         DX11_CENSUS_ANALYZER, "R236 per-log signature hash-cap saturation export"),
        ("current_signature_hash_cap_saturated_logs = sorted(",
         DX11_CENSUS_ANALYZER, "R236 saturated-log aggregation"),
        ('"AllCurrentSignatureEvidenceCoverageComplete": (',
         DX11_CENSUS_ANALYZER, "R236 fail-closed signature universe coverage export"),
        ("r236_current_signature_hash_cap_coverage_boundary = run_cases(",
         DX11_CENSUS_ANALYZER_TEST, "R236 hash-cap coverage regression fixture"),
        ('["AllCurrentSignatureEvidenceAccounted"] is True',
         DX11_CENSUS_ANALYZER_TEST, "R236 accounted-but-saturated boundary assertion"),
        ('["AllCurrentSignatureEvidenceCoverageComplete"] is False',
         DX11_CENSUS_ANALYZER_TEST, "R236 saturated coverage fail-closed assertion"),
    ]
    missing_r236_current_signature_hash_cap_coverage_boundary = [
        meaning
        for token, source, meaning in r236_current_signature_hash_cap_coverage_boundary_contract
        if token not in source
    ]
    if missing_r236_current_signature_hash_cap_coverage_boundary:
        raise SystemExit(
            "DX11 R236 current signature hash-cap coverage boundary drift: "
            + ", ".join(missing_r236_current_signature_hash_cap_coverage_boundary)
        )

    r237_exhaustive_status_signature_evidence_fail_closed_contract = [
        ("and not all_current_signature_evidence_coverage_complete",
         DX11_CENSUS_ANALYZER,
         "R237 exhaustive headline status must require complete current signature evidence"),
        ('"SIGNATURE_EVIDENCE_INCOMPLETE"',
         DX11_CENSUS_ANALYZER,
         "R237 explicit incomplete-signature exhaustive status"),
        ("r237_exhaustive_signature_evidence_status_boundary = (",
         DX11_CENSUS_ANALYZER_TEST,
         "R237 exhaustive incomplete-signature regression boundary"),
        ('== "OBSERVED_EXHAUSTIVE_TRANSLATION_EXACT_SIGNATURE_EVIDENCE_INCOMPLETE"',
         DX11_CENSUS_ANALYZER_TEST,
         "R237 exhaustive incomplete-signature status assertion"),
        ('"VR DX11 R85 signature#4: primitive=4 fixedFn=1 fvf=0x000001C4\\n"',
         DX11_CENSUS_ANALYZER_TEST,
         "R237 positive exhaustive fixture accounts for its complete signature universe"),
    ]
    missing_r237_exhaustive_status_signature_evidence_fail_closed = [
        meaning
        for token, source, meaning
        in r237_exhaustive_status_signature_evidence_fail_closed_contract
        if token not in source
    ]
    if missing_r237_exhaustive_status_signature_evidence_fail_closed:
        raise SystemExit(
            "DX11 R237 exhaustive signature-evidence status drift: "
            + ", ".join(
                missing_r237_exhaustive_status_signature_evidence_fail_closed
            )
        )

    r238_programmable_shader_pair_inventory_contract = [
        ("SIGNATURE_SHADER_RE = re.compile(", DX11_CENSUS_ANALYZER,
         "R238 programmable shader identity parser"),
        ("def summarize_programmable_shader_inventory(", DX11_CENSUS_ANALYZER,
         "R238 programmable shader pair inventory"),
        ('"EvidenceLimitedBySignatureDetailCap": detail_cap_saturated',
         DX11_CENSUS_ANALYZER, "R238 detail-cap fail-closed pair evidence"),
        ('"ProgrammableShaderInventory": programmable_shader_inventory',
         DX11_CENSUS_ANALYZER, "R238 analyzer inventory export"),
        ("r238_programmable_shader_pair_inventory = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R238 pair dedupe regression fixture"),
        ('r238_inventory["CurrentUniqueShaderPairs"] == 1',
         DX11_CENSUS_ANALYZER_TEST, "R238 pair dedupe assertion"),
        ("r238_programmable_shader_pair_detail_cap = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R238 detail-cap regression fixture"),
        ('r238_limited["EvidenceCoverageComplete"] is False',
         DX11_CENSUS_ANALYZER_TEST, "R238 incomplete pair coverage assertion"),
    ]
    missing_r238_programmable_shader_pair_inventory = [
        meaning
        for token, source, meaning
        in r238_programmable_shader_pair_inventory_contract
        if token not in source
    ]
    if missing_r238_programmable_shader_pair_inventory:
        raise SystemExit(
            "DX11 R238 programmable shader pair inventory drift: "
            + ", ".join(missing_r238_programmable_shader_pair_inventory)
        )

    r239_programmable_shader_pair_cache_identity_contract = [
        ("struct ProgrammableShaderPairCacheIdentity",
         PIPELINE_TRANSLATION_HPP,
         "R239 programmable pair cache identity type"),
        ("seal_programmable_shader_pair_cache_identity(",
         PIPELINE_TRANSLATION_HPP,
         "R239 programmable pair cache sealing declaration"),
        ("ProgrammableShaderPairIdentityUnsupportedInvalidVertexVersion",
         PIPELINE_TRANSLATION_HPP,
         "R239 stage-typed shader version fail-closed bit"),
        ("mix(0x5653000000000000ull)",
         PIPELINE_TRANSLATION_CPP,
         "R239 VS stage-tagged cache-key identity"),
        ("mix(0x5053000000000000ull)",
         PIPELINE_TRANSLATION_CPP,
         "R239 PS stage-tagged cache-key identity"),
        ("!programmablePair.translationImplemented",
         SHADER_OBJECT_PROBE,
         "R239 identity readiness must not claim translation"),
        ("programmablePairRepeat.cacheKey == programmablePair.cacheKey",
         SHADER_OBJECT_PROBE,
         "R239 deterministic cache-key regression"),
        ("ProgrammableShaderPairIdentityUnsupportedMixedPair",
         SHADER_OBJECT_PROBE,
         "R239 mixed-pair fail-closed regression"),
    ]
    missing_r239_programmable_shader_pair_cache_identity = [
        meaning
        for token, source, meaning
        in r239_programmable_shader_pair_cache_identity_contract
        if token not in source
    ]
    if missing_r239_programmable_shader_pair_cache_identity:
        raise SystemExit(
            "DX11 R239 programmable shader pair cache identity drift: "
            + ", ".join(
                missing_r239_programmable_shader_pair_cache_identity
            )
        )

    r240_programmable_shader_pair_device_cache_contract = [
        ("class NativeProgrammableShaderPairCache final",
         NATIVE_BACKEND_HPP,
         "R240 per-device programmable pair cache owner"),
        ("NativeProgrammableShaderPairCache::cache_for_observation(",
         NATIVE_BACKEND_CPP,
         "R240 programmable cache insertion implementation"),
        ("identity.translationImplemented",
         NATIVE_BACKEND_CPP,
         "R240 identity-only cache must reject translated-state claims"),
        ("found != entries_.end()",
         NATIVE_BACKEND_CPP,
         "R240 duplicate/collision lookup boundary"),
        ("programmableCache.entry_count() == 1",
         CONSTANT_BUFFER_PROBE,
         "R240 duplicate pair dedupe regression"),
        ("forged cache-key collision fails closed",
         CONSTANT_BUFFER_PROBE,
         "R240 cache-key collision fail-closed regression"),
        ("device reinitialize clears entries and invalidates prior snapshots",
         CONSTANT_BUFFER_PROBE,
         "R240 per-device generation isolation regression"),
    ]
    missing_r240_programmable_shader_pair_device_cache = [
        meaning
        for token, source, meaning
        in r240_programmable_shader_pair_device_cache_contract
        if token not in source
    ]
    if missing_r240_programmable_shader_pair_device_cache:
        raise SystemExit(
            "DX11 R240 programmable shader pair device cache drift: "
            + ", ".join(
                missing_r240_programmable_shader_pair_device_cache
            )
        )

    r241_programmable_translation_slot_ownership_contract = [
        ("struct NativeProgrammableShaderTranslationSlotReadiness",
         NATIVE_BACKEND_HPP,
         "R241 translation slot ownership readiness type"),
        ("reserve_translation_slot_for_observation(",
         NATIVE_BACKEND_HPP,
         "R241 translation slot reservation declaration"),
        ("translationObjectsPresent = false",
         NATIVE_BACKEND_CPP,
         "R241 slot ownership must not claim shader objects"),
        ("cache.snapshotToken == cacheSnapshotToken",
         NATIVE_BACKEND_CPP,
         "R241 reservation remains keyed to exact R240 cache snapshot"),
        ("translationSlotGeneration",
         NATIVE_BACKEND_HPP,
         "R241 per-entry translation slot generation"),
        ("cached pair starts without a translation object slot",
         CONSTANT_BUFFER_PROBE,
         "R241 no-implicit-slot regression"),
        ("forged cache-key collision cannot reserve translation slot",
         CONSTANT_BUFFER_PROBE,
         "R241 collision fail-closed regression"),
        ("stale cache snapshot rejected before fresh slot reservation",
         CONSTANT_BUFFER_PROBE,
         "R241 device-generation/cache-snapshot isolation regression"),
    ]
    missing_r241_programmable_translation_slot_ownership = [
        meaning
        for token, source, meaning
        in r241_programmable_translation_slot_ownership_contract
        if token not in source
    ]
    if missing_r241_programmable_translation_slot_ownership:
        raise SystemExit(
            "DX11 R241 programmable translation slot ownership drift: "
            + ", ".join(
                missing_r241_programmable_translation_slot_ownership
            )
        )

    r242_programmable_translation_object_attachment_contract = [
        ("struct NativeProgrammableShaderTranslationObjectReadiness",
         NATIVE_BACKEND_HPP,
         "R242 translated-object attachment readiness type"),
        ("attach_translation_objects_for_observation(",
         NATIVE_BACKEND_HPP,
         "R242 translated-object attachment declaration"),
        ("translation_object_readiness(",
         NATIVE_BACKEND_HPP,
         "R242 translated-object readiness declaration"),
        ("validate_translation_object_snapshot(",
         NATIVE_BACKEND_HPP,
         "R242 translated-object snapshot validation declaration"),
        ("translationObjectReceiptGeneration",
         NATIVE_BACKEND_HPP,
         "R242 per-entry translated-object receipt generation"),
        ("vertexShader->GetDevice(",
         NATIVE_BACKEND_CPP,
         "R242 vertex object exact-device ownership check"),
        ("pixelShader->GetDevice(",
         NATIVE_BACKEND_CPP,
         "R242 pixel object exact-device ownership check"),
        ("translation slot must exist before translated objects attach",
         CONSTANT_BUFFER_PROBE,
         "R242 no-implicit-slot attachment regression"),
        ("same translated object pair attachment is idempotent",
         CONSTANT_BUFFER_PROBE,
         "R242 duplicate attachment idempotence regression"),
        ("different translated object pair cannot replace sealed receipt",
         CONSTANT_BUFFER_PROBE,
         "R242 object replacement fail-closed regression"),
        ("stale slot snapshot cannot attach translated objects",
         CONSTANT_BUFFER_PROBE,
         "R242 stale slot fail-closed regression"),
        ("device reinitialize invalidates translated object receipt",
         CONSTANT_BUFFER_PROBE,
         "R242 device-generation receipt invalidation regression"),
    ]
    missing_r242_programmable_translation_object_attachment = [
        meaning
        for token, source, meaning
        in r242_programmable_translation_object_attachment_contract
        if token not in source
    ]
    if missing_r242_programmable_translation_object_attachment:
        raise SystemExit(
            "DX11 R242 programmable translated-object attachment drift: "
            + ", ".join(
                missing_r242_programmable_translation_object_attachment
            )
        )

    r243_programmable_input_layout_receipt_contract = [
        ("struct NativeProgrammableShaderInputLayoutReadiness",
         NATIVE_BACKEND_HPP,
         "R243 programmable input-layout receipt readiness type"),
        ("attach_input_layout_for_observation(",
         NATIVE_BACKEND_HPP,
         "R243 programmable input-layout attachment declaration"),
        ("input_layout_readiness(",
         NATIVE_BACKEND_HPP,
         "R243 programmable input-layout readiness declaration"),
        ("validate_input_layout_snapshot(",
         NATIVE_BACKEND_HPP,
         "R243 programmable input-layout snapshot validation declaration"),
        ("inputLayoutReceiptGeneration",
         NATIVE_BACKEND_HPP,
         "R243 per-entry input-layout receipt generation"),
        ("hash_pipeline_input_layout_identity(layout)",
         NATIVE_BACKEND_CPP,
         "R243 exact input-layout metadata identity"),
        ("inputLayout->GetDevice(",
         NATIVE_BACKEND_CPP,
         "R243 exact-device input-layout ownership check"),
        ("translated objects must exist before input layout attaches",
         CONSTANT_BUFFER_PROBE,
         "R243 requires validated R242 object receipt"),
        ("different input layout object cannot replace sealed receipt",
         CONSTANT_BUFFER_PROBE,
         "R243 input-layout replacement fail-closed regression"),
        ("changed input layout metadata cannot reuse sealed receipt",
         CONSTANT_BUFFER_PROBE,
         "R243 input-layout metadata replacement fail-closed regression"),
        ("stale object receipt cannot attach input layout",
         CONSTANT_BUFFER_PROBE,
         "R243 stale R242 receipt fail-closed regression"),
        ("device reinitialize invalidates input layout receipt",
         CONSTANT_BUFFER_PROBE,
         "R243 device-generation receipt invalidation regression"),
    ]
    missing_r243_programmable_input_layout_receipt = [
        meaning
        for token, source, meaning
        in r243_programmable_input_layout_receipt_contract
        if token not in source
    ]
    if missing_r243_programmable_input_layout_receipt:
        raise SystemExit(
            "DX11 R243 programmable input-layout receipt drift: "
            + ", ".join(missing_r243_programmable_input_layout_receipt)
        )

    r244_programmable_constant_state_receipt_contract = [
        ("struct NativeProgrammableShaderConstantStateReadiness",
         NATIVE_BACKEND_HPP, "R244 programmable constant-state readiness type"),
        ("attach_constant_state_for_observation(",
         NATIVE_BACKEND_HPP, "R244 constant-state attachment declaration"),
        ("constant_state_readiness(",
         NATIVE_BACKEND_HPP, "R244 constant-state readiness declaration"),
        ("validate_constant_state_snapshot(",
         NATIVE_BACKEND_HPP, "R244 constant-state snapshot validation declaration"),
        ("constantStateReceiptGeneration",
         NATIVE_BACKEND_HPP, "R244 per-entry receipt generation"),
        ("vertexConstantBuffer->GetDevice(",
         NATIVE_BACKEND_CPP, "R244 vertex constant exact-device ownership"),
        ("pixelConstantBuffer->GetDevice(",
         NATIVE_BACKEND_CPP, "R244 pixel constant exact-device ownership"),
        ("desc.BindFlags == D3D11_BIND_CONSTANT_BUFFER",
         NATIVE_BACKEND_CPP, "R244 exact constant-buffer descriptor guard"),
        ("input layout receipt must exist before constant state attaches",
         CONSTANT_BUFFER_PROBE, "R244 validated R243 prerequisite"),
        ("foreign-device constant buffers fail closed",
         CONSTANT_BUFFER_PROBE, "R244 foreign-device regression"),
        ("same constant-state attachment is idempotent",
         CONSTANT_BUFFER_PROBE, "R244 idempotence regression"),
        ("changed constant metadata cannot reuse sealed receipt",
         CONSTANT_BUFFER_PROBE, "R244 metadata mismatch regression"),
        ("different constant buffer object cannot replace sealed receipt",
         CONSTANT_BUFFER_PROBE, "R244 replacement-object regression"),
        ("device reinitialize invalidates constant-state receipt",
         CONSTANT_BUFFER_PROBE, "R244 device-generation invalidation regression"),
        ("stale input-layout receipt cannot attach constant state",
         CONSTANT_BUFFER_PROBE, "R244 stale R243 regression"),
        ("fresh device generation receives distinct constant-state receipt",
         CONSTANT_BUFFER_PROBE, "R244 fresh receipt regression"),
    ]
    missing_r244_programmable_constant_state_receipt = [
        meaning for token, source, meaning
        in r244_programmable_constant_state_receipt_contract
        if token not in source
    ]
    if missing_r244_programmable_constant_state_receipt:
        raise SystemExit(
            "DX11 R244 programmable constant-state receipt drift: "
            + ", ".join(missing_r244_programmable_constant_state_receipt)
        )

    r245_programmable_constant_payload_receipt_contract = [
        ("struct NativeProgrammableShaderConstantPayloadReadiness",
         NATIVE_BACKEND_HPP, "R245 programmable constant-payload readiness type"),
        ("upload_constant_payload_for_observation(",
         NATIVE_BACKEND_HPP, "R245 constant-payload upload declaration"),
        ("constant_payload_readiness(",
         NATIVE_BACKEND_HPP, "R245 constant-payload readiness declaration"),
        ("validate_constant_payload_snapshot(",
         NATIVE_BACKEND_HPP, "R245 constant-payload snapshot validation declaration"),
        ("constantPayloadReceiptGeneration",
         NATIVE_BACKEND_HPP, "R245 per-entry payload receipt generation"),
        ("expectedContext->UpdateSubresource(",
         NATIVE_BACKEND_CPP, "R245 exact constant payload upload operation"),
        ("expectedDevice->GetImmediateContext(",
         NATIVE_BACKEND_CPP, "R245 immediate-context ownership gate"),
        ("entry.constantUploadContext.Get() == expectedContext",
         NATIVE_BACKEND_CPP, "R245 exact upload-context seal"),
        ("deferred context cannot establish upload receipt",
         CONSTANT_BUFFER_PROBE, "R245 deferred-context regression"),
        ("constant-state receipt must exist before payload upload",
         CONSTANT_BUFFER_PROBE, "R245 validated R244 prerequisite"),
        ("foreign-device context fails closed",
         CONSTANT_BUFFER_PROBE, "R245 foreign-context regression"),
        ("exact constant payload upload receipt",
         CONSTANT_BUFFER_PROBE, "R245 exact payload readiness regression"),
        ("same constant payload upload is idempotent",
         CONSTANT_BUFFER_PROBE, "R245 idempotence regression"),
        ("changed constant payload cannot reuse sealed receipt",
         CONSTANT_BUFFER_PROBE, "R245 payload mismatch regression"),
        ("different same-device context cannot replace sealed receipt",
         CONSTANT_BUFFER_PROBE, "R245 context replacement regression"),
        ("device reinitialize invalidates constant-payload receipt",
         CONSTANT_BUFFER_PROBE, "R245 device-generation invalidation regression"),
        ("stale constant-state receipt cannot upload payload",
         CONSTANT_BUFFER_PROBE, "R245 stale R244 regression"),
        ("fresh device generation receives distinct constant-payload receipt",
         CONSTANT_BUFFER_PROBE, "R245 fresh receipt regression"),
    ]
    missing_r245_programmable_constant_payload_receipt = [
        meaning for token, source, meaning
        in r245_programmable_constant_payload_receipt_contract
        if token not in source
    ]
    if missing_r245_programmable_constant_payload_receipt:
        raise SystemExit(
            "DX11 R245 programmable constant-payload receipt drift: "
            + ", ".join(missing_r245_programmable_constant_payload_receipt)
        )

    r246_programmable_constant_binding_receipt_contract = [
        ("struct NativeProgrammableShaderConstantBindingReadiness",
         NATIVE_BACKEND_HPP, "R246 programmable constant-binding readiness type"),
        ("bind_constant_slots_for_observation(",
         NATIVE_BACKEND_HPP, "R246 constant-slot binding declaration"),
        ("constant_binding_readiness(",
         NATIVE_BACKEND_HPP, "R246 constant-binding readiness declaration"),
        ("validate_constant_binding_snapshot(",
         NATIVE_BACKEND_HPP, "R246 constant-binding snapshot validation declaration"),
        ("constantBindingReceiptGeneration",
         NATIVE_BACKEND_HPP, "R246 per-entry binding receipt generation"),
        ("expectedContext->VSSetConstantBuffers(0, 1, &vertexBuffer)",
         NATIVE_BACKEND_CPP, "R246 exact VS b0 binding operation"),
        ("expectedContext->PSSetConstantBuffers(0, 1, &pixelBuffer)",
         NATIVE_BACKEND_CPP, "R246 exact PS b0 binding operation"),
        ("expectedContext->VSGetConstantBuffers(",
         NATIVE_BACKEND_CPP, "R246 VS b0 readback gate"),
        ("expectedContext->PSGetConstantBuffers(",
         NATIVE_BACKEND_CPP, "R246 PS b0 readback gate"),
        ("constant-payload receipt must exist before slot binding",
         CONSTANT_BUFFER_PROBE, "R246 validated R245 prerequisite"),
        ("non-immediate context cannot establish slot binding",
         CONSTANT_BUFFER_PROBE, "R246 context regression"),
        ("exact constant-slot binding receipt",
         CONSTANT_BUFFER_PROBE, "R246 exact binding readiness regression"),
        ("same constant-slot binding is idempotent",
         CONSTANT_BUFFER_PROBE, "R246 idempotence regression"),
        ("external b0 slot drift invalidates binding receipt",
         CONSTANT_BUFFER_PROBE, "R246 state-drift regression"),
        ("device reinitialize invalidates constant-binding receipt",
         CONSTANT_BUFFER_PROBE, "R246 device-generation invalidation regression"),
        ("stale constant-payload receipt cannot bind slots",
         CONSTANT_BUFFER_PROBE, "R246 stale R245 regression"),
        ("fresh device generation receives distinct constant-binding receipt",
         CONSTANT_BUFFER_PROBE, "R246 fresh receipt regression"),
    ]
    missing_r246_programmable_constant_binding_receipt = [
        meaning for token, source, meaning
        in r246_programmable_constant_binding_receipt_contract
        if token not in source
    ]
    if missing_r246_programmable_constant_binding_receipt:
        raise SystemExit(
            "DX11 R246 programmable constant-binding receipt drift: "
            + ", ".join(missing_r246_programmable_constant_binding_receipt)
        )

    r247_programmable_pipeline_binding_receipt_contract = [
        ("struct NativeProgrammableShaderPipelineBindingReadiness",
         NATIVE_BACKEND_HPP, "R247 programmable pipeline-binding readiness type"),
        ("bind_pipeline_objects_for_observation(",
         NATIVE_BACKEND_HPP, "R247 pipeline-object binding declaration"),
        ("pipeline_binding_readiness(",
         NATIVE_BACKEND_HPP, "R247 pipeline-binding readiness declaration"),
        ("validate_pipeline_binding_snapshot(",
         NATIVE_BACKEND_HPP, "R247 pipeline-binding snapshot validation declaration"),
        ("programmableBindingReceiptGeneration",
         NATIVE_BACKEND_HPP, "R247 per-entry pipeline-binding receipt generation"),
        ("expectedContext->VSSetShader(",
         NATIVE_BACKEND_CPP, "R247 exact VS binding operation"),
        ("expectedContext->PSSetShader(",
         NATIVE_BACKEND_CPP, "R247 exact PS binding operation"),
        ("expectedContext->IASetInputLayout(",
         NATIVE_BACKEND_CPP, "R247 exact input-layout binding operation"),
        ("expectedContext->VSGetShader(",
         NATIVE_BACKEND_CPP, "R247 VS readback gate"),
        ("expectedContext->PSGetShader(",
         NATIVE_BACKEND_CPP, "R247 PS readback gate"),
        ("expectedContext->IAGetInputLayout(",
         NATIVE_BACKEND_CPP, "R247 input-layout readback gate"),
        ("constant-binding receipt must exist before pipeline binding",
         CONSTANT_BUFFER_PROBE, "R247 validated R246 prerequisite"),
        ("non-immediate context cannot establish pipeline binding",
         CONSTANT_BUFFER_PROBE, "R247 context regression"),
        ("exact programmable pipeline binding receipt",
         CONSTANT_BUFFER_PROBE, "R247 exact binding regression"),
        ("same programmable pipeline binding is idempotent",
         CONSTANT_BUFFER_PROBE, "R247 idempotence regression"),
        ("external shader drift invalidates pipeline binding receipt",
         CONSTANT_BUFFER_PROBE, "R247 shader-drift regression"),
        ("device reinitialize invalidates pipeline-binding receipt",
         CONSTANT_BUFFER_PROBE, "R247 device-generation invalidation regression"),
        ("stale constant-binding receipt cannot bind pipeline objects",
         CONSTANT_BUFFER_PROBE, "R247 stale R246 regression"),
        ("fresh device generation receives distinct pipeline-binding receipt",
         CONSTANT_BUFFER_PROBE, "R247 fresh receipt regression"),
    ]
    missing_r247_programmable_pipeline_binding_receipt = [
        meaning for token, source, meaning
        in r247_programmable_pipeline_binding_receipt_contract
        if token not in source
    ]
    if missing_r247_programmable_pipeline_binding_receipt:
        raise SystemExit(
            "DX11 R247 programmable pipeline-binding receipt drift: "
            + ", ".join(missing_r247_programmable_pipeline_binding_receipt)
        )

    r248_programmable_topology_binding_receipt_contract = [
        ("struct NativeProgrammableShaderTopologyBindingReadiness",
         NATIVE_BACKEND_HPP, "R248 programmable topology-binding readiness type"),
        ("bind_primitive_topology_for_observation(",
         NATIVE_BACKEND_HPP, "R248 topology binding declaration"),
        ("primitive_topology_binding_readiness(",
         NATIVE_BACKEND_HPP, "R248 topology readiness declaration"),
        ("validate_primitive_topology_binding_snapshot(",
         NATIVE_BACKEND_HPP, "R248 topology snapshot validation declaration"),
        ("topologyBindingReceiptGeneration",
         NATIVE_BACKEND_HPP, "R248 per-entry topology receipt generation"),
        ("translate_primitive(primitiveType)",
         NATIVE_BACKEND_CPP, "R248 exact D3D9 primitive translation gate"),
        ("expectedContext->IASetPrimitiveTopology(topology.value)",
         NATIVE_BACKEND_CPP, "R248 exact IA topology binding"),
        ("expectedContext->IAGetPrimitiveTopology(&current)",
         NATIVE_BACKEND_CPP, "R248 IA topology readback gate"),
        ("pipeline-binding receipt must exist before topology binding",
         CONSTANT_BUFFER_PROBE, "R248 validated R247 prerequisite"),
        ("triangle fan direct topology remains fail closed",
         CONSTANT_BUFFER_PROBE, "R248 triangle-fan direct bind rejection"),
        ("non-immediate context cannot establish topology binding",
         CONSTANT_BUFFER_PROBE, "R248 context regression"),
        ("exact primitive topology binding receipt",
         CONSTANT_BUFFER_PROBE, "R248 exact topology binding regression"),
        ("same primitive topology binding is idempotent",
         CONSTANT_BUFFER_PROBE, "R248 idempotence regression"),
        ("external topology drift invalidates topology binding receipt",
         CONSTANT_BUFFER_PROBE, "R248 topology drift regression"),
        ("device reinitialize invalidates topology-binding receipt",
         CONSTANT_BUFFER_PROBE, "R248 device-generation invalidation regression"),
        ("stale pipeline-binding receipt cannot bind topology",
         CONSTANT_BUFFER_PROBE, "R248 stale R247 regression"),
        ("fresh device generation receives distinct topology-binding receipt",
         CONSTANT_BUFFER_PROBE, "R248 fresh receipt regression"),
        ("restores prior fixed-function IA geometry after topology probe",
         CONSTANT_BUFFER_PROBE, "R248 probe-state restoration regression"),
    ]
    missing_r248_programmable_topology_binding_receipt = [
        meaning for token, source, meaning
        in r248_programmable_topology_binding_receipt_contract
        if token not in source
    ]
    if missing_r248_programmable_topology_binding_receipt:
        raise SystemExit(
            "DX11 R248 programmable topology-binding receipt drift: "
            + ", ".join(missing_r248_programmable_topology_binding_receipt)
        )

    r249_programmable_indexed_geometry_binding_receipt_contract = [
        ("struct NativeProgrammableShaderIndexedGeometryBindingReadiness",
         NATIVE_BACKEND_HPP, "R249 programmable indexed geometry readiness type"),
        ("bind_indexed_geometry_for_observation(",
         NATIVE_BACKEND_HPP, "R249 indexed geometry binding declaration"),
        ("indexed_geometry_binding_readiness(",
         NATIVE_BACKEND_HPP, "R249 indexed geometry readiness declaration"),
        ("validate_indexed_geometry_binding_snapshot(",
         NATIVE_BACKEND_HPP, "R249 indexed geometry snapshot validator"),
        ("indexedGeometryBindingReceiptGeneration",
         NATIVE_BACKEND_HPP, "R249 per-entry indexed geometry receipt generation"),
        ("expectedContext->IASetVertexBuffers(",
         NATIVE_BACKEND_CPP, "R249 exact slot-0 vertex-buffer binding"),
        ("expectedContext->IASetIndexBuffer(",
         NATIVE_BACKEND_CPP, "R249 exact index-buffer binding"),
        ("expectedContext->IAGetVertexBuffers(",
         NATIVE_BACKEND_CPP, "R249 vertex-buffer readback gate"),
        ("expectedContext->IAGetIndexBuffer(",
         NATIVE_BACKEND_CPP, "R249 index-buffer readback gate"),
        ("topology-binding receipt must exist before indexed geometry binding",
         CONSTANT_BUFFER_PROBE, "R249 validated R248 prerequisite"),
        ("stale managed mirror snapshots cannot bind indexed geometry",
         CONSTANT_BUFFER_PROBE, "R249 managed mirror generation regression"),
        ("non-immediate context cannot establish indexed geometry binding",
         CONSTANT_BUFFER_PROBE, "R249 context regression"),
        ("exact programmable indexed geometry binding receipt",
         CONSTANT_BUFFER_PROBE, "R249 exact binding regression"),
        ("same indexed geometry binding is idempotent",
         CONSTANT_BUFFER_PROBE, "R249 idempotence regression"),
        ("external vertex stride drift invalidates indexed geometry receipt",
         CONSTANT_BUFFER_PROBE, "R249 live vertex binding drift regression"),
        ("external index binding drift invalidates indexed geometry receipt",
         CONSTANT_BUFFER_PROBE, "R249 live index binding drift regression"),
        ("upstream topology drift invalidates indexed geometry receipt",
         CONSTANT_BUFFER_PROBE, "R249 upstream topology drift regression"),
        ("device reinitialize invalidates indexed geometry receipt",
         CONSTANT_BUFFER_PROBE, "R249 device-generation invalidation regression"),
        ("stale topology receipt cannot bind indexed geometry",
         CONSTANT_BUFFER_PROBE, "R249 stale R248 regression"),
        ("fresh device generation receives distinct indexed geometry receipt",
         CONSTANT_BUFFER_PROBE, "R249 fresh receipt regression"),
        ("R249 restores prior fixed-function IA geometry after indexed geometry probe",
         CONSTANT_BUFFER_PROBE, "R249 probe-state restoration regression"),
    ]
    missing_r249_programmable_indexed_geometry_binding_receipt = [
        meaning for token, source, meaning
        in r249_programmable_indexed_geometry_binding_receipt_contract
        if token not in source
    ]
    if missing_r249_programmable_indexed_geometry_binding_receipt:
        raise SystemExit(
            "DX11 R249 programmable indexed geometry-binding receipt drift: "
            + ", ".join(missing_r249_programmable_indexed_geometry_binding_receipt)
        )

    r250_programmable_nonindexed_geometry_binding_receipt_contract = [
        ("struct NativeProgrammableShaderNonIndexedGeometryBindingReadiness",
         NATIVE_BACKEND_HPP, "R250 programmable non-indexed geometry readiness type"),
        ("bind_nonindexed_geometry_for_observation(",
         NATIVE_BACKEND_HPP, "R250 non-indexed geometry binding declaration"),
        ("nonindexed_geometry_binding_readiness(",
         NATIVE_BACKEND_HPP, "R250 non-indexed geometry readiness declaration"),
        ("validate_nonindexed_geometry_binding_snapshot(",
         NATIVE_BACKEND_HPP, "R250 non-indexed geometry snapshot validator"),
        ("nonIndexedGeometryBindingReceiptGeneration",
         NATIVE_BACKEND_HPP, "R250 per-entry non-indexed geometry receipt generation"),
        ("nonindexed_geometry_binding_receipt_generation_counter_",
         NATIVE_BACKEND_HPP, "R250 monotonic receipt counter"),
        ("expectedContext->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0);",
         NATIVE_BACKEND_CPP, "R250 explicit IA index-buffer clear"),
        ("out.indexBufferClear =",
         NATIVE_BACKEND_CPP, "R250 index-buffer clear readback gate"),
        ("topology-binding receipt must exist before non-indexed geometry binding",
         CONSTANT_BUFFER_PROBE, "R250 validated R248 prerequisite"),
        ("stale managed vertex mirror snapshot cannot bind non-indexed geometry",
         CONSTANT_BUFFER_PROBE, "R250 managed vertex mirror generation regression"),
        ("non-immediate context cannot establish non-indexed geometry binding",
         CONSTANT_BUFFER_PROBE, "R250 context regression"),
        ("exact programmable non-indexed geometry binding receipt",
         CONSTANT_BUFFER_PROBE, "R250 exact binding regression"),
        ("same non-indexed geometry binding is idempotent",
         CONSTANT_BUFFER_PROBE, "R250 idempotence regression"),
        ("external index binding invalidates explicit IB-clear receipt",
         CONSTANT_BUFFER_PROBE, "R250 live index-clear drift regression"),
        ("external vertex binding drift invalidates non-indexed geometry receipt",
         CONSTANT_BUFFER_PROBE, "R250 live vertex binding drift regression"),
        ("device reinitialize invalidates non-indexed geometry receipt",
         CONSTANT_BUFFER_PROBE, "R250 device-generation invalidation regression"),
        ("stale topology receipt cannot bind non-indexed geometry",
         CONSTANT_BUFFER_PROBE, "R250 stale R248 regression"),
        ("fresh device generation receives distinct non-indexed geometry receipt",
         CONSTANT_BUFFER_PROBE, "R250 fresh receipt regression"),
        ("R250 restores prior fixed-function IA geometry after non-indexed geometry probe",
         CONSTANT_BUFFER_PROBE, "R250 probe-state restoration regression"),
    ]
    missing_r250_programmable_nonindexed_geometry_binding_receipt = [
        meaning for token, source, meaning
        in r250_programmable_nonindexed_geometry_binding_receipt_contract
        if token not in source
    ]
    if missing_r250_programmable_nonindexed_geometry_binding_receipt:
        raise SystemExit(
            "DX11 R250 programmable non-indexed geometry-binding receipt drift: "
            + ", ".join(missing_r250_programmable_nonindexed_geometry_binding_receipt)
        )

    r251_programmable_nonindexed_direct_dispatch_contract = [
        ("struct NativeProgrammableShaderNonIndexedDirectDispatchReadiness",
         NATIVE_BACKEND_HPP, "R251 programmable non-indexed dispatch readiness type"),
        ("nonindexed_direct_dispatch_readiness(",
         NATIVE_BACKEND_HPP, "R251 dispatch readiness declaration"),
        ("validate_nonindexed_direct_dispatch_snapshot(",
         NATIVE_BACKEND_HPP, "R251 dispatch snapshot validator"),
        ("direct_draw_element_count(primitiveType, primitiveCount, vertexCount)",
         NATIVE_BACKEND_CPP, "R251 exact primitive-count translation"),
        ("out.vertexRangeExact =",
         NATIVE_BACKEND_CPP, "R251 vertex-buffer byte-range gate"),
        ("out.geometryBindingSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R251 R250 receipt lineage gate"),
        ("R251 exact programmable non-indexed direct dispatch arguments",
         CONSTANT_BUFFER_PROBE, "R251 exact dispatch regression"),
        ("R251 stale R250 geometry receipt cannot seal dispatch arguments",
         CONSTANT_BUFFER_PROBE, "R251 stale geometry snapshot regression"),
        ("R251 out-of-range non-indexed vertex window fails closed",
         CONSTANT_BUFFER_PROBE, "R251 vertex range regression"),
        ("R251 primitive-count overflow fails closed",
         CONSTANT_BUFFER_PROBE, "R251 count overflow regression"),
        ("R251 same non-indexed direct dispatch arguments are idempotent",
         CONSTANT_BUFFER_PROBE, "R251 idempotence regression"),
        ("R251 live IA drift invalidates non-indexed dispatch receipt",
         CONSTANT_BUFFER_PROBE, "R251 live IA drift regression"),
        ("R251 device reinitialize invalidates non-indexed dispatch receipt",
         CONSTANT_BUFFER_PROBE, "R251 device-generation regression"),
        ("R251 fresh device generation receives distinct non-indexed dispatch receipt",
         CONSTANT_BUFFER_PROBE, "R251 fresh-generation regression"),
    ]
    missing_r251_programmable_nonindexed_direct_dispatch = [
        meaning for token, source, meaning
        in r251_programmable_nonindexed_direct_dispatch_contract
        if token not in source
    ]
    if missing_r251_programmable_nonindexed_direct_dispatch:
        raise SystemExit(
            "DX11 R251 programmable non-indexed direct-dispatch drift: "
            + ", ".join(missing_r251_programmable_nonindexed_direct_dispatch)
        )

    r252_programmable_indexed_direct_dispatch_contract = [
        ("struct NativeProgrammableShaderIndexedDirectDispatchReadiness",
         NATIVE_BACKEND_HPP, "R252 programmable indexed dispatch readiness type"),
        ("indexed_direct_dispatch_readiness(",
         NATIVE_BACKEND_HPP, "R252 indexed dispatch readiness declaration"),
        ("validate_indexed_direct_dispatch_snapshot(",
         NATIVE_BACKEND_HPP, "R252 indexed dispatch snapshot validator"),
        ("direct_draw_element_count(primitiveType, primitiveCount, indexCount)",
         NATIVE_BACKEND_CPP, "R252 exact indexed primitive-count translation"),
        ("out.sourceVertexRangeExact =",
         NATIVE_BACKEND_CPP, "R252 declared D3D9 source-vertex range gate"),
        ("out.effectiveVertexRangeExact =",
         NATIVE_BACKEND_CPP, "R252 BaseVertexIndex effective-range gate"),
        ("out.indexBufferRangeExact =",
         NATIVE_BACKEND_CPP, "R252 index-buffer byte-range gate"),
        ("out.vertexBufferRangeExact =",
         NATIVE_BACKEND_CPP, "R252 vertex-buffer byte-range gate"),
        ("R252 exact programmable indexed dispatch and source range",
         CONSTANT_BUFFER_PROBE, "R252 exact dispatch/source-range regression"),
        ("R252 stale R249 geometry receipt cannot seal indexed dispatch",
         CONSTANT_BUFFER_PROBE, "R252 stale geometry snapshot regression"),
        ("R252 out-of-range index window fails closed",
         CONSTANT_BUFFER_PROBE, "R252 index byte-range regression"),
        ("R252 out-of-range declared vertex window fails closed",
         CONSTANT_BUFFER_PROBE, "R252 vertex byte-range regression"),
        ("R252 negative effective vertex range fails closed",
         CONSTANT_BUFFER_PROBE, "R252 signed BaseVertexIndex regression"),
        ("R252 indexed primitive-count overflow fails closed",
         CONSTANT_BUFFER_PROBE, "R252 count overflow regression"),
        ("R252 same indexed dispatch arguments are idempotent",
         CONSTANT_BUFFER_PROBE, "R252 idempotence regression"),
        ("R252 live IA drift invalidates indexed dispatch receipt",
         CONSTANT_BUFFER_PROBE, "R252 live IA drift regression"),
        ("R252 device reinitialize invalidates indexed dispatch receipt",
         CONSTANT_BUFFER_PROBE, "R252 device-generation regression"),
        ("R252 fresh device generation receives distinct indexed dispatch receipt",
         CONSTANT_BUFFER_PROBE, "R252 fresh-generation regression"),
    ]
    missing_r252_programmable_indexed_direct_dispatch = [
        meaning for token, source, meaning
        in r252_programmable_indexed_direct_dispatch_contract
        if token not in source
    ]
    if missing_r252_programmable_indexed_direct_dispatch:
        raise SystemExit(
            "DX11 R252 programmable indexed direct-dispatch drift: "
            + ", ".join(missing_r252_programmable_indexed_direct_dispatch)
        )

    r253_programmable_indexed_source_value_contract = [
        ("struct NativeProgrammableShaderIndexedSourceValueReadiness",
         NATIVE_BACKEND_HPP, "R253 programmable indexed source-value readiness type"),
        ("indexed_source_value_readiness(",
         NATIVE_BACKEND_HPP, "R253 source-value readiness declaration"),
        ("validate_indexed_source_value_snapshot(",
         NATIVE_BACKEND_HPP, "R253 source-value snapshot validator"),
        ("indexBuffer.index_range_readiness(",
         NATIVE_BACKEND_CPP, "R253 reuses managed CPU-shadow index scanner"),
        ("out.sourceValuesMatchDispatchWindow =",
         NATIVE_BACKEND_CPP, "R253 exact dispatch index-window lineage"),
        ("out.sourceValuesMatchDispatchRange =",
         NATIVE_BACKEND_CPP, "R253 exact declared source-range lineage"),
        ("R253 programmable indexed source values seal exact managed IB contents",
         CONSTANT_BUFFER_PROBE, "R253 exact managed index-content regression"),
        ("R253 rejects managed source index outside declared D3D9 vertex range",
         CONSTANT_BUFFER_PROBE, "R253 declared-range value regression"),
        ("R253 stale R252 dispatch receipt cannot seal source values",
         CONSTANT_BUFFER_PROBE, "R253 stale dispatch receipt regression"),
    ]
    missing_r253_programmable_indexed_source_value = [
        meaning for token, source, meaning
        in r253_programmable_indexed_source_value_contract
        if token not in source
    ]
    if missing_r253_programmable_indexed_source_value:
        raise SystemExit(
            "DX11 R253 programmable indexed source-value drift: "
            + ", ".join(missing_r253_programmable_indexed_source_value)
        )

    r254_programmable_live_index_binding_contract = [
        ("struct NativeProgrammableShaderIndexedLiveIndexBindingReadiness",
         NATIVE_BACKEND_HPP, "R254 programmable live IA index-binding readiness type"),
        ("indexed_live_index_binding_readiness(",
         NATIVE_BACKEND_HPP, "R254 live IA index-binding readiness declaration"),
        ("validate_indexed_live_index_binding_snapshot(",
         NATIVE_BACKEND_HPP, "R254 live IA snapshot validator"),
        ("expectedContext->IAGetIndexBuffer(",
         NATIVE_BACKEND_CPP, "R254 fresh live IA index-buffer reobservation"),
        ("out.liveIndexBufferMatches =",
         NATIVE_BACKEND_CPP, "R254 exact live index-buffer identity"),
        ("out.liveIndexFormatMatches =",
         NATIVE_BACKEND_CPP, "R254 exact live index-format identity"),
        ("out.liveIndexOffsetMatches =",
         NATIVE_BACKEND_CPP, "R254 exact live index-offset identity"),
        ("R254 seals fresh live IA index buffer format and offset after R253",
         CONSTANT_BUFFER_PROBE, "R254 positive fresh IA receipt regression"),
        ("R254 rejects live IA index-buffer identity drift",
         CONSTANT_BUFFER_PROBE, "R254 live index-buffer drift regression"),
        ("R254 rejects live IA index-format drift",
         CONSTANT_BUFFER_PROBE, "R254 live index-format drift regression"),
        ("R254 rejects live IA index-offset drift",
         CONSTANT_BUFFER_PROBE, "R254 live index-offset drift regression"),
    ]
    missing_r254_programmable_live_index_binding = [
        meaning for token, source, meaning
        in r254_programmable_live_index_binding_contract
        if token not in source
    ]
    if missing_r254_programmable_live_index_binding:
        raise SystemExit(
            "DX11 R254 programmable live index-binding drift: "
            + ", ".join(missing_r254_programmable_live_index_binding)
        )

    r255_programmable_indexed_pre_draw_contract = [
        ("struct NativeProgrammableShaderIndexedPreDrawReadiness",
         NATIVE_BACKEND_HPP, "R255 programmable indexed pre-Draw readiness type"),
        ("indexed_pre_draw_readiness(",
         NATIVE_BACKEND_HPP, "R255 final indexed pre-Draw readiness declaration"),
        ("validate_indexed_pre_draw_snapshot(",
         NATIVE_BACKEND_HPP, "R255 final indexed pre-Draw snapshot validator"),
        ("out.dispatchSourceLineageMatches =",
         NATIVE_BACKEND_CPP, "R255 R252-to-R253 lineage seal"),
        ("out.baseVertexIndex = dispatch.baseVertexLocation",
         NATIVE_BACKEND_CPP, "R297 R255 retains indexed base vertex"),
        ("out.minVertexIndex = dispatch.minVertexIndex",
         NATIVE_BACKEND_CPP, "R297 R255 retains indexed min vertex"),
        ("out.numVertices = dispatch.numVertices",
         NATIVE_BACKEND_CPP, "R297 R255 retains indexed vertex range count"),
        ("out.sourceLiveLineageMatches =",
         NATIVE_BACKEND_CPP, "R255 R253-to-R254 live IA lineage seal"),
        ("token, 0x255u",
         NATIVE_BACKEND_CPP, "R255 independent snapshot-domain tag"),
        ("R255 joins current R252 R253 and R254 receipts into final indexed pre-Draw proof",
         CONSTANT_BUFFER_PROBE, "R255 positive final pre-Draw regression"),
        ("R255 rejects stale R252 dispatch receipt",
         CONSTANT_BUFFER_PROBE, "R255 stale dispatch regression"),
        ("R255 rejects stale R253 source-value receipt",
         CONSTANT_BUFFER_PROBE, "R255 stale source-value regression"),
        ("R255 rejects stale R254 live IA receipt",
         CONSTANT_BUFFER_PROBE, "R255 stale live-IA regression"),
    ]
    missing_r255_programmable_indexed_pre_draw = [
        meaning for token, source, meaning
        in r255_programmable_indexed_pre_draw_contract
        if token not in source
    ]
    if missing_r255_programmable_indexed_pre_draw:
        raise SystemExit(
            "DX11 R255 programmable indexed pre-Draw drift: "
            + ", ".join(missing_r255_programmable_indexed_pre_draw)
        )

    r256_programmable_draw_candidate_union_contract = [
        ("enum class NativeProgrammableShaderDrawCandidateKind",
         NATIVE_BACKEND_HPP, "R256 branch-tagged draw-candidate kind"),
        ("struct NativeProgrammableShaderDrawCandidateReadiness",
         NATIVE_BACKEND_HPP, "R256 common dormant draw-candidate receipt"),
        ("compose_programmable_draw_candidate_readiness(",
         NATIVE_BACKEND_HPP, "R256 draw-candidate composition declarations"),
        ("validate_programmable_draw_candidate_snapshot(",
         NATIVE_BACKEND_HPP, "R256 draw-candidate snapshot validators"),
        ("NativeProgrammableShaderDrawCandidateKind::NonIndexed",
         NATIVE_BACKEND_CPP, "R256 non-indexed branch identity"),
        ("NativeProgrammableShaderDrawCandidateKind::Indexed",
         NATIVE_BACKEND_CPP, "R256 indexed branch identity"),
        ("out.selectedReceiptSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R256 selected receipt snapshot gate"),
        ("out.baseVertexIndex = preDraw.baseVertexIndex",
         NATIVE_BACKEND_CPP, "R297 R256 carries indexed base vertex"),
        ("out.minVertexIndex = preDraw.minVertexIndex",
         NATIVE_BACKEND_CPP, "R297 R256 carries indexed min vertex"),
        ("out.numVertices = preDraw.numVertices",
         NATIVE_BACKEND_CPP, "R297 R256 carries indexed vertex range count"),
        ("token, 0x256u",
         NATIVE_BACKEND_CPP, "R256 independent snapshot-domain tag"),
        ("R256 indexed draw-candidate union accepts current R255 receipt",
         CONSTANT_BUFFER_PROBE, "R256 indexed positive regression"),
        ("R256 indexed draw-candidate union rejects stale R255 receipt",
         CONSTANT_BUFFER_PROBE, "R256 indexed stale receipt regression"),
        ("R256 non-indexed draw-candidate union accepts current R251 receipt",
         CONSTANT_BUFFER_PROBE, "R256 non-indexed positive regression"),
        ("R256 non-indexed draw-candidate union rejects stale R251 receipt",
         CONSTANT_BUFFER_PROBE, "R256 non-indexed stale receipt regression"),
    ]
    missing_r256_programmable_draw_candidate_union = [
        meaning for token, source, meaning
        in r256_programmable_draw_candidate_union_contract
        if token not in source
    ]
    if missing_r256_programmable_draw_candidate_union:
        raise SystemExit(
            "DX11 R256 programmable draw-candidate union drift: "
            + ", ".join(missing_r256_programmable_draw_candidate_union)
        )

    r257_programmable_dormant_pre_activation_contract = [
        ("struct NativeProgrammableShaderDormantPreActivationReadiness",
         NATIVE_BACKEND_HPP, "R257 dormant pre-activation receipt type"),
        ("compose_programmable_dormant_pre_activation_readiness(",
         NATIVE_BACKEND_HPP, "R257 dormant receipt composition declaration"),
        ("validate_programmable_dormant_pre_activation_snapshot(",
         NATIVE_BACKEND_HPP, "R257 dormant receipt snapshot validator"),
        ("out.candidatePayloadSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R257 R256 payload self-integrity gate"),
        ("out.diagnosticOnly = true;",
         NATIVE_BACKEND_CPP, "R257 F23 diagnostic-only boundary"),
        ("out.activationProofPresent = false;",
         NATIVE_BACKEND_CPP, "R257 cannot manufacture activation proof"),
        ("out.nativeDrawPathActivationAllowed = false;",
         NATIVE_BACKEND_CPP, "R257 cannot authorize NativeDrawPath"),
        ("out.drawDispatchAuthorized = false;",
         NATIVE_BACKEND_CPP, "R257 cannot authorize Draw dispatch"),
        ("token, 0x257u",
         NATIVE_BACKEND_CPP, "R257 independent snapshot-domain tag"),
        ("R257 indexed candidate seals dormant pre-activation review without draw authorization",
         CONSTANT_BUFFER_PROBE, "R257 indexed positive dormant review regression"),
        ("R257 rejects stale R256 indexed candidate token",
         CONSTANT_BUFFER_PROBE, "R257 stale candidate regression"),
        ("R257 rejects indexed source-range drift hidden behind an unchanged R256 snapshot token",
         CONSTANT_BUFFER_PROBE, "R257/R297 indexed range payload-tamper regression"),
        ("R257 non-indexed candidate seals dormant pre-activation review without draw authorization",
         CONSTANT_BUFFER_PROBE, "R257 non-indexed positive dormant review regression"),
        ("R298 rejects non-indexed source-start drift hidden behind an unchanged R256 snapshot token",
         CONSTANT_BUFFER_PROBE, "R298 non-indexed payload-tamper regression"),
        ("R257 rejects non-indexed R256 branch-tag mismatch",
         CONSTANT_BUFFER_PROBE, "R257 branch-tag mismatch regression"),
    ]
    missing_r257_programmable_dormant_pre_activation = [
        meaning for token, source, meaning
        in r257_programmable_dormant_pre_activation_contract
        if token not in source
    ]
    if missing_r257_programmable_dormant_pre_activation:
        raise SystemExit(
            "DX11 R257 programmable dormant pre-activation drift: "
            + ", ".join(missing_r257_programmable_dormant_pre_activation)
        )

    r258_programmable_source_revalidation_contract = [
        ("struct NativeProgrammableShaderDormantSourceRevalidationReadiness",
         NATIVE_BACKEND_HPP, "R258 current-source revalidation receipt type"),
        ("nonindexed_dormant_source_revalidation_readiness(",
         NATIVE_BACKEND_HPP, "R258 non-indexed current-source declaration"),
        ("indexed_dormant_source_revalidation_readiness(",
         NATIVE_BACKEND_HPP, "R258 indexed current-source declaration"),
        ("compose_programmable_dormant_source_revalidation_readiness(",
         NATIVE_BACKEND_CPP, "R258 common fail-closed composition"),
        ("out.baseVertexIndex = candidate.baseVertexIndex",
         NATIVE_BACKEND_CPP, "R297 R258 preserves current indexed base vertex"),
        ("out.minVertexIndex = candidate.minVertexIndex",
         NATIVE_BACKEND_CPP, "R297 R258 preserves current indexed min vertex"),
        ("out.numVertices = candidate.numVertices",
         NATIVE_BACKEND_CPP, "R297 R258 preserves current indexed vertex count"),
        ("token, 0x258u",
         NATIVE_BACKEND_CPP, "R258 independent snapshot-domain tag"),
        ("R258 indexed final dormant handoff revalidates current R255 source state",
         CONSTANT_BUFFER_PROBE, "R258 indexed current-source positive regression"),
        ("R258 indexed final dormant handoff rejects current source-state drift",
         CONSTANT_BUFFER_PROBE, "R258 indexed source drift rejection"),
        ("R258 non-indexed final dormant handoff revalidates current R251 source state",
         CONSTANT_BUFFER_PROBE, "R258 non-indexed current-source positive regression"),
        ("R258 non-indexed final dormant handoff rejects fresh source identity drift",
         CONSTANT_BUFFER_PROBE, "R258 non-indexed source drift rejection"),
    ]
    missing_r258_programmable_source_revalidation = [
        meaning for token, source, meaning
        in r258_programmable_source_revalidation_contract
        if token not in source
    ]
    if missing_r258_programmable_source_revalidation:
        raise SystemExit(
            "DX11 R258 programmable source revalidation drift: "
            + ", ".join(missing_r258_programmable_source_revalidation)
        )

    r260_programmable_resource_behavior_contract = [
        ("struct NativeProgrammableShaderResourceBehaviorReadiness",
         NATIVE_BACKEND_HPP, "R260 explicit F18 geometry resource-behavior receipt"),
        ("compose_programmable_resource_behavior_readiness(",
         NATIVE_BACKEND_HPP, "R260 resource-behavior composition declaration"),
        ("validate_programmable_resource_behavior_readiness_snapshot(",
         NATIVE_BACKEND_HPP, "R260 resource-behavior snapshot validator"),
        ("sourceRevalidationPayloadSnapshotMatches",
         NATIVE_BACKEND_HPP, "R300 R260 exposes R258 payload-integrity result"),
        ("out.sourceRevalidationPayloadSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R300 R260 recomputes R258 payload identity"),
        ("vertexMirror.validate_mirror_readiness_snapshot(",
         NATIVE_BACKEND_CPP, "R260 current vertex mirror identity validation"),
        ("indexMirror->validate_mirror_readiness_snapshot(",
         NATIVE_BACKEND_CPP, "R260 current index mirror identity validation"),
        ("out.textureResourceBehaviorProofPresent = false;",
         NATIVE_BACKEND_CPP, "R260 texture behavior scope remains fail-closed"),
        ("out.outputResourceBehaviorProofPresent = false;",
         NATIVE_BACKEND_CPP, "R260 output behavior scope remains fail-closed"),
        ("token, 0x260u",
         NATIVE_BACKEND_CPP, "R260 independent review snapshot-domain tag"),
        ("R260 indexed geometry resource behavior is exact while texture/output F18 scopes remain fail-closed",
         CONSTANT_BUFFER_PROBE, "R260 indexed positive/debt regression"),
        ("R300 rejects R258 payload drift before minting R260 geometry resource proof",
         CONSTANT_BUFFER_PROBE, "R300 R258-to-R260 payload tamper regression"),
        ("R260 indexed resource behavior rejects stale vertex mirror identity",
         CONSTANT_BUFFER_PROBE, "R260 stale vertex mirror regression"),
        ("R260 non-indexed geometry resource behavior is exact without inventing index coverage",
         CONSTANT_BUFFER_PROBE, "R260 non-indexed positive/debt regression"),
    ]
    missing_r260_programmable_resource_behavior = [
        meaning for token, source, meaning
        in r260_programmable_resource_behavior_contract
        if token not in source
    ]
    if missing_r260_programmable_resource_behavior:
        raise SystemExit(
            "DX11 R260 programmable resource-behavior drift: "
            + ", ".join(missing_r260_programmable_resource_behavior)
        )

    r261_programmable_texture_resource_behavior_contract = [
        ("struct NativeProgrammableShaderTextureResourceBehaviorReadiness",
         NATIVE_BACKEND_HPP, "R261 explicit F18 texture resource-behavior receipt"),
        ("compose_programmable_texture_resource_behavior_readiness(",
         NATIVE_BACKEND_HPP, "R261 texture resource-behavior composition declaration"),
        ("validate_programmable_texture_resource_behavior_readiness_snapshot(",
         NATIVE_BACKEND_HPP, "R261 texture resource-behavior snapshot validator"),
        ("geometryPayloadSnapshotMatches",
         NATIVE_BACKEND_HPP, "R301 R261 exposes R260 payload-integrity result"),
        ("recompute_programmable_resource_behavior_payload_snapshot(",
         NATIVE_BACKEND_CPP, "R301 reconstructs the exact R260 review payload identity"),
        ("out.geometryPayloadSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R301 R261 requires R260 payload self-integrity"),
        ("textureRegistry.validate_mirror_readiness_snapshot_for_stages(",
         NATIVE_BACKEND_CPP, "R261 current managed texture-stage identity validation"),
        ("out.textureResourceBehaviorExact =",
         NATIVE_BACKEND_CPP, "R261 exact supplied texture-stage resource behavior"),
        ("out.outputResourceBehaviorProofPresent = false;",
         NATIVE_BACKEND_CPP, "R261 output resource scope remains fail-closed"),
        ("token, 0x261u",
         NATIVE_BACKEND_CPP, "R261 independent review snapshot-domain tag"),
        ("R261 indexed texture resource behavior closes supplied texture scope while output F18 remains fail-closed",
         CONSTANT_BUFFER_PROBE, "R261 indexed positive/output-debt regression"),
        ("R301 rejects R260 payload drift before minting R261 texture resource proof",
         CONSTANT_BUFFER_PROBE, "R301 R260-to-R261 payload tamper regression"),
        ("R261 rejects stale managed texture-stage identity",
         CONSTANT_BUFFER_PROBE, "R261 stale texture-stage receipt regression"),
        ("R261 rejects stale R260 geometry resource-behavior identity",
         CONSTANT_BUFFER_PROBE, "R261 stale geometry receipt regression"),
        ("R261 non-indexed texture resource behavior reuses exact current texture stage without widening F18",
         CONSTANT_BUFFER_PROBE, "R261 non-indexed positive/output-debt regression"),
    ]
    missing_r261_programmable_texture_resource_behavior = [
        meaning for token, source, meaning
        in r261_programmable_texture_resource_behavior_contract
        if token not in source
    ]
    if missing_r261_programmable_texture_resource_behavior:
        raise SystemExit(
            "DX11 R261 programmable texture resource-behavior drift: "
            + ", ".join(missing_r261_programmable_texture_resource_behavior)
        )

    r262_programmable_output_resource_behavior_contract = [
        ("struct NativeProgrammableShaderOutputResourceBehaviorReadiness",
         NATIVE_BACKEND_HPP, "R262 explicit F18 output resource-behavior receipt"),
        ("compose_programmable_output_resource_behavior_readiness(",
         NATIVE_BACKEND_HPP, "R262 output resource-behavior composition declaration"),
        ("validate_programmable_output_resource_behavior_readiness_snapshot(",
         NATIVE_BACKEND_HPP, "R262 output resource-behavior snapshot validator"),
        ("texturePayloadSnapshotMatches",
         NATIVE_BACKEND_HPP, "R302 R262 exposes R261 payload-integrity result"),
        ("recompute_programmable_texture_resource_behavior_payload_snapshot(",
         NATIVE_BACKEND_CPP, "R302 reconstructs the exact R261 review payload identity"),
        ("out.texturePayloadSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R302 R262 requires R261 payload self-integrity"),
        ("surfaceBinding.binding_readiness(",
         NATIVE_BACKEND_CPP, "R262 live RTV/DSV binding observation"),
        ("surfaceBinding.validate_binding_snapshot(",
         NATIVE_BACKEND_CPP, "R262 current output binding identity validation"),
        ("out.outputResourceBehaviorExact =",
         NATIVE_BACKEND_CPP, "R262 exact output resource behavior"),
        ("out.fullResourceBehaviorProofPresent =",
         NATIVE_BACKEND_CPP, "R262 full F18 coverage result"),
        ("token, 0x262u",
         NATIVE_BACKEND_CPP, "R262 independent review snapshot-domain tag"),
        ("R262 indexed output resource behavior closes full F18 without activation authority",
         CONSTANT_BUFFER_PROBE, "R262 indexed positive F18 regression"),
        ("R302 rejects R261 payload drift before minting R262 full resource proof",
         CONSTANT_BUFFER_PROBE, "R302 R261-to-R262 payload tamper regression"),
        ("R262 rejects stale live output-binding identity",
         CONSTANT_BUFFER_PROBE, "R262 stale output binding regression"),
        ("R262 non-indexed output resource behavior closes full F18 on the same current output pair",
         CONSTANT_BUFFER_PROBE, "R262 non-indexed positive F18 regression"),
    ]
    missing_r262_programmable_output_resource_behavior = [
        meaning for token, source, meaning
        in r262_programmable_output_resource_behavior_contract
        if token not in source
    ]
    if missing_r262_programmable_output_resource_behavior:
        raise SystemExit(
            "DX11 R262 programmable output resource-behavior drift: "
            + ", ".join(missing_r262_programmable_output_resource_behavior)
        )

    r276_programmable_semantic_translation_plan_contract = [
        ("struct NativeProgrammableShaderSemanticTranslationPlanEvidence",
         NATIVE_BACKEND_HPP, "R276 source-derived semantic translation plan type"),
        ("derive_programmable_shader_semantic_translation_plan(",
         NATIVE_BACKEND_HPP, "R276 plan producer declaration"),
        ("validate_programmable_shader_semantic_translation_plan_snapshot(",
         NATIVE_BACKEND_HPP, "R276 plan snapshot validator declaration"),
        ("out.provenanceMatches =",
         NATIVE_BACKEND_CPP, "R276 R271/R268/R273 provenance convergence"),
        ("R276_D3D9_SOURCE_DERIVED_SEMANTIC_TRANSLATION_PLAN_V1",
         NATIVE_BACKEND_CPP, "R276 deterministic translator revision"),
        ("R276_R271_R268_R273_TARGET_SEMANTIC_IDENTITY_V1",
         NATIVE_BACKEND_CPP, "R276 deterministic semantic contract"),
        ("token, 0x276u",
         NATIVE_BACKEND_CPP, "R276 independent snapshot-domain tag"),
        ("R276 derives target semantic identities from R271 R268 R273 provenance",
         CONSTANT_BUFFER_PROBE, "R276 positive source-derived translation-plan regression"),
        ("R276 rejects stale R273 mapping snapshot before target semantic derivation",
         CONSTANT_BUFFER_PROBE, "R276 stale R273 fail-closed regression"),
        ("sig.shaderTranslationExact = false;",
         RUNTIME_CENSUS, "R276 keeps programmable production translation fail closed"),
    ]
    missing_r276_programmable_semantic_translation_plan = [
        meaning for token, source, meaning
        in r276_programmable_semantic_translation_plan_contract
        if token not in source
    ]
    if missing_r276_programmable_semantic_translation_plan:
        raise SystemExit(
            "DX11 R276 semantic translation plan drift: "
            + ", ".join(missing_r276_programmable_semantic_translation_plan)
        )

    r275_translated_semantic_receipt_contract = [
        ("struct NativeProgrammableShaderTranslatedSemanticReceipt",
         NATIVE_BACKEND_HPP, "R275 translated-semantic receipt type"),
        ("compose_programmable_shader_translated_semantic_receipt(",
         NATIVE_BACKEND_HPP, "R275 receipt composer declaration"),
        ("const NativeProgrammableShaderSemanticTranslationPlanEvidence& translationPlan",
         NATIVE_BACKEND_HPP, "R275 typed R276 plan consumption"),
        ("validate_programmable_shader_translated_semantic_receipt_snapshot(",
         NATIVE_BACKEND_HPP, "R275 receipt snapshot validator declaration"),
        ("out.sourceMappingHandoffSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R275 exact R273 receipt binding"),
        ("out.translationPlanReady =",
         NATIVE_BACKEND_CPP, "R275 validates R276 plan readiness"),
        ("out.translationPlanSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R275 binds exact R276 plan snapshot"),
        ("out.cacheIdentityMatches =",
         NATIVE_BACKEND_CPP, "R275 R239/R242/R273/R276 identity convergence"),
        ("token, 0x275276u",
         NATIVE_BACKEND_CPP, "R275/R276 receipt snapshot-domain tag"),
        ("R275 seals R276 source-derived semantic translation plan",
         CONSTANT_BUFFER_PROBE, "R275 positive typed-plan regression"),
        ("R275 rejects stale R276 semantic translation plan snapshot",
         CONSTANT_BUFFER_PROBE, "R275 stale R276 plan fail-closed regression"),
    ]
    missing_r275_translated_semantic_receipt = [
        meaning for token, source, meaning
        in r275_translated_semantic_receipt_contract
        if token not in source
    ]
    if missing_r275_translated_semantic_receipt:
        raise SystemExit(
            "DX11 R275 translated semantic receipt drift: "
            + ", ".join(missing_r275_translated_semantic_receipt)
        )
    stale_r275_loose_semantic_plan_signature = (
        "std::uint64_t translatedVertexSemanticHash,\n"
        "    std::uint64_t translatedPixelSemanticHash,\n"
        "    std::uint64_t translatorRevisionHash"
    )
    if stale_r275_loose_semantic_plan_signature in NATIVE_BACKEND_HPP:
        raise SystemExit(
            "DX11 R276 stale probe-supplied semantic scalars remain in R275 API"
        )

    r263_programmable_shader_semantic_translation_contract = [
        ("struct NativeProgrammableShaderSemanticTranslationReadiness",
         NATIVE_BACKEND_HPP, "R263 exact F21 semantic-translation readiness type"),
        ("compose_programmable_shader_semantic_translation_readiness(",
         NATIVE_BACKEND_HPP, "R263 semantic-translation composition declaration"),
        ("validate_programmable_shader_semantic_translation_readiness_snapshot(",
         NATIVE_BACKEND_HPP, "R263 semantic-translation snapshot validator"),
        ("const NativeProgrammableShaderTranslatedSemanticReceipt&",
         NATIVE_BACKEND_HPP, "R263 consumes R275 typed receipt"),
        ("out.translatedSemanticReceiptReady =",
         NATIVE_BACKEND_CPP, "R263 validates R275 receipt integrity"),
        ("out.translatedSemanticReceiptSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R263 binds exact R275 snapshot"),
        ("out.translatedSemanticIdentityMatches =",
         NATIVE_BACKEND_CPP, "R263 binds R275 receipt to current pair/object"),
        ("out.sourceMappingIdentityMatches =",
         NATIVE_BACKEND_CPP, "R263 retains R273 provenance through R275"),
        ("out.vertexSemanticExact =",
         NATIVE_BACKEND_CPP, "R263 vertex semantic exactness comes from R275"),
        ("out.pixelSemanticExact =",
         NATIVE_BACKEND_CPP, "R263 pixel semantic exactness comes from R275"),
        ("out.constantRegisterMappingExact =",
         NATIVE_BACKEND_CPP, "R263 constant mapping proof comes through R275"),
        ("out.samplerMappingExact =",
         NATIVE_BACKEND_CPP, "R263 sampler mapping proof comes through R275"),
        ("out.interfaceSourceIdentityMatches =",
         NATIVE_BACKEND_CPP, "R269 source/linkage identity match gate"),
        ("out.interfaceLinkExact =",
         NATIVE_BACKEND_CPP, "R263 stage-interface semantic exactness gate"),
        ("out.semanticProofPresent =",
         NATIVE_BACKEND_CPP, "R263 complete F21 semantic proof gate"),
        ("token, 0x263275u",
         NATIVE_BACKEND_CPP, "R263/R275 combined semantic review snapshot-domain tag"),
        ("R275 R263 consumes snapshot-sealed translated semantic receipt",
         CONSTANT_BUFFER_PROBE, "R263 consumes R275 positive regression"),
        ("R263 rejects stale R275 translated semantic receipt",
         CONSTANT_BUFFER_PROBE, "R263 stale R275 fail-closed regression"),
        ("R269 rejects R268 linkage provenance that does not match R263 source pair identity",
         CONSTANT_BUFFER_PROBE, "R269 source-linked interface fail-closed regression"),
        ("R263 rejects incomplete programmable constant-register semantic proof",
         CONSTANT_BUFFER_PROBE, "R263 incomplete constant-register fail-closed regression"),
        ("R263 rejects incomplete programmable sampler semantic proof",
         CONSTANT_BUFFER_PROBE, "R263 incomplete sampler fail-closed regression"),
    ]
    missing_r263_programmable_shader_semantic_translation = [
        meaning for token, source, meaning
        in r263_programmable_shader_semantic_translation_contract
        if token not in source
    ]
    if missing_r263_programmable_shader_semantic_translation:
        raise SystemExit(
            "DX11 R263 programmable shader semantic-translation drift: "
            + ", ".join(missing_r263_programmable_shader_semantic_translation)
        )
    stale_r263_loose_semantic_signature = (
        "std::uint64_t translatedVertexSemanticHash,\n"
        "    std::uint64_t translatedPixelSemanticHash,\n"
        "    const ProgrammableShaderInterfaceLinkageEvidence& sourceInterfaceLinkage"
    )
    if stale_r263_loose_semantic_signature in NATIVE_BACKEND_HPP:
        raise SystemExit(
            "DX11 R275 stale loose semantic scalars remain in R263 API"
        )

    r264_programmable_shader_source_evidence_contract = [
        ("struct ProgrammableShaderFunctionSourceEvidence",
         PIPELINE_TRANSLATION_HPP, "R264 retained programmable source-evidence type"),
        ("capture_programmable_shader_function_source_evidence(",
         PIPELINE_TRANSLATION_HPP, "R264 source-evidence capture declaration"),
        ("validate_programmable_shader_function_source_evidence(",
         PIPELINE_TRANSLATION_HPP, "R264 source-evidence identity validator declaration"),
        ("out.tokens.resize(",
         PIPELINE_TRANSLATION_CPP, "R264 bounded D3D9 shader token retention"),
        ("out.versionSupported =",
         PIPELINE_TRANSLATION_CPP, "R264 stage/version fail-closed gate"),
        ("identity.bytecodeHash == evidence.bytecodeHash",
         PIPELINE_TRANSLATION_CPP, "R264 exact R239 hash binding"),
        ("sourceEvidenceExact",
         RUNTIME_CENSUS, "R264 production census consumes exact source evidence"),
        ("capture_programmable_shader_function_source_evidence(",
         RUNTIME_CENSUS, "R264 D3D9 GetFunction bytes route through evidence producer"),
        ("R264 captures exact programmable shader source bytecode evidence",
         CONSTANT_BUFFER_PROBE, "R264 exact source-evidence positive regression"),
        ("R264 rejects source identity drift, wrong-stage bytecode, and misaligned payloads",
         CONSTANT_BUFFER_PROBE, "R264 fail-closed source-evidence regression"),
    ]
    missing_r264_programmable_shader_source_evidence = [
        meaning for token, source, meaning
        in r264_programmable_shader_source_evidence_contract
        if token not in source
    ]
    if missing_r264_programmable_shader_source_evidence:
        raise SystemExit(
            "DX11 R264 programmable shader source-evidence drift: "
            + ", ".join(missing_r264_programmable_shader_source_evidence)
        )

    r265_programmable_shader_instruction_decoder_contract = [
        ("struct ProgrammableShaderInstructionDecode",
         PIPELINE_TRANSLATION_HPP, "R265 decoded instruction-stream evidence type"),
        ("decode_programmable_shader_instruction_stream(",
         PIPELINE_TRANSLATION_HPP, "R265 instruction decoder declaration"),
        ("R265_D3D9_SM2_SM3_INSTRUCTION_OPERAND_DECODER_V1",
         PIPELINE_TRANSLATION_CPP, "R265 decoder revision provenance"),
        ("R265_RAW_OPCODE_OPERANDS_NO_REGISTER_SAMPLER_LINKAGE_SEMANTICS_V1",
         PIPELINE_TRANSLATION_CPP, "R265 bounded semantic-contract provenance"),
        ("opcode == static_cast<DWORD>(D3DSIO_COMMENT)",
         PIPELINE_TRANSLATION_CPP, "R265 COMMENT boundary handling"),
        ("opcode == static_cast<DWORD>(D3DSIO_END)",
         PIPELINE_TRANSLATION_CPP, "R265 exact END boundary"),
        ("opcode > static_cast<DWORD>(D3DSIO_BREAKP)",
         PIPELINE_TRANSLATION_CPP, "R265 unknown opcode fail-closed gate"),
        ("instructionDecodeExact",
         RUNTIME_CENSUS, "R265 production census records decoder exactness"),
        ("decode_programmable_shader_instruction_stream(evidence)",
         RUNTIME_CENSUS, "R265 production GetFunction evidence feeds decoder"),
        ("decodedStreamHash",
         RUNTIME_CENSUS, "R265 source-derived stream provenance retained"),
        ("R265 decodes exact SM3 instruction and raw operand provenance",
         CONSTANT_BUFFER_PROBE, "R265 positive structural decoder regression"),
        ("R265 fails closed on truncated, unknown-opcode, and SM1 streams",
         CONSTANT_BUFFER_PROBE, "R265 malformed/unsupported fail-closed regression"),
    ]
    missing_r265_programmable_shader_instruction_decoder = [
        meaning for token, source, meaning
        in r265_programmable_shader_instruction_decoder_contract
        if token not in source
    ]
    if missing_r265_programmable_shader_instruction_decoder:
        raise SystemExit(
            "DX11 R265 programmable shader instruction-decoder drift: "
            + ", ".join(missing_r265_programmable_shader_instruction_decoder)
        )

    r266_programmable_shader_register_semantics_contract = [
        ("struct ProgrammableShaderRegisterSemantics",
         PIPELINE_TRANSLATION_HPP, "R266 register/constant/sampler evidence type"),
        ("decode_programmable_shader_register_semantics(",
         PIPELINE_TRANSLATION_HPP, "R266 register-semantics decoder declaration"),
        ("R266_D3D9_SM2_SM3_REGISTER_SEMANTICS_DECODER_V1",
         PIPELINE_TRANSLATION_CPP, "R266 register decoder revision provenance"),
        ("R266_OPCODE_ROLE_REGISTER_MODIFIER_ADDRESS_CONSTANT_SAMPLER_PROVENANCE_V1",
         PIPELINE_TRANSLATION_CPP, "R266 register decoder contract provenance"),
        ("registerSemanticsExact",
         RUNTIME_CENSUS, "R266 production census records semantic exactness"),
        ("decode_programmable_shader_register_semantics(decode)",
         RUNTIME_CENSUS, "R266 production R265 evidence feeds register semantics"),
        ("registerSemanticsHash",
         RUNTIME_CENSUS, "R266 production source identity retains semantic hash"),
        ("R266 decodes destination/source register semantics, relative addressing, and normalized constant provenance",
         CONSTANT_BUFFER_PROBE, "R266 constant-bank and relative-address regression"),
        ("R266 derives exact TEX sampler provenance",
         CONSTANT_BUFFER_PROBE, "R266 sampler provenance regression"),
        ("R266 preserves R265 structure but fails closed on model-dependent register-role layouts",
         CONSTANT_BUFFER_PROBE, "R266 unsupported-layout fail-closed regression"),
    ]
    missing_r266_programmable_shader_register_semantics = [
        meaning for token, source, meaning
        in r266_programmable_shader_register_semantics_contract
        if token not in source
    ]
    if missing_r266_programmable_shader_register_semantics:
        raise SystemExit(
            "DX11 R266 programmable shader register-semantics drift: "
            + ", ".join(
                missing_r266_programmable_shader_register_semantics)
        )

    r267_programmable_shader_interface_semantics_contract = [
        ("struct ProgrammableShaderInterfaceSemantics",
         PIPELINE_TRANSLATION_HPP, "R267 interface semantic evidence type"),
        ("decode_programmable_shader_interface_semantics(",
         PIPELINE_TRANSLATION_HPP, "R267 interface semantic decoder declaration"),
        ("R267_D3D9_SM3_INTERFACE_DECLARATION_SEMANTICS_V1",
         PIPELINE_TRANSLATION_CPP, "R267 interface decoder revision provenance"),
        ("R267_EXPLICIT_DCL_USAGE_INDEX_REGISTER_WRITEMASK_PROVENANCE_V1",
         PIPELINE_TRANSLATION_CPP, "R267 interface semantic contract provenance"),
        ("interfaceSemanticsExact",
         RUNTIME_CENSUS, "R267 production census records interface exactness"),
        ("decode_programmable_shader_interface_semantics(",
         RUNTIME_CENSUS, "R267 production census consumes exact R265/R266 evidence"),
        ("interfaceSemanticsHash",
         RUNTIME_CENSUS, "R267 production identity retains interface hash"),
        ("R267 decodes exact SM3 DCL input/output interface semantics",
         CONSTANT_BUFFER_PROBE, "R267 positive SM3 DCL interface regression"),
        ("R267 rejects DCL info tokens without parameter marker bit",
         CONSTANT_BUFFER_PROBE, "R267 DCL token-marker fail-closed regression"),
        ("R267 rejects SM2 DCL interface semantics",
         CONSTANT_BUFFER_PROBE, "R267 SM2 fail-closed regression"),
        ("R267 rejects duplicate SM3 interface semantic declarations",
         CONSTANT_BUFFER_PROBE, "R267 duplicate-semantic fail-closed regression"),
        ("R267 rejects overlapping SM3 interface declaration masks",
         CONSTANT_BUFFER_PROBE, "R267 overlapping-mask fail-closed regression"),
    ]
    missing_r267_programmable_shader_interface_semantics = [
        meaning for token, source, meaning
        in r267_programmable_shader_interface_semantics_contract
        if token not in source
    ]
    if missing_r267_programmable_shader_interface_semantics:
        raise SystemExit(
            "DX11 R267 programmable shader interface-semantics drift: "
            + ", ".join(
                missing_r267_programmable_shader_interface_semantics)
        )

    r268_programmable_shader_stage_linkage_contract = [
        ("struct ProgrammableShaderInterfaceLinkageEvidence",
         PIPELINE_TRANSLATION_HPP, "R268 stage-linkage evidence type"),
        ("derive_programmable_shader_interface_linkage_evidence(",
         PIPELINE_TRANSLATION_HPP, "R268 stage-linkage derivation declaration"),
        ("R268_D3D9_SM3_STAGE_INTERFACE_LINKAGE_V1",
         PIPELINE_TRANSLATION_CPP, "R268 linker revision provenance"),
        ("R268_USAGE_INDEX_COMPONENT_COVERAGE_LINKAGE_V1",
         PIPELINE_TRANSLATION_CPP, "R268 linkage semantic-contract provenance"),
        ("matchedSemanticCount == pixelInputSemanticCount",
         PIPELINE_TRANSLATION_HPP, "R268 exactness requires every PS input matched"),
        ("(match->writeMask & pixelInput.writeMask) !=",
         PIPELINE_TRANSLATION_CPP, "R268 component coverage fail-closed gate"),
        ("R268 derives exact VS-output to PS-input stage linkage",
         CONSTANT_BUFFER_PROBE, "R268 positive linkage regression"),
        ("R268 rejects unmatched pixel input semantics",
         CONSTANT_BUFFER_PROBE, "R268 semantic mismatch regression"),
        ("R268 rejects insufficient vertex output component coverage",
         CONSTANT_BUFFER_PROBE, "R268 component-mask fail-closed regression"),
        ("R268 rejects reversed VS and PS interface receipts",
         CONSTANT_BUFFER_PROBE, "R268 stage inversion fail-closed regression"),
    ]
    missing_r268_programmable_shader_stage_linkage = [
        meaning for token, source, meaning
        in r268_programmable_shader_stage_linkage_contract
        if token not in source
    ]
    if missing_r268_programmable_shader_stage_linkage:
        raise SystemExit(
            "DX11 R268 programmable shader stage-linkage drift: "
            + ", ".join(
                missing_r268_programmable_shader_stage_linkage)
        )

    r269_programmable_linkage_provenance_handoff_contract = [
        ("std::uint64_t sourceBytecodeHash = 0;",
         PIPELINE_TRANSLATION_HPP, "R269 R267 source bytecode provenance"),
        ("std::uint64_t vertexSourceBytecodeHash = 0;",
         PIPELINE_TRANSLATION_HPP, "R269 R268 vertex source identity"),
        ("std::uint64_t pixelSourceBytecodeHash = 0;",
         PIPELINE_TRANSLATION_HPP, "R269 R268 pixel source identity"),
        ("out.vertexSourceBytecodeHash = vertexSemantics.sourceBytecodeHash;",
         PIPELINE_TRANSLATION_CPP, "R269 linkage carries VS source identity"),
        ("out.pixelSourceBytecodeHash = pixelSemantics.sourceBytecodeHash;",
         PIPELINE_TRANSLATION_CPP, "R269 linkage carries PS source identity"),
        ("const ProgrammableShaderInterfaceLinkageEvidence& sourceInterfaceLinkage",
         NATIVE_BACKEND_HPP, "R269 R263 consumes exact R268 receipt"),
        ("sourceInterfaceLinkage.vertexSourceBytecodeHash ==",
         NATIVE_BACKEND_CPP, "R269 R263 matches VS source identity"),
        ("sourceInterfaceLinkage.pixelSourceBytecodeHash ==",
         NATIVE_BACKEND_CPP, "R269 R263 matches PS source identity"),
        ("bool shaderInterfaceLinkExact{};",
         RUNTIME_CENSUS, "R269 production census pair linkage exactness"),
        ("const auto shaderInterfaceLinkage =",
         RUNTIME_CENSUS, "R269 production census derives R268 linkage"),
        ("hash, sig.shaderInterfaceLinkHash",
         RUNTIME_CENSUS, "R269 census identity seals pair linkage hash"),
        ("R269 rejects R268 linkage provenance that does not match R263 source pair identity",
         CONSTANT_BUFFER_PROBE, "R269 stale source-linkage negative regression"),
    ]
    missing_r269_programmable_linkage_provenance_handoff = [
        meaning for token, source, meaning
        in r269_programmable_linkage_provenance_handoff_contract
        if token not in source
    ]
    if missing_r269_programmable_linkage_provenance_handoff:
        raise SystemExit(
            "DX11 R269 programmable linkage-provenance handoff drift: "
            + ", ".join(
                missing_r269_programmable_linkage_provenance_handoff)
        )

    r270_programmable_register_semantics_source_provenance_contract = [
        ("validate_programmable_shader_register_semantics(",
         PIPELINE_TRANSLATION_HPP, "R270 R266-to-R265 provenance validator declaration"),
        ("semantics.sourceBytecodeHash == decode.sourceBytecodeHash",
         PIPELINE_TRANSLATION_CPP, "R270 exact source bytecode identity match"),
        ("semantics.versionToken == decode.versionToken",
         PIPELINE_TRANSLATION_CPP, "R270 exact shader version identity match"),
        ("validate_programmable_shader_register_semantics(",
         RUNTIME_CENSUS, "R270 production census requires source-attested register semantics"),
        ("R270 rejects detached R266 register semantics with stale R265 source provenance",
         CONSTANT_BUFFER_PROBE, "R270 detached receipt fail-closed regression"),
    ]
    missing_r270_programmable_register_semantics_source_provenance = [
        meaning for token, source, meaning
        in r270_programmable_register_semantics_source_provenance_contract
        if token not in source
    ]
    if missing_r270_programmable_register_semantics_source_provenance:
        raise SystemExit(
            "DX11 R270 register-semantics source-provenance drift: "
            + ", ".join(
                missing_r270_programmable_register_semantics_source_provenance)
        )

    r271_programmable_pair_source_semantic_receipt_contract = [
        ("struct ProgrammableShaderPairSourceSemanticEvidence",
         PIPELINE_TRANSLATION_HPP, "R271 pair source-semantic evidence type"),
        ("derive_programmable_shader_pair_source_semantic_evidence(",
         PIPELINE_TRANSLATION_HPP, "R271 pair receipt derivation declaration"),
        ("R271_D3D9_PROGRAMMABLE_PAIR_SOURCE_SEMANTIC_RECEIPT_V1",
         PIPELINE_TRANSLATION_CPP, "R271 receipt revision provenance"),
        ("R271_R239_R270_R266_R268_EXACT_PAIR_PROVENANCE_V1",
         PIPELINE_TRANSLATION_CPP, "R271 semantic contract provenance"),
        ("sourceSemanticPair =",
         RUNTIME_CENSUS, "R271 production census derives pair receipt"),
        ("shaderSourceSemanticPairExact",
         RUNTIME_CENSUS, "R271 production census seals receipt exactness"),
        ("VR DX11 R271 sourceSemanticPair:",
         RUNTIME_CENSUS, "R271 production census exposes diagnostic receipt"),
        ("R271 composes exact R239 R266 R268 pair source-semantic receipt",
         CONSTANT_BUFFER_PROBE, "R271 positive pair-receipt regression"),
        ("R271 rejects detached pixel register semantics from another source stream",
         CONSTANT_BUFFER_PROBE, "R271 stale source fail-closed regression"),
        ("sig.shaderTranslationExact = false;",
         RUNTIME_CENSUS, "R271 must not widen programmable translation readiness"),
    ]
    missing_r271_programmable_pair_source_semantic_receipt = [
        meaning for token, source, meaning
        in r271_programmable_pair_source_semantic_receipt_contract
        if token not in source
    ]
    if missing_r271_programmable_pair_source_semantic_receipt:
        raise SystemExit(
            "DX11 R271 programmable pair source-semantic receipt drift: "
            + ", ".join(
                missing_r271_programmable_pair_source_semantic_receipt)
        )

    r272_programmable_register_mapping_plan_contract = [
        ("struct ProgrammableShaderRegisterMappingPlanEvidence",
         PIPELINE_TRANSLATION_HPP, "R272 mapping-plan evidence type"),
        ("derive_programmable_shader_register_mapping_plan(",
         PIPELINE_TRANSLATION_HPP, "R272 mapping-plan derivation declaration"),
        ("R272_D3D9_PROGRAMMABLE_REGISTER_MAPPING_PLAN_V1",
         PIPELINE_TRANSLATION_CPP, "R272 mapping-plan revision provenance"),
        ("R272_R271_R266_EXACT_CONSTANT_SAMPLER_MAPPING_V1",
         PIPELINE_TRANSLATION_CPP, "R272 mapping semantic contract provenance"),
        ("operand.relativeAddressing)",
         PIPELINE_TRANSLATION_CPP, "R272 relative-address mapping stays fail closed"),
        ("shaderRegisterMappingPlanExact",
         RUNTIME_CENSUS, "R272 production census seals mapping-plan exactness"),
        ("VR DX11 R272 registerMappingPlan:",
         RUNTIME_CENSUS, "R272 production census exposes mapping-plan hashes"),
        ("R272 derives exact deterministic constant-register and sampler mapping plan",
         CONSTANT_BUFFER_PROBE, "R272 positive register/sampler mapping regression"),
        ("R272 rejects relative-address constant mapping plans fail closed",
         CONSTANT_BUFFER_PROBE, "R272 relative-address fail-closed regression"),
        ("sig.shaderTranslationExact = false;",
         RUNTIME_CENSUS, "R272 must not widen programmable translation readiness"),
    ]
    missing_r272_programmable_register_mapping_plan = [
        meaning for token, source, meaning
        in r272_programmable_register_mapping_plan_contract
        if token not in source
    ]
    if missing_r272_programmable_register_mapping_plan:
        raise SystemExit(
            "DX11 R272 programmable register-mapping plan drift: "
            + ", ".join(
                missing_r272_programmable_register_mapping_plan)
        )

    r273_programmable_source_mapping_handoff_contract = [
        ("struct NativeProgrammableShaderSourceMappingHandoff",
         NATIVE_BACKEND_HPP, "R273 source mapping handoff type"),
        ("compose_programmable_shader_source_mapping_handoff(",
         NATIVE_BACKEND_HPP, "R273 handoff composition declaration"),
        ("validate_programmable_shader_source_mapping_handoff_snapshot(",
         NATIVE_BACKEND_HPP, "R273 handoff snapshot validator"),
        ("out.sourceReceiptIdentityMatches =",
         NATIVE_BACKEND_CPP, "R273 R239/R271 source identity binding"),
        ("out.mappingPlanIdentityMatches =",
         NATIVE_BACKEND_CPP, "R273 R272 mapping-plan identity binding"),
        ("token, 0x273u",
         NATIVE_BACKEND_CPP, "R273 independent handoff snapshot-domain tag"),
        ("sourceMappingHandoff =",
         RUNTIME_CENSUS, "R273 production census composes source mapping handoff"),
        ("shaderSourceMappingHandoffExact",
         RUNTIME_CENSUS, "R273 production census seals handoff exactness"),
        ("VR DX11 R273 sourceMappingHandoff:",
         RUNTIME_CENSUS, "R273 production census logs handoff snapshot"),
        ("R273 binds exact R272 mapping plan to R239 R271 source identity",
         CONSTANT_BUFFER_PROBE, "R273 positive source/mapping handoff regression"),
        ("R273 rejects detached R272 mapping-plan identity fail closed",
         CONSTANT_BUFFER_PROBE, "R273 stale mapping-plan fail-closed regression"),
        ("sig.shaderTranslationExact = false;",
         RUNTIME_CENSUS, "R273 keeps programmable translation fail closed"),
    ]
    missing_r273_programmable_source_mapping_handoff = [
        meaning for token, source, meaning
        in r273_programmable_source_mapping_handoff_contract
        if token not in source
    ]
    if missing_r273_programmable_source_mapping_handoff:
        raise SystemExit(
            "DX11 R273 programmable source-mapping handoff drift: "
            + ", ".join(
                missing_r273_programmable_source_mapping_handoff)
        )

    r274_r263_source_mapping_consumption_contract = [
        ("const NativeProgrammableShaderSourceMappingHandoff& sourceMappingHandoff",
         NATIVE_BACKEND_HPP, "R274 R263 consumes R273 handoff by type"),
        ("sourceMappingHandoff.reviewSnapshotToken ==",
         NATIVE_BACKEND_CPP, "R274 exact source-mapping snapshot comparison"),
        ("sourceMappingHandoff.cacheKey == sourceIdentity.cacheKey",
         NATIVE_BACKEND_CPP, "R274 source mapping identity tied to R239 pair"),
        ("sourceMappingHandoff.constantRegisterMappingExact",
         NATIVE_BACKEND_CPP, "R274 constant mapping no longer fixture boolean"),
        ("sourceMappingHandoff.samplerMappingExact",
         NATIVE_BACKEND_CPP, "R274 sampler mapping no longer fixture boolean"),
        ("r274SourceMappingPlan =",
         CONSTANT_BUFFER_PROBE, "R274 source-derived mapping plan fixture replacement"),
        ("r274SourceMappingHandoff =",
         CONSTANT_BUFFER_PROBE, "R274 source-derived R273 handoff fixture replacement"),
        ("sig.shaderTranslationExact = false;",
         RUNTIME_CENSUS, "R274 preserves programmable production fail-closed gate"),
    ]
    missing_r274_r263_source_mapping_consumption = [
        meaning for token, source, meaning
        in r274_r263_source_mapping_consumption_contract
        if token not in source
    ]
    if missing_r274_r263_source_mapping_consumption:
        raise SystemExit(
            "DX11 R274 R263 source-mapping consumption drift: "
            + ", ".join(missing_r274_r263_source_mapping_consumption)
        )

    r275_r263_receipt_consumption_contract = [
        ("translatedSemanticReceipt.reviewSnapshotToken ==",
         NATIVE_BACKEND_CPP, "R275 receipt carries its sealed snapshot"),
        ("validate_programmable_shader_translated_semantic_receipt_snapshot(",
         NATIVE_BACKEND_CPP, "R263 validates R275 receipt integrity"),
        ("translatedSemanticReceipt.translationObjectSnapshotToken ==",
         NATIVE_BACKEND_CPP, "R263 binds R275 to current R242 object receipt"),
        ("translationPlan.reviewSnapshotToken ==",
         NATIVE_BACKEND_CPP, "R275 requires exact R276 plan snapshot"),
        ("r276TranslationPlan =",
         CONSTANT_BUFFER_PROBE, "R276 source-derived plan fixture is explicit"),
        ("r275SemanticReceipt =",
         CONSTANT_BUFFER_PROBE, "R275 receipt consumes typed R276 plan"),
        ("sig.shaderTranslationExact = false;",
         RUNTIME_CENSUS, "R275/R276 keep programmable production gate fail-closed"),
    ]
    missing_r275_r263_receipt_consumption = [
        meaning for token, source, meaning
        in r275_r263_receipt_consumption_contract
        if token not in source
    ]
    if missing_r275_r263_receipt_consumption:
        raise SystemExit(
            "DX11 R275 R263 receipt-consumption drift: "
            + ", ".join(missing_r275_r263_receipt_consumption)
        )

    r277_programmable_semantic_census_contract = [
        ("shaderSemanticTranslationPlanExact",
         RUNTIME_CENSUS, "R277 census carries R276 plan readiness"),
        ("derive_programmable_shader_semantic_translation_plan(",
         RUNTIME_CENSUS, "R277 census derives R276 plan from live source evidence"),
        ("shaderSemanticTranslationPlanSnapshotToken",
         RUNTIME_CENSUS, "R277 census seals R276 plan snapshot identity"),
        ("shaderTranslatedSemanticReceiptExact",
         RUNTIME_CENSUS, "R277 census carries R275 receipt readiness"),
        ("NativeProgrammableShaderTranslationObjectReadiness",
         RUNTIME_CENSUS, "R277 census explicitly models unavailable R242 ownership"),
        ("compose_programmable_shader_translated_semantic_receipt(",
         RUNTIME_CENSUS, "R277 census composes typed R275 receipt"),
        ("VR DX11 R276 semanticTranslationPlan signature#{}:",
         RUNTIME_CENSUS, "R277 detailed R276 plan log"),
        ("VR DX11 R275 translatedSemanticReceipt signature#{}:",
         RUNTIME_CENSUS, "R277 detailed R275 receipt log"),
        ("programmableSemantic[planExact={},planPending={},receiptExact={},receiptPending={}]",
         RUNTIME_CENSUS, "R277 periodic readiness counters"),
        ("ProgrammableSemanticTranslation",
         DX11_CENSUS_ANALYZER, "R277 analyzer exposes programmable semantic evidence"),
        ("r277_programmable_semantic",
         DX11_CENSUS_ANALYZER_TEST, "R277 analyzer regression fixture"),
        ("sig.shaderTranslationExact = false;",
         RUNTIME_CENSUS, "R277 does not promote programmable translation"),
    ]
    missing_r277_programmable_semantic_census = [
        meaning for token, source, meaning
        in r277_programmable_semantic_census_contract
        if token not in source
    ]
    if missing_r277_programmable_semantic_census:
        raise SystemExit(
            "DX11 R277 programmable semantic census drift: "
            + ", ".join(missing_r277_programmable_semantic_census)
        )

    r278_programmable_semantic_correlation_contract = [
        ("VR DX11 R276 semanticTranslationPlan signature#{}:",
         RUNTIME_CENSUS, "R278 R276 evidence is signature-attributable"),
        ("VR DX11 R275 translatedSemanticReceipt signature#{}:",
         RUNTIME_CENSUS, "R278 R275 evidence is signature-attributable"),
        ("R276_SEMANTIC_PLAN_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R278 analyzer parses R276 plan identity"),
        ("R275_SEMANTIC_RECEIPT_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R278 analyzer parses R275 receipt identity"),
        ("R242ObjectOwnershipMissingSignatures",
         DX11_CENSUS_ANALYZER, "R278 analyzer classifies exact R242 ownership gap"),
        ("SemanticTranslationEvidence",
         DX11_CENSUS_ANALYZER, "R278 programmable inventory carries per-signature evidence"),
        ("R242_TRANSLATED_OBJECT_OWNERSHIP",
         DX11_CENSUS_ANALYZER, "R278 explicit remaining prerequisite classification"),
        ("r278_programmable_semantic",
         DX11_CENSUS_ANALYZER_TEST, "R278 per-signature correlation regression"),
        ("NativeDrawPathActivationAllowed",
         DX11_CENSUS_ANALYZER_TEST, "R278 regression keeps activation disabled"),
    ]
    missing_r278_programmable_semantic_correlation = [
        meaning for token, source, meaning
        in r278_programmable_semantic_correlation_contract
        if token not in source
    ]
    if missing_r278_programmable_semantic_correlation:
        raise SystemExit(
            "DX11 R278 programmable semantic correlation drift: "
            + ", ".join(missing_r278_programmable_semantic_correlation)
        )

    r279_programmable_object_prerequisite_contract = [
        ("struct NativeProgrammableShaderTranslationObjectPrerequisiteEvidence",
         NATIVE_BACKEND_HPP, "R279 explicit R242 ownership/lifetime prerequisite type"),
        ("derive_programmable_shader_translation_object_prerequisite(",
         NATIVE_BACKEND_HPP, "R279 prerequisite derivation declaration"),
        ("validate_programmable_shader_translation_object_prerequisite_snapshot(",
         NATIVE_BACKEND_HPP, "R279 prerequisite snapshot validator declaration"),
        ("token, 0x279u", NATIVE_BACKEND_CPP,
         "R279 independent prerequisite snapshot domain"),
        ("cacheOwnerGenerationRequired", NATIVE_BACKEND_HPP,
         "R279 requires R240 owner generation"),
        ("translationSlotGenerationRequired", NATIVE_BACKEND_HPP,
         "R279 requires R241 slot generation"),
        ("translationObjectReceiptGenerationRequired", NATIVE_BACKEND_HPP,
         "R279 requires R242 object receipt generation"),
        ("sameDeviceObjectPairRequired", NATIVE_BACKEND_HPP,
         "R279 requires same-device VS/PS pair"),
        ("VR DX11 R279 translationObjectPrerequisite signature#{}:",
         RUNTIME_CENSUS, "R279 signature-attributable production prerequisite log"),
        ("R279_OBJECT_PREREQUISITE_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R279 analyzer parser"),
        ("ObjectOwnershipPrerequisite", DX11_CENSUS_ANALYZER,
         "R279 analyzer correlates prerequisite evidence"),
        ("R279_TRANSLATION_OBJECT_PREREQUISITE_EVIDENCE",
         DX11_CENSUS_ANALYZER, "R279 missing prerequisite evidence classification"),
        ("ObjectOwnershipPrerequisiteExactSignatures",
         DX11_CENSUS_ANALYZER_TEST, "R279 analyzer regression coverage"),
        ("R279 translated object prerequisite", CONSTANT_BUFFER_PROBE,
         "R279 hosted prerequisite regression"),
        ("sig.shaderTranslationExact = false;", RUNTIME_CENSUS,
         "R279 keeps programmable translation fail-closed"),
    ]
    missing_r279_programmable_object_prerequisite = [
        meaning for token, source, meaning
        in r279_programmable_object_prerequisite_contract
        if token not in source
    ]
    if missing_r279_programmable_object_prerequisite:
        raise SystemExit(
            "DX11 R279 programmable object prerequisite drift: "
            + ", ".join(missing_r279_programmable_object_prerequisite)
        )

    r280_programmable_object_creation_handoff_contract = [
        ("struct NativeProgrammableShaderObjectCreationHandoffEvidence",
         NATIVE_BACKEND_HPP, "R280 source-to-object handoff evidence type"),
        ("compose_programmable_shader_object_creation_handoff(",
         NATIVE_BACKEND_HPP, "R280 handoff composer declaration"),
        ("validate_programmable_shader_object_creation_handoff_snapshot(",
         NATIVE_BACKEND_HPP, "R280 handoff snapshot validator declaration"),
        ("validate_programmable_shader_function_source_evidence(",
         NATIVE_BACKEND_CPP, "R280 exact R264 source binding"),
        ("out.objectCreationAuthorized = false;", NATIVE_BACKEND_CPP,
         "R280 cannot authorize shader object creation"),
        ("token, 0x280u", NATIVE_BACKEND_CPP,
         "R280 independent handoff snapshot domain"),
        ("ProgrammableShaderFunctionSourceEvidence vertexSourceEvidence{};",
         RUNTIME_CENSUS, "R280 production census retains vertex R264 evidence"),
        ("ProgrammableShaderFunctionSourceEvidence pixelSourceEvidence{};",
         RUNTIME_CENSUS, "R280 production census retains pixel R264 evidence"),
        ("compose_programmable_shader_object_creation_handoff(",
         RUNTIME_CENSUS, "R280 production census composes handoff"),
        ("VR DX11 R280 objectCreationHandoff signature#{}:",
         RUNTIME_CENSUS, "R280 signature-attributable production log"),
        ("R280_OBJECT_CREATION_HANDOFF_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R280 analyzer parser"),
        ("ObjectCreationHandoff", DX11_CENSUS_ANALYZER,
         "R280 analyzer correlates handoff evidence"),
        ("R280_OBJECT_CREATION_HANDOFF_EVIDENCE",
         DX11_CENSUS_ANALYZER, "R280 missing handoff classification"),
        ("ObjectCreationHandoffExactSignatures",
         DX11_CENSUS_ANALYZER_TEST, "R280 analyzer regression coverage"),
        ("R280 object creation handoff binds exact R264 source bytes",
         CONSTANT_BUFFER_PROBE, "R280 hosted positive regression"),
        ("R280 object creation handoff rejects stale R264 source identity",
         CONSTANT_BUFFER_PROBE, "R280 source drift regression"),
        ("sig.shaderTranslationExact = false;", RUNTIME_CENSUS,
         "R280 keeps programmable translation fail-closed"),
    ]
    missing_r280_programmable_object_creation_handoff = [
        meaning for token, source, meaning
        in r280_programmable_object_creation_handoff_contract
        if token not in source
    ]
    if missing_r280_programmable_object_creation_handoff:
        raise SystemExit(
            "DX11 R280 programmable object creation handoff drift: "
            + ", ".join(missing_r280_programmable_object_creation_handoff)
        )

    r281_programmable_translated_artifact_receipt_contract = [
        ("struct NativeProgrammableShaderTranslatedArtifactReceiptEvidence",
         NATIVE_BACKEND_HPP, "R281 translated artifact receipt evidence type"),
        ("derive_programmable_shader_translated_artifact_receipt(",
         NATIVE_BACKEND_HPP, "R281 receipt composer declaration"),
        ("validate_programmable_shader_translated_artifact_receipt_snapshot(",
         NATIVE_BACKEND_HPP, "R281 receipt snapshot validator declaration"),
        ("targetVertexBytecodeReceiptIdentity", NATIVE_BACKEND_HPP,
         "R281 target vertex bytecode identity requirement"),
        ("targetPixelBytecodeReceiptIdentity", NATIVE_BACKEND_HPP,
         "R281 target pixel bytecode identity requirement"),
        ("out.targetBytecodeMaterialized = false;", NATIVE_BACKEND_CPP,
         "R281 cannot claim target bytecode materialization"),
        ("out.objectCreationAuthorized = false;", NATIVE_BACKEND_CPP,
         "R281 cannot authorize programmable object creation"),
        ("token, 0x281u", NATIVE_BACKEND_CPP,
         "R281 independent receipt snapshot domain"),
        ("derive_programmable_shader_translated_artifact_receipt(",
         RUNTIME_CENSUS, "R281 production census derives receipt"),
        ("VR DX11 R281 translatedArtifactReceipt signature#{}:",
         RUNTIME_CENSUS, "R281 signature-attributable production receipt log"),
        ("R281_TRANSLATED_ARTIFACT_RECEIPT_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R281 analyzer parser"),
        ("TranslatedArtifactReceipt", DX11_CENSUS_ANALYZER,
         "R281 analyzer correlates artifact receipt"),
        ("R281_TRANSLATED_ARTIFACT_RECEIPT_EVIDENCE",
         DX11_CENSUS_ANALYZER, "R281 missing receipt classification"),
        ("TranslatedArtifactReceiptExactSignatures",
         DX11_CENSUS_ANALYZER_TEST, "R281 analyzer regression coverage"),
        ("R281 translated artifact receipt defines target bytecode identity",
         CONSTANT_BUFFER_PROBE, "R281 hosted positive regression"),
        ("R281 translated artifact receipt rejects stale R280 handoff identity",
         CONSTANT_BUFFER_PROBE, "R281 stale handoff regression"),
        ("sig.shaderTranslationExact = false;", RUNTIME_CENSUS,
         "R281 keeps programmable translation fail-closed"),
    ]
    missing_r281_programmable_translated_artifact_receipt = [
        meaning for token, source, meaning
        in r281_programmable_translated_artifact_receipt_contract
        if token not in source
    ]
    if missing_r281_programmable_translated_artifact_receipt:
        raise SystemExit(
            "DX11 R281 programmable translated artifact receipt drift: "
            + ", ".join(missing_r281_programmable_translated_artifact_receipt)
        )

    r282_programmable_target_materialization_contract = [
        ("struct NativeProgrammableShaderTargetMaterializationContractEvidence",
         NATIVE_BACKEND_HPP, "R282 target materialization contract evidence type"),
        ("derive_programmable_shader_target_materialization_contract(",
         NATIVE_BACKEND_HPP, "R282 contract composer declaration"),
        ("validate_programmable_shader_target_materialization_contract_snapshot(",
         NATIVE_BACKEND_HPP, "R282 contract snapshot validator declaration"),
        ("constexpr char kEntryPoint[] = \"main\";", NATIVE_BACKEND_CPP,
         "R282 deterministic entrypoint"),
        ("constexpr char kVertexTargetProfile[] = \"vs_4_0\";", NATIVE_BACKEND_CPP,
         "R282 deterministic vertex profile"),
        ("constexpr char kPixelTargetProfile[] = \"ps_4_0\";", NATIVE_BACKEND_CPP,
         "R282 deterministic pixel profile"),
        ("D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3",
         NATIVE_BACKEND_CPP, "R282 deterministic compile flags"),
        ("out.targetBytecodeMaterialized = false;", NATIVE_BACKEND_CPP,
         "R282 cannot claim target bytecode materialization"),
        ("out.compilationAuthorized = false;", NATIVE_BACKEND_CPP,
         "R282 cannot authorize programmable compilation"),
        ("out.objectCreationAuthorized = false;", NATIVE_BACKEND_CPP,
         "R282 cannot authorize programmable object creation"),
        ("token, 0x282u", NATIVE_BACKEND_CPP,
         "R282 independent contract snapshot domain"),
        ("derive_programmable_shader_target_materialization_contract(",
         RUNTIME_CENSUS, "R282 production census derives contract"),
        ("VR DX11 R282 targetMaterializationContract signature#{}:",
         RUNTIME_CENSUS, "R282 signature-attributable production contract log"),
        ("R282_TARGET_MATERIALIZATION_CONTRACT_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R282 analyzer parser"),
        ("TargetMaterializationContract", DX11_CENSUS_ANALYZER,
         "R282 analyzer correlates materialization contract"),
        ("R283_TARGET_BYTECODE_MATERIALIZATION", DX11_CENSUS_ANALYZER,
         "R282 advances missing boundary to target bytecode materialization"),
        ("TargetMaterializationContractExactSignatures",
         DX11_CENSUS_ANALYZER_TEST, "R282 analyzer regression coverage"),
        ("R282 target materialization contract seals main vs_4_0 ps_4_0 strict O3 without compiling",
         CONSTANT_BUFFER_PROBE, "R282 hosted positive regression"),
        ("R282 target materialization contract rejects stale R281 artifact receipt identity",
         CONSTANT_BUFFER_PROBE, "R282 stale artifact regression"),
        ("sig.shaderTranslationExact = false;", RUNTIME_CENSUS,
         "R282 keeps programmable translation fail-closed"),
    ]
    missing_r282_programmable_target_materialization_contract = [
        meaning for token, source, meaning
        in r282_programmable_target_materialization_contract
        if token not in source
    ]
    if missing_r282_programmable_target_materialization_contract:
        raise SystemExit(
            "DX11 R282 programmable target materialization contract drift: "
            + ", ".join(missing_r282_programmable_target_materialization_contract)
        )

    r283_programmable_target_bytecode_materialization = [
        ("struct NativeProgrammableShaderTargetBytecodeMaterializationEvidence",
         NATIVE_BACKEND_HPP, "R283 materialized bytecode evidence type"),
        ("materialize_programmable_shader_target_bytecode(",
         NATIVE_BACKEND_HPP, "R283 materializer declaration"),
        ("validate_programmable_shader_target_bytecode_materialization_snapshot(",
         NATIVE_BACKEND_HPP, "R283 materialized bytecode validator declaration"),
        ("R283_D3D9_SM3_DCL_MOV_HLSL_MATERIALIZER_V1",
         NATIVE_BACKEND_CPP, "R283 bounded materializer revision"),
        ("R283_R281_R282_R276_SM3_DCL_MOV_DXBC_PROVENANCE_V1",
         NATIVE_BACKEND_CPP, "R283 provenance contract"),
        ("build_r283_sm3_mov_shader_source(",
         NATIVE_BACKEND_CPP, "R283 SM3 DCL+MOV fail-closed source translator"),
        ("r283_programmable_vs", NATIVE_BACKEND_CPP,
         "R283 vertex source is compiled through native compiler policy"),
        ("r283_programmable_ps", NATIVE_BACKEND_CPP,
         "R283 pixel source is compiled through native compiler policy"),
        ("r283_dxbc_payload(", NATIVE_BACKEND_CPP,
         "R283 validates materialized DXBC payload signature"),
        ("out.objectCreationAuthorized = false;", NATIVE_BACKEND_CPP,
         "R283 cannot authorize programmable object creation"),
        ("token, 0x283u", NATIVE_BACKEND_CPP,
         "R283 independent materialization snapshot domain"),
        ("materialize_programmable_shader_target_bytecode(",
         RUNTIME_CENSUS, "R283 production census materializes bounded target bytes"),
        ("VR DX11 R283 targetBytecodeMaterialization signature#{}:",
         RUNTIME_CENSUS, "R283 signature-attributable production materialization log"),
        ("R283_TARGET_BYTECODE_MATERIALIZATION_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R283 analyzer parser"),
        ("TargetBytecodeMaterialization", DX11_CENSUS_ANALYZER,
         "R283 analyzer correlates materialized bytecode evidence"),
        ("R242_TRANSLATED_OBJECT_OWNERSHIP", DX11_CENSUS_ANALYZER,
         "R283 advances exact materialization boundary to R242 ownership"),
        ("TargetBytecodeMaterializationExactSignatures",
         DX11_CENSUS_ANALYZER_TEST, "R283 analyzer regression coverage"),
        ("R283 materializes bounded SM3 DCL+MOV HLSL and DXBC while object creation stays disabled",
         CONSTANT_BUFFER_PROBE, "R283 hosted positive compile/materialization regression"),
        ("R283 rejects source bytes detached from the R281/R282 provenance",
         CONSTANT_BUFFER_PROBE, "R283 stale source provenance regression"),
        ("sig.shaderTranslationExact = false;", RUNTIME_CENSUS,
         "R283 keeps programmable translation activation fail-closed"),
    ]
    missing_r283_programmable_target_bytecode_materialization = [
        meaning for token, source, meaning
        in r283_programmable_target_bytecode_materialization
        if token not in source
    ]
    if missing_r283_programmable_target_bytecode_materialization:
        raise SystemExit(
            "DX11 R283 programmable target bytecode materialization drift: "
            + ", ".join(missing_r283_programmable_target_bytecode_materialization)
        )

    r284_programmable_shader_object_materialization = [
        ("struct NativeProgrammableShaderObjectMaterializationEvidence",
         NATIVE_BACKEND_HPP, "R284 object-materialization evidence type"),
        ("materialize_programmable_shader_translation_objects(",
         NATIVE_BACKEND_HPP, "R284 object materializer declaration"),
        ("validate_programmable_shader_object_materialization_snapshot(",
         NATIVE_BACKEND_HPP, "R284 object-materialization validator declaration"),
        ("R284_R283_DXBC_R240_R241_R242_OBJECT_MATERIALIZER_V1",
         NATIVE_BACKEND_CPP, "R284 materializer revision/provenance domain"),
        ("expectedDevice->CreateVertexShader(",
         NATIVE_BACKEND_CPP, "R284 creates VS only from exact R283 DXBC"),
        ("expectedDevice->CreatePixelShader(",
         NATIVE_BACKEND_CPP, "R284 creates PS only from exact R283 DXBC"),
        ("cache.attach_translation_objects_for_observation(",
         NATIVE_BACKEND_CPP, "R284 reuses R242 same-device ownership attachment"),
        ("out.objectBindingAuthorized = false;",
         NATIVE_BACKEND_CPP, "R284 cannot authorize shader/context binding"),
        ("token, 0x284u",
         NATIVE_BACKEND_CPP, "R284 independent materialization snapshot domain"),
        ("R284 materializes exact R283 DXBC into same-device R242 object ownership",
         CONSTANT_BUFFER_PROBE, "R284 hosted positive creation/ownership regression"),
        ("R284 object materialization must not bind VS or PS to the immediate context",
         CONSTANT_BUFFER_PROBE, "R284 explicit no-binding regression"),
        ("R284 ownership receipt rejects a foreign D3D11 device",
         CONSTANT_BUFFER_PROBE, "R284 foreign-device rejection regression"),
        ("R284 rejects stale/tampered R283 bytecode provenance before object creation",
         CONSTANT_BUFFER_PROBE, "R284 stale R283 provenance regression"),
    ]
    missing_r284_programmable_shader_object_materialization = [
        meaning for token, source, meaning
        in r284_programmable_shader_object_materialization
        if token not in source
    ]
    if missing_r284_programmable_shader_object_materialization:
        raise SystemExit(
            "DX11 R284 programmable shader object materialization drift: "
            + ", ".join(missing_r284_programmable_shader_object_materialization)
        )

    r285_programmable_backend_semantic_handoff = [
        ("struct NativeProgrammableShaderBackendSemanticHandoffEvidence",
         NATIVE_BACKEND_HPP, "R285 persistent backend handoff evidence type"),
        ("class NativeProgrammableShaderBackendOwnership",
         NATIVE_BACKEND_HPP, "R285 persistent native-device owner"),
        ("materialize_semantic_handoff_for_observation(",
         NATIVE_BACKEND_HPP, "R285 persistent ownership-to-R275 entrypoint"),
        ("validate_semantic_handoff_snapshot(",
         NATIVE_BACKEND_HPP, "R285 persistent handoff validator"),
        ("r285_backend_semantic_handoff_snapshot_token(",
         NATIVE_BACKEND_CPP, "R285 tamper-evident handoff snapshot"),
        ("token, 0x285u",
         NATIVE_BACKEND_CPP, "R285 independent snapshot domain"),
        ("materializations_.emplace(sourceIdentity.cacheKey, created)",
         NATIVE_BACKEND_CPP, "R285 persists exact R284 receipt per pair"),
        ("compose_programmable_shader_translated_semantic_receipt(",
         NATIVE_BACKEND_CPP, "R285 feeds current R242 object receipt into R275"),
        ("out.objectBindingAuthorized = false;",
         NATIVE_BACKEND_CPP, "R285 keeps shader/context binding unauthorized"),
        ("out.nativeDrawPathActivationAllowed = false;",
         NATIVE_BACKEND_CPP, "R285 keeps NativeDrawPath inactive"),
        ("out.drawDispatchAuthorized = false;",
         NATIVE_BACKEND_CPP, "R285 keeps Draw/DrawIndexed dispatch unauthorized"),
        ("programmable_shader_ownership_.initialize(device_.Get())",
         NATIVE_BACKEND_CPP, "NativeBackend initializes R285 owner on its native device"),
        ("programmable_shader_ownership_.shutdown();",
         NATIVE_BACKEND_CPP, "NativeBackend invalidates R285 ownership before device release"),
        ("R285 native owner feeds exact persistent R242 ownership into R275 without binding",
         CONSTANT_BUFFER_PROBE, "R285 hosted positive ownership-to-R275 regression"),
        ("R285 repeated pair reuses exact R284/R242 receipt instead of recreating shaders",
         CONSTANT_BUFFER_PROBE, "R285 persistent receipt reuse regression"),
        ("R285 persistent ownership handoff must not bind VS or PS to the immediate context",
         CONSTANT_BUFFER_PROBE, "R285 explicit no-binding regression"),
        ("R285 rejects stale R274 mapping identity after safe R284 receipt reuse",
         CONSTANT_BUFFER_PROBE, "R285 stale R275 provenance regression"),
        ("R285 native-device generation change invalidates prior persistent ownership handoff",
         CONSTANT_BUFFER_PROBE, "R285 device-generation invalidation regression"),
    ]
    missing_r285_programmable_backend_semantic_handoff = [
        meaning for token, source, meaning
        in r285_programmable_backend_semantic_handoff
        if token not in source
    ]
    if missing_r285_programmable_backend_semantic_handoff:
        raise SystemExit(
            "DX11 R285 programmable backend semantic handoff drift: "
            + ", ".join(missing_r285_programmable_backend_semantic_handoff)
        )


    r286_programmable_production_observation_bridge = [
        ("struct NativeProgrammableShaderProductionObservationEvidence",
         NATIVE_BACKEND_HPP, "R286 production observation evidence type"),
        ("observe_programmable_shader_production_source_evidence_chain(",
         NATIVE_BACKEND_HPP, "R286 bounded source-evidence bridge declaration"),
        ("observe_programmable_shader_source_evidence_chain(",
         NATIVE_BACKEND_HPP, "R286 NativeBackend production entrypoint"),
        ("r286_production_observation_snapshot_token(",
         NATIVE_BACKEND_CPP, "R286 tamper-evident production observation snapshot"),
        ("token, 0x286u",
         NATIVE_BACKEND_CPP, "R286 independent snapshot domain"),
        ("ownership.materialize_semantic_handoff_for_observation(",
         NATIVE_BACKEND_CPP, "R286 routes exact evidence into persistent R285 owner"),
        ("ownership.validate_semantic_handoff_snapshot(",
         NATIVE_BACKEND_CPP, "R286 validates exact R285 handoff receipt"),
        ("programmable_shader_ownership(),",
         NATIVE_BACKEND_CPP, "NativeBackend delegates through its persistent R285 owner"),
        ("out.objectBindingAuthorized =",
         NATIVE_BACKEND_CPP, "R286 carries explicit no-binding authority"),
        ("out.nativeDrawPathActivationAllowed =",
         NATIVE_BACKEND_CPP, "R286 keeps NativeDrawPath inactive"),
        ("out.drawDispatchAuthorized =",
         NATIVE_BACKEND_CPP, "R286 keeps Draw/DrawIndexed unauthorized"),
        ("R286 production source-evidence bridge reaches R285 ownership without binding or draw",
         CONSTANT_BUFFER_PROBE, "R286 positive hosted bridge regression"),
        ("R286 production bridge rejects stale R274 evidence before R285 handoff",
         CONSTANT_BUFFER_PROBE, "R286 stale source-evidence regression"),
        ("R286 NativeBackend entrypoint fails closed before native-device initialization",
         CONSTANT_BUFFER_PROBE, "R286 uninitialized production entrypoint regression"),
    ]
    missing_r286_programmable_production_observation_bridge = [
        meaning for token, source, meaning
        in r286_programmable_production_observation_bridge
        if token not in source
    ]
    if missing_r286_programmable_production_observation_bridge:
        raise SystemExit(
            "DX11 R286 programmable production observation bridge drift: "
            + ", ".join(missing_r286_programmable_production_observation_bridge)
        )


    r287_programmable_runtime_census_bridge = [
        ('#include "startup_census.hpp"',
         RUNTIME_CENSUS, "R287 runtime census can derive exact native bootstrap identity"),
        ("NativeBackend NativeProgrammableObservationBackend;",
         RUNTIME_CENSUS, "R287 owns one persistent dormant native backend"),
        ("NativeProgrammableObservationSourceDevice",
         RUNTIME_CENSUS, "R287 seals source-device lifetime identity"),
        ("!sourceIdentity.exact_identity()",
         RUNTIME_CENSUS, "R287 refuses native bootstrap for non-exact programmable pairs"),
        ("inspect_source_device(sourceDevice)",
         RUNTIME_CENSUS, "R287 derives adapter LUID and backbuffer bootstrap contract"),
        ("NativeProgrammableObservationBackend.initialize(config)",
         RUNTIME_CENSUS, "R287 initializes the dormant native backend on the source adapter"),
        ("observe_programmable_shader_source_evidence_chain(",
         RUNTIME_CENSUS, "R287 routes sampled production evidence through R286"),
        ("sig.shaderProductionObservationExact =",
         RUNTIME_CENSUS, "R287 persists production-observation readiness in signature identity"),
        ("productionObservation.semanticHandoff.translatedSemanticReceipt",
         RUNTIME_CENSUS, "R287 consumes exact R285/R275 semantic receipt"),
        ("VR DX11 R287 productionObservation signature#{}:",
         RUNTIME_CENSUS, "R287 emits bounded runtime census evidence"),
        ("NativeProgrammableObservationBackend.shutdown();",
         RUNTIME_CENSUS, "R287 invalidates native-device ownership on D3D9 Reset"),
        ("sig.shaderTranslationExact = false;",
         RUNTIME_CENSUS, "R287 cannot promote programmable translation or draw routing"),
    ]
    missing_r287_programmable_runtime_census_bridge = [
        meaning for token, source, meaning
        in r287_programmable_runtime_census_bridge
        if token not in source
    ]
    if missing_r287_programmable_runtime_census_bridge:
        raise SystemExit(
            "DX11 R287 programmable runtime census bridge drift: "
            + ", ".join(missing_r287_programmable_runtime_census_bridge)
        )

    r288_programmable_translation_admission_contract = [
        ("struct NativeProgrammableShaderTranslationAdmissionEvidence",
         NATIVE_BACKEND_HPP, "R288 promotion-review admission evidence type"),
        ("validate_programmable_shader_production_observation_snapshot(",
         NATIVE_BACKEND_HPP, "R288 validates the exact R286 production observation"),
        ("seal_programmable_shader_translation_admission(",
         NATIVE_BACKEND_HPP, "R288 admission receipt declaration"),
        ("validate_programmable_shader_translation_admission_snapshot(",
         NATIVE_BACKEND_HPP, "R288 admission snapshot validator declaration"),
        ("r288_programmable_translation_admission_snapshot_token(",
         NATIVE_BACKEND_CPP, "R288 tamper-evident admission snapshot"),
        ("token, 0x288u",
         NATIVE_BACKEND_CPP, "R288 independent snapshot domain"),
        ("validate_programmable_shader_production_observation_snapshot(",
         NATIVE_BACKEND_CPP, "R288 seals the current R286 observation snapshot"),
        ("validate_programmable_shader_translated_semantic_receipt_snapshot(",
         NATIVE_BACKEND_CPP, "R288 validates the nested exact R275 semantic receipt"),
        ("out.objectBindingAuthorized =",
         NATIVE_BACKEND_CPP, "R288 propagates and refuses shader binding authority"),
        ("out.nativeDrawPathActivationAllowed =",
         NATIVE_BACKEND_CPP, "R288 propagates and refuses NativeDrawPath authority"),
        ("out.drawDispatchAuthorized =",
         NATIVE_BACKEND_CPP, "R288 propagates and refuses Draw/DrawIndexed authority"),
        ("R288 translation admission seals exact R286/R275 readiness without authorizing binding or draw",
         CONSTANT_BUFFER_PROBE, "R288 exact admission hosted regression"),
        ("R288 translation admission rejects tampered R286 snapshot",
         CONSTANT_BUFFER_PROBE, "R288 stale/tampered R286 hosted regression"),
    ]
    missing_r288_programmable_translation_admission_contract = [
        meaning for token, source, meaning
        in r288_programmable_translation_admission_contract
        if token not in source
    ]
    if missing_r288_programmable_translation_admission_contract:
        raise SystemExit(
            "DX11 R288 programmable translation admission drift: "
            + ", ".join(missing_r288_programmable_translation_admission_contract)
        )

    r289_programmable_production_semantic_review_contract = [
        ("struct NativeProgrammableShaderProductionSemanticReviewEvidence",
         NATIVE_BACKEND_HPP, "R289 production semantic review evidence type"),
        ("materialize_semantic_translation_review_for_observation(",
         NATIVE_BACKEND_HPP, "R289 persistent owner review materializer declaration"),
        ("validate_semantic_translation_review_snapshot(",
         NATIVE_BACKEND_HPP, "R289 review snapshot validator declaration"),
        ("semantic_input_layouts_",
         NATIVE_BACKEND_HPP, "R289 persistent R243 input-layout object ownership"),
        ("r289_programmable_production_semantic_review_snapshot_token(",
         NATIVE_BACKEND_CPP, "R289 tamper-evident review snapshot"),
        ("token, 0x289u",
         NATIVE_BACKEND_CPP, "R289 independent snapshot domain"),
        ("device_->CreateInputLayout(",
         NATIVE_BACKEND_CPP, "R289 creates only the admitted input-layout object"),
        ("cache_.attach_input_layout_for_observation(",
         NATIVE_BACKEND_CPP, "R289 feeds the created layout into existing R243 ownership"),
        ("compose_programmable_shader_semantic_translation_readiness(",
         NATIVE_BACKEND_CPP, "R289 feeds R288/R243/R268 evidence into R263"),
        ("validate_programmable_shader_semantic_translation_readiness_snapshot(",
         NATIVE_BACKEND_CPP, "R289 validates the exact R263 review snapshot"),
        ("out.objectBindingAuthorized =",
         NATIVE_BACKEND_CPP, "R289 propagates and refuses object-binding authority"),
        ("out.nativeDrawPathActivationAllowed =",
         NATIVE_BACKEND_CPP, "R289 propagates and refuses NativeDrawPath authority"),
        ("out.drawDispatchAuthorized =",
         NATIVE_BACKEND_CPP, "R289 propagates and refuses Draw/DrawIndexed authority"),
        ("R289 production semantic review materializes R243 and validates R263 without binding or draw",
         CONSTANT_BUFFER_PROBE, "R289 positive hosted regression"),
        ("R289 repeated review reuses the persistent R243 input-layout receipt",
         CONSTANT_BUFFER_PROBE, "R289 persistent ownership regression"),
        ("R289 production semantic review rejects stale R288 admission before layout mutation",
         CONSTANT_BUFFER_PROBE, "R289 stale-admission fail-closed regression"),
        ("R289 production semantic review must not bind IA/VS/PS state",
         CONSTANT_BUFFER_PROBE, "R289 context-binding negative regression"),
    ]
    missing_r289_programmable_production_semantic_review_contract = [
        meaning for token, source, meaning
        in r289_programmable_production_semantic_review_contract
        if token not in source
    ]
    if missing_r289_programmable_production_semantic_review_contract:
        raise SystemExit(
            "DX11 R289 programmable production semantic review drift: "
            + ", ".join(missing_r289_programmable_production_semantic_review_contract)
        )

    r290_programmable_activation_pair_identity_contract = [
        ("R290 additionally seals the exact R239 cache key",
         NATIVE_BACKEND_HPP, "R290 R258 receipt carries explicit programmable-pair identity"),
        ("bool sourceIdentityMatches{};",
         NATIVE_BACKEND_HPP, "R290 R259 correlation result is explicit"),
        ("bool sourceIdentityProofPresent{};",
         NATIVE_BACKEND_HPP, "R290 identity proof is a distinct activation prerequisite"),
        ("out.cacheKey = cacheKey;",
         NATIVE_BACKEND_CPP, "R290 seals the source cache key into R258"),
        ("currentSource, identity.cacheKey,",
         NATIVE_BACKEND_CPP, "R290 both R258 revalidation paths receive exact R239 identity"),
        ("constexpr std::uint32_t kSourceIdentityMissing = 1u << 3;",
         NATIVE_BACKEND_CPP, "R290 reserves an independent missing-prerequisite bit"),
        ("out.sourceIdentityMatches =",
         NATIVE_BACKEND_CPP, "R290 compares R258 identity against R243/R263 evidence"),
        ("sourceRevalidationPayloadSnapshotMatches",
         NATIVE_BACKEND_HPP, "R299 R258 payload-integrity result is explicit"),
        ("recompute_programmable_dormant_source_revalidation_payload_snapshot(",
         NATIVE_BACKEND_CPP, "R299 recomputes the complete R258 payload identity"),
        ("out.sourceRevalidationPayloadSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R299 R259 requires R258 payload self-integrity"),
        ("R299 rejects R258 payload drift hidden behind an unchanged source-revalidation snapshot token",
         CONSTANT_BUFFER_PROBE, "R299 hosted R258 payload-tamper regression"),
        ("out.sourceIdentityProofPresent =",
         NATIVE_BACKEND_CPP, "R290 gates activation prerequisites on pair correlation"),
        ("token, 0x290u",
         NATIVE_BACKEND_CPP, "R290 extends the R259 snapshot domain"),
        ("R290 rejects cross-pair R258 versus R243/R263 prerequisite evidence",
         CONSTANT_BUFFER_PROBE, "R290 cross-pair hosted regression"),
    ]
    missing_r290_programmable_activation_pair_identity = [
        meaning for token, source, meaning
        in r290_programmable_activation_pair_identity_contract
        if token not in source
    ]
    if missing_r290_programmable_activation_pair_identity:
        raise SystemExit(
            "DX11 R290 programmable activation pair-identity drift: "
            + ", ".join(missing_r290_programmable_activation_pair_identity)
        )

    r291_programmable_runtime_semantic_review_bridge = [
        ("ProgrammableProductionSemanticReviewCensusEvidence",
         RUNTIME_CENSUS, "R291 production census bundle for R288/R289 evidence"),
        ("review_programmable_production_semantics(",
         RUNTIME_CENSUS, "R291 serialized production semantic review helper"),
        ("seal_programmable_shader_translation_admission(",
         RUNTIME_CENSUS, "R291 production path seals current R288 admission"),
        ("validate_programmable_shader_translation_admission_snapshot(",
         RUNTIME_CENSUS, "R291 validates exact R288 admission snapshot"),
        ("materialize_semantic_translation_review_for_observation(",
         RUNTIME_CENSUS, "R291 production path materializes R289 semantic review"),
        ("validate_semantic_translation_review_snapshot(",
         RUNTIME_CENSUS, "R291 validates exact R289 review snapshot"),
        ("sig.shaderTranslationAdmissionExact =",
         RUNTIME_CENSUS, "R291 census records R288 exactness"),
        ("sig.shaderProductionSemanticReviewExact =",
         RUNTIME_CENSUS, "R291 census records R289 exactness"),
        ("VR DX11 R291 productionSemanticReview",
         RUNTIME_CENSUS, "R291 bounded detailed-signature diagnostic"),
        ("sig.shaderTranslationExact = false;",
         RUNTIME_CENSUS, "R291 keeps programmable translation promotion fail-closed"),
    ]
    missing_r291_programmable_runtime_semantic_review = [
        meaning for token, source, meaning
        in r291_programmable_runtime_semantic_review_bridge
        if token not in source
    ]
    if missing_r291_programmable_runtime_semantic_review:
        raise SystemExit(
            "DX11 R291 programmable runtime semantic-review bridge drift: "
            + ", ".join(missing_r291_programmable_runtime_semantic_review)
        )

    r292_programmable_production_activation_prerequisite = [
        ("NativeProgrammableShaderProductionActivationPrerequisiteEvidence",
         NATIVE_BACKEND_HPP, "R292 explicit production prerequisite observation"),
        ("observe_programmable_shader_production_activation_prerequisites(",
         NATIVE_BACKEND_HPP, "R292 production prerequisite observer declaration"),
        ("validate_programmable_shader_production_activation_prerequisite_snapshot(",
         NATIVE_BACKEND_HPP, "R292 production prerequisite validator declaration"),
        ("resourceBehaviorPayloadSnapshotMatches",
         NATIVE_BACKEND_HPP, "R303 production gate exposes R262 payload-integrity result"),
        ("recompute_programmable_output_resource_behavior_payload_snapshot(",
         NATIVE_BACKEND_CPP, "R303 reconstructs the exact R262 review payload identity"),
        ("out.resourceBehaviorPayloadSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R303 R292 requires R262 payload self-integrity"),
        ("r292_programmable_production_activation_prerequisite_snapshot_token(",
         NATIVE_BACKEND_CPP, "R292 independent observation snapshot domain"),
        ("compose_programmable_activation_prerequisite_handoff(",
         NATIVE_BACKEND_CPP, "R292 reuses exact R259/R290 static prerequisite gate"),
        ("out.prerequisites.activationSnapshotToken == 0",
         NATIVE_BACKEND_CPP, "R292 keeps activation authority fail-closed"),
        ("R292 production activation-prerequisite observation combines exact R289+R258+R262 through R259 without activation",
         CONSTANT_BUFFER_PROBE, "R292 exact hosted production prerequisite regression"),
        ("R303 rejects R262 payload drift before production prerequisite handoff",
         CONSTANT_BUFFER_PROBE, "R303 R262-to-R292 payload tamper regression"),
        ("R292 rejects stale R289 production semantic review before R259 composition",
         CONSTANT_BUFFER_PROBE, "R292 stale production semantic review regression"),
    ]
    missing_r292_programmable_production_activation_prerequisite = [
        meaning for token, source, meaning
        in r292_programmable_production_activation_prerequisite
        if token not in source
    ]
    if missing_r292_programmable_production_activation_prerequisite:
        raise SystemExit(
            "DX11 R292 programmable production activation-prerequisite drift: "
            + ", ".join(
                missing_r292_programmable_production_activation_prerequisite
            )
        )

    r305_programmable_production_activation_payload_integrity = [
        ("r305_programmable_activation_prerequisite_payload_snapshot_token(",
         NATIVE_BACKEND_CPP, "R305 seals the complete copied R259 prerequisite payload"),
        ("r305_programmable_production_activation_payload_snapshot_token(",
         NATIVE_BACKEND_CPP, "R305 seals the complete copied R292 observation payload"),
        ("currentPayloadSnapshotToken",
         NATIVE_BACKEND_CPP, "R305 validator recomputes the current complete production payload"),
        ("observedPayloadSnapshotToken",
         NATIVE_BACKEND_CPP, "R305 validator recomputes the caller-supplied copied production payload"),
        ("R305 rejects copied R292 observation payload drift before production census trust",
         CONSTANT_BUFFER_PROBE, "R305 hosted top-level copied-observation tamper regression"),
        ("R305 rejects copied R259 prerequisite payload drift nested under R292",
         CONSTANT_BUFFER_PROBE, "R305 hosted nested prerequisite tamper regression"),
    ]
    missing_r305_programmable_production_activation_payload_integrity = [
        meaning for token, source, meaning
        in r305_programmable_production_activation_payload_integrity
        if token not in source
    ]
    if missing_r305_programmable_production_activation_payload_integrity:
        raise SystemExit(
            "DX11 R305 programmable production activation payload-integrity drift: "
            + ", ".join(
                missing_r305_programmable_production_activation_payload_integrity
            )
        )



    r313_programmable_source_mapping_handoff_analyzer_bridge = [
        ("def recompute_r273_handoff_snapshot(",
         DX11_CENSUS_ANALYZER, "R314 rebuilds R273 from exact R271/R272 identity"),
        ("token = mix_readiness_snapshot_token(token, 0x273u)",
         NATIVE_BACKEND_CPP, "R314 requires native R273 mixer domain tag"),
        ('"snapshot_matches_producer": snapshot_matches_producer',
         DX11_CENSUS_ANALYZER, "R314 rejects forged R273 snapshots"),
        ('"EXACT_RECONSTRUCTED_R273_SNAPSHOT"',
         DX11_CENSUS_ANALYZER, "R314 exact provenance strength classified"),
        ('"0x6AFFAF0E35D2F69B", "0xDEADBEEF00000001"',
         DX11_CENSUS_ANALYZER_TEST, "R314 counterfeit nonzero regression"),
        ("VR DX11 R273 sourceMappingHandoff",
         RUNTIME_CENSUS, "R313 consumes existing R273 source mapping handoff"),
        ("R273_SOURCE_MAPPING_HANDOFF_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R313 parses R273 exact/snapshot telemetry"),
        ("pending_source_mapping_handoffs",
         DX11_CENSUS_ANALYZER, "R313 tracks unnumbered R273 per log and epoch"),
        ("source_mapping_handoffs[signature_key]",
         DX11_CENSUS_ANALYZER, "R313 correlates R273 to following R276"),
        ('"register_mapping_plan_correlated":',
         DX11_CENSUS_ANALYZER, "R313 checks R272 prerequisite"),
        ('"identity_link_strength": (',
         DX11_CENSUS_ANALYZER, "R313/R314 classifies rebuilt producer identity"),
        ('"SourceMappingHandoff": source_mapping_handoff',
         DX11_CENSUS_ANALYZER, "R313 exposes diagnostic-only evidence"),
        ("r313_good = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R313 exact ordered handoff regression"),
        ("check_r313_inexact(",
         DX11_CENSUS_ANALYZER_TEST, "R313 negative handoff regressions"),
        ('r313_evidence["activation_proof"] is False',
         DX11_CENSUS_ANALYZER_TEST, "R313 cannot activate a native draw"),
    ]
    missing_r313_programmable_source_mapping_handoff_analyzer_bridge = [
        meaning for token, source, meaning
        in r313_programmable_source_mapping_handoff_analyzer_bridge
        if token not in source
    ]
    if missing_r313_programmable_source_mapping_handoff_analyzer_bridge:
        raise SystemExit(
            "DX11 R313 source mapping handoff analyzer drift: "
            + ", ".join(
                missing_r313_programmable_source_mapping_handoff_analyzer_bridge
            )
        )

    r311_programmable_register_mapping_plan_analyzer_bridge = [
        ("VR DX11 R272 registerMappingPlan",
         RUNTIME_CENSUS, "R311 consumes the existing R272 register mapping plan"),
        ("R272_REGISTER_MAPPING_PLAN_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R311 parses R272 register mapping evidence"),
        ("pending_register_mapping_plans",
         DX11_CENSUS_ANALYZER, "R311 binds unnumbered R272 to following R276 signature"),
        ('"mapping_identity_present":',
         DX11_CENSUS_ANALYZER, "R311 checks mapping hashes/revision/contract presence"),
        ('"source_semantic_pair_correlated":',
         DX11_CENSUS_ANALYZER, "R311 correlates exact R272 with R271"),
        ('"RegisterMappingPlan": register_mapping_plan',
         DX11_CENSUS_ANALYZER, "R311 attaches R272 evidence to the exact signature"),
        ("pending_register_mapping_plans.pop(",
         DX11_CENSUS_ANALYZER, "R312 invalidates stale R272 on a new R271 producer"),
        ('"producer_order_valid": producer_order_valid',
         DX11_CENSUS_ANALYZER, "R312 records unique R271-to-R272 producer order"),
        ('and register_mapping_plan["producer_order_valid"]',
         DX11_CENSUS_ANALYZER, "R312 fails closed on ambiguous mapping order"),
        ("r312_ambiguous_register_mapping = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R312 duplicate-producer regression"),
        ("r312_stale_register_mapping = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R312 stale-producer regression"),
        ("r311_register_mapping_plan = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R311 exact register-mapping fixture"),
        ("r311_inconsistent_register_mapping = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R311 zero-revision inconsistency fixture"),
        ('r311_evidence["activation_proof"] is False',
         DX11_CENSUS_ANALYZER_TEST, "R311 analyzer evidence cannot activate draw"),
    ]
    missing_r311_programmable_register_mapping_plan_analyzer_bridge = [
        meaning for token, source, meaning
        in r311_programmable_register_mapping_plan_analyzer_bridge
        if token not in source
    ]
    if missing_r311_programmable_register_mapping_plan_analyzer_bridge:
        raise SystemExit(
            "DX11 R311 programmable register-mapping analyzer drift: "
            + ", ".join(
                missing_r311_programmable_register_mapping_plan_analyzer_bridge
            )
        )

    r310_programmable_source_semantic_pair_analyzer_bridge = [
        ("VR DX11 R271 sourceSemanticPair",
         RUNTIME_CENSUS, "R310 consumes the existing R271 source semantic pair"),
        ("R271_SOURCE_SEMANTIC_PAIR_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R310 parses R271 source semantic evidence"),
        ("pending_source_semantic_pairs",
         DX11_CENSUS_ANALYZER, "R310 binds unnumbered R271 to following R276 signature"),
        ('"object_prerequisite_correlated":',
         DX11_CENSUS_ANALYZER, "R310 correlates R271 cache identity with R279"),
        ('"SourceSemanticPair": source_semantic_pair',
         DX11_CENSUS_ANALYZER, "R310 attaches R271 evidence to the exact signature"),
        ("r310_source_semantic_pair = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R310 exact source-semantic-pair fixture"),
        ("r310_inconsistent_source_semantic_pair = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R310 mismatched cache-key fixture"),
        ('r310_evidence["activation_proof"] is False',
         DX11_CENSUS_ANALYZER_TEST, "R310 analyzer evidence cannot activate draw"),
    ]
    missing_r310_programmable_source_semantic_pair_analyzer_bridge = [
        meaning for token, source, meaning
        in r310_programmable_source_semantic_pair_analyzer_bridge
        if token not in source
    ]
    if missing_r310_programmable_source_semantic_pair_analyzer_bridge:
        raise SystemExit(
            "DX11 R310 programmable source-semantic-pair analyzer drift: "
            + ", ".join(
                missing_r310_programmable_source_semantic_pair_analyzer_bridge
            )
        )

    r309_programmable_production_observation_analyzer_bridge = [
        ("VR DX11 R287 productionObservation",
         RUNTIME_CENSUS, "R309 consumes the existing R287 production observation"),
        ("R287_PRODUCTION_OBSERVATION_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R309 parses R287 production observation evidence"),
        ('"target_materialization_correlated":',
         DX11_CENSUS_ANALYZER, "R309 correlates exact R287 with R283 materialization"),
        ('"translated_semantic_receipt_correlated":',
         DX11_CENSUS_ANALYZER, "R309 correlates exact R287 with R275 semantic receipt"),
        ('"ProductionObservation": production_observation',
         DX11_CENSUS_ANALYZER, "R309 attaches R287 evidence to the exact signature"),
        ("r309_production_observation = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R309 exact production-observation fixture"),
        ("r309_inconsistent_production_observation = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R309 inconsistent production-observation fixture"),
        ('r309_evidence["activation_proof"] is False',
         DX11_CENSUS_ANALYZER_TEST, "R309 analyzer evidence cannot activate draw"),
    ]
    missing_r309_programmable_production_observation_analyzer_bridge = [
        meaning for token, source, meaning
        in r309_programmable_production_observation_analyzer_bridge
        if token not in source
    ]
    if missing_r309_programmable_production_observation_analyzer_bridge:
        raise SystemExit(
            "DX11 R309 programmable production-observation analyzer drift: "
            + ", ".join(
                missing_r309_programmable_production_observation_analyzer_bridge
            )
        )

    r308_programmable_production_semantic_review_analyzer_bridge = [
        ("VR DX11 R291 productionSemanticReview",
         RUNTIME_CENSUS, "R308 consumes the existing R291 production semantic review"),
        ("R291_PRODUCTION_SEMANTIC_REVIEW_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R308 parses R291 production semantic evidence"),
        ('"admission_snapshot_correlated":',
         DX11_CENSUS_ANALYZER, "R308 correlates R288 admission token presence"),
        ('"review_state_correlated": review_state_correlated',
         DX11_CENSUS_ANALYZER, "R308 correlates R289 readiness and token state"),
        ('"ProductionSemanticReview": production_semantic_review',
         DX11_CENSUS_ANALYZER, "R308 attaches R291 evidence to the exact signature"),
        ("r308_production_semantic_review = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R308 exact production semantic-review fixture"),
        ("r308_inconsistent_semantic_review = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R308 inconsistent semantic-review fixture"),
        ('r308_evidence["activation_proof"] is False',
         DX11_CENSUS_ANALYZER_TEST, "R308 analyzer evidence cannot activate draw"),
    ]
    missing_r308_programmable_production_semantic_review_analyzer_bridge = [
        meaning for token, source, meaning
        in r308_programmable_production_semantic_review_analyzer_bridge
        if token not in source
    ]
    if missing_r308_programmable_production_semantic_review_analyzer_bridge:
        raise SystemExit(
            "DX11 R308 programmable production semantic-review analyzer drift: "
            + ", ".join(
                missing_r308_programmable_production_semantic_review_analyzer_bridge
            )
        )

    r307_programmable_production_source_revalidation_analyzer_bridge = [
        ("VR DX11 R297 productionSourceRevalidation",
         RUNTIME_CENSUS, "R307 consumes the existing R297 production source record"),
        ("R297_PRODUCTION_SOURCE_REVALIDATION_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R307 parses R297 production source evidence"),
        ('"observable_mask_matches": observable_mask_matches',
         DX11_CENSUS_ANALYZER, "R307 correlates observable missing-evidence mask bits"),
        ('"join_snapshot_correlated": join_snapshot_correlated',
         DX11_CENSUS_ANALYZER, "R307 correlates R294/cache readiness with R297 join token"),
        ('"receipt_absence_fail_closed": receipt_absence_fail_closed',
         DX11_CENSUS_ANALYZER, "R307 validates missing R258 remains non-promoting"),
        ('"ProductionSourceRevalidation": production_source_revalidation',
         DX11_CENSUS_ANALYZER, "R307 attaches R297 evidence to the exact signature"),
        ("r307_production_source_revalidation = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R307 production missing-R258 fail-closed fixture"),
        ("r307_inconsistent_source_revalidation = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R307 inconsistent mask/snapshot fixture"),
        ('r307_evidence["activation_proof"] is False',
         DX11_CENSUS_ANALYZER_TEST, "R307 analyzer evidence cannot activate draw"),
    ]
    missing_r307_programmable_production_source_revalidation_analyzer_bridge = [
        meaning for token, source, meaning
        in r307_programmable_production_source_revalidation_analyzer_bridge
        if token not in source
    ]
    if missing_r307_programmable_production_source_revalidation_analyzer_bridge:
        raise SystemExit(
            "DX11 R307 programmable production source-revalidation analyzer drift: "
            + ", ".join(
                missing_r307_programmable_production_source_revalidation_analyzer_bridge
            )
        )

    r306_programmable_production_prerequisite_analyzer_bridge = [
        ("VR DX11 R293 productionPrerequisiteCensus",
         RUNTIME_CENSUS, "R306 consumes the existing R293 production census record"),
        ("R293_PRODUCTION_PREREQUISITE_RE = re.compile(",
         DX11_CENSUS_ANALYZER, "R306 parses R293 production prerequisite evidence"),
        ('"summary_correlation_exact": summary_correlation_exact',
         DX11_CENSUS_ANALYZER, "R306 correlates receipt mask, exactness and snapshot state"),
        ('"ProductionActivationPrerequisite":',
         DX11_CENSUS_ANALYZER, "R306 attaches R293 evidence to the exact signature"),
        ('"ProductionActivationEvidenceCoverageComplete":',
         DX11_CENSUS_ANALYZER, "R306 exports independent diagnostic evidence coverage"),
        ("r306_production_prerequisite = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R306 fail-closed R293 analyzer regression"),
        ("r306_inconsistent_prerequisite = run_case(",
         DX11_CENSUS_ANALYZER_TEST, "R306 inconsistent receipt-mask regression"),
        ('r306_evidence["activation_proof"] is False',
         DX11_CENSUS_ANALYZER_TEST, "R306 never promotes analyzer evidence to activation"),
    ]
    missing_r306_programmable_production_prerequisite_analyzer_bridge = [
        meaning for token, source, meaning
        in r306_programmable_production_prerequisite_analyzer_bridge
        if token not in source
    ]
    if missing_r306_programmable_production_prerequisite_analyzer_bridge:
        raise SystemExit(
            "DX11 R306 programmable production prerequisite analyzer drift: "
            + ", ".join(
                missing_r306_programmable_production_prerequisite_analyzer_bridge
            )
        )

    r294_programmable_production_draw_identity = [
        ("enum class SourceDrawKind", RUNTIME_CENSUS_HPP,
         "R294 explicit source draw-kind identity"),
        ("struct SourceDrawObservation", RUNTIME_CENSUS_HPP,
         "R294 exact source draw-call payload"),
        ("make_nonindexed_source_draw_observation(", RUNTIME_CENSUS_HPP,
         "R294 non-indexed draw factory"),
        ("make_indexed_source_draw_observation(", RUNTIME_CENSUS_HPP,
         "R294 indexed draw factory"),
        ("make_nonindexed_up_source_draw_observation(", RUNTIME_CENSUS_HPP,
         "R294 UP draw is a distinct source kind"),
        ("make_indexed_up_source_draw_observation(", RUNTIME_CENSUS_HPP,
         "R294 indexed-UP draw is a distinct source kind"),
        ("source_draw_identity_snapshot_token(", RUNTIME_CENSUS,
         "R294 tamper-evident source draw identity"),
        ("token = hash_mix(token, 0x294u);", RUNTIME_CENSUS,
         "R294 independent snapshot-domain tag"),
        ("sourceDrawNativeBufferEligible", RUNTIME_CENSUS,
         "R294 keeps UP memory draws ineligible for native-buffer evidence"),
        ("make_indexed_source_draw_observation(", D3D9_RENDER_STATE_CAPTURE,
         "R294 indexed hook forwards complete draw range"),
        ("baseVertexIndex, minVertexIndex, numVertices", D3D9_RENDER_STATE_CAPTURE,
         "R294 indexed source range is not discarded"),
        ("make_indexed_up_source_draw_observation(", D3D9_RENDER_STATE_CAPTURE,
         "R294 indexed UP hook remains explicitly separate"),
        ("productionSourceRevalidation = nullptr", RUNTIME_CENSUS,
         "R294 does not fabricate R258 from draw identity alone"),
    ]
    missing_r294_programmable_production_draw_identity = [
        meaning for token, source, meaning
        in r294_programmable_production_draw_identity
        if token not in source
    ]
    if missing_r294_programmable_production_draw_identity:
        raise SystemExit(
            "DX11 R294 programmable production draw-identity drift: "
            + ", ".join(missing_r294_programmable_production_draw_identity)
        )

    r295_programmable_production_source_revalidation_join = [
        ("ProgrammableProductionSourceRevalidationCensusEvidence",
         RUNTIME_CENSUS, "R295 explicit production source-revalidation join evidence"),
        ("review_programmable_production_source_revalidation(",
         RUNTIME_CENSUS, "R295 bounded R294-to-R258 join review"),
        ("kSourceDrawIdentityMissing",
         RUNTIME_CENSUS, "R295 explicit missing R294 identity bit"),
        ("kNativeBufferEligibilityMissing",
         RUNTIME_CENSUS, "R295 explicit native-buffer eligibility bit"),
        ("kSourceRevalidationReceiptMissing",
         RUNTIME_CENSUS, "R295 explicit missing R258 receipt bit"),
        ("sourceRevalidation->kind == expectedKind",
         RUNTIME_CENSUS, "R295 R258 draw-kind lineage gate"),
        ("sourceRevalidation->startLocation ==",
         RUNTIME_CENSUS, "R295 R258 source-start lineage gate"),
        ("kSourceElementCountMissing",
         RUNTIME_CENSUS, "R295 explicit source element-count evidence bit"),
        ("source_draw_element_count(",
         RUNTIME_CENSUS, "R295 primitive-to-element-count derivation"),
        ("sourceRevalidation->elementCount == out.sourceElementCount",
         RUNTIME_CENSUS, "R295 R258 element-count lineage gate"),
        ("shaderProductionSourceElementCountMatches",
         RUNTIME_CENSUS, "R295 element-count match participates in sampled identity"),
        ("sampledDraw.indexFormat = indexDesc.Format",
         RUNTIME_CENSUS, "R296 captures the live D3D9 indexed-buffer format"),
        ("sourceRevalidation->indexFormat == out.sourceIndexFormat",
         RUNTIME_CENSUS, "R296 requires exact R258 index-format lineage"),
        ("sourceRevalidation->indexOffset == 0u",
         RUNTIME_CENSUS, "R296 requires D3D9-equivalent zero index binding offset"),
        ("shaderProductionSourceIndexFormatMatches",
         RUNTIME_CENSUS, "R296 index-format match participates in sampled identity"),
        ("shaderProductionSourceIndexOffsetMatches",
         RUNTIME_CENSUS, "R296 index-offset match participates in sampled identity"),
        ("sourceRevalidation->baseVertexIndex ==",
         RUNTIME_CENSUS, "R297 exact R258 indexed base-vertex lineage"),
        ("sourceRevalidation->minVertexIndex ==",
         RUNTIME_CENSUS, "R297 exact R258 indexed min-vertex lineage"),
        ("sourceRevalidation->numVertices ==",
         RUNTIME_CENSUS, "R297 exact R258 indexed vertex-count lineage"),
        ("shaderProductionSourceRangeMatches",
         RUNTIME_CENSUS, "R297 source-range join participates in sampled identity"),
        ("VR DX11 R297 productionSourceRevalidation",
         RUNTIME_CENSUS, "R297 bounded diagnostic output"),
        ("sourceRevalidation->cacheKey == expectedCacheKey",
         RUNTIME_CENSUS, "R295 shader-pair cache lineage gate"),
        ("token = hash_mix(token, 0x295u);",
         RUNTIME_CENSUS, "R295 independent snapshot-domain tag"),
        ("productionSourceRevalidation = nullptr",
         RUNTIME_CENSUS, "R295 current production path cannot fabricate R258"),
        ("shaderProductionSourceJoinExact",
         RUNTIME_CENSUS, "R295 join result participates in sampled identity"),
        ("shaderProductionSourceMissingEvidenceMask",
         RUNTIME_CENSUS, "R295 missing evidence participates in sampled identity"),
    ]
    missing_r295_programmable_production_source_revalidation_join = [
        meaning for token, source, meaning
        in r295_programmable_production_source_revalidation_join
        if token not in source
    ]
    if missing_r295_programmable_production_source_revalidation_join:
        raise SystemExit(
            "DX11 R295 programmable production source-revalidation join drift: "
            + ", ".join(
                missing_r295_programmable_production_source_revalidation_join
            )
        )

    r293_programmable_production_prerequisite_census_gate = [
        ("ProgrammableProductionActivationPrerequisiteCensusEvidence",
         RUNTIME_CENSUS, "R293 explicit production prerequisite census evidence"),
        ("review_programmable_production_activation_prerequisites(",
         RUNTIME_CENSUS, "R293 bounded census prerequisite gate"),
        ("kSourceRevalidationReceiptMissing",
         RUNTIME_CENSUS, "R293 explicit missing R258 receipt bit"),
        ("kResourceBehaviorReceiptMissing",
         RUNTIME_CENSUS, "R293 explicit missing R262 receipt bit"),
        ("observe_programmable_shader_production_activation_prerequisites(",
         RUNTIME_CENSUS, "R293 delegates exact complete inputs to R292"),
        ("validate_programmable_shader_production_activation_prerequisite_snapshot(",
         RUNTIME_CENSUS, "R293 validates exact R292 snapshot before success"),
        ("productionSourceRevalidation = nullptr",
         RUNTIME_CENSUS, "R293 current production census must not fabricate R258"),
        ("productionResourceBehavior = nullptr",
         RUNTIME_CENSUS, "R293 current production census must not fabricate R262"),
        ("shaderProductionActivationMissingReceiptMask",
         RUNTIME_CENSUS, "R293 missing receipt state participates in signature identity"),
        ("VR DX11 R293 productionPrerequisiteCensus",
         RUNTIME_CENSUS, "R293 bounded diagnostic output"),
    ]
    missing_r293_programmable_production_prerequisite_census_gate = [
        meaning for token, source, meaning
        in r293_programmable_production_prerequisite_census_gate
        if token not in source
    ]
    if missing_r293_programmable_production_prerequisite_census_gate:
        raise SystemExit(
            "DX11 R293 programmable production prerequisite census drift: "
            + ", ".join(
                missing_r293_programmable_production_prerequisite_census_gate
            )
        )

    r259_programmable_activation_prerequisite_contract = [
        ("struct NativeProgrammableShaderActivationPrerequisiteHandoff",
         NATIVE_BACKEND_HPP, "R259 explicit prerequisite review handoff type"),
        ("compose_programmable_activation_prerequisite_handoff(",
         NATIVE_BACKEND_HPP, "R259 prerequisite handoff declaration"),
        ("validate_programmable_activation_prerequisite_handoff_snapshot(",
         NATIVE_BACKEND_HPP, "R259 review snapshot validator declaration"),
        ("resourceBehaviorPayloadSnapshotMatches",
         NATIVE_BACKEND_HPP, "R304 R259 exposes R262 payload-integrity result"),
        ("recompute_programmable_output_resource_behavior_payload_snapshot(",
         NATIVE_BACKEND_CPP, "R304 shared R259 gate reconstructs exact R262 payload"),
        ("out.resourceBehaviorPayloadSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R304 R259 requires R262 payload self-integrity"),
        ("out.resourceBehaviorGeometryProofPresent =",
         NATIVE_BACKEND_CPP, "R259 consumes R261-carried geometry resource-behavior evidence"),
        ("out.resourceBehaviorTextureProofPresent =",
         NATIVE_BACKEND_CPP, "R259 consumes R262-carried exact texture resource-behavior evidence"),
        ("out.resourceBehaviorOutputProofPresent =",
         NATIVE_BACKEND_CPP, "R259 consumes R262 exact output resource-behavior evidence"),
        ("out.resourceBehaviorCoverageComplete =",
         NATIVE_BACKEND_CPP, "R259 requires complete geometry/texture/output F18 coverage"),
        ("out.resourceBehaviorProofPresent =",
         NATIVE_BACKEND_CPP, "R259 full F18 proof remains separately gated"),
        ("out.shaderTranslationReviewReady =",
         NATIVE_BACKEND_CPP, "R259 consumes R263 semantic-translation review"),
        ("out.shaderTranslationSnapshotMatches =",
         NATIVE_BACKEND_CPP, "R259 requires exact current R263 semantic snapshot"),
        ("out.shaderTranslationProofPresent =",
         NATIVE_BACKEND_CPP, "R259 consumes exact F21 shader semantic proof"),
        ("out.activationSnapshotToken = 0;",
         NATIVE_BACKEND_CPP, "R259 cannot manufacture activation authority"),
        ("token, 0x259u",
         NATIVE_BACKEND_CPP, "R259 independent review snapshot-domain tag"),
        ("R259 indexed review handoff consumes exact F18+F21 while activation remains fail-closed",
         CONSTANT_BUFFER_PROBE, "R259 indexed full-F18/F21 static-prerequisite regression"),
        ("R304 rejects R262 payload drift at shared R259 prerequisite gate",
         CONSTANT_BUFFER_PROBE, "R304 direct R262-to-R259 payload tamper regression"),
        ("R259 rejects stale R258 source-revalidation identity",
         CONSTANT_BUFFER_PROBE, "R259 stale R258 receipt regression"),
        ("R259 rejects stale R262 resource-behavior identity",
         CONSTANT_BUFFER_PROBE, "R259 stale R262 receipt regression"),
        ("R259 rejects stale R243 input-layout identity",
         CONSTANT_BUFFER_PROBE, "R259 stale input-layout receipt regression"),
        ("R259 rejects stale R263 shader semantic-translation identity",
         CONSTANT_BUFFER_PROBE, "R259 stale R263 semantic receipt regression"),
        ("R259 non-indexed review handoff consumes exact F18+F21 while activation remains fail-closed",
         CONSTANT_BUFFER_PROBE, "R259 non-indexed full-F18/F21 static-prerequisite regression"),
    ]
    missing_r259_programmable_activation_prerequisite = [
        meaning for token, source, meaning
        in r259_programmable_activation_prerequisite_contract
        if token not in source
    ]
    if missing_r259_programmable_activation_prerequisite:
        raise SystemExit(
            "DX11 R259 programmable activation-prerequisite drift: "
            + ", ".join(missing_r259_programmable_activation_prerequisite)
        )

    source_hygiene_marker = "[" + "executed on device:"
    source_hygiene_contract = [
        (NATIVE_BACKEND_HPP, "native backend header"),
        (NATIVE_BACKEND_CPP, "native backend implementation"),
        (CONSTANT_BUFFER_PROBE, "constant-buffer probe"),
    ]
    contaminated_source_hygiene = [
        meaning for source, meaning in source_hygiene_contract
        if source_hygiene_marker in source
    ]
    if contaminated_source_hygiene:
        raise SystemExit(
            "DX11 remote execution transcript contamination: "
            + ", ".join(contaminated_source_hygiene)
        )

    verify_dx11_activation_boundary()

    print(f"DX11 source graph: OK ({len(cpp_files)} translation units compiled)")


if __name__ == "__main__":
    main()