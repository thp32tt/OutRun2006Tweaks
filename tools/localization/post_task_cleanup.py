#!/usr/bin/env python3
"""Conservative cleanup for OutRun tasks: only registered scratch/worktrees."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

MARKER = ".outrun-managed-scratch.json"
HOME = Path.home().resolve()
SCRATCH = HOME / "tmp" / "outrun-managed-scratch"
REGISTRY = HOME / ".local" / "state" / "outrun-task-cleanup" / "worktrees"

def confined(path, root):
    p = Path(path).expanduser().absolute()
    if any(x.is_symlink() for x in (p, *p.parents) if x.exists()):
        raise ValueError("symlink path refused")
    p = p.resolve()
    if p == root or root not in p.parents:
        raise ValueError("outside permitted directory")
    return p

def marker(path):
    p = path / MARKER
    if p.is_symlink() or not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("kind") == "scratch" and d.get("path") == str(path) and d.get("uid") == os.getuid():
            return d
    except (ValueError, OSError):
        pass
    return None

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex[:8] + ".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()

def remove_scratch(path):
    path = confined(path, SCRATCH)
    if not marker(path):
        raise ValueError("unmarked scratch path refused")
    shutil.rmtree(path)

def run_task(args):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,90}", args.task_id):
        raise ValueError("invalid task id")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("command required after --")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    d = SCRATCH / (args.task_id + "-" + uuid.uuid4().hex[:12])
    d.mkdir(mode=0o700)
    save(d / MARKER, {"kind": "scratch", "path": str(d), "uid": os.getuid(),
                      "status": "running", "created": time.time()})
    env = os.environ.copy()
    env.update({"TMPDIR": str(d), "TMP": str(d), "TEMP": str(d),
                "OUTRUN_TASK_SCRATCH": str(d)})
    print("SCRATCH=" + str(d), flush=True)
    try:
        result = subprocess.run(command, env=env, check=False)
        rc = result.returncode
    except BaseException:
        rc = 1
        raise
    finally:
        if rc == 0:
            remove_scratch(d)
            print("CLEANUP=scratch-removed", flush=True)
        else:
            data = marker(d)
            if data:
                data["status"], data["ended"] = "failed", time.time()
                save(d / MARKER, data)
            print("CLEANUP=failed-task-preserved " + str(d), flush=True)
    return rc

def git(path, *arguments):
    return subprocess.run(["git", "-C", str(path), *arguments],
                          capture_output=True, text=True, check=False)

def verify_worktree(base, path):
    base = confined(base, HOME)
    path = confined(path, HOME / "work")
    pointer = path / ".git"
    if not base.is_dir() or not path.is_dir() or not pointer.is_file() or pointer.is_symlink():
        raise ValueError("linked worktree required")
    txt = pointer.read_text(encoding="utf-8").strip()
    if not txt.startswith("gitdir: "):
        raise ValueError("invalid gitdir pointer")
    gitdir = Path(txt[8:]).resolve()
    gitroot = (base / ".git" / "worktrees").resolve()
    if gitdir == gitroot or gitroot not in gitdir.parents:
        raise ValueError("Git worktree belongs to another repository")
    return base, path

def registration(path):
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()
    return REGISTRY / (digest + ".json")

def register(args):
    base, path = verify_worktree(args.base, args.path)
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,90}", args.task_id):
        raise ValueError("invalid task id")
    reg = registration(path)
    if reg.exists():
        raise ValueError("already registered")
    save(reg, {"kind": "worktree", "path": str(path), "base": str(base),
               "uid": os.getuid(), "task_id": args.task_id, "created": time.time()})
    print("REGISTERED=" + str(path))

def active(path):
    if not Path("/proc").is_dir():
        return True
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            cwd = (proc / "cwd").resolve(strict=True)
            if cwd == path or path in cwd.parents:
                return True
        except (OSError, RuntimeError):
            continue
    return False

def finish(path, dry_run=False):
    path = confined(path, HOME / "work")
    reg = registration(path)
    if not reg.is_file() or reg.is_symlink():
        return "SKIP unregistered " + str(path)
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
        if data.get("kind") != "worktree" or data.get("path") != str(path) or data.get("uid") != os.getuid():
            return "SKIP invalid registration"
        base, path = verify_worktree(data["base"], path)
        if active(path):
            return "SKIP active worktree " + str(path)
        status = git(path, "status", "--porcelain", "--untracked-files=all")
        if status.returncode or status.stdout.strip():
            return "SKIP dirty/untracked " + str(path)
        refs = git(path, "branch", "-r", "--contains", "HEAD")
        if refs.returncode or not any(x.strip().startswith("origin/") for x in refs.stdout.splitlines()):
            return "SKIP unpushed commit " + str(path)
        if dry_run:
            return "WOULD_REMOVE " + str(path)
        outcome = git(base, "worktree", "remove", str(path))
        if outcome.returncode:
            return "SKIP Git refused removal: " + outcome.stderr.strip()[:180]
        reg.unlink()
        return "REMOVED " + str(path)
    except (OSError, ValueError, KeyError):
        return "SKIP safety check failed " + str(path)

def prune(args):
    removed = 0
    if REGISTRY.is_dir():
        for entry in REGISTRY.glob("*.json"):
            if entry.is_symlink():
                continue
            try:
                d = json.loads(entry.read_text(encoding="utf-8"))
                if (d.get("kind") != "worktree" or d.get("uid") != os.getuid()
                    or time.time() - float(d.get("created", time.time())) < args.worktree_hours * 3600):
                    continue
                result = finish(d["path"], dry_run=args.dry_run)
                print(result)
                removed += result.startswith(("REMOVED ", "WOULD_REMOVE "))
            except (OSError, ValueError, KeyError, TypeError):
                continue
    if args.remove_failed and SCRATCH.is_dir():
        for d in SCRATCH.iterdir():
            if not d.is_dir() or d.is_symlink():
                continue
            data = marker(d)
            if data and data.get("status") == "failed" and time.time() - float(data.get("ended", time.time())) >= args.failed_hours * 3600:
                print(("WOULD_REMOVE " if args.dry_run else "REMOVED ") + "failed scratch " + str(d))
                if not args.dry_run:
                    remove_scratch(d)
                removed += 1
    print("PRUNE=" + str(removed))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest="action", required=True)
    a = s.add_parser("run", help="remove task scratch after successful completion")
    a.add_argument("--task-id", required=True)
    a.add_argument("command", nargs=argparse.REMAINDER)
    a = s.add_parser("register-worktree", help="opt-in linked worktree")
    a.add_argument("--base", required=True)
    a.add_argument("--path", required=True)
    a.add_argument("--task-id", required=True)
    a = s.add_parser("finish-worktree", help="remove only clean pushed registered worktree")
    a.add_argument("--path", required=True)
    a.add_argument("--dry-run", action="store_true")
    a = s.add_parser("prune", help="periodic recovery from missed worktree finalization")
    a.add_argument("--worktree-hours", type=float, default=24)
    a.add_argument("--failed-hours", type=float, default=168)
    a.add_argument("--remove-failed", action="store_true", help="default: preserve all failed tasks")
    a.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    try:
        if a.action == "run":
            return run_task(a)
        if a.action == "register-worktree":
            register(a)
        if a.action == "finish-worktree":
            print(finish(a.path, dry_run=a.dry_run))
        if a.action == "prune":
            prune(a)
        return 0
    except (OSError, ValueError) as e:
        print("ERROR " + str(e), file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
