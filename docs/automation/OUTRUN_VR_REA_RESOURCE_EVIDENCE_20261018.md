# OutRun 2006 VR HUD / UI 역분석 보고서
분석일: 2026-10-18 KST | 게임 원본 읽기 전용, GitHub 게임 소스 및 DLL 변경 없음
대상 경로: /home/chatgpt-runner/rea-input/outrun/outrun2006
분석 산출물: /home/chatgpt-runner/rea-analysis
검증: 정적 EXE와 패키지/DDS 근거 VERIFIED; Quest3 HMD RUNTIME_VALIDATION=UNTESTED.

## 게임 및 자산
- 게임 파일 3692개, 2.04 GiB; SZ 2153개, PAK 832개, DDS 243개.
- 게임 EXE SHA256 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3.
- GitHub vr-d3d9ex-focus/tools/analyze_outrun_exe.py: 원본 EXE 직접 CALL 569, 기준 호출 앵커 10/10, HUD 문자열 500 확인.
- Sprite SZ 패키지 141개를 zlib 해제해 내장 DDS 1623개 추출·해시 계산. Sprite 내부 DDS→교체 이미지 238개 경로(237 원본 엔트리) 정확 일치.
- DDS 243개 모두 이미지 디코딩 성공, 36장 컨택트시트 생성. 미매칭 5개 중 PMT 씬 전용 4개와 sumo_loading 4E9FE840 1개.
- 원본 파일명 너비/높이와 고해상도 DDS 헤더 상이 141개는 대부분 정규 2x/4x/8x upscale이며 결함 확정 아님. 63C91067=2048x2047 및 A05BF610=2047x2048 크기는 UV 경계 점검 후보.

## 실물 이미지와 원본 Sprite 패키지 XXH32 매핑
| 원본 그룹/인덱스 | XXH32 | 이미지 기능 |
|---|---|---|
| GAME_CVT / 0 | C4A2937B | 게임 캐릭터·그래픽 |
| GAME_CVT / 1 | 39229D64 | 레이스 HUD, TIME/연장시간·스테이지 안내 혼합 이미지 |
| GAME_CVT / 2 | A064FDFC | 레이스 속도·순위/숫자·HUD 도형 |
| GAME_CVT / 3 | 36895E6C | 빛/글로우 이미지 (실제 3D 렌즈광 호출과 직접 대응 미확정) |
| GAME_CVT / 4 | 78C4EB6B | 대화 풍선 |
| GAME_CVT / 5 | 7CE1CFC5 | NEXT MISSION |
| GAME_CVT / 6 | 2EA557B4 | NEXT ROUND |
| ETC_CVT | BF3EE5C6 | GO! / 3·2·1 스타트 카운트다운 |
| ETC_CVT | CBF8ECBF | GOAL / TIME OVER |
| ETC_CVT | 1F77CB88 | 게임패드 컨트롤 아이콘 |
| RANKING_CVT | C598919A | 랭킹 표 / 결과 패널 (6th/6 레이스 HUD와 다름) |
| SUMO_FE_CVT | D657C2EB | 메인메뉴 TIME ATTACK 제목 |
| SUMO_FE_CVT | C05E67EF | GOAL A~E 메뉴 텍스트 |
| SUMO_FE_CVT | 31C58963 | 모드 선택 텍스트 |
| SELECTOR_CVT | 다수(31개) | Ferrari 차량명/차량선택 카드/화살표/배경 |
| FONT | 다수(9개) | 문자·숫자 글꼴 아틀라스 |
분류 신뢰도: 패키지/XXH32/이미지 일치는 확정. 게임 프레임에서 정확한 XY/UV/animation index는 실행 시 trace 없이는 미확정.

