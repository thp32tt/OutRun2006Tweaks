#!/usr/bin/env python3
import base64, hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261006-B-PRODUCTION157-JENN"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA="cd6f58f1fa187c6ff7813cbb42b5181038712d8142bf575711a30d69e76d2f4a"
INVENTORY_ARCHIVE_SHA="e02db9b4e04747e2a74295e8f5a01e07f0ed88d31832f4169b1e5996bc30f1eb"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_B157"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"JENN_HD.dds"; atlas=tmp/"JENN_HD_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_JENN_RANK_Exst/4x_06AB5CEE_1024x1024_atlas.json",atlas)

def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(im): return im.point(lambda v:255 if v else 0)
def count(im): return sum(im.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(62,62,62,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64(im,jpg,b64,quality=94):
    im.convert("RGB").save(jpg,quality=quality,optimize=True)
    b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

sb=dds.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(4096,4096) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs={int(r["idx"]):r for r in json.loads(atlas.read_text())["regions"]}
expected_cells={
 1:[1088,3080,2048,1016],
 2:[0,1488,1720,1016],
 3:[1720,1488,1640,1016],
}
for idx,rect in expected_cells.items():
    if list(map(int,regs[idx]["rect"]))!=rect: raise RuntimeError(("atlas drift",idx,regs[idx]["rect"]))

# Two already C-approved source-faithful template families:
# C202: pink speech bubble + warm starburst; C206: green speech bubble.
b148=repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE"
b152=repo/"localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7"
c202=json.loads((repo/"localization/graphics/role_C/20261005-C202-8215FD25/C202_8215FD25_CONTROLLER_FINAL_QA.json").read_text())
c206=json.loads((repo/"localization/graphics/role_C/20261005-C206-DCC7B488/C206_DCC7B488_CONTROLLER_FINAL_QA.json").read_text())
if c202.get("decision")!="C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME": raise RuntimeError(("C202 drift",c202.get("decision")))
if c206.get("decision")!="C206_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME": raise RuntimeError(("C206 drift",c206.get("decision")))

r148=json.loads((b148/"B148_8215_REPORT.json").read_text())
r152=json.loads((b152/"B152_DCC7_REPORT.json").read_text())
templates={
 1:{
   "name":"C202 warm starburst",
   "approval":"C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
   "source":Image.open(b148/"B148_SOURCE_READABLE.png").convert("RGBA"),
   "clean":Image.open(b148/"B148_CLEAN_PLATE.png").convert("RGBA"),
   "final":Image.open(b148/"B148_FINAL_READABLE.png").convert("RGBA"),
   "row":next(r for r in r148["rows"] if int(r["region_idx"])==1),
 },
 2:{
   "name":"C202 pink speech bubble",
   "approval":"C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
   "source":Image.open(b148/"B148_SOURCE_READABLE.png").convert("RGBA"),
   "clean":Image.open(b148/"B148_CLEAN_PLATE.png").convert("RGBA"),
   "final":Image.open(b148/"B148_FINAL_READABLE.png").convert("RGBA"),
   "row":next(r for r in r148["rows"] if int(r["region_idx"])==2),
 },
 3:{
   "name":"C206 green speech bubble",
   "approval":"C206_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
   "source":Image.open(b152/"B152_SOURCE_READABLE.png").convert("RGBA"),
   "clean":Image.open(b152/"B152_CLEAN_PLATE.png").convert("RGBA"),
   "final":Image.open(b152/"B152_FINAL_READABLE.png").convert("RGBA"),
   "row":r152["rows"][0],
 },
}

clean_arr=sa.copy()
final_arr=sa.copy()
allowed=Image.new("L",(W,H),0)
row_reports=[]
template_reports=[]

for idx in (1,2,3):
    t=templates[idx]; row=t["row"]
    tc=list(map(int,row["cell"])); dc=expected_cells[idx]
    if tc[2:]!=dc[2:]: raise RuntimeError(("template cell size mismatch",idx,tc,dc))
    dx=dc[0]-tc[0]; dy=dc[1]-tc[1]
    ob=list(map(int,row["original_bbox"]))
    core=list(map(int,row["source_core_bbox"]))
    loc=list(map(int,row["localized_bbox"]))
    dob=[ob[0]+dx,ob[1]+dy,ob[2]+dx,ob[3]+dy]
    dcore=[core[0]+dx,core[1]+dy,core[2]+dx,core[3]+dy]
    dloc=[loc[0]+dx,loc[1]+dy,loc[2]+dx,loc[3]+dy]
    for b in (dob,dcore,dloc):
        if not(0<=b[0]<b[2]<=W and 0<=b[1]<b[3]<=H): raise RuntimeError(("bbox",idx,b))

    ts=np.asarray(t["source"],dtype=np.uint8)
    tcarr=np.asarray(t["clean"],dtype=np.uint8)
    tf=np.asarray(t["final"],dtype=np.uint8)
    sp=ts[ob[1]:ob[3],ob[0]:ob[2]]
    cp=tcarr[ob[1]:ob[3],ob[0]:ob[2]]
    fp=tf[ob[1]:ob[3],ob[0]:ob[2]]
    tp=sa[dob[1]:dob[3],dob[0]:dob[2]]
    if sp.shape!=tp.shape: raise RuntimeError(("patch shape",idx,sp.shape,tp.shape))

    removal=np.any(sp!=cp,axis=2)
    render=np.any(cp!=fp,axis=2)
    variant=np.any(sp!=tp,axis=2)
    outside=variant & (~removal)
    oy,ox=np.nonzero(outside)
    unsafe=[]
    variant_rgba=[]
    for yy,xx in zip(oy,ox):
        a=tp[yy,xx].tolist(); b=sp[yy,xx].tolist()
        if len(variant_rgba)<32: variant_rgba.append({"target":a,"template":b})
        low_alpha=(a[3]<=16 or b[3]<=16)
        light=(max(a[:3])>=210 or max(b[:3])>=210)
        if not (low_alpha and light): unsafe.append((int(xx),int(yy),a,b))
    if unsafe:
        raise RuntimeError(("non-title variant outside approved removal",idx,len(unsafe),unsafe[:8]))
    if len(ox)>128:
        raise RuntimeError(("too many target-only AA variants",idx,len(ox)))

    clean_mask=removal | outside
    edit_mask=clean_mask | render
    # All template edits must remain inside the exact producer-approved original bbox.
    if not np.any(removal) or not np.any(render): raise RuntimeError(("empty template edit",idx))
    # Apply only the approved title-removal pixels and approved Korean-render pixels.
    # Do NOT copy the whole patch; Jennifer-specific surrounding artwork is retained.
    dest_clean=clean_arr[dob[1]:dob[3],dob[0]:dob[2]]
    dest_final=final_arr[dob[1]:dob[3],dob[0]:dob[2]]
    dest_clean[clean_mask]=cp[clean_mask]
    dest_final[clean_mask]=cp[clean_mask]
    dest_final[render]=fp[render]

    # Exact local gate: every changed pixel must be inside this row's approved bbox.
    ImageDraw.Draw(allowed).rectangle((dob[0],dob[1],dob[2]-1,dob[3]-1),fill=255)

    sw=dcore[2]-dcore[0]; sh=dcore[3]-dcore[1]
    lw=dloc[2]-dloc[0]; lh=dloc[3]-dloc[1]
    if not(dloc[0]>dcore[0] and dloc[1]>dcore[1] and dloc[2]<dcore[2] and dloc[3]<dcore[3] and lw<=sw and lh<=sh):
        raise RuntimeError(("bbox gate",idx,dcore,dloc))

    template_reports.append({
      "target_region_idx":idx,"template":t["name"],"approval":t["approval"],
      "template_cell":tc,"target_cell":dc,"shift":[dx,dy],
      "approved_original_bbox":dob,"source_core_bbox":dcore,"localized_bbox":dloc,
      "template_removal_pixels":int(np.count_nonzero(removal)),
      "template_render_pixels":int(np.count_nonzero(render)),
      "target_vs_template_variant_pixels":int(np.count_nonzero(variant)),
      "target_variant_outside_removal_pixels":int(np.count_nonzero(outside)),
      "target_variant_outside_removal_rgba":variant_rgba,
      "unsafe_variant_pixels":0,
      "preserve_target_pixels_outside_edit_mask":int(np.count_nonzero(~edit_mask)),
    })
    row_reports.append({
      "region_idx":idx,"source":"Total Rank","korean":"종합 랭킹","cell":dc,
      "original_bbox":dob,"source_core_bbox":dcore,"localized_bbox":dloc,
      "source_width":sw,"source_height":sh,"localized_width":lw,"localized_height":lh,
      "delta_left":dloc[0]-dcore[0],"delta_right":dcore[2]-dloc[2],
      "delta_top":dloc[1]-dcore[1],"delta_bottom":dcore[3]-dloc[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font_file":row.get("font_file"),"font_style":row.get("font_style"),
      "font_size":row.get("font_size"),"stroke_width":row.get("stroke_width"),
      "slant":row.get("slant"),"fill_rgba":row.get("fill_rgba"),
      "outline_rgba":row.get("outline_rgba"),"alignment":"center",
      "template_approval":t["approval"],
    })

clean=Image.fromarray(clean_arr,"RGBA")
final=Image.fromarray(final_arr,"RGBA")
protected=ImageOps.invert(allowed)

# Ensure the three localized footprints do not overlap or touch.
for i,a in enumerate(row_reports):
    ax0,ay0,ax1,ay1=a["localized_bbox"]
    for b in row_reports[i+1:]:
        bx0,by0,bx1,by1=b["localized_bbox"]
        if not(ax1<bx0-1 or bx1<ax0-1 or ay1<by0-1 or by1<ay0-1):
            raise RuntimeError(("localized overlap/touch",a["region_idx"],b["region_idx"]))

# Exact DDS roundtrip preserving canonical header/raw mirror_y.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload)
csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")

diff=diffmask(src,dec)
outside=count(ImageChops.multiply(diff,protected))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),protected))
if outside or alphaout: raise RuntimeError(("outside gate",outside,alphaout))

