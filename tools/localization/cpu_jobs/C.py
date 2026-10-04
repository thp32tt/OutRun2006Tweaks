#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C133-1762489B"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/1762489B_512x128.dds"
bdir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION46"
brep=json.loads((bdir/"B_PRODUCTION46_176_REPORT.json").read_text(encoding="utf-8"))
expected_input="cd066bd26952f6b9d20cf604919baa38ac1f0e74492d9f75ee6001e908b37d89"
candidate=repo/brep["candidate_path"]

def sha(b): return hashlib.sha256(b).hexdigest()

def decode_rgba_dds(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]
    w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]
    if len(b)!=128+w*h*4:
        raise RuntimeError(("unexpected_rgba_size",w,h,mips,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,readable,{"width":w,"height":h,"mipmaps":mips,"format":"RGBA32","raw_orientation":"mirror_y"}

def mask_png(path):
    return np.asarray(Image.open(path).convert("L"))>0

def rect(shape,b):
    h,w=shape
    x0,y0,x1,y1=map(int,b)
    m=np.zeros((h,w),bool)
    m[y0:y1,x0:x1]=True
    return m

def bbox(m):
    yy,xx=np.nonzero(m)
    if not len(xx): return None
    return [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]

def dil(m,px=1):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(px*2+1)))>0

source_zip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
with zipfile.ZipFile(source_zip) as z:
    sb=z.read(asset)
if sha(sb)!=brep["source_sha256"]:
    raise RuntimeError(("source_sha",sha(sb),brep["source_sha256"]))
ib=candidate.read_bytes()
if sha(ib)!=expected_input or brep["candidate_sha256"]!=expected_input:
    raise RuntimeError(("unexpected_input_candidate",sha(ib),brep["candidate_sha256"]))

src_raw,src_img,meta=decode_rgba_dds(sb)
old_raw,old_img,old_meta=decode_rgba_dds(ib)
if meta!=old_meta or meta["width"]!=2048 or meta["height"]!=512:
    raise RuntimeError(("structure",meta,old_meta))
if sb[:128]!=ib[:128]:
    raise RuntimeError("header mismatch")

src=np.asarray(src_img,dtype=np.uint8)
old=np.asarray(old_img,dtype=np.uint8)
clean_img=Image.open(bdir/"1762489B_CLEAN_PLATE.png").convert("RGBA")
clean=np.asarray(clean_img,dtype=np.uint8)
source_mask=mask_png(bdir/"1762489B_SOURCE_TEXT_MASK.png")
old_target=mask_png(bdir/"1762489B_TARGET_TEXT_MASK.png")
protected=mask_png(bdir/"1762489B_PROTECTED_MASK.png")
if clean.shape!=src.shape or source_mask.shape!=src.shape[:2] or old_target.shape!=src.shape[:2]:
    raise RuntimeError("evidence shape mismatch")

# Independent C static preflight of the B46 candidate.
allowed=np.zeros(src.shape[:2],bool)
for r in brep["rows"]:
    allowed |= rect(src.shape[:2],r["original_bbox"])
if int(np.count_nonzero(np.any(old!=src,axis=2)&~allowed))!=0:
    raise RuntimeError("B46 changed pixels outside allowed")
if int(np.count_nonzero((old[:,:,3]!=src[:,:,3])&~allowed))!=0:
    raise RuntimeError("B46 alpha changed outside allowed")
if int(np.count_nonzero(np.any(clean!=src,axis=2)&~source_mask))!=0:
    raise RuntimeError("B46 clean changed outside source mask")
if int(np.count_nonzero(source_mask&(clean[:,:,3]>0)))!=0:
    raise RuntimeError("B46 clean source residue")
if int(np.count_nonzero(np.any(old!=src,axis=2)&protected))!=0:
    raise RuntimeError("B46 protected artwork changed")

# C controller visual review identified one style-only defect: the four large source
# course rows share an upright condensed style, but B46 row 4 alone received a strong
# 0.32 right slant from a noisy edge-regression metric. Correct only row 4.
row4=brep["rows"][3]
if row4["source"]!="OUTRUN2SP COURSE" or row4["korean"]!="아웃런2 SP 코스":
    raise RuntimeError(("unexpected_row4_semantics",row4["source"],row4["korean"]))
if abs(float(row4["slant"])-0.32)>1e-9:
    raise RuntimeError(("unexpected_B46_row4_slant",row4["slant"]))
x0,y0,x1,y1=map(int,row4["original_bbox"])

font_path=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
if not font_path or not Path(font_path).exists() or "NotoSansCJK" not in Path(font_path).name:
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    font_path=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
if not font_path:
    raise RuntimeError("font unavailable")

