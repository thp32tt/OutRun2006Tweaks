#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")
repo=Path.cwd(); run="20261009-A201-Q161-C319-PRESERVED-FACE-REPAIR"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
tmp=Path("/tmp/outrun_A201"); tmp.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
source=tmp/"55B57CDE_HD.dds"; atlasp=tmp/"55B57CDE_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_55B57CDE_512x512_atlas.json",atlasp)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def dds_meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    H=struct.unpack_from("<I",b,12)[0]; W=struct.unpack_from("<I",b,16)[0]; mips=struct.unpack_from("<I",b,28)[0]; fourcc=b[84:88]
    need=128+((W+3)//4)*((H+3)//4)*16
    if fourcc!=b"DXT5" or mips not in (0,1) or len(b)!=need: raise RuntimeError(("unexpected DDS",W,H,mips,fourcc,len(b),need))
    return W,H,mips
sb=source.read_bytes(); ab=atlasp.read_bytes()
if gitblob(sb)!="0b12c672224ce05acb9470af895bbda335cc5543" or gitblob(ab)!="70001b44445f3e10b46eb7e3480abdece8eda790":
    raise RuntimeError(("pinned drift",gitblob(sb),gitblob(ab)))
W,H,MIPS=dds_meta(sb)
if (W,H)!=(2048,2048): raise RuntimeError(("dimension",W,H))
EXPECTED_BEFORE="2d0fe080682a0dc986436881bc6e12995250ca455c6984e5b75241e789c07d3b"
if not candidate.exists() or sha(candidate.read_bytes())!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift before A201",sha(candidate.read_bytes()) if candidate.exists() else None,EXPECTED_BEFORE))
old_bytes=candidate.read_bytes()
old_raw=Image.open(candidate).convert("RGBA"); old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM); olda=np.asarray(old,dtype=np.uint8)
regs={int(r["idx"]):r for r in json.loads(ab.decode("utf-8"))["regions"]}
raw_src=Image.open(source).convert("RGBA"); src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM); sa=np.asarray(src,dtype=np.uint8)

TARGETS={
0:("VIRGO","처녀자리"),1:("TAURUS","황소자리"),2:("SCORPIO","전갈자리"),3:("SAGITTARIUS","사수자리"),4:("PISCES","물고기자리"),5:("LIBRA","천칭자리"),
6:("LEO","사자"),7:("GEMINI","쌍둥이자리"),8:("CAPRICORN","염소자리"),9:("CANCER","게자리"),10:("ARIES","양자리"),11:("AQUARIUS","물병자리"),
12:("THAILAND","태국"),13:("SWITZERLAND","스위스"),14:("SWEDEN","스웨덴"),15:("SPAIN","스페인"),16:("SOUTH KOREA","대한민국"),17:("SINGAPORE","싱가포르"),
18:("OTHER","기타"),19:("NORWAY","노르웨이"),20:("NORTH KOREA","북한"),21:("NEW ZEALAND","뉴질랜드"),22:("MEXICO","멕시코"),23:("JAPAN","일본"),
24:("ITALY","이탈리아"),25:("HONG KONG","홍콩"),26:("GERMANY","독일"),27:("FRANCE","프랑스"),28:("FINLAND","핀란드"),29:("NETHERLANDS","네덜란드"),
30:("DENMARK","덴마크"),31:("CHINA","중국"),32:("CANADA","캐나다"),33:("BRITAIN","영국"),34:("BELGIUM","벨기에"),35:("AUSTRIA","오스트리아"),
36:("AUSTRALIA","호주"),37:("USA","미국")
}
if set(TARGETS)!=set(range(38)): raise RuntimeError("binding incomplete")

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
FONT_PATTERN="Noto Sans CJK KR:style=Black"
FONT=subprocess.check_output(["fc-match","-f","%{file}",FONT_PATTERN],text=True).strip()
if not FONT or not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("font unavailable",FONT))
# No nvcompress color selection: exact constant RGB565 source-face avoids source-family color speckling; BC3 alpha indices encoded directly.

