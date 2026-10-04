[Reading 1000 lines from start (total: 9098 lines, 8098 remaining)]

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

[executed on device: n100 (532e2e0c-a118-4e4d-bd8d-a52d93661113)]