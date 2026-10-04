#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
# Candidate-completion retry: exact-HD diagnostic exists; select the reviewed semantic line cluster and render in the same invocation.
run="20261004-B-PRODUCTION21"
# Retry after C107 detected residual source pixels in the pre-shadow-cleanup candidate.
outdir=repo/"localization/graphics/role_B"/run
outdir.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds"
source_sha_expected="cfed1de58cefd8c235fc464e27058439ffd26427294a3bce17192e584679426a"
source_dds=Path("/tmp/53CE39D5_HD.dds")
urllib.request.urlretrieve(source_url,source_dds)
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

# Exact-HD readable-orientation target regions. These exclude song titles, Ferrari/model art,
# OutRun logos, vehicle images, icons and unrelated selector artwork.
TARGETS=[
 {"key":"random","source":"RANDOM","korean":["무작위"],"cell":[1110,0,1490,125],"kind":"white","expected_lines":1,"slant":0.10},
 {"key":"time_attack_or2","source":"TimeAttack Mode OutRun2","korean":["타임 어택","모드","아웃런2"],"cell":[0,1620,365,1845],"kind":"orange","expected_lines":3,"slant":0.09},
 {"key":"heart_attack_or2","source":"HeartAttack Mode OutRun2","korean":["하트 어택","모드","아웃런2"],"cell":[375,1620,740,1845],"kind":"orange","expected_lines":3,"slant":0.09},
 {"key":"outrun_or2","source":"OutRun Mode OutRun2","korean":["아웃런","모드","아웃런2"],"cell":[750,1610,1095,1845],"kind":"orange","expected_lines":3,"slant":0.09},
 {"key":"time_attack_special","source":"TimeAttack Mode SPECIAL TOURS","korean":["타임 어택","모드","스페셜 투어"],"cell":[1110,1460,1470,1705],"kind":"orange","expected_lines":3,"slant":0.09},
 {"key":"heart_attack_special","source":"HeartAttack Mode SPECIAL TOURS","korean":["하트 어택","모드","스페셜 투어"],"cell":[1470,1460,1840,1710],"kind":"orange","expected_lines":3,"slant":0.09},
 {"key":"outrun_special","source":"OutRun Mode SPECIAL TOURS","korean":["아웃런","모드","스페셜 투어"],"cell":[1030,1790,1405,2048],"kind":"orange","expected_lines":3,"slant":0.09},
]

def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read_source(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]
    w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]
    mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]
    bpp=struct.unpack_from("<I",b,88)[0]
    masks=struct.unpack_from("<IIII",b,92)
    if sha256(p)!=source_sha_expected: raise RuntimeError("source SHA mismatch")
    if not (w==2048 and h==2048 and pitch==w*4 and mips==1 and fourcc==b"\0\0\0\0" and bpp==32):
        raise RuntimeError((w,h,pitch,mips,fourcc,bpp,masks,len(b)))
    if len(b)!=128+w*h*4: raise RuntimeError("unexpected payload")
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b,readable,{"width":w,"height":h,"pitch":pitch,"mips":mips,"fourcc":"00000000","bpp":bpp,"masks":[hex(x) for x in masks]}

def resolve_font():
    pat="Noto Sans CJK KR:style=Black"
    p=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
    if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        p=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
    if not p or not Path(p).exists(): raise RuntimeError("Noto CJK unavailable")
    return p

