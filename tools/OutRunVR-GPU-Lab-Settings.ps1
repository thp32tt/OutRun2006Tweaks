# Dedicated GPU-Lab per-section arguments. No global graphics defaults change.
function Set-OutRunVRGpuLabArguments {
    [CmdletBinding()]
    param(
        [string[]]$BaseArgs,
        [ValidateSet('ON','OFF')][string]$Transparency,
        [ValidateSet('512','1024')][string]$Reflection,
        [ValidateSet('0','4')][string]$SkyGlow,
        [ValidateSet('ON','OFF')][string]$StageCulling,
        [ValidateSet('OFF','2X','4X')][string]$Msaa = '4X'
    )
    $alphaValue=if($Transparency -eq 'ON'){'true'}else{'false'}
    $flags=[ordered]@{
        'Graphics.TransparencySupersampling'=$alphaValue
        'VR.TransparencySupersampling'=$alphaValue
        'Graphics.ReflectionResolution'=$Reflection
        'Graphics.SkyGlowFactor'=$SkyGlow
        'Graphics.DisableStageCulling'=if($StageCulling -eq 'ON'){'false'}else{'true'}
        'VR.AntiAliasing'=switch($Msaa){'OFF'{'0'} '2X'{'1'} '4X'{'2'}}
    }
    $out=@($BaseArgs | Where-Object {
        $arg=[string]$_
        $keep=$true
        foreach($key in $flags.Keys){
            $plain=($key -split '\.',2)[1]
            if($arg.StartsWith("-$key=",[StringComparison]::OrdinalIgnoreCase) -or
                $arg.StartsWith("-$plain=",[StringComparison]::OrdinalIgnoreCase)){
                $keep=$false
                break
            }
        }
        $keep
    })
    foreach($key in $flags.Keys){$out+="-$key=$($flags[$key])"}
    return $out
}
