# OutRun 2006 HD 한글화 자동 완성 계획 — 2026-11-03 KST

## 목표

HD 모드를 기준으로 **104개 활성 HD DDS / 954개 활성 한글 ROI**를 GitHub 정본에서 반복 재현 가능한 TEST_ONLY 패키지로 완성한다.

최종 우선순위는 다음과 같다.

1. **A/B가 이미 제작한 실제 고품질 ImageGen PNG**
2. SHA256이 고정된 OR2-HD-GUI 원본 DDS
3. 954행 crosswalk의 원본 DDS SHA / HD PNG SHA / bbox / 영문 / 한글 / A/B 소유권
4. A/B가 아직 GitHub에 이관되지 않았거나 안전하게 적용할 수 없는 ROI만 deterministic fallback으로 임시 커버
5. C1/C3 및 실제 HD 모드 게임 검증 전에는 항상 TEST_ONLY

일반 폰트 fallback은 A/B를 대체하는 최종 품질 경로가 아니다. 이번 완료 파이프라인에서는 **전체 커버리지 공백을 없애기 위한 TEST_ONLY 안전망**으로만 사용하며, 동일 ROI의 A/B PNG가 정상 적용되면 자동으로 A/B 결과가 우선한다.

## 정본

- 저장소: `thp32tt/OutRun2006Tweaks`
- 자산 브랜치: `korean-localization-recovery-20260928`
- HD 업스트림: `Sonic-TV/OR2006Sprites`
- 고정 커밋: `a95efe01d1f136514cef94b0d9e9fd61df021754`
- HD source plan: `localization/automation_inputs/hd_original_png_source_plan.json`
- 954 ROI crosswalk: `localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv`
- A/B 실물: `localization/automation_inputs/candidate_outputs/A|B/`

## H0 — 104 HD DDS 원본 확보

워크플로:
`.github/workflows/sync-hd-localization-source.yml`

동작:
- source plan의 104개 distinct target을 읽는다.
- 업스트림 고정 커밋 `Release/`에서 각 DDS를 GitHub-hosted runner가 직접 받는다.
- 각 바이트 SHA256이 source plan의 `original_dds_sha256`과 일치할 때만 사용한다.
- 기존 `hd_source` 파일이 다른 SHA이면 덮어쓰지 않고 즉시 실패한다.
- 104/104 확인된 원본만 `localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/`에 commit 한다.

완료 조건:
- distinct source DDS = 104
- SHA mismatch = 0
- source plan 누락 = 0

N100은 이 단계에 사용하지 않는다.

## H1 — A/B 954 PNG GitHub 증분 이관

현재 crosswalk는 954 ROI를 각각 A=453, B=501로 정확히 한 번 배정한다.

N100 역할은 최소화한다.
- 기존 A/B PNG의 **읽기 + SHA256 + GitHub 전송만**
- 재렌더링, DDS 합성, 대규모 이미지 처리 금지
- 파일 바이트 변경 금지
- 대상 파일명은 crosswalk의 기존 N100 candidate path basename과 정확히 일치해야 한다.

GitHub에 PNG가 들어올 때마다 completion workflow가 push trigger로 자동 재실행된다.

완료 조건:
- `candidate_outputs`의 활성 crosswalk 일치 = 954/954
- unmatched/legacy는 설치 대상에서 제외
- A/B 원본 SHA는 이관 기록과 일치

## H2 — DDS별 단일 합성

워크플로:
`.github/workflows/outrun-hd-korean-completion.yml`

엔진:
`tools/localization/github_hd_hybrid_completion.py`

핵심:
- 954 ROI를 104 source DDS별로 group 한다.
- 하나의 DDS 안에 여러 ROI가 있으면 최종 DDS를 한 번만 쓴다.
- 원본 crop bbox끼리 겹치는 경우 전체 bbox 충돌만으로 DROP하지 않는다.
- 먼저 비중첩 ROI를 배치하고, 겹침 ROI는 이미 그린 실제 glyph ink만 보호하여 free rectangle을 계산한다.
- 동일 번역/거의 동일 ROI(IoU >= 0.8)는 `DUPLICATE_TRANSLATION_REPRESENTED`로 1회 표현한다.
- A/B PNG가 존재하고 투명/경계 조건을 통과하면 해당 fallback glyph의 안전 ink box 안에서 A/B 이미지를 우선 적용한다.
- A/B가 없거나 후보가 안전 조건을 통과하지 못하면 fallback을 유지한다.
- 모든 변경 픽셀은 승인된 source ROI union 밖으로 나가면 즉시 실패한다.

