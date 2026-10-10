#!/usr/bin/env python3
"""R219 one-shot OM UAV isolation, negative guard mutations and WARP wiring."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d11/native_indexed_uav_eye_guard.hpp").read_text(encoding="utf-8")
# R229 composes R219; do not let its caller name mask an R219 removal mutant.
# Keep all ten original R219 guards mandatory within the R219 definition alone.
assert src.count("// R229: R219 proves sole-eye OM ownership") == 1, "R229 guard section missing"
src = src.split("// R229: R219 proves sole-eye OM ownership", 1)[0]
probe = (root / "tools/dx11_indexed_draw_probe_r186.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards = (
    "verified_indexed_uav_isolated_eye_ready(",
    "!context || !expectedRtv || !expectedDsv",
    "!verified_indexed_sealed_opaque_eye_draw_ready(",
    "ID3D11UnorderedAccessView* liveUavs[D3D11_PS_CS_UAV_REGISTER_COUNT]{};",
    "OMGetRenderTargetsAndUnorderedAccessViews(",
    "liveRtv[0] == expectedRtv && liveDsv == expectedDsv",
    "if (liveRtv[0]) liveRtv[0]->Release()",
    "if (liveDsv) liveDsv->Release()",
    "isolated = false;",
    "uav->Release();",
)
def checks(s): return all(g in s for g in guards)
assert checks(src), "missing R219 fail-closed guard"
for guard in guards:
    assert not checks(src.replace(guard, "", 1)), "R219 negative mutant escaped: " + guard
assert "->DrawIndexed(" not in src and "->Draw(" not in src, "production activation forbidden"
for phrase in (
    "R219 old guard accepts extra OM UAV",
    "R219 new guard rejects extra OM UAV",
    "R219 WARP hidden UAV writes real second texture",
    "R219 WARP indexed RTV remains green",
    "R219 UAV unbound restores isolated eye",
    "R219 restored WARP indexed green pixel",
):
    assert phrase in probe, "missing R219 WARP case: " + phrase
step = "python tools/test_dx11_indexed_uav_eye_r219.py"
assert workflow.count(step) == 1, "R219 static verification must run once"
assert workflow.index(step) < workflow.index("Build R186 owned indexed Draw WARP probe")
print("R219 indexed OM UAV isolation: PASS 10 guard mutants, WARP cases wired")
