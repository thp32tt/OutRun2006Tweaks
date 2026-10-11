OutRun 한글화 A 실행

모든 제작/QA 역할에 최신 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md` 필수 적용: 영문과 한글의 글자 수·문장 전체 폭/높이/가로세로 비율/underfill 차이만으로 반려 금지. 번역이 짧거나 글자가 조금 작아도 개별 한글 글자의 native·75·50% 획/내부 공간/가독성이 정상이면 크기 PASS. 원문 glyph/effect bbox 1px 초과는 FAIL. 기존 underfill 단독 반려는 크기 기준 PASS로 재심사하되 오자/보호 아트/실기/C2/C3는 허위 승인 금지.


저장소: thp32tt/OutRun2006Tweaks
브랜치: korean-localization-recovery-20260928

첫 작업은 이 브랜치의 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md를 읽는 것이다.
그 문서의 A 제작 및 글자별 크기 QA 역할대로 실제 미완료/REWORK 작업을 수행하고, 완료된 작업은 반복하지 마.
작업 결과와 필요한 상태/QA 기록을 같은 브랜치에 반영하고 실제 변경이 있으면 commit/push 후 HEAD SHA를 확인해.
VR/FFB/DX11/DXVK 작업은 하지 마. 장황한 계획이나 상태 설명보다 실제 한글화 작업을 우선해.
