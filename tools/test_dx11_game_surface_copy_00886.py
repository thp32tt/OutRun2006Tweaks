#!/usr/bin/env python3
"""00886: genuine D3D9 post-draw surface mutations -> native D3D11 frame.
Source-level integration proof only. A real game/Quest3 session is UNTESTED.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
hooks = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
region = (root / "src/vr/d3d11/native_game_surface_copy_region.hpp").read_text(encoding="utf-8")
gpu_outputs = (root / "src/vr/d3d11/native_game_gpu_output_preserve.hpp").read_text(encoding="utf-8")


def linked(b, h, r):
    start = b.find("bool preserve_game_surface_copy(")
    # Verify the post-Draw copy itself, not later CPU/GDI ticket helpers.
    end = b.find("bool begin_game_surface_cpu_write(", start)
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
        "!s.surfaceReplayBudget.admits_bytes(plannedReadbackBytes)",
        "actualIdentity.Get() != backbufferIdentity.Get()",
        "s.clearColor.matches(",
        "GameNativeSurfaceCopyRegion::destination(",
        "desc.MultiSampleType != D3DMULTISAMPLE_NONE",
        "game->GetRenderTargetData(",
        "tileSucceeded = s.surfaceReplayTile.capture(",
        "if (!tileSucceeded && !prepareFullReadback()) return false;",
        "if (!s.surfaceReplayBudget.admits(desc.Width,desc.Height))",
        "if (!tileSucceeded || !prepareFullReadback()) return false;",
        "tileSucceeded=false;",
        "if (tileSucceeded) readback=s.surfaceReplayTile.staging();",
        "readback=s.surfaceReplayReadback.Get();",
        "GameNativeSurfaceTilePlan::source_x(region, tileSucceeded)",
        "GameNativeSurfaceTilePlan::source_y(region, tileSucceeded)",
        "destination,s.surfaceReplayReadback.Get()",
        "readback->LockRect(",
        "readback->UnlockRect()",
        "catch (...) { copied=false; }",
        "desc.Format == D3DFMT_X8R8G8B8",
        "dst[x]=0xffu;",
        "context->UpdateSubresource(s.surfaceReplayScratch.Get()",
        "ScopedNativeGameGpuTransferInputs shaderInputs(",
        "ScopedNativeGameGpuTransferOutputs outputs(context);",
        "context->CopySubresourceRegion(",
        "s.backend.color_texture(), 0u, region.left, region.top, 0u,",
        "if (FAILED(device->GetDeviceRemovedReason())) return false;",
        "s.surfaceReplayBudget.note_success_bytes(",
    )) and (
        '#include "native_game_gpu_output_preserve.hpp"' in b
        and "ScopedNativeGameGpuTransferInputs shaderInputs(\n                context, s.backend.color_texture());" in replay
        and "resource == destination_" in gpu_outputs
        and all(name in gpu_outputs for name in (
            "VSGetShaderResources", "PSGetShaderResources",
            "GSGetShaderResources", "HSGetShaderResources",
            "DSGetShaderResources", "CSGetShaderResources",
            "VSSetShaderResources", "PSSetShaderResources",
            "GSSetShaderResources", "HSSetShaderResources",
            "DSSetShaderResources", "CSSetShaderResources",
        ))
        and "OMGetRenderTargets(1u, &oldColor" not in replay
        and "OMSetRenderTargets(1u, &oldColor" not in replay
        # An earlier device-loss guard already existed before UpdateSubresource.
        # Require a SECOND one after the GPU copy; replacing the earlier one
        # does not prove that a failed native copy is vetoed before publish.
        and replay.rfind("if (FAILED(device->GetDeviceRemovedReason())) return false;")
            > replay.index("context->CopySubresourceRegion(")
        # The pre-Draw snapshot has a separate successful replay charge before native
        # CopySubresourceRegion; prove the REAL post-Draw replay is counted
        # after the GPU copy, not just anywhere in this function.
        and replay.rfind("s.surfaceReplayBudget.note_success_bytes(")
            > replay.index("context->CopySubresourceRegion(")
        and replay.index("ScopedNativeGameGpuTransferOutputs outputs(context);")
            < replay.index("context->CopySubresourceRegion(")
        and all(token in gpu_outputs for token in (
            "OMGetRenderTargets(", "OMGetRenderTargetsAndUnorderedAccessViews(",
            "CSGetUnorderedAccessViews(", "CSSetUnorderedAccessViews(",
            "OMSetRenderTargetsAndUnorderedAccessViews(", "keepCounters",
        ))
    ) and all(token in upd for token in (
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
        "s.surfaceReplayBudget.reset();",
    )) and all(token in r for token in (
        "destX > destWidth || destY > destHeight",
        "(srcRight-srcLeft) > std::int64_t(destWidth)-destX",
        "(srcBottom-srcTop) > std::int64_t(destHeight)-destY",
        "w*h > 16u*1024u*1024u",
    ))


assert linked(bridge, hooks, region), "live surface copy integration is disconnected"
# Mutate the owning replay function, not an earlier frame admission check.
# A global first-occurrence replacement misses the actual protected copy when
# multiple native frame stages now use the same admission predicate.
replay_begin = bridge.index("bool preserve_game_surface_copy(")
replay_end = bridge.index("bool begin_game_surface_cpu_write(", replay_begin)
replay_body = bridge[replay_begin:replay_end]
for token in (
    # Mutation of either crop or fallback disconnects native integration.
    "tileSucceeded = s.surfaceReplayTile.capture(",
    "if (!tileSucceeded && !prepareFullReadback()) return false;",
    "GameNativeSurfaceTilePlan::source_x(region, tileSucceeded)",
    "GameNativeSurfaceTilePlan::source_y(region, tileSucceeded)",
    "readback=s.surfaceReplayReadback.Get();",
    "game->GetRenderTargetData(",
    "s.frameBatch.publishable(s.pending)",
    "actualIdentity.Get() != backbufferIdentity.Get()",
    "ScopedNativeGameGpuTransferInputs shaderInputs(",
    "ScopedNativeGameGpuTransferOutputs outputs(context);",
    "context->CopySubresourceRegion(",
    "if (FAILED(device->GetDeviceRemovedReason())) return false;\n        s.surfaceReplayBudget.note_success_bytes(",
    "readback->UnlockRect()",
    "s.surfaceReplayBudget.note_success_bytes(",
):
    assert token in replay_body, "replay guard absent before mutation: " + token
    # Pre-Draw snapshots have a separate bounded copy counter. The legacy
    # post-Draw mutation must remove the LAST charge, which belongs to
    # the real GPU CopySubresourceRegion replay, not the initial snapshot.
    if token == "s.surfaceReplayBudget.note_success_bytes(":
        at = replay_body.rfind(token)
        mutant_body = (replay_body[:at] + "/* removed native postpass */" +
                       replay_body[at + len(token):])
    else:
        mutant_body = replay_body.replace(token, "/* removed native postpass */", 1)
    mutant = bridge[:replay_begin] + mutant_body + bridge[replay_end:]
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
