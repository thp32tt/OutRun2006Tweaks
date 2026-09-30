from PIL import Image, ImageDraw, ImageFont, ImageChops
from pathlib import Path
import struct, hashlib, json, math

SRC=Path('/mnt/data/FF2462BB_1024x512.dds')
CUR=Path('/mnt/data/a00278/current.dds')
OUT=Path('/mnt/data/a00278/FF2462BB_A00278_v2.dds')
RDIR=Path('/mnt/data/a00278/KOREAN_PNG_REVIEW/FF2462BB'); RDIR.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(p):
 b=p.read_bytes(); h,w=struct.unpack_from('<II',b,12); pitch=struct.unpack_from('<I',b,20)[0]; m=struct.unpack_from('<I',b,28)[0] or 1
 assert b[:4]==b'DDS ' and pitch==w*4 and len(b)==128+w*h*4
 im=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 return b,w,h,m,im
sb,w,h,m,src=decode(SRC); cb,w2,h2,m2,cur=decode(CUR)
assert (w,h,m)==(w2,h2,m2)==(4096,2048,1)
assert sb[:128]==cb[:128]

els=[
 dict(key='SCREAMING', text='고성', box=(9,260,285,301), style='dark', align='left'),
 dict(key='ENTER_ACCOUNT_NAME', text='계정 이름 입력:', box=(2,321,558,361), style='dark', align='left'),
 dict(key='CHEATING', text='부정행위', box=(1122,197,1356,237), style='dark', align='left'),
 dict(key='ENTER_ACCOUNT_PASSWORD', text='계정 비밀번호 입력:', box=(1137,388,1785,429), style='dark', align='left'),
 dict(key='CREATE_ACCOUNT', text='계정 만들기', box=(2180,133,2584,173), style='dark', align='left'),
 dict(key='BAD_NAME', text='부적절한 이름', box=(2241,197,2488,236), style='dark', align='left'),
 dict(key='GOOD_ATTITUDE', text='좋은 태도', box=(2240,261,2603,301), style='dark', align='left'),
 dict(key='DELETE_ACCOUNT_SMALL', text='계정 삭제', box=(2560,393,2961,433), style='dark', align='left'),
 dict(key='LOAD_SAVE', text='불러오기 / 저장', box=(3253,136,3546,181), style='dark', align='left'),
 dict(key='IN_MENU', text='메뉴', box=(2414,9,2580,49), style='white_small', align='center'),
 dict(key='SIGN_IN', text='로그인', box=(0,455,268,518), style='white', align='left'),
 dict(key='DELETE_ACCOUNT_BIG', text='계정 삭제', box=(3,540,641,602), style='white', align='left'),
 dict(key='ENTER_XBOX_PASSCODE', text='XBOX 패스코드 입력', box=(906,456,1875,522), style='white', align='left'),
 dict(key='REGISTER_NEW_ACCOUNT_BIG', text='새 계정 등록', box=(2470,543,3399,606), style='white', align='left'),
 dict(key='LOGIN_TO_ACCOUNT', text='계정 로그인', box=(2470,1333,2920,1380), style='dark', align='center'),
 dict(key='START_1', text='시작', box=(1335,737,1449,785), style='outline', align='center'),
 dict(key='GOAL_1', text='골', box=(1965,737,2068,785), style='outline', align='center'),
 dict(key='START_2', text='시작', box=(2111,737,2225,785), style='outline', align='center'),
 dict(key='GOAL_2', text='골', box=(2741,737,2844,785), style='outline', align='center'),
 dict(key='START_3', text='시작', box=(2887,737,3001,785), style='outline', align='center'),
 dict(key='GOAL_3', text='골', box=(3517,737,3620,785), style='outline', align='center'),
]

# Clean-plate stage: remove only current localized lettering colors in exact source bboxes.
# Source/Candidate are sprite atlases with transparency; unchanged non-letter artwork is retained.
clean=cur.copy()
for e in els:
 x0,y0,x1,y1=e['box']; pix=clean.load()
 if e['style']=='dark':
  target={(63,71,74)}
  for y in range(y0,y1+1):
   for x in range(x0,x1+1):
    r,g,b,a=pix[x,y]
    if a and (r,g,b) in target: pix[x,y]=(0,0,0,0)
 elif e['style'] in ('white','white_small'):
  for y in range(y0,y1+1):
   for x in range(x0,x1+1):
    r,g,b,a=pix[x,y]
    if a and (r,g,b)==(255,255,255): pix[x,y]=(0,0,0,0)
 else: # outline Start/Goal cells are text-only; remove every current pixel in source effect bbox.
  for y in range(y0,y1+1):
   for x in range(x0,x1+1):
    pix[x,y]=(0,0,0,0)

