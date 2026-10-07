#!/usr/bin/env python3
# C2 q100 53CE39D5 PRE_INGAME export refresh
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os, subprocess, json
from pathlib import Path
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
subprocess.run(["python3","tools/localization/export_c_pass_comparison.py"],check=True)
manifest_path=repo/"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/manifest.json"
m=json.loads(manifest_path.read_text(encoding="utf-8"))
items=[x for x in m.get("items",[]) if int(x.get("queue_index",-1))==100]
if len(items)!=1:
    raise SystemExit(f"q100 export membership expected 1, got {len(items)}")
x=items[0]
expected_candidate="7235731a2add8e947476cd22b971e5b57a7de390ae134609f4254a2f493a557d"
expected_source="cfed1de58cefd8c235fc464e27058439ffd26427294a3bce17192e584679426a"
if x.get("candidate_sha256")!=expected_candidate:
    raise SystemExit(f"q100 candidate SHA mismatch {x.get('candidate_sha256')}")
if x.get("english_source_sha256")!=expected_source:
    raise SystemExit(f"q100 English source SHA mismatch {x.get('english_source_sha256')}")
summary={
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":"20261007-C2-Q100-53CE39D5-PRE-INGAME-EXPORT",
 "queue_index":100,
 "candidate_sha256":expected_candidate,
 "english_source_sha256":expected_source,
 "english_source_origin":x.get("english_source_origin"),
 "jpg":x.get("jpg"),
 "manifest_count":m.get("count"),
 "mandatory_c3_blocked_count":m.get("mandatory_c3_blocked_count"),
 "status":"PRE_INGAME_EXPORT_REFRESH_PASS",
 "runtime_validation":"UNTESTED"
}
(repo/"localization/graphics/worker_results/C2Q100_PRE_INGAME_EXPORT.json").write_text(
    json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
