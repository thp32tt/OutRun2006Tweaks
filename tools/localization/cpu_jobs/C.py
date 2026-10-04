#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd(); run='20261004-C108-LATEST-REWORK'
out=repo/'localization/graphics/role_C'/run; out.mkdir(parents=True,exist_ok=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def rgba(p): return np.asarray(Image.open(p).convert('RGBA'))
def mload(p): return np.asarray(Image.open(p).convert('L'))>0
def decode_rgba32_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b'DDS ': raise RuntimeError('not dds')
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]
    pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]; masks=struct.unpack_from('<IIII',b,92)
    if not(fourcc==b'\0\0\0\0' and bpp==32 and len(b)==128+w*h*4): raise RuntimeError('unexpected rgba32')
    im=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],np.asarray(im),{'width':w,'height':h,'pitch':pitch,'mips':mips,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks],'raw_orientation':'mirror_y'}
def bb(m):
    y,x=np.nonzero(m)
    return None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def rect(shape,b):
    H,W=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=1; return m
def dil2(m):
    a=m.copy()
    for _ in range(2):
        p=np.pad(a,1,constant_values=False)
        a=(p[:-2,:-2]|p[:-2,1:-1]|p[:-2,2:]|p[1:-1,:-2]|p[1:-1,1:-1]|p[1:-1,2:]|p[2:,:-2]|p[2:,1:-1]|p[2:,2:])
    return a

results=[]

# 39229D64 latest A_RECOVERY09 candidate
ad=repo/'localization/graphics/role_A/20261004-A-RECOVERY09'
ar=json.loads((ad/'A_RECOVERY09_39229D64_REPORT.json').read_text(encoding='utf-8'))
acand=repo/ar['candidate_path']
ah,ac,am=decode_rgba32_dds(acand)
src=rgba(ad/'39229D64_HD_SOURCE_READABLE.png')
clean=rgba(ad/'39229D64_REPAIRED_CLEAN_PLATE.png')
persist=rgba(ad/'39229D64_FINAL_DECODED_READABLE.png')
allowed=mload(ad/'39229D64_ALLOWED_TEXT_REGION_MASK.png')
protected=mload(ad/'39229D64_PROTECTED_VISIBLE_MASK.png')
source_text=mload(ad/'39229D64_SOURCE_TEXT_EFFECT_MASK.png')
target=mload(ad/'39229D64_LOCALIZED_LAYER_UNION_MASK.png')
if not(src.shape==clean.shape==persist.shape==ac.shape): raise RuntimeError('392 shape mismatch')
roundtrip=int(np.any(ac!=persist,axis=2).sum())
clean_changed=np.any(clean!=src,axis=2)
final_changed=np.any(ac!=src,axis=2)
clean_out=int(np.logical_and(clean_changed,~source_text).sum())
final_out=int(np.logical_and(final_changed,~allowed).sum())
prot=int(np.logical_and(final_changed,protected).sum())
residue=int(np.logical_and(source_text,np.all(clean==src,axis=2)).sum())
rows=[]; row_masks=[]
for r in ar['rows']:
    ob=list(map(int,r['original_bbox'])); lb=list(map(int,r['localized_bbox']))
    rm=target & rect(target.shape,lb); ab=bb(rm)
    if ab is None: raise RuntimeError(('392 empty row',r['key']))
    sw,shh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=ab[2]-ab[0],ab[3]-ab[1]
    rows.append({'key':r['key'],'original_bbox':ob,'localized_bbox':ab,
      'delta_left':ab[0]-ob[0],'delta_right':ob[2]-ab[2],'delta_top':ab[1]-ob[1],'delta_bottom':ob[3]-ab[3],
      'source_size':[sw,shh],'localized_size':[lw,lh],
      'containment':'PASS' if ab[0]>=ob[0] and ab[1]>=ob[1] and ab[2]<=ob[2] and ab[3]<=ob[3] else 'FAIL',
      'size_ceiling':'PASS' if lw<=sw and lh<=shh else 'FAIL'})
    row_masks.append(rm)
pair_overlap=0; pair_guard=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        ov=int(np.logical_and(row_masks[i],row_masks[j]).sum())
        near=int(np.logical_and(dil2(row_masks[i]),row_masks[j]).sum())
        pair_overlap+=ov
        if ov or near: pair_guard.append([ar['rows'][i]['key'],ar['rows'][j]['key'],ov,near])
apass=(sha(acand)==ar['candidate_sha256'] and roundtrip==0 and clean_out==0 and final_out==0 and prot==0 and residue==0 and pair_overlap==0 and not pair_guard and all(x['containment']=='PASS' and x['size_ceiling']=='PASS' for x in rows))
ares={'schema_version':1,'role':'C','run':run,'asset':'39229D64',
 'candidate_sha256':sha(acand),'source_sha256':ar['source_sha256'],'structure':am,
 'candidate_matches_producer_sha':sha(acand)==ar['candidate_sha256'],
 'decoded_candidate_vs_persisted_final_diff_pixels':roundtrip,
 'clean_changed_pixels_outside_source_text_mask':clean_out,
 'final_changed_pixels_outside_allowed_mask':final_out,
 'final_changed_pixels_in_protected_visible_mask':prot,
 'source_text_mask_pixels_unchanged_in_clean_plate':residue,
 'localized_pair_overlap_pixels':pair_overlap,'localized_2px_guard_conflicts':pair_guard,
 'rows':rows,'machine_status':'PASS' if apass else 'FAIL','controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'}
