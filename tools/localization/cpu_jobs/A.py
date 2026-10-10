#!/usr/bin/env python3
"""A226 q101 C1-confirmed 45px source remnant clean + canonical warning text material trial.
Official 13-cell DDS stays unchanged; rework only C1-confirmed warning.
"""
import hashlib, io, json, os, subprocess, urllib.request, statistics
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTCollection
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
repo=Path.cwd()
run="20261010-A226-Q101-SOURCE-45PIXEL-CLEAN-CANONICAL"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
q=json.loads(subprocess.run(["python","tools/localization/rework_triage.py","--index","101","--require-safe-rerender"],check=True,text=True,capture_output=True).stdout)["assets"][0]
assert q["index"]==101 and q["next_action"]=="MATERIAL_REWORK",q
review=json.loads((repo/"localization/graphics/role_C/20261010-C1-Q101-SOURCE-ITALIC-REWORK/C1_Q101_INDEPENDENT_VISUAL_REJECT.json").read_text())
assert review["decision"]=="REWORK_REQUIRED" and review["firsthand_review"]["reason_code"]=="SOURCE_FAMILY_RIGHT_ITALIC_MISMATCH"
new_c1=json.loads((repo/"localization/graphics/role_C/20261010-C1-Q101-A225-CLEAN-PLATE-LEFTOVER/C1_Q101_A226_INDEPENDENT_PERSISTED_REWORK.json").read_text())
assert new_c1["independent_C1_result"]=="REWORK_REQUIRED"
assert new_c1["first_hand_contact_residue"]["clean_visible_non_gray_pixels"]==45
assert new_c1["trial_candidate_sha256"]=="5b6bcfd83c39aebbe46f2cbdb8d95cfa584a4955ec9a84d9039480a77a709a86"
previous_trial=json.loads((repo/"localization/graphics/role_A/20261010-A225-Q101-WARNING-SOURCE-ITALIC/A225_MACHINE_TRIAL_QA.json").read_text())
assert previous_trial["new_trial_sha256"]==new_c1["trial_candidate_sha256"]
old_path=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/560FA536_1024x1024.dds"
old=old_path.read_bytes()
old_sha="939ac217127fc958f78524c021d2c735ffbc9af5d80af0d65bb04a226dbf3cdb"
english_sha="a29d70ffef85c74c67f78752b4dcc83cc4055220313952536081441a54f6b1aa"
assert sha(old)==old_sha and len(old)==128+4096*4096*4 and old[:4]==b"DDS "
url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
     "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/"
     "Release/spr_sprani_selector_cvt_Exst/560FA536_1024x1024.dds")
