#!/usr/bin/env python3
import csv, json, re, sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LOC=ROOT/'localization'
errors=[]

def fail(msg): errors.append(msg)

progress=json.loads((LOC/'progress/progress.json').read_text(encoding='utf-8'))

# Text state
text=[]
for n,line in enumerate((LOC/'text/korean_all.jsonl').read_text(encoding='utf-8').splitlines(),1):
    try: row=json.loads(line)
    except Exception as e:
        fail(f'text line {n}: invalid JSON: {e}'); continue
    text.append(row)
if len(text)!=1356: fail(f'text row count {len(text)} != 1356')
ids=[r.get('id') for r in text]
if ids!=list(range(1356)): fail('text IDs are not exactly 0..1355 in order')
for r in text:
    if r.get('status')=='blocked_null':
        if r.get('source_hash') not in ('',None): fail(f"id {r.get('id')}: null row has source hash")
    elif not re.fullmatch(r'[0-9a-f]{16}',r.get('source_hash','')):
        fail(f"id {r.get('id')}: invalid source hash")
    if 'korean' not in r: fail(f"id {r.get('id')}: missing korean field")
status=Counter(r.get('status') for r in text)
expected={
 'reviewed':progress['text']['reviewed'],
 'reviewed_special':progress['text']['reviewed_special'],
 'draft':progress['text']['draft_context'],
 'blocked_null':progress['text']['blocked_null'],
}
if dict(status)!=expected: fail(f'text status counts {dict(status)} != {expected}')
if sum(1 for r in text if r.get('status')!='blocked_null')!=progress['text']['translated_non_null']:
    fail('translated_non_null mismatch')

special=json.loads((LOC/'text/special_records.json').read_text(encoding='utf-8'))
special_ids=sorted(int(x) for x in special)
state_special=sorted(r['id'] for r in text if r.get('status')=='reviewed_special')
if special_ids!=state_special: fail(f'special record IDs {special_ids} != {state_special}')
for sid,obj in special.items():
    if obj.get('tail_policy')!='preserve_raw_after_first_nul': fail(f'special {sid}: invalid tail policy')

# Config text
with (LOC/'text/config_text_ko.tsv').open(encoding='utf-8-sig',newline='') as f:
    config=list(csv.DictReader(f,delimiter='\t'))
if len(config)!=progress['text']['config_text_rows']: fail('config text row count mismatch')

# Graphics transcription JSONL
transcriptions=[]
for n,line in enumerate((LOC/'graphics/transcriptions.jsonl').read_text(encoding='utf-8').splitlines(),1):
    if not line.strip():
        continue
    try:
        row=json.loads(line)
    except Exception as e:
        fail(f'graphics transcription line {n}: invalid JSON: {e}')
        continue
    transcriptions.append(row)
tr_ids=[r.get('index') for r in transcriptions]
if len(tr_ids)!=len(set(tr_ids)):
    fail('duplicate graphics transcription indices')
tr_segments=sum(len(r.get('segments',[])) for r in transcriptions)
expected_tr_assets=progress['graphics']['transcribed_assets']
expected_tr_segments=progress['graphics']['transcribed_segments']
if len(transcriptions)!=expected_tr_assets:
    fail(f'graphics transcription count {len(transcriptions)} != {expected_tr_assets}')
if tr_segments!=expected_tr_segments:
    fail(f'graphics transcription segments {tr_segments} != {expected_tr_segments}')

# Graphics state
with (LOC/'graphics/visual_review.csv').open(encoding='utf-8-sig',newline='') as f:
    visual=list(csv.DictReader(f))
with (LOC/'graphics/inventory.csv').open(encoding='utf-8-sig',newline='') as f:
    inventory=list(csv.DictReader(f))
if len(visual)!=243: fail(f'visual rows {len(visual)} != 243')
if len(inventory)!=243: fail(f'inventory rows {len(inventory)} != 243')
if [int(r['index']) for r in visual]!=list(range(243)): fail('visual indices are not 0..242')
vis_paths=[r['path'] for r in visual]
inv_paths=[r['path'] for r in inventory]
if vis_paths!=inv_paths: fail('visual/inventory path order mismatch')
if len(set(inv_paths))!=243: fail('duplicate graphics paths')
for r in inventory:
    if not re.fullmatch(r'[0-9a-f]{64}',r.get('sha256','')): fail(f"invalid asset hash: {r.get('path')}")
actions=Counter(r['action'] for r in visual)
action_keys=('localize_text','preserve_brand_song_credit','font_pipeline','hangul_name_entry','zoom_review','no_localization')
expected_actions={k:progress['graphics'][k] for k in action_keys}
if dict(actions)!=expected_actions: fail(f'graphics action counts {dict(actions)} != {expected_actions}')

if errors:
    print('LOCALIZATION_STATE_FAIL')
    for e in errors: print('-',e)
    sys.exit(1)
print('LOCALIZATION_STATE_OK')
print('text_status=',dict(status))
print('graphics_actions=',dict(actions))
print('draft_context_ids=',progress['text']['context_review_ids'])