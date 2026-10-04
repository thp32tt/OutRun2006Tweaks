#!/usr/bin/env python3
import hashlib, json, os, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C140-31C58963"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds"
cand_path=repo/"localization/graphics/hd_candidates"/asset
bdir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION58"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="2da84d800f3df0606df148c353f25c2f25a47573"
ATLAS_BLOB_SHA1="7829c90426d563960440dd70b9b7ae74b3b76c0d"
SOURCE_SHA256="ae048d04fef96108f6ee30c41022aedb78083d76386448df5483ae0ccd083dcd"
INPUT_CANDIDATE_SHA256="b6d8bcc2f2cc05d45d4af3fbfab30f0a71e8fa68a89dee4c78b6f8a6aeca4cd3"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT

tmp=Path("/tmp/outrun_C140"); tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"; apath=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds",sp)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_31C58963_512x256_atlas.json",apath)

def blob_sha(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def rect(shape,b):
    h,w=shape; x0,y0,x1,y1=map(int,b)
    m=np.zeros((h,w),bool); m[y0:y1,x0:x1]=1; return m
def dil(m,px=1):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(px*2+1)))>0
def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=sp.read_bytes(); ab=apath.read_bytes(); ib=cand_path.read_bytes()
if blob_sha(sb)!=SOURCE_BLOB_SHA1 or blob_sha(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError("pinned source/atlas blob mismatch")
if sha(sb)!=SOURCE_SHA256 or sha(ib)!=INPUT_CANDIDATE_SHA256: raise RuntimeError(("sha mismatch",sha(sb),sha(ib)))
if sb[:128]!=ib[:128]: raise RuntimeError("input header mismatch")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(2048,1024,8192,1) or len(sb)!=128+W*H*4 or len(ib)!=len(sb): raise RuntimeError("structure")
masks=(pf[4],pf[5],pf[6])
RAWMODE="RGBA" if masks==(0xff,0xff00,0xff0000) else "BGRA" if masks==(0xff0000,0xff00,0xff) else None
if not RAWMODE: raise RuntimeError(("rawmode",masks))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE)
raw_input=Image.frombytes("RGBA",(W,H),ib[128:],"raw",RAWMODE)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
inp=raw_input.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); ia=np.asarray(inp,dtype=np.uint8)

atlas=json.loads(ab.decode("utf-8")); regions={int(r["idx"]):r["rect"] for r in atlas["regions"]}
expected={0:[0,864,1760,160],1:[0,704,1760,160],2:[0,544,1760,160],3:[0,384,1760,160],4:[0,308,744,76]}
if regions!=expected: raise RuntimeError(("atlas drift",regions))

sem=[(0,"SELECT STAGE","스테이지 선택"),(1,"SELECT RACE","레이스 선택"),(2,"SELECT MODE","모드 선택"),(3,"SHOWROOM","쇼룸")]
source_masks=[]; allowed_masks=[]; rows=[]
for idx,en,ko in sem:
    x,y,cw,ch=regions[idx]; local=sa[y:y+ch,x:x+cw,3]>0; bb=bbox(local)
    if not bb: raise RuntimeError(("empty",idx))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    sm=np.zeros((H,W),bool); sm[y:y+ch,x:x+cw]=local
    source_masks.append(sm); allowed_masks.append(rect((H,W),ob))
    rows.append({"key":f"region_{idx}","region_idx":idx,"source":en,"korean":ko,"original_bbox":ob})

# Canonical region 4 has exactly three 8-connected alpha groups:
# PRESS | Enter-key icon | KEY. This independently discovers the exact word
# effect bboxes and catches any producer range that clipped source fringe.
x,y,cw,ch=regions[4]; local=sa[y:y+ch,x:x+cw,3]>0
lab,num=ndimage.label(local,np.ones((3,3),dtype=np.uint8))
groups=[]
for i in range(1,num+1):
    yy,xx=np.nonzero(lab==i)
    if len(xx)<3: continue
    gm_local=(lab==i); bb=bbox(gm_local)
    gm=np.zeros((H,W),bool); gm[y:y+ch,x:x+cw]=gm_local
    groups.append({"id":i,"mask":gm,"bbox":[x+bb[0],y+bb[1],x+bb[2],y+bb[3]],"pixels":int(len(xx))})
