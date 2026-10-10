#!/usr/bin/env python3
"""Fail closed if the F10 recenter IPC reader accepts an in-progress publisher.

The game publishes requesterPid=0 before advancing requestId. The host must
recheck that sentinel after its second sequence read, since a restarted game
can clear PID during a still-unchanged request ID. No HMD test is implied.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/ipc/recenter_request.hpp"


def violations(source: str) -> list[str]:
    errors: list[str] = []
    try:
        pending = source.split("bool Pending(LONG& requestId, DWORD& requesterPid) noexcept", 1)[1].split(
            "void MarkReceived(LONG requestId) noexcept", 1
        )[0]
    except IndexError:
        return ["missing recenter Pending/MarkReceived boundary"]

    ordered = (
        "const DWORD publishedPid = static_cast<DWORD>(",
        "if (publishedPid == 0)",
        "const LONG requestedAfter = InterlockedCompareExchange(",
        "if (requestedAfter != requested)",
        "const DWORD publishedPidAfter = static_cast<DWORD>(",
        "if (publishedPidAfter == 0 || publishedPidAfter != publishedPid)",
        "requestId = requested;",
        "requesterPid = publishedPid;",
        "return true;",
    )
    indices = [pending.find(part) for part in ordered]
    if any(i < 0 for i in indices) or indices != sorted(indices):
        errors.append("PID sentinel/sequence recheck order not preserved")
    if pending.count("InterlockedCompareExchange(&state_->requesterPid, 0, 0)") != 2:
        errors.append("both publisher PID snapshots must use atomic reads")
    if "InterlockedExchange(&state_->requesterPid, 0);" not in source:
        errors.append("writer-side in-progress publication sentinel removed")
    if "const LONG requestId = InterlockedIncrement(&state_->requestId);" not in source:
        errors.append("writer sequence advancement removed")
    return errors


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    errors = violations(source)
    if errors:
        raise SystemExit("VR RECENTER SNAPSHOT FAIL: " + "; ".join(errors))
    mutations = (
        ("publishedPidAfter == 0 || publishedPidAfter != publishedPid", "false"),
        ("publishedPidAfter != publishedPid", "publishedPidAfter == publishedPid"),
        ("publishedPidAfter == 0", "publishedPidAfter != 0"),
        ("if (requestedAfter != requested)", "if (false)"),
        ("InterlockedExchange(&state_->requesterPid, 0);", "/* sentinel removed */"),
    )
    for before, after in mutations:
        if before not in source or not violations(source.replace(before, after, 1)):
            raise SystemExit("VR RECENTER SNAPSHOT negative mutation escaped: " + before)
    print("VR RECENTER SNAPSHOT PASS: stable PID/sequence, 5 negative mutations")


if __name__ == "__main__":
    main()
