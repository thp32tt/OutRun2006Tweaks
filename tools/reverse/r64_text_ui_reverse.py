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

TARGETS={
    0x28E81:"put_sprite_ex2_internal_return",
    0x2C9DB:"put_sprite_ex_internal_return",
    0x2CFE0:"put_sprite_ex",
    0x2D0C0:"put_sprite_ex2",
    0x2A530:"sprani_play_ae_auth_alpha",
}
RANGES=[
    ("text_helper_28",0x28600,0x1200),
    ("sprite_helper_2c",0x2C300,0x1000),
    ("sprite_helper_2d",0x2CF00,0x900),
    ("menu_ui_44",0x44000,0x3000),
    ("goal_ui_7b",0x7B000,0x5000),
]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--exe",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    pe=mod.parse_pe(a.exe.read_bytes())
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    out=["# R64 text/UI producer reverse",""]
    refs={k:[] for k in TARGETS}
    # scan .text for direct calls/jumps into target funcs/near internal returns
    text=pe.section(".text")
    if text:
        start=text.virtual_address
        blob=pe.bytes_at_rva(start,text.virtual_size)
        for ins in md.disasm(blob,pe.image_base+start):
            if ins.mnemonic not in ("call","jmp") or not ins.operands or ins.operands[0].type!=X86_OP_IMM:
                continue
            rva=(ins.operands[0].imm-pe.image_base)&0xffffffff
            if rva in TARGETS:
                refs[rva].append(ins.address-pe.image_base)
    for t,label in TARGETS.items():
        out += [f"## Xrefs to {label} RVA 0x{t:08X}",""]
        out += [f"- 0x{x:08X}" for x in refs[t]]
        out += [""]
    for name,rva,size in RANGES:
        out += [f"## {name} RVA 0x{rva:08X}..0x{rva+size:08X}","", "```asm"]
        for ins in md.disasm(pe.bytes_at_rva(rva,size), pe.image_base+rva):
            irva=ins.address-pe.image_base
            extra=""
            if ins.mnemonic in ("call","jmp") and ins.operands and ins.operands[0].type==X86_OP_IMM:
                trva=(ins.operands[0].imm-pe.image_base)&0xffffffff
                if trva in TARGETS:
                    extra=f" ; -> {TARGETS[trva]}"
            out.append(f"{irva:08X}: {ins.mnemonic:<8} {ins.op_str}{extra}")
        out += ["```",""]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(out),encoding="utf-8")
if __name__=="__main__": main()
