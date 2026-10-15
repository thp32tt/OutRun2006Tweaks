from pathlib import Path
from PIL import Image
import hashlib,json,collections
root=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/full_bulk_20261015')
s=json.loads((root/'summary.json').read_text())
stats=collections.Counter()
fail=[];bytes_total=0
for ent in s['results']:
 for roi in ent.get('candidate_rois',[]):
  d=root/roi['path']
  try:
   m=json.loads((d/'manifest.json').read_text())
   a=d/'english_roi.png';b=d/'imagegen_input_REVIEW.png'
   ha=hashlib.sha256(b.read_bytes()).hexdigest()
   if ha!=m['imagegen_png_sha256']:raise ValueError('OUTPUT_SHA_MISMATCH')
   with Image.open(a) as im:
    if im.mode!='RGBA':raise ValueError('NOT_RGBA_NATIVE')
    w,h=im.size
   with Image.open(b) as im:
    if im.mode!='RGBA' or im.size!=(w*roi['upscale'],h*roi['upscale']):raise ValueError('OUTPUT_SIZE_OR_MODE_MISMATCH')
   stats['valid_output_pairs']+=1
   if m['edge_alpha_present']:stats['alpha_touches_crop_boundary']+=1
   if m['source_kind']=='DIRECT_GITHUB_FULL_HD_SOURCE':stats['direct_source_candidates']+=1
   else:stats['unverified_reassembled_source_candidates']+=1
   bytes_total+=a.stat().st_size+b.stat().st_size
  except Exception as e:
   fail.append({'path':str(d),'reason':str(e)})
stats['output_png_files']=2*stats['valid_output_pairs']
result={'schema':'outrun-text-roi-bulk-audit-v1','registered_sources':s['source_total'],
 'declared_translation_records':s['translation_total'],
 'sources_processed':s['processed_sources'],'candidates':s['candidate_pngs'],
 'count_match':stats['valid_output_pairs']==s['candidate_pngs'],
 'statistics':dict(stats),'png_total_bytes':bytes_total,'failures':fail[:25],
 'blocked_sources':s['hold_sources'],'status':'PIL_RGBA_SHA_DIMENSION_AUDIT_COMPLETE_NOT_SEMANTIC_QA',
 'approved_imagegen_inputs_from_this_bulk':0,'RUNTIME_VALIDATION':'UNTESTED'}
p=root/'bulk_audit.json';p.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False),flush=True)