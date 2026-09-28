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
        "if (!signature.resourceIntrospectionComplete)": "exactness rejection gate",
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

    analyzer = (ROOT / "tools" / "analyze_dx11_census.py").read_text(
        encoding="utf-8"
    )
    if '"NativeDrawPathActivationAllowed": False' not in analyzer:
        raise SystemExit("DX11 census must remain observation-only")
    if "introspectionFailure" not in analyzer:
        raise SystemExit(
            "DX11 analyzer must surface resource introspection failures"
        )

    print(f"DX11 source graph: OK ({len(cpp_files)} translation units compiled)")


if __name__ == "__main__":
    main()