(out/'C108_39229D64_MACHINE_QA.json').write_text(json.dumps(ares,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
results.append(ares)

# 53CE39D5 latest B_PRODUCTION21 candidate after C107 residue return.
bd=repo/'localization/graphics/role_B/20261004-B-PRODUCTION21'
br=json.loads((bd/'B_PRODUCTION21_53CE_REPORT.json').read_text(encoding='utf-8'))
bcand=repo/br['candidate_path']; bh,bc,bm=decode_rgba32_dds(bcand)
with urllib.request.urlopen(br['source_url'],timeout=30) as r: sb=r.read()
if sha_bytes(sb)!=br['source_sha256']: raise RuntimeError('53 source sha mismatch')
sraw=Image.frombytes('RGBA',(bm['width'],bm['height']),sb[128:],'raw','RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
bsrc=np.asarray(sraw)
bclean=rgba(bd/'53CE39D5_HD_CLEAN_PLATE.png')
ballowed=mload(bd/'53CE39D5_HD_ALLOWED_TEXT_REGION_MASK.png')
bprotected=mload(bd/'53CE39D5_HD_PROTECTED_MASK.png')
bsource=mload(bd/'53CE39D5_HD_SOURCE_TEXT_MASK.png')
btarget=mload(bd/'53CE39D5_HD_TARGET_TEXT_MASK.png')
bclean_changed=np.any(bclean!=bsrc,axis=2)
bresidue=int(np.logical_and(bsource,np.all(bclean==bsrc,axis=2)).sum())
bclean_out=int(np.logical_and(bclean_changed,~bsource).sum())
bout=int(np.logical_and(btarget,~ballowed).sum())
bprot=int(np.logical_and(btarget,bprotected).sum())
bguard=int(np.logical_and(dil2(btarget),bprotected).sum())
brows=[]
for r in br['rows']:
    ob=list(map(int,r['original_bbox'])); lb=list(map(int,r['localized_bbox']))
    rm=btarget & rect(btarget.shape,lb); ab=bb(rm)
    if ab is None: raise RuntimeError(('53 empty row',r['target'],r['line_index']))
    sw,shh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=ab[2]-ab[0],ab[3]-ab[1]
    brows.append({'key':f"{r['target']}_{r['line_index']}",'original_bbox':ob,'localized_bbox':ab,
      'delta_left':ab[0]-ob[0],'delta_right':ob[2]-ab[2],'delta_top':ab[1]-ob[1],'delta_bottom':ob[3]-ab[3],
      'source_size':[sw,shh],'localized_size':[lw,lh],
      'containment':'PASS' if ab[0]>=ob[0] and ab[1]>=ob[1] and ab[2]<=ob[2] and ab[3]<=ob[3] else 'FAIL',
      'size_ceiling':'PASS' if lw<=sw and lh<=shh else 'FAIL'})
bpass=(sha(bcand)==br['candidate_sha256'] and bh==sb[:128] and bclean_out==0 and bresidue==0 and bout==0 and bprot==0 and bguard==0 and all(x['containment']=='PASS' and x['size_ceiling']=='PASS' for x in brows))
bres={'schema_version':1,'role':'C','run':run,'asset':'53CE39D5',
 'candidate_sha256':sha(bcand),'source_sha256':br['source_sha256'],'structure':bm,
 'source_header_128_exact':bh==sb[:128],'candidate_matches_producer_sha':sha(bcand)==br['candidate_sha256'],
 'clean_changed_pixels_outside_source_text_mask':bclean_out,
 'source_text_mask_pixels_unchanged_in_clean_plate':bresidue,
 'target_pixels_outside_allowed_mask':bout,'target_protected_overlap_pixels':bprot,'target_2px_guard_vs_protected_conflicts':bguard,
 'rows':brows,'machine_status':'PASS' if bpass else 'FAIL','controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'}
(out/'C108_53CE39D5_MACHINE_QA.json').write_text(json.dumps(bres,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
results.append(bres)

summary={'schema_version':1,'role':'C','run':run,'results':results,
 'machine_pass_assets':[x['asset'] for x in results if x['machine_status']=='PASS'],
 'machine_fail_assets':[x['asset'] for x in results if x['machine_status']!='PASS'],
 'runtime_validation':'UNTESTED','vr_ffb_dx11_dxvk_changes':False}
(out/'C108_LATEST_REWORK_MACHINE_QA.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C108_DONE',json.dumps({'pass':summary['machine_pass_assets'],'fail':summary['machine_fail_assets']}),flush=True)
