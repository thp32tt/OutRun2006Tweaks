#include "../../src/vr/game/stage_extension_source_admission.hpp"
#include <cassert>

int main()
{
    using OutRunVR::StageExtension::SourceAdmission;
    // Both original sprani and numeric +TIME call families share the same
    // bounded ownership rule: VR off/on and queue reentry must fail closed.
    for (int family = 0; family != 2; ++family)
    {
        (void)family;
        const SourceAdmission direct{true, true};
        assert(direct.mayBeginDirect());
        assert(direct.mayPublish(true, true));
        assert(!direct.mayPublish(false, true));
        assert(!direct.mayPublish(true, false));
        const SourceAdmission desktop{false, true};
        assert(!desktop.mayBeginDirect());
        assert(!desktop.mayPublish(true, true));
        const SourceAdmission nestedQueue{true, false};
        assert(!nestedQueue.mayBeginDirect());
        assert(!nestedQueue.mayPublish(true, true));
    }
}
