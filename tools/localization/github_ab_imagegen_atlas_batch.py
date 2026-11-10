#!/usr/bin/env python3
"""SHA-gated A/B ImageGen multi-ROI -> native DDS. GitHub CPU, TEST_ONLY.

Selects only files already imported to the GitHub asset branch from the 954
reviewed translation rows. Unlike per-ROI outputs it composites each source
atlas once and never invents glyphs using a generic font.
"""
import argparse, csv, hashlib, io, json, re, struct, zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from PIL import Image, ImageChops, ImageDraw, ImageOps, UnidentifiedImageError
from hd_strict_qa import process_strict_atlas
from hd_bc3_index_patch import bc3_shape
from hd_bc3_native_codec import BC3Hold as NativeBC3Hold
from hd_manual_user_import import apply_user_manual_candidates

CROSS="localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv"
ORIGINAL="localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"
CANDIDATES="localization/automation_inputs/candidate_outputs"
APPROVED="localization/automation_inputs/qa_rework/approved"
SOURCE_PLAN="localization/automation_inputs/hd_original_png_source_plan.json"
ZIPNAME="OUTRUN_AB_HD_STRICT_CLEAN_TEST_ONLY.zip"
MASKS=(0x00ff0000,0x0000ff00,0x000000ff,0xff000000)
MASKS_RGBA=(0x000000ff,0x0000ff00,0x00ff0000,0xff000000)
ORIENTATIONS={
"D6DC1380":"NORMAL","19CEDB9":"FLIPY","FF2462BB":"FLIPY",
# Q047 original PNG 3ca447ddebe3035a2a16a70fd36f7805858bba02c6cf9ccd749c80d7a9c59d6c;
# original DDS 141e1f0773b82a8eca6ff49cd93d637221b96211566541f97de9ef4fc454d26f;
# both source-verified, original READABLE_FLIPY; try only this atlas, HOLD on all failures.
"AD720950":"FLIPY",
"568D3696":"FLIPY","FA7BBB13":"FLIPY","39229D64":"FLIPY",
"A064FDFC":"FLIPY","C4A2937B":"FLIPY","48DEBE77":"FLIPY",
"2DA43E41":"FLIPY","411827E":"FLIPY","571E78F3":"FLIPY",
"62BEBF33":"FLIPY","C075FB49":"FLIPY","E3FD08BE":"FLIPY",
"FD90AA9":"FLIPY","9F060EC1":"FLIPY"
}

def sha(b):return hashlib.sha256(b).hexdigest()

def imported_candidate(root,row):
 p=root/row["_candidate_rel"]
 return p.is_file() and not p.is_symlink()

def preview_name(target):
 return "PREVIEW_"+PurePosixPath(target).stem+"_"+sha(target.encode("utf-8"))[:16]+".png"
def good_path(path):
 p=PurePosixPath(path)
 return isinstance(path,str) and path.startswith("textures/load/") and p.suffix==".dds" and "\\" not in path and ":" not in path and ".." not in p.parts and len(p.parts) in (4,5) and (len(p.parts)==4 or p.parts[2] in ("Keyboard","PlayStation","Switch","Xbox")) and all(re.fullmatch(r"[A-Za-z0-9_.-]+",x) for x in p.parts)

