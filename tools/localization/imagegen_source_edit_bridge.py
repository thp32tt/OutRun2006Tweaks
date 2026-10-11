#!/usr/bin/env python3
"""Real B/C1 English PNG -> OpenAI Images Edit multipart-image bridge.

A displayed tool image is NOT a native ChatGPT image_gen edit attachment.
This explicit API alternative sends the verified source PNG file in the
images.edit(image=file) multipart field and records the server request ID.
No credentials or API success => no bound receipt or Korean DDS.
"""
import argparse
import base64
import hashlib
import io
import json
import os
import re
from pathlib import Path

from PIL import Image

SCHEMA = "outrun-imagegen-source-edit-v1"
MODEL = "gpt-image-1"
BINDING_TOOL = "openai.images.edit"


def digest(b):
    return hashlib.sha256(b).hexdigest()


def valid_ref(repo, spec):
    if not isinstance(spec, dict) or not isinstance(spec.get("path"), str):
        raise ValueError("SOURCE_REFERENCE_NOT_BOUND: source path missing")
    path = repo / spec["path"]
    if not path.resolve().is_relative_to(repo.resolve()) or not path.is_file():
        raise ValueError("SOURCE_REFERENCE_NOT_BOUND: unsafe or missing local source")
    data = path.read_bytes()
    if digest(data) != spec.get("sha256"):
        raise ValueError("SOURCE_REFERENCE_NOT_BOUND: source SHA256 mismatch")
    if len(data) > 20 * 1024 * 1024:
        raise ValueError("SOURCE_REFERENCE_NOT_BOUND: source exceeds input limit")
    with Image.open(io.BytesIO(data)) as im:
        if im.format != "PNG" or im.mode != "RGBA":
            raise ValueError("SOURCE_REFERENCE_NOT_BOUND: English source must be RGBA PNG")
        alpha = im.getchannel("A")
        lo, hi = alpha.getextrema()
        if lo != 0 or hi == 0 or alpha.getbbox() is None:
            raise ValueError("SOURCE_REFERENCE_NOT_BOUND: genuine transparent English lettering required")
        dimensions = list(im.size)
        visible_bbox = list(alpha.getbbox())
    return path, data, {"source_sha256": digest(data),
                        "source_size": dimensions,
                        "source_visible_bbox": visible_bbox}


def preflight(repo, request):
    if request.get("schema") != SCHEMA:
        raise ValueError("bad edit request schema")
    role, index = request.get("role"), request.get("queue_index")
    if role not in ("B", "C1") or type(index) is not int:
        raise ValueError("bad B/C1 role or index")
    if role == "C1" and index % 4 != 2:
        raise ValueError("C1 shard must be index % 4 == 2")
    if role == "B" and (index % 4 != 0 and
                         not (index % 4 == 2 and request.get("legacy_b_inflight") is True)):
        raise ValueError("B shard must be index % 4 == 0 or declared legacy inflight")
    if request.get("model", MODEL) != MODEL:
        raise ValueError("model is pinned to tested GPT image model")
    target = request.get("target_text")
    prompt = request.get("prompt")
    if not isinstance(target, str) or not target.strip() or not isinstance(prompt, str):
        raise ValueError("target text / prompt missing")
    if target not in prompt:
        raise ValueError("edit prompt must include exact target text")
    path, data, source = valid_ref(repo, request.get("english_reference"))
    # Require output to remain in its producer lane, never overwrite approvals.
    out = request.get("output_dir")
    root = repo / f"localization/graphics/role_{role}/imagegen_requests"
    if not isinstance(out, str) or not (repo / out).resolve().is_relative_to(root.resolve()):
        raise ValueError("output_dir must be inside producer imagegen_requests")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,90}", request.get("request_key", "")):
        raise ValueError("invalid request_key")
    return path, data, source


