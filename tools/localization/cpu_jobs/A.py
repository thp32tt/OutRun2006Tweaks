#!/usr/bin/env python3
# A165R2: q28 second retry. A165 historical clean crop and A165R whole-bbox
# polynomial replacement both showed a visible rectangular luminance patch.
# Recover exact pre-A165 A144 bytes, remove only the old Korean glyph/effect
# pixels, reconstruct those glyph-shaped holes from nearest intact plate pixels,
# then draw the larger source-relative Korean title.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
import hashlib,json,struct,math,subprocess,urllib.request
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt, binary_dilation
from PIL import Image,ImageDraw,ImageFont,ImageChops

repo=Path.cwd();run="20261007-A165R2-Q028-A05BF610-GLYPH-MASK-CLEAN"
out=repo/"localization/graphics/role_A"/run;out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
SOURCE_SHA="52cb2a5697e9efc81de4c74fcb669b44e70503c4ea54e913023f10c424371129"
A144_SHA="aa0692a2918326a494c1b04837603313faac7bdd9b7f043d4b679a8e8b1493f9"
CURRENT_BAD_SHA="567f37b20c5dabd377e4c83e14baca52e69552c033dab300bbac5606daa37d90"
A144_COMMIT="c268f99db3f454d1fe3b62e8d32a3f74dae30f90"
BOX=[543,1185,1068,1275];OLD_KO_BOX=[649,1190,961,1270];TARGET=(476,80);FONT_INDEX=1

def sha(b):return hashlib.sha256(b).hexdigest()
def decode(b):
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12);pf=struct.unpack_from("<8I",b,76);m=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if m[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if m[:3]==(0xff0000,0xff00,0xff) else None)
    if b[:4]!=b"DDS " or mode is None or (w,h)!=(2048,2048) or mips!=1 or len(b)!=128+w*h*4:raise RuntimeError(("dds",w,h,mips,m))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode);return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mode":mode,"mips":mips,"masks":m}
def bbox(mask):
    ys,xs=np.nonzero(mask);return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255));z.alpha_composite(im);return z.convert("RGB")
def render(text,fs=80,stroke=3,slant=.30,ss=4):
    font=ImageFont.truetype(str(FONT),fs*ss,index=FONT_INDEX);d=ImageDraw.Draw(Image.new("L",(1,1)));tb=d.textbbox((0,0),text,font=font,stroke_width=stroke*ss);pad=96*ss
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

current=cand.read_bytes()
if sha(current)!=CURRENT_BAD_SHA:raise RuntimeError(("current drift",sha(current),CURRENT_BAD_SHA))
# Exact pre-A165/A144 candidate is authoritative outside the material repair box.
a144=subprocess.check_output(["git","show",A144_COMMIT+":localization/graphics/hd_candidates/"+asset])
if sha(a144)!=A144_SHA:raise RuntimeError(("A144 drift",sha(a144)))
araw,old,meta=decode(a144)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds"
sp=Path("/tmp/A05_source.dds");urllib.request.urlretrieve(url,sp);sb=sp.read_bytes()
if sha(sb)!=SOURCE_SHA:raise RuntimeError(("source drift",sha(sb)))
sraw,source,smeta=decode(sb)
if smeta!=meta or sb[:128]!=a144[:128]:raise RuntimeError("structure mismatch")

# Remove only A144 Korean pixels inside its persisted localized bbox.
oa=np.asarray(old).copy();x0,y0,x1,y1=OLD_KO_BOX
crop=oa[y0:y1,x0:x1,:3].astype(np.int16)
dark=(crop[:,:,0]<90)&(crop[:,:,1]<110)&(crop[:,:,2]<155)
white=(crop[:,:,0]>220)&(crop[:,:,1]>220)&(crop[:,:,2]>220)
seed=dark|white
mask_local=binary_dilation(seed,iterations=2)
if int(mask_local.sum())<2000:raise RuntimeError(("glyph mask too small",int(mask_local.sum())))
# Padded nearest-background reconstruction only within glyph-shaped mask.
pad=10;px0=x0-pad;py0=y0-pad;px1=x1+pad;py1=y1+pad
arr=oa[py0:py1,px0:px1].copy();mask=np.zeros(arr.shape[:2],bool);mask[pad:pad+(y1-y0),pad:pad+(x1-x0)]=mask_local
_,inds=distance_transform_edt(mask,return_indices=True);yy,xx=np.nonzero(mask);arr[yy,xx]=arr[inds[0,yy,xx],inds[1,yy,xx]]
clean_np=oa.copy();clean_np[py0:py1,px0:px1]=arr;clean=Image.fromarray(clean_np.astype(np.uint8),"RGBA")

