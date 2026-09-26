#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM

HERE=Path(__file__).resolve().parent
ANALYZER=HERE.parent/"analyze_outrun_exe.py"
spec=importlib.util.spec_from_file_location("or_analyzer", ANALYZER)
mod=importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

RANGES=[
 ("Calc3D2D",0x049940,0x320),
 ("sprani_play_ae_auth_alpha",0x029580,0x700),
 ("put_clip_sprite_and_queue_entry",0x02D280,0xB00),
 ("DispRank",0x0B9E00,0x380),
 ("RankMarker_sub_4BAD20",0x0BAD20,0x700),
 ("RankSibling_BBBxx",0x0BBB00,0x380),
 ("RankSibling_BBDxx_BC4xx",0x0BBD80,0x780),
]
KNOWN=dict(mod.KNOWN_TARGETS)
for rva,label in mod.KNOWN_CALL_SITES.items():
    KNOWN[rva]=label

def fmt_target(ins):
    if ins.mnemonic!="call" or not ins.operands or ins.operands[0].type!=X86_OP_IMM:
        return ""
    va=ins.operands[0].imm & 0xffffffff
    rva=(va-0x00400000)&0xffffffff
    label=KNOWN.get(rva,"")
    return f" ; target_rva=0x{rva:08X}" + (f" {label}" if label else "")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--exe",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    pe=mod.parse_pe(a.exe.read_bytes())
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    out=["# R57 targeted deep disassembly","",f"EXE image base: 0x{pe.image_base:08X}",""]
    for name,rva,size in RANGES:
        blob=pe.bytes_at_rva(rva,size)
        out += [f"## {name} RVA 0x{rva:08X}..0x{rva+size:08X}","", "\`\`\`asm"]
        for ins in md.disasm(blob, pe.image_base+rva):
            irva=ins.address-pe.image_base
            mark=""
            if irva in mod.KNOWN_CALL_SITES: mark=f" ; *** {mod.KNOWN_CALL_SITES[irva]} ***"
            out.append(f"{irva:08X}: {ins.mnemonic:<8} {ins.op_str}{fmt_target(ins)}{mark}")
        out += ["\`\`\`",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(out),encoding="utf-8")
    print(a.out)
if __name__=="__main__":
    main()
