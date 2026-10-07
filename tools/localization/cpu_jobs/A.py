#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A161-Q111-C075FB49-YELLOW-SCALE"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds"
source=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset_rel
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
a10=repo/"localization/graphics/role_A/20261004-A-RECOVERY10"
clean_path=a10/"C075FB49_CLEAN_PLATE.png"

SOURCE_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
BEFORE_SHA="d5fa574c85c0481bd82793a92d1a98b251005269ff343910c7b329030afd1633"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])

if sha(source)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(source)))
if sha(candidate)!=BEFORE_SHA: raise RuntimeError(("candidate drift",sha(candidate)))
sb=source.read_bytes(); ib=candidate.read_bytes()
if sb[:4]!=b"DDS " or ib[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
if (W,H,pitch,depth,mips)!=(2048,2048,8192,1,1): raise RuntimeError((W,H,pitch,depth,mips))
if ib[:128]!=sb[:128] or len(ib)!=len(sb): raise RuntimeError("header/size drift")
src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA"); src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
old_raw=Image.frombytes("RGBA",(W,H),ib[128:],"raw","RGBA"); old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=(W,H): raise RuntimeError("clean size")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT_PATTERN="Noto Sans CJK KR:style=Black"
FONT=subprocess.check_output(["fc-match","-f","%{file}",FONT_PATTERN],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))

# Concrete current-policy false negatives visible in A_RECOVERY12 SOURCE|OLD|NEW:
# these yellow instruction rows are roughly half the source-family height.
targets={
 "keep_passing":{"source":"Keep passing the cars!","old":"계속 차량을 추월하세요!","ko":"계속 추월하세요!","bbox":[1,143,520,236],"prior":[40,165,491,215],"shear":0.24},
 "drift":{"source":"Drift!","old":"드리프트!","ko":"드리프트!","bbox":[500,120,720,228],"prior":[517,149,707,200],"shear":0.20},
 "dont_crash":{"source":"Don't crash!","old":"충돌하지 마세요!","ko":"충돌하지 마세요!","bbox":[550,200,1070,370],"prior":[602,259,1024,324],"shear":0.24},
 "go_gate":{"source":"Go through the gate!","old":"게이트를 통과하세요!","ko":"게이트를 통과하세요!","bbox":[1020,200,1590,370],"prior":[1077,261,1539,319],"shear":0.24}
}

def shear_rgba(im,s):
    extra=max(8,int(math.ceil(abs(s)*im.height))+8)
    c=Image.new("RGBA",(im.width+extra*2,im.height),(0,0,0,0)); c.paste(im,(extra,0),im)
    coeff=(1,-s,s*c.height,0,1,0)
    x=c.transform(c.size,Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC)
    bb=x.getchannel("A").getbbox()
    return x.crop(bb) if bb else x

# Source yellow family: yellow face, dark navy keyline, white border, navy outside/depth.
Y=(255,215,52,255); N=(20,31,65,255); WHT=(248,248,248,255)
def fresh(text,maxw,maxh,shear):
    for fs in range(min(120,int(maxh*1.15)),34,-1):
        font=ImageFont.truetype(FONT,fs)
        tmp=Image.new("RGBA",(maxw*3,maxh*3),(0,0,0,0)); d=ImageDraw.Draw(tmp)
        bb=d.textbbox((18,18),text,font=font,stroke_width=8)
        x=18-bb[0]; y=18-bb[1]
        d.text((x,y),text,font=font,fill=Y,stroke_width=8,stroke_fill=N)
        d.text((x,y),text,font=font,fill=Y,stroke_width=6,stroke_fill=WHT)
        d.text((x,y),text,font=font,fill=Y,stroke_width=3,stroke_fill=N)
        gb=tmp.getchannel("A").getbbox()
        if not gb: continue
        g=tmp.crop(gb)
        g=shear_rgba(g,shear)
        hscale=1.0
        if g.height>maxh: continue
        if g.width>maxw:
            hscale=maxw/g.width
            if hscale<0.60: continue
            g=g.resize((maxw,g.height),Image.Resampling.LANCZOS)
            gb=g.getchannel("A").getbbox()
            if gb:g=g.crop(gb)
        if g.width<=maxw and g.height<=maxh:
            return fs,g,hscale
    raise RuntimeError(("fit",text,maxw,maxh))

