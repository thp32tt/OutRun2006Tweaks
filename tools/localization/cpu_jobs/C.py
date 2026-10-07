#!/usr/bin/env python3
# C252 C1 fresh independent QA batch: q63/q121/q193
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import hashlib, io, json, os, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
OUT=Path("localization/graphics/role_C/20261007-C252-C1-BATCH-Q063-Q121-Q193");OUT.mkdir(parents=True,exist_ok=True)

def H(b): return hashlib.sha256(b).hexdigest()
def find_blob(path,want):
    for c in subprocess.check_output(["git","rev-list","HEAD","--",path],text=True).splitlines():
        try:b=subprocess.check_output(["git","show",f"{c}:{path}"])
        except subprocess.CalledProcessError:continue
        if H(b)==want:return b,c
    raise RuntimeError(f"historical blob not found {path} {want}")
def dec(b):
    with Image.open(io.BytesIO(b)) as im:return im.convert("RGBA")
def rd(b):return ImageOps.flip(dec(b))
def mask(shape,rows):
    m=np.zeros(shape,bool)
    for r in rows:
        x0,y0,x1,y1=r["source_bbox"];m[y0:y1,x0:x1]=1
    return m
def fit(im,maxw=900,maxh=700):
    im=im.convert("RGB");s=min(maxw/im.width,maxh/im.height,1)
    return im if s==1 else im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.Resampling.LANCZOS)
def overview(src,prior,cur,path,title):
    ims=[fit(x) for x in (src,prior,cur)];W=sum(x.width for x in ims)+20*2;H=max(x.height for x in ims)+42
    o=Image.new("RGB",(W,H),(25,25,25));d=ImageDraw.Draw(o);x=0
    for lab,im in zip(["SOURCE","PRIOR","CURRENT"],ims):d.text((x+3,4),lab,fill="white");o.paste(im,(x,28));x+=im.width+20
    d.text((4,H-3),title,fill="white",anchor="ls");o.save(path,quality=91,subsampling=0,optimize=True)
def contacts(src,prior,cur,rows,path):
    cards=[]
    for r in rows:
        x0,y0,x1,y1=r["source_bbox"];p=24;box=(max(0,x0-p),max(0,y0-p),min(src.width,x1+p),min(src.height,y1+p))
        ims=[fit(x.crop(box),650,260) for x in (src,prior,cur)]
        W=sum(x.width for x in ims)+12*2;H=max(x.height for x in ims)+38
        o=Image.new("RGB",(W,H),(38,38,38));d=ImageDraw.Draw(o);xx=0
        for lab,im in zip(["SRC","PRIOR","CUR"],ims):d.text((xx+2,2),lab,fill="white");o.paste(im,(xx,22));xx+=im.width+12
        d.text((4,H-3),r["key"],fill="white",anchor="ls");cards.append(o)
    W=max(x.width for x in cards);H=sum(x.height for x in cards)+8*(len(cards)-1);o=Image.new("RGB",(W,H),(18,18,18));y=0
    for c in cards:o.paste(c,(0,y));y+=c.height+8
    o.save(path,quality=94,subsampling=0,optimize=True)

AS=[
{"index":63,"key":"48DEBE77","candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_loading_cvt_Exst/48DEBE77_512x512.dds","candidate_sha":"f92629621d421e924a3f1b9d77252c551832824110e755325bcf0bf4a1af2ad0","prior_sha":"a6161cfaedb9ab83c311b3aa78cf3ae3e18ca333fc52e1e31a8d6055e21797ea","source_path":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_loading_cvt_Exst/48DEBE77_512x512.dds","source_sha":"5f6cc66875fd2c03678f7c893ae242eacd0bda6e56ee8d0b2a56e7578895e635","regression":"IGR-012 P0 START/GOAL residue/slant/layout","rows":[
{"key":"start_top","source_bbox":[124,502,348,566],"localized_bbox":[176,504,295,564]},
{"key":"start_bottom","source_bbox":[124,1540,348,1596],"localized_bbox":[184,1542,287,1594]},
{"key":"goal","source_bbox":[1650,26,1802,62],"localized_bbox":[1710,28,1741,60]}]},
{"index":121,"key":"FD90AA9","candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds","candidate_sha":"03271f4a84d5d69a162debc6490fa04f839487e4c9b03cbdcc64e66856dd1433","prior_sha":"3d000de4c8c88645f4f50deb388e2538a00154783a1db4b848f15f7e7bf86894","source_path":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds","source_sha":"f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e","regression":"IGR-018 P1 header ghost/low-res/style/slant","rows":[
{"key":"select_game_mode","source_bbox":[166,819,1166,973],"localized_bbox":[341,846,990,945]},
{"key":"select_car","source_bbox":[243,947,1156,1111],"localized_bbox":[485,979,913,1078]},
{"key":"select_course","source_bbox":[302,1062,1085,1213],"localized_bbox":[478,1088,908,1187]}]},
{"index":193,"key":"97E863AD","candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds","candidate_sha":"f1c68aa4211e81fae2444e4d0172a06709cd5dd98e8f85deba68bbce73ce7c69","prior_sha":"b17c26ad47611de67365449d2fed5cd4d17114cb3d4eb3fcd8cd373afacf8d1d","source_sha":"d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451","regression":"IGR-003 + IGR-019 P1 low-res showroom/multiplayer body","rows":[
{"key":"welcome","source_bbox":[3,148,476,195],"localized_bbox":[5,150,202,193]},
{"key":"multiplayer_intro_title","source_bbox":[8,297,540,359],"localized_bbox":[10,300,274,356]},
{"key":"showroom_body","source_bbox":[1205,957,1594,1011],"localized_bbox":[1207,959,1302,1009]}]}
]

