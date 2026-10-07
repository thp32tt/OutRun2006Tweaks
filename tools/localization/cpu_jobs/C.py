#!/usr/bin/env python3
# C240 C1 q107 PRE_INGAME export refresh
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, subprocess, json
from pathlib import Path
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
repo=Path.cwd()
subprocess.run(["python3","tools/localization/export_c_pass_comparison.py"],check=True)
m=json.loads((repo/"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/manifest.json").read_text(encoding="utf-8"))
items=[x for x in m.get("items",[]) if int(x.get("queue_index",-1))==107]
if len(items)!=1:
    raise SystemExit(f"q107 export membership expected 1, got {len(items)}")
x=items[0]
expected="d6a5cc84e7cf834afe11d8afdc2c0b869b306e75759b71ee392983db8999abda"
source="112f47e7b16ecf21f722738f7fc9053d1a9852d66da9ef9d29fd25dadf2f567e"
if x.get("candidate_sha256")!=expected:
    raise SystemExit(f"q107 candidate SHA mismatch {x.get('candidate_sha256')}")
if x.get("english_source_sha256")!=source:
    raise SystemExit(f"q107 source SHA mismatch {x.get('english_source_sha256')}")
summary={
 "role":"C","lane":"C1","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "run":"20261007-C240-C1-Q107-841E796B-EXPORT",
 "queue_index":107,"candidate_sha256":expected,"english_source_sha256":source,
 "jpg":x.get("jpg"),"manifest_count":m.get("count"),
 "mandatory_c3_blocked_count":m.get("mandatory_c3_blocked_count"),
 "status":"PRE_INGAME_EXPORT_REFRESH_PASS","runtime_validation":"UNTESTED"
}
(repo/"localization/graphics/worker_results/C240_PRE_INGAME_EXPORT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
