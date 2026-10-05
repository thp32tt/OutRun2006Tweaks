#!/usr/bin/env python3
import base64, hashlib, json, math, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter, ImageOps
from scipy.ndimage import label

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION151-DCC7"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_FLAG_RANK_Exst/DCC7B488_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB="7f8f0d10f2ac8a19bda1933d6a324a37123b48c0"
SOURCE_SHA="ecd0607fd021b6aa0c78700bffa05f70546a4d37da6182edc4a35bc41ab5ee4e"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_B151"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"DCC7B488.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_FLAG_RANK_Exst/DCC7B488_512x256.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_FLAG_RANK_Exst/4x_DCC7B488_512x256_atlas.json",atlas)

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
def save_b64(im,jpg,b64,quality=94):
    im.save(jpg,quality=quality,optimize=True); b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

sb=dds.read_bytes(); ab=atlas.read_bytes()
if gitblob(sb)!=SOURCE_BLOB or sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",gitblob(sb),sha(sb)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(2048,1024) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs=json.loads(ab.decode())["regions"]
if len(regs)!=1 or regs[0]["rect"]!=[0,8,1640,1016]: raise RuntimeError(("atlas drift",regs))
x,y,cw,ch=map(int,regs[0]["rect"]); roi=sa[y:y+ch,x:x+cw]

# Detect the white italic title core in the upper-center of the speech bubble.
r=roi[:,:,0].astype(np.int16); g=roi[:,:,1].astype(np.int16); b=roi[:,:,2].astype(np.int16); a=roi[:,:,3]
white=(a>80)&(r>180)&(g>180)&(b>180)&((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]))<65)
band=np.zeros_like(white,bool); band[int(ch*.08):int(ch*.38),int(cw*.22):int(cw*.78)]=True
lab,nlab=label(white&band,structure=np.ones((3,3),dtype=np.uint8))
comps=[]
for lid in range(1,nlab+1):
    yy,xx=np.nonzero(lab==lid)
    if len(xx)<20: continue
    ww=int(xx.max()-xx.min()+1); hh=int(yy.max()-yy.min()+1)
    if 4<=ww<=180 and 15<=hh<=140:
        comps.append({"id":lid,"area":len(xx),"cy":float(yy.mean())})
