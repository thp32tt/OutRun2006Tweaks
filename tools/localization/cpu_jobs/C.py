#!/usr/bin/env python3
import hashlib, json, os, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261004-1920-C99"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)

SPECS=[
 dict(
  id="455717B2", producer="A_PRODUCTION10",
  report="localization/graphics/role_A/20261004-A-PRODUCTION10/A_PRODUCTION10_455717B2_REPORT.json",
  candidate="localization/graphics/hd_candidates/textures/load/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds",
  source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds",
  source_sha="ce5d3610eac8945d76a559bb7f7201f9b1efb409c965bd20ed0a26164ed7f356",
  candidate_sha="50bb8b8d0541a090e032d47d1ebc62800b559a48f5ddb22e8982c8b625b1773f",
  source_mask="localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_SOURCE_TEXT_MASK.png",
  clean="localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_CLEAN_PLATE.png"
 ),
 dict(
  id="43B07A77", producer="A_PRODUCTION12",
  report="localization/graphics/role_A/20261004-A-PRODUCTION12/A_PRODUCTION12_43B07A77_REPORT.json",
  candidate="localization/graphics/hd_candidates/textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds",
  source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds",
  source_sha="906a17ef9534bcb43d8296ae1d2ac339a53910f7113b954a52475368ab9b4175",
  candidate_sha="d2311d4c20327363bacf8b336e925e527ef8c5c8f13a385b0a2fb2e25a946cbc",
  source_mask="localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_SOURCE_TEXT_MASK.png",
  clean="localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_CLEAN_PLATE.png"
 ),
 dict(
  id="CBF8ECBF", producer="B_RECOVERY08",
  report="localization/graphics/role_B/20261004-B-RECOVERY08/B_RECOVERY08_CBF8ECBF_REPORT.json",
  candidate="localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds",
  source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds",
  source_sha="3a2a40256a6c3c945dfd4fab275edba5ec05802e4cff54f2ad93d5196cd992fe",
  candidate_sha="ecc4cbb6cdc064d2c7ccccfc378569f1dc7fc8339c46330ec68ec81c8f899df1",
  source_mask="localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_SOURCE_TEXT_MASK.png",
  clean="localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_CLEAN_PLATE.png",
  target_mask="localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_TARGET_TEXT_MASK.png"
 ),
 dict(
  id="B1696633", producer="B_RECOVERY07/C96",
  report="localization/graphics/role_B/20261004-B-RECOVERY07/B_RECOVERY07_B1696633_REPORT.json",
  candidate="localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds",
  source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds",
  source_sha="3c58bf9587d0454e5bb8733bd35c5b2613b11c7fd52c49a428f0fa5fb4cea12d",
  candidate_sha="448d4cd751461af26731028daad4835ec0a8dfcbdcdd7fb23c194478fe74df21",
  source_mask="localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_SOURCE_TEXT_MASK.png",
  clean="localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_CLEAN_PLATE.png",
  target_mask="localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_TARGET_TEXT_MASK.png"
 ),
 dict(
  id="FD90AA9", producer="A_RECOVERY08/C96",
  report="localization/graphics/role_A/20261004-A-RECOVERY07/A_RECOVERY07_FD90AA9_REPORT.json",
  override_report="localization/graphics/role_A/20261004-A-RECOVERY08/A_RECOVERY08_FD90AA9_REPORT.json",
  candidate="localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds",
  source="localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds",
  source_sha="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e",
  candidate_sha="0b7a3138c140617a90207f63eb580c18e953a241951d4832867e8e3ce184338b",
  source_mask="localization/graphics/role_A/20261004-A-RECOVERY08/FD90AA9_SOURCE_TEXT_MASK_RECOVERY08.png",
  clean="localization/graphics/role_A/20261004-A-RECOVERY08/FD90AA9_CLEAN_PLATE_RECOVERY08.png"
 )
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readable(p): return Image.open(p).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def get_source(s):
    if s.get("source"): return repo/s["source"]
    p=Path("/tmp")/(s["id"]+"_source.dds"); urllib.request.urlretrieve(s["source_url"],p); return p
def mask_img(p,size):
    im=Image.open(p).convert("L")
    if im.size!=size: raise RuntimeError(("mask size",str(p),im.size,size))
    return np.asarray(im)>0
def rgba_img(p,size):
    im=Image.open(p).convert("RGBA")
    if im.size!=size: raise RuntimeError(("image size",str(p),im.size,size))
    return im
def bbox(m):
    ys,xs=np.nonzero(m)
    if len(xs)==0:return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def crop_bbox(m,b):
    x0,y0,x1,y1=map(int,b)
    z=np.zeros_like(m); z[y0:y1,x0:x1]=m[y0:y1,x0:x1]
    return bbox(z)
def comp(im):
    bg=Image.new("RGBA",im.size,(62,62,62,255)); bg.alpha_composite(im); return bg.convert("RGB")
def make_card(im,label,maxw=660,maxh=560):
    v=comp(im); v.thumbnail((maxw,maxh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+28),"white"); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); return c