fs=int(row4["font_size"])
sw=int(row4["stroke_width"])
fill=tuple(int(v) for v in row4["fill"])
outline=tuple(int(v) for v in row4["outline"])
font=ImageFont.truetype(font_path,fs)
d=ImageDraw.Draw(Image.new("L",(8,8),0))
tb=d.textbbox((0,0),row4["korean"],font=font,stroke_width=sw)
pad=sw+4
sz=(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad)
stroke=Image.new("L",sz,0)
fillmask=Image.new("L",sz,0)
pos=(pad-tb[0],pad-tb[1])
ImageDraw.Draw(stroke).text(pos,row4["korean"],font=font,fill=255,stroke_width=sw,stroke_fill=255)
ImageDraw.Draw(fillmask).text(pos,row4["korean"],font=font,fill=255)
tile=Image.new("RGBA",sz,(0,0,0,0))
tile.paste(outline,(0,0),stroke)
tile.paste(fill,(0,0),fillmask)
ab=tile.getchannel("A").getbbox()
if not ab: raise RuntimeError("empty row4 render")
tile=tile.crop(ab)
aw,ah=x1-x0,y1-y0
if tile.width>aw-2 or tile.height>ah-2:
    raise RuntimeError(("row4_not_fit",tile.size,[aw,ah]))
px=x0+(aw-tile.width)//2
py=y0+(ah-tile.height)//2
layer=Image.new("RGBA",(meta["width"],meta["height"]),(0,0,0,0))
layer.alpha_composite(tile,(px,py))
new_row4_mask=np.asarray(layer.getchannel("A"))>0
new_row4_bbox=list(layer.getchannel("A").getbbox())
if new_row4_bbox[0]<=x0 or new_row4_bbox[1]<=y0 or new_row4_bbox[2]>=x1 or new_row4_bbox[3]>=y1:
    raise RuntimeError(("row4_edge_touch",new_row4_bbox,row4["original_bbox"]))

final=old.copy()
final[y0:y1,x0:x1]=clean[y0:y1,x0:x1]
final_img=Image.fromarray(final,"RGBA")
final_img.alpha_composite(layer)
final=np.asarray(final_img,dtype=np.uint8)

new_target=old_target.copy()
new_target[y0:y1,x0:x1]=False
new_target |= new_row4_mask

final_raw=final_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+final_raw.tobytes("raw","RGBA")
candidate.write_bytes(payload)
new_sha=sha(payload)
dec_raw,dec_img,dec_meta=decode_rgba_dds(payload)
dec=np.asarray(dec_img,dtype=np.uint8)
if dec_meta!=meta or payload[:128]!=sb[:128] or not np.array_equal(dec,final):
    raise RuntimeError("DDS roundtrip/header regression")

# Full independent final QA.
changed=np.any(dec!=src,axis=2)
outside=int(np.count_nonzero(changed&~allowed))
alpha_out=int(np.count_nonzero((dec[:,:,3]!=src[:,:,3])&~allowed))
protected_changed=int(np.count_nonzero(changed&protected))
target_out=int(np.count_nonzero(new_target&~allowed))
target_invisible=int(np.count_nonzero(new_target&(dec[:,:,3]==0)))
guard=dil(new_target,2)
residue=int(np.count_nonzero(source_mask&(dec[:,:,3]>0)&~guard))
input_delta=np.any(dec!=old,axis=2)
row4_region=rect(src.shape[:2],row4["original_bbox"])
input_delta_outside_row4=int(np.count_nonzero(input_delta&~row4_region))

rows=[]
row_masks=[]
for rr in brep["rows"]:
    ob=list(map(int,rr["original_bbox"]))
    region=rect(src.shape[:2],ob)
    rm=new_target&region
    lb=bbox(rm)
    sw0,sh0=ob[2]-ob[0],ob[3]-ob[1]
    if lb is None:
        lw=lh=0; contain=size_ok=False; ds=[None]*4
    else:
        lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        contain=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
        size_ok=lw<=sw0 and lh<=sh0
        ds=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    rows.append({
      "n":rr["n"],"source":rr["source"],"korean":rr["korean"],
      "original_bbox":ob,"localized_bbox":lb,
      "source_size":[sw0,sh0],"localized_size":[lw,lh],
      "delta_left":ds[0],"delta_right":ds[1],"delta_top":ds[2],"delta_bottom":ds[3],
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
      "edge_touch_high_risk":bool(lb is not None and any(v==0 for v in ds)),
      "slant":0.0 if rr["n"]==4 else float(rr["slant"]),
      "rework_status":"C133_ROW4_UPRIGHT_STYLE_CORRECTION" if rr["n"]==4 else "C133_PRESERVED_B46"
    })
    row_masks.append(rm)

overlap=0
touch=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        ov=int(np.count_nonzero(row_masks[i]&row_masks[j]))
        near=int(np.count_nonzero(dil(row_masks[i],1)&row_masks[j]))
        overlap+=ov
        if ov or near: touch.append([i+1,j+1,ov,near])

