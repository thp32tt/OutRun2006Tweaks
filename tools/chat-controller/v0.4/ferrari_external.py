"""Ferrari16 external-model automation lane (OutRun slot A only).

Uses the existing browser/queue transport but NOT the retired imsi1 cockpit
workpack. One authoritative GitHub queue, no duplicate TASK_ID on rollover.
"""
from __future__ import annotations

import base64
from datetime import datetime
from hashlib import sha256
import json
import re
import urllib.parse

EXTERNAL_QUEUE_PATH = "docs/automation/FERRARI16_EXTERNAL_AUTODEV_QUEUE.json"
SLOT = "A"
VALID_STAGES = {"source_fix", "source_research_conversion", "renderer_fix", "test_and_package", "hardware_qa"}
ELIGIBLE = {"ACTIVE", "IN_PROGRESS", "QUEUED"}


def choose_external_work(queue: dict, expected_repo: str, expected_branch: str) -> dict | None:
    """Fail closed unless GitHub's current work item is actionable and scoped."""
    if queue.get("schema_version") != 1:
        raise ValueError("unsupported external-model queue schema")
    if queue.get("repository") != expected_repo or queue.get("target_branch") != expected_branch:
        raise ValueError("external-model queue repository/branch mismatch")
    if queue.get("one_owner_slot") != "A" or queue.get("cadence_kst_minutes") != [0, 30]:
        raise ValueError("external-model queue ownership/schedule mismatch")
    work = queue.get("work")
    if not isinstance(work, list) or not work:
        raise ValueError("empty external-model queue")
    if len(work) != len({w.get("id") for w in work}):
        raise ValueError("duplicate external-model work IDs")
    active_id = queue.get("active_work_id")
    if not active_id:
        return None
    active = next((w for w in work if w.get("id") == active_id), None)
    if active is None:
        raise ValueError("active_work_id not found")
    if active.get("stage") not in VALID_STAGES or not re.fullmatch(r"EXT16-[0-9]{3}", active_id):
        raise ValueError("unsafe external-model work stage or ID")
    if active.get("status") not in ELIGIBLE:
        return None
    if active.get("requires_user_headset"):
        return None  # no automatic physical Quest3/HMD pass
    return active


def make_external_prompt(work: dict, queue: dict, source_sha: str, continuation: bool) -> str:
    task_id = work["id"]
    return "\n".join([
        f"[자동개발 외부차량] TASK_ID={task_id}, MODE=FERRARI16_EXTERNAL, CONTINUATION={int(continuation)}",
        "프로젝트=OutRun 2006 Ferrari16 외부 3D 모델·스테레오/PBR 정상화. 원본 운전석 PMT 형상 리워크 아님.",
        f"GitHub SSOT={queue['repository']}@{queue['target_branch']}; BASE_HEAD={source_sha}. 시작 즉시 해당 브랜치 실제 최신 HEAD 재조회.",
        f"작업 큐={EXTERNAL_QUEUE_PATH}, ACTIVE_WORK_ID={task_id}, STAGE={work['stage']}, TARGET={work['title']}. 이전 동일 TASK_ID 결과/CI가 있으면 이어받고 중복 작업 금지.",
        "작업 세부 완료 조건: " + "; ".join(work.get("acceptance") or []),
        "먼저 근거 있는 미완료 코드/모델 변환 결함을 1개 찾아 실제 수정하고 관련 양성/음성 회귀검증을 작성하라. 계획·검토·문서 반복만으로 작업을 끝내지 마.",
        "최근 사용자 보고: v0.03 원래 게임은 정상, 16대 외부 모델 브랜치는 양안 스테레오/렌더링/성능 회귀가 있음. 우선 실제 원인 추적·패치. PBR·노멀맵·투명도·대시보드·메뉴·VR 포커스 보존.",
        "모든 16대에 정확 차종·실내·UV/알베도/노멀/PBR·바퀴·계기 게이트. 328 GTS/575 Superamerica/F430 Spider 저품질 exact 후보 자동 승격 금지; Testarossa Spider 오픈탑 실차 확인.",
        "소스는 GitHub 우선, ChatGPT 작업환경 우선, N100에서는 사설 원본·대형 GLB/OVC 실측 및 최소 보조작업만 수행. N100 과부하 큰 빌드·반복검색 금지.",
        "소스/가공품 SHA, 차량별 재질·노멀·메시 QA, 음성 테스트, Windows x86 DLL+x64 host exact-SHA CI를 구분해서 기록. 기존 정상 릴리즈를 덮어쓰지 마.",
        "제3자 모델 저작권·변환/배포 조건 준수. 공개 Git에 외부 상용 모델 바이너리, 게임 원본, 인증정보 올리지 마. 유료 구매·차단 우회 불가.",
        "완료할 때만 같은 큐 JSON의 현재 항목 status=COMPLETE_STATIC, material SHA/CI evidence를 추가하고 active_work_id를 다음 QUEUED 작업으로 진행. 실패/차단이면 status=BLOCKED와 구체적 이유 및 대안 기록, 다음 독립 작업으로 진행.",
        "실기 Quest3 테스트는 사용자만 가능. HMD/RUNTIME_VALIDATION=UNTESTED 또는 WAITING_USER_HMD; 정적 CI로 가상현실 완성이라 주장하지 마.",
        "새 TASK_ID 발급·기존 중단 프로젝트 재개·우회 커밋·CI-skip 금지. 한 가지 완성된 수정 단위가 끝나면 실제 SHA 기록 후 다음 미완료 하위 단계를 계속 수행.",
        f"끝에 TASK_ID={task_id}, RESULT_SHA=<실제 SHA 또는 NONE>, MATERIAL_DELTA=<실제 변경>, NEXT_ACTION=<다음 구현>, RUNTIME_VALIDATION=UNTESTED를 기재.",
    ])


