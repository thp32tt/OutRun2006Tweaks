#!/usr/bin/env python3
# B230: q232 EBFC709F localization-coverage repair.
# Current PRE_INGAME #019 shows both ordinary explanatory sentences still English.
# Preserve B219's four approved Korean headings and modify only the two exact help-line bboxes.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

repo=Path.cwd()
run="20261007-B-MANUALQA230-EBFC709F-HELP"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
validator=repo/"tools/localization/validate_clean_plate.py"
SOURCE_SHA="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0"
EXPECTED_BEFORE="54ed1e64dde7be9686b882748ab934d3e465d9966289c6ec7772daeeef8f7221"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit+"/Release/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"
tmp=Path("/tmp/b230"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(url,src_dds)

# B219/C225R exact source heading bboxes. These are already intentionally localized and are
# part of the total source-vs-final allowed set, but NOT part of B230's rework blast radius.
heading_bboxes=[
 [14,287,418,350],
 [898,291,1420,354],
 [24,695,1245,840],
 [9,874,979,1019],
]
help_specs=[
 {"key":"create_help","source":"Create a game and invite your friends!","ko":"게임을 만들고 친구를 초대하세요!","window":[0,360,1250,450]},
 {"key":"join_help","source":"Join your friends in a game of OutRun!","ko":"친구들과 OutRun 게임에 참가하세요!","window":[0,500,1650,620]},
]

def sha(b): return hashlib.sha256(b).hexdigest()
def rect(shape,b):
    m=np.zeros(shape,dtype=bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=True; return m
def bbox(m):
    ys,xs=np.nonzero(m); return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(2048,1024) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"mips":mips,"raw_mode":mode}
def binmask(im): return im.point(lambda p:255 if p else 0)
def count(im): return sum(im.histogram()[1:])
def changed_mask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for band in bands[1:]: m=ImageChops.lighter(m,band)
    return binmask(m)
def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=src_dds.read_bytes(); oldb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source sha drift",sha(sb),SOURCE_SHA))
if sha(oldb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha(oldb),EXPECTED_BEFORE))
src_raw,src,meta=decode(sb); old_raw,old,ometa=decode(oldb)
if meta!=ometa or sb[:128]!=oldb[:128]: raise RuntimeError("structure/header drift")
sa=np.asarray(src); oa=np.asarray(old); H,W=sa.shape[:2]
source_alpha=sa[:,:,3]>0

# Discover exact help-line source-alpha bboxes inside two narrow semantic windows.
# Fail closed if geometry no longer resembles the known two explanatory rows or if B219 changed them.
for spec in help_specs:
    wx0,wy0,wx1,wy1=spec["window"]
    wm=np.zeros((H,W),dtype=bool); wm[wy0:wy1,wx0:wx1]=source_alpha[wy0:wy1,wx0:wx1]
    bb=bbox(wm)
    if bb is None: raise RuntimeError(("missing help source row",spec["key"],spec["window"]))
    sw,sh=bb[2]-bb[0],bb[3]-bb[1]
    if not (450<=sw<=1500 and 40<=sh<=90):
        raise RuntimeError(("unexpected help geometry",spec["key"],bb,[sw,sh]))
    # C225R explicitly preserved these English sentences. Assert exact candidate equality in the
    # semantic window before rework so B230 cannot overwrite concurrent/unmapped content.
    if not np.array_equal(oa[wy0:wy1,wx0:wx1],sa[wy0:wy1,wx0:wx1]):
        raise RuntimeError(("precondition help window no longer source-exact",spec["key"],bb))
    spec["bbox"]=bb
    spec["source_size"]=[sw,sh]
    spec["source_alpha_pixels"]=int(np.count_nonzero(source_alpha & rect((H,W),bb)))

# Total source-vs-final allowance includes prior four headings and these two help rows.
allowed=np.zeros((H,W),dtype=bool)
for b in heading_bboxes: allowed |= rect((H,W),b)
rework=np.zeros((H,W),dtype=bool)
for spec in help_specs:
    rb=rect((H,W),spec["bbox"]); allowed|=rb; rework|=rb

# Clean only exact source-visible help pixels from the current B219 candidate; everything else
# (including the four Korean headings) remains byte/pixel exact to the prior candidate.
clean=old.copy(); ca=np.array(clean)
source_help=np.zeros((H,W),dtype=bool)
for spec in help_specs:
    bm=source_alpha & rect((H,W),spec["bbox"]); source_help|=bm; ca[bm]=[0,0,0,0]
