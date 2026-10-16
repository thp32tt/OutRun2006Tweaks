#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "game_addrs.hpp"
#include "vr/hud_semantics.hpp"
#include "vr/game/render_semantics.hpp"
#include "vr/game/texture_pack_cursor.hpp"
#include "vr/game/dds_alpha_mask_policy.hpp"
#include <fstream>
#include <xxhash.h>
#include <d3d9.h>
#include <ddraw.h>
#include <unordered_set>
#include <array>
#include <climits>
#include <cstdint>
#include <cstring>
#include <new>
#include <memory>
#include <intrin.h>

namespace OutRunVRHudInspector
{
    void TracePutSprite(SPRARGS* sprargs, float priority,
        const void* returnAddress);
    void TracePutSprite2(SPRARGS2* sprargs, float priority,
        const void* returnAddress);
    void TraceXstSet(int xstsetIndex, const char* filename);
}

namespace Settings
{
	extern Setting<bool> VREnabled;
	extern Setting<bool> VRHudInspector;
	Setting<std::string> TextureBaseFolder{ "Graphics", "TextureBaseFolder", "textures",
		"The base folder for texture replacements. Replacements are loaded from [TextureBaseFolder]/load/, and vanilla "
		"textures are extracted to [TextureBaseFolder]/dump/." };
	Setting<bool> SceneTextureReplacement{ "Graphics", "SceneTextureReplacement", true,
		"Allows stage textures to be replaced if a matching texture exists inside [TextureBaseFolder]/load/ folder. "
		"Textures must be named as [hash]_[width]x[height].dds, taken from the original texture to be replaced." };
	Setting<bool> SceneTextureExtract{ "Graphics", "SceneTextureExtract", false,
		"Extracts the vanilla stage textures from the game into [TextureBaseFolder]/dump/ when the game loads them in. "
		"Only useful if you want to work on your own improvements." };
	Setting<bool> UITextureReplacement{ "Graphics", "UITextureReplacement", true,
		"Allows UI textures to be replaced if a matching texture exists inside [TextureBaseFolder]/load/ folder. "
		"Textures must be named as [hash]_[width]x[height].dds, taken from the original texture to be replaced." };
	Setting<bool> UITextureExtract{ "Graphics", "UITextureExtract", false,
		"Extracts the vanilla UI textures from the game into [TextureBaseFolder]/dump/ when the game loads them in. "
		"Only useful if you want to work on your own improvements." };
	Setting<bool> EnableTextureCache{ "Graphics", "EnableTextureCache", true,
		"Caches stage texture replacements in a seperate thread when game loads in stage model, which may help reduce "
		"stutter when using large stage texture replacements." };
	Setting<bool> UseNewTextureAllocator{ "Graphics", "UseNewTextureAllocator", true,
		"Replaces games texture allocator with a faster simplified version, greatly reducing stutter & load times." };
}

#define MAX_TEXTURE_CACHE_SIZE_MB (1024 + 256)
#define VR_MAX_TEXTURE_CACHE_SIZE_MB 64

#define DDS_MAGIC 0x20534444  // "DDS "
struct DDS_FILE
{
	DWORD magic;
	DDSURFACEDESC2 data;
};

#define DDS_RGBA 0x41
#define DDS_RGB 0x40

inline D3DFORMAT GetD3DFormatFromPixelFormat(const DDPIXELFORMAT& format)
{
	const auto rgb32Intent = OutRunVR::DdsAlphaMask::Classify(
		format.dwFlags, format.dwRGBBitCount, format.dwRGBAlphaBitMask);
	using OutRunVR::DdsAlphaMask::Rgb32Intent;
	if (format.dwFourCC == FOURCC_DXT1) return D3DFMT_DXT1;
	if (format.dwFourCC == FOURCC_DXT3) return D3DFMT_DXT3;
	if (format.dwFourCC == FOURCC_DXT5) return D3DFMT_DXT5;

	if (format.dwRGBBitCount == 16 &&
		format.dwRBitMask == 0x00000f00 &&
		format.dwGBitMask == 0x000000f0 &&
		format.dwBBitMask == 0x0000000f &&
		format.dwRGBAlphaBitMask == 0x0000f000)
	{
		return D3DFMT_A4R4G4B4;
	}
	if (rgb32Intent == Rgb32Intent::Alpha &&
		format.dwRGBBitCount == 32 &&
		format.dwRBitMask == 0x00ff0000 &&
		format.dwGBitMask == 0x0000ff00 &&
		format.dwBBitMask == 0x000000ff &&
		format.dwRGBAlphaBitMask == 0xff000000)
	{
		return D3DFMT_A8R8G8B8;
	}
	if (rgb32Intent == Rgb32Intent::Alpha &&
		format.dwRGBBitCount == 32 &&
		format.dwRBitMask == 0x000000ff &&
		format.dwGBitMask == 0x0000ff00 &&
		format.dwBBitMask == 0x00ff0000 &&
		format.dwRGBAlphaBitMask == 0xff000000)
	{
		return D3DFMT_A8B8G8R8; // not supported by most cards, will need conversion >.>
	}

	// Some RGB-only DDS authors preserve a high-byte alpha *mask* without
	// declaring DDPF_ALPHAPIXELS. Its byte is undefined and must NOT hide
	// car-selection/menu sprites. Honor declared alpha intent for both native
	// BGRA and swizzled RGBA; keep genuine RGBA alpha unchanged.
	if (rgb32Intent == Rgb32Intent::Opaque &&
		format.dwRGBAlphaBitMask == 0xff000000u)
	{
		D3DFORMAT resolvedFormat = D3DFMT_UNKNOWN;
		if (format.dwRBitMask == 0x00ff0000 &&
			format.dwGBitMask == 0x0000ff00 &&
			format.dwBBitMask == 0x000000ff)
			resolvedFormat = D3DFMT_X8R8G8B8;
		else if (format.dwRBitMask == 0x000000ff &&
			format.dwGBitMask == 0x0000ff00 &&
			format.dwBBitMask == 0x00ff0000)
			resolvedFormat = D3DFMT_X8B8G8R8;
		if (resolvedFormat != D3DFMT_UNKNOWN)
			return resolvedFormat;
	}

	// Opaque 32-bit DDS menus and car-selection sprites carry RGB without
	// an alpha mask. They are valid X8 textures, not unknown fast-DDS data.
	// Keep the original BGRA/RGBA masks distinct: the latter must swizzle
	// to the broadly supported X8R8G8B8 destination at every mip level.
	if ((format.dwFlags & DDPF_RGB) != 0 &&
		format.dwRGBBitCount == 32 &&
		format.dwRGBAlphaBitMask == 0)
	{
		if (format.dwRBitMask == 0x00ff0000 &&
			format.dwGBitMask == 0x0000ff00 &&
			format.dwBBitMask == 0x000000ff)
			return D3DFMT_X8R8G8B8;
		if (format.dwRBitMask == 0x000000ff &&
			format.dwGBitMask == 0x0000ff00 &&
			format.dwBBitMask == 0x00ff0000)
			return D3DFMT_X8B8G8R8;
	}

	if (format.dwRGBBitCount == 16 &&
		format.dwRBitMask == 0x0000f800 &&
		format.dwGBitMask == 0x000007e0 &&
		format.dwBBitMask == 0x0000001f)
	{
		return D3DFMT_R5G6B5;
	}
	if (format.dwRGBBitCount == 24 &&
		format.dwRBitMask == 0x00ff0000 &&
		format.dwGBitMask == 0x0000ff00 &&
		format.dwBBitMask == 0x000000ff)
	{
		return D3DFMT_R8G8B8;
	}

	return D3DFMT_UNKNOWN;
}

size_t D3DXGetFormatSize(D3DFORMAT fmt, size_t width = 1, size_t height = 1)
{
	switch (fmt) {
	case D3DFMT_R8G8B8: return 3 * width * height;
	case D3DFMT_A8R8G8B8:
	case D3DFMT_A8B8G8R8:
	case D3DFMT_X8R8G8B8:
	case D3DFMT_X8B8G8R8: return 4 * width * height;
	case D3DFMT_R5G6B5:
	case D3DFMT_X1R5G5B5:
	case D3DFMT_A1R5G5B5:
	case D3DFMT_A4R4G4B4: return 2 * width * height;
	case D3DFMT_A8:
	case D3DFMT_P8:
	case D3DFMT_L8: return width * height;
	case D3DFMT_A8P8:
	case D3DFMT_A8L8:
	case D3DFMT_V8U8:
	case D3DFMT_L6V5U5: return 2 * width * height;
	case D3DFMT_X8L8V8U8:
	case D3DFMT_Q8W8V8U8:
	case D3DFMT_V16U16:
	case D3DFMT_D32:
	case D3DFMT_D24S8:
	case D3DFMT_D24X8:
	case D3DFMT_D24X4S4:
	case D3DFMT_D32F_LOCKABLE:
	case D3DFMT_R32F:
	case D3DFMT_G32R32F: return 4 * width * height;
	case D3DFMT_A32B32G32R32F: return 16 * width * height;
	case D3DFMT_A16B16G16R16F: return 8 * width * height;
	case D3DFMT_R16F:
	case D3DFMT_D16_LOCKABLE:
	case D3DFMT_D16: return 2 * width * height;
	case D3DFMT_D15S1: return 2 * width * height;
	case D3DFMT_DXT1: return ((width + 3) / 4) * ((height + 3) / 4) * 8;
	case D3DFMT_DXT3:
	case D3DFMT_DXT5: return ((width + 3) / 4) * ((height + 3) / 4) * 16;
	default:
		assert(false && "Unsupported format");
		return 0;
	}
}

