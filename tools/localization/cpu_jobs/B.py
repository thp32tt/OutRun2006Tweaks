#!/usr/bin/env python3
import hashlib,json,os,struct,subprocess,traceback,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageFilter
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

RUN="20261005-B-PRODUCTION48"
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"
INDEX=232
LABELS=[("JOIN GAME","게임 참가"),("CREATE GAME","게임 만들기")]

def main():
    repo=Path.cwd(); out=repo/"localization/graphics/role_B"/RUN
    out.mkdir(parents=True,exist_ok=True)
    wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
    srczip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
    histzip=repo/"localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip"
    cand=repo/"localization/graphics/hd_candidates"/ASSET; cand.parent.mkdir(parents=True,exist_ok=True)
    source_sha="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0"
    hist_sha="46d652b457b6316bd51d2d9f77113318a3397576793346b466c8dc8ffdd92aa5"
    def sha(b): return hashlib.sha256(b).hexdigest()
    def meta(b):
        if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
        h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; m=struct.unpack_from("<I",b,28)[0]
        if len(b)!=128+w*h*4: raise RuntimeError(("unexpected RGBA32",w,h,m,len(b)))
        return w,h,m
    with zipfile.ZipFile(srczip) as z: sb=z.read(ASSET)
    with zipfile.ZipFile(histzip) as z: hb=z.read(ASSET)
    if sha(sb)!=source_sha or sha(hb)!=hist_sha: raise RuntimeError(("hash mismatch",sha(sb),sha(hb)))
    W,H,mips=meta(sb)
    if (W,H)!=(2048,1024) or sb[:128]!=hb[:128]: raise RuntimeError(("source structure",W,H,mips))
    # Front-end sumo atlas family uses mirror-Y raw storage; preserve exact source transform.
    src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
    hist_raw=Image.frombytes("RGBA",(W,H),hb[128:],"raw","RGBA")
    src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    hist=hist_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    sa=np.asarray(src,dtype=np.uint8); ha=np.asarray(hist,dtype=np.uint8)
    diff=np.any(sa!=ha,axis=2)&((sa[:,:,3]>0)|(ha[:,:,3]>0))
    src_alpha=sa[:,:,3]>0

    def groups(vals,gap=3):
        vals=[int(v) for v in vals]
        if not vals:return []
        out=[]; g=[vals[0]]
        for v in vals[1:]:
            if v-g[-1]>gap:out.append(g);g=[v]
            else:g.append(v)
        out.append(g);return out
    def discover(k):
        d=np.asarray(Image.fromarray((diff.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(k)))>0
        boxes=[]
        for rg in groups(np.flatnonzero(np.any(d,axis=1)),3):
            y0,y1=rg[0],rg[-1]+1
            for cg in groups(np.flatnonzero(np.any(d[y0:y1],axis=0)),3):
                x0,x1=cg[0],cg[-1]+1; core=int(np.count_nonzero(diff[y0:y1,x0:x1]))
                if core>=30 and x1-x0>=12 and y1-y0>=8:boxes.append([x0,y0,x1,y1,core])
        boxes.sort(key=lambda b:(b[1],b[0]));return boxes
    raw=discover(7)
    # Merge glyph fragments only inside a common row.
    bands=[]
    for b in raw:
        hit=None
        for band in bands:
            a=band[0]; ov=max(0,min(a[3],b[3])-max(a[1],b[1])); mh=min(a[3]-a[1],b[3]-b[1])
            if mh>0 and ov/mh>=.7: hit=band;break
        if hit is None:bands.append([b])
        else:hit.append(b)
    anchors=[]
    for band in bands:
        band=sorted(band,key=lambda b:b[0]); cur=band[0][:]
        for b in band[1:]:
            gap=b[0]-cur[2]
            if 0<=gap<=140:cur=[min(cur[0],b[0]),min(cur[1],b[1]),max(cur[2],b[2]),max(cur[3],b[3]),cur[4]+b[4]]
            else:anchors.append(cur);cur=b[:]
        anchors.append(cur)
    anchors.sort(key=lambda b:(b[1],b[0]))
    if len(anchors)!=2:
        (out/"B_PRODUCTION48_DISCOVERY_FAIL.json").write_text(json.dumps({"raw":raw,"bands":bands,"anchors":anchors},indent=2)+"\n")
        raise RuntimeError(("expected 2 target rows",len(anchors)))

    # Hard y-cell split at midpoint, then exact source effect components intersecting historical diff seed.
    split=(anchors[0][3]+anchors[1][1])//2
    ycells=[(0,split),(split,H)]
    rows=[]; sms=[]; full=np.zeros((H,W),bool); structure=np.ones((3,3),np.uint8)
    for i,(a,(en,ko),(cy0,cy1)) in enumerate(zip(anchors,LABELS,ycells),1):
        pad=36; x0=max(0,a[0]-pad);x1=min(W,a[2]+pad);y0=max(cy0,a[1]-pad);y1=min(cy1,a[3]+pad)
        la=src_alpha[y0:y1,x0:x1]; seed=diff[y0:y1,x0:x1]
        near=np.asarray(Image.fromarray((seed.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(11)))>0
        lab,_=ndimage.label(la,structure=structure); ids=np.unique(lab[near&la]);ids=ids[ids!=0]
        if not len(ids):raise RuntimeError(("no source components",i))
        sm0=np.isin(lab,ids); yy,xx=np.nonzero(sm0)
        bb=[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1]
        dens=float(np.count_nonzero(sm0)/max(1,(bb[2]-bb[0])*(bb[3]-bb[1])))
        if dens>.62 or bb[2]-bb[0]>a[2]-a[0]+140 or bb[3]-bb[1]>a[3]-a[1]+100:
            raise RuntimeError(("source scope ambiguous",i,a,bb,dens))
        sm=np.zeros((H,W),bool);sm[y0:y1,x0:x1]=sm0;sms.append(sm);full|=sm
        rows.append({"n":i,"source":en,"korean":ko,"discovery_anchor":a[:4],"measurement_cell":[x0,y0,x1,y1],
                     "original_bbox":bb,"source_effect_pixels":int(np.count_nonzero(sm)),"source_mask_density":dens})
    if np.any(sms[0]&sms[1]):raise RuntimeError("source masks overlap")

    clean_a=sa.copy();clean_a[full,3]=0
    if np.any(clean_a[:,:,:3]!=sa[:,:,:3]):raise RuntimeError("clean RGB changed")
    clean=Image.fromarray(clean_a,"RGBA")
    p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    if not p or not Path(p).exists():
        subprocess.run(["sudo","apt-get","update","-qq"],check=True);subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        p=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
    FONT=p
    def palette(m):
        px=sa[m];px=px[px[:,3]>4]
        lum=.2126*px[:,0]+.7152*px[:,1]+.0722*px[:,2]
        hi=lum>=np.percentile(lum,67);lo=lum<=np.percentile(lum,25)
        fill=tuple(int(v) for v in np.median(px[hi],axis=0)) if np.any(hi) else (255,255,255,255)
        outline=tuple(int(v) for v in np.median(px[lo],axis=0)) if np.any(lo) else fill
        return fill,outline
    def render(row,m):
        x0,y0,x1,y1=row["original_bbox"];aw=x1-x0;ah=y1-y0;fill,outline=palette(m);d=ImageDraw.Draw(Image.new("L",(8,8),0))
        for fs in range(min(220,max(16,int(ah*.93))),8,-1):
            sw=max(1,round(fs*.05));f=ImageFont.truetype(FONT,fs);tb=d.textbbox((0,0),row["korean"],font=f,stroke_width=sw);pad=sw+4
            sz=(tb[2]-tb[0]+2*pad,tb[3]-tb[1]+2*pad);st=Image.new("L",sz,0);fi=Image.new("L",sz,0);pos=(pad-tb[0],pad-tb[1])
            ImageDraw.Draw(st).text(pos,row["korean"],font=f,fill=255,stroke_width=sw,stroke_fill=255);ImageDraw.Draw(fi).text(pos,row["korean"],font=f,fill=255)
            tile=Image.new("RGBA",sz,(0,0,0,0));tile.paste(outline,(0,0),st);tile.paste(fill,(0,0),fi);ab=tile.getchannel("A").getbbox()
            if not ab:continue
            tile=tile.crop(ab)
            if tile.width>aw-2 or tile.height>ah-2:continue
            layer=Image.new("RGBA",(W,H),(0,0,0,0));layer.alpha_composite(tile,(x0+(aw-tile.width)//2,y0+(ah-tile.height)//2));lb=list(layer.getchannel("A").getbbox())
            if lb[0]<=x0 or lb[1]<=y0 or lb[2]>=x1 or lb[3]>=y1:continue
            return layer,fs,sw,lb,fill,outline
        raise RuntimeError(("cannot fit",row))
    final=clean.copy();tms=[];target=np.zeros((H,W),bool)
    for row,sm in zip(rows,sms):
        layer,fs,sw,lb,fill,outline=render(row,sm);lm=np.asarray(layer.getchannel("A"))>0
        for old in tms:
            if np.any(lm&old):raise RuntimeError("localized overlap")
        tms.append(lm);target|=lm;final.alpha_composite(layer)
        ob=row["original_bbox"];row.update({"localized_bbox":lb,"source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
          "localized_width":lb[2]-lb[0],"localized_height":lb[3]-lb[1],"delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],
          "delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],"containment":"PASS","size_ceiling":"PASS",
          "font_size":fs,"stroke_width":sw,"fill":fill,"outline":outline,"rework_status":"NEW_EXACT_SOURCE_RGBA_NATIVE_RENDER"})
    raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM);payload=sb[:128]+raw_final.tobytes("raw","RGBA");cand.write_bytes(payload);cand_sha=sha(payload)
    dec_raw=Image.frombytes("RGBA",(W,H),payload[128:],"raw","RGBA");dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if payload[:128]!=sb[:128] or ImageChops.difference(dec,final).getbbox():raise RuntimeError("roundtrip/header")
    da=np.asarray(dec,dtype=np.uint8);allowed=np.zeros((H,W),bool)
    for r in rows:x0,y0,x1,y1=r["original_bbox"];allowed[y0:y1,x0:x1]=True
    changed=np.any(sa!=da,axis=2);outside=int(np.count_nonzero(changed&~allowed));alpha_out=int(np.count_nonzero((sa[:,:,3]!=da[:,:,3])&~allowed))
    guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
    residue=int(np.count_nonzero(full&(da[:,:,3]>0)&~guard));target_out=int(np.count_nonzero(target&~allowed));overlap=int(np.count_nonzero(tms[0]&tms[1]))
    near=np.asarray(Image.fromarray((tms[0].astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    touch=int(np.count_nonzero(near&tms[1]))
    if outside or alpha_out or residue or target_out or overlap or touch:raise RuntimeError(("QA",outside,alpha_out,residue,target_out,overlap,touch))
    def mi(m):return Image.fromarray((m.astype(np.uint8)*255),"L")
    mi(full).save(out/"EBFC709F_SOURCE_TEXT_MASK.png");mi(allowed).save(out/"EBFC709F_ALLOWED_TEXT_REGION_MASK.png");mi(~allowed).save(out/"EBFC709F_PROTECTED_MASK.png");mi(target).save(out/"EBFC709F_TARGET_TEXT_MASK.png");clean.save(out/"EBFC709F_CLEAN_PLATE.png")
    sp=Path("/tmp/ebfc_src.png");fp=Path("/tmp/ebfc_final.png");src.save(sp);dec.save(fp);v=repo/"tools/localization/validate_clean_plate.py"
    subprocess.run(["python3",str(v),str(sp),str(out/"EBFC709F_CLEAN_PLATE.png"),str(out/"EBFC709F_SOURCE_TEXT_MASK.png"),"--report",str(out/"B_PRODUCTION48_CLEAN_VALIDATION.json")],check=True)
    subprocess.run(["python3",str(v),str(sp),str(fp),str(out/"EBFC709F_ALLOWED_TEXT_REGION_MASK.png"),"--protected-mask",str(out/"EBFC709F_PROTECTED_MASK.png"),"--report",str(out/"B_PRODUCTION48_FINAL_VALIDATION.json")],check=True)
    def comp(im,bg=(64,64,64,255)):
        z=Image.new("RGBA",im.size,bg);z.alpha_composite(im);return z.convert("RGB")
    def card(lbl,im,bg=(64,64,64,255)):
        z=comp(im,bg);c=Image.new("RGB",(W,H+25),"white");c.paste(z,(0,25));ImageDraw.Draw(c).text((5,4),lbl,fill="black");return c
    cs=[card("SOURCE_READABLE",src),card("CLEAN",clean),card("FINAL",dec),card("FINAL_WHITE",dec,(255,255,255,255))]
    sh=Image.new("RGB",(W*2,(H+25)*2),"white");sh.paste(cs[0],(0,0));sh.paste(cs[1],(W,0));sh.paste(cs[2],(0,H+25));sh.paste(cs[3],(W,H+25));sh.thumbnail((1900,1500),Image.Resampling.LANCZOS);sh.save(out/"B_PRODUCTION48_EBFC_COMPARE.jpg",quality=96)
    contacts=[];sr=comp(src);cl=comp(clean);fi=comp(dec)
    for r in rows:
        x0,y0,x1,y1=r["original_bbox"];p=12;cr=(max(0,x0-p),max(0,y0-p),min(W,x1+p),min(H,y1+p));ims=[z.crop(cr) for z in (sr,cl,fi)];ims=[z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST) for z in ims]
        c=Image.new("RGB",(sum(z.width for z in ims)+12,max(z.height for z in ims)+25),"white");xx=0
        for z in ims:c.paste(z,(xx,25));xx+=z.width+6
        ImageDraw.Draw(c).text((4,4),f'{r["n"]} {r["source"]} -> {r["korean"]}',fill="black");contacts.append(c)
    rs=Image.new("RGB",(max(c.width for c in contacts),sum(c.height for c in contacts)+4),"white");yy=0
    for c in contacts:rs.paste(c,(0,yy));yy+=c.height+4
    rs.save(out/"B_PRODUCTION48_EBFC_ROW_CONTACT_2X.jpg",quality=96)
    rr=Image.new("RGB",(W,(H+25)*2),"white");rr.paste(card("SOURCE_RAW_MIRROR_Y",src_raw),(0,0));rr.paste(card("FINAL_RAW_MIRROR_Y",dec_raw),(0,H+25));rr.thumbnail((1600,1400),Image.Resampling.LANCZOS);rr.save(out/"B_PRODUCTION48_EBFC_RAW_COMPARE.jpg",quality=96)
    report={"schema_version":1,"role":"B","run":RUN,"queue_index":INDEX,"asset":ASSET,"readiness_tier":"RENDER_READY_COMPLETED_SAME_INVOCATION",
      "source_sha256":source_sha,"historical_discovery_sha256":hist_sha,"historical_discovery_only":True,"historical_localized_pixels_reused":False,
      "candidate_sha256":cand_sha,"candidate_path":str(cand.relative_to(repo)),"structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
      "rows":rows,"containment":{"elements_total":2,"elements_pass":2,"outside":outside,"alpha_outside":alpha_out,"target_out":target_out,"source_residue":residue,"overlap":overlap,"touch":touch,"status":"PASS"},
      "clean_plate":{"rgb_changed_pixels":0,"source_effect_alpha_remaining":0,"status":"PASS"},"manual_visual_qa":"PENDING_CONTROLLER_SELF_QA","RUNTIME_VALIDATION":"UNTESTED","status":"B_PRODUCTION48_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"}
    (out/"B_PRODUCTION48_EBFC_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    summary={"run":RUN,"asset":"EBFC709F","index":INDEX,"candidate_sha256":cand_sha,"bbox_size_pass":"2/2","outside":outside,"alpha_outside":alpha_out,"source_residue":residue,"overlap":overlap,"touch":touch,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{RUN}/B_PRODUCTION48_EBFC_REPORT.json"}
    (wr/"B_PRODUCTION48_EBFC709F.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n");print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        repo=Path.cwd();out=repo/"localization/graphics/role_B"/RUN;out.mkdir(parents=True,exist_ok=True);wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
        fail={"run":RUN,"asset":"EBFC709F","index":INDEX,"status":"FAIL_CLOSED_DIAGNOSTIC","exception":repr(e),"traceback":traceback.format_exc(),"RUNTIME_VALIDATION":"UNTESTED"}
        (out/"B_PRODUCTION48_FAIL_CLOSED.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n");(wr/"B_PRODUCTION48_EBFC709F_FAIL.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n");print(json.dumps(fail,ensure_ascii=False),flush=True)
