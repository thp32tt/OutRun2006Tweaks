#include "quest_pcvr/vr_core.hpp"
#include <cmath>

namespace quest_pcvr {
namespace {
bool finite(float a) noexcept { return std::isfinite(a); }
bool finite_vec(Vec3 v) noexcept { return finite(v.x) && finite(v.y) && finite(v.z); }
bool normalized_inverse(Quaternion q, Quaternion& result) noexcept {
    if (!finite(q.x) || !finite(q.y) || !finite(q.z) || !finite(q.w)) return false;
    const double m2 = double(q.x)*q.x + double(q.y)*q.y + double(q.z)*q.z + double(q.w)*q.w;
    if (!std::isfinite(m2) || m2 < 1e-12) return false;
    const float s = static_cast<float>(1.0/std::sqrt(m2));
    result = {-q.x*s, -q.y*s, -q.z*s, q.w*s};
    return true;
}
Vec3 cross(Vec3 a, Vec3 b) noexcept {
    return {a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x};
}
Vec3 rotate(Quaternion q, Vec3 v) noexcept {
    const Vec3 u{q.x,q.y,q.z};
    const Vec3 t0=cross(u,v);
    const Vec3 t{2.f*t0.x,2.f*t0.y,2.f*t0.z};
    const Vec3 w=cross(u,t);
    return {v.x+q.w*t.x+w.x,v.y+q.w*t.y+w.y,v.z+q.w*t.z+w.z};
}
bool valid_fov(Fov a) noexcept {
    constexpr float max_angle = 1.55f; // avoid tangent discontinuity at +/-pi/2
    return finite(a.left) && finite(a.right) && finite(a.down) && finite(a.up)
        && a.left > -max_angle && a.right < max_angle
        && a.down > -max_angle && a.up < max_angle
        && a.left < a.right && a.down < a.up;
}
Visibility one_eye(const EyeView& eye, const StereoViews& view, Vec3 center, float radius) noexcept {
    if (!valid_fov(eye.fov) || !finite_vec(eye.pose.position)) return Visibility::Unknown;
    Quaternion inv{};
    if (!normalized_inverse(eye.pose.orientation, inv)) return Visibility::Unknown;
    const Vec3 relative{center.x-eye.pose.position.x,center.y-eye.pose.position.y,center.z-eye.pose.position.z};
    if (!finite_vec(relative)) return Visibility::Unknown;
    const Vec3 p = rotate(inv, relative);
    if (!finite_vec(p)) return Visibility::Unknown;
    const float depth=-p.z; // OpenXR local -Z is forward
    if (depth + radius < view.near_plane || depth - radius > view.far_plane) return Visibility::Culled;
    const float l=std::tan(eye.fov.left), r=std::tan(eye.fov.right);
    const float d=std::tan(eye.fov.down), u=std::tan(eye.fov.up);
    if (!finite(l) || !finite(r) || !finite(d) || !finite(u)) return Visibility::Unknown;
    // Conservative plane-to-sphere margin, accounting for oblique asymmetric FOV.
    if (p.x < depth*l-radius*std::sqrt(1.f+l*l)) return Visibility::Culled;
    if (p.x > depth*r+radius*std::sqrt(1.f+r*r)) return Visibility::Culled;
    if (p.y < depth*d-radius*std::sqrt(1.f+d*d)) return Visibility::Culled;
    if (p.y > depth*u+radius*std::sqrt(1.f+u*u)) return Visibility::Culled;
    return Visibility::Visible;
}
}
Visibility sphere_in_stereo(const StereoViews& view, Vec3 center, float radius, float margin) noexcept {
    if (!finite_vec(center) || !finite(radius) || radius < 0.f || !finite(margin) || margin < 0.f
        || !finite(view.near_plane) || !finite(view.far_plane) || view.near_plane<=0.f
        || view.far_plane<=view.near_plane || !finite(radius+margin)) return Visibility::Unknown;
    const float r=radius+margin;
    const Visibility a=one_eye(view.eyes[0],view,center,r);
    if (a==Visibility::Visible) return a;
    const Visibility b=one_eye(view.eyes[1],view,center,r);
    if (b==Visibility::Visible) return b;
    return (a==Visibility::Unknown || b==Visibility::Unknown) ? Visibility::Unknown : Visibility::Culled;
}
bool should_render(Visibility r) noexcept { return r!=Visibility::Culled; }
bool valid_stereo_submission(const FrameSubmission& frame) noexcept {
    if (frame.generation==0 || frame.frame_id==0 || frame.pose_sample_id==0 ||
        frame.predicted_display_time_ns<=0) return false;
    if (frame.eyes[0].target_identity==0 || frame.eyes[1].target_identity==0 ||
        frame.eyes[0].target_identity==frame.eyes[1].target_identity) return false;
    for (const auto& eye:frame.eyes) {
        if (eye.generation!=frame.generation || eye.frame_id!=frame.frame_id ||
            eye.pose_sample_id!=frame.pose_sample_id) return false;
    }
    return true;
}
}