with urllib.request.urlopen(url,timeout=180) as r: srcbytes=r.read()
assert sha(srcbytes)==english_sha,(sha(srcbytes),english_sha)
source=Image.open(io.BytesIO(srcbytes)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
before=Image.open(io.BytesIO(old)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
assert source.size==before.size==(4096,4096)
# C180/C1 independently attributed exact source effect; warning icon/number are OUTSIDE.
rect=(3002,25,3932,168)
x0,y0,x1,y1=rect; cw,ch=x1-x0,y1-y0
oldreg=before.crop(rect)
srcreg=source.crop(rect)
S=np.asarray(srcreg,dtype=np.uint8)
O=np.asarray(oldreg,dtype=np.uint8)
assert int((S[:,:,3]>0).sum())>8000 and int((O[:,:,3]>0).sum())>8000
# C180 validated warning glyph alone in this canonical bbox. CLEAN is truly transparent.
# Fail closed if source opacity belongs to a rectangle or outside the originally attested warning.
assert int((S[:,:,3]>0).sum())<cw*ch*0.95
# C1 identified exactly 45 source-language italic trailing tip pixels
# in native readable x3002..3005; x3000..3001 is transparent gap to icon.
remnant=np.asarray(source.crop((3002,25,3006,168)),dtype=np.uint8)
remnant_old=np.asarray(before.crop((3002,25,3006,168)),dtype=np.uint8)
protected_gap=np.asarray(source.crop((3000,25,3002,110)),dtype=np.uint8)
assert int((remnant[:,:,3]>0).sum())==45,("C1 remnant count drift",int((remnant[:,:,3]>0).sum()))
assert np.array_equal(remnant,remnant_old),"Current trial/reference remnant changed; re-evaluate before masking"
assert int((protected_gap[:,:,3]>0).sum())==0,"Adjacent icon gap not clean; no blanket left deletion"
cleanreg=Image.new("RGBA",(cw,ch),(0,0,0,0))
# Source visual palette from the authentic source, not arbitrary colors.
opaque=S[S[:,:,3]>=220,:3]
facec=[tuple(map(int,v)) for v in opaque if int(v[0])>150 and int(v[1])>85 and int(v[0])>int(v[2])*1.55]
darkc=[tuple(map(int,v)) for v in opaque if int(v[2])>int(v[0])*1.3 and int(v[0])<85 and int(v[1])<90]
assert len(facec)>1000 and len(darkc)>1000,(len(facec),len(darkc))
face=Counter(facec).most_common(1)[0][0]
stroke=Counter(darkc).most_common(1)[0][0]
font_path=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
assert font_path.is_file()
fontsha=sha(font_path.read_bytes())
coverage=TTCollection(str(font_path),lazy=True).fonts[1].getBestCmap()
lines=["이 모드를 플레이하려면 모든", "플레이어가 동시에 참가해야 합니다."]
assert " ".join(lines)=="이 모드를 플레이하려면 모든 플레이어가 동시에 참가해야 합니다."
assert all(ord(k) in coverage for line in lines for k in line if k!=" ")
# Original text rows run at separate top/bottom heights. Derive their readable
# source alpha bounding boxes, not an enclosing plate.
alpha=S[:,:,3]>90
ys=alpha.sum(axis=1)
# Best valley within the inner line break (source rows, not Korean).
valley=int(np.argmin(ys[64:105]))+64
source_rows=[alpha[:valley,:],alpha[valley:,:]]
en_boxes=[]
for n,m in enumerate(source_rows):
 yy,xx=np.nonzero(m);assert len(xx)>1000
 yoffset=0 if n==0 else valley
 en_boxes.append([int(xx.min())+x0,int(yy.min())+y0+yoffset,int(xx.max())+1+x0,int(yy.max())+1+y0+yoffset])
assert en_boxes[0][3]<=en_boxes[1][1]+10,en_boxes
# English slant: a source-family right-italic, upper glyph strokes lean
# to the right relative to lower stems in readable orientation.
# A225 reconstitutes genuine Hangul outlines with a prescribed explicit
# native-source slant profile; do not shear pixels from old Korean DDS.
source_italic_dx_over_height=0.32
def make_layer(line,ppem):
    font=ImageFont.truetype(str(font_path),ppem,index=1)
    sw=4 if ppem>=40 else 3
    bounds=font.getbbox(line,stroke_width=sw)
    margin=16
    tmp=Image.new("RGBA",(bounds[2]-bounds[0]+margin*2,bounds[3]-bounds[1]+margin*2),(0,0,0,0))
    d=ImageDraw.Draw(tmp)
    d.text((margin-bounds[0],margin-bounds[1]),line,font=font,fill=face+(255,),stroke_width=sw,stroke_fill=stroke+(255,))
    bb=tmp.getbbox(); assert bb
    glyph=tmp.crop(bb)
    hh=glyph.height;k=source_italic_dx_over_height
    extra=int(hh*k)+5
    # Pillow inverse transform: output.top stem translated right by k*height.
    sheared=glyph.transform((glyph.width+extra,hh),Image.Transform.AFFINE,
        (1,k,-k*(hh-1)+2,0,1,0),resample=Image.Resampling.BICUBIC)
    b=sheared.getbbox();assert b
    return sheared.crop(b)
chosen=None
for pp in range(57,30,-1):
    ims=[make_layer(line,pp) for line in lines]
    # compare EACH Korean line to its English line's true source-effect extent;
    # leave 2px vertical margins and at least 3px horizontal.
    if all(im.width<=en_boxes[n][2]-en_boxes[n][0]-6 and
           im.height<=en_boxes[n][3]-en_boxes[n][1]-4 for n,im in enumerate(ims)):
        chosen=pp
        break
assert chosen is not None,{"source_line_boxes":en_boxes,"max":57}
# Place using English per-line natural centers, inside exact source glyph effect.
final_region=Image.new("RGBA",(cw,ch),(0,0,0,0))
glyph_bounds=[]
for n,im in enumerate(ims):
    bx=en_boxes[n]
    # exact source-per-line center and vertical center
    tx=(bx[0]+bx[2]-im.width)//2
    ty=(bx[1]+bx[3]-im.height)//2
    assert bx[0]<tx and bx[1]<ty and tx+im.width<bx[2] and ty+im.height<bx[3],(n,tx,ty,im.size,bx)
    final_region.alpha_composite(im,(tx-x0,ty-y0))
    glyph_bounds.append([tx,ty,tx+im.width,ty+im.height])
assert glyph_bounds[0][3]<glyph_bounds[1][1],glyph_bounds
assert all(x0<a and b<x1 and y0<c and d<y1 for a,c,b,d in glyph_bounds)
clean=before.copy()
clean.paste(cleanreg,rect[:2])
final=before.copy()
final.paste(final_region,rect[:2])
assert final.getbbox()
# Verify exact source-region changes only, including hidden RGB bytes.
assert np.array_equal(np.asarray(before.crop((0,0,x0,4096))),np.asarray(final.crop((0,0,x0,4096))))
# Re-encode as exact native DDS bytes and retain untouched atlas rows and headers.
updated=bytearray(old)
patch=np.asarray(final_region,dtype=np.uint8)
for row in range(ch):
    raw_y=4095-(y0+row)
    off=128+(raw_y*4096+x0)*4
    updated[off:off+cw*4]=patch[row].tobytes()
updated=bytes(updated)
assert sha(updated)!=old_sha and updated[:128]==old[:128] and len(updated)==len(old)
ddspath=out/"A226_Q101_REMNANT45_CANONICAL_UNPROMOTED.dds"
ddspath.write_bytes(updated)
saved=Image.open(ddspath).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
assert np.array_equal(np.asarray(saved.crop(rect)),patch)
# Crucial neighbor guard: compare every untouched pixel as exact bytes, not only bbox statistics.
a=np.asarray(saved,dtype=np.uint8)
b=np.asarray(before,dtype=np.uint8)
diff=np.any(a!=b,axis=2)
assert int(diff.sum())>0
outside=diff.copy();outside[y0:y1,x0:x1]=False
assert not bool(outside.any())
source_other=np.asarray(source,dtype=np.uint8)
assert np.array_equal(a[:y0],b[:y0]) and np.array_equal(a[y1:],b[y1:])
changed=int(diff.sum());changed_alpha=int((a[:,:,3]!=b[:,:,3]).sum())
# SOURCE->CLEAN warning only, then CLEAN->FINAL exact transparent lettering.
assert np.count_nonzero(np.asarray(cleanreg)[:,:,3])==0
assert int((patch[:,:,3]>0).sum())>3000
assert (a[~diff]==b[~diff]).all()
# Source optical profile and source/clean/final visual proof, including neighbors.
crop=(2850,0,4096,210)
def composite(im,rgb=(110,110,110,255)):
    return Image.alpha_composite(Image.new("RGBA",im.size,rgb),im).convert("RGB")
images=[source.crop(crop),clean.crop(crop),before.crop(crop),saved.crop(crop)]
for name,im in zip(("SOURCE","CLEAN","OLD","FINAL"),images):
    im.save(out/f"A225_{name}_READABLE_NATIVE_RGBA.png")
for bgname,bg in [("GRAY",(110,110,110,255)),("BLACK",(0,0,0,255)),("WHITE",(255,255,255,255))]:
    for pct in (100,75,50):
        cells=[composite(im,bg) for im in images]
        if pct!=100:
            size=(round(cells[0].width*pct/100),round(cells[0].height*pct/100))
            cells=[c.resize(size,Image.Resampling.LANCZOS) for c in cells]
        w,h=cells[0].size
        sheet=Image.new("RGB",(w*4,h+28),bg[:3])
        draw=ImageDraw.Draw(sheet)
        for j,(name,im) in enumerate(zip(("SOURCE","CLEAN","A38","A225"),cells)):
            sheet.paste(im,(j*w,28))
            draw.text((j*w+5,5),name,fill=(0,0,0) if bgname=="WHITE" else (255,255,255))
        sheet.save(out/f"A225_COMPARE_{bgname}_{pct}.png")
saved.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop((2850,4096-210,4096,4096)).save(out/"A225_FINAL_RAW_NATIVE_RGBA.png")
Image.fromarray(np.asarray(final_region)[:,:,3],mode="L").save(out/"A225_TRANSPARENT_LETTER_ALPHA.png")
report={
  "run":"A226","role":"A","queue_index":101,
  "run_key":"OUTRUN-KOR-A226-Q101-C1-45PIXEL-REMNANT-CANONICAL-20261010-1800",
  "triage":q,"source_sha256":english_sha,
  "confirmed_c1_a225_remnant_45":True,"canonical_translation_restored":True,
  "left_source_remnant_verified_pixels":int((remnant[:,:,3]>0).sum()),
  "protected_transparent_gap_to_icon":True,"remnant_source_old_bytes_equal":True,
  "source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
  "old_official_sha256":old_sha,"official_changed":False,
  "new_trial_sha256":sha(updated),"new_trial_path":str(ddspath.relative_to(repo)),
  "format":"4096x4096 RGBA32 mip1 RAW mirror_y",
  "original_warning_bbox":list(rect),"source_line_bboxes":en_boxes,
  "new_korean_lines":lines,"new_glyph_bboxes":glyph_bounds,
  "source_italic_source_family_ratio":source_italic_dx_over_height,
  "italic_source_anchor_status":"UNMEASURED_EXTERNAL_C1_REQUIRED",
  "slant_anchor_evidence":"SOURCE/CLEAN/FINAL native + RAW; independent paired-glyph source anchor pending",
  "font":{"file":str(font_path),"sha256":fontsha,"face_index":1,"family":"Noto Sans CJK KR Bold","ppem":chosen,"glyph_coverage":True},
  "source_sampled_face_rgb":face,"source_sampled_outline_rgb":stroke,
  "original_region_source_alpha_nonzero":int((S[:,:,3]>0).sum()),
  "original_region_old_alpha_nonzero":int((O[:,:,3]>0).sum()),
  "clean_alpha_nonzero":0,"new_letter_alpha_nonzero":int((patch[:,:,3]>0).sum()),
  "changed_rgba_pixels":changed,"changed_alpha_pixels":changed_alpha,
  "changed_outside_source_bbox":0,"source_warning_icon_numeric_outside_edit_preserved":True,
  "persisted_dds_redecoded_equal":True,"native_source_size_ceiling_each_line":True,
  "new_trial_dds":1,"promoted_dds":0,"stage":"SOURCE_CLEAN_REMNANT45_AND_CANONICAL_TEXT_NEW_TRIAL",
  "visual_review":"PENDING_CONTROLLER_FIRSTHAND","independent_C1":"PENDING",
  "C3":"NOT_RUN","USER_INGAME":"NOT_TESTED","RUNTIME_VALIDATION":"UNTESTED",
  "exclusions":["VR","FFB","DX11","DXVK"]}
(out/"A225_MACHINE_TRIAL_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"trial_sha":sha(updated),"ppem":chosen,"source_line_boxes":en_boxes,
                  "new_glyph_boxes":glyph_bounds,"changed":changed},ensure_ascii=False))
