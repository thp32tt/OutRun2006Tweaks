#!/usr/bin/env python3
"""R182 scoped native D3D11 DrawIndexed boundary: one static pass plus mutants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "src/vr/d3d11/triangle_fan_index_buffer.hpp"
SOURCE = ROOT / "src/vr/d3d11/triangle_fan_index_buffer.cpp"
PROBE = ROOT / "tools/dx11_triangle_fan_index_buffer_probe.cpp"

def exact(header: str, source: str, probe: str) -> bool:
    if "context->DrawIndexed(" in source:
        return False  # production activation boundary must remain dormant
    return all(mark in header for mark in (
        "validate_dormant_draw_indexed(", "bindingSnapshotToken",
        "ID3D11RenderTargetView* expectedColorTarget",
    )) and all(mark in source for mark in (
        "!validate_binding_snapshot(context, bindingSnapshotToken)",
        "context->IAGetVertexBuffers(0, 1, vertexBuffer.GetAddressOf()",
        "context->IAGetInputLayout(inputLayout.GetAddressOf())",
        "context->VSGetShader(vertexShader.GetAddressOf(), nullptr, nullptr)",
        "context->PSGetShader(pixelShader.GetAddressOf(), nullptr, nullptr)",
        "context->OMGetRenderTargets(",
        "targets[0] == expectedColorTarget",
        "!pixelShader || !outputExact",
        "viewportCount != 1",
        "return true;",
    )) and all(mark in probe for mark in (
        "R182 zero IA token must reject", "R182 missing PS must reject",
        "R182 missing OM target must reject", "R182 missing VB must reject",
        "R182 missing expected RTV must reject",
        "R182 guarded native DrawIndexed preconditions",
        "context->DrawIndexed(owner.index_count(), 0, 0)",
        "owner.validate_dormant_draw_indexed(",
    ))

def main() -> None:
    h, s, p = (path.read_text(encoding="utf-8")
               for path in (HEADER, SOURCE, PROBE))
    if not exact(h, s, p):
        raise SystemExit("R182 native live-DrawIndexed guard incomplete")
    for old, new in (
        ("!validate_binding_snapshot(context, bindingSnapshotToken)", "false"),
        ("!pixelShader || !outputExact", "!pixelShader"),
        ("context->IAGetInputLayout(inputLayout.GetAddressOf())", "/* removed */"),
    ):
        mutant = s.replace(old, new, 1)
        if mutant == s or exact(h, mutant, p):
            raise SystemExit("R182 source negative mutant accepted")
    print("R182 guarded native DrawIndexed source and 3 mutants: PASS")

if __name__ == "__main__":
    main()
