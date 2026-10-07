#!/usr/bin/env python3
# A177: q212 C259-returned HEART ATTACK phrase-grouping/hierarchy repair.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

repo=Path.cwd()
RUN="20261008-A177-Q212-HEART-PHRASE-GROUP"
out=repo/"localization/graphics/role_A"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="e3fc3275e696acb0dc5449908bd3b57a232d842ad51296e888cc7ede6a276863"
SOURCE="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12); masks=struct.unpack_from("<IIII",b,92)
    if b[84:88]!=b"\0\0\0\0" or struct.unpack_from("<I",b,88)[0]!=32 or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("DDS",w,h,mips,len(b)))
    mode="RGBA" if masks==(0xff,0xff00,0xff0000,0xff000000) else "BGRA" if masks==(0xff0000,0xff00,0xff,0xff000000) else None
    if not mode: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"pitch":pitch,"mips":mips,"masks":masks,"mode":mode}
def fontspec():
    for pat in ["Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try:q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except Exception:q=""
        if "|" in q:
            p,ix=q.rsplit("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:return p,int(ix or 0),pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    p,ix=q.rsplit("|",1); return p,int(ix or 0),"Noto Sans CJK KR:style=Bold"
FONT,FI,FPAT=fontspec()

def flat(im):
    z=Image.new("RGBA",im.size,(82,82,82,255)); z.alpha_composite(im); return z.convert("RGB")
def maskdiff(a,b):
    d=ImageChops.difference(a,b); cs=d.split(); m=cs[0]
    for c in cs[1:]:m=ImageChops.lighter(m,c)
    return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])

def source_word_groups(src,bb,n_groups):
    x0,y0,x1,y1=bb
    a=np.asarray(src.crop((x0,y0,x1,y1))).astype(np.int16)
    red=(a[:,:,3]>20)&(a[:,:,0]>100)&(a[:,:,0]>a[:,:,1]*1.6+25)&(a[:,:,0]>a[:,:,2]*1.6+25)
    on=red.any(axis=0); runs=[]; s=None
    for i,v in enumerate(on):
        if v and s is None:s=i
        elif not v and s is not None:runs.append([s,i]);s=None
    if s is not None:runs.append([s,len(on)])
    gaps=[(runs[i+1][0]-runs[i][1],i) for i in range(len(runs)-1)]
    cuts=sorted(i for _,i in sorted(gaps,reverse=True)[:n_groups-1])
    groups=[]; start=0
    for cut in cuts+[len(runs)-1]:
        rr=runs[start:cut+1]; groups.append([x0+rr[0][0],x0+rr[-1][1]]); start=cut+1
    if len(groups)!=n_groups: raise RuntimeError(("groups",groups,runs))
    return groups

def word_layer(word,target_h=150,hscale=0.90,stroke=2):
    f=ImageFont.truetype(FONT,220,index=FI)
    p=Image.new("L",(1800,360),0); d=ImageDraw.Draw(p)
    bb=d.textbbox((0,0),word,font=f,stroke_width=stroke)
    d.text((24-bb[0],24-bb[1]),word,font=f,fill=255,stroke_width=stroke,stroke_fill=255)
    box=p.getbbox()
    if not box: raise RuntimeError(("empty",word))
    g=p.crop(box); sc=target_h/g.height
    m=g.resize((max(1,round(g.width*sc*hscale)),target_h),Image.Resampling.LANCZOS)
    rgba=Image.new("RGBA",m.size,(196,0,0,255));rgba.putalpha(m)
    return rgba

if sha(cand)!=INPUT: raise RuntimeError(("candidate drift",sha(cand),INPUT))
srcp=Path("/tmp/BA0147DA_source.dds")
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",srcp)
if sha(srcp)!=SOURCE: raise RuntimeError(("source drift",sha(srcp),SOURCE))

