#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

if os.environ.get('OUTRUN_CPU_WORKER') != 'github-actions' or os.environ.get('OUTRUN_CPU_ROLE') != 'B':
    raise SystemExit('GitHub-hosted localization CPU worker / role B only')
repo=Path.cwd(); run='20261004-B-RECOVERY08'
outdir=repo/'localization/graphics/role_B'/run; outdir.mkdir(parents=True,exist_ok=True)
asset_rel='textures/load/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds'
candidate=repo/'localization/graphics/hd_candidates'/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
work=Path('/tmp/outrun_B_recovery08'); work.mkdir(parents=True,exist_ok=True)
source=work/'CBF8ECBF_HD.dds'
source_url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds'
source_sha_expected='3a2a40256a6c3c945dfd4fab275edba5ec05802e4cff54f2ad93d5196cd992fe'
# readable-orientation cells derived from the persisted exact-HD grid/strip diagnostic.
spec=[
 ('friend_request','FRIEND REQUEST','친구 요청',(630,1015,1350,1100),'plain_white',0.00),
 ('players','PLAYERS','플레이어',(1420,1015,2300,1105),'plain_white',0.00),
 ('your_friends','YOUR FRIENDS','내 친구',(2280,1015,2860,1105),'plain_white',0.00),
 ('please_wait','PLEASE WAIT','잠시만요',(1640,1115,2350,1248),'plain_black',0.00),
 ('time_over','Time Over','시간 종료',(140,1250,1590,1540),'gradient',0.12),
 ('game_over','Game Over','게임 오버',(1830,1250,3370,1545),'gradient',0.12),
 ('goal','GOAL','골',(1360,1500,2860,2020),'gradient',0.10),
]

urllib.request.urlretrieve(source_url,source)
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha256(source)!=source_sha_expected: raise RuntimeError('canonical HD source SHA mismatch')

def resolve_font(style):
    pattern=f'Noto Sans CJK KR:style={style}'
    try: fp=subprocess.check_output(['fc-match','-f','%{file}',pattern],text=True).strip()
    except Exception: fp=''
    if not fp or not Path(fp).exists() or 'NotoSansCJK' not in Path(fp).name:
        subprocess.run(['sudo','apt-get','update','-qq'],check=True)
        subprocess.run(['sudo','apt-get','install','-y','-qq','fonts-noto-cjk'],check=True)
        fp=subprocess.check_output(['fc-match','-f','%{file}',pattern],text=True).strip()
    if not fp or not Path(fp).exists(): raise RuntimeError('Noto CJK font unavailable')
    return fp
FONT_BLACK=resolve_font('Black'); FONT_BOLD=resolve_font('Bold')

def load_dds(p):
    b=Path(p).read_bytes(); assert b[:4]==b'DDS '
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]; pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
    pf=struct.unpack_from('<I',b,80)[0]; fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]; masks=struct.unpack_from('<IIII',b,92)
    if not(fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and pitch==w*4 and mips==1 and len(b)==128+w*h*4):
        raise RuntimeError((h,w,pitch,mips,fourcc,bpp,masks,len(b)))
    raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA'); readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],readable,{'width':w,'height':h,'pitch':pitch,'mips':mips,'pf_flags':pf,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks]}
def write_dds(srcp,readable,outp):
    b=Path(srcp).read_bytes(); raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM); payload=b[:128]+raw.tobytes('raw','RGBA'); Path(outp).write_bytes(payload); return hashlib.sha256(payload).hexdigest()
def count(mask): return int(np.count_nonzero(np.asarray(mask,dtype=np.uint8)))
def bin_alpha(im): return im.getchannel('A').point(lambda v:255 if v else 0)
def rect_mask(size,boxes):
    m=Image.new('L',size,0); d=ImageDraw.Draw(m)
    for b in boxes:d.rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=255)
    return m

