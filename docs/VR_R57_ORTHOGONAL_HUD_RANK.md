# R57 Orthogonal HUD / Rank Root-Cause Matrix

## 결론

R56의 20개 후보는 원인 공간을 넓게 덮었지만 01~04가 R55 기준선을 반복하고, 더 중요한 두 구조를 완전히 분리하지 못했다.

R57은 다음 두 원인에 집중한다.

1. 화면의 `6th/6 POSITION`은 하나의 HUD draw가 아니라 서로 다른 SpriteNode 타입의 합성이다.
2. 차량 위 순위는 최종 렌더 단계까지 3D billboard로 남지 않는다. 원본 EXE가 `Calc3D2D`에서 차량 기준점을 먼저 2D 화면좌표로 투영한 후 sprite를 큐에 넣는다.

따라서 기존 `WORLD_BILLBOARD` 하나로 둘을 처리하는 모델은 실제 EXE 구조와 맞지 않는다.

## Canonical EXE 근거

Canonical replacement EXE SHA-256:
`68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`

### DispRank / 6th/6 POSITION

`DispRank`는 최소 두 종류의 sprite producer를 사용한다.

- RVA `0xB9DA6` -> VA `0x429530`
  - animation/sprani 계열
  - 최종적으로 `put_sprite_ex2` RVA `0x2D0C0`
  - SpriteNode `kind_C=1`, `SPRARGS2`
- 8개 direct `put_clip_sprite` calls:
  - `0xB9F3A`
  - `0xB9F5E`
  - `0xB9F81`
  - `0xB9FD0`
  - `0xB9FFC`
  - `0xBA01E`
  - `0xBA035`
  - `0xBA052`
  - 이들은 `put_sprite_ex` 경로로 SpriteNode `kind_C=0`, `SPRARGS`를 사용한다.

따라서 R56에서 8개 clip call만 움직인 테스트는 POSITION 전체를 대표하지 못했다.

### 차량 위 1~6등

`sub_4BAD20`은 차량 기준점을 얻은 뒤 RVA `0xBAEE2`에서 `Calc3D2D` RVA `0x49940`을 호출한다.

`Calc3D2D`의 실제 식은 다음 형태다.

```
screenX = viewX / -viewZ * a1
screenY = viewY / -viewZ * a2
outZ    = viewZ
```

따라서 호출 직후 값으로 원래 view-space 기준점을 복구할 수 있다.

```
viewX = screenX * (-viewZ) / a1
viewY = screenY * (-viewZ) / a2
viewZ = outZ
```

이후 `sub_4BAD20`은 이 값을 640x480 sprite 위치로 변환하고:

- 1~3등: `sprani_play_ae_auth_alpha`
  - `0xBB0FB`, `0xBB133`, `0xBB16C`, `0xBB1A5`
- 4등 이후: `put_clip_sprite`
  - `0xBB21F`, `0xBB241`, `0xBB271`, `0xBB2BC`, `0xBB2D0`

로 큐에 넣는다.

즉 이것은 **world billboard draw**라기보다 **world point를 CPU에서 screen projection한 뒤 그리는 2D marker**다.

## 기존 R30의 구조적 충돌

기존 R30 shader 경로는 exact `WORLD_BILLBOARD` semantic이 있어도 final projection class가 `Perspective3D`일 때만 `WorldBillboard` owner로 승격했다.

하지만 차량 rank는 `Calc3D2D`에서 이미 화면 좌표로 평면화되므로 final draw가 orthographic/flat sprite처럼 보이는 것이 정상이다.

R55에서 `worldBillboard=0`이었던 현상과 이 조건이 일치한다.

## R57 수정 구조

### Exact producer semantic

`put_sprite_ex` / `put_sprite_ex2` 내부의 stack backtrace 추론에 의존하지 않는다.

producer wrapper가 `ScopedProducerSemantic`으로 정확한 의미를 설정하고, 해당 호출이 만든 SpriteNode에 직접 전달한다.

### ScreenHud

DispRank의 kind=1과 kind=0을 각각 또는 함께 `SCREEN_HUD`로 직접 태그한다.

이렇게 하면 6th/6 POSITION 전체를 동일한 finite world-fixed HUD plane으로 처리할 수 있다.

### ProjectedWorldMarker2D

차량 rank 전용 semantic `PROJECTED_WORLD_MARKER_2D`를 추가했다.

`Calc3D2D`에서 복구한 `viewX/viewY/viewZ`를 SpriteNode semantic metadata로 전달한다.

최종 draw에서는 원본 sprite의 크기/내부 offset을 다시 만들지 않는다. 대신 원래 중앙 카메라에서의 projected NDC와 각 OpenXR eye의 projected NDC 차이만 계산해 sprite 전체에 이동량으로 더한다.

이는 다음을 보존한다.

- 원본 rank sprite 크기
- 원본 숫자 조합/offset
- 원본 alpha/animation
- 차량에 붙는 실제 깊이 기반 양안 disparity

그리고 잘못된 generic billboard reconstruction을 피한다.

## 10개 직교 테스트

| # | Variant | 가설 |
|---|---|---|
| 01 | POSITION_KIND1_HUD35 | POSITION의 sprani/SPRARGS2 부분만 정확히 잡혔는지 |
| 02 | POSITION_KIND0_HUD35 | POSITION의 put_clip/SPRARGS 부분만 정확히 잡혔는지 |
| 03 | POSITION_ALL_WORLD35 | 두 타입 전체를 합친 실제 POSITION 수정 후보 |
| 04 | RANK_ALL_AS_HUD | 차량 rank draw owner 확인용 의도적 HUD 대조군 |
| 05 | RANK_PROJECTED_IPD | Calc3D2D 깊이 + 상대 eye IPD/FOV 재투영, 주 해결 후보 |
| 06 | RANK_PROJECTED_HEAD | 05 + head inverse; Calc3D2D가 이미 head-sync인지 판별 |
| 07 | RANK_PROJECTED_13 | 1~3 sprani 경로만 새 방식 |
| 08 | RANK_PROJECTED_46 | 4~6 clip 경로만 새 방식 |
| 09 | RANK_PROJECTED_ZERO | semantic owner는 새 방식, 재투영만 끔 |
| 10 | RANK_PROJECTED_TRACE | view depth / per-eye delta 계측, 화면은 원본 유지 |

## 우선 테스트 순서

모든 10개를 처음부터 다 돌릴 필요는 없다.

1. POSITION: 01 -> 02 -> 03
2. 차량 rank: 05 -> 06
3. 위 결과가 섞이거나 1~3/4~6 차이가 남을 때만 07 -> 08
4. owner/metadata 확인이 필요할 때만 09 -> 10

즉 첫 HMD 사이클은 최대 5개면 핵심 결론에 도달하도록 설계한다.

## 통합 규칙

R57은 진단 + 수정 candidate다. HMD 결과 전에는 `vr-d3d9ex-focus`에 merge하지 않는다.
R56 PR은 기록용으로 유지하되 R57이 후속 candidate다.