## 원본 실행 파일의 CALL RVA와 화면 기능
RVA는 EXE 로드 베이스 0x400000에 더하면 원본 VA. 정확한 호출 목록은 static/OR2006C2C_EXE_ANALYSIS.json 참고.
| 기능 | 원본 caller RVA | 원본 렌더러/목적 | VR 의도 공간 |
|---|---|---|---|
| 연장시간 Sprite | 0x9898E, 0x98A36, 0x98AC6 | sprani_play_ae_auth 0x29530 | StageExtensionTime / ScreenHud |
| 연장시간 숫자 | 0x989AD, 0x98A89, 0x98A10 | 0x973C0 또는 0x974E0 숫자 경로 | ScreenHud |
| 순위 선행 요소 | 0xB9DA6 | sprani_play_ae_auth | 6th/6 ScreenHud |
| 순위 뒤따르는 숫자·클립 | 0xB9Fxx~0xBA0xx | put_clip_sprite 0x2D280 | ScreenHud |
| 공통 HUD 문자 | 0xBAAA0, 0xBAAEA | clip sprite / sprani alpha | caller별 provenance |
| 자동차 위 3D 순위 | 0xBB0FB,0xBB133,0xBB16C,0xBB1A5,0xBB21F,0xBB241,0xBB271,0xBB2BC,0xBB2D0 | Calc3D2D + put_clip_sprite/sprani | ProjectedWorldMarker2D |
| TimeAttack | 0xBE300..0xBEA40 | DispTimeAttack2D | ScreenHud |
| GOAL timer | 0xBEA40..0xBEB20 | NaviPub_DispTimeAttackGoal | ScreenHud |
| 렌즈 중심 | 0xD3A5 → 0xC980 → 0xC993 | DrawObjectAlpha centre | 3D WorldEffect, HUD 아님 |

## 렌더링 처리 순서 및 버그 위험
1. Sprite/Sprani 로드 → 원본 XST/임베드 DDS → xxHash XXH32(bytes, length, 0) → hash_원본W×원본H.dds 교체.
2. hooks_textures.cpp는 UITextureReplacement/SceneTextureReplacement가 활성일 때 원본 DDS W/H 대비 교체 W/H 비율을 sprite_scales에 기록. put_sprite_ex, put_sprite_ex2에서 ScopedSprArgsScale / ScopedSprArgs2Scale로 원본 좌표를 스코프 내 변환한 뒤 즉시 원복한다.
3. +TIME: 3개 sprite + 3개 숫자 producer를 묶어야 하지만, SpriteNode queue와 D3DXSprite::Draw~Flush/End 지연 GPU 실행이 개입하면 원래 ScreenHud owner/scope가 물리 GPU draw에서 사라질 수 있다. 실제 지연 배치 이용 여부는 HMD trace로 입증 필요.
4. 6th/6 (HUD_RANK)는 고정 HUD, 4th/5th 차량 위 마커는 실제 3D 위치 Calc3D2D/원본 FVF 0x142/투영 world object. 두 경로 결합 금지.
5. ESC pause shell + 옵션 화살표는 pause_menu_eye_affine.hpp exact-owner opt-in. 3D world 경로 재투영/이중 변환 금지. F11 메뉴는 ImGui 외부 오버레이로 native game sprite와 다름.
6. 하늘·광원은 SkyGlow/WorldBillboard/SceneEffect 원본 WVP/c64/pose/양안 GPU로 확인해야 한다. 단순 DDS 분석으로 하늘이 헤드락되는 원인은 단정할 수 없음.
7. R84 기본 물리 dispatch: stereo_renderer_r33.cpp의 Draw/Reset/Present와 R30/R29 stereo path를 기준으로 per-eye duplicate, poseEpoch, shader epoch, render target/viewport/depth restore 추적.

## HMD 테스트에 필요한 자료
- VRHudInspector 활성화 후 게임 시작/연장시간 이벤트/6th·4th 순위/ESC/F11/하늘 수평-회전 상황에서 로그 수집.
- OutRun2006Tweaks-hudtrace.csv에서 return_rva/call_rva/sprite args/priority/mode/stage를 확인; 최신 게임 DLL/host SHA, R84 main variant 확인.
- Quest3 좌·우 화면 녹화 및 OutRun2_VR_ANALYZE_*.zip 제공. 사용자가 제공한 게임 설치본 내 OutRun2006Tweaks.log는 2025-04-17 기록이므로 현재 HMD 실행 증거 아님.
- REA/Ghidra 전체 EXE 분석은 N100 225초 제한에서 timeout 발생; 이 보고는 프로젝트 EXE 전용 분석기(569 CALL, 10/10)와 원본 Sprite/이미지 패키지 정적 분석에 기반함.