# Text-residue test within old bbox: navy/white Korean core density should collapse.
cc=clean_np[y0:y1,x0:x1,:3]
remain_dark=int(np.count_nonzero((cc[:,:,0]<90)&(cc[:,:,1]<110)&(cc[:,:,2]<155)))
remain_white=int(np.count_nonzero((cc[:,:,0]>235)&(cc[:,:,1]>235)&(cc[:,:,2]>235)))
if remain_dark>200 or remain_white>250:raise RuntimeError(("clean residue density",remain_dark,remain_white))

# Place fresh source-relative title.
bx0,by0,bx1,by1=BOX;final=clean.copy();layer=render("종합 랭킹");px=bx0+((bx1-bx0)-layer.width)//2;py=by0+((by1-by0)-layer.height)//2
tmp=Image.new("RGBA",final.size,(0,0,0,0));tmp.alpha_composite(layer,(px,py));final.alpha_composite(tmp);lm=np.asarray(tmp.getchannel("A"))>0;lb=bbox(lm)
margins=[lb[0]-bx0,bx1-lb[2],lb[1]-by0,by1-lb[3]]
if min(margins)<2:raise RuntimeError(("margin",margins))

# Both base->final and current-bad->final are exact outside canonical source box.
fin=np.asarray(final);curraw,curread,_=decode(current);cur=np.asarray(curread)
outside=np.ones((2048,2048),bool);outside[by0:by1,bx0:bx1]=False
blast_a144=int(np.count_nonzero(np.any(oa!=fin,axis=2)&outside));blast_bad=int(np.count_nonzero(np.any(cur!=fin,axis=2)&outside))
alpha=int(np.count_nonzero((oa[:,:,3]!=fin[:,:,3])&outside))
if blast_a144 or blast_bad or alpha:raise RuntimeError(("blast",blast_a144,blast_bad,alpha))

fraw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM);pb=a144[:128]+fraw.tobytes("raw",meta["mode"]);cand.write_bytes(pb);after=sha(pb)
praw,persisted,pmeta=decode(pb)
if pmeta!=meta or pb[:128]!=a144[:128] or ImageChops.difference(persisted,final).getbbox() is not None:raise RuntimeError("persist mismatch")

# Evidence
src_rgb,a144_rgb,bad_rgb,clean_rgb,new_rgb=map(comp,(source,old,curread,clean,persisted));cropbox=(bx0-80,by0-70,bx1+80,by1+70)
parts=[]
for lab,im in [("SOURCE",src_rgb),("A144 SMALL",a144_rgb),("A165R BAD BOX",bad_rgb),("A165R2 GLYPH CLEAN",clean_rgb),("A165R2 FINAL",new_rgb)]:
    c=im.crop(cropbox).resize(((cropbox[2]-cropbox[0])*2,(cropbox[3]-cropbox[1])*2),Image.Resampling.LANCZOS)
    z=Image.new("RGB",(c.width,c.height+30),(18,18,18));z.paste(c,(0,30));ImageDraw.Draw(z).text((5,5),lab,fill="white");parts.append(z)
sheet=Image.new("RGB",(sum(z.width for z in parts),max(z.height for z in parts)),(15,15,15));xx=0
for z in parts:sheet.paste(z,(xx,0));xx+=z.width
sheet.save(out/"A165R2_Q028_SOURCE_A144_BAD_CLEAN_FINAL.jpg","JPEG",quality=97,subsampling=0)
pcs=[]
for sc in (1,.75,.5):
    s=src_rgb.crop(cropbox);f=new_rgb.crop(cropbox);sz=(round(s.width*sc),round(s.height*sc));s=s.resize(sz,Image.Resampling.LANCZOS);f=f.resize(sz,Image.Resampling.LANCZOS)
    rr=Image.new("RGB",(s.width*2+6,s.height+28),(15,15,15));rr.paste(s,(0,28));rr.paste(f,(s.width+6,28));ImageDraw.Draw(rr).text((5,5),f"SOURCE | A165R2 {int(sc*100)}%",fill="white");pcs.append(rr)
