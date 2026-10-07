from __future__ import annotations
import csv, hashlib, json, struct, subprocess, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

R=Path(__file__).resolve().parents[2] if 'tools/localization' in str(Path(__file__)) else Path.cwd()
REL=Path("textures/load/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds")
DDS=R/"localization/graphics/hd_candidates"/REL
REP=R/"localization/graphics/role_A/20261006-A-PRODUCTION76-ACF/A76_ACF61D7C_REPORT.json"
OUT=R/"localization/graphics/role_A/20261007-A167-USER-INGAME-Q205-NATIVE"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds"
SRC_SHA="58a75fe75b5672169dcc2ed1f9993d462d80b700d4e12dad453b70f2ab701a5f"
OLD_SHA="2bbb9d19a833fb6c9ade243eb70132ef5ce46150d1fa1cb9423ff4e5101b770c"
NOW=datetime.now(timezone(timedelta(hours=9))).replace(microsecond=0).isoformat()
TARGET={"options":"옵션","rankings":"랭킹","out_run_1p":"1인 플레이!","view_rankings":"싱글·멀티플레이 랭킹 보기","enjoy_original":"오리지널","adjust_settings":"게임 설정 변경"}
REVISE={"Adjust your Game settings":"게임 설정 변경","View single player and multiplayer rankings":"싱글·멀티플레이 랭킹 보기","Enjoy the original OutRun2SP":"오리지널 OutRun2SP","OutRun for 1 player!":"OutRun 1인 플레이!"}

def H(b): return hashlib.sha256(b).hexdigest()
def dec(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]; bits=struct.unpack_from("<I",b,88)[0]
    if bits!=32 or len(b)-128!=w*h*4: raise RuntimeError(("bad_rgba_dds",w,h,bits,len(b)-128))
    raw=Image.frombytes("RGBA",(w,h),b[128:])
    return b[:128],raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(w,h)
def fc(pat):
    s=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip(); p,i=s.rsplit("|",1)
    if not Path(p).exists(): raise RuntimeError("font missing: "+pat)
    return p,int(i or 0)
def font(path,size,index):
    try:return ImageFont.truetype(path,size=size,index=index)
    except TypeError:return ImageFont.truetype(path,size=size)
def fit(text,path,index,mw,mh,ratio):
    cap=max(8,int(mh*ratio)); best=None; tmp=Image.new("L",(4096,1024)); d=ImageDraw.Draw(tmp)
    for sz in range(12,max(80,cap*3)):
        f=font(path,sz,index); bb=d.textbbox((0,0),text,font=f); w=bb[2]-bb[0]; h=bb[3]-bb[1]
        if w<=mw and h<=cap: best=(f,bb,sz)
        elif best and h>cap: break
    if not best: raise RuntimeError("fit "+text)
    f,bb,sz=best; w=bb[2]-bb[0]; h=bb[3]-bb[1]
    im=Image.new("RGBA",(w+8,h+8),(0,0,0,0)); ImageDraw.Draw(im).text((4-bb[0],4-bb[1]),text,font=f,fill=(255,255,255,255))
    return im.crop(im.getchannel("A").getbbox()),sz

