#!/usr/bin/env python3
"""B283 q098: new source-conditioned soft-navy-effect trial; NEVER auto-promote."""
import os,io,sys,json,struct,hashlib,urllib.request,tempfile,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter, binary_dilation
if os.getenv("OUTRUN_CPU_WORKER")!="github-actions" or os.getenv("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B283 source fetch requires remote runner; not for unqualified automatic promotion")
root=Path.cwd(); gfx=root/"localization/graphics"
rel="textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
dest=gfx/"hd_candidates"/rel
run=gfx/"role_B/20261009-B283-Q098-NATIVE-PRESERVED-FACE-SOFT-HALO";run.mkdir(parents=True,exist_ok=True)
sha=lambda data:hashlib.sha256(data).hexdigest()
source_sha="3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59"
old_sha="192d627428dfa4328035d5105dcfbd4395d8bbadfa154a9f533a1c48583eac4b"
clean_sha="b5c9c07a2490abd055153f750b415193eb84ef14c298b3e3873fd915db3af9e8"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98","--require-safe-rerender"],capture_output=True,text=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK","q098 is not a current material rework"
old=dest.read_bytes()
assert sha(old)==old_sha,("q098 remote producer collision",sha(old))
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
with tempfile.TemporaryDirectory(prefix="b283_github_src_") as tmp:
    p=Path(tmp)/"pinned_source.dds";urllib.request.urlretrieve(source_url,p);eng=p.read_bytes()
