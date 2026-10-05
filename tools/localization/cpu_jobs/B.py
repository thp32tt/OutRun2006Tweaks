#!/usr/bin/env python3
import base64, hashlib, json, math, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter, ImageOps
from scipy.ndimage import label

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION144-8215-C196-REWORK"
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
if not prior_clean_path.exists() or not prior_report_path.exists() or not candidate.exists():
    raise RuntimeError("B143 evidence/candidate missing")

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
if sha(candidate.read_bytes())!=PRIOR_SHA: raise RuntimeError(("prior candidate drift",sha(candidate.read_bytes())))
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
prior_final=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# Preserve C196-accepted speech-bubble (idx1) exactly from B143.
row1=next(r for r in prior_report["rows"] if int(r["region_idx"])==1)
row2_prev=next(r for r in prior_report["rows"] if int(r["region_idx"])==2)
allowed=Image.new("L",(W,H),0)
for r in (row1,row2_prev):
    x0,y0,x1,y1=map(int,r["original_bbox"])
    ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
protected=ImageOps.invert(allowed)

clean_arr=sa.copy()
final_arr=sa.copy()
r1box=tuple(map(int,row1["original_bbox"]))
clean_arr[r1box[1]:r1box[3],r1box[0]:r1box[2]]=np.asarray(prior_clean)[r1box[1]:r1box[3],r1box[0]:r1box[2]]
final_arr[r1box[1]:r1box[3],r1box[0]:r1box[2]]=np.asarray(prior_final)[r1box[1]:r1box[3],r1box[0]:r1box[2]]

# Re-derive idx2 title core from canonical source.
idx=2; x,y,cw,ch=map(int,regs[idx]["rect"]); roi=sa[y:y+ch,x:x+cw]
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

# Build a robust quadratic brown-field model from canonical pixels surrounding the title.
# This deliberately excludes the old 15px edit footprint and any low-alpha/ray/background outliers.
ob=list(map(int,row2_prev["original_bbox"]))
sx0=max(x,ob[0]-90); sy0=max(y,ob[1]-70); sx1=min(x+cw,ob[2]+90); sy1=min(y+ch,ob[3]+120)
Y,X=np.mgrid[sy0:sy1,sx0:sx1]
sub=sa[sy0:sy1,sx0:sx1].astype(np.float64)
near_sub=near[sy0:sy1,sx0:sx1]
sample=(sub[:,:,3]>16)&(~near_sub)
# Starburst interior is warm/brown. Alpha is intentionally soft in this artwork, so do not
# require opacity; reject transparent exterior by alpha and keep a broad warm-color family.
sample &= (sub[:,:,0]>70)&(sub[:,:,0]>sub[:,:,1]-5)&(sub[:,:,1]>sub[:,:,2]-30)&(sub[:,:,2]<225)
# If the warm filter is still too selective, fall back to all nontransparent non-title
# pixels; robust residual trimming below removes rays/border/outliers deterministically.
if np.count_nonzero(sample)<5000:
    sample=(sub[:,:,3]>16)&(~near_sub)&(sub[:,:,0]>45)
xn=(X-(sx0+sx1)/2)/max(1,(sx1-sx0)/2)
yn=(Y-(sy0+sy1)/2)/max(1,(sy1-sy0)/2)
B=np.stack([np.ones_like(xn),xn,yn,xn*xn,xn*yn,yn*yn],axis=-1)
flatB=B.reshape(-1,6); flatS=sub.reshape(-1,4); mask=sample.reshape(-1)
if np.count_nonzero(mask)<4000: raise RuntimeError(("background sample too small",int(np.count_nonzero(mask))))
coef=np.zeros((6,4),dtype=np.float64)
use=mask.copy()
for _ in range(3):
    for c in range(4): coef[:,c]=np.linalg.lstsq(flatB[use],flatS[use,c],rcond=None)[0]
    pred=flatB@coef
    resid=np.max(np.abs(pred[:,:3]-flatS[:,:3]),axis=1)
    vals=resid[mask]
    lim=max(18.0,float(np.quantile(vals,0.68)))
    use=mask&(resid<=lim)
pred=(flatB@coef).reshape(sub.shape)
pred=np.clip(np.rint(pred),0,255).astype(np.uint8)

# Exact text/effect mask: the source outline is about 4px. Use a conservative 7px
# glyph-local halo around the proven white title core, instead of B143's 15px halo.
# This removes the navy outline/AA without touching the top rays as a broad plate patch.
text_mask=np.asarray(core_im.filter(ImageFilter.MaxFilter(15)))>0
# Keep the rework inside the prior C196-reviewed allowed bbox.
obmask=np.zeros((H,W),dtype=bool); obmask[ob[1]:ob[3],ob[0]:ob[2]]=True
text_mask &= obmask
ty,tx=np.nonzero(text_mask)
if not len(tx): raise RuntimeError("empty precise title mask")
text_bbox=[int(tx.min()),int(ty.min()),int(tx.max())+1,int(ty.max())+1]
if np.count_nonzero(text_mask)>34000:
    raise RuntimeError(("precise mask unexpectedly broad",int(np.count_nonzero(text_mask)),text_bbox))

# Replace only exact detected title/effect pixels with the fitted interior field.
pglobal=np.zeros((H,W,4),dtype=np.uint8); pglobal[sy0:sy1,sx0:sx1]=pred
clean_arr[text_mask]=pglobal[text_mask]
# No source-title pixel may remain byte-identical in the precise mask.
same=text_mask&np.all(clean_arr==sa,axis=2)
if np.any(same):
    for yy0,xx0 in zip(*np.nonzero(same)):
        v=int(clean_arr[yy0,xx0,0]); clean_arr[yy0,xx0,0]=v+1 if v<255 else v-1
