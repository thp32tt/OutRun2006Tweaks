OutRun 한글화 B 실행 — 신규 index % 4 == 0 짝수 자산, ChatGPT 이미지 생성 전용 생산 + 실제 저장 DDS/QA

**2026-10-11 모든 작업 공통 크기판정 최우선:** 최신 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`를 반드시 먼저 읽고 적용한다. 한글/영문 **문장 전체** 폭·가로세로 비율·글자 수가 달라 작아 보이는 것만으로 REWORK/HOLD 금지. 크기가 더 작아도 가독성 있으면 크기 항목 PASS. 영문 원본 glyph/effect bbox를 넘지 않는지 확인하고, 한글 **글자마다** native 획·자소·가독성·효과를 실제 검사한다. 기존 underfill/width-ratio 단독 반려는 크기 기준 PASS로 재평가한다. 오자·획 깨짐·잔상·침범·다른 검수 및 C2/C3·실게임 미검증은 그대로 유지한다.



저장소 thp32tt/OutRun2006Tweaks / 브랜치 korean-localization-recovery-20260928.
첫 작업은 최신 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md를 읽는 것이다. 이어 docs/KOREAN_LOCALIZATION_B_IMAGEGEN_LANE.md 및 기존 SOURCE/CLEAN/EVIDENCE/PRODUCTION 정책을 읽는다.

최신 INGAME_REWORK_BACKLOG.csv의 B 담당 P0/P1, asset_queue.csv의 신규 미할당 index % 4 == 0 짝수 REWORK/RENDER_READY 중 실제 생성 가능한 1개를 선택한다. 최신 Git SHA, 원문 영문 DDS, 이미지 원본 SOURCE 미리보기, 독립 C2 PLATE_PASS CLEAN/영문 영역/한국어 정본을 검증한다. 완료/동일 SHA 반복 금지.

**B 신규 글자 제작은 반드시 ChatGPT의 @이미지 생성 (image generation) 도구 실제 호출만 사용한다.** 영문 원본을 시각 참고로 투명 RGBA 한국어 문자 이미지를 생성하라. 글자 정확성, 굵기/기울기/금속 효과/파란 윤곽, 자소 내부 공간과 콜론을 지켜라. 기존 B369/B368 벡터/폰트 레시피를 다시 실행하거나 A 방식으로 대체하지 마. 생성 도구가 해당 자동 ChatGPT 세션에 없다면 실제 도구 확인 결과와 IMAGEGEN_UNAVAILABLE을 기록하되 성공한 이미지라고 주장하지 마.

생성 결과의 진짜 generation_id, 도구명, 전체 생성 프롬프트, PNG 원본 바이트 SHA를 기록하고 GitHub role_B/imagegen_requests/ 안에 PNG+manifest를 등록한다. docs/KOREAN_LOCALIZATION_B_IMAGEGEN_LANE.md 스키마에 따라 독립 C2 승인 SOURCE/CLEAN 정확 SHA를 넣고 tools/localization/imagegen_b_pipeline.py 또는 GitHub CPU worker로 **이미지 생성 PNG 후처리만** 실행한다. 1픽셀 초과, 비투명 PNG, SHA/입력 오류, 편집 글자 누락이면 HOLD/REWORK. 프로덕션 승격 전 native100/white75/black50/RAW에서 **저장된 DDS** SOURCE/CLEAN/OFFICIAL/B-ImageGen 비교를 실제 눈으로 본 후 8항목 QA를 기록한다. 이미지 생성 특유 오자/가짜 획은 기계 PASS보다 우선해서 FAIL한다. 독립 C2/C3/실게임은 별개이고 RUNTIME_VALIDATION=UNTESTED.

A는 이전 폰트/벡터 방식 그대로 둔다. A/B/C1은 각각 분리된 담당 자산의 첫 C2 PASS까지 걸린 시간·리워크·생산된 시험 DDS 수를 기록해 경쟁 속도를 비교하고, 서로 후보 재제작하지 않는다. 작업 결과와 queue/resume/progress/WORKLOG/STATUS를 업데이트하고 실제 변경만 commit/push 후 원격 HEAD SHA를 확인하라. 컨테이너 배포/재시작은 사용자가 하므로 실행하지 않는다. VR/FFB/DX11/DXVK는 수정하지 마.

동일 even-shard의 C1 신규 index % 4 == 2 작업과 절대로 중복 생성하지 마. 과거 이미 B가 작업하던 index % 4 == 2는 새 C1 생산으로 넘기지 말고 기존 담당·Git HEAD 변경을 보존해.
