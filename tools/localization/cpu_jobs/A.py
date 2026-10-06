#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont
from scipy import ndimage
from scipy.spatial import ConvexHull

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261006-A-PRODUCTION116-D1039D6F"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds"
SOURCE_SHA="d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0"
srcp=Path("/tmp/A116_D103.dds"); urllib.request.urlretrieve(url,srcp)
raw=srcp.read_bytes()
if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA: raise RuntimeError("source drift")
H=struct.unpack_from("<I",raw,12)[0]; W=struct.unpack_from("<I",raw,16)[0]; MIPS=struct.unpack_from("<I",raw,28)[0]; MASKS=struct.unpack_from("<IIII",raw,92)
if (W,H,MIPS,MASKS)!=(2048,2048,1,(0xff,0xff00,0xff0000,0xff000000)): raise RuntimeError(("structure",W,H,MIPS,MASKS))
src_raw=Image.frombytes("RGBA",(W,H),raw[128:],"raw","RGBA"); src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); alpha=sa[:,:,3]>8

# A113 controller mapping: exact visible START/GOAL route-map sign ROIs in D103.
specs=[
 {"key":"start","source":"START","ko":"출발","roi":[788,495,910,545]},
 {"key":"goal","source":"GOAL","ko":"골","roi":[1325,755,1445,810]},
]
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

rows=[]; source_masks=[]; banner_masks=[]
for sp in specs:
    x0,y0,x1,y1=sp["roi"]; sub=sa[y0:y1,x0:x1,:]
    r=sub[:,:,0].astype(np.int16); g=sub[:,:,1].astype(np.int16); b=sub[:,:,2].astype(np.int16); a=sub[:,:,3]>8
    red=a&(r>155)&(r>g+65)&(r>b+45)&(g<100)
    lab,n=ndimage.label(red); comps=[]
    for i in range(1,n+1):
        c=lab==i; area=int(c.sum())
        if area<20: continue
        yy,xx=np.nonzero(c); comps.append((area,c,[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]))
    if not comps: raise RuntimeError(("no red banner",sp["key"]))
    # ROI is sign-tight; union all meaningful red islands and interpolate English-covered scanlines.
    seed=np.zeros_like(red)
    for area,c,cb in comps: seed|=c
    rb={}
    for yy in range(seed.shape[0]):
        xs=np.nonzero(seed[yy])[0]
        if len(xs)>=2: rb[yy]=(int(xs.min()),int(xs.max()))
    known=sorted(rb)
    if len(known)<2: raise RuntimeError(("insufficient sign rows",sp["key"]))
    banner=np.zeros_like(seed)
    for yy in range(known[0],known[-1]+1):
        if yy in rb: lx,rx=rb[yy]
        else:
            lo=max(k for k in known if k<yy); hi=min(k for k in known if k>yy); t=(yy-lo)/(hi-lo)
            lx=round(rb[lo][0]*(1-t)+rb[hi][0]*t); rx=round(rb[lo][1]*(1-t)+rb[hi][1]*t)
        banner[yy,lx:rx+1]=True
    banner&=a
    sign_red=(r>140)&(r>g+65)&(r>b+35)&(g<72)&(b<120)
    interior=ndimage.binary_erosion(banner,iterations=1,border_value=0)
    bright=interior&(r>150)&(g>90)&(b>55); near=ndimage.binary_dilation(bright,iterations=4)
    effect=interior&~sign_red&near; effect=ndimage.binary_dilation(effect,iterations=1)&interior
    elab,en=ndimage.label(effect); kept=np.zeros_like(effect); meta=[]
    for i in range(1,en+1):
        c=elab==i; area=int(c.sum())
        if area<3: continue
        yy,xx=np.nonzero(c); cb=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]; meta.append([area,cb]); kept|=c
    effect=kept
    if int(effect.sum())<80: raise RuntimeError(("effect too small",sp["key"],int(effect.sum()),meta))
    gm=np.zeros((H,W),bool); gm[y0:y1,x0:x1]=effect
    bm=np.zeros((H,W),bool); bm[y0:y1,x0:x1]=banner
    sb=bbox(gm); bb=bbox(bm)
    if not sb or not bb: raise RuntimeError(("empty",sp["key"]))
    if sb[0]<=bb[0] or sb[1]<=bb[1] or sb[2]>=bb[2] or sb[3]>=bb[3]: raise RuntimeError(("text touches sign edge",sp["key"],sb,bb))
    source_masks.append(gm); banner_masks.append(bm)
    rows.append({**sp,"source_bbox":sb,"banner_bbox":bb,"source_text_pixels":int(gm.sum()),"banner_pixels":int(bm.sum()),"component_meta":meta})