final=old.copy()
rows={}
render_masks={}
for key,t in targets.items():
    x0,y0,x1,y1=t["bbox"]; prior=t["prior"]
    # Restore the entire exact source text/effect bbox from already validated clean plate.
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))
    maxw=(x1-x0)-6; maxh=(y1-y0)-6
    fs,g,hs=fresh(t["ko"],maxw,maxh,t["shear"])
    px=x0+3+(maxw-g.width)//2
    py=y0+3+(maxh-g.height)//2
    final.alpha_composite(g,(px,py))
    gm=Image.new("L",(W,H),0); gm.paste(g.getchannel("A"),(px,py)); render_masks[key]=gm
    loc=[px,py,px+g.width,py+g.height]
    if not(loc[0]>x0 and loc[1]>y0 and loc[2]<x1 and loc[3]<y1): raise RuntimeError(("margin",key,loc,t["bbox"]))
    rows[key]={"source":t["source"],"prior_korean":t["old"],"korean":t["ko"],"original_bbox":t["bbox"],"prior_bbox":prior,"localized_bbox_preencode":loc,
               "source_size":[x1-x0,y1-y0],"prior_size":[prior[2]-prior[0],prior[3]-prior[1]],"preencode_size":[g.width,g.height],
               "font":Path(FONT).name,"font_size":fs,"shear":t["shear"],"horizontal_scale":round(hs,4)}

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
outb=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(outb)
raw_dec=Image.frombytes("RGBA",(W,H),outb[128:],"raw","RGBA"); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")

# Blast radius is exactly the four source bboxes.
mask=Image.new("L",(W,H),0); md=ImageDraw.Draw(mask)
for t in targets.values():
    x0,y0,x1,y1=t["bbox"]; md.rectangle((x0,y0,x1-1,y1-1),fill=255)
diff=dmask(old,dec); outside=count(ImageChops.multiply(diff,ImageOps.invert(mask)))
ad=ImageChops.difference(old.getchannel("A"),dec.getchannel("A")).point(lambda v:255 if v else 0)
alpha_out=count(ImageChops.multiply(ad,ImageOps.invert(mask)))
if outside or alpha_out: raise RuntimeError(("blast",outside,alpha_out))

# Persisted DDS is lossless RGBA32 and exact roundtrip has already been asserted.
# Therefore the rendered alpha footprint is the authoritative persisted text footprint.
for key,t in targets.items():
    x0,y0,x1,y1=t["bbox"]
    loc=list(rows[key]["localized_bbox_preencode"])
    rows[key]["localized_bbox"]=loc; rows[key]["localized_size"]=[loc[2]-loc[0],loc[3]-loc[1]]
    rows[key]["delta_left"]=loc[0]-x0; rows[key]["delta_right"]=x1-loc[2]; rows[key]["delta_top"]=loc[1]-y0; rows[key]["delta_bottom"]=y1-loc[3]
    if not(loc[0]>x0 and loc[1]>y0 and loc[2]<x1 and loc[3]<y1): raise RuntimeError(("persisted margin",key,loc))
    prior_h=t["prior"][3]-t["prior"][1]; new_h=loc[3]-loc[1]
    if new_h < prior_h+12: raise RuntimeError(("insufficient height gain",key,prior_h,new_h))

# Coverage and zero-overlap for the four changed rows. Unchanged 13 rows are
# guaranteed by current->new blast-radius exactness outside the target union.
coverage=17
row_masks=render_masks
pair_overlap={}
keys=list(row_masks)
for i,k1 in enumerate(keys):
    for k2 in keys[i+1:]:
        ov=count(ImageChops.multiply(row_masks[k1],row_masks[k2]))
        if ov: pair_overlap[f"{k1}|{k2}"]=ov
if pair_overlap: raise RuntimeError(("localized overlap",pair_overlap))

def gray(im):
    bg=Image.new("RGBA",im.size,(72,72,72,255)); bg.alpha_composite(im); return bg.convert("RGB")

# SOURCE|OLD|CLEAN|FINAL row contacts.
contacts=[]
for key,t in targets.items():
    x0,y0,x1,y1=t["bbox"]; m=16; box=(max(0,x0-m),max(0,y0-m),min(W,x1+m),min(H,y1+m))
    ims=[gray(z.crop(box)) for z in (src,old,clean,dec)]
    sc=min(1.0,1800/(sum(i.width for i in ims)+30))
    if sc<1: ims=[i.resize((int(i.width*sc),int(i.height*sc)),Image.Resampling.LANCZOS) for i in ims]
    row=Image.new("RGB",(sum(i.width for i in ims)+30,max(i.height for i in ims)+28),(235,235,235)); xx=0
    ImageDraw.Draw(row).text((3,3),key+" SOURCE | C111 OLD | CLEAN | A161",fill="black")
    for im in ims: row.paste(im,(xx,28)); xx+=im.width+10
    contacts.append(row)
