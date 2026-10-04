#!/usr/bin/env python3
import os,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd()
run='20261004-C104-PENDING-VISUAL'
out=repo/'localization/graphics/role_C'/run
out.mkdir(parents=True,exist_ok=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mload(p): return np.asarray(Image.open(p).convert('L'))>0
def rgba(p): return np.asarray(Image.open(p).convert('RGBA'))
def rect(shape,box):
    H,W=shape; x0,y0,x1,y1=map(int,box); m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=1; return m
def dil1(m):
    p=np.pad(m,1,constant_values=False)
    return (p[:-2,:-2]|p[:-2,1:-1]|p[:-2,2:]|p[1:-1,:-2]|p[1:-1,1:-1]|p[1:-1,2:]|p[2:,:-2]|p[2:,1:-1]|p[2:,2:])
def bb(m):
    y,x=np.nonzero(m)
    return None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]

specs=[
 {
  'asset':'455717B2','report':'localization/graphics/role_A/20261004-A-PRODUCTION10/A_PRODUCTION10_455717B2_REPORT.json',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds',
  'allowed':'localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_ALLOWED_TEXT_REGION_MASK.png',
  'protected':'localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_PROTECTED_VISIBLE_MASK.png',
  'clean':'localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_CLEAN_PLATE.png',
  'final':'localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_FINAL_DECODED_READABLE.png',
  'target':None
 },
 {
  'asset':'43B07A77','report':'localization/graphics/role_A/20261004-A-PRODUCTION12/A_PRODUCTION12_43B07A77_REPORT.json',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds',
  'allowed':'localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_ALLOWED_TEXT_REGION_MASK.png',
  'protected':'localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_PROTECTED_VISIBLE_MASK.png',
  'clean':'localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_CLEAN_PLATE.png',
  'final':'localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_FINAL_DECODED_READABLE.png',
  'target':None
 },
 {
  'asset':'B1696633','report':'localization/graphics/role_B/20261004-B-RECOVERY07/B_RECOVERY07_B1696633_REPORT.json',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds',
  'allowed':'localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_ALLOWED_TEXT_REGION_MASK.png',
  'protected':'localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_PROTECTED_MASK.png',
  'target':'localization/graphics/role_B/20261004-B-RECOVERY07/B1696633_TARGET_TEXT_MASK.png',
  'clean':None,'final':None
 },
 {
  'asset':'CBF8ECBF','report':'localization/graphics/role_B/20261004-B-RECOVERY08/B_RECOVERY08_CBF8ECBF_REPORT.json',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds',
  'allowed':'localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_ALLOWED_TEXT_REGION_MASK.png',
  'protected':'localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_PROTECTED_MASK.png',
  'target':'localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_TARGET_TEXT_MASK.png',
  'clean':None,'final':None
 }
]
results=[]
for s in specs:
    rep=json.loads((repo/s['report']).read_text(encoding='utf-8'))
    allowed=mload(repo/s['allowed']); protected=mload(repo/s['protected'])
    if s['target']:
        target=mload(repo/s['target'])
    else:
        clean=rgba(repo/s['clean']); final=rgba(repo/s['final'])
        if clean.shape!=final.shape: raise RuntimeError((s['asset'],'clean/final shape mismatch'))
        target=np.any(final!=clean,axis=2)
    if not(target.shape==allowed.shape==protected.shape): raise RuntimeError((s['asset'],'mask shape mismatch'))
    candidate_sha=sha(repo/s['candidate'])
    expected=rep['candidate_sha256']
    outside=int(np.logical_and(target,~allowed).sum())
    prot=int(np.logical_and(target,protected).sum())

    if rep.get('rows'):
        rowdefs=[(r['key'],r['original_bbox'],r['localized_bbox']) for r in rep['rows']]
    else:
        rowdefs=[('game_over',rep['original_bbox'],rep['localized_bbox'])]
    row_results=[]; row_masks=[]
    for key,ob,lb in rowdefs:
        ob=list(map(int,ob)); lb=list(map(int,lb))
        rm=target & rect(target.shape,lb)
        actual=bb(rm)
        if actual is None: raise RuntimeError((s['asset'],key,'empty localized target mask'))
        sw,shh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=actual[2]-actual[0],actual[3]-actual[1]
        row_results.append({
          'key':key,'original_bbox':ob,'localized_bbox':actual,
          'delta_left':actual[0]-ob[0],'delta_right':ob[2]-actual[2],
          'delta_top':actual[1]-ob[1],'delta_bottom':ob[3]-actual[3],
          'source_size':[sw,shh],'localized_size':[lw,lh],
          'containment':'PASS' if actual[0]>=ob[0] and actual[1]>=ob[1] and actual[2]<=ob[2] and actual[3]<=ob[3] else 'FAIL',
          'size_ceiling':'PASS' if lw<=sw and lh<=shh else 'FAIL'
        })
        row_masks.append(rm)
    pair_overlap=0; touching=[]
    for i in range(len(row_masks)):
        for j in range(i+1,len(row_masks)):
            ov=int(np.logical_and(row_masks[i],row_masks[j]).sum())
            near=int(np.logical_and(dil1(row_masks[i]),row_masks[j]).sum())
            pair_overlap+=ov
            if ov or near: touching.append([rowdefs[i][0],rowdefs[j][0],ov,near])
    passed=(candidate_sha==expected and outside==0 and prot==0 and pair_overlap==0 and not touching and
            all(x['containment']=='PASS' and x['size_ceiling']=='PASS' for x in row_results))
    result={
      'asset':s['asset'],'producer_report':s['report'],
      'candidate_sha256':candidate_sha,'candidate_matches_producer_sha':candidate_sha==expected,
      'target_pixels':int(target.sum()),'target_pixels_outside_allowed_mask':outside,
      'target_protected_overlap_pixels':prot,'localized_pair_overlap_pixels':pair_overlap,
      'localized_touch_or_overlap_pairs':touching,'rows':row_results,
      'machine_status':'PASS' if passed else 'FAIL','controller_visual_qa':'PENDING',
      'runtime_validation':'UNTESTED'
    }
    (out/f"C104_{s['asset']}_ZERO_OVERLAP_QA.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    results.append(result)

summary={
 'schema_version':1,'role':'C','run':run,
 'scope':'pending-C approval candidates with existing exact-size QA: 455717B2, 43B07A77, B1696633, CBF8ECBF. C103-completed assets and current producer REWORK were not repeated.',
 'policy':'new zero-overlap pixel-mask supplement to existing exact-source bbox/size QA; controller readable/raw visual gate remains separate',
 'results':results,
 'machine_pass_assets':[x['asset'] for x in results if x['machine_status']=='PASS'],
 'machine_fail_assets':[x['asset'] for x in results if x['machine_status']!='PASS'],
 'controller_visual_qa':'PENDING','runtime_validation':'UNTESTED',
 'vr_ffb_dx11_dxvk_changes':False
}
(out/'C104_PENDING_ZERO_OVERLAP_MACHINE_QA.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C104_DONE',json.dumps({'pass':summary['machine_pass_assets'],'fail':summary['machine_fail_assets']}),flush=True)
