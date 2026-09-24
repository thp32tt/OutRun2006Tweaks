#!/usr/bin/env python3
import argparse, fnmatch, re, subprocess, sys
from pathlib import Path
BRANCH_DOMAIN={"vr-d3d9ex-focus":"VR","korean-localization-prototype":"LOCALIZATION","korean-localization-clean":"LOCALIZATION","ffb-arcade-dd-research":"FFB"}
OWNED={"VR":["src/vr/**","src/vr_shared.hpp","VR_OPENXR.md","docs/VR_*",".github/workflows/vr-*"],"LOCALIZATION":["localization/**","tools/localization/**","src/hooks_localization.cpp","docs/KOREAN_LOCALIZATION.md",".github/workflows/localization-*"],"FFB":["WHEEL_FFB.md","docs/FFB_STANDALONE_BRANCH.md","docs/reverse/C2C_STAGE_FFB_MAP.md","docs/reverse/LINDBERGH_FFB_MAP.md","docs/reverse/PS2_FFB_MAP.md","reverse/ps2/**","src/hooks_wheel_ffb.cpp","src/hooks_wheel_ffb_build.cpp","src/hooks_wheel_r3_device_autoselect.hpp","src/hooks_wheel_vehicle_dynamics.hpp","src/wheel_ffb_math.hpp","src/wheel_profile_store.hpp","src/overlay/wheel_setup_ui.cpp","tools/reverse/ps2/**"]}
def git(*a): return subprocess.run(["git",*a],check=True,text=True,stdout=subprocess.PIPE).stdout.strip()
def owner(path):
 for d,ps in OWNED.items():
  if any(fnmatch.fnmatch(path,x) for x in ps): return d
def domain_at(c):
 q=subprocess.run(["git","show",f"{c}:.project-domain"],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
 return q.stdout.strip().upper() if q.returncode==0 else None
ap=argparse.ArgumentParser(); ap.add_argument("--base",required=True); ap.add_argument("--head",required=True); ap.add_argument("--branch",required=True); a=ap.parse_args()
branch=a.branch.removeprefix("refs/heads/"); expected=BRANCH_DOMAIN.get(branch)
if not expected: raise SystemExit(0)
errs=[]; actual=Path(".project-domain").read_text().strip().upper() if Path(".project-domain").exists() else ""
if actual!=expected: errs.append(f"domain marker {actual!r} != {expected}")
base=a.base
if re.fullmatch(r"0+",base): base=git("rev-parse",f"{a.head}^")
for path in git("diff","--name-only",f"{base}..{a.head}").splitlines():
 if path.startswith("docs/shared-knowledge/"):
  if Path(path).suffix.lower() not in {".md",".txt",".json",".jsonl",".csv",".tsv",".yaml",".yml"}: errs.append(f"non-data shared file: {path}")
  continue
 o=owner(path)
 if o and o!=expected: errs.append(f"foreign domain path: {path} ({o}->{expected})")
for c in git("rev-list","--reverse",f"{base}..{a.head}").splitlines():
 ps=git("show","-s","--format=%P",c).split()
 for parent in ps[1:]:
  d=domain_at(parent)
  if d and d!=expected: errs.append(f"cross-domain merge {c[:12]} parent={d}")
 m=re.search(r"(?mi)^Domain:\s*(VR|LOCALIZATION|FFB)\s*$",git("show","-s","--format=%B",c))
 if m and m.group(1).upper()!=expected: errs.append(f"wrong Domain trailer {c[:12]}")
if errs:
 print("DOMAIN ISOLATION FAILED",file=sys.stderr)
 [print(" - "+x,file=sys.stderr) for x in errs]
 raise SystemExit(1)
print(f"DOMAIN ISOLATION PASS {branch} {expected}")
