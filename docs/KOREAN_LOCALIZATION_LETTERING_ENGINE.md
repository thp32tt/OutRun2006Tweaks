# 글자 형태와 효과를 분리하는 제작 구조 — 2026-10-11

기존 A/B/C1/C2/C3, 단일 큐, 스케줄, CLEAN 라이브러리를 유지한다.
변경 지점은 P2 글자 제작과 새 공식 DDS의 게시 검사다. 기존 바이트의 승인을
이 문서만으로 취소하거나 같은 DDS를 다시 만들지 않는다.

## 실제 생산 순서

1. 독립 승인된 정확 SOURCE/CLEAN을 재사용한다.
2. 계열에 따라 `native_small`, `vector_title`, `layered_metal`을 선택한다.
   작은 HUD/메뉴는 최종 픽셀 크기로 렌더하고 획/자소 내부 공간을 보정한다.
   큰 제목은 필요한 한글 문구의 벡터 윤곽을 편집한다. 금속은 윤곽 확정 뒤
   앞면/하이라이트/측면을 별도로 만든다. 폰트 변경이나 가로 늘이기만 반복하지 않는다.
3. 효과 없는 단색 글자 비교를 100/75/50%와 읽는 방향으로 관찰한다.
   A/B가 실제 획, 내부 공간, 비례, 기울기, 가독성을 기록한 뒤 GEOMETRY_READY로 둔다.
   이것은 생산자 단계 판정이며 독립 C 승인/계열 확산 허가가 아니다.
4. 원본 크기의 RAW L-mode alpha PNG를 `geometry`로 저장한다. 흰 단색 검토본과
   editable SVG 또는 native renderer 설정/font SHA/license를 기존 자산 폴더에 보존한다.
   face PNG의 알파는 geometry와 정확히 같아야 한다. rim/extrusion/shadow/highlight는
   각각 투명 RGBA PNG로 저장하고 아래 공통 합성기로 lettering을 만든다.
5. CLEAN 합성 및 저장 DDS 검수는 기존 production_pixel_guard/C/C3/실게임 절차를 따른다.

```sh
python tools/localization/compose_lettering.py --repo . --recipe path/to/lettering.json --output path/to/LETTERING.png
python tools/localization/production_pixel_guard.py --changed-since BASE_SHA
```

## 레시피 형식

모든 입력 ref는 기존 `{path: repository-relative-path, sha256: full-SHA256}` 형식이다.
`source` ref는 final manifest의 source와 동일해야 한다. 암묵적 리사이즈는 없다.

```json
{
  "version": "separated-lettering-v1",
  "coordinates": "native_raw",
  "route": "vector_title",
  "source": {"path": "...", "sha256": "..."},
  "geometry": {"path": "...", "sha256": "..."},
  "geometry_recipe": {"path": "...", "sha256": "..."},
  "geometry_review": {"path": "...", "sha256": "..."},
  "layers": [
    {"role": "rim", "input": {"path": "...", "sha256": "..."}},
    {"role": "face", "input": {"path": "...", "sha256": "..."}}
  ]
}
```

layers는 뒤→앞 순서이며 각 role은 한 번만 쓴다. face 필수, highlight는 마지막에만
놓고 face 영역 안에 있어야 한다. layered_metal은 face/highlight/extrusion이 필수다.
geometry_review에는 status=GEOMETRY_READY, reviewer=A 또는 B, route,
source_sha256, geometry_sha256, observations의 stroke/counterspace/proportions/slant/readability
실제 관찰문과 evidence 배열의 무손실 비교 PNG ref를 넣는다. 빈 관찰이나 시험 fixture를
실제 제작 승인으로 사용하지 않는다. 해시 결합은 저자 독립성이나 시각 품질을 증명하지 않는다.

새/변경 공식 DDS의 final manifest에 `lettering_recipe` ref를 추가한다.
기존 CPU 게시 전 `--changed-since`와 push CI가 동일 공통 합성 결과와 lettering PNG를
바이트 디코드 후 비교한다. 누락/변조/옛 geometry 검토는 게시 검사 실패다.
`--manifest` 단독은 기존 기계 검사이며 새 게시 요건 전체를 대신하지 않는다.
과거 후보 재검수와 미승격 trial 보존은 계속 가능하다. 미승격은 공식 생산 통과가 아니다.

## 판단 기준과 적용 순서

영문/한글 전체 픽셀 수와 문자열 폭의 일치율을 일괄 합격선으로 쓰지 않는다.
문자 수/구조가 다르므로 획 두께 대비 높이, 내부 공간, face/rim 비율,
원본의 화면 강조 수준과 가독성을 함께 판단한다. 원문 경계 초과/겹침 금지는 유지한다.

q121 가속 페달: 흰 글자면부터 보정하고 남색 테두리는 별도 제작한다.
q154: 알파 혼합으로 내부 공간 결함을 고치지 말고 native 획/공간을 수정한다.
q176: 폭 72%를 무조건 늘이지 말고 넓고 굵은 계열의 실제 한글 윤곽을 다듬는다.
q060: 금속 앞면/반사광/측면을 분리한다. PSD 효과 추출은 출력 재현 검증이 필요하다.
이들은 아직 검증된 새 레시피가 아니다. 대표 저장 DDS의 독립 C 수락 전 확산 금지.

본 변경은 공통 합성기와 게시 경로 연결이다. 자동 벡터 디자인, 새 한글 DDS 완성,
글꼴 개선 실증, C3 또는 게임 PASS를 뜻하지 않는다. RUNTIME_VALIDATION=UNTESTED.
