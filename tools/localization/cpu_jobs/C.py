#!/usr/bin/env python3
# C232 PRE_INGAME export refresh / TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os,subprocess,json
from pathlib import Path
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
repo=Path.cwd()
subprocess.run(["python3","tools/localization/export_c_pass_comparison.py"],check=True)
m=json.loads((repo/"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/manifest.json").read_text(encoding="utf-8"))
items=[x for x in m.get("items",[]) if int(x.get("queue_index",-1))==95]
if len(items)!=1:
    raise SystemExit(f"q95 export membership expected 1, got {len(items)}")
x=items[0]
expected="ced8da1cbe46732f5f3793f9ddf63060efb6c856bb414b30499e2b39e2fa925b"
if x.get("candidate_sha256")!=expected:
    raise SystemExit("q95 candidate SHA mismatch in export")
summary={
 "role":"C","lane":"C1","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "run":"20261007-C232-C1-Q095-37759842-A137-EXPORT",
 "queue_index":95,"candidate_sha256":expected,"jpg":x.get("jpg"),
 "manifest_count":m.get("count"),"mandatory_c3_blocked_count":m.get("mandatory_c3_blocked_count"),
 "status":"PRE_INGAME_EXPORT_REFRESH_PASS","runtime_validation":"UNTESTED"
}
(repo/"localization/graphics/worker_results/C232_PRE_INGAME_EXPORT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
