#!/usr/bin/env python3
"""R226 fail-closed indexed D32 eye depth-only descriptor source mutations."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=(root/"src/vr/d3d11/native_indexed_target_viewport.hpp").read_text(encoding="utf-8")
probe=(root/"tools/dx11_indexed_draw_probe_r186.cpp").read_text(encoding="utf-8")
workflow=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
r218=src.split("// R218: composed indexed full-eye D32 readiness:",1)[1]
guards=("depthDesc.Format != DXGI_FORMAT_D32_FLOAT",
        "depthDesc.Usage != D3D11_USAGE_DEFAULT",
        "depthDesc.CPUAccessFlags != 0",
        "depthDesc.MiscFlags != 0",
        "depthDesc.BindFlags != D3D11_BIND_DEPTH_STENCIL")
def checks(s): return all(g in s for g in guards)
assert checks(r218), "missing R226 dedicated D32 source guards"
for g in guards:
    assert not checks(r218.replace(g,"",1)), "R226 negative mutation survived: "+g
assert "->DrawIndexed(" not in src and "->Draw(" not in src, "game Draw activation forbidden"
for p in ("R226 WARP D32 dedicated backing descriptor",
          "R226 dedicated D32 ready",
          "R226 dedicated D32 indexed DrawIndexed green pixel"):
    assert p in probe, "WARP indexed GPU proof missing: "+p
step="python tools/test_dx11_indexed_depth_dedicated_r226.py"
assert workflow.count(step)==1, "R226 step must be unique"
assert workflow.index(step)<workflow.index("Build R186 owned indexed Draw WARP probe")
print("R226 dedicated indexed D32: PASS 5 negative source mutations + indexed GPU fixture wired")
