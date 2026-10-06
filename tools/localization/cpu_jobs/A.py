#!/usr/bin/env python3
# A147: work-steal C222-returned q236 FEF70E85 source-typography repair.
# B217 fixed native-resolution rendering but C222 rejected the current bytes because
# Noto Sans CJK KR Black + <=1.18x widening is too broad/blocky versus the strongly
# condensed, lighter English source family. This job preserves B80's C153-validated
# clean plate/right anchors/native height and rerenders all 14 labels with a shared
# native-HD Medium treatment plus a source-family 0.82x horizontal condensation.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib, json, struct, subprocess, urllib.request, statistics
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

repo=Path.cwd()
run="20261007-A-PRODUCTION147-Q236-SOURCE-TYPOGRAPHY"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION80/FEF_CLEAN_PLATE.png"
EXPECTED_BEFORE="5c92d09a7b4df56655c34f8ca95dbe5c63b15a3670365eafe7ff3c22696ae245"
SOURCE_SHA="a1c7f7d6ca5d2440076e49477cefecbf5084b4188072f3427ff13e5da24bc518"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/a147"); work.mkdir(exist_ok=True)
src_dds=work/"src.dds"; atlas_path=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds",src_dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_FEF70E85_512x512_atlas.json",atlas_path)

specs=[
 (0,"INDUSTRIAL COMPLEX","인더스트리얼 컴플렉스"),
 (1,"WATERFALLS","워터폴스"),
 (2,"TULIP GARDEN","튤립 가든"),
 (3,"SUNNY BEACH","서니 비치"),
 (4,"SNOW MOUNTAIN","스노 마운틴"),
 (5,"SKYSCRAPERS","스카이스크레이퍼스"),
 (6,"PALM BEACH","팜 비치"),
 (7,"NATIONAL PARK","내셔널 파크"),
 (8,"MILKY WAY","밀키 웨이"),
 (9,"METROPOLIS","메트로폴리스"),
 (10,"LOST CITY","로스트 시티"),
 (11,"LEGEND","레전드"),
 (12,"JUNGLE","정글"),
 (13,"IMPERIAL AVENUE","임페리얼 애비뉴"),
]
protected_ids=[14]
CONDENSE=0.82
MARGIN=2

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bbox_bool(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rect_bool(shape,b):
    m=np.zeros(shape,dtype=bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=True; return m
def dil(m,px=1):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(px*2+1)))>0
def decode_linear(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(2048,2048) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"mipmaps":mips,"raw_mode":mode,"format":"RGBA32"}

sb=src_dds.read_bytes(); ab=atlas_path.read_bytes()
if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source sha drift",sha_bytes(sb)))
if not candidate.exists() or sha_file(candidate)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift before A147",sha_file(candidate) if candidate.exists() else None,EXPECTED_BEFORE))
cb=candidate.read_bytes()
src_raw,src,meta=decode_linear(sb); old_raw,old,old_meta=decode_linear(cb)
if meta!=old_meta or cb[:128]!=sb[:128]: raise RuntimeError("candidate/header structure drift")
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError(("clean size",clean.size))

sa=np.asarray(src,dtype=np.uint8); oa=np.asarray(old,dtype=np.uint8); ca=np.asarray(clean,dtype=np.uint8)
H,W=sa.shape[:2]
regs={r["idx"]:r for r in json.loads(ab.decode())["regions"]}
rows=[]; source_mask=np.zeros((H,W),bool); allowed=np.zeros((H,W),bool); rgb_samples=[]
for idx,en,ko in specs:
    x,y,cw,ch=regs[idx]["rect"]
    cm=sa[y:y+ch,x:x+cw,3]>0
    ys,xs=np.nonzero(cm)
    if not len(xs): raise RuntimeError(("empty source",idx,en))
    ob=[x+int(xs.min()),y+int(ys.min()),x+int(xs.max())+1,y+int(ys.max())+1]
    rm=np.zeros((H,W),bool); rm[y:y+ch,x:x+cw]=cm
    rm[:,:ob[0]]=False; rm[:,ob[2]:]=False; rm[:ob[1],:]=False; rm[ob[3]:,:]=False
    source_mask|=rm
    allowed[ob[1]:ob[3],ob[0]:ob[2]]=True
    pix=sa[rm]; sel=pix[pix[:,3]>=200]
    if len(sel): rgb_samples.extend(sel[:,:3].tolist())
    oldm=(oa[:,:,3]>0)&rect_bool((H,W),ob)
    oldb=bbox_bool(oldm)
    rows.append({"region_idx":idx,"source":en,"korean":ko,"cell":[x,y,cw,ch],"original_bbox":ob,
                 "source_mask_pixels":int(np.count_nonzero(rm)),"prior_localized_bbox":oldb})

