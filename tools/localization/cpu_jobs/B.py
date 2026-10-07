#!/usr/bin/env python3
# B239: q52 A8CE339F duplicate Start-family consistency repair.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo=Path.cwd()
RUN="20261007-B239-Q052-A8CE339F-START-FAMILY"
out=repo/"localization/graphics/role_B"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_fight_Exst/A8CE339F_512x256.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
cleanp=repo/"localization/graphics/role_B/20261006-B-PRODUCTION176-A8CE339F-DXT5-RESIDUE/B176_CLEAN_PLATE.png"
EXPECTED_PRIOR="d9e590a8e36a735d1edb116ee606aa486e85de8b926bab3a95a741cbfca66fd8"
SOURCE_SHA="08afacc681737d6a138496cefce559853985084cf779921ac32ef2ebfe06883b"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_fight_Exst/A8CE339F_512x256.dds"

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(Path(p).read_bytes())
def meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
    need=128+((w+3)//4)*((h+3)//4)*16
    if fourcc!=b"DXT5" or mips not in (0,1) or len(b)!=need:
        raise RuntimeError(("unexpected DDS",w,h,mips,fourcc,len(b),need))
    return w,h,mips,fourcc

prior_bytes=cand.read_bytes()
if sha_bytes(prior_bytes)!=EXPECTED_PRIOR:
    raise RuntimeError(("candidate drift",sha_bytes(prior_bytes),EXPECTED_PRIOR))
W,H,mips,fourcc=meta(prior_bytes)
if (W,H)!=(2048,1024): raise RuntimeError(("size",W,H))
prior_raw=Image.open(cand).convert("RGBA")
prior=prior_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean=Image.open(cleanp).convert("RGBA")
if clean.size!=(W,H): raise RuntimeError(("clean size",clean.size))

srcp=Path("/tmp/B239_A8CE_source.dds")
urllib.request.urlretrieve(SOURCE_URL,srcp)
if sha_file(srcp)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_file(srcp)))
source_raw=Image.open(srcp).convert("RGBA")
source=source_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# B176 proved these source bboxes and clean plate. Only the right Start is
# reopened: the two identical source Start labels had source boxes 107x41,
# but B176 used 30px / 27px fonts, creating a 60x36 vs 53x31 family mismatch.
left_bb=(24,308,131,349)
right_bb=(801,309,908,350)
goal_left=(649,308,744,349)
goal_right=(1426,308,1521,349)
extra_bb=(16,213,485,284)

# Verify current decoded family mismatch exactly as recorded by B176.
ca=np.asarray(clean)
pa=np.asarray(prior)
def introduced_bbox(im_arr,bb):
    x0,y0,x1,y1=bb
    a=(im_arr[y0:y1,x0:x1,3]>8) & (ca[y0:y1,x0:x1,3]<=1)
    ys,xs=np.nonzero(a)
    if not len(xs): raise RuntimeError(("empty localized bbox",bb))
    return [x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]
left_before=introduced_bbox(pa,left_bb)
right_before=introduced_bbox(pa,right_bb)
if left_before!=[46,310,106,346] or right_before!=[829,314,882,345]:
    raise RuntimeError(("B176 geometry drift",left_before,right_before))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","libnvtt-bin"],check=True)
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
if not FONT.exists(): raise RuntimeError("NotoSansCJK-Bold.ttc missing")
if not Path("/usr/bin/nvcompress").exists(): raise RuntimeError("nvcompress missing")
FONT_INDEX=1

# Reproduce the accepted B176 left-Start native render exactly: same font,
# size, white face, navy outline, no slant. This is a fresh render, not a
# resampled prior Korean bitmap.
font=ImageFont.truetype(str(FONT),30,index=FONT_INDEX)
probe=Image.new("RGBA",(400,160),(0,0,0,0))
d=ImageDraw.Draw(probe)
tb=d.textbbox((0,0),"출발",font=font,stroke_width=3)
pos=(20-tb[0],20-tb[1])
d.text(pos,"출발",font=font,fill=(255,255,255,255),stroke_width=3,stroke_fill=(0,10,65,255))
gb=probe.getchannel("A").getbbox()
glyph=probe.crop(gb)
if glyph.size!=(60,36):
    raise RuntimeError(("font render drift",glyph.size,"expected",(60,36)))

# The right source bbox has a 36px-high complete BC3-safe interior in readable
# orientation: x=804..908, y=312..348. A 60x36 glyph therefore fits natively
# with positive margins against the exact source bbox (3px top, 2px bottom).
safe=(804,312,908,348)
sx0,sy0,sx1,sy1=safe
if glyph.width>sx1-sx0 or glyph.height>sy1-sy0: raise RuntimeError("fresh glyph does not fit safe area")
px=sx0+((sx1-sx0)-glyph.width)//2
py=sy0+((sy1-sy0)-glyph.height)//2
expected_bbox=[px,py,px+glyph.width,py+glyph.height]
if expected_bbox!=[826,312,886,348]:
    raise RuntimeError(("placement drift",expected_bbox))

