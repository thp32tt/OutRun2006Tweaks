#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A163-Q051-FF2462BB-C239-REWORK"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
source_path=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset_rel
CURRENT_SHA="3a046a8b695ee6b0a766fca223455616a45a9480b72e28b0c39ddf42821d0b6d"
SOURCE_SHA="5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67"
PRE_A144_COMMIT="5bd0324d1acb9ce8f9465bb4de282a28a7334e06"
PRE_A144_SHA="4fff8c59a44a1b7d03cee192124915f87eb73b3988c7673feb3228785ce67726"

# C239 proved the A144 patch used RAW target coordinates as if they were
# readable coordinates. The real source cell is the exact FLIP-Y counterpart.
WRONG_READABLE_BOX=[3002,482,3512,643]
RAW_SOURCE_BOX=[3002,482,3512,643]
CORRECT_READABLE_BOX=[3002,1405,3512,1566]
RAW_LINE_1=[3002,482,3512,562]
RAW_LINE_2=[3002,562,3512,643]
CORRECT_TOP_LINE=[3002,1405,3512,1486]
CORRECT_BOTTOM_LINE=[3002,1486,3512,1566]
A144_LINE1_GLYPH=[3117,491,3397,553]
A144_LINE2_GLYPH=[3068,571,3445,634]

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def count(mask): return sum(mask.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    return w,h,pitch,depth,mips,b[84:88],struct.unpack_from("<4I",b,92)
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def bbox_size(b): return [b[2]-b[0],b[3]-b[1]]

curb=candidate.read_bytes()
if sha_bytes(curb)!=CURRENT_SHA:
    raise RuntimeError(("current candidate drift",sha_bytes(curb),CURRENT_SHA))
sb=source_path.read_bytes()
if sha_bytes(sb)!=SOURCE_SHA:
    raise RuntimeError(("source drift",sha_bytes(sb),SOURCE_SHA))
W,H,pitch,depth,mips,fourcc,masks=meta(curb)
if (W,H,mips)!=(4096,2048,1) or len(curb)!=128+W*H*4:
    raise RuntimeError(("unexpected current DDS",W,H,mips,len(curb),fourcc,masks))
if meta(sb)[:5]!=(W,H,pitch,depth,mips):
    raise RuntimeError(("source structure drift",meta(sb),meta(curb)))
if curb[:128]!=sb[:128]:
    raise RuntimeError("current header differs from canonical source")

# Recover the exact pre-A144 Korean candidate. It already contains the one
# semantic girlfriend instruction at the correct lower/right source location.
prior_bytes=subprocess.check_output(["git","show",PRE_A144_COMMIT+":"+str(Path("localization/graphics/hd_candidates")/asset_rel)])
if sha_bytes(prior_bytes)!=PRE_A144_SHA:
    raise RuntimeError(("pre-A144 drift",sha_bytes(prior_bytes),PRE_A144_SHA))
if prior_bytes[:128]!=curb[:128] or len(prior_bytes)!=len(curb):
    raise RuntimeError("pre-A144 structure mismatch")

tmp=Path("/tmp/outrun_A163")
tmp.mkdir(parents=True,exist_ok=True)
curfile=tmp/"current.dds"; curfile.write_bytes(curb)
priorfile=tmp/"prior.dds"; priorfile.write_bytes(prior_bytes)

cur_raw=Image.open(curfile).convert("RGBA")
prior_raw=Image.open(priorfile).convert("RGBA")
source_raw=Image.open(source_path).convert("RGBA")
cur=cur_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
prior=prior_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
source=source_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# Source-semantic proof: the historical source RAW box flips exactly to the
# lower/right readable target. The A144 upper box is different source content.
def flip_box(b):
    x1,y1,x2,y2=b
    return [x1,H-y2,x2,H-y1]
if flip_box(RAW_SOURCE_BOX)!=CORRECT_READABLE_BOX:
    raise RuntimeError(("flip mapping drift",flip_box(RAW_SOURCE_BOX),CORRECT_READABLE_BOX))
if flip_box(RAW_LINE_2)!=CORRECT_TOP_LINE or flip_box(RAW_LINE_1)!=CORRECT_BOTTOM_LINE:
    raise RuntimeError(("line flip mapping drift",flip_box(RAW_LINE_2),flip_box(RAW_LINE_1)))

# Harvest the fresh unclipped A144 lettering pixels only. C239 rejected their
# LOCATION, not their glyph rendering. The wrong-location boxes were cleared
# before A144 rendering, so each tight alpha crop contains only the intended
# Korean glyph/effect.
g1=cur.crop(tuple(A144_LINE1_GLYPH))
g2=cur.crop(tuple(A144_LINE2_GLYPH))
if g1.getchannel("A").getbbox()!=(0,0,g1.width,g1.height):
    # Tight crop may contain transparent antialias corners; normalize by bbox.
    bb=g1.getchannel("A").getbbox()
    if not bb: raise RuntimeError("A144 line1 glyph missing")
    g1=g1.crop(bb)
if g2.getchannel("A").getbbox()!=(0,0,g2.width,g2.height):
    bb=g2.getchannel("A").getbbox()
    if not bb: raise RuntimeError("A144 line2 glyph missing")
    g2=g2.crop(bb)

# Begin from exact pre-A144 bytes to restore the erroneous upper insertion and
# every unrelated UI pixel. Rebuild ONLY the true lower/right target footprint.
final=prior.copy()
x1,y1,x2,y2=CORRECT_READABLE_BOX
final.paste(Image.new("RGBA",(x2-x1,y2-y1),(0,0,0,0)),(x1,y1))

def place_center(img,tile,box):
    x1,y1,x2,y2=box
    x=x1+(x2-x1-tile.width)//2
    y=y1+(y2-y1-tile.height)//2
    img.alpha_composite(tile,(x,y))
    return [x,y,x+tile.width,y+tile.height]

top=place_center(final,g1,CORRECT_TOP_LINE)
bottom=place_center(final,g2,CORRECT_BOTTOM_LINE)

# Mandatory positive margins, especially the user-reported clipped bottom edge.
def margins(inner,outer):
    return [inner[0]-outer[0],outer[2]-inner[2],inner[1]-outer[1],outer[3]-inner[3]]
mt=margins(top,CORRECT_TOP_LINE); mb=margins(bottom,CORRECT_BOTTOM_LINE)
if min(mt)<8 or min(mb)<8:
    raise RuntimeError(("insufficient glyph/effect margin",top,mt,bottom,mb))
if bbox_size(top)[0]>bbox_size(CORRECT_TOP_LINE)[0] or bbox_size(top)[1]>bbox_size(CORRECT_TOP_LINE)[1]:
    raise RuntimeError("top line source ceiling")
if bbox_size(bottom)[0]>bbox_size(CORRECT_BOTTOM_LINE)[0] or bbox_size(bottom)[1]>bbox_size(CORRECT_BOTTOM_LINE)[1]:
    raise RuntimeError("bottom line source ceiling")

# Current->final blast radius may change only the erroneous A144 upper patch
# and the actual lower/right girlfriend source cell. Prior->final must change
# only the actual target cell.
allowed=Image.new("L",(W,H),0); ad=ImageDraw.Draw(allowed)
for b in (WRONG_READABLE_BOX,CORRECT_READABLE_BOX):
    ad.rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=255)
