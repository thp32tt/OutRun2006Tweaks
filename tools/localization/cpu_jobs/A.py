#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261006-A-PRODUCTION84-IGR012"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b); z=d.split(); m=z[0]
    for q in z[1:]: m=ImageChops.lighter(m,q)
    return bmask(m)
def flatten(im):
    bg=Image.new("RGBA",im.size,(88,88,88,255)); bg.alpha_composite(im); return bg.convert("RGB")
def fontspec():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try:q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
        except Exception:q=""
        if "|" in q:
            p,ix=q.rsplit("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name:return p,int(ix or 0),pat
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Black"],text=True).strip()
    p,ix=q.rsplit("|",1); return p,int(ix or 0),"Noto Sans CJK KR:style=Black"
FONT,FI,FPAT=fontspec()

def shear_mask(mask,k):
    pad=max(6,int(round(abs(k)*mask.height))+8)
    c=Image.new("L",(mask.width+pad*2,mask.height),0); c.paste(mask,(pad,0))
    o=c.transform(c.size,Image.Transform.AFFINE,(1,-k,k*c.height,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=o.getbbox(); return o.crop(bb) if bb else o
def offset_mask(m,dx,dy):
    o=Image.new("L",m.size,0)
    sx0=max(0,-dx); sy0=max(0,-dy); sx1=m.width-max(0,dx); sy1=m.height-max(0,dy)
    if sx1>sx0 and sy1>sy0:o.paste(m.crop((sx0,sy0,sx1,sy1)),(max(0,dx),max(0,dy)))
    return o
def gradient(size,top,bottom):
    w,h=size; a=np.zeros((h,w,4),dtype=np.uint8)
    for y in range(h):
        t=y/max(1,h-1); a[y,:,]=[round(top[i]*(1-t)+bottom[i]*t) for i in range(4)]
    return Image.fromarray(a,"RGBA")

def render_styled(text,kind,maxw,maxh,fs0):
    for fs in range(fs0,17,-1):
        f=ImageFont.truetype(FONT,fs,index=FI)
        dr=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=dr.textbbox((0,0),text,font=f)
        pad=18
        base=Image.new("L",(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2),0)
        ImageDraw.Draw(base).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
        k=0.22 if kind!="badge" else 0.18
        fill=shear_mask(base,k)
        if kind=="white":
            outer=fill.filter(ImageFilter.MaxFilter(11)); rim=fill.filter(ImageFilter.MaxFilter(5))
            sh=offset_mask(outer,5,6)
            w,h=outer.size; layer=Image.new("RGBA",(w,h),(0,0,0,0))
            layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(25,25,31,180)),Image.new("RGBA",(w,h),(0,0,0,0)),sh))
            layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(72,72,78,255)),Image.new("RGBA",(w,h),(0,0,0,0)),outer))
            layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(230,230,228,255)),Image.new("RGBA",(w,h),(0,0,0,0)),rim))
            layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(250,250,246,255)),Image.new("RGBA",(w,h),(0,0,0,0)),fill))
        elif kind=="yellow":
            outer=fill.filter(ImageFilter.MaxFilter(13)); rim=fill.filter(ImageFilter.MaxFilter(7))
            sh=offset_mask(outer,5,6)
            w,h=outer.size; layer=Image.new("RGBA",(w,h),(0,0,0,0))
            layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(8,16,48,205)),Image.new("RGBA",(w,h),(0,0,0,0)),sh))
            layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(14,30,82,255)),Image.new("RGBA",(w,h),(0,0,0,0)),outer))
            layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(250,248,235,255)),Image.new("RGBA",(w,h),(0,0,0,0)),rim))
            layer.alpha_composite(Image.composite(gradient((w,h),(255,248,180,255),(230,176,55,255)),Image.new("RGBA",(w,h),(0,0,0,0)),fill))
        else:
            outer=fill.filter(ImageFilter.MaxFilter(7)); sh=offset_mask(outer,3,3)
            w,h=outer.size; layer=Image.new("RGBA",(w,h),(0,0,0,0))
            layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(160,42,12,170)),Image.new("RGBA",(w,h),(0,0,0,0)),sh))
            layer.alpha_composite(Image.composite(Image.new("RGBA",(w,h),(255,205,150,255)),Image.new("RGBA",(w,h),(0,0,0,0)),outer))
            layer.alpha_composite(Image.composite(gradient((w,h),(255,255,247,255),(255,230,170,255)),Image.new("RGBA",(w,h),(0,0,0,0)),fill))
        lb=layer.getchannel("A").getbbox()
        if not lb: continue
        layer=layer.crop(lb)
        if layer.width<=maxw and layer.height<=maxh:return layer,fs,k
    raise RuntimeError(("cannot fit",text,kind,maxw,maxh))

