# OutRun HD DDS→정방향 PNG→ChatGPT 이미지 생성→좌표 보정→DDS 및 간이 QA

> 2026-10-13 Portainer Git 연결 정정: 컨트롤러 **운영 반영은 Portainer 기존 Git Stack에서 사용자가 수동 Pull and redeploy**. 최신 `docs/OUTRUN_PORTAINER_GITHUB_DELIVERY_20261013.md` 참조. `--stage` 로컬 명령은 레거시 경로이며 Git Stack 필수 명령이 아니다. Git 정책 변경만으로 런타임 controller/image가 바뀌었다고 주장하지 않는다.

> 2026-10-13 한시적 q217 A 단건 실제 첨부/생성 시험: `docs/OUTRUN_A_Q217_IMAGEGEN_SMOKE_20261013.md`. 스테이징에는 `--single-a-smoke`를 명시해야 한다. 원본 SHA 고정, 오직 A 작업 하나, B/C1/watchdog 발송 차단. 운영 배포 및 정상 스케줄 복원은 사용자 수동이고, 시험 PASS가 CLEAN·DDS·C1/C3·실게임 합격을 뜻하지 않는다.
적용: 2026-10-12 사용자 최신 지시. SSOT: thp32tt/OutRun2006Tweaks / korean-localization-recovery-20260928.

## 이 문서의 우선순위
본 문서는 과거의 A 폰트/벡터 신규 제작, B index % 4=0/C1 index % 4=2 이미지 생성 분담, C2 QA 탭·스케줄, 글자만 업로드해야 한다는 전면 금지, 영문 글자 효과 bbox보다 1px 큰 경우 무조건 반려를 대체한다. 단, 실제 HD UI 칸 침범/손상, 가독성, 저장 DDS 무결성, 사용자 실게임 불량 차단은 유지한다.

## 3개 탭 및 작업 소유권
- A: 홀수 자산 및 기존 명시 소유권 작업의 ChatGPT 이미지 생성 생산·자체 간이 QA.
- B: 짝수 자산 및 기존 명시 소유권 작업의 ChatGPT 이미지 생성 생산·자체 간이 QA. 신규 mod4 분할 중지; 과거 C1 소유 INFLIGHT는 명시 소유권 검토 후 인계한다.
- C1: A/B에서 실제 저장된 신규 후보의 독립 간이 QA 전용. 이미지 생성·신규 DDS 생산은 하지 않는다. 한 호출에 서로 다른 최신 항목 4~8개(최대 8개, 후보 부족 시 더 적게)를 한 비교판 묶음으로 검사하고 항목별 판정을 기록한다. 역사적으로 C1 자신이 만든 후보는 스스로 최종 승인하지 않는다.
- C2: 컨트롤러 탭·스케줄·프롬프트·신규 QA/생성을 폐지. 기존 C2 기록/이미 검증한 SHA는 삭제하지 않고 역사적 자료로만 보존한다. 가짜 C2 PASS를 생성하지 않는다.
- C3 및 사용자 실게임 재검증: 독립적 후속 단계. 특히 P0/P1/HUD/공유 아틀라스·정식 배포에서는 유지.
- 컨트롤러 활성 탭 순서: A, B, C1. C2 탭은 생성하지 않으며 기존 대화 기록은 파기하지 않는다.

## A/B 입력과 이미지 생성
1. 최신 Git HEAD·asset_queue.csv·INGAME_REWORK_BACKLOG.csv·담당자와 실제 게임 OPEN 상태를 확인한다.
2. 정본 HD DDS의 실제 SHA와 헤더(해상도/포맷/mipmap)를 확인한다. 이전 한글 후보나 저해상도 업스케일을 원본으로 사용하지 않는다.
3. 원본 DDS를 ORIENTATION_POLICY에 따라 사람이 읽는 정방향 READABLE PNG로 변환한다. 원본 텍스처 아틀라스의 UV 칸·문구별 ROI/bbox·원본 좌표·RAW/FLIPY 역변환 정보를 기록한다.
4. 원본 HD DDS에서 변환한 정방향 PNG 전체 이미지를 ChatGPT에 실제 파일로 업로드하는 것을 허용한다. 여러 문구 때문에 글자 오류가 나면 동일한 원본 HD PNG에서 단일 행/버튼 crop을 추가 업로드·생성한다. QA 비교표·서로 다른 자산 콜라주를 원본으로 쓰지 않는다.
5. 브라우저 컨트롤러 방식에서는 메시지 composer에 PNG 실제 바이트를 업로드하고 썸네일과 메시지 입력 첨부 사실을 검증한 다음 ChatGPT 기본 이미지 생성 기능으로 한글화를 요청한다. GitHub 링크/파일 경로/다른 도구에 표시한 그림이나 브라우저 input change 이벤트만으로 이미지가 모델에 전달됐다고 주장하지 않는다. 업로드/이미지 생성 실패 시 SOURCE_REFERENCE_NOT_BOUND 또는 IMAGEGEN_UNAVAILABLE로 보류하고 거짓 성공/생성 ID를 기록하지 않는다.
6. 짧은 생성 프롬프트에는 승인된 한국어 번역, 원본 텍스처의 대상 영문/일본어만 변경, 원본 스타일 최대한 유지, 자동차·로고·제조사/모델명·음악 제목·버튼/배경 보존, 칸 초과·겹침·글자 깨짐 금지를 포함한다.
7. OpenAI Images Edit API는 ChatGPT 기본 이미지 생성과 다르다. 별도 인증·비용이 필요한 실험 경로로 유지하며 사용자 승인 없이 자동 대체하지 않는다.

