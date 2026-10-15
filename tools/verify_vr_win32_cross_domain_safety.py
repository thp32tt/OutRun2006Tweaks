#!/usr/bin/env python3
"""MSVC-detected cross-feature Win32 safety contract and mutation tests."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def verify(source):
    draw=source["src/hooks_drawdistance.cpp"]
    fps=source["src/hooks_framerate.cpp"]
    checks=[
       ("clipboard checked lock", "void* destination = GlobalLock(hMem);" in draw),
       ("null lock guarded", "if (destination)" in draw),
       ("clipboard copy uses checked ptr", "memcpy(destination, clipboard.c_str()" in draw),
       ("clipboard success ownership transfer", "if (EmptyClipboard() && SetClipboardData(CF_TEXT, hMem))" in draw),
       ("clipboard releases failed handle", "if (hMem)\n\t\t\t\t\tGlobalFree(hMem);" in draw),
       ("clipboard requires opened handle", "if (OpenClipboard(nullptr))" in draw),
       ("winmm export guarded", 'auto timeBeginPeriod = winmm' in fps and 'auto timeGetDevCaps = winmm' in fps),
       ("caps function not called null", "if (timeGetDevCaps && timeGetDevCaps(&caps, sizeof caps) != 0)" in fps),
       ("caps positive default", "TIMECAPS caps{ 1, 1 };" in fps),
       ("QPC counter checked", "if (!QueryPerformanceFrequency(&qpf) || qpf.QuadPart <= 0)" in fps),
       ("timer optional", "Timer = CreateWaitableTimerExW(" in fps),
       ("render wait checks arming failure", "if (!SetWaitableTimerEx(Timer, &due, 0, NULL, NULL, NULL, 0))" in fps),
       ("render wait is bounded", "WaitForSingleObject(Timer, waitBudgetMs) != WAIT_OBJECT_0" in fps),
       ("timer wait has finite QPC slice", "std::clamp<INT64>((sleepTicks + 9999) / 10000 + 5, 1, 1000)" in fps),
       ("file loader lock failure refuses hook install",
        "if (!InitializeCriticalSectionAndSpinCount(&ListLock, 4000))" in source["src/hooks_bugfixes.cpp"] and
        "FixFileLoadRace: unable to initialize request-list lock" in source["src/hooks_bugfixes.cpp"]),
       ("network hook checks WSAStartup result", "const int wsaStatus = WSAStartup(0x202, &tmp);" in source["src/hooks_misc.cpp"] and
        "if (wsaStatus != 0)" in source["src/hooks_misc.cpp"]),
       ("wheel exit hook retains finalized FFB v0.2 ExitProcess lookup",
        'GetProcAddress(GetModuleHandleA("kernel32.dll"), "ExitProcess")' in source["src/hooks_wheel_ffb.cpp"])
    ]
    for label,ok in checks:
        if not ok:raise ValueError(label)
    if "memcpy(GlobalLock(hMem)," in draw:raise ValueError("unchecked GlobalLock use")
    if "GetProcAddress(winmm, " in fps and "auto timeBeginPeriod = (timeBeginPeriod_Fn)GetProcAddress" in fps:
        raise ValueError("unchecked winmm GetProcAddress")
    return len(checks)
def negatives(src):
    cases=[
      ("src/hooks_drawdistance.cpp","void* destination = GlobalLock(hMem);"),
      ("src/hooks_drawdistance.cpp","if (destination)"),
      ("src/hooks_drawdistance.cpp","if (EmptyClipboard() && SetClipboardData(CF_TEXT, hMem))"),
      ("src/hooks_drawdistance.cpp","if (OpenClipboard(nullptr))"),
      ("src/hooks_drawdistance.cpp","GlobalFree(hMem);"),
      ("src/hooks_framerate.cpp","auto timeBeginPeriod = winmm"),
      ("src/hooks_framerate.cpp","auto timeGetDevCaps = winmm"),
      ("src/hooks_framerate.cpp","TIMECAPS caps{ 1, 1 };"),
      ("src/hooks_framerate.cpp","if (!QueryPerformanceFrequency(&qpf) || qpf.QuadPart <= 0)"),
      ("src/hooks_bugfixes.cpp","if (!InitializeCriticalSectionAndSpinCount(&ListLock, 4000))"),
      ("src/hooks_framerate.cpp","if (!SetWaitableTimerEx(Timer, &due, 0, NULL, NULL, NULL, 0))"),
      ("src/hooks_framerate.cpp","WaitForSingleObject(Timer, waitBudgetMs) != WAIT_OBJECT_0"),
      ("src/hooks_framerate.cpp","std::clamp<INT64>((sleepTicks + 9999) / 10000 + 5, 1, 1000)"),
      ("src/hooks_misc.cpp","if (wsaStatus != 0)"),
      ("src/hooks_wheel_ffb.cpp",'GetProcAddress(GetModuleHandleA("kernel32.dll"), "ExitProcess")')]
    for path,token in cases:
       copy=dict(src)
       copy[path]=src[path].replace(token,"__FAIL_CROSS_SOURCE_GUARD__",1)
       if copy[path]==src[path]:raise ValueError("mutation not applied "+token)
       try:verify(copy)
       except ValueError:continue
       raise ValueError("undetected mutation "+token)
    return len(cases)
if __name__=="__main__":
    s={p:(ROOT/p).read_text(encoding="utf-8") for p in
       ["src/hooks_drawdistance.cpp","src/hooks_framerate.cpp","src/hooks_bugfixes.cpp","src/hooks_misc.cpp","src/hooks_wheel_ffb.cpp"]}
    try:
        n=verify(s)
        m=negatives(s) if "--self-test" in sys.argv[1:] else 0
    except ValueError as e:sys.exit("Win32 cross-domain contract FAIL: "+str(e))
    print(f"Win32 cross-domain contracts PASS: {n}, mutation-negative={m}/15, runtime UNTESTED")
