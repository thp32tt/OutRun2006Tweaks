#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

if os.environ.get('OUTRUN_CPU_WORKER') != 'github-actions' or os.environ.get('OUTRUN_CPU_ROLE') != 'B':
    raise SystemExit('This deterministic job must run in the GitHub-hosted localization CPU worker as role B.')

repo=Path.cwd()
run='20261004-B-RECOVERY06'
outdir=repo/'localization/graphics/role_B'/run
outdir.mkdir(parents=True,exist_ok=True)
asset_rel='textures/load/spr_sprani_etc_cvt_Exst/AA04D779_512x512.dds'
candidate=repo/'localization/graphics/hd_candidates'/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
work=Path('/tmp/outrun_B_recovery06'); work.mkdir(parents=True,exist_ok=True)
source=work/'AA04D779_512x512.dds'
source_url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/AA04D779_512x512.dds'
source_sha_expected='1a01e19b2749acdd275d10ff6e82bcb525d6621fd9118fb0c1fa5997c4c1dfa5'

urllib.request.urlretrieve(source_url,source)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=source_sha_expected: raise RuntimeError('canonical HD source SHA mismatch')

def resolve_font(style):
    pattern=f'Noto Sans CJK KR:style={style}'
    try: fp=subprocess.check_output(['fc-match','-f','%{file}',pattern],text=True).strip()
    except Exception: fp=''
    if not fp or not Path(fp).exists() or 'NotoSansCJK' not in Path(fp).name:
        subprocess.run(['sudo','apt-get','update','-qq'],check=True)
        subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk'],check=True)
        fp=subprocess.check_output(['fc-match','-f','%{file}',pattern],text=True).strip()
    if not fp or not Path(fp).exists(): raise RuntimeError(f'font unavailable: {style}')
    return fp
FONT_BLACK=resolve_font('Black'); FONT_BOLD=resolve_font('Bold')

def load_dds(p):
    b=Path(p).read_bytes(); assert b[:4]==b'DDS '
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]
    pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
    pf_flags=struct.unpack_from('<I',b,80)[0]; fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]
    masks=struct.unpack_from('<IIII',b,92)
    assert fourcc==b'\0\0\0\0' and bpp==32
    assert masks==(0x000000ff,0x0000ff00,0x00ff0000,0xff000000)
    assert pitch==w*4 and mips==1 and len(b)==128+w*h*4
    raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA')
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    info={'width':w,'height':h,'pitch':pitch,'mips':mips,'pf_flags':pf_flags,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks]}
    return b[:128],readable,info

def write_dds(src,readable,out):
    b=Path(src).read_bytes(); raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=b[:128]+raw.tobytes('raw','RGBA'); Path(out).write_bytes(payload); return hashlib.sha256(payload).hexdigest()
def bin_alpha(im): return im.getchannel('A').point(lambda v:255 if v else 0)
def count(m): return sum(1 for v in m.getdata() if v)
def rect_mask(size,boxes):
    m=Image.new('L',size,0); d=ImageDraw.Draw(m)
    for b in boxes: d.rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=255)
    return m

def shear(glyph,slant):
    if not slant: return glyph
    shift=max(0,int(round(abs(slant)*(glyph.height-1))))
    out=Image.new('RGBA',(glyph.width+shift,glyph.height),(0,0,0,0))
    for y in range(glyph.height):
        dx=int(round(slant*(glyph.height-1-y)))
        if dx<0: dx+=shift
        out.alpha_composite(glyph.crop((0,y,glyph.width,y+1)),(dx,y))
    return out