def components(mask,min_pixels=4):
    h,w=mask.shape; seen=np.zeros((h,w),bool); keep=np.zeros((h,w),bool); meta=[]
    for y in range(h):
        for x in range(w):
            if not mask[y,x] or seen[y,x]:continue
            st=[(x,y)];seen[y,x]=1;pts=[]
            while st:
                xx,yy=st.pop();pts.append((xx,yy))
                for nx,ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
                    if 0<=nx<w and 0<=ny<h and mask[ny,nx] and not seen[ny,nx]: seen[ny,nx]=1;st.append((nx,ny))
            if len(pts)<min_pixels:continue
            xs=[p[0] for p in pts];ys=[p[1] for p in pts]; touch=min(xs)==0 or max(xs)==w-1 or min(ys)==0 or max(ys)==h-1
            meta.append({'pixels':len(pts),'bbox':[min(xs),min(ys),max(xs)+1,max(ys)+1],'edge_touch':touch})
            if not touch:
                for xx,yy in pts:keep[yy,xx]=1
    return keep,meta

def source_mask_for(key,cell):
    x0,y0,x1,y1=cell; crop=np.asarray(src.crop(cell),dtype=np.uint8)
    border=np.concatenate([crop[:8].reshape(-1,4),crop[-8:].reshape(-1,4),crop[:,:8].reshape(-1,4),crop[:,-8:].reshape(-1,4)],axis=0)
    tf=float(np.mean(border[:,3]<=1))
    if tf<0.78: raise RuntimeError(f'{key} cell not predominantly transparent: {tf}')
    keep,cm=components(crop[:,:,3]>1)
    if any(x['edge_touch'] and x['pixels']>50 for x in cm):
        raise RuntimeError(f'{key} cell clips source component: {cm}')
    full=Image.new('L',src.size,0); full.paste(Image.fromarray((keep*255).astype(np.uint8),'L'),(x0,y0)); bb=full.getbbox()
    if not bb: raise RuntimeError(f'{key} empty source mask')
    margins=(bb[0]-x0,bb[1]-y0,x1-bb[2],y1-bb[3])
    if min(margins)<=0: raise RuntimeError(f'{key} no safe cell margin bbox={bb} cell={cell} margins={margins}')
    return full,bb,{'border_transparent_fraction':tf,'components':cm,'cell':list(cell)}

def source_palette(mask,bb):
    a=np.asarray(src,dtype=np.uint8); m=np.asarray(mask)>0; p=a[m]; coords=np.argwhere(m)
    p=p[p[:,3]>8]
    if len(p)<10:return (255,255,255,255),(255,255,255,255),(0,0,0,255)
    allp=a[m]; lum=.2126*allp[:,0]+.7152*allp[:,1]+.0722*allp[:,2]; hi=lum>=np.percentile(lum,72); lo=lum<=np.percentile(lum,20); mid=(bb[1]+bb[3])/2
    top_sel=allp[hi & (coords[:,0]<mid)]; bot_sel=allp[hi & (coords[:,0]>=mid)]
    top=tuple(int(v) for v in np.median(top_sel,axis=0)) if len(top_sel) else (255,255,255,255)
    bottom=tuple(int(v) for v in np.median(bot_sel,axis=0)) if len(bot_sel) else top
    outline=tuple(int(v) for v in np.median(allp[lo],axis=0)) if np.any(lo) else (0,0,0,255)
    return top,bottom,outline

def shear(im,slant):
    if not slant:return im
    shift=max(0,int(round(abs(slant)*(im.height-1)))); out=Image.new('RGBA',(im.width+shift,im.height),(0,0,0,0))
    for y in range(im.height):
        dx=int(round(slant*(im.height-1-y))); dx=max(0,dx)
        out.alpha_composite(im.crop((0,y,im.width,y+1)),(dx,y))
    return out

