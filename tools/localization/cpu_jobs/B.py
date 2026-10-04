#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

if os.environ.get('OUTRUN_CPU_WORKER') != 'github-actions' or os.environ.get('OUTRUN_CPU_ROLE') != 'B':
    raise SystemExit('GitHub-hosted localization CPU worker / role B only')

repo=Path.cwd(); run='20261004-B-RECOVERY07'
outdir=repo/'localization/graphics/role_B'/run; outdir.mkdir(parents=True,exist_ok=True)
asset_rel='textures/load/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds'
candidate=repo/'localization/graphics/hd_candidates'/asset_rel; candidate.parent.mkdir(parents=True,exist_ok=True)
work=Path('/tmp/outrun_B_recovery07'); work.mkdir(parents=True,exist_ok=True)
source=work/'B1696633_HD.dds'
source_url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds'
source_sha_expected='3c58bf9587d0454e5bb8733bd35c5b2613b11c7fd52c49a428f0fa5fb4cea12d'
# Readable-orientation HD cells resolved from the persisted B_RECOVERY07 grid evidence.
spec=[
 ('name','NAME','이름',(48,744,230,812),0.00,'opaque_header'),
 ('status','STATUS','상태',(1628,744,1818,812),0.00,'opaque_header'),
 ('stage','Stage','스테이지',(1080,796,1248,876),0.10,'transparent'),
 ('next_stage','Next Stage','다음 스테이지',(1310,866,1635,974),0.10,'transparent'),
 ('ghost','Ghost','고스트',(1640,866,1840,974),0.10,'transparent'),
 ('total_time','Total Time','총 시간',(36,1640,820,1840),0.10,'transparent'),
 ('slipstream','Slipstream','슬립스트림',(950,1660,1368,1835),0.08,'transparent'),
 ('new_record','NEW Record!!','신기록!!',(1628,1638,1905,1840),0.08,'transparent'),
 ('extend_time','Extend Time','시간 연장',(835,1830,1820,2048),0.11,'transparent'),
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
    h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]
    pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
    pf=struct.unpack_from('<I',b,80)[0]; fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]
    masks=struct.unpack_from('<IIII',b,92)
    if not(fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and pitch==w*4 and mips==1 and len(b)==128+w*h*4):
        raise RuntimeError((h,w,pitch,mips,fourcc,bpp,masks,len(b)))
    raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA')
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],readable,{'width':w,'height':h,'pitch':pitch,'mips':mips,'pf_flags':pf,'fourcc':'00000000','bpp':bpp,'masks':[hex(x) for x in masks]}

def write_dds(srcp,readable,outp):
    b=Path(srcp).read_bytes(); raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=b[:128]+raw.tobytes('raw','RGBA'); Path(outp).write_bytes(payload); return hashlib.sha256(payload).hexdigest()
def count(mask): return int(np.count_nonzero(np.asarray(mask,dtype=np.uint8)))
def bin_alpha(im): return im.getchannel('A').point(lambda v:255 if v else 0)
def rect_mask(size,boxes):
    m=Image.new('L',size,0); d=ImageDraw.Draw(m)
    for b in boxes: d.rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=255)
    return m

def otsu_threshold(vals):
    hist=np.bincount(vals.astype(np.uint8),minlength=256).astype(np.float64)
    total=hist.sum(); total_sum=float(np.dot(np.arange(256),hist)); w0=s0=0.0; best=-1.0; threshold=128
    for t in range(256):
        w0+=hist[t]
        if w0<=0: continue
        w1=total-w0
        if w1<=0: break
        s0+=t*hist[t]; m0=s0/w0; m1=(total_sum-s0)/w1
        between=w0*w1*(m0-m1)*(m0-m1)
        if between>best: best=between; threshold=t
    return threshold

