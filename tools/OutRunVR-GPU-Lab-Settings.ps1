# Pure argument transformation, sourceable with no side effects.
function Set-OutRunVRGpuLabArguments {
    [CmdletBinding()]
    param(
        [string[]]$BaseArgs,
        [ValidateSet('ON','OFF')][string]$Transparency,
        [ValidateSet('512','1024')][string]$Reflection,
        [ValidateSet('0','4')][string]$SkyGlow,
        [ValidateSet('ON','OFF')][string]$StageCulling
    )
    $flags=[ordered]@{
        TransparencySupersampling=if($Transparency -eq 'ON'){'true'}else{'false'}
        ReflectionResolution=$Reflection
        SkyGlowFactor=$SkyGlow
        DisableStageCulling=if($StageCulling -eq 'ON'){'false'}else{'true'}
    }
    $out=@($BaseArgs | Where-Object {
        $arg=[string]$_
        $keep=$true
        foreach($name in $flags.Keys) {
            if($arg.StartsWith("-$name=",[StringComparison]::OrdinalIgnoreCase)) {
                $keep=$false
                break
            }
        }
        $keep
    })
    foreach($name in $flags.Keys){$out+="-$name=$($flags[$name])"}
    return $out
}
