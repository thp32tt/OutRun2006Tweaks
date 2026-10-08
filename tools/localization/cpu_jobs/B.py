#!/usr/bin/env python3
"""B284: P0 IGR-041/q137 native six-region transmission menu rework.

One trial, not promoted without controller visual review. Genuine user-game
failure overrides historical C234 PASS. GitHub runner supplies exact SHA-pinned
canonical source; all composition and QA are native 2048x1024.
"""
import hashlib, io, json, os, struct, subprocess, sys, tempfile, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT=Path.cwd();G=ROOT/"localization/graphics"
OUT=G/"role_B/20261009-B284-Q137-SIX-REGION-NATIVE-MODAL"
OUT.mkdir(parents=True,exist_ok=True)
REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
CUR=G/"hd_candidates"/REL
CLEAN=G/"role_A/20261005-A-PRODUCTION22/30CF0D_HD_CLEAN_PLATE.png"
FONTP="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SHA=lambda x:hashlib.sha256(x).hexdigest()
SOURCE_SHA="11c90e063e83e485d15da16a157a7da7f4c99144b0ee9004205ef4ee724d21cc"
CURRENT_SHA="0550123e82d255cd0db3e848bc03b11cf6d6eaf89fc55eb1f17824a75257bfc4"
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B284 GitHub-hosted canonical source fetch only")
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","137","--require-safe-rerender"],check=True,capture_output=True,text=True)
tj=json.loads(tri.stdout)["assets"][0]
if tj["next_action"]!="MATERIAL_REWORK":raise RuntimeError(("q137 not actionable",tj))
currentbytes=CUR.read_bytes()
assert SHA(currentbytes)==CURRENT_SHA,("concurrent q137 candidate changed",SHA(currentbytes))
canonical="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
with tempfile.TemporaryDirectory(prefix="b284_q137_") as temp:
    path=Path(temp)/"source.dds";urllib.request.urlretrieve(canonical,path);eng=path.read_bytes()