def group_rows(core, expected):
    counts=np.count_nonzero(core,axis=1)
    active=[i for i,v in enumerate(counts) if v>=2]
    groups=[]
    for y in active:
        if not groups or y-groups[-1][-1]>4: groups.append([y])
        else: groups[-1].append(y)
    groups=[g for g in groups if len(g)>=3]
    # Some selector cells include one unrelated line from a neighboring tile.
    # Fail closed on missing lines, but when there are extra groups choose the tightest
    # consecutive cluster matching the reviewed semantic line count. This preserves the
    # three vertically adjacent source lines and excludes distant neighboring artwork.
    if len(groups)<expected:
        raise RuntimeError(("line_group_count",len(groups),expected,[(g[0],g[-1],len(g)) for g in groups]))
    if len(groups)>expected:
        if expected==1:
            groups=[max(groups,key=len)]
        else:
            windows=[groups[i:i+expected] for i in range(len(groups)-expected+1)]
            groups=min(windows,key=lambda w:(w[-1][-1]-w[0][0],-sum(len(g) for g in w)))
    if len(groups)!=expected:
        raise RuntimeError(("line_group_select",len(groups),expected,[(g[0],g[-1],len(g)) for g in groups]))
    return [(g[0],g[-1]+1) for g in groups]

def core_mask(crop,kind):
    a=np.asarray(crop,dtype=np.uint8)
    r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    if kind=="orange":
        m=(r>155)&(g>55)&(g<225)&(b<135)&(r.astype(int)>g.astype(int)+18)&(g.astype(int)>b.astype(int)+18)
    else:
        mx=np.maximum(np.maximum(r,g),b);mn=np.minimum(np.minimum(r,g),b)
        m=(r>178)&(g>178)&(b>178)&((mx.astype(int)-mn.astype(int))<75)
    return m

def estimate_background(arr, mask, cell, bbox, panel_bg):
    # Reconstruct the plate row from source pixels that belong to the dominant local
    # panel colour family.  Sampling immediately beside individual glyphs can pick up
    # the source outline/plate border and leaves letter-shaped ghosts.
    x0,y0,x1,y1=cell
    bx0,by0,bx1,by1=bbox
    out=arr.copy()
    bg=np.asarray(panel_bg,dtype=np.int16)
    for y in range(by0,by1):
        xx=np.where(mask[y])[0]
        if not len(xx): continue
        row=arr[y,x0:x1]
        dist=np.max(np.abs(row.astype(np.int16)-bg[None,:]),axis=1)
        good=(dist<=32)&(row[:,3]>16)
        if np.any(good):
            fill=np.median(row[good],axis=0)
        else:
            fill=bg
        out[y,xx]=np.clip(np.round(fill),0,255).astype(np.uint8)
    return out

def shear(im,slant):
    if not slant:return im
    shift=max(0,int(round(slant*(im.height-1))))
    out=Image.new("RGBA",(im.width+shift,im.height),(0,0,0,0))
    for y in range(im.height):
        dx=int(round(slant*(im.height-1-y)))
        out.alpha_composite(im.crop((0,y,im.width,y+1)),(dx,y))
    return out

def render_line(text,bbox,fill,outline,slant,font_path):
    x0,y0,x1,y1=bbox
    W=x1-x0;H=y1-y0
    dummy=ImageDraw.Draw(Image.new("L",(8,8),0))
    for fs in range(min(150,int(H*.98)),7,-1):
        font=ImageFont.truetype(font_path,fs)
        sw=max(1,round(fs*.045))
        shadow=max(1,round(fs*.018))
        tb=dummy.textbbox((0,0),text,font=font,stroke_width=sw)
        tw=tb[2]-tb[0];th=tb[3]-tb[1]
        pad=sw+shadow+4
        fillm=Image.new("L",(tw+2*pad,th+2*pad),0)
        stroke=Image.new("L",fillm.size,0)
        ImageDraw.Draw(fillm).text((pad-tb[0],pad-tb[1]),text,font=font,fill=255)
        ImageDraw.Draw(stroke).text((pad-tb[0],pad-tb[1]),text,font=font,fill=255,stroke_width=sw,stroke_fill=255)
        sb=stroke.getbbox()
        fillm=fillm.crop(sb);stroke=stroke.crop(sb)
        tile=Image.new("RGBA",stroke.size,(0,0,0,0))
        sh=Image.new("L",stroke.size,0);sh.paste(stroke,(shadow,shadow))
        tile.paste((outline[0],outline[1],outline[2],min(210,outline[3])),(0,0),sh)
        tile.paste(outline,(0,0),stroke)
        tile.paste(fill,(0,0),fillm)
        tile=shear(tile,slant)
        ab=tile.getchannel("A").getbbox()
        if not ab:continue
        tile=tile.crop(ab)
        if tile.width>W-4 or tile.height>H-4:continue
        layer=Image.new("RGBA",(2048,2048),(0,0,0,0))
        px=x0+(W-tile.width)//2;py=y0+(H-tile.height)//2
        layer.alpha_composite(tile,(px,py))
        lb=layer.getchannel("A").getbbox()
        if lb and lb[0]>x0 and lb[1]>y0 and lb[2]<x1 and lb[3]<y1:
            return layer,fs,sw,shadow,list(lb)
    raise RuntimeError(("cannot_fit",text,bbox))

