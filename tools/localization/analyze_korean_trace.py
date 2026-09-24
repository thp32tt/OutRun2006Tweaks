#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path

RE_RESOLVER = re.compile(
    r"KoreanLocalizationTrace: text_id=(\d+) original='(.*?)' returned='(.*?)' proof_override=(true|false)",
)
RE_WIDTH = re.compile(
    r"KoreanK3Trace: width_text='(.*?)' bytes=(\d+) high_bit=(true|false)",
)
RE_GLYPH = re.compile(
    r"KoreanK3Trace: glyph_code=0x([0-9A-Fa-f]{2}) ascii_printable=(true|false)",
)
RE_FONT = re.compile(
    r"KoreanK3Trace: font_state handle=0x([0-9A-Fa-f]{8}) texture=(\S+) kerning=(\S+) "
    r"tex=(\d+)x(\d+) cell=(-?\d+)x(-?\d+) cursor=\((-?\d+), (-?\d+)\) "
    r"scale=\(([-+0-9.eE]+), ([-+0-9.eE]+)\) color=0x([0-9A-Fa-f]{8}) "
    r"layer=(\d+) base_code=(\d+) flags=0x([0-9A-Fa-f]{8}) "
    r"spacing=([-+0-9.eE]+) line_advance=([-+0-9.eE]+)"
)

def main():
    ap=argparse.ArgumentParser(description="Analyze OutRun Korean localization K1/K2/K3 trace logs.")
    ap.add_argument("log")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--markdown", dest="md_out")
    args=ap.parse_args()

    text=Path(args.log).read_text(encoding="utf-8", errors="replace")
    resolver=[]
    widths=[]
    glyphs=[]
    fonts=[]

    for line in text.splitlines():
        m=RE_RESOLVER.search(line)
        if m:
            resolver.append({
                "id":int(m.group(1)),
                "original":m.group(2),
                "returned":m.group(3),
                "proof_override":m.group(4)=="true",
            })
            continue
        m=RE_WIDTH.search(line)
        if m:
            widths.append({
                "text":m.group(1),
                "bytes":int(m.group(2)),
                "high_bit":m.group(3)=="true",
            })
            continue
        m=RE_GLYPH.search(line)
        if m:
            glyphs.append({
                "code":int(m.group(1),16),
                "hex":"0x"+m.group(1).upper(),
                "ascii_printable":m.group(2)=="true",
            })
            continue
        m=RE_FONT.search(line)
        if m:
            fonts.append({
                "handle":int(m.group(1),16),
                "handle_hex":"0x"+m.group(1).upper(),
                "texture_ptr":m.group(2),
                "kerning_ptr":m.group(3),
                "texture_size":[int(m.group(4)),int(m.group(5))],
                "cell":[int(m.group(6)),int(m.group(7))],
                "cursor":[int(m.group(8)),int(m.group(9))],
                "scale":[float(m.group(10)),float(m.group(11))],
                "color":"0x"+m.group(12).upper(),
                "layer":int(m.group(13)),
                "base_code":int(m.group(14)),
                "flags":"0x"+m.group(15).upper(),
                "letter_spacing":float(m.group(16)),
                "line_advance":float(m.group(17)),
            })

    ids=sorted({x["id"] for x in resolver})
    result={
        "schema_version":1,
        "source_log":str(args.log),
        "resolver":{
            "records":len(resolver),
            "unique_ids":ids,
            "unique_id_count":len(ids),
            "proof_override_seen":any(x["proof_override"] for x in resolver),
            "id0":next((x for x in resolver if x["id"]==0),None),
            "context_ids":{
                str(i):next((x for x in resolver if x["id"]==i),None)
                for i in (96,97,279,280)
            },
        },
        "k3":{
            "width_records":len(widths),
            "widths":widths,
            "high_bit_width_count":sum(1 for x in widths if x["high_bit"]),
            "glyph_codes":glyphs,
            "font_states":fonts,
            "font_handles":sorted({x["handle"] for x in fonts}),
        },
    }

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
        )

    lines=[
        "# Korean Localization Trace Analysis",
        "",
        f"- resolver unique IDs: **{len(ids)}**",
        f"- K2 proof override seen: **{result['resolver']['proof_override_seen']}**",
        f"- K3 width strings: **{len(widths)}**",
        f"- K3 high-bit width strings: **{result['k3']['high_bit_width_count']}**",
        f"- K3 unique glyph codes: **{len(glyphs)}**",
        f"- K3 font-state records: **{len(fonts)}**",
        f"- K3 font handles: **{', '.join(str(x) for x in result['k3']['font_handles']) or 'none'}**",
        "",
        "## Context-sensitive IDs",
    ]
    for i in (96,97,279,280):
        x=result["resolver"]["context_ids"][str(i)]
        lines.append(f"- {i}: {json.dumps(x,ensure_ascii=False) if x else 'not observed'}")
    lines += ["", "## Font states"]
    for x in fonts:
        lines.append(
            f"- handle {x['handle']} ({x['handle_hex']}): tex {x['texture_size'][0]}x{x['texture_size'][1]}, "
            f"cell {x['cell'][0]}x{x['cell'][1]}, base {x['base_code']}, "
            f"scale {x['scale'][0]:.4f}/{x['scale'][1]:.4f}, spacing {x['letter_spacing']:.4f}"
        )
    md="\n".join(lines)+"\n"
    if args.md_out:
        Path(args.md_out).write_text(md,encoding="utf-8")
    print(md,end="")

if __name__=="__main__":
    main()
