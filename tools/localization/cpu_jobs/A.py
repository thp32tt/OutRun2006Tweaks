#!/usr/bin/env python3
# A165R: q28 retry after controller rejected A165 historical CLEAN crop
# for a visible rectangular/luminance patch. Rebuild the exact canonical source
# text bbox from a local polynomial fit to its intact surrounding source plate.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
import hashlib,json,struct,math,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops

repo=Path.cwd(); run="20261007-A165R-Q028-A05BF610-CLEAN-RETRY"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
SOURCE_SHA="52cb2a5697e9efc81de4c74fcb669b44e70503c4ea54e913023f10c424371129"
BEFORE_SHA="372d2f4056308fbbfef04fdf1735a6c722aecca9246d7b121f27b28f86479a72"
A144_SHA="aa0692a2918326a494c1b04837603313faac7bdd9b7f043d4b679a8e8b1493f9"
BOX=[543,1185,1068,1275]; TARGET=(476,80)
FONT_INDEX=1

def sha(b):return hashlib.sha256(b).hexdigest()
def decode(b):
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12);pf=struct.unpack_from("<8I",b,76);m=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if m[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if m[:3]==(0xff0000,0xff00,0xff) else None)
    if b[:4]!=b"DDS " or mode is None or (w,h)!=(2048,2048) or mips!=1 or len(b)!=128+w*h*4:raise RuntimeError(("dds",w,h,mips,m))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode);return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mode":mode,"mips":mips,"masks":m}
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255));z.alpha_composite(im);return z.convert("RGB")
def bbox(mask):
    ys,xs=np.nonzero(mask);return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def render(text,fs=80,stroke=3,slant=.30,ss=4):
    font=ImageFont.truetype(str(FONT),fs*ss,index=FONT_INDEX);dummy=Image.new("L",(1,1));d=ImageDraw.Draw(dummy)
    tb=d.textbbox((0,0),text,font=font,stroke_width=stroke*ss);pad=96*ss
    lay=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0));ld=ImageDraw.Draw(lay)
    ld.text((pad-tb[0],pad-tb[1]),text,font=font,fill=(255,255,255,255),stroke_width=stroke*ss,stroke_fill=(8,16,57,255))
    lay=lay.crop(lay.getbbox());extra=int(math.ceil(abs(slant)*lay.height))+40*ss
    tr=lay.transform((lay.width+extra,lay.height),Image.Transform.AFFINE,(1,-slant,extra//3,0,1,0),resample=Image.Resampling.BICUBIC)
    tr=tr.crop(tr.getbbox());return tr.resize(TARGET,Image.Resampling.LANCZOS)

FONT_CANDIDATES=[Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"),Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")]
FONT=next((p for p in FONT_CANDIDATES if p.exists()),None)
if FONT is None:
    subprocess.run(["sudo","apt-get","update","-qq"],check=True);subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    FONT=next((p for p in FONT_CANDIDATES if p.exists()),None)
if FONT is None:raise RuntimeError("font missing")

cb=cand.read_bytes()
if sha(cb)!=BEFORE_SHA:raise RuntimeError(("candidate drift",sha(cb),BEFORE_SHA))
raw,old,meta=decode(cb)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds"
tmp=Path("/tmp/A05BF610_source.dds");urllib.request.urlretrieve(url,tmp);sb=tmp.read_bytes()
if sha(sb)!=SOURCE_SHA:raise RuntimeError(("source drift",sha(sb)))
sraw,source,smeta=decode(sb)
if smeta!=meta or sb[:128]!=cb[:128]:raise RuntimeError("structure mismatch")

# Recover A144 exact bytes for outside-scope authority. A165 changed only BOX,
# but this proves retry cannot accumulate unrelated changes.
a144=subprocess.check_output(["git","show","9c69f004a20e8dc086a32b716b682cbe33d8e184^:localization/graphics/hd_candidates/"+asset])
if sha(a144)!=A144_SHA:raise RuntimeError(("A144 base drift",sha(a144)))
ta=Path("/tmp/A05_A144.dds");ta.write_bytes(a144);_,a144read,_=decode(a144)

x0,y0,x1,y1=BOX;pad=32
src=np.asarray(source).astype(np.float64)
rx0,ry0,rx1,ry1=x0-pad,y0-pad,x1+pad,y1+pad
region=src[ry0:ry1,rx0:rx1,:]
hh,ww=region.shape[:2]
yy,xx=np.mgrid[0:hh,0:ww]
inner=(xx>=pad)&(xx<pad+(x1-x0))&(yy>=pad)&(yy<pad+(y1-y0))
ring=~inner
# Fit a smooth local plate surface from intact 32px surrounding ring. Normalized
# cubic basis captures the oval's gentle luminance/color gradient without a box.
xn=(xx-(ww-1)/2)/max(1,ww/2);yn=(yy-(hh-1)/2)/max(1,hh/2)
features=np.stack([np.ones_like(xn),xn,yn,xn*xn,yn*yn,xn*yn,xn**3,yn**3,(xn*xn)*yn,xn*(yn*yn)],axis=-1)
X=features[ring]
pred=np.empty_like(region)
for ch in range(3):
    coef,*_=np.linalg.lstsq(X,region[:,:,ch][ring],rcond=None)
    pred[:,:,ch]=features@coef
pred[:,:,3]=255
pred=np.clip(np.rint(pred),0,255).astype(np.uint8)

clean=old.copy()
clean_patch=Image.fromarray(pred[pad:pad+(y1-y0),pad:pad+(x1-x0),:],"RGBA")
clean.paste(clean_patch,(x0,y0))
# Edge continuity metric against intact canonical source immediately outside bbox
# and inside first 2px of fitted bbox boundary.
clean_np=np.asarray(clean).astype(np.int16);source_np=np.asarray(source).astype(np.int16)
edge=np.zeros((y1-y0,x1-x0),bool);edge[:2,:]=True;edge[-2:,:]=True;edge[:,:2]=True;edge[:,-2:]=True
edge_delta=np.abs(clean_np[y0:y1,x0:x1,:3]-source_np[y0:y1,x0:x1,:3])[edge]
edge_mean=float(edge_delta.mean());edge_p95=float(np.percentile(edge_delta,95))
# Plate fit must not be wildly discontinuous. Controller visual remains authority.
if edge_mean>35 or edge_p95>80:raise RuntimeError(("plate edge fit too far from source",edge_mean,edge_p95))

final=clean.copy();layer=render("종합 랭킹");px=x0+((x1-x0)-layer.width)//2;py=y0+((y1-y0)-layer.height)//2
if min(px-x0,x1-(px+layer.width),py-y0,y1-(py+layer.height))<2:raise RuntimeError("margin")
tmpim=Image.new("RGBA",final.size,(0,0,0,0));tmpim.alpha_composite(layer,(px,py));final.alpha_composite(tmpim)
lm=np.asarray(tmpim.getchannel("A"))>0;lb=bbox(lm);margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
if min(margins)<2:raise RuntimeError(("bbox margin",margins))
# Current->retry and A144->retry blast radius restricted to exact canonical source box.
old_np=np.asarray(old);fin_np=np.asarray(final);a144_np=np.asarray(a144read)
outside=np.ones((2048,2048),bool);outside[y0:y1,x0:x1]=False
blast=int(np.count_nonzero(np.any(old_np!=fin_np,axis=2)&outside))
blast_a144=int(np.count_nonzero(np.any(a144_np!=fin_np,axis=2)&outside))
alpha=int(np.count_nonzero((old_np[:,:,3]!=fin_np[:,:,3])&outside))
if blast or blast_a144 or alpha:raise RuntimeError(("blast",blast,blast_a144,alpha))

fraw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM);pb=cb[:128]+fraw.tobytes("raw",meta["mode"]);cand.write_bytes(pb);after=sha(pb)
praw,persisted,pmeta=decode(pb)
if pmeta!=meta or pb[:128]!=cb[:128] or ImageChops.difference(persisted,final).getbbox() is not None:raise RuntimeError("persisted mismatch")

