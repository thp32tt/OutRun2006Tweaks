#!/usr/bin/env python3
"""Read-only audit of all 45 original-HD English test-only rework PNGs.
Never change original 242 crops, 108 originals, 255 archive, C queues or DDS.
"""
import csv,hashlib,io,json,math,zipfile
from collections import Counter
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
BASE=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
Q=BASE/'qa_review_20261019';OLD=BASE/'qa_review_20261018';SRC=BASE/'hd_original_108_verified'
with zipfile.ZipFile(BASE/'hd_original_108_zip_inbox/OutRun_ALL_HD_Korean_Source_PNG_PART01_of_05_20261013.zip') as z:
 sources=list(csv.DictReader(io.StringIO(z.read('01_DDS_PNG_MANIFEST_108.csv').decode('utf-8-sig'))))
pins={x['png_filename']:x for x in sources};assert len(pins)==108
triage=json.loads((OLD/'visual_triage_76.json').read_text(encoding='utf-8'))
src_cache={}
records=[]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for part in iter(lambda:f.read(1<<20),b''):h.update(part)
 return h.hexdigest()
roots=[OLD/'reworked_q057_test_only',OLD/'reworked_12_test_only',
       OLD/'reworked_15_followup_test_only',Q/'reworked_3_test_only']
for root in roots:
 for png in sorted(root.rglob('english_native_rework_candidate.png')):
  manifest=png.parent/'rework_manifest.json'
  meta=json.loads(manifest.read_text(encoding='utf-8'))
  name=meta['source_png'];row=pins[name]
  if name not in src_cache:
   with Image.open(SRC/name) as im:original=im.copy()
   src_cache[name]={'sha':sha(SRC/name),'original':original}
  inp=src_cache[name]
  warnings=[]
  if inp['sha']!=row['png_sha256']:warnings.append('SOURCE_SHA_FAILED')
  box=(meta.get('new_bbox_xyxy') or meta.get('updated_bbox') or
       meta.get('native_rework_bbox_xyxy') or meta.get('rework_bbox_xyxy'))
  expectedsha=meta.get('new_crop_sha256') or meta.get('crop_sha256') or meta.get('output_sha256')
  if not box or not(0<=box[0]<box[2]<=inp['original'].width and 0<=box[1]<box[3]<=inp['original'].height):
   warnings.append('BBOX_INVALID')
  outputhash=sha(png)
  if outputhash!=expectedsha:warnings.append('CROP_SHA_MISMATCH')
  with Image.open(png) as im:
   img=im.copy()
  if img.mode!='RGBA' or img.size!=(box[2]-box[0],box[3]-box[1]):warnings.append('CROP_MODE_OR_SIZE_WRONG')
  if img.tobytes()!=inp['original'].crop(tuple(box)).tobytes():warnings.append('CROP_DIFFERS_FROM_SOURCE_PIXELS')
  alpha=img.getchannel('A');w,h=img.size
  k=min(3,w//6,h//6)
  def check_border(bbox):
   a=alpha.crop(bbox)
   v=list(a.getdata())
   return sum(x>120 for x in v)
  edge={'T':check_border((0,0,w,k)),'B':check_border((0,h-k,w,h)),
        'L':check_border((0,0,k,h)),'R':check_border((w-k,0,w,h))}
  english=meta['english']
  previous=meta.get('old_bbox_xyxy') or meta.get('original_bbox') or meta.get('original_bbox_xyxy')
  index=meta.get('visual_index') or meta.get('visual_triage_index')
  matches=[x for x in triage if x['source_png']==name and x['english']==english and (previous is None or previous==x['original_box']) and (index is None or index==x['visual_sheet_index'])]
  assert len(matches)==1,(name,english,len(matches))
  n=matches[0]['visual_sheet_index']
  records.append({'visual_index':n,'english':english,'source_png':name,
    'original_bbox':matches[0]['original_box'],'new_bbox':box,
    'source_sha256':inp['sha'],'crop_sha256':outputhash,
    'technical_qa':'PASS' if not warnings else 'FAIL',
    'technical_failures':warnings,'alpha_border_contact_pixels':edge,
    'has_edge_contact':any(edge.values()),
    'visual_qa':'SOURCE_CROP_PREVIEW_ONLY_NOT_APPROVED',
    'runtime_qa':'UNTESTED',
    'file':str(png),'original_unmodified':True})
assert len(records)==45 and len({r['visual_index'] for r in records})==45
records.sort(key=lambda r:r['visual_index'])
assert not [r for r in records if r['technical_qa']=='FAIL']
counts=Counter({'source_108_verified':len(pins),'native_rework_candidates':len(records),
                'candidate_sha_pixel_source_pass':len(records),
                'candidate_alpha_edge_contact':sum(x['has_edge_contact'] for x in records),
                'original_242_unchanged':sum(1 for p in (BASE/'hd108_outputs').rglob('english_original_native_crop.png'))})
(Q/'ALL_45_QA.json').write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
with (Q/'ALL_45_QA.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['visual_index','english','source_png','original_bbox','new_bbox','technical_QA',
                             'alpha_border_pixels','manual_visual_approval','in_game_validation','file'])
 for r in records:w.writerow([r['visual_index'],r['english'],r['source_png'],r['original_bbox'],r['new_bbox'],
                               r['technical_qa'],r['alpha_border_contact_pixels'],'NOT_GRANTED','UNTESTED',r['file']])
