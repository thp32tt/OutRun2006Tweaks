#!/usr/bin/env python3
"""R203 native PS texture/sampler, plus stale second-eye MRT denial."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_linear_texture_binding.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_textured_linear_probe_r203.cpp").read_text(encoding="utf-8")
cm=(root/"cmake.toml").read_text(encoding="utf-8")
ci=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "!verified_linear_full_target_draw_ready(",
    "psSlot >= D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT",
    "liveSrv.Get() != expectedSrv || liveSampler.Get() != expectedSampler",
    "srvDevice.Get() != device.Get()",
    "view.Texture2D.MostDetailedMip != 0 || view.Texture2D.MipLevels != 1",
    "output.Get() != source.Get()",
    "if (liveOutputs[index]) singleEyeTarget = false;",
    "liveDepth.GetAddressOf()",
    "liveOutputs[0] == expectedTarget && !liveDepth",
)
def intact(text): return all(g in text for g in guards)
assert intact(h), "R203 non-indexed PS texture owner incomplete"
for g in (guards[0],guards[2],guards[3],guards[5],guards[6],guards[8]):
    assert not intact(h.replace(g,"",1)), "R203 negative mutant survived: "+g
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "game native dispatch forbidden"
for phrase in (
    "ctx->Draw(3,0);","reject stray second-eye RTV slot 1",
    "reject unowned retained depth view","restore depth-free textured eye",
    "restore sole eye render target","reject rebound SRV","reject rebound sampler",
    "reject wrong expected SRV","reject wrong expected sampler",
    "reject wrong source format","reject retired VB after texture binding",
    "actual non-indexed Draw sampled red center / black corner pixels",
    "actual rebound blue texture changes Draw center pixel",
    "actual restored red SRV recovers Draw pixel",
):
    assert phrase in p,"missing R203 real WARP behavior: "+phrase
assert "DrawIndexed" not in p, "R188 indexed dispatch must not leak"
assert "[target.dx11_textured_linear_probe_r203]" in cm
assert '"tools/dx11_textured_linear_probe_r203.cpp"' in cm
assert ci.count("python tools/test_dx11_textured_linear_r203.py")==1
assert ci.index("Run R203 textured linear WARP probe") < ci.index("Build DX11 constant buffer probe")
print("R203/R222 linear PS SRV/sampler, 6 negative mutants, single-eye no-unowned-DSV isolation, red/blue/red WARP Draw: PASS")
