#!/usr/bin/env python3
"""R32 DirectGPU backpressure: no source snapshot until a reusable slot exists."""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r32.cpp"


def verify(source: str) -> None:
    code = source.split("bool R32ResolveDirectTransport(", 1)[1].split(
        "void R32InvalidateResetCaches()", 1)[0]

    def at(fragment: str) -> int:
        assert code.count(fragment) == 1, f"missing or repeated guard: {fragment}"
        return code.index(fragment)

    assert at("R32EnsureDirectResources(device)") < at(
        "if (R32DirectCopyPathRejected)")
    assert at("if (R32DirectCopyPathRejected)") < at(
        "for (std::uint32_t offset = 0;")
    assert at("if (candidate.published && candidate.frameId)") < at(
        "R30SupportPollDirectTransportSlotProducer(index)")
    assert at("R30SupportTryGetGpuCompletionSnapshot(ackSnapshot)") < at(
        "R30SupportPollDirectTransportSlotProducer(index)")
    assert at("R30SupportPollDirectTransportSlotProducer(index)") < at(
        "selectedPublication = candidate;")
    assert at("selectedPublication = candidate;") < at("selected = index;")
    assert at("selected = index;") < at(
        "if (selected >= OutRunVR::RenderFrameRingSize)")
    assert at("if (selected >= OutRunVR::RenderFrameRingSize)") < at(
        "R30SupportTryGetDirectTransportSourceSurfaces(sourceSurfaces)")
    assert at("R30SupportTryGetDirectTransportSourceSurfaces(sourceSurfaces)") < at(
        "if (selectedPublication.published && selectedPublication.frameId)")
    assert at("if (selectedPublication.published && selectedPublication.frameId)") < at(
        "R30SupportRetireDirectTransportSlotPublication(selected)")
    assert at("R30SupportRetireDirectTransportSlotPublication(selected)") < at(
        "R30SupportCopyDirectTransportEyesAndIssueFence(")
    assert "if (!R30SupportTryGetDirectTransportSourceSurfaces(sourceSurfaces))\n                return false;" in code
    assert "if (ackBlocked)\n                    R30SupportNoteSafeAckBackpressure();" in code
    for token in (
        "R30SupportNoteDirectTransportRingBackpressure();",
        "if (ready == S_FALSE)",
        "if (FAILED(ready))",
        "R32DirectCopyPathRejected = true;",
        "R30SupportMarkDirectTransportSlotPending(selected, frameId);",
    ):
        assert token in code


def main() -> None:
    source = SRC.read_text(encoding="utf-8")
    verify(source)
    mutations = [
        ("lost_slot_guard", "if (selected >= OutRunVR::RenderFrameRingSize)", "if (false)"),
        ("lost_source_gate", "if (!R30SupportTryGetDirectTransportSourceSurfaces(sourceSurfaces))", "if (false)"),
        ("stale_pub", "selectedPublication = candidate;", "selectedPublication = {};"),
        ("retire_unconditionally", "if (selectedPublication.published && selectedPublication.frameId)", "if (true)"),
        ("wrong_slot", "R30SupportRetireDirectTransportSlotPublication(selected);", "R30SupportRetireDirectTransportSlotPublication(index);"),
        ("no_ack", "R30SupportTryGetGpuCompletionSnapshot(ackSnapshot)", "true"),
        ("no_fence", "R30SupportPollDirectTransportSlotProducer(index)", "D3D_OK"),
        ("no_ack_backpressure", "R30SupportNoteSafeAckBackpressure();", "/* no ACK pressure */"),
        ("no_ring_backpressure", "R30SupportNoteDirectTransportRingBackpressure();", "/* no ring pressure */"),
        ("no_pending_fence", "R30SupportMarkDirectTransportSlotPending(selected, frameId);", "/* no pending state */"),
        ("no_error_guard", "if (FAILED(ready))", "if (false)"),
    ]
    for name, old, new in mutations:
        assert old in source, f"missing mutation anchor: {name}"
        mutant = source.replace(old, new, 1)
        try:
            verify(mutant)
        except (AssertionError, ValueError, IndexError):
            continue
        raise AssertionError(f"mutation escaped: {name}")
    print(f"PASS R32 lazy DirectGPU source snapshot under ring backpressure; {len(mutations)} mutations")


if __name__ == "__main__":
    main()