header,src,info=read_source(source_dds)
arr=np.asarray(src,dtype=np.uint8)
font_path=resolve_font()
all_source_mask=np.zeros((2048,2048),bool)
line_defs=[]
clean_arr=arr.copy()

for spec in TARGETS:
    x0,y0,x1,y1=spec["cell"]
    crop=src.crop((x0,y0,x1,y1))
    core=core_mask(crop,spec["kind"])
    if spec["key"]=="random":
        # Isolate the RANDOM title from the bright tile rim and separate question-mark icon.
        core[:12,:]=False
        core[100:,:]=False
        core[:,:35]=False
        core[:,-35:]=False
    groups=group_rows(core,spec["expected_lines"])
    if len(groups)!=len(spec["korean"]): raise RuntimeError(("semantic_line_mismatch",spec["key"]))
    for gi,((gy0,gy1),ko) in enumerate(zip(groups,spec["korean"])):
        li=gi+1
        ys,xs=np.nonzero(core[gy0:gy1])
        if not len(xs):raise RuntimeError(("empty_core",spec["key"],li))
        abs_core=np.zeros((2048,2048),bool)
        abs_core[y0+gy0:y0+gy1,x0:x1]=core[gy0:gy1]
        dil=np.asarray(Image.fromarray((abs_core*255).astype(np.uint8),"L").filter(ImageFilter.MaxFilter(13)))>0
        zone_top=max(0,(groups[gi-1][1]+gy0)//2) if gi>0 else max(0,gy0-8)
        zone_bottom=min(y1-y0,(gy1+groups[gi+1][0])//2) if gi+1<len(groups) else min(y1-y0,gy1+8)
        cellmask=np.zeros((2048,2048),bool);cellmask[y0+zone_top:y0+zone_bottom,x0:x1]=True
        dil &= cellmask

        # Estimate the dominant local panel colour from opaque non-core pixels in this
        # semantic line zone.  A tiny ring can be contaminated by the outline itself; the
        # dominant quantized panel colour is more robust and lets us retain the complete
        # dark outline/shadow + antialias fringe without swallowing the blue plate.
        sample_sel=cellmask & ~dil & (arr[:,:,3]>16)
        rp=arr[sample_sel]
        if len(rp)<40:raise RuntimeError(("insufficient_panel_samples",spec["key"],li,len(rp)))
        q=(rp[:,:3]//16).astype(np.uint8)
        uq,cnt=np.unique(q,axis=0,return_counts=True)
        modeq=uq[int(np.argmax(cnt))]
        same=np.all(q==modeq,axis=1)
        bg=np.median(rp[same],axis=0) if np.any(same) else np.median(rp,axis=0)
        dist=np.max(np.abs(arr.astype(np.int16)-bg.astype(np.int16)),axis=2)
        effect=dil & (dist>8) & (arr[:,:,3]>0)
        effect |= abs_core
        if spec["kind"]=="orange":
            # The source family has a dark/navy drop shadow that can extend several
            # pixels below the orange core.  Include only dark pixels near the core so
            # the shadow is removed without consuming the light-blue plate.
            wide=np.asarray(Image.fromarray((abs_core*255).astype(np.uint8),"L").filter(ImageFilter.MaxFilter(33)))>0
            wide &= cellmask
            lum_all=.2126*arr[:,:,0]+.7152*arr[:,:,1]+.0722*arr[:,:,2]
            effect |= wide & (lum_all<135) & (arr[:,:,3]>0)
        ey,ex=np.nonzero(effect)
        if not len(ex):raise RuntimeError(("empty_effect",spec["key"],li))
        eb=[int(ex.min()),int(ey.min()),int(ex.max())+1,int(ey.max())+1]
        if eb[0]<=x0 or eb[1]<=y0 or eb[2]>=x1 or eb[3]>=y1:
            raise RuntimeError(("effect_touches_cell",spec["key"],li,spec["cell"],eb))
        if np.any(all_source_mask & effect):
            raise RuntimeError(("source_line_overlap",spec["key"],li))
        all_source_mask |= effect

        # Source palette: median core fill and dark effect pixels.
        cp=arr[abs_core]
        fill=tuple(int(v) for v in np.median(cp,axis=0))
        ep=arr[effect]
        lum=.2126*ep[:,0]+.7152*ep[:,1]+.0722*ep[:,2]
        dark=ep[lum<=np.percentile(lum,30)]
        outline=tuple(int(v) for v in np.median(dark,axis=0)) if len(dark) else (20,20,20,255)
        if spec["kind"]=="white" and sum(fill[:3])<540: fill=(245,245,245,255)
        line_defs.append({
            "target":spec["key"],"source_label":spec["source"],"line_index":li,
            "korean":ko,"cell":spec["cell"],"source_bbox":eb,"fill":fill,
            "outline":outline,"slant":spec["slant"],"kind":spec["kind"],"background":tuple(int(v) for v in bg)
        })

# All orange selector labels in this atlas use the same source family. Enforce a shared
# measured Korean palette so a contaminated line sample cannot invent a different style.
orange=[ld for ld in line_defs if ld["kind"]=="orange"]
reliable=[ld for ld in orange if (.2126*ld["outline"][0]+.7152*ld["outline"][1]+.0722*ld["outline"][2]) < 100]
if not reliable: raise RuntimeError("no reliable orange source outline sample")
shared_fill=tuple(int(v) for v in np.median(np.array([ld["fill"] for ld in reliable]),axis=0))
shared_outline=tuple(int(v) for v in np.median(np.array([ld["outline"] for ld in reliable]),axis=0))
for ld in orange:
    ld["fill"]=shared_fill
    ld["outline"]=shared_outline

# Clean-plate reconstruction, line by line, only on actual source glyph/effect pixels.
for ld in line_defs:
    mask=np.zeros((2048,2048),bool)
    x0,y0,x1,y1=ld["source_bbox"]
    mask[y0:y1,x0:x1]=all_source_mask[y0:y1,x0:x1]
    clean_arr=estimate_background(clean_arr,mask,ld["cell"],ld["source_bbox"],ld["background"])
clean=Image.fromarray(clean_arr,"RGBA")
# Mirror C's residue gate in producer self-QA: every selected source-effect pixel must
# differ from the exact source after clean reconstruction.
source_same=np.all(clean_arr==arr,axis=2)
source_mask_unchanged=int(np.count_nonzero(source_same & all_source_mask))
if source_mask_unchanged:
    raise RuntimeError(("source_text_mask_pixels_unchanged_in_clean_plate",source_mask_unchanged))

# Fresh native-resolution Korean lettering.
final=clean.copy()
layers=[]
rows=[]
for ld in line_defs:
    layer,fs,sw,shadow,lb=render_line(ld["korean"],ld["source_bbox"],ld["fill"],ld["outline"],ld["slant"],font_path)
    for prev in layers:
        if ImageChops.multiply(layer.getchannel("A"),prev.getchannel("A")).getbbox():
            raise RuntimeError(("localized_overlap",ld["target"],ld["line_index"]))
    layers.append(layer)
    final.alpha_composite(layer)
    ob=ld["source_bbox"]
    sw0,sh0=ob[2]-ob[0],ob[3]-ob[1];lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    ok=(lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3] and lw<=sw0 and lh<=sh0)
    if not ok:raise RuntimeError(("size_gate",ld["target"],ld["line_index"],ob,lb))
    rows.append({
        "target":ld["target"],"source":ld["source_label"],"line_index":ld["line_index"],"korean":ld["korean"],
        "cell":list(ld["cell"]),"original_bbox":ob,"localized_bbox":lb,
        "source_width":sw0,"source_height":sh0,"localized_width":lw,"localized_height":lh,
        "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
        "containment":"PASS","size_ceiling":"PASS","style_kind":ld["kind"],
        "font_size":fs,"stroke_width":sw,"shadow":shadow,
        "fill":list(ld["fill"]),"outline":list(ld["outline"]),
        "multi_line_style_consistency":"PASS_SHARED_FONT_WEIGHT_FILL_OUTLINE_EFFECTS_SOURCE_RELATIVE_LINE_SCALE_PRESERVED"
    })

target_mask=np.zeros((2048,2048),bool)
for layer in layers:target_mask |= (np.asarray(layer.getchannel("A"))>0)
allowed=np.zeros((2048,2048),bool)
for r in rows:
    x0,y0,x1,y1=r["original_bbox"];allowed[y0:y1,x0:x1]=True
if np.any(target_mask & ~allowed):raise RuntimeError("target outside allowed")
guard=np.asarray(Image.fromarray((target_mask*255).astype(np.uint8),"L").filter(ImageFilter.MaxFilter(5)))>0
guard_conflicts=int(np.count_nonzero(guard & ~allowed))
if guard_conflicts:raise RuntimeError(("target_2px_guard_vs_protected",guard_conflicts))
# Positive separation between independently localized line masks.
for i in range(len(layers)):
    for j in range(i+1,len(layers)):
        if ImageChops.multiply(layers[i].getchannel("A"),layers[j].getchannel("A")).getbbox():
            raise RuntimeError(("localized_pair_overlap",i,j))

# Exact-header RGBA32 DDS write and decoded roundtrip.
raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=header[:128]+raw.tobytes("raw","RGBA")
candidate.write_bytes(payload)
cand_sha=hashlib.sha256(payload).hexdigest()
cb,cand_dec,ci=read_source(candidate) if sha256(candidate)==source_sha_expected else (None,None,None)
# read_source enforces source SHA, so decode candidate directly.
b=candidate.read_bytes()
cand_raw=Image.frombytes("RGBA",(2048,2048),b[128:],"raw","RGBA")
decoded=cand_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if b[:128]!=header[:128] or ImageChops.difference(final,decoded).getbbox() is not None:
    raise RuntimeError("DDS roundtrip/header mismatch")

srca=np.asarray(src,dtype=np.uint8);deca=np.asarray(decoded,dtype=np.uint8)
diff=np.any(srca!=deca,axis=2)
outside=diff & ~allowed
alpha_out=(srca[:,:,3]!=deca[:,:,3]) & ~allowed
if np.any(outside) or np.any(alpha_out):
    raise RuntimeError(("outside_gate",int(np.count_nonzero(outside)),int(np.count_nonzero(alpha_out))))
# Clean changes must be exactly within source text/effect mask.
cleana=np.asarray(clean,dtype=np.uint8)
clean_diff=np.any(srca!=cleana,axis=2)
if np.any(clean_diff & ~all_source_mask):raise RuntimeError("clean plate collateral")

# Ensure all source fill cores were removed before lettering by checking source-mask pixels against clean.
source_residue=0
for ld in line_defs:
    x0,y0,x1,y1=ld["source_bbox"]
    if np.array_equal(cleana[y0:y1,x0:x1],srca[y0:y1,x0:x1]):
        source_residue+=1
if source_residue:raise RuntimeError(("unchanged_source_text_region",source_residue))

def mask_img(m):return Image.fromarray((m.astype(np.uint8)*255),"L")
source_mask_img=mask_img(all_source_mask)
allowed_img=mask_img(allowed)
protected_img=ImageChops.invert(allowed_img)
target_img=mask_img(target_mask)
source_mask_img.save(outdir/"53CE39D5_HD_SOURCE_TEXT_MASK.png")
allowed_img.save(outdir/"53CE39D5_HD_ALLOWED_TEXT_REGION_MASK.png")
protected_img.save(outdir/"53CE39D5_HD_PROTECTED_MASK.png")
target_img.save(outdir/"53CE39D5_HD_TARGET_TEXT_MASK.png")
clean.save(outdir/"53CE39D5_HD_CLEAN_PLATE.png")

srcpng=Path("/tmp/53_src.png");cleanpng=Path("/tmp/53_clean.png");finalpng=Path("/tmp/53_final.png")
src.save(srcpng);clean.save(cleanpng);decoded.save(finalpng)
subprocess.run(["python3",str(repo/"tools/localization/validate_clean_plate.py"),str(srcpng),str(cleanpng),str(outdir/"53CE39D5_HD_SOURCE_TEXT_MASK.png"),"--report",str(outdir/"B_PRODUCTION21_CLEAN_PLATE_VALIDATION.json")],check=True)
subprocess.run(["python3",str(repo/"tools/localization/validate_clean_plate.py"),str(srcpng),str(finalpng),str(outdir/"53CE39D5_HD_ALLOWED_TEXT_REGION_MASK.png"),"--protected-mask",str(outdir/"53CE39D5_HD_PROTECTED_MASK.png"),"--report",str(outdir/"B_PRODUCTION21_FINAL_MASK_VALIDATION.json")],check=True)

def comp(im,bg):
    z=Image.new("RGBA",im.size,bg);z.alpha_composite(im);return z.convert("RGB")
def card(label,im,bg):
    v=comp(im,bg);v.thumbnail((800,800),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+28),"white");c.paste(v,(0,28));ImageDraw.Draw(c).text((5,5),label,fill="black")
    return c
cards=[card("SOURCE",src,(64,64,64,255)),card("CLEAN",clean,(64,64,64,255)),card("FINAL",decoded,(64,64,64,255)),card("FINAL_WHITE",decoded,(255,255,255,255))]
sw=cards[0].width+cards[1].width+8;sh=cards[0].height+cards[2].height+8
sheet=Image.new("RGB",(sw,sh),"white");sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(cards[0].width+8,0));sheet.paste(cards[2],(0,cards[0].height+8));sheet.paste(cards[3],(cards[2].width+8,cards[1].height+8))
sheet.save(outdir/"B_PRODUCTION21_53CE_COMPARE.jpg",quality=95)

