#include "runtime/menu_projection_slice_copy.hpp"

using OutRunVrMenuProjectionCopy::CanCopyIdenticalEye;
static_assert(CanCopyIdenticalEye(true, true, 2, true, true));
static_assert(!CanCopyIdenticalEye(false, true, 2, true, true));
static_assert(!CanCopyIdenticalEye(true, false, 2, true, true));
static_assert(!CanCopyIdenticalEye(true, true, 1, true, true));
static_assert(!CanCopyIdenticalEye(true, true, 3, true, true));
static_assert(!CanCopyIdenticalEye(true, true, 0, true, true));
static_assert(!CanCopyIdenticalEye(true, true, 2, false, true));
static_assert(!CanCopyIdenticalEye(true, true, 2, true, false));
int main() { return CanCopyIdenticalEye(true, true, 2, true, true) ? 0 : 1; }
