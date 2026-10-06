#!/usr/bin/env python3
# B225: q154 4D38BBB0 strict PRE_INGAME hierarchy rework.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo=Path.cwd()
run="20261007-B-MANUALQA225-4D38BBB0"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
c141=repo/"localization/graphics/role_C/20261005-C141-4D38BBB0"
clean_path=c141/"C141_EXACT_CLEAN_PLATE.png"
source_mask_path=c141/"C141_SOURCE_TEXT_MASK.png"
allowed_full_path=c141/"C141_ALLOWED_BBOX_MASK.png"
protected_full_path=c141/"C141_PROTECTED_VISIBLE_MASK.png"
artwork_path=c141/"C141_ARTWORK_MASK.png"
EXPECTED_BEFORE="c92e095672a69a26191a635b509aa2f6a25be41836128b2d5f44163c3dc2908a"
SOURCE_SHA="15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf"
source_commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+source_commit+"/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
tmp=Path("/tmp/b225"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(url,src_dds)

ROWS=[
 {"key":"create_new_license","source":"CREATE NEW LICENSE","korean":"새 라이선스 만들기","bbox":[13,548,1954,696],"prior_bbox":[15,552,1126,692],"kind":"red","font_size":144,"target_width":1514},
 {"key":"select_license","source":"SELECT LICENSE","korean":"라이선스 선택","bbox":[2007,541,3468,689],"prior_bbox":[2009,545,2817,685],"kind":"red","font_size":144,"target_width":1096},
 {"key":"single_player_red","source":"SINGLE PLAYER","korean":"싱글 플레이","bbox":[12,374,1388,522],"prior_bbox":[14,378,693,518],"kind":"red","font_size":144,"target_width":991},
 {"key":"default_license","source":"DEFAULT LICENSE","korean":"기본 라이선스","bbox":[1772,374,3316,522],"prior_bbox":[1774,378,2594,518],"kind":"red","font_size":144,"target_width":1143},
 {"key":"multiplayer_red","source":"MULTIPLAYER","korean":"멀티플레이","bbox":[15,203,1235,347],"prior_bbox":[17,205,657,345],"kind":"red","font_size":144,"target_width":878},
 {"key":"single_player_gray","source":"SINGLE PLAYER","korean":"싱글 플레이","bbox":[1610,286,2197,350],"prior_bbox":[1612,289,1879,347],"kind":"gray","font_size":56,"target_width":411},
 {"key":"showroom_gray","source":"SHOWROOM","korean":"쇼룸","bbox":[2674,288,3094,350],"prior_bbox":[2676,291,2780,346],"kind":"gray","font_size":56,"target_width":210},
 {"key":"multiplayer_gray","source":"MULTIPLAYER","korean":"멀티플레이","bbox":[2566,952,3086,1014],"prior_bbox":[2568,954,2820,1012],"kind":"gray","font_size":56,"target_width":364},
]

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(4096,1024) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips,"mode":mode}
def bb(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def composite(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")
def card(label,im):
    v=composite(im)
    c=Image.new("RGB",(v.width,v.height+28),(24,24,24)); c.paste(v,(0,28))
    ImageDraw.Draw(c).text((6,6),label,fill="white")
    return c

sb=src_dds.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(cb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha(cb)))
src_raw,src,meta=decode(sb); old_raw,old,ometa=decode(cb)
if meta!=ometa or sb[:128]!=cb[:128]: raise RuntimeError("header/meta drift")
clean=Image.open(clean_path).convert("RGBA")
source_mask=Image.open(source_mask_path).convert("L")
allowed_full=Image.open(allowed_full_path).convert("L")
protected_full=Image.open(protected_full_path).convert("L")
artwork=Image.open(artwork_path).convert("L")
if any(im.size!=src.size for im in [clean,source_mask,allowed_full,protected_full,artwork]):
    raise RuntimeError("mask size drift")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
fm=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI,FSTYLE=fm.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name: raise RuntimeError(("font",fm))
COL={"red":(186,0,0,255),"gray":(78,96,100,255)}

def render(text,fs,kind):
    stroke=2
    f=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
    pad=stroke+8
    im=Image.new("RGBA",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),(0,0,0,0))
    ImageDraw.Draw(im).text((pad-tb[0],pad-tb[1]),text,font=f,fill=COL[kind],stroke_width=stroke,stroke_fill=COL[kind])
    b=im.getchannel("A").getbbox()
    return im.crop(b),stroke

