# OutRun 2006 HD 한국어 UI — 신규 제작 (2026-10-13)

이 브랜치는 이전 한글화 제작 결과·큐·QA 상태를 일절 승계하지 않는 **새 시작점**입니다.

## 보존한 것
- `source/original_hd_dds/`: 과거 사용자 제공 OR2-HD-GUI-v0.25.10a 패키지에서 실물 원본으로 별도 검증된 18개 영어 DDS 및 SOURCE_INFO.json.
- `source/english_png_reference/OUTRUN_HD_PNG_MANUAL_20261012.zip`: 원본 영어 HD 텍스처를 정방향 PNG로 준비한 참조 ZIP. 새 한국어 이미지가 아님.
- `translations/OUTRUN_HD_FULL_TRANSLATION_MAPPING_20261013.csv`: 영어 원문·한국어 대응 문구·원문 보호 목록.
- `translations/ko_draft.json`: 게임 문자열 번역 초안. 이미지 번역 매핑과 별개.

## 폐기·미승계
기존 생성 한글 PNG/DDS, 플레이트, A/B/C 제작 산출물, asset_queue.csv, resume_state.json, QA PASS/FAIL/REWORK, 자동화 정책/상태, 비교 이미지 및 오래된 작업 로그. **이 브랜치에는 새 한국어 생성 이미지 0개, 새 QA 통과 0개입니다.** 옛 브랜치는 복구용 기록으로만 보존합니다.

## 원본 범위
원본 패키지 기록에는 전체 289개 DDS가 언급되지만, 이 브랜치로 동일 Git blob SHA로 이관·확인한 원본 DDS는 현재 18개뿐입니다. 영문 PNG 참고 ZIP은 89개 번역 대상 제작용 참조 묶음이며, 각 PNG는 사용 전에 해당 원본 DDS와 대응을 검증해야 합니다. **과거 `hd_candidates`는 수정 산출물 가능성이 있어 원본으로 가져오지 않았습니다.** 나머지 원본이 필요하면 제공된 OR2-HD-GUI 전체 ZIP(패키지 SHA256: `76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958`)을 재검증하여 추가하세요.

## 신규 진행
원본 영어 DDS/정방향 PNG 확인 → 문구 매핑 확인 → 이미지 생성으로 처음부터 제작 → 픽셀/알파/해상도/방향/글자 검수 → 새 DDS 저장 → 독립 QA → 실게임 검증. 이전 통과/반려 이력은 재사용하지 않습니다.

[신규 이미지 제작 지침](docs/NEW_IMAGEGEN_QA.md) · [초기 상태](STATUS.md)
