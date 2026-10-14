#!/usr/bin/env python3
"""C salvage: SHA-pinned lettering salvage and native TEST_ONLY DDS assembly.

Never invokes image generation or grants C1/C3/game approval. Requires a reviewed
source-coordinate removal mask and a separate generated-text mask.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops

SCHEMA = "outrun-c-salvage-v1"
STATE = "C_DDS_TEST_ONLY_REQUIRES_C1_C3_GAME"
BGRA_MASKS = (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def checked(root, ref):
    if not isinstance(ref, dict) or not ref.get("path") or not ref.get("sha256"):
        raise ValueError("All inputs need {path, sha256}")
    p = (root / ref["path"]).resolve()
    if not p.is_relative_to(root) or not p.is_file():
        raise ValueError("Unsafe/missing source path")
    blob = p.read_bytes()
    if digest(blob) != ref["sha256"]:
        raise ValueError("Input SHA256 mismatch: " + ref["path"])
    return blob


def png(root, ref, mode):
    blob = checked(root, ref)
    with Image.open(io.BytesIO(blob)) as im:
        if im.format != "PNG" or im.mode != mode:
            raise ValueError("Expected native PNG in " + mode)
        return im.copy()


def binary_mask(root, ref, size):
    im = png(root, ref, "L")
    if im.size != size:
        raise ValueError("Mask dimensions mismatch")
    array = np.asarray(im)
    if not np.isin(array, (0, 255)).all():
        raise ValueError("Mask must be binary 0/255")
    return im, array != 0


def rgba_equal_outside(lhs, rhs, mask):
    diff = np.any(np.asarray(lhs) != np.asarray(rhs), axis=2)
    return int(np.count_nonzero(diff & ~mask))


def compose(root, manifest, out):
    if manifest.get("schema") != SCHEMA:
        raise ValueError("Unsupported manifest version")
    if manifest.get("orientation") not in ("IDENTITY", "FLIP_Y"):
        raise ValueError("Mixed/unknown source sprite transforms require manual ROI handling")
    if manifest.get("translation_verified") is not True:
        raise ValueError("Korean translation must be manually verified")
    src_dds = checked(root, manifest["source_dds"])
    if src_dds[:4] != b"DDS " or len(src_dds) < 128:
        raise ValueError("Not a canonical DDS")
    with Image.open(io.BytesIO(src_dds)) as im:
        source_native = im.convert("RGBA")
    source = source_native.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if manifest["orientation"] == "FLIP_Y" else source_native.copy()
    source_png = png(root, manifest["source_png"], "RGBA")
    if source_png.size != source.size:
        raise ValueError("Native readable input size differs from DDS")
    # Canonical decode is truth. A different input PNG cannot be fitted silently.
    if not np.array_equal(np.asarray(source_png), np.asarray(source)):
        raise ValueError("Readable PNG differs from pinned canonical DDS decode")
    size = source.size
    removal, removal_arr = binary_mask(root, manifest["removal_mask"], size)
    protected, protected_arr = binary_mask(root, manifest["protected_mask"], size)
    edit, edit_arr = binary_mask(root, manifest["edit_mask"], size)
    if not removal_arr.any() or not edit_arr.any() or np.any(removal_arr & protected_arr):
        raise ValueError("Empty/conflicting native edit/removal/protected masks")
    if np.any(removal_arr & ~edit_arr):
        raise ValueError("Removal mask exceeds approved edit area")

    generated = png(root, manifest["generated_png"], "RGBA")
    generated_mask, generated_mask_arr = binary_mask(root, manifest["generated_text_mask"], generated.size)
    if not generated_mask_arr.any():
        raise ValueError("No manually isolated Korean glyph/effect pixels")
    alpha = ImageChops.multiply(generated.getchannel("A"), generated_mask)
    isolated = generated.copy()
    isolated.putalpha(alpha)
    bounds = isolated.getbbox()
    if bounds is None:
        raise ValueError("Generated mask yielded no visible alpha")
    single_phrase = isolated.crop(bounds)

    box = manifest.get("cell_bbox")
    if not isinstance(box, list) or len(box) != 4 or not all(isinstance(x, int) for x in box):
        raise ValueError("Require integer verified native cell_bbox [left,top,right,bottom]")
    x0, y0, x1, y1 = box
    if x0 < 0 or y0 < 0 or x1 > size[0] or y1 > size[1] or x1 <= x0 or y1 <= y0:
        raise ValueError("Cell bounds outside canonical native image")
    if single_phrase.width > x1-x0 or single_phrase.height > y1-y0:
        single_phrase.thumbnail((x1-x0, y1-y0), Image.Resampling.LANCZOS)
    paste_x = x0 + (x1-x0-single_phrase.width)//2
    paste_y = y0 + (y1-y0-single_phrase.height)//2
    lettering = Image.new("RGBA", size)
    lettering.alpha_composite(single_phrase, (paste_x, paste_y))
    lettering_arr = np.asarray(lettering)
    visible = lettering_arr[:, :, 3] > 0
    if np.any(visible & ~edit_arr) or np.any(visible & protected_arr):
        raise ValueError("Korean pixels outside edit/over protected art")

    if manifest.get("clean_png"):
        clean = png(root, manifest["clean_png"], "RGBA")
        clean_origin = "SOURCE_PSD_OR_APPROVED_EXTERNAL_UNVERIFIED_BY_THIS_TOOL"
    elif manifest.get("clean_method") == "TRANSPARENT_MASK_TEST_ONLY":
        # This erases source glyphs/FX; it does NOT hallucinate an opaque background.
        source_pixels = np.asarray(source).copy()
        source_pixels[removal_arr] = (0, 0, 0, 0)
        clean = Image.fromarray(source_pixels, "RGBA")
        clean_origin = "TRANSPARENT_ERASURE_REQUIRES_INDEPENDENT_PLATE_REVIEW"
    else:
        raise ValueError("No CLEAN supplied. Opaque backgrounds require separately reconstructed CLEAN.")
    if clean.size != size:
        raise ValueError("CLEAN has wrong native dimensions")
    outside_clean = rgba_equal_outside(source, clean, removal_arr)
    if outside_clean:
        raise ValueError("CLEAN changed source outside removal mask: " + str(outside_clean))
    clean_diff = np.any(np.asarray(source) != np.asarray(clean), axis=2)
    if np.any(clean_diff & protected_arr):
        raise ValueError("CLEAN damaged protected pixels")
    final_readable = Image.alpha_composite(clean, lettering)
    outside_edit = rgba_equal_outside(source, final_readable, edit_arr)
    if outside_edit or rgba_equal_outside(source, final_readable, ~protected_arr):
        raise ValueError("Final changed unapproved or protected pixels")
    final_native = final_readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if manifest["orientation"] == "FLIP_Y" else final_readable.copy()

    out.mkdir(parents=True, exist_ok=False)
    outputs = {
        "korean_letter_only.png": lettering,
        "clean_candidate.png": clean,
        "intermediate_readable.png": final_readable,
        "intermediate_native_raw.png": final_native,
    }
    for name, im in outputs.items():
        im.save(out / name, format="PNG")
    dds = encode_bgra_single_mip_if_exact(src_dds, final_native)
    if dds is not None:
        (out / "intermediate_TEST_ONLY.dds").write_bytes(dds)
        with Image.open(io.BytesIO(dds)) as im:
            if not np.array_equal(np.asarray(im.convert("RGBA")), np.asarray(final_native)):
                raise ValueError("Persisted DDS roundtrip mismatch")
        dds_state = "BGRA32_MIP1_NATIVE_ROUNDTRIP_PASS_TEST_ONLY"
    else:
        dds_state = "ENCODER_UNSUPPORTED_USE_CANONICAL_CODEC_PIPELINE"
    result = {
        "schema": SCHEMA,
        "status": STATE if dds else "C_PNG_TEST_ONLY_DDS_ENCODER_REQUIRED",
        "RUNTIME_VALIDATION": "UNTESTED",
        "C1": "NOT_RUN", "C3": "NOT_RUN",
        "input_sha256": {k: v["sha256"] for k, v in manifest.items()
                         if isinstance(v, dict) and "sha256" in v},
        "generated_mask_bbox": list(bounds),
        "native_cell_bbox": box,
        "lettering_placed_xy": [paste_x, paste_y],
        "source_size": list(size),
        "clean_origin": clean_origin,
        "source_outside_clean_change": outside_clean,
        "source_outside_edit_final_change": outside_edit,
        "visible_lettering_px": int(np.count_nonzero(visible)),
        "DDS": dds_state,
        "outputs": {name: digest((out / name).read_bytes()) for name in
                    list(outputs) + (["intermediate_TEST_ONLY.dds"] if dds else [])},
    }
    (out / "C_SALVAGE_TEST_ONLY.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def encode_bgra_single_mip_if_exact(source, native):
    # No DXT recompression / mip alterations / pseudo-encoded DDS. Preserve header.
    if source[:4] != b"DDS " or len(source) < 128:
        return None
    width, height = native.size
    if struct.unpack_from("<I", source, 4)[0] != 124:
        return None
    h, w, mips = struct.unpack_from("<III", source, 12)
    pf_size, pf_flags = struct.unpack_from("<II", source, 76)
    fourcc = source[84:88]
    depth = struct.unpack_from("<I", source, 88)[0]
    masks = struct.unpack_from("<IIII", source, 92)
    if (w, h) != (width, height) or mips not in (0, 1):
        return None
    if pf_size != 32 or (pf_flags & 0x40) == 0 or fourcc != b"\x00"*4 or depth != 32 or masks != BGRA_MASKS:
        return None
    if len(source) != 128 + width*height*4:
        return None
    rgba = np.asarray(native)
    bgra = rgba[:, :, [2, 1, 0, 3]].tobytes()
    return source[:128] + bgra


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, help="Directory containing pinned input files")
    ap.add_argument("--manifest", required=True, help="JSON recipe; paths relative to root")
    ap.add_argument("--output-dir", required=True, help="New empty output directory")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    print(json.dumps(compose(root, manifest, Path(args.output_dir).resolve()), ensure_ascii=False))


if __name__ == "__main__":
    main()
