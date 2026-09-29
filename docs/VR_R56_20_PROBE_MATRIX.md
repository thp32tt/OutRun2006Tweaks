# R56 20-Probe HUD / Rank Ownership Matrix

## 목적

R55 HMD 결과에서 일반 HUD, 화면의 `6th/6 POSITION`, 차량 위 순위 마커가 동일한 렌더 경로가 아님이 확인됐다. R56은 한 DLL 안에 20개의 런타임 probe를 넣어 같은 바이너리/같은 코스/같은 시점에서 producer → queue semantic → R30 final draw ownership을 단계별로 분리한다.

R56은 production 통합용 수정이 아니라 **경로 판별용 candidate**다. 결과가 확인되기 전까지 `vr-d3d9ex-focus`에 merge하지 않는다.

## 역분석 근거

Canonical replacement EXE: SHA-256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`, PE32/x86, image base `0x00400000`.

확인된 anchor:

- `Calc3D2D`: RVA `0x49940` — 차량 world 위치를 screen 좌표로 투영.
- `sub_4BAD20`: RVA `0xBAD20` — rival rank marker producer.
- `RankMarker_Truncate`: RVA `0xBB046`.
- 1~3등 `sprani_play_ae_auth_alpha` callsites: `0xBB0FB`, `0xBB133`, `0xBB16C`, `0xBB1A5`.
- 4등 이후 `put_clip_sprite` callsites: `0xBB21F`, `0xBB241`, `0xBB271`, `0xBB2BC`, `0xBB2D0`.
- 화면 rank/POSITION `DispRank` semantic range: `0xB9E00..0xBA100`; existing exact adjustment anchors `0xB9F3A`, `0xB9F5E`, `0xB9F81`, `0xB9FD0`, `0xB9FFC`, `0xBA01E`, `0xBA035`, `0xBA052`.
- canonical SpriteNode queue: RVA `0x2D762` per-node, `0x2DCB4` exit. RVA `0x2D734` entry는 과거 crash evidence 때문에 hook 금지.

원본 UI-scaling 코드 자체가 1~3등과 4등 이후를 서로 다른 API로 그린다. 따라서 R55에서 1~3등과 4~6등이 서로 다르게 보인 현상은 실제 producer 구조와 일치한다.

## 20개 후보

| # | Variant | 직접 건드리는 층 | 기대 판별 |
|---|---|---|---|
| 01 | R56_01_ZERO | R55 final coordinate baseline | 일반 HUD zero-disparity 기준 |
| 02 | R56_02_SCALE35 | R55 final coordinate baseline | 일반 HUD 35% 반응 기준 |
| 03 | R56_03_WORLD35 | R55 finite world plane | 일반 HUD head-lock 기준 |
| 04 | R56_04_RANKZERO | R55 exact billboard final | 기존 rank zero 기준 |
| 05 | R56_05_POSITION_XP96 | DispRank producer | 6th/6가 오른쪽 이동하면 producer 확정 |
| 06 | R56_06_POSITION_XM96 | DispRank producer | 05와 반대면 강한 확증 |
| 07 | R56_07_POSITION_XS35 | DispRank producer X | 중앙 기준 X 35% 반응 |
| 08 | R56_08_POSITION_XCENTER | DispRank producer X | X=320 강제 반응 |
| 09 | R56_09_RANK13_XP96 | sprani 1~3 producer | 1~3등 visible producer 확인 |
| 10 | R56_10_RANK13_XM96 | sprani 1~3 producer | 09 대칭 확인 |
| 11 | R56_11_RANK13_YM72 | sprani 1~3 producer | Y 이동으로 오인 배제 |
| 12 | R56_12_RANK13_CENTER | sprani 1~3 producer | 320,208 강제 강한 시각 proof |
| 13 | R56_13_RANK46_XP96 | put_clip_sprite 4+ producer | 4~6등 visible producer 확인 |
| 14 | R56_14_RANK46_YM72 | put_clip_sprite 4+ producer | Y 이동으로 오인 배제 |
| 15 | R56_15_RANK46_CENTER | put_clip_sprite 4+ producer | 320,208 강제 proof |
| 16 | R56_16_RANK13_AS_HUD | 1~3 queue semantic | WORLD→SCREEN_HUD 전달 여부 |
| 17 | R56_17_RANK46_AS_HUD | 4+ queue semantic | WORLD→SCREEN_HUD 전달 여부 |
| 18 | R56_18_RANK46_NEXTDRAW | 4+ producer one-shot semantic | producer→D3D draw lifetime/thread 판별 |
| 19 | R56_19_POSITION_NEXTDRAW | DispRank one-shot semantic | POSITION producer→D3D draw lifetime 판별 |
| 20 | R56_20_ALLSCREEN_RAW | R30 XYZRHW + shader final owner | 여전히 안 바뀌는 요소는 R30 밖/composite 후보 |

## 결과 해석

- 05~08이 `6th/6 POSITION`을 움직이면 `DispRank` 계열 producer가 맞다. 이 경우 generic HUD semantic보다 producer-specific semantic/tagging으로 고치는 것이 우선이다.
- 05~08이 모두 무반응인데 20이 반응하면 producer 추정은 틀렸지만 visible output은 R30이 소유한다.
- 05~08과 20이 모두 무반응이면 `6th/6`은 별도 sprite/composite/render-target 경로 우선순위가 높다.
- 09~12만 1~3등에 반응하고 13~15만 4~6등에 반응하면 원본의 `sprani` / `put_clip_sprite` 분리가 HMD visible output까지 그대로 유지되는 것이 확정된다.
- 13~15가 반응하지만 17/18이 무반응이면 4~6 producer는 맞고 semantic이 queue/draw 사이에서 유실되거나 R30 owner가 아니다.
- 20까지 무반응인 visible element는 R30의 XYZRHW/shader screen-space 경로 밖이다. 다음 역분석은 alpha/translucent composite, render target, later presentation blit을 우선한다.

## 테스트 절차

`START_HERE_VR_TEST.cmd` 하나만 실행한다. GUI에서 01→20을 같은 코스/같은 카메라로 짧게 실행한다. 모든 세션은 VariantId별 로그 경로로 분리된다.

최소 관찰 항목:

- 일반 HUD 크기/고정 여부
- `6th/6 POSITION` 위치/크기/좌우 분리/head-follow
- 차량 위 1~3등 위치/좌우 분리/head-follow
- 차량 위 4~6등 위치/좌우 분리/head-follow
- FPS/Hz 및 fallback 증가 여부

테스트 후 생성되는 `OutRun2_VR_ANALYZE_*.zip`만 업로드하면 VariantId와 runtime probe를 기준으로 비교한다.
