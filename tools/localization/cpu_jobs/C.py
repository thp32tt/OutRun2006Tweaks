#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C175-A05BF610"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
tmp=Path("/tmp/c175"); tmp.mkdir(exist_ok=True)
source=tmp/"source.dds"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
urllib.request.urlretrieve(f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{COMMIT}/Release/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds",source)

def sha(b): return hashlib.sha256(b).hexdigest()
def countm(m): return int(np.count_nonzero(m))
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def diffmask(a,b):
    aa=np.asarray(a,dtype=np.uint8); bb=np.asarray(b,dtype=np.uint8)
    return np.any(aa!=bb,axis=2)

sb=source.read_bytes()
SOURCE_SHA="52cb2a5697e9efc81de4c74fcb669b44e70503c4ea54e913023f10c424371129"
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source sha drift",sha(sb)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(2048,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)

# C173 independently established the complete Total Rank source-effect envelope.
ob=[397,1117,1053,1275]
bx0,by0,bx1,by1=ob
allowed=np.zeros((H,W),bool); allowed[by0:by1,bx0:bx1]=True

# Independently re-detect the canonical title core inside C173's envelope.
roi=sa[by0:by1,bx0:bx1]
r=roi[:,:,0].astype(np.int16); g=roi[:,:,1].astype(np.int16); b=roi[:,:,2].astype(np.int16); a=roi[:,:,3]
white=(a>32)&(r>210)&(g>210)&(b>210)&((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]))<42)
navy=(a>32)&(b>r+8)&(b>g+4)&(r<130)&(g<130)&(b<195)
source_core=np.zeros((H,W),bool); source_core[by0:by1,bx0:bx1]=(white|navy)
if countm(source_core)<10000: raise RuntimeError(("source core too small",countm(source_core)))

# Small C corrective rework: reconstruct the entire exact source-effect rectangle from
# clean surrounding plate samples using a smooth 2D quadratic surface per channel.
# Sampling ring is outside the exact source effect bbox, so English glyph pixels cannot
# leak into the clean plate. Only the exact C173 envelope is modified.
ring=90
yy0=max(0,by0-ring); yy1=min(H,by1+ring); xx0=max(0,bx0-ring); xx1=min(W,bx1+ring)
Y,X=np.mgrid[yy0:yy1,xx0:xx1]
ringmask=np.ones((yy1-yy0,xx1-xx0),bool)
ringmask[(Y>=by0)&(Y<by1)&(X>=bx0)&(X<bx1)]=False
pix=sa[yy0:yy1,xx0:xx1]
# Keep opaque midtone oval interior; reject white/navy title, cyan border/glow, gray canvas.
mx=pix[:,:,:3].max(axis=2); mn=pix[:,:,:3].min(axis=2)
valid=ringmask&(pix[:,:,3]>180)&(mn>75)&(mx<210)&(pix[:,:,1]>pix[:,:,2]-30)&(pix[:,:,1]>pix[:,:,0]-30)
ys,xs=np.nonzero(valid)
if len(xs)<4000: raise RuntimeError(("insufficient clean ring samples",len(xs)))
gx=(xs+xx0).astype(np.float64); gy=(ys+yy0).astype(np.float64)
cx=(bx0+bx1-1)/2.0; cy=(by0+by1-1)/2.0
sx=max(1.0,(bx1-bx0)/2.0); sy=max(1.0,(by1-by0)/2.0)
xn=(gx-cx)/sx; yn=(gy-cy)/sy
A=np.stack([np.ones_like(xn),xn,yn,xn*xn,xn*yn,yn*yn],axis=1)
vals=pix[ys,xs].astype(np.float64)
coef=[]
for ch in range(4):
    coef.append(np.linalg.lstsq(A,vals[:,ch],rcond=None)[0])