## PNG 후처리와 시험 DDS
- 생성 직후 원본 PNG 바이너리와 SHA, 승인 번역, HD source SHA, 실제 첨부 근거, 생성 프롬프트·결과를 보관한다.
- 출력 캔버스 크기가 달라도 전체 텍스처를 단순 stretch하거나 생성본의 차량·아이콘까지 덮어쓰지 않는다. 번역한 텍스트/효과를 항목별로 추출하여 원본 HD atlas의 각 UI 칸 좌표로 이동하고 필요하면 **종횡비 유지 contain 축소**한다. 원본 영어 지우기는 검증된 CLEAN/PSD 원본 기반으로 하고, 차량·로고·음악·아이콘·비텍스트 보호 픽셀은 원본 DDS를 보존한다.
- 원본 실제 UI 칸 및 인접 스프라이트·화면 안전 영역 밖 가시 픽셀, 다른 문구·버튼 겹침, 잘림은 0 허용. 원문 영어 글자+효과의 좁은 bbox를 한글이 조금 넘더라도 **원래 실제 UI 칸 안에 들어오고 다른 요소를 침범하지 않는 경우 PASS 가능**. 작은 한국어와 남는 여백은 허용한다.
- RAW/FLIPY 방향을 되돌리고 정확한 DDS 헤더·원래 크기·픽셀포맷·mipmap을 지키며 시험 저장 DDS를 다시 디코딩한다. 원본 보호영역 변경·압축 후 가독성 훼손·형식 오류는 FAIL.

## 간이 QA (A/B 자체 + C1 다중 독립)
강한 FAIL: 오탈자/가짜·깨진 자소, 실제 게임 사용 크기에서 글자 읽힘 불량, 원본 UI 칸 초과·잘림·버튼/HUD 겹침, 눈에 보이는 영문 잔상이나 배경 오염, 자동차/로고/아이콘 등 원본 보호 요소 훼손, DDS 방향·헤더·포맷·mipmap/저장 이미지 깨짐, 사용자 실게임 P0/P1 재현.
허용: 원본과 조금 다른 광택·색감·획·그림자·기울기·자간·정렬, 짧아진 문장/작은 글자/넓은 여백. 스타일 완전 동일, 원문 글자 수·가로폭 비율·정밀 픽셀 유사도를 강제하지 않는다.
- C1은 매회 4~8개의 서로 다른 후보를 한 묶음으로 조회하고 개별 자산마다 원본 DDS SHA/후보 저장 DDS SHA/구체적 오류 좌표/PASS·REWORK·HOLD를 한 표에 기록한다. 새로운 후보 우선, 같은 SHA 재검수 남발 금지.
- 실제 P0/P1/HUD는 자동 일괄 승인하지 않고 개별 위험 확인 후 C3/사용자 실게임으로 넘긴다.
- Producer self-QA, C1 scoped QA, C3, 사용자 실게임 PASS, 정식 승격은 별도 수치. 실제 실행하지 않은 게임의 RUNTIME_VALIDATION=UNTESTED.
- 기존 qa_evidence_gate.py가 아직 역사적 C2 승인 토큰을 요구한다면 임의 C2 PASS로 우회하지 않는다. 새 C1/C3 정책에 맞는 코드 게이트를 별도 검증하기 전에는 TEST_ONLY/HOLD로 유지하며 공식 배포 승격을 주장하지 않는다.

