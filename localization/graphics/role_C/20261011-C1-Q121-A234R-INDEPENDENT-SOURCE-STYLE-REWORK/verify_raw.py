from pathlib import Path
import numpy as np, json
from PIL import Image,ImageDraw
p=Path("work/c1_q121_a234r_20261011_0640")
d={k:np.memmap(p/(k+".dds"),dtype=np.uint8,mode="r",offset=128,shape=(4096,4096,4)) for k in ("source","official","trial")}
roi=(3490,391,3722,440);l,t,r,b=roi
def sub(kind,flip):
    q=d[kind][4096-b:4096-t,l:r][::-1] if flip else d[kind][4096-b:4096-t,l:r]
    return np.array(q)
s=sub("source",True);n=sub("trial",True)
old_src=np.asarray(Image.open(p/"source_native.png").convert("RGBA"))
old_trial=np.asarray(Image.open(p/"producer_final_native.png").convert("RGBA"))
def diff(x,y):
    anydiff=np.any(x!=y,axis=2);alphadiff=x[:,:,3]!=y[:,:,3];visible=np.any(x[:,:,:3]!=y[:,:,:3],axis=2)&((x[:,:,3]>0)|(y[:,:,3]>0))
    over_black=np.abs(x[:,:,:3].astype(int)*x[:,:,3,None].astype(int)-y[:,:,:3].astype(int)*y[:,:,3,None].astype(int)).max(axis=2)>255
    return {"raw_pixels_changed":int(anydiff.sum()),"alpha_mismatch":int(alphadiff.sum()),"foreground_rgb_diff":int(visible.sum()),"alpha_weighted_over_black_mismatch":int(over_black.sum()),"hidden_rgb_only":int((anydiff&(~visible)&(~alphadiff)).sum())}
machine=json.loads((p/"INDEPENDENT_MACHINE.json").read_text())
machine["source_saved_png_diff_detail"]=diff(s,old_src)
machine["trial_saved_png_diff_detail"]=diff(n,old_trial)
# compare same RAW (the original readable bbox maps to mirrored raw y)
for face in ("BLACK","GRAY","WHITE"):
    bg={"BLACK":(0,0,0,255),"GRAY":(116,116,116,255),"WHITE":(255,255,255,255)}[face]
    sheet=Image.new("RGB",((r-l)*4,98), (240,240,240));dr=ImageDraw.Draw(sheet)
    for i,name in enumerate(("source","official","trial")):
        raw=Image.fromarray(sub(name,False),"RGBA")
        bgim=Image.new("RGBA",raw.size,bg);bgim.alpha_composite(raw)
        sheet.paste(bgim.convert("RGB"),((r-l)*i,22))
        dr.text(((r-l)*i+3,5),name.upper()+" RAW native",fill=(0,0,0))
    sheet.save(p/f"C1_RAW_ACTUAL_{face}.png")
machine["raw_footprint_corrected"]="raw y=[3656,3705) not readable y=[391,440), same pixels upside-down"
(p/"INDEPENDENT_MACHINE.json").write_text(json.dumps(machine,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(machine["source_saved_png_diff_detail"]))
print(json.dumps(machine["trial_saved_png_diff_detail"]))