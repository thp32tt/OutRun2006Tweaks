OutRun 한글화 C2 독립 최종 QA 실행

저장소: thp32tt/OutRun2006Tweaks
브랜치: korean-localization-recovery-20260928

첫 작업은 최신 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 docs/KOREAN_LOCALIZATION_EVIDENCE_GATE.md를 읽는 것이다.
C1은 B와 같은 ChatGPT 이미지 생성 생산으로 전환됐으므로 C2만 A/B/C1의 전체 홀수·짝수 후보 및 인덱스 없는 특별 C 작업을 독립 최종 검수한다. 현재 생성된 새 후보, 실제 P0/P1 게임 결함, PLATE 검토를 우선하고 최신 Git HEAD/큐를 기준으로 최대 3개까지 실제 픽셀·DDS·근거 있는 QA를 수행해.
SOURCE/CLEAN/글자층/저장 DDS/RAW/FLIPY, 오자·가짜 획, 초과 픽셀, 다른 UI 훼손을 확인한다. 독립 C2 PASS 없이 생산자가 자신을 승인할 수 없으며 C3와 사용자 실게임 테스트는 별개다. 기존 후보 SHA를 변경 없이 반복 검수해 생산 성과로 표시하지 마.
결과·증거·상태를 같은 브랜치에 commit/push하고 원격 HEAD를 확인해. VR/FFB/DX11/DXVK 및 별도 큐 엔진/TASK_ID는 사용하지 마.
