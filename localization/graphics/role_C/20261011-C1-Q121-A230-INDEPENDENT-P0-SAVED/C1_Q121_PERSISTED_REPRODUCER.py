from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np, hashlib, json, struct
root=Path('work/c1q121_20261011'); out=root/'results';out.mkdir(exist_ok=True)
source=Image.open(root/'A215_source_r20.png').convert('RGBA')
clean=Image.open(root/'A215_clean_r20.png').convert('RGBA')
assert source.size==clean.size==(256,73)
box=(3478,379,3734,452)
def decode(path):
  f=path.open('rb');header=f.read(128);f.close()
  assert header[:4]==b'DDS '
  h,w=struct.unpack_from('<II',header,12)
  assert (w,h)==(4096,4096) and path.stat().st_size==128+w*h*4
  im=Image.open(path).convert('RGBA')
  assert im.size==(4096,4096)
  return im,{'width':w,'height':h,'mip_count':struct.unpack_from('<I',header,28)[0],'fourcc':header[84:88].decode('ascii','replace'),'rgb_mask':hex(struct.unpack_from('<I',header,92)[0]),'g_mask':hex(struct.unpack_from('<I',header,96)[0]),'b_mask':hex(struct.unpack_from('<I',header,100)[0]),'a_mask':hex(struct.unpack_from('<I',header,104)[0])}
prior,pr_header=decode(root/'A220.dds'); new,new_header=decode(root/'A230.dds')
read_prior=prior.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
read_new=new.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
p=read_prior.crop(box);n=read_new.crop(box)
sa=np.asarray(source).copy();ca=np.asarray(clean).copy();pa=np.asarray(p).copy();na=np.asarray(n).copy()
mask=np.any(pa!=na,axis=2);alphamask=pa[:,:,3]!=na[:,:,3]
source_matches_p=(np.all(pa==sa,axis=2)&(sa[:,:,3]>0))
source_matches_n=(np.all(na==sa,axis=2)&(sa[:,:,3]>0))
source_to_clean=np.any(sa!=ca,axis=2)
clean_alpha=int((ca[:,:,3]>0).sum())
# Full atlas compare once, preserving provenance/RAW. Pillow source pixels are decoded image, not raw header channel copies.
aa=np.asarray(prior);bb=np.asarray(new)
all_d=np.any(aa!=bb,axis=2)
alpha_d=aa[:,:,3]!=bb[:,:,3]
all_count=int(all_d.sum()); alpha_count=int(alpha_d.sum())
xy=np.argwhere(all_d)
raw_bbox= [int(xy[:,1].min()),int(xy[:,0].min()),int(xy[:,1].max()+1),int(xy[:,0].max()+1)] if len(xy) else None
# RAW changed must fall within mirror-Y of readable 256x73 ROI
rx0,ry0,rx1,ry1=box
raw_allowed=np.zeros((4096,4096),dtype=bool);raw_allowed[4096-ry1:4096-ry0,rx0:rx1]=True
outside=int(np.count_nonzero(all_d & ~raw_allowed));alpha_outside=int(np.count_nonzero(alpha_d & ~raw_allowed))
delta_bbox = [int(z) for z in [np.where(mask)[1].min(),np.where(mask)[0].min(),np.where(mask)[1].max()+1,np.where(mask)[0].max()+1]]
def comp(img,bg):
  base=Image.new('RGBA',img.size,(*bg,255));base.alpha_composite(img)
  return base.convert('RGB')
def panel(bg=(85,85,85),scale=1,raw=False):
  imgs=([source,clean,p,n] if not raw else [source.transpose(Image.Transpose.FLIP_TOP_BOTTOM),clean.transpose(Image.Transpose.FLIP_TOP_BOTTOM),prior.crop((box[0],4096-box[3],box[2],4096-box[1])),new.crop((box[0],4096-box[3],box[2],4096-box[1]))])
  canvas=Image.new('RGB',(256*4+18,73*scale+36),bg)
  draw=ImageDraw.Draw(canvas)
  labels=['SOURCE','CLEAN','A220','A230']
  for i,img in enumerate(imgs):
    item=comp(img,bg)
    if scale!=1:item=item.resize((256*scale,73*scale),Image.Resampling.LANCZOS)
    canvas.paste(item,(i*256,35))
    draw.text((i*256+3,10),labels[i],fill=(255,255,255) if sum(bg)<420 else (30,30,30))
  return canvas
