#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont
from scipy import ndimage
from scipy.spatial import ConvexHull

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261008-A189-Q217-SOURCE-GOLD-ITALIC"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest()!="68bd22192de5e4a5133869790a042c410970858006d1afcf613f2b2f7140ab39":
    raise RuntimeError("q217 candidate changed after C288; no overwrite")
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","217","--require-safe-rerender"],
                      capture_output=True,text=True)
print("A189 TRIAGE "+triage.stdout,flush=True)
if triage.returncode: raise RuntimeError(("q217 unsafe rerender",triage.returncode,triage.stderr))
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds"
SOURCE_SHA="d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0"
srcp=Path("/tmp/A189_D103.dds"); urllib.request.urlretrieve(url,srcp)
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

# C288 remediation: reconstruct source cream/gold beveled italic display, preserving
# clean plate and both exact banner polygons from proven A189 reconstruction.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-nanum","fonts-noto-cjk"],check=True)
spec=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{family}|%{style}",
                               "NanumSquareRound:style=Bold"],text=True).strip()
FONT,FONT_INDEX,FONT_FAMILY,FONT_STYLE=spec.rsplit("|",3)
if not Path(FONT).exists() or "NanumSquareRound" not in FONT_FAMILY:
    raise RuntimeError(("q217 font fallback, refusing unverified square source family",spec))
FONT_INDEX=int(FONT_INDEX or 0)

def shift_mask(src_mask,dx,dy):
    z=Image.new("L",src_mask.size,0); z.paste(src_mask,(dx,dy));return z
