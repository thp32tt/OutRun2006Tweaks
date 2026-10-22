#!/usr/bin/env python3
"""Guard real D3D11->D3D9Ex shared frame consumption across consecutive Presents.

Source-level regression only. Live game/D3D9Ex hardware validation is UNTESTED.
"""
from pathlib import Path

source = (Path(__file__).resolve().parents[1] /
          "src/vr/d3d11/native_game_shared_desktop.hpp").read_text(encoding="utf-8")

def correct(s: str) -> bool:
    start = s.find("class NativeSharedDesktopBridge final")
    end = s.find("} // namespace outrun::vr::dx11::live_game_frame", start)
    if start < 0 or end < 0:
        return False
    part = s[start:end]
    init = part.find("ex->CreateQuery(D3DQUERYTYPE_EVENT,")
    fence = part.find("if (d3d9ReadPending_)")
    read = part.find("d3d9ReadFence_->GetData(", fence)
    d3d11_copy = part.find("context->CopyResource(source_.Get(), readySource)")
    failure = part.find("if (FAILED(game->StretchRect(\n                    sharedSurface.Get()")
    failure_issue = part.find("d3d9ReadFence_->Issue(D3DISSUE_END)", failure)
    success_issue = part.find("d3d9ReadFence_->Issue(D3DISSUE_END)", failure_issue + 1)
    success_return = part.find("return true;", success_issue)
    return all(p >= 0 for p in (init, fence, read, d3d11_copy, failure,
                               failure_issue, success_issue, success_return)) and (
        init < fence < read < d3d11_copy < failure < failure_issue < success_issue < success_return
    ) and all(token in part for token in (
        "d3d9ReadFence_.Reset();",
        "d3d9ReadPending_ = false;",
        "if (readDone == S_FALSE) return false;",
        "if (readDone != S_OK) {",
        "D3DGETDATA_FLUSH",
        "faulted_ = true;",
        "d3d9ReadPending_ = true;",
        "backups_[i].Get(), nullptr, backbuffer,",
        "Microsoft::WRL::ComPtr<IDirect3DQuery9> d3d9ReadFence_;",
        "bool d3d9ReadPending_ = false;",
    )) and (
        part.find("d3d9ReadPending_ = false;", read) < d3d11_copy
    ) and (
        # The failure path must also issue a consumer fence after rollback.
        part.find("if (!restored) faulted_ = true;", failure)
            < failure_issue < part.find("return false;", failure_issue)
    ) and (
        # On an event-issue failure, roll back before marking the bridge bad.
        part.find("for (std::uint32_t i = 0u; i < regionCount; ++i)", success_issue)
            < success_return
    )

assert correct(source), "D3D9Ex shared GPU read lifetime is not fenced"
for token in (
    "ex->CreateQuery(D3DQUERYTYPE_EVENT,",
    "if (d3d9ReadPending_)",
    "d3d9ReadFence_->GetData(",
    "if (readDone == S_FALSE) return false;",
    "D3DGETDATA_FLUSH",
    "d3d9ReadFence_->Issue(D3DISSUE_END)",
    "backups_[i].Get(), nullptr, backbuffer,",
):
    mutant = source.replace(token, "/* dropped consumer sync */", 1)
    assert mutant != source and not correct(mutant), token
print("PASS: D3D9Ex read fence, bounded fallback, rollback and reset")
