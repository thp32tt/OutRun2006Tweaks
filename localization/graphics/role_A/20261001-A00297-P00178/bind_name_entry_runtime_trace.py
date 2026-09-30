#!/usr/bin/env python3
"""Fail-closed runtime slot/UV/composition evidence binder for index24/66743AA8.

The canonical glyph geometry comes only from the C163-accepted A00279 report.
This tool does not infer runtime mapping from row/column order. It consumes
explicit runtime observations when available and reports whether they form a
complete, conflict-free mapping. Candidate generation remains unauthorized
until a later C disposition accepts sufficient runtime evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

GEOMETRY_REPORT = (
    "localization/graphics/role_A/20260930-A00279-P00163/"
    "A00279_P00163_INDEX24_NAME_ENTRY_ATLAS_PREFLIGHT.json"
)
EXPECTED_SOURCE_SHA256 = "7aa21de138af2d7f2aae54022a08f0aca79093a2a34a2bd74a87a442efaa60aa"
ATLAS_SIZE = 4096
TASK_ID = "LOCALIZATION-LOCALIZATION_A-00297"
WAVE_ID = "P00178"

def area(rect):
    x0, y0, x1, y1 = rect
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)

def intersection(a, b):
    x0=max(a[0],b[0]); y0=max(a[1],b[1])
    x1=min(a[2],b[2]); y1=min(a[3],b[3])
    return max(0.0,x1-x0)*max(0.0,y1-y0)

def normalize_rect(rec):
    rect=[float(x) for x in rec["uv_rect"]]
    space=rec.get("space")
    if space == "normalized_raw":
        return [x * ATLAS_SIZE for x in rect], "raw_px"
    if space in ("raw_px", "readable_px"):
        return rect, space
    raise ValueError("space must be raw_px, readable_px, or normalized_raw")

def load_geometry(root):
    doc=json.loads((root/GEOMETRY_REPORT).read_text(encoding="utf-8"))
    source=doc["source_acquisition"]["pinned_release"]
    if source["member_sha256"] != EXPECTED_SOURCE_SHA256:
        raise ValueError("A00279 canonical source fingerprint drift")
    glyphs=[]
    for row in doc["glyph_geometry"]["glyphs"]:
        glyphs.append({
            "visual_label":row[0],
            "row":row[1],
            "col":row[2],
            "readable_bbox":[row[3],row[4],row[5],row[6]],
            "raw_bbox":[row[7],row[8],row[9],row[10]],
            "alpha_nonzero_pixels":row[11],
        })
    if len(glyphs) != 48:
        raise ValueError("canonical glyph count drift")
    return doc, glyphs

def match_glyph(rect, space, glyphs):
    scored=[]
    for g in glyphs:
        box=g["raw_bbox"] if space == "raw_px" else g["readable_bbox"]
        denom=min(area(rect),area(box))
        score=0.0 if denom <= 0 else intersection(rect,box)/denom
        if score > 0:
            scored.append((score,g))
    scored.sort(key=lambda x:x[0], reverse=True)
    if not scored or scored[0][0] < 0.50:
        return {"status":"UNMATCHED","score":scored[0][0] if scored else 0.0}
    if len(scored)>1 and abs(scored[0][0]-scored[1][0]) < 0.05:
        return {
            "status":"AMBIGUOUS",
            "score":scored[0][0],
            "labels":[scored[0][1]["visual_label"],scored[1][1]["visual_label"]],
        }
    g=scored[0][1]
    return {
        "status":"MATCH",
        "score":scored[0][0],
        "visual_label":g["visual_label"],
        "row":g["row"],
        "col":g["col"],
    }

def has_hangul(text):
    return any(
        "\uac00" <= ch <= "\ud7a3"
        or "\u1100" <= ch <= "\u11ff"
        or "\u3130" <= ch <= "\u318f"
        for ch in text
    )

def analyze(root, observations):
    doc,glyphs=load_geometry(root)
    selections=[]
    compositions=[]
    errors=[]
    slot_to_label={}
    label_to_slots={}
    for line_no,rec in observations:
        kind=rec.get("kind")
        if kind == "selection_uv":
            try:
                idx=int(rec["selection_index"])
                rect,space=normalize_rect(rec)
                matched=match_glyph(rect,space,glyphs)
            except Exception as exc:
                errors.append({"line":line_no,"error":str(exc)})
                continue
            item={
                "line":line_no,
                "selection_index":idx,
                "space":space,
                "uv_rect":rect,
                "match":matched,
                "reported_visual_label":rec.get("visual_label"),
            }
            selections.append(item)
            if matched.get("status") == "MATCH":
                label=matched["visual_label"]
                slot_to_label.setdefault(idx,set()).add(label)
                label_to_slots.setdefault(label,set()).add(idx)
                if rec.get("visual_label") is not None and rec.get("visual_label") != label:
                    errors.append({
                        "line":line_no,
                        "error":"REPORTED_LABEL_MISMATCH",
                        "reported":rec.get("visual_label"),
                        "matched":label,
                    })
        elif kind == "composition":
            indices=rec.get("selection_indices")
            result=rec.get("result_utf8")
            if not isinstance(indices,list) or not all(isinstance(x,int) for x in indices):
                errors.append({"line":line_no,"error":"INVALID_COMPOSITION_SELECTION_INDICES"})
                continue
            if not isinstance(result,str):
                errors.append({"line":line_no,"error":"INVALID_COMPOSITION_RESULT"})
                continue
            compositions.append({
                "line":line_no,
                "selection_indices":indices,
                "result_utf8":result,
                "committed":bool(rec.get("committed",False)),
                "hangul_observed":has_hangul(result),
            })
        else:
            errors.append({"line":line_no,"error":"UNKNOWN_EVENT_KIND"})

    slot_conflicts={str(k):sorted(v) for k,v in slot_to_label.items() if len(v)>1}
    label_conflicts={k:sorted(v) for k,v in label_to_slots.items() if len(v)>1}
    resolved={str(k):next(iter(v)) for k,v in slot_to_label.items() if len(v)==1}
    expected_labels=[g["visual_label"] for g in glyphs]
    complete=(
        len(resolved)==48
        and len(set(resolved.values()))==48
        and not slot_conflicts
        and not label_conflicts
        and not errors
    )
    row_major=False
    if complete:
        try:
            row_major=all(resolved[str(i)]==expected_labels[i] for i in range(48))
        except KeyError:
            row_major=False

    any_hangul=any(x["hangul_observed"] and x["committed"] for x in compositions)
    if complete and any_hangul:
        readiness="PREFLIGHT_ONLY_RUNTIME_MAPPING_EVIDENCE_READY_FOR_C_REVIEW"
    elif observations:
        readiness="PREFLIGHT_ONLY_RUNTIME_TRACE_INCOMPLETE_OR_CONFLICTING"
    else:
        readiness="PREFLIGHT_ONLY_RUNTIME_TRACE_REQUIRED"

    return {
        "schema_version":1,
        "schema":"outrun-a00297-index24-name-entry-runtime-trace-binding-v1",
        "task_id":TASK_ID,
        "wave_id":WAVE_ID,
        "asset":"66743AA8",
        "queue_index":24,
        "canonical_source_sha256":EXPECTED_SOURCE_SHA256,
        "canonical_geometry_report":GEOMETRY_REPORT,
        "canonical_glyph_count":48,
        "canonical_visual_labels_row_major":expected_labels,
        "observations":{
            "selection_events":selections,
            "composition_events":compositions,
            "parse_errors":errors,
        },
        "mapping":{
            "resolved_slot_to_visual_label":resolved,
            "slot_conflicts":slot_conflicts,
            "visual_label_conflicts":label_conflicts,
            "complete_48_unique_mapping":complete,
            "matches_visual_row_major_order":row_major if complete else None,
        },
        "composition":{
            "committed_hangul_result_observed":any_hangul,
            "event_count":len(compositions),
        },
        "production_readiness":readiness,
        "candidate_dds_authorized":False,
        "runtime_validation":"UNTESTED",
        "note":"This binder validates supplied runtime evidence only. It never infers slot/UV mapping from A00279 visual row order and never grants runtime PASS.",
    }

def read_observations(path):
    if path is None:
        return []
    out=[]
    for line_no,line in enumerate(Path(path).read_text(encoding="utf-8",errors="replace").splitlines(),1):
        if not line.strip():
            continue
        try:
            out.append((line_no,json.loads(line)))
        except Exception as exc:
            out.append((line_no,{"kind":"__parse_error__","_error":str(exc)}))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--observations",help="JSONL runtime observations; omit to emit fail-closed contract state")
    ap.add_argument("--json-out")
    args=ap.parse_args()
    root=Path(args.repo_root)
    observations=read_observations(args.observations)
    result=analyze(root,observations)
    payload=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.json_out:
        Path(args.json_out).write_text(payload,encoding="utf-8")
    print(payload,end="")

if __name__ == "__main__":
    main()
