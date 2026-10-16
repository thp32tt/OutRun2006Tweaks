# Quest OutRun APK → Windows PC 포팅 구조 감사: 실행·자산·입력 경계

작성: 2026-10-16 KST · 신규 정적 분석 · 사용자 소유 APK · 대상 저장소 `thp32tt/OutRun2006Tweaks` / `vr-d3d9ex-focus`

## 목표와 범위

APK 원본에 존재하는 게임 로직, x86 guest 번역, Quest/Android 플랫폼 서비스, 렌더러, 자산 및 입력/오디오 경계를 밝혀 **PC 재포팅 가능한 설계 단위**로 분리한다. ARM64 전체를 Windows로 기계적으로 이식하거나 기존 Win32 게임 EXE를 동일 바이너리로 간주하지 않는다. 비공개 APK/ELF/EXE/자산/역컴파일 C 코드는 Git에 추가하지 않는다.

분석 원본: N100 `/home/chatgpt-runner/apk/outrun2.apk` (1,491,573,201 B). ARM64 `liboutrun_quest_core.so` (21,959,856 B, SHA-256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`). Ghidra/ARM64 선행 분석은 [QUEST_N100_NATIVE_DECOMP_FOCUS_20261016](QUEST_N100_NATIVE_DECOMP_FOCUS_20261016.md) 참조.

## 1. 신규 검증된 바이너리 패키징

APK ZIP central directory 검사:
- ZIP 엔트리 3,909개; 이 중 `assets/` 파일 3,901개, 자산 비압축 합계 3,307,643,353 B (APK 자체는 압축 1.49 GB).
- `assets/game/` 자산: Sound 900개, Stage 847, OCP 543, hd-menu-v4 449, Sprite 142, OSO 129, Media 127, BK 121, Common 102, Ghosts 92, Scripts 80, Cars 64, Anims 63, RVT 60, Sprani 51, Chr 40.
- 자산 확장자: `.sz` 2,157, `.pak` 832, `.dds` 448, `.rec` 181, `.bin` 153, `.ogg` 68, `.tgt` 32, `.qmv` 4, `.bik` 1, `.ini` 1, `.exe` 1.
- `assets/game/TestApp.EXE`를 APK에서 바이트로 읽고 DOS/PE/COFF 헤더 검증: 파일 크기 **962,560 B**, SHA-256 `4876712f501640951d892069db826e431aede3e4ab87686fc1d556e26df9fec1`; `MZ` / `PE\0\0`, Machine `0x014c` (Intel 386), PE32 magic `0x10b`, ImageBase `0x400000`, Entry VA `0x401000`; `.text` RVA `0x1000`, virtual size **5,820,416 B** vs raw size **954,880 B**; `.rsrc` RVA `0x58e000`.
- `assets/game/outrun2006.ini`(105 B), `README.html`, `MANUAL.PDF` 등 PC 표면을 갖고 있다.

**중요:** EXE의 `.text` 가상 공간이 파일 내 실데이터보다 현저히 크므로 **이 EXE가 플레이 가능한 완전한 원본 Windows 게임이라고 결론내릴 수 없다**. 실행 가능성, 임포트 테이블, 코드 세그먼트 재구성, 원본 게임 EXE와 해시/섹션 대응은 별도 검증해야 한다. 사용자 PC의 기존 설치본 실행 파일을 이 파일로 교체하지 말 것.

## 2. 새 함수 전수 목록에서 드러난 x86 번역 계층

N100 `apk/_static_out/porting_audit/all_functions.jsonl`의 **고유·정의됨·size>0 함수 14,341개**를 재분류:
- 최상위 네임스페이스: `outrun` 5,189, `or2x86` 3,819, `std` 4,206. (위 숫자는 첫 토큰에 따른 상호 배타 분류; 다른 문자열 포함 건수와 섞어 계산하지 않는다.)
- `or2x86::tr_bulk` 2,103, `or2x86::tr_network` 1,573, `or2x86::tr_network_cars` 140 → 합계 **3,816개** 주소별 번역 함수. `F_4d2820(or2x86::Cpu&)` 같은 함수는 guest x86 주소 표기와 CPU 상태 인자를 갖는다.
- `or2x86::Cpu` 구조를 입력으로 받는 번역 함수들이 실행되는 것으로 강하게 시사되지만, **어떤 guest 메모리/레지스터를 언제 읽고 쓰는지, 전체 원본 EXE가 얼마나 구현돼 있는지는 아직 복원되지 않았다.**

여기서 포팅 의사결정: 게임/물리/AI를 독자적으로 전부 다시 쓰기 전에 **기존 Windows x86 게임 실행부를 기준(오라클)으로 두고 APK 추가 기능의 경계 및 guest 주소 ↔ PC 루틴 대응표**를 만든다. APK가 Windows EXE의 직접 대체품이라는 의미는 아님.

## 3. 분석된 실행 계층 / 확인 정도

```text
[Android entry]  android_main 0x2daf60 (8,280 B)  [symbol and ELF body confirmed]
       │  *전체 호출 순서는 미복원, PLT/간접 호출 미해결*
       v
[Runtime orchestration]
  outrun::runtime::load_game_data       0x2c6904 (2,312 B)
  outrun::runtime::attach_pc_scene      0x2c720c (2,548 B)
  outrun::runtime::open_frontend        0x2c7c4c (2,208 B)
  outrun::platform::run_native_runtime  0x329d44 (164 B)
       |
[original PC game semantics / guest translation]
  or2x86::Cpu + tr_bulk / tr_network / tr_network_cars
  PcRaceMemory / NativeRuntimeContext / driving::* / Frontend*
       |
       +-- Assets: RetailAssetStore, parse_loader_asset_pack, retail_asset_lookup
       |   (lookup 0x377198, 2,456 B: 직접 호출에 inflate_exact 존재)
       +-- Input: XrRig::input, VirtualWheel::update, runtime::input_sample,
       |   native_pc_input_update_406fa0 / PcInputDevice
       +-- Sound: native_race_sound_invoke, RaceSoundState, PcSound::tick_42f330
       +-- Scene: PcSceneRenderer / PcD3D9Device / GlD3D9Device
             -> GLES targets, buffers, state, shaders
             -> XrSessionHost per-eye XR images / frame submit
```

**신뢰도 구별:** 위 개별 함수와 주소는 ELF 심볼/함수 길이에서 직접 확인. `retail_asset_lookup` → `inflate_exact`는 이 함수의 BL 직접 호출로 확인. 세로 연결선은 **추정된 구성요소 의존관계**이며 함수 간 완전한 호출 그래프/실행 순서가 아니다. 별도 BL 스캐너는 필수 PLT 호출을 `unknown_or_PLT:0x122...`로 남겼으므로 이런 호출을 확정된 내부 호출로 꾸미지 않는다.

## 4. PC 포팅 전 반드시 풀 문제 (게이트)

1. **PE/guest 주소 교차표:** `TestApp.EXE`를 원본 Windows 설치본과 섹션·import·entry stub·유효 명령 분포까지 대조. `F_<guestVA>` ↔ `OR2006C2C.exe`/원본 루틴의 실제 VA/기능 관계 확정. PE32의 code virtual/raw 차이를 먼저 해명. **게이트:** 20개 시드 guest 주소의 bytes/루틴 분류 및 근거.
2. **Android bootstrap 호출 그래프:** `android_main`, `run_game`, `load_game_data`, `attach_pc_scene`, `open_frontend`에서 PLT 재배치와 간접 호출을 복원해 생성·tick·파괴 순서 확인. **게이트:** 실행 주기/각 소유자/오류 종료 원인.
3. **게임 루프 이중 실행 차단:** 원본 PC 물리·AI·프론트엔드·음향은 프레임당 한 번만 실행, XR stereo는 렌더/제출만 per-eye. **게이트:** 같은 입력의 프레임 간 차량 상태/타이머 비교.
4. **자산 호환 계층:** `RetailAssetStore`, loader/course pack, `.pak/.sz/.dds/.rec/.qmv/.bik` 종류별 로더/압축·해시·경로 결정을 파악. **게이트:** 원본 아카이브 해시/CRC와 선택 자산 lookup 결과를 확인하되 원본 데이터는 공개 저장소 밖에 보존.
5. **입력 통합:** `XrRig::input` / `VirtualWheel` → `NativeInputState` / `PcInputDevice`를 추적하여 기존 Win32 SDL3/DirectInput/FFB와 충돌 없이 mapping. **게이트:** steering, throttle, brake, menu, controller recenter, FFB 단일 소유자.
6. **오디오/저장:** `PcSound`/RaceSound, AAudio/MediaNDK, `Ghosts`/`SaveGame`를 별도 게이트로 검사; 오디오 재생 오너 및 타이밍/세이브 호환.
7. **렌더러:** 기존 [VR_ARCHITECTURE](../VR_ARCHITECTURE.md)와 [Quest 집중 분석](QUEST_N100_NATIVE_DECOMP_FOCUS_20261016.md)의 확인된 eye pose/FOV, sphere culling, HUD producer, shadow, flare만 선택적으로 이식. Quest GLES 구현을 DX9Ex/DX11에 통째로 붙이지 않는다.

## 5. 재현 파일·작업 결과

N100에서 이번 작업에 생성(바이너리/자산 복제 없음):
- `apk/_porting_architecture_scan_20261016.py`
- `apk/_analysis_focus/porting_architecture_inventory_20261016.json`
- `apk/_porting_bootstrap_trace_20261016.py`
- `apk/_analysis_focus/porting_bootstrap_calls_20261016.json`

분석 산출물은 APK를 실행하거나 실측하지 않은 정적 결과. 과거 Ghidra decompilation 실패/함수 경계 중첩은 여전히 유효한 제한. **Windows build/Quest 3 실기 `RUNTIME_VALIDATION=UNTESTED`**, Windows 구동 성공이나 완전 PC 포팅을 주장하지 않음.

## 다음 조사 순서

우선순위는 **PE import/guest 주소 매칭 → PLT 포함 bootstrap call graph → input & asset loader 포맷 → simulation/tick 경계 → audio/save → renderer parity**. 이 단계가 끝나야 전체 Windows PC 포팅의 노력 범위 및 테스트 가능한 최소 루프를 확정할 수 있다.
