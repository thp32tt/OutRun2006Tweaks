from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Iterable
import re


STATE_VERSION = 1

GITHUB_CONNECTION_FIRST_LINE = "깃허브 연결은되어 있다 오류가 난다면 정상연결될때까지 무제한 다시 연결 상태를 확인한다"
GITHUB_TOOL_RECOVERY_MESSAGE = "진행해"
LOCALIZATION_QUEUE_RECOVERY_MESSAGE = (
    "계속 진행해. asset_queue.csv를 한 번에 전체 조회하지 말고 GitHub 파일 조회의 "
    "start_line/end_line 범위로 40~80줄씩 나눠 읽어. API 응답의 JSON wrapper나 출력 "
    "truncation을 실제 CSV가 단일 JSON 라인인 것으로 오인하지 마. CSV의 실제 index 값으로 "
    "shard(index % 3)를 판정하고 필요한 다음 범위를 계속 조회한 뒤, 같은 JOB_ID로 runnable "
    "asset을 확정해서 DDS 생성, 검증, material commit까지 끝내."
)
LOCALIZATION_BINARY_RECOVERY_MESSAGE = (
    "계속 진행해. GitHub 연결은 정상이며 지금 문제는 DDS 바이너리를 UTF-8/text API로 직접 "
    "읽으려 한 접근 방식이다. 바이너리 payload를 채팅으로 읽지 못하는 것은 파일 부재나 작업 "
    "불가가 아니다. 같은 바이너리 조회를 반복하지 말고 현재 branch에서 선택 asset 이름/경로를 "
    "기준으로 기존 GitHub Actions workflow, 생성 스크립트, QA/rework artifact를 먼저 찾는다. "
    "GitHub Actions가 checkout 또는 pinned release/archive에서 canonical source DDS를 서버측으로 "
    "읽고 기존 deterministic renderer/rework script를 실행하게 하라. 필요한 경우 같은 JOB_ID용 "
    "작은 text dispatch/request와 lane-safe workflow를 만들고 Actions 결과를 확인해서 최종 "
    "localization/graphics/hd_candidates/...dds material commit [AUTO:<JOB_ID>]까지 끝낸다. "
    "특히 index222/DDF0392A는 current branch의 .github/workflows/localization-a00221-ddf0392a.yml "
    "및 연결된 generate_index222 parts를 기존 증거로 확인하고, 현재 canonical translation과 "
    "현재 JOB_ID에 맞게 재사용/적응한다. 'binary payload를 확보할 수 없음'으로 응답을 끝내지 마."
)


def prepare_outgoing_message(message: str) -> str:
    """Force the GitHub recovery instruction to be the first line of every controller send."""
    body = (message or "").lstrip("\r\n")
    if body == GITHUB_CONNECTION_FIRST_LINE or body.startswith(GITHUB_CONNECTION_FIRST_LINE + "\n"):
        return body
    return GITHUB_CONNECTION_FIRST_LINE + "\n" + body


GITHUB_TOOL_UNAVAILABLE_PATTERNS = [
    r"(?:github|git허브|깃허브).{0,180}(?:connector|커넥터|plugin|플러그인|tool|도구|namespace|네임스페이스|호출 인터페이스).{0,180}(?:not\s+available|unavailable|not\s+exposed|cannot\s+access|can(?:not|'t)\s+use|노출되지|연결하지 못|사용할 수 없|접근할 수 없|호출할 수 없)",
    r"(?:connector|커넥터|plugin|플러그인).{0,120}(?:github|git허브|깃허브).{0,180}(?:not\s+available|unavailable|not\s+exposed|노출되지|연결하지 못|사용할 수 없)",
]


def github_tool_unavailable_response(text: str) -> bool:
    sample = (text or "").lower()
    return any(re.search(pattern, sample, flags=re.I | re.S) for pattern in GITHUB_TOOL_UNAVAILABLE_PATTERNS)


GITHUB_READ_LIMIT_PATTERNS = [
    r"(?:github|git허브|깃허브).{0,220}(?:api|응답|response|output|출력|파일|file).{0,220}(?:too large|truncat|잘리|대형|너무 크|끝까지 확인할 수 없|후반부.{0,40}확인할 수 없)",
    r"(?:asset_queue[.]csv|progress[.]json|resume_state[.]json).{0,220}(?:단일 대형|single large|truncat|잘리|끝까지 확인할 수 없|후반부.{0,40}확인할 수 없)",
    r"(?:runnable|unfinished|후보|asset).{0,180}(?:확정|판별|선택).{0,120}(?:불가|할 수 없).{0,180}(?:queue|candidate|원본|정보|응답)",
]


def github_read_limit_response(text: str) -> bool:
    sample = (text or "").lower()
    return any(re.search(pattern, sample, flags=re.I | re.S) for pattern in GITHUB_READ_LIMIT_PATTERNS)


LOCALIZATION_BINARY_BLOCKER_PATTERNS = [
    r"(?:github|git허브|깃허브).{0,160}(?:text api|텍스트 api|utf-?8).{0,220}(?:binary|바이너리|dds).{0,220}(?:읽|read|access|접근|payload|bytes|바이트|확보).{0,120}(?:못|불가|없|cannot|unavailable|failed)",
    r"(?:binary|바이너리|dds).{0,180}(?:payload|bytes|바이트|원본).{0,220}(?:직접 읽|읽을 수 없|확보되지|접근할 수 없|cannot read|cannot access|unavailable|not available)",
    r"(?:원본|source).{0,80}dds.{0,180}(?:payload|bytes|바이트|입력).{0,180}(?:확보되지|없|불가|cannot|unavailable)",
    r"(?:실제|canonical|원본).{0,120}(?:dds|binary|바이너리).{0,220}(?:확인할 수 없|확보할 수 없|확보되지|읽을 수 없|존재하지|없었다|불가)",
    r"(?:dds|binary|바이너리).{0,180}(?:source|원본|candidate|후보).{0,220}(?:branch|브랜치).{0,180}(?:없|확인되지|읽을 수 없|존재하지)",
    r"(?:canonical source|canonical source/candidate|원본/후보).{0,220}(?:확보할 수 없|확보되지|확보하지 못|도달하지 못|없었다)",
    r"(?:dds 원본/후보|원본/후보 바이너리|source binary).{0,220}(?:확보|읽기|접근).{0,160}(?:못|불가|없|도달하지 못)",
    r"(?:파일 객체|file object).{0,120}(?:존재하지|없).{0,180}(?:dds|source|candidate|canonical)",
]


def localization_binary_blocker_response(text: str) -> bool:
    sample = (text or "").lower()
    return any(
        re.search(pattern, sample, flags=re.I | re.S)
        for pattern in LOCALIZATION_BINARY_BLOCKER_PATTERNS
    )


RETRY_ERROR_PATTERNS = [
    r"something went wrong",
    r"there was an error (?:generating|producing) (?:a )?response",
    r"network error",
    r"failed to generate",
    r"문제가 발생했습니다",
    r"응답.{0,30}오류",
    r"네트워크.{0,20}오류",
]


def retry_surface_has_platform_error(text: str) -> bool:
    sample = (text or "").lower()
    return any(re.search(pattern, sample, flags=re.I | re.S) for pattern in RETRY_ERROR_PATTERNS)


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
