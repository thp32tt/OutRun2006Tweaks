Set-StrictMode -Version Latest

function Get-OutRunVRTestProfile {
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet('CONTROL','CORRECTNESS','PERFORMANCE')]
        [string]$Name
    )

    $commonVr = @(
        '-PreferD3D9Ex=true',
        '-DirectGpuOnly=false',
        '-DisableDesktopDuplication=false',
        '-TargetRefreshRateHz=0',
        '-SkyGlowFactor=1'
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
