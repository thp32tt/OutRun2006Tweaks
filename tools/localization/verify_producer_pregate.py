#!/usr/bin/env python3
"""Fast producer-side pre-gate for graphics QA evidence.

This is intentionally lane-local: it reads one or more JSON QA reports and never
touches shared state, candidate DDS files, the queue, or Git.  It catches the
repeat causes of C rework before a producer publishes a result.
"""
from __future__ import annotations
import argparse, json, pathlib, sys

ZERO_KEYS={
 "changed_pixels_outside_edit_mask",
 "changed_pixels_outside_source_region",
 "changed_pixels_outside_exact_source_bboxes",
 "changed_pixels_outside_safe_bboxes",
 "changed_pixels_in_protected_mask",
 "introduced_alpha_outside_source_region",
 "alpha_changed_outside_edit_mask",
 "alpha_changed_outside_exact_source_bboxes",
 "source_style_residue_pixels",
}
FORBIDDEN=("lanczos","flattened_raster","flattened-raster","shrink","trim")
METHOD_KEYS=("method","operation","repair","render_method","lettering_method","resample","transform")

def walk(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values(): yield from walk(v)
    elif isinstance(obj,list):
        for v in obj: yield from walk(v)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("reports",nargs="+",type=pathlib.Path)
    ns=ap.parse_args()
    errors=[]; saw_pass=False; saw_zero=False; saw_v2=False; saw_slant=False
    for path in ns.reports:
        try: obj=json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"{path}: unreadable JSON: {e}"); continue
        for d in walk(obj):
            status=" ".join(str(d.get(k,"")) for k in ("status","result","self_qa")).upper()
            if "PASS" in status: saw_pass=True
            contract=str(d.get("prompt_contract",d.get("contract","")))
            if contract=="outrun-first-pass-edit-v2": saw_v2=True
            if str(d.get("signed_slant_gate","")).upper()=="PASS": saw_slant=True
            for k in ZERO_KEYS:
                if k in d:
                    saw_zero=True
                    try:
                        if int(d[k]) != 0: errors.append(f"{path}: {k}={d[k]} (must be 0)")
                    except Exception: errors.append(f"{path}: {k} is not an integer")
            for k in METHOD_KEYS:
                if k in d:
                    val=str(d[k]).lower()
                    if any(tok in val for tok in FORBIDDEN):
                        errors.append(f"{path}: forbidden flattened-raster/refit operation in {k}={d[k]!r}")
    if not saw_pass: errors.append("no machine-readable PASS evidence")
    if not saw_zero: errors.append("no zero-pixel containment/protected/alpha metric found")
    if not saw_v2: errors.append("missing outrun-first-pass-edit-v2 evidence")
    if not saw_slant: errors.append("missing signed_slant_gate=PASS")
    if errors:
        print("PRODUCER_PRE_GATE_FAIL")
        for e in errors: print(f"- {e}")
        return 1
    print("PRODUCER_PRE_GATE_PASS")
    print("Runtime/in-game validation is separate and remains UNTESTED unless actually performed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