#define D3DX_FILTER_NONE                 0x00000001
#define D3DX_FILTER_POINT                0x00000002
#define D3DX_FILTER_LINEAR               0x00000003
#define D3DX_FILTER_TRIANGLE             0x00000004
#define D3DX_FILTER_BOX                  0x00000005
#define D3DX_FILTER_MIRROR_U             0x00010000
#define D3DX_FILTER_MIRROR_V             0x00020000
#define D3DX_FILTER_MIRROR_W             0x00040000
#define D3DX_FILTER_MIRROR               0x00070000
#define D3DX_FILTER_DITHER               0x00080000
#define D3DX_FILTER_DITHER_DIFFUSION     0x00100000
#define D3DX_FILTER_SRGB_IN              0x00200000
#define D3DX_FILTER_SRGB_OUT             0x00400000
#define D3DX_FILTER_SRGB                 0x00600000

// Native x86 D3D9 textures use little-endian X8R8G8B8 storage. Source DDS
// R8G8B8 rows are packed B,G,R (three bytes), not four-byte X8 texels.
// Expanding the channel triplet explicitly preserves both color and opacity.
constexpr std::uint32_t OpaqueBgr24Pixel(
    std::uint8_t blue, std::uint8_t green, std::uint8_t red) noexcept
{
    return 0xFF000000u |
        (static_cast<std::uint32_t>(red) << 16) |
        (static_cast<std::uint32_t>(green) << 8) | blue;
}
static_assert(OpaqueBgr24Pixel(0x11, 0x22, 0x33) == 0xFF332211u,
    "24-bit UI/car-selector DDS must preserve BGR and supply opaque X8");
static_assert(OpaqueBgr24Pixel(0x00, 0x00, 0x00) == 0xFF000000u,
    "24-bit DDS black must not acquire transparent alpha");

// Simplified version of D3DXCreateTextureFromFileInMemoryEx which allows loading textures much faster
HRESULT D3DXCreateTextureFromFileInMemoryEx_Custom(
	IDirect3DDevice9* pDevice,
	const void* pData,
	size_t dataSize,
	UINT Width,
	UINT Height,
	UINT MipLevels,
	DWORD Usage,
	D3DFORMAT Format,
	D3DPOOL Pool,
	DWORD Filter,
	DWORD MipFilter,
	LPDIRECT3DTEXTURE9* ppTexture)
{
	// Always clear a valid output slot before any failing fast-DDS exit.
	// Native D3DX fallback can then safely repopulate it without inheriting
	// a stale texture pointer from an invalid/truncated source.
	if (!ppTexture)
		return E_POINTER;
	*ppTexture = nullptr;
	if (!pDevice || !pData)
		return E_POINTER;

	// Refuse truncated DDS before reading the header and touching the UI resource.
	if (dataSize < sizeof(DDS_FILE))
		return E_FAIL;
	const uint8_t* data = static_cast<const uint8_t*>(pData);
	const DDS_FILE* header = reinterpret_cast<const DDS_FILE*>(data);

	// Validate DDS header
	if (header->magic != DDS_MAGIC ||
		header->data.dwSize != sizeof(DDSURFACEDESC2) ||
		header->data.ddpfPixelFormat.dwSize != sizeof(DDPIXELFORMAT))
		return E_FAIL;

	// Raw DDS rows are packed at the file's intrinsic dimensions. The fast
	// uploader does not resample: an explicit smaller/larger D3DX size would
	// reinterpret source row pitch and can corrupt HUD/car-selection textures.
	// Fail to the caller's original D3DX trampoline instead of clamping.
	if ((Width != D3DX_DEFAULT && Width != header->data.dwWidth) ||
		(Height != D3DX_DEFAULT && Height != header->data.dwHeight))
		return E_FAIL;

	// Extract texture information
	Width = (Width != D3DX_DEFAULT) ? Width : header->data.dwWidth;
	if (Width > header->data.dwWidth)
		Width = header->data.dwWidth;

	Height = (Height != D3DX_DEFAULT) ? Height : header->data.dwHeight;
	if (Height > header->data.dwHeight)
		Height = header->data.dwHeight;

	MipLevels = (MipLevels != D3DX_DEFAULT) ? MipLevels : header->data.dwMipMapCount;
	if (MipLevels > header->data.dwMipMapCount)
		MipLevels = header->data.dwMipMapCount;

	// MipLevels = 0 means caller is asking us to gen mips, the only caller that sets MipLevels = 0 is UI related though, which doesn't really need any
	// (though mip gen is still needed when caller asks for more mips than the texture file contains...)
	if (MipLevels == 0)
		MipLevels = 1; 
	if (!Width || !Height || Width > 16384 || Height > 16384 || MipLevels > 32)
		return E_FAIL;

	D3DFORMAT format_orig = GetD3DFormatFromPixelFormat(header->data.ddpfPixelFormat);
	if (format_orig == D3DFMT_UNKNOWN)
		return E_FAIL;

	// DDSD_PITCH describes the *file's* row stride for uncompressed DDS,
	// not the destination D3D9 LockRect pitch. A padded source must not be
	// decoded with tightly packed offsets (car-selection/UI corruption).
	const bool compressedSource = format_orig == D3DFMT_DXT1 ||
		format_orig == D3DFMT_DXT3 || format_orig == D3DFMT_DXT5;
	const bool hasSourcePitch = !compressedSource &&
		(header->data.dwFlags & DDSD_PITCH) != 0;
	const size_t declaredSourcePitch = hasSourcePitch && header->data.lPitch > 0
		? static_cast<size_t>(header->data.lPitch) : 0;
	if (hasSourcePitch && !declaredSourcePitch)
		return E_FAIL;
	// DDS supplies only the top-level pitch. For padded multi-mip sources,
	// alignment of subsequent mip rows is unknowable; native D3DX owns those.
	const size_t topRowBytes = D3DXGetFormatSize(format_orig, Width, Height) / Height;
	if (hasSourcePitch && declaredSourcePitch != topRowBytes && MipLevels > 1)
		return E_FAIL;

	// Preflight real source row strides *before* any D3D texture allocation.
	size_t remainingSourceBytes = dataSize - sizeof(DDS_FILE);
	for (UINT level = 0; level < MipLevels; ++level)
	{
		const UINT mipWidth = max(1U, Width >> level);
		const UINT mipHeight = max(1U, Height >> level);
		const size_t bytes = D3DXGetFormatSize(format_orig, mipWidth, mipHeight);
		const UINT mipRows = compressedSource ? max(1U, (mipHeight + 3) / 4) : mipHeight;
		const size_t rowBytes = bytes / mipRows;
		const size_t sourceRowPitch = hasSourcePitch && level == 0
			? declaredSourcePitch : rowBytes;
		if (!bytes || sourceRowPitch < rowBytes ||
			sourceRowPitch > remainingSourceBytes / mipRows)
			return E_FAIL;
		remainingSourceBytes -= sourceRowPitch * mipRows;
	}
	D3DFORMAT format_present = format_orig;
	// The same channel-order correction is needed for opaque X8B8G8R8
	// sprites. Never promote opaque X8 to an alpha-bearing A8 destination.
	if (format_orig == D3DFMT_A8B8G8R8 ||
		format_orig == D3DFMT_X8B8G8R8)
		format_present = format_orig == D3DFMT_A8B8G8R8
			? D3DFMT_A8R8G8B8 : D3DFMT_X8R8G8B8;
	// R8G8B8 is not a universally supported D3D9 texture allocation format.
	// Expand each opaque 24-bit car-selector/menu DDS texel into X8R8G8B8,
	// rather than asking CreateTexture/LockRect for a 3-byte GPU surface.
	if (format_orig == D3DFMT_R8G8B8)
		format_present = D3DFMT_X8R8G8B8;

#ifdef _DEBUG
	spdlog::info("Texture {}x{} mips {} fmt {}", Width, Height, MipLevels, (int)format_orig);
#endif

	// Create the texture
	HRESULT hr = pDevice->CreateTexture(
		Width,
		Height,
		MipLevels,
		Usage,
		format_present,
		Pool,
		ppTexture,
		nullptr
	);

	if (FAILED(hr))
		return hr;

	// MANAGED UI textures cannot be dynamic; DISCARD is legal only for
	// a dynamic texture's first mip level, never for ordinary UI uploads.
	const bool dynamicTexture = (Usage & D3DUSAGE_DYNAMIC) != 0;
	const uint8_t* srcData = data + sizeof(DDS_FILE);
	for (UINT mipLevel = 0; mipLevel < MipLevels; ++mipLevel)
	{
		D3DLOCKED_RECT lockedRect{};
		const DWORD lockFlags = (dynamicTexture && mipLevel == 0)
			? D3DLOCK_DISCARD : 0;
		hr = (*ppTexture)->LockRect(mipLevel, &lockedRect, nullptr, lockFlags);
		if (FAILED(hr))
		{
			(*ppTexture)->Release();
			*ppTexture = nullptr;
			return hr;
		}

		const UINT mipWidth = max(1U, Width >> mipLevel);
		const UINT mipHeight = max(1U, Height >> mipLevel);
		const size_t mipSize = D3DXGetFormatSize(format_orig, mipWidth, mipHeight);
		const bool compressed = format_orig == D3DFMT_DXT1 ||
			format_orig == D3DFMT_DXT3 || format_orig == D3DFMT_DXT5;
		const UINT rows = compressed ? max(1U, (mipHeight + 3) / 4) : mipHeight;
		const size_t rowBytes = mipSize / rows;
		const size_t sourceRowPitch = hasSourcePitch && mipLevel == 0
			? declaredSourcePitch : rowBytes;
		// Converted BGR24 occupies four destination bytes per source pixel.
		// Validate against the *destination* requirement, never source pitch.
		const size_t destinationRowBytes = format_orig == D3DFMT_R8G8B8
			? static_cast<size_t>(mipWidth) * 4u : rowBytes;
		if (!lockedRect.pBits || lockedRect.Pitch <= 0 ||
			static_cast<size_t>(lockedRect.Pitch) < destinationRowBytes)
		{
			(*ppTexture)->UnlockRect(mipLevel);
			(*ppTexture)->Release();
			*ppTexture = nullptr;
			return E_FAIL;
		}

		// D3D9 row pitch is not necessarily the same as packed DDS source pitch.
		uint8_t* dest = static_cast<uint8_t*>(lockedRect.pBits);
		const size_t dstPitch = static_cast<size_t>(lockedRect.Pitch);
		for (UINT row = 0; row < rows; ++row)
		{
			const uint8_t* srcRow = srcData + static_cast<size_t>(row) * sourceRowPitch;
			uint8_t* dstRow = dest + static_cast<size_t>(row) * dstPitch;
			if (format_orig == D3DFMT_R8G8B8)
			{
				for (UINT x = 0; x < mipWidth; ++x)
				{
					const size_t sourcePixel = static_cast<size_t>(x) * 3u;
					const std::uint32_t opaque = OpaqueBgr24Pixel(
						srcRow[sourcePixel], srcRow[sourcePixel + 1],
						srcRow[sourcePixel + 2]);
					std::memcpy(dstRow + static_cast<size_t>(x) * 4u,
						&opaque, sizeof(opaque));
				}
			}
			else if (format_orig == D3DFMT_A8B8G8R8 ||
				format_orig == D3DFMT_X8B8G8R8)
			{
				for (UINT x = 0; x < mipWidth; ++x)
				{
					const size_t p = static_cast<size_t>(x) * 4;
					dstRow[p] = srcRow[p + 2];
					dstRow[p + 1] = srcRow[p + 1];
					dstRow[p + 2] = srcRow[p];
					dstRow[p + 3] = srcRow[p + 3];
				}
			}
			else
				memcpy(dstRow, srcRow, rowBytes);
		}
		hr = (*ppTexture)->UnlockRect(mipLevel);
		if (FAILED(hr))
		{
			(*ppTexture)->Release();
			*ppTexture = nullptr;
			return hr;
		}
		srcData += sourceRowPitch * rows;
	}

	// Texture creation is not a rendering operation. Never change global
	// sampler state here: it belongs to each actual game draw and can change
	// menus, HUD, scene shaders and stereo passes if mutated while loading.

	return S_OK;
}

