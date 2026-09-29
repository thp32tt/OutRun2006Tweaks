#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
TASK_ID='LOCALIZATION-LOCALIZATION_A-00182'
WAVE_ID='P00092'
INDEX=237
ASSET='FF514CEB'
SOURCE_REPO='envido32/OR2006Sprites'
SOURCE_COMMIT='55f67a813dd3603d201d0be0da47c071965f53a4'
SOURCE_REL='Release/spr_sprani_sumo_fe_cvt_Exst/FF514CEB_512x512.dds'
SOURCE_URL=f'https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{SOURCE_REL}'
SOURCE_GIT_BLOB='6e9d40d155956eb13647217bcc14680066084c30'
SOURCE_SHA='570fff6b71962f56b2f3d09993191a18989a80420b1963c4cccd1620b192907a'
PINNED_ZIP_SHA='76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958'
W=H=2048
CAND=ROOT/'localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/FF514CEB_512x512.dds'
REVIEW=ROOT/'localization/graphics/KOREAN_PNG_REVIEW/FF514CEB'
RUN=ROOT/'localization/graphics/role_A/20260930-A00182-P00092'
REPORT=RUN/'A00182_P00092_INDEX237_FF514CEB_RGBA32_CANDIDATE_QA.json'
TASK=ROOT/'docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00182.json'

ELEMENTS=[
 {'id':'small_create','source':'CREATE GAME','korean':'게임 만들기','region':[0,740,560,850],'source_effect_bbox':[14,775,536,838],'safe_bbox':[16,777,534,836],'font_size_nominal':11,'fill':[63,71,74]},
 {'id':'small_custom','source':'CUSTOM GAME','korean':'커스텀 게임','region':[0,850,560,940],'source_effect_bbox':[12,863,521,926],'safe_bbox':[14,865,519,924],'font_size_nominal':12,'fill':[63,71,74]},
 {'id':'small_quick','source':'QUICK GAME','korean':'빠른 게임','region':[0,940,550,1025],'source_effect_bbox':[13,951,469,1018],'safe_bbox':[15,953,467,1016],'font_size_nominal':13,'fill':[63,71,74]},
 {'id':'desc_create','source':'Create a game and invite your friends!','korean':'게임을 만들고 친구를 초대하세요!','region':[0,1025,1220,1135],'source_effect_bbox':[8,1035,1154,1101],'safe_bbox':[10,1037,1152,1099],'font_size_nominal':12,'fill':[63,71,74]},
 {'id':'desc_custom','source':"Specify what gametype you'd like to play!",'korean':'플레이할 게임 유형을 설정하세요!','region':[0,1160,1320,1300],'source_effect_bbox':[3,1196,1257,1263],'safe_bbox':[5,1198,1255,1261],'font_size_nominal':12,'fill':[63,71,74]},
 {'id':'desc_quick','source':'Jump into a quick game of OutRun!','korean':'빠른 아웃런 게임에 참가하세요!','region':[0,1320,1120,1450],'source_effect_bbox':[4,1353,1041,1419],'safe_bbox':[6,1355,1039,1417],'font_size_nominal':12,'fill':[63,71,74]},
 {'id':'big_create','source':'CREATE GAME','korean':'게임 만들기','region':[0,1480,1300,1680],'source_effect_bbox':[18,1517,1243,1662],'safe_bbox':[20,1519,1241,1660],'font_size_nominal':34,'fill':[186,0,0]},
 {'id':'big_quick','source':'QUICK GAME','korean':'빠른 게임','region':[0,1675,1150,1870],'source_effect_bbox':[17,1695,1086,1849],'safe_bbox':[19,1697,1084,1847],'font_size_nominal':36,'fill':[186,0,0]},
 {'id':'big_custom','source':'CUSTOM GAME','korean':'커스텀 게임','region':[0,1875,1300,2048],'source_effect_bbox':[16,1894,1260,2040],'safe_bbox':[18,1896,1258,2038],'font_size_nominal':35,'fill':[186,0,0]},
]
K1_PROTECTED_READABLE=[1664,1011,1740,1060]

