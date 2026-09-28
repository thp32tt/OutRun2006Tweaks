#!/usr/bin/env python3
from pathlib import Path
import json, struct
from PIL import Image,ImageChops,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds"
CUR=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds"
C85=ROOT/"localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"
OUT=ROOT/"localization/graphics/role_A/20260928-A00004"
OUT.mkdir(parents=True,exist_ok=True)
def load(p):
 b=p.read_bytes()
 assert b[:4]==b"DDS " and b[84:88]==b"\0\0\0\0"
 h,w=struct.unpack_from("<II",b,12)
 assert struct.unpack_from("<I",b,88)[0]==32
 im=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
 return im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src,cur=load(SRC),load(CUR)
doc=json.loads(C85.read_text("utf-8")); asset=next(x for x in doc["assets"] if x["asset"]=="411827E")
keys=["automatic","seconds","engine","tuned","normal","random","recommendation"]
tiles=[]
for r in asset["rows"]:
 if r["key"] not in keys: continue
 x0,y0,x1,y1=r["sprite_cell"]; pad=6
 x0=max(0,x0-pad); y0=max(0,y0-pad); x1=min(src.width-1,x1+pad); y1=min(src.height-1,y1+pad)
 a=src.crop((x0,y0,x1+1,y1+1)); b=cur.crop((x0,y0,x1+1,y1+1))
 # white backgrounds make alpha/residue visible
 aw=Image.new("RGBA",a.size,(255,255,255,255)); aw.alpha_composite(a)
 bw=Image.new("RGBA",b.size,(255,255,255,255)); bw.alpha_composite(b)
 d=ImageChops.difference(a,b)
 dw=Image.new("RGBA",d.size,(255,255,255,255)); dw.alpha_composite(d)
 scale=2
 aw=aw.resize((aw.width*scale,aw.height*scale),Image.Resampling.NEAREST)
 bw=bw.resize((bw.width*scale,bw.height*scale),Image.Resampling.NEAREST)
 dw=dw.resize((dw.width*scale,dw.height*scale),Image.Resampling.NEAREST)
 tile=Image.new("RGB",(aw.width+bw.width+dw.width,max(aw.height,bw.height,dw.height)+28),"white")
 dr=ImageDraw.Draw(tile); dr.text((4,4),f"{r['key']} | SOURCE | CURRENT | DIFF | {r['containment']}",fill="black")
 yy=28; tile.paste(aw.convert("RGB"),(0,yy)); tile.paste(bw.convert("RGB"),(aw.width,yy)); tile.paste(dw.convert("RGB"),(aw.width+bw.width,yy))
 tiles.append(tile)
W=max(t.width for t in tiles); H=sum(t.height for t in tiles)
sheet=Image.new("RGB",(W,H),"white"); yy=0
for t in tiles: sheet.paste(t,(0,yy)); yy+=t.height
sheet.save(OUT/"A00004_411_SOURCE_CURRENT_DIFF.png")
(OUT/"A00004_411_PREVIEW.json").write_text(json.dumps({
 "task_id":"LOCALIZATION-LOCALIZATION_A-00004","asset":"411827E","mode":"source-current-diff-preview",
 "source":"canonical HD source","candidate":"current canonical hd_candidate","runtime_validation":"UNTESTED"
},indent=2)+"\n","utf-8")
