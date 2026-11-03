#!/usr/bin/env python3
"""Produce NEW native Korean DDS TEST_ONLY candidates on GitHub, never N100.

Uses existing SHA-pinned GitHub HD DDS and 954 reviewed translation crosswalk.
Rejects protected/opaque art and unsafe DDS; no game install/RELEASE approval.
"""
import argparse, collections, csv, hashlib, io, json, re, struct, zipfile
from pathlib import Path, PurePosixPath
from PIL import Image, ImageChops, ImageDraw, ImageFont

CROSS="localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv"
SRC="localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"
BGRA=(0xff0000,0xff00,0xff,0xff000000)
RGBA=(0xff,0xff00,0xff0000,0xff000000)
FLIP={
"D6DC1380":"NORMAL","19CEDB9":"FLIPY","FF2462BB":"FLIPY",
"568D3696":"FLIPY","FA7BBB13":"FLIPY","39229D64":"FLIPY",
"A064FDFC":"FLIPY","C4A2937B":"FLIPY","48DEBE77":"FLIPY",
"2DA43E41":"FLIPY","411827E":"FLIPY","571E78F3":"FLIPY",
"62BEBF33":"FLIPY","C075FB49":"FLIPY","E3FD08BE":"FLIPY",
"FD90AA9":"FLIPY","9F060EC1":"FLIPY"
}
FONTS=[
"/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
"/usr/share/fonts/truetype/nanum/NanumSquareB.ttf",
"/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]
MAX_FILE=70*1024*1024

def digest(b):return hashlib.sha256(b).hexdigest()
def pinned_file(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def safe_texture(s):
 p=PurePosixPath(s)
 return (isinstance(s,str) and s.startswith("textures/load/") and "\\" not in s and
         ":" not in s and not p.is_absolute() and ".." not in p.parts and
         len(p.parts)==4 and p.suffix.lower()==".dds" and
         all(re.fullmatch("[A-Za-z0-9_.-]+",x) for x in p.parts))
def read_rows(path):
 with path.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
 if len(rows)!=954:raise ValueError("ACTIVE_ROI_COUNT_CHANGED")
 groups=collections.defaultdict(list);ids=set()
 for r in rows:
  path=r["source_dds_path"]
  if not safe_texture(path):raise ValueError("UNSAFE_TEXTURE_PATH")
  rid=r["roi_id"]
  if rid in ids:raise ValueError("DUPLICATE_ROW_ID")
  ids.add(rid)
  if not re.fullmatch("[0-9a-f]{64}",r["source_dds_sha256"]):raise ValueError("SOURCE_SHA_MISSING")
  b=json.loads(r["bbox_xyxy"])
  if len(b)!=4 or any(type(x) is not int for x in b):raise ValueError("INVALID_BBOX")
  groups[path].append({"id":rid,"korean":r["korean"],"english":r["english"],
   "sha":r["source_dds_sha256"],"box":b})
 return groups

def inspect_dds(data):
 if len(data)<128 or data[:4]!=b"DDS " or struct.unpack_from("<I",data,4)[0]!=124:raise ValueError("DDS_HEADER_INVALID")
 h,w=struct.unpack_from("<II",data,12)
 mip=struct.unpack_from("<I",data,28)[0]
 pfsize,flags=struct.unpack_from("<II",data,76)
 bpp=struct.unpack_from("<I",data,88)[0]
 masks=struct.unpack_from("<IIII",data,92)
 if not 0<w<=4096 or not 0<h<=4096:raise ValueError("DDS_SIZE_INVALID")
 if (pfsize,flags,bpp)!=(32,65,32) or masks not in (BGRA,RGBA) or mip!=1:raise ValueError("DDS_SOURCE_FORMAT_NOT_NATIVE_SINGLE_MIP")
 if data[84:88]!=b"\x00"*4 or len(data)!=128+w*h*4:raise ValueError("DDS_LENGTH_INVALID")
 return w,h,"BGRA" if masks==BGRA else "RGBA"

def font_file():
 for p in FONTS:
  if Path(p).is_file():return p
 raise ValueError("HANGUL_FONT_MISSING")

def lines(s):
 return [v.strip() for v in s.split(" / ")] if " / " in s else s.splitlines() or [s]

def glyph(phrase,wh,f,background):
 w,h=wh;txt=lines(phrase)
 if not txt or len(txt)>3 or any(not a for a in txt):raise ValueError("TRANSLATION_LINES_INVALID")
 mg=max(1,min(w,h)//20)
 # White or golden, derived from original text ink.
 pixels=list(background.getdata())
 solids=[p for p in pixels if p[3]>=192]
 gold=sum(p[0]>=145 and p[1]>=95 and p[2]<=165 and p[0]>=p[2]*1.35 for p in solids)
 color=(255,210,40,255) if solids and gold/len(solids)>=0.035 else (246,249,255,255)
 out=Image.new("RGBA",(w,h))
 draw=ImageDraw.Draw(out)
 for px in range(max(6,min(h//len(txt),w)),4,-1):
  face=ImageFont.truetype(f,px)
  stroke=max(1,px//18)
  bounds=[draw.textbbox((0,0),s,font=face,stroke_width=stroke) for s in txt]
  line_h=max(x[3]-x[1] for x in bounds)
  spacing=max(1,px//8)
  total=line_h*len(txt)+spacing*(len(txt)-1)
  if max(x[2]-x[0] for x in bounds)<=w-2*mg and total<=h-2*mg:
   for i,s in enumerate(txt):
    draw.text((w//2,(h-total)//2+i*(line_h+spacing)+line_h//2),s,
     font=face,anchor="mm",fill=color,stroke_width=stroke,
     stroke_fill=(13,32,74,245))
   if out.getchannel("A").getbbox():return out
 raise ValueError("GLYPH_CANNOT_FIT")

def changed_outside(a,b,boxes):
 permitted=Image.new("L",a.size,0);dr=ImageDraw.Draw(permitted)
 for x0,y0,x1,y1 in boxes:dr.rectangle((x0,y0,x1-1,y1-1),fill=255)
 layers=ImageChops.difference(a,b).split()
 changed=layers[0]
 for layer in layers[1:]:changed=ImageChops.lighter(changed,layer)
 return ImageChops.darker(changed,ImageChops.invert(permitted)).getbbox() is not None

def produce(original,roi,orientation,font):
 w,h,mode=inspect_dds(original)
 with Image.open(io.BytesIO(original)) as im:
  native=im.convert("RGBA")
 if native.size!=(w,h) or native.tobytes("raw",mode)!=original[128:]:raise ValueError("SOURCE_BYTES_MISMATCH")
 readable=native.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if orientation=="FLIPY" else native
 out=readable.copy();approved=[];painted=[];held=[]
 for r in sorted(roi,key=lambda x:((x["box"][2]-x["box"][0])*(x["box"][3]-x["box"][1]),x["id"])):
  x0,y0,x1,y1=r["box"]
  if not 0<=x0<x1<=w or not 0<=y0<y1<=h:held.append([r["id"],"OUT_OF_BOUNDS"]);continue
  if any(x0<b[2] and b[0]<x1 and y0<b[3] and b[1]<y1 for b in approved):
   held.append([r["id"],"OVERLAPPING_ROI"]);continue
  box=(x0,y0,x1,y1)
  area=readable.crop(box)
  opacity=sum(area.getchannel("A").histogram()[16:])/(area.width*area.height)
  if opacity>0.9:held.append([r["id"],"OPAQUE_PROTECTED_ART_HOLD"]);continue
  if ("\n" in r["english"] or " / " in r["english"]) and len(lines(r["korean"]))<2:
   held.append([r["id"],"TWO_LINE_LAYOUT_HOLD"]);continue
  try:g=glyph(r["korean"],area.size,font,area)
  except ValueError as e:held.append([r["id"],str(e)]);continue
  out.paste((0,0,0,0),box);out.alpha_composite(g,(x0,y0))
  approved.append(box);painted.append([r["id"],r["english"],r["korean"],list(box)])
 if not painted:return None,out,painted,held
 if changed_outside(readable,out,approved):raise ValueError("OUTSIDE_ROI_PIXEL_CHANGE")
 n=out.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if orientation=="FLIPY" else out
 result=original[:128]+n.tobytes("raw",mode)
 with Image.open(io.BytesIO(result)) as verify:
  if verify.convert("RGBA").tobytes()!=n.tobytes():raise ValueError("DDS_REDECODE_MISMATCH")
 return result,out,painted,held

def add_zip(z,name,body):
 info=zipfile.ZipInfo(name,(1980,1,1,0,0,0))
 info.compress_type=zipfile.ZIP_DEFLATED
 info.external_attr=0o100644<<16
 z.writestr(info,body,compresslevel=5)

def run(repo,out,max_sources=18):
 if not 1<=max_sources<=18:raise ValueError("INVALID_SOURCE_LIMIT")
 repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 groups=read_rows(repo/CROSS)
 eligible=[(target,repo/SRC/target,rows) for target,rows in sorted(groups.items())
           if (repo/SRC/target).is_file() and not (repo/SRC/target).is_symlink()]
 summary={"schema":"outrun-github-native-new-production-v1",
  "active_rows":954,"github_eligible_sources":len(eligible),
  "github_eligible_rows":sum(len(rows) for _,_,rows in eligible),
  "release_approved":False,"visual_qa":"REVIEW_REQUIRED","runtime_validation":"UNTESTED",
  "A_B_GitHub_png_available":0,"generated":[],"held":[]}
 zipname="OUTRUN_KOREAN_NEW_NATIVE_TEST_ONLY.zip"
 with zipfile.ZipFile(out/zipname,"w") as z:
  for target,file,rows in eligible[:max_sources]:
   shas={r["sha"] for r in rows}
   fid=PurePosixPath(target).name.split("_")[0]
   reason=None
   if len(shas)!=1:reason="DDS_SHA_CONFLICT"
   elif pinned_file(file)!=next(iter(shas)):reason="DDS_SOURCE_SHA_MISMATCH"
   elif fid not in FLIP:reason="UNKNOWN_ORIENTATION"
   elif file.stat().st_size>MAX_FILE:reason="SOURCE_TOO_LARGE"
   if reason:
    summary["held"].append({"source":target,"rows":len(rows),"reason":reason});continue
   try:
    binary,png,painted,held=produce(file.read_bytes(),rows,FLIP[fid],font_file())
    if not painted:
     summary["held"].append({"source":target,"rows":len(rows),"reason":"ALL_ROIS_HELD","details":held[:15]})
     continue
    add_zip(z,target,binary)
    png.thumbnail((1200,1200),Image.Resampling.LANCZOS)
    png.save(out/("PREVIEW_"+fid+".png"))
    summary["generated"].append({"target":target,"dds_sha256":digest(binary),
     "source_sha256":next(iter(shas)),"orientation":FLIP[fid],
     "painted_rows":painted,"held_rows":held})
   except (ValueError,OSError,OverflowError) as e:
    summary["held"].append({"source":target,"rows":len(rows),"reason":str(e)})
  add_zip(z,"TEST_ONLY_MANIFEST.json",json.dumps({
   "status":"TEST_ONLY_NOT_RUNTIME_APPROVED","release_approved":False,
   "runtime_validation":"UNTESTED","files":[{"path":x["target"],"sha256":x["dds_sha256"]}
   for x in summary["generated"]]},ensure_ascii=False,sort_keys=True,indent=2).encode())
 summary["generated_dds"]=len(summary["generated"])
 summary["generated_rows"]=sum(len(v["painted_rows"]) for v in summary["generated"])
 summary["held_rows"]=sum(len(v["held_rows"]) for v in summary["generated"])+sum(v["rows"] for v in summary["held"])
 summary["zip_sha256"]=pinned_file(out/zipname)
 (out/"production_report.json").write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
 print(json.dumps({k:summary[k] for k in
  ("github_eligible_sources","github_eligible_rows","generated_dds","generated_rows","held_rows","zip_sha256")},ensure_ascii=False))
 if not summary["generated_dds"]:raise SystemExit("NO_NEW_DDS_PRODUCED")

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--repo-root",default=".")
 p.add_argument("--out",default="/tmp/gh-native")
 p.add_argument("--max-sources",type=int,default=18)
 a=p.parse_args()
 run(a.repo_root,a.out,a.max_sources)
