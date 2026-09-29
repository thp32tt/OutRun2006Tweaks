#!/usr/bin/env python3
"""Fail closed when checked-in CMake omits native DX11 translation/census TUs."""

from pathlib import Path

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
CONSTANT_BUFFER_CONTRACT_TEXT = (
    CONSTANT_BUFFER_PROBE + "\n" + NATIVE_BACKEND_CPP
)


def main() -> None:
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
        "unique <= 64": "R85 compile instrumentation remains bounded to detailed-signature cap",
        "shaderTranslationExact = false": "native shader translation remains fail-closed",
    }
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

    census_r73_contract = {
        "ResourceBehaviorUnsupportedSamples": "unmodelled descriptor counter",
        "ResourceMutationTelemetryRequiredSamples": "lock/update blocker counter",
        "ResourceManagedShadowRequiredSamples": "managed shadow blocker counter",
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
            "R30TextureLockRectVtableIndex": "Texture LockRect hook index",
            "R30TextureUnlockRectVtableIndex": "Texture UnlockRect hook index",
            "R30UpdateSurfaceVtableIndex": "UpdateSurface hook index",
            "R30UpdateTextureVtableIndex": "UpdateTexture hook index",
            "observe_texture_lock_rect": "texture LockRect bridge",
            "observe_texture_unlock_rect": "texture UnlockRect bridge",
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

    analyzer = (ROOT / "tools" / "analyze_dx11_census.py").read_text(
        encoding="utf-8"
    )
    if '"NativeDrawPathActivationAllowed": False' not in analyzer:
        raise SystemExit("DX11 census must remain observation-only")
    analyzer_contract = {
        "introspectionFailure": "resource introspection failure evidence",
        "behaviorUnsupported": "descriptor behavior evidence",
        "mutationTelemetryRequired": "lock/update blocker evidence",
        "managedShadowRequired": "managed lifetime blocker evidence",
        "R(?:7[23456789]|8[012345]) census": "R72 through R85 summary compatibility",
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

    print(f"DX11 source graph: OK ({len(cpp_files)} translation units compiled)")


if __name__ == "__main__":
    main()