def load_cross(path):
 with path.open(encoding="utf-8-sig",newline="") as f:
  rows=list(csv.DictReader(f))
 if len(rows)!=954 or len({r["roi_id"] for r in rows})!=954:
  raise ValueError("CROSSWALK_NOT_954_UNIQUE_ACTIVE")
 groups=defaultdict(list)
 for r in rows:
  target=r["source_dds_path"]
  if not good_path(target):raise ValueError("BAD_TARGET:"+r["roi_id"])
  if not re.fullmatch(r"[0-9a-f]{64}",r["source_dds_sha256"]):raise ValueError("DDS_SHA_NOT_PINNED")
  if r["candidate_status"]!="CANDIDATE_ONLY_QA_UNVERIFIED" or r["candidate_count"]!="1":
   raise ValueError("CANDIDATE_STATUS_CHANGED")
  if not re.fullmatch(r"Q\d{3}_[0-9a-f]{16}(?:_RB_B)?",r["roi_id"]):raise ValueError("INVALID_ROI_ID")
  if r["roles"] not in ("A","B"):raise ValueError("INVALID_ROLE")
  m=re.fullmatch(r"/home/chatgpt-runner2/work/image-src/text_roi_batches/candidate_outputs/([AB])/([A-Za-z0-9_-]+\.png)",r["candidate_paths"])
  if not m or m.group(1)!=r["roles"] or m.group(2) not in (r["roi_id"].removesuffix("_RB_B")+"_k.png",r["roi_id"].removesuffix("_RB_B")+"_source_k.png"):
   raise ValueError("UNSAFE_OR_AMBIGUOUS_CANDIDATE:"+r["roi_id"])
  r["_candidate_rel"]=f"{CANDIDATES}/{m.group(1)}/{m.group(2)}"
  box=json.loads(r["bbox_xyxy"])
  if len(box)!=4 or any(type(x)!=int for x in box):raise ValueError("BAD_ROI_BOX")
  r["_bbox"]=box
  groups[target].append(r)
 return groups

def load_pinned_orientations(repo, groups):
 """Only use orientation from exact SHA-pinned HD source plan.

 Plan original-PNG orientation is metadata evidence, NOT visual signoff. The
 native DDS must independently match the SHA in both plan and crosswalk.
 """
 plan=json.loads((repo/SOURCE_PLAN).read_text(encoding="utf-8"))
 entries=plan.get("entries")
 if not isinstance(entries,list) or len(entries)!=104:
  raise ValueError("HD_ORIENTATION_PLAN_NOT_104")
 pins={}
 for entry in entries:
  target=entry.get("target")
  direction=entry.get("orientation")
  original=entry.get("original_dds_sha256")
  png=entry.get("original_png_sha256")
  if target in pins or not good_path(target):
   raise ValueError("HD_ORIENTATION_PLAN_DUPLICATE_OR_UNSAFE_PATH")
  if direction not in ("NORMAL","FLIPY") or not isinstance(original,str) or not re.fullmatch(r"[0-9a-f]{64}",original):
   raise ValueError("HD_ORIENTATION_PLAN_UNPINNED")
  if not isinstance(png,str) or not re.fullmatch(r"[0-9a-f]{64}",png):
   raise ValueError("HD_ORIENTATION_PNG_SHA_MISSING")
  pins[target]={"orientation":direction,"sha256":original}
 if set(pins)!=set(groups):
  raise ValueError("HD_ORIENTATION_PLAN_TARGETS_DIFFER_FROM_CROSSWALK")
 for target,rows in groups.items():
  if any(r["source_dds_sha256"]!=pins[target]["sha256"] for r in rows):
   raise ValueError("HD_ORIENTATION_PLAN_DDS_SHA_CONFLICT:"+target)
  ident=PurePosixPath(target).stem.split("_")[0]
  if ident in ORIENTATIONS and ORIENTATIONS[ident]!=pins[target]["orientation"]:
   raise ValueError("HD_ORIENTATION_PLAN_CONFLICT_WITH_PRIOR_PIN:"+target)
 return {target:item["orientation"] for target,item in pins.items()}

def dominant_container_holds(rows):
 """Hold coarse boxes spanning multiple smaller text regions.

 Never guess which text should overwrite which. A provably large enclosing
 box is *excluded*, allowing disjoint smaller boxes to be evaluated safely.
 """
 def inside(a,b):
  a0,a1,a2,a3=a
  b0,b1,b2,b3=b
  return a0<=b0 and a1<=b1 and b2<=a2 and b3<=a3 and (a0<b0 or a1<b1 or b2<a2 or b3<a3)
 def size(b):
  return (b[2]-b[0])*(b[3]-b[1])
 held=set()
 for row in rows:
  outer=row["_bbox"]
  children=sum(1 for other in rows if other is not row and
   inside(outer,other["_bbox"]) and size(outer)>=4*size(other["_bbox"]))
  if children>=2:held.add(row["roi_id"])
 return held