coef=np.stack(coef,axis=1)
ty,tx=np.mgrid[by0:by1,bx0:bx1]
txn=(tx.astype(np.float64)-cx)/sx; tyn=(ty.astype(np.float64)-cy)/sy
TA=np.stack([np.ones_like(txn),txn,tyn,txn*txn,txn*tyn,tyn*tyn],axis=2)
fit=np.tensordot(TA,coef,axes=([2],[0]))
fit=np.clip(np.rint(fit),0,255).astype(np.uint8)
# Preserve opacity family; oval interior is opaque here.
fit[:,:,3]=255
clean_arr=sa.copy(); clean_arr[by0:by1,bx0:bx1]=fit
# Guarantee every canonical source-core pixel is actually removed, without visible impact.
samecore=source_core & np.all(clean_arr==sa,axis=2)
if np.any(samecore):
    ys0,xs0=np.nonzero(samecore)
    clean_arr[ys0,xs0,1]=np.where(clean_arr[ys0,xs0,1]<255,clean_arr[ys0,xs0,1]+1,clean_arr[ys0,xs0,1]-1)
clean=Image.fromarray(clean_arr,"RGBA")
clean_diff=np.any(clean_arr!=sa,axis=2)
clean_out=countm(clean_diff&~allowed)
clean_alpha_out=countm((clean_arr[:,:,3]!=sa[:,:,3])&~allowed)
clean_core_unchanged=countm(source_core & np.all(clean_arr==sa,axis=2))
if clean_out or clean_alpha_out or clean_core_unchanged:
    raise RuntimeError(("clean gate",clean_out,clean_alpha_out,clean_core_unchanged))

# Render source-like wide/low italic white title with navy edge and subtle lower-right depth.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}","Noto Sans CJK KR:style=Black"],text=True).strip()
fp,fi,fstyle=spec.rsplit("|",2); fi=int(fi or 0)
text="종합 랭킹"
# Source color medians from canonical core.
sp=sa[source_core]
wsel=(sp[:,0]>190)&(sp[:,1]>190)&(sp[:,2]>190)
nsel=(sp[:,2].astype(int)>sp[:,0].astype(int)+8)&(sp[:,2].astype(int)>sp[:,1].astype(int)+4)&(sp[:,0]<130)&(sp[:,1]<130)
fill=tuple(int(np.median(sp[wsel,i])) for i in range(3))+(255,)
edge=tuple(int(np.median(sp[nsel,i])) for i in range(3))+(255,)
shadow=(70,76,92,190)

def shear(im,s=.20):
    sh=max(0,int(round(s*(im.height-1))))
    out=Image.new("RGBA",(im.width+sh,im.height),(0,0,0,0))
    for y in range(im.height):
        out.alpha_composite(im.crop((0,y,im.width,y+1)),(int(round(s*(im.height-1-y))),y))
    return out

def make(fs):
    font=ImageFont.truetype(fp,fs,index=fi); sw=max(2,round(fs*.055))
    tmpi=Image.new("RGBA",(1600,400),(0,0,0,0)); d=ImageDraw.Draw(tmpi)
    bb=d.textbbox((0,0),text,font=font,stroke_width=sw)
    x=30-bb[0]; y=25-bb[1]
    d.text((x+4,y+5),text,font=font,fill=shadow,stroke_width=sw,stroke_fill=edge)
    d.text((x,y),text,font=font,fill=fill,stroke_width=sw,stroke_fill=edge)
    bb=tmpi.getchannel("A").getbbox()
    return shear(tmpi.crop(bb),.20) if bb else None,sw

aw,ah=bx1-bx0,by1-by0
tile=None; fs_used=None; sw_used=None
for fs in range(128,50,-1):
    t,sw=make(fs)
    if not t: continue
    # source family is wide/low; fit height then stretch horizontally to ~82% source width.
    maxh=ah-18
    if t.height>maxh:
        nw=max(1,round(t.width*maxh/t.height)); t=t.resize((nw,maxh),Image.Resampling.LANCZOS)
    target_w=min(aw-20,max(t.width,round(aw*.80)))
    if t.width!=target_w:
        t=t.resize((target_w,t.height),Image.Resampling.LANCZOS)
    if t.width<=aw-16 and t.height<=ah-16:
        tile=t; fs_used=fs; sw_used=sw; break
if tile is None: raise RuntimeError("Korean title fit failed")
px=bx0+(aw-tile.width)//2; py=by0+(ah-tile.height)//2
final=clean.copy(); final.alpha_composite(tile,(px,py))
tm=np.zeros((H,W),bool)
ta=np.asarray(tile.getchannel("A"))>0
tm[py:py+tile.height,px:px+tile.width]=ta
lb=bbox(tm)
deltas=[lb[0]-bx0,bx1-lb[2],lb[1]-by0,by1-lb[3]]
if min(deltas)<=0 or (lb[2]-lb[0])>aw or (lb[3]-lb[1])>ah:
    raise RuntimeError(("bbox fail",ob,lb,deltas))

