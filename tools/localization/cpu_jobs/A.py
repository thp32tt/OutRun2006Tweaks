#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request, statistics
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-PRODUCTION22"
out=repo/"localization/graphics/role_A"/run
wr=repo/"localization/graphics/worker_results"
out.mkdir(parents=True,exist_ok=True); wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
SRC_PATH="Release/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
ATLAS_PATH="Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_0030CF0D_512x256_atlas.json"
SRC_BLOB="a17e3caff8610356d70ddc52e89a7533aa99b98c"
ATLAS_BLOB="05aef390b13b39d3c9cd74d5c50f8291273fb0d9"

tmp=Path("/tmp/outrun_A_prod22"); tmp.mkdir(parents=True,exist_ok=True)
srcp=tmp/"30CF0D_HD.dds"; atp=tmp/"30CF0D_atlas.json"
urllib.request.urlretrieve(BASE+"/"+SRC_PATH,srcp)
urllib.request.urlretrieve(BASE+"/"+ATLAS_PATH,atp)

def blob_sha1(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def gray(im):
    bg=Image.new("RGBA",im.size,(64,64,64,255)); bg.alpha_composite(im); return bg.convert("RGB")

sb=srcp.read_bytes(); ab=atp.read_bytes()
assert blob_sha1(sb)==SRC_BLOB,(blob_sha1(sb),SRC_BLOB)
assert blob_sha1(ab)==ATLAS_BLOB,(blob_sha1(ab),ATLAS_BLOB)
assert sb[:4]==b"DDS "
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
assert (W,H,pitch,mips)==(2048,1024,8192,1),(W,H,pitch,mips)
assert depth in (0,1)
assert len(sb)==128+W*H*4
masks=(pf[4],pf[5],pf[6])
if masks==(0xff,0xff00,0xff0000): RAWMODE="RGBA"
elif masks==(0xff0000,0xff00,0xff): RAWMODE="BGRA"
else: raise RuntimeError(("unsupported RGB masks",masks))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

aj=json.loads(atp.read_text())
regions={int(r["idx"]):r for r in aj["regions"]}
targets=[
  {"key":"manual_large","idx":2,"source":"MANUAL","ko":"수동"},
  {"key":"automatic_large","idx":3,"source":"AUTOMATIC","ko":"자동"},
  {"key":"manual_small","idx":4,"source":"MANUAL","ko":"수동"},
  {"key":"automatic_small","idx":5,"source":"AUTOMATIC","ko":"자동"},
  {"key":"select_transmission","idx":6,"source":"SELECT TRANSMISSION","ko":"변속 방식 선택"},
  {"key":"transmission_small","idx":7,"source":"TRANSMISSION","ko":"변속 방식"},
]
for t in targets:
    t["cell"]=regions[t["idx"]]["rect"]

# Derive exact source effect pixels from each dedicated atlas cell by comparing against
# the row-wise edge background. This retains horizontal bar/gradient plate colors.
src_arr=np.array(src,dtype=np.uint8)
source_text_mask=Image.new("L",(W,H),0)
clean=src.copy()
allowed=Image.new("L",(W,H),0)
rows=[]
style_samples=[]

for t in targets:
    x,y,cw,ch=t["cell"]
    cell=src_arr[y:y+ch,x:x+cw,:]
    edge=max(4,int(cw*0.06))
    edges=np.concatenate([cell[:,:edge,:],cell[:,-edge:,:]],axis=1)
    bg=np.median(edges.astype(np.int16),axis=1).astype(np.uint8)  # ch x 4
    delta=np.abs(cell.astype(np.int16)-bg[:,None,:].astype(np.int16))
    rgb_delta=delta[:,:,:3].max(axis=2)
    a_delta=delta[:,:,3]
    # Source is uncompressed RGBA/BGRA. Low thresholds intentionally retain AA/effect fringe.
    mm=((rgb_delta>=3) | (a_delta>=2))
    # Ignore only 1-pixel outer cell boundary to avoid atlas separator pickup.
    mm[0,:]=False; mm[-1,:]=False; mm[:,0]=False; mm[:,-1]=False
    # Keep visible/effect deviations; reject huge plate-like masks as segmentation failures.
    ys,xs=np.where(mm)
    if len(xs)<20:
        raise RuntimeError(("too few source pixels",t["key"],len(xs)))
    bx=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
    area=(bx[2]-bx[0])*(bx[3]-bx[1])
    if len(xs)>area*0.90:
        raise RuntimeError(("mask looks plate-like",t["key"],len(xs),bx))
    ob=[x+bx[0],y+bx[1],x+bx[2],y+bx[3]]
    # Paste exact mask.
    mcell=Image.fromarray((mm.astype(np.uint8)*255),"L")
    source_text_mask.paste(mcell,(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    # Clean by restoring row-wise edge background on exact source-effect pixels.
    cclean=cell.copy()
    cclean[mm]=np.broadcast_to(bg[:,None,:],cell.shape)[mm]
    clean.paste(Image.fromarray(cclean,"RGBA"),(x,y))
    # Style samples from text/effect pixels.
    pix=cell[mm]
    lum=pix[:,:3].mean(axis=1)
    bright=pix[lum>=np.quantile(lum,0.70)]
    dark=pix[lum<=np.quantile(lum,0.30)]
    fill=tuple(int(v) for v in np.median(bright,axis=0))
    stroke=tuple(int(v) for v in np.median(dark,axis=0))
    style_samples.append((t["key"],fill,stroke))
    rows.append({**t,"original_bbox":ob,"source_mask_pixels":int(mm.sum()),
                 "source_fill_median":fill,"source_dark_median":stroke})

# Protected visible region = all source-visible pixels outside target source bboxes.
src_visible=src.getchannel("A").point(lambda v:255 if v else 0)
protected=ImageChops.multiply(src_visible,ImageOps.invert(allowed))

# Ensure cleaning changed every exact source-effect pixel and nothing outside source bboxes.
clean_diff=dmask(src,clean)
mask_unchanged=count(ImageChops.multiply(source_text_mask,ImageOps.invert(clean_diff)))
clean_outside=count(ImageChops.multiply(clean_diff,ImageOps.invert(allowed)))
if mask_unchanged!=0 or clean_outside!=0:
    raise RuntimeError(("clean gate",mask_unchanged,clean_outside))

def resolve_font():
    for pat in ("Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"):
        try:
            spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except Exception: spec=""
        if "|" in spec:
            fp,idx=spec.rsplit("|",1)
            try: idx=int(idx or "0")
            except: idx=0
            if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
                return fp,idx,pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    return resolve_font()

FONT,FONT_INDEX,FONT_PATTERN=resolve_font()

def median_rgba(a):
    return tuple(int(v) for v in np.median(np.asarray(a,dtype=np.uint8),axis=0))

def render_text(text,ob,fill,stroke,small=False):
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    # Source family is heavy white/silver with a narrow dark outline and slight right slant.
    stroke_w=max(1,min(5,int(round(ah*0.045))))
    slant=0.08 if not small else 0.04
    for fs in range(max(20,int(ah*1.05)),12,-1):
        font=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        d=ImageDraw.Draw(Image.new("L",(4,4),0))
        bb=d.textbbox((0,0),text,font=font,stroke_width=stroke_w)
        pad=stroke_w+8
        base=Image.new("RGBA",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),(0,0,0,0))
        bd=ImageDraw.Draw(base)
        pos=(pad-bb[0],pad-bb[1])
        bd.text(pos,text,font=font,fill=fill,stroke_width=stroke_w,stroke_fill=stroke)
        ab=base.getchannel("A").getbbox()
        if not ab: continue
        base=base.crop(ab)
        shift=int(round(base.height*slant))
        if shift:
            base=base.transform((base.width+shift,base.height),Image.Transform.AFFINE,
                (1,-slant,shift,0,1,0),resample=Image.Resampling.BICUBIC)
            ab=base.getchannel("A").getbbox()
            if ab: base=base.crop(ab)
        if base.width<=aw-4 and base.height<=ah-4:
            tx=ob[0]+(aw-base.width)//2
            ty=ob[1]+(ah-base.height)//2
            return base,(tx,ty),fs,stroke_w,slant
    raise RuntimeError(("fit failed",text,ob))

final=clean.copy()
target_masks={}
out_rows=[]
for r in rows:
    ob=r["original_bbox"]
    fill=r["source_fill_median"]; stroke=r["source_dark_median"]
    # Force a light fill/dark effect family if medians are inverted by a plate edge.
    if sum(fill[:3]) < sum(stroke[:3]):
        fill,stroke=stroke,fill
    layer,(tx,ty),fs,sw,slant=render_text(r["ko"],ob,fill,stroke,"small" in r["key"])
    final.alpha_composite(layer,(tx,ty))
    lm=Image.new("L",(W,H),0)
    lm.paste(layer.getchannel("A").point(lambda v:255 if v else 0),(tx,ty))
    loc=list(lm.getbbox() or ())
    if len(loc)!=4: raise RuntimeError(("empty render",r["key"]))
    contain=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=(loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
    positive=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    target_masks[r["key"]]=lm
    out_rows.append({
      "key":r["key"],"region_idx":r["idx"],"source":r["source"],"korean":r["ko"],
      "cell":r["cell"],"original_bbox":ob,"localized_bbox":loc,
      "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
      "localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
      "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],
      "delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if size_ok else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL",
      "font_file":FONT,"font_face_index":FONT_INDEX,"font_pattern":FONT_PATTERN,
      "font_size":fs,"stroke_width":sw,"slant":slant
    })

# Pairwise overlap/touch.
keys=list(target_masks)
overlap=0; touch=0
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        overlap+=count(ImageChops.multiply(target_masks[keys[i]],target_masks[keys[j]]))
        touch+=count(ImageChops.multiply(target_masks[keys[i]].filter(ImageFilter.MaxFilter(3)),target_masks[keys[j]]))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw",RAWMODE))
assert candidate.read_bytes()[:128]==sb[:128]
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw",RAWMODE)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
assert ImageChops.difference(decoded,final).getbbox() is None

final_diff=dmask(src,decoded)
outside=count(ImageChops.multiply(final_diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(
    ImageChops.difference(src.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0),
    ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(final_diff,protected))
all_bbox=all(r["containment"]=="PASS" for r in out_rows)
all_size=all(r["size_ceiling"]=="PASS" for r in out_rows)
all_positive=all(r["positive_margin"]=="PASS" for r in out_rows)

# Evidence.
src.save(out/"30CF0D_HD_SOURCE_READABLE.png")
clean.save(out/"30CF0D_HD_CLEAN_PLATE.png")
decoded.save(out/"30CF0D_HD_FINAL_DECODED_READABLE.png")
source_text_mask.save(out/"30CF0D_HD_SOURCE_TEXT_MASK.png")
allowed.save(out/"30CF0D_HD_ALLOWED_SOURCE_BBOX_MASK.png")
protected.save(out/"30CF0D_HD_PROTECTED_MASK.png")

sheet=Image.new("RGB",(1024,1536),(64,64,64))
for i,im in enumerate((src,clean,decoded)):
    sheet.paste(gray(im).resize((1024,512),Image.Resampling.LANCZOS),(0,i*512))
sheet.save(out/"A_PRODUCTION22_SOURCE_CLEAN_FINAL.jpg",quality=96)
gray(decoded_raw).resize((1024,512),Image.Resampling.LANCZOS).save(out/"A_PRODUCTION22_FINAL_RAW.jpg",quality=96)

contacts=[]
for r in out_rows:
    ob=r["original_bbox"]; m=18
    box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
    imgs=[gray(z.crop(box)) for z in (src,clean,decoded)]
    ri=Image.new("RGB",(sum(i.width for i in imgs)+24,max(i.height for i in imgs)+30),(230,230,230))
    xx=0
    for im in imgs:
        ri.paste(im,(xx,30)); xx+=im.width+12
    ImageDraw.Draw(ri).text((4,5),r["key"]+" SOURCE | CLEAN | FINAL",fill=(0,0,0))
    contacts.append(ri)
cw=max(i.width for i in contacts); ch=sum(i.height for i in contacts)+4*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(230,230,230)); yy=0
for im in contacts:
    cs.paste(im,(0,yy)); yy+=im.height+4
cs.save(out/"A_PRODUCTION22_ROW_CONTACT.jpg",quality=96)

status_ok=(mask_unchanged==0 and clean_outside==0 and all_bbox and all_size and all_positive
           and overlap==0 and touch==0 and outside==0 and alpha_out==0 and prot==0)
report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
 "queue_index":137,"asset":asset_rel,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"path":SRC_PATH,
   "git_blob_sha1":SRC_BLOB,"sha256":hashlib.sha256(sb).hexdigest()},
 "source_sha256":hashlib.sha256(sb).hexdigest(),"candidate_sha256":sha256(candidate),
 "candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pixel_raw_mode":RAWMODE,"pitch":pitch,
              "depth":depth,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "translations":[{"source":r["source"],"korean":r["korean"],"region_idx":r["region_idx"]} for r in out_rows],
 "physical_elements":len(out_rows),"rows":out_rows,
 "clean_source_mask_pixels_unchanged":mask_unchanged,"clean_changed_pixels_outside_source_bboxes":clean_outside,
 "localized_overlap_pixels":overlap,"localized_touch_pixels":touch,
 "decoded_changes":{"changed_pixels_total":count(final_diff),"changed_pixels_outside_source_bboxes":outside,
                    "alpha_changed_pixels_outside_source_bboxes":alpha_out,"protected_visible_pixels_changed":prot},
 "bbox_size_positive_margin":f"{sum(1 for r in out_rows if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS')}/{len(out_rows)}",
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "runtime_validation":"UNTESTED",
 "status":"A_PRODUCTION22_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION22_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION22_30CF0D_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"queue_index":137,"asset":"30CF0D","source_sha256":report["source_sha256"],
         "candidate_sha256":report["candidate_sha256"],"physical_elements":len(out_rows),
         "bbox_size_positive_margin":report["bbox_size_positive_margin"],
         "outside":outside,"alpha_outside":alpha_out,"protected":prot,
         "overlap":overlap,"touch":touch,"worker_status":report["status"],
         "report":"localization/graphics/role_A/20261005-A-PRODUCTION22/A_PRODUCTION22_30CF0D_REPORT.json",
         "runtime_validation":"UNTESTED"}
(wr/"A_PRODUCTION22_30CF0D.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
