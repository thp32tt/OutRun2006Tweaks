#!/usr/bin/env python3
"""C-only OCR of SHA-manifest-verified original unsplit HD PNGs (not old tiles).
Separate from DDS queue. Results are TEST_ONLY, without claiming DDS pixel proof.
"""
import csv
import hashlib
import io
import json
import os
import re
import zipfile
from pathlib import Path
from PIL import Image
import discover
import ocr_recognize as ocr

BASE=discover.BASE
SRC=BASE/"hd_original_108_verified"
ZIP=BASE/"hd_original_108_zip_inbox/OutRun_ALL_HD_Korean_Source_PNG_PART01_of_05_20261013.zip"
RECEIPT=BASE/"hd108_import_receipt.json"
REPORT=BASE/"hd108_ocr"
OUT=BASE/"hd108_outputs"

def digest(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()

def scan(max_sources=2,max_new=6):
 if not RECEIPT.is_file() or not ZIP.is_file():return {"status":"HD108_INPUT_HOLD_NOT_IMPORTED"}
 receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
 if not (receipt.get("original_full_hd_png")==108 and receipt.get("file_sha_verified")==108
         and receipt.get("manifest_matched")==108 and receipt.get("old_tiles_reused") is False):
  raise ValueError("HD108_IMPORT_PROOF_INVALID")
 with zipfile.ZipFile(ZIP) as z:
  rows=list(csv.DictReader(io.StringIO(z.read("01_DDS_PNG_MANIFEST_108.csv").decode("utf-8-sig"))))
 if len(rows)!=108 or len({r["png_filename"] for r in rows})!=108:
  raise ValueError("HD108_SOURCE_MANIFEST_INVALID")
 rows.sort(key=lambda r:r["png_filename"])
 REPORT.mkdir(parents=True,exist_ok=True)
 OUT.mkdir(parents=True,exist_ok=True)
 cursorfile=REPORT/"cursor.json"
 try:cursor=int(json.loads(cursorfile.read_text()).get("next",0))%len(rows)
 except (OSError,ValueError,TypeError,KeyError):cursor=0
 selected=[rows[(cursor+i)%len(rows)] for i in range(min(max_sources,len(rows)))]
 archive=json.loads(discover.MASTER.read_text(encoding="utf-8"))
 if len(archive.get("items",[]))!=255:raise ValueError("MASTER_255_ARCHIVE_CHANGED")
 result={"status":"HD108_ORIGINAL_OCR_SCAN","inventory":108,
         "selected":[r["png_filename"] for r in selected],
         "scanned":0,"matched":0,"new_crops":0,"duplicates":0,"held":0,"details":[]}
 for r in selected:
  name=r["png_filename"];detail={"source":name}
  try:
   if Path(name).name!=name or not re.fullmatch(r"Q[0-9]{3}_[a-zA-Z0-9_]+\.png",name):
    raise ValueError("SOURCE_FILENAME_UNSAFE")
   src=SRC/name
   if not src.is_file() or src.is_symlink():raise ValueError("MISSING_OR_SYMLINK_SOURCE")
   if src.stat().st_size!=int(r["png_size_bytes"]):raise ValueError("SOURCE_BYTE_SIZE_CHANGED")
   h=digest(src)
   if h!=r["png_sha256"]:raise ValueError("SOURCE_SHA_CHANGED")
   with Image.open(src) as im:
    if im.format!="PNG" or im.mode!="RGBA" or im.size!=(int(r["width"]),int(r["height"])):
     raise ValueError("SOURCE_FORMAT_DIMENSION_HOLD")
    image=im.copy()
   phrases={}
   for val in r["queue_indexes"].split(","):
    val=val.strip()
    if not re.fullmatch(r"[0-9]{1,3}",val):raise ValueError("QUEUE_ID_INVALID")
    phrases.update(ocr.approved_phrases("Q"+val.zfill(3)))
   if not phrases:
    detail["status"]="NO_REVIEWED_OFFICIAL_PHRASES"
    result["scanned"]+=1
    result["details"].append(detail)
    continue
   words=ocr.ocr_words(image)
   matches=ocr.unique_regions(words,phrases,image.width,image.height)
   used=[entry["bbox_xyxy"] for entry in archive["items"]
         if entry.get("source_sha256")==h and len(entry.get("bbox_xyxy",[]))==4]
   sourceout=OUT/src.stem
   if sourceout.is_dir():
    for saved in sourceout.glob("*/manifest.json"):
     try:
      j=json.loads(saved.read_text())
      if j.get("source_sha256")==h:used.append(j["bbox_xyxy"])
     except (ValueError,KeyError):pass
   result["matched"]+=len(matches)
   for item in matches:
    b=item["bbox_xyxy"]
    if any(discover.overlap(b,old)>0.38 for old in used):
     result["duplicates"]+=1;continue
    bad=ocr.margin_check(image,b)
    if bad:
     result["held"]+=1
     continue
    if result["new_crops"]>=max_new:break
    label=hashlib.sha256((name+item["ocr_exact_normalized"]+str(b)).encode()).hexdigest()[:16]
    target=sourceout/label
    if target.exists():result["duplicates"]+=1;continue
    target.mkdir(parents=True,exist_ok=False)
    cropped=image.crop(tuple(b))
    outfile=target/"english_original_native_crop.png"
    cropped.save(outfile,format="PNG")
    with Image.open(outfile) as proof:
     if proof.size!=cropped.size or proof.mode!=cropped.mode or proof.tobytes()!=cropped.tobytes():
      raise ValueError("CROP_PIXEL_ROUNDTRIP_MISMATCH")
    manifest={"status":"TEST_ONLY_UNTESTED_IN_GAME","source_type":"SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG",
              "source_png":name,"source_sha256":h,
              "reference_dds_path":r["source_dds_path"],
              "reference_dds_sha256":r["dds_sha256"],
              "independent_DDS_pixel_equality":"NOT_TESTED_FOR_THIS_PNG",
              "queue_indexes":r["queue_indexes"],"english":item["english"],
              "ocr_confidence":item["min_confidence"],
              "bbox_xyxy":b,"source_dimensions":list(image.size),
              "crop_dimensions":list(cropped.size),"crop_sha256":digest(outfile),
              "old_split_tiles_used":False,"A_B":"STOPPED_UNTOUCHED"}
    discover.save_json_atomic(target/"manifest.json",manifest)
    used.append(b)
    result["new_crops"]+=1
   result["scanned"]+=1
   detail.update({"status":"SCANNED","words":sum(len(x) for x in words),"matches":len(matches)})
  except Exception as e:
   result["held"]+=1
   detail.update({"status":"HOLD","reason":type(e).__name__+":"+str(e)[:130]})
  result["details"].append(detail)
 discover.save_json_atomic(REPORT/"last_scan.json",result)
 discover.save_json_atomic(cursorfile,{"next":(cursor+len(selected))%len(rows),"after":selected[-1]["png_filename"],
                                        "inventory":108})
 return result