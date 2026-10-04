#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':
    raise SystemExit('GitHub-hosted localization CPU worker / role B only')
repo=Path.cwd(); run='20261004-B-RECOVERY07'; outdir=repo/'localization/graphics/role_B'/run; outdir.mkdir(parents=True,exist_ok=True)
asset_rel='textures/load/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds'; candidate=repo/'localization/graphics/hd_candidates'/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
work=Path('/tmp/outrun_B_recovery07'); work.mkdir(parents=True,exist_ok=True); source=work/'B1696633_HD.dds'
source_url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds'
source_sha_expected='3c58bf9587d0454e5bb8733bd35c5b2613b11c7fd52c49a428f0fa5fb4cea12d'
# Human source review from the hosted discovery contact sheet; coordinates are source 512x512 logical cells and scale exactly x4 in the 2048 HD atlas.
spec=[
 ('name','NAME','이름',(12,177,82,191),0.0),
 ('status','STATUS','상태',(402,177,478,191),0.0),
 ('stage','Stage','스테이지',(268,188,330,212),0.10),
 ('next_stage','Next Stage','다음 스테이지',(326,207,414,236),0.10),
 ('ghost','Ghost','고스트',(414,207,478,236),0.10),
 ('total_time','Total Time','총 시간',(0,374,195,414),0.10),
 ('slipstream','Slipstream','슬립스트림',(226,374,350,414),0.08),
 ('new_record','NEW Record!!','신기록!!',(405,369,484,416),0.08),
 ('extend_time','Extend Time','시간 연장',(195,414,445,474),0.11),
]
urllib.request.urlretrieve(source_url,source)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=source_sha_expected: raise RuntimeError('source SHA mismatch')

def font(style):
    pat=f'Noto Sans CJK KR:style={style}'
    try: fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
    except Exception: fp=''
    if not fp or not Path(fp).exists() or 'NotoSansCJK' not in Path(fp).name:
        subprocess.run(['sudo','apt-get','update','-qq'],check=True);subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk'],check=True)
        fp=subprocess.check_output(['fc-match','-f','%{file}',pat],text=True).strip()
    if not fp or not Path(fp).exists(): raise RuntimeError('Noto CJK unavailable')
    return fp
FONT_BLACK=font('Black');FONT_BOLD=font('Bold')

def load(p):
    b=Path(p).read_bytes(); assert b[:4]==b'DDS '
    h=struct.unpack_from('<I',b,12)[0];w=struct.unpack_from('<I',b,16)[0];pitch=struct.unpack_from('<I',b,20)[0];mips=struct.unpack_from('<I',b,28)[0];pf=struct.unpack_from('<I',b,80)[0];fourcc=b[84:88];bpp=struct.unpack_from('<I',b,88)[0];masks=struct.unpack_from('<IIII',b,92)
    if not(fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and pitch==w*4 and mips==1 and len(b)==128+w*h*4):raise RuntimeError((h,w,pitch,mips,fourcc,bpp,masks,len(b)))
    raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA');return b[:128],raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{'width':w,'height':h,'pitch':pitch,'mips':mips,'pf_flags':pf,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks]}
def write(srcp,readable,out):
    b=Path(srcp).read_bytes(); raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=b[:128]+raw.tobytes('raw','RGBA');Path(out).write_bytes(payload);return hashlib.sha256(payload).hexdigest()
def count(m):return int(np.count_nonzero(np.asarray(m,dtype=np.uint8)))
def bin_alpha(im):return im.getchannel('A').point(lambda v:255 if v else 0)
def rectmask(size,boxes):
    m=Image.new('L',size,0);d=ImageDraw.Draw(m)
    for b in boxes:d.rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=255)
    return m
header,src,info=load(source)
if (src.width,src.height)!=(2048,2048):raise RuntimeError(info)
scale=4

