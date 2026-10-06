#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageOps
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261006-A-PRODUCTION114-D1039D6F"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst"
tmp=Path("/tmp/a114"); tmp.mkdir(exist_ok=True)
SOURCE_SHA="d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0"
REF_SHA="d5f4a36d5ef1285555ca8fc045e54d160876d1b3e33c6fbc45668c24566c2cf8"

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))

def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def bbox_np(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def decode(path,expected):
    raw=path.read_bytes()
    if sha(raw)!=expected: raise RuntimeError(("source drift",path.name,sha(raw),expected))
    H,W,pitch,depth,mips=struct.unpack_from("<5I",raw,12); pf=struct.unpack_from("<8I",raw,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or len(raw)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(raw)))
    rim=Image.frombytes("RGBA",(W,H),raw[128:],"raw",mode)
    return raw,W,H,mips,mode,rim,rim.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def comp(im):
    z=Image.new("RGBA",im.size,(255,255,255,255)); z.alpha_composite(im); return z.convert("RGB")
def shear(im,amount):
    add=max(1,int(round(amount*im.height)))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,(1,-amount,add,0,1,0),resample=Image.Resampling.BICUBIC)

dp=tmp/"D103.dds"; rp=tmp/"6C9B.dds"
urllib.request.urlretrieve(base+"/D1039D6F_512x512.dds",dp)
urllib.request.urlretrieve(base+"/6C9B3611_256x256.dds",rp)
raw,W,H,mips,mode,raw_src,src=decode(dp,SOURCE_SHA)
rraw,RW,RH,rmips,rmode,rraw_src,rsrc=decode(rp,REF_SHA)
if (W,H,mips,mode)!=(2048,2048,1,"RGBA") or (RW,RH,rmips,rmode)!=(1024,1024,1,"RGBA"):
    raise RuntimeError("structure mismatch")

# A113 proved these are the two actual red route-map signs. Their geometry is an exact shifted copy
# of the 6C9B route-map family used by B188/A85: START shift (+748,+136), GOAL (+747,+135).
specs=[
 {"key":"start","source":"START","ko":"출발","ref_banner":[52,371,142,398],"banner":[800,507,890,534],"ref_source_bbox":[55,373,136,396],"source_bbox":[803,509,884,532],"ref_poly":[(63,373),(139,373),(133,396),(55,396)],"poly":[(811,509),(887,509),(881,532),(803,532)]},
 {"key":"goal","source":"GOAL","ko":"골","ref_banner":[591,634,681,661],"banner":[1338,769,1428,796],"ref_source_bbox":[595,635,672,659],"source_bbox":[1342,770,1419,794],"ref_poly":[(602,636),(678,636),(672,659),(594,659)],"poly":[(1349,771),(1425,771),(1419,794),(1341,794)]},
]
# Pixel-prove the family/shift before using reviewed geometry.
family_diffs={}
for sp in specs:
    rb=sp["ref_banner"]; db=sp["banner"]
    rc=np.asarray(rsrc.crop(tuple(rb))); dc=np.asarray(src.crop(tuple(db)))
    if rc.shape!=dc.shape: raise RuntimeError(("family crop shape",sp["key"],rc.shape,dc.shape))
    diff=int(np.count_nonzero(np.any(rc!=dc,axis=2)))
    family_diffs[sp["key"]]=diff
    if diff!=0: raise RuntimeError(("route badge family not pixel-exact",sp["key"],diff))

