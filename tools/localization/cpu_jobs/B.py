#!/usr/bin/env python3
"""B268: authored B40 target-mask interior BC3 repair for q098."""
from pathlib import Path
import os, io, sys, json, hashlib, struct, urllib.request, tempfile, subprocess
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, distance_transform_edt

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("B268 requires pinned source download; GitHub worker only")
root=Path.cwd();gfx=root/"localization/graphics"
relative="textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
target=gfx/"hd_candidates"/relative
run=gfx/"role_B/20261008-B268-Q098-MASK-BOUND-WHITE-FACE"
run.mkdir(parents=True,exist_ok=True)
SHA=lambda b: hashlib.sha256(b).hexdigest()
old_sha="5ee0223fed4d6b9447157b285ff144ae470afb2e5f56244926feb866c84f6531"
src_sha="3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98","--require-safe-rerender"],capture_output=True,text=True,check=True)
triage=json.loads(tri.stdout)["assets"][0]
if triage["next_action"]!="MATERIAL_REWORK":
    raise RuntimeError(("q098 not material rework",triage))
oldbytes=target.read_bytes()
if SHA(oldbytes)!=old_sha:raise RuntimeError(("concurrent B production, stop",SHA(oldbytes)))
url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
"a95efe01d1f136514cef94b0d9e9fd61df021754/"
"Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds")
with tempfile.TemporaryDirectory(prefix="b266_q098_") as tmp:
    file=Path(tmp)/"stock.dds"
    urllib.request.urlretrieve(url,file)
    source=file.read_bytes()
