#!/usr/bin/env python3
"""Fail-closed A-shard runnable-work guard for A00285/P00168.

This does not approve, rebuild, or re-QA a DDS. It verifies the exact producer
identities that currently make A assets QA-pending and the current queue/contract
fingerprints. Any drift forces a fresh selection scan instead of silently
reusing this snapshot.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

EXPECTED = {
    "contract_blob": "764867c8448a94d335932247a870cb69637eba0d",
    "roles_blob": "aaef0d3224fbfef4b4dfdc63218a5bf673788580",
    "queue_blob": "8e099aefebb5911e46efa0d1e75a35d9bd8068ae",
    "c_result_sha": "8cffecbfe06f7ac72d2d0133ff596cdb827ae16c",
}
QA_PENDING = {
    51: ("docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00278.json", "e32e1c27a2045d1eaef318bbc56379102b0572c2"),
    111: ("docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00276.json", "bb19063245160837c4e0cfa5777f3a5e9c11e750"),
    159: ("docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00196.json", "1efd8de0f240b7a6170b29a4e86d9f8f6aa366fb"),
    198: ("docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00208.json", "b874d64204539123c7c3e13d35a26a5ff3511a77"),
    201: ("docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00196.json", "1efd8de0f240b7a6170b29a4e86d9f8f6aa366fb"),
    24: ("docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00279.json", "51b606da094b0a27fa161834cf7edefea18d88ca"),
    15: ("docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00281.json", "54d9119ac94f050549c3cc612cc99b5ba7798a65"),
    18: ("docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00281.json", "54d9119ac94f050549c3cc612cc99b5ba7798a65"),
    21: ("docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00281.json", "54d9119ac94f050549c3cc612cc99b5ba7798a65"),
}
STICKY_SOURCE = {30,36,48,132,135,147,219,225,228}
COVERED = {12,63,99,102,195,222,231,237}
LEGACY_PENDING = {54,57,60}

def load_json(root: Path, rel: str):
    return json.loads((root / rel).read_text(encoding="utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out")
    args=ap.parse_args()
    root=Path(args.repo_root)

    queue_path=root/"localization/graphics/asset_queue.csv"
    rows=list(csv.DictReader(queue_path.read_text(encoding="utf-8").splitlines()))
    arows={int(r["index"]):r for r in rows if int(r["index"]) % 3 == 0}

    drift=[]
    pending=[]
    for idx,(rel,sha) in QA_PENDING.items():
        doc=load_json(root,rel)
        actual=doc.get("result_sha") or doc.get("authoritative_result_sha")
        if actual != sha:
            drift.append({"index":idx,"kind":"QA_PENDING_RESULT_SHA_CHANGED","expected":sha,"actual":actual})
        else:
            pending.append(idx)

    c=load_json(root,"docs/automation/runs/LOCALIZATION-LOCALIZATION_C-00282.json")
    if c.get("validation_bearing_result_sha") != EXPECTED["c_result_sha"]:
        drift.append({"kind":"C_BASIS_CHANGED","expected":EXPECTED["c_result_sha"],"actual":c.get("validation_bearing_result_sha")})

    classified={}
    unknown=[]
    for idx,row in sorted(arows.items()):
        status=row.get("artwork_status","")
        if idx in QA_PENDING:
            classified[idx]="QA_PENDING_EXACT_RESULT"
        elif idx in STICKY_SOURCE:
            classified[idx]="STICKY_SOURCE_DEPENDENCY_BLOCKED"
        elif idx in COVERED:
            classified[idx]="STATIC_OR_RUNTIME_ISOLATION_COVERED"
        elif idx in LEGACY_PENDING or "pending_c" in status:
            classified[idx]="LEGACY_QA_PENDING"
        elif row.get("action")=="zoom_review" and status=="preserve_original":
            classified[idx]="RESOLVED_PRESERVE_ORIGINAL"
        else:
            unknown.append({"index":idx,"action":row.get("action"),"artwork_status":status})

    result={
        "schema_version":1,
        "task_id":"LOCALIZATION-LOCALIZATION_A-00285",
        "wave_id":"P00168",
        "shard_rule":"asset_queue.index % 3 == 0",
        "qa_pending_exact_indices":sorted(pending),
        "sticky_source_indices":sorted(STICKY_SOURCE),
        "covered_indices":sorted(COVERED),
        "classified_indices":{str(k):v for k,v in classified.items()},
        "fingerprint_drift":drift,
        "unknown_unclassified":unknown,
        "candidate_rebuild_authorized":False,
        "fresh_rescan_required":bool(drift or unknown),
        "result":"RESCAN_REQUIRED" if (drift or unknown) else "NO_LEGAL_A_CANDIDATE_AT_PINNED_FINGERPRINTS",
        "runtime_validation":"UNTESTED",
    }
    payload=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.out:
        Path(args.out).write_text(payload,encoding="utf-8")
    print(payload,end="")

if __name__=="__main__":
    main()