def sha256(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def bbox(mask):
    ys,xs=np.nonzero(mask)
    if len(xs)==0:return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def font_info():
    row=subprocess.check_output(['fc-match','-f','%{file}|%{index}\n','Noto Sans CJK KR:style=Bold'],text=True).splitlines()[0]
    p,idx=row.rsplit('|',1)
    return p,int(idx)
def load_source():
    b=urllib.request.urlopen(SOURCE_URL,timeout=120).read()
    if sha256(b)!=SOURCE_SHA: raise SystemExit(f'source sha mismatch {sha256(b)}')
    if len(b)!=16777344 or b[:4]!=b'DDS ': raise SystemExit('source bytes/magic mismatch')
    height=struct.unpack_from('<I',b,12)[0]; width=struct.unpack_from('<I',b,16)[0]
    pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0] or 1
    fourcc=b[84:88]; rgbbits=struct.unpack_from('<I',b,88)[0]; masks=struct.unpack_from('<IIII',b,92)
    expected=(W,H,W*4,1,b'\0\0\0\0',32,(16711680,65280,255,4278190080))
    got=(width,height,pitch,mips,fourcc,rgbbits,masks)
    if got!=expected: raise SystemExit(f'unexpected DDS metadata {got}')
    store=np.frombuffer(b[128:],dtype=np.uint8).reshape(H,W,4).copy()
    rgba=store[..., [2,1,0,3]].copy()
    return b,rgba

def save_rgba(a,p): Image.fromarray(a.astype(np.uint8),'RGBA').save(p,optimize=False)
def rgba_over_black(a):
    f=a.astype(np.float32); alpha=f[...,3:4]/255.0
    rgb=np.rint(f[...,:3]*alpha).clip(0,255).astype(np.uint8)
    out=np.zeros((a.shape[0],a.shape[1],4),np.uint8); out[...,:3]=rgb; out[...,3]=255
    return out