## 컨테이너 정책 백업 및 적용
- 변경 전 기준 정책 HEAD 1d690b771ebb56d319842ce2d1c9096c082c4c79 를 GitHub backup/korean-controller-policy-pre-hd-imagegen-20261012 브랜치로 보존했다.
- Docker/Portainer 실 운영 컨테이너의 app/controller.py, Compose, prompts, 상태 볼륨 및 설치 이미지는 실제 재배포 전에 별도 백업한다. 현 시점 GitHub 정책 수정은 실행 중인 브라우저 탭을 자동 종료하지 않는다. 새 컨트롤러는 활성 A/B/C1 3탭만 구성하고 실제 재배포 뒤 확인한다. VR/FFB/DX11/DXVK는 손대지 않는다.


## 2026-10-12 Work 검토 확정 — v2 / 수동 배포

사용자 13:33 KST 지시 및 첨부 `OUTRUN_IMAGEGEN_WORK_REVIEW_20261012.md` 검토 반영.
이 절은 위 내용 중 같은 항목의 세부 규칙을 보완·대체한다.

### 실제로 사용할 제작 방식

1. 기본 입력은 **동일 읽기 변환을 공유하는 HD 원본 atlas PNG 1장**이다.
   RAW atlas의 개별 sprite가 서로 다른 회전/미러링을 쓰면 문구별 정방향 ROI로 분리한다.
   원본→READABLE→원본 변환과 각 UI cell 좌표를 따로 보관한다.
2. 전체 편집 결과 1장을 받아도 최종 합성에는 검증한 **글자·효과층만** 사용한다.
   자동 추출로 배경/아이콘이 섞이면 실패 문구를 ROI 투명층으로 재생성한다.
   모델이 출력 해상도·알파·픽셀 보존을 정확히 지킨다고 가정하지 않는다.
3. 프롬프트 전문은 `tools/localization/imagegen_prompts/{atlas,roi}.txt`.
   `build_imagegen_prompt.py`로 승인 manifest를 치환하고 전문·템플릿 SHA를 남긴다.
   조립기 성공은 원본 DDS 검증이나 실제 이미지 첨부/생성 성공을 뜻하지 않는다.
4. 브라우저 composer 방식 외에도 내장 편집 도구가 지원하는 실제 파일/첨부 입력은 유효하다.
   실제 입력 연결과 생성 출력 바이트가 확인되어야 한다. 이미지 프리뷰나 URL은 대체 증거가 아니다.
   출력 ID 미노출 시 null을 유지하고 실제 출력 SHA로 식별한다.
5. 검증된 HD 원본/PSD CLEAN을 우선 재사용한다. 새 CLEAN의 독립 검토는 C1이 수행하며
   SOURCE/CLEAN SHA가 같고 새 결함이 없으면 결과를 재사용한다. 폐지한 C2를 다시 호출하지 않는다.
6. 같은 원인으로 두 번 실패하면 문제 ROI/입력을 바꾸거나 HOLD 후 다른 자산을 진행한다.
   기존 후보·승인·큐를 초기화하지 않는다. 유료 API나 옛 폰트 제작으로 자동 대체하지 않는다.

### 완화할 수 없는 실제 게임 경계

- `cell_bbox`는 확인된 sprite/UV·레이아웃 근거로 정한다. 주변 투명 공간을 임의로 셀에 포함하지 않는다.
- 실제 게임 샘플링/필터링 여백이 필요한 경우 이를 안전영역에서 뺀다. 미확인 cell/방향은 HOLD.
- 원본 글자 bbox보다 커져도 검증된 cell 안이면 허용한다. 원본 칸 밖 초과/인접 충돌은 0px.
- 기울기 **방향** 반전은 허용하지 않는다. 작은 각도·광택·색·간격 차이는 허용한다.
- 무손실 합성본은 보호 픽셀이 원본과 일치해야 한다. BC/DXT 저장 후에도 디코딩해 경계 블록,
  alpha, mip를 확인한다. 포맷이 같다고 보존을 추정하거나 임의 오차 허용치를 만들지 않는다.
  인접 보호 아트가 압축으로 훼손되면 별도 블록 보존 방법을 검증하거나 HOLD한다.
- 지원하지 않는 DDS 포맷/mipmap은 `ENCODER_UNSUPPORTED`로 남긴다. 단일 mip로 몰래 축소하지 않는다.
- 부분 문구 PASS는 전체 atlas 번역 완료가 아니다. 전체 대상·완료·남은 항목을 각각 기록한다.

### C1 기록 및 기존 코드 경계

