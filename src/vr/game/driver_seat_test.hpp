#pragma once

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <Windows.h>
#include <string>

#include "game.hpp"

namespace OutRunVR::DriverSeatTest
{
	struct CameraRestore
	{
		D3DVECTOR position{};
		D3DVECTOR look{};
		bool active = false;
	};

	bool IsActive(EvWorkCamera* camera) noexcept;
	CameraRestore ApplyCameraOffset(EvWorkCamera* camera) noexcept;
	void RestoreCamera(EvWorkCamera* camera, const CameraRestore& restore) noexcept;
}
