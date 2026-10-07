#!/usr/bin/env python3
import os,hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261008-A173-Q121-RESTORE-PRIOR-PLATE"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
srcp=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel
cand=repo/"localization/graphics/hd_candidates"/rel
CURRENT="7a7d1e6c62dca8d699dac689fabfb4314d7f6a5f35aeac130b9a8817afccea76"
PRIOR="03271f4a84d5d69a162debc6490fa04f839487e4c9b03cbdcc64e66856dd1433"
SOURCE="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
PRIOR_COMMIT="6ec13ee0efd5a8a2895e78050e7293f58f76b2be"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def dmask(a,b):
    d=ImageChops.difference(a,b); cs=d.split(); m=cs[0]
    for q in cs[1:]:m=ImageChops.lighter(m,q)
    return bmask(m)
def count(m): return sum(m.histogram()[1:])
def load_bytes(b):
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12); masks=struct.unpack_from("<IIII",b,92)
    if b[:4]!=b"DDS " or b[84:88]!=b"\0\0\0\0" or struct.unpack_from("<I",b,88)[0]!=32 or mips!=1 or len(b)!=128+w*h*4: raise RuntimeError(("dds",w,h,mips,len(b)))
    mode="RGBA" if masks==(0xff,0xff00,0xff0000,0xff000000) else "BGRA" if masks==(0xff0000,0xff00,0xff,0xff000000) else None
    if not mode: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"pitch":pitch,"mips":mips,"mode":mode,"masks":masks}
def load(p):
    b=Path(p).read_bytes(); raw,readable,m=load_bytes(b); return b,raw,readable,m
def flat(im):
    z=Image.new("RGBA",im.size,(86,86,86,255)); z.alpha_composite(im); return z.convert("RGB")
def fontspec():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold"]:
        try:q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except Exception:q=""
        if "|" in q:
            p,ix=q.rsplit("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:return p,int(ix or 0),pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True); subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Black"],text=True).strip(); p,ix=q.rsplit("|",1); return p,int(ix or 0),"Noto Sans CJK KR:style=Black"
FONT,FI,FPAT=fontspec()
def shear(mask,k):
    pad=max(12,int(mask.height*abs(k))+12); c=Image.new("L",(mask.width+pad*2,mask.height),0); c.paste(mask,(pad,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,k,0,0,1,0),resample=Image.Resampling.BICUBIC); return o.crop(o.getbbox())
def shift(m,dx,dy):
    o=Image.new("L",m.size,0); sx0=max(0,-dx); sy0=max(0,-dy); sx1=m.width-max(0,dx); sy1=m.height-max(0,dy)
    if sx1>sx0 and sy1>sy0:o.paste(m.crop((sx0,sy0,sx1,sy1)),(max(0,dx),max(0,dy)))
    return o
def render(text,fs=108,k=.28):
    f=ImageFont.truetype(FONT,fs,index=FI); d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=f)
    pad=28; m=Image.new("L",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),0); ImageDraw.Draw(m).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
    m=shear(m,k); m=m.crop(m.getbbox()); outer=m.filter(ImageFilter.MaxFilter(11)); inner=m.filter(ImageFilter.MaxFilter(5)); sh=shift(outer,7,8)
    z=Image.new("RGBA",outer.size,(0,0,0,0))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(18,18,20,190)),Image.new("RGBA",outer.size,(0,0,0,0)),sh))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(42,42,48,255)),Image.new("RGBA",outer.size,(0,0,0,0)),outer))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(218,218,220,255)),Image.new("RGBA",outer.size,(0,0,0,0)),inner))
    z.alpha_composite(Image.composite(Image.new("RGBA",outer.size,(252,252,250,255)),Image.new("RGBA",outer.size,(0,0,0,0)),m))
    return z.crop(z.getchannel("A").getbbox())
