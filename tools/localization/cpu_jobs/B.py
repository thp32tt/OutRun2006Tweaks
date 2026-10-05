#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,subprocess,statistics
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")
repo=Path.cwd()
run="20261005-B-PRODUCTION113"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/b113"); tmp.mkdir(exist_ok=True)
dds=tmp/"src.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_CLAR_RANK_Exst/4x_A05BF610_512x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def bmask(im): return im.point(lambda v:255 if v else 0)
def count(im): return sum(im.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

if blob(sb)!="1ed3fc83fc0501ac6420c0b3e3c51b7f0c9b1374": raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="a3e4b8b6cdc953ad1f83a7bbba679f1f71fbf2b2": raise RuntimeError(("atlas drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(2048,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs={int(r["idx"]):r for r in json.loads(ab.decode())["regions"]}
if regs[0]["rect"]!=[0,1032,1640,1016] or regs[1]["rect"]!=[0,16,1016,1016]: raise RuntimeError(("atlas geometry",regs))

# Region 0 is the oval Total Rank plate; region 1 is protected lens-flare artwork.
x,y,cw,ch=regs[0]["rect"]
rx0=x+int(cw*.12); rx1=x+int(cw*.88)
ry0=y+int(ch*.02); ry1=y+int(ch*.34)
roi=sa[ry0:ry1,rx0:rx1]
r=roi[:,:,0].astype(np.int16); g=roi[:,:,1].astype(np.int16); b=roi[:,:,2].astype(np.int16); a=roi[:,:,3]
white=(a>32)&(r>220)&(g>220)&(b>220)&((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]))<24)
navy=(a>32)&(b>r+10)&(b>g+5)&(r<110)&(g<110)&(b<180)

# Isolate the dark title outline by connected components. The oval navy border is one
# very large component; title letters are compact components near the upper center.
from scipy import ndimage as ndi
lab,ncomp=ndi.label(navy)
parts=[]
for k in range(1,ncomp+1):
    yy,xx=np.nonzero(lab==k)
    if len(xx)<80:
        continue
    x0=int(xx.min()); x1=int(xx.max())+1; y0=int(yy.min()); y1=int(yy.max())+1
    bw=x1-x0; bh=y1-y0; cx=(x0+x1)/2; cy=(y0+y1)/2
    if 8<=bw<=260 and 18<=bh<=150 and roi.shape[1]*.15<cx<roi.shape[1]*.85 and roi.shape[0]*.05<cy<roi.shape[0]*.70:
        parts.append((len(xx),x0,y0,x1,y1))
if len(parts)<4:
    raise RuntimeError(("insufficient title navy components",len(parts),sorted(parts,reverse=True)[:12]))
# Keep the compact letter components clustered around the median component y-center.
centers=np.array([((p[1]+p[3])/2,(p[2]+p[4])/2) for p in parts],dtype=np.float32)
medy=float(np.median(centers[:,1]))
parts=[p for p in parts if abs(((p[2]+p[4])/2)-medy)<70]
if len(parts)<4:
    raise RuntimeError(("title component y cluster too small",len(parts),medy))
ux0=max(0,min(p[1] for p in parts)-5); uy0=max(0,min(p[2] for p in parts)-5)
ux1=min(roi.shape[1],max(p[3] for p in parts)+5); uy1=min(roi.shape[0],max(p[4] for p in parts)+5)
core=np.zeros_like(white)
core[uy0:uy1,ux0:ux1]=(white|navy)[uy0:uy1,ux0:ux1]
cy,cx=np.nonzero(core)
if len(cx)<1000: raise RuntimeError(("title core too small",len(cx),[ux0,uy0,ux1,uy1]))
m=np.zeros((H,W),bool); m[ry0:ry1,rx0:rx1]=core
source_mask=Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(7))
sm=np.asarray(source_mask)>0
ys2,xs2=np.nonzero(sm)
ob=[int(xs2.min()),int(ys2.min()),int(xs2.max())+1,int(ys2.max())+1]
if (ob[2]-ob[0])>cw*.48 or (ob[3]-ob[1])>ch*.16:
    raise RuntimeError(("title bbox implausible",ob,"parts",parts))
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
protected=ImageOps.invert(allowed)

