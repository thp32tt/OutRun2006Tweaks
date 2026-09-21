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
                Description='FSR1 POC control: full OpenXR output and full-size DirectGPU transport; FSR1 disabled.'
                Arguments=@(
                    '-FramerateLimit=60',
                    '-FramerateFastLoad=0',
                    '-FramerateInterpolation=false',
                    '-FramerateUnlockExperimental=false',
                    '-FrameCadenceMode=0',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=false',
                    '-HostRenderScale=1.0',
                    '-DirectTransportScale=1.0',
                    '-FSR1Sharpness=0.0'
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
                Description='FSR1 POC A/B profile: full OpenXR output, 0.77 DirectGPU transport, EASU+RCAS sharpness 0.55.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true',
                    '-HostRenderScale=1.0',
                    '-DirectTransportScale=0.77',
                    '-FSR1Sharpness=0.55'
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
                Description='FSR1 POC correctness baseline: full OpenXR output and full-size DirectGPU transport; FSR1 disabled.'
                Arguments=@(
                    '-FramerateLimit=0',
                    '-FramerateFastLoad=3',
                    '-FramerateInterpolation=true',
                    '-FramerateUnlockExperimental=true',
                    '-FrameCadenceMode=1',
                    '-FrameCadenceTargetHz=0',
                    '-DisableDesktopVsync=true',
                    '-HostRenderScale=1.0',
                    '-DirectTransportScale=1.0',
                    '-FSR1Sharpness=0.0'
                ) + $commonVr
                Environment=[ordered]@{
                    OUTRUN_VR_TEST_PROFILE='CORRECTNESS'
                    OUTRUN_VR_PERFORMANCE_PROFILE='0'
                }
            }
        }
    }
}
