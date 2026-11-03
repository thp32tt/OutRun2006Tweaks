# OutRun 2006 — A/B ImageGen 원본 우선 GitHub 한글 DDS (2026-11-03 KST)

## 최상위 소스 우선순위 (사용자 재확인)

1. **A/B가 이미 제작한 실제 고품질 ImageGen PNG**: 해시 검증해 원문 텍스트 영역만 교체한다. 외곽선/그림자/기울기/한글 고유 스타일 유지.
2. 원본 DDS/원본 HD/ROI 좌표: 별도 SHA 확인. 원문·보호 아트에 손상 우려가 있으면 HOLD.
3. 독립 시각 QA C1/C3, 두 줄 레이아웃, HUD 보호아트, 게임 런타임 테스트: 별도 게이트.

일반 폰트로 새 한글을 그리는 구형 자동 생산은 1순위가 아니며, GitHub 정기·Push 워크플로에서 **퇴역/비활성화**됐다. 기존 폰트 산출물이 있다면 TEST_ONLY 이력일 뿐 최종 패키지에 반영하지 않는다. A/B PNG가 없으면 일반 폰트로 대신 만들지 말고 `A_B_CANDIDATE_NOT_IMPORTED`로 보류한다.

## GitHub에서 실증된 A/B 우선 시험

- GitHub Actions [41562747061](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/41562747061) **SUCCESS**.
- GitHub 기본 Python 실행기 사용; N100은 단 1회 생성된 후보 이미지 파일을 읽어 GitHub Git blob으로 복사하는 데만 사용. DDS 변환과 검사는 GitHub에서 수행.
- 원본 B 후보 `Q012_0909e9d5397ec72e_source_k.png` 488,487바이트, SHA256 `f88974af1876c6cf4ef21339dcd7c61ec1203165890773033b66c131e82ca75b`를 저장소 안으로 **바이트 변경 없이 이관**. 원본 HD SHA `bfabe98fb448814401f1c4c5bb6ae0cbb2c8ef81bbf9ec4b6457fdcc795ab2e8`.
- 네이티브 원본 Q012 `textures/load/spr_etc_xst/D6DC1380_256x64.dds` SHA256 `42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352`; 원본 글자 잉크 영역 [8,10,248,44] 확인. A/B PNG의 외곽선·그림자 색상을 그대로 이용.
- 테스트 6/6 PASS, DDS 원본 헤더/형식/FLIP-Y 소유권 보존, 보호아트 경계 밖 픽셀 변경 0, 2회 결정적 ZIP SHA 동일.
- 출력 `OUTRUN_AB_IMAGEGEN_NATIVE_TEST_ONLY.zip` SHA256 `d8db7fee432f03a01f8cb5d5221c484e4e0acf35d941b36543c120390abbc005`, QA JSON·미리보기 PNG, artifact `outrun-ab-original-imagegen-41562747061`, artifact ID 13197641544.
- TEST_ONLY / `release_approved=false` / `runtime_validation=UNTESTED` / C1·C3 시각 검수 필요.

## 코드·작업 흐름

- GitHub 실행: `.github/workflows/outrun-ab-imagegen-native.yml` (master와 한글 자산 브랜치).
- 엔진: `tools/localization/github_ab_imagegen_native_production.py`.
- 테스트: `tools/localization/test_github_ab_imagegen_native_production.py`.
- 바이너리 이관·SHA/원본 잉크 경계: `localization/automation_inputs/ab_imagegen_registry.json`.
- 고품질 A/B 원본 파일: `localization/automation_inputs/candidate_outputs/A/` 또는 `B/`.
- 기계적 검증을 통과한 고품질 ImageGen 소스만 TEST_ONLY ZIP으로 포장하고 GitHub Actions artifact로 저장. 자동 설치 없음.
- 기존 Portainer 경량 컨트롤러: `localization-controller-recovery-20260928`의 `github_actions_light_controller.py`는 이제 이 A/B 워크플로를 모니터·디스패치한다. 이미지/원본 DDS 처리는 N100에서 수행하지 않음.

## 남은 자산 이관 및 품질 게이트

- 전체 활성 번역 ROI 954, 기존 A/B 고품질 PNG 955개 (활성 954개와 정확히 매칭되는 954개, 레거시 1개 제외).
- GitHub에 **실제 이관 및 SHA 검증 완료된 현재 파일은 Q012 1개**. 나머지 953개는 N100에 있으므로 GitHub에서 임의 생성/대체하지 않는다.
- 게임 원본 108개 전부가 GitHub 체크아웃에서 확보된 것은 아니다. 여러 ROI가 공유 DDS 아틀라스를 구성하면 *각 ROI를 별도 독립 DDS로 덮어쓰지 않고* 리뷰된 소스/마스크를 함께 검증해 한 번에 합성한다.
- 민감하거나 소유권 불명확한 원본 게임 자산을 무조건 공개 업로드하지 않는다. 후보 PNG·메타의 일회성 GitHub 이관과 원본 DDS SHA 검증을 완료한 범위부터 점진적으로 처리한다.
- UI 2줄 텍스트/타 이미지 침범/알파/외곽선/FLIP-Y/RAW 확인 후 실제 게임 PASS 전에는 RELEASE 불가.

## 기존 경로의 중지
- `.github/workflows/outrun-korean-new-dds-production.yml`의 일반 폰트 기반 정기 실행·Push 트리거 제거. 이전 실행 결과 41561475752는 **우선 채택 금지** (TEST_ONLY 이력).
- A/B 원본을 다시 자체 폰트로 덮어쓰거나 A/B보다 앞에 두지 말 것.