sa=np.asarray(src,dtype=np.uint8)
clean_arr=sa.copy()
clean_region=np.zeros((H,W),bool)
source_effect=np.zeros((H,W),bool)
rows=[]
for sp in specs:
    sx0,sy0,sx1,sy1=sp["source_bbox"]
    # Verify source bbox is nonempty and lies strictly inside the sign.
    bx0,by0,bx1,by1=sp["banner"]
    if not (bx0<sx0<sx1<bx1 and by0<sy0<sy1<by1): raise RuntimeError(("bbox geometry",sp))
    # Manual interior polygon is inherited from pixel-exact B188 same-family sign geometry.
    pim=Image.new("L",(W,H),0); ImageDraw.Draw(pim).polygon(sp["poly"],fill=255)
    cm=np.asarray(pim)>0
    # Source effect: non-sign-red bright/effect pixels inside the exact source bbox.
    rr=sa[:,:,0].astype(np.int16); gg=sa[:,:,1].astype(np.int16); bb=sa[:,:,2].astype(np.int16); aa=sa[:,:,3]>8
    boxmask=np.zeros((H,W),bool); boxmask[sy0:sy1,sx0:sx1]=True
    sign_red=(rr>140)&(rr>gg+65)&(rr>bb+35)&(gg<90)&(bb<140)&aa
    bright=boxmask&aa&(rr>150)&(gg>90)&(bb>55)
    near=ndimage.binary_dilation(bright,iterations=3)
    effect=boxmask&~sign_red&near
    effect=ndimage.binary_dilation(effect,iterations=1)&boxmask
    if int(effect.sum())<40: raise RuntimeError(("effect too small",sp["key"],int(effect.sum())))
    if np.any(effect&~cm): raise RuntimeError(("manual interior misses effect",sp["key"],bbox_np(effect&~cm)))
    source_effect|=effect
    # Rebuild complete red interior from source red row donors, white rim/map remain untouched.
    red_donor=cm&~effect&(rr>135)&(rr>gg+50)&(rr>bb+25)&(gg<105)&(bb<150)
    ys=np.unique(np.nonzero(cm)[0]); samples={}
    for yy in ys:
        q=sa[yy,red_donor[yy]]
        if len(q)>=2: samples[int(yy)]=np.median(q,axis=0).astype(np.float64)
    if not samples: raise RuntimeError(("no row donors",sp["key"]))
    known=sorted(samples)
    for yy in ys:
        yy=int(yy); col=samples[yy] if yy in samples else samples[min(known,key=lambda z:abs(z-yy))]
        xs=np.nonzero(cm[yy])[0]; clean_arr[yy,xs]=np.clip(np.rint(col),0,255).astype(np.uint8)
    clean_region|=cm
    rows.append({k:v for k,v in sp.items() if k not in ("ref_poly","poly")} | {"clean_polygon":sp["poly"],"source_effect_pixels":int(effect.sum()),"clean_region_pixels":int(cm.sum())})

clean=Image.fromarray(clean_arr,"RGBA")
same_clean=np.all(clean_arr==sa,axis=2)
residue_clean=int(np.count_nonzero(source_effect&same_clean))
if residue_clean: raise RuntimeError(("clean residue exact",residue_clean))
final=clean.copy(); target=np.zeros((H,W),bool)

def sample_colors(mask):
    pix=sa[mask][:,:3]
    fillpix=pix[(pix[:,1]>165)&(pix[:,2]>95)]
    shadowpix=pix[(pix[:,0]>170)&(pix[:,1]>65)&(pix[:,1]<180)&(pix[:,2]<170)]
    fill=tuple(int(x) for x in (np.median(fillpix,axis=0) if len(fillpix) else np.array([250,235,175])))+(255,)
    shadow=tuple(int(x) for x in (np.median(shadowpix,axis=0) if len(shadowpix) else np.array([238,135,72])))+(255,)
    return fill,shadow

for rec in rows:
    x0,y0,x1,y1=rec["source_bbox"]; sw=x1-x0; sh=y1-y0
    box=np.zeros((H,W),bool); box[y0:y1,x0:x1]=True
    fill,shadow=sample_colors(source_effect&box)
    chosen=None
    for fs in range(max(18,int(sh*1.05)),14,-1):
        font=ImageFont.truetype(FONT,fs)
        can=Image.new("RGBA",(max(360,sw*4),max(180,sh*4)),(0,0,0,0)); d=ImageDraw.Draw(can)
        tb=d.textbbox((0,0),rec["ko"],font=font); ox=18-tb[0]; oy=18-tb[1]; shoff=max(1,round(fs*.055))
        d.text((ox+shoff,oy+shoff),rec["ko"],font=font,fill=shadow)
        d.text((ox,oy),rec["ko"],font=font,fill=fill,stroke_width=1,stroke_fill=shadow)
        gb=can.getchannel("A").getbbox()
        if not gb: continue
        glyph=can.crop(gb); glyph=shear(glyph,.17); gb=glyph.getchannel("A").getbbox()
        if gb: glyph=glyph.crop(gb)
        if glyph.width<=sw-4 and glyph.height<=sh-4:
            px=x0+(sw-glyph.width)//2; py=y0+(sh-glyph.height)//2
            chosen=(glyph,px,py,fs,shoff,fill,shadow); break
    if chosen is None: raise RuntimeError(("no fit",rec["key"],rec["source_bbox"]))
    glyph,px,py,fs,shoff,fill,shadow=chosen
    final.alpha_composite(glyph,(px,py)); lm=np.zeros((H,W),bool); ma=np.asarray(glyph.getchannel("A"))>0; lm[py:py+glyph.height,px:px+glyph.width]=ma
    lb=bbox_np(lm); margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    if min(margins)<2: raise RuntimeError(("margin",rec["key"],lb,margins))
    if np.any(target&lm): raise RuntimeError("localized overlap")
    # Every localized pixel must also stay within the cleaned red body (positive art separation).
    if np.any(lm&~clean_region): raise RuntimeError(("target leaves clean body",rec["key"],bbox_np(lm&~clean_region)))
    target|=lm
    rec.update({"localized_bbox":lb,"delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],"source_width":sw,"source_height":sh,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font":"Noto Sans CJK KR Black","font_size":fs,"shear":.17,"shadow_offset":shoff,"fill_rgba":fill,"shadow_rgba":shadow})