class FileDataCache
{
private:
	struct CacheEntry
	{
		std::shared_ptr<std::vector<uint8_t>> data;
		std::list<std::filesystem::path>::iterator lru_iterator;
	};

	std::size_t max_cache_size;
	std::size_t current_cache_size;
	std::unordered_map<std::filesystem::path, CacheEntry> cache;
	std::list<std::filesystem::path> lru_list;

	void evictToFit(std::size_t incoming = 0)
	{
		if (incoming > max_cache_size)
			incoming = max_cache_size;
		while (!lru_list.empty() &&
			current_cache_size > max_cache_size - incoming)
		{
			std::filesystem::path lru_file = lru_list.back();
			auto found = cache.find(lru_file);
			if (found != cache.end())
			{
				current_cache_size -= found->second.data->size();
				cache.erase(found);
			}
			lru_list.pop_back();
		}
	}

	mutable std::mutex mtx1; // Sole owner of cache, LRU and budget state.
	std::mutex mtx2;         // Serializes on-demand file loads only.
	std::mutex cachePopulationMutex; // Serializes cache-miss insertions without stalling read hits.

public:
	FileDataCache(std::size_t maxCacheSize) : max_cache_size(maxCacheSize), current_cache_size(0) {}

	void setMaxCacheSize(std::size_t bytes)
	{
		std::lock_guard _(mtx1);
		max_cache_size = std::max<std::size_t>(bytes, 16 * 1024 * 1024);
		evictToFit();
	}

	void cacheFolder(std::filesystem::path folder)
	{
		if (std::filesystem::exists(folder))
			for (const auto& entry : std::filesystem::directory_iterator(folder))
				if (entry.is_regular_file())
					cacheFile(entry.path());
	}

	void cacheFile(std::filesystem::path filename)
	{
		auto extension = filename.extension().string();
		std::transform(extension.begin(), extension.end(), extension.begin(),
			[](unsigned char c) { return std::tolower(c); });
		if (extension != ".dds")
			return;

		// Cache misses may originate on the background preload thread while
		// the game consumes other cached HUD/world DDS entries. Serialize only
		// cache *population*; never retain mtx1 across disk I/O.
		std::lock_guard populationLock(cachePopulationMutex);
		{
			std::lock_guard cacheLock(mtx1);
			auto found = cache.find(filename);
			if (found != cache.end())
			{
				lru_list.erase(found->second.lru_iterator);
				lru_list.push_front(filename);
				found->second.lru_iterator = lru_list.begin();
				return;
			}
		}

		std::ifstream file(filename, std::ios::binary | std::ios::ate);
		if (!file)
		{
			spdlog::warn("Texture cache: unable to open {}", filename.string());
			return;
		}
		const std::streamsize streamSize = file.tellg();
		if (streamSize <= 0)
			return;
		const std::size_t size = static_cast<std::size_t>(streamSize);
		{
			std::lock_guard cacheLock(mtx1);
			if (size > max_cache_size)
			{
				spdlog::warn("Texture cache: skipping {} ({} MiB) because it exceeds the {} MiB cache budget",
					filename.string(), size / (1024 * 1024),
					max_cache_size / (1024 * 1024));
				return;
			}
			// Evict before the transient allocation to protect the 32-bit
			// address space, while read hits remain lock-free of disk stalls.
			evictToFit(size);
		}
		file.seekg(0, std::ios::beg);

		try
		{
			auto buffer = std::make_shared<std::vector<uint8_t>>(size);
			if (!file.read(reinterpret_cast<char*>(buffer->data()),
				static_cast<std::streamsize>(size)))
			{
				spdlog::warn("Texture cache: error reading {}", filename.string());
				return;
			}

			// A concurrent budget change may have occurred while the file was
			// read. Re-evaluate it just before publishing the entry.
			std::lock_guard cacheLock(mtx1);
			if (size > max_cache_size)
				return;
			evictToFit(size);
			lru_list.push_front(filename);
			try
			{
				cache[filename] = { std::move(buffer), lru_list.begin() };
				current_cache_size += size;
			}
			catch (...)
			{
				lru_list.pop_front();
				throw;
			}
		}
		catch (const std::bad_alloc&)
		{
			spdlog::warn(
				"Texture cache: allocation failed for {} ({} MiB); skipping entry to keep the 32-bit game alive",
				filename.string(), size / (1024 * 1024));
			return;
		}
	}

