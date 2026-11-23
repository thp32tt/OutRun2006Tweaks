# Ferrari16 외부 모델 자동개발 실행 계획 (2026-11-23)

SSOT: `thp32tt/OutRun2006Tweaks@automation/ferrari16-external-20261123` 의 `docs/automation/FERRARI16_EXTERNAL_AUTODEV_QUEUE.json`. 컨트롤러: 같은 저장소 `chat-controller-downloads`, Portainer `outrun-chat-vr` 전용.

- **실행**: 매시 KST :00, :30, 단일 A 슬롯. 새 작업 ID를 매번 생성하지 않고 active_work_id를 완료할 때까지 승계한다. 동시 Git 작업 금지.
- **1순위**: 현재 기본 브랜치에서 깨진 모델 로더/양안 스테레오/PBR/유리 및 v0.03 대비 회귀 수정. 정상 release 덮어쓰기 금지.
- **2순위**: 정확 차종 + 고품질 모델/재질/노멀맵 16대 단위 정적 검증, 다이얼/속도/RPM/기어 연동, UV/투명도/메시 구조 개선.
- **3순위**: 변경된 코드와 변환 도구 테스트 후 Windows CI에서 x86 game+x64 host 패키지 exact-SHA 검증. 실패하면 같은 ID에서 원인을 수정한다.
- **4순위**: 테스트 ZIP·원복 스크립트·SHA·로그 경로 준비. Quest 3 실기 없이 최종 PASS/성능 PASS 주장 금지.

## 작업 반복 규칙

(1) GitHub 최신 active_work_id, source HEAD, 전차종 manifest·이전 작업 증거 확인 → (2) 중복 작업 판별 → (3) 실제 소스/모델 제작·오류 수정 → (4) 변경 영역 검사 → (5) 단일 material commit+증빙 → (6) 필수 final CI → (7) 큐 item status 및 next work ID 원자적 커밋. 실패/롤오버는 같은 ID. 고정 작업 한 번에 계획·검토만 반복 금지. 3회 연속 Git 진전 없음이면 추가 메시지 대신 `external_waiting_for_progress`로 대기.

## 안전 경계

- 기존 DX11/DX9Ex/DXVK, Model2, 한글화, 구형 `imsi1` 운전석 리워크 **자동 재활성화 금지**. 외부 모델링 전용 스위치에서만 작동한다.
- N100 우선 사용 금지: GitHub + ChatGPT 자체 로컬 우선. 원본/대용량 사설 자산이 N100에만 있을 때 최소 호출; 반복 빌드·압축·검색은 Actions/로컬에서.
- 328 GTS/575 Superamerica/F430 Spider 낮은 디테일 exact 후보를 기본 고품질 donor 위로 자동 강제승격 금지; Testarossa Spider 차종 검증 선행.
- 공개 저장소에 상용 모델·게임 원본·개인 사진·비밀키 업로드 금지. 재배포 권한 미확인 자료는 private evidence로 취급.
- 실제 HMD 결과가 없으면 `RUNTIME_VALIDATION=UNTESTED` (또는 `WAITING_USER_HMD`), 정적 검증과 별도로 기록.

## Portainer 반영 방법

`https://github.com/thp32tt/OutRun2006Tweaks.git` / `refs/heads/chat-controller-downloads` / `tools/chat-controller/v0.4/docker-compose.portainer-vr.yml`을 **Pull and redeploy / Rebuild image** 해야 코드·프롬프트가 반영된다. Docker 소켓 접근 불가 시 GitHub 코드 변경은 live 재배포로 간주하지 않는다. 상태 `http://192.168.0.48:8787/status`에서 `external_model_autodev_enabled`, target branch, enabled, actual last send를 재확인할 것. `AUTO_SEND=true`라도 Project URL/계정 로그인 검증 실패 시 발송 차단.
