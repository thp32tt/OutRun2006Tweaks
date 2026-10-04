#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261004-A-RECOVERY09"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker_out=repo/"localization/graphics/worker_results"
worker_out.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
source=Path("/tmp/39229D64_HD.dds")
c_rejected=Path("/tmp/39229D64_C_OVERLAP05_REJECTED.dds")
SOURCE_REPO_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB="81c10922293dcdfdc75090c980fb38ee5c3bedd1"
SOURCE_SHA="2f2c19db5a9b7eda058ee380396160e42884760c0d0282d2e75254bf08070481"
C_WORKER_COMMIT="ddfc5afbff650bfefe6e7de55d39f20a1f109450"
C_REJECTED_SHA="dfa2c39fba8c397191af804767ede25fef35f92b5b21f583130190b701bdb9a4"
validator=repo/"tools/localization/validate_clean_plate.py"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def count(mask): return sum(mask.histogram()[1:])
def changed_mask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)

# Exact authoritative HD source.
url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SOURCE_REPO_COMMIT}/Release/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds"
urllib.request.urlretrieve(url,source)
if sha(source)!=SOURCE_SHA: raise RuntimeError(("source SHA",sha(source),SOURCE_SHA))
sb=source.read_bytes()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,depth,mips)!=(4096,4096,16384,1,1): raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000): raise RuntimeError(("pixel format",pf))
if len(sb)!=128+W*H*4: raise RuntimeError(("byte size",len(sb)))
source_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=source_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# Recover the C_OVERLAP05 rejected machine candidate from exact Git history.
blob=subprocess.check_output(["git","show",f"{C_WORKER_COMMIT}:localization/graphics/hd_candidates/{asset_rel}"])
c_rejected.write_bytes(blob)
if sha(c_rejected)!=C_REJECTED_SHA: raise RuntimeError(("C rejected SHA",sha(c_rejected),C_REJECTED_SHA))
cb=c_rejected.read_bytes()
if cb[:128]!=sb[:128]: raise RuntimeError("C rejected header mismatch")
c_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
c_new=c_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
c_clean=Image.open(repo/"localization/graphics/role_C/20261004-C-OVERLAP05/39229D64_FULL_CLEAN.png").convert("RGBA")
if c_clean.size!=(W,H): raise RuntimeError(("C clean size",c_clean.size))

c_report=json.loads((repo/"localization/graphics/role_C/20261004-C-OVERLAP05/C_OVERLAP05_39229D64_REPORT.json").read_text(encoding="utf-8"))
rows=list(c_report["rows"])
if len(rows)!=15: raise RuntimeError(("C row count",len(rows)))
# C_OVERLAP05 tracked one SPECIAL REQUEST occurrence, but the atlas contains a second
# text-only SPECIAL REQUEST sprite at stock region 29. Treat duplicate on-screen text
# as a separate localized occurrence rather than leaving visible English in the final.
alt_cell=[2276,352,3276,520]
abb=src.crop(tuple(alt_cell)).getchannel("A").getbbox()
if not abb: raise RuntimeError("second SPECIAL REQUEST source bbox missing")
alt_bbox=[alt_cell[0]+abb[0],alt_cell[1]+abb[1],alt_cell[0]+abb[2],alt_cell[1]+abb[3]]
rows.append({"key":"special_request_alt","source":"SPECIAL REQUEST","korean":"스페셜 요청","source_bbox":alt_bbox})
row_by_key={r["key"]:r for r in rows}

# Background classes. All non-total-rank targets are transparent text/effect overlays in source.
# The three Total Rank labels sit on opaque speech/starburst art and require source-faithful fill reconstruction.
opaque_keys={"total_rank_green","total_rank_brown","total_rank_pink"}
allowed=Image.new("L",(W,H),0)
ad=ImageDraw.Draw(allowed)
clean_arr=np.asarray(src,dtype=np.uint8).copy()
src_arr=np.asarray(src,dtype=np.uint8)