def render_target(key,text,bb,style,slant):
    x0,y0,x1,y1=bb; W=x1-x0; H=y1-y0; dummy=ImageDraw.Draw(Image.new('L',(8,8),0)); top,bottom,outline=source_palette(source_masks[key],bb)
    if style in ('plain_white','plain_black'):
        srcp=np.asarray(src,dtype=np.uint8)[np.asarray(source_masks[key])>0]
        rgb=srcp[srcp[:,3]>16,:3]; fill=tuple(int(v) for v in np.median(rgb,axis=0))+(255,) if len(rgb) else ((255,255,255,255) if style=='plain_white' else (0,0,0,255))
        # Force intended luminance class while retaining source tint.
        if style=='plain_white' and sum(fill[:3])<450: fill=(245,245,245,255)
        if style=='plain_black' and sum(fill[:3])>180: fill=(8,8,8,255)
        for fs in range(min(180,int(H*.96)),7,-1):
            font=ImageFont.truetype(FONT_BLACK,fs); tb=dummy.textbbox((0,0),text,font=font); tw=tb[2]-tb[0]; th=tb[3]-tb[1]
            if tw>W-2 or th>H-2:continue
            g=Image.new('RGBA',(tw+4,th+4),(0,0,0,0)); ImageDraw.Draw(g).text((2-tb[0],2-tb[1]),text,font=font,fill=fill); gb=g.getchannel('A').getbbox();g=g.crop(gb)
            layer=Image.new('RGBA',src.size,(0,0,0,0)); px=x0+(W-g.width)//2; py=y0+(H-g.height)//2; layer.alpha_composite(g,(px,py)); lb=layer.getchannel('A').getbbox()
            if lb and lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1:return layer,fs,0,lb,{'top':fill,'bottom':fill,'outline':fill}
        raise RuntimeError(f'cannot fit {key}')
    for fs in range(min(360,int(H*.94)),11,-1):
        font=ImageFont.truetype(FONT_BLACK,fs); sw=max(3,round(fs*.055)); shadow=max(2,round(fs*.03)); tb=dummy.textbbox((0,0),text,font=font,stroke_width=sw); tw=tb[2]-tb[0]; th=tb[3]-tb[1]; pad=sw+shadow+6
        fillm=Image.new('L',(tw+2*pad,th+2*pad),0); stroke=Image.new('L',fillm.size,0)
        ImageDraw.Draw(fillm).text((pad-tb[0],pad-tb[1]),text,font=font,fill=255)
        ImageDraw.Draw(stroke).text((pad-tb[0],pad-tb[1]),text,font=font,fill=255,stroke_width=sw,stroke_fill=255)
        sb=stroke.getbbox();fillm=fillm.crop(sb);stroke=stroke.crop(sb);tile=Image.new('RGBA',stroke.size,(0,0,0,0))
        sh=Image.new('L',stroke.size,0);sh.paste(stroke,(shadow,shadow)); tile.paste((outline[0],outline[1],outline[2],min(220,max(120,outline[3]))),(0,0),sh);tile.paste(outline,(0,0),stroke)
        arr=np.zeros((tile.height,tile.width,4),dtype=np.uint8)
        for yy in range(tile.height):
            t=yy/max(1,tile.height-1)
            arr[yy,:,0]=round(top[0]*(1-t)+bottom[0]*t);arr[yy,:,1]=round(top[1]*(1-t)+bottom[1]*t);arr[yy,:,2]=round(top[2]*(1-t)+bottom[2]*t);arr[yy,:,3]=255
        tile.paste(Image.fromarray(arr,'RGBA'),(0,0),fillm);tile=shear(tile,slant);gb=tile.getchannel('A').getbbox();tile=tile.crop(gb)
        if tile.width>W-2 or tile.height>H-2:continue
        layer=Image.new('RGBA',src.size,(0,0,0,0)); px=x0+(W-tile.width)//2; py=y0+(H-tile.height)//2;layer.alpha_composite(tile,(px,py));lb=layer.getchannel('A').getbbox()
        if lb and lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1:return layer,fs,sw,lb,{'top':top,'bottom':bottom,'outline':outline}
    raise RuntimeError(f'cannot fit gradient {key}')

header,src,info=load_dds(source)
source_masks={};source_bboxes={};mask_meta={};source_text=Image.new('L',src.size,0)
for key,en,ko,cell,style,slant in spec:
    m,bb,meta=source_mask_for(key,cell);source_masks[key]=m;source_bboxes[key]=bb;mask_meta[key]=meta;source_text=ImageChops.lighter(source_text,m)
