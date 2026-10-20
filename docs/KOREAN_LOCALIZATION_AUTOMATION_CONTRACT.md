## 2026-10-19 사용자 명시 재개 — 원본 HD ROI 기반 한글 ImageGen + C1 QA 자동화

2026-10-19 사용자가 한글화 정책을 다시 확인한 뒤 **한글화 자동 실행 재개를 명시적으로 승인**했다. 이 항목은 2026-10-16/17의 A/B/C1 브라우저 자동화 중지 지시를 아래 범위에 한해 대체한다.

- 운영 구조는 기존 Portainer Git Stack `outrun-kor`의 **단일 컨테이너**다. Chrome은 A/B/C1 3개 영속 탭만 사용한다. C는 브라우저 탭이 아니라 같은 컨테이너의 N100 원본 HD 영문 크롭 백그라운드 worker다.
- C는 검증된 unsplit/native 전체 HD PNG에서 번역 대상 영문/일문 원본 픽셀을 **문구별 coverage가 100%가 될 때까지 계속 추출**한다. 원본 1장을 한 번 OCR했다는 이유로 완료 처리하지 않으며, 해당 원본의 `transcribed_reviewed` 문구 중 crop manifest가 없는 항목이 하나라도 있으면 재스캔 대상으로 남긴다. OCR은 승인된 다중 전처리/PSM 전략을 순환하고, 짧은 영문·일본어·아이콘 placeholder 주변 실제 텍스트도 coverage에 포함한다. edge 후보는 단계적 여백 확장 후 최대 컨텍스트/C1 필수검수 후보로 넘겨 영구 HOLD를 만들지 않는다. **문구 backlog와 edge backlog가 모두 0일 때만 C crop 완료**로 본다. 과거 986개 분할 타일·타일 재조립본·기존 생성 한글 이미지는 신규 입력으로 금지한다.
- 새 bridge는 C crop의 source PNG SHA, 원본 DDS SHA, crop SHA, XYXY, edge 상태를 확인하고 `transcriptions.jsonl`의 `transcribed_reviewed` 영문→한글이 정확히 하나 일치할 때만 A/B ImageGen 큐에 등록한다. 불명확·중복은 HOLD/skip한다. `ALPHA_TOUCHES_CROP_BORDER_REVIEW` 후보는 원본 SHA를 다시 확인한 뒤 별도 안전 여백 확장 재크롭을 수행하며, 확장 경계 검사를 통과한 새 sibling crop만 신규 큐에 등록한다.
- A/B는 등록된 실제 PNG를 ChatGPT 프로젝트 **아웃런 한글화 신규**에 바이너리 첨부하고, ChatGPT native ImageGen으로 한글 글자/효과 PNG를 생성한다. 최초 배정은 A=홀수/B=짝수지만 **이미 완료되었거나 진행 중인 배치의 ownership/ordinal은 절대 바꾸지 않는다. B가 자기 기존 큐를 소진하면 A의 미착수 ROI만 절반씩 B 큐 끝에 append하여 남은 작업량을 균등화**한다. 이후 edge-salvage 등 신규 ROI는 양쪽 미완료 잔량이 적은 쪽에 배정한다. 한 번에 1~5개만 처리한다. **다음 배치 진행의 필수 생산 게이트는 실제 생성물 수량 확인 + N100 로컬 후보 PNG 전부 저장 + task/role/output filename/파일 바이트 SHA256 재검증**이다. Project Library SHA 확인은 보조 증빙으로 유지하되 UI 지연·미저장 때문에 A/B 생산 큐를 막지 않는다. 로컬 후보는 계속 미승인/C1 QA 대기이며 DDS/실게임 PASS를 뜻하지 않는다.
- 브라우저 예약은 Asia/Seoul 기준 **A `:00/:20/:40`, B `:10/:30/:50`, C1(사용자 표기 C) `:15/:45`**. C native crop/queue bridge는 컨테이너 내부에서 60초 폴링한다.
- C1은 A/B 생성물을 4~8개 범위(적으면 있는 만큼) 독립 간이 QA한다. C1은 ImageGen 생산, A/B 큐 소비, DDS 최종 작성, C2/C3/실게임 PASS 생성을 하지 않는다. C2 탭은 계속 폐지한다.
- 자동 범위는 **원본 crop → 번역 매칭 → A/B ImageGen → 생성 PNG 저장/증빙 → C1 간이 QA**까지다. DDS 최종 합성/승인, 게임 파일 배포, C3, 사용자 실게임 PASS, Unicode 런타임 출시 게이트는 별도이며 자동 승인하지 않는다.
- 기존 F0~F4는 품질 확대 단계/인수 기준으로 유지한다. 현재 컨트롤러의 `F2` 표기는 자동 생산의 작업 범위 라벨일 뿐 F0/F1/F2 실게임 PASS를 새로 주장하는 증거가 아니다.
- Docker 자동 전송 활성화는 사용자 수동 Portainer Pull and redeploy 이후 적용한다. VR/FFB/DX11/DXVK 프로젝트·스택은 절대 변경하지 않는다.

정본 구현: controller branch `localization-controller-recovery-20260928`의 `docker-compose.yml`, `crop_to_imagegen_queue.py`, `text_roi_queue.py`, `patch_controller_c1_slot.py`, `v2_automation_policy.py`.

---

## 2026-10-17 사용자 명시 변경 — ChatGPT 예약 대신 C 전용 Docker 원본 영문 크롭

2026-10-16의 전체 한글화 정지 정책 중 **검증된 원본 HD 영어 문구 네이티브 크롭 C 단독 작업만** 독립 N100 Docker에서 재개한다. 기존 A/B/C1/ChatGPT 컨트롤러와 이미지 생성·합성·DDS/VR은 정지 유지. 현재 실행 범위/검증/HOLD 및 중복 방지 규정은 `docs/OUTRUN_C_N100_ORIGINAL_CROP_ONLY_20261016.md`의 2026-10-17 추가 규정과 `docker/c-original-english-crop/README.md`를 따른다. 신규 검증 스펙이 없으면 IDLE이며 자동 문구 발견 성공을 주장하지 않는다.

---

## 2026-10-17 00:10 KST 사용자 최우선 변경 — C 원본 영문 HD 글자 크롭 예약만 재개

사용자가 **C의 영문 원본 HD 글자/문구 픽셀 크롭만** 반복 자동 작업으로 명시 승인했다. 2026-10-16 전체 자동 중지 규칙은 **이 C 작업에 한해서만** 부분 해제한다. 기존 ChatGPT 예약 작업(`6ad160ee3a2c81918f7afe2b99ad29cd`)을 매시 03분 KST 실행으로 사용하며 별도 타이머를 중복 생성하지 않는다. 255개 기존 추출 결과를 보존하고 SHA·DDS 원본 동등성과 전체 HD 출처가 입증된 신규 영어 문구만 1회당 최대 1개 자른다. 원문 RGB/RGBA 픽셀·좌표·원본 해시 보존, 품질 상태는 TEST_ONLY. 불확실한 입력은 HOLD. 기존 A/B/C1 ImageGen, 브라우저, 포테이너, CLEAN, 확대, 한글 합성, DDS 및 VR은 재개 승인되지 않았다. 상세 정본: [OUTRUN_C_N100_ORIGINAL_CROP_ONLY_20261016.md](OUTRUN_C_N100_ORIGINAL_CROP_ONLY_20261016.md).

---

## 2026-10-16 사용자 최우선 지시 — 모든 한글화 자동 작업 정지, C는 N100 원본 HD 글자 크롭만

A/B/C/C1 자동 생성·전송·재조립·합성 작업은 정지. C의 향후 작업은 N100 원본 전체 HD PNG에서 영어 문구의 원래 픽셀만 네이티브 크롭(원본 좌표/SHA 보존)하는 것으로 완전히 변경한다. **과거 C ImageGen 확대 참조 생성, ROI ImageGen 입력 제작, CLEAN, 한글 합성, 986 타일 활용 전부 금지.** 새 자동 작업 재시작·Portainer 배포는 사용자 명시 승인 전 금지. 전체 세부 규정은 [OUTRUN_C_N100_ORIGINAL_CROP_ONLY_20261016.md](OUTRUN_C_N100_ORIGINAL_CROP_ONLY_20261016.md). 기존 파일과 A/B 상태는 보존.

---

## 2026-10-15 사용자 최신 변경 — 분할 타일 폐기, 한 문구 단위 ROI 이미지 생성