source_mask=np.zeros((H,W),bool)
for m in source_masks: source_mask|=m
if np.any(source_masks[0]&source_masks[1]): raise RuntimeError("source masks overlap")

# Same family as B190/B191: convex hull of strong source-red pixels, eroded one px, then union exact source-effect mask.
clean_masks=[]; clean_region=np.zeros((H,W),bool)
for row,sm,bm in zip(rows,source_masks,banner_masks):
    x0,y0,x1,y1=row["banner_bbox"]; sub=sa[y0:y1,x0:x1,:]
    r=sub[:,:,0].astype(np.int16); g=sub[:,:,1].astype(np.int16); b=sub[:,:,2].astype(np.int16); aa=sub[:,:,3]>8
    redseed=aa&(r>150)&(r>g+65)&(r>b+40)&(g<105)&(b<135)
    yy,xx=np.nonzero(redseed)
    if len(xx)<30: raise RuntimeError(("red hull seed too small",row["key"],len(xx)))
    pts=np.column_stack([xx,yy]); hull=ConvexHull(pts)
    poly=[(int(x0+pts[i,0]),int(y0+pts[i,1])) for i in hull.vertices]
    pim=Image.new("L",(W,H),0); ImageDraw.Draw(pim).polygon(poly,fill=255)
    cm=ndimage.binary_erosion(np.asarray(pim)>0,iterations=1,border_value=0); cm|=sm
    clean_masks.append(cm); clean_region|=cm
    row["clean_region_bbox"]=bbox(cm); row["clean_region_pixels"]=int(cm.sum()); row["red_hull_vertices"]=poly

clean_arr=sa.copy(); rr0=sa[:,:,0].astype(np.int16); gg0=sa[:,:,1].astype(np.int16); bb0=sa[:,:,2].astype(np.int16)
for row,cm,bm,sm in zip(rows,clean_masks,banner_masks,source_masks):
    donor=bm&~sm&(rr0>140)&(rr0>gg0+60)&(rr0>bb0+35)&(gg0<100)&(bb0<135)
    ys=np.unique(np.nonzero(cm)[0]); samples={}
    for y in ys:
        q=sa[y,donor[y]]
        if len(q)>=2: samples[int(y)]=np.median(q,axis=0).astype(np.float64)
    if not samples: raise RuntimeError(("no red donors",row["key"]))
    known=sorted(samples)
    for y in ys:
        y=int(y); col=samples[y] if y in samples else samples[min(known,key=lambda z:abs(z-y))]
        xs=np.nonzero(cm[y])[0]; clean_arr[y,xs]=np.clip(np.rint(col),0,255).astype(np.uint8)
clean=Image.fromarray(clean_arr,"RGBA")
rr=clean_arr[:,:,0].astype(np.int16); gg=clean_arr[:,:,1].astype(np.int16); bb=clean_arr[:,:,2].astype(np.int16)
clean_red=(rr>105)&(rr>gg+25)&(rr>bb+15)&(gg<145)&(bb<160)
residue_clean=int(np.count_nonzero(source_mask&~clean_red)); clean_not_red=int(np.count_nonzero(clean_region&~clean_red))
if residue_clean or clean_not_red: raise RuntimeError(("clean residue",residue_clean,clean_not_red))

