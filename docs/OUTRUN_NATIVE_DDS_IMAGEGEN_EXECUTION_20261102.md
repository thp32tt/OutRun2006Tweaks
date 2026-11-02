# OutRun 2006 — Q089/Q104 원본 포맷 보존 DDS 실행 기록 (2026-11-02 KST)

## 실행 결과
- 이전 계획: [OUTRUN_EXISTING_KOREAN_ASSET_INTEGRATION_PLAN_20261102.md](OUTRUN_EXISTING_KOREAN_ASSET_INTEGRATION_PLAN_20261102.md).
- A/B 후보 PNG를 재사용한 4x HD 합성 v4 8DDS 중 **Q089 Game Over→게임 오버, Q104 OutRun Mode→아웃런 모드** 2개를 원본 네이티브 DDS 형식으로 다시 작성했다.
- 고정 소스 + 원본 DDS 전수 해시 검증, HD 대조, 문자 bbox 이외 변경 금지, 원본 128바이트 DDS 헤더·BGRA 채널 마스크·512×64 해상도·1 mip 유지, FLIP-Y 반영, 디코딩 왕복, ZIP CRC 검증 및 독립 디렉터리의 재생성 SHA 일치를 통과했다.
- 결과는 **TEST_ONLY_NOT_RUNTIME_APPROVED**. C1 독립 QA, C3, 실게임 로드 및 사용자 승인은 **미완료**. 어떠한 출시 승인도 아니다.
- 생성 도구: `tools/localization/build_ab_q089_q104_native_test_20261102.py` (임의로 원본/게임 폴더 쓰기 금지, 기존 출력 경로 덮어쓰기 금지).
- GitHub 패키지: `localization/test_packages/OUTRUN_AB_Q089_Q104_NATIVE_2DDS_TEST_ONLY.zip`.
- 실행 산출물 ZIP SHA256: `79fd62e8205632371b31d002643d2565a0eee753412a46aa5e4ff7f5e6aa08fc`, **56,742 bytes**. GitHub 원격 재다운로드 SHA 및 재실행 SHA 일치 확인.
- 패키지 커밋: `7a2a693a7420b81e9dcbea46cf2fe7ccee23ee86`.
- N100 실행 출력: `work/image-src/text_roi_batches/ab_imagegen_native_q089_q104_test_only_20261102/`; 재현 폴더 별도 유지.

| 대상 | 네이티브 DDS SHA256 | 상태 |
|---|---|---|
| Q089 `textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds` | `2ac06eeaa6e77b9ab5525fed0a712b43707bcec347ed856e7930f2fbc0494395` | 정적 PASS / 시각·실게임 미검수 |
| Q104 `textures/load/spr_sprani_selector_cvt_Exst/62BEBF33_512x64.dds` | `7069d1c31feb9b83b59dfb75ee0fb80cd815d216ed0a07a4ffef4dd09f562a95` | 정적 PASS / 시각·실게임 미검수 |

## 다른 v4 대상은 자동 승인/변환 금지
- **Q055:** FLIP-Y 후 원본 DDS와 4x HD 픽셀 알파 mask IoU 약 `0.6257`에 불과해 단순 4배 역축소/전면 합성은 원문 위치/보호 픽셀 손상 위험이 있다. `HOLD_SOURCE_ALIGNMENT` 유지.
- **Q241:** 유사 알파 IoU 약 `0.7798`, 2개 ROI 구성 및 후보 테두리 접촉 1건. `HOLD_SOURCE_ALIGNMENT_AND_BORDER`.
- **Q089 / Q104:** FLIP-Y 기준 알파 IoU 각각 약 `0.9272` / `0.9175`, 평균 알파 절대 오차 약 `9.087` / `2.225`. 두 샘플의 정적 작업 허가 근거일 뿐 시각 QA PASS 아님.
- 기타 v4 대상 Q012/Q098/Q112/Q116에 대해서는 아직 본 기록의 네이티브 형식 재검증을 수행하지 않음. Q012은 별도 원본 포맷 보존 시험본이 이미 있으므로 **중복 제작/중복 점수화 금지**.

## 다음 순서
1. Q089/Q104 시험본의 게임 장면별 글자/색/기울기, 패딩, 보호영역을 기존 원본/HD 대비 독립 확인. 실제 게임 설치는 사용자가 명시적으로 수행.
2. Q055/Q241은 원본 DDS↔HD ROI 매핑과 텍스트 세로 위치를 추가 보정하기 전 HOLD 유지.
3. 다른 v4 대상에 대해 원본 format·orientation/HD alignment/모든 ROI 검증을 동일한 fail-closed 절차로 검사해 안전한 것만 별도 ZIP 시험본으로 생성.
4. 954 활성 ROI와 955 PNG의 대응표는 기존 `ab_dds_integration_prep_20261102`를 정본으로 재사용. 품질/기능 승인 및 사용자 실게임 게이트는 그대로 유지.
5. **현재 Portainer 재배포 불필요**. 게임 폴더 자동 덮어쓰기 금지.
