Set-StrictMode -Version Latest

function Get-OutRunVRTestProfile {
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet('CONTROL','CORRECTNESS','PERFORMANCE','STAGE_DIAGNOSTIC')]
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