def components(mask,min_pixels=2):
    h,w=mask.shape; seen=np.zeros((h,w),bool); keep=np.zeros((h,w),bool)
    for y in range(h):
        for x in range(w):
            if not mask[y,x] or seen[y,x]: continue
            stack=[(x,y)]; seen[y,x]=1; pts=[]
            while stack:
                xx,yy=stack.pop(); pts.append((xx,yy))
                for nx,ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
                    if 0<=nx<w and 0<=ny<h and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx]=1; stack.append((nx,ny))
            if len(pts)>=min_pixels:
                for xx,yy in pts: keep[yy,xx]=1
    return keep

def source_mask_for(key,cell,bg_kind):
    x0,y0,x1,y1=cell; crop=np.asarray(src.crop(cell),dtype=np.uint8); h,w,_=crop.shape
    if bg_kind=='transparent':
        rawmask=(crop[:,:,3]>1)
        bg_meta={'type':'transparent','transparent_fraction':float(np.mean(crop[:,:,3]<=1))}
    else:
        rgb=crop[:,:,:3].astype(np.float32); lum=(.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2])
        # Remove the header strip's horizontal shading per scanline, then select only pixels materially darker than their row background.
        row_med=np.median(lum,axis=1)[:,None]
        rawmask=(lum < (row_med-24.0))&(crop[:,:,3]>200)
        bg_meta={'type':'opaque_header','segmentation':'row_luminance_minus_24','row_median_min':float(row_med.min()),'row_median_max':float(row_med.max())}
    keep=components(rawmask,2)
    full=Image.new('L',src.size,0); full.paste(Image.fromarray((keep*255).astype(np.uint8),'L'),(x0,y0))
    bb=full.getbbox()
    if not bb: raise RuntimeError(f'empty source text mask {key}: cell={cell} meta={bg_meta}')
    margins=(bb[0]-x0,bb[1]-y0,x1-bb[2],y1-bb[3])
    edge_bottom_ok=(key=='extend_time' and bb[3]==src.height and y1==src.height)
    if margins[0]<=0 or margins[1]<=0 or margins[2]<=0 or (margins[3]<=0 and not edge_bottom_ok):
        raise RuntimeError(f'cell clips source text {key}: cell={cell} bbox={bb} margins={margins}')
    return full,bb,bg_meta

def row_background(crop,mask):
    a=np.asarray(crop,dtype=np.uint8); m=np.asarray(mask,dtype=np.uint8)>0; out=a.copy()
    for y in range(a.shape[0]):
        candidates=a[y][~m[y]]
        if len(candidates)==0: raise RuntimeError('header row has no reconstruction samples')
        # robust local flat/gradient estimate for this scanline
        bg=np.median(candidates,axis=0).astype(np.uint8)
        out[y][m[y]]=bg
    return Image.fromarray(out,'RGBA')

def shear(im,slant):
    if not slant: return im
    shift=max(0,int(round(abs(slant)*(im.height-1))))
    out=Image.new('RGBA',(im.width+shift,im.height),(0,0,0,0))
    for y in range(im.height):
        dx=int(round(slant*(im.height-1-y)))
        if dx<0: dx+=shift
        out.alpha_composite(im.crop((0,y,im.width,y+1)),(dx,y))
    return out

def palette_from_source(key,bb):
    m=np.asarray(source_masks[key],dtype=np.uint8)>0; p=np.asarray(src,dtype=np.uint8)[m]
    p=p[p[:,3]>=24]
    if len(p)<8: return (255,255,255,255),(255,255,255,255),(0,8,57,255)
    lum=.2126*p[:,0]+.7152*p[:,1]+.0722*p[:,2]
    hi=p[lum>=np.percentile(lum,70)]; lo=p[lum<=np.percentile(lum,25)]
    top=tuple(int(v) for v in np.median(hi,axis=0)); bottom=top
    y0,y1=bb[1],bb[3]; ys=np.nonzero(m)[0]
    mid=(y0+y1)/2
    top_sel=p[:0]; bottom_sel=p[:0]
    # source-mask order matches row-major; recover rows for high-luminance source pixels
    coords=np.argwhere(m); pp=np.asarray(src,dtype=np.uint8)[m]; ll=.2126*pp[:,0]+.7152*pp[:,1]+.0722*pp[:,2]
    high=ll>=np.percentile(ll,70)
    if np.any(high & (coords[:,0]<mid)): top_sel=pp[high & (coords[:,0]<mid)]
    if np.any(high & (coords[:,0]>=mid)): bottom_sel=pp[high & (coords[:,0]>=mid)]
    if len(top_sel): top=tuple(int(v) for v in np.median(top_sel,axis=0))
    if len(bottom_sel): bottom=tuple(int(v) for v in np.median(bottom_sel,axis=0))
    outline=tuple(int(v) for v in np.median(lo,axis=0)) if len(lo) else (0,8,57,255)
    return top,bottom,outline

