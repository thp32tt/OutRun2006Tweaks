#!/usr/bin/env python3
"""A196 q035: native source-derived Total Rank speech-bubble title repair."""
from pathlib import Path
import hashlib, json, os, struct, subprocess, urllib.request, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("A196 GitHub CPU worker lane only")
repo=Path.cwd()
run="20261008-A196-Q035-TOTAL-RANK-NATIVE-HIERARCHY"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_HOLL_RANK_Exst/E989E3B7_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/rel
prior="c0e76661ed974cb7c477f172e93fd67645391f1da3e81dcb867d86af3a595622"
source_sha="b4f0146b9caa0469a410601d633d3394703e5ec85d07f9bd4973ddc766105583"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_HOLL_RANK_Exst/E989E3B7_1024x1024.dds"
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise ValueError("not DDS")
    h,w=struct.unpack_from("<II",b,12)
    mips=struct.unpack_from("<I",b,28)[0]
    bpp=struct.unpack_from("<I",b,88)[0]
    masks=struct.unpack_from("<IIII",b,92)
    fourcc=b[84:88]
    if bpp!=32 or fourcc!=bytes(4) or mips!=1 or len(b)!=128+h*w*4:
        raise ValueError(("DDS format changed",h,w,bpp,mips,fourcc,len(b)))
    mode="RGBA" if masks==(255,65280,16711680,4278190080) else ("BGRA" if masks==(16711680,65280,255,4278190080) else None)
    if mode is None: raise ValueError(("unknown channel masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),mode
def save_dds(header,readable,path,mode):
    payload=header+readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()
def bounds(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def find_font():
    pp=glob.glob("/usr/share/fonts/**/NotoSansCJK-Black.ttc",recursive=True)
    if not pp:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
        pp=glob.glob("/usr/share/fonts/**/NotoSansCJK-Black.ttc",recursive=True)
    if not pp: raise RuntimeError("NotoSansCJK-Black.ttc required")
    return pp[0]
def banner(text,pt,tracking,lean):
    font=ImageFont.truetype(fontfile,pt,index=1)
    # Per-glyph native outlines, not an enlargement of an old Korean DDS.
    syllables=list(text)
    buf=Image.new("L",(1300,240),0)
    pen=45
    for ch in syllables:
        if ch==" ":
            pen+=round(pt*.42)
            continue
        bb=font.getbbox(ch)
        x=pen-bb[0]; y=45-bb[1]
        ImageDraw.Draw(buf).text((x,y),ch,fill=255,font=font)
        pen+=font.getlength(ch)+tracking
    bb=buf.getbbox()
    if bb is None: raise ValueError("no glyph")
    buf=buf.crop(bb)
    pad=round(buf.height*lean)+8
    slanted=buf.transform((buf.width+pad,buf.height),Image.Transform.AFFINE,
                (1,lean,-lean*buf.height+4,0,1,0),resample=Image.Resampling.BICUBIC,fillcolor=0)
    return slanted.crop(slanted.getbbox())
def flat_rgb(im):
    bg=Image.new("RGBA",im.size,(240,240,240,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")
if not candidate.is_file() or digest(candidate)!=prior:
    raise RuntimeError("q035 candidate changed concurrently; refusing stale edit")
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","35","--require-safe-rerender"],capture_output=True,text=True)
print("A196 TRIAGE:",triage.stdout,flush=True)
if triage.returncode!=0 or '"MATERIAL_REWORK"' not in triage.stdout:
    raise RuntimeError(("triage failed",triage.returncode,triage.stderr))
srcp=Path("/tmp/a196_e989_source.dds")
urllib.request.urlretrieve(source_url,srcp)
if digest(srcp)!=source_sha: raise RuntimeError(("canonical English source drift",digest(srcp)))
header,src,mode=load_dds(srcp)
prior_header,old,prior_mode=load_dds(candidate)
if (src.size,mode)!=( (4096,4096),"RGBA") or header!=prior_header or mode!=prior_mode:
    raise RuntimeError("source/prior structure mismatch")
root=repo/"localization/graphics/role_A/20261006-A-PRODUCTION102-E989E3B7"
source_png=Image.open(root/"A102_SOURCE_READABLE.png").convert("RGBA")
clean=Image.open(root/"A102_CLEAN_PLATE.png").convert("RGBA")
old_png=Image.open(root/"A102_FINAL_READABLE.png").convert("RGBA")
if ImageChops.difference(src,source_png).getbbox():
    raise RuntimeError("pinned original source not identical to source evidence PNG")
if ImageChops.difference(old,old_png).getbbox():
    raise RuntimeError("candidate not identical to A102 final PNG")
source=np.asarray(src)
ca=np.asarray(clean)
prev=np.asarray(old)
plate_change=np.any(source!=ca,axis=2)
rows=[
    dict(id="pink",source_bbox=[609,357,1113,429],edit_bbox=[594,342,1128,444],old_bbox=[745,361,977,425]),
    dict(id="green",source_bbox=[2273,370,2778,442],edit_bbox=[2266,363,2785,448],old_bbox=[2412,375,2639,437])
]
plate_allowed=np.zeros((4096,4096),dtype=bool)
text_allowed=np.zeros((4096,4096),dtype=bool)
for row in rows:
    x0,y0,x1,y1=row["edit_bbox"]
    plate_allowed[y0:y1,x0:x1]=True
    x0,y0,x1,y1=row["source_bbox"]
    text_allowed[y0:y1,x0:x1]=True
if int(np.logical_and(plate_change,~plate_allowed).sum()):
    raise RuntimeError("source-to-clean changed outside original A102 source effect scope")
if int(np.logical_and(np.any(source!=prev,axis=2),~plate_allowed).sum()):
    raise RuntimeError("prior DDS changed outside A102 effect scope")
# Source effects and clean plate must be independently inspectable before lettering.
for row in rows:
    x0,y0,x1,y1=row["source_bbox"]
    rmask=plate_change[y0:y1,x0:x1]
    if int(rmask.sum())<2000: raise RuntimeError(("missing source removal",row["id"]))
    row["source_removed_pixels"]=int(rmask.sum())
fontfile=find_font()
final=clean.copy()
new_masks=[]
for row in rows:
    x0,y0,x1,y1=row["source_bbox"]
    width=x1-x0; height=y1-y0
    # Native font size is limited by English effect-height. Tracking follows
    # visually wider "Total Rank" title family, never a numeric English width quota.
    options=[]
    for pt in range(76,61,-1):
        for tracking in (17,14,11,8):
            m=banner("종합 랭킹",pt,tracking,0.20)
            # Dark 3px source-derived contour plus white face, no opaque plate.
            outer=m.filter(ImageFilter.MaxFilter(7))
            if outer.width<=width-8 and outer.height<=height-8:
                options.append((pt,tracking,m,outer))
    if not options: raise RuntimeError(("text cannot fit without clipping",row["id"]))
    # Highest native readable font, then source-relative spacing; do not force English-width percent.
    pt,track,m,outer=options[0]
    # Effect mask outer filter retains the glyph canvas bounds. Add 4px padding.
    bw,bh=m.size
    px=x0+(width-bw)//2
    py=y0+(height-bh)//2
    if min(px-x0,py-y0,x1-(px+bw),y1-(py+bh))<4:
        raise RuntimeError(("4px positive margin missing",row["id"],px,py,bw,bh))
    navy=(6,8,45)
    face=(250,251,250)
    mask=Image.new("L",src.size,0)
    mask.paste(m,(px,py))
    # Outlining is source-family justified; keep within original bbox.
    stroke=mask.filter(ImageFilter.MaxFilter(7))
    stroke_arr=np.asarray(stroke)>0
    if np.any(stroke_arr & ~text_allowed):
        raise RuntimeError(("outline beyond original source text bbox",row["id"]))
    layer=Image.new("RGBA",src.size,navy+(0,))
    layer.putalpha(stroke)
    final.alpha_composite(layer)
    fg=Image.new("RGBA",src.size,face+(0,))
    fg.putalpha(mask)
    final.alpha_composite(fg)
    new_masks.append(stroke_arr)
    bb=bounds(stroke_arr)
    oldbox=row["old_bbox"]
    oldwidth=oldbox[2]-oldbox[0]
    row.update(font_pt=pt,tracking=track,readable_slant_top_minus_bottom_px=round(m.height*.20),
               new_bbox=bb,old_width=oldwidth,new_width=bb[2]-bb[0],
               gain_px=bb[2]-bb[0]-oldwidth,
               margins=[bb[0]-x0,x1-bb[2],bb[1]-y0,y1-bb[3]],
               width_ceiling=width,height_ceiling=height)
if int(np.logical_and(new_masks[0],new_masks[1]).sum()):
    raise RuntimeError("localized glyph mask collision")
fa=np.asarray(final)
changed=np.any(source!=fa,axis=2)
changed_out=int(np.logical_and(changed,~plate_allowed).sum())
alpha_out=int(np.logical_and(fa[:,:,3]!=source[:,:,3],~plate_allowed).sum())
clean_to_final=np.any(ca!=fa,axis=2)
all_new=new_masks[0]|new_masks[1]
composite_out=int(np.logical_and(clean_to_final,~all_new).sum())
protected_change=int(np.logical_and(changed,~plate_allowed).sum())
source_remnants=0
# Source effects were removed in CLEAN independently. No source-byte leftover outside the new effect masks.
for row in rows:
    x0,y0,x1,y1=row["source_bbox"]
    orig_diff=plate_change[y0:y1,x0:x1]
    orig_again=np.all(fa[y0:y1,x0:x1]==source[y0:y1,x0:x1],axis=2)
    rendered=all_new[y0:y1,x0:x1]
    source_remnants+=int(np.logical_and(orig_diff,orig_again&~rendered).sum())
if any((changed_out,alpha_out,composite_out,protected_change,source_remnants)):
    raise RuntimeError(("QA stage8",changed_out,alpha_out,composite_out,protected_change,source_remnants))
if min(x["gain_px"] for x in rows)<=45:
    raise RuntimeError(("not material source-hierarchy improvement",rows))
new_sha=save_dds(header,final,candidate,mode)
new_header,decoded,new_mode=load_dds(candidate)
if header!=new_header or mode!=new_mode or ImageChops.difference(final,decoded).getbbox():
    raise RuntimeError("saved DDS roundtrip mismatch")
# Save lossless stage-only proofs, both readable and native atlas evidence.
src.save(out/"A196_SOURCE_READABLE.png")
clean.save(out/"A196_CLEAN_PLATE.png")
decoded.save(out/"A196_FINAL_DECODED_READABLE.png")
Image.fromarray((plate_allowed*255).astype("uint8"),"L").save(out/"A196_PROTECTED_SCOPE_MASK.png")
Image.fromarray((all_new*255).astype("uint8"),"L").save(out/"A196_KOREAN_EFFECT_MASK.png")
for row in rows:
    x0,y0,x1,y1=row["edit_bbox"]
    crop=(max(0,x0-22),max(0,y0-45),min(src.width,x1+22),min(src.height,y1+45))
    for typ,img in (("SOURCE",src),("CLEAN",clean),("FINAL",decoded)):
        img.crop(crop).save(out/f"A196_{row['id']}_{typ}_NATIVE.png")
    imgs=[flat_rgb(img).crop(crop) for img in (src,clean,decoded)]
    ww=max(im.width for im in imgs)
    hh=max(im.height for im in imgs)
    trip=Image.new("RGB",(3*ww+12,hh+26),"white")
    draw=ImageDraw.Draw(trip)
    draw.text((4,6),f"{row['id']}  SOURCE | CLEAN | FINAL",fill="black")
    for i,img in enumerate(imgs): trip.paste(img,(i*(ww+6),26))
    trip.save(out/f"A196_{row['id']}_SOURCE_CLEAN_FINAL_NATIVE.png")
    for scale in (100,75,50):
        if scale==100: pic=trip
        else: pic=trip.resize((trip.width*scale//100,trip.height*scale//100),Image.Resampling.LANCZOS)
        pic.save(out/f"A196_{row['id']}_SOURCE_CLEAN_FINAL_{scale}.png")
for name,swap in (("READABLE",False),("RAW",True)):
    pair=[src,decoded]
    if swap:pair=[im.transpose(Image.Transpose.FLIP_TOP_BOTTOM) for im in pair]
    wa=flat_rgb(pair[0]); wb=flat_rgb(pair[1])
    wa.thumbnail((1200,1200));wb.thumbnail((1200,1200))
    joined=Image.new("RGB",(wa.width+wb.width+8,max(wa.height,wb.height)+30),"white")
    ImageDraw.Draw(joined).text((4,5),"ENGLISH SOURCE / KOREAN PERSISTED DDS",fill="black")
    joined.paste(wa,(0,30));joined.paste(wb,(wa.width+8,30))
    joined.save(out/f"A196_{name}_SOURCE_FINAL.jpg",quality=95)
report=dict(schema_version=1,role="A",run=run,queue_index=35,
    source_provenance=dict(repository="Sonic-TV/OR2006Sprites",
        commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",sha256=source_sha,url=source_url),
    prior_candidate_sha256=prior,new_candidate_sha256=new_sha,asset=rel,
    dds=dict(size=list(src.size),pixel_mode=mode,mip_count=1,header128_exact=True,
        raw_orientation="mirror_y"),
    source_family="Italic Total Rank white face + native deep-navy outline; enlarged native Hangul, positively centered inside original glyph box",
    clean_plate_provenance=str((root/"A102_CLEAN_PLATE.png").relative_to(repo)),
    rows=rows,
    machine_qa=dict(plate_only_source_removed_per_row=[r["source_removed_pixels"] for r in rows],
        changed_outside_declared_english_effect_scope=changed_out,
        alpha_changed_outside_declared_english_effect_scope=alpha_out,
        clean_to_final_changes_outside_korean_effect_mask=composite_out,
        protected_changed_pixels=protected_change,source_script_byte_residue=source_remnants,
        localized_overlap=0,persisted_dds_roundtrip="PASS",
        native_no_upscale=True,src_vs_evidence_png="BYTE_EXACT",
        previous_vs_evidence_png="BYTE_EXACT"),
    static_visual_status="PENDING_CONTROLLER_IMAGE_QA",
    C1="PENDING",C3="PENDING",RUNTIME_VALIDATION="UNTESTED",
    no_production_approval_from_worker=True)
(out/"A196_WORKER_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A196_Q035.json").write_text(json.dumps(dict(
    run=run,queue_index=35,candidate_sha256=new_sha,previous_sha256=prior,
    widths=[r["new_width"] for r in rows],machine=report["machine_qa"],
    worker_status="MACHINE_PASS_CONTROLLER_VISUAL_PENDING",report=str((out/"A196_WORKER_REPORT.json").relative_to(repo)),
    RUNTIME_VALIDATION="UNTESTED"),ensure_ascii=False,indent=2)+"\n")
print("A196_DONE",new_sha,[(r["id"],r["old_width"],r["new_width"],r["margins"]) for r in rows],flush=True)