all_rows=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and not r["edge_touch_high_risk"] for r in rows)
ok=(outside==0 and alpha_out==0 and protected_changed==0 and target_out==0 and target_invisible==0
    and residue==0 and input_delta_outside_row4==0 and overlap==0 and not touch and all_rows)
if not ok:
    raise RuntimeError(("C133_QA_FAIL",outside,alpha_out,protected_changed,target_out,target_invisible,residue,input_delta_outside_row4,overlap,touch,rows))

# Evidence.
Image.fromarray((new_target.astype(np.uint8)*255),"L").save(out/"C133_TARGET_TEXT_MASK.png")
Image.fromarray(final,"RGBA").save(out/"C133_FINAL_READABLE.png")

def comp(img,bg=(64,64,64,255)):
    z=Image.new("RGBA",img.size,bg); z.alpha_composite(img); return z.convert("RGB")
def card(label,img,bg=(64,64,64,255)):
    v=comp(img,bg)
    c=Image.new("RGB",(v.width,v.height+26),"white")
    c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="black")
    return c

cards=[card("SOURCE_READABLE",src_img),card("B46_OLD",old_img),card("C133_FINAL",dec_img),card("C133_FINAL_WHITE",dec_img,(255,255,255,255))]
sheet=Image.new("RGB",(meta["width"]*2,(meta["height"]+26)*2),"white")
sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(meta["width"],0))
sheet.paste(cards[2],(0,meta["height"]+26)); sheet.paste(cards[3],(meta["width"],meta["height"]+26))
sheet.thumbnail((1900,1200),Image.Resampling.LANCZOS)
sheet.save(out/"C133_176_COMPARE.jpg",quality=96)

p=14
cr=(max(0,x0-p),max(0,y0-p),min(meta["width"],x1+p),min(meta["height"],y1+p))
rowimgs=[comp(src_img).crop(cr),comp(old_img).crop(cr),comp(dec_img).crop(cr)]
rowimgs=[im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST) for im in rowimgs]
rowcard=Image.new("RGB",(sum(im.width for im in rowimgs)+12,max(im.height for im in rowimgs)+28),"white")
xx=0
for im in rowimgs:
    rowcard.paste(im,(xx,28)); xx+=im.width+6
ImageDraw.Draw(rowcard).text((4,5),"SOURCE | B46 slant=0.32 | C133 slant=0.00 — OUTRUN2SP COURSE -> 아웃런2 SP 코스",fill="black")
rowcard.save(out/"C133_ROW4_SOURCE_OLD_NEW_2X.jpg",quality=96)

raws=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("C133_FINAL_RAW_MIRROR_Y",dec_raw)]
rawsheet=Image.new("RGB",(meta["width"],(meta["height"]+26)*2),"white")
rawsheet.paste(raws[0],(0,0)); rawsheet.paste(raws[1],(0,meta["height"]+26))
rawsheet.thumbnail((1600,1000),Image.Resampling.LANCZOS)
rawsheet.save(out/"C133_176_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"C","run":run,"asset":"1762489B","queue_index":130,
 "producer_run":"B_PRODUCTION46","producer_report":"localization/graphics/role_B/20261005-B-PRODUCTION46/B_PRODUCTION46_176_REPORT.json",
 "input_candidate_sha256":expected_input,"candidate_sha256":new_sha,"candidate_changed_by_C":True,
 "corrective_scope":"row 4 style only: remove spurious B46 0.32 slant; preserve mirror-y orientation, semantics, source masks, clean plate, other four localized rows and protected artwork",
 "source_sha256":brep["source_sha256"],"structure":meta,"header_128_exact":True,
 "machine_checks":{
   "bbox_and_size":"5/5 PASS with positive margins",
   "changed_pixels_outside_original_bboxes":outside,
   "alpha_changed_pixels_outside_original_bboxes":alpha_out,
   "protected_changed_pixels":protected_changed,
   "target_pixels_outside_original_bboxes":target_out,
   "target_mask_pixels_invisible_in_candidate":target_invisible,
   "source_residue_pixels_outside_2px_target_guard":residue,
   "localized_pair_overlap_pixels":overlap,
   "localized_touch_pairs":touch,
   "changes_vs_B46_outside_row4_bbox":input_delta_outside_row4
 },
 "rows":rows,
 "machine_status":"PASS",
 "controller_visual_qa":"PENDING",
 "runtime_validation":"UNTESTED"
}
(out/"C133_176_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
 "run":run,"asset":"1762489B","index":130,"input_candidate_sha256":expected_input,
 "candidate_sha256":new_sha,"candidate_changed_by_C":True,"machine_status":"PASS",
 "bbox_size_pass":"5/5","positive_margin_pass":"5/5","outside":outside,"alpha_outside":alpha_out,
 "protected_changed":protected_changed,"source_residue":residue,"overlap":overlap,"touch_pairs":len(touch),
 "changes_vs_B46_outside_row4_bbox":input_delta_outside_row4,
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C133_176_MACHINE_QA.json"
}
(wr/"C133_1762489B.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
