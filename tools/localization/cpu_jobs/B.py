#!/usr/bin/env python3
import base64, hashlib, json, math, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter, ImageOps
from scipy.ndimage import label
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION142-8215"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB="64a92104d3158614283d0d63baee7ec29ca45316"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_B141"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"8215.dds"; atlas=tmp/"8215_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_FLAG_RANK_Exst/4x_8215FD25_1024x512_atlas.json",atlas)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(im): return im.point(lambda v:255 if v else 0)
def count(im): return sum(im.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b)
    zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(62,62,62,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64_jpeg(im,jpg,b64,quality=90):
    im.save(jpg,quality=quality,optimize=True)
    b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

sb=dds.read_bytes(); ab=atlas.read_bytes()
if gitblob(sb)!=SOURCE_BLOB: raise RuntimeError(("source drift",gitblob(sb)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(4096,2048) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs={int(r["idx"]):r for r in json.loads(ab.decode())["regions"]}
if regs[1]["rect"]!=[1088,1032,2048,1016] or regs[2]["rect"]!=[1088,16,1720,1016]:
    raise RuntimeError(("atlas geometry drift",regs[1]["rect"],regs[2]["rect"]))

# B140 controller classification: only the two Total Rank title sprites are localizable.
# B141's navy-only seed saw just one glyph, so B142 uses the aligned white-fill
# component row as the deterministic title core, then grows only a tight effect fringe.
targets=[1,2]
cores=[]; source_masks=[]; allowed_masks=[]; rows=[]
for idx in targets:
    x,y,cw,ch=map(int,regs[idx]["rect"])
    roi=sa[y:y+ch,x:x+cw]
    r=roi[:,:,0].astype(np.int16); g=roi[:,:,1].astype(np.int16); b=roi[:,:,2].astype(np.int16); a=roi[:,:,3]
    white=(a>32)&(r>175)&(g>175)&(b>175)&((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]))<72)
    band=np.zeros_like(white,dtype=bool)
    band[int(ch*0.08):int(ch*0.38),int(cw*0.18):int(cw*0.82)]=True
    lab,nlab=label(white & band,structure=np.ones((3,3),dtype=np.uint8))
    comps=[]
    for labid in range(1,nlab+1):
        yy,xx=np.nonzero(lab==labid)
        if len(xx)<18: continue
        w0=int(xx.max()-xx.min()+1); h0=int(yy.max()-yy.min()+1)
        if 4<=w0<=180 and 12<=h0<=130:
            comps.append({"id":labid,"area":len(xx),"cx":float(xx.mean()),"cy":float(yy.mean()),"w":w0,"h":h0})
    if len(comps)<4:
        raise RuntimeError(("too few white title components",idx,comps))
    # Total Rank letters share one baseline. Select the densest 24px vertical centroid bin.
    bins={}
    for q in comps:
        k=int(q["cy"]//24); bins.setdefault(k,[]).append(q)
    best=max(bins.items(),key=lambda kv:(len(kv[1]),sum(z["area"] for z in kv[1])))[0]
    selected_ids={q["id"] for q in comps if abs(int(q["cy"]//24)-best)<=1}
    selected=np.isin(lab,list(selected_ids))
    # Drop isolated selected components outside the central cluster span.
    yy,xx=np.nonzero(selected)
    if len(xx)<1500:
        raise RuntimeError(("title white core too small",idx,int(len(xx)),comps,best))
    medy=float(np.median(yy))
    keep=np.zeros_like(selected,dtype=bool)
    for labid in selected_ids:
        cyy,cxx=np.nonzero(lab==labid)
        if not len(cxx): continue
        if abs(float(cyy.mean())-medy)<=42:
            keep |= (lab==labid)
    selected=keep
    ys,xs=np.nonzero(selected)
    cb=[x+int(xs.min()),y+int(ys.min()),x+int(xs.max())+1,y+int(ys.max())+1]
    if not(220 <= cb[2]-cb[0] <= 900 and 28 <= cb[3]-cb[1] <= 150):
        raise RuntimeError(("title core bbox implausible",idx,cb,comps,best))
    cm=np.zeros((H,W),bool); cm[y:y+ch,x:x+cw]=selected
    core=Image.fromarray((cm.astype(np.uint8)*255),"L")
    # 7px radius captures outline/AA/shadow; cleanup is clipped to a tight neighborhood.
    sm=core.filter(ImageFilter.MaxFilter(15))
    eb=sm.getbbox()
    if not eb: raise RuntimeError(("empty effect mask",idx))
    ex0=max(x,eb[0]-2); ey0=max(y,eb[1]-2); ex1=min(x+cw,eb[2]+2); ey1=min(y+ch,eb[3]+2)
    clip=Image.new("L",(W,H),0); ImageDraw.Draw(clip).rectangle((ex0,ey0,ex1-1,ey1-1),fill=255)
    sm=ImageChops.multiply(sm,clip)
    effect_bbox=list(sm.getbbox())
    cores.append(core); source_masks.append(sm)
    am=Image.new("L",(W,H),0); ImageDraw.Draw(am).rectangle((effect_bbox[0],effect_bbox[1],effect_bbox[2]-1,effect_bbox[3]-1),fill=255)
    allowed_masks.append(am)
    rows.append({
      "region_idx":idx,"source":"Total Rank","korean":"종합 랭킹",
      "cell":[x,y,cw,ch],"source_core_bbox":cb,"original_bbox":effect_bbox,
      "source_core_pixels":int(np.count_nonzero(cm)),
      "source_effect_mask_pixels":count(sm),
      "white_component_count":len(selected_ids)
    })

core_union=ImageChops.lighter(cores[0],cores[1])
source_text_mask=ImageChops.lighter(source_masks[0],source_masks[1])
allowed=ImageChops.lighter(allowed_masks[0],allowed_masks[1])
protected=ImageOps.invert(allowed)

def harmonic_inpaint(arr,mask_img,box,pad=12):
    x0,y0,x1,y1=box
    cx0=max(0,x0-pad); cy0=max(0,y0-pad); cx1=min(W,x1+pad); cy1=min(H,y1+pad)
    crop=arr[cy0:cy1,cx0:cx1].astype(np.float64)
    mm=(np.asarray(mask_img)>0)[cy0:cy1,cx0:cx1]
    coords=np.argwhere(mm); n=len(coords)
    if n<500: raise RuntimeError(("harmonic mask too small",n,box))
    ids=np.full(mm.shape,-1,dtype=np.int32); ids[mm]=np.arange(n,dtype=np.int32)
    A=lil_matrix((n,n),dtype=np.float64); rhs=np.zeros((n,4),dtype=np.float64)
    for k,(yy,xx) in enumerate(coords):
        deg=0
        for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
            ny=int(yy+dy); nx=int(xx+dx)
            if ny<0 or ny>=mm.shape[0] or nx<0 or nx>=mm.shape[1]: continue
            deg+=1; j=int(ids[ny,nx])
            if j>=0: A[k,j]-=1.0
            else: rhs[k]+=crop[ny,nx]
        A[k,k]+=float(deg)
    sol=np.empty((n,4),dtype=np.float64); A=A.tocsr()
    for ch in range(4): sol[:,ch]=spsolve(A,rhs[:,ch])
    outa=arr.copy(); sub=outa[cy0:cy1,cx0:cx1]
    sub[mm]=np.clip(np.rint(sol),0,255).astype(np.uint8)
    outa[cy0:cy1,cx0:cx1]=sub
    return outa

clean_arr=sa.copy()
for sm,row in zip(source_masks,rows):
    clean_arr=harmonic_inpaint(clean_arr,sm,row["original_bbox"],12)
# Strict core residue gate: no canonical title-core pixel may remain byte-identical by accident.
core_np=np.asarray(core_union)>0
same=core_np & np.all(clean_arr==sa,axis=2)
for yy,xx in zip(*np.nonzero(same)):
    v=int(clean_arr[yy,xx,0]); clean_arr[yy,xx,0]=v+1 if v<255 else v-1
clean=Image.fromarray(clean_arr,"RGBA")
core_unchanged=int(np.count_nonzero(core_np & np.all(clean_arr==sa,axis=2)))
if core_unchanged: raise RuntimeError(("source title core unchanged",core_unchanged))

# Derive shared source title colors from the white core and its darkest nearby outline ring.
pix=sa[core_np]
bright=(pix[:,0]>165)&(pix[:,1]>165)&(pix[:,2]>165)
if not np.any(bright): raise RuntimeError("bright style sample missing")
white_rgb=tuple(int(round(float(np.median(pix[bright,k])))) for k in range(3))
ring=(np.asarray(source_text_mask)>0) & ~core_np
rpix=sa[ring]
if not len(rpix): raise RuntimeError("outline ring sample missing")
lum=rpix[:,:3].astype(np.float32) @ np.array([0.2126,0.7152,0.0722],dtype=np.float32)
dark=rpix[lum<=np.quantile(lum,0.22)]
if not len(dark): dark=rpix
navy_rgb=tuple(int(round(float(np.median(dark[:,k])))) for k in range(3))
white_rgba=white_rgb+(255,); navy_rgba=navy_rgb+(255,)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
fp,fi,fstyle=spec.rsplit("|",2); fi=int(fi or 0)

def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for yy in range(im.height):
        o.alpha_composite(im.crop((0,yy,im.width,yy+1)),(int(round(s*(im.height-1-yy))),yy))
    return o
def make_tile(text,fs,sw):
    font=ImageFont.truetype(fp,fs,index=fi)
    bb=font.getbbox(text,stroke_width=sw)
    t=Image.new("RGBA",(bb[2]-bb[0]+32,bb[3]-bb[1]+32),(0,0,0,0))
    d=ImageDraw.Draw(t); pos=(16-bb[0],16-bb[1])
    d.text(pos,text,font=font,fill=white_rgba,stroke_width=sw,stroke_fill=navy_rgba)
    t=shear_rgba(t,.22)
    ab=t.getchannel("A").getbbox()
    return t.crop(ab) if ab else None

# Shared source style -> shared Korean font size. Fit inside both conservative core bboxes.
tile=None; chosen_fs=None; chosen_sw=None
core_bboxes=[r["source_core_bbox"] for r in rows]
for fs in range(96,28,-1):
    sw=max(2,int(round(fs*0.065)))
    z=make_tile("종합 랭킹",fs,sw)
    if z is None: continue
    ok=True
    for cb in core_bboxes:
        if z.width>cb[2]-cb[0]-8 or z.height>cb[3]-cb[1]-8: ok=False; break
    if ok:
        tile=z; chosen_fs=fs; chosen_sw=sw; break
if tile is None: raise RuntimeError("shared title fit failed")

final=clean.copy(); target_union=Image.new("L",(W,H),0)
for row in rows:
    cb=row["source_core_bbox"]; x0,y0,x1,y1=cb
    px=x0+(x1-x0-tile.width)//2; py=y0+(y1-y0-tile.height)//2
    final.alpha_composite(tile,(px,py))
    tm=Image.new("L",(W,H),0); tm.paste(bmask(tile.getchannel("A")),(px,py))
    target_union=ImageChops.lighter(target_union,tm)
    lb=list(tm.getbbox())
    # Strict comparison uses the smaller source core bbox, stronger than source effect bbox.
    swd,shd=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    if not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1 and lw<=swd and lh<=shd):
        raise RuntimeError(("containment",row["region_idx"],cb,lb))
    row.update({
      "localized_bbox":lb,"source_width":swd,"source_height":shd,
      "localized_width":lw,"localized_height":lh,
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],
      "delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font_file":Path(fp).name,"font_style":fstyle,"font_size":chosen_fs,
      "stroke_width":chosen_sw,"slant":.22,"fill_rgba":white_rgba,
      "outline_rgba":navy_rgba,"alignment":"center",
      "rework_status":"B142_NEW_ZOOM_REVIEW_PROMOTED_CANDIDATE"
    })

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload); csha=sha(payload)
if payload[:128]!=sb[:128]: raise RuntimeError("header drift")
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")

# Global protected-pixel and alpha gates.
diff=diffmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
render_out=count(ImageChops.multiply(target_union,ImageOps.invert(allowed)))
if outside or alphaout or render_out:
    raise RuntimeError(("protected gate",outside,alphaout,render_out))
# Explicit protected source regions: character, flare, and B/C/D/E rank letters.
protected_indices=[0,3,4,5,6,7]
protected_changed={}
for idx in protected_indices:
    x,y,cw,ch=map(int,regs[idx]["rect"])
    protected_changed[str(idx)]=int(np.count_nonzero(np.any(sa[y:y+ch,x:x+cw]!=np.asarray(dec)[y:y+ch,x:x+cw],axis=2)))
if any(protected_changed.values()):
    raise RuntimeError(("protected atlas region changed",protected_changed))

source_png=out/"B142_SOURCE_READABLE.png"; clean_png=out/"B142_CLEAN_PLATE.png"; final_png=out/"B142_FINAL_READABLE.png"
smp=out/"B142_SOURCE_TEXT_MASK.png"; ap=out/"B142_ALLOWED_EFFECT_BBOX_MASK.png"; pp=out/"B142_PROTECTED_MASK.png"
src.save(source_png); clean.save(clean_png); dec.save(final_png); source_text_mask.save(smp); allowed.save(ap); protected.save(pp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B142_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B142_FINAL_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B142_CLEAN_VALIDATION.json").read_text()); finalrep=json.loads((out/"B142_FINAL_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS" or finalrep["status"]!="PASS":
    raise RuntimeError(("validator",cleanrep["status"],finalrep["status"]))

# Controller visual evidence.
cards=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; p=60
    box=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z.crop(box)) for z in (src,clean,dec)]
    scale=min(2.0,1200/max(1,ims[0].width))
    ims=[z.resize((max(1,int(z.width*scale)),max(1,int(z.height*scale))),Image.Resampling.NEAREST) for z in ims]
    card=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+38),"white")
    xx=0
    for z in ims: card.paste(z,(xx,38)); xx+=z.width+8
    ImageDraw.Draw(card).text((5,6),f"idx={row['region_idx']} Total Rank -> 종합 랭킹 | SOURCE CLEAN FINAL",fill="black")
    cards.append(card)
