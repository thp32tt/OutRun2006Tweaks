#!/usr/bin/env python3
# C253 C1 fresh independent QA batch: q147/q197/q241
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import hashlib, io, json, os, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

OUT=Path("localization/graphics/role_C/20261007-C253-C1-BATCH-Q147-Q197-Q241")
OUT.mkdir(parents=True,exist_ok=True)
PIN="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"

def H(b): return hashlib.sha256(b).hexdigest()
def git_blob(path, want):
    for c in subprocess.check_output(["git","rev-list","HEAD","--",path],text=True).splitlines():
        try: b=subprocess.check_output(["git","show",f"{c}:{path}"])
        except subprocess.CalledProcessError: continue
        if H(b)==want: return b, f"git-history:{c}"
    return None, None

def get_source(a):
    rel=a["asset"].replace("textures/load/","",1)
    hd=Path("localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a")/a["asset"]
    if hd.exists():
        b=hd.read_bytes()
        if H(b)==a["source_sha"]: return b, str(hd)
    b,prov=git_blob(a["candidate"],a["source_sha"])
    if b is not None: return b,prov
    url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{PIN}/Release/{rel}"
    try:
        with urllib.request.urlopen(url,timeout=90) as r: b=r.read()
        if H(b)==a["source_sha"]: return b, f"Sonic-TV/OR2006Sprites@{PIN}:Release/{rel}"
    except Exception:
        pass
    raise RuntimeError(f"canonical source unavailable or hash mismatch q{a['index']}")

def get_prior(a):
    b,prov=git_blob(a["candidate"],a["prior_sha"])
    if b is None: raise RuntimeError(f"prior blob unavailable q{a['index']} {a['prior_sha']}")
    return b,prov

def dec(b):
    with Image.open(io.BytesIO(b)) as im: return im.convert("RGBA")
def readable(b): return ImageOps.flip(dec(b))

def rectmask(shape,rects):
    m=np.zeros(shape,bool)
    for x0,y0,x1,y1 in rects:
        x0=max(0,int(x0));y0=max(0,int(y0));x1=min(shape[1],int(x1));y1=min(shape[0],int(y1))
        m[y0:y1,x0:x1]=True
    return m

def fit(im,maxw=720,maxh=520):
    im=im.convert("RGB"); s=min(maxw/im.width,maxh/im.height,1.0)
    return im if s>=1 else im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.Resampling.LANCZOS)

def triptych(src,prior,cur,path,title):
    ims=[fit(x) for x in (src,prior,cur)]
    W=sum(x.width for x in ims)+24*2; H=max(x.height for x in ims)+50
    o=Image.new("RGB",(W,H),(24,24,24)); d=ImageDraw.Draw(o); xx=0
    for lab,im in zip(["SOURCE","PRIOR","CURRENT"],ims):
        d.text((xx+4,5),lab,fill="white"); o.paste(im,(xx,26)); xx+=im.width+24
    d.text((5,H-5),title,fill="white",anchor="ls")
    o.save(path,quality=92,subsampling=0,optimize=True)

def contacts(src,prior,cur,rows,path):
    cards=[]
    for r in rows:
        x0,y0,x1,y1=r["source_bbox"]; p=28
        box=(max(0,x0-p),max(0,y0-p),min(src.width,x1+p),min(src.height,y1+p))
        ims=[fit(x.crop(box),430,180) for x in (src,prior,cur)]
        W=sum(i.width for i in ims)+12*2; H=max(i.height for i in ims)+42
        o=Image.new("RGB",(W,H),(34,34,34)); d=ImageDraw.Draw(o); xx=0
        for lab,im in zip(["SRC","PRIOR","CUR"],ims):
            d.text((xx+2,2),lab,fill="white"); o.paste(im,(xx,22)); xx+=im.width+12
        d.text((4,H-4),r["key"],fill="white",anchor="ls"); cards.append(o)
    W=max(x.width for x in cards); H=sum(x.height for x in cards)+8*(len(cards)-1)
    out=Image.new("RGB",(W,H),(18,18,18)); yy=0
    for c in cards: out.paste(c,(0,yy)); yy+=c.height+8
    out.save(path,quality=94,subsampling=0,optimize=True)

