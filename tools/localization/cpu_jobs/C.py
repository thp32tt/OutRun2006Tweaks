#!/usr/bin/env python3
# C267 C2 fresh independent QA for q140/q154/q164.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import hashlib, io, json, os, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

ROOT=Path(".")
RUN="20261008-C267-C2-Q140-Q154-Q164"
OUT=ROOT/"localization/graphics/role_C"/RUN
OUT.mkdir(parents=True,exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()
def load_bytes(b): return np.array(Image.open(io.BytesIO(b)).convert("RGBA"))
def load_path(p,mode="RGBA"): return np.array(Image.open(ROOT/p).convert(mode))
def flip(a): return np.flipud(a).copy()
def bbox(mask):
    ys,xs=np.where(mask)
    if len(xs)==0:return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def union(shape,boxes):
    m=np.zeros(shape[:2],bool)
    for x0,y0,x1,y1 in boxes:m[y0:y1,x0:x1]=True
    return m
def neutral(a):
    rgb=a[...,:3].astype(np.float32); al=a[...,3:4].astype(np.float32)/255.0
    return np.clip(rgb*al+128*(1-al),0,255).astype(np.uint8)
def pil(a): return Image.fromarray(neutral(a),"RGB")
def get_source(cfg):
    with urllib.request.urlopen(cfg["source_url"],timeout=120) as r:b=r.read()
    got=sha(b)
    if got!=cfg["source_sha"]: raise RuntimeError(f'{cfg["index"]} source sha {got}')
    return b
def save_contacts(src,clean,cur,rows,path):
    cards=[]
    for r in rows:
        x0,y0,x1,y1=r["source_bbox"]; pad=14
        x0=max(0,x0-pad);y0=max(0,y0-pad);x1=min(src.shape[1],x1+pad);y1=min(src.shape[0],y1+pad)
        ims=[pil(a[y0:y1,x0:x1]) for a in (src,clean,cur)]
        scale=min(2.0,760/max(i.width for i in ims))
        if scale!=1:
            ims=[i.resize((max(1,int(i.width*scale)),max(1,int(i.height*scale))),Image.Resampling.NEAREST if scale>1 else Image.Resampling.LANCZOS) for i in ims]
        w=max(i.width for i in ims);hh=max(i.height for i in ims)
        c=Image.new("RGB",(w*3,hh+30),(96,96,96));d=ImageDraw.Draw(c)
        d.text((4,4),f'SOURCE | CLEAN | CURRENT  {r["source"]} -> {r["korean"]}',fill=(255,255,255))
        for j,im in enumerate(ims):c.paste(im,(j*w,28))
        cards.append(c)
    W=max(c.width for c in cards);H=sum(c.height for c in cards)
    out=Image.new("RGB",(W,H),(96,96,96));y=0
    for c in cards:out.paste(c,(0,y));y+=c.height
    out.save(path,quality=95,subsampling=0)
def save_raw(srcraw,curraw,path):
    items=[]
    for title,a in [("SOURCE RAW",srcraw),("CURRENT RAW",curraw),("SOURCE FLIP-Y",flip(srcraw)),("CURRENT FLIP-Y",flip(curraw))]:
        im=pil(a); scale=min(1.0,1200/im.width)
        if scale<1:im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(im.width,im.height+26),(96,96,96));ImageDraw.Draw(c).text((4,4),title,fill=(255,255,255));c.paste(im,(0,24));items.append(c)
    W=max(i.width for i in items);H=sum(i.height for i in items)
    out=Image.new("RGB",(W,H),(96,96,96));y=0
    for i in items:out.paste(i,(0,y));y+=i.height
    out.save(path,quality=93,subsampling=0)
def save_practical(src,cur,path):
    items=[]
    for sc in (1.0,.75,.5,.25):
        a=pil(src);b=pil(cur)
        if sc!=1:
            a=a.resize((max(1,int(a.width*sc)),max(1,int(a.height*sc))),Image.Resampling.LANCZOS)
            b=b.resize((max(1,int(b.width*sc)),max(1,int(b.height*sc))),Image.Resampling.LANCZOS)
        w=max(a.width,b.width);hh=max(a.height,b.height)
        c=Image.new("RGB",(w*2,hh+28),(96,96,96));ImageDraw.Draw(c).text((4,4),f'SOURCE | CURRENT scale={sc}',fill=(255,255,255));c.paste(a,(0,26));c.paste(b,(w,26));items.append(c)
    W=max(i.width for i in items);H=sum(i.height for i in items)
    out=Image.new("RGB",(W,H),(96,96,96));y=0
    for i in items:out.paste(i,(0,y));y+=i.height
    out.save(path,quality=92,subsampling=0)