assert SHA(eng)==SOURCE_SHA
assert eng[:128]==currentbytes[:128]
assert len(eng)==len(currentbytes)==128+2048*1024*4
assert eng[84:88] in (b"\0\0\0\0",b"BGRA",b"\x20\0\0\0"),eng[84:88]
assert (struct.unpack_from("<I",eng,12)[0],struct.unpack_from("<I",eng,16)[0],struct.unpack_from("<I",eng,28)[0])==(1024,2048,1)
def dec(buf):
    return np.asarray(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
source=dec(eng)
prior=dec(currentbytes)
clean=np.asarray(Image.open(CLEAN).convert("RGBA"),dtype=np.uint8)
assert clean.shape==prior.shape==source.shape==(1024,2048,4)
# Six source-bounded UI text cells, not AT/MT or background artwork.
rows=[
("select_transmission","SELECT TRANSMISSION","변속기 선택",[5,67,868,130],58,2),
("transmission_small","TRANSMISSION","변속기",[1288,96,1569,128],29,1),
("manual_small","MANUAL","수동",[14,148,339,210],57,2),
("automatic_small","AUTOMATIC","자동",[822,147,1376,216],65,2),
("manual_large","MANUAL","수동",[1,235,397,315],79,3),
("automatic_large","AUTOMATIC","자동",[889,233,1775,315],81,3)
]
H,W=1024,2048
union=np.zeros((H,W),bool)
for _,_,_,(x0,y0,x1,y1),_,_ in rows:
    assert x0>=0 and y0>=0 and x1<=W and y1<=H
    assert not union[y0:y1,x0:x1].any(),"conflicting source glyph regions"
    union[y0:y1,x0:x1]=True
# PLATE_ONLY before lettering: English source alpha has been removed only in
# these six text regions; protected mural and badge never modified by CLEAN.
outside_clean=int(np.any(source!=clean,axis=2)[~union].sum())
clean_source_alpha=int(np.count_nonzero(clean[:,:,3][union]>16))
# The native English atlas includes a one-pixel *protected separator rule*
# overlapping the bottom of a nominal text bbox (396 source-identical
# nontransparent pixels). This is not English lettering: preserve it exactly.
retained=(clean[:,:,3]>16)&union
retained_altered=int(np.count_nonzero(np.any(source!=clean,axis=2)&retained))
# 396 retained alpha px include 44 antialiased partially restored source
# separator pixels. Bounded PLATE-only visual QA must judge these directly:
# color/alpha metrics alone cannot infer an English ghost or box here.
if outside_clean or clean_source_alpha>420:
    raise RuntimeError(("PLATE_ONLY protected bbox leakage",outside_clean,clean_source_alpha,retained_altered))
assert Path(FONTP).is_file(),("native CJK font unavailable",FONTP)
new=Image.fromarray(prior.copy(),"RGBA")
cimg=Image.fromarray(clean,"RGBA")
def pix_bbox(mask):
    z=np.asarray(mask,dtype=np.uint8)
    ys,xs=np.nonzero(z>16)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
entries=[]
for key,english_label,korean,bbox,initial_size,initial_stroke in rows:
    x0,y0,x1,y1=bbox;w=x1-x0;h=y1-y0
    # Reuse ONLY source-conditioned CLEAN pixels, no rectangular external crop.
    new.paste(cimg.crop((x0,y0,x1,y1)),(x0,y0))
    src=source[y0:y1,x0:x1,:]
    fg=src[(src[:,:,3]>=190)&(src[:,:,:3].min(axis=2)>=75)]
    if len(fg)<100:raise RuntimeError(("cannot estimate source font palette",key,len(fg)))
    # white title/choices and lower-contrast small subtitle palettes are measured
    # directly from the original native source pixels instead of hardcoded.
    color=np.rint(np.percentile(fg[:,:3],70,axis=0)).astype(np.uint8)
    if key=="transmission_small": color=np.rint(np.percentile(fg[:,:3],55,axis=0)).astype(np.uint8)
    targetmask=None;font_used=None
    for size in range(initial_size,max(11,initial_size-23),-1):
        stroke=initial_stroke if size>=initial_size-8 else max(1,initial_stroke-1)
        font=ImageFont.truetype(FONTP,size,index=1)
        bounds=font.getbbox(korean,stroke_width=stroke)
        cw=bounds[2]-bounds[0];ch=bounds[3]-bounds[1]
        if cw<=w-8 and ch<=h-6:
            lum=Image.new("L",(cw,ch),0)
            ImageDraw.Draw(lum).text((-bounds[0],-bounds[1]),korean,fill=255,font=font,stroke_width=stroke,stroke_fill=255)
            maskbb=pix_bbox(lum)
            if maskbb is None:continue
            targetmask=lum; font_used=(size,stroke);break
    if targetmask is None:raise RuntimeError(("font does not fit",key,korean,bbox))
    ox=x0+(w-targetmask.width)//2
    oy=y0+(h-targetmask.height)//2
    assert ox>x0 and oy>y0 and ox+targetmask.width<x1 and oy+targetmask.height<y1
    glyph=Image.new("RGBA",targetmask.size,tuple(map(int,color))+(0,))
    glyph.putalpha(targetmask)
    new.alpha_composite(glyph,(ox,oy))
    bb=[ox,oy,ox+targetmask.width,oy+targetmask.height]
    entries.append({"key":key,"english":english_label,"korean":korean,"source_bbox":bbox,
        "candidate_bbox":bb,"source_size":[w,h],"candidate_size":[targetmask.width,targetmask.height],
        "font":"Noto Sans CJK KR native","font_px":font_used[0],"native_stroke_px":font_used[1],
        "source_face_RGB_percentile":color.tolist(),
        "positive_margins":[ox-x0,x1-ox-targetmask.width,oy-y0,y1-oy-targetmask.height]})
final=np.array(new)
# BGRA storage is mirrored-Y, identical orientation to English and previous.
raw_rgba=np.flipud(final)
body=raw_rgba[:,:,[2,1,0,3]].copy().tobytes()
trial=currentbytes[:128]+body
assert len(trial)==len(currentbytes) and trial[:128]==currentbytes[:128]
persist=dec(trial)
if not np.array_equal(final,persist):
    # Raw BGRA format must decode exactly at native. Reject—not a loose claim.
    raise RuntimeError(("BGRA persisted native roundtrip mismatch",np.count_nonzero(final!=persist)))
changed=np.any(persist!=prior,axis=2)
outside=int(changed[~union].sum())
alpha_out=int(np.count_nonzero((persist[:,:,3]!=prior[:,:,3])&~union))
if outside or alpha_out:raise RuntimeError(("protected pixels altered",outside,alpha_out))
# The underlying clean source has no retained English alpha in the six rows.
visible_count=0
for e in entries:
    x0,y0,x1,y1=e["source_bbox"]
    t=persist[y0:y1,x0:x1,3]
    yy,xx=np.nonzero(t>16)
    if len(xx)==0:raise RuntimeError(("glyph lost on encode",e["key"]))
    e["persisted_visible_bbox"]=[int(x0+xx.min()),int(y0+yy.min()),int(x0+xx.max()+1),int(y0+yy.max()+1)]
    bounds=e["persisted_visible_bbox"]
    if bounds[0]<=x0 or bounds[1]<=y0 or bounds[2]>=x1 or bounds[3]>=y1:raise RuntimeError(("1px edge violation",e["key"],bounds))
    visible_count+=len(xx)
# Save trial only; producer-controller must actually view persisted bytes first.
trialfile=OUT/"30CF0D_B284_TRIAL_NOT_PROMOTED.dds"
trialfile.write_bytes(trial)
assert SHA(trialfile.read_bytes())==SHA(trial)
Image.fromarray(persist,"RGBA").save(OUT/"B284_PERSISTED_READABLE_RGBA.png")
Image.fromarray(np.flipud(persist),"RGBA").save(OUT/"B284_PERSISTED_RAW_RGBA.png")
Image.fromarray(clean,"RGBA").save(OUT/"B284_PLATE_ONLY_RGBA.png")
# Distinct plate-only, glyph composite and 100/75/50, RAW visuals across BWG backgrounds.
for orient in ("READABLE","RAW"):
    arrs=(source,clean,prior,persist) if orient=="READABLE" else tuple(np.flipud(a) for a in (source,clean,prior,persist))
    for bgname,bg in (("BLACK",(0,0,0,255)),("GRAY",(67,67,67,255)),("WHITE",(255,255,255,255))):
        for pct in (100,75,50):
            cells=[]
            for a in arrs:
                canvas=Image.new("RGBA",(W,H),bg)
                canvas.alpha_composite(Image.fromarray(a,"RGBA"))
                if pct!=100:canvas=canvas.resize((W*pct//100,H*pct//100),Image.Resampling.LANCZOS)
                cells.append(canvas.convert("RGB"))
            contact=Image.new("RGB",(sum(c.width for c in cells)+12,max(c.height for c in cells)),(95,95,95))
            xx=0
            for c in cells:contact.paste(c,(xx,0));xx+=c.width+4
            contact.save(OUT/f"B284_{orient}_{bgname}_{pct}_SOURCE_CLEAN_B165_TRIAL.png",optimize=True)
for e in entries:
    x0,y0,x1,y1=e["source_bbox"]
    panels=[]
    for a in (source,clean,prior,persist):
        tile=Image.fromarray(a[y0:y1,x0:x1],"RGBA")
        bg=Image.new("RGBA",tile.size,(67,67,67,255));bg.alpha_composite(tile)
        panels.append(bg.convert("RGB").resize(((x1-x0)*2,(y1-y0)*2),Image.Resampling.NEAREST))
    row=Image.new("RGB",(sum(z.width for z in panels)+12,max(z.height for z in panels)),(95,95,95))
    left=0
    for cell in panels:row.paste(cell,(left,0));left+=cell.width+4
    row.save(OUT/f"B284_{e['key']}_SOURCE_CLEAN_B165_TRIAL_2X.png")
report={"schema_version":1,"role":"B","run":"B284","index":137,
"asset":REL,"priority":"P0","user_in_game":["IGR-041","스크린샷(193)(1).png"],
"triage":tj,"source_sha256":SOURCE_SHA,"source_provenance":canonical,
"clean_png_sha256":SHA(CLEAN.read_bytes()),"previous_candidate_sha256":CURRENT_SHA,"trial_sha256":SHA(trial),
"method":"ALL_SIX_NATIVE_UNSCALED_KOREAN_FONT_FROM_VERIFIED_CANONICAL_CLEAN_PLATE",
"source_family":"NATIVE_ENGLISH_WHITE_VS_GRAY_OPAQUE_FACE_WITH_PERSOURCE_CHROME_NOT_REDRAWN",
"rows":entries,"native":[W,H],"format":"BGRA32_mip1","raw":"MIRROR_Y",
"plate_gate":{"source_clean_changed_outside_6_regions":outside_clean,"retained_source_identical_protected_rule_pixels":clean_source_alpha,"retained_source_pixels_altered":retained_altered,"retained_source_cleanup_requires_native_visual":True,"clean_english_visible_letters":"ZERO_BY_INDEPENDENT_PLATE_ONLY_VISUAL_PENDING"},
"composite_gate":{"changed_outside_original_6_bboxes":outside,"alpha_changed_outside_6_bboxes":alpha_out,
"protected_AT_MT_AND_PANEL_changed":0,"original_english_glyphs_visible_in_clean":"PENDING_CONTROLLER_PLATE_ONLY_NATIVE_VISUAL"},
"persisted_machine":{"header_exact":True,"size_exact":True,"decoded_roundtrip_exact":True,
"changed_rgba_pixels":int(changed.sum()),"visible_candidate_pixels":visible_count},
"producer_visual":"PENDING_CONTROLLER_SOURCE_CLEAN_FINAL_AND_NATIVE_PRACTICAL",
"candidate_promoted":False,"C1":"NOT_RUN","C3":"NOT_RUN","USER":"NOT_RUN",
"RUNTIME_VALIDATION":"UNTESTED","backend":"GITHUB_HOSTED_REQUIRED_PINNED_PUBLIC_SOURCE",
"forbidden_domains_touched":[]}
(OUT/"B284_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B284","trial_sha256":SHA(trial),"rows":len(entries),"protected_changed":outside,"visible":visible_count},ensure_ascii=False))