def render_lines(lines,bbox,fill,stroke,stroke_w,max_font=120,slant=0.0):
    x0,y0,x1,y1=bbox; W=x1-x0; H=y1-y0; gap=2
    dummy=ImageDraw.Draw(Image.new('L',(8,8),0))
    for fs in range(max_font,9,-1):
        font=ImageFont.truetype(FONT_BLACK,fs)
        metrics=[]
        for s in lines:
            tb=dummy.textbbox((0,0),s,font=font,stroke_width=stroke_w)
            metrics.append((tb,tb[2]-tb[0],tb[3]-tb[1]))
        total_h=sum(m[2] for m in metrics)+gap*(len(lines)-1)
        if max(m[1] for m in metrics)>W-2 or total_h>H-2: continue
        glyphs=[]
        for s,(tb,tw,th) in zip(lines,metrics):
            pad=stroke_w+3
            g=Image.new('RGBA',(tw+2*pad,th+2*pad),(0,0,0,0)); d=ImageDraw.Draw(g)
            d.text((pad-tb[0],pad-tb[1]),s,font=font,fill=fill,stroke_width=stroke_w,stroke_fill=stroke)
            bb=g.getchannel('A').getbbox(); g=g.crop(bb)
            g=shear(g,slant); glyphs.append(g)
        total_h=sum(g.height for g in glyphs)+gap*(len(glyphs)-1)
        if max(g.width for g in glyphs)>W-2 or total_h>H-2: continue
        layer=Image.new('RGBA',src.size,(0,0,0,0)); y=y0+(H-total_h)//2
        for g in glyphs:
            x=x0+(W-g.width)//2; layer.alpha_composite(g,(x,y)); y+=g.height+gap
        bb=layer.getchannel('A').getbbox()
        if bb and bb[0]>=x0 and bb[1]>=y0 and bb[2]<=x1 and bb[3]<=y1:
            return layer,fs,bb
    raise RuntimeError(f'cannot fit {lines} in {bbox}')

header,src,info=load_dds(source)
assert (info['width'],info['height'])==(2048,2048)
# Isolated readable-orientation source-label cells. Boundaries intentionally begin after the adjacent course icon cells.
isolation={
 'sector4':(190,330,385,410),
 'palm_beach':(140,410,390,555), 'coniferous_forest':(140,570,480,710), 'snow_mountain':(140,720,460,860), 'ancient_ruins':(138,870,450,1015), 'bay_area':(140,1020,440,1155), 'big_forest':(305,1190,645,1325),
 'castle_wall':(643,570,940,710), 'industrial_complex':(643,720,970,870), 'metropolis':(643,870,975,1015), 'sunny_beach':(643,1020,930,1155), 'water_falls':(808,1180,1045,1340),
 'alpine':(1146,570,1400,710), 'cloudy_highland':(1146,720,1480,870), 'tulip_garden':(1146,870,1430,1015), 'cape_way':(1146,1020,1510,1155), 'national_park':(1315,1180,1620,1340),
 'deep_lake':(1652,570,2000,710), 'desert':(1652,720,1940,850), 'ghost_forest':(1652,870,1970,1015), 'imperial_avenue':(1652,1020,1985,1155)
}
source_alpha=bin_alpha(src); source_masks={}; source_bboxes={}
for key,cell in isolation.items():
    m=Image.new('L',src.size,0); m.paste(source_alpha.crop(cell),(cell[0],cell[1])); bb=m.getbbox()
    if not bb: raise RuntimeError('empty source label '+key)
    # Isolation must not clip actual source glyph/effect pixels.
    if bb[0]<=cell[0] or bb[1]<=cell[1] or bb[2]>=cell[2] or bb[3]>=cell[3]:
        raise RuntimeError(f'isolation clips source label {key}: cell={cell} bbox={bb}')
    source_masks[key]=m; source_bboxes[key]=bb
source_text=Image.new('L',src.size,0)
for m in source_masks.values(): source_text=ImageChops.lighter(source_text,m)
allowed=rect_mask(src.size,list(source_bboxes.values())); protected=ImageChops.invert(allowed)
# Atlas label cells are transparent behind source glyphs; remove only the exact source alpha footprint.
clean=src.copy(); cp=clean.load(); sm=source_text.load()
for y in range(src.height):
    for x in range(src.width):
        if sm[x,y]: cp[x,y]=(0,0,0,0)

