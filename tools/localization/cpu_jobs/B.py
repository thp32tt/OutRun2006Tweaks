#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,zipfile
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':
    raise SystemExit('B hosted worker only')
repo=Path.cwd(); run='20261004-B-RECOVERY09'
outdir=repo/'localization/graphics/role_B'/run; outdir.mkdir(parents=True,exist_ok=True)
asset='textures/load/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds'
source_zip=repo/'localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip'
hist_zip=repo/'localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip'
candidate=repo/'localization/graphics/hd_candidates'/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
source_sha_expected='9caaf9d94bb853f8cc00faad6bf03fb6460e893a726c5e200fe4a7826768f3bf'
T=[
 ('giant_statues','Giant Statues','자이언트 스태추스',(0,590,360,675),.10),
 ('cape_way','Cape Way','케이프 웨이',(1570,650,1850,750),.10),
 ('imperial_avenue','Imperial Avenue','임페리얼 애비뉴',(1840,650,2290,750),.10),
 ('ancient_ruins','Ancient Ruins','에인션트 루인스',(2260,650,2630,750),.10),
 ('metropolis','Metropolis','메트로폴리스',(2620,650,2980,750),.10),
 ('tulip_garden','Tulip Garden','튤립 가든',(2970,650,3340,750),.10),
 ('skyscrapers','Skyscrapers','스카이스크레이퍼스',(3320,650,3710,750),.10),
 ('milky_way','Milky Way','밀키 웨이',(3690,650,4096,750),.10),
 ('floral_village','Floral Village','플로럴 빌리지',(3600,750,4096,855),.10),
 ('legend','Legend','레전드',(3700,850,4010,970),.10),
 ('normal_top_left','NORMAL','일반',(620,850,980,970),.10),
 ('tuned_top_mid1','TUNED','튜닝',(1250,850,1580,970),.10),
 ('tuned_top_mid2','TUNED','튜닝',(1880,850,2240,970),.10),
 ('outrun_mode_big','OutRun MODE','아웃런 모드',(230,965,1110,1125),.11),
 ('time_attack_mode_big','Time Attack MODE','타임 어택 모드',(1120,960,2400,1125),.11),
 ('continuous_ranking','15 Continuous Course Ranking','15코스 연속 랭킹',(2420,960,4096,1135),.06),
 ('top_runners','Top Runners of Each Goal','각 골별 최고 기록',(0,1080,1330,1250),.06),
 ('heart_attack_big','Heart Attack MODE','하트 어택 모드',(2550,1110,3730,1290),.10),
 ('normal_top_right','NORMAL','일반',(3720,1110,4096,1290),.10),
 ('small1_mode','Time Attack MODE','타임 어택 모드',(40,1250,650,1342),.03),
 ('small1_tuned','TUNED','튜닝',(40,1342,360,1440),.03),
 ('small2_mode','Time Attack MODE','타임 어택 모드',(650,1250,1280,1342),.03),
 ('small2_normal','NORMAL','일반',(650,1342,1050,1440),.03),
 ('small3_mode','Time Attack MODE','타임 어택 모드',(1270,1250,1940,1342),.03),
 ('small3_normal','NORMAL','일반',(1270,1342,1680,1440),.03),
 ('outrun_mode_small','OutRun MODE','아웃런 모드',(1930,1250,2410,1445),.03),
 ('small4_mode','Time Attack MODE','타임 어택 모드',(3060,1420,3710,1518),.03),
 ('small4_tuned','TUNED','튜닝',(3060,1518,3430,1620),.03),
 ('goal_e1','GOAL E','골 E',(180,1435,660,1640),.02),
 ('goal_d1','GOAL D','골 D',(800,1435,1280,1640),.02),
 ('goal_c1','GOAL C','골 C',(1430,1435,1930,1640),.02),
 ('goal_b1','GOAL B','골 B',(2070,1435,2580,1640),.02),
 ('goal_a1','GOAL A','골 A',(2700,1435,3220,1640),.02),
 ('course_sp','OutRun2SP 15 Continuous Course','아웃런2 SP 15코스 연속',(0,1625,1320,1840),.00),
 ('goal_e2','GOAL E','골 E',(1430,1625,1930,1840),.02),
 ('goal_d2','GOAL D','골 D',(2070,1625,2580,1840),.02),
 ('goal_c2','GOAL C','골 C',(2700,1625,3220,1840),.02),
 ('goal_b2','GOAL B','골 B',(3320,1625,3860,1840),.02),
 ('course_or2','OutRun2 15 Continuous Course','아웃런2 15코스 연속',(2700,1825,4096,2070),.00),
 ('goal_a3','GOAL A','골 A',(3320,2060,3830,2300),.02),
 ('tuned_bottom','TUNED','튜닝',(3630,2570,4000,2790),.10),
]

