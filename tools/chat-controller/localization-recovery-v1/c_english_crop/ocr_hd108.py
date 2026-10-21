#!/usr/bin/env python3
"""C-only OCR of SHA-manifest-verified original unsplit HD PNGs (not old tiles).
Separate from DDS queue. Results are TEST_ONLY, without claiming DDS pixel proof.
"""
import csv
import concurrent.futures
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
POLICY_VERSION = "hd108-coverage-v4-20261021-12strategy-parallel"
EDGE_REVIEW_VERSION = "edge-safe-expand-v2-20261021-progressive"
EDGE_STAGES = ((.55,.30),(.90,.50),(1.40,.80),(2.00,1.20))


def _row_phrases(row):
 phrases={}
 for val in row["queue_indexes"].split(","):
  val=val.strip()
  if not re.fullmatch(r"[0-9]{1,3}",val):
   raise ValueError("QUEUE_ID_INVALID")
  phrases.update(ocr.approved_phrases("Q"+val.zfill(3)))
 return phrases


def _covered_codes(row, out_root=OUT):
 sourceout=out_root/Path(row["png_filename"]).stem
 covered=set()
 if not sourceout.is_dir():
  return covered
 for saved in sourceout.glob("*/manifest.json"):
  try:
   j=json.loads(saved.read_text(encoding="utf-8"))
   if j.get("source_sha256")!=row["png_sha256"]:
    continue
   en=j.get("english")
   if isinstance(en,str) and en.strip():
    covered.add(ocr.norm(ocr.searchable_phrase(en)))
  except (OSError,ValueError,TypeError):
   continue
 return covered


def _coverage(row, out_root=OUT):
 phrases=_row_phrases(row)
 covered=_covered_codes(row,out_root)
 unresolved={k:v for k,v in phrases.items() if k not in covered}
 return phrases,covered,unresolved


