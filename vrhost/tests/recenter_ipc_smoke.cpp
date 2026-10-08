#include "vr/ipc/recenter_request.hpp"

int main()
{
    using OutRunVR::RecenterIpc::Channel;

    Channel channel;
    LONG pending = 0;
    DWORD requesterPid = 0;

    const LONG first = channel.Publish();
    if (first == 0)
        return 1;
    if (!channel.ConsumeEventSignal())
        return 2;
    if (!channel.Pending(pending, requesterPid))
        return 3;
    if (pending != first || requesterPid != GetCurrentProcessId())
        return 4;

    channel.MarkReceived(first);
    pending = 0;
    requesterPid = 0;
    if (channel.Pending(pending, requesterPid))
        return 5;

    channel.MarkApplied(first);
    if (channel.AppliedId() != first)
        return 6;

    const LONG second = channel.Publish();
    if (second == 0 || second == first)
        return 7;
    if (!channel.ConsumeEventSignal())
        return 8;

    pending = 0;
    requesterPid = 0;
    if (!channel.Pending(pending, requesterPid))
        return 9;
    if (pending != second || requesterPid != GetCurrentProcessId())
        return 10;

    channel.MarkReceived(second);
    channel.MarkApplied(second);
    if (channel.AppliedId() != second)
        return 11;

    return 0;
}