def plate_color(crop):
    a=np.asarray(crop); rgb=a[:,:,:3].astype(np.int16); al=a[:,:,3]; lum=rgb.mean(2)
    q=(np.max(rgb,2)-np.min(rgb,2)<=6)&(lum>60)&(lum<210)&(al>220); vals=a[q]
    if len(vals)<100: raise RuntimeError("plate sample low")
    return tuple(int(x) for x in np.median(vals,axis=0).astype(np.uint8))

if sha(cand)!=CURRENT: raise RuntimeError(("current drift",sha(cand),CURRENT))
if sha(srcp)!=SOURCE: raise RuntimeError(("source drift",sha(srcp),SOURCE))
priorp=Path("/tmp/FD90AA9_prior_A138.dds")
url=f"https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/{PRIOR_COMMIT}/localization/graphics/hd_candidates/{rel}"
urllib.request.urlretrieve(url,priorp)
if sha(priorp)!=PRIOR: raise RuntimeError(("prior drift",sha(priorp),PRIOR))
sb,sr,src,m=load(srcp); cb,cr,current,cm=load(cand); pb,pr,prior,pm=load(priorp)
if cb[:128]!=sb[:128] or pb[:128]!=sb[:128] or cm!=m or pm!=m: raise RuntimeError("structure drift")
cfg=[
 ("select_game_mode","게임 모드 선택",[166,819,1166,973]),
 ("select_car","차량 선택",[243,947,1156,1111]),
 ("select_course","코스 선택",[302,1062,1085,1213]),
]
clean=prior.copy(); final=prior.copy(); allowed=Image.new("L",prior.size,0); union_rm=Image.new("L",prior.size,0); rows=[]
for key,text,bb in cfg:
    x0,y0,x1,y1=bb; ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
    plate=plate_color(src.crop(tuple(bb))); pc=np.array(plate,dtype=np.int16)
    oc=np.asarray(prior.crop(tuple(bb))).astype(np.int16); sc=np.asarray(src.crop(tuple(bb))).astype(np.int16)
    # A138 prior contains Korean plus visible English silhouettes. Remove only text/effect-like pixels from that true pre-A171 plate.
    dev_prior=np.max(np.abs(oc[:,:,:3]-pc[:3]),axis=2)>12
    dev_src=np.max(np.abs(sc[:,:,:3]-pc[:3]),axis=2)>12
    alpha_prior=np.abs(oc[:,:,3]-pc[3])>8; alpha_src=np.abs(sc[:,:,3]-pc[3])>8
    rm=(dev_prior|dev_src|alpha_prior|alpha_src)
    rm=Image.fromarray((rm*255).astype(np.uint8),"L").filter(ImageFilter.MaxFilter(5))
    patch=clean.crop(tuple(bb)); bg=Image.new("RGBA",patch.size,plate); patch.paste(bg,(0,0),rm); clean.paste(patch,(x0,y0))
    fpatch=final.crop(tuple(bb)); fpatch.paste(bg,(0,0),rm); final.paste(fpatch,(x0,y0))
    union_rm.paste(ImageChops.lighter(union_rm.crop(tuple(bb)),rm),(x0,y0))
    layer=render(text,108,.28); tx=x0+(x1-x0-layer.width)//2; ty=y0+(y1-y0-layer.height)//2
    if not(x0<tx and y0<ty and tx+layer.width<x1 and ty+layer.height<y1): raise RuntimeError(("fit",key,layer.size,bb))
    final.alpha_composite(layer,(tx,ty))
    rows.append({"key":key,"text":text,"source_bbox":bb,"localized_bbox":[tx,ty,tx+layer.width,ty+layer.height],"plate_rgba":plate,"font":FPAT,"font_size":108,"shear":.28,"removal_pixels":count(rm),"result":"PASS"})

