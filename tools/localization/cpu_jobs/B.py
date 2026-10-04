#!/usr/bin/env python3
import os, subprocess
from pathlib import Path

FONT_BLACK=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc')
FONT_BOLD=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
if not (FONT_BLACK.exists() and FONT_BOLD.exists()):
    subprocess.run(['sudo','apt-get','update','-qq'],check=True)
    subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk'],check=True)


# ===== 19CEDB9 producer =====
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops
import struct, hashlib, json, subprocess

repo=Path.cwd()
work=Path('/tmp/outrun_B_worker'); work.mkdir(parents=True,exist_ok=True)
run='20261004-B-RECOVERY04'
outdir=repo/'localization/graphics/role_B'/run
outdir.mkdir(parents=True,exist_ok=True)
srcp=repo/'localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds'
cand=repo/'localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds'
cand.parent.mkdir(parents=True,exist_ok=True)
font_path='/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(p):
    b=Path(p).read_bytes(); assert b[:4]==b'DDS '
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]
    pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
    pf=struct.unpack_from('<I',b,80)[0]; fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]; masks=struct.unpack_from('<IIII',b,92)
    assert fourcc==b'\0\0\0\0' and bpp==32 and masks==(0x000000ff,0x0000ff00,0x00ff0000,0xff000000)
    assert pitch==w*4 and mips==1 and len(b)==128+w*h*4
    raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA')
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],readable,{'width':w,'height':h,'pitch':pitch,'mips':mips,'pf_flags':pf,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks]}
def write_dds(src_path, readable, out_path):
    b=Path(src_path).read_bytes(); raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    out=b[:128]+raw.tobytes('raw','RGBA')
    Path(out_path).write_bytes(out)
    return hashlib.sha256(out).hexdigest()
def count(m): return sum(1 for v in m.getdata() if v)
def binary_alpha(im): return im.getchannel('A').point(lambda v:255 if v else 0)
def rectmask(size,boxes):
    m=Image.new('L',size,0); d=ImageDraw.Draw(m)
    for b in boxes: d.rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=255)
    return m

def render_text(text,bbox,fill,outer,outer_w,inner=None,inner_w=0,max_font=None,slant=0.0):
    x0,y0,x1,y1=bbox; W=x1-x0; H=y1-y0
    dummy=ImageDraw.Draw(Image.new('L',(8,8),0))
    if max_font is None: max_font=H
    for fs in range(max_font,7,-1):
        f=ImageFont.truetype(font_path,fs)
        tb=dummy.textbbox((0,0),text,font=f,stroke_width=outer_w)
        tw,th=tb[2]-tb[0],tb[3]-tb[1]
        pad=outer_w+3
        local=Image.new('RGBA',(tw+2*pad,th+2*pad),(0,0,0,0)); d=ImageDraw.Draw(local)
        pos=(pad-tb[0],pad-tb[1])
        d.text(pos,text,font=f,fill=fill,stroke_width=outer_w,stroke_fill=outer)
        if inner is not None:
            d.text(pos,text,font=f,fill=fill,stroke_width=inner_w,stroke_fill=inner)
        bb0=local.getchannel('A').getbbox()
        if not bb0: continue
        glyph=local.crop(bb0)
        shift=max(0,int(round(abs(slant)*(glyph.height-1))))
        if shift:
            sheared=Image.new('RGBA',(glyph.width+shift,glyph.height),(0,0,0,0))
            for yy in range(glyph.height):
                dx=int(round(slant*(glyph.height-1-yy)))
                if dx<0: dx+=shift
                sheared.paste(glyph.crop((0,yy,glyph.width,yy+1)),(dx,yy))
            glyph=sheared
        if glyph.width<=W-2 and glyph.height<=H-2:
            layer=Image.new('RGBA',src.size,(0,0,0,0))
            px=x0+(W-glyph.width)//2; py=y0+(H-glyph.height)//2
            layer.alpha_composite(glyph,(px,py))
            bb=layer.getchannel('A').getbbox()
            if bb and bb[0]>=x0 and bb[1]>=y0 and bb[2]<=x1 and bb[3]<=y1:
                return layer,fs,bb
    raise RuntimeError('cannot fit '+text+' in '+repr(bbox))