	// Every returned pointer has a shared D3DX-call-scoped owner. Merely
	// holding a lock until return is not enough: background preloading can
	// evict a cached vector while D3D9 is still consuming its bytes.
	const uint8_t* getFileData(
		std::filesystem::path filename, size_t* size,
		std::shared_ptr<std::vector<uint8_t>>* transientOwner = nullptr)
	{
		if (!transientOwner)
			return nullptr; // Never publish an unowned cache pointer.
		transientOwner->reset();
		// A cached DDS is already protected by mtx1 and returned with a
		// shared owner. Do not serialize every render-thread hit on mtx2;
		// reserve the second lock for real cache misses and transient loads.
		std::unique_lock<std::mutex> fileRequestLock(mtx2, std::defer_lock);

		// All cache/LRU accesses, including background cacheFile(), use mtx1.
		// Do not hold it while calling cacheFile(): that routine locks mtx1.
		const auto acquireCachedOwner = [&]() -> std::shared_ptr<std::vector<uint8_t>>
		{
			std::lock_guard cacheLock(mtx1);
			auto found = cache.find(filename);
			if (found == cache.end())
				return {};
			lru_list.erase(found->second.lru_iterator);
			lru_list.push_front(filename);
			found->second.lru_iterator = lru_list.begin();
			return found->second.data;
		};

		auto owner = acquireCachedOwner();
		if (!owner)
		{
			// Only a miss enters the serialized disk-load path. A concurrent
			// caller may have populated the LRU while we acquired mtx2.
			fileRequestLock.lock();
			owner = acquireCachedOwner();
			if (!owner)
			{
				cacheFile(filename);
				owner = acquireCachedOwner();
			}
		}
		if (owner)
		{
			if (size)
				*size = owner->size();
			*transientOwner = std::move(owner);
			return (*transientOwner)->data();
		}

		// A legitimate large DDS exceeds the bounded cache budget: read it
		// transiently and keep that same buffer alive through fast/native D3DX.
		std::ifstream file(filename, std::ios::binary | std::ios::ate);
		if (!file)
			return nullptr;
		const std::streamsize streamSize = file.tellg();
		if (streamSize <= 0)
			return nullptr;
		try
		{
			auto transient = std::make_shared<std::vector<uint8_t>>(
				static_cast<std::size_t>(streamSize));
			file.seekg(0, std::ios::beg);
			if (!file.read(reinterpret_cast<char*>(transient->data()), streamSize))
				return nullptr;
			if (size)
				*size = transient->size();
			*transientOwner = std::move(transient);
			spdlog::info(
				"VR texture replacement: transient-load {} ({} MiB) outside bounded LRU; D3DX call retains source owner",
				filename.string(), static_cast<std::size_t>(streamSize) / (1024 * 1024));
			return (*transientOwner)->data();
		}
		catch (const std::bad_alloc&)
		{
			spdlog::warn("VR texture replacement: transient allocation failed for {}; preserving original", filename.string());
			return nullptr;
		}
	}

	std::size_t getCacheSize() const
	{
		std::lock_guard cacheLock(mtx1);
		return current_cache_size;
	}

};

// QnD file entry cache class, so we don't have to run std::filesystem::exists for every texture
// Probably not that much benefit since OS should have the directory cached anyway, but reducing OS calls should always help
class DirectoryFileCache
{
public:
	DirectoryFileCache() {}
	explicit DirectoryFileCache(const std::filesystem::path& directory)
		: directoryPath(directory)
	{
		scanDirectory();
	}

	bool exists(const std::filesystem::path& filename) const
	{
		return fileSet.find(filename) != fileSet.end();
	}

	void refresh()
	{
		fileSet.clear();
		scanDirectory();
	}

private:
	std::filesystem::path directoryPath;
	std::unordered_set<std::filesystem::path> fileSet;

	void scanDirectory()
	{
		if (!std::filesystem::exists(directoryPath))
			return;

		for (const auto& entry : std::filesystem::recursive_directory_iterator(directoryPath))
			if (entry.is_regular_file() || entry.is_directory())
				fileSet.insert(entry.path());
	}
};

// Keep compile-time negative cases at namespace scope. A constexpr member
// called from static_assert inside its still-incomplete class is not a valid
// constant expression on MSVC/GCC; the owner detours share this pure policy.
namespace
{
	static constexpr bool ShouldApplyUIScale(bool enabled, bool matches) noexcept
	{
		return enabled && matches;
	}
	static_assert(ShouldApplyUIScale(true, true) &&
		!ShouldApplyUIScale(false, true) &&
		!ShouldApplyUIScale(true, false) &&
		!ShouldApplyUIScale(false, false),
		"UI replacement scale must follow both the live toggle and source identity");
}

class TextureReplacement : public Hook
{
	inline static std::filesystem::path XmtDumpPath;
	inline static std::filesystem::path XmtLoadPath;
	inline static DirectoryFileCache FileSystem;
	inline static FileDataCache FileData = FileDataCache(MAX_TEXTURE_CACHE_SIZE_MB * 1024 * 1024);

	// Remappings for FXT modded sprites, so we can point them toward the vanilla versions
	inline static std::unordered_map<uint32_t, std::tuple<uint32_t, int, int>> FxtHashRemappings =
	{
		// spr_sprani_etc_cvt_Exst
		{0x8F1D69D3, {0x1F77CB88,128,128}}, // FXT arcade controls

		// spr_sprani_CLAR_RANK_Exst
		{0x8F663222, {0x4AFC1BED,512,512}}, // uncensored Clarissa
		{0x469F516D, {0xF043316B,1024,512}}, // uncensored Clarissa
		{0x86325B15, {0x8B52FEEC,1024,512}}, // uncensored Clarissa

		// spr_sprani_game_cvt_Exst
		{0x1025284E, {0xC4A2937B,1024,1024}}, // uncensored Clarissa
		{0xFDC4E73B, {0x39229D64,1024,1024}}, // uncensored Clarissa

		// spr_sprani_sumo_fe_cvt_Exst
		{0x50D487A9, {0xACF61D7C,1024,512}}, // arcade controls
		{0x2F7DFED1, {0x31C58963,512,256}}, // removed "press enter" text
		{0x678170B1, {0x4DC09A74,1024,1024}}, // uncensored Clarissa

		// spr_sprani_selector_cvt_Exst
		{0x698EEA48, {0x2DA43E41,1024,1024}}, // uncensored Clarissa

		// TODO: there is an FXT spr_sprani_congrats_cvt_exst but not sure how to get game to load that yet..
	};

	//
	// UI texture replacement code
	//
	// UI and scene have independent filename-index namespaces. A scene load
	// must never advance the car-selection/other UI indexed DDS lookup.
	inline static OutRunVR::TexturePacks::Cursor UiTextureCursor;
	inline static OutRunVR::TexturePacks::Cursor SceneTextureCursor;
	inline static std::filesystem::path CurrentXstsetFilename;
	inline static int CurrentXstsetIndex = 0;

	inline static std::unordered_map<int, std::pair<float, float>> sprite_scales;



	// put_sprite_ex2 usually doesn't have the proper textureId set inside SPRARGS2, only the d3dtexture_ptr_C
	// we could store each d3dtexture ptr somewhere when they're created, and then check against them later to find the scale
	// but that's not really ideal since pointers could get freed, with new texture using same address
	// luckily it seems almost every put_sprite_ex2 call is preceeded by a get_texture call with the actual texture ID
	// 
	// so we can just hook get_texture and check the textureId arg against our textureId -> scale map
	// if it exists we'll stash the d3d pointer -> textureId mapping temporarily for put_sprite_ex2 to use
	inline static void* prevTexture = nullptr;
	inline static int prevTextureId = 0;

	// Mask textures don't get put_sprite_ex2 called for them, instead the next sprite drawn will have ptr_B4 setup to point to it
	// That next sprite will likely call get_texture_dest with a different sprite ID, so we also have to keep track of the ID used prior
	inline static void* prevMaskTexture = nullptr;
	inline static int prevMaskTextureId = 0;

	inline static SafetyHookInline get_texture = {};
	static void* __cdecl get_texture_dest(int textureId)
	{
		auto* ret = get_texture.call<void*>(textureId);

		prevMaskTexture = prevTexture;
		prevMaskTextureId = prevTextureId;

		if (ShouldApplyUIScale(Settings::UITextureReplacement, ret != nullptr) &&
			sprite_scales.contains(textureId))
		{
			prevTexture = ret;
			prevTextureId = textureId;
		}
		else
		{
			prevTexture = nullptr;
			prevTextureId = 0;
		}
		return ret;
	}

	static void RescaleSprArgs2(SPRARGS2* a1, float scaleX, float scaleY)
	{
		// left is kept at both unk_88 & unk_A0, we'll do both seperately in case they're different for some reason
		float origLeft = 1.0f - a1->left_88;
		origLeft = origLeft * scaleX;
		a1->left_88 = 1.0f - origLeft;

		origLeft = 1.0f - a1->left_A0;
		origLeft = origLeft * scaleX;
		a1->left_A0 = 1.0f - origLeft;

		// right at unk_90 & unk_98
		float origRight = 1.0f - a1->right_90;
		origRight = origRight * scaleX;
		a1->right_90 = 1.0f - origRight;

		origRight = 1.0f - a1->right_98;
		origRight = origRight * scaleX;
		a1->right_98 = 1.0f - origRight;

		// bottom?
		a1->bottom_84 = a1->bottom_84 * scaleY;
		a1->bottom_8C = a1->bottom_8C * scaleY;

		// top?
		a1->top_94 = a1->top_94 * scaleY;
		a1->top_9C = a1->top_9C * scaleY;
	}

