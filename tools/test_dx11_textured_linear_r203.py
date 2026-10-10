#!/usr/bin/env python3
"""R203/R234 native source-to-pixel ownership with immutable SRV and OM UAV."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_linear_texture_binding.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_textured_linear_probe_r203.cpp").read_text(encoding="utf-8")
owner=(root/"src/vr/d3d11/native_linear_source_texture_r234.hpp").read_text(encoding="utf-8")
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
    "desc.Usage != D3D11_USAGE_IMMUTABLE",
    "desc.CPUAccessFlags != 0 || desc.MiscFlags != 0",
    "desc.BindFlags != D3D11_BIND_SHADER_RESOURCE",
    "OMGetRenderTargetsAndUnorderedAccessViews(",
    "for (auto* uav : liveUavs)",
    "if (!noPixelSideEffects) return false;",
)
def intact(text): return all(g in text for g in guards)
assert intact(h), "R203 non-indexed PS texture owner incomplete"
for g in (guards[0],guards[2],guards[3],guards[5],guards[6],guards[8],
          guards[9],guards[10],guards[11],guards[12],guards[13],guards[14]):
    assert not intact(h.replace(g,"",1)), "R203 negative mutant survived: "+g
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "game native dispatch forbidden"
owner_guards=(
    "sourceFormat != D3DFMT_A8B8G8R8",
    "required > static_cast<std::uint64_t>(availableBytes)",
    "desc.Usage = D3D11_USAGE_IMMUTABLE",
    "desc.BindFlags = D3D11_BIND_SHADER_RESOURCE",
    "CreateTexture2D(&desc, &data",
    "CreateShaderResourceView(",
    "generation != generation_ || sourceVersion != sourceVersion_",
    "return owner.binding_exact(context, 0u, generation, sourceVersion) &&",
    "verified_linear_textured_draw_ready(",
    "void shutdown() noexcept",
)
assert all(g in owner for g in owner_guards), "R234 connected GPU texture owner incomplete"
for g in owner_guards[:9]:
    assert not all(x in owner.replace(g,"",1) for x in owner_guards), "R234 owner deletion mutant survived: "+g
assert "->Draw(" not in owner and "->DrawIndexed(" not in owner
for phrase in (
    "ctx->Draw(3,0);","reject stray second-eye RTV slot 1",
    "reject unowned retained depth view","restore depth-free textured eye",
    "restore sole eye render target","reject rebound SRV","reject rebound sampler",
    "reject wrong expected SRV","reject wrong expected sampler",
    "reject wrong source format","reject retired VB after texture binding",
    "actual non-indexed Draw sampled red center / black corner pixels",
    "actual rebound blue texture changes Draw center pixel",
    "actual restored red SRV recovers Draw pixel",
    "R234 D3D9 snapshot -> native PS -> mono RTV ready",
    "R234 reject stale D3D9 texture source revision",
    "R234 reject mutable DEFAULT linear source",
    "R234 reject alias-capable linear source",
    "R234 restore immutable linear source",
    "R234 reject hidden linear side-eye OM UAV",
    "R234 restore UAV-free linear textured eye",
    "R234 reject retired CPU-source mirror",
):
    assert phrase in p,"missing R203 real WARP behavior: "+phrase
assert "DrawIndexed" not in p, "R188 indexed dispatch must not leak"
assert "[target.dx11_textured_linear_probe_r203]" in cm
assert '"tools/dx11_textured_linear_probe_r203.cpp"' in cm
assert ci.count("python tools/test_dx11_textured_linear_r203.py")==1
assert ci.index("Run R203 textured linear WARP probe") < ci.index("Build DX11 constant buffer probe")
print("R203/R222/R234 D3D9 source -> immutable D3D11 SRV -> real WARP Draw, stale/alias/UAV/retire negatives: PASS")