elements=[]; source_union=np.zeros((H,W),bool); allowed=np.zeros((H,W),bool)
for idx,(english,korean) in TARGETS.items():
    if idx not in (8,10,12): continue  # C319 confirmed remaining pinholes; preserve A200 04/06 and 33 untouched regions
    x,y,cw,ch=map(int,regs[idx]["rect"]); roi=sa[y:y+ch,x:x+cw]; mask=roi[:,:,3]>1
    ys,xs=np.nonzero(mask)
    if not len(xs): raise RuntimeError(("empty",idx))
    eb=[x+int(xs.min()),y+int(ys.min()),x+int(xs.max())+1,y+int(ys.max())+1]
    gm=np.zeros((H,W),bool); gm[y:y+ch,x:x+cw]=mask
    if np.any(source_union & gm): raise RuntimeError(("source overlap",idx))
    source_union |= gm; allowed[eb[1]:eb[3],eb[0]:eb[2]]=True
    pix=sa[gm]; vis=pix[pix[:,3]>16]; med=vis if len(vis) else pix
    color=tuple(int(np.median(med[:,k])) for k in range(3))+(255,)
    elements.append({"idx":idx,"source":english,"korean":korean,"cell":[x,y,cw,ch],"source_mask":gm,"original_bbox":eb,
                     "source_mask_pixels":int(np.count_nonzero(gm)),"source_rgba_median":list(color)})

clean_arr=olda.copy(); clean_arr[allowed,:]=0; clean=Image.fromarray(clean_arr,"RGBA")
# Preserve exactly all 35 other already-localized rows, including their native BC3 compressed bytes.
final=clean.copy(); target_union=np.zeros((H,W),bool); layers=[]

def text_alpha(text,maxw,maxh):
    # FIT BY NATURAL CJK PIXEL DIMENSIONS. Never horizontally condense Hangul.
    # C319 failed preserved CAPRICORN/ARIES/THAILAND native glyph face BC3 pinholes.
    for fs in range(max(24,int(maxh*1.60)),18,-1):
        font=ImageFont.truetype(FONT,fs)
        d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=font)
        im=Image.new("L",(max(8,bb[2]-bb[0]+16),max(8,bb[3]-bb[1]+16)),0)
        ImageDraw.Draw(im).text((8-bb[0],8-bb[1]),text,font=font,fill=255)
        box=im.getbbox()
        if not box: continue
        im=im.crop(box)
        if im.width<=maxw and im.height<=maxh:
            return fs,im,1.0,im.width
    raise RuntimeError(("NO_NATIVE_GLYPH_FIT",text,maxw,maxh))