header,src,structinfo=load_dds(srcp)
source_sha=sha(srcp)
assert source_sha=='2472c7aab0751987bd736131b8b4c22be4a7613d9bd1478c9b9f35a615dd6c7e'
# Readable/game orientation regions selected from exact 2048x2048 source. TOP is unchanged and intentionally excluded.
cells={
 'sector2':(8,100,190,160), 'sector1':(208,100,385,160), 'win':(418,100,500,160), 'lose':(528,100,635,160),
 'result':(32,170,247,260), 'ranking':(289,170,555,260), 'stage':(571,170,765,260), 'rank':(788,170,964,260),
 'you':(1759,180,1897,270), 'diff':(1853,300,1975,390), 'sector3':(1832,1170,2013,1245), 'rival':(498,1400,705,1490)
}
# Restrict source masks to actual visible alpha inside each isolated source text cell, then derive permitted bboxes from actual pixels.
source_alpha=binary_alpha(src)
source_masks={}; source_bboxes={}
for k,cell in cells.items():
    m=Image.new('L',src.size,0); crop=source_alpha.crop(cell); m.paste(crop,(cell[0],cell[1]))
    bb=m.getbbox();
    if not bb: raise RuntimeError('empty source mask '+k)
    source_masks[k]=m; source_bboxes[k]=bb
# Sanity expected segmentation: no selected bbox touches its isolation cell except where harmless anti-alias reaches source-defined edge.
print('SOURCE_BBOXES',source_bboxes)
source_text_mask=Image.new('L',src.size,0)
for m in source_masks.values(): source_text_mask=ImageChops.lighter(source_text_mask,m)
allowed=rectmask(src.size,list(source_bboxes.values()))
protected=ImageChops.invert(allowed)
# Clean plate: atlas is transparent around labels; remove only exact source glyph/effect pixels, preserving unrelated art exactly.
clean=src.copy(); cp=clean.load(); sm=source_text_mask.load()
for y in range(src.height):
    for x in range(src.width):
        if sm[x,y]: cp[x,y]=(0,0,0,0)
# Palette sampled from source families.
NAVY=(0,10,65,255); YELLOW=(249,208,12,255); YELLOW2=(245,204,12,255); WHITE=(255,255,255,255); ORANGE=(255,158,41,255)
# Render changed Korean labels natively. Rank1 semantic is composed from rendered '랭크' + preserved original 1P player badge immediately following it.
spec={
 'sector2':('섹터 2',YELLOW,NAVY,5,None,0,0.12),
 'sector1':('섹터 1',YELLOW,NAVY,5,None,0,0.12),
 'win':('승리',WHITE,NAVY,4,None,0,0.0),
 'lose':('패배',WHITE,NAVY,4,None,0,0.0),
 'result':('결과',YELLOW2,NAVY,7,WHITE,3,0.14),
 'ranking':('랭킹',YELLOW2,NAVY,7,WHITE,3,0.14),
 'stage':('스테이지',YELLOW2,NAVY,7,WHITE,3,0.14),
 'rank':('랭크',WHITE,NAVY,6,None,0,0.12),
 'you':('나',YELLOW,NAVY,6,None,0,0.12),
 'diff':('차이',YELLOW,NAVY,5,None,0,0.12),
 'sector3':('섹터 3',YELLOW,NAVY,5,None,0,0.12),
 'rival':('라이벌',ORANGE,NAVY,6,None,0,0.14),
}
final=clean.copy(); layers={}; font_sizes={}; final_bboxes={}; slants={}
for k,(txt,fill,outer,ow,inner,iw,slant) in spec.items():
    layer,fs,bb=render_text(txt,source_bboxes[k],fill,outer,ow,inner,iw,slant=slant)
    slants[k]=slant
    layers[k]=layer; font_sizes[k]=fs; final_bboxes[k]=bb; final.alpha_composite(layer)
# Exact encode/decode roundtrip.
candidate_sha=write_dds(srcp,final,cand)
chead,decoded,cinfo=load_dds(cand)
assert chead==header and cinfo==structinfo and ImageChops.difference(final,decoded).getbbox() is None
# Final target mask and gates.
target=Image.new('L',src.size,0)
for l in layers.values(): target=ImageChops.lighter(target,binary_alpha(l))
for k,bb in final_bboxes.items():
    ob=source_bboxes[k]
    assert bb[0]>=ob[0] and bb[1]>=ob[1] and bb[2]<=ob[2] and bb[3]<=ob[3],(k,ob,bb)
d=ImageChops.difference(src,decoded); bands=d.split(); dm=bands[0]
for b in bands[1:]: dm=ImageChops.lighter(dm,b)
dm=dm.point(lambda v:255 if v else 0)
outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
protected_changes=count(ImageChops.multiply(dm,protected))
ad=ImageChops.difference(src.getchannel('A'),decoded.getchannel('A')).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(ad,ImageChops.invert(allowed)))
assert outside==0 and protected_changes==0 and alpha_outside==0
# Clean plate must differ only on exact source glyph/effect mask.
cd=ImageChops.difference(src,clean); bands=cd.split(); cm=bands[0]
for b in bands[1:]: cm=ImageChops.lighter(cm,b)
cm=cm.point(lambda v:255 if v else 0)
clean_out=count(ImageChops.multiply(cm,ImageChops.invert(source_text_mask)))
residue=count(ImageChops.multiply(binary_alpha(clean),source_text_mask))
assert clean_out==0 and residue==0
# No target overlap between changed labels.
overlap_pairs=[]
keys=list(layers)
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        ov=count(ImageChops.multiply(binary_alpha(layers[keys[i]]),binary_alpha(layers[keys[j]])))
        if ov: overlap_pairs.append([keys[i],keys[j],ov])