if SHA(source)!=src_sha:raise RuntimeError(("English source SHA drift",SHA(source)))
w,h=struct.unpack_from("<II",oldbytes,16)[0],struct.unpack_from("<I",oldbytes,12)[0]
mips=struct.unpack_from("<I",oldbytes,28)[0]
if (w,h,mips,len(oldbytes))!=(2048,128,1,262272):raise RuntimeError("unexpected DDS dimensions/mip/bytes")
if oldbytes[:128]!=source[:128]:raise RuntimeError("DDS header changed")
if oldbytes[84:88]!=b"DXT5":raise RuntimeError("not DXT5")
def dec(b):return np.asarray(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
src=dec(source);cur=dec(oldbytes)
bbox=[431,6,1674,123];tgt=[580,11,1524,116]
Y,X=np.ogrid[:h,:w]
source_box=(X>=bbox[0])&(X<bbox[2])&(Y>=bbox[1])&(Y<bbox[3])
allowed=(X>=tgt[0])&(X<tgt[2])&(Y>=tgt[1])&(Y<tgt[3])
# Canonical 4x4 color block channels use BC1 RGB 565 endpoints plus 2bit/pixel
def rgb565(v):
    r=(v>>11)&31;g=(v>>5)&63;b=v&31
    return np.array([(r*255+15)//31,(g*255+31)//63,(b*255+15)//31],dtype=np.int32)
def palette(e0,e1):
    a,b=rgb565(e0),rgb565(e1)
    if e0>e1:
        return np.array([a,b,(2*a+b+1)//3,(a+2*b+1)//3])
    return np.array([a,b,(a+b+1)//2,np.array([0,0,0])])
# Mask authored during B40 Korean typesetting; do not guess lettering by
# expanding BC3 stippled seed patterns. All edits stay within inner face.
maskfile=gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_TARGET_TEXT_MASK.png"
mask=np.asarray(Image.open(maskfile).convert("L"),dtype=np.uint8)
if mask.shape!=(h,w):raise RuntimeError(("authored target mask size changed",mask.shape))
face_mask=(mask>212)&allowed
core=binary_erosion(face_mask,iterations=1)
rgb=cur[:,:,:3].astype(np.int16)
alpha=cur[:,:,3]
bright=(rgb[:,:,0]>=222)&(rgb[:,:,1]>=218)&(rgb[:,:,2]>=218)&(alpha>90)&allowed
seed_overlap=int(np.count_nonzero(bright&face_mask))
if seed_overlap<max(80,int(bright.sum()*0.35)):
    raise RuntimeError(("authored mask orientation or alignment mismatch",seed_overlap,int(bright.sum())))
repair=core & (alpha>=190) & ~bright
near=distance_transform_edt(~bright)
repair &= (near<=2.8)
if int(repair.sum())>20000:
    raise RuntimeError(("mask repair unexpectedly broad",int(repair.sum())))
if int(repair.sum())<10:
    raise RuntimeError(("no source-family compression pinholes detected",int(repair.sum())))
raw=bytearray(oldbytes)
block_w=w//4
touched=[];repaired=0;unsupported=0
# Raw scanlines are mirror-Y. Only 2-bit BC1 indices are changed; retain
# alpha endpoints/indices and chromatic endpoints byte-for-byte.
for y0 in range((tgt[1]//4)*4,((tgt[3]+3)//4)*4,4):
    for x0 in range((tgt[0]//4)*4,((tgt[2]+3)//4)*4,4):
        flags=repair[y0:y0+4,x0:x0+4]
        if not flags.any():continue
        raw_y0=h-y0-4
        if raw_y0<0:raise RuntimeError("raw flip coordinate invalid")
        ofs=128+((raw_y0//4)*block_w+(x0//4))*16
        end0,end1=struct.unpack_from("<HH",raw,ofs+8)
        pal=palette(end0,end1)
        whiteindex=int(np.argmin(np.sum((pal-np.array([255,255,255]))**2,axis=1)))
        if int(pal[whiteindex].min())<210:
            unsupported+=int(flags.sum())
            continue
        val=struct.unpack_from("<I",raw,ofs+12)[0]
        n=0
        for yi in range(4):
            for xi in range(4):
                if not flags[yi,xi]:continue
                raw_local_row=3-yi
                bit=2*(raw_local_row*4+xi)
                val=(val&~(3<<bit))|(whiteindex<<bit);n+=1
        struct.pack_into("<I",raw,ofs+12,val)
        if n:touched.append([x0,y0,n])
        repaired+=n
if repaired<10:raise RuntimeError(("no editable white palette blocks",repaired,unsupported))
new=bytes(raw)
if new==oldbytes:raise RuntimeError("no new compressed candidate")
if new[:128]!=oldbytes[:128] or len(new)!=len(oldbytes):raise RuntimeError("format mutated")
res=dec(new)
if np.any(res[:,:,3]!=cur[:,:,3]):raise RuntimeError("alpha changed, reject")
delta=np.any(res!=cur,axis=2)
outside=int(np.count_nonzero(delta & ~source_box))
outside_target=int(np.count_nonzero(delta & ~allowed))
if outside or outside_target:raise RuntimeError(("outside visible-text repair",outside,outside_target))
changed=int(delta.sum())
newrgb=res[:,:,:3].astype(np.int16)
newbright=(newrgb[:,:,0]>=222)&(newrgb[:,:,1]>=218)&(newrgb[:,:,2]>=218)&(res[:,:,3]>90)&allowed
improved=int(np.sum(repair&newbright))
if improved<10:raise RuntimeError(("white-stroke continuity did not improve",improved,repaired))
# Always verify original source-vs-candidate visible area has no new overflow
if int(np.count_nonzero((res[:,:,3]>16)&~source_box))!=int(np.count_nonzero((cur[:,:,3]>16)&~source_box)):
    raise RuntimeError("source extent changed")
target.write_bytes(new)
if SHA(target.read_bytes())!=SHA(new):raise RuntimeError("persist verification failed")
if not np.array_equal(dec(target.read_bytes()),res):raise RuntimeError("persist roundtrip mismatch")
# Small side-by-side independent pixel evidence with canonical source
# and old/new identical native dimensions, RAW plus FLIPY, 100/75/50.
for orientation in ("READABLE","RAW"):
    images=[src,cur,res] if orientation=="READABLE" else [np.flipud(i) for i in (src,cur,res)]
    y0,y1=(4,124) if orientation=="READABLE" else (4,124)
    for scale in (100,75,50):
        items=[]
        for idx,im in enumerate(images):
            tile=Image.fromarray(im[y0:y1,:,:],"RGBA")
            bg=Image.new("RGBA",tile.size,(75,75,75,255))
            bg.alpha_composite(tile)
            if scale!=100:bg=bg.resize((round(w*scale/100),round((y1-y0)*scale/100)),Image.Resampling.LANCZOS)
            items.append(bg.convert("RGB"))
        width=sum(x.width for x in items)+16; height=max(x.height for x in items)
        card=Image.new("RGB",(width,height),(92,92,92))
        x=0
        for im in items:card.paste(im,(x,0));x+=im.width+8
        card.save(run/f"{orientation}_SOURCE_PREVIOUS_REPAIRED_{scale}.png")
report={
 "run":"B268","queue_index":98,"asset":"42E618FD","run_key":"OUTRUN-KOR-B268-Q098-MASKFACE-20261008",
 "status":"B268_MATERIAL_CANDIDATE_PENDING_CONTROLLER_VISUAL",
 "source_sha256":src_sha,"old_candidate_sha256":old_sha,"new_candidate_sha256":SHA(new),
 "repair_kind":"AUTHORED_TARGET_MASK_BC3_CORE_FACE_WHITEN_NO_ALPHA_CHANGE",
 "canonical_source_bbox":bbox,"prior_localized_bbox":[580,11,1524,116],
 "native_size":[w,h],"dds":"BC3/DXT5 mip1 mirror_y",
 "repair_seed_bright_count":int(bright.sum()),"authored_mask_sha256":SHA(maskfile.read_bytes()),"authored_white_seed_overlap":seed_overlap,"target_face_mask_pixels":int(face_mask.sum()),"white_pinhole_proposals":int(repair.sum()),
 "repaired_indices":repaired,"unsupported_gray_pinholes":unsupported,
 "white_face_pixels_recovered":improved,"BC3_blocks_modified":len(touched),
 "modified_blocks":touched[:250],"changed_rgba_pixels":changed,
 "changed_rgba_outside_source_bbox":outside,"changed_rgba_outside_target_bbox":outside_target,
 "alpha_exact":True,"header_exact":True,"persisted_DDS_roundtrip_exact":True,
 "producer_visual":"PENDING_CONTROLLER_NATIVE_AND_50_PERCENT",
 "independent_C":"NOT_RUN","C3":"NOT_RUN","PRE_INGAME":"BLOCKED","RUNTIME_VALIDATION":"UNTESTED",
 "backend":"GITHUB_ACTIONS_PINNED_DDS_FALLBACK_UNAVAILABLE_GPT_LOCAL_RAW_GITHUB_DNS",
 "cleanup":"runner ephemeral, no N100 heavy work","prohibited_domains_touched":[]
}
(run/"B268_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"sha":SHA(new),"repaired":repaired,"white_recovered":improved,"blocks":len(touched),"outside":outside,"target_outside":outside_target},ensure_ascii=False))
