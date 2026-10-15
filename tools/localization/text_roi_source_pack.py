#!/usr/bin/env python3
"""Extract verified full-source text ROIs for individual ImageGen translations.

No tile inputs, no ImageGen calls, no changes to A/B queues or existing assets.
Works only on canonical full-image PNG files or verified local reconstructed
full-size sources (the latter must be explicitly marked with weaker provenance).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

SCHEMA = "outrun-hd-text-roi-v1"
MAX_NATIVE_PIXELS = 4096 * 4096
MAX_GENERATOR_SIDE = 3072  # Allow mildly oversize complete-phrase input; model may downsample.
MAX_INPUT_PIXELS = 3072 * 3072

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def filename(name: str) -> str:
    if not name or name in (".", "..") or Path(name).name != name or any(x in name for x in ("/", "\\", "\x00")):
        raise ValueError("UNSAFE_FILENAME")
    return name

def rect_box(box, size):
    if not isinstance(box, list) or len(box) != 4 or any(type(v) is not int for v in box):
        raise ValueError("INVALID_BBOX")
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
        raise ValueError("BBOX_OUTSIDE_SOURCE")
    return tuple(box)

def atomic_new_directory(target: Path, render):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError("OUTPUT_EXISTS_NO_OVERWRITE")
    with tempfile.TemporaryDirectory(prefix=".roi-build-", dir=target.parent) as tmpstr:
        tmp = Path(tmpstr)
        render(tmp)
        os.rename(tmp, target)

def run(spec: Path, source_root: Path, output_root: Path) -> dict:
    specdata = spec.read_bytes()
    conf = json.loads(specdata)
    if conf.get("schema") != SCHEMA or not isinstance(conf.get("assets"), list):
        raise ValueError("INVALID_ROI_SCHEMA")
    if source_root.resolve().is_relative_to(output_root.resolve()) or output_root.resolve().is_relative_to(source_root.resolve()):
        raise ValueError("OUTPUT_MUST_NOT_BE_WITHIN_SOURCE")
    result = {"schema": SCHEMA, "status": "TEST_ONLY", "ready": [], "hold": []}
    seen = set()
    for asset in conf["assets"]:
        q = filename(asset["queue_id"])
        name = filename(asset["source_png"])
        path = source_root / name
        for region in asset["regions"]:
            rid = filename(region["id"])
            identity = q + "-" + rid
            if identity in seen:
                raise ValueError("DUPLICATE_REGION_ID")
            seen.add(identity)
            try:
                source_bytes = path.read_bytes()
                if sha(source_bytes) != asset["source_sha256"]:
                    raise ValueError("SOURCE_SHA_MISMATCH")
                with Image.open(path) as im:
                    if im.format != "PNG" or im.mode != "RGBA" or im.width * im.height > MAX_NATIVE_PIXELS:
                        raise ValueError("EXPECTED_FULL_RGBA_PNG")
                    full = im.copy()
                x0, y0, x1, y1 = rect_box(region["bbox"], full.size)
                zoom = region.get("scale", 2)
                if type(zoom) is not int or not 1 <= zoom <= 4:
                    raise ValueError("SCALE_MUST_BE_1_TO_4")
                w, h = x1-x0, y1-y0
                if w*zoom*h*zoom > MAX_INPUT_PIXELS or w*zoom > MAX_GENERATOR_SIDE or h*zoom > MAX_GENERATOR_SIDE:
                    raise ValueError("IMAGEGEN_INPUT_OVER_3072_LIMIT")
                mode = region.get("isolation", "reference_crop")
                if mode not in ("alpha", "manual_mask", "reference_crop"):
                    raise ValueError("INVALID_ISOLATION")
                crop = full.crop((x0, y0, x1, y1))
                alpha = np.asarray(crop.getchannel("A"))
                if mode == "alpha":
                    if not np.any(alpha) or np.all(alpha == 255):
                        raise ValueError("ALPHA_NOT_ISOLATING_TEXT")
                    mask = alpha > 0
                elif mode == "manual_mask":
                    mname = filename(region["mask_png"])
                    maskbytes = (source_root / mname).read_bytes()
                    if sha(maskbytes) != region["mask_sha256"]:
                        raise ValueError("MASK_SHA_MISMATCH")
                    with Image.open(source_root / mname) as mi:
                        if mi.format != "PNG" or mi.mode != "L" or mi.size != full.size:
                            raise ValueError("MASK_WRONG_MODE_OR_DIMENSIONS")
                        mm = np.asarray(mi.crop((x0, y0, x1, y1)))
                    if not np.isin(mm, (0, 255)).all():
                        raise ValueError("MASK_MUST_BE_BINARY")
                    mask = mm > 0
                    if not np.any(mask):
                        raise ValueError("MASK_EMPTY")
                    ca = np.asarray(crop).copy()
                    ca[~mask] = [0, 0, 0, 0]
                    crop = Image.fromarray(ca, "RGBA")
                else:
                    mask = None  # Opaque background is reference-only, not a glyph layer.
                if mask is not None:
                    # A 2px transparent border proves that strokes/effects
                    # do not visibly touch the cropped canvas.
                    if (np.any(mask[:2]) or np.any(mask[-2:]) or
                        np.any(mask[:, :2]) or np.any(mask[:, -2:])):
                        raise ValueError("TEXT_OR_EFFECT_TOUCHES_CROP_EDGE")
                if not region["english"] or not region["korean"] or region["english"] == region["korean"]:
                    raise ValueError("TRANSLATION_NOT_PROVIDED")
                zoomed = crop.resize((w*zoom, h*zoom), resample=Image.Resampling.LANCZOS)
                output = output_root / identity
                def save(tmp):
                    native = tmp / "english_text_roi_native.png"
                    enlarged = tmp / "imagegen_input_upscaled.png"
                    crop.save(native)
                    zoomed.save(enlarged)
                    m = {
                        "schema": SCHEMA, "queue_id": q, "region_id": rid,
                        "source_png": name, "source_png_sha256": sha(source_bytes),
                        "source_kind": asset.get("source_kind", "FULL_HD_PNG"),
                        "source_dds_path": asset.get("source_dds_path", ""),
                        "original_dimensions": list(full.size), "bbox_xyxy": list((x0,y0,x1,y1)),
                        "english": region["english"], "korean": region["korean"],
                        "isolation": mode, "scale": zoom,
                        "native_dimensions": [w,h], "imagegen_dimensions": [w*zoom,h*zoom],
                        "native_png_sha256": sha(native.read_bytes()),
                        "imagegen_input_sha256": sha(enlarged.read_bytes()),
                        "alpha_crop_margin_checked": mask is not None,
                        "status": "IMAGEGEN_REFERENCE_TEST_ONLY",
                        "generate_output": "ONE_KOREAN_TEXT_ONLY_TRANSPARENT_PNG",
                        "required_review": ["KOREAN_GLYPHS", "SOURCE_EFFECT", "CLEAN_PLATE", "NATIVE_ROI_FIT", "C1", "C3_IF_REQUIRED", "USER_GAME"],
                        "RUNTIME_VALIDATION": "UNTESTED"
                    }
                    (tmp / "roi_manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    prompt = ("@Create image — OutRun 2006 글자영역 단독 한글화\n"
                              "첨부 PNG는 원본 HD 전체 화면이 아니라 하나의 온전한 영어 문구 ROI를 잘라 확대한 참조입니다.\n"
                              f"영어: {region['english']}\n한글 정본: {region['korean']}\n"
                              "정확한 한글 문구 1개만 출력하세요. 한글 자소/받침을 정확히 표현하고 원문과 같은 기울기, 색, 광택, 테두리, 그림자를 가능한 유지하세요.\n"
                              "출력은 투명 배경의 글자+글자 효과 RGBA PNG 1장입니다. 영어 원문, 배경, 테두리 밖 장식, 로고, 아이콘, 차량 또는 다른 문구를 포함하지 마세요.\n"
                              "좌우상하 글자 잘림이 없어야 하며 문구 전체를 한 캔버스 안에 유지하세요. 원본 영어 문자와 겹치지 마세요.\n"
                              f"이 ROI는 원래 ({x0},{y0})-({x1},{y1}) 좌표이며 확대율 {zoom}배입니다. 이를 출력 이미지에 문자로 쓰지 마세요.\n")
                    (tmp / "imagegen_prompt.txt").write_text(prompt, encoding="utf-8")
                atomic_new_directory(output, save)
                result["ready"].append({"id": identity, "output": str(output), "bbox": [x0,y0,x1,y1], "scale": zoom})
            except (OSError, ValueError, KeyError, TypeError) as e:
                result["hold"].append({"id": identity, "reason": str(e)})
    return result

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", required=True)
    p.add_argument("--source-root", required=True)
    p.add_argument("--output-root", required=True)
    a = p.parse_args()
    print(json.dumps(run(Path(a.spec), Path(a.source_root), Path(a.output_root)), ensure_ascii=False))