for e in elements:
    x0,y0,x1,y1=e["original_bbox"]
    bx0=((x0+3)//4)*4; by0=((y0+3)//4)*4; bx1=(x1//4)*4; by1=(y1//4)*4
    # Keep every changed BC3 block wholly inside the source bbox while using the
    # maximum pixel interior with >=1px exact-source margin.
    sx0=max(x0+1,bx0); sy0=max(y0+1,by0); sx1=min(x1-1,bx1); sy1=min(y1-1,by1)
    maxw=sx1-sx0; maxh=sy1-sy0
    if maxw<8 or maxh<8: raise RuntimeError(("no safe interior",e["idx"],e["original_bbox"],[sx0,sy0,sx1,sy1]))
    oldm=olda[y0:y1,x0:x1,3]>1; oys,oxs=np.nonzero(oldm)
    if not len(oxs): raise RuntimeError(("prior candidate empty",e["idx"]))
    oldbb=[x0+int(oxs.min()),y0+int(oys.min()),x0+int(oxs.max())+1,y0+int(oys.max())+1]
    fs,a,hscale,natural_w=text_alpha(e["korean"],maxw,maxh)
    px=sx0; py=sy0+(maxh-a.height)//2
    color=tuple(e["source_rgba_median"][:3])+(255,)
    tile=Image.new("RGBA",a.size,color); tile.putalpha(a)
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); layer.alpha_composite(tile,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    if np.any(target_union & lm): raise RuntimeError(("target overlap",e["idx"]))
    target_union|=lm; final.alpha_composite(layer); layers.append(layer)
    lb=list(layer.getchannel("A").getbbox() or ())
    if not(lb and lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1): raise RuntimeError(("bbox",e["idx"],e["original_bbox"],lb))
    e.update({"localized_bbox_preencode":lb,"font_file":Path(FONT).name,"font_pattern":FONT_PATTERN,"font_size":fs,
              "block_safe_bbox":[bx0,by0,bx1,by1],"render_safe_bbox":[sx0,sy0,sx1,sy1],
              "render_method":"NATURAL_CJK_WIDTH_ALPHA_CONTINUOUS_NO_HORIZ_SQUISH",
              "natural_width_before_condense":natural_w,"horizontal_scale":round(hscale,4),
              "prior_localized_bbox":oldbb,"prior_localized_width":oldbb[2]-oldbb[0],
              "prior_localized_height":oldbb[3]-oldbb[1],"prior_delta_left":oldbb[0]-x0})

# 1px separation
for i,m1 in enumerate([np.asarray(z.getchannel("A"))>0 for z in layers]):
    dil=np.asarray(Image.fromarray((m1.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for j in range(i+1,len(layers)):
        if np.any(dil & (np.asarray(layers[j].getchannel("A"))>0)): raise RuntimeError(("1px touch",i,j))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
# BC3 RGB constant fill precisely source flat-face, target glyph alpha encoded separately.

allowed_raw=np.flipud(allowed); source_raw=np.flipud(source_union); target_raw=np.flipud(target_union); source_alpha_raw=np.flipud(sa[:,:,3])
raw_final_arr=np.asarray(raw_final,dtype=np.uint8)
desired_alpha_raw=source_alpha_raw.copy()
desired_alpha_raw[allowed_raw]=0
desired_alpha_raw[target_raw]=raw_final_arr[:,:,3][target_raw]
bw=W//4; bh=H//4; outb=bytearray(old_bytes); target_blocks=set(); source_full=set(); source_partial=set()
r,g,b=(60,71,74)
FACE565=((r>>3)<<11)|((g>>2)<<5)|(b>>3)
FACE_BYTES=struct.pack("<HHI",FACE565,FACE565,0)

def alpha_indices(block):
    bits=int.from_bytes(block[2:8],"little"); return [(bits>>(3*i))&7 for i in range(16)]
def set_alpha_indices(block,idx):
    bits=sum((int(v)&7)<<(3*i) for i,v in enumerate(idx)); return block[:2]+bits.to_bytes(6,"little")+block[8:]
def alpha_palette(a0,a1):
    if a0>a1:
        return [a0,a1,(6*a0+1*a1)//7,(5*a0+2*a1)//7,(4*a0+3*a1)//7,(3*a0+4*a1)//7,(2*a0+5*a1)//7,(1*a0+6*a1)//7]
    return [a0,a1,(4*a0+1*a1)//5,(3*a0+2*a1)//5,(2*a0+3*a1)//5,(1*a0+4*a1)//5,0,255]
FIX_A0,FIX_A1=255,0
FIXPAL=alpha_palette(FIX_A0,FIX_A1)
def fixed_alpha_bytes(vals,force_nonzero):
    idx=[]
    nzchoices=[0,2,3,4,5,6,7]
    for a,nz in zip(vals,force_nonzero):
        choices=nzchoices if (nz and int(a)>0) else range(8)
        idx.append(min(choices,key=lambda k:abs(FIXPAL[k]-int(a))))
    bits=sum((int(v)&7)<<(3*i) for i,v in enumerate(idx))
    return bytes((FIX_A0,FIX_A1))+bits.to_bytes(6,"little")

for by in range(bh):
    y=by*4
    if not np.any(allowed_raw[y:y+4]): continue
    for bx in range(bw):
        x=bx*4; am=allowed_raw[y:y+4,x:x+4]; sm=source_raw[y:y+4,x:x+4]; tm=target_raw[y:y+4,x:x+4]
        if not np.any(am) and not np.any(tm): continue
        off=128+(by*bw+bx)*16
        if np.any(tm):
            if not np.all(am): raise RuntimeError(("target block crosses bbox",bx,by))
            vals=desired_alpha_raw[y:y+4,x:x+4].reshape(-1)
            alpha=fixed_alpha_bytes(vals,tm.reshape(-1))
            outb[off:off+16]=alpha+FACE_BYTES
            target_blocks.add((bx,by)); continue
        if np.all(am):
            vals=desired_alpha_raw[y:y+4,x:x+4].reshape(-1)
            alpha=fixed_alpha_bytes(vals,[False]*16)
            outb[off:off+16]=alpha+old_bytes[off+8:off+16]
            source_full.add((bx,by)); continue
        ob=bytes(outb[off:off+16]); idxs=alpha_indices(ob); pal=alpha_palette(ob[0],ob[1])
        z=[k for k,v in enumerate(pal) if v==0]
        if not z: raise RuntimeError(("boundary block has no exact-zero alpha code",bx,by,pal))
        zi=z[0]
        for yy in range(4):
            for xx in range(4):
                if am[yy,xx]: idxs[yy*4+xx]=zi
        nb=set_alpha_indices(ob,idxs)
        if nb[:2]!=ob[:2] or nb[8:]!=ob[8:]: raise RuntimeError(("endpoint/color drift",bx,by))
        outb[off:off+16]=nb; source_partial.add((bx,by))

candidate.write_bytes(outb); dec_raw=Image.open(candidate).convert("RGBA"); dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM); da=np.asarray(dec,dtype=np.uint8)
diff=np.any(olda!=da,axis=2); diff_out=int(np.count_nonzero(diff & ~allowed)); alpha_out=int(np.count_nonzero((olda[:,:,3]!=da[:,:,3]) & ~allowed))
intro=int(np.count_nonzero((olda[:,:,3]<=1)&(da[:,:,3]>1)&~allowed))
if any((diff_out,alpha_out,intro)): raise RuntimeError(("outside drift",diff_out,alpha_out,intro))
residue=int(np.count_nonzero(allowed & (da[:,:,3]>0) & ~target_union))
if residue: raise RuntimeError(("decoded alpha remains inside source bbox outside intended Hangul",residue))

bbox_exact=0; extra_total=0; missing_total=0
for e,layer in zip(elements,layers):
    x0,y0,x1,y1=e["original_bbox"]
    intended=np.asarray(layer.getchannel("A"))>0
    intended_crop=intended[y0:y1,x0:x1]
    cand_crop=da[y0:y1,x0:x1,3]>0
    extra=int(np.count_nonzero(cand_crop & ~intended_crop))
    missing=int(np.count_nonzero(intended_crop & ~cand_crop))
    extra_total+=extra; missing_total+=missing
    if extra or missing: raise RuntimeError(("decoded alpha footprint mismatch",e["idx"],extra,missing))
    ys,xs=np.nonzero(cand_crop)
    if not len(xs): raise RuntimeError(("decoded empty",e["idx"]))
    db=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]
    pre=e["localized_bbox_preencode"]
    if db!=pre: raise RuntimeError(("decoded bbox mismatch",e["idx"],pre,db))
    bbox_exact+=1
    dw,dh=db[2]-db[0],db[3]-db[1]; sw,sh=x1-x0,y1-y0
    if not(db[0]>x0 and db[1]>y0 and db[2]<x1 and db[3]<y1 and dw<=sw and dh<=sh):
        raise RuntimeError(("decoded bbox",e["idx"],e["original_bbox"],db))
    e.update({"localized_bbox":db,"localized_width":dw,"localized_height":dh,"source_width":sw,"source_height":sh,
      "delta_left":db[0]-x0,"delta_right":x1-db[2],"delta_top":db[1]-y0,"delta_bottom":y1-db[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "decoded_alpha_extra_pixels":extra,"decoded_alpha_missing_pixels":missing})
    e.pop("source_mask",None)

height_improved=sum(1 for e in elements if e["localized_height"]>e["prior_localized_height"])
height_not_worse=sum(1 for e in elements if e["localized_height"]>=e["prior_localized_height"])
left_anchor_improved=sum(1 for e in elements if e["delta_left"]<e["prior_delta_left"])
near_source_height=sum(1 for e in elements if e["localized_height"]>=max(1,e["source_height"]-10))
if len(elements)!=3 or sorted(e["idx"] for e in elements)!=[8,10,12]:
    raise RuntimeError("not exactly three diagnosed C319 regions")
if any(e["horizontal_scale"]!=1.0 for e in elements):
    raise RuntimeError(("Korean squish still present",elements))
# Persisted true opaque glyph cores cannot exhibit the C314 interior alpha pinholes.
for e,layer in zip(elements,layers):
    hi=np.asarray(layer.getchannel("A"))>235
    yy0,xx0=e["original_bbox"][1],e["original_bbox"][0]
    true_face=(np.asarray(layer.getchannel("A"))>=240)
    rgba=da[true_face]
    if len(rgba)<150: raise RuntimeError(("too little opaque native face",e["idx"]))
    pinholes=int(np.count_nonzero(rgba[:,3]<180))
    rgbdrift=int(np.count_nonzero(np.max(np.abs(rgba[:,:3].astype(int)-np.array((60,71,74))),axis=1)>24))
    if pinholes or rgbdrift: raise RuntimeError(("post-BC3 alpha/color pinhole",e["idx"],pinholes,rgbdrift))
    e["decoded_core_interior_pinhole_pixels"]=pinholes
    e["decoded_core_color_mismatch_pixels"]=rgbdrift

changed_blocks=0; changed_outside=0; patch=target_blocks|source_full|source_partial
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if old_bytes[off:off+16]!=outb[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patch: changed_outside+=1
if changed_outside: raise RuntimeError(("compressed outside patch",changed_outside))
if sha(bytes(outb))==EXPECTED_BEFORE:raise RuntimeError("No changed BC3 DDS bytes")

def comp(im):
    z=Image.new("RGBA",im.size,(65,65,65,255)); z.alpha_composite(im); return z.convert("RGB")
cards=[]
for e in elements:
    x0,y0,x1,y1=e["original_bbox"]; cr=(max(0,x0-8),max(0,y0-8),min(W,x1+8),min(H,y1+8))
    ims=[comp(z).crop(cr) for z in (src,old,clean,dec)]
    sc=min(1.4,250/max(1,ims[0].width)); ims=[z.resize((max(1,int(z.width*sc)),max(1,int(z.height*sc))),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+8,max(z.height for z in ims)+22),"white"); ImageDraw.Draw(c).text((3,3),f"{e['idx']} {e['source']} -> {e['korean']} SOURCE|A56|CLEAN|A157",fill="black")
    xx=0
    for z in ims: c.paste(z,(xx,22)); xx+=z.width+4
    cards.append(c)
cw=max(c.width for c in cards); sh=sum(c.height+2 for c in cards); sheet=Image.new("RGB",(cw,sh),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+2
sheet.save(out/"A201_55B57CDE_SOURCE_CLEAN_FINAL.jpg",quality=94)
comp(dec_raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A201_55B57CDE_FINAL_RAW_MIRROR_Y.jpg",quality=93)

# Native lossless per-region SOURCE / CLEAN / DECODED DDS on BWG at 100/75/50,
# including mirrored RAW. Controls intentionally keep 36 unrelated rows untouched.
for e in elements:
    idx=e["idx"]
    x0,y0,x1,y1=e["original_bbox"]
    rect=(max(0,x0-8),max(0,y0-8),min(W,x1+8),min(H,y1+8))
    for kind,im in (("SOURCE",src),("CLEAN",clean),("FINAL",dec)):
        im.crop(rect).save(out/f"A201_{idx:02}_{kind}_NATIVE.png")
    for bgname,rgb in (("BLACK",(0,0,0)),("GRAY",(95,95,95)),("WHITE",(245,245,245))):
        panels=[]
        for im in (src,clean,dec):
            b=Image.new("RGBA",im.size,(*rgb,255));b.alpha_composite(im)
            panels.append(b.convert("RGB").crop(rect))
        width,height=panels[0].size
        combined=Image.new("RGB",(width*3+12,height+26),"white")
        ImageDraw.Draw(combined).text((3,4),f"{idx:02} {e['source']} -> {e['korean']} | SOURCE / CLEAN / DDS",fill="black")
        for i,z in enumerate(panels):combined.paste(z,(i*(width+6),26))
        for pct in (100,75,50):
            view=combined if pct==100 else combined.resize((max(1,combined.width*pct//100),max(1,combined.height*pct//100)),Image.Resampling.LANCZOS)
            view.save(out/f"A201_{idx:02}_SOURCE_CLEAN_FINAL_{bgname}_{pct}.png")
    im1=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    im2=dec_raw
    rawrect=(rect[0],H-rect[3],rect[2],H-rect[1])
    rawpanels=[z.crop(rawrect) for z in (im1,im2)]
    raw=Image.new("RGBA",(rawpanels[0].width*2+6,rawpanels[0].height),(0,0,0,0))
    raw.alpha_composite(rawpanels[0]);raw.alpha_composite(rawpanels[1],(rawpanels[0].width+6,0))
    raw.save(out/f"A201_{idx:02}_SOURCE_FINAL_RAW.png")
# Verify exact original BC3 blocks of the other 35 rows remain byte-identical.
raw_allowed=np.flipud(allowed)
preserved_blocks=0
for by in range(H//4):
    for bx in range(W//4):
        blockmask=raw_allowed[by*4:by*4+4,bx*4:bx*4+4]
        if np.any(blockmask):continue
        off=128+(by*(W//4)+bx)*16
        if old_bytes[off:off+16]!=outb[off:off+16]:
            raise RuntimeError(("unrelated original BC3 block changed",bx,by))
        preserved_blocks+=1
report={"schema_version":1,"role":"A","run":run,"index":161,"asset":asset_rel,
"source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"blob_sha1":gitblob(sb),"sha256":sha(sb)},
"atlas_provenance":{"blob_sha1":gitblob(ab),"sha256":sha(ab),"regions":38},
"structure":{"width":W,"height":H,"format":"DXT5","mips":MIPS,"raw_orientation":"mirror_y","header_exact":bytes(outb[:128])==sb[:128]},
"old_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":sha(bytes(outb)),
"targeted_regions":elements,"repaired_rows":3,"other_regions_preserved":35,"untouched_BC3_blocks":preserved_blocks,
"translation_policy_note":"CAPRICORN=염소자리, ARIES=양자리, THAILAND=태국 preserve Korean strings; A200 LEO=사자 and PISCES=물고기자리 remain byte-identical pending independent user acceptance",
"root_cause":"C319 observed BC3 color/alpha speckle in retained region08/10/12","new_method":"Native unsqueezed Korean and exact source-flat gray RGB565 face, fixed BC3 alpha endpoints from glyph only; A200 region04/06 and 33 other regions byte-identical",
"source_clean":"SHA-pinned English source versus three cleared source-effect bboxes, no changed pixels outside for retained candidate",
"machine_checks":{"changed_pixels_outside_three_bboxes":diff_out,"alpha_changed_outside_three_bboxes":alpha_out,
"introduced_visible_outside_three_bboxes":intro,"source_residue_pixels":residue,
"decoded_alpha_extra_pixels":extra_total,"decoded_alpha_missing_pixels":missing_total,
"decoded_bbox_exact_match":f"{bbox_exact}/3 PASS","localized_overlap_pairs":0,
"changed_blocks_outside_patch":changed_outside,
"all_unrelated_blocks_unchanged":True,
"preserved_A200_04_06_and_other_33_blocks":True,
"opaque_core_color_pinhole_pixels":sum(e['decoded_core_interior_pinhole_pixels'] for e in elements),
"opaque_core_color_mismatch_pixels":sum(e['decoded_core_color_mismatch_pixels'] for e in elements)},
"persisted_dds_roundtrip":"PASS decoded source-visible and exact output header",
"producer_status":"MACHINE_PASS_CONTROLLER_VISUAL_PENDING","C1":"PENDING","C3":"PENDING",
"RUNTIME_VALIDATION":"UNTESTED"}

(out/"A201_Q161_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"role":"A","run":run,"index":161,"candidate_sha256":report["candidate_sha256"],
"repaired_regions":[8,10,12],"prior_candidate_sha256":EXPECTED_BEFORE,
"machine_qa":report["machine_checks"],"worker_status":report["producer_status"],
"RUNTIME_VALIDATION":"UNTESTED",
"report":str((out/"A201_Q161_REPORT.json").relative_to(repo))}
(wr/"A201_Q161.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print("A201_MACHINE_DONE",json.dumps(summary,ensure_ascii=False),flush=True)
