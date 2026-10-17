#!/usr/bin/env python3
"""Static contract checks for the DX11 triangle-fan expansion boundary.

This keeps the native backend conversion path covered without enabling runtime
rendering. The checks validate that the fan conversion contract remains
explicit and fail-closed for invalid input.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = ROOT / "src" / "vr" / "d3d11" / "triangle_fan_index_buffer.cpp"
    header = ROOT / "src" / "vr" / "d3d11" / "triangle_fan_index_buffer.hpp"

    if not source.exists() or not header.exists():
        raise SystemExit("missing triangle fan DX11 conversion files")

    text = source.read_text(encoding="utf-8")

    required = [
        "translate_triangle_fan_expansion(primitiveCount)",
        "materialize_triangle_fan_vertex_indices",
        "materialize_indexed_triangle_fan_indices",
        "D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST",
        "DXGI_FORMAT_R32_UINT",
        "sourceIndexSnapshotToken == 0",
    ]

    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit("triangle fan contract missing: " + ", ".join(missing))

    print("DX11 triangle fan index contract: OK")


if __name__ == "__main__":
    main()
