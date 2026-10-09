# 생산부터 수렴시키는 한글 DDS 제작 계획 — 2026-10-09

적용 브랜치: `korean-localization-recovery-20260928`.
사용자 요청: 서체 불일치·플레이트 잔상·반대 기울기의 반복 리워크를 생산 단계에서 차단한다.
이 문서가 기존 계약의 생산량/동일 호출 완료 권고와 충돌하면 **이 문서의 선행 품질 조건이 우선**한다.
기존 A/B 소유권, C1/C2, C3, 6회 호출 일정, 단일 asset_queue와 실게임 판정은 유지한다.

## 확인된 원인과 바꿀 행동

| 실제 근거 | 생산상의 문제 | 앞으로의 행동 |
| --- | --- | --- |
| C332 q060 B331: 인접 주황 아트 8,892픽셀 소실 | 이전 한글 후보도 이미 훼손되어 이전본 대비 검사와 제목 bbox 검사는 통과 가능 | 원본→CLEAN/최종 보호영역 검사와 이전본→신규 변경범위 검사를 각각 시행 |
| REWORK_ESCALATIONS의 q172/q214/q219 독립 반복 반려 | 크기·shear·색만 조절해 같은 서체/금속 효과 실패를 반복 | 해당 계열 대표 1개를 원본 윤곽/효과에 맞춰 재구성하고 C의 계열 검증 전 확산 금지 |
| C310/C328 q098: 효과 불일치와 원문 잔상은 서로 다른 결함 | 합성본 한 장에서 여러 원인을 한꺼번에 판단 | PLATE, LETTERING, COMPOSITE, persisted DDS를 분리하여 최초 실패 단계만 고침 |
| 현행 C HOLD 자료와 APPROVALS 요구 | 증거 미완료를 새 DDS 생산으로 해결하려 하거나 증거만 계속 생성 | 픽셀 결함과 증거 부족을 구분하고, 같은 SHA·같은 누락은 재검수/재생산 완료로 세지 않음 |

근거는 기존 role_C 보고서, `REWORK_ESCALATIONS.json`, `KOREAN_LOCALIZATION_EVIDENCE_GATE.md`에 있다.
이 진단은 새 후보/새 게임 화면이 통과했다는 뜻이 아니다. 기록된 실패에서 도출한 제작 개선이다.

## 1. 계열 대표를 먼저 완성한다

- 계열: 작은 HUD, 작은 회색 메뉴/도움말, 이탤릭 선택 제목, 금색 입체 제목, 은색/크롬 제목, 쇼룸 메타데이터.
- 소유 lane의 P0/P1 순서를 지키되 **한 제작법당 미검증 대표 후보는 1개**만 유지한다.
  C를 기다리는 동안 다른 독립 계열의 안전한 작업은 가능하다. 전체 생산을 중단하지 않는다.
- 기존 정확 SHA의 정상 후보/원본/CLEAN/서체 관찰을 재사용한다. 양식 변경 때문에 정상 DDS를 다시 만들지 않는다.
- 대표 검증은 기존 C lane이 담당한다. 한 아틀라스 일부 셀만 검증했다면 `FAMILY_PILOT_SCOPED`로
  범위·원본·후보·제작법 해시와 실제 관찰을 기록한다. 이는 전체 아틀라스 C PASS/배포 승인이 아니다.
  아틀라스의 다른 7개 셀 등이 미완료라는 이유로 정상 대표 셀의 제작법까지 계속 새로 만들지 않는다.
- 계열 검증 전에 같은 방법으로 여러 DDS를 양산하지 않는다. 검증 후에는 폰트/렌더 코드/효과 설정을
  해시로 고정하고 동일 계열에 재사용한다. 각 DDS의 자체검수와 독립 C/C3는 계속 필요하다.

## 2. 제작 레시피를 고정한다

기존 role_A/role_B 작업 폴더에 `recipe.json`을 둔다. 새 작업 큐/컨트롤러 상태기계가 아니다.