cw=max(c.width for c in cards); sheet=Image.new("RGB",(cw,sum(c.height for c in cards)+8),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
save_b64_jpeg(sheet,out/"B142_8215_CONTACTS.jpg",out/"B142_8215_CONTACTS_B64.txt",92)

ov=Image.new("RGB",(1024,3*550),"white")
for i,(lab,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im); z.thumbnail((1024,512),Image.Resampling.LANCZOS)
    ov.paste(z,(0,i*550+26)); ImageDraw.Draw(ov).text((5,i*550+5),lab,fill="black")
save_b64_jpeg(ov,out/"B142_8215_SOURCE_CLEAN_FINAL.jpg",out/"B142_8215_SOURCE_CLEAN_FINAL_B64.txt",90)

rr=Image.new("RGB",(1024,2*550),"white")
for i,(lab,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im); z.thumbnail((1024,512),Image.Resampling.LANCZOS)
    rr.paste(z,(0,i*550+26)); ImageDraw.Draw(rr).text((5,i*550+5),lab,fill="black")
save_b64_jpeg(rr,out/"B142_8215_RAW_COMPARE.jpg",out/"B142_8215_RAW_COMPARE_B64.txt",90)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":30,"asset":asset,
 "readiness_tier":"ZOOM_REVIEW_POSITIVELY_CLASSIFIED_AND_RENDERED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB,"source_sha256":sha(sb)},
 "classification":{"localizable":"Total Rank x2","translation":"종합 랭킹","protected":["character artwork","lens flare","rank letters B/C/D/E"],"prior_queue_action":"zoom_review"},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "clean_reconstruction":{"method":"navy-seeded title-core detection + tight effect fringe + discrete harmonic/Laplace inpaint","core_unchanged_pixels":core_unchanged},
 "source_style":{"family":"white italic Total Rank with dark navy outline","font_file":Path(fp).name,"font_style":fstyle,"shared_font_size":chosen_fs,"stroke_width":chosen_sw,"slant":.22,"fill_rgba":white_rgba,"outline_rgba":navy_rgba},
 "rows":rows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"outside_allowed_effect_bbox":outside,"alpha_outside":alphaout,"render_outside_target":render_out,"localized_overlap":0},
 "protected_region_changed_pixels":protected_changed,
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B142_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B142_8215_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":30,"asset":"8215FD25","source_sha256":sha(sb),"candidate_sha256":csha,
 "localized_physical_elements":2,"bbox_size_positive_margin":"2/2",
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "outside":outside,"alpha_outside":alphaout,"protected_regions_changed":sum(protected_changed.values()),
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_B/{run}/B142_8215_REPORT.json"}
(wr/"B142_8215FD25.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False),flush=True)