# ----------------------------------------------------------------------
# IGR-012 exact mixed-graphics mapping:
#   START badge art -> queue 63 / 48DEBE77
#   OUTRUN MILES banners -> queue 60 / A064FDFC
# Both are baked graphics; dynamic numeric meter is protected runtime content.
# ----------------------------------------------------------------------

# 1) 48DEBE77: remove the old rectangular plate reconstruction and rebuild only
# the three START/GOAL text regions on canonical source-derived badge artwork.
p48=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_loading_cvt_Exst/48DEBE77_512x512.dds"
s48=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_loading_cvt_Exst/48DEBE77_512x512.dds"
if sha(p48)!="fa0f6e27ebabfd81d67ecea3ec204361046d650dc6cf8ab00c1b6580ee58aca0": raise RuntimeError(("48 candidate drift",sha(p48)))
if sha(s48)!="5f6cc66875fd2c03678f7c893ae242eacd0bda6e56ee8d0b2a56e7578895e635": raise RuntimeError(("48 source drift",sha(s48)))
sb=s48.read_bytes(); cb=p48.read_bytes()
Hs,Ws,ps,ds,ms=struct.unpack_from("<5I",sb,12); H,W,pitch,depth,mips=struct.unpack_from("<5I",cb,12)
if (Ws,Hs)!=(512,512) or (W,H)!=(2048,2048): raise RuntimeError("48 dimensions")
src48_raw=Image.frombytes("RGBA",(Ws,Hs),sb[128:],"raw","BGRA"); src48=src48_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src48_4=src48.resize((W,H),Image.Resampling.LANCZOS)
old48_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","BGRA"); old48=old48_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
final48=old48.copy()
records=[
 ("start_top","출발",(104,492,368,576),20,10,70),
 ("start_bottom","출발",(104,1532,368,1604),20,8,64),
 ("goal","골",(1632,20,1820,68),18,6,48),
]
cells_mask=Image.new("L",(W,H),0); source48_face_union=Image.new("L",(W,H),0); source48_text_union=Image.new("L",(W,H),0); new48_union=Image.new("L",(W,H),0); rec48=[]
clean48=old48.copy()
for key,txt,cell,ix,iy,fs0 in records:
    x0,y0,x1,y1=cell; ImageDraw.Draw(cells_mask).rectangle((x0,y0,x1-1,y1-1),fill=255)
    base=src48_4.crop(cell).copy(); a=np.array(base)
    h,w=a.shape[:2]
    roi=np.zeros((h,w),bool); roi[iy:h-iy,ix:w-ix]=True
    bright=(a[:,:,0]>170)&(a[:,:,1]>135)&(a[:,:,2]>85)&(a[:,:,3]>0)&roi
    source48_face_union.paste(Image.fromarray((bright*255).astype(np.uint8),"L"),(x0,y0))
    # Source lettering includes cream face + glow; expand the measured bright face.
    mask=ndimage.binary_dilation(bright,iterations=5)&roi
    if mask.sum()<150: raise RuntimeError(("48 source text mask too small",key,int(mask.sum())))
    ys,xs=np.where(mask); sbbox=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]
    source48_text_union.paste(Image.fromarray((mask*255).astype(np.uint8),"L"),(x0,y0))
    ca=a.copy()
    red=(a[:,:,0]>120)&(a[:,:,0]>a[:,:,1]*1.25)&(a[:,:,0]>a[:,:,2]*1.25)&(a[:,:,3]>0)&(~mask)
    rowcols={}
    for yy in range(h):
        q=a[yy][red[yy]]
        if len(q): rowcols[yy]=np.median(q,axis=0).astype(np.uint8)
    known=sorted(rowcols)
    if not known: raise RuntimeError(("no red samples",key))
    for yy in np.unique(ys):
        near=min(known,key=lambda z:abs(z-int(yy))); ca[yy,mask[yy]]=rowcols[near]
    clean_cell=Image.fromarray(ca,"RGBA")
    clean48.paste(clean_cell,(x0,y0)); final48.paste(clean_cell,(x0,y0))
    maxw=sbbox[2]-sbbox[0]-4; maxh=sbbox[3]-sbbox[1]-4
    layer,fs,k=render_styled(txt,"badge",maxw,maxh,fs0)
    tx=sbbox[0]+(sbbox[2]-sbbox[0]-layer.width)//2
    ty=sbbox[1]+(sbbox[3]-sbbox[1]-layer.height)//2
    lm=bmask(layer.getchannel("A")); tm=Image.new("L",(W,H),0); tm.paste(lm,(tx,ty))
    lb=list(tm.getbbox() or ())
    if not lb or not(lb[0]>sbbox[0] and lb[1]>sbbox[1] and lb[2]<sbbox[2] and lb[3]<sbbox[3]): raise RuntimeError(("48 bbox",key,sbbox,lb))
    final48.paste(layer,(tx,ty),lm); new48_union=ImageChops.lighter(new48_union,tm)
    rec48.append({"key":key,"source":"START" if "start" in key else "GOAL","korean":txt,"source_effect_bbox":sbbox,
                  "localized_bbox":lb,"source_size":[sbbox[2]-sbbox[0],sbbox[3]-sbbox[1]],
                  "localized_size":[lb[2]-lb[0],lb[3]-lb[1]],"delta_left":lb[0]-sbbox[0],"delta_right":sbbox[2]-lb[2],
                  "delta_top":lb[1]-sbbox[1],"delta_bottom":sbbox[3]-lb[3],"containment":"PASS","size_ceiling":"PASS",
                  "positive_margin":"PASS","font":FPAT,"font_size":fs,"shear":k})
