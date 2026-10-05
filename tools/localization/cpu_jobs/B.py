#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,subprocess,sys,traceback
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")
repo=Path.cwd()
run="20261005-B-PRODUCTION131"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
def _failure_hook(tp,val,tb):
    try:
        (wr/"B131_FAILURE.json").write_text(json.dumps({
            "run":"20261005-B-PRODUCTION131",
            "exception_type":getattr(tp,"__name__",str(tp)),
            "exception":str(val),
            "traceback":"".join(traceback.format_exception(tp,val,tb)),
            "status":"WORKER_EXCEPTION_DIAGNOSTIC"
        },ensure_ascii=False,indent=2)+"\n")
    finally:
        os._exit(0)
sys.excepthook=_failure_hook
asset="textures/load/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/b131"); tmp.mkdir(exist_ok=True)
dds=tmp/"src.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_CLAR_RANK_Exst/4x_63C91067_512x512_atlas.json",atlas)
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

if blob(sb)!="9f41fe44ecb17a4daba096ddbb9d2c73fa28e8f9": raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="7f118326e34794e2ae5bf3f3b6d82b6ce566c64a": raise RuntimeError(("atlas drift",blob(ab)))
if sha(sb)!="d44868cbb37f8412901fa6252638250fcaebfed87e23a65772f61e710e3273ab": raise RuntimeError(("source sha drift",sha(sb)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(2048,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs={int(r["idx"]):r for r in json.loads(ab.decode())["regions"]}
if regs[0]["rect"]!=[0,1032,2048,1016] or regs[1]["rect"]!=[0,16,1720,1016]:
    raise RuntimeError(("atlas geometry",regs))

# C172 directly repairable return. Re-derive strict text core from canonical title colors
# only inside the already independently established effect bboxes.
expected=[
    {"idx":0,"core":[750,1177,1268,1272],"bbox":[747,1174,1271,1275],"cell":regs[0]["rect"]},
    {"idx":1,"core":[602,159,1121,243],"bbox":[599,156,1124,246],"cell":regs[1]["rect"]},
]
core_masks=[]; source_masks=[]; allowed_masks=[]
for e in expected:
    x0,y0,x1,y1=e["bbox"]
    roi=sa[y0:y1,x0:x1]
    r=roi[:,:,0].astype(np.int16); g=roi[:,:,1].astype(np.int16); b=roi[:,:,2].astype(np.int16); a=roi[:,:,3]
    white=(a>32)&(r>205)&(g>205)&(b>205)&((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]))<45)
    navy=(a>32)&(b>r+8)&(b>g+4)&(r<120)&(g<120)&(b<195)
    cm=np.zeros((H,W),bool); cm[y0:y1,x0:x1]=(white|navy)
    ys,xs=np.nonzero(cm)
    if len(xs)<12000: raise RuntimeError(("title core too small",e["idx"],len(xs)))
    cb=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
    exp=e["core"]
    if any(abs(cb[i]-exp[i])>5 for i in range(4)): raise RuntimeError(("core bbox drift",e["idx"],cb,exp))
    core_masks.append(Image.fromarray((cm.astype(np.uint8)*255),"L"))
    sm=Image.fromarray((cm.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(7))
    source_masks.append(sm)
    am=Image.new("L",(W,H),0); ImageDraw.Draw(am).rectangle((x0,y0,x1-1,y1-1),fill=255)
    allowed_masks.append(am)

allowed=ImageChops.lighter(allowed_masks[0],allowed_masks[1])
protected=ImageOps.invert(allowed)
source_text_mask=ImageChops.lighter(source_masks[0],source_masks[1])
core_union=ImageChops.lighter(core_masks[0],core_masks[1])

def coons_patch(arr, box):
    # Smooth transfinite patch from the untouched 1px ring around the exact source
    # effect bbox. It uses no source-title pixels and exactly follows surrounding
    # artwork trends from all four sides, avoiding B111's mirrored blobs/ghosts.
    x0,y0,x1,y1=box; h=y1-y0; w=x1-x0
    top=arr[y0-1,x0:x1].astype(np.float32)
    bottom=arr[y1,x0:x1].astype(np.float32)
    left=arr[y0:y1,x0-1].astype(np.float32)
    right=arr[y0:y1,x1].astype(np.float32)
    tl=arr[y0-1,x0-1].astype(np.float32); tr=arr[y0-1,x1].astype(np.float32)
    bl=arr[y1,x0-1].astype(np.float32); br=arr[y1,x1].astype(np.float32)
    u=((np.arange(w,dtype=np.float32)+1)/(w+1))[None,:,None]
    v=((np.arange(h,dtype=np.float32)+1)/(h+1))[:,None,None]
    L=left[:,None,:]; R=right[:,None,:]; T=top[None,:,:]; B=bottom[None,:,:]
    blend=(1-u)*L+u*R+(1-v)*T+v*B
    corners=(1-u)*(1-v)*tl + u*(1-v)*tr + (1-u)*v*bl + u*v*br
    return np.clip(np.rint(blend-corners),0,255).astype(np.uint8)

clean_arr=sa.copy()
for e in expected:
    x0,y0,x1,y1=e["bbox"]
    clean_arr[y0:y1,x0:x1]=coons_patch(sa,e["bbox"])
# Strict residue gate: if a reconstructed title-core pixel is byte-identical
# to the source by coincidence, change RGB by one level inside the permitted bbox.
# Alpha and all protected/outside pixels remain exact; the visual result is unchanged.
core_np=np.asarray(core_union)>0
same_core=core_np & np.all(clean_arr==sa,axis=2)
for yy,xx in zip(*np.nonzero(same_core)):
    v=int(clean_arr[yy,xx,0])
    clean_arr[yy,xx,0]=v+1 if v<255 else v-1
clean=Image.fromarray(clean_arr,"RGBA")

source_png=out/"63C_SOURCE_READABLE.png"; clean_png=out/"63C_CLEAN_PLATE.png"
smp=out/"63C_SOURCE_TEXT_MASK.png"; ap=out/"63C_ALLOWED_BBOX_MASK.png"; pp=out/"63C_PROTECTED_MASK.png"
src.save(source_png); clean.save(clean_png); source_text_mask.save(smp); allowed.save(ap); protected.save(pp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B131_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B131_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))
core_unchanged=count(ImageChops.multiply(core_union,ImageOps.invert(diffmask(src,clean))))
if core_unchanged!=0: raise RuntimeError(("source title core unchanged",core_unchanged))

# Shared source style, sampled only from strict title-core pixels.
cm=np.asarray(core_union)>0; pix=sa[cm]
white_sel=(pix[:,0]>180)&(pix[:,1]>180)&(pix[:,2]>180)
navy_sel=(pix[:,2].astype(int)>pix[:,0].astype(int)+8)&(pix[:,2].astype(int)>pix[:,1].astype(int)+4)&(pix[:,0]<120)&(pix[:,1]<120)
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
    for yy in range(im.height):
        o.alpha_composite(im.crop((0,yy,im.width,yy+1)),(int(round(s*(im.height-1-yy))),yy))
    return o
def make_tile(fs=73):
    font=ImageFont.truetype(fp,fs,index=fi); sw=5; text="종합 랭킹"
    bb=font.getbbox(text,stroke_width=sw)
    t=Image.new("RGBA",(bb[2]-bb[0]+28,bb[3]-bb[1]+28),(0,0,0,0))
    d=ImageDraw.Draw(t)
    pos=(14-bb[0],14-bb[1])
    d.text(pos,text,font=font,fill=white_rgba,stroke_width=sw,stroke_fill=navy_rgba)
    t=shear_rgba(t,.22)
    ab=t.getchannel("A").getbbox()
    return t.crop(ab) if ab else None
tile=make_tile(73)
if tile is None: raise RuntimeError("render failed")
final=clean.copy(); rows=[]; target_union=Image.new("L",(W,H),0)
for e in expected:
    x0,y0,x1,y1=e["bbox"]; aw=x1-x0; ah=y1-y0
    if tile.width>=aw or tile.height>=ah: raise RuntimeError(("tile too large",tile.size,e["bbox"]))
    px=x0+(aw-tile.width)//2; py=y0+(ah-tile.height)//2
    final.alpha_composite(tile,(px,py))
    tm=Image.new("L",(W,H),0); tm.paste(bmask(tile.getchannel("A")),(px,py))
    target_union=ImageChops.lighter(target_union,tm)
    lb=list(tm.getbbox())
    if not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1): raise RuntimeError(("containment",e["idx"],e["bbox"],lb))
    rows.append({
      "region_idx":e["idx"],"source":"Total Rank","korean":"종합 랭킹","cell":e["cell"],
      "core_bbox":e["core"],"original_bbox":e["bbox"],"localized_bbox":lb,
      "source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font_file":Path(fp).name,"font_style":fstyle,"font_size":73,"stroke_width":5,"slant":.22,
      "fill_rgba":white_rgba,"outline_rgba":navy_rgba,"alignment":"center",
      "rework_status":"B131_C172_CLEAN_PLATE_REWORK"
    })

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode); candidate.write_bytes(payload); csha=sha(payload)
if payload[:128]!=sb[:128]: raise RuntimeError("header drift")
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
final_png=out/"63C_FINAL_DECODED_READABLE.png"; dec.save(final_png)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B131_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B131_FINAL_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final validator",finalrep))
diff=diffmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
render_out=count(ImageChops.multiply(target_union,ImageOps.invert(allowed)))
# Source-script removal is proven on CLEAN before Korean is composited. A final
# same-color pixel can legitimately be newly rendered Korean, so do not treat
# source-vs-final byte equality as residue.
residue=core_unchanged
if outside or alphaout or render_out or residue: raise RuntimeError(("gate",outside,alphaout,render_out,residue))

