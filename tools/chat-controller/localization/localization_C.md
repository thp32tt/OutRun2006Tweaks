OutRun 2006 한글화 C 작업을 진행해줘. 역할은 A/B와 독립적으로 계속 동작하는 배치 QA consumer + 공용 상태 병합이다.

작업 기준은 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 최신 HEAD 하나뿐이다. N100 로컬 clone/worktree/작업파일, GPT Library, 과거 대화 진행률을 사용하지 마.

시작 즉시 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 최신 기준 파일을 읽어. 컨트롤러가 제공한 QA_BATCH_INPUTS의 각 TASK_ID + RESULT_SHA를 immutable 검수 기준으로 사용하고, A/B가 현재 무엇을 생산 중인지 기다리지 마.


Candidate-completion-first 정책을 지원해. pre-generation input을 PASS할 때 충분한 증거가 있으면 report에 `production_readiness`를 RENDER_READY / ONE_STAGE_TO_RENDER / PREFLIGHT_ONLY 중 하나로 기록해. RENDER_READY는 exact canonical source, source-effect/removal mask, 독립 QA된 CLEAN_PLATE, final candidate_safe_bbox, resolved semantic binding이 있고 실제 한글 렌더를 시작할 수 있는 상태다. baseline/slant/style 측정만 남은 경우에도 producer가 같은 invocation에서 측정 후 렌더할 수 있으므로 RENDER_READY로 분류할 수 있다. shared next_actions는 항상 RENDER_READY -> ONE_STAGE_TO_RENDER -> PREFLIGHT_ONLY 순으로 배치하고, unrelated preflight 확장을 candidate 완성보다 앞에 두지 마.

한 C task에서 QA_BATCH_INPUTS 전체를 한 번에 검수한다. 동일 asset/source SHA/candidate SHA/QA-contract fingerprint가 여러 입력에 반복되면 source identity, DDS header/mipmap/alpha/orientation, 1픽셀 containment, 영문원본-vs-한글후보 비교 같은 무거운 검사는 한 번만 수행하고 machine-readable 결과를 재사용해. 이미 같은 fingerprint로 PASS한 검사는 새 바이트/새 규칙/새 증거가 없으면 반복하지 마.

각 입력 result SHA에서 실제 candidate와 lane-local evidence를 읽고 의미/문맥/용어, 누락, 한글 깨짐, 글자 잘림, 원본 영역 1픽셀 초과, 해상도, DDS format/mipmap/alpha/투명도, 배경/오교체/고해상도 GUI를 검증해. 현재 HEAD에서 해당 candidate가 더 새로운 SHA로 대체됐다면 오래된 결과를 승인 상태로 덮어쓰지 말고 SUPERSEDED로 기록해. docs/automation/runs/<TASK_ID>.json 최상위에 각 QA_BATCH_INPUTS 항목의 task_id, result_sha, status를 담은 qa_dispositions 배열을 반드시 기록한다. status는 PASS, REWORK_REQUIRED, HOLD_STRICT_RECHECK, SUPERSEDED 중 하나다. 큰 실패는 해당 producer input만 REWORK_REQUIRED로 반환한다.

공용 상태는 이 QA batch 전체에 대해 마지막에 한 번만 병합한다. 최신 HEAD를 다시 읽은 뒤 localization/resume_state.json, localization/WORKLOG.md, canonical localization/progress/progress.json, localization/progress/STATUS.md, asset_queue.csv 및 필요한 공용 QA 상태를 충돌 없이 갱신해. canonical progress를 변경했다면 legacy localization/progress.json도 byte-for-byte 동일하게 갱신해.

C가 검수하는 동안 A/B 생산은 계속된다. C는 A/B 완료를 barrier로 기다리거나 다음 생산을 막지 않는다. 실제 결과를 docs/automation/runs/<TASK_ID>에 기록하고 commit 메시지에 [AUTO:TASK_ID]를 정확히 포함해. C commit 전 task record의 automation_validation은 PENDING으로 기록한다. C commit 하나가 batch 전체를 위한 유일한 Localization Automation Gate 대상이다. producer A/B commit에는 별도 runner Gate가 없다. 실기 테스트가 없으면 RUNTIME_VALIDATION=UNTESTED를 유지해. VR/FFB 및 빌드는 하지 마.