from pathlib import Path
import struct, json, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
p=Path("work/c1_q121_a234r_20261011_0640")
names=["source","official","trial"]
dds={}
meta={}
for name in names:
    f=p/(name+".dds"); b=f.open("rb").read(128)
    assert b[:4]==b"DDS ",(name,b[:4])
    height,width=struct.unpack_from("<II",b,12)
    mip=struct.unpack_from("<I",b,28)[0]
    assert (width,height,mip)==(4096,4096,1),(name,width,height,mip)
    dds[name]=np.memmap(f,dtype=np.uint8,mode="r",offset=128,shape=(height,width,4))
    meta[name]={"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"w":width,"h":height,"mip_count":mip,"size":f.stat().st_size,"pixel_format_raw":"RGBA32","header_sha256":hashlib.sha256(b).hexdigest()}
roi=[3490,391,3722,440]
L,T,R,B=roi
def rgba(name,area,flip=True):
    l,t,r,b=area
    block=dds[name][4096-b:4096-t,l:r,:][::-1] if flip else dds[name][t:b,l:r,:]
    return np.array(block,copy=True)
original_png=np.asarray(Image.open(p/"source_native.png").convert("RGBA"))
trial_png=np.asarray(Image.open(p/"producer_final_native.png").convert("RGBA"))
plate_png=np.asarray(Image.open(p/"clean_native.png").convert("RGBA"))
candidate_readable=rgba("trial",roi)
source_readable=rgba("source",roi)
source_raw=rgba("source",roi,False)
trial_raw=rgba("trial",roi,False)
orientation_samples={
"source_readable_mismatch":int(np.any(source_readable!=original_png,axis=2).sum()),
"source_raw_mismatch":int(np.any(source_raw!=original_png,axis=2).sum()),
"trial_readable_mismatch":int(np.any(candidate_readable!=trial_png,axis=2).sum()),
"trial_raw_mismatch":int(np.any(trial_raw!=trial_png,axis=2).sum()),
"clean_dimensions":list(plate_png.shape)}
# Changed-pixel map official -> new across full atlas (scanning raw BGRA in 128 row strips)
changed=alpha=outside=outside_alpha=0
bbox=None
for y0 in range(0,4096,128):
    old=np.array(dds["official"][y0:y0+128])
    new=np.array(dds["trial"][y0:y0+128])
    mask=np.any(old!=new,axis=2)
    amask=old[:,:,3]!=new[:,:,3]
    ch=int(mask.sum());changed+=ch;alpha+=int(amask.sum())
    if ch:
        ys,xs=np.where(mask)
        bb=(int(xs.min()),y0+int(ys.min()),int(xs.max()+1),y0+int(ys.max()+1))
        bbox=bb if bbox is None else (min(bbox[0],bb[0]),min(bbox[1],bb[1]),max(bbox[2],bb[2]),max(bbox[3],bb[3]))
    # readable ROI in raw is x 3490:3722, y 3656:3705
    allowed=np.zeros_like(mask,dtype=bool)
    lo=max(y0,4096-B);hi=min(y0+128,4096-T)
    if hi>lo: allowed[lo-y0:hi-y0,L:R]=True
    outside+=int((mask&~allowed).sum());outside_alpha+=int((amask&~allowed).sum())
def bboxalpha(a):
    yy,xx=np.where(a[:,:,3]>0)
    return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)] if len(xx) else None
def counts(a):
    return {"opaque":int((a[:,:,3]==255).sum()),"positive_alpha":int((a[:,:,3]>0).sum()),"alpha_sum":int(a[:,:,3].astype("uint64").sum()),"alpha_bbox_local":bboxalpha(a)}
