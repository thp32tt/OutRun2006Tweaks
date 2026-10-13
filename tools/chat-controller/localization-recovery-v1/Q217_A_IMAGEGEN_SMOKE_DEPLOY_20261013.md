# Portainer q217 A-only PNG upload / ImageGen smoke — 2026-10-13

## 실제 Portainer Stack 정본
- 사용자 스크린샷 기준 Git repository source: `OutRun2006Tweaks`.
- **Repository reference**: `refs/heads/localization-controller-recovery-20260928` (**korean-localization-recovery-20260928 아님**).
- **Compose path**: `tools/chat-controller/localization-recovery-v1/docker-compose.yml`.
- **Additional paths**: **빈 값** (이 브랜치에 직접 base Compose를 수정함). 앞서 다른 브랜치 `docker/localization-production/portainer-git-q217-a-smoke.override.yml`을 추가하라는 지시는 이 스택에는 적용하지 않는다.
- 실행 중 컨테이너 재배포·재시작은 사용자가 Portainer에서 수동으로 수행한다. Git commit/CI 성공이 배포 성공은 아니다.

## GitHub에 미리 적용한 작업
- `Dockerfile`: 4개 `src/controller.py.part*`을 합친 뒤 pinned `patch_controller_png_upload.py`를 빌드 시 적용. `controller_png_attach.py`를 실제 `/opt/outrun/app/`에 복사. 원본 anchor 변경 시 fail-closed.
- `docker-compose.yml`: 기존 controller service 및 `/data`/`/logs` 이름 있는 볼륨 유지. **하나의 입력 디렉터리만** `/home/chatgpt-runner2/work/a_q217_smoke_preflight/imagegen:/data/imagegen` bind로 추가. 이 경로는 *Docker daemon이 실행되는 실제 호스트*에 존재해야 한다. 서로 다른 머신에 Portainer/Docker가 있으면 작동하지 않으므로 실제 호스트를 먼저 확인한다.
- q217 PNG: N100 MCP 서버 `/home/chatgpt-runner2/work/a_q217_smoke_preflight/imagegen/inputs/A/Q217_D1039D6F_BASE_READABLE_FLIPY.png`, 3,735,331 bytes, SHA256 `56b3834649568383293786e862025351d0f2379ec632592cf40d78c532a50b15`.
- manifest: 같은 `imagegen/`의 `pending_A.json` (`task_id=OUTRUN-A-Q217-IMG-SMOKE-20261013`, original DDS SHA `d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0`, translations START→출발, GOAL→골).
- 실행 대상: `AUTO_SEND=true`, `CHAT_SLOTS=3`, `SCHEDULE_MINUTES=0`, `OUTRUN_A_SINGLE_SMOKE_TASK_ID=OUTRUN-A-Q217-IMG-SMOKE-20261013`, `WATCHDOG_ENABLED=false`. 첫 A `:00` 슬롯에서만 정확한 manifest 처리; B/C1/C2 등 다른 슬롯 자동 메시지 전송 금지. 기존 `/data`/로그 기록·과거 q217 QA/REWORK 상태는 보존한다.
- `pull_policy: build`: Git source에 있는 수정된 controller Dockerfile을 수동 redeploy 때 새로 build하게 지정한다.
- CI: `.github/workflows/localization-q217-a-imagegen-smoke-preflight.yml`에서 source patch / AST / SHA input / no-B scheduling / Compose mount 정적 테스트. **실제 Portainer runtime/UI ImageGen은 테스트하지 않는다.**

## 수동 재배포 전에 반드시 확인
1. **N100 실제 파일시스템 공간**: 2026-10-13 N100 MCP `system_status`는 `available_bytes=0`을 반환했고 새 임시 디렉터리 생성은 ENOSPC 실패. **디스크 여유 공간이 생기기 전 재배포 보류**. 운영/백업 데이터 및 named volumes를 임의 삭제하지 않는다.
2. Portainer Docker daemon이 **N100 동일 호스트**인지 확인. 호스트 디렉터리 `/home/chatgpt-runner2/work/a_q217_smoke_preflight/imagegen`가 실제 daemon에서 보이지 않으면 bind mount는 실패하거나 빈 폴더를 만든다. 동일 머신 검증 전에는 재배포 HOLD.
3. `/data/imagegen/pending_A.json`, `/data/imagegen/inputs/A/Q217_D1039D6F_BASE_READABLE_FLIPY.png`와 container-side SHA 실제 확인. `sent/A_OUTRUN-A-Q217-IMG-SMOKE-20261013.json` 기존 기록 있으면 **중복하지 않고 HOLD**, 지우지 않는다.
4. Portainer UI에서 Git repository URL/ref/Compose path가 위 정본과 같은지, build output에서 `OUTRUN_PNG_UPLOAD_V1_PATCHED`, 컨테이너에서 `OUTRUN_A_SINGLE_SMOKE_TASK_ID`, `AUTO_SEND`, scheduler, named volumes 확인.
5. **사용자가 수동** Portainer Pull and redeploy. GitHub 작업이 다른 서비스의 배포를 승인한 것은 아니다.
6. q217 한 번만: 실제 ChatGPT composer에 원본 파일 프리뷰, 전송 본문 TASK_ID, 이미지 생성 진행, 최종 출력 PNG 바이트/SHA 각각 따로 확인. 입력이 불량하면 fail closed / 무출력. `sent/`는 *메시지 전송*의 증거이지 ImageGen 완료의 증거가 아니다. 출력 생성 이후에도 CLEAN / native 75/50 QA / DDS / C1 / C3 / 실게임은 모두 별도 단계.
7. A-only 실험 이후 정상 스케줄 복귀는 **새 Git commit 및 사용자 수동 Portainer 재배포로만** 수행. q217 결과가 나오기 전에 정상 자동화로 자동 복귀하지 않는다.

## 13:00의 이전 실패 구분
- `korean-localization-recovery-20260928` QA JSON `A_Q217_IMAGEGEN_SOURCE_BINDING_QA.json`은 `generation.mode=ChatGPT native generation probe (NOT Portainer runtime)`, `actual_composer_source_attachment=false`, `source_reference_binding=FAIL`을 기록한다. 이 **채팅 자체의 source binding 실패**는 Portainer의 파일 업로드 기능이 이미 실패했다고 입증하지 않는다.
- 이번 GitHub 수정은 해당 원본 파일을 실제 **Portainer 컨트롤러 composer**에 첨부하는 경로를 준비하지만, 실제 사용자 수동 배포와 UI E2E 이전에는 `UPLOAD_RUNTIME=UNTESTED`, `IMAGEGEN_E2E=UNTESTED`, `RUNTIME_VALIDATION=UNTESTED`를 유지한다.