def patch_runtime():
    p=R/"src/overlay/overlay.cpp"; s=p.read_text()
    old='\t\t\tconst std::filesystem::path candidates[] = {\n\t\t\t\tfontsDir / "malgun.ttf",\n\t\t\t\tfontsDir / "malgunsl.ttf",\n\t\t\t\tfontsDir / "gulim.ttc",'
    new='\t\t\tconst std::filesystem::path candidates[] = {\n\t\t\t\t// 2026-10-07 actual-game review: prefer lighter Korean runtime text.\n\t\t\t\tfontsDir / "malgunsl.ttf",\n\t\t\t\tfontsDir / "malgun.ttf",\n\t\t\t\tfontsDir / "gulim.ttc",'
    if old in s: p.write_text(s.replace(old,new,1))
    elif "prefer lighter Korean runtime text" not in s: raise RuntimeError("overlay drift")
    p=R/"src/hooks_localization.cpp"; s=p.read_text()
    old='''    static bool NeedsCompactReadabilityStroke(const DrawCommand& cmd)
    {
        const float cellHeight =
            static_cast<float>(cmd.cellHeight == 0 ? 16 : std::abs(cmd.cellHeight));
        const float logicalFontHeight =
            cellHeight * (std::max)(0.05f, std::fabs(cmd.scaleY));

        // User in-game regressions IGR-006/007 show the compact runtime path
        // losing the source HUD/bubble weight. Keep larger menu/body copy
        // unchanged and reinforce only the small stock cells.
        return cmd.textId < TextEntryCount && logicalFontHeight <= 24.0f;
    }'''
    new='''    static bool NeedsCompactReadabilityStroke(const DrawCommand& cmd)
    {
        const float cellHeight =
            static_cast<float>(cmd.cellHeight == 0 ? 16 : std::abs(cmd.cellHeight));
        const float logicalFontHeight =
            cellHeight * (std::max)(0.05f, std::fabs(cmd.scaleY));

        // 2026-10-07 actual-game review: the previous heavy keyline reduced
        // legibility on dark Korean dialog/menu text. Dark text needs no stroke.
        const uint8_t r = static_cast<uint8_t>((cmd.color >> 16) & 0xFF);
        const uint8_t g = static_cast<uint8_t>((cmd.color >> 8) & 0xFF);
        const uint8_t b = static_cast<uint8_t>(cmd.color & 0xFF);
        const uint16_t luma =
            static_cast<uint16_t>((54u * r + 183u * g + 19u * b) >> 8);
        if (luma < 96)
            return false;
        return cmd.textId < TextEntryCount && logicalFontHeight <= 24.0f;
    }'''
    if old in s:s=s.replace(old,new,1)
    elif "previous heavy keyline reduced" not in s: raise RuntimeError("hook predicate drift")
    old='''                const float stroke = std::clamp(fontSize * 0.055f, 1.0f, 2.0f);
                const ImVec4 clip(x, y, x + size.x, y + size.y);
                const ImU32 outline = CompactOutlineColor(cmd.color);
                const ImVec2 offsets[] = {
                    ImVec2(-stroke, 0.0f),
                    ImVec2(stroke, 0.0f),
                    ImVec2(0.0f, -stroke),
                    ImVec2(0.0f, stroke),
                    ImVec2(-stroke, -stroke),
                    ImVec2(stroke, -stroke),
                    ImVec2(-stroke, stroke),
                    ImVec2(stroke, stroke)
                };'''
    new='''                const float stroke = std::clamp(fontSize * 0.018f, 0.45f, 0.85f);
                const ImVec4 clip(x, y, x + size.x, y + size.y);
                const ImU32 outline = CompactOutlineColor(cmd.color);
                const ImVec2 offsets[] = {
                    ImVec2(-stroke, 0.0f),
                    ImVec2(stroke, 0.0f),
                    ImVec2(0.0f, -stroke),
                    ImVec2(0.0f, stroke)
                };'''
    if old in s:s=s.replace(old,new,1)
    elif "fontSize * 0.018f" not in s: raise RuntimeError("hook stroke drift")
    p.write_text(s)

