#!/usr/bin/env python3
"""Fail closed when checked-in CMake omits native DX11 translation/census TUs."""

from pathlib import Path
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
SURFACE_MIRROR_HPP = (
    ROOT / "src" / "vr" / "d3d11" / "surface_mirror.hpp"
).read_text(encoding="utf-8")
SURFACE_MIRROR_CPP = (
    ROOT / "src" / "vr" / "d3d11" / "surface_mirror.cpp"
).read_text(encoding="utf-8")
SURFACE_MIRROR_PROBE = (
    ROOT / "tools" / "dx11_surface_mirror_probe.cpp"
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
CONSTANT_BUFFER_CONTRACT_TEXT = (
    CONSTANT_BUFFER_PROBE + "\n" + NATIVE_BACKEND_CPP
)


def main() -> None:
    verify_dx11_dual_source_contract()
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
        "resourcesExact && inputLayoutExact && shaderTranslationExact": "R80 exact-sample shader readiness gate",
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
        "D3DSAMP_ADDRESSU": "R81 per-stage sampler U addressing observation",
        "D3DSAMP_ADDRESSV": "R81 per-stage sampler V addressing observation",
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
        "FixedFunctionShaderCompileSkippedSignatureCap": "R85 bounded instrumentation cap",
        "compile_fixed_function_pixel_shader_prototype": "R85 census compiler probe invocation",
        "SignatureHashCap = 512u": "R114 bounded unique-signature hash cap",
        "DetailedSignatureLogCap = 64u": "R114 bounded detailed-signature log cap",
        "SignatureHashCapHitSamples": "R114 signature hash-cap saturation evidence",
        "DetailedSignatureLogSkippedSignatures": "R114 detailed-log saturation evidence",
        "mix_sample_ordinal": "R114 hashed draw-ordinal sampler",
        "(sampleKey & (sampleStride - 1u)) != 0u": "R114 hashed sampled-mode gate",
        "sampleStride > 1u": "R114 exhaustive-mode sampling bypass gate",
        "unique <= DetailedSignatureLogCap": "R114 compile instrumentation uses named detail cap",
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
    }
    missing_surface_mirror_contract += [
        meaning
        for token, meaning in probe_contract.items()
        if token not in SURFACE_MIRROR_PROBE
    ]
    if missing_surface_mirror_contract:
        raise SystemExit(
            "DX11 dormant surface-mirror contract drift: "
            + ", ".join(missing_surface_mirror_contract)
        )


    dual_source_blend_contract = {
        "case D3DBLEND_SRCCOLOR2: return {D3D11_BLEND_SRC1_COLOR, false};":
            "dual-source source-color blend stays fail-closed without SV_Target1 proof",
        "case D3DBLEND_INVSRCCOLOR2: return {D3D11_BLEND_INV_SRC1_COLOR, false};":
            "inverse dual-source source-color blend stays fail-closed without SV_Target1 proof",
    }
    missing_dual_source_blend_contract = [
        meaning
        for token, meaning in dual_source_blend_contract.items()
        if token not in STATE_TRANSLATION_CPP
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
        "triangle fan expansion overflow did not fail closed":
            "fan overflow negative semantic smoke",
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
        "R(?:7[23456789]|8[012345]|114) census": "R72 through R85 plus R114 summary compatibility",
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
        "output.diffuse = input.diffuse": "R93 diffuse propagation",
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
        "R93 normal/lighting path must fail closed": "R93 normal/lighting negative case",
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

    for forbidden, meaning in {
        "IASetInputLayout": "input-layout binding",
        "VSSetShader(": "vertex-shader binding",
        "PSSetShader(": "pixel-shader binding",
    }.items():
        if forbidden in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R97 bundle must remain non-routing; found " + meaning
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

    if "PSSetSamplers(" in NATIVE_BACKEND_CPP:
        raise SystemExit(
            "DX11 R98 sampler owner must remain non-routing; found PSSetSamplers binding"
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

    if "PSSetShaderResources(" in NATIVE_BACKEND_CPP:
        raise SystemExit(
            "DX11 R99 texture view must remain non-routing; "
            "found PSSetShaderResources binding"
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
    if '"src/vr/d3d11/resource_translation.cpp"' not in constant_probe_source_block:
        raise SystemExit(
            "DX11 R99 constant-buffer probe generated CMake must link "
            "resource_translation.cpp"
        )

    constant_probe_toml_block = CMAKE_TOML.split(
        "[target.dx11_constant_buffer_probe]", 1
    )[-1].split("[target.", 1)[0]
    if '"src/vr/d3d11/resource_translation.cpp"' not in constant_probe_toml_block:
        raise SystemExit(
            "DX11 R99 constant-buffer probe cmake.toml must link "
            "resource_translation.cpp"
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

    r117_draw_readiness_header = {
        "struct NativeFixedFunctionDrawReadiness":
            "R117 composite draw readiness",
        "bool renderStateReady{}":
            "R117 explicit render-state readiness",
        "std::uint64_t renderStateSnapshotToken{}":
            "R117 render-state snapshot identity",
        "compose_fixed_function_draw_readiness(":
            "R117 fail-closed draw readiness composition API",
        "validate_fixed_function_draw_snapshot(":
            "R117 composite draw snapshot validator",
    }
    missing_r117_header = [
        meaning
        for token, meaning in r117_draw_readiness_header.items()
        if token not in NATIVE_BACKEND_HPP
    ]
    if missing_r117_header:
        raise SystemExit(
            "DX11 R117 draw-readiness header drift: "
            + ", ".join(missing_r117_header)
        )

    for token, meaning in {
        "activation.ready && activation.snapshotToken != 0":
            "R117 activation snapshot prerequisite",
        "renderState.ready && renderState.snapshotToken != 0":
            "R117 render-state snapshot prerequisite",
        "out.componentSnapshotsPresent =":
            "R117 explicit component-token aggregation",
        "drawToken, out.activationSnapshotToken":
            "R117 activation identity in draw token",
        "drawToken, out.renderStateSnapshotToken":
            "R117 render-state identity in draw token",
    }.items():
        if token not in NATIVE_BACKEND_CPP:
            raise SystemExit(
                "DX11 R117 draw-readiness source drift: " + meaning
            )

    for token, meaning in {
        "R117 draw readiness composes activation and render-state snapshots":
            "R117 positive composition proof",
        "R117 draw readiness fails closed on missing component evidence":
            "R117 missing-evidence fail-closed proof",
        "R117 draw snapshot changes with render-state identity":
            "R117 render-state identity invalidation proof",
        "DX11 fixed-function draw readiness composition R117: PASS":
            "R117 hosted probe completion marker",
    }.items():
        if token not in CONSTANT_BUFFER_PROBE:
            raise SystemExit(
                "DX11 R117 draw-readiness probe drift: " + meaning
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

    verify_dx11_activation_boundary()

    print(f"DX11 source graph: OK ({len(cpp_files)} translation units compiled)")


if __name__ == "__main__":
    main()
