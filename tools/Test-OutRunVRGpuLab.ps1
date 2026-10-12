$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'OutRunVR-GPU-Lab-Settings.ps1')
function Assert-Vector([string]$id,[string]$alpha,[string]$refl,[string]$glow,[string]$cull,[string]$aa){
    $base=@('-TransparencySupersampling=false','-ReflectionResolution=256',
      '-SkyGlowFactor=4','-DisableStageCulling=false','-AntiAliasing=1',
      '-FramerateLimit=0','-DisableDesktopVsync=true')
    $out=@(Set-OutRunVRGpuLabArguments -BaseArgs $base -Transparency $alpha -Reflection $refl -SkyGlow $glow -StageCulling $cull -Msaa $aa)
    $v=if($alpha -eq 'ON'){'true'}else{'false'}
    $expected=[ordered]@{
        'Graphics.TransparencySupersampling'=$v
        'VR.TransparencySupersampling'=$v
        'Graphics.ReflectionResolution'=$refl
        'Graphics.SkyGlowFactor'=$glow
        'Graphics.DisableStageCulling'=if($cull -eq 'ON'){'false'}else{'true'}
        'VR.AntiAliasing'=switch($aa){'OFF'{'0'} '2X'{'1'} '4X'{'2'}}
    }
    foreach($key in $expected.Keys){
        $match=@($out | Where-Object { $_ -match "^-$([regex]::Escape($key))=" })
        if($match.Count -ne 1 -or $match[0] -ne "-$key=$($expected[$key])"){
            throw "$id $key expected once: $($match -join ',')"
        }
    }
    if($out -contains '-TransparencySupersampling=false' -or
       $out -contains '-AntiAliasing=1'){throw "$id ambiguous legacy override retained"}
    if($out -notcontains '-FramerateLimit=0'){throw "$id unrelated flag lost"}
    Write-Host "PASS $id explicit Graphics+VR SSAA and MSAA"
}
Assert-Vector A ON 1024 4 OFF 4X
Assert-Vector B ON 1024 4 ON 4X
Assert-Vector C OFF 1024 4 ON 4X
Assert-Vector D OFF 512 4 ON 4X
Assert-Vector E ON 1024 0 ON 4X
Assert-Vector MSAA2 ON 1024 4 ON 2X
Assert-Vector MSAAOFF ON 1024 4 ON OFF
try{Set-OutRunVRGpuLabArguments -BaseArgs @() -Transparency ON -Reflection 999 -SkyGlow 4 -StageCulling OFF | Out-Null;throw 'INVALID_ALLOWED'}catch{if($_.Exception.Message -eq 'INVALID_ALLOWED'){throw}}
$runner=Get-Content (Join-Path $PSScriptRoot 'Run-OutRunVRTest.ps1') -Raw
$gui=Get-Content (Join-Path $PSScriptRoot 'OutRunVR-GPU-Lab.ps1') -Raw
$settings=Get-Content (Join-Path $PSScriptRoot '../src/settings.cpp') -Raw
$graphics=Get-Content (Join-Path $PSScriptRoot '../src/hooks_graphics.cpp') -Raw
foreach($token in @('GpuLabTransparency','GpuLabReflection','GpuLabSkyGlow','GpuLabCulling','GpuLabScene',
  'Set-OutRunVRGpuLabArguments','RUN_OVERRIDES.txt','GpuDiagnostics')){
    if(!$runner.Contains($token)){throw "Missing runner token $token"}
}
foreach($token in @('GPU 측정 시작','Add-Choice','Select-OutRunVRBackend.ps1',
  'Run-OutRunVRTest.ps1','-GpuDiagnostics','WATERFRONT','SAND_SPRAY','DENSE_BUILDINGS')){
    if(!$gui.Contains($token)){throw "Missing GUI token $token"}
}
foreach($token in @("keyUtf8.find('.')",'sectionUtf8 = keyUtf8.substr(0, dot)',
  '_stricmp(setting->section().data(), sectionUtf8.c_str())')){
    if(!$settings.Contains($token)){throw "Missing qualified CLI resolver $token"}
}
foreach($token in @('VR GPU LAB SSAA GATE','VR GPU LAB SSAA DEVICE',
  'Settings::VRTransparencySupersampling')){
    if(!$graphics.Contains($token)){throw "Missing actual SSAA runtime gate $token"}
}
foreach($file in @('OutRunVR-GPU-Lab.ps1','Run-OutRunVRTest.ps1',
  'OutRunVR-GPU-Lab-Settings.ps1','Test-OutRunVRGpuLab.ps1')){
    $t=$null;$e=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $file),[ref]$t,[ref]$e)
    if($e.Count){throw "PowerShell syntax failed $file : $($e -join '; ')"}
}
Write-Host 'PASS seven vectors + negative invalid + two-gate SSAA source checks'
