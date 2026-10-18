# OutRun 2006 렌더링 실행 체계 — 원본 REA/Ghidra → R84 대응

## 1. 전체 경로 요약

```text
Win32 game loop 0x00417B20
  └─ original frame scheduler / drawing orchestration 0x00449050
       ├─ scene D3D9 render flows (indirect object dispatch, numerous callbacks)
       ├─ +TIME original HUD producer 0x00498670
       │    ├─ sprite anim 0x00429530 ... 0x0042D0C0 (queue type 1)
       │    └─ time/numeric 0x004973C0 / 0x004974E0 ... 0x0042CFE0 (queue type 0)
       ├─ 6th/6 screen rank 0x004B9D80  [different from car world anchor]
       ├─ car-attached rank 0x004BAD20 → Calc3D2D at 0x00449940
       └─ priority queue consumer 0x0042D710 (conditional early 0x004C50A0)
            ├─ Begin 0x00429C60 : ID3DXSprite Begin
            ├─ queue type 0 : 0x0042A0A0 → ID3DXSprite Draw, later End/Flush
            │                  └─ flagged path 0x0042C0F0 → device DrawPrimitiveUP
            ├─ queue type 1 : 0x0042A3A0 / 0x0042A800 → device DrawPrimitiveUP
            └─ End 0x00429F60 : ID3DXSprite End (deferred GPU submission)
       └─ D3D9 BeginScene/EndScene/Present in game loop
                ↓
R84 DX9Ex: orig GPU calls / hooks_textures.cpp → GameSemantic SpriteNode tags
    → R30 fixedFn XYZRHW first exits or R33 Draw* dispatcher
    → R33 HUD / world / raw / R29 fail-closed paths
    → left+right eye target + depth / viewport / pose / c64 / shader guards
    → x64 OpenXR host compositor [host trace currently not correlated]
                ↓
Quest3 actual optical image [UNTESTED]
```

원본은 한 개 모노 D3D9 장면을 그린다. 스테레오 양안 기능은 오직 모드 구현(R84/Host)에서 추가된다. 따라서 원본 REA만으로 좌우 눈 성공 여부를 결론낼 수 없다.

## 2. D3D9 COM 메서드 식별 근거

원본 Ghidra C는 같은 API를 서로 다른 형태로 표현한다:
- `(**(code **)(*DAT_0089bd60 + 0x14c))`: 포인터의 **바이트 오프셋** `0x14c / 4 = index 83` → `IDirect3DDevice9::DrawPrimitiveUP`
- `(*(code *)(*DAT_0089bd60)[0x53])`: 메서드 **인덱스 83** → 같은 `DrawPrimitiveUP`
- `+0x164` 는 index 89 `SetFVF`, `+0x170` 는 index 92 `SetVertexShader`.
- COM 인덱스 81~84 = DrawPrimitive / DrawIndexedPrimitive / DrawPrimitiveUP / DrawIndexedPrimitiveUP; 37=SetRenderTarget, 41=BeginScene, 42=EndScene, 43=Clear, 65=SetTexture.
- 원본 `DAT_0095B218`은 D3DXSprite 추정 COM 객체이며 +0x20=Begin, +0x24=Draw, +0x28=Flush, +0x2C=End. *주소와 객체 타입을 바탕으로 한 정적 복원*: 핸들 재바인딩 또는 래핑 시 런타임 확인 필요.

**주의:** Ghidra의 함수 호출 의사코드는 원본 x86 push 수/호출 규약을 잘못 표시할 수 있다. 원본 E8 CALL 주소, RVA, 함수 시작 VA를 구별한다. 원본 0x00498670의 비연속 케이스에는 정규화 어셈블리에서 생략됐지만 실제 기계어로 확인한 스프라이트 호출도 포함된다.

## 3. 하위 시스템별 발견

### A. 프레임·GPU 상태·드로우