assert not overlap_pairs
# Evidence masks and clean plate.
source_text_mask.save(outdir/'19CEDB9_SOURCE_TEXT_MASK.png')
allowed.save(outdir/'19CEDB9_ALLOWED_TEXT_REGION_MASK.png')
protected.save(outdir/'19CEDB9_PROTECTED_MASK.png')
clean.save(outdir/'19CEDB9_CLEAN_PLATE.png')
target.save(outdir/'19CEDB9_TARGET_TEXT_MASK.png')
# Validator files in readable orientation.
srcpng=work/'source_readable.png'; finalpng=work/'final_readable.png'; cleanpng=work/'clean_readable.png'; src.save(srcpng); decoded.save(finalpng); clean.save(cleanpng)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(cleanpng),str(outdir/'19CEDB9_SOURCE_TEXT_MASK.png'),'--report',str(outdir/'B_RECOVERY04_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(finalpng),str(outdir/'19CEDB9_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(outdir/'19CEDB9_PROTECTED_MASK.png'),'--report',str(outdir/'B_RECOVERY04_FINAL_MASK_VALIDATION.json')],check=True)
# Contact sheet: source / clean / final on dark and final on white, top and middle-label crops.
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',22)
def composite(im,bg):
    z=Image.new('RGBA',im.size,bg); z.alpha_composite(im); return z.convert('RGB')
def card(label,im,crop,bg):
    v=composite(im,bg).crop(crop); v.thumbnail((1000,440)); c=Image.new('RGB',(v.width,v.height+32),'white'); c.paste(v,(0,32)); ImageDraw.Draw(c).text((6,2),label,font=font,fill='black'); return c
crops=[('TOP',(0,60,2048,420)),('MID',(0,1120,2048,1540))]
rows=[]
for nm,cr in crops:
    cs=[card(nm+' SOURCE',src,cr,(72,72,72,255)),card(nm+' CLEAN',clean,cr,(72,72,72,255)),card(nm+' FINAL',decoded,cr,(72,72,72,255)),card(nm+' FINAL_WHITE',decoded,cr,(255,255,255,255))]
    W=max(x.width for x in cs); H=sum(x.height for x in cs)+8*(len(cs)-1); row=Image.new('RGB',(W,H),'white'); yy=0
    for c in cs: row.paste(c,(0,yy)); yy+=c.height+8
    rows.append(row)
W=sum(x.width for x in rows)+12; H=max(x.height for x in rows); sheet=Image.new('RGB',(W,H),'white'); xx=0
for r in rows: sheet.paste(r,(xx,0)); xx+=r.width+12
sheet.save(outdir/'B_RECOVERY04_19CEDB9_COMPARE.jpg',quality=94)
# Machine report.
source_names={'sector2':'Sector2','sector1':'Sector1','win':'WIN','lose':'LOSE','result':'Result','ranking':'Ranking','stage':'Stage','rank':'Rank1','you':'You','diff':'Diff','sector3':'Sector3','rival':'Rival'}
ko={'sector2':'섹터 2','sector1':'섹터 1','win':'승리','lose':'패배','result':'결과','ranking':'랭킹','stage':'스테이지','rank':'랭크 1','you':'나','diff':'차이','sector3':'섹터 3','rival':'라이벌'}
rowsrep=[]
for k in keys:
    ob=list(source_bboxes[k]); lb=list(final_bboxes[k])
    rowsrep.append({'key':k,'source':source_names[k],'korean':ko[k],'native_rendered_text':spec[k][0],'semantic_note':'preserved original 1P badge supplies player 1 marker' if k=='rank' else None,'original_bbox':ob,'localized_bbox':lb,'delta_left':lb[0]-ob[0],'delta_right':ob[2]-lb[2],'delta_top':lb[1]-ob[1],'delta_bottom':ob[3]-lb[3],'containment':'PASS','native_font_size':font_sizes[k],'fresh_glyph_slant':slants[k],'prior_localized_raster_resampled':False})
