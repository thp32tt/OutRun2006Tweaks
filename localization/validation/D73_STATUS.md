# OutRun 2006 한글화 D73 최종 QA 상태

- 실행 시각: 2026-09-27 09:20 KST
- 역할: D / 최종 QA + 승인본 판정
- 대상: A71 `FF2462BB_A71_v2.dds`, C72 `FF2462BB_C72_QA_BASE.dds`, HD canonical 원본 `FF2462BB_1024x512.dds`.
- A71과 C72 DDS는 SHA-256까지 완전 동일.
- canonical 원본과 직접 바이트/픽셀 대조 완료: 4096×2048, RGBA32 DDS, 128-byte 헤더 동일.
- 원본 대비 변경 215,324 px이며 선언된 10개 localization bbox 밖 변경은 0 px.
- bbox 밖 alpha 변경 0 px, 10개 bbox 경계의 불투명 픽셀 0, 편집 bbox 내부 완전투명 픽셀의 RGB 잔존 0.
- 완료된 10개 셀의 의미/문맥, 가독성, 잘림, 원본 영역 이탈, 고해상도 보존은 PASS.
- 최신 B71 폴더는 파일 0개이므로 B71 자체는 독립 QA 근거로 사용하지 않음.
- 전체 atlas 기준 한글 누락 FAIL: `Slipstream the cars!`, `Avoid the knockout!`, `Beat that car!`, Stage/route/account/menu 계열 등 미완료.
- 따라서 `FF2462BB` 파일 자체는 **REWORK_REQUIRED**이며 approved 최종 작업영역으로 승격하지 않음.
- 승인 파일 수: 0.
- QA 통과 셀 수: 10.
- Git 동기화 기록만 수행. 빌드/VR/FFB 작업은 수행하지 않음.
