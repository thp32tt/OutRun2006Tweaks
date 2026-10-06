#!/usr/bin/env python3
# B209: source-faithful Korean 2-beolsik Jamo keycap candidate for 66743AA8.
# Heavy DDS/image work is intentionally executed only by the GitHub-hosted CPU worker.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

repo=Path.cwd()
run="20261006-B-PRODUCTION209-NAMEENTRY-JAMO-KEYCAPS"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_name_entry_xst/66743AA8_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/rel
candidate.parent.mkdir(parents=True,exist_ok=True)
worker_result=repo/"localization/graphics/worker_results/B209_NAMEENTRY_JAMO.json"

SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_name_entry_xst/66743AA8_1024x1024.dds"
ATLAS_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_name_entry_xst/66743AA8_1024x1024_atlas.json"
SOURCE_SHA="8e18676ac303b07a56d81d1d21c5e025e0baf46da49b16ae9d2e411960181f73"
source=Path("/tmp/B209_66743AA8_source.dds")
atlas_path=Path("/tmp/B209_66743AA8_atlas.json")
urllib.request.urlretrieve(SOURCE_URL,source)
urllib.request.urlretrieve(ATLAS_URL,atlas_path)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=SOURCE_SHA: raise RuntimeError(("source sha mismatch",sha(source)))
atlas=json.loads(atlas_path.read_text(encoding="utf-8"))
regions={r["name"]:r for r in atlas["regions"]}
if atlas.get("regions_count")!=49: raise RuntimeError(("atlas region drift",atlas.get("regions_count")))

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    linear=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]
    if not (w==1024 and h==1024 and fourcc==b"DXT3" and len(b)==128+w*h):
        raise RuntimeError(("dds structure",w,h,linear,mips,fourcc,len(b)))
    raw=Image.open(p).convert("RGBA")
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],readable,{
      "width":w,"height":h,"linear_size":linear,"mips":mips,
      "fourcc":"DXT3","compression":"BC2/DXT3","raw_mode":"DXT3"
    }