# Native render; no resizing of a flattened final lettering raster.
def text_layer(text, size, style):
 font=ImageFont.truetype(FONT,size)
 sw=4 if style=='outline' else 0
 fill=(255,255,255,255) if style in ('white','white_small','outline') else (63,71,74,255)
 stroke=(0,10,57,255) if style=='outline' else None
 # generous temp layer; draw based on textbbox then crop exactly to alpha bbox
 d0=ImageDraw.Draw(Image.new('RGBA',(8,8),(0,0,0,0)))
 bb=d0.textbbox((0,0),text,font=font,stroke_width=sw)
 W=max(8,bb[2]-bb[0]+16); H=max(8,bb[3]-bb[1]+16)
 im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
 d.text((8-bb[0],8-bb[1]),text,font=font,fill=fill,stroke_width=sw,stroke_fill=stroke)
 ab=im.getchannel('A').getbbox(); assert ab
 return im.crop(ab), font

def target_max(style):
 return {'dark':46,'white_small':46,'white':76,'outline':52}[style]

cand=clean.copy(); records=[]
for e in els:
 x0,y0,x1,y1=e['box']; safe=(x0+2,y0+2,x1-2,y1-2)
 sw=safe[2]-safe[0]+1; sh=safe[3]-safe[1]+1
 chosen=None
 for fs in range(target_max(e['style']),7,-1):
  patch,_=text_layer(e['text'],fs,e['style'])
  if patch.width<=sw and patch.height<=sh:
   chosen=(fs,patch); break
 if not chosen: raise RuntimeError('cannot fit '+e['key'])
 fs,patch=chosen
 if e['align']=='left': px=safe[0]
 else: px=safe[0]+(sw-patch.width)//2
 py=safe[1]+(sh-patch.height)//2
 cand.alpha_composite(patch,(px,py))
 ab=patch.getchannel('A').getbbox(); rb=[px+ab[0],py+ab[1],px+ab[2]-1,py+ab[3]-1]
 assert rb[0]>=safe[0] and rb[1]>=safe[1] and rb[2]<=safe[2] and rb[3]<=safe[3]
 records.append({**e,'candidate_safe_bbox':list(safe),'font':'NotoSansCJK-Bold.ttc','font_size':fs,'render_bbox':rb,'stroke_width':4 if e['style']=='outline' else 0,
                 'fill_rgb':[255,255,255] if e['style']!='dark' else [63,71,74], 'stroke_rgb':[0,10,57] if e['style']=='outline' else None,
                 'source_text_transform':'flip_y raw / readable normal','slant_direction':'none','slant_angle_deg':0.0})

# QA masks/helpers
def changed_mask(a,b):
 d=ImageChops.difference(a,b); r,g,bb,aa=d.split(); return ImageChops.lighter(ImageChops.lighter(r,g),ImageChops.lighter(bb,aa)).point(lambda p:255 if p else 0)
def rect_mask(boxes):
 m=Image.new('L',(w,h),0); d=ImageDraw.Draw(m)
 for x0,y0,x1,y1 in boxes: d.rectangle((x0,y0,x1,y1),fill=255)
 return m
def count(m): return sum(v for i,v in enumerate(m.histogram()) if i)
allbox=rect_mask([e['box'] for e in els]); safemask=rect_mask([r['candidate_safe_bbox'] for r in records])
cur_to_cand=changed_mask(cur,cand); clean_to_cand=changed_mask(clean,cand)
outside_source=count(ImageChops.multiply(cur_to_cand,ImageChops.invert(allbox)))
outside_safe=count(ImageChops.multiply(clean_to_cand,ImageChops.invert(safemask)))
alpha_cur=cur.getchannel('A'); alpha_cand=cand.getchannel('A')
alpha_change=changed_mask(Image.merge('RGBA',(alpha_cur,alpha_cur,alpha_cur,alpha_cur)),Image.merge('RGBA',(alpha_cand,alpha_cand,alpha_cand,alpha_cand)))
alpha_outside=count(ImageChops.multiply(alpha_change,ImageChops.invert(allbox)))
assert outside_source==0 and outside_safe==0 and alpha_outside==0