subprocess.run(["sudo","apt-get","update","-qq"],check=True); subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font",FONT))
def shear(im,k):
    add=max(1,int(round(k*im.height)))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,(1,-k,add,0,1,0),resample=Image.Resampling.BICUBIC)
def sample_colors(sm):
    pix=sa[sm][:,:3]; fillpix=pix[(pix[:,1]>165)&(pix[:,2]>95)]; shadowpix=pix[(pix[:,0]>170)&(pix[:,1]>65)&(pix[:,1]<180)&(pix[:,2]<170)]
    fill=tuple(int(x) for x in (np.median(fillpix,axis=0) if len(fillpix) else np.array([250,235,175])))+(255,)
    shadow=tuple(int(x) for x in (np.median(shadowpix,axis=0) if len(shadowpix) else np.array([238,135,72])))+(255,)
    return fill,shadow

final=clean.copy(); target=np.zeros((H,W),bool)
for row,sm in zip(rows,source_masks):
    x0,y0,x1,y1=row["source_bbox"]; sw=x1-x0; sh=y1-y0; fill,shadow=sample_colors(sm); chosen=None
    for fs in range(max(18,int(sh*1.05)),14,-1):
        font=ImageFont.truetype(FONT,fs); canvas=Image.new("RGBA",(max(360,sw*4),max(180,sh*4)),(0,0,0,0)); d=ImageDraw.Draw(canvas)
        tb=d.textbbox((0,0),row["ko"],font=font); ox=18-tb[0]; oy=18-tb[1]; off=max(1,round(fs*.055))
        d.text((ox+off,oy+off),row["ko"],font=font,fill=shadow); d.text((ox,oy),row["ko"],font=font,fill=fill,stroke_width=1,stroke_fill=shadow)
        gb=canvas.getchannel("A").getbbox()
        if not gb: continue
        glyph=shear(canvas.crop(gb),.17); gb=glyph.getchannel("A").getbbox()
        if gb: glyph=glyph.crop(gb)
        if glyph.width>sw-4 or glyph.height>sh-4: continue
        px=x0+(sw-glyph.width)//2; py=y0+(sh-glyph.height)//2
        layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(glyph,(px,py)); lm=np.asarray(layer.getchannel("A"))>0; lb=bbox(lm)
        if lb and lb[0]>=x0+2 and lb[1]>=y0+2 and lb[2]<=x1-2 and lb[3]<=y1-2:
            chosen=(layer,lm,lb,fs,fill,shadow,off); break
    if chosen is None: raise RuntimeError(("no fit",row["key"],row["source_bbox"]))
    layer,lm,lb,fs,fill,shadow,off=chosen
    if np.any(target&lm): raise RuntimeError("localized overlap")
    final.alpha_composite(layer); target|=lm
    row.update({"korean":row["ko"],"font":"Noto Sans CJK KR Black","font_size":fs,"shear":.17,"shadow_offset":off,"fill_rgba":fill,"shadow_rgba":shadow,"localized_bbox":lb,"source_width":sw,"source_height":sh,"localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

fa=np.asarray(final,dtype=np.uint8); allowed=clean_region|target; changed=np.any(sa!=fa,axis=2)
outside=int(np.count_nonzero(changed&~allowed)); alpha_out=int(np.count_nonzero((sa[:,:,3]!=fa[:,:,3])&~allowed))
if outside or alpha_out: raise RuntimeError(("outside",outside,alpha_out))
guard=ndimage.binary_dilation(target,iterations=2); same=np.all(fa==sa,axis=2)
residue_exact=int(np.count_nonzero(source_mask&same&~guard))
rrf=fa[:,:,0].astype(np.int16); ggf=fa[:,:,1].astype(np.int16); bbf=fa[:,:,2].astype(np.int16)
final_red=(rrf>115)&(rrf>ggf+35)&(rrf>bbf+20)&(ggf<125)&(bbf<135)
residue_color=int(np.count_nonzero(source_mask&~guard&~final_red))
if residue_color: raise RuntimeError(("final residue",residue_exact,residue_color))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=raw[:128]+raw_final.tobytes("raw","RGBA"); candidate.write_bytes(payload)
dec_raw=Image.frombytes("RGBA",(W,H),payload[128:],"raw","RGBA"); dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")

src.save(out/"A116_SOURCE_READABLE.png"); clean.save(out/"A116_CLEAN_PLATE.png"); dec.save(out/"A116_FINAL_READABLE.png"); src_raw.save(out/"A116_SOURCE_RAW.png"); dec_raw.save(out/"A116_FINAL_RAW.png")
Image.fromarray((source_mask*255).astype(np.uint8),"L").save(out/"A116_SOURCE_TEXT_MASK.png"); Image.fromarray((clean_region*255).astype(np.uint8),"L").save(out/"A116_CLEAN_REGION_MASK.png"); Image.fromarray((target*255).astype(np.uint8),"L").save(out/"A116_TARGET_MASK.png")
def onwhite(im):
    z=Image.new("RGBA",im.size,(255,255,255,255)); z.alpha_composite(im); return z.convert("RGB")
cards=[]
for row in rows:
    x0,y0,x1,y1=row["banner_bbox"]; pad=12; box=(x0-pad,y0-pad,x1+pad,y1+pad)
    for labn,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
        v=onwhite(im).crop(box).resize(((box[2]-box[0])*4,(box[3]-box[1])*4),Image.Resampling.NEAREST)
        c=Image.new("RGB",(v.width,v.height+28),"white"); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),f'{row["key"].upper()} {labn}',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+5 for c in cards)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+5