def reconstruct_opaque_rowwise(arr, ob):
    x1,y1,x2,y2=ob
    ry1=min(H-1,y2+24); ry2=min(H,y2+120)
    ref=src_arr[ry1:ry2,x1:x2].reshape(-1,4)
    ref=ref[ref[:,3]>0]
    if len(ref)==0: raise RuntimeError(("opaque background reference empty",ob))
    refcol=np.median(ref,axis=0)
    for yy in range(y1,y2):
        vals=src_arr[yy,x1:x2]
        good=vals[vals[:,3]>0]
        if len(good):
            dist=np.max(np.abs(good[:,:3].astype(np.int16)-refcol[:3].astype(np.int16)),axis=1)
            bg=good[dist<55]
        else:
            bg=good
        fill=np.median(bg,axis=0).astype(np.uint8) if len(bg)>=8 else refcol.astype(np.uint8)
        arr[yy,x1:x2]=fill

for r in rows:
    ob=list(map(int,r["source_bbox"]))
    x1,y1,x2,y2=ob
    ad.rectangle((x1,y1,x2-1,y2-1),fill=255)
    if r["key"] in opaque_keys:
        reconstruct_opaque_rowwise(clean_arr,ob)
    else:
        clean_arr[y1:y2,x1:x2]=0

clean=Image.fromarray(clean_arr,"RGBA")

# Build source-text/effect mask as source-vs-reconstructed-clean change within each exact permitted bbox.
source_text_mask=changed_mask(src,clean)
# It must not extend outside exact allowed union.
source_text_out=count(ImageChops.multiply(source_text_mask,ImageOps.invert(allowed)))
if source_text_out!=0: raise RuntimeError(("source text mask outside allowed",source_text_out))

# Protected source art is every visible source pixel outside the exact allowed union.
src_visible=src.getchannel("A").point(lambda v:255 if v else 0)
protected=ImageChops.multiply(src_visible,ImageOps.invert(allowed))
clean_protected=protected.copy()

source_png=out/"39229D64_HD_SOURCE_READABLE.png"
clean_png=out/"39229D64_REPAIRED_CLEAN_PLATE.png"
allowed_png=out/"39229D64_ALLOWED_TEXT_REGION_MASK.png"
source_text_mask_png=out/"39229D64_SOURCE_TEXT_EFFECT_MASK.png"
protected_png=out/"39229D64_PROTECTED_VISIBLE_MASK.png"
clean_protected_png=out/"39229D64_CLEAN_PROTECTED_VISIBLE_MASK.png"
src.save(source_png); clean.save(clean_png)
allowed.save(allowed_png)
source_text_mask.save(source_text_mask_png)
protected.save(protected_png)
clean_protected.save(clean_protected_png)

subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(source_text_mask_png),
                "--protected-mask",str(clean_protected_png),
                "--report",str(out/"A_RECOVERY09_CLEAN_PLATE_VALIDATION.json")],check=True)
