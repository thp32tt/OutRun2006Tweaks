#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request, statistics, traceback
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION57"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds"
index=140
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="2da84d800f3df0606df148c353f25c2f25a47573"
ATLAS_BLOB_SHA1="7829c90426d563960440dd70b9b7ae74b3b76c0d"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
work=Path("/tmp/outrun_B57"); work.mkdir(parents=True,exist_ok=True)
source=work/"31C58963_HD.dds"
atlas=work/"4x_31C58963_512x256_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_31C58963_512x256_atlas.json",atlas)

def git_blob_sha1(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha256b(b): return hashlib.sha256(b).hexdigest()
def count(m): return sum(m.histogram()[1:])
def binmask(m): return m.point(lambda v:255 if v else 0)
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return binmask(m)
def median_rgba(vals):
    return tuple(int(round(statistics.median([v[i] for v in vals]))) for i in range(4))
def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=source.read_bytes(); ab=atlas.read_bytes()
if git_blob_sha1(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source blob",git_blob_sha1(sb)))
if git_blob_sha1(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas blob",git_blob_sha1(ab)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(2048,1024,8192,1) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,pitch,depth,mips,len(sb),pf))
masks=(pf[4],pf[5],pf[6])
if masks==(0xff,0xff00,0xff0000): RAWMODE="RGBA"
elif masks==(0xff0000,0xff00,0xff): RAWMODE="BGRA"
else: raise RuntimeError(("raw mode",masks))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj=json.loads(ab.decode("utf-8")); regions={r["idx"]:r for r in aj["regions"]}
expected_cells={0:[0,864,1760,160],1:[0,704,1760,160],2:[0,544,1760,160],3:[0,384,1760,160],4:[0,308,744,76]}
if {k:regions[k]["rect"] for k in regions}!=expected_cells: raise RuntimeError(("atlas drift",regions))

# B56 controller-readable binding established exact region semantics:
# 0 SELECT STAGE, 1 SELECT RACE, 2 SELECT MODE, 3 SHOWROOM,
# 4 PRESS [Enter-key icon] KEY. The icon is preserve-original protected artwork.
semantics=[
 (0,"SELECT STAGE","스테이지 선택"),
 (1,"SELECT RACE","레이스 선택"),
 (2,"SELECT MODE","모드 선택"),
 (3,"SHOWROOM","쇼룸"),
]

source_text_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
source_rows=[]
style_white=[]
for idx,en,ko in semantics:
    x,y,cw,ch=regions[idx]["rect"]
    cell=src.crop((x,y,x+cw,y+ch)); a=cell.getchannel("A")
    bb=a.getbbox()
    if not bb: raise RuntimeError(("empty source cell",idx))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    source_text_mask.paste(ImageChops.lighter(source_text_mask.crop((x,y,x+cw,y+ch)),binmask(a)),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    pix=cell.load()
    for yy in range(ch):
        for xx in range(cw):
            r,g,b,aa=pix[xx,yy]
            if aa and min(r,g,b)>=160 and max(r,g,b)-min(r,g,b)<=55:
                style_white.append((r,g,b,aa))
    source_rows.append({"key":f"region_{idx}","region_idx":idx,"source":en,"korean":ko,
                        "cell":[x,y,cw,ch],"original_bbox":ob})

# Region 4 is a compound sprite. B56 readable evidence gives three physical groups:
# PRESS | protected Enter-key icon | KEY. Use only source alpha inside the two word
# x-ranges as source text masks. The center icon remains byte/pixel preserved.
x,y,cw,ch=regions[4]["rect"]
cell=src.crop((x,y,x+cw,y+ch))
left_range=(150,0,374,ch)
right_range=(462,0,620,ch)
word_specs=[]
for key,en,ko,rr in [
    ("press_word","PRESS","누르세요",left_range),
    ("key_word","KEY","키",right_range),
]:
    rx0,ry0,rx1,ry1=rr
    crop=cell.crop(rr); a=binmask(crop.getchannel("A")); bb=a.getbbox()
    if not bb: raise RuntimeError(("compound word missing",key))
    ob=[x+rx0+bb[0],y+ry0+bb[1],x+rx0+bb[2],y+ry0+bb[3]]
    wm=Image.new("L",(W,H),0); wm.paste(a,(x+rx0,y+ry0))
    source_text_mask=ImageChops.lighter(source_text_mask,wm)
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    word_specs.append({"key":key,"region_idx":4,"source":en,"korean":ko,"original_bbox":ob,
                       "cell":[x+rx0,y+ry0,rx1-rx0,ry1-ry0]})

# Confirm the protected icon lives strictly between the two source word bboxes.
src_visible=binmask(src.getchannel("A"))
protected=ImageChops.multiply(src_visible,ImageOps.invert(allowed))
icon_window=Image.new("L",(W,H),0); ImageDraw.Draw(icon_window).rectangle((374,y,461,y+ch-1),fill=255)
icon_pixels=count(ImageChops.multiply(src_visible,icon_window))
if icon_pixels<1000: raise RuntimeError(("protected icon evidence too small",icon_pixels))

# Source style for compound text.
yellow=[]; dark=[]
cp=cell.load()
for yy in range(ch):
    for xx in list(range(left_range[0],left_range[2]))+list(range(right_range[0],right_range[2])):
        if xx<0 or xx>=cw: continue
        r,g,b,aa=cp[xx,yy]
        if not aa: continue
        if r>=170 and g>=90 and b<=100: yellow.append((r,g,b,aa))
        if max(r,g,b)<=70: dark.append((r,g,b,aa))
if len(yellow)<100 or len(dark)<100: raise RuntimeError(("compound style samples",len(yellow),len(dark)))
WHITE=median_rgba(style_white) if style_white else (255,255,255,255)
YELLOW=median_rgba(yellow); DARK=median_rgba(dark)

# Clean exact glyph/effect footprints only; the sprite background is transparent.
clean=src.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)
clean_protected=ImageChops.multiply(src_visible,ImageOps.invert(source_text_mask))
sp=out/"31C_HD_SOURCE_READABLE.png"; cpout=out/"31C_HD_CLEAN_PLATE.png"
smp=out/"31C_SOURCE_TEXT_MASK.png"; ap=out/"31C_ALLOWED_BBOX_MASK.png"; pp=out/"31C_PROTECTED_VISIBLE_MASK.png"
src.save(sp); clean.save(cpout); source_text_mask.save(smp); allowed.save(ap); protected.save(pp)
clean_protected.save(out/"31C_CLEAN_PROTECTED_VISIBLE_MASK.png")
subprocess.run(["python3",str(validator),str(sp),str(cpout),str(smp),"--protected-mask",
                str(out/"31C_CLEAN_PROTECTED_VISIBLE_MASK.png"),"--report",str(out/"B57_CLEAN_VALIDATION.json")],
               check=True)
cleanrep=json.loads((out/"B57_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))
source_unchanged=count(ImageChops.multiply(source_text_mask,ImageOps.invert(dmask(src,clean))))
if source_unchanged: raise RuntimeError(("source residue in clean",source_unchanged))

def resolve_font():
    def pick(patterns):
        for pat in patterns:
            try: spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
            except Exception: spec=""
            if "|" in spec:
                fp,idx=spec.rsplit("|",1)
                if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
                    return fp,int(idx or 0),pat
        return None
    got=pick(["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"])
    if got: return got
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    got=pick(["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"])
    if not got: raise RuntimeError("Noto CJK unavailable")
    return got
FONT,FONT_INDEX,FONT_PATTERN=resolve_font()

def render_plain(text,ob):
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    for fs in range(min(120,int(ah*1.15)),20,-1):
        font=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        d=ImageDraw.Draw(Image.new("L",(8,8),0)); tb=d.textbbox((0,0),text,font=font)
        pad=4
        lay=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
        ImageDraw.Draw(lay).text((pad-tb[0],pad-tb[1]),text,font=font,fill=WHITE)
        bb=lay.getchannel("A").getbbox()
        if not bb: continue
        lay=lay.crop(bb)
        if lay.width<=aw-4 and lay.height<=ah-4:
            return lay,(ob[0]+2,ob[1]+(ah-lay.height)//2),fs,0
    raise RuntimeError(("plain fit",text,ob))

# Estimate the yellow source outline width from alpha-vs-yellow-fill margins.
stroke_samples=[]
for w in word_specs:
    ob=w["original_bbox"]; crop=src.crop(tuple(ob)); a=crop.getchannel("A").getbbox()
    ym=Image.new("L",crop.size,0); yp=ym.load(); pix=crop.load()
    for yy in range(crop.height):
        for xx in range(crop.width):
            r,g,b,aa=pix[xx,yy]
            if aa and r>=170 and g>=90 and b<=100: yp[xx,yy]=255
    yb=ym.getbbox()
    if a and yb:
        stroke_samples += [max(1,yb[0]-a[0]),max(1,a[2]-yb[2]),max(1,yb[1]-a[1]),max(1,a[3]-yb[3])]
stroke=max(2,min(8,int(round(statistics.median(stroke_samples or [4])))))

def render_yellow(text,ob):
    aw,ah=ob[2]-ob[0],ob[3]-ob[1]
    for fs in range(min(84,int(ah*1.1)),16,-1):
        font=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        d=ImageDraw.Draw(Image.new("L",(8,8),0)); tb=d.textbbox((0,0),text,font=font,stroke_width=stroke)
        pad=stroke+4
        lay=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
        ImageDraw.Draw(lay).text((pad-tb[0],pad-tb[1]),text,font=font,fill=YELLOW,
                                 stroke_width=stroke,stroke_fill=DARK)
        bb=lay.getchannel("A").getbbox()
        if not bb: continue
        lay=lay.crop(bb)
        if lay.width<=aw-4 and lay.height<=ah-4:
            return lay,(ob[0]+(aw-lay.width)//2,ob[1]+(ah-lay.height)//2),fs,stroke
    raise RuntimeError(("yellow fit",text,ob))

final=clean.copy(); target_masks=[]; rows=[]
for spec in source_rows+word_specs:
    ob=spec["original_bbox"]
    if spec["region_idx"]==4: lay,pos,fs,sw=render_yellow(spec["korean"],ob)
    else: lay,pos,fs,sw=render_plain(spec["korean"],ob)
    final.alpha_composite(lay,pos)
    lm=Image.new("L",(W,H),0); lm.paste(binmask(lay.getchannel("A")),pos)
    lb=list(lm.getbbox() or ())
    if len(lb)!=4: raise RuntimeError(("missing localized bbox",spec["key"]))
    contain=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
    sizeok=(lb[2]-lb[0])<=(ob[2]-ob[0]) and (lb[3]-lb[1])<=(ob[3]-ob[1])
    positive=lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]
    if not(contain and sizeok and positive): raise RuntimeError(("bbox",spec["key"],ob,lb))
    if count(ImageChops.multiply(lm,protected)): raise RuntimeError(("localized overlaps protected",spec["key"]))
    target_masks.append((spec["key"],lm))
    rows.append({**spec,"localized_bbox":lb,
      "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
      "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
      "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font_file":Path(FONT).name,"font_face_index":FONT_INDEX,"font_pattern":FONT_PATTERN,
      "font_size":fs,"stroke_width":sw,
      "rework_status":"B57_NEW_EXACT_HD_CANDIDATE"})

# Zero overlap/touch among localized labels and positive separation from preserved icon/artwork.
overlap=0; touch=[]
for i in range(len(target_masks)):
    for j in range(i+1,len(target_masks)):
        a=target_masks[i][1]; b=target_masks[j][1]
        ov=count(ImageChops.multiply(a,b))
        near=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
        overlap+=ov
        if ov or near: touch.append([target_masks[i][0],target_masks[j][0],ov,near])
for key,lm in target_masks:
    nearprot=count(ImageChops.multiply(lm.filter(ImageFilter.MaxFilter(3)),protected))
    # Only enforce 1px protected separation for the compound PRESS/KEY row;
    # other row cells intentionally sit near their own source-cell bounds but no protected art exists there.
    if key in ("press_word","key_word") and nearprot:
        raise RuntimeError(("compound target touches protected icon/art",key,nearprot))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",RAWMODE)
candidate.write_bytes(payload); cand_sha=sha256b(payload)
if payload[:128]!=sb[:128]: raise RuntimeError("header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),payload[128:],"raw",RAWMODE)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox(): raise RuntimeError("roundtrip mismatch")
fp=out/"31C_HD_FINAL_DECODED_READABLE.png"; decoded.save(fp)

subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),
                "--report",str(out/"B57_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B57_FINAL_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final validator",finalrep))

diff=dmask(src,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_out=count(ImageChops.multiply(binmask(ImageChops.difference(src.getchannel("A"),decoded.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
if outside or alpha_out or prot or overlap or touch: raise RuntimeError(("final gates",outside,alpha_out,prot,overlap,touch))

# Evidence
target_union=Image.new("L",(W,H),0)
for _,m in target_masks: target_union=ImageChops.lighter(target_union,m)
target_union.save(out/"31C_TARGET_TEXT_MASK.png")
cards=[]
for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",decoded)]:
    z=comp(im).resize((1024,512),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(1024,540),"white"); c.paste(z,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); cards.append(c)
sheet=Image.new("RGB",(1024,1620),"white")
for i,c in enumerate(cards): sheet.paste(c,(0,i*540))
sheet.save(out/"B57_31C_SOURCE_CLEAN_FINAL.jpg",quality=96)

contacts=[]
for r in rows:
    ob=r["original_bbox"]; p=12
    cr=(max(0,ob[0]-p),max(0,ob[1]-p),min(W,ob[2]+p),min(H,ob[3]+p))
    ims=[comp(z).crop(cr) for z in (src,clean,decoded)]
    scale=2
    ims=[z.resize((z.width*scale,z.height*scale),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+28),"white")
    xx=0
    for z in ims: c.paste(z,(xx,28)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["source"]} -> {r["korean"]}',fill="black")
    contacts.append(c)
rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white")
yy=0
for c in contacts: rs.paste(c,(0,yy)); yy+=c.height+4
rs.save(out/"B57_31C_ROW_CONTACT_2X.jpg",quality=96)

rawsheet=Image.new("RGB",(1024,1080),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",decoded_raw)]):
    z=comp(im).resize((1024,512),Image.Resampling.LANCZOS)
    rawsheet.paste(z,(0,i*540+28)); ImageDraw.Draw(rawsheet).text((5,i*540+5),label,fill="black")
rawsheet.save(out/"B57_31C_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"B","run":run,"index":index,"asset":asset,
 "readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,
   "sha256":sha256b(sb),"path":"Release/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds"},
 "source_semantic_correction":{"prior_transcription":"PRESS START","canonical_source_visual":"PRESS [Enter-key icon] KEY",
   "localized_physical_words":{"PRESS":"누르세요","KEY":"키"},"preserved_icon":"Enter-key icon"},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"mipmaps":mips,"bytes":len(sb),
   "header_128_exact":True,"raw_orientation":"mirror_y"},
 "source_style":{"plain_white_fill_rgba":WHITE,"compound_yellow_fill_rgba":YELLOW,
   "compound_dark_outline_rgba":DARK,"compound_stroke_width":stroke},
 "rows":rows,"protected_enter_icon_pixels":icon_pixels,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "source_mask_pixels_unchanged_in_clean":source_unchanged,
 "localized_overlap_pixels":overlap,"localized_touch_pairs":touch,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_source_bboxes":outside,
   "alpha_changed_pixels_outside_source_bboxes":alpha_out,"protected_visible_pixels_changed":prot},
 "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "RUNTIME_VALIDATION":"UNTESTED",
 "status":"B_PRODUCTION57_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B57_31C_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"31C58963","index":index,"source_sha256":sha256b(sb),"candidate_sha256":cand_sha,
 "bbox_size_positive_margin":"6/6","clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "source_mask_residue":source_unchanged,"outside":outside,"alpha_outside":alpha_out,"protected_changed":prot,
 "overlap":overlap,"touch_pairs":len(touch),"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_B/20261005-B-PRODUCTION57/B57_31C_REPORT.json"}
(wr/"B57_31C58963.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