# Strict change scope vs prior candidate.
diff48=dmask(old48,final48); out48=count(ImageChops.multiply(diff48,ImageOps.invert(cells_mask)))
if out48: raise RuntimeError(("48 outside",out48))
# Clean-plate source-script gate: every detected canonical cream-face pixel in
# the inset text mask must change. Dilation fringe is excluded because it intentionally
# contains source-red background; badge borders are outside the inset ROI.
same48_clean=ImageOps.invert(dmask(src48_4,clean48))
res48=count(ImageChops.multiply(source48_face_union,same48_clean))
if res48: raise RuntimeError(("48 clean source-face residue",res48))
raw48=final48.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
p48.write_bytes(cb[:128]+raw48.tobytes("raw","BGRA")); sha48=sha(p48)
dec48_raw=Image.frombytes("RGBA",(W,H),p48.read_bytes()[128:],"raw","BGRA"); dec48=dec48_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec48,final48).getbbox() is not None: raise RuntimeError("48 roundtrip")

# 2) A064FDFC: rebuild both OUTRUN MILES labels smaller/lower-risk and source-slanted.
pa=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
sa=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
clp=repo/"localization/graphics/role_B/20261004-B-RECOVERY02/A064FDFC_CLEAN_PLATE.png"
if sha(pa)!="f822c0727e8ce9c8d0b801fe5a39dd870c43a30d872819c42829040e14474665": raise RuntimeError(("A064 candidate drift",sha(pa)))
if sha(sa)!="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc": raise RuntimeError(("A064 source drift",sha(sa)))
ab=pa.read_bytes(); asb=sa.read_bytes(); H2,W2,p2,d2,m2=struct.unpack_from("<5I",ab,12)
oldA_raw=Image.frombytes("RGBA",(W2,H2),ab[128:],"raw","RGBA"); oldA=oldA_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
srcA_raw=Image.frombytes("RGBA",(W2,H2),asb[128:],"raw","RGBA"); srcA=srcA_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cleanA=Image.open(clp).convert("RGBA")
if cleanA.size!=oldA.size: raise RuntimeError("A064 clean size")
finalA=oldA.copy(); allowedA=Image.new("L",(W2,H2),0)
a_rows=[
 {"key":"outrun_miles_white","source":"OUTRUN MILES!","korean":"아웃런 마일!","source_bbox":(1090,245,1930,385),
  "old_bbox":(1241,245,1913,370),"protect":(1506,123,2024,247),"safe":(1096,252,1924,358),"kind":"white","fs":92},
 {"key":"outrun_miles","source":"OUTRUN MILES:","korean":"아웃런 마일:","source_bbox":(2081,250,2860,370),
  "old_bbox":(2197,253,2742,370),"protect":(2281,365,2943,536),"safe":(2087,256,2854,358),"kind":"yellow","fs":84},
]
newA_union=Image.new("L",(W2,H2),0); recA=[]
for r in a_rows:
    sx0,sy0,sx1,sy1=r["source_bbox"]; ImageDraw.Draw(allowedA).rectangle((sx0,sy0,sx1-1,sy1-1),fill=255)
    ox0,oy0,ox1,oy1=r["old_bbox"]
    od=dmask(oldA.crop((ox0,oy0,ox1,oy1)),cleanA.crop((ox0,oy0,ox1,oy1)))
    em=Image.new("L",(W2,H2),0); em.paste(od,(ox0,oy0))
    px0,py0,px1,py1=r["protect"]; pd=Image.new("L",(W2,H2),0); ImageDraw.Draw(pd).rectangle((px0,py0,px1-1,py1-1),fill=255)
    em=ImageChops.multiply(em,ImageOps.invert(pd))
    finalA.paste(cleanA,(0,0),em)
    ax0,ay0,ax1,ay1=r["safe"]
    layer,fs,k=render_styled(r["korean"],r["kind"],ax1-ax0,ay1-ay0,r["fs"])
    tx=ax0; ty=ay0+(ay1-ay0-layer.height)//2
    lm=bmask(layer.getchannel("A")); tm=Image.new("L",(W2,H2),0); tm.paste(lm,(tx,ty)); lb=list(tm.getbbox() or ())
    if not lb or not(lb[0]>sx0 and lb[1]>sy0 and lb[2]<sx1 and lb[3]<sy1): raise RuntimeError(("A064 bbox",r["key"],lb))
    # Hard 2px geometric separation from the adjacent preserved localized row.
    if not (lb[3]+2 <= py0 or lb[1] >= py1+2 or lb[2]+2 <= px0 or lb[0] >= px1+2):
        raise RuntimeError(("A064 neighbor gap",r["key"],lb,r["protect"]))
    finalA.paste(layer,(tx,ty),lm); newA_union=ImageChops.lighter(newA_union,tm)
    recA.append({"key":r["key"],"source":r["source"],"korean":r["korean"],"source_effect_bbox":list(r["source_bbox"]),
      "localized_bbox":lb,"source_size":[sx1-sx0,sy1-sy0],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
      "delta_left":lb[0]-sx0,"delta_right":sx1-lb[2],"delta_top":lb[1]-sy0,"delta_bottom":sy1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","neighbor_positive_separation_px":2,
      "font":FPAT,"font_size":fs,"shear":k,"style":r["kind"]})
