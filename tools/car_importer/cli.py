"""CLI used by GUI, tests and power users. Python stdlib only."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import struct
import zlib
from pathlib import Path
import shutil
import subprocess
import sys

try:
    from .glb import inspect_glb
    from .game import verify_game, make_backup, restore_backup, install_model
    from .profiles import get_profile
except ImportError:
    from glb import inspect_glb
    from game import verify_game, make_backup, restore_backup, install_model
    from profiles import get_profile


class StageError(RuntimeError):
    pass


def stage_model(glb: str | Path, blender: str | Path, output_dir: str | Path,
                slot: str = "f50", rights_confirmed: bool = False,
                reference_blend: str | Path | None = None, timeout: int = 240) -> dict:
    if not rights_confirmed:
        raise StageError("Confirm that you have permission to use and locally convert this model")
    profile = get_profile(slot)
    inp = Path(glb).expanduser().resolve(strict=True)
    preflight = inspect_glb(inp)
    exe = Path(blender).expanduser().resolve(strict=True)
    if not exe.is_file():
        raise StageError("Specify a real Blender executable")
    out = Path(output_dir).expanduser().resolve()
    if out == inp.parent or inp == out or out in inp.parents:
        raise StageError("Use a dedicated output folder, not the model source folder")
    # Never stage into an installed game tree, even if the destination is an existing symlink.
    for parent in (out, *out.parents):
        if any((parent / name).is_file() for name in ("OR2006C2C.exe", "OR2006C2C.EXE", "or2006c2c.exe")):
            raise StageError("Stage output must be OUTSIDE the OutRun game installation")
    if reference_blend:
        reference = Path(reference_blend).expanduser().resolve(strict=True)
        if reference.suffix.lower() != ".blend":
            raise StageError("Reference must be an original PMT-derived .blend")
        if out == reference.parent or out in reference.parents:
            raise StageError("Output may not overwrite the reference folder")
    else:
        reference = None
    # Never overwrite existing user files during preview staging.
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise StageError("Select a new/empty staging directory (nothing will be overwritten)")
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / "stage_manifest.json"
    worker = Path(__file__).with_name("blender_worker.py")
    if not worker.is_file():
        raise StageError("Blender worker missing from installation")
    args = [str(exe), "--background", "--factory-startup", "--disable-autoexec", "--python", str(worker), "--",
            "--input", str(inp), "--output", str(out), "--slot", profile.slug]
    if reference:
        args.extend(["--reference-blend", str(reference)])
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False,
                              env={**os.environ, "PYTHONUTF8": "1"})
    except subprocess.TimeoutExpired as exc:
        raise StageError(f"Blender conversion exceeded {timeout}s; no game file modified") from exc
    if proc.returncode or not manifest.is_file():
        err = (proc.stderr + "\n" + proc.stdout)[-4000:]
        raise StageError("Blender staging failed (game untouched): " + err)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("status") != "BLENDER_STAGED_NOT_GAME_INSTALLABLE" or data.get("source_sha256") != preflight["sha256"]:
        raise StageError("Blender output manifest did not match inspected source")
    for name in ("staged_car.blend", "staged_car.glb", "car_preview.png"):
        if not (out / name).is_file() or (out / name).stat().st_size < 100:
            raise StageError(f"Staging incomplete: {name}")
    try:
        check = subprocess.run([str(exe), "--background", "--factory-startup", "--disable-autoexec", "--python",
                                str(worker), "--", "--verify", "--output", str(out)],
                               capture_output=True, text=True, timeout=min(timeout, 180), check=False,
                               env={**os.environ, "PYTHONUTF8": "1"})
    except subprocess.TimeoutExpired as exc:
        raise StageError("Independent Blender reopen timeout") from exc
    if check.returncode or "OUTRUN_CAR_INDEPENDENT_REOPEN_PASS" not in check.stdout:
        raise StageError("Independent Blender reopen failed: " + (check.stderr + check.stdout)[-3000:])
    data["independent_blender_reopen"] = "PASS"
    data["preflight"] = preflight
    data["output_dir"] = str(out)
    return data



def validate_ovc2(path: str | Path) -> dict:
    """Independent bounded OVRCABH2 format validation (not a runtime test)."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 128 * 1024 * 1024:
        raise StageError("OVC file missing or exceeds 128 MiB")
    b = path.read_bytes()
    if len(b) < 36 or b[:8] != b"OVRCABH2":
        raise StageError("Expected OVRCABH2 v2 header")
    version, ng, nm, nv, nt, nbytes, crc = struct.unpack_from("<7I", b, 8)
    if version != 2 or not (1 <= ng <= 512) or not (1 <= nm <= 64) or nv > 1_000_000 or nt > 2_000_000:
        raise StageError("Invalid OVC2 counts")
    if nbytes != len(b) - 36 or zlib.crc32(b[36:]) != crc:
        raise StageError("OVC2 payload/CRC failure")
    p = 36
    sumv = sumt = gpu_bytes = 0
    for _ in range(ng):
        if p + 16 > len(b):
            raise StageError("Truncated group")
        name_len, material, vc, ic, iw = struct.unpack_from("<HHIII", b, p)
        p += 16
        if not (0 < name_len <= 256) or material >= nm or vc < 3 or ic < 3 or ic % 3 or iw not in (2, 4) or (iw == 2 and vc > 65535):
            raise StageError("Invalid group fields")
        vertex_bytes, index_bytes = vc * 32, ic * iw
        if p + name_len + vertex_bytes + index_bytes > len(b):
            raise StageError("Truncated vertex/index data")
        name = b[p:p+name_len]
        if b"\x00" in name:
            raise StageError("Null group name")
        p += name_len + vertex_bytes
        indices = b[p:p+index_bytes]
        if iw == 4:
            if max(x[0] for x in struct.iter_unpack("<I", indices)) >= vc:
                raise StageError("Index range failure")
        elif max(x[0] for x in struct.iter_unpack("<H", indices)) >= vc:
            raise StageError("Index range failure")
        p += index_bytes
        sumv += vc
        sumt += ic // 3
        gpu_bytes += vertex_bytes + index_bytes
    if sumv != nv or sumt != nt:
        raise StageError("Total vertex/triangle count mismatch")
    for _ in range(nm):
        if p + 4 + 128 > len(b):
            raise StageError("Truncated texture")
        size = struct.unpack_from("<I", b, p)[0]
        p += 4
        if size < 132 or p + size > len(b) or b[p:p+4] != b"DDS " or struct.unpack_from("<I", b, p+4)[0] != 124:
            raise StageError("Invalid DDS block")
        h, w, mips = struct.unpack_from("<I", b, p+12)[0], struct.unpack_from("<I", b, p+16)[0], struct.unpack_from("<I", b, p+28)[0]
        if not (1 <= w <= 2048 and 1 <= h <= 2048) or w & (w-1) or h & (h-1) or mips != 1:
            raise StageError("Invalid DDS dimensions")
        if struct.unpack_from("<I", b, p+76)[0] != 32 or struct.unpack_from("<I", b, p+88)[0] != 32:
            raise StageError("Expected ARGB32 DDS")
        if size != 128 + w * h * 4:
            raise StageError("Incorrect DDS ARGB payload")
        p += size
        gpu_bytes += size
    if p != len(b) or gpu_bytes > 112 * 1024 * 1024:
        raise StageError("Trailing bytes or GPU budget failure")
    return {"status": "OVRCABH2_FORMAT_VALIDATED_NOT_GAMEPLAY", "groups": ng, "materials": nm,
            "vertices": nv, "triangles": nt,
            "sha256": hashlib.sha256(b).hexdigest(), "size": len(b),
            "game_files_modified": False}


