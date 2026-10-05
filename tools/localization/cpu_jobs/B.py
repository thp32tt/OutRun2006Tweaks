#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261006-B-PRODUCTION174-A8CE339F"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_fight_Exst/A8CE339F_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/rel
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_fight_Exst/A8CE339F_512x256.dds"
SOURCE_SHA="08afacc681737d6a138496cefce559853985084cf779921ac32ef2ebfe06883b"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not dds",str(p)))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    pf_flags=struct.unpack_from("<I",b,80)[0]; fourcc=b[84:88]
    bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if bpp!=32 or fourcc!=b"\0\0\0\0" or mips!=1 or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported dds",w,h,mips,fourcc,bpp,len(b)))
    if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
    else: raise RuntimeError(("masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],readable,{"width":w,"height":h,"pitch":pitch,"mips":mips,"pf_flags":pf_flags,"fourcc":fourcc.hex(),"bpp":bpp,"masks":[hex(x) for x in masks],"raw_mode":mode}

def write_dds(header,readable,p,mode):
    p.parent.mkdir(parents=True,exist_ok=True)
    payload=header+readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode)
    p.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

def font_path(style="Black"):
    q=subprocess.check_output(["fc-match","-f","%{file}",f"Noto Sans CJK KR:style={style}"],text=True).strip()
    if not q or not Path(q).exists() or "NotoSansCJK" not in Path(q).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        q=subprocess.check_output(["fc-match","-f","%{file}",f"Noto Sans CJK KR:style={style}"],text=True).strip()
    if not q or not Path(q).exists(): raise RuntimeError(("font",style,q))
    return q
FONT=font_path("Black")

def alpha_bbox_in(im,window):
    x0,y0,x1,y1=window
    a=np.asarray(im.getchannel("A"))[y0:y1,x0:x1]
    ys,xs=np.nonzero(a>0)
    if not len(xs): raise RuntimeError(("empty target window",window))
    return [x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max()+1),y0+int(ys.max()+1)]

def bbox_mask(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def shear_rgba(im,amount):
    if not amount: return im
    add=int(round(amount*im.height))
    return im.transform((im.width+add,im.height),Image.Transform.AFFINE,(1,-amount,add,0,1,0),resample=Image.Resampling.BICUBIC)

def render_text(text,bb,kind):
    x0,y0,x1,y1=bb; bw=x1-x0; bh=y1-y0
    if kind=="extra":
        start=max(30,bh)
        shear=0.20
        outer=(0,10,65,255); inner=(214,154,42,255); fill=(255,238,188,255)
        outer_sw=max(2,round(bh*0.08)); inner_sw=max(1,round(bh*0.035))
    else:
        start=max(24,bh)
        shear=0.0
        outer=(2,10,58,255); inner=None; fill=(255,255,255,255)
        outer_sw=max(2,round(bh*0.08)); inner_sw=0
    for fs in range(start,15,-1):
        f=ImageFont.truetype(FONT,fs)
        probe=Image.new("RGBA",(max(600,bw*3),max(180,bh*3)),(0,0,0,0))
        d=ImageDraw.Draw(probe)
        tb=d.textbbox((0,0),text,font=f,stroke_width=outer_sw)
        xy=(16-tb[0],16-tb[1])
        d.text(xy,text,font=f,fill=fill,stroke_width=outer_sw,stroke_fill=outer)
        if inner is not None:
            d.text(xy,text,font=f,fill=fill,stroke_width=inner_sw,stroke_fill=inner)
        gb=probe.getchannel("A").getbbox()
        if not gb: continue
        g=probe.crop(gb)
        g=shear_rgba(g,shear)
        gb=g.getchannel("A").getbbox()
        if gb: g=g.crop(gb)
        if g.width<=bw-4 and g.height<=bh-4:
            return g,fs,shear,{"fill":fill,"outer":outer,"inner":inner,"outer_stroke":outer_sw,"inner_stroke":inner_sw}
    raise RuntimeError(("fit failed",text,bb))

tmp=Path("/tmp/B174_A8CE339F_SOURCE.dds")
urllib.request.urlretrieve(url,tmp)
if sha(tmp)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(tmp),SOURCE_SHA))
header,src,meta=load_dds(tmp)
if (meta["width"],meta["height"])!=(2048,1024): raise RuntimeError(("unexpected size",meta))

