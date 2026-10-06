#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
from statistics import median
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A-MANUALQA149-2B0863D6"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker_out=repo/"localization/graphics/worker_results"
worker_out.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

work=Path("/tmp/outrun_A149_q135"); work.mkdir(parents=True,exist_ok=True)
source=work/"2B0863D6_HD.dds"
atlas=work/"4x_2B0863D6_512x64_atlas.json"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BLOB="1875af13ea28e27a4b61f917e43d561e6527106e"
SOURCE_SHA="dafe21ec29ace60273f3ec10a40072446f3f28232b3f9a8acce3897ade1eff06"
EXPECTED_BEFORE="2f3e99f468367e056ee3c6edfdb412b1fe5f10f27387a463472b07aeaa335fbb"
REVIEW_JPG="localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/016_q135_2B0863D6.jpg"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds",source)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_2B0863D6_512x64_atlas.json",atlas)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=SOURCE_SHA: raise RuntimeError(("source SHA",sha(source),SOURCE_SHA))
if not candidate.exists() or sha(candidate)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift before A149",sha(candidate) if candidate.exists() else None,EXPECTED_BEFORE))
prior_bytes=candidate.read_bytes()
sb=source.read_bytes()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,depth,mips)!=(2048,256,8192,1,1): raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000): raise RuntimeError(("pixel format",pf))
if len(sb)!=128+W*H*4: raise RuntimeError(("byte size",len(sb)))

raw_source=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
source_readable=raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
prior_raw=Image.frombytes("RGBA",(W,H),prior_bytes[128:],"raw","RGBA")
prior_readable=prior_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj=json.loads(atlas.read_text(encoding="utf-8"))
regions={r["idx"]:r for r in aj["regions"]}
if len(regions)!=11: raise RuntimeError(("region count",len(regions)))

specs=[
 (0,"professional","PROFESSIONAL","프로","gray"),
 (1,"novice","NOVICE","초급","gray"),
 (2,"outrun","OUTRUN","아웃런","gray"),
 (3,"intermediate_b","INTERMEDIATE B","중급 B","gray"),
 (4,"intermediate_a","INTERMEDIATE A","중급 A","gray"),
 (5,"change_class","CHANGE CLASS","클래스 변경","gray"),
 (6,"class","CLASS","클래스","badge_white"),
 (7,"acceleration","ACCELERATION","가속","gray"),
 (8,"max_speed","MAX SPEED","최고 속도","gray"),
 (9,"handling","HANDLING","핸들링","gray"),
]

def count(mask): return sum(mask.histogram()[1:])
def binary_alpha(im): return im.getchannel("A").point(lambda v:255 if v else 0)
def changed_mask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)

source_text_mask=Image.new("L",(W,H),0)
allowed_bbox=Image.new("L",(W,H),0)
targets=[]

