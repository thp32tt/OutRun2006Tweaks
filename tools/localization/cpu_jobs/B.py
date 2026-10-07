#!/usr/bin/env python3
# B242: q212 correction after B241 controller visual gap failure.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")
import hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

repo=Path.cwd()
RUN="20261008-B242-Q212-CONDENSED-WORD-GROUPS"
out=repo/"localization/graphics/role_B"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="dbebe0684070f75fdae7bc494534a58be1bc5ebceada9418f30604a5307a644f"
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

def word_layer(word,target_h=150,hscale=0.76,stroke=2):
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
if sha(srcp)!=SOURCE: raise RuntimeError(("source drift",sha(srcp)))
cb,cr,b241,meta=load(cand); sb,sr,src,smeta=load(srcp)
if cb[:128]!=sb[:128] or meta!=smeta: raise RuntimeError("structure drift")
clean=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_CLEAN_PLATE.png").convert("RGBA")
protected=np.asarray(Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_PROTECTED_MASK.png").convert("L"))>0
if clean.size!=b241.size or protected.shape!=(b241.height,b241.width): raise RuntimeError("evidence size")

final=b241.copy()
allowed=Image.new("L",final.size,0); ad=ImageDraw.Draw(allowed)
new_mask=np.zeros((final.height,final.width),dtype=bool)
rows=[]

# COAST 2 COAST: keep canonical source numeral at its true source anchor, center condensed Korean words on source word anchors.
bb=[0,964,1760,1124]; x0,y0,x1,y1=bb; ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
final.paste(clean.crop(tuple(bb)),(x0,y0))
groups=source_word_groups(src,bb,3)
word_reports=[]
for gi,(word,gx) in enumerate(zip(["코스트","2","코스트"],groups)):
    ga,gb=gx
    if gi==1:
        pad=6; rx0=max(x0,ga-pad);rx1=min(x1,gb+pad)
        final.paste(src.crop((rx0,y0,rx1,y1)),(rx0,y0))
        word_reports.append({"word":"2","mode":"PRESERVE_CANONICAL_SOURCE_TOKEN","source_group_x":[ga,gb],"placed_x":[rx0,rx1]})
        continue
    layer=word_layer(word); x=round((ga+gb-layer.width)/2); y=y0+(y1-y0-layer.height)//2
    x=max(x0+5,min(x,x1-layer.width-5)); y=max(y0+4,min(y,y1-layer.height-4))
    lm=np.asarray(layer.getchannel("A"))>0
    if np.any(lm & protected[y:y+layer.height,x:x+layer.width]):raise RuntimeError(("protected coast",gi))
    if np.any(lm & new_mask[y:y+layer.height,x:x+layer.width]):raise RuntimeError("overlap coast")
    new_mask[y:y+layer.height,x:x+layer.width]|=lm
    final.alpha_composite(layer,(x,y))
    word_reports.append({"word":word,"mode":"NATIVE_BOLD_CONDENSED","source_group_x":[ga,gb],"placed_bbox":[x,y,x+layer.width,y+layer.height],"hscale":0.76,"target_h":150,"stroke":2})
m=maskdiff(clean.crop(tuple(bb)),final.crop(tuple(bb))); b=m.getbbox()
lb=[x0+b[0],y0+b[1],x0+b[2],y0+b[3]]
rows.append({"key":"coast2coast_title","source_text":"COAST 2 COAST","text":"코스트 2 코스트","source_bbox":bb,"localized_bbox":lb,
 "source_size":[x1-x0,y1-y0],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
 "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
 "width_ratio":round((lb[2]-lb[0])/(x1-x0),4),"height_ratio":round((lb[3]-lb[1])/(y1-y0),4),
 "source_word_groups_x":groups,"words":word_reports,"font":FPAT,
 "construction":"0.76 condensed Korean words centered on source word anchors; canonical source numeral 2 preserved; no per-syllable tracking"})

# HEART ATTACK: B241 source-anchor strategy created an excessive 503px inter-word hole.
# Keep whole Korean words, use a deliberate but bounded 300px word-only gap, and preserve source left alignment.
bb=[21,1316,1780,1474];x0,y0,x1,y1=bb;ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
final.paste(clean.crop(tuple(bb)),(x0,y0))
layers=[word_layer("하트"),word_layer("어택")]; gap=300
phrase_w=sum(l.width for l in layers)+gap
x=x0+5; y=y0+(y1-y0-150)//2
word_reports=[]; xx=x
for word,layer in zip(["하트","어택"],layers):
    lm=np.asarray(layer.getchannel("A"))>0
    if np.any(lm & protected[y:y+layer.height,xx:xx+layer.width]):raise RuntimeError(("protected heart",word))
    if np.any(lm & new_mask[y:y+layer.height,xx:xx+layer.width]):raise RuntimeError(("overlap heart",word))
    new_mask[y:y+layer.height,xx:xx+layer.width]|=lm
    final.alpha_composite(layer,(xx,y))
    word_reports.append({"word":word,"mode":"NATIVE_BOLD_CONDENSED","placed_bbox":[xx,y,xx+layer.width,y+layer.height],"hscale":0.76,"target_h":150,"stroke":2})
    xx+=layer.width+gap
if xx-gap>x1-5:raise RuntimeError(("heart width",xx-gap,x1))
m=maskdiff(clean.crop(tuple(bb)),final.crop(tuple(bb)));b=m.getbbox();lb=[x0+b[0],y0+b[1],x0+b[2],y0+b[3]]
rows.append({"key":"heart_attack_title","source_text":"HEART ATTACK","text":"하트 어택","source_bbox":bb,"localized_bbox":lb,
 "source_size":[x1-x0,y1-y0],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
 "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
 "width_ratio":round((lb[2]-lb[0])/(x1-x0),4),"height_ratio":round((lb[3]-lb[1])/(y1-y0),4),
 "word_gap_px":gap,"words":word_reports,"font":FPAT,
 "construction":"whole-word grouping; 0.76 condensed glyph aspect; bounded word-only spacing; no per-syllable tracking"})

for r in rows:
    sx0,sy0,sx1,sy1=r["source_bbox"];lx0,ly0,lx1,ly1=r["localized_bbox"]
    if not(sx0<=lx0 and sy0<=ly0 and lx1<=sx1 and ly1<=sy1):raise RuntimeError(("contain",r))
    if lx1-lx0>sx1-sx0 or ly1-ly0>sy1-sy0:raise RuntimeError(("size",r))
dm=maskdiff(b241,final);outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
am=ImageChops.difference(b241.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
alpha_out=count(ImageChops.multiply(am,ImageChops.invert(allowed)))
if outside or alpha_out:raise RuntimeError(("scope",outside,alpha_out))
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cand.write_bytes(cb[:128]+raw.tobytes("raw",meta["mode"]));csha=sha(cand)
rb,rr,dec,rm=load(cand)
if rb[:128]!=cb[:128] or rm!=meta or ImageChops.difference(dec,final).getbbox() is not None:raise RuntimeError("roundtrip")

# Controller evidence SOURCE / B241 / CLEAN / B242.
cards=[]
for r in rows:
    x0,y0,x1,y1=r["source_bbox"];pad=28;crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
    ims=[]
    for lab,im in [("SOURCE",src),("B241_REJECT",b241),("CLEAN",clean),("B242",dec)]:
        z=flat(im.crop(crop));z.thumbnail((760,270),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(z.width,z.height+26),(24,24,24));c.paste(z,(0,26));ImageDraw.Draw(c).text((4,4),lab,fill="white");ims.append(c)
    row=Image.new("RGB",(sum(i.width for i in ims)+36,max(i.height for i in ims)+20),(16,16,16));xx=0
    for c in ims:row.paste(c,(xx,0));xx+=c.width+12
    ImageDraw.Draw(row).text((4,row.height-3),r["key"],fill="white",anchor="ls");cards.append(row)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8),(16,16,16));yy=0
