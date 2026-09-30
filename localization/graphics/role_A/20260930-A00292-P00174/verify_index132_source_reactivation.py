#!/usr/bin/env python3
"""Fail-closed source-reactivation guard for A-owned index132 / 1F5FE6E9.

This tool never reacquires source bytes. It verifies the GitHub-SSOT
fingerprints that currently make index132 SOURCE_ACQUISITION_EXHAUSTED and
forbids substituting the noncanonical 4096x2048 pinned object for the current
1024x512 canonical inventory object. Dependency drift requests a fresh rescan.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

INDEX=132
ASSET="1F5FE6E9"
QUEUE_PATH="textures/load/spr_sprani_sumo_fe_cvt_Exst/1F5FE6E9_1024x512.dds"
LOCKED_CANONICAL={
    "sha256":"3656adbd699b7852cb5fcf4bb01fc4f1f65bbd9d7d39e12e7a1c2ac5a49fef1d",
    "width":1024,"height":512,"mode":"RGBA",
}
LOCKED_A00179_RESULT="7548b44b7364504c248341cce0771969f0793160"
LOCKED_DIRECT_BLOB="a89e403c92d335f83c808e5f10dcc9e584d4ff7c"
LOCKED_RELEASE_SHA256="2a02471fe95e0c4253cf72ec58423cb9d16ae074e3012418716e88e75e2a2a80"
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
    a179=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00179.json")
    ev=load_json(root,"localization/graphics/role_A/20260930-0138-A00179-P00090/A00179_P00090_MOD3_SOURCE_ACQUISITION_EXHAUSTION.json")
    c136=load_json(root,"localization/graphics/role_C/20260930-0208-C136/C136_Q00034_INDEPENDENT_QA_BATCH.json")
    c163=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00288.json")
    a285=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00285.json")
    a286=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00286.json")
    a290=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00290.json")
    a291=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00291.json")
    contract=(root/"docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md").read_text(encoding="utf-8")
    roles=load_json(root,"localization/controller_roles.json")

    canonical=None if inv is None else {
        "sha256":inv["sha256"],"width":int(inv["width"]),
        "height":int(inv["height"]),"mode":inv["mode"],
    }
    src=next((x for x in ev.get("source_results",[]) if x.get("index")==INDEX),None)
    cdisp=next((x for x in c136.get("qa_dispositions",[])
        if x.get("task_id")=="LOCALIZATION-LOCALIZATION_A-00179"
        and x.get("result_sha")==LOCKED_A00179_RESULT),None)
    rr=c163.get("readiness_reconciliation",{})

    checks={
      "queue_identity": bool(queue and queue["path"]==QUEUE_PATH and queue["action"]=="localize_text" and INDEX%3==0),
      "canonical_inventory_identity": canonical==LOCKED_CANONICAL,
      "a00179_result_identity": a179.get("result_sha")==LOCKED_A00179_RESULT or a179.get("authoritative_result_sha")==LOCKED_A00179_RESULT,
      "a00179_index132_exhausted": bool(src and src.get("final")=="SOURCE_ACQUISITION_EXHAUSTED"),
      "drive_exact_name_miss": bool(src and src.get("drive",{}).get("outcome")=="SOURCE_TRANSPORT_MISS"),
      "pinned_direct_identity_mismatch": bool(src and src.get("pinned_direct",{}).get("outcome")=="SOURCE_IDENTITY_MISMATCH" and src.get("pinned_direct",{}).get("git_blob_sha")==LOCKED_DIRECT_BLOB),
      "pinned_release_identity_mismatch": bool(src and src.get("pinned_release",{}).get("outcome")=="SOURCE_IDENTITY_MISMATCH" and src.get("pinned_release",{}).get("member_sha256")==LOCKED_RELEASE_SHA256 and src.get("pinned_release",{}).get("width")==4096 and src.get("pinned_release",{}).get("height")==2048),
      "c136_accepts_exhaustion_only": bool(cdisp and cdisp.get("status")=="PASS" and c136.get("production_readiness",{}).get(str(INDEX))=="PREFLIGHT_ONLY" and INDEX in c136.get("source_acquisition_exhausted",[])),
      "c163_has_no_render_ready": rr.get("render_ready_indices",[])==[],
      "c163_has_no_one_stage_to_render": rr.get("one_stage_to_render_indices",[])==[],
      "c163_cross_lane_rework_only": all(i%3!=0 for i in rr.get("candidate_rework_indices",[])),
      "a00285_tracks_sticky_index132": INDEX in a285.get("selection",{}).get("sticky_source_acquisition_not_repeated",[]),
      "prior_guards_are_disjoint": a286.get("selection",{}).get("selected_index")==30 and a290.get("selection",{}).get("selected_index")==36 and a291.get("selection",{}).get("selected_index")==48,
      "controller_schema15_mod3": roles.get("schema_version")==15 and roles.get("lanes",{}).get("A",{}).get("primary_index_modulo_3")==0,
      "pinned_source_policy_unchanged": all(x in contract for x in (PINNED_TAG,PINNED_COMMIT,PINNED_ZIP_SHA256,DRIVE_FOLDER_ID)),
    }
    unchanged=all(checks.values())
    out={
      "schema_version":1,"task_id":"LOCALIZATION-LOCALIZATION_A-00292","wave_id":"P00174","lane":"LOCALIZATION_A",
      "index":INDEX,"asset":ASSET,"queue_path":QUEUE_PATH,
      "checks":checks,"current_canonical":canonical,"locked_canonical":LOCKED_CANONICAL,
      "source_reprobe_authorized":False,
      "alias_or_scale_substitution_authorized":False,
      "candidate_rebuild_authorized":False,
      "reactivation_triggers":[
        "canonical inventory identity for index132 changes",
        "C disposition/source-acquisition state for index132 changes",
        "accepted A00179 result identity is superseded",
        "pinned source tag/commit/bundle or approved Drive transport policy changes",
        "an exact canonical 1024x512 1F5FE6E9 source transport is newly recorded by authoritative evidence",
      ],
      "fresh_rescan_required":not unchanged,
      "result":"BLOCKED_UNCHANGED_CANONICAL_SOURCE_IDENTITY_FINGERPRINT" if unchanged else "FRESH_RESCAN_REQUIRED",
      "runtime_validation":"UNTESTED",
    }
    print(json.dumps(out,ensure_ascii=False,indent=2))
    raise SystemExit(0 if unchanged else 2)

if __name__=="__main__":
    main()