def review_edge_warnings(max_items=10, src_root=SRC, out_root=OUT):
 """Second-pass salvage for prior alpha-edge review crops.

 Existing warning crops are never mutated or auto-approved. Each is re-read
 from the SHA-pinned full-HD source, expanded with deterministic safe margins,
 and only a new sibling crop whose expanded boundary passes margin_check is
 emitted without edge_warning. Unresolved cases remain explicit REVIEW/HOLD.
 """
 pending=[]
 for mp in sorted(out_root.glob("*/*/manifest.json")):
  try:
   j=json.loads(mp.read_text(encoding="utf-8"))
   if j.get("edge_warning")!="ALPHA_TOUCHES_CROP_BORDER_REVIEW":
    continue
   stage_index=0
   receipt=mp.parent/"edge_review_v1.json"
   if receipt.is_file():
    rec=json.loads(receipt.read_text(encoding="utf-8"))
    if (rec.get("version")==EDGE_REVIEW_VERSION and
        rec.get("source_crop_sha256")==j.get("crop_sha256")):
     if rec.get("status") in ("RESCUED_SAFE_EXPANDED_CROP","RESCUED_MAX_CONTEXT_C1_REQUIRED"):
      continue
     stage_index=min(int(rec.get("stage_index",-1))+1,len(EDGE_STAGES)-1)
   pending.append((mp,j,stage_index))
  except (OSError,ValueError,TypeError):
   continue
 result={"status":"EDGE_REVIEW","version":EDGE_REVIEW_VERSION,
         "pending_before":len(pending),"reviewed":0,"rescued":0,
         "held":0,"details":[]}
 for mp,j,stage_index in pending[:max_items]:
  detail={"manifest":str(mp),"stage_index":stage_index}
  try:
   if (j.get("source_type")!="SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG" or
       j.get("old_split_tiles_used") is not False):
    raise ValueError("EDGE_REVIEW_SOURCE_PROVENANCE_INVALID")
   name=j.get("source_png")
   if not isinstance(name,str) or Path(name).name!=name:
    raise ValueError("EDGE_REVIEW_SOURCE_NAME_INVALID")
   original_crop=mp.parent/"english_original_native_crop.png"
   if (not original_crop.is_file() or original_crop.is_symlink() or
       digest(original_crop)!=j.get("crop_sha256")):
    raise ValueError("EDGE_REVIEW_ORIGINAL_CROP_SHA_MISMATCH")
   src=src_root/name
   if not src.is_file() or src.is_symlink() or digest(src)!=j.get("source_sha256"):
    raise ValueError("EDGE_REVIEW_SOURCE_SHA_MISMATCH")
   box=j.get("bbox_xyxy")
   dims=j.get("source_dimensions")
   if not (isinstance(box,list) and len(box)==4 and all(type(v) is int for v in box)):
    raise ValueError("EDGE_REVIEW_BBOX_INVALID")
   with Image.open(src) as im:
    if im.format!="PNG" or im.mode!="RGBA":
     raise ValueError("EDGE_REVIEW_SOURCE_FORMAT_INVALID")
    if isinstance(dims,list) and len(dims)==2 and list(im.size)!=dims:
     raise ValueError("EDGE_REVIEW_SOURCE_DIMENSIONS_CHANGED")
    image=im.copy()
   x0,y0,x1,y1=box
   h=max(1,y1-y0)
   xfactor,yfactor=EDGE_STAGES[stage_index]
   padx=max(24,int(h*xfactor))
   pady=max(16,int(h*yfactor))
   expanded=[max(0,x0-padx),max(0,y0-pady),
             min(image.width,x1+padx),min(image.height,y1+pady)]
   if expanded==box:
    raise ValueError("EDGE_REVIEW_NO_EXPANSION_POSSIBLE")
   bad=ocr.margin_check(image,expanded)
   opaque_context=(bad=="ALPHA_TOUCHES_CROP_BORDER_REVIEW" and
                   ocr.opaque_context_border(image,expanded))
   max_context=(stage_index==len(EDGE_STAGES)-1 and
                bad=="ALPHA_TOUCHES_CROP_BORDER_REVIEW")
   detail["original_bbox"]=box
   detail["expanded_bbox"]=expanded
   detail["expanded_margin_result"]=bad
   detail["opaque_context_border"]=opaque_context
   detail["max_context_fallback"]=max_context
   rescued_path=None
   if bad is None or opaque_context or max_context:
    sourceout=out_root/Path(name).stem
    label=hashlib.sha256((name+j.get("english","")+str(expanded)+EDGE_REVIEW_VERSION).encode()).hexdigest()[:16]
    target=sourceout/label
    outfile=target/"english_original_native_crop.png"
    if target.exists():
     manifest_path=target/"manifest.json"
     if not manifest_path.is_file():
      raise ValueError("EDGE_REVIEW_TARGET_COLLISION")
     existing=json.loads(manifest_path.read_text(encoding="utf-8"))
     if existing.get("edge_review_version")!=EDGE_REVIEW_VERSION:
      raise ValueError("EDGE_REVIEW_TARGET_COLLISION")
    else:
     target.mkdir(parents=True,exist_ok=False)
     cropped=image.crop(tuple(expanded))
     cropped.save(outfile,format="PNG")
     with Image.open(outfile) as proof:
      if proof.mode!=cropped.mode or proof.size!=cropped.size or proof.tobytes()!=cropped.tobytes():
       raise ValueError("EDGE_REVIEW_CROP_ROUNDTRIP_MISMATCH")
     manifest={k:v for k,v in j.items() if k not in ("edge_warning","crop_dimensions","crop_sha256")}
     manifest.update({
       "status":"CROP_TEST_ONLY_REVIEW_REQUIRED",
       "bbox_xyxy":expanded,
       "crop_dimensions":list(cropped.size),
       "crop_sha256":digest(outfile),
       "edge_warning":None,
       "human_review_required":True,
       "edge_review_version":EDGE_REVIEW_VERSION,
       "edge_review_of":str(mp),
       "edge_review_original_bbox":box,
       "edge_review_method":("PROGRESSIVE_SAFE_MARGIN_EXPANSION" if bad is None else
                             "OPAQUE_CONTEXT_BORDER_C1_REQUIRED" if opaque_context else
                             "PROGRESSIVE_MAX_CONTEXT_C1_REQUIRED"),
       "edge_review_stage_index":stage_index,
       "runtime_validation":"UNTESTED",
       "old_split_tiles_used":False,
     })
     discover.save_json_atomic(target/"manifest.json",manifest)
    rescued_path=str(target/"manifest.json")
    result["rescued"]+=1
    detail["status"]=("RESCUED_SAFE_EXPANDED_CROP" if bad is None else
                      "RESCUED_MAX_CONTEXT_C1_REQUIRED")
    detail["rescued_manifest"]=rescued_path
   else:
    result["held"]+=1
    detail["status"]="REVIEW_REMAINS_HOLD"
   receipt={
     "version":EDGE_REVIEW_VERSION,
     "status":detail["status"],
     "stage_index":stage_index,
     "source_crop_sha256":j.get("crop_sha256"),
     "source_png":name,
     "original_bbox":box,
     "expanded_bbox":expanded,
     "expanded_margin_result":bad,
     "rescued_manifest":rescued_path,
     "runtime_validation":"UNTESTED",
   }
   discover.save_json_atomic(mp.parent/"edge_review_v1.json",receipt)
   result["reviewed"]+=1
  except Exception as e:
   result["held"]+=1
   result["reviewed"]+=1
   detail.update({"status":"EDGE_REVIEW_HOLD","reason":type(e).__name__+":"+str(e)[:180]})
   try:
    discover.save_json_atomic(mp.parent/"edge_review_v1.json",{
      "version":EDGE_REVIEW_VERSION,"status":"EDGE_REVIEW_HOLD",
      "source_crop_sha256":j.get("crop_sha256"),"reason":detail["reason"],
      "runtime_validation":"UNTESTED"})
   except Exception:
    pass
  result["details"].append(detail)
 result["pending_after"]=max(0,len(pending)-min(max_items,len(pending)))
 if not pending:
  result["status"]="EDGE_REVIEW_COMPLETE"
 return result

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
 done_dir=REPORT/"processed_v3"
 done_dir.mkdir(parents=True,exist_ok=True)

 def record_for(row):
  return done_dir/(row["png_filename"]+".json")

 def attempt_count(row):
  try:
   obj=json.loads(record_for(row).read_text(encoding="utf-8"))
   if obj.get("policy_version")==POLICY_VERSION and obj.get("source_sha256")==row["png_sha256"]:
    return int(obj.get("attempts",0))
  except (ValueError,OSError,TypeError):
   pass
  return 0

 def unresolved(row):
  return _coverage(row,OUT)[2]

 cursorfile=REPORT/"cursor_v3.json"
 try:cursor=int(json.loads(cursorfile.read_text(encoding="utf-8")).get("next",0))%len(rows)
 except (OSError,ValueError,TypeError,KeyError):cursor=0
 # Source-level SCANNED is not completion. Keep rotating until every reviewed
 # phrase in every verified HD source has a crop manifest.
 order=list(range(cursor,len(rows)))+list(range(cursor))
 pending=[(i,rows[i]) for i in order if unresolved(rows[i])]
 selected=pending[:min(max_sources,len(pending))]
 pending_phrase_count=sum(len(unresolved(r)) for _,r in pending)
 total_phrase_count=sum(len(_row_phrases(r)) for r in rows)
 located_phrase_count=total_phrase_count-pending_phrase_count
 result={"status":"HD108_CROP_COVERAGE_RUNNING","policy_version":POLICY_VERSION,
         "inventory":108,"pending_sources_before":len(pending),
         "pending_phrases_before":pending_phrase_count,
         "reviewed_phrase_total":total_phrase_count,
         "located_phrase_count":located_phrase_count,
         "selected":[r["png_filename"] for _,r in selected],
         "scanned":0,"matched":0,"new_crops":0,"duplicates":0,
         "held":0,"edge_review_crops":0,"details":[]}
 if not selected:
  result["status"]="HD108_CROP_COVERAGE_COMPLETE"
  result["pending_sources_after"]=0
  result["pending_phrases_after"]=0
  result["source_records"]=len(rows)
  discover.save_json_atomic(REPORT/"last_scan.json",result)
  return result

 archive=json.loads(discover.MASTER.read_text(encoding="utf-8"))
 if len(archive.get("items",[]))!=255:raise ValueError("MASTER_255_ARCHIVE_CHANGED")

 # OCR is the expensive step. Run at most two Tesseract jobs concurrently,
 # matching the container's 2 CPU limit; source verification is repeated below
 # before any crop bytes are written.
 def _prefetch_ocr(pair):
  index,row=pair
  name=row["png_filename"]
  src=SRC/name
  if (Path(name).name!=name or
      not re.fullmatch(r"Q[0-9]{3}_[a-zA-Z0-9_]+[.]png",name) or
      not src.is_file() or src.is_symlink() or
      src.stat().st_size!=int(row["png_size_bytes"])):
   return index,None,None
  h=digest(src)
  if h!=row["png_sha256"]:
   return index,None,None
  with Image.open(src) as im:
   if im.format!="PNG" or im.mode!="RGBA" or im.size!=(int(row["width"]),int(row["height"])):
    return index,None,None
   image=im.copy()
  _,_,unresolved_before=_coverage(row,OUT)
  if not unresolved_before:
   return index,h,[]
  attempts=attempt_count(row)
  words=ocr.ocr_words(image,strategy=attempts%ocr.OCR_STRATEGY_COUNT)
  return index,h,words

 ocr_cache={}
 if selected:
  with concurrent.futures.ThreadPoolExecutor(max_workers=min(2,len(selected))) as pool:
   futures=[pool.submit(_prefetch_ocr,pair) for pair in selected]
   for fut in concurrent.futures.as_completed(futures):
    try:
     idx,source_sha,words=fut.result()
     if source_sha is not None and words is not None:
      ocr_cache[idx]=(source_sha,words)
    except Exception:
     # The main verified path below retains fail-closed error handling.
     pass

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
   phrases,covered_before,unresolved_before=_coverage(r,OUT)
   attempts=attempt_count(r)
   strategy=attempts%ocr.OCR_STRATEGY_COUNT
   detail.update({"attempt":attempts+1,"ocr_strategy":strategy,
                  "reviewed_phrases":len(phrases),
                  "covered_before":len(covered_before),
                  "unresolved_before":sorted(unresolved_before.values())})
   if not unresolved_before:
    detail["status"]="COVERAGE_COMPLETE"
    detail["matches"]=0
   else:
    cached=ocr_cache.get(index)
    if cached and cached[0]==h:
     words=cached[1]
    else:
     words=ocr.ocr_words(image,strategy=strategy)
    matches=ocr.unique_regions(words,unresolved_before,image.width,image.height,
                               allow_fuzzy=attempts>=3)
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
    _,covered_after,unresolved_after=_coverage(r,OUT)
    detail.update({"status":("COVERAGE_COMPLETE" if not unresolved_after else
                             "COVERAGE_PENDING"),
                   "words":sum(len(x) for x in words),
                   "matches":len(matches),"hard_holds":hardhold,
                   "covered_after":len(covered_after),
                   "unresolved_after":sorted(unresolved_after.values())})
   result["scanned"]+=1
  except Exception as e:
   result["held"]+=1
   detail.update({"status":"HOLD","reason":type(e).__name__+":"+str(e)[:180]})
  result["details"].append(detail)
  discover.save_json_atomic(record_for(r),{
      "status":detail.get("status","HOLD"),"policy_version":POLICY_VERSION,
      "source_png":name,"source_sha256":r["png_sha256"],
      "source_size_bytes":int(r["png_size_bytes"]),
      "source_dimensions":[int(r["width"]),int(r["height"])],
      "attempts":attempt_count(r)+1,
      "ocr_strategy":detail.get("ocr_strategy"),
      "ocr_matches":detail.get("matches",0),
      "unresolved_after":detail.get("unresolved_after",[]),
      "hard_holds":hardhold,"review_only":True,
      "runtime_validation":"UNTESTED"})

 newcursor=(selected[-1][0]+1)%len(rows)
 discover.save_json_atomic(cursorfile,{"next":newcursor,"after":selected[-1][1]["png_filename"],
                                      "inventory":108,"policy_version":POLICY_VERSION})
 unresolved_rows=[row for row in rows if unresolved(row)]
 pending_phrase_after=sum(len(unresolved(row)) for row in unresolved_rows)
 result["pending_sources_after"]=len(unresolved_rows)
 result["pending_phrases_after"]=pending_phrase_after
 result["located_phrase_count"]=result["reviewed_phrase_total"]-pending_phrase_after
 if not unresolved_rows:
  result["status"]="HD108_CROP_COVERAGE_COMPLETE"
 discover.save_json_atomic(REPORT/"last_scan.json",result)
 return result
