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

# Update the permanent CI source guards to the optional callback bridge contract.
path = Path('.github/workflows/vr-openxr.yml')
text = path.read_text(encoding='utf-8')
text = replace_once(
    text,
    "              'RequestShadowBridgeStop'\n",
    "              'RequestShadowBridgeStop',\n              'RegisterShadowBridgeStopCallback'\n",
    'game source callback guard')
text = replace_once(
    text,
    "              'OutRunVR::IpcV3::RequestShadowBridgeStop();'\n",
    "              'OutRunVR::IpcV3::RequestRegisteredShadowBridgeStop();'\n",
    'dllmain callback guard')
text = replace_once(
    text,
    "            'process-lifetime worker tracked with stop event',\n",
    "            'process-lifetime worker tracked with stop event',\n            'detach callback registered',\n",
    'binary callback marker')
path.write_text(text, encoding='utf-8', newline='\n')

# Exact postconditions.
checks = {
    'src/vr/ipc/v3_game_shadow_bridge.cpp': [
        '#include "vr/ipc/shadow_lifetime_bridge.hpp"',
        'RegisterShadowBridgeStopCallback(&RequestShadowBridgeStop);',
        'RegisterShadowBridgeStopCallback(nullptr);',
        'detach callback registered',
    ],
    '.github/workflows/vr-openxr.yml': [
        'RequestRegisteredShadowBridgeStop();',
        'RegisterShadowBridgeStopCallback',
        'detach callback registered',
    ],
}
for file, markers in checks.items():
    body = Path(file).read_text(encoding='utf-8')
    for marker in markers:
        if marker not in body:
            raise RuntimeError(f'missing {marker!r} in {file}')

print('shadow lifetime callback registration applied')
