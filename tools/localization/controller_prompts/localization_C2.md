OutRun 한글화 C2 실행 — A/B/C1 모든 제작 자산의 유일한 독립 최종 QA

**2026-10-11 모든 작업 공통 크기판정 최우선:** 최신 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`를 반드시 먼저 읽고 적용한다. 한글/영문 **문장 전체** 폭·가로세로 비율·글자 수가 달라 작아 보이는 것만으로 REWORK/HOLD 금지. 크기가 더 작아도 가독성 있으면 크기 항목 PASS. 영문 원본 glyph/effect bbox를 넘지 않는지 확인하고, 한글 **글자마다** native 획·자소·가독성·효과를 실제 검사한다. 기존 underfill/width-ratio 단독 반려는 크기 기준 PASS로 재평가한다. 오자·획 깨짐·잔상·침범·다른 검수 및 C2/C3·실게임 미검증은 그대로 유지한다.



저장소 thp32tt/OutRun2006Tweaks, 브랜치 korean-localization-recovery-20260928.
최신 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md, docs/KOREAN_LOCALIZATION_EVIDENCE_GATE.md, docs/KOREAN_LOCALIZATION_PLATE_LIBRARY.md, 최신 queue/INGAME_REWORK_BACKLOG부터 확인해.
C1은 B와 같은 **이미지 생성 생산자**로 전환됐다. C2는 홀수/짝수 구분 없이 A(홀수), B(even %4=0 신규), C1(even %4=2 신규), 기존 B 진행 중인 모든 짝수 및 인덱스 없는 특별 C 작업의 독립 QA와 PLATE_PASS를 담당한다. 이미 저장된 최신 SOURCE/CLEAN/생성 PNG/저장 DDS에서 1회 최대 3개의 실제 검증 가능한 항목을 검토해. 실제 사용자 게임 결함 P0/P1, 최신 미검증 DDS, PLATE/CLEAN부터 우선한다.
정본 오타·가짜 획·폰트 계열·원본 RAW/FLIPY 비교, 잘못된 CLEAN, source bbox 1픽셀 침범, 타 UI 손상, mip/투명층을 실제 파일 기준으로 확인하고 증거/정확 SHA를 저장해. 숫자 PASS만으로 승인하지 마. 기존 SHA의 동일 근거 재검수만 되풀이하지 말고 신규 생성 문제를 구체적으로 생산자에게 REWORK로 반환해. C3/사용자 실게임 검증은 별개이며 아직 미검증이면 RUNTIME_VALIDATION=UNTESTED.
새 승인·반려 증거 및 queue/resume/progress/WORKLOG를 같은 브랜치에 commit/push하고 원격 HEAD 확인해. VR/FFB/DX11/DXVK, 신규 큐/컨트롤러 TASK_ID 도입 금지.
