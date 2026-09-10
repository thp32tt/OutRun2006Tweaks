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
        calibrated_ = false;
        sampleValid_ = false;
        torqueActive_ = false;
        forwardAxis_ = 0;
        forwardSign_ = 1.0f;
        calibrationSamples_ = 0;
        calibrationScoreX_ = 0.0f;
        calibrationScoreZ_ = 0.0f;
        calibrationSignedX_ = 0.0f;
        calibrationSignedZ_ = 0.0f;
        calibrationConfidence_ = 0.0f;
        activationBlend_ = 0.0f;
        invalidTicks_ = 0;
        discontinuityCount_ = 0;
        lastTorque_ = 0.0f;
        prevPosition_ = D3DVECTOR{};
        prevHeading_ = 0.0f;
        bodySlip_ = 0.0f;
        yawRate_ = 0.0f;
        frontSlip_ = 0.0f;
        vLong_ = 0.0f;
        vLat_ = 0.0f;
        positionStep_ = 0.0f;
        motionScaleEma_ = 0.0f;
        motionScaleSamples_ = 0;
        spdLen_ = 0.0f;
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
        sampleValid_ = false;
        torqueActive_ = false;
        vLong_ = 0.0f;
        vLat_ = 0.0f;
        positionStep_ = 0.0f;
        spdLen_ = 0.0f;
        spdCorrelation_ = 0.0f;

        if (!car)
            return decay_invalid_sample();

        const D3DVECTOR current = car->position_14;
        if (!std::isfinite(current.x) || !std::isfinite(current.z))
            return decay_invalid_sample();

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
        positionStep_ = std::isfinite(motionLen) ? motionLen : 0.0f;

        // A stop/restart must not inherit the previous corner's beta/yaw/front
        // slip. Keep the already-proven matrix basis, but restart dynamic state
        // and its crossfade before the car moves again.
        if (speedNorm <= 0.04f)
        {
            clear_dynamic_state();
            sampleValid_ = calibrated_;
            return 0.0f;
        }

        if (!std::isfinite(motionLen) || motionLen <= 0.00001f)
            return decay_invalid_sample();

        // Detect restart/warp discontinuities without assuming OutRun world
        // units. Position step is normalized by current speed, then compared
        // with its own rolling scale. A large relative jump clears dynamic SAT
        // history instead of becoming a one-frame lateral-velocity impulse.
        const float motionScale = motionLen / std::max(speedNorm, 0.05f);
        if (motionScaleSamples_ >= 12 &&
            motionScaleEma_ > 0.00001f &&
            motionScale > motionScaleEma_ * 5.0f)
        {
            ++discontinuityCount_;
            clear_dynamic_state();
            return 0.0f;
        }
        if (std::isfinite(motionScale))
        {
            if (motionScaleSamples_ == 0)
                motionScaleEma_ = motionScale;
            else
                motionScaleEma_ += (motionScale - motionScaleEma_) * 0.05f;
            ++motionScaleSamples_;
        }

        const float motionX = dx / motionLen;
        const float motionZ = dz / motionLen;
        const D3DMATRIX& body = car->matrix_70;

        // D3D's OutRun car transforms use row-vector basis/translation layout.
        // The model's local forward axis may be row 1 or row 3, so score both
        // across multiple straight rolling physics ticks. Never commit basis
        // identity from one noisy frame and never recalibrate in a drift.
        if (!calibrated_ &&
            speedNorm > 0.12f &&
            std::abs(steer) < 0.08f &&
            cornerLoadSmooth < 0.12f)
        {
            const float xLen = std::sqrt(body._11 * body._11 + body._13 * body._13);
            const float zLen = std::sqrt(body._31 * body._31 + body._33 * body._33);
            if (std::isfinite(xLen) && std::isfinite(zLen) &&
                xLen > 0.0001f && zLen > 0.0001f)
            {
                const float xDot =
                    (body._11 / xLen) * motionX + (body._13 / xLen) * motionZ;
                const float zDot =
                    (body._31 / zLen) * motionX + (body._33 / zLen) * motionZ;
                calibrationScoreX_ += std::abs(xDot);
                calibrationScoreZ_ += std::abs(zDot);
                calibrationSignedX_ += xDot;
                calibrationSignedZ_ += zDot;
                ++calibrationSamples_;

                constexpr int CalibrationSamplesRequired = 12;
                if (calibrationSamples_ >= CalibrationSamplesRequired)
                {
                    const float invSamples = 1.0f / static_cast<float>(calibrationSamples_);
                    const float xScore = calibrationScoreX_ * invSamples;
                    const float zScore = calibrationScoreZ_ * invSamples;
                    const float bestScore = std::max(xScore, zScore);
                    const float secondScore = std::min(xScore, zScore);
                    calibrationConfidence_ = bestScore - secondScore;

                    // Require both strong motion alignment and clear separation
                    // from the orthogonal basis. If not confident, keep
                    // collecting straight samples instead of guessing.
                    if (bestScore >= 0.85f && calibrationConfidence_ >= 0.25f)
                    {
                        forwardAxis_ = zScore >= xScore ? 3 : 1;
                        const float signedScore = forwardAxis_ == 3
                            ? calibrationSignedZ_
                            : calibrationSignedX_;
                        forwardSign_ = signedScore >= 0.0f ? 1.0f : -1.0f;
                        calibrated_ = true;
                        clear_dynamic_state();
                    }
                }
            }
        }

        if (!calibrated_)
            return 0.0f;

        float forwardX = forwardAxis_ == 3 ? body._31 : body._11;
        float forwardZ = forwardAxis_ == 3 ? body._33 : body._13;
        forwardX *= forwardSign_;
        forwardZ *= forwardSign_;
        const float forwardLen = std::sqrt(forwardX * forwardX + forwardZ * forwardZ);
        if (!std::isfinite(forwardLen) || forwardLen <= 0.0001f)
            return decay_invalid_sample();
        forwardX /= forwardLen;
        forwardZ /= forwardLen;

        // Right-positive car-local motion. Position delta is intentionally used
        // until spd_mb_20's units/coordinate space are proven by telemetry.
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
        {
            ++discontinuityCount_;
            clear_dynamic_state();
            return 0.0f;
        }

        // This helper is called once per OutRun simulation tick. The game
        // physics loop remains fixed at 60 Hz even when rendering >60 FPS.
        const float rawYawRate = std::clamp(headingDelta * 60.0f, -3.5f, 3.5f);
        yawRate_ += (rawYawRate - yawRate_) * 0.20f;

        // Bicycle-model inspired front-slip proxy:
        // alpha_f ~= road-wheel-angle - beta - a*r/v.
        // World velocity units are not calibrated yet, so a*r/v is represented
        // by a bounded speed-dependent time constant for this experimental pass.
        constexpr float RoadWheelLockRad = 0.52f;
        const float roadWheelAngle = steer * RoadWheelLockRad;
        const float yawLeadSeconds = 0.10f - 0.045f * speedNorm;
        const float rawFrontSlip = std::clamp(
            roadWheelAngle - bodySlip_ - yawRate_ * yawLeadSeconds,
            -0.70f, 0.70f);
        frontSlip_ += (rawFrontSlip - frontSlip_) * 0.22f;

        // Measure whether spd_mb_20 is a world-space velocity vector. Keep it
        // telemetry-only until correlation and scale are proven by a real lap.
        const float spdX = car->spd_mb_20.x;
        const float spdZ = car->spd_mb_20.z;
        const float spdLen = std::sqrt(spdX * spdX + spdZ * spdZ);
        if (std::isfinite(spdLen) && spdLen > 0.0001f)
        {
            spdLen_ = spdLen;
            spdCorrelation_ =
                (spdX / spdLen) * motionX + (spdZ / spdLen) * motionZ;
        }

        sampleValid_ = true;
        invalidTicks_ = 0;
        activationBlend_ = std::min(1.0f, activationBlend_ + (1.0f / 24.0f));

        const float slipAbs = std::abs(frontSlip_);
        if (slipAbs <= 0.004f)
        {
            lastTorque_ = 0.0f;
            return 0.0f;
        }

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
        if (!std::isfinite(torque))
            return decay_invalid_sample();

        lastTorque_ = torque;
        torqueActive_ = std::abs(torque) > 0.0001f;
        return torque;
    }

    bool calibrated() const { return calibrated_; }
    bool sampleValid() const { return sampleValid_; }
    bool torqueActive() const { return torqueActive_; }
    int forwardAxis() const { return forwardAxis_; }
    int discontinuityCount() const { return discontinuityCount_; }
    float calibrationConfidence() const { return calibrationConfidence_; }
    float activationBlend() const { return activationBlend_; }
    float bodySlip() const { return bodySlip_; }
    float yawRate() const { return yawRate_; }
    float frontSlip() const { return frontSlip_; }
    float vLong() const { return vLong_; }
    float vLat() const { return vLat_; }
    float positionStep() const { return positionStep_; }
    float motionScale() const { return motionScaleEma_; }
    float spdLen() const { return spdLen_; }
    float spdCorrelation() const { return spdCorrelation_; }

