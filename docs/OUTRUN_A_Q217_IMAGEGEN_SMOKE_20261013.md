# A q217 — ChatGPT 브라우저 PNG 첨부 + 내장 이미지 생성 단건 실험 (2026-10-13)

## 목적 및 경계
- 사용자 지시: **A 작업 하나**로 실제 Docker 브라우저 컨트롤러의 영문 PNG 첨부→ChatGPT 내장 이미지 생성 결과를 검증한다. 실제 Docker/Portainer 배포·재시작은 **사용자가 수동**으로 수행한다.
- 현재 GitHub 변경은 소스/스테이징 정책과 격리 테스트용이다. 운영 컨테이너를 수정·재시작하지 않았다. 유료 OpenAI API 호출 금지.
- 1건만: `TASK_ID=OUTRUN-A-Q217-IMG-SMOKE-20261013`, 역할 `A`, 큐 `q217`, 정본 `D1039D6F`. q217 공식 DDS/상태/과거 C1/C3/사용자 OPEN 기록은 변경하지 않는다.
- 이미지 입력: `Q217_D1039D6F_BASE_READABLE_FLIPY.png`, 실제 크기 **2048×2048 RGBA**. SHA256 `56b3834649568383293786e862025351d0f2379ec632592cf40d78c532a50b15`. 
- 원본 HD DDS: `textures/load/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds`; SHA256 `d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0`. 원본 DDS→PNG 방향은 `FLIP_Y_PREVIEW_PER_SPRITE_VERIFY`이므로 **스프라이트 실사용 방향은 승인 전 추가 확인**.
- 정확한 승인 매핑: `START → 출발`, `GOAL → 골`. OutRun2SP 로고·코스 썸네일·경로/도로 아트·다른 문구를 보호한다.
- 사용자 원본 ZIP `OR2-HD-GUI-v0.25.10a.zip`에서 2026-10-13 생성된 `OutRun_ALL_HD_Korean_Source_PNG_PART05_of_05_20261013.zip`의 q217 PNG/manifest를 사용한다. 임의 편집·재압축 후 원본이라고 기록하지 않는다.

## 1. GitHub 사전 검사 (배포 전)
- `python -m unittest discover -s tools/localization -p test_controller_png_upload.py -v`
- `python -m unittest discover -s tools/localization -p test_hd_imagegen_policy.py -v`
- `python -m py_compile tools/localization/controller_png_attach.py tools/localization/patch_controller_png_upload.py tools/localization/stage_controller_policy.py tools/localization/deploy_plate_controller.py`
- 확인: `--single-a-smoke`가 Compose `CHAT_SLOTS=3`, `SCHEDULE_MINUTES=0`, `AUTO_SEND=true`, `OUTRUN_A_SINGLE_SMOKE_TASK_ID=OUTRUN-A-Q217-IMG-SMOKE-20261013`를 작성. 다른 서비스·볼륨·기밀 설정 유지.
- 컨트롤러 패치는 `OUTRUN_A_SINGLE_SMOKE_TASK_ID` 존재 시 예약 맵을 `{0: "A"}`로 제한하며, B/C1 예약 전송 및 모든 탭 watchdog 전송을 차단. A의 manifest `task_id`가 정확히 일치하지 않으면 차단.
- 허용된 새로운 DATA 첨부 바이트, SHA, 프리뷰 확인 없이는 절대 텍스트만 보내지 않는다. `sent/A_OUTRUN-A-Q217-IMG-SMOKE-20261013.json`이 있으면 두 번째 발송을 중단한다.

## 2. 사용자 수동 STAGE 및 Portainer 재배포 절차
1. 이 브랜치의 **최신 정확한 commit SHA**를 확인해 체크아웃하고 기존 컨트롤러 image/Compose/프롬프트/`/data`/`/logs`를 보관한다.
2. 별도 전달하는 q217 단건 입력 묶음의 `inputs/A/Q217_D1039D6F_BASE_READABLE_FLIPY.png`, `pending_A.json`을 기존 컨트롤러의 **`/data/imagegen/`** 에 복사한다. 템플릿 예제나 해시가 다른 파일은 쓰지 않는다. 기존 `pending_B.json`/C1/상태는 삭제하지 않는다.
3. 현재 컨트롤러 설정·이미지를 백업한 뒤 사용자만 다음 명령을 실행한다:
   `python tools/localization/deploy_plate_controller.py --root . --revision <정확한40자리GitSHA> --stage --single-a-smoke`
4. 스테이징 결과가 `single_a_smoke=true`, `deployment_mode=MANUAL_ONLY`인지 점검한다. 운영 controller에 예상한 anchor가 없으면 빌드가 실패해야 하며 임의 우회하지 않는다.
5. 사용자가 Portainer에서 기존 **한글화 컨트롤러만** 수동 재배포한다. 별도 docker run으로 중복 컨트롤러 실행 금지. /data 및 /logs 볼륨 보존. AUTO_SEND=true여도 다음 A 예약 시각 `:00`에 **단 한 번**만 q217 전송, B/C1 예정 발송·watchdog 전송은 시험 동안 없음.

