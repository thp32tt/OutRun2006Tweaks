"""Original-game verification and immutable backups; NO unverified geometry installation."""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid

try:
    from .glb import file_hash
    from .profiles import get_profile
except ImportError:
    from glb import file_hash
    from profiles import get_profile


class GameSafetyError(ValueError):
    pass


def verify_game(game_root: str | Path, profile_name: str = "f50") -> dict:
    root = Path(game_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise GameSafetyError("Game path is not a directory")
    exe_names = ("OR2006C2C.exe", "OR2006C2C.EXE", "or2006c2c.exe")
    if not any((root / name).is_file() for name in exe_names):
        raise GameSafetyError("OR2006C2C.exe missing; select the actual installed game folder")
    profile = get_profile(profile_name)
    cars_dir = root / "Cars"
    if cars_dir.is_symlink() or (root / profile.source_filename).exists():
        raise GameSafetyError("Unexpected/symlink car directory or path")
    src = cars_dir / profile.source_filename
    if src.is_symlink() or not src.is_file():
        raise GameSafetyError(f"Missing non-symlink Cars/{profile.source_filename}")
    if src.resolve().parent != cars_dir.resolve():
        raise GameSafetyError("Car path escapes expected game directory")
    digest = file_hash(src)
    if digest != profile.source_sha256:
        raise GameSafetyError(f"Unrecognized original {profile_name} PMT SHA-256: {digest}; abort")
    return {
        "status": "SOURCE_VERIFIED_NO_GAME_FILES_CHANGED",
        "root": str(root),
        "vehicle": profile.slug,
        "source_path": str(src),
        "source_sha256": digest,
        "game_installable": False,
    }


def _atomic_json(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(prefix=".receipt-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def make_backup(game_root: str | Path, backup_root: str | Path, slot: str = "f50") -> dict:
    data = verify_game(game_root, slot)
    root = Path(data["root"])
    out = Path(backup_root).expanduser().resolve()
    if out == root or root in out.parents:
        raise GameSafetyError("Keep backup outside your game installation")
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"OutRunCarImporter_{slot}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    dest.mkdir()
    source = Path(data["source_path"])
    backup = dest / "original_pmt.sz"
    try:
        with source.open("rb") as fin, backup.open("xb") as fout:
            shutil.copyfileobj(fin, fout, 1024 * 1024)
            fout.flush()
            os.fsync(fout.fileno())
        if file_hash(backup) != data["source_sha256"]:
            raise GameSafetyError("Backup SHA-256 verification failed")
        receipt = {
            "schema": 1,
            "status": "ORIGINAL_BACKUP_ONLY_NO_MOD_INSTALLED",
            "vehicle": slot,
            "original_sha256": data["source_sha256"],
            "original_game_root": str(root),
            "original_relative_path": "Cars/" + source.name,
            "backup_file": "original_pmt.sz",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        _atomic_json(dest / "receipt.json", receipt)
        return {**receipt, "backup_directory": str(dest)}
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise


def restore_backup(game_root: str | Path, receipt_file: str | Path) -> dict:
    """Restore only when original is already present; no untrusted replacement is overwritten.

    The public v0.1 importer cannot create install receipts. This validates a backup
    but deliberately blocks restoring over an arbitrary changed game file.
    """
    receipt_path = Path(receipt_file).expanduser().resolve(strict=True)
    if receipt_path.name != "receipt.json" or receipt_path.is_symlink():
        raise GameSafetyError("Select a valid generated receipt.json")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GameSafetyError("Invalid backup receipt") from exc
    if receipt.get("schema") != 1 or receipt.get("status") != "ORIGINAL_BACKUP_ONLY_NO_MOD_INSTALLED":
        raise GameSafetyError("Unknown backup format or install state")
    slot = receipt.get("vehicle")
    profile = get_profile(slot)
    if receipt.get("original_relative_path") != "Cars/" + profile.source_filename or receipt.get("backup_file") != "original_pmt.sz":
        raise GameSafetyError("Backup location or target mismatch")
    root = Path(game_root).expanduser().resolve(strict=True)
    if str(root) != receipt.get("original_game_root"):
        raise GameSafetyError("Backup was created for a different game directory")
    backup = receipt_path.parent / "original_pmt.sz"
    if backup.is_symlink() or not backup.is_file() or file_hash(backup) != profile.source_sha256:
        raise GameSafetyError("Backup content fails original source signature")
    verified = verify_game(root, slot)
    return {"status": "ALREADY_ORIGINAL_NO_RESTORE_REQUIRED", "source_sha256": verified["source_sha256"], "game_files_changed": False}


def install_model(*_args, **_kwargs):
    raise GameSafetyError(
        "GAME_INSTALL_BLOCKED: No validated GLB-to-PMT/OVC serializer and no PC/VR runtime proof. "
        "Staged .blend/.glb is NOT a native OutRun car package."
    )