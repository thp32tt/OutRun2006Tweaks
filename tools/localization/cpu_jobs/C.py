#!/usr/bin/env python3
# C243R C1 q51 PRE_INGAME export refresh
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, subprocess, json
from pathlib import Path
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted role C required")
repo=Path.cwd()
subprocess.run(["python3","tools/localization/export_c_pass_comparison.py"],check=True)
m=json.loads((repo/"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/manifest.json").read_text(encoding="utf-8"))
items=[x for x in m.get("items",[]) if int(x.get("queue_index",-1))==51]
if len(items)!=1:
    raise SystemExit(f"q51 export membership expected 1, got {len(items)}")
x=items[0]
cand="b1c91a8c0050f0f31523afc055185288f2756e4da02014c9597b69cff25fc129"
src="5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67"
if x.get("candidate_sha256")!=cand: raise SystemExit(f"q51 candidate SHA mismatch {x.get('candidate_sha256')}")
if x.get("english_source_sha256")!=src: raise SystemExit(f"q51 source SHA mismatch {x.get('english_source_sha256')}")
summary={
 "run":"20261007-C243R-C1-Q051-FF2462BB-EXPORT",
 "role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":51,"candidate_sha256":cand,"english_source_sha256":src,
 "jpg":x.get("jpg"),"manifest_count":m.get("count"),
 "mandatory_c3_blocked_count":m.get("mandatory_c3_blocked_count"),
 "status":"PRE_INGAME_EXPORT_REFRESH_PASS","runtime_validation":"UNTESTED"
}
(repo/"localization/graphics/worker_results/C243R_PRE_INGAME_EXPORT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