allowed=rect_mask(src.size,list(source_bboxes.values()));protected=ImageChops.invert(allowed)
clean=src.copy();a=np.asarray(clean).copy();m=np.asarray(source_text)>0;a[m]=(0,0,0,0);clean=Image.fromarray(a,'RGBA')
final=clean.copy();layers={};render_meta={}
for key,en,ko,cell,style,slant in spec:
    layer,fs,sw,lb,pal=render_target(key,ko,source_bboxes[key],style,slant);layers[key]=layer;final.alpha_composite(layer);render_meta[key]={'font_size':fs,'stroke_width':sw,'localized_bbox':lb,'palette':pal}
# no target overlap
keys=list(layers);overlap=[]
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        n=count(ImageChops.multiply(bin_alpha(layers[keys[i]]),bin_alpha(layers[keys[j]])))
        if n:overlap.append([keys[i],keys[j],n])
if overlap:raise RuntimeError(('target overlap',overlap))
rows=[]
for key,en,ko,cell,style,slant in spec:
    ob=source_bboxes[key];lb=render_meta[key]['localized_bbox'];ok=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
    if not ok:raise RuntimeError((key,ob,lb))
    rows.append({'key':key,'source':en,'korean':ko,'cell':list(cell),'original_bbox':list(ob),'localized_bbox':list(lb),'delta_left':lb[0]-ob[0],'delta_right':ob[2]-lb[2],'delta_top':lb[1]-ob[1],'delta_bottom':ob[3]-lb[3],'containment':'PASS','rework_status':'NEW_CANDIDATE','style':style,'native_font_size':render_meta[key]['font_size'],'stroke_width':render_meta[key]['stroke_width'],'palette':render_meta[key]['palette'],'source_mask_meta':mask_meta[key]})
# DDS exact roundtrip
candidate_sha=write_dds(source,final,candidate);chead,decoded,cinfo=load_dds(candidate)
if chead!=header or cinfo!=info or ImageChops.difference(final,decoded).getbbox() is not None:raise RuntimeError('DDS roundtrip/header mismatch')
# gates
cd=ImageChops.difference(src,clean);bands=cd.split();cm=bands[0]
for z in bands[1:]:cm=ImageChops.lighter(cm,z)
cm=cm.point(lambda v:255 if v else 0);clean_out=count(ImageChops.multiply(cm,ImageChops.invert(source_text)))
diff=ImageChops.difference(src,decoded);bands=diff.split();dm=bands[0]
for z in bands[1:]:dm=ImageChops.lighter(dm,z)
dm=dm.point(lambda v:255 if v else 0);outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)));protected_changes=count(ImageChops.multiply(dm,protected));ad=ImageChops.difference(src.getchannel('A'),decoded.getchannel('A')).point(lambda v:255 if v else 0);alpha_out=count(ImageChops.multiply(ad,ImageChops.invert(allowed)))
residue=count(ImageChops.multiply(bin_alpha(clean),source_text))
if any((clean_out,outside,protected_changes,alpha_out,residue)):raise RuntimeError(('static gate',clean_out,outside,protected_changes,alpha_out,residue))
# evidence
source_text.save(outdir/'CBF8ECBF_SOURCE_TEXT_MASK.png');allowed.save(outdir/'CBF8ECBF_ALLOWED_TEXT_REGION_MASK.png');protected.save(outdir/'CBF8ECBF_PROTECTED_MASK.png');clean.save(outdir/'CBF8ECBF_CLEAN_PLATE.png')
target=Image.new('L',src.size,0)
for layer in layers.values():target=ImageChops.lighter(target,bin_alpha(layer))
target.save(outdir/'CBF8ECBF_TARGET_TEXT_MASK.png')
srcpng=work/'source.png';cleanpng=work/'clean.png';finalpng=work/'final.png';src.save(srcpng);clean.save(cleanpng);decoded.save(finalpng)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(cleanpng),str(outdir/'CBF8ECBF_SOURCE_TEXT_MASK.png'),'--report',str(outdir/'B_RECOVERY08_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(finalpng),str(outdir/'CBF8ECBF_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(outdir/'CBF8ECBF_PROTECTED_MASK.png'),'--report',str(outdir/'B_RECOVERY08_FINAL_MASK_VALIDATION.json')],check=True)
# visual sheets
def comp(im,bg):z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
def card(label,im,bg):
    v=comp(im,bg);v.thumbnail((1000,500));c=Image.new('RGB',(v.width,v.height+32),'white');c.paste(v,(0,32));ImageDraw.Draw(c).text((5,5),label,fill='black');return c
