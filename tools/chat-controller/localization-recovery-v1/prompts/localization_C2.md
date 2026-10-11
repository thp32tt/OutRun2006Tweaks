OutRun 한글화 C2 독립 최종 QA 실행

모든 제작/QA 역할에 최신 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md` 필수 적용: 영문과 한글의 글자 수·문장 전체 폭/높이/가로세로 비율/underfill 차이만으로 반려 금지. 번역이 짧거나 글자가 조금 작아도 개별 한글 글자의 native·75·50% 획/내부 공간/가독성이 정상이면 크기 PASS. 원문 glyph/effect bbox 1px 초과는 FAIL. 기존 underfill 단독 반려는 크기 기준 PASS로 재심사하되 오자/보호 아트/실기/C2/C3는 허위 승인 금지.


저장소: thp32tt/OutRun2006Tweaks
브랜치: korean-localization-recovery-20260928

첫 작업은 최신 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 docs/KOREAN_LOCALIZATION_EVIDENCE_GATE.md를 읽는 것이다.
C1은 B와 같은 ChatGPT 이미지 생성 생산으로 전환됐으므로 C2만 A/B/C1의 전체 홀수·짝수 후보 및 인덱스 없는 특별 C 작업을 독립 최종 검수한다. 현재 생성된 새 후보, 실제 P0/P1 게임 결함, PLATE 검토를 우선하고 최신 Git HEAD/큐를 기준으로 최대 3개까지 실제 픽셀·DDS·근거 있는 글자별 QA를 수행해. 문장 전체 폭/height ratio만으로 REWORK하지 마.
SOURCE/CLEAN/글자층/저장 DDS/RAW/FLIPY, 오자·가짜 획, 초과 픽셀, 다른 UI 훼손을 확인한다. 독립 C2 PASS 없이 생산자가 자신을 승인할 수 없으며 C3와 사용자 실게임 테스트는 별개다. 기존 후보 SHA를 변경 없이 반복 검수해 생산 성과로 표시하지 마.
결과·증거·상태를 같은 브랜치에 commit/push하고 원격 HEAD를 확인해. VR/FFB/DX11/DXVK 및 별도 큐 엔진/TASK_ID는 사용하지 마.
