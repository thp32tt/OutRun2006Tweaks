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


def choose_continuous_debug_work(queue: dict, expected_repo: str, expected_branch: str) -> dict | None:
    """When fixed work runs out, keep investigating independent, known open defects.

    This does not mark blocked/completed work as passed, nor auto-pass HMD QA.
    The same task ID is reused across 30-minute diagnostic dispatches.
    """
    policy = queue.get("continuous_debug_policy") or {}
    if policy.get("enabled") is not True:
        return None
    if queue.get("repository") != expected_repo or queue.get("target_branch") != expected_branch:
        raise ValueError("continuous debugging scope mismatch")
    debug_id = policy.get("work_id")
    if not isinstance(debug_id, str) or not re.fullmatch(r"EXT16-[0-9]{3}", debug_id):
        raise ValueError("invalid continuous debug work ID")
    item = next((w for w in queue["work"] if w["id"] == debug_id), None)
    if not item or item.get("continuous_debug") is not True or item.get("requires_user_headset"):
        raise ValueError("continuous debug work must be explicit and non-HMD")
    if item.get("stage") not in VALID_STAGES:
        raise ValueError("invalid continuous debug stage")
    # Never change persisted queue status or erase blocked evidence.
    return dict(item, status="ACTIVE")


def make_external_prompt(work: dict, queue: dict, source_sha: str, continuation: bool,
                         debug_iteration: int = 0, debug_focus: str = "") -> str:
    task_id = work["id"]
    continuous = work.get("continuous_debug") is True
    batch_policy = queue.get("development_batch_policy") or {}
    if (continuous and batch_policy.get("enabled") is True
            and batch_policy.get("work_id") == task_id):
        # Operator's implementation-first contract takes precedence over
        # the old generic "find one defect + test it" diagnostic template.
        return "\n".join([
            f"[자동개발 외부차량] TASK_ID={task_id}, MODE=FEATURE_BATCH, CONTINUATION={int(continuation)}, ITERATION={debug_iteration}",
            f"GitHub SSOT={queue['repository']}@{queue['target_branch']}; BASE_HEAD={source_sha}. 실제 최신 HEAD와 직전 작업 인수부터 확인.",
            f"QUEUE={EXTERNAL_QUEUE_PATH}; POLICY=development_batch_policy + atomic_stereo_plan. FOCUS={debug_focus}",
            "구현 우선: 기존 A1의 모든 예외 검증을 기다리지 말고 A2 실제 차량 전체 양안 stage, 직접 호출부/수명/복구, 다음 가능한 A3/A4 비활성 기능을 개발. A1은 직접 선행 의존성만 수정.",
            "이번 회차는 기능 묶음 개발이다. 작은 수정 하나, 첫 테스트 PASS, 첫 커밋으로 종료하지 마. 메인 구현 후 실제 호출 경로/연관 자원과 실패 경로까지 연결하고 다음 하위 구현을 같은 응답에서 계속해. 막히면 다음 독립적인 구현 의존성으로 전환.",
            "가용 실행 예산 대부분을 소스 구현에 사용(목표 개발 80%, 변경 영역 검증 15%, 기록 5%). 시간 채우기/줄 수 할당 금지. 이미 확인한 동일 SHA, 전체 차량 자료, 과거 CI 반복 검증 금지.",
            "한 기능 묶음 후 변경 영역 컴파일 및 핵심 양성/음성 테스트 1회. 관련 변경은 가능한 한 한 번에 커밋. 기존 자동 CI 유지; 개별 패치마다 전체 CI/패키지 완료를 기다리지 말고 다음 개발을 진행. 통합/배포 전 최종 exact-SHA 필수 검증은 유지.",
            "기존 v0.03, 양안 원자성, 실제 장면 깊이, 원본 fallback/ABI 보호. 실제 생산 백엔드와 통합 증거 없이 guard 해제 금지. HMD는 UNTESTED; 사설 모델/원본 공개 금지. GitHub/ChatGPT 로컬 우선, N100 최소 사용.",
            "EXT16-011 ACTIVE 유지. 작업 마무리는 실제 기능 묶음 구현과 연결 후 또는 불가피한 실행 한계에서만. 독립적으로 확인된 결함이 없으면 가짜 수정하지 말고 다음 실제 기능을 구현.",
            f"짧은 인수 기록만: TASK_ID={task_id}, SOURCE_SHA, 실제 구현 기능/경로, 남은 연결, 변경영역 테스트와 CI 상태, NEXT_SOURCE_ACTION. 중복 점수 금지.",
        ])
    preface = ([
        f"CONTINUOUS_DEBUG=1, DEBUG_ITERATION={debug_iteration}, ROTATING_FOCUS={debug_focus}",
        "영구 디버깅 큐: 기존 BLOCKED/COMPLETE_STATIC 근거를 보존하고 동일 EXT16-011 ID로 계속 추적한다. 원인을 못 찾았거나 이번 회차 코드 커밋이 없어도 작업을 종료/차단/완료로 바꾸지 마.",
        "이번 회차에는 ROTATING_FOCUS를 우선해 콜 그래프, 실패 경로, 예외, VR 렌더 상태, 16대 PBR 경계조건을 추적하라. 수정 가능한 실제 결함이면 소스+양성/음성 테스트 커밋; 결함이 입증되지 않으면 코드 변경을 꾸미지 말고 다른 경로를 조사하고 관찰 증거 및 다음 가설을 남겨라.",
        "00/30분 실행은 독립된 진단 회차다. 중복 검토/반복 보고를 신규 성과로 가산하지 말고, 사용자 Quest3 실기 통과·16대 개인 모델 실물을 자동으로 인증하지 마.",
        "이 작업 항목은 정적 CI 통과, 미발견, 자료 미확보, WAIT_INPUT만으로 영구 종료하지 않는다. 큐의 EXT16-011은 ACTIVE 유지, active_work_id도 EXT16-011 유지. 불가한 단일 가설은 기록 후 다음 회차로 넘긴다.",
    ] if continuous else [])
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
        *preface,
        ("이번 회차에 실제 수정했으면 결과 SHA와 테스트를 기록하되 EXT16-011 status/active_work_id는 유지하고 다음 진단 회차를 계속한다. 수정사항이 없으면 증거/가설만 정리하고 상태는 유지." if continuous else
         "완료할 때만 같은 큐 JSON의 현재 항목 status=COMPLETE_STATIC, material SHA/CI evidence를 추가하고 active_work_id를 다음 QUEUED 작업으로 진행. 실패/차단이면 status=BLOCKED와 구체적 이유 및 대안 기록, 다음 독립 작업으로 진행."),
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

    # Recover the current half-hour window after a restart or a slow browser
    # operation instead of requiring a poll during the exact boundary minute.
    window = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0).isoformat()
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
    # Distinct :00 and :30 windows, even if the previous browser send was delayed.
    # Keep a minimum safety gap for rate-limit and accidental clock overlap.
    if last and (now - last).total_seconds() < 600:
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
        if work is None:
            work = choose_continuous_debug_work(queue, repo, branch)
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
    # Continuous diagnostics must not stop just because no new commit was found.
    # Every 30-minute window is a new hypothesis, NOT a fake material success.
    if not work.get("continuous_debug") and int(state.get("same_progress_dispatches") or 0) >= max(1, min(max_repeat, 3)):
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
    debug_iteration = int(state.get("debug_cycle_count") or 0) + 1
    rotation = (queue.get("continuous_debug_policy") or {}).get("focus_rotation") or []
    if work.get("continuous_debug") and rotation:
        debug_focus = str(rotation[(debug_iteration - 1) % len(rotation)])[:320]
    else:
        debug_focus = ""
    prompt = make_external_prompt(work, queue, head, bool(last), debug_iteration, debug_focus)
    outcome = await g("send_message")(page, prompt, slot_name=SLOT)
    if outcome != "sent":
        g("write_runtime")(status="external_model_send_retry", last_action=f"send outcome={outcome}")
        return False
    # Use this dispatch cycle's aware KST instant for durable send accounting.
    # It makes :00/:30 rollover and dedup tests deterministic.
    at = now
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
    if work.get("continuous_debug"):
        state["debug_cycle_count"] = debug_iteration
        state["debug_focus"] = debug_focus
    state["last_git_head"] = head
    state["same_progress_dispatches"] = int(state.get("same_progress_dispatches") or 0) + 1
    g("save_queue_state")(q)
    g("write_runtime")(status="external_model_continuous_debug" if work.get("continuous_debug") else "external_model_running",
        last_action=f"{work['id']} debug cycle={debug_iteration} focus={debug_focus[:100]} Github HEAD={head[:12]}" if work.get("continuous_debug") else f"{work['id']} dispatched KST :00/:30; Github HEAD={head[:12]}",
        external_model_task_id=work["id"], external_model_git_head=head,
        external_model_dispatches_without_progress=state["same_progress_dispatches"])
    return True
