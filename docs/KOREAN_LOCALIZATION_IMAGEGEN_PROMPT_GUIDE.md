
## 2026-10-12 ImageGen English-letter-only input binding — user correction (HARD STOP)

B/C1 shall **not generate from a game screenshot, full menu, atlas, QA contact sheet, project description, or prompt text alone**. Prepare ONE asset-/row-specific, visibly isolated **real transparent English glyph/effect RGBA PNG** first:

1. Query the actual mirrored PSD in `localization/graphics/plate_library/upstream_psd/` and `source_psd_upstream/`; verify its Git blob SHA against `PSD_IMPORT_CATALOG.json`. If Photoshop letter/effect layers can be identified, isolate exactly those. A PSD transparent *merged composite* may instead be cropped row-by-row **only if it visibly contains just target lettering, no scenery/menu/background or other UI**; label this `PSD_TRANSPARENT_COMPOSITE_REFERENCE`, **not** `PSD_LAYER_SEPARATED` or `C2_PLATE_PASS`. Independently compare to canonical DDS before using it as pixel-accurate source/CLEAN.
2. If PSD layers or merged image are unsuitable, extract the English lettering/effect alpha only from **SHA-pinned canonical game DDS** at the exact READABLE source ROI. Record original DDS SHA-256, source format, transform, native bbox, PNG SHA-256 and transparent alpha result. Do not use a previous Korean candidate or an opaque screenshot as an English source.
3. Stage the **actual PNG bytes as a visible/attached image input supported by the chosen generation tool**. A GitHub URL, filename, message saying "see source", or an image printed in an unrelated tool result does **not** establish media attachment to ImageGen. Verify how the tool actually receives that image; record binding mechanism and evidence. If the image cannot be supplied to the generator, **do not call**: record `SOURCE_REFERENCE_NOT_BOUND` and keep work HOLD. `edit_op=null` / missing input metadata is not, by itself, proof of successful source binding.
4. Tell the generator to create **only ONE Korean transparent lettering PNG** of the exact approved Korean phrase, retaining the *attached* English glyph's stroke, slant, fill, outline and glow. Forbid new game screens, UI bars, vehicles, logos, extra words and scenery. Do not send huge task contracts, filenames, QA labels or screenshot descriptions as the model's image prompt. Treat `transparent_background=true` as an instruction, not evidence; inspect actual alpha and visual output.
5. **Pre-DDS structural reject:** output has any full-screen menu/background/vehicle/extra captions, wrong text, missing alpha or unbound source -> `NON_GLYPH_SCENE_OUTPUT` / `SOURCE_REFERENCE_NOT_BOUND`; keep raw rejected output ID/SHA and zero qualified glyph PNG/DDS. Do not retry twice with the same unbound input. Refine reference attachment/preflight rather than blindly describing a different screen.
6. Only after a qualified glyph-only PNG and the existing separately approved CLEAN/plate, allow `imagegen_b_pipeline.py` conversion and persisted DDS mechanical/self visual QA. C2/C3/user-game approvals remain independent and `RUNTIME_VALIDATION=UNTESTED` until tested.

**2026-10-12 q092 concrete reference:** exact copied `plate_library/upstream_psd/1A43E9D9/1A43E9D9_512x64.psd` (938,768 bytes; Git blob `0589de5e9a3ac2e2d032ca1943f7502c07890312`; PSD SHA-256 `ee000ce057b58891a62ecfe419ac50fd798a6d660bf5a2bb47a6870f798b8923`), native 2048x256 PSD transparent composite. Isolated English lines are saved under `localization/graphics/role_B/source_references/q092_20261012/`; this does not imply Photoshop leaf-layer separation, canonical DDS pixel equivalence, C2 plate certification, ImageGen source binding, a new Korean DDS or user game approval. Previous q092 generations `7778beba` and `cb10612b` produced unrelated complete game scenes; neither is a qualified letter layer.

# 이미지 생성 글자 프롬프트 작성 지침 — B·C1 공통

## 2026-10-11 전 레인 글자별 크기 검수 규칙 (최신 사용자 지시)

