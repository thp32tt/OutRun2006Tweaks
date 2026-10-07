#!/usr/bin/env python3
import os,json,hashlib,struct,statistics,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261007-B-MANUALQA229-FA7BBB13"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_fruity_cvt_Exst/FA7BBB13_1024x512.dds"
source_path=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset
candidate=repo/"localization/graphics/hd_candidates"/asset
prior_report=repo/"localization/graphics/role_B/20261004-B-RECOVERY01/B_RECOVERY01_FA7BBB13_REPORT.json"
clean_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY01/FA7BBB13_CLEAN_PLATE.png"
source_mask_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY01/FA7BBB13_SOURCE_TEXT_MASK.png"
allowed_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY01/FA7BBB13_ALLOWED_TEXT_REGION_MASK.png"
protected_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY01/FA7BBB13_PROTECTED_MASK.png"
validator=repo/"tools/localization/validate_clean_plate.py"

SOURCE_SHA="61c82072fcc44e9e5f4c6f127d2a29b17abecf5cdb536a5609512246d1ab8d15"
EXPECTED_BEFORE="b5873faa62f4aeb88e8d13712a20092ef95610130d20eb0330e126ad25d2dd68"

def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b)
    m=d.split()[0]
    for z in d.split()[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=source_path.read_bytes(); oldb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb),SOURCE_SHA))
if sha(oldb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha(oldb),EXPECTED_BEFORE))
if sb[:4]!=b"DDS " or oldb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(4096,2048) or len(sb)!=128+W*H*4 or len(oldb)!=len(sb):
    raise RuntimeError(("structure",W,H,mips,masks,len(sb),len(oldb)))
if sb[:128]!=oldb[:128]: raise RuntimeError("candidate header drift")
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw_old=Image.frombytes("RGBA",(W,H),oldb[128:],"raw",mode)
old=raw_old.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

clean=Image.open(clean_path).convert("RGBA")
source_mask=Image.open(source_mask_path).convert("L")
allowed=Image.open(allowed_path).convert("L")
protected=Image.open(protected_path).convert("L")
if clean.size!=(W,H) or source_mask.size!=(W,H) or allowed.size!=(W,H) or protected.size!=(W,H):
    raise RuntimeError("evidence size drift")

prior=json.loads(prior_report.read_text())
rows=[]
for r in prior["rows"]:
    row={k:r[k] for k in ("key","source","korean","original_bbox")}
    if row["key"]=="slipstream_cars":
        row["korean"]="슬립스트림하세요!"
        row["translation_change"]="B229 concise imperative prevents long-string height collapse while preserving the established 슬립스트림 term"
    rows.append(row)
if len(rows)!=17: raise RuntimeError(("row count",len(rows)))

# Current contract's hard permitted region is each exact source glyph/effect BBOX, not the
# historical union-of-old-target-alpha helper mask. Rebuild the permission/protection masks
# from the 17 measured original_bboxes so a new source-faithful slant may occupy previously
# empty pixels inside the same source bbox, while every source-visible pixel outside remains protected.
allowed=Image.new("L",(W,H),0)
ad=ImageDraw.Draw(allowed)
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]
    ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed))

# Revalidate the exact verified clean plate before lettering.
tmp=Path("/tmp/b229"); tmp.mkdir(exist_ok=True)
sp=tmp/"source.png"; cp=tmp/"clean.png"; smp=tmp/"source_mask.png"; pp=tmp/"protected.png"
src.save(sp); clean.save(cp); source_mask.save(smp); protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),
                "--protected-mask",str(pp),"--report",str(out/"B229_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B229_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean",cleanrep))

# Font: native-resolution only.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
fm=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI,FSTYLE=fm.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("verified CJK Bold unavailable",fm))

# Measure the source family palette only inside the exact source text mask.
arr=np.asarray(src); sm=np.asarray(source_mask)>0
pix=arr[sm & (arr[:,:,3]>16)]
if len(pix)<100: raise RuntimeError("source palette sample too small")
rgb=pix[:,:3]
yellow=rgb[(rgb[:,0]>150)&(rgb[:,1]>90)&(rgb[:,0]>rgb[:,2]+45)]
white=rgb[(rgb.min(axis=1)>150)&((rgb.max(axis=1)-rgb.min(axis=1))<70)]
dark=rgb[(rgb.mean(axis=1)<110)]
def med(group,fallback):
    if len(group)<20: return fallback
    return tuple(int(round(statistics.median(group[:,k].tolist()))) for k in range(3))+(255,)