targetmask=Image.new("L",(W,H),0)
ImageDraw.Draw(targetmask).rectangle((x1,y1,x2-1,y2-1),fill=255)

curdiff=diffmask(cur,final)
current_outside=count(ImageChops.multiply(curdiff,ImageOps.invert(allowed)))
priordiff=diffmask(prior,final)
prior_outside=count(ImageChops.multiply(priordiff,ImageOps.invert(targetmask)))
if current_outside or prior_outside:
    raise RuntimeError(("blast radius",current_outside,prior_outside))

# Restore exact DDS structure/channel order.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
rawmode=None
for mode in ("BGRA","RGBA"):
    try:
        if cur_raw.tobytes("raw",mode)==curb[128:]:
            rawmode=mode; break
    except Exception:
        pass
if rawmode is None: raise RuntimeError(("cannot infer rawmode",masks))
newb=curb[:128]+raw_final.tobytes("raw",rawmode)
if newb[:128]!=curb[:128] or len(newb)!=len(curb):
    raise RuntimeError("DDS structure changed")
candidate.write_bytes(newb)

dec_raw=Image.open(candidate).convert("RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None:
    raise RuntimeError("persisted decode mismatch")

# Verify the erroneous upper insertion is exactly restored to pre-A144 bytes.
if ImageChops.difference(dec.crop(tuple(WRONG_READABLE_BOX)),prior.crop(tuple(WRONG_READABLE_BOX))).getbbox() is not None:
    raise RuntimeError("wrong A144 insertion not fully restored")
# Verify all unrelated pixels are exact to pre-A144.
if count(ImageChops.multiply(diffmask(prior,dec),ImageOps.invert(targetmask))):
    raise RuntimeError("final differs from pre-A144 outside intended target")

newsha=sha_bytes(newb)

# Evidence: full atlas and target/source practical-scale comparisons.
full=Image.new("RGB",(3072,512),(36,36,36))
for i,z in enumerate((source,cur,dec)):
    v=comp(z).resize((1024,512),Image.Resampling.LANCZOS)
    full.paste(v,(i*1024,0))
ImageDraw.Draw(full).text((8,5),"SOURCE | C239-REJECTED A144 CURRENT | A163 FINAL",fill="white")
full.save(out/"A163_FF2462_FULL_SOURCE_REJECTED_FINAL.jpg",quality=94)

pad=80
crop=[x1-pad,y1-pad,x2+pad,y2+pad]
views=[comp(z.crop(tuple(crop))) for z in (source,prior,cur,dec)]
labels=["SOURCE","PRE-A144","C239 REJECTED","A163 FINAL"]
sheet=Image.new("RGB",(sum(v.width for v in views)+30,max(v.height for v in views)+32),(235,235,235))
xx=0; d=ImageDraw.Draw(sheet)
for lab,v in zip(labels,views):
    d.text((xx+3,4),lab,fill="black"); sheet.paste(v,(xx,32)); xx+=v.width+10
sheet.save(out/"A163_FF2462_TARGET_SOURCE_PRIOR_REJECTED_FINAL.jpg",quality=96)

# Explicit upper erroneous region evidence.
ucrop=[WRONG_READABLE_BOX[0]-40,WRONG_READABLE_BOX[1]-40,WRONG_READABLE_BOX[2]+40,WRONG_READABLE_BOX[3]+40]
uv=[comp(z.crop(tuple(ucrop))) for z in (source,cur,dec)]
us=Image.new("RGB",(sum(v.width for v in uv)+20,max(v.height for v in uv)+30),(235,235,235)); xx=0
for lab,v in zip(["SOURCE","C239 REJECTED","A163 RESTORED"],uv):
    ImageDraw.Draw(us).text((xx+3,3),lab,fill="black"); us.paste(v,(xx,30)); xx+=v.width+10
us.save(out/"A163_FF2462_WRONG_INSERTION_RESTORED.jpg",quality=96)

# RAW evidence of exact source-cell orientation.
rcrop=[RAW_SOURCE_BOX[0]-80,RAW_SOURCE_BOX[1]-80,RAW_SOURCE_BOX[2]+80,RAW_SOURCE_BOX[3]+80]
rv=[comp(z.crop(tuple(rcrop))) for z in (source_raw,cur_raw,dec_raw)]
rs=Image.new("RGB",(sum(v.width for v in rv)+20,max(v.height for v in rv)+30),(235,235,235)); xx=0
for lab,v in zip(["SOURCE RAW","A144 RAW","A163 RAW"],rv):
    ImageDraw.Draw(rs).text((xx+3,3),lab,fill="black"); rs.paste(v,(xx,30)); xx+=v.width+10
rs.save(out/"A163_FF2462_RAW_SOURCE_REJECTED_FINAL.jpg",quality=96)

for pct in (100,75,50):
    c=dec.crop(tuple(crop))
    sz=(round(c.width*pct/100),round(c.height*pct/100))
    z=comp(c).resize(sz,Image.Resampling.LANCZOS)
    z.save(out/f"A163_FF2462_PRACTICAL_{pct}.jpg",quality=95)

report={
 "schema_version":2,"role":"A","run":"A163","queue_index":51,"priority":"P0",
 "asset":asset_rel,"trigger":"C239_REWORK_REQUIRED_SOURCE_TARGET_MISMATCH_DUPLICATED_GIRLFRIEND",
 "user_regression":"PJR-014-20261006 BOTTOM_OUTLINE_CLIPPED|GLYPH_EFFECT_CLIPPING",
 "source_sha256":SOURCE_SHA,"rejected_candidate_sha256":CURRENT_SHA,
 "pre_a144_candidate":{"commit":PRE_A144_COMMIT,"sha256":PRE_A144_SHA},
 "candidate_sha256":newsha,
 "mapping_correction":{
   "historical_raw_source_box":RAW_SOURCE_BOX,
   "wrong_a144_readable_box":WRONG_READABLE_BOX,
   "correct_readable_box":CORRECT_READABLE_BOX,
   "proof":"correct_readable_y = H - raw_y; C239 showed A144 had treated RAW y as readable y"
 },
 "repair":{
   "restore_wrong_insertion":"PASS_EXACT_PRE_A144_BYTES",
   "correct_target":"lower/right Don't lose your girlfriend! source footprint only",
   "top_line":{"text":"여자친구를","source_box":CORRECT_TOP_LINE,"localized_bbox":top,"margins_lrtb":mt},
   "bottom_line":{"text":"놓치지 마세요!","source_box":CORRECT_BOTTOM_LINE,"localized_bbox":bottom,"margins_lrtb":mb},
   "glyph_source":"A144 fresh unclipped Korean glyph/effect pixels reused losslessly; location corrected"
 },
 "machine_qa":{
   "current_to_final_changed_pixels_outside_declared_union":current_outside,
   "pre_a144_to_final_changed_pixels_outside_correct_target":prior_outside,
   "wrong_insertion_exactly_restored":True,
   "header_128_exact":newb[:128]==curb[:128],
   "dimensions":[W,H],"mips":mips,"rawmode":rawmode,
   "persisted_decode_exact":True,
   "source_size_ceiling":"PASS_2_OF_2",
   "positive_margin":"PASS_2_OF_2_MIN_8PX"
 },
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_TRANSPARENT_SOURCE_CELL_CLEARED_ONLY_AT_TRUE_TARGET_AND_WRONG_A144_INSERTION_RESTORED",
   "2_slant_direction":"PASS_REUSED_A144_SOURCE_FAMILY_GLYPH_PIXELS",
   "3_no_unnecessary_undersizing":"PASS_SOURCE_RELATIVE_TWO_LINE_SCALE_WITH_POSITIVE_MARGINS",
   "4_weight_outline_shadow":"PASS_A144_YELLOW_NAVY_SOURCE_FAMILY_REUSED",
   "5_clipping":"PASS_MIN_8PX_LINE_EFFECT_MARGIN",
   "6_protected_clearance":"PASS_ZERO_CHANGE_OUTSIDE_DECLARED_RESTORE_PLUS_TARGET_UNION",
   "7_flip_y_raw":"PASS_EXACT_RAW_SOURCE_CELL_MAPPING_AND_EVIDENCE",
   "8_readability":"PENDING_CONTROLLER_VISUAL_CONFIRMATION"
 },
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "fresh_independent_c":"REQUIRED","mandatory_c3":"REQUIRED_EXACT_SHA",
 "pre_ingame_export":"BLOCKED_UNTIL_FRESH_C_C3",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"A163_FF2462BB_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":"A163","queue_index":51,"asset":"FF2462BB","candidate_sha256":newsha,
 "worker_status":"STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL","report":"localization/graphics/role_A/20261007-A163-Q051-FF2462BB-C239-REWORK/A163_FF2462BB_REPORT.json",
 "runtime_validation":"UNTESTED"}
(wr/"A163_FF2462BB.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