NAVY_STAGE=(0,8,57,255); NAVY_SECTOR=(0,10,65,255); WHITE=(255,255,255,255); YELLOW=(249,208,12,255)
spec={
 'sector4':(['섹터 4'],YELLOW,NAVY_SECTOR,5,0.12),
 'palm_beach':(['팜 비치'],WHITE,NAVY_STAGE,7,0.0),
 'coniferous_forest':(['침엽수림'],WHITE,NAVY_STAGE,7,0.0),
 'snow_mountain':(['스노','마운틴'],WHITE,NAVY_STAGE,7,0.0),
 'ancient_ruins':(['고대 유적'],WHITE,NAVY_STAGE,7,0.0),
 'bay_area':(['베이 에어리어'],WHITE,NAVY_STAGE,7,0.0),
 'big_forest':(['빅 포레스트'],WHITE,NAVY_STAGE,7,0.0),
 'castle_wall':(['캐슬 월'],WHITE,NAVY_STAGE,7,0.0),
 'industrial_complex':(['인더스트리얼','컴플렉스'],WHITE,NAVY_STAGE,7,0.0),
 'metropolis':(['메트로폴리스'],WHITE,NAVY_STAGE,7,0.0),
 'sunny_beach':(['서니 비치'],WHITE,NAVY_STAGE,7,0.0),
 'water_falls':(['워터폴스'],WHITE,NAVY_STAGE,7,0.0),
 'alpine':(['알파인'],WHITE,NAVY_STAGE,7,0.0),
 'cloudy_highland':(['클라우디','하이랜드'],WHITE,NAVY_STAGE,7,0.0),
 'tulip_garden':(['튤립 가든'],WHITE,NAVY_STAGE,7,0.0),
 'cape_way':(['케이프 웨이'],WHITE,NAVY_STAGE,7,0.0),
 'national_park':(['내셔널 파크'],WHITE,NAVY_STAGE,7,0.0),
 'deep_lake':(['딥 레이크'],WHITE,NAVY_STAGE,7,0.0),
 'desert':(['사막'],WHITE,NAVY_STAGE,7,0.0),
 'ghost_forest':(['고스트','포레스트'],WHITE,NAVY_STAGE,7,0.0),
 'imperial_avenue':(['임페리얼','애비뉴'],WHITE,NAVY_STAGE,7,0.0)
}
final=clean.copy(); layers={}; fonts={}; localized_bboxes={}
for key,(lines,fill,stroke,sw,slant) in spec.items():
    layer,fs,bb=render_lines(lines,source_bboxes[key],fill,stroke,sw,slant=slant)
    layers[key]=layer; fonts[key]=fs; localized_bboxes[key]=bb; final.alpha_composite(layer)

cand_sha=write_dds(source,final,candidate)
chead,decoded,cinfo=load_dds(candidate)
assert chead==header and cinfo==info and ImageChops.difference(final,decoded).getbbox() is None
# Exhaustive static gates.
target=Image.new('L',src.size,0)
for l in layers.values(): target=ImageChops.lighter(target,bin_alpha(l))
for key,bb in localized_bboxes.items():
    ob=source_bboxes[key]
    if not (bb[0]>=ob[0] and bb[1]>=ob[1] and bb[2]<=ob[2] and bb[3]<=ob[3]): raise RuntimeError((key,ob,bb))