**최우선:** [OUTRUN_TEXT_ROI_IMAGEGEN_20261015.md](OUTRUN_TEXT_ROI_IMAGEGEN_20261015.md). 기존 986 균등 타일은 신규 A/B 생성 입력에서 사용 금지. 검증된 HD 전체 원본에서 각 글자 문구와 윤곽/그림자 전체를 잘림 없이 한 번에 크롭한 RGBA PNG만 사용하며, 2~4배 확대 참조를 ImageGen으로 개별 한글화한다. 해상도 및 경미한 스타일 차이는 허용하나 글자 잘림·가짜 한글·원래 UI/UV 안전영역 침범·배경 훼손은 금지. 전체 원본 없이 예전 타일 한 장만 사용하는 작업 금지. C-SALVAGE의 예전 분할원본 재조립·A/B 타일 합성은 과거 작업 증빙으로만 보관. 새 입력 ROI 실물/승인 증빙 및 독립 A/B 상태 전환 없이 이전 타일 큐를 새 작업처럼 계속 전송 금지. Portainer 배포는 사용자 수동, A/B 기존 파일·큐 데이터는 삭제하지 않음. C1/C3/실게임 승인 구분, RUNTIME_VALIDATION=UNTESTED 유지.

---

## 2026-10-15 C-SALVAGE 오프라인 자동화 추가 — 운영 배포는 사용자 수동

신규 생산자 `C`는 ChatGPT ImageGen을 호출하지 않는 **별도 오프라인 파일 복구 작업자**이다. 기존 A/B 브라우저 생산과 C1 독립 QA **3탭/분별 dispatch는 변경하지 않는다**. C2도 재활성화하지 않는다.

- 실행 코드: `tools/localization/c_salvage_worker.py`, `c_salvage_plate.py`, `c_salvage_compose.py`; SHA 고정 입력/중복방지, PSD 우선 검색 및 선택 레이어를 사용한 CLEAN 후보, PSD 부재 시 검수된 영문 제거 마스크와 정본 HD DDS 기반 투명 배경 CLEAN, 읽기 방향 좌표 합성, 지원 BGRA32 단일 mip 시험 DDS. 불투명 배경·불명확한 마스크·비지원 DDS 압축·이미지 원본 부재는 HOLD 처리.
- Portainer 추가 서비스는 `docker/localization-production/portainer-git-c-salvage.override.yml`이며 독립 볼륨 입력 read-only/출력 rw, 자체 네트워크 없음, CPU 제한, **사용자가 기존 Git 기반 Stack 확인 후 수동 Pull and redeploy한 때부터 30분/최대 10개 자동 실행**. GitHub commit이나 GitHub 테스트 워크플로 자체는 배포가 아니다.
- 기존 사용자 A/B 이미지 출력 변경·게임 패치 적용·QA 상태 자동 승격·ImageGen 추가 시도 금지. C가 산출한 레이어/플레이트/중간 DDS는 `TEST_ONLY`; 독립 C1 및 고위험 C3, 사용자 실게임까지 분리.
- 정확한 준비·배포·검증 지침: `docs/OUTRUN_C_SALVAGE_AUTOMATION_MANUAL_DEPLOY_20261015.md`.
- 실제 Portainer build/redeploy와 live DDS·실기 전체 체인은 검증 전까지 `UNTESTED`.

---

## 2026-10-13 11:03 KST 사용자 운영 경로 확정: Portainer ← GitHub

운영 Docker lifecycle은 Portainer가 관리하며 GitHub가 정책 정본이다. q217 단건 A 이미지 생성 smoke의 최신 전달 정본은 `docs/OUTRUN_PORTAINER_GITHUB_DELIVERY_20261013.md`. 기존 Git 연결 Stack인 경우 Portainer의 지정 Git repository/ref/Compose path가 실제 반영 경로이며 사용자가 **Portainer에서 수동 Pull and redeploy** 한다. 기존 `deploy_plate_controller.py --stage`는 레거시 비Git Stack 지원 수단일 뿐 이 경로의 필수 단계로 제시하지 않는다. 현 브랜치의 Portainer base Compose와 사용 중 이미지/입력 PNG 자동 공급이 확인되지 않았으므로 GitHub 정책 commit만으로 live 이미지 첨부·ImageGen이 작동한다고 주장하지 않는다. 단건 Compose override는 기존 Git Stack에만 선택 적용하며 다른 Stack·볼륨/서비스/이미지를 훼손하지 않는다. 실제 upload/generation/DDS/game은 증거 전까지 UNTESTED. Portainer 자동 GitOps 재배포는 사용자 수동 배포 승인과 별개다.

---

## 2026-10-13 q217 A 단건 ChatGPT PNG/이미지 생성 실험 — 수동 Docker 배포

사용자 최신 단건 시험 지시: `docs/OUTRUN_A_Q217_IMAGEGEN_SMOKE_20261013.md` 및 `--single-a-smoke` 스테이징을 사용한다. 이 모드는 기존 A/B/C1 정상 자동화 규칙을 영구 대체하지 않는 **명시적·임시 단건 모드**다. A q217의 해시 지정 PNG와 TASK_ID 하나만 송신, B/C1 스케줄 및 모든 watchdog 전송 차단, `AUTO_SEND=true` 유지, 중복 송신 차단. GitHub 변경 자체는 컨테이너 배포가 아니다. Portainer 스테이징·재배포·복원은 사용자 수동. 라이브 ChatGPT 첨부·이미지 생성·결과 PNG·DDS/게임 실기 성공은 각각 실제 증거가 생기기 전까지 UNTESTED.

---

# Korean Localization Automation Contract

## 2026-10-12 16:39 KST 사용자 수정: AUTO_SEND=true

도커 준비 설정의 자동 전송 기본값은 `true`다. 이전 AUTO_SEND=false 강제 및 별도 수동 활성화 지시는 대체한다. 컨테이너 배포·재시작은 계속 사용자 수동이며, 설정 변경은 운영/E2E 검증 통과를 의미하지 않는다.

## 2026-10-12 13:33 KST 재시작 정책 — 현행 규칙 우선

현행 정본은 `docs/KOREAN_LOCALIZATION_HD_PNG_IMAGEGEN_AND_FAST_QA_20261012.md`와
`localization/controller_roles.json`이다. A/B=HD 원본 기반 내장 이미지 생성,
C1=4~8개 독립 QA, C2=폐지. 전체 atlas 입력 허용, 혼합 방향은 sprite별 정방향 ROI.
검수 경계는 검증된 실제 UI cell/UV 안전영역이며 옛 영문 효과 bbox 상한은 대체한다.
**도커 배포·재시작·자동 전송 활성화·게임 패치 배포는 사용자가 수동 실행한다.**
아래 과거 지시 중 A 폰트 생산/C1 생산/C2 신규 승인/유료 API 자동 대체/옛 bbox 규칙은
역사적 참고일 뿐 실행 지시가 아니다. 원본 보호·CLEAN·한글 정확성·저장 DDS 무결성·
실게임 불량 OPEN은 유지한다. 기존 코드의 C2/lettering_recipe gate를 우회하지 않는다.
새 C1 판정은 별도 기록하며 미이관 consumer는 TEST_ONLY/HOLD로 명시한다.

---

## 2026-10-12 USER OVERRIDE: A/B HD original DDS→READABLE PNG→native ChatGPT ImageGen; C1 batch QA; NO C2 TAB

**APPLY FIRST**: docs/KOREAN_LOCALIZATION_HD_PNG_IMAGEGEN_AND_FAST_QA_20261012.md. This later user policy supersedes older A native font/vector production, B/C1 mod4 generation split, C1 production, C2 active independent QA/tab/schedule and single-glyph-only input restrictions. A owns odd HD-source ImageGen; B owns even HD-source ImageGen; C1 performs independent lightweight batch QA for 4–8 saved DDS candidates per run, no generation; C2 is retired (historic evidence preserved, no tab). Actual HD DDS READABLE PNG upload in ChatGPT message is mandatory, not just a GitHub display. Restore original UI cell coordinates and preserved nontext pixels, original DDS format/mips/orientation. FAIL unreadable/misspelled Hangul, UI cell overflow/clipping/collisions, protected damage and corrupted saved DDS; ACCEPT minor style/space differences. Do not fake legacy C2 approval or actual user game pass; unresolved legacy approval gate needs explicit migration. RUNTIME_VALIDATION=UNTESTED unless tested.

---

## 2026-10-12 source-PNG real multipart attachment bridge

The ChatGPT native image generator cannot see GitHub/tool-result images as edit inputs; the controlled tool call returned **generation not started**. A tool-displayed image is **not** source attachment. To establish a real binary source attachment for B/C1, use [KOREAN_LOCALIZATION_IMAGEGEN_MULTIPART_BRIDGE.md](KOREAN_LOCALIZATION_IMAGEGEN_MULTIPART_BRIDGE.md): the separate OpenAI Images Edit API client sends SHA-pinned English-only transparent PNG as actual multipart `image` bytes and requires a server response request ID before recording a binding receipt. This is an experimental **GPT Image API**, not a successful native ChatGPT `image_gen.text2im` invocation. It requires an encrypted `OPENAI_API_KEY` Actions secret; without it, HOLD and zero output. Only RAW UNREVIEWED generated PNG may be stored until independent exact-source CLEAN and C2/C3/game gates. A/B/C1 queue ownership and original runtime rules stay unchanged.

