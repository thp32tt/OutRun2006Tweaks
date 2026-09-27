// R70 production stereo owner.
// This file is the only stereo translation unit compiled by the normal target.
// Historical Rxx files remain implementation layers until they are extracted
// into role-based modules; selecting a diagnostic path changes only this facade.

#if defined(OUTRUN_VR_SAFE_DRAW_COMPARE)
#include "stereo_renderer_r26_compare.cpp"
#elif defined(OUTRUN_VR_C1_COMPARE)
#include "stereo_renderer_r29_c1_compare.cpp"
#elif defined(OUTRUN_VR_C2_COMPARE)
#include "stereo_renderer_r30_c2_compare.cpp"
#elif defined(OUTRUN_VR_R26_HUD_COMPARE)
#include "stereo_renderer_r30_r26_safe.cpp"
#else
#include "stereo_renderer_r34.cpp"
#endif
