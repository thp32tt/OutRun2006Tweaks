#!/usr/bin/env python3
"""Summarize exhaustive DX9Ex EvidenceTrace logs.

Usage:
  python tools/analyze_vr_evidence_trace.py <game-log> [host-evidence-log]

The parser is intentionally tolerant: unknown/new fields are preserved as raw
samples while known VR EVIDENCE families are counted for automated review.
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

KV = re.compile(r'([A-Za-z][A-Za-z0-9_]*)=([^\s]+)')

def fields(line: str) -> dict[str, str]:
    return dict(KV.findall(line))

def read(path: pathlib.Path):
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for no, line in enumerate(f, 1):
            if "VR EVIDENCE" in line:
                yield no, line.rstrip("\n")

def main() -> int:
    if len(sys.argv) < 2:
        print("usage: analyze_vr_evidence_trace.py <game-log> [host-log]")
        return 2

    game = pathlib.Path(sys.argv[1])
    host = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None

    family = collections.Counter()
    draw_routes = collections.Counter()
    draw_hrs = collections.Counter()
    present = collections.Counter()
    stateblock = collections.Counter()
    r14 = collections.Counter()
    r15 = collections.Counter()
    cockpit = collections.Counter()
    failures: list[tuple[int, str]] = []
    samples: dict[str, list[str]] = collections.defaultdict(list)

    for no, line in read(game):
        f = fields(line)
        if "VR EVIDENCE DRAW STATE" in line:
            family["DRAW_STATE"] += 1
            draw_routes[f.get("route", "?")] += 1
            draw_hrs[f.get("hr", "?")] += 1
            if f.get("hr", "0x00000000").lower() not in (
                "0x00000000", "0x0", "0x00000001"):
                failures.append((no, line))
        elif "VR EVIDENCE DRAW BEGIN" in line:
            family["DRAW_BEGIN"] += 1
        elif "VR EVIDENCE MATRIX" in line:
            family["MATRIX"] += 1
        elif "VR EVIDENCE PRESENT" in line:
            family["PRESENT"] += 1
            present[f.get("failure", "?")] += 1
            if f.get("incomplete") == "1" or f.get("rightFailed") == "1":
                failures.append((no, line))
        elif "VR EVIDENCE RESET" in line:
            family["RESET"] += 1
        elif "VR EVIDENCE D3DX" in line:
            family["D3DX"] += 1
            evt = f.get("event", "?")
            samples["D3DX:" + evt].append(line)
            if f.get("hr", "0x00000000").lower() not in (
                "0x00000000", "0x0", "0x00000001"):
                failures.append((no, line))
        elif "VR EVIDENCE STATEBLOCK" in line:
            family["STATEBLOCK"] += 1
            event = line.split("VR EVIDENCE STATEBLOCK", 1)[1].strip().split()[0]
            stateblock[event] += 1
            if f.get("coverageLost") == "1" or f.get("reliable") == "0":
                failures.append((no, line))
        elif "VR EVIDENCE R14" in line:
            family["R14"] += 1
            event = line.split("VR EVIDENCE R14", 1)[1].strip().split()[0]
            r14[event] += 1
            if ("FAIL" in line or f.get("retirePending") == "1" or
                    f.get("externalWrite") == "1"):
                failures.append((no, line))
        elif "VR EVIDENCE R15" in line:
            family["R15"] += 1
            event = line.split("VR EVIDENCE R15", 1)[1].strip().split()[0]
            r15[event] += 1
            if "FAIL" in line or f.get("healthy") == "0":
                failures.append((no, line))
        elif "VR EVIDENCE COCKPIT" in line:
            family["COCKPIT"] += 1
            cockpit[f.get("pose", f.get("reason", "?"))] += 1
            if "FAIL" in line or "eligible=0" in line:
                failures.append((no, line))

    host_count = 0
    host_actual = collections.Counter()
    host_reject = collections.Counter()
    if host and host.exists():
        for no, line in read(host):
            if "VR EVIDENCE XR" not in line:
                continue
            host_count += 1
            f = fields(line)
            host_actual[f.get("actualFinal", "?")] += 1
            host_reject[f.get("candidateReject", "?")] += 1
            if (f.get("actualLayer") == "0" or
                    f.get("xrEndResult", "0") not in ("0", "XR_SUCCESS")):
                failures.append((no, "[HOST] " + line))

    print("=== VR EvidenceTrace summary ===")
    print("game:", game)
    if host:
        print("host:", host)
    print("families:", dict(family))
    print("draw routes:", dict(draw_routes))
    print("draw HRESULTs:", dict(draw_hrs))
    print("present failure codes:", dict(present))
    print("stateblock:", dict(stateblock))
    print("R14:", dict(r14))
    print("R15:", dict(r15))
    print("cockpit:", dict(cockpit))
    print("host XR frames:", host_count)
    print("host actualFinal:", dict(host_actual))
    print("host candidateReject:", dict(host_reject))
    print("suspicious records:", len(failures))
    for no, line in failures[:200]:
        print(f"! {no}: {line}")
    if len(failures) > 200:
        print(f"... {len(failures) - 200} more suspicious records")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
