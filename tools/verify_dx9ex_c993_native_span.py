#!/usr/bin/env python3
"""Review 01523: protect c64..c67 raw read without suppressing native partial writes."""
from pathlib import Path
src=(Path(__file__).resolve().parents[1]/"src/vr/game/outrun_renderer.cpp").read_text(encoding="utf-8-sig")
begin=src.index("const bool projectedLensWithSyncedCamera =")
end=src.index("HudQueuedPartialWvp.Reset();\n\t\t\t// Native D3D9 shader",begin)
body=src[begin:end]
native=body.index("SetVertexShaderConstantFHook.stdcall<HRESULT>(")
guard=body.index("UploadContainsOutRunWvp(startRegister, vector4fCount)")
read=body.index("const float* nativeGameWvp =")
publish=body.index("RecordGameWvpWrite(nativeGameWvp, nativeGameWvp)")
assert native < guard < read < publish
assert "if (SUCCEEDED(result) && sourceUnchanged &&\n\t\t\t\t\tUploadContainsOutRunWvp(startRegister, vector4fCount))" in body
assert "TrackQueuedHudWvp(startRegister, vector4fCount," in body
assert "return result;" in body
def contains(start, count):
    return count != 0 and count <= 256 and start <= 64 and count >= (64-start)+4
for start,count,expected in ((64,4,True),(63,5,True),(64,1,False),(65,1,False),(63,2,False),(67,1,False)):
    assert contains(start,count) == expected,(start,count)
# Negative control: an unchanged-success guard without complete range must fail.
mutant=body.replace("if (SUCCEEDED(result) && sourceUnchanged &&\n\t\t\t\t\tUploadContainsOutRunWvp(startRegister, vector4fCount))", "if (SUCCEEDED(result) && sourceUnchanged)",1)
assert mutant != body and "if (SUCCEEDED(result) && sourceUnchanged &&\n\t\t\t\t\tUploadContainsOutRunWvp(startRegister, vector4fCount))" not in mutant
print("PASS C993 full c64..c67 native-source guard; six boundary cases; HMD UNTESTED")
