#!/usr/bin/env python3
import base64, hashlib, json, math, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter, ImageOps
from scipy.ndimage import label
from scipy.spatial import cKDTree

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION148-8215-C200-TEMPLATE"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB="64a92104d3158614283d0d63baee7ec29ca45316"
PRIOR_SHA="04d2c23333999873b7f467d0a8647c1056f40fa3bcd06e0174711bb2345277ba"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_B144"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"8215.dds"; atlas=tmp/"8215_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_FLAG_RANK_Exst/4x_8215FD25_1024x512_atlas.json",atlas)

prior_clean_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION143-8215/B142_CLEAN_PLATE.png"
prior_report_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION143-8215/B142_8215_REPORT.json"
prior_final_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION143-8215/B142_FINAL_READABLE.png"
if not prior_clean_path.exists() or not prior_report_path.exists() or not prior_final_path.exists():
    raise RuntimeError("B143 evidence missing")

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(im): return im.point(lambda v:255 if v else 0)
def count(im): return sum(im.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(62,62,62,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64_jpeg(im,jpg,b64,quality=92):
    im.save(jpg,quality=quality,optimize=True); b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

sb=dds.read_bytes(); ab=atlas.read_bytes()
if gitblob(sb)!=SOURCE_BLOB: raise RuntimeError(("source drift",gitblob(sb)))
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(4096,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs={int(r["idx"]):r for r in json.loads(ab.decode())["regions"]}
prior_report=json.loads(prior_report_path.read_text())
prior_clean=Image.open(prior_clean_path).convert("RGBA")
prior_final=Image.open(prior_final_path).convert("RGBA")

# C196 accepted the upper speech-bubble plate (atlas idx2). Preserve it exactly from B143.
# The failed lower starburst plate is atlas idx1 and is the only reconstruction target here.
star_row=next(r for r in prior_report["rows"] if int(r["region_idx"])==1)
bubble_row=next(r for r in prior_report["rows"] if int(r["region_idx"])==2)
allowed=Image.new("L",(W,H),0)
for r in (star_row,bubble_row):
    x0,y0,x1,y1=map(int,r["original_bbox"])
    ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
protected=ImageOps.invert(allowed)

clean_arr=sa.copy()
bubble_box=tuple(map(int,bubble_row["original_bbox"]))
clean_arr[bubble_box[1]:bubble_box[3],bubble_box[0]:bubble_box[2]]=np.asarray(prior_clean)[bubble_box[1]:bubble_box[3],bubble_box[0]:bubble_box[2]]

# Re-derive idx1 starburst title core from canonical source.
idx=1; x,y,cw,ch=map(int,regs[idx]["rect"]); roi=sa[y:y+ch,x:x+cw]
rr=roi[:,:,0].astype(np.int16); gg=roi[:,:,1].astype(np.int16); bb=roi[:,:,2].astype(np.int16); aa=roi[:,:,3]
white=(aa>32)&(rr>175)&(gg>175)&(bb>175)&((np.maximum.reduce([rr,gg,bb])-np.minimum.reduce([rr,gg,bb]))<72)
band=np.zeros_like(white,dtype=bool); band[int(ch*.08):int(ch*.38),int(cw*.18):int(cw*.82)]=True
lab,nlab=label(white&band,structure=np.ones((3,3),dtype=np.uint8))
comps=[]
for lid in range(1,nlab+1):
    yy,xx=np.nonzero(lab==lid)
    if len(xx)<18: continue
    w0=int(xx.max()-xx.min()+1); h0=int(yy.max()-yy.min()+1)
    if 4<=w0<=180 and 12<=h0<=130:
        comps.append({"id":lid,"area":len(xx),"cy":float(yy.mean())})
bins={}
for q in comps:
    bins.setdefault(int(q["cy"]//24),[]).append(q)
best=max(bins.items(),key=lambda kv:(len(kv[1]),sum(z["area"] for z in kv[1])))[0]
ids={q["id"] for q in comps if abs(int(q["cy"]//24)-best)<=1}
sel=np.isin(lab,list(ids)); yy,xx=np.nonzero(sel); medy=float(np.median(yy))
keep=np.zeros_like(sel,dtype=bool)
for lid in ids:
    cyy,cxx=np.nonzero(lab==lid)
    if len(cxx) and abs(float(cyy.mean())-medy)<=42: keep|=(lab==lid)
sel=keep; ys,xs=np.nonzero(sel)
if len(xs)<12000: raise RuntimeError(("title core too small",len(xs)))
core_local_bbox=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
core_bbox=[x+core_local_bbox[0],y+core_local_bbox[1],x+core_local_bbox[2],y+core_local_bbox[3]]
core=np.zeros((H,W),bool); core[y:y+ch,x:x+cw]=sel
core_im=Image.fromarray((core.astype(np.uint8)*255),"L")
near=np.asarray(core_im.filter(ImageFilter.MaxFilter(25)))>0

# B148 reuses the C193-approved B137 63C clean starburst as a same-family
# canonical template. Both starburst atlas cells are 2048x1016 at y=1032; the
# current FLAG_RANK cell is x-shifted by about +1088. We fail closed unless the
# two canonical source backgrounds match outside their source-title footprints.
ob=list(map(int,star_row["original_bbox"]))
template_dir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION137"
tpl_src=Image.open(template_dir/"63C_SOURCE_READABLE.png").convert("RGBA")
tpl_clean=Image.open(template_dir/"63C_CLEAN_PLATE.png").convert("RGBA")
tpl_rep=json.loads((template_dir/"B137_63C_REPORT.json").read_text())
tpl_row=next(r for r in tpl_rep["rows"] if int(r["region_idx"])==0)
tpl_cell=list(map(int,tpl_row["cell"]))
tpl_box=list(map(int,tpl_row["original_bbox"]))
if tpl_cell != [0,1032,2048,1016] or [x,y,cw,ch] != [1088,1032,2048,1016]:
    raise RuntimeError(("starburst cell geometry drift",tpl_cell,[x,y,cw,ch]))

tsa=np.asarray(tpl_src,dtype=np.uint8)
tca=np.asarray(tpl_clean,dtype=np.uint8)
best=None
for dx in range(1082,1095):
    dy=0
    tx0=max(0,ob[0]-dx-170); ty0=max(0,ob[1]-90)
    tx1=min(tpl_src.width,ob[2]-dx+170); ty1=min(tpl_src.height,ob[3]+120)
    cx0=tx0+dx; cy0=ty0+dy; cx1=tx1+dx; cy1=ty1+dy
    if cx0<0 or cy0<0 or cx1>W or cy1>H: continue
    a=tsa[ty0:ty1,tx0:tx1].astype(np.int16)
    b=sa[cy0:cy1,cx0:cx1].astype(np.int16)
    mask=np.ones(a.shape[:2],dtype=bool)
    ex=16
    ax0=max(0,tpl_box[0]-ex-tx0); ay0=max(0,tpl_box[1]-ex-ty0)
    ax1=min(mask.shape[1],tpl_box[2]+ex-tx0); ay1=min(mask.shape[0],tpl_box[3]+ex-ty0)
    if ax1>ax0 and ay1>ay0: mask[ay0:ay1,ax0:ax1]=False
    bx0=max(0,ob[0]-ex-cx0); by0=max(0,ob[1]-ex-cy0)
    bx1=min(mask.shape[1],ob[2]+ex-cx0); by1=min(mask.shape[0],ob[3]+ex-cy0)
    if bx1>bx0 and by1>by0: mask[by0:by1,bx0:bx1]=False
    vis=mask & (a[:,:,3]>8) & (b[:,:,3]>8)
    if np.count_nonzero(vis)<20000: continue
    d=np.max(np.abs(a[:,:,:3]-b[:,:,:3]),axis=2)
    vals=d[vis]
    score=(float(np.median(vals)),float(np.mean(vals)),float(np.quantile(vals,.95)),int(np.count_nonzero(vals==0)),int(len(vals)))
    if best is None or score[:3] < best[0][:3]:
        best=(score,dx,dy)
if best is None: raise RuntimeError("no template alignment candidate")
(score,shift_x,shift_y)=best
median_diff,mean_diff,p95_diff,exact_rgb,total_cmp=score
if median_diff>2.0 or mean_diff>8.0 or p95_diff>20.0:
    raise RuntimeError(("63C template background mismatch",best))

# Replace the entire current source-title footprint from the approved clean template.
# Using the whole permitted bbox guarantees no source-letter fringe can survive while
# retaining the source-family starburst gradient/glow/rays from the matched template.
sx0=ob[0]-shift_x; sy0=ob[1]-shift_y; sx1=ob[2]-shift_x; sy1=ob[3]-shift_y
if sx0<0 or sy0<0 or sx1>tpl_clean.width or sy1>tpl_clean.height:
    raise RuntimeError(("template patch bounds",ob,shift_x,shift_y,[sx0,sy0,sx1,sy1]))
patch=tca[sy0:sy1,sx0:sx1]
if patch.shape[:2] != (ob[3]-ob[1],ob[2]-ob[0]):
    raise RuntimeError(("template patch shape",patch.shape,ob))
clean_arr[ob[1]:ob[3],ob[0]:ob[2]]=patch

# Edit mask/evidence is the exact C200-permitted source-effect bbox.
text_mask=np.zeros((H,W),dtype=bool)
text_mask[ob[1]:ob[3],ob[0]:ob[2]]=True
text_bbox=list(ob)

# Boundary seam gate: compare canonical source backgrounds on a 4px ring outside patch.
ring=np.zeros((H,W),dtype=bool)
ring[max(0,ob[1]-4):min(H,ob[3]+4),max(0,ob[0]-4):min(W,ob[2]+4)]=True
ring[ob[1]:ob[3],ob[0]:ob[2]]=False
qy,qx=np.nonzero(ring)
valid=(qx-shift_x>=0)&(qx-shift_x<tpl_src.width)&(qy-shift_y>=0)&(qy-shift_y<tpl_src.height)
qy=qy[valid]; qx=qx[valid]
if len(qx)<1000: raise RuntimeError(("template ring too small",len(qx)))
ring_tpl=tsa[qy-shift_y,qx-shift_x,:3].astype(np.int16)
ring_cur=sa[qy,qx,:3].astype(np.int16)
ring_diff=np.max(np.abs(ring_tpl-ring_cur),axis=1)
ring_med=float(np.median(ring_diff)); ring_p95=float(np.quantile(ring_diff,.95))
if ring_med>2.0 or ring_p95>20.0:
    raise RuntimeError(("template ring mismatch",ring_med,ring_p95))

clean=Image.fromarray(clean_arr,"RGBA")
core_same=int(np.count_nonzero(core & np.all(clean_arr==sa,axis=2)))
if core_same:
    raise RuntimeError(("template clean left source core unchanged",core_same))

# Re-render the same Korean source-family title, now over the corrected starburst clean field.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
fp,fi,fstyle=spec.rsplit("|",2); fi=int(fi or 0)
fill=tuple(prior_report["source_style"]["fill_rgba"])
outline=tuple(prior_report["source_style"]["outline_rgba"])
fs=int(prior_report["source_style"]["shared_font_size"]); sw=int(prior_report["source_style"]["stroke_width"]); slant=float(prior_report["source_style"]["slant"])

def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for yy0 in range(im.height):
        o.alpha_composite(im.crop((0,yy0,im.width,yy0+1)),(int(round(s*(im.height-1-yy0))),yy0))
    return o
font=ImageFont.truetype(fp,fs,index=fi)
fb=font.getbbox("종합 랭킹",stroke_width=sw)
tile=Image.new("RGBA",(fb[2]-fb[0]+32,fb[3]-fb[1]+32),(0,0,0,0))
ImageDraw.Draw(tile).text((16-fb[0],16-fb[1]),"종합 랭킹",font=font,fill=fill,stroke_width=sw,stroke_fill=outline)
tile=shear_rgba(tile,slant); abx=tile.getchannel("A").getbbox(); tile=tile.crop(abx)

cb=core_bbox; px=cb[0]+(cb[2]-cb[0]-tile.width)//2; py=cb[1]+(cb[3]-cb[1]-tile.height)//2
final=clean.copy()
# Restore C196-accepted idx2 speech-bubble final exactly.
final_arr=np.asarray(final).copy()
final_arr[bubble_box[1]:bubble_box[3],bubble_box[0]:bubble_box[2]]=np.asarray(prior_final)[bubble_box[1]:bubble_box[3],bubble_box[0]:bubble_box[2]]
final=Image.fromarray(final_arr,"RGBA")
final.alpha_composite(tile,(px,py))
tm=Image.new("L",(W,H),0); tm.paste(bmask(tile.getchannel("A")),(px,py)); lb=list(tm.getbbox())
if not(lb[0]>cb[0] and lb[1]>cb[1] and lb[2]<cb[2] and lb[3]<cb[3]):
    raise RuntimeError(("localized bbox",cb,lb))

# Round-trip exact DDS structure.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")

diff=diffmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
if outside or alphaout: raise RuntimeError(("outside gate",outside,alphaout))
protected_indices=[0,3,4,5,6,7]
protected_changed={}
da=np.asarray(dec)
for pi in protected_indices:
    xx0,yy0,ww,hh=map(int,regs[pi]["rect"])
    protected_changed[str(pi)]=int(np.count_nonzero(np.any(sa[yy0:yy0+hh,xx0:xx0+ww]!=da[yy0:yy0+hh,xx0:xx0+ww],axis=2)))
if any(protected_changed.values()): raise RuntimeError(("protected changed",protected_changed))

# Bbox/margin report for both physical titles.
rows=[]
for old in (star_row,bubble_row):
    z=dict(old)
    if int(z["region_idx"])==2:
        z["rework_status"]="B148_C200_ACCEPTED_SPEECH_BUBBLE_PRESERVED_EXACT"
    else:
        z["source_effect_mask_pixels"]=int(np.count_nonzero(text_mask))
        z["original_bbox"]=ob
        z["source_core_bbox"]=core_bbox
        z["localized_bbox"]=lb
        z["source_width"]=core_bbox[2]-core_bbox[0]; z["source_height"]=core_bbox[3]-core_bbox[1]
        z["localized_width"]=lb[2]-lb[0]; z["localized_height"]=lb[3]-lb[1]
        z["delta_left"]=lb[0]-core_bbox[0]; z["delta_right"]=core_bbox[2]-lb[2]
        z["delta_top"]=lb[1]-core_bbox[1]; z["delta_bottom"]=core_bbox[3]-lb[3]
        z["containment"]="PASS"; z["size_ceiling"]="PASS"; z["positive_margin"]="PASS"
        z["rework_status"]="B148_C200_C193_TEMPLATE_STARBRUST_RECONSTRUCTION"
        z["template_patch_bbox"]=text_bbox; z["template_shift"]=[shift_x,shift_y]
    rows.append(z)

source_text_mask=Image.new("L",(W,H),0)
# Keep C196-accepted idx2 prior source mask for evidence; idx1 uses the new starburst mask.
prior_sm=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION143-8215/B142_SOURCE_TEXT_MASK.png").convert("L")
source_text_mask.paste(prior_sm.crop(bubble_box),(bubble_box[0],bubble_box[1]))
source_text_mask=ImageChops.lighter(source_text_mask,Image.fromarray((text_mask.astype(np.uint8)*255),"L"))

source_png=out/"B148_SOURCE_READABLE.png"; clean_png=out/"B148_CLEAN_PLATE.png"; final_png=out/"B148_FINAL_READABLE.png"
smp=out/"B148_SOURCE_TEXT_MASK.png"; ap=out/"B148_ALLOWED_EFFECT_BBOX_MASK.png"; pp=out/"B148_PROTECTED_MASK.png"
src.save(source_png); clean.save(clean_png); dec.save(final_png); source_text_mask.save(smp); allowed.save(ap); protected.save(pp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B148_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B148_FINAL_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B148_CLEAN_VALIDATION.json").read_text()); finalrep=json.loads((out/"B148_FINAL_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS" or finalrep["status"]!="PASS": raise RuntimeError(("validator",cleanrep["status"],finalrep["status"]))

# Focused controller evidence.
cards=[]
for r in rows:
    x0,y0,x1,y1=map(int,r["original_bbox"]); p=70
    box=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z.crop(box)) for z in (src,clean,dec)]
    scale=min(2.2,1250/max(1,ims[0].width))
    ims=[z.resize((max(1,int(z.width*scale)),max(1,int(z.height*scale))),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+42),"white")
    xx1=0
    for z in ims: c.paste(z,(xx1,42)); xx1+=z.width+8
    ImageDraw.Draw(c).text((5,6),f"idx={r['region_idx']} Total Rank -> 종합 랭킹 | SOURCE CLEAN FINAL",fill="black")
    cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+5 for c in cards)),"white"); yy1=0
for c in cards: sheet.paste(c,(0,yy1)); yy1+=c.height+5
save_b64_jpeg(sheet,out/"B148_8215_CONTACTS.jpg",out/"B148_8215_CONTACTS_B64.txt",94)

# Extra starburst closeup makes C196 defect directly reviewable.
x0,y0,x1,y1=ob; p=110; box=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
ims=[comp(z.crop(box)) for z in (src,clean,dec)]
scale=min(2.8,1500/max(1,ims[0].width)); ims=[z.resize((int(z.width*scale),int(z.height*scale)),Image.Resampling.NEAREST) for z in ims]
focus=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+44),"white"); xx1=0
for labtxt,z in zip(("SOURCE","CLEAN","FINAL"),ims):
    focus.paste(z,(xx1,44)); ImageDraw.Draw(focus).text((xx1+4,8),labtxt,fill="black"); xx1+=z.width+8
save_b64_jpeg(focus,out/"B148_STARBURST_FOCUS.jpg",out/"B148_STARBURST_FOCUS_B64.txt",95)

rrim=Image.new("RGB",(1024,2*550),"white")
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
for i,(labtxt,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im); z.thumbnail((1024,512),Image.Resampling.LANCZOS); rrim.paste(z,(0,i*550+26)); ImageDraw.Draw(rrim).text((5,i*550+5),labtxt,fill="black")
save_b64_jpeg(rrim,out/"B148_RAW_COMPARE.jpg",out/"B148_RAW_COMPARE_B64.txt",90)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":30,"asset":asset,
 "reworks":"C200_REWORK_REQUIRED_STARBURST_TEXTURE_DISCONTINUITY_AND_SMEAR",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB,"source_sha256":sha(sb)},
 "prior_candidate_sha256":"d8687e615007af7bdd8e4d0bf41f1830e0bf105a3ef225cc157671fc8e9fd377",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":payload[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "classification":{"localizable":"Total Rank x2","translation":"종합 랭킹","protected":["character artwork","lens flare","rank letters B/C/D/E"]},
 "clean_reconstruction":{
   "idx2":"C196-accepted B143 speech-bubble clean/final preserved exact inside prior allowed bbox",
   "idx1":"C193-approved B137 63C same-family starburst CLEAN template aligned to canonical source and copied across current source-title footprint",
   "idx1_prior_effect_mask_pixels":int(star_row["source_effect_mask_pixels"]),
   "idx1_template_patch_pixels":int(np.count_nonzero(text_mask)),
   "idx1_template_patch_bbox":text_bbox,
   "idx1_template_alignment":{"shift_x":shift_x,"shift_y":shift_y,"median_rgb_diff":median_diff,"mean_rgb_diff":mean_diff,"p95_rgb_diff":p95_diff,"exact_rgb":exact_rgb,"compared_pixels":total_cmp,"ring_median_rgb_diff":ring_med,"ring_p95_rgb_diff":ring_p95}
 },
 "source_style":prior_report["source_style"],
 "rows":rows,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"outside_allowed_effect_bbox":outside,"alpha_outside":alphaout,"localized_overlap":0},
 "protected_region_changed_pixels":protected_changed,
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "status":"B148_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "RUNTIME_VALIDATION":"UNTESTED"
}
(out/"B148_8215_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":30,"asset":"8215FD25","candidate_sha256":csha,
 "localized_physical_elements":2,"bbox_size_positive_margin":"2/2",
 "idx1_precise_effect_mask_pixels":int(np.count_nonzero(text_mask)),
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "outside":outside,"alpha_outside":alphaout,"protected_regions_changed":sum(protected_changed.values()),
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_B/{run}/B148_8215_REPORT.json"}
(wr/"B148_8215FD25.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False),flush=True)
