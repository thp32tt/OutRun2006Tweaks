#pragma once

// Experimental OutRun vehicle-dynamics SAT helper.
// This file deliberately owns no DirectInput objects. It only converts the
// game's car motion/transform into a signed aligning-torque request; the main
// WheelFFBEngine remains the sole hardware-output owner.
class WheelPhysicsSatV1
{
public:
    void reset()
    {
        positionValid_ = false;
        headingValid_ = false;
        ready_ = false;
        forwardAxis_ = 0;
        forwardSign_ = 1.0f;
        prevPosition_ = D3DVECTOR{};
        prevHeading_ = 0.0f;
        bodySlip_ = 0.0f;
        yawRate_ = 0.0f;
        frontSlip_ = 0.0f;
        vLong_ = 0.0f;
        vLat_ = 0.0f;
        spdCorrelation_ = 0.0f;
    }

    float update(
        EVWORK_CAR* car,
        float steer,
        float speedNorm,
        float cornerLoadSmooth,
        float returnRateSmooth,
        float gripLoss,
        float satStrength,
        float satSpeed)
    {
        ready_ = false;
        vLong_ = 0.0f;
        vLat_ = 0.0f;
        spdCorrelation_ = 0.0f;
        if (!car)
            return 0.0f;

        const D3DVECTOR current = car->position_14;
        if (!std::isfinite(current.x) || !std::isfinite(current.z))
            return 0.0f;

        if (!positionValid_)
        {
            prevPosition_ = current;
            positionValid_ = true;
            return 0.0f;
        }

        const float dx = current.x - prevPosition_.x;
        const float dz = current.z - prevPosition_.z;
        prevPosition_ = current;
        const float motionLen = std::sqrt(dx * dx + dz * dz);
        if (!std::isfinite(motionLen) || motionLen <= 0.00001f)
            return 0.0f;

        const float motionX = dx / motionLen;
        const float motionZ = dz / motionLen;

        // matrix_B0 is known to be the display transform and can be touched by
        // frame interpolation. matrix_70 is therefore the first physics/body
        // transform candidate. Calibrate whether the car model's forward axis
        // is local X or local Z only on a reasonably straight rolling sample,
        // and never switch it during a drift.
        const D3DMATRIX& body = car->matrix_70;
        if (forwardAxis_ == 0 && speedNorm > 0.12f && cornerLoadSmooth < 0.18f)
        {
            const float xLen = std::sqrt(body._11 * body._11 + body._13 * body._13);
            const float zLen = std::sqrt(body._31 * body._31 + body._33 * body._33);
            if (xLen > 0.0001f && zLen > 0.0001f)
            {
                const float xDot =
                    (body._11 / xLen) * motionX + (body._13 / xLen) * motionZ;
                const float zDot =
                    (body._31 / zLen) * motionX + (body._33 / zLen) * motionZ;
                forwardAxis_ = std::abs(zDot) >= std::abs(xDot) ? 3 : 1;
                const float chosen = forwardAxis_ == 3 ? zDot : xDot;
                forwardSign_ = chosen >= 0.0f ? 1.0f : -1.0f;
            }
        }

        if (forwardAxis_ == 0)
            return 0.0f;

        float forwardX = forwardAxis_ == 3 ? body._31 : body._11;
        float forwardZ = forwardAxis_ == 3 ? body._33 : body._13;
        forwardX *= forwardSign_;
        forwardZ *= forwardSign_;
        const float forwardLen = std::sqrt(forwardX * forwardX + forwardZ * forwardZ);
        if (!std::isfinite(forwardLen) || forwardLen <= 0.0001f)
            return 0.0f;
        forwardX /= forwardLen;
        forwardZ /= forwardLen;

        // Right-positive car-local motion. Only direction is required here, so
        // position delta is safe even before OutRun's world-speed scale is known.
        const float rightX = forwardZ;
        const float rightZ = -forwardX;
        vLong_ = dx * forwardX + dz * forwardZ;
        vLat_ = dx * rightX + dz * rightZ;
        const float rawBodySlip = std::clamp(
            std::atan2(vLat_, std::max(std::abs(vLong_), 0.00001f)),
            -0.70f, 0.70f);
        bodySlip_ += (rawBodySlip - bodySlip_) * 0.18f;

        const float heading = std::atan2(forwardX, forwardZ);
        if (!headingValid_)
        {
            prevHeading_ = heading;
            headingValid_ = true;
            return 0.0f;
        }

        constexpr float Pi = 3.14159265359f;
        constexpr float TwoPi = 6.28318530718f;
        float headingDelta = heading - prevHeading_;
        prevHeading_ = heading;
        while (headingDelta > Pi)
            headingDelta -= TwoPi;
        while (headingDelta < -Pi)
            headingDelta += TwoPi;
        if (std::abs(headingDelta) >= 0.35f)
            return 0.0f;

        const float rawYawRate = std::clamp(headingDelta * 60.0f, -3.5f, 3.5f);
        yawRate_ += (rawYawRate - yawRate_) * 0.20f;

        // Bicycle-model inspired front-slip proxy:
        // alpha_f ~= road-wheel-angle - beta - a*r/v.
        // The game's world velocity scale is not calibrated yet, so a*r/v is a
        // bounded speed-dependent time constant for v1 rather than fake metres.
        constexpr float RoadWheelLockRad = 0.52f;
        const float roadWheelAngle = steer * RoadWheelLockRad;
        const float yawLeadSeconds = 0.10f - 0.045f * speedNorm;
        const float rawFrontSlip = std::clamp(
            roadWheelAngle - bodySlip_ - yawRate_ * yawLeadSeconds,
            -0.70f, 0.70f);
        frontSlip_ += (rawFrontSlip - frontSlip_) * 0.22f;

        // Track whether spd_mb_20 is a world-space velocity vector. It is not
        // used for force yet: if this correlation stays near +/-1 during a lap,
        // v2 can switch from position differencing to the direct game vector.
        const float spdX = car->spd_mb_20.x;
        const float spdZ = car->spd_mb_20.z;
        const float spdLen = std::sqrt(spdX * spdX + spdZ * spdZ);
        if (std::isfinite(spdLen) && spdLen > 0.0001f)
            spdCorrelation_ = (spdX / spdLen) * motionX + (spdZ / spdLen) * motionZ;

        const float slipAbs = std::abs(frontSlip_);
        if (slipAbs <= 0.004f || speedNorm <= 0.04f)
            return 0.0f;

        // Pneumatic-trail-like response: rise to a peak around 9 degrees front
        // slip, then unload as the tyre slides more deeply instead of increasing
        // forever like a generic centering spring.
        constexpr float HalfPi = 1.57079632679f;
        const float slipX = slipAbs / 0.16f;
        const float trailShape = slipX <= 1.0f
            ? std::sin(slipX * HalfPi)
            : std::exp(-(slipX - 1.0f) * 0.90f);

        const float slideT = std::clamp(
            (std::abs(bodySlip_) - 0.12f) / 0.28f, 0.0f, 1.0f);
        const float slideSmooth = slideT * slideT * (3.0f - 2.0f * slideT);
        const float physicsGrip = 1.0f - 0.70f * gripLoss * slideSmooth;
        const float physicsLoad = 0.62f + 0.48f * cornerLoadSmooth;
        const float returnRelief = 1.0f - 0.15f * returnRateSmooth;

        const float torque =
            (frontSlip_ > 0.0f ? -1.0f : 1.0f) *
            trailShape * satSpeed * physicsLoad * physicsGrip *
            returnRelief * satStrength;
        ready_ = std::isfinite(torque);
        return ready_ ? torque : 0.0f;
    }

    bool ready() const { return ready_; }
    int forwardAxis() const { return forwardAxis_; }
    float bodySlip() const { return bodySlip_; }
    float yawRate() const { return yawRate_; }
    float frontSlip() const { return frontSlip_; }
    float vLong() const { return vLong_; }
    float vLat() const { return vLat_; }
    float spdCorrelation() const { return spdCorrelation_; }

private:
    bool positionValid_ = false;
    bool headingValid_ = false;
    bool ready_ = false;
    int forwardAxis_ = 0;
    float forwardSign_ = 1.0f;
    D3DVECTOR prevPosition_{};
    float prevHeading_ = 0.0f;
    float bodySlip_ = 0.0f;
    float yawRate_ = 0.0f;
    float frontSlip_ = 0.0f;
    float vLong_ = 0.0f;
    float vLat_ = 0.0f;
    float spdCorrelation_ = 0.0f;
};
