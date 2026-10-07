#!/usr/bin/env python3
# C260 C2 independent fresh-C static QA for q092/q094/q102.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os, json, hashlib, urllib.request
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

RUN="20261008-C260-C2-Q092-Q094-Q102"
OUT="localization/graphics/role_C/"+RUN
os.makedirs(OUT, exist_ok=True)

ASSETS={
"q092":{
 "index":92,"asset":"1A43E9D9",
 "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/1A43E9D9_512x64.dds",
 "candidate_sha":"c23888347f446a0acd65667624bd3ee210f7d9a84b5f7adafeb746c94676a43a",
 "source_url":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/1A43E9D9_512x64.dds",
 "source_sha":"d19e5191fb1e084fbeb182b5528738b4ad47ab56bef38fb1e1f027e0b6816774",
 "all_rows":[
   ["outrun_mode","OutRun Mode","아웃런 모드",[387,13,1318,132]],
   ["continuous_15","15 continuous course","15코스 연속",[519,132,1589,245]]
 ],
 "target_keys":["outrun_mode","continuous_15"],
 "high_risk":False
},
"q094":{
 "index":94,"asset":"2DA43E41",
 "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds",
 "candidate_sha":"c36da00d6fa421180f6017fd188e9de783a35eb57a6dcc4927039c663aeee905",
 "source":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds",
 "source_sha":"3e00bfda82c2175b28c1d45d3041f91e34ede6de52b867cd867c1c27d4837099",
 "all_rows":[
   ["course_or2","OutRun2 · 15 Continuous Course has been selected.","OutRun2 · 15코스 연속이 / 선택되었습니다.",[115,192,2056,448]],
   ["course_sp","OutRun2: SP · 15 Continuous Course has been selected.","OutRun2: SP · 15코스 연속이 / 선택되었습니다.",[132,488,2078,717]],
   ["wait_other","waiting other","기존 C90 보존",[2200,192,3533,448]],
   ["wait_now","waiting now","기존 C90 보존",[2228,461,3776,717]],
   ["acceleration","acceleration","기존 C90 보존",[3826,247,4016,320]],
   ["max_speed","最高速:","최고 속도:",[3827,319,4018,410]],
   ["handling","ハンドリング:","핸들링:",[1677,896,2112,1050]],
   ["view_change","View Change Button :","시점 변경 버튼:",[3430,998,3896,1102]],
   ["single_play","single play","기존 C90 보존",[1677,1075,2355,1229]],
   ["expert","For Expert Drivers","상급자용",[2842,1124,3479,1229]],
   ["special_course","Special Course","스페셜 코스",[3137,1279,3879,1403]]
 ],
 "target_keys":["course_or2","course_sp","max_speed","handling","view_change","expert","special_course"],
 "high_risk":False
},
"q102":{
 "index":102,"asset":"571E78F3",
 "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds",
 "candidate_sha":"442babea9c5dea9a944dff3d4a6a577f007dad2ae63a9699d380baf0ce7fc05d",
 "source":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds",
 "source_sha":"17ee051e59d23c741c9df428dccd3ee2f7863c19a038f02db250001f44b6c121",
 "all_rows":[
   ["time_attack_mode","Time Attack Mode","타임 어택 모드",[395,15,1330,140]],
   ["continuous_15","15 Continuous Course","15코스 연속",[520,132,1590,245]]
 ],
 "target_keys":["time_attack_mode","continuous_15"],
 "high_risk":True
}
}

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def load_rgba(path):
    im=Image.open(path).convert("RGBA")
    return np.array(im), im.size

def visdiff(a,b):
    ad=a[:,:,3] != b[:,:,3]
    rgb=np.any(a[:,:,:3] != b[:,:,:3],axis=2)
    visible=(a[:,:,3]>0)|(b[:,:,3]>0)
    return ad | (rgb & visible), ad

def bbox(mask):
    ys,xs=np.where(mask)
    if len(xs)==0: return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def opaque(a,bg=(112,112,112,255)):
    fg=Image.fromarray(a,"RGBA")
    return Image.alpha_composite(Image.new("RGBA",fg.size,bg),fg).convert("RGB")

def union_mask(shape, rows):
    m=np.zeros(shape,dtype=bool)
    for _,_,_,b in rows:
        x0,y0,x1,y1=b
        m[y0:y1,x0:x1]=True
    return m