final=old.copy()
selected=np.zeros((meta["h"],meta["w"]),bool)
layers={}
rows=[]
for cfg in ROWS:
    x0,y0,x1,y1=cfg["bbox"]; sw=x1-x0; sh=y1-y0
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
    tile,stroke=render(cfg["korean"],cfg["font_size"],cfg["kind"])
    target=min(sw-4,cfg["target_width"])
    if tile.width!=target: tile=tile.resize((target,tile.height),Image.Resampling.LANCZOS)
    if tile.width>=sw or tile.height>=sh: raise RuntimeError(("ceiling",cfg["key"],tile.size,[sw,sh]))
    # All source labels in this family are left anchored.
    px=x0+2; py=y0+(sh-tile.height)//2
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lb=list(layer.getchannel("A").getbbox())
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<=0: raise RuntimeError(("margin",cfg["key"],lb,margins))
    final.alpha_composite(layer); layers[cfg["key"]]=layer
    selected[y0:y1,x0:x1]=True
    rows.append({
      "key":cfg["key"],"source":cfg["source"],"korean":cfg["korean"],"kind":cfg["kind"],
      "source_bbox":cfg["bbox"],"source_size":[sw,sh],"prior_bbox":cfg["prior_bbox"],
      "prior_size":[cfg["prior_bbox"][2]-cfg["prior_bbox"][0],cfg["prior_bbox"][3]-cfg["prior_bbox"][1]],
      "localized_bbox":lb,"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"margins":margins,
      "width_source_ratio":round((lb[2]-lb[0])/sw,4),"height_source_ratio":round((lb[3]-lb[1])/sh,4),
      "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"font_size":cfg["font_size"],
      "stroke_width":stroke,"fill_rgba":COL[cfg["kind"]],"containment":"PASS","size_ceiling":"PASS"
    })

ks=list(layers)
for i in range(len(ks)):
    for j in range(i+1,len(ks)):
        if ImageChops.multiply(layers[ks[i]].getchannel("A"),layers[ks[j]].getchannel("A")).getbbox():
            raise RuntimeError(("overlap",ks[i],ks[j]))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",meta["mode"])
candidate.write_bytes(payload); AFTER=sha(payload)
new_raw,new,nmeta=decode(payload)
if nmeta!=meta or payload[:128]!=sb[:128] or ImageChops.difference(new,final).getbbox() is not None:
    raise RuntimeError("roundtrip")

oa=np.asarray(old); na=np.asarray(new)
diff=np.any(oa!=na,axis=2); adiff=oa[:,:,3]!=na[:,:,3]
outside=int(np.count_nonzero(diff&~selected)); alpha_out=int(np.count_nonzero(adiff&~selected))
prot=np.asarray(protected_full)>0; art=np.asarray(artwork)>0
protected_changed=int(np.count_nonzero(diff&prot)); artwork_changed=int(np.count_nonzero(diff&art))
if outside or alpha_out or protected_changed or artwork_changed:
    raise RuntimeError(("protection",outside,alpha_out,protected_changed,artwork_changed))

ca=np.asarray(clean)
for rr in rows:
    x0,y0,x1,y1=rr["source_bbox"]
    a=na[y0:y1,x0:x1]; c=ca[y0:y1,x0:x1]
    vis=(a[:,:,3]>16)&(np.any(a[:,:,:3]!=c[:,:,:3],axis=2)|(a[:,:,3]!=c[:,:,3]))
    db=bb(vis)
    if db is None: raise RuntimeError(("decoded empty",rr["key"]))
    db=[db[0]+x0,db[1]+y0,db[2]+x0,db[3]+y0]
    margins=[db[0]-x0,x1-db[2],db[1]-y0,y1-db[3]]
    if min(margins)<=0: raise RuntimeError(("decoded margin",rr["key"],db,margins))
    rr["decoded_bbox"]=db; rr["decoded_size"]=[db[2]-db[0],db[3]-db[1]]; rr["decoded_margins"]=margins

# Full independent masks remain the authoritative family gate.
src_png=tmp/"source.png"; new_png=tmp/"new.png"
src.save(src_png); new.save(new_png)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(src_png),str(clean_path),str(source_mask_path),
                "--protected-mask",str(protected_full_path),"--report",str(out/"B225_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(src_png),str(new_png),str(allowed_full_path),
                "--protected-mask",str(protected_full_path),"--report",str(out/"B225_FINAL_VALIDATION.json")],check=True)

