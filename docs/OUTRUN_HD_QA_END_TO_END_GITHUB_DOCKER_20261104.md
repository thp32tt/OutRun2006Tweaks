# OutRun 2006 한글화 — GitHub 중심 HD QA / A·B·C1 재작업 파이프라인 (2026-11-04)

## 사용자 지시 / 배포 경계
- 2026-11-04 사용자 실제 JPG 검수: 원본보다 큰 글자, 영어 잔상 및 배경 침범은 불합격. 과거 60 DDS/200 ROI 결과는 새 QA에서 **정식 PASS가 아니다**.
- 원본 HD DDS 104개 / 기존 A/B ImageGen PNG 후보 954개 보존. 원본·기존 후보·과거 기록을 덮어쓰지 않는다.
- 도커 Pull latest / Rebuild / Redeploy, VNC 브라우저 로그인, 실게임 패치·시험은 사용자 담당. **GitHub 코드 커밋만으로 실제 브라우저 실행·이미지 생성·C1 합격을 주장하지 않는다.**

## 구현된 단계

| 단계 | 실행 위치 | 구현 | 승인 경계 |
|---|---|---|---|
| 1. HD 원본·A/B PNG 목록, SHA 고정 | GitHub asset 브랜치 | 104 DDS / 954 후보 | 소스 SHA 필수 |
| 2. 원문 투명 마스크만 제거·CLEAN·한글 축소·줄 수 보존 | GitHub Actions Python | `tools/localization/hd_strict_qa.py` | 불투명 배경·마스크 불명확·오버플로우 HOLD |
| 3. QA 실패 항목 사유별 분류 및 원본 HD PNG 증거 | GitHub Actions | `hd_rework_queue.py` | 최대 8건 (A/B 각 4), PNG SHA와 원본 SHA 검증 |
| 4. 별도 GitHub QA 큐에 독립 게시 | GitHub Actions | `publish_hd_rework_queue.py` | `korean-localization-qa-queue-20261104` 브랜치, 업로드 후 재조회 |
| 5. 빈 슬롯에 후속 QA 재작업 큐 보충 | GitHub 정기 작업 | `hd_qa_queue_refill.py`, master workflow `outrun-hd-qa-refill.yml` (매시간 :12/:42 UTC) | 기존 작업 ID 상태가 남았으면 재전송 방지 |
| 6. A/B ChatGPT 이미지 생성 및 PNG 저장 | 선택형 Portainer 브라우저 서비스 | `github_chat_rework_controller.py` | 실제 PNG 첨부, 생성 이미지 blob 1개, 재조회/파일 SHA 확인 |
| 7. 독립 C1 채팅 2장 원본/한글 비교 | 별도 C1 브라우저 탭 | 동일 worker C1 lane | 정확한 task ID, 원본 DDS SHA, 후보 SHA, 구조화 판단 없으면 HOLD |
| 8. C1 잠정 통과 후보 별도 저장 | GitHub asset 브랜치 | `localization/automation_inputs/qa_rework/approved/HDRW-*.png/.json` | 기존 후보 불변, C1_PRELIMINARY_PASS_NOT_C3, exact SHA |
| 9. 수정 PNG 자동 재조립·원본 HD QA 재검사 | GitHub Actions push 트리거 | `github_ab_imagegen_atlas_batch.py` | `TEST_ONLY`, C3/실게임 UNTESTED |
| 10. 최종 C3·실제 게임 검수 / 패치 | 별도 사용자 QA | 미자동화 | 사용자 승인 없이 RELEASE 불가 |

