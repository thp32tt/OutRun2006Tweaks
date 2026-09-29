#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(os.environ['REPO_ROOT']) if 'REPO_ROOT' in os.environ else Path(__file__).resolve().parents[4]
TASK_ID='LOCALIZATION-LOCALIZATION_A-00221'; WAVE_ID='P00117'; INDEX=222; ASSET='DDF0392A'
SRC=Path(os.environ.get('SOURCE_DDS','/tmp/DDF0392A_256x512.dds'))
SOURCE_SHA='bcfad5a1a71ab66c841134b0f3f3aa8fa5571b806bd3945dabeca3722d18fb72'
ARCHIVE_SHA='76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958'
EXPECTED_FONT_SHA='faa5f3656a78b2e2d450d27fe8382c778bc2b6bb5ea29c986664a6a435056ceb'
EXPECTED_CANDIDATE_SHA='c2938974e9dbde92b05eab319f85e9dd226b7f89b037d24b67b463b312a92878'
EXPECTED_PROMPT_SHA='44027028e5209a1bfb9e2c0af2b31dfd418b06748e8bb059fa711a0e18059a3b'
EXPECTED_MASK_PIXELS=56615
EXPECTED_CLEAN_RAW='c75279677800c75db338aaa5285b6e64dded5f4b4c7f67452e7686aaef21447f'
W,H=1024,2048
REGIONS=[
 (0,'sprite_401','OutRun Mode / 15 C.','아웃런 모드 / 15코스',[0,1972,960,76],[6,14,548,66],[8,16,546,64],[46,53,57],45),
 (1,'sprite_402','OutRun 1986','아웃런 1986',[0,1896,960,76],[4,17,333,61],[6,19,331,59],[57,61,65],40),
 (2,'sprite_403','Journey Mode / Random','저니 모드 / 무작위',[0,1820,960,76],[2,10,627,68],[4,12,625,66],[46,53,57],50),
 (3,'sprite_404','Who Are You?','당신은 누구?',[0,1744,960,76],[2,17,342,60],[4,19,340,58],[66,65,66],39),
 (6,'sprite_407','Shake The Street','거리를 뒤흔들어라',[0,1516,960,76],[3,17,419,60],[5,19,417,58],[66,65,66],39),
 (7,'sprite_408','Rush A Difficulty','난이도에 도전',[0,1440,960,76],[6,17,421,70],[8,19,419,68],[66,65,66],49),
]
MASK_SHA={0:'2ce842e4548201e2c50e088f709f14b5ac2a35e80ea8fbdb5f2784056858f1f7',1:'349ff963d0aebf0ae1fe6909cd4d9ce18d7909dde19be119220e81660c4a78d5',2:'b8f773f47536dfa3917eece034fed358323d2f15a87cbfbb09f34bade3bf4dbe',3:'72051598ae3662c21e347666deb6bc825e13e1c3099ec9cf8e0e10fdea2f32c5',6:'669eb0c12e6b6a3e4e4c3b3828a7afa4e50dc7751a535a4d2f36ed214403bbc1',7:'e435df981046fe8ebe4bc7355473dfb29010699f6d947f7e6944de5f508146d5'}
RUN=ROOT/'localization/graphics/role_A/20260930-A00221-P00117'
REVIEW=ROOT/'localization/graphics/KOREAN_PNG_REVIEW/DDF0392A'
CAND=ROOT/'localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/DDF0392A_256x512.dds'
TASK=ROOT/'docs/automation/runs/LOCALIZATION-LOCALIZATION_A-00221.json'
REPORT=RUN/'A00221_P00117_INDEX222_V2_PRODUCTION.json'

def sha(b): return hashlib.sha256(b).hexdigest()
def fsha(p): return sha(Path(p).read_bytes())
def githead(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def font_info():
    out=subprocess.check_output(['fc-match','-f','%{file}|%{index}\\n','Noto Sans CJK KR:style=Bold'],text=True).splitlines()[0]
    p,i=out.rsplit('|',1); p=Path(p)
    if fsha(p)!=EXPECTED_FONT_SHA: raise SystemExit('font fingerprint mismatch')
    return p,int(i)
def inside(a,b): return a[0]>=b[0] and a[1]>=b[1] and a[2]<=b[2] and a[3]<=b[3]
def save_rgba(a,p): p.parent.mkdir(parents=True,exist_ok=True); Image.fromarray(a.astype(np.uint8),'RGBA').save(p,optimize=False)