diffA=dmask(oldA,finalA); outA=count(ImageChops.multiply(diffA,ImageOps.invert(allowedA)))
alphaA=bmask(ImageChops.difference(oldA.getchannel("A"),finalA.getchannel("A"))); alphaOutA=count(ImageChops.multiply(alphaA,ImageOps.invert(allowedA)))
if outA or alphaOutA: raise RuntimeError(("A064 outside",outA,alphaOutA))
rawA=finalA.transpose(Image.Transpose.FLIP_TOP_BOTTOM); pa.write_bytes(ab[:128]+rawA.tobytes("raw","RGBA")); shaA=sha(pa)
decA_raw=Image.frombytes("RGBA",(W2,H2),pa.read_bytes()[128:],"raw","RGBA"); decA=decA_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decA,finalA).getbbox() is not None: raise RuntimeError("A064 roundtrip")

# Evidence.
# 48 badge contacts SOURCE4 | OLD | CLEAN | FINAL
cards=[]
for r in rec48:
    x0,y0,x1,y1=r["source_effect_bbox"]; pad=18; box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    ims=[flatten(z.crop(box)) for z in (src48_4,old48,clean48,dec48)]
    row=Image.new("RGB",(sum(i.width for i in ims)+24,max(i.height for i in ims)+28),(228,228,228)); x=0; d=ImageDraw.Draw(row)
    d.text((4,4),r["key"]+" SOURCE | OLD | CLEAN | A84",fill=(0,0,0))
    for im in ims: row.paste(im,(x,28)); x+=im.width+8
    cards.append(row)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+4 for c in cards)),(230,230,230)); y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height+4
sheet.save(out/"A84_48DEBE77_BADGE_CONTACTS.jpg",quality=95)

