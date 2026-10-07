#!/usr/bin/env python3
# retry-after-C254-head-lease
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
import hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

repo=Path.cwd()
run="20261008-A168R-Q212-TITLE-FAMILY"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="2a9f1f841cc9d05b851d8edc630b6c2d9eaea5aa14a90ec13c47a51bdf1b9a9a"
SOURCE="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12); masks=struct.unpack_from("<IIII",b,92)
    if b[84:88]!=b"\0\0\0\0" or struct.unpack_from("<I",b,88)[0]!=32 or mips!=1 or len(b)!=128+w*h*4: raise RuntimeError(("DDS",w,h,mips))
    mode="RGBA" if masks==(0xff,0xff00,0xff0000,0xff000000) else "BGRA" if masks==(0xff0000,0xff00,0xff,0xff000000) else None
    if not mode: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"pitch":pitch,"mips":mips,"masks":masks,"mode":mode}
def fontspec():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold"]:
        try:q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except Exception:q=""
        if "|" in q:
            p,ix=q.rsplit("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:return p,int(ix or 0),pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Black"],text=True).strip()
    p,ix=q.rsplit("|",1); return p,int(ix or 0),"Noto Sans CJK KR:style=Black"
FONT,FI,FPAT=fontspec()
def flat(im):
    z=Image.new("RGBA",im.size,(82,82,82,255)); z.alpha_composite(im); return z.convert("RGB")
def maskdiff(a,b):
    d=ImageChops.difference(a,b); cs=d.split(); m=cs[0]
    for c in cs[1:]:m=ImageChops.lighter(m,c)
    return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])

def word_mask(word,target_h,condense=.95):
    f=ImageFont.truetype(FONT,220,index=FI)
    p=Image.new("L",(1800,360),0); d=ImageDraw.Draw(p)
    bb=d.textbbox((0,0),word,font=f,stroke_width=10)
    d.text((24-bb[0],24-bb[1]),word,font=f,fill=255,stroke_width=10,stroke_fill=255)
    box=p.getbbox()
    if not box: raise RuntimeError(("empty word",word))
    g=p.crop(box)
    sc=target_h/g.height
    w=max(1,round(g.width*sc*condense))
    return g.resize((w,target_h),Image.Resampling.LANCZOS)

def grouped(text,target_h,word_gap):
    words=text.split(" ")
    gs=[word_mask(w,target_h) for w in words]
    w=sum(g.width for g in gs)+word_gap*(len(gs)-1)
    m=Image.new("L",(w,target_h),0); x=0
    for i,g in enumerate(gs):
        m.paste(g,(x,0),g); x+=g.width
        if i+1<len(gs):x+=word_gap
    rgba=Image.new("RGBA",m.size,(196,0,0,255)); rgba.putalpha(m)
    return rgba

