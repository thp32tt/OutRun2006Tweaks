#!/usr/bin/env python3
import hashlib,json,os,subprocess
from pathlib import Path

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
source_commit="5f5f87c41ce43ccdf205e9936a645d44690f01b2"
asset="localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
expected="bfb50ebd9a6f9d572ce3349b56f76cf461dabc9e209f6cf0b7f48608d44b5178"
out=repo/"localization/graphics/role_A/20261006-A-RESTORE108-590A4724"; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

# Restore the already completed A108 bytes exactly; do not rerender or modify the approved candidate.
data=subprocess.check_output(["git","show",f"{source_commit}:{asset}"],cwd=repo)
sha=hashlib.sha256(data).hexdigest()
if sha!=expected:
    raise RuntimeError(("historical A108 candidate drift",sha,expected))
dst=repo/asset
before=hashlib.sha256(dst.read_bytes()).hexdigest() if dst.exists() else None
dst.write_bytes(data)
after=hashlib.sha256(dst.read_bytes()).hexdigest()
if after!=expected:
    raise RuntimeError(("restore write mismatch",after))
report={
 "schema_version":1,"role":"A","run":"A108_EXACT_RESTORE",
 "asset":"textures/load/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds",
 "historical_commit":source_commit,"before_sha256":before,"restored_sha256":after,
 "reason":"A108 was already controller-self-QA PASS. A later superseded A107 worker output overwrote the candidate path without updating A108 state; restore exact A108 bytes instead of repeating production.",
 "a108_report":"localization/graphics/role_A/20261006-A-PRODUCTION108-590A4724/A108_590A4724_REPORT.json",
 "a108_controller":"localization/graphics/role_A/20261006-A-PRODUCTION108-590A4724/A108_CONTROLLER_SELF_QA.json",
 "status":"A108_EXACT_BYTES_RESTORED_NO_REPRODUCTION","runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_touched":False
}
(out/"A108_EXACT_RESTORE_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
(wr/"A108_EXACT_RESTORE.json").write_text(json.dumps({"asset":"590A4724","restored_sha256":after,"status":report["status"]},indent=2)+"\n")
print(json.dumps(report),flush=True)
