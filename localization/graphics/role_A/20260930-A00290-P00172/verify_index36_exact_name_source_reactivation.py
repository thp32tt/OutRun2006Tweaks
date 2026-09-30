#!/usr/bin/env python3
"""Fail-closed source-reactivation guard for A-owned index36 / 06AB5CEE.

This tool does not reacquire source bytes. It verifies the GitHub-SSOT
fingerprints that currently make index36 SOURCE_ACQUISITION_EXHAUSTED and
explicitly forbids filename/alias substitution while those fingerprints remain
unchanged. Any material dependency drift returns FRESH_RESCAN_REQUIRED.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

INDEX=36
ASSET="06AB5CEE"
QUEUE_PATH="textures/load/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.dds"
LOCKED_CANONICAL={
    "sha256":"e02db9b4e04747e2a74295e8f5a01e07f0ed88d31832f4169b1e5996bc30f1eb",
    "width":4096,"height":4096,"mode":"RGBA",
}
LOCKED_A00179_RESULT="7548b44b7364504c248341cce0771969f0793160"
PINNED_TAG="v0.25.10a"
PINNED_COMMIT="55f67a813dd3603d201d0be0da47c071965f53a4"
PINNED_ZIP_SHA256="76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"

def load_json(root,rel):
    return json.loads((root/rel).read_text(encoding="utf-8"))

def inventory_row(root):
    with (root/"localization/graphics/inventory.csv").open("r",encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            if row["path"]==QUEUE_PATH:
                return {"sha256":row["sha256"],"width":int(row["width"]),"height":int(row["height"]),"mode":row["mode"]}
    return None

def queue_row(root):
    with (root/"localization/graphics/asset_queue.csv").open("r",encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            if int(row["index"])==INDEX:
                return row
    return None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",default=".")
    args=ap.parse_args(); root=Path(args.repo_root)
    inv=inventory_row(root); queue=queue_row(root)
    a179=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00179.json")
    ev=load_json(root,"localization/graphics/role_A/20260930-0138-A00179-P00090/A00179_P00090_MOD3_SOURCE_ACQUISITION_EXHAUSTION.json")
    c136=load_json(root,"localization/graphics/role_C/20260930-0208-C136/C136_Q00034_INDEPENDENT_QA_BATCH.json")
    a285=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00285.json")
    a289=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00289.json")
    contract=(root/"docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md").read_text(encoding="utf-8")

    src=next((x for x in ev.get("source_results",[]) if x.get("index")==INDEX),None)
    cdisp=next((x for x in c136.get("qa_dispositions",[]) if x.get("task_id")=="LOCALIZATION-LOCALIZATION_A-00179" and x.get("result_sha")==LOCKED_A00179_RESULT),None)

    checks={
      "queue_identity": bool(queue and queue["path"]==QUEUE_PATH and queue["action"]=="localize_text" and INDEX%3==0),
      "canonical_inventory_identity": inv==LOCKED_CANONICAL,
      "a00179_result_identity": (a179.get("result_sha")==LOCKED_A00179_RESULT or a179.get("authoritative_result_sha")==LOCKED_A00179_RESULT),
      "a00179_index36_exact_name_exhausted": bool(src and src.get("final")=="SOURCE_ACQUISITION_EXHAUSTED" and src.get("canonical")==LOCKED_CANONICAL and src.get("drive",{}).get("outcome")=="SOURCE_TRANSPORT_MISS" and src.get("pinned_direct",{}).get("outcome")=="SOURCE_TRANSPORT_MISS" and src.get("pinned_release",{}).get("outcome")=="SOURCE_TRANSPORT_MISS"),
      "c136_accepts_exhaustion_only": bool(cdisp and cdisp.get("status")=="PASS" and c136.get("production_readiness",{}).get(str(INDEX))=="PREFLIGHT_ONLY" and INDEX in c136.get("source_acquisition_exhausted",[])),
      "a00285_tracks_sticky_index36": INDEX in a285.get("selection",{}).get("sticky_source_acquisition_not_repeated",[]),
      "a00289_is_qa_pending_and_disjoint": a289.get("automation_validation")=="PENDING" and a289.get("selection",{}).get("selected_index")==111,
      "pinned_source_policy_unchanged": PINNED_TAG in contract and PINNED_COMMIT in contract and PINNED_ZIP_SHA256 in contract,
      "alias_substitution_forbidden_by_evidence": bool(src and "no 6AB5CEE alias substitution allowed" in src.get("pinned_direct",{}).get("detail","") and "no filename-similarity substitution" in src.get("pinned_release",{}).get("detail","")),
    }
    unchanged=all(checks.values())
    out={
      "schema_version":1,"task_id":"LOCALIZATION-LOCALIZATION_A-00290","wave_id":"P00172","lane":"LOCALIZATION_A",
      "index":INDEX,"asset":ASSET,"queue_path":QUEUE_PATH,
      "checks":checks,"current_canonical":inv,"locked_canonical":LOCKED_CANONICAL,
      "alias_substitution_authorized":False,"source_reprobe_authorized":False,"candidate_rebuild_authorized":False,
      "reactivation_triggers":[
        "canonical inventory identity changes",
        "C disposition/source-acquisition state changes",
        "accepted A00179 result identity is superseded",
        "pinned source tag/commit/bundle digest policy changes",
        "an exact canonical 06AB5CEE source transport is newly recorded by authoritative C/producer evidence"
      ],
      "fresh_rescan_required":not unchanged,
      "result":"BLOCKED_UNCHANGED_EXACT_NAME_SOURCE_FINGERPRINT" if unchanged else "FRESH_RESCAN_REQUIRED",
      "runtime_validation":"UNTESTED"
    }
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
