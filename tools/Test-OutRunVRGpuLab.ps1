$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'OutRunVR-GPU-Lab-Settings.ps1')
function Assert-Vector([string]$id,[string]$alpha,[string]$refl,[string]$glow,[string]$cull){
    $in=@('-FramerateLimit=0','-TransparencySupersampling=false','-ReflectionResolution=256',
          '-SkyGlowFactor=4','-DisableStageCulling=false','-DisableDesktopVsync=true')
    $out=@(Set-OutRunVRGpuLabArguments -BaseArgs $in -Transparency $alpha -Reflection $refl -SkyGlow $glow -StageCulling $cull)
    $expected=@{
        TransparencySupersampling=if($alpha -eq 'ON'){'true'}else{'false'}
        ReflectionResolution=$refl
        SkyGlowFactor=$glow
        DisableStageCulling=if($cull -eq 'ON'){'false'}else{'true'}
    }
    foreach($k in $expected.Keys){
        $matches=@($out|Where-Object {$_ -match "^-$k="})
        if($matches.Count -ne 1 -or $matches[0] -ne "-$k=$($expected[$k])"){throw "$id $k failed"}
    }
    if($out -notcontains '-FramerateLimit=0' -or $out -notcontains '-DisableDesktopVsync=true'){throw "$id lost unrelated flag"}
    Write-Host "PASS GPU lab $id"
}
Assert-Vector A ON 1024 4 OFF
Assert-Vector B ON 1024 4 ON
Assert-Vector C OFF 1024 4 ON
Assert-Vector D OFF 512 4 ON
Assert-Vector E ON 1024 0 ON
try {Set-OutRunVRGpuLabArguments -BaseArgs @() -Transparency ON -Reflection 999 -SkyGlow 4 -StageCulling OFF | Out-Null;throw 'invalid input accepted'} catch {if($_.Exception.Message -eq 'invalid input accepted'){throw}}
$runner=Get-Content (Join-Path $PSScriptRoot 'Run-OutRunVRTest.ps1') -Raw
$gui=Get-Content (Join-Path $PSScriptRoot 'OutRunVR-GPU-Lab.ps1') -Raw
foreach($token in @('GpuLabTransparency','GpuLabReflection','GpuLabSkyGlow','GpuLabCulling',
    'GpuLabScene','Set-OutRunVRGpuLabArguments','RUN_OVERRIDES.txt','GpuDiagnostics')){
    if(!$runner.Contains($token)){throw "missing runner token $token"}
}
foreach($token in @('GPU 측정 시작','Add-Choice','Select-OutRunVRBackend.ps1',
    'Run-OutRunVRTest.ps1','-GpuDiagnostics','WATERFRONT','SAND_SPRAY','DENSE_BUILDINGS')){
    if(!$gui.Contains($token)){throw "missing GUI token $token"}
}
foreach($p in @('OutRunVR-GPU-Lab.ps1','Run-OutRunVRTest.ps1','OutRunVR-GPU-Lab-Settings.ps1')){
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $p),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw "PowerShell parser error $p : $($errors -join '; ')"}
}
Write-Host 'PASS GPU lab GUI/presets + 5 positive/1 negative vectors + parser'