with zipfile.ZipFile(source_zip) as z: sb=z.read(asset)
with zipfile.ZipFile(hist_zip) as z: hb=z.read(asset)
if hashlib.sha256(sb).hexdigest()!=source_sha_expected: raise RuntimeError('source SHA mismatch')
source_file=Path('/tmp/C598_source.dds'); hist_file=Path('/tmp/C598_hist.dds')
source_file.write_bytes(sb); hist_file.write_bytes(hb)
def meta(data):
    h=struct.unpack_from('<I',data,12)[0];w=struct.unpack_from('<I',data,16)[0]
    mips=struct.unpack_from('<I',data,28)[0];fourcc=data[84:88]
    need=128+((w+3)//4)*((h+3)//4)*16
    if fourcc!=b'DXT5' or mips!=1 or len(data)!=need: raise RuntimeError((w,h,mips,fourcc,len(data),need))
    return {'width':w,'height':h,'mips':mips,'fourcc':'DXT5','bytes':len(data)}
info=meta(sb); assert (info['width'],info['height'])==(4096,4096)
src=Image.open(source_file).convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
hist=Image.open(hist_file).convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8);ha=np.asarray(hist,dtype=np.uint8);H,W=sa.shape[:2]
diff=np.any(sa!=ha,axis=2);visible=(sa[:,:,3]>1)|(ha[:,:,3]>1)
hint=np.asarray(Image.fromarray(((diff&visible)*255).astype(np.uint8),'L').filter(ImageFilter.MaxFilter(17)))>0

def get_font():
    pat='Noto Sans CJK KR:style=Black'
    p=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
    if not p or not Path(p).exists() or 'NotoSansCJK' not in Path(p).name:
        subprocess.run(['sudo','apt-get','update','-qq'],check=True)
        subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk','libnvtt-bin'],check=True)
        p=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
    return p
FONT=get_font()
if not Path('/usr/bin/nvcompress').exists():
    subprocess.run(['sudo','apt-get','update','-qq'],check=True)
    subprocess.run(['sudo','apt-get','install','-y','-qq','libnvtt-bin'],check=True)

source_masks={};bboxes={};mask_meta={};union_text=np.zeros((H,W),bool);failures=[]
for key,en,ko,cell,slant in T:
    x0,y0,x1,y1=cell
    local_hint=hint[y0:y1,x0:x1]; local_alpha=sa[y0:y1,x0:x1,3]>1
    mask=local_hint & local_alpha
    ys,xs=np.nonzero(mask)
    if not len(xs):
        failures.append([key,'empty_mask',cell]); continue
    mm=Image.fromarray((mask*255).astype(np.uint8),'L').filter(ImageFilter.MaxFilter(5))
    mask=(np.asarray(mm)>0)&local_alpha;ys,xs=np.nonzero(mask)
    bb=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]
    margins=[bb[0]-x0,bb[1]-y0,x1-bb[2],y1-bb[3]]
    density=float(np.count_nonzero(mask)/max(1,(bb[2]-bb[0])*(bb[3]-bb[1])))
    if min(margins)<=0: failures.append([key,'mask_touches_cell',cell,bb,margins])
    if density>0.85: failures.append([key,'suspicious_density',density,bb])
    full=np.zeros((H,W),bool); full[y0:y1,x0:x1]=mask
    source_masks[key]=full;bboxes[key]=bb;union_text|=full
    mask_meta[key]={'cell':list(cell),'source_bbox':bb,'cell_margins':margins,'alpha_pixels':int(np.count_nonzero(mask)),'bbox_density':density,'hint_pixels':int(np.count_nonzero(local_hint))}
