#include "vr/game/pmt_node_culling_contract.hpp"

int main()
{
    using namespace OutRunVR::PmtNodeCull;

    static_assert(RenderNodeVisibleRva == 0x4B00u);
    static_assert(WalkNodeVisibleCallRva == 0x5015u);
    static_assert(ResultTestRva == 0x501Du);
    static_assert(DisableBranchRva == 0x501Fu);
    static_assert(PmtNodeCenterOffset == 0x04u);
    static_assert(PmtNodeRadiusOffset == 0x10u);

    if (!ResultGateBytesCompatible(
            OriginalResultGate.data(), OriginalResultGate.size()))
        return 1;
    if (!ResultGateBytesCompatible(
            DisabledResultGate.data(), DisabledResultGate.size()))
        return 2;

    auto wrongOpcode = OriginalResultGate;
    wrongOpcode[0] = 0x84;
    if (ResultGateBytesCompatible(wrongOpcode.data(), wrongOpcode.size()))
        return 3;

    auto foreignBranch = OriginalResultGate;
    foreignBranch[3] ^= 0x01;
    if (ResultGateBytesCompatible(foreignBranch.data(), foreignBranch.size()))
        return 4;

    if (ResultGateBytesCompatible(nullptr, 0))
        return 5;
    if (ResultGateBytesCompatible(OriginalResultGate.data(), 3))
        return 6;

    return 0;
}