# Region 6 contains a red pill background; other target regions are text-only.
for idx,key,src,kor,style in specs:
    rr=regions[idx]; x,y,w,h=rr["rect"]
    cell=source_readable.crop((x,y,x+w,y+h))
    if idx!=6:
        local_mask=binary_alpha(cell)
    else:
        pix=cell.load()
        obvious=[]
        for yy in range(h):
            for xx in range(w):
                r,g,b,a=pix[xx,yy]
                if a>0 and min(r,g,b)>=105 and max(r,g,b)-min(r,g,b)<=70:
                    obvious.append((xx,yy))
        if not obvious:
            raise RuntimeError("CLASS seed mask missing")
        bx1=max(0,min(q[0] for q in obvious)-4)
        by1=max(0,min(q[1] for q in obvious)-4)
        bx2=min(w,max(q[0] for q in obvious)+5)
        by2=min(h,max(q[1] for q in obvious)+5)
        local_mask=Image.new("L",(w,h),0); mp=local_mask.load()
        # Reconstruct the expected red badge row color from untouched red pixels, then
        # classify every deviating pixel inside the seeded glyph neighborhood as source text.
        # This captures blended antialias fringe without erasing the pill border/background.
        for yy in range(by1,by2):
            reds=[]
            for xx in range(w):
                r,g,b,a=pix[xx,yy]
                seed=(a>0 and min(r,g,b)>=105 and max(r,g,b)-min(r,g,b)<=70)
                if a>0 and not seed and r>120 and r>g*1.35 and r>b*1.25:
                    reds.append((r,g,b,a))
            fill=tuple(int(median([v[k] for v in reds])) for k in range(4)) if reds else (204,55,65,255)
            for xx in range(bx1,bx2):
                r,g,b,a=pix[xx,yy]
                if a<=0:
                    continue
                delta=max(abs(r-fill[0]),abs(g-fill[1]),abs(b-fill[2]),abs(a-fill[3]))
                if delta>6:
                    mp[xx,yy]=255
    bb=local_mask.getbbox()
    if not bb: raise RuntimeError(("empty source mask",idx,key))
    gb=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_text_mask.paste(ImageChops.lighter(source_text_mask.crop((x,y,x+w,y+h)),local_mask),(x,y))
    ImageDraw.Draw(allowed_bbox).rectangle((gb[0],gb[1],gb[2]-1,gb[3]-1),fill=255)
    style_pixels=[]
    if idx!=6:
        cpix=cell.load()
        for yy in range(h):
            for xx in range(w):
                if local_mask.getpixel((xx,yy)):
                    r0,g0,b0,a0=cpix[xx,yy]
                    if a0>=128: style_pixels.append((r0,g0,b0,a0))
    source_core_rgba=tuple(int(median([p[k] for p in style_pixels])) for k in range(4)) if style_pixels else None
    targets.append({"region_idx":idx,"key":key,"source":src,"korean":kor,"style":style,"cell_rect":[x,y,x+w,y+h],"original_bbox":gb,"source_core_rgba":source_core_rgba})

source_visible=binary_alpha(source_readable)
protected_visible=ImageChops.multiply(source_visible,ImageOps.invert(allowed_bbox))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))
clean=source_readable.copy()

# Text-only regions become transparent where source lettering existed.
for t in targets:
    idx=t["region_idx"]; x1,y1,x2,y2=t["cell_rect"]
    if idx==6: continue
    lm=source_text_mask.crop((x1,y1,x2,y2))
    clean.paste(Image.new("RGBA",(x2-x1,y2-y1),(0,0,0,0)),(x1,y1),lm)

# Reconstruct the red CLASS pill under its white source glyphs using row-wise red-background medians.
t6=next(t for t in targets if t["region_idx"]==6)
x1,y1,x2,y2=t6["cell_rect"]; csrc=source_readable.crop((x1,y1,x2,y2)); cmask=source_text_mask.crop((x1,y1,x2,y2))
cpix=csrc.load(); mp=cmask.load(); cout=csrc.copy(); op=cout.load()
for yy in range(y2-y1):
    reds=[]
    for xx in range(x2-x1):
        r,g,b,a=cpix[xx,yy]
        if a>0 and not mp[xx,yy] and r>120 and r>g*1.35 and r>b*1.25:
            reds.append((r,g,b,a))
    if reds:
        fill=tuple(int(median([p[k] for p in reds])) for k in range(4))
    else:
        fill=(204,55,65,255)
    for xx in range(x2-x1):
        if mp[xx,yy]:
            op[xx,yy]=fill
clean.paste(cout,(x1,y1))

source_png=out/"2B0863D6_HD_SOURCE_READABLE.png"
clean_png=out/"2B0863D6_HD_CLEAN_PLATE.png"
source_readable.save(source_png); clean.save(clean_png)
source_text_mask.save(out/"2B0863D6_HD_SOURCE_TEXT_MASK.png")
allowed_bbox.save(out/"2B0863D6_HD_ALLOWED_TEXT_REGION_MASK.png")
protected_visible.save(out/"2B0863D6_HD_PROTECTED_VISIBLE_MASK.png")
clean_protected.save(out/"2B0863D6_HD_CLEAN_PROTECTED_VISIBLE_MASK.png")

subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(out/"2B0863D6_HD_SOURCE_TEXT_MASK.png"),
                "--protected-mask",str(out/"2B0863D6_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"),
                "--report",str(out/"A149_CLEAN_PLATE_VALIDATION.json")],check=True)
