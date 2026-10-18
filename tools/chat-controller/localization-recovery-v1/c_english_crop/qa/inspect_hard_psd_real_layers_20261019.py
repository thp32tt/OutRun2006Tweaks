#!/usr/bin/env python3
"""Inspect verified upstream editable HARD PSD layers with psd-tools in private QA target."""
import sys,json,hashlib,traceback
from pathlib import Path
B=Path('/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/qa_review_20261018')
S=B/'upstream_psd_evidence'
sys.path.insert(0,str(S/'_qa_psd_deps'))
from psd_tools import PSDImage
from PIL import Image
p=S/'33491F83_512x256.psd'
psd=PSDImage.open(p)
target=(805,291,1071,369)
print('PSD',psd.size,'top children',len(psd),flush=True)
records=[]
def visit(node,prefix='',depth=0):
 for idx,layer in enumerate(node):
  rect=(layer.left,layer.top,layer.right,layer.bottom)
  intersections=max(0,min(target[2],rect[2])-max(target[0],rect[0]))*max(0,min(target[3],rect[3])-max(target[1],rect[1]))
  obj={'path':prefix+'/'+str(idx), 'name':layer.name,'kind':layer.kind,'bbox':rect,
       'visible':layer.visible,'group':layer.is_group(),'target_bbox_intersect':intersections,
       'effects': len(layer.effects) if hasattr(layer,'effects') else 0}
  if intersections or 'HARD' in layer.name.upper(): records.append(obj)
  if layer.is_group():visit(layer,obj['path'],depth+1)
visit(psd)
print('TARGET_RELEVANT_LAYERS',len(records),flush=True)
print(json.dumps(records,ensure_ascii=False)[:16000],flush=True)
(S/'psd_tools_hard_layer_map.json').write_text(json.dumps({'repo':'Sonic-TV/OR2006Sprites','verified_psd':True,'target':target,'layers':records},ensure_ascii=False,indent=2)+'\n')