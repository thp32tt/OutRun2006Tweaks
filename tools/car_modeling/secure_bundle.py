#!/usr/bin/env python3
"""AES-256-GCM encrypted Ferrari Blender input/output bundle.

Public GitHub must contain only authenticated ciphertext, never raw game assets,
real photos, or proprietary .blend. Key belongs only in private N100 storage
and GitHub Actions Secret FERRARI_BUNDLE_KEY_B64. No secret is printed.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import stat
import zipfile

MAGIC = b"FERRARI_COCPIT_AESGCM_V1\n"
MAX_BUNDLE_SIZE = 160 * 1024 * 1024
ALLOWED_ROOTS = {"rea-input", "work_handoff", "outrun2_vr_refs"}
MANIFEST_NAME = "_ferrari_sha256_manifest.json"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def key_bytes(args):
    if args.key_file:
        path = Path(args.key_file)
        if not path.is_file():
            if not args.init_key:
                raise SystemExit("BLOCKED_KEY: private key file absent; --init-key only on N100")
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(path.parent, 0o700)
            key = secrets.token_bytes(32)
            with path.open("xb") as out:
                os.chmod(path, 0o600)
                out.write(base64.b64encode(key) + b"\n")
        data = path.read_text(encoding="ascii").strip()
    else:
        data = os.environ.get("FERRARI_BUNDLE_KEY_B64", "")
    try:
        key = base64.b64decode(data, validate=True)
    except Exception as exc:
        raise SystemExit("BLOCKED_KEY: invalid key encoding") from exc
    if len(key) != 32:
        raise SystemExit("BLOCKED_KEY: expected 32-byte AES256 key")
    return key


def check_name(name):
    p = PurePosixPath(name)
    if not name or name.startswith("/") or "\\" in name or ".." in p.parts or len(p.parts) < 2:
        raise ValueError("BLOCKED_PATH: unsafe private asset archive member")
    if p.parts[0] not in ALLOWED_ROOTS or p.name == MANIFEST_NAME:
        raise ValueError("BLOCKED_PATH: unapproved archive member")
    return p


def pack(args):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    root = Path(args.root).resolve()
    mem = io.BytesIO()
    manifest = {"format": 1, "scope": "private authorized Ferrari cockpit assets",
                "slot": args.slot, "files": {}}
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_STORED) as zipout:
        for relative in args.include:
            member = check_name(relative)
            source = (root / relative).resolve(strict=True)
            if not source.is_relative_to(root) or not source.is_file() or source.is_symlink():
                raise ValueError("BLOCKED_PATH: symlinks/escapes prohibited")
            data = source.read_bytes()
            if not data or len(data) > 80 * 1024 * 1024:
                raise ValueError("BLOCKED_INPUT: invalid private file size")
            manifest["files"][relative] = {"sha256": sha256(data), "size": len(data)}
            zipout.writestr(relative, data)
        zipout.writestr(MANIFEST_NAME, json.dumps(manifest, separators=(",", ":")))
    plaintext = mem.getvalue()
    if len(plaintext) > MAX_BUNDLE_SIZE:
        raise SystemExit("BLOCKED_SIZE: oversized encrypted bundle")
    nonce = secrets.token_bytes(12)
    sealed = MAGIC + nonce + AESGCM(key_bytes(args)).encrypt(nonce, plaintext, MAGIC)
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(sealed)
    os.chmod(out, 0o600)
    print(json.dumps({"status": "ENCRYPTED_ONLY", "slot": args.slot,
                      "ciphertext_sha256": sha256(sealed), "ciphertext_bytes": len(sealed),
                      "input_files": list(manifest["files"]),
                      "key_exported_to_log": False}, ensure_ascii=False))


def unpack(args):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    payload = Path(args.bundle).read_bytes()
    if len(payload) > MAX_BUNDLE_SIZE or not payload.startswith(MAGIC):
        raise SystemExit("BLOCKED_BUNDLE: invalid encrypted input")
    offset = len(MAGIC)
    nonce = payload[offset:offset + 12]
    if len(nonce) != 12:
        raise SystemExit("BLOCKED_BUNDLE: invalid nonce")
    data = AESGCM(key_bytes(args)).decrypt(nonce, payload[offset + 12:], MAGIC)
    root = Path(args.root).resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.namelist()
        if len(members) < 2 or len(members) != len(set(members)) or MANIFEST_NAME not in members:
            raise ValueError("BLOCKED_BUNDLE: malformed archive")
        manifest = json.loads(archive.read(MANIFEST_NAME))
        if args.slot != manifest.get("slot"):
            raise ValueError("BLOCKED_SLOT: private bundle belongs to another car slot")
        if set(members) != set(manifest["files"]) | {MANIFEST_NAME}:
            raise ValueError("BLOCKED_BUNDLE: inventory mismatch")
        files = {}
        for name, expected in manifest["files"].items():
            check_name(name)
            info = archive.getinfo(name)
            if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
                raise ValueError("BLOCKED_BUNDLE: link unsupported")
            if info.file_size > 80 * 1024 * 1024:
                raise ValueError("BLOCKED_BUNDLE: huge member")
            content = archive.read(name)
            if sha256(content) != expected["sha256"] or len(content) != expected["size"]:
                raise ValueError("BLOCKED_SHA: asset mismatch")
            files[name] = content
        for name, content in files.items():
            out = (root / name).resolve()
            if not out.is_relative_to(root):
                raise ValueError("BLOCKED_PATH: archive traversal")
            out.parent.mkdir(parents=True, exist_ok=True)
            if out.exists():
                if sha256(out.read_bytes()) != sha256(content):
                    raise ValueError("BLOCKED_INPUT: input already exists but differs")
            else:
                out.write_bytes(content)
                os.chmod(out, 0o600)
    print(json.dumps({"status": "VERIFIED_PRIVATE_INPUTS", "slot": args.slot,
                      "input_count": len(files), "key_exported_to_log": False}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("pack", "unpack"))
    p.add_argument("--slot", choices=("A", "C"), required=True)
    p.add_argument("--root", required=True)
    p.add_argument("--key-file")
    p.add_argument("--init-key", action="store_true")
    p.add_argument("--out")
    p.add_argument("--bundle")
    p.add_argument("--include", action="append", default=[])
    args = p.parse_args()
    if args.command == "pack":
        if not args.out or not args.include:
            p.error("pack needs --out and --include")
        pack(args)
    else:
        if not args.bundle:
            p.error("unpack needs --bundle")
        unpack(args)


if __name__ == "__main__":
    main()
