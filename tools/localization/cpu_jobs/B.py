#!/usr/bin/env python3
# B223: q112 D41D0B1 strict PRE_INGAME hierarchy rework.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter

repo=Path.cwd()
run="20261007-B-MANUALQA223-D41D0B1"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION43/D41D0B1_CLEAN_PLATE.png"
source_mask_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION43/D41D0B1_SOURCE_TEXT_MASK.png"
EXPECTED_BEFORE="0ac0b2d326914d88f13689eb9be3df6b06111582dd1ba19d2849e7f1be8a8a80"
SOURCE_SHA="524de4c0db3dbb69c6cda484ace71a9213a378e3e4895a035199ced0ac0a3617"
source_commit="a95efe01d1f136514cef94b0d9e9fd61df021754"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+source_commit+"/Release/spr_sprani_selector_cvt_Exst/D41D0B1_512x64.dds"
tmp=Path("/tmp/b223"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(url,src_dds)

ROWS=[
 {"n":1,"source":"Try to reach the goal","korean":"여자친구와 함께","bbox":[435,19,1346,122],"prior_bbox":[604,23,1176,117],"width_ratio":0.80},
 {"n":2,"source":"with your girlfriend.","korean":"골에 도착하세요.","bbox":[499,122,1357,238],"prior_bbox":[638,132,1218,228],"width_ratio":0.80},
]

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_path(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
    need=128+((w+3)//4)*((h+3)//4)*16
    if fourcc!=b"DXT5" or mips not in (0,1) or len(b)!=need:
        raise RuntimeError(("unexpected DDS",w,h,mips,fourcc,len(b),need))
    return w,h,mips,fourcc
def bb(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def shear_rgba(im,s):
    shift=max(0,int(round(s*(im.height-1))))
    o=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for y in range(im.height):
        dx=int(round(s*(im.height-1-y)))
        o.alpha_composite(im.crop((0,y,im.width,y+1)),(dx,y))
    return o

sb=src_dds.read_bytes(); cb=candidate.read_bytes()
if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_bytes(sb)))
if sha_bytes(cb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha_bytes(cb)))
W,H,_,_=meta(sb); W2,H2,_,_=meta(cb)
if (W,H)!=(2048,256) or (W,H)!=(W2,H2): raise RuntimeError(("size",W,H,W2,H2))
src_raw=Image.open(src_dds).convert("RGBA")
old_raw=Image.open(candidate).convert("RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean=Image.open(clean_path).convert("RGBA")
source_mask=Image.open(source_mask_path).convert("L")
if clean.size!=src.size or source_mask.size!=src.size: raise RuntimeError("clean/mask size drift")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","libnvtt-bin"],check=True)
fl=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT,FI,FSTYLE=fl.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("Noto CJK Black unavailable",fl))
if not Path("/usr/bin/nvcompress").exists(): raise RuntimeError("nvcompress unavailable")

# C127/B43 established this source family: white fill + dark navy outline + readable right slant.
WHITE=(255,255,255,255)
NAVY=(2,13,60,255)
FONT_SIZE=83
STROKE=8
SLANT=0.31

def render_native(text):
    f=ImageFont.truetype(FONT,FONT_SIZE,index=FI)
    d=ImageDraw.Draw(Image.new("L",(8,8),0))
    tb=d.textbbox((0,0),text,font=f,stroke_width=STROKE)
    pad=STROKE+8
    tile=Image.new("RGBA",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),(0,0,0,0))
    ImageDraw.Draw(tile).text((pad-tb[0],pad-tb[1]),text,font=f,fill=WHITE,stroke_width=STROKE,stroke_fill=NAVY)
    tile=shear_rgba(tile,SLANT)
    ab=tile.getchannel("A").getbbox()
    if not ab: raise RuntimeError(("empty render",text))
    return tile.crop(ab)

# Build from the validated B43 clean plate only inside the two exact source line bboxes.
# This removes the old Korean bytes before the new wider source-family render is placed.
final=old.copy()
allowed=np.zeros((H,W),bool)
layers=[]
row_reports=[]
for row in ROWS:
    x0,y0,x1,y1=row["bbox"]; sw=x1-x0; sh=y1-y0
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
    tile=render_native(row["korean"])
    target_w=min(sw-8,max(tile.width,round(sw*row["width_ratio"])))
    if target_w!=tile.width:
        tile=tile.resize((target_w,tile.height),Image.Resampling.LANCZOS)
    if tile.width>=sw or tile.height>=sh:
        raise RuntimeError(("size ceiling before place",row["n"],tile.size,[sw,sh]))
    px=x0+(sw-tile.width)//2
    py=y0+(sh-tile.height)//2
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lb=list(layer.getchannel("A").getbbox())
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<=0: raise RuntimeError(("positive margin",row["n"],lb,margins))
    final.alpha_composite(layer); layers.append(layer)
    allowed[y0:y1,x0:x1]=True
    oldw=row["prior_bbox"][2]-row["prior_bbox"][0]; oldh=row["prior_bbox"][3]-row["prior_bbox"][1]
    row_reports.append({
      "n":row["n"],"source":row["source"],"korean":row["korean"],"original_bbox":row["bbox"],
      "source_size":[sw,sh],"prior_localized_bbox":row["prior_bbox"],"prior_localized_size":[oldw,oldh],
      "localized_bbox":lb,"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"margins":margins,
      "width_source_ratio":round((lb[2]-lb[0])/sw,4),"height_source_ratio":round((lb[3]-lb[1])/sh,4),
      "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"font_size":FONT_SIZE,
      "stroke_width":STROKE,"slant":SLANT,"containment":"PASS","size_ceiling":"PASS"
    })

