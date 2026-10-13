# 이미지 생성 정책 수동 적용 절차

## 2026-10-13 Portainer GitHub 정책 전달 — 최신 사용자 운영 경로

- **GitHub 정책 SSOT → 기존 Portainer Git Stack → 사용자 수동 Pull and redeploy**. 표준 경로에서 로컬 Docker CLI staging은 필수가 아니다. 세부: `docs/OUTRUN_PORTAINER_GITHUB_DELIVERY_20261013.md`.
- q217 시험에 한해 **이미지 코드가 GitHub의 PNG 업로드 패치를 실제 포함**하고 Portainer Git Repository/ref/Compose path가 확인되면, 기존 Stack의 Additional paths에 `docker/localization-production/portainer-git-q217-a-smoke.override.yml`을 적용할 수 있다. 단독 Compose로 새 스택을 띄우지 않는다.
- q217 단건 `/data/imagegen/inputs/A/...png` 및 `pending_A.json` 실제 바이트·SHA는 Git 정책 pull과 별개로 영구 볼륨에 공급해야 한다. 없으면 작업은 SOURCE_REFERENCE_NOT_BOUND.
- 실험 종료 후 `docker/localization-production/portainer-git-normal.override.yml` 또는 정상 Git Compose 정책으로 복귀한 다음 사용자가 Portainer에서 수동 Pull and redeploy.
- **현재 저장소에는 Portainer Stack의 정본 base Compose 파일을 확인하지 못했다.** 따라서 위 override가 실제 Stack에 이미 연결되어 있다거나 GitHub push만으로 ImageGen이 실행된다고 주장할 수 없다. 이미지/Stack 연결이 확인될 때까지 `UPLOAD_RUNTIME=UNTESTED`, `IMAGEGEN_E2E=UNTESTED`.

---



대상: localization recovery 컨트롤러만. 사용자 2026-10-12 수동 배포 지시.
이 문서와 Git 커밋은 실행 중 컨테이너를 변경하지 않는다.
`docker/localization-production/Dockerfile`은 CPU plate 작업 이미지이며 ChatGPT 브라우저
컨트롤러가 아니다. 이 이미지 자체에 내장 ImageGen이 있다고 가정하지 않는다.

## 레거시 비Git형 Portainer Stack만을 위한 CLI 스테이징 (Git-connected Stack 표준 절차 아님)

1. 검토한 정확한 커밋으로 checkout한다. 운영 app/controller.py, Compose 원본,
   prompt 디렉터리, 현재 image ID와 /data·/logs를 백업한다. 기존 백업 브랜치와 Git 이력을 유지한다.
2. 로컬 사전 검사:
   `python -m unittest discover -s tools/localization -p test_hd_imagegen_policy.py -v`
3. 기존 Portainer 배포 호스트에서만 수동 실행:
   `python tools/localization/deploy_plate_controller.py --root . --revision FULL_40_CHAR_SHA --stage`
   PyYAML과 Docker가 필요하다. 기존 BASE 이미지와 stack `/pdata/compose/54`를 대상으로 한다.
   다른 설치는 경로를 먼저 확인한다. 스크립트는 이미지 빌드와 Compose 준비만 수행한다.
4. 기존 Portainer stack을 사용자가 수동 재배포한다. 독립 docker run으로 앱을 띄우지 않는다.
   이름 충돌이 있으면 해당 컨트롤러만 유지보수 시간에 정리하고 볼륨은 삭제하지 않는다.
5. `/opt/outrun/production_revision`과 A/B/C1 prompt를 확인한다. 활성 탭은 A/B/C1,
   C2 없음. 원래 대화 기록은 삭제하지 않는다. AUTO_SEND=true인지 확인한다.
6. 단건 원본 PNG 업로드/전송 메시지 첨부 → 내장 이미지 생성 → 실제 PNG 다운로드 →
   원본 SHA/승인 문구/알파 확인 → CLEAN 합성 → 원본 방향·포맷·mipmap의 시험 DDS →
   저장본 재디코딩 순서를 확인한다. 결과를 C1이 독립 검사한다.
7. 실제 controller 코드/로그가 **0:A, 10:C1, 30:B, 40:C1** (KST)을 지원하는지 확인한다.
   SCHEDULE_MINUTES와 CHAT_SLOTS만으로는 충분하지 않다. round-robin이면 역할 배정이
   다를 수 있으므로 운영 controller의 dispatch를 별도 확인한다. 설정 변경은 검증 PASS가 아니다.
8. 2026-10-12 16:39 KST 사용자 지시로 AUTO_SEND=true가 기본이다. 다시 staging해도
   true를 유지한다. 별도 활성화 단계는 없으며 컨테이너 배포·게임 설치·정식 릴리스는 사용자 수동이다.

## 신규 PNG 자동 첨부 — 수동 배포 전 준비

`docs/KOREAN_LOCALIZATION_CONTROLLER_PNG_UPLOAD_20261012.md`의 `/data/imagegen/inputs/` 및 `pending_A.json`/`pending_B.json`에 실제 SHA·승인 프롬프트가 포함된 원본 HD PNG를 준비한다.

수동 `--stage`는 컨트롤러의 실제 `send_message()`에 Playwright 파일 선택 및 첨부 프리뷰 검증을 적용한 이미지로 빌드한다. 기존 기본 Docker 이미지의 소스가 알려진 구조와 다르면 **패치 자체가 실패**하며 운영 재배포로 넘어가지 않는다. A/B는 원본 바인딩이 없으면 `SOURCE_REFERENCE_NOT_BOUND`로 전송 보류, C1은 기존 QA 경로를 사용한다. 기존 C2 상태는 별도 파일로 보존하며 탭을 다시 열지 않는다.

`AUTO_SEND=true`라는 사용자 승인 값은 유지한다. 이것이 PNG 업로드 또는 ImageGen 통합 PASS를 의미하지 않는다. 수동 재배포 후 실제 ChatGPT composer 썸네일, 본문 메시지, 실제 이미지 출력 바이트를 단건 확인한다. 검사 전에는 `UPLOAD_RUNTIME=UNTESTED`이다.

## 현재 제한

고정 프롬프트/조립기와 staging 회귀는 검증 가능하다. 실제 브라우저 첨부, 내장 ImageGen 호출,
다운로드, runtime scheduler, C1→legacy 승인 consumer 이관, 실제 게임은 미검증이다.
새 role 후보는 TEST_ONLY이며 C2 승인 토큰으로 위장하지 않는다.
운영 실패 시 기존 image/Compose/prompts를 백업에서 복구하고 동일 named volume을 유지한다.
소스 상태·사용자 실게임 불량·기존 후보를 리셋하지 않는다.
