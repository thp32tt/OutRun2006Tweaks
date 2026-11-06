# OutRun 2006 HD 한국어 리소스 적용·검증·배포 계획 — 2026-11-06 KST

## 범위·목표

- **목표:** A/B가 이미 만든 고품질 한글 PNG를 재생성하지 않고, 사용자가 적용한 HD 모드의 원본 DDS를 텍스트 영역에 한해 교체하여 **검증 가능한 게임 시험 패치**로 제공한다.
- **게임 교체 경로:** OutRun2006Tweaks texture loader의 기본 \`textures/load/\` 파일명·서브폴더 구조. 게임 실행 파일·FFB·VR·로더 자체 코드는 이 작업에서 수정하지 않는다.
- **정본:** \`thp32tt/OutRun2006Tweaks@korean-localization-recovery-20260928\`. GitHub CPU에서 DDS 합성·QA·압축 실행. N100은 이미지 처리를 하지 않는다.
- **생산 자산:** 954 활성 번역 ROI, 기존 A/B 한글 PNG 954/954 이관 완료, 원본 활성 DDS 104종은 별도 SHA 계획으로 관리. 지금의 패키지는 원본 게임 패치 또는 최종 배포 승인을 의미하지 않는다.
- **기존 최종 확인된 안전 산출물:** 250 ROI가 46 HD DDS 아틀라스에 TEST_ONLY 합성, 704 ROI HOLD; 자동 보정 245 ROI.
- **변경 후 전체 재검증:** GitHub Actions 42123678870, commit \`2ad912267fdc1e987fd0e24fa833ee358bb67c99\`; **완료 결과/수량 미확정**. 마지막으로 성공한 기존 산출물은 run 41953585087, SHA \`2a759c7cd7a923bfcdf1235116ee92b51118b89b\`.

## 실제 사용 가능한 1차 시험 패키지 (구현·실행 완료)

- \`.github/workflows/outrun-hd-korean-preview-package.yml\`는 기본 브랜치의 GitHub CPU 워크플로. workflow_dispatch 또는 다중 아틀라스 빌드의 **SUCCESS** \`workflow_run\`에서만 실행; 초기 push는 **마지막으로 성공한** exact run을 사용.
- 성공 검증: **42131850343** / artifact **13463068075**, \`outrun-korean-hd-preview-test-only-42131850343\`; SHA-검증된 내부 패키지 \`OUTRUN_KOREAN_HD_PREVIEW_TEST_ONLY.zip\`, 46 DDS, 250 합성 ROI, 704 HOLD, 바깥 GitHub artifact ZIP SHA256 \`892f0aa2dbb3702b49b87ba3233017f44ccac839dfc621a10596e502e8386992\`.
- 내부 TEST_ONLY 패치 ZIP SHA256 \`19938848c794f62075f251031bf551d2b27c564f2af919f4cecb87f0d313950c\`. 원본 A/B QA ZIP의 SHA는 패치 manifest에 기록된다.
- 엔진 \`tools/localization/make_hd_korean_test_patch.py\`는 정확한 이전 성공 RUN ID/SHA, QA/zip SHA, 각 DDS SHA, 경로 유효성, 954 ROI 보류 분류 합계, 원본 DDS SHA, zip CRC, TEST_ONLY/UNTESTED 상태를 검증한 뒤에만 패치 ZIP을 생성. 승인되지 않은 추가 파일이나 예상하지 못한 DDS는 통과시키지 않는다.
- 패키지 안의 \`Install-OutRunKoreanTest.ps1\`는 사용자 지정 **실제 게임 경로를 명시하고 \`-ConfirmTestOnly\`를 넣어야만** 실행한다. 기본 5개 아틀라스 카나리; \`-ApplyAll\`은 명시적 확장 시험이다. 기존 HD DDS의 SHA가 원본 계획과 다르면 절대 덮어쓰지 않는다. 기존 파일이 없으면 기본 HOLD(옵션 \`-AllowMissingSource\`는 별도 사용자 검증 후). 설치 전 전부 검사하고, 백업·롤백 JSON과 기록을 남긴다. \`UITextureReplacement=true\`, \`TextureBaseFolder=textures\` 확인.
- 기본 설치 예 (Windows PowerShell, 압축을 안전한 폴더에 푼 후): 
  \`.\Install-OutRunKoreanTest.ps1 -GameDirectory "D:\Games\OutRun2006" -ConfirmTestOnly\`
- 복구 예 (설치 결과가 출력한 백업 경로를 사용):
  \`.\Install-OutRunKoreanTest.ps1 -GameDirectory "D:\Games\OutRun2006" -ConfirmTestOnly -Rollback -BackupDirectory "D:\Games\OutRun2006\_KoreanTestBackups\YYYYMMDD_HHMMSS"\`
- **주의:** 정식 배포 버전이 아니며, 사용자의 Windows 게임 환경은 이 CI에서 접근하거나 시험하지 않았다. 게임을 실행하기 전부터 패치 자동적용하지 않는다.

## 단계별 잔여 704 HOLD 처리 우선순위

1. **실제 원본 alpha 교차 점검 (457 ROI):** 광역 ROI 메타데이터가 겹쳐도 원본 공유 알파가 없고 새 한글 알파도 다른 문구에 들어가지 않을 때만 재시험 합성. 소스 픽셀 공유는 계속 HOLD. \`059f326bf924\` + \`2ad912267fdc\`로 안전 검사와 회귀 테스트 구현; fast safety 42123678819 SUCCESS. 새로운 합성 ROI 수는 최신 full QA 보고서 확인 전까지 주장하지 않는다.
2. **원본 DDS 압축/밉맵 변형 (111 ROI):** 미지원 FOURCC/BC 또는 mip 체인 포맷별 SHA·header·실제 길이를 분류. 원본 포맷과 mip 수/차원 유지 가능한 encode/decode roundtrip이 검증된 경우에만 합성. BGRA로 강제변환 또는 mip 손실 금지.
3. **원문 경계 좌표 (80 ROI):** 원본 알파 경계의 외부 이웃 픽셀을 검증한다. 이웃이 불명확하면 HOLD; 새 ImageGen으로 해결하려 하지 않는다.
4. **복합 원문 셀 (30 ROI)와 불확실한 알파 분리 (21 ROI):** 영어만 지우는 검증된 CLEAN/마스크를 별도 승인해야 한다. 게임 메뉴·아이콘·HUD 픽셀 손상 위험이 있으면 HOLD.
5. **소형 글자/자소 손상 (5 ROI):** 기존 A/B 픽셀의 패딩·줄 재배치·다운스케일만 우선; 잔상/오탈자/가독성 위험이 남는 후보는 수동 QA.
6. **QA/실게임 게이트:** 정확한 저장 DDS를 SOURCE/CLEAN/FINAL·native/50%·FLIP-Y/RAW로 비교. C1/C3는 원문 삭제, 한글 자소, 원문보다 큰 효과, 두 줄 레이아웃, 보호 아트 침범을 확인. 최종 사용자가 실제 게임 스크린샷으로 승인 전에는 \`release_approved=false\`, \`runtime_validation=UNTESTED\` 유지.

## 다음 자동화·배포 승격 기준

- **빌드와 배포 분리:** 각 DDS 합성 커밋 후 두 번의 결정적 QA 실행; 성공 실행의 TEST_ONLY artifact와 보고서 SHA를 고정. 설치 ZIP을 생성해도 RELEASE로 승격하지 않는다.
- **신규 성과 판단:** exact branch/HEAD, Actions run ID, QA artifact SHA 및 \`translated_roi_generated + hold ROI = 954\` 확인; 전부 동일한 SHA라면 추가 성과로 재계산하지 않는다.
- **사용자에게 수동 작업을 요청할 때:** 테스트 패키지 수령 및 게임 폴더에 카나리 설치가 가능한 시점에만 알린다. 기본적으로 N100 Docker/Portainer 재배포 불필요.
- **최종 배포 승인:** 필수 현장 테스트와 버그 없음이 확인되면 별도 서명·버전별 출시 승인 단계를 만든다. 현 상태의 TEST_ONLY ZIP을 정식 릴리스에 재사용하거나 자동 승격하지 않는다.


## 2026-11-06 10:04 KST — DXT5 네이티브 시험 결과 및 다음 병목

- 포맷 미지원 111 ROI가 15개 DDS에 걸쳐 있음. 직접 읽은 원본 DDS 헤더는 `DXT5` (BC3). `568D3696_1024x1024.dds`는 4096x4096, 13 mips로 기존 서브밉 영문 잔상을 막을 수 없으므로 여전히 HOLD.
- GitHub 자산 브랜치에 `hd_bc3_index_patch.py` / `test_hd_bc3_index_patch.py` 및 BC3 통합기를 구현. RGB565 엔드포인트 보존/변경 픽셀 인덱스만 수정하는 1차 경로와, 엄격한 저장 바이트·원문 주변 픽셀 검증을 전제로 DXT5 블록 재압축하는 대체 경로를 구별. 양쪽 모두 TEST_ONLY; 자동 RELEASE 금지.
- **실제 원본 오류 수정:** DDS `dwDepth=1`은 정상 2D 텍스처일 수 있다. `hd_bc3_native_codec.py`에서 기존의 `dwDepth != 0` 일괄 거부를 `dwDepth not in (0,1)`만 거부하도록 변경; cubemap 및 depth2 이상은 여전히 HOLD. 별도 회귀 테스트 통과.
- **DXT5 글자 AA:** 1~255의 약한 알파 획이 0으로 양자화되는 경우를 방지하려고 양 알파 보간 모드와 선택 팔레트를 검사. 원본 보호 알파 또는 색상 손상이 있으면 그대로 HOLD. 이후 16픽셀 컬러 팔레트가 실패할 때 RGB565 엔드포인트를 제한적으로 탐색하되 55/채널 저장 색오차 제한을 완화하지 않음.
- 실제 3개 SHA 원본/기존 A/B PNG 가벼운 실증: `outrun-hd-bc3-canary.yml` GitHub run **42141243845 SUCCESS**. **QA RESULT = 0/3 TEST_ONLY, 3/3 HOLD**. Q098 `42E618FD`: `QA_BC3_TRANSLATED_COLOR_LOSS`; Q055 `2EA557B4`, Q099 `4F68708E`: `QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE`. 안전 제한을 내려 자동 합성하지 말 것.
- synthetic GitHub regression **42141161995 SUCCESS** (서로 다른 아틀라스 픽셀, 글리프, DXT5 헤더 및 AA 검증). 3개 real-source canary는 두 번 실행해 동일한 JSON 및 ZIP 바이트를 검증. 원본 DDS/한글 PNG를 덮어쓰지 않았으며 실제 게임 테스트도 하지 않음.
- 전체 954 ROI 재합성 GitHub Actions **42141161976** (커밋 `9c48e03b4c1ffc79512c4ba56d10bb4c2600d375`)은 이 기록 당시 실행 중. **새 합성 ROI 및 새 아틀라스 증가 없음으로 처리**하여 최신 성공 `last_report.json` 갱신 전 `250/46/704` 기준값을 유지.
- 다음 작업은 겹침·CLEAN/원문 bbox를 원본 SHA로 재심사하고, 안전한 원본 UI 지움/PSD 마스크가 없으면 수동 QA로 넘김. DXT5 13mip은 저장 후 밉 레벨 1..13 전체 갱신·RAW/FLIP-Y/보호 아트 실증 없이는 배포하지 않음.
