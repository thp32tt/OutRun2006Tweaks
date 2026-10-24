# Rival-depth review correction — 2026-10-25 KST

TASK_ID: USER-RIVAL-REVIEW-CORRECTION-20261025
Reviewed HEAD: b3ea4439748f154d4f9fefc919ad5be7af3a5922
Historical hook and R26 source: a6f8497c2fbe83959984275c30fbf43aa6a72d55
Scope: review supplied chat conclusions against existing user evidence; no runtime source modification.
RUNTIME_VALIDATION=UNTESTED for current candidate; score_delta=0.

## Confirmed contrary runtime evidence

Existing user Library archive libfile_0a3a8f07ba9c8191b21e4db1c5b618de:
OutRun2_VR_ANALYZE_R26_GOAL_FINAL_SEAT_OFF_DEBUG_CURRENT_FOCUS_CORRECTNESS_20261024T165717245Z-6fbc67b1.zip
Archive SHA256 ca5f24f6e77bbe501b7578a95ac2ee9406ae9693f0ca562cec585c53eb690bc3.
Declared integration SHA 50ea48da3f7308528bd230a250b7e69dc67ca710.
Selected/installed DLL SHA256 098e6f57cb17549a30161eb985258983212640abeb7694115e769f29449bb265; loaded-module hash NOT_ATTESTED.

OutRun2006Tweaks.log:
- line 228, 01:57:22.868 KST: RivalDx11NativeRoute: false.
- line 1098, 01:59:50.997: VR RIVAL EXACT CALC EDGE e8=0xBB6F0 hits=1 anchorValid=1 sourceZ=-258.1944 outputZ=-258.1944.
- line 1099, same time: VR RIVAL PHYSICAL PRODUCER hits=1 anchorValid=1 viewZ=-258.1944 spriteId=2883787.
- Both bounded log families have 15 emitted samples, all anchorValid=1, through hits=1024 at 02:00:02.498. This is sampled evidence, not a claim that every draw was captured.
- Short archive 81c4a685 also logs RivalDx11NativeRoute:false at 02:02:35.180, but has no rival gameplay samples.

Therefore historical source-default/INI disagreement is real, but disabled hooks cannot explain this captured run: exact hook and producer execution are observed with valid anchors. Existing reports that the effective option is wholly unknown, or that toggling it alone establishes recovery, must be corrected.

## Historical source comparison

The supplied before/after description of RivalMarker_sprani is substantially accurate:
historical source calls native sprani then snapshots/clears the anchor and tags appended nodes; current source snapshots/clears before native sprani, wraps direct native execution in the exact projected scope, and tags appended nodes afterward with the same local projectedAnchor.

However, clearing RivalMarkerProjectedInfo does NOT clear the copied local projectedAnchor. The producer log confirms that the copy is valid in the captured run. Merely observing this ordering difference does not prove it caused the regression or that reverting it repairs the physical eye draw. Source-time ownership also covers immediate native draws that post-call tagging alone cannot cover.

Both historical/current rival unprojection use output x/y/z and the same projection divisors. Current ordinal-only camera/cant alternatives do not select the rival producer. Historical R26 R57BuildProjectedMarkerDelta and the current non-ordinal branch retain HeadInverse, relative eye IPD, identity eye orientation, per-eye FOV and eye-minus-base delta. Historical/current rival clip-W gate remains positive-W. This does not prove the complete rendering pipeline is equivalent.

Live-root/reachability/registration-order checks differ from the old direct-list traversal. Do not remove stale-pointer or nested-owner protection solely to resemble old code.

## Evidence gap and next engineering cursor

Trace valid rival projectedAnchor through RegisterSpriteNodeScope, node consumption, effective ProjectedWorldMarker2D, R57BuildProjectedMarkerDelta, and both actual physical GPU eye submissions. Aggregate rank+rival projected counters are not rival-specific completion proof. Existing HUD trace rows for sprite 2883787 carry zero return-address/UNKNOWN diagnostic labels; that return-site diagnostic is not itself proof that the runtime semantic registry lost ownership.

The original 10/9 HMD evidence does not by itself establish which exact renderer build/options the user's latest capture used. Compare exact compiled path and module identity before claiming equivalent historical behavior.

Do not request an identical option-only HMD retry as if it tested a newly restored rendering path. The current package pins false and fixes INI parsing, but the visible depth issue remains unproven.

## Existing build status reconciled

Official TEST/DEBUG aa6468ea82fba8aadc0a90175a368a2af465facf run 40138586556 SUCCESS.
General user TEST b3ea4439748f154d4f9fefc919ad5be7af3a5922 run 40138597564 SUCCESS.
Official artifact 12578119248 was downloaded and both inner SOURCE_SHA, strict INI, RivalDx11NativeRoute=false, launch argument override, batch/PS runner/INI/DLL/host presence verified.
These are build/package facts, not optical recovery. The supplied chat's 'CI in progress' is stale.
