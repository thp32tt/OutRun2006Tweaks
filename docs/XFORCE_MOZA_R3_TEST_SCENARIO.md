# MOZA R3 X-Force validation scenario

## Starting settings
- FeedbackCharacter = Modern DD (0)
- PhysicsSAT = true
- XForceGain = 1.00
- XForceMix = 0.50 (not consumed in Modern DD)
- XForceInvert = false
- XForceCapture60Hz = true only for this capture
- Keep the existing v0.2 Spring/Damper/SteeringWeight tuning unchanged.
- Abort with F11/panic-stop if force direction is wrong, oscillation is violent, or steering force persists while stopped.

## One-pass sequence
1. Stationary baseline, 10 s: 5 s centred, then ~25% left/right while stopped.
2. Low-speed slalom, 20 s: gentle alternating steering.
3. Steady left circle, 15 s.
4. Steady right circle, 15 s.
5. Progressive understeer, 15 s: increase steering until front push is obvious.
6. Medium/high-speed same-angle comparison, 20 s.
7. Fast left-right/counter-steer transitions, 15 s.
8. Full stop, 10 s: 5 s still, then move wheel while still stopped.
9. Restart, 15 s: pull away and repeat two slalom inputs.
10. Arcade/Hybrid feel check only after the identity log is reviewed.

## Analyze
```text
python tools/analyze_xforce_capture.py OutRun2006Tweaks.log
```
Record p95/p99/max and best steer/Modern SAT/frontSlip/yaw correlation + lag for dbc/dc0/dc4. A promising force source should follow vehicle load/slip rather than simply mirror steering position, behave symmetrically left/right, and not remain stale at a stop. Correlation is evidence only; confirm the write-site before promoting any field to a production rack/tyre-force source.
