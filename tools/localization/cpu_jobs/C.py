#!/usr/bin/env python3
import os,json,hashlib,struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd()
run='20261005-C111-C075-FINAL'
out=repo/'localization/graphics/role_C'/run
out.mkdir(parents=True,exist_ok=True)
rep_path=repo/'localization/graphics/role_A/20261005-A-RECOVERY12/A_RECOVERY12_C075FB49_REPORT.json'
rep=json.loads(rep_path.read_text(encoding='utf-8'))
src_path=repo/'localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds'
cand_path=repo/rep['candidate_path']
d=repo/'localization/graphics/role_A/20261005-A-RECOVERY12'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(p):
    b=Path(p).read_bytes()
    if b[:4]!=b'DDS ': raise RuntimeError('not DDS')
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]
    pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]; masks=struct.unpack_from('<IIII',b,92)
    if not (fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and pitch==w*4 and mips==1):
        raise RuntimeError(('unexpected DDS',w,h,pitch,mips,fourcc,bpp,masks))
    im=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b,np.asarray(im),{'width':w,'height':h,'pitch':pitch,'mips':mips,'format':'RGBA32','raw_orientation':'mirror_y'}
def mask(p): return np.asarray(Image.open(p).convert('L'))>0
def rect(shape,b):
    H,W=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((H,W),bool);m[y0:y1,x0:x1]=1;return m
def bb(m):
    y,x=np.nonzero(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def dil1(m):
    return np.asarray(Image.fromarray((m*255).astype(np.uint8),'L').filter(ImageFilter.MaxFilter(3)))>0

sb,source,si=decode(src_path); cb,cand,ci=decode(cand_path)
if sha(src_path)!=rep['source_sha256']: raise RuntimeError('source sha mismatch')
if sha(cand_path)!=rep['candidate_sha256']: raise RuntimeError('candidate sha mismatch')
clean=np.asarray(Image.open(d/'C075FB49_CLEAN_PLATE.png').convert('RGBA'))
final=np.asarray(Image.open(d/'C075FB49_FINAL_READABLE.png').convert('RGBA'))
if source.shape!=cand.shape or clean.shape!=source.shape or final.shape!=source.shape: raise RuntimeError('shape mismatch')
final_decode_diff=int(np.any(final!=cand,axis=2).sum())
source_png=np.asarray(Image.open(d/'C075FB49_SOURCE_READABLE.png').convert('RGBA'))
source_decode_diff=int(np.any(source_png!=source,axis=2).sum())
allowed=mask(d/'C075FB49_ALLOWED_TEXT_REGION_MASK.png')
protected=mask(d/'C075FB49_PROTECTED_MASK.png')
source_top=mask(d/'C075FB49_TOP_SOURCE_TEXT_MASK.png')
changed=np.any(cand!=source,axis=2)
target=np.any(cand!=clean,axis=2)
source_residue=int(np.logical_and(source_top,np.all(clean==source,axis=2)).sum())
outside=int(np.logical_and(changed,~allowed).sum())
prot=int(np.logical_and(changed,protected).sum())
rows=[]; rowm=[]; union=np.zeros(target.shape,bool)
for r in rep['rows']:
    ob=list(map(int,r['original_bbox'])); lb=list(map(int,r['localized_bbox']))
    union |= rect(target.shape,ob)
    rm=target & rect(target.shape,lb)
    ab=bb(rm)
    if ab is None: raise RuntimeError((r['key'],'empty target'))
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=ab[2]-ab[0],ab[3]-ab[1]
    rows.append({'key':r['key'],'original_bbox':ob,'localized_bbox':ab,
      'delta_left':ab[0]-ob[0],'delta_right':ob[2]-ab[2],'delta_top':ab[1]-ob[1],'delta_bottom':ob[3]-ab[3],
      'source_size':[sw,sh],'localized_size':[lw,lh],
      'containment':'PASS' if ab[0]>=ob[0] and ab[1]>=ob[1] and ab[2]<=ob[2] and ab[3]<=ob[3] else 'FAIL',
      'size_ceiling':'PASS' if lw<=sw and lh<=sh else 'FAIL',
      'producer_shear':r.get('shear')})
    rowm.append((r['key'],rm))
target_outside=int(np.logical_and(target,~union).sum())
pair=0; touch=[]
for i in range(len(rowm)):
    for j in range(i+1,len(rowm)):
        ov=int(np.logical_and(rowm[i][1],rowm[j][1]).sum())
        near=int(np.logical_and(dil1(rowm[i][1]),rowm[j][1]).sum())
        pair+=ov
        if ov or near: touch.append([rowm[i][0],rowm[j][0],ov,near])
preserved_ok=all(v==0 for v in rep['preserved_lower_input_pixel_diffs'].values()) and all(v==0 for v in rep['preserved_source_label_pixel_diffs'].values())
ok=(sb[:128]==cb[:128] and source_decode_diff==0 and final_decode_diff==0 and source_residue==0 and outside==0 and prot==0 and
    target_outside==0 and pair==0 and not touch and preserved_ok and
    all(x['containment']=='PASS' and x['size_ceiling']=='PASS' for x in rows))
res={'schema_version':1,'role':'C','run':run,'asset':'C075FB49',
 'source_sha256':rep['source_sha256'],'candidate_sha256':rep['candidate_sha256'],
 'source_header_128_exact':sb[:128]==cb[:128],'structure':ci,
 'source_png_vs_independent_decode_diff_pixels':source_decode_diff,
 'persisted_final_vs_independent_decode_diff_pixels':final_decode_diff,
 'top_source_text_mask_pixels_unchanged_in_clean_plate':source_residue,
 'final_changed_pixels_outside_allowed_mask':outside,'final_changed_pixels_in_protected_mask':prot,
 'target_pixels_outside_union_source_bboxes':target_outside,
 'localized_pair_overlap_pixels':pair,'localized_touch_pairs':touch,
 'preserved_lower_and_source_labels_exact':preserved_ok,'rows':rows,
 'machine_status':'PASS' if ok else 'FAIL','controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'}
(out/'C111_C075FB49_MACHINE_QA.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C111_C075_FINAL',res['machine_status'],res['candidate_sha256'],flush=True)
