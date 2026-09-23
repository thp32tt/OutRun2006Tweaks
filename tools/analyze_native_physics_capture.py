#!/usr/bin/env python3
"""Analyze WheelFFB NATIVE_PHYSICS capture records.

The analyzer is intentionally diagnostic-only. It does not modify source/config
or promote a reverse-engineered field to production semantics. It summarizes
scale, sign/correlation and the four-wheel relationships needed before native
tyre/suspension channels are allowed to influence FFB.
"""
from __future__ import annotations

import argparse
import math
import re
import statistics
from pathlib import Path
from typing import Dict, Iterable, List, Optional

MARKER = "WheelFFB NATIVE_PHYSICS "
BLOCK_RE = re.compile(r"(front0|front1|rear0|rear1)\[([^\]]+)\]")
KV_RE = re.compile(r"([A-Za-z][A-Za-z0-9]*)=([^\s\]]+)")
ANGLE_UNIT_RAD = 2.0 * math.pi / 65536.0


def number(text: str) -> Optional[float]:
    text = text.rstrip(",;)]")
    if text.lower() == "true":
        return 1.0
    if text.lower() == "false":
        return 0.0
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def parse_kv(text: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for m in KV_RE.finditer(text):
        value = number(m.group(2))
        if value is not None:
            out[m.group(1)] = value
    return out


def load(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            pos = line.find(MARKER)
            if pos < 0:
                continue
            payload = line[pos + len(MARKER):]
            blocks = {m.group(1): parse_kv(m.group(2)) for m in BLOCK_RE.finditer(payload)}
            prefix = BLOCK_RE.sub("", payload)
            root = parse_kv(prefix)
            if all(name in blocks for name in ("front0", "front1", "rear0", "rear1")):
                rows.append({"root": root, **blocks})
    return rows


def percentile(values: Iterable[float], q: float) -> float:
    data = sorted(v for v in values if math.isfinite(v))
    if not data:
        return float("nan")
    if len(data) == 1:
        return data[0]
    x = (len(data) - 1) * q
    lo = int(math.floor(x))
    hi = int(math.ceil(x))
    if lo == hi:
        return data[lo]
    return data[lo] + (data[hi] - data[lo]) * (x - lo)


def corr(a: Iterable[float], b: Iterable[float]) -> float:
    pairs = [(x, y) for x, y in zip(a, b) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 3:
        return float("nan")
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    return sum(x * y for x, y in zip(dx, dy)) / denom if denom > 1e-20 else 0.0


def fmt(v: float, digits: int = 4) -> str:
    return "n/a" if not math.isfinite(v) else f"{v:.{digits}f}"


def series(rows: List[dict], fn):
    out = []
    for r in rows:
        try:
            v = float(fn(r))
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            v = float("nan")
        out.append(v if math.isfinite(v) else float("nan"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    args = ap.parse_args()

    rows = load(args.log)
    print(f"NATIVE_PHYSICS records : {len(rows)}")
    if len(rows) < 60:
        print("Too few records. Capture at least several seconds including straights and corners.")
        return 3

    finite = series(rows, lambda r: r["root"].get("finite", 0.0))
    valid_rows = [r for r, f in zip(rows, finite) if f >= 0.5]
    print(f"finite records         : {len(valid_rows)} / {len(rows)}")
    if len(valid_rows) < 60:
        print("Too few finite records for useful inference.")
        return 4
    rows = valid_rows

    speed = series(rows, lambda r: r["root"]["speed"])
    d_speed = series(rows, lambda r: r["root"]["dSpeed"])
    prev_d_speed = series(rows, lambda r: r["root"]["prevDSpeed"])
    normal = series(rows, lambda r: r["root"]["frontNormal"])
    normal_diff = series(rows, lambda r: r["root"]["frontNormalDiff"])

    ac_sum = series(rows, lambda r: r["front0"]["ac"] + r["front1"]["ac"])
    b0_sum = series(rows, lambda r: r["front0"]["b0"] + r["front1"]["b0"])
    b4_sum = series(rows, lambda r: r["front0"]["b4"] + r["front1"]["b4"])
    b8_sum = series(rows, lambda r: r["front0"]["b8"] + r["front1"]["b8"])
    capacity = series(rows, lambda r: abs(r["front0"]["c0"]) + abs(r["front1"]["c0"]))
    force_ratio = [
        (fy / cap if math.isfinite(fy) and math.isfinite(cap) and cap > 1e-6 else float("nan"))
        for fy, cap in zip(ac_sum, capacity)
    ]

    slip0 = series(rows, lambda r: -r["front0"]["steerEE"] * ANGLE_UNIT_RAD)
    slip1 = series(rows, lambda r: -r["front1"]["steerEE"] * ANGLE_UNIT_RAD)
    slip_mean = []
    for r, s0, s1 in zip(rows, slip0, slip1):
        c0 = abs(r["front0"].get("c0", 0.0))
        c1 = abs(r["front1"].get("c0", 0.0))
        total = c0 + c1
        slip_mean.append((s0 * c0 + s1 * c1) / total if total > 1e-6 else float("nan"))

    rear_ac_sum = series(rows, lambda r: r["rear0"]["ac"] + r["rear1"]["ac"])
    rear_capacity = series(
        rows, lambda r: abs(r["rear0"]["c0"]) + abs(r["rear1"]["c0"]))
    rear_force_ratio = [
        (fy / cap if math.isfinite(fy) and math.isfinite(cap) and cap > 1e-6 else float("nan"))
        for fy, cap in zip(rear_ac_sum, rear_capacity)
    ]
    rear_slip0 = series(rows, lambda r: -r["rear0"]["steerEE"] * ANGLE_UNIT_RAD)
    rear_slip1 = series(rows, lambda r: -r["rear1"]["steerEE"] * ANGLE_UNIT_RAD)
    rear_slip_mean = []
    for r, s0, s1 in zip(rows, rear_slip0, rear_slip1):
        c0 = abs(r["rear0"].get("c0", 0.0))
        c1 = abs(r["rear1"].get("c0", 0.0))
        total = c0 + c1
        rear_slip_mean.append(
            (s0 * c0 + s1 * c1) / total if total > 1e-6 else float("nan"))

    compression_diff = series(
        rows, lambda r: r["front0"]["c18"] - r["front1"]["c18"])
    reaction_diff = series(
        rows, lambda r: r["front0"]["susp24"] - r["front1"]["susp24"])

    print("\nScale / headroom")
    for name, values in (
        ("|front AC sum|", [abs(v) for v in ac_sum]),
        ("front capacity", capacity),
        ("|AC/capacity|", [abs(v) for v in force_ratio]),
        ("front normal load", normal),
        ("|front load diff|", [abs(v) for v in normal_diff]),
        ("|front slip rad|", [abs(v) for v in slip_mean]),
        ("|rear AC sum|", [abs(v) for v in rear_ac_sum]),
        ("rear capacity", rear_capacity),
        ("|rear AC/capacity|", [abs(v) for v in rear_force_ratio]),
        ("|rear slip rad|", [abs(v) for v in rear_slip_mean]),
        ("|dSpeed|", [abs(v) for v in d_speed]),
    ):
        print(
            f"{name:20s} p50={fmt(percentile(values, .50))} "
            f"p90={fmt(percentile(values, .90))} "
            f"p95={fmt(percentile(values, .95))} "
            f"p99={fmt(percentile(values, .99))} "
            f"max={fmt(max((v for v in values if math.isfinite(v)), default=float('nan')))}"
        )

    print("\nCross-checks")
    print(f"corr(front slip, AC sum)       : {fmt(corr(slip_mean, ac_sum), 3)}")
    print(f"corr(AC sum, transformed B4)   : {fmt(corr(ac_sum, b4_sum), 3)}")
    print(f"corr(AC sum, transformed B8)   : {fmt(corr(ac_sum, b8_sum), 3)}")
    print(f"corr(B0 sum, transformed B4)   : {fmt(corr(b0_sum, b4_sum), 3)}")
    print(f"corr(B0 sum, transformed B8)   : {fmt(corr(b0_sum, b8_sum), 3)}")
    print(f"corr(load diff, AC sum)        : {fmt(corr(normal_diff, ac_sum), 3)}")
    print(f"corr(compression diff, AC sum) : {fmt(corr(compression_diff, ac_sum), 3)}")
    print(f"corr(reaction diff, AC sum)    : {fmt(corr(reaction_diff, ac_sum), 3)}")
    print(f"corr(rear slip, rear AC sum)   : {fmt(corr(rear_slip_mean, rear_ac_sum), 3)}")
    print(f"corr(front slip, rear slip)    : {fmt(corr(slip_mean, rear_slip_mean), 3)}")
    print(f"corr(dSpeed, prevDSpeed)       : {fmt(corr(d_speed[1:], prev_d_speed[1:]), 3)}")

    rear_abs = [abs(v) for v in rear_slip_mean if math.isfinite(v)]
    if rear_abs:
        print(
            "rear-slip reference hints       : "
            f"P90={fmt(percentile(rear_abs, .90), 3)} rad  "
            f"P95={fmt(percentile(rear_abs, .95), 3)} rad  "
            "(use only as capture evidence, not automatic tuning)"
        )

    moving = [r for r in rows if abs(r["root"].get("speed", 0.0)) > 0.05]
    air_or_zero_cap = sum(
        1 for r in moving
        if abs(r["front0"].get("c0", 0.0)) + abs(r["front1"].get("c0", 0.0)) <= 1e-6
    )
    rear_zero_cap = sum(
        1 for r in moving
        if abs(r["rear0"].get("c0", 0.0)) + abs(r["rear1"].get("c0", 0.0)) <= 1e-6
    )
    print("\nGuards")
    print(f"moving rows with zero front capacity: {air_or_zero_cap} / {len(moving)}")
    print(f"moving rows with zero rear capacity : {rear_zero_cap} / {len(moving)}")
    print(
        "Interpretation rule: strong correlations support a candidate relationship, "
        "but field names remain provisional until writer/consumer dataflow and a "
        "controlled driving capture agree. This tool never changes FFB settings."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
