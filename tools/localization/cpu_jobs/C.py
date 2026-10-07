#!/usr/bin/env python3
# C237 PRE_INGAME export refresh / TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os,subprocess,json
from pathlib import Path
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
repo=Path.cwd()
subprocess.run(["python3","tools/localization/export_c_pass_comparison.py"],check=True)
m=json.loads((repo/"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/manifest.json").read_text(encoding="utf-8"))
items=[x for x in m.get("items",[]) if int(x.get("queue_index",-1))==12]
if len(items)!=1:
    raise SystemExit(f"q12 export membership expected 1, got {len(items)}")
x=items[0]
expected="1df64df712f990ee5d92c53998269604ff7b9fc4ccdff8913d648f18aa604013"
if x.get("candidate_sha256")!=expected:
    raise SystemExit(f"q12 candidate SHA mismatch: {x.get('candidate_sha256')}")
summary={
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":"20261007-C237-C2-Q012-D6DC1380-EXPORT",
 "queue_index":12,"candidate_sha256":expected,
 "jpg":x.get("jpg"),"manifest_count":m.get("count"),
 "mandatory_c3_blocked_count":m.get("mandatory_c3_blocked_count"),
 "status":"PRE_INGAME_EXPORT_REFRESH_PASS","runtime_validation":"UNTESTED"
}
(repo/"localization/graphics/worker_results/C237_PRE_INGAME_EXPORT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
