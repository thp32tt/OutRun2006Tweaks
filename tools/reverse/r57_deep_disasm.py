#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

HERE=Path(__file__).resolve().parent
ANALYZER=HERE.parent/"analyze_outrun_exe.py"
spec=importlib.util.spec_from_file_location("or_analyzer", ANALYZER)
mod=importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

RANGES=[
 ("mxPushLoadMatrix",0x009F90,0x190),
 ("matrix_helper_A170",0x00A170,0x110),
 ("mxCalcPoint",0x00A7D0,0x130),
 ("Calc3D2D",0x049940,0x320),
 ("dispMarkerCheck",0x0BA0E0,0x190),
 ("rank_helper_BABF0",0x0BABF0,0x130),
 ("sprani_core_28A10",0x028A10,0x390),
 ("sprite_batch_begin_end",0x029B00,0x560),
 ("sprani_core_28AF0",0x028AF0,0x390),
 ("sprani_play_ae_auth_alpha",0x029580,0x700),
 ("draw_sprite_plain",0x02A0A0,0x250),
 ("draw_sprite_state_2A2B0",0x02A2B0,0x110),
 ("draw_sprite_custom_matrix",0x02A3A0,0x4C0),
 ("draw_sprite_custom_matrix_alt",0x02A800,0x390),
 ("draw_sprite_kind0_helper",0x02C0F0,0x330),
 ("put_sprite_ex",0x02CFE0,0x2A0),
 ("put_clip_sprite_and_queue_entry",0x02D280,0xD80),
 ("DispRank",0x0B9E00,0x380),
 ("RankPre_BA9xx_BACxx",0x0BA900,0x420),
 ("RankMarker_sub_4BAD20",0x0BAD20,0x700),
 ("RankSibling_BB3xx_BB8xx",0x0BB300,0x600),
 ("RankSibling_BBBxx",0x0BBB00,0x380),
 ("RankSibling_BBDxx_BC4xx",0x0BBD80,0x780),
 ("Third_dispMarkerCheck_caller",0x0BE980,0x280),
]
KNOWN=dict(mod.KNOWN_TARGETS)\nKNOWN.update({\n  0x02D0C0: 'put_sprite_ex2_kind1',\n  0x0295D0: 'sprani_projected_world_helper_295D0',\n  0x028A10: 'sprani_core_28A10',\n  0x028AF0: 'sprani_core_28AF0',\n  0x028EA0: 'sprani_build_args2_28EA0',\n  0x029460: 'sprani_emit_29460',\n  0x02A0A0: 'draw_sprite_plain',\n  0x02A3A0: 'draw_sprite_custom_matrix',\n  0x02A800: 'draw_sprite_custom_matrix_alt',\n  0x02C0F0: 'draw_sprite_kind0_helper',\n  0x02DDF0: 'sprite_texture_metrics_2DDF0',\n  0x029C60: 'sprite_batch_begin_29C60',\n})
for rva,label in mod.KNOWN_CALL_SITES.items():
    KNOWN[rva]=label

def fmt_target(ins):
    if ins.mnemonic!="call" or not ins.operands or ins.operands[0].type!=X86_OP_IMM:
        return ""
    va=ins.operands[0].imm & 0xffffffff
    rva=(va-0x00400000)&0xffffffff
    label=KNOWN.get(rva,"")
    return f" ; target_rva=0x{rva:08X}" + (f" {label}" if label else "")

WATCH_ABS = {\n    0x0095D8A0: 'renderer_projection',\n    0x0089B564: 'sprite_matrix_stack_ptr',\n    0x0089B568: 'sprite_matrix_stack_depth',\n    0x00956C00: 'sprite_priority_roots',\n    0x00986B28: 'sprani_deferred_flag',\n    0x00986B30: 'sprani_deferred_index',\n}\n\ndef full_text_xrefs(pe, md):\n    text_section = pe.section('.text')\n    if not text_section:\n        return [], []\n    blob = pe.data[text_section.raw_pointer:text_section.raw_pointer + text_section.raw_size]\n    calls, datarefs = [], []\n    for ins in md.disasm(blob, pe.image_base + text_section.virtual_address):\n        irva = ins.address - pe.image_base\n        if ins.mnemonic == 'call' and ins.operands and ins.operands[0].type == X86_OP_IMM:\n            trva = ((ins.operands[0].imm & 0xffffffff) - pe.image_base) & 0xffffffff\n            if trva in KNOWN:\n                frva = mod.guess_function_start(blob, text_section.virtual_address, irva - text_section.virtual_address)\n                calls.append((irva, trva, KNOWN[trva], frva))\n        for op in ins.operands:\n            if op.type == X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:\n                va = op.mem.disp & 0xffffffff\n                if va in WATCH_ABS:\n                    frva = mod.guess_function_start(blob, text_section.virtual_address, irva - text_section.virtual_address)\n                    datarefs.append((irva, va, WATCH_ABS[va], frva))\n    return calls, datarefs\n\ndef main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--exe",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    pe=mod.parse_pe(a.exe.read_bytes())
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    out=["# R57 targeted deep disassembly","",f"EXE image base: 0x{pe.image_base:08X}",""]\n    calls, datarefs = full_text_xrefs(pe, md)\n    out += ["## Full-text direct call cross-references","",\n            "| Call RVA | Function start guess | Target RVA | Target |",\n            "|---:|---:|---:|---|"]\n    for crva,trva,label,frva in calls:\n        fr = "-" if frva is None else f"0x{frva:08X}"\n        out.append(f"| 0x{crva:08X} | {fr} | 0x{trva:08X} | {label} |")\n    out += ["","## Full-text watched data references","",\n            "| Ref RVA | Function start guess | Absolute VA | Meaning |",\n            "|---:|---:|---:|---|"]\n    for rrva,va,label,frva in datarefs:\n        fr = "-" if frva is None else f"0x{frva:08X}"\n        out.append(f"| 0x{rrva:08X} | {fr} | 0x{va:08X} | {label} |")\n    out += [""]
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