if failures:
    (outdir/'B_RECOVERY09_MASK_PREFLIGHT_FAILURE.json').write_text(json.dumps({'failures':failures,'mask_meta':mask_meta},ensure_ascii=False,indent=2)+'\n')
    raise RuntimeError('mask preflight '+repr(failures[:8]))
keys=list(bboxes)
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        a=bboxes[keys[i]];b=bboxes[keys[j]]
        if max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3]):
            raise RuntimeError(('bbox_overlap',keys[i],keys[j],a,b))

clean_arr=sa.copy();clean_arr[union_text]=(0,0,0,0);clean=Image.fromarray(clean_arr,'RGBA')
def palette(mask,bb):
    p=sa[mask];coords=np.argwhere(mask);valid=p[:,3]>8;p=p[valid];coords=coords[valid]
    if len(p)<10:return (255,255,255,255),(255,255,255,255),(0,0,0,220)
    lum=.2126*p[:,0]+.7152*p[:,1]+.0722*p[:,2];hi=lum>=np.percentile(lum,70);lo=lum<=np.percentile(lum,24);mid=(bb[1]+bb[3])/2
    top_p=p[hi&(coords[:,0]<mid)];bot_p=p[hi&(coords[:,0]>=mid)]
    top=tuple(int(v) for v in np.median(top_p,axis=0)) if len(top_p) else tuple(int(v) for v in p[np.argmax(lum)])
    bot=tuple(int(v) for v in np.median(bot_p,axis=0)) if len(bot_p) else top
    outline=tuple(int(v) for v in np.median(p[lo],axis=0)) if np.any(lo) else (0,0,0,220)
    return top,bot,outline
def shear(im,slant):
    if not slant:return im
    shift=max(0,int(round(slant*(im.height-1))));o=Image.new('RGBA',(im.width+shift,im.height),(0,0,0,0))
    for y in range(im.height):o.alpha_composite(im.crop((0,y,im.width,y+1)),(int(round(slant*(im.height-1-y))),y))
    return o