**적용 대상:** A/B/C1 제작·자체 QA, C2 독립 최종 QA, C3 엄격 QA, CLEAN 이후 렌더·저장 DDS 시각검수, PRE_INGAME 및 재작업 판정 전부. 원문과 번역의 언어/글자 수가 다르다는 이유로 한글 문장 전체 가로세로 비율·폭 점유율·영문 픽셀 면적/실루엣 일치율이 다르게 나온다는 것은 **반려 사유가 아니다**. 이 지시가 과거의 "undersized/underfill/원문 길이·폭에 비례/가능한 크게" 문구보다 우선한다. 자세한 단일 정본은 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`.

**판정:** 원문 개별 텍스트/줄의 정확한 글자+효과 bbox를 넘는 한글 픽셀은 1px도 허용하지 않는다. 그 안에서는 한글이 원문보다 더 좁거나 작아도 허용하고, 원문 총 문장 길이나 글자 개수/캔버스 비율을 맞추기 위해 확대하거나 가로 늘이지 않는다. 비교 대상은 실제 한글 **글자 하나하나**의 네이티브 높이/획 굵기/받침·내부 공간/윤곽·효과·가독성과 UI 계열의 대표 원문 글자 크기·위계이다. 영문과 한글 글자 수가 달라 1:1 대응시킬 수 없으므로 'n번째 영문 글자 = n번째 한글 글자' 강제 매칭도 금지한다. 번역이 더 짧은 **그 사실 자체는 PASS** 처리한다.

**반려 가능 조건:** 원문 bbox 초과, 겹침·보호 아트 변경·잘림, 한글 오탈자/획 손상/실제 읽히지 않음, 명백한 서체·기울기·효과 오류는 각각 구체적 원인과 실제 픽셀 증거가 있을 때만 FAIL. 기존 `UNDERFILL`/`SOURCE_WIDTH_RATIO`/`WIDTH_RATIO`/`WHOLE_SENTENCE_ASPECT`만 근거인 REWORK는 현행 글자별 시각검수에서 **크기 조건 PASS로 재분류**하고 나머지 QA 통과를 확인한 뒤 정상 C2/C3 경로로 진행한다. 미검수 자료를 근거 없이 전체 승인으로 바꾸거나 사용자 실게임 OPEN을 닫지 않는다. `RUNTIME_VALIDATION=UNTESTED` 유지.


버전: 1.0 / 2026-10-11
TASK_ID: OUTRUN-KOR-IMAGEGEN-PROMPT-GUIDE-20261011-1741

## 목적과 적용 범위

B·C1은 모든 신규/수정 ImageGen 호출 전에 이 지침으로 자산별 프롬프트를 작성한다.
A 제작 방식, 기존 자산 소유권, B/C1 분담, C2 독립 검수, C3 및 사용자 실게임 판정은 유지한다.
이 문서는 프롬프트 작성 규칙이다. 프롬프트 준수나 생성 성공 자체는 DDS/독립 QA 통과가 아니다.
생산 순서와 CLEAN/PLATE_PASS 선행 조건은 기존 계약 및 B_IMAGEGEN_LANE을 따른다.

## 1. 원본을 보고 제작 명세를 만든다

최신 큐와 정확한 원본 DDS SHA를 확인한 뒤 읽기 방향으로 정규화하여 관찰한다.
원문이 불명확하면 먼저 확인한다. 이미지 생성기에게 번역이나 정본 문구 결정을 맡기지 않는다.

| 명세 | 기록할 내용 |
|---|---|
| 문구 | 승인된 한글 그대로, 공백·숫자·문장부호·줄바꿈, 보존할 영문 |
| 영역 | source/placement bbox와 좌표계, 효과 포함 허용 크기 |
| 글자 형태 | 굵기, 곡선/각진 획, 폭/높이, 받침·내부 공간 |
| 방향 | 읽기 방향 기준 기울임, 필요 시 원근; 원본 관찰 근거 |
| 색·효과 | 실제 채움색/그라데이션, 테두리, 그림자 방향·깊이, 광륜 범위 |
| 배치 | 기준선, 정렬, 줄 사이 위계, 원문 대비 시각적 크기 |
| 보호 | 수정하면 안 되는 장식·로고·다른 글자; 생성 대상에서 분리 |
| 불확실성 | 확인하지 못한 값. 임의 각도·색상·비율로 채우지 않음 |

q060의 금색/남색이나 약 6.34:1은 해당 자산의 관찰값이다. 다른 자산에 복사하지 않는다.
작은 안내문, 평면 메뉴, 이탤릭 제목, 금속 제목을 별도 계열로 다룬다.
노래 제목·브랜드 등 원문 보존 규칙을 먼저 적용한다.

## 2. 생성 참조는 원본 글자만 준비한다

- 정확한 영문 원본에서 대상 문구와 필요한 효과가 잘리지 않도록 crop한다.
- 참조는 READABLE 방향이다. RAW/FLIP-Y 저장 변환은 후처리 책임이며 생성기에 뒤집힌 글자를 주문하지 않는다.
- QA 비교표, SOURCE/CLEAN/FINAL 패널, 파일명·SHA·판정 라벨이 붙은 이미지, 여러 자산 콜라주를 생성 참조로 넣지 않는다.
- 원본 crop에 장식이 포함되어야 할 때는 스타일 참조일 뿐 출력 대상은 글자층이라고 명시한다.
- 편집 호출은 수정할 후보와 원본 스타일 참조를 명확히 구분한다. 실패 후보는 정본 스타일로 취급하지 않는다.
- 사용한 crop의 원본 SHA, crop 좌표, 방향 변환, crop SHA를 기록한다.
- 파일 참조가 가능하면 정확한 파일 경로를 지정한다. 최근 대화 이미지 참조만 가능하면 필요한 최소 이미지만 선택하고 다른 QA 이미지가 섞이지 않았는지 확인한다.

## 3. 운영 지시와 생성 프롬프트를 분리한다

에이전트 작업 명령에는 TASK_ID, 큐, CLEAN, 검수, DDS, 커밋 정보를 유지한다.
이미지 생성 도구에는 아래 다섯 항목으로 구성한 짧고 완결된 시각 제작 지시만 전달한다.

1. 산출물: 투명한 단일 글자층 이미지.
2. 정본 문구: 한 번 명확하게 제시; 공백·문장부호·줄 구분 설명.
3. 원본 관찰에 근거한 형태·색·효과.
4. 원문 bbox를 넘지 않는 여백·정렬과 글자 하나하나의 높이/굵기/내부 공간. 문장 전체 가로세로 비율을 강제로 맞추지 않는다.
5. 허용 출력 범위: 대상 문구 한 번, 추가 레이블·배경 없음.

GitHub, DDS, QA PASS, 해시, 점수, 비교표 제작 지시를 생성 프롬프트에 복사하지 않는다.
가짜 획이나 배경이 생긴 원인을 문구 길이/참조 혼입이라고 확정하지 않는다. 입력을 통제하여 비교한다.
금지어만 길게 나열하지 말고 원하는 결과를 먼저 설명한다.
프롬프트의 언어는 작업자가 명료하게 작성할 수 있는 언어를 사용하며, 목표 한글은 번역하지 않는다.

## 4. 범용 생성 템플릿

아래 대괄호는 실제 값으로 치환한다. 미확인 속성은 삭제하거나 조사하고, 자리표시자 채로 호출하지 않는다.

> 첨부한 영문 원본 글자 이미지를 형태와 효과의 참조로 사용하여 게임 UI용 글자층 하나를 만든다.
>
> 정확한 출력 문구:
> [승인된 문구]
>
> [한 줄 / 명시한 줄 구성]. [공백·숫자·문장부호의 정확한 배치와 필요한 형태].
> 원본의 [획 굵기·곡선·기울임]과 [채움·테두리·그림자·광륜]을 따른다.
> 한글의 받침과 내부 공간을 명확하게 유지한다.
>
> 한글 각 글자의 네이티브 높이·획·내부 공간을 살리고 원본 효과 포함 bbox 이내에 배치한다. 문구가 영어보다 짧아도 그대로 둔다. 전체 문장 가로세로 비율을 맞추기 위해 늘리지 않는다.
> 모든 효과가 잘리지 않도록 투명 여백을 둔다.
> 대상 문구가 한 번만 있는 투명 글자 이미지 하나를 출력한다. 추가 문구와 배경은 넣지 않는다.

수치는 생성 목표이며 픽셀 보증이 아니다. bbox/0픽셀 보호는 저장 결과로 검사한다.
캔버스 비율과 알파 글자층의 실제 bbox 비율을 혼동하지 않는다.
한글 글자 수가 적다고 가로로 강제 늘리지 않는다. 원문 영역 상한 안에서 가독성과 위계를 함께 검토한다.
원본과 같은 전체 폭이 언제나 정답은 아니다. 자산별 시각 검토로 목표를 결정한다.

## 5. 여러 문구와 작은 글자

기본은 한 호출에 한 레이블이다. 작은 부제/설명은 별도 생성하여 정본 좌표에 합성한다.
여러 줄이 하나의 연결된 디자인일 때만 함께 생성하고 각 줄 문구·순서·위계를 명시한다.
슬래시로 줄바꿈을 대신 적지 않는다. 실제 슬래시가 필요한 경우에만 목표 문구에 넣는다.
q102처럼 제목과 부제가 분리된 경우 각각 원본 crop으로 생성하고, 두 출력의 SHA·배치·결합 결과를 기록한다.
기존 consumer가 여러 글자층을 직접 지원한다고 가정하지 않는다. 지원 경로를 확인하고 검증된 알파 합성으로 입력을 준비한다.
작은 글자에는 원본에 없는 두꺼운 입체 효과를 추가하지 않는다. 네이티브/75/50%에서 내부 공간을 확인한다.

## 6. 도구 호출과 원본 출력 보존

- 투명이 필요한 호출은 지원되는 실제 도구 인자 transparent_background=true를 설정한다.
- 참조 방식은 해당 도구 스키마를 따른다. 서로 배타적인 참조 인자를 함께 지정하지 않는다.
- 호출 직전에 정확한 prompt 문자열과 실제 도구 인자를 기록한다. 응답의 빈 prompt 메타데이터를 이유로 호출 입력을 잃지 않는다.
- 실제 반환 원본 PNG를 변경 없이 먼저 보존하고 SHA를 계산한다. crop/resize/composite는 파생 파일로 구분한다.
- PNG RGBA 모드만으로 투명 배경 PASS를 주지 않는다. 실제 알파, 배경판·체커보드, 문자 영역을 확인한다.
- 이미지에 인쇄된 SHA·PASS·치수는 검증 결과가 아니다.
- 도구가 생성 ID를 노출하지 않으면 unavailable로 기록하고 실제 출력 SHA와 호출 기록으로 식별한다. 가짜 ID를 만들지 않는다.
- 생성 실패도 프롬프트/참조/출력/원인 기록을 보존한다. 바이너리 미게시와 생성 실패는 별도 상태다.

## 7. 실패 종류에 따라 다음 요청을 바꾼다

| 실제 실패 | 다음 입력 변경 |
|---|---|
| 비교표·콜라주·추가 문구 | 참조를 영문 단일 crop으로 재구성하고 시각 제작 지시만 전달 |
| 다른 한글/오자/누락 | 승인 문구 확인, 한 레이블로 축소; 정확한 글자 위치를 지정해 편집 |
| 콜론·숫자 형태 오류 | 원본의 해당 부호 crop을 확인하고 개수·배치·형태를 명시 |
| 원본과 다른 획·색·기울임 | 모호한 '레이싱 느낌' 대신 관찰한 차이 한 가지를 구체화 |
| 실제 글자 1개가 안 읽히거나 손상 | 해당 자소의 네이티브 획·높이·내부 공간만 수정; 전체 영문/한글 문장 폭·비율 차이는 반려 금지 |
| 외곽선·광륜 과다 | 원본 효과 범위를 기준으로 줄이도록 편집하고 네이티브 결과 확인 |
| 투명 대신 배경 생성 | 도구 인자·알파를 확인하고 투명 글자층으로 재요청; 휴리스틱 배경제거를 원본 투명 출력으로 위장 금지 |

읽히는 후보의 일부만 문제라면 해당 후보를 참조한 제한 편집을 우선 고려한다.
예: '기존 네 글자의 형태·색·기울임을 유지하고 마지막 콜론만 원본처럼 작은 두 점으로 수정한다.'
모델이 다른 부분도 바꿀 수 있으므로 편집 후 전체 문구와 스타일을 다시 확인한다.
한 번의 재시도에서는 주된 변경을 명시하고, 동일 실패가 반복되면 입력/참조/방법 변경 근거 없이 같은 요청을 반복하지 않는다.
프롬프트만으로 해결되지 않는 경우 사실대로 HOLD/REWORK를 기록한다. B·C1 폰트/벡터 우회 금지는 유지한다.

## 8. 생성 후 판정 순서

1. 요청한 레이블 하나인지, 한글·공백·숫자·문장부호가 정확한지 확인.
2. 참조와 획·기울임·색·효과·위계를 대조하고 실제 알파와 bbox 측정.
3. 검증된 CLEAN과 기존 pipeline으로 네이티브 크기 합성. 실제 출력에 맞춘 fit 검토.
4. 실저장 DDS RAW/FLIP-Y, MIP, 100/75/50%, 영역 밖·보호 픽셀 검사.
5. 생산자 self-QA와 C2/C3/실게임 상태를 따로 기록.

1~2 실패를 숨긴 채 DDS 생성 성공만으로 생산 PASS를 주지 않는다.
반대로 정상 생성물을 QA 대시보드로 다시 그리게 하지 않는다. 비교 이미지는 검증 도구로 만든다.

## 9. 호출별 최소 기록과 개선 비교

기존 imagegen_requests의 자산별 기록을 사용한다. 새 큐를 만들지 않는다.
기존 consumer 스키마를 임의 변경하지 않고 필요한 호출 기록은 별도 JSON sidecar로 남긴다.

- TASK_ID / role / queue_index / attempt / base HEAD / 이전 attempt 참조
- 정본 문구, 원본 DDS SHA, 참조 crop 경로·SHA·좌표·방향
- 실제 prompt 원문, 실제 도구 인자, 템플릿 버전
- 생성 ID(노출 시), 원본 PNG SHA/경로/게시 여부
- 이전 호출 대비 바꾼 항목과 가설, 실제 관찰 실패, 다음 조치
- 글자층 bbox/알파/네이티브 축소 결과, trial DDS SHA(생성 시)
- PRODUCER / C2 / C3 / RUNTIME_VALIDATION 각각의 상태

같은 자산/원본/문구를 기준으로 시도 수, 문구 정확성, 스타일 수용, 첫 C2 PASS까지 시간을 비교한다.
프롬프트 개선 효과는 실험 전에는 미검증이다. 정책 추가를 새 DDS나 QA PASS로 집계하지 않는다.
서로 다른 난이도 자산의 단순 생성 횟수만으로 A/B/C1 우열을 확정하지 않는다.

## 근거와 검증 범위

- role_B/imagegen_requests/q060_B370_OUTPUT_INVALID_20261011.json
- role_B/imagegen_requests/q060_B371_IMAGEGEN_SCOPED_HANGUL_MISSING_COLON_20261011.json
- role_B/imagegen_requests/q060_B372_SOURCE_STYLE_PUNCT_HOLD_20261011.json
- role_C1/imagegen_requests/q102_20261011_1710_IMAGEGEN_HOLD.json

위 경로는 localization/graphics/ 아래다.
기록상 실패 현상을 근거로 설계했다. 과거 전체 실제 호출 입력이 없어 근본 원인 확정은 하지 않는다.
이 지침 도입 시점 신규 이미지 생성 시험: NOT_RUN. RUNTIME_VALIDATION=UNTESTED.