clean_rep=json.loads((out/"A149_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"]!="PASS": raise RuntimeError(("clean validator",clean_rep))

def resolve_font():
    pats=["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]
    for pat in pats:
        try: fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    for pat in pats:
        fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        if fp and Path(fp).exists(): return fp
    raise RuntimeError("Noto CJK unavailable")
FONT=resolve_font()

def render_plain(text,color,aw,ah,style):
    for fs in range(max(14,int(ah*1.25)),9,-1):
        font=ImageFont.truetype(FONT,fs)
        stroke=max(1,round(fs*0.025)) if style=="gray" else 0
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        bb=d.textbbox((0,0),text,font=font,stroke_width=stroke)
        pad=stroke+6
        glyph=Image.new("RGBA",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),(0,0,0,0))
        gd=ImageDraw.Draw(glyph)
        gd.text((pad-bb[0],pad-bb[1]),text,font=font,fill=color,stroke_width=stroke,stroke_fill=color)
        gb=glyph.getchannel("A").getbbox()
        if not gb: continue
        glyph=glyph.crop(gb)
        if style=="gray":
            target_w=min(aw-4,max(glyph.width,int(round(glyph.width*1.14))))
            if target_w>glyph.width:
                glyph=glyph.resize((target_w,glyph.height),Image.Resampling.LANCZOS)
                gb2=glyph.getchannel("A").getbbox()
                if gb2: glyph=glyph.crop(gb2)
        if glyph.width>aw-4:
            glyph=glyph.resize((aw-4,glyph.height),Image.Resampling.LANCZOS)
        if glyph.width<=aw-4 and glyph.height<=ah-4:
            return glyph,fs,stroke
    raise RuntimeError(("fit failed",text,aw,ah))

final=clean.copy()
for t in targets:
    ox1,oy1,ox2,oy2=t["original_bbox"]; aw,ah=ox2-ox1,oy2-oy1
    if t["style"]=="badge_white":
        color=(252,247,247,255)
    else:
        sc=t.get("source_core_rgba") or (82,90,92,255)
        # Preserve the exact source gray family instead of the old generic 101/108/110,
        # but keep a fully opaque core; antialias remains in the glyph mask.
        color=(sc[0],sc[1],sc[2],255)
    glyph,fs,stroke=render_plain(t["korean"],color,aw,ah,t["style"])
    tx=ox1+(aw-glyph.width)//2; ty=oy1+(ah-glyph.height)//2
    tx=max(ox1+1,min(tx,ox2-glyph.width-1)); ty=max(oy1+1,min(ty,oy2-glyph.height-1))
    final.alpha_composite(glyph,(tx,ty))
    t["font_size"]=fs; t["stroke_width"]=stroke; t["render_rgba"]=list(color); t["preencode_bbox"]=[tx,ty,tx+glyph.width,ty+glyph.height]

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cb=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(cb); candidate_sha=sha(candidate)
if cb[:128]!=sb[:128]: raise RuntimeError("header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
decoded_png=out/"2B0863D6_HD_FINAL_DECODED_READABLE.png"; decoded.save(decoded_png)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("roundtrip mismatch")

subprocess.run(["python3",str(validator),str(source_png),str(decoded_png),str(out/"2B0863D6_HD_ALLOWED_TEXT_REGION_MASK.png"),
                "--protected-mask",str(out/"2B0863D6_HD_PROTECTED_VISIBLE_MASK.png"),
                "--report",str(out/"A149_FINAL_MASK_VALIDATION.json")],check=True)
final_rep=json.loads((out/"A149_FINAL_MASK_VALIDATION.json").read_text())
if final_rep["status"]!="PASS": raise RuntimeError(("final validator",final_rep))

diff=changed_mask(source_readable,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed_bbox)))
alpha_delta=ImageChops.difference(source_readable.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed_bbox)))
protected_changed=count(ImageChops.multiply(diff,protected_visible))
clean_residue=0
for t in targets:
    ob=t["original_bbox"]
    if t["region_idx"]!=6:
        clean_residue += count(ImageChops.multiply(binary_alpha(clean.crop(tuple(ob))), source_text_mask.crop(tuple(ob))))
    else:
        cc=clean.crop(tuple(ob))
        mm=source_text_mask.crop(tuple(ob))
        cp=cc.load(); mp=mm.load()
        for yy in range(cc.height):
            for xx in range(cc.width):
                if not mp[xx,yy]:
                    continue
                r0,g0,b0,a0=cp[xx,yy]
                if a0>0 and min(r0,g0,b0)>=105 and max(r0,g0,b0)-min(r0,g0,b0)<=70:
                    clean_residue += 1

