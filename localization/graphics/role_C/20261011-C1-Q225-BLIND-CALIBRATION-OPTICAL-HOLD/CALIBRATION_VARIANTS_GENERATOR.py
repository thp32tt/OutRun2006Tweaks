from PIL import Image, ImageFilter, ImageDraw, ImageFont
from pathlib import Path
import secrets, json, hashlib
out=Path('work/c1-visual-calibration-20261011');out.mkdir(exist_ok=True)
src=Image.open('work/c1_q101_a226_1910/A226_SOURCE_READABLE_NATIVE_RGBA.png').convert('RGBA')
roi=src.crop((150,15,1085,160))
w,h=roi.size
px=roi.load()
mask=Image.new('L',(w,h)); mp=mask.load()
for y in range(h):
 for x in range(w):
  r,g,b,a=px[x,y]
  if a>96 and r>160 and g>90 and b<130 and r>g*1.15:
   mp[x,y]=255
base_bg=(1,9,39)
yellow=(255,188,0)
def render(m, ghost=None):
 im=Image.new('RGB',(w,h),base_bg)
 if ghost:
  im.paste((151,97,20),(0,0,w,h),ghost)
 im.paste(yellow,(0,0,w,h),m)
 return im
cases={'normal':render(mask)}
# reversible readable-coordinate direction defect: tilt top left relative to bottom
reverse=mask.transform((w,h),Image.Transform.AFFINE,(1,-0.95,75,0,1,0),resample=Image.Resampling.BILINEAR)
cases['opposite_slant']=render(reverse)
clip=mask.copy()
# deliberately cut narrow vertical paths through multiple yellow glyph contours
from PIL import ImageDraw
d=ImageDraw.Draw(clip); d.rectangle((680,15,693,126),fill=0);d.rectangle((875,40,890,142),fill=0)
cases['clipped_stroke']=render(clip)
ghost=mask.transform((w,h),Image.Transform.AFFINE,(1,0,-8,0,1,-5),resample=Image.Resampling.NEAREST).point(lambda v:int(v*.6))
cases['residue']=render(mask,ghost=ghost)
thick=mask.filter(ImageFilter.MaxFilter(9))
cases['excessive_weight']=render(thick)
names=list(cases); secrets.SystemRandom().shuffle(names)
sheet=Image.new('RGB',(w+60, len(names)*(h+12)),(225,225,225));D=ImageDraw.Draw(sheet)
public=[]
for n,name in enumerate(names):
 label='ABCDE'[n]
 sheet.paste(cases[name],(55,n*(h+12)))
 D.text((15,n*(h+12)+20),label,fill=(20,20,20))
 fn=out/(f'case_{label}.png');cases[name].save(fn)
 public.append({'label':label,'sha256':hashlib.sha256(fn.read_bytes()).hexdigest()})
sheet.save(out/'BLIND_FIVE_CASES.png')
(out/'ANSWER_KEY_SEALED.json').write_text(json.dumps({'mapping':dict(zip('ABCDE',names)),'reference':str(src.getbbox()),'source_file':'work/c1_q101_a226_1910/A226_SOURCE_READABLE_NATIVE_RGBA.png','synthetic_only':True},indent=2))
print(json.dumps({'sheet':str(out/'BLIND_FIVE_CASES.png'),'sha256':hashlib.sha256((out/'BLIND_FIVE_CASES.png').read_bytes()).hexdigest(),'cases':public,'answer_key': 'SEALED_UNREAD'}))