# Separate 100%, 75%, 50% for realistic legibility
for label,bg in [('GRAY',(85,85,85)),('BLACK',(0,0,0)),('WHITE',(255,255,255))]:
  for pct in [100,75,50]:
    frame=panel(bg=bg).crop((0,0,1024,108))
    # preserve labels while scaling complete composite to practical size
    if pct!=100:frame=frame.resize((int(frame.width*pct/100),int(frame.height*pct/100)),Image.Resampling.LANCZOS)
    frame.save(out/f'C1_Q121_SOURCE_CLEAN_A220_A230_{label}_{pct}.png')
panel(raw=True).save(out/'C1_Q121_SOURCE_CLEAN_A220_A230_RAW_100.png')
# New direct exact-pixel source-remnant map, not proof of every pixel being visible defect.
mark=Image.new('RGB',source.size,(25,25,25))
mark.paste(comp(n,(70,70,70)))
d=ImageDraw.Draw(mark)
for yy,xx in np.argwhere(source_matches_n):
  d.point((int(xx),int(yy)),fill=(255,5,255))
mark.resize((1024,292),Image.Resampling.NEAREST).save(out/'C1_Q121_A230_SOURCE_MATCH_REMAINDERS_4X.png')
# Changes in A220→A230 only; exact bounded edit.
changes=Image.new('RGB',source.size,(25,25,25));dc=ImageDraw.Draw(changes)
for yy,xx in np.argwhere(mask):dc.point((int(xx),int(yy)),fill=(255,235,50))
changes.resize((1024,292),Image.Resampling.NEAREST).save(out/'C1_Q121_A220_TO_A230_CHANGED_4X.png')
# RAW control pixel symmetry under flip-Y
native=new.crop((rx0,4096-ry1,rx1,4096-ry0))
raw_mismatch=int(np.count_nonzero(np.any(np.asarray(native.transpose(Image.Transpose.FLIP_TOP_BOTTOM))!=na,axis=2)))
manifest={}
for file in sorted(out.glob('*.png')):
  manifest[file.name]={'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size}
report={'source_roi_sha256':hashlib.sha256((root/'A215_source_r20.png').read_bytes()).hexdigest(),'clean_roi_sha256':hashlib.sha256((root/'A215_clean_r20.png').read_bytes()).hexdigest(),'prior_dds_sha256':hashlib.sha256((root/'A220.dds').read_bytes()).hexdigest(),'new_dds_sha256':hashlib.sha256((root/'A230.dds').read_bytes()).hexdigest(),'header_prior':pr_header,'header_new':new_header,'source_crop_readable':box,'source_roi_size':source.size,'CLEAN_source_alpha_pixels':int((sa[:,:,3]>0).sum()),'CLEAN_alpha_pixels':clean_alpha,'source_to_clean_rgba_changed':int(source_to_clean.sum()),'A220_to_A230_changed_full_rgba_pixels':all_count,'A220_to_A230_changed_full_alpha_pixels':alpha_count,'A220_to_A230_changed_outside_20_region':outside,'A220_to_A230_alpha_changed_outside_20_region':alpha_outside,'A220_to_A230_raw_changed_bbox':raw_bbox,'A220_to_A230_readable_changed_bbox_roi':delta_bbox,'prior_exact_source_visible_positive_rgba':int(source_matches_p.sum()),'new_exact_source_visible_positive_rgba':int(source_matches_n.sum()),'source_exact_removed':int((source_matches_p & ~source_matches_n).sum()),'source_exact_added':int((~source_matches_p & source_matches_n).sum()),'raw_yflip_mismatch':raw_mismatch,'pngs':manifest,'note':'Source ROI PNG only; canonical 67MB English source DDS not re-downloaded. Reference source image SHA is authenticated prior A215 artifact; this run downloads full A220 and A230 DDS and independently decodes native.'}
(out/'C1_Q121_MACHINE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('pngs',)},ensure_ascii=False))
print('FILES',json.dumps(manifest))