report={
 'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'queue_index':44,'asset':'textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds',
 'source_upstream_repo':'Sonic-TV/OR2006Sprites','source_upstream_commit':'a95efe01d1f136514cef94b0d9e9fd61df021754','source_sha256':source_sha,'candidate_sha256':candidate_sha,
 'candidate_path':'localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds',
 'method':'pinned exact HD upstream source -> isolated source alpha glyph/effect masks -> protected mask -> transparent clean plate -> 12 fresh native-resolution Korean labels -> exact RGBA32 source-header DDS encode -> decoded static QA; TOP unchanged; mph/km/h/numeric/player markers preserved',
 'structure':{**structinfo,'header_128_exact':True,'raw_orientation':'mirror_y','channel_layout':'RGBA masks preserved'},
 'segments_total':13,'segments_materially_changed':12,'segments_preserved_original':1,'preserved_segments':['TOP'],'preserved_nontext':['mph','km/h','numeric markers','1P/2P/3P badges','vehicle sprites','bowling pins','flags','arrows','sector/result numeric glyphs'],
 'clean_plate':{'changed_pixels_outside_source_text_mask':clean_out,'source_text_residue_pixels':residue,'status':'PASS'},
 'containment':{'elements_checked':12,'elements_pass':12,'elements_fail':0,'changed_pixels_outside_permitted_source_bboxes':outside,'alpha_changed_outside_permitted_source_bboxes':alpha_outside,'protected_changes':protected_changes,'target_overlap_pairs':overlap_pairs,'status':'PASS'},
 'rows':rowsrep,'manual_visual_qa':'PENDING_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_RECOVERY04_STATIC_PASS_PENDING_MANUAL_SELF_QA_AND_C'
}
(outdir/'B_RECOVERY04_19CEDB9_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(outdir/'B_RECOVERY04_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':source_sha,'candidate_sha256':candidate_sha,'bbox_pass':'12/12','preserved_TOP':'exact source','clean_plate_residue_pixels':residue,'outside_permitted_bboxes':outside,'alpha_outside_permitted_bboxes':alpha_outside,'protected_changes':protected_changes,'target_overlap_pairs':0,'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SOURCE_SHA',source_sha); print('CANDIDATE_SHA',candidate_sha); print('STRUCT',structinfo); print('FONT_SIZES',font_sizes); print('OUTSIDE',outside,'ALPHA_OUT',alpha_outside,'PROTECTED',protected_changes,'RESIDUE',residue)
for rr in rowsrep: print(rr['key'],rr['source'],rr['korean'],rr['original_bbox'],rr['localized_bbox'],rr['containment'])

# ===== 2DA43E41 canonical C88-return producer =====
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops
import struct,hashlib,json,subprocess
repo=Path.cwd(); work=Path('/tmp/outrun_B_worker'); work.mkdir(parents=True,exist_ok=True)
run='20261004-B-RECOVERY05'; outdir=repo/'localization/graphics/role_B'/run; outdir.mkdir(parents=True,exist_ok=True)
srcp=repo/'localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds'
priorp=work/'2DA_BEFORE_BREC03.dds'; priorp.write_bytes(subprocess.check_output(['git','show','c0e0bd4b79dc0eead4b4a0ed432e48ae76d7f20a:localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds'])); cand=repo/'localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds'
c85p=repo/'localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json'
font_bold='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'; font_black='/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 b=Path(p).read_bytes(); assert b[:4]==b'DDS '
 h=struct.unpack_from('<I',b,12)[0];w=struct.unpack_from('<I',b,16)[0];pitch=struct.unpack_from('<I',b,20)[0];mips=struct.unpack_from('<I',b,28)[0]
 masks=struct.unpack_from('<IIII',b,92);bpp=struct.unpack_from('<I',b,88)[0];fourcc=b[84:88]
 assert masks==(0xff,0xff00,0xff0000,0xff000000) and bpp==32 and fourcc==b'\0\0\0\0' and pitch==w*4 and mips==1
 raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA')
 return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{'width':w,'height':h,'pitch':pitch,'mips':mips,'masks':[hex(x) for x in masks],'bpp':bpp,'fourcc':'00000000'}
def write(src,im,out):
 b=Path(src).read_bytes();raw=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM);o=b[:128]+raw.tobytes('raw','RGBA');Path(out).write_bytes(o);return hashlib.sha256(o).hexdigest()
def count(m):return sum(1 for v in m.getdata() if v)
def bin_alpha(im):return im.getchannel('A').point(lambda v:255 if v else 0)
def rectmask(size,boxes):
 m=Image.new('L',size,0);d=ImageDraw.Draw(m)
 for b in boxes:d.rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=255)
 return m

