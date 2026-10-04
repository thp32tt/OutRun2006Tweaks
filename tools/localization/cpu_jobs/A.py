#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request, shutil, statistics, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-PRODUCTION17"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

work=Path("/tmp/outrun_A_prod17")
work.mkdir(parents=True,exist_ok=True)
source=work/"4F68708E_HD.dds"
atlas=work/"4x_4F68708E_512x64_atlas.json"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="eb8c2ddacf4075ff2c7c1dd7a025ca791008fbc8"
ATLAS_BLOB_SHA1="bb0c1f6cace28337dbfba90bac149ef2a14681a7"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_selector_cvt_Exst/4x_4F68708E_512x64_atlas.json",atlas)

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git_blob_sha1(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()
def count(mask): return sum(mask.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split()
    m=bands[0]
    for z in bands[1:]:
        m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def balpha(im): return im.getchannel("A").point(lambda v:255 if v else 0)
def median_rgba(vals):
    return tuple(int(round(statistics.median([v[i] for v in vals]))) for i in range(4))

sb=source.read_bytes()
if git_blob_sha1(sb)!=SOURCE_BLOB_SHA1:
    raise RuntimeError(("source git blob mismatch",git_blob_sha1(sb),SOURCE_BLOB_SHA1))
ab=atlas.read_bytes()
if git_blob_sha1(ab)!=ATLAS_BLOB_SHA1:
    raise RuntimeError(("atlas git blob mismatch",git_blob_sha1(ab),ATLAS_BLOB_SHA1))
SOURCE_SHA=hashlib.sha256(sb).hexdigest()
if sb[:4]!=b"DDS " or sb[84:88]!=b"DXT5":
    raise RuntimeError(("not DXT5",sb[:4],sb[84:88]))
H,W=struct.unpack_from("<2I",sb,12)
if (W,H)!=(2048,256) or len(sb)!=524416:
    raise RuntimeError(("structure",W,H,len(sb)))

raw_source=Image.open(source).convert("RGBA")
source_readable=raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj=json.loads(atlas.read_text(encoding="utf-8"))
if aj.get("regions_count")!=1 or aj["regions"][0]["rect"]!=[0,0,2048,256]:
    raise RuntimeError(("atlas drift",aj.get("regions_count"),aj["regions"][0]["rect"]))

pix=source_readable.load()
alpha=source_readable.getchannel("A")
panel_bbox=alpha.getbbox()
if not panel_bbox:
    raise RuntimeError("empty source")

# White/gray source glyph seed; the dark navy plate is excluded.
seed=Image.new("L",(W,H),0); sp=seed.load()
for y in range(panel_bbox[1],panel_bbox[3]):
    for x in range(panel_bbox[0],panel_bbox[2]):
        r,g,b,a=pix[x,y]
        if a>32 and min(r,g,b)>=105 and (max(r,g,b)-min(r,g,b))<=85:
            sp[x,y]=255
seed_bbox=seed.getbbox()
if not seed_bbox:
    raise RuntimeError("source text bright seed missing")

active_rows=[]
for y in range(seed_bbox[1],seed_bbox[3]):
    if seed.crop((seed_bbox[0],y,seed_bbox[2],y+1)).getbbox():
        active_rows.append(y)
if len(active_rows)<10:
    raise RuntimeError(("too few text rows",len(active_rows)))
gaps=[(active_rows[i+1]-active_rows[i],active_rows[i],active_rows[i+1]) for i in range(len(active_rows)-1)]
gap,gy1,gy2=max(gaps)
if gap<8:
    raise RuntimeError(("two-line split not proven",gap,gy1,gy2))
split=(gy1+gy2)//2

# Estimate the exact plate background per row from both side margins and linearly
# interpolate across x. This removes only the source glyph/effect pixels.
px1,py1,px2,py2=panel_bbox
pw=px2-px1
strip=max(24,min(160,pw//8))
bg_lr={}
for y in range(py1,py2):
    left=[]; right=[]
    for x in range(px1,min(px2,px1+strip)):
        v=pix[x,y]
        if v[3]>0 and not sp[x,y]: left.append(v)
    for x in range(max(px1,px2-strip),px2):
        v=pix[x,y]
        if v[3]>0 and not sp[x,y]: right.append(v)
    allv=left+right
    if len(allv)<8:
        # nearest usable neighboring row will be filled later
        continue
    bg_lr[y]=(median_rgba(left if left else allv),median_rgba(right if right else allv))
if not bg_lr:
    raise RuntimeError("background samples missing")
ys=sorted(bg_lr)
for y in range(py1,py2):
    if y in bg_lr: continue
    nearest=min(ys,key=lambda yy:abs(yy-y))
    bg_lr[y]=bg_lr[nearest]

def expected_bg(x,y):
    l,r=bg_lr[y]
    t=0.5 if pw<=1 else max(0.0,min(1.0,(x-px1)/(pw-1)))
    return tuple(int(round(l[i]*(1-t)+r[i]*t)) for i in range(4))

near=seed.filter(ImageFilter.MaxFilter(21))
np=near.load()
effect=Image.new("L",(W,H),0); ep=effect.load()
env_y1=max(py1,seed_bbox[1]-12); env_y2=min(py2,seed_bbox[3]+12)
for y in range(env_y1,env_y2):
    for x in range(px1,px2):
        if not np[x,y]:
            continue
        v=pix[x,y]; e=expected_bg(x,y)
        dist=sum(abs(v[i]-e[i]) for i in range(4))
        if dist>=18 or sp[x,y]:
            ep[x,y]=255

def bbox_half(y1,y2):
    bb=effect.crop((px1,y1,px2,y2)).getbbox()
    if not bb: return None
    return [px1+bb[0],y1+bb[1],px1+bb[2],y1+bb[3]]

line1=bbox_half(env_y1,split)
line2=bbox_half(split,env_y2)
if not line1 or not line2:
    raise RuntimeError(("line effect bbox missing",line1,line2))
if line1[3]>=line2[1]:
    raise RuntimeError(("line effects overlap",line1,line2))
source_bboxes=[line1,line2]

# Exact DXT5 block splice is safe only if the exact source effect bboxes align to 4x4 blocks.
block_aligned=all(v%4==0 for box in source_bboxes for v in box)
if not block_aligned:
    report={
      "schema_version":1,"role":"A","run":run,"index":99,"asset":asset_rel,
      "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA,
        "path":"Release/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds","classification":"authoritative HD source; DDS 2048x256 DXT5"},
      "source_effect_bboxes":source_bboxes,
      "status":"A_PRODUCTION17_FAIL_CLOSED_DXT5_EXACT_BBOX_NOT_BLOCK_ALIGNED",
      "runtime_validation":"UNTESTED"
    }
    (out/"A_PRODUCTION17_4F68708E_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (wr/"A_PRODUCTION17_4F68708E.json").write_text(json.dumps({"run":run,"asset":"4F68708E","index":99,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261005-A-PRODUCTION17/A_PRODUCTION17_4F68708E_REPORT.json"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(3)

source_text_mask=effect
allowed=Image.new("L",(W,H),0); ad=ImageDraw.Draw(allowed)
for b in source_bboxes:
    ad.rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=255)
source_visible=balpha(source_readable)
protected_visible=ImageChops.multiply(source_visible,ImageOps.invert(allowed))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))

clean=source_readable.copy(); cp=clean.load()
for y in range(H):
    for x in range(W):
        if ep[x,y]:
            cp[x,y]=expected_bg(x,y)

source_png=out/"4F68708E_HD_SOURCE_READABLE.png"
clean_png=out/"4F68708E_HD_CLEAN_PLATE.png"
mask_png=out/"4F68708E_HD_SOURCE_TEXT_MASK.png"
allowed_png=out/"4F68708E_HD_ALLOWED_SOURCE_BBOX_MASK.png"
protected_png=out/"4F68708E_HD_PROTECTED_VISIBLE_MASK.png"
clean_protected_png=out/"4F68708E_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"
source_readable.save(source_png); clean.save(clean_png); source_text_mask.save(mask_png); allowed.save(allowed_png); protected_visible.save(protected_png); clean_protected.save(clean_protected_png)

subprocess.run([
 "python3",str(validator),str(source_png),str(clean_png),str(mask_png),
 "--protected-mask",str(clean_protected_png),
 "--report",str(out/"A_PRODUCTION17_CLEAN_PLATE_VALIDATION.json")
],check=True)
clean_rep=json.loads((out/"A_PRODUCTION17_CLEAN_PLATE_VALIDATION.json").read_text(encoding="utf-8"))
if clean_rep["status"]!="PASS":
    raise RuntimeError(("clean validator",clean_rep))
source_mask_unchanged=count(ImageChops.multiply(source_text_mask,ImageOps.invert(dmask(source_readable,clean))))
if source_mask_unchanged!=0:
    raise RuntimeError(("source effect unchanged in clean",source_mask_unchanged))

def resolve_font():
    pats=["Noto Sans CJK KR:style=Medium","Noto Sans CJK KR:style=Regular","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]
    for pat in pats:
        try: fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
            return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    for pat in pats:
        fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        if fp and Path(fp).exists(): return fp
    raise RuntimeError("Noto CJK Korean unavailable")
FONT=resolve_font()

# Source fill median from bright seed.
seed_vals=[]
for y in range(seed_bbox[1],seed_bbox[3]):
    for x in range(seed_bbox[0],seed_bbox[2]):
        if sp[x,y]: seed_vals.append(pix[x,y])
fill_color=median_rgba(seed_vals)

# Source has a subtle dark lower-right effect; infer a dark effect color from pixels
# inside source effect that are darker than the expected plate background.
dark_vals=[]
for y in range(env_y1,env_y2):
    for x in range(px1,px2):
        if not ep[x,y] or sp[x,y]: continue
        v=pix[x,y]; e=expected_bg(x,y)
        lv=v[0]+v[1]+v[2]; le=e[0]+e[1]+e[2]
        if lv+12<le: dark_vals.append(v)
shadow_color=median_rgba(dark_vals) if dark_vals else (0,0,0,150)
shadow_enabled=len(dark_vals)>=20

def shear_mask(m,shear):
    extra=max(6,int(math.ceil(abs(shear)*m.height))+8)
    canvas=Image.new("L",(m.width+extra*2,m.height),0)
    canvas.paste(m,(extra,0))
    coeff=(1,-shear,shear*canvas.height,0,1,0)
    z=canvas.transform(canvas.size,Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC)
    bb=z.getbbox()
    return z.crop(bb) if bb else z

def build_line(text,fs):
    font=ImageFont.truetype(FONT,fs)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=font,stroke_width=0)
    pad=max(8,fs//6)
    m=Image.new("L",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),0)
    ImageDraw.Draw(m).text((pad-tb[0],pad-tb[1]),text,font=font,fill=255)
    bb=m.getbbox(); m=m.crop(bb)
    m=shear_mask(m,0.22)
    dx=max(2,round(fs*0.045)); dy=max(2,round(fs*0.045))
    extra_x=dx+4 if shadow_enabled else 2
    extra_y=dy+4 if shadow_enabled else 2
    layer=Image.new("RGBA",(m.width+extra_x,m.height+extra_y),(0,0,0,0))
    if shadow_enabled:
        sh=Image.new("RGBA",layer.size,(shadow_color[0],shadow_color[1],shadow_color[2],shadow_color[3]))
        sm=Image.new("L",layer.size,0); sm.paste(m,(dx,dy))
        layer.paste(sh,(0,0),sm)
    fill=Image.new("RGBA",layer.size,fill_color)
    fm=Image.new("L",layer.size,0); fm.paste(m,(0,0))
    layer.paste(fill,(0,0),fm)
    bb=layer.getchannel("A").getbbox()
    return layer.crop(bb),dx,dy

texts=["고스트 카와 달리며","코스 기록에 도전하세요!"]
max_h=min(b[3]-b[1] for b in source_bboxes)
chosen=None
for fs in range(max(18,int(max_h*1.25)),15,-1):
    built=[build_line(t,fs) for t in texts]
    ok=True
    for (layer,dx,dy),ob in zip(built,source_bboxes):
        if layer.width>=(ob[2]-ob[0])-4 or layer.height>=(ob[3]-ob[1])-4:
            ok=False; break
    if ok:
        chosen=(fs,built); break
if chosen is None:
    raise RuntimeError(("Korean fit failed",source_bboxes))
font_size,built=chosen

final=clean.copy()
pre_rows=[]
intended_masks=[]
for key,src_txt,ko_txt,ob,built_line in zip(
    ["line1","line2"],
    ["Drive against the Ghost Car","and challenge for the course record!!"],
    texts,source_bboxes,built):
    layer,dx,dy=built_line
    bw,bh=ob[2]-ob[0],ob[3]-ob[1]
    tx=ob[0]+(bw-layer.width)//2
    ty=ob[1]+(bh-layer.height)//2
    if tx<=ob[0]: tx=ob[0]+2
    if ty<=ob[1]: ty=ob[1]+2
    if tx+layer.width>=ob[2]: tx=ob[2]-layer.width-2
    if ty+layer.height>=ob[3]: ty=ob[3]-layer.height-2
    final.alpha_composite(layer,(tx,ty))
    lm=Image.new("L",(W,H),0); lm.paste(layer.getchannel("A").point(lambda v:255 if v else 0),(tx,ty))
    intended_masks.append((key,lm))
    pre_rows.append({
      "key":key,"source":src_txt,"korean":ko_txt,"original_bbox":ob,
      "preencode_bbox":[tx,ty,tx+layer.width,ty+layer.height],
      "font":"Noto Sans CJK KR Medium/Regular","font_size":font_size,
      "style":"shared two-line source family: white/gray italic sans + subtle dark lower-right effect",
      "shear":0.22,"shadow_enabled":shadow_enabled,"shadow_offset":[dx,dy]
    })

# DXT5 encode the full raw-oriented frame, then splice only exact source-bbox blocks.
exe=shutil.which("convert") or shutil.which("magick")
if not exe:
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","imagemagick"],check=True)
    exe=shutil.which("convert") or shutil.which("magick")
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
png=work/"raw_final.png"; encp=work/"encoded_full.dds"
raw_final.save(png)
cmd=[exe]+(["convert"] if Path(exe).name=="magick" else [])+[str(png),"-define","dds:compression=dxt5","-define","dds:mipmaps=0",str(encp)]
subprocess.run(cmd,check=True)
enc=encp.read_bytes()
if len(enc)!=len(sb) or enc[:4]!=b"DDS " or enc[84:88]!=b"DXT5":
    raise RuntimeError(("DXT5 encode structure",len(enc),enc[:4],enc[84:88]))

outb=bytearray(sb)
bw=W//4
touched=set()
for ob in source_bboxes:
    rx1,ry1,rx2,ry2=ob
    raw_y1=H-ry2; raw_y2=H-ry1
    for by in range(raw_y1//4,raw_y2//4):
        for bx in range(rx1//4,rx2//4):
            touched.add((bx,by))
for bx,by in touched:
    p=128+(by*bw+bx)*16
    outb[p:p+16]=enc[p:p+16]
candidate.write_bytes(outb)
CANDIDATE_SHA=sha256(candidate)
if candidate.read_bytes()[:128]!=sb[:128]:
    raise RuntimeError("source DDS header changed")

decoded_raw=Image.open(candidate).convert("RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
decoded_png=out/"4F68708E_HD_FINAL_DECODED_READABLE.png"
decoded.save(decoded_png)

subprocess.run([
 "python3",str(validator),str(source_png),str(decoded_png),str(allowed_png),
 "--protected-mask",str(protected_png),
 "--report",str(out/"A_PRODUCTION17_FINAL_MASK_VALIDATION.json")
],check=True)
final_rep=json.loads((out/"A_PRODUCTION17_FINAL_MASK_VALIDATION.json").read_text(encoding="utf-8"))
if final_rep["status"]!="PASS":
    raise RuntimeError(("final validator",final_rep))

diff=dmask(source_readable,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_delta=ImageChops.difference(source_readable.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(diff,protected_visible))

rows=[]
for pre,(key,lm) in zip(pre_rows,intended_masks):
    ob=pre["original_bbox"]
    bb=lm.getbbox()
    loc=list(bb) if bb else None
    ok=loc is not None and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=loc is not None and loc[2]-loc[0]<=ob[2]-ob[0] and loc[3]-loc[1]<=ob[3]-ob[1]
    positive=loc is not None and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    row=dict(pre)
    row.update({
      "localized_bbox":loc,
      "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
      "localized_width":loc[2]-loc[0] if loc else None,"localized_height":loc[3]-loc[1] if loc else None,
      "delta_left":loc[0]-ob[0] if loc else None,"delta_right":ob[2]-loc[2] if loc else None,
      "delta_top":loc[1]-ob[1] if loc else None,"delta_bottom":ob[3]-loc[3] if loc else None,
      "containment":"PASS" if ok else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
      "positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
      "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
      "raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]] if loc else None,
      "raw_containment":"PASS" if ok else "FAIL",
      "rework_status":"A_PRODUCTION17_NEW_EXACT_HD_CANDIDATE"
    })
    rows.append(row)

label_overlap=count(ImageChops.multiply(intended_masks[0][1],intended_masks[1][1]))
label_touch=count(ImageChops.multiply(intended_masks[0][1].filter(ImageFilter.MaxFilter(3)),intended_masks[1][1]))
all_bbox=all(r["containment"]=="PASS" and r["raw_containment"]=="PASS" for r in rows)
all_size=all(r["size_ceiling"]=="PASS" for r in rows)
all_positive=all(r["positive_margin"]=="PASS" for r in rows)

# Visual evidence.
def gray(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255)); bg.alpha_composite(im); return bg.convert("RGB")
sheet=Image.new("RGB",(W,H*3),(70,70,70))
sheet.paste(gray(source_readable),(0,0)); sheet.paste(gray(clean),(0,H)); sheet.paste(gray(decoded),(0,H*2))
sheet.save(out/"A_PRODUCTION17_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=96)
gray(decoded_raw).save(out/"A_PRODUCTION17_FINAL_RAW_GRAY.jpg",quality=96)

contacts=[]
for r in rows:
    ob=r["original_bbox"]; m=12
    box=(max(0,ob[0]-m),max(0,ob[1]-m),min(W,ob[2]+m),min(H,ob[3]+m))
    a=gray(source_readable.crop(box)); b=gray(decoded.crop(box))
    rowim=Image.new("RGB",(a.width+b.width+12,max(a.height,b.height)+24),(235,235,235))
    rowim.paste(a,(0,24)); rowim.paste(b,(a.width+12,24))
    ImageDraw.Draw(rowim).text((3,2),r["key"]+" SOURCE | FINAL",fill=(0,0,0))
    contacts.append(rowim)
cw=max(x.width for x in contacts); ch=sum(x.height for x in contacts)+4
cs=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for x in contacts: cs.paste(x,(0,yy)); yy+=x.height+4
cs.save(out/"A_PRODUCTION17_LINE_CONTACT_SOURCE_FINAL.jpg",quality=96)

status_ok=(
 clean_rep["status"]=="PASS" and final_rep["status"]=="PASS" and source_mask_unchanged==0
 and all_bbox and all_size and all_positive and label_overlap==0 and label_touch==0
 and outside==0 and alpha_outside==0 and protected_changed==0
)

report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"base_head":os.environ.get("GITHUB_SHA"),
 "index":99,"asset":asset_rel,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,
   "sha256":SOURCE_SHA,"path":"Release/spr_sprani_selector_cvt_Exst/4F68708E_512x64.dds",
   "classification":"authoritative high-resolution source; DDS header 2048x256 DXT5"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"compression":"DXT5","bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y","source_effect_bboxes_block_aligned":block_aligned},
 "translation":{"source":"Drive against the Ghost Car and challenge for the course record!!",
   "korean":"고스트 카와 달리며 코스 기록에 도전하세요!",
   "line_mapping":[{"source":"Drive against the Ghost Car","korean":texts[0]},{"source":"and challenge for the course record!!","korean":texts[1]}]},
 "source_panel_bbox":panel_bbox,"source_seed_bbox":seed_bbox,"source_effect_bboxes":source_bboxes,
 "source_style":{"fill_median":fill_color,"shadow_enabled":shadow_enabled,"shadow_median":shadow_color,"shared_line_shear":0.22,"shared_font_size":font_size},
 "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,
 "source_mask_pixels_unchanged_in_clean":source_mask_unchanged,
 "rows":rows,"all_2_readable_and_raw_bbox_pass":all_bbox,"all_2_size_ceiling_pass":all_size,"all_2_positive_margin":all_positive,
 "localized_label_overlap_pixels":label_overlap,"localized_label_touch_pixels":label_touch,
 "dxt5_touched_blocks":len(touched),
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_source_bboxes":outside,
   "alpha_changed_pixels_outside_source_bboxes":alpha_outside,"protected_visible_pixels_changed":protected_changed},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_PRODUCTION17_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION17_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION17_4F68708E_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
 "run":run,"asset":"4F68708E","index":99,"source_sha256":SOURCE_SHA,"candidate_sha256":CANDIDATE_SHA,
 "source_dimensions":[W,H],"compression":"DXT5","bbox_pass":"2/2" if all_bbox else "FAIL","size_ceiling":"2/2" if all_size else "FAIL",
 "positive_margin":"2/2" if all_positive else "FAIL","clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],
 "source_mask_pixels_unchanged_in_clean":source_mask_unchanged,"localized_label_overlap_pixels":label_overlap,"localized_label_touch_pixels":label_touch,
 "changed_pixels_outside_source_bboxes":outside,"alpha_changed_pixels_outside_source_bboxes":alpha_outside,"protected_visible_pixels_changed":protected_changed,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261005-A-PRODUCTION17/A_PRODUCTION17_4F68708E_REPORT.json"
}
(wr/"A_PRODUCTION17_4F68708E.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