def rgb_layer(color,mask,opacity=255):
    rr=Image.new("RGBA",mask.size,color[:3]+(0,))
    rr.putalpha(mask.point(lambda v:(v*opacity)//255))
    return rr
def source_colors(sm):
    pix=sa[sm][:,:3]
    fillpix=pix[(pix[:,1]>165)&(pix[:,2]>95)]
    shadowpix=pix[(pix[:,0]>170)&(pix[:,1]>65)&(pix[:,1]<180)&(pix[:,2]<170)]
    base=tuple(int(v) for v in (np.median(fillpix,axis=0) if len(fillpix) else [247,234,194]))
    depth=tuple(int(v) for v in (np.median(shadowpix,axis=0) if len(shadowpix) else [230,133,91]))
    return base,depth
def native_bevel(text,fontsize,tracking,base,depth,lean=.28):
    ss=4
    font=ImageFont.truetype(FONT,fontsize*ss,index=FONT_INDEX)
    letters=list(text)
    advances=[font.getlength(c) for c in letters]
    ww=int(sum(advances)+ss*tracking*(len(letters)-1))
    ascent,descent=font.getmetrics()
    m=Image.new("L",(ww+48*ss,ascent+descent+48*ss),0)
    draw=ImageDraw.Draw(m); xp=20*ss
    for c,adv in zip(letters,advances):
        draw.text((int(xp),20*ss),c,font=font,fill=255)
        xp+=adv+ss*tracking
    bb=m.getbbox()
    if bb is None:return None
    m=m.crop(bb)
    # Top shifted right with regard to baseline; source display leans right.
    shw=int(np.ceil(lean*m.height)); z=Image.new("L",(m.width+shw+4*ss,m.height),0)
    for y in range(m.height):
        off=int(round(lean*(m.height-1-y)))
        z.paste(m.crop((0,y,m.width,y+1)),(off,y))
    z=z.crop(z.getbbox())
    z=z.resize((max(1,round(z.width/ss)),max(1,round(z.height/ss))),Image.Resampling.LANCZOS)
    bb=z.getbbox()
    if bb is None:return None
    z=z.crop(bb)
    pad=5;core=Image.new("L",(z.width+pad*2,z.height+pad*2),0)
    core.paste(z,(pad,pad))
    stroke=core.filter(ImageFilter.MaxFilter(3))
    layer=Image.new("RGBA",core.size,(0,0,0,0))
    # Warm orange/red backing is source-badge metal glow, not dark flat offset.
    layer.alpha_composite(rgb_layer(depth,shift_mask(stroke,1,2),180))
    layer.alpha_composite(rgb_layer((223,118,75),stroke,210))
    arr=np.zeros((core.height,core.width,4),np.uint8)
    # White cream upper facet; warm yellow mid band; orange lower lip.
    b=np.array(base,dtype=np.float32)
    stops=[(0.0,np.array([255,250,229])),(.22,np.maximum(b,[249,236,194])),
           (.53,np.maximum(b*.97,[245,221,170])),
           (.76,np.array([255,244,206])),(1.,np.array([249,201,139]))]
    for yy in range(core.height):
        v=(yy-pad)/max(1,z.height-1)
        if v<=0: cc=stops[0][1]
        elif v>=1: cc=stops[-1][1]
        else:
            for j in range(1,len(stops)):
                if v<=stops[j][0]:
                    a,va=stops[j-1];n,vb=stops[j]; t=(v-a)/(n-a)
                    cc=va+(vb-va)*t;break
        arr[yy,:,:3]=np.clip(cc,0,255).astype(np.uint8)
        arr[yy,:,3]=255
    face=Image.fromarray(arr,"RGBA");face.putalpha(core)
    layer.alpha_composite(face)
    # Narrow bright bevel along top-left source-direction contour.
    upper=ImageChops.subtract(core,shift_mask(core,0,1))
    layer.alpha_composite(rgb_layer((255,252,234),upper,220))
    # Lower red-orange inset, not a plain uniform black edge.
    lower=ImageChops.subtract(core,shift_mask(core,0,-1))
    layer.alpha_composite(rgb_layer((228,142,91),lower,110))
    bb=layer.getbbox()
    return layer.crop(bb) if bb else None

final=clean.copy(); target=np.zeros((H,W),bool)
for row,sm in zip(rows,source_masks):
    x0,y0,x1,y1=row["source_bbox"]; sw=x1-x0; sh=y1-y0
    base,depth=source_colors(sm); chosen=None
    # Fit original SOURCE HEIGHT first, not a fixed percent of English width.
    for fs in range(max(22,round(sh*1.25)),16,-1):
        for tr in (4,3,2):
            glyph=native_bevel(row["ko"],fs,tr,base,depth)
            if glyph is None or glyph.width>sw-2 or glyph.height>sh-2:continue
            px=x0+(sw-glyph.width)//2;py=y0+(sh-glyph.height)//2
            layer=Image.new("RGBA",(W,H),(0,0,0,0))
            layer.alpha_composite(glyph,(px,py))
            lm=np.asarray(layer.getchannel("A"))>0
            lb=bbox(lm)
            if lb and lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1:
                chosen=(layer,lm,lb,fs,tr,base,depth);break
        if chosen:break
    if chosen is None: raise RuntimeError(("could not fit source-height cream-gold italic",row["key"],row["source_bbox"]))
    layer,lm,lb,fs,tracking,base,depth=chosen
    if np.any(target&lm):raise RuntimeError("localized overlap")
    final.alpha_composite(layer);target|=lm
    row.update({"korean":row["ko"],"font":"NanumSquareRound Bold","font_family":FONT_FAMILY,
                "font_size":fs,"tracking_px":tracking,"readable_shear":.28,
                "bevel":"three-tone source-cream-gold face/white upper lip/orange lower inset",
                "extrusion":"warm source-orange offset 1x2px","horizontal_scaling":1.0,
                "source_base_rgb":base,"source_depth_rgb":depth,
                "localized_bbox":lb,"source_width":sw,"source_height":sh,
                "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
                "delta_left":lb[0]-x0,"delta_right":x1-lb[2],
                "delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
                "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

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

src.save(out/"A189_SOURCE_READABLE.png"); clean.save(out/"A189_CLEAN_PLATE.png"); dec.save(out/"A189_FINAL_READABLE.png"); src_raw.save(out/"A189_SOURCE_RAW.png"); dec_raw.save(out/"A189_FINAL_RAW.png")
Image.fromarray((source_mask*255).astype(np.uint8),"L").save(out/"A189_SOURCE_TEXT_MASK.png"); Image.fromarray((clean_region*255).astype(np.uint8),"L").save(out/"A189_CLEAN_REGION_MASK.png"); Image.fromarray((target*255).astype(np.uint8),"L").save(out/"A189_TARGET_MASK.png")
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
sheet.save(out/"A189_D103_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=97,optimize=True)
rawsheet=Image.new("RGB",(1000,1040),"white")
for i,(labn,im) in enumerate((("SOURCE_RAW_MIRROR_Y",src_raw),("FINAL_RAW_MIRROR_Y",dec_raw))):
    v=onwhite(im); v.thumbnail((1000,480),Image.Resampling.LANCZOS); rawsheet.paste(v,(0,i*515+25)); ImageDraw.Draw(rawsheet).text((5,i*515+5),labn,fill="black")
rawsheet.save(out/"A189_D103_RAW_COMPARE.jpg",quality=93,optimize=True)

# Exact current SHA guard keeps worker from issuing a coincidentally unchanged DDS.
if hashlib.sha256(payload).hexdigest()=="68bd22192de5e4a5133869790a042c410970858006d1afcf613f2b2f7140ab39":
    raise RuntimeError("No material production change relative to A116")
# Source-vs-persisted native and scaled comparisons (source text always English).
def panel(im,box,scale,label):
    im=im.crop(box)
    im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
    gray=Image.new("RGBA",im.size,(110,110,110,255))
    gray.alpha_composite(im)
    vis=gray.convert("RGB")
    tile=Image.new("RGB",(vis.width,vis.height+22),(60,60,60))
    tile.paste(vis,(0,22))
    ImageDraw.Draw(tile).text((3,4),label,fill=(255,255,255))
    return tile
panels=[]
for row in rows:
    ob=row["banner_bbox"]; pad=9
    box=(ob[0]-pad,ob[1]-pad,ob[2]+pad,ob[3]+pad)
    for scale in (4,1,.75,.5):
        srcv=panel(src,box,scale,f"{row['key']} SOURCE ENGLISH {scale}")
        finv=panel(dec,box,scale,f"{row['key']} FINAL KOREAN {scale}")
        line=Image.new("RGB",(srcv.width+finv.width+6,max(srcv.height,finv.height)),(65,65,65))
        line.paste(srcv,(0,0));line.paste(finv,(srcv.width+6,0));panels.append(line)
contact=Image.new("RGB",(max(x.width for x in panels),sum(x.height+5 for x in panels)),(65,65,65))
y=0
for p in panels: contact.paste(p,(0,y));y+=p.height+5
contact.save(out/"A189_SOURCE_EN_KO_4X_100_75_50.jpg",quality=96,subsampling=0)
report={"schema_version":1,"role":"A","run":run,"queue_index":217,"asset":asset,"source_sha256":SOURCE_SHA,"candidate_sha256":hashlib.sha256(payload).hexdigest(),"classification":{"from":"zoom_review","to":"localize_text","segments":[{"source":"START","korean":"출발"},{"source":"GOAL","korean":"골"}],"physical_elements":2},"mapping_provenance":"A113 exact readable/component mapping fixed the two D103 route-map sign ROIs. A189 uses the B190/B191 convex-red-hull clean reconstruction method independently on D103 source pixels.","same_family_reference":"C288 user-returned native English START/GOAL cream-gold italic badge family","structure":{"dimensions":[W,H],"format":"RGBA32","mipmaps":MIPS,"header_128_exact":payload[:128]==raw[:128],"raw_orientation":"mirror_y"},"rows":rows,"static_qa":{"bbox_size_positive_margin":"2/2 PASS","clean_source_residue":residue_clean,"clean_non_red":clean_not_red,"changed_outside":outside,"alpha_outside":alpha_out,"final_source_residue_exact":residue_exact,"final_source_residue_color":residue_color,"localized_overlap":0,"dds_roundtrip":"PASS","status":"PASS"},"candidate_path":str(candidate.relative_to(repo)),"controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","status":"A189_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED","vr_ffb_dx11_dxvk_touched":False}
(out/"A189_D1039D6F_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A189_D1039D6F.json").write_text(json.dumps({"run":run,"index":217,"candidate_sha256":report["candidate_sha256"],"bbox_size_positive_margin":"2/2 PASS","outside":outside,"alpha_outside":alpha_out,"residue":residue_color,"status":report["status"],"report":f"localization/graphics/role_A/{run}/A189_D1039D6F_REPORT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False),flush=True)