def render_target(key,text,bb,slant,bg_kind):
    x0,y0,x1,y1=bb; W=x1-x0; H=y1-y0; dummy=ImageDraw.Draw(Image.new('L',(8,8),0))
    top,bottom,outline=palette_from_source(key,bb)
    if bg_kind=='opaque_header':
        # header text is flat gray, no source outline/shadow
        srcp=np.asarray(src,dtype=np.uint8)[np.asarray(source_masks[key])>0]
        lum=.2126*srcp[:,0]+.7152*srcp[:,1]+.0722*srcp[:,2]
        dark=srcp[lum<=np.percentile(lum,55)]; fill=tuple(int(v) for v in np.median(dark,axis=0))
        for fs in range(min(130,int(H*.95)),9,-1):
            font=ImageFont.truetype(FONT_BOLD,fs); tb=dummy.textbbox((0,0),text,font=font); tw=tb[2]-tb[0]; th=tb[3]-tb[1]
            if tw>W-2 or th>H-2: continue
            g=Image.new('RGBA',(tw+6,th+6),(0,0,0,0)); ImageDraw.Draw(g).text((3-tb[0],3-tb[1]),text,font=font,fill=fill)
            gb=g.getchannel('A').getbbox(); g=g.crop(gb)
            layer=Image.new('RGBA',src.size,(0,0,0,0)); px=x0+(W-g.width)//2; py=y0+(H-g.height)//2; layer.alpha_composite(g,(px,py)); lb=layer.getchannel('A').getbbox()
            if lb and lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1: return layer,fs,0,lb,{'top':fill,'bottom':fill,'outline':fill}
        raise RuntimeError(f'cannot fit header {text} in {bb}')
    for fs in range(min(220,int(H*.92)),9,-1):
        font=ImageFont.truetype(FONT_BLACK,fs); sw=max(2,round(fs*.07)); shadow=max(1,round(fs*.035))
        tb=dummy.textbbox((0,0),text,font=font,stroke_width=sw); tw=tb[2]-tb[0]; th=tb[3]-tb[1]; pad=sw+shadow+5
        fillmask=Image.new('L',(tw+2*pad,th+2*pad),0); stroke=Image.new('L',fillmask.size,0)
        ImageDraw.Draw(fillmask).text((pad-tb[0],pad-tb[1]),text,font=font,fill=255)
        ImageDraw.Draw(stroke).text((pad-tb[0],pad-tb[1]),text,font=font,fill=255,stroke_width=sw,stroke_fill=255)
        sb=stroke.getbbox(); fillmask=fillmask.crop(sb); stroke=stroke.crop(sb)
        tile=Image.new('RGBA',stroke.size,(0,0,0,0))
        # compact source-like shadow behind the outlined glyph
        sh=Image.new('L',stroke.size,0); sh.paste(stroke,(shadow,shadow))
        shadow_rgba=(outline[0],outline[1],outline[2],min(190,max(80,outline[3])))
        tile.paste(shadow_rgba,(0,0),sh)
        tile.paste(outline,(0,0),stroke)
        arr=np.zeros((tile.height,tile.width,4),dtype=np.uint8)
        for yy in range(tile.height):
            t=yy/max(1,tile.height-1)
            arr[yy,:,0]=round(top[0]*(1-t)+bottom[0]*t); arr[yy,:,1]=round(top[1]*(1-t)+bottom[1]*t); arr[yy,:,2]=round(top[2]*(1-t)+bottom[2]*t); arr[yy,:,3]=255
        grad=Image.fromarray(arr,'RGBA'); tile.paste(grad,(0,0),fillmask)
        tile=shear(tile,slant); gb=tile.getchannel('A').getbbox(); tile=tile.crop(gb)
        if tile.width>W-2 or tile.height>H-2: continue
        layer=Image.new('RGBA',src.size,(0,0,0,0)); px=x0+(W-tile.width)//2; py=y0+(H-tile.height)//2; layer.alpha_composite(tile,(px,py)); lb=layer.getchannel('A').getbbox()
        if lb and lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1: return layer,fs,sw,lb,{'top':top,'bottom':bottom,'outline':outline}
    raise RuntimeError(f'cannot fit {text} in {bb}')

