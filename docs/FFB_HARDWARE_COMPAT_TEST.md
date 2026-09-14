# FFB hardware compatibility retest

[English](#english) | [한국어](#한국어)

<a id="english"></a>
## English

This checklist is for the v0.1.1 DirectInput compatibility and profile-save path. The steering feel should remain consistent with the established **Physics SAT / Natural SAT** implementation while device/runtime/profile compatibility is retested across different wheel drivers.

### What changed

- FFB profile persistence keeps the staged-write/backup path and falls back from `rename` to `copy_file` on Windows when the final rename is rejected by a filesystem/filter/driver edge case.
- First-time profile creation treats a missing destination `.ini` and missing `.bak` as the normal new-profile state instead of a filesystem failure.
- The final profile file is verified after installation.
- Profile save success and failure messages include the real runtime destination path. Failures are also written to `OutRun2006Tweaks.log`.
- The Ready to Drive panel distinguishes a real failure `[!]` from a pending state `[..]`.
- Outside gameplay, `FFB device (starts in gameplay)` is pending rather than failed because the runtime intentionally acquires the saved DirectInput FFB device when driving starts.
- `Direction test (not run)` is a setup confirmation state, not a hardware failure.
- DirectInput interface selection now handles wheelbases that expose multiple candidate Windows interfaces more defensively.
- Reported force-actuator axes are probed and ConstantForce creation/update is validated before an interface is accepted for output.
- Transient output/device failures can trigger retry/reinitialization instead of immediately leaving the runtime in a dead state.

### Retest sequence

1. Start the game, open **Force Feedback** before entering a race, and select the intended FFB output interface.
2. Confirm the menu-time status shows `[..] FFB device (starts in gameplay)` instead of treating `waiting / released / inactive` as a hardware error.
3. Enter gameplay. Confirm FFB initializes and works normally.
4. Run **Test Left** and **Test Right** once. Confirm the direction-test status changes from pending to OK when the directions are correct.
5. Make sure `OutRun2006Tweaks.profiles\FFB\ffb.ini` does **not** already exist, enter `ffb` as the FFB profile name, and select **Save as profile**. This explicitly tests first-time creation.
6. Confirm the UI reports the full saved path and that `<game folder>\OutRun2006Tweaks.profiles\FFB\ffb.ini` exists.
7. Change one FFB value and overwrite the same `ffb` profile once. Confirm overwrite also succeeds.
8. Load the saved profile and confirm the feel settings return while the selected physical FFB output device remains unchanged.
9. If saving fails, attach `OutRun2006Tweaks.log`; the error should include the destination folder and the Windows filesystem error.
10. During gameplay, disconnect and reconnect the wheelbase once. Confirm the device is reacquired and FFB resumes without restarting the game.
11. Repeat one short left and right corner and confirm SAT direction/feel is unchanged.
12. Exit to the menu and re-enter gameplay once more to confirm normal acquire/release/reacquire behavior.

### Requested hardware coverage

- **MOZA R3** regression check
- **Simucube 3** / actual force-feedback interface exposed by its driver
- **Fanatec** wheelbase / DirectInput FFB interface
- Other DirectInput wheelbases that expose more than one Windows interface

Do not change force-feel tuning for this test. The goal is device/runtime/profile compatibility and regression checking.

When reporting a result, please include:

- wheelbase model;
- driver/control-software version;
- firmware version;
- whether the 20% left/right test is correct;
- whether in-game disconnect/reconnect recovers;
- whether first-save and overwrite of an FFB profile both succeed;
- the full `OutRun2006Tweaks.log` from launch through exit if anything fails.

---

<a id="한국어"></a>
## 한국어

이 체크리스트는 v0.1.1의 DirectInput 호환성과 FFB 프로필 저장 경로를 다시 확인하기 위한 것입니다. 서로 다른 휠 드라이버에서 장치/런타임/프로필 호환성을 확인하되, 조향 감각은 기존 **Physics SAT / Natural SAT** 구현과 동일하게 유지되어야 합니다.

### 변경된 부분

- FFB 프로필 저장은 staged write/backup 구조를 유지하고, Windows에서 파일시스템/필터/드라이버 예외 때문에 최종 `rename`이 거부되는 경우 `copy_file`로 폴백합니다.
- 최초 프로필 생성 시 목적지 `.ini`와 `.bak`가 없는 것은 정상적인 새 프로필 상태로 처리하며 파일시스템 오류로 보지 않습니다.
- 설치 후 최종 프로필 파일이 실제로 존재하는지 확인합니다.
- 프로필 저장 성공/실패 메시지에 실제 런타임 대상 경로를 표시하고, 실패 내용은 `OutRun2006Tweaks.log`에도 기록합니다.
- Ready to Drive 패널에서 실제 실패 `[!]`와 대기 상태 `[..]`를 구분합니다.
- 게임플레이 밖에서는 런타임이 주행 시작 시 저장된 DirectInput FFB 장치를 acquire하므로 `FFB device (starts in gameplay)`를 실패가 아닌 대기 상태로 표시합니다.
- `Direction test (not run)`은 하드웨어 오류가 아니라 아직 방향 테스트를 실행하지 않은 설정 확인 상태입니다.
- 여러 Windows 인터페이스를 노출하는 휠베이스에서 DirectInput 인터페이스 선택을 더 보수적으로 처리합니다.
- 드라이버가 보고하는 force-actuator axis를 탐색하고 ConstantForce 생성/갱신을 검증한 뒤 실제 출력 인터페이스로 인정합니다.
- 일시적인 출력/장치 실패가 발생하면 즉시 죽은 상태로 남기지 않고 재시도/재초기화를 수행할 수 있습니다.

### 재테스트 순서

1. 게임을 실행하고 레이스 진입 전에 **Force Feedback**을 열어 사용할 FFB 출력 인터페이스를 선택합니다.
2. 메뉴에서 `waiting / released / inactive`를 하드웨어 오류로 표시하지 않고 `[..] FFB device (starts in gameplay)`로 표시하는지 확인합니다.
3. 실제 주행에 들어가 FFB가 정상 초기화되고 동작하는지 확인합니다.
4. **Test Left**와 **Test Right**를 한 번씩 실행하고 방향이 올바르면 방향 테스트 상태가 pending에서 OK로 바뀌는지 확인합니다.
5. `OutRun2006Tweaks.profiles\FFB\ffb.ini`가 **없는 상태**에서 프로필 이름에 `ffb`를 입력하고 **Save as profile**을 실행합니다. 최초 생성 경로를 명확히 확인하기 위한 단계입니다.
6. UI에 전체 저장 경로가 표시되고 `<게임 폴더>\OutRun2006Tweaks.profiles\FFB\ffb.ini`가 실제로 생성되는지 확인합니다.
7. FFB 값을 하나 변경한 뒤 같은 `ffb` 프로필에 덮어쓰기하고 정상 저장되는지 확인합니다.
8. 저장한 프로필을 다시 불러와 감각 설정은 복원되지만 선택된 실제 FFB 출력 장치는 바뀌지 않는지 확인합니다.
9. 저장이 실패하면 `OutRun2006Tweaks.log`를 첨부합니다. 로그에는 대상 폴더와 Windows 파일시스템 오류가 포함되어야 합니다.
10. 주행 중 휠베이스를 한 번 분리했다 다시 연결하고, 게임을 재시작하지 않아도 장치가 다시 acquire되어 FFB가 복구되는지 확인합니다.
11. 짧은 좌/우 코너를 다시 주행해 SAT 방향과 감각이 이전과 동일한지 확인합니다.
12. 메뉴로 나갔다가 다시 주행에 들어가 acquire/release/reacquire 흐름이 정상인지 한 번 더 확인합니다.

### 요청 하드웨어 범위

- **MOZA R3** 회귀 테스트
- **Simucube 3** / 드라이버가 노출하는 실제 FFB 인터페이스
- **Fanatec** 휠베이스 / DirectInput FFB 인터페이스
- 하나의 휠베이스가 여러 Windows 인터페이스를 노출하는 기타 DirectInput 장치

이 테스트에서는 FFB 감각 튜닝을 바꾸지 마세요. 목적은 장치/런타임/프로필 호환성과 회귀 여부를 확인하는 것입니다.

테스트 결과를 공유할 때는 다음 정보를 함께 제공해 주세요.

- 휠베이스 모델
- 드라이버/제어 프로그램 버전
- 펌웨어 버전
- 20% 좌/우 방향 테스트 정상 여부
- 게임 중 분리/재연결 후 복구 여부
- FFB 프로필 최초 저장 및 덮어쓰기 성공 여부
- 문제가 발생한 경우 게임 실행부터 종료까지의 전체 `OutRun2006Tweaks.log`
