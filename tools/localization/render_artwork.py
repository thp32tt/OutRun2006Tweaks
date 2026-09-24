#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def fit_font(draw, text, font_path, max_size, box_w, box_h, stroke_width):
    for size in range(max_size, 5, -1):
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        if bbox[2] - bbox[0] <= box_w and bbox[3] - bbox[1] <= box_h:
            return font, bbox
    raise RuntimeError(f"cannot fit text: {text}")

def render(spec, font_path, output_dir):
    width, height = spec["canvas"]
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    box = spec["box"]
    x, y, w, h = box
    stroke_width = int(spec.get("stroke_width", 2))
    max_font_size = int(spec.get("max_font_size", h))
    text = spec["korean"]

    font, bbox = fit_font(draw, text, font_path, max_font_size, w, h, stroke_width)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = x + (w - tw) / 2 - bbox[0]
    ty = y + (h - th) / 2 - bbox[1]

    shadow = spec.get("shadow")
    if shadow:
        dx, dy = shadow.get("offset", [2, 2])
        draw.text(
            (tx + dx, ty + dy), text, font=font,
            fill=tuple(shadow.get("fill", [0, 0, 0, 255])),
            stroke_width=stroke_width,
            stroke_fill=tuple(shadow.get("stroke_fill", [0, 0, 0, 255])),
        )

    draw.text(
        (tx, ty), text, font=font,
        fill=tuple(spec.get("fill", [255, 255, 255, 255])),
        stroke_width=stroke_width,
        stroke_fill=tuple(spec.get("stroke_fill", [18, 43, 104, 255])),
    )

    if spec.get("stored_mirrored_x", False):
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / spec["output_png"]
    image.save(out)
    return out

def main():
    ap = argparse.ArgumentParser(
        description="Render deterministic Korean UI proof overlays from JSONL specs."
    )
    ap.add_argument("spec_jsonl")
    ap.add_argument("--font", required=True, help="Path to a Hangul-capable TTF/TTC owned by the user")
    ap.add_argument("--output-dir", default="localization_work/rendered")
    ap.add_argument("--id", type=int, help="Render only one spec id")
    args = ap.parse_args()

    output_dir = Path(args.output_dir)
    count = 0
    with open(args.spec_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            spec = json.loads(line)
            if args.id is not None and spec["id"] != args.id:
                continue
            out = render(spec, args.font, output_dir)
            print(out)
            count += 1
    print(f"rendered={count}")

if __name__ == "__main__":
    main()
