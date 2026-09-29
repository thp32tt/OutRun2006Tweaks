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
 ("kind0_draw_A0A0",0x02A000,0xA00),
 ("kind0_alt_C0F0",0x02C000,0x260),
 ("sprite_queue_kind_split",0x02D720,0x5B0),
 ("sprite_core_28A10",0x028A00,0x700),
]
KNOWN=dict(mod.KNOWN_TARGETS)
for rva,label in mod.KNOWN_CALL_SITES.items(): KNOWN[rva]=label

def target(ins):
    if ins.mnemonic!="call" or not ins.operands or ins.operands[0].type!=X86_OP_IMM:
        return ""
    va=ins.operands[0].imm & 0xffffffff
    rva=(va-0x00400000)&0xffffffff
    return f" ; target_rva=0x{rva:08X}" + (f" {KNOWN[rva]}" if rva in KNOWN else "")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--exe",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    pe=mod.parse_pe(a.exe.read_bytes())
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    out=["# R60 kind-0 sprite path disassembly",""]
    for name,rva,size in RANGES:
        out += [f"## {name} RVA 0x{rva:08X}..0x{rva+size:08X}","", "```asm"]
        for ins in md.disasm(pe.bytes_at_rva(rva,size), pe.image_base+rva):
            irva=ins.address-pe.image_base
            out.append(f"{irva:08X}: {ins.mnemonic:<8} {ins.op_str}{target(ins)}")
        out += ["```",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(out),encoding="utf-8")
if __name__=="__main__": main()
