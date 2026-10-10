#!/usr/bin/env python3
"""R188/R223 indexed texture UAV eye-isolation, mutation and WARP contract."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
h = (root / "src/vr/d3d11/native_indexed_texture_binding.hpp").read_text(encoding="utf-8")
p = (root / "tools/dx11_textured_indexed_probe_r188.cpp").read_text(encoding="utf-8")
manifest = (root / "cmake.toml").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards = (
    "!verified_indexed_full_target_draw_ready(",
    "psSlot >= D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT",
    "liveSrv.Get() != expectedSrv || liveSampler.Get() != expectedSampler",
    "srvDevice.Get() != device.Get()",
    "view.Texture2D.MostDetailedMip != 0 || view.Texture2D.MipLevels != 1",
    "output.Get() != source.Get()",
    "OMGetRenderTargetsAndUnorderedAccessViews(",
    "bool isolated = liveRtv[0] == expectedTarget && !liveDsv;",
    "for (auto* uav : liveUavs)",
    "if (!isolated) return false;",
)
def contract(text): return all(guard in text for guard in guards)
assert contract(h), "missing dormant indexed texture binding ownership preflight"
for guard in (guards[0], guards[2], guards[5], guards[6], guards[7], guards[8], guards[9]):
    assert not contract(h.replace(guard, "", 1)), "guard removal mutant survived: " + guard
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "game draw dispatch forbidden"
for phrase in (
    "ctx->DrawIndexed(3,0,0);", "reject rebound SRV", "reject rebound sampler",
    "reject wrong expected SRV", "reject wrong expected sampler",
    "reject wrong source format", "reject retired IB",
    "actual DrawIndexed sampled red center / black corner pixels",
    "reject hidden side-eye OM UAV", "restore UAV-free indexed texture eye",
):
    assert phrase in p, "missing isolated WARP behavioral evidence: " + phrase
assert "[target.dx11_textured_indexed_probe_r188]" in manifest
assert '"tools/dx11_textured_indexed_probe_r188.cpp"' in manifest
assert "python tools/test_dx11_textured_indexed_r188.py" in workflow
assert workflow.index("Run R188 textured indexed WARP probe") < workflow.index("Build DX11 constant buffer probe")
print("R188/R223 indexed textured eye OM UAV isolation, 7 mutants, WARP DrawIndexed: PASS")
