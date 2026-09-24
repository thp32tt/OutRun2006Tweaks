#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def text_bbox(draw, text, font, stroke_width, spacing):
    if "\n" in text:
        return draw.multiline_textbbox(
            (0, 0), text, font=font, stroke_width=stroke_width,
            spacing=spacing, align="center"
        )
    return draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)

def fit_font(draw, text, font_path, max_size, box_w, box_h, stroke_width, spacing):
    for size in range(max_size, 5, -1):
        font = ImageFont.truetype(font_path, size)
        bbox = text_bbox(draw, text, font, stroke_width, spacing)
        if bbox[2] - bbox[0] <= box_w and bbox[3] - bbox[1] <= box_h:
            return font, bbox
    raise RuntimeError(f"cannot fit text: {text}")

def draw_text(draw, pos, text, font, fill, stroke_width, stroke_fill, spacing):
    if "\n" in text:
        draw.multiline_text(
            pos, text, font=font, fill=fill, stroke_width=stroke_width,
            stroke_fill=stroke_fill, spacing=spacing, align="center"
        )
    else:
        draw.text(
            pos, text, font=font, fill=fill, stroke_width=stroke_width,
            stroke_fill=stroke_fill
        )

def render(spec, font_path, output_dir):
    width, height = spec["canvas"]
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    x, y, w, h = spec["box"]
    stroke_width = int(spec.get("stroke_width", 2))
    max_font_size = int(spec.get("max_font_size", h))
    spacing = int(spec.get("line_spacing", 2))
    text = spec["korean"]

    font, bbox = fit_font(
        draw, text, font_path, max_font_size, w, h, stroke_width, spacing
    )
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = x + (w - tw) / 2 - bbox[0]
    ty = y + (h - th) / 2 - bbox[1]

    shadow = spec.get("shadow")
    if shadow:
        dx, dy = shadow.get("offset", [2, 2])
        draw_text(
            draw, (tx + dx, ty + dy), text, font,
            tuple(shadow.get("fill", [0, 0, 0, 255])),
            stroke_width,
            tuple(shadow.get("stroke_fill", [0, 0, 0, 255])),
            spacing
        )

    draw_text(
        draw, (tx, ty), text, font,
        tuple(spec.get("fill", [255, 255, 255, 255])),
        stroke_width,
        tuple(spec.get("stroke_fill", [18, 43, 104, 255])),
        spacing
    )

    if spec.get("stored_mirrored_x", False):
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if spec.get("stored_flip_y", False):
        image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if spec.get("stored_rotate_180", False):
        image = image.transpose(Image.Transpose.ROTATE_180)

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
