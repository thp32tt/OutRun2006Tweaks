#!/usr/bin/env python3
import importlib.util, tempfile,csv
from pathlib import Path
p=Path(__file__).with_name('analyze_vr_screen_traces.py')
spec=importlib.util.spec_from_file_location('trace_analysis',p)
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 log=root/'OutRun2006Tweaks.log'
 log.write_text(
 '2026-10-18 VR R84 DRAW TRACE 5s: family=STAGE_PLUS_TIME total=12 ok=11 fail=1 '
 'eyes[both=5,failed=1,unverified=6] source[queued=4,unknown=2,badQueue=1,scope=SCREEN_HUD,'
 'producer=OUTRUN_STAGE_EXTENSION_TIME,qEpoch=45] route[none=2,r30Fvf=3,r30Xyz=1,'
 'r33Hud=5,r33World=0,r29=0,raw=1,sbRaw=0] '
 'api[dp=3,dip=4,dpup=5,dipup=0] lastDraw=1000 centreCallEpoch=0\n'
 'VR R84 DRAW TRACE 5s: family=RANK_6TH_OF_6 total=6 ok=6 fail=0 '
 'eyes[both=6,failed=0,unverified=0] source[queued=6,unknown=0,badQueue=0,'
 'scope=SCREEN_HUD,producer=DISPLAY_RANK_FIRST,qEpoch=80] '
 'route[none=0,r30Fvf=0,r30Xyz=0,r33Hud=6,r33World=0,r29=0,raw=0,sbRaw=0] '
 'api[dp=0,dip=6,dpup=0,dipup=0] lastDraw=1010 centreCallEpoch=0\n')
 with (root/'OutRun2006Tweaks-hudtrace.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['call_rva','event','semantic','mode','stage','arg0'])
  w.writeheader();w.writerow(dict(call_rva='0x9898E',event='sprani',semantic='EXTTIME',
                                   mode='STATE_GAME',stage='2',arg0='0x2C00B4'))
 data=t.analyze(root)
 assert data['families']['STAGE_PLUS_TIME']['counters']['total']==12
 assert data['families']['STAGE_PLUS_TIME']['status']=='INVESTIGATE'
 assert 'R33_EYE_OR_RESTORE_FAILED' in data['families']['STAGE_PLUS_TIME']['flags']
 assert data['families']['RANK_6TH_OF_6']['status']=='OBSERVED_NEEDS_QUEST3_OPTICAL_VALIDATION'
 assert data['families']['PAUSE_OPTION_ARROW']['status']=='NOT_OBSERVED'
 assert data['families']['STAGE_PLUS_TIME']['hud_source_rows']==1
 assert data['known_gaps']['f11'].startswith('Separate host')
 print('PASS aggregate screen diagnostics, named producers, unknown/eye flags, NOT_OBSERVED, HUD crosswalk')