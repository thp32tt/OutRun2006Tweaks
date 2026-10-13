# 정방향 영문 기준 이미지 정책 — OutRun 2006 HD (2026-10-14)

## 사용자 결정

**원문이 뒤집힌 채로 한글을 제작하지 않는다.** 영어 원문 기준 PNG의 문자가 사람이 읽는 정방향이 되도록 먼저 보정하고, 그 정방향 기준 이미지에서만 ImageGen으로 한국어 문자를 생성한다. 원본 영문 PNG와 DDS는 수정하지 않는다.

## 실물 확인 결과

| 입력 파일 | 실물 상태 | ImageGen 입력 | 원본 PNG 좌표계 복원 |
|---|---|---|---|
| `Q012_D6DC1380_BASE_READABLE_NORMAL__r01c01__x0_y0__256x64.png` | `Continue?` 글자가 거꾸로 됨 | **세로 반전된 별도 정방향 PNG** | 결과를 세로 반전해 원래 타일 방향 복원 |
| `Q032_DCC7B488_BASE_READABLE_FLIPY...` | `Total Rank` 글자가 이미 정방향 | 기존 파일 그대로 | 변경 불필요 |
| `Q043_455717B2_KEYBOARD_READABLE_FLIPY...` | `CONTINUE`가 이미 정방향 | 기존 파일 그대로 | 변경 불필요 |
| 추가 `READABLE_FLIPY` 파일 | 파일명/방향 지도 기준 이미 읽는 방향으로 제공됨 | 기존 파일 그대로 | 원본 이미지 방향 변경 없음; 실제 게임 방향 별도 검증 |

`FLIPY`라는 문자열은 **원본 DDS → 사람이 읽는 미리보기**의 이력을 나타낼 수 있으므로 `FLIPY`를 보고 PNG를 다시 무조건 반전하지 않는다. 다른 `NORMAL` 유형이나 예상 밖 방향 표기를 만나면 자동 제작을 차단하고 실물 검증한다. 전체 파일의 각 문자를 개별 육안 검증한 것으로 표현해서는 안 된다.

## N100 결과

- 원본: `/home/chatgpt-runner2/work/image-src/inputs/A/HD_EN_TILES_20261014/`
- 정방향 보정 Q012:
  `/home/chatgpt-runner2/work/image-src/a_tile_batches/upright_sources/Q012_D6DC1380_BASE_READABLE_NORMAL__r01c01__x0_y0__256x64.png`
- 변환 증빙: 같은 디렉터리의 `.orientation.json`
- 전체 방향 매핑: `/home/chatgpt-runner2/work/image-src/a_tile_batches/UPRIGHT_SOURCE_MANIFEST_20261014.csv`
- 검증 요약: `/home/chatgpt-runner2/work/image-src/a_tile_batches/UPRIGHT_SOURCE_MANIFEST_20261014.summary.json`

Q012 원본 SHA256: `6497fa31804353844f703d1eb9355af0d6f7fdf345edadf860eb0eb93430ea2e`

Q012 정방향 보정 SHA256: `48cedd9621577ce8a5d97227150105a0d2f5092c8109abdfe4f25f0ac14c8ad5`

Q012 256×64 RGBA 유지. 상하반전 한 번을 적용한 결과를 다시 상하반전했을 때 **원본 픽셀과 알파가 바이트 단위 동일**함을 확인했다.

986개 원본 타일 중 PNG CRC/크기 검사 통과 **985개**, 오류 **1개(Q046 깨진 IDAT)**. 실물 샘플 확인 및 파일명/방향 지도 기준으로 985개 가운데 추가 상하반전 대상은 Q012 하나이며, 이미 읽기 방향인 984개는 원본 그대로 사용한다. 깨진 Q046은 복구 전 생성 대상에서 제외한다.

## 컨트롤러 처리

1. `ALL_TILE_MAPPING.csv`의 정확한 원본 해시/크기/CRC를 검사한다.
2. `tile_orientation_policy.resolve_upright_source()`에서 검증한 정방향 입력을 얻는다.
3. Q012만 `a_tile_batches/upright_sources/`의 생성형 참조 PNG를 사용한다. 984개 원본/미리보기는 그대로 사용한다.
4. 이미지 생성 요청에 **"한글은 영문 기준 이미지와 같은 정상 방향으로 출력, 뒤집지 않기"**를 넣는다.
5. 한글 이미지를 기존 DDS에 합성할 때는 `upright_to_source`를 먼저 적용하고, 그 다음에 원본 DDS 스프라이트 방향 검증을 거친다. 게임 자체 방향 검증 전에는 DDS QA를 PASS 처리하지 않는다.
6. 정방향 이미지 출력도 실제 ImageGen의 해상도·알파·문자 및 보호아트 QA에 합격해야만 다음 단계로 전달한다.

## 이 작업과 별개인 생산 차단 사유

초기 5파일 ChatGPT 입력은 하나의 합성 결과로 돌아왔다. 현재 `a_tile_batches/state.json`은 `OUTRUN-A-HD5-0001-20261014` 배치가 열려 있고 전송 증빙에는 `SUBMISSION_UNVERIFIED_DO_NOT_AUTO_RETRY`가 남아 있다. **정방향 참조 보정은 이 오래된 작업의 완료 증빙이나 5장 개별 결과 생성 성공을 의미하지 않는다.** 기존 기록을 지우지 않고 안전하게 보류한다. 별도의 1입력 1생성 이미지 생산 로직으로 교체 검증해야 한다.

관련 코드: `tile_orientation_policy.py`, `tile_batch_queue.py`, `audit_upright_sources.py`, `tests/test_tile_orientation_policy.py`.