def rework_q205():
    OUT.mkdir(parents=True,exist_ok=True); rows={x["key"]:x for x in json.loads(REP.read_text())["rows"]}
    oldb=DDS.read_bytes()
    if H(oldb)!=OLD_SHA: raise RuntimeError("q205 drift "+H(oldb))
    hdr,_,old,size=dec(oldb); srcb=urllib.request.urlopen(SRC_URL,timeout=90).read()
    if H(srcb)!=SRC_SHA: raise RuntimeError("source SHA")
    sh,_,src,ss=dec(srcb)
    if hdr!=sh or size!=ss: raise RuntimeError("source structure")
    sans,si=fc("Noto Sans CJK KR:style=Medium"); serif,sei=fc("Noto Serif CJK KR:style=Bold")
    final=old.copy(); result=[]
    for k in TARGET: final.paste((0,0,0,0),tuple(map(int,rows[k]["localized_bbox"])))
    for k,text in TARGET.items():
        r=rows[k]; o=list(map(int,r["original_bbox"])); x0,y0,x1,y1=o; shh=y1-y0; token=r.get("preserved_inline_token_bbox"); side=r.get("token_side"); gap=16
        if k in ("options","rankings"): fp,fi,fill,ratio=serif,sei,(186,0,0,255),.86
        else: fp,fi,fill,ratio=sans,si,(63,71,74,255),.78
        ax0=x0+4; ax1=x1-4
        if token:
            t=list(map(int,token))
            if side=="left": ax0=t[2]+gap
            elif side=="right": ax1=t[0]-gap
            else: raise RuntimeError("token side")
        layer,fs=fit(text,fp,fi,ax1-ax0,shh-8,ratio); alpha=layer.getchannel("A"); col=Image.new("RGBA",layer.size,fill); col.putalpha(alpha); layer=col
        lw,lh=layer.size; x=ax1-lw if token and side=="right" else ax0; y=min(y0+max(4,(shh-lh)//2),y1-4-lh); b=[x,y,x+lw,y+lh]
        if not (x>=x0 and y>=y0 and x+lw<=x1 and y+lh<=y1): raise RuntimeError("bbox "+k)
        if token and not (b[2]<=t[0]-gap or b[0]>=t[2]+gap): raise RuntimeError("token gap "+k)
        final.alpha_composite(layer,(x,y)); result.append({"key":k,"text":text,"font_file":Path(fp).name,"font_size_native_px":fs,"pixel_scale":1,"original_bbox":o,"prior_localized_bbox":list(map(int,r["localized_bbox"])),"localized_bbox":b,"protected_token":r.get("preserved_inline_token"),"token_bbox":token,"token_gap_px":gap if token else None})
    mask=Image.new("L",final.size,0); md=ImageDraw.Draw(mask)
    for k in TARGET: md.rectangle(tuple(map(int,rows[k]["original_bbox"])),fill=255)
    diff=ImageChops.difference(old,final); changed=diff.convert("RGB").convert("L").point(lambda v:255 if v else 0)
    if ImageChops.multiply(changed,ImageChops.invert(mask)).getbbox(): raise RuntimeError("blast radius")
    for k in TARGET:
        t=rows[k].get("preserved_inline_token_bbox")
        if t and ImageChops.difference(old.crop(tuple(t)),final.crop(tuple(t))).getbbox(): raise RuntimeError("token changed "+k)
    newb=hdr+final.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes(); _,_,persist,_=dec(newb)
    if ImageChops.difference(persist,final).getbbox(): raise RuntimeError("persist")
    DDS.write_bytes(newb); ns=H(newb)
    cards=[]
    for rr in result:
        x0,y0,x1,y1=rr["original_bbox"]; rect=(max(0,x0-24),max(0,y0-18),min(final.width,x1+24),min(final.height,y1+18)); ims=[src.crop(rect),old.crop(rect),final.crop(rect)]; labs=["ENGLISH SOURCE","C217 PRIOR","A167 NATIVE"]
        card=Image.new("RGB",(sum(i.width for i in ims),max(i.height for i in ims)+30),(24,24,24)); d=ImageDraw.Draw(card); dx=0
        for im,lab in zip(ims,labs):
            bg=Image.new("RGBA",im.size,(235,235,235,255)); bg.alpha_composite(im); card.paste(bg.convert("RGB"),(dx,30)); d.text((dx+4,6),lab,fill="white"); dx+=im.width
        cards.append(card)
    sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)),(15,15,15)); y=0
    for c in cards: sheet.paste(c,(0,y)); y+=c.height
    sheet.save(OUT/"A167_Q205_SOURCE_PRIOR_FINAL.jpg","JPEG",quality=95,subsampling=0)
    ev={"run":"A167","timestamp_kst":NOW,"queue_index":205,"asset":REL.as_posix(),"source_sha256":SRC_SHA,"prior_candidate_sha256":OLD_SHA,"candidate_sha256":ns,"dimensions":list(size),"format":"RGBA32","raw_orientation":"mirror_y","native_resolution_render":True,"pixel_scale":1,"changed_pixels_outside_target_bboxes":0,"protected_inline_tokens_pixel_exact":True,"rows":result,"decision":"A167_SELF_QA_PASS_PENDING_FRESH_C_C3_PRE_INGAME_AND_INGAME_RETEST","runtime_validation":"UNTESTED"}
    (OUT/"A167_Q205_REPORT.json").write_text(json.dumps(ev,ensure_ascii=False,indent=2)+"\n")
    return ns