clean_diff=np.any(sa!=ca,axis=2)
if int(np.count_nonzero(clean_diff & ~source_mask))!=0:
    raise RuntimeError("validated clean plate drift outside source text mask")
if int(np.count_nonzero(source_mask & (ca[:,:,3]>0)))!=0:
    raise RuntimeError("validated clean plate retains visible source alpha")
if not rgb_samples: raise RuntimeError("source style sample empty")
fill_rgb=tuple(int(round(statistics.median(v[k] for v in rgb_samples))) for k in range(3))
fill=(fill_rgb[0],fill_rgb[1],fill_rgb[2],255)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
font_line=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Medium"],text=True).strip()
FONT,FI,FSTYLE=font_line.rsplit("|",2); FI=int(FI or 0)
if not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name or "Medium" not in FSTYLE:
    raise RuntimeError(("Noto CJK Medium unavailable",font_line))

def render_native(text,fs):
    f=ImageFont.truetype(FONT,fs,index=FI)
    probe=Image.new("L",(8,8),0); d=ImageDraw.Draw(probe)
    tb=d.textbbox((0,0),text,font=f)
    pad=10
    a=Image.new("L",(max(8,tb[2]-tb[0]+2*pad),max(8,tb[3]-tb[1]+2*pad)),0)
    ImageDraw.Draw(a).text((pad-tb[0],pad-tb[1]),text,font=f,fill=255)
    bb=a.getbbox()
    if not bb: raise RuntimeError(("empty render",text,fs))
    a=a.crop(bb)
    tile=Image.new("RGBA",a.size,fill); tile.putalpha(a)
    return tile

# Preserve B217's native-height readability: choose the largest shared Medium
# size that fits every exact source height before the horizontal source-family transform.
shared_fs=None
for fs in range(120,40,-1):
    ok=True
    for r in rows:
        t=render_native(r["korean"],fs)
        ah=r["original_bbox"][3]-r["original_bbox"][1]
        if t.height>ah-2*MARGIN:
            ok=False; break
    if ok:
        shared_fs=fs; break
if shared_fs is None: raise RuntimeError("shared Medium native height fit failed")

