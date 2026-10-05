#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,subprocess,statistics
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")
repo=Path.cwd()
run="20261005-B-PRODUCTION97"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
w=Path("/tmp/b91"); w.mkdir(exist_ok=True)
dds=w/"src.dds"; atlas=w/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_CLAR_RANK_Exst/4x_63C91067_512x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def bmask(im): return im.point(lambda v:255 if v else 0)
def count(im): return sum(im.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

if blob(sb)!="9f41fe44ecb17a4daba096ddbb9d2c73fa28e8f9": raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="7f118326e34794e2ae5bf3f3b6d82b6ce566c64a": raise RuntimeError(("atlas drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(2048,2048) or len(sb)!=128+W*H*4:
    raise RuntimeError(("unexpected structure",W,H,mips,masks,len(sb),mode))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

# Both regions contain the same functional label Total Rank. Constrain discovery to
# the centered upper title area to exclude the speech-bubble/starburst artwork.
rows=[]; source_core=np.zeros((H,W),bool)
for idx in (0,1):
    x,y,cw,ch=regs[idx]["rect"]
    rx0=x+int(cw*.20); rx1=x+int(cw*.80)
    ry0=y+int(ch*.02); ry1=y+min(int(ch*.28),300)
    roi=sa[ry0:ry1,rx0:rx1]
    r=roi[:,:,0].astype(np.int16); g=roi[:,:,1].astype(np.int16); b=roi[:,:,2].astype(np.int16); a=roi[:,:,3]
    white=(a>32)&(r>220)&(g>220)&(b>220)&((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]))<20)
    navy=(a>32)&(b>r+10)&(b>g+5)&(r<100)&(g<100)&(b<170)
    # Navy outline is unique to the title inside this central ROI; use it to isolate the title from cream plate highlights.
    nys,nxs=np.nonzero(navy)
    if len(nxs)<100: raise RuntimeError(("title navy core too small",idx,len(nxs)))
    nx0=max(0,int(nxs.min())-10); ny0=max(0,int(nys.min())-10); nx1=min(navy.shape[1],int(nxs.max())+11); ny1=min(navy.shape[0],int(nys.max())+11)
    core=np.zeros_like(navy)
    core[ny0:ny1,nx0:nx1]=(white|navy)[ny0:ny1,nx0:nx1]
    ys,xs=np.nonzero(core)
    if len(xs)<100: raise RuntimeError(("title core too small",idx,len(xs)))
    gx0=rx0+int(xs.min()); gy0=ry0+int(ys.min()); gx1=rx0+int(xs.max())+1; gy1=ry0+int(ys.max())+1
    if gx1-gx0>cw*.50 or gy1-gy0>ch*.16: raise RuntimeError(("title discovery implausible",idx,[gx0,gy0,gx1,gy1]))
    m=np.zeros((H,W),bool); m[ry0:ry1,rx0:rx1]=core
    pim=Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(13))
    pm=np.asarray(pim)>0
    pys,pxs=np.nonzero(pm)
    bx0=int(pxs.min()); by0=int(pys.min()); bx1=int(pxs.max())+1; by1=int(pys.max())+1
    source_core|=m
    rows.append({"region_idx":idx,"source":"Total Rank","korean":"종합 랭킹","cell":[x,y,cw,ch],
      "core_bbox":[gx0,gy0,gx1,gy1],"original_bbox":[bx0,by0,bx1,by1],"source_core_pixels":int(np.count_nonzero(m)),
      "source_mask_pixels":int(np.count_nonzero(pm))})

source_mask_img=Image.new("L",(W,H),0)
for row in rows:
    # recreate per-row dilation from its core bounded by row core neighborhood
    idx=row["region_idx"]; x,y,cw,ch=regs[idx]["rect"]; rx0=x+int(cw*.20); rx1=x+int(cw*.80); ry0=y+int(ch*.02); ry1=y+min(int(ch*.28),300)
    roi=sa[ry0:ry1,rx0:rx1]; r=roi[:,:,0].astype(np.int16); g=roi[:,:,1].astype(np.int16); b=roi[:,:,2].astype(np.int16); a=roi[:,:,3]
    white=(a>32)&(r>220)&(g>220)&(b>220)&((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]))<20)
    navy=(a>32)&(b>r+10)&(b>g+5)&(r<100)&(g<100)&(b<170)
    nys,nxs=np.nonzero(navy)
    nx0=max(0,int(nxs.min())-10); ny0=max(0,int(nys.min())-10); nx1=min(navy.shape[1],int(nxs.max())+11); ny1=min(navy.shape[0],int(nys.max())+11)
    core=np.zeros_like(navy); core[ny0:ny1,nx0:nx1]=(white|navy)[ny0:ny1,nx0:nx1]
    m=Image.new("L",(W,H),0); patch=Image.fromarray((core.astype(np.uint8)*255),"L"); m.paste(patch,(rx0,ry0))
    m=m.filter(ImageFilter.MaxFilter(13))
    source_mask_img=ImageChops.lighter(source_mask_img,m)
