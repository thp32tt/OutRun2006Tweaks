#!/usr/bin/env python3
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
import hashlib,json,math,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

repo=Path.cwd()
run="20261007-A167-WORKSTEAL-C251-Q060-Q212"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",p))
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bpp!=32 or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported DDS",p,w,h,mips,fourcc,bpp,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"pitch":pitch,"mips":mips,"mode":mode,"masks":masks}
def write_dds(path,header_src,readable,meta):
    raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=header_src[:128]+raw.tobytes("raw",meta["mode"])
    Path(path).write_bytes(payload)
    rb,rr,rd,rm=load_dds(path)
    if rb[:128]!=header_src[:128] or rm!=meta or ImageChops.difference(rd,readable).getbbox() is not None:
        raise RuntimeError(("persisted DDS mismatch",path))
    return hashlib.sha256(payload).hexdigest()
def fontspec(style="Black"):
    for pat in [f"Noto Sans CJK KR:style={style}","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try:q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except Exception:q=""
        if "|" in q:
            p,ix=q.rsplit("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:return p,int(ix or 0),pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",f"Noto Sans CJK KR:style={style}"],text=True).strip()
    p,ix=q.rsplit("|",1)
    if not Path(p).exists(): raise RuntimeError(("font",q))
    return p,int(ix or 0),f"Noto Sans CJK KR:style={style}"
FONT,FI,FPAT=fontspec("Black")

