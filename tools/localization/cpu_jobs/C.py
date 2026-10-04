#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,io
from pathlib import Path
import numpy as np
from PIL import Image

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')

repo=Path.cwd(); run='20261005-C110-NEW-AB'
out=repo/'localization/graphics/role_C'/run; out.mkdir(parents=True,exist_ok=True)

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def rgba_png(p): return np.asarray(Image.open(p).convert('RGBA'))
def mask_png(p): return np.asarray(Image.open(p).convert('L'))>0
def rect(shape,b):
    H,W=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=1; return m
def bb(m):
    y,x=np.nonzero(m)
    return None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def dil1(m):
    p=np.pad(m,1,constant_values=False)
    return p[:-2,:-2]|p[:-2,1:-1]|p[:-2,2:]|p[1:-1,:-2]|p[1:-1,1:-1]|p[1:-1,2:]|p[2:,:-2]|p[2:,1:-1]|p[2:,2:]
def fetch(url):
    with urllib.request.urlopen(url,timeout=60) as r: return r.read()
def decode_rgba32(b):
    if b[:4]!=b'DDS ': raise RuntimeError('not DDS')
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]
    pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]; masks=struct.unpack_from('<IIII',b,92)
    if not(fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and pitch==w*4 and mips==1):
        raise RuntimeError(('unexpected rgba32 DDS',w,h,pitch,mips,fourcc,bpp,masks))
    im=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return np.asarray(im),{'width':w,'height':h,'pitch':pitch,'mips':mips,'format':'RGBA32','raw_orientation':'mirror_y'}
def decode_pillow_dds(b):
    if b[:4]!=b'DDS ': raise RuntimeError('not DDS')
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]
    mips=struct.unpack_from('<I',b,28)[0]; fourcc=b[84:88]
    im=Image.open(io.BytesIO(b)).convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return np.asarray(im),{'width':w,'height':h,'mips':mips,'fourcc':fourcc.decode('ascii','replace'),'raw_orientation':'mirror_y'}

