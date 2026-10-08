#!/usr/bin/env python3
"""Whole-source cross-domain impact inventory for OutRun2006Tweaks.

This scans every C++/H/HPP/INC in src, examines build/CI contracts,
records source-line risky interactions as review candidates, and checks that
the hard original EXE/HUD/scene DDS invariants remain wired.
It is NOT an AST proof, and observations != confirmed runtime defects.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"fullsource-review-output"
OUT.mkdir(exist_ok=True)
EXT={".cpp",".h",".hpp",".inc"}
files=sorted(p for p in (ROOT/"src").rglob("*") if p.is_file() and p.suffix.lower() in EXT)
inventory=[]
source={}
for file in files:
    rel=file.relative_to(ROOT).as_posix()
    blob=file.read_bytes()
    try: txt=blob.decode("utf-8")
    except UnicodeDecodeError: txt=blob.decode("utf-8",errors="replace")
    source[rel]=txt
    inventory.append({"path":rel,"bytes":len(blob),"sha256":hashlib.sha256(blob).hexdigest(),
                      "lines":txt.count("\n")+1})
def get(path):return (ROOT/path).read_text(encoding="utf-8")
def occurrences(path,regex):
    body=source.get(path,"")
    return [{"path":path,"line":body.count("\n",0,m.start())+1,
             "evidence":body[max(0,m.start()-80):min(len(body),m.end()+120)].replace("\n"," ")[:245]}
            for m in re.finditer(regex,body)]
def check(condition,message):
    if not condition:hard.append(message)

hard=[]
claims=[]
checks=[
("scene fast Ex legacy fallback", "src/hooks_textures.cpp", r"const bool requiresLegacyD3DX"),
("scene Ex original trampoline", "src/hooks_textures.cpp", r"return D3DXCreateTextureFromFileInMemoryEx\.stdcall<HRESULT>\("),
("texture pitch and static lock", "src/hooks_textures.cpp", r"const DWORD lockFlags = \(dynamicTexture && mipLevel == 0\)"),
("DX9Ex HUD pose validity", "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", r"headPoseSequence != state\.stereo\.poseSequence"),
("rank semantic original CALL", "src/hooks_uiscaling.cpp", r"RankMarker_SpraniCalls"),
("input wheel separation", "src/hooks_wheel_ffb.cpp", r"Settings::"),
("D3D renderer reset lifecycle", "src/vr/game/outrun_renderer.cpp", r"NotifyGameReset\(\)"),
("F11 ImGui semantic isolation", "src/overlay/hooks_overlay.cpp", r"ScopedExternalOverlaySemantic"),
]
for label,path,pattern in checks:
    ok=bool(re.search(pattern,source.get(path,"")))
    claims.append({"check":label,"file":path,"present":ok})
    check(ok,"Missing cross-domain invariant "+label)
cmake=get("CMakeLists.txt")
active=get(".github/workflows/vr-dx9ex-active.yml")
pcfast=get("tools/Build-OutRunPCFast.ps1")
hud=get(".github/workflows/outrun-exe-hud-inspector.yml")
p0=get("tools/verify_vr_visual_composition_p0.py")
for flag in ["-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF",
             "-DOUTRUN_VR_R26_HUD_COMPARE=ON",
             "-DOUTRUN_VR_C1_COMPARE=OFF",
             "-DOUTRUN_VR_C2_COMPARE=OFF"]:
    check(flag in active and flag in pcfast,"Active/PC fast config divergence: "+flag)
check("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp" in cmake,"Active HUD source not in build")
check("python tools/verify_vr_texture_scene_contract.py --self-test" in hud,
      "HUD Inspector does not run scene Ex negative test")
check("verify_scene_texture_contract(textures)" in p0,"P0 missing scene Ex static verification")
check("python tools/verify_vr_visual_composition_p0.py" in hud,
      "P0 visual contract not run by HUD Inspector")
check("verify_vr_hud_dds_loader.py" in active,
      "DX9Ex active CI does not watch DDS loader changes")
risk_specs=[
 ("F01","HIGH","possible background thread lifetime after unload",
  "src/hooks_input.cpp",r"DeviceEnumerationThreadHandle->detach\(\)"),
 ("F02","MEDIUM","VR non-default fast-load can trigger D3D9 Reset and recreation while cadence/off state changes",
  "src/hooks_framerate.cpp",r"Game::D3DDevice\(\)->Reset\("),
 ("F03","MEDIUM","old EXE string patch uses strcpy, binary capacity must be proved before changing",
  "src/hooks_bugfixes.cpp",r"strcpy\(patch_addr,\s*NewPath\.c_str\(\)\)"),
 ("F04","MEDIUM","DDS replacement mutates original game buffer header before GPU creation success",
  "src/hooks_textures.cpp",r"memcpy\(\*ppSrcData,\s*file,\s*sizeof\(DDS_FILE\)\)"),
 ("F05","MEDIUM","rank exact sprani path tags final node only, not all siblings",
  "src/hooks_uiscaling.cpp",r"static int __cdecl RankMarker_sprani\("),
 ("F06","MEDIUM","fixed-function ScreenOverlay2D uses recentered HUD plane unlike shader FOV-only path",
  "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",r"state\.screenOverlay2D = semanticOverlay2D;"),
 ("F07","LOW","legacy input thread polls input COM pointer while game may tear down",
  "src/hooks_input.cpp",r"Game::DirectInput8\(\)->EnumDevices\("),
 ("F08","LOW","scene DDS fallback has repaired two-decoder transient lifetime; verify live original assets still valid",
  "src/hooks_textures.cpp",r"const bool requiresLegacyD3DX\s*="),
]
candidates=[]
for ident,severity,why,path,regex in risk_specs:
    found=occurrences(path,regex)
    candidates.append({"id":ident,"severity":severity,"hypothesis":why,
                       "evidence":found,"state":"SOURCE_REVIEW_CANDIDATE_NOT_RUNTIME_PROVEN"})
    if not found: hard.append("Risk candidate source moved: "+ident)
extra=[]
for path,txt in source.items():
    for match in re.finditer(r"(?<!\w)\.detach\s*\(|\bstrcpy\s*\(|->Reset\s*\(",txt):
        extra.append({"path":path,"line":txt.count("\n",0,match.start())+1,"token":match.group(0)})
summary={
 "source_sha":os.getenv("GITHUB_SHA","LOCAL_UNTRUSTED"),
 "scope":"whole-current-branch-src-C++-and-cross-domain-build-graph",
 "source_files":len(files),
 "source_bytes":sum(x["bytes"] for x in inventory),
 "groups":dict(Counter("/".join(x["path"].split("/")[:3]) for x in inventory)),
 "hard_failures":hard,
 "hard_checks":claims,
 "risk_candidates":candidates,
 "unclassified_unsafe_interactions":extra,
 "known_runtime_failures_remain_open":True,
 "runtime_validation":"UNTESTED",
 "warning":"Source heuristics and compilation cannot establish a Quest3/VDXR visual pass."
}
(OUT/"source_inventory.json").write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+"\n")
(OUT/"cross_domain_review.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(f"FULL_SOURCE_INVENTORY files={len(files)} bytes={summary['source_bytes']} risks={len(candidates)} hard={len(hard)}")
for row in candidates:
    print(f"CROSS_DOMAIN_CANDIDATE={row['id']} {row['severity']} {row['hypothesis']} ({row['evidence'][0]['path']}:{row['evidence'][0]['line'] if row['evidence'] else 0})")
if hard:
    for error in hard:print("FULL_SOURCE_HARD_FAILURE="+error)
    sys.exit(1)
print("FULL_SOURCE_CROSS_DOMAIN_STATIC=PASS (risks preserved as unresolved, runtime UNTESTED)")