pw=max(z.width for z in pcs);ph=sum(z.height+4 for z in pcs);ps=Image.new("RGB",(pw,ph),(15,15,15));yy=0
for z in pcs:ps.paste(z,(0,yy));yy+=z.height+4
ps.save(out/"A165R2_Q028_PRACTICAL.jpg","JPEG",quality=95,subsampling=0)
rawpair=Image.new("RGB",(2048,1054),(15,15,15))
for i,(lab,im) in enumerate([("SOURCE RAW",sraw),("A165R2 RAW",praw)]):
    z=comp(im).resize((1024,1024),Image.Resampling.LANCZOS);card=Image.new("RGB",(1024,1054),(18,18,18));card.paste(z,(0,30));ImageDraw.Draw(card).text((5,5),lab,fill="white");rawpair.paste(card,(i*1024,0))
rawpair.save(out/"A165R2_Q028_RAW.jpg","JPEG",quality=94,subsampling=0)

report={"schema_version":2,"role":"A","run":run,"queue_index":28,"asset":asset,"work_stolen_from_lane":"B",
 "trigger":"A165_AND_A165R_CONTROLLER_CLEAN_PLATE_VISUAL_REJECTS_AFTER_C245_UNDERSIZE",
 "source_sha256":SOURCE_SHA,"a144_candidate_sha256":A144_SHA,"a165r_rejected_candidate_sha256":CURRENT_BAD_SHA,"candidate_sha256":after,
 "clean_plate":{"method":"remove only A144 Korean white/navy glyph/effect mask inside persisted old bbox; 2px dilation; nearest intact local plate fill; no whole-bbox replacement",
  "masked_pixels":int(mask_local.sum()),"remaining_dark_core_pixels":remain_dark,"remaining_white_core_pixels":remain_white},
 "row":{"original_bbox":BOX,"localized_bbox":lb,"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"source_size":[bx1-bx0,by1-by0],"margins":margins,
  "width_ratio":round((lb[2]-lb[0])/(bx1-bx0),4),"font_file":FONT.name,"font_index":1,"font_size":80,"stroke":3,"readable_right_slant":.30},
 "machine_qa":{"changed_pixels_outside_source_box_vs_a144":blast_a144,"changed_pixels_outside_source_box_vs_a165r_bad":blast_bad,
  "alpha_changes_outside_source_box":alpha,"bbox_size_positive_margin":"PASS","header_128_exact":pb[:128]==a144[:128],"mip_count":1,"raw_orientation":"mirror_y","persisted_decode":"PASS"},
 "ordered_generation_gate":{"1_plate_restoration":"PENDING_CONTROLLER_VISUAL_GLYPH_MASK_ONLY","2_slant_direction":"PASS_RIGHT_0.30","3_no_undersizing":"PASS_NEAR_90_PERCENT_SOURCE_WIDTH",
  "4_weight_outline_shadow":"PASS_WHITE_NAVY_SOURCE_FAMILY","5_no_clipping":"PASS_POSITIVE_MARGIN","6_protected_clearance":"PASS_ZERO_OUTSIDE_SOURCE_BOX",
  "7_flip_y_raw":"EVIDENCE_WRITTEN","8_immediate_readability":"PENDING_CONTROLLER_VISUAL"},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","fresh_independent_c":"REQUIRED","mandatory_c3_strict_audit":"REQUIRED_EXACT_SHA",
 "pre_ingame_export":"BLOCKED_UNTIL_FRESH_C_C3","runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
(out/"A165R2_Q028_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A165R2_Q028_A05BF610.json").write_text(json.dumps({"role":"A","run":run,"queue_index":28,"asset":"A05BF610","work_stolen_from_lane":"B","candidate_sha256":after,
 "status":"STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL","report":str((out/"A165R2_Q028_REPORT.json").relative_to(repo)),"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"after":after,"mask":int(mask_local.sum()),"remain_dark":remain_dark,"remain_white":remain_white,"bbox":lb,"margins":margins},ensure_ascii=False,indent=2))