def shear_glyph(glyph,slant):
 if not slant:return glyph
 shift=max(0,int(round(abs(slant)*(glyph.height-1)))); out=Image.new('RGBA',(glyph.width+shift,glyph.height),(0,0,0,0))
 for y in range(glyph.height):
  dx=int(round(slant*(glyph.height-1-y))); dx=dx if dx>=0 else dx+shift
  out.paste(glyph.crop((0,y,glyph.width,y+1)),(dx,y))
 return out

def render_one(text,bbox,fill,outer,ow,inner=None,iw=0,font_path=font_bold,slant=0,max_font=None):
 x0,y0,x1,y1=bbox;W=x1-x0;H=y1-y0;dummy=ImageDraw.Draw(Image.new('L',(8,8),0)); max_font=max_font or H
 for fs in range(max_font,7,-1):
  f=ImageFont.truetype(font_path,fs);tb=dummy.textbbox((0,0),text,font=f,stroke_width=ow);tw,th=tb[2]-tb[0],tb[3]-tb[1];pad=ow+4
  local=Image.new('RGBA',(tw+pad*2,th+pad*2),(0,0,0,0));d=ImageDraw.Draw(local);pos=(pad-tb[0],pad-tb[1]);d.text(pos,text,font=f,fill=fill,stroke_width=ow,stroke_fill=outer)
  if inner is not None:d.text(pos,text,font=f,fill=fill,stroke_width=iw,stroke_fill=inner)
  bb=local.getchannel('A').getbbox();
  if not bb:continue
  g=shear_glyph(local.crop(bb),slant)
  if g.width<=W-2 and g.height<=H-2:
   lay=Image.new('RGBA',src.size,(0,0,0,0));px=x0+(W-g.width)//2;py=y0+(H-g.height)//2;lay.alpha_composite(g,(px,py));fb=lay.getchannel('A').getbbox()
   if fb and fb[0]>=x0 and fb[1]>=y0 and fb[2]<=x1 and fb[3]<=y1:return lay,fs,fb
 raise RuntimeError((text,bbox))
def render_two(t1,t2,bbox,fill1,fill2,outer,ow,font_path=font_bold,slant=0,max_font=None,gap=3):
 x0,y0,x1,y1=bbox;W=x1-x0;H=y1-y0;dummy=ImageDraw.Draw(Image.new('L',(8,8),0));max_font=max_font or H//2
 for fs in range(max_font,7,-1):
  f=ImageFont.truetype(font_path,fs); gs=[]
  ok=True
  for t,fill in [(t1,fill1),(t2,fill2)]:
   tb=dummy.textbbox((0,0),t,font=f,stroke_width=ow);tw,th=tb[2]-tb[0],tb[3]-tb[1];pad=ow+4
   loc=Image.new('RGBA',(tw+2*pad,th+2*pad),(0,0,0,0));d=ImageDraw.Draw(loc);pos=(pad-tb[0],pad-tb[1]);d.text(pos,t,font=f,fill=fill,stroke_width=ow,stroke_fill=outer);bb=loc.getchannel('A').getbbox();g=shear_glyph(loc.crop(bb),slant);gs.append(g)
  total=sum(g.height for g in gs)+gap
  if max(g.width for g in gs)<=W-2 and total<=H-2:
   lay=Image.new('RGBA',src.size,(0,0,0,0));yy=y0+(H-total)//2
   for g in gs:
    xx=x0+(W-g.width)//2;lay.alpha_composite(g,(xx,yy));yy+=g.height+gap
   fb=lay.getchannel('A').getbbox();return lay,fs,fb
 raise RuntimeError((t1,t2,bbox))

head,src,sinfo=load(srcp);phead,prior,pinfo=load(priorp);assert head==phead and sinfo==pinfo
assert sha(srcp)=='3e00bfda82c2175b28c1d45d3041f91e34ede6de52b867cd867c1c27d4837099';assert sha(priorp)=='02da4680cbb25936aedbb6b61857d7d33b1e10889b5dc427420d4eea7e6e6563'
j=json.load(open(c85p,encoding='utf-8'));a=next(x for x in j['assets'] if x['asset']=='2DA43E41');rows={r['key']:r for r in a['rows']}
failed=['course_sp','wait_now','acceleration','max_speed','view_change','expert','special_course'];passed=['course_or2','wait_other','handling','single_play'];allkeys=[r['key'] for r in a['rows']]
# Canonical source-text removal masks. Text-only rows use source alpha; stats use white-only glyph alpha; view-change excludes the player badge band above y=1020.
source_masks={}
sa=bin_alpha(src)
for k in failed:
 ob=rows[k]['original_bbox'];m=Image.new('L',src.size,0)
 if k in ('acceleration','max_speed'):
  crop=src.crop(tuple(ob)); cm=Image.new('L',crop.size,0); po=crop.load(); mo=cm.load()
  for yy in range(crop.height):
   for xx in range(crop.width):
    r,g,b,al=po[xx,yy]
    if al and max(r,g,b)-min(r,g,b)<=2 and r>=220: mo[xx,yy]=255
  m.paste(cm,(ob[0],ob[1]))
 elif k=='view_change':
  region=(ob[0],1020,ob[2],ob[3]);m.paste(sa.crop(region),(region[0],region[1]))
 else:
  m.paste(sa.crop(tuple(ob)),(ob[0],ob[1]))
 assert m.getbbox(),k;source_masks[k]=m
