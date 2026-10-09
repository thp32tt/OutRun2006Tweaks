#!/usr/bin/env python3
"""R199 non-indexed Draw exact RTV/viewport owner and real WARP half-eye negative."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_linear_target_viewport.hpp").read_text(encoding="utf-8")
probe=(root/"tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
ci=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "verified_linear_draw_ready(",
    "!expectedTarget",
    "liveTarget.Get() != expectedTarget",
    "view.ViewDimension != D3D11_RTV_DIMENSION_TEXTURE2D",
    "desc.Width != width || desc.Height != height",
    "context->RSGetViewports(&boundCount, nullptr)",
    "boundCount != 1",
    "rasterDesc.ScissorEnable",
)
def contract(code):
    return all(token in code for token in guards)
assert contract(h), "R199 non-indexed target and viewport owner guard absent"
for token in (
    "liveTarget.Get() != expectedTarget",
    "desc.Width != width || desc.Height != height",
    "context->RSGetViewports(&boundCount, nullptr)",
    "rasterDesc.ScissorEnable",
):
    assert not contract(h.replace(token,"",1)), "R199 negative source mutant survived: "+token
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "R199 production gameplay dispatch prohibited"
for token in (
    '#include "vr/d3d11/native_linear_target_viewport.hpp"',
    '"R199 owned full linear target ready"',
    '"R199 reject null expected target"',
    '"R199 reject wrong target width"',
    '"R199 reject wrong target format"',
    '"R199 reject different-eye RTV"',
    '"R199 reject missing viewport"',
    '"R199 reject extra viewport"',
    '"R199 negative: old IA/pipeline alone accepts half viewport"',
    '"R199 reject half viewport"',
    "ctx->Draw(3,0);",
    '"R199 half viewport suppresses WARP center pixel"',
    '"R199 restore full viewport"',
    '"R199 reject scissor-enabled rasterizer"',
    '"R199 restore full RTV/viewport/scissor"',
    '"R199 final owned linear full target ready"',
    '"linear Draw GPU pixel readback"',
):
    assert token in probe, "R199 WARP negative/recovery case absent: "+token
assert probe.index('"R199 reject half viewport"') < probe.index(
    '"R199 half viewport suppresses WARP center pixel"') < probe.index(
    '"R199 restore full viewport"') < probe.index(
    '"linear Draw GPU pixel readback"')
assert ci.count("python tools/test_dx11_linear_target_r199.py")==1
assert ci.index("Verify R199 native linear target and viewport fence") < ci.index(
    "Build DX11 linear VB/IB mirror R183 WARP probe")
print("R199 non-indexed native target/viewport owner, 4 mutants, WARP pixel negative and recovery: PASS")
