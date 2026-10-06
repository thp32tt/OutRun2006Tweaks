#!/usr/bin/env python3
# B211: manual PRE_INGAME JPG QA scale/hierarchy rework for q198 9FC88069.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

repo=Path.cwd()
run="20261006-B-MANUALQA211-9FC88069"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/9FC88069_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/rel
clean_path=repo/"localization/graphics/role_C/20261005-C150-9FC88069/C150_EXACT_CLEAN_PLATE.png"
EXPECTED_BEFORE="34e7a924b46c98b0b714d6bebd40f7e94d352a26de269816e421db5242ad819c"
SOURCE_SHA="2729b78176ec648039f5b45baf52b1a78e8586e6233baf9a6be4f351f5b1add4"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/9FC88069_1024x512.dds"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(candidate)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift",sha(candidate),EXPECTED_BEFORE))
srcp=Path("/tmp/B211_9FC_SOURCE.dds")
urllib.request.urlretrieve(SOURCE_URL,srcp)
if sha(srcp)!=SOURCE_SHA:
    raise RuntimeError(("source sha drift",sha(srcp),SOURCE_SHA))

def meta(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    fourcc=b[84:88]; masks=struct.unpack_from("<4I",b,92)
    return b,w,h,fourcc,masks

def load_readable(p):
    b,w,h,fourcc,masks=meta(p)
    if fourcc!=b"\0\0\0\0": raise RuntimeError(("expected RGBA32",fourcc))
    if len(b)!=128+w*h*4: raise RuntimeError(("size",len(b),w,h))
    if masks[:3]==(0xff0000,0xff00,0xff): rawmode="BGRA"
    elif masks[:3]==(0xff,0xff00,0xff0000): rawmode="RGBA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",rawmode)
    return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"header":b[:128],"w":w,"h":h,"rawmode":rawmode,"masks":list(masks)}

def write_readable(p,im,m):
    raw=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=m["header"]+raw.tobytes("raw",m["rawmode"])
    Path(p).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

source,smeta=load_readable(srcp)
old,m=load_readable(candidate)
clean=Image.open(clean_path).convert("RGBA")
if old.size!=(4096,2048) or source.size!=old.size or clean.size!=old.size:
    raise RuntimeError(("dimensions",source.size,old.size,clean.size))

targets=[
 ("random_card","무작위",[116,1922,434,1984],1.14),
 ("random_play","- 무작위 재생 -",[548,1984,1128,2036],1.12),
 ("intermediate_b","중급 B",[1561,43,1984,84],1.18),
 ("intermediate_a","중급 A",[2198,43,2624,84],1.18),
]
new=old.copy()
allowed=np.zeros((old.height,old.width),bool)
rows=[]

def extract(bbox):
    o=np.asarray(old.crop(bbox),dtype=np.uint8)
    c=np.asarray(clean.crop(bbox),dtype=np.uint8)
    diff=np.max(np.abs(o.astype(np.int16)-c.astype(np.int16)),axis=2)>3
    ys,xs=np.nonzero(diff)
    if len(xs)<20: raise RuntimeError(("empty localized delta",bbox,len(xs)))
    x0,x1=int(xs.min()),int(xs.max()+1); y0,y1=int(ys.min()),int(ys.max()+1)
    arr=o[y0:y1,x0:x1].copy(); dm=diff[y0:y1,x0:x1]; arr[~dm]=0
    return Image.fromarray(arr,"RGBA"),[bbox[0]+x0,bbox[1]+y0,bbox[0]+x1,bbox[1]+y1]

for key,ko,bbox,max_scale in targets:
    x1,y1,x2,y2=bbox; sw=x2-x1; sh=y2-y1
    allowed[y1:y2,x1:x2]=True
    tile,prior=extract(bbox)
    # Increase only isotropically, preserving the C150 Korean style and card/pixel-art geometry.
    scale=min(max_scale,(sw-8)/tile.width,(sh-6)/tile.height)
    if scale<=1.0:
        raise RuntimeError(("B211 expected scale headroom",key,scale,tile.size,(sw,sh)))
    tile=tile.resize((round(tile.width*scale),round(tile.height*scale)),Image.Resampling.LANCZOS)
    bb=tile.getchannel("A").getbbox()
    if bb: tile=tile.crop(bb)
    px=x1+(sw-tile.width)//2; py=y1+(sh-tile.height)//2
    lb=[px,py,px+tile.width,py+tile.height]
    if not (x1<lb[0] and y1<lb[1] and lb[2]<x2 and lb[3]<y2):
        raise RuntimeError(("positive margin",key,bbox,lb))
    new.paste(clean.crop(bbox),(x1,y1))
    layer=Image.new("RGBA",new.size,(0,0,0,0)); layer.alpha_composite(tile,(px,py)); new.alpha_composite(layer)
    rows.append({
      "key":key,"korean":ko,"source_bbox":bbox,"prior_localized_bbox":prior,"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[tile.width,tile.height],"scale_from_prior":scale,
      "delta_left":lb[0]-x1,"delta_right":x2-lb[2],"delta_top":lb[1]-y1,"delta_bottom":y2-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
    })

