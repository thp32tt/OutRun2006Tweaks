#!/usr/bin/env python3
"""DX9Ex 01514 bounded 2-strip full-surface D3DRECT proof.

No GPU/HMD validation. Exhaustive small-grid independent pixel oracle.
"""
from pathlib import Path

source=(Path(__file__).resolve().parents[1]/
        "src/vr/d3d9/stereo_renderer_r7.inc").read_text(encoding="utf-8-sig")
fn=source.split("bool ClearCoversStereoBackbuffer(",1)[1].split(
    "bool DepthDescMatches(",1)[0]
assert "if(!ViewportCoversStereoBackbuffer(device))return false;" in fn
assert "if(count==0)return true;" in fn
assert "if(!rects)return false;" in fn
assert "if(count==2)" in fn
assert "const bool validA=a.x2>a.x1&&a.y2>a.y1;" in fn
assert "const bool validC=c.x2>c.x1&&c.y2>c.y1;" in fn
assert "const bool fullHeight=a.y1<=0&&c.y1<=0&&" in fn
assert "const bool fullWidth=a.x1<=0&&c.x1<=0&&" in fn
assert "a.y2>=height&&c.y2>=height;" in fn
assert "a.x2>=width&&c.x2>=width;" in fn
assert "(a.x1<=0&&c.x2>=width&&a.x2>=c.x1)" in fn
assert "(c.x1<=0&&a.x2>=width&&c.x2>=a.x1)" in fn
assert "(a.y1<=0&&c.y2>=height&&a.y2>=c.y1)" in fn
assert "(c.y1<=0&&a.y2>=height&&c.y2>=a.y1)" in fn

def accepted(a,c,w,h):
    x1,y1,x2,y2=a
    u1,v1,u2,v2=c
    if x2<=x1 or y2<=y1 or u2<=u1 or v2<=v1:
        return False
    full_height=y1<=0 and v1<=0 and y2>=h and v2>=h
    full_width=x1<=0 and u1<=0 and x2>=w and u2>=w
    return (full_height and ((x1<=0 and u2>=w and x2>=u1) or
                             (u1<=0 and x2>=w and u2>=x1))) or (
            full_width and ((y1<=0 and v2>=h and y2>=v1) or
                            (v1<=0 and y2>=h and v2>=y1)))

def pixels_cover(a,c,w,h):
    return all((a[0]<=x<a[2] and a[1]<=y<a[3]) or
               (c[0]<=x<c[2] and c[1]<=y<c[3])
               for x in range(w) for y in range(h))

cases=0
accepted_count=0
for w,h in ((4,3),(3,4),(8,5)):
    xvals=(-1,0,1,w//2,w-1,w,w+1)
    yvals=(-1,0,1,h//2,h-1,h,h+1)
    for split in range(-1,w+2):
        for delta in (-2,-1,0,1,2):
            for inset in (-1,0,1):
                a=(-1,inset,split,h+1)
                c=(split+delta,inset,w+1,h+1)
                for left,right in ((a,c),(c,a)):
                    pred=accepted(left,right,w,h)
                    if pred:
                        assert pixels_cover(left,right,w,h), (w,h,left,right)
                        accepted_count+=1
                    cases+=1
    for split in range(-1,h+2):
        for delta in (-2,-1,0,1,2):
            for inset in (-1,0,1):
                a=(inset,-1,w+1,split)
                c=(inset,split+delta,w+1,h+1)
                for top,bottom in ((a,c),(c,a)):
                    pred=accepted(top,bottom,w,h)
                    if pred:
                        assert pixels_cover(top,bottom,w,h), (w,h,top,bottom)
                        accepted_count+=1
                    cases+=1
    for x in xvals:
        for y in yvals:
            a=(0,0,x,h)
            c=(x,y,w,h)
            if accepted(a,c,w,h):
                assert pixels_cover(a,c,w,h)
            cases+=1

assert accepted((0,0,2,3),(2,0,4,3),4,3)
assert accepted((0,0,4,1),(0,1,4,3),4,3)
assert accepted((2,0,4,3),(0,0,2,3),4,3)
assert not accepted((0,0,1,3),(2,0,4,3),4,3)
assert not accepted((0,0,4,1),(0,2,4,3),4,3)
assert not accepted((0,0,2,2),(2,0,4,3),4,3)
assert not accepted((0,0,0,3),(0,0,4,3),4,3)

# Destructive mutations must violate at least one exact source guard.
mutations=(
    ("if(count==2)","if(count>=2)"),
    ("a.x2>=c.x1","a.x2<c.x1"),
    ("a.y2>=c.y1","a.y2<c.y1"),
    ("const bool validA=a.x2>a.x1&&a.y2>a.y1;",
     "const bool validA=true;"),
    ("if(!ViewportCoversStereoBackbuffer(device))return false;",
     "if(false)return false;"),
)
guards=(
    "if(count==2)","a.x2>=c.x1","a.y2>=c.y1",
    "const bool validA=a.x2>a.x1&&a.y2>a.y1;",
    "if(!ViewportCoversStereoBackbuffer(device))return false;",
)
for (old,bad),guard in zip(mutations,guards):
    assert old in fn
    assert guard not in fn.replace(old,bad,1)
print(f"PASS bounded R7 two-strip union: {cases} deterministic cases, "
      f"{accepted_count} accepted coverage samples, five destructive controls")
print("RUNTIME_VALIDATION=UNTESTED")
