// Host-only tests execute production headers. No Windows/DirectInput device needed.
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
struct D3DVECTOR { float x=0, y=0, z=0; };
struct D3DMATRIX { float _11=1,_12=0,_13=0,_14=0,_21=0,_22=1,_23=0,_24=0,_31=0,_32=0,_33=1; };
struct EVWORK_CAR { D3DVECTOR position_14, spd_mb_20; D3DMATRIX matrix_70; };
#include "hooks_wheel_vehicle_dynamics.hpp"
#include "wheel_ffb_math.hpp"
static int checks = 0;
void require(bool b, const char* msg) { ++checks; if (!b) { std::cerr << msg << '\n'; std::exit(1); } }
void heading(EVWORK_CAR& c, float a) { c.matrix_70._11=std::cos(a);c.matrix_70._13=-std::sin(a);c.matrix_70._31=std::sin(a);c.matrix_70._33=std::cos(a); }
void step(WheelVehicleDynamics& d, EVWORK_CAR& c, float a=0, float beta=0, float steer=0) {
 heading(c,a);c.position_14.x+=std::sin(a+beta);c.position_14.z+=std::cos(a+beta);d.update(&c,steer,.5f,0);
}
int main() {
 using WheelFFBMath::trail_shape;
 require(trail_shape(0)==0,"SAT zero");
 require(trail_shape(std::numeric_limits<float>::quiet_NaN())==0,"SAT NaN");
 float prev=0;
 for(int i=0;i<=7000;++i) {float a=i*.0001f,t=trail_shape(a);require(std::isfinite(t)&&t>=0&&t<=1.000001f,"trail bounds");require(std::abs(t-trail_shape(-a))<1e-6,"trail symmetry");if(i<=1600)require(t>=prev-1e-6,"trail rise");else require(t<=prev+1e-6,"trail fall");prev=t;}
 for(float a: {.004f,.16f,.176f}) {float h=1e-5f;float l=(trail_shape(a)-trail_shape(a-h))/h,r=(trail_shape(a+h)-trail_shape(a))/h; require(std::abs(l-r)<.05f,"trail C1 join");}
 require(trail_shape(.004001f)-trail_shape(.003999f)<.0001f,"no SAT cutoff step");
 require(std::abs(trail_shape(.32f)-std::exp(-.9f))<1e-6,"deep-slip baseline preserved");
 require(WheelFFBMath::soft_saturate(.5f)==.5f,"soft clip linear midrange");
 require(std::abs(WheelFFBMath::soft_saturate(-.5f)+.5f)<1e-6,"soft clip symmetry");
 require(WheelFFBMath::soft_saturate(1.0f)>.90f&&WheelFFBMath::soft_saturate(1.0f)<1.0f,"soft clip late knee");
 require(WheelFFBMath::soft_saturate(2.0f)==1.0f&&WheelFFBMath::soft_saturate(-2.0f)==-1.0f,"soft clip cap");
 float clipPrev=0; for(int i=0;i<=2000;++i){float x=i*.001f,y=WheelFFBMath::soft_saturate(x);require(std::isfinite(y)&&y>=clipPrev-1e-6f&&y<=1.000001f,"soft clip monotonic");clipPrev=y;}
 // Fixed front slip and wheel velocity have the same relief on either side of centre.
 require(WheelFFBMath::physics_return_relief(.15f,-.08f)==.85f,"countersteer relief");
 require(WheelFFBMath::physics_return_relief(.15f,.08f)==1,"opposing work no relief");
 WheelVehicleDynamics gap; EVWORK_CAR gapCar; gap.reset();
 for(int i=0;i<80;++i)step(gap,gapCar);
 gap.update(nullptr,0,.5,0);
 step(gap,gapCar,.2f);step(gap,gapCar,.2f);
 require(std::abs(gap.yawRate())<.01f,"short-gap derivative baseline");
 WheelVehicleDynamics d; EVWORK_CAR c;d.reset();for(int i=0;i<80;++i)step(d,c);
 require(d.calibrated()&&d.forwardAxis()==3,"straight basis calibration");require(d.sampleValid()&&d.activationBlend()==1,"activation");
 for(int i=0;i<40;++i)step(d,c,i*.01f,.20f,.5f);
 require(std::abs(d.yawRate()-.6f)<.01f,"known yaw");require(std::abs(d.bodySlip()-.2f)<.002f,"known beta");
 float beta=d.bodySlip();d.update(nullptr,0,.5,0);require(d.bodySlip()<beta&&!d.sampleValid(),"invalid decay");
 for(int i=0;i<4;++i)d.update(nullptr,0,.5,0);
 require(d.bodySlip()==0&&d.yawRate()==0&&d.frontSlip()==0&&d.activationBlend()==0,"five-invalid clear");
 step(d,c,1);step(d,c,1);step(d,c,1);require(std::abs(d.yawRate())<.001,"reentry does not treat missing interval as one tick");
 c.position_14.x+=1000;d.update(&c,0,.5,0);require(d.discontinuityCount()>0&&d.frontSlip()==0,"warp clear");
 for(int i=0;i<30;++i)step(d,c,0);
 c.position_14.z-=1;d.update(&c,0,.5,0);require(!d.sampleValid()&&d.frontSlip()==0,"reverse proxy disabled");
 d.update(&c,0,0,0);require(d.frontSlip()==0&&d.yawRate()==0&&!d.sampleValid(),"stop clear and invalid dynamic sample");
 std::cout<<checks<<" production-header invariants passed\n";
}
