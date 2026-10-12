# A/B 컨트롤러 PNG 자동 첨부 — 2026-10-12

저장소: `thp32tt/OutRun2006Tweaks`, 브랜치: `korean-localization-recovery-20260928`.
배포는 사용자 수동이다. 이 코드는 사용자의 기존 Portainer 컨테이너를 자동 변경하지 않는다.

## 구현

- `tools/localization/controller_png_attach.py`: /data 내부 작업별 PNG SHA-256·PNG 구조/CRC·원본 DDS SHA·승인 프롬프트 검증, Playwright `set_input_files` 또는 파일 선택창 이용, **신규로 보이는 첨부 프리뷰 확인 후에만** 전송 허용.
- `tools/localization/patch_controller_png_upload.py`: 기존 Docker 이미지의 `/opt/outrun/app/controller.py`를 이미지 빌드에서만 수정. A/B/C1 세 슬롯, A :00/C1 :10/B :30/C1 :40, C2의 기존 상태 별도 보존. 알 수 없는 기존 소스 구조라면 빌드 FAIL.
- `tools/localization/deploy_plate_controller.py`: 패치를 수동 staging 이미지 생성에 포함한다. 자동 Portainer 재배포 없음.
- A/B는 원본이 없거나 SHA/첨부 프리뷰 검증에 실패한 경우 `SOURCE_REFERENCE_NOT_BOUND`로 보류한다. **PNG 없이 텍스트만 전송하지 않는다.** C1에는 PNG 첨부를 강제하지 않는다.
- 컨트롤러 watchdog은 A/B의 오래된 작업 프롬프트를 텍스트로 재전송하지 않는다.

## 사용자 수동으로 넣을 입력 파일

컨트롤러의 기존 `/data` 볼륨 내부에 다음처럼 파일을 준비한다.

```
/data/imagegen/
  inputs/A/q001_READABLE.png
  inputs/B/q002_READABLE.png
  pending_A.json
  pending_B.json
  sent/                 # 전송 성공 시 자동 기록
```

`pending_A.json` 예제 (실제 SHA/문구/자산별 값으로 바꿀 것):

```json
{
  "role": "A",
  "task_id": "OUTRUN-A-Q001-ORIGINAL-20261012",
  "png": "A/q001_READABLE.png",
  "png_sha256": "원본 PNG 파일의 64자리 소문자 SHA-256",
  "source_dds_sha256": "정본 영문 DDS의 64자리 소문자 SHA-256",
  "prompt": "첨부한 HD 영문 원본에서 SELECT CAR만 '차량 선택'으로 바꾸고, 다른 모든 아트와 투명도를 보존하세요."
}
```

B는 `role=B`, `pending_B.json`, `inputs/B/...`를 사용한다.
`png`는 `inputs/` 아래의 상대 경로여야 하며 외부 디렉터리 이동·심볼릭 링크 탈출은 차단한다. SHA와 프롬프트는 이전에 승인된 변환 manifest를 바탕으로 제작한다. 예제의 SHA 문자열 그대로는 사용 불가하다.

- 성공적으로 ChatGPT 메시지를 전송하면 `sent/{role}_{task_id}.json` 기록이 생겨 같은 작업 재발송을 차단한다. 이 기록은 **메시지 송신**만 뜻하며 이미지 생성/다운로드/DDS 성공은 뜻하지 않는다.
- 같은 자산을 다시 생성하려면 **새 TASK_ID와 검증된 새 작업 manifest**를 사용한다. 기존 `sent/` 기록이나 게임 불량 상태를 초기화하지 않는다.
- `AUTO_SEND=true`는 사용자의 별도 명시 지시를 유지하지만, A/B에서는 입력 파일이 빠져 있으면 전송하지 않는다.
- 이미지 생성 결과의 실제 바이트 다운로드, 원본 CLEAN 합성, DDS 인코딩 및 C1/C3/실게임 검증은 **아직 이 첨부 모듈의 수행 범위 밖**이다.

## 검증 구분

- 로컬 단위 테스트: `python -m unittest discover -s tools/localization -p test_controller_png_upload.py -v`.
- 실제 기본 Docker 이미지의 `controller.py`를 별도 격리된 소스 복사본에 적용해 `ast.parse`/멱등성/A-B-C1 스케줄 패치 여부를 시험할 수 있다.
- 수동 배포 후 **실제 Chrome 브라우저에서 업로드된 프리뷰와 ChatGPT 요청/응답을 검증**하기 전까지 `UPLOAD_RUNTIME=UNTESTED`, `IMAGEGEN_E2E=UNTESTED`.
- 원본 DDS 해상도·방향·포맷, CLEAN/승인 게이트와 사용자의 실게임 OPEN은 기존 정책 그대로 유지한다.

배포 운영 절차: `docker/localization-production/MANUAL_IMAGEGEN_ROLLOUT.md`.
