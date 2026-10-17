#!/usr/bin/env python3
"""00886: genuine D3D9 post-draw surface mutations -> native D3D11 frame.
Source-level integration proof only. A real game/Quest3 session is UNTESTED.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
hooks = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
region = (root / "src/vr/d3d11/native_game_surface_copy_region.hpp").read_text(encoding="utf-8")


def linked(b, h, r):
    start = b.find("bool preserve_game_surface_copy(")
    end = b.find("void observe_game_surface_mutation(", start)
    if start < 0 or end <= start:
        return False
    replay = b[start:end]
    upd = h[h.find("HRESULT __stdcall R30UpdateSurfaceDest("):
            h.find("HRESULT __stdcall R30StretchRectDest(")]
    stretch = h[h.find("HRESULT __stdcall R30StretchRectDest("):
                h.find("HRESULT __stdcall R30ColorFillDest(")]
    if not upd or not stretch or not replay:
        return False
    return all(token in replay for token in (
        "nativeOutputUploadDepth != 0u",
        "!env_full_game_opt_in()",
        "FAILED(originalResult)",
        "s.sourceGameDevice != owner",
        "s.frameBatch.publishable(s.pending)",
        "s.surfaceReplayCount >= 8u",
        "actualIdentity.Get() != backbufferIdentity.Get()",
        "s.clearColor.matches(",
        "GameNativeSurfaceCopyRegion::destination(",
        "desc.MultiSampleType != D3DMULTISAMPLE_NONE",
        "game->GetRenderTargetData(",
        "destination, s.surfaceReplayReadback.Get()",
        "s.surfaceReplayReadback->LockRect(",
        "s.surfaceReplayReadback->UnlockRect()",
        "catch (...) { copied = false; }",
        "desc.Format == D3DFMT_X8R8G8B8",
        "dst[x] = 0xffu;",
        "context->UpdateSubresource(s.surfaceReplayScratch.Get()",
        "context->OMSetRenderTargets(0u, nullptr, nullptr);",
        "context->CopySubresourceRegion(",
        "s.backend.color_texture(), 0u, region.left, region.top, 0u,",
        "context->OMSetRenderTargets(1u, &oldColor, oldDepth);",
        "++s.surfaceReplayCount;",
    )) and all(token in upd for token in (
        "R30UpdateSurfaceHook.stdcall<HRESULT>(",
        "GameNativeSurfaceCopyRegion::update_surface(",
        "preserve_game_surface_copy(device, destination, &rect, hr)",
        "if (!replayed)",
        "observe_game_surface_mutation(",
    )) and all(token in stretch for token in (
        "R30StretchRectHook.stdcall<HRESULT>(",
        "GameNativeSurfaceCopyRegion::destination(",
        "preserve_game_surface_copy(device, destination, &rect, hr)",
        "if (!replayed)",
        "observe_game_surface_mutation(",
    )) and all(token in b for token in (
        "s.surfaceReplayReadback.Reset();",
        "s.surfaceReplayScratch.Reset();",
        "s.surfaceReplayCount = 0u;",
    )) and all(token in r for token in (
        "destX > destWidth || destY > destHeight",
        "(srcRight-srcLeft) > std::int64_t(destWidth)-destX",
        "(srcBottom-srcTop) > std::int64_t(destHeight)-destY",
        "w*h > 16u*1024u*1024u",
    ))


assert linked(bridge, hooks, region), "live surface copy integration is disconnected"
for token in (
    "game->GetRenderTargetData(",
    "s.frameBatch.publishable(s.pending)",
    "actualIdentity.Get() != backbufferIdentity.Get()",
    "context->OMSetRenderTargets(0u, nullptr, nullptr);",
    "context->CopySubresourceRegion(",
    "s.surfaceReplayReadback->UnlockRect()",
    "++s.surfaceReplayCount;",
):
    mutant = bridge.replace(token, "/* removed native postpass */", 1)
    assert mutant != bridge and not linked(mutant, hooks, region), token
for token in (
    "GameNativeSurfaceCopyRegion::update_surface(",
    "GameNativeSurfaceCopyRegion::destination(",
):
    mutant = hooks.replace(token, "source_region_unguarded(", 1)
    assert mutant != hooks and not linked(bridge, mutant, region), token
for token in (
    "destX > destWidth || destY > destHeight",
    "w*h > 16u*1024u*1024u",
):
    mutant = region.replace(token, "false", 1)
    assert mutant != region and not linked(bridge, hooks, mutant), token
print("PASS: live D3D9 copy -> D3D11 GPU region replay; original fallback preserved")
