#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd(); run='20261004-C107-NEW-B'
out=repo/'localization/graphics/role_C'/run; out.mkdir(parents=True,exist_ok=True)

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def mload(p): return np.asarray(Image.open(p).convert('L'))>0
def rgba_dds_bytes(b):
    if b[:4]!=b'DDS ': raise RuntimeError('not dds')
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]
    if b[84:88]!=b'\0\0\0\0' or struct.unpack_from('<I',b,88)[0]!=32: raise RuntimeError('non-rgba32')
    im=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return np.asarray(im)
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

specs=[
 {'asset':'788CE557','dir':'localization/graphics/role_B/20261004-B-PRODUCTION21',
  'report':'B_PRODUCTION21_788CE557_REPORT.json','prefix':'788CE557',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/788CE557_512x256.dds'},
 {'asset':'53CE39D5','dir':'localization/graphics/role_B/20261004-B-PRODUCTION21',
  'report':'B_PRODUCTION21_53CE_REPORT.json','prefix':'53CE39D5_HD',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds'}
]
results=[]
for s in specs:
    d=repo/s['dir']; rep=json.loads((d/s['report']).read_text(encoding='utf-8'))
    cand=(repo/s['candidate']).read_bytes()
    with urllib.request.urlopen(rep['source_url'],timeout=30) as r: src=r.read()
    if sha_bytes(src)!=rep['source_sha256'] or sha_bytes(cand)!=rep['candidate_sha256']: raise RuntimeError((s['asset'],'sha mismatch'))
    header_exact=(cand[:128]==src[:128])
    source=rgba_dds_bytes(src)
    clean=np.asarray(Image.open(d/f"{s['prefix']}_CLEAN_PLATE.png").convert('RGBA'))
    allowed=mload(d/f"{s['prefix']}_ALLOWED_TEXT_REGION_MASK.png")
    protected=mload(d/f"{s['prefix']}_PROTECTED_MASK.png")
    source_text=mload(d/f"{s['prefix']}_SOURCE_TEXT_MASK.png")
    target=mload(d/f"{s['prefix']}_TARGET_TEXT_MASK.png")
    if not(source.shape[:2]==clean.shape[:2]==allowed.shape==protected.shape==source_text.shape==target.shape): raise RuntimeError((s['asset'],'shape mismatch'))
    clean_changed=np.any(clean!=source,axis=2)
    source_same=np.all(clean==source,axis=2)
    residue=int(np.logical_and(source_text,source_same).sum())
    clean_outside=int(np.logical_and(clean_changed,~source_text).sum())
    outpix=int(np.logical_and(target,~allowed).sum())
    prot=int(np.logical_and(target,protected).sum())
    guard=int(np.logical_and(dil2(target),protected).sum())
    rows=[]
    for r in rep['rows']:
        ob=list(map(int,r['original_bbox'])); lb=list(map(int,r['localized_bbox']))
        rm=target & rect(target.shape,lb); ab=bb(rm)
        if ab is None: raise RuntimeError((s['asset'],r.get('key') or r.get('target'),'empty row'))
        sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=ab[2]-ab[0],ab[3]-ab[1]
        rows.append({'key':r.get('key') or f"{r.get('target')}_{r.get('line_index')}",
          'original_bbox':ob,'localized_bbox':ab,
          'delta_left':ab[0]-ob[0],'delta_right':ob[2]-ab[2],
          'delta_top':ab[1]-ob[1],'delta_bottom':ob[3]-ab[3],
          'source_size':[sw,sh],'localized_size':[lw,lh],
          'containment':'PASS' if ab[0]>=ob[0] and ab[1]>=ob[1] and ab[2]<=ob[2] and ab[3]<=ob[3] else 'FAIL',
          'size_ceiling':'PASS' if lw<=sw and lh<=sh else 'FAIL'})
    passed=(header_exact and clean_outside==0 and residue==0 and outpix==0 and prot==0 and guard==0 and all(x['containment']=='PASS' and x['size_ceiling']=='PASS' for x in rows))
    res={'schema_version':1,'role':'C','run':run,'asset':s['asset'],
      'candidate_sha256':rep['candidate_sha256'],'source_sha256':rep['source_sha256'],
      'source_header_128_exact':header_exact,
      'clean_changed_pixels_outside_source_text_mask':clean_outside,
      'source_text_mask_pixels_unchanged_in_clean_plate':residue,
      'target_pixels_outside_allowed_mask':outpix,'target_protected_overlap_pixels':prot,
      'target_2px_guard_vs_protected_conflicts':guard,'rows':rows,
      'machine_status':'PASS' if passed else 'FAIL','controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'}
    (out/f"C107_{s['asset']}_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    results.append(res)
summary={'schema_version':1,'role':'C','run':run,'results':results,
 'machine_pass_assets':[x['asset'] for x in results if x['machine_status']=='PASS'],
 'machine_fail_assets':[x['asset'] for x in results if x['machine_status']!='PASS'],
 'runtime_validation':'UNTESTED','vr_ffb_dx11_dxvk_changes':False}
(out/'C107_NEW_B_MACHINE_QA.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C107_DONE',json.dumps({'pass':summary['machine_pass_assets'],'fail':summary['machine_fail_assets']}),flush=True)