def render(key,text,bb,slant):
    x0,y0,x1,y1=bb;sx0=((x0+3)//4)*4;sy0=((y0+3)//4)*4;sx1=(x1//4)*4;sy1=(y1//4)*4
    if sx1-sx0<12 or sy1-sy0<12:raise RuntimeError((key,'no block-safe bbox',bb))
    WW=sx1-sx0;HH=sy1-sy0;top,bot,outline=palette(source_masks[key],bb);dummy=ImageDraw.Draw(Image.new('L',(8,8),0))
    for fs in range(min(300,int(HH*.95)),7,-1):
        f=ImageFont.truetype(FONT,fs);sw=max(1,round(fs*.045));shadow=max(0,round(fs*.018))
        tb=dummy.textbbox((0,0),text,font=f,stroke_width=sw);tw=tb[2]-tb[0];th=tb[3]-tb[1];pad=sw+shadow+4
        fill=Image.new('L',(tw+2*pad,th+2*pad),0);stroke=Image.new('L',fill.size,0)
        ImageDraw.Draw(fill).text((pad-tb[0],pad-tb[1]),text,font=f,fill=255)
        ImageDraw.Draw(stroke).text((pad-tb[0],pad-tb[1]),text,font=f,fill=255,stroke_width=sw,stroke_fill=255)
        sbx=stroke.getbbox();fill=fill.crop(sbx);stroke=stroke.crop(sbx);tile=Image.new('RGBA',stroke.size,(0,0,0,0))
        if shadow:
            sh=Image.new('L',stroke.size,0);sh.paste(stroke,(shadow,shadow));tile.paste((outline[0],outline[1],outline[2],min(210,outline[3])),(0,0),sh)
        tile.paste(outline,(0,0),stroke)
        ar=np.zeros((tile.height,tile.width,4),dtype=np.uint8)
        for yy in range(tile.height):
            t=yy/max(1,tile.height-1)
            for c in range(3):ar[yy,:,c]=round(top[c]*(1-t)+bot[c]*t)
            ar[yy,:,3]=255
        tile.paste(Image.fromarray(ar,'RGBA'),(0,0),fill);tile=shear(tile,slant);ab=tile.getchannel('A').getbbox();tile=tile.crop(ab)
        if tile.width>WW-2 or tile.height>HH-2:continue
        layer=Image.new('RGBA',src.size,(0,0,0,0));px=sx0+(WW-tile.width)//2;py=sy0+(HH-tile.height)//2;layer.alpha_composite(tile,(px,py));lb=layer.getchannel('A').getbbox()
        if lb and lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1:return layer,fs,sw,shadow,lb,{'top':top,'bottom':bot,'outline':outline,'block_safe_bbox':[sx0,sy0,sx1,sy1]}
    raise RuntimeError((key,'cannot_fit',bb,text))

final=clean.copy();layers={};rmeta={}
for key,en,ko,cell,slant in T:
    layer,fs,sw,sh,lb,pal=render(key,ko,bboxes[key],slant);layers[key]=layer;rmeta[key]={'font_size':fs,'stroke_width':sw,'shadow':sh,'localized_bbox':lb,'palette':pal};final.alpha_composite(layer)
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        if ImageChops.multiply(layers[keys[i]].getchannel('A'),layers[keys[j]].getchannel('A')).getbbox():raise RuntimeError(('target_overlap',keys[i],keys[j]))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM);tmp_png=Path('/tmp/C598_final_raw.png');tmp_dds=Path('/tmp/C598_final_nv.dds');raw_final.save(tmp_png)
subprocess.run(['/usr/bin/nvcompress','-bc3','-nomips',str(tmp_png),str(tmp_dds)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
tb=tmp_dds.read_bytes();meta(tb)
allowed_read=np.zeros((H,W),bool)
for bb in bboxes.values():x0,y0,x1,y1=bb;allowed_read[y0:y1,x0:x1]=1
allowed_raw=np.flipud(allowed_read);text_raw=np.flipud(union_text);source_raw=np.flipud(sa)
bw=W//4;bh=H//4;out=bytearray(sb);full_blocks=set();partial_blocks=set()
def aidx(block):
    bits=int.from_bytes(block[2:8],'little');return [(bits>>(3*i))&7 for i in range(16)]
def seta(block,idx):
    bits=sum((int(v)&7)<<(3*i) for i,v in enumerate(idx));return block[:2]+bits.to_bytes(6,'little')+block[8:]
for by in range(bh):
    y=by*4
    if not np.any(allowed_raw[y:y+4]):continue
    for bx in range(bw):
        x=bx*4;am=allowed_raw[y:y+4,x:x+4]
        if not np.any(am):continue
        off=128+(by*bw+bx)*16
        if np.all(am):
            out[off:off+16]=tb[off:off+16];full_blocks.add((bx,by))
        else:
            tm=text_raw[y:y+4,x:x+4]
            if not np.any(tm):continue
            ob=bytes(out[off:off+16]);idx=aidx(ob);srca=source_raw[y:y+4,x:x+4,3]
            zero=[idx[yy*4+xx] for yy in range(4) for xx in range(4) if srca[yy,xx]==0]
            if not zero:raise RuntimeError(('partial_no_zero_alpha',bx,by))
            zi=Counter(zero).most_common(1)[0][0]
            for yy in range(4):
                for xx in range(4):
                    if tm[yy,xx]:idx[yy*4+xx]=zi
            nb=seta(ob,idx)
            if nb[8:]!=ob[8:]:raise RuntimeError('partial color change')
            out[off:off+16]=nb;partial_blocks.add((bx,by))
candidate.write_bytes(out);cand_sha=hashlib.sha256(out).hexdigest()
decoded=Image.open(candidate).convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM);da=np.asarray(decoded,dtype=np.uint8)
all_diff=np.any(sa!=da,axis=2);outside=all_diff&(~allowed_read);alpha_out=(sa[:,:,3]!=da[:,:,3])&(~allowed_read)
if np.any(outside):raise RuntimeError(('strict_outside',int(np.count_nonzero(outside))))
target_alpha=np.zeros((H,W),bool)
for l in layers.values():target_alpha|=(np.asarray(l.getchannel('A'))>0)
residue=union_text&(da[:,:,3]>0)&(~target_alpha)
if np.any(residue):raise RuntimeError(('source_alpha_residue',int(np.count_nonzero(residue))))
rows=[]
for key,en,ko,cell,slant in T:
    ob=bboxes[key];lb=list(rmeta[key]['localized_bbox']);sw0,sh0=ob[2]-ob[0],ob[3]-ob[1];lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    if not(lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3] and lw<=sw0 and lh<=sh0):raise RuntimeError((key,'size_gate',ob,lb))
    rows.append({'key':key,'source':en,'korean':ko,'cell':list(cell),'original_bbox':ob,'localized_bbox':lb,'source_width':sw0,'source_height':sh0,'localized_width':lw,'localized_height':lh,'delta_left':lb[0]-ob[0],'delta_right':ob[2]-lb[2],'delta_top':lb[1]-ob[1],'delta_bottom':ob[3]-lb[3],'containment':'PASS','size_ceiling':'PASS','rework_status':'NEW_EXACT_HD_DXT5_NATIVE_RENDER','native_font_size':rmeta[key]['font_size'],'stroke_width':rmeta[key]['stroke_width'],'shadow':rmeta[key]['shadow'],'palette':rmeta[key]['palette'],'source_mask_meta':mask_meta[key],'historical_localized_raster_reused':False})