header,src,info=load_dds(source)
if src.size!=(2048,2048): raise RuntimeError(info)
source_masks={}; source_bboxes={}; mask_meta={}; source_text=Image.new('L',src.size,0)
for key,en,ko,cell,slant,bg in spec:
    m,bb,meta=source_mask_for(key,cell,bg); source_masks[key]=m; source_bboxes[key]=bb; mask_meta[key]=meta; source_text=ImageChops.lighter(source_text,m)
allowed=rect_mask(src.size,list(source_bboxes.values())); protected=ImageChops.invert(allowed)
# Clean plate: exact transparent removal or row-wise source-neighbor reconstruction for the two header labels.
clean=src.copy()
for key,en,ko,cell,slant,bg in spec:
    x0,y0,x1,y1=cell; local=source_masks[key].crop(cell)
    if bg=='transparent':
        a=np.asarray(clean).copy(); lm=np.asarray(source_masks[key])>0; a[lm]=(0,0,0,0); clean=Image.fromarray(a,'RGBA')
    else:
        rec=row_background(src.crop(cell),local); clean.paste(rec,cell)
# Render nine fresh Korean labels from measured source styles.
final=clean.copy(); layers={}; render_meta={}
for key,en,ko,cell,slant,bg in spec:
    layer,fs,sw,lb,pal=render_target(key,ko,source_bboxes[key],slant,bg); layers[key]=layer; final.alpha_composite(layer)
    render_meta[key]={'font_size':fs,'stroke_width':sw,'localized_bbox':lb,'palette':pal}

candidate_sha=write_dds(source,final,candidate)
chead,decoded,cinfo=load_dds(candidate)
if chead!=header or cinfo!=info or ImageChops.difference(final,decoded).getbbox() is not None: raise RuntimeError('DDS roundtrip/header mismatch')
# Static gates.
target=Image.new('L',src.size,0)
for layer in layers.values(): target=ImageChops.lighter(target,bin_alpha(layer))
rows=[]
for key,en,ko,cell,slant,bg in spec:
    ob=source_bboxes[key]; lb=render_meta[key]['localized_bbox']
    ok=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
    if not ok: raise RuntimeError((key,ob,lb))
    rows.append({'key':key,'source':en,'korean':ko,'hd_cell':list(cell),'original_bbox':list(ob),'localized_bbox':list(lb),'delta_left':lb[0]-ob[0],'delta_right':ob[2]-lb[2],'delta_top':lb[1]-ob[1],'delta_bottom':ob[3]-lb[3],'containment':'PASS','rework_status':'NEW_CANDIDATE','native_font_size':render_meta[key]['font_size'],'stroke_width':render_meta[key]['stroke_width'],'palette':render_meta[key]['palette'],'source_mask_meta':mask_meta[key],'historical_localized_raster_reused':False})