private:
    void clear_dynamic_state()
    {
        headingValid_ = false;
        prevHeading_ = 0.0f;
        bodySlip_ = 0.0f;
        yawRate_ = 0.0f;
        frontSlip_ = 0.0f;
        activationBlend_ = 0.0f;
        invalidTicks_ = 0;
        lastTorque_ = 0.0f;
        torqueActive_ = false;
    }

    float decay_invalid_sample()
    {
        sampleValid_ = false;
        torqueActive_ = false;
        if (!calibrated_)
            return 0.0f;

        // Do not switch force models for a single bad physics sample. Briefly
        // decay the previous Physics SAT request, then reach a safe zero.
        ++invalidTicks_;
        if (invalidTicks_ > 4)
        {
            lastTorque_ = 0.0f;
            return 0.0f;
        }
        lastTorque_ *= 0.55f;
        return lastTorque_;
    }

    bool positionValid_ = false;
    bool headingValid_ = false;
    bool calibrated_ = false;
    bool sampleValid_ = false;
    bool torqueActive_ = false;
    int forwardAxis_ = 0;
    float forwardSign_ = 1.0f;
    int calibrationSamples_ = 0;
    float calibrationScoreX_ = 0.0f;
    float calibrationScoreZ_ = 0.0f;
    float calibrationSignedX_ = 0.0f;
    float calibrationSignedZ_ = 0.0f;
    float calibrationConfidence_ = 0.0f;
    float activationBlend_ = 0.0f;
    int invalidTicks_ = 0;
    int discontinuityCount_ = 0;
    float lastTorque_ = 0.0f;
    D3DVECTOR prevPosition_{};
    float prevHeading_ = 0.0f;
    float bodySlip_ = 0.0f;
    float yawRate_ = 0.0f;
    float frontSlip_ = 0.0f;
    float vLong_ = 0.0f;
    float vLat_ = 0.0f;
    float positionStep_ = 0.0f;
    float motionScaleEma_ = 0.0f;
    int motionScaleSamples_ = 0;
    float spdLen_ = 0.0f;
    float spdCorrelation_ = 0.0f;
};