def mi(a):return Image.fromarray((a.astype(np.uint8)*255),'L')
allowed_img=mi(allowed_read);source_mask_img=mi(union_text);protected_img=ImageChops.invert(allowed_img);target_img=mi(target_alpha)
source_mask_img.save(outdir/'C598919A_SOURCE_TEXT_MASK.png');allowed_img.save(outdir/'C598919A_ALLOWED_TEXT_REGION_MASK.png');protected_img.save(outdir/'C598919A_PROTECTED_MASK.png');clean.save(outdir/'C598919A_CLEAN_PLATE.png');target_img.save(outdir/'C598919A_TARGET_TEXT_MASK.png')
srcpng=Path('/tmp/C598_source.png');cleanpng=Path('/tmp/C598_clean.png');finalpng=Path('/tmp/C598_final_dec.png');src.save(srcpng);clean.save(cleanpng);decoded.save(finalpng)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(cleanpng),str(outdir/'C598919A_SOURCE_TEXT_MASK.png'),'--report',str(outdir/'B_RECOVERY09_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(finalpng),str(outdir/'C598919A_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(outdir/'C598919A_PROTECTED_MASK.png'),'--report',str(outdir/'B_RECOVERY09_FINAL_MASK_VALIDATION.json')],check=True)

def comp(im,bg):z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
def card(label,im,bg):
    v=comp(im,bg);v.thumbnail((900,900),Image.Resampling.LANCZOS);c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),label,fill='black');return c
cards=[card('SOURCE',src,(64,64,64,255)),card('CLEAN',clean,(64,64,64,255)),card('FINAL',decoded,(64,64,64,255)),card('FINAL_WHITE',decoded,(255,255,255,255))]
ww=cards[0].width+cards[1].width+8;hh=cards[0].height+cards[2].height+8;sheet=Image.new('RGB',(ww,hh),'white');sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(cards[0].width+8,0));sheet.paste(cards[2],(0,cards[0].height+8));sheet.paste(cards[3],(cards[2].width+8,cards[1].height+8));sheet.save(outdir/'B_RECOVERY09_C598_COMPARE.jpg',quality=94)
contacts=[];src_rgb=comp(src,(64,64,64,255));clean_rgb=comp(clean,(64,64,64,255));fin_rgb=comp(decoded,(64,64,64,255))
for n,row in enumerate(rows,1):
    ob=row['original_bbox'];pad=18;cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(W,ob[2]+pad),min(H,ob[3]+pad));ims=[src_rgb.crop(cr),clean_rgb.crop(cr),fin_rgb.crop(cr)]
    scale=min(1.0,650/max(1,ims[0].width))
    if scale<1:
        ns=(round(ims[0].width*scale),round(ims[0].height*scale));ims=[x.resize(ns,Image.Resampling.LANCZOS) for x in ims]
    ch=max(x.height for x in ims)+30;cw=sum(x.width for x in ims)+12;c=Image.new('RGB',(cw,ch),'white');xx=0
    for im in ims:c.paste(im,(xx,30));xx+=im.width+6
    ImageDraw.Draw(c).text((4,4),f'{n} {row["source"]} -> {row["korean"]}',fill='black');contacts.append(c)