diff=ImageChops.difference(src,decoded); bands=diff.split(); dm=bands[0]
for z in bands[1:]: dm=ImageChops.lighter(dm,z)
dm=dm.point(lambda v:255 if v else 0)
outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed))); protected_changes=count(ImageChops.multiply(dm,protected))
ad=ImageChops.difference(src.getchannel('A'),decoded.getchannel('A')).point(lambda v:255 if v else 0); alpha_out=count(ImageChops.multiply(ad,ImageChops.invert(allowed)))
cd=ImageChops.difference(src,clean); bands=cd.split(); cm=bands[0]
for z in bands[1:]: cm=ImageChops.lighter(cm,z)
cm=cm.point(lambda v:255 if v else 0); clean_out=count(ImageChops.multiply(cm,ImageChops.invert(source_text)))
# Transparent elements must be completely cleared under the source effect mask.
residue=0
for key,en,ko,cell,slant,bg in spec:
    if bg=='transparent': residue+=count(ImageChops.multiply(bin_alpha(clean),source_masks[key]))
if any((outside,protected_changes,alpha_out,clean_out,residue)): raise RuntimeError(('static gate',outside,protected_changes,alpha_out,clean_out,residue))
overlap=[]; keys=list(layers)
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        n=count(ImageChops.multiply(bin_alpha(layers[keys[i]]),bin_alpha(layers[keys[j]])))
        if n: overlap.append([keys[i],keys[j],n])
if overlap: raise RuntimeError(('target overlap',overlap))
# Evidence.
source_text.save(outdir/'B1696633_SOURCE_TEXT_MASK.png'); allowed.save(outdir/'B1696633_ALLOWED_TEXT_REGION_MASK.png'); protected.save(outdir/'B1696633_PROTECTED_MASK.png'); clean.save(outdir/'B1696633_CLEAN_PLATE.png'); target.save(outdir/'B1696633_TARGET_TEXT_MASK.png')
srcpng=work/'source.png'; cleanpng=work/'clean.png'; finalpng=work/'final.png'; src.save(srcpng); clean.save(cleanpng); decoded.save(finalpng)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(cleanpng),str(outdir/'B1696633_SOURCE_TEXT_MASK.png'),'--report',str(outdir/'B_RECOVERY07_CLEAN_PLATE_VALIDATION.json')],check=True)
subprocess.run(['python3',str(repo/'tools/localization/validate_clean_plate.py'),str(srcpng),str(finalpng),str(outdir/'B1696633_ALLOWED_TEXT_REGION_MASK.png'),'--protected-mask',str(outdir/'B1696633_PROTECTED_MASK.png'),'--report',str(outdir/'B_RECOVERY07_FINAL_MASK_VALIDATION.json')],check=True)
label_font=ImageFont.truetype(FONT_BOLD,22)
def comp(im,bg): z=Image.new('RGBA',im.size,bg); z.alpha_composite(im); return z.convert('RGB')
def card(label,im,bg):
    v=comp(im,bg); v.thumbnail((800,800)); c=Image.new('RGB',(v.width,v.height+34),'white'); c.paste(v,(0,34)); ImageDraw.Draw(c).text((6,3),label,font=label_font,fill='black'); return c
cards=[card('SOURCE',src,(72,72,72,255)),card('CLEAN',clean,(72,72,72,255)),card('FINAL',decoded,(72,72,72,255)),card('FINAL_WHITE',decoded,(255,255,255,255))]
W=cards[0].width+cards[1].width+10; H=cards[0].height+cards[2].height+10; sheet=Image.new('RGB',(W,H),'white'); sheet.paste(cards[0],(0,0)); sheet.paste(cards[1],(cards[0].width+10,0)); sheet.paste(cards[2],(0,cards[0].height+10)); sheet.paste(cards[3],(cards[2].width+10,cards[1].height+10)); sheet.save(outdir/'B_RECOVERY07_B1696633_COMPARE.jpg',quality=94)
# Per-row readable QA contact sheet.
contacts=[]
for n,row in enumerate(rows,1):
    ob=row['original_bbox']; pad=24; cr=(max(0,ob[0]-pad),max(0,ob[1]-pad),min(src.width,ob[2]+pad),min(src.height,ob[3]+pad))
    a=comp(src,(72,72,72,255)).crop(cr); b=comp(decoded,(72,72,72,255)).crop(cr); h=max(a.height,b.height)+36
    c=Image.new('RGB',(a.width+b.width+8,h),'white'); c.paste(a,(0,36)); c.paste(b,(a.width+8,36)); ImageDraw.Draw(c).text((4,3),f'{n}. {row["source"]} -> {row["korean"]}',font=label_font,fill='black'); contacts.append(c)