# Text-only windows established from B174 readable probe. They exclude route lines, player markers and all numerals.
windows={
 "extra_time":[0,220,540,325],
 "start_left":[0,315,180,382],
 "goal_left":[620,315,785,382],
 "start_right":[775,315,945,382],
 "goal_right":[1390,315,1565,382]
}
bboxes={k:alpha_bbox_in(src,v) for k,v in windows.items()}

# Sanity sizes guard against accidental capture of route artwork.
guards={
 "extra_time":(250,540,40,105),
 "start_left":(45,180,20,67),
 "goal_left":(45,165,20,67),
 "start_right":(45,170,20,67),
 "goal_right":(45,175,20,67)
}
for k,bb in bboxes.items():
    w=bb[2]-bb[0]; h=bb[3]-bb[1]; minw,maxw,minh,maxh=guards[k]
    if not (minw<=w<=maxw and minh<=h<=maxh):
        raise RuntimeError(("bbox guard",k,bb,(w,h),guards[k]))

translations={
 "extra_time":("Extra Time","추가 시간","extra"),
 "start_left":("Start","출발","small"),
 "goal_left":("Goal","골","small"),
 "start_right":("Start","출발","small"),
 "goal_right":("Goal","골","small")
}

clean=src.copy()
for bb in bboxes.values():
    clean.paste((0,0,0,0),tuple(bb))

# Clean plate: exact transparent source-class text cells; source text alpha must be fully gone.
ca=np.asarray(clean.getchannel("A"))
for k,bb in bboxes.items():
    x0,y0,x1,y1=bb
    if int((ca[y0:y1,x0:x1]>0).sum())!=0:
        raise RuntimeError(("clean residue",k))

final=clean.copy()
layers={}
rows=[]
for k,(eng,kor,kind) in translations.items():
    bb=bboxes[k]; x0,y0,x1,y1=bb
    glyph,fs,shear,sty=render_text(kor,bb,kind)
    px=x0+(x1-x0-glyph.width)//2
    py=y0+(y1-y0-glyph.height)//2
    layer=Image.new("RGBA",src.size,(0,0,0,0)); layer.alpha_composite(glyph,(px,py))
    m=np.asarray(layer.getchannel("A"))>0
    lb=bbox_mask(m)
    if not (x0<lb[0] and y0<lb[1] and lb[2]<x1 and lb[3]<y1):
        raise RuntimeError(("positive margin",k,bb,lb))
    if lb[2]-lb[0]>x1-x0 or lb[3]-lb[1]>y1-y0:
        raise RuntimeError(("size ceiling",k,bb,lb))
    final.alpha_composite(layer); layers[k]=m
    rows.append({
      "key":k,"source":eng,"korean":kor,"original_bbox":bb,"localized_bbox":lb,
      "source_size":[x1-x0,y1-y0],"localized_size":[lb[2]-lb[0],lb[3]-lb[1]],
      "delta_left":lb[0]-x0,"delta_right":x1-lb[2],"delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font":"Noto Sans CJK KR Black","font_size":fs,"shear":shear,"style":sty
    })

# Allowed/source-text/protected masks.
allowed=np.zeros((src.height,src.width),bool)
for bb in bboxes.values():
    x0,y0,x1,y1=bb; allowed[y0:y1,x0:x1]=True
source_alpha=np.asarray(src.getchannel("A"))>0
protected=np.logical_and(source_alpha,~allowed)

sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
changed=np.any(sa!=fa,axis=2)
outside=int(np.logical_and(changed,~allowed).sum())
alpha_out=int(np.logical_and(sa[:,:,3]!=fa[:,:,3],~allowed).sum())
protected_changed=int(np.logical_and(changed,protected).sum())
if outside or alpha_out or protected_changed:
    raise RuntimeError(("scope",outside,alpha_out,protected_changed))