## 세부 품질 기준
- 원본 읽기 방향과 DDS 헤더/저장 바이트 보존.
- SOURCE→CLEAN→FINAL 별도 PNG와 원문/한글 줄별 실제 HD 글자·효과 bounding box 기록.
- 원문 영문 alpha/그림자까지 CLEAN 제거; 다른 UI를 섞은 불투명 배경을 임의 지우지 않음.
- 한글은 원문 글자보다 커지지 않으며 확대·가로 강제 늘리기·반대 기울기·줄 수 변경·잘림을 차단.
- 압축 DDS/독립 CLEAN 또는 실제 문자 마스크가 없는 경우 FAIL/CLEAN_EVIDENCE_HOLD. 아무 수량이든 원본 픽셀을 잘못 훼손하는 것보다 보류 우선.
- 이미 QA 실패한 정확한 SHA를 큐 재전송으로 무한 반복하지 않음. `queue/state/<task-id>.json`에 CLAIMED/SENT/C1_PENDING/REWORK/HOLD/임시 PASS 기록.
- C1은 실제 문구·크기·기울기·획 손상에 대한 별도 정성 판단이고, 최종 DDS/실게임 합격과 분리.

## Portainer 사용자 재배포
- Git Stack: `thp32tt/OutRun2006Tweaks`, 브랜치 `localization-controller-recovery-20260928`.
- 기존 `tools/chat-controller/localization-recovery-v1/docker-compose.yml` Stack을 그대로 Pull latest + Rebuild + Redeploy. **기존 볼륨 삭제 금지**.
- Portainer stack 환경변수:
  - `COMPOSE_PROFILES=chat-rework` (선택형 이미지 작업 컨테이너 활성화)
  - `OUTRUN_GITHUB_CONTENTS_TOKEN` (저장소 한정 Contents **Read and write** PAT; 채팅/파일/코드에 절대 출력하지 않음)
  - `OUTRUN_REWORK_VNC_PASSWORD` (별도 강한 VNC 암호; 미설정 시 시작 차단)
  - `CHATGPT_PROJECT_URL` (기존 한글화 ChatGPT 프로젝트 URL, 기본 `https://chatgpt.com/`)
  - `OUTRUN_REWORK_POLL_SECONDS=600` (옵션; 120~3600초, 기본 10분)
  - `OUTRUN_REWORK_VNC_BIND=6084` (옵션; 포트 충돌 시 다른 포트 사용)
- 브라우저 컨테이너는 별도 프로필 `/data/hd-rework/browser-rework-profile`을 사용. 최초 실행 후 VNC `http://N100_HOST:6084/vnc.html`에서 **사용자가 직접** ChatGPT 로그인해야 함.
- 기존 저부하 GitHub 모니터 `outrun-chat-controller-localization-recovery`는 0.1 CPU/96MB로 독립 유지. 브라우저 컨테이너는 필요할 때만 프로필 활성화(최대 0.65 CPU/1800MB).
- 실패/로그인 없음/UI 변경/이미지 생성 제한/파일 저장 실패는 `HOLD`. 자동 생성·저장·승인 성공이라고 주장하지 않음.

## 검증 증거
- GitHub 원본/QA asset branch `korean-localization-recovery-20260928`.
- GitHub QA 큐 branch `korean-localization-qa-queue-20261104`; `localization/automation_runs/hd_rework_queue/latest.json`.
- 기존 21/21 HD strict gate + 신규 5 queue + 4 C1 override 테스트: GitHub Actions 빠른 QA.
- 새 Portainer Chat rework CI `41778651158`: 코드/회귀 테스트 성공, **실제 ChatGPT 로그인/생성/다운로드/배포는 아직 미검증**.
- 최종 QA 풀 빌드는 동일 소스 SHA 완료와 실제 `qa_report.json`/GitHub queue refs 생성으로 추가 확인. 잘못된 JPEG 샘플의 품질을 CI 통과로 거짓 승인하지 않는다.

## 남은 작업
- 불투명·혼합 원문 영역의 독립 CLEAN 플레이트·마스크 확보, BC/DXT/mip 인코더, 좌표 중첩 매뉴얼 매핑, C3 및 게임 실제 QA는 기계적 PASS가 아니며 별도 해결 필요.
- 실제 도커 배포 후 A/B/C1 로그, 큐 상태, 결과 원본 SHA 증빙을 확인해 자동 루프가 정상 동작하는지 재검증한다.
