#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261007-A-MANUALQA156-39BCA907"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/39BCA907_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
work=Path("/tmp/outrun_A156"); work.mkdir(parents=True,exist_ok=True)
EXPECTED_BEFORE="6f59084b340a2a2bc56bd72b276c4cd264aaabfb7e76b013fe190a8f9cb0417b"
MARGIN_X=2
MARGIN_Y=2

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1=None
ATLAS_BLOB_SHA1="60b751126f313f7239d37522a6291c38b782635c"
SOURCE_SHA256=None
ATLAS_SHA256=None
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
source=work/"39BCA907_HD.dds"; atlasp=work/"4x_39BCA907_512x256_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/39BCA907_512x256.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_39BCA907_512x256_atlas.json",atlasp)

def blobsha(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def flatten(im):
    z=Image.new("RGBA",im.size,(72,72,72,255)); z.alpha_composite(im); return z.convert("RGB")
def diffmask(a,b):
    d=ImageChops.difference(a,b); ps=d.split(); m=ps[0]
    for p in ps[1:]: m=ImageChops.lighter(m,p)
    return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])

sb=source.read_bytes(); ab=atlasp.read_bytes()
SOURCE_BLOB_SHA1=blobsha(sb); SOURCE_SHA256=hashlib.sha256(sb).hexdigest()
if blobsha(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError("atlas drift")
ATLAS_SHA256=hashlib.sha256(ab).hexdigest()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(2048,1024,8192,1) or len(sb)!=128+W*H*4 or pf[3]!=32: raise RuntimeError(("structure",W,H,pitch,mips,len(sb)))
rgbm=(pf[4],pf[5],pf[6])
RAWMODE="BGRA" if rgbm==(0xff0000,0xff00,0xff) else "RGBA" if rgbm==(0xff,0xff00,0xff0000) else None
if RAWMODE not in ("RGBA","BGRA"): raise RuntimeError(("rawmode",rgbm))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if not candidate.exists() or sha256(candidate)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift before A156",sha256(candidate) if candidate.exists() else None,EXPECTED_BEFORE))
old_bytes=candidate.read_bytes()
if old_bytes[:128]!=sb[:128] or len(old_bytes)!=len(sb): raise RuntimeError("prior candidate structure drift")
old_raw=Image.frombytes("RGBA",(W,H),old_bytes[128:],"raw",RAWMODE)
old_readable=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
atlas=json.loads(ab.decode("utf-8")); regs={int(r["idx"]):r for r in atlas["regions"]}
if len(regs)!=17: raise RuntimeError(("regions",len(regs)))

# A49 binding: controller visual review of A48 fixed canonical atlas idx->source semantics.
# Region 0 is larger decorative/header artwork and region 16 is an 8px separator; preserve both exactly.
TARGETS={
 1:("TULIP GARDEN","튤립 가든"),
 2:("SNOW MOUNTAIN","스노 마운틴"),
 3:("PALM BEACH","팜 비치"),
 4:("METROPOLIS","메트로폴리스"),
 5:("INDUSTRIAL COMPLEX","인더스트리얼 컴플렉스"),
 6:("IMPERIAL AVENUE","임페리얼 애비뉴"),
 7:("GHOST FOREST","고스트 포레스트"),
 8:("DESERT","데저트"),
 9:("DEEP LAKE","딥 레이크"),
 10:("CONIFEROUS FOREST","코니퍼러스 포레스트"),
 11:("CLOUDY HIGHLAND","클라우디 하이랜드"),
 12:("CASTLE WALL","캐슬 월"),
 13:("CAPE WAY","케이프 웨이"),
 14:("ANCIENT RUINS","에인션트 루인스"),
 15:("ALPINE","알파인"),
}
PROTECTED=[0,16]

def resolve_font():
    pats=["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]
    for install in (False,True):
        for pat in pats:
            try: spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
            except Exception: spec=""
            if "|" in spec:
                fp,ix=spec.rsplit("|",1)
                if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp,int(ix or 0),pat
        if not install:
            subprocess.run(["sudo","apt-get","update","-qq"],check=True)
            subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    raise RuntimeError("font unavailable")
FONT,FONT_INDEX,FONT_PATTERN=resolve_font()

srca=np.asarray(src).copy()
clean_a=srca.copy()
allowed=Image.new("L",(W,H),0); allowed_draw=ImageDraw.Draw(allowed)
source_mask=Image.new("L",(W,H),0)
rows=[]

# First derive exact source glyph/effect alpha bboxes and clean every source pixel.
for idx,(english,korean) in TARGETS.items():
    r=regs[idx]; x,y,w,h=map(int,r["rect"])
    crop=src.crop((x,y,x+w,y+h)); aa=np.asarray(crop.getchannel("A"))
    m=aa>0
    yy,xx=np.where(m)
    if len(xx)==0: raise RuntimeError(("empty target",idx))
    eb=[x+int(xx.min()),y+int(yy.min()),x+int(xx.max())+1,y+int(yy.max())+1]
    mask_full=Image.new("L",(W,H),0); mask_full.paste(Image.fromarray((m*255).astype(np.uint8)),(x,y))
    source_mask=ImageChops.lighter(source_mask,mask_full)
    allowed_draw.rectangle((eb[0],eb[1],eb[2]-1,eb[3]-1),fill=255)
    # Text-only sprite cells: remove every visible source text/effect pixel.
    cy,cx=np.where(m); clean_a[y+cy,x+cx,:]=0

    # Source style statistics, including vertical RGBA profile.
    pix=np.asarray(crop)[m]
    med=np.median(pix,axis=0)
    rows.append({"idx":idx,"source":english,"korean":korean,"source_effect_bbox":eb,
                 "source_width":eb[2]-eb[0],"source_height":eb[3]-eb[1],
                 "source_visible_pixels":int(m.sum()),"source_rgba_median":[int(v) for v in med]})

clean=Image.fromarray(clean_a,"RGBA")
final=clean.copy()

def render_mask(text,bw,bh):
    # A49 forced every Korean row to 92% of the English bbox width. A156 keeps
    # native Hangul aspect and sizes by source HEIGHT, never by a width quota.
    for fs in range(max(24,int(bh*1.45)),20,-1):
        font=ImageFont.truetype(FONT,fs,index=FONT_INDEX)
        stroke=1
        bb=font.getbbox(text,stroke_width=stroke); tw,th=bb[2]-bb[0],bb[3]-bb[1]
        if tw<=0 or th<=0: continue
        pad=stroke+6
        im=Image.new("L",(tw+pad*2,th+pad*2),0); d=ImageDraw.Draw(im)
        d.text((pad-bb[0],pad-bb[1]),text,font=font,fill=255,stroke_width=stroke,stroke_fill=255)
        cb=im.getbbox()
        if not cb: continue
        im=im.crop(cb)
        if im.height>bh-2*MARGIN_Y: continue
        if im.width>bw-2*MARGIN_X:
            maxw=bw-2*MARGIN_X
            im=im.resize((maxw,im.height),Image.Resampling.LANCZOS)
            cb=im.getbbox()
            if cb: im=im.crop(cb)
        if im.width<bw-1 and im.height<bh-1:
            return im,fs,stroke
    raise RuntimeError(("cannot fit native aspect",text,bw,bh))

localized_masks={}
for row in rows:
    idx=row["idx"]; eb=row["source_effect_bbox"]; bw,bh=row["source_width"],row["source_height"]
    text=row["korean"]; mask,fs,stroke=render_mask(text,bw,bh)
    tx=eb[0]+MARGIN_X; ty=eb[1]+(bh-mask.height)//2
    if ty<=eb[1]: ty=eb[1]+MARGIN_Y
    if ty+mask.height>=eb[3]: ty=eb[3]-MARGIN_Y-mask.height
    # Build source-derived vertical fill/alpha profile from exact source glyphs.
    r=regs[idx]; x,y,w,h=map(int,r["rect"]); crop=np.asarray(src.crop((x,y,x+w,y+h)))
    local_eb=[eb[0]-x,eb[1]-y,eb[2]-x,eb[3]-y]
    source_alpha=crop[:,:,3]
    profile=[]
    for sy in range(local_eb[1],local_eb[3]):
        sel=source_alpha[sy,local_eb[0]:local_eb[2]]>0
        vals=crop[sy,local_eb[0]:local_eb[2]][sel]
        if len(vals):
            profile.append(np.median(vals,axis=0))
        else:
            profile.append(None)
    known=[i for i,v in enumerate(profile) if v is not None]
    fallback=np.array(row["source_rgba_median"],dtype=float)
    layer=np.zeros((mask.height,mask.width,4),dtype=np.uint8)
    ma=np.asarray(mask,dtype=np.float32)/255.0
    for dy in range(mask.height):
        spos=(dy+0.5)/mask.height*len(profile)-0.5
        if known:
            k=min(known,key=lambda i:abs(i-spos)); rgba=np.array(profile[k],dtype=float)
        else: rgba=fallback
        layer[dy,:,0:3]=np.clip(np.rint(rgba[:3]),0,255).astype(np.uint8)
        base_alpha=max(1.0,float(rgba[3]))
        layer[dy,:,3]=np.clip(np.rint(ma[dy]*base_alpha),0,255).astype(np.uint8)
    lim=Image.fromarray(layer,"RGBA")
    lm=lim.getchannel("A")
    final.alpha_composite(lim,(tx,ty))
    full=Image.new("L",(W,H),0); full.paste(lm,(tx,ty)); localized_masks[idx]=full
    lb=list(full.getbbox() or ())
    contain=len(lb)==4 and lb[0]>eb[0] and lb[1]>eb[1] and lb[2]<eb[2] and lb[3]<eb[3]
    sizeok=contain and (lb[2]-lb[0])<=bw and (lb[3]-lb[1])<=bh
    if not (contain and sizeok): raise RuntimeError(("bbox",idx,eb,lb))
    oldbb=old_readable.crop(tuple(eb)).getchannel("A").getbbox()
    oldloc=[eb[0]+oldbb[0],eb[1]+oldbb[1],eb[0]+oldbb[2],eb[1]+oldbb[3]] if oldbb else None
    if not oldloc: raise RuntimeError(("prior bbox missing",idx))
    oldw=oldloc[2]-oldloc[0]; oldh=oldloc[3]-oldloc[1]
    neww=lb[2]-lb[0]; newh=lb[3]-lb[1]
    row.update({"localized_bbox":lb,"localized_width":neww,"localized_height":newh,
      "delta_left":lb[0]-eb[0],"delta_right":eb[2]-lb[2],"delta_top":lb[1]-eb[1],"delta_bottom":eb[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font":FONT_PATTERN,"font_size":fs,
      "stroke_width":stroke,"render_method":"DIRECT_NATIVE_ASPECT_NO_WIDTH_TARGET",
      "prior_localized_bbox":oldloc,"prior_localized_width":oldw,"prior_localized_height":oldh,
      "prior_width_ratio":round(oldw/bw,4),"new_width_ratio":round(neww/bw,4),
      "artificial_width_target_removed":True})

# Encode exact DDS header/layout/orientation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(sb[:128]+raw_final.tobytes("raw",RAWMODE))
if candidate.read_bytes()[:128]!=sb[:128] or len(candidate.read_bytes())!=len(sb): raise RuntimeError("DDS structure drift")
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw",RAWMODE)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("decoded drift")

# Exhaustive static gates.
clean_diff=diffmask(src,clean)
clean_out=count(ImageChops.multiply(clean_diff,ImageOps.invert(source_mask)))
final_diff=diffmask(src,decoded)
outside=count(ImageChops.multiply(final_diff,ImageOps.invert(allowed)))
alpha_diff=ImageChops.difference(src.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_out=count(ImageChops.multiply(alpha_diff,ImageOps.invert(allowed)))
# Protected decorative/header/separator sprites 0 and 16 must remain exact.
protected_changed=0
for idx in PROTECTED:
    r=regs[idx]; x,y,w,h=map(int,r["rect"])
    protected_changed+=count(diffmask(src.crop((x,y,x+w,y+h)),decoded.crop((x,y,x+w,y+h))))
# CLEAN must remove every original target pixel exactly.
same_clean=np.all(np.asarray(clean)==np.asarray(src),axis=2)
srcmask_np=np.asarray(source_mask)>0
clean_source_unchanged=int(np.logical_and(srcmask_np,same_clean).sum())
# FINAL residue is only meaningful outside new Korean glyph masks.
union=Image.new("L",(W,H),0)
for m in localized_masks.values(): union=ImageChops.lighter(union,m)
same_final=np.all(np.asarray(decoded)==np.asarray(src),axis=2)
residue=int(np.logical_and(srcmask_np,np.logical_and(same_final,np.asarray(union)==0)).sum())
# Regions are disjoint; prove localized bboxes do not overlap/touch.
bbs=[r["localized_bbox"] for r in rows]; overlap=0; touch=0
for i,a in enumerate(bbs):
    for b in bbs[i+1:]:
        if max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3]): overlap+=1
        if max(a[0]-1,b[0]-1)<min(a[2]+1,b[2]+1) and max(a[1]-1,b[1]-1)<min(a[3]+1,b[3]+1): touch+=1
allpass=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in rows)
status=allpass and clean_out==0 and outside==0 and alpha_out==0 and protected_changed==0 and clean_source_unchanged==0 and residue==0 and overlap==0 and touch==0
if not status: raise RuntimeError(("static fail",clean_out,outside,alpha_out,protected_changed,clean_source_unchanged,residue,overlap,touch))

# Controller evidence: SOURCE | CLEAN | FINAL for all nine targets.
cards=[]
for row in rows:
    eb=row["source_effect_bbox"]; pad=12
    box=(max(0,eb[0]-pad),max(0,eb[1]-pad),min(W,eb[2]+pad),min(H,eb[3]+pad))
    ims=[flatten(z.crop(box)) for z in (src,old_readable,clean,decoded)]
    scaled=[]
    for q in ims:
        sc=min(1.0,360/max(1,q.width),100/max(1,q.height))
        scaled.append(q.resize((max(1,int(q.width*sc)),max(1,int(q.height*sc))),Image.Resampling.LANCZOS) if sc<1 else q)
    cw=sum(q.width for q in scaled)+18; ch=max(q.height for q in scaled)+28
    card=Image.new("RGB",(cw,ch),(215,215,215)); d=ImageDraw.Draw(card)
    d.text((4,4),f"idx {row['idx']} {row['source']} -> {row['korean']}   SOURCE | A49 | CLEAN | A156",fill=(0,0,0))
    xx=0
    for q in scaled: card.paste(q,(xx,28)); xx+=q.width+9
    cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height+3 for c in cards)