source_text=Image.new('L',src.size,0)
for m in source_masks.values():source_text=ImageChops.lighter(source_text,m)
# Build canonical clean plate from exact source, only removing source glyph/effect pixels.
clean=src.copy();cp=clean.load();sm=source_text.load()
for y in range(src.height):
 for x in range(src.width):
  if sm[x,y]:cp[x,y]=(0,0,0,0)
# Restore four C85 PASS Korean regions exactly from pre-BREC03 canonical candidate, confined to C85 original bboxes.
final=clean.copy()
for k in passed:
 ob=tuple(rows[k]['original_bbox']);final.paste(prior.crop(ob),(ob[0],ob[1]))
# Canonical source palette sampled directly from header-aware decode.
NAVY=(0,10,57,255);YELLOW=(247,186,24,255);WHITE=(255,255,255,255);RED=(199,50,50,255);CREAM=(255,244,214,255);YELLOW_SPECIAL=(255,203,67,255);GRAY=(32,32,32,255)
layers={};fonts={};final_bboxes={};modes={}
# Fit against C85 permitted original bboxes. Stats intentionally omit ':' because the canonical source colon lies outside the C85 original bbox and remains protected.
layers['course_sp'],fonts['course_sp'],final_bboxes['course_sp']=render_two('OutRun2: SP · 15코스 연속이','선택되었습니다.',tuple(rows['course_sp']['original_bbox']),YELLOW,WHITE,NAVY,6,max_font=98,gap=3);modes['course_sp']='two_line_native'
layers['wait_now'],fonts['wait_now'],final_bboxes['wait_now']=render_two('현재 다른 플레이어를 기다리는 중입니다.','잠시 기다려 주세요.',tuple(rows['wait_now']['original_bbox']),YELLOW,WHITE,NAVY,6,max_font=96,gap=3);modes['wait_now']='two_line_native'
layers['acceleration'],fonts['acceleration'],final_bboxes['acceleration']=render_one('가속도',tuple(rows['acceleration']['original_bbox']),WHITE,(48,48,48,255),1,max_font=66);modes['acceleration']='native_body_source_colon_preserved'
layers['max_speed'],fonts['max_speed'],final_bboxes['max_speed']=render_one('최고 속도',tuple(rows['max_speed']['original_bbox']),WHITE,(48,48,48,255),1,max_font=64);modes['max_speed']='native_body_source_colon_preserved'
# View source is italic white with a dark shadow, not the cyan/gold contaminated style from B_RECOVERY03.
view_box=(3430,1020,3896,1102)
layers['view_change'],fonts['view_change'],final_bboxes['view_change']=render_one('시점 변경 버튼:',view_box,WHITE,NAVY,3,font_path=font_bold,slant=0.14,max_font=72);modes['view_change']='canonical_white_navy_italic_native'
layers['expert'],fonts['expert'],final_bboxes['expert']=render_one('상급자용',tuple(rows['expert']['original_bbox']),RED,NAVY,8,inner=WHITE,iw=3,font_path=font_black,slant=0.10,max_font=105);modes['expert']='canonical_red_white_navy_native'
layers['special_course'],fonts['special_course'],final_bboxes['special_course']=render_one('스페셜 코스',tuple(rows['special_course']['original_bbox']),YELLOW_SPECIAL,NAVY,9,inner=CREAM,iw=4,font_path=font_black,slant=0.10,max_font=130);modes['special_course']='canonical_yellow_cream_navy_native'
for k in failed:final.alpha_composite(layers[k])
newsha=write(srcp,final,cand);chead,decoded,cinfo=load(cand);assert chead==head and cinfo==sinfo and ImageChops.difference(final,decoded).getbbox() is None
# QA allowed regions: exact C85 original bboxes for all 11 elements. View render additionally constrained to its text-only subbox.
allowed=rectmask(src.size,[rows[k]['original_bbox'] for k in allkeys]);protected=ImageChops.invert(allowed);target=Image.new('L',src.size,0)
for l in layers.values():target=ImageChops.lighter(target,bin_alpha(l))
# containment per all elements (prior PASS use exact C85 localized bboxes from canonical prior candidate)
rep=[]
ko={'course_or2':'OutRun2 · 15코스 연속이 / 선택되었습니다.','course_sp':'OutRun2: SP · 15코스 연속이 / 선택되었습니다.','wait_other':'다른 플레이어를 기다리는 중입니다. / 잠시 기다려 주세요.','wait_now':'현재 다른 플레이어를 기다리는 중입니다. / 잠시 기다려 주세요.','acceleration':'가속도:','max_speed':'최고 속도:','handling':'핸들링:','view_change':'시점 변경 버튼:','single_play':'싱글 플레이','expert':'상급자용','special_course':'스페셜 코스'}
for k in allkeys:
 ob=rows[k]['original_bbox'];lb=list(final_bboxes[k]) if k in failed else rows[k]['localized_bbox'];deltas=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]];ok=min(deltas)>=0
 rep.append({'key':k,'source':rows[k]['source'],'korean':ko[k],'original_bbox':ob,'localized_bbox':lb,'delta_left':deltas[0],'delta_right':deltas[1],'delta_top':deltas[2],'delta_bottom':deltas[3],'containment':'PASS' if ok else 'FAIL','reworked':k in failed,'mode':modes.get(k,'preserved_exact_pre_brec03'),**({'native_font_size':fonts[k],'prior_localized_raster_resampled':False} if k in failed else {})})
