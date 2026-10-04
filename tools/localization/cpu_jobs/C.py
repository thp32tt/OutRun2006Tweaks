#!/usr/bin/env python3
import os,json,hashlib,struct
from pathlib import Path
from PIL import Image

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C125-1A43-RAW"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
bp=repo/"localization/graphics/role_B/20261005-B-PRODUCTION39"
rep=json.loads((bp/"B_PRODUCTION39_1A43_REPORT.json").read_text(encoding="utf-8"))
cand=repo/rep["candidate_path"]
b=cand.read_bytes()
assert hashlib.sha256(b).hexdigest()==rep["candidate_sha256"]
assert b[:4]==b"DDS "
h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
assert (w,h,b[84:88])==(2048,256,b"DXT5")
raw=Image.open(cand).convert("RGBA")
# Composite raw DDS orientation over dark gray so low-alpha fringe/orientation is inspectable.
bg=Image.new("RGBA",raw.size,(64,64,64,255))
comp=Image.alpha_composite(bg,raw)
comp.save(out/"C125_B39_RAW_MIRROR_Y_QA.png")
# Also save readable orientation for direct side-by-side controller inspection.
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
bg2=Image.new("RGBA",readable.size,(64,64,64,255))
Image.alpha_composite(bg2,readable).save(out/"C125_B39_READABLE_QA.png")
report={
 "schema_version":1,"role":"C","run":run,"asset":"1A43E9D9","producer_run":"B_PRODUCTION39",
 "candidate_sha256":rep["candidate_sha256"],"dimensions":[w,h],"format":"DXT5",
 "raw_orientation":"mirror_y","raw_proof":"localization/graphics/role_C/20261005-C125-1A43-RAW/C125_B39_RAW_MIRROR_Y_QA.png",
 "readable_proof":"localization/graphics/role_C/20261005-C125-1A43-RAW/C125_B39_READABLE_QA.png",
 "runtime_validation":"UNTESTED"
}
(out/"C125_RAW_ORIENTATION_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C125_RAW_PROOF",rep["candidate_sha256"],flush=True)