if ImageChops.multiply(layers[0].getchannel("A"),layers[1].getchannel("A")).getbbox():
    raise RuntimeError("localized row overlap")
target=np.zeros((H,W),bool)
for layer in layers: target|=(np.asarray(layer.getchannel("A"))>0)
ys1=row_reports[0]["localized_bbox"][3]; ys2=row_reports[1]["localized_bbox"][1]
row_gap=ys2-ys1
if row_gap<=0: raise RuntimeError(("row gap",row_gap))

# Encode a candidate and replace only fully-inside allowed BC3 blocks in the current C127 bytes.
# Partial boundary blocks remain byte-identical to the already validated C127 candidate.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=tmp/"final_raw.png"; tmp_dds=tmp/"final_nv.dds"
raw_final.save(tmp_png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(tmp_png),str(tmp_dds)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=tmp_dds.read_bytes(); meta(tb)
outb=bytearray(cb)
allowed_raw=np.flipud(allowed)
bw=W//4; bh=H//4
changed_blocks=0
for by in range(bh):
    y=by*4
    if not np.any(allowed_raw[y:y+4]): continue
    for bx in range(bw):
        x=bx*4; am=allowed_raw[y:y+4,x:x+4]
        if not np.all(am): continue
        off=128+(by*bw+bx)*16
        if cb[off:off+16]!=tb[off:off+16]:
            outb[off:off+16]=tb[off:off+16]
            changed_blocks+=1
candidate.write_bytes(outb)
AFTER=sha_bytes(outb)

new_raw=Image.open(candidate).convert("RGBA")
new=new_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
oa=np.asarray(old); na=np.asarray(new); sa=np.asarray(src); ca=np.asarray(clean)
diff=np.any(oa!=na,axis=2)
outside=int(np.count_nonzero(diff & ~allowed))
alpha_out=int(np.count_nonzero((oa[:,:,3]!=na[:,:,3]) & ~allowed))
if outside or alpha_out: raise RuntimeError(("outside candidate change",outside,alpha_out))

# Ensure source residue does not survive away from the new Korean target footprint.
srcm=np.asarray(source_mask)>0
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue=int(np.count_nonzero(srcm & (na[:,:,3]>16) & ~guard))
if residue: raise RuntimeError(("source residue",residue))

# Re-measure decoded current rows from visible alpha in the exact source line bboxes.
for rr in row_reports:
    x0,y0,x1,y1=rr["original_bbox"]
    cm=na[y0:y1,x0:x1,3]>16
    db=bb(cm)
    if db is None: raise RuntimeError(("decoded empty",rr["n"]))
    db=[db[0]+x0,db[1]+y0,db[2]+x0,db[3]+y0]
    dw,dh=db[2]-db[0],db[3]-db[1]
    margins=[db[0]-x0,x1-db[2],db[1]-y0,y1-db[3]]
    if min(margins)<=0 or dw>(x1-x0) or dh>(y1-y0):
        raise RuntimeError(("decoded size",rr["n"],db,margins))
    rr["decoded_localized_bbox"]=db
    rr["decoded_localized_size"]=[dw,dh]
    rr["decoded_margins"]=margins
    rr["decoded_containment"]="PASS"; rr["decoded_size_ceiling"]="PASS"
decoded_gap=row_reports[1]["decoded_localized_bbox"][1]-row_reports[0]["decoded_localized_bbox"][3]
if decoded_gap<=0: raise RuntimeError(("decoded gap",decoded_gap))

# Validation masks/evidence.
allowed_img=Image.fromarray((allowed.astype(np.uint8)*255),"L")
protected_img=Image.fromarray(((~allowed).astype(np.uint8)*255),"L")
target_img=Image.fromarray((target.astype(np.uint8)*255),"L")
allowed_img.save(out/"D41D0B1_ALLOWED_TEXT_REGION_MASK.png")
protected_img.save(out/"D41D0B1_PROTECTED_MASK.png")
target_img.save(out/"D41D0B1_TARGET_TEXT_MASK.png")
source_mask.save(out/"D41D0B1_SOURCE_TEXT_MASK.png")
clean.save(out/"D41D0B1_CLEAN_PLATE.png")
src_png=tmp/"source_readable.png"; new_png=tmp/"new_readable.png"
src.save(src_png); new.save(new_png)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(src_png),str(clean_path),str(source_mask_path),"--report",str(out/"B223_CLEAN_PLATE_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(src_png),str(new_png),str(out/"D41D0B1_ALLOWED_TEXT_REGION_MASK.png"),"--protected-mask",str(out/"D41D0B1_PROTECTED_MASK.png"),"--report",str(out/"B223_FINAL_MASK_VALIDATION.json")],check=True)

# Readable source / C127 / B223 evidence.
def card(label,im):
    v=comp(im)
    c=Image.new("RGB",(v.width,v.height+28),(24,24,24)); c.paste(v,(0,28))
    ImageDraw.Draw(c).text((6,6),label,fill="white")
    return c
cards=[card("SOURCE",src),card("C127",old),card("B223",new)]
sheet=Image.new("RGB",(W,H*3+84),(20,20,20))
for i,c in enumerate(cards): sheet.paste(c,(0,i*(H+28)))
sheet.save(out/"B223_D41_SOURCE_C127_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)

contacts=[]
for rr in row_reports:
    x0,y0,x1,y1=rr["original_bbox"]; p=10
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[comp(z).crop(cr) for z in [src,old,new]]
    ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
    cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+28
    c=Image.new("RGB",(cw,ch),(24,24,24)); d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(["SOURCE","C127","B223"],ims):
        d.text((xx+5,6),lab,fill="white"); c.paste(z,(xx,28)); xx+=z.width+6
    contacts.append(c)
cs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4),(20,20,20)); yy=0
for c in contacts: cs.paste(c,(0,yy)); yy+=c.height+4
cs.save(out/"B223_D41_ROW_CONTACT_2X.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE RAW",src_raw),card("B223 RAW",new_raw)]
rs=Image.new("RGB",(W,H*2+56),(20,20,20))
for i,c in enumerate(rawcards): rs.paste(c,(0,i*(H+28)))
rs.save(out/"B223_D41_SOURCE_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"B","run":"B223","queue_index":112,"asset":asset,
 "trigger":"STRICT_PRE_INGAME_8_STEP_VISUAL_FALSE_NEGATIVE_UNDERSIZED_MULTI_LINE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/014_q112_D41D0B1.jpg",
 "prior_c_status":"C127_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":AFTER,
 "source_url":url,
 "defects":["MULTI_LINE_TEXT_HIERARCHY_UNDERSIZED","SOURCE_RELATIVE_WIDTH_TOO_WEAK"],
 "method":"exact pinned 2048x256 DXT5 source + B43/C127 validated clean plate; fresh native Noto Sans CJK KR Black 83px, source white/navy family and readable right slant; each Korean line widened from fresh native raster to 0.80x exact corresponding source width while preserving independent line centers and source height ceiling; only fully allowed BC3 blocks replaced, partial boundary blocks preserved from C127",
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":1,"raw_orientation":"mirror_y","header_128_exact":bytes(outb[:128])==sb[:128]},
 "rows":row_reports,
 "machine_qa":{"bbox_source_size_positive_margin":"2/2 PASS","decoded_row_gap":decoded_gap,
   "candidate_changes_outside_two_exact_source_bboxes":outside,"alpha_changes_outside_two_exact_source_bboxes":alpha_out,
   "source_residue_pixels_alpha_gt16_outside_2px_target_guard":residue,"localized_overlap_pixels":0,
   "changed_full_bc3_blocks":changed_blocks,"header_exact":bytes(outb[:128])==sb[:128],"raw_orientation":"mirror_y"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_INHERITED_B43_C127_VALIDATED_CLEAN_REVALIDATED",
   "2_slant_direction":"PASS_SOURCE_RIGHT_LEAN_0_31_READABLE",
   "3_no_unnecessary_undersizing":"PASS_WIDTH_HIERARCHY_RESTORED_TO_0_80_SOURCE",
   "4_source_weight_outline_shadow":"PASS_SHARED_WHITE_NAVY_83PX_8PX",
   "5_no_clipping":"PASS_2_OF_2_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_ZERO_CHANGE_OUTSIDE_EXACT_SOURCE_BBOXES",
   "7_flip_y_raw":"PASS_EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER"
 },
 "runtime_validation":"UNTESTED","status":"B223_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B223_D41D0B1_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B223_D41D0B1.json").write_text(json.dumps({"role":"B","run":"B223","queue_index":112,"asset":asset,
 "candidate_sha256":AFTER,"report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B223","before":EXPECTED_BEFORE,"after":AFTER,"rows":[{"n":r["n"],"old":r["prior_localized_size"],"new":r["decoded_localized_size"],"source":r["source_size"],"margins":r["decoded_margins"]} for r in row_reports],"decoded_gap":decoded_gap,"residue":residue,"outside":outside,"status":report["status"]},ensure_ascii=False))