assert all(x['containment']=='PASS' for x in rep)
# prior PASS exact pixel region check against canonical prior candidate.
prior_checks={}
for k in passed:
 ob=tuple(rows[k]['original_bbox']);prior_checks[k]=count(ImageChops.difference(decoded.crop(ob),prior.crop(ob)).convert('RGB').convert('L').point(lambda v:255 if v else 0))
assert all(v==0 for v in prior_checks.values())
# exact source vs final protected/collateral gates.
d=ImageChops.difference(src,decoded);bands=d.split();dm=bands[0]
for b in bands[1:]:dm=ImageChops.lighter(dm,b)
dm=dm.point(lambda v:255 if v else 0);outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)));prot=count(ImageChops.multiply(dm,protected));ad=ImageChops.difference(src.getchannel('A'),decoded.getchannel('A')).point(lambda v:255 if v else 0);aout=count(ImageChops.multiply(ad,ImageChops.invert(allowed)));assert outside==prot==aout==0
# clean plate only changes source-text mask.
cd=ImageChops.difference(src,clean);bands=cd.split();cm=bands[0]
for b in bands[1:]:cm=ImageChops.lighter(cm,b)
cm=cm.point(lambda v:255 if v else 0);cleanout=count(ImageChops.multiply(cm,ImageChops.invert(source_text)));residue=count(ImageChops.multiply(bin_alpha(clean),source_text));assert cleanout==residue==0
# target overlaps
ovs=[];ks=list(layers)
for i in range(len(ks)):
 for j in range(i+1,len(ks)):
  n=count(ImageChops.multiply(bin_alpha(layers[ks[i]]),bin_alpha(layers[ks[j]])))
  if n:ovs.append([ks[i],ks[j],n])
assert not ovs
# evidence
source_text.save(outdir/'2DA43E41_SOURCE_TEXT_MASK_CANONICAL.png');allowed.save(outdir/'2DA43E41_ALLOWED_TEXT_REGION_MASK.png');protected.save(outdir/'2DA43E41_PROTECTED_MASK.png');clean.save(outdir/'2DA43E41_CLEAN_PLATE_CANONICAL.png');target.save(outdir/'2DA43E41_TARGET_TEXT_MASK.png')
srcpng=work/'2da05_source.png';cleanpng=work/'2da05_clean.png';finpng=work/'2da05_final.png';src.save(srcpng);clean.save(cleanpng);decoded.save(finpng)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(cleanpng),str(outdir/'2DA43E41_SOURCE_TEXT_MASK_CANONICAL.png'),'--report',str(outdir/'B_RECOVERY05_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(finpng),str(outdir/'2DA43E41_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(outdir/'2DA43E41_PROTECTED_MASK.png'),'--report',str(outdir/'B_RECOVERY05_FINAL_MASK_VALIDATION.json')],check=True)
# canonical readable comparison and raw orientation comparison
font=ImageFont.truetype(font_bold,22)
def comp(im,bg):z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
views=[]
for label,im,bg in [('SOURCE_CANONICAL',src,(48,48,48,255)),('PRIOR_PRE_BREC03',prior,(48,48,48,255)),('CLEAN_CANONICAL',clean,(48,48,48,255)),('FINAL_CANONICAL',decoded,(48,48,48,255)),('FINAL_WHITE',decoded,(255,255,255,255))]:
 v=comp(im,bg).crop((0,0,4096,1500));v.thumbnail((1100,410));c=Image.new('RGB',(v.width,v.height+32),'white');c.paste(v,(0,32));ImageDraw.Draw(c).text((6,2),label,font=font,fill='black');views.append(c)
