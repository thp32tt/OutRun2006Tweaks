# OutRun 원본 Sprite 애니메이션·클립 분리 렌더 경로 검증

원본 EXE SHA256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3` | 검증: N100 Ghidra 정적 소스 근거, HMD 미확인.

## 확인

- 원본 렌더 큐 소비: 0x0042D710. 우선순위 버킷 21개, 노드 슬롯 560개(헤더·센티널 슬롯 포함), 0x110 바이트 stride. 순환 사용이므로 node 주소를 영구적인 producer identity로 사용할 수 없다.
- 클립/2D producer: 0x0042D280 → 0x0042CFE0 → 0x0042DD50, node type=0.
- 애니메이션 producer: 0x00429530 → 0x00428A10 → 0x00429460 → 0x00429350 → 0x00428BD0 → 0x0042D0C0 → 0x0042DD50, node type=1.
- 애니메이션 내 별도 지연 버퍼 최대 0x30=48 슬롯 확인(동작 조건·실제 채움 여부는 런타임 미확인).
- 0x0042D710의 각 우선순위 순회는 D3DXSprite::Begin(0x00429C60), Draw(0x0042A0A0), End(0x00429F60)를 포함하며 node flag에 따라 0x0042C0F0의 D3D9 DrawPrimitiveUP 가상 호출(오프셋 0x14C) 또는 다른 native 3D 경로로 분기한다.
- original D3DXSprite Draw vtable +0x24 / End +0x2C에 의해 큐 producer 함수가 돌아온 후 실제 GPU draw가 발생할 수 있다. **소유권을 호출 스택 지역 상태만으로 전달하면 충분하지 않다.**
- stage +TIME, rank HUD, 차량 위 rank는 animation node와 clip node가 동일 화면 기능에 공존할 수 있으므로 두 경로를 따로 계측해야 한다.

## 추가 확인: 게임 프레임 소비 위치와 분기

- 0x0042D710는 0x00449050 프레임 함수와 0x004C50A0 조건부 함수의 정적 직접 피호출 대상이다.
- 0x00449050는 0..8 아홉 단계를 순회하면서 동적 function-table callback과 게임 렌더 스테이지를 실행한 뒤 0x0042D710를 호출한다.
- 스테이지 8에서 특정 조건(원본 0x0078026C==0x20)이 만족되면 0x004C50A0를 통해 **조건부 부분 소비**가 먼저 일어날 수 있다. 0x004C50A0 자체도 별도 런타임 플래그가 true여야 0x0042D710를 호출한다.
- 따라서 프레임 내 queueEpoch을 한 번의 Present와 같은 것으로 가정하지 말고, 실제 소비 시작마다 독립적으로 증가시키는 편이 안전하다. 조건부 소비 여부 및 동일 sprite의 중복 GPU 제출은 실기 미검증이며 단정하지 않는다.
- node type=0인 D3DXSprite Draw 경로와 type=1인 Sprani 직접 D3D9 경로는 공통 0x0042D710 소비 과정에서 갈라진다. 원본 0x0042C0F0의 D3D9 DrawPrimitiveUP, D3DXSprite::Draw/End는 **정적 GPU 제출 경계 근거**지만, R84 후킹이 어느 physical draw에서 어느 eye로 재생하는지는 별도 동적 계측이 필요하다.

## 생성 함수별 두 큐 경로 (정적 함수 참조 그래프)
- stage_extension/to_clip_node: 0x00498670 → 0x004979E0 → 0x0042D200 → 0x0042CFE0
- stage_extension/to_animation_node: 0x00498670 → 0x00429530 → 0x00428A10 → 0x00429460 → 0x00429350 → 0x00428BD0 → 0x0042D0C0
- rank_hud/to_clip_node: 0x004B9D80 → 0x0042D280 → 0x0042CFE0
- rank_hud/to_animation_node: 0x004B9D80 → 0x00429530 → 0x00428A10 → 0x00429460 → 0x00429350 → 0x00428BD0 → 0x0042D0C0
- vehicle_rank/to_clip_node: 0x004BAD20 → 0x0042D280 → 0x0042CFE0
- vehicle_rank/to_animation_node: 0x004BAD20 → 0x00429580 → 0x00428A10 → 0x00429460 → 0x00429350 → 0x00428BD0 → 0x0042D0C0
- shared_hud_text/to_clip_node: 0x004BA9D0 → 0x0042D280 → 0x0042CFE0
- shared_hud_text/to_animation_node: 0x004BA9D0 → 0x00429580 → 0x00428A10 → 0x00429460 → 0x00429350 → 0x00428BD0 → 0x0042D0C0
- animation_sprite/to_clip_node: no static direct-call chain
- animation_sprite/to_animation_node: 0x00429530 → 0x00428A10 → 0x00429460 → 0x00429350 → 0x00428BD0 → 0x0042D0C0
- animation_alpha/to_clip_node: no static direct-call chain
- animation_alpha/to_animation_node: 0x00429580 → 0x00428A10 → 0x00429460 → 0x00429350 → 0x00428BD0 → 0x0042D0C0
- clip_sprite/to_clip_node: 0x0042D280 → 0x0042CFE0
- clip_sprite/to_animation_node: no static direct-call chain
- lens_scene/to_clip_node: no static direct-call chain
- lens_scene/to_animation_node: no static direct-call chain

## 구현 반영 시 검증 포인트

- 원본 kind 0/1, sourceSerial, 원본 caller RVA, node generation, priority bucket 및 queueEpoch을 독립 키로 기록한다.
- 0x00449050 → 0x0042D710와 0x004C50A0 → 0x0042D710 양쪽을 진단해야 누락된 조기 소비를 놓치지 않는다.
- +TIME·6th/6·RANK_MARKERS는 두 node type 모두에 해당할 수 있으므로 애니메이션 sprite 처리만 또는 clip sprite 처리만 수정해서 전체 해결로 간주하지 않는다.
- 렌즈 중심은 별도 WorldEffect call family로서 이 Sprite 노드 큐와의 직접 연결이 확인되지 않았다. HUD 노드로 강제 분류해서는 안 된다.

## 실기 자료로 검증할 공백

1. 0x0042D710 소비의 queueEpoch/nodeGeneration/sourceSerial 별로 physical R84 Draw* 두 눈 도달·HRESULT, pose/c64, host Submit 증명.
2. kind-0 D3DXSprite::Begin→Draw→Flush→End 동안 기존 batch 소유권이 바뀌는지 확인.
3. kind-1 animation direct D3D draw과 0x30 임시 스프라이트 버퍼의 serial 보존을 별도 확인.
4. +TIME 3 sprite/3 numeric, 6th/6 first animation/clip siblings, projected rank markers mixed owner를 분리.
5. 560 슬롯/48 임시 슬롯 실제 포화·드롭은 계산상 위험일 뿐 재현된 결함이 아님.

분석 전용; 게임 원본·디컴파일된 C·DDS를 GitHub에 업로드하지 말 것. 본 정적 결과만으로 시각 버그 수정 완료라 판정하지 말 것.