def apply_c1_preliminary_overrides(root,groups):
 """Use new ImageGen PNG only with independent C1 SHA-bound receipt.

 A passed C1 is still TEST_ONLY; strict clean/size/line QA runs again in DDS.
 """
 directory=root/APPROVED
 if not directory.is_dir():
  return 0
 by_id={r["roi_id"]:r for rows in groups.values() for r in rows}
 used=set()
 imported=0
 for receipt_path in sorted(directory.glob("HDRW-*.json")):
  if receipt_path.is_symlink() or receipt_path.stat().st_size>16000:
   raise ValueError("C1_RECEIPT_INVALID_FILE")
  item=json.loads(receipt_path.read_text(encoding="utf-8"))
  task=item.get("task_id","")
  if not re.fullmatch(r"HDRW-[AB]-[0-9a-f]{20}",task):
   raise ValueError("C1_TASK_ID_UNSAFE")
  if task in used or receipt_path.stem!=task:
   raise ValueError("C1_DUPLICATE_OR_NAME_CONFLICT")
  used.add(task)
  rid=item.get("roi_id")
  if rid not in by_id:
   raise ValueError("C1_ROI_NOT_IN_954")
  row=by_id[rid]
  if (item.get("schema")!="outrun-hd-rework-c1-provisional-v1" or
      item.get("role")!=row["roles"] or
      item.get("source_dds_sha256")!=row["source_dds_sha256"] or
      item.get("source_dds_path")!=row["source_dds_path"] or
      item.get("c1_decision")!="C1_PRELIMINARY_PASS_NOT_C3" or
      item.get("release_approved") is not False or
      item.get("runtime_validation")!="UNTESTED"):
   raise ValueError("C1_RECEIPT_NOT_PINNED_OR_FAKE_APPROVAL")
  prior=root/row["_candidate_rel"]
  if not prior.is_file() or prior.is_symlink():
   raise ValueError("C1_ORIGINAL_CANDIDATE_MISSING")
  if sha(prior.read_bytes())!=item.get("old_candidate_sha256"):
   raise ValueError("C1_ORIGINAL_CANDIDATE_SHA_CHANGED")
  candidate=directory/(task+".png")
  if not candidate.is_file() or candidate.is_symlink() or candidate.stat().st_size>4*1024*1024:
   raise ValueError("C1_NEW_CANDIDATE_UNAVAILABLE")
  if sha(candidate.read_bytes())!=item.get("candidate_sha256"):
   raise ValueError("C1_NEW_CANDIDATE_SHA_CHANGED")
  row["_candidate_rel"]=str(candidate.relative_to(root))
  row["_c1_source_candidate_sha256"]=item["old_candidate_sha256"]
  row["_c1_receipt"]=task
  imported+=1
 return imported

def native_image(b):
 if len(b)<128 or b[:4]!=b"DDS " or struct.unpack_from("<I",b,4)[0]!=124:raise ValueError("DDS_HEADER")
 height,width=struct.unpack_from("<II",b,12)
 if not 0<height<=4096 or not 0<width<=4096:raise ValueError("DDS_DIMENSIONS")
 if (struct.unpack_from("<I",b,76)[0]==32 and
     struct.unpack_from("<I",b,80)[0]==4 and
     b[84:88]==b"DXT5"):
  # The BC3 codec never changes source endpoints or any untouched pixel;
  # mip chains fail closed until their complete format-preserving path exists.
  bc3_shape(b)
  with Image.open(io.BytesIO(b)) as im:
   im.load()
   image=im.convert("RGBA")
  if image.size!=(width,height):raise ValueError("QA_BC3_DECODE_DIMENSIONS")
  return image
 if (struct.unpack_from("<I",b,76)[0]!=32 or
     struct.unpack_from("<I",b,80)[0]!=65 or
     struct.unpack_from("<I",b,88)[0]!=32 or
     struct.unpack_from("<I",b,28)[0]!=1 or
     struct.unpack_from("<IIII",b,92) not in (MASKS,MASKS_RGBA) or
     b[84:88]!=bytes(4) or len(b)!=128+width*height*4):
  raise ValueError("DDS_NOT_32_BGRA_MIP1:"+json.dumps({"size":[width,height],"mip":struct.unpack_from("<I",b,28)[0],"pf_size":struct.unpack_from("<I",b,76)[0],"pf_flags":struct.unpack_from("<I",b,80)[0],"depth":struct.unpack_from("<I",b,88)[0],"masks":list(struct.unpack_from("<IIII",b,92)),"payload":len(b)-128},separators=(",",":")))
 with Image.open(io.BytesIO(b)) as im:
  image=im.convert("RGBA")
 if image.size!=(width,height) or image.tobytes("raw","BGRA" if struct.unpack_from("<IIII",b,92)==MASKS else "RGBA")!=b[128:]:
  raise ValueError("DDS_ORIGINAL_PIXELS_DIFFER")
 return image