## 생성한 상세 자료
- inventory.json: 파일 전수 인벤토리
- dds_audit.csv/json: 243 DDS 크기/압축/배율
- sprite_dds_map.csv/json: 141 Sprite SZ / 1623 원본 DDS → 외부 DDS
- static/OR2006C2C_EXE_ANALYSIS.json/md: 569 direct CALL + 500 HUD strings
- atlas/*.png (36장), atlas/index.json: 243개 모든 DDS 시각화

참고 코드 및 문서: thp32tt/OutRun2006Tweaks (vr-d3d9ex-focus) / src/hooks_textures.cpp / src/vr/game/sprite_uv_transaction.hpp / src/vr/game/render_semantics.hpp / src/vr/d3d9/pause_menu_eye_affine.hpp / src/vr/d3d9/stereo_renderer_r33.cpp / docs/VR_EXE_HUD_INSPECTOR.md / docs/DX9EX_VISUAL_REPAIR_LENS_EXTTIME_20261015.md / docs/DX9EX_R62_R84_RANK_CALLPATH_AUDIT_20261017.md.
## Automatic developer handoff and work queue mapping (2026-10-18)
The user explicitly requests actual functional C++ fixes, not reviews, based on the N100 local original-game asset research. This is input evidence for existing FEATURES, not a new feature claim, lease, TASK_ID or scoreboard event.
**Do not upload or commit any original copyrighted executable, game asset, extracted resource, decompiled C or full copyrighted game content** to GitHub; only small fingerprint summaries, offsets, manifests and independent mod source fixes. REA/Ghidra decompile output remains N100-local at `/home/chatgpt-runner/rea-analysis/ghidra/`. Long-running headless decompilation does not block existing actionable DX9EX features.
- DX9EX:VIS:EXTENDED_TIME: test exact sprite three calls 0x9898E/0x98A36/0x98AC6 + glyph three calls 0x989AD/0x98A89/0x98A10; resource `spr_SPRANI_GAME_CVT_Exst.sz`, `39229D64`; source→queue→D3DX Flush/End→R84 right-eye owner; confirm or disprove deferred batch hypothesis.
- DX9EX:VIS:HUD_GAMEPLAY: `39229D64`, `A064FDFC`, font atlas. Follow `DispRank` first 0xB9DA6 and later clip sprites 0xB9Fxx..0xBA0xx independently. 6th/6 SCREEN_HUD is NOT vehicle-attached rank.
- DX9EX:VIS:RANK_MARKERS: Calc3D2D projected rival anchors 0xBB0FB/0xBB133/0xBB16C/0xBB1A5, clip calls 0xBB21F/0xBB241/0xBB271/0xBB2BC/0xBB2D0, original FVF 0x142; project per eye with live marker owner. Maintain physical vehicle world attachment.
- DX9EX:VIS:ESC_MENU: preserve distinct native ESC shell/option arrows and correct pause stereo plane. Do not conflates this with F11 external ImGui.
- DX9EX:VIS:F11_MENU: test standalone ImGui overlay shell/font/input/hitbox, independent of game pack.
- DX9EX:VIS:MAIN_MENU and DX9EX:VIS:VEHICLE_SELECT: `SUMO_FE_CVT` 111 DDS and `SELECTOR_CVT` 31 DDS; verify original sprite UV, nonuniform crops and renderer aspect/letterbox; R84 native menu aspect must not stretch/crop or make white sprites.
- DX9EX:VIS:LENS_FLARE_CENTRE: centre 0xD3A5→0xC980→0xC993 3D owner; outer discs and `SkyGlow` protected. Do not infer that bright DDS `36895E6C` itself proves the world lens producer.
- DX9EX:VIS:GOAL_PROGRESS: separate original `CBF8ECBF` GOAL, `BF3EE5C6` 3-2-1 and ranked final scoreboard `C598919A`; trace GOAL time and result producer scopes.
**Execution:** On each new/continued C DX9Ex dispatch, recover existing active lease/TASK_ID/feature/symptom first from live GitHub run record; never increment work IDs on retry/rollover. Choose ONE whole defect and implement actual source correction in R84 independent R29-R33 plus owner producer and tests. Do not mark fixed from asset mapping, static call paths or CI alone. Preserve DX11 independence, DXVK freeze, input/FFB/SkyGlow/world positives, exact-SHA final CI/HUD Inspector/Domain/Full Source gating. Quest3/VDXR `RUNTIME_VALIDATION=UNTESTED` until matching physical runtime test. Do not restart or terminate an existing active Ghidra process from an auto-dev dispatch; consume only durable results.
**Local evidence:** `/home/chatgpt-runner/rea-analysis/sprite_dds_map.json`, `dds_audit.json`, `static/OR2006C2C_EXE_ANALYSIS.json`, `atlas/index.json`, `ghidra/progress.json`. The local game EXE SHA is `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.
