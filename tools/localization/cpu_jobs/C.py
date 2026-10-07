#!/usr/bin/env python3
# C261 C2 independent fresh-C batch: q102 / q062 / q024.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os, json, hashlib, tempfile, urllib.request
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

OUT="localization/graphics/role_C/20261008-C261-C2-Q102-Q062-Q024"
os.makedirs(OUT, exist_ok=True)

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def load_dds(path):
    im=Image.open(path).convert("RGBA")
    return np.array(im), open(path,"rb").read(128)

def load_rgba(path):
    return np.array(Image.open(path).convert("RGBA"))

def visible_diff(a,b):
    ad=a[:,:,3]!=b[:,:,3]
    rgb=np.any(a[:,:,:3]!=b[:,:,:3],axis=2)
    vis=(a[:,:,3]>0)|(b[:,:,3]>0)
    return ad | (rgb & vis), ad

def bbox(mask):
    ys,xs=np.where(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def composite(a,bg=(112,112,112,255)):
    fg=Image.fromarray(a.astype(np.uint8),"RGBA")
    return Image.alpha_composite(Image.new("RGBA",fg.size,bg),fg).convert("RGB")

def read_json(path):
    with open(path,"r",encoding="utf-8-sig") as f: return json.load(f)

def save_contacts(key,S,clean,C,rows):
    cards=[]
    for r in rows:
        b=r["source_bbox"]; name=r["key"]; x0,y0,x1,y1=b; p=10
        xx0=max(0,x0-p); yy0=max(0,y0-p); xx1=min(S.shape[1],x1+p); yy1=min(S.shape[0],y1+p)
        ims=[composite(S[yy0:yy1,xx0:xx1]),composite(clean[yy0:yy1,xx0:xx1]),composite(C[yy0:yy1,xx0:xx1])]
        maxw=1150
        scale=min(2.0,maxw/max(1,sum(i.width for i in ims)))
        if scale!=1:
            ims=[i.resize((max(1,int(i.width*scale)),max(1,int(i.height*scale))),Image.Resampling.NEAREST if scale>1 else Image.Resampling.LANCZOS) for i in ims]
        W=sum(i.width for i in ims); H=max(i.height for i in ims)+24
        card=Image.new("RGB",(W,H),(235,235,235)); d=ImageDraw.Draw(card)
        x=0
        for lab,im in zip(["SOURCE","CLEAN","CURRENT"],ims):
            d.text((x+3,3),name+" "+lab,fill=(0,0,0)); card.paste(im,(x,24)); x+=im.width
        cards.append(card)
    W=max(c.width for c in cards); H=sum(c.height for c in cards)
    out=Image.new("RGB",(W,H),(220,220,220)); y=0
    for c in cards: out.paste(c,(0,y)); y+=c.height
    out.save(os.path.join(OUT,f"C261_{key}_CONTACTS.jpg"),quality=90)

def save_practical(key,S,C,crop):
    x0,y0,x1,y1=crop
    a=composite(S[y0:y1,x0:x1]); b=composite(C[y0:y1,x0:x1])
    rows=[]
    for pct in [100,75,50]:
        sc=pct/100.0
        aa=a.resize((max(1,int(a.width*sc)),max(1,int(a.height*sc))),Image.Resampling.LANCZOS)
        bb=b.resize((max(1,int(b.width*sc)),max(1,int(b.height*sc))),Image.Resampling.LANCZOS)
        row=Image.new("RGB",(aa.width+bb.width,max(aa.height,bb.height)+22),(235,235,235))
        d=ImageDraw.Draw(row); d.text((3,3),f"SOURCE {pct}%",fill=(0,0,0)); d.text((aa.width+3,3),f"CURRENT {pct}%",fill=(0,0,0))
        row.paste(aa,(0,22)); row.paste(bb,(aa.width,22)); rows.append(row)
    out=Image.new("RGB",(max(x.width for x in rows),sum(x.height for x in rows)),(220,220,220)); y=0
    for r in rows: out.paste(r,(0,y)); y+=r.height
    out.save(os.path.join(OUT,f"C261_{key}_PRACTICAL.jpg"),quality=90)

def save_raw_flipy(key,src,cand):
    panels=[]
    for label,A,B in [("RAW",src,cand),("FLIP-Y",src[::-1],cand[::-1])]:
        a=composite(A); b=composite(B)
        sc=min(1.0,900/max(a.width,b.width))
        if sc<1:
            z=(max(1,int(a.width*sc)),max(1,int(a.height*sc)))
            a=a.resize(z,Image.Resampling.LANCZOS); b=b.resize(z,Image.Resampling.LANCZOS)
        p=Image.new("RGB",(a.width+b.width,max(a.height,b.height)+22),(235,235,235))
        d=ImageDraw.Draw(p); d.text((3,3),label+" SOURCE",fill=(0,0,0)); d.text((a.width+3,3),label+" CURRENT",fill=(0,0,0))
        p.paste(a,(0,22)); p.paste(b,(a.width,22)); panels.append(p)
    out=Image.new("RGB",(max(x.width for x in panels),sum(x.height for x in panels)),(220,220,220)); y=0
    for p in panels: out.paste(p,(0,y)); y+=p.height
    out.save(os.path.join(OUT,f"C261_{key}_RAW_FLIPY.jpg"),quality=88)

def analyze(key,source_path,candidate_path,clean,rows,expected_source,expected_candidate,allow_edge_keys=()):
    src,sh=load_dds(source_path); cand,ch=load_dds(candidate_path)
    if sha256(source_path)!=expected_source: raise RuntimeError(key+" source sha mismatch "+sha256(source_path))
    if sha256(candidate_path)!=expected_candidate: raise RuntimeError(key+" candidate sha mismatch "+sha256(candidate_path))
    # All three assets are persisted mirror-Y; source bboxes and clean evidence are readable coordinates.
    S=src[::-1]; C=cand[::-1]
    if clean.shape!=S.shape: raise RuntimeError(key+" clean shape mismatch")
    union=np.zeros(S.shape[:2],dtype=bool)
    row_reports=[]
    for r in rows:
        b=r["source_bbox"]; x0,y0,x1,y1=b; union[y0:y1,x0:x1]=True
        d,_=visible_diff(C[y0:y1,x0:x1],clean[y0:y1,x0:x1])
        bb=bbox(d)
        if bb:
            loc=[bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
            w=loc[2]-loc[0]; h=loc[3]-loc[1]
            m=[loc[0]-x0,x1-loc[2],loc[1]-y0,y1-loc[3]]
        else:
            loc=None; w=h=0; m=None
        edge=bool(loc and min(m)==0)
        containment=bool(loc and min(m)>=0 and w<=x1-x0 and h<=y1-y0)
        if r["key"] in allow_edge_keys and edge and containment:
            margin_state="HIGH_RISK_EDGE_TOUCH"
        else:
            margin_state="PASS" if loc and min(m)>0 else "FAIL"
        row_reports.append({
            "key":r["key"],"source_bbox":b,"source_size":[x1-x0,y1-y0],
            "localized_bbox":loc,"localized_size":[w,h],"margins":m,
            "containment":"PASS" if containment else "FAIL",
            "size_ceiling":"PASS" if loc and w<=x1-x0 and h<=y1-y0 else "FAIL",
            "positive_margin":margin_state
        })
    sd,sa=visible_diff(C,S)
    outside_changed=int(sd[~union].sum())
    outside_alpha=int(sa[~union].sum())
    hard_pass=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"] in ("PASS","HIGH_RISK_EDGE_TOUCH") for r in row_reports)
    status="PASS_HIGH_RISK_EDGE_TOUCH" if hard_pass and any(r["positive_margin"]=="HIGH_RISK_EDGE_TOUCH" for r in row_reports) and outside_changed==0 and outside_alpha==0 and sh==ch else ("PASS" if hard_pass and outside_changed==0 and outside_alpha==0 and sh==ch else "FAIL")
    return src,cand,S,C,{
      "schema_version":2,"role":"C","run":"20261008-C261-C2-Q102-Q062-Q024",
      "TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":int(key[1:]),
      "source_sha256":sha256(source_path),"candidate_sha256":sha256(candidate_path),
      "dimensions":[int(S.shape[1]),int(S.shape[0])],"header_128_exact":bool(sh==ch),
      "review_coordinate_orientation":"FLIP_Y","rows":row_reports,
      "row_summary":{"pass":sum(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"] in ("PASS","HIGH_RISK_EDGE_TOUCH") for r in row_reports),"total":len(row_reports)},
      "changed_pixels_outside_source_bbox_union":outside_changed,
      "alpha_changed_pixels_outside_source_bbox_union":outside_alpha,
      "machine_status":status,"controller_visual_qa":"PENDING_CONTROLLER",
      "c3_strict_decision":"PENDING_CONTROLLER","runtime_validation":"UNTESTED",
      "forbidden_domains_touched":[]
    }

batch={}
with tempfile.TemporaryDirectory() as td:
    # q102: A179 current candidate, exact repository HD source, C91 clean plate.
    q102_src="localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds"
    q102_cand="localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds"
    b212=read_json("localization/graphics/role_B/20261006-B-MANUALQA212-SELECTOR-SLANT/B212_571E78F3_REPORT.json")
    q102_rows=[{"key":r["key"],"source_bbox":r["source_bbox"]} for r in b212["rows"]]
    q102_clean=load_rgba("localization/graphics/role_C/20261004-1720-C91/C91_571E78F3_CLEAN_PLATE.png")
    src,cand,S,C,rep=analyze("q102",q102_src,q102_cand,q102_clean,q102_rows,
      "17ee051e59d23c741c9df428dccd3ee2f7863c19a038f02db250001f44b6c121",
      "d5ef9adb659e3013d9d3e581d89366a28599f250be1883e13c35c0f88d9338db",
      allow_edge_keys=("time_attack_mode",))
    rep["producer_binding"]="A179 exact candidate; Time Attack row intentionally preserved from B212; continuous row materially rerendered."
    with open(os.path.join(OUT,"C261_Q102_MACHINE_QA.json"),"w",encoding="utf-8") as f: json.dump(rep,f,ensure_ascii=False,indent=2)
    save_contacts("Q102",S,q102_clean,C,q102_rows); save_practical("Q102",S,C,[350,0,1650,256]); save_raw_flipy("Q102",src,cand)
    batch["q102"]={"candidate_sha256":rep["candidate_sha256"],"machine_status":rep["machine_status"],"row_summary":rep["row_summary"],"outside":rep["changed_pixels_outside_source_bbox_union"]}

    # q062: exact upstream source. Hybrid clean = A132 all-label clean with B244 authored Layer43 EASY/HARD repair.
    q62_src=os.path.join(td,"33491F83_source.dds")
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds",q62_src)
    q62_cand="localization/graphics/hd_candidates/textures/load/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
    a132=read_json("localization/graphics/role_A/20261006-A-WORKSTEAL132-33491F83-GROUP16-CLEAN/A132_33491F83_REPORT.json")
    q62_rows=[{"key":r["key"],"source_bbox":r["source_bbox"]} for r in a132["rows"]]
    q62_clean=load_rgba("localization/graphics/role_A/20261006-A-WORKSTEAL132-33491F83-GROUP16-CLEAN/A132_CLEAN_PLATE.png")
    b244_clean=load_rgba("localization/graphics/role_B/20261008-B244-Q062-PSD-L43-CLEAN/B244_Q062_CLEAN_PLATE.png")
    for k in ("easy_main","hard_main"):
        b=next(r["source_bbox"] for r in q62_rows if r["key"]==k); x0,y0,x1,y1=b
        q62_clean[y0:y1,x0:x1]=b244_clean[y0:y1,x0:x1]
    src,cand,S,C,rep=analyze("q62",q62_src,q62_cand,q62_clean,q62_rows,
      "796531b06a159745d799f66f1476b9f78c5a14fd670468f58ce5404e6ced0551",
      "fa5cd96ff30b41d563886b336ca6305e2fdb7b050b39b2bcd5a5e8c2d46d64b6")
    rep["clean_plate_basis"]="A132 verified all-label clean plate, with EASY/HARD exact source bboxes replaced by B244 PSD-authored Layer43 continuous-road clean."
    with open(os.path.join(OUT,"C261_Q062_MACHINE_QA.json"),"w",encoding="utf-8") as f: json.dump(rep,f,ensure_ascii=False,indent=2)
    save_contacts("Q062",S,q62_clean,C,q62_rows); save_practical("Q062",S,C,[50,0,1120,420]); save_raw_flipy("Q062",src,cand)
    batch["q62"]={"candidate_sha256":rep["candidate_sha256"],"machine_status":rep["machine_status"],"row_summary":rep["row_summary"],"outside":rep["changed_pixels_outside_source_bbox_union"]}

    # q024: B209 name-entry A-Z -> 2-beolsik Jamo keycaps, exact upstream source and producer clean plate.
    q24_src=os.path.join(td,"66743AA8_source.dds")
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_name_entry_xst/66743AA8_1024x1024.dds",q24_src)
    q24_cand="localization/graphics/hd_candidates/textures/load/spr_name_entry_xst/66743AA8_1024x1024.dds"
    b209=read_json("localization/graphics/role_B/20261006-B-PRODUCTION209-NAMEENTRY-JAMO-KEYCAPS/B209_JAMO_KEYCAP_REPORT.json")
    q24_rows=[{"key":r["letter"]+"_"+r["jamo"],"source_bbox":r["original_bbox"]} for r in b209["qa"]["rows"]]
    q24_clean=load_rgba("localization/graphics/role_B/20261006-B-PRODUCTION209-NAMEENTRY-JAMO-KEYCAPS/B209_CLEAN_PLATE.png")
    src,cand,S,C,rep=analyze("q24",q24_src,q24_cand,q24_clean,q24_rows,
      "8e18676ac303b07a56d81d1d21c5e025e0baf46da49b16ae9d2e411960181f73",
      "c6daaf2e7aa0bb20714e257bf47b0a99e8faee3d46bd2c1382e3a92bd7da485e")
    rep["semantic_binding"]="A-Z visual keycaps mapped to standard 2-beolsik base Jamo; digits/punctuation/END and non-target atlas remain source-exact outside the 26 source bboxes."
    with open(os.path.join(OUT,"C261_Q024_MACHINE_QA.json"),"w",encoding="utf-8") as f: json.dump(rep,f,ensure_ascii=False,indent=2)
    save_contacts("Q024",S,q24_clean,C,q24_rows); save_practical("Q024",S,C,[0,0,1024,310]); save_raw_flipy("Q024",src,cand)
    batch["q24"]={"candidate_sha256":rep["candidate_sha256"],"machine_status":rep["machine_status"],"row_summary":rep["row_summary"],"outside":rep["changed_pixels_outside_source_bbox_union"]}

with open(os.path.join(OUT,"C261_BATCH_COMPUTE.json"),"w",encoding="utf-8") as f:
    json.dump({"run":"20261008-C261-C2-Q102-Q062-Q024","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","execution_backend":"GitHub Actions because ChatGPT local github.com DNS resolution failed before materialization","assets":batch,"controller_visual_qa":"PENDING_CONTROLLER","runtime_validation":"UNTESTED"},f,ensure_ascii=False,indent=2)
print(json.dumps(batch,ensure_ascii=False,indent=2))