C1은 후보별 source/CLEAN/candidate SHA, producer와 reviewer, 검수 범위/비교판,
구체적인 결함 좌표, `C1_STATIC_PASS`/`REWORK`/`HOLD`를 기록한다.
과거 C1 자신이 제작한 후보는 다른 독립 검수자에게 인계한다.
공유 atlas/P0/P1은 배치 판정 외 개별 확대 및 C3/사용자 재시험을 유지한다.
이 정책 변경은 `qa_evidence_gate.py`와 `production_pixel_guard.py`의 C2/lettering_recipe
consumer 이관 완료가 아니다. 시험 DDS는 기존 role_A/role_B 시험 경로에 남기며,
기존 gate가 거부하면 TEST_ONLY/HOLD로 남긴다. 가짜 C2 PASS, 무조건 승인, 사용자 실게임
OPEN 자동 종료는 금지한다. 정식 승격 전 별도 consumer 코드 이관/검증이 필요하다.

### Docker 적용·배포 구분

- 저장소 정책 적용과 실행 중 컨테이너 배포는 별개다. 이번 작업은 GitHub 파일만 변경한다.
- `deploy_plate_controller.py --stage`는 사용자가 수동 호출할 때만 이미지/프롬프트/Compose를
  준비한다. 기존 Compose의 다른 서비스, 볼륨, 개인 환경설정은 유지하고 원문을 먼저 백업한다.
  같은 이미지 태그가 있어도 탭·스케줄·AUTO_SEND 변경을 저장한다. 재실행은 멱등적이다.
- 2026-10-12 16:39 KST 사용자 지시에 따라 준비된 Compose는 A/B/C1 3슬롯,
  분 0/10/30/40, **AUTO_SEND=true**다. 이전 false 강제 및 별도 수동 활성화 절차를 대체한다.
  컨테이너 배포·재시작은 여전히 사용자가 수동 실행한다.
- 실제 역할 스케줄은 A :00 / C1 :10 / B :30 / C1 :40 (Asia/Seoul)이다.
  3슬롯 round-robin으로 4시점을 순환하면 이 매핑을 보장하지 못한다.
  이 저장소에 운영 `app/controller.py`가 없어 런타임 분→역할 dispatch를 수정/검증하지 않았다.
  `controller_roles.json`만 배포했다고 runtime이 이를 읽는다고 주장하지 않는다.
  런타임 지원은 미검증이며, 수동 배포 후 실제 분→역할 실행 로그와 단건 결과를 확인한다.
- C2 프롬프트는 준비 이미지에서 제거한다. 실제 브라우저 C2 탭 정리는 사용자가 배포 후 확인한다.
- 컨테이너 재시작/Portainer 재배포, 게임 설치·릴리스는 모두 **사용자 수동**.
- 실제 업로드→기본 이미지 생성→결과 다운로드→DDS 변환은 현재 `E2E_UNVERIFIED`.
  자동화 완성이나 신규 DDS 생산으로 계산하지 않는다. 런타임은 `UNTESTED`.

수동 절차: `docker/localization-production/MANUAL_IMAGEGEN_ROLLOUT.md`.

## 2026-10-12 PNG 첨부 컨트롤러 GitHub 구현 보완 (운영 배포 아님)

사용자 PNG 자동 첨부 요청으로 `tools/localization/controller_png_attach.py`와
`patch_controller_png_upload.py`가 신규 추가되었다. 수동 `--stage`에서만 기존
기본 Docker 이미지의 `controller.py`에 변경을 적용한다. A/B는 `/data/imagegen/`
입력 manifest + 실제 SHA 일치 PNG + 승인 문구를 필요로 하며, 첨부 프리뷰를 확인한
경우에만 메시지를 전송한다. 실패 시 텍스트만 전송하는 fallback은 금지한다.
이미 전송한 TASK_ID는 `sent/` 기록으로 중복 방지한다.
C1은 별도 QA, C2 기록은 백업 후 신규 탭을 제외한다. 스케줄 패치는
A :00/C1 :10/B :30/C1 :40으로 3슬롯이다.
소스 기본 이미지에 적용한 정적 패치 구문/멱등성 및 격리 테스트는 통과했으나,
운영 Portainer 수동 배포, ChatGPT 실첨부 성공, 생성 후 PNG 다운로드, DDS 연결,
게임 실기 검증은 여전히 **UNTESTED**다.
자세한 준비·입력 방법은 `docs/KOREAN_LOCALIZATION_CONTROLLER_PNG_UPLOAD_20261012.md` 참조.
사용자가 별도 명시한 `AUTO_SEND=true` staging 설정은 그대로 유지하되
입력이 없으면 A/B는 FAIL-CLOSED 처리한다.