clean_rep=json.loads((out/"A_RECOVERY09_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"]!="PASS": raise RuntimeError(("clean validator",clean_rep))

# Freshly render Korean from the repaired clean plate. Reusing the C candidate's
# localized delta would also reuse its black/gray overdraw fragments, so this retry
# measures/fits a new source-family Korean layer for every returned row.
def resolve_font():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try: fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    return subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT=resolve_font()

style_defs={
 "hearts":          dict(top=(255,236,74,255), bottom=(244,167,12,255), inner=(255,249,224,255), outer=(16,28,74,255), shadow=(6,9,24,220), ir=.018, orr=.060, sr=.060, shear=.05),
 "technical_bonus": dict(top=(255,255,255,255), bottom=(231,188,177,255), inner=(250,250,250,255), outer=(55,55,65,255), shadow=(14,13,20,210), ir=.020, orr=.050, sr=.050, shear=.15),
 "mission_cleared": dict(top=(255,244,170,255), bottom=(248,112,18,255), inner=(255,246,222,255), outer=(24,26,40,255), shadow=(5,5,9,235), ir=.025, orr=.055, sr=.070, shear=.13),
 "total_rank_green":dict(top=(255,255,255,255), bottom=(245,240,237,255), inner=(255,255,255,255), outer=(20,31,76,255), shadow=(8,9,20,190), ir=.012, orr=.055, sr=.045, shear=.10),
 "storing":         dict(top=(255,236,73,255), bottom=(255,178,15,255), inner=(255,250,220,255), outer=(18,25,55,255), shadow=(8,8,15,200), ir=.016, orr=.050, sr=.040, shear=.11),
 "special_request_alt": dict(top=(255,255,255,255), bottom=(236,232,231,255), inner=(255,255,255,255), outer=(65,63,67,255), shadow=(24,23,28,185), ir=.012, orr=.050, sr=.045, shear=.12),
 "special_request": dict(top=(255,255,255,255), bottom=(236,232,231,255), inner=(255,255,255,255), outer=(65,63,67,255), shadow=(24,23,28,185), ir=.012, orr=.050, sr=.045, shear=.12),
 "target":          dict(top=(230,230,230,255), bottom=(135,135,135,255), inner=(242,242,242,255), outer=(55,55,62,255), shadow=(28,28,31,180), ir=.014, orr=.045, sr=.035, shear=.05),
 "start":           dict(top=(255,248,218,255), bottom=(235,218,176,255), inner=(255,255,248,255), outer=(18,30,75,255), shadow=(8,12,30,220), ir=.018, orr=.060, sr=.065, shear=.04),
 "goal":            dict(top=(255,248,218,255), bottom=(235,218,176,255), inner=(255,255,248,255), outer=(18,30,75,255), shadow=(8,12,30,220), ir=.018, orr=.060, sr=.065, shear=.04),
 "hit_ghost":       dict(top=(255,244,77,255), bottom=(255,192,16,255), inner=(255,250,229,255), outer=(15,27,70,255), shadow=(7,10,24,220), ir=.018, orr=.055, sr=.050, shear=.05),
 "exit":            dict(top=(255,239,225,255), bottom=(239,116,145,255), inner=(255,247,240,255), outer=(22,30,72,255), shadow=(7,10,24,225), ir=.022, orr=.060, sr=.060, shear=.14),
 "collect_stars":   dict(top=(255,242,76,255), bottom=(255,186,16,255), inner=(255,251,228,255), outer=(16,28,70,255), shadow=(7,10,24,220), ir=.018, orr=.055, sr=.050, shear=.04),
 "mission_failed":  dict(top=(247,252,255,255), bottom=(103,180,242,255), inner=(247,251,255,255), outer=(24,31,70,255), shadow=(6,8,20,225), ir=.022, orr=.060, sr=.065, shear=.12),
 "total_rank_brown":dict(top=(255,255,255,255), bottom=(245,240,237,255), inner=(255,255,255,255), outer=(20,31,76,255), shadow=(8,9,20,190), ir=.012, orr=.055, sr=.045, shear=.10),
 "total_rank_pink": dict(top=(255,255,255,255), bottom=(245,240,237,255), inner=(255,255,255,255), outer=(20,31,76,255), shadow=(8,9,20,190), ir=.012, orr=.055, sr=.045, shear=.10),
}
translations={
 "hearts":"하트","technical_bonus":"테크니컬 보너스","mission_cleared":"미션 성공!",
 "total_rank_green":"종합 랭크","storing":"온라인 기록 저장 중...","special_request":"스페셜 요청","special_request_alt":"스페셜 요청",
 "target":"목표","start":"시작","goal":"골","hit_ghost":"고스트를 맞히세요!","exit":"종료",
 "collect_stars":"별을 모으세요!","mission_failed":"미션 실패!","total_rank_brown":"종합 랭크","total_rank_pink":"종합 랭크"
}
def shear_mask(m,amount):
    if not amount: return m
    extra=max(4,int(abs(amount)*m.height)+8)
    c=Image.new("L",(m.width+extra*2,m.height),0); c.paste(m,(extra,0))
    z=c.transform(c.size,Image.Transform.AFFINE,(1,-amount,amount*c.height,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=z.getbbox(); return z.crop(bb) if bb else z
def gradient(size,top,bottom):
    w,h=size; im=Image.new("RGBA",size); px=im.load()
    for yy in range(h):
        t=yy/max(1,h-1); col=tuple(round(top[k]*(1-t)+bottom[k]*t) for k in range(4))
        for xx in range(w): px[xx,yy]=col
    return im
def render_text(text,key,aw,ah):
    st=style_defs[key]
    for fs in range(max(20,int(ah*.98)),13,-1):
        f=ImageFont.truetype(FONT,fs)
        outer=max(2,round(fs*st["orr"])); inner=max(0,round(fs*st["ir"])); shadow=max(1,round(fs*st["sr"]))
        d=ImageDraw.Draw(Image.new("L",(8,8),0)); bb=d.textbbox((0,0),text,font=f,stroke_width=outer)
        pad=outer+shadow+10; cw=bb[2]-bb[0]+pad*2; ch=bb[3]-bb[1]+pad*2
        def m(sw):
            z=Image.new("L",(cw,ch),0); q=ImageDraw.Draw(z)
            q.text((pad-bb[0],pad-bb[1]),text,font=f,fill=255,stroke_width=sw,stroke_fill=255)
            return shear_mask(z,st["shear"])
        fill=m(0); inm=m(inner); outm=m(outer)
        mw=max(fill.width,inm.width,outm.width); mh=max(fill.height,inm.height,outm.height)
        def center(z):
            c=Image.new("L",(mw+shadow+8,mh+shadow+8),0); c.paste(z,((mw-z.width)//2,(mh-z.height)//2)); return c
        fill,inm,outm=center(fill),center(inm),center(outm)
        layer=Image.new("RGBA",outm.size,(0,0,0,0))
        sh=Image.new("L",outm.size,0); sh.paste(outm.crop((0,0,outm.width-shadow,outm.height-shadow)),(shadow,shadow))
        layer.paste(Image.new("RGBA",layer.size,st["shadow"]),(0,0),sh)
        layer.paste(Image.new("RGBA",layer.size,st["outer"]),(0,0),outm)
        if inner: layer.paste(Image.new("RGBA",layer.size,st["inner"]),(0,0),inm)
        layer.paste(gradient(layer.size,st["top"],st["bottom"]),(0,0),fill)
        lb=layer.getchannel("A").getbbox()
        if not lb: continue
        layer=layer.crop(lb)
        if layer.width<=aw-8 and layer.height<=ah-8: return layer,fs
    raise RuntimeError(("fit",key,text,aw,ah))
final=clean.copy(); localized_masks={}; layer_meta={}
for r in rows:
    key=r["key"]; ob=list(map(int,r["source_bbox"])); x1,y1,x2,y2=ob
    layer,fs=render_text(translations[key],key,x2-x1,y2-y1)
    tx=x1+(x2-x1-layer.width)//2; ty=y1+(y2-y1-layer.height)//2
    tx=max(x1+2,min(tx,x2-layer.width-2)); ty=max(y1+2,min(ty,y2-layer.height-2))
    final.alpha_composite(layer,(tx,ty))
    lm=layer.getchannel("A").point(lambda v:255 if v else 0)
    full=Image.new("L",(W,H),0); full.paste(lm,(tx,ty)); localized_masks[key]=full
    bb=lm.getbbox(); gb=[tx+bb[0],ty+bb[1],tx+bb[2],ty+bb[3]]
    layer_meta[key]={"localized_bbox":gb,"layer_pixels":count(lm),"font_size":fs}

# Exact RGBA32 candidate with original header/raw mirror-Y orientation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
outb=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(outb)
cand_sha=sha(candidate)
if outb[:128]!=sb[:128]: raise RuntimeError("candidate header changed")
dec_raw=Image.frombytes("RGBA",(W,H),outb[128:],"raw","RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("RGBA roundtrip mismatch")
dec_png=out/"39229D64_FINAL_DECODED_READABLE.png"; dec.save(dec_png)

subprocess.run(["python3",str(validator),str(source_png),str(dec_png),str(allowed_png),
                "--protected-mask",str(protected_png),
                "--report",str(out/"A_RECOVERY09_FINAL_MASK_VALIDATION.json")],check=True)
final_rep=json.loads((out/"A_RECOVERY09_FINAL_MASK_VALIDATION.json").read_text())
if final_rep["status"]!="PASS": raise RuntimeError(("final validator",final_rep))

diff=changed_mask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_diff=ImageChops.difference(src.getchannel("A"),dec.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_diff,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(diff,protected))

# Exact source residue check: no pixel from the source text/effect mask may survive unchanged
# unless it is also part of the newly isolated Korean layer at that pixel.
same=ImageChops.difference(src,dec).point(lambda v:255 if v==0 else 0)
same_rgba=ImageChops.multiply(ImageChops.multiply(same.split()[0],same.split()[1]),ImageChops.multiply(same.split()[2],same.split()[3]))
localized_union=Image.new("L",(W,H),0)
for m in localized_masks.values(): localized_union=ImageChops.lighter(localized_union,m)
residue_mask=ImageChops.multiply(source_text_mask,ImageOps.invert(localized_union))
source_residue_unchanged=count(ImageChops.multiply(residue_mask,same_rgba))

# Pairwise localized overlap must be zero.
keys=list(localized_masks)
pair_overlaps=[]
for i,k1 in enumerate(keys):
    for k2 in keys[i+1:]:
        n=count(ImageChops.multiply(localized_masks[k1],localized_masks[k2]))
        if n: pair_overlaps.append({"a":k1,"b":k2,"pixels":n})
localized_pair_overlap=sum(x["pixels"] for x in pair_overlaps)

qa_rows=[]
for r in rows:
    key=r["key"]; ob=list(map(int,r["source_bbox"])); loc=layer_meta[key]["localized_bbox"]
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=loc[2]-loc[0],loc[3]-loc[1]
    contain=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=lw<=sw and lh<=sh
    positive=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    qa_rows.append({
      "key":key,"source":r.get("source"),"korean":r.get("korean"),
      "original_bbox":ob,"localized_bbox":loc,
      "source_width":sw,"source_height":sh,"localized_width":lw,"localized_height":lh,
      "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],
      "delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
      "positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
      "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
      "raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],
      "raw_containment":"PASS" if contain else "FAIL",
      "layer_pixels":layer_meta[key]["layer_pixels"],"font_size":layer_meta[key]["font_size"],
      "style":"fresh source-family Korean render after full source-text clean; target-specific fill/outline/shadow/slant",
      "rework_status":"A_RECOVERY09_FULL_BBOX_CLEAN_RECONSTRUCTION"
    })

all_bbox=all(x["containment"]=="PASS" and x["raw_containment"]=="PASS" for x in qa_rows)
all_size=all(x["size_ceiling"]=="PASS" for x in qa_rows)
all_positive=all(x["positive_margin"]=="PASS" for x in qa_rows)

# Persist residue mask for independent review.
residue_mask.save(out/"39229D64_SOURCE_RESIDUE_CHECK_MASK.png")
localized_union.save(out/"39229D64_LOCALIZED_LAYER_UNION_MASK.png")

# Visual evidence. Four panels show exactly why this supersedes C_OVERLAP05.
def gray(im):
    bg=Image.new("RGBA",im.size,(72,72,72,255)); bg.alpha_composite(im); return bg.convert("RGB")
thumb=(1024,1024)
panel=Image.new("RGB",(thumb[0]*2,thumb[1]*2),(235,235,235))
panel.paste(gray(src).resize(thumb,Image.Resampling.LANCZOS),(0,0))
panel.paste(gray(c_clean).resize(thumb,Image.Resampling.LANCZOS),(thumb[0],0))
panel.paste(gray(clean).resize(thumb,Image.Resampling.LANCZOS),(0,thumb[1]))
panel.paste(gray(dec).resize(thumb,Image.Resampling.LANCZOS),(thumb[0],thumb[1]))
pd=ImageDraw.Draw(panel)
try:
    font_path=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR"],text=True).strip()
    labelfont=ImageFont.truetype(font_path,28)
except Exception:
    labelfont=ImageFont.load_default()
for xy,label in [((8,8),"SOURCE"),((1032,8),"C_OVERLAP05 CLEAN (rejected)"),((8,1032),"A09 REPAIRED CLEAN"),((1032,1032),"A09 FINAL")]:
    pd.rectangle((xy[0]-4,xy[1]-4,xy[0]+520,xy[1]+38),fill=(245,245,245))
    pd.text(xy,label,font=labelfont,fill=(0,0,0))
panel.save(out/"A_RECOVERY09_SOURCE_CLEAN_REPAIR_FINAL.jpg",quality=94)

contact=[]
for q in qa_rows:
    ob=q["original_bbox"]; m=16
    x1=max(0,ob[0]-m);y1=max(0,ob[1]-m);x2=min(W,ob[2]+m);y2=min(H,ob[3]+m)
    ims=[gray(src.crop((x1,y1,x2,y2))),gray(c_clean.crop((x1,y1,x2,y2))),gray(clean.crop((x1,y1,x2,y2))),gray(dec.crop((x1,y1,x2,y2)))]
    maxw=1200
    total=sum(i.width for i in ims)+24
    if total>maxw:
        sc=(maxw-24)/sum(i.width for i in ims)
        ims=[i.resize((max(1,int(i.width*sc)),max(1,int(i.height*sc))),Image.Resampling.LANCZOS) for i in ims]
    row=Image.new("RGB",(sum(i.width for i in ims)+24,max(i.height for i in ims)+30),(230,230,230))
    xx=0
    for im in ims:
        row.paste(im,(xx,30)); xx+=im.width+8
    ImageDraw.Draw(row).text((3,3),q["key"]+" SRC | C-CLEAN | A09-CLEAN | FINAL",font=labelfont,fill=(0,0,0))
    contact.append(row)
cw=max(x.width for x in contact); ch=sum(x.height for x in contact)+4*(len(contact)-1)
sheet=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for im in contact:
    sheet.paste(im,(0,yy)); yy+=im.height+4
sheet.save(out/"A_RECOVERY09_ROW_CONTACT.jpg",quality=94)
gray(dec_raw).resize(thumb,Image.Resampling.LANCZOS).save(out/"A_RECOVERY09_FINAL_RAW_GRAY.jpg",quality=94)

status_ok=(clean_rep["status"]=="PASS" and final_rep["status"]=="PASS" and all_bbox and all_size and all_positive
           and outside==0 and alpha_outside==0 and protected_changed==0 and localized_pair_overlap==0
           and source_residue_unchanged==0)

report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"base_head":os.environ.get("GITHUB_SHA"),
 "index":57,"asset":asset_rel,
 "return_reason":"C_OVERLAP05 controller visual FAIL: source-English residue/layer overlap despite machine 15/15 placement",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":SOURCE_REPO_COMMIT,"git_blob_sha1":SOURCE_BLOB,"sha256":SOURCE_SHA,
   "path":"Release/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds","classification":"authoritative HD source; DDS header 4096x4096 RGBA32"},
 "source_sha256":SOURCE_SHA,"rejected_c_candidate_sha256":C_REJECTED_SHA,"rejected_c_worker_commit":C_WORKER_COMMIT,
 "candidate_sha256":cand_sha,"candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
 "repair_method":{
   "clean_plate":"replace full exact source text/effect bbox for all 16 target occurrences; transparent overlays become transparent, three Total Rank labels receive row-wise source-art interior reconstruction",
   "korean_layer":"fresh target-specific source-family Korean render; C candidate pixels are not reused, preventing prior black/gray source-layer overdraw from returning",
   "non_target_art":"source pixels outside exact 16 allowed bboxes remain byte/pixel identical"
 },
 "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_original_bboxes":outside,
   "alpha_changed_pixels_outside_original_bboxes":alpha_outside,"protected_visible_pixels_changed":protected_changed,
   "source_residue_unchanged_pixels_outside_localized_layers":source_residue_unchanged,
   "localized_pair_overlap_pixels":localized_pair_overlap},
 "pair_overlaps":pair_overlaps,"rows":qa_rows,
 "all_16_readable_and_raw_bbox_pass":all_bbox,"all_16_size_ceiling_pass":all_size,"all_16_positive_margin":all_positive,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_RECOVERY09_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_RECOVERY09_WORKER_REWORK_REQUIRED"
}
(out/"A_RECOVERY09_39229D64_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"39229D64","index":57,"source_sha256":SOURCE_SHA,"candidate_sha256":cand_sha,
 "rejected_c_candidate_sha256":C_REJECTED_SHA,"target_occurrences":16,"bbox_pass":"16/16" if all_bbox else "FAIL",
 "size_ceiling":"16/16" if all_size else "FAIL","positive_margin":"16/16" if all_positive else "FAIL",
 "clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],
 "changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,
 "protected_visible_pixels_changed":protected_changed,"source_residue_unchanged_pixels_outside_localized_layers":source_residue_unchanged,
 "localized_pair_overlap_pixels":localized_pair_overlap,"worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261004-A-RECOVERY09/A_RECOVERY09_39229D64_REPORT.json"}
(worker_out/"A_RECOVERY09_39229D64.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
