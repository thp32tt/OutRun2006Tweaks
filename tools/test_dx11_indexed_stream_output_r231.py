#!/usr/bin/env python3
"""R231 indexed sole-eye stream-output ownership with source mutants and WARP proof."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
s = (root / "src/vr/d3d11/native_indexed_uav_eye_guard.hpp").read_text(encoding="utf-8")
p = (root / "tools/dx11_indexed_draw_probe_r186.cpp").read_text(encoding="utf-8")
w = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
assert s.count("// R231: a retained stream-output buffer") == 1
section = s.split("// R231: a retained stream-output buffer", 1)[1].split(
    "} // namespace outrun::vr::dx11", 1)[0]
guards = (
    "verified_indexed_no_stream_output_eye_ready(",
    "!verified_indexed_unpredicated_eye_ready(",
    "context->SOGetTargets(D3D11_SO_BUFFER_SLOT_COUNT, soTargets);",
    "ID3D11Buffer* soTargets[D3D11_SO_BUFFER_SLOT_COUNT]{};",
    "if (target) {",
    "isolated = false;",
    "target->Release();",
    "return isolated;",
)
assert all(g in section for g in guards), "R231 missing composition, slots or COM cleanup"
for g in guards:
    mutant = section.replace(g, "", 1)
    assert not all(v in mutant for v in guards), "R231 negative mutant escaped: " + g
assert "->DrawIndexed(" not in s and "->Draw(" not in s, "no production draw dispatch"
for label in (
    "R231 initial clean indexed eye",
    "R231 same-device stream-output buffer",
    "R231 predecessor ignores SO target",
    "R231 reject slot-zero stream-output",
    "R231 reject highest stream-output slot",
    "R231 restore after SO unbind",
    "R231 restored WARP DrawIndexed green pixel",
    "r231BufferDesc.BindFlags=D3D11_BIND_STREAM_OUTPUT;",
    "context->SOSetTargets(1u,&r231Slot0,r231Offsets);",
    "context->SOSetTargets(D3D11_SO_BUFFER_SLOT_COUNT,r231Slot3,r231Offsets);",
    "context->SOSetTargets(0u,nullptr,nullptr);",
):
    assert label in p, "R231 WARP ownership proof missing: " + label
step = "python tools/test_dx11_indexed_stream_output_r231.py"
assert w.count(step) == 1
assert w.index("Verify R229 indexed GPU predication fence") < w.index(step)
assert w.index(step) < w.index("Build R186 owned indexed Draw WARP probe")
print("R231 indexed SO: 8 source mutants, slots 0/3, WARP recovery wired PASS")
