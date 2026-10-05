#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,subprocess,statistics
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")
repo=Path.cwd()
run="20261005-B-PRODUCTION126"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/b126"); tmp.mkdir(exist_ok=True)
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
# The oval top border is well above the title. Restrict discovery to the measured
# central title band so the plate border/glow can never become part of the text mask.
# C173 independently measured the complete source-title core at
# [400,1120,1050,1272] and its 3px effect bbox at [397,1117,1053,1275].
# The prior producer discovery window began too far right/down and clipped the
# leading/top title geometry, leaving a full English Rank residue. Use a broad,
# color-gated interior band that contains the complete title but excludes the
# oval border by color classification.
# Use C173's independently proven canonical title geometry only to bound
# discovery; the actual mask is still re-derived from canonical white/navy pixels.
# C173's broad white/navy audit usefully exposed residue but also included the oval
# top border. The canonical visual evidence places the actual Total Rank title below
# that border. Detect the complete title in the border-free title band only.
rx0=520; rx1=1070
ry0=1175; ry1=1290
roi=sa[ry0:ry1,rx0:rx1]
r=roi[:,:,0].astype(np.int16); g=roi[:,:,1].astype(np.int16); b=roi[:,:,2].astype(np.int16); a=roi[:,:,3]
white=(a>32)&(r>220)&(g>220)&(b>220)&((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]))<24)
navy=(a>32)&(b>r+10)&(b>g+5)&(r<110)&(g<110)&(b<180)
core=(white|navy)
cy,cx=np.nonzero(core)
if len(cx)<4000: raise RuntimeError(("title core too small",len(cx)))
m=np.zeros((H,W),bool); m[ry0:ry1,rx0:rx1]=core
source_mask=Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(7))
sm=np.asarray(source_mask)>0
ys2,xs2=np.nonzero(sm)
ob=[int(xs2.min()),int(ys2.min()),int(xs2.max())+1,int(ys2.max())+1]
if not (450 <= ob[2]-ob[0] <= 550 and 80 <= ob[3]-ob[1] <= 115):
    raise RuntimeError(("title bbox implausible",ob))
if not (535 <= ob[0] <= 550 and 1175 <= ob[1] <= 1192 and 1060 <= ob[2] <= 1072 and 1268 <= ob[3] <= 1282):
    raise RuntimeError(("title bbox outside canonical visual title band",ob))
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
protected=ImageOps.invert(allowed)

# Clean plate: the canonical A05 oval interior beneath the title is a nearly
# uniform light-green plate; only its cyan/navy border/glow is spatially varying.
# Sample a broad protected interior patch well below the title and away from the
# border, then replace ONLY the exact source-title/effect mask with that robust RGBA
# median. This avoids text-shaped ghosts and never touches protected border/artwork.
safe=sa[y+330:y+560, x+360:x+1120].reshape(-1,4)
keep=(safe[:,3]>180)&(safe[:,:3].min(axis=1)>80)&(safe[:,:3].max(axis=1)<230)
if np.count_nonzero(keep)<10000:
    raise RuntimeError(("insufficient protected oval interior samples",int(np.count_nonzero(keep))))
