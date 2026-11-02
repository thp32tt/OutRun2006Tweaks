# OutRun 2006: 기존 Portainer Docker → GitHub 한글화/QA GitOps (2026-11-03 KST)

## 실행 주체 교정

실제 작업은 GitHub-hosted runner가 아니라 **사용자의 기존 Portainer Docker 컨테이너** outrun-chat-controller-localization-recovery가 수행한다. GitHub Actions에서 Docker를 실행하도록 만들었던 잘못된 예약/Push 워크플로는 master와 korean-localization-recovery-20260928 양쪽에서 비활성화했다.

동작: 기존 Docker → GitHub 한글화 자산 브랜치 HEAD 조회 → SHA로 고정된 Python QA 코드와 소형 DDS 패키지 다운로드 → 컨테이너 내부 실행·TEST_ONLY 결과물 생성 → 재처리 방지 → (별도 쓰기 인증이 있을 때) 결과 JSON/ZIP을 GitHub에 커밋하고 원격 바이트 재확인.

## 코드·설정

- tools/chat-controller/localization-recovery-v1/docker-compose.yml: 기존 Stack/서비스 이름과 데이터·로그 named volume은 그대로 유지. Dockerfile.gitops로 경량 실행.
- Dockerfile.gitops: Python 3.12/Pillow, 기존 브라우저/Playwright 프로세스 없이 작동. 0.5 CPU/768MiB 메모리 제한.
- github_gitops_worker.py: GitHub HEAD와 자산 SHA를 조회하고, GitHub 안에 있는 7개 필수 입력을 받아 기존 tools/localization/github_docker_qa.py를 실행. SHA 기반 파일 지문, 중복 방지, TEST_ONLY 보호검증. 결과는 /data/gitops/results 아래.
- test_github_gitops_worker.py: 경로 탈출 차단, 미인증 무쓰기, 중복 실행 차단, 허위 RELEASE 차단 등 6개 유닛 테스트.
- GitHub 출력 (토큰 설정 후): localization/automation_runs/github_portainer/<input-fingerprint16>/qa_report.json 및 TEST_ONLY.zip. 파일 기존 동일 바이트는 재사용하고 내용이 다른 경우 HOLD. 원본 게임 DDS/후보 PNG 수정 없음.
- 기존 Chrome/VNC 접속 포트 6083/8788은 이 GitOps 모드에서 제공하지 않음. 브라우저 A/B/C1 세션과 기록은 기존 /data 볼륨에 보존하되 프로세스 실행만 중지.

## 검증 실적과 경계

- 기존 N100 MCP로 진행한 경량 독립 확인: GitHub 코드의 6/6 보안 단위 테스트 PASS, self-test PASS.
- 실제 GitHub HEAD (첫 통합 시험 기준) 87e5af11abcd5e29d1bfc9f3bffc73ddacaf19ea에서 소스 파일을 받아 QA 한 회차 실행 SUCCESS.
- GitHub 기보유 Q012/Q089/Q104 네이티브 DDS 3개 TEST_ONLY 생성, ZIP SHA256 b463761812f8785658bb1e36f6d7dc5049b2f8151defe23b760d3d0b4a300582 (기존 별도 CI 실험 SHA와 동일).
- 원래 GitHub에 없는 ImageGen A/B PNG 954개는 현재 0/954. 따라서 AWAITING_GITHUB_ASSET_IMPORT, 전체 자동변환 완료가 아님. 이전 v3 104 DDS ZIP은 N100에 안전하게 보존한다.
- 실제 통합 시험에는 Docker 내부 Github 쓰기 토큰이 없어 publish_status=NO_GITHUB_WRITE_TOKEN. 업로드 성공을 주장하지 않는다.
- 시각 QA(C1/C3)와 실게임 검증은 UNTESTED. 하드 게이트와 HOLD 유지.

## 사용자 수동 배포 (지금 필요)

기존 Portainer Git Stack outrun-kor, 브랜치 localization-controller-recovery-20260928, Compose tools/chat-controller/localization-recovery-v1/docker-compose.yml을 그대로 사용한다. **Pull latest → Rebuild → Redeploy**만 수행하며 볼륨 삭제/스택 삭제는 하지 않는다.

GitHub 결과 자동 커밋까지 사용하려면 Portainer 스택 환경변수 OUTRUN_GITHUB_TOKEN에 해당 저장소 하나의 Contents Read and write로 제한된 fine-grained PAT를 설정한다. 토큰을 GitHub 소스·채팅·로그에 공유하지 말 것. 토큰이 없더라도 GitHub 읽기와 컨테이너 내 QA, 볼륨 저장은 된다. 재배포 후 status=SUCCESS/native_dds_count=3을 로그에서 확인한다.

## 후속 확장

전체 954개를 GitHub 기반으로 생산하려면 해당 A/B PNG와 원본 HD·DDS를 권한 있는 비공개 GitHub 입력 저장소에 별도 이관해야 한다. 파일 경로 대응표만으로 이미지 바이트를 추측하거나 원본 게임 텍스처를 공개하지 않는다. GitHub 소스가 준비되면 Docker 안에 A/B 합성·DDS 인코딩 게이트를 추가하며 N100에 별도 반복 Python 워커를 띄우지 않는다.