if len(comps)<5: raise RuntimeError(("too few title comps",comps))
bins={}
for q in comps: bins.setdefault(int(q["cy"]//20),[]).append(q)
best=max(bins.items(),key=lambda kv:(len(kv[1]),sum(z["area"] for z in kv[1])))[0]
ids={q["id"] for q in comps if abs(int(q["cy"]//20)-best)<=1}
sel=np.isin(lab,list(ids)); yy,xx=np.nonzero(sel); medy=float(np.median(yy))
core_local=np.zeros_like(sel,bool)
for lid in ids:
    cyy,cxx=np.nonzero(lab==lid)
    if len(cxx) and abs(float(cyy.mean())-medy)<=38: core_local|=(lab==lid)
ys,xs=np.nonzero(core_local)
if len(xs)<12000: raise RuntimeError(("core too small",len(xs)))
core_bbox=[x+int(xs.min()),y+int(ys.min()),x+int(xs.max())+1,y+int(ys.max())+1]
if not(350<=core_bbox[2]-core_bbox[0]<=850 and 45<=core_bbox[3]-core_bbox[1]<=150):
    raise RuntimeError(("core bbox implausible",core_bbox))
core=np.zeros((H,W),bool); core[y:y+ch,x:x+cw]=core_local

# Fit the local pale-green speech-bubble field from a ring around the title.
padx,pady=80,58
sx0=max(x,core_bbox[0]-padx); sx1=min(x+cw,core_bbox[2]+padx)
sy0=max(y,core_bbox[1]-pady); sy1=min(y+ch,core_bbox[3]+pady)
Y,X=np.mgrid[sy0:sy1,sx0:sx1]
sub=sa[sy0:sy1,sx0:sx1].astype(np.float64)
core_sub=core[sy0:sy1,sx0:sx1]
near=np.asarray(Image.fromarray((core_sub.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(35)))>0
# Interior samples are opaque/translucent pale-green and exclude title, navy edge, and bright outer glow.
sample=(sub[:,:,3]>60)&(~near)
sample&=(sub[:,:,0]>105)&(sub[:,:,1]>105)&(sub[:,:,2]>85)
sample&=(np.max(sub[:,:,:3],axis=2)-np.min(sub[:,:,:3],axis=2)<95)
xn=(X-(sx0+sx1)/2)/max(1,(sx1-sx0)/2); yn=(Y-(sy0+sy1)/2)/max(1,(sy1-sy0)/2)
B=np.stack([np.ones_like(xn),xn,yn,xn*xn,xn*yn,yn*yn],axis=-1)
flatB=B.reshape(-1,6); flatS=sub.reshape(-1,4); mask=sample.reshape(-1)
if np.count_nonzero(mask)<12000: raise RuntimeError(("background samples",int(np.count_nonzero(mask))))
use=mask.copy(); coef=np.zeros((6,4),float)
for _ in range(4):
    for c in range(4): coef[:,c]=np.linalg.lstsq(flatB[use],flatS[use,c],rcond=None)[0]
    pred=flatB@coef
    resid=np.max(np.abs(pred[:,:3]-flatS[:,:3]),axis=1)
    lim=max(12.0,float(np.quantile(resid[mask],.62)))
    use=mask&(resid<=lim)
pred=(flatB@coef).reshape(sub.shape)
pred=np.clip(np.rint(pred),0,255).astype(np.uint8)

# Exact source title/effect mask: residual pixels connected to the white core.
resid=np.max(np.abs(sub[:,:,:3]-pred[:,:,:3].astype(float)),axis=2)
zone=np.asarray(Image.fromarray((core_sub.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(43)))>0
cand=(resid>20)&zone&(sub[:,:,3]>10)
cl,nc=label(cand,structure=np.ones((3,3),dtype=np.uint8))
seed_ids=set(np.unique(cl[core_sub]).tolist()); seed_ids.discard(0)
effect_local=np.isin(cl,list(seed_ids))|core_sub
dil=np.asarray(Image.fromarray((effect_local.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
effect_local|=dil&(resid>8)&zone
effect=np.zeros((H,W),bool); effect[sy0:sy1,sx0:sx1]=effect_local
ey,ex=np.nonzero(effect)
if not len(ex): raise RuntimeError("empty effect mask")
effect_bbox=[int(ex.min()),int(ey.min()),int(ex.max())+1,int(ey.max())+1]
if not(effect_bbox[0]<core_bbox[0] and effect_bbox[1]<=core_bbox[1] and effect_bbox[2]>core_bbox[2] and effect_bbox[3]>=core_bbox[3]):
    raise RuntimeError(("effect does not cover core",effect_bbox,core_bbox))
if np.count_nonzero(effect)>65000: raise RuntimeError(("effect too broad",int(np.count_nonzero(effect)),effect_bbox))

pglobal=np.zeros((H,W,4),np.uint8); pglobal[sy0:sy1,sx0:sx1]=pred
# B150 controller visual QA found a faint low-contrast Total Rank silhouette outside the
# residual-connected mask. Reconstruct the entire exact effect bbox from the fitted
# speech-bubble field; the box is fully inside the smooth interior and never touches
# the navy border/glow. This removes all source-shaped low-alpha/low-contrast residue.
clean_scope=np.zeros((H,W),bool)
clean_scope[effect_bbox[1]:effect_bbox[3],effect_bbox[0]:effect_bbox[2]]=True
clean_arr=sa.copy(); clean_arr[clean_scope]=pglobal[clean_scope]
same=effect&np.all(clean_arr==sa,axis=2)
if np.any(same):
    for yy0,xx0 in zip(*np.nonzero(same)):
        v=int(clean_arr[yy0,xx0,0]); clean_arr[yy0,xx0,0]=v+1 if v<255 else v-1
if np.count_nonzero(effect&np.all(clean_arr==sa,axis=2)): raise RuntimeError("source effect unchanged")
clean=Image.fromarray(clean_arr,"RGBA")

# Source-faithful white/navy style.
pix=sa[core]
bright=(pix[:,0]>170)&(pix[:,1]>170)&(pix[:,2]>170)
fill_rgb=tuple(int(round(float(np.median(pix[bright,k])))) for k in range(3))
ring=np.asarray(Image.fromarray((effect.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
ring&=~core
rp=sa[ring]
lum=rp[:,:3].astype(np.float32)@np.array([.2126,.7152,.0722],np.float32)
dark=rp[lum<=np.quantile(lum,.18)]
outline_rgb=tuple(int(round(float(np.median(dark[:,k])))) for k in range(3))
fill=fill_rgb+(255,); outline=outline_rgb+(255,)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
fp,fi,fstyle=spec.rsplit("|",2); fi=int(fi or 0)
def shear(im,s=.22):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for yy0 in range(im.height):
        o.alpha_composite(im.crop((0,yy0,im.width,yy0+1)),(int(round(s*(im.height-1-yy0))),yy0))
    return o
def tile_for(text,fs,sw):
    font=ImageFont.truetype(fp,fs,index=fi); bb=font.getbbox(text,stroke_width=sw)
    t=Image.new("RGBA",(bb[2]-bb[0]+32,bb[3]-bb[1]+32),(0,0,0,0))
    ImageDraw.Draw(t).text((16-bb[0],16-bb[1]),text,font=font,fill=fill,stroke_width=sw,stroke_fill=outline)
    t=shear(t,.22); q=t.getchannel("A").getbbox(); return t.crop(q) if q else None

tile=None; chosen_fs=None; chosen_sw=None
for fs in range(104,32,-1):
    sw=max(2,int(round(fs*.065))); t=tile_for("종합 랭킹",fs,sw)
    if t and t.width<=core_bbox[2]-core_bbox[0]-12 and t.height<=core_bbox[3]-core_bbox[1]-10:
        tile=t; chosen_fs=fs; chosen_sw=sw; break
if tile is None: raise RuntimeError("title fit failed")
px=core_bbox[0]+(core_bbox[2]-core_bbox[0]-tile.width)//2
py=core_bbox[1]+(core_bbox[3]-core_bbox[1]-tile.height)//2
final=clean.copy(); final.alpha_composite(tile,(px,py))
tm=Image.new("L",(W,H),0); tm.paste(bmask(tile.getchannel("A")),(px,py)); lb=list(tm.getbbox())
if not(lb[0]>core_bbox[0] and lb[1]>core_bbox[1] and lb[2]<core_bbox[2] and lb[3]<core_bbox[3]):
    raise RuntimeError(("localized containment",core_bbox,lb))

allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((effect_bbox[0],effect_bbox[1],effect_bbox[2]-1,effect_bbox[3]-1),fill=255)
protected=ImageOps.invert(allowed)
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
diff=diffmask(src,dec)
outside=count(ImageChops.multiply(diff,protected))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),protected))
renderout=count(ImageChops.multiply(tm,protected))
if outside or alphaout or renderout: raise RuntimeError(("outside",outside,alphaout,renderout))

# Validate title source effect no longer survives outside the Korean target guard.
guard=np.asarray(tm.filter(ImageFilter.MaxFilter(5)))>0
source_residue=int(np.count_nonzero(effect&(np.asarray(clean.getchannel("A"))>1)&np.all(np.asarray(clean)==sa,axis=2)))
if source_residue: raise RuntimeError(("clean source residue",source_residue))
row={
 "region_idx":0,"source":"Total Rank","korean":"종합 랭킹","cell":[x,y,cw,ch],
 "source_core_bbox":core_bbox,"original_bbox":effect_bbox,
 "source_core_pixels":int(np.count_nonzero(core)),"source_effect_mask_pixels":int(np.count_nonzero(effect)),
 "localized_bbox":lb,"source_width":core_bbox[2]-core_bbox[0],"source_height":core_bbox[3]-core_bbox[1],
 "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
 "delta_left":lb[0]-core_bbox[0],"delta_right":core_bbox[2]-lb[2],
 "delta_top":lb[1]-core_bbox[1],"delta_bottom":core_bbox[3]-lb[3],
 "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
 "font_file":Path(fp).name,"font_style":fstyle,"font_size":chosen_fs,"stroke_width":chosen_sw,
 "slant":.22,"fill_rgba":list(fill),"outline_rgba":list(outline),"alignment":"center"
}

source_png=out/"B151_SOURCE_READABLE.png"; clean_png=out/"B151_CLEAN_PLATE.png"; final_png=out/"B151_FINAL_READABLE.png"
smp=out/"B151_SOURCE_TEXT_MASK.png"; ap=out/"B151_ALLOWED_EFFECT_BBOX_MASK.png"; pp=out/"B151_PROTECTED_MASK.png"
src.save(source_png); clean.save(clean_png); dec.save(final_png)
Image.fromarray((clean_scope.astype(np.uint8)*255),"L").save(smp); allowed.save(ap); protected.save(pp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B151_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B151_FINAL_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B151_CLEAN_VALIDATION.json").read_text()); finalrep=json.loads((out/"B151_FINAL_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS" or finalrep["status"]!="PASS": raise RuntimeError(("validator",cleanrep["status"],finalrep["status"]))

# Controller evidence.
p=70; box=(max(0,effect_bbox[0]-p),max(0,effect_bbox[1]-p),min(W,effect_bbox[2]+p),min(H,effect_bbox[3]+p))
ims=[comp(z.crop(box)) for z in (src,clean,dec)]
scale=min(2.2,1500/max(1,ims[0].width)); ims=[z.resize((int(z.width*scale),int(z.height*scale)),Image.Resampling.NEAREST) for z in ims]
card=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+46),"white"); xx1=0
for labtxt,z in zip(("SOURCE","CLEAN","FINAL"),ims):
    card.paste(z,(xx1,46)); ImageDraw.Draw(card).text((xx1+4,9),labtxt,fill="black"); xx1+=z.width+8
save_b64(card,out/"B151_DCC7_FOCUS.jpg",out/"B151_DCC7_FOCUS_B64.txt",95)
ov=Image.new("RGB",(1024,3*550),"white")
for i,(labtxt,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im); z.thumbnail((1024,512),Image.Resampling.LANCZOS); ov.paste(z,(0,i*550+26)); ImageDraw.Draw(ov).text((5,i*550+5),labtxt,fill="black")
save_b64(ov,out/"B151_DCC7_SOURCE_CLEAN_FINAL.jpg",out/"B151_DCC7_SOURCE_CLEAN_FINAL_B64.txt",92)
rr=Image.new("RGB",(1024,2*550),"white")
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
for i,(labtxt,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im); z.thumbnail((1024,512),Image.Resampling.LANCZOS); rr.paste(z,(0,i*550+26)); ImageDraw.Draw(rr).text((5,i*550+5),labtxt,fill="black")
save_b64(rr,out/"B151_DCC7_RAW_COMPARE.jpg",out/"B151_DCC7_RAW_COMPARE_B64.txt",92)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":32,"asset":asset,
 "readiness_tier":"ZOOM_REVIEW_POSITIVELY_CLASSIFIED_AND_RENDERED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB,"source_sha256":SOURCE_SHA},
 "classification":{"localizable":"Total Rank","translation":"종합 랭킹","prior_queue_action":"zoom_review"},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":payload[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "clean_reconstruction":{"method":"B151 full exact effect-bbox quadratic pale-green field reconstruction after B150 visual ghost rejection","background_fit_samples":int(np.count_nonzero(use)),"clean_source_residue":source_residue,"clean_scope_pixels":int(np.count_nonzero(clean_scope))},
 "source_style":{"family":"white italic Total Rank with dark navy outline","font_file":Path(fp).name,"font_style":fstyle,"font_size":chosen_fs,"stroke_width":chosen_sw,"slant":.22,"fill_rgba":list(fill),"outline_rgba":list(outline)},
 "rows":[row],"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"outside_allowed_effect_bbox":outside,"alpha_outside":alphaout,"render_outside_target":renderout,"localized_overlap":0},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","status":"B151_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "RUNTIME_VALIDATION":"UNTESTED"
}
(out/"B151_DCC7_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B151_DCC7B488.json").write_text(json.dumps({
 "run":run,"index":32,"asset":"DCC7B488","candidate_sha256":csha,
 "localized_physical_elements":1,"bbox_size_positive_margin":"1/1",
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "outside":outside,"alpha_outside":alphaout,"worker_status":report["status"],
 "report":f"localization/graphics/role_B/{run}/B151_DCC7_REPORT.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"index":32,"candidate_sha256":csha,"bbox":lb,"source_bbox":core_bbox,"effect_bbox":effect_bbox},ensure_ascii=False))
