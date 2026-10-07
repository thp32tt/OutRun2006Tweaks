#!/usr/bin/env python3
import os,hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261008-A171-Q121-Q193-CLEAN-PLATE"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def dmask(a,b):
    d=ImageChops.difference(a,b); cs=d.split(); m=cs[0]
    for q in cs[1:]: m=ImageChops.lighter(m,q)
    return bmask(m)
def count(m): return sum(m.histogram()[1:])
def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not dds",p))
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if b[84:88]!=b"\0\0\0\0" or bpp!=32 or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported DDS",p,w,h,mips,bpp,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"pitch":pitch,"mips":mips,"mode":mode,"masks":masks}
def write_dds(p,header,readable,meta):
    raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    Path(p).write_bytes(header[:128]+raw.tobytes("raw",meta["mode"]))
def flat(im,bg=(86,86,86,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def fontspec():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
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

def shear(mask,k):
    pad=max(12,int(mask.height*abs(k))+12)
    c=Image.new("L",(mask.width+pad*2,mask.height),0); c.paste(mask,(pad,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,k,0,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=o.getbbox(); return o.crop(bb) if bb else o
def shift(m,dx,dy):
    o=Image.new("L",m.size,0)
    sx0=max(0,-dx); sy0=max(0,-dy); sx1=m.width-max(0,dx); sy1=m.height-max(0,dy)
    if sx1>sx0 and sy1>sy0:o.paste(m.crop((sx0,sy0,sx1,sy1)),(max(0,dx),max(0,dy)))
    return o
def render_fd(text,fs=108,k=.28):
    f=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=f)
    pad=28; m=Image.new("L",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),0)
    ImageDraw.Draw(m).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
    m=shear(m,k); m=m.crop(m.getbbox())
    outer=m.filter(ImageFilter.MaxFilter(11)); inner=m.filter(ImageFilter.MaxFilter(5)); sh=shift(outer,7,8)
    z=Image.new("RGBA",outer.size,(0,0,0,0))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(18,18,20,190)),Image.new("RGBA",outer.size,(0,0,0,0)),sh))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(42,42,48,255)),Image.new("RGBA",outer.size,(0,0,0,0)),outer))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(218,218,220,255)),Image.new("RGBA",outer.size,(0,0,0,0)),inner))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(252,252,250,255)),Image.new("RGBA",outer.size,(0,0,0,0)),m))
    return z.crop(z.getchannel("A").getbbox())

def dominant_gray(crop):
    a=np.asarray(crop)
    rgb=a[:,:,:3].astype(np.int16); al=a[:,:,3]
    lum=rgb.mean(axis=2)
    gray=(np.max(rgb,axis=2)-np.min(rgb,axis=2)<=6)&(lum>60)&(lum<210)&(al>220)
    vals=a[gray]
    if len(vals)<100:
        border=np.concatenate([a[:4].reshape(-1,4),a[-4:].reshape(-1,4),a[:, :4].reshape(-1,4),a[:, -4:].reshape(-1,4)],axis=0)
        vals=border[border[:,3]>220]
    if len(vals)==0: raise RuntimeError("no plate samples")
    med=np.median(vals,axis=0).astype(np.uint8)
    return tuple(int(x) for x in med)

def render_flat(text,fill,desired_fs,maxw,maxh):
    for fs in range(desired_fs,16,-1):
        f=ImageFont.truetype(FONT,fs,index=FI)
        d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=f,stroke_width=0)
        pad=8; m=Image.new("L",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),0)
        ImageDraw.Draw(m).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
        box=m.getbbox()
        if not box: continue
        m=m.crop(box)
        if m.width<=maxw and m.height<=maxh:
            z=Image.new("RGBA",m.size,fill); z.putalpha(m)
            return z,fs
    raise RuntimeError(("flat fit",text,maxw,maxh))

