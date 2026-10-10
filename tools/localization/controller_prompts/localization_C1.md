OutRun 한글화 C1 실행 — 홀수 자산 독립 QA 및 별도 C3 엄격 검수

저장소 thp32tt/OutRun2006Tweaks, 브랜치 korean-localization-recovery-20260928.
최신 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md 및 docs/KOREAN_LOCALIZATION_PLATE_LIBRARY.md부터 읽고 현재 Git 작업을 이어서 실제 실행해.
공통 plate_library를 원본 SHA·영역·방향으로 조회하고 기존 플레이트를 재분리하지 마. A/B는 독립 승인된 플레이트를 prepare로 확인하여 기존 자산별 렌더 레시피에 사용해. C1/C2는 저장된 SOURCE/CLEAN 및 새 한글/persisted DDS를 독립 검수하고 플레이트 승인과 최종 C/C3 승인을 분리해.
한글 글꼴·윤곽·기울기·입체감이 실패하면 해당 제작 단계를 고치고 정상 배경을 다시 만들지 마. 계열 대표의 독립 C 통과 전 확산 금지.
기존 소유권·실게임 OPEN·10단계 QA를 유지하고 실제 변경만 같은 브랜치에 commit/push 후 원격 SHA를 확인해. VR/FFB/DX11/DXVK는 수정하지 마. 계획/상태 설명만으로 끝내지 마.