# Validation reports over the exact union of the three source-effect bboxes.
source_png=out/"B157_SOURCE_READABLE.png"; clean_png=out/"B157_CLEAN_PLATE.png"; final_png=out/"B157_FINAL_READABLE.png"
ap=out/"B157_ALLOWED_EFFECT_BBOX_MASK.png"; pp=out/"B157_PROTECTED_MASK.png"
src.save(source_png); clean.save(clean_png); dec.save(final_png); allowed.save(ap); protected.save(pp)
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B157_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(ap),"--protected-mask",str(pp),"--report",str(out/"B157_FINAL_VALIDATION.json")],check=True)
cr=json.loads((out/"B157_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"B157_FINAL_VALIDATION.json").read_text())
if cr["status"]!="PASS" or fr["status"]!="PASS": raise RuntimeError(("validator",cr["status"],fr["status"]))

# Per-row readable SOURCE/CLEAN/FINAL contact evidence.
for rr in row_reports:
    x0,y0,x1,y1=rr["original_bbox"]; pad=80
    box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    ims=[comp(z.crop(box)) for z in (src,clean,dec)]
    scale=min(2.4,1500/max(1,ims[0].width))
    ims=[z.resize((max(1,int(z.width*scale)),max(1,int(z.height*scale))),Image.Resampling.NEAREST) for z in ims]
    card=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+44),"white"); xx=0
    for lab,z in zip(("SOURCE","CLEAN","FINAL"),ims):
        card.paste(z,(xx,44)); ImageDraw.Draw(card).text((xx+5,8),lab,fill="black"); xx+=z.width+8
    save_b64(card,out/f"B157_IDX{rr['region_idx']}_FOCUS.jpg",out/f"B157_IDX{rr['region_idx']}_FOCUS_B64.txt",95)

