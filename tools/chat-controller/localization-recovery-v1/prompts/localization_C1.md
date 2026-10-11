OutRun 한글화 C1 이미지 생성 생산 실행

모든 제작/QA 역할에 최신 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md` 필수 적용: 영문과 한글의 글자 수·문장 전체 폭/높이/가로세로 비율/underfill 차이만으로 반려 금지. 번역이 짧거나 글자가 조금 작아도 개별 한글 글자의 native·75·50% 획/내부 공간/가독성이 정상이면 크기 PASS. 원문 glyph/effect bbox 1px 초과는 FAIL. 기존 underfill 단독 반려는 크기 기준 PASS로 재심사하되 오자/보호 아트/실기/C2/C3는 허위 승인 금지.


저장소: thp32tt/OutRun2006Tweaks
브랜치: korean-localization-recovery-20260928

첫 작업은 최신 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md 및 docs/KOREAN_LOCALIZATION_B_IMAGEGEN_LANE.md를 읽는 것이다.
C1은 검수 전용이 아니라 B와 동일한 ChatGPT 실제 이미지 생성 기반 생산 + 자체 QA 레인이다. B와 중복되지 않는 C1의 짝수 큐(기본 index % 4 == 2)를 우선 담당한다. B는 기본 index % 4 == 0이며 A는 기존 홀수 제작을 유지한다. 기진행·명시적 담당 P0/P1은 기존 소유권과 최신 HEAD를 존중한다.
원본 영문 이미지 기반 투명 한국어 글자 PNG를 이미지 생성 도구에서 실제 생성하고 generation_id/프롬프트/SHA를 기록한다. tools/localization/imagegen_b_pipeline.py의 C1 입력 스키마를 사용해 role_C1 시험 DDS/자체 QA를 만들되 C2 독립 QA, C3, 사용자 실게임 검증을 승인으로 가장하지 마.
도구 미제공·바이너리 저장 불가 시 근거를 기록하고 허위 생성, 폰트 우회, 같은 SHA 검수만 반복하지 마. 미완료 다른 생산 항목을 계속 확인한다.
변경된 실물과 queue/WORKLOG/상태를 동일 브랜치에 commit/push하고 HEAD SHA를 재확인해. VR/FFB/DX11/DXVK 및 새 큐 엔진/컨트롤러 TASK_ID 도입 금지.
