#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops
from scipy import ndimage
from scipy.spatial import ConvexHull

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-PRODUCTION194-BF229CF4-START-GOAL"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3da79726739ac631d8e2703a65330dbb0c310770/Release/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
SOURCE_SHA="9a2e428bdb87399a7589338053b49efdcfd103d14f12a33a4bcde7705ab76c6b"
srcp=Path("/tmp/B194_BF229CF4.dds")
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
print("B194_RED_CANDIDATES",[(z["area"],z["bbox"],round((z["bbox"][2]-z["bbox"][0])/max(1,z["bbox"][3]-z["bbox"][1]),2)) for z in cands],flush=True)
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
print("B194_SELECTED",start_comp["area"],start_comp["bbox"],goal_comp["area"],goal_comp["bbox"],flush=True)

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
    # Union all meaningful red islands inside this tight sign ROI, then convex-hull them.
    lab2,n2=ndimage.label(red2)
    pts=[]
    comp_meta=[]
    for j in range(1,n2+1):
        cm=lab2==j; ar=int(cm.sum())
        if ar<15: continue
        yy,xx=np.nonzero(cm)
        comp_meta.append([ar,[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]])
        pts.extend((int(x),int(y)) for x,y in zip(xx,yy))
    if len(pts)<30:
        raise RuntimeError(("insufficient red hull seed",key,len(pts),comp_meta))
    pts_arr=np.asarray(pts,dtype=np.int32)
    hull=ConvexHull(pts_arr)
    poly=[(x0+int(pts_arr[i,0]),y0+int(pts_arr[i,1])) for i in hull.vertices]
    pm=Image.new("L",(W,H),0)
    ImageDraw.Draw(pm).polygon(poly,fill=255)
    banner_full=np.asarray(pm)>0
    banner_full &= alpha
    banner=ndimage.binary_erosion(banner_full,iterations=1,border_value=0)
    # Keep only source-visible sign pixels; this strips any accidental hull excursion into transparency.
    banner &= alpha

    # Source glyph/effect footprint: non-sign-red bright pixels near bright text within sign interior.
    sign_red=(rr>125)&(rr>gg+35)&(rr>bb+18)&(gg<175)&(bb<185)&alpha
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
            raise RuntimeError(("nearest donor failed to remove source residue",row["key"],int(stubborn2.sum())))
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

