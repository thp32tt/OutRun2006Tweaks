# OutRun 2006 — HD 원본 기준 DDS 전체 재조립 / QA 재시작 (2026-11-04)

## 사용자 판정과 기존 산출물 처리
- 2026-11-04 사용자 직접 확인: 기존 DDS→JPG 샘플에서 원본보다 큰 한글, 원문 잔존, 배경 및 다른 UI 침범을 확인. **기존 11/35 및 60/200 DDS는 전부 사용자 품질 기준 미통과이며 새 QA의 승인 목록에 넣지 않는다.**
- 이전 `OUTRUN_AB_IMAGEGEN_MULTI_ATLAS_TEST_ONLY.zip`과 그 이력은 진단용으로만 보존. 사용자에게 최종 패치로 제시하거나 합격/완료 수로 이관하지 않는다.
- 새 실행은 `OUTRUN_AB_HD_STRICT_CLEAN_TEST_ONLY.zip`을 **원본 104 DDS + 보존된 A/B ImageGen 한글 PNG 954개**에서 처음부터 재생성한다. 폰트 재렌더, 과거 DDS 픽셀 재사용, 생성 이미지 업스케일/원문 위 덧칠을 금지한다.

## QA 정본과 구체적 차단 조건
1. 고정된 HD 원본 DDS의 SHA256, 원래 포맷·크기·RAW/FLIP-Y 방향을 104-원본 소스 계획과 교차 확인한다.
2. 크롭 좌표는 **실제 HD source DDS 네이티브 픽셀 기준**이다. PNG 파일명에 옛 저해상도 이름이 남아도 헤더의 HD 크기를 따른다.
3. 영어가 독립적인 투명 글자층이면 **영어 alpha 효과/그림자 전체를 CLEAN에서 투명하게 지운 다음** 한글만 합성한다. 지워진 원본 alpha 잔상이 CLEAN에 하나라도 남으면 실패다.
4. **투명한 원문 글자층임을 증명할 수 없는 불투명 패널·차량/로고·복합 배경·불명확한 글자 마스크는 HOLD**. 임의 검은 사각형/인페인팅 추측으로 패치를 만들지 않는다. 원본 PSD·CLEAN/정밀 마스크를 확보한 뒤 독립 검수한다.
5. 새 한글은 **원본 문구의 각 줄별 실제 글자+외곽선+그림자 bbox보다 1px도 커지면 안 된다.** 원본 한글 후보를 획일적으로 확대하거나 전체 문장 길이를 맞추기 위해 늘이지 않는다. 종횡비 유지 축소만 허용하며 더 작은 한글은 정상이다.
6. 원문이 2줄이면 한글도 2줄이어야 한다. 소스/candidate 줄 수가 다르면 HOLD하고 별도 줄별 수정 후보가 있어야 재검토한다.
7. 한글·영어의 주변 PNG 여백이 없거나 텍스트/그림자가 가장자리에서 잘리면 HOLD. 서로 다른 UI 문구·보호 아트가 같은 ROI에 섞이거나 겹치면 임의로 덮어쓰지 않는다.
8. SOURCE→CLEAN→FINAL lossless 미리보기와 저장된 native DDS의 방향 복원 및 헤더/픽셀 roundtrip 증거를 생성한다. 기계적 합격만으로 C1, C3 또는 게임 QA PASS를 만들지 않는다.
9. 전체 954개 활성 ROI에서 `converted + per_reason_hold == 954` 불변식을 CI로 강제한다. 보류 사유가 없거나 누락된 영역을 "완료"로 집계하지 않는다.

## 구현 및 증거
- `tools/localization/hd_strict_qa.py`: 새 엄격한 SOURCE/CLEAN/FINAL DDS 합성 엔진.
- `tools/localization/github_ab_imagegen_atlas_batch.py`: 기존 취약한 부분은 남겨 과거 회귀와 비교하지만, **생산 경로는 반드시 엄격 엔진으로 실행**한다.
- `tools/localization/test_hd_strict_qa.py`: 영어 제거, 투명 CLEAN, 원문 줄 크기보다 큰 글자 축소, 2줄 유지, 원문/한글 경계, 보호 픽셀, 저장 RAW/FLIP-Y를 회귀 검사한다.
- `.github/workflows/outrun-ab-multi-atlas.yml`: 매번 SHA가 고정된 원본 PNG+DDS로 전체 재조립하고 두 번 빌드해 결정성을 비교한다. SOURCE_/CLEAN_/PREVIEW_는 화면 판단을 위한 PNG이고 RELEASE 승인 아님.
- `.github/workflows/outrun-ab-multi-atlas-safety-tests.yml`: 새 엔진의 빠른 테스트 포함. GitHub Actions 실행 `41775150366`에서 기존 13건 + 엄격 8건 = 21/21 PASS.
- `qa_report.json`: 각 합성 ROI에 source-native lines / Korean-native lines / 알파 CLEAN / 후보 SHA / 수치 QA 근거 기록. `release_approved=false`, `runtime_validation=UNTESTED`, `visual_qa=REVIEW_REQUIRED`을 유지한다.

## 남은 게이트와 재작업 순서
- 1순위: 원문 크기·배경 제거가 정확한지 SOURCE/CLEAN/FINAL 같은 배율로 C1에서 서로 다른 후보 4~8건 독립 확인. 사용자가 지적한 Q044/HUD/두 줄 사례를 우선한다.
- 2순위: 혼합 배경·불투명 보호 아트에 대한 별도의 검증된 CLEAN/PSD 텍스트 마스크. 원본 아트 변경은 0이어야 한다.
- 3순위: BC/DXT·mipmap 형식은 원래 포맷/모든 mip 복원이 가능한 독립 DDS 인코더·roundtrip 검사까지 자동 생성 금지.
- 4순위: 나머지 ROI 교차·중복 목록을 실제 인게임 UV/원문 텍스트 기준으로 수동 분할하거나 안전한 단독 합성 대상으로 독립 인증한다.
- 최종 단계: C1, C3, 사용자 실제 게임 QA까지 별도 통과하고 SHA가 일치하기 전에는 승인된 104 DDS 완성·출시를 주장하지 않는다.

## 배포 경계
이 변경은 GitHub Actions 작업만 바꿨다. N100 Portainer 재배포가 필요한 변경은 없다. 이전 60 DDS/200 ROI 기록은 *과거 위험한 시험 출력*이며 새 최종 진행률이 아니다.