contacts=[];srgb=comp(src,(64,64,64,255));crgb=comp(clean,(64,64,64,255));frgb=comp(decoded,(64,64,64,255))
for n,r in enumerate(rows,1):
    ob=r["original_bbox"];pad=14;cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(2048,ob[2]+pad),min(2048,ob[3]+pad))
    ims=[srgb.crop(cr),crgb.crop(cr),frgb.crop(cr)]
    scale=min(1.0,600/max(1,ims[0].width))
    if scale<1:
        ns=(round(ims[0].width*scale),round(ims[0].height*scale));ims=[x.resize(ns,Image.Resampling.LANCZOS) for x in ims]
    h=max(x.height for x in ims)+28;w=sum(x.width for x in ims)+12
    c=Image.new("RGB",(w,h),"white");xx=0
    for im in ims:c.paste(im,(xx,28));xx+=im.width+6
    ImageDraw.Draw(c).text((4,4),f'{n} {r["target"]}/{r["line_index"]} -> {r["korean"]}',fill="black")
    contacts.append(c)
cw=max(c.width for c in contacts);ch=sum(c.height for c in contacts)+3*(len(contacts)-1)
cs=Image.new("RGB",(cw,ch),"white");yy=0
for c in contacts:cs.paste(c,(0,yy));yy+=c.height+3
cs.save(outdir/"B_PRODUCTION21_53CE_ROW_CONTACT.jpg",quality=96)

