#!/usr/bin/env python3
"""R232 dormant linear SO side-write exclusion, source mutations and GPU proof."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
s = (root / "src/vr/d3d11/native_linear_uav_eye_guard.hpp").read_text(encoding="utf-8")
p = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
w = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
assert s.count("// R232: even an otherwise unpredicated") == 1
section = s.split("// R232: even an otherwise unpredicated", 1)[1].split(
    "} // namespace outrun::vr::dx11", 1)[0]
guards = (
    "verified_linear_no_stream_output_eye_ready(",
    "!verified_linear_unpredicated_eye_ready(",
    "ID3D11Buffer* soTargets[D3D11_SO_BUFFER_SLOT_COUNT]{};",
    "context->SOGetTargets(D3D11_SO_BUFFER_SLOT_COUNT, soTargets);",
    "for (auto* target : soTargets)",
    "if (target) {",
    "isolated = false;",
    "target->Release();",
    "return isolated;",
)
assert all(g in section for g in guards), "R232 missing predecessor, SO slot census or COM cleanup"
for g in guards:
    mutant = section.replace(g, "", 1)
    assert not all(v in mutant for v in guards), "R232 negative mutant escaped: " + g
assert "->Draw(" not in s and "->DrawIndexed(" not in s, "no gameplay draw dispatch"
for label in (
    "R232 initial clean linear eye",
    "R232 same-device stream-output buffer",
    "R232 predecessor ignores SO target",
    "R232 reject slot-zero stream-output",
    "R232 reject highest stream-output slot",
    "R232 restore after SO unbind",
    "R232 restored WARP Draw paints red eye pixel",
    "r232BufferDesc.BindFlags = D3D11_BIND_STREAM_OUTPUT;",
    "ctx->SOSetTargets(1u, &r232Slot0, r232Offsets);",
    "ctx->SOSetTargets(D3D11_SO_BUFFER_SLOT_COUNT, r232Slot3, r232Offsets);",
    "ctx->SOSetTargets(0u, nullptr, nullptr);",
):
    assert label in p, "R232 WARP source probe missing: " + label
step = "python tools/test_dx11_linear_stream_output_r232.py"
assert w.count(step) == 1
assert w.index("Verify R230 non-indexed predication guard") < w.index(step)
assert w.index(step) < w.index("Build DX11 linear VB/IB mirror R183 WARP probe")
print("R232 non-indexed SO: 9 source mutants, slots 0/3, WARP recovery wired PASS")
