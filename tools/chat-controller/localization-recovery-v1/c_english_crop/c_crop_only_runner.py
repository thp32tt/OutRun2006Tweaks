#!/usr/bin/env python3
"""C-only offline N100 original HD crop runner. No A/B/browser/ImageGen operations."""
from __future__ import annotations
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
from PIL import Image, ImageChops

BASE = Path("/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only")
SOURCE = Path("/home/chatgpt-runner2/work/c_salvage_text_roi/source_full_20261012")
CROP_HELPER = Path("/app/c_original_hd_crop_only_checked_20261016.py")
QUEUE = BASE / "queue_specs"
RESULTS = BASE / "outputs"
AUDIT = BASE / "run_audit.jsonl"
STATE = BASE / "last_run.json"

# The only allowed source is independently checked against its pinned complete original PC HD DDS.
# Additional sources require manual explicit verification and an updated allowlist.
VERIFIED = {
 "Q116": {
 "png": "q116_DIRECT_ORIGINAL_HD.png",
 "png_sha256": "502920f902cc821250af69b5194f0190394ffeaa5695e7332a82e8c435f11197",
 "size": [
  2048,
  256
 ],
 "dds": "q116_E3FD08BE_original_pinned_106cc0cb.dds",
 "dds_sha256": "ebc2d866597955c6e802de65eff2d07e048f66b4ae2770fffd86b81b61fd5845",
 "dds_repo_path": "work/c_salvage_text_roi/source_full_20261012/q116_E3FD08BE_original_pinned_106cc0cb.dds"
},
 "Q197": {
 "png": "q197_DIRECT_ORIGINAL_HD.png",
 "png_sha256": "5436e6855b92fff6739e68a9774a9d7aadc95c65f012b4e7c098d36f24db5073",
 "size": [
  2048,
  2048
 ],
 "dds": "Q197_PINNED_EN_ORIGINAL_20261017.dds",
 "dds_sha256": "177e3be8f3a8fd4d0482bcf1849cbe333cef6f86486afbc4ca6307ec417c2e05",
 "dds_repo_path": "work/c_roi_q197_original_20261016/9F060EC1_512x512.dds"
},
 "Q161": {
 "png": "q161_DIRECT_ORIGINAL_HD.png",
 "png_sha256": "905f9701eea594647f1d00cfc7e1222f7b6fe8f93466f8a0b401e05b18ced13a",
 "size": [
  2048,
  2048
 ],
 "dds": "Q161_PINNED_EN_ORIGINAL_20261017.dds",
 "dds_sha256": "a74d31016e9ab38da4f6bd9a37196848534b9a1c8ac04db3f071000030681c4d",
 "dds_repo_path": "work/c_roi_q060_easy_git_20261016_0533/localization/graphics/role_A/20261011-A236-Q161-THREE-SOURCE-AUTHENTICATED-CLEAN/A236_CANONICAL_ENGLISH_SOURCE_EXACT.dds"
},
 "Q212": {
 "png": "q212_DIRECT_ORIGINAL_HD.png",
 "png_sha256": "0961cf674a533c77e6ac39cf7ee707d241d8180433be3b39d97cf08664b321de",
 "size": [
  2048,
  2048
 ],
 "dds": "Q212_PINNED_EN_ORIGINAL_20261017.dds",
 "dds_sha256": "f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61",
 "dds_repo_path": "work/c_roi_q060_easy_git_20261016_0533/localization/graphics/role_B/20261010-B342-Q212-CANONICAL-SOURCE-PLATE-RECHECK/B342_EXACT_ENGLISH_SOURCE_2048_RGBA32.dds"
},
 "Q051": {
  "png": "q051_FF2462BB_FLIPY_CHECK_ORIENTATION.png",
  "png_sha256": "2da1b6f01219356ddc6ea925bd8fcd4afd37d9040eb48081a40861cc649da6f0",
  "size": [4096, 2048],
  "dds": "q051_FF2462BB_GITHUB_HD_SOURCE_20261015.dds",
  "dds_sha256": "5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67",
  "dds_repo_path": "textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
 },
 "Q060": {
  "png": "q060_A064FDFC_FLIPY_CHECK_ORIENTATION.png",
  "png_sha256": "c9600e9c77067b64b6e57d67ceb8e1ab58359479b5520fcdb44a042be5d19731",
  "size": [4096, 2048],
  "dds": "Q060_A064FDFC_GITHUB_PINNED_ORIGINAL_20261016.dds",
  "dds_sha256": "6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc",
  "dds_repo_path": "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
 }
}

