#!/usr/bin/env python3
"""B365 q176: new geometric NanumGothic flat-block face pilot, FLAGMAN4 only.

C371 independently rejected the B346 native Noto Bold stroke method for
underweight source-family red type; this pilot changes the typeface itself and
keeps the rest of the atlas byte-identical, pending C2 family qualification.
"""
import hashlib,io,json,os,struct,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont

assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions"
assert os.getenv("OUTRUN_CPU_ROLE")=="B"
sha=lambda b:hashlib.sha256(b).hexdigest()
G=Path("localization/graphics")
O=G/"role_B/20261011-B365-Q176-NANUM-GEOMETRIC-RED-PILOT"
O.mkdir(parents=True,exist_ok=True)
Q=176
SOURCE_SHA="8ba40915abca8b7022acbcc743e93186970fdf7e29f0eb80e84903d31074c708"
CLEAN_SHA="29e77ca7391022eff23b84a197a41c123938f3aa03a6fb7c69a783d0ce0b6ebe"
OFFICIAL_SHA="494d42c09c58241405dd14de74ca976b5432d84eb250d4bceb5684e97fbad407"
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
old=(G/"hd_candidates"/asset).read_bytes()
assert sha(old)==OFFICIAL_SHA,("CONCURRENT_OFFICIAL_CHANGED",sha(old))
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","176"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),tri
lib=subprocess.run([sys.executable,"tools/localization/plate_library.py","inspect","--index","176",
"--source-sha",SOURCE_SHA,"--region","flagman4","--orientation","readable_flip_y"],capture_output=True,text=True)
assert lib.returncode!=0 or "PLATE_PASS" in lib.stdout,("LIBRARY_UNAPPROVED",lib.stdout[-700:])
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
with urllib.request.urlopen(source_url,timeout=90) as rr:sb=rr.read()
assert sha(sb)==SOURCE_SHA,("SOURCE_NOT_CANONICAL",sha(sb))
assert len(sb)==len(old)==16777344 and sb[:128]==old[:128], "HEADER_SIZE_MISMATCH"
clean_path=G/"role_B/20261010-B346-Q176-SOURCE-HEAVY-RED-FONT-PILOT/B346_P1_CLEAN_SOURCE_ONLY.png"
cp=clean_path.read_bytes()
assert sha(cp)==CLEAN_SHA,("CLEAN_NOT_EXACT",sha(cp))
def decode(b):
    return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
src=decode(sb);prev=decode(old)
clean=np.array(Image.open(io.BytesIO(cp)).convert("RGBA"))
assert src.shape==prev.shape==clean.shape==(2048,2048,4)
# Exact originally printed source pixels (before any new lettering).
bb=(8,49,988,204)
x0,y0,x1,y1=bb
assert np.count_nonzero(clean[y0:y1,x0:x1,3])==0
srcink=src[y0:y1,x0:x1]
ink=np.median(srcink[srcink[:,:,3]>=200,:3],axis=0).round().astype(np.uint8)
assert tuple(ink)==(186,0,0),("SOURCE_RED_FAMILY_CHANGED",ink.tolist())
# Source family red BLOCK characters require new native face topology; no
# previously rejected Noto Bold stroke/dilation trial may be reused.
fontpath=Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")
if not fontpath.is_file():
    subprocess.run(["sudo","apt-get","install","-y","--no-install-recommends","fonts-nanum"],check=True)
assert fontpath.is_file(),"NANUM_NATIVE_FACE_NOT_INSTALLED"
fb=fontpath.read_bytes()
ft=TTFont(str(fontpath),lazy=True)
chars="플래그맨 4"
cmap=ft.getBestCmap()
assert all(ord(c) in cmap for c in chars if c!=" "),"FAMILY_FONT_GLYPH_FALLBACK_FORBIDDEN"
# Direct final-size FreeType vector raster. No bitmap scaling or synthetic
# outline. Choose largest height <= original face ceiling with positive margin.
fits=[]
for ppem in range(120,176):
    font=ImageFont.truetype(str(fontpath),ppem,layout_engine=ImageFont.Layout.BASIC)
    im=Image.new("L",(1300,230),0)
    d=ImageDraw.Draw(im)
    d.text((16,15),chars,font=font,fill=255)
    ob=im.getbbox()
    if ob is None:continue
    w,h=ob[2]-ob[0],ob[3]-ob[1]
    if w<=(x1-x0-10) and h<=(y1-y0-10):
        fits.append((abs(h-145),-h,ppem,im,ob))
