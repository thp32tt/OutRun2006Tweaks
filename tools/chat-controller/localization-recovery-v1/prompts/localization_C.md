OutRun 2006 한글화 C — N100 원본 HD 영어 글자 크롭 전용 (2026-10-16 최신 사용자 지시)

현재 모든 한글화 자동 제작·전송은 중단 상태다. C를 별도로 실행하라는 명시적 새 요청이 없으면 자동 전송하거나 기존 큐를 소비하지 마.
프로젝트는 "아웃런 한글화 신규"이며 VR 프로젝트/VR URL/FFB/DX11/DXVK는 절대 사용하지 마.

1. 자산 브랜치 korean-localization-recovery-20260928의 docs/OUTRUN_C_N100_ORIGINAL_CROP_ONLY_20261016.md와 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md를 먼저 확인한다. 과거 C-ROI-SOURCE, C-SALVAGE, ImageGen A/B 작업 지시는 이 사용자 지시로 대체한다.
2. 유일한 새 C 임무는 N100에 보관된 실제 영문 원본 전체 HD PNG(/home/chatgpt-runner2/work/c_salvage_text_roi/source_full_20261012)에서 영어 원문 한 문구 전체의 네이티브 픽셀만 크롭하는 작업이다. 원본 DDS/플랫폼/정방향/전체 이미지 SHA를 대조한다. 986개 분할 타일·타일 재조립본·한글 생성물을 입력으로 쓰지 않는다.
3. 문구별 윤곽·그림자·효과가 잘리지 않도록 별도 XYXY 크롭하고 보호 아트/이웃 문구 접촉을 확인한다. 원본 RGBA·크기·색·알파 그대로 보존. 임의 변형, 2~4배 확대, ImageGen 프롬프트/이미지 생성 호출, 번역 합성, 배경 제거, CLEAN, 마스크 추측, DDS 합성은 금지한다.
4. 원본 및 좌표가 검증된 새 문구에만 tools/localization/c_n100_original_hd_crop_only.py를 사용해 신규 영어 native PNG와 source SHA, crop SHA, DDS path, native xyxy가 포함된 crop_manifest.json을 격리 생성한다. 기존 N100 crop archive/ROI/queue/state를 덮어쓰지 않는다. 불명확하면 HOLD하고 사유를 기록한다.
5. 모든 C 산출물 CROP_TEST_ONLY_REVIEW_REQUIRED, RUNTIME_VALIDATION=UNTESTED. C1/C3/실게임 PASS 선언하지 않는다. ImageGen, 자동 A/B 재전송, ChatGPT ImageGen 프로젝트 업로드, Portainer 자동 배포는 하지 않는다.
6. 기존 A/B/C 상태·SHA·자산 기록은 보존한다. GitHub 증빙 반영 시 새 파일만 커밋하고 원격 HEAD 확인한다. RDC 사용 금지.