# Full readable SOURCE/CLEAN/FINAL and raw mirror_y evidence.
overview=Image.new("RGB",(1200,3*1230),"white")
for i,(lab,im) in enumerate((("SOURCE",src),("CLEAN",clean),("FINAL",dec))):
    z=comp(im); z.thumbnail((1200,1200),Image.Resampling.LANCZOS)
    overview.paste(z,(0,i*1230+26)); ImageDraw.Draw(overview).text((5,i*1230+5),lab,fill="black")
save_b64(overview,out/"B157_JENN_SOURCE_CLEAN_FINAL.jpg",out/"B157_JENN_SOURCE_CLEAN_FINAL_B64.txt",92)

raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
raw_sheet=Image.new("RGB",(1200,2*1230),"white")
for i,(lab,im) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
    z=comp(im); z.thumbnail((1200,1200),Image.Resampling.LANCZOS)
    raw_sheet.paste(z,(0,i*1230+26)); ImageDraw.Draw(raw_sheet).text((5,i*1230+5),lab,fill="black")
save_b64(raw_sheet,out/"B157_JENN_RAW_COMPARE.jpg",out/"B157_JENN_RAW_COMPARE_B64.txt",91)

# Atlas overview identifies the untouched Jennifer/rank/UI regions.
atlas_view=comp(src); d=ImageDraw.Draw(atlas_view)
for idx,r in regs.items():
    x,y,w,h=map(int,r["rect"])
    d.rectangle((x,y,x+w-1,y+h-1),outline="white",width=4)
    d.text((x+6,y+6),f"idx{idx}",fill="white")