def jlines(path,fn):
    out=[]
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip(): out.append(json.dumps(fn(json.loads(line)),ensure_ascii=False,separators=(",",":")))
    path.write_text("\n".join(out)+"\n")

def state(ns):
    q=R/"localization/graphics/asset_queue.csv"
    with q.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f)); fields=list(rows[0])
    for x in rows:
        if x["index"]=="205": x["artwork_status"]="a167_user_ingame_native_rework_self_qa_pass_pending_fresh_c"; x["notes"]+=" USER_INGAME_20261007: screenshots 159-163 override C217; lowres x4 raster was a visual false-negative. A167 native 4096x2048 AA candidate "+ns+"; protected OutRun/OutRun2SP tokens exact with positive spacing. Fresh C+C3+PRE_INGAME+NEW actual-game retest required."
    with q.open("w",encoding="utf-8-sig",newline="") as f: w=csv.DictWriter(f,fieldnames=fields,lineterminator="\r\n"); w.writeheader(); w.writerows(rows)
    def tfn(o):
        if o.get("index")==205:
            for s in o["segments"]:
                if s["source"] in REVISE:s["korean"]=REVISE[s["source"]]
            o["notes"]="visual transcription pass 10; protected tokens preserved; 2026-10-07 actual-game wording/spacing revision"
        return o
    jlines(R/"localization/graphics/transcriptions.jsonl",tfn)
    def pfn(o):
        if o.get("index")==205:
            for s in o["segments"]:
                if s["source"] in REVISE:s["korean"]=REVISE[s["source"]]
            o.update({"layout_status":"a167_user_ingame_native_render_positive_margin_pass","render_status":"a167_native_self_qa_pass_pending_fresh_c_c3","dds_status":"candidate_pending_fresh_c_c3_user_ingame_retest","ingame_status":"pending_new_user_retest","candidate_sha256":ns,"a167_report":"localization/graphics/role_A/20261007-A167-USER-INGAME-Q205-NATIVE/A167_Q205_REPORT.json"}); o["notes"]+=" A167 actual-game override: six visible main-menu rows rerendered directly at native 4096x2048 pixel_scale=1; no low-res upscale; fresh C+C3+new game retest pending."
        return o
    jlines(R/"localization/graphics/artwork_plan.jsonl",pfn)
    b=R/"localization/graphics/INGAME_REWORK_BACKLOG.csv"
    with b.open(encoding="utf-8-sig",newline="") as f: br=list(csv.DictReader(f)); bf=list(br[0])
    ids={x["id"] for x in br}
    if "IGR-020" not in ids: br.append(dict(zip(bf,["IGR-020","스크린샷(159)-스크린샷(163).png","MAIN_MENU_Q205","P0","GRAPHICS","A","205",REL.as_posix(),"EXACT_Q205_ACF61D7C","LOW_RES_FONT|UPSCALED_BITMAP|PIXELATED_HANGUL|DIRTY_RASTER|MAIN_MENU_STYLE_MISMATCH|AWKWARD_TOKEN_SPACING","Native 4096x2048 rerender; preserve product tokens; fresh C+C3 and new game retest.","A167_STATIC_PASS_PENDING_FRESH_C_C3_INGAME_RETEST","FRESH_C + EXACT_SHA_C3 + PRE_INGAME_USER_REVIEW + NEW_INGAME_RETEST"])))
    if "IGR-021" not in ids: br.append(dict(zip(bf,["IGR-021","스크린샷(164).png","INGAME_CONFIRM_DIALOG_RUNTIME_TEXT","P0","RUNTIME_TEXT","A","","src/hooks_localization.cpp|src/overlay/overlay.cpp","EXACT_K4_RUNTIME_OVERLAY","OVERWEIGHT_FONT|EXCESSIVE_STROKE|READABILITY_DEGRADED","Semilight first; dark dialog/menu gets no synthetic stroke; bright compact stroke reduced.","A167_SOURCE_FIX_PENDING_WIN32_BUILD_AND_INGAME_RETEST","CURRENT_WIN32_RELEASE_BUILD_PASS + NEW_INGAME_RETEST"])))
    with b.open("w",encoding="utf-8-sig",newline="") as f: w=csv.DictWriter(f,fieldnames=bf,lineterminator="\r\n"); w.writeheader(); w.writerows(br)
    qual=R/"docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md"; s=qual.read_text()
    if "### Native-resolution final UI raster gate" not in s: qual.write_text(s+"\n\n### Native-resolution final UI raster gate\n- Final Korean menu/UI text may not be produced by enlarging a low-resolution bitmap. Integer/nearest-neighbor upscale is a hard FAIL even when bbox checks pass. Rasterize at native DDS resolution or true supersampling with high-quality downsampling.\n- Where crisp English and Korean share a screen, practical 1x edge smoothness and stroke consistency are mandatory. Visibly blockier Korean is REWORK_REQUIRED.\n- Protected inline OutRun/OutRun2SP tokens require positive visual spacing from Korean.\n")
    k=R/"docs/KOREAN_RUNTIME_K4_OVERLAY_TEST.md"; s=k.read_text()
    if "## 2026-10-07 actual-game readability correction" not in s: k.write_text(s+"\n\n## 2026-10-07 actual-game readability correction\n- Prefer malgunsl.ttf before malgun.ttf for Korean runtime copy.\n- Dark Korean dialog/menu text no longer receives the synthetic compact keyline.\n- Bright compact HUD text retains only a light four-direction cardinal keyline (0.45-0.85 screen px), replacing the old eight-direction 1-2px reinforcement.\n- Current Win32 Release and NEW actual-game retest are mandatory before closure.\n")
    entry="\n\n## "+NOW+" — A167 actual-game readability rework\n- q205 ACF61D7C: screenshots 159-163 override C217. Six visible main-menu rows rerendered directly at native 4096x2048, candidate "+ns+"; no low-res upscale; protected OutRun/OutRun2SP tokens exact with positive spacing. Fresh C/C3/PRE_INGAME/new game retest pending.\n- Runtime screenshot 164: Semilight-first Korean overlay; dark dialog/menu copy no artificial compact keyline; bright compact reinforcement reduced. Current Win32 Release validation required.\n- VR/FFB/DX11/DXVK untouched.\n"
    for p in (R/"localization/WORKLOG.md",R/"localization/progress/STATUS.md"): p.write_text(p.read_text()+entry)
    p=R/"localization/progress/progress.json"; o=json.loads(p.read_text()); o["updated_at_kst"]=NOW; o["user_ingame_review_20261007"]={"q205":{"candidate_sha256":ns,"status":"A167_NATIVE_PASS_PENDING_C_C3_INGAME"},"runtime_overlay":{"status":"SOURCE_FIX_PENDING_WIN32_RELEASE_AND_INGAME"}}; p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n")
    p=R/"localization/resume_state.json"; o=json.loads(p.read_text()); o["next_actions"]=["A167 q205 "+ns+" producer PASS: fresh C + exact-SHA C3 + PRE_INGAME + NEW actual-game retest required.","A167 runtime Korean weight fix: current Win32 Release + NEW actual-game retest required."]+o.get("next_actions",[]); o["a167_user_ingame_review_20261007"]={"timestamp_kst":NOW,"q205_candidate_sha256":ns,"runtime_validation":"PENDING_CURRENT_WIN32_RELEASE"}; p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n")

def main():
    patch_runtime(); ns=rework_q205(); state(ns); print(json.dumps({"run":"A167","q205_candidate_sha256":ns,"runtime_source_fix":"APPLIED_PENDING_BUILD"},ensure_ascii=False))
if __name__=="__main__": main()