if sha(cand)!=INPUT: raise RuntimeError(("candidate drift",sha(cand),INPUT))
srcp=Path("/tmp/BA0147DA_source.dds")
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",srcp)
if sha(srcp)!=SOURCE: raise RuntimeError(("source drift",sha(srcp)))
cb,cr,old,meta=load(cand); sb,sr,src,smeta=load(srcp)
if cb[:128]!=sb[:128] or meta!=smeta: raise RuntimeError("structure drift")
clean=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_CLEAN_PLATE.png").convert("RGBA")
protected=np.asarray(Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_PROTECTED_MASK.png").convert("L"))>0
if clean.size!=old.size or protected.shape!=(old.height,old.width): raise RuntimeError("evidence size")
cfg=[
 ("coast2coast_title","코스트 2 코스트",[0,964,1760,1124],150,140),
 ("heart_attack_title","하트 어택",[21,1316,1780,1474],150,220),
]
final=old.copy()
allowed=Image.new("L",old.size,0); ad=ImageDraw.Draw(allowed)
rows=[]
for key,text,bb,th,gap in cfg:
    x0,y0,x1,y1=bb; ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
    final.paste(clean.crop(tuple(bb)),(x0,y0))
    layer=grouped(text,th,gap)
    if layer.width>=x1-x0-10: raise RuntimeError(("too wide",key,layer.width,x1-x0))
    x=x0+5; y=y0+(y1-y0-layer.height)//2
    lm=np.asarray(layer.getchannel("A"))>0
    if np.any(lm & protected[y:y+layer.height,x:x+layer.width]): raise RuntimeError(("protected",key))
    final.alpha_composite(layer,(x,y))
    rows.append({"key":key,"text":text,"source_bbox":bb,"localized_bbox":[x,y,x+layer.width,y+layer.height],
      "source_size":[x1-x0,y1-y0],"localized_size":[layer.width,layer.height],
      "width_ratio":round(layer.width/(x1-x0),4),"height_ratio":round(layer.height/(y1-y0),4),
      "font":FPAT,"construction":"whole-word groups; no per-syllable tracking; horizontal glyph condense 0.95; moderately heavier source-like red title stroke; whole-word spacing only",
      "word_gap_px":gap})
dm=maskdiff(old,final); outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
am=ImageChops.difference(old.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
alpha_out=count(ImageChops.multiply(am,ImageChops.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("scope",outside,alpha_out))
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=cb[:128]+raw.tobytes("raw",meta["mode"]); cand.write_bytes(payload); csha=sha(cand)
rb,rr,dec,rm=load(cand)
if rb[:128]!=cb[:128] or rm!=meta or ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")
for r in rows:
    x0,y0,x1,y1=r["source_bbox"]; a,b,c,d=r["localized_bbox"]
    if not(x0<a and y0<b and c<x1 and d<y1):raise RuntimeError(("margin",r))
# evidence
cards=[]
for r in rows:
    x0,y0,x1,y1=r["source_bbox"]; pad=26; crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
    ims=[]
    for lab,im in [("SOURCE",src),("A168_PRIOR",old),("CLEAN",clean),("A168R",dec)]:
        z=flat(im.crop(crop)); z.thumbnail((720,260),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(z.width,z.height+24),(24,24,24));c.paste(z,(0,24));ImageDraw.Draw(c).text((4,4),lab,fill="white");ims.append(c)
    row=Image.new("RGB",(sum(i.width for i in ims)+12*3,max(i.height for i in ims)+18),(16,16,16)); xx=0
    for c in ims:row.paste(c,(xx,0));xx+=c.width+12
    ImageDraw.Draw(row).text((4,row.height-2),r["key"],fill="white",anchor="ls");cards.append(row)
sh=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8),(16,16,16)); yy=0
for c in cards:sh.paste(c,(0,yy));yy+=c.height+8
sh.save(out/"A168R_Q212_CONTACTS.jpg","JPEG",quality=96,subsampling=0)
s=flat(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)); f=flat(dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
s.thumbnail((950,950),Image.Resampling.LANCZOS);f.thumbnail((950,950),Image.Resampling.LANCZOS)
rw=Image.new("RGB",(s.width+f.width+12,max(s.height,f.height)+26),(16,16,16));rw.paste(s,(0,26));rw.paste(f,(s.width+12,26))
d=ImageDraw.Draw(rw);d.text((4,4),"SOURCE RAW",fill="white");d.text((s.width+16,4),"A168R RAW",fill="white");rw.save(out/"A168R_Q212_RAW.jpg","JPEG",quality=94,subsampling=0)
report={"schema_version":2,"role":"A","run":run,"queue_index":212,"asset":"BA0147DA","work_stolen_from_lane":"B",
 "controller_rejected_sha256":"2a9f1f841cc9d05b851d8edc630b6c2d9eaea5aa14a90ec13c47a51bdf1b9a9a","superseded_a168_sha256":INPUT,"candidate_sha256":csha,"source_sha256":SOURCE,"rows":rows,
 "machine_qa":{"bbox_size_positive_margin":"2/2 PASS","changed_outside":outside,"alpha_outside":alpha_out,"header_128_exact":True,"mips":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS"},
 "retry_reason":"A168 machine PASS was controller-rejected because 18px source-canvas stroke reinforcement visibly filled Hangul counters and harmed readability. A168R retains the improved 150px hierarchy and whole-word spacing but reduces reinforcement to 10px for source-like weight without glyph blob/closure.",
 "controller_visual_qa":"PENDING","runtime_validation":"UNTESTED","forbidden_domains_touched":[],"status":"A168R_MACHINE_PASS_PENDING_CONTROLLER_VISUAL"}
(out/"A168R_Q212_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A168R_Q212.json").write_text(json.dumps({"run":run,"queue_index":212,"asset":"BA0147DA","candidate_sha256":csha,"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"candidate_sha256":csha,"rows":rows},ensure_ascii=False,indent=2))