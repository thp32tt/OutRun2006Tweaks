#pragma once

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
