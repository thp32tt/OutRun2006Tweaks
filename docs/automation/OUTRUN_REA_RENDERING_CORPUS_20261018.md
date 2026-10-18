# OutRun 2006 — REA/Ghidra 전체 렌더링 역분석 개발 자료

기준: 2026-10-18 KST · 분석 대상: N100에 있는 사용자 보유 원본 `OR2006C2C.exe` · 원본 SHA256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`

## 이 결과는 무엇을 끝냈나?

- Ghidra 12.1.4에서 인식한 내부 함수 **7,238개**의 기계어 흐름을 새로 전수 인덱싱했다(기계어 **404,925**개, 제어흐름 참조 **71,667**개). 이 중 기존 C 디컴파일 성공 **7,237개**, 실패 **1개(`0x00536D82`)**; Ghidra가 식별한 전체 함수 수 7,415개는 외부/스텁 등까지 포함하는 별도 총계이므로 혼동 금지.
- C 디컴파일에서 이름이 복원된 직접 호출·GPU API를 추출하고 **93개 직접 렌더링 근거 함수**, 네이티브/Ghidra-C 참조 2단계 연관 **1,810개 함수 후보**를 식별했다. 후보 1,810개 모두를 실제 Draw 함수라고 표현하면 틀리다.
- 네이티브 함수 간 흐름 약 **28,733개 호출 위치**와 직접·간접·조건 분기를 구분했고, 함수별 원본 VA/RVA, caller/callee, D3D9 메서드, ID3DXSprite 호출, 디컴파일 경고를 정리했다.
- REA 6.5.0의 Ghidra provider로 `0x00498670`(+TIME)과 `0x0042DD50`(큐 노드 할당)을 실제 함수 단위로 조회한 증거를 결합했다. **나머지 97개 개별 REA 분석은 별도 실행 큐이며 완료 여부는 진행 상태 JSON으로만 판단한다.**
- 원본 함수와 R84 소스의 연결 경로, 차단 조건, 화면 오류 유형과 개발자 검증 조건을 별도 문서에 정의했다.

## 자료 파일

| 파일 | 용도 |
|---|---|
| `summary.json` | 분류량·진행 상태·원본 SHA·범위 |
| `FUNCTION_CATALOG_NATIVE_MERGED.jsonl` | 전체 7,238개 함수 구조화 레코드 |
| `GHIDRA_NATIVE_FUNCTIONS.csv` | 네이티브 함수별 명령 수·간접 호출 수 |
| `GHIDRA_NATIVE_FLOW_EDGES.csv` | 전체 기계어 흐름 참조 71,667개 |
| `NATIVE_INTERFUNCTION_EDGES.csv` | 함수 사이 CALL / cross-function JMP / resolved computed call |
| `CALLGRAPH_EDGES.csv` | C 의사코드에서 복원한 보조 함수 호출 그래프 |
| `RENDER_FUNCTION_NATIVE_SHORTLIST.csv` | 원본 직접 렌더 근거 기준 2단계 후보 |
| `RENDER_FUNCTION_SHORTLIST.csv` | 별도 Ghidra C 그래프의 2단계 후보 |
| `INDIRECT_RENDER_CALL_SITES.csv` | 해결되지 않은 원본 간접 호출 조사 우선순위 |
| `FUNCTION_PROFILE_INDEX.md` | **렌더 관련 1,810개 주소별 프로파일 문서 색인** |
| `function_profiles/RENDER_FUNCTIONS_001.md` ~ `038.md` | 각 함수의 주소·직접 호출·API·후속 디버깅 지침 |
| `DIRECT_RENDER_GATES.md` | 직접 D3D9/ID3DXSprite와 확정된 생성자 93개 |
| `API_TO_FUNCTION_INDEX.md` | GPU API별 역방향 함수 조회 |
| `RENDER_ARCHITECTURE.md` | 원본 프레임→SpriteNode→GPU 렌더링 아키텍처 |
| `DX9EX_DEVELOPER_HANDOFF.md` | **R84 자동개발에 활용할 구체적인 문제-소스 대응표** |
| `RENDER_DIAGNOSTIC_ACCEPTANCE.md` | 양안·큐·D3DX·OpenXR 검증 이벤트와 PASS 조건 |
| `REA_RENDER_BATCH_MANIFEST.json` | 별도 직접 REA 검증 대상 99개, 우선순위 |
| `REA_RENDER_BATCH_RECONCILED_STATUS.json` | **실행된 결과만** 성공/실패로 집계 |
| `rea_evidence/*.json` | 개별 REA 출력. 미완료인 경우 이 파일이 없을 수 있음 |

## 즉시 검색

N100 쉘 기준:

```bash
cd /home/chatgpt-runner/rea-analysis/rendering_complete_20261018

# 전체 함수 중 주소 찾기
grep -n '"va": "0x0042D710"' FUNCTION_CATALOG_NATIVE_MERGED.jsonl

# 실제 GPU Draw를 호출하는 함수
grep -E 'DrawPrimitiveUP|DrawIndexedPrimitiveUP' DIRECT_RENDER_GATES.md

# Stage +TIME/6th·6/렌즈 분석
grep -n -E '0x00498670|0x004B9D80|0x0040CBC0' DX9EX_DEVELOPER_HANDOFF.md

# 개별 REA 분석 진행
python3 reconcile_rea_batch.py && python3 -m json.tool REA_RENDER_BATCH_RECONCILED_STATUS.json | head -70
```

## 정적 분석과 게임 실기 검증 구분

- **REA/Ghidra 함수 분석:** 원본 실행 파일의 호출·데이터·가상 메서드·큐 구조를 알아낸다. **원본 게임은 OpenXR 좌우 눈을 그리지 않는다.**
- **R84 C++ 정적 검사:** 해당 원본 생성자가 `hooks_textures` → `render_semantics` → R30/R33에서 어떤 보호 조건과 변환 분기를 갖는지 확인한다. 성공한 배포를 의미하지 않는다.
- **Windows CI/빌드:** 정확한 소스 SHA로 빌드 가능함을 증명할 수 있으나 실제 영상이 정상임을 보장하지 않는다.
- **Quest3/VDXR HMD 실기:** 동일 빌드·같은 프레임의 생성자 ID, 큐 ID, 왼쪽/오른쪽 실제 Draw와 OpenXR swapchain 제출·시야를 확인해야 화면 오류 원인 확정 및 수정 PASS를 선언할 수 있다.
- 이 자료는 **RUNTIME_VALIDATION=UNTESTED**이다. **렌더링 소스 코드를 이번 자료 작성 중 수정하지 않았다.**
- N100 자료에는 사용자 보유 게임의 역분석 메타데이터가 있다. **전체 디컴파일 C, 원본 EXE 및 원본 DDS 등 저작물 원문을 GitHub에 게시하지 않는다.** 공개/공유 가능한 것은 주소·요약·독립 작성한 모드 분석·검증 명세로 한정한다.

## 확정되지 않은 부분

간접 호출에 의한 함수 도달, 엔진의 실제 객체 타입, 스프라이트/파티클의 화면별 실제 텍스처 일치, 미실행 스테이지, 마스킹된 셰이더·GPU 상태, R30 조기 반환 이후 양안 Draw, OpenXR 합성 및 Quest3 실제 표시 성공. 미확정 내용을 함수의 역할 또는 버그 원인으로 자동 승격하지 않는다.