def prepare_candidate(b):
 if len(b)>4*1024*1024:raise ValueError("CANDIDATE_TOO_BIG")
 with Image.open(io.BytesIO(b)) as im:
  if im.format!="PNG" or not 24<=im.width<=4096 or not 12<=im.height<=4096:
   raise ValueError("CANDIDATE_NOT_APPROVED_PNG")
  im.load()
  cand=im.convert("RGBA")
 raw=cand.getchannel("A").getbbox()
 if not raw:raise ValueError("CANDIDATE_INVISIBLE")
 if raw[0]==0 or raw[1]==0 or raw[2]==cand.width or raw[3]==cand.height:
  raise ValueError("CANDIDATE_BORDER_TOUCH")
 alpha=cand.getchannel("A").point(lambda v:255 if v>=16 else 0).getbbox()
 if not alpha:raise ValueError("CANDIDATE_INVISIBLE_ALPHA16")
 pad=4
 box=(max(0,alpha[0]-pad),max(0,alpha[1]-pad),
      min(cand.width,alpha[2]+pad),min(cand.height,alpha[3]+pad))
 return cand.crop(box),box

def intersects(a,b):
 return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]

def conflicting_rois(rows):
 conflicts=set()
 for i,row in enumerate(rows):
  for other in rows[i+1:]:
   if intersects(row["_bbox"],other["_bbox"]):
    conflicts.update((row["roi_id"],other["roi_id"]))
 return conflicts

