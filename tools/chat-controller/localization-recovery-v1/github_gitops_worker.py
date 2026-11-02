#!/usr/bin/env python3
"""Existing Portainer container -> GitHub-source Korean localization QA GitOps.

No GitHub Actions Docker, Chrome/ImageGen/OCR, N100 processing service or paid API.
Fetches SHA-pinned repo inputs and invokes the repository's QA code inside THIS
container. Uses a fine-grained token only for safe, content-addressed publication.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = "thp32tt/OutRun2006Tweaks"
BRANCH = "korean-localization-recovery-20260928"
API = "https://api.github.com/repos/" + REPO
RAW = "https://raw.githubusercontent.com/" + REPO
FILES = (
    "tools/localization/github_docker_qa.py",
    "tools/localization/test_github_docker_qa.py",
    "localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv",
    "localization/test_packages/q012_native_format_test_only_20261102/OUTRUN_Q012_IMAGEGEN_NATIVE_FORMAT_1DDS_TEST_ONLY.zip",
    "localization/test_packages/OUTRUN_AB_Q089_Q104_NATIVE_2DDS_TEST_ONLY.zip",
    "localization/test_packages/OUTRUN_KOR_Q032_Q241_DDS_TEST_ONLY.zip",
    "localization/test_packages/ab_imagegen_alpha_composite_v4_20261102/OUTRUN_AB_IMAGEGEN_ALPHA_COMPOSITE_8DDS_TEST_ONLY.zip",
)
MAX_BYTES = 6 * 1024 * 1024
OUTPUT_ZIP = "OUTRUN_KOREAN_NATIVE_3DDS_STATIC_TEST_ONLY.zip"


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def urlopen(url: str, *, token: str = "", data: bytes | None = None,
            method: str = "GET", max_bytes: int = MAX_BYTES) -> bytes:
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "User-Agent": "outrun-existing-portainer-github-worker/1",
            "Accept": "application/vnd.github+json" if url.startswith(API) else "application/octet-stream",
            **({"Authorization": "Bearer " + token} if token else {}),
            **({"Content-Type": "application/json"} if data is not None else {}),
            "X-GitHub-Api-Version": "2022-11-28",
        })
    with urllib.request.urlopen(req, timeout=45) as response:
        if max_bytes < 0:
            return b""
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("REMOTE_RESPONSE_TOO_LARGE")
    return payload


def remote_head(token: str) -> str:
    url = API + "/git/ref/heads/" + urllib.parse.quote(BRANCH, safe="")
    obj = json.loads(urlopen(url, token=token))
    sha = obj["object"]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("REMOTE_SHA_INVALID")
    return sha


def safe_snapshot_path(root: Path, rel: str) -> Path:
    if rel not in FILES or "\\" in rel or ".." in Path(rel).parts:
        raise ValueError("UNAPPROVED_GITHUB_INPUT_PATH")
    return root / rel


def fetch_snapshot(root: Path, sha: str, token: str) -> str:
    """Download small bounded GitHub originals; do not use N100 source folders."""
    digest = hashlib.sha256()
    for rel in FILES:
        url = RAW + "/" + sha + "/" + "/".join(
            urllib.parse.quote(p, safe="") for p in rel.split("/"))
        payload = urlopen(url, token=token)
        target = safe_snapshot_path(root, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        digest.update(rel.encode("utf-8") + b"\0" + bytes.fromhex(hash_bytes(payload)))
    return digest.hexdigest()


def verify_test_only(report: dict, out: Path) -> None:
    if report.get("release_approved") is not False or report.get("runtime_validation") != "UNTESTED":
        raise ValueError("GATE_FALSE_RELEASE_APPROVAL")
    if report.get("visual_qa") != "REVIEW_REQUIRED" or report.get("native_dds_count") != 3:
        raise ValueError("GATE_NATIVE_OR_VISUAL_REVIEW_MISSING")
    if report.get("asset_inventory", {}).get("expected_active") != 954:
        raise ValueError("GATE_UNEXPECTED_ACTIVE_ROI_COUNT")
    pack = out / OUTPUT_ZIP
    if not pack.is_file() or hash_bytes(pack.read_bytes()) != report.get("test_only_sha256"):
        raise ValueError("GATE_OUTPUT_SHA_MISMATCH")


def execute_qa(snapshot: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    script = snapshot / "tools/localization/github_docker_qa.py"
    test = "test_github_docker_qa.py"
    test_dir = snapshot / "tools/localization"
    cmd = [sys.executable, "-m", "unittest", "discover",
           "-s", str(test_dir), "-p", test, "-v"]
    # Not even the repository's code gets a GITHUB_TOKEN environment variable.
    env = {k: v for k, v in os.environ.items() if k not in (
        "OUTRUN_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN")}
    test_result = subprocess.run(cmd, cwd=str(snapshot), env=env, timeout=90,
                                 capture_output=True, text=True)
    if test_result.returncode:
        raise RuntimeError("GITHUB_SOURCE_TESTS_FAILED: " + test_result.stderr[-1500:])
    run_result = subprocess.run(
        [sys.executable, str(script), "--repo-root", str(snapshot), "--out", str(output)],
        cwd=str(snapshot), env=env, timeout=180, capture_output=True, text=True)
    if run_result.returncode:
        raise RuntimeError("GITHUB_SOURCE_QA_FAILED: " + run_result.stderr[-1500:])
    report = json.loads((output / "qa_report.json").read_text(encoding="utf-8"))
    verify_test_only(report, output)
    return {"result": report, "tests_passed": True}


def validate_publish_path(path: str) -> None:
    if not re.fullmatch(
        r"localization/automation_runs/github_portainer/[0-9a-f]{16}/(?:qa_report\.json|TEST_ONLY\.zip)", path):
        raise ValueError("UNSAFE_PUBLISH_PATH")


def publish_new(path: str, payload: bytes, token: str) -> str:
    """Create once; existing same content is success, different bytes is HOLD."""
    validate_publish_path(path)
    if not token:
        return "NO_GITHUB_WRITE_TOKEN"
    url = API + "/contents/" + path
    try:
        existing = json.loads(urlopen(
            url + "?ref=" + urllib.parse.quote(BRANCH), token=token, max_bytes=750000))
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        existing = None
    if existing is not None:
        remote_content = existing.get("content")
        if existing.get("encoding") != "base64" or not isinstance(remote_content, str):
            raise ValueError("REMOTE_CONTENT_NOT_BASE64")
        if base64.b64decode(remote_content) != payload:
            raise ValueError("REMOTE_SAME_PATH_DIFFERENT_BYTES")
        return "ALREADY_PUBLISHED_EXACT"
    body = json.dumps({
        "message": "localization: record Portainer GitOps TEST_ONLY " + path.split("/")[-2],
        "content": base64.b64encode(payload).decode("ascii"),
        "branch": BRANCH,
    }, separators=(",", ":")).encode("utf-8")
    result = json.loads(urlopen(url, token=token, data=body, method="PUT", max_bytes=20000))
    if not re.fullmatch(r"[0-9a-f]{40}", result.get("commit", {}).get("sha", "")):
        raise ValueError("GITHUB_COMMIT_NOT_VERIFIED")
    # Full-byte readback prevents silently reporting a successful upload.
    response = json.loads(urlopen(url + "?ref=" + urllib.parse.quote(BRANCH),
                                  token=token, max_bytes=750000))
    if base64.b64decode(response.get("content", "")) != payload:
        raise ValueError("REMOTE_PUBLISH_READBACK_MISMATCH")
    return "PUBLISHED_EXACT:" + result["commit"]["sha"]


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".gitops-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def one_cycle(home: Path, token: str) -> dict:
    home.mkdir(parents=True, exist_ok=True)
    last_path = home / "last_run.json"
    state = json.loads(last_path.read_text(encoding="utf-8")) if last_path.is_file() else {}
    sha = remote_head(token)
    if (sha == state.get("remote_head") and state.get("status") == "SUCCESS" and
            (state.get("publish_status") == "PUBLISHED" or not token)):
        return {"status": "NO_NEW_GITHUB_SOURCE", "sha": sha[:12]}
    with tempfile.TemporaryDirectory(prefix="github-source-", dir=home) as temp:
        snapshot = Path(temp)
        fingerprint = fetch_snapshot(snapshot, sha, token)
        out = home / "results" / fingerprint[:16]
        if not (out / "qa_report.json").is_file():
            execute_qa(snapshot, out)
        report = json.loads((out / "qa_report.json").read_text(encoding="utf-8"))
        verify_test_only(report, out)
    basename = "localization/automation_runs/github_portainer/" + fingerprint[:16] + "/"
    # Never publish an unvalidated or falsely approved report.
    report_meta = {
        "schema": "outrun-existing-portainer-gitops-v1",
        "input_fingerprint_sha256": fingerprint, "source_repo": REPO,
        "release_approved": False,
        "runtime_validation": "UNTESTED", "visual_qa": "REVIEW_REQUIRED",
        "native_dds_count": 3, "native_test_sha256": report["test_only_sha256"],
        "asset_inventory": report["asset_inventory"],
        "github_controller": "EXISTING_PORTAINER_CONTAINER",
        "notes": "No automatic A/B full set without GitHub input asset import.",
    }
    payload = (json.dumps(report_meta, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    publish_status = "NO_GITHUB_WRITE_TOKEN"
    if token:
        # First publish the actual binary and then the receipt with matching hashes.
        z = publish_new(basename + "TEST_ONLY.zip", (out / OUTPUT_ZIP).read_bytes(), token)
        j = publish_new(basename + "qa_report.json", payload, token)
        publish_status = "PUBLISHED"
    state = {
        "status": "SUCCESS", "remote_head": sha, "input_fingerprint": fingerprint,
        "publish_status": publish_status, "finished_utc": now_iso(),
        "native_dds_count": 3, "source_asset_import_status":
            report["asset_inventory"]["status"],
        "source_asset_imported_count": report["asset_inventory"]["on_github"],
        "native_test_sha256": report["test_only_sha256"],
        "result_root": str(out),
        "github_report_path": basename + "qa_report.json",
    }
    atomic_json(last_path, state)
    return state


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="Perform one bounded cycle")
    p.add_argument("--home", default=None, help="Optional absolute state path for isolated manual smoke test")
    p.add_argument("--self-test", action="store_true", help="No network smoke test")
    args = p.parse_args()
    if args.self_test:
        validate_publish_path(
            "localization/automation_runs/github_portainer/0123456789abcdef/TEST_ONLY.zip")
        assert hash_bytes(b"hello") == hashlib.sha256(b"hello").hexdigest()
        assert not os.environ.get("GITOPS_DO_NOT_EXIST")
        print("GITOPS_SELFTEST_PASS")
        return
    home = Path(args.home or os.environ.get("OUTRUN_GITOPS_HOME", "/data/gitops"))
    if not home.is_absolute():
        p.error("OUTRUN_GITOPS_HOME must be absolute")
    token = os.environ.get("OUTRUN_GITHUB_TOKEN", "").strip()
    seconds = int(os.environ.get("OUTRUN_GITOPS_POLL_SECONDS", "3600"))
    if not 900 <= seconds <= 86400:
        p.error("OUTRUN_GITOPS_POLL_SECONDS must be 900..86400")
    while True:
        try:
            status = one_cycle(home, token)
            print(json.dumps(status, ensure_ascii=False, sort_keys=True), flush=True)
        except Exception as exc:
            error = {"status": "HOLD_RETRY", "error_type": type(exc).__name__,
                     "message": str(exc)[:800], "finished_utc": now_iso()}
            atomic_json(home / "last_error.json", error)
            print(json.dumps(error, ensure_ascii=False), flush=True)
            if args.once:
                sys.exit(2)
        if args.once:
            break
        time.sleep(seconds)


if __name__ == "__main__":
    main()
