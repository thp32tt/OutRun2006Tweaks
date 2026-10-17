#!/usr/bin/env python3
"""Static DX11 native conversion contract regression guard.

This check is intentionally runtime-free. It verifies that the DX11 lane keeps
its native backend evidence, semantic probes, and dormant activation boundary
separate from hardware validation.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    state_path = ROOT / "docs" / "CONVERSION_LANE_STATE.json"
    require(state_path.exists(), "missing DX11 conversion state")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    require(state.get("lane") == "DX11", "wrong conversion lane")
    require(state.get("branch") == "vr-dx11-native-r71", "wrong branch contract")

    task = state.get("latest_durable_task", {})
    require(
        task.get("runtime_validation") == "UNTESTED",
        "runtime validation must not be claimed by static checks",
    )

    source_markers = {
        "src/vr/d3d11/native_backend.cpp": "Native DX11 backend source missing",
        "tools/dx11_fixed_function_shader_semantics.cpp": "semantic probe missing",
        "tools/dx11_input_layout_semantics.cpp": "input layout probe missing",
        "tools/dx11_shader_linkage_probe.cpp": "shader linkage probe missing",
    }

    for relative, message in source_markers.items():
        require((ROOT / relative).exists(), message)

    cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    for target in (
        "dx11_fixed_function_shader_semantics",
        "dx11_input_layout_semantics",
        "dx11_shader_linkage_probe",
    ):
        require(target in cmake, f"missing CMake target marker: {target}")

    print("DX11_NATIVE_CONTRACT_R72=PASS")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