# Localized layers cannot overlap/touch each other.
keys=list(layers)
overlap=[]; touch=[]
for i in range(len(keys)):
    a=layers[keys[i]]
    dil=a.copy()
    dil[:-1,:]|=a[1:,:]; dil[1:,:]|=a[:-1,:]; dil[:,:-1]|=a[:,1:]; dil[:,1:]|=a[:,:-1]
    for j in range(i+1,len(keys)):
        b=layers[keys[j]]
        n=int(np.logical_and(a,b).sum())
        t=int(np.logical_and(dil,b).sum())
        if n: overlap.append([keys[i],keys[j],n])
        if t: touch.append([keys[i],keys[j],t])
if overlap or touch: raise RuntimeError(("localized overlap/touch",overlap,touch))

candidate_sha=write_dds(header,final,candidate,meta["raw_mode"])
dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox():
    raise RuntimeError("dds roundtrip mismatch")

# Evidence.
src.save(out/"B174_SOURCE_READABLE.png")
clean.save(out/"B174_CLEAN_PLATE.png")
decoded.save(out/"B174_FINAL_READABLE.png")
Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/"B174_EDIT_MASK.png")
Image.fromarray((protected*255).astype(np.uint8),"L").save(out/"B174_PROTECTED_MASK.png")

def comp(im,bg=(88,88,88,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im,crop,scale=1):
    v=comp(im).crop(crop)
    if scale!=1: v=v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c=Image.new("RGB",(v.width,v.height+28),"white"); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),label,fill="black"); return c

# top-family source/clean/final contact
crop=(0,190,1600,450)
cards=[card("SOURCE",src,crop,1),card("CLEAN",clean,crop,1),card("FINAL",decoded,crop,1)]
W=max(c.width for c in cards); H=sum(c.height for c in cards)+8*(len(cards)-1)
sheet=Image.new("RGB",(W,H),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.thumbnail((2200,1400),Image.Resampling.LANCZOS)
sheet.save(out/"B174_SOURCE_CLEAN_FINAL_CONTACT.jpg",quality=96)

raw_src=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM); raw_final=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cards=[card("SOURCE_RAW",raw_src,(0,1024-450,1600,1024-190),1),card("FINAL_RAW",raw_final,(0,1024-450,1600,1024-190),1)]
W=max(c.width for c in cards); H=sum(c.height for c in cards)+8
rawsheet=Image.new("RGB",(W,H),"white"); yy=0
for c in cards: rawsheet.paste(c,(0,yy)); yy+=c.height+8
rawsheet.thumbnail((2200,1200),Image.Resampling.LANCZOS)
rawsheet.save(out/"B174_RAW_CONTACT.jpg",quality=96)

report={
 "schema_version":1,"role":"B","run":run,
 "base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "queue_index":52,"asset":rel,
 "readiness_tier":"ZOOM_REVIEW_POSITIVE_THEN_RENDERED_SAME_INVOCATION",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":url,"sha256":SOURCE_SHA},
 "classification":{"localizable":["Extra Time","Start x2","Goal x2"],"translations":{"Extra Time":"추가 시간","Start":"출발","Goal":"골"},
   "protected":["6P/5P/4P/3P/2P/1P player markers","route/timeline bars and ticks","all numeric countdown glyphs","white transition/decorative shards"]},
 "structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":rows,
 "clean_plate":{"class":"transparent sprite cells","source_text_residue_alpha_pixels":0,"status":"PASS"},
 "static_qa":{"elements":"5/5 PASS","changed_outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,
   "localized_overlap_pairs":overlap,"localized_touch_pairs":touch,"dds_roundtrip":"PASS","status":"PASS"},
 "candidate_sha256":candidate_sha,"candidate_path":str(candidate.relative_to(repo)),
 "worker_visual_qa":"PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED",
 "status":"B174_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"B174_A8CE339F_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(repo/"localization/graphics/worker_results/B174_A8CE339F.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":52,"asset":"A8CE339F","source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
 "report":str((out/"B174_A8CE339F_REPORT.json").relative_to(repo)),"status":"WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B174_RENDER_DONE",candidate_sha,bboxes,rows)