# Critical blast-radius check is against the true A138 prior, not rejected A171/A172 bytes.
diff_prior=dmask(prior,final); outside=count(ImageChops.multiply(diff_prior,ImageOps.invert(allowed)))
ad=bmask(ImageChops.difference(prior.getchannel("A"),final.getchannel("A"))); alpha_out=count(ImageChops.multiply(ad,ImageOps.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("scope",outside,alpha_out))
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); cand.write_bytes(cb[:128]+raw.tobytes("raw",cm["mode"])); csha=sha(cand)
rb,rr,dec,rmmeta=load(cand)
if rb[:128]!=cb[:128] or rmmeta!=cm or ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")

clean.save(out/"A173_Q121_CLEAN.png"); union_rm.save(out/"A173_Q121_REMOVAL_MASK.png")
cards=[]
for r in rows:
    x0,y0,x1,y1=r["source_bbox"]; pad=26; crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
    ims=[]
    for lab,im in [("SOURCE",src),("A138_PRIOR",prior),("A173_CLEAN",clean),("A173",dec)]:
        z=flat(im.crop(crop)); scale=min(1.0,720/max(1,z.width))
        if scale<1:z=z.resize((max(1,int(z.width*scale)),max(1,int(z.height*scale))),Image.Resampling.LANCZOS)
        cc=Image.new("RGB",(z.width,z.height+24),(24,24,24));cc.paste(z,(0,24));ImageDraw.Draw(cc).text((4,4),lab,fill="white");ims.append(cc)
    row=Image.new("RGB",(sum(i.width for i in ims)+36,max(i.height for i in ims)+18),(16,16,16));xx=0
    for cc in ims:row.paste(cc,(xx,0));xx+=cc.width+12
    ImageDraw.Draw(row).text((4,row.height-2),r["key"],fill="white",anchor="ls");cards.append(row)
sh=Image.new("RGB",(max(cc.width for cc in cards),sum(cc.height for cc in cards)+16),(16,16,16));yy=0
for cc in cards:sh.paste(cc,(0,yy));yy+=cc.height+8
sh.save(out/"A173_Q121_CONTACTS.jpg","JPEG",quality=96,subsampling=0)
s=flat(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM));f=flat(dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM));s.thumbnail((1000,1000),Image.Resampling.LANCZOS);f.thumbnail((1000,1000),Image.Resampling.LANCZOS)
rw=Image.new("RGB",(s.width+f.width+12,max(s.height,f.height)+26),(16,16,16));rw.paste(s,(0,26));rw.paste(f,(s.width+12,26));dr=ImageDraw.Draw(rw);dr.text((4,4),"SOURCE RAW",fill="white");dr.text((s.width+16,4),"A173 RAW",fill="white");rw.save(out/"A173_Q121_RAW.jpg","JPEG",quality=94,subsampling=0)
report={"schema_version":2,"role":"A","run":run,"queue_index":121,"asset":"FD90AA9","regression":"C255 English residue; A171/A172 rejected full-bbox plate rectangle","rejected_current_sha256":CURRENT,"restored_prior_sha256":PRIOR,"candidate_sha256":csha,"source_sha256":SOURCE,"rows":rows,"construction":"restore true pre-A171 A138 atlas plate, remove source+Korean text/effects with text-shaped masks only, locally rebuild masked pixels, then fresh native Korean render","machine_qa":{"bbox_size_positive_margin":"3/3 PASS","changed_outside_vs_A138_prior":outside,"alpha_outside_vs_A138_prior":alpha_out,"header_128_exact":True,"persisted_decode":"PASS","raw_orientation":"mirror_y"},"controller_visual_qa":"PENDING","runtime_validation":"UNTESTED","status":"A173_Q121_MACHINE_PASS_PENDING_CONTROLLER_VISUAL","forbidden_domains_touched":[]}
(out/"A173_Q121_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A173_Q121.json").write_text(json.dumps({"run":run,"index":121,"asset":"FD90AA9","rejected_current":CURRENT,"restored_prior":PRIOR,"after":csha,"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"candidate_sha256":csha,"rows":rows},ensure_ascii=False,indent=2))
