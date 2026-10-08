#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261008-A187-Q175-CHROME-BEVEL-FAMILY"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
PRIOR_SHA="cac88b8553e36b2cf8e87edbc9edea7edf25f2b9e0ff651b14ea21f75a6c91ab"
if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest()!=PRIOR_SHA: raise RuntimeError("q175 current persisted A185R bytes drifted; do not overwrite")
validator=repo/"tools/localization/validate_clean_plate.py"
work=Path("/tmp/outrun_A_prod28_final"); work.mkdir(parents=True,exist_ok=True)
source=work/"754F0599_HD.dds"; atlas=work/"4x_754F0599_512x256_atlas.json"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="60cbe90be5765b4ade3ce80916d9b2c7ed23e589"
ATLAS_BLOB_SHA1="01228b8c8d50564b77f980773d99a5741b135a5a"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_754F0599_512x256_atlas.json",atlas)

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blobsha(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def count(m): return sum(m.histogram()[1:])
def bmask(m): return m.point(lambda v:255 if v else 0)
def balpha(im): return bmask(im.getchannel("A"))
def dmask(a,b):
    d=ImageChops.difference(a,b); z=d.split(); m=z[0]
    for q in z[1:]: m=ImageChops.lighter(m,q)
    return bmask(m)
def gray(im):
    z=Image.new("RGBA",im.size,(96,96,96,255)); z.alpha_composite(im); return z.convert("RGB")
def med(vals,k):
    return int(round(statistics.median([v[k] for v in vals])))

sb=source.read_bytes(); ab=atlas.read_bytes()
if blobsha(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source blob drift",blobsha(sb)))
if blobsha(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas blob drift",blobsha(ab)))
SOURCE_SHA=hashlib.sha256(sb).hexdigest()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(2048,1024,8192,1) or depth not in (0,1): raise RuntimeError(("structure",W,H,pitch,depth,mips))
if len(sb)!=128+W*H*4: raise RuntimeError(("bytes",len(sb)))
if pf[1]!=65 or pf[2]!=0 or pf[3]!=32 or pf[7]!=0xff000000: raise RuntimeError(("pf",pf))
rgbm=(pf[4],pf[5],pf[6])
if rgbm==(0xff,0xff00,0xff0000): RAWMODE="RGBA"
elif rgbm==(0xff0000,0xff00,0xff): RAWMODE="BGRA"
else: raise RuntimeError(("masks",rgbm))

raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# Preflight/controller visual evidence from the same canonical source proves this HD
# replacement contains exactly three visible labels: stage select, showroom, single player.
# Historical "system link" and "xbox live" draft rows are absent from canonical HD pixels.
alpha=src.getchannel("A")
# Strong-alpha projection yields one seed band per visible source label. Low-alpha
# shadow/fringe can bridge rows, so it is assigned afterward by midpoint partitions.
strong=alpha.point(lambda v:255 if v>=128 else 0)
proj=[]
for y in range(H):
    crop=strong.crop((0,y,W,y+1))
    proj.append(count(crop)>=20)
seed=[]
s=None
for y,on in enumerate(proj+[False]):
    if on and s is None: s=y
    if not on and s is not None:
        seed.append([s,y]); s=None
merged=[]
for b in seed:
    if merged and b[0]-merged[-1][1]<=12:
        merged[-1][1]=b[1]
    else:
        merged.append(b)
seed=merged
if len(seed)!=3:
    raise RuntimeError(("canonical strong row seeds drift",seed))
centers=[(a+b)//2 for a,b in seed]
gb=alpha.getbbox()
if not gb: raise RuntimeError("global alpha empty")
cuts=[gb[1],(centers[0]+centers[1])//2,(centers[1]+centers[2])//2,gb[3]]
bands=[[cuts[i],cuts[i+1]] for i in range(3)]

sem=[("stage select","스테이지 선택"),("showroom","쇼룸"),("single player","싱글 플레이")]
rows=[]; source_text_mask=Image.new("L",(W,H),0); allowed=Image.new("L",(W,H),0); styles={}
for i,(yb,enko) in enumerate(zip(bands,sem)):
    y0,y1=yb; en,ko=enko
    row_alpha=alpha.crop((0,y0,W,y1))
    bb=row_alpha.getbbox()
    if not bb: raise RuntimeError(("empty band",i,yb))
    ob=[bb[0],y0+bb[1],bb[2],y0+bb[3]]
    m=Image.new("L",(W,H),0)
    m.paste(bmask(src.crop(tuple(ob)).getchannel("A")),(ob[0],ob[1]))
    source_text_mask=ImageChops.lighter(source_text_mask,m)
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)

    crop=src.crop(tuple(ob)); ca=crop.getchannel("A"); pix=crop.load()
    k=max(3,min(9,(max(3,(ob[3]-ob[1])//10)|1)))
    core=bmask(ca.point(lambda v:255 if v>=140 else 0)).filter(ImageFilter.MinFilter(k))
    cm=core.load(); profile=[]
    for yy in range(crop.height):
        vals=[pix[xx,yy] for xx in range(crop.width) if cm[xx,yy]]
        profile.append(tuple(med(vals,c) for c in range(3)) if vals else None)
    valid=[j for j,v in enumerate(profile) if v is not None]
    if len(valid)<6:
        profile=[]
        ap=ca.load()
        for yy in range(crop.height):
            vals=[pix[xx,yy] for xx in range(crop.width) if ap[xx,yy]>=100]
            profile.append(tuple(med(vals,c) for c in range(3)) if vals else None)
        valid=[j for j,v in enumerate(profile) if v is not None]
    if not valid: raise RuntimeError(("no style profile",i))
    for yy in range(len(profile)):
        if profile[yy] is None:
            j=min(valid,key=lambda z:abs(z-yy)); profile[yy]=profile[j]
    visible=[pix[xx,yy] for yy in range(crop.height) for xx in range(crop.width) if pix[xx,yy][3]>=60]
    visible.sort(key=lambda p:p[0]+p[1]+p[2]); q=max(1,len(visible)//6)
    dark=tuple(med(visible[:q],c) for c in range(3))+(255,)
    bright=tuple(med(visible[-q:],c) for c in range(3))+(255,)
    styles[i]={"profile":profile,"dark":dark,"bright":bright}
    rows.append({"row":i,"source":en,"korean":ko,"original_bbox":ob,
                 "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
                 "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1]})

source_visible=balpha(src)
protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))
clean=src.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)

sp=out/"754F0599_HD_SOURCE_READABLE.png"; cp=out/"754F0599_HD_CLEAN_PLATE.png"
smp=out/"754F0599_HD_SOURCE_TEXT_MASK.png"; apath=out/"754F0599_HD_ALLOWED_TEXT_BBOX_MASK.png"
pp=out/"754F0599_HD_PROTECTED_VISIBLE_MASK.png"; cpp=out/"754F0599_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_text_mask.save(smp); allowed.save(apath); protected.save(pp); clean_protected.save(cpp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(cpp),
                "--report",str(out/"A187_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A187_CLEAN_PLATE_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean",cleanrep))
source_unchanged=count(ImageChops.multiply(source_text_mask,ImageOps.invert(dmask(src,clean))))
if source_unchanged!=0: raise RuntimeError(("clean unchanged source",source_unchanged))

def resolve_font():
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-nanum","fonts-noto-cjk"],check=True)
    spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{family}|%{style}",
                                  "NanumSquareRound:style=Bold"],text=True).strip()
    path,index,family,style=spec.rsplit("|",3)
    if not Path(path).exists() or "NanumSquareRound" not in family or "Bold" not in family+style:
        raise RuntimeError(("rounded Hangul family not available",spec))
    return path,int(index or 0),family,style
FONT,FONT_INDEX,FONT_FAMILY,FONT_STYLE=resolve_font()
FONT_PATTERN=FONT_FAMILY+':'+FONT_STYLE

def tracked_core(text, fs, tracking):
    # 3x supersampled original-size native Hangul; scale down only for AA.
    ss=3
    font=ImageFont.truetype(FONT,fs*ss,index=FONT_INDEX)
    tr=tracking*ss
    chars=list(text)
    width=int(sum(font.getlength(c) for c in chars) + max(0,len(chars)-1)*tr)
    asc,desc=font.getmetrics(); pad=36*ss
    m=Image.new("L",(width+2*pad+ss*12,asc+desc+2*pad),0)
    d=ImageDraw.Draw(m); pos=float(pad)
    for c in chars:
        d.text((int(round(pos)),pad),c,font=font,fill=255)
        pos+=font.getlength(c)+tr
    bb=m.getbbox()
    if not bb:return None
    m=m.crop(bb)
    # Positive readable tilt = top displaced right, original source right leaning.
    lean=.115
    extra=int(round(lean*(m.height-1)))
    shear=Image.new("L",(m.width+extra+3*ss,m.height),0)
    for y in range(m.height):
        dx=int(round(lean*(m.height-1-y)))
        shear.paste(m.crop((0,y,m.width,y+1)),(dx,y))
    shear=shear.crop(shear.getbbox())
    return shear.resize((max(1,round(shear.width/ss)),max(1,round(shear.height/ss))),Image.Resampling.LANCZOS)

def blend_lut(points,z):
    if z<=points[0][0]:return points[0][1]
    for k in range(1,len(points)):
        b,c=points[k]
        if z<=b:
            a,d=points[k-1]; t=(z-a)/max(.00001,b-a)
            return round(d*(1-t)+c*t)
    return points[-1][1]

def colored_mask(size,color,mask):
    layer=Image.new("RGBA",size,color)
    # Putalpha is safe for gradient/outline; native overlay uses alpha compositing.
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"),mask))
    return layer

def offset_mask(mask,dx,dy):
    dest=Image.new("L",mask.size,0)
    dest.paste(mask,(dx,dy))
    return dest

def render(row):
    ob=row["original_bbox"]; aw,ah=ob[2]-ob[0],ob[3]-ob[1]; style=styles[row["row"]]
    # Geometry: natural rounded Korean strokes with character tracking, never width quota.
    # Visual: source-chrome bright top, steel/gray mid and lower specular lip;
    # dark multi-layer downward extrusion; outer keyline, bevel and full opaque counters.
    for fs in range(round(ah*1.18),48,-1):
        tracking=max(4,round(fs*.20))
        core=tracked_core(row["korean"],fs,tracking)
        if core is None:continue
        pad=16
        body=Image.new("L",(core.width+2*pad,core.height+2*pad),0)
        body.paste(core,(pad,pad))
        outline=body.filter(ImageFilter.MaxFilter(7))
        # Source chrome has appreciable 3D depth, not the shallow flat A185R drop.
        extrusions=[(5,9,135),(4,7,170),(3,5,205)]
        tile=Image.new("RGBA",body.size,(0,0,0,0))
        for dx,dy,op in extrusions:
            em=offset_mask(outline,dx,dy)
            tile.alpha_composite(colored_mask(body.size,(9,11,20,op),em))
        tile.alpha_composite(colored_mask(body.size,(30,34,40,255),outline))
        h,w=body.height,body.width
        # Source samples set the upper face ceiling, not an arbitrary fixed white.
        hi=min(250,max(235,int(sum(style["bright"][:3])/3)))
        stops=[(0.0,hi),(.18,hi-3),(.37,188),(.54,230),
               (.63,245),(.76,168),(.86,98),(1.0,175)]
        arr=bytearray(w*h*4)
        # Vectorization is not required for 3 small rows.
        for y in range(h):
            t=(y-pad)/max(1,core.height-1)
            v=max(0,min(255,blend_lut(stops,t)))
            for x in range(w):
                j=(y*w+x)*4
                arr[j:j+4]=bytes((v,v,v,255))
        face=Image.frombytes("RGBA",(w,h),bytes(arr));face.putalpha(body)
        tile.alpha_composite(face)
        # Top bevel: visible pale lip inside strokes; lower-inner charcoal inset.
        lip=ImageChops.subtract(body,offset_mask(body,0,3))
        tile.alpha_composite(colored_mask(body.size,(250,250,252,215),lip))
        low=ImageChops.subtract(body,offset_mask(body,0,-3))
        tile.alpha_composite(colored_mask(body.size,(50,53,60,190),low))
        bbox=tile.getbbox()
        if bbox is None:continue
        tile=tile.crop(bbox)
        if tile.width>aw-12 or tile.height>ah-10:continue
        if tile.height<ah*.81:continue
        tx=ob[0]+6
        ty=ob[1]+(ah-tile.height)//2
        if tx<=ob[0] or ty<=ob[1] or tx+tile.width>=ob[2] or ty+tile.height>=ob[3]:
            continue
        effects={"font_family":FONT_FAMILY,"font_style":FONT_STYLE,"source_style":"thick bright silver beveled rounded geometric lower extrusion",
                 "face_chrome_gradient":"source sampled top + specular band + dark lower channel",
                 "bevel_highlight_px":3,"lower_inner_dark_px":3,
                 "extrusion_layers":extrusions,"outline_px":3,"readable_right_shear":.115,
                 "natural_hangul_width_no_forced_resize":True,"tracking_px":tracking,
                 "prior_flat_chrome_A185R_source_style_rework":True}
        return tile,(tx,ty),fs,3,0,round(fs*.115),[5,9],tile.width,tile.height,effects
    raise RuntimeError(("SOURCE CHROME natural fit impossible",row))

final=clean.copy(); target_masks={}
for row in rows:
    layer,(tx,ty),fs,outer,body,slant,shadow,target_w,target_h,effects=render(row)
    layer.save(out/f"A187_ROW_{row['row']}_KOREAN_LAYER.png")
    lm=bmask(layer.getchannel("A")); final.alpha_composite(layer,(tx,ty))
    tm=Image.new("L",(W,H),0); tm.paste(lm,(tx,ty)); target_masks[row["row"]]=tm
    loc=list(tm.getbbox() or ()); ob=row["original_bbox"]
    contain=len(loc)==4 and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=contain and loc[2]-loc[0]<=ob[2]-ob[0] and loc[3]-loc[1]<=ob[3]-ob[1]
    positive=contain and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    row.update({"localized_bbox":loc,"raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],
      "localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
      "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],"delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "FAIL",
      "font_file":FONT,"font_face_index":FONT_INDEX,"font_pattern":FONT_PATTERN,"font_size":fs,
      "outer_stroke":outer,"body_extra":body,"slant_px":slant,"shadow_offset":shadow,"natural_width":target_w,"natural_height":target_h,"c278_rework":"source_rounded_chrome_bevel_lower_extrusion_without_forced_width",
      "native_chrome_family_effects":effects,
      "source_style":{"dark":styles[row["row"]]["dark"],"bright":styles[row["row"]]["bright"],
                      "profile_samples":[styles[row["row"]]["profile"][0],styles[row["row"]]["profile"][len(styles[row["row"]]["profile"])//2],styles[row["row"]]["profile"][-1]]}})

keys=sorted(target_masks); overlap=0; touch=0
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        overlap+=count(ImageChops.multiply(target_masks[keys[i]],target_masks[keys[j]]))
        touch+=count(ImageChops.multiply(target_masks[keys[i]].filter(ImageFilter.MaxFilter(3)),target_masks[keys[j]]))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw",RAWMODE))
CANDIDATE_SHA=sha256(candidate)
if candidate.read_bytes()[:128]!=sb[:128]: raise RuntimeError("header")
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw",RAWMODE)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("roundtrip")
dp=out/"754F0599_HD_FINAL_DECODED_READABLE.png"; decoded.save(dp)
subprocess.run(["python3",str(validator),str(sp),str(dp),str(apath),"--protected-mask",str(pp),
                "--report",str(out/"A187_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A187_FINAL_MASK_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final",finalrep))
diff=dmask(src,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
guard=Image.new("L",(W,H),0)
for tm in target_masks.values(): guard=ImageChops.lighter(guard,tm.filter(ImageFilter.MaxFilter(5)))
residue=count(ImageChops.multiply(balpha(decoded),ImageChops.multiply(source_text_mask,ImageOps.invert(guard))))
all_bbox=all(r["containment"]=="PASS" for r in rows); all_size=all(r["size_ceiling"]=="PASS" for r in rows); all_positive=all(r["positive_margin"]=="PASS" for r in rows)

sheet=Image.new("RGB",(W,H*3),(96,96,96))
for i,im in enumerate([src,clean,decoded]): sheet.paste(gray(im),(0,i*H))
sheet.save(out/"A187_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=96)
gray(decoded_raw).save(out/"A187_FINAL_RAW_GRAY.jpg",quality=96)
contacts=[]
for row in rows:
    ob=row["original_bbox"]; m=16; box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
    ims=[gray(z.crop(box)) for z in [src,clean,decoded]]
    ri=Image.new("RGB",(sum(x.width for x in ims)+16,max(x.height for x in ims)+28),(235,235,235)); xx=0
    for im in ims: ri.paste(im,(xx,28)); xx+=im.width+8
    ImageDraw.Draw(ri).text((3,4),f"{row['source']} -> {row['korean']}  SOURCE | CLEAN | FINAL",fill=(0,0,0)); contacts.append(ri)
cw=max(x.width for x in contacts); ch=sum(x.height for x in contacts)+4*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for im in contacts: cs.paste(im,(0,yy)); yy+=im.height+4
cs.save(out/"A187_ROW_CONTACT.jpg",quality=96)

status=(cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and source_unchanged==0 and all_bbox and all_size and all_positive
        and overlap==0 and touch==0 and outside==0 and alpha_out==0 and prot==0 and residue==0)
report={"schema_version":1,"role":"A","run":run,"index":175,"asset":asset_rel,"worker":"github-actions",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA,
  "path":"Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds","classification":"authoritative HD source; actual DDS 2048x1024 RGBA32"},
 "source_sha256":SOURCE_SHA,"previous_candidate_sha256":PRIOR_SHA,"candidate_sha256":CANDIDATE_SHA,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pixel_raw_mode":RAWMODE,"pitch":pitch,"depth":depth,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
 "semantic_binding":{"canonical_visible_physical_rows":3,"localized":["stage select -> 스테이지 선택","showroom -> 쇼룸","single player -> 싱글 플레이"],
  "historical_draft_rows_absent_in_canonical_hd":["system link","xbox live"],
  "binding_evidence":"20261008-A187-Q175-CHROME-BEVEL-FAMILY-PREFLIGHT full raw/flip canonical source visuals"},
 "rows":rows,"clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "machine_checks":{"source_mask_pixels_unchanged_in_clean":source_unchanged,"localized_overlap_pixels":overlap,"localized_touch_pixels":touch,
  "changed_pixels_outside_source_bboxes":outside,"alpha_changed_pixels_outside_source_bboxes":alpha_out,"protected_visible_pixels_changed":prot,"source_residue_visible_pixels":residue},
 "all_3_bbox_pass":all_bbox,"all_3_size_ceiling_pass":all_size,"all_3_positive_margin":all_positive,
 "controller_visual_qa":"PENDING_CONTROLLER_SOURCE_CLEAN_FINAL_RAW_PRACTICAL","c278_rework_reason":"C278_SOURCE_CHROME_BEVEL_EXTRUSION_UNDERDEPTH","c170_rework_applied":"wider/lower horizontal scaling, lighter keyline, metallic source-derived grayscale fill, lower dark extrusion; absent system link/xbox live remain omitted","runtime_validation":"UNTESTED",
 "status":"A187_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_PIXEL_VISUAL_REVIEW" if status else "A187_WORKER_REWORK_REQUIRED"}
(out/"A187_754F0599_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"asset":"754F0599","index":175,"source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,
 "source_dimensions":[W,H],"format":"RGBA32","localized_rows":3,"absent_historical_rows":2,
 "bbox_pass":"3/3" if all_bbox else "FAIL","size_ceiling":"3/3" if all_size else "FAIL","positive_margin":"3/3" if all_positive else "FAIL",
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],"source_mask_pixels_unchanged_in_clean":source_unchanged,
 "localized_overlap_pixels":overlap,"localized_touch_pixels":touch,"changed_pixels_outside_source_bboxes":outside,
 "alpha_changed_pixels_outside_source_bboxes":alpha_out,"protected_visible_pixels_changed":prot,"source_residue_visible_pixels":residue,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261008-A187-Q175-CHROME-BEVEL-FAMILY/A187_754F0599_REPORT.json"}
(wr/"A187_754F0599.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
# Source-vs-actual persisted DDS practical scale comparisons.
practical=[]
for row in rows:
    ob=row["original_bbox"]; pad=12; box=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(W,ob[2]+pad),min(H,ob[3]+pad))
    for sc in [1.0,.75,.5]:
        images=[]
        for name,im in [("ENGLISH SOURCE",src),("KOREAN PERSISTED DDS",decoded)]:
            a=gray(im.crop(box))
            a=a.resize((max(1,round(a.width*sc)),max(1,round(a.height*sc))),Image.Resampling.LANCZOS)
            z=Image.new("RGB",(a.width,a.height+24),(70,70,70));z.paste(a,(0,24))
            ImageDraw.Draw(z).text((3,3),f"{row['row']} {name} {sc:.2f}",fill=(255,255,255))
            images.append(z)
        line=Image.new("RGB",(sum(z.width for z in images)+8,max(z.height for z in images)),(70,70,70))
        xx=0
        for z in images:line.paste(z,(xx,0));xx+=z.width+8
        practical.append(line)
sheet=Image.new("RGB",(max(z.width for z in practical),sum(z.height+4 for z in practical)),(70,70,70))
yy=0
for z in practical: sheet.paste(z,(0,yy));yy+=z.height+4
sheet.save(out/"A187_PRACTICAL_100_75_50.jpg",quality=97,subsampling=0)
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status: raise SystemExit(2)