def mode_rgba(pix):
    # Quantized mode suppresses tiny antialias variation.
    q=[tuple((int(c)//8)*8 for c in p) for p in pix]
    return Counter(q).most_common(1)[0][0]
def text_mask_for_cell(cell):
    crop=np.asarray(src.crop(cell),dtype=np.int16); h,w,_=crop.shape; bw=max(3,min(12,min(h,w)//12))
    border=np.concatenate([crop[:bw].reshape(-1,4),crop[-bw:].reshape(-1,4),crop[:, :bw].reshape(-1,4),crop[:, -bw:].reshape(-1,4)],axis=0)
    transparent=float(np.mean(border[:,3]<8))
    if transparent>=0.60:
        mask=(crop[:,:,3]>2); bg=(0,0,0,0); bg_type='transparent'; variance=0.0
    else:
        allpix=crop.reshape(-1,4); bg=mode_rgba(allpix.tolist()); bgv=np.array(bg,dtype=np.int16)
        quant=np.array([[(int(c)//8)*8 for c in px] for px in allpix],dtype=np.int16); coverage=float(np.mean(np.all(quant==bgv,axis=1)))
        dist=np.max(np.abs(crop-bgv),axis=2); mask=(dist>10)&(crop[:,:,3]>8); bg_type='flat_or_near_flat'; variance=float(np.percentile(np.max(np.abs(border-bgv),axis=1),90))
        if coverage<0.30: raise RuntimeError(f'background lacks dominant flat color cell={cell} coverage={coverage} variance={variance}')
    # Remove isolated one-pixel noise while retaining punctuation/dots by keeping components >=2 px in HD.
    im=Image.fromarray((mask*255).astype(np.uint8),'L'); a=np.asarray(im)>0; seen=np.zeros(a.shape,bool); keep=np.zeros(a.shape,bool)
    H,W=a.shape
    for yy in range(H):
        for xx in range(W):
            if not a[yy,xx] or seen[yy,xx]:continue
            q=[(xx,yy)];seen[yy,xx]=1;pts=[]
            while q:
                x,y=q.pop();pts.append((x,y))
                for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if 0<=nx<W and 0<=ny<H and a[ny,nx] and not seen[ny,nx]:seen[ny,nx]=1;q.append((nx,ny))
            if len(pts)>=2:
                for x,y in pts:keep[y,x]=1
    full=Image.new('L',src.size,0);full.paste(Image.fromarray((keep*255).astype(np.uint8),'L'),(cell[0],cell[1]));bb=full.getbbox()
    if not bb:raise RuntimeError(f'empty text mask {cell}')
    # Fail if measured text touches the manual cell boundary; coordinates must isolate the element with margin.
    margins=(bb[0]-cell[0],bb[1]-cell[1],cell[2]-bb[2],cell[3]-bb[3])
    if min(margins)<=0:raise RuntimeError(f'cell clips source text cell={cell} bbox={bb} margins={margins}')
    return full,bb,bg,bg_type,variance

rows=[];masks={};bboxes={};bg_meta={}; source_text_mask=Image.new('L',src.size,0)
for key,english,korean,lc,slant in spec:
    cell=tuple(v*scale for v in lc);m,bb,bg,bgt,var=text_mask_for_cell(cell);masks[key]=m;bboxes[key]=bb;source_text_mask=ImageChops.lighter(source_text_mask,m);bg_meta[key]=(bg,bgt,var,cell)
    rows.append({'key':key,'source':english,'korean':korean,'logical_cell':list(lc),'hd_cell':list(cell),'original_bbox':list(bb),'clean_background_rgba':list(bg),'background_type':bgt,'background_variance_p90':var,'slant':slant})
allowed=rectmask(src.size,list(bboxes.values()));protected=ImageChops.invert(allowed)
# Build clean plate per element: exact transparent restore for transparent cells; local flat background reconstruction for opaque header strips.
arr=np.asarray(src).copy()
for key,english,korean,lc,slant in spec:
    mk=np.asarray(masks[key])>0;bg,bgt,var,cell=bg_meta[key]
    if bgt=='transparent':arr[mk]=np.array((0,0,0,0),dtype=np.uint8)
    else:arr[mk]=np.array(bg,dtype=np.uint8)
clean=Image.fromarray(arr,'RGBA')

def palette(key):
    mk=np.asarray(masks[key])>0; p=np.asarray(src)[mk];
    common=Counter(tuple(int(x) for x in q[:3]) for q in p if q[3]>=96).most_common(32)
    if not common:return (255,255,255,255),(0,8,57,255),0
    cols=[c for c,n in common]; lum=lambda c:.2126*c[0]+.7152*c[1]+.0722*c[2]; hi=max(cols,key=lum);lo=min(cols,key=lum); spread=lum(hi)-lum(lo)
    stroke=0 if spread<28 else None
    return (*hi,255),(*lo,255),stroke

def shear(g,s):
    if not s:return g
    shift=max(0,int(round(s*(g.height-1))));o=Image.new('RGBA',(g.width+shift,g.height),(0,0,0,0))
    for y in range(g.height):o.alpha_composite(g.crop((0,y,g.width,y+1)),(int(round(s*(g.height-1-y))),y))
    return o
def render_fit(text,bb,fill,outline,stroke_override,slant):
    x0,y0,x1,y1=bb;W=x1-x0;H=y1-y0;dummy=ImageDraw.Draw(Image.new('L',(8,8)))
    for fs in range(min(220,max(12,int(H*.92))),8,-1):
        sw=stroke_override if stroke_override is not None else max(1,round(fs*.065)); f=ImageFont.truetype(FONT_BLACK,fs);tb=dummy.textbbox((0,0),text,font=f,stroke_width=sw);tw=tb[2]-tb[0];th=tb[3]-tb[1];pad=sw+4
        g=Image.new('RGBA',(tw+2*pad,th+2*pad),(0,0,0,0));d=ImageDraw.Draw(g);d.text((pad-tb[0],pad-tb[1]),text,font=f,fill=fill,stroke_width=sw,stroke_fill=outline)
        gb=g.getchannel('A').getbbox();g=shear(g.crop(gb),slant)
        if g.width<=W-2 and g.height<=H-2:
            layer=Image.new('RGBA',src.size,(0,0,0,0));px=x0+(W-g.width)//2;py=y0+(H-g.height)//2;layer.alpha_composite(g,(px,py));lb=layer.getchannel('A').getbbox()
            if lb and lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1:return layer,fs,sw,lb
    raise RuntimeError(('cannot fit',text,bb))
final=clean.copy();layers={}
for row,(key,english,korean,lc,slant) in zip(rows,spec):
    fill,outline,stroke_override=palette(key);layer,fs,sw,lb=render_fit(korean,bboxes[key],fill,outline,stroke_override,slant);layers[key]=layer;final.alpha_composite(layer);row.update({'sampled_fill_rgba':list(fill),'sampled_outline_rgba':list(outline),'native_font_size':fs,'stroke_width':sw,'localized_bbox':list(lb),'delta_left':lb[0]-bboxes[key][0],'delta_right':bboxes[key][2]-lb[2],'delta_top':lb[1]-bboxes[key][1],'delta_bottom':bboxes[key][3]-lb[3],'containment':'PASS','rework_status':'NEW_CANDIDATE','historical_localized_raster_reused':False})
sha_candidate=write(source,final,candidate);chead,decoded,cinfo=load(candidate)
if chead!=header or cinfo!=info or ImageChops.difference(final,decoded).getbbox() is not None:raise RuntimeError('DDS roundtrip/header mismatch')
target=Image.new('L',src.size,0)
for l in layers.values():target=ImageChops.lighter(target,bin_alpha(l))
d=ImageChops.difference(src,decoded);bands=d.split();dm=bands[0]
for z in bands[1:]:dm=ImageChops.lighter(dm,z)
dm=dm.point(lambda v:255 if v else 0);outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)));protected_changes=count(ImageChops.multiply(dm,protected));ad=ImageChops.difference(src.getchannel('A'),decoded.getchannel('A')).point(lambda v:255 if v else 0);alpha_out=count(ImageChops.multiply(ad,ImageChops.invert(allowed)))
cd=ImageChops.difference(src,clean);bands=cd.split();cm=bands[0]
for z in bands[1:]:cm=ImageChops.lighter(cm,z)
cm=cm.point(lambda v:255 if v else 0);clean_out=count(ImageChops.multiply(cm,ImageChops.invert(source_text_mask)))
# Residue check only for transparent-cell masks; opaque cells reconstruct to nonzero background by design.
transparent_union=Image.new('L',src.size,0)
for key,*_ in spec:
    if bg_meta[key][1]=='transparent':transparent_union=ImageChops.lighter(transparent_union,masks[key])
residue=count(ImageChops.multiply(bin_alpha(clean),transparent_union))
if any((outside,protected_changes,alpha_out,clean_out,residue)):raise RuntimeError(('static',outside,protected_changes,alpha_out,clean_out,residue))
overlap=[];ks=list(layers)
for i in range(len(ks)):
    for j in range(i+1,len(ks)):
        n=count(ImageChops.multiply(bin_alpha(layers[ks[i]]),bin_alpha(layers[ks[j]])))
        if n:overlap.append([ks[i],ks[j],n])
if overlap:raise RuntimeError(('overlap',overlap))
source_text_mask.save(outdir/'B1696633_SOURCE_TEXT_MASK.png');allowed.save(outdir/'B1696633_ALLOWED_TEXT_REGION_MASK.png');protected.save(outdir/'B1696633_PROTECTED_MASK.png');clean.save(outdir/'B1696633_CLEAN_PLATE.png');target.save(outdir/'B1696633_TARGET_TEXT_MASK.png')
srcpng=work/'source.png';cleanpng=work/'clean.png';finalpng=work/'final.png';src.save(srcpng);clean.save(cleanpng);decoded.save(finalpng)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(cleanpng),str(outdir/'B1696633_SOURCE_TEXT_MASK.png'),'--report',str(outdir/'B_RECOVERY07_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(finalpng),str(outdir/'B1696633_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(outdir/'B1696633_PROTECTED_MASK.png'),'--report',str(outdir/'B_RECOVERY07_FINAL_MASK_VALIDATION.json')],check=True)
# Human QA evidence.
lab=ImageFont.truetype(FONT_BOLD,23)
def comp(im,bg):q=Image.new('RGBA',im.size,bg);q.alpha_composite(im);return q.convert('RGB')
def panel(title,im,bg):v=comp(im,bg);v.thumbnail((850,850));c=Image.new('RGB',(v.width,v.height+38),'white');c.paste(v,(0,38));ImageDraw.Draw(c).text((6,4),title,font=lab,fill='black');return c
cards=[panel('SOURCE',src,(72,72,72,255)),panel('CLEAN',clean,(72,72,72,255)),panel('FINAL',decoded,(72,72,72,255)),panel('FINAL_WHITE',decoded,(255,255,255,255))];W=cards[0].width+cards[1].width+10;H=cards[0].height+cards[2].height+10;sheet=Image.new('RGB',(W,H),'white');sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(cards[0].width+10,0));sheet.paste(cards[2],(0,cards[0].height+10));sheet.paste(cards[3],(cards[2].width+10,cards[1].height+10));sheet.save(outdir/'B_RECOVERY07_B1696633_COMPARE.jpg',quality=94)
contacts=[]
for n,row in enumerate(rows,1):
    ob=row['original_bbox'];pad=24;cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(src.width,ob[2]+pad),min(src.height,ob[3]+pad));s=comp(src,(72,72,72,255)).crop(cr);f=comp(decoded,(72,72,72,255)).crop(cr);h=max(s.height,f.height)+36;c=Image.new('RGB',(s.width+f.width+8,h),'white');c.paste(s,(0,36));c.paste(f,(s.width+8,36));ImageDraw.Draw(c).text((4,3),f'{n}. {row["source"]} -> {row["korean"]}',font=lab,fill='black');contacts.append(c)
CW=max(c.width for c in contacts);CH=sum(c.height for c in contacts)+6*(len(contacts)-1);cs=Image.new('RGB',(CW,CH),'white');yy=0
for c in contacts:cs.paste(c,(0,yy));yy+=c.height+6
cs.save(outdir/'B_RECOVERY07_B1696633_ROW_CONTACT.jpg',quality=95)
raws=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM);rawf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM);p1=panel('SOURCE_RAW',raws,(72,72,72,255));p2=panel('FINAL_RAW',rawf,(72,72,72,255));rs=Image.new('RGB',(p1.width+p2.width+8,max(p1.height,p2.height)),'white');rs.paste(p1,(0,0));rs.paste(p2,(p1.width+8,0));rs.save(outdir/'B_RECOVERY07_B1696633_RAW_COMPARE.jpg',quality=92)
report={'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'queue_index':48,'asset':asset_rel,'readiness_tier':'ONE_STAGE_TO_RENDER','source_upstream_repo':'Sonic-TV/OR2006Sprites','source_upstream_commit':'a95efe01d1f136514cef94b0d9e9fd61df021754','source_sha256':source_sha_expected,'candidate_sha256':sha_candidate,'candidate_path':str(candidate.relative_to(repo)),'method':'exact pinned HD source + human-reviewed source-label cells -> adaptive transparent/flat-background source-text masks -> protected mask -> clean plate -> nine fresh native-resolution Korean labels -> exact RGBA32 source-header DDS -> decoded final QA','historical_full_draft_note':'used only for hosted visual discovery; no historical localized raster pixels reused or upscaled','structure':{**info,'header_128_exact':True,'raw_orientation':'mirror_y','channel_layout':'RGBA masks preserved'},'segments_total':9,'segments_rendered':9,'clean_plate':{'changed_pixels_outside_source_text_mask':clean_out,'transparent_source_text_residue_pixels':residue,'status':'PASS'},'containment':{'elements_total':9,'elements_pass':9,'elements_fail':0,'changed_pixels_outside_permitted_source_bboxes':outside,'alpha_changed_outside_permitted_source_bboxes':alpha_out,'protected_changes':protected_changes,'target_overlap_pairs':overlap,'status':'PASS'},'rows':rows,'manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_RECOVERY07_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(outdir/'B_RECOVERY07_B1696633_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(outdir/'B_RECOVERY07_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':source_sha_expected,'candidate_sha256':sha_candidate,'bbox_pass':'9/9','clean_plate_outside_mask':clean_out,'transparent_residue_pixels':residue,'outside_permitted_bboxes':outside,'alpha_outside_permitted_bboxes':alpha_out,'protected_changes':protected_changes,'target_overlap_pairs':0,'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('B_RECOVERY07_DONE',sha_candidate,'9/9',[(r['key'],r['original_bbox'],r['localized_bbox'],r['background_type']) for r in rows])
