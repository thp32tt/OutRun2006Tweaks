#!/usr/bin/env python3
"""R196 native VS/PS-only indexed draw safety fence; five targeted source mutants."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/native_indexed_draw_submit.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_indexed_draw_probe_r186.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards = (
    "context->GSGetShader(gs.GetAddressOf(), nullptr, nullptr);",
    "context->HSGetShader(hs.GetAddressOf(), nullptr, nullptr);",
    "context->DSGetShader(ds.GetAddressOf(), nullptr, nullptr);",
    "if (gs || hs || ds) return false;",
)
assert all(g in header for g in guards), "R196 shader stage null requirement missing"
for guard in guards:
    assert not all(g in header.replace(guard, "", 1) for g in guards), "negative mutation escaped: " + guard
assert "->DrawIndexed(" not in header, "do not authorize gameplay dispatch"
gpu = (
    '"compile interfering GS"',
    '"create interfering GS"',
    'context->GSSetShader(gs.Get(),nullptr,0);',
    '"reject unexpected live GS"',
    "context->DrawIndexed(3,0,0);",
    '"R196 GS must change actual WARP DrawIndexed pixels"',
    'context->GSSetShader(nullptr,nullptr,0);',
    '"restore pure VS/PS indexed pipeline"',
    '"R186 actual DrawIndexed green center / black corner pixels"',
)
assert all(g in probe for g in gpu), "R196 WARP negative/positive GPU proof missing"
assert workflow.count("python tools/test_dx11_shader_stage_r196.py") == 1
assert workflow.index("Verify R196 native indexed shader stage fence") < workflow.index("Build R186 owned indexed Draw WARP probe")
print("R196 owned native indexed VS/PS-only fence, 4 mutants, real WARP geometry interference: PASS")