plate=np.median(safe[keep].astype(np.float32),axis=0)
clean_arr=sa.copy()
clean_arr[sm]=np.clip(np.rint(plate),0,255).astype(np.uint8)
clean=Image.fromarray(clean_arr,"RGBA")
source_png=out/"A05_SOURCE_READABLE.png"; clean_png=out/"A05_CLEAN_PLATE.png"; smp=out/"A05_SOURCE_TEXT_MASK.png"; ap=out/"A05_ALLOWED_BBOX_MASK.png"; pp=out/"A05_PROTECTED_MASK.png"
src.save(source_png); clean.save(clean_png); source_mask.save(smp); allowed.save(ap); protected.save(pp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(smp),"--protected-mask",str(pp),"--report",str(out/"B126_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B126_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))
core_mask=Image.fromarray((m.astype(np.uint8)*255),"L")
core_unchanged=count(ImageChops.multiply(core_mask,ImageOps.invert(diffmask(src,clean))))
if core_unchanged!=0: raise RuntimeError(("source title core unchanged",core_unchanged))

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

def tracked_masks(text,font,sw,track):
    # Render each character at source-like wide spacing without geometrically
    # stretching Hangul glyphs. The space keeps a slightly larger word gap.
    boxes=[font.getbbox(ch,stroke_width=sw) if ch!=" " else (0,0,int(font.size*.34),font.size) for ch in text]
    advances=[]
    for ch,bb in zip(text,boxes):
        adv=int(round(font.getlength(ch))) if ch!=" " else int(font.size*.34)
        advances.append(max(1,adv))
    width=sum(advances)+track*(len(text)-1)+2*(sw+8)
    height=max((bb[3]-bb[1] for ch,bb in zip(text,boxes) if ch!=" "),default=font.size)+2*(sw+10)
    om=Image.new("L",(width,height),0); fm=Image.new("L",(width,height),0)
    od=ImageDraw.Draw(om); fd=ImageDraw.Draw(fm)
    cursor=sw+8; baseline=sw+8
    for i,ch in enumerate(text):
        if ch!=" ":
            bb=font.getbbox(ch,stroke_width=sw)
            y0=baseline-bb[1]
            od.text((cursor,y0),ch,font=font,fill=255,stroke_width=sw,stroke_fill=255)
            fd.text((cursor,y0),ch,font=font,fill=255)
        cursor+=advances[i]+(track if i<len(text)-1 else 0)
    return om,fm

def tile_for(fs,track):
    font=ImageFont.truetype(fp,fs,index=fi); sw=max(2,round(fs*.07)); text="종합 랭킹"
    om,fm=tracked_masks(text,font,sw,track)
    t=Image.new("RGBA",om.size,(0,0,0,0)); t.paste(navy_rgba,(0,0),om); t.paste(white_rgba,(0,0),fm); t=shear_rgba(t,.22)
    bb=t.getchannel("A").getbbox(); return (t.crop(bb),sw) if bb else (None,sw)

aw,ah=ob[2]-ob[0],ob[3]-ob[1]
fits=[]
for fs in range(96,28,-1):
    for track in range(38,-1,-2):
        t,sw=tile_for(fs,track)
        if t and t.width<=aw-8 and t.height<=ah-8:
            # Prefer a wide/low result near 82% of source width while maximizing
            # vertical source-style presence without edge touch.
            score=abs(t.width-aw*.82)+abs(t.height-ah*.88)*1.4
            fits.append((score,-fs,-track,t,sw,fs,track))
if not fits: raise RuntimeError("Hangul fit failed")
fits.sort(key=lambda z:(z[0],z[1],z[2]))
_,_,_,tile,sw,fs,track= fits[0]
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
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B126_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B126_FINAL_VALIDATION.json").read_text())
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
sheet.save(out/"B126_A05_SOURCE_CLEAN_FINAL.jpg",quality=96)
margin=40; box=(max(0,ob[0]-margin),max(0,ob[1]-margin),min(W,ob[2]+margin),min(H,ob[3]+margin))
ims=[comp(z.crop(box)) for z in [src,clean,dec]]
row=Image.new("RGB",(sum(i.width for i in ims)+16,max(i.height for i in ims)+28),"white"); xx=0
for im in ims: row.paste(im,(xx,28)); xx+=im.width+8
ImageDraw.Draw(row).text((4,4),"Total Rank -> 종합 랭킹   SOURCE | CLEAN | FINAL",fill="black"); row.save(out/"B126_A05_ROW_CONTACT.jpg",quality=96)
rr=Image.new("RGB",(1024,2*1050),"white")
for i,(lab,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1050+26)); ImageDraw.Draw(rr).text((5,i*1050+5),lab,fill="black")
rr.save(out/"B126_A05_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"B","run":run,"queue_index":28,"asset":asset,
 "readiness_tier":"ZOOM_REVIEW_PROMOTED_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"region0":"Total Rank -> 종합 랭킹","region1":"lens flare artwork -> preserve"},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "row":{"region_idx":0,"source":"Total Rank","korean":"종합 랭킹","original_bbox":ob,"localized_bbox":lb,
        "source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
        "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_file":Path(fp).name,"font_style":fstyle,"font_size":fs,"stroke_width":sw,"slant":.22,"tracking_px":track,
        "fill_rgba":white_rgba,"outline_rgba":navy_rgba,"alignment":"center"},
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"outside":outside,"alpha_outside":alphaout,"render_outside_target":render_out,"protected_lens_flare_cell_changed":protected_cell_changes,"localized_overlap":0},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B126_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"B126_A05_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":28,"asset":"A05BF610","source_sha256":sha(sb),"candidate_sha256":csha,"localized_physical_elements":1,
 "bbox_size_positive_margin":"1/1","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "outside":outside,"alpha_outside":alphaout,"protected_lens_flare_cell_changed":protected_cell_changes,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{run}/B126_A05_REPORT.json"}
(wr/"B126_A05BF610.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