## 3. 실제 브라우저에서 확인해야 할 순서
- `UPLOAD_RUNTIME`: 첨부 전 입력 manifest 및 PNG 실제 해시 확인→Playwright 실제 파일 입력/파일 선택→ChatGPT composer에 **원본 이미지 프리뷰 등장**→첨부 완료 후 A 문구가 정확히 1회 송신됐는지 확인. UI 이벤트나 프리뷰만으로 서버 수신 성공을 단정하지 않는다.
- `CHAT_MESSAGE_SENT`: 전송된 메시지 본문에 `UPLOAD_TASK_ID=OUTRUN-A-Q217-IMG-SMOKE-20261013`가 남는지, 신규 A 대화 1개인지 확인. `sent/` 기록은 **메시지 전송**에만 사용하며 이미지 생성 PASS 아님.
- `IMAGEGEN_RESULT`: 실제 ChatGPT 내장 이미지 생성 작업이 시작·종료됐는지 확인하고, **생성된 출력 PNG 실제 바이트**와 SHA256 및 텍스트 번역을 저장한다. 단순 답변 텍스트·GitHub 링크·프리뷰는 출력 결과가 아니다.
- `QA`: 파일을 native/75%/50%로 열어 `출발/골` 정확성, 아틀라스 혼동·검정 박스·원본 로고·지도·배지 보호 여부, 투명도, CLEAN 영문 잔상, 클리핑을 확인한다. 원본 크기가 다르면 전체 그림을 임의 stretch하지 않는다. CLEAN은 별도 검증 대상이다.
- 판정: `INPUT_MISSING` / `SOURCE_REFERENCE_NOT_BOUND` / `UPLOAD_CONFIRMED_SEND_UNVERIFIED` / `MESSAGE_SENT_IMAGEGEN_UNVERIFIED` / `IMAGEGEN_OUTPUT_CAPTURED_UNREVIEWED` / `REWORK_REQUIRED` / `C1_SCOPED_TEST_PASS`. 파일 SHA 없는 결과·생성 호출 불명·DDS 미실행은 PASS 금지.
- `RUNTIME_VALIDATION=UNTESTED`, `DDS=NOT_BUILT`, `OFFICIAL_PROMOTION=NO` 고정. 실제 게임 재시험이나 C3 승인으로 위장하지 않는다.

## 4. 원복 (사용자 수동)
- 단건 실험 뒤 저장소 정책을 이전 커밋으로 되돌리지 말고 **같은 HEAD에서 `--single-a-smoke` 없이** 다시 `--stage`하여 전체 스케줄 설정(`0,10,30,40`) 및 `OUTRUN_A_SINGLE_SMOKE_TASK_ID` 제거를 검증한다.
- 사용자가 Portainer에서 수동 재배포하여 A/B/C1 정상 일정을 복원한다. 기존 `sent/` 기록·QA/DDS·원본 및 사용자 실게임 OPEN 상태는 삭제하지 않는다.
- 시험 결과가 확정되지 않으면 스테이징 구성을 방치하지 말고 의도한 격리 상태/복원 여부를 분명하게 기록한다.

## 5. 실행 기록
- GitHub 코드·정책 변경 / q217 입력 SHA 검증: 2026-10-13 사전 준비 완료.
- **실제로 실행한 검사**: GitHub 최신 수정 코드를 N100의 `work/a_q217_smoke_preflight/` 별도 임시 경로에 작은 Python 4개만 다운로드하여 `test_controller_png_upload.py` 13/13 PASS (0.027초). 기존 운영 Docker/볼륨을 열거나 변경하지 않았다.
- ChatGPT 자체 로컬 Chromium 실파일 시험: 정확 SHA256 `56b383...` / 3,735,331바이트 q217 PNG를 숨겨진 `input[type=file]`에 첨부하고 브라우저 File 이름/길이/MIME 확인 **PASS**. **실제 ChatGPT 프리뷰/메시지 수신 검증은 아님**.
- 첨부·검사 결과 패키지: `OUTRUN_A_Q217_ONE_SHOT_IMAGEGEN_DOCKER_SMOKE_20261013.zip` (원본 PNG + 정확 task manifest + 사전 QA 기록).
- 운영 Docker 재배포: **NOT_RUN (USER_MANUAL)**.
- 운영 ChatGPT 실제 파일 업로드: **UNTESTED (manual deploy pending)**.
- 내장 ImageGen 생성 / 결과 PNG 확보: **UNTESTED (manual deploy pending)**.
- 유료 API: **NOT_USED**.
- DDS·C1/C3·실게임: **NOT_RUN**.

참고: `docs/KOREAN_LOCALIZATION_CONTROLLER_PNG_UPLOAD_20261012.md`, `docker/localization-production/MANUAL_IMAGEGEN_ROLLOUT.md`. 해당 두 문서 및 계약에 대한 2026-10-13 단건 예외는 이 문서가 담당하며, 시험 이외 정상 정책은 그대로다.