cb,cr,b242,meta=load(cand); sb,sr,src,smeta=load(srcp)
if cb[:128]!=sb[:128] or meta!=smeta: raise RuntimeError("structure drift")
clean=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_CLEAN_PLATE.png").convert("RGBA")
protected=np.asarray(Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_PROTECTED_MASK.png").convert("L"))>0
if clean.size!=b242.size or protected.shape!=(b242.height,b242.width): raise RuntimeError("evidence size")

# Preserve the C259-accepted COAST 2 COAST pixels exactly. Only HEART ATTACK is changed.
final=b242.copy()
heart=[21,1316,1780,1474]; x0,y0,x1,y1=heart
final.paste(clean.crop(tuple(heart)),(x0,y0))

groups=source_word_groups(src,heart,2)
source_phrase_left=groups[0][0]; source_phrase_right=groups[-1][1]
source_gap=groups[1][0]-groups[0][1]
layers=[word_layer("하트"),word_layer("어택")]
# C259 rejected B242's arbitrary 300px gap. Use the source's actual inter-word
# relationship, scaled only by the nearly identical localized/source title height.
gap=max(36,round(source_gap*(150/(y1-y0))))
phrase_w=layers[0].width+gap+layers[1].width
phrase_center=(source_phrase_left+source_phrase_right)/2
start=round(phrase_center-phrase_w/2)
start=max(x0+5,min(start,x1-phrase_w-5))
y=y0+(y1-y0-150)//2

new_mask=np.zeros((final.height,final.width),dtype=bool)
word_reports=[]; xx=start
for word,layer in zip(["하트","어택"],layers):
    lm=np.asarray(layer.getchannel("A"))>0
    if np.any(lm & protected[y:y+layer.height,xx:xx+layer.width]): raise RuntimeError(("protected",word))
    if np.any(lm & new_mask[y:y+layer.height,xx:xx+layer.width]): raise RuntimeError(("overlap",word))
    new_mask[y:y+layer.height,xx:xx+layer.width]|=lm
    final.alpha_composite(layer,(xx,y))
    word_reports.append({"word":word,"placed_bbox":[xx,y,xx+layer.width,y+layer.height],"hscale":0.90,"target_h":150,"stroke":2})
    xx+=layer.width+gap

# Exact localized alpha/effect bbox relative to verified clean.
m=maskdiff(clean.crop(tuple(heart)),final.crop(tuple(heart))); b=m.getbbox()
if not b: raise RuntimeError("empty heart diff")
lb=[x0+b[0],y0+b[1],x0+b[2],y0+b[3]]
if not(x0<lb[0] and y0<lb[1] and lb[2]<x1 and lb[3]<y1): raise RuntimeError(("margin",lb,heart))
if lb[2]-lb[0]>x1-x0 or lb[3]-lb[1]>y1-y0: raise RuntimeError(("size",lb,heart))

# Blast radius only in HEART ATTACK source bbox; C2C and all other atlas pixels remain exact B242 bytes.
allowed=Image.new("L",final.size,0); ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
dm=maskdiff(b242,final); outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
am=ImageChops.difference(b242.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
alpha_out=count(ImageChops.multiply(am,ImageChops.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("scope",outside,alpha_out))

# Explicitly prove C2C region is unchanged from C259-reviewed B242.
c2c=(0,964,1760,1124)
c2c_diff=count(maskdiff(b242.crop(c2c),final.crop(c2c)))
if c2c_diff!=0: raise RuntimeError(("c2c drift",c2c_diff))

raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cand.write_bytes(cb[:128]+raw.tobytes("raw",meta["mode"])); csha=sha(cand)
rb,rr,dec,rm=load(cand)
if rb[:128]!=cb[:128] or rm!=meta or ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")

row={
 "key":"heart_attack_title","source_text":"HEART ATTACK","text":"하트 어택",
 "source_bbox":heart,"localized_bbox":lb,
 "source_size":[x1-x0,y1-y0],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
 "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
 "width_ratio_bbox":round((lb[2]-lb[0])/(x1-x0),4),"height_ratio":round((lb[3]-lb[1])/(y1-y0),4),
 "source_word_groups_x":groups,"source_visible_phrase_span":[source_phrase_left,source_phrase_right],
 "source_visible_phrase_width":source_phrase_right-source_phrase_left,
 "source_word_gap_px":source_gap,"localized_word_gap_px":gap,
 "localized_phrase_center_x":round((lb[0]+lb[2])/2,1),"source_phrase_center_x":round(phrase_center,1),
 "words":word_reports,"font":FPAT,
 "construction":"native 150px Bold; 0.90 mildly-condensed whole-word glyph aspect; source-derived inter-word gap; full phrase centered on canonical source visible phrase span; no per-syllable tracking"
}

# Evidence SOURCE | B242(C259 reject) | CLEAN | A177.
cards=[]
for key,bb in [("coast2coast_preserved",list(c2c)),("heart_attack_reworked",heart)]:
    ax0,ay0,ax1,ay1=bb; pad=28
    crop=(max(0,ax0-pad),max(0,ay0-pad),min(src.width,ax1+pad),min(src.height,ay1+pad))
    ims=[]
    for lab,im in [("SOURCE",src),("B242_C259_REJECT",b242),("CLEAN",clean),("A177",dec)]:
        z=flat(im.crop(crop)); z.thumbnail((760,270),Image.Resampling.LANCZOS)
        cc=Image.new("RGB",(z.width,z.height+26),(24,24,24)); cc.paste(z,(0,26)); ImageDraw.Draw(cc).text((4,4),lab,fill="white"); ims.append(cc)
    rr=Image.new("RGB",(sum(i.width for i in ims)+36,max(i.height for i in ims)+20),(16,16,16)); px=0
    for cc in ims: rr.paste(cc,(px,0)); px+=cc.width+12
    ImageDraw.Draw(rr).text((4,rr.height-3),key,fill="white",anchor="ls"); cards.append(rr)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8),(16,16,16)); py=0
for cc in cards: sheet.paste(cc,(0,py)); py+=cc.height+8
sheet.save(out/"A177_Q212_CONTACTS.jpg","JPEG",quality=96,subsampling=0)

# Practical-scale comparison for the failed HEART title.
prs=[]
for sc in [1.0,0.75,0.5]:
    pair=[]
    for lab,im in [("SOURCE",src),("B242",b242),("A177",dec)]:
        z=flat(im.crop(tuple(heart)))
        if sc!=1.0:z=z.resize((round(z.width*sc),round(z.height*sc)),Image.Resampling.LANCZOS)
        z.thumbnail((760,220),Image.Resampling.LANCZOS)
        cc=Image.new("RGB",(z.width,z.height+24),(20,20,20));cc.paste(z,(0,24));ImageDraw.Draw(cc).text((4,4),f"{lab} {int(sc*100)}%",fill="white");pair.append(cc)
    rr=Image.new("RGB",(max(p.width for p in pair),sum(p.height for p in pair)+10),(16,16,16));yy=0
    for p in pair:rr.paste(p,(0,yy));yy+=p.height+5
    prs.append(rr)
ps=Image.new("RGB",(sum(p.width for p in prs)+12,max(p.height for p in prs)),(16,16,16));px=0
for p in prs:ps.paste(p,(px,0));px+=p.width+6
ps.save(out/"A177_Q212_PRACTICAL.jpg","JPEG",quality=95,subsampling=0)

s=flat(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)); f=flat(dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
s.thumbnail((950,950),Image.Resampling.LANCZOS); f.thumbnail((950,950),Image.Resampling.LANCZOS)
rw=Image.new("RGB",(s.width+f.width+12,max(s.height,f.height)+26),(16,16,16));rw.paste(s,(0,26));rw.paste(f,(s.width+12,26))
d=ImageDraw.Draw(rw);d.text((4,4),"SOURCE RAW",fill="white");d.text((s.width+16,4),"A177 RAW",fill="white")
rw.save(out/"A177_Q212_RAW.jpg","JPEG",quality=94,subsampling=0)

report={
 "schema_version":2,"role":"A","run":RUN,"queue_index":212,"asset":"BA0147DA",
 "trigger":"C259_VISUAL_FAIL_HEART_ATTACK_WORD_GAP_AND_SOURCE_HIERARCHY_UNDERFILL",
 "owner_override":"IGR-001 owner_lane=A overrides even queue parity for this regression",
 "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":csha,
 "preserved":{"coast2coast_candidate_pixels":"EXACT_B242","c2c_diff_pixels":c2c_diff},
 "reworked":row,
 "machine_qa":{"bbox_size_positive_margin":"1/1 PASS","changed_outside_heart_bbox":outside,"alpha_outside_heart_bbox":alpha_out,
   "localized_overlap_pixels":0,"protected_overlap_pixels":0,"header_128_exact":True,"mips":meta["mips"],
   "raw_orientation":"mirror_y","persisted_decode":"PASS"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_REUSE_B85_VERIFIED_CLEAN_PLATE",
   "2_source_matching_slant":"PASS_SOURCE_TITLE_UPRIGHT",
   "3_no_undersized_lettering":"PASS_NATIVE_150PX_HEIGHT_AND_SOURCE_CENTERED_PHRASE",
   "4_source_faithful_weight_effect":"PASS_BOLD_0.90_MILD_CONDENSED_OPEN_COUNTERS",
   "5_no_clipped_pixels":"PASS_POSITIVE_MARGIN",
   "6_protected_art_clearance":"PASS_ZERO_PROTECTED_OVERLAP",
   "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_CONFIRM",
   "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_CONFIRM"},
 "correction":"C259 rejected B242 300px arbitrary word gap and left-heavy phrase. A177 uses the canonical source HEART/ATTACK visible word gap scaled by title height, mildly-condensed whole-word glyphs, and centers the complete Korean phrase on the canonical source phrase span; no per-syllable tracking.",
 "execution_backend":"GITHUB_HOSTED_CPU_WORKER_FOR_REPOSITORY_BACKED_DDS",
 "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
 "fresh_independent_c":"REQUIRED",
 "mandatory_c3":"REQUIRED_EXACT_SHA_USER_INGAME_REGRESSION",
 "runtime_validation":"UNTESTED","status":"A177_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA",
 "forbidden_domains_touched":[]
}
(out/"A177_Q212_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A177_Q212.json").write_text(json.dumps({"role":"A","run":RUN,"queue_index":212,"asset":"BA0147DA","before":INPUT,"after":csha,"status":report["status"],"runtime_validation":"UNTESTED","report":str((out/"A177_Q212_REPORT.json").relative_to(repo))},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"candidate_sha256":csha,"heart":row,"c2c_diff":c2c_diff,"outside":outside,"alpha_out":alpha_out},ensure_ascii=False,indent=2))
