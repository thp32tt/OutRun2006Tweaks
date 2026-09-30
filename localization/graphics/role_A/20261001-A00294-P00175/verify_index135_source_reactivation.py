#!/usr/bin/env python3
"""Fail-closed source-reactivation guard for A-owned index135 / 2B0863D6.

This tool never reacquires source bytes. It verifies the current GitHub-SSOT
fingerprints that keep index135 SOURCE_ACQUISITION_EXHAUSTED. If any dependency
changes, it requests a fresh rescan; otherwise it forbids Drive/direct/Release
re-probing and forbids substituting the verified-but-noncanonical pinned Release
member for the canonical inventory object.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

INDEX=135
ASSET="2B0863D6"
QUEUE_PATH="textures/load/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds"
LOCKED_CANONICAL={
    "sha256":"7cb768c657869981b0e548293f68975a84d4e2fb179f29a7568dbf096c365521",
    "width":2048,"height":256,"mode":"RGBA",
}
LOCKED_A00225_RESULT="06627778c8b433cf37820831f21be157777a0352"
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
    ev=load_json(root,"localization/graphics/role_A/20260930-A00225-P00119/A00225_P00119_INDEX135_SOURCE_ACQUISITION_EXHAUSTED.json")
    c164=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00293.json")
    a289=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00289.json")
    a286=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00286.json")
    a290=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00290.json")
    a291=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00291.json")
    a292=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00292.json")
    roles=load_json(root,"localization/controller_roles.json")
    contract=(root/"docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md").read_text(encoding="utf-8")

    canonical=None if inv is None else {
        "sha256":inv["sha256"],"width":int(inv["width"]),
        "height":int(inv["height"]),"mode":inv["mode"],
    }
    tiers=ev.get("acquisition_tiers",[])
    rr=c164.get("readiness_reconciliation",{})
    qnote="" if queue is None else queue.get("notes","")

    checks={
      "queue_identity": bool(queue and queue["path"]==QUEUE_PATH and queue["action"]=="localize_text" and INDEX%3==0),
      "queue_sticky_source_exhaustion": "SOURCE_ACQUISITION_EXHAUSTED sticky until dependency changes" in qnote,
      "canonical_inventory_identity": canonical==LOCKED_CANONICAL,
      "a00225_evidence_identity": ev.get("task_id")=="LOCALIZATION-LOCALIZATION_A-00225" and ev.get("asset",{}).get("index")==INDEX and ev.get("asset",{}).get("canonical_inventory",{}).get("sha256")==LOCKED_CANONICAL["sha256"],
      "a00225_source_exhausted": ev.get("final_source_outcome")=="SOURCE_ACQUISITION_EXHAUSTED",
      "a00225_drive_miss": len(tiers)>0 and tiers[0].get("outcome")=="SOURCE_TRANSPORT_MISS",
      "a00225_direct_miss": len(tiers)>1 and tiers[1].get("outcome")=="SOURCE_TRANSPORT_MISS" and tiers[1].get("http_status")==404,
      "a00225_release_mismatch": len(tiers)>2 and tiers[2].get("outcome")=="SOURCE_IDENTITY_MISMATCH" and tiers[2].get("member_sha256")==LOCKED_RELEASE_SHA256 and tiers[2].get("bundle_sha256")==PINNED_ZIP_SHA256,
      "c164_dependency_blocked": INDEX in rr.get("preflight_only_dependency_blocked_indices",[]),
      "c164_no_a_render_ready": all(i%3!=0 for i in rr.get("render_ready_indices",[])),
      "c164_no_a_one_stage": all(i%3!=0 for i in rr.get("one_stage_to_render_indices",[])),
      "c164_no_a_candidate_rework": all(i%3!=0 for i in rr.get("candidate_rework_indices",[])),
      "c164_a_candidate_qa_pending": all(i in rr.get("candidate_qa_pending_indices",[]) for i in (159,198,201)),
      "index111_pending_not_repeated": a289.get("selection",{}).get("selected_index")==111 and a289.get("automation_validation")=="PENDING",
      "prior_guard_chain_disjoint": a286.get("selection",{}).get("selected_index")==30 and a290.get("selection",{}).get("selected_index")==36 and a291.get("selection",{}).get("selected_index")==48 and a292.get("selection",{}).get("selected_index")==132,
      "controller_schema15_mod3": roles.get("schema_version")==15 and roles.get("lanes",{}).get("A",{}).get("primary_index_modulo_3")==0,
      "pinned_source_policy_unchanged": all(x in contract for x in (PINNED_TAG,PINNED_COMMIT,PINNED_ZIP_SHA256,DRIVE_FOLDER_ID)),
    }
    unchanged=all(checks.values())
    out={
      "schema_version":1,
      "task_id":"LOCALIZATION-LOCALIZATION_A-00294",
      "wave_id":"P00175",
      "lane":"LOCALIZATION_A",
      "index":INDEX,
      "asset":ASSET,
      "queue_path":QUEUE_PATH,
      "checks":checks,
      "current_canonical":canonical,
      "locked_canonical":LOCKED_CANONICAL,
      "locked_a00225_result_sha":LOCKED_A00225_RESULT,
      "source_reprobe_authorized":False,
      "release_member_substitution_authorized":False,
      "candidate_rebuild_authorized":False,
      "reactivation_triggers":[
        "canonical inventory identity for index135 changes",
        "C readiness/disposition stops classifying index135 as dependency-blocked SOURCE_ACQUISITION_EXHAUSTED",
        "A00225 exhaustion evidence is superseded or amended by authoritative C evidence",
        "pinned source tag/commit/bundle or approved Drive transport policy changes",
        "an exact canonical 2048x256 2B0863D6 source transport is newly recorded by authoritative evidence",
      ],
      "fresh_rescan_required":not unchanged,
      "result":"BLOCKED_UNCHANGED_SOURCE_ACQUISITION_EXHAUSTED_FINGERPRINT" if unchanged else "FRESH_RESCAN_REQUIRED",
      "runtime_validation":"UNTESTED",
    }
    print(json.dumps(out,ensure_ascii=False,indent=2))
    raise SystemExit(0 if unchanged else 2)

if __name__=="__main__":
    main()
