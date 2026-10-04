#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,traceback,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

RUN="20261005-B-PRODUCTION51"
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/1F5FE6E9_1024x512.dds"
INDEX=132
LABELS=[("REQUEST","요청"),("SPECIAL REQUEST 1","스페셜 요청 1"),("SPECIAL REQUEST 2","스페셜 요청 2"),("SPECIAL REQUEST 3","스페셜 요청 3")]

def main():
    repo=Path.cwd(); out=repo/"localization/graphics/role_B"/RUN; out.mkdir(parents=True,exist_ok=True)
    wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
    srczip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
    histzip=repo/"localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip"
    cand=repo/"localization/graphics/hd_candidates"/ASSET; cand.parent.mkdir(parents=True,exist_ok=True)
    source_sha="3656adbd699b7852cb5fcf4bb01fc4f1f65bbd9d7d39e12e7a1c2ac5a49fef1d"
    hist_sha="a775eff64b49ac61f107a55ab0233f89fc6cdaa0bfd6e97d3fa5aa112180dc45"
    with zipfile.ZipFile(srczip) as z: sb=z.read(ASSET)
    with zipfile.ZipFile(histzip) as z: hb=z.read(ASSET)
    def sha(b): return hashlib.sha256(b).hexdigest()
    if sha(sb)!=source_sha or sha(hb)!=hist_sha: raise RuntimeError(("sha",sha(sb),sha(hb)))
    H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
    if (W,H)!=(1024,512) or len(sb)!=128+W*H*4 or hb[:128]!=sb[:128]: raise RuntimeError(("structure",W,H,mips,len(sb)))
    raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
    raw_hist=Image.frombytes("RGBA",(W,H),hb[128:],"raw","RGBA")
    # B51 preflight visual proof established mirror-Y as the exact readable orientation.
    src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    hist=raw_hist.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    sa=np.asarray(src,dtype=np.uint8); ha=np.asarray(hist,dtype=np.uint8)
    diff=np.any(sa!=ha,axis=2)

    # Historical candidate is location evidence only. Detect its four changed row plates,
    # but never reuse historical color/background/text pixels.
    lab,n=ndimage.label(diff,np.ones((3,3),dtype=np.uint8))
    comps=[]
    for i in range(1,n+1):
        yy,xx=np.nonzero(lab==i); area=len(xx)
        if area<120: continue
        bb=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
        if bb[0] < W//2: continue
        comps.append((area,bb))
    comps.sort(reverse=True)
    # merge components sharing essentially the same row
    boxes=sorted([bb for _,bb in comps[:12]],key=lambda b:(b[1],b[0]))
    merged=[]
    for b in boxes:
        hit=False
        for k,a in enumerate(merged):
            ov=max(0,min(a[3],b[3])-max(a[1],b[1])); mh=min(a[3]-a[1],b[3]-b[1])
            if mh>0 and ov/mh>0.72 and abs(((a[1]+a[3])-(b[1]+b[3]))/2)<10:
                merged[k]=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])];hit=True;break
        if not hit: merged.append(b)
    # Keep four dominant rows in the known text band.
    merged=[b for b in merged if 70<=b[1]<=260 and b[0]>=520]
    merged=sorted(merged,key=lambda b:b[1])
    # Historical draft bars for SPECIAL REQUEST 2/3 are vertically contiguous,
    # so the diff labels them as one ~2-row component. Split only this proven
    # 3-component case when the final component is about twice the normal row height.
    if len(merged)==3:
        hs=[b[3]-b[1] for b in merged]
        base=(hs[0]+hs[1])/2.0
        if hs[2]>=1.7*base:
            b=merged[2]; mid=(b[1]+b[3])//2
            merged=merged[:2]+[[b[0],b[1],b[2],mid],[b[0],mid,b[2],b[3]]]
    if len(merged)!=4:
        (out/"B51_DISCOVERY_FAIL.json").write_text(json.dumps({"components":comps[:20],"merged":merged},indent=2)+"\n")
        raise RuntimeError(("expected four historical row hints",len(merged)))

    rows=[]; sms=[]; full=np.zeros((H,W),bool)
    for idx,(cell,(en,ko)) in enumerate(zip(merged,LABELS),1):
        # Expand hint modestly to include original English fringe, not neighboring panels.
        cx0,cy0,cx1,cy1=cell; x0=max(0,cx0-14); y0=max(0,cy0-8); x1=min(W,cx1+14); y1=min(H,cy1+8)
        roi=sa[y0:y1,x0:x1].astype(np.float32)
        # Estimate flat/near-flat dark panel background from outer border.
        h,w=roi.shape[:2]
        border=np.zeros((h,w),bool); border[:4,:]=1;border[-4:,:]=1;border[:,:4]=1;border[:,-4:]=1
        bp=roi[border]
        # robust background RGB/alpha median; colored panel line at row edge cannot dominate border.
        bg=np.median(bp,axis=0)
        dist=np.sqrt(np.sum((roi[:,:,:3]-bg[:3])**2,axis=2))
        # Text core = clear color deviation away from the dark panel; exclude cell edges and very low alpha.
        core=(dist>18)&(roi[:,:,3]>max(8,bg[3]*0.25))
        core[:3,:]=0;core[-3:,:]=0;core[:,:3]=0;core[:,-3:]=0
        # Keep connected components consistent with glyph fragments, reject broad artwork/panel blocks.
        ll,nn=ndimage.label(core,np.ones((3,3),dtype=np.uint8)); kept=np.zeros_like(core)
        for j in range(1,nn+1):
            yy,xx=np.nonzero(ll==j)
            if 2<=len(xx)<=1200 and (xx.max()-xx.min()+1)<=max(80,w//2) and (yy.max()-yy.min()+1)<=max(36,h-4):
                kept[yy,xx]=1
        # Recover antialias/effect fringe at lower color-distance threshold around kept core.
        near=np.asarray(Image.fromarray((kept.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
        sm_local=near & (dist>5) & (roi[:,:,3]>3)
        yy,xx=np.nonzero(sm_local)
        if len(xx)<30: raise RuntimeError(("source text mask too small",idx,cell,int(len(xx)),bg.tolist()))
        bb=[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1]
        dens=len(xx)/max(1,(bb[2]-bb[0])*(bb[3]-bb[1]))
        if dens>0.55 or bb[0]<=x0+1 or bb[2]>=x1-1: raise RuntimeError(("ambiguous source mask",idx,cell,bb,dens))
        sm=np.zeros((H,W),bool);sm[y0:y1,x0:x1]=sm_local;sms.append(sm);full|=sm
        rows.append({"n":idx,"source":en,"korean":ko,"historical_hint_bbox":cell,"measurement_cell":[x0,y0,x1,y1],
                     "original_bbox":bb,"source_effect_pixels":int(len(xx)),"mask_density":dens,
                     "background_rgba":[float(v) for v in bg]})

    for i in range(4):
        for j in range(i+1,4):
            if np.any(sms[i]&sms[j]): raise RuntimeError(("source mask overlap",i+1,j+1))

    # Background-aware reconstruction: fit a local RGBA plane from a 5px ring around each
    # exact source-effect mask. This uses exact source pixels only.
    clean=sa.astype(np.float32).copy()
    for row,sm in zip(rows,sms):
        dil=np.asarray(Image.fromarray((sm.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(11)))>0
        ring=dil & ~sm
        yy,xx=np.nonzero(ring)
        if len(xx)<80: raise RuntimeError(("insufficient clean ring",row["n"]))
        A=np.column_stack([np.ones(len(xx)),xx.astype(float),yy.astype(float)])
        vals=sa[yy,xx].astype(float)
        coefs=[];pred_ring=np.zeros_like(vals)
        for c in range(4):
            coef=np.linalg.lstsq(A,vals[:,c],rcond=None)[0];coefs.append(coef);pred_ring[:,c]=A@coef
        mae=float(np.mean(np.abs(pred_ring[:,:3]-vals[:,:3])))
        # Text rows sit on a flat/very smooth dark panel. Fail closed if model says otherwise.
        if mae>12: raise RuntimeError(("background not smooth enough",row["n"],mae))
        my,mx=np.nonzero(sm); MA=np.column_stack([np.ones(len(mx)),mx.astype(float),my.astype(float)])
        for c in range(4): clean[my,mx,c]=np.clip(MA@coefs[c],0,255)
        row["clean_ring_rgb_mae"]=mae
    clean_a=np.rint(clean).astype(np.uint8)
    clean_img=Image.fromarray(clean_a,"RGBA")

    # Shared source style: same font family/weight/size/color across all four source rows.
    p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    if not p or not Path(p).exists() or "NotoSansCJK" not in Path(p).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True);subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    if "NotoSansCJK" not in Path(p).name: raise RuntimeError(("font unavailable",p))
    FONT=p
    pix=sa[full]; # actual source text/effect palette only
    alpha=pix[:,3]>5; pix=pix[alpha]
    fill=tuple(int(v) for v in np.median(pix,axis=0)) if len(pix) else (145,135,78,255)

    def tile(text,fs):
        f=ImageFont.truetype(FONT,fs);d=ImageDraw.Draw(Image.new("L",(8,8),0));tb=d.textbbox((0,0),text,font=f)
        pad=3; im=Image.new("RGBA",(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad),(0,0,0,0))
        ImageDraw.Draw(im).text((pad-tb[0],pad-tb[1]),text,font=f,fill=fill)
        bb=im.getchannel("A").getbbox();return im.crop(bb) if bb else None
    min_h=min(r["original_bbox"][3]-r["original_bbox"][1] for r in rows)
    common=None
    for fs in range(min(80,max(14,int(min_h*.95))),7,-1):
        ts=[tile(r["korean"],fs) for r in rows]
        if all(t and t.width<=r["source_width"]-2 if "source_width" in r else True for t,r in zip(ts,rows)):
            ok=True
            for t,r in zip(ts,rows):
                ob=r["original_bbox"]
                if t.width>ob[2]-ob[0]-2 or t.height>ob[3]-ob[1]-2:ok=False;break
            if ok: common=(fs,ts);break
    if common is None: raise RuntimeError("cannot fit shared typography")
    fs,tiles=common

    final=clean_img.copy();tms=[];target=np.zeros((H,W),bool)
    for row,t in zip(rows,tiles):
        x0,y0,x1,y1=row["original_bbox"]; aw=x1-x0;ah=y1-y0
        # Preserve source left alignment; leave a 1px positive left/top/bottom margin.
        px=x0+1; py=y0+(ah-t.height)//2
        if px+t.width>=x1 or py<=y0 or py+t.height>=y1: raise RuntimeError(("fit",row["n"],row["original_bbox"],t.size))
        layer=Image.new("RGBA",(W,H),(0,0,0,0));layer.alpha_composite(t,(px,py));lm=np.asarray(layer.getchannel("A"))>0
        for old in tms:
            if np.any(lm&old):raise RuntimeError(("localized overlap",row["n"]))
        tms.append(lm);target|=lm;final.alpha_composite(layer)
        lb=list(layer.getchannel("A").getbbox());ob=row["original_bbox"]
        row.update({"source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],"localized_bbox":lb,
          "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
          "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],"containment":"PASS","size_ceiling":"PASS",
          "font_size":fs,"font_basename":Path(FONT).name,"fill_rgba":fill,"shared_source_style":"PASS"})

    raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM);payload=sb[:128]+raw_final.tobytes("raw","RGBA");cand.write_bytes(payload);csha=sha(payload)
    raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw","RGBA");dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if payload[:128]!=sb[:128] or ImageChops.difference(final,dec).getbbox():raise RuntimeError("roundtrip")
    da=np.asarray(dec,dtype=np.uint8);allowed=np.zeros((H,W),bool)
    for r in rows:x0,y0,x1,y1=r["original_bbox"];allowed[y0:y1,x0:x1]=1
    changed=np.any(sa!=da,axis=2); outside=int(np.count_nonzero(changed&~allowed));alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed));target_out=int(np.count_nonzero(target&~allowed))
    guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
    residue=int(np.count_nonzero(full&(np.any(sa!=da,axis=2))&(da[:,:,3]>0)&~guard))
    overlap=0;touch=[]
    for i in range(4):
        for j in range(i+1,4):
            ov=int(np.count_nonzero(tms[i]&tms[j]));near=np.asarray(Image.fromarray((tms[i].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0;npix=int(np.count_nonzero(near&tms[j]));overlap+=ov
            if ov or npix:touch.append([i+1,j+1,ov,npix])
    if outside or alpha_out or target_out or overlap or touch:raise RuntimeError(("QA",outside,alpha_out,target_out,overlap,touch))

    def mi(m):return Image.fromarray((m.astype(np.uint8)*255),"L")
    mi(full).save(out/"1F5_SOURCE_TEXT_MASK.png");mi(allowed).save(out/"1F5_ALLOWED_TEXT_REGION_MASK.png");mi(~allowed).save(out/"1F5_PROTECTED_MASK.png");mi(target).save(out/"1F5_TARGET_TEXT_MASK.png");clean_img.save(out/"1F5_CLEAN_PLATE.png")
    sp=Path("/tmp/b51src.png");fp=Path("/tmp/b51fin.png");src.save(sp);dec.save(fp);v=repo/"tools/localization/validate_clean_plate.py"
    subprocess.run(["python3",str(v),str(sp),str(out/"1F5_CLEAN_PLATE.png"),str(out/"1F5_SOURCE_TEXT_MASK.png"),"--report",str(out/"B51_CLEAN_VALIDATION.json")],check=True)
    subprocess.run(["python3",str(v),str(sp),str(fp),str(out/"1F5_ALLOWED_TEXT_REGION_MASK.png"),"--protected-mask",str(out/"1F5_PROTECTED_MASK.png"),"--report",str(out/"B51_FINAL_VALIDATION.json")],check=True)

    def comp(im,bg=(64,64,64,255)):z=Image.new("RGBA",im.size,bg);z.alpha_composite(im);return z.convert("RGB")
    def card(lbl,im,bg=(64,64,64,255)):z=comp(im,bg);c=Image.new("RGB",(W,H+25),"white");c.paste(z,(0,25));ImageDraw.Draw(c).text((5,4),lbl,fill="black");return c
    cs=[card("SOURCE_READABLE",src),card("CLEAN",clean_img),card("FINAL",dec),card("FINAL_WHITE",dec,(255,255,255,255))]
    sh=Image.new("RGB",(W*2,(H+25)*2),"white");sh.paste(cs[0],(0,0));sh.paste(cs[1],(W,0));sh.paste(cs[2],(0,H+25));sh.paste(cs[3],(W,H+25));sh.save(out/"B51_1F5_COMPARE.jpg",quality=96)
    contacts=[];sr=comp(src);cl=comp(clean_img);fi=comp(dec)
    for r in rows:
        x0,y0,x1,y1=r["original_bbox"];p=10;cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p));ims=[z.crop(cr) for z in (sr,cl,fi)];ims=[z.resize((z.width*3,z.height*3),Image.Resampling.NEAREST) for z in ims]
        c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+25),"white");xx=0
        for z in ims:c.paste(z,(xx,25));xx+=z.width+6
        ImageDraw.Draw(c).text((4,4),f'{r["n"]} {r["source"]} -> {r["korean"]}',fill="black");contacts.append(c)
    rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4*(len(contacts)-1)),"white");yy=0
    for c in contacts:rs.paste(c,(0,yy));yy+=c.height+4
    rs.save(out/"B51_1F5_ROW_CONTACT_3X.jpg",quality=96)
    rr=Image.new("RGB",(W,(H+25)*2),"white");rr.paste(card("SOURCE_RAW_MIRROR_Y",raw_src),(0,0));rr.paste(card("FINAL_RAW_MIRROR_Y",raw_dec),(0,H+25));rr.save(out/"B51_1F5_RAW_COMPARE.jpg",quality=96)

    report={"schema_version":1,"role":"B","run":RUN,"queue_index":INDEX,"asset":ASSET,"readiness_tier":"ONE_STAGE_TO_RENDER_COMPLETED_SAME_INVOCATION",
      "source_sha256":source_sha,"historical_discovery_sha256":hist_sha,"historical_discovery_only":True,"historical_localized_pixels_reused":False,
      "candidate_sha256":csha,"candidate_path":str(cand.relative_to(repo)),"structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
      "segments_total":4,"rows":rows,"shared_typography":{"font_size":fs,"fill_rgba":fill,"status":"PASS_SHARED_SOURCE_STYLE"},
      "containment":{"elements_total":4,"elements_pass":4,"outside":outside,"alpha_outside":alpha_out,"target_out":target_out,"source_residue_metric":residue,"overlap":overlap,"touch_pairs":touch,"status":"PASS"},
      "policy":{"colored_menu_panels_preserved":"YES","song_titles_credits":"not_targeted","stage_names":"not_applicable","multi_line":"not_applicable"},
      "manual_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED","status":"B_PRODUCTION51_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
    (out/"B51_1F5_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    summary={"run":RUN,"asset":"1F5FE6E9","index":INDEX,"candidate_sha256":csha,"bbox_size_pass":"4/4","outside":outside,"alpha_outside":alpha_out,"overlap":overlap,"touch_pairs":len(touch),"worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{RUN}/B51_1F5_REPORT.json"}
    (wr/"B51_1F5FE6E9.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n");print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        repo=Path.cwd();out=repo/"localization/graphics/role_B"/RUN;out.mkdir(parents=True,exist_ok=True);wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
        fail={"run":RUN,"asset":"1F5FE6E9","index":INDEX,"status":"FAIL_CLOSED_DIAGNOSTIC","exception":repr(e),"traceback":traceback.format_exc(),"RUNTIME_VALIDATION":"UNTESTED"}
        (out/"B51_FAIL_CLOSED.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n");(wr/"B51_1F5FE6E9_FAIL.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n");print(json.dumps(fail,ensure_ascii=False),flush=True)
