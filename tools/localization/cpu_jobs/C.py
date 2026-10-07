#!/usr/bin/env python3
# C266 C1 fresh independent QA evidence for q59/q89/q135.
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import hashlib, io, json, os, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

ROOT=Path(".")
RUN="20261008-C266-C1-Q059-Q089-Q135"
OUT=ROOT/"localization/graphics/role_C"/RUN
OUT.mkdir(parents=True, exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()
def load_rgba_bytes(b): return np.array(Image.open(io.BytesIO(b)).convert("RGBA"))
def load_rgba_path(p): return np.array(Image.open(p).convert("RGBA"))
def flip(a): return np.flipud(a).copy()
def bbox(mask):
    ys,xs=np.where(mask)
    if len(xs)==0: return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def inside(a,b):
    return bool(a and a[0]>=b[0] and a[1]>=b[1] and a[2]<=b[2] and a[3]<=b[3])
def union(shape, boxes):
    m=np.zeros(shape[:2],dtype=bool)
    for x0,y0,x1,y1 in boxes: m[y0:y1,x0:x1]=True
    return m
def neutral(a):
    rgb=a[...,:3].astype(np.float32)
    al=a[...,3:4].astype(np.float32)/255.0
    return np.clip(rgb*al+128*(1-al),0,255).astype(np.uint8)
def pil(a): return Image.fromarray(neutral(a),"RGB")
def get_source(cfg):
    with urllib.request.urlopen(cfg["source_url"],timeout=90) as r: b=r.read()
    got=sha(b)
    if got!=cfg["source_sha"]: raise RuntimeError(f'{cfg["id"]} source sha mismatch {got}')
    return b
def mask_path(path):
    a=np.array(Image.open(ROOT/path).convert("L"))
    return a>0
def save_contacts(src,clean,cur,rows,path):
    cards=[]
    for r in rows:
        x0,y0,x1,y1=r["source_bbox"]; pad=12
        x0=max(0,x0-pad); y0=max(0,y0-pad); x1=min(src.shape[1],x1+pad); y1=min(src.shape[0],y1+pad)
        ims=[pil(a[y0:y1,x0:x1]) for a in (src,clean,cur)]
        scale=min(1.0,520/max(i.width for i in ims))
        if scale<1:
            ims=[i.resize((max(1,int(i.width*scale)),max(1,int(i.height*scale))),Image.Resampling.LANCZOS) for i in ims]
        w=max(i.width for i in ims); h=max(i.height for i in ims)
        card=Image.new("RGB",(w*3,h+30),(96,96,96)); d=ImageDraw.Draw(card)
        d.text((4,4),f'SOURCE | CLEAN | CURRENT   {r["source"]} -> {r["korean"]}',fill=(255,255,255))
        for j,im in enumerate(ims): card.paste(im,(j*w,28))
        cards.append(card)
    W=max(c.width for c in cards); H=sum(c.height for c in cards)
    out=Image.new("RGB",(W,H),(96,96,96)); y=0
    for c in cards: out.paste(c,(0,y)); y+=c.height
    out.save(path,quality=95,subsampling=0)
def save_raw(srcraw,curraw,path):
    items=[]
    for title,a in [("SOURCE RAW",srcraw),("CURRENT RAW",curraw),("SOURCE FLIP-Y",flip(srcraw)),("CURRENT FLIP-Y",flip(curraw))]:
        im=pil(a); scale=min(1.0,1100/im.width)
        if scale<1: im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(im.width,im.height+26),(96,96,96)); ImageDraw.Draw(c).text((4,4),title,fill=(255,255,255)); c.paste(im,(0,24)); items.append(c)
    W=max(i.width for i in items); H=sum(i.height for i in items)
    out=Image.new("RGB",(W,H),(96,96,96)); y=0
    for i in items: out.paste(i,(0,y)); y+=i.height
    out.save(path,quality=94,subsampling=0)
