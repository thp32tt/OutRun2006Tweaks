#!/usr/bin/env python3
import os,json,hashlib,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd()
run='20261004-2124-C102'
out=repo/'localization/graphics/role_C'/run
out.mkdir(parents=True,exist_ok=True)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def rgba(p, flip=False):
    im=Image.open(p).convert('RGBA')
    return np.asarray(ImageOps.flip(im) if flip else im)

def mask(p):
    return np.asarray(Image.open(p).convert('L'))>0

def bb(m):
    y,x=np.nonzero(m)
    if len(x)==0:return None
    return [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]

def header_info(p):
    b=Path(p).read_bytes()[:128]
    if b[:4]!=b'DDS ': raise RuntimeError(('not_dds',str(p)))
    h,w,pitch=struct.unpack_from('<III',b,12)
    mip=struct.unpack_from('<I',b,28)[0]
    pf=struct.unpack_from('<8I',b,76)
    return {
      'width':w,'height':h,'pitch':pitch,'mipmaps':mip,
      'pf_size':pf[0],'pf_flags':pf[1],'fourcc':pf[2],
      'rgb_bits':pf[3],'r_mask':pf[4],'g_mask':pf[5],'b_mask':pf[6],'a_mask':pf[7]
    }

results=[]

# 1) A_PRODUCTION16 / 841E796B: independent C scan from persisted exact source PNG,
# clean plate, final decode, masks, and actual candidate DDS.
a_dir=repo/'localization/graphics/role_A/20261004-A-PRODUCTION16'
a_rep=json.loads((a_dir/'A_PRODUCTION16_841E796B_REPORT.json').read_text(encoding='utf-8'))
a_cand=repo/a_rep['candidate_path']
src=rgba(a_dir/'841E796B_HD_SOURCE_READABLE.png')
clean=rgba(a_dir/'841E796B_HD_CLEAN_PLATE.png')
final_png=rgba(a_dir/'841E796B_HD_FINAL_DECODED_READABLE.png')
cand=rgba(a_cand,flip=True)
allowed=mask(a_dir/'841E796B_HD_ALLOWED_LINE_BBOX_MASK.png')
protected=mask(a_dir/'841E796B_HD_PROTECTED_VISIBLE_MASK.png')
source_text=mask(a_dir/'841E796B_HD_SOURCE_TEXT_MASK.png')
if not (src.shape==clean.shape==final_png.shape==cand.shape): raise RuntimeError('841 shape mismatch')
roundtrip=int(np.any(cand!=final_png,axis=2).sum())
changed=np.any(final_png!=src,axis=2)
clean_changed=np.any(clean!=src,axis=2)
target=np.any(final_png!=clean,axis=2)
outside=int(np.logical_and(changed,~allowed).sum())
clean_outside=int(np.logical_and(clean_changed,~source_text).sum())
target_protected=int(np.logical_and(target,protected).sum())
rows=[]
row_masks=[]
for r in a_rep['rows']:
    x0,y0,x1,y1=map(int,r['original_bbox'])
    rm=np.zeros(target.shape,bool); rm[y0:y1,x0:x1]=target[y0:y1,x0:x1]
    lb=bb(rm)
    if lb is None: raise RuntimeError(('841 empty target',r['key']))
    sw,sh=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    rec={
      'key':r['key'],'original_bbox':[x0,y0,x1,y1],'localized_bbox':lb,
      'delta_left':lb[0]-x0,'delta_right':x1-lb[2],
      'delta_top':lb[1]-y0,'delta_bottom':y1-lb[3],
      'source_size':[sw,sh],'localized_size':[lw,lh],
      'containment':'PASS' if lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1 else 'FAIL',
      'size_ceiling':'PASS' if lw<=sw and lh<=sh else 'FAIL'
    }
    rows.append(rec);row_masks.append(rm)
pair_overlap=sum(int(np.logical_and(row_masks[i],row_masks[j]).sum()) for i in range(len(row_masks)) for j in range(i+1,len(row_masks)))
positive_gap=rows[1]['localized_bbox'][1]-rows[0]['localized_bbox'][3]
ah=header_info(a_cand)
a_pass=(sha(a_cand)==a_rep['candidate_sha256'] and ah['width']==2048 and ah['height']==512 and ah['rgb_bits']==32 and
        ah['r_mask']==0xff and ah['g_mask']==0xff00 and ah['b_mask']==0xff0000 and ah['a_mask']==0xff000000 and
        roundtrip==0 and outside==0 and clean_outside==0 and target_protected==0 and pair_overlap==0 and positive_gap>0 and
        all(x['containment']=='PASS' and x['size_ceiling']=='PASS' for x in rows))