def run(repo, request, api_client=None):
    repo = Path(repo).resolve()
    path, original_bytes, source = preflight(repo, request)
    output_dir = (repo / request["output_dir"]).resolve()
    basename = request["request_key"]
    out_png = output_dir / (basename + "_RAW_UNREVIEWED.png")
    receipt_path = output_dir / (basename + "_TOOL_INPUT_RECEIPT.json")
    result_path = output_dir / (basename + "_OUTPUT_MANIFEST.json")
    # Check before any billable request, not only after generation.
    if any(p.exists() for p in (out_png, receipt_path, result_path)):
        raise FileExistsError("request_key output exists: do not duplicate same generation")
    if api_client is None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("SOURCE_ATTACHMENT_API_CREDENTIAL_MISSING: no API call, no receipt")
        from openai import OpenAI
        api_client = OpenAI()
    # The only live binding proof is a successful remote EDIT request with
    # the verified PNG bytes supplied as image=<open binary file>.
    with path.open("rb") as source_stream:
        if digest(source_stream.read()) != source["source_sha256"]:
            raise ValueError("SOURCE_REFERENCE_NOT_BOUND: changed source after preflight")
        source_stream.seek(0)
        raw = api_client.images.with_raw_response.edit(
            model=request.get("model", MODEL),
            image=source_stream,
            prompt=request["prompt"],
            size="1536x1024",
            background="transparent",
            output_format="png",
        )
    request_id = (raw.headers.get("x-request-id") or
                  raw.headers.get("X-Request-ID"))
    if not isinstance(request_id, str) or not request_id.strip():
        raise RuntimeError("SOURCE_REFERENCE_NOT_BOUND: API response without request ID")
    result = raw.parse()
    if not result.data or not result.data[0].b64_json:
        raise RuntimeError("IMAGEGEN_OUTPUT_MISSING: API response without image")
    output = base64.b64decode(result.data[0].b64_json, validate=True)
    with Image.open(io.BytesIO(output)) as im:
        if im.format != "PNG" or im.mode != "RGBA":
            raise RuntimeError("IMAGEGEN_OUTPUT_NOT_TRANSPARENT_RGBA_PNG")
        alpha = im.getchannel("A")
        low, high = alpha.getextrema()
        if low != 0 or high == 0:
            raise RuntimeError("IMAGEGEN_OUTPUT_MISSING_ALPHA")
        output_size = list(im.size)
        output_visible_bbox = list(alpha.getbbox() or ())
    output_dir.mkdir(parents=True, exist_ok=True)
    # Never overwrite even unreviewed artifacts: retries need new request keys.
    if any(p.exists() for p in (out_png, receipt_path, result_path)):
        raise FileExistsError("request_key output exists: do not duplicate same generation")
    receipt = {
        "schema": "outrun-imagegen-edit-receipt-v1",
        "tool": BINDING_TOOL,
        "media_attached": True,
        "image_input_field": "multipart_image",
        "input_reference_id": request_id,
        "openai_request_id": request_id,
        "source_image_sha256": source["source_sha256"],
        "source_image_bytes": len(original_bytes),
        "source_image_dimensions": source["source_size"],
        "target_text": request["target_text"],
        "generation_id": request_id,
        "model": request.get("model", MODEL),
        "output_format": "png",
        "background": "transparent",
        "result_sha256": digest(output),
        "output_dimensions": output_size,
        "output_visible_bbox": output_visible_bbox,
        "actual_api_response_received": True,
        "C2": "NOT_RUN", "C3": "NOT_RUN",
        "RUNTIME_VALIDATION": "UNTESTED",
    }
    info = {
        "schema": "outrun-imagegen-raw-output-v1",
        "role": request["role"], "queue_index": request["queue_index"],
        "target_text": request["target_text"],
        "provider": "openai-images-edit",
        "generator": {"provider": "openai-images-edit",
                      "generation_id": request_id,
                      "prompt": request["prompt"]},
        "source_media_binding": {
            "english_reference": request["english_reference"],
            "tool_request_receipt": {
                "path": str(receipt_path.relative_to(repo)),
                "sha256": digest((json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode()),
            },
        },
        "generated": {"path": str(out_png.relative_to(repo)),
                      "sha256": digest(output)},
        "producer": "RAW_UNREVIEWED_REQUIRES_VISUAL_GLYPH_AND_PLATE_GATES",
        "new_trial_dds": 0, "official_promoted": 0,
        "C2": "NOT_RUN", "C3": "NOT_RUN",
        "RUNTIME_VALIDATION": "UNTESTED",
    }
    out_png.write_bytes(output)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result_path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "REMOTE_MULTIPART_EDIT_RESPONSE_RECEIVED_RAW_UNREVIEWED",
            "request_id": request_id, "source_sha256": source["source_sha256"],
            "generated_sha256": digest(output), "output_dir": request["output_dir"],
            "C2": "NOT_RUN", "new_trial_dds": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--request", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    repo = Path(args.repo).resolve()
    manifest = (repo / args.request).resolve()
    if not manifest.is_relative_to(repo):
        raise SystemExit("unsafe request path")
    request = json.loads(manifest.read_text(encoding="utf-8"))
    try:
        if args.dry_run:
            _, _, source = preflight(repo, request)
            print(json.dumps({
                "status": "LOCAL_SOURCE_SHA_VERIFIED_ONLY_NOT_GENERATOR_BOUND",
                "role": request["role"], "queue_index": request["queue_index"],
                **source, "generation_calls": 0, "new_trial_dds": 0
            }, ensure_ascii=False))
        else:
            print(json.dumps(run(repo, request), ensure_ascii=False))
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as e:
        p.exit(2, str(e) + "\n")


if __name__ == "__main__":
    main()
