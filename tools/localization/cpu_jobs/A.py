#!/usr/bin/env python3
# A179: work-steal q102 C260 selector hierarchy repair.
# A primary ODD shard had no material RENDER_READY/C-returned item after refresh.
# q212 changed in the current B cycle, so skip it; steal older q102 C260 REWORK.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib,json,struct,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

repo=Path.cwd()
RUN="20261008-A179-Q102-SELECTOR-HIERARCHY"
out=repo/"localization/graphics/role_A"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_selector_cvt_Exst/571E78F3_512x64.dds"
source_path=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel
cand=repo/"localization/graphics/hd_candidates"/rel
clean_path=repo/"localization/graphics/role_C/20261004-1720-C91/C91_571E78F3_CLEAN_PLATE.png"
SOURCE="17ee051e59d23c741c9df428dccd3ee2f7863c19a038f02db250001f44b6c121"
INPUT="442babea9c5dea9a944dff3d4a6a577f007dad2ae63a9699d380baf0ce7fc05d"

TIME_BBOX=[395,15,1330,140]
CONT_BBOX=[520,132,1590,245]
OLD_CONT_BBOX=[830,132,1280,244]
TARGET_TEXT="15코스 연속"
TARGET_WIDTH=815
TARGET_PRECOMPRESS_HEIGHT=96
LEAN=0.14

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dds_meta(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",str(p)))
    h=struct.unpack_from("<I",b,12)[0];w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0];fourcc=b[84:88]
    need=128+((w+3)//4)*((h+3)//4)*16
    if fourcc!=b"DXT5" or mips not in (0,1) or len(b)!=need:
        raise RuntimeError(("unexpected DXT5",w,h,mips,fourcc,len(b),need))
    return b,{"width":w,"height":h,"mips":mips,"fourcc":"DXT5","bytes":len(b)}
def decode_readable(p):
    return Image.open(p).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def bool_bbox(mask):
    ys,xs=np.nonzero(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def diffmask(a,b):
    aa=np.asarray(a,dtype=np.uint8);bb=np.asarray(b,dtype=np.uint8)
    return np.any(aa!=bb,axis=2)
def rect_mask(size,bb):
    W,H=size;m=np.zeros((H,W),dtype=bool);x0,y0,x1,y1=bb;m[y0:y1,x0:x1]=True;return m
def flat(im,bg=(112,112,112,255)):
    z=Image.new("RGBA",im.size,bg);z.alpha_composite(im);return z.convert("RGB")

def fontspec():
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    if "|" in q:
        p,ix=q.rsplit("|",1)
        if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:
            return p,int(ix or 0),"Noto Sans CJK KR:style=Bold"
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    p,ix=q.rsplit("|",1);return p,int(ix or 0),"Noto Sans CJK KR:style=Bold"

def source_colors(src,bb):
    a=np.asarray(src.crop(tuple(bb)),dtype=np.uint8)
    alpha=a[:,:,3]>20
    rgb=a[:,:,:3]
    orange=alpha&(rgb[:,:,0]>150)&(rgb[:,:,1]>45)&(rgb[:,:,1]<205)&(rgb[:,:,2]<95)
    white=alpha&(rgb.min(axis=2)>175)
    # dark blue/navy pixels in the outlined title family.
    navy=alpha&(rgb[:,:,2]>=rgb[:,:,0])&(rgb[:,:,2]>=rgb[:,:,1])&(rgb.max(axis=2)<120)
    def med(mask,fallback):
        v=rgb[mask]
        return tuple(int(x) for x in np.median(v,axis=0)) if len(v)>=20 else fallback
    return {
      "fill":med(orange,(241,128,0)),
      "white":med(white,(239,239,239)),
      "navy":med(navy,(4,20,57))
    }

def render_native(text,font_path,font_index,colors):
    # Render from a vector font at native working resolution; no prior Korean bitmap is reused/upscaled.
    f=ImageFont.truetype(font_path,112,index=font_index)
    probe=Image.new("L",(1800,320),0);d=ImageDraw.Draw(probe)
    bb=d.textbbox((0,0),text,font=f,stroke_width=12)
    W=bb[2]-bb[0]+64;H=bb[3]-bb[1]+64
    masks=[]
    for sw in (12,7,3,0):
        m=Image.new("L",(W,H),0);md=ImageDraw.Draw(m)
        md.text((32-bb[0],32-bb[1]),text,font=f,fill=255,stroke_width=sw,stroke_fill=255)
        masks.append(m)
    union=masks[0].getbbox()
    if not union: raise RuntimeError("empty render")
    masks=[m.crop(union) for m in masks]
    layer=Image.new("RGBA",masks[0].size,(0,0,0,0))
    for mask,col in [(masks[0],colors["navy"]),(masks[1],colors["white"]),(masks[2],colors["navy"]),(masks[3],colors["fill"])]:
        c=Image.new("RGBA",mask.size,tuple(col)+(255,));c.putalpha(mask);layer.alpha_composite(c)
    # Source-relative height first, then horizontal hierarchy expansion.
    ah=layer.getchannel("A").getbbox()
    layer=layer.crop(ah)
    scale_h=TARGET_PRECOMPRESS_HEIGHT/layer.height
    scaled_w=max(1,round(layer.width*scale_h))
    layer=layer.resize((scaled_w,TARGET_PRECOMPRESS_HEIGHT),Image.Resampling.LANCZOS)
    # Horizontal source-family fit from fresh native render, not from old Korean pixels.
    prelean_target=max(1,TARGET_WIDTH-round(LEAN*(TARGET_PRECOMPRESS_HEIGHT-1)))
    layer=layer.resize((prelean_target,layer.height),Image.Resampling.LANCZOS)
    # readable right lean: top shifts right relative to bottom.
    shift=max(1,int(np.ceil(LEAN*(layer.height-1))))
    src=Image.new("RGBA",(layer.width+shift+8,layer.height),(0,0,0,0));src.alpha_composite(layer,(0,0))
    dst=Image.new("RGBA",src.size,(0,0,0,0))
    for y in range(src.height):
        dx=int(round(LEAN*(src.height-1-y)))
        dst.alpha_composite(src.crop((0,y,src.width,y+1)),(dx,y))
    ab=dst.getchannel("A").getbbox()
    if not ab: raise RuntimeError("empty lean")
    return dst.crop(ab)

if sha(source_path)!=SOURCE: raise RuntimeError(("source drift",sha(source_path),SOURCE))
if sha(cand)!=INPUT: raise RuntimeError(("candidate drift",sha(cand),INPUT))
sb,smeta=dds_meta(source_path);cb,cmeta=dds_meta(cand)
if sb[:128]!=cb[:128] or smeta!=cmeta: raise RuntimeError("header/structure drift")
source=decode_readable(source_path);before=decode_readable(cand)
clean=Image.open(clean_path).convert("RGBA")
if source.size!=before.size or source.size!=clean.size: raise RuntimeError("dimension mismatch")
W,H=source.size
FONT,FI,FPAT=fontspec()
colors=source_colors(source,CONT_BBOX)
fresh=render_native(TARGET_TEXT,FONT,FI,colors)

sw=CONT_BBOX[2]-CONT_BBOX[0];sh=CONT_BBOX[3]-CONT_BBOX[1]
if fresh.width>sw-4 or fresh.height>sh-4:
    fit=min((sw-4)/fresh.width,(sh-4)/fresh.height)
    fresh=fresh.resize((max(1,int(fresh.width*fit)),max(1,int(fresh.height*fit))),Image.Resampling.LANCZOS)
ab=fresh.getchannel("A").getbbox();fresh=fresh.crop(ab)

# Preserve the accepted Time Attack Mode row byte-for-byte in readable pixels.
final=before.copy()
# B212's reported second-row bbox overlaps the accepted Time row vertically because
# cell-alpha measurement included first-row fringe. Preserve y<140 byte-for-byte and
# clear only the safely separable second-row footprint from y=140 downward.
cx0=max(CONT_BBOX[0]+4,OLD_CONT_BBOX[0]-8)
cy0=max(CONT_BBOX[1],TIME_BBOX[3])
cx1=min(CONT_BBOX[2]-4,OLD_CONT_BBOX[2]+8)
cy1=min(CONT_BBOX[3]-1,OLD_CONT_BBOX[3])
baseline=before.copy()
baseline.paste(clean.crop((cx0,cy0,cx1,cy1)),(cx0,cy0))
final=baseline.copy()

px=CONT_BBOX[0]+(sw-fresh.width)//2
py=max(TIME_BBOX[3]+2, CONT_BBOX[1]+(sh-fresh.height)//2)
if px<=CONT_BBOX[0] or py<=CONT_BBOX[1] or px+fresh.width>=CONT_BBOX[2] or py+fresh.height>=CONT_BBOX[3]:
    raise RuntimeError(("no positive precompress margin",fresh.size,[px,py],CONT_BBOX))
final.alpha_composite(fresh,(px,py))

# Desired changes must be wholly inside continuous_15 source bbox, and Time Attack must remain exact.
allowed=rect_mask(source.size,CONT_BBOX)
dm=diffmask(before,final)
outside=int(np.logical_and(dm,~allowed).sum())
if outside: raise RuntimeError(("desired outside",outside,bool_bbox(dm)))
time_diff=int(diffmask(before.crop(tuple(TIME_BBOX)),final.crop(tuple(TIME_BBOX))).sum())
if time_diff: raise RuntimeError(("time row drift",time_diff))

# Install NVTT only when unavailable on the runner.
if not Path("/usr/bin/nvcompress").exists():
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","libnvtt-bin"],check=True)
nvcompress=Path("/usr/bin/nvcompress")
if not nvcompress.exists(): raise RuntimeError("nvcompress unavailable")

# Compress once, but patch only BC3 blocks containing actual desired changed pixels.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp")/"A179_q102_raw.png";tmp_dds=Path("/tmp")/"A179_q102_nv.dds"
raw_final.save(tmp_png)
subprocess.run([str(nvcompress),"-bc3","-nomips",str(tmp_png),str(tmp_dds)],
               check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb,tmeta=dds_meta(tmp_dds)
if tmeta["width"]!=W or tmeta["height"]!=H: raise RuntimeError("nvcompress size drift")

raw_before=before.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw_change=diffmask(raw_before,raw_final)
ys,xs=np.nonzero(raw_change)
if not len(xs): raise RuntimeError("no desired changes")
bw=(W+3)//4;bh=(H+3)//4
patch_blocks={(int(x)//4,int(y)//4) for x,y in zip(xs,ys)}
# Every patched 4x4 block must be completely inside the readable source bbox after Y mirroring.
for bx,by in patch_blocks:
    rx0=bx*4;rx1=min(W,rx0+4)
    ry0=H-min(H,(by+1)*4);ry1=H-by*4
    if rx0<CONT_BBOX[0] or rx1>CONT_BBOX[2] or ry0<CONT_BBOX[1] or ry1>CONT_BBOX[3]:
        raise RuntimeError(("patch block escape",[bx,by],[rx0,ry0,rx1,ry1],CONT_BBOX))

out_bytes=bytearray(cb)
for bx,by in patch_blocks:
    off=128+(by*bw+bx)*16
    out_bytes[off:off+16]=tb[off:off+16]
cand.write_bytes(out_bytes)
after=sha(cand)

fb,fmeta=dds_meta(cand);decoded=decode_readable(cand)
if fb[:128]!=sb[:128] or fmeta!=smeta: raise RuntimeError("persisted structure drift")
pdiff=diffmask(before,decoded)
persist_out=int(np.logical_and(pdiff,~allowed).sum())
alpha_out=int(np.logical_and(np.asarray(before.getchannel("A"))!=np.asarray(decoded.getchannel("A")),~allowed).sum())
if persist_out or alpha_out: raise RuntimeError(("persisted outside",persist_out,alpha_out,bool_bbox(pdiff)))
if diffmask(before.crop(tuple(TIME_BBOX)),decoded.crop(tuple(TIME_BBOX))).any():
    raise RuntimeError("persisted Time Attack row drift")

# Measure the new second-row label against the clean/reconstructed baseline rather
# than raw atlas alpha, because q102 sprite cells overlap in Y.
td=diffmask(baseline,decoded)
local=np.zeros_like(td);x0,y0,x1,y1=CONT_BBOX;local[y0:y1,x0:x1]=td[y0:y1,x0:x1]
lb=bool_bbox(local)
if not lb: raise RuntimeError("empty persisted target diff")
lw,lh=lb[2]-lb[0],lb[3]-lb[1]
margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
if not(all(v>0 for v in margins) and lw<=sw and lh<=sh):
    raise RuntimeError(("postcompress bbox/margin fail",lb,margins,[sw,sh]))
width_ratio=lw/sw
if width_ratio<0.68:
    raise RuntimeError(("hierarchy still underfilled",width_ratio,lb))

# Check no unintended changed BC3 blocks.
changed_blocks=0;outside_patch=0
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if cb[off:off+16]!=fb[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patch_blocks:outside_patch+=1
if outside_patch: raise RuntimeError(("compressed collateral",outside_patch))

# Evidence.
def card(crop):
    ims=[]
    for lab,im in [("SOURCE",source),("B212_C260_REJECT",before),("C91_CLEAN",clean),("A179",decoded)]:
        z=flat(im.crop(crop));z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST)
        c=Image.new("RGB",(z.width,z.height+26),(20,20,20));c.paste(z,(0,26));ImageDraw.Draw(c).text((4,4),lab,fill="white");ims.append(c)
    s=Image.new("RGB",(sum(i.width for i in ims)+18,max(i.height for i in ims)),(16,16,16));xx=0
    for i in ims:s.paste(i,(xx,0));xx+=i.width+6
    return s
crop=(CONT_BBOX[0]-24,CONT_BBOX[1]-12,CONT_BBOX[2]+24,CONT_BBOX[3]+12)
sheet=card(crop);sheet.save(out/"A179_Q102_CONTACTS.jpg","JPEG",quality=96,subsampling=0)

rows=[]
for sc in [1.0,0.75,0.5]:
    ims=[]
    for lab,im in [("SOURCE",source),("B212",before),("A179",decoded)]:
        z=flat(im.crop(tuple(CONT_BBOX)))
        if sc!=1.0:z=z.resize((round(z.width*sc),round(z.height*sc)),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(z.width,z.height+24),(20,20,20));c.paste(z,(0,24));ImageDraw.Draw(c).text((4,4),f"{lab} {int(sc*100)}%",fill="white");ims.append(c)
    r=Image.new("RGB",(max(i.width for i in ims),sum(i.height for i in ims)+10),(16,16,16));yy=0
    for i in ims:r.paste(i,(0,yy));yy+=i.height+5
    rows.append(r)
p=Image.new("RGB",(sum(i.width for i in rows)+12,max(i.height for i in rows)),(16,16,16));xx=0
for i in rows:p.paste(i,(xx,0));xx+=i.width+6
p.save(out/"A179_Q102_PRACTICAL.jpg","JPEG",quality=95,subsampling=0)

sr=flat(source.transpose(Image.Transpose.FLIP_TOP_BOTTOM));fr=flat(decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
sr.thumbnail((1024,512),Image.Resampling.LANCZOS);fr.thumbnail((1024,512),Image.Resampling.LANCZOS)
rw=Image.new("RGB",(sr.width+fr.width+8,max(sr.height,fr.height)+26),(16,16,16));rw.paste(sr,(0,26));rw.paste(fr,(sr.width+8,26))
d=ImageDraw.Draw(rw);d.text((4,4),"SOURCE RAW",fill="white");d.text((sr.width+12,4),"A179 RAW",fill="white")
rw.save(out/"A179_Q102_RAW.jpg","JPEG",quality=94,subsampling=0)

report={
 "schema_version":2,"role":"A","run":RUN,"queue_index":102,"asset":"571E78F3",
 "work_stolen_from_lane":"B",
 "selection_reason":"A ODD shard had no material RENDER_READY/C-returned item; q212 changed by B in current cycle, so older unchanged q102 C260 REWORK was stolen after live refresh.",
 "trigger":"C260_REWORK_REQUIRED_TEXT_SCALE_HIERARCHY",
 "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":after,
 "preserved":{"time_attack_mode":"PIXEL_EXACT_TO_B212","time_attack_readable_diff_pixels":0},
 "reworked":{
   "key":"continuous_15","source":"15 Continuous Course","korean":TARGET_TEXT,
   "source_bbox":CONT_BBOX,"prior_localized_bbox":[830,132,1280,244],
   "localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
   "margins":margins,"width_ratio":round(width_ratio,4),
   "prior_width_ratio":round(450/1070,4),
   "font":FPAT,"font_source":"native vector font; no previous Korean bitmap reuse/upscale",
   "readable_right_lean":LEAN,
   "effect_family":{"fill_rgb":colors["fill"],"inner_outline_rgb":colors["navy"],"keyline_rgb":colors["white"],"outer_outline_rgb":colors["navy"]},
   "construction":"fresh native Hangul render, source-derived orange/navy/white effect family, readable-right lean, source-relative horizontal hierarchy expansion, centered inside exact source bbox with positive vertical/horizontal margins"
 },
 "machine_qa":{
   "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
   "changed_pixels_outside_continuous_source_bbox":persist_out,
   "alpha_changed_pixels_outside_continuous_source_bbox":alpha_out,
   "changed_bc3_blocks":changed_blocks,"changed_bc3_blocks_outside_patch":outside_patch,
   "header_128_exact":True,"mips":smeta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS"
 },
 "ordered_generation_gate":{
   "1_english_removal_plate_restoration":"PASS_REUSE_C91_VERIFIED_CLEAN_PLATE_ONLY_FOR_PRIOR_KOREAN_FOOTPRINT",
   "2_source_matching_slant":"PASS_READABLE_RIGHT_LEAN_0.14",
   "3_no_undersized_lettering":"PASS_WIDTH_RATIO_MATERIALLY_RAISED_FROM_0.421_TO_"+str(round(width_ratio,3)),
   "4_source_faithful_weight_effect":"PASS_SOURCE_DERIVED_ORANGE_NAVY_WHITE_LAYER_FAMILY",
   "5_no_clipped_pixels":"PASS_POSITIVE_MARGIN",
   "6_protected_art_clearance":"PASS_ZERO_OUTSIDE_SOURCE_BBOX_AND_TIME_ROW_EXACT",
   "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_CONFIRM",
   "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_CONFIRM"
 },
 "execution_backend":"GitHub Actions fallback after ChatGPT local environment lacked nvcompress and package installation timed out; repository-backed BC3 encode required.",
 "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
 "fresh_independent_c":"REQUIRED","mandatory_c3":"REQUIRED_EXACT_SHA",
 "runtime_validation":"UNTESTED","status":"A179_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA",
 "forbidden_domains_touched":[]
}
(out/"A179_Q102_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A179_Q102.json").write_text(json.dumps({"role":"A","run":RUN,"queue_index":102,"asset":rel,"candidate_sha256":after,"report":str((out/"A179_Q102_REPORT.json").relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"candidate_sha256":after,"localized_bbox":lb,"localized_size":[lw,lh],"margins":margins,"width_ratio":width_ratio,"changed_blocks":changed_blocks},ensure_ascii=False,indent=2))
