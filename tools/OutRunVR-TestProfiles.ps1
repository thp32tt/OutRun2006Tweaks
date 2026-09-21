Set-StrictMode -Version Latest

function Get-OutRunVRTestProfile {
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet('CONTROL','CORRECTNESS','HUD_SCREEN','HUD_MENU','HUD_WORLD','PERFORMANCE','STAGE_DIAGNOSTIC','A_BASELINE','B_CULLING','C_CULLING_NO_SSAA','D_CULLING_NO_SSAA_R512')]
        [string]$Name
    )

    $commonVr = @(
        '-PreferD3D9Ex=true',
        '-DirectGpuOnly=false',
        '-DisableDesktopDuplication=false',
        '-TargetRefreshRateHz=0',
        '-SkyGlowFactor=1',
        '-CullingUnionFov=true',
        '-CullingUnionMarginDegrees=4.0',
        '-NormalizeReflectionRate=true',
        '-NearPlane=0.10'
    )

    switch ($Name) {
        'CONTROL' {
            return [ordered]@{
                Name='CONTROL'
                Description='Conservative DX9Ex reference. Use only when CORRECTNESS needs an A/B baseline.'
                Arguments=@(
                    '-FramerateLimit=60',
                    '-FramerateFastLoad=0',
                    '-FramerateInterpolation=false',
                    '-FramerateUnlockExperimental=false',
                    '-FrameCadenceMode=0',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=false'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='CONTROL'
                    OUTRUN_VR_PERFORMANCE_PROFILE='0'
                }
            }
        }
        'STAGE_DIAGNOSTIC' {
            return [ordered]@{
                Name='STAGE_DIAGNOSTIC'
                Description='Fast world/effect diagnostic: skip intros, open debug level select and remove race timeout so sky/particle/rival/stage issues can be reproduced without menu traversal.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true',
                    '-SkipIntros',
                    '-OuttaTime',
                    '-LevelSelect'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='STAGE_DIAGNOSTIC'
                    OUTRUN_VR_PERFORMANCE_PROFILE='0'
                    OUTRUN_VR_ASSET_DIAGNOSTICS='1'
                }
            }
        }
        'HUD_SCREEN' {
            return [ordered]@{
                Name='HUD_SCREEN'
                Description='Primary HUD correctness session: rank/score/time/gear/ghost/goal/heart/rival/speech/emoji and zero-disparity alignment.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='HUD_SCREEN'
                    OUTRUN_VR_PERFORMANCE_PROFILE='0'
                    OUTRUN_VR_HUD_FOCUS='SCREEN'
                }
            }
        }
        'HUD_MENU' {
            return [ordered]@{
                Name='HUD_MENU'
                Description='Menu/UI correctness session: menu car rendering, exit YES/NO, menu recenter and non-game HUD alignment.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=0',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='HUD_MENU'
                    OUTRUN_VR_PERFORMANCE_PROFILE='0'
                    OUTRUN_VR_HUD_FOCUS='MENU'
                }
            }
        }
        'HUD_WORLD' {
            return [ordered]@{
                Name='HUD_WORLD'
                Description='World-attached display session: rival rank markers, Heart Attack markers, world hearts/lines, lens flare, smoke/skid and sky anchoring.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true',
                    '-SkipIntros',
                    '-OuttaTime',
                    '-LevelSelect'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='HUD_WORLD'
                    OUTRUN_VR_PERFORMANCE_PROFILE='0'
                    OUTRUN_VR_HUD_FOCUS='WORLD'
                    OUTRUN_VR_ASSET_DIAGNOSTICS='1'
                }
            }
        }
        'A_BASELINE' {
            return [ordered]@{
                Name='A_BASELINE'
                Description='A/B baseline: current conservative graphics policy, stage culling disabled, transparency SSAA on, reflections 1024.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true',
                    '-DisableStageCulling=true',
                    '-TransparencySupersampling=true',
                    '-ReflectionResolution=1024'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='A_BASELINE'
                    OUTRUN_VR_PERFORMANCE_PROFILE='0'
                    OUTRUN_VR_AB_GROUP='A'
                }
            }
        }
        'B_CULLING' {
            return [ordered]@{
                Name='B_CULLING'
                Description='A/B step B: enable stage culling so the VR union-FOV culling path can be evaluated; keep SSAA and 1024 reflections.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true',
                    '-DisableStageCulling=false',
                    '-TransparencySupersampling=true',
                    '-ReflectionResolution=1024'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='B_CULLING'
                    OUTRUN_VR_PERFORMANCE_PROFILE='0'
                    OUTRUN_VR_AB_GROUP='B'
                }
            }
        }
        'C_CULLING_NO_SSAA' {
            return [ordered]@{
                Name='C_CULLING_NO_SSAA'
                Description='A/B step C: B plus transparency SSAA disabled to isolate its stereo GPU cost.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true',
                    '-DisableStageCulling=false',
                    '-TransparencySupersampling=false',
                    '-ReflectionResolution=1024'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='C_CULLING_NO_SSAA'
                    OUTRUN_VR_PERFORMANCE_PROFILE='1'
                    OUTRUN_VR_AB_GROUP='C'
                }
            }
        }
        'D_CULLING_NO_SSAA_R512' {
            return [ordered]@{
                Name='D_CULLING_NO_SSAA_R512'
                Description='A/B step D: C plus 512 reflection cubemap to isolate reflection-resolution cost.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true',
                    '-DisableStageCulling=false',
                    '-TransparencySupersampling=false',
                    '-ReflectionResolution=512'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='D_CULLING_NO_SSAA_R512'
                    OUTRUN_VR_PERFORMANCE_PROFILE='1'
                    OUTRUN_VR_AB_GROUP='D'
                }
            }
        }
        'PERFORMANCE' {
            return [ordered]@{
                Name='PERFORMANCE'
                Description='CORRECTNESS runtime baseline plus opt-in performance feature flags when the binary supports them.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='PERFORMANCE'
                    OUTRUN_VR_PERFORMANCE_PROFILE='1'
                }
            }
        }
        default {
            return [ordered]@{
                Name='CORRECTNESS'
                Description='Default daily Quest/VDXR test. Correctness fixes enabled; risky performance experiments remain opt-in.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='CORRECTNESS'
                    OUTRUN_VR_PERFORMANCE_PROFILE='0'
                }
            }
        }
    }
}