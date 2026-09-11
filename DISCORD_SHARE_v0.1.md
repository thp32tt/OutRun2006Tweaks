# Discord share text — v0.1

## English

I made an experimental **OutRun2006Tweaks Wheel FFB v0.1** build mainly around my **MOZA R3** setup. The only wheel I have personally hardware-tested is the R3, so other DirectInput wheels are still unverified on my side.

It adds SDL3 multi-device input, an in-game Quick Setup/calibration flow, and native DirectInput COM FFB without vJoy or an external mapper. Current F11 FFB presets are **MOZA R3 Physics SAT** and **MOZA R3 Natural SAT**. The Physics starting point uses Overall 0.70, Spring 0.65, Dynamic Damping 0.28 and SAT 1.45; Natural SAT uses Damping 0.30 and SAT 1.75. Both keep Collision at 0.38.

Quick Setup now covers steering, pedals, paddles, Start/Confirm/Back and all four menu directions, with Skip and fine-tune/calibration paths. FFB changes apply live and the UI marks unsaved tuning until `Save Force Feedback` is used.

Credits/thanks to **emoose/OutRun2006Tweaks**, **hyp36rmax/multi-device-input**, **d-b-c-e/OutRun2006Tweaks-FFB**, and everyone who shared wheel-testing information. The upstream license/notices are retained in the fork.

Release / install details:
https://github.com/thp32tt/OutRun2006Tweaks/releases/tag/v0.1

If anyone tries another wheel, compatibility feedback plus `OutRun2006Tweaks.log` would be very useful.

## 한국어

개인적으로 **MOZA R3로 OutRun 2006을 하려고 만든 OutRun2006Tweaks Wheel FFB v0.1**을 공유합니다. 제가 직접 실기 테스트한 휠은 R3 하나뿐이라 다른 DirectInput 휠은 아직 미검증입니다.

SDL3 멀티 디바이스 입력, 게임 내 Quick Setup/축 보정, 별도 vJoy 없이 DirectInput COM 방식의 네이티브 FFB를 넣었습니다. 현재 F11 프리셋은 **MOZA R3 Physics SAT**와 **MOZA R3 Natural SAT** 두 가지입니다. Physics 시작값은 Overall 0.70, Spring 0.65, Dynamic Damping 0.28, SAT 1.45이고 Natural SAT는 Damping 0.30, SAT 1.75를 사용합니다. Collision은 둘 다 0.38입니다.

Quick Setup은 조향/페달/패들/Start/Confirm/Back/메뉴 4방향을 설정하며 Skip과 세부 보정 경로가 있습니다. FFB 변경은 즉시 적용되고 `Save Force Feedback` 전에는 UI에 미저장 상태가 표시됩니다.

원본 **emoose/OutRun2006Tweaks**, **hyp36rmax/multi-device-input**, **d-b-c-e/OutRun2006Tweaks-FFB** 및 테스트 정보를 공유해 주신 커뮤니티 분들께 감사합니다. 원본 라이선스/고지는 포크에 유지했습니다.

릴리스/설치 방법:
https://github.com/thp32tt/OutRun2006Tweaks/releases/tag/v0.1

다른 휠에서 테스트해 보신 분이 있다면 `OutRun2006Tweaks.log`와 함께 결과를 알려주시면 도움이 됩니다.
