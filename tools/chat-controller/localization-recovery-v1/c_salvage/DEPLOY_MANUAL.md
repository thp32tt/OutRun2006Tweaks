# OutRun 2006 한글화 C 오프라인 복구 — Portainer 수동 재배포

Git origin: `thp32tt/OutRun2006Tweaks`
Git ref: `refs/heads/localization-controller-recovery-20260928`
Base compose: `tools/chat-controller/localization-recovery-v1/docker-compose.yml`

## 현재 상태

이 브랜치의 **실제 Portainer 기본 Compose에** `outrun-c-salvage-offline` 서비스를 병합했다. 과거 `korean-localization-recovery-20260928`에만 있던 코드를 별도의 `./c_salvage/` 디렉터리에 SHA 동일하게 배치했다. 포팅용 추가 Compose path는 **필요하지 않다**. GitHub 작업은 실행 중인 Portainer Stack을 바꾸지 않는다.

기존 A/B ChatGPT ImageGen 2탭, `CHAT_SLOTS=2`, 5분 스케줄, `AUTO_SEND`, 프로젝트 URL 및 볼륨/포트는 유지한다. C는 **별도 CPU 백그라운드 서비스**이며 ChatGPT 창이나 ImageGen을 호출하지 않는다. C1/C3와 사용자의 게임 테스트는 별도이다.

## 사용자가 실행할 작업

1. Portainer → Stacks → `outrun-kor`. Git Repository가 `OutRun2006Tweaks`, Reference가 `refs/heads/localization-controller-recovery-20260928`, Compose path가 위 경로인지 확인한다.
2. 새 `c_salvage` Dockerfile/원본 마스크/PNG 소스는 해당 Git branch에 있다. N100 전용 출력 폴더 `/home/chatgpt-runner2/work/c-salvage-production`는 준비되어 있고, 컨테이너 사용자 UID/GID는 1002:1002로 일치하도록 설정했다.
3. Portainer의 **Pull and redeploy**를 **사용자가 직접** 실행한다. Git 자동 polling/webhook으로 강제 갱신하지 않는다.
4. `outrun-c-salvage-offline` 컨테이너가 실행 중인지 확인한다. 컨테이너가 없으면 최신 브랜치/Compose가 반영되지 않은 것이므로 사용자 재배포 설정 확인; 비정상 종료면 로그를 조사한다.
5. 실행 직후 C 출력 경로 `/home/chatgpt-runner2/work/c-salvage-production/last_cycle.json`과 `candidates/*/receipt.json`을 확인한다. 이후 30분마다 신규 이미지 최대 10개를 분석한다. 원본 입력 `/home/chatgpt-runner2/work/image-src`는 읽기 전용, C 출력 폴더만 쓰기 가능.
6. 불투명 후보는 명시적 `masks/*.mask.png`가 없으면 `HOLD`. 소스 PSD의 정확한 영어 레이어·원본 DDS/UV 영역/번역/검증 마스크/압축 코덱 근거가 없으면 최종 DDS는 자동 승인하지 않고 `TEST_ONLY`로 유지한다.

## 실패 시 안전 경계

- Compose는 기존 A/B 서비스의 환경·마운트·포트 설정을 변경하지 않고 C만 추가했다.
- C만 실패하더라도 A/B 볼륨을 초기화하거나 기존 컨트롤러를 새 이미지로 교체하는 조치를 하지 않는다.
- C의 Docker 구성을 빼고 복원하려면 **사용자가** 이전 Git commit으로 Stack ref를 변경하거나 C 블록을 제거한 커밋으로 수동 재배포해야 한다. 컨테이너 데이터 삭제 금지.
- C는 `network_mode: none`, 메모리 512MiB, CPU 0.5, 원본 폴더 ro, `read_only: true`로 제한된다.
- Portainer CI 검사: `.github/workflows/localization-c-salvage-predeploy.yml`. GitHub Actions의 Docker 이미지 빌드는 *운영 배포가 아니다*. 빌드/실기 PASS 여부는 실제 로그 확인 전까지 UNTESTED.

## QA 단계

`LAYER_PROPOSAL` → `CLEAN_CANDIDATE_REVIEW` → `C_COMPOSITE_TEST_ONLY` → `C_DDS_TEST_ONLY` → 독립 QA → 사용자 실게임 검증.

`RUNTIME_VALIDATION=UNTESTED`는 실제 게임을 실행할 때까지 유지한다. 사용자 게임 불량 OPEN은 자동 닫기/실패 재분류 금지.
