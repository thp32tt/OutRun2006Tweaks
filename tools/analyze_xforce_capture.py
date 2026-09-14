#!/usr/bin/env python3
"""Analyze OutRun wheel X-Force research captures.

This tool is deliberately diagnostic-only. It pairs the physics-side
"WheelFFB XFORCE60" records with the input-side
"WheelFFB XFORCE_NEIGHBORS" records and compares actionforce_DBC plus its two
adjacent unknown floats (field_DC0 / field_DC4) against steering, the Modern SAT
model, estimated front slip and yaw rate.

Correlation is evidence for further reverse engineering, not proof that a field
is a steering-rack or tyre force. No setting or source file is modified.
"""

from __future__ import annotations

import argparse
import bisect
import math
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


PHYSICS_MARKER = "WheelFFB XFORCE60 "
NEIGHBOR_MARKER = "WheelFFB XFORCE_NEIGHBORS "
PAIR_TOLERANCE_MS = 25
MAX_SAMPLE_LAG = 2
CURRENT_XFORCE_FULL_SCALE = 62.0
KEY_VALUE_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)=([^\s]+)")


@dataclass
class Row:
    tick: int
    values: Dict[str, float]


def parse_number(text: str) -> Optional[float]:
    text = text.rstrip(",;)]")
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return 1.0 if lowered == "true" else 0.0
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def parse_record(line: str, marker: str) -> Optional[Row]:
    pos = line.find(marker)
    if pos < 0:
        return None

    payload = line[pos + len(marker):]
    values: Dict[str, float] = {}
    for match in KEY_VALUE_RE.finditer(payload):
        value = parse_number(match.group(2))
        if value is not None:
            values[match.group(1)] = value

    tick_value = values.get("t")
    if tick_value is None:
        return None
    return Row(int(tick_value) & 0xFFFFFFFF, values)


def load_capture(path: Path) -> Tuple[List[Row], List[Row]]:
    physics: List[Row] = []
    neighbors: List[Row] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if PHYSICS_MARKER in line:
                row = parse_record(line, PHYSICS_MARKER)
                if row:
                    physics.append(row)
            elif NEIGHBOR_MARKER in line:
                row = parse_record(line, NEIGHBOR_MARKER)
                if row:
                    neighbors.append(row)
    return physics, neighbors


def monotonic_segment(rows: Sequence[Row]) -> List[Row]:
    """Keep the largest nondecreasing GetTickCount segment."""
    if not rows:
        return []
    segments: List[List[Row]] = [[]]
    previous = rows[0].tick
    for row in rows:
        if segments[-1] and row.tick < previous:
            segments.append([])
        segments[-1].append(row)
        previous = row.tick
    return max(segments, key=len)


def pair_rows(physics: Sequence[Row], neighbors: Sequence[Row]) -> List[Tuple[Row, Row, int]]:
    if not physics or not neighbors:
        return []

    neighbor_ticks = [row.tick for row in neighbors]
    pairs: List[Tuple[Row, Row, int]] = []
    next_neighbor = 0
    for physics_row in physics:
        # Match only against still-unused input-side records. Reusing one
        # candidate sample for multiple physics rows biases distributions and
        # can artificially strengthen correlation.
        index = bisect.bisect_left(
            neighbor_ticks, physics_row.tick, lo=next_neighbor)
        candidate_indices: List[int] = []
        if index < len(neighbors):
            candidate_indices.append(index)
        if index > next_neighbor:
            candidate_indices.append(index - 1)
        if not candidate_indices:
            continue
        chosen = min(
            candidate_indices,
            key=lambda i: abs(neighbors[i].tick - physics_row.tick))
        delta = abs(neighbors[chosen].tick - physics_row.tick)
        if delta <= PAIR_TOLERANCE_MS:
            pairs.append((physics_row, neighbors[chosen], delta))
            next_neighbor = chosen + 1
    return pairs


def percentile(values: Sequence[float], q: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return ordered[lo]
    fraction = position - lo
    return ordered[lo] * (1.0 - fraction) + ordered[hi] * fraction


def pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    denom_x = math.sqrt(sum(value * value for value in dx))
    denom_y = math.sqrt(sum(value * value for value in dy))
    denom = denom_x * denom_y
    if denom <= 1e-12:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / denom


def lagged_paired_values(
    pairs: Sequence[Tuple[Row, Row, int]],
    candidate: str,
    target: str,
    lag: int,
) -> Tuple[List[float], List[float]]:
    """Return candidate/target samples with an input-record lag.

    lag +1 means the candidate comes from the next input record relative to the
    current physics record; lag -1 means it comes from the previous input record.
    This matters because input sampling can occur just before the physics update.
    """
    xs: List[float] = []
    ys: List[float] = []
    start = max(0, -lag)
    stop = min(len(pairs), len(pairs) - lag)
    for physics_index in range(start, stop):
        neighbor_index = physics_index + lag
        physics = pairs[physics_index][0]
        neighbor = pairs[neighbor_index][1]
        x = neighbor.values.get(candidate)
        y = physics.values.get(target)
        if x is None or y is None:
            continue
        xs.append(x)
        ys.append(y)
    return xs, ys


def best_lag_correlation(
    pairs: Sequence[Tuple[Row, Row, int]], candidate: str, target: str
) -> Tuple[Optional[float], int]:
    best_r: Optional[float] = None
    best_lag = 0
    for lag in range(-MAX_SAMPLE_LAG, MAX_SAMPLE_LAG + 1):
        xs, ys = lagged_paired_values(pairs, candidate, target, lag)
        r = pearson(xs, ys)
        if r is not None and (best_r is None or abs(r) > abs(best_r)):
            best_r = r
            best_lag = lag
    return best_r, best_lag


def fmt(value: Optional[float], digits: int = 4) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_corr(value: Optional[float], lag: int) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.3f}@{lag:+d}"


