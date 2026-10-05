#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-PRODUCTION27"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_sumo_loading_Exst/E1639D2E_256x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

work=Path("/tmp/outrun_A_prod27"); work.mkdir(parents=True,exist_ok=True)
source=work/"E1639D2E_HD.dds"
atlas=work/"4x_E1639D2E_256x64_atlas.json"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="1a119356bf20b0116d408ffe510e62ec90fc0c53"
ATLAS_BLOB_SHA1="7dea136122a164eeb72a53f060308410facd3fd9"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_loading_Exst/E1639D2E_256x64.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_loading_Exst/4x_E1639D2E_256x64_atlas.json",atlas)

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
    bg=Image.new("RGBA",im.size,(90,90,90,255)); bg.alpha_composite(im); return bg.convert("RGB")
def med(vals,k):
    a=sorted(v[k] for v in vals)
    return int(round(a[len(a)//2]))

sb=source.read_bytes(); ab=atlas.read_bytes()
if git_blob_sha1(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source blob drift",git_blob_sha1(sb)))
if git_blob_sha1(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas blob drift",git_blob_sha1(ab)))
SOURCE_SHA=hashlib.sha256(sb).hexdigest()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(1024,256,4096,1) or depth not in (0,1): raise RuntimeError(("structure",W,H,pitch,depth,mips))
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
if len(regs)!=2 or regs[0]["rect"]!=[0,104,904,152] or regs[1]["rect"]!=[0,44,512,60]:
    raise RuntimeError(("atlas drift",regs))

# Atlas/readable binding from stock visual and region geometry:
# region 0 = Loading, region 1 = PLEASE WAIT.
specs=[
  {"idx":0,"source":"Loading","korean":"로딩","family":"large_metallic"},
  {"idx":1,"source":"PLEASE WAIT","korean":"잠시만요","family":"small_wait"},
]

source_text_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
rows=[]
styles={}
for spec in specs:
    x,y,cw,ch=regs[spec["idx"]]["rect"]
    cell=src.crop((x,y,x+cw,y+ch))
    am=bmask(cell.getchannel("A"))
    bb=am.getbbox()
    if not bb: raise RuntimeError(("empty region",spec))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_text_mask.paste(ImageChops.lighter(source_text_mask.crop((x,y,x+cw,y+ch)),am),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)

    crop=src.crop(tuple(ob))
    alpha=crop.getchannel("A")
    ah=ob[3]-ob[1]
    k=max(3,min(9,(max(3,ah//10)|1)))
    core=bmask(alpha.point(lambda v:255 if v>=140 else 0)).filter(ImageFilter.MinFilter(k))
    pix=crop.load(); cm=core.load()
    profile=[]
    for yy in range(crop.height):
        vals=[]
        for xx in range(crop.width):
            if cm[xx,yy]:
                r,g,b,a=pix[xx,yy]
                if a>=100: vals.append((r,g,b,a))
        if vals:
            profile.append((med(vals,0),med(vals,1),med(vals,2)))
        else:
            profile.append(None)
    valid=[i for i,v in enumerate(profile) if v is not None]
    if len(valid)<max(4,ah//12):
        # Small source rows may have no erosion core. Use visible row medians.
        profile=[]
        ap=alpha.load()
        for yy in range(crop.height):
            vals=[pix[xx,yy] for xx in range(crop.width) if ap[xx,yy]>=100]
            profile.append((med(vals,0),med(vals,1),med(vals,2)) if vals else None)
        valid=[i for i,v in enumerate(profile) if v is not None]
    if not valid: raise RuntimeError(("no profile",spec["idx"]))
    for i in range(len(profile)):
        if profile[i] is None:
            j=min(valid,key=lambda z:abs(z-i)); profile[i]=profile[j]

    visible=[]
    ap=alpha.load()
    for yy in range(crop.height):
        for xx in range(crop.width):
            if ap[xx,yy]>=50: visible.append(pix[xx,yy])
    lums=sorted(((p[0]+p[1]+p[2],p) for p in visible),key=lambda z:z[0])
    dark_pool=[p for _,p in lums[:max(1,len(lums)//5)]]
    bright_pool=[p for _,p in lums[-max(1,len(lums)//5):]]
    dark=(med(dark_pool,0),med(dark_pool,1),med(dark_pool,2),255)
    bright=(med(bright_pool,0),med(bright_pool,1),med(bright_pool,2),255)

    # Estimate effect asymmetry from bright-core bbox vs complete alpha bbox.
    brightm=Image.new("L",crop.size,0); bp=brightm.load()
    for yy in range(crop.height):
        for xx in range(crop.width):
            r,g,b,a=pix[xx,yy]
            if a>=100 and min(r,g,b)>=150: bp[xx,yy]=255
    bbb=brightm.getbbox() or [0,0,crop.width,crop.height]
    margins={"left":bbb[0],"top":bbb[1],"right":crop.width-bbb[2],"bottom":crop.height-bbb[3]}
    styles[spec["idx"]]={"profile":profile,"dark":dark,"bright":bright,"margins":margins}
    rows.append({**spec,"cell":[x,y,cw,ch],"original_bbox":ob,"source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
                 "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]]})

source_visible=balpha(src)
protected=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))
clean=src.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)

sp=out/"E1639D2E_HD_SOURCE_READABLE.png"
cp=out/"E1639D2E_HD_CLEAN_PLATE.png"
smp=out/"E1639D2E_HD_SOURCE_TEXT_MASK.png"
apath=out/"E1639D2E_HD_ALLOWED_TEXT_REGION_MASK.png"
pp=out/"E1639D2E_HD_PROTECTED_VISIBLE_MASK.png"
cpp=out/"E1639D2E_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cp); source_text_mask.save(smp); allowed.save(apath); protected.save(pp); clean_protected.save(cpp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(cpp),
                "--report",str(out/"A_PRODUCTION27_CLEAN_PLATE_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"A_PRODUCTION27_CLEAN_PLATE_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean",cleanrep))
unchanged=count(ImageChops.multiply(source_text_mask,ImageOps.invert(dmask(src,clean))))
if unchanged!=0: raise RuntimeError(("source text unchanged",unchanged))

def resolve_font():
    specs=[("Noto Sans CJK KR:style=Bold","Bold"),("Noto Sans CJK KR","")]
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
    if not got: raise RuntimeError("Noto CJK Bold unavailable")
    return got
FONT,FONT_INDEX,FONT_PATTERN=resolve_font()

def shear(m,s):
    w,h=m.size
    if s==0: return m
    k=s/max(1,h-1)
    return m.transform((w+abs(s)+4,h),Image.Transform.AFFINE,(1,k,-min(s,0),0,1,0),resample=Image.Resampling.BICUBIC)

def gradient(size,profile):
    w,h=size; im=Image.new("RGBA",size,(0,0,0,0)); p=im.load(); n=len(profile)
    for yy in range(h):
        sy=int(round((yy/max(1,h-1))*(n-1)))
        r,g,b=profile[sy]
        for xx in range(w): p[xx,yy]=(r,g,b,255)
    return im

def render(row):
    ob=row["original_bbox"]; aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    st=styles[row["idx"]]
    # Loading source is visibly techno/slanted; small PLEASE WAIT stays conservative.
    slant_ratio=0.10 if row["idx"]==0 else 0.03
    for fs in range(max(18,int(ah*1.05)),12,-1):
        f=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        outline=max(1,min(8,int(round(ah*0.045))))
        body_extra=max(1,min(4,int(round(ah*0.018))))
        pad=outline+12
        tb=f.getbbox(row["korean"],stroke_width=outline)
        cw=tb[2]-tb[0]+pad*2; ch=tb[3]-tb[1]+pad*2
        om=Image.new("L",(cw,ch),0); od=ImageDraw.Draw(om)
        od.text((pad-tb[0],pad-tb[1]),row["korean"],font=f,fill=255,stroke_width=outline,stroke_fill=255)
        bm=Image.new("L",(cw,ch),0); bd=ImageDraw.Draw(bm)
        bd.text((pad-tb[0],pad-tb[1]),row["korean"],font=f,fill=255,stroke_width=body_extra,stroke_fill=255)
        slant=int(round(fs*slant_ratio))
        om=shear(om,slant); bm=shear(bm,slant)
        ub=om.getbbox()
        if not ub: continue
        om=om.crop(ub); bm=bm.crop(ub)
        sw=max(0,min(8,st["margins"]["right"]-st["margins"]["left"]))
        sh=max(0,min(8,st["margins"]["bottom"]-st["margins"]["top"]))
        layer=Image.new("RGBA",(max(om.width,bm.width)+sw,max(om.height,bm.height)+sh),(0,0,0,0))
        if sw or sh:
            sm=Image.new("L",layer.size,0); sm.paste(om,(sw,sh))
            d=st["dark"]; layer.paste(Image.new("RGBA",layer.size,(d[0],d[1],d[2],190)),(0,0),sm)
        mm=Image.new("L",layer.size,0); mm.paste(om,(0,0))
        d=st["dark"]; layer.paste(Image.new("RGBA",layer.size,(d[0],d[1],d[2],255)),(0,0),mm)
        fm=Image.new("L",layer.size,0); fm.paste(bm,(0,0))
        layer.paste(gradient(layer.size,st["profile"]),(0,0),fm)
        lb=layer.getchannel("A").getbbox()
        if not lb: continue
        layer=layer.crop(lb)
        if layer.width<=aw-4 and layer.height<=ah-4:
            tx=ob[0]+(aw-layer.width)//2; ty=ob[1]+(ah-layer.height)//2
            if tx>ob[0] and ty>ob[1] and tx+layer.width<ob[2] and ty+layer.height<ob[3]:
                return layer,(tx,ty),fs,outline,body_extra,slant,[sw,sh]
    raise RuntimeError(("fit",row))

final=clean.copy()
target_masks={}
for row in rows:
    layer,(tx,ty),fs,outline,body_extra,slant,shadow=render(row)
    layer.save(out/f"A_PRODUCTION27_REGION_{row['idx']}_KOREAN_LAYER.png")
    lm=bmask(layer.getchannel("A"))
    final.paste(layer,(tx,ty),lm)
    tm=Image.new("L",(W,H),0); tm.paste(lm,(tx,ty)); target_masks[row["idx"]]=tm
    loc=list(tm.getbbox() or ())
    if len(loc)!=4: raise RuntimeError(("loc bbox",row["idx"]))
    ob=row["original_bbox"]
    contain=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=(loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
    positive=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    row.update({"localized_bbox":loc,"localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
                "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],"delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
                "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
                "positive_margin":"PASS" if positive else "FAIL",
                "raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],
                "font_file":FONT,"font_face_index":FONT_INDEX,"font_pattern":FONT_PATTERN,"font_size":fs,
                "outline_px":outline,"body_extra_px":body_extra,"slant_px":slant,"shadow_offset":shadow,
                "source_style":{"dark":styles[row["idx"]]["dark"],"bright":styles[row["idx"]]["bright"],
                                "margins":styles[row["idx"]]["margins"],
                                "profile_samples":[styles[row["idx"]]["profile"][0],
                                    styles[row["idx"]]["profile"][len(styles[row["idx"]]["profile"])//2],
                                    styles[row["idx"]]["profile"][-1]]}})

overlap=count(ImageChops.multiply(target_masks[0],target_masks[1]))
touch=count(ImageChops.multiply(target_masks[0].filter(ImageFilter.MaxFilter(3)),target_masks[1]))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw",RAWMODE))
CANDIDATE_SHA=sha256(candidate)
if candidate.read_bytes()[:128]!=sb[:128]: raise RuntimeError("header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw",RAWMODE)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("roundtrip mismatch")
dp=out/"E1639D2E_HD_FINAL_DECODED_READABLE.png"; decoded.save(dp)
subprocess.run(["python3",str(validator),str(sp),str(dp),str(apath),"--protected-mask",str(pp),
                "--report",str(out/"A_PRODUCTION27_FINAL_MASK_VALIDATION.json")],check=True)
finalrep=json.loads((out/"A_PRODUCTION27_FINAL_MASK_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final",finalrep))

diff=dmask(src,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
source_residue=count(ImageChops.multiply(balpha(decoded),ImageChops.multiply(source_text_mask,ImageOps.invert(ImageChops.lighter(target_masks[0].filter(ImageFilter.MaxFilter(5)),target_masks[1].filter(ImageFilter.MaxFilter(5)))))))
all_bbox=all(r["containment"]=="PASS" for r in rows)
all_size=all(r["size_ceiling"]=="PASS" for r in rows)
all_positive=all(r["positive_margin"]=="PASS" for r in rows)

sheet=Image.new("RGB",(W,H*3),(90,90,90))
for i,im in enumerate([src,clean,decoded]): sheet.paste(gray(im),(0,i*H))
sheet.save(out/"A_PRODUCTION27_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=96)
gray(decoded_raw).save(out/"A_PRODUCTION27_FINAL_RAW_GRAY.jpg",quality=96)

contacts=[]
for row in rows:
    ob=row["original_bbox"]; m=16
    box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
    ims=[gray(z.crop(box)) for z in [src,clean,decoded]]
    h=max(i.height for i in ims)+24; w=sum(i.width for i in ims)+16
    ri=Image.new("RGB",(w,h),(230,230,230)); xx=0
    for im in ims: ri.paste(im,(xx,24)); xx+=im.width+8
    ImageDraw.Draw(ri).text((3,3),f"idx{row['idx']} {row['source']} -> {row['korean']}  SOURCE | CLEAN | FINAL",fill=(0,0,0))
    contacts.append(ri)
cw=max(i.width for i in contacts); ch=sum(i.height for i in contacts)+4*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),(230,230,230)); yy=0
for im in contacts: cs.paste(im,(0,yy)); yy+=im.height+4
cs.save(out/"A_PRODUCTION27_ROW_CONTACT.jpg",quality=96)

status=(cleanrep["status"]=="PASS" and finalrep["status"]=="PASS" and unchanged==0 and all_bbox and all_size and all_positive
        and overlap==0 and touch==0 and outside==0 and alpha_out==0 and prot==0 and source_residue==0)
report={
 "schema_version":1,"role":"A","run":run,"index":241,"asset":asset_rel,"worker":"github-actions",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,
  "sha256":SOURCE_SHA,"path":"Release/spr_sprani_sumo_loading_Exst/E1639D2E_256x64.dds",
  "classification":"authoritative high-resolution source; DDS header 1024x256 RGBA32"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pixel_raw_mode":RAWMODE,"pitch":pitch,"depth":depth,"mipmaps":mips,
  "bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
 "translation":{"physical_occurrences":2,"rows":[{"source":r["source"],"korean":r["korean"],"region_idx":r["idx"]} for r in rows]},
 "rows":rows,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "machine_checks":{"source_mask_pixels_unchanged_in_clean":unchanged,"localized_overlap_pixels":overlap,
  "localized_touch_pixels":touch,"changed_pixels_outside_source_bboxes":outside,"alpha_changed_pixels_outside_source_bboxes":alpha_out,
  "protected_visible_pixels_changed":prot,"source_residue_visible_pixels":source_residue},
 "all_2_bbox_pass":all_bbox,"all_2_size_ceiling_pass":all_size,"all_2_positive_margin":all_positive,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_PRODUCTION27_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status else "A_PRODUCTION27_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION27_E1639D2E_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"E1639D2E","index":241,"source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,
 "source_dimensions":[W,H],"format":"RGBA32","bbox_pass":"2/2" if all_bbox else "FAIL","size_ceiling":"2/2" if all_size else "FAIL",
 "positive_margin":"2/2" if all_positive else "FAIL","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "source_mask_pixels_unchanged_in_clean":unchanged,"localized_overlap_pixels":overlap,"localized_touch_pixels":touch,
 "changed_pixels_outside_source_bboxes":outside,"alpha_changed_pixels_outside_source_bboxes":alpha_out,
 "protected_visible_pixels_changed":prot,"source_residue_visible_pixels":source_residue,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261005-A-PRODUCTION27/A_PRODUCTION27_E1639D2E_REPORT.json"}
(wr/"A_PRODUCTION27_E1639D2E.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status: raise SystemExit(2)
