#!/usr/bin/env python3
"""Fail closed when checked-in CMake omits native DX11 translation/census TUs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DX11 = ROOT / "src" / "vr" / "d3d11"
CMAKE = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")


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
    census_contract = {
        "resourceIntrospectionComplete": "sample-level fail-closed resource observation",
        "ResourceIntrospectionFailureSamples": "durable failure counter",
        "bool resourcesExact = signature.resourceIntrospectionComplete;": "exactness starts from observation completeness",
        "if (!signature.resourceIntrospectionComplete)": "durable failure accounting gate",
        "if (unsupported == PipelineUnsupportedNone && topology.exact && resourcesExact)": "exact sample fail-closed gate",
        "GetStreamSource": "vertex-buffer observation",
        "GetRenderTarget": "render-target observation",
        "GetDepthStencilSurface": "depth observation",
        "GetIndices": "index-buffer observation",
        "GetTexture": "texture observation",
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
    }
    missing_resource_contract = [
        meaning
        for token, meaning in resource_contract.items()
        if token not in resource_translation
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
        "R7[23] census": "R72/R73 summary compatibility",
    }
    missing_analyzer = [
        meaning for token, meaning in analyzer_contract.items() if token not in analyzer
    ]
    if missing_analyzer:
        raise SystemExit(
            "DX11 analyzer resource evidence drift: " + ", ".join(missing_analyzer)
        )

    print(f"DX11 source graph: OK ({len(cpp_files)} translation units compiled)")


if __name__ == "__main__":
    main()
