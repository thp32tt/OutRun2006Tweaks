# OutRun 2006 HD 한글화 — 기존 Docker ChatGPT 첨부로 HOLD 재생성/QA 수렴 계획
기준일: 2026-11-08 KST
범위: UI 한글 이미지 / 검증된 원본 HD DDS. VR/FFB/DX11/DXVK 제외.
상태: 실행 설계안. 이 파일의 GitHub 등록은 Portainer 배포 또는 ImageGen 실행 증거가 아님.

## 1. GitHub에서 확인한 현재 상태
- Compose: `tools/chat-controller/localization-recovery-v1/docker-compose.yml`, 브랜치 `localization-controller-recovery-20260928`.
- 기존 `outrun-chat-qa-rework` 서비스: `Dockerfile.chat-rework`, `entrypoint.chat-rework.sh`, `github_chat_rework_controller.py`, `controller_png_attach.py`.
- noVNC 기본 호스트 포트 6084, 단일 로컬 CDP Chromium, 쿠키 보존 named volume. 현재 Compose 자원 상한은 CPU 1.50 / 메모리 3072m / shm 1g이며 실제 여유 메모리와 OOM 로그 검증 전 변경하지 않는다.
- `controller_png_attach.py`는 실제 로컬 PNG 바이트를 ChatGPT 파일 입력에 첨부하고 미리보기/영속 사용자 메시지를 구분해 검증한다. `github_chat_rework_controller.py`에는 A/B 원본 첨부·ImageGen 전송·결과 PNG 다운로드·SHA 확인·GitHub 기록, C1 원본+생성물 첨부·판정이 존재한다. 이는 코드 존재 확인이지 현재 live 성공 증거가 아니다.
- 2026-11-05부터 `OUTRUN_REWORK_REUSE_ONLY=1`이고 큐도 `new_imagegen_disabled=true`: 새 생성 전송은 막혀 있다.
- `korean-localization-qa-queue-20261104` 브랜치의 `localization/automation_runs/hd_rework_queue/latest.json` SHA e918c20c36f5d9147adb5629b912b497674e7721 기준: 원본 ROI 954, HOLD 654 = 이미지·CLEAN 43(A 23/B 20) + 엔진/좌표 594 + 증빙 17. `tasks=[]`, `source_reference_count_verified=0`, 기존 A/B 재사용 우선이다. 큐 상태는 향후 재측정한다.

## 2. 작업 원칙
- 우선순위: 재생성 없이 해결(기존 고품질 A/B PNG 재사용·알파 정리·원본 안전 bbox 안에서 비율 유지 리사이즈·CLEAN) > 재생성이 불가피한 글자/효과 부분만 ImageGen.
- 594개 ENGINE_OR_COORDINATE_HOLD를 ImageGen 큐에 넣지 않는다. 좌표/UV, CLEAN, 원본 DDS 포맷 및 엔진 결함 진단 별도.
- 17개 EVIDENCE_REVIEW_HOLD는 원본 PNG/DDS SHA, 실제 원문 ROI와 번역·마스크를 우선 복구한다.
- 43개 AB_IMAGE_AND_CLEAN_REWORK만 우선 후보 집합. 재검토 후 재생성이 필요한 실제 수를 측정하여 확정한다. 중복 `TASK_ID + source_dds_sha256 + source_crop_sha256`는 절대 재전송하지 않는다.
- 원본 글자/효과 영역보다 새 한글이 크게 나오면 FAIL. 한글 문구가 짧다는 이유만으로 FAIL하지 않는다. 원본 줄 수·기울기·보호 아트·투명 RGBA·CLEAN·원문 잔상·네이티브/축소 가독성 검사.
- 유료 API/임의 ChatGPT API는 사용하지 않는다. 이미 로그인한 사용자 ChatGPT UI 및 기존 무료 포함 ImageGen 경로만 검증한다.

