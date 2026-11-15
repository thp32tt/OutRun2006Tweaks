"""CLI used by GUI, tests and power users. Python stdlib only."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

try:
    from .glb import inspect_glb
    from .game import verify_game, make_backup, restore_backup, install_model
    from .profiles import get_profile
    from .sidecar import export_experimental_ovc, inspect_ovc, install_test_sidecar, remove_test_sidecar
except ImportError:
    from glb import inspect_glb
    from game import verify_game, make_backup, restore_backup, install_model
    from profiles import get_profile
    from sidecar import export_experimental_ovc, inspect_ovc, install_test_sidecar, remove_test_sidecar


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
    a = sub.add_parser("stage-sidecar", help="Combined: external GLB -> staged Blender -> experimental OVRCABH2 sidecar")
    a.add_argument("glb")
    a.add_argument("--blender", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--slot", default="f50")
    a.add_argument("--reference-blend")
    a.add_argument("--rights-confirmed", action="store_true")
    a = sub.add_parser("verify-sidecar", help="Independently validate OVRCABH2, does not touch game")
    a.add_argument("ovc")
    a = sub.add_parser("install-test-sidecar", help="Copy verified OVC to CarImporter/f50 only, PMT untouched")
    a.add_argument("game_root")
    a.add_argument("ovc")
    a.add_argument("--rights-confirmed", action="store_true")
    a = sub.add_parser("remove-test-sidecar", help="Remove only matching importer-owned sidecar")
    a.add_argument("game_root")
    a = sub.add_parser("install", help="Disabled: native PMT installation not supported")
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
        elif args.cmd == "stage-sidecar":
            if args.slot != "f50":
                raise StageError("Only F50 is enabled for experimental sidecar generation")
            stage = stage_model(args.glb, args.blender, args.out, args.slot, args.rights_confirmed, args.reference_blend)
            sidecar = export_experimental_ovc(Path(args.out) / "staged_car.blend", args.blender,
                                             Path(args.out) / "ovc_test", args.rights_confirmed)
            answer = {"status": "COMBINED_EXTERNAL_GLB_TO_OVC_STATIC_PASS_RUNTIME_UNTESTED",
                      "staging": stage, "sidecar": sidecar, "game_files_modified": False}
        elif args.cmd == "verify-sidecar":
            answer = inspect_ovc(args.ovc)
        elif args.cmd == "install-test-sidecar":
            answer = install_test_sidecar(args.game_root, args.ovc, args.rights_confirmed)
        elif args.cmd == "remove-test-sidecar":
            answer = remove_test_sidecar(args.game_root)
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