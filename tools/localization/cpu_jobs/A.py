#!/usr/bin/env python3
import os,hashlib,json,urllib.request
from pathlib import Path
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
repo=Path.cwd()
run="20261008-A175-Q121-FAILCLOSE-RESTORE"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
CURRENT="fbb99b69a3cd67c070db00fdd68d39daf492e1ea329014f46ae22a5138ac1c53"
RESTORE="03271f4a84d5d69a162debc6490fa04f839487e4c9b03cbdcc64e66856dd1433"
COMMIT="6ec13ee0efd5a8a2895e78050e7293f58f76b2be"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(cand)!=CURRENT: raise RuntimeError(("candidate drift",sha(cand),CURRENT))
tmp=Path("/tmp/FD90AA9_A138_restore.dds")
urllib.request.urlretrieve("https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/"+COMMIT+"/localization/graphics/hd_candidates/"+rel,tmp)
if sha(tmp)!=RESTORE: raise RuntimeError(("restore drift",sha(tmp),RESTORE))
cand.write_bytes(tmp.read_bytes())
if sha(cand)!=RESTORE: raise RuntimeError("restore write failed")
report={
 "schema_version":2,"role":"A","run":run,"queue_index":121,"asset":"FD90AA9",
 "rejected_attempts":[
   {"run":"A171","sha256":"7a7d1e6c62dca8d699dac689fabfb4314d7f6a5f35aeac130b9a8817afccea76","reason":"controller visual FAIL: rectangular plate reconstruction"},
   {"run":"A172","sha256":"7a7d1e6c62dca8d699dac689fabfb4314d7f6a5f35aeac130b9a8817afccea76","reason":"no material correction; same rectangular plate"},
   {"run":"A173","sha256":"7a7d1e6c62dca8d699dac689fabfb4314d7f6a5f35aeac130b9a8817afccea76","reason":"mask selected full bbox due source/prior plate mismatch"},
   {"run":"A174","sha256":CURRENT,"reason":"controller visual FAIL: source/prior plate mismatch still produced flat rectangular plate"}
 ],
 "restored_candidate_sha256":RESTORE,
 "restore_provenance_commit":COMMIT,
 "decision":"HOLD_STRICT_RECHECK",
 "reason":"C255 visual source-residue finding remains authoritative, but all same-invocation reconstruction attempts introduced a worse plate rectangle. Fail-closed restoration prevents regression; requires a source-art-aware reconstruction method before producer PASS.",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"A175_Q121_FAILCLOSE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A175_Q121.json").write_text(json.dumps({"run":run,"index":121,"asset":"FD90AA9","restored_sha256":RESTORE,"decision":"HOLD_STRICT_RECHECK","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