## 3. 구현 단계 (GitHub에서 코드·CI, N100은 가벼운 VNC/전송만)
1. **인벤토리+재분류**: QA 최신 상태/원본/후보/좌표/번역을 SHA로 조인하는 GitHub Actions 스크립트. `REUSE_PASS | CLEAN_FIX | REGEN_REQUIRED | COORDINATE_FIX | EVIDENCE_BLOCKED`로 분류. 재검증한 결과만 큐에 반영; 654건을 모두 재생성하지 않는다.
2. **자동 복구 우선**: `REUSE_PASS` 및 `CLEAN_FIX`에는 기존 A/B PNG를 검증된 HD 원문 bbox 안에 종횡비 유지로 조절한다. 필요 시 알파 가장자리와 불필요 픽셀 제거, 영문 제거 마스크와 CLEAN 플레이트 별도 생성, 테스트 오버레이. 기존 후보 원본은 불변.
3. **재생성용 source reference 구축**: `REGEN_REQUIRED`에 한해 미분할 HD 원본에서 원문/효과 전체와 줄 관계가 확인된 ROI PNG(참조용)를 생성. 원본 DDS SHA·전체 HD PNG SHA·ROI XYXY·원문/번역·crop SHA·source PNG 파일을 증빙으로 묶는다. 대상별 GitHub refs 바이너리와 manifest를 업로드하여 다운로드 재조회 SHA가 통과할 때만 전송 가능한 `tasks` 작성. 현 큐의 `tasks=[]`/참조 0 상황을 해결하는 선행 조건.
4. **안전한 Docker 토글**: 현 `OUTRUN_REWORK_REUSE_ONLY=1` 기본 유지. 이미지 첨부 단건 smoke를 통과하고 미송신 REGEN_REQUIRED 태스크가 실제로 준비된 경우에만 선택적으로 `OUTRUN_REWORK_REUSE_ONLY=0`을 설정할 수 있게 한다. GitHub 작업 큐가 0이거나 SHA가 틀리거나 로그인/도구 선택 증거가 없으면 fail-closed. 수동 Portainer Pull+Rebuild+Redeploy 전에는 실제 설정 변경이 적용되지 않음.
5. **A/B 자동 첨부·생성**: 기존 `set_input_files` 실 첨부, 프리뷰 수량 증가 확인, ImageGen 도구 선택 확인, 제출 `UPLOAD_TASK_ID`가 포함된 사용자 영속 메시지 + 원본 썸네일 확인. 최초 1건 smoke. 성공 시 회차당 최대 2건(현재 코드 속도 제한), 작업별 독립 대화/이미지 하나. 같은 SHA 무한 재시도 금지; 실패 원인별 최대 2회 검토 뒤 HOLD 및 사람이 확인.
6. **이미지 회수/증빙**: 응답에 실제 이미지 1개가 있고 작업 식별/일치가 증명될 때만 PNG 저장. `candidate_sha256`, 투명도, 경계 침범, 픽셀 크기, 원본 SHA를 기록. 현재 GitHub Contents 경로에는 PNG당 650KiB 코드 제한이 있으므로 전송 전에 무손실 PNG 최적화와 대용량 저장 경로를 시험·마련해야 한다. 사이즈 초과를 성공 처리하지 않는다.
7. **C1 독립 QA**: A/B 후보에 원본 HD ROI+생성된 PNG를 실제 2장 첨부하고 SHA가 일치한 구조화 판정 `PASS_PROVISIONAL | REWORK_REQUIRED | HOLD_EVIDENCE`를 기록. 기존 이미지 재사용도 동일 정적 QA. C1은 최종 승인 아님.
8. **DDS 정적/실게임 게이트**: GitHub-hosted Actions에서 원문 제거 CLEAN, 보호 픽셀, RAW/FLIP-Y, bbox·줄 수, HD native/75%/50%·mip, DDS 헤더·압축·좌표를 검증하여 TEST_ONLY DDS 생성. 문제가 없는 후보만 C3/사용자 인게임 확인 단계로 넘긴다. 확인 전 `release_approved=false`, `runtime_validation=UNTESTED` 유지.
9. **운영/리소스**: GitHub Actions는 전처리·QA·합성을 담당. N100 Docker는 로그인 Chromium+로컬 임시 이미지 첨부·다운로드만. 현 3072m 상한은 메모리 부족 우려가 있으므로 실제 VNC/Chromium 상주 메모리 측정 후 단일 브라우저 context와 비활성 탭 정리 방식으로 점진적 축소 시험; 검증 전 무리한 동시 실행 금지.

## 4. 배포와 수용기준
- 1차 소스/큐/토글/결과 저장 변경은 개별 PR/CI로 검증하고 기존 볼륨/쿠키/로그를 절대 초기화하지 않는다.
- 배포 전에 테스트 태스크의 참조 원본 1개 다운로드 SHA PASS, GitHub 큐에 `tasks` 1개, 권한·로그인·VNC 상태를 확인한다.
- 배포 후 1건 실증: ChatGPT 사용자 첨부 메시지 확인 → ImageGen 결과물 1개 → 로컬+GitHub 원격 후보 PNG SHA 재조회 → C1 JSON 판정 → 정적 DDS TEST_ONLY 기록.
- 성공해야 재생성 대상 건수를 확대한다. 오류/캡/브라우저 변경 시 전송 중단·HOLD, 자동 과금/우회 호출 금지.
- 수동 작업: 사용자가 Portainer 기존 Stack `outrun-kor`에서 최신 Git ref를 Pull+Rebuild+Redeploy하고 필요 시 ChatGPT 로그인 확인. 배포 지시는 소스/CI 준비와 smoke 전제 조건을 확인한 뒤 요청한다.
- 작업 종결 조건: 재생성 대상/좌표·엔진/증빙 보류를 별도 집계하고, 원인 해결 후 GitHub QA·C3·사용자 실게임 판정까지 추적. 자동 수렴만으로 실게임 PASS 선언 금지.

## 5. 코드 수정 순서
- PR-A: SHA 기반 QA 분류기 + existing PNG salvage + 검증된 HD ROI reference builder.
- PR-B: `github_chat_rework_controller.py`의 선택적 REGEN_REQUIRED 전송, 추가 감시/재시도 게이트; Compose 환경 토글, 메모리 사용 로그.
- PR-C: 이미지 결과 저장 상한 안전 처리 + C1 결과 검증 + 원격 SHA readback.
- PR-D: GitHub Actions 정적 DDS/CLEAN/보호 픽셀 QA 및 통합 1건 실증.
