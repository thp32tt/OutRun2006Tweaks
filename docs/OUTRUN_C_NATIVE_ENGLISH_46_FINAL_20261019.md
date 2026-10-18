# OutRun 2006 — GitOps C 슬롯: HD 원본 영문 크롭 46건 분리 보고

**일자:** 2026-10-19 KST  
**배포 소스:** `thp32tt/OutRun2006Tweaks` / `localization-controller-recovery-20260928`  
**C 서비스:** `outrun-c-english-native-crop`  
**상태:** `TEST_ONLY`, 실게임 검증 미진행. 기존 C Docker 인스턴스나 A/B 작업을 추가·변경하지 않음.

## 1. 현재 전체 실적

| 구분 | 결과 | 검증 |
| --- | ---: | --- |
| 기존 원본 HD PNG | 108개 | 기존 108/108 SHA·매니페스트 검증 유지 |
| 기존 크롭 | 242개 | 원본 RGBA 일치·크롭 SHA 242/242 기존 검증 유지 |
| 원본 HD 네이티브 픽셀 재크롭 | 45개 | 새로운 마지막 Q201 포함, 픽셀 직접 대조 |
| PSD 독립 레이어 추출 | 1개 | 상위 Git blob SHA 검증 + 레이어 분리, **게임 원본 PNG의 픽셀과 완전 동일하지 않음** |
| 별도 검토용 후보 총수 | **46개** | 각 PNG SHA/manifest + ZIP CRC PASS |
| 기존 MASTER | 255건 | 파일 수정 없음 |
| DDS / 한글 생성 / A/B | 0건 실행 | 모두 기존 상태 유지 |

## 2. 마지막 2건 수정

### Q201 — CONIFEROUS FOREST

- 원본: `Q201_A9ABD877_BASE_READABLE_FLIPY.png` (2048×2048, SHA-256 `6e05218ad9e60e727343c3197afee430323e0c41f9f58fdd199df69c30c8f56a`).
- 이전 크롭: `[89,1924,1186,2036]`. 우측 **STAGES** 문구의 일부가 포함됨.
- 새 원본 크롭: `[89,1924,1167,2036]`. 마지막 T는 x=1156까지 앤티앨리어싱이 있고, x=1157~1172는 전체 ROI 높이에서 **실제 알파값 0**. 뒤따르는 글자는 x≥1173에서 시작하므로 글자와 이웃 텍스트 사이 빈 간격을 정확히 잘라냄.
- 원본 RGBA 바이트 비교 PASS, 알파 생성/마스킹 없음, 원본 픽셀 수정 없음.
- 파일: N100 `qa_review_20261018/reworked_final2_test_only_20261019/059_Q201_CONIFEROUS_FOREST/english_native_c_crop_candidate.png`.
- **게임 수용 상태:** 미검증, `TEST_ONLY`.

### Q062 — HARD

- 원본: `Q062_33491F83_BASE_READABLE_FLIPY.png` (2048×1024, SHA-256 `45545843d55e1e33a059b1832e6c75206056468b86a29478838391636eae8772`).
- PSD 출처: 상위 `Sonic-TV/OR2006Sprites`, commit `3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6`.
- PSD 경로: `PSDs, XCFs, SVGs, and other Working Source Assets/OutRun2SP Mode UI/spr_sprani_loading_cvt_Exst/33491F83_512x256.psd`.
- 원본 PSD Git blob SHA-1: `e22ed4d6b9f7d8464fc40d724dd0b1d37e306104`. 8,669,875바이트. N100에서 직접 검증.
- `psd-tools==1.25.0` QA 전용 의존성으로 PSD의 그룹 `Right-Hard` 내부 `HARD [Rasterized]` 픽셀 레이어를 확인. Photoshop 원본 캔버스 `[808,287,1068,373]` / 크기 260×86. 회색·녹색 인접 플레이트가 아닌 **HARD 글자/외곽 효과 레이어만** 추출했으며 외곽 잘림 방지용 투명 패딩 8px 추가.
- **중요:** 레이어와 평탄화된 기존 게임 원본 PNG는 완전히 동일하지 않음. 레이어 불투명 픽셀 중 20,675/21,302가 RGBA 완전 일치, 627픽셀 차이가 남음. 따라서 **원본 HD 픽셀 그대로 잘랐다는 주장 금지**, PSD 레이어 기반 후보로 별도 분류.
- 파일: N100 `qa_review_20261018/reworked_final2_test_only_20261019/036_Q062_HARD_PSD_RASTER_LAYER/english_psd_layer_test_candidate.png`.
- **게임 수용 상태:** 원본 효과·색상 일치 여부 육안 검수 및 실게임 검증 전에는 사용 금지.

## 3. 전달물

- N100 ZIP: `qa_review_20261018/OUTRUN_C_NATIVE_ENGLISH_46_TEST_ONLY_20261019.zip`
- 패키지 SHA-256: `77301b467d51a6c24d5ca9d138829e65b000d0537ee05c62afbc6e4ae16cb1e8`, 크기 5,981,364바이트.
- ZIP 수록: 46개 재크롭 후보, 개별 검증 JSON, 76건 육안검수 CSV, 6장 원본 비교 시트 및 최신 2개 비교 JPG.
- 마지막 두 건 비교: `qa_review_20261018/FINAL2_SOURCE_VS_EXTRACTED_20261019.jpg`.
- 전체 출처 표: `qa_review_20261018/C_NATIVE_ENGLISH_46_PROVENANCE_INDEX.csv`.

## 4. 후속 품질 게이트

**현재 영문 추출 후보 46개 제작 완료**지만 이것은 번역·합성에 바로 사용할 최종 승인본이 아님. 기존 원본 크롭 242개(166 초기 + 76 경고), 기존 46개 수정 후보 모두 실게임 검증 전. 특히 PSD 기반 HARD는 원본 PNG와 픽셀 차이가 있어 원본과 효과 비교 검수가 필수.

기존 A/B 자동 실행, C1/C3, 원본 108개, MASTER 255건, DDS와 한글 합성 상태는 변경하지 않음. GitHub에는 **QA 스크립트와 증거 JSON/문서만 추가**하며 별도 Docker 생성·배포·A/B 재가동하지 않음.