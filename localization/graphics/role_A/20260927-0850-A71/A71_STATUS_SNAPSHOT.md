# OutRun 2006 한글화 A71 상태

- 역할: A / 실제 한글화 제작
- 범위: 한글화만 수행. Git 동기화, 빌드, VR, FFB 작업 없음.
- 기준: 원본 모드 기반 독립 한글패치. OR2-HD-GUI의 고해상도 자산을 기준으로 기존 HD 그래픽은 유지.
- 기준 자산: `FF2462BB_1024x512.dds` 실제 4096×2048 RGBA32.
- 이전 B67 `Drift! → 드리프트!` 작업은 그대로 유지.
- 이번 신규 제작:
  - `Don't lose your girlfriend! → 여자친구를 놓치지 마세요!`
  - `Total / Time → 총 / 시간`
  - `Lap / Time → 랩 / 타임`
  - `Hearts / Score → 하트 / 점수`
  - 독립 `Time → 시간`
  - 동일 아틀라스의 중복 `Lap → 랩`
- 모든 신규 픽셀은 각 원본 텍스트 bbox 내부에만 기록했고, 경계 픽셀에는 불투명 텍스트가 닿지 않도록 안전 여백을 확인.
- DDS 128-byte 헤더, 4096×2048 크기, 파일 크기 유지.
- B67 대비 신규 bbox 외 변경 픽셀: 0.
- canonical 원본 대비 기존 Drift + 이번 신규 bbox 외 변경 픽셀: 0.

## 다음 미완료
`FF2462BB`의 `Slipstream the cars!`, `Avoid the knockout!`, `Beat that car!`, Stage/route/account/menu 계열 남은 텍스트를 계속 처리한 뒤 `568D3696`으로 진행.
