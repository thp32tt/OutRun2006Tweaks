#!/usr/bin/env python3
"""Package verified TEST_ONLY Korean DDS outputs; never install game files."""
from __future__ import annotations
import argparse, hashlib, io, json, os, tempfile, zipfile
from pathlib import Path, PurePosixPath

BASE=Path("/home/chatgpt-runner2/work")
IMG=Path("/data/imagegen") if (Path("/data/imagegen/text_roi_batches/production_manifest.json")).exists() else BASE/"image-src"
ROOT=IMG/"text_roi_batches/offline_bulk_test_only"
SOURCE=BASE/"c_salvage_text_roi/c_original_hd_crop_only/hd_original_108_verified"

def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()

def safe_target(s):
 p=PurePosixPath(str(s))
 if p.is_absolute() or ".." in p.parts or not str(p).startswith("textures/load/") or not str(p).endswith(".dds"):
  raise ValueError("UNSAFE_TARGET")
 return str(p)

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument("--output-root",default=str(ROOT))
 ap.add_argument("--source-root",default=str(SOURCE))
 ap.add_argument("--when-complete",action="store_true",help="Do nothing until every eligible source has saved output")
 ap.add_argument("--allow-partial",action="store_true",help="Explicitly include only completed DDS for a small test")
 args=ap.parse_args()
 root=Path(args.output_root)
 # Sources missing an approved translation/ROI are documented as out of scope,
 # not silently counted as all localized.
 candidates=list(sorted(Path(args.source_root).glob("Q*.png")))
 source_reports={}
 source_coverage=[]
 by_target={}
 issues=[]
 for src in candidates:
  matching=list((root/"sources").glob(src.stem+"_*/report.json"))
  if not matching:
   source_coverage.append({"source":src.name,"state":"NOT_OUTPUT_OR_NO_APPROVED_REGION"})
   continue
  if len(matching)>1:
   issues.append({"source":src.name,"error":"MULTIPLE_SOURCE_REPORT_VERSIONS"})
   continue
  receipt=matching[0]
  row=json.loads(receipt.read_text(encoding="utf-8"))
  if row.get("status")!="TEST_ONLY_NOT_RUNTIME_APPROVED" or row.get("source")!=src.name:
   issues.append({"source":src.name,"error":"REPORT_SOURCE_OR_STATUS_MISMATCH"});continue
  if sha(src)!=row.get("source_sha256"):
   issues.append({"source":src.name,"error":"SOURCE_SHA_CHANGED"});continue
  d=receipt.parent/"KOREAN_TEST_ONLY.dds"
  p=receipt.parent/"KOREAN_READABLE_TEST_ONLY.png"
  if not d.is_file() or not p.is_file() or sha(d)!=row.get("output_dds_sha256") or sha(p)!=row.get("output_png_sha256"):
   issues.append({"source":src.name,"error":"OUTPUT_SHA_MISMATCH"});continue
  target=safe_target(row.get("target_path"))
  info={"source":src.name,"target":target,"sha256":row["output_dds_sha256"],
        "relative_receipt":str(receipt.relative_to(root)),
        "painted_count":row.get("painted_count",0),"held_count":row.get("held_count",0)}
  if target in by_target and by_target[target]["sha256"]!=info["sha256"]:
   issues.append({"source":src.name,"error":"DDS_TARGET_COLLISION","target":target});continue
  by_target[target]={"dds":d,"receipt":receipt,**info}
  source_reports[src.name]=info
  source_coverage.append({"source":src.name,"state":"VERIFIED"})
 # last_run inventory is the current process's determiner of which sources had
 # approved ROI. Never rely on 'Q*' file counts for actual language coverage.
 inventory=root/"last_run.json"
 pending=[]
 if inventory.is_file():
  status=json.loads(inventory.read_text(encoding="utf-8"))
  pending=[x["source"] for x in status.get("results",[]) if x.get("status") in ("HOLD_ERROR","HELD_PREVIOUSLY")]
 if issues:
  print(json.dumps({"status":"HOLD_VERIFY","errors":issues,"verified_target_dds":len(by_target)},ensure_ascii=False));return 2
 if not by_target:
  print(json.dumps({"status":"NOTHING_TO_PACKAGE"},ensure_ascii=False));return 0
 if args.when_complete and not args.allow_partial:
  # Use original production manifest source hashes to distinguish eligible
  # from truly untranslated sources/identical console aliases.
  manifest_path=IMG/"text_roi_batches/production_manifest.json"
  orig=json.loads(manifest_path.read_text(encoding="utf-8"))
  approved={x.get("source_png_sha256") for x in orig.get("items",[]) if x.get("status") in ("ROI_APPROVED_FOR_IMAGEGEN","ROI_REBALANCED_TO_B")}
  for src in candidates:
   if src.name in source_reports:
    continue
   current=sha(src)
   if current not in approved:
    continue
   # Byte-identical console variants are satisfied by the same base DDS
   # receipt; only when the base source SHA actually matches.
   base_name=src.name
   for tag in ("KEYBOARD","PLAYSTATION","SWITCH","XBOX"):
    base_name=base_name.replace("_"+tag+"_READABLE","_BASE_READABLE")
   base=Path(args.source_root)/base_name
   if base!=src and base.is_file() and sha(base)==current and base.name in source_reports:
    continue
   pending.append(src.name)
  if pending:
   print(json.dumps({"status":"PENDING_NOT_PACKAGED","verified_target_dds":len(by_target),
                     "unresolved_sources":sorted(set(pending))[:25],"pending_count":len(set(pending))},ensure_ascii=False))
   return 0
 ordered=sorted(by_target.values(),key=lambda z:z["target"])
 version=hashlib.sha256(json.dumps([(a["target"],a["sha256"]) for a in ordered]).encode()).hexdigest()[:12]
 archive=root/("OUTRUN_OFFLINE_KOREAN_TEST_ONLY_"+version+".zip")
 if archive.is_file():
  print(json.dumps({"status":"PACKAGE_ALREADY_PRESENT","path":str(archive),"sha256":sha(archive),"dds":len(ordered)},ensure_ascii=False));return 0
 root.mkdir(parents=True,exist_ok=True)
 meta={"status":"TEST_ONLY_NOT_GAME_APPROVED","originals_modified":False,
       "outputs":source_coverage,"included_dds":len(ordered),
       "included_labels":sum(int(x.get("painted_count",0)) for x in ordered),
       "source_reports":source_reports,"issues":issues,
       "important":"Uncompressed DDS may use more VRAM and lose background art inside ROI. No C1/C3 or game PASS."}
 with tempfile.NamedTemporaryFile(prefix=".kor-package-",suffix=".zip",dir=root,delete=False) as tf:
  tmp=Path(tf.name)
 try:
  with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED,compresslevel=2,allowZip64=True) as z:
   for row in ordered:
    z.write(row["dds"],arcname=row["target"])
    z.write(row["receipt"],arcname="qa_receipts/"+row["source"]+".json")
   z.writestr("TEST_ONLY_MANIFEST.json",json.dumps(meta,ensure_ascii=False,indent=2)+"\n")
  with zipfile.ZipFile(tmp) as z:
   bad=z.testzip()
   if bad:raise ValueError("ZIP_INTEGRITY_FAILED:"+bad)
  os.replace(tmp,archive)
 finally:
  if tmp.exists():tmp.unlink()
 print(json.dumps({"status":"TEST_ONLY_PACKAGE_CREATED","path":str(archive),
   "sha256":sha(archive),"bytes":archive.stat().st_size,
   "dds_count":len(ordered),"included_labels":meta["included_labels"],
   "runtime_validation":"UNTESTED"},ensure_ascii=False))
 return 0
if __name__=="__main__":
 raise SystemExit(main())