configs=[
{"index":140,"id":"31C58963","candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds","candidate_sha":"588eb51d554c8adeef850bd53d665ed9f4a4d1c3389b9e67dcdd4be9f4dd635c","source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds","source_sha":"ae048d04fef96108f6ee30c41022aedb78083d76386448df5483ae0ccd083dcd","clean_path":"localization/graphics/role_C/20261005-C140-31C58963/C140_EXACT_CLEAN_PLATE.png","protected_path":"localization/graphics/role_C/20261005-C140-31C58963/C140_PROTECTED_VISIBLE_MASK.png","source_text_mask":"localization/graphics/role_C/20261005-C140-31C58963/C140_SOURCE_TEXT_MASK.png","rows":[
{"key":"select_stage","source":"SELECT STAGE","korean":"스테이지 선택","source_bbox":[7,905,840,1003]},
{"key":"select_race","source":"SELECT RACE","korean":"레이스 선택","source_bbox":[13,749,793,847]},
{"key":"select_mode","source":"SELECT MODE","korean":"모드 선택","source_bbox":[7,589,815,687]},
{"key":"showroom","source":"SHOWROOM","korean":"쇼룸","source_bbox":[7,432,652,527]},
{"key":"key_word","source":"KEY","korean":"키","source_bbox":[457,319,583,381]}]},
{"index":154,"id":"4D38BBB0","candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds","candidate_sha":"815f0112c772ef1a99b5cb86639415701582301edaaf3ac5bec276e69a475288","source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds","source_sha":"15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf","clean_path":"localization/graphics/role_C/20261005-C141-4D38BBB0/C141_EXACT_CLEAN_PLATE.png","protected_path":"localization/graphics/role_C/20261005-C141-4D38BBB0/C141_PROTECTED_VISIBLE_MASK.png","source_text_mask":"localization/graphics/role_C/20261005-C141-4D38BBB0/C141_SOURCE_TEXT_MASK.png","rows":[
{"key":"create_new_license","source":"CREATE NEW LICENSE","korean":"새 라이선스 만들기","source_bbox":[13,548,1954,696]},
{"key":"select_license","source":"SELECT LICENSE","korean":"라이선스 선택","source_bbox":[2007,541,3468,689]},
{"key":"single_player_red","source":"SINGLE PLAYER","korean":"싱글 플레이","source_bbox":[12,374,1388,522]},
{"key":"default_license","source":"DEFAULT LICENSE","korean":"기본 라이선스","source_bbox":[1772,374,3316,522]},
{"key":"multiplayer_red","source":"MULTIPLAYER","korean":"멀티플레이","source_bbox":[15,203,1235,347]},
{"key":"single_player_gray","source":"SINGLE PLAYER","korean":"싱글 플레이","source_bbox":[1610,286,2197,350]},
{"key":"showroom_gray","source":"SHOWROOM","korean":"쇼룸","source_bbox":[2674,288,3094,350]},
{"key":"multiplayer_gray","source":"MULTIPLAYER","korean":"멀티플레이","source_bbox":[2566,952,3086,1014]}]},
{"index":164,"id":"5B65E08C","candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/5B65E08C_512x256.dds","candidate_sha":"65bad7ee4e2f74bb859f4b993a046fd11747cc416e3192d2e671fd621593ee5f","source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_sumo_fe_cvt_Exst/5B65E08C_512x256.dds","source_sha":"5ca485fc5bcad59ba4d23225a951660a5009c436cac23b590946cb1a64e4634e","clean_path":"localization/graphics/role_B/20261004-B-PRODUCTION20/5B65E08C_CLEAN_PLATE.png","protected_path":"localization/graphics/role_B/20261004-B-PRODUCTION20/5B65E08C_PROTECTED_MASK.png","source_text_mask":"localization/graphics/role_B/20261004-B-PRODUCTION20/5B65E08C_SOURCE_TEXT_MASK.png","rows":[
{"key":"select_license","source":"SELECT LICENSE","korean":"라이선스 선택","source_bbox":[590,565,1493,659]}]}
]