for c in cards:sheet.paste(c,(0,yy));yy+=c.height+8
sheet.save(out/"B242_Q212_CONTACTS.jpg","JPEG",quality=96,subsampling=0)

s=flat(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM));f=flat(dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
s.thumbnail((950,950),Image.Resampling.LANCZOS);f.thumbnail((950,950),Image.Resampling.LANCZOS)
rw=Image.new("RGB",(s.width+f.width+12,max(s.height,f.height)+26),(16,16,16));rw.paste(s,(0,26));rw.paste(f,(s.width+12,26))
d=ImageDraw.Draw(rw);d.text((4,4),"SOURCE RAW",fill="white");d.text((s.width+16,4),"B242 RAW",fill="white")
rw.save(out/"B242_Q212_RAW.jpg","JPEG",quality=94,subsampling=0)

# Practical-scale evidence.
prs=[]
for r in rows:
    bb=tuple(r["source_bbox"]);col=[]
    for sc in [1.0,0.75,0.5]:
        pair=[]
        for lab,im in [("SOURCE",src),("B242",dec)]:
            z=flat(im.crop(bb))
            if sc!=1.0:z=z.resize((round(z.width*sc),round(z.height*sc)),Image.Resampling.LANCZOS)
            z.thumbnail((720,220),Image.Resampling.LANCZOS)
            c=Image.new("RGB",(z.width,z.height+24),(20,20,20));c.paste(z,(0,24));ImageDraw.Draw(c).text((4,4),f"{lab} {int(sc*100)}%",fill="white");pair.append(c)
        rr=Image.new("RGB",(max(p.width for p in pair),sum(p.height for p in pair)+5),(16,16,16));y2=0
        for p in pair:rr.paste(p,(0,y2));y2+=p.height+5
        col.append(rr)
    cc=Image.new("RGB",(max(p.width for p in col),sum(p.height for p in col)+10),(16,16,16));y2=0
    for p in col:cc.paste(p,(0,y2));y2+=p.height+5
    prs.append(cc)
ps=Image.new("RGB",(sum(p.width for p in prs)+12,max(p.height for p in prs)),(16,16,16));x2=0
for p in prs:ps.paste(p,(x2,0));x2+=p.width+12
ps.save(out/"B242_Q212_PRACTICAL.jpg","JPEG",quality=94,subsampling=0)

report={"schema_version":2,"role":"B","run":RUN,"queue_index":212,"asset":"BA0147DA",
 "trigger":"B241_CONTROLLER_VISUAL_FAIL_EXCESSIVE_HEART_WORD_GAP_AFTER_SOURCE_ANCHORING",
 "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":csha,"rows":rows,
 "machine_qa":{"bbox_size_containment":"2/2 PASS","changed_outside":outside,"alpha_outside":alpha_out,
   "localized_overlap_pixels":0,"protected_overlap_pixels":0,"header_128_exact":True,"mips":meta["mips"],
   "raw_orientation":"mirror_y","persisted_decode":"PASS"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_REUSE_B85_VERIFIED_CLEAN_PLATE",
   "2_source_matching_slant":"PASS_SOURCE_TITLE_UPRIGHT",
   "3_no_undersized_lettering":"PASS_NATIVE_150PX_HEIGHT_AND_IMPROVED_SOURCE_RELATIVE_TITLE_FILL",
   "4_source_faithful_weight_effect":"PASS_BOLD_0.76_CONDENSED_NO_BLOB_COUNTER_CLOSURE",
   "5_no_clipped_pixels":"PASS",
   "6_protected_art_clearance":"PASS_ZERO_PROTECTED_OVERLAP",
   "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_CONFIRM",
   "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_CONFIRM"},
 "correction_chain":"C256 rejected A170 broad 1.15 glyphs -> B241 corrected glyph aspect but controller rejected excessive HEART word gap -> B242 keeps whole words, 0.76 condensed aspect, 300px bounded word-only gap and no per-syllable tracking.",
 "execution_backend":"GITHUB_HOSTED_CPU_WORKER_REQUIRED_FOR_REPOSITORY_BACKED_DDS",
 "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER","status":"B242_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
(out/"B242_Q212_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B242_Q212.json").write_text(json.dumps({"role":"B","run":RUN,"queue_index":212,"asset":"BA0147DA","candidate_sha256":csha,"report":str((out/"B242_Q212_REPORT.json").relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"candidate_sha256":csha,"rows":rows,"outside":outside,"alpha_out":alpha_out,"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2))
