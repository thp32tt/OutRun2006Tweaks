// R70 production game-renderer owner.
// Safe/R26+HUD uses the proven R23 renderer. Other comparison/full paths keep
// the existing R29 owner. Only this facade is compiled as a translation unit.

#if defined(OUTRUN_VR_SAFE_DRAW_COMPARE) || defined(OUTRUN_VR_R26_HUD_COMPARE)
#include "../game/outrun_renderer_r23.cpp"
#else
#include "../game/outrun_renderer_r29.cpp"
#endif
