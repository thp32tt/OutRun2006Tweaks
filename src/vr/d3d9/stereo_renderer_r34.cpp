// R34 compatibility final-TU shim.
//
// The former R34 Reset/Present/draw detours, install worker, replay-health sync,
// terminal status publication, and compatibility Hook registration now all live
// in the R33 final dispatcher. This wrapper remains only because build matrices
// still select stereo_renderer_r34.cpp as the final translation unit.
//
// Do not add Hook objects, install state, polling, workers, or D3D9 detours here.

#include "stereo_renderer_r33.cpp"
