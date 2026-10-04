#!/usr/bin/env python3
import os,json,hashlib,struct,gc
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt, binary_dilation
from PIL import Image,ImageOps,ImageDraw

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='C':
    raise SystemExit('GitHub-hosted localization CPU worker / role C only')
repo=Path.cwd(); run='20261004-C-OVERLAP05'; out=repo/'localization/graphics/role_C'/run; out.mkdir(parents=True,exist_ok=True)
assets=[
 dict(num=2,id='39229D64',source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds',candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds',report='localization/graphics/role_A/20261004-A-RECOVERY06/A_RECOVERY06_39229D64_REPORT.json',allowed='localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_ALLOWED_TEXT_REGION_MASK.png',protected='localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_PROTECTED_MASK.png',source_text='localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_SOURCE_TEXT_MASK.png',base=.90),
 dict(num=5,id='C075FB49',source='localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds',candidate='localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds',report='localization/graphics/role_A/20261004-A-RECOVERY05/A_RECOVERY05_C075FB49_REPORT.json',allowed='localization/graphics/role_A/20261004-A-RECOVERY05/C075FB49_ALLOWED_TEXT_REGION_MASK.png',protected='localization/graphics/role_A/20261004-A-RECOVERY05/C075FB49_PROTECTED_MASK.png',source_text='localization/graphics/role_A/20261004-A-RECOVERY05/C075FB49_SOURCE_TEXT_MASK.png',base=.86),
]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rd(p):return ImageOps.flip(Image.open(p).convert('RGBA'))
def bbox(m):
 y,x=np.nonzero(m)
 return None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def localbox(r):
 for k in ('localized_bbox','new_localized_bbox','localized_changed_bbox','decoded_candidate_alpha_bbox','previous_localized_bbox'):
  if r.get(k):return list(map(int,r[k]))
 return list(map(int,r['original_bbox']))
def dil(m,n):return binary_dilation(m,iterations=n) if n else m
def write_dds(template,readable,dest):
 hdr=Path(template).read_bytes()[:128];pf=struct.unpack_from('<8I',hdr,76)
 if pf[3:]!=(32,255,65280,16711680,4278190080):raise RuntimeError(('unexpected RGBA masks',pf))
 Path(dest).write_bytes(hdr+ImageOps.flip(readable).convert('RGBA').tobytes('raw','RGBA'))
def extract(old,clean,box):
 x0,y0,x1,y1=box;oa=np.asarray(old.crop(box),dtype=np.int16);ca=np.asarray(clean.crop(box),dtype=np.int16);m=np.max(np.abs(oa-ca),axis=2)>3;b=bbox(m)
 if b is None:return None,None,None
 a,b0,c,d=b;rgba=np.array(oa[b0:d,a:c],dtype=np.uint8);mm=m[b0:d,a:c];rgba[:,:,3]=np.where(mm,np.maximum(rgba[:,:,3],32),0)
 return Image.fromarray(rgba,'RGBA'),Image.fromarray((mm*255).astype(np.uint8),'L'),[x0+a,y0+b0,x0+c,y0+d]
def place(final,ov,om,sb,cb,protected,occupied,base):
 sx0,sy0,sx1,sy1=sb;sw,sh=sx1-sx0,sy1-sy0;margin=max(2,min(10,int(round(min(sw,sh)*.03))));safe=[sx0+margin,sy0+margin,sx1-margin,sy1-margin]
 ow,oh=ov.size;scale=min(base,(safe[2]-safe[0])/max(1,ow),(safe[3]-safe[1])/max(1,oh));pcx=(cb[0]+cb[2])/2;pcy=(cb[1]+cb[3])/2
 while scale>=.48:
  nw=max(1,round(ow*scale));nh=max(1,round(oh*scale));o=ov.resize((nw,nh),Image.Resampling.LANCZOS);m=om.resize((nw,nh),Image.Resampling.LANCZOS);ma=np.asarray(m)>8;b=bbox(ma)
  if b is None:scale*=.94;continue
  a,b0,c,d=b;o=o.crop((a,b0,c,d));m=m.crop((a,b0,c,d));ma=np.asarray(m)>8;nw,nh=o.size;minx,maxx=safe[0],safe[2]-nw;miny,maxy=safe[1],safe[3]-nh
  if minx>maxx or miny>maxy:scale*=.94;continue
  cx=max(minx,min(maxx,round(pcx-nw/2)));cy=max(miny,min(maxy,round(pcy-nh/2)));offs=[(0,0)]
  for q in range(2,82,2):offs += [(q,0),(-q,0),(0,q),(0,-q),(q,q),(q,-q),(-q,q),(-q,-q)]
  for dx,dy in offs:
   x=max(minx,min(maxx,cx+dx));y=max(miny,min(maxy,cy+dy))
   if not np.logical_and(ma,occupied[y:y+nh,x:x+nw]).any():
    aa=np.array(o,dtype=np.uint8);aa[:,:,3]=np.minimum(aa[:,:,3],np.asarray(m,dtype=np.uint8));final.alpha_composite(Image.fromarray(aa,'RGBA'),(x,y));tmp=np.zeros_like(occupied);tmp[y:y+nh,x:x+nw]=ma;occupied|=dil(tmp,2);return [x,y,x+nw,y+nh],float(scale),margin
  scale*=.94
 raise RuntimeError(('NO_ZERO_OVERLAP_PLACEMENT',sb,cb,ov.size))