def write_dds(header,readable,p,mode):
    if mode!="DXT3": raise RuntimeError(("unexpected mode",mode))
    raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    temp=Path("/tmp/B209_encode_dxt3.dds")
    raw.save(temp,format="DDS",pixel_format="DXT3")
    encoded=temp.read_bytes()
    original=source.read_bytes()
    if encoded[:4]!=b"DDS " or encoded[84:88]!=b"DXT3":
        raise RuntimeError(("Pillow did not emit DXT3",encoded[84:88]))
    expected=readable.width*readable.height
    if len(encoded)!=128+expected or len(original)!=128+expected:
        raise RuntimeError(("DXT3 size drift",len(encoded),len(original),128+expected))
    # DXT3/BC2 = one 16-byte block per 4x4 pixels. Recompress only blocks that
    # intersect an allowed A-Z source bbox; preserve every other canonical block
    # byte-for-byte. Raw DDS Y is inverse of readable Y for this asset.
    src_payload=bytearray(original[128:])
    enc_payload=encoded[128:]
    blocks_x=readable.width//4
    replaced=0
    for by_raw in range(readable.height//4):
        y_read=readable.height-(by_raw+1)*4
        for bx in range(blocks_x):
            x=bx*4
            if not allowed[y_read:y_read+4,x:x+4].any():
                continue
            off=(by_raw*blocks_x+bx)*16
            src_payload[off:off+16]=enc_payload[off:off+16]
            replaced+=1
    payload=header+bytes(src_payload)
    Path(p).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest(),replaced

header,src,meta=load_dds(source)
sa=np.asarray(src,dtype=np.uint8)
H,W=sa.shape[:2]
alpha=sa[:,:,3]>0

# B207 proves stock base-page selections 10..35 == a..z.
# A135 visual classification proves 66743AA8 sprite_92..sprite_67 == A..Z.
# Therefore letter identity gives an exact physical-key mapping to standard 2-beolsik.
letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
jamo=["ㅁ","ㅠ","ㅊ","ㅇ","ㄷ","ㄹ","ㅎ","ㅗ","ㅑ","ㅓ","ㅏ","ㅣ","ㅡ",
      "ㅜ","ㅐ","ㅔ","ㅂ","ㄱ","ㄴ","ㅅ","ㅕ","ㅍ","ㅈ","ㅌ","ㅛ","ㅋ"]
mapping=[]
for n,(letter,key) in enumerate(zip(letters,jamo)):
    sprite=92-n
    name=f"sprite_{sprite}"
    r=regions.get(name)
    if not r: raise RuntimeError(("missing region",name))
    x,y,w,h=r["rect"]
    if (w,h)!=(96,96): raise RuntimeError(("region size",name,r["rect"]))
    mapping.append((letter,key,name,(x,y,x+w,y+h)))

# Verify the readable source has exactly one non-empty source glyph family in every mapped cell.
source_masks={}
source_bboxes={}
allowed=np.zeros((H,W),bool)
source_text=np.zeros((H,W),bool)
all_style_pixels=[]
all_style_pos=[]
for letter,key,name,cell in mapping:
    x0,y0,x1,y1=cell
    cm=np.zeros((H,W),bool); cm[y0:y1,x0:x1]=alpha[y0:y1,x0:x1]
    ys,xs=np.nonzero(cm)
    if len(xs)<250: raise RuntimeError(("too few source pixels",letter,name,len(xs)))
    bb=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
    if not (x0<=bb[0]<bb[2]<=x1 and y0<=bb[1]<bb[3]<=y1):
        raise RuntimeError(("source bbox escapes cell",letter,bb,cell))
    source_masks[letter]=cm; source_bboxes[letter]=bb
    allowed[bb[1]:bb[3],bb[0]:bb[2]]=True
    source_text|=cm
    pix=sa[cm]
    all_style_pixels.append(pix[:,:3])
    # normalized Y position inside original bbox, for gradient sampling
    yy=np.nonzero(cm)[0]
    all_style_pos.append((yy-bb[1])/max(1,bb[3]-bb[1]-1))

style=np.concatenate(all_style_pixels,axis=0).astype(np.int16)
lum=style.mean(axis=1)
dark=style[lum<=np.percentile(lum,18)]
light=style[lum>=np.percentile(lum,82)]
# Blue/cyan face heuristic; fall back to middle luminance if needed.
face=style[(style[:,2]>=style[:,0]+18)&(style[:,1]>=style[:,0]+8)&(lum>75)]
if len(face)<200:
    face=style[(lum>np.percentile(lum,35))&(lum<np.percentile(lum,78))]
def med(a,default):
    return tuple(int(v) for v in (np.median(a,axis=0) if len(a) else np.array(default)))+(255,)
outer=med(dark,(7,40,86))
rim=med(light,(208,238,252))
face_mid=med(face,(52,151,245))
# Source-faithful vertical blue gradient: brighter/cyan upper face, deeper blue lower face.
face_arr=face
face_l=face_arr.mean(axis=1)
face_top=med(face_arr[face_l>=np.percentile(face_l,58)] if len(face_arr) else [],(91,191,255))
face_bottom=med(face_arr[face_l<=np.percentile(face_l,42)] if len(face_arr) else [],(31,112,226))
palette={"outer":outer,"rim":rim,"face_mid":face_mid,"face_top":face_top,"face_bottom":face_bottom}

def font_path():
    try:
        p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    except Exception:
        p=""
    if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not p or not Path(p).exists(): raise RuntimeError(("font unavailable",p))
    return p
FONT=font_path()

def shear_rgba(im,s=0.18):
    pad=max(6,int(np.ceil(abs(s)*(im.height-1)))+8)
    c=Image.new("RGBA",(im.width+2*pad,im.height),(0,0,0,0)); c.alpha_composite(im,(pad,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1.0,s,0.0,0.0,1.0,0.0),resample=Image.Resampling.BICUBIC)
    bb=o.getchannel("A").getbbox()
    return o.crop(bb) if bb else o

def render_key(text,maxw,maxh):
    # Render a three-layer source-family glyph and fit after readable-orientation shear.
    for fs in range(76,23,-1):
        font=ImageFont.truetype(FONT,fs)
        probe=Image.new("L",(180,150),0); d=ImageDraw.Draw(probe)
        tb=d.textbbox((0,0),text,font=font,stroke_width=5)
        pw=max(32,tb[2]-tb[0]+34); ph=max(32,tb[3]-tb[1]+30)
        base=Image.new("RGBA",(pw,ph),(0,0,0,0))
        pos=(17-tb[0],15-tb[1])
        # Dark outer stroke.
        ImageDraw.Draw(base).text(pos,text,font=font,fill=face_mid,stroke_width=5,stroke_fill=outer)
        # Icy inner rim.
        ImageDraw.Draw(base).text(pos,text,font=font,fill=face_mid,stroke_width=3,stroke_fill=rim)
        # Replace the flat face with a vertical source-blue gradient.
        fillmask=Image.new("L",base.size,0)
        ImageDraw.Draw(fillmask).text(pos,text,font=font,fill=255)
        grad=Image.new("RGBA",base.size,(0,0,0,0)); ga=np.asarray(grad).copy()
        top=np.array(face_top[:3],dtype=np.float32); bot=np.array(face_bottom[:3],dtype=np.float32)
        for yy in range(base.height):
            t=yy/max(1,base.height-1)
            rgb=np.round(top*(1-t)+bot*t).astype(np.uint8)
            ga[yy,:,0:3]=rgb; ga[yy,:,3]=255
        grad=Image.fromarray(ga,"RGBA"); grad.putalpha(fillmask)
        base.alpha_composite(grad)
        bb=base.getchannel("A").getbbox()
        if not bb: continue
        glyph=shear_rgba(base.crop(bb),0.18)
        bb2=glyph.getchannel("A").getbbox()
        if bb2: glyph=glyph.crop(bb2)
        if glyph.width<=maxw-2 and glyph.height<=maxh-2:
            return glyph,fs
    raise RuntimeError(("no fit",text,maxw,maxh))

# Exact clean plate: clear only the source A-Z alpha/effect pixels.
clean_arr=sa.copy(); clean_arr[source_text]=0
clean=Image.fromarray(clean_arr,"RGBA")
if int(np.logical_and(np.asarray(clean.getchannel("A"))>0,source_text).sum())!=0:
    raise RuntimeError("clean source residue")
protected_source=alpha & ~source_text

final=clean.copy()
localized_union=np.zeros((H,W),bool)
rows=[]
for letter,key,name,cell in mapping:
    x0,y0,x1,y1=cell
    ob=source_bboxes[letter]; ow=ob[2]-ob[0]; oh=ob[3]-ob[1]
    glyph,fs=render_key(key,ow,oh)
    px=ob[0]+(ow-glyph.width)//2; py=ob[1]+(oh-glyph.height)//2
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(glyph,(px,py))
    lm=np.asarray(layer.getchannel("A"))>0
    ys,xs=np.nonzero(lm); lb=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
    if not (ob[0]<lb[0] and ob[1]<lb[1] and lb[2]<ob[2] and lb[3]<ob[3]):
        raise RuntimeError(("positive margin/containment",letter,ob,lb))
    if (lb[2]-lb[0])>ow or (lb[3]-lb[1])>oh: raise RuntimeError(("size ceiling",letter,ob,lb))
    ov=int(np.logical_and(lm,protected_source).sum())
    newov=int(np.logical_and(lm,localized_union).sum())
    if ov or newov: raise RuntimeError(("overlap",letter,ov,newov))
    localized_union|=lm
    final.alpha_composite(layer)
    rows.append({
      "letter":letter,"jamo":key,"sprite":name,"cell_rect":list(cell),
      "original_bbox":ob,"localized_bbox":lb,
      "original_size":[ow,oh],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
      "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "protected_overlap_pixels":ov,"localized_overlap_pixels":newov,
      "font_size":fs,"shear_readable":0.18
    })

fa=np.asarray(final,dtype=np.uint8)
changed=np.any(fa!=sa,axis=2)
outside=int(np.logical_and(changed,~allowed).sum())
alpha_out=int(np.logical_and(fa[:,:,3]!=sa[:,:,3],~allowed).sum())
protected_changed=int(np.logical_and(changed,protected_source).sum())
if outside or alpha_out or protected_changed:
    raise RuntimeError(("global scope",outside,alpha_out,protected_changed))

candidate_sha,replaced_blocks=write_dds(header,final,candidate,meta["raw_mode"])
dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta:
    raise RuntimeError(("DDS header/meta mismatch",dh==header,dmeta,meta))
# BC2 is lossy in RGB, so final QA is performed on the decoded candidate,
# not by requiring equality with the pre-compression RGBA render.
da=np.asarray(decoded,dtype=np.uint8)
decoded_changed=np.any(da!=sa,axis=2)
decoded_visible=np.logical_or(da[:,:,3]>0,sa[:,:,3]>0)
decoded_visible_outside=int(np.logical_and.reduce((decoded_changed,~allowed,decoded_visible)).sum())
decoded_alpha_outside=int(np.logical_and(da[:,:,3]!=sa[:,:,3],~allowed).sum())
decoded_protected_visible_changed=int(np.logical_and.reduce((decoded_changed,protected_source,decoded_visible)).sum())
if decoded_visible_outside or decoded_alpha_outside or decoded_protected_visible_changed:
    raise RuntimeError(("decoded compressed scope",decoded_visible_outside,decoded_alpha_outside,decoded_protected_visible_changed))
# Re-measure each localized non-transparent bbox from decoded BC2 pixels.
for row in rows:
    x0,y0,x1,y1=row["original_bbox"]
    sub=da[y0:y1,x0:x1,3]>0
    ys,xs=np.nonzero(sub)
    if not len(xs): raise RuntimeError(("decoded empty jamo",row["letter"]))
    db=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max()+1),y0+int(ys.max()+1)]
    row["decoded_localized_bbox"]=db
    row["decoded_containment"]="PASS" if (x0<=db[0] and y0<=db[1] and db[2]<=x1 and db[3]<=y1) else "FAIL"
    row["decoded_size_ceiling"]="PASS" if (db[2]-db[0]<=x1-x0 and db[3]-db[1]<=y1-y0) else "FAIL"
    if row["decoded_containment"]!="PASS" or row["decoded_size_ceiling"]!="PASS":
        raise RuntimeError(("decoded bbox fail",row))