allrep=[]
for cfg in configs:
    sb=get_source(cfg);cb=(ROOT/cfg["candidate_path"]).read_bytes()
    srcraw=load_bytes(sb);curraw=load_bytes(cb);src=flip(srcraw);cur=flip(curraw)
    clean=load_path(cfg["clean_path"]); protected=load_path(cfg["protected_path"],"L")>0; srcmask=load_path(cfg["source_text_mask"],"L")>0
    if src.shape!=cur.shape or clean.shape!=cur.shape: raise RuntimeError(f'{cfg["index"]} shape mismatch')
    allow=union(cur.shape,[r["source_bbox"] for r in cfg["rows"]])
    delta=np.any(cur!=clean,axis=2); alpha_delta=cur[...,3]!=clean[...,3]
    source_delta=np.any(cur!=src,axis=2)
    rows=[]
    for r in cfg["rows"]:
        x0,y0,x1,y1=r["source_bbox"];bb=bbox(delta[y0:y1,x0:x1])
        if bb:bb=[bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
        rows.append({"key":r["key"],"source":r["source"],"korean":r["korean"],"original_bbox":r["source_bbox"],"localized_bbox":bb,
        "delta_left":bb[0]-x0 if bb else None,"delta_right":x1-bb[2] if bb else None,"delta_top":bb[1]-y0 if bb else None,"delta_bottom":y1-bb[3] if bb else None,
        "containment":"PASS" if bb and bb[0]>=x0 and bb[1]>=y0 and bb[2]<=x1 and bb[3]<=y1 else "FAIL",
        "size_ceiling":"PASS" if bb and bb[2]-bb[0]<=x1-x0 and bb[3]-bb[1]<=y1-y0 else "FAIL",
        "positive_margin":"PASS" if bb and bb[0]>x0 and bb[1]>y0 and bb[2]<x1 and bb[3]<y1 else "FAIL"})
    outside=int(np.count_nonzero(delta & ~allow)); alpha_out=int(np.count_nonzero(alpha_delta & ~allow))
    protected_changed=int(np.count_nonzero(source_delta & protected))
    localized_protected=int(np.count_nonzero(delta & protected))
    clean_source_exact=int(np.count_nonzero(np.all(clean==src,axis=2) & srcmask))
    current_source_exact=int(np.count_nonzero(np.all(cur==src,axis=2) & srcmask))
    machine=(sha(cb)==cfg["candidate_sha"] and sha(sb)==cfg["source_sha"] and cb[:128]==sb[:128] and outside==0 and alpha_out==0 and protected_changed==0 and localized_protected==0 and all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in rows))
    rep={"schema_version":1,"run":"C267","role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":cfg["index"],"asset":cfg["id"],
    "candidate_sha256":sha(cb),"expected_candidate_sha256":cfg["candidate_sha"],"candidate_sha_match":sha(cb)==cfg["candidate_sha"],"source_sha256":sha(sb),"source_origin":cfg["source_url"],
    "dimensions":[int(cur.shape[1]),int(cur.shape[0])],"header_128_exact":cb[:128]==sb[:128],"raw_orientation":"mirror_y","rows":rows,
    "changed_pixels_outside_source_bboxes":outside,"alpha_changed_pixels_outside_source_bboxes":alpha_out,"protected_source_pixels_changed":protected_changed,
    "localized_pixels_overlapping_protected_mask":localized_protected,"clean_source_text_mask_pixels_exact_source":clean_source_exact,"current_source_text_mask_pixels_exact_source":current_source_exact,
    "machine_result":"PASS" if machine else "FAIL","controller_visual_qa":"PENDING","c3_strict":"PENDING","runtime_validation":"UNTESTED"}
    stem=f'C267_Q{cfg["index"]:03d}'
    (OUT/f'{stem}_MACHINE_QA.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    save_contacts(src,clean,cur,cfg["rows"],OUT/f'{stem}_CONTACTS.jpg')
    save_raw(srcraw,curraw,OUT/f'{stem}_RAW_FLIPY.jpg')
    save_practical(src,cur,OUT/f'{stem}_PRACTICAL.jpg')
    allrep.append(rep)
(OUT/"C267_BATCH_MACHINE_SUMMARY.json").write_text(json.dumps({"run":"C267","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","reports":allrep},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