def build_sidecar(stage_dir: str | Path, blender: str | Path, model_dir: str | Path,
                  rights_confirmed: bool = False, timeout: int = 280) -> dict:
    """Generate separate F50 OVC2 data using already staged verified Blender model."""
    if not rights_confirmed:
        raise StageError("Confirm rights to convert the chosen external model")
    stage = Path(stage_dir).expanduser().resolve(strict=True)
    ref = stage / "staged_car.blend"
    meta = json.loads((stage / "stage_manifest.json").read_text(encoding="utf-8"))
    if meta.get("profile") != "f50" or meta.get("status") != "BLENDER_STAGED_NOT_GAME_INSTALLABLE":
        raise StageError("Requires verified F50 stage, not an arbitrary .blend")
    if not ref.is_file() or hashlib.sha256(ref.read_bytes()).hexdigest() != meta["blender_sha256"]:
        raise StageError("Staged .blend SHA mismatch")
    exe = Path(blender).expanduser().resolve(strict=True)
    dest = Path(model_dir).expanduser().resolve()
    if not exe.is_file() or dest == stage or dest in stage.parents or stage in dest.parents:
        raise StageError("Separate Blender binary, source and model output directories required")
    for parent in (dest, *dest.parents):
        if any((parent / n).is_file() for n in ("OR2006C2C.exe", "or2006c2c.exe")):
            raise StageError("OVC must be OUTSIDE an existing game install")
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise StageError("Select an empty separate model directory")
    dest.mkdir(parents=True, exist_ok=True)
    worker = Path(__file__).with_name("sidecar_worker.py")
    if not worker.is_file():
        raise StageError("Missing packaged OVC worker")
    output = dest / "F50_External_Test.ovc"
    receipt = dest / "F50_External_Test_manifest.json"
    command = [str(exe), "--background", "--disable-autoexec", "--python", str(worker),
               "--", str(ref), str(output), str(receipt)]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False,
                              env={**os.environ, "PYTHONUTF8": "1"})
    except subprocess.TimeoutExpired as exc:
        raise StageError("Sidecar conversion timed out") from exc
    if proc.returncode or not output.is_file() or not receipt.is_file():
        raise StageError("OVC conversion failed: " + (proc.stdout + proc.stderr)[-3500:])
    actual = validate_ovc2(output)
    rec = json.loads(receipt.read_text(encoding="utf-8"))
    if rec["output_sha256"] != actual["sha256"] or rec["source_blend_sha256"] != meta["blender_sha256"]:
        raise StageError("OVC2 source/output receipt mismatch")
    actual["output_path"] = str(output)
    actual["model_dir"] = str(dest)
    actual["independent_crc_parse"] = "PASS"
    actual["runtime_in_game"] = "UNTESTED"
    return actual

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="OutRunCarImporter", description="OutRun 2006 external GLB importer preview")
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("inspect", help="Check external .glb structure and declared license")
    a.add_argument("glb")
    a = sub.add_parser("verify-game", help="Validate exact unmodified original F50 PMT")
    a.add_argument("game_root")
    a.add_argument("--slot", default="f50")
    a = sub.add_parser("backup", help="Create an immutable SHA-256 verified backup outside game")
    a.add_argument("game_root")
    a.add_argument("backup_dir")
    a.add_argument("--slot", default="f50")
    a = sub.add_parser("restore", help="Verify original backup; refuse overwriting unknown modded files")
    a.add_argument("game_root")
    a.add_argument("receipt")
    a = sub.add_parser("stage", help="Create normalized Blender/glb draft without modifying game")
    a.add_argument("glb")
    a.add_argument("--blender", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--slot", default="f50")
    a.add_argument("--reference-blend")
    a.add_argument("--rights-confirmed", action="store_true")
    a = sub.add_parser("sidecar", help="Write model-only F50 OVC2 into a separate directory")
    a.add_argument("stage_dir")
    a.add_argument("--blender", required=True)
    a.add_argument("--model-dir", required=True)
    a.add_argument("--rights-confirmed", action="store_true")
    a = sub.add_parser("install", help="Disabled: verified PMT serializer not yet available")
    a.add_argument("game_root")
    a.add_argument("staged_model")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "inspect":
            answer = inspect_glb(args.glb)
        elif args.cmd == "verify-game":
            answer = verify_game(args.game_root, args.slot)
        elif args.cmd == "backup":
            answer = make_backup(args.game_root, args.backup_dir, args.slot)
        elif args.cmd == "restore":
            answer = restore_backup(args.game_root, args.receipt)
        elif args.cmd == "stage":
            answer = stage_model(args.glb, args.blender, args.out, args.slot,
                                 args.rights_confirmed, args.reference_blend)
        elif args.cmd == "sidecar":
            answer = build_sidecar(args.stage_dir, args.blender, args.model_dir,
                                   args.rights_confirmed)
        elif args.cmd == "install":
            answer = install_model(args.game_root, args.staged_model)
        else:
            raise AssertionError("Unknown command")
        print(json.dumps(answer, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "game_files_changed": False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())