specs=[
 {'asset':'2EA557B4','report':'localization/graphics/role_A/20261005-A-PRODUCTION17/A_PRODUCTION17_2EA557B4_REPORT.json',
  'dir':'localization/graphics/role_A/20261005-A-PRODUCTION17',
  'source_url':'https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds',
  'source_png':'2EA557B4_HD_SOURCE_READABLE.png','clean':'2EA557B4_HD_CLEAN_PLATE.png','final':'2EA557B4_HD_FINAL_DECODED_READABLE.png',
  'source_mask':'2EA557B4_HD_SOURCE_TEXT_MASK.png','allowed':'2EA557B4_HD_ALLOWED_TEXT_REGION_MASK.png','protected':'2EA557B4_HD_PROTECTED_VISIBLE_MASK.png',
  'kind':'dxt5'},
 {'asset':'BF3EE5C6','report':'localization/graphics/role_A/20261005-A-RECOVERY11/A_RECOVERY11_BF3EE5C6_REPORT.json',
  'dir':'localization/graphics/role_A/20261005-A-RECOVERY11',
  'source_url':'https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds',
  'source_png':'BF3EE5C6_HD_SOURCE_READABLE.png','clean':'BF3EE5C6_HD_CLEAN_PLATE.png','final':'BF3EE5C6_HD_FINAL_DECODED_READABLE.png',
  'source_mask':'BF3EE5C6_HD_SOURCE_TEXT_MASK.png','allowed':'BF3EE5C6_HD_ALLOWED_TEXT_REGION_MASK.png','protected':'BF3EE5C6_HD_PROTECTED_VISIBLE_MASK.png',
  'kind':'rgba32'},
 {'asset':'53CE39D5','report':'localization/graphics/role_B/20261005-B-PRODUCTION23/B_PRODUCTION23_53CE_REPORT.json',
  'dir':'localization/graphics/role_B/20261005-B-PRODUCTION23',
  'candidate':'localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds',
  'clean':'53CE39D5_HD_CLEAN_PLATE.png','source_mask':'53CE39D5_HD_SOURCE_TEXT_MASK.png',
  'allowed':'53CE39D5_HD_ALLOWED_TEXT_REGION_MASK.png','protected':'53CE39D5_HD_PROTECTED_MASK.png',
  'target_mask':'53CE39D5_HD_TARGET_TEXT_MASK.png','kind':'rgba32'}
]
results=[]
for s in specs:
    rep=json.loads((repo/s['report']).read_text(encoding='utf-8')); d=repo/s['dir']
    cb=(repo/s['candidate']).read_bytes()
    source_url=s.get('source_url') or rep.get('source_url')
    if not source_url:
        sp=rep['source_provenance']; source_url=f"https://raw.githubusercontent.com/{sp['repository']}/{sp['commit']}/{sp['path']}"
    sb=fetch(source_url)
    if sha_bytes(sb)!=rep['source_sha256']: raise RuntimeError((s['asset'],'source sha mismatch',sha_bytes(sb),rep['source_sha256']))
    if sha_bytes(cb)!=rep['candidate_sha256']: raise RuntimeError((s['asset'],'candidate sha mismatch',sha_bytes(cb),rep['candidate_sha256']))
    header_exact=(sb[:128]==cb[:128])
    if s['kind']=='dxt5':
        source,sm=decode_pillow_dds(sb); cand,cm=decode_pillow_dds(cb)
        if sm['fourcc']!='DXT5' or cm['fourcc']!='DXT5': raise RuntimeError((s['asset'],'not DXT5',sm,cm))
    else:
        source,sm=decode_rgba32(sb); cand,cm=decode_rgba32(cb)
    clean=rgba_png(d/s['clean'])
    if s.get('source_png'):
        src_png=rgba_png(d/s['source_png']); source_png_diff=int(np.any(source!=src_png,axis=2).sum())
    else: source_png_diff=None
    if s.get('final'):
        fp=rgba_png(d/s['final']); final_png_diff=int(np.any(cand!=fp,axis=2).sum())
    else: final_png_diff=None
    if source.shape!=cand.shape or source.shape!=clean.shape: raise RuntimeError((s['asset'],'shape mismatch'))
    source_mask=mask_png(d/s['source_mask']); allowed=mask_png(d/s['allowed']); protected=mask_png(d/s['protected'])
    changed_clean=np.any(clean!=source,axis=2)
    changed_final=np.any(cand!=source,axis=2)
    source_residue=int(np.logical_and(source_mask,np.all(clean==source,axis=2)).sum())
    clean_outside=int(np.logical_and(changed_clean,~source_mask).sum())
    final_outside=int(np.logical_and(changed_final,~allowed).sum())
    protected_changed=int(np.logical_and(changed_final,protected).sum())
    target=np.any(cand!=clean,axis=2)
    if s.get('target_mask'):
        persisted_target=mask_png(d/s['target_mask'])
        target_mask_xor=int(np.logical_xor(target,persisted_target).sum())
    else: target_mask_xor=None

    if s['asset']=='2EA557B4':
        rows=[{'key':'next_round','original_bbox':rep['original_bbox'],'localized_bbox':rep['localized_bbox']}]
    else: rows=rep['rows']
    union_source=np.zeros(target.shape,bool); union_local=np.zeros(target.shape,bool)
    rr=[]; rowm=[]
    for r in rows:
        key=r.get('key') or f"{r.get('target')}_{r.get('line_index')}"
        ob=list(map(int,r['original_bbox'])); lb=list(map(int,r['localized_bbox']))
        union_source |= rect(target.shape,ob); union_local |= rect(target.shape,lb)
        rm=target & rect(target.shape,lb)
        ab=bb(rm)
        if ab is None: raise RuntimeError((s['asset'],key,'empty target'))
        sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=ab[2]-ab[0],ab[3]-ab[1]
        rr.append({'key':key,'original_bbox':ob,'localized_bbox':ab,
          'delta_left':ab[0]-ob[0],'delta_right':ob[2]-ab[2],'delta_top':ab[1]-ob[1],'delta_bottom':ob[3]-ab[3],
          'source_size':[sw,sh],'localized_size':[lw,lh],
          'containment':'PASS' if ab[0]>=ob[0] and ab[1]>=ob[1] and ab[2]<=ob[2] and ab[3]<=ob[3] else 'FAIL',
          'size_ceiling':'PASS' if lw<=sw and lh<=sh else 'FAIL'})
        rowm.append((key,rm))
    target_outside_source=int(np.logical_and(target,~union_source).sum())
    target_outside_local=int(np.logical_and(target,~union_local).sum())
    pair=0; touch=[]
    for i in range(len(rowm)):
        for j in range(i+1,len(rowm)):
            ov=int(np.logical_and(rowm[i][1],rowm[j][1]).sum())
            near=int(np.logical_and(dil1(rowm[i][1]),rowm[j][1]).sum())
            pair+=ov
            if ov or near: touch.append([rowm[i][0],rowm[j][0],ov,near])
    allowed_xor_source_union=int(np.logical_xor(allowed,union_source).sum())

    ok=(header_exact and source_residue==0 and clean_outside==0 and final_outside==0 and protected_changed==0 and
        target_outside_source==0 and target_outside_local==0 and pair==0 and not touch and
        all(x['containment']=='PASS' and x['size_ceiling']=='PASS' for x in rr) and
        (source_png_diff in (None,0)) and (final_png_diff in (None,0)))
    if s['asset']=='53CE39D5':
        ok &= (target_mask_xor==0)
    res={'schema_version':1,'role':'C','run':run,'asset':s['asset'],
      'source_sha256':rep['source_sha256'],'candidate_sha256':rep['candidate_sha256'],'header_128_exact':header_exact,
      'structure_source':sm,'structure_candidate':cm,
      'source_png_vs_independent_decode_diff_pixels':source_png_diff,
      'persisted_final_vs_independent_decode_diff_pixels':final_png_diff,
      'clean_changed_pixels_outside_source_text_mask':clean_outside,
      'source_text_mask_pixels_unchanged_in_clean_plate':source_residue,
      'final_changed_pixels_outside_allowed_mask':final_outside,
      'final_changed_pixels_in_protected_mask':protected_changed,
      'target_mask_xor_vs_persisted_target_mask':target_mask_xor,
      'target_pixels_outside_union_source_bboxes':target_outside_source,
      'target_pixels_outside_union_localized_bboxes':target_outside_local,
      'persisted_allowed_mask_xor_vs_union_source_bboxes':allowed_xor_source_union,
      'localized_pair_overlap_pixels':pair,'localized_touch_pairs':touch,'rows':rr,
      'machine_status':'PASS' if ok else 'FAIL','controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'}
    (out/f"C110_{s['asset']}_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    results.append(res)
summary={'schema_version':1,'role':'C','run':run,'results':results,
 'machine_pass_assets':[x['asset'] for x in results if x['machine_status']=='PASS'],
 'machine_fail_assets':[x['asset'] for x in results if x['machine_status']!='PASS'],
 'runtime_validation':'UNTESTED','vr_ffb_dx11_dxvk_changes':False}
(out/'C110_MACHINE_QA.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C110_DONE',json.dumps({'pass':summary['machine_pass_assets'],'fail':summary['machine_fail_assets']}),flush=True)