## 2026-10-12 source-first throughput optimization (additive)

Apply [KOREAN_LOCALIZATION_THROUGHPUT_OPTIMIZATION_20261012.md](KOREAN_LOCALIZATION_THROUGHPUT_OPTIMIZATION_20261012.md) before A/B/C1 production or C2 triage: reuse SHA-bound SOURCE/CLEAN, prove actual English glyph-only ImageGen attachment before generation, preserve aspect ratio in every PNG-to-DDS fit, distinguish region-only static PASS from full-asset/C3/user acceptance, and stop repeated same-method retries. OPEN_USER_INGAME_FAIL statuses with any appended QA suffix remain mandatory export vetoes. Existing lane ownership, approval gates and game retest requirements are unchanged.

## 2026-10-12 B/C1 input correction (latest user request)

Before every B/C1 real ImageGen call, **require actual attached English lettering-only transparent RGBA media**, separately cropped from SHA-verified mirrored PSD letter/effect layers or, when not separable, isolated native PSD transparent composite / canonical DDS glyph-only ROI. A full game image, UI screenshot, menu screenshot, multi-label sheet, generator prompt alone, file path or a different tool's image display is **not** valid generator input. Preflight shall record reference file SHA/ROI/PSD source and actual attachment evidence, otherwise `SOURCE_REFERENCE_NOT_BOUND` HOLD and **no generation call**. Full game/menu/car outputs are `NON_GLYPH_SCENE_OUTPUT` and do not count as Korean lettering or DDS. See `docs/KOREAN_LOCALIZATION_IMAGEGEN_PROMPT_GUIDE.md`; keep C2 PLATE_PASS, native DDS, protected pixels, C3 and in-game unchanged. q092 English-only PSD source reference under `role_B/source_references/q092_20261012` is prepared but not C2-approved or proven bound to the generator.

# Korean Localization Automation Contract

## 2026-10-11 QA 수렴·실게임 시험 분리 정책 (최신 사용자 결정)

**모든 생산/검수 레인 공통 적용:** [KOREAN_LOCALIZATION_QA_THROUGHPUT_POLICY.md](KOREAN_LOCALIZATION_QA_THROUGHPUT_POLICY.md)를 최신 QA 판정의 정본으로 먼저 읽는다. 기존 문서에서 **경미한 원본 서체/효과 차이, 완벽하지 않은 금속 광택, 미세한 각도·자간 차이, 과거 미관만의 HOLD**를 자동 재작업으로 표시하던 지시는 이 정책으로 대체한다. C2는 저장 DDS에서 실제 읽히는 글자·보호 픽셀·CLEAN·RAW/FLIP-Y를 독립 확인하고, 구체적 시각 결함이 없으면 `COSMETIC_VARIANCE_ACCEPTED`와 정적 QA PASS를 검토한다. 없는 결함을 추측하거나 같은 SHA를 반복 재생산하지 않는다.

**하드 게이트 유지:** 오자/가짜 자소/잘림/가독성 불량/원문 효과 bbox 1px 침범/다른 UI 충돌/영어 잔상/플레이트 손상/저장 DDS 압축 훼손/사용자 실게임 FAIL은 계속 차단한다. `TEST_ONLY_ELIGIBLE` 및 `C3_LIGHT_REVIEW_TEST_ONLY`는 격리 시험용 판단이며 `C2_PASS`, `C3_STRICT_PASS`, `qa_evidence_gate.py` 승인·배포, 실게임 PASS를 자동 생성하지 않는다. 고위험 P0/P1 및 공유 HUD는 C3 엄격검수를 유지하고, 사용자가 실제 게임에서 확인하기 전 `RUNTIME_VALIDATION=UNTESTED` 및 OPEN을 유지한다. 기존 A/B/C1/C2 역할·작업 소유권·일정은 불변.


## 2026-10-11 전 레인 글자별 크기 검수 규칙 (최신 사용자 지시)

