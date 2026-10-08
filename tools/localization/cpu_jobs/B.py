# B253 q214: native high-contrast BC3 badge glyph rework with decoded-face gate.
#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter
from scipy import ndimage
from scipy.spatial import ConvexHull

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261008-B253-Q214-BC3-COUNTER-SPACE"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3da79726739ac631d8e2703a65330dbb0c310770/Release/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
SOURCE_SHA="9a2e428bdb87399a7589338053b49efdcfd103d14f12a33a4bcde7705ab76c6b"
PRIOR_SHA="db3fefaadd3eac56c16f0f3d68a8b8824a4b05051b13240d8d382f061a53651d"
prior_bytes=candidate.read_bytes()
if hashlib.sha256(prior_bytes).hexdigest()!=PRIOR_SHA:
    raise RuntimeError("A183 q214 prior DDS SHA drift; stop rather than overwrite")
srcp=Path("/tmp/B253_BF229CF4.dds")
urllib.request.urlretrieve(url,srcp)

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def sha256_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

sb=srcp.read_bytes()
if sha256_bytes(sb)!=SOURCE_SHA:
    raise RuntimeError(("source drift",sha256_bytes(sb),SOURCE_SHA))
if sb[:4]!=b"DDS ":
    raise RuntimeError("not DDS")