- `0x00417B20`: 윈도 메시지/원본 게임 프레임·장치 실패 등. 
- `0x00449050`: 스테이지별 렌더 스케줄링 + 우선순위 렌더 큐 소비. 조건에 따라 `0x004C50A0` 경로도 존재.
- 직접 D3D9 Draw를 포함하는 여러 원본 함수가 의사코드 호출자 0개로 표시된다. 이는 기능이 없음을 의미하지 않는다. 객체 가상 호출이나 포인터 테이블을 REA XREF/메모리/진입 추적으로 해결해야 한다.
- R84: `stereo_renderer_r30.cpp` / `stereo_renderer_r33.cpp` / `stereo_renderer_r29.cpp` / `src/vr/game/universal_draw_trace.hpp`.
- **조사:** CPU call_serial ↔ 실제 R84 Draw ID, vertex format, shader, RT, stencil, texture, draw HRESULT, pose epoch, 리셋 후 복원.

### B. 스프라이트·애니메이션

- `0x00429530` → `0x00428A10` → `0x00429460` → `0x00429350` → `0x00428BD0` → 큐.
- 원본 애니메이션 하나가 하위 스프라이트 여러 개로 분해될 수 있다. 한 애니메이션 ID를 한 물리 Draw로 1:1 강제 연결하면 오류.
- `0x0042A800`은 특수 마스크/합성, `0x0042A3A0`은 일반 GPU 제출. 필터/알파/깊이 복원 후 양안을 비교.
- 원본 텍스처와 `SPRANI` 패키지는 별도 `sprite_dds_map.json` 색인과 결합해야 정확한 UV·DDS 비교가 가능하다.
- R84: `src/hooks_textures.cpp`, `sprite_uv_transaction.hpp`, `render_semantics.hpp`; SpriteNode ptr + generation + queueEpoch가 일관성 증거.

### C. +TIME · 시간 문자 · 결과

- 원본 `0x00498670` 안에서 `0x2C00B4`(RVA `0x9898E`), `0x2C00B5`(`0x98A36`), 별도 모드 `0x2C006C`(`0x98AC6`) 애니메이션 분기.
- 시간 문자는 `0x004973C0`(`0x989AD`/`0x98A89`), 7자리 숫자는 `0x004974E0`(`0x98A10`) → `0x004B9200` → glyph queue. 한 호출자가 끝난 뒤 D3DXSprite End에서 GPU가 실행될 수 있다.
- `0x004979E0` 자체도 진행률 텍스트와 애니메이션을 생성하므로 서로 다른 원본 출처가 **같은 프레임에 섞인다**.
- R84에는 `CanDrainDirectResultBeforeFirstQueueNode`, `CanIsolateD3DXStageQueueNodeTransition`, `R30CaptureStagePhysicalSource`, `StageExtensionPhysical::SameAfterNativeLeft` 방어 로직이 이미 있으므로 다시 구현할 이유 없음. 실제 어떤 이유로 R30 실패/폴백하는지 계측.

### D. 6th/6 고정 HUD와 차량 부착 순위

- 고정 HUD `0x004B9D80`은 `0x2B005F` 등 스프라이트와 문자를 별도 출력. 
- 차량 위 마커 `0x004BAD20`은 `0x00449940`의 Calc3D2D 원본 투영 경로. 오른쪽 눈에서 원본 화면상 X,Y를 복제하면 월드 부착이 깨질 수 있음.
- 렌더 도중 별도 게임 상태·화면 마커 노드가 끼어들면 원래 마커 owner와 WVP/pose를 분리해야 함.
- R84: `R30CaptureProjectedRankPhysicalSource`, `R30SupportTryFixedFunctionProjectedRankIndexed` 등 확인. FVF=0x142 고정경로의 R33 generic 진입 전에 조기 Draw 가능.

### E. 렌즈 중심·외곽 링·하늘

