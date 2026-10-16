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
CROP_HELPER = Path("/home/chatgpt-runner2/work/c_original_hd_crop_only_checked_20261016.py")
QUEUE = BASE / "queue_specs"
RESULTS = BASE / "outputs"
AUDIT = BASE / "run_audit.jsonl"
STATE = BASE / "last_run.json"

# The only allowed source is independently checked against its pinned complete original PC HD DDS.
# Additional sources require manual explicit verification and an updated allowlist.
VERIFIED = {
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
  header=f.read(128)
  payload=f.read()
 if header[:4]!=b"DDS " or len(payload)!=p["size"][0]*p["size"][1]*4:
  raise ValueError("HOLD_DDS_UNSUPPORTED_FORMAT")
 original=Image.frombytes("RGBA",tuple(p["size"]),payload).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
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