**적용 대상:** A/B/C1 제작·자체 QA, C2 독립 최종 QA, C3 엄격 QA, CLEAN 이후 렌더·저장 DDS 시각검수, PRE_INGAME 및 재작업 판정 전부. 원문과 번역의 언어/글자 수가 다르다는 이유로 한글 문장 전체 가로세로 비율·폭 점유율·영문 픽셀 면적/실루엣 일치율이 다르게 나온다는 것은 **반려 사유가 아니다**. 이 지시가 과거의 "undersized/underfill/원문 길이·폭에 비례/가능한 크게" 문구보다 우선한다. 자세한 단일 정본은 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`.

**판정:** 원문 개별 텍스트/줄의 정확한 글자+효과 bbox를 넘는 한글 픽셀은 1px도 허용하지 않는다. 그 안에서는 한글이 원문보다 더 좁거나 작아도 허용하고, 원문 총 문장 길이나 글자 개수/캔버스 비율을 맞추기 위해 확대하거나 가로 늘이지 않는다. 비교 대상은 실제 한글 **글자 하나하나**의 네이티브 높이/획 굵기/받침·내부 공간/윤곽·효과·가독성과 UI 계열의 대표 원문 글자 크기·위계이다. 영문과 한글 글자 수가 달라 1:1 대응시킬 수 없으므로 'n번째 영문 글자 = n번째 한글 글자' 강제 매칭도 금지한다. 번역이 더 짧은 **그 사실 자체는 PASS** 처리한다.

**반려 가능 조건:** 원문 bbox 초과, 겹침·보호 아트 변경·잘림, 한글 오탈자/획 손상/실제 읽히지 않음, 명백한 서체·기울기·효과 오류는 각각 구체적 원인과 실제 픽셀 증거가 있을 때만 FAIL. 기존 `UNDERFILL`/`SOURCE_WIDTH_RATIO`/`WIDTH_RATIO`/`WHOLE_SENTENCE_ASPECT`만 근거인 REWORK는 현행 글자별 시각검수에서 **크기 조건 PASS로 재분류**하고 나머지 QA 통과를 확인한 뒤 정상 C2/C3 경로로 진행한다. 미검수 자료를 근거 없이 전체 승인으로 바꾸거나 사용자 실게임 OPEN을 닫지 않는다. `RUNTIME_VALIDATION=UNTESTED` 유지.


## ImageGen prompt authoring — 2026-10-11

B and C1 MUST read and apply `docs/KOREAN_LOCALIZATION_IMAGEGEN_PROMPT_GUIDE.md` before each new/edit image-generation call. Build an asset-specific visual specification from the exact readable source crop; separate generator instructions from QA/commit metadata, preserve exact call inputs, and use failure-specific revisions. This is prompt policy, not a new queue or QA approval. A, ownership, CLEAN prerequisites and independent C2/C3/game gates remain unchanged.


## B+C1 ImageGen production override — 2026-10-11 (latest user decision)
A remains the existing odd-index font/vector/manual production lane. B and C1 are independent **ChatGPT real image-generation production + producer self-QA** lanes, NOT final-QA-only workers. B takes *new* even queue indexes where index % 4 == 0; C1 takes *new* even indexes where index % 4 == 2. Existing in-flight explicit assignments are preserved and must not be overwritten: skip any candidate already actively owned by another lane at the latest Git HEAD; preserve P0/P1 explicit lane owners until safely transferred with recorded evidence. C2 alone independently reviews ALL odd/even A/B/C1 products, special unindexed C work, CLEAN/plate and final QA; C3 and actual user game tests remain separate. This replaces all earlier C1=odd QA/C2=even QA statements and all B-only imagegen restrictions in older sections of this contract and other documents.
B and C1 MUST read `docs/KOREAN_LOCALIZATION_B_IMAGEGEN_LANE.md` and call the real ChatGPT image generator for actual transparent Korean text PNG. A is NOT changed. The same exact-source/CLEAN/plate-review/0-pixel-overflow/native DDS/visual/source-style evidence guards apply to both. ImageGen is not available inside plain GitHub Actions or Pillow, and cannot be fabricated or silently replaced by font/vector fallback. On missing tool/output/upload, record truthful IMAGEGEN_UNAVAILABLE/OUTPUT_MISSING without false production or approval. Use the existing asset_queue.csv (no new job queue); C1 writes under role_C1 with schema outrun-c1-imagegen-v1. C2 provides independent PLATE_PASS and final evaluation for all three producers; producers NEVER self-approve C2/C3/game. Keep A :00, C1 :10/:40, C2 :20/:50 and B :30 until user explicitly changes the schedule.


## Separated lettering engine — 2026-10-11

Apply `docs/KOREAN_LOCALIZATION_LETTERING_ENGINE.md` for A's native/vector lettering only; B/C1 real ImageGen production takes priority for their new text. Review native glyph geometry before effects, preserve separate face/effect layers and compose through `compose_lettering.py`. Newly published production DDS require a SHA-bound `lettering_recipe` in the final manifest; the existing changed-candidate gate verifies the actual composition. Producer geometry readiness is not C/C3/game approval. Keep existing scheduling and ownership.

## Shared PSD/CLEAN engine — 2026-10-11

A/B and C1/C2/C3 MUST apply `docs/KOREAN_LOCALIZATION_PLATE_LIBRARY.md`.
Lookup exact reusable plates before reconstruction; qualify PSD layers against the
canonical DDS, bind C plate review independently, and retain final DDS/C3/game gates.
The library and controller prompts are production inputs, not a new queue.


## Production reset: qualify the method before multiplying candidates — 2026-10-09

Read and apply `docs/KOREAN_LOCALIZATION_PRODUCTION_RESET.md` before A/B/C1 production
and fresh C2 review. Its stage prerequisites override throughput/same-invocation
recommendations when they conflict: one unqualified family pilot at a time,
source-derived CLEAN before lettering, pinned reusable font/effect recipes,
readable-coordinate slant anchors, and exact persisted-DDS mechanical checks.
New/changed hd_candidates require a final manifest and
`production_pixel_guard.py --changed-since BASE_SHA` before publication.
CPU-worker publication enforces this; direct-push CI detects violations without
claiming automatic rollback or branch protection. Mechanical PASS is never
visual/C/C3/game approval. Preserve unchanged candidates and independent lanes.


## External retro-localization skill adoption: consumer-chain and playtest coverage — 2026-10-09

Read and apply `docs/KOREAN_LOCALIZATION_END_TO_END_PLAYTEST_GATE.md` whenever a new/materially revised DDS, font/runtime text, in-game regression, C/C3 review, or user preview build involves an in-game consumer. It requires exact source-to-persisted-byte-to-screen traceability, multi-screen shared-atlas impact checks, explicit untested runtime links, and reproducible user playtest routes. Existing A/B/C/C3 ownership, queue/evidence SSOT, ten-stage visual construction, 1-pixel rules, preview exclusion, and user-only in-game closure remain unchanged. Do not import ROM-console tooling or add new queues.

> Recovery baseline: 2026-09-28 10:12 KST (`11631c5f12037bcd01cda1af57ec9bc564af4bcf`). Keep this branch intentionally small and production-focused. Do not import later controller schemas, event-ID layers, queue engines, or VR/FFB rules unless separately proven necessary.

This is the canonical contract for the A/B/C localization controller. Every run MUST read this file first, then docs/KOREAN_LOCALIZATION.md, docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md, localization/WORKLOG.md, localization/progress/progress.json, localization/resume_state.json, localization/graphics/README.md, localization/graphics/ORIENTATION_POLICY.md, localization/graphics/TRANSLATION_NAMING_POLICY.md and localization/graphics/INGAME_REWORK_BACKLOG.csv. Repository state on korean-localization-recovery-20260928 is the only work state; do not use GPT Library as a work store.

## In-game regression hard stop — 2026-10-09

The new user-marked actual-game review (screenshots 173–203) overrides
all previous static C/C3 PASS verdicts on affected exact candidate bytes.
For every report, register a row in INGAME_REWORK_BACKLOG.csv, connect the
unambiguous queue index, and make that row REWORK_REQUIRED even if it was
historical C3 PASS. Keep uncertain MIXED/RUNTIME_TEXT source mapping OPEN
rather than editing arbitrary DDS. An open user report cannot be closed
by static C, C3 or screenshot JPG; require a newer game retest containing
the exact repaired DDS/runtime commit.

The black outlines drawn on screenshots are **annotations**; only
independently observed pixels are intrinsic background/box defects. The
reported actual plate contamination, degraded tiny Hangul, unreadable
glyphs, wrong lean, clipped headers, collision of Stage 2 text and rank
HUD, duplicated/overlapping text, and bad protected-art orientation
are hard failures regardless of zero mask-overflow metrics.

Before producing related assets, calibrate native-HUD, big chrome
header, italic main title, small showroom/help and stage/rank families
separately. Require a clean source plate approved *before* lettering,
transparent-only lettering, source-specific slant anchors, persisted DDS
RAW/FLIP-Y/mips/native/75/50 checks, and a game-composed review. Never
upscale earlier low-resolution Hangul, use an arbitrary shear/scale to
force PASS, or let source glyph remnants hide beneath new Korean glyphs.
User P0 (HUD, stage overlap, broken/glitched glyph) precedes P1
(menu/title and showroom metadata) within the existing owner lanes.

See docs/KOREAN_LOCALIZATION_INGAME_REVIEW_20261009.md; preserve the
existing six-launch scheduler, C/C3 evidence gate, and VR/FFB/DX11/DXVK
exclusions. Preview packaging must suppress active user-failed queue
indexes even if stale C3 metadata remains.

## Mandatory production contamination prevention — 2026-10-08

Every A/B localization run MUST apply the **10-stage producer sequence** in
`docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md` to every new/materially revised
DDS. This supplements, never replaces, the existing eight ordered visual
checks, source-size/bbox ceiling, zero overlap, exact orientation and C/C3 gates.

- **Before lettering:** identify exact SHA-pinned English source and protected
  source effects; reconstruct CLEAN_PLATE and **independently QA SOURCE vs CLEAN**
  with no Korean lettering hiding the result. English remnants, glyph shadows,
  bright/dark ghosts, damaged background, alpha discontinuity, donor seam,
  rectangular patched areas or source-shaped residuals are producer FAIL.
- **At composition:** render Korean at the actual source resolution from an
  English source-derived UI-family type/effect profile. Use a transparent glyph
  mask plus only justified source-family effects over CLEAN; never paste opaque
  or semitransparent background rectangles with letter crops. A clean editing
  rectangle is not intrinsically bad; a visible changed plate/edge is bad.
- **After composition:** independently QA **CLEAN vs FINAL** for visible
  box-edge traces, extra artwork, shifted background patches, glow/stroke
  residue, changes outside justified effect masks and protected-layer
  intrusions. Also compare SOURCE vs FINAL for font hierarchy/style. A/B must
  preserve lossless plate-only and composite-only proof, masks and decoded DDS.
  Zero bbox violations cannot overrule a visually dirty final.
- **After DDS encode:** visually inspect native decoded persisted-DDS bytes,
  RAW/FLIP-Y, all authored MIPs, full/practical 75/50-percent previews, glyph
  integrity, style match and protected-art isolation; fail any 1-pixel escape.
- **Reason codes:** use `SOURCE_RESIDUE_UNDER_KOREAN`,
  `INCOMPLETE_CLEAN_PLATE`, `FOREIGN_BOX_ARTIFACT`,
  `BACKGROUND_PATCH_INTRUSION`, and `RECTANGULAR_COMPOSITE_TRACE` to
  distinguish background/removal/composite defects in per-asset QA. Confirmed
  visual defect => `REWORK_REQUIRED` or `MANUAL_RECONSTRUCTION_REQUIRED`;
  missing exact-byte/plate proof => `HOLD_STRICT_RECHECK`. Never add false
  PASS evidence.
- **Family first:** establish a source-derived profile for each flat/menu/help,
  italic/selector, chrome/metallic family and independently review ONE
  representative persisted candidate before applying that method across
  multiple DDS. q172/q214 bevel failures and q175/q219 chrome/style failures
  must not be addressed by repeated width-only, flat, shear-only, or arbitrary
  bevel/shadow overlays. If two independent C rejections share an evidenced
  root cause, use the existing `METHOD_CHANGE_REQUIRED` triage and switch to
  actual source-conditioned or manual/vector construction. No new queue engine.
- **User validation before final approval:** the separate
  `USER_REVIEW_NOT_APPROVED` build may include clearly marked historical-C3
  current candidates with SHA-pinned manifests for actual user testing.
  This is NOT `PRE_INGAME_JPG_REVIEW` final approved export and must never
  declare current `qa_evidence_gate.py` PASS, user acceptance or
  `RUNTIME_VALIDATION=PASS`. The evidence-approved package remains
  independently fail-closed. The user may report a new in-game defect and
  reopen the exact DDS even after past C/C3 PASS.
- **Producer handoff and performance:** account for source removal, plate
  QA, source-family profile, exact candidate SHA, composite-only/RAW/mip
  evidence and root-cause codes before marking producer PASS. Count genuinely
  new/revised candidate DDS, first-pass independent C acceptance, defect
  recurrence, final evidence approvals and user in-game closures separately.
  Repeated same-SHA inspection and new evidence alone do not count as new DDS.

Current roles: A/B/C1 do production/self-QA; C2 performs independent final QA across all producer shards. C3 remains additional strict QA, and only the user's actual-game evidence can close a user-reported in-game regression.

## Rework convergence selection guard — 2026-10-08

Before each A/B/C1 production selection and C2 evidence selection, read `docs/KOREAN_LOCALIZATION_REWORK_CONVERGENCE.md`, refresh the Git queue, and run `python tools/localization/rework_triage.py --index N` on the selected asset. Use `--require-safe-rerender` before ordinary same-method DDS rerender attempts; a nonzero result prevents blind rerender, not genuine corrective reconstruction. Do not use this read-only triage as visual QA or approval.

- `EVIDENCE_ONLY_HOLD` / `FRESH_C_REVIEW` / `VALIDATION_ONLY`: preserve the current candidate bytes, gather the missing independent evidence or actual-game retest, and do not use A/B throughput to reproduce an unchanged DDS without a newly verified pixel defect.
- `MATERIAL_REWORK`: repair the specific confirmed visual failure against the canonical native English source and measured UI-family style.
- `METHOD_CHANGE_REQUIRED`: repeated independently evidenced source-family rejection requires a documented new reconstruction method and source-derived font/plate/style reference before producer PASS. Do not retry the same width/stretch, slant or flat-effect method. Initial evidence: q219 in `localization/graphics/REWORK_ESCALATIONS.json`. Any new escalation must cite genuine C review decisions and cannot be inferred from a test fixture.
- `PRESERVE_ORIGINAL`: keep the preserved original without producing a replacement DDS.

Do not reopen a current approved candidate merely to migrate evidence. New pixel evidence outranks prior numeric PASS; missing approval evidence remains HOLD rather than auto-REWORK. Measure produced DDS, current-evidence approvals, P0/P1 regressions, user acceptance and actual in-game closures separately. Keep the six-launch schedule, updated distinct A/B/C1 production shards, exact-SHA C2/C3 and RUNTIME_VALIDATION semantics.

## Evidence enforcement override — 2026-10-08

Read `docs/KOREAN_LOCALIZATION_EVIDENCE_GATE.md` before selection. Its evidence gate
supersedes legacy note-token approval and any conflicting throughput/export wording.
Keep six launches/hour and the updated A/B/C1 production + C2 QA ownership. Up to three C2 QA assets is a
ceiling, not a quota. Start with known-defect calibration and current regressions;
q154 gray-menu glyph-weight/counter-space is HOLD for C2 native-DDS recheck.
A/B/C1 establish source-derived family references while repairing owned regressions.
C and C3 must record separate per-region observations; all localized PRE_INGAME
exports require validated `role_C/APPROVALS/qNNN.json` evidence. Missing evidence
means HOLD for export, not automatic DDS regeneration. Do not copy test fixtures
into approval/calibration records or invent visual findings to satisfy the schema.
Use `tools/localization/summarize_qa_state.py` for current counts; historical PASS
and stale aggregate counters must not be reported as final approval.

## Execution backend priority
- **Default execution backend: ChatGPT local execution environment.** Run Python/image/DDS transforms, candidate generation, comparison-image production, deterministic static QA, manifest generation and other work that can execute safely from locally materialized repository inputs in the ChatGPT local environment first.
- **GitHub remains the source-of-truth and synchronization layer.** Read current branch/queue state from GitHub before selection; after local work, persist required outputs/state to this branch and verify the resulting remote HEAD.
- **Do not dispatch a GitHub Actions run merely to execute work that the ChatGPT local environment can perform directly.** This applies especially to ordinary DDS/image processing, source/candidate comparisons, Python validators and PRE_INGAME JPG generation.
- Use **GitHub Actions only when the remote runner environment itself is part of the required evidence or capability**, including Windows/Win32 Release build validation, repository CI/status checks, exact runner-specific reproducibility, or another dependency unavailable in the ChatGPT local environment.
- **N100 MCP is fallback/auxiliary capacity only.** Use it when GitHub plus the ChatGPT local environment cannot safely complete the task, or when a required file/tool/resource exists only there. Do not send routine localization work to N100 solely because it is available.
- Backend choice never weakens QA. Local execution must use the same exact source/candidate hashes, persisted-DDS decode checks, RAW/FLIP-Y review, C/C3 semantics and evidence requirements as hosted execution.
- Record the execution backend in work evidence when material work is performed so later runs can reproduce where the result came from.

## Post-task cleanup — mandatory (2026-10-08)
- **Finish publication and QA first.** Persist every required DDS/source, English-original comparison, RAW/FLIP-Y JPG, QA JSON, queue/resume/progress/WORKLOG update, and any required build artifact; commit/push and verify remote HEAD before removing any temporary material.
- After EVERY A/B/C1/C2 job, regardless of execution backend, run the post-task cleanup finalization step before reporting completion. Clean only transient, reproducible task scratch; do not delete tracked source, user review exports, pending QA evidence, backup source originals, or work in progress.
- **GPT local:** Prefer per-run `tempfile.TemporaryDirectory()` or a `try/finally` to remove generated-only intermediate directories after outputs are safely persisted. GitHub-hosted ephemeral runner workspaces are discarded by Actions; do not copy ephemeral outputs onto N100 for storage.
- **N100 fallback:** Use `python3 n100-mcp/post_task_cleanup.py run --task-id ROLE-ID -- python3 path/to/job.py` (or repository `tools/localization/post_task_cleanup.py`) for each managed computation. It supplies isolated `TMPDIR` / `OUTRUN_TASK_SCRATCH` and removes only that run's marked scratch on exit code 0. Nonzero exit preserves failed scratch and diagnostic evidence; a failed or unverified publish MUST NOT be called successful.
- **N100 Git worktrees:** Create only when strictly required. Immediately after `git worktree add`, opt in using `python3 n100-mcp/post_task_cleanup.py register-worktree --base /home/chatgpt-runner2/work/<base-repo> --path /home/chatgpt-runner2/work/<ephemeral-worktree> --task-id ROLE-ID`. Following verified remote publication call `finish-worktree --path /home/chatgpt-runner2/work/<ephemeral-worktree>`. It removes the worktree via non-force `git worktree remove` ONLY if it is registered, not active, completely clean (including untracked files), and its HEAD is reachable from an origin remote-tracking ref. Otherwise preserve it and record why it was skipped.
- **Interrupted-run recovery:** The N100 current-user systemd timer `outrun-task-cleanup.timer` checks explicitly registered worktrees hourly with a minimum 24-hour grace period. The timer never deletes unknown/unregistered worktrees or failed scratch. Use `post_task_cleanup.py prune --dry-run` to audit candidates.
- Never use `git clean -fdx`, `git reset --hard`, forced worktree removal, or broad `rm -rf ~/work` / `~/tmp` as a routine cleanup action. Never clean another account or overwrite concurrent lane work. Report cleaned/skipped paths and available disk space when N100 was used.

## Isolation and source rules
- Work only on korean-localization-recovery-20260928. Never merge VR/FFB source or history.
- Preserve the independent original-mod Korean patch architecture.
- When an HD-mod DDS exists it is the graphics baseline. Never upscale an older low-resolution Korean DDS.
- Read DDS headers and preserve dimensions, format/compression, alpha and mip behavior.
- Preserve raw DDS per-sprite mirror/rotation/orientation.
- Preserve vehicle/model names, brands/logos, song titles/credits and legal/licensing marks unless explicitly approved otherwise.
- Preserve non-text artwork/background wherever possible and modify only intended text regions.
- Preserve source style: fill/gradient, outline, shadow/glow, proportions, alignment, scale and spacing.
- Reject seams, black lines, erasure residue, opaque boxes, alpha halos, clipping, overlap and unintended artwork changes.
- **Zero-overlap rule:** localized glyph/effect pixels may not overlap any other localized label, preserved source text, icon, decorative foreground, or protected artwork by even 1 pixel. Source-text residue beneath/behind Korean lettering also counts as overlap and is FAIL. Generation must leave positive separation whenever the source layout provides it; QA must use pixel masks plus controller visual review, not bbox containment alone.
- Stage names are proper names and MUST use the canonical phonetic Hangul transliterations in `localization/graphics/TRANSLATION_NAMING_POLICY.md`; semantic stage-name translations or mixed semantic/phonetic naming are forbidden.
- Song titles/music credits MUST remain original English artwork and are protected from clean-plate removal or Korean redraw.
- Before rendering, measure the exact source glyph/effect bbox. Localized width and height may never exceed source width/height by even 1 pixel, regardless of plate/cell headroom.
- Multi-line rendering MUST preserve source typography per line. Shared source style means shared Korean line style; source-intentional line differences must be reproduced rather than normalized or invented.

## Zero-pixel-overflow rule
All new, modified and previously approved graphics are subject to exhaustive containment QA.
For each text element determine the original/HD baseline's actual non-transparent text-pixel bounding box and the applicable sprite-cell/text-region boundary. Compare the localized non-transparent pixels including outline, shadow, glow and alpha fringe.
If the localized result extends even 1 pixel farther than the exact original text bounding box, is even 1 pixel wider/taller than that source glyph/effect bbox, or crosses the sprite-cell/text-region boundary on left, right, top or bottom, it is FAIL and MUST be reworked. A larger empty plate/cell never grants extra text size. Same DDS canvas dimensions alone never constitute a pass.
Rework by reducing horizontal/overall scale, repositioning, shortening the Korean wording, or preserving the original when necessary. Recheck raw DDS orientation and readable/game orientation.
Existing approved_dds are not grandfathered: recheck them and remove/rework any FAIL.
Machine-readable QA must record per asset/element: original_bbox, localized_bbox, delta_left, delta_right, delta_top, delta_bottom, containment PASS/FAIL, and rework status.

## Controller queue scope gate
- The controller MUST use `localization/graphics/asset_queue.csv` as the authoritative graphics work queue on every run. Never use the number of DDS binaries currently committed under `localization/graphics/` as the total-work denominator.
- Current queue sanity baseline (2026-09-28): 137 rows = 79 `localize_text` + 47 `zoom_review` + 9 `font_pipeline` + 1 `hangul_name_entry` + 1 `preserve_brand_song_credit`. Recompute these counts from the current CSV each run; the numbers are a drift check, not a hard-coded limit.
- Direct image containment scope is at least the 79 `localize_text` items plus all 47 `zoom_review` items until each is positively classified, i.e. 126 texture rows in the current queue. Existing 16 HD candidates or the 40 DDS binaries presently stored in the repository are only partial working sets.
- A run MUST continue from pending/rework rows in the full queue; it MUST NOT declare graphics complete merely because every currently committed candidate DDS passed.
- For each localized/reviewed element, any 1-pixel escape from the original/HD source permitted region is `REWORK_REQUIRED`. Such an item MUST NOT be promoted to approval, packaging, or completed state.
- If original-region evidence is missing/ambiguous, classify `HOLD_STRICT_RECHECK`, never PASS. For BC/DXT/DXT5 assets, block-level containment alone is not sufficient for final approval when decoded-pixel evidence is unavailable.
- Edge-touch with zero outside pixels may remain a containment PASS, but must be marked high-risk and receive high-zoom/readable-orientation and in-game validation before final approval.
- QA/report state must distinguish `PASS`, `REWORK_REQUIRED`, and `HOLD_STRICT_RECHECK`; do not collapse HOLD into PASS.
- PNG comparison/proof images are evidence only and do not count as completed deployable DDS assets.

## User in-game regression override

`localization/graphics/INGAME_REWORK_BACKLOG.csv` is the authoritative user-visible regression backlog. It records defects confirmed from actual in-game screenshots and overrides prior static PASS/approval state until a newer in-game retest closes the row.

- Every A/B/C run MUST read the backlog before generic queue selection.
- Any row with `status=OPEN_USER_INGAME_FAIL` is actionable even if `asset_queue.csv` currently says PASS or `*_pass_pending_ingame`. Screenshot-confirmed failure reopens the work; historical PASS is not grandfathered.
- A/B production priority is: active P0 in-game backlog -> active P1 in-game backlog -> C-returned `REWORK_REQUIRED` -> normal readiness tiers. Do not select unrelated new production while an owned P0/P1 regression is actionable.
- `owner_lane` in the backlog overrides normal odd/even queue parity for that regression only. The non-owner lane must skip the active regression asset unless the backlog is explicitly reassigned or the owner is blocked and work-steal is recorded.
- `mapping_status=UNRESOLVED` or `SUSPECTED` means the first step is exact source/asset/runtime-ID mapping. Once exact mapping is obtained, continue through material rework in the SAME invocation when safe; do not stop at mapping-only evidence.
- Never guess the defect domain. `GRAPHICS` means DDS/artwork rework; `RUNTIME_TEXT` means localization text/runtime draw-path rework; `MIXED` must be split by source before changes. A/B must not create a fake DDS fix for a runtime-overlay defect or edit runtime code for a raster-only defect.
- Runtime-text fixes are allowed only inside the Korean-localization domain (for example `src/hooks_localization.cpp`, `localization/text/runtime_ko.tsv`, localization runtime docs/evidence). Do not touch VR/FFB/DX11/DXVK work. Any runtime source change requires current Win32 Release build validation before static completion.
- Low-resolution mixed-font evidence is a hard failure. Re-render from the native-resolution/HD source and source-faithful typography; never upscale a prior Korean bitmap candidate to hide blur.
- Broken glyphs, source-script residue, duplicate English/Korean, other-image intrusion, protected-art damage, wrong slant/perspective, bad baseline, clipping, or visible layer collision are hard failures even when numeric bbox/mask checks previously passed.
- For card/popup/HUD/title families, preserve the source transform: slant/perspective, baseline, alignment, fill/gradient, outline, shadow/glow, relative scale, line spacing and protected artwork. Source-style mismatch seen in-game is sufficient to reopen a candidate.
- User screenshot evidence outranks earlier controller visual PASS when they conflict. Numeric false negatives must be recorded as such and the visual defect must be repaired.
- A/B may reach `STATIC_PASS_PENDING_INGAME_RETEST` (or `BUILD_PASS_PENDING_INGAME_RETEST` for runtime changes) after repair. They MUST NOT set an in-game backlog row to CLOSED without a newer actual in-game retest.
- C must revalidate repaired backlog items but likewise cannot erase the user-visible defect based only on static evidence. C may mark `C_STATIC_PASS_PENDING_INGAME_RETEST`; final closure requires later in-game evidence.
- When one DDS causes multiple screenshot defects (for example the selector card family), treat them as one material asset rework while keeping every backlog row linked for retest. Do not award/record duplicate production completion for the same bytes.
- Preserve the screenshot filename, defect tags, mapping provenance, before/after asset hash, and remaining retest state in role reports/WORKLOG so later A/B/C runs do not repeat closed work.

## Short controller dispatch
The controller prompt may be intentionally minimal. The following commands are sufficient entry points once this repository/branch is selected:
- `OutRun 한글화 A 실행`
- `OutRun 한글화 B 실행`
- `OutRun 한글화 C 실행`

On any of those commands, first fetch the latest `korean-localization-recovery-20260928`, read this contract and all required state/policy files named at the top of this document, resolve the requested role below, perform the work, update Git state, commit/push when changed, and verify the resulting SHA. The Docker/controller prompt must not duplicate the detailed rules from this file.

## Dual-production lane schedule
- A (:00 / :30): PRODUCTION LANE A + self-QA. Create/rework actual localization assets continuously from A's queue shard. Run zero-pixel-overflow QA on every touched element and immediately fix failures in the same run. Do not spend the run only reviewing when producible work remains.
- B (:10 / :40): PRODUCTION LANE B + self-QA. B is no longer review-only. Create/rework actual localization assets continuously from B's queue shard, including promoting positively identified `zoom_review` text assets into production. Run the same zero-pixel-overflow QA and immediately fix failures in the same run.
- C (:20 / :50): CROSS-LANE FINAL QA + approval + Git synchronization. Revalidate new/changed A and B results plus approval candidates. Only exact containment PASS results may advance. C may immediately perform small corrective rework it discovers and revalidate it; larger failures return to `REWORK_REQUIRED` for the next A/B production cycle.

### Current production-first four-slot scheduler
- Keep exactly six launches per hour: A :00, C1 :10/:40, C2 :20/:50, B :30.
- A = odd index font/vector/manual producer; B = new even index % 4 == 0 real ImageGen producer; C1 = new even index % 4 == 2 real ImageGen producer. Producer self-QA is not independent C approval.
- C2 = **only independent C final-QA lane** for all odd/even candidate indexes from A/B/C1 and unindexed special C tasks. Batch cap is three fully evidenced items per invocation, not a quota. Prioritize user P0/P1, fresh/changed material, plate/CLEAN/actual DDS quality; repeated same-SHA evidence without change is not production or new approval.
- Every role refreshes actual branch HEAD/asset_queue and active in-flight owner before selection and immediately before commit. Never overwrite another producer's trial, queue update or already-persisted evidence. C2 may inspect all indexes but must not represent a self-reviewed producer as independently approved.
- Keep the previous B-owned in-flight jobs, explicit active P0/P1 assignments and durable SHA-bound proof with their current owners; deterministic mod-4 division applies to new unclaimed even work. A keeps its existing odd ownership unchanged. No automatic work stealing across active claims. Idle roles may select their next unclaimed actionable item within their assigned shard, never inflate QA-only activity into production.
- Strict C2/C3/user playtest, unapproved trial isolation, QA evidence retention, real PNG generation IDs, and RUNTIME_VALIDATION=UNTESTED are preserved. This user-directed mode remains active until explicitly changed; older temporary-backlog auto-restore thresholds do not apply.

## A/B/C1 production shard and anti-duplication
- Source of truth: stable numeric `index` from the **existing** `localization/graphics/asset_queue.csv`; no controller-specific queue state machine.
- A primary shard: odd indexes and existing explicit A ownership.
- B primary shard: unclaimed even indexes where `index % 4 == 0`; preserve older B-owned in-flight even items including index % 4 == 2 until legitimately completed/transferred.
- C1 primary shard: unclaimed even indexes where `index % 4 == 2` with real ImageGen. C1 never changes in-flight B-owned assets or odd A-owned assets.
- Producer selection order is user-owned P0/P1 assigned to that lane, then direct material REWORK, RENDER_READY, ONE_STAGE_TO_RENDER and only then PREFLIGHT. Select actual image-generation-capable work first and produce visible trial DDS and SHA-bound artifacts whenever all inputs and tools exist.
- Producer already holding an item must complete/persist or explicitly release ownership before another producer can take it. Each producer re-reads HEAD immediately before selection and commit; if another lane changed the item, skip/reconcile rather than overwrite. If no valid work is available, record the actual blocking dependency, not repeated generic review.
- C2 reviews all producer shards and unindexed C special tasks; independently binds SOURCE/CLEAN/PLATE_PASS/candidate exact SHA. Do not mark C2 or C3 passed on behalf of the producer.


## Candidate-completion-first production
This recovery branch restores the production methodology without restoring the later queue/state-machine architecture. The purpose is to convert accepted preparation evidence into actual Korean DDS candidates instead of accumulating masks, work orders or preflight-only commits.

### Readiness tiers
Classify unfinished A/B/C1 work from current Git evidence:
1. **RENDER_READY** — exact canonical source, removal/protected geometry, verified CLEAN_PLATE and safe lettering region are known, with no unresolved semantic blocker. Missing baseline/slant/style measurement is not a reason to stop; measure it and render in the same invocation.
2. **ONE_STAGE_TO_RENDER** — one deterministic preparation stage remains before RENDER_READY. Complete that stage and continue through Korean rendering in the same invocation whenever the inputs are safe.
3. **PREFLIGHT_ONLY** — source identity, semantic binding, effect geometry or another prerequisite still requires broader investigation before candidate construction can safely begin.

### Mandatory producer order
A/B/C1 select work in this order:
1. assigned active P0 rows from `localization/graphics/INGAME_REWORK_BACKLOG.csv`;
2. assigned active P1 rows from that backlog;
3. directly repairable C-returned `REWORK_REQUIRED`;
4. `RENDER_READY` assets without a current acceptable Korean candidate;
5. `ONE_STAGE_TO_RENDER` assets;
6. existing candidate DDS needing material rework;
7. only when 1-6 are exhausted, new `PREFLIGHT_ONLY` work.

When a RENDER_READY or ONE_STAGE_TO_RENDER item exists, do not open unrelated preflight/work-order work merely to record progress.

### Same-invocation completion rule
- No artificial task boundary is allowed after the last deterministic prerequisite becomes ready. If the current A/B/C1 run creates or verifies the final source/mask/CLEAN_PLATE/safe-bbox/style prerequisite, continue in the same run through Korean render, DDS encode, decoded-final self-QA and candidate persistence.
- The normal production path is: exact canonical HD source -> verified CLEAN_PLATE -> source typography/baseline/slant measurement -> native-resolution Korean render -> measure/refit loop -> exact DDS encode -> decoded-final static self-QA -> English-source-vs-Korean-candidate evidence.
- If baseline/slant/style is the only missing information, measure it and render in the same task; do not create a separate successful preflight-only result.
- If the first ready asset becomes fail-closed during rendering, record the precise blocker and try the next ready item in the same shard before opening new preflight work.
- A/B should produce at least one new or materially reworked Korean DDS candidate whenever a RENDER_READY or ONE_STAGE_TO_RENDER item is safely runnable. Candidate output, not mask/work-order/commit count, is the primary production metric.
- A zero-candidate producer run is acceptable only when current evidence shows that no RENDER_READY or ONE_STAGE_TO_RENDER item can safely advance. In that case, perform at most one new preflight-only batch before the next candidate-completion attempt.
- This methodology is a Git workflow rule only. It MUST NOT add Production/Event IDs, task queues, rollover state machines, C0-C6 orchestration, Actions-gate bookkeeping or controller-side work-state engines.

### Mandatory production self-QA visual gate
- The global production visual gates in `docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md` apply to every new or materially reworked A/B candidate, not only screenshot-returned regressions.
- Before A/B records producer PASS, it MUST perform readable-orientation SOURCE/CLEAN/FINAL visual review plus raw/game-orientation review in addition to numeric checks.
- Mixed low-resolution Korean, broken glyphs, source residue/double drawing, other-image intrusion, unintended layer collision, wrong slant/perspective/baseline/alignment, or source-style/family mismatch are producer FAIL conditions.
- Numeric zero-overlap/bbox/protected-mask PASS cannot override a visible defect. When visual QA and machine QA disagree, fail closed, record the numeric false negative and rework.
- Do not hand a visibly questionable candidate to C as PASS. Use `REWORK_REQUIRED` or `MANUAL_RECONSTRUCTION_REQUIRED` and continue repair in the same invocation when safe.
- Static producer PASS without actual game evidence remains runtime-unvalidated and must retain `RUNTIME_VALIDATION=UNTESTED` or pending-in-game state.

### Ordered rework construction gate
- Every new or materially reworked graphics candidate MUST first execute the mandatory 10-stage producer sequence (including independent PLATE_ONLY and COMPOSITE_CONTAMINATION gates) and MUST retain all eight existing ordered visual checks in `docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md` before producer PASS: (1) English/source removal and complete plate/background restoration, (2) source-matching readable slant direction, (3) per-glyph Korean legibility at native/75/50 while obeying the exact source-bbox ceiling; shorter translated phrase is not a failure, (4) source-faithful weight/outline/shadow without excessive effects, (5) no clipped glyph/effect pixels, (6) no intrusion into protected graphics/vehicle/name/box content, (7) clean/correct FLIP-Y and RAW views, and (8) immediate readability versus the English source.
- This is a **generation loop**, not a final-review-only checklist. A/B must correct the failed construction stage and regenerate before recording producer PASS; C must return any missed violation as `REWORK_REQUIRED`.
- Machine bbox/mask success cannot override any failed ordered step.
- The post-encode/presentation hardening gate in `docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md` is mandatory for all new/materially reworked graphics: producer QA must judge pixels decoded from the persisted DDS, not only pre-encode renders; text-bearing authored mips and practical display scale must be reviewed; shared UI-family style must remain consistent; and current reworks must have zero unintended blast-radius changes outside the declared rework mask.
- C MUST run a fresh C3_STRICT_AUDIT before PRE_INGAME export for high-risk candidates defined by the quality pipeline (including prior user/in-game/JPG failures, BC/DXT or text-bearing mip chains, textured/gradient plate reconstruction, transformed/multi-line/small text, tight protected-art proximity, and prior typography/style false-negatives). Missing required C3 evidence is HOLD/pending-C3, never PASS.
- Coverage is asset-level as well as pixel-level: every visible localizable source segment must be localized, explicitly preserve-original by policy, or fail closed. A skipped English UI segment is FAIL even if all rendered Korean segments pass.

## Throughput rule
- Continue producing multiple assets in one run while tool/runtime budget allows; do not stop after a single DDS when additional independent queue items are actionable.
- Persist each completed batch and machine-readable QA evidence to Git so the next invocation can resume from repository state alone.
- Do not require Docker/controller configuration changes for workflow-rule changes; modify this Git contract/state instead.


## Compute placement policy
- N100 is the controller/orchestration host, not the preferred heavy image-processing host. Keep N100 work to Git synchronization, queue/state inspection, hashes, short metadata transforms, browser/controller duties, local-only source access, and runtime/in-game operations.
- Do **not** run full-resolution DDS/Pillow/NumPy rendering, compression/decompression, whole-atlas pixel scans, clean-plate generation, or equivalent CPU-heavy static QA on N100 when the required inputs already exist in this Git branch.
- If a computation does not need to write large repository binaries, prefer the ChatGPT native sandbox.
- If required inputs/dependencies cannot be materialized locally and hosted execution is necessary, use the GitHub-hosted worker in `.github/workflows/localization-cpu-worker.yml`: write/replace the deterministic role slot `tools/localization/cpu_jobs/A.py`, `B.py`, or `C.py` and push it. The workflow runs the script on `ubuntu-latest` and may commit only candidate/evidence paths under `localization/graphics/hd_candidates/`, `localization/graphics/role_A/`, `localization/graphics/role_B/`, `localization/graphics/role_C/`, or `localization/graphics/worker_results/`.
- CPU worker scripts MUST NOT mutate shared controller state (`asset_queue.csv`, `resume_state.json`, `progress/`, `WORKLOG.md`) or source/runtime code. After the worker output commit lands, fetch latest Git and perform semantic reconciliation plus shared-state updates in the role/controller step.
- Do not duplicate the same heavy computation on N100 after dispatch. Until the worker output is present, report it as compute-pending rather than candidate-complete. A later role invocation consumes the Git result first.
- N100 heavy-Python fallback is allowed only when required input exists only on N100, the hosted worker is unavailable/failed, or runtime-local access is intrinsically required. Record the fallback reason in the role report.
- This compute handoff does not change the authoritative work queue, role parity, approval rules, or completion semantics; it is execution placement only.

## State and completion
Do not repeat completed work. Resume from current Git progress/resume state. Each completed batch updates its machine-readable report, localization/WORKLOG.md and localization/progress/STATUS.md as applicable.
Before approval inspect raw DDS and readable/game orientation; use in-game screenshot validation when available.
Git synchronization is mandatory at the end of each role when that role changed files: commit/push only its localization changes to korean-localization-recovery-20260928 and verify the resulting commit SHA. Do not create empty commits. Resolve conflicts by preserving current localization work and never importing VR/FFB changes.


## Quality layer separation
- Image-quality rules are independent from controller scheduling/state logic.
- For every newly produced or materially reworked localized graphics asset, follow `docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md`.
- Preserve the pipeline: exact HD source -> source-text mask -> protected-artwork mask -> clean plate -> Korean lettering -> final candidate -> static QA.
- Do not invalidate every historical approved candidate merely because this quality layer was imported. Apply it to new/reworked assets and to existing assets only when QA evidence flags a concrete defect.
- Static QA and runtime/in-game validation are separate. If runtime validation was not actually performed, record `RUNTIME_VALIDATION=UNTESTED`.
- These quality requirements MUST NOT introduce new scheduler schemas, Production/Event IDs, rollover state machines, C0-C6 orchestration, or other controller bookkeeping.

## C-pass pre-in-game human JPG review gate

Before any graphics asset that has reached independent C static PASS is treated as ready for actual in-game testing, C MUST maintain a consolidated English-original-vs-current-Korean human-review JPG export under localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/.

- Rebuild the export from current asset_queue.csv state; never carry stale images for assets reopened by later user/JPG/in-game regression.
- Include every current localize_text graphics row whose latest valid state is independent C PASS, plus exact byte-identical aliases of a C-approved candidate.
- Exclude A/B/user-rework states that are still pending a newer C pass.
- Number files in queue-index order as NNN_qIII_ASSETKEY.jpg and retain manifest.csv / manifest.json so the user can report corrections by number.
- The English original is mandatory. Each numbered localized-candidate JPG must place the canonical unmodified English source and the current Korean candidate side-by-side at the same decoded dimensions. The top comparison is FLIP-Y review orientation; the bottom comparison is RAW DDS orientation.
- Fetch the English source from a pinned canonical source revision or exact repository stock-original archive and record source origin/revision, native dimensions and SHA-256 in the manifest. Prefer a same-resolution English source. If an asset was intentionally rebuilt at a higher native resolution while only a proven lower-resolution English original exists, that English original may be integer nearest-neighbor scaled for the JPG display only; record the native size and scale and never treat the scaled preview as pixel-QA evidence. If a larger public HD source conflicts with a lower-resolution C-approved source, use the exact SHA-proven source that C actually validated when available. Otherwise fail closed. Do not substitute an older Korean bitmap, clean plate, or already-localized candidate for the English original.
- The persistent exporter is tools/localization/export_c_pass_comparison.py. Whenever C changes the current C-PASS membership or candidate bytes, the C execution path (local preferred, hosted only when needed) MUST invoke this exporter before C synchronization is considered complete. A later C QA script may replace tools/localization/cpu_jobs/C.py, but it must still invoke the persistent exporter when the C-pass review set needs refresh.
- The comparison must use an opaque neutral background so wrong orientation, reversed slant, source residue, overlap, broken glyphs, alpha halos, other-image intrusion, source-style drift, baseline/alignment mismatch and protected-art damage can be judged directly against the English original.
- A C policy PASS that intentionally has no localized candidate remains in the numbered set; its comparison shows the English source on both sides and clearly marks the current result as original-preserved/no-localized-pixels.
- User rejection from this JPG review overrides prior static/C PASS exactly like in-game screenshot evidence: reopen the affected asset for A/B rework and require a newer C pass before it returns to this export.
- C pre-in-game visual review MUST enforce plate restoration, readable slant direction, source-relative text hierarchy/scale, readable effect weight, zero clipping, protected-art isolation and completeness of visible translated labels. Any user-visible failure in these categories overrides an earlier C numeric/static PASS and reopens the row.
- A/B rework after such a rejection MUST materially change the candidate or exact rendering evidence; merely changing status/notes or re-running the old bytes is not completion.

- This JPG review is a pre-in-game human gate only. It does not replace actual in-game validation and must not close RUNTIME_VALIDATION.


## C third-stage strict QA fallback

When normal actionable work is exhausted, C MUST not idle or declare the graphics stream complete merely because current candidates already have an independent C static PASS. Instead, C enters **C3_STRICT_AUDIT**, a third-stage fail-closed QA pass over previously C-approved graphics.

### Trigger and target set
- Trigger only after the current C invocation has refreshed Git and confirmed there is no higher-priority fresh A/B candidate, user in-game regression, C-returned rework, or pending independent C review that it can safely process first.
- The target set is graphics whose **current bytes** have a valid independent C static PASS. Superseded/reopened candidates, A/B-only PASS, and candidates awaiting fresh C are not eligible until they receive a new C PASS.
- Audit the least-recently third-stage-reviewed eligible C-pass asset first so the whole C-pass set is eventually covered. Do not repeatedly audit the same unchanged bytes while other eligible C-pass assets remain unaudited.
- A changed candidate SHA, changed canonical English source/clean-plate evidence, new user/JPG/in-game defect, or changed quality policy invalidates any earlier third-stage result for the affected asset and makes it eligible again.
- This is QA evidence, not a new scheduler or production queue. Existing asset_queue.csv remains authoritative for work state.

### Mandatory C3_STRICT_AUDIT visual priorities
C3 MUST compare the canonical English source, verified clean plate, and current Korean candidate at matched decoded dimensions. Review readable/FLIP-Y orientation, RAW DDS orientation, practical game scale, and high zoom. Give extra scrutiny to:
1. **Slant / perspective direction** — Korean text must lean in the same readable visual direction and with a source-faithful amount of slant/perspective. Opposite lean, accidental upright text, excessive lean, or per-line inconsistency is FAIL.
2. **Clean plate / source removal** — the pre-render plate must look naturally reconstructed with no English/source-script residue, blur/smear, ghosting, patch rectangle, donor seam, wrong texture, damaged graphic, or alpha discontinuity. A merely hidden/blurred original is FAIL.
3. **Original-font/style fidelity** — compare font-family impression, condensed/wide proportion, weight, stroke character, corner/roundness character, capitalization-equivalent hierarchy, line hierarchy, spacing, alignment, baseline, gradient/fill, outline, shadow/glow and depth. The exact same font is not required when unavailable, but an obviously different family or visual weight is FAIL.
4. **Per-glyph scale and readability** — compare native size, stroke/counter clarity, and readability of individual Hangul glyphs against representative source-family glyphs. A smaller Korean word/line/sentence is PASS for length and scale if each letter is readable and fits within the strict source bbox; no minimum whole-sentence width, height or aspect ratio.
5. **Glyph integrity** — no broken Hangul strokes, missing pixels, clipped antialias fringe, malformed syllables, jagged low-resolution upscaling, mixed-resolution font appearance, or partially erased glyph/effect pixels.
6. **Protected-art separation** — zero overlap with vehicle/character graphics, names, icons, boxes, frames, neighboring labels, preserved English/song/brand artwork, or unrelated atlas content. Even a 1-pixel prohibited intrusion is FAIL.
7. **Source-faithful placement** — preserve intended horizontal/vertical anchoring, baseline, line spacing, per-line scale hierarchy and plate relationship. Numeric bbox containment alone does not make visibly misplaced text acceptable.
8. **FLIP-Y and RAW consistency** — both views must be clean and semantically correct. A candidate that looks correct only in one orientation is FAIL.

### Third-stage decision rules
- **Visual evidence outranks machine PASS.** Zero-overlap, bbox, mask, header, roundtrip or other numeric success can never override a visible defect found in C3.
- If any mandatory C3 item fails, immediately supersede the prior C PASS for the current bytes and return the asset as `REWORK_REQUIRED` with the exact visual defect and source-vs-candidate evidence. A/B must then rework it before it can regain C approval.
- If evidence is ambiguous, the source is not exact, or BC/DXT decoded-pixel proof is insufficient, use `HOLD_STRICT_RECHECK`, never PASS.
- Use `C3_STRICT_PASS` only when all ordered visual checks and the existing numeric/containment gates pass for the same candidate SHA.
- C3_STRICT_PASS is **not** runtime validation and does not close any user in-game backlog. Keep `RUNTIME_VALIDATION=UNTESTED` or the existing pending-in-game state until an actual game retest exists.
- Record candidate SHA, canonical source SHA/provenance, clean-plate evidence, prior C-pass provenance, FLIP-Y+RAW review evidence, C3 result and failure reason in the C role report/WORKLOG. Third-stage PASS is QA hardening, not a new production completion and must not be counted as a newly produced DDS.


