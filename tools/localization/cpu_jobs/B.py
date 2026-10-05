#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,statistics,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageOps,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION72"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds"
index=230
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b70"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_00E95DA5_512x256_atlas.json",atlas)

sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(m): return m.point(lambda v:255 if v else 0)
def count(m): return sum(m.histogram()[1:])
def dmask(a,b):
    d=ImageChops.difference(a,b)
    m=d.split()[0]
    for z in d.split()[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

if blob(sb)!="ee939d33fd363be135e681b076021c92cddcb489":
    raise RuntimeError(("source blob drift",blob(sb)))
if blob(ab)!="d1cbe695add81e599424c29aa40539bb6875ef5a":
    raise RuntimeError(("atlas blob drift",blob(ab)))

H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(2048,1024) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,pitch,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}

# Reviewed pass11 semantics. BGM is intentionally unchanged and therefore preserved exactly.
specs=[
    (5,"FERRARI CARS","페라리 차량","dark"),
    (6,"CAR COLORS","차량 색상","dark"),
    (13,"SHOWROOM ITEMS","쇼룸 아이템","white"),
    (14,"GAME MODES","게임 모드","white"),
    (15,"FERRARI'S","페라리","white"),
    (16,"COURSES","코스","white"),
    (17,"CAR COLOURS","차량 색상","white"),
    (18,"BONUS MATERIAL","보너스 자료","white"),
    (19,"BGMUSIC","BGM","white"),
    (24,"UNAVAILABLE","이용 불가","pill"),
    (25,"SOLD","판매 완료","pill"),
]
preserved={
    1:"Night Flight (song title)",2:"Magical Sound Shower (song title)",3:"Life Was A Bore (song title)",
    4:"Keep Your Heart (song title)",7:"BGM (translation unchanged)",8:"Alberto's Antics Vol.5",
    9:"Alberto's Antics Vol.4",10:"Alberto's Antics Vol.3",11:"Alberto's Antics Vol.2",12:"Alberto's Antics Vol.1",
    20:"You cannot buy this item yet",21:"You already own this item",22:"yellow bar artwork",23:"gray bar artwork",
    26:"separator artwork",0:"decorative panel"
}

# Exact source masks. Transparent text-only regions use exact non-zero alpha.
# Pill labels need a text-only color separation from the opaque red rounded plate.
def pill_text_mask(cell):
    pix=cell.load(); w,h=cell.size
    m=Image.new("L",(w,h),0); mp=m.load()
    row_bg={}
    for y in range(h):
        vals=[]
        for x in range(4,max(4,w-4)):
            r,g,b,a=pix[x,y]
            if a>=245 and not (g>105 and b>105 and max(r,g,b)-min(r,g,b)<95):
                vals.append((r,g,b,a))
        if vals:
            row_bg[y]=tuple(int(round(statistics.median(v[k] for v in vals))) for k in range(4))
    for y in range(h):
        bg=row_bg.get(y)
        if not bg: continue
        br,bg_g,bb,ba=bg
        for x in range(w):
            r,g,b,a=pix[x,y]
            if a<16: continue
            # White/gray glyph and antialias pixels rise strongly in G/B above the red plate.
            if (g-bg_g)>=18 and (b-bb)>=18 and r>=br-28 and max(r,g,b)-min(r,g,b)<=115:
                mp[x,y]=255
    # Strengthen the text/effect footprint inside the tight detected bbox.
    # This catches low-contrast antialias/shadow residue without enlarging the hard source bbox.
    tight=m.getbbox()
    if tight:
        x0,y0,x1,y1=tight
        for y in range(y0,y1):
            bg=row_bg.get(y)
            if not bg: continue
            br,bg_g,bb,ba=bg
            for x in range(x0,x1):
                r,g,b,a=pix[x,y]
                if a<16: continue
                if max(abs(r-br),abs(g-bg_g),abs(b-bb))>6:
                    mp[x,y]=255
        grown=bmask(m.filter(ImageFilter.MaxFilter(3)))
        clipped=Image.new("L",(w,h),0)
        clipped.paste(grown.crop(tight),(x0,y0))
        m=clipped
    return bmask(m)