# Verified additional full-HD originals, staged from canonical HD DDS files or
# SHA-pinned original-DDS archive. Only admission script writes this registry.
AUTO_REGISTRY = BASE / "docker" / "source_registry_auto.json"

def load_auto_sources():
 if not AUTO_REGISTRY.exists():return {}
 data=json.loads(AUTO_REGISTRY.read_text(encoding="utf-8"))
 if data.get("schema")!="outrun-dds-pixel-verified-native-HD-sources-v1":
  raise ValueError("HOLD_AUTO_SOURCE_REGISTRY_SCHEMA")
 accepted={}
 for q,item in data.get("entries",{}).items():
  if (not isinstance(q,str) or len(q)!=4 or not q.startswith("Q")
      or not q[1:].isdigit() or not isinstance(item,dict)):
   raise ValueError("HOLD_AUTO_SOURCE_REGISTRY_ID")
  if (item.get("native_scale")!=4 or
      item.get("status")!="SOURCE_VERIFIED_CROP_TEST_ONLY" or
      item.get("admission_provenance") not in (
       "GIT_PINNED_CANONICAL_HD_SOURCE","ORIGINAL_BINARY_COMPARE_ARCHIVE")):
   raise ValueError("HOLD_AUTO_SOURCE_PROVENANCE")
  for key in ("png","dds"):
   v=item.get(key)
   if not isinstance(v,str) or Path(v).name!=v or not v.startswith(q.lower() if key=="png" else q+"_"):
    raise ValueError("HOLD_AUTO_SOURCE_BASENAME")
  for key in ("png_sha256","dds_sha256"):
   value=item.get(key)
   if not isinstance(value,str) or len(value)!=64 or any(c not in "0123456789abcdef" for c in value):
    raise ValueError("HOLD_AUTO_SOURCE_SHA")
  if q in VERIFIED:
   continue
  accepted[q]=item
 return accepted

VERIFIED.update(load_auto_sources())

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):
   h.update(b)
 return h.hexdigest()

def check_original(task):
 q=task.get("queue_id")
 p=VERIFIED.get(q)
 if p is None:
  raise ValueError("HOLD_FULL_ORIGINAL_NOT_IN_VERIFIED_REGISTRY")
 if task.get("source_kind")!="N100_DDS_VERIFIED_READABLE_FULL_HD_PNG":
  raise ValueError("HOLD_SOURCE_KIND_UNVERIFIED")
 if (task.get("source_png"),task.get("source_sha256"),task.get("source_dimensions"))!=(p["png"],p["png_sha256"],p["size"]):
  raise ValueError("HOLD_PNG_OR_DIMENSIONS_MISMATCH")
 if (task.get("source_dds_path"),task.get("source_dds_sha256"))!=(p["dds_repo_path"],p["dds_sha256"]):
  raise ValueError("HOLD_DDS_IDENTITY_MISMATCH")
 png=SOURCE/p["png"]; dds=SOURCE/p["dds"]
 if sha(png)!=p["png_sha256"] or sha(dds)!=p["dds_sha256"]:
  raise ValueError("HOLD_SOURCE_FILE_SHA_MISMATCH")
 with Image.open(png) as im:
  assert im.format=="PNG" and im.mode=="RGBA" and list(im.size)==p["size"]
  whole=im.copy()
 with dds.open("rb") as f:
  if f.read(4)!=b"DDS ":
   raise ValueError("HOLD_NOT_AN_ORIGINAL_DDS")
 # The pinned HD original can be RGBA32 or compressed DXT5.
 # Pillow decodes native DDS without any scaling; all decoded pixels must
 # exactly equal the independently pinned full English PNG.
 with Image.open(dds) as image:
  if image.format!="DDS" or list(image.size)!=p["size"]:
   raise ValueError("HOLD_ORIGINAL_DDS_DIMENSIONS_OR_FORMAT")
  original=image.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 if ImageChops.difference(whole,original).getbbox() is not None:
  raise ValueError("HOLD_FULL_DDS_PNG_PIXEL_MISMATCH")
 return True