# Start from exact B176 candidate, restore only the right-Start source bbox
# from the already-validated B176 clean plate, then add fresh matching glyph.
final=prior.copy()
final.paste(clean.crop(right_bb),(right_bb[0],right_bb[1]))
layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(glyph,(px,py))
final.alpha_composite(layer)

# Encode complete raw image, but patch only full BC3 blocks wholly contained in
# the exact right-Start source bbox. Boundary blocks remain B176-exact; B176
# already cleanly removed the English source there.
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/B239_A8CE_raw.png"); tmp_dds=Path("/tmp/B239_A8CE_nv.dds")
raw.save(tmp_png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(tmp_png),str(tmp_dds)],
               check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
enc=tmp_dds.read_bytes(); meta(enc)

# readable [801,309,908,350) -> raw [801,674,908,715)
rx0,ry0,rx1,ry1=right_bb[0],H-right_bb[3],right_bb[2],H-right_bb[1]
bx0=((rx0+3)//4)*4; by0=((ry0+3)//4)*4
bx1=(rx1//4)*4; by1=(ry1//4)*4
if (bx0,by0,bx1,by1)!=(804,676,908,712):
    raise RuntimeError(("raw full-block scope drift",(bx0,by0,bx1,by1)))
outb=bytearray(prior_bytes); bw=W//4
patched=set()
for y in range(by0,by1,4):
    by=y//4
    for x in range(bx0,bx1,4):
        bx=x//4; off=128+(by*bw+bx)*16
        outb[off:off+16]=enc[off:off+16]; patched.add((bx,by))
cand.write_bytes(outb)

new_bytes=cand.read_bytes(); new_sha=sha_bytes(new_bytes)
if new_bytes[:128]!=prior_bytes[:128]: raise RuntimeError("header changed")
new_raw=Image.open(cand).convert("RGBA"); new=new_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
na=np.asarray(new)

# Hard blast-radius gate: nothing may change outside exact right Start bbox.
diff=np.any(pa!=na,axis=2)
alpha_diff=pa[:,:,3]!=na[:,:,3]
allowed=np.zeros((H,W),bool); allowed[right_bb[1]:right_bb[3],right_bb[0]:right_bb[2]]=True
outside=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero(alpha_diff & ~allowed))
if outside or alpha_out: raise RuntimeError(("outside drift",outside,alpha_out))

# Compression gate.
changed_blocks=0; changed_outside=0
for by in range(H//4):
    for bx in range(W//4):
        off=128+(by*bw+bx)*16
        if prior_bytes[off:off+16]!=new_bytes[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patched: changed_outside+=1
if changed_outside: raise RuntimeError(("compressed outside",changed_outside))

left_after=introduced_bbox(na,left_bb)
right_after=introduced_bbox(na,right_bb)
left_size=(left_after[2]-left_after[0],left_after[3]-left_after[1])
right_size=(right_after[2]-right_after[0],right_after[3]-right_after[1])
if left_after!=left_before: raise RuntimeError(("left Start changed",left_before,left_after))
# BC3 alpha may expand by <=1px at edge, but both duplicate Starts must now
# share the same rendered family and near-identical decoded size.
if abs(left_size[0]-right_size[0])>1 or abs(left_size[1]-right_size[1])>1:
    raise RuntimeError(("duplicate family still mismatched",left_size,right_size))
rb=right_after
margins=[rb[0]-right_bb[0],right_bb[2]-rb[2],rb[1]-right_bb[1],right_bb[3]-rb[3]]
if min(margins)<=0: raise RuntimeError(("non-positive margin",margins))
if right_size[0]>(right_bb[2]-right_bb[0]) or right_size[1]>(right_bb[3]-right_bb[1]):
    raise RuntimeError("source size ceiling fail")

# Verify all untouched localized families are pixel-exact to B176.
for name,bb in [("extra_time",extra_bb),("goal_left",goal_left),("goal_right",goal_right),("start_left",left_bb)]:
    a=np.asarray(prior.crop(bb)); b=np.asarray(new.crop(bb))
    if np.any(a!=b): raise RuntimeError(("untouched family changed",name))

# Visual evidence: source / B176 / CLEAN / B239 for both Start rows.
def comp(im,bg=(88,88,88,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im,bb,scale=4):
    x0,y0,x1,y1=bb; pad=20
    cr=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    v=comp(im).crop(cr).resize(((cr[2]-cr[0])*scale,(cr[3]-cr[1])*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+30),"white"); c.paste(v,(0,30))
    ImageDraw.Draw(c).text((6,6),label,fill="black")
    return c
rows=[]
for name,bb in [("START LEFT",left_bb),("START RIGHT",right_bb)]:
    cards=[card(name+" SOURCE",source,bb),card(name+" B176",prior,bb),card(name+" CLEAN",clean,bb),card(name+" B239",new,bb)]
    rw=sum(c.width for c in cards); rh=max(c.height for c in cards)
    rr=Image.new("RGB",(rw,rh),"white"); xx=0
    for c in cards: rr.paste(c,(xx,0)); xx+=c.width
    rows.append(rr)
sw=max(r.width for r in rows); sh=sum(r.height for r in rows)
sheet=Image.new("RGB",(sw,sh),"white"); yy=0
for r in rows: sheet.paste(r,(0,yy)); yy+=r.height
sheet.save(out/"B239_START_FAMILY_SOURCE_B176_CLEAN_FINAL.jpg",quality=96,subsampling=0)

# Full readable and RAW before/after.
def full_card(label,im,maxw=1000):
    rgb=comp(im)
    if rgb.width>maxw:
        nh=round(rgb.height*maxw/rgb.width); rgb=rgb.resize((maxw,nh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(rgb.width,rgb.height+30),"white"); c.paste(rgb,(0,30)); ImageDraw.Draw(c).text((6,6),label,fill="black"); return c
cards=[full_card("SOURCE",source),full_card("B176",prior),full_card("B239",new)]
fs=Image.new("RGB",(sum(c.width for c in cards),max(c.height for c in cards)),"white"); xx=0
for c in cards: fs.paste(c,(xx,0)); xx+=c.width
fs.save(out/"B239_FULL_READABLE.jpg",quality=94)

rawcards=[full_card("SOURCE RAW",source_raw),full_card("B176 RAW",prior_raw),full_card("B239 RAW",new_raw)]
rs=Image.new("RGB",(sum(c.width for c in rawcards),max(c.height for c in rawcards)),"white"); xx=0
for c in rawcards: rs.paste(c,(xx,0)); xx+=c.width
rs.save(out/"B239_RAW.jpg",quality=94)

report={
 "schema_version":2,"role":"B","run":RUN,"queue_index":52,"asset":asset,
 "trigger":"CURRENT_POLICY_FAMILY_CONSISTENCY_FALSE_NEGATIVE_IDENTICAL_START_LABELS_DIFFERENT_FONT_SIZE",
 "source_sha256":SOURCE_SHA,"source_commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "prior_candidate_sha256":EXPECTED_PRIOR,"candidate_sha256":new_sha,
 "prior_family":{"start_left":{"font_size":30,"decoded_bbox":left_before,"decoded_size":list(left_size)},
                 "start_right":{"font_size":27,"decoded_bbox":right_before,"decoded_size":[right_before[2]-right_before[0],right_before[3]-right_before[1]]}},
 "repair":{"scope":"right Start only","korean":"출발","font":"Noto Sans CJK KR Bold","ttc_index":FONT_INDEX,
           "font_size":30,"fill":[255,255,255,255],"outline":[0,10,65,255],"stroke":3,"slant":0.0,
           "fresh_native_glyph_size":list(glyph.size),"expected_native_bbox":expected_bbox,
           "decoded_bbox":right_after,"decoded_size":list(right_size),"margins":margins},
 "machine_qa":{"left_start_pixel_exact_to_B176":left_after==left_before,
               "duplicate_start_decoded_size_delta":[right_size[0]-left_size[0],right_size[1]-left_size[1]],
               "changed_pixels_outside_right_start_bbox":outside,
               "alpha_changed_outside_right_start_bbox":alpha_out,
               "changed_bc3_blocks":changed_blocks,"changed_bc3_blocks_outside_patched_full_blocks":changed_outside,
               "header_128_exact":new_bytes[:128]==prior_bytes[:128],"mip_count":mips,"raw_orientation":"mirror_y",
               "extra_time_goal_left_goal_right_pixel_exact_to_B176":True},
 "ordered_generation_gate":{
   "1_english_removal_plate_restoration":"PASS_REUSE_B176_VALIDATED_CLEAN_PLATE",
   "2_source_matching_slant":"PASS_SOURCE_START_IS_UPRIGHT",
   "3_no_undersized_lettering":"PASS_RIGHT_START_RESTORED_TO_ACCEPTED_LEFT_START_30PX_FAMILY",
   "4_source_faithful_weight_effect":"PASS_MATCHES_LEFT_START_WHITE_NAVY_3PX",
   "5_no_clipped_pixels":"PASS_POSITIVE_SOURCE_BBOX_MARGINS",
   "6_protected_art_clearance":"PASS_ZERO_PIXEL_ALPHA_DRIFT_OUTSIDE_RIGHT_START_BBOX",
   "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_VISUAL_CONFIRM",
   "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_VISUAL_CONFIRM"
 },
 "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
 "status":"B239_WORKER_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA_AND_FRESH_C",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"B239_Q052_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B239_Q052_A8CE339F.json").write_text(json.dumps({
 "role":"B","run":RUN,"queue_index":52,"candidate_sha256":new_sha,
 "report":str((out/"B239_Q052_MACHINE_QA.json").relative_to(repo)),
 "status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"prior":EXPECTED_PRIOR,"candidate":new_sha,
 "left_before":left_before,"right_before":right_before,"left_after":left_after,"right_after":right_after,
 "left_size":left_size,"right_size":right_size,"margins":margins,"outside":outside,"alpha_out":alpha_out,
 "changed_blocks":changed_blocks},ensure_ascii=False))
