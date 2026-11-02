# GitHub-hosted Docker 자동 한글화 QA 전환 — 2026-11-03 KST

## 실행 결과
- GitHub Actions run [41470946864](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/41470946864): **SUCCESS**. GitHub-hosted ubuntu-latest 내부 Docker 실행. N100/Portainer 실행 불필요.
- 6개 단위 테스트 통과, 동일 입력에서 두 번 생성한 TEST_ONLY ZIP SHA 동일. GitHub Actions artifact #13154193440 생성.
- GitHub 생성 시험 ZIP SHA256: b463761812f8785658bb1e36f6d7dc5049b2f8151defe23b760d3d0b4a300582.
- 네이티브 DDS 3개: Q012, Q089, Q104. 원본 규격 BGRA/해상도/1 mip, DDS 바이트·디코드 검사 및 결과 SHA 검증.
- 기존 2개 시험 ZIP(Q032/Q241, AB8)은 네이티브 포맷·보호 아트·시각 QA 재확인이 필요하므로 HOLD.
- 출력: 자동 QA JSON/CSV, DDS→PNG 리뷰 이미지, TEST_ONLY ZIP. 모든 결과 release_approved=false, runtime_validation=UNTESTED, visual_qa=REVIEW_REQUIRED.
- 엔진: tools/localization/github_docker_qa.py, 컨테이너: tools/localization/ci/Dockerfile, 회귀시험: tools/localization/test_github_docker_qa.py.
- 예약: GitHub 기본 master 워크플로 .github/workflows/outrun-korean-docker-auto.yml. UTC 17:17 = KST 익일 02:17. 자산 브랜치에도 동일 워크플로를 등록하여 해당 브랜치 push 때 실행한다.
- Docker는 GitHub-hosted runner에서 네트워크 없이 읽기 전용 Git checkout, 제한된 CPU/메모리로 실행한다. 기존 N100의 outrun-kor Docker에 의존하지 않는다.

## 전체 954개 입력 자산의 실제 제약
GitHub asset 브랜치의 localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv에는 활성 954개 ROI의 목록만 존재한다. 955개 A/B 후보 PNG의 **실제 파일은 N100에 저장되어 있고 GitHub 호스트 checkout에는 아직 없다**. CI가 확인한 상태는 AWAITING_GITHUB_ASSET_IMPORT / github_candidates=0 / expected_active=954 이다.

원본 HD PNG 108개 및 현재 v3 104 DDS ZIP 또한 GitHub의 이 자동 작업 입력으로 완전하게 제공되어 있지 않다. 정적 QA 3 DDS 성공을 전체 한글화 완료라고 보고하지 않는다.

**다음 필수 선행 조건:** N100에 저장된 활성 954개 PNG와 SHA 고정 원본 HD PNG·원본 DDS를 일회성으로 GitHub 내부 비공개 입력 자산 보관소(예: 비공개 Release 또는 전용 private assets repository)에 이관해야 한다. 각 아카이브는 파일 크기·SHA256 고정 후 안전 추출한다. 공개 저장소에 게임 원본/HD 모드/대용량 후보 이미지를 무단 공개하거나 3GB 저장소에 무분별하게 추가하지 않는다. 이관 완료 후 GitHub-hosted Docker에서 합성→DDS 재인코딩→자동 QA→TEST_ONLY 패키징 확장. N100 반복 작업은 필요하지 않다.

## QA 및 배포 게이트
- Python 자동 검사: 파일 SHA, 원문 제거, 원본 보호 마스크, 배치 소유권, DDS 헤더/압축/mip/RAW/FLIP-Y, 저장→재디코드, ZIP 재현, 중복 및 안전 영역.
- 별도 독립 시각 검수: 오탈자·한글 자소·기울임·가독성·두 줄 아이콘, HUD 하트/Stage2/메뉴 상단/랭크·컨트롤러별 변형. 자동 정적 검사 합격은 시각 PASS 아님.
- 사용자 게임 테스트 전 RUNTIME_VALIDATION=UNTESTED. 최종 패키지 승인·설치는 사용자 판단.
- 기존 N100 이미지, 작업 상태, Portainer 데이터/볼륨을 보존한다. N100 Docker 컨트롤러 중지는 사용자가 별도로 할 수 있지만 삭제는 금지한다.

## 자동화 운영
- GitHub → Actions → OutRun Korean GitHub Docker QA에서 수동 실행 가능.
- 기본은 매일 자동 실행. 각 실행에서 SHA 재현과 GitHub 아티팩트를 확인한다.
- ChatGPT 기존 예약 작업은 동일 DDS 재생산과 N100 호출 대신 GitHub CI 검사·실패 알림 전용으로 바꾸는 것을 권장한다.
