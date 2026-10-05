#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted role C required")

repo=Path.cwd()
run="20261006-C220-37759842-TRANSFORM"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
input_sha="e581da473a69acf8b2dbb651fb44668b5d61177459bc556fcf775a15bfef86a7"
source_sha="7b41a04e2b0736717dd0da4d82f9e18f3aac7c469a5738848c5cfa6bf28e15b5"
a81=repo/"localization/graphics/role_A/20261006-A-PRODUCTION81-3775-BBOX"
r81=json.loads((a81/"A81_37759842_REPORT.json").read_text(encoding="utf-8"))
clean=Image.open(a81/"37759842_HD_CLEAN_PLATE.png").convert("RGBA")
producer_src=Image.open(a81/"37759842_HD_SOURCE_READABLE.png").convert("RGBA")
core=Image.open(a81/"37759842_HD_SOURCE_CORE_MASK.png").convert("L")
protected=Image.open(a81/"37759842_HD_PROTECTED_VISIBLE_MASK.png").convert("L")
rows=r81["rows"]
TARGET_KINDS={"continuous","continuous_small","mode","mode_small"}
targets=[r for r in rows if r["kind"] in TARGET_KINDS]
if len(targets)!=16: raise RuntimeError(("target rows",len(targets)))

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_path(p): return sha_bytes(Path(p).read_bytes())
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); z=d.split(); m=z[0]
    for q in z[1:]: m=ImageChops.lighter(m,q)
    return bmask(m)
def flatten(im):
    bg=Image.new("RGBA",im.size,(92,92,92,255)); bg.alpha_composite(im); return bg.convert("RGB")

# Independent canonical source fetch.
tmp=Path("/tmp/c220"); tmp.mkdir(exist_ok=True)
srcdds=tmp/"source.dds"
urllib.request.urlretrieve(
 "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds",
 srcdds)
