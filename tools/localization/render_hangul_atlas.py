#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def main():
    ap=argparse.ArgumentParser(description="Render compact Hangul glyph atlas pages from the stable manifest.")
    ap.add_argument("manifest_json")
    ap.add_argument("--font", required=True, help="Hangul-capable TTF/TTC owned/licensed by the developer")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--cell", type=int, default=64)
    ap.add_argument("--font-size", type=int, default=48)
    ap.add_argument("--stroke-width", type=int, default=0)
    args=ap.parse_args()

    manifest=json.loads(Path(args.manifest_json).read_text(encoding="utf-8"))
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    cell=args.cell
    page_size=cell*16
    pages=[
        Image.new("RGBA",(page_size,page_size),(0,0,0,0))
        for _ in range(manifest["page_count"])
    ]
    draws=[ImageDraw.Draw(p) for p in pages]
    font=ImageFont.truetype(args.font,args.font_size)

    metrics=[]
    for entry in manifest["entries"]:
        ch=entry["char"]; page=entry["page"]; col=entry["col"]; row=entry["row"]
        x0=col*cell; y0=row*cell
        bbox=draws[page].textbbox((0,0),ch,font=font,stroke_width=args.stroke_width)
        w=bbox[2]-bbox[0]; h=bbox[3]-bbox[1]
        tx=x0+(cell-w)/2-bbox[0]
        ty=y0+(cell-h)/2-bbox[1]
        draws[page].text(
            (tx,ty),ch,font=font,fill=(255,255,255,255),
            stroke_width=args.stroke_width,stroke_fill=(255,255,255,255)
        )
        advance=float(draws[page].textlength(ch,font=font))
        metrics.append({
            "index":entry["index"],"char":ch,"codepoint":entry["codepoint"],
            "page":page,"cell":entry["cell"],"row":row,"col":col,
            "advance_px":round(advance,4),
            "bbox_px":[int(v) for v in bbox],
            "cell_px":cell
        })

    for i,page in enumerate(pages):
        page.save(out/f"hangul_page_{i}.png")

    result={
        "schema_version":1,
        "font_source":"external-not-distributed",
        "cell_px":cell,
        "page_px":[page_size,page_size],
        "font_size_px":args.font_size,
        "stroke_width":args.stroke_width,
        "glyph_count":len(metrics),
        "metrics":metrics
    }
    (out/"hangul_metrics.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    print(f"pages={len(pages)} glyphs={len(metrics)} page={page_size}x{page_size}")

if __name__=="__main__":
    main()