async def external_model_cycle(context, pages: dict, q: dict, now: datetime, host: dict) -> bool:
    """Schedule one owner at :00/:30 KST; state persists in /data queue JSON."""
    g = host.__getitem__
    if not (g("AUTO_SEND") and g("CAR_MODEL_AUTODEV_ENABLED") and g("EXTERNAL_MODEL_AUTODEV_ENABLED")):
        return False
    state = q.setdefault("ferrari_external_simple_A", {})
    if not q.get("ferrari_external_initialized"):
        reg = g("load_registry")(now)
        slot = next((s for s in reg.slots if s.name == SLOT), None)
        if slot is None:
            raise ValueError("external Ferrari A slot missing")
        if slot.url:
            state["retired_slot_url"] = slot.url
        slot.url = None
        slot.completed_tasks_in_chat = 0
        slot.last_result = "ferrari_external_A_initialized"
        state["new_chat_required"] = True
        state["initialized_at"] = now.isoformat()
        q["ferrari_external_initialized"] = True
        g("save_registry")(reg)
        g("save_queue_state")(q)

    if now.minute in (0, 30):
        window = now.replace(second=0, microsecond=0).isoformat()
        if state.get("last_sent_window") != window:
            state["pending_window"] = window
    pending = state.get("pending_window")
    if not pending or pending == state.get("last_sent_window"):
        return False
    try:
        pending_dt = datetime.fromisoformat(pending)
    except (TypeError, ValueError):
        state.pop("pending_window", None)
        g("save_queue_state")(q)
        return False
    if not 0 <= (now - pending_dt).total_seconds() < 1800:
        state.pop("pending_window", None)
        g("save_queue_state")(q)
        return False

    last = g("_parse_iso")(state.get("last_sent_at"))
    if last and (now - last).total_seconds() < 1800:
        return False
    repo = g("CAR_MODEL_GITHUB_REPO")
    branch = g("CAR_MODEL_TARGET_BRANCH")
    if repo != "thp32tt/OutRun2006Tweaks" or not branch.startswith("automation/ferrari16-external-"):
        raise ValueError("external-model lane must target dedicated OutRun branch")
    owner, name = repo.split("/", 1)
    api = g("github_api_json")
    prefix = f"/repos/{owner}/{name}"
    encoded_branch = urllib.parse.quote(branch, safe="")
    try:
        remote = api(f"{prefix}/contents/{EXTERNAL_QUEUE_PATH}?ref={encoded_branch}")
        if not isinstance(remote, dict) or remote.get("encoding") != "base64":
            raise ValueError("GitHub queue unavailable")
        queue = json.loads(base64.b64decode(remote["content"]))
        work = choose_external_work(queue, repo, branch)
        head_result = api(f"{prefix}/branches/{encoded_branch}")
        head = head_result["commit"]["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", head):
            raise ValueError("invalid GitHub branch HEAD")
    except Exception as ex:
        g("write_runtime")(status="external_model_ssot_unavailable", last_action=str(ex)[:250])
        return False
    if not work:
        g("write_runtime")(status="external_model_no_actionable_work",
                           last_action="Queue complete/blocked or waiting for physical HMD QA")
        return False

    signature = sha256((work["id"] + "|" + work["stage"] + "|" + head).encode()).hexdigest()
    if state.get("progress_signature") != signature:
        state["progress_signature"] = signature
        state["same_progress_dispatches"] = 0
        g("save_queue_state")(q)
    max_repeat = int(queue.get("max_unchanged_dispatches", 3))
    if int(state.get("same_progress_dispatches") or 0) >= max(1, min(max_repeat, 3)):
        g("write_runtime")(status="external_model_waiting_for_progress",
            last_action=f"{work['id']} no new GitHub HEAD after {max_repeat} sends; retry only after material progress")
        return False

    reg = g("load_registry")(now)
    slot = next((s for s in reg.slots if s.name == SLOT), None)
    if slot is None:
        return False
    guard = g("send_guard_reason")(reg, slot, now)
    if guard:
        g("write_runtime")(status="external_model_send_guard", last_action=str(guard))
        return False
    chat_start = g("_parse_iso")(state.get("chat_started_at"))
    rotate = bool(chat_start and (now - chat_start).total_seconds() >= 3600)
    if rotate:
        page = await g("hard_replace_slot_page")(context, pages, slot)
        state["chat_started_at"] = None
    elif state.get("new_chat_required"):
        page = await g("replace_with_fresh_slot_page")(context, pages, slot)
        state["new_chat_required"] = False
    else:
        page = await g("slot_page")(context, pages, slot)
        if slot.url and await g("detect_conversation_limit")(page):
            page = await g("replace_with_fresh_slot_page")(context, pages, slot)
            state["chat_started_at"] = None
    if not rotate and await g("detect_busy")(page):
        g("write_runtime")(status="external_model_busy", last_action="Existing external model work still generating")
        return False
    if not await g("ensure_logged_in")(page):
        g("write_runtime")(status="external_model_login_required", last_action="ChatGPT login required")
        return False
    if not g("is_slot_project_url")(page.url, SLOT):
        g("write_runtime")(status="external_model_wrong_project_blocked", last_action="OutRun project scope mismatch")
        return False
    if await g("detect_rate_limit")(page) or await g("detect_limit")(page):
        g("mark_rate_limit")(reg, datetime.now(g("TZ")), "external-model-A")
        return False
    if not await g("ensure_thinking_level")(page):
        return False
    prompt = make_external_prompt(work, queue, head, bool(last))
    outcome = await g("send_message")(page, prompt, slot_name=SLOT)
    if outcome != "sent":
        g("write_runtime")(status="external_model_send_retry", last_action=f"send outcome={outcome}")
        return False
    at = datetime.now(g("TZ"))
    if not slot.url:
        new_url = await g("wait_for_chat_url")(page, timeout_sec=8, slot_name=SLOT)
        if new_url:
            slot.url = new_url
    g("note_successful_request")(reg, at, SLOT)
    slot.runs += 1
    slot.last_sent_at = at.isoformat()
    slot.last_result = "external_model_task_sent"
    slot.last_assistant_hash = None
    slot.last_assistant_change_at = at.isoformat()
    slot.watchdog_resumes_since_schedule = 0
    g("save_registry")(reg)
    state["last_sent_at"] = at.isoformat()
    state["last_sent_window"] = pending
    state.pop("pending_window", None)
    if not state.get("chat_started_at"):
        state["chat_started_at"] = at.isoformat()
    state["new_chat_required"] = False
    state["last_task_id"] = work["id"]
    state["last_git_head"] = head
    state["same_progress_dispatches"] = int(state.get("same_progress_dispatches") or 0) + 1
    g("save_queue_state")(q)
    g("write_runtime")(status="external_model_running",
        last_action=f"{work['id']} dispatched KST :00/:30; Github HEAD={head[:12]}",
        external_model_task_id=work["id"], external_model_git_head=head,
        external_model_dispatches_without_progress=state["same_progress_dispatches"])
    return True