final=clean.copy(); target=np.zeros((H,W),bool); row_reports=[]
for r in rows:
    ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
    native=render_native(r["korean"],shared_fs)
    native_size=list(native.size)
    nw=max(1,int(round(native.width*CONDENSE)))
    tile=native.resize((nw,native.height),Image.Resampling.LANCZOS)
    bb=tile.getchannel("A").getbbox()
    if bb: tile=tile.crop(bb)
    maxw=aw-2*MARGIN
    if tile.width>maxw:
        tile=tile.resize((maxw,tile.height),Image.Resampling.LANCZOS)
        bb=tile.getchannel("A").getbbox()
        if bb: tile=tile.crop(bb)
    if tile.height>ah-2*MARGIN: raise RuntimeError(("height fit",r["region_idx"],tile.size,ob))
    px=ob[2]-MARGIN-tile.width
    py=ob[1]+(ah-tile.height)//2
    if py<=ob[1]: py=ob[1]+MARGIN
    if py+tile.height>=ob[3]: py=ob[3]-MARGIN-tile.height

    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    lb=bbox_bool(lm)
    if not lb: raise RuntimeError(("empty placed",r["region_idx"]))
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if min(margins)<=0 or lw>aw or lh>ah:
        raise RuntimeError(("bbox/positive margin",r["region_idx"],ob,lb,margins))

    oldb=r["prior_localized_bbox"]
    if not oldb: raise RuntimeError(("missing B217 bbox",r["region_idx"]))
    oldw,oldh=oldb[2]-oldb[0],oldb[3]-oldb[1]
    if lw > int(round(oldw*0.92)):
        raise RuntimeError(("not materially more condensed",r["region_idx"],oldw,lw))
    if lh < oldh-2:
        raise RuntimeError(("height/readability regression",r["region_idx"],oldh,lh))

    final.alpha_composite(layer); target|=lm
    source_area=max(1,aw*ah)
    old_alpha=int(np.count_nonzero((oa[:,:,3]>0)&rect_bool((H,W),ob)))
    new_alpha=int(np.count_nonzero(lm))
    row_reports.append({
      **r,"localized_bbox":lb,"source_size":[aw,ah],"prior_localized_size":[oldw,oldh],
      "localized_size":[lw,lh],"delta_left":margins[0],"delta_right":margins[1],
      "delta_top":margins[2],"delta_bottom":margins[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,
      "font_size_native":shared_fs,"native_unscaled_size":native_size,
      "horizontal_source_family_scale":CONDENSE,"fill_rgba":list(fill),"alignment":"right",
      "prior_width_px":oldw,"new_width_px":lw,"width_ratio_vs_B217":round(lw/oldw,4),
      "prior_height_px":oldh,"new_height_px":lh,
      "prior_alpha_coverage_of_source_bbox":round(old_alpha/source_area,5),
      "new_alpha_coverage_of_source_bbox":round(new_alpha/source_area,5),
      "fresh_native_hd_render":True,"rework_status":"A147_SOURCE_TYPOGRAPHY_REBUILD"
    })

row_masks=[target & rect_bool((H,W),r["original_bbox"]) for r in row_reports]
overlap=0; touch=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        ov=int(np.count_nonzero(row_masks[i]&row_masks[j]))
        near=int(np.count_nonzero(dil(row_masks[i],1)&row_masks[j]))
        overlap+=ov
        if ov or near: touch.append([i,j,ov,near])
if overlap or touch: raise RuntimeError(("target overlap/touch",overlap,touch))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",meta["raw_mode"])
candidate.write_bytes(payload)
after=sha_bytes(payload)
new_raw,new,new_meta=decode_linear(payload)
if payload[:128]!=sb[:128] or new_meta!=meta: raise RuntimeError("header/meta drift")
if ImageChops.difference(new,final).getbbox() is not None: raise RuntimeError("roundtrip mismatch")
na=np.asarray(new,dtype=np.uint8)

diff=np.any(sa!=na,axis=2)
outside=int(np.count_nonzero(diff&~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=na[:,:,3])&~allowed))
protected_changed=outside
guard=dil(target,2)
source_residue=int(np.count_nonzero(source_mask&(na[:,:,3]>0)&~guard))
if outside or alpha_out or protected_changed or source_residue:
    raise RuntimeError(("zero-pixel gate",outside,alpha_out,protected_changed,source_residue))

preserved={}
for idx in protected_ids:
    x,y,cw,ch=regs[idx]["rect"]
    preserved[str(idx)]=int(np.count_nonzero(np.any(sa[y:y+ch,x:x+cw]!=na[y:y+ch,x:x+cw],axis=2)))
if any(preserved.values()): raise RuntimeError(("protected changed",preserved))

condensed_rows=sum(1 for r in row_reports if r["width_ratio_vs_B217"]<=0.92)
height_preserved_rows=sum(1 for r in row_reports if r["new_height_px"]>=r["prior_height_px"]-2)
if condensed_rows!=14 or height_preserved_rows!=14:
    raise RuntimeError(("source typography materiality",condensed_rows,height_preserved_rows))

def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im):
    v=comp(im).resize((1024,1024),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(1024,1050),(28,28,28)); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,5),label,fill="white"); return c

cards=[card("SOURCE_READABLE",src),card("B217_REJECTED",old),card("B80_CLEAN",clean),card("A147_MEDIUM_CONDENSED",new)]
sheet=Image.new("RGB",(2048,2100),(24,24,24))
sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(1024,0)); sheet.paste(cards[2],(0,1050)); sheet.paste(cards[3],(1024,1050))
sheet.thumbnail((1800,1850),Image.Resampling.LANCZOS)
sheet.save(out/"A147_FEF_SOURCE_B217_CLEAN_NEW_READABLE.jpg","JPEG",quality=96,subsampling=0)

rawcards=[card("SOURCE_RAW_MIRROR_Y",src_raw),card("B217_RAW_REJECTED",old_raw),card("A147_RAW_MIRROR_Y",new_raw)]
rawsheet=Image.new("RGB",(3072,1050),(24,24,24))
for i,c in enumerate(rawcards): rawsheet.paste(c,(1024*i,0))
rawsheet.thumbnail((2100,760),Image.Resampling.LANCZOS)
rawsheet.save(out/"A147_FEF_SOURCE_B217_NEW_RAW.jpg","JPEG",quality=96,subsampling=0)