sheet=Image.new("RGB",(cw,ch),(195,195,195)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+3
sheet.save(out/"A156_39BCA907_SOURCE_CLEAN_FINAL.jpg",quality=95)
flatten(decoded_raw).resize((1024,512),Image.Resampling.LANCZOS).save(out/"A156_39BCA907_FINAL_RAW_MIRROR_Y.jpg",quality=94)

report={"schema_version":1,"role":"A","run":run,"index":147,"asset":asset_rel,"worker":"github-actions",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA256},
 "atlas_provenance":{"blob_sha1":ATLAS_BLOB_SHA1,"sha256":ATLAS_SHA256,"regions":24},
 "trigger":"PRE_INGAME_014_A49_FORCED_92_PERCENT_WIDTH_HORIZONTAL_STRETCH_FALSE_NEGATIVE",
 "prior_c_status":"C192_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "prior_candidate_sha256":EXPECTED_BEFORE,
 "candidate_path":str(candidate.relative_to(repo)),"candidate_sha256":sha256(candidate),
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "binding":{"localized_indices":sorted(TARGETS),"protected_indices":PROTECTED,"semantic_strings":15,
            "policy":"canonical stage names use TRANSLATION_NAMING_POLICY phonetic Hangul; idx0 decorative/header and idx16 separator preserved"},
 "rows":rows,
 "machine_checks":{"clean_changed_outside_source_text_mask":clean_out,"decoded_changed_outside_source_bboxes":outside,
   "alpha_changed_outside_source_bboxes":alpha_out,"protected_pixels_changed":protected_changed,
   "clean_source_pixels_unchanged":clean_source_unchanged,"final_source_residue_outside_korean":residue,
   "localized_overlap_pairs":overlap,"localized_1px_touch_pairs":touch},
 "all_15_bbox_size_positive_margin_pass":allpass,
 "proportion_rework":{"prior_behavior":"A49 normalized every localized row to ~92% of source English bbox width regardless of native Hangul aspect","current_behavior":"direct native Black render sized by source height; no horizontal enlargement; width reduction is intentional to remove distortion","artificial_width_target_removed_rows":15},
 "ordered_generation_gate":{"plate_restoration":"PASS_EXACT_SOURCE_ALPHA_CLEAN","slant_direction":"PASS_SOURCE_UPRIGHT_FAMILY","no_unnecessary_undersizing":"PASS_NATIVE_HEIGHT_DRIVEN_WITH_POSITIVE_MARGIN","source_weight_outline_shadow":"REWORKED_NATIVE_BLACK_PLUS_1PX_WEIGHT_PENDING_CONTROLLER","clipping":"PASS_15_OF_15_POSITIVE_MARGIN","protected_clearance":"PASS_ZERO_PROTECTED_CHANGE","flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER","immediate_readability":"PENDING_CONTROLLER"},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "runtime_validation":"UNTESTED","status":"A156_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA","no_vr_ffb_dx11_dxvk_work":True}
(out/"A156_39BCA907_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":147,"asset":"39BCA907","candidate_sha256":report["candidate_sha256"],
 "bbox_size_positive_margin":"15/15 PASS","artificial_width_target_removed":"15/15","changed_outside":outside,"alpha_outside":alpha_out,
 "protected_changed":protected_changed,"clean_source_unchanged":clean_source_unchanged,"source_residue":residue,
 "overlap":overlap,"touch":touch,"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_A/{run}/A156_39BCA907_REPORT.json"}
(wr/"A156_39BCA907.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