source_mask=Image.new("L",(W,H),0)
allowed=Image.new("L",(W,H),0)
rows=[]
pill_bg={}
for idx,en,ko,group in specs:
    x,y,cw,ch=regions[idx]["rect"]
    cell=src.crop((x,y,x+cw,y+ch))
    if group=="pill":
        lm=pill_text_mask(cell)
    else:
        lm=bmask(cell.getchannel("A"))
    bb=lm.getbbox()
    if not bb:
        raise RuntimeError(("empty source text mask",idx,en))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    # source mask paste
    smcrop=source_mask.crop((x,y,x+cw,y+ch))
    source_mask.paste(ImageChops.lighter(smcrop,lm),(x,y))
    ImageDraw.Draw(allowed).rectangle((ob[0],ob[1],ob[2]-1,ob[3]-1),fill=255)
    rows.append({"region_idx":idx,"source":en,"korean":ko,"group":group,"cell":[x,y,cw,ch],"original_bbox":ob,"source_mask_pixels":count(lm)})
    if group=="pill":
        # Per-row exact plate estimate from non-text opaque pixels.
        cp=cell.load(); mp=lm.load(); rb={}
        for yy in range(ch):
            vals=[]
            for xx in range(4,max(4,cw-4)):
                r,g,b,a=cp[xx,yy]
                if a>=245 and mp[xx,yy]==0:
                    vals.append((r,g,b,a))
            if vals:
                rb[yy]=tuple(int(round(statistics.median(v[k] for v in vals))) for k in range(4))
        pill_bg[idx]=rb

# Ensure preserved regions do not intersect edit bboxes.
for idx,name in preserved.items():
    r=regions[idx]; x,y,w,h=r["rect"]
    cellmask=Image.new("L",(W,H),0)
    ImageDraw.Draw(cellmask).rectangle((x,y,x+w-1,y+h-1),fill=255)
    if count(ImageChops.multiply(cellmask,allowed)):
        raise RuntimeError(("preserved region intersects allowed edit bbox",idx,name))

clean=src.copy()
cpix=clean.load(); sm=source_mask.load()
# Transparent/text-only rows clear to transparent. Pill rows restore the red plate.
for r in rows:
    idx=r["region_idx"]; x,y,cw,ch=r["cell"]; group=r["group"]
    if group!="pill":
        for yy in range(y,y+ch):
            for xx in range(x,x+cw):
                if sm[xx,yy]: cpix[xx,yy]=(0,0,0,0)
    else:
        rb=pill_bg[idx]
        for yy in range(ch):
            bg=rb.get(yy)
            if bg is None: continue
            for xx in range(cw):
                if sm[x+xx,y+yy]: cpix[x+xx,y+yy]=bg

sp=out/"E95_SOURCE_READABLE.png"; cp=out/"E95_CLEAN_PLATE.png"
smp=out/"E95_SOURCE_TEXT_MASK.png"; ap=out/"E95_ALLOWED_BBOX_MASK.png"
src.save(sp); clean.save(cp); source_mask.save(smp); allowed.save(ap)
protected=ImageChops.multiply(bmask(src.getchannel("A")),ImageOps.invert(allowed))
pp=out/"E95_PROTECTED_VISIBLE_MASK.png"; protected.save(pp)
subprocess.run(["python3",str(validator),str(sp),str(cp),str(smp),"--protected-mask",str(pp),"--report",str(out/"B72_CLEAN_VALIDATION.json")],check=True)
cleanrep=json.loads((out/"B72_CLEAN_VALIDATION.json").read_text())
if cleanrep["status"]!="PASS": raise RuntimeError(("clean validation",cleanrep))

def findfont():
    # Force a heavy CJK face; Regular fallback failed controller source-style QA in B70.
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold"]:
        try: s=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{style}",pat],text=True).strip()
        except Exception: s=""
        parts=s.rsplit("|",2)
        if len(parts)==3:
            fp,ix,style=parts
            name=Path(fp).name
            if fp and Path(fp).exists() and "NotoSansCJK" in name and ("Black" in name or "Bold" in name or "Black" in style or "Bold" in style):
                return fp,int(ix or 0),pat,style
    raise RuntimeError("verified Noto Sans CJK Bold/Black face unavailable")
FONT,FI,FPAT,FSTYLE=findfont()

# Source-family color measurements.
def source_colors(group):
    vals=[]
    for r in rows:
        if r["group"]!=group: continue
        ob=r["original_bbox"]
        for yy in range(ob[1],ob[3]):
            for xx in range(ob[0],ob[2]):
                if sm[xx,yy]:
                    rr,gg,bb,aa=src.getpixel((xx,yy))
                    if aa>=48: vals.append((rr,gg,bb,aa))
    if not vals: return (240,240,240,255)
    vals.sort(key=lambda v:0.2126*v[0]+0.7152*v[1]+0.0722*v[2])
    top=vals[max(0,int(len(vals)*0.72)):]
    return tuple(int(round(statistics.median(v[k] for v in top))) for k in range(4))