def record(row):
 BASE.mkdir(parents=True,exist_ok=True)
 row={"time_utc":dt.datetime.now(dt.timezone.utc).isoformat(),**row}
 with AUDIT.open("a",encoding="utf-8") as f:
  f.write(json.dumps(row,ensure_ascii=False)+"\n")
 temporary=STATE.with_suffix(".json.tmp")
 temporary.write_text(json.dumps(row,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 os.replace(temporary,STATE)
 print(json.dumps(row,ensure_ascii=False),flush=True)

def main():
 BASE.mkdir(parents=True,exist_ok=True)
 QUEUE.mkdir(exist_ok=True)
 RESULTS.mkdir(exist_ok=True)
 with (BASE/".run.lock").open("a+") as lock:
  try: fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:
   record({"status":"SKIPPED_OVERLAPPING_RUNNING_C","A_B":"STOPPED_UNTOUCHED"});return
  jobs=sorted(QUEUE.glob("*.json"))
  for specpath in jobs:
   if not specpath.is_file() or specpath.is_symlink():continue
   try:
    obj=json.loads(specpath.read_text(encoding="utf-8"))
    if not isinstance(obj.get("regions"),list) or len(obj["regions"])!=1:raise ValueError("ONE_ENGLISH_PHRASE_PER_C_RUN")
    region=obj["regions"][0]
    jobname=str(obj["queue_id"])+"-"+str(region["id"])
    out=RESULTS/jobname
    if out.exists():
     continue
    check_original(obj)
    sys.path.insert(0,str(CROP_HELPER.parent))
    import c_original_hd_crop_only_checked_20261016 as helper
    report=helper.run(specpath,SOURCE,RESULTS)
    if report["hold"] or len(report["ready"])!=1:
     record({"status":"HOLD","spec":specpath.name,"reason":report["hold"],"A_B":"STOPPED_UNTOUCHED"})
     return
    manifest=json.loads((out/"crop_manifest.json").read_text(encoding="utf-8"))
    if sha(out/"english_original_native_crop.png")!=manifest["crop_png_sha256"]:
     raise ValueError("OUTPUT_SHA_CHECK_FAIL")
    record({"status":"C_NATIVE_HD_CROP_COMPLETED_TEST_ONLY","spec":specpath.name,
            "id":jobname,"png":str(out/"english_original_native_crop.png"),
            "crop_sha256":manifest["crop_png_sha256"],"source_sha256":manifest["source_full_png_sha256"],
            "RUNTIME_VALIDATION":"UNTESTED","A_B":"STOPPED_UNTOUCHED"})
    return
   except Exception as e:
    record({"status":"HOLD","spec":specpath.name,"reason":type(e).__name__+":"+str(e),"A_B":"STOPPED_UNTOUCHED"})
    return
  record({"status":"IDLE_NO_NEW_VERIFIED_ORIGINAL_HD_CROP","queue_entries":len(jobs),
          "note":"Already produced jobs skipped. New independently verified full sources/ROIs required.",
          "A_B":"STOPPED_UNTOUCHED"})

if __name__=="__main__":
 main()