# Evidence
src_rgb,old_rgb,clean_rgb,new_rgb=map(comp,(source,old,clean,persisted))
crop=(x0-80,y0-70,x1+80,y1+70);parts=[]
for lab,im in [("SOURCE",src_rgb),("A165 REJECT",old_rgb),("A165R POLY CLEAN",clean_rgb),("A165R FINAL",new_rgb)]:
    c=im.crop(crop).resize(((crop[2]-crop[0])*2,(crop[3]-crop[1])*2),Image.Resampling.LANCZOS)
    z=Image.new("RGB",(c.width,c.height+30),(18,18,18));z.paste(c,(0,30));ImageDraw.Draw(z).text((5,5),lab,fill="white");parts.append(z)
sheet=Image.new("RGB",(sum(x.width for x in parts),max(x.height for x in parts)),(15,15,15));xx=0
for z in parts:sheet.paste(z,(xx,0));xx+=z.width
sheet.save(out/"A165R_Q028_SOURCE_A165_CLEAN_FINAL.jpg","JPEG",quality=97,subsampling=0)
pcs=[]
for sc in (1,.75,.5):
    s=src_rgb.crop(crop);f=new_rgb.crop(crop);sz=(round(s.width*sc),round(s.height*sc));s=s.resize(sz,Image.Resampling.LANCZOS);f=f.resize(sz,Image.Resampling.LANCZOS)
    rr=Image.new("RGB",(s.width*2+6,s.height+28),(15,15,15));rr.paste(s,(0,28));rr.paste(f,(s.width+6,28));ImageDraw.Draw(rr).text((5,5),f"SOURCE | A165R {int(sc*100)}%",fill="white");pcs.append(rr)
