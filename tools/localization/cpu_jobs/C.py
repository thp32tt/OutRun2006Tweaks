#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd()
run='20261004-2128-C103'
out=repo/'localization/graphics/role_C'/run
out.mkdir(parents=True,exist_ok=True)

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_dds_bytes(b):
    if b[:4]!=b'DDS ': raise RuntimeError('not dds')
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]
    pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]
    masks=struct.unpack_from('<IIII',b,92)
    if not(fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000)
           and pitch==w*4 and mips==1 and len(b)==128+w*h*4):
        raise RuntimeError(('unexpected dds structure',h,w,pitch,mips,fourcc,bpp,masks,len(b)))
    raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA')
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],np.asarray(readable),{
      'width':w,'height':h,'pitch':pitch,'mips':mips,'fourcc':'00000000',
      'bpp':bpp,'masks':[hex(x) for x in masks],'raw_orientation':'mirror_y'
    }

def mload(p): return np.asarray(Image.open(p).convert('L'))>0
def rect(shape,box):
    H,W=shape; x0,y0,x1,y1=map(int,box); m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=1; return m
def dil(m,n=2):
    a=m.copy()
    for _ in range(n):
        # pure numpy 3x3 dilation to avoid scipy dependency beyond workflow defaults
        p=np.pad(a,1,constant_values=False)
        a=(p[:-2,:-2]|p[:-2,1:-1]|p[:-2,2:]|p[1:-1,:-2]|p[1:-1,1:-1]|p[1:-1,2:]|p[2:,:-2]|p[2:,1:-1]|p[2:,2:])
    return a
def bb(m):
    y,x=np.nonzero(m)
    return None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]

bdir=repo/'localization/graphics/role_B/20261004-B-RECOVERY09'
rep=json.loads((bdir/'B_RECOVERY09_A064FDFC_REPORT.json').read_text(encoding='utf-8'))
if rep.get('schema_version')!=2: raise RuntimeError(('expected B_RECOVERY09 v2',rep.get('schema_version')))
rel='localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds'
source=repo/'localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds'
candidate=repo/rel
source_bytes=source.read_bytes(); cand_bytes=candidate.read_bytes()
sh,src,sm=load_dds_bytes(source_bytes); ch,final,cm=load_dds_bytes(cand_bytes)
if src.shape!=final.shape: raise RuntimeError('shape mismatch')
H,W=src.shape[:2]
rows=rep['rows']
selected=np.zeros((H,W),bool)
for r in rows:
    selected |= rect((H,W),r['original_bbox'])

new=mload(bdir/'A064FDFC_NEW_TARGET_MASK.png')
existing=mload(bdir/'A064FDFC_EXISTING_TARGET_MASK.png')
saved_allowed=mload(bdir/'A064FDFC_SELECTED_ALLOWED_REGION_MASK.png')
saved_source=mload(bdir/'A064FDFC_SELECTED_SOURCE_TEXT_MASK.png')
clean=np.asarray(Image.open(bdir/'A064FDFC_SELECTED_CLEAN_PLATE.png').convert('RGBA'))
if not(new.shape==existing.shape==selected.shape==saved_allowed.shape==saved_source.shape): raise RuntimeError('mask shape mismatch')

source_alpha=src[:,:,3]>0
expected_source_mask=source_alpha & selected
expected_clean=src.copy()
expected_clean[expected_source_mask]=0
clean_diff=int(np.any(clean!=expected_clean,axis=2).sum())
allowed_xor=int(np.logical_xor(saved_allowed,selected).sum())
source_mask_xor=int(np.logical_xor(saved_source,expected_source_mask).sum())
new_outside=int(np.logical_and(new,~selected).sum())
new_existing_overlap=int(np.logical_and(new,existing).sum())
new_existing_guard=int(np.logical_and(dil(new,2),existing).sum())