# Evidence.
Image.fromarray((source_text*255).astype(np.uint8),"L").save(out/"B209_SOURCE_AZ_MASK.png")
Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/"B209_ALLOWED_BBOX_MASK.png")
Image.fromarray((localized_union*255).astype(np.uint8),"L").save(out/"B209_LOCALIZED_JAMO_MASK.png")
clean.save(out/"B209_CLEAN_PLATE.png")
decoded.save(out/"B209_FINAL_READABLE.png")
decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/"B209_FINAL_RAW_MIRROR_Y.png")

def card(label,im,cell,scale=2):
    x0,y0,x1,y1=cell
    rgba=im.crop((x0,y0,x1,y1))
    bg=Image.new("RGBA",rgba.size,(28,38,72,255))
    bg.alpha_composite(rgba)
    v=bg.convert("RGB").resize(((x1-x0)*scale,(y1-y0)*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+28),"white"); c.paste(v,(0,28))
    ImageDraw.Draw(c).text((5,6),label,fill="black")
    return c
cards=[]
for letter,key,name,cell in mapping:
    a=card(f"{letter} -> {key}",src,cell,2)
    b=card(f"{name}",decoded,cell,2)
    pair=Image.new("RGB",(a.width+b.width+4,max(a.height,b.height)),"white"); pair.paste(a,(0,0)); pair.paste(b,(a.width+4,0))
    cards.append(pair)
