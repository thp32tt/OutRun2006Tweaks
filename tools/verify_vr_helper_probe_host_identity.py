#!/usr/bin/env python3
"""Prevent helper D3D9Ex probe ACK success after OpenXR host replacement.

Single static source contract plus five independent negative mutations.
Device/HMD functional acceptance is outside this guard.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/helper_ex_probe.cpp"


def violations(text: str) -> list[str]:
    problems = []
    if "const std::uint32_t expectedHostPid = shared.state->hostPid;" not in text:
        problems.append("host PID is not pinned")
    if "shared.state->hostPid == expectedHostPid" not in text:
        problems.append("host PID is not compared")
    if "shared.state->hostAdapterLuidLow == wanted.LowPart" not in text or (
        "shared.state->hostAdapterLuidHigh ==" not in text
    ):
        problems.append("host LUID is not compared")
    if "(shared.state->flags & OutRunVR::HostAdapterLuidValid) != 0" not in text:
        problems.append("host LUID validity is not compared")
    start = text.find("const auto hostIdentityUnchanged = [&]() noexcept")
    publish = text.find("InterlockedExchange(reinterpret_cast<volatile LONG*>(&shared.state->clientInteropProbeToken)")
    check = text.find("if (!hostIdentityUnchanged())")
    if start < 0 or publish < 0 or check < start or check >= publish:
        problems.append("missing pre-publication identity check")
    ack_start = text.find("bool verified = false;")
    ack_check = text.find("if (!hostIdentityUnchanged())", ack_start)
    ack_token = text.find("if (shared.state->hostInteropProbeAckToken == token)", ack_start)
    if ack_start < 0 or ack_check < ack_start or ack_token < ack_check:
        problems.append("missing identity check before ACK consumption")
    if "verified = verified && hostIdentityUnchanged();" not in text:
        problems.append("ACK success not rechecked against host identity")
    if "InterlockedCompareExchange(reinterpret_cast<volatile LONG*>(&shared.state->clientInteropProbeHandle)" not in text:
        problems.append("probe handle cleanup no longer conditional")
    return problems


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert not violations(source), violations(source)
    mutations = (
        ("shared.state->hostPid == expectedHostPid", "shared.state->hostPid != expectedHostPid"),
        ("shared.state->hostAdapterLuidLow == wanted.LowPart", "shared.state->hostAdapterLuidLow != wanted.LowPart"),
        ("(shared.state->flags & OutRunVR::HostAdapterLuidValid) != 0", "false"),
        ("if (!hostIdentityUnchanged())", "if (false)"),
        ("verified = verified && hostIdentityUnchanged();", "verified = verified;"),
    )
    for old, replacement in mutations:
        assert old in source, "missing mutation anchor: " + old
        broken = source.replace(old, replacement, 1)
        assert violations(broken), "negative mutation escaped: " + old
    print("DX9Ex helper host identity PASS: PID/LUID, pre-publish, ACK, 5 negative mutations")


if __name__ == "__main__":
    main()
