from pathlib import Path
p=Path("src/vr/d3d11")
frame=(p/"live_game_frame_bridge.cpp").read_text()
backend=(p/"native_backend.cpp").read_text()
shader=(p/"native_sm3_texture_codegen.hpp").read_text()
volume=(p/"live_game_volume_texture.hpp").read_text()
lod=(p/"live_game_mip_lod.hpp").read_text()
assert "D3DRTYPE_VOLUMETEXTURE" in frame
assert "live_game_mip_lod::select" in frame and "textureLod" in frame
assert "capture.texture->GetLOD()" in frame and "capture.cubeTexture->GetLOD()" in frame
assert "state.MinLOD = static_cast<float>(lod.minLevel)" in frame
assert "state.MaxLOD = static_cast<float>(lod.maxLevel)" in frame
assert "source->GetLOD()" in volume and "live_game_mip_lod::select" in volume
assert "sourceLod > maxMipLevel" in lod and "uploadedLevels - 1u" in lod
assert "mirror_volume_texture" in frame and "vertexVolumeSamplerMask" in frame
assert "pixelVolumeSamplerMask" in frame and "captured.volumeTexture.Get()" in frame
assert "CreateTexture3D" in volume and "D3D11_SRV_DIMENSION_TEXTURE3D" in volume
assert "base.Pool == D3DPOOL_MANAGED || base.Pool == D3DPOOL_SYSTEMMEM" in volume
assert "base.Pool == D3DPOOL_DEFAULT" in volume and "D3DUSAGE_DYNAMIC" in volume
assert "D3DFMT_A8B8G8R8" in volume and "D3DFMT_X8B8G8R8" in volume
assert "D3DFMT_R16F" in volume and "D3DFMT_A16B16G16R16F" in volume
assert "bounded_chain_bytes" in volume and "convert_row" in volume
assert "LockBox(" in volume and "UnlockBox(mip)" in volume and "bounded_chain" in volume
assert "D3DSTT_VOLUME" in backend and "Texture3D<float4>" in backend
assert "append_native_sm3_texture3d_sample" in backend
assert "native_sm3_volume_source_components" in shader
print("00975 native SM3 volume texture -> native Draw / fail-closed source: PASS")