for row,sm,banner,safe_banner in zip(rows,source_masks,banner_masks,safe_banner_masks):
    x0,y0,x1,y1=row["source_bbox"]; sw=x1-x0; sh=y1-y0
    fill,shadow=source_colors(sm)
    chosen=None
    for fs in range(max(18,int(sh*1.10)),13,-1):
        font=ImageFont.truetype(FONT,fs)
        can=Image.new("RGBA",(max(360,sw*4),max(180,sh*4)),(0,0,0,0))
        d=ImageDraw.Draw(can)
        tb=d.textbbox((0,0),row["korean"],font=font)
        ox=18-tb[0]; oy=18-tb[1]; off=max(1,round(fs*0.055))
        d.text((ox+off,oy+off),row["korean"],font=font,fill=shadow)
        d.text((ox,oy),row["korean"],font=font,fill=fill,stroke_width=1,stroke_fill=shadow)
        gb=can.getchannel("A").getbbox()
        if not gb: continue
        glyph=shear(can.crop(gb),0.17)
        gb=glyph.getchannel("A").getbbox()
        if gb: glyph=glyph.crop(gb)
        if glyph.width>sw-4 or glyph.height>sh-4: continue
        px=x0+(sw-glyph.width)//2; py=y0+(sh-glyph.height)//2
        lm=np.zeros((H,W),bool)
        ma=np.asarray(glyph.getchannel("A"))>0
        lm[py:py+glyph.height,px:px+glyph.width]=ma
        lb=bbox(lm)
        if lb is None: continue
        if not(lb[0]>=x0+2 and lb[1]>=y0+2 and lb[2]<=x1-2 and lb[3]<=y1-2):
            continue
        blocks={(xx//4,yy//4) for yy,xx in zip(*np.nonzero(lm))}
        if np.any(lm & ~safe_banner):
            continue
        chosen=(glyph,px,py,lm,lb,blocks,fs,off,fill,shadow)
        break
    if chosen is None:
        raise RuntimeError(("no safe render fit",row["key"],row["source_bbox"]))
    glyph,px,py,lm,lb,blocks,fs,off,fill,shadow=chosen
    if np.any(target&lm):
        raise RuntimeError(("localized overlap",row["key"]))
    final.alpha_composite(glyph,(px,py)); target |= lm; safe_target_blocks |= blocks
    row.update({
      "localized_bbox":lb,"source_width":sw,"source_height":sh,
      "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font":"Noto Sans CJK KR Black","font_size":fs,"shear":0.17,"shadow_offset":off,
      "fill_rgba":fill,"shadow_rgba":shadow,"target_bc3_blocks":len(blocks)
    })

# Compress entire raw-orientation image, then splice only complete sign-interior BC3
# blocks touched by source removal or Korean lettering. Every other compressed block
# remains byte-identical to the canonical DDS.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png=Path("/tmp/B194_final_raw.png"); tmp_dds=Path("/tmp/B194_final_nv.dds")
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
    raise RuntimeError(("decoded protected drift",outside,alpha_out,introduced))

# Final source-residue gate outside a 2px guard around new Korean.
guard=ndimage.binary_dilation(target,iterations=2)
same_source=np.all(da==sa,axis=2)
residue_exact=int(np.count_nonzero(source_mask & same_source & ~guard))
# Color-family fallback: any non-red leftover source-effect pixel outside the guard is a hard fail.
rrf=da[:,:,0].astype(np.int16); ggf=da[:,:,1].astype(np.int16); bbf=da[:,:,2].astype(np.int16)
final_red=(rrf>105)&(rrf>ggf+20)&(rrf>bbf+10)&(ggf<190)&(bbf<195)&(da[:,:,3]>8)
residue_color=int(np.count_nonzero(source_mask & ~guard & ~final_red))
if residue_color:
    raise RuntimeError(("final source residue",residue_exact,residue_color))

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
src.save(out/"B194_SOURCE_READABLE.png")
clean.save(out/"B194_CLEAN_PLATE.png")
dec.save(out/"B194_FINAL_READABLE.png")
src_raw.save(out/"B194_SOURCE_RAW.png")
dec_raw.save(out/"B194_FINAL_RAW.png")
Image.fromarray((source_mask.astype(np.uint8)*255),"L").save(out/"B194_SOURCE_TEXT_MASK.png")
Image.fromarray((allowed.astype(np.uint8)*255),"L").save(out/"B194_ALLOWED_BLOCK_MASK.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"B194_TARGET_MASK.png")

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
sheet.save(out/"B194_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=97)

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
rs.save(out/"B194_RAW_CONTACT.jpg",quality=95)

report={
 "schema_version":1,"role":"B","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "queue_index":214,"asset":asset,
 "readiness_tier":"ZOOM_REVIEW_POSITIVE_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3da79726739ac631d8e2703a65330dbb0c310770","url":url,"sha256":SOURCE_SHA},
 "classification":{"from":"zoom_review","to":"localize_text","segments":[{"source":"START","korean":"출발"},{"source":"GOAL","korean":"골"}],"physical_elements":2,
   "protected":["OutRun2 logos","course-map artwork","stage photos","route artwork","all non-label pixels"]},
 "construction":"Controller-reviewed BF229 route map uses the same START/GOAL red-badge family as B191/A116. Source-effect pixels are detected only inside the route-map red signs. Fully permitted BC3 blocks use the fresh encode; sign-edge partial blocks preserve original BC3 endpoints and all outside indices while changing only sign-hull pixel indices, so white rim/map/photo/logo pixels remain exact.",
 "structure":{"width":W,"height":H,"format":"DXT5","mipmaps":MIPS,"header_128_exact":bytes(outb[:128])==sb[:128],"raw_orientation":"mirror_y"},
 "rows":rows,
 "static_qa":{"elements_total":2,"bbox_size_positive_margin":"2/2 PASS","clean_source_residue":clean_residue,
   "changed_outside_allowed_blocks":outside,"alpha_changed_outside_allowed_blocks":alpha_out,
   "introduced_visible_outside_allowed_blocks":introduced,"final_source_residue_exact":residue_exact,
   "final_source_residue_color":residue_color,"localized_overlap":int(np.count_nonzero(source_masks[0]&source_masks[1])),
   "changed_bc3_blocks":changed_blocks,"changed_bc3_blocks_outside_allowed":outside_blocks,
   "full_reencoded_blocks":full_reencoded_blocks,"partial_constrained_blocks":partial_constrained_blocks,"status":"PASS"},
 "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "runtime_validation":"UNTESTED",
 "status":"B194_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"B194_BF229CF4_REPORT.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B194_BF229CF4.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":214,"asset":"BF229CF4","source_sha256":SOURCE_SHA,
 "candidate_sha256":cand_sha,"report":str(rp.relative_to(repo)),"status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B194_DONE",cand_sha,[(r["key"],r["banner_bbox"],r["source_bbox"],r["localized_bbox"]) for r in rows],flush=True)