CW=max(c.width for c in contacts); CH=sum(c.height for c in contacts)+6*(len(contacts)-1); cs=Image.new('RGB',(CW,CH),'white'); yy=0
for c in contacts: cs.paste(c,(0,yy)); yy+=c.height+6
cs.save(outdir/'B_RECOVERY07_B1696633_ROW_CONTACT.jpg',quality=95)
raws=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM); rawf=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM); p1=card('SOURCE_RAW',raws,(72,72,72,255)); p2=card('FINAL_RAW',rawf,(72,72,72,255)); rs=Image.new('RGB',(p1.width+p2.width+8,max(p1.height,p2.height)),'white'); rs.paste(p1,(0,0)); rs.paste(p2,(p1.width+8,0)); rs.save(outdir/'B_RECOVERY07_B1696633_RAW_COMPARE.jpg',quality=92)
report={'schema_version':1,'role':'B','run':run,'base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'queue_index':48,'asset':asset_rel,'readiness_tier':'RENDER_READY_AFTER_PERSISTED_HD_GRID_DIAGNOSTIC','source_upstream_repo':'Sonic-TV/OR2006Sprites','source_upstream_commit':'a95efe01d1f136514cef94b0d9e9fd61df021754','source_url':source_url,'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'candidate_path':str(candidate.relative_to(repo)),'method':'pinned exact HD source -> nine source glyph/effect masks -> protected mask -> transparent/row-reconstructed clean plate -> fresh native-resolution Korean lettering with measured source palette/slant -> exact source-header RGBA32 DDS -> decoded final QA','historical_full_draft_note':'used only as discovery evidence; no historical localized raster pixels reused or upscaled','structure':{**info,'header_128_exact':True,'raw_orientation':'mirror_y','channel_layout':'RGBA masks preserved'},'segments_total':9,'segments_rendered':9,'clean_plate':{'changed_pixels_outside_source_text_mask':clean_out,'transparent_source_text_residue_pixels':residue,'status':'PASS'},'containment':{'elements_total':9,'elements_pass':9,'elements_fail':0,'changed_pixels_outside_permitted_source_bboxes':outside,'alpha_changed_outside_permitted_source_bboxes':alpha_out,'protected_changes':protected_changes,'target_overlap_pairs':overlap,'status':'PASS'},'rows':rows,'manual_visual_qa':'PENDING_CONTROLLER_SELF_QA','RUNTIME_VALIDATION':'UNTESTED','status':'B_RECOVERY07_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C'}
(outdir/'B_RECOVERY07_B1696633_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(outdir/'B_RECOVERY07_STATIC_VALIDATION_SUMMARY.json').write_text(json.dumps({'source_sha256':source_sha_expected,'candidate_sha256':candidate_sha,'bbox_pass':'9/9','clean_plate_outside_mask':clean_out,'transparent_residue_pixels':residue,'outside_permitted_bboxes':outside,'alpha_outside_permitted_bboxes':alpha_out,'protected_changes':protected_changes,'target_overlap_pairs':0,'header_128_exact':True,'raw_orientation':'mirror_y','status':'PASS'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('B_RECOVERY07_DONE',candidate_sha,'bbox=9/9','outside=',outside,'protected=',protected_changes,'residue=',residue)
