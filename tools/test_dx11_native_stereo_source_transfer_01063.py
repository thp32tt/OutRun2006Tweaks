#!/usr/bin/env python3
"""01063 physical stereo GPU source / typed view and game OM preservation."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
ring=(r/"src/vr/d3d11/native_shared_eye_ring.cpp").read_text()
helper=(r/"src/vr/d3d11/native_game_eye_pair_sources.hpp").read_text()
bridge=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
workflow=(r/".github/workflows/dx11-fast-structural.yml").read_text()
def integrated(rr,hh,bb):
    source=rr.split("const auto exact_source =",1)[1].split(
        "// Validate both resource descriptors",1)[0]
    # The newest captured-game RTV proof and the older live-OM fallback
    # have separate identical ownership terms. Both must be proven, and a
    # mutation to either route must independently break this integration.
    legacy=source.split("ID3D11RenderTargetView* bound[",1)[1]
    format_logic=hh.split("native_game_eye_format_transfer_admitted(",1)[1].split(
        "// Only a view containing",1)[0]
    caller=bb.split("// Authenticate the producer's actual GPU resource",1)[1].split(
        "// Optional real GPU-only desktop presentation",1)[0]
    return all((
        "native_game_eye_format_transfer_admitted(" in hh,
        "typedView == ringFormat" in format_logic,
        "sampleCount == 1u" in format_logic,
        "native_game_eye_rtv_subresource_matches(" in hh,
        "desc.Format == format_" in source,
        "D3D11_RTV_DIMENSION_TEXTURE2DARRAY" in legacy,
        "D3D11_RTV_DIMENSION_TEXTURE2D" in legacy,
        "viewIdentity.Get() == sourceIdentity.Get()" in legacy,
        "viewDesc.Format, format_" in legacy,
        "context->OMGetRenderTargets(" in legacy,
        "view->Release();" in legacy,
        "return viewProven;" in legacy,
        "leftIdentity.Get() == rightIdentity.Get()" in rr,
        "if (transfer == NativeGameEyeTransfer::Resolve)" in rr,
        "entry.gpu_copy_queued = true;" in rr,
        "signal_producer_fence(context, slot, frame_id)" in rr,
        "ScopedNativeGameGpuTransferOutputs preserveGameOutputs(ctx);" in caller,
        "s.gpuFrameSink(s.gpuFrameSinkUser, frame)" in caller,
        "s.sourceGameDevice == presentDevice" in caller,
        "const bool outputWritable = monoNativePublicationAllowed &&" in bb,
    ))
assert integrated(ring,helper,bridge)
for needle in ("viewIdentity.Get() == sourceIdentity.Get()",
               "D3D11_RTV_DIMENSION_TEXTURE2DARRAY",
               "return viewProven;","view->Release();"):
    # Mutate the legacy OM-bound view proof, not the new earlier
    # captured-camera RTV proof: both must remain independently enforced.
    prefix, legacy = ring.split("ID3D11RenderTargetView* bound[",1)
    assert needle in legacy, needle
    b=prefix+"ID3D11RenderTargetView* bound["+legacy.replace(
        needle,"/* broken source-to-RTV proof */",1)
    assert b!=ring and not integrated(b,helper,bridge),needle
for needle in ("typedView == ringFormat","sampleCount == 1u"):
    prefix, format_logic=helper.split(
        "native_game_eye_format_transfer_admitted(",1)
    assert needle in format_logic.split("// Only a view containing",1)[0]
    b=prefix+"native_game_eye_format_transfer_admitted("+format_logic.replace(
        needle,"false /* unsafe gamma */",1)
    assert b!=helper and not integrated(ring,b,bridge),needle
for needle in ("ScopedNativeGameGpuTransferOutputs preserveGameOutputs(ctx);",
               "s.gpuFrameSink(s.gpuFrameSinkUser, frame)"):
    b=bridge.replace(needle,"/* source copy without owner */",1)
    assert b!=bridge and not integrated(ring,helper,b),needle
assert "tests/vr/dx11_native_stereo_source_transfer_01063.cpp" in workflow
assert "python tools/test_dx11_native_stereo_source_transfer_01063.py" in workflow
print("PASS 01063 actual stereo typed-source GPU copy and native game output restoration")
