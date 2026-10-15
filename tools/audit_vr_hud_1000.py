#!/usr/bin/env python3
"""1000 deterministic full-source HUD contract checks + adversarial mutations.
Writes a checkpoint at cycles 30,60,...,990,1000. No HMD claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from verify_vr_hud_exact_callsite_contract import check as check_calls

ROOT=Path(__file__).resolve().parents[1]
FAMILIES={
 "01_original_exe": [
  ("src/hooks_uiscaling.cpp","RankMarker_SpraniCalls"),
  ("src/hooks_uiscaling.cpp","RankMarker_ClipSpriteCalls"),
  ("src/hooks_uiscaling.cpp","OptionArrow_ClipSpriteCalls"),
  ("src/hooks_uiscaling.cpp","TextGlyph_PutSpriteCalls"),
  ("docs/VR_BINARY_CONTRACT.json","VR-EXE-RANK-MARKER-SPRANI-BB0FB")],
 "02_rank_vs_world": [
  ("src/hooks_uiscaling.cpp","RankMarkerSubScreenHudDepth != 0"),
  ("src/hooks_uiscaling.cpp","RenderScope::ProjectedWorldMarker2D"),
  ("src/hooks_uiscaling.cpp","RenderScope::WorldBillboard"),
  ("src/hooks_uiscaling.cpp","ProducerToken::RankMarkerSprani"),
  ("src/hooks_uiscaling.cpp","TagAppendedNodes(")],
 "03_semantic_registry": [
  ("src/vr/game/render_semantics.hpp","SpriteNodeSemanticMutex"),
  ("src/vr/game/render_semantics.hpp","ConsumeSpriteNodeScope("),
  ("src/vr/game/render_semantics.hpp","SpriteQueueSemanticCutoff"),
  ("src/vr/game/render_semantics.hpp","CurrentSpriteQueueNode"),
  ("src/vr/game/render_semantics.hpp","SpriteNodeSemanticStaleCleared")],
 "04_texture_sprite_source": [
  ("src/hooks_textures.cpp","TagDirectVrSpriteNodes("),
  ("src/hooks_textures.cpp","ClassifyDirectVrSpriteCaller(returnAddress)"),
  ("src/hooks_textures.cpp","Game::SpriteNodeMax"),
  ("src/hooks_textures.cpp","put_sprite_ex.call<int>"),
  ("src/hooks_textures.cpp","transientOwner")],
 "05_projected_marker": [
  ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp","semanticProjectedWorld"),
  ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp","R57BuildProjectedMarkerDelta("),
  ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp","R57ProjectedPayloadMissing"),
  ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp","state.projectedWorldMarker = true;"),
  ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp","R57ProjectedBuildFailures")],
 "06_recenter_hud": [
  ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp","GetLatchedHeadInverse("),
  ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp","headPoseSequence != state.stereo.poseSequence"),
  ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp","R30BuildHudPlaneCoefficients(state)"),
  ("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp","state.hudWorldLockValid = true;"),
  ("src/vr/game/outrun_renderer.cpp","Recenter")],
 "07_menu_result_text": [
  ("src/hooks_uiscaling.cpp","ExactScreenHudRight_putClipSprite"),
  ("src/hooks_uiscaling.cpp","ExactScreenHudLeft_putClipSprite"),
  ("src/hooks_uiscaling.cpp","TextGlyph_putSprite"),
  ("src/hooks_uiscaling.cpp","0x97BB7"),
  ("src/hooks_textures.cpp","D3DXCreateTextureFromFileInMemory")],
 "08_flare_shadow": [
  ("src/hooks_graphics.cpp","VRLensFlareProjected2D"),
  ("src/hooks_graphics.cpp","Module::exe_ptr(0xCABE)"),
  ("src/hooks_graphics.cpp","RenderScope::ProjectedScreenEffect2D"),
  ("src/hooks_graphics.cpp","CalcPeraShadow"),
  ("src/hooks_graphics.cpp","RenderScope::WorldParticle")],
 "09_f11_reset": [
  ("src/overlay/hooks_overlay.cpp","ScopedExternalOverlaySemantic"),
  ("src/overlay/hooks_overlay.cpp","ImGui_ImplDX9_RenderDrawData("),
  ("src/vr/game/render_semantics.hpp","ExternalOverlaySemanticDepth"),
  ("src/vr/d3d9/ex_device_upgrade_r14.cpp","R14TrackDirectLockable"),
  ("src/vr/d3d9/ex_device_upgrade_r14.cpp","D3DUSAGE_DYNAMIC")],
 "10_ci_variant_contract": [
  ("tools/verify_vr_visual_composition_p0.py","verify_hud_callsite_contract"),
  ("tools/verify_vr_hud_exact_callsite_contract.py","10/10 failures detected"),
  (".github/workflows/outrun-exe-hud-inspector.yml","Reject corrupted HUD producer mutations"),
  (".github/workflows/vr-dx9ex-active.yml","verify_vr_binary_contract.py"),
  ("tools/Build-OutRunPCFast.ps1","OUTRUN_VR_R26_HUD_COMPARE=ON")]
}
SOURCE_FILES=sorted({p for pairs in FAMILIES.values() for p,_ in pairs})
KNOWN_GAPS=[
 {"id":"F1","state":"NOT_PROVEN","finding":"rank sprani single-tail registration assumes exactly one queued node"},
 {"id":"F2","state":"SEMANTIC_POLICY_CONFLICT","finding":"generic ScreenOverlay2D FOV-only comments disagree with active finite HUD plane"},
 {"id":"F3","state":"ASSET_PROOF_MISSING","finding":"menu/car selection replacement DDS actual load, alpha and pixels not proven"}
]

def structural(content):
    errors=[]
    for lens,pairs in FAMILIES.items():
        for path,anchor in pairs:
            if anchor not in content[path]:
                errors.append(lens+": missing "+path+"::"+anchor)
    try:
        contract=json.loads(content["docs/VR_BINARY_CONTRACT.json"])
        check_calls(content["src/hooks_uiscaling.cpp"],contract)
    except (ValueError,KeyError,TypeError,json.JSONDecodeError) as error:
        errors.append("original EXE CALL/installed hook drift: "+str(error))
    ui=content["src/hooks_uiscaling.cpp"]
    sem=content["src/vr/game/render_semantics.hpp"]
    r30=content["src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"]
    if "tag.serial <= SpriteQueueSemanticCutoff" not in sem:
        errors.append("queue stale cleanup cutoff lost")
    if "CurrentScope = ConsumeSpriteNodeScope(" not in sem:
        errors.append("current queue node semantic consumer lost")
    if "if (ExternalOverlaySemanticDepth != 0)" not in sem:
        errors.append("F11 external overlay can steal draw token")
    if not (0 <= r30.find("if (semanticProjectedWorld)") < r30.find("if (semanticWorld)")):
        errors.append("projected world owner no longer precedes world fallback")
    if not (0 <= ui.find("if (RankMarkerSubScreenHudDepth != 0)") <
            ui.find("RenderScope::ScreenHud",ui.find("if (RankMarkerSubScreenHudDepth != 0)")) <
            ui.find("RenderScope::ProjectedWorldMarker2D",ui.find("if (RankMarkerSubScreenHudDepth != 0)"))):
        errors.append("NaviPub HUD override no longer precedes rank world tag")
    return errors

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--cycles",type=int,default=1000)
    parser.add_argument("--batch",type=int,default=30)
    parser.add_argument("--output",default="hud-audit-output")
    opt=parser.parse_args()
    if opt.cycles!=1000 or opt.batch!=30:
        raise SystemExit("This review requires exactly 1000 iterations with 30-step checkpoints")
    out=ROOT/opt.output
    out.mkdir(parents=True,exist_ok=True)
    original={path:(ROOT/path).read_text(encoding="utf-8") for path in SOURCE_FILES}
    digest=hashlib.sha256("".join(path+"\0"+hashlib.sha256(raw.encode()).hexdigest()
                         for path,raw in sorted(original.items())).encode()).hexdigest()
    baseline=structural(original)
    families=list(FAMILIES)
    failures=[]
    probes=Counter()
    batch=[]
    reports=[]
    sha=os.getenv("GITHUB_SHA","LOCAL_SNAPSHOT_UNVERIFIED")
    for index in range(1,opt.cycles+1):
        # Every pass checks ALL families, including the 71 original EXE CALLs.
        current=structural(original)
        name=families[(index-1)%len(families)]
        variant=(index-1)//len(families)
        path,token=FAMILIES[name][variant%len(FAMILIES[name])]
        changed=dict(original)
        changed[path]=original[path].replace(token,"__AUDIT_CORRUPTION_"+str(index)+"__")
        rejected=bool(structural(changed))
        probes[name]+=1
        result={"cycle":index,"lens":name,"target":path+"::"+token,
                "source_pass":not current,"injected_fault_rejected":rejected}
        if current or not rejected:
            failures.append({"cycle":index,"error":current,"missed_mutation":not rejected})
        batch.append(result)
        if index%opt.batch==0 or index==opt.cycles:
            report={"head_sha":sha,"source_digest":digest,"from":index-len(batch)+1,"to":index,
                    "verdict":"PASS" if all(v["source_pass"] and v["injected_fault_rejected"] for v in batch) else "FAIL",
                    "observations":batch,"open_evidence_gaps":KNOWN_GAPS,
                    "runtime_validation":"UNTESTED"}
            namefile="checkpoint-%04d.json"%index
            (out/namefile).write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            reports.append(namefile)
            print("HUD_CHECKPOINT=%04d/1000 %s findings=%d"%(
                index,report["verdict"],len(failures)),flush=True)
            batch=[]
    summary={"head_sha":sha,"source_digest":digest,"cycles":1000,
             "checkpoints":reports,"family_counts":dict(probes),
             "static_failures":baseline,"missed_mutations":failures,
             "known_unresolved_evidence":KNOWN_GAPS,"runtime_validation":"UNTESTED"}
    (out/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    good=not baseline and not failures and len(reports)==34 and all(v==100 for v in probes.values())
    print("HUD_REVIEW_RESULT="+("PASS" if good else "FAIL")+
          " cycles=1000 checkpoints=%d source_digest=%s runtime=UNTESTED"%(
              len(reports),digest),flush=True)
    return 0 if good else 1

if __name__=="__main__":
    sys.exit(run())
