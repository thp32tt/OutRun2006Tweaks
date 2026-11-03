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

CROSS="localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv"
ORIGINAL="localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"
CANDIDATES="localization/automation_inputs/candidate_outputs"
ZIPNAME="OUTRUN_AB_IMAGEGEN_MULTI_ATLAS_TEST_ONLY.zip"
MASKS=(0x00ff0000,0x0000ff00,0x000000ff,0xff000000)
ORIENTATIONS={
"D6DC1380":"NORMAL","19CEDB9":"FLIPY","FF2462BB":"FLIPY",
"568D3696":"FLIPY","FA7BBB13":"FLIPY","39229D64":"FLIPY",
"A064FDFC":"FLIPY","C4A2937B":"FLIPY","48DEBE77":"FLIPY",
"2DA43E41":"FLIPY","411827E":"FLIPY","571E78F3":"FLIPY",
"62BEBF33":"FLIPY","C075FB49":"FLIPY","E3FD08BE":"FLIPY",
"FD90AA9":"FLIPY","9F060EC1":"FLIPY"
}

def sha(b):return hashlib.sha256(b).hexdigest()
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

def native_image(b):
 if len(b)<128 or b[:4]!=b"DDS " or struct.unpack_from("<I",b,4)[0]!=124:raise ValueError("DDS_HEADER")
 height,width=struct.unpack_from("<II",b,12)
 if not 0<height<=4096 or not 0<width<=4096:raise ValueError("DDS_DIMENSIONS")
 if (struct.unpack_from("<I",b,76)[0]!=32 or
     struct.unpack_from("<I",b,80)[0]!=65 or
     struct.unpack_from("<I",b,88)[0]!=32 or
     struct.unpack_from("<I",b,28)[0]!=1 or
     struct.unpack_from("<IIII",b,92)!=MASKS or
     b[84:88]!=bytes(4) or len(b)!=128+width*height*4):
  raise ValueError("DDS_NOT_32_BGRA_MIP1:"+json.dumps({"size":[width,height],"mip":struct.unpack_from("<I",b,28)[0],"pf_size":struct.unpack_from("<I",b,76)[0],"pf_flags":struct.unpack_from("<I",b,80)[0],"depth":struct.unpack_from("<I",b,88)[0],"masks":list(struct.unpack_from("<IIII",b,92)),"payload":len(b)-128},separators=(",",":")))
 with Image.open(io.BytesIO(b)) as im:
  image=im.convert("RGBA")
 if image.size!=(width,height) or image.tobytes("raw","BGRA")!=b[128:]:
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

def process_atlas(raw,rows,repo,orientation):
 readable=native_image(raw)
 if orientation=="FLIPY":readable=ImageOps.flip(readable)
 result=readable.copy();used=[];painted=[];holds=[]
 for row in sorted(rows,key=lambda r:(r["_bbox"][1],r["_bbox"][0],r["roi_id"])):
  rid=row["roi_id"]
  path=repo/row["_candidate_rel"]
  if not path.is_file() or path.is_symlink():
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
 data=raw[:128]+native.tobytes("raw","BGRA")
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

def build(root,out):
 root=Path(root).resolve();out=Path(out).resolve()
 if out.is_relative_to(root):raise ValueError("OUTPUT_INSIDE_REPO_FORBIDDEN")
 out.mkdir(parents=True,exist_ok=True)
 groups=load_cross(root/CROSS)
 archive={};admitted=[];holds=[];unavailable=0;sha_conflicts=0
 for target,rows in sorted(groups.items()):
  imported=sum((root/r["_candidate_rel"]).is_file() for r in rows)
  if not imported:continue
  path=root/ORIGINAL/target
  if not path.is_file() or path.is_symlink():
   unavailable+=imported
   holds.append({"target":target,"reason":"SOURCE_DDS_UNAVAILABLE_IN_GITHUB","rows":imported})
   continue
  hashes={r["source_dds_sha256"] for r in rows}
  if len(hashes)!=1 or path.stat().st_size>80*1024*1024:
   holds.append({"target":target,"reason":"SOURCE_DDS_SHA_AMBIGUOUS_OR_TOO_BIG","rows":imported});continue
  raw=path.read_bytes()
  if sha(raw)!=next(iter(hashes)):
   sha_conflicts+=imported
   holds.append({"target":target,"reason":"SOURCE_DDS_SHA_MISMATCH","rows":imported});continue
  ident=PurePosixPath(target).stem.split("_")[0]
  orientation=ORIENTATIONS.get(ident)
  if not orientation:
   holds.append({"target":target,"reason":"NATIVE_ORIENTATION_UNVERIFIED","rows":imported});continue
  try:
   binary,readable,painted,local_holds=process_atlas(raw,rows,root,orientation)
   if painted:
    archive[target]=binary
    thumb=readable.copy()
    thumb.thumbnail((1536,1536),Image.Resampling.LANCZOS)
    thumb.save(out/("PREVIEW_"+ident+".png"),format="PNG")
    admitted.append({"target":target,"origin_sha256":sha(raw),"dds_sha256":sha(binary),
                     "orientation":orientation,"painted":painted,
                     "holds":local_holds[:100]})
   else:
    holds.append({"target":target,"reason":"IMPORTED_ROI_ALL_HELD",
                  "rows":imported,"details":local_holds[:30]})
  except (OSError,ValueError,OverflowError) as exc:
   holds.append({"target":target,"reason":str(exc)[:130],"rows":imported})
 imported_total=sum((root/r["_candidate_rel"]).is_file() for rows in groups.values() for r in rows)
 report={"schema":"outrun.ab-imagegen-multi-atlas.v1",
         "release_approved":False,"runtime_validation":"UNTESTED","visual_qa":"REVIEW_REQUIRED",
         "source":"A/B original ImageGen PNG only, no font fallback",
         "active_roi_total":954,"imported_roi_total":imported_total,
         "pending_import":954-imported_total,
         "native_dds_generated":len(archive),
         "translated_roi_generated":sum(len(v["painted"]) for v in admitted),
         "source_dds_missing_rows":unavailable,"source_sha_conflict_rows":sha_conflicts,
         "generated":admitted,"holds":holds}
 with zipfile.ZipFile(out/ZIPNAME,"w") as z:
  for path,dds in sorted(archive.items()):zput(z,path,dds)
  zput(z,"TEST_ONLY_MANIFEST.json",json.dumps({
   "status":"NOT_GAME_APPROVED","source":"A/B ImageGen original PNG",
   "release_approved":False,"game_runtime":"UNTESTED",
   "entries":{p:sha(d) for p,d in sorted(archive.items())}},
   ensure_ascii=False,sort_keys=True,indent=2).encode())
 with zipfile.ZipFile(out/ZIPNAME) as z:
  if z.testzip() is not None:raise ValueError("ZIP_CRC_BAD")
  for path,dds in archive.items():
   if z.read(path)!=dds:raise ValueError("ZIP_SOURCE_DDS_REENCODE_MISMATCH")
 report["zip_sha256"]=sha((out/ZIPNAME).read_bytes())
 (out/"qa_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps({k:report[k] for k in ("active_roi_total","imported_roi_total","native_dds_generated",
   "translated_roi_generated","source_dds_missing_rows","source_sha_conflict_rows","zip_sha256")},ensure_ascii=False))
 if not archive:raise SystemExit("NO_SAFE_AB_NATIVE_ATLAS_GENERATED")
 return report

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--repo-root",default=".")
 p.add_argument("--out",default="/tmp/outrun-ab-multi-atlas")
 a=p.parse_args()
 build(a.repo_root,a.out)
