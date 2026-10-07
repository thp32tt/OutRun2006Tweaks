#!/usr/bin/env python3
# C258 C2 independent static QA batch for q198/q226/q228 (visible-pixel + mirror-Y correction).
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os, json, hashlib, struct, tempfile, urllib.request
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

OUT="localization/graphics/role_C/20261008-C258-C2-Q198-Q226-Q228"
os.makedirs(OUT, exist_ok=True)
SRC_BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst"

ASSETS={
"q198":{
 "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/9FC88069_1024x512.dds",
 "source_url":SRC_BASE+"/9FC88069_1024x512.dds",
 "source_sha":"2729b78176ec648039f5b45baf52b1a78e8586e6233baf9a6be4f351f5b1add4",
 "candidate_sha":"2160e7eef9dd27b028b5adc3df770a508c62891fd21676677365a0f55bee5885",
 "clean":"localization/graphics/role_C/20261005-C150-9FC88069/C150_EXACT_CLEAN_PLATE.png",
 "allowed":"localization/graphics/role_C/20261005-C150-9FC88069/C150_ALLOWED_BBOX_MASK.png",
 "source_mask":"localization/graphics/role_C/20261005-C150-9FC88069/C150_SOURCE_TEXT_MASK.png",
 "rows":[["RANDOM",[116,1922,434,1984]],["RANDOM PLAY",[548,1984,1128,2036]],["INTERMEDIATE B",[1561,43,1984,84]],["INTERMEDIATE A",[2198,43,2624,84]]]
},
"q226":{
 "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds",
 "source_url":SRC_BASE+"/E3F4BA07_512x128.dds",
 "source_sha":"fb31e9f62e0d46c4554646be2f32d70cb015e8fdbc269189bf9d76a26eab5b72",
 "candidate_sha":"5449edb846d6ca3a5de1ab1f817a41feb776e9af3bdda2175967312369e5e374",
 "clean":"localization/graphics/role_C/20261005-C143-E3F4BA07/C143_EXACT_CLEAN_PLATE.png",
 "allowed":"localization/graphics/role_C/20261005-C143-E3F4BA07/C143_ALLOWED_BBOX_MASK.png",
 "source_mask":"localization/graphics/role_C/20261005-C143-E3F4BA07/C143_SOURCE_TEXT_MASK.png",
 "rows":[["STAGE",[0,436,228,500]],["GOAL E",[980,346,1233,410]],["GOAL D",[4,262,256,326]],["GOAL C",[983,262,1234,326]],["GOAL B",[4,170,257,234]],["GOAL A",[986,170,1242,234]],["GOAL",[4,86,195,150]],["15 STAGE CONTINUOUS",[985,86,1809,150]]]
},
"q228":{
 "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds",
 "source_url":SRC_BASE+"/E7F6E9B7_512x512.dds",
 "source_sha":"3f98c940c51d2f054934d4e0b7c7d9745f9f8ad71d68548b0b336c62c1cf5154",
 "candidate_sha":"28e814599105600eb0222eb1ffe0057dc1e108520580a958ae3b3b7ec08f2808",
 "clean":"localization/graphics/role_C/20261005-C144-E7F6E9B7/C144_EXACT_CLEAN_PLATE.png",
 "allowed":"localization/graphics/role_C/20261005-C144-E7F6E9B7/C144_ALLOWED_BBOX_MASK.png",
 "source_mask":"localization/graphics/role_C/20261005-C144-E7F6E9B7/C144_SOURCE_TEXT_MASK.png",
 "rows":[["coast 2 coast",[5,26,1456,145]],["car select",[5,182,1124,301]],["license select",[6,338,1500,457]],["game lobby",[7,494,1132,644]],["main menu",[6,644,1107,769]],["multiplayer",[6,806,1195,956]],["music select",[6,956,1276,1077]],["options",[6,1114,748,1265]],["network",[6,1274,816,1424]],["rankings",[6,1424,792,1580]],["game select",[3,1580,1236,1736]],["mode select",[2,1736,1252,1861]],["race select",[6,1898,1244,2017]]]
}
}

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def load_dds(path):
    data=open(path,"rb").read()
    if data[:4] != b"DDS ": raise RuntimeError("not DDS: "+path)
    h=struct.unpack_from("<I",data,12)[0]; w=struct.unpack_from("<I",data,16)[0]
    bitcount=struct.unpack_from("<I",data,88)[0]
    masks=struct.unpack_from("<IIII",data,92)
    if bitcount != 32 or masks != (0x00ff0000,0x0000ff00,0x000000ff,0xff000000):
        raise RuntimeError("unexpected DDS RGB32 masks: "+repr((bitcount,masks)))
    pix=np.frombuffer(data,dtype=np.uint8,offset=128,count=w*h*4).reshape(h,w,4)
    return pix[:,:,[2,1,0,3]].copy(), data[:128]

