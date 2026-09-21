#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <atomic>
#include <cstdint>
#include <cstring>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "vr/ipc/protocol.hpp"
#include "vr/ipc/protocol_v3.hpp"
#include "vr/ipc/shadow_legacy_v2.hpp"
#include "vr/ipc/win32_channel.hpp"

namespace OutRunVR::Host::Diagnostics
{
    namespace
    {
        constexpr std::size_t RollingSampleCount = 100; // 100 ms cadence ~= previous 10 seconds.
        constexpr ULONGLONG CapturePostWindowMs = 2000;

        std::string Timestamp()
        {
            SYSTEMTIME t{};
            GetSystemTime(&t);
            std::ostringstream s;
            s << std::setfill('0') << std::setw(4) << t.wYear << '-'
              << std::setw(2) << t.wMonth << '-' << std::setw(2) << t.wDay << 'T'
              << std::setw(2) << t.wHour << ':' << std::setw(2) << t.wMinute << ':'
              << std::setw(2) << t.wSecond << '.' << std::setw(3) << t.wMilliseconds << 'Z';
            return s.str();
        }

        std::string CaptureStamp()
        {
            SYSTEMTIME t{};
            GetSystemTime(&t);
            std::ostringstream s;
            s << std::setfill('0') << std::setw(4) << t.wYear
              << std::setw(2) << t.wMonth << std::setw(2) << t.wDay << 'T'
              << std::setw(2) << t.wHour << std::setw(2) << t.wMinute
              << std::setw(2) << t.wSecond << std::setw(3) << t.wMilliseconds << 'Z';
            return s.str();
        }

        std::string BoundedString(const char* text, std::size_t capacity)
        {
            if (!text || !capacity) return {};
            std::size_t length = 0;
            while (length < capacity && text[length] != '\0') ++length;
            return std::string(text, length);
        }

        std::string EnvValue(const char* name)
        {
            char buffer[1024]{};
            const DWORD size = GetEnvironmentVariableA(
                name, buffer, static_cast<DWORD>(sizeof(buffer)));
            if (!size || size >= sizeof(buffer))
                return {};
            return std::string(buffer, size);
        }

        class Log
        {
        public:
            Log()
            {
                // Keep same-session restarts instead of destroying the previous
                // diagnostic evidence. The session collector will archive the
                // file after the game/host are closed.
                stream_.open("outrun-vr-watchdog.log",
                    std::ios::out | std::ios::app);
            }
            void Write(const char* level, const std::string& message)
            {
                if (!stream_.is_open()) return;
                stream_ << Timestamp() << ' ' << level << ' ' << message << '\n';
                stream_.flush();
            }
        private:
            std::ofstream stream_;
        };

        template <typename T>
        bool StableReadState(const Ipc::ReadOnlyMapping<T>& mapping, T& out) noexcept
        {
            return mapping.IsOpen() && Ipc::StableRead(mapping.Get(), out);
        }

        bool StableReadFrameRing(const IpcV3::FrameRing* shared,
            IpcV3::FrameRing& out) noexcept
        {
            if (!shared) return false;
            for (int attempt = 0; attempt < 6; ++attempt)
            {
                const std::uint32_t before = shared->publishSequence;
                if (before & 1u) continue;
                MemoryBarrier();
                std::memcpy(&out, shared, sizeof(out));
                MemoryBarrier();
                const std::uint32_t after = shared->publishSequence;
                if (before == after && !(after & 1u)) return true;
            }
            return false;
        }

        bool HeaderValid(const IpcV3::HostState& s) noexcept
        {
            return s.magic == IpcV3::HostMagic &&
                s.version == IpcV3::ProtocolVersion &&
                s.structSize == sizeof(s);
        }

        bool HeaderValid(const IpcV3::ClientState& s) noexcept
        {
            return s.magic == IpcV3::ClientMagic &&
                s.version == IpcV3::ProtocolVersion &&
                s.structSize == sizeof(s);
        }

        bool HeaderValid(const IpcV3::AckState& s) noexcept
        {
            return s.magic == IpcV3::AckMagic &&
                s.version == IpcV3::ProtocolVersion &&
                s.structSize == sizeof(s);
        }

        bool HeaderValid(const IpcV3::FrameRing& s) noexcept
        {
            return s.magic == IpcV3::FrameMagic &&
                s.version == IpcV3::ProtocolVersion &&
                s.structSize == sizeof(s) &&
                s.slotCount == IpcV3::RingSize;
        }

        const IpcV3::FrameDescriptor* LatestFrame(
            const IpcV3::FrameRing& ring) noexcept
        {
            if (ring.latestSlot >= IpcV3::RingSize)
                return nullptr;
            return &ring.slots[ring.latestSlot];
        }