def summarize_candidate(
    pairs: Sequence[Tuple[Row, Row, int]], candidate: str
) -> Dict[str, object]:
    samples = [
        neighbor.values[candidate]
        for _, neighbor, _ in pairs
        if candidate in neighbor.values
    ]
    magnitudes = [abs(value) for value in samples]
    deltas: List[float] = []
    previous: Optional[float] = None
    for value in samples:
        if previous is not None:
            deltas.append(value - previous)
        previous = value

    result: Dict[str, object] = {
        "count": len(samples),
        "p50": percentile(magnitudes, 0.50),
        "p90": percentile(magnitudes, 0.90),
        "p95": percentile(magnitudes, 0.95),
        "p99": percentile(magnitudes, 0.99),
        "max": max(magnitudes) if magnitudes else None,
        "delta_rms": math.sqrt(statistics.fmean([d * d for d in deltas])) if deltas else None,
    }

    p99 = result["p99"]
    result["equivalent_gain"] = (
        CURRENT_XFORCE_FULL_SCALE / p99
        if isinstance(p99, float) and p99 > 1e-6
        else None
    )

    for target in ("steer", "modern", "frontSlip", "yaw"):
        corr, lag = best_lag_correlation(pairs, candidate, target)
        result[f"corr_{target}"] = corr
        result[f"lag_{target}"] = lag
    return result


def print_table(pairs: Sequence[Tuple[Row, Row, int]]) -> None:
    candidates = ("dbc", "dc0", "dc4")
    summaries = {name: summarize_candidate(pairs, name) for name in candidates}

    print("\nCandidate magnitude / responsiveness")
    print("candidate  samples      p50      p90      p95      p99      max   deltaRMS  62/p99")
    for name in candidates:
        s = summaries[name]
        print(
            f"{name:9s} {int(s['count']):7d} "
            f"{fmt(s['p50']):>8s} {fmt(s['p90']):>8s} {fmt(s['p95']):>8s} "
            f"{fmt(s['p99']):>8s} {fmt(s['max']):>8s} {fmt(s['delta_rms']):>10s} "
            f"{fmt(s['equivalent_gain'], 3):>7s}"
        )

    print(f"\nBest signed Pearson correlation within +/-{MAX_SAMPLE_LAG} input records (r@lag)")
    print("candidate       steer       modern    frontSlip          yaw")
    for name in candidates:
        s = summaries[name]
        print(
            f"{name:9s} "
            f"{fmt_corr(s['corr_steer'], int(s['lag_steer'])):>11s} "
            f"{fmt_corr(s['corr_modern'], int(s['lag_modern'])):>12s} "
            f"{fmt_corr(s['corr_frontSlip'], int(s['lag_frontSlip'])):>12s} "
            f"{fmt_corr(s['corr_yaw'], int(s['lag_yaw'])):>12s}"
        )

    sanity_r, sanity_lag = best_lag_correlation(pairs, "dbc", "raw")
    print(
        "\nPairing sanity: best corr(XFORCE60.raw, NEIGHBORS.dbc) = "
        f"{fmt_corr(sanity_r, sanity_lag)}"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze WheelFFB XFORCE60/XFORCE_NEIGHBORS log records without modifying FFB settings."
    )
    parser.add_argument("log", type=Path, help="OutRun2006Tweaks.log capture file")
    args = parser.parse_args(argv)

    if not args.log.is_file():
        parser.error(f"log file not found: {args.log}")

    physics, neighbors = load_capture(args.log)
    physics = monotonic_segment(physics)
    neighbors = monotonic_segment(neighbors)

    print(f"physics XFORCE60 samples : {len(physics)}")
    print(f"neighbor samples         : {len(neighbors)}")
    if not physics:
        print("No XFORCE60 records found. Enable WheelFFB XForceCapture60Hz and drive a representative lap.", file=sys.stderr)
        return 2
    if not neighbors:
        print(
            "No XFORCE_NEIGHBORS records found. Confirm this wheel build contains the research capture hook and that XForceCapture60Hz is enabled.",
            file=sys.stderr,
        )
        return 3

    pairs = pair_rows(physics, neighbors)
    print(f"paired within {PAIR_TOLERANCE_MS} ms      : {len(pairs)}")
    if len(pairs) < 30:
        print(
            "Too few paired samples for useful inference; capture a longer section with straights, loaded corners, understeer and counter-steer.",
            file=sys.stderr,
        )
        return 4

    deltas = [delta for _, _, delta in pairs]
    print(
        "pair time delta ms       : "
        f"median={fmt(percentile(deltas, 0.50), 1)} "
        f"p95={fmt(percentile(deltas, 0.95), 1)} max={max(deltas)}"
    )
    print_table(pairs)

    print(
        "\nLag convention: +1 uses the next input-side candidate record against the current physics record; "
        "-1 uses the previous record. This protects the comparison from a one-tick input/physics phase offset."
    )
    print(
        "Interpretation guard: correlation and p99 magnitude can identify promising fields, "
        "but they do not prove tyre/rack-force semantics. Confirm a candidate from its write-site "
        "or controlled driving tests before routing it into FFB. The 62/p99 column is only the "
        "gain that would map that observed p99 to the current DBC nominal scale; it is not an "
        "automatic tuning recommendation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