cw=max(c.width for c in contacts);ch=sum(c.height for c in contacts)+3*(len(contacts)-1);cs=Image.new('RGB',(cw,ch),'white');yy=0
for c in contacts:cs.paste(c,(0,yy));yy+=c.height+3
cs.save(outdir/'B_RECOVERY09_C598_ROW_CONTACT.jpg',quality=95)
r1=card('SOURCE_RAW',src.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(64,64,64,255));r2=card('FINAL_RAW',decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(64,64,64,255));rs=Image.new('RGB',(r1.width+r2.width+8,max(r1.height,r2.height)),'white');rs.paste(r1,(0,0));rs.paste(r2,(r1.width+8,0));rs.save(outdir/'B_RECOVERY09_C598_RAW_COMPARE.jpg',quality=94)

changed_blocks=0;outside_patch=0;patch=full_blocks|partial_blocks
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        if sb[off:off+16]!=out[off:off+16]:
            changed_blocks+=1
            if (bx,by) not in patch:outside_patch+=1
if outside_patch:raise RuntimeError(('compressed_outside_patch',outside_patch))
report={'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'queue_index':86,'asset':asset,'readiness_tier':'ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION','source_sha256':source_sha_expected,'historical_discovery_sha256':hashlib.sha256(hb).hexdigest(),'historical_discovery_only':True,'candidate_sha256':cand_sha,'candidate_path':str(candidate.relative_to(repo)),'method':'exact 4096x4096 DXT5 source; historical candidate used only for discovery; fresh native Hangul render; full BC3 blocks only inside exact source bboxes; partial edge blocks preserve source color bytes and only clear target source alpha indices; decoded all-channel zero-pixel outside QA','structure':{**info,'header_128_exact':bytes(out[:128])==sb[:128],'raw_orientation':'mirror_y'},'segments_total':41,'physical_cells':37,'segments_rendered':41,'preserved_original':['Ferrari model names','MT/AT abbreviations','rank medals/numbers','icons','bars','OutRun logos','vehicle/model art','non-target ranking artwork'],'clean_plate':{'source_text_residue_pixels':0,'status':'PASS'},'containment':{'elements_total':41,'elements_pass':41,'elements_fail':0,'decoded_all_channel_changed_pixels_outside_exact_source_bboxes':int(np.count_nonzero(outside)),'decoded_alpha_changed_pixels_outside_exact_source_bboxes':int(np.count_nonzero(alpha_out)),'target_overlap_pairs':0,'status':'PASS'},'compressed_patch_gate':{'full_interior_blocks':len(full_blocks),'partial_alpha_only_edge_blocks':len(partial_blocks),'changed_blocks_vs_source':changed_blocks,'changed_blocks_outside_patch_set':outside_patch,'partial_blocks_preserve_source_color_bytes':True,'status':'PASS'},'rows':rows,'manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_RECOVERY09_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(outdir/'B_RECOVERY09_C598_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(outdir/'B_RECOVERY09_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':source_sha_expected,'candidate_sha256':cand_sha,'bbox_and_exact_size_pass':'41/41','decoded_all_channel_outside_exact_bboxes':int(np.count_nonzero(outside)),'decoded_alpha_outside_exact_bboxes':int(np.count_nonzero(alpha_out)),'changed_blocks_outside_patch_set':outside_patch,'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('B_RECOVERY09_DONE',cand_sha,'elements=41/41','full_blocks',len(full_blocks),'partial',len(partial_blocks),'changed_blocks',changed_blocks)
