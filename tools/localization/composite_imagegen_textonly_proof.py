#!/usr/bin/env python3
"""TEST_ONLY ImageGen alpha compositing for isolated text-only full-HD sprite atlases.

No paid API, no OCR, no game writes. Fails closed on changed source identity,
ambiguous text rows, opaque source art or unsafe output targets.
"""
from __future__ import annotations
import argparse, hashlib, io, json, struct, zipfile
from pathlib import Path
from PIL import Image, ImageChops
try:
 import numpy as np
except ImportError:
 np=None

ROOT=Path("/home/chatgpt-runner2/work/image-src/text_roi_batches")
HD=Path("/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/hd_original_108_verified")
DEFAULT_OUT=ROOT/"ab_imagegen_composite_v2_test_only_20261102"
SELECTION={
 "Q012": ["Q012_0909e9d5397ec72e"],
 "Q055": ["Q055_dd5213d64f53d429"],
 "Q241": ["Q241_f3aead3fa521f783", "Q241_7157da1bb0c3538d"]
}

def sha(data):return hashlib.sha256(data).hexdigest()
def sha_path(p):return sha(Path(p).read_bytes())
def derive_source_index(name):
 parts=name.split("_")
 return parts[0]
def alpha_row_groups(img):
 a=img.getchannel("A")
 # alpha of nontransparent source pixel is authoritative: empty rows separate glyph runs
 groups=[];begin=None
 for y in range(img.height):
  bbox=a.crop((0,y,img.width,y+1)).getbbox()
  if bbox and begin is None:begin=y
  if begin is not None and (not bbox or y==img.height-1):
   end=y if not bbox else y+1
   groups.append((begin,end))
   begin=None
 return groups

def exact_box(img, ys):
 alpha=img.getchannel("A").crop((0,ys[0],img.width,ys[1]))
 b=alpha.getbbox()
 if not b: raise ValueError("EMPTY_SOURCE_ALPHA")
 return (b[0], b[1]+ys[0], b[2], b[3]+ys[0])

def encode_rgba_dds(img,orientation):
 raw=img if orientation=="NORMAL" else img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 w,h=raw.size
 d=bytearray(128);d[:4]=b"DDS "
 struct.pack_into("<I",d,4,124)
 struct.pack_into("<I",d,8,0x1|0x2|0x4|0x8|0x1000)
 struct.pack_into("<I",d,12,h);struct.pack_into("<I",d,16,w)
 struct.pack_into("<I",d,20,4*w);struct.pack_into("<I",d,28,1)
 struct.pack_into("<I",d,76,32);struct.pack_into("<I",d,80,0x41)
 struct.pack_into("<I",d,88,32)
 struct.pack_into("<IIII",d,92,255,65280,16711680,4278190080)
 struct.pack_into("<I",d,108,0x1000)
 return bytes(d)+raw.tobytes()