FILL=med(yellow,(238,177,50,255))
INNER=med(white,(245,245,245,255))
OUTER=med(dark,(20,30,72,255))

# Source English is a consistent readable right-italic family. Old Korean is upright;
# current gate requires matching readable-direction slant. Apply explicit row-wise top-right shear.
SLANT=0.16
MIN_XSCALE=0.80
MARGIN=2

def native_tile(text,fs):
    outer=max(5,int(round(fs*0.105)))
    inner=max(2,int(round(fs*0.052)))
    font=ImageFont.truetype(FONT,fs,index=FI)
    scratch=Image.new("RGBA",(8,8),(0,0,0,0)); d=ImageDraw.Draw(scratch)
    bb=d.textbbox((0,0),text,font=font,stroke_width=outer)
    pad=outer+8
    w=max(16,bb[2]-bb[0]+2*pad); h=max(16,bb[3]-bb[1]+2*pad)
    im=Image.new("RGBA",(w,h),(0,0,0,0))
    draw=ImageDraw.Draw(im)
    xy=(pad-bb[0],pad-bb[1])
    draw.text(xy,text,font=font,fill=FILL,stroke_width=outer,stroke_fill=OUTER)
    draw.text(xy,text,font=font,fill=FILL,stroke_width=inner,stroke_fill=INNER)
    ab=im.getchannel("A").getbbox()
    return im.crop(ab) if ab else im

def xscale(im,scale):
    if abs(scale-1.0)<1e-6: return im
    nw=max(1,int(round(im.width*scale)))
    return im.resize((nw,im.height),Image.Resampling.LANCZOS)

def shear_right(im):
    # Shift the top farther right than the bottom in readable orientation.
    a=np.array(im)
    h,w=a.shape[:2]
    maxshift=int(round(SLANT*(h-1)))
    outa=np.zeros((h,w+maxshift,4),dtype=np.uint8)
    for y in range(h):
        shift=int(round(SLANT*(h-1-y)))
        outa[y,shift:shift+w]=a[y]
    z=Image.fromarray(outa,"RGBA")
    bb=z.getchannel("A").getbbox()
    return z.crop(bb) if bb else z

def fit(row):
    x0,y0,x1,y1=row["original_bbox"]; aw=x1-x0; ah=y1-y0
    oldrow=next(x for x in prior["rows"] if x["key"]==row["key"])
    prior_bb=oldrow.get("new_localized_bbox") or oldrow.get("localized_bbox")
    # Most rows already had acceptable scale; B229's material family fix is readable slant.
    # Keep their vertical envelope slightly inside the prior non-overlapping envelope so
    # adjacent atlas labels cannot collide. Slipstream alone is deliberately expanded because
    # the concise copy removes the historical long-string height collapse.
    max_h=(ah-2*MARGIN) if row["key"]=="slipstream_cars" else max(12,(prior_bb[3]-prior_bb[1])-2)
    best=None
    for fs in range(min(110,ah+12),23,-1):
        base=native_tile(row["korean"],fs)
        if base.height>max_h: continue
        avail=aw-2*MARGIN
        scale=min(1.0,avail/max(1,base.width+int(round(SLANT*(base.height-1)))))
        if scale<MIN_XSCALE: continue
        t=shear_right(xscale(base,scale))
        if t.width<=avail and t.height<=max_h:
            best=(fs,scale,t,prior_bb)
            break
    if best is None: raise RuntimeError(("fit failed",row["key"],row["korean"],row["original_bbox"],prior_bb,max_h))
    return best

