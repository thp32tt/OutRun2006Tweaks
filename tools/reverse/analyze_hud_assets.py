#!/usr/bin/env python3
"""Read-only HUD/Sprite/Sprani asset analyzer for canonical OutRun 2006 C2C."""
from __future__ import annotations
import argparse, hashlib, json, re, struct, zipfile, zlib
from pathlib import Path

CANON="68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3"
TABLES={"E":0x639CB8,"F":0x639DE4,"G":0x639F10,"I":0x63A03C,"S":0x63A168}
SLOTS=75
MAX_INFLATED=64*1024*1024

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def u16(b,o):return struct.unpack_from("<H",b,o)[0]
def u32(b,o):return struct.unpack_from("<I",b,o)[0]

class PE:
    def __init__(self,data:bytes):
        self.data=data
        pe=u32(data,0x3c)
        if data[pe:pe+4]!=b"PE\0\0":raise ValueError("bad PE")
        self.nsec=u16(data,pe+6)
        opt=pe+24
        if u16(data,opt)!=0x10b:raise ValueError("expected PE32")
        self.image_base=u32(data,opt+28)
        opt_size=u16(data,pe+20)
        sec=opt+opt_size
        self.sections=[]
        for i in range(self.nsec):
            o=sec+i*40
            name=data[o:o+8].split(b"\0",1)[0].decode("ascii","replace")
            vsize=u32(data,o+8); va=u32(data,o+12)
            rsize=u32(data,o+16); raw=u32(data,o+20)
            self.sections.append((name,va,max(vsize,rsize),raw,rsize))
    def rva_off(self,rva:int)->int:
        for _,va,size,raw,rsize in self.sections:
            if va<=rva<va+size:
                d=rva-va
                if d>=rsize:raise ValueError(f"RVA {rva:#x} not file-backed")
                return raw+d
        raise ValueError(f"RVA {rva:#x} not mapped")
    def va_off(self,va:int)->int:return self.rva_off(va-self.image_base)
    def dword_va(self,va:int)->int:return u32(self.data,self.va_off(va))
    def cstr_va(self,va:int)->str:
        o=self.va_off(va); e=self.data.find(b"\0",o)
        if e<0:raise ValueError("unterminated cstr")
        return self.data[o:e].decode("ascii","replace")

def inflate(raw:bytes)->bytes:
    o=zlib.decompressobj()
    out=o.decompress(raw,MAX_INFLATED+1)+o.flush()
    if len(out)>MAX_INFLATED:raise ValueError("inflated asset too large")
    if o.unused_data:raise ValueError("trailing zlib data")
    return out

def parse_xst(data:bytes)->dict:
    base=0; sysmem=vidmem=None
    if len(data)>=8:
        s,v=struct.unpack_from("<II",data,0)
        if s+v+8==len(data):
            base=8;sysmem=s;vidmem=v
    if base+32>len(data):raise ValueError("short XST")
    flag,tex_ofs,ntex,dummy,ndsp,dsptbl,nspr,sprtbl=struct.unpack_from("<8I",data,base)
    if max(ntex,ndsp,nspr)>100000:raise ValueError("unreasonable XST counts")
    standard=True
    texture_indices=[]
    if base+sprtbl+nspr*28<=len(data):
        for i in range(nspr):
            ti=u32(data,base+sprtbl+i*28)
            texture_indices.append(ti)
            if ntex and ti>=ntex:standard=False
    return {
        "size":len(data),"sysmem":sysmem,"vidmem":vidmem,
        "textureCount":ntex,"displayTableCount":ndsp,"spriteCount":nspr,
        "standardSpriteTextureIndex":standard,
        "maxSpriteTextureIndex":max(texture_indices) if texture_indices else None,
        "sha256":sha(data)
    }

def parse_sprani(data:bytes)->dict:
    if len(data)<12:raise ValueError("short Sprani")
    payload,first=struct.unpack_from("<II",data,0)
    if payload+4!=len(data):raise ValueError("Sprani payload mismatch")
    if first<8 or first%4:raise ValueError("bad first record offset")
    count=first//4-1
    offs=[u32(data,4+i*4) for i in range(count)]
    if not all(first<=x<len(data) for x in offs):raise ValueError("Sprani offset OOB")
    if any(a>b for a,b in zip(offs,offs[1:])):raise ValueError("Sprani offsets nonmonotonic")
    return {"size":len(data),"animationCount":count,"firstRecordOffset":first,"sha256":sha(data)}

