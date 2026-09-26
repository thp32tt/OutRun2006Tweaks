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

# Absolute VAs referenced by Calc3D2D / rank producers.
FLOAT_VAS={
    0x0062806C:"Calc3D2D focal/half-width constant",
    0x006281CC:"rank screen Y center/reference",
    0x006281C8:"rank screen X offset/reference",
    0x005B0424:"rank vertical glyph offset",
    0x006281F0:"near-zero epsilon",
    0x006280F8:"rank depth/alpha scale A",
    0x005C6F98:"rank depth/alpha scale B",
    0x005C6F9C:"rank Y clamp/reference",
    0x005C6F90:"rank X clamp low",
    0x005B0304:"rank X clamp high",
}

def f32(pe,va):
    rva=va-pe.image_base
    b=pe.bytes_at_rva(rva,4)
    return None if len(b)!=4 else struct.unpack("<f",b)[0]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--exe",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    pe=mod.parse_pe(a.exe.read_bytes())
    lines=["# R57 Calc3D2D inverse-projection facts","",
           "Canonical formula recovered from RVA 0x49940:","",
           "- transformed = mxCalcPoint(currentMatrix, input)",
           "- factor = K / (-transformed.z)",
           "- out.x = factor * a1 * transformed.x",
           "- out.y = factor * a2 * transformed.y",
           "- out.z = transformed.z",
           "",
           "Therefore, for nonzero K/a1/a2:","",
           "- transformed.x = out.x * (-out.z) / (K * a1)",
           "- transformed.y = out.y * (-out.z) / (K * a2)",
           "- transformed.z = out.z",
           "",
           "This is sufficient to reconstruct the pre-perspective camera/current-matrix point from the projected marker output without retaining the original vehicle point.",
           "",
           "## Referenced constants","",
           "| VA | RVA | float | meaning |",
           "|---:|---:|---:|---|"]
    for va,desc in FLOAT_VAS.items():
        val=f32(pe,va)
        lines.append(f"| 0x{va:08X} | 0x{va-pe.image_base:08X} | {val!r} | {desc} |")
    lines += ["",
      "## Candidate implementation shortcut","",
      "Capture only the exact projected-rank Calc3D2D result (screen x/y + preserved z), a1/a2, producer id and frame generation. When the corresponding SpriteNode is queued, store its glyph offset from the projected marker anchor. During stereo replay, reconstruct the camera/current-matrix point with the equations above, project the anchor once per eye, then translate the existing sprite quad by eyeAnchor - originalAnchor. Texture, animation, alpha, scale and multi-digit layout remain owned by the original game.",
      "",
      "Because OutRun's live render camera is already head-synchronised during gameplay, first test relative-eye/IPD reprojection without applying common head rotation a second time. This mirrors the existing R30 CPU-projected world-effect path."
    ]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))
if __name__=="__main__":
    main()
