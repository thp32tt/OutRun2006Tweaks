#!/usr/bin/env python3
# C242 C1 q49 PRE_INGAME export refresh
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, subprocess, json
from pathlib import Path
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
repo=Path.cwd()
subprocess.run(["python3","tools/localization/export_c_pass_comparison.py"],check=True)
m=json.loads((repo/"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/manifest.json").read_text(encoding="utf-8"))
items=[x for x in m.get("items",[]) if int(x.get("queue_index",-1))==49]
if len(items)!=1:
    raise SystemExit(f"q49 export membership expected 1, got {len(items)}")
x=items[0]
expected="a7eb06e2441956f4418f4cc95da52313696bc13d7864f7c7f76c8efdf909f85d"
source="b5c0a868add94395745af1827c21ddddd178439b5b4614fbadd8f0e4135a9887"
if x.get("candidate_sha256")!=expected:
    raise SystemExit(f"q49 candidate SHA mismatch {x.get('candidate_sha256')}")
if x.get("english_source_sha256")!=source:
    raise SystemExit(f"q49 source SHA mismatch {x.get('english_source_sha256')}")
summary={
 "role":"C","lane":"C1","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "run":"20261007-C242-C1-Q049-BF3EE5C6-EXPORT",
 "queue_index":49,"candidate_sha256":expected,"english_source_sha256":source,
 "jpg":x.get("jpg"),"manifest_count":m.get("count"),
 "mandatory_c3_blocked_count":m.get("mandatory_c3_blocked_count"),
 "status":"PRE_INGAME_EXPORT_REFRESH_PASS","runtime_validation":"UNTESTED"
}
(repo/"localization/graphics/worker_results/C242_PRE_INGAME_EXPORT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