clean=Image.fromarray(ca.astype(np.uint8),"RGBA")

# Source-visible protected content outside the total six text bboxes.
protected=source_alpha & ~allowed

# Save validator inputs.
sp=tmp/"source.png"; op=tmp/"baseline.png"; cp=out/"B230_EBFC_HELP_CLEAN_PLATE.png"
ap=out/"B230_EBFC_TOTAL_ALLOWED_MASK.png"; rp=out/"B230_EBFC_REWORK_MASK.png"; pp=out/"B230_EBFC_PROTECTED_MASK.png"
src.save(sp); old.save(op); clean.save(cp)
Image.fromarray((allowed*255).astype(np.uint8),"L").save(ap)
Image.fromarray((rework*255).astype(np.uint8),"L").save(rp)
Image.fromarray((protected*255).astype(np.uint8),"L").save(pp)

subprocess.run(["python3",str(validator),str(sp),str(cp),str(ap),
 "--protected-mask",str(pp),"--baseline-candidate",str(op),"--rework-mask",str(rp),
 "--report",str(out/"B230_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B230_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validator",cleanrep))
if np.count_nonzero(np.asarray(clean)[:,:,3][source_help]): raise RuntimeError("source help alpha remains after clean")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Bold"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("Noto CJK Bold unavailable",font_line))

def sample_fill(spec):
    b=spec["bbox"]; x0,y0,x1,y1=b
    p=sa[y0:y1,x0:x1]
    vis=p[p[:,:,3]>=220]
    if len(vis)<100: raise RuntimeError(("fill sample too small",spec["key"],len(vis)))
    rgb=np.median(vis[:,:3],axis=0).round().astype(np.uint8)
    return tuple(int(x) for x in rgb)+(255,)

def render(text,fs,fill,xscale=0.92):
    font=ImageFont.truetype(FONT,fs,index=FI)
    d=ImageDraw.Draw(Image.new("L",(4,4),0))
    tb=d.textbbox((0,0),text,font=font,stroke_width=0)
    pad=8
    m=Image.new("L",(max(8,tb[2]-tb[0]+2*pad),max(8,tb[3]-tb[1]+2*pad)),0)
    ImageDraw.Draw(m).text((pad-tb[0],pad-tb[1]),text,font=font,fill=255)
    bb=m.getbbox()
    if not bb: raise RuntimeError(("empty render",text,fs))
    m=m.crop(bb)
    if xscale!=1.0:
        m=m.resize((max(1,int(round(m.width*xscale))),m.height),Image.Resampling.LANCZOS)
    tile=Image.new("RGBA",m.size,fill); tile.putalpha(m)
    return tile

# Source family is dark, upright, left-anchored, condensed explanatory text.
# Preserve height first and use a shared <=0.92 width profile; never stretch toward English width.
MARGIN=2
final=clean.copy(); target_masks=[]; row_reports=[]
for spec in help_specs:
    b=spec["bbox"]; aw=b[2]-b[0]; ah=b[3]-b[1]; fill=sample_fill(spec)
    best=None
    for fs in range(min(100,ah+20),20,-1):
        # shared source-family condensation starts at 0.92; reduce only if exact width requires it
        for xs in (0.92,0.90,0.88,0.86,0.84,0.82):
            tile=render(spec["ko"],fs,fill,xs)
            if tile.width<=aw-2*MARGIN and tile.height<=ah-2*MARGIN:
                best=(fs,xs,tile); break
        if best: break
    if best is None: raise RuntimeError(("native help fit failed",spec["key"],b,spec["ko"]))
    fs,xs,tile=best
    px=b[0]+MARGIN
    py=b[1]+(ah-tile.height)//2
    py=max(b[1]+MARGIN,min(py,b[3]-MARGIN-tile.height))
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0; lb=bbox(lm)
    margins=[lb[0]-b[0],b[2]-lb[2],lb[1]-b[1],b[3]-lb[3]]
    if min(margins)<=0: raise RuntimeError(("positive margin",spec["key"],lb,b,margins))
    # Zero overlap against all preserved visible candidate pixels.
    preserved=(oa[:,:,3]>0) & ~source_help
    if np.count_nonzero(lm & preserved):
        raise RuntimeError(("localized help overlaps preserved content",spec["key"],int(np.count_nonzero(lm&preserved))))
    final.alpha_composite(layer); target_masks.append(lm)
    row_reports.append({**spec,"localized_bbox":lb,"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
      "margins":margins,"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,
      "font_size":fs,"horizontal_scale":xs,"fill_rgba":list(fill),"alignment":"source_left",
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

if np.count_nonzero(target_masks[0] & target_masks[1]):
    raise RuntimeError("help rows overlap")

# Persist exact DDS bytes, then decode FROM PERSISTED BYTES for authoritative final QA.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",meta["raw_mode"])
candidate.write_bytes(payload)
after=sha(payload)
persisted=candidate.read_bytes()
new_raw,new,nmeta=decode(persisted)
if sha(persisted)!=after or nmeta!=meta or persisted[:128]!=sb[:128]:
    raise RuntimeError("persisted DDS structure/hash mismatch")
if ImageChops.difference(new,final).getbbox() is not None:
    raise RuntimeError("uncompressed persisted DDS differs from intended render")

np_new=np.asarray(new)
old_diff=np.any(oa!=np_new,axis=2)
blast_out=int(np.count_nonzero(old_diff & ~rework))
blast_alpha_out=int(np.count_nonzero((oa[:,:,3]!=np_new[:,:,3]) & ~rework))
if blast_out or blast_alpha_out: raise RuntimeError(("blast radius",blast_out,blast_alpha_out))

fp=tmp/"persisted_final.png"; new.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),
 "--protected-mask",str(pp),"--baseline-candidate",str(op),"--rework-mask",str(rp),
 "--report",str(out/"B230_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B230_FINAL_VALIDATION.json").read_text())
if finalrep["status"]!="PASS": raise RuntimeError(("final validator",finalrep))

# Coverage gate: exactly the two newly identified ordinary UI sentences are now Korean.
# Headings were already localized and remain exact outside the two help bboxes.
if not np.array_equal(oa[~rework],np_new[~rework]):
    raise RuntimeError("baseline drift outside rework mask")

# Post-encode practical-scale evidence from PERSISTED decoded DDS.
source_rgb,old_rgb,clean_rgb,new_rgb=map(comp,(src,old,clean,new))
def crop_pad(im,b,p=8):
    x0,y0,x1,y1=b; return im.crop((max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p)))
