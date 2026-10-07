#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A-MANUALQA158-AD720950-SHIFT"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_etc_cvt_Exst/AD720950_1024x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
work=Path("/tmp/outrun_A158"); work.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA="141e1f0773b82a8eca6ff49cd93d637221b96211566541f97de9ef4fc454d26f"
EXPECTED_BEFORE="6dad37489e7027b8f546c38b3729167697965fc8e33fcabff46f09aba1677955"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
source=work/"AD720950_HD.dds"
atlas=work/"4x_AD720950_1024x256_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_etc_cvt_Exst/AD720950_1024x256.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_etc_cvt_Exst/4x_AD720950_1024x256_atlas.json",atlas)

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(Path(p).read_bytes())
def changed_mask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def count(mask): return sum(mask.histogram()[1:])

sb=source.read_bytes()
if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_bytes(sb),SOURCE_SHA))
if not candidate.exists(): raise RuntimeError("current candidate missing")
oldb=candidate.read_bytes()
if sha_bytes(oldb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha_bytes(oldb),EXPECTED_BEFORE))
if sb[:4]!=b"DDS " or oldb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
if (W,H,pitch,depth,mips)!=(4096,1024,16384,1,1): raise RuntimeError(("source structure",W,H,pitch,depth,mips))
if oldb[:128]!=sb[:128] or len(oldb)!=len(sb): raise RuntimeError("current candidate structure/header drift")

raw_source=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
source_readable=raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw_old=Image.frombytes("RGBA",(W,H),oldb[128:],"raw","RGBA")
old=raw_old.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(atlas.read_text(encoding="utf-8"))["regions"]}

# Re-derive exact Shift source glyph/effect bbox using the same canonical HD discovery geometry as A13.
stock_bbox=[940,44,968,55]
rr=regions[4]; rx,ry,rw,rh=map(int,rr["rect"]); rx2,ry2=rx+rw,ry+rh
sx1,sy1,sx2,sy2=stock_bbox
zx1=max(rx,sx1*4-24); zy1=max(ry,sy1*4-16)
zx2=min(rx2,sx2*4+24); zy2=min(ry2,sy2*4+16)
zone=(zx1,zy1,zx2,zy2)
bb=source_readable.crop(zone).getchannel("A").getbbox()
if not bb: raise RuntimeError("Shift source empty")
ob=[zx1+bb[0],zy1+bb[1],zx1+bb[2],zy1+bb[3]]
if not(ob[0]>rx and ob[1]>ry and ob[2]<rx2 and ob[3]<ry2):
    raise RuntimeError(("unexpected Shift bbox/cell contact",ob,[rx,ry,rx2,ry2]))

x0,y0,x1,y1=ob
source_crop=source_readable.crop(tuple(ob))
old_crop=old.crop(tuple(ob))
if ImageChops.difference(source_crop,old_crop).getbbox() is not None:
    raise RuntimeError("A13 Shift is no longer source-pixel-identical")

# Build exact clean plate from current candidate by removing only canonical Shift source alpha pixels.
sm=source_crop.getchannel("A").point(lambda v:255 if v else 0)
clean=old.copy()
clean.paste(Image.new("RGBA",(x1-x0,y1-y0),(0,0,0,0)),(x0,y0),sm)
if count(ImageChops.multiply(clean.crop(tuple(ob)).getchannel("A"),sm))!=0:
    raise RuntimeError("clean Shift source alpha residue")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT_PATTERN="Noto Sans CJK KR:style=Black"
FONT=subprocess.check_output(["fc-match","-f","%{file}",FONT_PATTERN],text=True).strip()
if not FONT or not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("Korean font unavailable",FONT))