필수 내용: canonical source 경로·revision·SHA, 전체 셀 목록과 보호 대상, 한국어 정본 문구,
font 파일·SHA·라이선스·실제 glyph coverage, 렌더러/버전/코드 SHA, 네이티브 ppem/힌팅/AA 방식,
줄별 높이·기준선·자간·획·내부 공간, 색/그라데이션/외곽선/음영, RAW↔readable 변환,
영문/한글 대응 획의 위·아래 좌표, 제거/보호/효과/수정범위 마스크, 이전 반려 원인과 이번 변경점.

- 기본 폰트가 없으면 fallback으로 계속하지 않는다. 정본 모든 글자의 실제 glyph coverage를 확인한다.
- 작은 HUD는 목표 픽셀 크기로 직접 렌더하고 획/내부 공간을 확인한다. 큰 한글 래스터를 반복 축소·확대하지 않는다.
- 벡터/윤곽 렌더는 원본 계열에 맞는 최종 크기에서 검증한다. 필요하면 한 번의 명시적 다운샘플만 사용하고
  필터·배율을 기록한다. 오래된 저해상도 한글 확대는 금지한다.
- 금속/크롬은 일반 굵은 고딕에 임의 그림자를 붙여 대체하지 않는다. 윤곽·면·하이라이트·측면을 분리해
  원본에 맞춰 벡터/수동 재구성한다. 맞출 수 없으면 MANUAL_RECONSTRUCTION_REQUIRED로 둔다.
- AI 이미지 생성은 배경 복원 초안/참고에 한정한다. 정확한 한글 획·투명 글자층·보호영역·DDS 규격은
  결정적 렌더/마스크와 실제 저장 파일 검사로 확정한다. 새 도구 사용 자체를 개선 성과로 세지 않는다.
- 렌더 코드/폰트/효과/변환을 바꾸면 영향받는 대표만 다시 검증한다. 근거 없는 전체 승인 무효화는 하지 않는다.

## 3. 세 번의 생산 정지점

### P1 — 글자를 올리기 전에 CLEAN 확정

원본 HD DDS에서 각 글자와 외곽선/그림자의 제거 마스크를 구한다. OCR bbox는 위치 힌트다.
같은 사각형 안에 있는 이웃 글자·주황 아트·프레임도 보호 마스크로 별도 지정한다.
이전 한글 CLEAN을 정상 원본으로 간주하지 않는다. 이미 없어진 보호 아트는 정본에서 복원한다.

SOURCE/CLEAN만 검토하여 PASS/FAIL/HOLD와 실제 PNG 관찰을 저장한 **뒤** 글자를 렌더한다.
투명 스프라이트의 제거 영역은 CLEAN alpha=0을 검사한다. 유색/그라데이션/질감 플레이트에는
이 조건을 적용하지 않는다. 그곳은 주변 연속성·원문 효과 잔존을 시각적으로 검토한다.
마스크 의미가 불명확하거나 원문 획/효과 잔상이 보이면 여기서 고친다. 한글로 덮지 않는다.

### P2 — 투명 글자층과 방향 확정

레시피의 폰트로 투명 글자층만 만든다. 최종 source bbox/양수 여백/클리핑 규칙은 그대로 적용한다.
읽는 방향에서 `dx = top.x - bottom.x`를 기록한다(좌표의 y는 아래로 증가).
원본 오른쪽 기울기는 양수다. Pillow 역변환 행렬의 부호와 동일시하지 않는다.
RAW 저장용 flip/회전을 마지막에 적용하고, 다시 읽는 방향으로 되돌려 원본과 비교한다.
각 앵커의 대응 획을 표시한 PNG가 필요하다. 서로 다른 획/끝점이나 임의 0으로 통과시키지 않는다.
방향 일치만으로 충분하지 않다. 기울기 크기·원근·획/카운터·서체 느낌도 대표와 시각 비교한다.

### P3 — 합성 및 저장 DDS 확정

CLEAN 위에 투명 글자/정당한 효과만 합성한다. 원본 보호영역과 이전본 수정범위는 각각 검사한다.
저장 DDS를 다시 디코드하고 SOURCE/CLEAN/LETTERING/FINAL과 이웃 셀까지 100/75/50%, RAW/FLIP-Y,
검정/회색/흰색 배경 및 모든 authored mip에서 본다. 제목만 잘라 인접 손실을 숨기지 않는다.
부분 수정은 부분 완료로만 기록한다. 전체 셀 목록이 미완료면 whole-atlas REWORK/HOLD를 유지한다.