groups.sort(key=lambda g:g["bbox"][0])
if len(groups)!=3: raise RuntimeError(("compound groups",[(g["bbox"],g["pixels"]) for g in groups]))
left,icon,right=groups
if not(left["bbox"][2]<icon["bbox"][0]<icon["bbox"][2]<right["bbox"][0]) or icon["pixels"]<1000: raise RuntimeError("compound ordering")
for key,en,ko,g in [("press_word","PRESS","누르세요",left),("key_word","KEY","키",right)]:
    source_masks.append(g["mask"]); allowed_masks.append(rect((H,W),g["bbox"]))
    rows.append({"key":key,"region_idx":4,"source":en,"korean":ko,"original_bbox":g["bbox"]})

source_mask=np.logical_or.reduce(source_masks); allowed=np.logical_or.reduce(allowed_masks); icon_mask=icon["mask"]
protected=(sa[:,:,3]>0)&~source_mask
expected_clean=sa.copy(); expected_clean[source_mask]=0
bclean=np.asarray(Image.open(bdir/"31C_HD_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
producer_clean_diff=np.any(bclean!=expected_clean,axis=2)
producer_clean_diff_pixels=int(np.count_nonzero(producer_clean_diff))
producer_clean_diff_bbox=bbox(producer_clean_diff)
# The B58 clean plate is expected to expose a clipped KEY fringe here. This is
# a concrete C defect, not a reason to abandon the run; C may make a small fix.
if producer_clean_diff_pixels<=0: raise RuntimeError("expected independent defect disappeared")
if np.count_nonzero(producer_clean_diff & ~source_mask): raise RuntimeError(("clean diff outside exact source mask",bbox(producer_clean_diff)))

# Derive actual Korean render masks from B58 input-vs-B58 clean delta, rather
# than treating all candidate alpha as target (which would misclassify residue).
b_render=np.any(ia!=bclean,axis=2)
target_masks=[]; row_results=[]
for r,am in zip(rows,allowed_masks):
    tm=b_render & am
    lb=bbox(tm)
    if not lb: raise RuntimeError(("missing target",r["key"]))
    ob=r["original_bbox"]; sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    if lw>sw or lh>sh or min(d)<=0: raise RuntimeError(("bbox",r["key"],ob,lb,d))
    target_masks.append(tm)
    row_results.append({**r,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})
target=np.logical_or.reduce(target_masks)

# C140 small corrective rework: remove exact canonical source-effect residue
# outside Korean target masks. For RGBA32 transparent background this is exact.
input_residue=source_mask & ~target & np.any(ia!=expected_clean,axis=2)
input_residue_pixels=int(np.count_nonzero(input_residue))
input_residue_bbox=bbox(input_residue)
if input_residue_pixels!=producer_clean_diff_pixels or input_residue_bbox!=producer_clean_diff_bbox:
    raise RuntimeError(("residue/clean mismatch",input_residue_pixels,input_residue_bbox,producer_clean_diff_pixels,producer_clean_diff_bbox))
fixed=ia.copy(); fixed[input_residue]=expected_clean[input_residue]
fix_delta=np.any(fixed!=ia,axis=2)
if np.count_nonzero(fix_delta)!=input_residue_pixels or np.count_nonzero(fix_delta&~input_residue): raise RuntimeError("fix scope escaped residue")
final=Image.fromarray(fixed,"RGBA"); raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",RAWMODE); cand_path.write_bytes(payload); out_sha=sha(payload)
if payload[:128]!=sb[:128]: raise RuntimeError("output header")
dec_raw=Image.frombytes("RGBA",(W,H),payload[128:],"raw",RAWMODE); dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da=np.asarray(dec,dtype=np.uint8)
if np.any(da!=fixed): raise RuntimeError("roundtrip")

final_diff=np.any(da!=sa,axis=2); alpha_diff=da[:,:,3]!=sa[:,:,3]
outside=int(np.count_nonzero(final_diff&~allowed)); alpha_out=int(np.count_nonzero(alpha_diff&~allowed))
protected_changed=int(np.count_nonzero(final_diff&protected)); icon_changed=int(np.count_nonzero(final_diff&icon_mask))
render_diff=np.any(da!=expected_clean,axis=2)
render_out=int(np.count_nonzero(render_diff&~target))
source_residue=int(np.count_nonzero(source_mask&~target&np.any(da!=expected_clean,axis=2)))
if outside or alpha_out or protected_changed or icon_changed or render_out or source_residue:
    raise RuntimeError(("final gates",outside,alpha_out,protected_changed,icon_changed,render_out,source_residue))

overlap=0; touch=[]
for i in range(len(target_masks)):
  for j in range(i+1,len(target_masks)):
    ov=int(np.count_nonzero(target_masks[i]&target_masks[j]))
    near=int(np.count_nonzero(dil(target_masks[i],1)&target_masks[j]))
    overlap+=ov
    if ov or near: touch.append([rows[i]["key"],rows[j]["key"],ov,near])
if overlap or touch: raise RuntimeError(("overlap",overlap,touch))
icon_near={}
for i in [4,5]:
    n=int(np.count_nonzero(dil(target_masks[i],1)&icon_mask)); icon_near[rows[i]["key"]]=n
    if n: raise RuntimeError(("icon touch",rows[i]["key"],n))

# Style sanity.
style={}
for i,r in enumerate(row_results):
    px=da[target_masks[i]]
    if i<4:
        frac=float(np.mean((px[:,0]>=240)&(px[:,1]>=240)&(px[:,2]>=240)))
        style[r["key"]]={"near_white_fraction":frac}
        if frac<0.80: raise RuntimeError(("white style",r["key"],frac))
    else:
        yellow=int(np.count_nonzero((px[:,0]>=170)&(px[:,1]>=90)&(px[:,2]<=100)))
        dark=int(np.count_nonzero((px[:,0]<=70)&(px[:,1]<=70)&(px[:,2]<=70)))
        style[r["key"]]={"yellow_pixels":yellow,"dark_outline_pixels":dark}
        if yellow<50 or dark<50: raise RuntimeError(("compound style",r["key"],yellow,dark))

# Evidence.
clean_img=Image.fromarray(expected_clean,"RGBA")
for name,m in [("C140_SOURCE_TEXT_MASK.png",source_mask),("C140_ALLOWED_BBOX_MASK.png",allowed),
 ("C140_PROTECTED_VISIBLE_MASK.png",protected),("C140_TARGET_TEXT_MASK.png",target),("C140_ENTER_ICON_MASK.png",icon_mask),
 ("C140_B58_RESIDUE_MASK.png",input_residue)]:
    Image.fromarray((m.astype(np.uint8)*255),"L").save(out/name)
clean_img.save(out/"C140_EXACT_CLEAN_PLATE.png")
def card(lbl,im,bg=(64,64,64,255)):
    v=comp(im,bg); c=Image.new("RGB",(W,H+28),"white"); c.paste(v,(0,28)); ImageDraw.Draw(c).text((5,5),lbl,fill="black"); return c
cards=[card("SOURCE",src),card("B58_INPUT",inp),card("C140_EXACT_CLEAN",clean_img),card("C140_FIXED_FINAL",dec)]
sheet=Image.new("RGB",(W*2,(H+28)*2),"white")
sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(W,0)); sheet.paste(cards[2],(0,H+28)); sheet.paste(cards[3],(W,H+28))
sheet.resize((2048,1052),Image.Resampling.LANCZOS).save(out/"C140_31C_COMPARE.jpg",quality=96)

sr,bi,cl,fi=map(comp,[src,inp,clean_img,dec]); contacts=[]
for r in row_results:
    x0,y0,x1,y1=r["original_bbox"]; p=12; cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p))
    ims=[z.crop(cr) for z in (sr,bi,cl,fi)]; ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
    c=Image.new("RGB",(sum(z.width for z in ims)+18,max(z.height for z in ims)+28),"white"); xx=0
    for z in ims: c.paste(z,(xx,28)); xx+=z.width+6
    ImageDraw.Draw(c).text((5,5),f'{r["source"]} -> {r["korean"]}',fill="black"); contacts.append(c)
rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white"); yy=0
for c in contacts: rs.paste(c,(0,yy)); yy+=c.height+4
rs.save(out/"C140_31C_ROW_CONTACT_2X.jpg",quality=96)
rawsheet=Image.new("RGB",(1024,1080),"white")
for i,(lbl,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("C140_FIXED_RAW_MIRROR_Y",dec_raw)]):
    z=comp(im).resize((1024,512),Image.Resampling.LANCZOS); rawsheet.paste(z,(0,i*540+28)); ImageDraw.Draw(rawsheet).text((5,i*540+5),lbl,fill="black")
rawsheet.save(out/"C140_31C_RAW_COMPARE.jpg",quality=96)

report={"schema_version":1,"role":"C","run":run,"queue_index":140,"asset":asset,
 "producer_run":"20261005-B-PRODUCTION58","source_sha256":SOURCE_SHA256,
 "input_candidate_sha256":INPUT_CANDIDATE_SHA256,"candidate_sha256":out_sha,"candidate_changed_by_C":True,
 "corrective_scope":"remove 298 canonical KEY source-effect fringe pixels x457..461 omitted by B58 right_range beginning at x462; no Korean target or protected icon pixels changed",
 "independent_source_method":"pinned canonical source+atlas; rows0-3 exact cell alpha; region4 exact three 8-connected alpha groups PRESS|Enter icon|KEY",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "compound_source_groups":{"press_bbox":left["bbox"],"enter_icon_bbox":icon["bbox"],"key_bbox":right["bbox"],
   "press_pixels":left["pixels"],"enter_icon_pixels":icon["pixels"],"key_pixels":right["pixels"]},
 "producer_defect":{"clean_diff_vs_independent_exact_pixels":producer_clean_diff_pixels,"clean_diff_bbox":producer_clean_diff_bbox,
   "input_source_residue_pixels":input_residue_pixels,"input_source_residue_bbox":input_residue_bbox},
 "rows":row_results,"style_checks":style,
 "machine_checks":{"fix_changed_pixels":int(np.count_nonzero(fix_delta)),"changes_vs_input_outside_fix_mask":int(np.count_nonzero(fix_delta&~input_residue)),
   "bbox_size_positive_margin":"6/6 PASS","final_outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,
   "enter_icon_changed":icon_changed,"render_outside_target":render_out,"source_residue":source_residue,
   "overlap":overlap,"touch_pairs":touch,"compound_target_icon_1px_near_pixels":icon_near},
 "machine_status":"PASS_AFTER_C_SMALL_CORRECTION","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C140_31C_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"31C58963","index":140,"input_candidate_sha256":INPUT_CANDIDATE_SHA256,"candidate_sha256":out_sha,
 "machine_status":"PASS_AFTER_C_SMALL_CORRECTION","corrected_source_residue_pixels":input_residue_pixels,
 "bbox_size_positive_margin":"6/6","outside":outside,"alpha_outside":alpha_out,"protected_changed":protected_changed,
 "icon_changed":icon_changed,"source_residue":source_residue,"overlap":overlap,"touch_pairs":len(touch),
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C140_31C_MACHINE_QA.json"}
(wr/"C140_31C58963.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
