OutRun 한글화 A 실행 — 홀수 자산 제작 및 자체 QA

**2026-10-11 모든 작업 공통 크기판정 최우선:** 최신 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`를 반드시 먼저 읽고 적용한다. 한글/영문 **문장 전체** 폭·가로세로 비율·글자 수가 달라 작아 보이는 것만으로 REWORK/HOLD 금지. 크기가 더 작아도 가독성 있으면 크기 항목 PASS. 영문 원본 glyph/effect bbox를 넘지 않는지 확인하고, 한글 **글자마다** native 획·자소·가독성·효과를 실제 검사한다. 기존 underfill/width-ratio 단독 반려는 크기 기준 PASS로 재평가한다. 오자·획 깨짐·잔상·침범·다른 검수 및 C2/C3·실게임 미검증은 그대로 유지한다.



저장소 thp32tt/OutRun2006Tweaks, 브랜치 korean-localization-recovery-20260928.
최신 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md 및 docs/KOREAN_LOCALIZATION_PLATE_LIBRARY.md부터 읽고 현재 Git 작업을 이어서 실제 실행해.
공통 plate_library를 원본 SHA·영역·방향으로 조회하고 기존 플레이트를 재분리하지 마. A/B는 독립 승인된 플레이트를 prepare로 확인하여 기존 자산별 렌더 레시피에 사용해. C1/C2는 저장된 SOURCE/CLEAN 및 새 한글/persisted DDS를 독립 검수하고 플레이트 승인과 최종 C/C3 승인을 분리해.
한글 글꼴·윤곽·기울기·입체감이 실패하면 해당 제작 단계를 고치고 정상 배경을 다시 만들지 마. 계열 대표의 독립 C 통과 전 확산 금지.
기존 소유권·실게임 OPEN·10단계 QA를 유지하고 실제 변경만 같은 브랜치에 commit/push 후 원격 SHA를 확인해. VR/FFB/DX11/DXVK는 수정하지 마. 계획/상태 설명만으로 끝내지 마.

새 제작에는 docs/KOREAN_LOCALIZATION_LETTERING_ENGINE.md를 적용해. 작은 글자는 native, 큰 제목은 벡터 윤곽, 금속은 분리 효과 경로를 사용해. A/B는 효과 없는 형태를 먼저 실제 검토하고 face/effect를 compose_lettering.py로 합성해. 새 공식 DDS final manifest에 lettering_recipe SHA를 연결해. C는 producer GEOMETRY_READY를 승인으로 간주하지 말고 글자면/윤곽 비율·자소 공간·원본 계열을 독립 검수해. 기존 최신 계약을 매 실행 읽으므로 이 변경은 컨트롤러 재시작 없이 다음 실행부터 적용한다.