oa=np.asarray(old,dtype=np.uint8); na=np.asarray(new,dtype=np.uint8)
changed=np.any(oa!=na,axis=2)
outside=int(np.logical_and(changed,~allowed).sum())
alpha_out=int(np.logical_and(oa[:,:,3]!=na[:,:,3],~allowed).sum())
if outside or alpha_out: raise RuntimeError(("scope",outside,alpha_out))
after=write_readable(candidate,new,m)
dec,dm=load_readable(candidate)
if dm["header"]!=m["header"] or not np.array_equal(np.asarray(dec),na):
    raise RuntimeError("roundtrip/header")

def flat(im):
    bg=Image.new("RGBA",im.size,(104,104,104,255)); bg.alpha_composite(im); return bg.convert("RGB")
def contact(raw=False):
    s=source.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else source
    o=old.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else old
    n=dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else dec
    cards=[]
    for key,ko,bbox,_ in targets:
        if raw:
            x1,y1,x2,y2=bbox; bbox=[x1,old.height-y2,x2,old.height-y1]
        x1,y1,x2,y2=bbox; pad=20
        crop=(max(0,x1-pad),max(0,y1-pad),min(old.width,x2+pad),min(old.height,y2+pad))
        ims=[]
        for im in (s,o,n):
            c=flat(im.crop(crop)); c=c.resize((c.width*2,c.height*2),Image.Resampling.NEAREST)
            ims.append(c)
        W=sum(i.width for i in ims)+12; H=max(i.height for i in ims)+32
        card=Image.new("RGB",(W,H),(30,30,30)); d=ImageDraw.Draw(card); x=0
        for lab,im in zip(("SOURCE","OLD","B211"),ims):
            d.text((x+3,3),lab,fill="white"); card.paste(im,(x,28)); x+=im.width+6
        cards.append(card)
    W=max(c.width for c in cards); H=sum(c.height for c in cards)+6*(len(cards)-1)
    sheet=Image.new("RGB",(W,H),(24,24,24)); y=0
    for c in cards: sheet.paste(c,(0,y)); y+=c.height+6
    return sheet
contact(False).save(out/"B211_SOURCE_OLD_NEW_READABLE.jpg","JPEG",quality=95,subsampling=0)
contact(True).save(out/"B211_SOURCE_OLD_NEW_RAW.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B211","queue_index":198,"asset":rel,
 "trigger":"B_MANUAL_PRE_INGAME_JPG_REVIEW_053_VISUAL_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/053_q198_9FC88069.jpg",
 "prior_c_status":"C150_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "defects":["TEXT_SCALE_TOO_SMALL_VS_SOURCE","SOURCE_STYLE_HIERARCHY_MISMATCH"],
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "rows":rows,
 "preservation":{
   "song_titles_music_credits_and_parenthetical_variants":"PIXEL_EXACT_UNTOUCHED_OUTSIDE_4_FUNCTIONAL_BBOXES",
   "other_card_art":"PIXEL_EXACT_UNTOUCHED_OUTSIDE_4_FUNCTIONAL_BBOXES"
 },
 "qa":{
   "changed_pixels_outside_four_source_bboxes":outside,"alpha_changed_outside_four_source_bboxes":alpha_out,
   "dds_header_128_exact":True,"rgba32_roundtrip_exact":True,
   "readable_source_old_new_visual_review":"PENDING_CONTROLLER",
   "raw_source_old_new_visual_review":"PENDING_CONTROLLER"
 },
 "runtime_validation":"UNTESTED",
 "status":"B211_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"B211_9FC88069_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B211_9FC88069.json").write_text(json.dumps({
 "role":"B","run":"B211","queue_index":198,"asset":rel,"candidate_sha256":after,
 "report":str((out/"B211_9FC88069_REPORT.json").relative_to(repo)),
 "status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B211","before":EXPECTED_BEFORE,"after":after,"rows":rows,"status":report["status"]},ensure_ascii=False))
