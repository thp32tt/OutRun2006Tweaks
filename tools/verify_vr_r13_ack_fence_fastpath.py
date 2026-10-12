#!/usr/bin/env python3
"""R13 DirectGPU fallback: ACK-first ring scan avoids busy-slot GPU GetData.

The consumer's per-slot completed frame is the ownership gate. A producer
EVENT remains mandatory before overwriting a published shared texture.
These checks are static/source and modeled concurrency regressions, not HMD.
"""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r13.cpp"


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for end in range(brace, len(source)):
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:end + 1]
    raise AssertionError("unbalanced C++ function")


def verify(source: str) -> None:
    body = function_body(source, "bool ResolveDirectTransportR13(")
    scan = body.split("for (std::uint32_t offset = 0;", 1)[1].split(
        "selected = index;", 1)[0]
    required = (
        "const bool publicationNeedsAck =",
        "slot.published && slot.frameId != 0;",
        "if (publicationNeedsAck)",
        "R13ReadGpuCompletionSnapshotWithRebind(ackSnapshot);",
        "if (!ackSnapshotValid ||",
        "!FrameIdAtOrAfter(gpuCompleted, slot.frameId))",
        "ackBlocked = true;\n                        continue;",
        "if (slot.producerPending)",
        "slot.fence ? slot.fence->GetData(nullptr, 0, 0) : E_FAIL;",
        "if (ready == S_OK)",
        "slot.producerPending = false;",
        "slot.pendingFrameId = 0;",
        "if (!slot.published)\n                            slot.frameId = 0;",
        "else if (ready == S_FALSE)\n                    {\n                        continue;",
        "R13DirectCopyPathRejected = true;",
        "R13DirectCopyRejectHr = ready;",
        "return false;",
        "slot.frameId = 0;\n                    slot.published = false;",
    )
    for term in required:
        assert term in scan, ("missing fence/ownership guard", term)
    ack = scan.index("if (publicationNeedsAck)")
    poll = scan.index("if (slot.producerPending)")
    retire = scan.rindex("if (publicationNeedsAck)")
    assert ack < poll < retire
    assert scan.count("R13ReadGpuCompletionSnapshotWithRebind(ackSnapshot)") == 1
    assert scan.count("slot.fence->GetData(nullptr, 0, 0)") == 1
    assert scan[ack:poll].count("continue;") == 1
    assert scan[poll:retire].count("continue;") == 1
    assert "slot.published = false;" not in scan[:retire]
    assert "selected = index;\n                break;" in body


def scan_model(*, published: bool, producer_pending: bool,
               ack_ready: bool, fence_status: str):
    """Simple reference state machine for one ring slot, no D3D device."""
    get_data_calls = 0
    if published and not ack_ready:
        return "ACK_BLOCKED", get_data_calls
    if producer_pending:
        get_data_calls += 1
        if fence_status == "S_FALSE":
            return "FENCE_BUSY", get_data_calls
        if fence_status != "S_OK":
            return "QUARANTINE", get_data_calls
    return "REUSE", get_data_calls


def main() -> None:
    source = SRC.read_text(encoding="utf-8")
    verify(source)
    changes = (
        ("if (publicationNeedsAck)", "if (false)"),
        ("slot.published && slot.frameId != 0", "slot.published && false"),
        ("if (!ackSnapshotValid ||", "if (false ||"),
        ("!FrameIdAtOrAfter(gpuCompleted, slot.frameId))",
         "FrameIdAtOrAfter(gpuCompleted, slot.frameId))"),
        ("ackBlocked = true;\n                        continue;",
         "ackBlocked = true;\n                        break;"),
        ("if (slot.producerPending)", "if (false)"),
        ("slot.fence->GetData(nullptr, 0, 0)", "S_OK"),
        ("else if (ready == S_FALSE)", "else if (ready == S_OK)"),
        ("R13DirectCopyPathRejected = true;", "R13DirectCopyPathRejected = false;"),
        ("if (!slot.published)\n                            slot.frameId = 0;",
         "slot.frameId = 0;"),
        ("slot.frameId = 0;\n                    slot.published = false;",
         "slot.frameId = 0;\n                    slot.published = true;"),
    )
    # Mutate only the fallback resolve function, not another R13 producer.
    signature = "bool ResolveDirectTransportR13("
    start = source.index(signature)
    end = start + len(function_body(source, signature)) + (
        source.index("{", start) - start)
    mutants_checked = 0
    for old, new in changes:
        original = source[start:end]
        assert old in original, ("ineffective mutation", old)
        broken = source[:start] + original.replace(old, new, 1) + source[end:]
        try:
            verify(broken)
        except (AssertionError, ValueError, IndexError):
            mutants_checked += 1
        else:
            raise AssertionError("R13 ACK/fence negative mutation survived: " + old)
    assert mutants_checked == len(changes)
    cases = (
        (True, True, False, "S_OK", ("ACK_BLOCKED", 0)),
        (True, True, True, "S_FALSE", ("FENCE_BUSY", 1)),
        (True, True, True, "E_FAIL", ("QUARANTINE", 1)),
        (True, True, True, "S_OK", ("REUSE", 1)),
        (True, False, False, "S_OK", ("ACK_BLOCKED", 0)),
        (True, False, True, "S_OK", ("REUSE", 0)),
        (False, True, False, "S_FALSE", ("FENCE_BUSY", 1)),
        (False, True, False, "S_OK", ("REUSE", 1)),
        (False, False, False, "S_OK", ("REUSE", 0)),
    )
    for published, pending, ack, fence, expected in cases:
        assert scan_model(published=published, producer_pending=pending,
                          ack_ready=ack, fence_status=fence) == expected
    print(f"PASS R13 ACK-before-EVENT fallback ring: {len(cases)} model cases, "
          f"{mutants_checked} negative mutations")


if __name__ == "__main__":
    main()
