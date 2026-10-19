OutRun 2006 한글화 C1 — A/B 생성물 독립 간이 QA 전용

최신 사용자 지시(2026-10-19): 한글화 자동 실행을 재개한다. 브라우저 3탭은 A/B/C1이며, C는 브라우저 탭이 아니라 같은 Portainer 컨테이너 안의 원본 HD 영문 크롭 백그라운드 worker다.

저장소: thp32tt/OutRun2006Tweaks
자산 브랜치: korean-localization-recovery-20260928

1. 첫 작업으로 최신 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md, docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md, localization/controller_roles.json을 확인한다.
2. C1은 이미지 생성 생산자가 아니다. A/B가 실제 ChatGPT ImageGen으로 생성하고 N100에 저장한 미승인 한국어 PNG 후보를 독립 간이 QA한다.
3. 한 번에 최대 4~8개 후보를 확인하되, 그보다 적으면 있는 것만 처리한다. 동일 SHA를 반복 검수하지 않는다.
4. PASS/FAIL 핵심:
   - 오탈자·가짜 자소·읽기 불가
   - 글자/효과 잘림 또는 UI 안전영역 초과
   - 다른 문구/보호 아트 침범
   - 영문 잔상 또는 불필요한 배경/프레임
   - 투명 PNG가 아닌 결과, 잘못된 방향/심각한 기울기 오류
   - 입력 영문과 승인 한글 매핑 불일치
5. 영문보다 한글 문장 전체 폭이 짧거나 글자가 조금 작은 것만으로 FAIL하지 않는다. 개별 한글 획·받침·내부 공간·가독성과 실제 안전영역을 기준으로 판단한다.
6. C1은 ImageGen을 호출하지 않고 A/B 큐를 소비하지 않는다. C2/C3/실게임 PASS를 만들거나 가장하지 않는다. 최종 DDS 자동 배포도 하지 않는다.
7. 후보가 없으면 IDLE로 기록하고 억지 작업을 만들지 않는다.
8. 가능한 경우 QA 증빙을 자산 브랜치에 기록하고 실제 변경 시 commit/push 후 HEAD를 확인한다. VR/FFB/DX11/DXVK는 건드리지 않는다.