rows=[]
for t in targets:
    ob=t["original_bbox"]
    if t["region_idx"]==6:
        oldbb=changed_mask(clean.crop(tuple(ob)),prior_readable.crop(tuple(ob))).getbbox()
    else:
        oldbb=prior_readable.crop(tuple(ob)).getchannel("A").getbbox()
    oldloc=[ob[0]+oldbb[0],ob[1]+oldbb[1],ob[0]+oldbb[2],ob[1]+oldbb[3]] if oldbb else None
    if t["region_idx"]==6:
        bb=changed_mask(clean.crop(tuple(ob)),decoded.crop(tuple(ob))).getbbox()
    else:
        bb=decoded.crop(tuple(ob)).getchannel("A").getbbox()
    loc=[ob[0]+bb[0],ob[1]+bb[1],ob[0]+bb[2],ob[1]+bb[3]] if bb else None
    ok=loc is not None and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=loc is not None and loc[2]-loc[0]<=ob[2]-ob[0] and loc[3]-loc[1]<=ob[3]-ob[1]
    positive=loc is not None and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    rows.append({
      "key":t["key"],"region_idx":t["region_idx"],"source":t["source"],"korean":t["korean"],"style":t["style"],
      "original_bbox":ob,"localized_bbox":loc,
      "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
      "localized_width":loc[2]-loc[0] if loc else None,"localized_height":loc[3]-loc[1] if loc else None,
      "delta_left":loc[0]-ob[0] if loc else None,"delta_right":ob[2]-loc[2] if loc else None,
      "delta_top":loc[1]-ob[1] if loc else None,"delta_bottom":ob[3]-loc[3] if loc else None,
      "containment":"PASS" if ok else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
      "positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
      "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
      "raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]] if loc else None,
      "raw_containment":"PASS" if ok else "FAIL","font":"Noto Sans CJK KR Black","font_size":t["font_size"],"stroke_width":t["stroke_width"],
      "source_core_rgba":list(t["source_core_rgba"]) if t.get("source_core_rgba") else None,"render_rgba":t["render_rgba"],
      "prior_localized_bbox":oldloc,"prior_localized_width":oldloc[2]-oldloc[0] if oldloc else None,"prior_localized_height":oldloc[3]-oldloc[1] if oldloc else None,
      "width_gain_px":(loc[2]-loc[0])-(oldloc[2]-oldloc[0]) if loc and oldloc else None,
      "rework_status":"A149_SOURCE_WEIGHT_CONTRAST_REWORK"
    })

all_bbox=all(x["containment"]=="PASS" and x["raw_containment"]=="PASS" for x in rows)
all_size=all(x["size_ceiling"]=="PASS" for x in rows)
all_positive=all(x["positive_margin"]=="PASS" for x in rows)

def gray(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255)); bg.alpha_composite(im); return bg.convert("RGB")
scale=2
full=Image.new("RGB",(W*scale,H*scale*4),(80,80,80))
full.paste(gray(source_readable).resize((W*scale,H*scale),Image.Resampling.NEAREST),(0,0))
full.paste(gray(prior_readable).resize((W*scale,H*scale),Image.Resampling.NEAREST),(0,H*scale))
full.paste(gray(clean).resize((W*scale,H*scale),Image.Resampling.NEAREST),(0,H*scale*2))
full.paste(gray(decoded).resize((W*scale,H*scale),Image.Resampling.NEAREST),(0,H*scale*3))
full.save(out/"A149_SOURCE_C109_CLEAN_FINAL_GRAY.jpg",quality=95)
rawcmp=Image.new("RGB",(W*3,H),(80,80,80))
rawcmp.paste(gray(raw_source),(0,0)); rawcmp.paste(gray(prior_raw),(W,0)); rawcmp.paste(gray(decoded_raw),(W*2,0))
rawcmp.thumbnail((2100,320),Image.Resampling.LANCZOS)
rawcmp.save(out/"A149_SOURCE_C109_FINAL_RAW.jpg",quality=95)