ASSETS=[
{
 "index":147,"key":"39BCA907",
 "asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/39BCA907_512x256.dds",
 "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/39BCA907_512x256.dds",
 "candidate_sha":"ab002e4f172ebe72b593914b92661c4f8137d50f8b073a22005fd175cff0153e",
 "prior_sha":"6f59084b340a2a2bc56bd72b276c4cd264aaabfb7e76b013fe190a8f9cb0417b",
 "source_sha":"b913c9670288f7b67be514ddb4bc7eaba97fe70e0e640ba744429bbb4e5625a5",
 "trigger":"PRE_INGAME #014 forced-width Hangul distortion; A156 natural-aspect height-driven rerender",
 "mandatory_c3":True,
 "rows":[
  {"key":"TULIP_GARDEN","source_bbox":[3,811,502,874],"localized_bbox":[5,813,239,872]},
  {"key":"SNOW_MOUNTAIN","source_bbox":[981,813,1576,876],"localized_bbox":[983,815,1270,874]},
  {"key":"PALM_BEACH","source_bbox":[0,724,439,786],"localized_bbox":[2,726,170,784]},
  {"key":"METROPOLIS","source_bbox":[985,723,1422,786],"localized_bbox":[987,725,1319,784]},
  {"key":"INDUSTRIAL_COMPLEX","source_bbox":[8,635,790,698],"localized_bbox":[10,637,581,696]},
  {"key":"IMPERIAL_AVENUE","source_bbox":[986,639,1630,701],"localized_bbox":[988,641,1377,699]},
  {"key":"GHOST_FOREST","source_bbox":[11,551,517,613],"localized_bbox":[13,553,411,611]},
  {"key":"DESERT","source_bbox":[981,547,1260,610],"localized_bbox":[983,549,1146,608]},
  {"key":"DEEP_LAKE","source_bbox":[6,466,401,528],"localized_bbox":[8,468,236,526]},
  {"key":"CONIFEROUS_FOREST","source_bbox":[980,457,1731,522],"localized_bbox":[982,459,1514,520]},
  {"key":"CLOUDY_HIGHLAND","source_bbox":[3,373,675,438],"localized_bbox":[5,375,479,436]},
  {"key":"CASTLE_WALL","source_bbox":[980,371,1485,437],"localized_bbox":[982,373,1166,435]},
  {"key":"CAPE_WAY","source_bbox":[0,285,375,350],"localized_bbox":[2,287,297,348]},
  {"key":"ANCIENT_RUINS","source_bbox":[982,285,1554,350],"localized_bbox":[984,287,1400,348]},
  {"key":"ALPINE","source_bbox":[6,194,282,256],"localized_bbox":[8,196,167,254]}
 ]
},
{
 "index":197,"key":"9F060EC1",
 "asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/9F060EC1_512x512.dds",
 "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/9F060EC1_512x512.dds",
 "candidate_sha":"60cfa3ef1257e3bbc50a8c7152aba538837eabd2322c18e098ee7ceb61381fea",
 "prior_sha":"39d917ca74552a86b459d1110ddcc351a07705e078d75160aabae49c7de20a60",
 "source_sha":"177e3be8f3a8fd4d0482bcf1849cbe333cef6f86486afbc4ca6307ec417c2e05",
 "trigger":"historical C85 zero-pixel false-negative; A164R exact-bbox and clean-plate repair",
 "mandatory_c3":True,
 "rows":[
  {"key":"license","source_bbox":[41,1285,625,1347],"localized_bbox":[43,1287,446,1345],"old_bbox":[25,1270,496,1339]},
  {"key":"complete","source_bbox":[399,1561,679,1608],"localized_bbox":[401,1564,525,1604],"old_bbox":[398,1558,546,1607]},
  {"key":"vs_rank","source_bbox":[397,1652,625,1699],"localized_bbox":[399,1655,550,1695],"old_bbox":[398,1651,574,1697]},
  {"key":"win_ratio","source_bbox":[398,1742,677,1789],"localized_bbox":[400,1745,487,1785],"old_bbox":[399,1741,503,1789]},
  {"key":"drive_time","source_bbox":[400,1834,708,1879],"localized_bbox":[402,1836,576,1877],"old_bbox":[399,1832,607,1881]}
 ]
},
{
 "index":241,"key":"E1639D2E",
 "asset":"textures/load/spr_sprani_sumo_loading_Exst/E1639D2E_256x64.dds",
 "candidate":"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_loading_Exst/E1639D2E_256x64.dds",
 "candidate_sha":"b94f215b889231a7942299d6a2179540425d11538df21feb25565cac13bab037",
 "prior_sha":"fe9bb931d94a13a44a08bcf61b6325c01080b462afff84f92c97205cbe0eea65",
 "source_sha":"e250a41e7c59ccd5b8a68a02aace066f6578fbe0d84a365d7a0a27044b353511",
 "trigger":"PRE_INGAME #062 Loading hierarchy undersize; A146 native-HD hierarchy rework",
 "mandatory_c3":True,
 "rows":[
  {"key":"loading","source_bbox":[1,110,731,256],"localized_bbox":[9,116,413,250]},
  {"key":"please_wait","source_bbox":[4,50,375,98],"localized_bbox":[6,52,163,96]}
 ]
}
]

summary={"schema_version":1,"role":"C","run":"C253","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
         "execution_backend":"github-actions independent repository-backed pixel QA after ChatGPT-local GitHub DNS failure",
         "assets":[],"runtime_validation":"UNTESTED","forbidden_domains_touched":[]}