        std::string BuildCaptureSample(bool havePose,
            const SharedPoseState& pose, std::uint32_t heartbeat,
            bool haveFrame, const SharedRenderFrameState& frame,
            bool haveHost3, const IpcV3::HostState& host3,
            bool haveClient, const IpcV3::ClientState& client,
            const IpcV3::FrameDescriptor* frame3,
            bool haveAck, const IpcV3::AckState& ack)
        {
            std::ostringstream s;
            s << Timestamp()
              << ',' << (havePose ? pose.sequence : 0)
              << ',' << heartbeat
              << ',' << (haveFrame ? frame.frameId : 0)
              << ',' << (haveFrame ? frame.state : 0)
              << ',' << (haveFrame ? frame.failureReason : 0)
              << ',' << (haveHost3 ? host3.poseId : 0)
              << ',' << (haveHost3 ? host3.recommendedWidth[0] : 0)
              << ',' << (haveHost3 ? host3.recommendedHeight[0] : 0)
              << ',' << (haveHost3 ? host3.recommendedWidth[1] : 0)
              << ',' << (haveHost3 ? host3.recommendedHeight[1] : 0)
              << ',' << (haveClient ? client.presentationMode : 0)
              << ',' << (haveClient ? client.stereoState : 0)
              << ',' << (haveClient ? client.lastFailure : 0)
              << ',' << (frame3 ? frame3->frameId : 0)
              << ',' << (frame3 ? frame3->renderPoseId : 0)
              << ',' << (frame3 ? frame3->transportKind : 0)
              << ',' << (frame3 ? frame3->failureReason : 0)
              << ',' << (haveAck ? ack.consumedFrameId : 0)
              << ',' << (haveAck ? ack.consumedSlot : 0);
            return s.str();
        }

        void WriteEye(std::ostream& out, const char* prefix,
            const IpcV3::WireEyeView& eye)
        {
            out << prefix << ".orientation="
                << eye.orientation[0] << ',' << eye.orientation[1] << ','
                << eye.orientation[2] << ',' << eye.orientation[3] << '\n';
            out << prefix << ".positionMeters="
                << eye.positionMeters[0] << ',' << eye.positionMeters[1] << ','
                << eye.positionMeters[2] << '\n';
            out << prefix << ".fov="
                << eye.fov.angleLeft << ',' << eye.fov.angleRight << ','
                << eye.fov.angleUp << ',' << eye.fov.angleDown << '\n';
        }