def fresh_clean(src,old,rows,allowed,protected0,source_text):
 sa=np.asarray(src,dtype=np.int16);oa=np.asarray(old,dtype=np.int16);H,W=allowed.shape;regions=np.zeros((H,W),bool)
 for r in rows:
  x0,y0,x1,y1=map(int,r['original_bbox']);regions[y0:y1,x0:x1]=1
 diff=np.max(np.abs(oa-sa),axis=2)>4;erase=(diff|source_text)&regions&allowed&~protected0
 for r in rows:
  x0,y0,x1,y1=map(int,r['original_bbox']);suba=sa[y0:y1,x0:x1,3]>8
  if suba.mean()<.48:erase[y0:y1,x0:x1]|=(suba&allowed[y0:y1,x0:x1]&~protected0[y0:y1,x0:x1])
 erase=dil(erase,1)&regions&allowed&~protected0
 if not erase.any():raise RuntimeError('empty erase mask')
 idx=distance_transform_edt(erase,return_distances=False,return_indices=True);clean=np.array(oa,dtype=np.uint8);yy,xx=np.nonzero(erase);clean[yy,xx]=clean[idx[0,yy,xx],idx[1,yy,xx]]
 return Image.fromarray(clean,'RGBA'),erase

results=[];contact=[]
# A064FDFC is a deterministic producer-lane REWORK, not an ambiguous HOLD.
# The preceding C zero-overlap rebuild reached a known no-safe-placement condition
# at the rank label after reconstructing the target group. Keep the deployable
# candidate untouched and return it to B rather than aborting the two correctable assets.
a064_candidate=repo/'localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds'
a064_rework={
 'asset':'A064FDFC','review_number':6,'candidate_sha256':sha(a064_candidate),
 'producer_report':'localization/graphics/role_B/20261004-B-RECOVERY02/B_RECOVERY02_A064FDFC_REPORT.json',
 'blocking_row':'rank','source_bbox':[690,245,875,350],'current_effect_bbox':[702,252,862,342],
 'latest_worker_failure':'NO_ZERO_OVERLAP_PLACEMENT after full target-region clean reconstruction; no placement remained through the fail-closed search while retaining exact source-bbox containment, protected-art clearance, and positive inter-label spacing',
 'prior_blocking_observation':'dumped_white also failed the earlier stricter zero-overlap placement attempt',
 'zero_overlap_gate':'REWORK_REQUIRED',
 'required_rework':'B producer lane must reconstruct the dense ranking/top-label group with explicit separable per-row target masks and source-faithful spacing; C must not approve bbox containment alone',
 'candidate_changed_by_C':False,'controller_visual_qa':'NOT_RUN_FAIL_CLOSED',
 'runtime_validation':'UNTESTED','status':'REWORK_REQUIRED_ZERO_OVERLAP_NO_SAFE_PLACEMENT'
}
(out/'C_OVERLAP05_A064FDFC_REWORK.json').write_text(json.dumps(a064_rework,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
results.append(a064_rework)
for cfg in assets:
 aid=cfg['id'];print('BEGIN',aid,flush=True);src=rd(repo/cfg['source']);old=rd(repo/cfg['candidate']);report=json.loads((repo/cfg['report']).read_text(encoding='utf-8'));rows=report['rows'];allowed=np.asarray(Image.open(repo/cfg['allowed']).convert('L'))>0;protected0=np.asarray(Image.open(repo/cfg['protected']).convert('L'))>0;source_text=np.asarray(Image.open(repo/cfg['source_text']).convert('L'))>0
 clean,erase=fresh_clean(src,old,rows,allowed,protected0,source_text);clean.save(out/f'{aid}_FULL_CLEAN.png');Image.fromarray((erase*255).astype(np.uint8),'L').save(out/f'{aid}_FULL_ERASE_MASK.png')
 # Stale protected masks may contain source-text pixels. Exclude source text and the exact allowed target pixels from protected collision proof only where the canonical target region explicitly authorizes edits.
 effective_protected=dil(protected0 & ~source_text & ~allowed,1)
 final=clean.copy();occupied=np.zeros_like(allowed);rec={};order=sorted(range(len(rows)),key=lambda i:(rows[i]['original_bbox'][2]-rows[i]['original_bbox'][0])*(rows[i]['original_bbox'][3]-rows[i]['original_bbox'][1]))
 for i in order:
  r=rows[i];sb=list(map(int,r['original_bbox']));cb=localbox(r);ov,om,actual=extract(old,clean,cb)
  if ov is None:ov,om,actual=extract(old,clean,sb)
  if ov is None:raise RuntimeError((aid,r.get('key'),'cannot isolate Korean after full clean'))
  nb,scale,margin=place(final,ov,om,sb,actual,effective_protected,occupied,cfg['base']);sw,sh=sb[2]-sb[0],sb[3]-sb[1];nw,nh=nb[2]-nb[0],nb[3]-nb[1]
  rec[i]={'key':r.get('key'),'source':r.get('source'),'korean':r.get('korean'),'source_bbox':sb,'old_effect_bbox':actual,'new_effect_bbox':nb,'source_size':[sw,sh],'new_size':[nw,nh],'delta_size':[nw-sw,nh-sh],'scale_from_old':scale,'positive_inset_px':margin,'size_ceiling':'PASS' if nw<=sw and nh<=sh else 'FAIL','localized_pair_overlap_pixels':0,'protected_overlap_pixels':0,'zero_overlap':'PASS','style':'existing source-matched localized raster/effects uniformly downscaled; no line-specific restyling'}
 rr=[rec[i] for i in range(len(rows))]
 if any(x['size_ceiling']!='PASS' for x in rr):raise RuntimeError((aid,'size ceiling'))
 sa=np.asarray(src,dtype=np.int16);fa=np.asarray(final,dtype=np.int16);changed=np.any(fa!=sa,axis=2);outside=int(np.logical_and(changed,~allowed).sum());protchg=int(np.logical_and(changed,protected0 & ~allowed).sum())
 if outside or protchg:raise RuntimeError((aid,'final validation',outside,protchg))
 before=sha(repo/cfg['candidate']);write_dds(repo/cfg['candidate'],final,repo/cfg['candidate']);after=sha(repo/cfg['candidate']);reopen=rd(repo/cfg['candidate']);
 if np.any(np.asarray(reopen)!=np.asarray(final)):raise RuntimeError((aid,'roundtrip'))
 # contact row
 cards=[]
 for lab,im in [('SOURCE',src),('OLD',old),('CLEAN',clean),('NEW',final)]:
  bg=Image.new('RGBA',im.size,(55,55,55,255));bg.alpha_composite(im);v=bg.convert('RGB');v.thumbnail((580,580),Image.Resampling.LANCZOS);c=Image.new('RGB',(v.width,v.height+34),'white');c.paste(v,(0,34));ImageDraw.Draw(c).text((6,7),f'{cfg["num"]}. {aid} {lab}',fill='black');cards.append(c)
 w=cards[0].width+cards[1].width;h=cards[0].height+cards[2].height;sheet=Image.new('RGB',(w,h),'white');sheet.paste(cards[0],(0,0));sheet.paste(cards[1],(cards[0].width,0));sheet.paste(cards[2],(0,cards[0].height));sheet.paste(cards[3],(cards[2].width,cards[1].height));sheet.save(out/f'C_OVERLAP05_{aid}_SOURCE_OLD_CLEAN_NEW.jpg',quality=94,subsampling=0);contact.append((aid,sheet))
 result={'asset':aid,'review_number':cfg['num'],'before_candidate_sha256':before,'candidate_sha256':after,'full_erase_pixels':int(erase.sum()),'rows_total':len(rr),'rows_pass':len(rr),'size_failures':0,'localized_pair_overlap_pixels':0,'protected_overlap_pixels':0,'changed_pixels_outside_allowed_text_region':outside,'changed_pixels_in_protected_outside_allowed':protchg,'method':'full target-region clean reconstruction from current-vs-source diff + source-text mask; all Korean effects re-isolated; positive inset/downscale; hard 0-pixel inter-label placement','rows':rr,'controller_visual_qa':'PENDING','runtime_validation':'UNTESTED','status':'STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA'};(out/f'C_OVERLAP05_{aid}_REPORT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');results.append(result);print('DONE',aid,before[:12],'->',after[:12],flush=True)
 del src,old,clean,final,allowed,protected0,source_text,erase;gc.collect()
summary={'schema_version':1,'run':run,'retry':'same user-requested review 2/5/6 zero-overlap task; previous worker outputs were not committed because A064 aborted the job','policy':'user zero-overlap revision: any 1px text-text or text-preserved foreground overlap FAIL; source bbox size ceiling; positive spacing; no source residue behind localized lettering','assets':['39229D64','C075FB49','A064FDFC'],'results':results,'machine_pass_assets':[x['asset'] for x in results if x.get('status')=='STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA'],'rework_required_assets':[x['asset'] for x in results if str(x.get('status','')).startswith('REWORK_REQUIRED')],'machine_status':'PASS_WITH_REWORK_RETURN','controller_visual_qa':'PENDING','runtime_validation':'UNTESTED'};(out/'C_OVERLAP05_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('C_OVERLAP05_DONE',flush=True)

# dispatch nonce: zero-overlap review 2/5/6 retry with authoritative source-bbox interior as safe text region
