# OutRun2006Tweaks Wheel FFB v0.2

## English

v0.2 is a major FFB update focused on making **OutRun 2006 more enjoyable with modern Direct Drive wheels such as the MOZA R3**, while also adding a separate **Arcade Original** force-feedback mode.

### Changes since v0.1.1

- **Reworked Modern DD countersteer**
  - Added adjustable **Countersteer Strength** in F11 / INI.
  - Improved drift countersteer behavior using vehicle slip information.
  - Smoother transition when the car regains grip to reduce steering rebound.

- **Improved road and stage vibration**
  - Retuned stage-specific surfaces including **Imperial Avenue** and **Floral Village**.
  - Better distinction between normal road texture, rough road, curb and shoulder feedback.
  - Road vibration now fades out when the car is stopped.

- **Improved collision feedback**
  - Stronger and more reliable wall/collision feedback for Modern DD wheels.

- **Added Arcade Original mode**
  - Separate FFB model based on reconstructed OutRun arcade / OutRun2Real behavior.
  - Uses its own spring, road, collision and gear-effect behavior instead of the Modern DD physics model.
  - Modern DD and Arcade Original settings are isolated so switching modes does not mix their force characteristics.

---

## 한국어

v0.2는 **MOZA R3 같은 현대식 Direct Drive 휠로 OutRun 2006을 좀 더 재미있게 즐길 수 있도록 FFB를 크게 개선한 버전**이며, 별도의 **Arcade Original 모드**도 추가했습니다.

### v0.1.1 대비 변경사항

- **Modern DD 카운터스티어 개선**
  - F11 / INI에서 조절 가능한 **Countersteer Strength** 옵션 추가
  - 차량의 슬립 상태를 이용한 드리프트 카운터스티어 동작 개선
  - 그립을 되찾을 때 핸들이 좌우로 튕기는 현상 완화

- **노면 및 스테이지 진동 개선**
  - **Imperial Avenue, Floral Village** 등 스테이지별 특수 노면 진동 재조정
  - 일반 노면, 거친 노면, 연석, 갓길의 진동 차이를 개선
  - 차량이 정지하면 노면 진동이 계속 발생하지 않도록 수정

- **충돌 FFB 개선**
  - Modern DD 휠에서 벽 충돌 및 충격 피드백을 더 확실하게 조정

- **Arcade Original 모드 추가**
  - OutRun 아케이드 / OutRun2Real 자료를 기반으로 재구성한 별도 FFB 모드
  - Modern DD 물리 FFB와 달리 아케이드 방식의 Spring, Road, Collision, Gear 효과를 별도로 사용
  - Modern DD와 Arcade Original의 설정과 힘 계산을 분리해 서로 섞이지 않도록 구성
