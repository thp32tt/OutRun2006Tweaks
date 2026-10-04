#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd(); run='20261004-C109-PENDING-AND-C075'
out=repo/'localization/graphics/role_C'/run; out.mkdir(parents=True,exist_ok=True)

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds_bytes(b):
    if b[:4]!=b'DDS ': raise RuntimeError('not dds')
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]
    pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]; masks=struct.unpack_from('<IIII',b,92)
    if not(fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and pitch==w*4 and mips==1):
        raise RuntimeError(('unexpected DDS',w,h,pitch,mips,fourcc,bpp,masks))
    raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],np.asarray(raw),{'width':w,'height':h,'pitch':pitch,'mips':mips,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks],'raw_orientation':'mirror_y'}
def rgba_png(p): return np.asarray(Image.open(p).convert('RGBA'))
def mask_png(p): return np.asarray(Image.open(p).convert('L'))>0
def rect(shape,b):
    H,W=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=1; return m
def bb(m):
    y,x=np.nonzero(m)
    return None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def dil1(m):
    p=np.pad(m,1,constant_values=False)
    return (p[:-2,:-2]|p[:-2,1:-1]|p[:-2,2:]|p[1:-1,:-2]|p[1:-1,1:-1]|p[1:-1,2:]|p[2:,:-2]|p[2:,1:-1]|p[2:,2:])

def source_bytes_from_report(rep, local_source=None):
    if local_source:
        return (repo/local_source).read_bytes()
    sp=rep['source_provenance']
    url=f"https://raw.githubusercontent.com/{sp['repository']}/{sp['commit']}/{sp['path']}"
    with urllib.request.urlopen(url,timeout=60) as r: return r.read()

specs=[
 {
  'asset':'AD720950','report':'localization/graphics/role_A/20261004-A-PRODUCTION13/A_PRODUCTION13_AD720950_REPORT.json',
  'dir':'localization/graphics/role_A/20261004-A-PRODUCTION13',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/AD720950_1024x256.dds',
  'source_png':'AD720950_HD_SOURCE_READABLE.png','clean':'AD720950_HD_CLEAN_PLATE.png','final':'AD720950_HD_FINAL_DECODED_READABLE.png',
  'source_mask':'AD720950_HD_SOURCE_TEXT_MASK.png','allowed':'AD720950_HD_ALLOWED_TEXT_REGION_MASK.png','protected':'AD720950_HD_PROTECTED_VISIBLE_MASK.png',
  'rows_kind':'report_rows'
 },
 {
  'asset':'BF3EE5C6','report':'localization/graphics/role_A/20261004-A-PRODUCTION14/A_PRODUCTION14_BF3EE5C6_REPORT.json',
  'dir':'localization/graphics/role_A/20261004-A-PRODUCTION14',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds',
  'source_png':'BF3EE5C6_HD_SOURCE_READABLE.png','clean':'BF3EE5C6_HD_CLEAN_PLATE.png','final':'BF3EE5C6_HD_FINAL_DECODED_READABLE.png',
  'source_mask':'BF3EE5C6_HD_SOURCE_TEXT_MASK.png','allowed':'BF3EE5C6_HD_ALLOWED_TEXT_REGION_MASK.png','protected':'BF3EE5C6_HD_PROTECTED_VISIBLE_MASK.png',
  'rows_kind':'report_rows'
 },
 {
  'asset':'2B0863D6','report':'localization/graphics/role_A/20261004-A-PRODUCTION15/A_PRODUCTION15_2B0863D6_REPORT.json',
  'dir':'localization/graphics/role_A/20261004-A-PRODUCTION15',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/2B0863D6_512x64.dds',
  'source_png':'2B0863D6_HD_SOURCE_READABLE.png','clean':'2B0863D6_HD_CLEAN_PLATE.png','final':'2B0863D6_HD_FINAL_DECODED_READABLE.png',
  'source_mask':'2B0863D6_HD_SOURCE_TEXT_MASK.png','allowed':'2B0863D6_HD_ALLOWED_TEXT_REGION_MASK.png','protected':'2B0863D6_HD_PROTECTED_VISIBLE_MASK.png',
  'rows_kind':'report_rows'
 },
 {
  'asset':'C075FB49','report':'localization/graphics/role_A/20261004-A-RECOVERY10/A_RECOVERY10_C075FB49_REPORT.json',
  'dir':'localization/graphics/role_A/20261004-A-RECOVERY10',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds',
  'local_source':'localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds',
  'source_png':'C075FB49_SOURCE_READABLE.png','clean':'C075FB49_CLEAN_PLATE.png','final':'C075FB49_FINAL_READABLE.png',
  'source_mask':'C075FB49_TOP_SOURCE_TEXT_MASK.png','allowed':'C075FB49_ALLOWED_TEXT_REGION_MASK.png','protected':'C075FB49_PROTECTED_MASK.png',
  'rows_kind':'report_rows','partial_source_mask':True
 },
 {
  'asset':'FD90AA9','report':'localization/graphics/role_A/20261004-A-RECOVERY08/A_RECOVERY08_FD90AA9_REPORT.json',
  'dir':'localization/graphics/role_A/20261004-A-RECOVERY08',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds',
  'local_source':'localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds',
  'clean':'FD90AA9_CLEAN_PLATE_RECOVERY08.png',
  'source_mask':'FD90AA9_SOURCE_TEXT_MASK_RECOVERY08.png','protected':'FD90AA9_CLEAN_PLATE_PROTECTED_MASK_RECOVERY08.png',
  'rows_kind':'fd90'
 }
]

