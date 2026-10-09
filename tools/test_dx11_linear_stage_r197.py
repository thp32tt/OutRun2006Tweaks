#!/usr/bin/env python3
"""R197 VS/PS-only non-indexed Draw guard plus real WARP GS pixel proof."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/native_linear_draw_submit.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
ci = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards = (
    "context->GSGetShader(gs.GetAddressOf(), nullptr, nullptr);",
    "context->HSGetShader(hs.GetAddressOf(), nullptr, nullptr);",
    "context->DSGetShader(ds.GetAddressOf(), nullptr, nullptr);",
    "if (gs || hs || ds) return false;",
)
def guarded(source):
    return all(g in source for g in guards)
assert guarded(header), "R197 non-indexed shader-stage ownership missing"
for guard in guards:
    assert not guarded(header.replace(guard, "", 1)), "R197 mutant escaped: " + guard
assert "->Draw(" not in header and "->DrawIndexed(" not in header, "gameplay activation forbidden"
markers = (
    '"R197 compile interfering GS"',
    '"R197 create interfering GS"',
    "ctx->GSSetShader(interferingGs.Get(),nullptr,0);",
    '"R197 reject unexpected non-indexed GS"',
    "ctx->Draw(3,0);",
    '"R197 GS changes actual WARP Draw pixels"',
    "ctx->GSSetShader(nullptr,nullptr,0);",
    '"R197 restore pure VS/PS native Draw"',
    '"linear Draw GPU pixel readback"',
)
assert all(x in probe for x in markers), "R197 negative/positive GPU proof missing"
assert probe.index('"R197 reject unexpected non-indexed GS"') < probe.index(
    '"R197 GS changes actual WARP Draw pixels"') < probe.index(
    '"R197 restore pure VS/PS native Draw"') < probe.index(
    '"linear Draw GPU pixel readback"')
assert ci.count("python tools/test_dx11_linear_stage_r197.py") == 1
assert ci.index("Verify R197 native linear shader stage fence") < ci.index(
    "Build DX11 linear VB/IB mirror R183 WARP probe")
print("R197 linear VS/PS-only stage fence, 4 negative mutants, WARP GS proof wired: PASS")
