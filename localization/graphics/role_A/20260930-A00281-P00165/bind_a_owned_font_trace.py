#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

RE_RESOLVER = re.compile(r"KoreanLocalizationTrace: text_id=(\\d+) original='(.*?)' returned='(.*?)' proof_override=(true|false)")
RE_FONT = re.compile(
    r"KoreanK3Trace: font_state handle=0x([0-9A-Fa-f]{8}) texture=(\\S+) kerning=(\\S+) "
    r"tex=(\\d+)x(\\d+) cell=(-?\\d+)x(-?\\d+) cursor=\\((-?\\d+), (-?\\d+)\\) "
    r"scale=\\(([-+0-9.eE]+), ([-+0-9.eE]+)\\) color=0x([0-9A-Fa-f]{8}) "
    r"layer=(\\d+) base_code=(\\d+) flags=0x([0-9A-Fa-f]{8}) "
    r"spacing=([-+0-9.eE]+) line_advance=([-+0-9.eE]+)"
)
RE_WIDTH = re.compile(r"KoreanK3Trace: width_text='(.*?)' bytes=(\\d+) high_bit=(true|false)")

TARGETS = {
    0: {"index": 18, "asset_hash": "7B65A191", "stock_size": [256, 128], "cell": [12, 12], "base_code": 0, "spacing": 0.0},
    2: {"index": 21, "asset_hash": "D7CE8BC3", "stock_size": [512, 256], "cell": [22, 26], "base_code": 32, "spacing": 0.0},
    9: {"index": 15, "asset_hash": "20389D70", "stock_size": [512, 256], "cell": [17, 17], "base_code": 32, "spacing": 2.0},
}

def analyze(text):
    resolver_by_text = {}
    events = []
    for line_no, line in enumerate(text.splitlines(), 1):
        m = RE_RESOLVER.search(line)
        if m:
            rec = {"line": line_no, "text_id": int(m.group(1)), "original": m.group(2), "returned": m.group(3)}
            for value in (rec["original"], rec["returned"]):
                resolver_by_text.setdefault(value, set()).add(rec["text_id"])
            events.append(("resolver", rec))
            continue
        m = RE_FONT.search(line)
        if m:
            events.append(("font", {
                "line": line_no,
                "handle": int(m.group(1), 16),
                "handle_hex": "0x" + m.group(1).upper(),
                "texture_size": [int(m.group(4)), int(m.group(5))],
                "cell": [int(m.group(6)), int(m.group(7))],
                "base_code": int(m.group(14)),
                "letter_spacing": float(m.group(16)),
            }))
            continue
        m = RE_WIDTH.search(line)
        if m:
            events.append(("width", {
                "line": line_no,
                "text": m.group(1),
                "bytes": int(m.group(2)),
                "high_bit": m.group(3) == "true",
            }))

    observations = {handle: [] for handle in TARGETS}
    for pos, (kind, rec) in enumerate(events):
        if kind != "font" or rec["handle"] not in TARGETS:
            continue
        expected = TARGETS[rec["handle"]]
        mismatches = []
        for field, want, got in (
            ("texture_size", expected["stock_size"], rec["texture_size"]),
            ("cell", expected["cell"], rec["cell"]),
            ("base_code", expected["base_code"], rec["base_code"]),
            ("letter_spacing", expected["spacing"], rec["letter_spacing"]),
        ):
            if want != got:
                mismatches.append({"field": field, "expected": want, "actual": got})

        binding = None
        if pos + 1 < len(events) and events[pos + 1][0] == "width":
            width = events[pos + 1][1]
            binding = {
                "rule": "immediate_next_unique_width_event_same_trace_stream",
                "width_line": width["line"],
                "text": width["text"],
                "resolver_text_ids": sorted(resolver_by_text.get(width["text"], set())),
            }

        observations[rec["handle"]].append({
            "font_state": rec,
            "descriptor_match": not mismatches,
            "mismatches": mismatches,
            "first_width_binding": binding,
        })

    targets = []
    for handle, expected in TARGETS.items():
        obs = observations[handle]
        if not obs:
            status = "RUNTIME_HANDLE_NOT_OBSERVED"
        elif any(not item["descriptor_match"] for item in obs):
            status = "RUNTIME_DESCRIPTOR_MISMATCH"
        elif any(item["first_width_binding"] and item["first_width_binding"]["resolver_text_ids"] for item in obs):
            status = "RUNTIME_HANDLE_OBSERVED_BOUND_TO_TEXT_ID"
        elif any(item["first_width_binding"] for item in obs):
            status = "RUNTIME_HANDLE_OBSERVED_WIDTH_ONLY"
        else:
            status = "RUNTIME_HANDLE_OBSERVED_UNBOUND"
        targets.append({
            "index": expected["index"],
            "asset_hash": expected["asset_hash"],
            "resource_handle": handle,
            "status": status,
            "observations": obs,
        })

    return {
        "schema_version": 1,
        "purpose": "A-owned font-pipeline runtime trace binding; fail closed and never infer runtime PASS",
        "targets": targets,
        "summary": {
            "all_three_target_handles_observed": all(x["observations"] for x in targets),
            "any_descriptor_mismatch": any(any(not y["descriptor_match"] for y in x["observations"]) for x in targets),
            "safe_repurpose_inferred": False,
            "candidate_dds_authorized": False,
            "runtime_validation": "UNTESTED",
        },
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log")
    parser.add_argument("--json-out")
    args = parser.parse_args()
    result = analyze(Path(args.log).read_text(encoding="utf-8", errors="replace"))
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    print(payload, end="")

if __name__ == "__main__":
    main()
