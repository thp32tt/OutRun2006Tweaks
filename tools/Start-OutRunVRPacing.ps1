# Separate opt-in launcher, does not alter normal selector/configuration.
$ErrorActionPreference = 'Stop'
$env:OUTRUN_VR_PACING_DIAGNOSTICS = '1'
& (Join-Path $PSScriptRoot 'OutRunVR-Slot-Selector.ps1')