- 원본 렌즈 중심의 기존 확인된 시퀀스는 `0x0040CBC0` 아래 `0x0040C980` 중심과 `0x0040C9A0` 외곽 후보로 구별. 직접 디컴파일에서 outer가 중심과 완전히 같은 객체인지 픽셀 검증 완료된 것은 아님.
- SkyGlow는 중심 3D 빌보드·화면 투영 링·후처리의 독립 경계로 검사.
- 원본 `0x00449940` 원근/뷰포트 투영 계산이 GPU c64의 좌우 눈 카메라와 동일 프레임인지 확인.
- **금지:** 밝은 DDS만으로 중심광·SkyGlow의 GPU 원본 소유자 단정, FVF/alpha만으로 모든 렌즈 판정, 검증 없이 이미 정상이던 하늘을 재투영.

### F. 월드·파티클·반사·차량 그림자

- Direct3D device 메서드까지 도달하는 수십 개 함수가 있으나 원본 인디렉트 디스패치가 남아 있어 모두의 역할을 단정할 수 없음. `DIRECT_RENDER_GATES.md`에서 원본 위치별 API를 식별.
- 파티클은 수명, 블렌딩/테스트, 생성/소멸, 카메라 변환, 우선순위 큐와 실제 Draw를 연결해야 한다. 특정 GPU API만으로 “먼지 파티클”이나 “유리”로 선언하지 않음.
- 차량 바닥 그림자는 별도 3D original WVP provenance. WorldParticle, SkyGlow, 렌즈 링과 합치지 않음.
- 물·반사·글래스는 실제 RenderTarget·텍스처 샘플링/Depth 관계와 GPU 계측을 비교해야 함.
- 현재 전체 함수 목록은 메서드·호출 그래프를 제공하지만 **이러한 의미론적 분류의 미해결 범위도 표시**한다.

### G. UI 원본 텍스처·메뉴·F11

- 메인 메뉴는 `SUMO_FE_CVT`, 차량 선택은 `SELECTOR_CVT` 리소스와 연동된 원본 Sprite/UV 계산, 화면 종횡비, 알파/마스크, DDS 포맷을 검사한다.
- ESC와 게임 내 옵션 화살표는 원본 스프라이트 레이어. F11 호스트 ImGui는 원본 EXE가 아닌 별도 host overlay이므로 REA의 원본 GPU 목록에 없을 수 있다.
- 오류는 위치/텍스처/양안/입력 히트박스로 따로 진단해야 함.

## 4. 실제 원본 Callgraph가 없다고 판단하면 안 되는 사례

- `0x00498670` 원본 호출자 0개 = 미사용이 아니다. 인접 thunk `0x004998E6` 점프와 간접 콜백 경계가 존재한다.
- `0x004B9D80` / `0x004BAD20`는 직결 caller 수가 0으로 표시될 수 있다. 스테이지 콜백·함수 테이블 소유자를 조사해야 한다.
- C 의사코드 호출 그래프는 **보조 자료**, 새 Ghidra 원시 디스어셈블리 CALL/JMP 그래프는 **확인된 opcode 흐름 참조**이나 계산된 미해결 타깃은 여전히 UNKNOWN이다.

## 5. 자료 해석 우선순위

1. 정밀 REA evidence JSON의 정확 함수 본체 / 직접 호출 관계.
2. 기계어 instruction × XREF native exported rows.
3. Ghidra C 디컴파일 함수 내부 알고리즘 및 원본 DDS 패키지 데이터.
4. DX9Ex R84 최신 GitHub 브랜치 실제 구현.
5. 같은 원본/모드 SHA의 Windows CI와 Quest3/HMD 실기 관측.

**확정:** 원본 함수→큐→D3D9 메서드 호출을 정적으로 추적 가능.
**미확정:** 어느 GPU Draw가 VR LEFT/RIGHT에 성공했는지, 광학 중복 여부, 모든 파티클의 생성·소멸, 각 셰이더의 효과 역할, 정확한 3D Draw→OpenXR 호스트 이미지의 1:1 연계.