def process_atlas(raw,rows,repo,orientation):
 readable=native_image(raw)
 if orientation=="FLIPY":readable=ImageOps.flip(readable)
 result=readable.copy();used=[];painted=[];holds=[]
 containers=dominant_container_holds(rows)
 conflicts=conflicting_rois([r for r in rows if r["roi_id"] not in containers])
 for row in sorted(rows,key=lambda r:(r["_bbox"][1],r["_bbox"][0],r["roi_id"])):
  rid=row["roi_id"]
  if rid in containers:
   holds.append({"roi_id":rid,"reason":"COARSE_ROI_CONTAINS_OTHER_TEXT_HOLD"});continue
  if rid in conflicts:
   holds.append({"roi_id":rid,"reason":"ROI_OVERLAP_NEEDS_MANUAL_QA"});continue
  path=repo/row["_candidate_rel"]
  if not imported_candidate(repo,row):
   holds.append({"roi_id":rid,"reason":"AB_PNG_NOT_YET_IMPORTED"});continue
  try:
   (x0,y0,x1,y1)=row["_bbox"]
   if not 0<=x0<x1<=readable.width or not 0<=y0<y1<=readable.height:
    raise ValueError("ROI_NOT_IN_NATIVE_DDS")
   box=(x0,y0,x1,y1)
   if any(intersects(box,prev) for prev in used):
    raise ValueError("ROI_OVERLAP_NEEDS_MANUAL_QA")
   area=readable.crop(box)
   source_box=area.getchannel("A").getbbox()
   if not source_box:raise ValueError("ORIGINAL_ALPHA_MISSING")
   # A/B source atlas text is alpha-isolated. Opaque panels/artwork require manual masks.
   hist=area.getchannel("A").histogram()
   opaque=sum(hist[192:])/max(1,area.width*area.height)
   if opaque>0.80:raise ValueError("OPAQUE_PROTECTED_ART_HOLD")
   ink_box=(x0+source_box[0],y0+source_box[1],
            x0+source_box[2],y0+source_box[3])
   if ink_box[2]-ink_box[0]<3 or ink_box[3]-ink_box[1]<3:
    raise ValueError("NATIVE_SOURCE_INK_TOO_SMALL")
   data=path.read_bytes()
   art,alpha_crop=prepare_candidate(data)
   maxw=ink_box[2]-ink_box[0];maxh=ink_box[3]-ink_box[1]
   factor=min(maxw/art.width,maxh/art.height)
   nw=max(1,min(maxw,int(art.width*factor)));nh=max(1,min(maxh,int(art.height*factor)))
   rendered=art.resize((nw,nh),Image.Resampling.LANCZOS)
   px=ink_box[0]+(maxw-nw)//2;py=ink_box[1]+(maxh-nh)//2
   # Blank the native SOURCE INK box ONLY; no edits to unrelated pixels.
   result.paste((0,0,0,0),ink_box)
   result.alpha_composite(rendered,(px,py))
   used.append(box)
   painted.append({"roi_id":rid,"english":row["english"],"korean":row["korean"],
     "sha256_candidate":sha(data),"roi":list(box),"native_ink":list(ink_box),
     "new_ink":[px,py,px+nw,py+nh],"alpha_crop":list(alpha_crop)})
  except (OSError,ValueError,OverflowError,UnidentifiedImageError) as exc:
   holds.append({"roi_id":rid,"reason":str(exc)[:100]})
 if not painted:return None,None,painted,holds
 mask=Image.new("L",readable.size,0)
 draw=ImageDraw.Draw(mask)
 for x0,y0,x1,y1 in used:draw.rectangle((x0,y0,x1-1,y1-1),fill=255)
 diffs=ImageChops.difference(readable,result)
 if any(ImageChops.multiply(v,ImageOps.invert(mask)).getbbox() for v in diffs.split()):
  raise ValueError("SOURCE_PROTECTED_PIXELS_CHANGED")
 native=result if orientation=="NORMAL" else ImageOps.flip(result)
 data=raw[:128]+native.tobytes("raw","BGRA" if struct.unpack_from("<IIII",raw,92)==MASKS else "RGBA")
 if data[:128]!=raw[:128] or len(data)!=len(raw) or data==raw:
  raise ValueError("DDS_HEADER_OR_NOOP_ERROR")
 restored=native_image(data)
 if ImageChops.difference(restored,native).getbbox():
  raise ValueError("DDS_BINARY_ROUNDTRIP_BAD")
 return data,result,painted,holds

def zput(z,name,raw):
 i=zipfile.ZipInfo(name,(1980,1,1,0,0,0))
 i.external_attr=0o100644<<16
 i.compress_type=zipfile.ZIP_DEFLATED
 z.writestr(i,raw,compresslevel=4)

def process_strict_with_bc3_quarantine(raw,rows,repo,orientation):
 # Quarantine up to four exact, unambiguous failing ROIs per DDS.
 # Every other original ROI and protected pixel is still independently gated.
 excluded=set()
 for _ in range(min(5,len(rows)+1)):
  try:
   return process_strict_atlas(raw,rows,repo,orientation,native_image,
    imported_candidate,conflicting_rois,dominant_container_holds,
    excluded_bc3=excluded)
  except NativeBC3Hold as exc:
   if str(exc)!="QA_BC3_TRANSLATED_COLOR_LOSS":raise
   xy=getattr(exc,"native_xy",None)
   if not(isinstance(xy,tuple) and len(xy)==2 and
          all(isinstance(v,int) for v in xy)):raise
   x,ny=xy
   height=struct.unpack_from("<I",raw,12)[0]
   y=height-1-ny if orientation=="FLIPY" else ny
   matches=[r["roi_id"] for r in rows
    if r["roi_id"] not in excluded and
       r["_bbox"][0]<=x<r["_bbox"][2] and
       r["_bbox"][1]<=y<r["_bbox"][3]]
   if len(matches)!=1:raise
   excluded.add(matches[0])
 raise ValueError("QA_BC3_COLOR_ISOLATION_BUDGET_EXHAUSTED")