r1=card("SOURCE_RAW",src.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(64,64,64,255))
r2=card("FINAL_RAW",decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(64,64,64,255))
rs=Image.new("RGB",(r1.width+r2.width+8,max(r1.height,r2.height)),"white");rs.paste(r1,(0,0));rs.paste(r2,(r1.width+8,0))
rs.save(outdir/"B_PRODUCTION21_53CE_RAW_COMPARE.jpg",quality=95)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":100,"asset":asset,
 "readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_url":source_url,"source_sha256":source_sha_expected,"candidate_sha256":cand_sha,
 "candidate_path":str(candidate.relative_to(repo)),
 "method":"exact 2048x2048 RGBA32 HD source -> colour-core semantic line discovery -> dominant-panel colour separation of complete source effects -> dominant-panel row reconstruction clean plate -> fresh native Hangul lettering -> exact-header DDS -> decoded all-channel static QA",
 "structure":{**info,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "semantic_targets":7,"physical_lines":len(rows),
 "translations":[{"source":t["source"],"korean":" / ".join(t["korean"])} for t in TARGETS],
 "protected_original":["all song titles/music credits","Ferrari/model names","vehicle images","OutRun/OutRun2 logos","music-note icons","non-target selector artwork"],
 "clean_plate":{"changed_pixels_outside_source_text_mask":int(np.count_nonzero(clean_diff & ~all_source_mask)),"source_text_mask_pixels_unchanged_in_clean_plate":source_mask_unchanged,"status":"PASS"},
 "containment":{"lines_total":len(rows),"lines_pass":len(rows),"lines_fail":0,"all_channel_changed_pixels_outside_exact_source_bboxes":int(np.count_nonzero(outside)),"alpha_changed_pixels_outside_exact_source_bboxes":int(np.count_nonzero(alpha_out)),"localized_overlap_pixels":0,"target_2px_guard_vs_protected_conflicts":guard_conflicts,"status":"PASS"},
 "rows":rows,
 "manual_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "RUNTIME_VALIDATION":"UNTESTED",
 "status":"B_PRODUCTION21_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(outdir/"B_PRODUCTION21_53CE_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(outdir/"B_PRODUCTION21_STATIC_VALIDATION_SUMMARY.json").write_text(json.dumps({
 "source_sha256":source_sha_expected,"candidate_sha256":cand_sha,
 "semantic_targets":"7/7","physical_lines":f"{len(rows)}/{len(rows)}",
 "exact_bbox_and_size_ceiling":f"{len(rows)}/{len(rows)} PASS",
 "clean_outside_source_text_mask":0,
 "source_text_mask_pixels_unchanged_in_clean_plate":source_mask_unchanged,
 "final_all_channel_outside_exact_bboxes":int(np.count_nonzero(outside)),
 "final_alpha_outside_exact_bboxes":int(np.count_nonzero(alpha_out)),
 "localized_overlap_pixels":0,"target_2px_guard_vs_protected_conflicts":guard_conflicts,"header_128_exact":True,"raw_orientation":"mirror_y",
 "song_title_and_vehicle_regions":"PIXEL_EXACT_OUTSIDE_TARGET_BBOXES",
 "runtime_validation":"UNTESTED","status":"PASS"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B_PRODUCTION21_DONE",cand_sha,"lines",len(rows),"outside",int(np.count_nonzero(outside)))
