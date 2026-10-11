param(
    [ValidateSet('CONTROL','CORRECTNESS','HUD_SCREEN','HUD_MENU','HUD_WORLD','PERFORMANCE','STAGE_DIAGNOSTIC')]
    [string]$TestProfile='CORRECTNESS'
)
$ErrorActionPreference='Stop'
$launcher=Join-Path $PSScriptRoot 'Run-OutRunVRTest.ps1'
if(-not(Test-Path $launcher)){throw 'DX9Ex launcher missing'}
$old=[Environment]::GetEnvironmentVariable('OUTRUN_VR_NATIVE_EYE_GEOMETRY','Process')
Write-Warning 'OPT-IN EXPERIMENT: Requires host eye size before CreateDeviceEx or next GAME-INITIATED ResetEx. Host may start later; change graphics settings once to use game ResetEx.'
Write-Warning 'GPU cost/HUD/HMD image quality not verified. Normal launcher leaves native geometry OFF.'
try{
    $env:OUTRUN_VR_NATIVE_EYE_GEOMETRY='1'
    & $launcher -TestProfile $TestProfile
    if(-not $?) {throw 'DX9Ex native game launcher failed'}
} finally{
    [Environment]::SetEnvironmentVariable('OUTRUN_VR_NATIVE_EYE_GEOMETRY',$old,'Process')
}
