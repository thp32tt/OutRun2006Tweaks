2026-10-15 사용자 최신 방식: 기존 986개 분할 타일을 신규 이미지 생성에 사용하지 마. 먼저 한글화 자산 브랜치 docs/OUTRUN_TEXT_ROI_IMAGEGEN_20261015.md를 읽어. HD 전체 원본의 글자+윤곽+그림자가 온전히 들어가는 1문구/1ROI PNG를 추출한 뒤 필요시 2~4배 확대, 원문/한글 정본과 좌표·SHA가 검증된 ROI가 실제 첨부된 경우에만 ChatGPT 이미지 생성. 한글 텍스트+효과만 투명 배경에 제작하고 완성된 원본/UI 영역에서 잘림·겹침·보호 아트 변경을 금지해. 검증된 ROI가 준비되지 않으면 HOLD하고 이전 타일 큐를 소비하지 마. 기존 A/B state, queue, 이미지 파일은 보존하고 삭제하거나 완료 판정을 재사용하지 마. C1/C3와 사용자 게임 QA는 별도. Portainer 배포는 사용자 수동.

---

OutRun 한글화 A 실행

모든 제작/QA 역할에 최신 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md` 필수 적용: 영문과 한글의 글자 수·문장 전체 폭/높이/가로세로 비율/underfill 차이만으로 반려 금지. 번역이 짧거나 글자가 조금 작아도 개별 한글 글자의 native·75·50% 획/내부 공간/가독성이 정상이면 크기 PASS. 원문 glyph/effect bbox 1px 초과는 FAIL. 기존 underfill 단독 반려는 크기 기준 PASS로 재심사하되 오자/보호 아트/실기/C2/C3는 허위 승인 금지.


저장소: thp32tt/OutRun2006Tweaks
브랜치: korean-localization-recovery-20260928

첫 작업은 이 브랜치의 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md를 읽는 것이다.
그 문서의 A 제작 및 글자별 크기 QA 역할대로 실제 미완료/REWORK 작업을 수행하고, 완료된 작업은 반복하지 마.
작업 결과와 필요한 상태/QA 기록을 같은 브랜치에 반영하고 실제 변경이 있으면 commit/push 후 HEAD SHA를 확인해.
VR/FFB/DX11/DXVK 작업은 하지 마. 장황한 계획이나 상태 설명보다 실제 한글화 작업을 우선해.
