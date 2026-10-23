#!/usr/bin/env python3
"""R195 immutable indexed slice fix and WARP proof, four negative source mutants."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_linear_buffer_mirror.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
w=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "rangeTree.reset(new (std::nothrow) IndexExtrema",
    "index_range_tree_ = std::move(rangeTree);",
    "index.index_range_tree_[left++]",
    "index.index_range_tree_[--right]",
    "index_range_tree_.reset();",
    "high >= low && high < vertices",
    "!index.binding_exact(context, currentGeneration, currentIndexSnapshotVersion)",
)
def intact(x):
    return all(g in x for g in guards)
assert intact(h),"R195 immutable index slice tree/live IA contract missing"
for guard in (guards[0],guards[2],guards[3],guards[4]):
    assert not intact(h.replace(guard,"")),"negative mutant survived "+guard
assert "ctx->DrawIndexed(" not in h,"R195 must not enable gameplay Draw"
for proof in (
    "const std::uint16_t indices[] = {0,1,2,99,100,101};",
    '"valid complete index slice"',
    '"R195 reject whole IB invalid tail"',
    '"R195 reject bad tail slice"',
    '"R184 range and live IA ready before GPU"',
    "ctx->DrawIndexed(3,0,0)",
    "center[0]==255",
    "ib.shutdown()"):
    assert proof in p,"missing source-accurate WARP check "+proof
assert "python tools/test_dx11_index_slice_r195.py" in w
assert w.index("Verify R195 native indexed slice ownership") < w.index("Build DX11 linear VB/IB mirror R183 WARP probe")
print("R195 per-slice immutable tree + four mutants + WARP indexed pixel fixture: PASS")