def save_full(src_raw,cand_raw,key):
    cards=[]
    for title,a,b in [("RAW",src_raw,cand_raw),("FLIP-Y",src_raw[::-1],cand_raw[::-1])]:
        ia=opaque(a); ib=opaque(b)
        scale=min(1.0,1000/max(ia.width,ib.width))
        if scale<1:
            z=(max(1,int(ia.width*scale)),max(1,int(ia.height*scale)))
            ia=ia.resize(z,Image.Resampling.LANCZOS); ib=ib.resize(z,Image.Resampling.LANCZOS)
        card=Image.new("RGB",(ia.width+ib.width,max(ia.height,ib.height)+26),(230,230,230))
        d=ImageDraw.Draw(card); d.text((4,5),title+" SOURCE",fill=(0,0,0)); d.text((ia.width+4,5),title+" CURRENT",fill=(0,0,0))
        card.paste(ia,(0,26)); card.paste(ib,(ia.width,26)); cards.append(card)
    out=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)),(220,220,220))
    y=0
    for c in cards: out.paste(c,(0,y)); y+=c.height
    out.save(os.path.join(OUT,"C260_"+key.upper()+"_RAW_FLIPY.jpg"),quality=88)

def save_contacts(src,cand,rows,key):
    cards=[]
    for rk,source,ko,b in rows:
        x0,y0,x1,y1=b; p=12
        xx0=max(0,x0-p); yy0=max(0,y0-p); xx1=min(src.shape[1],x1+p); yy1=min(src.shape[0],y1+p)
        ia=opaque(src[yy0:yy1,xx0:xx1]); ib=opaque(cand[yy0:yy1,xx0:xx1])
        scale=min(2.5,1400/max(1,ia.width+ib.width))
        if scale>1:
            ia=ia.resize((int(ia.width*scale),int(ia.height*scale)),Image.Resampling.NEAREST)
            ib=ib.resize((int(ib.width*scale),int(ib.height*scale)),Image.Resampling.NEAREST)
        card=Image.new("RGB",(ia.width+ib.width,max(ia.height,ib.height)+28),(240,240,240))
        d=ImageDraw.Draw(card); d.text((4,4),rk+" SOURCE",fill=(0,0,0)); d.text((ia.width+4,4),rk+" CURRENT",fill=(0,0,0))
        card.paste(ia,(0,28)); card.paste(ib,(ia.width,28)); cards.append(card)
    W=max(c.width for c in cards); H=sum(c.height for c in cards)
    out=Image.new("RGB",(W,H),(220,220,220)); y=0
    for c in cards: out.paste(c,(0,y)); y+=c.height
    out.save(os.path.join(OUT,"C260_"+key.upper()+"_CONTACTS.jpg"),quality=90)

def save_practical(src,cand,rows,key):
    target=[r for r in rows]
    blocks=[]
    for scale in [1.0,0.75,0.5]:
        rowimgs=[]
        for rk,source,ko,b in target:
            x0,y0,x1,y1=b
            ia=opaque(src[y0:y1,x0:x1]); ib=opaque(cand[y0:y1,x0:x1])
            z=(max(1,int(ia.width*scale)),max(1,int(ia.height*scale)))
            ia=ia.resize(z,Image.Resampling.LANCZOS); ib=ib.resize(z,Image.Resampling.LANCZOS)
            card=Image.new("RGB",(ia.width+ib.width,max(ia.height,ib.height)+24),(235,235,235))
            d=ImageDraw.Draw(card); d.text((4,4),f"{int(scale*100)}% {rk} SRC",fill=(0,0,0)); d.text((ia.width+4,4),"CURRENT",fill=(0,0,0))
            card.paste(ia,(0,24));card.paste(ib,(ia.width,24));rowimgs.append(card)
        W=max(c.width for c in rowimgs); H=sum(c.height for c in rowimgs)
        block=Image.new("RGB",(W,H),(220,220,220)); y=0
        for c in rowimgs:block.paste(c,(0,y));y+=c.height
        blocks.append(block)
    W=max(b.width for b in blocks); H=sum(b.height for b in blocks)
    out=Image.new("RGB",(W,H),(215,215,215)); y=0
    for b in blocks: out.paste(b,(0,y)); y+=b.height
    out.save(os.path.join(OUT,"C260_"+key.upper()+"_PRACTICAL.jpg"),quality=88)

