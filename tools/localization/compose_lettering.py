"""Deterministic face/effect composition; geometry review is NOT C approval."""
import argparse
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from production_pixel_guard import bound, rgba

VERSION = "separated-lettering-v1"
ROUTES = {"native_small", "vector_title", "layered_metal"}


def compose(repo, recipe):
    if recipe.get("version") != VERSION or recipe.get("coordinates") != "native_raw":
        raise ValueError("Unknown lettering version/coordinates")
    if recipe.get("route") not in ROUTES:
        raise ValueError("Choose native_small, vector_title or layered_metal")
    source = rgba(bound(repo, recipe["source"]))
    # Pin the actual native geometry, not a font name or an approximate bbox.
    geometry_bytes = bound(repo, recipe["geometry"])
    with Image.open(io.BytesIO(geometry_bytes)) as im:
        if im.format != "PNG" or im.mode != "L":
            raise ValueError("Geometry must be native L-mode alpha PNG")
        geometry = np.array(im)
    if geometry.shape != source.shape[:2] or not np.any(geometry):
        raise ValueError("Empty or resized geometry")
    review = json.loads(bound(repo, recipe["geometry_review"]))
    if (review.get("status") != "GEOMETRY_READY"
            or review.get("geometry_sha256") != recipe["geometry"]["sha256"]
            or review.get("source_sha256") != recipe["source"]["sha256"]
            or review.get("route") != recipe["route"]
            or review.get("reviewer") not in {"A", "B"}):
        raise ValueError("Missing/stale producer geometry review")
    for key in ("stroke", "counterspace", "proportions", "slant", "readability"):
        if not isinstance(review.get("observations", {}).get(key), str) or not review["observations"][key].strip():
            raise ValueError("Missing geometry observation: " + key)
    evidence = review.get("evidence", [])
    if not evidence:
        raise ValueError("Geometry comparison evidence required")
    for ref in evidence:
        rgba(bound(repo, ref))
    # Pin editable outlines or native renderer recipe, including font/version in that recipe.
    bound(repo, recipe["geometry_recipe"])
    layers = recipe["layers"]  # back to front; never infer order from names
    roles = [layer["role"] for layer in layers]
    if roles.count("face") != 1 or len(roles) != len(set(roles)):
        raise ValueError("Exactly one face and unique effect roles required")
    if set(roles) - {"shadow", "extrusion", "rim", "face", "highlight"}:
        raise ValueError("Unknown effect role")
    if roles[-1] not in {"face", "highlight"} or ("highlight" in roles and roles[-1] != "highlight"):
        raise ValueError("Effects behind face; optional highlight last")
    if recipe["route"] == "layered_metal" and not {"face", "highlight", "extrusion"}.issubset(roles):
        raise ValueError("Metal route needs face, highlight and extrusion layers")
    image = Image.new("RGBA", (source.shape[1], source.shape[0]))
    metrics = {}
    for layer in layers:
        pixels = rgba(bound(repo, layer["input"]))
        if pixels.shape != source.shape:
            raise ValueError("No implicit layer resizing")
        alpha = pixels[:, :, 3]
        if layer["role"] == "face" and not np.array_equal(alpha, geometry):
            raise ValueError("Face alpha differs from reviewed geometry")
        if layer["role"] == "highlight" and np.any((alpha != 0) & (geometry == 0)):
            raise ValueError("Highlight escapes face geometry")
        metrics[layer["role"]] = int(np.count_nonzero(alpha))
        image = Image.alpha_composite(image, Image.fromarray(pixels))
    return image, {"result": "COMPOSED_REQUIRES_VISUAL_DDS_C_C3_REVIEW",
                   "route": recipe["route"], "layer_visible_pixels": metrics,
                   "runtime_validation": "UNTESTED"}


def verify_lettering(repo, manifest):
    recipe = json.loads(bound(repo, manifest["lettering_recipe"]))
    if recipe["source"] != manifest["inputs"]["source"]:
        raise ValueError("Lettering recipe source differs from final manifest")
    image, report = compose(repo, recipe)
    actual = rgba(bound(repo, manifest["inputs"]["lettering"]))
    if not np.array_equal(np.array(image), actual):
        raise ValueError("Final lettering differs from reviewed separated layers")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--recipe", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    image, report = compose(Path(args.repo).resolve(), json.loads(Path(args.recipe).read_text()))
    image.save(args.output, format="PNG")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