final=clean.copy()
layers=[]
outrows=[]
for row in rows:
    fs,xs,tile,prior_bb=fit(row)
    x0,y0,x1,y1=row["original_bbox"]; aw=x1-x0; ah=y1-y0
    # Center horizontally in the exact source effect bbox. For previously accepted rows keep
    # the vertical placement inside the old non-overlapping envelope; Slipstream may use the
    # larger source-height envelope because adjacent bottom-row labels are horizontally disjoint.
    px=x0+(aw-tile.width)//2
    if row["key"]=="slipstream_cars":
        py=y0+(ah-tile.height)//2
    else:
        prior_center=(prior_bb[1]+prior_bb[3])//2
        py=prior_center-tile.height//2
        py=max(y0+MARGIN,prior_bb[1]+1,min(py,prior_bb[3]-1-tile.height,y1-MARGIN-tile.height))
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lb=list(layer.getchannel("A").getbbox())
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<=0: raise RuntimeError(("margin",row["key"],lb,margins))
    if lb[2]-lb[0]>aw or lb[3]-lb[1]>ah: raise RuntimeError(("ceiling",row["key"],lb,row["original_bbox"]))
    final.alpha_composite(layer)
    layers.append((row["key"],layer.getchannel("A")))
    oldrow=next(x for x in prior["rows"] if x["key"]==row["key"])
    outrows.append({**row,"prior_localized_bbox":oldrow.get("new_localized_bbox") or oldrow.get("localized_bbox"),
      "localized_bbox":lb,"source_size":[aw,ah],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
      "margins":margins,"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,
      "font_size":fs,"horizontal_scale":round(xs,4),"readable_right_shear":SLANT,
      "fill_rgba":FILL,"inner_stroke_rgba":INNER,"outer_stroke_rgba":OUTER,
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

touch=[]
for i in range(len(layers)):
    for j in range(i+1,len(layers)):
        a=layers[i][1]; b=layers[j][1]
        ov=count(ImageChops.multiply(a,b))
        near=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
        if ov or near: touch.append([layers[i][0],layers[j][0],ov,near])
if touch: raise RuntimeError(("localized overlap/touch",touch))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
if payload[:128]!=sb[:128]: raise RuntimeError("header changed")
candidate.write_bytes(payload)
AFTER=sha(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")

fp=tmp/"final.png"; dec.save(fp); ap=tmp/"allowed.png"; allowed.save(ap)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),
                "--protected-mask",str(pp),"--report",str(out/"B229_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B229_FINAL_VALIDATION.json").read_text())
diff=dmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
target=Image.new("L",(W,H),0)
for _,m in layers: target=ImageChops.lighter(target,bmask(m))
clean_change=dmask(src,clean)
residue=count(ImageChops.multiply(ImageChops.multiply(clean_change,ImageOps.invert(target)),ImageOps.invert(diff)))
if finalrep["status"]!="PASS" or outside or alphaout or prot or residue or touch:
    raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,residue,touch))
target.save(out/"B229_FA7_TARGET_TEXT_MASK.png")

# Old/current candidate must differ only in allowed text regions.
olddiff=dmask(old,dec)
oldoutside=count(ImageChops.multiply(olddiff,ImageOps.invert(allowed)))
if oldoutside: raise RuntimeError(("old candidate changed outside allowed",oldoutside))

# Evidence summaries.
overview=Image.new("RGB",(1536,3*800+90),(20,20,20))
for i,(lab,im) in enumerate([("ENGLISH SOURCE",src),("C88/B-RECOVERY CURRENT",old),("B229 FINAL",dec)]):
    z=comp(im).resize((1536,768),Image.Resampling.LANCZOS)
    overview.paste(z,(0,i*800+28)); ImageDraw.Draw(overview).text((8,i*800+6),lab,fill="white")
overview.save(out/"B229_FA7_SOURCE_OLD_FINAL.jpg","JPEG",quality=94,subsampling=0)

cards=[]
for row in outrows:
    x0,y0,x1,y1=row["original_bbox"]; p=8
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in (src,old,dec)]
    # normalize practical high-zoom without enormous sheets
    scale=2
    ims=[z.resize((z.width*scale,z.height*scale),Image.Resampling.NEAREST) for z in ims]
    cw=sum(z.width for z in ims)+16; ch=max(z.height for z in ims)+26
    c=Image.new("RGB",(cw,ch),(22,22,22)); d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(("SOURCE","OLD","B229"),ims):
        d.text((xx+3,5),lab,fill="white"); c.paste(z,(xx,26)); xx+=z.width+6
    cards.append(c)