summary={"schema_version":1,"role":"C","run":"C252","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)","execution_backend":"github-actions fallback: ChatGPT local git ls-remote failed DNS resolution; N100 not used","assets":[]}
for a in AS:
    cb=Path(a["candidate"]).read_bytes()
    if H(cb)!=a["candidate_sha"]:raise RuntimeError(("candidate drift",a["index"],H(cb)))
    pb,pcommit=find_blob(a["candidate"],a["prior_sha"])
    if "source_path" in a:
        sb=Path(a["source_path"]).read_bytes()
        if H(sb)!=a["source_sha"]:raise RuntimeError(("source drift",a["index"],H(sb)))
        scommit="current hd_source"
    else:
        sb,scommit=find_blob(a["candidate"],a["source_sha"])
    cur,prior,src=rd(cb),rd(pb),rd(sb)
    source_display_scale=1
    if cur.size!=prior.size: raise RuntimeError(("candidate/prior size mismatch",a["index"],prior.size,cur.size))
    if src.size!=cur.size:
        if cur.width%src.width or cur.height%src.height or cur.width//src.width!=cur.height//src.height:
            raise RuntimeError(("non-integer source display scale",a["index"],src.size,cur.size))
        source_display_scale=cur.width//src.width
        src=src.resize(cur.size,Image.Resampling.NEAREST)
    ca,pa=np.array(cur),np.array(prior); ch=np.any(ca!=pa,axis=2); ach=ca[:,:,3]!=pa[:,:,3]
    allow=mask(ch.shape,a["rows"]);outside=int((ch&~allow).sum());aout=int((ach&~allow).sum())
    if outside or aout:raise RuntimeError(("blast radius",a["index"],outside,aout))
    geom=[]
    for r in a["rows"]:
        sbx=r["source_bbox"];lbx=r["localized_bbox"]
        sw,sh=sbx[2]-sbx[0],sbx[3]-sbx[1];lw,lh=lbx[2]-lbx[0],lbx[3]-lbx[1]
        mg=[lbx[0]-sbx[0],sbx[2]-lbx[2],lbx[1]-sbx[1],sbx[3]-lbx[3]]
        ok=lw<=sw and lh<=sh and min(mg)>0
        if not ok:raise RuntimeError(("bbox",a["index"],r["key"],mg))
        geom.append({"key":r["key"],"source_bbox":sbx,"localized_bbox":lbx,"source_size":[sw,sh],"localized_size":[lw,lh],"margins":mg,"width_ratio":round(lw/sw,4),"height_ratio":round(lh/sh,4),"result":"PASS"})
    if cb[:128]!=pb[:128]:raise RuntimeError(("candidate/prior header mismatch",a["index"]))
    source_header_exact=(source_display_scale==1 and cb[:128]==sb[:128])
    overview(src,prior,cur,OUT/f'C252_q{a["index"]:03d}_{a["key"]}_FLIPY.jpg',f'q{a["index"]} readable FLIP-Y {a["regression"]}')
    overview(dec(sb),dec(pb),dec(cb),OUT/f'C252_q{a["index"]:03d}_{a["key"]}_RAW.jpg',f'q{a["index"]} RAW DDS')
    contacts(src,prior,cur,a["rows"],OUT/f'C252_q{a["index"]:03d}_{a["key"]}_CONTACTS.jpg')
    rep={"schema_version":1,"role":"C","run":"C252","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)","queue_index":a["index"],"asset_key":a["key"],"regression":a["regression"],"candidate_sha256":H(cb),"prior_candidate_sha256":H(pb),"canonical_source_sha256":H(sb),"prior_blob_commit":pcommit,"source_blob_commit":scommit,"independent_machine_qa":{"dimensions":list(cur.size),"canonical_source_native_dimensions":list(dec(sb).size),"source_display_scale_nearest_neighbor":source_display_scale,"header_128_exact_candidate_prior":True,"header_128_exact_source_when_same_native_dimensions":source_header_exact,"prior_to_current_changed_pixels":int(ch.sum()),"prior_to_current_changed_outside_declared_rework_union":outside,"prior_to_current_alpha_changed_outside_declared_rework_union":aout,"bbox_size_positive_margin":f'{len(geom)}/{len(geom)} PASS',"regions":geom},"visual_evidence":[f'C252_q{a["index"]:03d}_{a["key"]}_FLIPY.jpg',f'C252_q{a["index"]:03d}_{a["key"]}_RAW.jpg',f'C252_q{a["index"]:03d}_{a["key"]}_CONTACTS.jpg'],"controller_visual_qa":"PENDING","c3_strict_audit":"PENDING","runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
    (OUT/f'C252_q{a["index"]:03d}_{a["key"]}_MACHINE_QA.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary["assets"].append({"index":a["index"],"key":a["key"],"candidate_sha256":H(cb),"machine_qa":"PASS","controller_visual_qa":"PENDING","c3":"PENDING"})
(OUT/"C252_BATCH_MACHINE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