diff=ImageChops.difference(src,decoded); bands=diff.split(); dm=bands[0]
for b in bands[1:]: dm=ImageChops.lighter(dm,b)
dm=dm.point(lambda v:255 if v else 0)
outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed))); protected_changes=count(ImageChops.multiply(dm,protected))
ad=ImageChops.difference(src.getchannel('A'),decoded.getchannel('A')).point(lambda v:255 if v else 0)
alpha_out=count(ImageChops.multiply(ad,ImageChops.invert(allowed)))
if outside or protected_changes or alpha_out: raise RuntimeError((outside,protected_changes,alpha_out))
cd=ImageChops.difference(src,clean); bands=cd.split(); cm=bands[0]
for b in bands[1:]: cm=ImageChops.lighter(cm,b)
cm=cm.point(lambda v:255 if v else 0)
clean_out=count(ImageChops.multiply(cm,ImageChops.invert(source_text))); residue=count(ImageChops.multiply(bin_alpha(clean),source_text))
if clean_out or residue: raise RuntimeError((clean_out,residue))
overlap=[]; keys=list(layers)
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        n=count(ImageChops.multiply(bin_alpha(layers[keys[i]]),bin_alpha(layers[keys[j]])))
        if n: overlap.append([keys[i],keys[j],n])
if overlap: raise RuntimeError(overlap)
# Persist reproducible evidence.
source_text.save(outdir/'AA04D779_SOURCE_TEXT_MASK.png'); allowed.save(outdir/'AA04D779_ALLOWED_TEXT_REGION_MASK.png'); protected.save(outdir/'AA04D779_PROTECTED_MASK.png'); clean.save(outdir/'AA04D779_CLEAN_PLATE.png'); target.save(outdir/'AA04D779_TARGET_TEXT_MASK.png')
srcpng=work/'source.png'; cleanpng=work/'clean.png'; finalpng=work/'final.png'; src.save(srcpng); clean.save(cleanpng); decoded.save(finalpng)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(cleanpng),str(outdir/'AA04D779_SOURCE_TEXT_MASK.png'),'--report',str(outdir/'B_RECOVERY06_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(finalpng),str(outdir/'AA04D779_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(outdir/'AA04D779_PROTECTED_MASK.png'),'--report',str(outdir/'B_RECOVERY06_FINAL_MASK_VALIDATION.json')],check=True)
# Readable comparison evidence on dark and white backgrounds.
label_font=ImageFont.truetype(FONT_BOLD,22)
def comp(im,bg): z=Image.new('RGBA',im.size,bg); z.alpha_composite(im); return z.convert('RGB')
def card(label,im,bg):
    v=comp(im,bg); v.thumbnail((720,720)); c=Image.new('RGB',(v.width,v.height+32),'white'); c.paste(v,(0,32)); ImageDraw.Draw(c).text((6,2),label,font=label_font,fill='black'); return c
cards=[card('SOURCE',src,(72,72,72,255)),card('CLEAN',clean,(72,72,72,255)),card('FINAL',decoded,(72,72,72,255)),card('FINAL_WHITE',decoded,(255,255,255,255))]
W=cards[0].width+cards[1].width+10; H=cards[0].height+cards[2].height+10; sheet=Image.new('RGB',(W,H),'white'); sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(cards[0].width+10,0)); sheet.paste(cards[2],(0,cards[0].height+10)); sheet.paste(cards[3],(cards[2].width+10,cards[1].height+10)); sheet.save(outdir/'B_RECOVERY06_AA04D779_COMPARE.jpg',quality=94)
# Raw-orientation proof.
sraw=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM); fraw=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
rcards=[card('SOURCE_RAW',sraw,(72,72,72,255)),card('FINAL_RAW',fraw,(72,72,72,255))]; rw=rcards[0].width+rcards[1].width+10; rh=max(x.height for x in rcards); rs=Image.new('RGB',(rw,rh),'white'); rs.paste(rcards[0],(0,0)); rs.paste(rcards[1],(rcards[0].width+10,0)); rs.save(outdir/'B_RECOVERY06_AA04D779_RAW_COMPARE.jpg',quality=92)