a_result={
 'asset':'841E796B','source_result':'A_PRODUCTION16','candidate_sha256':sha(a_cand),
 'structure':ah,'candidate_matches_producer_sha':sha(a_cand)==a_rep['candidate_sha256'],
 'decoded_candidate_vs_persisted_final_diff_pixels':roundtrip,
 'final_changed_pixels_outside_exact_allowed_mask':outside,
 'clean_changed_pixels_outside_source_text_mask':clean_outside,
 'localized_target_vs_protected_visible_overlap_pixels':target_protected,
 'localized_pair_overlap_pixels':pair_overlap,'positive_interline_gap_px':positive_gap,
 'rows':rows,'machine_status':'PASS' if a_pass else 'FAIL',
 'controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'
}
(out/'C102_841E796B_MACHINE_QA.json').write_text(json.dumps(a_result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
results.append(a_result)

# 2) B_RECOVERY09 / A064FDFC: independent C machine scan from canonical source DDS,
# selected clean plate/allowed/target masks, actual candidate DDS and producer row geometry.
b_dir=repo/'localization/graphics/role_B/20261004-B-RECOVERY09'
b_rep=json.loads((b_dir/'B_RECOVERY09_A064FDFC_REPORT.json').read_text(encoding='utf-8'))
b_cand=repo/b_rep['asset'].replace('textures/','localization/graphics/hd_candidates/textures/')
b_source=repo/'localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds'
bsrc=rgba(b_source,flip=True); bcand=rgba(b_cand,flip=True)
bclean=rgba(b_dir/'A064FDFC_SELECTED_CLEAN_PLATE.png')
ballowed=mask(b_dir/'A064FDFC_SELECTED_ALLOWED_REGION_MASK.png')
persist_target=mask(b_dir/'A064FDFC_NEW_TARGET_MASK.png')
if not (bsrc.shape==bcand.shape==bclean.shape): raise RuntimeError('A064 shape mismatch')
derived_target=np.any(bcand!=bclean,axis=2)
outside_target=int(np.logical_and(derived_target,~ballowed).sum())
target_xor=int(np.logical_xor(derived_target,persist_target).sum())
rows2=[];masks2=[]
for r in b_rep['rows']:
    x0,y0,x1,y1=map(int,r['original_bbox'])
    rm=np.zeros(derived_target.shape,bool); rm[y0:y1,x0:x1]=derived_target[y0:y1,x0:x1]
    lb=bb(rm)
    if lb is None: raise RuntimeError(('A064 empty target',r['key']))
    sw,sh=x1-x0,y1-y0;lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    rows2.append({
      'key':r['key'],'original_bbox':[x0,y0,x1,y1],'localized_bbox':lb,
      'delta_left':lb[0]-x0,'delta_right':x1-lb[2],'delta_top':lb[1]-y0,'delta_bottom':y1-lb[3],
      'source_size':[sw,sh],'localized_size':[lw,lh],
      'containment':'PASS' if lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1 else 'FAIL',
      'size_ceiling':'PASS' if lw<=sw and lh<=sh else 'FAIL'
    });masks2.append(rm)
pair2=sum(int(np.logical_and(masks2[i],masks2[j]).sum()) for i in range(len(masks2)) for j in range(i+1,len(masks2)))
bh=header_info(b_cand)
source_header=Path(b_source).read_bytes()[:128]
candidate_header=Path(b_cand).read_bytes()[:128]
b_pass=(sha(b_cand)==b_rep['candidate_sha256'] and candidate_header==source_header and outside_target==0 and
        pair2==0 and all(x['containment']=='PASS' and x['size_ceiling']=='PASS' for x in rows2))
b_result={
 'asset':'A064FDFC','source_result':'B_RECOVERY09','candidate_sha256':sha(b_cand),
 'source_sha256':sha(b_source),'candidate_matches_producer_sha':sha(b_cand)==b_rep['candidate_sha256'],
 'structure':bh,'source_header_128_exact':candidate_header==source_header,
 'derived_localized_target_pixels_outside_selected_allowed_mask':outside_target,
 'derived_vs_persisted_target_mask_xor_pixels':target_xor,
 'localized_pair_overlap_pixels':pair2,'rows':rows2,
 'machine_status':'PASS' if b_pass else 'FAIL',
 'controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'
}
(out/'C102_A064FDFC_MACHINE_QA.json').write_text(json.dumps(b_result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
results.append(b_result)

summary={
 'schema_version':1,'role':'C','run':run,
 'scope':'new/changed A_PRODUCTION16 841E796B plus C-returned B_RECOVERY09 A064FDFC only; completed unrelated assets not repeated',
 'results':results,
 'machine_pass_assets':[x['asset'] for x in results if x['machine_status']=='PASS'],
 'machine_fail_assets':[x['asset'] for x in results if x['machine_status']!='PASS'],
 'controller_visual_qa':'PENDING',
 'runtime_validation':'UNTESTED',
 'vr_ffb_dx11_dxvk_changes':False
}
(out/'C102_CROSS_LANE_MACHINE_QA.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C102_DONE',json.dumps({'machine_pass_assets':summary['machine_pass_assets'],'machine_fail_assets':summary['machine_fail_assets']}),flush=True)