for a in ASSETS:
    cb=Path(a["candidate"]).read_bytes()
    if H(cb)!=a["candidate_sha"]: raise RuntimeError(("candidate drift",a["index"],H(cb),a["candidate_sha"]))
    pb,pprov=get_prior(a)
    sb,sprov=get_source(a)
    cur,prior,src=readable(cb),readable(pb),readable(sb)
    if cur.size!=prior.size or cur.size!=src.size:
        raise RuntimeError(("dimension mismatch",a["index"],src.size,prior.size,cur.size))
    ca,pa=np.array(cur),np.array(prior)
    changed=np.any(ca!=pa,axis=2); ach=ca[:,:,3]!=pa[:,:,3]
    allowed=[]
    for r in a["rows"]:
        allowed.append(r["source_bbox"])
        if "old_bbox" in r: allowed.append(r["old_bbox"])
    am=rectmask(changed.shape,allowed)
    outside=int((changed&~am).sum()); alpha_outside=int((ach&~am).sum())
    if outside or alpha_outside:
        raise RuntimeError(("blast radius fail",a["index"],outside,alpha_outside))
    geom=[]
    for r in a["rows"]:
        s=r["source_bbox"]; l=r["localized_bbox"]
        sw,sh=s[2]-s[0],s[3]-s[1]; lw,lh=l[2]-l[0],l[3]-l[1]
        margins=[l[0]-s[0],s[2]-l[2],l[1]-s[1],s[3]-l[3]]
        ok=(lw<=sw and lh<=sh and min(margins)>0)
        if not ok: raise RuntimeError(("bbox/size/margin fail",a["index"],r["key"],margins))
        geom.append({"key":r["key"],"source_bbox":s,"localized_bbox":l,
                     "source_size":[sw,sh],"localized_size":[lw,lh],"margins":margins,
                     "width_ratio":round(lw/sw,4),"height_ratio":round(lh/sh,4),"result":"PASS"})
    if cb[:128]!=pb[:128] or cb[:128]!=sb[:128]:
        raise RuntimeError(("DDS header mismatch",a["index"]))
    raw_cur,raw_prior,raw_src=dec(cb),dec(pb),dec(sb)
    triptych(src,prior,cur,OUT/f'C253_q{a["index"]:03d}_{a["key"]}_FLIPY.jpg',f'q{a["index"]} readable FLIP-Y | {a["trigger"]}')
    triptych(raw_src,raw_prior,raw_cur,OUT/f'C253_q{a["index"]:03d}_{a["key"]}_RAW.jpg',f'q{a["index"]} RAW DDS')
    contacts(src,prior,cur,a["rows"],OUT/f'C253_q{a["index"]:03d}_{a["key"]}_CONTACTS.jpg')
    rep={
      "schema_version":1,"role":"C","run":"C253","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
      "queue_index":a["index"],"asset":a["asset"],"asset_key":a["key"],"trigger":a["trigger"],
      "candidate_sha256":H(cb),"prior_candidate_sha256":H(pb),"canonical_source_sha256":H(sb),
      "prior_provenance":pprov,"source_provenance":sprov,
      "independent_machine_qa":{
        "dimensions":list(cur.size),"header_128_exact_source_prior_current":True,
        "prior_to_current_changed_pixels":int(changed.sum()),
        "prior_to_current_changed_outside_declared_rework_union":outside,
        "prior_to_current_alpha_changed_outside_declared_rework_union":alpha_outside,
        "bbox_size_positive_margin":f'{len(geom)}/{len(geom)} PASS',
        "regions":geom
      },
      "visual_evidence":[f'C253_q{a["index"]:03d}_{a["key"]}_FLIPY.jpg',
                         f'C253_q{a["index"]:03d}_{a["key"]}_RAW.jpg',
                         f'C253_q{a["index"]:03d}_{a["key"]}_CONTACTS.jpg'],
      "verified_clean_plate_evidence":{
        "q147":"producer A156_SOURCE_CLEAN_FINAL; C controller must re-open before verdict",
        "q197":"producer A164R_SOURCE_OLD_CLEAN_FINAL; C controller must re-open before verdict",
        "q241":"producer E1639D2E_HD_CLEAN_PLATE + A146 validation; C controller must re-open before verdict"
      }.get("q"+str(a["index"])),
      "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
      "mandatory_c3_strict_audit":a["mandatory_c3"],
      "c3_strict_audit":"PENDING_CONTROLLER_REVIEW",
      "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
    }
    (OUT/f'C253_q{a["index"]:03d}_{a["key"]}_MACHINE_QA.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary["assets"].append({"index":a["index"],"key":a["key"],"candidate_sha256":H(cb),
                              "machine_qa":"PASS","controller_visual_qa":"PENDING","c3":"PENDING"})

(OUT/"C253_BATCH_MACHINE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
