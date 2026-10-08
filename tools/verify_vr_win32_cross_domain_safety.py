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
       ("file loader lock failure refuses hook install",
        "if (!InitializeCriticalSectionAndSpinCount(&ListLock, 4000))" in source["src/hooks_bugfixes.cpp"] and
        "FixFileLoadRace: unable to initialize request-list lock" in source["src/hooks_bugfixes.cpp"])
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
      ("src/hooks_bugfixes.cpp","if (!InitializeCriticalSectionAndSpinCount(&ListLock, 4000))")]
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
       ["src/hooks_drawdistance.cpp","src/hooks_framerate.cpp","src/hooks_bugfixes.cpp"]}
    try:
        n=verify(s)
        m=negatives(s) if "--self-test" in sys.argv[1:] else 0
    except ValueError as e:sys.exit("Win32 cross-domain contract FAIL: "+str(e))
    print(f"Win32 cross-domain contracts PASS: {n}, mutation-negative={m}/10, runtime UNTESTED")