def maskdiff(a,b):return int(np.any(a!=b,axis=2).sum())
orig_vs_plate=maskdiff(source_readable,plate_png)
full_source_roi_rgba_diff=maskdiff(source_readable,candidate_readable)
clean_final_roi_rgba_diff=maskdiff(plate_png,candidate_readable)
original_bbox=bboxalpha(source_readable)
final_bbox=bboxalpha(candidate_readable)
if original_bbox and final_bbox:
  allowedalpha=np.zeros((B-T,R-L),dtype=bool);l,t,r,b=original_bbox;allowedalpha[t:b,l:r]=True
  alpha_outside=int(((candidate_readable[:,:,3]>0)&~allowedalpha).sum())
else:alpha_outside=-1
machine={
"source_path":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds",
"candidate_path":"localization/graphics/role_A/20261011-A234R-Q121-RANK20-SOURCE-PLATE-VISIBLE-ALPHA/A234_Q121_RANK20_REBUILT_SOURCE_PLATE_UNPROMOTED.dds",
"official_path":"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds",
"files":meta,
"region_READABLE":roi,"region_RAW":[L,4096-B,R,4096-T],
"orientation_checks":orientation_samples,
"official_to_trial_full_atlas_changed_RGBA":changed,
"official_to_trial_full_atlas_changed_ALPHA":alpha,
"official_to_trial_CHANGED_bbox_RAW":bbox,
"outside_exact_source_roi_RGBA":outside,
"outside_exact_source_roi_ALPHA":outside_alpha,
"source_english_ROI":counts(source_readable),
"saved_trial_korean_ROI":counts(candidate_readable),
"authored_CLEAN_roi":counts(plate_png),
"source_to_clean_changed_ROI":orig_vs_plate,
"clean_to_final_changed_ROI":clean_final_roi_rgba_diff,
"source_to_final_changed_ROI":full_source_roi_rgba_diff,
"candidate_visible_alpha_outside_source_glyph_bbox":alpha_outside,
"candidate_pixel_bbox_inside_source_positive_margin":final_bbox is not None and original_bbox is not None and all([final_bbox[0]>original_bbox[0],final_bbox[1]>original_bbox[1],final_bbox[2]<original_bbox[2],final_bbox[3]<original_bbox[3]]),
"runtime_validation":"UNTESTED","not_claimed":"whole-atlas C approval; actual game compositor; C3"}
(p/"INDEPENDENT_MACHINE.json").write_text(json.dumps(machine,indent=2,ensure_ascii=False)+"\n")
# independently render exact persisted bytes without accepting producer's visual panels
def over(a,bg):
    out=Image.new("RGBA",(R-L,B-T),bg)
    out.alpha_composite(Image.fromarray(a,"RGBA"))
    return out.convert("RGB")
for color,c in [("GRAY",(116,116,116,255)),("BLACK",(0,0,0,255)),("WHITE",(255,255,255,255))]:
    imgs=[over(x,c) for x in [source_readable,plate_png,rgba("official",roi),candidate_readable]]
    for scale in [100,75,50]:
        w=max(1,round((R-L)*scale/100));h=max(1,round((B-T)*scale/100))
        dest=Image.new("RGB",(w*4,max(40,h+21)),(231,231,231));draw=ImageDraw.Draw(dest)
        for j,im in enumerate(imgs):
            if scale!=100: im=im.resize((w,h),Image.Resampling.LANCZOS)
            dest.paste(im,(j*w,20))
            draw.text((j*w+4,4),("SOURCE","CLEAN","OFFICIAL","A234R")[j],fill=(0,0,0))
        dest.save(p/f"C1_SOURCE_CLEAN_OFFICIAL_A234R_{color}_{scale}.png",optimize=True)
raw_contact=Image.new("RGB",((R-L)*4,70),(224,224,224));dr=ImageDraw.Draw(raw_contact)
for j,n in enumerate(["source","official","trial"]):
    im=over(rgba(n,roi,False),(100,100,100,255))
    raw_contact.paste(im,(j*(R-L),20))
    dr.text((j*(R-L)+4,4),n.upper()+" RAW same ROI",fill=(0,0,0))
raw_contact.save(p/"C1_RAW_COMPARE.png")
print(json.dumps(machine,ensure_ascii=False))