results=[]
for s in specs:
    rep=json.loads((repo/s['report']).read_text(encoding='utf-8')); d=repo/s['dir']
    cb=(repo/s['candidate']).read_bytes(); sb=source_bytes_from_report(rep,s.get('local_source'))
    sh,source,sm=load_dds_bytes(sb); ch,cand,cm=load_dds_bytes(cb)
    candidate_sha=sha_bytes(cb); source_sha=sha_bytes(sb)
    if candidate_sha!=rep['candidate_sha256']: raise RuntimeError((s['asset'],'candidate sha mismatch',candidate_sha,rep['candidate_sha256']))
    if source_sha!=rep['source_sha256']: raise RuntimeError((s['asset'],'source sha mismatch',source_sha,rep['source_sha256']))
    header_exact=(ch==sh)
    if s.get('source_png'):
        src_png=rgba_png(d/s['source_png'])
        source_png_diff=int(np.any(src_png!=source,axis=2).sum())
    else: source_png_diff=0
    clean=rgba_png(d/s['clean'])
    if s.get('final'):
        final_png=rgba_png(d/s['final'])
        final_decode_diff=int(np.any(final_png!=cand,axis=2).sum())
        final=final_png
    else:
        final_decode_diff=0; final=cand
    if not(source.shape==clean.shape==final.shape): raise RuntimeError((s['asset'],'shape mismatch'))
    source_mask=mask_png(d/s['source_mask']); protected=mask_png(d/s['protected'])
    changed_clean=np.any(clean!=source,axis=2)
    source_residue=int(np.logical_and(source_mask,np.all(clean==source,axis=2)).sum())
    clean_outside_mask=None if s.get('partial_source_mask') else int(np.logical_and(changed_clean,~source_mask).sum())
    changed_final=np.any(final!=source,axis=2)
    protected_final=int(np.logical_and(changed_final,protected).sum())
    target=np.any(final!=clean,axis=2)

    # Row metadata: FD90 uses 29 C92 rows with the four recovery rows substituted.
    if s['rows_kind']=='fd90':
        c92=json.loads((repo/'localization/graphics/role_C/20261004-1740-C92/C92_FD90AA9_FINAL_QA.json').read_text(encoding='utf-8'))
        by={r['key']:dict(r) for r in c92['bbox_gate']['rows']}
        for r in rep['reworked_rows']:
            by[r['key']]=dict(r)
        rowdefs=list(by.values())
    else:
        rowdefs=rep['rows']

    allowed_union=np.zeros(target.shape,bool); local_union=np.zeros(target.shape,bool)
    row_results=[]; row_masks=[]
    for r in rowdefs:
        key=r['key']; ob=list(map(int,r['original_bbox'])); lb=list(map(int,r['localized_bbox']))
        allowed_union |= rect(target.shape,ob)
        local_union |= rect(target.shape,lb)
        rm=target & rect(target.shape,lb)
        actual=bb(rm)
        if actual is None: raise RuntimeError((s['asset'],key,'empty localized target'))
        sw,hh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=actual[2]-actual[0],actual[3]-actual[1]
        row_results.append({
          'key':key,'original_bbox':ob,'localized_bbox':actual,
          'delta_left':actual[0]-ob[0],'delta_right':ob[2]-actual[2],
          'delta_top':actual[1]-ob[1],'delta_bottom':ob[3]-actual[3],
          'source_size':[sw,hh],'localized_size':[lw,lh],
          'containment':'PASS' if actual[0]>=ob[0] and actual[1]>=ob[1] and actual[2]<=ob[2] and actual[3]<=ob[3] else 'FAIL',
          'size_ceiling':'PASS' if lw<=sw and lh<=hh else 'FAIL'
        }); row_masks.append((key,rm))
    target_outside_allowed=int(np.logical_and(target,~allowed_union).sum())
    target_outside_localized_boxes=int(np.logical_and(target,~local_union).sum())
    pair_overlap=0; touching=[]
    for i in range(len(row_masks)):
        for j in range(i+1,len(row_masks)):
            ov=int(np.logical_and(row_masks[i][1],row_masks[j][1]).sum())
            near=int(np.logical_and(dil1(row_masks[i][1]),row_masks[j][1]).sum())
            pair_overlap+=ov
            if ov or near: touching.append([row_masks[i][0],row_masks[j][0],ov,near])

    extra={}
    if s['asset']=='FD90AA9':
        prior=subprocess.check_output(['git','show',f"{rep['base_head']}:{s['candidate']}"])
        if sha_bytes(prior)!=rep['input_candidate_sha256']: raise RuntimeError(('FD90 prior sha mismatch',sha_bytes(prior)))
        _,prior_img,_=load_dds_bytes(prior)
        changed_prior=np.any(final!=prior_img,axis=2)
        four=np.zeros(target.shape,bool)
        for r in rep['reworked_rows']: four |= rect(target.shape,r['original_bbox'])
        extra['changed_pixels_vs_input_outside_four_reworked_source_bboxes']=int(np.logical_and(changed_prior,~four).sum())
        extra['preserved_unaffected_report_all_zero']=all(v==0 for v in rep['preserved_unaffected_target_layer_diffs'].values())

    if s.get('allowed'):
        allowed=mask_png(d/s['allowed'])
        allowed_mask_xor_vs_union=int(np.logical_xor(allowed,allowed_union).sum())
        target_outside_persisted_allowed=int(np.logical_and(target,~allowed).sum())
    else:
        allowed_mask_xor_vs_union=None; target_outside_persisted_allowed=None

    machine_pass=(header_exact and source_png_diff==0 and final_decode_diff==0 and source_residue==0 and
        (clean_outside_mask in (None,0)) and protected_final==0 and target_outside_allowed==0 and
        target_outside_localized_boxes==0 and pair_overlap==0 and not touching and
        all(r['containment']=='PASS' and r['size_ceiling']=='PASS' for r in row_results))
    if target_outside_persisted_allowed is not None: machine_pass &= (target_outside_persisted_allowed==0)
    if s['asset']=='FD90AA9':
        machine_pass &= (extra['changed_pixels_vs_input_outside_four_reworked_source_bboxes']==0 and extra['preserved_unaffected_report_all_zero'])

    res={
      'schema_version':1,'role':'C','run':run,'asset':s['asset'],
      'candidate_sha256':candidate_sha,'source_sha256':source_sha,'source_header_128_exact':header_exact,'structure':cm,
      'source_png_vs_decoded_source_diff_pixels':source_png_diff,
      'decoded_candidate_vs_persisted_final_diff_pixels':final_decode_diff,
      'clean_changed_pixels_outside_source_text_mask':clean_outside_mask,
      'source_text_mask_pixels_unchanged_in_clean_plate':source_residue,
      'final_changed_pixels_in_protected_mask':protected_final,
      'target_pixels_outside_union_source_bboxes':target_outside_allowed,
      'target_pixels_outside_union_localized_bboxes':target_outside_localized_boxes,
      'persisted_allowed_mask_xor_vs_union_source_bboxes':allowed_mask_xor_vs_union,
      'target_pixels_outside_persisted_allowed_mask':target_outside_persisted_allowed,
      'localized_pair_overlap_pixels':pair_overlap,'localized_touch_pairs':touching,
      'rows':row_results,'extra':extra,
      'machine_status':'PASS' if machine_pass else 'FAIL',
      'controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'
    }
    (out/f"C109_{s['asset']}_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    results.append(res)

summary={'schema_version':1,'role':'C','run':run,'results':results,
 'machine_pass_assets':[x['asset'] for x in results if x['machine_status']=='PASS'],
 'machine_fail_assets':[x['asset'] for x in results if x['machine_status']!='PASS'],
 'controller_visual_qa':'PENDING','runtime_validation':'UNTESTED','vr_ffb_dx11_dxvk_changes':False}
(out/'C109_MACHINE_QA.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C109_DONE',json.dumps({'pass':summary['machine_pass_assets'],'fail':summary['machine_fail_assets']}),flush=True)
