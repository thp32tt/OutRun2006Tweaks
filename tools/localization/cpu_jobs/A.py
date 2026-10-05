#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-PRODUCTION28"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

work=Path("/tmp/outrun_A_prod28"); work.mkdir(parents=True,exist_ok=True)
source=work/"754F0599_HD.dds"
atlas=work/"4x_754F0599_512x256_atlas.json"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="60cbe90be5765b4ade3ce80916d9b2c7ed23e589"
ATLAS_BLOB_SHA1="01228b8c8d50564b77f980773d99a5741b135a5a"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_754F0599_512x256_atlas.json",atlas)

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git_blob_sha1(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def count(m): return sum(m.histogram()[1:])
def bmask(m): return m.point(lambda v:255 if v else 0)
def balpha(im): return bmask(im.getchannel("A"))
def dmask(a,b):
    d=ImageChops.difference(a,b); z=d.split(); m=z[0]
    for q in z[1:]: m=ImageChops.lighter(m,q)
    return bmask(m)
def gray(im):
    bg=Image.new("RGBA",im.size,(88,88,88,255)); bg.alpha_composite(im); return bg.convert("RGB")
def median4(vals):
    return tuple(int(round(statistics.median([v[k] for v in vals]))) for k in range(4))

sb=source.read_bytes(); ab=atlas.read_bytes()
if git_blob_sha1(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source blob drift",git_blob_sha1(sb)))
if git_blob_sha1(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas blob drift",git_blob_sha1(ab)))
SOURCE_SHA=hashlib.sha256(sb).hexdigest()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(2048,1024,8192,1) or depth not in (0,1):
    raise RuntimeError(("structure",W,H,pitch,depth,mips))
if len(sb)!=128+W*H*4: raise RuntimeError(("bytes",len(sb)))
if pf[1]!=65 or pf[2]!=0 or pf[3]!=32 or pf[7]!=0xff000000: raise RuntimeError(("pf",pf))
masks=(pf[4],pf[5],pf[6])
if masks==(0xff,0xff00,0xff0000): RAWMODE="RGBA"
elif masks==(0xff0000,0xff00,0xff): RAWMODE="BGRA"
else: raise RuntimeError(("unsupported masks",masks))

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

aj=json.loads(ab.decode("utf-8"))
regs={int(r["idx"]):r for r in aj["regions"]}
expected={
 0:[0,868,2048,156],1:[0,712,2048,156],2:[0,556,2048,156],
 3:[0,400,2048,156],4:[0,244,2048,156]
}
if len(regs)!=5 or any(regs[i]["rect"]!=expected[i] for i in expected):
    raise RuntimeError(("atlas drift",regs))

# Stock visual is top-to-bottom stage select/showroom/single player/system link/xbox live.
# The atlas indices are bottom-to-top (idx4..idx0) in the canonical readable HD source.
# Xbox Live is a service/brand mark and is preserved pixel-exact.
semantics={
 0:("xbox live",None),
 1:("system link","시스템 링크"),
 2:("single player","싱글 플레이"),
 3:("showroom","쇼룸"),
 4:("stage select","스테이지 선택"),
}
rows=[]
source_text_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
style_data={}
for idx in range(5):
    rx,ry,cw,ch=regs[idx]["rect"]
    y=ry
    cell_rect=[rx,y,rx+cw,y+ch]
    cell=src.crop(tuple(cell_rect))
    am=bmask(cell.getchannel("A"))
    bb=am.getbbox()
    if not bb: raise RuntimeError(("empty cell",idx))
    ob=[rx+bb[0],y+bb[1],rx+bb[2],y+bb[3]]
    en,ko=semantics[idx]
    row={"region_idx":idx,"source":en,"korean":ko,"raw_cell":[rx,ry,cw,ch],
         "readable_cell":[rx,y,cw,ch],"original_bbox":ob,
         "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
         "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
         "preserve_original":ko is None}
    rows.append(row)
    if ko is None:
        continue
    source_text_mask.paste(ImageChops.lighter(source_text_mask.crop(tuple(cell_rect)),am),(rx,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)

    crop=src.crop(tuple(ob)); alpha=crop.getchannel("A")
    pix=crop.load()
    # Source body color profile from eroded high-alpha interior; fall back to row medians.
    k=max(3,min(9,(max(3,(ob[3]-ob[1])//10)|1)))
    core=bmask(alpha.point(lambda v:255 if v>=140 else 0)).filter(ImageFilter.MinFilter(k))
    cm=core.load(); profile=[]
    for yy in range(crop.height):
        vals=[pix[xx,yy] for xx in range(crop.width) if cm[xx,yy]]
        if vals:
            profile.append(tuple(int(round(statistics.median([v[c] for v in vals]))) for c in range(3)))
        else:
            profile.append(None)
    valid=[i for i,v in enumerate(profile) if v is not None]
    if len(valid)<6:
        profile=[]
        ap=alpha.load()
        for yy in range(crop.height):
            vals=[pix[xx,yy] for xx in range(crop.width) if ap[xx,yy]>=110]
            profile.append(tuple(int(round(statistics.median([v[c] for v in vals]))) for c in range(3)) if vals else None)
        valid=[i for i,v in enumerate(profile) if v is not None]
    if not valid: raise RuntimeError(("no fill profile",idx))
    for yy in range(len(profile)):
        if profile[yy] is None:
            j=min(valid,key=lambda z:abs(z-yy)); profile[yy]=profile[j]

    visible=[]
    for yy in range(crop.height):
        for xx in range(crop.width):
            p=pix[xx,yy]
            if p[3]>=60: visible.append(p)
    visible.sort(key=lambda p:p[0]+p[1]+p[2])
    q=max(1,len(visible)//5)
    dark=median4(visible[:q]); bright=median4(visible[-q:])

    # Source visual is a narrow silver techno face with a dark lower-right depth.
    high=Image.new("L",crop.size,0); hp=high.load()
    for yy in range(crop.height):
        for xx in range(crop.width):
            r,g,b,a=pix[xx,yy]
            if a>=120 and min(r,g,b)>=150: hp[xx,yy]=255
    hbb=high.getbbox() or [0,0,crop.width,crop.height]
    margins={"left":hbb[0],"top":hbb[1],"right":crop.width-hbb[2],"bottom":crop.height-hbb[3]}
    style_data[idx]={"profile":profile,"dark":dark,"bright":bright,"margins":margins}

source_visible=balpha(src)
protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))
clean=src.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)

sp=out/"754F0599_HD_SOURCE_READABLE.png"
cp=out/"754F0599_HD_CLEAN_PLATE.png"
smp=out/"754F0599_HD_SOURCE_TEXT_MASK.png"
apath=out/"754F0599_HD_ALLOWED_TEXT_BBOX_MASK.png"
pp=out/"754F0599_HD_PROTECTED_VISIBLE_MASK.png"
cpp=out/"754F0599_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_text_mask.save(smp); allowed.save(apath); protected.save(pp); clean_protected.save(cpp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(cpp),
                "--report",str(out/"A_PRODUCTION28_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A_PRODUCTION28_CLEAN_PLATE_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean fail",cleanrep))
source_unchanged=count(ImageChops.multiply(source_text_mask,ImageOps.invert(dmask(src,clean))))
if source_unchanged!=0: raise RuntimeError(("source pixels unchanged after clean",source_unchanged))

def resolve_font():
    specs=[("Noto Sans CJK KR:style=Regular","Regular"),("Noto Sans CJK KR:style=Bold","Bold"),("Noto Sans CJK KR","")]
    def pick():
        for pat,want in specs:
            try: spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
            except Exception: spec=""
            if "|" not in spec: continue
            fp,idx=spec.rsplit("|",1)
            try: idx=int(idx or "0")
            except Exception: idx=0
            if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name and (not want or want in Path(fp).name):
                return fp,idx,pat
        return None
    got=pick()
    if got: return got
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    got=pick()
    if not got: raise RuntimeError("Noto CJK font unavailable")
    return got
FONT,FONT_INDEX,FONT_PATTERN=resolve_font()

def shear(m,s):
    if not s: return m
    w,h=m.size; k=s/max(1,h-1)
    return m.transform((w+s+4,h),Image.Transform.AFFINE,(1,k,-s,0,1,0),resample=Image.Resampling.BICUBIC)
def gradient(size,profile):
    w,h=size; im=Image.new("RGBA",size,(0,0,0,0)); p=im.load(); n=len(profile)
    for yy in range(h):
        sy=int(round((yy/max(1,h-1))*(n-1))); r,g,b=profile[sy]
        for xx in range(w): p[xx,yy]=(r,g,b,255)
    return im

def render(row):
    ob=row["original_bbox"]; aw,ah=ob[2]-ob[0],ob[3]-ob[1]; st=style_data[row["region_idx"]]
    for fs in range(max(20,int(ah*1.06)),14,-1):
        font=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        outer=max(2,min(8,int(round(ah*0.045))))
        body_extra=max(1,min(3,int(round(ah*0.018))))
        slant=max(3,int(round(fs*0.08)))
        pad=outer+12
        tb=font.getbbox(row["korean"],stroke_width=outer)
        cw=tb[2]-tb[0]+pad*2; ch=tb[3]-tb[1]+pad*2
        om=Image.new("L",(cw,ch),0); od=ImageDraw.Draw(om)
        od.text((pad-tb[0],pad-tb[1]),row["korean"],font=font,fill=255,stroke_width=outer,stroke_fill=255)
        bm=Image.new("L",(cw,ch),0); bd=ImageDraw.Draw(bm)
        bd.text((pad-tb[0],pad-tb[1]),row["korean"],font=font,fill=255,stroke_width=body_extra,stroke_fill=255)
        om=shear(om,slant); bm=shear(bm,slant)
        ub=om.getbbox()
        if not ub: continue
        om=om.crop(ub); bm=bm.crop(ub)
        shadow_x=max(1,min(8,st["margins"]["right"]-st["margins"]["left"]))
        shadow_y=max(2,min(8,st["margins"]["bottom"]-st["margins"]["top"]))
        layer=Image.new("RGBA",(max(om.width,bm.width)+shadow_x,max(om.height,bm.height)+shadow_y),(0,0,0,0))
        sm=Image.new("L",layer.size,0); sm.paste(om,(shadow_x,shadow_y))
        d=st["dark"]; layer.paste(Image.new("RGBA",layer.size,(d[0],d[1],d[2],190)),(0,0),sm)
        mm=Image.new("L",layer.size,0); mm.paste(om,(0,0))
        layer.paste(Image.new("RGBA",layer.size,(d[0],d[1],d[2],255)),(0,0),mm)
        fm=Image.new("L",layer.size,0); fm.paste(bm,(0,0))
        layer.paste(gradient(layer.size,st["profile"]),(0,0),fm)
        lb=layer.getchannel("A").getbbox()
        if not lb: continue
        layer=layer.crop(lb)
        if layer.width<=aw-8 and layer.height<=ah-8:
            tx=ob[0]+4
            ty=ob[1]+(ah-layer.height)//2
            if tx>ob[0] and ty>ob[1] and tx+layer.width<ob[2] and ty+layer.height<ob[3]:
                return layer,(tx,ty),fs,outer,body_extra,slant,[shadow_x,shadow_y]
    raise RuntimeError(("fit",row["source"],row["korean"],ob))

final=clean.copy()
target_masks={}
for row in rows:
    if row["preserve_original"]: continue
    layer,(tx,ty),fs,outer,body_extra,slant,shadow=render(row)
    idx=row["region_idx"]
    layer.save(out/f"A_PRODUCTION28_REGION_{idx}_KOREAN_LAYER.png")
    lm=bmask(layer.getchannel("A"))
    final.paste(layer,(tx,ty),lm)
    tm=Image.new("L",(W,H),0); tm.paste(lm,(tx,ty)); target_masks[idx]=tm
    loc=list(tm.getbbox() or ())
    ob=row["original_bbox"]
    contain=len(loc)==4 and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=contain and (loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
    positive=contain and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    row.update({"localized_bbox":loc,"raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],
                "localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
                "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],
                "delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
                "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
                "positive_margin":"PASS" if positive else "FAIL",
                "font_file":FONT,"font_face_index":FONT_INDEX,"font_pattern":FONT_PATTERN,"font_size":fs,
                "outer_stroke":outer,"body_extra":body_extra,"slant_px":slant,"shadow_offset":shadow,
                "source_style":{"dark":style_data[idx]["dark"],"bright":style_data[idx]["bright"],
                                "profile_samples":[style_data[idx]["profile"][0],
                                  style_data[idx]["profile"][len(style_data[idx]["profile"])//2],
                                  style_data[idx]["profile"][-1]]}})

# Pairwise overlap/touch among four localized labels.
keys=sorted(target_masks)
pair_overlap=0; pair_touch=0
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        pair_overlap+=count(ImageChops.multiply(target_masks[keys[i]],target_masks[keys[j]]))
        pair_touch+=count(ImageChops.multiply(target_masks[keys[i]].filter(ImageFilter.MaxFilter(3)),target_masks[keys[j]]))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw",RAWMODE))
CANDIDATE_SHA=sha256(candidate)
if candidate.read_bytes()[:128]!=sb[:128]: raise RuntimeError("header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw",RAWMODE)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("roundtrip mismatch")
dp=out/"754F0599_HD_FINAL_DECODED_READABLE.png"; decoded.save(dp)
subprocess.run(["python3",str(validator),str(sp),str(dp),str(apath),"--protected-mask",str(pp),
                "--report",str(out/"A_PRODUCTION28_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A_PRODUCTION28_FINAL_MASK_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final fail",finalrep))

diff=dmask(src,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
preserve=next(r for r in rows if r["region_idx"]==0)
px,py,pw,ph=preserve["readable_cell"]
preserve_changes=count(dmask(src.crop((px,py,px+pw,py+ph)),decoded.crop((px,py,px+pw,py+ph))))
guard=Image.new("L",(W,H),0)
for tm in target_masks.values(): guard=ImageChops.lighter(guard,tm.filter(ImageFilter.MaxFilter(5)))
source_residue=count(ImageChops.multiply(balpha(decoded),ImageChops.multiply(source_text_mask,ImageOps.invert(guard))))
localized_rows=[r for r in rows if not r["preserve_original"]]
all_bbox=all(r["containment"]=="PASS" for r in localized_rows)
all_size=all(r["size_ceiling"]=="PASS" for r in localized_rows)
all_positive=all(r["positive_margin"]=="PASS" for r in localized_rows)

sheet=Image.new("RGB",(W,H*3),(88,88,88))
for i,im in enumerate([src,clean,decoded]): sheet.paste(gray(im),(0,i*H))
sheet.save(out/"A_PRODUCTION28_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=96)
gray(decoded_raw).save(out/"A_PRODUCTION28_FINAL_RAW_GRAY.jpg",quality=96)
contacts=[]
for row in rows:
    ob=row["original_bbox"]; m=12
    box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
    ims=[gray(z.crop(box)) for z in [src,clean,decoded]]
    ri=Image.new("RGB",(sum(im.width for im in ims)+16,max(im.height for im in ims)+26),(230,230,230))
    xx=0
    for im in ims: ri.paste(im,(xx,26)); xx+=im.width+8
    label=f"idx{row['region_idx']} {row['source']} -> {row['korean'] if row['korean'] else 'PRESERVE'}  SOURCE | CLEAN | FINAL"
    ImageDraw.Draw(ri).text((3,3),label,fill=(0,0,0))
    contacts.append(ri)
cw=max(im.width for im in contacts); ch=sum(im.height for im in contacts)+4*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(230,230,230)); yy=0
for im in contacts: cs.paste(im,(0,yy)); yy+=im.height+4
cs.save(out/"A_PRODUCTION28_ROW_CONTACT.jpg",quality=96)

status=(cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and source_unchanged==0
        and all_bbox and all_size and all_positive and pair_overlap==0 and pair_touch==0
        and outside==0 and alpha_out==0 and prot==0 and preserve_changes==0 and source_residue==0)

report={
 "schema_version":1,"role":"A","run":run,"index":175,"asset":asset_rel,"worker":"github-actions",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,
  "sha256":SOURCE_SHA,"path":"Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds",
  "classification":"authoritative high-resolution source; stale filename suffix; actual DDS header 2048x1024 RGBA32"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pixel_raw_mode":RAWMODE,"pitch":pitch,"depth":depth,"mipmaps":mips,
  "bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
 "semantic_binding":{"stock_visual_order":["stage select","showroom","single player","system link","xbox live"],"atlas_index_order_readable":[4,3,2,1,0],
  "localized":["stage select -> 스테이지 선택","showroom -> 쇼룸","single player -> 싱글 플레이","system link -> 시스템 링크"],
  "preserved":["xbox live"],"preserve_reason":"Xbox Live is brand/service artwork; preserve original pixels"},
 "rows":rows,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "machine_checks":{"source_mask_pixels_unchanged_in_clean":source_unchanged,
  "localized_pair_overlap_pixels":pair_overlap,"localized_pair_touch_pixels":pair_touch,
  "changed_pixels_outside_source_bboxes":outside,"alpha_changed_pixels_outside_source_bboxes":alpha_out,
  "protected_visible_pixels_changed":prot,"preserved_xbox_live_region_changed_pixels":preserve_changes,
  "source_residue_visible_pixels":source_residue},
 "all_4_bbox_pass":all_bbox,"all_4_size_ceiling_pass":all_size,"all_4_positive_margin":all_positive,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_PRODUCTION28_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status else "A_PRODUCTION28_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION28_754F0599_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"754F0599","index":175,"source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,
 "source_dimensions":[W,H],"format":"RGBA32","localized_rows":4,"preserved_rows":1,
 "bbox_pass":"4/4" if all_bbox else "FAIL","size_ceiling":"4/4" if all_size else "FAIL",
 "positive_margin":"4/4" if all_positive else "FAIL","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "source_mask_pixels_unchanged_in_clean":source_unchanged,"localized_pair_overlap_pixels":pair_overlap,
 "localized_pair_touch_pixels":pair_touch,"changed_pixels_outside_source_bboxes":outside,
 "alpha_changed_pixels_outside_source_bboxes":alpha_out,"protected_visible_pixels_changed":prot,
 "preserved_xbox_live_region_changed_pixels":preserve_changes,"source_residue_visible_pixels":source_residue,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261005-A-PRODUCTION28/A_PRODUCTION28_754F0599_REPORT.json"}
(wr/"A_PRODUCTION28_754F0599.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status: raise SystemExit(2)
