# 신규 A 슬롯 이미지 생성 시험

이 스택은 옛 생산 큐/QA/예약 스케줄을 가져오지 않는다. A 탭 하나에서 PNG 업로드 → 자동 프롬프트 전송 → 내장 이미지 생성 결과 다운로드 → 기계 QA → 원본/결과 재첨부 및 ChatGPT 자체 QA를 단 한 번 실행한다. 유료 API 키 불필요. 생산 버튼을 사람이 누를 필요는 없다.

## Portainer 설정

- Repository: `https://github.com/thp32tt/OutRun2006Tweaks`
- Reference: `refs/heads/korean-localization-clean-start-20261013`
- Compose path: `docker/imagegen-a/docker-compose.yml`
- 환경변수: `VNC_PASSWORD` 필수. `LOCALIZATION_PROJECT_URL`은 원하는 ChatGPT 프로젝트 URL; 비우면 일반 새 채팅.
- 기존 초기화된 스택과 6082/8788 포트가 겹치면 `VNC_PORT` / `STATUS_PORT`를 변경한다. 기존 컨테이너와 브라우저 볼륨을 동시에 공유하지 않는다.
- 사용자가 수동 Deploy. 새 브라우저 프로필이므로 `http://서버주소:6082/vnc.html`에서 최초 ChatGPT 로그인만 완료하면 전송은 자동 시작된다. 인증/접근 제한 화면은 사람이 처리한다.
- `http://서버주소:8788`에서 현재 단계 JSON 확인. GitOps 자동 재배포는 켜지 않는다.

## 원본 PNG 경로

GitHub `source/english_png/Q217_D1039D6F_BASE_READABLE_FLIPY.png` → 컨테이너 `/sources/Q217_D1039D6F_BASE_READABLE_FLIPY.png`.
`input/source.json`의 commit 고정 URL에서 최초 실행 시 다운로드하고 SHA-256, PNG 디코딩, 2048×2048 RGBA를 검증한다. `/sources`는 스택 전용 named volume으로 접근 가능하며 이후 같은 해시는 캐시를 재사용한다. 원본 디렉터리를 N100에서 수동 복사할 필요가 없다. 파일을 변경할 때는 URL의 commit와 SHA도 함께 검증해서 변경한다.

## 결과와 중단

`/data/results/OUTRUN-NEW-A-Q217-20261013-142553/`:
- `generated.png`: 실제 다운로드 바이트. 자동 크기 보정/리사이즈 없음.
- `mechanical_qa.json`, `compare_100.jpg`, `compare_75.jpg`, `compare_50.jpg`.
- `generation_prompt.txt`, `qa_prompt.txt`, `visual_self_qa.txt`, `state.json`.

`COMPLETE`는 파이프라인 종료이며 이미지 합격 의미가 아니다. `self_qa`와 `mechanical`을 확인한다. 같은 A의 검수이므로 독립 QA가 아니다. 보호 영역의 정확한 픽셀 마스크가 없는 이번 시험에서는 기계 보호픽셀 검증도 미확인으로 남긴다. DDS 생성/게임 테스트/정식 승격 없음.

전송 직전에 체크포인트를 기록하여 재시작/타임아웃 때 동일 TASK를 자동 재전송하지 않는다. `HOLD`이면 이유와 기존 채팅을 확인한다. UI가 변경되거나 출력 다운로드 버튼을 구분하지 못하면 멈춘다. `IMAGE_DOWNLOAD_SELECTOR`를 추가 설정할 수 있으나 해당 생성 답변 안의 정확한 이미지 다운로드 버튼 하나만 지정해야 한다. 다음 시험은 기존 결과를 보존하고 새 TASK_ID로 명시적으로 실행한다.

## 검증 경계

로컬 단위 테스트 10개 통과. GitHub workflow는 동일 SHA에서 단위 테스트, 실제 Chromium HTML fixture의 PNG 첨부/전송/다운로드/2장 재첨부, Docker 이미지 빌드를 검사한다. fixture는 실제 ChatGPT 사이트 검증이 아니다. 운영 업로드/내장 ImageGen/자동 자체 QA는 사용자 수동 배포 후 실물 결과가 생기기 전까지 UNTESTED. 로그인 후 UI 선택자가 현재 화면과 맞지 않으면 HOLD로 남는다.

TASK_ID: `OUTRUN-NEW-A-Q217-20261013-142553`; RUNTIME_VALIDATION=UNTESTED.
