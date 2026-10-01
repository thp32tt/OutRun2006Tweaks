#!/usr/bin/env python3
"""Fail-closed source-dependency reactivation guard for A-owned index135/2B0863D6.

This tool performs no network or source acquisition. It replays current GitHub-SSOT
metadata against the C152-accepted A00225 SOURCE_ACQUISITION_EXHAUSTED fingerprint.
Unchanged dependencies keep source reprobes and noncanonical Release substitution
forbidden. A dependency change exits non-zero and requests a fresh producer rescan.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

INDEX=135
ASSET="2B0863D6"
QUEUE_PATH="textures/load/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds"
LOCKED_CANONICAL={"sha256":"7cb768c657869981b0e548293f68975a84d4e2fb179f29a7568dbf096c365521","width":2048,"height":256,"mode":"RGBA"}
LOCKED_A00225_RESULT="06627778c8b433cf37820831f21be157777a0352"
LOCKED_C152_RESULT="648cfaab4a7bd5c01ca2a6aa21d775291235a942"
LOCKED_RELEASE_SHA256="dafe21ec29ace60273f3ec10a40072446f3f28232b3f9a8acce3897ade1eff06"
PINNED_TAG="v0.25.10a"
PINNED_COMMIT="55f67a813dd3603d201d0be0da47c071965f53a4"
PINNED_ZIP_SHA256="76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
DRIVE_FOLDER_ID="1TpFYOgf0ulxmj6lJozHjAS-69asQajXr"

def load_json(root, rel):
    return json.loads((root/rel).read_text(encoding="utf-8"))

def csv_row(root, rel, key, value):
    with (root/rel).open("r",encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            if row.get(key)==value:
                return row
    return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=".")
    args=ap.parse_args()
    root=Path(args.repo_root)
    inv=csv_row(root,"localization/graphics/inventory.csv","path",QUEUE_PATH)
    queue=csv_row(root,"localization/graphics/asset_queue.csv","index",str(INDEX))
    prod=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00225.json")
    ev=load_json(root,"localization/graphics/role_A/20260930-A00225-P00119/A00225_P00119_INDEX135_SOURCE_ACQUISITION_EXHAUSTED.json")
    c152=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00228.json")
    roles=load_json(root,"localization/controller_roles.json")
    contract=(root/"docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md").read_text(encoding="utf-8")
    canonical=None if inv is None else {"sha256":inv["sha256"],"width":int(inv["width"]),"height":int(inv["height"]),"mode":inv["mode"]}
    tiers={x.get("tier"):x for x in ev.get("acquisition_tiers",[])}
    c_input=next((x for x in c152.get("qa_batch_inputs",[]) if x.get("task_id")=="LOCALIZATION-LOCALIZATION_A-00225"),None)
    c_disp=next((x for x in c152.get("qa_dispositions",[]) if x.get("task_id")=="LOCALIZATION-LOCALIZATION_A-00225"),None)
    qnote="" if queue is None else queue.get("notes","")
    checks={
      "queue_identity_current_a_shard": bool(queue and queue.get("path")==QUEUE_PATH and queue.get("action")=="localize_text" and INDEX%3==0),
      "queue_retains_c152_source_exhaustion": "Q00050 C152 consumed A00225@06627778 PASS PREFLIGHT_ONLY" in qnote and "SOURCE_ACQUISITION_EXHAUSTED sticky until dependency changes" in qnote,
      "canonical_inventory_identity": canonical==LOCKED_CANONICAL,
      "a00225_result_identity": prod.get("authoritative_result_sha")==LOCKED_A00225_RESULT,
      "drive_exact_path_miss": tiers.get(1,{}).get("outcome")=="SOURCE_TRANSPORT_MISS" and tiers.get(1,{}).get("exact_name_results")==0,
      "pinned_direct_404": tiers.get(2,{}).get("outcome")=="SOURCE_TRANSPORT_MISS" and tiers.get(2,{}).get("http_status")==404,
      "release_noncanonical": tiers.get(3,{}).get("member_sha256")==LOCKED_RELEASE_SHA256 and tiers.get(3,{}).get("canonical_expected_sha256")==LOCKED_CANONICAL["sha256"] and tiers.get(3,{}).get("canvas_match") is True and tiers.get(3,{}).get("outcome")=="SOURCE_IDENTITY_MISMATCH",
      "final_source_exhaustion": ev.get("final_source_outcome")=="SOURCE_ACQUISITION_EXHAUSTED",
      "c152_exact_input_pass": bool(c_input and c_input.get("result_sha")==LOCKED_A00225_RESULT and c_disp and c_disp.get("status")=="PASS"),
      "c152_validation_identity": c152.get("validation_bearing_result_sha")==LOCKED_C152_RESULT and c152.get("automation_validation")=="PASS",
      "schema30_current_a_ownership": roles.get("schema_version")==30 and roles.get("lanes",{}).get("A",{}).get("primary_index_modulo_3")==0,
      "source_transport_policy_current": roles.get("source_transport",{}).get("acquisition_order")==["GOOGLE_DRIVE_EXACT_RELATIVE_PATH","PINNED_UPSTREAM_DIRECT_FILE","PINNED_V0.25.10A_RELEASE"] and roles.get("source_transport",{}).get("canonical_hd_source",{}).get("folder_id")==DRIVE_FOLDER_ID,
      "sticky_source_guard_policy": roles.get("production_strategy",{}).get("source_exhaustion_reselection",{}).get("skip_unchanged_source_acquisition_exhausted") is True,
      "pinned_policy_tokens_current": all(x in contract for x in (PINNED_TAG,PINNED_COMMIT,PINNED_ZIP_SHA256,DRIVE_FOLDER_ID)),
    }
    unchanged=all(checks.values())
    out={
      "schema_version":30,"task_id":"LOCALIZATION-LOCALIZATION_A-00378","wave_id":"P00246","lane":"LOCALIZATION_A",
      "index":INDEX,"asset":ASSET,"queue_path":QUEUE_PATH,"checks":checks,
      "current_canonical":canonical,"locked_canonical":LOCKED_CANONICAL,
      "locked_a00225_result_sha":LOCKED_A00225_RESULT,"locked_c152_validation_bearing_result_sha":LOCKED_C152_RESULT,
      "locked_release_sha256":LOCKED_RELEASE_SHA256,
      "source_reprobe_authorized":False,"release_member_substitution_authorized":False,"candidate_rebuild_authorized":False,
      "reactivation_triggers":["index135 canonical inventory identity changes","asset_queue no longer retains C152/A00225 source exhaustion","C152/A00225 evidence is superseded by authoritative C evidence","pinned source tag/commit/bundle or approved Drive transport policy changes","an exact canonical 2B0863D6 source transport is newly recorded by authoritative evidence"],
      "fresh_rescan_required":not unchanged,
      "result":"BLOCKED_UNCHANGED_SOURCE_ACQUISITION_EXHAUSTED_FINGERPRINT" if unchanged else "FRESH_RESCAN_REQUIRED",
      "runtime_validation":"UNTESTED"}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    raise SystemExit(0 if unchanged else 2)
if __name__=="__main__":
    main()
