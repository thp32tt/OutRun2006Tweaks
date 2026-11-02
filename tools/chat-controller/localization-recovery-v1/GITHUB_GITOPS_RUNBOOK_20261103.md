# OutRun 2006 GitHub 연산 + 기존 Portainer 경량 컨트롤러 (2026-11-03)

## 실행 구조 — N100 연산 최소화
- **N100의 기존 Docker** outrun-chat-controller-localization-recovery: GitHub API 조회와 Actions 실행 요청만 수행. 이미지/DDS 파일 다운로드, PNG 합성, DDS 인코딩, QA Python 처리, ZIP 생성 **하지 않음**.
- **GitHub Actions ubuntu-latest의 일반 Python 프로세스**: DDS QA/저장/시험 ZIP 생성 및 GitHub artifact 업로드. GitHub Actions 안에서 Docker build/run 하지 않음.
- Github workflow: thp32tt/OutRun2006Tweaks@master 의 .github/workflows/outrun-korean-github-compute.yml. 매일 02:17 KST 예약 + asset 브랜치 관련 파일 push 시 자동 실행 + 수동 workflow_dispatch.
- Asset 브랜치: korean-localization-recovery-20260928. 2026-11-03 최초 GitHub 순수 Python 실행 41544581244 SUCCESS; artifact 13188516120. Q012/Q089/Q104 네이티브 DDS 3개 TEST_ONLY; QA 유닛 테스트와 2회 ZIP SHA 재현 PASS. C1/C3 및 실제 게임 미검수.
- 기본 저장장소: GitHub Actions artifact. 게임 자동 설치와 GitHub 저장소 상시 대용량 파일 push 없음.

## 변경된 Docker Stack
기존 Portainer Stack outrun-kor, 브랜치 localization-controller-recovery-20260928.
- Compose: tools/chat-controller/localization-recovery-v1/docker-compose.yml
- Build: Dockerfile.gitops (python:3.12-alpine; Pillow·Chrome·Playwright 불포함)
- Entrypoint: github_actions_light_controller.py. GitHub API로 asset branch head 및 최근 workflow run 조회, optional Actions:write token 있을 경우 신규 SHA에 대해 1회 workflow_dispatch.
- 1시간 1회 조회. Docker 제한 CPU 0.10, 메모리 96MiB. 실제 사용량 0을 뜻하지 않음. 미설정 토큰 시 GitHub 자체 schedule/push가 계속 연산하며 Docker는 조회만 수행한다.
- 이전 source 전량 다운로드와 Docker 안에서 DDS를 계산하던 github_gitops_worker.py는 **운영 경로에서 제외**되어 더 이상 실행되지 않음.
- 기존 Docker named volume outrun_chat_localization_recovery_data, outrun_chat_localization_recovery_logs 유지. 절대 삭제하지 않음. 브라우저/VNC 6083/8788은 새 모드에서 실행되지 않음.
- 선택적 환경변수 OUTRUN_GITHUB_ACTIONS_TOKEN: fine-grained GitHub PAT with repository Actions:Read and write. 비밀값을 소스/로그/채팅에 기재하지 않는다. 기존 OUTRUN_GITHUB_TOKEN을 새 모드에서 사용하지 않음.

## 검증 경계
- GitHub 순수 Python 작업: Actions run 41544581244 SUCCESS, artifact 13188516120 생성.
- 경량 컨트롤러 GitHub CI: Actions run 41544844038 SUCCESS (6/6 보안 테스트, Compose 정적 검사).
- Portainer 실제 재배포/컨테이너 동작: 아직 사용자 재배포 전이므로 **UNTESTED**. 기존 컨테이너를 정지/재배포했다고 주장하지 말 것.
- 전체 A/B PNG 후보 954개는 아직 GitHub 처리용 파일이 이관되지 않아 0/954. **전체 자동 한글화 완료가 아님**. 향후 GitHub 비공개 asset storage에 필요한 입력 이관 뒤 GitHub Actions 코드에서 확장. N100은 그 경우 한 번의 자산 이관만 필요하며 반복 컴퓨팅은 제외.
- 자원 소모를 **완전히 0으로** 하려면 기존 Portainer Docker를 Stop하고 GitHub Actions schedule/push만 사용한다. 사용자가 기존 Docker를 남기길 원하면 극히 작은 GitHub API 모니터 역할로만 유지.

## 사용자 배포
1. Portainer 기존 outrun-kor Stack Pull latest → Rebuild → Redeploy (동일 브랜치/Compose 유지).
2. 별도 GitHub dispatch 기능까지 원할 때만 Actions:Read/write 토큰 OUTRUN_GITHUB_ACTIONS_TOKEN 설정. 없어도 GitHub schedule/push 실행.
3. 볼륨 삭제 금지; 재배포 후 /data/gitops/last_status.json 및 로그의 execution_location=GITHUB_ACTIONS_UBUNTU_HOSTED_RUNNER 확인.

기존 GITHUB_GITOPS_RUNBOOK의 Docker 내 Python QA 명세는 이 문서가 대체한다.
