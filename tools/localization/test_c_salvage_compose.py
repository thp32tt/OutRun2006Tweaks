import hashlib, json, tempfile, struct, sys
from pathlib import Path
from PIL import Image
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c_salvage_compose as c

def put(base,name,im):
    p=base/name; im.save(p,"PNG"); return {"path":name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
def msk(w,h, rect):
    a=np.zeros((h,w),dtype=np.uint8)
    x0,y0,x1,y1=rect;a[y0:y1,x0:x1]=255
    return Image.fromarray(a,"L")
def create_dds(source):
    w,h=source.size
    b=bytearray(128);b[:4]=b"DDS "
    struct.pack_into("<I",b,4,124);struct.pack_into("<I",b,8,0x100f)
    struct.pack_into("<I",b,12,h);struct.pack_into("<I",b,16,w)
    struct.pack_into("<I",b,20,4*w);struct.pack_into("<I",b,28,1)
    struct.pack_into("<I",b,76,32);struct.pack_into("<I",b,80,0x41)
    struct.pack_into("<I",b,88,32)
    struct.pack_into("<IIII",b,92,*c.BGRA_MASKS)
    struct.pack_into("<I",b,108,0x1000)
    return bytes(b)+np.array(source)[:,:,[2,1,0,3]].tobytes()
with tempfile.TemporaryDirectory(prefix="c-smoke-") as td:
    root=Path(td)
    src=Image.new("RGBA",(64,32),(0,0,0,0))
    from PIL import ImageDraw
    d=ImageDraw.Draw(src)
    d.rectangle((8,6,18,16),fill=(250,250,250,255))
    d.rectangle((45,8,54,19),fill=(0,200,20,255))
    original_dds=create_dds(src)
    (root/"original.dds").write_bytes(original_dds)
    source_dds={"path":"original.dds","sha256":hashlib.sha256(original_dds).hexdigest()}
    gen=Image.new("RGBA",(128,64),(100,100,100,255))
    ImageDraw.Draw(gen).rectangle((28,9,48,22),fill=(10,60,240,255))
    inputs=dict(
      source_dds=source_dds,source_png=put(root,"source.png",src),
      generated_png=put(root,"generated.png",gen),
      generated_text_mask=put(root,"gen_mask.png",msk(128,64,(28,9,49,23))),
      removal_mask=put(root,"removal.png",msk(64,32,(8,6,19,17))),
      edit_mask=put(root,"edit.png",msk(64,32,(5,4,34,29))),
      protected_mask=put(root,"protected.png",msk(64,32,(45,8,55,20))),
    )
    recipe={"schema":c.SCHEMA,"orientation":"IDENTITY","translation_verified":True,
            "cell_bbox":[5,4,34,29],"clean_method":"TRANSPARENT_MASK_TEST_ONLY",**inputs}
    out=c.compose(root,recipe,root/"out")
    assert out["status"] == c.STATE
    assert out["generated_mask_bbox"] == [28,9,49,23], out["generated_mask_bbox"]
    assert (root/"out"/"intermediate_TEST_ONLY.dds").exists()
    assert out["source_outside_clean_change"]==0 and out["source_outside_edit_final_change"]==0
    bad=dict(recipe);bad["cell_bbox"]=[45,8,55,20]
    try: c.compose(root,bad,root/"bad")
    except ValueError as e: assert "protected" in str(e)
    else: raise AssertionError("protected overlap guard was bypassed")
    bad=dict(recipe);bad["source_png"]=dict(inputs["source_png"],sha256="a"*64)
    try:c.compose(root,bad,root/"bad2")
    except ValueError as e:assert "SHA256 mismatch" in str(e)
    else: raise AssertionError("sha guard was bypassed")
    print(json.dumps({"result":"PASS","test_cases":3,"dds":out["DDS"],"RUNTIME_VALIDATION":out["RUNTIME_VALIDATION"],"outputs":list(out["outputs"])}))