def mask(path):
    im=np.array(Image.open(path).convert("RGBA"))
    m=im[:,:,3] > 0
    if not m.any(): m=im[:,:,:3].max(axis=2)>0
    return m

def bbox(m):
    ys,xs=np.where(m)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def render_rgba(a, bg=(112,112,112,255)):
    fg=Image.fromarray(a,"RGBA")
    base=Image.new("RGBA",fg.size,bg)
    return Image.alpha_composite(base,fg).convert("RGB")

def full_sheet(src,cand,key):
    cards=[]
    for title,a,b in [("RAW",src,cand),("FLIP-Y",src[::-1],cand[::-1])]:
        ia=render_rgba(a); ib=render_rgba(b)
        scale=min(1.0,900/max(ia.width,ib.width))
        if scale<1:
            size=(max(1,int(ia.width*scale)),max(1,int(ia.height*scale)))
            ia=ia.resize(size,Image.Resampling.LANCZOS); ib=ib.resize(size,Image.Resampling.LANCZOS)
        card=Image.new("RGB",(ia.width+ib.width,max(ia.height,ib.height)+24),(235,235,235))
        d=ImageDraw.Draw(card); d.text((4,4),title+" SOURCE",fill=(0,0,0)); d.text((ia.width+4,4),title+" CURRENT",fill=(0,0,0))
        card.paste(ia,(0,24)); card.paste(ib,(ia.width,24)); cards.append(card)
    out=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)),(220,220,220))
    y=0
    for c in cards: out.paste(c,(0,y)); y+=c.height
    out.save(os.path.join(OUT,"C258_"+key.upper()+"_RAW_FLIPY.jpg"),quality=88)

def contacts(src,cand,rows,key):
    cards=[]
    for name,b in rows:
        x0,y0,x1,y1=b; p=12
        xx0=max(0,x0-p); yy0=max(0,y0-p); xx1=min(src.shape[1],x1+p); yy1=min(src.shape[0],y1+p)
        ia=render_rgba(src[yy0:yy1,xx0:xx1])
        ib=render_rgba(cand[yy0:yy1,xx0:xx1])
        scale=min(3.0,1100/max(1,ia.width+ib.width))
        if scale>1:
            ia=ia.resize((int(ia.width*scale),int(ia.height*scale)),Image.Resampling.NEAREST)
            ib=ib.resize((int(ib.width*scale),int(ib.height*scale)),Image.Resampling.NEAREST)
        card=Image.new("RGB",(ia.width+ib.width,max(ia.height,ib.height)+22),(245,245,245))
        d=ImageDraw.Draw(card); d.text((4,3),name+" SOURCE",fill=(0,0,0)); d.text((ia.width+4,3),name+" CURRENT",fill=(0,0,0))
        card.paste(ia,(0,22)); card.paste(ib,(ia.width,22)); cards.append(card)
    out=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)),(225,225,225))
    y=0
    for c in cards: out.paste(c,(0,y)); y+=c.height
    out.save(os.path.join(OUT,"C258_"+key.upper()+"_CONTACTS.jpg"),quality=90)