maxw=max(c.width for c in cards)
sheet=Image.new("RGB",(maxw,sum(c.height for c in cards)+4*(len(cards)-1)),(18,18,18)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B229_FA7_17ROW_CONTACT_2X.jpg","JPEG",quality=95,subsampling=0)

rawsheet=Image.new("RGB",(1024,2*540),(20,20,20))
for i,(lab,im) in enumerate([("SOURCE RAW MIRROR_Y",raw_src),("B229 RAW MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,512),Image.Resampling.LANCZOS)
    rawsheet.paste(z,(0,i*540+24)); ImageDraw.Draw(rawsheet).text((6,i*540+5),lab,fill="white")
rawsheet.save(out/"B229_FA7_RAW_COMPARE.jpg","JPEG",quality=94,subsampling=0)

old_slip=next(r for r in prior["rows"] if r["key"]=="slipstream_cars")
new_slip=next(r for r in outrows if r["key"]=="slipstream_cars")
report={
 "schema_version":1,"role":"B","run":run,"queue_index":54,"asset":asset,
 "trigger":"PRE_INGAME_004_CURRENT_POLICY_SOURCE_TRANSFORM_AND_SCALE_FALSE_NEGATIVE_RETRY_AFTER_PAIRWISE_COLLISION_GATE",
 "failed_attempts":[
   {"workflow_run":37560975826,"candidate_persisted":False,"reason":"pairwise collision gate rejected first geometry before DDS persistence: match_total/count_gifts and hold_line/honk_horn overlap"},
   {"workflow_run":37561234026,"candidate_persisted":False,"reason":"historical helper allowed-mask was narrower than the current exact source-bbox policy and rejected 23,361 newly slanted pixels that were still inside measured original bboxes; retry rebuilds permission/protection from the 17 exact original_bboxes"}
 ],
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/004_q054_FA7BBB13.jpg",
 "prior_status":"C_USERPOLICY02_PASS_PENDING_INGAME",
 "source_sha256":SOURCE_SHA,"before_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":AFTER,
 "method":"verified B_RECOVERY01 exact clean plate + native CJK rerender of all 17 text rows; no old Korean bitmap scaling",
 "current_policy_findings":[
   "English source family visibly right-italic while B_RECOVERY01 Korean family remained upright; current readable slant-direction gate reopens the asset.",
   "Slipstream the cars! row used long Korean text with fs61 + 0.7651 width compression and decoded height 74 inside a 103px source bbox, visibly weaker than adjacent/source family. B229 uses concise imperative 슬립스트림하세요! and near-source-height native rendering."
 ],
 "palette":{"fill_rgba":FILL,"inner_stroke_rgba":INNER,"outer_stroke_rgba":OUTER},
 "render_policy":{"font":Path(FONT).name,"font_style":FSTYLE,"right_shear":SLANT,"minimum_horizontal_scale":MIN_XSCALE,
   "fit":"largest native per-row height; only bounded horizontal condensation when required; exact source bbox remains hard ceiling"},
 "rows":outrows,
 "slipstream_before":{"korean":old_slip["korean"],"bbox":old_slip.get("new_localized_bbox"),"font_size":old_slip.get("font_size"),"note":"historical renderer additionally used xscale 0.7651"},
 "slipstream_after":{"korean":new_slip["korean"],"bbox":new_slip["localized_bbox"],"font_size":new_slip["font_size"],"horizontal_scale":new_slip["horizontal_scale"]},
 "machine_qa":{"bbox_size_positive_margin":"17/17 PASS","clean_validator":cleanrep["status"],"final_validator":finalrep["status"],
   "changed_pixels_outside_allowed":outside,"alpha_changed_outside_allowed":alphaout,"protected_changed":prot,
   "source_residue":residue,"localized_overlap_touch_pairs":touch,"old_candidate_changes_outside_allowed":oldoutside,
   "header_128_exact":payload[:128]==sb[:128],"raw_mode":mode,"raw_orientation":"mirror_y","roundtrip":"PASS"},
 "ordered_generation_gate":{"1_plate_restoration":"PASS_VERIFIED_B_RECOVERY01_CLEAN",
   "2_slant_direction":"PASS_FRESH_RIGHT_LEAN_ALL_17_ROWS",
   "3_no_unnecessary_undersizing":"PASS_LARGEST_NATIVE_PER_ROW_FIT_WITH_CONCISE_SLIPSTREAM_COPY",
   "4_source_weight_outline_shadow":"PASS_SOURCE_YELLOW_WHITE_NAVY_EFFECT_FAMILY",
   "5_no_clipping":"PASS_17_OF_17_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_OUTSIDE_AND_PROTECTED_ZERO",
   "7_flip_y_raw":"EVIDENCE_WRITTEN","8_immediate_readability":"PENDING_CONTROLLER"},
 "controller_visual_qa":"PENDING_CONTROLLER","status":"B229_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "RUNTIME_VALIDATION":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B229_FA7_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"role":"B","run":run,"queue_index":54,"asset":"FA7BBB13","source_sha256":SOURCE_SHA,
 "before_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":AFTER,
 "reworked_rows":17,"bbox_size_positive_margin":"17/17","outside":outside,"alpha_outside":alphaout,
 "protected_changed":prot,"source_residue":residue,"overlap_touch_pairs":len(touch),
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":str(rp.relative_to(repo))}
(wr/"B229_FA7BBB13.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