sheet.save(out/"A116_D103_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=97,optimize=True)
rawsheet=Image.new("RGB",(1000,1040),"white")
for i,(labn,im) in enumerate((("SOURCE_RAW_MIRROR_Y",src_raw),("FINAL_RAW_MIRROR_Y",dec_raw))):
    v=onwhite(im); v.thumbnail((1000,480),Image.Resampling.LANCZOS); rawsheet.paste(v,(0,i*515+25)); ImageDraw.Draw(rawsheet).text((5,i*515+5),labn,fill="black")
rawsheet.save(out/"A116_D103_RAW_COMPARE.jpg",quality=93,optimize=True)

report={"schema_version":1,"role":"A","run":run,"queue_index":217,"asset":asset,"source_sha256":SOURCE_SHA,"candidate_sha256":hashlib.sha256(payload).hexdigest(),"classification":{"from":"zoom_review","to":"localize_text","segments":[{"source":"START","korean":"출발"},{"source":"GOAL","korean":"골"}],"physical_elements":2},"mapping_provenance":"A113 exact readable/component mapping fixed the two D103 route-map sign ROIs. A116 uses the B190/B191 convex-red-hull clean reconstruction method independently on D103 source pixels.","same_family_reference":"A85/B190-B191 route START/GOAL badge family","structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":MIPS,"header_128_exact":payload[:128]==raw[:128],"raw_orientation":"mirror_y"},"rows":rows,"static_qa":{"bbox_size_positive_margin":"2/2 PASS","clean_source_residue":residue_clean,"clean_non_red":clean_not_red,"changed_outside":outside,"alpha_outside":alpha_out,"final_source_residue_exact":residue_exact,"final_source_residue_color":residue_color,"localized_overlap":0,"dds_roundtrip":"PASS","status":"PASS"},"candidate_path":str(candidate.relative_to(repo)),"controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","status":"A116_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_touched":False}
(out/"A116_D1039D6F_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A116_D1039D6F.json").write_text(json.dumps({"run":run,"index":217,"candidate_sha256":report["candidate_sha256"],"bbox_size_positive_margin":"2/2 PASS","outside":outside,"alpha_outside":alpha_out,"residue":residue_color,"status":report["status"],"report":f"localization/graphics/role_A/{run}/A116_D1039D6F_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False),flush=True)