# Encode exact RGBA32 DDS payload with unchanged header/orientation.
raw=cand.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes('raw','RGBA'); out=cb[:128]+raw
assert len(out)==len(cb)==len(sb) and out[:128]==sb[:128]==cb[:128]
OUT.write_bytes(out)

# Review artifacts.
src.save(RDIR/'source_display.png'); clean.save(RDIR/'clean_plate_display.png'); cand.save(RDIR/'candidate_display.png')
# Native crop comparison, then 2x nearest-neighbor integer scale for inspection.
tiles=[]
for r in records:
 x0,y0,x1,y1=r['box']; pad=5; B=(max(0,x0-pad),max(0,y0-pad),min(w,x1+pad+1),min(h,y1+pad+1))
 ims=[src.crop(B),clean.crop(B),cand.crop(B)]
 tw=sum(i.width for i in ims); th=max(i.height for i in ims)+18
 tile=Image.new('RGBA',(tw,th),(230,230,230,255)); xx=0
 for z in ims: tile.alpha_composite(z,(xx,18)); xx+=z.width
 ImageDraw.Draw(tile).text((2,2),r['key']+'  source | clean | candidate',fill=(0,0,0,255),font=ImageFont.load_default())
 tiles.append(tile.convert('RGB'))
CW=max(t.width for t in tiles); CH=sum(t.height for t in tiles)
comp=Image.new('RGB',(CW,CH),'white'); yy=0
for t in tiles: comp.paste(t,(0,yy)); yy+=t.height
comp=comp.resize((comp.width*2,comp.height*2),Image.Resampling.NEAREST); comp.save(RDIR/'comparison.png')

prompt={
 'contract':'outrun-first-pass-edit-v2','task_id':'LOCALIZATION-LOCALIZATION_A-00278','asset':'FF2462BB','source_dimensions':[w,h],
 'raw_orientation':'mirror_y / readable flip_y','instruction':'EDIT, DO NOT REDESIGN. Replace only the listed source text elements with approved Korean. Preserve all unrelated pixels and transparency. No cover boxes, no source residue, no crop/resize. Render natively and keep effect-inclusive Korean bbox inside each 2px-inset candidate_safe_bbox.',
 'font_identifier':'NotoSansCJK-Bold.ttc (system font; bytes not redistributed)','elements':records,
 'negative':['no English residue','no cover rectangle/panel','no flattened-raster shrink/resample','no changes outside exact source bboxes','no alpha changes outside exact source bboxes','no clipping','no unrelated artwork changes'],
 'self_check':'Before producing the candidate, verify that no source-language text or effect remains; no cover box, patch, seam or invented panel exists; all protected artwork is unchanged; Korean text is fully inside the permitted region and unclipped; canvas, orientation and transparency are unchanged. If any condition cannot be satisfied, do not produce a production candidate.'
}
(RDIR/'generation_prompt.json').write_text(json.dumps(prompt,ensure_ascii=False,indent=2)+'\n','utf-8')
qa={
 'schema':'outrun-a00278-index51-v2-native-rerender-selfqa-v1','task_id':'LOCALIZATION-LOCALIZATION_A-00278','asset':'FF2462BB','index':51,
 'source_sha256':sha(sb),'previous_candidate_sha256':sha(cb),'candidate_sha256':sha(out),'dimensions':[w,h],'format':'RGBA32','mipmaps':m,
 'header_128_exact_source':sb[:128]==out[:128],'header_128_exact_previous':cb[:128]==out[:128],
 'candidate_changed':out!=cb,'elements':records,'outside_exact_source_bboxes_changed_pixels_vs_previous':outside_source,
 'candidate_vs_clean_outside_safe_bbox_changed_pixels':outside_safe,'alpha_changed_outside_exact_source_bboxes':alpha_outside,
 'clean_plate_method':'remove current localized lettering by style palette inside exact source-effect bbox; preserve non-letter current pixels; Start/Goal text-only cells fully cleared',
 'render_method':'native glyph render at final size; measure/refit by rerendering font size; no flattened-raster scaling','source_comparison':'comparison.png',
 'runtime_validation':'UNTESTED','automation_validation':'PENDING','validation_mode':'C_BATCH_GATE'
}
(RDIR/'qa_report.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps({'source':sha(sb),'previous':sha(cb),'candidate':sha(out),'outside_source':outside_source,'outside_safe':outside_safe,'alpha_outside':alpha_outside,'records':records},ensure_ascii=False,indent=2))
