# HD 이미지 생성 프롬프트 — A/B 공통, v2 (2026-10-12)

정본: `KOREAN_LOCALIZATION_HD_PNG_IMAGEGEN_AND_FAST_QA_20261012.md`.
기존 B/C1 전용·글자-only 강제·C2 활성 지시는 이 문서에서 폐지한다.
과거 전문은 Git 이력(07ce19d3)에 보존한다. C1은 생성하지 않는다.

## 입력과 출력 선택

- 기본: 실제 HD 원본 한 atlas의 READABLE PNG → 편집 이미지 1장.
- 한 atlas 안에 서로 다른 sprite 방향이 있으면 해당 sprite별 정방향 ROI 입력.
  전체 flip-Y 한 번을 모든 문구의 정방향이라고 간주하지 않는다.
- 오자/작은 글자/배경 변화 등 실패는 실패 문구만 ROI → 투명 한글 글자·효과층.
- 원본이 투명하면 투명 유지. 전체 출력은 원본 비번역 픽셀을 대체하지 않는다.
- 생성기에 번역을 추측시키지 않는다. 승인 manifest의 정확한 문구만 사용한다.

## 고정 전문과 조립

`tools/localization/imagegen_prompts/atlas.txt`, `roi.txt`가 시각 프롬프트 정본이다.
역할 작업 명령, Git SHA, 점수, QA 판정은 생성 전문에 넣지 않는다.

`python tools/localization/build_imagegen_prompt.py INPUT.json --output OUTPUT_DIR`

INPUT.json의 필수 키:
- `mode`: `atlas` 또는 `roi` (ROI는 문구 1개).
- `source_dds_sha256`: 실제 정본 원본의 SHA-256.
- `reference_png`: manifest 기준 상대 경로 또는 로컬 절대 경로.
- `reference_png_sha256`: 실제 첨부할 PNG의 SHA-256.
- `readable_transform`: identity / flip_x / flip_y / rotate_180 / rotate_90 / rotate_270.
- `translations`: `[{"source":"OUT RUN MODE","korean":"아웃런 모드"}]` 형태.

조립기는 PNG 파일/헤더/SHA, 필수 문구, 미치환 자리표시자를 검사하고
`prompt.txt`와 `request.json`을 만든다. 이 단계는 DDS 원본/UV 검증·실제 업로드·
이미지 생성·DDS 변환을 실행하지 않는다. `PROMPT_PREPARED_NOT_GENERATED`를
생성 완료로 바꾸지 않는다. 도구 인자의 참조 경로/실제 첨부, 최종 prompt 원문,
출력 바이트와 SHA를 호출 후 별도 기존 imagegen_requests 기록에 연결한다.
생성 ID가 노출되지 않으면 null을 유지한다.

## 실제 이미지 입력의 증명

브라우저 컨트롤러는 PNG 바이트 업로드 → 썸네일 → 전송 메시지 첨부 확인 후 호출한다.
직접 편집 도구는 해당 도구가 지원하는 실제 로컬 파일/첨부 참조 입력을 사용한다.
GitHub URL, 텍스트 경로, 다른 도구 프리뷰는 실제 참조 입력을 대신하지 않는다.
조립기의 파일 검증은 첨부 확인이 아니다. 미확인이면 SOURCE_REFERENCE_NOT_BOUND.
내장 이미지 생성 불가/한도/다운로드 실패 시 HOLD하며 유료 API로 자동 전환하지 않는다.

## 출력 확인과 재시도

1. 원본 생성 PNG를 그대로 보관하고 SHA를 계산한다.
2. 승인 문구의 음절·받침·공백·숫자·줄바꿈 확인. 전체 atlas는 모든 번역 항목 점검.
3. ROI는 실제 알파를 확인. 체커보드가 그려진 RGB/RGBA 파일은 투명층이 아니다.
4. 검증된 CLEAN 위에 텍스트·효과만 추출/합성. 불확실한 배경 분리는 HOLD/ROI 재생성.
5. 원본 칸/UV와 보호 mask 내부에 종횡비 유지 축소·정렬. 역변환·DDS 저장 후 디코딩 QA.
6. 같은 원인으로 2회 실패하면 입력/방법을 변경하거나 HOLD 후 다른 자산을 진행한다.
   미세한 색·광택 차이만으로 무한 재생성을 하지 않는다.

원본 계열의 기울기 방향은 유지한다. 경미한 각도·색·광택·여백은 허용하지만,
반대 기울기·잘못된 방향·오자·잘림·실제 UI 칸 초과·겹침·보호 아트 훼손은 재작업한다.
C1_STATIC_PASS, C3, 사용자 실게임, 정식 배포는 별도 상태다.