## 4. 실행 가능한 픽셀 차단기

`tools/localization/production_pixel_guard.py`는 다음을 실제 픽셀로 계산한다.

- source→CLEAN/최종 보호 픽셀 손실(이전 후보가 이미 훼손되어도 탐지)
- 제거 마스크와 보호영역 충돌, 이전본 대비 허용 범위 밖 변경
- 투명 플레이트의 미세 alpha 잔상, 글자층/합성의 효과 마스크 밖 변경
- 명시적 원본 보호 아트 복원과 새 글자 침범의 구분
- 정확 SHA, 네이티브 크기, DDS 헤더/파일 길이, 비압축 DDS의 의도한 합성과 저장 디코드 일치
- 측정 앵커의 읽는 방향 기울기 반전/잘못된 직립

종료 0과 `MECHANICAL_PASS_VISUAL_REVIEW_REQUIRED`는 **수치 선행조건만 충족**했다는 뜻이다.
불투명 플레이트 잔상, 잘못 그린 마스크, 미관, 전체 셀 누락, mip 품질, 실제 게임을 자동 판정하지 않는다.
기존 10단계 생산/8항목 시각 검사·C/C3를 대체하지 않는다. 압축 DDS의 블록 밖/보호 픽셀 차이는
허용 오차로 감추지 않는다. 원본 블록 보존 또는 맞는 인코더를 사용하고 실패하면 중단한다.

모든 입력은 `{path: 저장소 상대 경로, sha256: 전체 해시}`다. 이전 DDS는
`git_revision: 전체 40자리 commit SHA`를 추가하여 Git의 이전 바이트를 읽을 수 있다.
현재 candidate에는 git_revision을 쓰지 않는다. 원본이 외부에만 있으면 정확 원본을 materialize하고
해시를 검증한다. 게시 시 검사 입력은 저장소에서 재현 가능해야 하며 credential/개인 경로를 넣지 않는다.

manifest 구조(아래는 설명이며 PASS fixture가 아님):

```text
version: production-pixels-v1-20261009
stage: plate 또는 final
coordinates: native_raw
inputs: source, baseline, clean (final에는 candidate, lettering 추가)
masks: removal, protected, edit, transparent, restore (final에는 effect 추가)
regions (final): [{id, source_anchors:{top:[x,y],bottom:[x,y]},
                   candidate_anchors:{top:[x,y],bottom:[x,y]}, anchor_evidence:{path,sha256}}]
```

이미지는 전체 네이티브 RAW DDS/PNG다. 마스크는 같은 크기의 L-mode 0/255 PNG다.
`transparent`는 실제 투명 배경인 제거 영역만 지정하며 그 외에는 빈 마스크다.
`restore`는 원본 보호 아트를 복원하는 `protected ∩ edit` 부분만 지정하며 필요 없으면 빈 마스크다.
`removal`과 `protected`는 겹치지 않는다. full-image 마스크를 최종 차이에서 역산해 검사 통과용으로 만들지 않는다.
SOURCE 기반 마스크 검토를 기존 PLATE 관찰에 남긴다. 모든 포맷·mip 시각 검사도 기존 QA 기록에 남긴다.

```sh
python tools/localization/production_pixel_guard.py --manifest PLATE_MANIFEST.json --report PLATE_MACHINE.json
# 실제 PLATE 시각 PASS 뒤 렌더/저장한다.
python tools/localization/production_pixel_guard.py --manifest FINAL_MANIFEST.json --report FINAL_MACHINE.json
python tools/localization/production_pixel_guard.py --changed-since BASE_COMMIT_SHA
```

