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

# Bump this to explicitly re-run the original 108 files after an approved
# change to OCR/safety policy. No silent endless re-scanning of exhausted inputs.
POLICY_VERSION = "hd108-pass-v2-20261018-reviewed-edge-crops"

def scan(max_sources=4,max_new=1000):
 if not RECEIPT.is_file() or not ZIP.is_file():
  return {"status":"HD108_INPUT_HOLD_NOT_IMPORTED"}
 receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
 if not (receipt.get("original_full_hd_png")==108 and
         receipt.get("file_sha_verified")==108 and receipt.get("manifest_matched")==108 and
         receipt.get("old_tiles_reused") is False):
  raise ValueError("HD108_IMPORT_PROOF_INVALID")
 with zipfile.ZipFile(ZIP) as z:
  rows=list(csv.DictReader(io.StringIO(z.read("01_DDS_PNG_MANIFEST_108.csv").decode("utf-8-sig"))))
 if len(rows)!=108 or len({r["png_filename"] for r in rows})!=108:
  raise ValueError("HD108_SOURCE_MANIFEST_INVALID")
 rows.sort(key=lambda r:r["png_filename"])
 REPORT.mkdir(parents=True,exist_ok=True)
 OUT.mkdir(parents=True,exist_ok=True)
 done_dir=REPORT/"processed_v2"
 done_dir.mkdir(parents=True,exist_ok=True)

 # A source is eligible once per approved scanner revision and original SHA.
 # HOLDs remain visible but are not reprocessed without a version/source change.
 def record_for(row):
  return done_dir/(row["png_filename"]+".json")
 def cached(row):
  try:
   obj=json.loads(record_for(row).read_text(encoding="utf-8"))
   return obj.get("policy_version")==POLICY_VERSION and obj.get("source_sha256")==row["png_sha256"] and obj.get("status") in ("SCANNED","NO_REVIEWED_OFFICIAL_PHRASES","HOLD")
  except (ValueError,OSError,TypeError):return False

 cursorfile=REPORT/"cursor.json"
 try:cursor=int(json.loads(cursorfile.read_text(encoding="utf-8")).get("next",0))%len(rows)
 except (OSError,ValueError,TypeError,KeyError):cursor=0
 # Pick next *unprocessed* sources. Do not spend 24 hours repeatedly OCRing
 # images already scanned when no new phrase is available.
 pending=[(i,rows[i]) for i in list(range(cursor,len(rows)))+list(range(cursor))
          if not cached(rows[i])]
 selected=pending[:min(max_sources,len(pending))]
 result={"status":"HD108_ORIGINAL_OCR_SCAN","policy_version":POLICY_VERSION,
         "inventory":108,"pending_before":len(pending),
         "selected":[r["png_filename"] for _,r in selected],
         "scanned":0,"matched":0,"new_crops":0,"duplicates":0,
         "held":0,"edge_review_crops":0,"details":[]}
 if not selected:
  result["status"]="HD108_PASS_COMPLETE_REVIEW_PENDING"
  result["pending_after"]=0
  result["source_records"]=len(rows)
  return result

 archive=json.loads(discover.MASTER.read_text(encoding="utf-8"))
 if len(archive.get("items",[]))!=255:raise ValueError("MASTER_255_ARCHIVE_CHANGED")
 for index,r in selected:
  name=r["png_filename"]; detail={"source":name}
  hardhold=[]
  try:
   if Path(name).name!=name or not re.fullmatch(r"Q[0-9]{3}_[a-zA-Z0-9_]+[.]png",name):
    raise ValueError("SOURCE_FILENAME_UNSAFE")
   src=SRC/name
   if not src.is_file() or src.is_symlink():
    raise ValueError("MISSING_OR_SYMLINK_SOURCE")
   if src.stat().st_size!=int(r["png_size_bytes"]):
    raise ValueError("SOURCE_BYTE_SIZE_CHANGED")
   h=digest(src)
   if h!=r["png_sha256"]:raise ValueError("SOURCE_SHA_CHANGED")
   with Image.open(src) as im:
    if im.format!="PNG" or im.mode!="RGBA" or im.size!=(int(r["width"]),int(r["height"])):
     raise ValueError("SOURCE_FORMAT_DIMENSION_HOLD")
    image=im.copy()
   phrases={}
   for val in r["queue_indexes"].split(","):
    val=val.strip()
    if not re.fullmatch(r"[0-9]{1,3}",val):
     raise ValueError("QUEUE_ID_INVALID")
    phrases.update(ocr.approved_phrases("Q"+val.zfill(3)))
   if not phrases:
    detail["status"]="NO_REVIEWED_OFFICIAL_PHRASES"
    detail["matches"]=0
   else:
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
      result["duplicates"]+=1
      continue
     bad=ocr.margin_check(image,b)
     # Alpha at the edge is often the original opaque plate/background,
     # rather than glyph clipping. Preserve original pixels for human QA;
     # never claim an automatic PASS. Truly empty/tiny crops still HOLD.
     if bad and bad!="ALPHA_TOUCHES_CROP_BORDER_REVIEW":
      result["held"]+=1
      hardhold.append({"bbox_xyxy":b,"reason":bad})
      continue
     if result["new_crops"]>=max_new:
      # This source must be visited again: do NOT write completion stamp.
      raise RuntimeError("SOURCE_CROP_LIMIT_HIT_INCREASE_MAX_NEW")
     label=hashlib.sha256((name+item["ocr_exact_normalized"]+str(b)).encode()).hexdigest()[:16]
     target=sourceout/label
     if target.exists():
      result["duplicates"]+=1
      continue
     target.mkdir(parents=True,exist_ok=False)
     cropped=image.crop(tuple(b))
     outfile=target/"english_original_native_crop.png"
     cropped.save(outfile,format="PNG")
     with Image.open(outfile) as proof:
      if (proof.size!=cropped.size or proof.mode!=cropped.mode or
          proof.tobytes()!=cropped.tobytes()):
       raise ValueError("CROP_PIXEL_ROUNDTRIP_MISMATCH")
     manifest={"status":"CROP_TEST_ONLY_REVIEW_REQUIRED",
               "source_type":"SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG",
               "source_png":name,"source_sha256":h,
               "reference_dds_path":r["source_dds_path"],
               "reference_dds_sha256":r["dds_sha256"],
               "independent_DDS_pixel_equality":"NOT_TESTED_FOR_THIS_PNG",
               "queue_indexes":r["queue_indexes"],"english":item["english"],
               "ocr_confidence":item["min_confidence"],
               "bbox_xyxy":b,"source_dimensions":list(image.size),
               "crop_dimensions":list(cropped.size),"crop_sha256":digest(outfile),
               "edge_warning":bad if bad else None,
               "human_review_required":True,"runtime_validation":"UNTESTED",
               "old_split_tiles_used":False,"A_B":"STOPPED_UNTOUCHED"}
     discover.save_json_atomic(target/"manifest.json",manifest)
     used.append(b)
     result["new_crops"]+=1
     if bad:result["edge_review_crops"]+=1
    detail.update({"status":"SCANNED","words":sum(len(x) for x in words),
                   "matches":len(matches),"hard_holds":hardhold})
   result["scanned"]+=1
  except Exception as e:
   result["held"]+=1
   detail.update({"status":"HOLD","reason":type(e).__name__+":"+str(e)[:180]})
  result["details"].append(detail)
  # A retryable crop-count cap is the only condition that never marks done.
  if detail.get("reason","").find("SOURCE_CROP_LIMIT_HIT")<0:
   discover.save_json_atomic(record_for(r),{
       "status":detail["status"],"policy_version":POLICY_VERSION,
       "source_png":name,"source_sha256":r["png_sha256"],
       "source_size_bytes":int(r["png_size_bytes"]),
       "source_dimensions":[int(r["width"]),int(r["height"])],
       "ocr_matches":detail.get("matches",0),"hard_holds":hardhold,
       "review_only":True,"runtime_validation":"UNTESTED"})

 newcursor=(selected[-1][0]+1)%len(rows)
 discover.save_json_atomic(cursorfile,{"next":newcursor,"after":selected[-1][1]["png_filename"],
                                      "inventory":108,"policy_version":POLICY_VERSION})
 pending_after=sum(1 for row in rows if not cached(row))
 result["pending_after"]=pending_after
 if pending_after==0:result["status"]="HD108_PASS_COMPLETE_REVIEW_PENDING"
 discover.save_json_atomic(REPORT/"last_scan.json",result)
 return result