cw=max(i.width for i in contacts); ch=sum(i.height for i in contacts)+4*(len(contacts)-1)
sheet=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for im in contacts: sheet.paste(im,(0,yy)); yy+=im.height+4
sheet.save(out/"A161_C075_YELLOW_SOURCE_OLD_CLEAN_FINAL.jpg",quality=95)

# Full/practical and raw evidence.
full=Image.new("RGB",(2048,1024),(50,50,50)); full.paste(gray(old).resize((1024,1024),Image.Resampling.LANCZOS),(0,0)); full.paste(gray(dec).resize((1024,1024),Image.Resampling.LANCZOS),(1024,0)); full.save(out/"A161_C075_OLD_FINAL_FULL.jpg",quality=94)
raws=Image.new("RGB",(2048,1024),(50,50,50)); raws.paste(gray(old_raw).resize((1024,1024),Image.Resampling.LANCZOS),(0,0)); raws.paste(gray(raw_dec).resize((1024,1024),Image.Resampling.LANCZOS),(1024,0)); raws.save(out/"A161_C075_OLD_FINAL_RAW.jpg",quality=94)
pr=[]
for pct in (100,75,50):
    crop=gray(dec.crop((0,100,1600,390))); size=(int(crop.width*pct/100),int(crop.height*pct/100)); pr.append(crop.resize(size,Image.Resampling.LANCZOS))
pw=max(i.width for i in pr); ph=sum(i.height for i in pr)+50
ps=Image.new("RGB",(pw,ph),"white"); yy=0; d=ImageDraw.Draw(ps)
for pct,im in zip((100,75,50),pr): d.text((2,yy),f"{pct}% decoded persisted",fill="black"); yy+=18; ps.paste(im,(0,yy)); yy+=im.height+8
ps.save(out/"A161_C075_PRACTICAL_100_75_50.jpg",quality=94)

report={"schema_version":1,"role":"A","run":"A161","index":111,"asset":asset_rel,
 "trigger":"POST_ENCODE_PRESENTATION_HARDENING_YELLOW_INSTRUCTION_SCALE_FALSE_NEGATIVE",
 "prior_c_status":"C111_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","prior_candidate_sha256":BEFORE_SHA,"source_sha256":SOURCE_SHA,
 "candidate_sha256":sha(candidate),"reworked_keys":list(targets),"translation_change":{"keep_passing":"계속 차량을 추월하세요! -> 계속 추월하세요!"},
 "rows":rows,
 "machine_qa":{"coverage":"17/17 PASS","changed_pixels_outside_declared_rework_mask":outside,"alpha_changed_outside_declared_rework_mask":alpha_out,"localized_pair_overlap":pair_overlap,"header_128_exact":outb[:128]==sb[:128],"mip_count":mips,"rgba32_roundtrip_exact":True,"raw_orientation":"mirror_y"},
 "ui_family":"selector yellow instruction family","style_profile":"yellow face + navy keyline + white border + navy outer edge; readable right lean 0.20-0.24",
 "post_encode":{"authority":"decoded persisted DDS","practical_scales":[100,75,50],"text_bearing_mips":1,"status":"PASS_PENDING_CONTROLLER_VISUAL"},
 "ordered_generation_gate":{"1_plate_restoration":"PASS_A_RECOVERY10_VALIDATED_CLEAN","2_slant_direction":"PASS_RIGHT_LEAN","3_no_unnecessary_undersizing":"PASS_MATERIAL_HEIGHT_GAIN_ALL_4","4_weight_outline_shadow":"PASS_SOURCE_YELLOW_NAVY_WHITE_FAMILY","5_clipping":"PASS_POSITIVE_MARGIN_ALL_4","6_protected_clearance":"PASS_ZERO_OUTSIDE_REWORK_MASK","7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER","8_readability":"PENDING_CONTROLLER"},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","status":"A161_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA","runtime_validation":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True}
(out/"A161_C075FB49_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":"A161","index":111,"asset":"C075FB49","candidate_sha256":report["candidate_sha256"],"reworked_keys":list(targets),"coverage":"17/17 PASS","outside":outside,"alpha_outside":alpha_out,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261007-A161-Q111-C075FB49-YELLOW-SCALE/A161_C075FB49_REPORT.json"}
(wr/"A161_C075FB49.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
