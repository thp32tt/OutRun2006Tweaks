"""Generate verified *readable-upright* English reference PNGs without touching inputs.

OutRun HD source sprites have two different relationships to the readable source:
- _BASE_READABLE_FLIPY PNGs already display upright English (do NOT flip again).
- Q012 _BASE_READABLE_NORMAL is actually upside down and needs a vertical flip.

The derived upright PNG exists solely for ImageGen. Recomposition restores to the
source tile's original pixel orientation before any DDS/game-specific transforms.
"""
import hashlib
import json
import os
from pathlib import Path

OVERRIDE_Q012 = (
    "Q012_D6DC1380_BASE_READABLE_NORMAL__r01c01__x0_y0__256x64.png"
)
ORIGINAL_Q012_SHA = "6497fa31804353844f703d1eb9355af0d6f7fdf345edadf860eb0eb93430ea2e"
DERIVED_DIR = "a_tile_batches/upright_sources"
ORIGINAL_ORIENTATION = "FLIP_Y_PREVIEW_PER_SPRITE_VERIFY"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _save_json_atomic(path, payload):
    tmp = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def resolve_upright_source(root, row, original_path):
    """Return verified upright source path, SHA, and exact inverse for later QA.

    Caller must already have validated original PNG against ALL_TILE_MAPPING.csv.
    No user source image is modified.
    """
    from PIL import Image, ImageOps

    root = Path(root).resolve()
    original_path = Path(original_path).resolve()
    filename = row["part_filename"]
    orientation = row.get("orientation")
    source_sha = row["part_png_sha256"]
    original_bytes = original_path.read_bytes()
    if _sha(original_bytes) != source_sha:
        raise ValueError("UPRIGHT_SOURCE_HASH_MISMATCH:" + filename)
    if orientation == ORIGINAL_ORIENTATION:
        if "READABLE_FLIPY" not in filename:
            raise ValueError("FLIPY_METADATA_FILENAME_CONFLICT:" + filename)
        return {
            "path": str(original_path),
            "sha256": source_sha,
            "source_png_sha256": source_sha,
            "source_orientation": orientation,
            "input_direction": "UPRIGHT_VERIFIED_BY_SOURCE_ORIENTATION_POLICY",
            "source_to_upright": "IDENTITY",
            "upright_to_source": "IDENTITY",
            "dds_orientation": "VERIFY_PER_SPRITE_BEFORE_DDS_WRITE",
        }
    if orientation != "NORMAL" or filename != OVERRIDE_Q012:
        raise ValueError("ORIENTATION_UNREVIEWED:" + filename + ":" + str(orientation))
    if source_sha != ORIGINAL_Q012_SHA:
        raise ValueError("Q012_KNOWN_ORIGINAL_HASH_CHANGED")
    with Image.open(original_path) as image:
        image.load()
        if image.mode != "RGBA":
            raise ValueError("Q012_SOURCE_NOT_RGBA")
        upright = ImageOps.flip(image)
        if ImageOps.flip(upright).tobytes() != image.tobytes():
            raise ValueError("ORIENTATION_ROUNDTRIP_FAILED")
    output = root / DERIVED_DIR / filename
    manifest = output.with_suffix(".orientation.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() != manifest.exists():
        raise ValueError("INCOMPLETE_UPRIGHT_DERIVATIVE_PAIR")
    if not output.exists():
        tmp = output.with_name(output.name + "." + str(os.getpid()) + ".tmp")
        upright.save(tmp, format="PNG")
        derived_sha = _sha(tmp.read_bytes())
        os.replace(tmp, output)
        _save_json_atomic(manifest, {
            "source": "inputs/A/HD_EN_TILES_20261014/" + filename,
            "source_sha256": source_sha,
            "upright_path": DERIVED_DIR + "/" + filename,
            "upright_sha256": derived_sha,
            "source_to_upright": "FLIP_Y",
            "upright_to_source": "FLIP_Y",
            "rgba_lossless": True,
            "dimensions": list(upright.size),
            "dds_orientation": "VERIFY_ORIGINAL_TEXTURE_ORIENTATION_BEFORE_WRITE",
        })
    details = json.loads(manifest.read_text(encoding="utf-8"))
    actual_sha = _sha(output.read_bytes())
    if details.get("source_sha256") != source_sha or details.get("upright_sha256") != actual_sha:
        raise ValueError("UPRIGHT_DERIVATIVE_SHA_MISMATCH")
    with Image.open(output) as saved:
        saved.load()
        if saved.mode != "RGBA" or saved.size != upright.size or saved.tobytes() != upright.tobytes():
            raise ValueError("UPRIGHT_DERIVATIVE_PIXEL_MISMATCH")
    return {
        "path": str(output),
        "sha256": actual_sha,
        "source_png_sha256": source_sha,
        "source_orientation": orientation,
        "input_direction": "UPRIGHT_DERIVED_VERIFIED",
        "source_to_upright": "FLIP_Y",
        "upright_to_source": "FLIP_Y",
        "dds_orientation": "VERIFY_ORIGINAL_TEXTURE_ORIENTATION_BEFORE_WRITE",
    }


def restore_source_orientation(candidate_image, source_mapping):
    """Pixel-exact inverse when mapping an approved upright candidate into source tiles.

    Do not use this to bypass required source dimensions/alpha/typography QA.
    """
    from PIL import ImageOps
    method = source_mapping["upright_to_source"]
    if method == "IDENTITY":
        return candidate_image.copy()
    if method == "FLIP_Y":
        return ImageOps.flip(candidate_image)
    raise ValueError("UNKNOWN_INVERSE_ORIENTATION:" + str(method))