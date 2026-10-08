#!/usr/bin/env python3
"""A199 P0 q121 new native white-italic car/mode/course headers.
No VR, FFB, DX11, DXVK. CPU-heavy work on GitHub-hosted runner only.
"""
import os, json, struct, hashlib, glob, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("A199 requires GitHub Actions CPU role A")
root=Path.cwd()
run="20261009-A199-P0-Q121-ORIGINAL-WHITE-ITALIC"
out=root/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker=root/"localization/graphics/worker_results"
worker.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
candidate=root/"localization/graphics/hd_candidates"/asset
oldsha="d1bb0c7cc22a398b47085445787bc15fc10db1125b5298d1c38d1f5deaf7dc27"
originalsha="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
baseline=root/"localization/graphics/role_A/20261008-A176-Q121-TRANSPARENT-PLATE"
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
    bb=Path(path).read_bytes()
    if bb[:4]!=b"DDS ":raise RuntimeError("Invalid DDS")
    h,w=struct.unpack_from("<II",bb,12)
    pitch=struct.unpack_from("<I",bb,20)[0]
    mips=struct.unpack_from("<I",bb,28)[0]
    bpp=struct.unpack_from("<I",bb,88)[0]
    fmt=bb[84:88]
    masks=struct.unpack_from("<IIII",bb,92)
    mode={(255,65280,16711680,4278190080):"RGBA",(16711680,65280,255,4278190080):"BGRA"}.get(masks)
    if not mode or bpp!=32 or mips!=1 or fmt!=bytes(4) or len(bb)!=128+w*h*4:raise RuntimeError(("DDS changed",w,h,bpp,mips,mode))
    image=Image.frombytes("RGBA",(w,h),bb[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return bb[:128],image,{"width":w,"height":h,"mode":mode,"mips":mips,"pitch":pitch,"masks":list(masks),"raw":"mirror_y"}
def write(header,image,mode):
    binary=header+image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",mode)
    candidate.write_bytes(binary)
    return hashlib.sha256(binary).hexdigest()
def bb(mask):
    ys,xs=np.nonzero(mask)
    if len(xs)==0:raise RuntimeError("No visible title")
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def font():
    p=glob.glob("/usr/share/fonts/**/NotoSansCJK-Black.ttc",recursive=True)
    if not p:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
        p=glob.glob("/usr/share/fonts/**/NotoSansCJK-Black.ttc",recursive=True)
    if not p:raise RuntimeError("CJK original-style Black font missing")
    return p[0]
def glyph(text,size,shear):
    f=ImageFont.truetype(FONT,size,index=1)
    tmp=Image.new("L",(2800,370),0)
    dr=ImageDraw.Draw(tmp)
    dr.text((40,35),text,font=f,fill=255)
    b=tmp.getbbox()
    if b is None or b[0]<=2 or b[1]<=2 or b[2]>=tmp.width-2 or b[3]>=tmp.height-2:
        raise RuntimeError(("Clipped source glyph render",text,size,b))
    im=tmp.crop(b)
    d=int(np.ceil(shear*im.height))+8
    # x_src=x_dst+shear*y-shear*height+4 means upper glyph leans RIGHT.
    result=im.transform((im.width+d,im.height),Image.Transform.AFFINE,
       (1,shear,-shear*im.height+4,0,1,0),resample=Image.Resampling.BICUBIC,fillcolor=0)
    bounds=result.getbbox()
    if not bounds:raise RuntimeError("Slant transform empty")
    return result.crop(bounds)
def rgb(im,color):
    back=Image.new("RGBA",im.size,(*color,255))
    back.alpha_composite(im)
    return back.convert("RGB")
if not candidate.exists() or sha(candidate)!=oldsha:
    raise RuntimeError(("P0 q121 concurrent newer work, fail closed",sha(candidate) if candidate.exists() else "missing"))
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","121","--require-safe-rerender"],
                      capture_output=True,text=True)
print("A199_TRIAGE",triage.stdout,flush=True)
if triage.returncode!=0 or '"MATERIAL_REWORK"' not in triage.stdout:
    raise RuntimeError(("P0 rerender blocked",triage.stderr,triage.stdout))
original=Path("/tmp/a199_q121_canonical.dds")
urllib.request.urlretrieve(url,original)
if sha(original)!=originalsha:raise RuntimeError(("canonical English source mismatch",sha(original)))
header,source,meta=load(original)
prior_header,prior,prior_meta=load(candidate)
if header!=prior_header or meta!=prior_meta or (meta["width"],meta["height"],meta["mode"])!=(4096,4096,"RGBA"):
    raise RuntimeError("Candidate/source format incompatible")
clean=Image.open(baseline/"A176_Q121_CLEAN.png").convert("RGBA")
if clean.size!=source.size:raise RuntimeError("Authored clean size changed")
a176=json.loads((baseline/"A176_Q121_REPORT.json").read_text(encoding="utf-8"))
if a176["source_sha256"]!=originalsha or a176["candidate_sha256"]!=oldsha:raise RuntimeError("A176 provenance drift")
regions=[
  {"key":"select_game_mode","english":"Select Game Mode","korean":"게임 모드 선택","source_bbox":[166,819,1166,973],"old_bbox":[341,846,990,945],"band":[820,953],"min_height":118},
  {"key":"select_car","english":"Select your car","korean":"차량 선택","source_bbox":[243,947,1156,1111],"old_bbox":[485,979,913,1078],"band":[959,1077],"min_height":109},
  {"key":"select_course","english":"Select Course","korean":"코스 선택","source_bbox":[302,1062,1085,1213],"old_bbox":[478,1088,908,1187],"band":[1083,1207],"min_height":110}
]
# Exact A176 authored CLEAN preserves previously localized non-title sprites.
src=np.asarray(source)
ca=np.asarray(clean)
priorpix=np.asarray(prior)
allowed=np.zeros((4096,4096),dtype=bool)
for row in regions:
    x0,y0,x1,y1=row["source_bbox"]
    allowed[y0:y1,x0:x1]=True
    if np.any(ca[y0:y1,x0:x1,3]):raise RuntimeError(("old-source-clean not transparent",row["key"]))
preexisting_out=int(np.logical_and(np.any(ca!=priorpix,axis=2),~allowed).sum())
if preexisting_out:raise RuntimeError(("A176 CLEAN/current unrelated asset drift",preexisting_out))
FONT=font()
final=clean.copy()
glyph_masks=[]
result=[]
for row in regions:
    x0,y0,x1,y1=row["source_bbox"]
    by0,by1=row["band"]
    # Source bbox envelopes overlap in Y; explicit non-touch vertical
    # corridors avoid STAGE/selector header layer overlap after enlarged type.
    if by0<y0 or by1>y1:raise RuntimeError("Vertical title corridor not source-contained")
    availh=by1-by0
    availw=x1-x0
    picked=None
    for size in range(160,102,-1):
        white=glyph(row["korean"],size,0.25)
        # 5px right+5px down SINGLE flat black original-like depth only.
        if white.width+11<=availw-6 and white.height+11<=availh-4:
            picked=(size,white)
            break
    if not picked:raise RuntimeError(("No style-preserving native size fits",row["key"]))
    pt,face=picked
    if face.height<row["min_height"]-6:
        raise RuntimeError(("Insufficient source-height hierarchy",row["key"],face.size))
    gx=x0+(availw-face.width-5)//2
    gy=by0+(availh-face.height-5)//2
    if gx-x0<=2 or gx+face.width+5>=x1-2 or gy<=by0+1 or gy+face.height+5>=by1-1:
        raise RuntimeError(("Original bbox/vertical band with shadow fail",row["key"],face.size,(gx,gy)))
    fg=Image.new("L",source.size,0)
    fg.paste(face,(gx,gy))
    bg=Image.new("L",source.size,0)
    bg.paste(face,(gx+5,gy+5))
    union=(np.asarray(fg)>0)|(np.asarray(bg)>0)
    for former in glyph_masks:
        if np.any(union & former):raise RuntimeError(("Label collision",row["key"]))
    if np.any(union & ~allowed):raise RuntimeError(("Protected source pixel intrusion",row["key"]))
    # RGBA flat right/lower black shadow and clean white original-like face.
    black=Image.new("RGBA",source.size,(0,0,0,0))
    black.putalpha(bg)
    white=Image.new("RGBA",source.size,(250,250,250,0))
    white.putalpha(fg)
    final.alpha_composite(black)
    final.alpha_composite(white)
    glyph_masks.append(union)
    b=bb(union)
    oldb=row["old_bbox"]
    result.append({
       "key":row["key"],"english":row["english"],"korean":row["korean"],
       "source_bbox":row["source_bbox"],"old_bbox":oldb,"new_bbox":b,
       "old_size":[oldb[2]-oldb[0],oldb[3]-oldb[1]],
       "new_size":[b[2]-b[0],b[3]-b[1]],"face_size":list(face.size),
       "source_size":[x1-x0,y1-y0],"positive_margins":[b[0]-x0,x1-b[2],b[1]-y0,y1-b[3]],
       "band":row["band"],"point_size":pt,"shear":0.25,"shadow_delta":[5,5],
       "face_rgb":[250,250,250],"shadow_rgb":[0,0,0]
    })
fa=np.asarray(final)
newglyph=np.zeros_like(allowed)
for m in glyph_masks:newglyph|=m
changed=np.any(ca!=fa,axis=2)
clean_final_outside=int(np.logical_and(changed,~allowed).sum())
clean_final_nonglyph=int(np.logical_and(changed,~newglyph).sum())
alpha_changed_outside=int(np.logical_and(fa[:,:,3]!=ca[:,:,3],~allowed).sum())
protected_changed=int(np.logical_and(fa!=priorpix,~allowed[:,:,None]).sum())
source_remainder=0
for r in regions:
    x0,y0,x1,y1=r["source_bbox"]
    # English source has alpha; clean is genuinely transparent here.
    source_remainder+=int(np.logical_and(src[y0:y1,x0:x1,3]>0,
                  np.logical_and(np.all(fa[y0:y1,x0:x1]==src[y0:y1,x0:x1],axis=2),
                                 ~newglyph[y0:y1,x0:x1])).sum())
if any((clean_final_outside,clean_final_nonglyph,alpha_changed_outside,protected_changed,source_remainder)):
    raise RuntimeError(("source-clean composite-protected fail",
                        clean_final_outside,clean_final_nonglyph,alpha_changed_outside,protected_changed,source_remainder))
if len(result)!=3 or any(r["new_size"][1]<=r["old_size"][1]+6 for r in result):
    raise RuntimeError(("No materially better title size",result))
newsha=write(header,final,meta["mode"])
hh,encoded,mm=load(candidate)
if hh!=header or mm!=meta or ImageChops.difference(encoded,final).getbbox():
    raise RuntimeError("actual persisted DDS bytes roundtrip failed")
source.save(out/"A199_SOURCE_NATIVE.png")
clean.save(out/"A199_CLEAN_NATIVE.png")
encoded.save(out/"A199_FINAL_SAVED_NATIVE.png")
Image.fromarray((allowed*255).astype("uint8"),"L").save(out/"A199_ORIGINAL_BBOX_SCOPE.png")
Image.fromarray((newglyph*255).astype("uint8"),"L").save(out/"A199_COMPOSED_GLYPHS_SCOPE.png")
proof=[]
for i,r in enumerate(regions):
    x0,y0,x1,y1=r["source_bbox"]
    crop=(max(0,x0-16),max(0,y0-20),min(4096,x1+16),min(4096,y1+20))
    for k,im in (("SOURCE",source),("CLEAN",clean),("FINAL",encoded)):
        im.crop(crop).save(out/f"A199_{i}_{r['key']}_{k}_NATIVE.png")
    for bgname,bgc in (("BLACK",(0,0,0)),("GRAY",(128,128,128)),("WHITE",(255,255,255))):
        images=[rgb(im,bgc).crop(crop) for im in (source,clean,encoded)]
        w,h=images[0].size
        sheet=Image.new("RGB",(3*w+14,h+30),"white")
        ImageDraw.Draw(sheet).text((2,4),f"A199 {r['key']} SOURCE | CLEAN | SAVED FINAL {bgname}",fill="black")
        for j,im in enumerate(images):sheet.paste(im,(j*(w+7),30))
        for scale in (100,75,50):
            if scale<100:
                view=sheet.resize((sheet.width*scale//100,sheet.height*scale//100),Image.Resampling.LANCZOS)
            else:view=sheet
            name=f"A199_{i}_{r['key']}_{bgname}_{scale}.jpg"
            view.save(out/name,quality=95)
            proof.append(name)
for orientation,imgs in (("READABLE",(source,encoded)),
                         ("RAW",(source.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
                                 encoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)))):
    a,b=[rgb(im,(200,200,200)) for im in imgs]
    a.thumbnail((1100,1100));b.thumbnail((1100,1100))
    sheet=Image.new("RGB",(a.width+b.width+10,max(a.height,b.height)+30),"white")
    ImageDraw.Draw(sheet).text((3,5),f"English exact SOURCE / Korean saved DDS {orientation}",fill="black")
    sheet.paste(a,(0,30));sheet.paste(b,(a.width+10,30))
    sheet.save(out/f"A199_{orientation}_SOURCE_FINAL.jpg",quality=95)
qa={
 "schema_version":1,"role":"A","run":run,"priority":"P0","queue_index":121,
 "affected_screenshots":["181","182","192"],"ingame_rows":["IGR-030","IGR-031","IGR-040"],
 "asset":asset,"canonical_source_sha256":originalsha,"superseded_sha256":oldsha,"candidate_sha256":newsha,
 "source_clean":"localization/graphics/role_A/20261008-A176-Q121-TRANSPARENT-PLATE/A176_Q121_CLEAN.png",
 "source_style":"original heavy WHITE italic face with simple RIGHT-DOWN 5px BLACK depth, not multi hard gray outlines",
 "rows":result,"machine_qa":{"clean_old_unrelated_diff_outside_original_bboxes":preexisting_out,
 "clean_final_outside_original_bboxes":clean_final_outside,"clean_final_outside_glyph_masks":clean_final_nonglyph,
 "alpha_outside_original_bboxes":alpha_changed_outside,"protected_unrelated_changed_pixels":protected_changed,
 "source_exact_residue_outside_localized_masks":source_remainder,"label_collision_pairs":0,
 "header128_exact":True,"native_dds_roundtrip":"PASS"},
 "native_structure":meta,"artifacts":proof,"header_alpha_preserved":True,
 "C1":"PENDING","C3":"PENDING","user_game_retest":"REQUIRED","RUNTIME_VALIDATION":"UNTESTED",
 "producer_decision":"MACHINE_PASS_CONTROLLER_VISUAL_PENDING",
 "known_limitations":["In-game car header clip may also involve runtime/title-layer mapping","No protected Dino logo source established: left untouched","In-game English small info cells are separate mixed source mapping"]
}
(out/"A199_WORKER_REPORT.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(worker/"A199_Q121.json").write_text(json.dumps({
 "run":run,"index":121,"candidate_sha256":newsha,
 "source_sha256":originalsha,"regions":result,"machine_qa":qa["machine_qa"],
 "status":"MACHINE_PASS_CONTROLLER_VISUAL_PENDING","RUNTIME_VALIDATION":"UNTESTED",
 "report":str((out/"A199_WORKER_REPORT.json").relative_to(root))
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("A199_MACHINE_DONE",newsha,[(r["key"],r["old_size"],r["new_size"],r["positive_margins"]) for r in result],flush=True)
