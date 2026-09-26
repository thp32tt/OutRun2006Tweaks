#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, struct, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ANALYZER=HERE.parent/"analyze_outrun_exe.py"
spec=importlib.util.spec_from_file_location("or_analyzer", ANALYZER)
mod=importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

TARGETS={
  0x00049940:"Calc3D2D",
  0x000BA0E0:"dispMarkerCheck",
  0x00029580:"sprani_play_ae_auth_alpha",
  0x0002D280:"put_clip_sprite",
  0x0002CFE0:"put_sprite_ex",
  0x0002D0C0:"put_sprite_ex2",
  0x0002DD50:"SpriteNode_alloc_append",
  0x0002A0A0:"draw_sprite_plain",
  0x0002A3A0:"draw_sprite_custom_matrix",
  0x0002A800:"draw_sprite_custom_matrix_alt",
  0x0002C0F0:"draw_sprite_kind0_helper",
}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--exe",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    pe=mod.parse_pe(a.exe.read_bytes())
    textsec=pe.section(".text")
    assert textsec
    blob=pe.data[textsec.raw_pointer:textsec.raw_pointer+textsec.raw_size]
    rows=[]
    for i in range(0,len(blob)-5):
        if blob[i]!=0xE8: continue
        rel=struct.unpack_from("<i",blob,i+1)[0]
        call_rva=textsec.virtual_address+i
        next_va=pe.image_base+call_rva+5
        target_va=(next_va+rel)&0xffffffff
        target_rva=(target_va-pe.image_base)&0xffffffff
        if target_rva not in TARGETS: continue
        rows.append((call_rva,target_rva,TARGETS[target_rva],mod.guess_function_start(blob,textsec.virtual_address,i)))
    lines=["# R57 global xrefs for projected-marker pipeline","",
           "| Call RVA | Caller start guess | Target RVA | Target |",
           "|---:|---:|---:|---|"]
    for call,target,name,start in rows:
        lines.append(f"| 0x{call:08X} | {mod.hexrva(start)} | 0x{target:08X} | {name} |")
    lines += ["","## Counts",""]
    for target,name in TARGETS.items():
        c=sum(1 for r in rows if r[1]==target)
        lines.append(f"- {name} 0x{target:08X}: {c} direct CALL xrefs")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))
if __name__=="__main__":
    main()