def run(root, hdroot, output, keys):
 root=Path(root);hdroot=Path(hdroot);output=Path(output)
 if output.resolve().is_relative_to((root/"candidate_outputs").resolve()):
  raise ValueError("OUTPUT_MUST_NOT_TOUCH_CANDIDATES")
 manifest=json.loads((root/"production_manifest.json").read_text())
 active={r["id"]:r for r in manifest["items"] if r.get("status")=="ROI_APPROVED_FOR_IMAGEGEN"}
 output.mkdir(parents=True,exist_ok=True)
 reports=[];payloads={}
 for key in keys:
  selected=SELECTION[key]
  rows=[active[k] for k in selected]
  hashes={r["source_png_sha256"] for r in rows}
  targets={r["source_dds_path"] for r in rows}
  if len(hashes)!=1 or len(targets)!=1:raise ValueError(f"MIXED_SOURCE_OR_TARGET:{key}")
  target=next(iter(targets))
  if not target.startswith("textures/load/") or not target.endswith(".dds") or ".." in Path(target).parts:
   raise ValueError("BAD_TARGET")
  imgs=list(hdroot.glob(key+"_*.png"))
  found=[p for p in imgs if sha_path(p)==next(iter(hashes))]
  if len(found)!=1:raise ValueError(f"NO_UNAMBIGUOUS_PINNED_HD:{key} matches={len(found)}")
  src=found[0];source=Image.open(src).convert("RGBA")
  groups=alpha_row_groups(source)
  if len(groups)!=len(selected):raise ValueError(f"TEXT_ONLY_RUNS_REQUIRED:{key} groups={groups}")
  row_pairs=[]
  for r in rows:
   x1,y1,x2,y2=r["bbox_xyxy"]
   if not (0<=x1<x2<=source.width and 0<=y1<y2<=source.height):raise ValueError("BAD_ROI_COORDS")
   matched=[g for g in groups if y1<=g[0] and g[1]<=y2]
   if len(matched)!=1:raise ValueError(f"NON_UNIQUE_ROW_GROUP:{r['id']} {groups}")
   row_pairs.append((r,matched[0]))
  if len(set(g for _,g in row_pairs))!=len(selected):raise ValueError("DUPLICATED_ROW_GROUP")
  out=source.copy();details=[];allowed=[]
  for r,g in row_pairs:
   box=exact_box(source,g)
   bx1,by1,bx2,by2=box
   rx1,ry1,rx2,ry2=r["bbox_xyxy"]
   if bx1<rx1 or by1<ry1 or bx2>rx2 or by2>ry2:raise ValueError(f"SOURCE_GLYPH_OUTSIDE_APPROVED_ROI:{r['id']} {box}")
   original_part=source.crop(box)
   if original_part.getchannel("A").getbbox() is None:raise ValueError("NO_ORIGINAL_GLYPH")
   matches=[]
   for lane in ("A","B"):
    for suffix in ("_source_k.png","_k.png"):
     f=root/"candidate_outputs"/lane/(r["id"]+suffix)
     if f.is_file():matches.append(f)
   if len(matches)!=1:raise ValueError(f"CANDIDATE_UNAVAILABLE_OR_AMBIGUOUS:{r['id']}:{len(matches)}")
   img_path=matches[0]
   with Image.open(img_path) as im:
    cand=im.convert("RGBA")
   # Crop visible ink; ImageGen often leaves low-alpha ghost halos.
   raw_ab=cand.getchannel("A").getbbox()
   ab=cand.getchannel("A").point(lambda a:255 if a>=16 else 0).getbbox()
   if not ab:raise ValueError("CANDIDATE_EMPTY_VISIBLE_INK")
   touches=(raw_ab[0]==0 or raw_ab[1]==0 or raw_ab[2]==cand.width or raw_ab[3]==cand.height)
   pad=4
   ab=(max(0,ab[0]-pad),max(0,ab[1]-pad),min(cand.width,ab[2]+pad),min(cand.height,ab[3]+pad))
   letters=cand.crop(ab)
   maxw=bx2-bx1; maxh=by2-by1
   scale=min(maxw/letters.width,maxh/letters.height)
   nw=max(1,min(maxw,int(letters.width*scale)));nh=max(1,min(maxh,int(letters.height*scale)))
   resized=letters.resize((nw,nh),Image.Resampling.LANCZOS)
   px=bx1+(maxw-nw)//2;py=by1+(maxh-nh)//2
   # clear only text's isolated row group, not source art in other rows
   # Remove old glyph RGB even in fully transparent texels to prevent edge bleed.
   for y in range(g[0],g[1]):
    for x in range(bx1,bx2):
     out.putpixel((x,y),(0,0,0,0))
   out.alpha_composite(resized,(px,py))
   allowed.append(box)
   details.append(dict(roi_id=r["id"],english=r["english"],korean=r["korean"],roi=r["bbox_xyxy"],
       original_ink_box=box,row_span=list(g),candidate=str(img_path.relative_to(root)),
       candidate_sha256=sha_path(img_path),candidate_size=cand.size,candidate_alpha_box=ab,candidate_raw_alpha_box=raw_ab,
       candidate_border_touch=touches,composed_ink_box=[px,py,px+nw,py+nh],scale=scale))
  if np is not None:
   a=np.asarray(source);b=np.asarray(out)
   changed=np.any(a!=b,axis=2)
   mask=np.zeros((source.height,source.width),dtype=bool)
   for x1,y1,x2,y2 in allowed:mask[y1:y2,x1:x2]=True
   outside=int((changed&(~mask)).sum()); changed_count=int(changed.sum())
  else:
   mask=Image.new("L",source.size,0)
   for x1,y1,x2,y2 in allowed:
    mask.paste(255,(x1,y1,x2,y2))
   before=ImageChops.difference(source,out).convert("RGBA")
   outside=0;changed_count=None
   for yy in range(source.height):
    for xx in range(source.width):
     if not mask.getpixel((xx,yy)) and any(before.getpixel((xx,yy))):outside+=1
  if outside:raise ValueError(f"PIXELS_CHANGED_OUTSIDE_TEXT_ONLY_GLYPH_ROWS:{outside}")
  orientation="FLIPY" if "_FLIPY" in src.name else "NORMAL"
  data=encode_rgba_dds(out,orientation)
  with Image.open(io.BytesIO(data)) as dd:
   decoded=dd.convert("RGBA")
   expected=out if orientation=="NORMAL" else out.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
   if ImageChops.difference(expected,decoded).getbbox():raise AssertionError("DDS_ROUNDTRIP_FAILED")
  outdir=output/key
  outdir.mkdir(parents=True,exist_ok=True)
  png_path=outdir/"IMAGEGEN_COMPOSED_READABLE_TEST_ONLY.png"
  dds_path=outdir/"IMAGEGEN_COMPOSED_TEST_ONLY.dds"
  if png_path.exists() or dds_path.exists():raise ValueError("REFUSE_OVERWRITE")
  png_tmp=io.BytesIO();out.save(png_tmp,format="PNG"); png_path.write_bytes(png_tmp.getvalue());dds_path.write_bytes(data)
  report={"status":"TEST_ONLY_PIXEL_GUARDS_PASS_VISUAL_QA_REQUIRED","runtime_validation":"UNTESTED","source":src.name,
   "source_sha256":next(iter(hashes)),"target_path":target,"orientation":orientation,"source_dimensions":source.size,
   "output_dds_sha256":sha(data),"output_png_sha256":sha(png_tmp.getvalue()),
   "changed_pixel_count":changed_count,"outside_text_row_changes":outside,"details":details,
   "warnings":["candidate source QA unverified","source row bands are text-only but final sprite consumer not game verified",
       "original DXT/mip may not be preserved; uncompressed mip1 test only"]}
  (outdir/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
  reports.append(report);payloads[target]=data
  print(json.dumps({"source":key,"status":report["status"],"dds_sha256":report["output_dds_sha256"],"changed":changed_count,
      "outside":outside,"candidate_border_touch":sum(d["candidate_border_touch"] for d in details)},ensure_ascii=False))
 zip_path=output/"OUTRUN_AB_IMAGEGEN_ALPHA_COMPOSITE_3DDS_TEST_ONLY.zip"
 if zip_path.exists():raise ValueError("REFUSE_OVERWRITE_ZIP")
 with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
  for r in reports:
   z.writestr(r["target_path"],payloads[r["target_path"]])
   z.writestr("qa_receipts/"+r["source"]+".json",json.dumps(r,ensure_ascii=False,indent=2))
  z.writestr("TEST_ONLY_MANIFEST.json",json.dumps({"status":"NOT_RUNTIME_APPROVED","dds_count":len(reports),
    "sources":[r["source"] for r in reports],"no_game_files_written":True},ensure_ascii=False,indent=2))
 with zipfile.ZipFile(zip_path) as z:
  assert z.testzip() is None
 summary={"status":"TEST_ONLY_STATIC_PIXEL_GUARDS_PASS","count_dds":len(reports),"count_roi":sum(len(r["details"]) for r in reports),
  "zip_path":str(zip_path),"zip_sha256":sha_path(zip_path),"zip_bytes":zip_path.stat().st_size}
 (output/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
 print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--source",action="append",choices=sorted(SELECTION))
 p.add_argument("--root",default=str(ROOT))
 p.add_argument("--hdroot",default=str(HD))
 p.add_argument("--output",default=str(DEFAULT_OUT))
 a=p.parse_args()
 run(a.root,a.hdroot,a.output,a.source or sorted(SELECTION))
