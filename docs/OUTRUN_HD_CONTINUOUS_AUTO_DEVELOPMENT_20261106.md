# OutRun 2006 HD 한글화: 지속 자동개발 / 재시작 정책 (2026-11-06 KST)

## 실행되는 2개 자동 경로

1. **GitHub Actions 최소 부하 제어기**: 기본 브랜치 `master:.github/workflows/outrun-hd-korean-auto-controller.yml`, 매시 07분/37분 UTC (일정 지연 가능). Ubuntu GitHub-hosted Python으로 실행, 별도 Docker/N100 빌드 없음. 자산 브랜치 `korean-localization-recovery-20260928` 정확한 HEAD 및 GitHub Actions 실행 기록과 산출물 확인.
2. **ChatGPT 자동 기술개발·QA**: 기존 계정 자동화 ID `6ae873f373dc8191a80c1bfa86245a25`를 **시간당 1회**로 변경하고 새 개발 목표/안전 정책 반영. 남은 QA HOLD 원인을 조사해 안전한 변경만 GitHub에 커밋·CI 검증하는 역할. 이 일정은 GitHub CI와 별개의 자동화이며 실제 커밋/성공 여부를 매회 독립 검증해야 함.

## GitHub 자동 제어기가 하는 일

- 자산 HEAD의 최신 완전 DDS 빌드가 이미 실행 중이거나 대기 중이면 그대로 둠. 이전 SHA 빌드가 돌 때 새 코드 때문에 강제 취소하지 않음.
- HEAD와 정확히 일치하는 성공한 DDS 빌드에 `outrun-ab-multi-atlas-{run_id}` 아티팩트가 있고 유효하면 **신규 빌드 0회**.
- 마지막 성공 DDS SHA와 HEAD가 다르면 GitHub compare로 영향 파일을 확인. **자산·DDS 인코더·QA 코드·후보 PNG·원본 HD DDS 등 생산 입력 파일이 실제 변경됐을 때만** 새 전체 빌드 dispatch. 문서·감시 스크립트·점수판 변경은 불필요한 빌드 금지.
- 첫 실패는 **1회** 재실행. 두 번째 실패는 더 이상 반복하지 않고 담당 자동개발/QA로 원인 보정. 동일 SHA의 취소·아티팩트 누락·GitHub API 검증 불가도 무제한 자동 호출 금지.
- `outrun-ab-multi-atlas.yml`은 `master` 및 자산 브랜치 모두 **workflow_dispatch 전용**: 기존 Push 폭주와 매일 동일 리소스 블라인드 재빌드 제거. 빌드 concurrency `cancel-in-progress: false`.
- QA 읽기 전용 감사 `master:.github/workflows/outrun-hd-qa-refill.yml`는 계속 12/42분 UTC에 데이터 무결성만 검증. QA 감사 성공을 생산/게임 통과로 착각하지 않음.
- 빌드가 성공할 때만 `master:.github/workflows/outrun-hd-korean-preview-package.yml`에서 정확한 RUN ID·QA ZIP SHA를 검증한 **TEST_ONLY 설치 패키지** 생성. 설치는 사용자 PC에서 명시 동의한 경우에만 진행.

## 실제 완료 정의

- 현재 최신 확정 자료: 954 활성 한글 ROI 중 954 PNG 이관 완료, 250 ROI / 46 DDS **TEST_ONLY**, 704 ROI **HOLD**; 최근 BC3/DXT5 7개 아틀라스·13문구 카나리도 품질 기준에서 전부 HOLD. 새 DDS 통과 수가 확인되기 전까지 임의 가산 금지.
- GitHub 원본 DDS SHA 104종과 A/B PNG 우선, 원문 제거, 원본 이하 글자 크기·기울임·줄바꿈, 알파/인접 아이콘 보호, BC3 색/밉맵 보존. 뚜렷한 보호 픽셀/색상 손상은 HOLD.
- 자동화가 진행하는 것은 **GitHub 기술개발·변환·QA 증거 생산**이며, 컴퓨터 시각 검사가 현장 게임 확인을 대체할 수 없음. C1/C3 독립 시각 검수와 사용자 게임 실기검증 전 `release_approved=false`, `runtime_validation=UNTESTED` 유지. 자동으로 정식 배포하거나 사용자 게임 파일을 변경하지 않음.
- 자동화는 정상적인 품질 게이트가 충족될 때까지 계속 동작하지만, 증거 없는 범위에서는 완료를 보장하거나 가짜 PASS로 종료하지 않음. 잔여분이 수동 승인/새 ImageGen/실게임 테스트를 요구할 때만 사용자에게 필요한 항목을 통보함.
- 병목과 상태 갱신은 GitHub 최근 실행 ID/원격 HEAD/QA report SHA·`test_only_painted + hold = 954`을 기준으로 추적.
