#!/usr/bin/env python3
"""Deterministic destructive regression for R32 DirectGPU ACK fast polling."""
from pathlib import Path

text = (Path(__file__).resolve().parents[1] /
        "vrhost/src/runtime/r32_direct_submit.hpp").read_text(encoding="utf-8")

def contract(s):
    r = s.split("inline void ReleasePending()", 1)[1].split(
        "inline void ObserveAckIdentity(", 1)[0]
    p = s.split("inline void PollCompletedAcks()", 1)[1].split(
        "inline bool ArmConsumptionFence(", 1)[0]
    a = s.split("inline bool ArmConsumptionFence(", 1)[1].split(
        "inline bool MetadataValid(", 1)[0]
    return all((
        "inline std::uint32_t PendingAckCount = 0;" in s,
        "PendingAckCount = 0;" in r,
        "pending.completionObserved = false;" in r,
        "OutRunVrFinalTest::Context || PendingAckCount == 0" in p,
        "if (!pending.completionObserved)" in p,
        "if (hr == S_FALSE)" in p,
        "if (SUCCEEDED(hr))\n                    pending.completionObserved = true;" in p,
        p.count("--PendingAckCount;") == 3,
        p.count("pending.completionObserved = false;") == 3,
        "PublishCompletedFrame(" in p,
        a.count("++PendingAckCount;") == 1,
        "pending.completionObserved = false;\n        ++PendingAckCount;" in a,
    ))

assert contract(text)
for old, new in (
    ("PendingAckCount == 0", "false"),
    ("if (!pending.completionObserved)", "if (true)"),
    ("++PendingAckCount;", "++AckArmed;"),
    ("--PendingAckCount;", "--AckArmed;"),
    ("PendingAckCount = 0;", "PendingAckCount = 7;"),
):
    assert old in text
    assert not contract(text.replace(old, new, 1)), old

# GPU signals once. A publisher timeout across two more XR ticks must not
# reissue GetData. On successful publication, the ring returns to idle.
pending, observed, driver_queries = 1, False, 0
for publication_ok in (False, False, True):
    if not observed:
        driver_queries += 1
        observed = True
    if publication_ok:
        pending -= 1
        observed = False
assert pending == 0 and driver_queries == 1
print("R32 ACK GPU EVENT retry/idle polling regression PASS (5 mutants)")
