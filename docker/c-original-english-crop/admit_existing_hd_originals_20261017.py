#!/usr/bin/env python3
"""Stage genuine native full-image HD DDS into the isolated English crop input root.

Sources must be exact official transcribed paths from canonical HD source or a
previously archived ORIGINAL DDS comparison (not 986 tiles, stitched images,
Korean result, generated plate or a lower-resolution fallback).
No changes to any A/B queue, game DDS, or historical 255 crops.
"""
import argparse,hashlib,io,json,os,re,shutil,struct,tempfile,zipfile
from pathlib import Path
from PIL import Image
HOME=Path("/home/chatgpt-runner2/work")
BASE=HOME/"c_salvage_text_roi/c_original_hd_crop_only"
SRC=HOME/"c_salvage_text_roi/source_full_20261012"
HD=HOME/"c_roi_q060_easy_git_20261016_0533/localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"
ARCHIVE=HOME/"c_roi_q060_easy_git_20261016_0533/localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
TABLE=SRC/"transcriptions.jsonl"
REGISTRY=BASE/"docker/source_registry_auto.json"
RECEIPTS=BASE/"docker/original_admission_audit.json"

def sha(data):
 return hashlib.sha256(data).hexdigest()
def sha_file(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for part in iter(lambda:f.read(1<<20),b""):h.update(part)
 return h.hexdigest()
def atomic_json(p,obj):
 tmp=p.with_name(p.name+".staging")
 tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 os.replace(tmp,p)
def exact_paths():
 entries={}
 for line in TABLE.read_text(encoding="utf-8").splitlines():
  if not line.strip():continue
  x=json.loads(line)
  if x.get("status")!="transcribed_reviewed" or not x.get("segments"):continue
  path=x.get("path","")
  if not path.startswith("textures/load/") or Path(path).suffix.lower()!=".dds":continue
  q="Q"+str(x["index"]).zfill(3)
  if q not in entries:entries[q]=path
 return entries
def dims_from_name(path):
 m=re.search(r"_(\d+)x(\d+)\.dds$",path,re.I)
 if not m: return None
 return int(m.group(1)),int(m.group(2))
def candidate_items():
 entries=exact_paths()
 with zipfile.ZipFile(ARCHIVE) as z:
  filenames=set(z.namelist())
  for q,path in sorted(entries.items()):
   canonical=HD/path
   options=[]
   if canonical.is_file():
    options.append(("GIT_PINNED_CANONICAL_HD_SOURCE",canonical))
   if path in filenames:
    options.append(("ORIGINAL_BINARY_COMPARE_ARCHIVE",path))
   for kind,source in options:
    try:
     raw=source.read_bytes() if isinstance(source,Path) else z.read(source)
     if len(raw)<128 or raw[:4]!=b"DDS ":continue
     height,width=struct.unpack_from("<II",raw,12)
     ref=dims_from_name(path)
     # Verified 4x actual HD, not merely a file named HD with low-res pixels.
     if not ref or (width,height)!=(ref[0]*4,ref[1]*4):continue
     with Image.open(io.BytesIO(raw)) as im:
      if im.format!="DDS" or im.size!=(width,height):continue
      im.verify()
     yield q,path,kind,source,(width,height),raw
     break
    except Exception as exc:
     print(json.dumps({"q":q,"source":str(source),"hold":str(exc)[:140]}),flush=True)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--limit",type=int,default=100)
 args=ap.parse_args()
 if not 1<=args.limit<=100:raise SystemExit("bad limit")
 # Earlier registry must be preserved; add new entries only.
 prior=json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {"schema":"outrun-dds-pixel-verified-native-HD-sources-v1","entries":{}}
 if prior.get("schema")!="outrun-dds-pixel-verified-native-HD-sources-v1":raise ValueError("REGISTRY_SCHEMA")
 prior.setdefault("entries",{})
 receipts=json.loads(RECEIPTS.read_text()) if RECEIPTS.exists() else {"archive_sha256":sha_file(ARCHIVE),"entries":[]}
 existing=prior["entries"]
 added=[]
 held=[]
 archive_hash=sha_file(ARCHIVE)
 if receipts.get("archive_sha256")!=archive_hash:raise ValueError("SOURCE_ARCHIVE_CHANGED_HOLD")
 for q,source_path,origin,source,size,raw in candidate_items():
  if len(added)>=args.limit:break
  if q in existing or q in ("Q051","Q060","Q116","Q161","Q197","Q212"):
   continue
  dhash=sha(raw)
  suffix=Path(source_path).stem.split("_")[0]
  dname=q+"_"+suffix+"_DIRECT_HD_EN_"+dhash[:12]+".dds"
  pname=q.lower()+"_"+suffix+"_DIRECT_ORIGINAL_HD_READABLE_"+dhash[:12]+".png"
  dp=SRC/dname;pp=SRC/pname
  try:
   # Do not allow overwrite; any stale mismatch is HOLD.
   if dp.exists():
    if sha_file(dp)!=dhash:raise ValueError("DDS_PATH_COLLISION")
   else:
    temp=dp.with_name("."+dp.name+".tmp")
    with temp.open("xb") as f:f.write(raw)
    os.replace(temp,dp)
   if pp.exists():
    phash=sha_file(pp)
   else:
    with Image.open(dp) as im:
     # DDS stores game-native origin; readable atlas is FLIPY, no scale.
     readable=im.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if readable.size!=size:raise ValueError("NATIVE_DIMENSIONS")
    temp=pp.with_name("."+pp.name+".tmp")
    readable.save(temp,format="PNG")
    with Image.open(temp) as verify:
     if verify.size!=readable.size or verify.mode!=readable.mode or verify.tobytes()!=readable.tobytes():
      raise ValueError("PNG_PIXEL_ROUNDTRIP")
    os.replace(temp,pp)
    phash=sha_file(pp)
   # Confirm staged DDS has the identical original bytes.
   if sha_file(dp)!=dhash:raise ValueError("DDS_COPY_SHA_CHANGED")
   with Image.open(dp) as d,Image.open(pp) as p:
    from PIL import ImageChops
    if p.size!=size or p.mode!="RGBA" or ImageChops.difference(d.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),p.convert("RGBA")).getbbox() is not None:
     raise ValueError("FULL_IMAGE_DDS_PNG_PIXELS_DIFFER")
   entry={"png":pname,"png_sha256":phash,"size":list(size),"dds":dname,
           "dds_sha256":dhash,"dds_repo_path":source_path,"admission_provenance":origin,
           "original_zip_sha256":archive_hash if origin=="ORIGINAL_BINARY_COMPARE_ARCHIVE" else None,
           "native_scale":4,"orientation":"DDS_FLIPY_READABLE_PNG",
           "status":"SOURCE_VERIFIED_CROP_TEST_ONLY"}
   existing[q]=entry
   added.append({"q":q,"path":source_path,"origin":origin,"size":size,"dds_sha256":dhash})
   receipts["entries"].append({"q":q,"path":source_path,"dds_sha256":dhash,"png_sha256":phash,"source":origin})
   # Crash-safe archive preservation: registry only after original files verified.
   atomic_json(REGISTRY,prior)
   atomic_json(RECEIPTS,receipts)
   print(json.dumps({"ADMITTED":q,"dimensions":size,"origin":origin}),flush=True)
  except Exception as e:
   held.append({"q":q,"reason":str(e)})
   print(json.dumps({"HOLD":q,"reason":str(e)}),flush=True)
 print(json.dumps({"result":"HD_STAGE_COMPLETE","admitted":len(added),"new":added,"held":held,
                  "registry_total":len(existing),"zip_original_sha256":archive_hash},ensure_ascii=False),flush=True)
if __name__=="__main__":main()