#!/usr/bin/env python3
# B241: q212 BA0147DA C256 title-family proportion rework.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")
import hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

repo=Path.cwd()
RUN="20261008-B241-Q212-CONDENSED-SOURCE-ANCHORS"
out=repo/"localization/graphics/role_B"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="3266d0740f9fc5b8d1b0771e2313fe3364e485da06bc5ad578f94999082315c4"
SOURCE="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12); masks=struct.unpack_from("<IIII",b,92)
    if b[84:88]!=b"\0\0\0\0" or struct.unpack_from("<I",b,88)[0]!=32 or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("DDS",w,h,mips,len(b)))
    mode="RGBA" if masks==(0xff,0xff00,0xff0000,0xff000000) else "BGRA" if masks==(0xff0000,0xff00,0xff,0xff000000) else None
    if not mode: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return b,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"pitch":pitch,"mips":mips,"masks":masks,"mode":mode}
def fontspec():
    for pat in ["Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try:q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except Exception:q=""
        if "|" in q:
            p,ix=q.rsplit("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:return p,int(ix or 0),pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    p,ix=q.rsplit("|",1); return p,int(ix or 0),"Noto Sans CJK KR:style=Bold"
FONT,FI,FPAT=fontspec()

def flat(im):
    z=Image.new("RGBA",im.size,(82,82,82,255)); z.alpha_composite(im); return z.convert("RGB")
def maskdiff(a,b):
    d=ImageChops.difference(a,b); cs=d.split(); m=cs[0]
    for c in cs[1:]:m=ImageChops.lighter(m,c)
    return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def mbbox(mask):
    b=mask.getbbox()
    return list(b) if b else None

# Detect English source word anchors from red title pixels, using the largest inter-letter gaps.
def source_word_groups(src,bb,n_groups):
    x0,y0,x1,y1=bb
    a=np.asarray(src.crop((x0,y0,x1,y1))).astype(np.int16)
    red=(a[:,:,3]>20)&(a[:,:,0]>100)&(a[:,:,0]>a[:,:,1]*1.6+25)&(a[:,:,0]>a[:,:,2]*1.6+25)
    on=red.any(axis=0)
    runs=[]; s=None
    for i,v in enumerate(on):
        if v and s is None:s=i
        elif not v and s is not None:runs.append([s,i]);s=None
    if s is not None:runs.append([s,len(on)])
    if len(runs)<n_groups: raise RuntimeError(("source red runs",bb,runs))
    gaps=[(runs[i+1][0]-runs[i][1],i) for i in range(len(runs)-1)]
    cuts=sorted(i for _,i in sorted(gaps,reverse=True)[:n_groups-1])
    groups=[]; start=0
    for cut in cuts+[len(runs)-1]:
        rr=runs[start:cut+1]
        groups.append([x0+rr[0][0],x0+rr[-1][1]])
        start=cut+1
    if len(groups)!=n_groups: raise RuntimeError(("groups",groups))
    return groups,runs,sorted(gaps,reverse=True)[:n_groups-1]

def word_layer(word,target_h=146,hscale=0.62,stroke=2):
    f=ImageFont.truetype(FONT,220,index=FI)
    p=Image.new("L",(1800,360),0); d=ImageDraw.Draw(p)
    bb=d.textbbox((0,0),word,font=f,stroke_width=stroke)
    d.text((24-bb[0],24-bb[1]),word,font=f,fill=255,stroke_width=stroke,stroke_fill=255)
    box=p.getbbox()
    if not box: raise RuntimeError(("empty",word))
    g=p.crop(box)
    sc=target_h/g.height
    w=max(1,round(g.width*sc*hscale))
    m=g.resize((w,target_h),Image.Resampling.LANCZOS)
    rgba=Image.new("RGBA",m.size,(196,0,0,255)); rgba.putalpha(m)
    return rgba

if sha(cand)!=INPUT: raise RuntimeError(("candidate drift",sha(cand),INPUT))
srcp=Path("/tmp/BA0147DA_source.dds")
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",srcp)
if sha(srcp)!=SOURCE: raise RuntimeError(("source drift",sha(srcp)))
cb,cr,old,meta=load(cand); sb,sr,src,smeta=load(srcp)
if cb[:128]!=sb[:128] or meta!=smeta: raise RuntimeError("structure drift")
clean=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_CLEAN_PLATE.png").convert("RGBA")
protected=np.asarray(Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_PROTECTED_MASK.png").convert("L"))>0
if clean.size!=old.size or protected.shape!=(old.height,old.width): raise RuntimeError("evidence size")

cfg=[
 {"key":"coast2coast_title","source_text":"COAST 2 COAST","words":["코스트","2","코스트"],"bbox":[0,964,1760,1124],"groups":3,"preserve_source_groups":[1]},
 {"key":"heart_attack_title","source_text":"HEART ATTACK","words":["하트","어택"],"bbox":[21,1316,1780,1474],"groups":2,"preserve_source_groups":[]},
]
final=old.copy()
allowed=Image.new("L",old.size,0); ad=ImageDraw.Draw(allowed)
rows=[]
new_text_mask=np.zeros((old.height,old.width),dtype=bool)

for spec in cfg:
    bb=spec["bbox"]; x0,y0,x1,y1=bb; ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
    final.paste(clean.crop(tuple(bb)),(x0,y0))
    groups,runs,word_gaps=source_word_groups(src,bb,spec["groups"])
    word_reports=[]
    visible_union=Image.new("L",old.size,0)
    for gi,(word,gx) in enumerate(zip(spec["words"],groups)):
        ga,gb=gx
        if gi in spec["preserve_source_groups"]:
            # Preserve unchanged numeric token from canonical English source exactly.
            pad=6
            rx0=max(x0,ga-pad); rx1=min(x1,gb+pad)
            final.paste(src.crop((rx0,y0,rx1,y1)),(rx0,y0))
            diff=maskdiff(clean.crop((rx0,y0,rx1,y1)),src.crop((rx0,y0,rx1,y1)))
            visible_union.paste(diff,(rx0,y0))
            word_reports.append({"word":word,"mode":"PRESERVE_CANONICAL_SOURCE_TOKEN","source_group_x":[ga,gb],"placed_x":[rx0,rx1]})
            continue
        layer=word_layer(word)
        cx=(ga+gb)/2.0
        x=round(cx-layer.width/2)
        y=y0+(y1-y0-layer.height)//2
        # Keep positive margin inside the full exact source title bbox.
        x=max(x0+5,min(x,x1-layer.width-5))
        y=max(y0+4,min(y,y1-layer.height-4))
        lm=np.asarray(layer.getchannel("A"))>0
        if np.any(lm & protected[y:y+layer.height,x:x+layer.width]): raise RuntimeError(("protected",spec["key"],word))
        if np.any(new_text_mask[y:y+layer.height,x:x+layer.width] & lm): raise RuntimeError(("localized overlap",spec["key"],word))
        new_text_mask[y:y+layer.height,x:x+layer.width] |= lm
        final.alpha_composite(layer,(x,y))
        visible_union.paste(ImageChops.lighter(visible_union.crop((x,y,x+layer.width,y+layer.height)),layer.getchannel("A")),(x,y))
        word_reports.append({"word":word,"mode":"NATIVE_BOLD_CONDENSED","source_group_x":[ga,gb],"placed_bbox":[x,y,x+layer.width,y+layer.height],"hscale":0.62,"target_h":146,"stroke":2})
    changed_vs_clean=maskdiff(clean.crop(tuple(bb)),final.crop(tuple(bb)))
    local=changed_vs_clean.getbbox()
    if not local: raise RuntimeError(("empty final",spec["key"]))
    lb=[x0+local[0],y0+local[1],x0+local[2],y0+local[3]]
    sw,sh=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    if lw>sw or lh>sh or lb[0]<x0 or lb[1]<y0 or lb[2]>x1 or lb[3]>y1: raise RuntimeError(("size",spec["key"],lb,bb))
    rows.append({
      "key":spec["key"],"source_text":spec["source_text"],"text":" ".join(spec["words"]),
      "source_bbox":bb,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "width_ratio":round(lw/sw,4),"height_ratio":round(lh/sh,4),
      "source_word_groups_x":groups,"source_run_count":len(runs),"source_largest_word_gaps":word_gaps,
      "words":word_reports,
      "font":FPAT,
      "construction":"source-word-anchor reconstruction; Korean glyphs horizontally condensed to 0.62 at native height; unchanged numeral 2 preserved from canonical source; no per-syllable spacing hack"
    })

dm=maskdiff(old,final); outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
am=ImageChops.difference(old.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
alpha_out=count(ImageChops.multiply(am,ImageChops.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("scope",outside,alpha_out))

raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=cb[:128]+raw.tobytes("raw",meta["mode"]); cand.write_bytes(payload); csha=sha(cand)
rb,rr,dec,rm=load(cand)
if rb[:128]!=cb[:128] or rm!=meta or ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")

# Visual evidence: exact source / rejected A170 / clean / current B241.
cards=[]
for r in rows:
    x0,y0,x1,y1=r["source_bbox"]; pad=28
    crop=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
    ims=[]
    for lab,im in [("SOURCE",src),("C256_REJECTED_A170",old),("CLEAN",clean),("B241",dec)]:
        z=flat(im.crop(crop)); z.thumbnail((760,270),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(z.width,z.height+26),(24,24,24));c.paste(z,(0,26));ImageDraw.Draw(c).text((4,4),lab,fill="white");ims.append(c)
    row=Image.new("RGB",(sum(i.width for i in ims)+12*3,max(i.height for i in ims)+20),(16,16,16)); xx=0
    for c in ims:row.paste(c,(xx,0));xx+=c.width+12
    ImageDraw.Draw(row).text((4,row.height-3),r["key"],fill="white",anchor="ls");cards.append(row)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8),(16,16,16)); yy=0
for c in cards:sheet.paste(c,(0,yy));yy+=c.height+8
sheet.save(out/"B241_Q212_CONTACTS.jpg","JPEG",quality=96,subsampling=0)

s=flat(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)); f=flat(dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
s.thumbnail((950,950),Image.Resampling.LANCZOS); f.thumbnail((950,950),Image.Resampling.LANCZOS)
rw=Image.new("RGB",(s.width+f.width+12,max(s.height,f.height)+26),(16,16,16));rw.paste(s,(0,26));rw.paste(f,(s.width+12,26))
d=ImageDraw.Draw(rw);d.text((4,4),"SOURCE RAW",fill="white");d.text((s.width+16,4),"B241 RAW",fill="white")
rw.save(out/"B241_Q212_RAW.jpg","JPEG",quality=94,subsampling=0)

# Practical scale evidence at 100/75/50% for title crops.
prs=[]
for r in rows:
    bb=tuple(r["source_bbox"]); parts=[]
    for scale in [1.0,0.75,0.5]:
        for lab,im in [("SOURCE",src),("B241",dec)]:
            z=flat(im.crop(bb))
            if scale!=1.0:z=z.resize((max(1,round(z.width*scale)),max(1,round(z.height*scale))),Image.Resampling.LANCZOS)
            z.thumbnail((700,220),Image.Resampling.LANCZOS)
            c=Image.new("RGB",(z.width,z.height+24),(20,20,20));c.paste(z,(0,24));ImageDraw.Draw(c).text((4,4),f"{lab} {int(scale*100)}%",fill="white");parts.append(c)
    row=Image.new("RGB",(max(p.width for p in parts),sum(p.height for p in parts)+5*(len(parts)-1)),(16,16,16)); y=0
    for p in parts:row.paste(p,(0,y));y+=p.height+5
    prs.append(row)
ps=Image.new("RGB",(sum(p.width for p in prs)+12*(len(prs)-1),max(p.height for p in prs)),(16,16,16));x=0
for p in prs:ps.paste(p,(x,0));x+=p.width+12
ps.save(out/"B241_Q212_PRACTICAL.jpg","JPEG",quality=94,subsampling=0)

report={
 "schema_version":2,"role":"B","run":RUN,"queue_index":212,"asset":"BA0147DA",
 "trigger":"C256_VISUAL_FAIL_SOURCE_TITLE_GLYPH_PROPORTION",
 "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":csha,
 "rows":rows,
 "machine_qa":{"bbox_size_positive_margin":"2/2 PASS","changed_outside":outside,"alpha_outside":alpha_out,
   "localized_pair_overlap_pixels":0,"protected_overlap_pixels":0,"header_128_exact":True,"mips":meta["mips"],
   "raw_orientation":"mirror_y","persisted_decode":"PASS"},
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_REUSE_B85_VERIFIED_CLEAN_PLATE",
   "2_source_matching_slant":"PASS_SOURCE_TITLE_UPRIGHT",
   "3_no_undersized_lettering":"PASS_NATIVE_146PX_HEIGHT_WITH_SOURCE_WORD_ANCHORS",
   "4_source_faithful_weight_effect":"PASS_BOLD_CONDENSED_NO_EXCESSIVE_A170_REINFORCEMENT",
   "5_no_clipped_pixels":"PASS_POSITIVE_FULL_TITLE_MARGIN",
   "6_protected_art_clearance":"PASS_ZERO_PROTECTED_OVERLAP",
   "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_CONFIRM",
   "8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_CONFIRM"
 },
 "c256_correction":"A170 1.15 horizontal expansion removed. B241 uses 0.62 horizontal glyph aspect and source-derived English word anchors; canonical numeral 2 is preserved pixel-faithfully instead of redrawn.",
 "execution_backend":"GITHUB_HOSTED_CPU_WORKER_REQUIRED_FOR_REPOSITORY_BACKED_DDS",
 "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
 "status":"B241_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"B241_Q212_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B241_Q212.json").write_text(json.dumps({"role":"B","run":RUN,"queue_index":212,"asset":"BA0147DA","candidate_sha256":csha,"report":str((out/"B241_Q212_REPORT.json").relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"candidate_sha256":csha,"rows":rows,"outside":outside,"alpha_out":alpha_out,"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2))