def build_contacts(name,src,old,clean,final,rows):
    cards=[]
    for r in rows:
        x0,y0,x1,y1=r["source_bbox"]; pad=26
        crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
        ims=[]
        for lab,im in [("SOURCE",src),("PRIOR",old),("CLEAN",clean),("A171",final)]:
            z=flat(im.crop(crop)); scale=min(1.0,720/max(1,z.width))
            if scale<1:z=z.resize((max(1,int(z.width*scale)),max(1,int(z.height*scale))),Image.Resampling.LANCZOS)
            c=Image.new("RGB",(z.width,z.height+24),(24,24,24)); c.paste(z,(0,24)); ImageDraw.Draw(c).text((4,4),lab,fill="white"); ims.append(c)
        row=Image.new("RGB",(sum(i.width for i in ims)+12*3,max(i.height for i in ims)+18),(16,16,16)); xx=0
        for c in ims: row.paste(c,(xx,0)); xx+=c.width+12
        ImageDraw.Draw(row).text((4,row.height-2),r["key"],fill="white",anchor="ls"); cards.append(row)
    sh=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8*(len(cards)-1)),(16,16,16)); yy=0
    for c in cards: sh.paste(c,(0,yy)); yy+=c.height+8
    sh.save(out/f"A171_{name}_CONTACTS.jpg","JPEG",quality=96,subsampling=0)
    s=flat(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)); f=flat(final.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
    s.thumbnail((1000,1000),Image.Resampling.LANCZOS); f.thumbnail((1000,1000),Image.Resampling.LANCZOS)
    rw=Image.new("RGB",(s.width+f.width+12,max(s.height,f.height)+26),(16,16,16)); rw.paste(s,(0,26)); rw.paste(f,(s.width+12,26))
    dr=ImageDraw.Draw(rw); dr.text((4,4),"SOURCE RAW",fill="white"); dr.text((s.width+16,4),"A171 RAW",fill="white")
    rw.save(out/f"A171_{name}_RAW.jpg","JPEG",quality=94,subsampling=0)

# ---------------- q121 FD90AA9 ----------------
q121_rel="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
q121_src=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/q121_rel
q121_cand=repo/"localization/graphics/hd_candidates"/q121_rel
Q121_INPUT="03271f4a84d5d69a162debc6490fa04f839487e4c9b03cbdcc64e66856dd1433"
Q121_SOURCE="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
if sha(q121_cand)!=Q121_INPUT: raise RuntimeError(("q121 candidate drift",sha(q121_cand),Q121_INPUT))
if sha(q121_src)!=Q121_SOURCE: raise RuntimeError(("q121 source drift",sha(q121_src),Q121_SOURCE))
sb,sr,src,m=load_dds(q121_src); cb,cr,old,cm=load_dds(q121_cand)
if cb[:128]!=sb[:128] or cm!=m: raise RuntimeError("q121 structure drift")
q121_cfg=[
 ("select_game_mode","게임 모드 선택",[166,819,1166,973]),
 ("select_car","차량 선택",[243,947,1156,1111]),
 ("select_course","코스 선택",[302,1062,1085,1213]),
]
clean=old.copy(); final=old.copy(); allowed=Image.new("L",old.size,0); rec=[]
for key,text,bb in q121_cfg:
    x0,y0,x1,y1=bb; ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
    plate=dominant_gray(src.crop(tuple(bb)))
    patch=Image.new("RGBA",(x1-x0,y1-y0),plate)
    clean.paste(patch,(x0,y0)); final.paste(patch,(x0,y0))
    layer=render_fd(text,108,.28)
    if layer.width>=x1-x0-8 or layer.height>=y1-y0-8: raise RuntimeError(("q121 fit",key,layer.size,bb))
    tx=x0+(x1-x0-layer.width)//2; ty=y0+(y1-y0-layer.height)//2
    final.alpha_composite(layer,(tx,ty))
    loc=[tx,ty,tx+layer.width,ty+layer.height]
    if not(x0<loc[0] and y0<loc[1] and loc[2]<x1 and loc[3]<y1): raise RuntimeError(("q121 margin",key,loc,bb))
    rec.append({"key":key,"text":text,"source_bbox":bb,"localized_bbox":loc,"source_size":[x1-x0,y1-y0],"localized_size":[layer.width,layer.height],"plate_rgba":plate,"font":FPAT,"font_size":108,"shear":.28,"result":"PASS"})
diff=dmask(old,final); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
ad=bmask(ImageChops.difference(old.getchannel("A"),final.getchannel("A"))); alpha_out=count(ImageChops.multiply(ad,ImageOps.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("q121 scope",outside,alpha_out))
write_dds(q121_cand,cb,final,cm); q121_sha=sha(q121_cand)
rb,rr,dec,rm=load_dds(q121_cand)
if rb[:128]!=cb[:128] or rm!=cm or ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("q121 roundtrip")
build_contacts("Q121_FD90AA9",src,old,clean,dec,rec)
clean.save(out/"A171_Q121_FD90AA9_CLEAN.png")
q121_report={"schema_version":2,"role":"A","run":run,"queue_index":121,"asset":"FD90AA9","regressions":["IGR-018","C255_VISIBLE_ENGLISH_SOURCE_RESIDUE_DOUBLE_DRAW"],"input_candidate_sha256":Q121_INPUT,"candidate_sha256":q121_sha,"source_sha256":Q121_SOURCE,"rows":rec,"construction":"rebuild each exact source header bbox to source-matched flat gray plate before fresh native Korean render; no old Korean bitmap reuse","machine_qa":{"bbox_size_positive_margin":"3/3 PASS","changed_outside":outside,"alpha_outside":alpha_out,"header_128_exact":True,"persisted_decode":"PASS","raw_orientation":"mirror_y"},"controller_visual_qa":"PENDING","runtime_validation":"UNTESTED","status":"A171_Q121_MACHINE_PASS_PENDING_CONTROLLER_VISUAL","forbidden_domains_touched":[]}
(out/"A171_Q121_FD90AA9_REPORT.json").write_text(json.dumps(q121_report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

# ---------------- q193 97E863AD ----------------
q193_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds"
q193_cand=repo/"localization/graphics/hd_candidates"/q193_rel
Q193_INPUT="f1c68aa4211e81fae2444e4d0172a06709cd5dd98e8f85deba68bbce73ce7c69"
Q193_SOURCE="d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451"
if sha(q193_cand)!=Q193_INPUT: raise RuntimeError(("q193 candidate drift",sha(q193_cand),Q193_INPUT))
srcp=Path("/tmp/97E863AD_source.dds")
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds",srcp)
if sha(srcp)!=Q193_SOURCE: raise RuntimeError(("q193 source drift",sha(srcp),Q193_SOURCE))
sb,sr,src,m=load_dds(srcp); cb,cr,old,cm=load_dds(q193_cand)
if cb[:128]!=sb[:128] or cm!=m: raise RuntimeError("q193 structure drift")
q193_cfg=[
 ("welcome","환영합니다",[3,148,476,195],48),
 ("multiplayer_intro_title","멀티플레이",[8,297,540,359],60),
 ("showroom_body","쇼룸",[1205,957,1594,1011],55),
]
clean=old.copy(); final=old.copy(); allowed=Image.new("L",old.size,0); rec=[]
for key,text,bb,fs0 in q193_cfg:
    x0,y0,x1,y1=bb; ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
    # Canonical source rows sit on transparent atlas background; clear the full exact source text bbox.
    clean.paste(Image.new("RGBA",(x1-x0,y1-y0),(0,0,0,0)),(x0,y0))
    final.paste(Image.new("RGBA",(x1-x0,y1-y0),(0,0,0,0)),(x0,y0))
    sc=np.asarray(src.crop(tuple(bb)))
    vis=sc[sc[:,:,3]>32]
    if len(vis)==0: raise RuntimeError(("q193 no source visible",key))
    fill=tuple(int(x) for x in np.median(vis,axis=0).astype(np.uint8)); fill=(fill[0],fill[1],fill[2],255)
    layer,fs=render_flat(text,fill,fs0,x1-x0-4,y1-y0-4)
    tx=x0+2; ty=y0+(y1-y0-layer.height)//2
    final.alpha_composite(layer,(tx,ty))
    loc=[tx,ty,tx+layer.width,ty+layer.height]
    if not(x0<loc[0] and y0<loc[1] and loc[2]<x1 and loc[3]<y1): raise RuntimeError(("q193 margin",key,loc,bb))
    rec.append({"key":key,"text":text,"source_bbox":bb,"localized_bbox":loc,"source_size":[x1-x0,y1-y0],"localized_size":[layer.width,layer.height],"fill_rgba":fill,"font":FPAT,"font_size":fs,"alignment":"left","result":"PASS"})
diff=dmask(old,final); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
ad=bmask(ImageChops.difference(old.getchannel("A"),final.getchannel("A"))); alpha_out=count(ImageChops.multiply(ad,ImageOps.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("q193 scope",outside,alpha_out))
write_dds(q193_cand,cb,final,cm); q193_sha=sha(q193_cand)
rb,rr,dec,rm=load_dds(q193_cand)
if rb[:128]!=cb[:128] or rm!=cm or ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("q193 roundtrip")
build_contacts("Q193_97E863AD",src,old,clean,dec,rec)
clean.save(out/"A171_Q193_97E863AD_CLEAN.png")
q193_report={"schema_version":2,"role":"A","run":run,"queue_index":193,"asset":"97E863AD","regressions":["IGR-003","IGR-019","C255_VISIBLE_ENGLISH_SOURCE_RESIDUE_DOUBLE_DRAW"],"input_candidate_sha256":Q193_INPUT,"candidate_sha256":q193_sha,"source_sha256":Q193_SOURCE,"rows":rec,"construction":"clear each exact canonical source text bbox to transparent atlas plate, then native Noto CJK dark source-color rerender; no old Korean bitmap reuse","machine_qa":{"bbox_size_positive_margin":"3/3 PASS","changed_outside":outside,"alpha_outside":alpha_out,"header_128_exact":True,"persisted_decode":"PASS","raw_orientation":"mirror_y"},"controller_visual_qa":"PENDING","runtime_validation":"UNTESTED","status":"A171_Q193_MACHINE_PASS_PENDING_CONTROLLER_VISUAL","forbidden_domains_touched":[]}
(out/"A171_Q193_97E863AD_REPORT.json").write_text(json.dumps(q193_report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

summary={"run":run,"role":"A","backend":"github_actions_fallback_after_chatgpt_local_github_dns_failure","assets":[{"index":121,"asset":"FD90AA9","before":Q121_INPUT,"after":q121_sha,"machine":"PASS"},{"index":193,"asset":"97E863AD","before":Q193_INPUT,"after":q193_sha,"machine":"PASS"}],"runtime_validation":"UNTESTED","status":"A171_BATCH_MACHINE_PASS_PENDING_CONTROLLER_VISUAL"}
(out/"A171_BATCH_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A171_Q121_Q193.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
