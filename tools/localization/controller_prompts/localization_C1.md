OutRun 한글화 C1 실행 — B 방식 ChatGPT 이미지 생성 전용 생산 + 자체 QA (최신 사용자 지시)

**2026-10-11 모든 작업 공통 크기판정 최우선:** 최신 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`를 반드시 먼저 읽고 적용한다. 한글/영문 **문장 전체** 폭·가로세로 비율·글자 수가 달라 작아 보이는 것만으로 REWORK/HOLD 금지. 크기가 더 작아도 가독성 있으면 크기 항목 PASS. 영문 원본 glyph/effect bbox를 넘지 않는지 확인하고, 한글 **글자마다** native 획·자소·가독성·효과를 실제 검사한다. 기존 underfill/width-ratio 단독 반려는 크기 기준 PASS로 재평가한다. 오자·획 깨짐·잔상·침범·다른 검수 및 C2/C3·실게임 미검증은 그대로 유지한다.



저장소 thp32tt/OutRun2006Tweaks / 브랜치 korean-localization-recovery-20260928.
즉시 최신 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md 와 docs/KOREAN_LOCALIZATION_B_IMAGEGEN_LANE.md, SOURCE/CLEAN/EVIDENCE/PRODUCTION 정책 및 최신 queue/INGAME_REWORK_BACKLOG를 읽어.
C1은 더 이상 홀수 QA가 아니다. B와 같은 **실제 ChatGPT 이미지 생성 도구**를 호출해 투명 한국어 글자 RGBA PNG를 생성하는 별도 생산 레인이다. 신규 미할당 짝수 index % 4 == 2의 재작업/P0/P1/RENDER_READY 중 제작 가능한 자산을 생산해. A의 홀수와 B의 신규 even % 4 == 0 및 과거 B가 선점한 진행 중인 even 자산을 덮어쓰지 마. 명시적으로 담당 지정된 사용자 P0/P1은 최신 HEAD 소유권 우선.
원본 영문 SOURCE를 실제 이미지 레퍼런스로 제공하고 한글 정본의 정확성·서체 계열·기울기·입체 효과·배경 분리·소스 bbox 보호를 요구해. 반드시 진짜 imagegen 결과/생성 ID/전체 프롬프트/PNG SHA를 수집하고 role_C1/imagegen_requests/ 내에 C1 전용 outrun-c1-imagegen-v1 manifest+PNG를 저장해. tools/localization/imagegen_b_pipeline.py를 C1 manifest로 실행하여 role_C1/imagegen_trials/에 미승격 DDS 및 SOURCE/CLEAN/OFFICIAL/GENERATOR 비교 이미지를 생성한 뒤 10단계 생산 자체 QA, 저장 DDS RAW/FLIPY 시각 검수를 수행해.
도구를 실제 호출할 수 없으면 IMAGEGEN_UNAVAILABLE/OUTPUT_MISSING 사실만 기록하고 폰트/벡터/허위 이미지 생성을 가장하지 마. 검토만 반복하거나 생성 없는 리포트만 연속 생산하지 말고 다른 C1 생산 가능 작업을 시도해. 자체 QA는 절대 독립 C2/C3/실게임 승인으로 치지 마. RUNTIME_VALIDATION=UNTESTED.
실물 PNG/DDS/manifest, 작업 queue/resume/progress/WORKLOG/STATUS를 같은 브랜치에 commit/push하고 원격 HEAD 검증해. 사용자 배포는 하지 마. VR/FFB/DX11/DXVK는 수정 금지.