def zip_index(path:Path):
    z=zipfile.ZipFile(path)
    names={n.lower():n for n in z.namelist() if not n.endswith("/")}
    basenames={}
    for n in z.namelist():
        if n.endswith("/"):continue
        basenames.setdefault(Path(n).name.lower(),[]).append(n)
    return z,names,basenames

def find_by_basename(z,idx,name):
    hits=idx.get(name.lower(),[])
    if len(hits)!=1:return None
    return hits[0]

def sprani_basename_from_xst(xstbase:str)->str|None:
    low=xstbase.lower()
    if not low.startswith("spr_") or not low.endswith(".sz"):return None
    stem=xstbase[:-3]
    stem=re.sub(r"_[EFGIS]xst$","",stem,flags=re.I)
    stem=re.sub(r"_xst$","",stem,flags=re.I)
    if stem.lower().startswith("spr_sprani_"):
        return "ani_SPRANI_"+stem[len("spr_sprani_"):]+".sz"
    if stem.lower().startswith("spr_meter_"):
        return "ani_SPRANI_"+stem[len("spr_"):]+".sz"
    return None

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--exe",required=True,type=Path)
    ap.add_argument("--sprite-zip",required=True,type=Path)
    ap.add_argument("--sprani-zip",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args()

    exe=args.exe.read_bytes()
    digest=sha(exe)
    if digest!=CANON:raise SystemExit(f"non-canonical EXE SHA256 {digest}")
    pe=PE(exe)
    sz,snames,sbase=zip_index(args.sprite_zip)
    az,anames,abase=zip_index(args.sprani_zip)
    try:
        tables={}
        for lang,tva in TABLES.items():
            rows=[]
            for slot in range(SLOTS):
                ptr=pe.dword_va(tva+slot*4)
                path=pe.cstr_va(ptr) if ptr else None
                rows.append(path)
            tables[lang]=rows

        outrows=[]
        for slot in range(SLOTS):
            paths={lang:tables[lang][slot] for lang in TABLES}
            epath=paths["E"]
            rec={"slot":slot,"paths":paths,"nonNull":bool(epath)}
            if not epath:
                outrows.append(rec);continue
            bas=Path(epath.replace("\\","/")).name
            zn=find_by_basename(sz,sbase,bas)
            if zn:
                data=inflate(sz.read(zn))
                rec["xst"]={"zipPath":zn,**parse_xst(data)}
                sprbase=sprani_basename_from_xst(bas)
                if sprbase:
                    an=find_by_basename(az,abase,sprbase)
                    if an:
                        adata=inflate(az.read(an))
                        rec["sprani"]={"zipPath":an,**parse_sprani(adata)}
            rec["localizedPathVariant"]=len({p for p in paths.values() if p})>1
            outrows.append(rec)

        report={
            "schema":"outrun-hud-xst-analysis-v1",
            "canonicalExeSha256":digest,
            "tables":{"slotCount":SLOTS,**{k:f"0x{v:08X}" for k,v in TABLES.items()}},
            "summary":{
                "englishNonNull":sum(1 for x in outrows if x["nonNull"]),
                "localizedPathVariantSlots":sum(1 for x in outrows if x.get("localizedPathVariant")),
                "xstParsed":sum(1 for x in outrows if "xst" in x),
                "spraniParsed":sum(1 for x in outrows if "sprani" in x)
            },
            "packedIdentity":{
                "spriteResolverVa":"0x0042DDF0",
                "spriteFormula":"xstSet=packed>>16; spriteIndex=packed&0xFFFF",
                "spraniResolverVa":"0x00428A10",
                "spraniFormula":"spraniSet=id>>16; animIndex=id&0xFFFF",
                "spraniChildSpriteCall":"0x00428C0F -> 0x0042DDF0"
            },
            "slots":outrows
        }
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report["summary"],ensure_ascii=False))
        print(args.output)
    finally:
        sz.close();az.close()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