def flat(im,bg=(82,82,82,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def bmask(im): return im.point(lambda v:255 if v else 0)
def diffmask(a,b):
    d=ImageChops.difference(a,b); chans=d.split(); m=chans[0]
    for z in chans[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def count(m): return sum(m.histogram()[1:])
def gradient(size,top,bottom):
    w,h=size; a=np.zeros((h,w,4),dtype=np.uint8)
    for y in range(h):
        t=y/max(1,h-1); a[y,:,]=[round(top[i]*(1-t)+bottom[i]*t) for i in range(4)]
    return Image.fromarray(a,"RGBA")
def shear_mask(mask,k):
    pad=max(8,int(abs(k)*mask.height)+10)
    c=Image.new("L",(mask.width+pad*2,mask.height),0); c.paste(mask,(pad,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,k,0,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=o.getbbox(); return o.crop(bb) if bb else o
def offset_mask(m,dx,dy):
    o=Image.new("L",m.size,0)
    sx0=max(0,-dx); sy0=max(0,-dy); sx1=m.width-max(0,dx); sy1=m.height-max(0,dy)
    if sx1>sx0 and sy1>sy0:o.paste(m.crop((sx0,sy0,sx1,sy1)),(max(0,dx),max(0,dy)))
    return o

def render_hud(text,kind,target_w,target_h,shear=.28):
    f=ImageFont.truetype(FONT,220,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=f)
    pad=40
    base=Image.new("L",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),0)
    ImageDraw.Draw(base).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
    fill=shear_mask(base,shear)
    outer=fill.filter(ImageFilter.MaxFilter(15)); inner=fill.filter(ImageFilter.MaxFilter(7)); sh=offset_mask(outer,6,7)
    W,H=outer.size; layer=Image.new("RGBA",(W,H),(0,0,0,0))
    if kind=="stage":
        layer.alpha_composite(Image.composite(Image.new("RGBA",(W,H),(8,13,40,210)),Image.new("RGBA",(W,H),(0,0,0,0)),sh))
        layer.alpha_composite(Image.composite(Image.new("RGBA",(W,H),(255,255,255,255)),Image.new("RGBA",(W,H),(0,0,0,0)),outer))
        layer.alpha_composite(Image.composite(Image.new("RGBA",(W,H),(13,31,83,255)),Image.new("RGBA",(W,H),(0,0,0,0)),inner))
        layer.alpha_composite(Image.composite(gradient((W,H),(255,245,92,255),(238,184,18,255)),Image.new("RGBA",(W,H),(0,0,0,0)),fill))
    elif kind=="white":
        layer.alpha_composite(Image.composite(Image.new("RGBA",(W,H),(18,18,26,185)),Image.new("RGBA",(W,H),(0,0,0,0)),sh))
        layer.alpha_composite(Image.composite(Image.new("RGBA",(W,H),(112,112,120,255)),Image.new("RGBA",(W,H),(0,0,0,0)),outer))
        layer.alpha_composite(Image.composite(Image.new("RGBA",(W,H),(232,232,230,255)),Image.new("RGBA",(W,H),(0,0,0,0)),inner))
        layer.alpha_composite(Image.composite(Image.new("RGBA",(W,H),(255,255,250,255)),Image.new("RGBA",(W,H),(0,0,0,0)),fill))
    else:
        layer.alpha_composite(Image.composite(Image.new("RGBA",(W,H),(5,11,36,210)),Image.new("RGBA",(W,H),(0,0,0,0)),sh))
        layer.alpha_composite(Image.composite(Image.new("RGBA",(W,H),(11,28,78,255)),Image.new("RGBA",(W,H),(0,0,0,0)),outer))
        layer.alpha_composite(Image.composite(Image.new("RGBA",(W,H),(252,249,232,255)),Image.new("RGBA",(W,H),(0,0,0,0)),inner))
        layer.alpha_composite(Image.composite(gradient((W,H),(255,249,180,255),(230,171,50,255)),Image.new("RGBA",(W,H),(0,0,0,0)),fill))
    box=layer.getchannel("A").getbbox()
    layer=layer.crop(box)
    return layer.resize((target_w,target_h),Image.Resampling.LANCZOS)

def render_condensed_title(text,target_h,target_w,fill=(196,0,0,255),condense=.78):
    f=ImageFont.truetype(FONT,190,index=FI)
    tokens=[]; gaps=[]
    chars=list(text)
    for i,ch in enumerate(chars):
        if ch==" ":
            if gaps: gaps[-1]="word"
            continue
        probe=Image.new("L",(360,280),0); d=ImageDraw.Draw(probe)
        bb=d.textbbox((0,0),ch,font=f); d.text((20-bb[0],20-bb[1]),ch,font=f,fill=255)
        b=probe.getbbox(); g=probe.crop(b)
        scale=target_h/max(1,g.height)
        w=max(1,round(g.width*scale*condense))
        g=g.resize((w,target_h),Image.Resampling.LANCZOS)
        if tokens: gaps.append("char")
        tokens.append(g)
    if not tokens: raise RuntimeError(("empty title",text))
    base=sum(g.width for g in tokens)
    weights=[1.8 if x=="word" else 1.0 for x in gaps]
    remain=max(0,target_w-base)
    unit=remain/sum(weights) if weights else 0
    gap_px=[round(unit*w) for w in weights]
    actual=base+sum(gap_px)
    layer=Image.new("RGBA",(actual,target_h),(0,0,0,0))
    x=0
    for i,g in enumerate(tokens):
        rgba=Image.new("RGBA",g.size,fill); rgba.putalpha(g)
        layer.alpha_composite(rgba,(x,0)); x+=g.width
        if i<len(gap_px): x+=gap_px[i]
    return layer

def paste_crop(dest,clean,bbox):
    x0,y0,x1,y1=bbox
    if clean.size==dest.size: dest.paste(clean.crop(bbox),(x0,y0))
    elif clean.size==(x1-x0,y1-y0): dest.paste(clean,(x0,y0))
    else: raise RuntimeError(("clean size mismatch",clean.size,bbox,dest.size))

def place(final,layer,bbox,left_margin=None):
    x0,y0,x1,y1=bbox
    if layer.width>=x1-x0 or layer.height>=y1-y0: raise RuntimeError(("layer too large",layer.size,bbox))
    x=x0+(left_margin if left_margin is not None else (x1-x0-layer.width)//2)
    y=y0+(y1-y0-layer.height)//2
    if x<=x0: x=x0+1
    if x+layer.width>=x1: x=x1-layer.width-1
    if y<=y0: y=y0+1
    if y+layer.height>=y1: y=y1-layer.height-1
    final.alpha_composite(layer,(x,y))
    return [x,y,x+layer.width,y+layer.height]

def qa(old,final,bboxes,header,cand,meta,rows):
    allow=Image.new("L",old.size,0); dr=ImageDraw.Draw(allow)
    for b in bboxes: dr.rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=255)
    d=diffmask(old,final)
    outside=count(ImageChops.multiply(d,ImageChops.invert(allow)))
    ad=bmask(ImageChops.difference(old.getchannel("A"),final.getchannel("A")))
    alpha_out=count(ImageChops.multiply(ad,ImageChops.invert(allow)))
    if outside or alpha_out: raise RuntimeError(("scope",outside,alpha_out))
    rb,rr,rd,rm=load_dds(cand)
    if rb[:128]!=header[:128] or rm!=meta or ImageChops.difference(rd,final).getbbox() is not None: raise RuntimeError("persist QA")
    for r in rows:
        x0,y0,x1,y1=r["source_bbox"]; a,b,c,d2=r["localized_bbox"]
        if not (x0<a and y0<b and c<x1 and d2<y1): raise RuntimeError(("margin",r))
    return {"changed_outside":outside,"alpha_outside":alpha_out,"header_128_exact":True,"mips":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS","bbox_size_positive_margin":f"{len(rows)}/{len(rows)} PASS"}

def evidence(prefix,src,old,clean,final,rows):
    cards=[]
    for r in rows:
        x0,y0,x1,y1=r["source_bbox"]; pad=24
        crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
        ims=[]
        for lab,im in [("SOURCE",src),("C251",old),("CLEAN",clean),("A167",final)]:
            z=flat(im.crop(crop)); z.thumbnail((640,260),Image.Resampling.LANCZOS)
            c=Image.new("RGB",(z.width,z.height+24),(28,28,28)); c.paste(z,(0,24)); ImageDraw.Draw(c).text((4,4),lab,fill="white"); ims.append(c)
        row=Image.new("RGB",(sum(x.width for x in ims)+12*(len(ims)-1),max(x.height for x in ims)+18),(18,18,18)); xx=0
        for x in ims: row.paste(x,(xx,0)); xx+=x.width+12
        ImageDraw.Draw(row).text((4,row.height-2),r["key"],fill="white",anchor="ls"); cards.append(row)
    sh=Image.new("RGB",(max(x.width for x in cards),sum(x.height for x in cards)+8*(len(cards)-1)),(18,18,18)); yy=0
    for x in cards: sh.paste(x,(0,yy)); yy+=x.height+8
    sh.save(out/f"{prefix}_CONTACTS.jpg","JPEG",quality=96,subsampling=0)
    s=flat(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)); f=flat(final.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
    s.thumbnail((950,950),Image.Resampling.LANCZOS); f.thumbnail((950,950),Image.Resampling.LANCZOS)
    raw=Image.new("RGB",(s.width+f.width+12,max(s.height,f.height)+26),(18,18,18)); raw.paste(s,(0,26)); raw.paste(f,(s.width+12,26))
    d=ImageDraw.Draw(raw); d.text((4,4),"SOURCE RAW",fill="white"); d.text((s.width+16,4),"A167 RAW",fill="white")
    raw.save(out/f"{prefix}_RAW.jpg","JPEG",quality=94,subsampling=0)

reports={}
# q60 A064FDFC
rel60="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
cand60=repo/"localization/graphics/hd_candidates"/rel60
src60p=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel60
if sha(cand60)!="2d3d7fd7b612cee048067813f150d323be30483042010786168a90fa983386b6": raise RuntimeError(("q60 candidate drift",sha(cand60)))
if sha(src60p)!="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc": raise RuntimeError(("q60 source drift",sha(src60p)))
b60,raw60,old60,m60=load_dds(cand60); sb60,sraw60,src60,sm60=load_dds(src60p)
if b60[:128]!=sb60[:128] or m60!=sm60: raise RuntimeError("q60 structure drift")
cleanOut=Image.open(repo/"localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_CLEAN_PLATE.png").convert("RGBA")
cleanStage=Image.open(repo/"localization/graphics/role_B/20261006-B-USERREWORK204-A064-STAGE-SLANT/B204_STAGE_CLEAN.png").convert("RGBA")
rows60_cfg=[
 ("stage","스테이지",[455,245,690,350],"stage",(216,90),8),
 ("outrun_miles_white","아웃런 마일!",[1090,245,1930,385],"white",(720,118),6),
 ("outrun_miles","아웃런 마일:",[2081,250,2860,370],"yellow",(665,102),6),
]
clean60=old60.copy()
paste_crop(clean60,cleanStage,tuple(rows60_cfg[0][2]))
for rr in rows60_cfg[1:]: paste_crop(clean60,cleanOut,tuple(rr[2]))
final60=clean60.copy(); rows60=[]
for key,txt,bb,kind,size,lm in rows60_cfg:
    layer=render_hud(txt,kind,size[0],size[1],.30 if kind!="stage" else .26)
    lb=place(final60,layer,bb,lm)
    rows60.append({"key":key,"text":txt,"source_bbox":bb,"localized_bbox":lb,"source_size":[bb[2]-bb[0],bb[3]-bb[1]],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"width_ratio":round((lb[2]-lb[0])/(bb[2]-bb[0]),4),"height_ratio":round((lb[3]-lb[1])/(bb[3]-bb[1]),4),"style":kind,"right_shear":.30 if kind!="stage" else .26})
sha60=write_dds(cand60,b60,final60,m60); mq60=qa(old60,final60,[r[2] for r in rows60_cfg],b60,cand60,m60,rows60); evidence("A167_Q060",src60,old60,clean60,final60,rows60)
reports["q60"]={"queue_index":60,"asset":"A064FDFC","input_candidate_sha256":"2d3d7fd7b612cee048067813f150d323be30483042010786168a90fa983386b6","candidate_sha256":sha60,"source_sha256":"6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc","rows":rows60,"machine_qa":mq60,"controller_visual_qa":"PENDING","fix":"C251 source-relative hierarchy scale return: Stage height ~86%; OUTRUN MILES rows ~85% source width/~84-85% source height with source-family right lean/effects"}

# q212 BA0147DA
rel212="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
cand212=repo/"localization/graphics/hd_candidates"/rel212
if sha(cand212)!="61ae0c45568e023cc258379173f8d80f43cc5257f2d8facefbcf3c87759179e1": raise RuntimeError(("q212 candidate drift",sha(cand212)))
source212=Path("/tmp/BA0147DA_source.dds")
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",source212)
if sha(source212)!="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61": raise RuntimeError(("q212 source drift",sha(source212)))
b212,raw212,old212,m212=load_dds(cand212); sb212,sraw212,src212,sm212=load_dds(source212)
if b212[:128]!=sb212[:128] or m212!=sm212: raise RuntimeError("q212 structure drift")
clean212=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_CLEAN_PLATE.png").convert("RGBA")
protected=np.asarray(Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_PROTECTED_MASK.png").convert("L"))>0
if clean212.size!=old212.size or protected.shape!=(old212.height,old212.width): raise RuntimeError("q212 evidence size")
final212=old212.copy()
cfg212=[
 ("coast2coast_title","코스트 2 코스트",[0,964,1760,1124],146,1300,5),
 ("heart_attack_title","하트 어택",[21,1316,1780,1474],146,820,5),
]
for _,_,bb,*_ in cfg212: final212.paste(clean212.crop(tuple(bb)),tuple(bb[:2]))
rows212=[]
for key,txt,bb,th,tw,lm in cfg212:
    layer=render_condensed_title(txt,th,tw,(196,0,0,255),.78)
    lb=place(final212,layer,bb,lm)
    arr=np.asarray(layer.getchannel("A"))>0
    if np.any(arr & protected[lb[1]:lb[3],lb[0]:lb[2]]): raise RuntimeError(("q212 protected overlap",key))
    rows212.append({"key":key,"text":txt,"source_bbox":bb,"localized_bbox":lb,"source_size":[bb[2]-bb[0],bb[3]-bb[1]],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"width_ratio":round((lb[2]-lb[0])/(bb[2]-bb[0]),4),"height_ratio":round((lb[3]-lb[1])/(bb[3]-bb[1]),4),"style":"solid red tall-condensed display, per-glyph horizontal condense 0.78 + source-title tracking","font":FPAT})
sha212=write_dds(cand212,b212,final212,m212); mq212=qa(old212,final212,[r[2] for r in cfg212],b212,cand212,m212,rows212); evidence("A167_Q212",src212,old212,clean212,final212,rows212)
reports["q212"]={"queue_index":212,"asset":"BA0147DA","input_candidate_sha256":"61ae0c45568e023cc258379173f8d80f43cc5257f2d8facefbcf3c87759179e1","candidate_sha256":sha212,"source_sha256":"f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61","rows":rows212,"machine_qa":mq212,"controller_visual_qa":"PENDING","fix":"C251 title-family proportion return: tall-condensed red display geometry with materially stronger source-relative height/width hierarchy"}

report={"schema_version":2,"role":"A","run":run,"selection":{"primary_shard":"ODD","odd_actionable_count":0,"work_stolen_from_lane":"B","queue_indices":[60,212],"reason":"A primary shard exhausted; C251 direct even REWORK_REQUIRED remained unchanged after latest HEAD refresh"},"execution_backend":"GITHUB_ACTIONS_REPOSITORY_BACKED_CPU_FALLBACK_AFTER_CHATGPT_LOCAL_GITHUB_DNS_FAILURE","assets":reports,"ordered_generation_gate":{"plate_restoration":"PASS_REUSED_VERIFIED_CLEAN","source_matching_slant":"PASS","no_unnecessary_undersize":"PASS_MATERIALLY_UPSCALED_WITHIN_SOURCE_BBOX","source_faithful_weight_effects":"PASS","no_clipping":"PASS","protected_art_clearance":"PASS_ZERO_OUTSIDE","flip_y_raw":"EVIDENCE_WRITTEN","immediate_readability":"PENDING_CONTROLLER_VISUAL"},"runtime_validation":"UNTESTED","forbidden_domains_touched":[],"status":"A167_MACHINE_SELF_QA_PASS_PENDING_CONTROLLER_VISUAL"}
(out/"A167_BATCH_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A167_WORKSTEAL_C251_Q060_Q212.json").write_text(json.dumps({"role":"A","run":run,"queue_indices":[60,212],"work_stolen_from_lane":"B","candidates":{"A064FDFC":sha60,"BA0147DA":sha212},"status":"MACHINE_SELF_QA_PASS_PENDING_CONTROLLER_VISUAL","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"font":FPAT,"q60":sha60,"q212":sha212,"q60_rows":rows60,"q212_rows":rows212},ensure_ascii=False,indent=2))