# A064 contacts SOURCE | OLD | CLEAN | FINAL.
cards=[]
for r in recA:
    x0,y0,x1,y1=r["source_effect_bbox"]; pad=20; box=(max(0,x0-pad),max(0,y0-pad),min(W2,x1+pad),min(H2,y1+pad))
    ims=[flatten(z.crop(box)) for z in (srcA,oldA,cleanA,decA)]
    sc=[]
    for im in ims:
        q=min(1.0,220/max(1,im.height),440/max(1,im.width)); sc.append(im.resize((max(1,int(im.width*q)),max(1,int(im.height*q))),Image.Resampling.LANCZOS) if q<1 else im)
    row=Image.new("RGB",(sum(i.width for i in sc)+24,max(i.height for i in sc)+28),(228,228,228)); x=0; d=ImageDraw.Draw(row)
    d.text((4,4),r["key"]+" SOURCE | OLD | CLEAN | A84",fill=(0,0,0))
    for im in sc: row.paste(im,(x,28)); x+=im.width+8
    cards.append(row)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+4 for c in cards)),(230,230,230)); y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height+4
sheet.save(out/"A84_A064_OUTRUN_MILES_CONTACTS.jpg",quality=95)

# Raw orientation proofs.
flatten(dec48_raw).resize((768,768),Image.Resampling.LANCZOS).save(out/"A84_48DEBE77_RAW_MIRROR_Y.jpg",quality=94)
flatten(decA_raw).resize((1024,512),Image.Resampling.LANCZOS).save(out/"A84_A064_RAW_MIRROR_Y.jpg",quality=94)

report={"schema_version":1,"role":"A","run":run,"regression":"IGR-012","screenshot":"스크린샷(157).png",
 "mapping":{"status":"EXACT_HIGH_CONFIDENCE_MULTI_ASSET","primary_queue_index":60,
   "primary_asset":"textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds",
   "secondary_queue_index":63,"secondary_asset":"textures/load/spr_sprani_loading_cvt_Exst/48DEBE77_512x512.dds",
   "basis":"A064 contains both baked OUTRUN MILES variants visible in the reported banner; 48DEBE77 contains the paired START/GOAL route badge art. Dynamic numeric meter is protected runtime content; no runtime-text edit is made."},
 "assets":{"A064FDFC":{"source_sha256":"6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc",
   "input_candidate_sha256":"f822c0727e8ce9c8d0b801fe5a39dd870c43a30d872819c42829040e14474665","candidate_sha256":shaA,
   "rows":recA,"changes_outside_two_source_bboxes":outA,"alpha_changes_outside_two_source_bboxes":alphaOutA,
   "header_128_exact":pa.read_bytes()[:128]==ab[:128],"raw_orientation":"mirror_y"},
  "48DEBE77":{"source_sha256":"5f6cc66875fd2c03678f7c893ae242eacd0bda6e56ee8d0b2a56e7578895e635",
   "input_candidate_sha256":"fa0f6e27ebabfd81d67ecea3ec204361046d650dc6cf8ab00c1b6580ee58aca0","candidate_sha256":sha48,
   "rows":rec48,"changes_outside_three_badge_cells":out48,"source_face_residue_in_clean_plate":res48,
   "header_128_preserved_from_2048_candidate":p48.read_bytes()[:128]==cb[:128],"raw_orientation":"mirror_y",
   "construction":"canonical stock source artwork resampled 4x special-case baseline; fresh native-resolution Korean glyphs; no old Korean raster reuse"}},
 "producer_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "status":"A84_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA"}
(out/"A84_IGR012_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A84_IGR012.json").write_text(json.dumps({"run":run,"regression":"IGR-012","assets":["A064FDFC","48DEBE77"],
 "candidate_sha256":{"A064FDFC":shaA,"48DEBE77":sha48},"bbox_size_margin":{"A064FDFC":"2/2 PASS","48DEBE77":"3/3 PASS"},
 "outside":{"A064FDFC":outA,"48DEBE77":out48},"source_face_residue_48_clean_plate":res48,
 "worker_status":report["status"],"runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "report":str((out/"A84_IGR012_REPORT.json").relative_to(repo))},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"A064FDFC":shaA,"48DEBE77":sha48,"A064_rows":recA,"badge_rows":rec48,
                  "outside":{"A064":outA,"A064_alpha":alphaOutA,"48":out48},"source_residue_48":res48},ensure_ascii=False))