cards=[]
for rr in row_reports:
    b=rr["bbox"]
    src_c,old_c,clean_c,new_c=[crop_pad(z,b) for z in (source_rgb,old_rgb,clean_rgb,new_rgb)]
    for scale in (1.0,0.75,0.5):
        ims=[]
        for z in (src_c,old_c,clean_c,new_c):
            ims.append(z.resize((max(1,int(round(z.width*scale))),max(1,int(round(z.height*scale)))),Image.Resampling.LANCZOS))
        cw=sum(z.width for z in ims)+18; ch=max(z.height for z in ims)+28
        c=Image.new("RGB",(cw,ch),(22,22,22)); d=ImageDraw.Draw(c); xx=0
        for lab,z in zip(("SOURCE","C225R","CLEAN","B230"),ims):
            d.text((xx+3,5),f"{lab} {int(scale*100)}%",fill="white"); c.paste(z,(xx,26)); xx+=z.width+6
        cards.append(c)
maxw=max(c.width for c in cards)
sheet=Image.new("RGB",(maxw,sum(c.height for c in cards)+4*(len(cards)-1)),(18,18,18)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((3600,5000),Image.Resampling.LANCZOS)
sheet.save(out/"B230_EBFC_HELP_PRACTICAL_SCALE_CONTACT.jpg","JPEG",quality=95,subsampling=0)

# Full decoded readable and RAW comparisons.
def fullcard(label,im):
    z=comp(im).resize((1024,512),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(1024,540),(24,24,24)); c.paste(z,(0,28)); ImageDraw.Draw(c).text((6,6),label,fill="white"); return c
cards2=[fullcard("ENGLISH SOURCE",src),fullcard("C225R CURRENT",old),fullcard("B230 CLEAN",clean),fullcard("B230 PERSISTED FINAL",new)]
overview=Image.new("RGB",(2048,1080),(20,20,20))
overview.paste(cards2[0],(0,0));overview.paste(cards2[1],(1024,0));overview.paste(cards2[2],(0,540));overview.paste(cards2[3],(1024,540))
overview.save(out/"B230_EBFC_SOURCE_OLD_CLEAN_FINAL.jpg","JPEG",quality=95,subsampling=0)

rawsheet=Image.new("RGB",(2048,540),(20,20,20))
rawsheet.paste(fullcard("SOURCE RAW MIRROR_Y",src_raw),(0,0)); rawsheet.paste(fullcard("B230 RAW MIRROR_Y",new_raw),(1024,0))
rawsheet.save(out/"B230_EBFC_RAW_COMPARE.jpg","JPEG",quality=95,subsampling=0)

target=Image.new("L",(W,H),0)
for lm in target_masks: target=ImageChops.lighter(target,Image.fromarray((lm*255).astype(np.uint8),"L"))
target.save(out/"B230_EBFC_HELP_TARGET_MASK.png")

report={
 "schema_version":1,"role":"B","run":run,"queue_index":232,"asset":asset,
 "trigger":"PRE_INGAME_019_LOCALIZATION_COVERAGE_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/019_q232_EBFC709F.jpg",
 "prior_c_status":"C225R_PIXEL_VISUAL_POLICY_PASS_PENDING_USER_JPG_AND_INGAME",
 "source_sha256":SOURCE_SHA,"before_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "defect":["UNTRANSLATED_VISIBLE_UI_CREATE_HELP","UNTRANSLATED_VISIBLE_UI_JOIN_HELP"],
 "semantic_binding":[{"source":x["source"],"korean":x["ko"]} for x in row_reports],
 "brand_policy":"OutRun retained in English inside the Korean explanatory sentence",
 "method":"current C225R candidate + exact canonical source alpha help rows; clear only exact source-visible help pixels; native Noto Sans CJK KR Bold rerender; prior four B219 headings preserved pixel-exact",
 "rows":row_reports,
 "ui_family_style_profile":{"family":"EBFC small dark explanatory UI","font_impression":"bold condensed sans","slant":"upright",
   "alignment":"source_left","fill":"sampled exact source dark-gray per row","outline":"none","shadow_glow":"none",
   "horizontal_profile":"shared 0.92 condensation, reduced only if exact source width requires"},
 "machine_qa":{"bbox_source_size_positive_margin":"2/2 PASS","clean_validator":cleanrep["status"],
   "final_validator":finalrep["status"],"baseline_changes_outside_rework_mask":blast_out,
   "baseline_alpha_changes_outside_rework_mask":blast_alpha_out,"clean_source_help_alpha_remaining":0,
   "localized_help_overlap":0,"header_128_exact":persisted[:128]==sb[:128],"raw_mode":meta["raw_mode"],
   "raw_orientation":"mirror_y","persisted_decode_matches_intended":"PASS","mip_count":meta["mips"],
   "mip_review":"PASS_LEVEL0_ONLY_NO_AUTHORED_EXTRA_MIPS"},
 "post_encode_presentation_gate":{"decoded_persisted_dds_authority":"PASS","practical_scales":["100%","75%","50%"],
   "family_profile":"RECORDED","rework_blast_radius":"PASS_ZERO_OUTSIDE_EXACT_TWO_HELP_BBOXES",
   "coverage":"PASS_6_PHYSICAL_LOCALIZED_TEXT_OCCURRENCES_ACROSS_4_SEMANTIC_SEGMENTS",
   "mandatory_c3":"REQUIRED_BEFORE_PRE_INGAME_EXPORT_DUE_PRIOR_STYLE_FALSE_NEGATIVE_HISTORY"},
 "ordered_generation_gate":{"1_plate_restoration":"PASS_TRANSPARENT_HELP_PLATE","2_slant_direction":"PASS_SOURCE_UPRIGHT",
   "3_no_unnecessary_undersizing":"PASS_MAX_NATIVE_HEIGHT_WITH_SOURCE_CONDENSED_PROFILE",
   "4_source_weight_outline_shadow":"PASS_DARK_BOLD_NO_EXTRA_EFFECTS","5_no_clipping":"PASS_2_OF_2_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_BASELINE_AND_PROTECTED_OUTSIDE_ZERO","7_flip_y_raw":"EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER"},
 "controller_visual_qa":"PENDING_CONTROLLER",
 "status":"B230_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_FRESH_C_C3",
 "RUNTIME_VALIDATION":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True
}
report_path=out/"B230_EBFC_REPORT.json"; report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"role":"B","run":run,"queue_index":232,"asset":"EBFC709F","source_sha256":SOURCE_SHA,
 "before_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":after,"new_visible_ui_rows":2,
 "bbox_size_positive_margin":"2/2","blast_outside":blast_out,"alpha_blast_outside":blast_alpha_out,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":str(report_path.relative_to(repo))}
(wr/"B230_EBFC709F.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
