#include "../../src/vr/d3d11/native_game_shared_desktop_admission.hpp"
#include "../../src/vr/d3d11/native_game_shared_desktop_rollback.hpp"
#include "../../src/vr/d3d11/native_game_shared_desktop_backup.hpp"
#include "../../src/vr/d3d11/native_game_shared_desktop_source.hpp"
#include <cassert>
#include <array>
using outrun::vr::dx11::live_game_frame::NativeSharedDesktopAdmission;
int main() {
    auto allowed = [](bool opt, bool full, bool complete, bool writable,
                      bool owner, bool region, bool dirty, bool bgra,
                      bool single, unsigned w, unsigned h, unsigned gen) {
        return NativeSharedDesktopAdmission::allowed(
            opt,full,complete,writable,owner,region,dirty,bgra,single,w,h,gen);
    };
    assert(allowed(true,true,true,true,true,true,true,true,true,3440,1440,3));
    // D3DFMT_A8R8G8B8=21 and X8R8G8B8=22 are valid full-screen
    // desktop destinations. Unsupported format conversions stay on D3D9.
    constexpr unsigned a8 = 21u, x8 = 22u;
    assert(NativeSharedDesktopAdmission::destination_compatible(a8,a8,x8));
    assert(NativeSharedDesktopAdmission::destination_compatible(x8,a8,x8));
    assert(!NativeSharedDesktopAdmission::destination_compatible(23u,a8,x8));
    assert(allowed(true,true,true,true,true,true,true,
                   NativeSharedDesktopAdmission::destination_compatible(x8,a8,x8),
                   true,3440,1440,3));
    assert(!allowed(true,true,true,true,true,true,true,
                    NativeSharedDesktopAdmission::destination_compatible(23u,a8,x8),
                    true,3440,1440,3));
    // Real GPU game color MSAA is resolved before shared-desktop Present.
    // The GPU fence, exact-tile copy and original-D3D9 rollback still apply.
    using outrun::vr::dx11::live_game_frame::NativeSharedDesktopSourceTransfer;
    using outrun::vr::dx11::live_game_frame::native_shared_desktop_source_transfer;
    constexpr auto copy = NativeSharedDesktopSourceTransfer::Copy;
    constexpr auto resolve = NativeSharedDesktopSourceTransfer::Resolve;
    constexpr auto reject = NativeSharedDesktopSourceTransfer::Reject;
    static_assert(native_shared_desktop_source_transfer(1,1,1,0,false,false) == copy);
    static_assert(native_shared_desktop_source_transfer(1,1,4,0,true,true) == resolve);
    static_assert(native_shared_desktop_source_transfer(1,1,8,7,true,true) == resolve);
    static_assert(native_shared_desktop_source_transfer(1,1,4,0,false,true) == reject);
    static_assert(native_shared_desktop_source_transfer(1,1,4,0,true,false) == reject);
    static_assert(native_shared_desktop_source_transfer(1,2,4,0,true,true) == reject);
    static_assert(native_shared_desktop_source_transfer(2,1,4,0,true,true) == reject);
    static_assert(native_shared_desktop_source_transfer(1,1,0,0,true,true) == reject);
    static_assert(native_shared_desktop_source_transfer(1,1,33,0,true,true) == reject);
    static_assert(native_shared_desktop_source_transfer(1,1,1,1,true,true) == reject);
    // Strictly fail closed for default-off gameplay/fallback, unsupported
    // scene draws, unknown dirty regions and non-BGRA/MSAA.
    for (unsigned mask = 0; mask < 9; ++mask) {
        bool f[9]{true,true,true,true,true,true,true,true,true};
        f[mask] = false;
        assert(!allowed(f[0],f[1],f[2],f[3],f[4],f[5],f[6],f[7],f[8],
                        3440,1440,3));
    }
    assert(!allowed(true,true,true,true,true,true,true,true,true,0,1440,3));
    assert(!allowed(true,true,true,true,true,true,true,true,true,3440,0,3));
    assert(!allowed(true,true,true,true,true,true,true,true,true,3440,1440,0));
    // Exact game Present source crop: GPU StretchRect updates the cropped
    // area only, not the rest of the original D3D9 menu/race backbuffer.
    using outrun::vr::dx11::live_game_frame::GameNativePresentRegion;
    using outrun::vr::dx11::live_game_frame::GameNativePartialDirtySelection;
    constexpr GameNativePresentRegion full{0,0,3440,1440};
    constexpr GameNativePresentRegion crop{100,50,3300,1390};
    constexpr GameNativePresentRegion tile{200,100,400,300};
    constexpr GameNativePartialDirtySelection noTile{};
    constexpr GameNativePartialDirtySelection oneTile{tile,true};
    auto select = [](GameNativePresentRegion visible, bool hasDirty,
                     bool oneDirty, bool fullDirty, bool cropDirty,
                     bool partitionCrop, GameNativePartialDirtySelection partial) {
        return NativeSharedDesktopAdmission::select_region(
            3440,1440,visible,hasDirty,oneDirty,fullDirty,cropDirty,
            partitionCrop,partial);
    };
    const auto whole = select(full,false,false,false,false,false,noTile);
    assert(whole.valid && whole.source.right == 3440 && whole.source.bottom == 1440);
    const auto cropped = select(crop,false,false,false,false,false,noTile);
    assert(cropped.valid && cropped.source.left == 100 && cropped.source.top == 50);
    const auto completeCrop = select(crop,true,true,false,true,false,noTile);
    assert(completeCrop.valid && completeCrop.source.right == 3300);
    assert(select(crop,true,false,true,false,false,noTile).valid);
    assert(select(crop,true,false,false,false,true,noTile).valid);
    const auto dirty = select(crop,true,true,false,false,false,oneTile);
    assert(dirty.valid && dirty.source.left == 200 &&
           dirty.source.right == 400 && dirty.source.bottom == 300);
    // CopySubresourceRegion and the subsequent StretchRect share this exact
    // rect, so the GPU transfer can skip all untouched source/backbuffer pixels.
    assert((dirty.source.right - dirty.source.left) *
           (dirty.source.bottom - dirty.source.top) == 40000);
    assert((cropped.source.right - cropped.source.left) *
           (cropped.source.bottom - cropped.source.top) < 3440 * 1440);
    // Contradictory dirty metadata must never authorize a partial GPU copy.
    assert(!select(crop,false,true,false,false,false,oneTile).valid);
    assert(!select(crop,false,false,true,false,false,noTile).valid);
    assert(!select(crop,false,false,false,true,false,noTile).valid);
    assert(!select(crop,false,false,false,false,true,noTile).valid);
    assert(!select(crop,true,false,false,false,false,oneTile).valid);
    assert(!select(crop,true,true,false,false,false,noTile).valid);
    assert(!select(crop,true,false,false,false,false,noTile).valid);
    const GameNativePartialDirtySelection foreign{{10,10,400,300},true};
    assert(!select(crop,true,true,false,false,false,foreign).valid);
    // Multi-rectangle menu/race update must preserve disjoint game pixels
    // inside the bounding rectangle. Reject fake union bounds, tiles outside
    // the Present crop and incomplete/contradictory coverage.
    using outrun::vr::dx11::live_game_frame::GameNativeDirtyRectangle;
    using outrun::vr::dx11::live_game_frame::GameNativeMultiDirtyUpload;
    constexpr GameNativeDirtyRectangle tiles[2]{
        {200,100,400,300},{500,100,700,300}};
    constexpr auto provenMulti = GameNativeMultiDirtyUpload::select(
        3440,1440,crop,2,32,200,100,700,300,tiles,true);
    static_assert(provenMulti.valid && provenMulti.count == 2);
    auto selectMulti = [&](auto candidate, bool dirty = true,
                           bool complete = false) {
        return NativeSharedDesktopAdmission::select_multi_regions(
            3440,1440,crop,dirty,complete,false,false,candidate);
    };
    const auto multi = selectMulti(provenMulti);
    assert(multi.valid && multi.count == 2);
    assert(multi.regions[0].right == 400 && multi.regions[1].left == 500);
    assert(!selectMulti(provenMulti,false).valid);
    assert(!selectMulti(provenMulti,true,true).valid);
    auto outside = provenMulti;
    outside.regions[1].right = 3400;
    assert(!selectMulti(outside).valid);
    auto wrongBounds = provenMulti;
    wrongBounds.uploadBounds.right = 800;
    assert(!selectMulti(wrongBounds).valid);
    auto missing = provenMulti;
    missing.count = 1;
    assert(!selectMulti(missing).valid);
    constexpr GameNativeDirtyRectangle outOfCrop[2]{
        {200,100,400,300},{3300,100,3400,300}};
    const auto clipped = GameNativeMultiDirtyUpload::select(
        3440,1440,crop,2,32,200,100,3400,300,outOfCrop,true);
    assert(!selectMulti(clipped).valid);
    // The GPU desktop rollback retains original game pixels for each
    // independently proven tile, not a huge bounding rectangle containing
    // untouched menu/vehicle/race HUD pixels.
    using outrun::vr::dx11::live_game_frame::NativeSharedDesktopRollbackPlan;
    constexpr GameNativePresentRegion distantHud[2]{
        {100,100,200,200},{1800,1000,1900,1100}};
    constexpr auto backupPlan = NativeSharedDesktopRollbackPlan::select(
        3440,1440,distantHud,2u);
    static_assert(backupPlan.valid && backupPlan.count == 2u);
    static_assert(backupPlan.totalPixels == 20000u);
    static_assert(backupPlan.tiles[0].width == 100u &&
                  backupPlan.tiles[1].height == 100u);
    assert(backupPlan.totalPixels < 1800ull * 1000ull);
    // Allocation reuse reduces repeat D3D9Ex CreateRenderTarget work during
    // sustained GPU native full-frame menu/car/race Presents, but re-snapshots
    // each new original-game backbuffer before any native pixel mutation.
    using outrun::vr::dx11::live_game_frame::NativeSharedDesktopBackupKey;
    constexpr NativeSharedDesktopBackupKey initialBackup{100,100,21u,9u,0x1234u};
    static_assert(initialBackup.valid());
    static_assert(initialBackup.reusable_for(initialBackup));
    // Moving a HUD tile without changing its allocation shape is reusable.
    constexpr NativeSharedDesktopBackupKey movedTile{100,100,21u,9u,0x1234u};
    static_assert(initialBackup.reusable_for(movedTile));
    static_assert(!initialBackup.reusable_for({101,100,21u,9u,0x1234u}));
    static_assert(!initialBackup.reusable_for({100,101,21u,9u,0x1234u}));
    static_assert(!initialBackup.reusable_for({100,100,22u,9u,0x1234u}));
    static_assert(!initialBackup.reusable_for({100,100,21u,10u,0x1234u}));
    static_assert(!initialBackup.reusable_for({100,100,21u,9u,0x5678u}));
    static_assert(!initialBackup.reusable_for({0,100,21u,9u,0x1234u}));
    static_assert(!NativeSharedDesktopBackupKey{}.reusable_for(initialBackup));

    // Overlapping update tiles are also backed up before any publication.
    constexpr GameNativePresentRegion overlappingHud[2]{
        {20,30,120,130},{80,100,160,200}};
    static_assert(NativeSharedDesktopRollbackPlan::select(
        3440,1440,overlappingHud,2u).totalPixels == 18000u);
    constexpr GameNativePresentRegion illegalHud[2]{
        {20,30,120,130},{80,100,3441,200}};
    static_assert(!NativeSharedDesktopRollbackPlan::select(
        3440,1440,illegalHud,2u).valid);
    // One full/cropped frame MUST have a backup: a failed first StretchRect
    // may partially overwrite the original game Present just like tile two.
    constexpr auto oneCropBackup = NativeSharedDesktopRollbackPlan::select(
        3440,1440,&crop,1u);
    static_assert(oneCropBackup.valid && oneCropBackup.count == 1u);
    static_assert(oneCropBackup.totalPixels == 3200ull * 1340ull);
    static_assert(oneCropBackup.tiles[0].width == 3200u &&
                  oneCropBackup.tiles[0].height == 1340u);
    constexpr auto wholeBackup = NativeSharedDesktopRollbackPlan::select(
        3440,1440,&full,1u);
    static_assert(wholeBackup.valid && wholeBackup.totalPixels == 3440ull * 1440ull);
    static_assert(!NativeSharedDesktopRollbackPlan::select(
        3440,1440,distantHud,0u).valid);
    constexpr GameNativePresentRegion clippedSingle{-1,0,3440,1440};
    static_assert(!NativeSharedDesktopRollbackPlan::select(
        3440,1440,&clippedSingle,1u).valid);
    static_assert(!NativeSharedDesktopRollbackPlan::select(
        3440,1440,nullptr,2u).valid);
    // Model original D3D9 backbuffer, two native tiles and a driver's
    // partially failed StretchRect. The saved regions must restore exact
    // pixels, including when the FIRST and ONLY publication fails.
    const auto exerciseRollback = [](bool twoRegions, unsigned failIndex) {
        constexpr unsigned w = 8u, h = 4u;
        constexpr GameNativePresentRegion spans[2]{{1,1,4,3},{5,0,7,2}};
        const unsigned count = twoRegions ? 2u : 1u;
        const auto plan = NativeSharedDesktopRollbackPlan::select(
            w,h,spans,count);
        assert(plan.valid && plan.count == count);
        std::array<int,w*h> pixels{};
        for (unsigned i = 0; i < pixels.size(); ++i) pixels[i] = int(i + 17);
        const auto original = pixels;
        std::array<std::array<int,w*h>,2> snapshots{};
        // Snapshot every original tile before ANY native GPU desktop write.
        for (unsigned tile = 0; tile < count; ++tile) {
            for (int y = spans[tile].top; y < spans[tile].bottom; ++y)
                for (int x = spans[tile].left; x < spans[tile].right; ++x)
                    snapshots[tile][unsigned(y)*w + unsigned(x)] =
                        original[unsigned(y)*w + unsigned(x)];
        }
        for (unsigned tile = 0; tile <= failIndex; ++tile) {
            const auto& rect = spans[tile];
            for (int y = rect.top; y < rect.bottom; ++y)
                for (int x = rect.left; x < rect.right; ++x)
                    pixels[unsigned(y)*w + unsigned(x)] = -1;
        }
        for (unsigned tile = 0; tile <= failIndex; ++tile) {
            const auto& rect = spans[tile];
            for (int y = rect.top; y < rect.bottom; ++y)
                for (int x = rect.left; x < rect.right; ++x)
                    pixels[unsigned(y)*w + unsigned(x)] =
                        snapshots[tile][unsigned(y)*w + unsigned(x)];
        }
        assert(pixels == original); // untouched HUD and failed tile survive
    };
    exerciseRollback(false,0u);
    exerciseRollback(true,0u);
    exerciseRollback(true,1u);
    const auto malformed = NativeSharedDesktopAdmission::select_region(
        3440,1440,{0,-1,3440,1440},false,false,false,false,false,noTile);
    assert(!malformed.valid);
}