def save_practical(src,cur,path):
    items=[]
    for scale in (1.0,.75,.5,.25):
        a=pil(src); b=pil(cur)
        if scale!=1:
            a=a.resize((max(1,int(a.width*scale)),max(1,int(a.height*scale))),Image.Resampling.LANCZOS)
            b=b.resize((max(1,int(b.width*scale)),max(1,int(b.height*scale))),Image.Resampling.LANCZOS)
        w=max(a.width,b.width); h=max(a.height,b.height)
        c=Image.new("RGB",(w*2,h+28),(96,96,96)); ImageDraw.Draw(c).text((4,4),f'SOURCE | CURRENT scale={scale}',fill=(255,255,255))
        c.paste(a,(0,26)); c.paste(b,(w,26)); items.append(c)
    W=max(i.width for i in items); H=sum(i.height for i in items)
    out=Image.new("RGB",(W,H),(96,96,96)); y=0
    for i in items: out.paste(i,(0,y)); y+=i.height
    out.save(path,quality=92,subsampling=0)

def evaluate(cfg):
    cb=(ROOT/cfg["candidate_path"]).read_bytes()
    sb=get_source(cfg)
    csha=sha(cb)
    srcraw=load_rgba_bytes(sb); curraw=load_rgba_bytes(cb)
    src=flip(srcraw); cur=flip(curraw)
    clean=load_rgba_path(ROOT/cfg["clean_path"])
    if src.shape!=cur.shape or clean.shape!=cur.shape:
        raise RuntimeError(f'{cfg["id"]} shape mismatch src={src.shape} cur={cur.shape} clean={clean.shape}')
    allow=union(cur.shape,[r["source_bbox"] for r in cfg["rows"]])
    changed=np.any(cur!=clean,axis=2)
    alpha_changed=(cur[...,3]!=clean[...,3])
    protected=mask_path(cfg["protected_path"]) if cfg.get("protected_path") else np.zeros(cur.shape[:2],bool)
    srcmask=mask_path(cfg["source_text_mask"]) if cfg.get("source_text_mask") else allow
    rows=[]
    for r in cfg["rows"]:
        x0,y0,x1,y1=r["source_bbox"]
        d=changed[y0:y1,x0:x1]
        bb=bbox(d)
        if bb: bb=[bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
        exp=r["localized_bbox"]
        rows.append({
            "key":r["key"],"source":r["source"],"korean":r["korean"],
            "original_bbox":r["source_bbox"],"localized_bbox":bb,"producer_localized_bbox":exp,
            "derived_bbox_matches_producer":bb==exp,
            "delta_left":bb[0]-x0 if bb else None,"delta_right":x1-bb[2] if bb else None,
            "delta_top":bb[1]-y0 if bb else None,"delta_bottom":y1-bb[3] if bb else None,
            "source_size":[x1-x0,y1-y0],
            "localized_size":[bb[2]-bb[0],bb[3]-bb[1]] if bb else None,
            "containment":"PASS" if inside(bb,r["source_bbox"]) else "FAIL",
            "size_ceiling":"PASS" if bb and bb[2]-bb[0]<=x1-x0 and bb[3]-bb[1]<=y1-y0 else "FAIL",
            "positive_margin":"PASS" if bb and bb[0]>x0 and bb[1]>y0 and bb[2]<x1 and bb[3]<y1 else "FAIL"
        })
    outside=int(np.count_nonzero(changed & ~allow))
    alpha_out=int(np.count_nonzero(alpha_changed & ~allow))
    protected_changes=int(np.count_nonzero(np.any(cur!=src,axis=2) & protected))
    clean_protected_changes=int(np.count_nonzero(np.any(clean!=src,axis=2) & protected))
    clean_source_unchanged=int(np.count_nonzero(np.all(clean==src,axis=2) & srcmask))
    current_source_exact=int(np.count_nonzero(np.all(cur==src,axis=2) & srcmask))
    rows_ok=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" and r["derived_bbox_matches_producer"] for r in rows)
    machine=(csha==cfg["candidate_sha"] and sha(sb)==cfg["source_sha"] and sb[:128]==cb[:128] and
             outside==0 and alpha_out==0 and protected_changes==0 and clean_protected_changes==0 and rows_ok)
    rep={
      "schema_version":1,"run":RUN,"role":"C","lane":"C1",
      "TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
      "queue_index":cfg["index"],"asset":cfg["id"],
      "candidate_sha256":csha,"expected_candidate_sha256":cfg["candidate_sha"],"candidate_sha_match":csha==cfg["candidate_sha"],
      "source_sha256":sha(sb),"source_origin":cfg["source_url"],
      "dimensions":[int(cur.shape[1]),int(cur.shape[0])],"header_128_exact":sb[:128]==cb[:128],"raw_orientation":"mirror_y",
      "rows":rows,
      "changed_pixels_outside_source_bboxes":outside,
      "alpha_changed_pixels_outside_source_bboxes":alpha_out,
      "protected_source_pixels_changed":protected_changes,
      "clean_protected_source_pixels_changed":clean_protected_changes,
      "clean_source_text_mask_pixels_unchanged":clean_source_unchanged,
      "current_source_text_mask_pixels_exact_source":current_source_exact,
      "machine_result":"PASS" if machine else "FAIL",
      "controller_visual_qa":"PENDING","c3_strict":"PENDING","runtime_validation":"UNTESTED"
    }
    stem=f'C266_Q{cfg["index"]:03d}'
    (OUT/f'{stem}_MACHINE_QA.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    save_contacts(src,clean,cur,cfg["rows"],OUT/f'{stem}_CONTACTS.jpg')
    save_raw(srcraw,curraw,OUT/f'{stem}_RAW_FLIPY.jpg')
    save_practical(src,cur,OUT/f'{stem}_PRACTICAL.jpg')
    return rep

configs=[
 {"id":"7CE1CFC5","index":59,
  "candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds",
  "candidate_sha":"cc8745c36a40422f747fd5ceb66f42f36d165292750765a506a8b1fcba7cb217",
  "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds",
  "source_sha":"9c35216873d617ed68df55be424f35ddf50b1eacc8ee86072068745aea166f9f",
  "clean_path":"localization/graphics/role_A/20261005-A-PRODUCTION25/7CE_CLEAN_PLATE.png",
  "protected_path":"localization/graphics/role_A/20261005-A-PRODUCTION25/7CE_PROTECTED_MASK.png",
  "source_text_mask":"localization/graphics/role_A/20261005-A-PRODUCTION25/7CE_SOURCE_TEXT_MASK.png",
  "rows":[
   {"key":"next_mission","source":"NEXT MISSION","korean":"다음 미션","source_bbox":[8,353,1293,500],"localized_bbox":[396,361,904,492]},
   {"key":"race_rivals","source":"Race The Rivals!","korean":"라이벌과 레이스!","source_bbox":[75,222,625,304],"localized_bbox":[102,227,597,299]},
   {"key":"drift_score","source":"Drift To Score!","korean":"드리프트 점수 도전!","source_bbox":[119,53,609,137],"localized_bbox":[128,66,599,123]},
   {"key":"slipstream_score","source":"Slipstream To Score!","korean":"슬립스트림 점수 도전!","source_bbox":[717,225,1408,320],"localized_bbox":[727,235,1398,310]}
  ]},
 {"id":"43B07A77","index":89,
  "candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds",
  "candidate_sha":"741a05cb632e85a4fea783e51bb2f98678c0510f8b34fc7a73cc39c898c0749c",
  "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds",
  "source_sha":"906a17ef9534bcb43d8296ae1d2ac339a53910f7113b954a52475368ab9b4175",
  "clean_path":"localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_CLEAN_PLATE.png",
  "protected_path":"localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_PROTECTED_VISIBLE_MASK.png",
  "source_text_mask":"localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_SOURCE_TEXT_MASK.png",
  "rows":[{"key":"game_over","source":"Game Over","korean":"게임 오버","source_bbox":[1,13,1494,251],"localized_bbox":[122,19,1372,245]}]},
 {"id":"2B0863D6","index":135,
  "candidate_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds",
  "candidate_sha":"8657a59f966bb4be994a00ead41d6939a5145efba320deab83cd3ef8af92b0c1",
  "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds",
  "source_sha":"dafe21ec29ace60273f3ec10a40072446f3f28232b3f9a8acce3897ade1eff06",
  "clean_path":"localization/graphics/role_A/20261007-A-MANUALQA149-2B0863D6/2B0863D6_HD_CLEAN_PLATE.png",
  "protected_path":"localization/graphics/role_A/20261007-A-MANUALQA149-2B0863D6/2B0863D6_HD_CLEAN_PROTECTED_VISIBLE_MASK.png",
  "source_text_mask":"localization/graphics/role_A/20261007-A-MANUALQA149-2B0863D6/2B0863D6_HD_SOURCE_TEXT_MASK.png",
  "rows":[
   {"key":"professional","source":"PROFESSIONAL","korean":"프로","source_bbox":[189,185,698,245],"localized_bbox":[370,187,516,243]},
   {"key":"novice","source":"NOVICE","korean":"초급","source_bbox":[1154,187,1399,246],"localized_bbox":[1216,189,1337,244]},
   {"key":"outrun","source":"OUTRUN","korean":"아웃런","source_bbox":[423,107,700,166],"localized_bbox":[477,109,646,164]},
   {"key":"intermediate_b","source":"INTERMEDIATE B","korean":"중급 B","source_bbox":[830,108,1396,164],"localized_bbox":[1026,110,1200,162]},
   {"key":"intermediate_a","source":"INTERMEDIATE A","korean":"중급 A","source_bbox":[128,28,696,84],"localized_bbox":[325,30,499,82]},
   {"key":"change_class","source":"CHANGE CLASS","korean":"클래스 변경","source_bbox":[840,38,1243,86],"localized_bbox":[923,40,1160,84]},
   {"key":"class","source":"CLASS","korean":"클래스","source_bbox":[1292,50,1429,87],"localized_bbox":[1313,52,1407,85]},
   {"key":"acceleration","source":"ACCELERATION","korean":"가속","source_bbox":[1475,48,1736,81],"localized_bbox":[1576,50,1635,79]},
   {"key":"max_speed","source":"MAX SPEED","korean":"최고 속도","source_bbox":[1746,48,1962,81],"localized_bbox":[1793,50,1914,79]},
   {"key":"handling","source":"HANDLING","korean":"핸들링","source_bbox":[1412,128,1597,161],"localized_bbox":[1460,130,1549,159]}
  ]}
]
reports=[evaluate(c) for c in configs]
summary={
 "schema_version":1,"run":RUN,"role":"C","lane":"C1","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "selection_head":"b1bf355b797697a454bc01321bbc40ef792a302e",
 "execution_backend":"github_actions_cpu_worker_exact_repository_candidate_and_pinned_public_source_after_local_binary_materialization_unavailable",
 "assets":[{"queue_index":r["queue_index"],"asset":r["asset"],"candidate_sha256":r["candidate_sha256"],"machine_result":r["machine_result"]} for r in reports],
 "controller_visual_qa":"PENDING","c3_strict":"PENDING","pre_ingame_export":"PENDING_CONTROLLER_DECISION","runtime_validation":"UNTESTED"
}
(OUT/"C266_BATCH_COMPUTE.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(ROOT/"localization/graphics/worker_results/C266_C1_Q059_Q089_Q135.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