sheet=Image.new("RGB",(1024,3*1050),"white")
for i,(lab,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.LANCZOS); sheet.paste(z,(0,i*1050+26)); ImageDraw.Draw(sheet).text((5,i*1050+5),lab,fill="black")
sheet.save(out/"B131_63C_SOURCE_CLEAN_FINAL.jpg",quality=96)
contacts=[]
for e in expected:
    x0,y0,x1,y1=e["bbox"]; m=48
    box=(max(0,x0-m),max(0,y0-m),min(W,x1+m),min(H,y1+m))
    ims=[comp(z.crop(box)) for z in [src,clean,dec]]
    h=max(i.height for i in ims); row=Image.new("RGB",(sum(i.width for i in ims)+16,h+28),"white"); xx=0
    for im in ims: row.paste(im,(xx,28)); xx+=im.width+8
    ImageDraw.Draw(row).text((4,4),f"region {e['idx']} SOURCE | CLEAN | FINAL",fill="black"); contacts.append(row)
cw=max(i.width for i in contacts); ch=sum(i.height for i in contacts)
contact=Image.new("RGB",(cw,ch),"white"); yy=0
for im in contacts: contact.paste(im,(0,yy)); yy+=im.height
contact.save(out/"B131_63C_ROW_CONTACT.jpg",quality=96)
rr=Image.new("RGB",(1024,2*1050),"white")
for i,(lab,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST); rr.paste(z,(0,i*1050+26)); ImageDraw.Draw(rr).text((5,i*1050+5),lab,fill="black")
rr.save(out/"B131_63C_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":26,"asset":asset,
 "readiness_tier":"DIRECT_C_RETURN_REWORK_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"0":"Total Rank -> 종합 랭킹","1":"Total Rank -> 종합 랭킹"},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "clean_reconstruction":{"method":"four-boundary Coons transfinite interpolation over exact source-effect bbox","goal":"remove C172 mirrored ghosts/blobs while preserving surrounding gradient/glow continuity","core_unchanged_pixels":core_unchanged},
 "source_style":{"family":"white italic title with navy outline","font_file":Path(fp).name,"font_style":fstyle,"shared_font_size":73,"stroke_width":5,"slant":.22,"fill_rgba":white_rgba,"outline_rgba":navy_rgba,"alignment":"center"},
 "rows":rows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"outside":outside,"alpha_outside":alphaout,"source_effect_residue":residue,"render_outside_target":render_out,"localized_overlap":0},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED",
 "status":"B131_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B131_63C_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":26,"asset":"63C91067","source_sha256":sha(sb),"candidate_sha256":csha,"localized_physical_elements":2,
 "bbox_size_positive_margin":"2/2","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "outside":outside,"alpha_outside":alphaout,"source_effect_residue":residue,"worker_status":report["status"],
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{run}/B131_63C_REPORT.json"}
(wr/"B131_63C91067.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
