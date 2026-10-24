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


# R236 source-to-WARP mono path: the existing full-Gate R183 executable builds
# and executes the new source adapter without enabling the live game hook.
target = (root/"src/vr/d3d11/native_linear_target_viewport.hpp").read_text(encoding="utf-8")
r236 = target.split("// R236: one D3D9 non-indexed DrawPrimitive",1)[1].split(
    "} // namespace outrun::vr::dx11",1)[0]
r236_guards = (
    "primitiveType != D3DPT_TRIANGLELIST",
    "primitiveCount > (std::numeric_limits<UINT>::max)() / 3u",
    "const UINT vertexCount = primitiveCount * 3u;",
    "verified_linear_pipeline_identity_ready(",
    "verified_linear_full_target_draw_ready(",
    "outputs[0] == expectedRtv && !depth",
    "if (outputs[slot]) isolated = false;",
    "if (output) output->Release();",
    "sampleMask != D3D11_DEFAULT_SAMPLE_MASK",
    "if (predicate) return false;",
    "context->SOGetTargets(",
)
def r236_contract(source):
    return all(term in source for term in r236_guards)
assert r236_contract(r236), "R236 D3D9 source/native mono integration incomplete"
for token in r236_guards:
    assert not r236_contract(r236.replace(token,"",1)), "R236 negative mutant survived: " + token
for token in (
    "R236 valid nonzero D3D9 DrawPrimitive source command",
    "R236 reject D3D9 source VB overrun",
    "R236 reject D3D9 primitive overflow",
    "R236 reject stale source version",
    "R236 reject missing native PS",
    "R236 reject foreign second eye",
    "ctx->Draw(3u,0u);",
    "R236 first source triangle misses WARP eye",
    "ctx->Draw(3u,3u);",
    "R236 D3D9 DrawPrimitive -> WARP Draw(3,3) red pixel",
    "R236 reject released source VB ownership",
):
    assert token in probe, "missing R236 WARP integration proof: " + token
assert "->Draw(" not in r236 and "->DrawIndexed(" not in r236, "gameplay native Draw forbidden"
print("R236 nonindexed D3D9 source to native mono Draw WARP + 11 mutants: PASS")


# R237 transient DrawPrimitiveUP source ownership -> R236 pipeline -> WARP GPU
# evidence. No production header is allowed to issue a Draw call.
up = (root/"src/vr/d3d11/native_d3d9_up_triangle_batch.hpp").read_text(encoding="utf-8")
r237_guards = (
    "reset(); // A failed re-capture",
    "primitiveType != D3DPT_TRIANGLELIST",
    "primitiveCount > (std::numeric_limits<UINT>::max)() / 3u",
    "vertexStride > (std::numeric_limits<UINT>::max)() / vertexCount",
    "sourceByteLength < neededBytes",
    "vertex_.initialize(device, ResourceRole::Vertex",
    "generation != generation_ || snapshotVersion != snapshot_version_",
    "!vertex_.bind(context, generation, snapshotVersion)",
    "verified_d3d9_nonindexed_triangles_ready(",
)
def r237_contract(source):
    return all(x in source for x in r237_guards)
assert r237_contract(up), "R237 UP source immutable VB/mono pipeline integration incomplete"
for guard in r237_guards:
    assert not r237_contract(up.replace(guard,"",1)), "R237 guard mutant survived: " + guard
assert "->Draw(" not in up and "->DrawIndexed(" not in up, "R237 live Draw forbidden"
for label in (
    "R237 reject null D3D9 UP source",
    "R237 reject undersized D3D9 UP source span",
    "R237 reject unexpanded source topology",
    "R237 reject empty D3D9 UP draw",
    "R237 reject zero source stride",
    "R237 reject primitive-count overflow",
    "R237 reject byte-width overflow",
    "R237 copy D3D9 UP user vertices into native D3D11 VB",
    "R237 reject stale D3D9 UP generation",
    "R237 reject stale D3D9 UP snapshot",
    "R237 reject absent programmable native pixel shader",
    "R237 reject foreign second-eye RTV",
    "ctx->Draw(3u,0u);",
    "R237 captured DrawPrimitiveUP -> native WARP red pixel",
    "R237 retired UP batch cannot authorize stale Draw",
):
    assert label in probe, "R237 WARP proof missing: " + label
assert "for (auto& point : r237Vertices) point={3.f,3.f};" in probe, (
    "R237 UP source mutation isolation not tested")
print("R237 DrawPrimitiveUP source->native VB->WARP mono pixel + 9 mutants: PASS")
