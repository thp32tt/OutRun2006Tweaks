# Portainer ← GitHub 배포 경계 및 A q217 단건 smoke (2026-10-13)

## 확인 및 원칙
- 사용자가 2026-10-13 명시한 실제 운영 흐름: **GitHub에서 정책 소스를 관리하고 Portainer가 Git 설정을 가져오며, Docker stack의 pull/redeploy는 사용자가 Portainer에서 수동 관리**한다.
- 정책 SSOT: `thp32tt/OutRun2006Tweaks`, `korean-localization-recovery-20260928`. A 테스트 설명: `docs/OUTRUN_A_Q217_IMAGEGEN_SMOKE_20261013.md`.
- **GitHub commit 자체는 운영 재배포가 아님**. `AUTO_SEND=true`는 이미 승인된 메시지 자동 전송 설정이지 컨테이너 자동 재배포 허가가 아니다.
- 현 브랜치에서 `tools/chat-controller/localization-recovery-v1/docker-compose.yml` 직접 파일은 **조회 404**. 현재 Stack의 **정확한 Git Repository URL / Repository reference / Compose path / Additional paths / 빌드 이미지 경로 / 마운트 상태는 Portainer 화면이나 실제 Stack API에서 확인 전에는 미검증**. 다른 Git 저장소를 사용하는 스택에 이 저장소의 override를 자동 사용할 수 있다고 주장하지 않는다.
- 과거 `deploy_plate_controller.py --stage`는 별도의 레거시 지원 경로로, Portainer 내부 `/pdata/compose/54`와 **로컬 Docker**를 갱신한다. Git-origin Portainer Stack의 기본 절차로 실행하지 않는다. Git 관리 스택의 Compose는 **Git 원본에서** 수정한다. Portainer에서 Git 연결 분리(Detach)나 Web Editor로 편집하지 않는다.
- 동일한 Git 저장소를 참조하는 **기존 Git-based Stack**에서만 Portainer Git > Additional paths를 통한 Compose override를 시험할 수 있다. base Compose가 다른 저장소에 있는 경우에는 **그 실제 Git 저장소의 Compose 정의에 동일 설정을 적용**해야 하며, 이 저장소의 샘플 YAML을 별도 Stack으로 배포해서는 안 된다.

## 실제 Git-based Portainer 적용 절차 (운영 변경은 사용자만)
1. Portainer > **Stacks > 기존 localization recovery 스택** 선택. Git Repository URL, branch/ref, **Compose path**, Additional paths와 현재 이미지명/태그 및 named volume을 백업/확인한다. 현재 Git 기반인지 확인한다. *이 확인을 하기 전에는 새 Stack 생성·동일 이름 중복 실행 금지*.
2. controller 이미지가 GitHub의 `controller_png_attach.py` + `patch_controller_png_upload.py`를 **빌드 시 내장**하거나 런타임이 그 모듈을 사용한다는 근거를 확인한다. Git의 Markdown/override만 갱신하고 **기존 이미지가 구버전인 경우에는 파일 첨부가 작동하지 않는다**. 이때 수동 빌드된 이미지가 정확한 Git SHA에 대응한다는 근거 또는 Git 기반 build context/Dockerfile 연결이 먼저 필요하다. 이 저장소에는 사용 중인 Portainer base Compose의 정확한 경로가 아직 없다.
3. Stack이 **이 Git repository/ref**를 이미 직접 소비하고 있고 Compose Additional paths 적용이 지원되는 경우: 기존 base Compose에 `docker/localization-production/portainer-git-q217-a-smoke.override.yml`을 추가. 이 파일은 기존 service의 환경변수 4개만 변경하고 image/build/volume/port/다른 서비스를 변경하지 않는다. 지원되지 않거나 다른 repo라면 적용하지 않는다.
4. 정확한 q217 입력 `/data/imagegen/inputs/A/Q217_D1039D6F_BASE_READABLE_FLIPY.png`과 `/data/imagegen/pending_A.json`이 같은 named volume 안에 실제 있는지, SHA256과 TASK_ID가 맞는지 확인한다. **Git에서 Compose를 pull하는 것만으로 /data의 PNG가 자동 생성·복사되지 않는다.** 별도의 입력 공급 경로가 검증되기 전에는 추가 파일 복사를 사용자 수동으로 처리한다.
5. GitOps 자동 Polling/Webhook 자동 재배포는 사용자 수동 배포 지시와 충돌하지 않도록 해제/비활성화 여부를 확인한다. **사용자가 Portainer의 Pull and redeploy를 명시적으로 실행**한다. 삭제/재생성/컨테이너명 충돌 조치는 운영 관리자 판단 없이는 금지.
6. 배포 이후 컨테이너에서 실제 `OUTRUN_A_SINGLE_SMOKE_TASK_ID`, `SCHEDULE_MINUTES=0`, `AUTO_SEND=true`, 패치 마커, 소스 PNG SHA, 신규 첨부 메시지의 해당 TASK_ID, 이미지 생성 출력 바이트/SHA를 구분 검증한다. 어느 단계라도 미확인이라면 `UNTESTED` 또는 `HOLD`. 실게임/C1/C3/DDS 승인 없음.
7. 시험이 끝나면 **q217 overlay를 제거하고** `docker/localization-production/portainer-git-normal.override.yml`로 정상 환경변수(`SCHEDULE_MINUTES=0,10,30,40`, task ID 비우기)를 적용한 Git 상태를 만든 뒤, **사용자가 다시 Portainer에서 Pull and redeploy**한다. A/B/C1 정상 실행과 C2 제외를 확인한다. 기존 /data·/logs·sent/·게임 상태 유지.

## Git Compose overlay 자체의 제한
- Smoke 파일: `docker/localization-production/portainer-git-q217-a-smoke.override.yml`.
- Restore 파일: `docker/localization-production/portainer-git-normal.override.yml`.
- 둘 다 **기존 Compose에 추가하는 환경변수 override**이므로 단독으로 docker image 빌드나 PNG 볼륨 공급을 하지 않는다.
- 명시적으로 같은 Git repository에 연결된 stack이라는 실증 증거가 없으면 운영 배포는 HOLD. 문서에 적힌 `--single-a-smoke` 로컬 스테이징은 *Git pull 기반 Portainer 운영 시 실행하지 않는다*.
- GitHub Action은 코드를 검증할 뿐 Portainer 배포나 Docker 빌드 권한으로 무단 전환하지 않는다.

## 정적 사전 검사 현황
- GitHub에서 Portainer Git-source 모드/필요한 연결 정보 미확인을 식별했고, 하나의 기존 service에서 네 개의 환경변수만 오버라이드하는 두 YAML 파일을 Git에 작성했다.
- 실제 Git-connected stack의 Compose path / image build / PNG bind, Portainer Pull and redeploy / ChatGPT 이미지 생성은 **UNTESTED**.
- 공식 Portainer 참고: https://docs.portainer.io/user/docker/stacks/edit 및 https://docs.portainer.io/faqs/troubleshooting/stacks-deployments-and-updates/how-do-automatic-updates-for-stacks-applications-work
