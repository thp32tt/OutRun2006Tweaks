# OutRun x86 OpenXR Direct POC

이 파일은 OutRun 게임 모드가 아니라 **32비트 OpenXR 직접 연결 가능성만 확인하는 독립 진단 프로그램**입니다.

## 실행 전

1. Quest 3를 Virtual Desktop으로 연결합니다.
2. Virtual Desktop의 OpenXR runtime이 VDXR로 활성화된 상태를 사용합니다.
3. 게임은 실행하지 않아도 됩니다.
4. `Run-x86-openxr-probe.cmd`를 실행합니다.

## 성공 기준

콘솔 마지막 부분에 다음 형식이 나오면 x86 direct OpenXR 기본 경로가 성립합니다.

`x86-direct-session=READY eye0=<width>x<height> eye1=<width>x<height>`

이 결과는 32비트 프로세스에서 다음 단계가 성공했다는 뜻입니다.

- OpenXR instance 생성
- HMD system 조회
- `XR_KHR_D3D11_enable` graphics requirements 조회
- OpenXR이 요구한 GPU adapter로 D3D11 device 생성
- OpenXR session 생성
- 양안 권장 해상도 조회

## 실패 시

`x86-direct-session=FAILED ...` 뒤의 메시지를 그대로 보존하면 됩니다.

이 POC는 기존 x64 `outrun-vr-host.exe`를 대체하지 않습니다. x64 Host/IPC가 실제 병목인지 확인할 필요가 생겼을 때만 다음 단계로 확장합니다.
