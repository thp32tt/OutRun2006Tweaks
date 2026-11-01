#!/usr/bin/env python3
"""Offline Korean UI fallback, TEST_ONLY.

Existing reviewed translation + SHA pinned full-HD ROI -> deterministic Hangul,
no OCR/ImageGen/paid API. Never edits originals, A/B queue, or approval state.
Supports uncompressed single-mip 32-bit RGBA/BGRA DDS only.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, struct, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE=Path("/home/chatgpt-runner2/work")
MANIFEST=BASE/"image-src/text_roi_batches/production_manifest.json"
SOURCE=BASE/"c_salvage_text_roi/c_original_hd_crop_only/hd_original_108_verified"
DDSROOT=BASE/"c_salvage_text_roi/source_full_20261012"
OUTPUT=BASE/"image-src/text_roi_batches/offline_test_only"
FONTS=(
 "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
 "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
 "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
 "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf",
)
FORMAT={
 (255,65280,16711680,4278190080):[0,1,2,3],
 (16711680,65280,255,4278190080):[2,1,0,3],
}
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()
def font_path():
 for s in FONTS:
  if Path(s).is_file():return s
 raise RuntimeError("KOREAN_FONT_MISSING (install Noto Sans CJK or Nanum Gothic)")
def native_from_dds(dds, readable, orientation):
 blob=dds.read_bytes()
 if blob[:4]!=b"DDS " or len(blob)<128 or struct.unpack_from("<I",blob,4)[0]!=124:
  raise ValueError("DDS_INVALID_HEADER")
 h,w=struct.unpack_from("<II",blob,12)
 mip=struct.unpack_from("<I",blob,28)[0]
 pfsize,flags=struct.unpack_from("<II",blob,76)
 bit_count=struct.unpack_from("<I",blob,88)[0]
 masks=struct.unpack_from("<IIII",blob,92)
 if (w,h)!=readable.size or mip not in (0,1) or pfsize!=32 or not flags&0x40 or blob[84:88]!=b"\0"*4 or bit_count!=32 or masks not in FORMAT or len(blob)!=128+w*h*4:
  raise ValueError("DDS_UNSUPPORTED_SINGLE_MIP_RGBA")
 raw=np.frombuffer(blob,dtype=np.uint8,offset=128).reshape((h,w,4))
 base=raw[:,:,FORMAT[masks]]
 expected=np.asarray(readable)
 if orientation=="FLIPY":
  expected=expected[::-1,:,:]
 elif orientation!="NORMAL":
  raise ValueError("ORIENTATION_UNKNOWN")
 if not np.array_equal(base,expected):
  raise ValueError("DDS_ORIGINAL_PNG_PIXEL_MISMATCH")
 return blob,masks
def korean_lines(s):
 # reviewed slash marks preserve intentionally multi-line original labels
 if " / " in s:return [p.strip() for p in s.split(" / ")]
 return s.splitlines() or [s]
def make_glyph(text, bw, bh, fontfile, reference=None):
 color=(246,249,255,255)
 if reference is not None:
  pixels=reference.reshape(-1,4)
  solid=pixels[:,3]>=192
  if int(np.count_nonzero(solid))>0:
   rgb=pixels[solid,:3].astype(np.int32)
   gold=(rgb[:,0]>=145)&(rgb[:,1]>=95)&(rgb[:,2]<=165)&(rgb[:,0]>=rgb[:,2]*1.35)
   if np.count_nonzero(gold)/len(rgb)>=0.035:
    color=(255,210,40,255)
 lines=korean_lines(text)
 margin=max(2,min(bw,bh)//18)
 maxfont=max(6,int(min(bh/max(1,len(lines))*0.88,bw/max(1,max(map(len,lines)))*1.7)))
 best=None
 for size in range(maxfont,4,-1):
  face=ImageFont.truetype(fontfile,size=size)
  stroke=max(1,round(size/18))
  scratch=Image.new("RGBA",(1,1))
  d=ImageDraw.Draw(scratch)
  widths=[]; heights=[]
  for line in lines:
   box=d.textbbox((0,0),line,font=face,stroke_width=stroke)
   widths.append(box[2]-box[0]);heights.append(box[3]-box[1])
  line_h=max(heights)
  if max(widths)<=bw-2*margin and len(lines)*line_h+max(0,len(lines)-1)*max(1,size//8)<=bh-2*margin:
   best=(face,stroke,line_h,widths);break
 if best is None:raise ValueError("TRANSLATION_CANNOT_FIT")
 face,stroke,line_h,widths=best
 letter=Image.new("RGBA",(bw,bh),(0,0,0,0))
 painter=ImageDraw.Draw(letter)
 spacing=max(1,face.size//8)
 total=len(lines)*line_h+(len(lines)-1)*spacing
 for n,line in enumerate(lines):
  # textbbox may have positive ascent offset; anchor=mm centers accurately
  cx=bw//2
  cy=(bh-total)//2+n*(line_h+spacing)+line_h//2
  painter.text((cx,cy),line,font=face,anchor="mm",
       fill=color,stroke_width=stroke,stroke_fill=(13,32,74,245))
 if not letter.getchannel("A").getbbox():raise ValueError("RENDER_EMPTY")
 return letter
def find_dds(q, target_sha, root):
 # No fuzzy filename matching for the canonical DDS.
 options=list(root.glob(q+"_*.dds"))
 matches=[p for p in options if target_sha[:12] in p.name and sha(p)==target_sha]
 if len(matches)!=1:raise ValueError("DDS_PIN_NOT_LOCATED:"+str(len(matches)))
 return matches[0]
def source_rows(manifest, source_sha, width, height):
 rows=[r for r in manifest["items"] if r.get("source_png_sha256")==source_sha
       and r.get("status")=="ROI_APPROVED_FOR_IMAGEGEN"
       and r.get("english") and r.get("korean")]
 unique={}
 for r in rows:
  b=r.get("bbox_xyxy")
  if not isinstance(b,list) or len(b)!=4 or not all(type(v)==int for v in b):
   continue
  x0,y0,x1,y1=b
  if not(0<=x0<x1<=width and 0<=y0<y1<=height):
   continue
  k=tuple(b)
  if k in unique and unique[k]["korean"]!=r["korean"]:
   raise ValueError("CONFLICTING_TRANSLATION_SAME_BOX")
  unique[k]=r
 return sorted(unique.values(),key=lambda r:((r["bbox_xyxy"][2]-r["bbox_xyxy"][0])*(r["bbox_xyxy"][3]-r["bbox_xyxy"][1]),r["bbox_xyxy"][1]))
def do_run(a):
 root=Path(a.source_root);manifest=json.loads(Path(a.manifest).read_text(encoding="utf-8"))
 src=root/a.source_name
 if Path(a.source_name).name!=a.source_name:raise ValueError("SOURCE_NAME_NOT_BASENAME")
 if not src.is_file() or src.is_symlink():raise ValueError("ORIGINAL_NOT_FOUND")
 original_sha=sha(src)
 with Image.open(src) as im:
  if im.format!="PNG" or im.mode!="RGBA":raise ValueError("ORIGINAL_NOT_RGBA_PNG")
  source=im.copy()
 rows=source_rows(manifest,original_sha,*source.size)
 if not rows:raise ValueError("NO_APPROVED_ROWS_FOR_SOURCE")
 if len(rows)>a.max_rows:
  rows=rows[:a.max_rows]
 pinned={r.get("source_dds_sha256") for r in rows}
 if len(pinned)!=1:raise ValueError("MIXED_DDS_SHA_SAME_SOURCE")
 target_sha=pinned.pop()
 q=a.source_name[:4]
 dds=find_dds(q,target_sha,Path(a.dds_root))
 flip=("FLIPY" if "_FLIPY" in a.source_name else "NORMAL")
 header,format_masks=native_from_dds(dds,source,flip)
 before=np.asarray(source).copy()
 final=source.copy()
 details=[]
 f=font_path()
 regions=[]
 for r in rows:
  b=r["bbox_xyxy"];box=tuple(b)
  # Avoid changing any pixel outside the verified ROI. Regions overlapping
  # each other cannot be safely composed independently.
  if any(b[0]<c[2] and c[0]<b[2] and b[1]<c[3] and c[1]<b[3] for c in regions):
   continue  # keep enclosing/overlapping labels for separate review
  regions.append(b)
  x0,y0,x1,y1=b
  piece=before[y0:y1,x0:x1]
  alpha_fraction=float(np.count_nonzero(piece[:,:,3]>=16))/piece[:,:,3].size
  if alpha_fraction>a.max_opaque_fraction:
   raise ValueError("SOURCE_ROI_ART_BACKGROUND_HOLD:"+r["english"]+":"+str(round(alpha_fraction,3)))
  # Low-fidelity fallback: remove all pixels confined to the approved text ROI.
  final.paste((0,0,0,0),box)
  letter=make_glyph(r["korean"],x1-x0,y1-y0,f,piece)
  final.alpha_composite(letter,(x0,y0))
  details.append({"id":r["id"],"english":r["english"],"korean":r["korean"],"bbox":b,"roi_original_opaque_fraction":round(alpha_fraction,4)})
 if not details:raise ValueError("NO_NON_OVERLAPPING_RENDERABLE_ROWS")
 aft=np.asarray(final)
 permitted=np.zeros((source.height,source.width),dtype=bool)
 for b in regions:permitted[b[1]:b[3],b[0]:b[2]]=True
 changed=np.any(before!=aft,axis=2)
 changes_outside=int(np.count_nonzero(changed&~permitted))
 if changes_outside:raise AssertionError("OUTSIDE_REGION_PIXEL_CHANGED")
 raw=aft if flip=="NORMAL" else aft[::-1,:,:]
 raw=raw[:,:,FORMAT[format_masks]]
 output=header[:128]+np.ascontiguousarray(raw).tobytes()
 if not a.execute:
  print(json.dumps({"status":"DRY_RUN","source":a.source_name,"source_sha":original_sha,
   "dds_sha":target_sha,"count":len(details),"change_pixels":int(changed.sum()),
   "outside_change_pixels":changes_outside,"items":details},ensure_ascii=False))
  return
 dest=Path(a.output_root)/(src.stem+"_"+original_sha[:12])
 if dest.exists():raise ValueError("OUTPUT_EXISTS_REFUSE_OVERWRITE:"+str(dest))
 dest.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=dest.parent,prefix=".offline-korean-") as tmp:
  tmp=Path(tmp)
  readable=tmp/"KOREAN_READABLE_TEST_ONLY.png"
  native=tmp/"KOREAN_NATIVE_TEST_ONLY.dds"
  final.save(readable,format="PNG")
  native.write_bytes(output)
  with Image.open(native) as check:
   original_native=aft if flip=="NORMAL" else aft[::-1,:,:]
   if not np.array_equal(np.asarray(check.convert("RGBA")),original_native):
    raise AssertionError("DDS_ROUNDTRIP_MISMATCH")
  report={"status":"OFFLINE_KOREAN_DDS_TEST_ONLY","runtime_validation":"UNTESTED",
   "source_png":a.source_name,"source_png_sha256":original_sha,
   "source_dds":dds.name,"source_dds_sha256":target_sha,"orientation":flip,
   "dds_pixel_masks":list(format_masks),"items":details,"items_count":len(details),
   "original_pixels_changed_outside_roi":changes_outside,
   "readable_png_sha256":sha(readable),"test_only_dds_sha256":sha(native),
   "original_files_modified":False,"external_api_used":False,"generated_by":"PIL_DIRECT_HANGUL_FALLBACK_V1",
   "quality_limitations":"Approximate font/stroke; erases full approved ROI including any unprotected art; requires visual QA, C3, user gameplay."}
  (tmp/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  os.replace(tmp,dest)
 print(json.dumps({"output":str(dest),**report},ensure_ascii=False))
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--manifest",default=str(MANIFEST))
 p.add_argument("--source-root",default=str(SOURCE))
 p.add_argument("--dds-root",default=str(DDSROOT))
 p.add_argument("--output-root",default=str(OUTPUT))
 p.add_argument("--source-name",required=True)
 p.add_argument("--max-rows",type=int,default=10)
 p.add_argument("--max-opaque-fraction",type=float,default=0.95)
 p.add_argument("--execute",action="store_true")
 a=p.parse_args()
 if not(0<a.max_rows<=200 and 0<=a.max_opaque_fraction<=1):p.error("invalid limits")
 do_run(a)
if __name__=="__main__":main()