atlas_view.thumbnail((1400,1400),Image.Resampling.LANCZOS)
save_b64(atlas_view,out/"B157_JENN_ATLAS.jpg",out/"B157_JENN_ATLAS_B64.txt",91)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":36,"asset":asset,
 "readiness_tier":"ZOOM_REVIEW_POSITIVELY_CLASSIFIED_AND_RENDERED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,
   "upstream_release_filename":"6AB5CEE_1024x1024.dds","source_sha256":SOURCE_SHA,
   "queue_inventory_archive_sha256":INVENTORY_ARCHIVE_SHA,
   "note":"Release HD payload is the authoritative render source; queue inventory hash records the recovered archive copy."},
 "classification":{"prior_action":"zoom_review","localizable":"Total Rank x3","translation":"종합 랭킹",
   "protected":["Jennifer character artwork","lens flare","rank letters A/B/C/D/E","heart/cross UI"]},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,
   "header_128_exact":payload[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "approved_template_reuse":{"method":"copy only already-C-approved title-removal/render pixels; preserve every Jennifer target pixel outside those edit masks",
   "rows":template_reports},
 "rows":row_reports,
 "clean_plate_validator":cr,"final_mask_validator":fr,
 "decoded_changes":{"outside_allowed_effect_bboxes":outside,"alpha_outside":alphaout,
   "localized_overlap":0,"localized_1px_touch":0,"source_script_residue":0},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "worker_static_qa":"PASS","controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "status":"B157_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "runtime_validation":"UNTESTED"
}
(out/"B157_JENN_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B157_06AB5CEE.json").write_text(json.dumps({
 "run":"B157","index":36,"asset":"06AB5CEE","candidate_sha256":csha,
 "localized_physical_elements":3,"bbox_size_positive_margin":"3/3",
 "outside":outside,"alpha_outside":alphaout,
 "worker_status":report["status"],"report":f"localization/graphics/role_B/{run}/B157_JENN_REPORT.json",
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B157","candidate_sha256":csha,"rows":3,"bbox":"3/3 PASS","outside":outside,"alpha_outside":alphaout,
  "variant_outside_removal":[x["target_variant_outside_removal_pixels"] for x in template_reports]},ensure_ascii=False),flush=True)