완료 조건:
- source DDS verified = 104
- output DDS = 104
- active ROI = 954
- painted + duplicate represented = 954
- fallback hard hold = 0
- deterministic 2회 ZIP SHA 동일

## H3 — A/B 고품질 수렴

H2의 전체 커버리지 패키지는 A/B 이관이 덜 끝나도 만들어질 수 있다. 품질 수렴은 별도 수치로 추적한다.

매 실행 시 QA JSON에 기록:
- `ab_candidate_imported_count`
- `ab_candidate_applied_count`
- `ab_candidate_pending_import`
- `ab_candidate_hold_count`

A/B 파일이 추가되면 동일 ROI의 fallback보다 A/B가 우선되어 새 ZIP이 생성된다.

목표:
- imported = 954
- pending import = 0
- A/B 적용 실패는 C1/C3 또는 재생성 큐로 이동
- 단순 underfill/한글 문장 폭 차이만으로 반려하지 않는다.

## H4 — QA

자동 기계 QA:
- 원본 HD DDS SHA
- 경로 안전성
- DDS decode/encode roundtrip
- 104 DDS 수량
- 954 ROI coverage
- 승인 ROI 밖 픽셀 변경 0
- ZIP CRC
- 2회 deterministic ZIP SHA

C1:
- 한글 오탈자/가짜 자소
- 잘림
- 2줄 원본을 잘못 1줄화
- 반대 기울기
- 타 이미지/아이콘 침범
- 영어 잔상
- HUD/Stage/랭킹/온라인 기록 등 P0 화면

C3/실게임:
- 고위험 HUD/공유 아틀라스
- HD 모드 실제 로딩
- 메뉴/Stage1→Stage2→Goal
- 컨트롤러 variant
- VRAM/FPS 및 RGBA32 mip1 호환성

## H5 — 패키지와 배포

GitHub Action artifact:
`OUTRUN_HD_KOREAN_HYBRID_TEST_ONLY.zip`

ZIP 내부는 게임 상대 경로 `textures/load/...dds`를 유지한다.

중요:
- GitHub Actions는 게임 폴더를 자동 설치하지 않는다.
- Portainer/Docker는 GitHub 작업을 감시/디스패치하거나 N100의 후보 바이트를 전송하는 보조 역할만 한다.
- 사용자 게임 PC에 대한 실제 설치/HD 모드 실기 PASS 전에는 `release_approved=false`, `runtime_validation=UNTESTED`를 유지한다.

## 자동 실행 구조

1. HD source plan 또는 sync workflow 변경
   → 104 원본 SHA 동기화
2. hd_source commit
   → completion workflow 자동 실행
3. N100 A/B candidate 증분 GitHub commit
   → completion workflow 자동 실행
4. 매번 전체 104 DDS / 954 ROI 기준으로 재검증
5. A/B 비율이 계속 증가하면서 fallback 비율 감소
6. 954 PNG 이관 완료 후에도 A/B hold가 있으면 QA/재작업 대상으로 남기되 전체 TEST_ONLY 커버리지는 유지

## 완료 상태 정의

- **SOURCE_COMPLETE**: HD 원본 104/104 SHA PASS
- **COVERAGE_COMPLETE_TEST_ONLY**: 104 DDS + 954 ROI account + fallback hold 0
- **AB_IMPORT_COMPLETE**: A/B 954/954 GitHub 이관
- **AB_QUALITY_CONVERGED**: C1/C3에서 허용되지 않은 A/B hold/시각 결함 해소
- **RUNTIME_APPROVED**: 사용자 실제 HD 모드 게임 검증 PASS

`COVERAGE_COMPLETE_TEST_ONLY`를 `RUNTIME_APPROVED`로 오인하지 않는다.