src_rgb=comp(src); old_rgb=comp(old); new_rgb=comp(new)
contacts=[]
for rr in row_reports:
    x0,y0,x1,y1=rr["original_bbox"]; p=8
    cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[]
    for im in (src_rgb,old_rgb,new_rgb):
        z=im.crop(cr)
        sc=min(2.0,900/max(1,z.width))
        z=z.resize((max(1,round(z.width*sc)),max(1,round(z.height*sc))),Image.Resampling.NEAREST)
        ims.append(z)
    cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+28
    c=Image.new("RGB",(cw,ch),(28,28,28)); d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(("SOURCE","B217_REJECTED","A147"),ims):
        d.text((xx+4,4),lab,fill="white"); c.paste(z,(xx,26)); xx+=z.width+6
    contacts.append(c)
rowsheet=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+6*(len(contacts)-1)),(24,24,24))
yy=0
for c in contacts: rowsheet.paste(c,(0,yy)); yy+=c.height+6
rowsheet.thumbnail((2200,12000),Image.Resampling.LANCZOS)
rowsheet.save(out/"A147_FEF_ROW_CONTACT.jpg","JPEG",quality=96,subsampling=0)

report={
 "schema_version":1,"role":"A","run":"A147","queue_index":236,"asset":asset,
 "work_stolen_from_lane":"B","trigger":"C222_REWORK_REQUIRED_SOURCE_STYLE_PROPORTION_WEIGHT",
 "prior_candidate_sha256":EXPECTED_BEFORE,"source_sha256":SOURCE_SHA,"candidate_sha256":after,
 "c222_defect":"B217 Noto Sans CJK KR Black is broad/blocky and widened <=1.18x versus strongly condensed/narrow English source",
 "method":"preserve C153/B80 validated clean plate + source right anchors + B217 native-height readability; rerender every row at native 2048x2048 using shared Noto Sans CJK KR Medium, then apply one consistent 0.82x native-resolution horizontal source-family transform; no nearest-neighbor enlargement; exact source bbox/RAW mirror-Y/header retained",
 "shared_style":{"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,
                 "font_size_native":shared_fs,"horizontal_source_family_scale":CONDENSE,
                 "fill_rgba":list(fill),"alignment":"right"},
 "stage_name_policy":"PASS_CANONICAL_PHONETIC_TRANSLITERATION",
 "rows":row_reports,
 "protected_regions_changed_pixels":preserved,
 "qa":{
   "header_128_exact_canonical":True,"raw_mode":meta["raw_mode"],"raw_orientation":"mirror_y",
   "clean_changed_pixels_outside_source_mask":int(np.count_nonzero(clean_diff&~source_mask)),
   "clean_source_alpha_remaining":int(np.count_nonzero(source_mask&(ca[:,:,3]>0))),
   "changed_pixels_outside_exact_source_bboxes":outside,
   "alpha_changed_pixels_outside_exact_source_bboxes":alpha_out,
   "protected_changed_pixels":protected_changed,"source_residue_pixels":source_residue,
   "localized_overlap_pixels":overlap,"localized_touch_pairs":touch,
   "materially_more_condensed_rows":condensed_rows,"height_preserved_rows":height_preserved_rows,
   "fresh_native_hd_render":"PASS_NO_LOWRES_NEAREST_UPSCALE",
   "ordered_gate":{
      "plate_restoration":"PASS_INHERITED_C153_VALIDATED_B80_CLEAN_PLATE",
      "source_matching_slant_direction":"PASS_UPRIGHT_SOURCE_FAMILY",
      "no_unnecessary_undersizing":"PASS_NATIVE_HEIGHT_PRESERVED_14_OF_14",
      "source_faithful_weight_outline_shadow":"REWORKED_MEDIUM_CONDENSED_NO_INVENTED_EFFECTS_PENDING_CONTROLLER",
      "clipping":"PASS_14_OF_14_POSITIVE_MARGIN",
      "protected_art_clearance":"PASS_ZERO_OUTSIDE_SOURCE_BBOX_AND_REVERSED_EXACT",
      "flip_y_and_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
      "immediate_readability":"PENDING_CONTROLLER"
   }
 },
 "runtime_validation":"UNTESTED",
 "status":"A147_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"A147_FEF70E85_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A147_FEF70E85.json").write_text(json.dumps({
 "role":"A","run":"A147","queue_index":236,"asset":asset,"candidate_sha256":after,
 "report":str(rp.relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"A147","before":EXPECTED_BEFORE,"after":after,
 "font_style":FSTYLE,"font_size_native":shared_fs,"condense":CONDENSE,
 "materially_more_condensed_rows":condensed_rows,"height_preserved_rows":height_preserved_rows,
 "status":report["status"]},ensure_ascii=False))