label_font=ImageFont.truetype(FONT,18); contact=[]
for t in targets:
    ob=t["original_bbox"]; m=6
    x1=max(0,ob[0]-m);y1=max(0,ob[1]-m);x2=min(W,ob[2]+m);y2=min(H,ob[3]+m)
    a=gray(source_readable.crop((x1,y1,x2,y2))); b=gray(decoded.crop((x1,y1,x2,y2)))
    p=gray(prior_readable.crop((x1,y1,x2,y2)))
    row=Image.new("RGB",(a.width+p.width+b.width+18,max(a.height,p.height,b.height)+24),(230,230,230))
    row.paste(a,(0,24)); row.paste(p,(a.width+6,24)); row.paste(b,(a.width+p.width+12,24))
    ImageDraw.Draw(row).text((3,2),t["key"]+" SOURCE | C109 | A149",font=label_font,fill=(0,0,0))
    contact.append(row)
cw=max(c.width for c in contact); ch=sum(c.height for c in contact)+4*(len(contact)-1)
sheet=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for c in contact: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"A149_ROW_CONTACT.jpg",quality=95)

status_ok=(clean_rep["status"]=="PASS" and final_rep["status"]=="PASS" and all_bbox and all_size and all_positive and outside==0 and alpha_outside==0 and protected_changed==0 and clean_residue==0)
report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"base_head":os.environ.get("GITHUB_SHA"),
 "index":135,"asset":asset_rel,"trigger":"PRE_INGAME_016_SOURCE_WEIGHT_CONTRAST_FALSE_NEGATIVE","review_jpg":REVIEW_JPG,
 "prior_c_status":"C109_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","prior_candidate_sha256":EXPECTED_BEFORE,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":BLOB,"sha256":SOURCE_SHA,
   "path":"Release/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds","classification":"authoritative high-resolution source; stale filename suffix, DDS header 2048x256 RGBA32"},
 "source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
 "translations":[{"source":s,"korean":k} for _,_,s,k,_ in specs],
 "class_badge_background_reconstruction":"row-wise red-background median inside source white-text mask; badge border/background preserved",
 "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,"protected_visible_pixels_changed":protected_changed,"clean_plate_source_text_residue_pixels":clean_residue},
 "rows":rows,"all_10_readable_and_raw_bbox_pass":all_bbox,"all_10_size_ceiling_pass":all_size,"all_10_positive_margin":all_positive,
 "ordered_generation_gate":{"plate_restoration":"PASS_REBUILT_FROM_CANONICAL_SOURCE","slant_direction":"PASS_SOURCE_UPRIGHT_FAMILY","no_unnecessary_undersizing":"PASS_HEIGHT_NEAR_SOURCE_PLUS_1_14X_WIDTH_REINFORCEMENT","source_weight_effects":"REWORKED_SOURCE_DERIVED_CORE_RGB_PLUS_NATIVE_BLACK_STROKE_PENDING_CONTROLLER","clipping":"PASS_POSITIVE_MARGINS","protected_clearance":"PASS_ZERO_PROTECTED_CHANGE","flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER","immediate_readability":"PENDING_CONTROLLER"},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A149_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A149_WORKER_REWORK_REQUIRED","no_vr_ffb_dx11_dxvk_work":True
}
(out/"A149_2B0863D6_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"2B0863D6","index":135,"trigger":"PRE_INGAME_016_SOURCE_WEIGHT_CONTRAST_FALSE_NEGATIVE","prior_candidate_sha256":EXPECTED_BEFORE,"source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,"source_dimensions":[W,H],"format":"RGBA32","target_occurrences":10,
 "bbox_pass":"10/10" if all_bbox else "FAIL","size_ceiling":"10/10" if all_size else "FAIL","positive_margin":"10/10" if all_positive else "FAIL",
 "clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],"changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,
 "protected_visible_pixels_changed":protected_changed,"clean_plate_source_text_residue_pixels":clean_residue,"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261007-A-MANUALQA149-2B0863D6/A149_2B0863D6_REPORT.json"}
(worker_out/"A149_2B0863D6.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
