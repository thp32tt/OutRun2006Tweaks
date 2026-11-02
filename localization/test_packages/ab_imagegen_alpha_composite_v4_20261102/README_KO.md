# OutRun 2006 기존 ImageGen PNG 실제 DDS 합성 — 8개 아틀라스 시험본 (2026-11-02 KST)

## 확인된 결과
- **정본 원본 PNG SHA와 후보 ImageGen PNG SHA 검증, 8개 DDS 실제 작성 / 원본 한글 문구 9개 ROI 반영**.
- 원본 라벨: Q012 계속?, Q055 다음 라운드, Q089 게임 오버, Q098 코스 기록에 도전하세요., Q104 아웃런 모드, Q112 여자친구와 함께 골에 도착하세요., Q116 하트 어택 모드, Q241 잠시만요 + 로딩.
- 안전 규칙: 원본 영문 알파/색상 텍셀 제거는 **원본의 다른 아트와 분리된 텍스트 전용 row-group**에만 허용. 관련 텍스트 ROI 외 RGB/alpha 차이 0픽셀, 모든 생성 이미지 실제 저장/선택, DDS top-level PNG 재디코드 일치.
- 원본/후보/변환 PNG/DDS SHA256은 ZIP `qa_receipts/`에 각각 기록. Q112는 본래 2줄/새 한글 2줄 구성 확인.
- 독립적으로 다른 경로에 2회 동일 원본/후보로 재실행했을 때 **8개 개별 DDS SHA 및 ZIP SHA까지 모두 일치**.
- ZIP: `OUTRUN_AB_IMAGEGEN_ALPHA_COMPOSITE_8DDS_TEST_ONLY.zip`, 1,708,982 bytes, SHA256 `ddc534b526ebc428efbff38839c015fab59782fb6f5813dac5e8a65c3aa9db01`.
- 그림 참조: `AB8_VISUAL_REVIEW_CONTACT.png`는 알파 합성 후 어두운 배경에 띄운 **미리보기**이며 실제 게임 스크린샷이 아니다.
- 소스: `tools/localization/composite_imagegen_textonly_proof.py` (브랜치 `korean-localization-recovery-20260928`).

## 중요: 현 시점 배포 불필요
- **TEST_ONLY / STATIC_PIXEL_GUARDS_PASS / C1-C3 및 RUNTIME_VALIDATION=UNTESTED**. 기존 104개 v3 시험 DDS를 대체하거나 출시 승인하는 결과가 아니다.
- 현재 DDS는 비압축 RGBA32 mip1. 원본 DXT5/다중 mip와 다를 수 있으며 VRAM/실게임 호환성은 미검증.
- Q116 및 Q241는 생성 PNG의 **원시** alpha가 캔버스 경계에 닿아 별도 시각 재검수가 필요(실제 렌더링 컷 처리에서 visible alpha는 분리). 다른 항목도 독립 C1 QA는 아직 미검증.
- Q032 등 원본이 겹치는/여러 UI를 공유하는 아틀라스는 이 자동 합성 대상으로 묶지 않았다. 추가 원본 CLEAN/부위별 안전 마스크 및 개별 QA가 필요.
- Portainer/게임 설치/VR 설정은 변경하지 않았다. 원본 A/B 후보와 v3 ZIP은 보존.

## 진행 위치 (N100)
- `/home/chatgpt-runner2/work/image-src/text_roi_batches/ab_imagegen_composite_v4_test_only_20261102`
- `summary.json` 및 Q별 `report.json`, `IMAGEGEN_COMPOSED_READABLE_TEST_ONLY.png`, `IMAGEGEN_COMPOSED_TEST_ONLY.dds` 출력 존재.
- 확장 작업 시 기존 `production_manifest.json` 중 954 active ROI와 `candidate_outputs/{A,B}`의 원본 SHA를 다시 검증하고, 실패/아트 침범 소스는 쓰지 않는다.
