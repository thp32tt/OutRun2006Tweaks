#!/usr/bin/env python3
"""Daytona 365 GTS/4 original-PMT-preserving GLB rework (non-runtime preview).
Reads only the original PMT; never modifies it. No Dino code/assets are changed.
AI grain seed is abstract material microdetail only, NOT a generated UV atlas.
"""
import base64
import hashlib
import io
import json
import math
import struct
import zlib
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
try:
    import pmt_export_base as base
except ModuleNotFoundError:
    import dino_original_pmt_to_glb as base

ROOT=Path(__file__).resolve().parent
GAME=Path("/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars")
SOURCE=GAME/"obj_plcar_dayts_pmt.sz"
EXPECTED_SHA="f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe"
PBR_TEX={14,16,19}
AI_GRAIN_TEX={14,16,19}
ENGINEERING_WARNING="GLB visual preview, NOT an R26/OVC runtime model or proof of live Quest compatibility."
NORMAL_CACHE={}
ORIGINAL_DECODE=base.decode_dds

def load_seed():
    b=zlib.decompress(base64.b85decode((ROOT/"daytona365_pmt_ai_grain_seed.b85").read_text().strip()))
    if len(b)!=1024:raise ValueError("Generated grain tile size mismatch")
    tile=Image.frombytes("L",(32,32),b)
    block=Image.new("L",(64,64))
    block.paste(tile,(0,0))
    block.paste(tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT),(32,0))
    block.paste(tile.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(0,32))
    block.paste(tile.transpose(Image.Transpose.ROTATE_180),(32,32))
    return block

SEED=load_seed()
OUT=ROOT/"outputs"
TEX=OUT/"textures"
OUT.mkdir(exist_ok=True)
TEX.mkdir(exist_ok=True)