        bool WriteCaptureBundle(const std::string& captureId,
            const std::vector<std::string>& samples,
            bool haveHost3, const IpcV3::HostState& host3,
            const IpcV3::FrameDescriptor* frame3,
            Log& log)
        {
            try
            {
                const std::filesystem::path root("captures");
                const std::filesystem::path dir = root / captureId;
                std::filesystem::create_directories(dir);

                {
                    std::ofstream telemetry(
                        dir / "telemetry.csv", std::ios::out | std::ios::trunc);
                    telemetry
                        << "utc,v2PoseSeq,heartbeat,v2FrameId,v2StereoState,"
                           "v2Failure,v3PoseId,recWidthL,recHeightL,recWidthR,"
                           "recHeightR,presentationMode,v3StereoState,"
                           "v3ClientFailure,v3FrameId,v3RenderPoseId,"
                           "transportKind,v3FrameFailure,ackFrameId,ackSlot\n";
                    for (const auto& sample : samples)
                        telemetry << sample << '\n';
                }

                {
                    std::ofstream meta(
                        dir / "metadata.txt", std::ios::out | std::ios::trunc);
                    meta << "captureId=" << captureId << '\n'
                         << "trigger=Ctrl+F9\n"
                         << "capturedUtc=" << Timestamp() << '\n'
                         << "backend=" << EnvValue("OUTRUN_VR_BACKEND") << '\n'
                         << "profile=" << EnvValue("OUTRUN_VR_TEST_PROFILE") << '\n'
                         << "session=" << EnvValue("OUTRUN_VR_SESSION_ID") << '\n'
                         << "variant=" << EnvValue("OUTRUN_VR_VARIANT_ID") << '\n'
                         << "matrix=" << EnvValue("OUTRUN_VR_MATRIX_ID") << '\n'
                         << "sourceSha=" << EnvValue("OUTRUN_VR_SOURCE_SHA") << '\n'
                         << "configSha256=" << EnvValue("OUTRUN_VR_CONFIG_SHA256") << '\n'
                         << "samplePeriodMs=100\n"
                         << "rollingPreWindowApproxMs=10000\n"
                         << "postWindowMs=" << CapturePostWindowMs << '\n'
                         << "sampleCount=" << samples.size() << '\n'
                         << "runtime=" << (haveHost3 ?
                            BoundedString(host3.runtimeName,
                                sizeof(host3.runtimeName)) : std::string{}) << '\n'
                         << "recommendedEye0=" << (haveHost3 ?
                            std::to_string(host3.recommendedWidth[0]) + "x" +
                            std::to_string(host3.recommendedHeight[0]) : "0x0") << '\n'
                         << "recommendedEye1=" << (haveHost3 ?
                            std::to_string(host3.recommendedWidth[1]) + "x" +
                            std::to_string(host3.recommendedHeight[1]) : "0x0") << '\n'
                         << "phase1Limitations=per-stage wait/acquire/render/copy/end "
                            "timings and eye image snapshots are not exported by "
                            "the watchdog yet\n";
                }

                {
                    std::ofstream eyes(
                        dir / "eye_state.txt", std::ios::out | std::ios::trunc);
                    if (haveHost3)
                    {
                        eyes << "host.poseId=" << host3.poseId << '\n';
                        eyes << "host.headPositionMeters="
                             << host3.headPositionMeters[0] << ','
                             << host3.headPositionMeters[1] << ','
                             << host3.headPositionMeters[2] << '\n';
                        WriteEye(eyes, "host.left", host3.eyes[0]);
                        WriteEye(eyes, "host.right", host3.eyes[1]);
                    }
                    if (frame3)
                    {
                        eyes << "frame.frameId=" << frame3->frameId << '\n';
                        eyes << "frame.renderPoseId=" << frame3->renderPoseId << '\n';
                        WriteEye(eyes, "rendered.left", frame3->renderedEyes[0]);
                        WriteEye(eyes, "rendered.right", frame3->renderedEyes[1]);
                    }
                }

                {
                    std::ofstream last(
                        "VR_CAPTURE_LAST.txt",
                        std::ios::out | std::ios::trunc);
                    if (last)
                    {
                        last << "status=READY\n"
                             << "captureId=" << captureId << '\n'
                             << "path=" << (std::filesystem::path("captures") /
                                  captureId).string() << '\n'
                             << "completedUtc=" << Timestamp() << '\n';
                    }
                }
                log.Write("INFO", "diagnostic_capture_written id=" + captureId +
                    " samples=" + std::to_string(samples.size()));
                // Ctrl+F9 previously had no visible/audible acknowledgement,
                // making a successful capture look like a missing feature.
                MessageBeep(MB_ICONASTERISK);
                return true;
            }
            catch (const std::exception& e)
            {
                log.Write("ERROR", std::string("diagnostic_capture_failed: ") + e.what());
                return false;
            }
        }

        class RuntimeWatchdog
        {
        public:
            RuntimeWatchdog() : thread_([this] { Run(); }) {}
            ~RuntimeWatchdog()
            {
                stop_.store(true, std::memory_order_release);
                if (thread_.joinable()) thread_.join();
            }

