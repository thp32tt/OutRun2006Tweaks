#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd()
run='20261004-C106-5B65E08C'
out=repo/'localization/graphics/role_C'/run
out.mkdir(parents=True,exist_ok=True)
bdir=repo/'localization/graphics/role_B/20261004-B-PRODUCTION20'
rep=json.loads((bdir/'B_PRODUCTION20_5B65E08C_REPORT.json').read_text(encoding='utf-8'))
candidate=repo/rep['candidate_path']

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def mload(p): return np.asarray(Image.open(p).convert('L'))>0
def bb(m):
    y,x=np.nonzero(m)
    return None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def rect(shape,box):
    H,W=shape; x0,y0,x1,y1=map(int,box); m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=1; return m
def dil2(m):
    a=m.copy()
    for _ in range(2):
        p=np.pad(a,1,constant_values=False)
        a=(p[:-2,:-2]|p[:-2,1:-1]|p[:-2,2:]|p[1:-1,:-2]|p[1:-1,1:-1]|p[1:-1,2:]|p[2:,:-2]|p[2:,1:-1]|p[2:,2:])
    return a

cand=candidate.read_bytes()
with urllib.request.urlopen(rep['source_url'],timeout=30) as r:
    src=r.read()
if sha_bytes(src)!=rep['source_sha256']: raise RuntimeError(('source sha mismatch',sha_bytes(src)))
if sha_bytes(cand)!=rep['candidate_sha256']: raise RuntimeError(('candidate sha mismatch',sha_bytes(cand)))
if cand[:128]!=src[:128]: raise RuntimeError('DDS header mismatch to exact HD source')
h=struct.unpack_from('<I',cand,12)[0]; w=struct.unpack_from('<I',cand,16)[0]
pitch=struct.unpack_from('<I',cand,20)[0]; mips=struct.unpack_from('<I',cand,28)[0]
fourcc=cand[84:88]; bpp=struct.unpack_from('<I',cand,88)[0]; masks=struct.unpack_from('<IIII',cand,92)
if not(h==1024 and w==2048 and pitch==8192 and mips==1 and fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000)):
    raise RuntimeError(('structure mismatch',h,w,pitch,mips,fourcc,bpp,masks))

allowed=mload(bdir/'5B65E08C_ALLOWED_TEXT_REGION_MASK.png')
protected=mload(bdir/'5B65E08C_PROTECTED_MASK.png')
source_text=mload(bdir/'5B65E08C_SOURCE_TEXT_MASK.png')
target=mload(bdir/'5B65E08C_TARGET_TEXT_MASK.png')
if not(allowed.shape==protected.shape==source_text.shape==target.shape==(1024,2048)): raise RuntimeError('mask shape mismatch')
outside=int(np.logical_and(target,~allowed).sum())
prot=int(np.logical_and(target,protected).sum())
guard=int(np.logical_and(dil2(target),protected).sum())

r=rep['rows'][0]; ob=list(map(int,r['original_bbox']))
actual=bb(target)
if actual is None: raise RuntimeError('empty target')
sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=actual[2]-actual[0],actual[3]-actual[1]
contain=actual[0]>=ob[0] and actual[1]>=ob[1] and actual[2]<=ob[2] and actual[3]<=ob[3]
size_ok=lw<=sw and lh<=sh

clean=np.asarray(Image.open(bdir/'5B65E08C_CLEAN_PLATE.png').convert('RGBA'))
# Exact source DDS readable orientation.
raw=Image.frombytes('RGBA',(w,h),src[128:],'raw','RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
source=np.asarray(raw)
changed=np.any(clean!=source,axis=2)
clean_outside=int(np.logical_and(changed,~source_text).sum())
# Any exact source RGBA pixel left on source-text mask is suspicious residue; producer declared the mask as glyph effect footprint.
same=np.all(clean==source,axis=2)
source_residue=int(np.logical_and(source_text,same).sum())

passed=(outside==0 and prot==0 and guard==0 and clean_outside==0 and source_residue==0 and contain and size_ok)
result={
 'schema_version':1,'role':'C','run':run,'asset':'5B65E08C','queue_index':164,
 'producer_report':'localization/graphics/role_B/20261004-B-PRODUCTION20/B_PRODUCTION20_5B65E08C_REPORT.json',
 'source_sha256':rep['source_sha256'],'candidate_sha256':rep['candidate_sha256'],
 'source_header_128_exact':cand[:128]==src[:128],
 'structure':{'width':w,'height':h,'pitch':pitch,'mips':mips,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks],'raw_orientation':'mirror_y'},
 'target_pixels_outside_allowed_mask':outside,
 'target_protected_overlap_pixels':prot,
 'target_2px_guard_vs_protected_conflicts':guard,
 'clean_changed_pixels_outside_source_text_mask':clean_outside,
 'source_text_residue_pixels_in_clean_plate':source_residue,
 'row':{
   'key':r['key'],'original_bbox':ob,'localized_bbox':actual,
   'delta_left':actual[0]-ob[0],'delta_right':ob[2]-actual[2],
   'delta_top':actual[1]-ob[1],'delta_bottom':ob[3]-actual[3],
   'source_size':[sw,sh],'localized_size':[lw,lh],
   'containment':'PASS' if contain else 'FAIL','size_ceiling':'PASS' if size_ok else 'FAIL'
 },
 'machine_status':'PASS' if passed else 'FAIL',
 'controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'
}
(out/'C106_5B65E08C_MACHINE_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C106_DONE',json.dumps({'machine_status':result['machine_status'],'source_residue':source_residue,'guard':guard}),flush=True)
