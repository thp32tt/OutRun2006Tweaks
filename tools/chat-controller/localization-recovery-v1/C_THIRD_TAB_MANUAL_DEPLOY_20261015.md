# 기존 A/B 컨트롤러 C 제3탭 추가 — 2026-10-15

상태: GITHUB_STAGED / LOCAL_TEST_PASS / LIVE_PORTAINER_UNTESTED.
실제 운영 컨트롤러 Git 브랜치: thp32tt/OutRun2006Tweaks, localization-controller-recovery-20260928.
기존 Stack: outrun-kor, 서비스: outrun-chat-controller-localization-recovery.

## 운영 역할

- A: 매시 00,10,20,30,40,50분. 기존 HD PNG ImageGen·배치 큐·첨부·증빙 보존.
- B: 매시 05,15,25,35,45,55분. 동일하게 유지.
- C: 매시 03,33분. **같은 컨트롤러의 제3 ChatGPT 탭**. 이미 만든 A/B PNG, 기존 PSD·원본 DDS 재활용, 텍스트 기반 작업만.
- C는 ImageGen/Create image, 유료 API, 새 ChatGPT 계정, 자체 C1/C3 최종승인을 하지 않음.
- 이전 C1/C2 기록은 보존. VR/FFB/DX11/DXVK 변경 없음.
- 구형 별도 C Docker 서비스는 optional-offline-c profile로 기본 비활성. 자동 시작 서비스는 기존 컨트롤러 1개.

## GitHub 변경 파일

- tools/chat-controller/localization-recovery-v1/patch_controller_c_slot.py: A/B 업로드 빌드 패치 후 C를 같은 컨트롤러에 등록하는 소스-anchor 검증 패치.
- tools/chat-controller/localization-recovery-v1/Dockerfile: A/B 빌드 패치 후 C 패치 적용/컴파일.
- tools/chat-controller/localization-recovery-v1/docker-compose.yml: CHAT_SLOTS=3과 03/33분 C 추가. A/B 환경 변수는 변경 안 함.
- tools/chat-controller/localization-recovery-v1/prompts/localization_C.md: 기존 A/B 제작분을 이용하는 C 작업 지시.
- tools/chat-controller/localization-recovery-v1/tests/test_controller_c_third_tab.py: 4개 컨트롤러 원본 part, 선행 A/B 패치, C 패치, AST 검사, 멱등성, A6/B6/C2 분별 매핑 시험.

## 사용자 수동 Portainer 배포

1. Portainer > Stacks > outrun-kor, Git URL/Reference/Compose 경로가 위 실제 컨트롤러 브랜치의 파일을 가리키는지 확인한다.
2. 기존 data/logs 볼륨, 브라우저 인증 프로필, A/B 작업 상태 보존. 사용자가 Pull and redeploy를 실행해 새 Dockerfile을 다시 빌드한다.
3. 배포 후 CHAT_SLOTS=3, 논리 역할 A/B/C, 14개의 schedule minute, C가 :03/:33에 기존 한국어 프로젝트에서 text 작업만 전송하는지 검사. A/B 첨부·큐 유지, C는 ImageGen 미사용, 별도 C 컨테이너가 생성되지 않아야 한다.
4. 문제가 있으면 이전 정상 Git 커밋을 사용자 수동으로 redeploy한다. 볼륨/기록 삭제 금지.

## 아까 주신 VR 주소

VR_PROJECT_URL=https://chatgpt.com/g/g-p-6ac1b6beb7308191bac67ba3c49b6d4f/project 는 VR용으로 이름 붙은 ChatGPT 프로젝트 주소이지 GitHub 주소가 아니다. 이 주소는 건드리지 않는다. 한국어 컨트롤러는 기존 OUTRUN_AB_PROJECT_NAME=아웃런 한글화 신규를 확인한다. C도 같은 프로젝트로 간다. 그 VR URL을 한국어 LOCALIZATION_PROJECT_URL에 무조건 복사하지 않는다.

## 검증

- 컨트롤러 4조각 조립, A/B → C 순차 빌드 patch, AST/compile, C 패치 재적용 무변경, A/B 분별 시간 12건 유지 및 C 2건 추가: N100 격리 PASS.
- 변경된 Compose yaml과 docker compose config --services: 기본 서비스 1개만 나옴. N100 PASS.
- 실제 Portainer 새 이미지 빌드, C ChatGPT 제출, 이후 게임 실행은 사용자 재배포 전까지 UNTESTED.