cards=[card('SOURCE',src,(72,72,72,255)),card('CLEAN',clean,(72,72,72,255)),card('FINAL',decoded,(72,72,72,255)),card('FINAL_WHITE',decoded,(255,255,255,255))]
W=cards[0].width+cards[1].width+8;H=cards[0].height+cards[2].height+8;sheet=Image.new('RGB',(W,H),'white');sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(cards[0].width+8,0));sheet.paste(cards[2],(0,cards[0].height+8));sheet.paste(cards[3],(cards[2].width+8,cards[1].height+8));sheet.save(outdir/'B_RECOVERY08_CBF8ECBF_COMPARE.jpg',quality=94)
contacts=[]
for n,row in enumerate(rows,1):
    ob=row['original_bbox'];pad=28;cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(src.width,ob[2]+pad),min(src.height,ob[3]+pad));a=comp(src,(72,72,72,255)).crop(cr);b=comp(clean,(72,72,72,255)).crop(cr);c=comp(decoded,(72,72,72,255)).crop(cr);h=max(a.height,b.height,c.height)+30;cardi=Image.new('RGB',(a.width+b.width+c.width+12,h),'white');cardi.paste(a,(0,30));cardi.paste(b,(a.width+6,30));cardi.paste(c,(a.width+b.width+12,30));ImageDraw.Draw(cardi).text((4,4),f'{n}. {row["source"]} -> {row["korean"]}',fill='black');contacts.append(cardi)
CW=max(c.width for c in contacts);CH=sum(c.height for c in contacts)+6*(len(contacts)-1);cs=Image.new('RGB',(CW,CH),'white');yy=0
for c in contacts:cs.paste(c,(0,yy));yy+=c.height+6
cs.save(outdir/'B_RECOVERY08_CBF8ECBF_ROW_CONTACT.jpg',quality=95)
raws=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM);rawf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM);p1=card('SOURCE_RAW',raws,(72,72,72,255));p2=card('FINAL_RAW',rawf,(72,72,72,255));rs=Image.new('RGB',(p1.width+p2.width+8,max(p1.height,p2.height)),'white');rs.paste(p1,(0,0));rs.paste(p2,(p1.width+8,0));rs.save(outdir/'B_RECOVERY08_CBF8ECBF_RAW_COMPARE.jpg',quality=94)
report={'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'queue_index':50,'asset':asset_rel,'readiness_tier':'ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION','source_upstream_repo':'Sonic-TV/OR2006Sprites','source_upstream_commit':'a95efe01d1f136514cef94b0d9e9fd61df021754','source_url':source_url,'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'candidate_path':str(candidate.relative_to(repo)),'method':'pinned exact HD RGBA32 -> transparent source-glyph masks -> clean plate -> native Korean lettering -> exact-header DDS -> decoded final QA','structure':{**info,'header_128_exact':True,'raw_orientation':'mirror_y'},'segments_total':7,'segments_rendered':7,'clean_plate':{'changed_pixels_outside_source_text_mask':clean_out,'source_text_residue_pixels':residue,'status':'PASS'},'containment':{'elements_total':7,'elements_pass':7,'elements_fail':0,'changed_pixels_outside_permitted_source_bboxes':outside,'alpha_changed_outside_permitted_source_bboxes':alpha_out,'protected_changes':protected_changes,'target_overlap_pairs':overlap,'status':'PASS'},'rows':rows,'manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_RECOVERY08_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(outdir/'B_RECOVERY08_CBF8ECBF_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(outdir/'B_RECOVERY08_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'bbox_pass':'7/7','clean_plate_outside_mask':clean_out,'source_text_residue_pixels':residue,'outside_permitted_bboxes':outside,'alpha_outside_permitted_bboxes':alpha_out,'protected_changes':protected_changes,'target_overlap_pairs':0,'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'},indent=2)+'\n')
print('B_RECOVERY08_DONE',candidate_sha,'bbox=7/7','outside=',outside,'protected=',protected_changes,'residue=',residue)
