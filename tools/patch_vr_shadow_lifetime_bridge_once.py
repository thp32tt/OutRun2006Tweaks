from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected 1 match, found {count}')
    return text.replace(old, new, 1)


path = Path('src/vr/ipc/v3_game_shadow_bridge.cpp')
text = path.read_text(encoding='utf-8')
text = replace_once(
    text,
    '#include "vr/ipc/win32_channel.hpp"\n',
    '#include "vr/ipc/win32_channel.hpp"\n#include "vr/ipc/shadow_lifetime_bridge.hpp"\n',
    'lifetime bridge include')
text = replace_once(
    text,
    'namespace OutRunVR::IpcV3\n{\n    namespace\n',
    'namespace OutRunVR::IpcV3\n{\n    void RequestShadowBridgeStop() noexcept;\n\n    namespace\n',
    'stop callback forward declaration')
text = replace_once(
    text,
    '                ShadowBridgeThreadHandle = thread;\n                spdlog::info("VR v3 shadow: process-lifetime worker tracked with stop event; plugin module pinned");',
    '                ShadowBridgeThreadHandle = thread;\n                RegisterShadowBridgeStopCallback(&RequestShadowBridgeStop);\n                spdlog::info("VR v3 shadow: process-lifetime worker tracked with stop event; plugin module pinned; detach callback registered");',
    'callback registration')
text = replace_once(
    text,
    '    void RequestShadowBridgeStop() noexcept\n    {\n        ShadowBridgeStop.store(true, std::memory_order_release);',
    '    void RequestShadowBridgeStop() noexcept\n    {\n        RegisterShadowBridgeStopCallback(nullptr);\n        ShadowBridgeStop.store(true, std::memory_order_release);',
    'callback unregister')
path.write_text(text, encoding='utf-8', newline='\n')

body = path.read_text(encoding='utf-8')
for marker in (
    '#include "vr/ipc/shadow_lifetime_bridge.hpp"',
    'RegisterShadowBridgeStopCallback(&RequestShadowBridgeStop);',
    'RegisterShadowBridgeStopCallback(nullptr);',
    'detach callback registered',
):
    if marker not in body:
        raise RuntimeError(f'missing {marker!r} in {path}')

print('shadow lifetime callback registration applied')