dark_fill=source_colors("dark")
white_fill=source_colors("white")
pill_fill=(247,247,247,255)

MARGIN=2
def render(text,fs,color):
    f=ImageFont.truetype(FONT,fs,index=FI)
    tmp=Image.new("L",(16,16),0)
    bb=ImageDraw.Draw(tmp).textbbox((0,0),text,font=f,stroke_width=0)
    pad=6
    w=max(8,bb[2]-bb[0]+pad*2); h=max(8,bb[3]-bb[1]+pad*2)
    a=Image.new("L",(w,h),0)
    ImageDraw.Draw(a).text((pad-bb[0],pad-bb[1]),text,font=f,fill=255)
    abb=a.getbbox()
    a=a.crop(abb) if abb else a
    rgba=Image.new("RGBA",a.size,color)
    rgba.putalpha(a)
    return rgba

# Shared font sizes for source-shared families. Pill rows intentionally have different source scales.
group_fs={}
for group in ["dark","white"]:
    rr=[r for r in rows if r["group"]==group]
    chosen=None
    for fs in range(74,16,-1):
        ok=True
        for r in rr:
            ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
            color=dark_fill if group=="dark" else white_fill
            lay=render(r["korean"],fs,color)
            if lay.width>aw-2*MARGIN or lay.height>ah-2*MARGIN:
                ok=False; break
        if ok: chosen=fs; break
    if chosen is None: raise RuntimeError(("no shared fit",group))
    group_fs[group]=chosen

final=clean.copy(); targets=[]; outrows=[]
for r in rows:
    ob=r["original_bbox"]; aw=ob[2]-ob[0]; ah=ob[3]-ob[1]
    group=r["group"]
    color=dark_fill if group=="dark" else (white_fill if group=="white" else pill_fill)
    if group=="pill":
        fs=None
        for q in range(86,15,-1):
            lay=render(r["korean"],q,color)
            if lay.width<=aw-2*MARGIN and lay.height<=ah-2*MARGIN:
                fs=q; break
        if fs is None: raise RuntimeError(("pill fit",r["region_idx"]))
    else:
        fs=group_fs[group]
        lay=render(r["korean"],fs,color)
    lay=render(r["korean"],fs,color)
    # Preserve source alignment: text-only rows are left aligned, pill labels centered.
    if group=="pill":
        px=ob[0]+(aw-lay.width)//2
    else:
        px=ob[0]+MARGIN
    py=ob[1]+(ah-lay.height)//2
    px=max(ob[0]+MARGIN,min(px,ob[2]-MARGIN-lay.width))
    py=max(ob[1]+MARGIN,min(py,ob[3]-MARGIN-lay.height))
    final.alpha_composite(lay,(px,py))
    lm=Image.new("L",(W,H),0); lm.paste(bmask(lay.getchannel("A")),(px,py))
    lb=list(lm.getbbox())
    if not(lb[0]>ob[0] and lb[1]>ob[1] and lb[2]<ob[2] and lb[3]<ob[3]):
        raise RuntimeError(("positive margin",r["region_idx"],ob,lb))
    if lb[2]-lb[0]>aw or lb[3]-lb[1]>ah:
        raise RuntimeError(("size ceiling",r["region_idx"],ob,lb))
    targets.append((r["region_idx"],lm))
    outrows.append({
        **r,"localized_bbox":lb,
        "source_width":aw,"source_height":ah,
        "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],
        "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
        "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
        "font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"font_size":fs,"fill_rgba":color,
        "alignment":"center" if group=="pill" else "left",
        "rework_status":"B72_NEW_EXACT_HD_CANDIDATE"
    })

ov=0; touch=[]
for i in range(len(targets)):
    for j in range(i+1,len(targets)):
        a=targets[i][1]; b=targets[j][1]
        x=count(ImageChops.multiply(a,b))
        n=count(ImageChops.multiply(a.filter(ImageFilter.MaxFilter(3)),b))
        ov+=x
        if x or n: touch.append([targets[i][0],targets[j][0],x,n])
if ov or touch: raise RuntimeError(("label overlap/touch",ov,touch))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
if payload[:128]!=sb[:128]: raise RuntimeError("header")
candidate.write_bytes(payload)
csha=sha(payload)

raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip")
fp=out/"E95_FINAL_DECODED_READABLE.png"; dec.save(fp)
subprocess.run(["python3",str(validator),str(sp),str(fp),str(ap),"--protected-mask",str(pp),"--report",str(out/"B72_FINAL_VALIDATION.json")],check=True)
finalrep=json.loads((out/"B72_FINAL_VALIDATION.json").read_text())

diff=dmask(src,dec)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alphaout=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),dec.getchannel("A"))),ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(diff,protected))
target=Image.new("L",(W,H),0)
for _,m in targets: target=ImageChops.lighter(target,m)
residue=count(ImageChops.multiply(ImageChops.multiply(source_mask,ImageOps.invert(target)),ImageOps.invert(diff)))
if finalrep["status"]!="PASS" or outside or alphaout or prot or residue or ov or touch:
    raise RuntimeError(("gates",finalrep["status"],outside,alphaout,prot,residue,ov,touch))
target.save(out/"E95_TARGET_TEXT_MASK.png")

# Verify preserved regions are byte/pixel exact.
preserved_changed={}
for idx,name in preserved.items():
    x,y,w,h=regions[idx]["rect"]
    d=dmask(src.crop((x,y,x+w,y+h)),dec.crop((x,y,x+w,y+h)))
    preserved_changed[str(idx)]=count(d)
if any(preserved_changed.values()):
    raise RuntimeError(("preserved region changed",preserved_changed))

# Evidence sheets.
full=Image.new("RGB",(1024,3*540),"white")
for i,(label,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",dec)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST)
    full.paste(z,(0,i*540+24))
    ImageDraw.Draw(full).text((5,i*540+4),label,fill="black")
full.save(out/"B72_E95_SOURCE_CLEAN_FINAL.jpg",quality=96)

cards=[]
for r in outrows:
    ob=r["original_bbox"]; p=12
    cr=(max(0,ob[0]-p),max(0,ob[1]-p),min(W,ob[2]+p),min(H,ob[3]+p))
    ims=[comp(z).crop(cr) for z in (src,clean,dec)]
    cw=sum(z.width for z in ims)+12; ch=max(z.height for z in ims)+30
    c=Image.new("RGB",(cw,ch),"white"); xx=0
    for z in ims: c.paste(z,(xx,30)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["region_idx"]} {r["source"]} -> {r["korean"]}',fill="black")
    cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B72_E95_ROW_CONTACT.jpg",quality=96)

rr=Image.new("RGB",(1024,2*540),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec)]):
    z=comp(im).resize((1024,512),Image.Resampling.NEAREST)
    rr.paste(z,(0,i*540+24)); ImageDraw.Draw(rr).text((5,i*540+4),label,fill="black")
rr.save(out/"B72_E95_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"B","run":run,"index":index,"asset":asset,
 "readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "semantic_binding":{"localized":{str(i):s for i,s,_,_ in specs},"preserved":{str(k):v for k,v in preserved.items()}},
 "translations":{str(i):k for i,_,k,_ in specs},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "style_groups":{"dark":{"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"font_size":group_fs["dark"],"fill_rgba":dark_fill,"alignment":"left"},"white":{"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"font_size":group_fs["white"],"fill_rgba":white_fill,"alignment":"left"},"pill":{"font_file":Path(FONT).name,"font_face_index":FI,"font_style":FSTYLE,"fill_rgba":pill_fill,"alignment":"center","background_reconstruction":"per-row median of non-text opaque red plate pixels"}},
 "rows":outrows,
 "preserved_regions_changed_pixels":preserved_changed,
 "clean_plate_validator":cleanrep,"final_mask_validator":finalrep,
 "decoded_changes":{"changed_pixels_total":count(diff),"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,"exact_source_residue":residue,"overlap":ov,"touch_pairs":touch},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "RUNTIME_VALIDATION":"UNTESTED",
 "status":"B_PRODUCTION72_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B72_E95_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={
 "run":run,"index":index,"asset":"E95DA5","source_sha256":sha(sb),"candidate_sha256":csha,
 "localized_physical_elements":len(specs),"preserved_regions":len(preserved),
 "bbox_size_positive_margin":f"{len(specs)}/{len(specs)}",
 "clean_plate_validator":cleanrep["status"],"final_mask_validator":finalrep["status"],
 "source_residue":residue,"outside":outside,"alpha_outside":alphaout,"protected_changed":prot,
 "preserved_regions_changed":sum(preserved_changed.values()),"overlap":ov,"touch_pairs":len(touch),
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":f"localization/graphics/role_B/{run}/B72_E95_REPORT.json"
}
(wr/"B72_E95DA5.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False))