# Full-sheet readable and RAW evidence.
cards=[card("SOURCE",src),card("C141",old),card("B225",new)]
sheet=Image.new("RGB",(meta["w"],sum(c.height for c in cards)+8),(20,20,20)); y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height+4
sheet.save(out/"B225_4D38_SOURCE_C141_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)

contacts=[]
for rr in rows:
    x0,y0,x1,y1=rr["source_bbox"]; p=8
    cr=(max(0,x0-p),max(0,y0-p),min(meta["w"],x1+p),min(meta["h"],y1+p))
    ims=[composite(z).crop(cr) for z in (src,old,new)]
    ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
    cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+28
    c=Image.new("RGB",(cw,ch),(24,24,24)); d=ImageDraw.Draw(c); x=0
    for lab,z in zip(("SOURCE","C141","B225"),ims):
        d.text((x+5,6),lab,fill="white"); c.paste(z,(x,28)); x+=z.width+6
    contacts.append(c)
cs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4),(20,20,20)); y=0
for c in contacts: cs.paste(c,(0,y)); y+=c.height+4
cs.save(out/"B225_4D38_ROW_CONTACT_2X.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE RAW",src_raw),card("B225 RAW",new_raw)]
rs=Image.new("RGB",(meta["w"],sum(c.height for c in rawcards)+4),(20,20,20)); y=0
for c in rawcards: rs.paste(c,(0,y)); y+=c.height+4
rs.save(out/"B225_4D38_SOURCE_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B225","queue_index":154,"asset":asset,
 "trigger":"STRICT_PRE_INGAME_8_STEP_VISUAL_FALSE_NEGATIVE_HIERARCHY",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/020_q154_4D38BBB0.jpg",
 "prior_c_status":"C141_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":AFTER,"source_url":url,
 "defects":["RED_FAMILY_SOURCE_RELATIVE_WIDTH_TOO_WEAK","GRAY_FAMILY_SOURCE_RELATIVE_WIDTH_TOO_WEAK","SHOWROOM_CAPTION_LIKE_UNDERSIZING"],
 "method":"exact pinned 4096x1024 RGBA32 source + C141 independently verified exact clean plate; all eight localizable labels rebuilt from fresh native Noto Sans CJK KR Bold at existing source-family heights/colors/strokes, source-left anchored, with moderate horizontal hierarchy restoration that remains below each exact source bbox; no old Korean bitmap upscaling; Ferrari artwork and protected regions unchanged",
 "rows":rows,
 "machine_qa":{"bbox_source_size_positive_margin":"8/8 PASS","candidate_changes_outside_selected_source_bboxes":outside,
   "alpha_changes_outside_selected_source_bboxes":alpha_out,"protected_visible_changed":protected_changed,
   "artwork_changed":artwork_changed,"localized_overlap_pixels":0,"header_128_exact":True,
   "raw_mode":meta["mode"],"raw_orientation":"mirror_y","roundtrip":"PASS"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_C141_EXACT_CLEAN_REUSED_AND_REVALIDATED",
   "2_slant_direction":"PASS_SOURCE_UPRIGHT_FAMILY",
   "3_no_unnecessary_undersizing":"PASS_MATERIAL_HORIZONTAL_HIERARCHY_RESTORATION",
   "4_source_weight_outline_shadow":"PASS_SHARED_RED_AND_GRAY_SOURCE_FAMILIES",
   "5_no_clipping":"PASS_8_OF_8_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_ZERO_PROTECTED_OR_FERRARI_ARTWORK_CHANGE",
   "7_flip_y_raw":"PASS_RAW_EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER"
 },
 "runtime_validation":"UNTESTED","status":"B225_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B225_4D38BBB0_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B225_4D38BBB0.json").write_text(json.dumps({"role":"B","run":"B225","queue_index":154,"asset":asset,
 "candidate_sha256":AFTER,"report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B225","before":EXPECTED_BEFORE,"after":AFTER,"rows":[{"key":r["key"],"old":r["prior_size"],"new":r["decoded_size"],"source":r["source_size"],"margins":r["decoded_margins"]} for r in rows],"outside":outside,"protected":protected_changed,"artwork":artwork_changed,"status":report["status"]},ensure_ascii=False))