pw=max(x.width for x in pcs);ph=sum(x.height+4 for x in pcs);ps=Image.new("RGB",(pw,ph),(15,15,15));yy=0
for z in pcs:ps.paste(z,(0,yy));yy+=z.height+4
ps.save(out/"A165R_Q028_PRACTICAL.jpg","JPEG",quality=95,subsampling=0)
rawpair=Image.new("RGB",(2048,1054),(15,15,15))
for i,(lab,im) in enumerate([("SOURCE RAW",sraw),("A165R RAW",praw)]):
    z=comp(im).resize((1024,1024),Image.Resampling.LANCZOS);card=Image.new("RGB",(1024,1054),(18,18,18));card.paste(z,(0,30));ImageDraw.Draw(card).text((5,5),lab,fill="white");rawpair.paste(card,(i*1024,0))
rawpair.save(out/"A165R_Q028_RAW.jpg","JPEG",quality=94,subsampling=0)
report={
 "schema_version":2,"role":"A","run":run,"queue_index":28,"asset":asset,"work_stolen_from_lane":"B",
 "trigger":"A165_CONTROLLER_CLEAN_PLATE_RECTANGLE_REJECT_AFTER_C245_UNDERSIZE_REWORK",
 "source_sha256":SOURCE_SHA,"a144_candidate_sha256":A144_SHA,"a165_rejected_candidate_sha256":BEFORE_SHA,"candidate_sha256":after,
 "clean_plate":{"method":"local cubic polynomial fit from 32px intact canonical-source ring; exact source bbox only","edge_mean_abs_rgb_delta":round(edge_mean,4),"edge_p95_abs_rgb_delta":round(edge_p95,4)},
 "row":{"original_bbox":BOX,"localized_bbox":lb,"source_size":[x1-x0,y1-y0],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"margins":margins,
        "width_ratio":round((lb[2]-lb[0])/(x1-x0),4),"font_file":FONT.name,"font_index":1,"font_size":80,"stroke":3,"readable_right_slant":.30},
 "machine_qa":{"bbox_size_positive_margin":"PASS","changed_pixels_outside_box_vs_a165":blast,"changed_pixels_outside_box_vs_a144":blast_a144,
               "alpha_changes_outside_box":alpha,"header_128_exact":pb[:128]==cb[:128],"mip_count":1,"raw_orientation":"mirror_y","persisted_decode":"PASS"},
 "ordered_generation_gate":{"1_plate_restoration":"PENDING_CONTROLLER_VISUAL_POLYNOMIAL_CLEAN","2_slant_direction":"PASS_RIGHT_0.30","3_no_undersizing":"PASS_NEAR_90_PERCENT_SOURCE_WIDTH",
  "4_weight_outline_shadow":"PASS_WHITE_NAVY_SOURCE_FAMILY","5_no_clipping":"PASS_POSITIVE_MARGIN","6_protected_clearance":"PASS_ZERO_OUTSIDE_BOX",
  "7_flip_y_raw":"EVIDENCE_WRITTEN","8_immediate_readability":"PENDING_CONTROLLER_VISUAL"},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","fresh_independent_c":"REQUIRED","mandatory_c3_strict_audit":"REQUIRED_EXACT_SHA",
 "pre_ingame_export":"BLOCKED_UNTIL_FRESH_C_C3","runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
(out/"A165R_Q028_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A165R_Q028_A05BF610.json").write_text(json.dumps({"role":"A","run":run,"queue_index":28,"asset":"A05BF610","work_stolen_from_lane":"B","candidate_sha256":after,
 "status":"STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL","report":str((out/"A165R_Q028_REPORT.json").relative_to(repo)),"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"before":BEFORE_SHA,"after":after,"bbox":lb,"margins":margins,"edge_mean":edge_mean,"edge_p95":edge_p95},ensure_ascii=False,indent=2))