assert fits,"SOURCE_FAMILY_SIZE_CEILING_FAIL"
fits.sort(key=lambda x:x[:3])
_,_,ppem,layer,ob=fits[0]
layer=layer.crop(ob);lw,lh=layer.size
px=x0+6;py=y0+(y1-y0-lh)//2
assert px+lw<=x1-4 and py>=y0+4 and py+lh<=y1-4
# SOURCE->CLEAN is audited separately. Retain all other 3 labels exactly
# from the saved official candidate; composite glyph-only over transparent.
result=prev.copy()
result[y0:y1,x0:x1]=clean[y0:y1,x0:x1]
mask=np.asarray(layer,dtype=np.uint8)
roi=result[py:py+lh,px:px+lw]
roi[:,:,:3]=ink
roi[:,:,3]=mask
a=np.zeros((2048,2048),bool);a[y0:y1,x0:x1]=True
delta=np.any(result!=prev,axis=2)
assert int(np.count_nonzero(delta&~a))==0,"PROTECTED_ART_CHANGED"
alpha_yx=np.argwhere(result[y0:y1,x0:x1,3]>0)
assert len(alpha_yx)>0
miny,minx=alpha_yx.min(axis=0);maxy,maxx=alpha_yx.max(axis=0)+1
bbox=[x0+int(minx),y0+int(miny),x0+int(maxx),y0+int(maxy)]
assert bbox[0]>x0 and bbox[1]>y0 and bbox[2]<x1 and bbox[3]<y1,("OVERFLOW",bbox)
# Commit only experiment bytes to role_B (NOT hd_candidates).
raw=old[:128]+result[::-1][:,:,[2,1,0,3]].tobytes()
saved=O/"B365_Q176_FLAGMAN_NANUM_UNAPPROVED.dds"
saved.write_bytes(raw)
actual=decode(saved.read_bytes())
assert saved.read_bytes()[:128]==old[:128] and np.array_equal(actual,result),"PERSISTED_MISMATCH"
assert sha(raw)!=OFFICIAL_SHA
assert np.count_nonzero(np.any(actual!=prev,axis=2)&~a)==0
# SOURCE vs CLEAN must have zero changes outside canonical union of 4
# authored source regions (C371 exact evidence), and this pilot must not touch
# three sibling Korean labels or original ??? route art.
source_union=np.zeros((2048,2048),bool)
for b in [(8,49,988,204),(9,213,542,364),(0,374,838,532),(905,372,1745,532)]:
    l,t,r,bottom=b;source_union[t:bottom,l:r]=True
assert np.count_nonzero(np.any(src!=clean,axis=2)&~source_union)==0
comparisons=[]
for orientation in ["FLIPY","RAW"]:
    for bg,pct in ([(128,100),(0,75),(255,50)] if orientation=="FLIPY" else [(128,100)]):
        arrays=[src,clean,prev,actual]
        if orientation=="RAW":arrays=[v[::-1] for v in arrays]
        yy0,yy1=(y0-3,y1+3) if orientation=="FLIPY" else (2048-y1-3,2048-y0+3)
        imgs=[]
        for arr in arrays:
            z=Image.fromarray(arr[yy0:yy1,x0-3:x1+3].copy(),"RGBA")
            back=Image.new("RGBA",z.size,(bg,bg,bg,255));back.alpha_composite(z)
            img=back.convert("RGB")
            if pct!=100:img=img.resize((img.width*pct//100,img.height*pct//100),Image.Resampling.LANCZOS)
            imgs.append(img)
        w,h=imgs[0].size;sheet=Image.new("RGB",(w*4+30,h),(bg,bg,bg))
        for i,img in enumerate(imgs):sheet.paste(img,(i*(w+10),0))
        fn=f"B365_SOURCE_CLEAN_OFFICIAL_NANUM_{orientation}_BG{bg}_{pct}.png"
        sheet.save(O/fn);comparisons.append(fn)
Image.fromarray(np.where(delta,255,0).astype("uint8"),"L").save(O/"B365_CHANGED_MASK_NATIVE.png")
report={"run":"B365","role":"B","index":176,"candidate":"UNAPPROVED_SINGLE_FLAGMAN_ROW","source_sha256":SOURCE_SHA,"clean_sha256":CLEAN_SHA,
"official_sha256_unchanged":OFFICIAL_SHA,"trial_sha256":sha(raw),"font_sha256":sha(fb),"font_license":"Ubuntu fonts-nanum packaged open licensed font",
"font":str(fontpath),"font_glyph_coverage":"ALL_VERIFIED","native_ppem":ppem,"renderer":"Pillow FreeType BASIC native no outline no postscale",
"method_change":"Replace Noto CJK Bold synthetic 1-3px stroke family with authentic NanumGothicBold native geometric glyph contours and exact red source ink; preserve each glyph counter",
"bbox_original":list(bb),"bbox_trial":bbox,"native_wh":[2048,2048],"dds":"BGRA32_MIP1_RAW_MIRROR_Y",
"changed_rgba":int(delta.sum()),"outside_region":0,"roundtrip_difference":0,"other_three_labels_unchanged":True,
"plate_qa":"SOURCE_PINNED_AND_CLEAN_ALPHA_ZERO_FLAGMAN","producer_visual":"PENDING_FIRSTHAND_NATIVE",
"family_gate":"C2_NEW_PILOT_PENDING","whole_atlas":"C343_REWORK_UNCHANGED","C3":"NOT_RUN",
"RUNTIME_VALIDATION":"UNTESTED","official_promoted":0,"new_trial":1,"evidence":comparisons,"excluded":["VR","FFB","DX11","DXVK"]}
(O/"B365_MACHINE.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
(O/"recipe.json").write_text(json.dumps({"source":SOURCE_SHA,"clean":CLEAN_SHA,"trial":sha(raw),
"renderer":"Pillow native OpenType Sans NanumGothicBold","font":str(fontpath),"font_sha":sha(fb),
"font_size":ppem,"glyph":"플래그맨 4","source_bbox":list(bb),"new_bbox":bbox,
"color_source":ink.tolist(),"orientation":"RAW_MIRROR_Y","no_font_raster_rescale":True},indent=2,ensure_ascii=False)+"\n")
print(json.dumps({"run":"B365","trial_sha":sha(raw),"font":sha(fb),"bbox":bbox,"changed":int(delta.sum()),"outside":0}),flush=True)
