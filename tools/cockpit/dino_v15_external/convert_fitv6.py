#!/usr/bin/env python3
"""Convert the exact user-made Dino NoGlass FitV6 GLB into the R26 OVC2 sidecar.

FitV6 geometry already includes uniform 0.88 sizing and glass removal.
Do not rescale a second time; never touch original game PMT or EXE.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import tempfile
import zipfile
import build_sidecar_hq as hq

SOURCE_NAME = "Dino246_NoGlass_FitV6_UniformProportions.glb"
OUTPUT_NAME = "Dino246_Cockpit_LHD_v15.ovc"
MAX_GLB = 120 * 1024 * 1024

def read_model(src: Path) -> bytes:
    if not src.is_file():
        raise ValueError(f"V6 model is missing: {src}")
    if src.suffix.lower() == ".glb":
        if src.name != SOURCE_NAME:
            raise ValueError(f"Use original FitV6 filename: {SOURCE_NAME}")
        if src.stat().st_size > MAX_GLB:
            raise ValueError("FitV6 GLB file too large")
        b = src.read_bytes()
    elif src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as z:
            hits = [x for x in z.infolist() if not x.is_dir()
                    and Path(x.filename).name == SOURCE_NAME]
            if len(hits) != 1:
                raise ValueError("Zip must contain exactly one original FitV6 GLB")
            if hits[0].file_size > MAX_GLB:
                raise ValueError("FitV6 GLB entry too large")
            b = z.read(hits[0])
    else:
        raise ValueError("Expected original FitV6 .glb or its .zip")
    if len(b) < 20 or len(b) > MAX_GLB or b[:4] != b"glTF" or \
       struct.unpack_from("<I", b, 4)[0] != 2 or \
       struct.unpack_from("<I", b, 8)[0] != len(b):
        raise ValueError("Not a valid glTF 2.0 GLB")
    return b

def build(source: Path, out_dir: Path) -> dict:
    b = read_model(source)
    digest = hashlib.sha256(b).hexdigest()
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dino-fitv6-") as tmp:
        temp_zip = Path(tmp) / "input.zip"
        with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_STORED) as z:
            z.writestr(SOURCE_NAME, b)
        hq.HQ_ENTRY = SOURCE_NAME
        hq.HQ_SHA256 = digest
        result = hq.build(temp_zip, out_dir / OUTPUT_NAME)
    result.update(
        model_version="DINO_NOGLASS_FIT_V6",
        source_name=SOURCE_NAME,
        source_sha256=digest,
        source_bytes=len(b),
        output_name=OUTPUT_NAME,
        additional_scale=1.0,
        runtime_validation="UNTESTED",
    )
    (out_dir / "FITV6_BUILD_MANIFEST.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return result

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--v6", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(build(args.v6, args.out_dir), ensure_ascii=False, indent=2))
