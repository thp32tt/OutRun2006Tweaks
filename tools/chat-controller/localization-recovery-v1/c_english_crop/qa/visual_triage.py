#!/usr/bin/env python3
"""Visual contact-sheet triage; candidate != accepted; standalone QA only.
The enumerated item IDs are the printed 001..076 contact-sheet order.
"""
from pathlib import Path
from collections import Counter
import json,csv
B=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/qa_review_20261018')
edge=json.loads((B/'qa_76_edge.json').read_text(encoding='utf-8'))
assert len(edge)==76
# Human-readable visual judgments based on six contact sheets; no auto-PASS.
clean={7,8,9,11,13,14,41,50,51,57}
plate={3,35,40,43,48,61,62,63,64,65,66,67,68,69,70,71,72,73,75,76}
clip={
 16:'Exclamation mark / final glyph appears at crop edge',
 37:'Final button text/punctuation meets right crop edge',
 39:'Steering Wheel punctuation appears cut at right edge',
 42:'Time remaining colon and following UI text near right edge',
 44:'Gas Pedal punctuation touches right edge',
 45:'Versus Mode final dot touches crop edge',
 59:'Coniferous Forest meets adjacent text at right edge'
}
art={
 1:'Car and neighboring stage text included',
 2:'Left neighboring red sprite fragment',
 4:'Neighboring vertical black UI fragment',
 5:'Red UI sprite bar inside crop',
 6:'Red UI sprite bar inside crop',
 10:'Yellow UI borders/plate lines cross crop',
 12:'Black vertical UI element included',
 15:'Right neighboring letter visible',
 17:'Stray bottom UI pixels included',
 18:'Stray bottom UI pixels included',
 19:'Stray bottom UI pixels included',
 20:'Cars / unrelated sprites inside Special Request box',
 21:'Red car/sprite fragments under Target',
 22:'Cars below Technical Bonus title included',
 23:'Cars / unrelated sprites inside Special Request box',
 24:'Red car/sprite fragments under Target',
 25:'Cars below Technical Bonus title included',
 26:'Cars / unrelated sprites inside Special Request box',
 27:'Red car/sprite fragments under Target',
 28:'Cars below Technical Bonus title included',
 29:'Cars / unrelated sprites inside Special Request box',
 30:'Red car/sprite fragments under Target',
 31:'Cars below Technical Bonus title included',
 32:'Cars / unrelated sprites inside Special Request box',
 33:'Red car/sprite fragments under Target',
 34:'Cars below Technical Bonus title included',
 36:'White/green adjacent plate parts protrude from HARD crop',
 38:'Adjacent numeral visible after seconds',
 46:'Neighboring NOVICE/CLASS/UI fragment included',
 47:'Left neighboring letter visible before MAX SPEED',
 49:'Duplicated adjacent SELECT LICENSE text',
 52:'Red UI border and neighboring sprite line',
 53:'Neighboring left number/sprite fragment',
 54:'Neighboring left number/sprite fragment',
 55:'Neighboring left number/sprite fragment',
 56:'Neighboring left number/sprite fragment',
 58:'Horizontal fragment from neighboring UI text',
 60:'Adjacent typography touches right edge',
 74:'Black left menu/UI bar included'
}
allgroup=clean|plate|set(clip)|set(art)
assert allgroup==set(range(1,77)),{'missing':sorted(set(range(1,77))-allgroup),'overlap':len(allgroup), 'groups_total':sum(map(len,[clean,plate,clip,art]))}
for i,r in enumerate(edge,1):
 if i in clean:
  status='VISUAL_LEGIBLE_CANDIDATE_QA_REQUIRED'
  reason='Main English phrase appears legible and isolated in visual preview; outline/alpha boundary remains to check in native pixels'
 elif i in plate:
  status='PLATE_UNDERLINE_REVIEW_REQUIRED'
  reason='Phrase appears legible, but original plate, underline, or visual decorations may need separate clean-layer treatment'
 elif i in clip:
  status='REWORK_CLIPPED_OR_LABEL_MISMATCH'
  reason=clip[i]
 else:
  status='REWORK_NEIGHBOR_ART_INCLUDED'
  reason=art[i]
 r['visual_sheet_index']=i
 r['visual_sheet']='EDGE_REVIEW_CONTACT_%02d_of_06.jpg'%((i-1)//15+1)
 r['visual_triage']=status
 r['visual_triage_reason']=reason
 r['manual_approval']='NOT_GRANTED'
 r['runtime_validation']='UNTESTED'
qa_counts=Counter(r['visual_triage'] for r in edge)
(B/'visual_triage_76.json').write_text(json.dumps(edge,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
with (B/'visual_triage_76.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['index','english','source_png','category','reason','visual_sheet','source_bbox','pixel_qa','human_approval'])
 for r in edge:
  w.writerow([r['visual_sheet_index'],r['english'],r['source_png'],r['visual_triage'],r['visual_triage_reason'],r['visual_sheet'],r['original_box'],r['technical_qa'],r['manual_approval']])
hold=[r for r in edge if r['visual_triage'].startswith('REWORK_')]
(B/'rework_queue_43_or_more.json').write_text(json.dumps({'status':'C_ONLY_OFFLINE_REWORK_PLANNED_NOT_ENQUEUED',
  'instructions':'Do not touch the running OCR queue, do not mark C1/C3/game PASS; prepare narrower native crop and compare at full res',
  'count':len(hold),'items':[{k:r[k] for k in ['visual_sheet_index','source_png','english','original_box','visual_triage','visual_triage_reason','manifest']} for r in hold]},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
summ={'status':'VISUAL_TRIAGE_COMPLETE_NOT_GAME_APPROVAL','total_edge':len(edge),'summary':dict(qa_counts),
      'rework_count':len(hold),'no_mutation_to_original_crops':True,
      'operator_approval':'PENDING','C1_C3_RUNTIME':'UNTESTED',
      'contact_sheets':6,'files':['visual_triage_76.json','visual_triage_76.csv','rework_queue_43_or_more.json']}
(B/'visual_triage_summary.json').write_text(json.dumps(summ,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(summ,ensure_ascii=False))