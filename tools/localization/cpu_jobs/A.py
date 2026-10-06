#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261006-A-PRODUCTION115-D1039D6F"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset; cand.parent.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds"
SOURCE_SHA="d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0"
p=Path("/tmp/A115_D103.dds"); urllib.request.urlretrieve(url,p)
raw=p.read_bytes()
if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA: raise RuntimeError("source drift")
H=struct.unpack_from("<I",raw,12)[0]; W=struct.unpack_from("<I",raw,16)[0]; MIPS=struct.unpack_from("<I",raw,28)[0]
MASKS=struct.unpack_from("<IIII",raw,92)
if (W,H,MIPS,MASKS)!=(2048,2048,1,(0xff,0xff00,0xff0000,0xff000000)): raise RuntimeError(("structure",W,H,MIPS,MASKS))
src_raw=Image.frombytes("RGBA",(W,H),raw[128:],"raw","RGBA"); src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); alpha=sa[:,:,3]>8

# A113 exact component mapping: these two tight ROIs are the visible START/GOAL route-map badges.
specs=[
 {"key":"start","source":"START","ko":"출발","roi":[788,495,910,545],"manual_poly":[(811,509),(887,509),(881,532),(803,532)]},
 {"key":"goal","source":"GOAL","ko":"골","roi":[1325,755,1445,810],"manual_poly":[(1349,771),(1426,771),(1420,795),(1341,795)]},
]
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
rows=[]; source_masks=[]; clean_masks=[]
for sp in specs:
    rx0,ry0,rx1,ry1=sp["roi"]; sub=sa[ry0:ry1,rx0:rx1,:]
    r=sub[:,:,0].astype(np.int16); g=sub[:,:,1].astype(np.int16); b=sub[:,:,2].astype(np.int16); a=sub[:,:,3]>8
    red=a&(r>155)&(r>g+65)&(r>b+45)&(g<110)
    lab,n=ndimage.label(red); comps=[]
    for i in range(1,n+1):
        c=lab==i; area=int(c.sum())
        if area<20: continue
        yy,xx=np.nonzero(c); comps.append((area,c,[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]))
    if not comps: raise RuntimeError(("no sign red",sp["key"]))
    comps.sort(key=lambda z:z[0],reverse=True)
    # union meaningful sign red islands, then envelope across every row to bridge English glyph holes.
    seed=np.zeros_like(red)
    for area,c,cb in comps:
        if area>=20: seed|=c
    rb={}
    for yy in range(seed.shape[0]):
        xs=np.nonzero(seed[yy])[0]
        if len(xs)>=2: rb[yy]=(int(xs.min()),int(xs.max()))
    known=sorted(rb)
    if len(known)<2: raise RuntimeError(("sign rows",sp["key"],known))
    banner=np.zeros_like(seed)
    for yy in range(known[0],known[-1]+1):
        if yy in rb: lx,hx=rb[yy]
        else:
            lo=max(k for k in known if k<yy); hi=min(k for k in known if k>yy); t=(yy-lo)/(hi-lo)
            lx=round(rb[lo][0]*(1-t)+rb[hi][0]*t); hx=round(rb[lo][1]*(1-t)+rb[hi][1]*t)
        banner[yy,lx:hx+1]=True
    banner&=a
    sign_red=(r>140)&(r>g+65)&(r>b+35)&(g<90)&(b<145)
    interior=ndimage.binary_erosion(banner,iterations=1,border_value=0)
    bright=interior&(r>150)&(g>90)&(b>55)
    near=ndimage.binary_dilation(bright,iterations=4)
    effect=interior&~sign_red&near
    effect=ndimage.binary_dilation(effect,iterations=1)&interior
    if int(effect.sum())<80: raise RuntimeError(("effect too small",sp["key"],int(effect.sum())))
    gm=np.zeros((H,W),bool); gm[ry0:ry1,rx0:rx1]=effect
    sb=bbox(gm)
    # Controller-reviewed complete sign interior from A113 visual mapping and same B188 route-badge geometry.
    pim=Image.new("L",(W,H),0); ImageDraw.Draw(pim).polygon(sp["manual_poly"],fill=255); cm=np.asarray(pim)>0
    miss=gm&~cm
    if np.any(miss): raise RuntimeError(("manual clean interior misses source effect",sp["key"],bbox(miss),int(miss.sum())))
    source_masks.append(gm); clean_masks.append(cm)
    rows.append({**sp,"source_bbox":sb,"source_text_pixels":int(gm.sum()),"clean_region_bbox":bbox(cm),"clean_region_pixels":int(cm.sum()),"component_meta":[[x[0],x[2]] for x in comps]})

