#!/usr/bin/env python3
"""00590: game-authored trilinear mip sampler reaches native D3D11 Draw."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def connected(s: str) -> bool:
    try:
        gate = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
        mirror = s.split("bool create_game_sampler(", 1)[1].split("bool submit(", 1)[0]
        # Both the standalone Stage1 sampler and the Stage0 game texture
        # mirror must remain connected after 00716 sampler extraction.
        if "return create_game_sampler(dev, capture, levels, sampler);" not in mirror:
            return False
        sampler_impl = s.split("bool create_game_sampler(", 1)[1].split("bool mirror_cube_texture(", 1)[0]
        texture2d = s.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        if not all(x in sampler_impl for x in ("capture.mipFilter == D3DTEXF_LINEAR;", "if (capture.mipFilter == D3DTEXF_LINEAR) {")):
            return False
        submit = s.split("bool submit(", 1)[1].split("void observe(", 1)[0]
    except IndexError:
        return False
    a = [
        "GetSamplerState(0, D3DSAMP_MIPFILTER, &mip)",
        "((mip != D3DTEXF_NONE && mip != D3DTEXF_POINT) && mip != D3DTEXF_LINEAR)",
        "(mip == D3DTEXF_NONE && (maxMip != 0u || decodedMipBias != 0.0f)) || !validMipBias",
        "capture.mipFilter = static_cast<D3DTEXTUREFILTERTYPE>(mip)",
        "GetSamplerState(0, D3DSAMP_SRGBTEXTURE, &srgb)"
    ]
    b = [
        "capture.mipFilter == D3DTEXF_POINT ||",
        "capture.mipFilter == D3DTEXF_LINEAR;",
        "const UINT levels = usesMips ? sourceLevels : 1u;",
        "usesMips && (base.Usage & D3DUSAGE_AUTOGENMIPMAP)",
        "usesMips && capture.texture->GetLOD() != 0u",
        "capture.texture->GetSurfaceLevel(level, sourceSurface.GetAddressOf())",
        "capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY)",
        "initial[level].pSysMem = copied[level].data();",
        "initial[level].SysMemPitch = pitches[level];",
        "desc.MipLevels = levels; desc.ArraySize = 1;",
    ]
    c = ["mirror_texture(dev, capture, sampledView, sampledSampler)",
         "ctx->PSSetSamplers(0, 1, &boundSampler);",
         "ctx->DrawIndexed(indexCount, 0, 0);",
         "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"]
    sampler_required = (
        "capture.mipFilter == D3DTEXF_LINEAR;",
        "if (capture.mipFilter == D3DTEXF_LINEAR) {",
        "D3D11_FILTER_MIN_MAG_MIP_LINEAR",
        "D3D11_FILTER_MIN_LINEAR_MAG_POINT_MIP_LINEAR",
        "D3D11_FILTER_MIN_POINT_MAG_MIP_LINEAR",
        "D3D11_FILTER_MIN_MAG_POINT_MIP_LINEAR",
        "state.MaxLOD = usesMips ? static_cast<float>(levels - 1u) : 0.0f;",
    )
    return (all(x in gate for x in a) and
            all(x in sampler_impl for x in sampler_required) and
            all(x in texture2d for x in b) and
            all(x in submit for x in c))

def sampler(min_linear: bool, mag_linear: bool, mip_linear: bool) -> str:
    suffix = "LINEAR" if mip_linear else "POINT"
    combinations = {
        (False, False): "MIN_MAG_POINT_MIP_LINEAR" if mip_linear else "MIN_MAG_MIP_POINT",
        (False, True): "MIN_POINT_MAG_MIP_LINEAR" if mip_linear else "MIN_POINT_MAG_LINEAR_MIP_POINT",
        (True, False): "MIN_LINEAR_MAG_POINT_MIP_LINEAR" if mip_linear else "MIN_LINEAR_MAG_MIP_POINT",
        (True, True): "MIN_MAG_MIP_LINEAR" if mip_linear else "MIN_MAG_LINEAR_MIP_POINT"
    }
    return "D3D11_FILTER_" + combinations[min_linear, mag_linear]

def main() -> None:
    s = SOURCE.read_text(encoding="utf-8")
    assert connected(s), "D3D9 MIP_LINEAR to native D3D11 draw disconnected"
    mutations = [
        ("&& mip != D3DTEXF_LINEAR)", "&& mip != D3DTEXF_POINT)"),
        ("capture.mipFilter == D3DTEXF_LINEAR;", "capture.mipFilter == D3DTEXF_POINT;"),
        ("if (capture.mipFilter == D3DTEXF_LINEAR) {", "if (false) {"),
        ("D3D11_FILTER_MIN_MAG_MIP_LINEAR", "D3D11_FILTER_MIN_MAG_MIP_POINT"),
        ("D3D11_FILTER_MIN_LINEAR_MAG_POINT_MIP_LINEAR", "D3D11_FILTER_MIN_LINEAR_MAG_MIP_POINT"),
        ("D3D11_FILTER_MIN_POINT_MAG_MIP_LINEAR", "D3D11_FILTER_MIN_POINT_MAG_LINEAR_MIP_POINT"),
        ("D3D11_FILTER_MIN_MAG_POINT_MIP_LINEAR", "D3D11_FILTER_MIN_MAG_MIP_POINT"),
        ("usesMips && (base.Usage & D3DUSAGE_AUTOGENMIPMAP)", "false && (base.Usage & D3DUSAGE_AUTOGENMIPMAP)"),
        ("usesMips && capture.texture->GetLOD() != 0u", "false && capture.texture->GetLOD() != 0u"),
        ("const UINT levels = usesMips ? sourceLevels : 1u;", "const UINT levels = 1u;"),
        ("capture.texture->GetSurfaceLevel(level, sourceSurface.GetAddressOf())",
         "capture.texture->GetSurfaceLevel(0, sourceSurface.GetAddressOf())"),
        ("capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY)", "capture.texture->LockRect(0, &lock, nullptr, D3DLOCK_READONLY)"),
        ("initial[level].pSysMem = copied[level].data();", "initial[level].pSysMem = copied[0].data();"),
        ("initial[level].SysMemPitch = pitches[level];", "initial[level].SysMemPitch = pitches[0];"),
        ("desc.MipLevels = levels; desc.ArraySize = 1;", "desc.MipLevels = 1; desc.ArraySize = 1;"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->PSSetSamplers(0, 1, &boundSampler);", "ctx->PSSetSamplers(0, 0, &boundSampler);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);")
    ]
    for before, after in mutations:
        assert before in s, before
        assert not connected(s.replace(before, after, 1)), before
    # An independent mutation in the live 2D mirror cannot be hidden by the
    # sampler helper or an unchanged cube-texture mip branch.
    old = "capture.mipFilter == D3DTEXF_LINEAR;"
    prefix, rest = s.split("bool mirror_texture(", 1)
    texture2d, suffix = rest.split("bool submit(", 1)
    assert old in texture2d
    mutated = (prefix + "bool mirror_texture(" +
               texture2d.replace(old, "capture.mipFilter == D3DTEXF_POINT;", 1) +
               "bool submit(" + suffix)
    assert not connected(mutated), "2D MIP_LINEAR mutation survived"
    values = {sampler(mn, mg, mp) for mn in (False, True) for mg in (False, True) for mp in (False, True)}
    assert len(values) == 8
    assert all(v in s for v in values), "missing MIN/MAG/MIP filter variant"
    print("00590 PASS: 8 filters, 19 negative source mutations; Quest3/VDXR runtime UNTESTED")

if __name__ == "__main__":
    main()
