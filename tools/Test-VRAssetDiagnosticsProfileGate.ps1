$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $root 'OutRunVR-TestProfiles.ps1')

function Require([bool]$Condition,[string]$Message){
    if(-not $Condition){throw $Message}
}

foreach($name in @('HUD_WORLD','STAGE_DIAGNOSTIC')){
    $p=Get-OutRunVRTestProfile -Name $name
    Require ([string]$p.Environment['OUTRUN_VR_ASSET_DIAGNOSTICS'] -eq '1') "$name must request asset diagnostics"
}

foreach($name in @('CONTROL','CORRECTNESS','HUD_SCREEN','HUD_MENU','PERFORMANCE','A_BASELINE','B_CULLING','C_CULLING_NO_SSAA','D_CULLING_NO_SSAA_R512')){
    $p=Get-OutRunVRTestProfile -Name $name
    Require ([string]$p.Environment['OUTRUN_VR_ASSET_DIAGNOSTICS'] -ne '1') "$name must not request asset diagnostics"
}

$runnerPath=Join-Path $root 'Run-OutRunVRTest.ps1'
Require (Test-Path $runnerPath) 'Run-OutRunVRTest.ps1 missing'
$runner=Get-Content $runnerPath -Raw
Require ($runner -match '\$assetDiagnosticsRequested=.*OUTRUN_VR_ASSET_DIAGNOSTICS') 'runner does not derive asset diagnostics request from profile'
Require ($runner -match 'if\(\$assetDiagnosticsRequested\)') 'runner does not gate analyzer invocation'
Require ($runner -match 'assetDiagnosticsRequested=\$assetDiagnosticsRequested') 'RUN_OVERRIDES missing requested state'
Require ($runner -match 'assetDiagnosticsState=\$assetDiagnosticsState') 'RUN_OVERRIDES missing diagnostics result state'

Write-Host 'VR asset diagnostics profile gate validation passed.'