source_mask=np.zeros((H,W),bool); clean_region=np.zeros((H,W),bool)
for m in source_masks: source_mask|=m
for m in clean_masks: clean_region|=m
if np.any(source_masks[0]&source_masks[1]): raise RuntimeError("source masks overlap")

# Complete red-body reconstruction from local source row donors; artwork outside the two polygons is byte/pixel protected.
clean_arr=sa.copy(); rr=sa[:,:,0].astype(np.int16); gg=sa[:,:,1].astype(np.int16); bb=sa[:,:,2].astype(np.int16)
for row,cm,sm in zip(rows,clean_masks,source_masks):
    donor=cm&~sm&(rr>130)&(rr>gg+45)&(rr>bb+20)&(gg<120)&(bb<160)
    ys=np.unique(np.nonzero(cm)[0]); samples={}
    for yy in ys:
        q=sa[yy,donor[yy]]
        if len(q)>=2: samples[int(yy)]=np.median(q,axis=0).astype(np.float64)
    if not samples: raise RuntimeError(("no red donors",row["key"]))
    known=sorted(samples)
    for yy in ys:
        yy=int(yy); col=samples[yy] if yy in samples else samples[min(known,key=lambda z:abs(z-yy))]
        xs=np.nonzero(cm[yy])[0]; clean_arr[yy,xs]=np.clip(np.rint(col),0,255).astype(np.uint8)
clean=Image.fromarray(clean_arr,"RGBA")
same_clean=np.all(clean_arr==sa,axis=2)
clean_residue=int(np.count_nonzero(source_mask&same_clean))
if clean_residue: raise RuntimeError(("clean source residue",clean_residue))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))
def shear(im,k):
    add=max(1,int(round(k*im.height)))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,(1,-k,add,0,1,0),resample=Image.Resampling.BICUBIC)
def colors(sm):
    pix=sa[sm][:,:3]; fillpix=pix[(pix[:,1]>165)&(pix[:,2]>95)]; shadowpix=pix[(pix[:,0]>170)&(pix[:,1]>65)&(pix[:,1]<180)&(pix[:,2]<170)]
    fill=tuple(int(x) for x in (np.median(fillpix,axis=0) if len(fillpix) else np.array([250,235,175])))+(255,)
    shadow=tuple(int(x) for x in (np.median(shadowpix,axis=0) if len(shadowpix) else np.array([238,135,72])))+(255,)
    return fill,shadow