sb=srcdds.read_bytes(); cb=candidate.read_bytes()
if sha_bytes(sb)!=source_sha: raise RuntimeError(("source SHA",sha_bytes(sb)))
if sha_bytes(cb)!=input_sha: raise RuntimeError(("candidate SHA",sha_bytes(cb)))
if sb[:128]!=cb[:128]: raise RuntimeError("header mismatch")
if cb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",cb,12)
if (W,H,pitch,depth,mips)!=(4096,4096,16384,1,1): raise RuntimeError((W,H,pitch,depth,mips))
src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(src,producer_src).getbbox() is not None: raise RuntimeError("producer source drift")
old_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

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
    extra=max(5,int(round(abs(k)*im.height))+8)
    c=Image.new("RGBA",(im.width+extra*2,im.height),(0,0,0,0)); c.alpha_composite(im,(extra,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,-k,k*c.height,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=o.getchannel("A").getbbox()
    return o.crop(bb) if bb else o

def line_bands(row,n):
    x0,y0,x1,y1=map(int,row["source_effect_bbox"])
    a=np.asarray(core.crop((x0,y0,x1,y1)))>0
    active=np.where(a.any(axis=1))[0]
    if len(active)==0: raise RuntimeError(("no core rows",row["idx"]))
    gaps=[(int(active[i+1]-active[i]),i) for i in range(len(active)-1)]
    cuts=sorted(i for _,i in sorted(gaps,reverse=True)[:max(0,n-1)])
    groups=[]; st=0
    for ci in cuts:
        groups.append(active[st:ci+1]); st=ci+1
    groups.append(active[st:])
    groups=sorted(groups,key=lambda g:g[0])
    if len(groups)!=n: raise RuntimeError(("band split",row["idx"],n,len(groups)))
    all_x=np.where(a)[1]; overall_xmin=int(all_x.min())
    bands=[]
    for g in groups:
        gy0,gy1=int(g[0]),int(g[-1])+1
        sub=a[gy0:gy1,:]; xs=np.where(sub)[1]
        bands.append({"y0":y0+gy0,"y1":y0+gy1,
                      "source_core_xmin":x0+int(xs.min()),
                      "source_indent":int(xs.min())-overall_xmin})
    return bands

def render_one(text,style,fs):
    fill,edge,shadow=palette(style)
    font=ImageFont.truetype(FONT,fs,index=FI)
    sw=max(2,min(7,int(round(fs*0.055))))
    dr=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=dr.textbbox((0,0),text,font=font,stroke_width=sw)
    pad=sw*4+12
    base=Image.new("RGBA",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),(0,0,0,0))
    d=ImageDraw.Draw(base)
    d.text((pad-bb[0]+3,pad-bb[1]+4),text,font=font,fill=shadow,stroke_width=sw,stroke_fill=edge)
    d.text((pad-bb[0],pad-bb[1]),text,font=font,fill=fill,stroke_width=sw,stroke_fill=edge)
    base=shear_rgba(base,0.24)
    return base,sw

final=old.copy()
allowed=Image.new("L",(W,H),0); ad=ImageDraw.Draw(allowed)
new_union=Image.new("L",(W,H),0)
row_results=[]
for row in targets:
    ob=list(map(int,row["source_effect_bbox"])); x0,y0,x1,y1=ob
    ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
    lines=list(row["korean_lines"]); bands=line_bands(row,len(lines))
    source_block_center=(bands[0]["y0"]+bands[-1]["y1"])/2.0

    chosen=None
    start_fs=int(row["font_size"])
    for fs in range(start_fs,17,-1):
        rendered=[render_one(t,row["style"],fs) for t in lines]
        gap=max(2,int(round(fs*0.06)))
        total_h=sum(im.height for im,_ in rendered)+gap*(len(rendered)-1)
        if total_h>=(y1-y0-4): continue
        ok=True
        for (im,_),b in zip(rendered,bands):
            anchor=x0+3+int(b["source_indent"])
            if im.width > x1-anchor-3: ok=False; break
        if ok:
            chosen=(fs,gap,total_h,rendered); break
    if chosen is None: raise RuntimeError(("shared block fit",row["idx"],lines,ob))
    fs,gap,total_h,rendered=chosen
    block_top=int(round(source_block_center-total_h/2.0))
    block_top=max(y0+2,min(block_top,y1-total_h-2))
    yy=block_top
    row_mask=Image.new("L",(W,H),0); line_meta=[]
    for txt,b,(layer,sw) in zip(lines,bands,rendered):
        tx=x0+3+int(b["source_indent"]); ty=yy
        lm=bmask(layer.getchannel("A")); tm=Image.new("L",(W,H),0); tm.paste(lm,(tx,ty))
        lb=list(tm.getbbox() or ())
        if not lb or not(lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1):
            raise RuntimeError(("line bbox",row["idx"],txt,ob,lb))
        if count(ImageChops.multiply(row_mask,tm))!=0: raise RuntimeError(("line overlap",row["idx"],txt))
        row_mask=ImageChops.lighter(row_mask,tm); new_union=ImageChops.lighter(new_union,tm)
        final.paste(layer,(tx,ty),lm)
        line_meta.append({"line":txt,"source_core_band":[b["y0"],b["y1"]],
                          "source_indent_px":int(b["source_indent"]),"localized_bbox":lb,
                          "font_size":fs,"stroke_px":sw,"shear":0.24,"alignment":"source_left"})
        yy += layer.height + gap
    rb=list(row_mask.getbbox() or ())
    if not rb or not(rb[0]>x0 and rb[1]>y0 and rb[2]<x1 and rb[3]<y1):
        raise RuntimeError(("row bbox",row["idx"],ob,rb))
    row_results.append({"idx":int(row["idx"]),"kind":row["kind"],"source_effect_bbox":ob,"localized_bbox":rb,
                        "delta_left":rb[0]-x0,"delta_right":x1-rb[2],"delta_top":rb[1]-y0,"delta_bottom":y1-rb[3],
                        "source_size":[x1-x0,y1-y0],"localized_size":[rb[2]-rb[0],rb[3]-rb[1]],
                        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
                        "shared_font_size":fs,"shared_line_gap_px":gap,"lines":line_meta})

# Exact DDS encode.
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
newb=cb[:128]+raw.tobytes("raw","RGBA")
candidate.write_bytes(newb)
csha=sha_bytes(newb)
dec_raw=Image.frombytes("RGBA",(W,H),newb[128:],"raw","RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")

# Independent material-rework gates.
diff=dmask(old,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_diff=bmask(ImageChops.difference(old.getchannel("A"),dec.getchannel("A")))
alpha_out=count(ImageChops.multiply(alpha_diff,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(dmask(src,dec),protected))
same=ImageOps.invert(dmask(src,dec))
core_touched=ImageChops.multiply(core,allowed)
guard=new_union.filter(ImageFilter.MaxFilter(5))
residue=count(ImageChops.multiply(core_touched,ImageChops.multiply(same,ImageOps.invert(guard))))
# All non-C219-returned candidate pixels must remain exactly A81.
if any(v!=0 for v in (outside,alpha_out,protected_changed,residue)):
    raise RuntimeError(("zero gate fail",outside,alpha_out,protected_changed,residue))

# Re-derive final localized bboxes from clean->decoded render pixels.
bbox_mismatch=0
for rr in row_results:
    x0,y0,x1,y1=rr["source_effect_bbox"]
    rm=dmask(clean.crop((x0,y0,x1,y1)),dec.crop((x0,y0,x1,y1)))
    bb=rm.getbbox()
    ib=[x0+bb[0],y0+bb[1],x0+bb[2],y0+bb[3]] if bb else None
    rr["localized_bbox_independent"]=ib
    rr["localized_bbox_exact_match"]=ib==rr["localized_bbox"]
    if not rr["localized_bbox_exact_match"]: bbox_mismatch+=1
if bbox_mismatch: raise RuntimeError(("bbox mismatch",bbox_mismatch))

# SOURCE | CLEAN | A81 | C220 contacts.
cards=[]; lab=ImageFont.truetype(FONT,20,index=FI)
for rr in row_results:
    ob=rr["source_effect_bbox"]; pad=12
    box=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(W,ob[2]+pad),min(H,ob[3]+pad))
    ims=[flatten(z.crop(box)) for z in (src,clean,old,dec)]
    scaled=[]
    for q in ims:
        sc=min(1.0,160/max(1,q.height),320/max(1,q.width))
        scaled.append(q.resize((max(1,int(q.width*sc)),max(1,int(q.height*sc))),Image.Resampling.LANCZOS) if sc<1 else q)
    cw=sum(q.width for q in scaled)+18; ch=max(q.height for q in scaled)+28
    card=Image.new("RGB",(cw,ch),(230,230,230)); d=ImageDraw.Draw(card)
    d.text((4,4),f"idx {rr['idx']} SOURCE | CLEAN | A81 | C220",font=lab,fill=(0,0,0))
    xx=0
    for q in scaled: card.paste(q,(xx,28)); xx+=q.width+6
    cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height+3 for c in cards)
sheet=Image.new("RGB",(cw,ch),(225,225,225)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+3
sheet.save(out/"C220_TRANSFORM_CONTACTS.jpg",quality=94)

full=Image.new("RGB",(1024*4,1024),(90,90,90))
for i,z in enumerate((src,clean,old,dec)): full.paste(flatten(z).resize((1024,1024),Image.Resampling.LANCZOS),(i*1024,0))
full.save(out/"C220_SOURCE_CLEAN_A81_C220_FULL.jpg",quality=94)
rawcmp=Image.new("RGB",(2048,1024),(90,90,90))
rawcmp.paste(flatten(src_raw).resize((1024,1024),Image.Resampling.LANCZOS),(0,0))
rawcmp.paste(flatten(dec_raw).resize((1024,1024),Image.Resampling.LANCZOS),(1024,0))
rawcmp.save(out/"C220_RAW_COMPARE.jpg",quality=94)

report={"schema_version":1,"role":"C","run":run,"qa_id":"C220","queue_index":95,"asset":asset_rel,
 "source_sha256":source_sha,"input_candidate_sha256":input_sha,"candidate_sha256":csha,
 "candidate_path":str(candidate.relative_to(repo)),"c219_return":"FAIL_SOURCE_TRANSFORM_ALIGNMENT_SLANT",
 "user_ingame_regressions":["IGR-014","IGR-015","IGR-016"],
 "small_corrective_rework":"Preserved A81 manual clean plate and every non-C219-returned candidate pixel; re-rendered only 16 continuous/mode selector rows as shared-font source-left blocks with per-line source indent, true 0.24 shear and consistent line gap.",
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"header_128_exact":newb[:128]==cb[:128],"raw_orientation":"mirror_y"},
 "rows":row_results,
 "machine_checks":{"changes_outside_c219_transform_rows":outside,"alpha_changes_outside_c219_transform_rows":alpha_out,
                   "protected_source_pixels_changed":protected_changed,"source_core_residue_outside_new_korean_guard":residue,
                   "localized_bbox_mismatches":bbox_mismatch,"untouched_a81_pixels":"PIXEL_EXACT"},
 "machine_status":"PASS","controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA","candidate_changed_by_C":True,
 "runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "preview_files":[str((out/"C220_TRANSFORM_CONTACTS.jpg").relative_to(repo)),
                  str((out/"C220_SOURCE_CLEAN_A81_C220_FULL.jpg").relative_to(repo)),
                  str((out/"C220_RAW_COMPARE.jpg").relative_to(repo))]}
(out/"C220_37759842_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C220_37759842.json").write_text(json.dumps({"run":run,"qa_id":"C220","index":95,"asset":"37759842",
 "candidate_sha256":csha,"machine_status":"PASS","machine_checks":report["machine_checks"],
 "worker_status":"C220_SMALL_REWORK_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA",
 "runtime_validation":"PENDING_NEW_INGAME_RETEST","report":str((out/"C220_37759842_MACHINE_QA.json").relative_to(repo))},
 ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"candidate_sha256":csha,"rows":len(row_results),"machine_checks":report["machine_checks"]},ensure_ascii=False,indent=2))
