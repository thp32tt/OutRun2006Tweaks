from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Iterable


STATE_VERSION = 1


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def lane_defaults(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": spec["name"],
        "role": spec["role"],
        "branch": spec["branch"],
        "shard": spec.get("shard"),
        "backend": spec.get("backend"),
        "qa_batch_size": spec.get("qa_batch_size"),
        "job": None,
        "chat_url": None,
        "chat_started_at": None,
        "chat_jobs": 0,
        "idle_until": None,
        "last_send_at": None,
        "last_commit_sha": None,
        "last_result": None,
        "retry_clicked_at": None,
        "recycle_reason": None,
    }


def initial_state(mode: str, lane_specs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "mode": mode,
        "counter": 0,
        "lanes": {spec["name"]: lane_defaults(spec) for spec in lane_specs},
        "qa_pending": [],
        "completed": [],
        "rate_limit_attempts": 0,
        "rate_limit_until": None,
        "last_global_send_at": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def reconcile_state(
    state: dict[str, Any] | None,
    mode: str,
    lane_specs: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    specs = list(lane_specs)
    if not isinstance(state, dict) or state.get("version") != STATE_VERSION or state.get("mode") != mode:
        return initial_state(mode, specs)

    state.setdefault("counter", 0)
    state.setdefault("qa_pending", [])
    state.setdefault("completed", [])
    state.setdefault("rate_limit_attempts", 0)
    state.setdefault("rate_limit_until", None)
    state.setdefault("last_global_send_at", None)
    lanes = state.setdefault("lanes", {})

    configured = {spec["name"]: spec for spec in specs}
    for name in list(lanes):
        if name not in configured:
            lanes.pop(name, None)

    for name, spec in configured.items():
        current = lanes.get(name)
        if not isinstance(current, dict):
            lanes[name] = lane_defaults(spec)
            continue
        defaults = lane_defaults(spec)
        for key, value in defaults.items():
            current.setdefault(key, deepcopy(value))
        for key in ("name", "role", "branch", "shard", "backend", "qa_batch_size"):
            current[key] = defaults[key]

    state["updated_at"] = now_iso()
    return state


def next_job_id(state: dict[str, Any], lane: dict[str, Any]) -> str:
    state["counter"] = int(state.get("counter", 0)) + 1
    counter = state["counter"]
    role = lane["role"]
    if role == "localization_producer":
        prefix = f"LOC-{lane['name']}"
    elif role == "localization_qa":
        prefix = "LOC-C"
    else:
        prefix = f"CONV-{lane['name']}"
    return f"{prefix}-{counter:06d}"


def make_job(
    state: dict[str, Any],
    lane: dict[str, Any],
    base_sha: str,
    qa_inputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "job_id": next_job_id(state, lane),
        "role": lane["role"],
        "branch": lane["branch"],
        "base_sha": base_sha,
        "status": "READY",
        "created_at": now_iso(),
        "sent_at": None,
        "next_send_at": None,
        "turn_count": 0,
        "baseline_assistant_hash": None,
        "response_hash": None,
        "response_last_changed_at": None,
        "verify_started_at": None,
        "last_nonmaterial_sha": None,
        "last_nonmaterial_paths": [],
        "qa_inputs": deepcopy(qa_inputs or []),
        "force_full_prompt": True,
    }


def enqueue_qa(
    state: dict[str, Any],
    *,
    producer_job_id: str,
    sha: str,
    lane: str,
    branch: str,
) -> bool:
    pending = state.setdefault("qa_pending", [])
    identity = f"{producer_job_id}@{sha}"
    if any(item.get("identity") == identity for item in pending):
        return False
    pending.append(
        {
            "identity": identity,
            "job_id": producer_job_id,
            "sha": sha,
            "lane": lane,
            "branch": branch,
            "enqueued_at": now_iso(),
        }
    )
    return True


def select_qa_batch(state: dict[str, Any], batch_size: int) -> list[dict[str, Any]]:
    return deepcopy((state.get("qa_pending") or [])[: max(1, batch_size)])


def consume_qa_inputs(state: dict[str, Any], inputs: Iterable[dict[str, Any]]) -> int:
    identities = {str(item.get("identity") or f"{item.get('job_id')}@{item.get('sha')}") for item in inputs}
    before = list(state.get("qa_pending") or [])
    state["qa_pending"] = [
        item for item in before
        if str(item.get("identity") or f"{item.get('job_id')}@{item.get('sha')}") not in identities
    ]
    return len(before) - len(state["qa_pending"])


def material_commit_ok(role: str, paths: Iterable[str]) -> bool:
    paths = [str(p) for p in paths]
    if role == "localization_producer":
        return any(
            p.startswith("localization/graphics/hd_candidates/") and p.lower().endswith(".dds")
            for p in paths
        )
    if role == "localization_qa":
        allowed_prefixes = (
            "localization/progress",
            "localization/resume_state.json",
            "localization/graphics/asset_queue.csv",
            "localization/validation/",
            "localization/WORKLOG.md",
            "docs/automation/v05/",
        )
        return any(p.startswith(allowed_prefixes) for p in paths)
    if role == "conversion":
        material_prefixes = (
            "src/",
            "vr/",
            "tools/",
            "reverse/",
            "dxvk-fork/",
            "dx12poc/",
            ".github/workflows/",
            "docs/reverse/",
            "docs/file_formats/",
            "docs/shared-knowledge/",
        )
        material_exact = {
            "CMakeLists.txt",
            "cmake.toml",
            "OutRun2006Tweaks.ini",
        }
        return any(p in material_exact or p.startswith(material_prefixes) for p in paths)
    return bool(paths)


def record_completed(
    state: dict[str, Any],
    lane: dict[str, Any],
    job: dict[str, Any],
    sha: str | None,
    result: str,
) -> None:
    row = {
        "job_id": job["job_id"],
        "lane": lane["name"],
        "role": lane["role"],
        "branch": lane["branch"],
        "sha": sha,
        "result": result,
        "turn_count": int(job.get("turn_count", 0)),
        "completed_at": now_iso(),
    }
    state.setdefault("completed", []).append(row)
    state["completed"] = state["completed"][-200:]
