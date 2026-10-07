"""Generate lossless SOURCE/CLEAN/FINAL region views from persisted DDS bytes.

This prepares evidence only and never creates approval decisions.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps

TRANSFORMS = {
    "identity": lambda im: im,
    "flip_y": ImageOps.flip,
    "flip_x": ImageOps.mirror,
    "rotate_180": lambda im: im.transpose(Image.Transpose.ROTATE_180),
    "rotate_90": lambda im: im.transpose(Image.Transpose.ROTATE_90),
    "rotate_270": lambda im: im.transpose(Image.Transpose.ROTATE_270),
}


def ref(path, repo):
    return {"path": path.resolve().relative_to(repo.resolve()).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def card(images, background=(96, 96, 96)):
    w, h = images[0].size
    out = Image.new("RGB", (w * len(images), h), background)
    for i, im in enumerate(images):
        out.paste(im, (i * w, 0), im.getchannel("A"))
    return out


def generate(repo, source, clean, candidate, regions, out):
    out.mkdir(parents=True, exist_ok=True)
    images = [Image.open(p).convert("RGBA") for p in (source, clean, candidate)]
    if len({im.size for im in images}) != 1:
        raise ValueError("native source/clean/candidate dimensions must match")
    images[2].save(out / "decoded_final.png")
    result = []
    for ordinal, region in enumerate(regions):
        box = region["bbox"]
        w, h = images[0].size
        if len(box) != 4 or not (0 <= box[0] < box[2] <= w and 0 <= box[1] < box[3] <= h):
            raise ValueError("invalid region bounds")
        raw = [im.crop(box) for im in images]
        readable = [TRANSFORMS[region["readable_transform"]](im) for im in raw]
        base = card(readable)
        views = {"native": base, "raw": card(raw),
                 "zoom": base.resize((base.width * 4, base.height * 4), Image.Resampling.NEAREST),
                 "black": card(readable, (0, 0, 0)), "white": card(readable, (255, 255, 255)),
                 "gray": base}
        for percent in (75, 50):
            views[f"practical_{percent}"] = base.resize(
                (max(1, round(base.width * percent / 100)), max(1, round(base.height * percent / 100))),
                Image.Resampling.LANCZOS)
        views["practical"] = views["practical_50"]
        refs = {}
        for name, im in views.items():
            p = out / f"region_{ordinal:03d}_{name}.png"
            im.save(p)
            refs[name] = ref(p, repo)
        result.append({**region, "views": refs})
    manifest = {"candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "clean_plate": ref(clean, repo), "decoded_final": ref(out / "decoded_final.png", repo),
                "column_order": ["SOURCE", "CLEAN", "PERSISTED_DDS_FINAL"],
                "result": "EVIDENCE_ONLY_NOT_APPROVAL", "regions": result}
    (out / "region_evidence.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "clean", "candidate", "regions", "out"):
        p.add_argument("--" + name, required=True, type=Path)
    a = p.parse_args()
    generate(Path.cwd(), a.source, a.clean, a.candidate,
             json.loads(a.regions.read_text(encoding="utf-8")), a.out)