def build(root,out):
 root=Path(root).resolve();out=Path(out).resolve()
 if out.is_relative_to(root):raise ValueError("OUTPUT_INSIDE_REPO_FORBIDDEN")
 out.mkdir(parents=True,exist_ok=True)
 groups=load_cross(root/CROSS)
 orientations=load_pinned_orientations(root,groups)
 manual_user_count=apply_user_manual_candidates(root,groups)
 c1_provisional_count=apply_c1_preliminary_overrides(root,groups)
 archive={};admitted=[];holds=[];unavailable=0;sha_conflicts=0
 for target,rows in sorted(groups.items()):
  imported_rows=[r for r in rows if imported_candidate(root,r)]
  imported=len(imported_rows)
  if not imported:continue
  path=root/ORIGINAL/target
  if not path.is_file() or path.is_symlink():
   unavailable+=imported
   holds.append({"target":target,"reason":"SOURCE_DDS_UNAVAILABLE_IN_GITHUB","rows":imported,"roi_ids":[r["roi_id"] for r in imported_rows]})
   continue
  hashes={r["source_dds_sha256"] for r in rows}
  if len(hashes)!=1 or path.stat().st_size>80*1024*1024:
   holds.append({"target":target,"reason":"SOURCE_DDS_SHA_AMBIGUOUS_OR_TOO_BIG","rows":imported,"roi_ids":[r["roi_id"] for r in imported_rows]});continue
  raw=path.read_bytes()
  if sha(raw)!=next(iter(hashes)):
   sha_conflicts+=imported
   holds.append({"target":target,"reason":"SOURCE_DDS_SHA_MISMATCH","rows":imported,"roi_ids":[r["roi_id"] for r in imported_rows]});continue
  orientation=orientations[target]
  try:
   binary,readable,clean,painted,local_holds=process_strict_with_bc3_quarantine(
    raw,rows,root,orientation)
   if painted:
    archive[target]=binary
    thumb=readable.copy()
    thumb.thumbnail((1536,1536),Image.Resampling.LANCZOS)
    thumb.save(out/preview_name(target),format="PNG")
    source_view=native_image(raw)
    if orientation=="FLIPY":source_view=ImageOps.flip(source_view)
    source_view.thumbnail((1536,1536),Image.Resampling.LANCZOS)
    source_view.save(out/preview_name(target).replace("PREVIEW_","SOURCE_"),format="PNG")
    clean_view=clean.copy()
    clean_view.thumbnail((1536,1536),Image.Resampling.LANCZOS)
    clean_view.save(out/preview_name(target).replace("PREVIEW_","CLEAN_"),format="PNG")
    admitted.append({"target":target,"origin_sha256":sha(raw),"dds_sha256":sha(binary),
                     "orientation":orientation,"orientation_evidence":"DDS_SHA_PINNED_SOURCE_PLAN_NOT_VISUAL_QA",
                     "plate_evidence":"SOURCE_CLEAN_FINAL_PREVIEWS_REVIEW_REQUIRED",
                     "text_scale_gate":"NO_NEW_GLYPH_LINE_LARGER_THAN_ORIGINAL_NATIVE_HD_EFFECT_BBOX",
                     "painted":painted,
                     "holds":local_holds})
   else:
    holds.append({"target":target,"reason":"IMPORTED_ROI_ALL_HELD",
                  "rows":imported,"roi_ids":[r["roi_id"] for r in imported_rows],"details":local_holds})
  except (OSError,ValueError,OverflowError) as exc:
   holds.append({"target":target,"reason":str(exc)[:130],"rows":imported,"roi_ids":[r["roi_id"] for r in imported_rows]})
 imported_total=sum(imported_candidate(root,r) for rows in groups.values() for r in rows)
 pending_import_holds=[{"roi_id":r["roi_id"],"target":target,"reason":"AB_PNG_NOT_YET_IMPORTED"}
  for target,rows in sorted(groups.items()) for r in rows if not imported_candidate(root,r)]
 if len(pending_import_holds)!=954-imported_total:raise ValueError("PENDING_IMPORT_HOLD_COUNT_MISMATCH")
 report={"schema":"outrun.ab-imagegen-hd-strict.v2",
         "legacy_oversize_outputs_rejected":True,
         "clean_plate_qa":"MECHANICAL_ALPHA_ONLY_C1_C3_VISUAL_REVIEW_REQUIRED",
         "scale_policy":"SOURCE_NATIVE_HD_GLYPH_AND_LINE_BOX_CEILING_NO_UPSCALE",
         "layout_policy":"ORIGINAL_LINE_COUNT_AND_PER_LINE_BBOX_PRESERVED",
         "release_approved":False,"runtime_validation":"UNTESTED","visual_qa":"REVIEW_REQUIRED",
         "source":"Existing A/B PNG reused exclusively; native HD bounded pad/reflow/downscale; no new ImageGen or fonts",
         "salvage_policy":"EXISTING_AB_PNG_RESIZE_REFLOW_ONLY_NO_NEW_IMAGEGEN_V2",
         "active_roi_total":954,"imported_roi_total":imported_total,
         "c1_preliminary_new_png_count":c1_provisional_count,
         "manual_user_test_only_roi_count":manual_user_count,
         "cosmetic_alpha_tolerance_max":15,
         "cosmetic_bc3_color_channel_error_max":64,
         "manual_stage_child_roi_test_only":manual_user_count > 0,
         "deterministic_salvaged_roi":sum(
             1 for atlas_item in admitted for p in atlas_item["painted"] if p.get("auto_salvage")
         ),
         "pending_import":954-imported_total,
         "native_dds_generated":len(archive),
         "translated_roi_generated":sum(len(v["painted"]) for v in admitted),
         "source_dds_missing_rows":unavailable,"source_sha_conflict_rows":sha_conflicts,
         "generated":admitted,"holds":holds,"pending_import_holds":pending_import_holds}
 with zipfile.ZipFile(out/ZIPNAME,"w") as z:
  for path,dds in sorted(archive.items()):zput(z,path,dds)
  zput(z,"TEST_ONLY_MANIFEST.json",json.dumps({
   "status":"NOT_GAME_APPROVED","source":"A/B existing ImageGen PNG deterministic salvage first",
   "release_approved":False,"game_runtime":"UNTESTED",
   "hd_quality_gate":"SOURCE_CLEAN_FINAL_STRICT_V2_NOT_VISUALLY_APPROVED",
   "entries":{p:sha(d) for p,d in sorted(archive.items())}},
   ensure_ascii=False,sort_keys=True,indent=2).encode())
 with zipfile.ZipFile(out/ZIPNAME) as z:
  if z.testzip() is not None:raise ValueError("ZIP_CRC_BAD")
  for path,dds in archive.items():
   if z.read(path)!=dds:raise ValueError("ZIP_SOURCE_DDS_REENCODE_MISMATCH")
 reason_counts={}
 def note(reason,n=1):
  reason_counts[reason]=reason_counts.get(reason,0)+n
 for h in holds:
  if h.get("details"):
   for local in h["details"]:note(local["reason"])
  else:note(h["reason"],h.get("rows",1))
 for g in admitted:
  for h in g["holds"]:note(h["reason"])
 for h in pending_import_holds:note(h["reason"])
 report["hold_roi_reason_counts"]=dict(sorted(reason_counts.items()))
 if sum(reason_counts.values())+report["translated_roi_generated"]!=report["active_roi_total"]:
  raise ValueError("ROI_HOLD_COVERAGE_MISMATCH")
 report["zip_sha256"]=sha((out/ZIPNAME).read_bytes())
 (out/"qa_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps({k:report[k] for k in ("active_roi_total","imported_roi_total","native_dds_generated",
   "translated_roi_generated","source_dds_missing_rows","source_sha_conflict_rows","hold_roi_reason_counts","zip_sha256")},ensure_ascii=False))
 if not archive:
  print("QA_ALL_ROWS_HELD_NO_SAFE_NATIVE_ATLAS",flush=True)
 return report

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--repo-root",default=".")
 p.add_argument("--out",default="/tmp/outrun-ab-multi-atlas")
 a=p.parse_args()
 build(a.repo_root,a.out)