H=struct.unpack_from("<I",sb,12)[0]
W=struct.unpack_from("<I",sb,16)[0]
MIPS=struct.unpack_from("<I",sb,28)[0]
FOURCC=sb[84:88]
need=128+((W+3)//4)*((H+3)//4)*16
if (W,H,MIPS,FOURCC,len(sb))!=(2048,2048,1,b"DXT5",need):
    raise RuntimeError(("unexpected structure",W,H,MIPS,FOURCC,len(sb),need))

src_raw=Image.open(srcp).convert("RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
alpha=sa[:,:,3]>8
rr=sa[:,:,0].astype(np.int16); gg=sa[:,:,1].astype(np.int16); bb=sa[:,:,2].astype(np.int16)

# The route-map card occupies the upper-right atlas quadrant in readable orientation.
# Find only large saturated-red plate components there. OutRun logos are blue/white and
# the other course-photo artwork is excluded by this color/size gate.
q=np.zeros((H,W),bool)
q[0:1024,512:2048]=True
red=q & alpha & (rr>145) & (rr>gg+48) & (rr>bb+28) & (gg<150) & (bb<165)
lab,n=ndimage.label(red)
cands=[]
for i in range(1,n+1):
    m=lab==i
    area=int(m.sum())
    if area<180:
        continue
    b=bbox(m)
    w=b[2]-b[0]; h=b[3]-b[1]
    if 45<=w<=300 and 12<=h<=90 and (w/max(h,1))>=1.55:
        cands.append({"area":area,"bbox":b,"mask":m})
print("B253_RED_CANDIDATES",[(z["area"],z["bbox"],round((z["bbox"][2]-z["bbox"][0])/max(1,z["bbox"][3]-z["bbox"][1]),2)) for z in cands],flush=True)
if len(cands)<2:
    raise RuntimeError(("fewer than two route-sign red components",[(c["area"],c["bbox"]) for c in cands]))
# START is the upper-left sign, GOAL the lower-right sign. Keep the pair maximizing
# that geometric relation and total area, so incidental red scene pixels cannot win.
pairs=[]
for a in cands:
    for b in cands:
        if a is b: continue
        ac=((a["bbox"][0]+a["bbox"][2])/2,(a["bbox"][1]+a["bbox"][3])/2)
        bc=((b["bbox"][0]+b["bbox"][2])/2,(b["bbox"][1]+b["bbox"][3])/2)
        if ac[0] < bc[0] and ac[1] < bc[1] and (bc[0]-ac[0])>250 and (bc[1]-ac[1])>80:
            pairs.append((a["area"]+b["area"],a,b))
if not pairs:
    raise RuntimeError(("cannot geometrically identify START/GOAL pair",[(c["area"],c["bbox"]) for c in cands]))
pairs.sort(key=lambda z:z[0],reverse=True)
_,start_comp,goal_comp=pairs[0]
print("B253_SELECTED",start_comp["area"],start_comp["bbox"],goal_comp["area"],goal_comp["bbox"],flush=True)

specs=[("start","START","출발",start_comp),("goal","GOAL","골",goal_comp)]
rows=[]
source_masks=[]
banner_masks=[]
safe_banner_masks=[]
safe_source_blocks=set()

for key,en,ko,comp in specs:
    cb=comp["bbox"]
    pad=12
    x0=max(0,cb[0]-pad); y0=max(0,cb[1]-pad); x1=min(W,cb[2]+pad); y1=min(H,cb[3]+pad)
    sub=sa[y0:y1,x0:x1,:]
    r=sub[:,:,0].astype(np.int16); g=sub[:,:,1].astype(np.int16); b=sub[:,:,2].astype(np.int16)
    a=sub[:,:,3]>8
    red2=a & (r>135) & (r>g+42) & (r>b+24) & (g<160) & (b<175)
    # Reconstruct the sign's red-body envelope scanline-by-scanline inside this
    # sign-tight ROI. B191 proved this avoids swallowing the bright white rim,
    # which a convex hull can include even when its seed pixels are all red.
    lab2,n2=ndimage.label(red2)
    raw_comps=[]
    for j in range(1,n2+1):
        cm=lab2==j; ar=int(cm.sum())
        if ar<15: continue
        yy,xx=np.nonzero(cm)
        cb2=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
        raw_comps.append((ar,cm,cb2))
    if not raw_comps:
        raise RuntimeError(("no red body components",key))
    raw_comps.sort(key=lambda z:z[0],reverse=True)
    main_bbox=raw_comps[0][2]
    seed=np.zeros_like(red2)
    pts=[]
    comp_meta=[]
    for ar,cm,cb2 in raw_comps:
        cx=(cb2[0]+cb2[2])/2; cy=(cb2[1]+cb2[3])/2
        # Keep the main sign plate and small red islands enclosed by that plate.
        # Reject nearby scene reds (the START traffic-light lamp was the visual-QA
        # false inclusion that produced a horizontal red bar into protected art).
        if not (main_bbox[0] <= cx <= main_bbox[2] and main_bbox[1] <= cy <= main_bbox[3]):
            continue
        yy,xx=np.nonzero(cm)
        comp_meta.append([ar,cb2])
        seed |= cm
        pts.extend((int(x),int(y)) for x,y in zip(xx,yy))
    if len(pts)<30:
        raise RuntimeError(("insufficient red body seed",key,len(pts),comp_meta,main_bbox))
    row_bounds={}
    for yy in range(seed.shape[0]):
        xx=np.nonzero(seed[yy])[0]
        if len(xx)>=2:
            row_bounds[int(yy)]=(int(xx.min()),int(xx.max()))
    known=sorted(row_bounds)
    if len(known)<2:
        raise RuntimeError(("insufficient red body rows",key,known,comp_meta))
    body=np.zeros_like(seed)
    for yy in range(known[0],known[-1]+1):
        if yy in row_bounds:
            lx,rx=row_bounds[yy]
        else:
            lo=max(z for z in known if z<yy); hi=min(z for z in known if z>yy)
            t=(yy-lo)/(hi-lo)
            lx=round(row_bounds[lo][0]*(1-t)+row_bounds[hi][0]*t)
            rx=round(row_bounds[lo][1]*(1-t)+row_bounds[hi][1]*t)
        body[yy,lx:rx+1]=True
    body &= a
    banner_full=np.zeros((H,W),bool)
    banner_full[y0:y1,x0:x1]=body
    banner=ndimage.binary_erosion(banner_full,iterations=1,border_value=0) & alpha

    # Keep the hull only as audit metadata; it no longer defines editable pixels.
    pts_arr=np.asarray(pts,dtype=np.int32)
    hull=ConvexHull(pts_arr)
    poly=[(x0+int(pts_arr[i,0]),y0+int(pts_arr[i,1])) for i in hull.vertices]

    # Source glyph/effect footprint: every pale/orange non-body pixel near the
    # lettering inside the reconstructed red interior. Use B191's stricter
    # sign-red family so orange English shadows cannot be mistaken for background.
    sign_red=(rr>140)&(rr>gg+60)&(rr>bb+35)&(gg<110)&(bb<140)&alpha
    bright=banner & (rr>145) & (gg>85) & (bb>45)
    near=ndimage.binary_dilation(bright,iterations=4)
    effect=banner & ~sign_red & near
    effect=ndimage.binary_dilation(effect,iterations=1) & banner
    # Restrict to a horizontal central band to avoid white rim leakage; source labels occupy sign center.
    eb=bbox(effect)
    if eb is None:
        raise RuntimeError(("empty effect",key))
    # Remove tiny disconnected noise and retain components in the main effect cluster.
    elab,en2=ndimage.label(effect)
    comps=[]
    for j in range(1,en2+1):
        cm=elab==j; ar=int(cm.sum())
        if ar<4: continue
        b0=bbox(cm); comps.append((ar,cm,b0))
    if not comps:
        raise RuntimeError(("no effect components",key))
    # Retain components whose centers lie inside the central 85% of the sign width/height.
    bbanner=bbox(banner)
    cx0=bbanner[0]+0.06*(bbanner[2]-bbanner[0]); cx1=bbanner[2]-0.06*(bbanner[2]-bbanner[0])
    cy0=bbanner[1]+0.05*(bbanner[3]-bbanner[1]); cy1=bbanner[3]-0.05*(bbanner[3]-bbanner[1])
    kept=np.zeros((H,W),bool)
    for ar,cm,b0 in comps:
        cx=(b0[0]+b0[2])/2; cy=(b0[1]+b0[3])/2
        if cx0<=cx<=cx1 and cy0<=cy<=cy1:
            kept |= cm
    effect=kept
    sbx=bbox(effect)
    if sbx is None or int(effect.sum())<80:
        raise RuntimeError(("effect too small",key,int(effect.sum()),bbanner,comp_meta))
    sw=sbx[2]-sbx[0]; sh=sbx[3]-sbx[1]
    bw0=bbanner[2]-bbanner[0]; bh0=bbanner[3]-bbanner[1]
    if sw>bw0*0.98 or sh>bh0*0.98:
        raise RuntimeError(("effect/banner separation unsafe",key,sbx,bbanner,sw/bw0,sh/bh0))

    # Every BC3 block touched by source effect must be fully inside the eroded red-body hull.
    blocks=set()
    ys,xs=np.nonzero(effect)
    for yy,xx in zip(ys,xs):
        blocks.add((xx//4,yy//4))
    safe_source_blocks |= blocks
    source_masks.append(effect); banner_masks.append(banner); safe_banner_masks.append(banner_full)
    rows.append({
      "key":key,"source":en,"korean":ko,"probe_roi":[x0,y0,x1,y1],
      "red_component_bbox":cb,"banner_bbox":bbanner,"source_bbox":sbx,
      "source_text_pixels":int(effect.sum()),"source_bc3_blocks":len(blocks),
      "red_component_meta":comp_meta,"red_hull_vertices":poly
    })

source_mask=np.zeros((H,W),bool)
for m in source_masks: source_mask |= m
if np.any(source_masks[0]&source_masks[1]):
    raise RuntimeError("source masks overlap")

# Build a clean plate by repainting entire safe source-effect BC3 blocks from local
# per-scanline red donors. This guarantees English/effect pixels are removed while
# keeping all changes inside full sign-body blocks.
clean_arr=sa.copy()
for row,sm,banner,safe_banner in zip(rows,source_masks,banner_masks,safe_banner_masks):
    donor=banner & ~sm & (rr>120) & (rr>gg+30) & (rr>bb+15) & (gg<180) & (bb<190)
    samples={}
    ys=np.unique(np.nonzero(banner)[0])
    for y in ys:
        pix=sa[y,donor[y]]
        if len(pix)>=3:
            samples[int(y)]=np.median(pix,axis=0).astype(np.float64)
    if not samples:
        raise RuntimeError(("no red donors",row["key"]))
    known=sorted(samples)
    for bx,by in {(x//4,y//4) for y,x in zip(*np.nonzero(sm))}:
        for y in range(by*4,by*4+4):
            col=samples[y] if y in samples else samples[min(known,key=lambda z:abs(z-y))]
            xs=np.arange(bx*4,bx*4+4)
            keep=safe_banner[y,bx*4:bx*4+4]
            if np.any(keep):
                clean_arr[y,xs[keep]]=np.clip(np.rint(col),0,255).astype(np.uint8)

    # A median red-body fill can coincidentally reproduce a small number of source
    # effect pixels byte-for-byte. That is not acceptable for the strict source-residue
    # gate. Replace only those stubborn source-effect pixels with the nearest genuine
    # donor pixel from this same sign body; protected/outside pixels remain untouched.
    same_row=np.all(clean_arr==sa,axis=2)
    stubborn=sm & same_row
    if np.any(stubborn):
        _, nearest=ndimage.distance_transform_edt(~donor,return_indices=True)
        sy,sx=np.nonzero(stubborn)
        clean_arr[sy,sx]=sa[nearest[0,sy,sx],nearest[1,sy,sx]]
        stubborn2=sm & np.all(clean_arr==sa,axis=2)
        if np.any(stubborn2):
            # A nearest donor can legitimately have the exact same RGBA value as the
            # source effect pixel. For the remaining tiny set, select the closest donor
            # whose RGBA differs, still strictly inside this sign's red-body donor mask.
            dyy,dxx=np.nonzero(donor)
            if not len(dxx):
                raise RuntimeError(("no alternate donor pixels",row["key"]))
            for py,px in zip(*np.nonzero(stubborn2)):
                diff=np.any(sa[dyy,dxx] != sa[py,px],axis=1)
                if not np.any(diff):
                    raise RuntimeError(("all donor pixels equal stubborn source pixel",row["key"],int(px),int(py)))
                yy=dyy[diff]; xx=dxx[diff]
                k=int(np.argmin((yy-int(py))**2 + (xx-int(px))**2))
                clean_arr[py,px]=sa[yy[k],xx[k]]
            stubborn3=sm & np.all(clean_arr==sa,axis=2)
            if np.any(stubborn3):
                raise RuntimeError(("alternate donor failed to remove source residue",row["key"],int(stubborn3.sum())))
clean=Image.fromarray(clean_arr,"RGBA")

# Source effect must be fully changed away in clean plate.
same_clean=np.all(clean_arr==sa,axis=2)
clean_residue=int(np.count_nonzero(source_mask & same_clean))
if clean_residue:
    raise RuntimeError(("clean source residue",clean_residue))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra","libnvtt-bin"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists():
    raise RuntimeError(("font",FONT))
if not Path("/usr/bin/nvcompress").exists():
    raise RuntimeError("nvcompress unavailable")

def shear(im,amount):
    add=max(1,int(round(amount*im.height)))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,(1,-amount,add,0,1,0),resample=Image.Resampling.BICUBIC)

def source_colors(mask):
    pix=sa[mask][:,:3]
    fillpix=pix[(pix[:,0]>170)&(pix[:,1]>135)&(pix[:,2]>70)]
    shadowpix=pix[(pix[:,0]>160)&(pix[:,1]>55)&(pix[:,1]<180)&(pix[:,2]<170)]
    fill=tuple(int(v) for v in (np.median(fillpix,axis=0) if len(fillpix) else np.array([250,230,175])))+(255,)
    shadow=tuple(int(v) for v in (np.median(shadowpix,axis=0) if len(shadowpix) else np.array([235,125,85])))+(255,)
    return fill,shadow

final=clean.copy()
target=np.zeros((H,W),bool)
safe_target_blocks=set()

# Source-family counter-space repair: natural-aspect 18px Hangul, thin source-red
# keyline, no heavy generic white extrusion. Review persisted DDS at practical scale.
MEDIUM=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Medium"],text=True).strip()
if not MEDIUM or not Path(MEDIUM).exists():raise RuntimeError("No Korean Medium font")
preencode={}
for row,sm,banner,safe_banner in zip(rows,source_masks,banner_masks,safe_banner_masks):
    x0,y0,x1,y1=row["source_bbox"];sw=x1-x0;sh=y1-y0
    font=ImageFont.truetype(MEDIUM,24*4)
    m=Image.new("L",(1200,350),0);d=ImageDraw.Draw(m)
    tb=d.textbbox((0,0),row["korean"],font=font)
    d.text((40-tb[0],40-tb[1]),row["korean"],font=font,fill=255)
    bb=m.getbbox()
    if not bb:raise RuntimeError(("empty Korean glyph",row["key"]))
    size={"start":(43,18),"goal":(23,18)}[row["key"]]
    m=m.crop(bb).resize(size,Image.Resampling.LANCZOS)
    m=shear(m,0.10).point(lambda v:255 if v>=130 else 0)
    face_n=int(sum(m.histogram()[1:]))
    face_frac=face_n/(m.width*m.height)
    if face_frac<0.13 or face_frac>0.57:
        raise RuntimeError(("counter-space occupancy not readable",row["key"],face_frac))
    edge=m.filter(ImageFilter.MaxFilter(3))
    w,h=m.size
    glyph=Image.new("RGBA",(w+2,h+2),(0,0,0,0))
    glyph.paste((117,40,25,255),(1,1,w+1,h+1),edge)
    glyph.paste((255,242,211,255),(0,0,w,h),m)
    glyph=glyph.crop(glyph.getchannel("A").getbbox())
    px=x0+(sw-glyph.width)//2;py=y0+(sh-glyph.height)//2
    lm=np.zeros((H,W),bool)
    ga=np.asarray(glyph.getchannel("A"))>0
    lm[py:py+glyph.height,px:px+glyph.width]=ga
    lb=bbox(lm)
    if lb is None or not (lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1):
        raise RuntimeError(("glyph overflow",row["key"],lb,row["source_bbox"]))
    if np.any(lm&~safe_banner):raise RuntimeError(("sign/art intrusion",row["key"]))
    if np.any(lm&target):raise RuntimeError(("glyph collision",row["key"]))
    final.alpha_composite(glyph,(px,py));target|=lm
    blocks={(int(x)//4,int(y)//4) for y,x in zip(*np.nonzero(lm))}
    safe_target_blocks |= blocks
    preencode[row["key"]]={"xy":[px,py],"image":glyph}
    glyph.save(out/("B253_"+row["key"]+"_PREENCODE.png"))
    row.update({"localized_bbox":lb,"source_width":sw,"source_height":sh,
      "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],
      "delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font":"Noto Sans CJK KR Medium 24px/4x source-family",
      "font_size":24,"readable_shear":0.10,"face_occupancy":round(face_frac,4),
      "shadow_offset":1,"fill_rgba":[255,242,211,255],
      "shadow_rgba":[117,40,25,255],"target_bc3_blocks":len(blocks)})

# Compress entire raw-orientation image, then splice only complete sign-interior BC3
# blocks touched by source removal or Korean lettering. Every other compressed block
# remains byte-identical to the canonical DDS.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/B253_final_raw.png"); tmp_dds=Path("/tmp/B253_final_nv.dds")
raw_final.save(tmp_png)
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(tmp_png),str(tmp_dds)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=tmp_dds.read_bytes()
if tb[:4]!=b"DDS " or tb[84:88]!=b"DXT5" or len(tb)!=len(sb):
    raise RuntimeError(("nvcompress structure",tb[:4],tb[84:88],len(tb),len(sb)))

# Convert readable patch blocks to raw coordinates (mirror_y). Full sign-body
# blocks may use the fresh BC3 encode; partial blocks keep original endpoints and
# outside indices, changing only sign-hull pixels to the nearest palette entry.
patch_blocks_readable=safe_source_blocks|safe_target_blocks
banner_union=np.zeros((H,W),bool)
for bm in safe_banner_masks:
    banner_union |= bm
allowed=np.zeros((H,W),bool)
for bx,by in patch_blocks_readable:
    allowed[by*4:by*4+4,bx*4:bx*4+4] |= banner_union[by*4:by*4+4,bx*4:bx*4+4]
# Tight source-bbox containment overrides the sign-body block mask.
exact_source=np.zeros((H,W),bool)
for rrrow in rows:
    xa,ya,xb,yb=rrrow["source_bbox"]
    exact_source[ya:yb,xa:xb]=True
allowed &= exact_source
bw=W//4; bh=H//4
patch_blocks_raw={(bx,bh-1-by) for bx,by in patch_blocks_readable}
allowed_raw=np.flipud(allowed)
desired_raw=np.asarray(raw_final,dtype=np.uint8)
outb=bytearray(sb)
partial_constrained_blocks=0
full_reencoded_blocks=0

def rgb565(v):
    return np.array([((v>>11)&31)*255/31.0,((v>>5)&63)*255/63.0,(v&31)*255/31.0],dtype=np.float64)

def color_palette(block):
    c0=int.from_bytes(block[8:10],"little"); c1=int.from_bytes(block[10:12],"little")
    p0=rgb565(c0); p1=rgb565(c1)
    return [p0,p1,(2*p0+p1)/3.0,(p0+2*p1)/3.0]

def alpha_palette(block):
    a0=block[0]; a1=block[1]
    if a0>a1:
        return [float(a0),float(a1)]+[((7-i)*a0+i*a1)/7.0 for i in range(1,7)]
    return [float(a0),float(a1)]+[((5-i)*a0+i*a1)/5.0 for i in range(1,5)]+[0.0,255.0]

def get_aidx(block):
    bits=int.from_bytes(block[2:8],"little")
    return [(bits>>(3*i))&7 for i in range(16)]

def get_cidx(block):
    bits=int.from_bytes(block[12:16],"little")
    return [(bits>>(2*i))&3 for i in range(16)]

def set_indices(block,aidx,cidx):
    nb=bytearray(block)
    abits=sum((int(v)&7)<<(3*i) for i,v in enumerate(aidx))
    cbits=sum((int(v)&3)<<(2*i) for i,v in enumerate(cidx))
    nb[2:8]=abits.to_bytes(6,"little")
    nb[12:16]=cbits.to_bytes(4,"little")
    return bytes(nb)

for bx,by in patch_blocks_raw:
    off=128+(by*bw+bx)*16
    am=allowed_raw[by*4:by*4+4,bx*4:bx*4+4]
    if not np.any(am):
        continue
    if np.all(am):
        outb[off:off+16]=tb[off:off+16]
        full_reencoded_blocks+=1
        continue
    ob=bytes(outb[off:off+16])
    ap=alpha_palette(ob); cp=color_palette(ob)
    ai=get_aidx(ob); ci=get_cidx(ob)
    want=desired_raw[by*4:by*4+4,bx*4:bx*4+4]
    for yy in range(4):
        for xx in range(4):
            if not am[yy,xx]:
                continue
            i=yy*4+xx
            rgb=want[yy,xx,:3].astype(np.float64); aa=float(want[yy,xx,3])
            ai[i]=min(range(8),key=lambda k:abs(ap[k]-aa))
            ci[i]=min(range(4),key=lambda k:float(np.sum((cp[k]-rgb)**2)))
    outb[off:off+16]=set_indices(ob,ai,ci)
    partial_constrained_blocks+=1
candidate.write_bytes(outb)
cand_sha=sha256_file(candidate)

dec_raw=Image.open(candidate).convert("RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)

changed=np.any(sa!=da,axis=2)
outside=int(np.count_nonzero(changed&~allowed))
alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
introduced=int(np.count_nonzero((da[:,:,3]>8)&(sa[:,:,3]<=8)&~allowed))
if outside or alpha_out or introduced:
    raise RuntimeError(("A183 exact-source-bbox overflow",outside,alpha_out,introduced))
from io import BytesIO
prev_raw=Image.open(BytesIO(prior_bytes)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
prev_a=np.asarray(prev_raw,dtype=np.uint8)
blast_out=int(np.count_nonzero(np.any(prev_a!=da,axis=2)&~exact_source))
blast_alpha=int(np.count_nonzero((prev_a[:,:,3]!=da[:,:,3])&~exact_source))
previous_outside=int(np.count_nonzero(np.any(sa!=prev_a,axis=2)&~exact_source))
if blast_out>previous_outside:
    raise RuntimeError(("A183 grew changed area outside source bboxes",blast_out,previous_outside))


# Final source-residue gate outside a 2px guard around new Korean.
guard=ndimage.binary_dilation(target,iterations=2)
same_source=np.all(da==sa,axis=2)
residue_exact=int(np.count_nonzero(source_mask & same_source & ~guard))
# Color-family fallback: any non-red leftover source-effect pixel outside the guard is a hard fail.
rrf=da[:,:,0].astype(np.int16); ggf=da[:,:,1].astype(np.int16); bbf=da[:,:,2].astype(np.int16)
final_red=(rrf>105)&(rrf>ggf+20)&(rrf>bbf+10)&(ggf<190)&(bbf<195)&(da[:,:,3]>8)
residue_color=int(np.count_nonzero(source_mask & ~guard & ~final_red))
if residue_color:
    # A183R2 left one source-effect pixel in a partial BC3 boundary block
    # after the clean plate was encoded. Fix the ACTUAL compressed color/alpha
    # indices inside the exact source bbox, never weaken residue thresholds.
    bad=np.argwhere(source_mask & ~guard & ~final_red)
    if len(bad)>8: raise RuntimeError(("too much BC3 source residue for constrained repair",len(bad)))
    fixed=[]
    for ry,rx in bad:
        ry=int(ry);rx=int(rx)
        if not allowed[ry,rx] or not exact_source[ry,rx]:
            raise RuntimeError(("source residue on protected pixel",rx,ry))
        raw_y=H-1-ry;bx=rx//4;by=raw_y//4;i=(raw_y%4)*4+(rx%4)
        pos=128+(by*bw+bx)*16
        block=bytes(outb[pos:pos+16])
        ai=get_aidx(block);ci=get_cidx(block)
        cp=color_palette(block);ap=alpha_palette(block)
        goal_rgb=clean_arr[ry,rx,:3].astype(np.float64)
        choices=[k for k in range(4) if cp[k][0]>105 and cp[k][0]>cp[k][1]+20 and cp[k][0]>cp[k][2]+10 and cp[k][1]<190]
        if not choices: raise RuntimeError(("no safe red BC3 palette entry",rx,ry,[p.tolist() for p in cp]))
        ci[i]=min(choices,key=lambda k:float(np.sum((cp[k]-goal_rgb)**2)))
        ai[i]=min(range(8),key=lambda k:abs(ap[k]-float(clean_arr[ry,rx,3])))
        outb[pos:pos+16]=set_indices(block,ai,ci)
        fixed.append([rx,ry,bx,by])
    candidate.write_bytes(outb)
    cand_sha=sha256_file(candidate)
    dec_raw=Image.open(candidate).convert("RGBA")
    dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    da=np.asarray(dec,dtype=np.uint8)
    chk_change=np.any(sa!=da,axis=2)
    chk_out=int(np.count_nonzero(chk_change&~allowed))
    chk_alpha=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
    if chk_out or chk_alpha: raise RuntimeError(("post-fix outside changed",chk_out,chk_alpha))
    rrf=da[:,:,0].astype(np.int16);ggf=da[:,:,1].astype(np.int16);bbf=da[:,:,2].astype(np.int16)
    final_red=(rrf>105)&(rrf>ggf+20)&(rrf>bbf+10)&(ggf<190)&(bbf<195)&(da[:,:,3]>8)
    residue_color=int(np.count_nonzero(source_mask & ~guard & ~final_red))
    print("BC3_TINY_SOURCE_RESIDUE_CORRECTION",fixed,"remaining",residue_color,flush=True)
if residue_color:
    raise RuntimeError(("final source residue",residue_exact,residue_color))

# Fail closed on post-encode loss of full-opacity Hangul strokes.
integrity=[]
for row in rows:
    z=preencode[row["key"]];px,py=z["xy"];g=z["image"]
    ih,iw=g.height,g.width
    pre=np.asarray(g);post=da[py:py+ih,px:px+iw]
    face=(pre[:,:,0]>=245)&(pre[:,:,1]>=225)&(pre[:,:,2]>=200)&(pre[:,:,3]==255)
    n=int(face.sum())
    if n<45:raise RuntimeError(("insufficient face pixels",row["key"],n))
    bright=(post[:,:,0]>=195)&(post[:,:,1]>=140)&(post[:,:,2]>=105)&(post[:,:,3]>=170)
    k=int((face&bright).sum())
    scan=[]
    for yy in range(ih):
        zc=int(face[yy].sum())
        if zc>=4:scan.append({"y":int(py+yy),"ratio":round(int((face[yy]&bright[yy]).sum())/zc,4)})
    bad=[q["y"] for q in scan if q["ratio"]<0.25]
    item={"key":row["key"],"face":n,"bright_retained":k,
      "face_recall":round(k/n,4),"bad_scanlines":bad,"scanlines":scan}
    integrity.append(item)
    if k/n<0.77 or bad:raise RuntimeError(("BC3 face is fractured; block publication",item))
print("B253_DECODED_FACE_INTEGRITY",integrity,flush=True)

# Candidate bboxes from actual decoded-vs-clean alpha/content delta inside source bboxes.
clean_a=np.asarray(clean.getchannel("A"))
for row in rows:
    x0,y0,x1,y1=row["source_bbox"]
    # Use target-render mask bbox as semantic bbox; decoded candidate can have BC3 fringe,
    # but it must remain within the source bbox.
    lb=row["localized_bbox"]
    if lb[0]<x0 or lb[1]<y0 or lb[2]>x1 or lb[3]>y1:
        raise RuntimeError(("bbox escape",row["key"],row["source_bbox"],lb))

# Compressed-block audit.
changed_blocks=0; outside_blocks=0
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=outb[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patch_blocks_raw:
                outside_blocks+=1
if outside_blocks:
    raise RuntimeError(("compressed block drift",outside_blocks))

# Evidence
src.save(out/"B253_SOURCE_READABLE.png")
clean.save(out/"B253_CLEAN_PLATE.png")
dec.save(out/"B253_FINAL_READABLE.png")
src_raw.save(out/"B253_SOURCE_RAW.png")
dec_raw.save(out/"B253_FINAL_RAW.png")
Image.fromarray((source_mask.astype(np.uint8)*255),"L").save(out/"B253_SOURCE_TEXT_MASK.png")
Image.fromarray((allowed.astype(np.uint8)*255),"L").save(out/"B253_ALLOWED_BLOCK_MASK.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"B253_TARGET_MASK.png")

def on_bg(im,bg=(245,245,245,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def crop_card(label,im,box,scale=4):
    v=on_bg(im).crop(box).resize(((box[2]-box[0])*scale,(box[3]-box[1])*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+30),"white"); c.paste(v,(0,30)); ImageDraw.Draw(c).text((6,7),label,fill="black"); return c

cards=[]
for row in rows:
    bx0,by0,bx1,by1=row["banner_bbox"]; pad=14
    box=(max(0,bx0-pad),max(0,by0-pad),min(W,bx1+pad),min(H,by1+pad))
    for label,im in [("SOURCE",src),("CLEAN",clean),("FINAL",dec)]:
        cards.append(crop_card(f'{row["source"]}->{row["korean"]} {label}',im,box,4))
mw=max(c.width for c in cards); mh=sum(c.height for c in cards)+8*(len(cards)-1)
sheet=Image.new("RGB",(mw,mh),"white"); yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.thumbnail((1800,3200),Image.Resampling.LANCZOS)
sheet.save(out/"B253_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=97)

raw_cards=[]
for label,im in [("SOURCE_RAW_MIRROR_Y",src_raw),("FINAL_RAW_MIRROR_Y",dec_raw)]:
    v=on_bg(im)
    v.thumbnail((1200,1200),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+30),"white"); c.paste(v,(0,30)); ImageDraw.Draw(c).text((6,7),label,fill="black"); raw_cards.append(c)
mw=max(c.width for c in raw_cards); mh=sum(c.height for c in raw_cards)+8
rs=Image.new("RGB",(mw,mh),"white"); yy=0
for c in raw_cards:
    rs.paste(c,(0,yy)); yy+=c.height+8
rs.thumbnail((1400,2200),Image.Resampling.LANCZOS)
rs.save(out/"B253_RAW_CONTACT.jpg",quality=95)

report={
 "schema_version":2,"role":"B","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "queue_index":214,"asset":asset,
 "readiness_tier":"C269_RETURNED_REWORK_MATERIAL_RENDERED",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3da79726739ac631d8e2703a65330dbb0c310770","url":url,"sha256":SOURCE_SHA},
 "classification":{"from":"zoom_review","to":"localize_text","segments":[{"source":"START","korean":"출발"},{"source":"GOAL","korean":"골"}],"physical_elements":2,
   "protected":["OutRun2 logos","course-map artwork","stage photos","route artwork","all non-label pixels"]},
 "construction":"Controller-reviewed BF229 route map uses the same START/GOAL red-badge family as B191/A116. Source-effect pixels are detected only inside the route-map red signs. Fully permitted BC3 blocks use the fresh encode; sign-edge partial blocks preserve original BC3 endpoints and all outside indices while changing only sign-hull pixel indices, so white rim/map/photo/logo pixels remain exact.",
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":MIPS,"header_128_exact":bytes(outb[:128])==sb[:128],"raw_orientation":"mirror_y"},
 "rows":rows,
 "bc3_decoded_glyph_integrity":integrity,
  "static_qa":{"elements_total":2,"bbox_size_positive_margin":"2/2 PASS","clean_source_residue":clean_residue,
   "changed_outside_allowed_blocks":outside,"alpha_changed_outside_allowed_blocks":alpha_out,
   "introduced_visible_outside_allowed_blocks":introduced,"final_source_residue_exact":residue_exact,
   "final_source_residue_color":residue_color,"localized_overlap":int(np.count_nonzero(source_masks[0]&source_masks[1])),
   "changed_bc3_blocks":changed_blocks,"changed_bc3_blocks_outside_allowed":outside_blocks,
   "full_reencoded_blocks":full_reencoded_blocks,"partial_constrained_blocks":partial_constrained_blocks,"status":"PASS"},
 "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "rework_trigger":"B252_CONTROLLER_VISUAL_FAIL_GLYPH_COUNTER_SPACES_COLLAPSED",
 "prior_candidate_sha256":PRIOR_SHA,
 "target_width_by_row":{"start":43,"goal":23},
 "exact_source_bbox_hard_gate":{"decoded_outside":outside,"alpha_outside":alpha_out,"introduced_outside":introduced,
   "previous_to_current_outside":blast_out,"previous_to_current_alpha_outside":blast_alpha},
 "execution_backend":"GITHUB_HOSTED_CPU_WORKER",
 "fresh_independent_c":"REQUIRED_C2","c3":"REQUIRED_AFTER_FRESH_C",
 "pre_ingame":"PENDING_FRESH_C_C3","runtime_validation":"UNTESTED",
 "runtime_validation":"UNTESTED",
 "status":"B253_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B253_BF229CF4_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B253_BF229CF4.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":214,"asset":"BF229CF4","source_sha256":SOURCE_SHA,
 "candidate_sha256":cand_sha,"report":str(rp.relative_to(repo)),"status":"B253_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B253_DONE",cand_sha,[(r["key"],r["banner_bbox"],r["source_bbox"],r["localized_bbox"]) for r in rows],flush=True)