row_results=[]; row_masks=[]
for r in rows:
    ob=list(map(int,r['original_bbox']))
    lb=list(map(int,r['localized_bbox']))
    rm=new & rect((H,W),lb)
    actual=bb(rm)
    if actual is None: raise RuntimeError((r['key'],'empty target row'))
    sw,shh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=actual[2]-actual[0],actual[3]-actual[1]
    row_results.append({
      'key':r['key'],'original_bbox':ob,'localized_bbox':actual,
      'delta_left':actual[0]-ob[0],'delta_right':ob[2]-actual[2],
      'delta_top':actual[1]-ob[1],'delta_bottom':ob[3]-actual[3],
      'source_size':[sw,shh],'localized_size':[lw,lh],
      'containment':'PASS' if actual[0]>=ob[0] and actual[1]>=ob[1] and actual[2]<=ob[2] and actual[3]<=ob[3] else 'FAIL',
      'size_ceiling':'PASS' if lw<=sw and lh<=shh else 'FAIL'
    })
    row_masks.append(rm)

pair_overlap=0; pair_guard=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        ov=int(np.logical_and(row_masks[i],row_masks[j]).sum())
        near=int(np.logical_and(dil(row_masks[i],2),row_masks[j]).sum())
        pair_overlap+=ov
        if ov or near: pair_guard.append([rows[i]['key'],rows[j]['key'],ov,near])

unselected_inside=existing & selected
final_alpha=final[:,:,3]>0
residue=int(np.logical_and(expected_source_mask & ~unselected_inside, final_alpha & ~new).sum())

# Independently prove no collateral versus coherent pre-overlap C_OVERLAP05 fallback candidate.
prior_commit='c88701d061ca3ecafd87b360c5591eb7a4de8a06'
prior_bytes=subprocess.check_output(['git','show',f'{prior_commit}:{rel}'])
ph,prior,pm=load_dds_bytes(prior_bytes)
if ph!=sh or pm!=sm: raise RuntimeError('prior structure mismatch')
changed_vs_prior=np.any(final!=prior,axis=2)
outside_vs_prior=int(np.logical_and(changed_vs_prior,~selected).sum())

machine_pass=(
    sha(candidate)==rep['candidate_sha256'] and
    sha(source)==rep['source_sha256'] and ch==sh and cm==sm and
    allowed_xor==0 and source_mask_xor==0 and clean_diff==0 and
    new_outside==0 and new_existing_overlap==0 and new_existing_guard==0 and
    pair_overlap==0 and not pair_guard and residue==0 and outside_vs_prior==0 and
    all(r['containment']=='PASS' and r['size_ceiling']=='PASS' for r in row_results)
)

result={
  'schema_version':1,'role':'C','run':run,'asset':'A064FDFC',
  'producer_result':'B_RECOVERY09_v2',
  'candidate_sha256':sha(candidate),'producer_candidate_sha256':rep['candidate_sha256'],
  'source_sha256':sha(source),'source_header_128_exact':ch==sh,
  'structure':cm,
  'selected_allowed_mask_xor_vs_union_source_bboxes':allowed_xor,
  'selected_source_text_mask_xor_vs_source_alpha_in_union_bboxes':source_mask_xor,
  'persisted_clean_plate_diff_vs_independent_exact_source_alpha_clear':clean_diff,
  'new_target_pixels_outside_selected_source_bboxes':new_outside,
  'new_vs_existing_localized_overlap_pixels':new_existing_overlap,
  'new_vs_existing_2px_guard_conflicts':new_existing_guard,
  'new_pair_overlap_pixels':pair_overlap,
  'new_pair_guard_conflicts':pair_guard,
  'unexplained_source_alpha_residue_pixels':residue,
  'changed_pixels_vs_c_overlap05_fallback_outside_selected_source_bboxes':outside_vs_prior,
  'rows':row_results,
  'machine_status':'PASS' if machine_pass else 'FAIL',
  'controller_visual_qa':'PENDING',
  'runtime_validation':'UNTESTED'
}
(out/'C103_A064FDFC_MACHINE_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C103_DONE',json.dumps({'machine_status':result['machine_status'],'candidate_sha256':result['candidate_sha256'],'residue':residue,'outside':outside_vs_prior}),flush=True)
