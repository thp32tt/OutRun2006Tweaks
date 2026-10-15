OutRun 2006 한글화 C-ROI-SOURCE 실행 — 기존 A/B 자동화의 제3 ChatGPT 탭
프로젝트: "아웃런 한글화 신규" (VR 프로젝트 금지)
소스 저장소: thp32tt/OutRun2006Tweaks
자산 브랜치: korean-localization-recovery-20260928
컨트롤러 브랜치: localization-controller-recovery-20260928

1. 첫 작업으로 자산 브랜치 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md와 docs/OUTRUN_TEXT_ROI_IMAGEGEN_20261015.md를 읽고 최신 사용자 지시를 우선 적용해.
2. **이전 986개 분할 타일은 새 이미지생성 입력으로 사용하지 마.** 기존 A/B 한글 생성 결과의 분할 이미지·조합·재활용 및 1장씩 재조립 작업은 신규 생산 우선순위에서 제외해. 과거 SHA/아티팩트는 삭제하지 말고 기록으로 보존해. 이미 진행 중인 A/B 배치·큐·상태를 소비하거나 변경하지 마.
3. GitHub의 버전 고정된 원본 HD 전체 PNG, 또는 실제 원본 DDS/검증된 PSD에서 **완전한 영어 원문 전체**를 확보해. 전체 영어 PNG가 없다면 N100의 기존 타일을 대신 사용하지 말고 `HOLD_FULL_SOURCE_MISSING`으로 분리해. 실제 원본 DDS/플랫폼/좌표의 일치 여부를 확인해.
4. 기존 타일 경계와 무관하게 한글화할 영어 **한 문구 전체** 및 외곽선·그림자·빛 효과까지 포함한 1개 ROI를 정방향으로 지정해. 복수 문구는 별도 ROI. 테두리 접촉/잘린 영문이 있으면 보류하고 ROI를 확장해. 번역은 원본 공식 매핑 기준, 음악 제목은 영어 그대로 유지.
5. `tools/localization/text_roi_source_pack.py`와 `outrun-hd-text-roi-v1` ROI manifest로 네이티브 글자 ROI와 2~4배 확대 ImageGen 입력 PNG를 만들어. 원본 전체 PNG SHA, native xyxy, 확대 배율, PNG SHA, 정확한 원문/번역, 원본 DDS 경로를 기록해. 투명 source는 글자 alpha를 사용하고 불투명 배경은 리뷰된 PSD/정확 마스크가 없으면 글자층/CLEAN 완성을 주장하지 마.
6. C에서는 ChatGPT 이미지 생성 도구나 외부 이미지 생성 API를 호출하지 마. 새 글자 ROI PNG를 기존 A/B ImageGen용 **별도 출처 검증된 입력 후보**로만 남겨. 원본 영역보다 한글 결과의 폭이 달라도 자동 반려하지 말고 UI cell/UV 안전영역에 비율 보존 후 복귀하도록 기록해. 마스크 없이 이미지를 추측 합성하지 마.
7. 한 번의 C 실행에서 새로운 문구 ROI 1개를 실제 제작·검증하거나 명확한 HOLD 사유를 기록해. QA는 `TEST_ONLY`이며 C1/C3/실게임 PASS를 선언하지 마. RUNTIME_VALIDATION=UNTESTED.
8. GitHub/ChatGPT 로컬 작업 우선, 실제 원본 파일에만 연결된 MCP N100을 보조로 이용해. RDC 사용 금지. 실물 증빙을 자산 브랜치에 반영한다면 commit/push 후 정확한 원격 HEAD를 확인해.
9. A/B 기존 자동생성 전송을 다시 활성화하려면 검증된 ROI 입력 인덱스, 새 state/queue 및 Portainer 사용자 수동 배포가 별도로 필요하다. 기존 `ab_batch_queue.py`의 986 타일 자동전송을 그대로 부활시키지 마.

VR/FFB/DX11/DXVK 금지. 사용자 번역/검수 정책 우선.