# Clean plate: row-wise interior-color reconstruction from protected side bands.
# The oval interior is a smooth green plate; avoid pulling its cyan/navy border.
clean_arr=sa.copy()
bx0,by0,bx1,by1=ob
row_colors=[]
for yy in range(by0,by1):
    parts=[]
    for xa,xb in [(max(x,bx0-180),max(x,bx0-30)),(min(x+cw,bx1+30),min(x+cw,bx1+180))]:
        if xb>xa:
            p=sa[yy,xa:xb]
            # Use opaque, midtone interior pixels; exclude bright cyan edge/glow and dark outline.
            keep=(p[:,3]>180)&(p[:,:3].min(axis=1)>70)&(p[:,:3].max(axis=1)<220)
            if np.any(keep): parts.append(p[keep])
    vals=np.concatenate(parts,axis=0) if parts else np.empty((0,4),dtype=np.uint8)
    if len(vals):
        row_colors.append(np.median(vals.astype(np.float32),axis=0))
    else:
        row_colors.append(None)
valid=[i for i,v in enumerate(row_colors) if v is not None]
if not valid: raise RuntimeError("no clean-plate side samples")
for i in range(len(row_colors)):
    if row_colors[i] is None: row_colors[i]=row_colors[min(valid,key=lambda j:abs(j-i))]
rc=np.stack(row_colors,axis=0).astype(np.float32)
# smooth only along y to retain the source's vertical gradient family
kernel=np.array([1,2,3,4,5,4,3,2,1],dtype=np.float32); kernel/=kernel.sum()
for c in range(4): rc[:,c]=np.convolve(rc[:,c],kernel,mode="same")
for yy in range(by0,by1):
    maskrow=sm[yy]
    if np.any(maskrow): clean_arr[yy,maskrow]=np.clip(np.rint(rc[yy-by0]),0,255).astype(np.uint8)
clean=Image.fromarray(clean_arr,"RGBA")

source_png=out/"A05_SOURCE_READABLE.png"; clean_png=out/"A05_CLEAN_PLATE.png"; smp=out/"A05_SOURCE_TEXT_MASK.png"; ap=out/"A05_ALLOWED_BBOX_MASK.png"; pp=out/"A05_PROTECTED_MASK.png"
src.save(source_png); clean.save(clean_png); source_mask.save(smp); allowed.save(ap); protected.save(pp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(smp),"--protected-mask",str(pp),"--report",str(out/"B113_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B113_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))
unchanged=count(ImageChops.multiply(source_mask,ImageOps.invert(diffmask(src,clean))))
if unchanged!=0: raise RuntimeError(("source mask unchanged",unchanged))

# Source colors from strict title core.
pix=sa[m]
white_sel=(pix[:,0]>165)&(pix[:,1]>165)&(pix[:,2]>165)
navy_sel=(pix[:,2].astype(int)>pix[:,0].astype(int)+10)&(pix[:,2].astype(int)>pix[:,1].astype(int)+5)&(pix[:,0]<110)&(pix[:,1]<110)
white_rgb=tuple(int(round(float(np.median(pix[white_sel,k])))) for k in range(3))
navy_rgb=tuple(int(round(float(np.median(pix[navy_sel,k])))) for k in range(3))
white_rgba=white_rgb+(255,); navy_rgba=navy_rgb+(255,)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
fp,fi,fstyle=spec.rsplit("|",2); fi=int(fi or 0)
def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for yy in range(im.height): o.alpha_composite(im.crop((0,yy,im.width,yy+1)),(int(round(s*(im.height-1-yy))),yy))
    return o
def tile_for(fs):
    font=ImageFont.truetype(fp,fs,index=fi); sw=max(2,round(fs*.075)); text="종합 랭킹"
    d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=font,stroke_width=sw)
    pad=sw+5; size=(bb[2]-bb[0]+2*pad,bb[3]-bb[1]+2*pad); pos=(pad-bb[0],pad-bb[1])
    om=Image.new("L",size,0); fm=Image.new("L",size,0)
    ImageDraw.Draw(om).text(pos,text,font=font,fill=255,stroke_width=sw,stroke_fill=255)
    ImageDraw.Draw(fm).text(pos,text,font=font,fill=255)
    t=Image.new("RGBA",size,(0,0,0,0)); t.paste(navy_rgba,(0,0),om); t.paste(white_rgba,(0,0),fm); t=shear_rgba(t,.22)
    bb=t.getchannel("A").getbbox(); return (t.crop(bb),sw) if bb else (None,sw)
aw,ah=ob[2]-ob[0],ob[3]-ob[1]
chosen=None
for fs in range(110,20,-1):
    t,sw=tile_for(fs)
    if t and t.width<=aw-8 and t.height<=ah-8: chosen=(t,sw,fs); break
if not chosen: raise RuntimeError("Hangul fit failed")
tile,sw,fs=chosen
px=ob[0]+(aw-tile.width)//2; py=ob[1]+(ah-tile.height)//2
final=clean.copy(); final.alpha_composite(tile,(px,py))
target=Image.new("L",(W,H),0); target.paste(bmask(tile.getchannel("A")),(px,py)); lb=list(target.getbbox())
if not(lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]): raise RuntimeError(("containment",ob,lb))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload); csha=sha(payload)
if payload[:128]!=sb[:128]: raise RuntimeError("header drift")
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
final_png=out/"A05_FINAL_DECODED_READABLE.png"; dec.save(final_png)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B113_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B113_FINAL_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final validator",finalrep))
diff=diffmask(src,dec); outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
render_out=count(ImageChops.multiply(target,ImageOps.invert(allowed)))
# Region 1 protected cell must remain pixel exact.
rx,ry,rw,rh=regs[1]["rect"]
protected_cell_changes=count(diffmask(src.crop((rx,ry,rx+rw,ry+rh)),dec.crop((rx,ry,rx+rw,ry+rh))))
if outside or alphaout or render_out or protected_cell_changes: raise RuntimeError(("gate",outside,alphaout,render_out,protected_cell_changes))