batch={}
with tempfile.TemporaryDirectory() as td:
    for key,a in ASSETS.items():
        src_path=os.path.join(td,key+"_source.dds")
        urllib.request.urlretrieve(a["source_url"],src_path)
        if sha256(src_path)!=a["source_sha"]: raise RuntimeError(key+" source sha mismatch")
        if sha256(a["candidate"])!=a["candidate_sha"]: raise RuntimeError(key+" candidate sha mismatch")
        src,sh=load_dds(src_path); cand,ch=load_dds(a["candidate"])
        clean=np.array(Image.open(a["clean"]).convert("RGBA"))
        allowed=mask(a["allowed"]); smask=mask(a["source_mask"])
        if src.shape!=cand.shape or src.shape!=clean.shape or src.shape[:2]!=allowed.shape: raise RuntimeError(key+" shape mismatch")
        outside=~allowed
        raw_mismatch=int(np.any(src!=clean,axis=2)[outside].sum())
        flip_mismatch=int(np.any(src[::-1]!=clean,axis=2)[outside].sum())
        # ORIENTATION_POLICY: these spr_sprani_sumo_fe_cvt_Exst DDS atlases are persisted mirror-Y.
        # The exact source bboxes / clean plates from C143/C144/C150 are in readable coordinates.
        # Outside-only auto detection is ambiguous because both orientations can be identical there.
        review_orientation="FLIP_Y"; S=src[::-1]; C=cand[::-1]
        # Visible-pixel comparison: DDS may retain arbitrary hidden RGB where alpha==0.
        # Hidden RGB is not rendered and must not inflate the localized bbox or residue checks.
        adiff=C[:,:,3]!=clean[:,:,3]
        rgbdiff=np.any(C[:,:,:3]!=clean[:,:,:3],axis=2)
        visible_support=(C[:,:,3]>0)|(clean[:,:,3]>0)
        diff=adiff | (rgbdiff & visible_support)
        outside_changed=int(diff[outside].sum()); outside_alpha=int(adiff[outside].sum())
        row_reports=[]
        for name,b in a["rows"]:
            x0,y0,x1,y1=b; loc=bbox(diff[y0:y1,x0:x1])
            if loc:
                loc=[loc[0]+x0,loc[1]+y0,loc[2]+x0,loc[3]+y0]
                w=loc[2]-loc[0]; h=loc[3]-loc[1]
                margins=[loc[0]-x0,x1-loc[2],loc[1]-y0,y1-loc[3]]
            else:
                w=h=0; margins=None
            row_reports.append({"key":name,"source_bbox":b,"source_size":[x1-x0,y1-y0],"localized_bbox":loc,
                "localized_size":[w,h],"margins":margins,
                "containment":"PASS" if loc and min(margins)>=0 else "FAIL",
                "size_ceiling":"PASS" if loc and w<=x1-x0 and h<=y1-y0 else "FAIL",
                "positive_margin":"PASS" if loc and min(margins)>0 else "FAIL"})
        src_alpha=S[:,:,3]>0
        src_eq=(C[:,:,3]==S[:,:,3]) & np.all(C[:,:,:3]==S[:,:,:3],axis=2) & src_alpha
        src_clean_alpha=(S[:,:,3]!=clean[:,:,3])
        src_clean_rgb=np.any(S[:,:,:3]!=clean[:,:,:3],axis=2) & ((S[:,:,3]>0)|(clean[:,:,3]>0))
        src_clean_delta=src_clean_alpha | src_clean_rgb
        residue_diag=int((src_eq & smask & src_clean_delta).sum())
        passed=sum(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in row_reports)
        machine="PASS" if passed==len(row_reports) and outside_changed==0 and outside_alpha==0 and sh==ch else "FAIL"
        report={"schema_version":1,"role":"C","run":"20261008-C258-C2-Q198-Q226-Q228",
            "TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":int(key[1:]),
            "candidate_sha256":sha256(a["candidate"]),"source_sha256":sha256(src_path),
            "dimensions":[int(src.shape[1]),int(src.shape[0])],"header_128_exact":bool(sh==ch),
            "review_coordinate_orientation":review_orientation,
            "orientation_probe_outside_allowed":{"raw_mismatch":raw_mismatch,"flip_y_mismatch":flip_mismatch},
            "changed_pixels_outside_allowed_bboxes":outside_changed,
            "alpha_changed_pixels_outside_allowed_bboxes":outside_alpha,
            "source_exact_pixel_residue_diagnostic":residue_diag,
            "rows":row_reports,"row_summary":{"pass":passed,"total":len(row_reports)},
            "machine_status":machine,"controller_visual_qa":"PENDING_CONTROLLER",
            "c3_strict_decision":"PENDING_CONTROLLER","runtime_validation":"UNTESTED",
            "forbidden_domains_touched":[]}
        with open(os.path.join(OUT,"C258_"+key.upper()+"_MACHINE_QA.json"),"w",encoding="utf-8") as f:
            json.dump(report,f,ensure_ascii=False,indent=2)
        full_sheet(src,cand,key); contacts(S,C,a["rows"],key)
        batch[key]={"candidate_sha256":report["candidate_sha256"],"machine_status":machine,"row_summary":report["row_summary"],
                    "outside_changed":outside_changed,"outside_alpha":outside_alpha,"review_orientation":review_orientation}
with open(os.path.join(OUT,"C258_BATCH_COMPUTE.json"),"w",encoding="utf-8") as f:
    json.dump({"run":"20261008-C258-C2-Q198-Q226-Q228","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","assets":batch,
               "controller_visual_qa":"PENDING_CONTROLLER","runtime_validation":"UNTESTED"},f,ensure_ascii=False,indent=2)
print(json.dumps(batch,ensure_ascii=False,indent=2))