batch={}
for key,a in ASSETS.items():
    cand=a["candidate"]
    if sha256(cand)!=a["candidate_sha"]: raise RuntimeError(key+" candidate SHA mismatch")
    if "source_url" in a:
        src_path=os.path.join("/tmp",key+"_source.dds")
        urllib.request.urlretrieve(a["source_url"],src_path)
    else:
        src_path=a["source"]
    if sha256(src_path)!=a["source_sha"]: raise RuntimeError(key+" source SHA mismatch")
    src_raw,src_size=load_rgba(src_path); cand_raw,cand_size=load_rgba(cand)
    if src_raw.shape!=cand_raw.shape: raise RuntimeError(key+" shape mismatch")

    # ORIENTATION_POLICY: selector/name/menu atlases here are persisted mirror-Y.
    src=src_raw[::-1].copy(); cand_r=cand_raw[::-1].copy()
    allowed=union_mask(src.shape[:2],a["all_rows"])
    diff,adiff=visdiff(src,cand_r)
    outside=~allowed
    outside_changed=int(diff[outside].sum())
    outside_alpha=int(adiff[outside].sum())
    header_equal=open(src_path,"rb").read(128)==open(cand,"rb").read(128)

    target_rows=[]
    row_reports=[]
    for rk,source,ko,b in a["all_rows"]:
        if rk not in a["target_keys"]: continue
        target_rows.append([rk,source,ko,b])
        x0,y0,x1,y1=b
        # These selector/name-entry text sprites are transparent-backed inside the exact source bbox.
        m=cand_r[y0:y1,x0:x1,3] > 0
        bb=bbox(m)
        if bb:
            loc=[bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
            w=loc[2]-loc[0]; h=loc[3]-loc[1]
            margins=[loc[0]-x0,x1-loc[2],loc[1]-y0,y1-loc[3]]
        else:
            loc=None; w=h=0; margins=None
        edge=bool(loc and min(margins)==0)
        row_reports.append({
          "key":rk,"source":source,"korean":ko,"original_bbox":b,
          "localized_bbox":loc,"source_size":[x1-x0,y1-y0],"localized_size":[w,h],
          "delta_left":None if not loc else margins[0],"delta_right":None if not loc else margins[1],
          "delta_top":None if not loc else margins[2],"delta_bottom":None if not loc else margins[3],
          "containment":"PASS" if loc and min(margins)>=0 else "FAIL",
          "size_ceiling":"PASS" if loc and w<=x1-x0 and h<=y1-y0 else "FAIL",
          "positive_margin":"HIGH_RISK_EDGE_TOUCH" if edge else ("PASS" if loc and min(margins)>0 else "FAIL"),
          "edge_touch_high_risk":edge
        })

    row_pass=sum(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" for r in row_reports)
    edge_count=sum(1 for r in row_reports if r["edge_touch_high_risk"])
    machine="PASS_HIGH_RISK_EDGE_TOUCH" if row_pass==len(row_reports) and outside_changed==0 and outside_alpha==0 and header_equal and edge_count else (
      "PASS" if row_pass==len(row_reports) and outside_changed==0 and outside_alpha==0 and header_equal else "FAIL"
    )
    report={
      "schema_version":2,"role":"C","run":RUN,"TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
      "queue_index":a["index"],"asset":a["asset"],"candidate_sha256":sha256(cand),"source_sha256":sha256(src_path),
      "dimensions":[cand_size[0],cand_size[1]],"header_128_exact":header_equal,"raw_orientation":"mirror_y",
      "independent_method":"Fresh decode of persisted candidate and exact pinned/source DDS; readable FLIP-Y visible-pixel diff; allowed scope is union of independently prior-C/producer-established exact source bboxes; candidate alpha is remeasured inside each selected source bbox.",
      "changed_visible_pixels_outside_all_localized_source_bboxes":outside_changed,
      "alpha_changed_pixels_outside_all_localized_source_bboxes":outside_alpha,
      "rows":row_reports,"row_summary":{"pass":row_pass,"total":len(row_reports),"edge_touch_high_risk":edge_count},
      "machine_status":machine,"controller_visual_qa":"PENDING_CONTROLLER","c3_strict_decision":"PENDING_CONTROLLER",
      "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
    }
    with open(os.path.join(OUT,"C260_"+key.upper()+"_MACHINE_QA.json"),"w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    save_full(src_raw,cand_raw,key)
    save_contacts(src,cand_r,target_rows,key)
    save_practical(src,cand_r,target_rows,key)
    batch[key]={"candidate_sha256":report["candidate_sha256"],"source_sha256":report["source_sha256"],
                "machine_status":machine,"row_summary":report["row_summary"],
                "outside_changed":outside_changed,"outside_alpha":outside_alpha,"header_128_exact":header_equal}

with open(os.path.join(OUT,"C260_BATCH_COMPUTE.json"),"w",encoding="utf-8") as f:
    json.dump({"run":RUN,"TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","assets":batch,
               "controller_visual_qa":"PENDING_CONTROLLER","runtime_validation":"UNTESTED","forbidden_domains_touched":[]},f,ensure_ascii=False,indent=2)
print(json.dumps(batch,ensure_ascii=False,indent=2))
