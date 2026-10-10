from pathlib import Path
import json,numpy as np
from PIL import Image
root=Path('/home/chatgpt-runner2/work/outrun-c2-20261010-2150/localization/graphics')
out=root/'role_C/20261010-C2-Q060-B359-INDEPENDENT-NATIVE-FAMILY'
paths={
 'source':root/'hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds',
 'B353':root/'role_B/20261010-B353-Q060-ENGLISH-PERROW-MATERIAL-PILOT/B353_Q060_SOURCE_CONTOUR_GOLD_KOREAN_UNAPPROVED.dds',
 'B359':root/'role_B/20261010-B359-Q060-CONTOUR-NORMAL-BEVEL-FAMILY/B359_Q060_SOURCE_CONTOUR_GOLD_KOREAN_UNAPPROVED.dds'}
def get(p):
 b=p.read_bytes()
 return np.frombuffer(b,dtype=np.uint8,offset=128).reshape(2048,4096,4)[::-1][340:474,2179:3028].copy()
s={k:get(v) for k,v in paths.items()}
profile={}
for k,a in s.items():
 rgb=a[:,:,:3].astype(int);al=a[:,:,3]
 opaque=al>=200
 r,g,b=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
 orange=(r>=200)&(g>=60)&(g<=165)&(b<=115)&(r-g>=55)
 pale=(r>=220)&(g>=175)&(b>=125)
 yellow=(r>=215)&(g>=165)&(b<=130)
 navy=(b<=120)&(r<=75)&(g<=85)
 highlight=(r>=235)&(g>=210)&(b>=155)
 profile[k]={'alpha_ge_200':int(opaque.sum()),'saturated_source_orange_face_pixels':int((opaque&orange).sum()),
 'pale_cream_face_pixels':int((opaque&pale).sum()),
 'gold_yellow_pixels':int((opaque&yellow).sum()),
 'navy_pixels':int((opaque&navy).sum()),
 'bright_highlight_pixels':int((opaque&highlight).sum()),
 'saturated_orange_of_opaque_ratio':round(float((opaque&orange).sum())/max(1,int(opaque.sum())),4),
 'pale_cream_of_opaque_ratio':round(float((opaque&pale).sum())/max(1,int(opaque.sum())),4)}
v=json.loads((out/'C2_Q060_B359_INDEPENDENT_MACHINE.json').read_text())
v['color_family_proxy']=profile
v['color_metric_limit']='Fixed RGB thresholds are descriptive of actual persisted pixels and not universal font-quality or visual-approval thresholds. Text glyph shapes differ; cross-script pixel fraction alone cannot determine PASS.'
(out/'C2_Q060_B359_INDEPENDENT_MACHINE.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(profile,ensure_ascii=False))