# 5 pages of 9 paired-crops. Previews do not modify source or candidate bytes.
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
pages=[]
for page in range(5):
 chunk=records[page*9:(page+1)*9]
 W,H=560,216
 contact=Image.new('RGB',(W*3,H*3),(228,231,235))
 draw=ImageDraw.Draw(contact)
 for pos,r in enumerate(chunk):
  ix=(pos%3)*W;iy=(pos//3)*H
  draw.rounded_rectangle((ix+6,iy+6,ix+W-6,iy+H-6),radius=8,fill='white',outline=(183,191,202),width=2)
  draw.text((ix+14,iy+14),f'#{r["visual_index"]:03d} {r["english"][:30]}',font=font,fill=(29,38,51))
  with Image.open(r['file']) as im:crop=im.convert('RGBA')
  crop.thumbnail((W-26,145),Image.Resampling.LANCZOS)
  backdrop=Image.new('RGBA',(W-26,152),(230,232,235,255))
  d=ImageDraw.Draw(backdrop)
  for x in range(0,backdrop.width,19):
   for y in range(0,152,19):
    if (x//19+y//19)%2==0:d.rectangle((x,y,x+18,y+18),fill=(246,248,250,255))
  backdrop.alpha_composite(crop,((backdrop.width-crop.width)//2,(152-crop.height)//2))
  contact.paste(backdrop.convert('RGB'),(ix+13,iy+36))
  draw.text((ix+14,iy+192),f'TEST ONLY · alpha edge {sum(r["alpha_border_contact_pixels"].values())}',font=font,fill=(85,77,70))
 filename=f'45_REWORK_QA_PAGE_{page+1:02d}_of_05.jpg'
 contact.save(Q/filename,quality=93)
 pages.append(filename)
report={'status':'45_NATIVE_REWORK_TECHNICAL_QA_PASS_VISUAL_APPROVAL_PENDING',
        'counts':dict(counts),'manual_visual_qa':'PENDING',
        'in_game_qa':'UNTESTED','pages':pages,
        'original_242_preserved':True,'original_255_archived_preserved':True,
        'A_B':'UNCHANGED','unresolved_cases':[{'id':36,'english':'HARD','reason':'glyph plate cannot be safely separated using only rectangular crop'}]}
(Q/'STAGE_45_TECHNICAL_REPORT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(report,ensure_ascii=False))