cols=5; gap=6
cw=max(c.width for c in cards); ch=max(c.height for c in cards)
sheet=Image.new("RGB",(cols*cw+(cols-1)*gap,((len(cards)+cols-1)//cols)*ch+(((len(cards)+cols-1)//cols)-1)*gap),"white")
for i,c in enumerate(cards):
    x=(i%cols)*(cw+gap); y=(i//cols)*(ch+gap); sheet.paste(c,(x,y))
sheet.save(out/"B209_AZ_TO_JAMO_CONTACT.jpg",quality=96)

# Full source/final readable and raw visual evidence.
bg=(64,64,64,255)
def flatten(im):
    x=Image.new("RGBA",im.size,bg); x.alpha_composite(im); return x.convert("RGB")
s1=flatten(src); s2=flatten(decoded)
full=Image.new("RGB",(2048,1054),"white"); full.paste(s1,(0,30)); full.paste(s2,(1024,30))
d=ImageDraw.Draw(full); d.text((5,6),"SOURCE readable",(255,255,255)); d.text((1029,6),"B209 Jamo candidate readable",(255,255,255))
full.save(out/"B209_SOURCE_FINAL_FULL.jpg",quality=96)
rawsrc=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM); rawfin=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw=Image.new("RGB",(2048,1054),"white"); raw.paste(flatten(rawsrc),(0,30)); raw.paste(flatten(rawfin),(1024,30))
d=ImageDraw.Draw(raw); d.text((5,6),"SOURCE raw DDS orientation",(255,255,255)); d.text((1029,6),"B209 raw DDS orientation",(255,255,255))
raw.save(out/"B209_SOURCE_FINAL_RAW.jpg",quality=96)

report={
 "schema_version":1,"run":"B209","role":"B","queue_index":24,"asset":rel,
 "source":{"repo":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","sha256":SOURCE_SHA,"atlas_regions":49},
 "semantic_proof":{
   "runtime":"B207 proves stock base-page selection 10..35 == a..z",
   "visual":"A135 controller review proves sprite_92..sprite_67 == A..Z",
   "binding":"case-insensitive key identity: selection 10+n / a+n -> visual A+n / sprite_(92-n)",
   "keycap_policy":"replace only A-Z visual glyph resources with their standard 2-beolsik base Jamo; digits, punctuation, END and all other textures remain byte/pixel exact"
 },
 "mapping":[{"letter":a,"jamo":b,"sprite":c,"cell_rect":list(d)} for a,b,c,d in mapping],
 "palette_rgba":palette,"font":"Noto Sans CJK KR Black","shear_readable":0.18,
 "candidate_sha256":candidate_sha,"dds_meta":meta,
 "qa":{"rows":rows,"precompression_changed_pixels":int(changed.sum()),"precompression_changed_pixels_outside_original_bboxes":outside,"precompression_alpha_changed_outside_original_bboxes":alpha_out,"precompression_protected_changed_pixels":protected_changed,"clean_source_residue_pixels":0,"dds_header_128_exact":True,"compression":"DXT3/BC2","recompressed_blocks":replaced_blocks,"non_target_compressed_blocks_preserved_exact":True,"decoded_visible_changed_outside_original_bboxes":decoded_visible_outside,"decoded_alpha_changed_outside_original_bboxes":decoded_alpha_outside,"decoded_protected_visible_changed_pixels":decoded_protected_visible_changed,"decoded_containment":"PASS","raw_orientation":"mirror_y","visual_controller_review":"PENDING","runtime_validation":"UNTESTED"},
 "promotion":{"status":"HOLD_INPUT_WIRING_REQUIRED","test_build_selected":False,"reason":"Do not package/promote until B208 composer is wired to the B207 character path and END commits the A141 alias."},
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"B209_JAMO_KEYCAP_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
worker_result.write_text(json.dumps({"role":"B","run":run,"queue_index":24,"asset":rel,"candidate_sha256":candidate_sha,"report":str((out/"B209_JAMO_KEYCAP_REPORT.json").relative_to(repo)),"status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_INPUT_WIRING_HOLD"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B209_DONE",candidate_sha,"palette",palette,"font",FONT)