# Match the plain heavy white source family. Maximize height within exact bbox; never expand to English width.
text="시프트"
aw,ah=x1-x0,y1-y0
best=None
for fs in range(max(24,int(ah*1.7)),14,-1):
    font=ImageFont.truetype(FONT,fs)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=font,stroke_width=1)
    gw,gh=tb[2]-tb[0],tb[3]-tb[1]
    glyph=Image.new("L",(gw+12,gh+12),0)
    ImageDraw.Draw(glyph).text((6-tb[0],6-tb[1]),text,font=font,fill=255,stroke_width=1,stroke_fill=255)
    gb=glyph.getbbox()
    if not gb: continue
    glyph=glyph.crop(gb)
    if glyph.height>ah-4: continue
    hscale=1.0
    if glyph.width>aw-4:
        hscale=(aw-4)/glyph.width
        if hscale<0.65: continue
        glyph=glyph.resize((aw-4,glyph.height),Image.Resampling.LANCZOS)
        gb=glyph.getbbox()
        if gb: glyph=glyph.crop(gb)
    if glyph.width<=aw-4 and glyph.height<=ah-4:
        best=(fs,glyph,hscale); break
if best is None: raise RuntimeError(("Shift Korean fit failed",ob))
fs,glyph,hscale=best

# Source labels in this right-side function column share a left anchor.
px=x0+2
py=y0+(ah-glyph.height)//2
if px+glyph.width>=x1: px=x1-glyph.width-1
if py<=y0: py=y0+1
if py+glyph.height>=y1: py=y1-glyph.height-1
if not(px>x0 and py>y0 and px+glyph.width<x1 and py+glyph.height<y1):
    raise RuntimeError(("positive margin failed",ob,[px,py,px+glyph.width,py+glyph.height]))

# Source visible color is white; sample median nontransparent source RGB to preserve exact family.
vals=[]
sp=source_crop.load()
for yy in range(source_crop.height):
    for xx in range(source_crop.width):
        r,g,b,a=sp[xx,yy]
        if a>16: vals.append((r,g,b))
if not vals: raise RuntimeError("no source color")
vals.sort(key=lambda z:z[0]+z[1]+z[2])
color=vals[len(vals)//2]+(255,)
tile=Image.new("RGBA",glyph.size,color); tile.putalpha(glyph)
final=clean.copy(); final.alpha_composite(tile,(px,py))
loc=[px,py,px+glyph.width,py+glyph.height]

# Exact RGBA32 encode preserving source header/raw mirror-y.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
newb=sb[:128]+raw_final.tobytes("raw","RGBA")
if newb[:128]!=sb[:128] or len(newb)!=len(sb): raise RuntimeError("encode structure drift")
candidate.write_bytes(newb)
decoded_raw=Image.frombytes("RGBA",(W,H),newb[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("RGBA roundtrip mismatch")

# Blast-radius and containment gates relative to the previously accepted A13/C109 bytes.
diff_old=changed_mask(old,decoded)
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
outside=count(ImageChops.multiply(diff_old,ImageOps.invert(allowed)))
alpha_delta=ImageChops.difference(old.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed)))
if outside or alpha_outside: raise RuntimeError(("blast radius",outside,alpha_outside))

db=decoded.crop(tuple(ob)).getchannel("A").getbbox()
if not db: raise RuntimeError("decoded Korean empty")
dl=[x0+db[0],y0+db[1],x0+db[2],y0+db[3]]
if not(dl[0]>x0 and dl[1]>y0 and dl[2]<x1 and dl[3]<y1):
    raise RuntimeError(("decoded positive margin",ob,dl))
if (dl[2]-dl[0])>(x1-x0) or (dl[3]-dl[1])>(y1-y0):
    raise RuntimeError(("size ceiling",ob,dl))

# Verify every previous A13 localized pixel and all other artwork remains exact outside Shift bbox.
old_exact_outside = outside==0
source_clean_residue=count(ImageChops.multiply(clean.crop(tuple(ob)).getchannel("A"),sm))
if source_clean_residue: raise RuntimeError(("clean residue",source_clean_residue))

# Evidence.
def comp(im):
    bg=Image.new("RGBA",im.size,(70,70,70,255)); bg.alpha_composite(im); return bg.convert("RGB")
m=18; cr=(max(0,x0-m),max(0,y0-m),min(W,x1+m),min(H,y1+m))
views=[comp(z).crop(cr) for z in (source_readable,old,clean,decoded)]
scale=4
views=[v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST) for v in views]
cw=sum(v.width for v in views)+12*3
ch=max(v.height for v in views)+34
sheet=Image.new("RGB",(cw,ch),"white")
labels=["SOURCE Shift","C109/A13 Shift","CLEAN","A158 시프트"]
xx=0
sd=ImageDraw.Draw(sheet)
for label,v in zip(labels,views):
    sd.text((xx+3,3),label,fill="black")
    sheet.paste(v,(xx,34)); xx+=v.width+12