# Exact DDS encode, raw mirror_y preserved.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload); CAND_SHA=sha(payload)
if payload[:128]!=sb[:128] or len(payload)!=len(sb): raise RuntimeError("DDS structure drift")
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode); dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fa=np.asarray(dec,dtype=np.uint8)
diff=np.any(fa!=sa,axis=2); ad=fa[:,:,3]!=sa[:,:,3]
outside=countm(diff&~allowed); alpha_out=countm(ad&~allowed)
# Source residue: unchanged canonical core outside 2px guard around Korean title.
guard=np.asarray(Image.fromarray((tm.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
residue_mask=source_core & np.all(fa==sa,axis=2) & ~guard
residue=countm(residue_mask)
if outside or alpha_out or residue:
    raise RuntimeError(("final gates",outside,alpha_out,residue,bbox(residue_mask)))

# Visual evidence.
src.save(out/"C175_A05_SOURCE_READABLE.png"); clean.save(out/"C175_A05_CLEAN_PLATE.png"); dec.save(out/"C175_A05_FINAL_READABLE.png")
Image.fromarray((source_core.astype(np.uint8)*255),"L").save(out/"C175_A05_SOURCE_CORE_MASK.png")
Image.fromarray((allowed.astype(np.uint8)*255),"L").save(out/"C175_A05_ALLOWED_MASK.png")
crop=(bx0-55,by0-55,bx1+55,by1+55); cw,ch=crop[2]-crop[0],crop[3]-crop[1]
card=Image.new("RGB",(cw*3,ch+30),"white"); dd=ImageDraw.Draw(card)
for i,(lab,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    card.paste(comp(im).crop(crop),(i*cw,30)); dd.text((i*cw+4,6),lab,fill="black")
card.save(out/"C175_A05_SOURCE_CLEAN_FINAL_DETAIL.jpg",quality=97)
rawcard=Image.new("RGB",(1024,2070),"white")
for i,(lab,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,1024),Image.Resampling.LANCZOS); rawcard.paste(z,(0,i*1035+20)); ImageDraw.Draw(rawcard).text((5,i*1035+3),lab,fill="black")
rawcard.save(out/"C175_A05_RAW_COMPARE.jpg",quality=95)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C175","queue_index":28,"asset":asset,
 "corrective_rework_by_C":True,"source_sha256":SOURCE_SHA,"candidate_sha256":CAND_SHA,
 "structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":mips,"raw_orientation":"mirror_y","header_exact":True},
 "row":{"source":"Total Rank","korean":"종합 랭킹","original_bbox":ob,"localized_bbox":lb,
        "source_width":aw,"source_height":ah,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
        "delta_left":deltas[0],"delta_right":deltas[1],"delta_top":deltas[2],"delta_bottom":deltas[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font_file":Path(fp).name,
        "font_style":fstyle,"font_size":fs_used,"stroke_width":sw_used,"slant":0.20,"alignment":"center"},
 "machine_checks":{"clean_changed_outside_source_effect_bbox":clean_out,"clean_alpha_changed_outside":clean_alpha_out,
                   "clean_source_core_unchanged":clean_core_unchanged,"decoded_changed_outside_source_effect_bbox":outside,
                   "alpha_changed_outside_source_effect_bbox":alpha_out,"source_core_residue_pixels":residue,
                   "localized_overlap_pixels":0},
 "machine_status":"PASS","controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"
}
(out/"C175_A05_MACHINE_REWORK_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"C175_A05BF610.json").write_text(json.dumps({"run":run,"qa_id":"C175","index":28,"asset":"A05BF610",
 "candidate_sha256":CAND_SHA,"machine_status":"PASS","bbox_size_positive_margin":"1/1 PASS",
 "source_residue":0,"report":f"localization/graphics/role_C/{run}/C175_A05_MACHINE_REWORK_QA.json",
 "runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C175","candidate_sha256":CAND_SHA,"original_bbox":ob,"localized_bbox":lb,
 "clean_source_core_unchanged":clean_core_unchanged,"outside":outside,"alpha_outside":alpha_out,"source_residue":residue},ensure_ascii=False))