W=max(v.width for v in views);H=sum(v.height for v in views)+8*(len(views)-1);sheet=Image.new('RGB',(W,H),'white');yy=0
for v in views:sheet.paste(v,(0,yy));yy+=v.height+8
sheet.save(outdir/'B_RECOVERY05_2DA43E41_CANONICAL_COMPARE.jpg',quality=94)
# raw exact storage orientation source/final
rawsrc=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM);rawfin=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM);cards=[]
for label,im in [('SOURCE_RAW',rawsrc),('FINAL_RAW',rawfin)]:
 v=comp(im,(48,48,48,255));v.thumbnail((900,900));c=Image.new('RGB',(v.width,v.height+32),'white');c.paste(v,(0,32));ImageDraw.Draw(c).text((6,2),label,font=font,fill='black');cards.append(c)
rawsheet=Image.new('RGB',(sum(c.width for c in cards)+10,max(c.height for c in cards)),'white');xx=0
for c in cards:rawsheet.paste(c,(xx,0));xx+=c.width+10
rawsheet.save(outdir/'B_RECOVERY05_2DA43E41_RAW_COMPARE.jpg',quality=92)
report={'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'queue_index':94,'asset':'textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds','c88_return_reason':'REWORK_REQUIRED_CANONICAL_DECODE_VISUAL_CORRUPTION','source_sha256':sha(srcp),'pre_brec03_candidate_sha256':sha(priorp),'superseded_brec03_sha256':'9f48c04586fe8d7d446760d47345f010bc279ef21f618db44f73c3a548660fcf','candidate_sha256':newsha,'candidate_path':'localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds','decoder_encoder':'DDS masks R=0x000000ff G=0x0000ff00 B=0x00ff0000 A=0xff000000 -> raw RGBA; readable=raw FLIP_TOP_BOTTOM; encode=readable FLIP_TOP_BOTTOM raw RGBA under exact source header','method':'canonical header-aware exact source -> text-specific source masks/protected mask -> canonical clean plate -> exact restore of four prior PASS regions from pre-BREC03 canonical candidate -> seven fresh native Korean rerenders with canonical source palette/style -> raw RGBA exact-header encode -> decoded QA','structure':{**sinfo,'header_128_exact':True,'raw_orientation':'mirror_y'},'reworked_elements':7,'prior_pass_elements_preserved_exact':4,'clean_plate':{'source_text_residue_pixels':residue,'changed_outside_source_text_mask':cleanout,'status':'PASS'},'containment':{'elements_total':11,'elements_pass':11,'elements_fail':0,'changed_pixels_outside_11_original_bboxes':outside,'alpha_changed_outside_11_original_bboxes':aout,'protected_changes':prot,'target_overlap_pairs':ovs,'status':'PASS'},'prior_pass_exact':prior_checks,'rows':rep,'manual_visual_qa':'PENDING_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_RECOVERY05_CANONICAL_STATIC_PASS_PENDING_MANUAL_SELF_QA_AND_C'}
(outdir/'B_RECOVERY05_2DA43E41_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(outdir/'B_RECOVERY05_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':sha(srcp),'candidate_sha256':newsha,'canonical_channel_layout':'raw_RGBA','bbox_pass':'11/11','c88_failed_rework_pass':'7/7','prior_pass_exact':prior_checks,'clean_residue':residue,'outside':outside,'alpha_outside':aout,'protected_changes':prot,'overlaps':0,'header_exact':True,'status':'PASS'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('NEW_SHA',newsha);print('FONTS',fonts);print('PRIOR',prior_checks,'OUTSIDE',outside,'AOUT',aout,'PROT',prot,'RESIDUE',residue)
for x in rep:print(x['key'],x['localized_bbox'],x['delta_left'],x['delta_right'],x['delta_top'],x['delta_bottom'],x['containment'])

# Worker-only summary; shared controller state is intentionally untouched here.
import json, hashlib
def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
summary={
  'status':'PASS',
  'worker':os.environ.get('OUTRUN_CPU_WORKER'),
  'role':os.environ.get('OUTRUN_CPU_ROLE'),
  'trigger_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
  'outputs':{
    '19CEDB9':_sha('localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds'),
    '2DA43E41':_sha('localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds')
  },
  'shared_state_mutated':False,
  'runtime_validation':'UNTESTED'
}
p=Path('localization/graphics/worker_results/B_PRODUCTION_20261004.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