	using VrSpriteTailSnapshot =
		std::array<SpriteNode*, Game::SpritePriorityCount>;

	static VrSpriteTailSnapshot SnapshotVrSpriteTails()
	{
		VrSpriteTailSnapshot before{};
		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			before[prio] = root ? root->tail_4 : nullptr;
		}
		return before;
	}

	static OutRunVRHudSemantics::SemanticInfo
		ClassifyDirectVrSpriteCaller(const void* returnAddress) noexcept
	{
		const auto base =
			reinterpret_cast<std::uintptr_t>(Module::ExeHandle);
		const auto ret =
			reinterpret_cast<std::uintptr_t>(returnAddress);
		if (!base || ret < base + 5)
			return OutRunVRHudSemantics::UnknownInfo();

		const auto offset = ret - base;
		if (offset > 0xFFFFFFFFull)
			return OutRunVRHudSemantics::UnknownInfo();

		const auto callRva =
			static_cast<std::uint32_t>(offset) - 5u;
		return OutRunVRHudSemantics::ClassifyCaller(callRva);
	}

	static void TagDirectVrSpriteNodes(
		const VrSpriteTailSnapshot& before,
		const void* returnAddress) noexcept
	{
		if (!Settings::VREnabled)
			return;

		const auto semantic =
			ClassifyDirectVrSpriteCaller(returnAddress);
		OutRunVR::GameSemantic::RenderScope scope =
			OutRunVR::GameSemantic::RenderScope::None;
		switch (semantic.space)
		{
		case OutRunVRHudSemantics::SpacePolicy::ScreenHud:
			scope = OutRunVR::GameSemantic::RenderScope::ScreenHud;
			break;
		case OutRunVRHudSemantics::SpacePolicy::WorldBillboard:
			scope = OutRunVR::GameSemantic::RenderScope::WorldBillboard;
			break;
		default:
			return;
		}

		for (int prio = 0; prio < Game::SpritePriorityCount; ++prio)
		{
			SpriteNode* root = Game::sprite_prio_root[prio];
			SpriteNode* tailAfter = root ? root->tail_4 : nullptr;
			if (!root || !tailAfter || tailAfter == before[prio])
				continue;

			SpriteNode* node = before[prio]
				? before[prio]->next_0 : root->next_0;
			for (unsigned guard = 0;
				node && guard < Game::SpriteNodeMax; ++guard)
			{
				OutRunVR::GameSemantic::RegisterSpriteNodeScope(
					node, scope);
				if (node == tailAfter)
					break;
				node = node->next_0;
			}
		}
	}

	inline static SafetyHookInline put_sprite_ex2 = {};
	static int __cdecl put_sprite_ex2_dest(SPRARGS2* a1, float a2)
	{
		const void* returnAddress = _ReturnAddress();
		const auto vrTailsBefore = SnapshotVrSpriteTails();
		OutRunVRHudInspector::TracePutSprite2(a1, a2, returnAddress);
		int xstnum = a1->xstnum_0;

		// The active option may change while these get_texture hooks stay
		// installed. Discard pending pointer/ID bindings on disable, including
		// the independent mask owner, before handling any new sprite.
		if (!Settings::UITextureReplacement)
		{
			prevTexture = nullptr;
			prevTextureId = 0;
			prevMaskTexture = nullptr;
			prevMaskTextureId = 0;
		}

		if (ShouldApplyUIScale(Settings::UITextureReplacement,
			a1->d3dtexture_ptr_C == prevTexture))
		{
			const auto scale = sprite_scales.find(prevTextureId);
			if (scale != sprite_scales.end())
			{
				RescaleSprArgs2(a1, scale->second.first, scale->second.second);
				prevTexture = nullptr;
				prevTextureId = 0;
			}
		}

		if (a1->child_B4)
		{
			int spr_mask_flag = *Module::exe_ptr<int>(0x586B28);
			if (spr_mask_flag)
			{
				if (ShouldApplyUIScale(Settings::UITextureReplacement,
					a1->child_B4->d3dtexture_ptr_C == prevMaskTexture))
				{
					const auto scale = sprite_scales.find(prevMaskTextureId);
					if (scale != sprite_scales.end())
					{
						RescaleSprArgs2(a1->child_B4, scale->second.first, scale->second.second);
						prevMaskTexture = nullptr;
						prevMaskTextureId = 0;
					}
				}
			}
		}

		const int result = put_sprite_ex2.call<int>(a1, a2);
		TagDirectVrSpriteNodes(vrTailsBefore, returnAddress);
		return result;
	}

	inline static SafetyHookInline put_sprite_ex = {};
	static int __cdecl put_sprite_ex_dest(SPRARGS* a1, float a2)
	{
		const void* returnAddress = _ReturnAddress();
		const auto vrTailsBefore = SnapshotVrSpriteTails();
		OutRunVRHudInspector::TracePutSprite(a1, a2, returnAddress);
		int xstnum = a1->xstnum_0;
		if (ShouldApplyUIScale(Settings::UITextureReplacement, true))
		{
			const auto scale = sprite_scales.find(xstnum);
			if (scale != sprite_scales.end())
			{
				const auto scaleX = scale->second.first;
				const auto scaleY = scale->second.second;
				a1->top_4 = a1->top_4 * scaleY;
				a1->left_8 = a1->left_8 * scaleX;
				a1->bottom_C = a1->bottom_C * scaleY;
				a1->right_10 = a1->right_10 * scaleX;
				a1->scaleX = a1->scaleX / scaleX;
				a1->scaleY = a1->scaleY / scaleY;
			}
		}
		const int result = put_sprite_ex.call<int>(a1, a2);
		TagDirectVrSpriteNodes(vrTailsBefore, returnAddress);
		return result;
	}

	inline static SafetyHookMid LoadXstsetSprite_hook = {};
	static void LoadXstsetSprite_dest(safetyhook::Context& ctx)
	{
		const char* xstsetFilename = (char*)ctx.ecx;
		// A repeated xstset filename can occupy another slot; both the
		// filename *contents* and original game slot identify its textures.
		if (UiTextureCursor.Select(xstsetFilename, static_cast<int>(ctx.eax)))
		{
			CurrentXstsetFilename = UiTextureCursor.Name();
			CurrentXstsetIndex = static_cast<int>(ctx.eax);
			OutRunVRHudInspector::TraceXstSet(
				CurrentXstsetIndex, CurrentXstsetFilename.string().c_str());
		}
	};

	inline static const char* padType = nullptr;

	static void HandleTexture(
		void** ppSrcData, UINT* pSrcDataSize,
		std::filesystem::path texturePackName, bool isUITexture,
		std::shared_ptr<std::vector<uint8_t>>& transientOwner)
	{
		if (!*ppSrcData || *pSrcDataSize < sizeof(DDS_FILE)) [[unlikely]]
			return;

		bool allowReplacement = isUITexture ? Settings::UITextureReplacement : Settings::SceneTextureReplacement;
		bool allowExtract = isUITexture ? Settings::UITextureExtract : Settings::SceneTextureExtract;

		const DDS_FILE* header = (const DDS_FILE*)*ppSrcData;
		if (header->magic != DDS_MAGIC ||
			!header->data.dwWidth || !header->data.dwHeight) [[unlikely]]
			return;

		int width = header->data.dwWidth;
		int height = header->data.dwHeight;
		auto hash = XXH32(*ppSrcData, *pSrcDataSize, 0);

		// Remap some modified FXT textures to their original hashes
		if (FxtHashRemappings.count(hash)) [[unlikely]]
		{
			auto& mapping = FxtHashRemappings[hash];
			if (std::get<1>(mapping) == width && std::get<2>(mapping) == height) // make sure width/height match expected in case of collision...
				hash = std::get<0>(mapping);
		}

		bool usePadDirectory = false;
		if (isUITexture && (hash == 0x455717B2 || hash == 0x1F77CB88 || hash == 0xFA7BBB13 || hash == 0x39229D64 || hash == 0xACF61D7C || hash == 0x31C58963)) [[unlikely]]
		{
			// TODO: switching textures during gameplay (eg. from Xbox -> PC due to controller disconnect) will cause corruption ;_;
			// instead we'll have to track the first pad-type we switched to, and always use that for the session
			if (padType == nullptr && (Game::CurrentPadType != Game::GamepadType::None || Game::ForcedPadType != Game::GamepadType::None))
			{
				auto type = (Game::ForcedPadType != Game::GamepadType::None) ? Game::ForcedPadType : Game::CurrentPadType;
				if (type != Game::GamepadType::PC)
					padType = Game::PadTypes[int(type)];
			}

			usePadDirectory = padType != nullptr;
		}

		std::string ddsName = std::format("{:X}_{}x{}.dds", hash, width, height);
		const std::uint64_t ordinal = isUITexture
			? UiTextureCursor.NextIndexForGameTexture(
                *Module::exe_ptr<int>(0x55B25C))
            : SceneTextureCursor.NextIndex();
		std::string ddsNameIndexed = std::format("{}_{}", ordinal, ddsName);

		if (allowReplacement)
		{
			std::filesystem::path path_load;
			if (usePadDirectory) [[unlikely]]
			{
				if (!FileSystem.exists(path_load))
					path_load = XmtLoadPath / texturePackName.filename().stem() / padType / ddsNameIndexed;
				if (!FileSystem.exists(path_load))
					path_load = XmtLoadPath / texturePackName.filename().stem() / padType / ddsName;
				if (!FileSystem.exists(path_load))
					path_load = XmtLoadPath / padType / texturePackName.filename().stem() / ddsNameIndexed;
				if (!FileSystem.exists(path_load))
					path_load = XmtLoadPath / padType / texturePackName.filename().stem() / ddsName;
				if (!FileSystem.exists(path_load))
					path_load = XmtLoadPath / padType / ddsNameIndexed;
				if (!FileSystem.exists(path_load))
					path_load = XmtLoadPath / padType / ddsName;
			}

			if (!FileSystem.exists(path_load))
				path_load = XmtLoadPath / texturePackName.filename().stem() / ddsNameIndexed;
			if (!FileSystem.exists(path_load))
				path_load = XmtLoadPath / texturePackName.filename().stem() / ddsName;
			if (!FileSystem.exists(path_load))
				path_load = XmtLoadPath / ddsNameIndexed;
			if (!FileSystem.exists(path_load))
				path_load = XmtLoadPath / ddsName;

			if (FileSystem.exists(path_load))
			{
				size_t size = 0;
				const uint8_t* file = FileData.getFileData(
					path_load, &size, &transientOwner);
				// D3DX and the original game accept a UINT byte count. Never
				// truncate a size_t cache/transient replacement length to 32 bits.
				if (file && size >= sizeof(DDS_FILE) &&
					size <= static_cast<size_t>(UINT_MAX))
				{
					const DDS_FILE* newhead = (const DDS_FILE*)file;
					// A malformed replacement must not overwrite the game's original
					// DDS header or publish invalid HUD sprite scaling ratios.
					const bool validHeader = newhead->magic == DDS_MAGIC &&
						newhead->data.dwSize == sizeof(DDSURFACEDESC2) &&
						newhead->data.ddpfPixelFormat.dwSize == sizeof(DDPIXELFORMAT);
					const D3DFORMAT newFormat = validHeader
						? GetD3DFormatFromPixelFormat(newhead->data.ddpfPixelFormat) : D3DFMT_UNKNOWN;
					const bool validDimensions = newhead->data.dwWidth && newhead->data.dwHeight &&
						newhead->data.dwWidth <= 16384 && newhead->data.dwHeight <= 16384;
					const size_t firstMipSize = validDimensions && newFormat != D3DFMT_UNKNOWN
						? D3DXGetFormatSize(newFormat, newhead->data.dwWidth, newhead->data.dwHeight) : 0;
					// D3DX (scene/cube and UI fallback) may consume the full mip
					// chain, not just level zero. Never mutate original game data or
					// publish HUD scaling for a DDS whose later levels are truncated.
					const UINT mipCount = (newhead->data.dwFlags & DDSD_MIPMAPCOUNT)
						? newhead->data.dwMipMapCount : 1U;
					bool completeMipPayload = validHeader && validDimensions &&
						newFormat != D3DFMT_UNKNOWN && firstMipSize &&
						mipCount >= 1 && mipCount <= 32;
					if (completeMipPayload)
					{
						size_t remainingMipBytes = size - sizeof(DDS_FILE);
						for (UINT level = 0; level < mipCount; ++level)
						{
							const size_t levelBytes = D3DXGetFormatSize(newFormat,
								max(1U, newhead->data.dwWidth >> level),
								max(1U, newhead->data.dwHeight >> level));
							if (!levelBytes || levelBytes > remainingMipBytes)
							{
								completeMipPayload = false;
								break;
							}
							remainingMipBytes -= levelBytes;
						}
					}
					if (validHeader && completeMipPayload && firstMipSize &&
						firstMipSize <= size - sizeof(DDS_FILE))
					{
						if (isUITexture)
						{
							// Calc the scaling ratio of new texture vs old one, to use in put_sprite funcs later
							float ratio_width = float(newhead->data.dwWidth) / float(header->data.dwWidth);
							float ratio_height = float(newhead->data.dwHeight) / float(header->data.dwHeight);

							int curTextureNum = *Module::exe_ptr<int>(0x55B25C);
							sprite_scales[(CurrentXstsetIndex << 16) | curTextureNum] = { ratio_width, ratio_height };
						}

						// Replace header in the old data in case some game code tries reading it...
						memcpy(*ppSrcData, file, sizeof(DDS_FILE));

						// Update pointers to our new texture
						*ppSrcData = (void*)file;
						*pSrcDataSize = size;

						// Don't dump texture if we've loaded in new one
						allowExtract = false;
					}
				}
			}
		}

		if (allowExtract) [[unlikely]]
		{
			auto path_dump = XmtDumpPath / texturePackName.filename().stem();
			if (!FileSystem.exists(path_dump))
				std::filesystem::create_directories(path_dump);

			path_dump = path_dump / ddsNameIndexed;
			if (!FileSystem.exists(path_dump))
			{
				std::ofstream file(path_dump, std::ios::binary);
				if (file)
				{
					file.write((const char*)*ppSrcData, *pSrcDataSize);
					FileSystem.refresh();
				}
			}
		}
	}

	// The selected UI replacement is only committed when texture creation succeeds.
	// HandleTexture updates the original DDS header and sprite scale eagerly; on
	// decoder failure restore both before trying the untouched original DDS.
	struct UiDdsOriginalState
	{
		void* data;
		UINT bytes;
		DDS_FILE header{};
		int scaleKey = 0;
		bool snapshotted = false;
		bool hadScale = false;
		std::pair<float, float> previousScale{};

		UiDdsOriginalState(void* originalData, UINT originalBytes)
			: data(originalData), bytes(originalBytes)
		{
			// Even with replacement OFF, a successful original texture reload
			// must retire any ratio cached for this reused xstset texture slot.
			if (!data || bytes < sizeof(DDS_FILE))
				return;
			memcpy(&header, data, sizeof(DDS_FILE));
			const int textureNum = *Module::exe_ptr<int>(0x55B25C);
			scaleKey = (CurrentXstsetIndex << 16) | textureNum;
			const auto found = sprite_scales.find(scaleKey);
			if (found != sprite_scales.end())
			{
				hadScale = true;
				previousScale = found->second;
			}
			snapshotted = true;
		}

		bool replacementSelected(const void* selectedData) const
		{
			return snapshotted && selectedData && selectedData != data;
		}

		void restoreOriginal() const
		{
			if (!snapshotted)
				return;
			memcpy(data, &header, sizeof(DDS_FILE));
			if (hadScale)
				sprite_scales[scaleKey] = previousScale;
			else
				sprite_scales.erase(scaleKey);
		}

		// A reloaded xstset slot can still have the scale of an earlier DDS.
		// Loading the original game sprite must revoke that old ratio.
		void commitUnreplacedSuccessfulLoad(const void* selectedData) const
		{
			if (snapshotted && !replacementSelected(selectedData))
				sprite_scales.erase(scaleKey);
		}

		// Preserve the old slot on a failed decode/retry. Only a successful
		// original-DDS retry retires its previous replacement's scale.
		void finishOriginalRetry(HRESULT result) const
		{
			if (snapshotted && SUCCEEDED(result))
				sprite_scales.erase(scaleKey);
		}
	};

	// Two versions of the func depending on Settings::UseNewTextureAllocator, to reduce branching
	inline static SafetyHookInline D3DXCreateTextureFromFileInMemory = {};
	static HRESULT __stdcall D3DXCreateTextureFromFileInMemory_Custom_dest(LPDIRECT3DDEVICE9 pDevice, void* pSrcData, UINT SrcDataSize, LPDIRECT3DTEXTURE9* ppTexture)
	{
		const UiDdsOriginalState original(pSrcData, SrcDataSize);
		std::shared_ptr<std::vector<uint8_t>> transientTextureData;
		if (pSrcData && SrcDataSize)
		{
			HandleTexture(&pSrcData, &SrcDataSize, CurrentXstsetFilename, true,
				transientTextureData);
		}

		// Prefer the fast DDS decoder, then original D3DX on the selected DDS.
		// If BOTH reject an optional UI replacement, retry the unmodified game
		// DDS and revoke its premature header/scale changes.
		const HRESULT fastResult = D3DXCreateTextureFromFileInMemoryEx_Custom(
			pDevice, pSrcData, SrcDataSize, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,
			D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, ppTexture);
		if (SUCCEEDED(fastResult) || !pDevice || !pSrcData || !SrcDataSize || !ppTexture)
		{
			if (SUCCEEDED(fastResult))
				original.commitUnreplacedSuccessfulLoad(pSrcData);
			else if (original.replacementSelected(pSrcData))
				original.restoreOriginal();
			return fastResult;
		}
		const HRESULT nativeResult = D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(
			pDevice, pSrcData, SrcDataSize, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,
			D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, 0, nullptr, nullptr, ppTexture);
		if (SUCCEEDED(nativeResult) || !original.replacementSelected(pSrcData))
		{
			if (SUCCEEDED(nativeResult))
				original.commitUnreplacedSuccessfulLoad(pSrcData);
			return nativeResult;
		}
		original.restoreOriginal();
		const HRESULT originalResult = D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(
			pDevice, original.data, original.bytes, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,
			D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, 0, nullptr, nullptr, ppTexture);
		original.finishOriginalRetry(originalResult);
		return originalResult;
	}
	static HRESULT __stdcall D3DXCreateTextureFromFileInMemory_Orig_dest(LPDIRECT3DDEVICE9 pDevice, void* pSrcData, UINT SrcDataSize, LPDIRECT3DTEXTURE9* ppTexture)
	{
		const UiDdsOriginalState original(pSrcData, SrcDataSize);
		std::shared_ptr<std::vector<uint8_t>> transientTextureData;
		if (pSrcData && SrcDataSize)
		{
			HandleTexture(&pSrcData, &SrcDataSize, CurrentXstsetFilename, true,
				transientTextureData);
		}

		const HRESULT nativeResult = D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(
			pDevice, pSrcData, SrcDataSize, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,
			D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, 0, nullptr, nullptr, ppTexture);
		if (SUCCEEDED(nativeResult) || !original.replacementSelected(pSrcData))
		{
			if (SUCCEEDED(nativeResult))
				original.commitUnreplacedSuccessfulLoad(pSrcData);
			return nativeResult;
		}
		original.restoreOriginal();
		const HRESULT originalResult = D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(
			pDevice, original.data, original.bytes, D3DX_DEFAULT, D3DX_DEFAULT, 1, 0,
			D3DFMT_UNKNOWN, D3DPOOL_MANAGED, 1, 3, 0, nullptr, nullptr, ppTexture);
		original.finishOriginalRetry(originalResult);
		return originalResult;
	}


	// The optional scene/cube replacement rewrites the original DDS header.
	// Preserve the untouched original in case the decoder rejects the replacement.
	struct SceneDdsOriginalState
	{
		void* data;
		UINT bytes;
		DDS_FILE header{};
		bool snapshotted = false;
		SceneDdsOriginalState(void* source, UINT size) : data(source), bytes(size)
		{
			if (data && bytes >= sizeof(DDS_FILE))
			{
				memcpy(&header, data, sizeof(DDS_FILE));
				snapshotted = true;
			}
		}
		bool replacementSelected(const void* selectedData) const
		{
			return snapshotted && selectedData && selectedData != data;
		}
		void restoreOriginal() const
		{
			if (snapshotted)
				memcpy(data, &header, sizeof(DDS_FILE));
		}
	};

	//
	// Scene texture replacement code
	//

	inline static std::filesystem::path CurrentXmtsetFilename;

	// Two versions of the func depending on Settings::UseNewTextureAllocator, to reduce branching
	inline static SafetyHookInline D3DXCreateTextureFromFileInMemoryEx = {};
	static HRESULT __stdcall D3DXCreateTextureFromFileInMemoryEx_Custom_dest(LPDIRECT3DDEVICE9 pDevice, void* pSrcData, UINT SrcDataSize, UINT Width, UINT Height, UINT MipLevels, DWORD Usage, D3DFORMAT Format, D3DPOOL Pool, DWORD Filter, DWORD MipFilter, D3DCOLOR ColorKey, struct D3DXIMAGE_INFO* pSrcInfo, PALETTEENTRY* pPalette, LPDIRECT3DTEXTURE9* ppTexture)
	{
		const SceneDdsOriginalState original(pSrcData, SrcDataSize);
		std::shared_ptr<std::vector<uint8_t>> transientTextureData;
		if ((Settings::SceneTextureReplacement || Settings::SceneTextureExtract) && pSrcData && SrcDataSize)
		{
			HandleTexture(&pSrcData, &SrcDataSize, CurrentXmtsetFilename, false,
				transientTextureData);
		}

		// Unlike the UI-only decoder, the game's scene Ex call has richer API
		// semantics. Fast DDS does not provide pSrcInfo/pPalette, ColorKey,
		// explicit format/size, extra mips or filtered resampling. Route those
		// requests to the original Ex trampoline without modifying game state.
		const bool requiresLegacyD3DX =
			pSrcInfo != nullptr || pPalette != nullptr || ColorKey != 0 ||
			Format != D3DFMT_UNKNOWN ||
			Width != D3DX_DEFAULT || Height != D3DX_DEFAULT ||
			(MipLevels != D3DX_DEFAULT && MipLevels != 1) ||
			Usage != 0 || Pool != D3DPOOL_MANAGED ||
			(Filter != D3DX_FILTER_NONE && Filter != D3DX_DEFAULT) ||
			(MipFilter != D3DX_FILTER_NONE && MipFilter != D3DX_DEFAULT);
		if (!requiresLegacyD3DX && pDevice && pSrcData && SrcDataSize && ppTexture)
		{
			const HRESULT fastResult = D3DXCreateTextureFromFileInMemoryEx_Custom(
				pDevice, pSrcData, SrcDataSize, Width, Height, MipLevels,
				Usage, Format, Pool, Filter, MipFilter, ppTexture);
			if (SUCCEEDED(fastResult))
				return fastResult;
		}
		// A failed/unsupported fast decoder must not make world/environment
		// textures disappear. Preserve every Ex argument on the native path;
		// transientTextureData remains alive through both decoder attempts.
		const HRESULT nativeResult = D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(
			pDevice, pSrcData, SrcDataSize, Width, Height, MipLevels,
			Usage, Format, Pool, Filter, MipFilter, ColorKey,
			pSrcInfo, pPalette, ppTexture);
		if (SUCCEEDED(nativeResult) || !original.replacementSelected(pSrcData))
			return nativeResult;
		original.restoreOriginal();
		return D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(
			pDevice, original.data, original.bytes, Width, Height, MipLevels,
			Usage, Format, Pool, Filter, MipFilter, ColorKey,
			pSrcInfo, pPalette, ppTexture);
	}
	static HRESULT __stdcall D3DXCreateTextureFromFileInMemoryEx_Orig_dest(LPDIRECT3DDEVICE9 pDevice, void* pSrcData, UINT SrcDataSize, UINT Width, UINT Height, UINT MipLevels, DWORD Usage, D3DFORMAT Format, D3DPOOL Pool, DWORD Filter, DWORD MipFilter, D3DCOLOR ColorKey, struct D3DXIMAGE_INFO* pSrcInfo, PALETTEENTRY* pPalette, LPDIRECT3DTEXTURE9* ppTexture)
	{
		const SceneDdsOriginalState original(pSrcData, SrcDataSize);
		std::shared_ptr<std::vector<uint8_t>> transientTextureData;
		if ((Settings::SceneTextureReplacement || Settings::SceneTextureExtract) && pSrcData && SrcDataSize)
		{
			HandleTexture(&pSrcData, &SrcDataSize, CurrentXmtsetFilename, false,
				transientTextureData);
		}

		const HRESULT nativeResult = D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(
			pDevice, pSrcData, SrcDataSize, Width, Height, MipLevels,
			Usage, Format, Pool, Filter, MipFilter, ColorKey,
			pSrcInfo, pPalette, ppTexture);
		if (SUCCEEDED(nativeResult) || !original.replacementSelected(pSrcData))
			return nativeResult;
		original.restoreOriginal();
		return D3DXCreateTextureFromFileInMemoryEx.stdcall<HRESULT>(
			pDevice, original.data, original.bytes, Width, Height, MipLevels,
			Usage, Format, Pool, Filter, MipFilter, ColorKey,
			pSrcInfo, pPalette, ppTexture);
	}

	inline static SafetyHookInline D3DXCreateCubeTextureFromFileInMemoryEx = {};
	static HRESULT __stdcall D3DXCreateCubeTextureFromFileInMemoryEx_dest(LPDIRECT3DDEVICE9 pDevice, void* pSrcData, UINT SrcDataSize, UINT Size, UINT MipLevels, DWORD Usage, D3DFORMAT Format, D3DPOOL Pool, DWORD Filter, DWORD MipFilter, D3DCOLOR ColorKey, struct D3DXIMAGE_INFO* pSrcInfo, PALETTEENTRY* pPalette, LPDIRECT3DCUBETEXTURE9* ppCubeTexture)
	{
		const SceneDdsOriginalState original(pSrcData, SrcDataSize);
		std::shared_ptr<std::vector<uint8_t>> transientTextureData;
		if ((Settings::SceneTextureReplacement || Settings::SceneTextureExtract) && pSrcData && SrcDataSize)
		{
			HandleTexture(&pSrcData, &SrcDataSize, CurrentXmtsetFilename, false,
				transientTextureData);
		}

		const HRESULT nativeResult = D3DXCreateCubeTextureFromFileInMemoryEx.stdcall<HRESULT>(
			pDevice, pSrcData, SrcDataSize, Size, MipLevels, Usage, Format,
			Pool, Filter, MipFilter, ColorKey, pSrcInfo, pPalette, ppCubeTexture);
		if (SUCCEEDED(nativeResult) || !original.replacementSelected(pSrcData))
			return nativeResult;
		original.restoreOriginal();
		return D3DXCreateCubeTextureFromFileInMemoryEx.stdcall<HRESULT>(
			pDevice, original.data, original.bytes, Size, MipLevels, Usage, Format,
			Pool, Filter, MipFilter, ColorKey, pSrcInfo, pPalette, ppCubeTexture);
	}

	inline static SafetyHookInline LoadXmtsetObject = {};
	static int __cdecl LoadXmtsetObject_dest(char* XmtFileName, int XmtIndex)
	{
		// The engine may overwrite and reuse the same char* for another
		// stage/car pack. Compare contents, not the storage address. XmtIndex
		// is an object index inside a pack, not a new pack identity.
		if (SceneTextureCursor.Select(XmtFileName, 0))
			CurrentXmtsetFilename = SceneTextureCursor.Name();

		return LoadXmtsetObject.call<int>(XmtFileName, XmtIndex);
	}

	inline static std::atomic<bool> isComplete{ true };
	inline static std::thread cachingThread;
	static void cacheFolderFiles(const std::filesystem::path& xmtFileName)
	{
		auto fileName = xmtFileName.stem();
		auto folderPath = XmtLoadPath / fileName;

#ifdef _DEBUG
		std::string msg = "cacheFolderFiles: " + folderPath.string() + "\n";
		OutputDebugStringA(msg.c_str());
#endif

		try
		{
			FileData.cacheFolder(folderPath);
		}
		catch (const std::exception& e)
		{
			spdlog::warn(
				"Texture cache: background preload failed for {}: {}",
				folderPath.string(), e.what());
		}
		catch (...)
		{
			spdlog::warn(
				"Texture cache: background preload failed for {} with an unknown exception",
				folderPath.string());
		}

		isComplete = true;
	}

	inline static SafetyHookMid LoadXmtsetObject_Step1 = {};
	static void __cdecl LoadXmtsetObject_Step1_dest(SafetyHookContext& ctx)
	{
		if (!isComplete)
			return;

		isComplete = false;
		cachingThread = std::thread(cacheFolderFiles, (const char*)ctx.esi);
		cachingThread.detach();
	}

	inline static SafetyHookMid LoadXmtsetObject_Step3 = {};
	static void __cdecl LoadXmtsetObject_Step3_dest(SafetyHookContext& ctx)
	{
		if (!isComplete)
			ctx.eax = 0;
	}


