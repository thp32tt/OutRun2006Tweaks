#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261006-A-PRODUCTION83-C219-TRANSFORM"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
input_sha="e581da473a69acf8b2dbb651fb44668b5d61177459bc556fcf775a15bfef86a7"
source_sha="7b41a04e2b0736717dd0da4d82f9e18f3aac7c469a5738848c5cfa6bf28e15b5"
a81=repo/"localization/graphics/role_A/20261006-A-PRODUCTION81-3775-BBOX"
r81=json.loads((a81/"A81_37759842_REPORT.json").read_text(encoding="utf-8"))
clean=Image.open(a81/"37759842_HD_CLEAN_PLATE.png").convert("RGBA")
src=Image.open(a81/"37759842_HD_SOURCE_READABLE.png").convert("RGBA")
core=Image.open(a81/"37759842_HD_SOURCE_CORE_MASK.png").convert("L")
rows=r81["rows"]
TARGET_KINDS={"continuous","continuous_small","mode","mode_small"}
targets=[r for r in rows if r["kind"] in TARGET_KINDS]
if len(targets)!=16: raise RuntimeError(("target rows",len(targets)))

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); z=d.split(); m=z[0]
    for q in z[1:]: m=ImageChops.lighter(m,q)
    return bmask(m)
def flatten(im):
    bg=Image.new("RGBA",im.size,(92,92,92,255)); bg.alpha_composite(im); return bg.convert("RGB")

if sha(candidate)!=input_sha: raise RuntimeError(("input SHA drift",sha(candidate)))
cb=candidate.read_bytes()
if cb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",cb,12)
if (W,H,pitch,depth,mips)!=(4096,4096,16384,1,1): raise RuntimeError((W,H,pitch,depth,mips))
old_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if old.size!=clean.size or src.size!=old.size: raise RuntimeError("evidence size drift")

def fontspec():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try:q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except Exception:q=""
        if "|" in q:
            p,ix=q.rsplit("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:return p,int(ix or 0),pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Black"],text=True).strip()
    p,ix=q.rsplit("|",1); return p,int(ix or 0),"Noto Sans CJK KR:style=Black"
FONT,FI,FPAT=fontspec()

def palette(style):
    return {
      "orange_blue":((244,148,25,255),(25,35,55,255),(8,12,18,215)),
      "white_dark":((238,238,233,255),(26,27,33,255),(5,5,8,215)),
    }[style]

