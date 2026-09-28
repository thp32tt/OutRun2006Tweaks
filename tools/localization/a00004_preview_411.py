#!/usr/bin/env python3
from pathlib import Path
import json,struct
from PIL import Image,ImageChops,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds"
CUR=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds"
C85=ROOT/"localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"
B91=ROOT/"localization/graphics/role_B/20260928-0920-B91/B91_RGBA_REWORK_ACTIONS.json"
OUT=ROOT/"localization/graphics/role_A/20260928-A00004"; OUT.mkdir(parents=True,exist_ok=True)
def load(p):
 b=p.read_bytes(); h,w=struct.unpack_from("<II",b,12)
 return Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def mask(size,boxes):
 m=Image.new("L",size,0); d=ImageDraw.Draw(m)
 for b in boxes:d.rectangle(tuple(b),fill=255)
 return m
src,cur=load(SRC),load(CUR); after=cur.copy()
c=json.loads(C85.read_text("utf-8")); rows=next(x for x in c["assets"] if x["asset"]=="411827E")["rows"]
b=json.loads(B91.read_text("utf-8")); acts={x["key"]:x for x in next(a for a in b["assets"] if a["asset"]=="411827E")["rows"]}
r=next(x for x in rows if x["key"]=="seconds"); x0,y0,x1,y1=r["localized_bbox"]; t=acts["seconds"]["new_localized_bbox"]; tx0,ty0,tx1,ty1=t
patch=cur.crop((x0,y0,x1+1,y1+1)); after.paste((0,0,0,0),(x0,y0,x1+1,y1+1))
patch=patch.resize((tx1-tx0+1,ty1-ty0+1),Image.Resampling.LANCZOS); after.alpha_composite(patch,(tx0,ty0))
for key in ("tuned","normal","random"):
 r=next(x for x in rows if x["key"]==key)
 repair=ImageChops.multiply(mask(after.size,[r["sprite_cell"]]),ImageOps.invert(mask(after.size,[r["original_bbox"]])))
 after=Image.composite(src,after,repair)
tiles=[]
for key in ("seconds","tuned","normal","random"):
 r=next(x for x in rows if x["key"]==key); x0,y0,x1,y1=r["sprite_cell"]; pad=6
 x0=max(0,x0-pad);y0=max(0,y0-pad);x1=min(src.width-1,x1+pad);y1=min(src.height-1,y1+pad)
 ims=[src.crop((x0,y0,x1+1,y1+1)),cur.crop((x0,y0,x1+1,y1+1)),after.crop((x0,y0,x1+1,y1+1))]
 ims.append(ImageChops.difference(ims[0],ims[2]))
 panels=[]
 for im in ims:
  bg=Image.new("RGBA",im.size,(255,255,255,255)); bg.alpha_composite(im)
  panels.append(bg.resize((bg.width*3,bg.height*3),Image.Resampling.NEAREST).convert("RGB"))
 tile=Image.new("RGB",(sum(p.width for p in panels),max(p.height for p in panels)+30),"white")
 ImageDraw.Draw(tile).text((4,4),f"{key} | SOURCE | BEFORE | PROPOSED | DIFF",fill="black")
 xx=0
 for p in panels:tile.paste(p,(xx,30));xx+=p.width
 tiles.append(tile)
W=max(t.width for t in tiles);H=sum(t.height for t in tiles);sheet=Image.new("RGB",(W,H),"white");yy=0
for t in tiles:sheet.paste(t,(0,yy));yy+=t.height
sheet.save(OUT/"A00004_411_PROPOSED_QA.png")
(OUT/"A00004_411_PROPOSED_PREVIEW.json").write_text(json.dumps({"task_id":"LOCALIZATION-LOCALIZATION_A-00004","asset":"411827E","candidate_written":False,"proposal":{"seconds":"minimal resize to B91 contained bbox","tuned_normal_random":"restore canonical source only outside original bbox"},"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n","utf-8")