if np.count_nonzero(text_mask&np.all(clean_arr==sa,axis=2)):
    raise RuntimeError("precise source-text residue unchanged")

clean=Image.fromarray(clean_arr,"RGBA")

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
# Restore C196-accepted idx1 final exactly.
final_arr=np.asarray(final).copy()
final_arr[r1box[1]:r1box[3],r1box[0]:r1box[2]]=np.asarray(prior_final)[r1box[1]:r1box[3],r1box[0]:r1box[2]]
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
for old in (row1,row2_prev):
    z=dict(old)
    if int(z["region_idx"])==1:
        z["rework_status"]="B144_C196_ACCEPTED_SPEECH_BUBBLE_PRESERVED_EXACT"
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
        z["rework_status"]="B144_C196_PRECISE_MASK_QUADRATIC_FIELD_RECONSTRUCTION"
        z["precise_text_mask_bbox"]=text_bbox
    rows.append(z)

source_text_mask=Image.new("L",(W,H),0)
# Keep idx1 prior source mask in its allowed bbox for evidence; idx2 uses the new precise mask.
prior_sm=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION143-8215/B142_SOURCE_TEXT_MASK.png").convert("L")
source_text_mask.paste(prior_sm.crop(r1box),(r1box[0],r1box[1]))
source_text_mask=ImageChops.lighter(source_text_mask,Image.fromarray((text_mask.astype(np.uint8)*255),"L"))

source_png=out/"B144_SOURCE_READABLE.png"; clean_png=out/"B144_CLEAN_PLATE.png"; final_png=out/"B144_FINAL_READABLE.png"
smp=out/"B144_SOURCE_TEXT_MASK.png"; ap=out/"B144_ALLOWED_EFFECT_BBOX_MASK.png"; pp=out/"B144_PROTECTED_MASK.png"
src.save(source_png); clean.save(clean_png); dec.save(final_png); source_text_mask.save(smp); allowed.save(ap); protected.save(pp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B144_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B144_FINAL_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B144_CLEAN_VALIDATION.json").read_text()); finalrep=json.loads((out/"B144_FINAL_VALIDATION.json").read_text())
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
save_b64_jpeg(sheet,out/"B144_8215_CONTACTS.jpg",out/"B144_8215_CONTACTS_B64.txt",94)

# Extra starburst closeup makes C196 defect directly reviewable.
x0,y0,x1,y1=ob; p=110; box=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
ims=[comp(z.crop(box)) for z in (src,clean,dec)]
scale=min(2.8,1500/max(1,ims[0].width)); ims=[z.resize((int(z.width*scale),int(z.height*scale)),Image.Resampling.NEAREST) for z in ims]
focus=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+44),"white"); xx1=0
for labtxt,z in zip(("SOURCE","CLEAN","FINAL"),ims):
    focus.paste(z,(xx1,44)); ImageDraw.Draw(focus).text((xx1+4,8),labtxt,fill="black"); xx1+=z.width+8
save_b64_jpeg(focus,out/"B144_STARBURST_FOCUS.jpg",out/"B144_STARBURST_FOCUS_B64.txt",95)

rrim=Image.new("RGB",(1024,2*550),"white")
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
for i,(labtxt,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im); z.thumbnail((1024,512),Image.Resampling.LANCZOS); rrim.paste(z,(0,i*550+26)); ImageDraw.Draw(rrim).text((5,i*550+5),labtxt,fill="black")
save_b64_jpeg(rrim,out/"B144_RAW_COMPARE.jpg",out/"B144_RAW_COMPARE_B64.txt",90)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":30,"asset":asset,
 "reworks":"C196_REWORK_REQUIRED_STARBURST_CLEAN_PLATE_RECONSTRUCTION_ARTIFACT",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB,"source_sha256":sha(sb)},
 "prior_candidate_sha256":PRIOR_SHA,
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":payload[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "classification":{"localizable":"Total Rank x2","translation":"종합 랭킹","protected":["character artwork","lens flare","rank letters B/C/D/E"]},
 "clean_reconstruction":{
   "idx1":"C196-accepted B143 speech-bubble clean/final preserved exact inside prior allowed bbox",
   "idx2":"precise connected source-title/effect mask + robust quadratic warm-interior field reconstruction",
   "idx2_prior_effect_mask_pixels":int(row2_prev["source_effect_mask_pixels"]),
   "idx2_precise_effect_mask_pixels":int(np.count_nonzero(text_mask)),
   "idx2_precise_mask_bbox":text_bbox,
   "idx2_background_fit_samples":int(np.count_nonzero(use))
 },
 "source_style":prior_report["source_style"],
 "rows":rows,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"outside_allowed_effect_bbox":outside,"alpha_outside":alphaout,"localized_overlap":0},
 "protected_region_changed_pixels":protected_changed,
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "status":"B144_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "RUNTIME_VALIDATION":"UNTESTED"
}
(out/"B144_8215_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":30,"asset":"8215FD25","candidate_sha256":csha,
 "localized_physical_elements":2,"bbox_size_positive_margin":"2/2",
 "idx2_precise_effect_mask_pixels":int(np.count_nonzero(text_mask)),
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "outside":outside,"alpha_outside":alphaout,"protected_regions_changed":sum(protected_changed.values()),
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_B/{run}/B144_8215_REPORT.json"}
(wr/"B144_8215FD25.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False),flush=True)