def enhance_tex(asset, idx, scale):
    png, size, _ = ORIGINAL_DECODE(asset,idx,1)
    img=Image.open(io.BytesIO(png)).convert("RGBA")
    w,h=img.size
    fac=min(4,max(1,1024//max(w,h))) # Never oversample beyond 4x, cap 1024.
    img=img.resize((w*fac,h*fac),Image.Resampling.LANCZOS)
    if idx in (8,15,18,33):
        img=img.filter(ImageFilter.UnsharpMask(radius=1.25,percent=130,threshold=3))
    elif idx in AI_GRAIN_TEX or idx==10 and CURRENT_CONTEXT=="wheel":
        rgb=img.convert("RGB")
        grain=SEED.resize(rgb.size, Image.Resampling.BILINEAR)
        data=list(rgb.getdata())
        n=list(grain.getdata())
        # Subtle material micrograin; preserve signage, UV borders, original shading and alpha.
        blend=[]
        factor=0.28 if idx in (16,19) else 0.18
        for c,g in zip(data,n):
            delta=round((g-128)*factor)
            blend.append(tuple(max(0,min(255,q+delta)) for q in c))
        rgb.putdata(blend)
        img=Image.merge("RGBA",(*rgb.split(),img.getchannel("A")))
        img=img.filter(ImageFilter.UnsharpMask(radius=0.65,percent=35,threshold=4))
    else:
        img=img.filter(ImageFilter.UnsharpMask(radius=0.8,percent=55,threshold=4))
    dst=TEX/("Daytona_%s_tex%02d_BaseColor.png"%(CURRENT_CONTEXT,idx))
    img.save(dst,optimize=True)
    NORMAL_CACHE[(CURRENT_CONTEXT,idx)]=img.copy()
    bio=io.BytesIO();img.save(bio,format="PNG",optimize=True)
    return bio.getvalue(),size,list(img.size)

def safe_subdivide(part):
    # Exact linear interpolation: refines topology/normals, NEVER moves the original silhouette.
    v=part["vertices"]; n=part["normals"]; uv=part["uvs"]; idx=part["indices"]
    if part["tex_index"] not in (16,19) or len(idx)>30000:return part,False
    newv=list(v);newn=list(n);newuv=list(uv);newi=[];edges={}
    def mid(a,b):
        k=(a,b) if a<b else (b,a)
        if k not in edges:
            p=tuple((v[a][t]+v[b][t])*.5 for t in range(3))
            normal=[n[a][t]+n[b][t] for t in range(3)]
            mag=math.sqrt(sum(t*t for t in normal))
            normal=tuple(t/mag for t in normal) if mag>1e-8 else tuple(n[a])
            newv.append(p);newn.append(normal)
            newuv.append(tuple((uv[a][t]+uv[b][t])*.5 for t in range(2)))
            edges[k]=len(newv)-1
        return edges[k]
    for i in range(0,len(idx),3):
        a,b,c=idx[i:i+3]
        ab,bc,ca=mid(a,b),mid(b,c),mid(c,a)
        newi.extend((a,ab,ca,ab,b,bc,ca,bc,c,ab,bc,ca))
    result=dict(part,vertices=newv,normals=newn,uvs=newuv,indices=newi)
    return result,True

def normalize(part):
    p=dict(part)
    n=[]
    for r in p["normals"]:
        mag=math.sqrt(sum(x*x for x in r))
        n.append(tuple(x/mag for x in r) if mag>1e-8 else (0,1,0))
    p["normals"]=n
    return p

def img_png(img):
    bio=io.BytesIO();img.save(bio,format="PNG",optimize=True);return bio.getvalue()

def extra_maps(im,idx):
    im=im.convert("RGBA")
    w,h=im.size
    height=im.convert("L")
    if idx in AI_GRAIN_TEX or CURRENT_CONTEXT=="wheel":
        grain=SEED.resize((w,h),Image.Resampling.BILINEAR)
        # Original macro height remains dominant, low-amplitude generated micrograin.
        orig=list(height.getdata());extra=list(grain.getdata())
        vals=[min(255,max(0,round(x*0.6+y*0.4))) for x,y in zip(orig,extra)]
    else: vals=list(height.getdata())
    normals=[]
    for y in range(h):
        for x in range(w):
            dx=(vals[y*w+max(0,x-1)]-vals[y*w+min(w-1,x+1)])/255.0
            dy=(vals[max(0,y-1)*w+x]-vals[min(h-1,y+1)*w+x])/255.0
            a,b=dx*.65,dy*.65
            z=1.0/math.sqrt(1+a*a+b*b)
            normals.append((int(127.5+127.5*a*z),int(127.5+127.5*b*z),int(127.5+127.5*z),255))
    norm=Image.new("RGBA",(w,h));norm.putdata(normals)
    # glTF: G=roughness, B=metallic. Black leather/trim is nonmetallic.
    rough=190 if idx==14 else 225 if idx==16 else 210
    mr=Image.new("RGBA",(w,h),(255,rough,0,255))
    ao=Image.new("RGBA",(w,h),(235,235,235,255))
    return norm,mr,ao

def append_maps(glb_path,parts):
    raw=glb_path.read_bytes()
    if raw[:4]!=b"glTF": raise ValueError("invalid GLB")
    jlen,jtyp=struct.unpack_from("<I4s",raw,12)
    if jtyp!=b"JSON":raise ValueError("missing JSON chunk")
    js=json.loads(raw[20:20+jlen])
    bp=20+jlen
    blen,btyp=struct.unpack_from("<I4s",raw,bp)
    if btyp!=b"BIN\x00":raise ValueError("missing BIN chunk")
    bb=bytearray(raw[bp+8:bp+8+blen])
    cache={}
    def append_png(img,key):
        if key in cache:return cache[key]
        payload=img_png(img)
        bb.extend(b"\x00"*((-len(bb))%4))
        start=len(bb);bb.extend(payload)
        vi=len(js["bufferViews"]);js["bufferViews"].append({"buffer":0,"byteOffset":start,"byteLength":len(payload)})
        ii=len(js["images"]);js["images"].append({"name":key,"mimeType":"image/png","bufferView":vi})
        ti=len(js["textures"]);js["textures"].append({"source":ii})
        cache[key]=ti
        return ti
    applied=[]
    for i,part in enumerate(parts):
        tex=part["tex_index"]
        if tex not in PBR_TEX and not (CURRENT_CONTEXT=="wheel" and tex==10):continue
        m=js["materials"][i]
        data=NORMAL_CACHE.get((CURRENT_CONTEXT,tex))
        if data is None:continue
        n,mr,ao=extra_maps(data,tex)
        for suffix,tex_img in (("Normal",n),("MetallicRoughness",mr),("AO",ao)):
            tex_img.save(TEX/("Daytona_%s_tex%02d_%s.png"%(CURRENT_CONTEXT,tex,suffix)),optimize=True)
        m["normalTexture"]={"index":append_png(n,f"tex{tex:02d}_normal"),"scale":0.25}
        m["pbrMetallicRoughness"]["metallicRoughnessTexture"]={"index":append_png(mr,f"tex{tex:02d}_roughness")}
        m["pbrMetallicRoughness"]["metallicFactor"]=0.0
        m["pbrMetallicRoughness"]["roughnessFactor"]=1.0
        m["occlusionTexture"]={"index":append_png(ao,f"tex{tex:02d}_AO"),"strength":0.35}
        applied.append(tex)
    js["buffers"][0]["byteLength"]=len(bb)
    js.setdefault("extras",{})["Daytona365Rework"]="source UV preserved, PBR tangent-space approximated, R26 runtime untested"
    j=json.dumps(js,separators=(",",":")).encode()
    j+=b" "*((-len(j))%4)
    bb.extend(b"\x00"*((-len(bb))%4))
    glb_path.write_bytes(struct.pack("<4sII",b"glTF",2,12+8+len(j)+8+len(bb))
                         +struct.pack("<I4s",len(j),b"JSON")+j
                         +struct.pack("<I4s",len(bb),b"BIN\x00")+bb)
    # Structural validation, no claim of actual on-device or OVC compatibility.
    b=glb_path.read_bytes()
    assert struct.unpack_from("<I",b,8)[0]==len(b)
    assert all("POSITION" in m["primitives"][0]["attributes"] for m in js["meshes"])
    assert len(js["materials"])==len(parts)
    return sorted(set(applied))

def export(src_obj,context,filename):
    global CURRENT_CONTEXT
    CURRENT_CONTEXT=context
    p=[normalize(q) for q in base.decode_object(ASSET,src_obj)]
    if context=="cockpit":
        p=[q for q in p if q["tex_index"] in (8,14,15,16,18,19)]
    counts=(sum(len(q["indices"])//3 for q in p),sum(len(q["vertices"]) for q in p))
    if context in ("car","cockpit"):
        p,flags=zip(*(safe_subdivide(x) for x in p))
        p=list(p); upgraded=sum(flags)
    else:upgraded=0
    output=OUT/filename
    # decode_dds is temporarily overridden for this isolated work product.
    stats=base.build_glb(ASSET,p,1,output)
    pbr=append_maps(output,p)
    return {"file":output.name,"bytes":output.stat().st_size,"source_object":src_obj,
            "triangles_before":counts[0],"triangles_after":sum(len(q["indices"])//3 for q in p),
            "subdivided_parts":upgraded,"source_vertex_count":counts[1],
            "meshes":stats["meshes"],"normal_and_roughness_texture_indices":pbr,
            "base_color_images":stats["textures"],"image_decode_notes":stats["imageNotes"]}

if __name__=="__main__":
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=EXPECTED_SHA:
        raise SystemExit("Fail closed: Daytona source SHA changed")
    ASSET=base.open_pmt(SOURCE)
    base.decode_dds=enhance_tex
    result={"source":SOURCE.name,"source_sha256":EXPECTED_SHA,
            "input_unmodified":True,"dino_unmodified":True,"warning":ENGINEERING_WARNING,
            "generated_grain":"AI-generated illustrated leather detail as a 32x32 grayscale high-pass seed; not full UV art",
            "car":export(0,"car","Daytona365_OriginalCar_CockpitPBR_v1.glb"),
            "cockpit":export(0,"cockpit","Daytona365_InteriorSurfaces_ONLY_v1.glb"),
            "wheel_local":export(22,"wheel","Daytona365_Steering_LOCAL_PBR_v1.glb")}
    (OUT/"MANIFEST.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))