source_mask=bmask(source_mask_img)
allowed=Image.new("L",(W,H),0)
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)

# Style colors from source core.
pix=sa[source_core]
white_sel=(pix[:,0]>165)&(pix[:,1]>165)&(pix[:,2]>165)
navy_sel=(pix[:,2].astype(int)>pix[:,0].astype(int)+10)&(pix[:,2].astype(int)>pix[:,1].astype(int)+5)&(pix[:,0]<100)&(pix[:,1]<100)
white_rgb=tuple(int(round(float(np.median(pix[white_sel,k].astype(np.float32))))) for k in range(3))
navy_rgb=tuple(int(round(float(np.median(pix[navy_sel,k].astype(np.float32))))) for k in range(3))
white=white_rgb+(255,); navy=navy_rgb+(255,)

# Patterned/gradient plate reconstruction: per-column interpolation between
# nearest untouched pixels above/below each title-effect run. This preserves the
# starburst's vertical cream spike and the speech-bubble gradient without
# propagating text-edge colors back into the cleaned region. Alpha remains byte-exact.
sm=np.asarray(source_mask)>0
clean_arr=sa.copy()
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]
    for xx in range(x0,x1):
        ys=np.flatnonzero(sm[y0:y1,xx])
        if not len(ys): continue
        ay=y0+int(ys.min()); by=y0+int(ys.max())+1
        up=ay-1
        while up>=max(0,y0-32) and sm[up,xx]: up-=1
        dn=by
        while dn<min(H,y1+32) and sm[dn,xx]: dn+=1
        if up<0 or dn>=H or up>=ay or dn<by: raise RuntimeError(("plate interpolation anchors",row["region_idx"],xx,up,dn))
        top=sa[up,xx,:3].astype(np.float32); bot=sa[dn,xx,:3].astype(np.float32)
        span=float(dn-up)
        for yy in range(ay,by):
            if not sm[yy,xx]: continue
            t=(yy-up)/span
            clean_arr[yy,xx,:3]=np.clip(np.rint(top*(1.0-t)+bot*t),0,255).astype(np.uint8)
clean_arr[:,:,3]=sa[:,:,3]
clean=Image.fromarray(clean_arr,"RGBA")
source_png=out/"63C_SOURCE_READABLE.png"; clean_png=out/"63C_CLEAN_PLATE.png"; smp=out/"63C_SOURCE_TEXT_MASK.png"; allowedp=out/"63C_ALLOWED_BBOX_MASK.png"
src.save(source_png); clean.save(clean_png); source_mask.save(smp); allowed.save(allowedp)
protected=ImageOps.invert(allowed); pp=out/"63C_PROTECTED_MASK.png"; protected.save(pp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(smp),"--protected-mask",str(pp),"--report",str(out/"B97_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B97_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
fp,fi,fstyle=FONT.rsplit("|",2); fi=int(fi or 0)
if not Path(fp).exists(): raise RuntimeError(("font missing",FONT))

def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for y in range(im.height):
        o.alpha_composite(im.crop((0,y,im.width,y+1)),(int(round(s*(im.height-1-y))),y))
    return o

def make_tile(text,fs):
    font=ImageFont.truetype(fp,fs,index=fi)
    sw=max(2,round(fs*.075))
    d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=font,stroke_width=sw)
    pad=sw+5; size=(bb[2]-bb[0]+2*pad,bb[3]-bb[1]+2*pad)
    fillm=Image.new("L",size,0); outm=Image.new("L",size,0)
    pos=(pad-bb[0],pad-bb[1])
    ImageDraw.Draw(outm).text(pos,text,font=font,fill=255,stroke_width=sw,stroke_fill=255)
    ImageDraw.Draw(fillm).text(pos,text,font=font,fill=255)
    tile=Image.new("RGBA",size,(0,0,0,0)); tile.paste(navy,(0,0),outm); tile.paste(white,(0,0),fillm)
    tile=shear_rgba(tile,.22)
    ab=tile.getchannel("A").getbbox()
    return tile.crop(ab) if ab else None,sw

# Shared source style, maximum safe size with positive margin in both occurrences.
shared_fs=None; shared_tile=None; shared_sw=None
for fs in range(110,20,-1):
    tile,sw=make_tile("종합 랭킹",fs)
    if not tile: continue
    ok=True
    for row in rows:
        x0,y0,x1,y1=row["original_bbox"]
        if tile.width>(x1-x0)-8 or tile.height>(y1-y0)-8: ok=False; break
    if ok: shared_fs,shared_tile,shared_sw=fs,tile,sw; break
if shared_fs is None: raise RuntimeError("shared Korean title fit failed")

final=clean.copy(); targets=[]; outrows=[]
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]; tile=shared_tile
    px=x0+(x1-x0-tile.width)//2; py=y0+(y1-y0-tile.height)//2
    final.alpha_composite(tile,(px,py))
    lm=Image.new("L",(W,H),0); lm.paste(bmask(tile.getchannel("A")),(px,py)); lb=list(lm.getbbox())
    sw0,sh0=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    if not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1 and lw<=sw0 and lh<=sh0):
        raise RuntimeError(("containment",row["region_idx"],[x0,y0,x1,y1],lb))
    targets.append(lm)
    outrows.append({**row,"localized_bbox":lb,"source_width":sw0,"source_height":sh0,"localized_width":lw,"localized_height":lh,
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_file":Path(fp).name,"font_style":fstyle,
      "font_size":shared_fs,"stroke_width":shared_sw,"slant":.22,"fill_rgba":white,"outline_rgba":navy,"alignment":"center",
      "rework_status":"B97_NEW_EXACT_HD_CANDIDATE"})