assert sha(eng)==source_sha
assert eng[:128]==old[:128] and old[84:88]==b"DXT5"
width=struct.unpack_from("<I",old,16)[0];height=struct.unpack_from("<I",old,12)[0];mips=struct.unpack_from("<I",old,28)[0]
assert (width,height,mips,len(old))==(2048,128,1,262272)
def decode(b):return np.asarray(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
source=decode(eng);current=decode(old)
cleanfile=gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_CLEAN_PLATE.png"
maskfile=gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_TARGET_TEXT_MASK.png"
assert sha(cleanfile.read_bytes())==clean_sha
clean=np.asarray(Image.open(cleanfile).convert("RGBA"),dtype=np.uint8)
mask=np.asarray(Image.open(maskfile).convert("L"),dtype=np.uint8)
assert source.shape==current.shape==clean.shape==(128,2048,4) and mask.shape==(128,2048)
srcbbox=[431,6,1674,123];visible_source_bbox=[434,9,1671,120];editbbox=[564,12,1540,116] # exact native English bounds, nonprotected
y,x=np.ogrid[:height,:width]
srcmask=(x>=srcbbox[0])&(x<srcbbox[2])&(y>=srcbbox[1])&(y<srcbbox[3])
editmask=(x>=editbbox[0])&(x<editbbox[2])&(y>=editbbox[1])&(y<editbbox[3])
assert not np.any((source!=clean).any(axis=2)&~srcmask),"English CLEAN unexpected changed outside exact English"
assert not np.any((current!=clean).any(axis=2)&~srcmask),"prior target outside English"
assert (clean[:,:,3][srcmask]==0).all(),"source lettering not erased in clean"
# Extract original source's WHITE:navy layer coloring *and* soft halo profile.
srgb=source[:,:,:3]
salpha=source[:,:,3]
sface=(srgb[:,:,0]>=235)&(srgb[:,:,1]>=235)&(srgb[:,:,2]>=235)&(salpha>=190)&srcmask
snavy=(srgb[:,:,0]<36)&(srgb[:,:,1]<65)&(srgb[:,:,2]>srgb[:,:,0]+12)&(salpha>=140)&srcmask
assert sface.sum()>20000 and snavy.sum()>30000
white=np.percentile(srgb[sface],90,axis=0).round().astype(int)
navy=np.percentile(srgb[snavy],30,axis=0).round().astype(int)
assert (white.tolist(),navy.tolist())==([255,255,255],[0,12,57]),(white,navy)
# The source includes a thick navy aura beyond white ink: the earlier B279
# script only recolored existing compressed pixels; it never authored a glow.
# Resize the *source-authored* Korean glyph silhouette vertically, leaving room
# under the original height ceiling for separate navy outline+diffusion.
# Native geometry source is the CURRENT B279 decoded text ink only. No
# stretching, no target B40 broad mask, no background from previous DDS.
# Rebuild source-conditioned ink/halo on exact canonical CLEAN: B282's
# enlarged hard 6px ring crowded Hangul counters, so this uses only the
# original visible shape and a soft alpha diffusion.
prior_alpha=current[:,:,3].astype(np.float32)/255.0
prior_min=current[:,:,:3].min(axis=2).astype(np.float32)
prior_white=np.clip((prior_min-138.0)/105.0,0.0,1.0)*prior_alpha
# Restrict ink to pixels that existed as white in the persisted B279
# candidate, not all authored glyph area. The face border is source-navy.
white_seed=(prior_min>=215)&(prior_alpha>=0.46)
face_depth=distance_transform_edt(white_seed)
inset=np.clip((face_depth-0.7)/1.7,0,1)
white_alpha=np.clip(prior_white*inset*0.98,0,1)
# Use the previously visible, native glyph alpha for solid navy boundaries;
# a low-amplitude gaussian extends source-derived *diffuse* navy just beyond
# it, without the prior hard-dilation that merges adjacent Hangul glyphs.
glow=gaussian_filter((prior_alpha>0.08).astype(np.float32),sigma=2.45)
soft_alpha=np.clip((glow-0.03)/0.97,0,1)*0.44
key_alpha=np.maximum(prior_alpha*0.94,soft_alpha)
target_alpha=key_alpha+white_alpha*(1-key_alpha)
# Prior candidate had a smooth continuous face; recreate full white mask, not
# BC3 index-only pore filling, and blend navy halo only where justified.
result=np.asarray(clean.copy(),dtype=np.uint8)
rgba=np.zeros((height,width,4),dtype=np.uint8)
rgb=(np.asarray(navy,np.float32)[None,None,:]*(1-white_alpha[...,None])+np.asarray(white,np.float32)[None,None,:]*white_alpha[...,None])
rgba[:,:,:3]=np.clip(np.rint(rgb),0,255).astype(np.uint8)
rgba[:,:,3]=np.clip(np.rint(target_alpha*255),0,255).astype(np.uint8)
# Hard native source bbox guard and exact target region; keep antialias vanishing
# beyond full 4x4 editable blocks to avoid changing protected source pixels.
rgba[~editmask]=0
rgba[rgba[:,:,3]<10]=0
result[editmask]=rgba[editmask]
# Completely transparent plate must remain transparent; no foreign patches.
if np.any(result[:,:,3][~srcmask]):raise RuntimeError("target escapes canonical source bbox")
if not np.any((result[:,:,3]>16)&editmask):raise RuntimeError("no visible Korean glyph")
def pack565(c):
    return ((int(c[0])*31+127)//255<<11)|((int(c[1])*63+127)//255<<5)|((int(c[2])*31+127)//255)
def rgb565(v):
    return np.array([(((v>>11)&31)*255+15)//31,(((v>>5)&63)*255+31)//63,((v&31)*255+15)//31],dtype=np.int32)
hi=pack565(white);lo=pack565(navy)
assert hi>lo
col=np.array([rgb565(hi),rgb565(lo)],dtype=np.int32)
pal=np.array([col[0],col[1],(2*col[0]+col[1]+1)//3,(col[0]+2*col[1]+1)//3],dtype=np.int32)
raw=bytearray(old); touched=0; alpha_touched=0
def palalpha(a0,a1):
    if a0>a1: return np.array([a0,a1]+[((7-i)*a0+i*a1+3)//7 for i in range(1,7)],dtype=np.int32)
    return np.array([a0,a1]+[((5-i)*a0+i*a1+2)//5 for i in range(1,5)]+[0,255],dtype=np.int32)
# Blocks inside source + target edit scope only. Each pixel's nearest decoded
# color/alpha palette is solved with INT32 arithmetic (fixes B276 overflow).
for by in range(8,116,4):
    for bx in range(564,1540,4):
        if bx<srcbbox[0] or bx+4>srcbbox[2] or by<srcbbox[1] or by+4>srcbbox[3]:
            continue
        sub=result[by:by+4,bx:bx+4,:]
        old_sub=current[by:by+4,bx:bx+4,:]
        if not np.any(sub!=old_sub):continue
        a=sub[:,:,3].astype(np.int32)
        a0=max(1,int(a.max()));a1=int(a.min())
        if a0<=a1:a0=min(255,a1+1)
        ap=palalpha(a0,a1)
        ai=np.argmin(np.abs(a[:,:,None]-ap[None,None,:]),axis=2)
        c=sub[:,:,:3].astype(np.int32)
        ci=np.argmin(np.sum((c[:,:,None,:]-pal[None,None,:,:])**2,axis=3),axis=2)
        abits=0;cbits=0
        for iy in range(4):
            for ix in range(4):
                local=3-iy
                abits|=int(ai[iy,ix])<<(3*(4*local+ix))
                cbits|=int(ci[iy,ix])<<(2*(4*local+ix))
        offset=128+(((height-by-4)//4)*(width//4)+(bx//4))*16
        raw[offset:offset+8]=bytes((a0,a1))+abits.to_bytes(6,"little")
        struct.pack_into("<HHI",raw,offset+8,hi,lo,cbits)
        touched+=1
# Reconcile old candidate's 1-row top edge by alpha-only patch without
# recoloring the adjacent row8 outside exact canonical source bbox.
for by in (8,):
    for bx in range(580,1524,4):
        offset=128+(((height-by-4)//4)*(width//4)+(bx//4))*16
        before=bytes(raw[offset:offset+8]);prev=current[by:by+4,bx:bx+4,3]
        changed=np.any(prev[3,:]!=0)
        if not np.any(changed):continue
        a=prev.copy();a[3,:]=0
        a0=int(a.max());a1=int(a.min())
        if a0<=a1:a0=min(255,a1+1)
        ap=palalpha(a0,a1);ii=np.argmin(np.abs(a.astype(np.int32)[:,:,None]-ap[None,None,:]),axis=2)
        bits=0
        for iy in range(4):
            for ix in range(4):bits|=int(ii[iy,ix])<<(3*(4*(3-iy)+ix))
        raw[offset:offset+8]=bytes([a0,a1])+bits.to_bytes(6,"little")
        if before!=raw[offset:offset+8]:alpha_touched+=1
if touched<1500:raise RuntimeError(("too few changed BC3 blocks",touched))
trial=bytes(raw)
assert trial[:128]==old[:128] and len(trial)==len(old)
native=decode(trial)
delta=np.any(native!=current,axis=2)
outside_src=int(np.count_nonzero(delta&~srcmask))
# Pixel-exact zero changes outside English source, across ALL RGBA components.
if outside_src: raise RuntimeError(("source bbox escape",outside_src))
out_alpha=int(np.count_nonzero(native[:,:,3][~srcmask]>16))
if out_alpha:raise RuntimeError(("visible alpha outside source",out_alpha))
# Clean-to-final target permitted effect includes outer halo, never beyond
# original English bounds. Original English has max 111px actual effect height.
newpos=native[:,:,3]>16
ys,xs=np.nonzero(newpos)
if not len(xs):raise RuntimeError("empty trial")
nbbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
if not(nbbox[0]>=visible_source_bbox[0] and nbbox[1]>=visible_source_bbox[1] and nbbox[2]<=visible_source_bbox[2] and nbbox[3]<=visible_source_bbox[3]):
    raise RuntimeError(("source extent escape",nbbox))
old_white=int(np.count_nonzero((current[:,:,0]>230)&(current[:,:,1]>230)&(current[:,:,2]>230)&(current[:,:,3]>175)&srcmask))
new_white=int(np.count_nonzero((native[:,:,0]>230)&(native[:,:,1]>230)&(native[:,:,2]>230)&(native[:,:,3]>175)&srcmask))
new_navy=int(np.count_nonzero((native[:,:,2]>native[:,:,0]+12)&(native[:,:,3]>140)&srcmask))
source_navy=int(np.count_nonzero((source[:,:,2]>source[:,:,0]+12)&(source[:,:,3]>140)&srcmask))
if new_white<9000 or new_navy<12000:raise RuntimeError(("glyph/glow erased",new_white,new_navy))
# C310 regression gate: do not hand C2 a candidate with the same oversized
# white-face vs navy-support dominance as rejected B279 (ratio >2.0).
if new_white / max(1,new_navy) > 1.25:raise RuntimeError(("source-family white dominance C310 recurrence",new_white,new_navy))
tfile=run/"42E618FD_B283_TRIAL_NOT_APPROVED.dds";tfile.write_bytes(trial)
assert sha(tfile.read_bytes())==sha(trial) and np.array_equal(decode(tfile.read_bytes()),native)
# Individual lossless decoded plate/final evidence, plus four panels
Image.fromarray(native,"RGBA").save(run/"B283_PERSISTED_READABLE_RGBA.png")
Image.fromarray(np.flipud(native),"RGBA").save(run/"B283_PERSISTED_RAW_RGBA.png")
Image.fromarray(clean,"RGBA").save(run/"B283_PLATE_ONLY_RGBA.png")
for direction in ("READABLE","RAW"):
    ims=(source,clean,current,native) if direction=="READABLE" else tuple(np.flipud(z) for z in (source,clean,current,native))
    for back,bgc in (("WHITE",(255,255,255,255)),("GRAY",(72,72,72,255)),("BLACK",(0,0,0,255))):
        for scale in (100,75,50):
            chunks=[]
            for a in ims:
                canvas=Image.new("RGBA",(width,height),bgc);canvas.alpha_composite(Image.fromarray(a,"RGBA"))
                if scale!=100:canvas=canvas.resize((int(width*scale/100),int(height*scale/100)),Image.Resampling.LANCZOS)
                chunks.append(canvas.convert("RGB"))
            panel=Image.new("RGB",(sum(z.width for z in chunks)+12,max(z.height for z in chunks)),(87,87,87))
            left=0
            for z in chunks:panel.paste(z,(left,0));left+=z.width+4
            panel.save(run/f"B283_{direction}_{back}_{scale}_EN_CLEAN_B279_TRIAL.png",optimize=True)
report={"run":"B283","index":98,"asset":"42E618FD_512x32.dds","source_sha256":source_sha,"clean_png_sha256":clean_sha,"previous_sha256":old_sha,"trial_sha256":sha(trial),"method":"NATIVE_NEW_BC3_NATIVE_B279_SEPARATE_WHITE_FACE_INSET_AND_SOFT_NAVY_HALO_WITH_EXACT_ENGLISH_CLEAN","method_not_same_as_B279":True,"source_family":{"white_rgb":white.tolist(),"navy_rgb":navy.tolist(),"english_white_support":int(sface.sum()),"english_navy_support":int(snavy.sum()),"source_navy_alpha_gt140":source_navy,"render_vertical_glyph_scale":1.0,"navy_outline_radius":"NATIVE_EXISTING_KEYLINE_ONLY","navy_diffuse_sigma":2.45,"glyph_mask_only":"B279_NATIVE_DECODED_WHITE_FACE_NO_UPSCALING"},"format":"BC3_DXT5","native":[width,height],"mips":mips,"raw_orientation":"mirror_y","machine":{"blocks_reencoded":touched,"alpha_only_cleanup_blocks":alpha_touched,"changed_rgba_pixels":int(delta.sum()),"outside_exact_english_source":outside_src,"original_alpha_residue_in_clean":0,"decoded_bbox":nbbox,"source_effect_rgba_scope":srcbbox,"source_visible_alpha_bbox":visible_source_bbox,"previous_white_count":old_white,"trial_white_count":new_white,"trial_navy_count":new_navy,"white_navy_ratio":round(new_white/max(new_navy,1),3),"dds_header_exact":True,"roundtrip_persisted_dds":True},"visual_producer":"PENDING_PIXELS_FIRST_SOURCE_CLEAN_B279_TRIAL_NATIVE_AND_50","candidate_promoted":False,"independent_C2":"NOT_RUN","C3":"NOT_RUN","USER":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED","backend":"GITHUB_HOSTED_CANONICAL_PUBLIC_SOURCE_DNS_DEPENDENCY_NO_GPT_LOCAL_NETWORK","forbidden_domains_touched":[]}
(run/"B283_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"trial":sha(trial),"changed":int(delta.sum()),"white":new_white,"navy":new_navy,"bbox":nbbox},ensure_ascii=False))