source_names={'sector4':'Sector4','palm_beach':'Palm Beach','coniferous_forest':'Coniferous Forest','snow_mountain':'Snow Mountain','ancient_ruins':'Ancient Ruins','bay_area':'Bay Area','big_forest':'Big Forest','castle_wall':'Castle Wall','industrial_complex':'Industrial Complex','metropolis':'Metropolis','sunny_beach':'Sunny Beach','water_falls':'Water Falls','alpine':'Alpine','cloudy_highland':'Cloudy Highland','tulip_garden':'Tulip Garden','cape_way':'Cape Way','national_park':'National Park','deep_lake':'Deep Lake','desert':'Desert','ghost_forest':'Ghost Forest','imperial_avenue':'Imperial Avenue'}
ko={'sector4':'섹터 4','palm_beach':'팜 비치','coniferous_forest':'침엽수림','snow_mountain':'스노 마운틴','ancient_ruins':'고대 유적','bay_area':'베이 에어리어','big_forest':'빅 포레스트','castle_wall':'캐슬 월','industrial_complex':'인더스트리얼 컴플렉스','metropolis':'메트로폴리스','sunny_beach':'서니 비치','water_falls':'워터폴스','alpine':'알파인','cloudy_highland':'클라우디 하이랜드','tulip_garden':'튤립 가든','cape_way':'케이프 웨이','national_park':'내셔널 파크','deep_lake':'딥 레이크','desert':'사막','ghost_forest':'고스트 포레스트','imperial_avenue':'임페리얼 애비뉴'}
rows=[]
for key in source_names:
    ob=list(source_bboxes[key]); lb=list(localized_bboxes[key])
    rows.append({'key':key,'source':source_names[key],'korean':ko[key],'render_lines':spec[key][0],'original_bbox':ob,'localized_bbox':lb,'delta_left':lb[0]-ob[0],'delta_right':ob[2]-lb[2],'delta_top':lb[1]-ob[1],'delta_bottom':ob[3]-lb[3],'containment':'PASS','rework_status':'NEW_CANDIDATE','native_font_size':fonts[key],'prior_localized_raster_resampled':False})
report={'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'queue_index':46,'asset':asset_rel,'readiness_tier':'ONE_STAGE_TO_RENDER','source_upstream_repo':'Sonic-TV/OR2006Sprites','source_upstream_commit':'a95efe01d1f136514cef94b0d9e9fd61df021754','source_url':source_url,'source_sha256':source_sha_expected,'candidate_sha256':cand_sha,'candidate_path':str(candidate.relative_to(repo)),'method':'pinned exact HD source -> isolated source-alpha glyph/effect masks -> protected mask -> transparent clean plate -> 21 fresh native-resolution Korean labels -> exact source-header RGBA32 DDS -> decoded final QA','structure':{**info,'header_128_exact':True,'raw_orientation':'mirror_y','channel_layout':'RGBA masks preserved'},'segments_total':21,'segments_rendered':21,'preserved_original':['REV','TOP','You','player-number labels','icons','course symbols','gray control labels','decorative/numeric art'],'clean_plate':{'changed_pixels_outside_source_text_mask':clean_out,'source_text_residue_pixels':residue,'status':'PASS'},'containment':{'elements_total':21,'elements_pass':21,'elements_fail':0,'changed_pixels_outside_permitted_source_bboxes':outside,'alpha_changed_outside_permitted_source_bboxes':alpha_out,'protected_changes':protected_changes,'target_overlap_pairs':overlap,'status':'PASS'},'rows':rows,'manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_RECOVERY06_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(outdir/'B_RECOVERY06_AA04D779_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(outdir/'B_RECOVERY06_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':source_sha_expected,'candidate_sha256':cand_sha,'bbox_pass':'21/21','clean_plate_residue_pixels':residue,'outside_permitted_bboxes':outside,'alpha_outside_permitted_bboxes':alpha_out,'protected_changes':protected_changes,'target_overlap_pairs':0,'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('B_RECOVERY06_DONE',cand_sha,'bbox=21/21','outside=',outside,'protected=',protected_changes,'residue=',residue)
