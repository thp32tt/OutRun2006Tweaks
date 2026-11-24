# Ferrari16 외부 모델 자동개발 실행 계획 (2026-11-23)

SSOT: `thp32tt/OutRun2006Tweaks@automation/ferrari16-external-20261123` 의 `docs/automation/FERRARI16_EXTERNAL_AUTODEV_QUEUE.json`. 컨트롤러: 같은 저장소 `chat-controller-downloads`, Portainer `outrun-chat-vr` 전용.

- **실행**: 매시 KST :00, :30, 단일 A 슬롯. 새 작업 ID를 매번 생성하지 않고 active_work_id를 완료할 때까지 승계한다. 동시 Git 작업 금지.
- **1순위**: 현재 기본 브랜치에서 깨진 모델 로더/양안 스테레오/PBR/유리 및 v0.03 대비 회귀 수정. 정상 release 덮어쓰기 금지.
- **2순위**: 정확 차종 + 고품질 모델/재질/노멀맵 16대 단위 정적 검증, 다이얼/속도/RPM/기어 연동, UV/투명도/메시 구조 개선.
- **3순위**: 변경된 코드와 변환 도구 테스트 후 Windows CI에서 x86 game+x64 host 패키지 exact-SHA 검증. 실패하면 같은 ID에서 원인을 수정한다.
- **4순위**: 테스트 ZIP·원복 스크립트·SHA·로그 경로 준비. Quest 3 실기 없이 최종 PASS/성능 PASS 주장 금지.

## 작업 반복 규칙

(1) GitHub 최신 active_work_id, source HEAD, 전차종 manifest·이전 작업 증거 확인 → (2) 중복 작업 판별 → (3) 실제 소스/모델 제작·오류 수정 → (4) 변경 영역 검사 → (5) 단일 material commit+증빙 → (6) 필수 final CI → (7) 큐 item status 및 next work ID 원자적 커밋. 실패/롤오버는 같은 ID. 고정 작업 한 번에 계획·검토만 반복 금지. **고정 마일스톤 작업은 진전 없음 3회 제한을 유지하되, 반복 디버깅 `EXT16-011`은 이 제한을 적용하지 않는다.**

## 안전 경계

- 기존 DX11/DX9Ex/DXVK, Model2, 한글화, 구형 `imsi1` 운전석 리워크 **자동 재활성화 금지**. 외부 모델링 전용 스위치에서만 작동한다.
- N100 우선 사용 금지: GitHub + ChatGPT 자체 로컬 우선. 원본/대용량 사설 자산이 N100에만 있을 때 최소 호출; 반복 빌드·압축·검색은 Actions/로컬에서.
- 328 GTS/575 Superamerica/F430 Spider 낮은 디테일 exact 후보를 기본 고품질 donor 위로 자동 강제승격 금지; Testarossa Spider 차종 검증 선행.
- 공개 저장소에 상용 모델·게임 원본·개인 사진·비밀키 업로드 금지. 재배포 권한 미확인 자료는 private evidence로 취급.
- 실제 HMD 결과가 없으면 `RUNTIME_VALIDATION=UNTESTED` (또는 `WAITING_USER_HMD`), 정적 검증과 별도로 기록.

## Portainer 반영 방법

`https://github.com/thp32tt/OutRun2006Tweaks.git` / `refs/heads/chat-controller-downloads` / `tools/chat-controller/v0.4/docker-compose.portainer-vr.yml`을 **Pull and redeploy / Rebuild image** 해야 코드·프롬프트가 반영된다. Docker 소켓 접근 불가 시 GitHub 코드 변경은 live 재배포로 간주하지 않는다. 상태 `http://192.168.0.48:8787/status`에서 `external_model_autodev_enabled`, target branch, enabled, actual last send를 재확인할 것. `AUTO_SEND=true`라도 Project URL/계정 로그인 검증 실패 시 발송 차단.

## 2026-11-24 14시 운영 정책 변경 — 원인 미발견 시에도 디버깅 지속

- 사고 원인: 09:37:59 마지막 EXT16-010 발송 이후 09:53:30 KST에 정적 게이트가 완료되어 `active_work_id=EXT16-006`(사용자 Quest3 HMD 전용)으로 전이했으며, 기존 컨트롤러는 HMD 전용 작업이나 비활성/차단 상태를 만나면 다음 프롬프트를 내보내지 않는다. 더 오래된 `max_unchanged_dispatches=3`도 커밋 변화가 없는 진단을 영구 중단시켰다.
- 해결: 큐에 `EXT16-011` **상시 ACTIVE** 반복 디버깅을 배치하고 `continuous_debug_policy.enabled=true`와 열 가지 코드/렌더링/차량별 검증 초점을 기록한다. 실기 전용 EXT16-006과 완료/차단된 기존 작업은 그대로 보존한다.
- **매 :00/:30 회차** GitHub 최신 SHA·이전 조사 증거를 승계하고 한 초점을 선정해 실제 소스 분석, 실패 경로/테스트 추적, 재현성 확보 및 가능한 안전한 실제 소스 수정을 한다. 실제 결함과 수정이 입증될 때만 소스 커밋 + 양성/음성 테스트 + 해당 SHA의 CI를 수행한다. 결함이 발견되지 않아도 실패한 가설과 새 근거/다음 가설을 정리하고 **코드를 임의로 바꾸지 않는다**.
- `EXT16-011`은 소스 커밋 유무, 기존 단일 이슈 BLOCKED, 다운로드 가능한 private 모델 자료 부재, 최종 HMD 검증 대기 때문에 자동 COMPLETE/BLOCKED 처리하거나 `active_work_id`를 006으로 보내지 않는다. 만약 잘못 처리되어도 최신 컨트롤러는 GitHub의 해당 항목을 복원하지 않고, **동일 ID** 임시 진단 작업으로 선택해 발송한다.
- 중복 없는 점수: 동일 변경사항·동일 TASK_ID 재확인·회차 반복·근거 보강·CI 재실행에 신규 점수는 주지 않는다. 매 회차 커밋을 강제하지 않는다.
- 60분 대화 교체 / 30분 시간창 별 중복 발송 방지 / 10분 최소 전송 간격 / 인증·프로젝트·rate-limit 보호는 그대로 유지한다. Chrome/브라우저 로그인 실패나 외부 인증 제한을 우회하지 않는다.
- 컨트롤러 구현은 `chat-controller-downloads@tools/chat-controller/v0.4/ferrari_external.py`이며 반영하려면 **Portainer 해당 스택의 이미지 재빌드**가 필요하다. GitHub 큐 EXT16-011 자체는 현행 컨트롤러가 이후 :00/:30에 읽을 수 있지만, **미발견/마일스톤 완료 후에도 무조건 계속 디버깅하는 복구 규칙**은 새 컨트롤러 이미지부터 적용된다.