final=clean.copy(); target=np.zeros((H,W),bool)
for row,sm,cm in zip(rows,source_masks,clean_masks):
    x0,y0,x1,y1=row["source_bbox"]; sw=x1-x0; sh=y1-y0; fill,shadow=colors(sm)
    chosen=None
    for fs in range(max(18,int(sh*1.05)),14,-1):
        font=ImageFont.truetype(FONT,fs); can=Image.new("RGBA",(max(360,sw*4),max(180,sh*4)),(0,0,0,0)); d=ImageDraw.Draw(can)
        tb=d.textbbox((0,0),row["ko"],font=font); ox=18-tb[0]; oy=18-tb[1]; off=max(1,round(fs*.055))
        d.text((ox+off,oy+off),row["ko"],font=font,fill=shadow); d.text((ox,oy),row["ko"],font=font,fill=fill,stroke_width=1,stroke_fill=shadow)
        gb=can.getchannel("A").getbbox()
        if not gb: continue
        glyph=shear(can.crop(gb),.17); gb=glyph.getchannel("A").getbbox()
        if gb: glyph=glyph.crop(gb)
        if glyph.width>sw-4 or glyph.height>sh-4: continue
        px=x0+(sw-glyph.width)//2; py=y0+(sh-glyph.height)//2
        lm=np.zeros((H,W),bool); ma=np.asarray(glyph.getchannel("A"))>0; lm[py:py+glyph.height,px:px+glyph.width]=ma
        lb=bbox(lm)
        if lb and lb[0]>=x0+2 and lb[1]>=y0+2 and lb[2]<=x1-2 and lb[3]<=y1-2 and not np.any(lm&~cm):
            chosen=(glyph,px,py,lm,lb,fs,off,fill,shadow); break
    if chosen is None: raise RuntimeError(("no render fit",row["key"],row["source_bbox"]))
    glyph,px,py,lm,lb,fs,off,fill,shadow=chosen
    if np.any(target&lm): raise RuntimeError("localized overlap")
    final.alpha_composite(glyph,(px,py)); target|=lm
    row.update({"localized_bbox":lb,"source_width":sw,"source_height":sh,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","font":"Noto Sans CJK KR Black","font_size":fs,"shear":.17,"shadow_offset":off,"fill_rgba":fill,"shadow_rgba":shadow})

fa=np.asarray(final,dtype=np.uint8); changed=np.any(sa!=fa,axis=2)
outside=int(np.count_nonzero(changed&~clean_region)); alpha_out=int(np.count_nonzero((sa[:,:,3]!=fa[:,:,3])&~clean_region))
if outside or alpha_out: raise RuntimeError(("outside protected",outside,alpha_out))
guard=ndimage.binary_dilation(target,iterations=2); same=np.all(fa==sa,axis=2); final_residue=int(np.count_nonzero(source_mask&same&~guard))
if final_residue: raise RuntimeError(("final source residue",final_residue))
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=raw[:128]+raw_final.tobytes("raw","RGBA"); cand.write_bytes(payload)
dec_raw=Image.frombytes("RGBA",(W,H),payload[128:],"raw","RGBA"); dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")

src.save(out/"A115_SOURCE_READABLE.png"); clean.save(out/"A115_CLEAN_PLATE.png"); dec.save(out/"A115_FINAL_READABLE.png"); src_raw.save(out/"A115_SOURCE_RAW.png"); dec_raw.save(out/"A115_FINAL_RAW.png")
Image.fromarray((source_mask*255).astype(np.uint8),"L").save(out/"A115_SOURCE_TEXT_MASK.png"); Image.fromarray((clean_region*255).astype(np.uint8),"L").save(out/"A115_CLEAN_REGION_MASK.png"); Image.fromarray((target*255).astype(np.uint8),"L").save(out/"A115_RENDER_MASK.png")
cards=[]
for row in rows:
    bx0,by0,bx1,by1=row["clean_region_bbox"]; pad=12; box=(bx0-pad,by0-pad,bx1+pad,by1+pad)
    ims=[comp(z.crop(box)).resize(((box[2]-box[0])*4,(box[3]-box[1])*4),Image.Resampling.NEAREST) for z in (src,clean,dec)]
    card=Image.new("RGB",(sum(i.width for i in ims)+16,max(i.height for i in ims)+34),"white"); xx=0; ImageDraw.Draw(card).text((5,5),f'{row["source"]}->{row["ko"]} SOURCE | CLEAN | FINAL',fill="black")
    for im in ims: card.paste(im,(xx,34)); xx+=im.width+8
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+6 for c in cards)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+6
sheet.save(out/"A115_D103_BADGE_CONTACTS.jpg",quality=97,optimize=True)
rrimg=Image.new("RGB",(1000,1040),"white")
for i,(labn,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",src_raw),("FINAL_RAW_MIRROR_Y",dec_raw))):
    z=comp(z0); z.thumbnail((1000,480),Image.Resampling.LANCZOS); rrimg.paste(z,(0,i*515+25)); ImageDraw.Draw(rrimg).text((5,i*515+5),labn,fill="black")
rrimg.save(out/"A115_D103_RAW_COMPARE.jpg",quality=93,optimize=True)

report={"schema_version":1,"role":"A","run":run,"queue_index":217,"asset":asset,"source_sha256":SOURCE_SHA,"candidate_sha256":hashlib.sha256(payload).hexdigest(),"classification":{"segments":[{"source":"START","korean":"출발"},{"source":"GOAL","korean":"골"}],"physical_elements":2},"mapping_provenance":"A113 readable/component map fixed exact D103 route-card sign ROIs; manual complete red-body interiors follow controller-reviewed B188/A85 route-badge family geometry but all reconstruction/colors are sampled from D103 source itself.","structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":MIPS,"header_128_exact":payload[:128]==raw[:128],"raw_orientation":"mirror_y"},"rows":rows,"zero_pixel_gates":{"clean_source_residue":clean_residue,"final_source_residue":final_residue,"changed_outside_clean_regions":outside,"alpha_outside_clean_regions":alpha_out,"localized_overlap":0},"candidate_path":str(cand.relative_to(repo)),"worker_static_qa":"PASS","controller_visual_qa":"PENDING","status":"A115_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_touched":False}
(out/"A115_D1039D6F_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A115_D1039D6F.json").write_text(json.dumps({"run":run,"index":217,"candidate_sha256":report["candidate_sha256"],"bbox_size_positive_margin":"2/2 PASS","outside":outside,"alpha_outside":alpha_out,"status":report["status"],"report":f"localization/graphics/role_A/{run}/A115_D1039D6F_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False),flush=True)