def save_rows(aid,src,clean,cand,rows):
    strips=[]
    for r in rows:
        ob=r["coarse_bbox"]; pad=8
        cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(src.width,ob[2]+pad),min(src.height,ob[3]+pad))
        cs=[]
        for tag,im in (("SOURCE",src),("CLEAN",clean),("FINAL",cand)):
            v=comp(im).crop(cr); v.thumbnail((480,160),Image.Resampling.LANCZOS)
            c=Image.new("RGB",(500,192),"white"); c.paste(v,((500-v.width)//2,26+(160-v.height)//2)); ImageDraw.Draw(c).text((4,4),f'{r["key"]} {tag}',fill="black"); cs.append(c)
        strip=Image.new("RGB",(1512,192),"white")
        for i,c in enumerate(cs): strip.paste(c,(i*506,0))
        strips.append(strip)
    sh=Image.new("RGB",(1512,192*len(strips)),"white"); y=0
    for s in strips: sh.paste(s,(0,y)); y+=192
    sh.save(out/f"C99_{aid}_EXACT_SIZE_ROWS.jpg",quality=95)

results=[]; fullcards=[]; multiline=[]
for s in SPECS:
    aid=s["id"]; srcp=get_source(s); candp=repo/s["candidate"]
    if sha(srcp)!=s["source_sha"]: raise RuntimeError((aid,"source sha",sha(srcp)))
    if sha(candp)!=s["candidate_sha"]: raise RuntimeError((aid,"candidate sha",sha(candp)))
    src=readable(srcp); cand=readable(candp); size=src.size
    clean=rgba_img(repo/s["clean"],size)
    sm=mask_img(repo/s["source_mask"],size)
    if s.get("target_mask"):
        tm=mask_img(repo/s["target_mask"],size)
    else:
        ca=np.asarray(cand,dtype=np.int16); cl=np.asarray(clean,dtype=np.int16)
        delta=np.max(np.abs(ca-cl),axis=2)
        tm=(delta>=8) & ((ca[:,:,3]>4)|(cl[:,:,3]>4))
    rep=json.loads((repo/s["report"]).read_text(encoding="utf-8"))
    rows=rep.get("rows")
    if not rows:
        if aid=="43B07A77":
            rows=[{"key":"game_over","source":rep["translation"]["source"],"korean":rep["translation"]["korean"],"original_bbox":rep["original_bbox"],"localized_bbox":rep["localized_bbox"]}]
        else: raise RuntimeError((aid,"no rows"))
    if s.get("override_report"):
        ov=json.loads((repo/s["override_report"]).read_text(encoding="utf-8"))
        by={r["key"]:r for r in ov["reworked_rows"]}
        rows=[({**r,**by[r["key"]]} if r["key"] in by else r) for r in rows]
    rowres=[]; failures=[]; holds=[]; edge=[]
    for r in rows:
        ob=[int(x) for x in r["original_bbox"]]
        sb=crop_bbox(sm,ob); tb=crop_bbox(tm,ob)
        rr={"key":r["key"],"source":r.get("source"),"korean":r.get("korean"),"coarse_bbox":ob,"source_exact_bbox":sb,"localized_exact_bbox":tb}
        if sb is None or tb is None:
            rr["exact_size_gate"]="HOLD_STRICT_RECHECK_MISSING_PIXEL_EVIDENCE"; holds.append(rr); rowres.append(rr); continue
        sw,sh=sb[2]-sb[0],sb[3]-sb[1]; lw,lh=tb[2]-tb[0],tb[3]-tb[1]
        contained=tb[0]>=sb[0] and tb[1]>=sb[1] and tb[2]<=sb[2] and tb[3]<=sb[3]
        sizeok=lw<=sw and lh<=sh
        deltas=[tb[0]-sb[0],sb[2]-tb[2],tb[1]-sb[1],sb[3]-tb[3]]
        rr.update({"source_size":[sw,sh],"localized_size":[lw,lh],"delta_size":[lw-sw,lh-sh],
                   "delta_left":deltas[0],"delta_right":deltas[1],"delta_top":deltas[2],"delta_bottom":deltas[3],
                   "exact_containment":contained,"exact_size_gate":"PASS" if contained and sizeok else "REWORK_REQUIRED"})
        if min(deltas)==0: edge.append(r["key"])
        if rr["exact_size_gate"]!="PASS": failures.append(rr)
        rowres.append(rr)
        ko=str(r.get("korean") or "")
        if "/" in ko or "\n" in ko:
            cr=(max(0,ob[0]-16),max(0,ob[1]-16),min(size[0],ob[2]+16),min(size[1],ob[3]+16))
            a=comp(src).crop(cr); b=comp(cand).crop(cr)
            cc=Image.new("RGB",(a.width+b.width+8,max(a.height,b.height)+30),"white"); cc.paste(a,(0,30)); cc.paste(b,(a.width+8,30)); ImageDraw.Draw(cc).text((4,5),f'{aid} {r.get("source")} -> {ko}',fill="black"); multiline.append(cc)
    status="PASS" if not failures and not holds else ("REWORK_REQUIRED" if failures else "HOLD_STRICT_RECHECK")
    save_rows(aid,src,clean,cand,rowres)
    a=make_card(src,aid+" SOURCE"); b=make_card(cand,aid+" FINAL"); card=Image.new("RGB",(a.width+b.width+8,max(a.height,b.height)),"white"); card.paste(a,(0,0)); card.paste(b,(a.width+8,0)); fullcards.append(card)
    results.append({"asset":aid,"producer":s["producer"],"candidate_sha256":sha(candp),"source_sha256":sha(srcp),
                    "rows_checked":len(rowres),"pass":sum(r.get("exact_size_gate")=="PASS" for r in rowres),
                    "rework_required":len(failures),"hold_strict_recheck":len(holds),"edge_touch_keys":edge,
                    "rows":rowres,"status":status,
                    "visual_evidence":{"row_contact":f"localization/graphics/role_C/{run}/C99_{aid}_EXACT_SIZE_ROWS.jpg","controller_visual_qa":"PENDING"},
                    "runtime_validation":"UNTESTED"})
W=max(c.width for c in fullcards); H=sum(c.height for c in fullcards)+8*(len(fullcards)-1); sheet=Image.new("RGB",(W,H),"white"); y=0
for c in fullcards: sheet.paste(c,(0,y)); y+=c.height+8
sheet.save(out/"C99_PENDING_AND_C96_FULL_COMPARE.jpg",quality=94)
if multiline:
    W=max(c.width for c in multiline); H=sum(c.height for c in multiline)+6*(len(multiline)-1); sheet=Image.new("RGB",(W,H),"white"); y=0
    for c in multiline: sheet.paste(c,(0,y)); y+=c.height+6
    sheet.save(out/"C99_MULTILINE_STYLE_REVIEW.jpg",quality=95)
summary={"schema_version":1,"role":"C","run":run,"base_head":os.popen("git rev-parse HEAD").read().strip(),
         "policy":"exact source glyph/effect bbox size ceiling from 8fe3425285; multi-line style controller review",
         "scope":"current pending-C assets 455717B2/43B07A77/CBF8ECBF plus C96-finalized B1696633/FD90AA9 recheck under newly introduced exact-size policy",
         "assets":results,"summary":{"assets_checked":len(results),"pass":sum(r["status"]=="PASS" for r in results),
         "rework_required":sum(r["status"]=="REWORK_REQUIRED" for r in results),"hold_strict_recheck":sum(r["status"]=="HOLD_STRICT_RECHECK" for r in results),
         "runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_changes":False}}
(out/"C99_EXACT_SIZE_POLICY_QA.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C99_DONE",[(r["asset"],r["status"],r["pass"],r["rework_required"],r["hold_strict_recheck"]) for r in results])
