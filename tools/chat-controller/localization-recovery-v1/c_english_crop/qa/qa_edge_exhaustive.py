#!/usr/bin/env python3
"""Non-destructive pixel/source QA for all existing C native-HD English crops.
No OCR rerun, ImageGen, game DDS writes, C/A/B state edits, or UI automation.
"""
import csv, hashlib, json, math, os, textwrap, zipfile, io
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops
B=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only')
SOURCES=B/'hd_original_108_verified'
OUTPUT=B/'hd108_outputs'
QA=B/'qa_review_20261018'
QA.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(B/'hd_original_108_zip_inbox/OutRun_ALL_HD_Korean_Source_PNG_PART01_of_05_20261013.zip') as z:
 manifest=list(csv.DictReader(io.StringIO(z.read('01_DDS_PNG_MANIFEST_108.csv').decode('utf-8-sig'))))
expected={j['png_filename']:j for j in manifest}
assert len(expected)==108
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def alpha_stats(a,w,h):
 k=min(4,max(1,h//6),max(1,w//6))
 vals={}
 for side,b in {'top':(0,0,w,k),'bottom':(0,h-k,w,h),'left':(0,0,k,h),'right':(w-k,0,w,h)}.items():
  vals[side]=sum(t>120 for t in a.crop(b).getdata())
 return vals
source_cache={}
counts=Counter()
rows=[]
old_conflicts=[]
for mp in sorted(OUTPUT.glob('*/*/manifest.json')):
 j=json.loads(mp.read_text(encoding='utf-8'))
 name=j['source_png']
 png=mp.parent/'english_original_native_crop.png'
 row={'id':mp.parent.name,'source_png':name,'english':j.get('english',''),
  'crop_png':str(png),'manifest':str(mp),'original_box':j['bbox_xyxy'],
  'status':j.get('status'),'edge_warning':j.get('edge_warning'),
  'ocr_confidence':j.get('ocr_confidence'),'human_review_required':True}
 reasons=[]
 if name not in expected:
  reasons.append('SOURCE_NOT_IN_ORIGINAL_108_MANIFEST')
 else:
  ex=expected[name]
  sp=SOURCES/name
  if not sp.exists() or sp.is_symlink():reasons.append('SOURCE_MISSING_OR_SYMLINK')
  else:
   if name not in source_cache:
    digest=sha(sp)
    with Image.open(sp) as im:source_cache[name]=(digest,im.copy())
   digest,source=source_cache[name]
   if digest!=ex['png_sha256'] or digest!=j['source_sha256']:
    reasons.append('SOURCE_SHA_MISMATCH')
   if source.size!=(int(ex['width']),int(ex['height'])):
    reasons.append('SOURCE_SIZE_MISMATCH')
   b=j['bbox_xyxy']
   if any(type(x)!=int for x in b) or not(0<=b[0]<b[2]<=source.width and 0<=b[1]<b[3]<=source.height):
    reasons.append('BOX_INVALID_OR_OUTSIDE')
   if not png.is_file():reasons.append('OUTPUT_MISSING')
   else:
    if sha(png)!=j['crop_sha256']:reasons.append('CROP_SHA_MISMATCH')
    with Image.open(png) as im:
     out=im.copy()
    if out.mode!='RGBA' or out.size!=(b[2]-b[0],b[3]-b[1]):
     reasons.append('CROP_MODE_OR_SIZE')
    if out.size==(b[2]-b[0],b[3]-b[1]) and out.mode==source.mode:
     if ImageChops.difference(out,source.crop(tuple(b))).getbbox() is not None:
      reasons.append('CROP_PIXELS_DIFFER')
    a=out.getchannel('A')
    row['alpha_at_edge']=alpha_stats(a,*out.size)
    row['crop_size']=[out.width,out.height]
    row['source_size']=[source.width,source.height]
    row['image_edge_crop_contact']=any(x>0 for x in row['alpha_at_edge'].values())
    possible=[max(0,b[0]-min(24,out.height//5)),max(0,b[1]-min(24,out.height//5)),min(source.width,b[2]+min(24,out.height//5)),min(source.height,b[3]+min(24,out.height//5))]
    row['expanded_review_box']=possible
    row['expansion_possible']=possible!=b
    if j.get('edge_warning'):
     counts['edge_review_items']+=1
    else:counts['legacy_items']+=1
 row['technical_issues']=reasons
 row['technical_qa']='FAIL' if reasons else 'PASS'
 row['visual_qa']='REVIEW_REQUIRED' if j.get('edge_warning') else 'UNREVIEWED_HISTORIC'
 row['gameplay_qa']='UNTESTED'
 counts['technical_fail' if reasons else 'technical_pass']+=1
 rows.append(row)
# Check overlaps between review crops at the same source (not necessarily a defect).
by_source={}
for r in rows:by_source.setdefault(r['source_png'],[]).append(r)
def overlap_ratio(a,b):
 x=max(0,min(a[2],b[2])-max(a[0],b[0]));y=max(0,min(a[3],b[3])-max(a[1],b[1]))
 return x*y/max(1,min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1])))
for r in rows:
 others=[]
 for v in by_source[r['source_png']]:
  if v is r:continue
  if overlap_ratio(r['expanded_review_box'],v['original_box'])>.2:
   others.append({'other_id':v['id'],'other_english':v['english']})
 r['neighbor_overlap_if_expanded']=others
 if r['edge_warning'] and others:counts['edge_expansion_collision_risk']+=1
 if r['edge_warning'] and not others:counts['edge_expansion_no_known_collision']+=1
edge=[r for r in rows if r['edge_warning']]
edge.sort(key=lambda a:(a['source_png'],a['english'],a['id']))
# Contact sheets show the exact crop on a checkerboard and context from unchanged original.
tileW,tileH=550,342
columns=3
pages=[]
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
for page_index in range((len(edge)+14)//15):
 chunk=edge[page_index*15:(page_index+1)*15]
 canvas=Image.new('RGB',(columns*tileW,math.ceil(len(chunk)/columns)*tileH),(225,228,233))
 D=ImageDraw.Draw(canvas)
 for k,r in enumerate(chunk):
  x=(k%columns)*tileW;y=(k//columns)*tileH
  D.rounded_rectangle((x+7,y+7,x+tileW-7,y+tileH-7),radius=10,fill=(255,255,255),outline=(176,184,194),width=2)
  title='%03d · %s'%(page_index*15+k+1,r['english'][:29])
  D.text((x+20,y+14),title,font=font,fill=(20,32,48))
  D.text((x+20,y+42),r['source_png'][:57],font=small,fill=(68,78,87))
  crop=Image.open(r['crop_png']).convert('RGBA')
  # ensure no image manipulation in actual stored output; previews only
  display=crop.copy()
  display.thumbnail((tileW-44,112),Image.Resampling.LANCZOS)
  backdrop=Image.new('RGB',(tileW-44,118),(218,225,232))
  bd=ImageDraw.Draw(backdrop)
  for bx in range(0,backdrop.width,20):
   for by in range(0,backdrop.height,20):
    if (bx//20+by//20)%2==0: bd.rectangle((bx,by,bx+19,by+19),fill=(242,244,247))
  dx=(backdrop.width-display.width)//2;dy=(backdrop.height-display.height)//2
  backdrop.paste(display,(dx,dy),display)
  canvas.paste(backdrop,(x+20,y+62))
  # Context panel: original source ROI expanded to show possible other artwork.
  with Image.open(SOURCES/r['source_png']) as orig:
   bx=r['original_box']
   pw=max(32,int((bx[2]-bx[0])*.18));ph=max(32,int((bx[3]-bx[1])*.35))
   cb=(max(0,bx[0]-pw),max(0,bx[1]-ph),min(orig.width,bx[2]+pw),min(orig.height,bx[3]+ph))
   context=orig.crop(cb).convert('RGBA')
   frame=context.copy()
   dr=ImageDraw.Draw(frame)
   dr.rectangle((bx[0]-cb[0],bx[1]-cb[1],bx[2]-cb[0]-1,bx[3]-cb[1]-1),outline=(255,62,43,255),width=max(2,context.width//180))
  frame.thumbnail((tileW-44,115),Image.Resampling.LANCZOS)
  panel=Image.new('RGB',(tileW-44,122),(230,231,234))
  px=(panel.width-frame.width)//2;py=(panel.height-frame.height)//2
  panel.paste(frame,(px,py),frame)
  canvas.paste(panel,(x+20,y+190))
  def fmt(rr):return '/'.join(k[0].upper()+':'+str(n) for k,n in rr['alpha_at_edge'].items())
  D.text((x+20,y+318),fmt(r),font=small,fill=(93,48,31))
 name='EDGE_REVIEW_CONTACT_%02d_of_%02d.jpg'%(page_index+1,(len(edge)+14)//15)
 fp=QA/name
 canvas.save(fp,quality=90,optimize=True)
 pages.append(str(fp))
(QA/'qa_242_all.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
(QA/'qa_76_edge.json').write_text(json.dumps(edge,ensure_ascii=False,indent=2)+'\n')
with (QA/'qa_76_edge.csv').open('w',newline='',encoding='utf-8-sig') as f:
 wr=csv.writer(f)
 wr.writerow(['source_png','english','crop_png','bbox_xyxy','source_sha','crop_sha','technical_qa','visual_qa','alpha_at_edge','neighbor_overlap_if_expanded','operator_decision'])
 for r in edge:
  meta=json.loads(Path(r['manifest']).read_text())
  wr.writerow([r['source_png'],r['english'],r['crop_png'],r['original_box'],meta['source_sha256'],meta['crop_sha256'],r['technical_qa'],r['visual_qa'],r.get('alpha_at_edge'),r['neighbor_overlap_if_expanded'],'PENDING_MANUAL_VISUAL_QA'])
report={'status':'TECHNICAL_QA_COMPLETE_VISUAL_PENDING','inventory_total':len(rows),'edge_candidates':len(edge),'counts':dict(counts),'pages':pages,'read_only_input':True,'source_108_sha_pinned':True,'unchanged_outputs':True,'generated_qa_file_count':len(pages)+3,'next_gate':'HUMAN_VISUAL_REVIEW_OF_EDGE_AND_NEIGHBOR_CONTENT','A_B':'UNTOUCHED'}
(QA/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))