public:
	std::string_view description() override
	{
		return "TextureReplacement";
	}

	bool validate() override
	{
		return (Settings::SceneTextureReplacement || Settings::SceneTextureExtract) ||
			(Settings::UITextureReplacement || Settings::UITextureExtract) ||
			(Settings::VREnabled && Settings::VRHudInspector);
	}

	void declare_settings() override
	{
		Settings::TextureBaseFolder.needs_restart();
		Settings::EnableTextureCache.needs_restart();
		Settings::UseNewTextureAllocator.needs_restart();
		Settings::TextureBaseFolder.hidden(true);
	}

	bool apply() override
	{
		const static int D3DXCreateTextureFromFileInMemory_Addr = 0x39412;
		const static int get_texture_Addr = 0x2A030;
		const static int put_sprite_ex_Addr = 0x2CFE0;
		const static int put_sprite_ex2_Addr = 0x2D0C0;
		const static int LoadXstsetSprite_Addr = 0x2FE20;

		const static int D3DXCreateTextureFromFileInMemoryEx_Addr = 0x39406;
		const static int D3DXCreateCubeTextureFromFileInMemoryEx_Addr = 0x3940C;
		const static int LoadXmtsetObject_Addr = 0x2E0D0;

		const static int LoadXmtsetObject_Step1_HookAddr = 0x2E169;
		const static int LoadXmtsetObject_Step3_HookAddr = 0x2E304;

		std::filesystem::path textureBaseDir = "textures";
		if (!Settings::TextureBaseFolder.get().empty())
			textureBaseDir = Settings::TextureBaseFolder.get();
		
		XmtDumpPath = textureBaseDir / "dump";
		XmtLoadPath = textureBaseDir / "load";

		if (Settings::VREnabled)
		{
			FileData.setMaxCacheSize(
				static_cast<std::size_t>(VR_MAX_TEXTURE_CACHE_SIZE_MB) *
				1024 * 1024);
			spdlog::info(
				"VR texture cache: capped at {} MiB to preserve 32-bit address space for D3D9Ex stereo/shadow resources",
				VR_MAX_TEXTURE_CACHE_SIZE_MB);
		}

		// Startup texture cache, causes game to take a while to boot, disabled for now...
#if 0
		if (std::filesystem::exists(XmtLoadPath))
		{
			for (const auto& entry : std::filesystem::recursive_directory_iterator(XmtLoadPath))
			{
				if (entry.is_regular_file()) {
					FileData.cacheFile(entry.path());
				}
			}
			std::string msg = "Initial cache size: " + std::to_string(FileData.getCacheSize());
			OutputDebugStringA(msg.c_str());
		}
#endif

		FileSystem = DirectoryFileCache(XmtLoadPath);

		bool ApplyUIHooks = Settings::UITextureReplacement || Settings::UITextureExtract;
		bool ApplySceneHooks = Settings::SceneTextureReplacement || Settings::SceneTextureExtract;
		const bool ApplyHudInspectorFeeds =
			Settings::VREnabled && Settings::VRHudInspector;

		// Scene hooks are applied through D3DXCreateTextureFromFileInMemoryEx
		// But our UI code also calls D3DXCreateTextureFromFileInMemoryEx to allow loading textures slightly faster
		// So we'll setup this hook if either are enabled
		if (ApplyUIHooks || ApplySceneHooks)
		{
			if (Settings::UseNewTextureAllocator)
				D3DXCreateTextureFromFileInMemoryEx = safetyhook::create_inline(Module::exe_ptr(D3DXCreateTextureFromFileInMemoryEx_Addr), D3DXCreateTextureFromFileInMemoryEx_Custom_dest);
			else
				D3DXCreateTextureFromFileInMemoryEx = safetyhook::create_inline(Module::exe_ptr(D3DXCreateTextureFromFileInMemoryEx_Addr), D3DXCreateTextureFromFileInMemoryEx_Orig_dest);
		}

		if (ApplyUIHooks || ApplyHudInspectorFeeds)
		{
			// The HUD inspector owns only observation feeds. Do not enable
			// replacement/extraction behavior just because diagnostics are on.
			if (ApplyUIHooks)
			{
				if(Settings::UseNewTextureAllocator)
					D3DXCreateTextureFromFileInMemory = safetyhook::create_inline(Module::exe_ptr(D3DXCreateTextureFromFileInMemory_Addr), D3DXCreateTextureFromFileInMemory_Custom_dest);
				else
					D3DXCreateTextureFromFileInMemory = safetyhook::create_inline(Module::exe_ptr(D3DXCreateTextureFromFileInMemory_Addr), D3DXCreateTextureFromFileInMemory_Orig_dest);
			}

			LoadXstsetSprite_hook = safetyhook::create_mid(Module::exe_ptr(LoadXstsetSprite_Addr), LoadXstsetSprite_dest);

			if (Settings::UITextureReplacement)
				get_texture = safetyhook::create_inline(Module::exe_ptr(get_texture_Addr), get_texture_dest);

			if (Settings::UITextureReplacement || ApplyHudInspectorFeeds)
			{
				put_sprite_ex = safetyhook::create_inline(Module::exe_ptr(put_sprite_ex_Addr), put_sprite_ex_dest);
				put_sprite_ex2 = safetyhook::create_inline(Module::exe_ptr(put_sprite_ex2_Addr), put_sprite_ex2_dest);
			}
		}

		if (ApplySceneHooks)
		{
			D3DXCreateCubeTextureFromFileInMemoryEx = safetyhook::create_inline(Module::exe_ptr(D3DXCreateCubeTextureFromFileInMemoryEx_Addr), D3DXCreateCubeTextureFromFileInMemoryEx_dest);
			LoadXmtsetObject = safetyhook::create_inline(Module::exe_ptr(LoadXmtsetObject_Addr), LoadXmtsetObject_dest);

			if (Settings::EnableTextureCache)
			{
				LoadXmtsetObject_Step1 = safetyhook::create_mid(Module::exe_ptr(LoadXmtsetObject_Step1_HookAddr), LoadXmtsetObject_Step1_dest);
				LoadXmtsetObject_Step3 = safetyhook::create_mid(Module::exe_ptr(LoadXmtsetObject_Step3_HookAddr), LoadXmtsetObject_Step3_dest);
			}
		}

		return true;
	}

	static TextureReplacement instance;
};
TextureReplacement TextureReplacement::instance;