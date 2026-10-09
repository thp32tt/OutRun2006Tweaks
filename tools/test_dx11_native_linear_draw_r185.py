#!/usr/bin/env python3
"""R185 one-shot native non-indexed Draw fail-closed source contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
code = (root / "src/vr/d3d11/native_linear_draw_submit.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
guards = (
    "!vertexOwner.binding_exact(",
    "liveVertex.Get() != native",
    "desc.ByteWidth % stride != 0",
    "startVertex >= capacity || vertexCount > capacity - startVertex",
    "topology != D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST",
    "vertexCount % 3u != 0",
    "if (!layout || !vs || !ps || !rtv)",
    "objectDevice.Get() != device.Get()",
    "return true;",
)
def contract(source):
    return all(source.count(token) >= 1 for token in guards)

assert contract(code), "R185 owner/bounds/pipeline readiness contract incomplete"
assert "->Draw(" not in code and "->DrawIndexed(" not in code, "native activation boundary crossed"
for token in (
    "!vertexOwner.binding_exact(",
    "startVertex >= capacity || vertexCount > capacity - startVertex",
    "if (!layout || !vs || !ps || !rtv)",
):
    assert not contract(code.replace(token, "", 1)), "negative mutant escaped: " + token

for token in (
    "verified_linear_draw_ready(vb,ctx.Get(),0,3,generation,version)",
    "linear Draw GPU pixel readback",
    "ctx->Draw(3,0);",
    "linear Draw stale snapshot rejected",
    "linear Draw missing PS rejected",
    "linear Draw missing RT rejected",
):
    assert token in probe, "missing isolated WARP proof: " + token
print("R185 native linear Draw readiness + 3 mutants + isolated WARP dispatch: PASS")