# Evidence.
sheet=Image.new("RGB",(1024,3*1050),"white")
for i,(lab,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.LANCZOS); sheet.paste(z,(0,i*1050+26)); ImageDraw.Draw(sheet).text((5,i*1050+5),lab,fill="black")
sheet.save(out/"B113_A05_SOURCE_CLEAN_FINAL.jpg",quality=96)
margin=40; box=(max(0,ob[0]-margin),max(0,ob[1]-margin),min(W,ob[2]+margin),min(H,ob[3]+margin))
ims=[comp(z.crop(box)) for z in [src,clean,dec]]
row=Image.new("RGB",(sum(i.width for i in ims)+16,max(i.height for i in ims)+28),"white"); xx=0
for im in ims: row.paste(im,(xx,28)); xx+=im.width+8
ImageDraw.Draw(row).text((4,4),"Total Rank -> 종합 랭킹   SOURCE | CLEAN | FINAL",fill="black"); row.save(out/"B113_A05_ROW_CONTACT.jpg",quality=96)
rr=Image.new("RGB",(1024,2*1050),"white")
for i,(lab,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1050+26)); ImageDraw.Draw(rr).text((5,i*1050+5),lab,fill="black")
rr.save(out/"B113_A05_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"B","run":run,"queue_index":28,"asset":asset,
 "readiness_tier":"ZOOM_REVIEW_PROMOTED_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"region0":"Total Rank -> 종합 랭킹","region1":"lens flare artwork -> preserve"},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "row":{"region_idx":0,"source":"Total Rank","korean":"종합 랭킹","original_bbox":ob,"localized_bbox":lb,
        "source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
        "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_file":Path(fp).name,"font_style":fstyle,"font_size":fs,"stroke_width":sw,"slant":.22,
        "fill_rgba":white_rgba,"outline_rgba":navy_rgba,"alignment":"center"},
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"outside":outside,"alpha_outside":alphaout,"render_outside_target":render_out,"protected_lens_flare_cell_changed":protected_cell_changes,"localized_overlap":0},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B113_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"B113_A05_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":28,"asset":"A05BF610","source_sha256":sha(sb),"candidate_sha256":csha,"localized_physical_elements":1,
 "bbox_size_positive_margin":"1/1","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "outside":outside,"alpha_outside":alphaout,"protected_lens_flare_cell_changed":protected_cell_changes,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{run}/B113_A05_REPORT.json"}
(wr/"B113_A05BF610.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