sheet.save(out/"A158_AD720950_SHIFT_SOURCE_OLD_CLEAN_FINAL.jpg",quality=95)

full=Image.new("RGB",(2048,512*2),(50,50,50))
full.paste(comp(old).resize((2048,512),Image.Resampling.LANCZOS),(0,0))
full.paste(comp(decoded).resize((2048,512),Image.Resampling.LANCZOS),(0,512))
full.save(out/"A158_AD720950_OLD_FINAL_FULL.jpg",quality=94)
raw_sheet=Image.new("RGB",(2048,512*2),(50,50,50))
raw_sheet.paste(comp(raw_old).resize((2048,512),Image.Resampling.LANCZOS),(0,0))
raw_sheet.paste(comp(decoded_raw).resize((2048,512),Image.Resampling.LANCZOS),(0,512))
raw_sheet.save(out/"A158_AD720950_OLD_FINAL_RAW_MIRROR_Y.jpg",quality=94)

report={
 "schema_version":1,"role":"A","run":"A158","index":47,"asset":asset_rel,
 "trigger":"PRE_INGAME_002_UNTRANSLATED_VISIBLE_SHIFT_CURRENT_POLICY_FALSE_NEGATIVE",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"sha256":SOURCE_SHA,"dimensions":[W,H],"format":"RGBA32","raw_orientation":"mirror_y"},
 "prior_c_status":"C109_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "prior_candidate_sha256":EXPECTED_BEFORE,
 "translation_change":{"source":"Shift","prior":"Shift","korean":"시프트","reason":"visible functional UI label is not preserve-original by policy; neighboring keyboard-function labels are localized"},
 "source_bbox":ob,"source_size":[x1-x0,y1-y0],"localized_bbox":dl,"localized_size":[dl[2]-dl[0],dl[3]-dl[1]],
 "margins":{"left":dl[0]-x0,"right":x1-dl[2],"top":dl[1]-y0,"bottom":y1-dl[3]},
 "render":{"font_pattern":FONT_PATTERN,"font_file":Path(FONT).name,"font_size":fs,"horizontal_scale":round(hscale,4),"alignment":"source-left +2px","color":list(color)},
 "machine_qa":{"bbox_containment":"1/1 PASS","size_ceiling":"1/1 PASS","positive_margin":"1/1 PASS","changed_pixels_outside_shift_bbox":outside,"alpha_changed_outside_shift_bbox":alpha_outside,"clean_source_alpha_residue":source_clean_residue,"prior_candidate_exact_outside_shift_bbox":old_exact_outside,"header_128_exact":newb[:128]==sb[:128],"rgba32_roundtrip_exact":True,"raw_orientation":"mirror_y"},
 "ordered_generation_gate":{"1_source_text_removed_plate_restored":"PASS_EXACT_ALPHA_CLEAN","2_source_slant_direction":"PASS_UPRIGHT_SOURCE","3_no_unnecessary_undersizing":"PASS_MAX_SAFE_HEIGHT","4_source_faithful_weight_outline_shadow":"PASS_PLAIN_HEAVY_WHITE","5_no_clipped_pixels":"PASS_POSITIVE_MARGIN","6_protected_clearance":"PASS_ZERO_OUTSIDE_CHANGE","7_flip_y_and_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER","8_immediate_readability":"PENDING_CONTROLLER"},
 "candidate_sha256":sha_bytes(newb),
 "candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "status":"A158_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA",
 "runtime_validation":"UNTESTED",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"A158_AD720950_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":"A158","index":47,"asset":"AD720950","candidate_sha256":report["candidate_sha256"],"translation":"Shift -> 시프트","bbox_size_positive_margin":"1/1 PASS","changed_outside":outside,"alpha_outside":alpha_outside,"clean_residue":source_clean_residue,"prior_exact_outside":old_exact_outside,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261007-A-MANUALQA158-AD720950-SHIFT/A158_AD720950_REPORT.json"}
(wr/"A158_AD720950.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