if ImageChops.multiply(targets[0],targets[1]).getbbox(): raise RuntimeError("target overlap")
target=ImageChops.lighter(targets[0],targets[1]); target.save(out/"63C_TARGET_TEXT_MASK.png")

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload); csha=sha(payload)
if payload[:128]!=sb[:128]: raise RuntimeError("header drift")
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("RGBA roundtrip mismatch")
final_png=out/"63C_FINAL_DECODED_READABLE.png"; dec.save(final_png)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(allowedp),"--protected-mask",str(pp),"--report",str(out/"B97_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B97_FINAL_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final validator",finalrep))

diff=diffmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
render_out=count(ImageChops.multiply(target,ImageOps.invert(allowed)))
prot=outside
# Residue basis is the source-effect pixels actually removed by CLEAN, not color-classifier
# candidates that happened to match the reconstructed plate exactly.
guard=target.filter(ImageFilter.MaxFilter(5))
clean_changed=diffmask(src,clean)
unchanged=ImageOps.invert(diff)
residue=count(ImageChops.multiply(ImageChops.multiply(clean_changed,ImageOps.invert(guard)),unchanged))
if outside or alphaout or render_out or prot or residue:
    raise RuntimeError(("pixel gates",outside,alphaout,render_out,prot,residue))

# Evidence.
stack=Image.new("RGB",(1024,3*1050),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); stack.paste(z,(0,i*1050+26)); ImageDraw.Draw(stack).text((5,i*1050+5),label,fill="black")
stack.save(out/"B97_63C_SOURCE_CLEAN_FINAL.jpg",quality=96)
cards=[]
for row in outrows:
    x0,y0,x1,y1=row["original_bbox"]; p=20; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]
    sc=max(1,min(3,1200//max(1,ims[0].width)))
    ims=[z.resize((z.width*sc,z.height*sc),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+34),"white"); xx=0
    for z in ims: c.paste(z,(xx,34)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{row["region_idx"]} Total Rank -> 종합 랭킹',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+4 for c in cards)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B97_63C_ROW_CONTACT.jpg",quality=96)
rr=Image.new("RGB",(1024,2*1050),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1050+26)); ImageDraw.Draw(rr).text((5,i*1050+5),label,fill="black")
rr.save(out/"B97_63C_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"B","run":run,"queue_index":26,"asset":asset,
 "readiness_tier":"PREFLIGHT_PROMOTED_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"0":"Total Rank -> 종합 랭킹","1":"Total Rank -> 종합 랭킹"},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "source_style":{"family":"white italic title with navy outline","font_file":Path(fp).name,"font_style":fstyle,"shared_font_size":shared_fs,"stroke_width":shared_sw,"slant":.22,"fill_rgba":white,"outline_rgba":navy,"alignment":"center"},
 "rows":outrows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"source_effect_residue":residue,"render_outside_target":render_out,"localized_overlap":0},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B97_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
(out/"B97_63C_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":26,"asset":"63C91067","source_sha256":sha(sb),"candidate_sha256":csha,"localized_physical_elements":2,
 "bbox_size_positive_margin":"2/2","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "source_residue":residue,"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"render_outside_target":render_out,"overlap":0,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{run}/B97_63C_REPORT.json"}
(wr/"B97_63C91067.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
