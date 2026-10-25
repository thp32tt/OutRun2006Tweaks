#!/usr/bin/env python3
"""01073: all four R30 game Draw sources capture D3D9 instance-rate VB slots."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
hooks = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
contract = (root / "src/vr/d3d11/live_game_frame_bridge.hpp").read_text(encoding="utf-8")
def connected(r30: str, native: str, iface: str) -> bool:
    begin = r30.find("bool R30CaptureNativeAdditionalStreams(")
    end = r30.find("void R30ObserveNativeLinearVB(", begin)
    if begin < 0 or end <= begin: return False
    capture = r30[begin:end]
    required = (
        "GetStreamSourceFreq(0u, &streamZeroFrequency)",
        "GetStreamSourceFreq(slot, &secondaryFrequency)",
        "game_native_instance_stream_capture(",
        "capturePlan.instanceRate",
        "capturePlan.sourceSlots",
        "R30CopySparseVertexShadow(",
        "sourcePhysical",
    )
    if any(s not in capture for s in required): return False
    if capture.index("game_native_instance_stream_capture(") > capture.index("R30CopySparseVertexShadow("):
        return False
    # Both the bounded source-slot plan and the published compact record
    # count must survive. Removing one while retaining the other is unsafe.
    if ("capturePlan.sourceSlots >" not in capture or
            "owned[slot-1u].data(),stride,capturePlan.sourceSlots" not in capture):
        return False
    if 'native_game_instance_stream_capture.hpp' not in r30: return False
    sections = [
        ("void R30ObserveNativeLinearVB(", "void R30ObserveNativeIndexedVB("),
        ("void R30ObserveNativeIndexedVB(", "void R30ObserveNativeLinearUP("),
        ("void R30ObserveNativeLinearUP(", "void R30ObserveNativeIndexedUP("),
        ("void R30ObserveNativeIndexedUP(", "void R30CompleteNativeGameSource("),
    ]
    if any(r30.find(b) < 0 or r30.find(e, r30.find(b)) < 0 or
           "R30CaptureNativeAdditionalStreams(" not in
           r30[r30.find(b):r30.find(e, r30.find(b))]
           for b,e in sections): return False
    return ("game_sm3_assemble_instanced_streams(" in native and
            "instanceSteps[slot] = frequency & kStreamFrequencyMask;" in native and
            "Each instance-rate" in iface)
assert connected(hooks, bridge, contract), "R30 instance-rate shadow to SM3 Draw disjoint"
for mutation in (
    "GetStreamSourceFreq(0u, &streamZeroFrequency)",
    "GetStreamSourceFreq(slot, &secondaryFrequency)",
    "capturePlan.instanceRate",
    "capturePlan.sourceSlots",
):
    # Mutate every occurrence of shared slot accounting; it is referenced
    # by the range cap AND by the assembler's captured record count.
    changed = hooks.replace(mutation, "REMOVED_FOR_NEGATIVE_REGRESSION")
    assert changed != hooks and not connected(changed, bridge, contract), mutation
assert not connected(hooks, bridge.replace(
    "game_sm3_assemble_instanced_streams(", "REMOVED_ASSEMBLER(", 1), contract)
print("01073 real game four-route instance-rate capture + native SM3 integration PASS")