        private:
            void Run()
            {
                Log log;
                log.Write("INFO", "watchdog_start pid=" +
                    std::to_string(GetCurrentProcessId()) +
                    " profile=" + EnvValue("OUTRUN_VR_TEST_PROFILE") +
                    " session=" + EnvValue("OUTRUN_VR_SESSION_ID"));

                Ipc::ReadOnlyMapping<SharedPoseState> v2Pose;
                Ipc::ReadOnlyMapping<SharedRenderFrameRing> v2Frames;
                Ipc::ReadOnlyMapping<IpcV3::HostState> v3Host;
                Ipc::ReadOnlyMapping<IpcV3::ClientState> v3Client;
                Ipc::ReadOnlyMapping<IpcV3::FrameRing> v3Frames;
                Ipc::ReadOnlyMapping<IpcV3::AckState> v3Ack;

                ULONGLONG activeSince = 0;
                ULONGLONG lastSummary = 0;
                ULONGLONG lastPoseChange = 0;
                ULONGLONG lastFrameChange = 0;
                std::uint32_t lastPoseSequence = 0;
                std::uint32_t lastHeartbeat = 0;
                std::uint32_t lastFrameId = 0;
                bool noClientWarned = false;
                bool noStereoWarned = false;
                bool poseStallWarned = false;
                bool frameStallWarned = false;

                std::deque<std::string> rollingSamples;
                std::vector<std::string> captureSamples;
                bool captureKeyWasDown = false;
                bool capturePending = false;
                ULONGLONG captureUntil = 0;
                std::string captureId;
                IpcV3::HostState captureHost{};
                bool captureHaveHost = false;
                IpcV3::FrameDescriptor captureFrame{};
                bool captureHaveFrame = false;

                while (!stop_.load(std::memory_order_acquire))
                {
                    v2Pose.EnsureOpen(SharedMemoryName);
                    v2Frames.EnsureOpen(RenderFrameMemoryName);
                    v3Host.EnsureOpen(IpcV3::HostStateName);
                    v3Client.EnsureOpen(IpcV3::ClientStateName);
                    v3Frames.EnsureOpen(IpcV3::FrameRingName);
                    v3Ack.EnsureOpen(IpcV3::AckStateName);

                    SharedPoseState pose{};
                    const bool havePose = v2Pose.IsOpen() &&
                        IpcV3::ShadowV2::StableReadPose(v2Pose.Get(), pose) &&
                        pose.magic == SharedMagic &&
                        pose.protocolVersion == SharedProtocolVersion;

                    SharedRenderFrameState frame{};
                    bool haveFrame = false;
                    if (v2Frames.IsOpen())
                    {
                        SharedRenderFrameRing ring{};
                        if (IpcV3::ShadowV2::StableReadFrameRing(
                                v2Frames.Get(), ring))
                            haveFrame =
                                IpcV3::ShadowV2::LatestFrame(ring, frame);
                    }

                    IpcV3::HostState host3{};
                    const bool haveHost3 = v3Host.IsOpen() &&
                        StableReadState(v3Host, host3) && HeaderValid(host3);
                    IpcV3::ClientState client{};
                    const bool haveClient = v3Client.IsOpen() &&
                        StableReadState(v3Client, client) &&
                        HeaderValid(client);
                    IpcV3::FrameRing frameRing3{};
                    const bool haveFrame3 = v3Frames.IsOpen() &&
                        StableReadFrameRing(v3Frames.Get(), frameRing3) &&
                        HeaderValid(frameRing3);
                    const IpcV3::FrameDescriptor* frame3 =
                        haveFrame3 ? LatestFrame(frameRing3) : nullptr;
                    IpcV3::AckState ack{};
                    const bool haveAck = v3Ack.IsOpen() &&
                        StableReadState(v3Ack, ack) && HeaderValid(ack);

                    const ULONGLONG now = GetTickCount64();
                    if (havePose && pose.hostPid == GetCurrentProcessId() &&
                        !activeSince)
                    {
                        activeSince = now;
                        lastPoseChange = now;
                        lastFrameChange = now;
                        log.Write("INFO", "host_pose_active runtime=" +
                            BoundedString(
                                pose.runtimeName, sizeof(pose.runtimeName)));
                    }

                    if (havePose)
                    {
                        if (pose.sequence != lastPoseSequence)
                        {
                            lastPoseSequence = pose.sequence;
                            lastPoseChange = now;
                            poseStallWarned = false;
                        }
                        const std::uint32_t heartbeat =
                            pose.reserved[ClientHeartbeatIndex];
                        if (heartbeat != lastHeartbeat)
                            lastHeartbeat = heartbeat;
                    }
                    if (haveFrame && frame.frameId != lastFrameId)
                    {
                        lastFrameId = frame.frameId;
                        lastFrameChange = now;
                        frameStallWarned = false;
                    }

                    const std::string sample = BuildCaptureSample(
                        havePose, pose, lastHeartbeat, haveFrame, frame,
                        haveHost3, host3, haveClient, client, frame3,
                        haveAck, ack);
                    rollingSamples.push_back(sample);
                    while (rollingSamples.size() > RollingSampleCount)
                        rollingSamples.pop_front();

                    const bool captureKeyDown =
                        (GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0 &&
                        (GetAsyncKeyState(VK_F9) & 0x8000) != 0;
                    const bool triggeredThisLoop =
                        captureKeyDown && !captureKeyWasDown && !capturePending;
                    captureKeyWasDown = captureKeyDown;

                    if (triggeredThisLoop)
                    {
                        capturePending = true;
                        captureUntil = now + CapturePostWindowMs;
                        captureId = "CAP_" + CaptureStamp();
                        captureSamples.assign(
                            rollingSamples.begin(), rollingSamples.end());
                        captureHaveHost = haveHost3;
                        if (haveHost3) captureHost = host3;
                        captureHaveFrame = frame3 != nullptr;
                        if (frame3) captureFrame = *frame3;
                        log.Write("INFO",
                            "diagnostic_capture_triggered id=" + captureId +
                            " key=Ctrl+F9 preSamples=" +
                            std::to_string(captureSamples.size()));
                        {
                            std::ofstream last(
                                "VR_CAPTURE_LAST.txt",
                                std::ios::out | std::ios::trunc);
                            if (last)
                            {
                                last << "status=CAPTURING\n"
                                     << "captureId=" << captureId << '\n'
                                     << "trigger=Ctrl+F9\n"
                                     << "startedUtc=" << Timestamp() << '\n';
                            }
                        }
                        MessageBeep(MB_OK);
                    }
                    else if (capturePending)
                    {
                        captureSamples.push_back(sample);
                        if (haveHost3)
                        {
                            captureHaveHost = true;
                            captureHost = host3;
                        }
                        if (frame3)
                        {
                            captureHaveFrame = true;
                            captureFrame = *frame3;
                        }
                    }

                    if (capturePending && now >= captureUntil)
                    {
                        WriteCaptureBundle(captureId, captureSamples,
                            captureHaveHost, captureHost,
                            captureHaveFrame ? &captureFrame : nullptr, log);
                        capturePending = false;
                        captureUntil = 0;
                        captureSamples.clear();
                        captureId.clear();
                        captureHaveHost = false;
                        captureHaveFrame = false;
                    }

                    if (activeSince)
                    {
                        if (!noClientWarned && now - activeSince > 7000 &&
                            (!havePose || pose.clientPid == 0 ||
                             lastHeartbeat == 0))
                        {
                            noClientWarned = true;
                            log.Write("WARN",
                                "game_client_missing: dinput8 VR hook heartbeat "
                                "not observed after 7s");
                        }
                        if (!noStereoWarned && now - activeSince > 12000 &&
                            lastFrameId == 0)
                        {
                            noStereoWarned = true;
                            log.Write("WARN",
                                "stereo_frame_missing: no rendered stereo frame "
                                "observed after 12s; enter gameplay if still in menus");
                        }
                        if (!poseStallWarned && lastPoseSequence &&
                            now - lastPoseChange > 2000)
                        {
                            poseStallWarned = true;
                            log.Write("WARN",
                                "pose_stalled: OpenXR host pose sequence has not "
                                "advanced for 2s");
                        }
                        if (!frameStallWarned && lastFrameId &&
                            now - lastFrameChange > 3000 &&
                            haveClient &&
                            client.presentationMode == PresentationGameplay)
                        {
                            frameStallWarned = true;
                            log.Write("WARN",
                                "frame_stalled: game reports gameplay but stereo "
                                "frame id has not advanced for 3s");
                        }
                    }

                    if (now - lastSummary >= 5000)
                    {
                        lastSummary = now;
                        std::ostringstream s;
                        s << "summary hostPose=" << (havePose ? 1 : 0)
                          << " hostSeq=" << (havePose ? pose.sequence : 0)
                          << " hostFlags=0x" << std::hex
                          << (havePose ? pose.flags : 0) << std::dec
                          << " clientPid=" << (havePose ? pose.clientPid : 0)
                          << " heartbeat=" << lastHeartbeat
                          << " stereoFrame=" << (haveFrame ? frame.frameId : 0)
                          << " stereoState=" << (haveFrame ? frame.state : 0)
                          << " failure="
                          << (haveFrame ? frame.failureReason : 0)
                          << " poseSeq="
                          << (haveFrame ? frame.sourcePoseSequence : 0)
                          << " direct="
                          << ((haveFrame &&
                              (frame.flags & RenderFrameDirectGpuTransport))
                                  ? 1 : 0)
                          << " v3Host=" << (haveHost3 ? 1 : 0)
                          << " v3PoseId=" << (haveHost3 ? host3.poseId : 0)
                          << " v3Client=" << (haveClient ? 1 : 0)
                          << " v3ClientSeq="
                          << (haveClient ? client.sequence : 0)
                          << " v3Frame=" << (frame3 ? frame3->frameId : 0)
                          << " v3Ack=" << (haveAck ? 1 : 0)
                          << " ackFrame="
                          << (haveAck ? ack.consumedFrameId : 0)
                          << " ackSlot="
                          << (haveAck ? ack.consumedSlot : 0);
                        log.Write("INFO", s.str());
                    }

                    Sleep(100);
                }

                if (capturePending && !captureSamples.empty())
                {
                    WriteCaptureBundle(captureId, captureSamples,
                        captureHaveHost, captureHost,
                        captureHaveFrame ? &captureFrame : nullptr, log);
                }
                log.Write("INFO", "watchdog_stop");
            }

            std::atomic<bool> stop_{false};
            std::thread thread_;
        };

        RuntimeWatchdog g_runtimeWatchdog;
    }
}
