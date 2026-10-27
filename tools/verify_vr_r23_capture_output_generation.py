#!/usr/bin/env python3
"""DXGI output rebind must retire stale capture/menu ownership fail-closed."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / 'vrhost/src/main.cpp').read_text(encoding='utf-8')
R23 = (ROOT / 'vrhost/src/main_r23.cpp').read_text(encoding='utf-8')
WF = (ROOT / '.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')

def body(source: str, signature: str) -> str:
    at = source.index(signature)
    start = source.index('{', at)
    depth = 0
    for pos in range(start, len(source)):
        if source[pos] == '{': depth += 1
        elif source[pos] == '}':
            depth -= 1
            if depth == 0: return source[start:pos + 1]
    raise AssertionError('unclosed ' + signature)

bind = body(MAIN, 'bool BindCaptureOutput(bool initial)')
have = bind.index('haveFrame_ = false;')
generation = bind.index('++captureOutputGeneration_')
release = bind.index('ReleaseCom(duplication_);')
query = bind.index('device_->QueryInterface(')
assert have < release < query
assert generation < release
assert 'stereoSourceValid_ = false;' in bind[:release]
assert 'lastCapturePresentQpc_ = 0;' in bind[:release]
assert 'lastCapturePresentQpcLow_ = 0;' in bind[:release]
assert 'std::uint64_t captureOutputGeneration_ = 1;' in MAIN

assert 'std::uint64_t cachedMenuCaptureGeneration = 0;' in R23
menu = R23[R23.index('const bool currentMenuLetterbox ='):R23.index('// Review 01490:', R23.index('const bool currentMenuLetterbox ='))]
assert 'const std::uint64_t currentMenuCaptureGeneration =' in menu
assert 'compositor.captureOutputGeneration_' in menu
assert 'cachedMenuCaptureGeneration !=' in menu
assert 'currentMenuCaptureGeneration' in menu
assert 'cachedMenuProjectionValid = false;' in menu
assert menu.index('cachedMenuCaptureGeneration !=') < menu.index('cachedMenuProjectionValid = false;')

assert WF.count('tools/verify_vr_r23_capture_output_generation.py') == 2

# Destructive controls: old ordering and cache key omission must be detectable.
bad_bind = bind.replace('haveFrame_ = false;', '/* stale haveFrame */', 1)
assert 'haveFrame_ = false;' not in bad_bind[:bad_bind.index('ReleaseCom(duplication_);')]
bad_menu = menu.replace('cachedMenuCaptureGeneration !=\n                            currentMenuCaptureGeneration', 'false', 1)
assert bad_menu != menu
assert 'cachedMenuCaptureGeneration !=' not in bad_menu
print('PASS R23 output rebind retires stale capture before teardown and menu cache keys source generation; HMD UNTESTED')