def shear_rgba(im,k):
    # True source-style shear factor across the rendered line height. A81 used
    # fs-scaled pixel offsets that became too weak on multi-line stacks.
    extra=max(4,int(round(abs(k)*im.height))+6)
    c=Image.new("RGBA",(im.width+extra*2,im.height),(0,0,0,0)); c.alpha_composite(im,(extra,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,-k,k*c.height,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=o.getchannel("A").getbbox()
    return o.crop(bb) if bb else o

def line_bands(row,n):
    x0,y0,x1,y1=row["source_effect_bbox"]
    a=np.asarray(core.crop((x0,y0,x1,y1)))>0
    active=np.where(a.any(axis=1))[0]
    if len(active)==0: raise RuntimeError(("no core rows",row["idx"]))
    # Split at the n-1 largest vertical gaps in the source core projection.
    gaps=[(int(active[i+1]-active[i]),i) for i in range(len(active)-1)]
    cuts=sorted(i for _,i in sorted(gaps,reverse=True)[:max(0,n-1)])
    groups=[]; st=0
    for ci in cuts:
        groups.append(active[st:ci+1]); st=ci+1
    groups.append(active[st:])
    groups=sorted(groups,key=lambda g:g[0])
    if len(groups)!=n: raise RuntimeError(("band split",row["idx"],n,len(groups)))
    bands=[]
    all_x=np.where(a)[1]; overall_xmin=int(all_x.min())
    for g in groups:
        gy0,gy1=int(g[0]),int(g[-1])+1
        sub=a[gy0:gy1,:]
        xs=np.where(sub)[1]
        if len(xs)==0: raise RuntimeError(("empty line band",row["idx"]))
        bands.append({"y0":y0+gy0,"y1":y0+gy1,"center":y0+(gy0+gy1)/2.0,
                      "source_core_xmin":x0+int(xs.min()),"source_indent":int(xs.min())-overall_xmin})
    return bands

def render_line(text,style,fs,stroke,maxw,maxh):
    fill,edge,shadow=palette(style)
    for fsz in range(fs,max(13,fs-28),-1):
        font=ImageFont.truetype(FONT,fsz,index=FI)
        sw=max(2,min(7,int(round(fsz*0.055))))
        dr=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=dr.textbbox((0,0),text,font=font,stroke_width=sw)
        pad=sw*4+12
        base=Image.new("RGBA",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),(0,0,0,0))
        d=ImageDraw.Draw(base)
        # Source family uses a directional depth/shadow behind the same slanted line.
        d.text((pad-bb[0]+3,pad-bb[1]+4),text,font=font,fill=shadow,stroke_width=sw,stroke_fill=edge)
        d.text((pad-bb[0],pad-bb[1]),text,font=font,fill=fill,stroke_width=sw,stroke_fill=edge)
        base=shear_rgba(base,0.24)
        if base.width<=maxw and base.height<=maxh:
            return base,fsz,sw
    raise RuntimeError(("line fit",text,style,fs,maxw,maxh))

final=old.copy()
allowed=Image.new("L",(W,H),0); ad=ImageDraw.Draw(allowed)
new_union=Image.new("L",(W,H),0)
row_results=[]
for row in targets:
    ob=list(row["source_effect_bbox"]); x0,y0,x1,y1=ob
    ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
    # Preserve A81 manual clean plate exactly; only lettering is reworked.
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
    lines=row["korean_lines"]; bands=line_bands(row,len(lines))
    centers=[b["center"] for b in bands]
    boundaries=[y0+2]
    for i in range(len(centers)-1): boundaries.append(int(round((centers[i]+centers[i+1])/2)))
    boundaries.append(y1-2)
    line_meta=[]; row_mask=Image.new("L",(W,H),0)
    for i,(txt,b) in enumerate(zip(lines,bands)):
        sy0,sy1=boundaries[i],boundaries[i+1]
        slot_h=max(8,sy1-sy0-4)
        # Preserve source indentation between lines; all new effect pixels remain
        # positively inside the exact source effect bbox.
        anchor=x0+3+b["source_indent"]
        maxw=max(8,x1-anchor-3)
        layer,fs,sw=render_line(txt,row["style"],int(row["font_size"]),int(row["stroke_px"]),maxw,slot_h)
        tx=anchor
        ty=int(round(b["center"]-layer.height/2))
        ty=max(sy0+2,min(ty,sy1-layer.height-2))
        if ty<=y0: ty=y0+2
        if ty+layer.height>=y1: ty=y1-layer.height-2
        lm=bmask(layer.getchannel("A")); tm=Image.new("L",(W,H),0); tm.paste(lm,(tx,ty))
        lb=list(tm.getbbox() or ())
        if not lb or not (lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1):
            raise RuntimeError(("line bbox",row["idx"],i,ob,lb))
        if count(ImageChops.multiply(row_mask,tm))!=0: raise RuntimeError(("line overlap",row["idx"],i))
        row_mask=ImageChops.lighter(row_mask,tm); new_union=ImageChops.lighter(new_union,tm)
        final.paste(layer,(tx,ty),lm)
        line_meta.append({"line":txt,"source_core_band":[b["y0"],b["y1"]],"source_indent_px":b["source_indent"],
                          "slot":[sy0,sy1],"localized_bbox":lb,"font_size":fs,"stroke_px":sw,"shear":0.24})
    rb=list(row_mask.getbbox() or ())
    if not rb or not (rb[0]>x0 and rb[1]>y0 and rb[2]<x1 and rb[3]<y1): raise RuntimeError(("row bbox",row["idx"],rb))
    row_results.append({"idx":row["idx"],"kind":row["kind"],"source_effect_bbox":ob,"localized_bbox":rb,
                        "delta_left":rb[0]-x0,"delta_right":x1-rb[2],"delta_top":rb[1]-y0,"delta_bottom":y1-rb[3],
                        "source_size":[x1-x0,y1-y0],"localized_size":[rb[2]-rb[0],rb[3]-rb[1]],
                        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","lines":line_meta})

# Encode exact A81/canonical RGBA32 header and mirror_y raw orientation.
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
candidate.write_bytes(cb[:128]+raw.tobytes("raw","RGBA"))
csha=sha(candidate)
dec_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw","RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")
decp=out/"37759842_A83_FINAL_READABLE.png"; dec.save(decp)

# Scoped material-rework gates: no changes beyond C219-returned transform rows relative to A81.
diff=dmask(old,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_diff=bmask(ImageChops.difference(old.getchannel("A"),dec.getchannel("A")))
alpha_out=count(ImageChops.multiply(alpha_diff,ImageOps.invert(allowed)))
preserved_outside=outside
clean_diff=dmask(clean,Image.composite(dec,clean,allowed))
# Source-core residue outside new Korean glyph/effect guard in touched rows.
same=ImageOps.invert(dmask(src,dec))
core_touched=ImageChops.multiply(core,allowed)
guard=new_union.filter(ImageFilter.MaxFilter(5)) if False else new_union
# Use a 2px Pillow dilation without large-filter ambiguity.
guard=new_union.filter(ImageFilter.MaxFilter(5))
residue=count(ImageChops.multiply(core_touched,ImageChops.multiply(same,ImageOps.invert(guard))))
# Pairwise exact overlap of all new target lines/rows.
# row source bboxes are disjoint physical atlas regions; within-row line overlap was checked above.
if any(v!=0 for v in (outside,alpha_out,residue)): raise RuntimeError(("zero gate fail",outside,alpha_out,residue))

# Build compact SOURCE | CLEAN | A81 | A83 contacts for every C219-returned row.
cards=[]
lab=ImageFont.truetype(FONT,20,index=FI)
for rr in row_results:
    ob=rr["source_effect_bbox"]; pad=12
    box=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(W,ob[2]+pad),min(H,ob[3]+pad))
    ims=[flatten(z.crop(box)) for z in (src,clean,old,dec)]
    scaled=[]
    for q in ims:
        sc=min(1.0,145/max(1,q.height),300/max(1,q.width))
        scaled.append(q.resize((max(1,int(q.width*sc)),max(1,int(q.height*sc))),Image.Resampling.LANCZOS) if sc<1 else q)
    cw=sum(q.width for q in scaled)+18; ch=max(q.height for q in scaled)+28
    card=Image.new("RGB",(cw,ch),(230,230,230)); d=ImageDraw.Draw(card)
    d.text((4,4),f"idx {rr['idx']} SOURCE | CLEAN | A81 | A83",font=lab,fill=(0,0,0))
    xx=0
    for q in scaled: card.paste(q,(xx,28)); xx+=q.width+6
    cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height+3 for c in cards)
sheet=Image.new("RGB",(cw,ch),(225,225,225)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+3
sheet.save(out/"A83_C219_TRANSFORM_CONTACTS.jpg",quality=94)

full=Image.new("RGB",(1024*3,1024),(90,90,90))
for i,z in enumerate((src,old,dec)): full.paste(flatten(z).resize((1024,1024),Image.Resampling.LANCZOS),(i*1024,0))
full.save(out/"A83_SOURCE_A81_A83_FULL.jpg",quality=94)
flatten(dec_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A83_FINAL_RAW_MIRROR_Y.jpg",quality=94)

report={"schema_version":1,"role":"A","run":run,"queue_index":95,"asset":asset_rel,
 "source_sha256":source_sha,"input_candidate_sha256":input_sha,"candidate_sha256":csha,
 "candidate_path":str(candidate.relative_to(repo)),"c219_return":"FAIL_SOURCE_TRANSFORM_ALIGNMENT_SLANT",
 "user_ingame_regressions":["IGR-014","IGR-015","IGR-016"],
 "method":"preserve A81 full-bbox manual clean plate and all non-returned candidate pixels; rerender only 16 continuous/mode rows using source line-band vertical centers, preserved per-line source indents, true 0.24 shear, left anchors and native Korean glyphs",
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"header_128_exact":candidate.read_bytes()[:128]==cb[:128],"raw_orientation":"mirror_y"},
 "rows":row_results,"all_16_containment_size_positive_margin_pass":all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in row_results),
 "machine_checks":{"changes_outside_c219_transform_rows":outside,"alpha_changes_outside_c219_transform_rows":alpha_out,
                   "source_core_residue_outside_new_korean_guard":residue,"untouched_a81_pixels":"PIXEL_EXACT"},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"A83_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA"}
(out/"A83_37759842_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A83_37759842.json").write_text(json.dumps({"run":run,"index":95,"asset":"37759842","candidate_sha256":csha,
 "c219_transform_rows":16,"bbox_size_margin":"16/16 PASS","outside":outside,"alpha_outside":alpha_out,"source_residue":residue,
 "worker_status":report["status"],"runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "report":str((out/"A83_37759842_REPORT.json").relative_to(repo))},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"candidate_sha256":csha,"rows":len(row_results),"outside":outside,"alpha_outside":alpha_out,"residue":residue},ensure_ascii=False))