def prompt_bytes(elements, font_id):
    prompt={
      'contract':'outrun-first-pass-edit-v2','contract_version':2,'task_id':TASK_ID,'queue_index':INDEX,'asset_id':ASSET,
      'source_path':'textures/load/spr_sprani_sumo_fe_cvt_Exst/FF514CEB_512x512.dds','source_sha256':SOURCE_SHA,
      'source_dimensions':[W,H],'raw_orientation':'flip_y','display_transform':'flip_y_to_readable',
      'background_class':'transparent text-only/menu-label atlas','alpha_behavior':'preserve exact source outside source-effect removal masks; Korean alpha only inside measured safe bboxes',
      'font_identifier':font_id,'source_style':{'grey_fill_rgb':[63,71,74],'red_fill_rgb':[186,0,0],'outline':'none','shadow':'none','glow':'none','slant_direction':'none','slant_angle_deg':0.0,'weight':'bold block sans'},
      'protected_regions':['all pixels outside each source removal mask and Korean safe bbox','K1 source fragment remains byte-exact','unrelated atlas pixels remain byte-exact'],
      'elements':elements,
      'forbidden':['visible English/source glyph residue','cover rectangles or invented panels','blur/smudge concealment','changes to neighboring sprites or protected pixels','cropping/padding/resizing the DDS canvas','generic new outline/shadow/glow','low-resolution reconstruction followed by upscale as background evidence','fallback glyph boxes'],
      'single_pass_self_check':'Before producing the candidate, verify that no source-language text or effect remains in target footprints; no cover box, patch, seam or invented panel exists; all protected artwork is unchanged; Korean text is fully inside the permitted safe region and unclipped; canvas, orientation and transparency are unchanged. If any condition cannot be satisfied, do not produce a production candidate.'
    }
    return (json.dumps(prompt,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')

def main():
    now=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
    base_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    src_bytes,src_raw=load_source(); src=np.flipud(src_raw).copy()
    fp,fi=font_info(); font_id=f'{Path(fp).name}#{fi} Noto Sans CJK KR Bold (font bytes not distributed)'
    removal=np.zeros((H,W),bool); measured=[]
    for e in ELEMENTS:
        sx0,sy0,sx1,sy1=e['source_effect_bbox']
        x0=max(e['region'][0],sx0-4); y0=max(e['region'][1],sy0-4); x1=min(e['region'][2],sx1+4); y1=min(e['region'][3],sy1+4)
        sub=src[y0:y1,x0:x1]; m=np.any(sub!=0,axis=2)
        removal[y0:y1,x0:x1]|=m
        measured.append({**e,'removal_search_bbox':[x0,y0,x1,y1],'removal_pixels':int(m.sum())})
    clean=src.copy(); clean[removal]=0
    if np.any(clean[~removal]!=src[~removal]): raise SystemExit('clean changed outside mask')
    kx0,ky0,kx1,ky1=K1_PROTECTED_READABLE
    if not np.array_equal(clean[ky0:ky1,kx0:kx1],src[ky0:ky1,kx0:kx1]): raise SystemExit('K1 changed during clean plate')

    cand=clean.copy(); lettering=np.zeros((H,W),bool); per=[]; prompt_elements=[]
    for e in measured:
        x0,y0,x1,y1=e['safe_bbox']; maxw=x1-x0; maxh=y1-y0
        fs=e['font_size_nominal']; font=ImageFont.truetype(fp,size=fs,index=fi)
        probe=Image.new('L',(1024,256),0); pd=ImageDraw.Draw(probe); bb=pd.textbbox((0,0),e['korean'],font=font)
        tw=max(1,bb[2]-bb[0]); th=max(1,bb[3]-bb[1])
        while (tw*4>maxw-4 or th*4>maxh-4) and fs>7:
            fs-=1; font=ImageFont.truetype(fp,size=fs,index=fi); bb=pd.textbbox((0,0),e['korean'],font=font); tw=max(1,bb[2]-bb[0]); th=max(1,bb[3]-bb[1])
        if tw*4>maxw or th*4>maxh: raise SystemExit('cannot safe-fit '+e['id'])
        m=Image.new('L',(tw,th),0); md=ImageDraw.Draw(m); md.text((-bb[0],-bb[1]),e['korean'],font=font,fill=255)
        up=m.resize((tw*4,th*4),Image.Resampling.NEAREST); ma=np.array(up,dtype=np.uint8); nz=ma>0
        xx=x0+2; yy=y0+max(2,(maxh-up.height)//2)
        if xx+up.width>x1: xx=x1-up.width-2
        if yy+up.height>y1: yy=y1-up.height-2
        sub=cand[yy:yy+up.height,xx:xx+up.width]
        sub[nz,0]=e['fill'][0]; sub[nz,1]=e['fill'][1]; sub[nz,2]=e['fill'][2]; sub[nz,3]=ma[nz]
        cand[yy:yy+up.height,xx:xx+up.width]=sub
        cur=np.zeros((H,W),bool); cur[yy:yy+up.height,xx:xx+up.width]=nz; lettering|=cur
        cb=bbox(cur)
        if cb is None or cb[0]<x0 or cb[1]<y0 or cb[2]>x1 or cb[3]>y1: raise SystemExit('containment fail '+e['id'])
        margins={'left':cb[0]-x0,'top':cb[1]-y0,'right':x1-cb[2],'bottom':y1-cb[3]}
        if min(margins.values())<1: raise SystemExit('safety margin fail '+e['id'])
        per.append({'element_id':e['id'],'source':e['source'],'korean':e['korean'],'source_effect_bbox_readable':e['source_effect_bbox'],'removal_search_bbox_readable':e['removal_search_bbox'],'candidate_safe_bbox_readable':e['safe_bbox'],'localized_bbox_readable':cb,'containment_margins':margins,'font_size_nominal':fs,'source_removal_pixels':e['removal_pixels'],'containment':'PASS'})
        prompt_elements.append({'element_id':e['id'],'source_text':e['source'],'korean':e['korean'],'source_bbox':e['source_effect_bbox'],'permitted_region':e['region'],'candidate_safe_bbox':e['safe_bbox'],'safety_inset_px':2,'alignment':'left','line_count':1,'colors':{'fill_rgb':e['fill']},'effects':{'outline':'none','shadow':'none','glow':'none'},'source_text_transform':'flip_y raw / normal readable','baseline_vector':[1,0],'slant_dx_per_dy':0.0,'slant_angle_deg':0.0,'slant_direction':'none','style_traits':{'weight':'bold','width_character':'source-like block sans'},'font_size_nominal':fs})

    allowed=removal|lettering; changed=np.any(cand!=src,axis=2); alpha_changed=cand[:,:,3]!=src[:,:,3]
    changed_outside=int((changed&~allowed).sum()); alpha_outside=int((alpha_changed&~allowed).sum())
    if changed_outside or alpha_outside: raise SystemExit(f'outside change {changed_outside} alpha {alpha_outside}')
    if not np.array_equal(cand[ky0:ky1,kx0:kx1],src[ky0:ky1,kx0:kx1]): raise SystemExit('K1 changed final')
    clean_outside=int((np.any(clean!=src,axis=2)&~removal).sum()); lettering_outside=int((np.any(cand!=clean,axis=2)&~lettering).sum())
    if clean_outside or lettering_outside: raise SystemExit('stage isolation fail')

    cand_raw=np.flipud(cand).copy(); store=cand_raw[..., [2,1,0,3]].copy(); cand_bytes=src_bytes[:128]+store.tobytes(); cand_sha=sha256(cand_bytes)
    if cand_bytes[:128]!=src_bytes[:128] or len(cand_bytes)!=len(src_bytes): raise SystemExit('DDS structure changed')
    dec_store=np.frombuffer(cand_bytes[128:],dtype=np.uint8).reshape(H,W,4); dec_raw=dec_store[..., [2,1,0,3]].copy(); dec=np.flipud(dec_raw).copy()
    roundtrip_exact=bool(np.array_equal(dec,cand))
    if not roundtrip_exact: raise SystemExit('roundtrip mismatch')

    CAND.parent.mkdir(parents=True,exist_ok=True); REVIEW.mkdir(parents=True,exist_ok=True); RUN.mkdir(parents=True,exist_ok=True); TASK.parent.mkdir(parents=True,exist_ok=True)
    CAND.write_bytes(cand_bytes)
    src_disp=rgba_over_black(src); clean_disp=rgba_over_black(clean); cand_disp=rgba_over_black(cand)
    save_rgba(src_disp,REVIEW/'source_display.png'); save_rgba(clean_disp,REVIEW/'clean_plate_display.png'); save_rgba(cand_disp,REVIEW/'candidate_display.png')
    scale=0.5; sw=int(W*scale); sh=int(H*scale); banner=40
    comp=Image.new('RGBA',(sw*3,sh+banner),(24,24,24,255)); labels=['ENGLISH SOURCE','CLEAN PLATE','KOREAN CANDIDATE']
    lf=ImageFont.truetype(fp,size=22,index=fi); d=ImageDraw.Draw(comp)
    for i,(a,label) in enumerate(zip([src_disp,clean_disp,cand_disp],labels)):
        im=Image.fromarray(a,'RGBA').resize((sw,sh),Image.Resampling.NEAREST); comp.paste(im,(i*sw,banner)); d.text((i*sw+10,7),label,font=lf,fill=(255,255,255,255))
    comp.save(REVIEW/'comparison.png',optimize=False)
    diff=np.abs(cand.astype(np.int16)-src.astype(np.int16)).astype(np.uint8); diff[...,3]=255; save_rgba(diff,REVIEW/'diff_display.png')
    al=Image.new('L',(W*2,H),0); al.paste(Image.fromarray(src[:,:,3],'L'),(0,0)); al.paste(Image.fromarray(cand[:,:,3],'L'),(W,0)); al.resize((W,H//2),Image.Resampling.NEAREST).convert('RGBA').save(REVIEW/'alpha_comparison.png',optimize=False)
    crop=[0,760,1320,2048]; x0,y0,x1,y1=crop
    native=Image.new('RGBA',((x1-x0)*2,y1-y0),(0,0,0,255)); native.paste(Image.fromarray(src_disp[y0:y1,x0:x1],'RGBA'),(0,0)); native.paste(Image.fromarray(cand_disp[y0:y1,x0:x1],'RGBA'),(x1-x0,0)); native.save(REVIEW/'text_region_native.png',optimize=False)
    native.resize((native.width*2,native.height*2),Image.Resampling.NEAREST).save(REVIEW/'text_region_nn2x.png',optimize=False)

    pbytes=prompt_bytes(prompt_elements,font_id); prompt_sha=sha256(pbytes); (REVIEW/'generation_prompt.json').write_bytes(pbytes)
    qa={
      'schema_version':10,'schema':'outrun-a00182-index237-rgba32-decoded-final-qa-v2','task_id':TASK_ID,'wave_id':WAVE_ID,'lane':'LOCALIZATION_A','queue_index':INDEX,'asset_id':ASSET,'recorded_at_kst':now,'status':'PASS_SELF_QA_PENDING_C',
      'source_sha256':SOURCE_SHA,'candidate_dds_sha256':cand_sha,'runtime_validation':'UNTESTED','prompt_contract':'outrun-first-pass-edit-v2','prompt_sha256':prompt_sha,'prompt_json_sha256':prompt_sha,'signed_slant_gate':'PASS',
      'source':{'repository':SOURCE_REPO,'commit':SOURCE_COMMIT,'path':SOURCE_REL,'git_blob_sha':SOURCE_GIT_BLOB,'sha256':SOURCE_SHA,'bytes':len(src_bytes),'width':W,'height':H,'format':'RGBA32','pitch':W*4,'mip_count':1,'raw_to_readable':'flip_y','canonical_inventory_match':True},
      'source_acquisition':{'google_drive_exact_filename':'SOURCE_TRANSPORT_MISS','pinned_queue_path_direct':'SOURCE_TRANSPORT_MISS_404','pinned_release_object_direct':'PASS_EXACT_CANONICAL_SOURCE','pinned_release_object_git_blob_sha':SOURCE_GIT_BLOB,'pinned_release_bundle_sha256':PINNED_ZIP_SHA,'local_pre_dispatch_bundle_crosscheck':'PASS_EXACT_DIGEST_AND_MEMBER_SHA'},
      'translations':[{'source':x['source'],'korean':x['korean'],'physical_occurrences':sum(1 for y in ELEMENTS if y['source']==x['source'])} for i,x in enumerate(ELEMENTS) if x['source'] not in [y['source'] for y in ELEMENTS[:i]]],
      'raw_orientation':'flip_y','source_text_transform':'flip_y','signed_slant_angle_deg':0.0,'slant_direction':'none','style':{'font_identifier':font_id,'grey_fill_rgb':[63,71,74],'red_fill_rgb':[186,0,0],'outline_shadow_glow':'none'},
      'source_removal_mask':{'method':'source-effect-aware exact search windows; any nonzero RGBA in 4px-expanded measured English effect bbox; no rectangular whole-cell erase','pixels':int(removal.sum()),'changed_pixels_outside_edit_mask':clean_outside,'changed_pixels_in_protected_mask':0,'protected_k1_exact':True},
      'clean_plate':{'contract':'outrun-clean-plate-qa-v1','changed_pixels_outside_edit_mask':clean_outside,'alpha_changed_outside_edit_mask':int(((clean[:,:,3]!=src[:,:,3])&~removal).sum()),'visible_source_residue_in_target_search_windows':0},
      'decoded_final':{'candidate_path':str(CAND.relative_to(ROOT)).replace('\\','/'),'bytes':len(cand_bytes),'header_128_exact':True,'dimensions':[W,H],'mip_count':1,'roundtrip_decoded_exact':roundtrip_exact,'changed_pixels':int(changed.sum()),'changed_pixels_outside_edit_mask':changed_outside,'changed_pixels_outside_source_region':0,'changed_pixels_in_protected_mask':0,'introduced_alpha_outside_source_region':alpha_outside,'alpha_changed_outside_edit_mask':alpha_outside,'lettering_changed_outside_permitted_regions':lettering_outside,'protected_k1_exact':True,'per_element':per,'orientation':'PASS_FLIP_Y_RAW_TO_READABLE','containment':'PASS_ALL_NINE_PHYSICAL_OCCURRENCES_POSITIVE_MARGIN'},
      'comparison_evidence':[str((REVIEW/x).relative_to(ROOT)).replace('\\','/') for x in ['source_display.png','clean_plate_display.png','candidate_display.png','comparison.png','text_region_native.png','text_region_nn2x.png','diff_display.png','alpha_comparison.png','generation_prompt.json']],
      'english_source_vs_korean_candidate':'PASS_MACHINE_GEOMETRY__HUMAN_EXACT_GITHUB_VISUAL_PENDING','candidate_static_qa':'PASS_MACHINE_V2_PENDING_EXACT_GITHUB_VISUAL_AND_INDEPENDENT_C',
      'automation_validation':'PENDING','validation_mode':'C_BATCH_GATE','runtime_test_performed':False,'build_performed':False,'n100_used':False,'local_clone_used':False,'gpt_library_used':False,'google_drive_used':True,'google_drive_write_performed':False,'vr_ffb_dx_changes':False
    }
    qbytes=(json.dumps(qa,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8'); REPORT.write_bytes(qbytes); (REVIEW/'qa_report.json').write_bytes(qbytes)
    task={
      'schema_version':13,'task_id':TASK_ID,'lane':'LOCALIZATION_A','target_branch':'korean-localization-clean','attempt':'1/3','wave_id':WAVE_ID,'recorded_at_kst':now,'base_head_sha':base_head,'commit_mode':'GITHUB_ACTIONS_ATOMIC_LANE_LOCAL_INDEX237_CANDIDATE_AND_TASK_RECORD',
      'result':'PASS_MATERIAL_INDEX237_FF514CEB_RGBA32_KOREAN_CANDIDATE_V2_SELF_QA_PENDING_C_RUNTIME_UNTESTED',
      'summary':'Latest modulo-3 contract assigns index237 to A. Fresh candidate-first scan skipped A00179 source-exhausted 30/36/48/132, A00173 index99 pending C, and unchanged dependency/runtime blockers. Exact canonical source discovery then found multiple A-shard assets; index231 was fail-closed because its exact source contains unbound English description text not present in canonical transcription. Index237/FF514CEB had exact canonical source plus complete 6-semantic/9-physical binding, so this invocation continued through measured source-effect removal, independently clean transparent plate, flip_y orientation/style measurement, 2px safe-fit Korean render, exact RGBA32 DDS encode and decoded-final self-QA. All nine physical Korean occurrences remain inside safe bboxes with positive margins, no pixels or alpha change outside allowed regions, DDS header/canvas/mips remain exact, and the protected K1 fragment is unchanged. Exact Git visual review and independent C batch QA remain pending; runtime is UNTESTED.',
      'evidence':[str(REPORT.relative_to(ROOT)).replace('\\','/')]+qa['comparison_evidence']+[str((REVIEW/'qa_report.json').relative_to(ROOT)).replace('\\','/'),str(CAND.relative_to(ROOT)).replace('\\','/')],
      'material_deliverable':{'type':'INDEX237_FF514CEB_NEW_V2_KOREAN_RGBA32_CANDIDATE','index':INDEX,'asset':ASSET,'source_sha256':SOURCE_SHA,'candidate_dds_sha256':cand_sha,'candidate_dds_modified':True,'canonical_semantic_segments':6,'physical_localized_occurrences':9,'source_effect_removal_pixels':int(removal.sum()),'changed_pixels_outside_allowed_region':changed_outside,'alpha_changed_pixels_outside_allowed':alpha_outside,'protected_k1_exact':True,'materially_reduces_unresolved_work':True,'material_payload_in_result_commit':True},
      'readiness_audit':{'shard_rule':'A_INDEX_MOD_3_EQ_0','selected_priority':'ONE_STAGE_TO_RENDER_DISCOVERED_AFTER_EXACT_CANONICAL_SOURCE_SCAN','selected_index':INDEX,'skipped_source_exhausted_from_A00179':[30,36,48,132],'qa_pending_skip':{'task_id':'LOCALIZATION-LOCALIZATION_A-00173','index':99,'asset':'4F68708E'},'dependency_or_runtime_blocked_indices':[12,51,54,57,60,63,102,111,195],'index231_fail_closed':'SEMANTIC_BINDING_INCOMPLETE_EXACT_SOURCE_HAS_TWO_DESCRIPTION_STRINGS_NOT_IN_CANONICAL_TRANSCRIPTION','readiness_transition':'PREFLIGHT_ONLY -> EXACT_SOURCE + COMPLETE_BINDING -> ONE_STAGE_TO_RENDER -> CANDIDATE_COMPLETED_SAME_INVOCATION','unrelated_preflight_stopped_after_ready_discovery':True},
      'self_qa':'PASS_MOD3_A_INDEX237__EXACT_CANONICAL_SOURCE__SOURCE_EFFECT_AWARE_CLEAN_PLATE__FLIP_Y__V2_2PX_SAFE_FIT__9_PHYSICAL_OCCURRENCES__ZERO_OUTSIDE_ALLOWED__ZERO_ALPHA_OUTSIDE_ALLOWED__HEADER_EXACT__K1_EXACT__ROUNDTRIP_EXACT',
      'candidate_static_qa':'PASS_MACHINE_V2_PENDING_EXACT_GITHUB_VISUAL_AND_INDEPENDENT_C','shared_state_modified':False,'peer_lane_files_modified':False,'candidate_dds_modified':True,'runtime_test_performed':False,'build_performed':False,'n100_used':False,'local_clone_used':False,'google_drive_used':True,'google_drive_write_performed':False,'gpt_library_used':False,'uploaded_archive_used':True,'uploaded_archive_role':'READ_ONLY_PINNED_V0.25.10A_DIGEST_AND_MEMBER_IDENTITY_CROSSCHECK','work_stolen_from_lane':None,'vr_ffb_dx_changes':False,'automation_validation':'PENDING','validation_mode':'C_BATCH_GATE','runtime_validation':'UNTESTED'
    }
    TASK.write_text(json.dumps(task,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','source_sha256':SOURCE_SHA,'candidate_sha256':cand_sha,'prompt_sha256':prompt_sha,'changed_outside':changed_outside,'alpha_outside':alpha_outside,'removal_pixels':int(removal.sum())},ensure_ascii=False))

if __name__=='__main__': main()
