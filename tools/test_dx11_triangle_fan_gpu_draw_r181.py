#!/usr/bin/env python3
"""R181 single-pass source contract: actual offscreen native DrawIndexed."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tools/dx11_triangle_fan_index_buffer_probe.cpp"
GATE = ROOT / ".github/workflows/backend-conversion-gate.yml"
MANIFEST = ROOT / "cmake.toml"

def exact(source: str) -> bool:
    section = source.split("void prove_fan_gpu_pixels(", 1)[-1]
    section = section.split("} // namespace", 1)[0]
    return all(x in section for x in (
        "D3DCompile(", "CreateVertexShader(", "CreatePixelShader(",
        "CreateInputLayout(", "CreateBuffer(", "CreateRenderTargetView(",
        "owner.initialize_nonindexed(device, 2, 0)",
        "owner.initialize_indexed(device, 2, D3DFMT_INDEX16, 1",
        "owner.bind(context)",
        "context->DrawIndexed(owner.index_count(), 0, 0)",
        "context->CopyResource(staging.Get(), target.Get())",
        "center[0] == 255", "corner[0] == 0",
    ))

def main() -> None:
    source = PROBE.read_text(encoding="utf-8")
    manifest = MANIFEST.read_text(encoding="utf-8")
    gate = GATE.read_text(encoding="utf-8")
    if not exact(source):
        raise SystemExit("R181 WARP GPU draw pixel proof incomplete")
    segment = manifest.split("[target.dx11_triangle_fan_index_buffer_probe]", 1)[1].split("[target.", 1)[0]
    if "d3dcompiler.lib" not in segment or "d3d11.lib" not in segment:
        raise SystemExit("R181 cmkr target missing compiler or DX11 link")
    if gate.index("Run DX11 triangle-fan generated index-buffer probe") >= gate.index("Build DX11 constant buffer probe"):
        raise SystemExit("R181 must run before unrelated R175 blocker")
    for before, after in (
        ("context->DrawIndexed(owner.index_count(), 0, 0)", "/* removed */"),
        ("center[0] == 255", "center[0] == 0"),
        ("owner.initialize_indexed(device, 2, D3DFMT_INDEX16, 1", "owner.initialize_nonindexed(device, 2, 0"),
    ):
        mutant = source.replace(before, after, 1)
        if mutant == source or exact(mutant):
            raise SystemExit("R181 negative mutant accepted")
    print("R181 real WARP DrawIndexed source/order/link contract and 3 mutants: PASS")

if __name__ == "__main__":
    main()
