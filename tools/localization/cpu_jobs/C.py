#!/usr/bin/env python3
# C241 C2 q232 PRE_INGAME export refresh
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os, subprocess, json
from pathlib import Path
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
repo=Path.cwd()
subprocess.run(["python3","tools/localization/export_c_pass_comparison.py"],check=True)
m=json.loads((repo/"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/manifest.json").read_text(encoding="utf-8"))
items=[x for x in m.get("items",[]) if int(x.get("queue_index",-1))==232]
if len(items)!=1:
    raise SystemExit(f"q232 export membership expected 1, got {len(items)}")
x=items[0]
expected="dc76c000cfce17098940f551512e6f746319ba8a1892345eb060693004747ea1"
source="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0"
if x.get("candidate_sha256")!=expected:
    raise SystemExit(f"q232 candidate SHA mismatch {x.get('candidate_sha256')}")
if x.get("english_source_sha256")!=source:
    raise SystemExit(f"q232 source SHA mismatch {x.get('english_source_sha256')}")
summary={
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":"20261007-C241-C2-Q232-EBFC709F-EXPORT",
 "queue_index":232,"candidate_sha256":expected,"english_source_sha256":source,
 "jpg":x.get("jpg"),"manifest_count":m.get("count"),
 "mandatory_c3_blocked_count":m.get("mandatory_c3_blocked_count"),
 "status":"PRE_INGAME_EXPORT_REFRESH_PASS","runtime_validation":"UNTESTED"
}
(repo/"localization/graphics/worker_results/C241_PRE_INGAME_EXPORT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
