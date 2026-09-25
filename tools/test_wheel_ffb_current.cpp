// Host-only tests execute production headers. No Windows/DirectInput device needed.
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
struct D3DVECTOR { float x=0, y=0, z=0; };
struct D3DMATRIX { float _11=1,_12=0,_13=0,_14=0,_21=0,_22=1,_23=0,_24=0,_31=0,_32=0,_33=1; };
struct EVWORK_CAR { D3DVECTOR position_14, spd_mb_20; D3DMATRIX matrix_70; };
#include "hooks_wheel_vehicle_dynamics.hpp"
#include "wheel_ffb_math.hpp"
#include "wheel_ffb_ps2.hpp"
static int checks = 0;
void require(bool b, const char* msg) { ++checks; if (!b) { std::cerr << msg << '\n'; std::exit(1); } }
void heading(EVWORK_CAR& c, float a) { c.matrix_70._11=std::cos(a);c.matrix_70._13=-std::sin(a);c.matrix_70._31=std::sin(a);c.matrix_70._33=std::cos(a); }
void step(WheelVehicleDynamics& d, EVWORK_CAR& c, float a=0, float beta=0, float steer=0, float speed=.5f) {
 heading(c,a);c.position_14.x+=std::sin(a+beta);c.position_14.z+=std::cos(a+beta);d.update(&c,steer,speed,0);
}
int main() {
 using namespace WheelFFBMath;
 require(sanitize_model(-10)==Model::ModernDD&&sanitize_model(99)==Model::PS2OriginalExperimental,"FFB model setting clamps");
 require(model_uses_modern_sat(Model::ModernDD)&&model_uses_modern_sat(Model::ArcadeHybrid),"modern SAT models");
 require(!model_uses_modern_sat(Model::ArcadeOriginal)&&!model_uses_modern_sat(Model::PS2OriginalExperimental),"original modes do not claim modern SAT");
 require(model_uses_arcade_events(Model::ArcadeOriginal)&&model_uses_arcade_events(Model::ArcadeHybrid),"arcade event models");
 require(std::abs(frequency_hz_from_period_ms(70.0f)-(1000.0f/70.0f))<1e-6f,"arcade road 70ms period converts to host Hz");
 require(frequency_hz_from_period_ms(0.0f)==0.0f,"invalid zero period is rejected");
 require(frequency_hz_from_period_ms(std::numeric_limits<float>::quiet_NaN())==0.0f,"NaN period is rejected");
 require(!crash_speed_drop_fallback(.057f,.90f),"normal logged deceleration does not trigger crash fallback");
 require(!crash_speed_drop_fallback(.12f,.90f),"crash fallback threshold is strict");
 require(crash_speed_drop_fallback(.121f,.90f),"severe deceleration above threshold triggers fallback");
 require(!crash_speed_drop_fallback(.36f,.10f),"near-stop speed does not trigger emergency crash fallback");
 require(std::abs(crash_speed_drop_severity(.12f))<1e-6f,"crash fallback severity starts at zero");
 require(std::abs(crash_speed_drop_severity(.36f)-1.0f)<1e-6f,"crash fallback severity reaches one at captured large-impact bound");
 require(crash_speed_drop_severity(std::numeric_limits<float>::quiet_NaN())==0.0f,"crash fallback severity rejects NaN");
 require(std::abs(arcade_gear_sine_force(0,1.0f))<1e-6f,"arcade gear Sine starts at zero phase");
 require(arcade_gear_sine_force(4,1.0f)>0.09f,"arcade gear Sine reaches positive lobe near quarter cycle");
 require(arcade_gear_sine_force(11,1.0f)<-0.09f,"arcade gear Sine reaches negative lobe");
 require(std::abs(arcade_gear_sine_force(4,.5f)-.5f*arcade_gear_sine_force(4,1.0f))<1e-6f,"arcade gear host scaler is linear");
 require(arcade_gear_sine_force(ArcadeGearEventFrames,1.0f)==0.0f,"arcade gear Sine stops after 240ms event window");
 require(std::abs(compose_arcade_directional_surface(-.7f,.7f,true)-.7f)<1e-6f,"arcade right transition overrides opposite sustained force");
 require(std::abs(compose_arcade_directional_surface(.7f,-.7f,true)+.7f)<1e-6f,"arcade left transition overrides opposite sustained force");
 require(std::abs(compose_arcade_directional_surface(.4f,-.8f,false)-.4f)<1e-6f,"arcade sustained force remains when no transition is active");
 require(std::abs(arcade_speed_strength(.10f)-.10f)<1e-6f,"arcade first speed step");
 require(std::abs(arcade_speed_strength(.20f)-.20f)<1e-6f,"arcade second speed step");
 require(std::abs(arcade_speed_strength(.50f)-.50f)<1e-6f,"arcade mid speed step");
 require(std::abs(arcade_speed_strength(.90f)-.90f)<1e-6f,"arcade upper speed step");
 require(std::abs(arcade_speed_strength(1.20f)-1.00f)<1e-6f,"arcade top speed step");
 require(arcade_speed_strength(std::numeric_limits<float>::quiet_NaN())==0.0f,"arcade speed rejects NaN");

 // Retail PS2 translation invariants recovered from SLPM_666.28.
 require(std::abs(WheelFFBPS2::drive_factor(.875f)-1.0f)<1e-6f,"PS2 retail drive factor reaches one at field_1C4 0.875");
 require(std::abs(WheelFFBPS2::drive_factor(.4375f)-.5f)<1e-6f,"PS2 retail drive factor midpoint");
 require(WheelFFBPS2::drive_factor(std::numeric_limits<float>::quiet_NaN())==0.0f,"PS2 drive factor rejects NaN");
 require(WheelFFBPS2::spring_saturation_raw(0.0f)==15,"PS2 spring low-speed saturation");
 require(WheelFFBPS2::spring_saturation_raw(1.0f)==60,"PS2 spring high-speed saturation");
 require(std::abs(WheelFFBPS2::spring_coefficient_norm()-200.0f/255.0f)<1e-6f,"PS2 spring coefficient 200/255");
 require(WheelFFBPS2::damper_coefficient_raw(0.0f)==10,"PS2 damper low-speed coefficient");
 require(WheelFFBPS2::damper_coefficient_raw(1.0f)==0,"PS2 damper fades at retail drive factor one");
 require(WheelFFBPS2::triangle_period_raw(0.0f)==100,"PS2 Triangle base period field");
 require(WheelFFBPS2::triangle_period_raw(1.0f)==160,"PS2 Triangle high-speed period field");
 require(std::abs(WheelFFBPS2::triangle_frequency_hz_for_directinput(0.0f)-10.0f)<1e-6f,"PS2 host Triangle 100ms translation");
 require(std::abs(WheelFFBPS2::triangle_frequency_hz_for_directinput(1.0f)-6.25f)<1e-6f,"PS2 host Triangle 160ms translation");
 require(std::abs(WheelFFBPS2::triangle_wave(0.0f)+1.0f)<1e-6f,"PS2 Triangle starts at negative peak");
 require(std::abs(WheelFFBPS2::triangle_wave(0.25f)-0.0f)<1e-6f,"PS2 Triangle quarter-cycle zero");
 require(std::abs(WheelFFBPS2::triangle_wave(0.5f)-1.0f)<1e-6f,"PS2 Triangle half-cycle positive peak");
 require(std::abs(WheelFFBPS2::triangle_wave(1.25f)-0.0f)<1e-6f,"PS2 Triangle wraps cycles");
 require(WheelFFBPS2::triangle_wave(std::numeric_limits<float>::quiet_NaN())==0.0f,"PS2 Triangle rejects NaN");
 require(std::abs(WheelFFBPS2::constant_magnitude_cap_norm()-220.0f/255.0f)<1e-6f,"PS2 constant cap 220/255");
 require(std::abs(WheelFFBPS2::surface_speed_factor(.50f)-.50f)<1e-6f,"PS2 periodic surface speed factor");
 require(WheelFFBPS2::surface_speed_factor(2.0f)==1.0f,"PS2 periodic surface speed factor caps at one");
 require(WheelFFBPS2::surface_speed_factor(std::numeric_limits<float>::quiet_NaN())==0.0f,"PS2 periodic surface speed factor rejects NaN");
 require(WheelFFBPS2::periodic_magnitude_raw(.50f,1.0f,1.0f)==25,"PS2 periodic raw magnitude below threshold");
 require(WheelFFBPS2::periodic_magnitude_raw(.54f,1.0f,1.0f)==27,"PS2 periodic raw magnitude threshold");
 require(WheelFFBPS2::periodic_magnitude_raw(.70f,1.0f,1.0f)==35,"PS2 periodic retail magnitude scale 50");
 require(WheelFFBPS2::periodic_magnitude_norm(.50f,1.0f,1.0f)==0.0f,"PS2 periodic raw values below 27 are suppressed");
 require(std::abs(WheelFFBPS2::periodic_magnitude_norm(.54f,1.0f,1.0f)-27.0f/255.0f)<1e-6f,"PS2 periodic threshold is inclusive at raw 27");
 require(std::abs(WheelFFBPS2::periodic_magnitude_norm(.70f,1.0f,1.0f)-35.0f/255.0f)<1e-6f,"PS2 periodic normalized retail magnitude");
 require(WheelFFBPS2::periodic_magnitude_raw(.90f,.50f,1.0f)==23,"PS2 periodic source includes min(field_1C4,1) speed factor");
 require(std::abs(WheelFFBPS2::retail_wheel_level_scale(1)-2.0f/11.0f)<1e-6f,"PS2 retail wheel level 1 scale");
 require(std::abs(WheelFFBPS2::retail_wheel_level_scale(10)-1.0f)<1e-6f,"PS2 retail wheel level 10 scale");
 require(std::abs(WheelFFBPS2::surface_envelope(.30f,0.0f,0.0f)-.30f)<1e-6f,"PS2 surface boost starts strictly above 0.30");
 require(std::abs(WheelFFBPS2::surface_envelope(.31f,-.5f,0.0f)-.3875f)<1e-6f,"PS2 surface first car-field predicate boosts by 1.25");
 require(std::abs(WheelFFBPS2::surface_envelope(.80f,0.0f,.5f)-1.0f)<1e-6f,"PS2 surface second car-field predicate boosts by 1.25");
 require(std::abs(WheelFFBPS2::surface_envelope(.90f,0.0f,0.0f)-1.125f)<1e-6f,"PS2 surface envelope preserves retail headroom above one");
 require(std::abs(WheelFFBPS2::surface_envelope(.90f,-.10f,.10f)-.90f)<1e-6f,"PS2 surface envelope stays unboosted when both strict predicates fail");
 require(WheelFFBPS2::surface_envelope(std::numeric_limits<float>::quiet_NaN(),0.0f,0.0f)==0.0f,"PS2 surface envelope rejects NaN roughness");
 require(WheelFFBPS2::periodic_magnitude_raw(1.125f,1.0f,1.0f)==56,"PS2 periodic magnitude retains boosted 1.125 envelope");
 require(WheelFFBPS2::retail_wheel_level_scale(0)==0.0f,"PS2 retail wheel level zero disables feedback");
 require(WheelFFBPS2::retail_wheel_level_scale(11)==0.0f,"PS2 invalid wheel level is rejected");
 require(WheelFFBPS2::periodic_magnitude_raw(.90f,1.0f,1.0f,WheelFFBPS2::retail_wheel_level_scale(5))==25,"PS2 periodic accepts recovered wheel-level scaler");
 require(WheelFFBPS2::periodic_magnitude_raw(std::numeric_limits<float>::quiet_NaN(),1.0f,1.0f)==0,"PS2 periodic magnitude rejects NaN");

 auto engineIdle=estimate_engine_haptics(0.0f,0,0.0f);
 require(engineIdle.rpmNorm>=.08f&&engineIdle.rpmNorm<.20f,"engine idle RPM estimate");
 require(engineIdle.frequencyHz>=13.0f&&engineIdle.frequencyHz<16.0f,"engine idle haptic frequency");
 auto engineFree=estimate_engine_haptics(0.0f,0,1.0f);
 require(engineFree.rpmNorm>engineIdle.rpmNorm&&engineFree.frequencyHz>engineIdle.frequencyHz,"free-rev haptic rises with throttle");
 auto engineGear1=estimate_engine_haptics(.15f,1,.5f);
 auto engineGear2=estimate_engine_haptics(.15f,2,.5f);
 require(engineGear1.rpmNorm>engineGear2.rpmNorm,"upshift lowers estimated RPM at equal road speed");
 require(engineGear1.frequencyHz<=24.0001f&&engineGear1.amplitudeScale<=1.0001f,"engine haptic bounded");
 require(estimate_engine_haptics(std::numeric_limits<float>::quiet_NaN(),99,std::numeric_limits<float>::quiet_NaN()).frequencyHz>=13.0f,"engine haptic rejects non-finite inputs");
 require(pneumatic_sat_shape(0)==0,"SAT zero");
 require(pneumatic_sat_shape(std::numeric_limits<float>::quiet_NaN())==0,"SAT NaN");
 require(lateral_force_shape(.32f)>.999f,"Fy proxy saturates in deep slip");
 require(pneumatic_sat_shape(.12f)>.90f,"pneumatic SAT strong in normal loaded corner");
 require(pneumatic_sat_shape(.16f)>.98f,"pneumatic SAT peaks near prior 0.16rad region");
 require(pneumatic_sat_shape(.32f)<.50f,"pneumatic trail falls in deep understeer");
 require(combined_sat_shape(.16f,.25f)<=1.000001f,"combined SAT bounded");
 require(mechanical_sat_shape(.12f,.25f)>0.10f,"mechanical trail acts in normal loaded corner");
 require(mechanical_sat_shape(.32f,.25f)>mechanical_sat_shape(.12f,.25f),"mechanical term follows front lateral force");
 require(combined_sat_shape(.32f,.25f)>pneumatic_sat_shape(.32f),"total trail preserves deep-slip torque");
 require(combined_sat_shape(.32f,0.0f)==pneumatic_sat_shape(.32f),"mechanical trail zero is pure pneumatic");
 require(std::abs(combined_sat_shape(.32f,.25f)-combined_sat_shape(-.32f,.25f))<1e-6f,"SAT shape symmetry");
 require(pneumatic_sat_shape(.20f,.28f)<pneumatic_sat_shape(.20f,.20f),"phase-led growing slip drops pneumatic trail sooner");
 require(pneumatic_sat_shape(.20f,.12f)>pneumatic_sat_shape(.20f,.20f),"phase-led recovering slip restores pneumatic trail sooner");
 for(int i=0;i<=7000;++i) {float a=i*.0001f;float p=pneumatic_sat_shape(a),c=combined_sat_shape(a,.25f);require(std::isfinite(p)&&p>=0&&p<=1.000001f,"pneumatic bounds");require(std::isfinite(c)&&c>=0&&c<=1.000001f,"combined bounds");}
 require(soft_saturate(.5f)==.5f,"soft clip linear midrange");
 require(std::abs(soft_saturate(-.5f)+.5f)<1e-6,"soft clip symmetry");
 require(soft_saturate(1.0f)>.90f&&soft_saturate(1.0f)<1.0f,"soft clip late knee");
 require(soft_saturate(2.0f)==1.0f&&soft_saturate(-2.0f)==-1.0f,"soft clip cap");
 float clipPrev=0; for(int i=0;i<=2000;++i){float x=i*.001f,y=soft_saturate(x);require(std::isfinite(y)&&y>=clipPrev-1e-6f&&y<=1.000001f,"soft clip monotonic");clipPrev=y;}
 require(physics_return_relief(.15f,-.08f)==.85f,"countersteer relief");
 require(physics_return_relief(.15f,.08f)==1,"opposing work no relief");
 ResponseLUT linear{}; require(parse_response_lut("0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1",linear),"linear LUT parses");
 require(std::abs(apply_response_lut(.55f,linear)-.55f)<1e-5f,"linear LUT identity");
 ResponseLUT boosted{}; require(parse_response_lut("0,0.15,0.25,0.35,0.45,0.55,0.65,0.75,0.84,0.92,1",boosted),"boost LUT parses");
 require(apply_response_lut(.10f,boosted)>.10f,"LUT can compensate low-force deadzone");
 require(!parse_response_lut("0,0.2,0.1,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1",boosted),"non-monotonic LUT rejected");
 require(!parse_response_lut("0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1,1",boosted),"nonzero LUT origin rejected");
 WheelVehicleDynamics gap; EVWORK_CAR gapCar; gap.reset();
 for(int i=0;i<80;++i)step(gap,gapCar);
 gap.update(nullptr,0,.5,0);
 step(gap,gapCar,.2f);step(gap,gapCar,.2f);
 require(std::abs(gap.yawRate())<.01f,"short-gap derivative baseline");
 WheelVehicleDynamics resume; EVWORK_CAR resumeCar;resume.reset();for(int i=0;i<80;++i)step(resume,resumeCar);
 require(resume.calibrated()&&resume.motionScale()>0,"resume baseline ready");
 resume.reset_dynamic();
 require(resume.calibrated()&&resume.motionScale()==0&&!resume.sampleValid(),"dynamic reset preserves basis but clears motion scale");
 WheelVehicleDynamics d; EVWORK_CAR c;d.reset();for(int i=0;i<80;++i)step(d,c);
 require(d.calibrated()&&d.forwardAxis()==3,"straight basis calibration");require(d.sampleValid()&&d.activationBlend()==1,"activation");
 for(int i=0;i<40;++i)step(d,c,i*.01f,.20f,.5f);
 require(std::abs(d.yawRate()-.6f)<.02f,"known yaw");require(std::abs(d.bodySlip()-.2f)<.003f,"known beta");
 require(std::isfinite(d.rawFrontSlip())&&d.frontSlipBlend()>.24f,"raw/filtered front slip telemetry active");
 WheelVehicleDynamics low; EVWORK_CAR lowCar; low.reset(); for(int i=0;i<80;++i)step(low,lowCar,0,0,0,.15f); step(low,lowCar,.01f,0,.2f,.15f);
 WheelVehicleDynamics high; EVWORK_CAR highCar; high.reset(); for(int i=0;i<80;++i)step(high,highCar,0,0,0,.90f); step(high,highCar,.01f,0,.2f,.90f);
 require(high.frontSlipBlend()>low.frontSlipBlend(),"front-slip transient speeds up with vehicle speed");

 // v0.2: a rapid steering reversal must change the Physics SAT tyre proxy on
 // the first valid tick instead of carrying stale opposite torque for several
 // frames. The steering-rate predictor should point in the new direction too.
 WheelVehicleDynamics reversal; EVWORK_CAR reversalCar; reversal.reset();
 for(int i=0;i<80;++i)step(reversal,reversalCar);
 for(int i=0;i<8;++i)step(reversal,reversalCar,0,0,.50f,.55f);
 require(reversal.frontSlip()>.08f,"front-slip positive corner established");
 step(reversal,reversalCar,0,0,-.50f,.55f);
 require(reversal.rawFrontSlip()<0&&reversal.frontSlip()<0,"front-slip reversal crosses in one tick");
 require(reversal.steerRate()<0,"steering transient lead follows counter-steer direction");

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