새/변경 hd_candidates DDS를 게시하려면 final manifest를
`localization/graphics/worker_results/production_manifests/<candidate_SHA256>.json`에 저장한다.
CPU worker는 commit **전** 변경 후보를 재검사한다. 독립 CI는 직접 push된 변경도 검사하며 누락/실패면 빨간 상태다.
CI 실패는 이미 push된 커밋의 자동 롤백이 아니고 branch protection 설치를 의미하지 않는다.
로컬/API 생산도 같은 명령을 게시 전에 실행해야 한다. 기존 미변경 DDS는 새 양식 때문에 재제작하지 않는다.
trial DDS는 기존 role_A/B 작업 폴더에 보존 가능하나 생산 후보 PASS나 배포 대상이 아니다.

## 5. 무한 리워크를 끝내는 재시도 규칙

- 처음 실패한 단계를 고치고, 이미 정확 해시로 통과한 전단계는 재사용한다. 수정이 그 입력을 바꾸면 관련 단계만 무효화한다.
- 같은 근거 있는 결함이 새 후보에서 재발하면 기존 METHOD_CHANGE_REQUIRED 규칙을 적용한다.
  새로운 폰트/윤곽/플레이트/인코더 중 무엇을 바꿨고 왜 해결되는지 기록한다. 숫자만 다른 동일 방법은 금지한다.
- 한 호출에서 같은 방법의 조정 시험은 최대 2회다. 실패 시 정확 원인/마지막 바이트/실패 단계와
  다음 다른 방법을 기록하고 다른 안전한 소유 항목을 진행한다. 다음 호출에서 횟수를 초기화해 같은 방법을 반복하지 않는다.
- 폰트/플레이트/마스크가 미확정인 경우 'DDS 하나 생산' 목표 때문에 억지로 PASS하지 않는다.
- C HOLD는 누락 목록을 한 번에 반환한다. producer는 그 목록을 한 묶음으로 완결한다.
  같은 SHA와 같은 누락뿐이면 새 반려/생산/완료로 재보고하지 않는다.
- 작업량 지표는 신규 DDS 수와 별도로 **최초 독립 C 수락률, 동일 원인 재발, 현재 승인 수,
  사용자 실게임 종결 수**를 기록한다. JPG/커밋/시도/점수 증가를 패치 진척으로 표시하지 않는다.

## 다음 자동 호출에 적용

1. A/B는 최신 Git 계약과 이 문서를 읽고 소유 P0/P1 및 rework_triage를 확인한다.
2. q060 계열은 C332의 인접 아트 보존을 포함해 PLATE부터, q193은 기존 부분 개선을 보존하며
   남은 셀과 대표 제작법 검증을 구분한다. 동시 실행 중의 B332 trial/다른 lane 변경을 덮어쓰지 않는다.
3. q172/q214/q219는 기존 escalation에 따라 소스 기반 입체/크롬 대표 제작법을 변경한다.
4. C는 새로운 대표 후보를 먼저 검증하고 같은 SHA HOLD 반복보다 정확 누락 해소를 우선한다.
5. 게임 회귀는 해당 수정 DDS/빌드의 사용자 실제 재검 전까지 OPEN, `RUNTIME_VALIDATION=UNTESTED`다.
   이번 계획 변경은 DDS 생산이나 게임 결함 해결 건수로 계산하지 않는다.

## 외부 자료에서 가져온 범위 (2026-10-09 직접 확인)

- [mcpads/create-kr-patch-template](https://github.com/mcpads/create-kr-patch-template): 선언한 원본/채택 입력과
  Expected Write 검증 개념을 두 기준(source 보호/previous 수정범위)으로 적용. ROM 패처/Rust 실행 구조는 도입하지 않음.
- [FreeType 현재 API — Sizing and Scaling](https://freetype.org/freetype2/docs/reference/ft2-sizing_and_scaling.html):
  명목 크기만으로 실제 glyph 픽셀 치수를 보장하지 않으므로 최종 크기 실제 렌더 결과를 측정.
- [Microsoft — TrueType hinting](https://learn.microsoft.com/en-us/typography/truetype/hinting):
  작은 픽셀 크기의 윤곽/그리드 정렬을 고려. 모든 UI에 동일 폰트/힌팅이 맞는다는 의미는 아님.

외부 코드를 복사하지 않았으며 특정 폰트 라이선스/새 압축 형식 도입을 승인하는 문서가 아니다.