allowed=clean_region|target
da=np.asarray(final,dtype=np.uint8)
changed=np.any(sa!=da,axis=2)
outside=int(np.count_nonzero(changed&~allowed))
alphaout=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
if outside or alphaout: raise RuntimeError(("outside",outside,alphaout))
guard=ndimage.binary_dilation(target,iterations=2)
same=np.all(da==sa,axis=2)
residue_final=int(np.count_nonzero(source_effect&same&~guard))
if residue_final: raise RuntimeError(("final source residue",residue_final))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=raw[:128]+raw_final.tobytes("raw",mode)
cand=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds"; cand.parent.mkdir(parents=True,exist_ok=True); cand.write_bytes(payload)
raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode); decim=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decim,final).getbbox(): raise RuntimeError("roundtrip")
# Persist masks and evidence.
src.save(out/"A114_SOURCE_READABLE.png"); clean.save(out/"A114_CLEAN_PLATE.png"); decim.save(out/"A114_FINAL_READABLE.png"); raw_src.save(out/"A114_SOURCE_RAW.png"); raw_dec.save(out/"A114_FINAL_RAW.png")
Image.fromarray((source_effect*255).astype(np.uint8),"L").save(out/"A114_SOURCE_EFFECT_MASK.png")
Image.fromarray((clean_region*255).astype(np.uint8),"L").save(out/"A114_CLEAN_REGION_MASK.png")
Image.fromarray((target*255).astype(np.uint8),"L").save(out/"A114_RENDER_MASK.png")
protected=ImageOps.invert(Image.fromarray((allowed*255).astype(np.uint8),"L")); protected.save(out/"A114_PROTECTED_MASK.png")
# High-zoom contacts.
cards=[]
for rec in rows:
    bx0,by0,bx1,by1=rec["banner"]; pad=12; box=(bx0-pad,by0-pad,bx1+pad,by1+pad)
    ims=[comp(z.crop(box)).resize(((box[2]-box[0])*4,(box[3]-box[1])*4),Image.Resampling.NEAREST) for z in (src,clean,decim)]
    row=Image.new("RGB",(sum(i.width for i in ims)+16,max(i.height for i in ims)+34),"white"); xx=0; ImageDraw.Draw(row).text((5,5),f'{rec["source"]}->{rec["ko"]} SOURCE | CLEAN | FINAL',fill="black")
    for im in ims: row.paste(im,(xx,34)); xx+=im.width+8
    cards.append(row)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+6 for c in cards)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+6
sheet.save(out/"A114_D103_BADGE_CONTACTS.jpg",quality=97,optimize=True)
rr=Image.new("RGB",(1000,1040),"white")
for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
    z=comp(z0); z.thumbnail((1000,480),Image.Resampling.LANCZOS); rr.paste(z,(0,i*515+25)); ImageDraw.Draw(rr).text((5,i*515+5),lab,fill="black")
rr.save(out/"A114_D103_RAW_COMPARE.jpg",quality=93,optimize=True)

report={"schema_version":1,"role":"A","run":run,"queue_index":217,"asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds","source_sha256":SOURCE_SHA,"candidate_sha256":sha(payload),"classification":{"segments":[{"source":"START","korean":"출발"},{"source":"GOAL","korean":"골"}],"physical_elements":2},"family_provenance":{"reference_asset":"6C9B3611","reference_source_sha256":REF_SHA,"pixel_exact_sign_crop_diff":family_diffs,"geometry":"B188 manually reviewed trapezoid interiors shifted into D103 route-map card after A113 exact component mapping"},"structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":mips,"header_128_exact":payload[:128]==raw[:128],"raw_orientation":"mirror_y"},"rows":rows,"zero_pixel_gates":{"clean_source_residue":residue_clean,"final_source_residue":residue_final,"changed_outside":outside,"alpha_outside":alphaout,"localized_overlap":0},"candidate_path":str(cand.relative_to(repo)),"worker_static_qa":"PASS","controller_visual_qa":"PENDING","status":"A114_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_touched":False}
(out/"A114_D1039D6F_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A114_D1039D6F.json").write_text(json.dumps({"run":run,"index":217,"candidate_sha256":report["candidate_sha256"],"bbox_size_positive_margin":"2/2 PASS","family_crop_diff":family_diffs,"outside":outside,"alpha_outside":alphaout,"status":report["status"],"report":f"localization/graphics/role_A/{run}/A114_D1039D6F_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False),flush=True)
